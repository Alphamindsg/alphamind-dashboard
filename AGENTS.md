# alphamind-dashboard — Autonomous Agent Contract

## Operating model
ISSUE → ONE BUILDER → DRAFT PR → CI → DIFFERENT MODEL REVIEW → FIX LOOP → EXACT-HEAD CI → OWNER/RELEASE GATE

## Roles
- Copilot, Claude, and Codex may act as asynchronous builders on bounded GitHub issues.
- Only one builder owns a workstream at a time.
- A different model should independently review material changes.
- ChatGPT may coordinate portfolio work, research, issue/PR state, and owner escalation, but is not a separate GitHub coding-agent identity.

## Engineering rules
- Read repository docs and existing architecture before editing.
- Preserve one canonical source of truth per domain; do not create duplicate engines or ledgers.
- Prefer deterministic services and bots before AI when AI adds no material value.
- Add tests for new behavior and negative/failure paths.
- Do not remove existing features merely to make a task easier.
- Do not commit secrets.
- Do not deploy, merge, or perform consequential production actions autonomously.
- Keep agent work on task branches/PRs.
- Exact-head CI evidence is required before work is called complete.
- Maximum recommended portfolio concurrency: five active workstreams.

## Escalate to owner when
- requirements materially conflict;
- an irreversible migration is needed;
- production/customer credentials or access are required;
- a consequential financial/security/deployment action is requested;
- two workstreams collide on the same canonical contract.
