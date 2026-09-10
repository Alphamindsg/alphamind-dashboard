"""Durable dual-destination report delivery layered on the notification state."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping

from .gateway import GatewayError, MAX_TELEGRAM_LENGTH, SQLiteState, _safe_text

DESTINATIONS = ("chatgpt", "telegram")
REQUIRED_SECTIONS = (
    "status",
    "changes_since_previous",
    "exact_head_evidence",
    "defects_blockers",
    "tests_security_recovery",
    "next_autonomous_work",
    "owner_actions",
)
REPORT_KEYS = frozenset({
    "report_id", "revision", "kind", "scope", "window", "previous_report_id",
    "sections", "priority",
})


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class Report:
    report_id: str
    revision: int
    kind: str
    scope: str
    window: str
    previous_report_id: str | None
    sections: Mapping[str, str]
    priority: str = "normal"

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "Report":
        if not isinstance(raw, Mapping) or set(raw) - REPORT_KEYS:
            raise GatewayError("report schema is not closed")
        required = REPORT_KEYS - {"previous_report_id", "priority"}
        if not required.issubset(raw):
            raise GatewayError("report schema is incomplete")
        if not isinstance(raw["revision"], int) or isinstance(raw["revision"], bool) or raw["revision"] < 1:
            raise GatewayError("report revision is invalid")
        values = []
        for key in ("report_id", "kind", "scope", "window"):
            value = raw[key]
            if not isinstance(value, str):
                raise GatewayError("report identity is invalid")
            values.append(_safe_text(value, 128))
        previous = raw.get("previous_report_id")
        if previous is not None:
            previous = _safe_text(previous, 128)
        sections = raw["sections"]
        if not isinstance(sections, Mapping) or set(sections) != set(REQUIRED_SECTIONS):
            raise GatewayError("report sections are incomplete")
        safe_sections = {
            key: _safe_text(sections[key], 6000) for key in REQUIRED_SECTIONS
        }
        priority = raw.get("priority", "normal")
        if priority not in {"normal", "urgent", "critical"}:
            raise GatewayError("report priority is invalid")
        return cls(values[0], raw["revision"], values[1], values[2], values[3], previous, safe_sections, priority)

    def canonical(self) -> str:
        return json.dumps(self.__dict__, sort_keys=True, separators=(",", ":"))

    @property
    def content_hash(self) -> str:
        return _digest(self.canonical())

    def full_text(self) -> str:
        return "\n".join(f"{key.upper().replace('_', ' ')}: {self.sections[key]}" for key in REQUIRED_SECTIONS)

    def telegram_parts(self) -> list[str]:
        # Split only at section boundaries; every part repeats its section label.
        parts: list[str] = []
        current = ""
        for key in REQUIRED_SECTIONS:
            label = f"{key.upper().replace('_', ' ')}: "
            section = label + self.sections[key]
            if len(section.encode("utf-16-le")) // 2 > MAX_TELEGRAM_LENGTH:
                if current:
                    parts.append(current)
                    current = ""
                chunk = ""
                for character in self.sections[key]:
                    candidate = label + chunk + character
                    if len(candidate.encode("utf-16-le")) // 2 > MAX_TELEGRAM_LENGTH:
                        parts.append(label + chunk)
                        chunk = character
                    else:
                        chunk += character
                if chunk:
                    parts.append(label + chunk)
                continue
            if len((current + "\n" + section).encode("utf-16-le")) // 2 > MAX_TELEGRAM_LENGTH:
                if current:
                    parts.append(current)
                current = section
            else:
                current = (current + "\n" + section).strip()
        if current:
            parts.append(current)
        return parts


@dataclass(frozen=True)
class DeliveryReceipt:
    destination: str
    report_id: str
    revision: int
    part: int
    content_hash: str
    provider_message_id: str
    attempt_id: str


@dataclass(frozen=True)
class DeliveryRetry:
    retry_after: int | None = None


@dataclass(frozen=True)
class DeliveryUnknown:
    reason: str = "ambiguous provider outcome"


@dataclass(frozen=True)
class DeliveryBlocked:
    reason: str = "destination unavailable"


class ReportStore:
    """Stores canonical reports and independently keyed destination parts."""

    def __init__(self, state: SQLiteState):
        self.state = state
        self.db = state.db
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS reports (
          report_id TEXT, revision INTEGER, kind TEXT, scope TEXT, window TEXT,
          previous_report_id TEXT, content_hash TEXT, canonical TEXT, status TEXT,
          priority TEXT, created_at TEXT, PRIMARY KEY(report_id, revision)
        );
        CREATE TABLE IF NOT EXISTS report_deliveries (
          report_id TEXT, revision INTEGER, destination TEXT, part INTEGER,
          total_parts INTEGER, content_hash TEXT, body TEXT, status TEXT,
          attempts INTEGER, receipt_id TEXT, last_error TEXT, next_attempt REAL,
          lease_until REAL, lease_token TEXT, attempt_id TEXT,
          PRIMARY KEY(report_id, revision, destination, part)
        );
        CREATE TABLE IF NOT EXISTS report_audit (
          id INTEGER PRIMARY KEY AUTOINCREMENT, report_id TEXT, revision INTEGER,
          destination TEXT, part INTEGER, transition TEXT, detail TEXT, created_at TEXT
        );
        """)
        self.db.execute(
            """CREATE TABLE IF NOT EXISTS report_delivery_cursor (
               id INTEGER PRIMARY KEY CHECK(id=1), last_destination TEXT)"""
        )

    def _audit(self, report: Report, destination: str, part: int, transition: str, detail: str = "") -> None:
        self.db.execute(
            "INSERT INTO report_audit(report_id,revision,destination,part,transition,detail,created_at) VALUES(?,?,?,?,?,?,?)",
            (report.report_id, report.revision, destination, part, transition, detail, _now()),
        )

    def ingest(self, report: Report) -> str:
        canonical = report.canonical()
        self.db.execute("BEGIN IMMEDIATE")
        try:
            existing = self.db.execute(
                "SELECT content_hash FROM reports WHERE report_id=? AND revision=?",
                (report.report_id, report.revision),
            ).fetchone()
            if existing:
                if existing["content_hash"] != report.content_hash:
                    raise GatewayError("report revision conflicts")
                self.db.execute("COMMIT")
                return "duplicate"
            if report.revision > 1:
                previous = self.db.execute(
                    "SELECT 1 FROM reports WHERE report_id=? AND revision=?",
                    (report.previous_report_id, report.revision - 1),
                ).fetchone()
                if not report.previous_report_id or not previous:
                    raise GatewayError("previous report revision is required")
            telegram = report.telegram_parts()
            self.db.execute(
                "INSERT INTO reports VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (report.report_id, report.revision, report.kind, report.scope, report.window,
                 report.previous_report_id, report.content_hash, canonical, "GENERATED",
                 report.priority, _now()),
            )
            prefix = f"REPORT {report.report_id} REVISION {report.revision}"
            bodies = {"chatgpt": [report.full_text()], "telegram": [
                f"{prefix} PART {index + 1}/{len(telegram)}\n{body}"
                for index, body in enumerate(telegram)
            ]}
            for destination, parts in bodies.items():
                for index, body in enumerate(parts):
                    self.db.execute(
                        "INSERT INTO report_deliveries VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (report.report_id, report.revision, destination, index, len(parts),
                         _digest(body), body, "PENDING", 0, None, None, 0, 0, None, None),
                    )
                    self._audit(report, destination, index, "PENDING")
            self.db.execute("COMMIT")
            return "generated"
        except Exception:
            self.db.execute("ROLLBACK")
            raise

    def report(self, report_id: str, revision: int) -> Report:
        row = self.db.execute(
            "SELECT canonical FROM reports WHERE report_id=? AND revision=?",
            (report_id, revision),
        ).fetchone()
        if not row:
            raise GatewayError("report not found")
        return Report.from_mapping(json.loads(row["canonical"]))

    def pending(self, report_id: str, revision: int) -> list[sqlite3.Row]:
        return self.db.execute(
            """SELECT * FROM report_deliveries WHERE report_id=? AND revision=?
               AND status IN ('PENDING','RETRY') AND next_attempt<=?
               ORDER BY part""",
            (report_id, revision, self.state.clock()),
        ).fetchall()

    def claim(self, report_id: str, revision: int, lease_seconds: int = 60) -> dict[str, Any] | None:
        now = self.state.clock()
        self.db.execute("BEGIN IMMEDIATE")
        self.db.execute(
            """UPDATE report_deliveries SET status='UNKNOWN', lease_token=NULL
               WHERE status='LEASED' AND lease_until<?""", (now,))
        last = self.db.execute(
            "SELECT last_destination FROM report_delivery_cursor WHERE id=1"
        ).fetchone()
        preferred = "telegram" if last and last["last_destination"] == "chatgpt" else "chatgpt"
        row = self.db.execute(
            """SELECT * FROM report_deliveries WHERE report_id=? AND revision=?
               AND status IN ('PENDING','RETRY') AND next_attempt<=?
               ORDER BY (SELECT CASE priority WHEN 'critical' THEN 0 WHEN 'urgent' THEN 1 ELSE 2 END
                         FROM reports WHERE reports.report_id=report_deliveries.report_id
                         AND reports.revision=report_deliveries.revision),
                        CASE WHEN destination=? THEN 0 ELSE 1 END, part LIMIT 1""",
            (report_id, revision, now, preferred),
        ).fetchone()
        if not row:
            self.db.execute("COMMIT")
            return None
        token = secrets.token_hex(16)
        attempt_id = secrets.token_hex(16)
        self.db.execute(
            """UPDATE report_deliveries SET status='LEASED', lease_until=?,
               lease_token=?, attempt_id=?, attempts=attempts+1 WHERE report_id=?
               AND revision=? AND destination=? AND part=?""",
            (now + lease_seconds, token, attempt_id, report_id, revision,
             row["destination"], row["part"]),
        )
        self.db.execute(
            """INSERT INTO report_delivery_cursor(id,last_destination) VALUES(1,?)
               ON CONFLICT(id) DO UPDATE SET last_destination=excluded.last_destination""",
            (row["destination"],),
        )
        self._audit(self.report(report_id, revision), row["destination"], row["part"], "LEASED", attempt_id)
        self.db.execute("COMMIT")
        return {**dict(row), "lease_token": token, "attempt_id": attempt_id,
                "attempts": row["attempts"] + 1}

    def record(self, report: Report, delivery: Mapping[str, Any], receipt: DeliveryReceipt | None,
               attempt_id: str, lease_token: str) -> str:
        self.db.execute("BEGIN IMMEDIATE")
        row = self.db.execute(
            """SELECT * FROM report_deliveries WHERE report_id=? AND revision=?
               AND destination=? AND part=? AND status='LEASED' AND lease_token=?
               AND attempt_id=? AND lease_until>?""",
            (report.report_id, report.revision, delivery["destination"], delivery["part"],
             lease_token, attempt_id, self.state.clock()),
        ).fetchone()
        if not row:
            self.db.execute("ROLLBACK")
            raise GatewayError("delivery not found")
        if receipt and receipt.provider_message_id:
            if (
                receipt.destination != row["destination"]
                or receipt.report_id != row["report_id"]
                or receipt.revision != row["revision"]
                or receipt.part != row["part"]
                or receipt.content_hash != row["content_hash"]
                or receipt.attempt_id != attempt_id
            ):
                self.db.execute("ROLLBACK")
                raise GatewayError("delivery receipt mismatch")
            self.db.execute(
                "UPDATE report_deliveries SET status='VERIFIED', receipt_id=?, lease_token=NULL WHERE report_id=? AND revision=? AND destination=? AND part=?",
                (receipt.provider_message_id, report.report_id, report.revision, row["destination"], row["part"]),
            )
            self._audit(report, row["destination"], row["part"], "VERIFIED")
        else:
            self.db.execute(
                "UPDATE report_deliveries SET status='UNKNOWN', last_error=?, lease_token=NULL WHERE report_id=? AND revision=? AND destination=? AND part=?",
                ("ambiguous provider outcome", report.report_id, report.revision, row["destination"], row["part"]),
            )
            self._audit(report, row["destination"], row["part"], "UNKNOWN")
        statuses = self.db.execute(
            "SELECT destination,status FROM report_deliveries WHERE report_id=? AND revision=?",
            (report.report_id, report.revision),
        ).fetchall()
        final = "RECONCILED" if all(item["status"] == "VERIFIED" for item in statuses) else "GENERATED"
        self.db.execute(
            "UPDATE reports SET status=? WHERE report_id=? AND revision=?",
            (final, report.report_id, report.revision),
        )
        self.db.execute("COMMIT")
        return "verified" if receipt else "unknown"

    def blocked(self, report: Report, delivery: Mapping[str, Any], reason: str,
                attempt_id: str, lease_token: str) -> str:
        self.db.execute("BEGIN IMMEDIATE")
        row = self.db.execute(
            """SELECT status FROM report_deliveries WHERE report_id=? AND revision=?
               AND destination=? AND part=? AND status='LEASED' AND lease_token=?
               AND attempt_id=? AND lease_until>?""",
            (report.report_id, report.revision, delivery["destination"], delivery["part"],
             lease_token, attempt_id, self.state.clock()),
        ).fetchone()
        if not row:
            self.db.execute("ROLLBACK")
            raise GatewayError("stale delivery lease")
        self.db.execute(
            """UPDATE report_deliveries SET status='BLOCKED', last_error=?,
               lease_token=NULL WHERE report_id=? AND revision=? AND destination=? AND part=?""",
            (_safe_text(reason, 256), report.report_id, report.revision,
             delivery["destination"], delivery["part"]),
        )
        self._audit(report, delivery["destination"], delivery["part"], "BLOCKED", reason)
        self.db.execute("COMMIT")
        return "blocked"

    def health(self, report_id: str | None = None, revision: int | None = None) -> dict[str, Any]:
        clauses = ""
        args: tuple[Any, ...] = ()
        if report_id is not None and revision is not None:
            clauses = " WHERE report_id=? AND revision=?"
            args = (report_id, revision)
        rows = self.db.execute(
            f"SELECT destination,status,COUNT(*) AS count FROM report_deliveries{clauses} GROUP BY destination,status",
            args,
        ).fetchall()
        stalled = self.db.execute(
            f"""SELECT COUNT(*) AS count FROM report_deliveries
                {clauses + (' AND ' if clauses else ' WHERE ')}
                status='LEASED' AND lease_until<=?""",
            (*args, self.state.clock()),
        ).fetchone()["count"]
        return {
            "deliveries": [
                {"destination": row["destination"], "status": row["status"], "count": row["count"]}
                for row in rows
            ],
            "stalled": stalled,
            "state": "BLOCKED" if stalled or any(row["status"] in {"UNKNOWN", "DEAD", "BLOCKED"} for row in rows)
            else "READY",
        }

    def retry(self, report: Report, delivery: Mapping[str, Any], reason: str = "",
              retry_after: int | None = None) -> str:
        self.db.execute("BEGIN IMMEDIATE")
        row = self.db.execute(
            """SELECT status, attempts, lease_token, lease_until FROM report_deliveries
               WHERE report_id=? AND revision=? AND destination=? AND part=?""",
            (report.report_id, report.revision, delivery["destination"], delivery["part"]),
        ).fetchone()
        if not row or row["status"] != "LEASED" or row["lease_token"] != delivery.get("lease_token") \
                or row["lease_until"] <= self.state.clock():
            self.db.execute("ROLLBACK")
            raise GatewayError("stale delivery lease")
        attempts = row["attempts"]
        status = "DEAD" if attempts >= 5 else "RETRY"
        delay = retry_after if type(retry_after) is int and retry_after >= 0 else min(7200, 2 ** attempts)
        self.db.execute(
            """UPDATE report_deliveries SET status=?, attempts=?, last_error=?,
               next_attempt=?, lease_until=0, lease_token=NULL
               WHERE report_id=? AND revision=? AND destination=? AND part=?""",
            (status, attempts, _safe_text(reason, 256), self.state.clock() + delay,
             report.report_id, report.revision,
             delivery["destination"], delivery["part"]),
        )
        self._audit(report, delivery["destination"], delivery["part"], status, reason)
        self.db.execute("COMMIT")
        return status.lower()


