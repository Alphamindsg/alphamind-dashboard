# Shared contract — version 0.1.0

Owner: Alphamindsg. Maintainer: repository owner or an explicitly delegated maintainer; no individual appointment is implied.

These are engineering skills, not installed production controls. A capability is COMPLETE only when IMPLEMENTED + INTEGRATED + TESTED + SECURITY-CHECKED + FAILURE-TESTED + EVIDENCED. A skill document, schema, issue or passing format check does not satisfy that definition.

Use deterministic constraints/calculations → deterministic services → bots/workflows → validated statistical/ML methods → bounded AI reasoning → human authority where reserved. AI escalation requires a concrete unresolved reasoning task and material expected value; record reason, bounded inputs, uncertainty, validation and incremental cost. Never promote AI opinion into authority.

Before editing: inspect current repository, branch, exact SHA, working tree, relevant instructions, production/security/financial gates and existing implementation/tests. Work on branches/PRs and reuse sound existing components. Do not expand a narrow task into a portfolio audit. Current repository evidence overrides stale inventory observations.

Authority: L0 observe; L1 analyse; L2 reversible action within granted scope; L3 consequential action; L4 financial/irreversible action. Apply the actual repo policy at the authoritative sink. Missing critical authority fails closed. Owner approval for reserved consequential actions remains necessary; avoid repeatedly requesting approval already given for the same unchanged scope.

Tools: local Git and the repository's inspected test/build entrypoints; installed database/provider adapters only where authorized; GitHub connectors/CLI for evidence and branches/PRs; deterministic calculation libraries when needed. Inspect current tool metadata and availability rather than inventing endpoints. Never assume Copilot or Claude worked merely because configured. Codex supervises and integrates; Copilot is a bounded implementation worker where available; Claude is the preferred independent challenger where available. Require actual artifacts and label a substitute honestly.

Structured task output is JSON with:
- skill, version, repository, baseline_sha, candidate_sha, scope;
- state: HEALTHY | DEGRADED | BLOCKED | FAILED | PAUSED;
- authority: level, permitted_actions, reserved_actions, authorization_evidence;
- inputs: provenance references and relevant timestamps/versions;
- results: the skill-specific fields named in its entrypoint;
- evidence: artifact references, digests, check commands/outcomes and tested candidate;
- failures, risks, metrics, next_actions;
- capability_status: PLANNED | IMPLEMENTED | VERIFIED_LOCAL | INTEGRATED | COMPLETE, with a reason and supporting links.

Use null/unknown with an explicit blocker instead of invented values. The task-output contract is a reporting convention; it is not an authorization token.

Failure handling: preserve failed runs; bound retries; distinguish transient failure from invalid input and uncertain external outcomes. Fail closed for security, finance, accounting, execution or authority-critical uncertainty. Quarantine suspect data and reconcile ambiguous effects. Normal healthy recurring operation remains quiet.

Security/privacy: minimize source payloads; redact credentials and personal/financial/customer data; keep private repository evidence private; synthetic fixtures should not reproduce real identities. Do not bypass anti-bot or platform controls.

Promotion: run relevant golden/failure scenarios, bind tests and independent review to the exact candidate, prove a predefined benefit against baseline, satisfy applicable domain/release/owner gates and monitor rollback criteria. Retirement: replace/downgrade when evidence shows no incremental value, unacceptable risk, obsolete interfaces or a superior proven deterministic implementation. Preserve migration/rollback evidence.

Testing is risk-based: document selected scenarios and actual outcomes, not a universal requirement to run every technique. Domain golden scenarios in entrypoints are required acceptance cases when implementing that domain; they are not claims that those runtime tests already exist.
