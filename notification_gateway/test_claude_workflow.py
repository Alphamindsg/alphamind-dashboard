import unittest
from pathlib import Path


WORKFLOW = Path(__file__).parents[1] / ".github" / "workflows" / "claude-review.yml"


class ClaudeWorkflowContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = WORKFLOW.read_text(encoding="utf-8")

    def test_push_path_is_narrow_and_exact_head_bound(self):
        self.assertIn("push:", self.text)
        self.assertIn("copilot/notify-001-shared-telegram-gateway", self.text)
        self.assertIn("gh pr list --repo", self.text)
        self.assertIn('test "${#candidates[@]}" -eq 1', self.text)
        self.assertIn('test "$candidate_sha" = "$PUSH_SHA"', self.text)
        self.assertIn('test "$(git rev-parse HEAD)" = "$EXPECTED_SHA"', self.text)

    def test_pull_request_path_is_same_repo_only(self):
        self.assertIn("github.event.pull_request.head.repo.full_name == github.repository", self.text)
        self.assertIn('test "$PR_REPO" = "$REPOSITORY"', self.text)
        self.assertIn("pull_request:", self.text)
        self.assertIn("persist-credentials: false", self.text)

    def test_secret_step_is_after_fail_closed_candidate_resolution(self):
        self.assertLess(
            self.text.index("Resolve exact candidate PR"),
            self.text.index("Require Claude OAuth configuration"),
        )
        self.assertNotIn("pull_request_target", self.text)
        self.assertIn(
            "uses: anthropics/claude-code-action@50b26a71effe456d50842a733597491c5636cb6f",
            self.text,
        )


if __name__ == "__main__":
    unittest.main()
