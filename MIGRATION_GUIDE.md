# Migration Guide: Moving to Data Folder Structure

## Overview
This guide explains how to reorganize the project to use a `Data/` folder for all game assets, keeping only `main.py` and Steam files at the root.

## Steam Files (MUST Stay at Root)
These files **must** remain at the root level for Steam integration to work:
- `steam_api.dll` - Steam runtime requires this next to the executable
- `steam_appid.txt` - Steam looks for this file at the root directory

## Step-by-Step Migration

### 1. Create Data Folder Structure
Create a `Data` folder in your project root and move these folders/files:

```
Data/
├── images/          (from root/images/)
├── Images/          (from root/Images/)
├── videos/          (from root/videos/)
├── Videos/          (from root/Videos/)
├── Audio/           (from root/Audio/)
├── Bradsonic_Docs/  (from root/Bradsonic_Docs/)
├── Urgent_Ops/      (from root/Urgent_Ops/)
├── games/           (from root/games/)
├── Retro Gaming.ttf  (from root/Retro Gaming.ttf)
├── emails_inbox.json
├── emails_outbox.json
├── main_terminal_feed.json
└── user_state.json  (created at runtime, but will save here)
```

### 2. Python Modules Decision
You have two options for Python modules:

**Option A: Keep at Root (Recommended)**
- Keep `tokens.py`, `handshake_001.py`, `retro_core_breach.py` at root
- They remain importable as normal Python modules
- No changes needed to imports

**Option B: Move to Data**
- Move modules to `Data/` folder
- Add `Data/` to `sys.path` in `main.py` before imports
- More complex, but keeps everything in Data

**Recommendation: Use Option A** - Python modules are code, not data assets.

### 3. Code Changes (Already Done)
The following changes have been made to `main.py`:
- Added `get_data_path()` helper function
- Updated all file paths to use `get_data_path()`
- Updated `DocumentationViewer` to use data paths
- Updated JSON file loading/saving
- Updated image, video, and font loading

### 4. Build Configuration (Already Updated)
The `build_game.spec` file has been updated to:
- Include entire `Data/` folder
- Keep `steam_appid.txt` at root
- Keep `steam_api.dll` as binary (next to executable)

### 5. Testing
After moving files:
1. Test the game in development mode (should work with fallback)
2. Create the `Data/` folder and move files
3. Test again (should use Data folder)
4. Build with PyInstaller
5. Test the built executable

## File Path Reference

### Before (Old Structure)
```
project/
├── main.py
├── images/
├── videos/
├── Retro Gaming.ttf
├── emails_inbox.json
└── steam_api.dll
```

### After (New Structure)
```
project/
├── main.py
├── steam_api.dll          (Steam - stays at root)
├── steam_appid.txt        (Steam - stays at root)
├── tokens.py              (Python module - stays at root)
├── handshake_001.py       (Python module - stays at root)
├── retro_core_breach.py   (Python module - stays at root)
└── Data/
    ├── images/
    ├── videos/
    ├── Videos/
    ├── Images/
    ├── Audio/
    ├── Bradsonic_Docs/
    ├── Urgent_Ops/
    ├── games/
    ├── Retro Gaming.ttf
    ├── emails_inbox.json
    ├── emails_outbox.json
    ├── main_terminal_feed.json
    └── user_state.json
```

## Backwards Compatibility
The `get_data_path()` function includes fallback logic:
- If `Data/` folder exists, use it
- If not, fall back to root directory (for transition period)

This allows you to migrate gradually without breaking the game.

## Build Process
After migration:
1. Run `build_for_steam.bat` or `pyinstaller build_game.spec`
2. The build will include:
   - `main.py` compiled into executable
   - `Data/` folder with all assets
   - `steam_api.dll` next to executable
   - `steam_appid.txt` at root

## Notes
- The `get_data_path()` function handles both development and built executable scenarios
- In development: looks for `Data/` relative to script
- In built exe: looks for `Data/` in PyInstaller's temp extraction folder
- Steam files must stay at root - this is a Steam runtime requirement

