# Steam Testing & Development Setup Guide

## Quick Setup for Local Testing

### 1. Create `steam_appid.txt` for Local Development

Create a file named `steam_appid.txt` in your project root with just your App ID:

```
4179570
```

This allows Steam API to work locally without uploading to Steam.

### 2. Local Development Workflow

**For daily development:**
- Run `python main.py` directly
- Steam API will initialize if Steam client is running
- Achievements/stats work locally
- No upload needed

**To test on Steam:**
- Upload build using SteamCMD (see below)
- Test via Steam Playtest

## Uploading Builds to Steam

### Option 1: SteamCMD (Recommended)

1. **Download SteamCMD:**
   - Windows: https://steamcdn-a.akamaihd.net/client/installer/steamcmd.zip
   - Extract to a folder (e.g., `C:\SteamCMD`)

2. **Create upload script** (`upload_to_steam.bat`):
```batch
@echo off
cd /d C:\SteamCMD
steamcmd.exe +login YOUR_STEAM_USERNAME YOUR_STEAM_PASSWORD +app_update 4179570 validate +quit
```

**OR use Steamworks SDK tools** (if you have SDK at E:/SDK):
- Use `steamcmd.exe` from `E:/SDK/tools/ContentBuilder/builder/steamcmd.exe`
- Or use the Steam Partner web interface

### Option 2: Steam Partner Web Interface

1. Go to https://partner.steamgames.com/
2. Navigate to your app (4179570)
3. Go to "Builds" → "Upload Build"
4. Upload your game files

### Option 3: Steamworks SDK Content Builder

If you have the SDK at `E:/SDK`:

1. Use `E:/SDK/tools/ContentBuilder/builder/steamcmd.exe`
2. Or use the ContentBuilder scripts in `E:/SDK/tools/ContentBuilder/`

## Recommended Development Structure

```
Crackers BBS/
├── main.py
├── steam_appid.txt          # For local testing
├── steam_api.dll            # Steam API DLL
├── upload_to_steam.bat      # Upload script
├── build_local.bat          # Local test script
└── [your game files]
```

## Testing Workflow

### Daily Development:
```bash
# Just run locally
python main.py
```

### When Ready to Test on Steam:
```bash
# 1. Create a build package
# 2. Upload via SteamCMD or web interface
# 3. Set as playtest build
# 4. Test via Steam client
```

## Steam Playtest Setup

1. **In Steam Partner Portal:**
   - App Admin → Playtest
   - Create new playtest
   - Set visibility (private with codes, or public)
   - Upload build

2. **Invite Testers:**
   - Generate invite codes
   - Share codes with testers
   - They install via Steam client

## Important Files for Steam

- `steam_appid.txt` - Required for local testing
- `steam_api.dll` - Steam API library (already in root ✓)
- Build must include all dependencies (Python runtime, etc.)

## Python Game Distribution Options

Since this is a Python game, you'll need to package it:

### Option A: PyInstaller (Recommended)
```bash
pip install pyinstaller
pyinstaller --onefile --windowed main.py
```

### Option B: cx_Freeze
```bash
pip install cx_Freeze
# Create setup.py for freezing
```

### Option C: Steam's Python Runtime
- Steam supports Python games
- May need to bundle Python runtime with your game

## Quick Test Checklist

- [ ] `steam_appid.txt` created with App ID
- [ ] Steam client running
- [ ] Run game locally - check console for "Steam API initialized"
- [ ] Test achievement unlock
- [ ] Upload build to Steam Playtest
- [ ] Test via Steam client

## Troubleshooting

**Steam API not initializing:**
- Ensure Steam client is running
- Check `steam_appid.txt` exists and has correct App ID
- Verify `steam_api.dll` is in root directory

**Build upload fails:**
- Check Steam Partner account permissions
- Verify App ID is correct
- Ensure all files are included in build

