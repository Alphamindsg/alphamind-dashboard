"""Read-only Telegram inline navigation for notification and report state."""

from __future__ import annotations

import json
import secrets
from dataclasses import dataclass
from typing import Any, Mapping

from .gateway import GatewayError, MAX_TELEGRAM_LENGTH, REPO_RE, SQLiteState, _safe_text, redact
from .report import Report, ReportStore

CALLBACK_PREFIX = "menu"
CALLBACK_TTL_SECONDS = 900
CALLBACK_RATE_LIMIT_WINDOW = 30
CALLBACK_RATE_LIMIT_MAX = 12
REPO_PAGE_SIZE = 4
SECTION_LABELS = {
    "status": "Status",
    "changes_since_previous": "Recent Changes",
    "exact_head_evidence": "Latest Evidence",
    "defects_blockers": "Blockers",
    "tests_security_recovery": "Tests / CI",
    "next_autonomous_work": "ETA",
    "owner_actions": "Owner Action",
}
REPO_SECTION_ACTIONS = {
    "repo_status": "status",
    "repo_progress": "changes_since_previous",
    "repo_tests": "tests_security_recovery",
    "repo_blockers": "defects_blockers",
    "repo_changes": "changes_since_previous",
    "repo_eta": "next_autonomous_work",
}


def _button(text: str, callback_data: str | None = None, url: str | None = None) -> dict[str, str]:
    value = {"text": text}
    if callback_data is not None:
        value["callback_data"] = callback_data
    if url is not None:
        value["url"] = url
    return value


def _keyboard(*rows: list[dict[str, str]]) -> dict[str, list[list[dict[str, str]]]]:
    return {"inline_keyboard": [row for row in rows if row]}


def _session_state(row: Mapping[str, Any]) -> dict[str, Any]:
    return json.loads(row["state_json"])


@dataclass(frozen=True)
class MenuRender:
    text: str
    reply_markup: Mapping[str, Any]
    view: str