class ReportGateway:
    def __init__(self, store: ReportStore, adapters: Mapping[str, Any]):
        if set(adapters) != set(DESTINATIONS):
            raise GatewayError("both ChatGPT and Telegram adapters are required")
        self.store, self.adapters = store, dict(adapters)

    def ingest(self, raw: Mapping[str, Any]) -> str:
        return self.store.ingest(Report.from_mapping(raw))

    def deliver_one(self, report_id: str, revision: int) -> str:
        report = self.store.report(report_id, revision)
        pending = self.store.pending(report_id, revision)
        if not pending:
            return "complete" if self.store.db.execute(
                "SELECT status FROM reports WHERE report_id=? AND revision=?",
                (report_id, revision),
            ).fetchone()["status"] == "RECONCILED" else "blocked"
        row = self.store.claim(report_id, revision)
        if not row:
            return "blocked"
        try:
            result = self.adapters[row["destination"]].send(
                report_id, revision, row["part"], row["body"], row["content_hash"],
                row["attempt_id"]
            )
            if isinstance(result, DeliveryRetry):
                return self.store.retry(
                    report, row, "provider retry", result.retry_after
                )
            if isinstance(result, DeliveryUnknown):
                return self.store.record(report, row, None, row["attempt_id"], row["lease_token"])
            if isinstance(result, DeliveryBlocked):
                return self.store.blocked(
                    report, row, result.reason, row["attempt_id"], row["lease_token"]
                )
            receipt = result
        except RuntimeError as exc:
            return self.store.blocked(
                report, row, str(exc), row["attempt_id"], row["lease_token"]
            )
        except Exception:
            return self.store.record(report, row, None, row["attempt_id"], row["lease_token"])
        return self.store.record(report, row, receipt, row["attempt_id"], row["lease_token"])
