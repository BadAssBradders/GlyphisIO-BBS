# CyberTrain Build Synchronization

## Overview

CyberTrain has **two build targets** that both use the **same source file** (`main.cpp`):

1. **Standalone Version**: `bin\CyberTrain.exe` - Runs as a standalone game
2. **BBS Embedded Version**: `cybertrain.dll` - Embedded in the GlyphisIO BBS

## Key Point: Same Source, Same Logic

✅ **Both versions compile from `main.cpp`** - there is only ONE source file.

✅ **Both versions use the same game logic** - they both call `GameLoopBody()` which contains all the game code.

✅ **The only differences are I/O**:
- **Standalone**: Uses `main()` function, creates its own window, uses direct Raylib input
- **Embedded**: Uses `InitializeGame()` function, uses framebuffer rendering, uses injected input from BBS

## How It Works

The code uses a `g_standalone_mode` flag to switch between modes:

- **Standalone mode** (`g_standalone_mode = true`):
  - Entry point: `main()` function
  - Window: Creates visible window (1200x800)
  - Input: Direct Raylib input functions
  - Rendering: Direct to window

- **Embedded mode** (`g_standalone_mode = false`):
  - Entry point: `InitializeGame()` DLL export
  - Window: Hidden window for OpenGL context
  - Input: Injected via `SetKeyState()`, `SetMouseButtonState()`, etc.
  - Rendering: To framebuffer texture (read by BBS)

## Building Both Versions

### Recommended: Unified Build

**Use `build_both.bat`** to build both versions at once:
- Ensures both are built from the same source
- Guarantees they're in sync
- Single command builds everything

### Individual Builds

- `build_and_run.bat` - Builds standalone only
- `build_dll.bat` - Builds BBS DLL only

**Note**: If you build them separately, make sure to rebuild both after making changes!

## Making Changes

When you edit `main.cpp`:

1. **Build both versions** using `build_both.bat`
2. **OR** rebuild both individually:
   - Run `build_dll.bat` for BBS version
   - Run `build_and_run.bat` for standalone version

3. **Test in standalone first** (faster iteration)
4. **Test in BBS** to verify embedded mode works

## Verification

To verify both versions are in sync:

1. Make a change to `main.cpp` (e.g., change a color, add a feature)
2. Build both using `build_both.bat`
3. Test in standalone: `bin\CyberTrain.exe`
4. Test in BBS: Launch BBS and play CyberTrain
5. Both should show the same change!

## Architecture

```
main.cpp (single source file)
├── GameLoopBody() - Core game logic (shared by both)
├── main() - Standalone entry point
│   └── Sets g_standalone_mode = true
│   └── Calls GameLoopBody() in loop
└── InitializeGame() - Embedded entry point (DLL export)
    └── Sets g_standalone_mode = false
    └── UpdateFrame() calls GameLoopBody() once per frame
```

## Summary

✅ **Yes, the standalone IS an exact copy of the BBS version** - they use the same source code!

✅ **One change affects both** - as long as you rebuild both versions after making changes.

✅ **Use `build_both.bat`** to ensure both are always built together and stay in sync!
