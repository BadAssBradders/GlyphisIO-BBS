# CyberTrain Engineer Build Guide (Windows) — Toolchain + Libraries

This document is written for an engineer working **on this Windows machine** to understand **exactly how CyberTrain builds**, **what it links against**, and how to create new games in the **same “single `main.cpp` + raylib + batch script” format**.

---

## What this project is

- **Language/standard**: C++17
- **Entry point**: `main.cpp`
- **Primary library**: **raylib** (graphics/input/audio)
- **Runtime output**: `bin\CyberTrain.exe` plus `bin\raylib.dll`

---

## The canonical build method on this machine (recommended)

The project is designed to compile with **a direct g++ command** via the batch file:

- **Build + run**: `build_and_run.bat`
- **Run only**: `run.bat`

### What compiler it uses

`build_and_run.bat` searches for `g++.exe` in this order:

- `g++` found in PATH
- `C:\raylib\w64devkit\bin\g++.exe`
- `C:\raylib\raylib\w64devkit\bin\g++.exe`
- `C:\w64devkit\bin\g++.exe`

If it finds w64devkit, it temporarily prepends that folder to PATH inside the script.

### Where it expects raylib to be installed

`build_and_run.bat` auto-detects raylib by looking for:

- `C:\raylib\include\raylib.h`  (raylib root = `C:\raylib`)
- `C:\raylib\raylib\include\raylib.h` (raylib root = `C:\raylib\raylib`)

### The exact compile/link command used

This is the exact command line used by `build_and_run.bat`:

```bat
g++ -std=c++17 -O2 -I "C:\raylib\include" -L "C:\raylib\lib" main.cpp -lraylib -lwinmm -lgdi32 -o bin\CyberTrain.exe
```

Notes:

- **Includes**: `-I "%RAYLIB_PATH%\include"`
- **Library search path**: `-L "%RAYLIB_PATH%\lib"`
- **Linked libs (Windows)**:
  - `-lraylib` (raylib)
  - `-lwinmm` (Windows multimedia timing/audio support used by raylib)
  - `-lgdi32` (Windows GDI used by raylib’s windowing backend)

### The runtime DLL requirement

After a successful build, the script copies:

- From: `%RAYLIB_PATH%\lib\raylib.dll`
- To: `bin\raylib.dll`

`bin\CyberTrain.exe` expects `raylib.dll` to be present next to it (same folder) unless raylib is on the system PATH.

### How to build/run

- **Double-click** `build_and_run.bat`
  - Compiles to `bin\CyberTrain.exe`
  - Copies `raylib.dll`
  - Runs the game
- **Double-click** `run.bat`
  - Runs `bin\CyberTrain.exe` if it exists

---

## Optional build method (CMake)

There is also a `CMakeLists.txt`. It sets **C++17** and tries to find raylib via:

- `find_package(raylib QUIET)` (system-wide install)
- fallback “local raylib” hints (paths inside `CMakeLists.txt`)

On Windows, if raylib is found, CMake links:

- `raylib`
- `winmm`

If you use the CMake path, ensure raylib is installed in a way CMake can find (or adjust the include/lib paths in `CMakeLists.txt`).

---

## Libraries/dependencies summary

### Direct-build (batch file) dependencies

- **C++ compiler**: `g++` (MinGW-w64 / w64devkit)
- **raylib headers**: `raylib.h` under `%RAYLIB_PATH%\include`
- **raylib library**: available under `%RAYLIB_PATH%\lib` so `-lraylib` resolves
- **Windows system libs linked**:
  - `winmm`
  - `gdi32`
- **Runtime**: `raylib.dll` must be alongside the `.exe`

### Project assets

- `images\...` contains textures used by the game.

---

## How to make a new game in this same format

This repo’s format is:

- One main translation unit: `main.cpp`
- One batch file that:
  - locates `g++`
  - locates raylib
  - compiles to `bin\<GameName>.exe`
  - copies `raylib.dll`

### Steps (recommended)

- Copy this folder as a starting template.
- Rename the output binary in `build_and_run.bat`:
  - change `-o bin\CyberTrain.exe` to `-o bin\YourGame.exe`
- (Optional) rename window title and any strings in `main.cpp`.
- Keep using the same raylib install location (`C:\raylib` or `C:\raylib\raylib`).

### Minimal skeleton for a new `main.cpp`

Use raylib’s standard loop structure:

- `InitWindow(...)`
- `SetTargetFPS(...)`
- `while (!WindowShouldClose()) { BeginDrawing(); ... EndDrawing(); }`
- `CloseWindow()`

For examples, see raylib examples on [raylib’s site](https://www.raylib.com/examples.html).

---

## Troubleshooting (most common)

- **“g++ not found”**
  - Install/restore w64devkit under `C:\raylib\w64devkit\bin\`
  - Or install MinGW-w64 and ensure `g++.exe` is on PATH

- **“Raylib not found!”**
  - Ensure raylib is extracted/installed to `C:\raylib` (or `C:\raylib\raylib`)
  - Confirm `C:\raylib\include\raylib.h` exists

- **Game runs but immediately fails to start**
  - Confirm `bin\raylib.dll` exists next to `bin\CyberTrain.exe`


