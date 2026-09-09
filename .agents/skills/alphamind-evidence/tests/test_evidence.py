import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("evidence", Path(__file__).resolve().parents[1] / "scripts/evidence.py")
ev = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ev)
HEAD = "a" * 40
class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "proof.log").write_bytes(b"synthetic proof")
        self.bundle = {"schema_version": "0.1.0", "repository": "synthetic/repo", "branch": "test",
                       "baseline_sha": "b" * 40, "candidate_sha": HEAD, "created_at": "2026-09-08T00:00:00Z",
                       "rollback_plan": "Revert in isolated test.", "outstanding_risks": [], "checks": [
                           {"id": k, "kind": k, "candidate_sha": HEAD, "status": "PASS",
                            "artifact": "proof.log", "sha256": ev.digest(b"synthetic proof")}
                           for k in ev.REQUIRED]}
    def result(self):
        return ev.inspect_bundle(self.bundle, self.root, HEAD)
    def test_complete_evidence_never_authorizes_production(self):
        result = self.result()
        self.assertEqual(result["readiness"], "EVIDENCE_PRESENT")
        self.assertIs(result["production_authorized"], False)
    def test_each_missing_category_blocks(self):
        for kind in ev.REQUIRED:
            with self.subTest(kind=kind):
                candidate = copy.deepcopy(self.bundle)
                candidate["checks"] = [c for c in candidate["checks"] if c["kind"] != kind]
                self.assertEqual(ev.inspect_bundle(candidate, self.root, HEAD)["readiness"], "BLOCKED")
    def test_stale_candidate(self):
        self.bundle["candidate_sha"] = "c" * 40
        self.assertEqual(self.result()["integrity"], "FAIL")
    def test_stale_individual_check(self):
        self.bundle["checks"][0]["candidate_sha"] = "c" * 40
        self.assertEqual(self.result()["readiness"], "BLOCKED")
    def test_log_tamper(self):
        (self.root / "proof.log").write_bytes(b"changed")
        self.assertEqual(self.result()["integrity"], "FAIL")
    def test_missing_artifact(self):
        (self.root / "proof.log").unlink()
        self.assertEqual(self.result()["readiness"], "BLOCKED")
    def test_traversal_and_absolute_paths(self):
        for path in ("../proof.log", "/proof.log", "C:/proof.log", "x\\proof.log"):
            with self.subTest(path=path):
                self.bundle["checks"][0]["artifact"] = path
                self.assertEqual(self.result()["integrity"], "FAIL")
    def test_failed_check_cannot_be_masked(self):
        extra = copy.deepcopy(self.bundle["checks"][0])
        extra.update(id="failure", status="FAIL")
        self.bundle["checks"].append(extra)
        self.assertEqual(self.result()["readiness"], "BLOCKED")
    def test_unknown_and_duplicate_check(self):
        self.bundle["checks"].append(copy.deepcopy(self.bundle["checks"][0]))
        self.assertEqual(self.result()["integrity"], "FAIL")
    def test_no_security_waiver(self):
        self.bundle["checks"][2].update(status="NOT_APPLICABLE", reason="unwanted")
        self.assertEqual(self.result()["readiness"], "BLOCKED")
    def test_migration_waiver_needs_reason(self):
        check = next(c for c in self.bundle["checks"] if c["kind"] == "migration")
        check["status"] = "NOT_APPLICABLE"
        self.assertEqual(self.result()["readiness"], "BLOCKED")
        check["reason"] = "No schema or data change; review attached."
        self.assertEqual(self.result()["readiness"], "EVIDENCE_PRESENT")
    def test_forged_approval_is_not_authority(self):
        self.bundle["production_authorization"] = {"status": "APPROVED", "ai_confidence": 1.0}
        self.assertIs(self.result()["production_authorized"], False)
    def test_malformed_input(self):
        for bad in (None, [], "pass"):
            self.assertEqual(ev.inspect_bundle(bad, self.root, HEAD)["readiness"], "BLOCKED")
    def test_unknown_status(self):
        self.bundle["checks"][0]["status"] = "GOOD"
        self.assertEqual(self.result()["readiness"], "BLOCKED")
    def test_duplicate_json_keys_rejected(self):
        path = self.root / "invalid.json"
        path.write_text('{"candidate_sha":"a","candidate_sha":"b"}')
        with self.assertRaises(ValueError):
            ev.load_json(path)
    def test_future_schema_rejected(self):
        self.bundle["schema_version"] = "99"
        self.assertEqual(self.result()["readiness"], "BLOCKED")
if __name__ == "__main__":
    unittest.main()
