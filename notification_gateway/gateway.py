"""Bounded server-side notification gateway.

The package deliberately has no browser integration and uses only the standard
library.  Telegram is a transport, not an authority: receipts are verified
against the exact request before an event is marked delivered.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import secrets
import sqlite3
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Mapping

MAX_TELEGRAM_LENGTH = 4096
MAX_COOLDOWN = 7200
SEVERITIES = frozenset({"INFO", "WARNING", "OWNER_ACTION", "CRITICAL"})
PROVENANCE_KEYS = frozenset({"repo", "head_sha", "pr", "issue", "run"})
TOP_LEVEL_KEYS = frozenset({
    "event_id", "producer", "event_code", "severity", "summary", "impact",
    "owner_action", "provenance", "occurred_at", "sequence", "business_id",
})
SHA_RE = re.compile(r"^[0-9a-f]{40}$", re.I)
REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
SAFE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
EVENT_CODE_RE = re.compile(r"^[A-Z0-9][A-Z0-9_.-]{1,63}$")
CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
URL_RE = re.compile(r"https?://\S+", re.I)
TOKEN_RE = re.compile(
    r"(?i)(?:bearer\s+|token\s*[:=]\s*|password\s*[:=]\s*|"
    r"secret\s*[:=]\s*|api[_ -]?key\s*[:=]\s*)[^\s,;]+"
)
PEM_RE = re.compile(r"-----BEGIN [^-]+-----.*?-----END [^-]+-----", re.S)
BARE_TOKEN_RE = re.compile(r"\b(?:sk|gh[pousr]|xox[baprs])-[A-Za-z0-9_-]{8,}\b")


class GatewayError(ValueError):
    """A safe, non-secret event or state transition error."""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *_args: Any, **_kwargs: Any) -> None:
        return None


_SAFE_URL_OPEN = urllib.request.build_opener(_NoRedirect()).open


def _safe_text(value: str, limit: int = 1000) -> str:
    if not isinstance(value, str) or len(value) > limit:
        raise GatewayError("text field is invalid")
    if CONTROL_RE.search(value) or any(0xD800 <= ord(c) <= 0xDFFF for c in value):
        raise GatewayError("text contains unsafe characters")
    value = PEM_RE.sub("[REDACTED]", value)
    value = URL_RE.sub("[URL REDACTED]", value)
    value = TOKEN_RE.sub("[CREDENTIAL REDACTED]", value)
    return BARE_TOKEN_RE.sub("[CREDENTIAL REDACTED]", value)


def redact(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): redact(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact(v) for v in value]
    if isinstance(value, str):
        return _safe_text(value)
    return value


def _utc(value: Any, now: float) -> str:
    if not isinstance(value, str) or value.endswith("Z") or "+" not in value:
        raise GatewayError("occurred_at must be timezone-aware ISO-8601")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise GatewayError("occurred_at is invalid") from exc
    timestamp = parsed.timestamp()
    if not math.isfinite(timestamp) or timestamp > now + 300 or timestamp < now - 90 * 86400:
        raise GatewayError("occurred_at is outside the accepted window")
    return value


@dataclass(frozen=True)
class NotificationEvent:
    event_id: str
    producer: str
    event_code: str
    severity: str
    summary: str
    impact: str
    owner_action: str
    provenance: Mapping[str, Any]
    occurred_at: str
    sequence: int = 0
    business_id: str = ""

    @classmethod
    def from_mapping(
        cls, raw: Mapping[str, Any], trusted_producers: frozenset[str],
        allowed_repos: frozenset[str] = frozenset(), now: Callable[[], float] = time.time,
    ) -> "NotificationEvent":
        if not isinstance(raw, Mapping) or set(raw) - TOP_LEVEL_KEYS:
            raise GatewayError("event schema is not closed")
        required = TOP_LEVEL_KEYS - {"sequence", "business_id"}
        if not required.issubset(raw):
            raise GatewayError("event schema is incomplete")
        producer = raw["producer"]
        if not isinstance(producer, str) or producer not in trusted_producers:
            raise GatewayError("producer is not authenticated")
        severity = raw["severity"]
        if not isinstance(severity, str) or severity not in SEVERITIES:
            raise GatewayError("invalid severity")
        event_id = raw["event_id"]
        event_code = raw["event_code"]
        if not isinstance(event_id, str) or not SAFE_ID_RE.fullmatch(event_id):
            raise GatewayError("invalid event_id")
        if not isinstance(event_code, str) or not EVENT_CODE_RE.fullmatch(event_code):
            raise GatewayError("invalid event_code")
        provenance = raw["provenance"]
        if not isinstance(provenance, Mapping) or set(provenance) - PROVENANCE_KEYS:
            raise GatewayError("provenance schema is invalid")
        repo = provenance.get("repo")
        if not isinstance(repo, str) or not REPO_RE.fullmatch(repo) or (
            allowed_repos and repo not in allowed_repos
        ):
            raise GatewayError("repository is not allowed")
        if not isinstance(provenance.get("head_sha"), str) or not SHA_RE.fullmatch(
            provenance["head_sha"]
        ):
            raise GatewayError("head_sha is invalid")
        for key in ("pr", "issue", "run"):
            if key in provenance and (
                type(provenance[key]) is not int or not 0 < provenance[key] < 10**9
            ):
                raise GatewayError("provenance reference is invalid")
        sequence = raw.get("sequence", 0)
        if type(sequence) is not int or not 0 <= sequence < 10**9:
            raise GatewayError("sequence is invalid")
        business_id = raw.get("business_id", event_id)
        if not isinstance(business_id, str) or not SAFE_ID_RE.fullmatch(business_id):
            raise GatewayError("business_id is invalid")
        return cls(
            event_id, producer, event_code, severity,
            _safe_text(raw["summary"]), _safe_text(raw["impact"]),
            _safe_text(raw["owner_action"]), dict(provenance),
            _utc(raw["occurred_at"], now()), sequence, business_id,
        )

    def should_notify(self) -> bool:
        return self.severity in {"OWNER_ACTION", "CRITICAL"} or (
            self.severity == "WARNING" and bool(self.owner_action.strip())
        )

    def canonical(self) -> str:
        return json.dumps(self.__dict__, sort_keys=True, separators=(",", ":"))


def format_telegram_message(event: NotificationEvent) -> str:
    provenance = " ".join(
        f"{key}={event.provenance[key]}" for key in ("repo", "head_sha", "pr", "issue", "run")
        if key in event.provenance
    )
    text = (
        f"[{event.severity}] {event.event_code}\n"
        f"What happened: {event.summary}\nImpact: {event.impact}\n"
        f"Minimum owner action: {event.owner_action}\nProvenance: {provenance}"
    )
    encoded = text.encode("utf-16-le", "surrogatepass")
    if len(encoded) // 2 <= MAX_TELEGRAM_LENGTH:
        return text
    return encoded[: (MAX_TELEGRAM_LENGTH - 1) * 2].decode("utf-16-le", "ignore") + "…"


@dataclass(frozen=True)
class TransportOutcome:
    kind: str  # sent, retry, rejected, unknown
    message_id: int | None = None
    chat_id: str | None = None
    text: str | None = None
    retry_after: int | None = None


class SQLiteState:
    def __init__(self, path: str, clock: Callable[[], float] = time.time,
                 random_fn: Callable[[], float] = lambda: 0.0):
        if not path or path == ":memory:":
            raise GatewayError("durable external state path is required")
        self.path, self.clock, self.random_fn = path, clock, random_fn
        self.db = sqlite3.connect(path, timeout=5, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS events (
          producer TEXT, repo TEXT, business_id TEXT, event_id TEXT, fingerprint TEXT,
          payload TEXT, sequence INTEGER, status TEXT, created_at REAL,
          PRIMARY KEY (producer, repo, business_id)
        );
        CREATE TABLE IF NOT EXISTS outbox (
          event_id TEXT PRIMARY KEY, attempts INTEGER NOT NULL, next_attempt REAL,
          lease_until REAL, lease_token TEXT, status TEXT
        );
        CREATE TABLE IF NOT EXISTS send_intents (
          event_id TEXT, attempt INTEGER, text_digest TEXT, text TEXT, created_at REAL,
          PRIMARY KEY(event_id, attempt)
        );
        CREATE TABLE IF NOT EXISTS receipts (
          event_id TEXT, attempt INTEGER, provider TEXT, message_id INTEGER,
          chat_id TEXT, text_digest TEXT, verified INTEGER, created_at REAL,
          PRIMARY KEY(event_id, attempt)
        );
        CREATE TABLE IF NOT EXISTS audit (
          id INTEGER PRIMARY KEY AUTOINCREMENT, event_id TEXT, transition TEXT,
          detail TEXT, created_at REAL
        );
        CREATE TABLE IF NOT EXISTS dead_letters (
          event_id TEXT PRIMARY KEY, reason TEXT, created_at REAL
        );
        CREATE TABLE IF NOT EXISTS provider_state (
          name TEXT PRIMARY KEY, cooldown_until REAL NOT NULL DEFAULT 0
        );
        """)

    def close(self) -> None:
        self.db.close()

    def __enter__(self) -> "SQLiteState":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    def _audit(self, event_id: str, transition: str, detail: str = "") -> None:
        self.db.execute("INSERT INTO audit(event_id,transition,detail,created_at) VALUES(?,?,?,?)",
                        (event_id, transition, redact(detail), self.clock()))

    def enqueue(self, event: NotificationEvent) -> str:
        fingerprint = hashlib.sha256(event.canonical().encode()).hexdigest()
        repo = event.provenance["repo"]
        self.db.execute("BEGIN IMMEDIATE")
        try:
            old = self.db.execute(
                "SELECT fingerprint, sequence FROM events WHERE producer=? AND repo=? AND business_id=?",
                (event.producer, repo, event.business_id)).fetchone()
            if old:
                if old["fingerprint"] != fingerprint:
                    raise GatewayError("duplicate business event conflicts")
                self.db.execute("COMMIT")
                return "duplicate"
            prior = self.db.execute(
                "SELECT MAX(sequence) AS n FROM events WHERE producer=? AND repo=? AND business_id=?",
                (event.producer, repo, event.business_id)).fetchone()["n"]
            if prior is not None and event.sequence < prior:
                raise GatewayError("stale event")
            status = "QUEUED" if event.should_notify() else "SILENT"
            self.db.execute("INSERT INTO events VALUES (?,?,?,?,?,?,?,?,?)",
                            (event.producer, repo, event.business_id, event.event_id,
                             fingerprint, event.canonical(), event.sequence, status, self.clock()))
            if event.should_notify():
                self.db.execute("INSERT INTO outbox VALUES (?,?,?,0,NULL,'READY')",
                                (event.event_id, 0, self.clock()))
            self._audit(event.event_id, status)
            self.db.execute("COMMIT")
            return status.lower()
        except Exception:
            self.db.execute("ROLLBACK")
            raise

    def claim(self, lease_seconds: int = 60) -> dict[str, Any] | None:
        now = self.clock()
        self.recover_expired()
        self.db.execute("BEGIN IMMEDIATE")
        cooldown = self.db.execute(
            "SELECT cooldown_until FROM provider_state WHERE name='telegram'").fetchone()
        if cooldown and cooldown["cooldown_until"] > now:
            self.db.execute("COMMIT")
            return None
        row = self.db.execute(
            "SELECT o.*, e.payload FROM outbox o JOIN events e ON e.event_id=o.event_id "
            "WHERE o.status='READY' AND o.next_attempt<=? ORDER BY o.next_attempt LIMIT 1",
            (now,)).fetchone()
        if not row:
            self.db.execute("COMMIT")
            return None
        token = secrets.token_hex(16)
        self.db.execute("UPDATE outbox SET status='LEASED', lease_until=?, lease_token=? WHERE event_id=?",
                        (now + lease_seconds, token, row["event_id"]))
        self._audit(row["event_id"], "LEASED")
        self.db.execute("COMMIT")
        return {**dict(row), "lease_token": token}

    def recover_expired(self) -> int:
        now = self.clock()
        self.db.execute("BEGIN IMMEDIATE")
        rows = self.db.execute(
            "SELECT event_id FROM outbox WHERE status='LEASED' AND lease_until<?", (now,)).fetchall()
        for row in rows:
            self.db.execute("UPDATE outbox SET status='UNKNOWN', lease_token=NULL WHERE event_id=?",
                            (row["event_id"],))
            self.db.execute("UPDATE events SET status='UNKNOWN' WHERE event_id=?", (row["event_id"],))
            self._audit(row["event_id"], "LEASE_EXPIRED", "possible send quarantined")
        self.db.execute("COMMIT")
        return len(rows)

    def record_intent(self, item: Mapping[str, Any], text: str) -> str:
        digest = hashlib.sha256(text.encode()).hexdigest()
        self.db.execute("BEGIN IMMEDIATE")
        row = self.db.execute("SELECT status, lease_token FROM outbox WHERE event_id=?", (item["event_id"],)).fetchone()
        if not row or row["status"] != "LEASED" or row["lease_token"] != item["lease_token"]:
            self.db.execute("ROLLBACK")
            raise GatewayError("stale lease")
        attempt = int(item["attempts"]) + 1
        self.db.execute("INSERT INTO send_intents VALUES (?,?,?,?,?)",
                        (item["event_id"], attempt, digest, text, self.clock()))
        self._audit(item["event_id"], "SEND_INTENT", f"attempt={attempt}")
        self.db.execute("COMMIT")
        return digest

    def finish(self, item: Mapping[str, Any], outcome: TransportOutcome,
               max_attempts: int = 5) -> str:
        self.db.execute("BEGIN IMMEDIATE")
        row = self.db.execute("SELECT * FROM outbox WHERE event_id=? AND lease_token=? AND status='LEASED'",
                              (item["event_id"], item["lease_token"])).fetchone()
        if not row:
            self.db.execute("ROLLBACK")
            raise GatewayError("stale lease")
        attempt = row["attempts"] + 1
        intent = self.db.execute("SELECT * FROM send_intents WHERE event_id=? AND attempt=?",
                                 (item["event_id"], attempt)).fetchone()
        if outcome.kind == "sent":
            if not intent or outcome.message_id is None or outcome.chat_id is None or outcome.text is None:
                outcome = TransportOutcome("unknown")
            elif hashlib.sha256(outcome.text.encode()).hexdigest() != intent["text_digest"]:
                outcome = TransportOutcome("unknown")
            else:
                self.db.execute("INSERT INTO receipts VALUES (?,?,?,?,?,?,?,?)",
                                (item["event_id"], attempt, "telegram", outcome.message_id,
                                 outcome.chat_id, intent["text_digest"], 1, self.clock()))
        status = {"sent": "VERIFIED", "unknown": "UNKNOWN", "rejected": "BLOCKED"}.get(outcome.kind)
        if status:
            self.db.execute("UPDATE outbox SET status=?, attempts=?, lease_token=NULL WHERE event_id=?",
                            (status, attempt, item["event_id"]))
            self.db.execute("UPDATE events SET status=? WHERE event_id=?", (status, item["event_id"]))
            self._audit(item["event_id"], status, outcome.kind)
            if status == "UNKNOWN":
                self.db.execute("INSERT OR REPLACE INTO dead_letters VALUES (?,?,?)",
                                (item["event_id"], "ambiguous provider outcome", self.clock()))
            self.db.execute("COMMIT")
            return status.lower()
        if attempt >= max_attempts:
            self.db.execute("UPDATE outbox SET status='DEAD', attempts=?, lease_token=NULL WHERE event_id=?",
                            (attempt, item["event_id"]))
            self.db.execute("UPDATE events SET status='DEAD' WHERE event_id=?", (item["event_id"],))
            self.db.execute("INSERT OR REPLACE INTO dead_letters VALUES (?,?,?)",
                            (item["event_id"], "retry budget exhausted", self.clock()))
            self._audit(item["event_id"], "DEAD")
            self.db.execute("COMMIT")
            return "dead"
        delay = min(MAX_COOLDOWN, 2 ** min(attempt, 10)) + self.random_fn()
        self.db.execute("UPDATE outbox SET status='READY', attempts=?, next_attempt=?, lease_until=0, lease_token=NULL WHERE event_id=?",
                        (attempt, self.clock() + delay, item["event_id"]))
        self._audit(item["event_id"], "RETRY", f"attempt={attempt}")
        self.db.execute("COMMIT")
        return "retry"

    def pause(self, item: Mapping[str, Any]) -> str:
        self.db.execute("BEGIN IMMEDIATE")
        row = self.db.execute(
            "SELECT status, lease_token FROM outbox WHERE event_id=?", (item["event_id"],)
        ).fetchone()
        if not row or row["status"] != "LEASED" or row["lease_token"] != item["lease_token"]:
            self.db.execute("ROLLBACK")
            raise GatewayError("stale lease")
        self.db.execute(
            "UPDATE outbox SET status='PAUSED', lease_token=NULL WHERE event_id=?",
            (item["event_id"],),
        )
        self.db.execute("UPDATE events SET status='PAUSED' WHERE event_id=?", (item["event_id"],))
        self._audit(item["event_id"], "PAUSED", "provider configuration absent")
        self.db.execute("COMMIT")
        return "paused"

    def cooldown(self, seconds: int) -> None:
        value = self.clock() + max(0, min(int(seconds), MAX_COOLDOWN))
        self.db.execute("""INSERT INTO provider_state VALUES('telegram',?)
                           ON CONFLICT(name) DO UPDATE SET cooldown_until=
                           MAX(cooldown_until, excluded.cooldown_until)""", (value,))

    def reconcile(self, event_id: str, evidence: list[str], decision: str) -> str:
        if decision not in {"delivered", "not_delivered", "dead"} or not evidence or len(evidence) > 5:
            raise GatewayError("bounded reconciliation evidence is required")
        if any(not isinstance(ref, str) or not SAFE_ID_RE.fullmatch(ref) for ref in evidence):
            raise GatewayError("invalid evidence reference")
        self.db.execute("BEGIN IMMEDIATE")
        row = self.db.execute("SELECT status FROM events WHERE event_id=?", (event_id,)).fetchone()
        if not row or row["status"] != "UNKNOWN":
            self.db.execute("ROLLBACK")
            raise GatewayError("only UNKNOWN events can be reconciled")
        status = {"delivered": "RECONCILED", "not_delivered": "DEAD", "dead": "DEAD"}[decision]
        self.db.execute("UPDATE events SET status=? WHERE event_id=?", (status, event_id))
        self.db.execute("UPDATE outbox SET status=?, lease_token=NULL WHERE event_id=?", (status, event_id))
        self._audit(event_id, "RECONCILE", f"{decision} evidence={','.join(evidence)}")
        self.db.execute("COMMIT")
        return status.lower()

    def health(self, provider_ready: bool = True) -> dict[str, Any]:
        self.recover_expired()
        rows = self.db.execute("SELECT status, COUNT(*) count FROM outbox GROUP BY status").fetchall()
        counts = {row["status"]: row["count"] for row in rows}
        bad = counts.get("UNKNOWN", 0) + counts.get("DEAD", 0) + counts.get("BLOCKED", 0)
        state = "BLOCKED" if bad else (
            "PAUSED" if (counts.get("PAUSED") or not provider_ready) else "READY"
        )
        return {"queue": counts, "dead_letters": counts.get("DEAD", 0), "state": state}


