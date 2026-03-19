# Desktop Shell

## Scope

Use this reference for the Bradsonic desktop itself: icon data, click handling, dragging, hover states, and desktop-only launch rules.

## Main Structures

- `self.icons` is the core desktop icon list. Each icon carries its image, selected image, desktop coordinates, dimensions, label, and drag state.
- Icon positions can be restored from save data and later persisted again through `_load_icon_positions()` and `_save_icon_positions()`.
- `desktop_rect` defines the clickable desktop bounds and is reused for drag clamping.

## Input Model

- Single click selects an icon and can begin a drag.
- Double click launches the icon action or opens the related modal/app.
- Dragging stores per-icon offsets so the icon follows the mouse without snapping its top-left corner directly under the cursor.
- Desktop icon handling happens in the main mouse path before most modal-content interactions, so desktop behavior can feel global if you change ordering carelessly.

## Hover and Hotspots

- `_update_hover_states()` maintains hovered icon/button state and is the main place to trace desktop hover feedback.
- Desktop hover labels and button highlighting depend on current mouse position in scaled desktop space.
- `is_mouse_in_desktop()` is the useful boundary check when debugging clicks that should only count over the desktop.

## Desktop Visibility Rules

- The mail icon is desktop-visible only in locale/region `1`.
- The `dotSONIC` icon is hidden in Pacifica and also depends on the `DOTSONIC` token.
- Game icons are rebuilt through the desktop/game icon loaders when region or state changes affect availability.

## Editing Notes

- Keep icon drag constraints inside `desktop_rect`.
- If you change icon dimensions or spacing, re-check label overlap and saved-position compatibility.
- If launch behavior changes, verify both click timing and drag start logic still feel distinct.