class TelegramInlineMenuService:
    def __init__(
        self,
        state: SQLiteState,
        store: ReportStore | None = None,
        transport: Any = None,
        allowed_chat_id: str = "",
        allowed_user_ids: set[str] | None = None,
        callback_ttl_seconds: int = CALLBACK_TTL_SECONDS,
        callback_window: int = CALLBACK_RATE_LIMIT_WINDOW,
        callback_limit: int = CALLBACK_RATE_LIMIT_MAX,
    ):
        if not allowed_chat_id:
            raise GatewayError("Telegram menu chat binding is required")
        if not allowed_user_ids:
            raise GatewayError("Telegram menu user binding is required")
        self.state = state
        self.db = state.db
        self.store = store or ReportStore(state)
        self.transport = transport
        self.allowed_chat_id = str(allowed_chat_id)
        self.allowed_user_ids = {str(value) for value in allowed_user_ids}
        self.callback_ttl_seconds = callback_ttl_seconds
        self.callback_window = callback_window
        self.callback_limit = callback_limit

    def open_home(self, user_id: str, expected_heads: Mapping[str, str] | None = None) -> dict[str, Any]:
        user = str(user_id)
        self._authorize(self.allowed_chat_id, user)
        session_id = secrets.token_hex(8)
        now = self.state.clock()
        state = {
            "view": "home",
            "history": [],
            "repo": None,
            "report_id": None,
            "report_revision": None,
            "report_part": 0,
            "page": 0,
            "expected_heads": dict(expected_heads or {}),
        }
        self.db.execute(
            "INSERT INTO telegram_menu_sessions(session_id,chat_id,user_id,message_id,revision,state_json,active,created_at,updated_at) VALUES(?,?,?,?,?,?,1,?,?)",
            (session_id, self.allowed_chat_id, user, None, 1, json.dumps(state, sort_keys=True), now, now),
        )
        render = self._render(session_id, 1, state)
        outcome = self._send_menu(render)
        if outcome["status"] != "sent":
            self.db.execute("UPDATE telegram_menu_sessions SET active=0,updated_at=? WHERE session_id=?", (now, session_id))
            return outcome
        self.db.execute(
            "UPDATE telegram_menu_sessions SET message_id=?,updated_at=? WHERE session_id=?",
            (outcome["message_id"], now, session_id),
        )
        self._audit_render(session_id, 1, render.view, "home-opened")
        return {
            "status": "sent",
            "session_id": session_id,
            "message_id": outcome["message_id"],
            "view": render.view,
        }

    def handle_update(self, raw: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(raw, Mapping):
            raise GatewayError("callback update is invalid")
        callback = raw.get("callback_query")
        if not isinstance(callback, Mapping):
            raise GatewayError("callback query is required")
        message = callback.get("message")
        actor = callback.get("from")
        if not isinstance(message, Mapping) or not isinstance(actor, Mapping):
            raise GatewayError("callback message context is required")
        chat = message.get("chat")
        if not isinstance(chat, Mapping):
            raise GatewayError("callback chat context is required")
        callback_id = callback.get("id")
        data = callback.get("data")
        message_id = message.get("message_id")
        if not isinstance(callback_id, str) or not isinstance(data, str) or type(message_id) is not int:
            raise GatewayError("callback payload is invalid")
        return self.handle_callback(
            callback_id=callback_id,
            chat_id=str(chat.get("id")),
            user_id=str(actor.get("id")),
            message_id=message_id,
            data=data,
        )

    def handle_callback(
        self, callback_id: str, chat_id: str, user_id: str, message_id: int, data: str
    ) -> dict[str, Any]:
        cached = self.db.execute(
            "SELECT outcome,detail FROM telegram_menu_callbacks WHERE callback_id=?",
            (callback_id,),
        ).fetchone()
        if cached:
            self._answer_callback(callback_id, "Already processed")
            detail = json.loads(cached["detail"])
            return {"status": cached["outcome"], **detail}
        try:
            action, session_id, revision, argument = self._parse_callback(data)
        except GatewayError:
            return self._record_callback(
                callback_id, "invalid", "invalid", "rejected", {"reason": "invalid-callback-data"}
            )
        row = self.db.execute(
            "SELECT * FROM telegram_menu_sessions WHERE session_id=?",
            (session_id,),
        ).fetchone()
        if not row:
            return self._record_callback(callback_id, session_id, action, "stale", {"reason": "missing-session"})
        try:
            self._authorize(chat_id, user_id)
        except GatewayError:
            return self._record_callback(callback_id, session_id, action, "rejected", {"reason": "unauthorized"})
        if str(row["chat_id"]) != str(chat_id) or str(row["user_id"]) != str(user_id):
            return self._record_callback(callback_id, session_id, action, "rejected", {"reason": "actor-mismatch"})
        if not row["active"] or row["message_id"] != message_id:
            return self._record_callback(callback_id, session_id, action, "stale", {"reason": "message-superseded"})
        if int(row["revision"]) != revision:
            return self._record_callback(callback_id, session_id, action, "stale", {"reason": "stale-revision"})
        current = _session_state(row)
        now = self.state.clock()
        if now - float(row["updated_at"]) > self.callback_ttl_seconds:
            self.db.execute(
                "UPDATE telegram_menu_sessions SET active=0,updated_at=? WHERE session_id=?",
                (now, session_id),
            )
            return self._record_callback(callback_id, session_id, action, "stale", {"reason": "expired"})
        if self._rate_limited(chat_id, user_id):
            return self._record_callback(callback_id, session_id, action, "rate_limited", {"reason": "callback-rate-limited"})
        try:
            updated = self._transition(dict(current), action, argument)
        except (GatewayError, ValueError):
            return self._record_callback(callback_id, session_id, action, "rejected", {"reason": "invalid-action"})
        new_revision = revision + 1
        render = self._render(session_id, new_revision, updated)
        outcome = self._edit_menu(message_id, render)
        if outcome["status"] != "sent":
            return self._record_callback(
                callback_id,
                session_id,
                action,
                outcome["status"],
                {"reason": outcome.get("reason", outcome["status"])},
            )
        self.db.execute(
            "UPDATE telegram_menu_sessions SET revision=?,state_json=?,updated_at=? WHERE session_id=?",
            (new_revision, json.dumps(updated, sort_keys=True), now, session_id),
        )
        self._audit_render(session_id, new_revision, render.view, f"callback={action}")
        self._answer_callback(callback_id, "Updated")
        return self._record_callback(callback_id, session_id, action, "sent", {"view": render.view, "revision": new_revision})

    def _authorize(self, chat_id: str, user_id: str) -> None:
        if str(chat_id) != self.allowed_chat_id or str(user_id) not in self.allowed_user_ids:
            raise GatewayError("callback actor is not authorized")

    def _rate_limited(self, chat_id: str, user_id: str) -> bool:
        now = self.state.clock()
        row = self.db.execute(
            "SELECT window_start,count FROM telegram_menu_rate_limits WHERE chat_id=? AND user_id=?",
            (str(chat_id), str(user_id)),
        ).fetchone()
        if not row or now - row["window_start"] >= self.callback_window:
            self.db.execute(
                "INSERT INTO telegram_menu_rate_limits(chat_id,user_id,window_start,count) VALUES(?,?,?,1) "
                "ON CONFLICT(chat_id,user_id) DO UPDATE SET window_start=excluded.window_start,count=excluded.count",
                (str(chat_id), str(user_id), now),
            )
            return False
        if row["count"] >= self.callback_limit:
            return True
        self.db.execute(
            "UPDATE telegram_menu_rate_limits SET count=count+1 WHERE chat_id=? AND user_id=?",
            (str(chat_id), str(user_id)),
        )
        return False

    def _parse_callback(self, data: str) -> tuple[str, str, int, str | None]:
        parts = data.split(":")
        if len(parts) < 4 or parts[0] != CALLBACK_PREFIX:
            raise GatewayError("callback data is invalid")
        session_id = parts[1]
        if len(session_id) != 16:
            raise GatewayError("callback session is invalid")
        try:
            revision = int(parts[2])
        except ValueError as exc:
            raise GatewayError("callback revision is invalid") from exc
        action = parts[3]
        argument = parts[4] if len(parts) > 4 else None
        return action, session_id, revision, argument

    def _callback_data(self, session_id: str, revision: int, action: str, argument: str | None = None) -> str:
        parts = [CALLBACK_PREFIX, session_id, str(revision), action]
        if argument is not None:
            parts.append(argument)
        value = ":".join(parts)
        if len(value.encode("utf-8")) > 64:
            raise GatewayError("callback payload exceeds Telegram limit")
        return value

    def _transition(self, state: dict[str, Any], action: str, argument: str | None) -> dict[str, Any]:
        next_state = dict(state)
        current_view = str(state["view"])
        if action == "home":
            next_state.update({"view": "home", "repo": None, "report_part": 0, "page": 0, "history": []})
            return next_state
        if action == "back":
            history = list(state.get("history") or [])
            if not history:
                next_state.update({"view": "home", "repo": None, "report_part": 0, "page": 0})
                return next_state
            previous = history.pop()
            next_state.update(previous)
            next_state["history"] = history
            return next_state
        if action in {"portfolio", "owner", "blocked", "changes", "repositories", "full_report", "settings", "help"}:
            next_state["history"] = list(state.get("history") or []) + [self._snapshot(state)]
            target = {
                "portfolio": "portfolio_status",
                "owner": "owner_action",
                "blocked": "blocked_incidents",
                "changes": "todays_changes",
                "repositories": "repositories",
                "full_report": "full_report",
                "settings": "settings",
                "help": "help",
            }[action]
            next_state["view"] = target
            if target != "full_report":
                next_state["report_part"] = 0
            return next_state
        if action in {"repo_next", "repo_prev"}:
            next_state["page"] = max(0, int(state.get("page", 0)) + (1 if action == "repo_next" else -1))
            return next_state
        if action == "repo":
            repos = self._repositories()
            if argument is None:
                raise GatewayError("repository selection is invalid")
            index = int(argument)
            if not 0 <= index < len(repos):
                raise GatewayError("repository selection is invalid")
            next_state["history"] = list(state.get("history") or []) + [self._snapshot(state)]
            next_state["view"] = "repo_overview"
            next_state["repo"] = repos[index]
            next_state["report_part"] = 0
            return next_state
        if action in REPO_SECTION_ACTIONS:
            next_state["history"] = list(state.get("history") or []) + [self._snapshot(state)]
            next_state["view"] = action
            return next_state
        if action in {"details", "evidence", "why"}:
            next_state["history"] = list(state.get("history") or []) + [self._snapshot(state)]
            next_state["view"] = action
            return next_state
        if action in {"report_next", "report_prev"}:
            report = self._latest_report(str(state.get("repo") or "")) or self._latest_report()
            parts = report.telegram_parts() if report else []
            if not parts:
                raise GatewayError("no report is available")
            delta = 1 if action == "report_next" else -1
            next_state["report_part"] = min(max(0, int(state.get("report_part", 0)) + delta), len(parts) - 1)
            next_state["view"] = "full_report"
            return next_state
        raise GatewayError("callback action is invalid")

    def _snapshot(self, state: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "view": state.get("view"),
            "repo": state.get("repo"),
            "report_part": state.get("report_part", 0),
            "page": state.get("page", 0),
        }

    def _render(self, session_id: str, revision: int, state: Mapping[str, Any]) -> MenuRender:
        view = str(state["view"])
        repo = state.get("repo")
        if view == "home":
            text = self._render_home()
            keyboard = _keyboard(
                [
                    _button("Portfolio Status", self._callback_data(session_id, revision, "portfolio")),
                    _button("Owner Action", self._callback_data(session_id, revision, "owner")),
                ],
                [
                    _button("Blocked / Incidents", self._callback_data(session_id, revision, "blocked")),
                    _button("Today's Changes", self._callback_data(session_id, revision, "changes")),
                ],
                [
                    _button("Repositories", self._callback_data(session_id, revision, "repositories")),
                    _button("Full Report", self._callback_data(session_id, revision, "full_report")),
                ],
                [
                    _button("Settings", self._callback_data(session_id, revision, "settings")),
                    _button("Help", self._callback_data(session_id, revision, "help")),
                ],
            )
            return MenuRender(text, keyboard, view)
        if view == "repositories":
            return self._render_repositories(session_id, revision, state)
        if view == "repo_overview":
            return self._render_repo_overview(session_id, revision, str(repo))
        if view in REPO_SECTION_ACTIONS:
            return self._render_repo_section(session_id, revision, str(repo), REPO_SECTION_ACTIONS[view])
        if view == "portfolio_status":
            return self._render_context(
                session_id, revision, view, "Portfolio Status", self._portfolio_status_text()
            )
        if view == "owner_action":
            return self._render_context(
                session_id, revision, view, "Owner Action", self._owner_action_text(repo if isinstance(repo, str) else None)
            )
        if view == "blocked_incidents":
            return self._render_context(
                session_id, revision, view, "Blocked / Incidents", self._blocked_text(repo if isinstance(repo, str) else None)
            )
        if view == "todays_changes":
            return self._render_context(
                session_id, revision, view, "Today's Changes", self._changes_text(repo if isinstance(repo, str) else None)
            )
        if view == "details":
            return self._render_context(
                session_id, revision, view, "View Details", self._details_text(repo if isinstance(repo, str) else None)
            )
        if view == "evidence":
            return self._render_context(
                session_id, revision, view, "Latest Evidence", self._evidence_text(state, repo if isinstance(repo, str) else None)
            )
        if view == "why":
            return self._render_context(
                session_id, revision, view, "Why?", self._why_text(repo if isinstance(repo, str) else None)
            )
        if view == "full_report":
            return self._render_full_report(session_id, revision, state, repo if isinstance(repo, str) else None)
        if view == "settings":
            return self._render_context(
                session_id,
                revision,
                view,
                "Settings",
                f"Read-only menu is bound to chat {self.allowed_chat_id} and user(s) {', '.join(sorted(self.allowed_user_ids))}.\n"
                "No inline action can mutate production, credentials, or delivery state.",
            )
        if view == "help":
            return self._render_context(
                session_id,
                revision,
                view,
                "Help",
                "Use the buttons to inspect status, evidence, blockers, and reports. "
                "Telegram callbacks are validated server-side on every tap and stale or unauthorized callbacks are rejected.",
            )
        raise GatewayError("menu view is invalid")

    def _render_context(self, session_id: str, revision: int, view: str, heading: str, body: str) -> MenuRender:
        text = self._fit_text(f"{heading}\n\n{body}")
        keyboard = _keyboard(
            [
                _button("View Details", self._callback_data(session_id, revision, "details")),
                _button("Latest Evidence", self._callback_data(session_id, revision, "evidence")),
            ],
            [
                _button("Why?", self._callback_data(session_id, revision, "why")),
                _button("Back", self._callback_data(session_id, revision, "back")),
            ],
            [_button("Home", self._callback_data(session_id, revision, "home"))],
        )
        return MenuRender(text, keyboard, view)

    def _render_repositories(self, session_id: str, revision: int, state: Mapping[str, Any]) -> MenuRender:
        repos = self._repositories()
        page = int(state.get("page", 0))
        pages = max(1, (len(repos) + REPO_PAGE_SIZE - 1) // REPO_PAGE_SIZE)
        page = min(page, pages - 1)
        start = page * REPO_PAGE_SIZE
        items = repos[start:start + REPO_PAGE_SIZE]
        lines = [f"Repositories page {page + 1}/{pages}"]
        if not items:
            lines.append("No repositories have recent alert or report evidence.")
        else:
            for repo in items:
                lines.append(f"- {repo}")
        rows = [[_button(repo, self._callback_data(session_id, revision, "repo", str(start + offset)))] for offset, repo in enumerate(items)]
        nav: list[dict[str, str]] = []
        if page > 0:
            nav.append(_button("Prev", self._callback_data(session_id, revision, "repo_prev")))
        if page + 1 < pages:
            nav.append(_button("Next", self._callback_data(session_id, revision, "repo_next")))
        rows.extend([nav, [_button("Back", self._callback_data(session_id, revision, "back"))], [_button("Home", self._callback_data(session_id, revision, "home"))]])
        return MenuRender(self._fit_text("\n".join(lines)), _keyboard(*rows), "repositories")

    def _render_repo_overview(self, session_id: str, revision: int, repo: str) -> MenuRender:
        event = self._latest_event(repo)
        report = self._latest_report(repo)
        lines = [f"Repository: {repo}"]
        if event:
            lines.append(f"Alert: {event['event_code']} [{event['status']}]")
            lines.append(event["summary"])
        if report:
            lines.append(f"Report revision: {report.revision}")
            lines.append(f"Status: {report.sections['status']}")
        if not event and not report:
            lines.append("No repository evidence is currently available.")
        rows = [
            [
                _button("Status", self._callback_data(session_id, revision, "repo_status")),
                _button("Progress", self._callback_data(session_id, revision, "repo_progress")),
            ],
            [
                _button("Tests / CI", self._callback_data(session_id, revision, "repo_tests")),
                _button("Blockers", self._callback_data(session_id, revision, "repo_blockers")),
            ],
            [
                _button("Recent Changes", self._callback_data(session_id, revision, "repo_changes")),
                _button("ETA", self._callback_data(session_id, revision, "repo_eta")),
            ],
            [
                _button("Latest Evidence", self._callback_data(session_id, revision, "evidence")),
                _button("Why?", self._callback_data(session_id, revision, "why")),
            ],
        ]
        github_url = self._github_url(event)
        if github_url:
            rows.append([_button("Open GitHub", url=github_url)])
        rows.extend([
            [_button("Back", self._callback_data(session_id, revision, "back"))],
            [_button("Home", self._callback_data(session_id, revision, "home"))],
        ])
        return MenuRender(self._fit_text("\n".join(lines)), _keyboard(*rows), "repo_overview")

    def _render_repo_section(self, session_id: str, revision: int, repo: str, section: str) -> MenuRender:
        report = self._latest_report(repo)
        body = report.sections[section] if report else f"No {SECTION_LABELS[section].lower()} evidence is available."
        keyboard = _keyboard(
            [_button("Latest Evidence", self._callback_data(session_id, revision, "evidence"))],
            [
                _button("Back", self._callback_data(session_id, revision, "back")),
                _button("Home", self._callback_data(session_id, revision, "home")),
            ],
        )
        return MenuRender(self._fit_text(f"{repo} — {SECTION_LABELS[section]}\n\n{body}"), keyboard, section)

    def _render_full_report(self, session_id: str, revision: int, state: Mapping[str, Any], repo: str | None) -> MenuRender:
        report = self._latest_report(repo or "") or self._latest_report()
        if not report:
            return MenuRender(
                "Full Report\n\nNo report is currently available.",
                _keyboard(
                    [_button("Back", self._callback_data(session_id, revision, "back"))],
                    [_button("Home", self._callback_data(session_id, revision, "home"))],
                ),
                "full_report",
            )
        parts = report.telegram_parts()
        part = min(max(0, int(state.get("report_part", 0))), len(parts) - 1)
        text = self._fit_text(f"Full Report {part + 1}/{len(parts)}\n\n{parts[part]}")
        nav: list[dict[str, str]] = []
        if part > 0:
            nav.append(_button("Prev", self._callback_data(session_id, revision, "report_prev")))
        if part + 1 < len(parts):
            nav.append(_button("Next", self._callback_data(session_id, revision, "report_next")))
        return MenuRender(
            text,
            _keyboard(
                nav,
                [_button("Back", self._callback_data(session_id, revision, "back"))],
                [_button("Home", self._callback_data(session_id, revision, "home"))],
            ),
            "full_report",
        )

    def _render_home(self) -> str:
        health = self.state.health(provider_ready=bool(self.transport))
        latest = self._latest_report()
        repos = self._repositories()
        lines = [
            "Portfolio Control Plane",
            f"Gateway state: {health['state']}",
            f"Queue summary: {json.dumps(health['queue'], sort_keys=True)}",
            f"Active repositories: {len(repos)}",
        ]
        if latest:
            lines.append(f"Latest report: {latest.report_id} revision {latest.revision} ({latest.scope})")
        return self._fit_text("\n".join(lines))

    def _portfolio_status_text(self) -> str:
        health = self.state.health(provider_ready=bool(self.transport))
        latest = self._latest_report()
        lines = [
            f"Gateway state: {health['state']}",
            f"Queue: {json.dumps(health['queue'], sort_keys=True)}",
            f"Dead letters: {health['dead_letters']}",
        ]
        if latest:
            lines.append(f"Latest report status: {latest.sections['status']}")
        return self._fit_text("\n".join(lines))

    def _owner_action_text(self, repo: str | None) -> str:
        report = self._latest_report(repo or "")
        if report:
            return report.sections["owner_actions"]
        event = self._latest_event(repo)
        if event:
            return event["owner_action"]
        return "No owner action is currently pending."

    def _blocked_text(self, repo: str | None) -> str:
        report = self._latest_report(repo or "")
        if report:
            return report.sections["defects_blockers"]
        rows = self.db.execute(
            "SELECT payload,status FROM events WHERE (? = '' OR repo=?) AND status IN ('UNKNOWN','BLOCKED','DEAD','PAUSED') ORDER BY created_at DESC LIMIT 5",
            (repo or "", repo or ""),
        ).fetchall()
        if not rows:
            return "No blocked incidents are currently recorded."
        lines = []
        for row in rows:
            payload = json.loads(row["payload"])
            lines.append(f"{row['status']}: {payload['event_code']} — {payload['summary']}")
        return self._fit_text("\n".join(lines))

    def _changes_text(self, repo: str | None) -> str:
        report = self._latest_report(repo or "")
        if report:
            return report.sections["changes_since_previous"]
        return "No current report changes are available."

    def _details_text(self, repo: str | None) -> str:
        event = self._latest_event(repo)
        report = self._latest_report(repo or "")
        lines: list[str] = []
        if event:
            lines.extend([
                f"Alert code: {event['event_code']}",
                f"Severity: {event['severity']}",
                f"Impact: {event['impact']}",
            ])
        if report:
            lines.extend([
                f"Report scope: {report.scope}",
                f"Window: {report.window}",
                f"Next autonomous work: {report.sections['next_autonomous_work']}",
            ])
        return self._fit_text("\n".join(lines) if lines else "No additional details are available.")

    def _evidence_text(self, state: Mapping[str, Any], repo: str | None) -> str:
        report = self._latest_report(repo or "")
        event = self._latest_event(repo)
        lines: list[str] = []
        if report:
            lines.append(report.sections["exact_head_evidence"])
        if event:
            lines.append(
                f"repo={event['repo']} head_sha={event['head_sha']} pr={event.get('pr', 'n/a')} run={event.get('run', 'n/a')}"
            )
        expected = (state.get("expected_heads") or {}).get(repo) if repo else None
        if expected:
            actual = event["head_sha"] if event else ""
            if actual != expected and (not report or expected not in report.sections["exact_head_evidence"]):
                lines.append(f"STALE EXACT-HEAD EVIDENCE: expected {expected}")
        return self._fit_text("\n".join(lines) if lines else "No exact-head evidence is currently available.")

    def _why_text(self, repo: str | None) -> str:
        report = self._latest_report(repo or "")
        if report:
            return (
                f"Blockers: {report.sections['defects_blockers']}\n\n"
                f"Owner action: {report.sections['owner_actions']}"
            )
        event = self._latest_event(repo)
        if event:
            return f"Impact: {event['impact']}\nOwner action: {event['owner_action']}"
        return "No explanatory evidence is currently available."

    def _repositories(self) -> list[str]:
        repos = {
            row["repo"]
            for row in self.db.execute("SELECT DISTINCT repo FROM events WHERE repo <> ''").fetchall()
            if isinstance(row["repo"], str) and REPO_RE.fullmatch(row["repo"])
        }
        for row in self.db.execute("SELECT DISTINCT scope FROM reports").fetchall():
            scope = row["scope"]
            if isinstance(scope, str) and REPO_RE.fullmatch(scope):
                repos.add(scope)
        return sorted(repos)

    def _latest_report(self, repo: str = "") -> Report | None:
        if repo:
            row = self.db.execute(
                "SELECT canonical FROM reports WHERE scope=? ORDER BY revision DESC LIMIT 1",
                (repo,),
            ).fetchone()
        else:
            row = self.db.execute(
                "SELECT canonical FROM reports ORDER BY created_at DESC, revision DESC LIMIT 1"
            ).fetchone()
        return Report.from_mapping(json.loads(row["canonical"])) if row else None

    def _latest_event(self, repo: str | None) -> dict[str, Any] | None:
        if repo:
            row = self.db.execute(
                "SELECT payload,status FROM events WHERE repo=? ORDER BY created_at DESC, sequence DESC LIMIT 1",
                (repo,),
            ).fetchone()
        else:
            row = self.db.execute(
                "SELECT payload,status FROM events ORDER BY created_at DESC, sequence DESC LIMIT 1"
            ).fetchone()
        if not row:
            return None
        payload = json.loads(row["payload"])
        return {
            "status": row["status"],
            "event_code": payload["event_code"],
            "severity": payload["severity"],
            "summary": payload["summary"],
            "impact": payload["impact"],
            "owner_action": payload["owner_action"],
            "repo": payload["provenance"]["repo"],
            "head_sha": payload["provenance"]["head_sha"],
            "pr": payload["provenance"].get("pr"),
            "run": payload["provenance"].get("run"),
        }

    def _github_url(self, event: Mapping[str, Any] | None) -> str | None:
        if not event:
            return None
        repo = event.get("repo")
        if not isinstance(repo, str) or not REPO_RE.fullmatch(repo):
            return None
        if type(event.get("run")) is int:
            return f"https://github.com/{repo}/actions/runs/{event['run']}"
        if type(event.get("pr")) is int:
            return f"https://github.com/{repo}/pull/{event['pr']}"
        return f"https://github.com/{repo}"

    def _fit_text(self, text: str) -> str:
        text = text.strip()
        if len(text.encode("utf-16-le")) // 2 <= MAX_TELEGRAM_LENGTH:
            return text
        suffix = "\n…[truncated]"
        truncated = ""
        for character in text:
            candidate = truncated + character + suffix
            if len(candidate.encode("utf-16-le")) // 2 > MAX_TELEGRAM_LENGTH:
                break
            truncated += character
        return truncated + suffix

    def _send_menu(self, render: MenuRender) -> dict[str, Any]:
        if not self.transport:
            return {"status": "sent", "message_id": 0}
        outcome = self.transport.send(render.text, reply_markup=render.reply_markup, chat_id=self.allowed_chat_id)
        return self._transport_result(outcome)

    def _edit_menu(self, message_id: int, render: MenuRender) -> dict[str, Any]:
        if not self.transport:
            return {"status": "sent", "message_id": message_id}
        outcome = self.transport.edit(
            message_id, render.text, reply_markup=render.reply_markup, chat_id=self.allowed_chat_id
        )
        return self._transport_result(outcome)

    def _answer_callback(self, callback_id: str, text: str) -> None:
        if self.transport:
            self.transport.answer_callback(callback_id, text)

    def _transport_result(self, outcome: Any) -> dict[str, Any]:
        kind = getattr(outcome, "kind", "unknown")
        if kind == "sent":
            return {"status": "sent", "message_id": getattr(outcome, "message_id", None) or 0}
        if kind == "retry":
            return {"status": "retry", "reason": "telegram-retry"}
        if kind == "rejected":
            return {"status": "rejected", "reason": "telegram-rejected"}
        return {"status": "unknown", "reason": "telegram-unknown"}

    def _record_callback(
        self, callback_id: str, session_id: str, action: str, outcome: str, detail: Mapping[str, Any]
    ) -> dict[str, Any]:
        body = json.dumps(redact(detail), sort_keys=True)
        self.db.execute(
            "INSERT INTO telegram_menu_callbacks(callback_id,session_id,action,outcome,detail,created_at) VALUES(?,?,?,?,?,?)",
            (callback_id, session_id, action, outcome, body, self.state.clock()),
        )
        if outcome != "sent":
            self._answer_callback(callback_id, str(detail.get("reason", outcome)))
        return {"status": outcome, **json.loads(body)}

    def _audit_render(self, session_id: str, revision: int, view: str, detail: str) -> None:
        self.db.execute(
            "INSERT INTO telegram_menu_audit(session_id,revision,view,detail,created_at) VALUES(?,?,?,?,?)",
            (session_id, revision, view, _safe_text(detail, 256), self.state.clock()),
        )
