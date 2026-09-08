import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from notification_gateway.adapters import LocalHandoffAdapter, OfflineReportAdapter
from notification_gateway.gateway import GatewayError, SQLiteState
from notification_gateway.report import (
    DeliveryRetry,
    REQUIRED_SECTIONS,
    Report,
    ReportGateway,
    ReportStore,
)


def report(**changes):
    value = {
        "report_id": "report-1",
        "revision": 1,
        "kind": "engineering",
        "scope": "synthetic/repository",
        "window": "2026-09-08T09:00Z/2026-09-08T10:00Z",
        "previous_report_id": None,
        "sections": {key: f"{key} details" for key in REQUIRED_SECTIONS},
    }
    value.update(changes)
    return value


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.state = SQLiteState(str(Path(self.tempdir.name) / "state.sqlite3"))
        self.store = ReportStore(self.state)

    def tearDown(self):
        self.state.close()
        self.tempdir.cleanup()

    def gateway(self, chat=True, telegram=True):
        return ReportGateway(
            self.store,
            {
                "chatgpt": OfflineReportAdapter("chatgpt", chat),
                "telegram": OfflineReportAdapter("telegram", telegram),
            },
        )

    def test_generation_is_not_delivery_and_both_receipts_reconcile(self):
        gateway = self.gateway()
        self.assertEqual(gateway.ingest(report()), "generated")
        self.assertEqual(
            self.store.db.execute("SELECT status FROM reports").fetchone()[0], "GENERATED"
        )
        self.assertEqual(gateway.deliver_one("report-1", 1), "verified")
        self.assertEqual(
            self.store.db.execute("SELECT status FROM reports").fetchone()[0], "GENERATED"
        )
        self.assertEqual(gateway.deliver_one("report-1", 1), "verified")
        self.assertEqual(
            self.store.db.execute("SELECT status FROM reports").fetchone()[0], "RECONCILED"
        )

    def test_duplicate_conflict_revision_delta_and_required_sections(self):
        gateway = self.gateway()
        self.assertEqual(gateway.ingest(report()), "generated")
        self.assertEqual(gateway.ingest(report()), "duplicate")
        with self.assertRaises(GatewayError):
            gateway.ingest(report(sections={**report()["sections"], "status": "changed"}))
        self.assertEqual(
            gateway.ingest(report(revision=2, previous_report_id="report-1")), "generated"
        )
        with self.assertRaises(GatewayError):
            gateway.ingest(report(report_id="missing", sections={"status": "only"}))

    def test_telegram_failure_preserves_chatgpt_and_unknown_is_not_retried(self):
        gateway = self.gateway(telegram=False)
        gateway.ingest(report())
        self.assertEqual(gateway.deliver_one("report-1", 1), "verified")
        self.assertEqual(gateway.deliver_one("report-1", 1), "blocked")
        self.assertEqual(
            self.store.db.execute(
                "SELECT status FROM report_deliveries WHERE destination='telegram'"
            ).fetchone()[0],
            "BLOCKED",
        )
        self.assertEqual(
            self.store.db.execute(
                "SELECT status FROM report_deliveries WHERE destination='chatgpt'"
            ).fetchone()[0],
            "VERIFIED",
        )

    def test_chatgpt_failure_preserves_telegram_and_retry_is_independent(self):
        gateway = self.gateway(chat=False)
        gateway.ingest(report(priority="urgent"))
        self.assertEqual(gateway.deliver_one("report-1", 1), "blocked")
        # The other destination remains independently deliverable.
        self.assertEqual(gateway.deliver_one("report-1", 1), "verified")
        self.assertEqual(
            self.store.db.execute(
                "SELECT status FROM report_deliveries WHERE destination='telegram'"
            ).fetchone()[0],
            "VERIFIED",
        )

        retry_adapter = OfflineReportAdapter("chatgpt")
        retry_adapter.send = lambda *_args: DeliveryRetry(7200)
        retry_store = ReportStore(self.state)
        retry_gateway = ReportGateway(
            retry_store, {"chatgpt": retry_adapter, "telegram": OfflineReportAdapter("telegram")}
        )
        retry_gateway.ingest(report(report_id="retry-report"))
        self.assertEqual(retry_gateway.deliver_one("retry-report", 1), "retry")
        self.assertEqual(
            self.state.db.execute(
                "SELECT status FROM report_deliveries WHERE report_id='retry-report' AND destination='chatgpt'"
            ).fetchone()[0],
            "RETRY",
        )

    def test_receipt_mismatch_and_local_handoff_are_not_success(self):
        gateway = self.gateway()
        gateway.ingest(report())
        row = self.store.claim("report-1", 1)
        self.assertIsNotNone(row)
        with self.assertRaises(GatewayError):
            self.store.record(
                Report.from_mapping(report()), row,
                self.gateway().adapters["chatgpt"].send(
                    "wrong", 1, row["part"], row["body"], row["content_hash"], row["attempt_id"]
                ),
                row["attempt_id"], row["lease_token"],
            )
        self.assertEqual(
            LocalHandoffAdapter().send("report-1", 1, 0, "body", "digest").reason,
            "operator/platform confirmation is required",
        )

    def test_unicode_chunking_retains_all_sections(self):
        raw = report()
        raw["sections"]["changes_since_previous"] = "😀" * 2000
        parsed = Report.from_mapping(raw)
        parts = parsed.telegram_parts()
        joined = "\n".join(parts)
        self.assertIn("CHANGES SINCE PREVIOUS", joined)
        self.assertIn("OWNER ACTIONS", joined)
        self.assertTrue(all(len(part.encode("utf-16-le")) // 2 <= 4096 for part in parts))


if __name__ == "__main__":
    unittest.main()
