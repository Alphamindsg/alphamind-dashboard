---
name: alphamind-evidence
description: Collect and validate Alphamindsg engineering evidence, artifact integrity and exact-candidate coverage.
metadata:
  version: "0.1.0"
  owner: "Alphamindsg"
---
# Evidence and Provenance Engineering

Read [the shared contract](references/shared-contract.md) for authority, output, evidence, lifecycle and privacy requirements. Install this skill together with alphamind-evidence.

## Purpose and trigger
Collect and validate Alphamindsg engineering evidence, artifact integrity and exact-candidate coverage.

## Non-goals and authority
Hashes prove content consistency, not source truth, signer identity or permission. Do not put secret or personal payloads into shareable evidence.

## Required inputs
Repository/branch; baseline and exact candidate SHA; clean source; commands/results; source provenance; evidence directory.

## Procedure and tools
Preserve SOURCE → EVIDENCE → CALCULATION → THESIS/DECISION → CHALLENGE → AUTHORIZATION → ACTION/ABSTENTION → OUTCOME → ATTRIBUTION → LESSON as linked records. Bind source URI, retrieval/effective timestamps, versions, exact SHA and relevant hashes; retain corrections as new records. Use the supplied offline evidence collector for the Dashboard pilot and validator for declared release coverage. Keep evidence outside the tested tree to avoid a self-referential candidate SHA. Authenticate producer and authority independently of content hashes.
Use existing repository tools under the shared contract. AI is optional only for material unresolved reasoning; deterministic verification and authority decisions remain outside model opinion.

## Structured results
Include source_records, evidence_links, candidate_sha, artifact_digests, missing_coverage, authority_status in the shared task-output contract. Report facts, inferred conclusions and unknowns separately.

## Tests and golden scenarios
Tampered or absent artifacts, stale candidate/check SHAs, duplicate JSON keys, traversal paths and masked failed checks must be rejected. Complete declared evidence must still never authorize production.
Record actual fixture paths, commands and outcomes when integrating this skill. Unexecuted scenarios remain acceptance requirements.

## Metrics
artifact_verification_rate, stale_evidence_rejection_rate, provenance_coverage, reconstruction_success. Define denominators, measurement window and baseline before interpreting changes.

## Failure handling, security and lifecycle
Apply the shared contract. Preserve failed evidence and stop dependent consequential actions when required proof is unavailable.
Version: 0.1.0. Owner: Alphamindsg; maintainer is the relevant repository owner/delegate.
Promotion requires runtime integration and evidence; these instructions alone do not certify a repository capability.

## Executable pilot
Run `python -m unittest discover -s tests -v` from this skill directory.
The Dashboard adapter is deliberately fixed to the inspected repository test commands:
`python scripts/evidence.py collect-dashboard --repo <clean-checkout> --out <new-external-directory> --baseline <exact-sha> --node <node-executable>`.
Validate with `python scripts/evidence.py validate <bundle.json> --expected-head <independently-obtained-candidate-sha>`.
Exit 2 means BLOCKED; missing coverage after successful automated checks is expected.
Read [pilot limitations](references/pilot.md) before interpreting the result.
