import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from notification_gateway.gateway import (
    DirectTelegramTransport,
    Gateway,
    GatewayError,
    NotificationEvent,
    SQLiteState,
    TransportOutcome,
    format_telegram_message,
)


def event(**overrides):
    value = {
        "event_id": "evt-1",
        "business_id": "incident-1",
        "producer": "dashboard",
        "event_code": "OWNER_BLOCKED",
        "severity": "OWNER_ACTION",
        "summary": "Release is blocked token=do-not-store https://bad.example",
        "impact": "The release cannot proceed.",
        "owner_action": "Review the exact head and approve.",
        "provenance": {
            "repo": "Alphamindsg/alphamind-dashboard",
            "head_sha": "b" * 40,
            "pr": 26,
            "issue": 26,
            "run": 123,
        },
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "sequence": 1,
    }
    value.update(overrides)
    return value


class FakeTransport:
    def __init__(self, outcomes):
        self.outcomes = iter(outcomes)
        self.calls = []

    def send(self, text):
        self.calls.append(text)
        return next(self.outcomes)


class Response:
    def __init__(self, body):
        self.body = json.dumps(body).encode()

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass


class GatewayTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.path = str(Path(self.tempdir.name) / "state.sqlite3")
        self.state = SQLiteState(self.path)
        self.gateway = Gateway(
            self.state, {"dashboard"}, allowed_repos={"Alphamindsg/alphamind-dashboard"}
        )

    def tearDown(self):
        self.state.close()
        self.tempdir.cleanup()

    def test_closed_schema_redaction_policy_and_utf16_bound(self):
        parsed = NotificationEvent.from_mapping(event(), frozenset({"dashboard"}))
        self.assertTrue(parsed.should_notify())
        self.assertNotIn("do-not-store", parsed.summary)
        self.assertNotIn("https://", parsed.summary)
        huge = NotificationEvent(
            "long", "dashboard", "OWNER_BLOCKED", "OWNER_ACTION",
            "😀" * 3000, "impact", "action",
            {"repo": "Alphamindsg/alphamind-dashboard", "head_sha": "b" * 40},
            event()["occurred_at"],
        )
        self.assertLessEqual(len(format_telegram_message(huge).encode("utf-16-le")) // 2, 4096)
        with self.assertRaises(GatewayError):
            self.gateway.submit({**event(), "unexpected": "field"})

    def test_scoped_dedup_conflict_stale_and_concurrent_connections(self):
        fixed = event(occurred_at="2026-09-08T09:00:00+00:00")
        self.assertEqual(self.gateway.submit(fixed), "queued")
        self.assertEqual(self.gateway.submit(fixed), "duplicate")
        with self.assertRaises(GatewayError):
            self.gateway.submit(event(summary="different"))
        with self.assertRaises(GatewayError):
            self.gateway.submit(event(event_id="old", sequence=0))
        other = SQLiteState(self.path)
        try:
            self.assertEqual(
                Gateway(other, {"dashboard"},
                        allowed_repos={"Alphamindsg/alphamind-dashboard"}).submit(
                            event(event_id="same", business_id="incident-2")
                        ),
                "queued",
            )
        finally:
            other.close()

    def test_unknown_crash_expiry_receipt_verification_and_reconcile(self):
        transport = FakeTransport([TransportOutcome("unknown")])
        gateway = Gateway(self.state, {"dashboard"}, transport,
                          allowed_repos={"Alphamindsg/alphamind-dashboard"})
        gateway.submit(event(occurred_at="2026-09-08T09:00:00+00:00"))
        self.assertEqual(gateway.process_one(), "unknown")
        self.assertEqual(self.state.health()["state"], "BLOCKED")
        self.assertEqual(self.state.reconcile("evt-1", ["run-123"], "delivered"), "reconciled")

        self.state.enqueue(NotificationEvent.from_mapping(
            event(event_id="evt-2", business_id="incident-2"),
            frozenset({"dashboard"}), frozenset()
        ))
        item = self.state.claim()
        self.assertIsNotNone(item)
        self.state.db.execute("UPDATE outbox SET lease_until=0 WHERE event_id='evt-2'")
        self.assertEqual(self.state.recover_expired(), 1)
        self.assertEqual(self.state.health()["state"], "BLOCKED")

    def test_retry_cooldown_and_verified_receipt(self):
        text_holder = {}

        class ValidTransport:
            def send(self, text):
                text_holder["text"] = text
                return TransportOutcome("sent", 9, "42", text)

        gateway = Gateway(self.state, {"dashboard"}, ValidTransport(),
                          allowed_repos={"Alphamindsg/alphamind-dashboard"})
        gateway.submit(event())
        self.assertEqual(gateway.process_one(), "verified")
        self.assertEqual(self.state.db.execute("SELECT COUNT(*) FROM receipts").fetchone()[0], 1)

        retry_state = SQLiteState(str(Path(self.tempdir.name) / "retry.sqlite3"))
        retry_gateway = Gateway(
            retry_state, {"dashboard"},
            FakeTransport([TransportOutcome("retry", retry_after=7200)]),
            allowed_repos={"Alphamindsg/alphamind-dashboard"},
        )
        retry_gateway.submit(event(event_id="retry", business_id="retry"))
        self.assertEqual(retry_gateway.process_one(), "retry")
        self.assertGreaterEqual(
            retry_state.db.execute(
                "SELECT cooldown_until FROM provider_state"
            ).fetchone()[0],
            retry_state.clock() + 7199,
        )
        retry_state.close()

    def test_transport_rejects_malformed_success_and_bad_producer(self):
        def opener(*_args, **_kwargs):
            return Response({"ok": True})

        outcome = DirectTelegramTransport("synthetic-token", "42", opener).send("hello")
        self.assertEqual(outcome.kind, "unknown")
        with self.assertRaises(GatewayError):
            self.gateway.submit(event(producer="untrusted"))
        with self.assertRaises(GatewayError):
            self.gateway.submit(event(provenance={"repo": "evil/repo", "head_sha": "b" * 40}))


if __name__ == "__main__":
    unittest.main()
