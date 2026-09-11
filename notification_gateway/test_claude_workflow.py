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
        self.assertIn("push:", self.text)
        self.assertIn("copilot/notify-001-shared-telegram-gateway", self.text)
        self.assertIn('gh api --paginate "repos/$REPOSITORY/pulls?state=open&per_page=100"', self.text)
        self.assertIn("head.repo.full_name", self.text)
        self.assertIn("awk -F", self.text)
        self.assertNotIn("--head", self.text)
        self.assertIn('test "${#candidates[@]}" -eq 1', self.text)
        self.assertIn('test "$candidate_sha" = "$PUSH_SHA"', self.text)
        self.assertIn('test "$(git rev-parse HEAD)" = "$EXPECTED_SHA"', self.text)
        self.assertIn("does not support push events", self.text)

    def test_api_match_requires_repository_branch_and_sha(self):
        self.assertIn('repo="$REPOSITORY"', self.text)
        self.assertIn('branch="$expected_branch"', self.text)
        self.assertIn('sha="$PUSH_SHA"', self.text)
        self.assertIn('$2 == repo && $3 == branch && $4 == sha', self.text)

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
        self.assertIn(
            "if: github.event_name == 'pull_request' && steps.auth.outputs.configured == 'true'",
            self.text,
        )


if __name__ == "__main__":
    unittest.main()
