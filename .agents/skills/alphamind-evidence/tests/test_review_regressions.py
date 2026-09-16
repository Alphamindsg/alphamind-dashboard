"""Independent Codex review regressions; only isolated temporary repos are changed."""
import copy
import importlib.util
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("review_evidence", Path(__file__).resolve().parents[1] / "scripts/evidence.py")
ev = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ev)
HEAD = "a" * 40
REMOTE = "https://github.com/Alphamindsg/alphamind-dashboard.git"
NODE = shutil.which("node")


class ReviewedValidationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "proof.log").write_bytes(b"synthetic review proof")
        self.bundle = {
            "schema_version": ev.VERSION, "repository": "synthetic/repo", "branch": "test",
            "baseline_sha": "b" * 40, "candidate_sha": HEAD, "created_at": "2026-09-08T00:00:00Z",
            "rollback_plan": "Revert isolated change", "outstanding_risks": [],
            "checks": [{"id": k, "kind": k, "candidate_sha": HEAD, "status": "PASS",
                        "artifact": "proof.log", "sha256": ev.digest(b"synthetic review proof")}
                       for k in ev.REQUIRED],
        }

    def assert_blocked(self, bundle):
        result = ev.inspect_bundle(bundle, self.root, HEAD)
        self.assertEqual(result["readiness"], "BLOCKED")
        self.assertIs(result["production_authorized"], False)

    def test_waiver_requires_nonblank_string(self):
        for reason in ("", "   ", None, True, 1, [], ["reason"], {"reason": "text"}):
            with self.subTest(reason=reason):
                bundle = copy.deepcopy(self.bundle)
                next(c for c in bundle["checks"] if c["kind"] == "migration").update(status="NOT_APPLICABLE", reason=reason)
                self.assert_blocked(bundle)

    def test_contradictory_or_malformed_pass_exit_code(self):
        for code in (1, -1, True, False, "0", None, 0.0, {}):
            with self.subTest(code=code):
                bundle = copy.deepcopy(self.bundle)
                bundle["checks"][0]["exit_code"] = code
                self.assert_blocked(bundle)

    def test_risks_require_nonblank_strings(self):
        for risks in ([None], [{}], ["   "], [42], [True], "risk", None):
            with self.subTest(risks=risks):
                bundle = copy.deepcopy(self.bundle)
                bundle["outstanding_risks"] = risks
                self.assert_blocked(bundle)


@unittest.skipUnless(NODE and shutil.which("git"), "Real Node.js and Git required")
class ReviewedCollectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.git("init")
        self.git("config", "user.name", "Isolated Review")
        self.git("config", "user.email", "review@example.invalid")
        self.git("config", "commit.gpgsign", "false")
        self.git("config", "core.autocrlf", "false")
        self.git("remote", "add", "origin", REMOTE)
        for name in ("app.js", "memory-engine.js", "command-center-regression-checks.js",
                     "memory-mvp-regression-checks.js", "security-regression-checks.js"):
            (self.repo / name).write_text('console.log("COMMITTED_SOURCE");\n', encoding="utf-8")
        (self.repo / "nested").mkdir()
        (self.repo / "nested" / "candidate.txt").write_text("nested committed evidence\n", encoding="utf-8")
        self.commit()

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.repo), *args], stderr=subprocess.PIPE).decode().strip()

    def commit(self):
        self.git("add", ".")
        self.git("commit", "-m", "Isolated review fixture")
        self.head = self.git("rev-parse", "HEAD")

    def collect(self):
        return ev.collect(self.repo, self.root / "evidence", self.head, NODE)

    def test_assume_unchanged_executes_committed_source(self):
        self.git("update-index", "--assume-unchanged", "security-regression-checks.js")
        (self.repo / "security-regression-checks.js").write_text('console.log("UNCOMMITTED_SOURCE");\n')
        self.assertEqual(ev.clean_head(self.repo), self.head)
        bundle = self.collect()
        log = (self.root / "evidence/security.log").read_text()
        self.assertIn("COMMITTED_SOURCE", log)
        self.assertNotIn("UNCOMMITTED_SOURCE", log)
        self.assertEqual(bundle["candidate_sha"], self.head)
        self.assertEqual(bundle["configured_remote"], REMOTE)
        result = ev.inspect_bundle(bundle, self.root / "evidence", self.head)
        self.assertEqual(result["readiness"], "BLOCKED")
        self.assertIs(result["production_authorized"], False)

    def test_wrong_configured_remote_rejected(self):
        self.git("remote", "set-url", "origin", "https://github.com/example/unrelated.git")
        with self.assertRaisesRegex(ValueError, "matching configured Git remote"):
            self.collect()
        self.assertFalse((self.root / "evidence").exists())

    def test_local_archive_attributes_cannot_hide_committed_test_input(self):
        (self.repo / "sentinel.txt").write_text("committed condition that must fail the check\n")
        (self.repo / "security-regression-checks.js").write_text(
            'const fs = require("fs"); console.log(fs.existsSync("sentinel.txt") ? "SENTINEL_PRESENT" : "SENTINEL_MISSING"); process.exit(fs.existsSync("sentinel.txt") ? 1 : 0);\n')
        self.commit()
        (self.repo / ".git/info/attributes").write_text("sentinel.txt export-ignore\n")
        self.assertEqual(ev.clean_head(self.repo), self.head)
        # An implementation may reject attributes or reconstruct exact Git tree bytes.
        try:
            bundle = self.collect()
        except (ValueError, FileNotFoundError):
            return
        security = next(c for c in bundle["checks"] if c["id"] == "security")
        self.assertEqual(security["status"], "FAIL", "Local archive attributes silently removed committed input and created a false PASS")

    def test_export_substitution_cannot_relabel_changed_source_as_commit(self):
        (self.repo / "version.txt").write_text("$Format:%H$\n")
        (self.repo / ".gitattributes").write_text("version.txt export-subst\n")
        self.commit()
        with self.assertRaisesRegex(ValueError, "Exported bytes differ"):
            self.collect()
        self.assertFalse((self.root / "evidence/bundle.json").exists())

    def test_test_source_mutation_rejects_bundle(self):
        (self.repo / "security-regression-checks.js").write_text(
            'require("fs").writeFileSync("app.js", "// changed by test\\n");\n')
        self.commit()
        with self.assertRaisesRegex(ValueError, "Test changed exported source"):
            self.collect()
        self.assertFalse((self.root / "evidence/bundle.json").exists())


if __name__ == "__main__":
    unittest.main()
