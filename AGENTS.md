<!-- ALPHAMIND_MULTI_AI_CONTRACT_V1 -->
# Alphamind Multi-AI Engineering Contract

This repository participates in the Alphamind portfolio multi-agent engineering system.

## Roles

- **ChatGPT — Portfolio Supervisor / Architect / Release Gate**
  - decomposes goals into bounded workstreams;
  - checks cross-repository architecture, duplication, owner authority and portfolio standards;
  - independently reviews evidence and recommends the next task;
  - never treats another agent's explanation as proof; require code/test/CI evidence.

- **GitHub Copilot — Primary bounded builder**
  - implements one clearly scoped issue/workstream at a time;
  - creates a dedicated branch and pull request;
  - runs tests, static checks and security checks available in the repository;
  - fixes CI/review findings before requesting merge.

- **OpenAI Codex — Implementation / Debug / Verification specialist**
  - may be primary builder on separately assigned work;
  - otherwise verifies implementation, reproduces failures, adds tests and proposes bounded fixes;
  - must not silently rewrite unrelated code.

- **Anthropic Claude — Independent architecture / security / regression reviewer**
  - reviews intent, architecture, diff, tests, failure modes and regressions;
  - should remain independent from the builder for the same workstream;
  - may implement a fix only when explicitly assigned a separate bounded task.

## Operating model

1. One primary builder per workstream. Never let multiple agents concurrently edit the same branch.
2. Maximum five active implementation workstreams portfolio-wide unless the owner explicitly changes the limit.
3. Work from an issue with objective, scope, acceptance criteria, non-goals, risk level and required evidence.
4. Prefer deterministic services and existing reusable components before generating new systems.
5. Search the repository and shared Alphamind skills before creating duplicate logic.
6. Use a dedicated feature/fix branch. Do not push implementation directly to the protected/default branch.
7. Open a PR early as draft when useful; keep scope bounded.
8. Builder runs the strongest available tests/checks. Independent reviewer validates behavior, regressions, security and maintainability.
9. Evidence is authoritative: exact head SHA, test output, CI status, security scan results and reproducible steps.
10. Never remove features, tests or controls merely to make CI pass.
11. No secret values in code, prompts, issues, logs or PR comments.
12. Do not automatically merge consequential or high-risk changes.

## Owner approval required

Explicit owner approval is required before:
- production deployment or production configuration changes;
- live trading or movement of money;
- payments/refunds outside pre-approved bounded policy;
- destructive data deletion or irreversible migrations;
- privileged account/security-policy changes;
- rotating/revoking real credentials;
- enabling autonomous external actions with material financial, legal, security or safety impact.

## Security

Only perform security testing against authorized Alphamind assets or explicit lab/test targets. Do not create credential theft, destructive malware/ransomware, uncontrolled propagation, unauthorized intrusion or deliberate uncontrolled outages.

## Handoff format

Every agent handoff should state:
- task / issue;
- branch and exact head SHA;
- files changed;
- tests/checks run and results;
- known risks / unresolved assumptions;
- next recommended action;
- whether owner action is required.

## Review rule

A builder must not be the sole final reviewer of its own consequential change. Use an independent agent and deterministic CI/security gates.

## Research rule

For version-sensitive frameworks, APIs, platform policies or unfamiliar technology, verify current official documentation before implementation. Do not present stale model memory as certainty.

