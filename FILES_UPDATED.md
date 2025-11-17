# Files Updated for Data Folder Structure

## Summary
All Python files that reference asset files have been updated to use the new `Data/` folder structure.

## Files Modified

### 1. `main.py`
- ✅ Added `get_data_path()` helper function
- ✅ Updated all image loading paths (`images/`, `Images/`)
- ✅ Updated all video loading paths (`videos/`, `Videos/`)
- ✅ Updated font loading (`Retro Gaming.ttf`)
- ✅ Updated JSON file paths (`emails_inbox.json`, `emails_outbox.json`, `main_terminal_feed.json`, `user_state.json`)
- ✅ Updated PDF/document paths (`Bradsonic_Docs/`)
- ✅ Updated `DocumentationViewer` class to use data paths
- ✅ Added Python path modification to allow imports from `Data/` folder

### 2. `Urgent_Ops/CRACKER_IDE_LAPC1_Driver_Challenge.py`
- ✅ Added `get_data_path()` helper function
- ✅ Updated `IDE-Parrot-logo.png` loading
- ✅ Updated `Parrot-Mov.mp4` video loading
- ✅ Updated `NODE-*.png` badge loading (NODE-1.png through NODE-10.png)
- ✅ Updated `Audio/On-Test.wav` sound loading

### 3. `games/SIMULACRA_CORE.py`
- ✅ Updated font loading in test section to use `get_data_path()` for `Retro Gaming.ttf`
- ✅ Added fallback logic for backwards compatibility

### 4. `games/utils.py`
- ✅ Added `get_data_path()` helper function
- ✅ Updated `resolve_asset_path()` to check Data folder first
- ✅ Updated `load_root_font()` to check Data folder first

### 5. `retro_core_breach.py`
- ✅ Updated font loading in test section (`if __name__ == "__main__"`) to use `get_data_path()` for `Retro Gaming.ttf`
- ✅ Added fallback logic for backwards compatibility

### 6. `build_game.spec`
- ✅ Updated to include entire `Data/` folder
- ✅ Kept `steam_appid.txt` at root (Steam requirement)
- ✅ Kept `steam_api.dll` as binary (Steam requirement)

## Files That Don't Need Changes

### `games/CRACKER_IDE_LAPC1_Driver_Challenge.py`
- Uses default fonts (None) - no file paths to update

### `games/lapc1_assembler_quiz.py`
- Uses default fonts (None) - no file paths to update
- Commented out image loading line - no changes needed

### `tokens.py`
- No file loading - pure Python module

### `handshake_001.py`
- No file loading - pure Python module

### `games/registry.py`
- Only uses `os.path.join` for resolving Python module paths, not asset files

## How It Works

Each file that needs to load assets now:
1. Defines or imports a `get_data_path()` helper function
2. Uses `get_data_path()` to construct paths to assets in the `Data/` folder
3. Falls back to root directory if `Data/` folder doesn't exist (backwards compatibility)

The `get_data_path()` function:
- In development: Looks for `Data/` folder relative to project root
- In built executable: Looks for `Data/` folder in PyInstaller's temp extraction folder (`sys._MEIPASS`)
- Falls back to root directory if `Data/` doesn't exist

## Testing Checklist

After moving files to `Data/` folder, test:
- [ ] Game runs in development mode
- [ ] All images load correctly
- [ ] All videos play correctly
- [ ] All fonts load correctly
- [ ] JSON files load/save correctly
- [ ] PDF documents load correctly
- [ ] Urgent_Ops module loads all assets
- [ ] Games module loads all assets
- [ ] Build process completes successfully
- [ ] Built executable runs correctly

