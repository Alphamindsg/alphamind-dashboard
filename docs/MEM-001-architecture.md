# MEM-001 — Memory MVP Architecture Notes

## Objective

Deliver the smallest daily-use memory workflow for the CEO: create, edit, search, view, tag, score, and relate memories. This sprint intentionally excludes semantic search, embeddings, knowledge graphs, multi-agent synchronization, promotion workflows, and advanced permissions.

## Architecture

```text
Browser UI
  -> app.js (interaction and safe rendering)
  -> memory-engine.js (validation and memory rules)
  -> Supabase JavaScript client
  -> company_memories table
```

The browser remains an untrusted client. Supabase RLS and trusted database configuration remain responsible for data authorization. This change does not modify RLS, authentication, keys, policies, or production data.

## MVP behavior

- **Create:** Saves title, category, notes, source, owner, tags, importance, optional confidence, and related IDs.
- **Edit:** Updates the same record and recalculates tags, importance, confidence, and simple related IDs.
- **Search:** Filters already-loaded memories by title, category, notes, tags, owner, importance, and confidence.
- **Tags:** Merges comma-separated user tags with deterministic automatic tags; normalizes and deduplicates up to 12 values.
- **Confidence:** Calculates a deterministic 20–95 score from completeness and evidence/uncertainty signals. It is not an AI truth probability.
- **Importance:** Retains the existing Low/Medium/High/Critical rule-based classification.
- **Related memories:** Selects up to three records using shared category and tag overlap.

## Legacy-schema confidence

The MVP uses the current `company_memories` schema. Confidence is derived in the browser from memory content and tags. The engine remains tolerant of a future `confidence_score` column, but this PR contains no schema artifact and requires no database migration.

## Database impact

- No schema artifact remains in this PR.
- No migration was applied.
- No RLS, policy, key, authentication, or production-data change occurred.
- No database action is required to merge or evaluate this application change.

Any future confidence persistence must be proposed in a separate database-specific task or PR with environment-specific approval and authorization testing.

## Rollback plan

**Rollback trigger:** create/edit/search failure, incorrect memory mutation, severe UI regression, or a security finding that makes controlled evaluation unsafe.

**Authorized owner:** CTO-approved repository maintainer. Production rollback deployment, if ever applicable, still requires the normal CEO deployment gate.

**Expected recovery time:** approximately 15 minutes for a Git revert and static validation, excluding review or deployment time.

**Steps:**

1. Stop controlled evaluation and preserve the failing record, console output, and reproduction steps without exposing sensitive data.
2. Revert the MEM-001 application commit through a feature branch and pull request.
3. Run JavaScript syntax checks, `memory-mvp-regression-checks.js`, and `security-regression-checks.js`.
4. Verify the previous create, view, search, importance, tags, and related-memory behavior using the acceptance protocol.
5. Confirm the resulting commit and scope before any deployment approval is requested.
6. Record the issue, impact, and follow-up owner.

**Post-rollback verification:** the dashboard loads, existing memories remain readable, legacy create/search/view flows work, no new console error appears, and no database/RLS state changed.

**Rehearsal status:** this rollback has not yet been rehearsed against an authorized shared or production-connected environment.

## Security and privacy

- Database, user, and external content remains untrusted and is safely rendered.
- Dynamic importance classes continue to use strict allowlists.
- Tags are normalized before storage and escaped before display.
- Confidence is numeric and rendered as text.
- No secret or privileged credential is added.
- Client-side validation does not replace RLS or authentication.

## Known limitations

- Search is client-side and loads all records for the Memory page.
- Related memories are one-directional stored IDs and are not a graph.
- Confidence is a completeness/evidence heuristic, not factual verification.
- Automatic and manual tags share one array. The edit form infers manual tags by removing tags reproducible from the current content; a manual tag identical to an automatic tag is not distinguishable, but it is regenerated while still relevant.
- No conflict history or edit version history is included in this MVP.
- Authentication and production-grade RLS remain outside this sprint.
