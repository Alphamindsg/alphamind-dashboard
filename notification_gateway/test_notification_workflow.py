import unittest
from pathlib import Path


WORKFLOW = Path(__file__).parents[1] / ".github" / "workflows" / "notification-gateway.yml"
CHECKOUT_PIN = "actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683"
REQUIRED_PATHS = (
    ".github/workflows/notification-gateway.yml",
    "telegram-gateway-regression-checks.py",
    "notification_gateway/__init__.py",
    "notification_gateway/__main__.py",
    "notification_gateway/adapters.py",
    "notification_gateway/gateway.py",
    "notification_gateway/report.py",
    "notification_gateway/test_gateway.py",
    "notification_gateway/test_report.py",
    "notification_gateway/test_claude_workflow.py",
    "notification_gateway/test_notification_workflow.py",
)


class NotificationWorkflowContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = WORKFLOW.read_text(encoding="utf-8")

    def test_exact_head_checkout_and_no_persisted_credentials(self):
        self.assertIn(f"uses: {CHECKOUT_PIN}", self.text)
        self.assertIn(
            "ref: ${{ github.event_name == 'pull_request' && github.event.pull_request.head.sha || github.sha }}",
            self.text,
        )
        self.assertIn("persist-credentials: false", self.text)

    def test_required_artifact_guard_precedes_offline_checks(self):
        guard = self.text.index("Verify required notification artifacts")
        offline = self.text.index("Run offline checks")
        self.assertLess(guard, offline)
        self.assertIn("set -euo pipefail", self.text)
        self.assertIn("echo \"::error::Missing required notification artifact: $path\"", self.text)
        self.assertIn("echo \"::error::Missing required Python sources under notification_gateway/\"", self.text)
        for path in REQUIRED_PATHS:
            self.assertIn(f'"{path}"', self.text)

    def test_offline_checks_cover_all_required_contract_tests(self):
        self.assertIn("python3 -m py_compile notification_gateway/*.py", self.text)
        self.assertIn("python3 -m unittest notification_gateway.test_gateway", self.text)
        self.assertIn("python3 -m unittest notification_gateway.test_report", self.text)
        self.assertIn("python3 -m unittest notification_gateway.test_claude_workflow", self.text)
        self.assertIn("python3 -m unittest notification_gateway.test_notification_workflow", self.text)
        self.assertIn("python3 telegram-gateway-regression-checks.py", self.text)
        self.assertNotIn("continue-on-error: true", self.text)


if __name__ == "__main__":
    unittest.main()
