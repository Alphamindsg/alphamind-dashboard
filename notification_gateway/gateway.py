"""Bounded, durable notification gateway with Direct Telegram as its primary provider.

This module uses only the Python standard library and has no browser-facing API.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import re
import sqlite3
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Mapping

MAX_TELEGRAM_LENGTH = 4096
SEVERITIES = frozenset({"INFO", "WARNING", "OWNER_ACTION", "CRITICAL"})
PROVENANCE_KEYS = ("repo", "head_sha", "pr", "issue", "run")
SHA_RE = re.compile(r"^[0-9a-f]{40}$", re.I)
REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
SECRET_RE = re.compile(
    r"(?i)(bearer\s+|token\s*[:=]\s*|password\s*[:=]\s*|"
    r"secret\s*[:=]\s*|api[_ -]?key\s*[:=]\s*)[^\s,;]+"
)
URL_RE = re.compile(r"https?://\S+")


class GatewayError(ValueError):
    """An event or state transition was rejected."""


def redact(value: Any) -> Any:
    """Return a JSON-safe value with common credentials and URLs removed."""
    if isinstance(value, Mapping):
        return {str(k): redact(v) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    if isinstance(value, tuple):
        return [redact(v) for v in value]
    if isinstance(value, str):
        return URL_RE.sub("[URL REDACTED]", SECRET_RE.sub(r"\1[REDACTED]", value))
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

    @classmethod
    def from_mapping(
        cls, raw: Mapping[str, Any], trusted_producers: frozenset[str]
    ) -> "NotificationEvent":
        if not isinstance(raw, Mapping):
            raise GatewayError("event must be an object")
        required = (
            "event_id", "producer", "event_code", "severity", "summary",
            "impact", "owner_action", "provenance", "occurred_at",
        )
        if any(key not in raw for key in required):
            raise GatewayError("event schema is incomplete")
        producer = str(raw["producer"])
        if producer not in trusted_producers:
            raise GatewayError("producer is not trusted")
        severity = str(raw["severity"]).upper()
        if severity not in SEVERITIES:
            raise GatewayError("invalid severity")
        event_id = str(raw["event_id"])
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}", event_id):
            raise GatewayError("invalid event_id")
        event_code = str(raw["event_code"])
        if not re.fullmatch(r"[A-Z0-9][A-Z0-9_.-]{1,63}", event_code):
            raise GatewayError("invalid event_code")
        provenance = raw["provenance"]
        if not isinstance(provenance, Mapping):
            raise GatewayError("provenance must be an object")
        if set(provenance) - set(PROVENANCE_KEYS):
            raise GatewayError("provenance contains unsupported fields")
        if not REPO_RE.fullmatch(str(provenance.get("repo", ""))):
            raise GatewayError("provenance repo is invalid")
        if not SHA_RE.fullmatch(str(provenance.get("head_sha", ""))):
            raise GatewayError("provenance head_sha is invalid")
        for key in ("pr", "issue", "run"):
            if key in provenance and (
                not isinstance(provenance[key], int) or provenance[key] < 1
            ):
                raise GatewayError("provenance references must be positive integers")
        for field in ("summary", "impact", "owner_action"):
            if not isinstance(raw[field], str) or len(raw[field]) > 1000:
                raise GatewayError(f"{field} is invalid")
        try:
            datetime.fromisoformat(str(raw["occurred_at"]).replace("Z", "+00:00"))
        except ValueError as exc:
            raise GatewayError("occurred_at must be ISO-8601") from exc
        sequence = raw.get("sequence", 0)
        if not isinstance(sequence, int) or sequence < 0:
            raise GatewayError("sequence is invalid")
        return cls(
            event_id=event_id,
            producer=producer,
            event_code=event_code,
            severity=severity,
            summary=redact(raw["summary"]),
            impact=redact(raw["impact"]),
            owner_action=redact(raw["owner_action"]),
            provenance=dict(provenance),
            occurred_at=str(raw["occurred_at"]),
            sequence=sequence,
        )

    def should_notify(self) -> bool:
        return self.severity in {"OWNER_ACTION", "CRITICAL"} or (
            self.severity in {"INFO", "WARNING"} and bool(self.owner_action.strip())
        )

    def canonical(self) -> str:
        return json.dumps(self.__dict__, sort_keys=True, separators=(",", ":"))


def format_telegram_message(event: NotificationEvent) -> str:
    """Produce bounded plaintext; no producer-controlled links or markup."""
    provenance = " ".join(
        f"{key}={event.provenance[key]}" for key in PROVENANCE_KEYS
        if key in event.provenance
    )
    text = (
        f"[{event.severity}] {event.event_code}\n"
        f"What happened: {event.summary}\n"
        f"Impact: {event.impact}\n"
        f"Minimum owner action: {event.owner_action or 'No action required'}\n"
        f"Provenance: {provenance}"
    )
    if len(text) <= MAX_TELEGRAM_LENGTH:
        return text
    return text[: MAX_TELEGRAM_LENGTH - 1] + "…"


class SQLiteState:
    """Transactional event/outbox state with idempotency and monotonic fencing."""

    def __init__(self, path: str):
        self.path = path
        self.db = sqlite3.connect(path, timeout=5, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS events (
              event_id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, payload TEXT NOT NULL,
              producer TEXT NOT NULL, sequence INTEGER NOT NULL, status TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS outbox (
              event_id TEXT PRIMARY KEY REFERENCES events(event_id), attempts INTEGER NOT NULL,
              next_attempt REAL NOT NULL, lease_until REAL NOT NULL DEFAULT 0,
              lease_token TEXT, status TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS dead_letters (
              event_id TEXT PRIMARY KEY, reason TEXT NOT NULL, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS provider_state (
              name TEXT PRIMARY KEY, cooldown_until REAL NOT NULL DEFAULT 0
            );
            """
        )

    def enqueue(self, event: NotificationEvent) -> str:
        fingerprint = hashlib.sha256(event.canonical().encode()).hexdigest()
        now = datetime.now(timezone.utc).isoformat()
        self.db.execute("BEGIN IMMEDIATE")
        try:
            existing = self.db.execute(
                "SELECT fingerprint FROM events WHERE event_id=?", (event.event_id,)
            ).fetchone()
            if existing:
                if existing["fingerprint"] != fingerprint:
                    raise GatewayError("duplicate event_id has conflicting content")
                self.db.execute("COMMIT")
                return "duplicate"
            latest = self.db.execute(
                "SELECT MAX(sequence) AS latest FROM events WHERE producer=?",
                (event.producer,),
            ).fetchone()["latest"]
            if latest is not None and event.sequence < latest:
                raise GatewayError("stale or out-of-order event")
            self.db.execute(
                "INSERT INTO events VALUES (?, ?, ?, ?, ?, ?, ?)",
                (event.event_id, fingerprint, event.canonical(), event.producer,
                 event.sequence, "QUEUED" if event.should_notify() else "SILENT", now),
            )
            if event.should_notify():
                self.db.execute(
                    "INSERT INTO outbox VALUES (?, 0, ?, 0, NULL, 'READY')",
                    (event.event_id, time.time()),
                )
            self.db.execute("COMMIT")
            return "queued" if event.should_notify() else "silent"
        except Exception:
            self.db.execute("ROLLBACK")
            raise

    def claim(self, lease_seconds: int = 60) -> sqlite3.Row | None:
        now = time.time()
        token = str(uuid.uuid4())
        self.db.execute("BEGIN IMMEDIATE")
        cooldown = self.db.execute(
            "SELECT cooldown_until FROM provider_state WHERE name='telegram'"
        ).fetchone()
        if cooldown and cooldown["cooldown_until"] > now:
            self.db.execute("COMMIT")
            return None
        row = self.db.execute(
            """SELECT o.event_id, o.attempts, e.payload FROM outbox o JOIN events e
               ON e.event_id=o.event_id
               WHERE o.status='READY' AND o.next_attempt<=? AND o.lease_until<=?
               ORDER BY o.next_attempt, o.event_id LIMIT 1""", (now, now)
        ).fetchone()
        if not row:
            self.db.execute("COMMIT")
            return None
        self.db.execute(
            "UPDATE outbox SET lease_until=?, lease_token=?, status='LEASED' WHERE event_id=?",
            (now + lease_seconds, token, row["event_id"]),
        )
        self.db.execute("COMMIT")
        return {"event_id": row["event_id"], "attempts": row["attempts"],
                "payload": row["payload"], "lease_token": token}

    def cooldown(self, seconds: int) -> None:
        self.db.execute(
            """INSERT INTO provider_state(name, cooldown_until) VALUES ('telegram', ?)
               ON CONFLICT(name) DO UPDATE SET cooldown_until=excluded.cooldown_until""",
            (time.time() + max(0, min(seconds, 3600)),),
        )

    def finish(self, event_id: str, lease_token: str, outcome: str, reason: str = "") -> None:
        self.db.execute("BEGIN IMMEDIATE")
        row = self.db.execute(
            "SELECT attempts FROM outbox WHERE event_id=? AND lease_token=? AND status='LEASED'",
            (event_id, lease_token),
        ).fetchone()
        if not row:
            self.db.execute("ROLLBACK")
            raise GatewayError("stale lease")
        attempts = row["attempts"] + 1
        if outcome == "sent":
            self.db.execute("UPDATE outbox SET status='VERIFIED', attempts=? WHERE event_id=?",
                            (attempts, event_id))
            self.db.execute("UPDATE events SET status='VERIFIED' WHERE event_id=?", (event_id,))
        elif outcome == "unknown":
            self.db.execute("UPDATE outbox SET status='UNKNOWN', attempts=? WHERE event_id=?",
                            (attempts, event_id))
            self.db.execute("UPDATE events SET status='UNKNOWN' WHERE event_id=?", (event_id,))
        elif outcome == "dead":
            self.db.execute("UPDATE outbox SET status='DEAD', attempts=? WHERE event_id=?",
                            (attempts, event_id))
            self.db.execute("UPDATE events SET status='DEAD' WHERE event_id=?", (event_id,))
            self.db.execute("INSERT OR REPLACE INTO dead_letters VALUES (?, ?, ?)",
                            (event_id, redact(reason), datetime.now(timezone.utc).isoformat()))
        else:
            delay = min(3600, 2 ** min(attempts, 10)) + random.random()
            self.db.execute(
                "UPDATE outbox SET status='READY', attempts=?, next_attempt=?, lease_token=NULL WHERE event_id=?",
                (attempts, time.time() + delay, event_id),
            )
        self.db.execute("COMMIT")

    def health(self) -> dict[str, Any]:
        rows = self.db.execute("SELECT status, COUNT(*) AS count FROM outbox GROUP BY status").fetchall()
        counts = {row["status"]: row["count"] for row in rows}
        return {"queue": counts, "dead_letters": counts.get("DEAD", 0),
                "state": "BLOCKED" if counts.get("UNKNOWN") else ("PAUSED" if counts.get("DEAD") else "READY")}


