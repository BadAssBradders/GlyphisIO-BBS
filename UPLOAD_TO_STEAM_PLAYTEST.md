# Step-by-Step: Upload to Steam Playtest

## Prerequisites Checklist

- [ ] Steam Partner account active
- [ ] App ID: 4179570 created in Steam Partner Portal
- [ ] Steam client installed and logged in
- [ ] Game runs locally with Steam API working
- [ ] All dependencies identified

---

## Step 1: Package Your Python Game

Since this is a Python game, you need to create an executable or bundle Python with it.

### Option A: PyInstaller (Recommended - Single Executable)

1. **Install PyInstaller:**
```bash
pip install pyinstaller
```

2. **Create a spec file** (`build_game.spec`):
```python
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('images', 'images'),
        ('videos', 'videos'),
        ('Audio', 'Audio'),
        ('Bradsonic_Docs', 'Bradsonic_Docs'),
        ('Urgent_Ops', 'Urgent_Ops'),
        ('games', 'games'),
        ('steam_api.dll', '.'),
        ('steam_appid.txt', '.'),
        ('Retro Gaming.ttf', '.'),
    ],
    hiddenimports=[
        'pygame',
        'numpy',
        'cv2',
        'fitz',
        'steamworks',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='GlyphisIO_BBS',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Set to False to hide console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
```

3. **Build the executable:**
```bash
pyinstaller build_game.spec
```

4. **Your build will be in:** `dist/GlyphisIO_BBS/` or `dist/GlyphisIO_BBS.exe`

### Option B: Manual Folder Structure (Alternative)

If PyInstaller doesn't work, create a folder structure:

```
GlyphisIO_BBS_Build/
├── GlyphisIO_BBS.exe (or main.py)
├── steam_api.dll
├── steam_appid.txt
├── images/
├── videos/
├── Audio/
├── Bradsonic_Docs/
├── Urgent_Ops/
├── games/
├── Retro Gaming.ttf
└── [all Python dependencies]
```

---

## Step 2: Prepare Your Build Folder

1. **Create a clean build folder:**
```
SteamBuild/
└── GlyphisIO_BBS/
    ├── GlyphisIO_BBS.exe (or main.py)
    ├── steam_api.dll
    ├── steam_appid.txt
    └── [all game files]
```

2. **Verify these files are included:**
   - ✅ `steam_api.dll`
   - ✅ `steam_appid.txt` (with App ID: 4179570)
   - ✅ All images, videos, audio folders
   - ✅ All Python modules (Urgent_Ops, games, etc.)
   - ✅ Font file (Retro Gaming.ttf)
   - ✅ All dependencies

3. **Test the build locally:**
   - Copy build folder to a different location
   - Run the executable
   - Verify it works without your dev environment

---

## Step 3: Upload via Steam Partner Portal

### Method 1: Web Interface (Easiest)

1. **Go to Steam Partner Portal:**
   - https://partner.steamgames.com/
   - Log in with your Steam account

2. **Navigate to Your App:**
   - Click "Apps & Packages" → "Your Apps"
   - Find App ID: 4179570 (GlyphisIO BBS)
   - Click on it

3. **Go to Builds Section:**
   - Left sidebar → "Builds"
   - Click "Upload Build"

4. **Upload Your Build:**
   - **Build Name:** `playtest-001` (or any name)
   - **Build Description:** "Initial playtest build"
   - **Select Files:** Upload your entire `GlyphisIO_BBS` folder
     - You can zip it first, or upload folder contents
   - **Depot:** Select/create a depot (usually "default" or "content")
   - Click "Upload"

5. **Wait for Upload:**
   - Upload time depends on file size
   - You'll see progress bar
   - Wait for "Upload Complete"

### Method 2: SteamCMD (Command Line)