class DirectTelegramTransport:
    def __init__(self, token: str, chat_id: str, opener: Callable[..., Any] = _SAFE_URL_OPEN):
        if not token or not chat_id:
            raise GatewayError("Telegram configuration is incomplete")
        self.token, self.chat_id, self.opener = token, chat_id, opener

    def send(self, text: str) -> TransportOutcome:
        request = urllib.request.Request(
            f"https://api.telegram.org/bot{self.token}/sendMessage",
            data=json.dumps({"chat_id": self.chat_id, "text": text}).encode(),
            headers={"Content-Type": "application/json"}, method="POST",
        )
        try:
            with self.opener(request, timeout=10) as response:
                body = json.loads(response.read().decode("utf-8"))
                if not isinstance(body, dict) or body.get("ok") is not True:
                    return TransportOutcome("unknown")
                result = body.get("result")
                if not isinstance(result, dict) or type(result.get("message_id")) is not int:
                    return TransportOutcome("unknown")
                chat = result.get("chat")
                if not isinstance(chat, dict) or str(chat.get("id")) != str(self.chat_id):
                    return TransportOutcome("unknown")
                if result.get("text") != text:
                    return TransportOutcome("unknown")
                return TransportOutcome("sent", result["message_id"], str(chat["id"]), result["text"])
        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                try:
                    body = json.loads(exc.read().decode())
                    params = body.get("parameters") if isinstance(body, dict) else None
                    retry = params.get("retry_after") if isinstance(params, dict) else None
                    return TransportOutcome("retry", retry_after=retry if type(retry) is int else None)
                except (ValueError, OSError):
                    return TransportOutcome("unknown")
            if 400 <= exc.code < 500:
                return TransportOutcome("rejected")
            return TransportOutcome("unknown")
        except (urllib.error.URLError, TimeoutError, OSError, ValueError, TypeError):
            return TransportOutcome("unknown")


