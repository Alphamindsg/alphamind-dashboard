"""Offline evidence collection and integrity checks. Never grants production authority."""
import argparse
import hashlib
import json
import os
import io
import tarfile
import tempfile
from pathlib import Path
import re
import subprocess
import sys
from datetime import datetime, timezone

VERSION = "0.1.0"
SHA = re.compile(r"^[0-9a-f]{40}$")
REQUIRED = ("build", "tests", "security", "dependencies", "migration", "recovery", "independent_review")
def digest(data):
    return hashlib.sha256(data).hexdigest()

def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], stderr=subprocess.PIPE).decode().strip()

def clean_head(root):
    head = git(root, "rev-parse", "HEAD")
    if not SHA.fullmatch(head):
        raise ValueError("Unsupported Git object format")
    if git(root, "status", "--porcelain", "--untracked-files=all"):
        raise ValueError("Working tree is not clean")
    return head

def safe_file(root, relative):
    if not isinstance(relative, str) or not relative or "\\" in relative or ":" in relative:
        raise ValueError("Invalid artifact path")
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError("Artifact path escapes evidence root")
    root = root.resolve()
    resolved = (root / candidate).resolve(strict=True)
    if not resolved.is_relative_to(root) or not resolved.is_file():
        raise ValueError("Artifact is not a contained file")
    for parent in [root / candidate, *(root / candidate).parents]:
        if parent == root:
            break
        if parent.is_symlink():
            raise ValueError("Symlink artifacts are not accepted")
    return resolved

def load_json(path):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate JSON key")
            result[key] = value
        return result
    return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError("Non-finite number")))

def inspect_bundle(bundle, root, expected_head):
    """Integrity/coverage only. Trusted CI/reviewer must authenticate all assertions."""
    errors = []
    if not isinstance(bundle, dict):
        return {"integrity": "FAIL", "readiness": "BLOCKED", "production_authorized": False,
                "errors": ["Bundle must be an object"], "missing": list(REQUIRED)}
    if not isinstance(expected_head, str) or not SHA.fullmatch(expected_head):
        errors.append("Invalid externally supplied expected head")
    if bundle.get("schema_version") != VERSION:
        errors.append("Unsupported schema version")
    if bundle.get("candidate_sha") != expected_head:
        errors.append("Candidate differs from expected head")
    if not isinstance(bundle.get("baseline_sha"), str) or not SHA.fullmatch(bundle.get("baseline_sha", "")):
        errors.append("Invalid baseline SHA")
    for key in ("repository", "branch", "created_at", "rollback_plan"):
        if not isinstance(bundle.get(key), str) or not bundle[key].strip():
            errors.append("Missing " + key)
    if not isinstance(bundle.get("outstanding_risks"), list) or any(not isinstance(r, str) or not r.strip() for r in bundle.get("outstanding_risks", [])):
        errors.append("Risks must be explicit")
    checks = bundle.get("checks")
    if not isinstance(checks, list):
        checks = []
        errors.append("Checks must be an array")
    completed, ids = set(), set()
    for check in checks:
        if not isinstance(check, dict):
            errors.append("Check must be an object")
            continue
        cid = check.get("id")
        if not isinstance(cid, str) or not cid or cid in ids:
            errors.append("Invalid/duplicate check ID")
            continue
        ids.add(cid)
        kind = check.get("kind")
        if kind not in REQUIRED:
            errors.append("Unknown check kind: " + str(kind))
            continue
        if check.get("candidate_sha") != expected_head:
            errors.append(cid + ": stale check")
            continue
        status = check.get("status")
        if status not in ("PASS", "FAIL", "BLOCKED", "NOT_APPLICABLE"):
            errors.append(cid + ": unknown status")
            continue
        try:
            artifact = safe_file(root, check.get("artifact"))
            if digest(artifact.read_bytes()) != check.get("sha256"):
                raise ValueError("Artifact digest mismatch")
        except (OSError, ValueError, TypeError) as exc:
            errors.append(cid + ": " + str(exc))
            continue
        if "exit_code" in check and (type(check["exit_code"]) is not int or (status == "PASS" and check["exit_code"] != 0)):
            errors.append(cid + ": contradictory or invalid exit code")
            continue
        if status == "PASS":
            # A declared pass is not independently authenticated by this validator.
            completed.add(kind)
        elif status == "NOT_APPLICABLE":
            # Only scope-conditional categories can be waived, with reviewable reasoning.
            if kind not in ("migration", "recovery") or not isinstance(check.get("reason"), str) or not check["reason"].strip():
                errors.append(cid + ": invalid applicability waiver")
            else:
                completed.add(kind)
    missing = sorted(set(REQUIRED) - completed)
    # A failed or blocked check cannot be hidden by another passing check of the same kind.
    adverse = [c.get("id") for c in checks if isinstance(c, dict) and c.get("status") in ("FAIL", "BLOCKED")]
    if adverse:
        errors.append("Unresolved non-passing checks: " + ", ".join(str(i) for i in adverse))
    ready = not errors and not missing
    return {"integrity": "PASS" if not errors else "FAIL",
            "readiness": "EVIDENCE_PRESENT" if ready else "BLOCKED",
            "production_authorized": False, "errors": errors, "missing": missing,
            "trust_boundary": "Local integrity and declared coverage only; authenticate producer, review and authorization externally."}