1. **Download SteamCMD:**
   - https://steamcdn-a.akamaihd.net/client/installer/steamcmd.zip
   - Extract to `C:\SteamCMD\`

2. **Create upload script** (`upload_build.bat`):
```batch
@echo off
echo Uploading to Steam...
cd /d C:\SteamCMD
steamcmd.exe +login YOUR_STEAM_USERNAME YOUR_STEAM_PASSWORD +app_update 4179570 validate +quit
pause
```

3. **Run the script:**
   - Replace `YOUR_STEAM_USERNAME` and `YOUR_STEAM_PASSWORD`
   - Or use Steam Guard token (more secure)

**Note:** SteamCMD method requires more setup. Web interface is easier for first upload.

---

## Step 4: Set Up Playtest

1. **In Steam Partner Portal:**
   - Go to your app (4179570)
   - Left sidebar → "Playtest"

2. **Create Playtest:**
   - Click "Create New Playtest"
   - **Name:** "GlyphisIO BBS - Early Testing"
   - **Description:** "Early access playtest for feedback"
   - **Visibility:** Choose:
     - **Private with codes** (recommended for testing)
     - **Public** (if you want anyone to test)

3. **Assign Build:**
   - Select the build you just uploaded
   - Set as "Active Build"

4. **Configure Settings:**
   - **Max Players:** Set limit (e.g., 100)
   - **End Date:** Optional (or leave open)
   - **Save Changes**

---

## Step 5: Generate Invite Codes (If Private)

1. **In Playtest Settings:**
   - Go to "Invite Codes" section
   - Click "Generate Codes"
   - **Quantity:** How many testers? (e.g., 10-50)
   - **Click Generate**

2. **Share Codes:**
   - Copy codes
   - Share with testers via email/Discord/etc.
   - Testers use codes at: https://store.steam.com/playtest/

---

## Step 6: Test Your Upload

1. **Install via Steam:**
   - Open Steam client
   - Go to Library
   - Find "GlyphisIO BBS" (or search)
   - Click "Install" or "Playtest"

2. **Verify It Works:**
   - Launch game
   - Check console for "Steam API initialized"
   - Test achievements
   - Verify all assets load

3. **Check Steam Overlay:**
   - Press Shift+Tab (default Steam overlay)
   - Should work if Steam API is functioning

---

## Step 7: Update Builds (When You Make Changes)

1. **Make your changes locally**
2. **Rebuild executable** (if using PyInstaller)
3. **Upload new build:**
   - Steam Partner Portal → Builds
   - Upload new version
   - Set as new "Active Build" in Playtest
4. **Testers get update automatically** (if auto-update enabled)

---

## Troubleshooting

### Upload Fails:
- **Check file size limits** (Steam has limits)
- **Verify all files included** (especially DLLs)
- **Check Steam Partner permissions**

### Game Won't Launch on Steam:
- **Verify `steam_appid.txt` exists** in build
- **Check `steam_api.dll` is included**
- **Test build locally first** (outside dev environment)
- **Check Steam client logs**

### Achievements Not Working:
- **Verify Steam client is running**
- **Check achievement names match Steam Partner Portal**
- **Verify App ID is correct** (4179570)

### Missing Assets:
- **Double-check `datas` in PyInstaller spec**
- **Verify folder structure matches local**
- **Test build in clean folder**

---

## Quick Reference Commands

### Build with PyInstaller:
```bash
pyinstaller build_game.spec
```

### Test Build Locally:
```bash
cd dist/GlyphisIO_BBS
./GlyphisIO_BBS.exe
```

### Upload via Web:
1. Partner Portal → Your App → Builds → Upload Build

---

## Next Steps After Upload

1. ✅ Test yourself first
2. ✅ Share with 2-3 trusted testers
3. ✅ Gather feedback
4. ✅ Fix critical issues
5. ✅ Upload updated build
6. ✅ Expand testing gradually

---

## Important Notes

- **First upload takes longest** - be patient
- **Test thoroughly before sharing** - first impressions matter
- **Keep builds organized** - name them clearly (v0.1, v0.2, etc.)
- **Document known issues** - in playtest description
- **Respond to feedback** - testers appreciate communication

Good luck! 🚀

