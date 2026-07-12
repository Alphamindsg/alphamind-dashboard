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

## Backward-compatible confidence

The engine first checks whether `confidence_score` is available. If the column does not exist, it retries legacy queries without that column and calculates confidence in the browser. This allows create, edit, search, and view to work before the optional migration is approved.

When the column exists, new and edited records persist the calculated score. Existing rows with `NULL` confidence continue to receive a derived score when loaded.

## Proposed database change

Migration file:

`supabase/migrations/202607120126_mem_001_confidence_score.sql`

It proposes one nullable `smallint` column with a 0–100 check constraint. It does not alter RLS, policies, keys, authentication, existing memory values, or ownership.

The migration is a proposal only and has not been executed.

## Migration plan

1. Review the migration and confirm the target Supabase environment.
2. Obtain explicit CTO and CEO approval for that environment and operation.
3. Record a backup/recovery checkpoint appropriate to the environment.
4. Apply the additive migration.
5. Verify the column and check constraint.
6. Create a test memory and confirm confidence persistence.
7. Edit the memory and confirm the score updates.
8. Verify existing rows with `NULL` scores still display a derived score.
9. Confirm RLS behavior is unchanged for SELECT, INSERT, and UPDATE.

Because the application has a legacy-schema fallback, migration failure should not block the other MVP features.

## Rollback plan

### Application rollback

1. Stop further rollout or testing.
2. Revert the MEM-001 application commit.
3. Re-run JavaScript syntax and existing security regression checks.
4. Verify legacy create, view, search, importance, tags, and related-memory behavior.
5. Record the issue and reopen the task with evidence.

### Database rollback

The safest immediate rollback is to leave the additive nullable column in place because older code ignores it. Dropping the column is destructive and requires separate approval. If removal is approved:

1. Confirm no deployed code depends on `confidence_score`.
2. Export or otherwise preserve needed confidence values.
3. Drop the check constraint and column in the approved environment.
4. Verify existing memory data and RLS behavior.

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
