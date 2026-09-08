import json
import tempfile
import unittest
from pathlib import Path

from notification_gateway.gateway import (
    Gateway,
    GatewayError,
    NotificationEvent,
    SQLiteState,
    format_telegram_message,
)


def event(**overrides):
    value = {
        "event_id": "evt-1",
        "producer": "dashboard",
        "event_code": "OWNER_BLOCKED",
        "severity": "OWNER_ACTION",
        "summary": "A deploy is blocked token=do-not-store https://bad.example",
        "impact": "The release cannot proceed.",
        "owner_action": "Review the exact head and approve.",
        "provenance": {
            "repo": "Alphamindsg/alphamind-dashboard",
            "head_sha": "b" * 40,
            "pr": 26,
            "issue": 26,
            "run": 123,
        },
        "occurred_at": "2026-09-08T09:00:00+00:00",
        "sequence": 1,
    }
    value.update(overrides)
    return value


class GatewayTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.state = SQLiteState(str(Path(self.tempdir.name) / "state.sqlite3"))
        self.gateway = Gateway(self.state, {"dashboard"})

    def tearDown(self):
        self.tempdir.cleanup()

    def test_validation_policy_redaction_and_bounded_plaintext(self):
        parsed = NotificationEvent.from_mapping(event(), frozenset({"dashboard"}))
        self.assertTrue(parsed.should_notify())
        self.assertNotIn("do-not-store", parsed.summary)
        self.assertNotIn("https://", parsed.summary)
        self.assertLessEqual(len(format_telegram_message(parsed)), 4096)
        self.assertEqual(self.gateway.submit(event()), "queued")
        self.assertEqual(self.gateway.submit(event()), "duplicate")
        with self.assertRaises(GatewayError):
            self.gateway.submit(event(summary="different"))

    def test_silent_and_stale_events(self):
        quiet = event(event_id="quiet", severity="INFO", owner_action="")
        self.assertEqual(self.gateway.submit(quiet), "silent")
        with self.assertRaises(GatewayError):
            self.gateway.submit(event(event_id="old", sequence=0))

    def test_unknown_is_quarantined_and_not_resent(self):
        class TimeoutTransport:
            def send(self, _text):
                raise GatewayError("Telegram transport outcome is unknown")

        gateway = Gateway(self.state, {"dashboard"}, TimeoutTransport())
        gateway.submit(event())
        self.assertEqual(gateway.process_one(), "unknown")
        self.assertIsNone(self.state.claim())
        self.assertEqual(self.state.health()["state"], "BLOCKED")

    def test_retry_then_verify_and_invalid_producer(self):
        class RetryTransport:
            def __init__(self):
                self.calls = 0

            def send(self, _text):
                self.calls += 1
                return ("retry", 1) if self.calls == 1 else ("sent", None)

        transport = RetryTransport()
        gateway = Gateway(self.state, {"dashboard"}, transport)
        with self.assertRaises(GatewayError):
            gateway.submit(event(producer="untrusted"))
        gateway.submit(event())
        self.assertEqual(gateway.process_one(), "retry")
        self.state.db.execute("UPDATE outbox SET next_attempt=0")
        self.assertEqual(gateway.process_one(), "sent")
        self.assertEqual(self.state.health()["queue"]["VERIFIED"], 1)

    def test_malformed_provenance_rejected(self):
        with self.assertRaises(GatewayError):
            NotificationEvent.from_mapping(
                event(provenance={"repo": "https://evil.example", "head_sha": "b" * 40}),
                frozenset({"dashboard"}),
            )


if __name__ == "__main__":
    unittest.main()
