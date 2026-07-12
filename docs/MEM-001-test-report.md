# MEM-001 — Test and Evidence Report

## Scope and risk

Risk classification: **Medium**.

Validation covers the approved application scope only:

- create and edit logic;
- client-side search and retrieval;
- manual and automatic tags;
- confidence and importance;
- simple related memories;
- legacy-schema compatibility.

No Supabase schema artifact remains in this PR. No migration, RLS, policy, key, authentication, production-data, deployment, or production test action occurred.

## Reproducible static and regression checks

Run from the repository root:

```sh
for file in *.js; do node --check "$file"; done
node memory-mvp-regression-checks.js
node security-regression-checks.js
```

Recorded result on the PR head:

- JavaScript syntax checks: passed.
- Memory MVP regression checks: passed.
- Existing frontend security regression checks: passed.
- `git diff --check`: passed.

The regression suite covers:

- tag normalization and deduplication;
- user and automatic tag merging;
- confidence bounds and evidence behavior;
- derived confidence for `NULL` or absent persisted values;
- related-memory ranking and self-exclusion;
- create and edit behavior through a Supabase-compatible mock;
- search by content, tags, and confidence;
- legacy schema fallback;
- removal of obsolete derived tags after edit;
- required edit, tag, and confidence UI controls.

## Manual acceptance protocol

The reproducible human procedure is documented in [MEM-001 Manual Acceptance Test Protocol](MEM-001-acceptance-test.md).

Current status:

| Acceptance area | Evidence status |
|---|---|
| Open Create Memory | Visual fixture evidence available |
| Submit and list a new memory | Visual fixture evidence available |
| Refresh persistence | Not executed against an authorized Supabase environment |
| Edit and post-save update | Visual fixture evidence available |
| Search and detail retrieval | Visual fixture evidence available |
| Edited-state persistence after refresh | Not executed against an authorized Supabase environment |

The visual evidence was captured from a non-production fixture. No Playwright, Puppeteer, package tooling, or browser harness is included or claimed as part of this PR.

## Performance impact

No reproducible performance benchmark is claimed by this PR.

Search is a 300 ms debounced, client-side filter over all memories loaded into the browser. Performance depends on browser, device, network, RLS-visible dataset size, and note length. The current implementation requires controlled evaluation and later pagination/server-side search before corpus growth.

## Screenshot and textual evidence

- [Create Memory form](screenshots/memory-mvp-create.png)
- [Memory list](screenshots/memory-mvp-list.png)
- [Filtered search](screenshots/memory-mvp-search.png)
- [Memory detail](screenshots/memory-mvp-detail.png)
- [Edit Memory form](screenshots/memory-mvp-edit.png)
- [Updated memory after save](screenshots/memory-mvp-updated.png)

Visual inspection found no blocking desktop clipping in the provided states. Responsive behavior, accessibility, failure states, and refresh persistence remain outside the captured evidence.

## Not executed

- Live or shared Supabase create/edit operations
- Refresh persistence against an authorized Supabase environment
- RLS/authorization negative tests
- Authentication or multi-user tests
- Production performance tests
- Deployment or rollback rehearsal

These gaps are explicit. The accurate readiness statement is:

> MVP ready for controlled CEO evaluation after merge.
