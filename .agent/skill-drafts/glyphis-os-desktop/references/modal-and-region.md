# Modal And Region Behavior

## Scope

Use this reference for modal lifecycle, modal dragging, stacking order, region switching, desktop reset behavior, and desktop scaling side effects.

## Modal State

- `active_modals` tracks which modal windows are open.
- `modal_positions` stores per-modal placement.
- `modal_dragging` and related offsets handle title-bar dragging.
- `modal_title_bar_height` defines the draggable strip and matters when tuning hitboxes.

## Desktop Hit-Testing Model

- Treat the front-most window surface as the sole owner of the mouse event at that point.
- Split the window into hit regions first, then route by region:
  - title bar / caption
  - close button
  - client area
  - desktop background
- Do not let clicks fall through a modal surface to icons or windows beneath it.
- Once a drag starts, keep routing motion and release to the captured surface until the drag ends.
- Hover state should follow the same rule: if the cursor is over a modal surface, do not light up desktop icons behind it.

## Modal Lifecycle

- `_open_modal()` is the common entry point for desktop apps and windows.
- `_close_modal()` handles teardown and includes special-case cleanup for some apps.
- Mouse-down logic checks modal title bars in top-most order, so z-order and reversed iteration matter.
- Dragging should avoid fighting with close buttons or modal-specific controls.

## Region Switching

- `_switch_os_region(region_num)` updates `os_locale` and applies desktop side effects.
- Region `1` restores mail availability on the desktop and can award the `SCHOOL_HACK2` token.
- Regions `2` and `3` remove the desktop mail icon and close the mail modal if it is open.
- Region `3` also closes `dotSONIC` if it is active.
- Region changes also reload game icons so desktop availability matches the current locale.

## Scaling And Reset

- `update_scale()` recalculates desktop geometry, rescales icon assets, and repositions elements relative to the current desktop.
- Desktop changes should be checked at multiple resolutions because icon overlap bugs can come from scaling math, not just raw coordinates.
- `_reset_os_mode()` clears modal state and restores core desktop state, including icon placement behavior.

## Editing Notes

- When changing modal visuals, keep the title bar, drag rules, and click targets aligned.
- When changing region logic, verify icon visibility, modal cleanup, and token-triggered desktop state together.
- If a change touches scaling, test both a fresh desktop and a save with moved icons.
