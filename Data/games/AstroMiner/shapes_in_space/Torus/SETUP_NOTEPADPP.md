# Setting Up Notepad++ for Building and Running

This guide shows you how to compile and run your Torus game directly from Notepad++ using keyboard shortcuts.

## Method 1: Using NppExec Plugin (Recommended)

### Step 1: Install/Enable NppExec Plugin

1. Open Notepad++
2. Go to **Plugins** → **Plugins Admin** (or **NppExec** if already installed)
3. If NppExec is not installed:
   - Go to **Plugins** → **Plugins Admin**
   - Search for "NppExec"
   - Check the box and click **Install**
   - Restart Notepad++
4. If NppExec is already installed, you're ready!

### Step 2: Create Build Script

1. Open your `src/main.cpp` file in Notepad++
2. Press **F6** (or go to **Plugins** → **NppExec** → **Execute...**)
3. In the script box, paste this:

```batch
cd "$(CURRENT_DIRECTORY)"
IF "$(CURRENT_DIRECTORY)" == "$(CURRENT_DIRECTORY:\src=)" THEN
    cd "$(CURRENT_DIRECTORY)\.."
ENDIF
IF EXIST "C:\raylib\w64devkit\bin\g++.exe" THEN
    SET PATH=C:\raylib\w64devkit\bin;$(PATH)
ENDIF
IF EXIST "Makefile" THEN
    cmd /c "mingw32-make clean 2>nul"
    cmd /c "mingw32-make"
ELSE
    cmd /c "g++ -std=c++17 -O2 -I C:/raylib/include src/main.cpp -L C:/raylib/lib -lraylib -lwinmm -lgdi32 -o bin/Torus.exe"
    cmd /c "copy C:\raylib\lib\raylib.dll bin\ 2>nul"
ENDIF
```

4. Click **Save...** button
5. Name it: **"Build Torus"**
6. Click **Save**

### Step 3: Create Run Script

1. Press **F6** again
2. Paste this script:

```batch
cd "$(CURRENT_DIRECTORY)"
IF "$(CURRENT_DIRECTORY)" == "$(CURRENT_DIRECTORY:\src=)" THEN
    cd "$(CURRENT_DIRECTORY)\.."
ENDIF
IF EXIST "C:\raylib\w64devkit\bin\g++.exe" THEN
    SET PATH=C:\raylib\w64devkit\bin;$(PATH)
ENDIF
IF EXIST "Makefile" THEN
    cmd /c "mingw32-make clean 2>nul"
    cmd /c "mingw32-make"
ELSE
    cmd /c "g++ -std=c++17 -O2 -I C:/raylib/include src/main.cpp -L C:/raylib/lib -lraylib -lwinmm -lgdi32 -o bin/Torus.exe"
    cmd /c "copy C:\raylib\lib\raylib.dll bin\ 2>nul"
ENDIF
IF $(EXITCODE) == 0 THEN
    IF EXIST "bin\Torus.exe" THEN
        cmd /c "start bin\Torus.exe"
    ENDIF
ENDIF
```

3. Click **Save...**
4. Name it: **"Build and Run Torus"**
5. Click **Save**

### Step 4: Assign Keyboard Shortcuts

1. Go to **Plugins** → **NppExec** → **Advanced Options...**
2. Under **Menu Item**, select **"Build Torus"**
3. Click **Add/Modify**
4. Check **"Place to Macros submenu"** (optional, or leave unchecked for main menu)
5. Click **OK**
6. Repeat for **"Build and Run Torus"**
7. Go to **Settings** → **Shortcut Mapper...**
8. Click **Plugin commands** tab
9. Find your scripts (they'll be named like "NppExec: Build Torus")
10. Double-click to assign shortcuts:
    - **Build**: `Ctrl+B` or `F7`
    - **Build and Run**: `Ctrl+R` or `F5`
11. Click **Close**

### Step 5: Use Your Shortcuts!

1. Edit `src/main.cpp` in Notepad++
2. Press your build shortcut (e.g., `Ctrl+B`) to compile
3. Press your run shortcut (e.g., `Ctrl+R`) to build and run
4. Check the console output at the bottom for build messages

## Method 2: Using Run Menu (Simpler, No Shortcuts)

1. Go to **Run** → **Run...** (or press `F5`)
2. Paste this for building (keeps terminal open):
   ```
   cmd /c "cd /d C:\Dev Projects\Torus && build_simple.bat && pause"
   ```
3. Click **Save...** and name it "Build"
4. For building and running (with console open):
   ```
   cmd /c "cd /d C:\Dev Projects\Torus && build_simple.bat && if exist bin\Torus.exe (bin\Torus.exe && pause)"
   ```
5. Click **Save...** and name it "Build and Run"

## Method 3: Quick Build Script (Simplest)

Create a simple batch file and call it from Notepad++:

1. **Run** → **Run...** (`F5`)
2. Enter:
   ```
   $(CURRENT_DIRECTORY)\..\build_mingw.bat
   ```
   (This assumes you're in the `src` folder)
3. Click **Save** and assign a shortcut

## Troubleshooting

**"g++ not found"**
- Make sure MinGW is installed and in PATH
- Or update the script to use `C:\raylib\w64devkit\bin\g++.exe` directly

**Script doesn't run**
- Make sure NppExec plugin is enabled
- Check the console output at the bottom for errors

**Wrong directory**
- The scripts automatically detect if you're in `src` folder and go up one level
- Make sure your project structure is correct

## Quick Reference

After setup:
- **Build**: Press your shortcut (e.g., `Ctrl+B`)
- **Build & Run**: Press your shortcut (e.g., `Ctrl+R`)
- **Check output**: Look at the console at the bottom of Notepad++

Enjoy coding in Notepad++! 🎮

