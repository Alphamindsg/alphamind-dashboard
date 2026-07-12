# DASH-001 — CEO Command Center User Guide

## Morning workflow

1. Open **Command Center**.
2. Confirm the displayed browser-local date and time.
3. Read **Today's Focus**. It contains no more than three manually selected records.
4. Scan **Waiting For CEO** for approvals, decisions, reviews, and outstanding actions.
5. Review **Recent Knowledge** and **System Pulse**.
6. Select the first valuable action.

## Today's Focus

Focus is controlled through existing Memory tags:

- `focus-1`
- `focus-2`
- `focus-3`

The Command Center does not fill empty positions automatically. To change Focus, edit the relevant existing Memory records and update these manual tags.

## Waiting For CEO

Add `waiting-ceo` to an existing Memory record. Optionally add one reason tag:

- `pr-approval`
- `executive-decision`
- `review`
- `outstanding-action`

The Command Center only opens the Memory record. It does not approve, merge, publish, or complete the underlying action.

## Recent Knowledge

Recent Knowledge displays up to five important existing Memory records not already shown in Focus, Waiting For CEO, or Today's Progress. Select an item to open its existing detail panel.

## Quick Capture

1. Select the Quick Capture input.
2. Type one sentence.
3. Press Enter or select **Capture**.
4. Wait for **Knowledge captured**.

Quick Capture uses the existing Memory save workflow with:

- category: `Learning`;
- source: `command-center`;
- tag: `quick-capture`;
- title: a bounded portion of the captured sentence.

Use the Memory page to correct the title, category, notes, or tags later.

## Today's Progress

Existing records tagged `completed` or `done` appear as recent completed actions. The section remains empty when no qualifying records exist.

## System Pulse

System Pulse is manual. It does not derive health from AI, telemetry, GitHub, or Memory content. The initial states are:

- Memory — Healthy
- Engineering — Healthy
- Research — Learning
- Creator Studio — Planning

## Honest empty states

An empty section means no existing record matches the explicit convention. It does not mean AlphaMind inferred that no work exists.

## Daily pilot observation

Record:

- estimated minutes of valuable work saved;
- which section created the saving;
- what still required unnecessary application switching;
- missing, stale, or distracting information.

Do not request additional scope from one observation alone. Collect repeated evidence before expansion.
