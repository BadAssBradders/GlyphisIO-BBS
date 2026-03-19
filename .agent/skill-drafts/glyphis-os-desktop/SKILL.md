---
name: glyphis-os-desktop
description: "Understand, explain, debug, or modify the Bradsonic OS desktop shell in `Data/OS/OS_Mode.py`. Use when a task involves modal windows, desktop hotspots, icon movement, mouse interaction, scaling, region-driven desktop changes, or desktop app launch behavior."
---

# Glyphis OS Desktop

Use this skill when a task involves the Bradsonic OS desktop shell in `Data/OS/OS_Mode.py`: desktop icons, modal windows, hotspots, mouse interaction, drag behavior, scaling, or region-driven desktop changes.

Do not use this skill for terminal-only work unless the task crosses back into the desktop shell.

## What to Inspect First

Identify which desktop subsystem the task touches:

- icon layout, selection, dragging, or double-click launch
- modal opening, stacking, dragging, or closing
- hover states, desktop hotspots, or click routing
- region changes and their effect on icons, apps, or modal availability
- desktop scaling, reset, or saved icon positions

## Workflow

1. Read the relevant reference file only:
   - `references/desktop-shell.md` for icons, mouse input, drag rules, and desktop-only visibility
   - `references/modal-and-region.md` for modal lifecycle, z-order, region switching, and scaling/reset behavior
2. Open the targeted code in `Data/OS/OS_Mode.py`.
3. Trace both state mutation and rendering. Desktop bugs in this file usually require checking both.
4. When editing, keep icon behavior, modal state, and region side effects consistent.

## Useful Searches

```powershell
rg -n "self\.icons|dragging|last_click_time|_load_icon_positions|_save_icon_positions|_update_hover_states" Data\OS\OS_Mode.py
rg -n "active_modals|modal_positions|_open_modal|_close_modal|modal_dragging|_switch_os_region|os_locale|update_scale" Data\OS\OS_Mode.py
```

## Guardrails

- Preserve single-click select, drag, and double-click launch semantics together.
- Preserve modal z-order and title-bar drag behavior when changing window handling.
- Check region side effects before changing icon visibility or app access.
- After desktop layout edits, verify both saved icon positions and scaled layouts still behave correctly.
