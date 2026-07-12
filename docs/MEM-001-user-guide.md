# AlphaMind Memory MVP — CEO User Guide

## Open Memory

Select **Memory** in the left navigation. The page shows saved memories, search, category filters, tags, importance, confidence, and related-memory access.

## Create a memory

1. Select **Add Memory** from the Dashboard or Memory page.
2. Enter a clear title.
3. Choose a category.
4. Write the important context, decision, evidence, or lesson in Notes.
5. Optionally enter comma-separated tags.
6. Select **Save**.

AlphaMind automatically adds relevant tags, calculates importance and confidence, and finds up to three simple related memories.

## Search memories

1. Open **Memory**.
2. Type a word, phrase, tag, owner, importance value, or confidence number.
3. Optionally select a category filter.
4. Results update after a short debounce.

Search is case-insensitive and covers title, category, notes, tags, owner, importance, and confidence.

## View a memory

Select any memory card. The detail panel shows:

- category and owner;
- importance;
- confidence;
- full notes;
- tags;
- related memories.

Select a related memory to open it.

## Edit a memory

1. Open the memory detail panel.
2. Select **Edit Memory**.
3. Change title, category, notes, or tags.
4. Select **Save Changes**.

AlphaMind updates the record and recalculates automatic tags, importance, confidence, and related memories.

## Tags

Enter tags separated by commas, for example:

`strategy, q3, board-decision`

Tags are converted to lowercase, spaces become hyphens, duplicates are removed, and the total is limited to 12. AlphaMind may add category and content tags automatically.

## Confidence score

Confidence is a deterministic content-quality indicator from 20% to 95%. It increases when a memory has clear detail, tags, and evidence-oriented language. It decreases when the content explicitly says it is uncertain or unverified.

Confidence does **not** prove a memory is true. Use the source and notes to judge reliability.

## Importance

- **Low:** routine or short context.
- **Medium:** useful operational knowledge.
- **High:** priorities, decisions, strategy, or substantial notes.
- **Critical:** strategic and urgent decision-oriented knowledge with strong importance signals.

## Related memories

Related memories are selected using category and shared tags. This is intentionally simple and does not use semantic search, embeddings, or a knowledge graph.

## Daily-use suggestions

- Save decisions immediately after they are made.
- Include why the decision was made and what evidence supported it.
- Use stable tags for recurring topics.
- Correct memories when facts change rather than creating contradictory duplicates.
- Search before repeating research or reopening an old decision.

## Troubleshooting

### Memory does not save or update

Confirm the Supabase URL, publishable key, table permissions, and RLS rules allow the required operation.

### Confidence changes after editing

Confidence is derived in the browser from the current title, category, notes, and tags. It may change when the memory content changes. This PR does not require or include a database schema change for confidence.

### Search returns no result

Clear the category filter and search with a shorter title word or tag.

### Related memories are empty

Add useful tags or select a category shared with other memories. Records need category or tag overlap to be related.
