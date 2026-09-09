# AlphaMind CEO Command Center MVP

A focused static web application that helps the CEO understand priorities, pending attention, recent knowledge, progress, and system state from one morning screen.

DASH-001 reuses the existing MEM-001 Memory MVP. It does not add Memory capabilities, database schema, RLS, authentication, integrations, AI summaries, semantic search, analytics, notifications, or orchestration.

## CEO Command Center

The Command Center includes:

- **Welcome:** Good Morning Lim, current browser-local date, and current time.
- **Today's Focus:** zero to three existing Memory records selected manually with `focus-1`, `focus-2`, and `focus-3` tags. Critical or recent records never become priorities automatically.
- **Waiting For CEO:** existing records tagged `waiting-ceo`, optionally with `pr-approval`, `executive-decision`, `review`, or `outstanding-action`.
- **Recent Knowledge:** up to five important existing Memory records not already shown elsewhere.
- **Quick Capture:** one text input saved through the existing Memory create workflow with category `Learning`, source `command-center`, and tag `quick-capture`.
- **Today's Progress:** up to five recent existing records tagged `completed` or `done`.
- **System Pulse:** four manually maintained statuses in `COMMAND_CENTER_CONFIG`; no generated health assessment.

Only **Command Center** and **Memory** appear in primary navigation. “Ask AlphaMind” remains a future backlog concept and is not present in the UI.

## Existing Memory MVP

The Memory page continues to support:

- create and edit;
- live search and category filters;
- title, notes, owner, importance, confidence, and tags;
- detail panel and simple related memories;
- safe rendering of stored content;
- legacy-schema fallback when the optional confidence column is unavailable.

## Supabase setup

DASH-001 introduces **no Supabase change**. The existing `company_memories` table and approved browser-client configuration must already be available for live data.

1. Open `supabase-config.js`.
2. Provide only the Supabase Project URL and publishable/anon key.
3. Confirm the existing environment permits the approved Memory MVP operations.

Never place a database password, secret key, service-role key, connection string, or other privileged credential in frontend files.

## Run locally

The static application can be served from the repository root:

```bash
python3 -m http.server 8000
```

Then open `http://127.0.0.1:8000/`.

## Validation

Run all dependency-free checks:

```bash
node --check app.js
node --check memory-engine.js
node --check command-center-regression-checks.js
node command-center-regression-checks.js
node memory-mvp-regression-checks.js
node security-regression-checks.js
git diff --check
```

Manual acceptance is documented in [DASH-001 acceptance test](docs/DASH-001-acceptance-test.md). Architecture and rollback are documented in [DASH-001 architecture](docs/DASH-001-architecture.md).

## Review screenshots

- [CEO Command Center — populated review state](docs/screenshots/command-center-populated.png)
- [CEO Command Center — narrow responsive state](docs/screenshots/command-center-responsive.png)
- [Quick Capture](docs/screenshots/command-center-quick-capture.png)

## Key files

| File | Purpose |
|---|---|
| `index.html` | Command Center, Memory page, quick capture, modal, and detail-panel structure |
| `styles.css` | Command Center, responsive, Memory, modal, and safe status presentation styles |
| `app.js` | Manual selectors, Command Center rendering, Quick Capture, navigation, and Memory UI |
| `memory-engine.js` | Existing MEM-001 create/edit/load/search/tag/confidence/importance/related-memory behavior |
| `command-center-regression-checks.js` | DASH-001 deterministic selection, scope, and UI-marker checks |
| `memory-mvp-regression-checks.js` | Existing Memory MVP regression coverage |
| `security-regression-checks.js` | Safe CSS-class normalization and stored-content checks |
| `docs/DASH-001-architecture.md` | Architecture impact, constraints, and rollback plan |
| `docs/DASH-001-user-guide.md` | Daily CEO workflow and tag conventions |
| `docs/DASH-001-acceptance-test.md` | Manual review protocol |
| `docs/DASH-001-test-report.md` | Executed test and screenshot evidence |

## Explicitly out of scope

- AI morning summaries or automatic priorities;
- semantic search, embeddings, or knowledge graph;
- reflection or promotion;
- multi-agent orchestration;
- analytics or notifications;
- new Memory capability;
- Supabase schema, RLS, policy, key, authentication, or production-data changes;
- GitHub, email, calendar, market, research, creator, or task integrations;
- approval, merge, publication, or external execution from the Command Center;
- Ask AlphaMind implementation;
- deployment or merge.

## Offline release-evidence pilot

The reusable `.agents/skills/alphamind-evidence` skill collects the existing seven automated checks from a candidate Git snapshot and verifies exported bytes against the full Git tree. It records artifact hashes, exact candidate and explicit missing release coverage. It does not grant production authorization.

Requires Python 3.12+ and Node.js. From a clean committed checkout, with evidence stored outside the repository:

```bash
python -m unittest discover -s .agents/skills/alphamind-evidence/tests -v
python .agents/skills/alphamind-evidence/scripts/evidence.py collect-dashboard --repo . --out ../dashboard-evidence-new-run --baseline <exact-baseline-sha>
```

The collector exits 2 when release coverage is incomplete, even if all automated checks pass. Authenticate producer/review records separately; local artifact integrity is not production authorization. See the skill's `references/pilot.md` for the tested boundary.