# Quick Start Guide - Torus Game Project

## ✅ Step-by-Step Setup

### Step 1: Verify Raylib Installation
- Open File Explorer
- Navigate to `C:\raylib`
- You should see:
  - ✅ `include` folder (contains `raylib.h`)
  - ✅ `lib` folder (contains `raylib.lib` and `raylib.dll`)

**If Raylib is NOT installed:**
1. Go to: https://github.com/raysan5/raylib/releases
2. Download: `raylib-5.0-w64-msvc16.zip` (or latest Windows x64 version)
3. Extract to `C:\raylib`

### Step 2: Verify Environment Variable
Open PowerShell and run:
```powershell
$env:RAYLIB_PATH
```
Should show: `C:\raylib`

✅ **You already did this!** Skip to Step 3.

### Step 3: Open Code in Notepad++
1. Open **Notepad++**
2. **File** → **Open**
3. Navigate to: `C:\Dev Projects\Torus\src\main.cpp`
4. You'll see the example game code

### Step 4: Build Your Project
1. Open **File Explorer**
2. Navigate to: `C:\Dev Projects\Torus`
3. **Double-click** `build.bat`
4. A black command window will appear
5. Wait for "Build successful!" message
6. Press any key to close the window

**If build fails:**
- Make sure Visual Studio (or Build Tools) is installed
- Check that `RAYLIB_PATH` is set correctly
- Look at the error messages in the command window

### Step 5: Run the Game
**Option A - Manual:**
1. Navigate to: `C:\Dev Projects\Torus\bin\x64\Debug\`
2. Double-click `Torus.exe`

**Option B - Automatic:**
1. In project folder, double-click `run.bat`
2. It will build and run automatically

You should see a window with:
- "Welcome to Torus!" text
- A blue circle
- Press ESC to close

### Step 6: Start Coding!
1. Edit `src/main.cpp` in Notepad++
2. Make your changes
3. **Save** (Ctrl+S)
4. Run `build.bat` again
5. Run the game to test

## 📁 Project Structure

```
Torus/
├── src/
│   ├── main.cpp      ← Edit your game code here!
│   └── main.h
├── build.bat         ← Double-click to build
├── build_release.bat ← Build optimized version
├── run.bat           ← Build and run automatically
└── bin/
    └── x64/
        └── Debug/
            └── Torus.exe  ← Your compiled game
```

## 🎮 Common Tasks

**Edit code:**
- Open `src/main.cpp` in Notepad++

**Build project:**
- Double-click `build.bat`

**Build and run:**
- Double-click `run.bat`

**Find your executable:**
- `bin\x64\Debug\Torus.exe`

## 🐛 Troubleshooting

**"RAYLIB_PATH not set" error:**
- Run: `[System.Environment]::SetEnvironmentVariable("RAYLIB_PATH", "C:\raylib", "User")` in PowerShell
- Restart your command prompt/terminal

**"Cannot find MSBuild.exe" error:**
- Install Visual Studio 2019 or later with "Desktop development with C++" workload
- Or install "Visual Studio Build Tools"

**"raylib.dll not found" when running:**
- The build script should copy it automatically
- Manually copy `C:\raylib\lib\raylib.dll` to `bin\x64\Debug\`

**Game window doesn't appear:**
- Check `bin\x64\Debug\` folder exists
- Make sure `raylib.dll` is in the same folder as `Torus.exe`

## 📚 Next Steps

- Check out [Raylib Cheat Sheet](https://www.raylib.com/cheatsheet/cheatsheet.html)
- Browse [Raylib Examples](https://www.raylib.com/examples.html)
- Read the [Raylib Wiki](https://github.com/raysan5/raylib/wiki)

Happy coding! 🎮

