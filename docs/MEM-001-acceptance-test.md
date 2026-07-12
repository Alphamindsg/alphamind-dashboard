# MEM-001 — Manual Acceptance Test Protocol

## Purpose

Provide a reproducible, human-executed acceptance procedure for the Medium-risk Memory MVP. This protocol verifies create, persistence after refresh, edit, search, and detail retrieval without requiring Playwright, Puppeteer, package tooling, or CI.

## Environment requirements

Use only an explicitly approved controlled-evaluation environment containing no sensitive production data.

Record before testing:

- Application commit:
- Application URL:
- Browser and exact version:
- Operating system:
- Supabase project/environment:
- Dataset size before test:
- Tester:
- Date/time in UTC:
- Approval reference for `SELECT`, `INSERT`, and `UPDATE` testing:

Do not run this protocol against production or shared CEO data without explicit environment-specific approval.

## Test record

Use a unique memory title:

`MEM-001 Acceptance <YYYY-MM-DD HH:MM UTC>`

Suggested values:

- Category: `Operations`
- Notes: `Controlled MEM-001 acceptance record used to verify create, refresh persistence, edit, search, and detail retrieval.`
- Tags: `mem-001, acceptance`

## Procedure

### 1. Open Create Memory

1. Load the dashboard.
2. Select **Add Memory**.
3. Confirm the Create Memory form opens with Title, Category, Notes, Tags, Cancel, and Save controls.
4. Record screenshot/evidence.

**Expected:** Form is visible, usable, and contains no stale values.

### 2. Submit a new memory

1. Enter the unique title and suggested values.
2. Select **Save** once.
3. Wait for the success notification.

**Expected:** The modal closes and one new memory is created without an error or duplicate submission.

### 3. Confirm list visibility

1. Locate the new memory in Recent Memory or the Memory page.
2. Confirm title, category, tags, importance, and confidence are displayed.
3. Record screenshot/evidence.

**Expected:** Exactly one matching memory is visible.

### 4. Refresh and confirm persistence

1. Record the browser refresh time.
2. Refresh the page normally.
3. Return to the Memory page if necessary.
4. Search for the exact unique title.

**Expected:** The same memory is retrieved after refresh with the saved title, notes, category, and tags. No duplicate appears.

### 5. Edit the memory

1. Open the memory detail view.
2. Select **Edit Memory**.
3. Append ` updated` to the title.
4. Add tag `edited`.
5. Select **Save Changes** once.

**Expected:** A success notification appears and the detail view reopens with the updated title and tag.

### 6. Search and retrieve

1. Close the detail view.
2. Search for the exact updated title.
3. Confirm exactly one result appears.
4. Open the result.

**Expected:** Detail view shows the updated title, notes, category, tags, importance, confidence, and any simple related memories.

### 7. Refresh edited state

1. Refresh the browser again.
2. Search for the exact updated title.
3. Open the detail view.

**Expected:** The edited title and tag remain after refresh.

## Result recording

| Step | Result | Evidence | Notes |
|---|---|---|---|
| Open Create Memory | Pass / Fail / Not run | | |
| Submit new memory | Pass / Fail / Not run | | |
| Appears once in list | Pass / Fail / Not run | | |
| Persists after refresh | Pass / Fail / Not run | | |
| Edit saves successfully | Pass / Fail / Not run | | |
| Search returns exact memory | Pass / Fail / Not run | | |
| Detail view is correct | Pass / Fail / Not run | | |
| Edited state persists after refresh | Pass / Fail / Not run | | |

## Current PR evidence status

- Create form: visually evidenced by [Create Memory form](screenshots/memory-mvp-create.png).
- Create submission/list appearance: visually evidenced in the non-production fixture by [Memory list](screenshots/memory-mvp-list.png).
- Edit form and post-save update: visually evidenced by [Edit Memory form](screenshots/memory-mvp-edit.png) and [updated detail](screenshots/memory-mvp-updated.png).
- Search and detail retrieval: visually evidenced by [filtered search](screenshots/memory-mvp-search.png) and [Memory detail](screenshots/memory-mvp-detail.png).
- Refresh persistence against an authorized Supabase environment: **not yet executed**.

The screenshots are visual evidence from a non-production fixture, not a committed automated browser test harness. Final refresh persistence must be recorded during controlled CEO evaluation after merge and before any broader readiness claim.

## Cleanup

The application has no delete workflow in this MVP. Run the protocol in a disposable or explicitly approved test environment. Any cleanup that modifies database data requires separate authorization.
