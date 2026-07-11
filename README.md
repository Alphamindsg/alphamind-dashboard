# AlphaMind OS — Dashboard Prototype

A simple static web prototype for the AlphaMind AI operating system dashboard.

This version uses **Memory Engine v2** — a production-ready memory layer backed by Supabase. Memories are stored in the `company_memories` table with auto-generated tags, importance scores, owner assignment, and related memory links.

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

6. Click **Add Memory**, fill in Title, Category, and Notes, then click **Save**.
7. Confirm:
   - The modal closes
   - A success notification appears
   - The new memory shows in **Recent Memory** with owner, importance, and tags

### Test Memory page

8. Click **Memory** in the sidebar.
9. Confirm all memories load.
10. Type in the search box — results filter live across title, category, notes, and tags.
11. Click a category filter chip (e.g. Strategy) — results narrow to that category.
12. Click a memory card — the detail panel opens with full notes, tags, owner, importance, and related memories.

### Test persistence

13. Refresh the page and confirm memories still load from Supabase.

If something fails, open the browser developer console (**F12 → Console**) for the full error message.

## What each file does

| File | Purpose |
|------|---------|
| `index.html` | Page structure, dashboard sections, Memory page, modal form, detail panel, and script loading order |
| `styles.css` | Visual design: layout, colors, cards, memory filters, tags, importance badges, responsive rules |
| `supabase-config.js` | Supabase Project URL, publishable key, and shared client initialization |
| `memory-engine.js` | Memory Engine v2: save, load, search, auto-tags, importance, related memories |
| `app.js` | UI wiring: navigation, search, filters, detail panel, toast notifications |
| `README.md` | This documentation file |

## What works in this prototype

- Dashboard layout with sidebar navigation
- Summary cards for Athena, Atlas, Market, and Creator
- CEO tasks, company health, and quick action buttons
- Sidebar navigation between Dashboard and Memory page
- Add Memory modal with Title, Category, and Notes fields
- Memories saved to Supabase with owner = Athena (auto-set)
- Rule-based auto-generated tags and importance (Low, Medium, High, Critical)
- Related memory linking on save (up to 3 matches)
- Recent Memory section loads the latest 20 rows
- Memory page with live search and category filters
- Memory detail panel with tags, owner, importance, and related memories
- Clickable memory cards on both Dashboard and Memory page
- Friendly error notifications with full details logged to the browser console

## What is not connected yet

- **AI-generated tags** (planned for Memory Engine v3)
- **Vector search / embeddings**
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
├── index.html
├── styles.css
├── supabase-config.js
├── memory-engine.js
├── app.js
└── README.md
```