def collect(repo, out, baseline, node):
    repo, out = Path(repo).resolve(), Path(out).resolve()
    if out.is_relative_to(repo):
        raise ValueError("Evidence output must be outside the repository")
    head = clean_head(repo)
    if not SHA.fullmatch(baseline):
        raise ValueError("Baseline must be an exact SHA")
    git(repo, "cat-file", "-e", baseline + "^{commit}")
    remote = git(repo, "remote", "get-url", "origin")
    if remote not in ("https://github.com/Alphamindsg/alphamind-dashboard.git", "https://github.com/Alphamindsg/alphamind-dashboard", "git@github.com:Alphamindsg/alphamind-dashboard.git"):
        raise ValueError("Dashboard adapter requires its matching configured Git remote")
    # Run an exported immutable candidate rather than trusting Git's dirty flags.
    archive = subprocess.check_output(["git", "-c", "core.autocrlf=false", "-C", str(repo), "archive", "--format=tar", head])
    with tempfile.TemporaryDirectory(prefix="alphamind-evidence-") as sandbox_name:
        snapshot = Path(sandbox_name)
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            if any(not member.isfile() and not member.isdir() for member in tar.getmembers()):
                raise ValueError("Snapshot must not contain symlinks or special files")
            tar.extractall(snapshot, filter="data")
        def snapshot_hashes():
            return {str(p.relative_to(snapshot)): digest(p.read_bytes()) for p in snapshot.rglob("*") if p.is_file()}
        before = snapshot_hashes()
        expected = {}
        entries = subprocess.check_output(["git", "-C", str(repo), "ls-tree", "-rz", "--full-tree", head])
        for entry in entries.split(b"\0"):
            if not entry:
                continue
            metadata, raw_path = entry.split(b"\t", 1)
            mode, kind, blob_sha = metadata.split()
            if kind != b"blob" or mode not in (b"100644", b"100755"):
                raise ValueError("Unsupported candidate tree entry")
            relative = raw_path.decode("utf-8")
            path = safe_file(snapshot, relative)
            content = path.read_bytes()
            actual_blob = hashlib.sha1(b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest()
            if actual_blob != blob_sha.decode():
                raise ValueError("Exported bytes differ from candidate Git blob")
            expected[str(path.relative_to(snapshot))] = digest(content)
        if before != expected:
            raise ValueError("Exported file inventory differs from candidate tree")
        # Fixed, inspected pilot adapter. No commands are accepted from untrusted JSON.
        commands = [
            ("syntax-app", "build", [node, "--check", "app.js"]),
            ("syntax-memory", "build", [node, "--check", "memory-engine.js"]),
            ("syntax-regression", "build", [node, "--check", "command-center-regression-checks.js"]),
            ("command-center", "tests", [node, "command-center-regression-checks.js"]),
            ("memory", "tests", [node, "memory-mvp-regression-checks.js"]),
            ("security", "security", [node, "security-regression-checks.js"]),
            ("whitespace", "build", ["git", "diff", "--check", baseline, head]),
        ]
        # Exclusive creation preserves failed runs and prevents accidental evidence overwrites.
        out.mkdir(parents=True, exist_ok=False)
        checks = []
        for cid, kind, command in commands:
            try:
                run = subprocess.run(command, cwd=snapshot if cid != "whitespace" else repo, capture_output=True, timeout=60, shell=False)
                data = run.stdout + b"\nSTDERR\n" + run.stderr
                status, code = ("PASS" if run.returncode == 0 else "FAIL"), run.returncode
            except (OSError, subprocess.TimeoutExpired) as exc:
                data, status, code = str(exc).encode(), "BLOCKED", None
            path = cid + ".log"
            (out / path).write_bytes(data)
            checks.append({"id": cid, "kind": kind, "candidate_sha": head, "status": status,
                           "exit_code": code, "artifact": path, "sha256": digest(data)})
        if snapshot_hashes() != before:
            raise ValueError("Test changed exported source; reject this run")
    # Verify no source changes or branch movement during the run.
    if clean_head(repo) != head:
        raise ValueError("HEAD changed during collection; reject this run")
    bundle = {"schema_version": VERSION, "repository": "Alphamindsg/alphamind-dashboard",
              "configured_remote": remote, "source_binding": "git-archive-of-candidate",
              "snapshot_sha256": digest(json.dumps(before, sort_keys=True).encode()),
              "branch": os.environ.get("GITHUB_HEAD_REF") or git(repo, "branch", "--show-current") or ("detached@" + head),
              "baseline_sha": baseline,
              "candidate_sha": head, "created_at": datetime.now(timezone.utc).isoformat(),
              "checks": checks, "outstanding_risks": ["Local automated checks do not cover live data, browser acceptance, recovery or production configuration."],
              "rollback_plan": "Revert the pilot commit through an approved PR; this pilot changes no application behavior.",
              "production_authorization": {"status": "NOT_REQUESTED"}}
    (out / "bundle.json").write_text(json.dumps(bundle, indent=2) + "\n", encoding="utf-8")
    return bundle

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="mode", required=True)
    c = subs.add_parser("collect-dashboard")
    c.add_argument("--repo", required=True)
    c.add_argument("--out", required=True)
    c.add_argument("--baseline", required=True)
    c.add_argument("--node", default="node")
    v = subs.add_parser("validate")
    v.add_argument("bundle")
    v.add_argument("--expected-head", required=True)
    args = parser.parse_args()
    try:
        if args.mode == "collect-dashboard":
            bundle = collect(args.repo, args.out, args.baseline, args.node)
            result = inspect_bundle(bundle, Path(args.out), bundle["candidate_sha"])
        else:
            result = inspect_bundle(load_json(args.bundle), Path(args.bundle).parent, args.expected_head)
        print(json.dumps(result, indent=2))
        return 0 if result["readiness"] == "EVIDENCE_PRESENT" else 2
    except (ValueError, OSError, subprocess.SubprocessError, TypeError) as exc:
        print(json.dumps({"readiness": "BLOCKED", "production_authorized": False, "error": str(exc)}))
        return 2
if __name__ == "__main__":
    sys.exit(main())
