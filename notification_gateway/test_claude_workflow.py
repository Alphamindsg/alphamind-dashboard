import unittest
from pathlib import Path


WORKFLOW = Path(__file__).parents[1] / ".github" / "workflows" / "claude-review.yml"
CHECKOUT_PIN = "actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803"
CLAUDE_PIN = (
    "anthropics/claude-code-action@"
    "a874e9ecd7bb36efdad65429c6b35815f5a08f10"
)


class ClaudeWorkflowContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = WORKFLOW.read_text(encoding="utf-8")

    def test_canonical_pr_trigger_and_same_repo_guard(self):
        self.assertIn("pull_request:", self.text)
        self.assertNotIn("\n  push:", self.text)
        self.assertNotIn("pull_request_target", self.text)
        self.assertIn(
            "github.event.pull_request.head.repo.full_name == github.repository",
            self.text,
        )

    def test_checkout_is_exact_pr_head_and_not_merge_sha(self):
        self.assertIn(f"uses: {CHECKOUT_PIN}", self.text)
        self.assertIn(
            "ref: ${{ github.event.pull_request.head.sha }}",
            self.text,
        )
        self.assertIn("persist-credentials: false", self.text)
        self.assertNotIn("ref: ${{ github.sha }}", self.text)
        self.assertNotIn("ref: ${{ github.event.pull_request.merge_commit_sha }}", self.text)

    def test_pinned_action_provenance_precedes_secret_use(self):
        self.assertIn(f"uses: {CLAUDE_PIN}", self.text)
        provenance = self.text.index("Verify Claude action release provenance")
        oauth = self.text.index("Require Claude OAuth configuration")
        action = self.text.index("Run independent Claude review")
        self.assertLess(provenance, oauth)
        self.assertLess(oauth, action)
        self.assertIn('expected_tag_object="50b26a71effe456d50842a733597491c5636cb6f"', self.text)
        self.assertIn('expected_commit="a874e9ecd7bb36efdad65429c6b35815f5a08f10"', self.text)

    def test_oauth_is_presence_only_and_fail_closed(self):
        self.assertIn("CLAUDE_CODE_OAUTH_TOKEN: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}", self.text)
        self.assertIn('if [ -n "${CLAUDE_CODE_OAUTH_TOKEN:-}" ]', self.text)
        self.assertIn("exit 1", self.text)
        self.assertNotIn("echo \"$CLAUDE_CODE_OAUTH_TOKEN\"", self.text)

    def test_prompt_binds_exact_head_and_requires_terminal_disposition(self):
        self.assertIn("PR NUMBER: ${{ github.event.pull_request.number }}", self.text)
        self.assertIn("EXACT HEAD SHA: ${{ github.event.pull_request.head.sha }}", self.text)
        self.assertIn("PASS, PASS WITH CONDITIONS, or FAIL", self.text)
        self.assertIn('allowed-tools "Bash(gh pr view:*),Bash(gh pr diff:*),Bash(gh pr checks:*)"', self.text)
        self.assertIn("Do not modify repository code, merge, deploy", self.text)


if __name__ == "__main__":
    unittest.main()
