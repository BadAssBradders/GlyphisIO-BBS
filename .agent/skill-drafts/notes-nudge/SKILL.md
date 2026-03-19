---
name: notes-nudge
description: "Implement, tune, or reuse the NOTES-NUDGE (NN) player aide in GlyphisIO BBS. Use when a task needs to auto-surface the external notes overlay, display a full-screen keyboard prompt such as SHIFT+N from `main.py`, or connect story/UI events in `Data/OS/OS_Mode.py`, BBS flows, or other systems to the reusable notes-guidance animation."
---

# NOTES-NUDGE

Use this skill for the reusable player aide that prompts note usage and can auto-open the external notes overlay.

## Workflow

1. Read the NOTES-NUDGE state and renderer in `main.py`.
2. Confirm where the triggering event lives.
3. Trigger NN from the source system through a callback or helper instead of duplicating full-screen UI in that subsystem.
4. Keep the screen-wide animation in `main.py` so it renders from the center of the full game window.
5. If the nudge should show notes immediately, route through the helper that mirrors `SHIFT+N` for the player.

## Source Of Truth

- `main.py`
  - `NOTES_NUDGE_*` constants
  - `_trigger_notes_nudge(...)`
  - `_update_notes_nudge(...)`
  - `_draw_notes_nudge()`
  - `_show_external_notes_overlay_from_nudge()`
- `Data/OS/OS_Mode.py`
  - Use callback hooks such as `trigger_notes_nudge_callback`
  - Trigger from story emails, modal actions, or note-worthy reveals

## Guardrails

- Keep NN as a player aide, not a one-off school-hack special case.
- Do not render the full-screen nudge inside OS Mode or another subsystem.
- Prefer short prompt text such as `SHIFT+N`.
- If a trigger also opens the notes overlay, let `main.py` own that behavior.
- Preserve story pacing: use NN for important reminders, new instructions, or moments where the player should consult notes.

## Search Patterns

```text
rg -n "NOTES_NUDGE|notes_nudge|trigger_notes_nudge|draw_notes_nudge|notepad_overlay_visible" main.py Data/OS/OS_Mode.py
rg -n "trigger_notes_nudge_callback|_maybe_trigger_notes_nudge_for_email" Data/OS/OS_Mode.py
```
