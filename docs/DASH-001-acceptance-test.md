# DASH-001 — CEO Command Center Acceptance Test

## Purpose

Verify the approved Command Center objectives without changing Supabase schema, RLS, authentication, integrations, or production data.

## Preconditions

- Review is performed on the DASH-001 feature branch.
- Existing Memory MVP configuration is available, or browser-only fixture data is injected for screenshot review without changing repository or database state.
- No privileged credential is exposed.
- Browser console is available for error inspection.

## Required fixture characteristics

Use non-sensitive existing or temporary browser-only records representing:

- `focus-1`, `focus-2`, and `focus-3`;
- one `waiting-ceo` + `pr-approval` record;
- one `waiting-ceo` + `executive-decision` record;
- High/Critical recent knowledge;
- one `completed` or `done` record.

Do not insert test records into a shared or production-connected database without separate authorization.

## A. Welcome and navigation

1. Open the Command Center.
2. Confirm **Good Morning Lim** appears.
3. Confirm current date and time render.
4. Confirm primary navigation contains only **Command Center** and **Memory**.
5. Confirm Ask AlphaMind and unfinished modules do not appear.

**Expected:** clear morning orientation with no generated summary.

## B. Today's Focus

1. Confirm focus records appear in `focus-1`, `focus-2`, `focus-3` order.
2. Confirm no more than three appear.
3. Add a Critical record without a focus tag to fixture data.
4. Confirm it does not appear in Focus.
5. Select a Focus item.

**Expected:** only explicitly selected records appear, and selection opens existing Memory detail.

## C. Waiting For CEO

1. Confirm only records tagged `waiting-ceo` appear.
2. Confirm PR approval and executive-decision reason labels render when tagged.
3. Confirm a record without `waiting-ceo` does not appear.
4. Select an item.

**Expected:** existing source Memory opens; no approval or merge action is offered.

## D. Recent Knowledge

1. Confirm up to five important existing records appear.
2. Confirm records already shown in Focus, Waiting For CEO, or Progress are not duplicated.
3. Confirm category, importance, and available date render.
4. Select **View Memory**.

**Expected:** existing Memory page opens without adding search or Memory capability.

## E. Quick Capture

1. Enter one sentence.
2. Press Enter or select **Capture**.
3. Confirm the button prevents duplicate submission while saving.
4. Confirm success notification and cleared input.
5. Open Memory and inspect the new record in an authorized test environment.

**Expected:** title is bounded from the sentence, category is Learning, source is command-center, quick-capture tag exists, and no new field/schema is required.

## F. Today's Progress

1. Confirm records tagged `completed` or `done` appear newest first.
2. Confirm the list is limited to five.
3. Confirm an honest empty state appears when none qualify.

## G. System Pulse

1. Confirm Memory — Healthy.
2. Confirm Engineering — Healthy.
3. Confirm Research — Learning.
4. Confirm Creator Studio — Planning.
5. Confirm no generated explanation or health score appears.

## H. Existing Memory regression

1. Open Memory.
2. Create a record through the full modal in an authorized test environment.
3. Search and filter.
4. Open detail.
5. Edit title, category, notes, and tags.
6. Confirm confidence, importance, tags, and related-memory behavior remain available.

## I. Responsive and accessibility review

1. Review desktop and narrow viewport.
2. Confirm Command Center sections stack without horizontal overflow.
3. Navigate sidebar, cards, Quick Capture, Memory controls, modal, and detail panel by keyboard.
4. Confirm visible focus state and usable labels.
5. Confirm dynamic stored text is displayed as text, not executable markup.

## J. Scope and repository review

1. Run all documented checks.
2. Inspect diff for migrations, schema, RLS, authentication, integrations, analytics, notifications, AI summaries, semantic search, and orchestration.
3. Confirm none were introduced.
4. Confirm branch is not `main` and PR remains unmerged.

## Acceptance gate

- CEO can understand the review state within 60 seconds.
- Quick Capture interaction can be completed within 10 seconds excluding external network failure.
- Pending CEO attention is immediately visible when explicitly represented in existing data.
- Existing Memory workflows and security checks pass.
- No critical defect, scope violation, or prohibited data/system change remains.
