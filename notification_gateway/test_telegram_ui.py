import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from notification_gateway.gateway import Gateway, SQLiteState, TransportOutcome
from notification_gateway.report import REQUIRED_SECTIONS, Report, ReportStore
from notification_gateway.telegram_ui import TelegramInlineMenuService


def event(**overrides):
    value = {
        "event_id": "evt-1",
        "business_id": "incident-1",
        "producer": "dashboard",
        "event_code": "OWNER_BLOCKED",
        "severity": "OWNER_ACTION",
        "summary": "Release is blocked",
        "impact": "The release cannot proceed.",
        "owner_action": "Review the exact head and approve.",
        "provenance": {
            "repo": "Alphamindsg/alphamind-dashboard",
            "head_sha": "b" * 40,
            "pr": 28,
            "run": 12345,
        },
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "sequence": 1,
    }
    value.update(overrides)
    return value


def report(**changes):
    value = {
        "report_id": "report-1",
        "revision": 1,
        "kind": "engineering",
        "scope": "Alphamindsg/alphamind-dashboard",
        "window": "2026-09-23T00:00:00Z/2026-09-23T01:00:00Z",
        "previous_report_id": None,
        "sections": {key: f"{key} details" for key in REQUIRED_SECTIONS},
    }
    value["sections"]["exact_head_evidence"] = "Exact head evidence for sha=" + ("b" * 40)
    value.update(changes)
    return value


class FakeMenuTransport:
    def __init__(self, edit_outcomes=None):
        self.edit_outcomes = list(edit_outcomes or [])
        self.sent = []
        self.edits = []
        self.answers = []
        self.message_id = 100

    def send(self, text, reply_markup=None, chat_id=None):
        self.message_id += 1
        self.sent.append({"text": text, "reply_markup": reply_markup, "chat_id": chat_id})
        return TransportOutcome("sent", self.message_id, str(chat_id), text)

    def edit(self, message_id, text, reply_markup=None, chat_id=None):
        self.edits.append(
            {"message_id": message_id, "text": text, "reply_markup": reply_markup, "chat_id": chat_id}
        )
        if self.edit_outcomes:
            kind = self.edit_outcomes.pop(0)
            if kind == "retry":
                return TransportOutcome("retry", retry_after=5)
            if kind == "rejected":
                return TransportOutcome("rejected")
            if kind == "unknown":
                return TransportOutcome("unknown")
        return TransportOutcome("sent", int(message_id), str(chat_id), text)

    def answer_callback(self, callback_id, text=""):
        self.answers.append({"callback_id": callback_id, "text": text})
        return TransportOutcome("sent")


class TelegramInlineMenuTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.state = SQLiteState(str(Path(self.tempdir.name) / "state.sqlite3"))
        self.gateway = Gateway(
            self.state,
            {"dashboard"},
            allowed_repos={"Alphamindsg/alphamind-dashboard"},
        )
        self.gateway.submit(event())
        self.store = ReportStore(self.state)
        self.store.ingest(Report.from_mapping(report()))
        self.transport = FakeMenuTransport()
        self.service = TelegramInlineMenuService(
            self.state,
            self.store,
            self.transport,
            allowed_chat_id="42",
            allowed_user_ids={"9001"},
        )

    def tearDown(self):
        self.state.close()
        self.tempdir.cleanup()

    def _button_data(self, row, column):
        return self.transport.sent[0]["reply_markup"]["inline_keyboard"][row][column]["callback_data"]

    def test_home_menu_opens_and_authorized_callback_edits_existing_message(self):
        opened = self.service.open_home("9001")
        self.assertEqual(opened["status"], "sent")
        self.assertEqual(len(self.transport.sent), 1)
        owner_action = self._button_data(0, 1)
        result = self.service.handle_callback(owner_action, "42", "9001", opened["message_id"], owner_action)
        self.assertEqual(result["status"], "sent")
        self.assertEqual(result["view"], "owner_action")
        self.assertEqual(len(self.transport.sent), 1)
        self.assertEqual(len(self.transport.edits), 1)
        self.assertIn("Owner Action", self.transport.edits[0]["text"])
        self.assertEqual(self.transport.answers[-1]["text"], "Updated")

    def test_unauthorized_callback_is_rejected_and_audited(self):
        opened = self.service.open_home("9001")
        portfolio = self._button_data(0, 0)
        result = self.service.handle_callback("cb-unauth", "42", "7777", opened["message_id"], portfolio)
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["reason"], "unauthorized")
        row = self.state.db.execute(
            "SELECT outcome FROM telegram_menu_callbacks WHERE callback_id='cb-unauth'"
        ).fetchone()
        self.assertEqual(row["outcome"], "rejected")

    def test_duplicate_taps_are_idempotent_and_stale_revision_is_rejected(self):
        opened = self.service.open_home("9001")
        owner_action = self._button_data(0, 1)
        first = self.service.handle_callback("cb-1", "42", "9001", opened["message_id"], owner_action)
        duplicate = self.service.handle_callback("cb-1", "42", "9001", opened["message_id"], owner_action)
        stale = self.service.handle_callback("cb-2", "42", "9001", opened["message_id"], owner_action)
        self.assertEqual(first["status"], "sent")
        self.assertEqual(duplicate["status"], "sent")
        self.assertEqual(stale["status"], "stale")
        self.assertEqual(stale["reason"], "stale-revision")
        self.assertEqual(len(self.transport.edits), 1)
        self.assertEqual(self.transport.answers[-1]["text"], "stale-revision")

    def test_stale_exact_head_evidence_is_flagged(self):
        opened = self.service.open_home("9001", {"Alphamindsg/alphamind-dashboard": "c" * 40})
        repositories = self._button_data(2, 0)
        repos = self.service.handle_callback("cb-repos", "42", "9001", opened["message_id"], repositories)
        self.assertEqual(repos["status"], "sent")
        repo_button = self.transport.edits[-1]["reply_markup"]["inline_keyboard"][0][0]["callback_data"]
        overview = self.service.handle_callback("cb-repo", "42", "9001", opened["message_id"], repo_button)
        self.assertEqual(overview["status"], "sent")
        evidence = self.transport.edits[-1]["reply_markup"]["inline_keyboard"][3][0]["callback_data"]
        result = self.service.handle_callback("cb-evidence", "42", "9001", opened["message_id"], evidence)
        self.assertEqual(result["status"], "sent")
        self.assertIn("STALE EXACT-HEAD EVIDENCE", self.transport.edits[-1]["text"])

    def test_retry_result_does_not_advance_session_and_restart_can_recover(self):
        opened = self.service.open_home("9001")
        owner_action = self._button_data(0, 1)
        retry_transport = FakeMenuTransport(edit_outcomes=["retry"])
        retry_service = TelegramInlineMenuService(
            self.state,
            self.store,
            retry_transport,
            allowed_chat_id="42",
            allowed_user_ids={"9001"},
        )
        retry = retry_service.handle_callback("cb-retry", "42", "9001", opened["message_id"], owner_action)
        self.assertEqual(retry["status"], "retry")
        revision = self.state.db.execute(
            "SELECT revision FROM telegram_menu_sessions"
        ).fetchone()["revision"]
        self.assertEqual(revision, 1)

        recovered_transport = FakeMenuTransport()
        recovered_service = TelegramInlineMenuService(
            self.state,
            self.store,
            recovered_transport,
            allowed_chat_id="42",
            allowed_user_ids={"9001"},
        )
        recovered = recovered_service.handle_callback("cb-recovered", "42", "9001", opened["message_id"], owner_action)
        self.assertEqual(recovered["status"], "sent")
        self.assertEqual(recovered["view"], "owner_action")
        self.assertEqual(
            self.state.db.execute("SELECT revision FROM telegram_menu_sessions").fetchone()["revision"],
            2,
        )

    def test_rate_limit_and_audit_survive_restart(self):
        opened = self.service.open_home("9001")
        limited_service = TelegramInlineMenuService(
            self.state,
            self.store,
            self.transport,
            allowed_chat_id="42",
            allowed_user_ids={"9001"},
            callback_limit=1,
        )
        first = self._button_data(0, 0)
        second = self._button_data(0, 1)
        self.assertEqual(
            limited_service.handle_callback("cb-first", "42", "9001", opened["message_id"], first)["status"],
            "sent",
        )
        second = self.transport.edits[-1]["reply_markup"]["inline_keyboard"][0][1]["callback_data"]
        limited = limited_service.handle_callback("cb-second", "42", "9001", opened["message_id"], second)
        self.assertEqual(limited["status"], "rate_limited")
        audit_count = self.state.db.execute(
            "SELECT COUNT(*) FROM telegram_menu_audit"
        ).fetchone()[0]
        callback_count = self.state.db.execute(
            "SELECT COUNT(*) FROM telegram_menu_callbacks"
        ).fetchone()[0]
        self.assertGreaterEqual(audit_count, 2)
        self.assertEqual(callback_count, 2)


if __name__ == "__main__":
    unittest.main()
