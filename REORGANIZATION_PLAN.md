# Project Reorganization Plan: Data Folder Structure

## Overview
Reorganize the project to separate game assets into a `Data` folder, keeping only `main.py` and Steam files at the root level.

## Steam Files (Keep at Root)
These files MUST stay at the root level for Steam to work:
- `steam_api.dll` - Must be next to executable
- `steam_appid.txt` - Steam looks for this at root

## Files to Move to `Data/` Folder

### Directories:
- `images/` → `Data/images/`
- `Images/` → `Data/Images/` (note: capital I)
- `videos/` → `Data/videos/`
- `Videos/` → `Data/Videos/` (note: capital V)
- `Audio/` → `Data/Audio/`
- `Bradsonic_Docs/` → `Data/Bradsonic_Docs/`
- `games/` → `Data/games/`
- `Urgent_Ops/` → `Data/Urgent_Ops/`

### Root-level files:
- `Retro Gaming.ttf` → `Data/Retro Gaming.ttf`
- `emails_inbox.json` → `Data/emails_inbox.json`
- `emails_outbox.json` → `Data/emails_outbox.json`
- `main_terminal_feed.json` → `Data/main_terminal_feed.json`
- `user_state.json` → `Data/user_state.json` (created at runtime, but should save to Data/)
- `tokens.py` → `Data/tokens.py` (or keep at root if imported as module)
- `handshake_001.py` → `Data/handshake_001.py` (or keep at root)
- `retro_core_breach.py` → `Data/retro_core_breach.py` (or keep at root)

## Implementation Steps

1. Add data path helper function to `main.py`
2. Update all file paths in `main.py` to use `get_data_path()`
3. Update `build_game.spec` to include `Data/` folder
4. Move files/folders to `Data/` directory
5. Test build

## Notes
- Python modules (`tokens.py`, `handshake_001.py`, etc.) can stay at root OR be moved to Data and imported from there
- The `get_data_path()` function will handle both development and built executable scenarios