class Gateway:
    def __init__(self, state: SQLiteState, trusted_producers: Mapping[str, str] | set[str],
                 transport: Any = None, allowed_repos: set[str] | None = None,
                 clock: Callable[[], float] = time.time):
        self.state, self.transport, self.clock = state, transport, clock
        self.producers = (dict.fromkeys(trusted_producers, "local")
                          if not isinstance(trusted_producers, Mapping) else dict(trusted_producers))
        self.allowed_repos = frozenset(allowed_repos or ())

    def submit(self, raw: Mapping[str, Any], auth: str = "local") -> str:
        producer = raw.get("producer") if isinstance(raw, Mapping) else None
        if producer not in self.producers or not isinstance(auth, str) or not secrets.compare_digest(
            str(self.producers[producer]), auth
        ):
            raise GatewayError("producer authentication failed")
        event = NotificationEvent.from_mapping(raw, frozenset(self.producers), self.allowed_repos, self.clock)
        return self.state.enqueue(event)

    def process_one(self, max_attempts: int = 5) -> str:
        item = self.state.claim()
        if not item:
            return "empty"
        event = NotificationEvent(**json.loads(item["payload"]))
        text = format_telegram_message(event)
        if not self.transport:
            return self.state.pause(item)
        else:
            self.state.record_intent(item, text)
            try:
                outcome = self.transport.send(text)
            except GatewayError:
                outcome = TransportOutcome("unknown")
            if isinstance(outcome, tuple):
                kind, retry_after = outcome
                outcome = TransportOutcome(
                    "sent" if kind == "sent" else "retry",
                    retry_after=retry_after,
                    text=text if kind == "sent" else None,
                )
        if outcome.kind == "retry" and outcome.retry_after is not None:
            self.state.cooldown(outcome.retry_after)
        return self.state.finish(item, outcome, max_attempts)


def doctor() -> dict[str, bool]:
    return {
        "ALPHAMIND_TELEGRAM_BOT_TOKEN": bool(os.getenv("ALPHAMIND_TELEGRAM_BOT_TOKEN")),
        "ALPHAMIND_TELEGRAM_CHAT_ID": bool(os.getenv("ALPHAMIND_TELEGRAM_CHAT_ID")),
        "ALPHAMIND_NOTIFICATION_STATE": bool(os.getenv("ALPHAMIND_NOTIFICATION_STATE")),
    }
