# AlphaMind OS — Dashboard Prototype

A simple static web prototype for the AlphaMind AI operating system dashboard.

This version includes the **MEM-001 Memory MVP** backed by Supabase. It supports daily create, edit, search, view, tagging, confidence, importance, and simple related-memory workflows without semantic search or advanced AI memory.

## Supabase setup

Before testing, add your Supabase credentials to **`supabase-config.js`**.

1. Open [Supabase Dashboard](https://supabase.com/dashboard) and select your project.
2. Go to **Project Settings → API**.
3. Copy the **Project URL**.
4. Copy the **Publishable key** (also called the anon / public key).
5. Open `supabase-config.js` in this folder.
6. Replace the placeholders:

```js
const SUPABASE_URL = "PASTE_PROJECT_URL_HERE";
const SUPABASE_PUBLISHABLE_KEY = "PASTE_PUBLISHABLE_KEY_HERE";
```

### Database migration (Memory Engine v2)

Run this SQL in the Supabase SQL Editor **before** testing v2 features:

```sql
ALTER TABLE company_memories
  ADD COLUMN IF NOT EXISTS owner text DEFAULT 'Athena',
  ADD COLUMN IF NOT EXISTS importance text DEFAULT 'Medium',
  ADD COLUMN IF NOT EXISTS tags text[] DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS related_memory_ids int8[] DEFAULT '{}';

CREATE INDEX IF NOT EXISTS idx_company_memories_category
  ON company_memories (category);

CREATE INDEX IF NOT EXISTS idx_company_memories_owner
  ON company_memories (owner);
```

Existing rows receive safe defaults. No data is deleted.

### Optional MEM-001 confidence migration

The MVP works before this migration by calculating confidence in the browser. To persist confidence for new and edited memories, review:

`supabase/migrations/202607120126_mem_001_confidence_score.sql`

Do not apply it without explicit approval for the exact Supabase environment. It adds one nullable `confidence_score` column with a 0–100 check constraint and does not modify RLS or existing memory values.

### Security warning

Use only the **Project URL** and **Publishable (anon) key** in `supabase-config.js`.

Never put these in the dashboard:

- Database password
- Secret key
- Service role key
- Connection string

The publishable key is designed for browser use when Row Level Security (RLS) is enabled. The service role key bypasses RLS and must never be exposed in frontend code.

## How to test locally

1. Paste your Supabase URL and publishable key into `supabase-config.js`.
2. Run the database migration SQL above in Supabase.
3. Confirm temporary RLS policies allow `SELECT`, `INSERT`, and `UPDATE` for local testing.
4. Open this folder: `07_Code/alphamind-dashboard`
5. Double-click `index.html` to open the dashboard in your browser.

### Test Add Memory

6. Click **Add Memory**, fill in Title, Category, Notes, and optional comma-separated Tags, then click **Save**.
7. Confirm:
   - The modal closes
   - A success notification appears
   - The new memory shows in **Recent Memory** with owner, importance, confidence, and tags

### Test Memory page

8. Click **Memory** in the sidebar.
9. Confirm all memories load.
10. Type in the search box — results filter live across title, category, notes, and tags.
11. Click a category filter chip (e.g. Strategy) — results narrow to that category.
12. Click a memory card — the detail panel opens with full notes, tags, owner, importance, confidence, and related memories.

### Test Edit Memory

13. Open a memory and click **Edit Memory**.
14. Change the title, notes, category, or tags and click **Save Changes**.
15. Confirm the detail panel reopens with the updated content and recalculated confidence, importance, and related memories.

### Test persistence

16. Refresh the page and confirm memories still load from Supabase.

If something fails, open the browser developer console (**F12 → Console**) for the full error message.

## MEM-001 screenshots

- [Memory list with importance and confidence](docs/screenshots/memory-mvp-list.png)
- [Filtered memory search](docs/screenshots/memory-mvp-search.png)
- [Memory detail with tags and related memories](docs/screenshots/memory-mvp-detail.png)
- [Edit Memory form](docs/screenshots/memory-mvp-edit.png)
- [Updated memory after save](docs/screenshots/memory-mvp-updated.png)

## What each file does

| File | Purpose |
|------|---------|
| `index.html` | Page structure, dashboard sections, Memory page, modal form, detail panel, and script loading order |
| `styles.css` | Visual design: layout, colors, cards, memory filters, tags, importance badges, responsive rules |
| `supabase-config.js` | Supabase Project URL, publishable key, and shared client initialization |
| `memory-engine.js` | Memory MVP engine: create, edit, load, search, tags, confidence, importance, related memories, and schema fallback |
| `app.js` | UI wiring: create/edit form, navigation, search, filters, detail panel, toast notifications |
| `memory-mvp-regression-checks.js` | Dependency-free regression checks for create, edit, tags, confidence, search, relations, and legacy schema fallback |
| `docs/MEM-001-architecture.md` | MVP architecture, migration plan, security notes, limitations, and rollback plan |
| `docs/MEM-001-user-guide.md` | Daily CEO workflow for creating, searching, editing, tagging, and retrieving memories |
| `docs/MEM-001-test-report.md` | Syntax, regression, browser-flow, search-performance, and screenshot evidence |
| `supabase/migrations/202607120126_mem_001_confidence_score.sql` | Proposed optional confidence persistence migration; not applied automatically |
| `README.md` | This documentation file |

## What works in this prototype

- Dashboard layout with sidebar navigation
- Summary cards for Athena, Atlas, Market, and Creator
- CEO tasks, company health, and quick action buttons
- Sidebar navigation between Dashboard and Memory page
- Add Memory modal with Title, Category, and Notes fields
- Add Memory action on both Dashboard and Memory pages
- Edit existing memories from the detail panel
- Memories saved to Supabase with owner = Athena (auto-set)
- User-entered tags merged with rule-based automatic tags
- Rule-based importance (Low, Medium, High, Critical)
- Deterministic 20–95 confidence score with legacy-schema fallback
- Related memory linking on save (up to 3 matches)
- Recent Memory section loads the latest 20 rows
- Memory page with live search and category filters
- Memory detail panel with tags, owner, importance, confidence, edit, and related memories
- Clickable memory cards on both Dashboard and Memory page
- Friendly error notifications with full details logged to the browser console

## What is not connected yet

- **AI-generated tags** (planned for Memory Engine v3)
- **Vector search / embeddings**
- **Semantic search or knowledge graph**
- **Multi-agent memory synchronization or promotion queues**
- **Owner selection dropdown** (future: Atlas, Orion, Creator, Sentinel, Hermes, Apollo)
- **Real AI employee connections** (Athena, Atlas, and others)
- **Research, trading, and virtual influencer modules**
- **Authentication and user accounts**
- **Production-grade RLS policies**

## Technical notes

- Built with plain HTML, CSS, and JavaScript
- Uses the official Supabase JavaScript browser client via CDN
- No React, Node.js, npm, TypeScript, Python, or Docker required
- Works by opening `index.html` directly in a browser

## Script loading order

`index.html` loads scripts in this order:

1. `https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2`
2. `supabase-config.js`
3. `memory-engine.js`
4. `app.js`

## Folder structure

```
alphamind-dashboard/
├── docs/
│   ├── screenshots/
│   │   ├── memory-mvp-detail.png
│   │   ├── memory-mvp-edit.png
│   │   ├── memory-mvp-list.png
│   │   ├── memory-mvp-search.png
│   │   └── memory-mvp-updated.png
│   ├── MEM-001-architecture.md
│   ├── MEM-001-test-report.md
│   └── MEM-001-user-guide.md
├── supabase/
│   └── migrations/
│       └── 202607120126_mem_001_confidence_score.sql
├── index.html
├── styles.css
├── supabase-config.js
├── memory-engine.js
├── memory-mvp-regression-checks.js
├── app.js
└── README.md
```
