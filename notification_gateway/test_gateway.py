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
        with self.assertRaises(GatewayError):
            format_telegram_message(huge)
        with self.assertRaises(GatewayError):
            self.gateway.submit({**event(), "unexpected": "field"})
        credential = event(summary='{"password":"synthetic-secret"}')
        self.gateway.submit(credential)
        stored = self.state.db.execute("SELECT payload FROM events").fetchone()[0]
        self.assertNotIn("synthetic-secret", stored)

    def test_equal_sequence_conflicts_and_oversized_events_fail_before_queue(self):
        self.gateway.submit(event())
        with self.assertRaises(GatewayError):
            self.gateway.submit(event(event_id="different"))
        oversized = event(summary="😀" * 3000)
        with self.assertRaises(GatewayError):
            self.gateway.submit(oversized)
        self.assertEqual(
            self.state.db.execute("SELECT COUNT(*) FROM outbox").fetchone()[0], 1
        )

    def test_leased_older_version_is_fenced_before_send(self):
        self.gateway.submit(event())
        item = self.state.claim()
        self.assertIsNotNone(item)
        self.gateway.submit(event(event_id="new", sequence=2))
        with self.assertRaises(GatewayError):
            self.state.record_intent(item, "bounded text")
        self.assertEqual(
            self.state.db.execute(
                "SELECT status FROM outbox WHERE scope_key=?", (item["scope_key"],)
            ).fetchone()[0],
            "SUPERSEDED",
        )

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

    def test_same_event_id_silent_and_actionable_scopes_do_not_cross_join(self):
        silent = event(
            producer="a", event_id="evt-1", business_id="one", severity="INFO",
            owner_action="", sequence=1,
        )
        actionable = event(
            producer="b", event_id="evt-1", business_id="two", severity="OWNER_ACTION",
            sequence=1,
        )
        self.assertEqual(
            Gateway(self.state, {"a", "b"},
                    allowed_repos={"Alphamindsg/alphamind-dashboard"}).submit(silent),
            "silent",
        )
        gateway = Gateway(
            self.state, {"a": "local", "b": "local"},
            allowed_repos={"Alphamindsg/alphamind-dashboard"},
        )
        self.assertEqual(gateway.submit(actionable), "queued")
        self.state.db.execute("UPDATE provider_state SET cooldown_until=0")
        item = self.state.claim()
        self.assertEqual(item["scope_key"], "b|Alphamindsg/alphamind-dashboard|two|evt-1")

    def test_unknown_crash_expiry_receipt_verification_and_reconcile(self):
        transport = FakeTransport([TransportOutcome("unknown")])
        gateway = Gateway(self.state, {"dashboard"}, transport,
                          allowed_repos={"Alphamindsg/alphamind-dashboard"})
        gateway.submit(event(occurred_at="2026-09-08T09:00:00+00:00"))
        self.assertEqual(gateway.process_one(), "unknown")
        self.assertEqual(self.state.health()["state"], "BLOCKED")
        self.assertEqual(
            self.state.reconcile("dashboard|Alphamindsg/alphamind-dashboard|incident-1|evt-1",
                                 ["run-123"], "delivered", "operator-1"),
            "operator_attested",
        )

        self.state.enqueue(NotificationEvent.from_mapping(
            event(event_id="evt-2", business_id="incident-2"),
            frozenset({"dashboard"}), frozenset()
        ))
        self.state.db.execute("UPDATE provider_state SET cooldown_until=0")
        item = self.state.claim()
        self.assertIsNotNone(item)
        self.state.db.execute(
            "UPDATE outbox SET lease_until=0 WHERE scope_key=?",
            ("dashboard|Alphamindsg/alphamind-dashboard|incident-2|evt-2",),
        )
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
