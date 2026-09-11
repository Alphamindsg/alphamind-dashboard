import unittest
from pathlib import Path


WORKFLOW = Path(__file__).parents[1] / ".github" / "workflows" / "claude-review.yml"
REPOSITORY = "Alphamindsg/alphamind-dashboard"
BRANCH = "copilot/notify-001-shared-telegram-gateway"


def matching_candidates(candidates, sha):
    return [
        candidate for candidate in candidates
        if candidate["head"]["repo"]["full_name"] == REPOSITORY
        and candidate["head"]["ref"] == BRANCH
        and candidate["head"]["sha"] == sha
    ]


class ClaudeWorkflowContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = WORKFLOW.read_text(encoding="utf-8")

    def test_push_path_is_narrow_and_exact_head_bound(self):
        self.assertNotIn("\n  push:", self.text)
        self.assertIn("copilot/notify-001-shared-telegram-gateway", self.text)
        self.assertIn('test "$PR_REPO" = "$GITHUB_REPOSITORY"', self.text)
        self.assertIn('test "${{ github.event.pull_request.head.ref }}" = "$EXPECTED_BRANCH"', self.text)
        self.assertIn('test "$(git rev-parse HEAD)" = "$EXPECTED_SHA"', self.text)
        self.assertIn("issue_comment:", self.text)
        self.assertIn("github.event.comment.user.login == github.repository_owner", self.text)
        self.assertIn('[[ "$COMMENT_BODY" =~ ^@claude', self.text)
        self.assertIn('test "$candidate_sha" = "$requested_sha"', self.text)
        self.assertIn("github.event.issue.pull_request", self.text)
        self.assertIn("github.event.comment.user.login == github.repository_owner", self.text)

    def test_candidate_matching_accepts_only_one_exact_same_repo_head(self):
        sha = "a" * 40
        candidate = {"number": 27, "head": {
            "repo": {"full_name": REPOSITORY}, "ref": BRANCH, "sha": sha,
        }}
        self.assertEqual(matching_candidates([candidate], sha), [candidate])
        self.assertEqual(matching_candidates([], sha), [])
        self.assertEqual(matching_candidates([candidate, candidate], sha), [candidate, candidate])
        self.assertEqual(matching_candidates([{
            **candidate, "head": {**candidate["head"], "sha": "b" * 40}
        }], sha), [])
        self.assertEqual(matching_candidates([{
            **candidate, "head": {**candidate["head"], "repo": {"full_name": "fork/repo"}}
        }], sha), [])

    def test_push_or_skipped_action_cannot_be_certification(self):
        self.assertNotIn("Record push bootstrap limitation", self.text)
        self.assertNotIn("github.event_name == 'push'", self.text)
        self.assertIn("pull_request:", self.text)
        self.assertIn("Run independent Claude review", self.text)
        self.assertIn("steps.auth.outputs.configured == 'true'", self.text)

    def test_pull_request_path_is_same_repo_only(self):
        self.assertIn("github.event.pull_request.head.repo.full_name == github.repository", self.text)
        self.assertIn('test "$PR_REPO" = "$GITHUB_REPOSITORY"', self.text)
        self.assertIn("pull_request:", self.text)
        self.assertIn("persist-credentials: false", self.text)
        self.assertIn("if: github.event_name == 'pull_request'", self.text)
        self.assertIn('gh api "repos/$GITHUB_REPOSITORY/pulls/$ISSUE_NUMBER"', self.text)

    def test_secret_step_is_after_fail_closed_candidate_resolution(self):
        self.assertLess(
            self.text.index("Resolve exact candidate PR"),
            self.text.index("Require Claude OAuth configuration"),
        )
        self.assertNotIn("pull_request_target", self.text)
        self.assertIn(
            "uses: anthropics/claude-code-action@a874e9ecd7bb36efdad65429c6b35815f5a08f10",
            self.text,
        )
        self.assertIn(
            "if: steps.auth.outputs.configured == 'true'",
            self.text,
        )
        self.assertIn('trigger_phrase: "@claude review"', self.text)


if __name__ == "__main__":
    unittest.main()
