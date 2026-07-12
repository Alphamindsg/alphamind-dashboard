# DASH-001 — CEO Command Center MVP Architecture

## Objective

Provide one fast morning surface where the CEO can understand manually selected priorities, items waiting for CEO attention, recent important knowledge, completed work, and manually maintained system state. Quick Capture must save one sentence through the existing Memory MVP workflow.

## Architecture

```text
Browser UI
  -> index.html (Command Center + existing Memory surfaces)
  -> app.js
       -> deterministic existing-record selectors
       -> manual System Pulse configuration
       -> existing Memory detail/navigation
       -> one-input Quick Capture
  -> memory-engine.js (unchanged MEM-001 behavior)
  -> existing Supabase browser client and company_memories table
```

DASH-001 does not introduce a service, framework, package manager, API, schema, table, field, RLS policy, authentication model, or integration.

## Component impact

### `index.html`

- Replaces placeholder module cards and navigation with Command Center and Memory.
- Adds Welcome, Today's Focus, Waiting For CEO, Recent Knowledge, Quick Capture, Today's Progress, and System Pulse.
- Preserves the existing Memory page, create/edit modal, toast, and detail panel.

### `app.js`

- Defines the manual configuration contract.
- Selects only explicitly tagged Focus and Waiting For CEO records.
- Selects recent knowledge using existing importance and available timestamps.
- Selects progress using existing `completed` or `done` tags.
- Saves Quick Capture through `MemoryEngine.saveMemory()` with deterministic defaults.
- Uses text nodes for dynamic Command Center records and the existing safe Memory rendering paths.

### `styles.css`

- Adds bounded Command Center layout and responsive behavior.
- Reuses existing colors, cards, typography, buttons, empty states, and importance classes.

### `memory-engine.js`

Unchanged. All create, edit, load, tags, importance, confidence, related-memory, legacy-schema, and Supabase behavior remains MEM-001 behavior.

## Existing-data conventions

| Surface | Existing marker |
|---|---|
| Focus position 1 | `focus-1` |
| Focus position 2 | `focus-2` |
| Focus position 3 | `focus-3` |
| Waiting For CEO | `waiting-ceo` |
| Waiting reason | `pr-approval`, `executive-decision`, `review`, or `outstanding-action` |
| Completed action | `completed` or `done` |
| Quick Capture | source `command-center`, category `Learning`, tag `quick-capture` |

Focus is never inferred from importance, age, category, or content. If markers are missing, the interface shows an honest empty state.

## System Pulse

System Pulse is a small manually maintained array in `COMMAND_CENTER_CONFIG`:

- Memory — Healthy
- Engineering — Healthy
- Research — Learning
- Creator Studio — Planning

It is not generated from telemetry, agent output, repository activity, or Memory content.

## Today's Progress decision

Today's Progress is included because it can be implemented cleanly with existing records and tags. It is a bounded read-only list and requires no schema, integration, or new Memory capability.

## Security and privacy

- No credentials or secret values are introduced.
- No authorization behavior changes.
- Browser access remains controlled by the existing Supabase/RLS environment.
- Dynamic Command Center fields use `textContent`; stored content is not inserted as executable HTML.
- Existing importance CSS continues to use an allowlist.
- Quick Capture uses existing validation and safe rendering.
- The landing page may expose more existing records at once; broader audiences require a separate security review.

## Performance

The Command Center performs one existing Memory load with a 200-record limit and renders bounded lists. This is acceptable for the controlled CEO MVP. Pagination, server filtering, and analytics remain out of scope.

## Known limitations

- External PRs, reviews, and actions appear only when represented by existing Memory records.
- The current Memory select list has `created_at` but not `updated_at`; the implementation uses `updated_at` if already returned and otherwise honestly falls back to `created_at`.
- Quick Capture uses `Learning` as the conservative existing category and may require later correction.
- System Pulse requires a code/configuration change to update during this static MVP.
- Browser-local time is used.
- No action can be approved, merged, completed, or published from the Command Center.

## Rollback plan

**Rollback triggers**

- Existing Memory create, edit, search, detail, tags, confidence, importance, or relations regress.
- Focus includes automatically inferred records or exceeds three items.
- Quick Capture mutates unexpected fields or creates duplicate submissions.
- Stored content creates a rendering/security regression.
- Command Center fails to load while the prior dashboard was usable.
- A material accessibility or responsive-layout regression is confirmed.

**Rollback owner:** CTO-approved repository maintainer. Production rollback, if ever applicable, requires the existing CEO deployment gate.

**Expected code recovery time:** approximately 15 minutes after authorization, excluding review and deployment time.

**Procedure**

1. Stop DASH-001 evaluation and preserve reproduction evidence without exposing sensitive data.
2. Revert the DASH-001 commit on a new feature branch; do not push directly to `main`.
3. Run:
   - `node --check app.js`
   - `node --check memory-engine.js`
   - `node memory-mvp-regression-checks.js`
   - `node security-regression-checks.js`
   - `git diff --check`
4. Verify the previous dashboard and Memory workflows manually.
5. Confirm no database, RLS, authentication, key, policy, or production-data state changed.
6. Submit the revert for review and obtain required deployment approval if applicable.
7. Record the defect, impact, evidence, and follow-up owner.

**Data rollback:** None expected. DASH-001 contains no migration or data operation. Quick Capture records created during an authorized pilot remain ordinary existing Memory records and require separate owner-approved correction/deletion if inappropriate.