class DirectTelegramTransport:
    def __init__(self, token: str, chat_id: str, opener: Callable[..., Any] = urllib.request.urlopen):
        if not token or not chat_id:
            raise GatewayError("Telegram configuration is incomplete")
        self.token, self.chat_id, self.opener = token, chat_id, opener

    def send(self, text: str) -> tuple[str, int | None]:
        request = urllib.request.Request(
            f"https://api.telegram.org/bot{self.token}/sendMessage",
            data=json.dumps({"chat_id": self.chat_id, "text": text}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with self.opener(request, timeout=10) as response:
                body = json.loads(response.read().decode("utf-8"))
                if body.get("ok") is True:
                    return "sent", None
                retry = body.get("parameters", {}).get("retry_after")
                return "retry", retry if isinstance(retry, int) else None
        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                try:
                    body = json.loads(exc.read().decode("utf-8"))
                    retry = body.get("parameters", {}).get("retry_after")
                    return "retry", retry if isinstance(retry, int) else None
                except (ValueError, KeyError, TypeError):
                    return "retry", None
            raise GatewayError("Telegram transport error") from None
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            raise GatewayError("Telegram transport outcome is unknown") from None


class Gateway:
    def __init__(self, state: SQLiteState, trusted_producers: set[str], transport: Any = None):
        self.state = state
        self.trusted_producers = frozenset(trusted_producers)
        self.transport = transport

    def submit(self, raw: Mapping[str, Any]) -> str:
        return self.state.enqueue(NotificationEvent.from_mapping(raw, self.trusted_producers))

    def process_one(self, max_attempts: int = 5) -> str:
        item = self.state.claim()
        if not item:
            return "empty"
        event = NotificationEvent(**json.loads(item["payload"]))
        if not self.transport:
            self.state.finish(item["event_id"], item["lease_token"], "dead", "provider disabled")
            return "dead"
        try:
            result, retry_after = self.transport.send(format_telegram_message(event))
            if result == "sent":
                self.state.finish(item["event_id"], item["lease_token"], "sent")
                return "sent"
            if item["attempts"] + 1 >= max_attempts:
                self.state.finish(item["event_id"], item["lease_token"], "dead", "retry budget exhausted")
                return "dead"
            if retry_after is not None:
                self.state.cooldown(retry_after)
            self.state.finish(item["event_id"], item["lease_token"], "retry")
            return "retry"
        except GatewayError as exc:
            if "unknown" in str(exc).lower():
                self.state.finish(item["event_id"], item["lease_token"], "unknown", str(exc))
                return "unknown"
            if item["attempts"] + 1 >= max_attempts:
                self.state.finish(item["event_id"], item["lease_token"], "dead", str(exc))
                return "dead"
            self.state.finish(item["event_id"], item["lease_token"], "retry", str(exc))
            return "retry"


def doctor() -> dict[str, bool]:
    return {
        "ALPHAMIND_TELEGRAM_BOT_TOKEN": bool(os.getenv("ALPHAMIND_TELEGRAM_BOT_TOKEN")),
        "ALPHAMIND_TELEGRAM_CHAT_ID": bool(os.getenv("ALPHAMIND_TELEGRAM_CHAT_ID")),
        "ALPHAMIND_NOTIFICATION_STATE": bool(os.getenv("ALPHAMIND_NOTIFICATION_STATE")),
    }
