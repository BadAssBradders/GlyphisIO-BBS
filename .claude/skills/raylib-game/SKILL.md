---
name: raylib-game
description: "Create, modify, or integrate Raylib C++ games into the GlyphisIO BBS system. Use this skill whenever the user wants to: create a new game, add a game to the BBS, build a C++ game with Raylib, create a game DLL, write a Python embed wrapper, add a game session adapter, write build scripts, debug framebuffer rendering, fix input forwarding, or anything related to games in this project. Trigger on keywords: game, raylib, DLL, framebuffer, embed, game session, build_dll, build_and_run, C++ game, new game."
---

# Raylib C++ Game Integration Skill for GlyphisIO BBS

This skill covers the complete process of creating and integrating a C++ Raylib game into the GlyphisIO BBS system using the **DLL-based framebuffer sharing** architecture.

## Architecture Overview

The BBS embeds C++ games via a three-layer pipeline:

```
C++ Game (DLL) --[framebuffer pixels]--> Python Embed Wrapper --[pygame Surface]--> BBS Main Loop
```

1. C++ game renders to an **offscreen RenderTexture2D** (hidden window, no visible output)
2. Python loads the DLL via `ctypes`, calls `UpdateFrame()` + `GetFrameBuffer()` each frame
3. Pygame displays the framebuffer at the **OS Desktop position** within the BBS
4. Input is forwarded from Pygame events to the DLL via exported functions

## File Structure for a New Game

When creating a new game called `{GameName}` (e.g., "SpaceRogue"), create these files:

```
Data/games/{GameName}/
    main.cpp              # C++ game source (single-file preferred)
    build_dll.bat         # Builds {gamename}.dll for BBS embedding
    build_and_run.bat     # Builds standalone EXE for testing
    {gamename}.dll        # Built output (not committed)
    raylib.dll            # Raylib shared library (copied by build script)
    libgcc_s_seh-1.dll    # MinGW runtime (copied by build script)
    libstdc++-6.dll       # MinGW C++ runtime (copied by build script)
    libwinpthread-1.dll   # MinGW threading (copied by build script)
    [assets: .png, .ttf, .wav, etc.]

Data/games/{gamename}_embed.py    # Python DLL wrapper
Data/games/registry.py            # Add session class + GameDefinition entry
tokens.py                          # Add token constant if game requires unlock
```

---

## Part 1: C++ Side (main.cpp)

### Required Includes and Global State

```cpp
#include "raylib.h"
#include "raymath.h"
#include "rlgl.h"
#include <math.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#ifdef __cplusplus
extern "C" {
#endif

// ══════════════════════════════════════════════════════════════════
// FRAMEBUFFER GLOBALS
// ══════════════════════════════════════════════════════════════════
RenderTexture2D g_framebuffer = {0};
bool g_framebuffer_initialized = false;
unsigned char* g_frame_buffer_data = NULL;
int g_frame_buffer_size = 0;
bool g_game_initialized = false;

// Render at LOW resolution for performance (GPU->CPU transfer is bottleneck)
// Python scales up via smoothscale. Presets: 0=480x320, 1=600x400, 2=720x480
int g_dynamicRenderWidth = 600;
int g_dynamicRenderHeight = 400;
#define RENDER_WIDTH g_dynamicRenderWidth
#define RENDER_HEIGHT g_dynamicRenderHeight

// Virtual resolution for UI coordinate calculations (authored at this size)
#define VIRTUAL_WIDTH 1200
#define VIRTUAL_HEIGHT 800

// ══════════════════════════════════════════════════════════════════
// INPUT STATE (populated by Python when embedded, by raylib when standalone)
// ══════════════════════════════════════════════════════════════════
struct InputState {
    bool keys[512];
    bool keysPressed[512];
    bool keysReleased[512];
    bool mouseButtons[8];
    bool mouseButtonsPressed[8];
    bool mouseButtonsReleased[8];
    Vector2 mousePosition;
    Vector2 mouseDelta;
    float mouseWheelMove;
} g_inputState = {0};

bool g_exit_requested = false;
bool g_shouldCenterMouse = false;
bool g_standalone_mode = true;  // true=EXE, false=DLL embedded
```

### Required DLL Exports

Every game MUST export these functions:

```cpp
// ── REQUIRED EXPORTS ──────────────────────────────────────────────
__declspec(dllexport) bool InitializeGame();
__declspec(dllexport) void UpdateFrame();
__declspec(dllexport) unsigned char* GetFrameBuffer();
__declspec(dllexport) int GetWidth();
__declspec(dllexport) int GetHeight();
__declspec(dllexport) void SetKeyState(int key, bool down);
__declspec(dllexport) void SetMouseButtonState(int button, bool down);
__declspec(dllexport) void SetInputMousePosition(float x, float y);
__declspec(dllexport) void SetMouseDelta(float dx, float dy);
__declspec(dllexport) void SetMouseWheelMove(float move);

// ── OPTIONAL EXPORTS ──────────────────────────────────────────────
__declspec(dllexport) bool ShouldExit();
__declspec(dllexport) bool ShouldCenterMouse();
__declspec(dllexport) void CleanupGame();
__declspec(dllexport) void SetRenderResolution(int width, int height);
__declspec(dllexport) void SetRenderResolutionPreset(int preset);
__declspec(dllexport) void ResetGame();
__declspec(dllexport) void SetUsername(const char* username);
__declspec(dllexport) int GetLastFinalScore();
__declspec(dllexport) void SaveGameData();
__declspec(dllexport) bool LoadGameData();
```

### InitializeGame() Pattern

```cpp
__declspec(dllexport) bool InitializeGame() {
    g_standalone_mode = false;  // CRITICAL: Switch to embedded input

    SetConfigFlags(FLAG_WINDOW_HIDDEN | FLAG_WINDOW_UNDECORATED);
    InitWindow(VIRTUAL_WIDTH, VIRTUAL_HEIGHT, "{GameName} (Embedded)");
    SetTargetFPS(0);  // BBS controls timing

    InitAudioDevice();

    g_framebuffer = LoadRenderTexture(RENDER_WIDTH, RENDER_HEIGHT);
    g_framebuffer_initialized = true;

    // Load resources (CWD is DLL directory, so use relative paths)
    // g_font = LoadFont("myfont.ttf");
    // g_texture = LoadTexture("sprite.png");

    // Initialize game state
    g_game_initialized = true;
    return g_framebuffer_initialized && g_game_initialized;
}
```

### UpdateFrame() Pattern

```cpp
__declspec(dllexport) void UpdateFrame() {
    if (!g_framebuffer_initialized || !g_game_initialized) return;

    // CRITICAL: Clamp delta time (GetFrameTime() can return 0 in hidden-window mode)
    float dt = GetFrameTime();
    if (dt <= 0.0f || dt > 0.1f) dt = 1.0f / 60.0f;

    // Update game logic using Custom* input functions (NOT raw raylib!)
    UpdateGameLogic(dt);

    // Render to framebuffer (NOT to screen!)
    BeginTextureMode(g_framebuffer);  // NOT BeginDrawing()!
    ClearBackground(BLACK);

    float scaleX = (float)RENDER_WIDTH / (float)VIRTUAL_WIDTH;
    float scaleY = (float)RENDER_HEIGHT / (float)VIRTUAL_HEIGHT;
    Camera2D cam = {0};
    cam.zoom = scaleX;

    BeginMode2D(cam);
    DrawYourGame();  // Draw at VIRTUAL_WIDTH x VIRTUAL_HEIGHT coordinates
    EndMode2D();

    EndTextureMode();  // NOT EndDrawing()!

    // Clear one-shot input flags
    ClearInputFrame();
}
```

### GetFrameBuffer() Pattern

```cpp
__declspec(dllexport) unsigned char* GetFrameBuffer() {
    if (!g_framebuffer_initialized || g_framebuffer.texture.id == 0) return NULL;

    int width = g_framebuffer.texture.width;
    int height = g_framebuffer.texture.height;
    int size = width * height * 4;  // RGBA

    if (g_frame_buffer_size != size) {
        if (g_frame_buffer_data) MemFree(g_frame_buffer_data);
        g_frame_buffer_data = (unsigned char*)MemAlloc(size);
        g_frame_buffer_size = size;
    }

    void* pixels = rlReadTexturePixels(g_framebuffer.texture.id, width, height, g_framebuffer.texture.format);
    if (pixels) {
        memcpy(g_frame_buffer_data, pixels, size);
        MemFree(pixels);
    }
    return g_frame_buffer_data;
}
```

### Custom Input Wrappers (CRITICAL)

**You MUST use these instead of raylib's built-in input functions!** Raw raylib input won't work because the window is hidden.

```cpp
static bool CustomIsKeyDown(int key) {
    return g_standalone_mode ? IsKeyDown(key) :
           (key >= 0 && key < 512 ? g_inputState.keys[key] : false);
}
static bool CustomIsKeyPressed(int key) {
    return g_standalone_mode ? IsKeyPressed(key) :
           (key >= 0 && key < 512 ? g_inputState.keysPressed[key] : false);
}
static bool CustomIsMouseButtonDown(int button) {
    return g_standalone_mode ? IsMouseButtonDown(button) :
           (button >= 0 && button < 8 ? g_inputState.mouseButtons[button] : false);
}
static bool CustomIsMouseButtonPressed(int button) {
    return g_standalone_mode ? IsMouseButtonPressed(button) :
           (button >= 0 && button < 8 ? g_inputState.mouseButtonsPressed[button] : false);
}
static Vector2 CustomGetMousePosition() {
    return g_standalone_mode ? GetMousePosition() : g_inputState.mousePosition;
}
static Vector2 CustomGetMouseDelta() {
    return g_standalone_mode ? GetMouseDelta() : g_inputState.mouseDelta;
}
static float CustomGetMouseWheelMove() {
    return g_standalone_mode ? GetMouseWheelMove() : g_inputState.mouseWheelMove;
}
```

### Input Export Functions

```cpp
__declspec(dllexport) void SetKeyState(int key, bool down) {
    if (key >= 0 && key < 512) {
        if (down && !g_inputState.keys[key]) g_inputState.keysPressed[key] = true;
        if (!down && g_inputState.keys[key]) g_inputState.keysReleased[key] = true;
        g_inputState.keys[key] = down;
    }
}
__declspec(dllexport) void SetMouseButtonState(int button, bool down) {
    if (button >= 0 && button < 8) {
        if (down && !g_inputState.mouseButtons[button]) g_inputState.mouseButtonsPressed[button] = true;
        if (!down && g_inputState.mouseButtons[button]) g_inputState.mouseButtonsReleased[button] = true;
        g_inputState.mouseButtons[button] = down;
    }
}
__declspec(dllexport) void SetInputMousePosition(float x, float y) {
    g_inputState.mousePosition = (Vector2){x, y};
}
__declspec(dllexport) void SetMouseDelta(float dx, float dy) {
    g_inputState.mouseDelta = (Vector2){dx, dy};
}
__declspec(dllexport) void SetMouseWheelMove(float move) {
    g_inputState.mouseWheelMove = move;
}

static void ClearInputFrame() {
    memset(g_inputState.keysPressed, 0, sizeof(g_inputState.keysPressed));
    memset(g_inputState.keysReleased, 0, sizeof(g_inputState.keysReleased));
    memset(g_inputState.mouseButtonsPressed, 0, sizeof(g_inputState.mouseButtonsPressed));
    memset(g_inputState.mouseButtonsReleased, 0, sizeof(g_inputState.mouseButtonsReleased));
    g_inputState.mouseDelta = (Vector2){0, 0};
    g_inputState.mouseWheelMove = 0;
}
```

### Standalone main() (for testing outside BBS)

```cpp
int main() {
    g_standalone_mode = true;
    InitWindow(VIRTUAL_WIDTH, VIRTUAL_HEIGHT, "{GameName}");
    SetTargetFPS(60);
    InitAudioDevice();

    // Load resources, init game state...

    while (!WindowShouldClose()) {
        float dt = GetFrameTime();
        if (dt <= 0.0f || dt > 0.1f) dt = 1.0f / 60.0f;

        UpdateGameLogic(dt);

        BeginDrawing();
        ClearBackground(BLACK);
        DrawYourGame();
        EndDrawing();
    }

    CloseAudioDevice();
    CloseWindow();
    return 0;
}

#ifdef __cplusplus
}
#endif
```

### Key Code Reference

| Key | Raylib | Key | Raylib |
|-----|--------|-----|--------|
| UP | 265 | A-Z | 65-90 |
| DOWN | 264 | 0-9 | 48-57 |
| LEFT | 263 | SPACE | 32 |
| RIGHT | 262 | ENTER | 257 |
| ESCAPE | 256 | BACKSPACE | 259 |
| LSHIFT | 340 | RSHIFT | 344 |
| LCTRL | 341 | RCTRL | 345 |
| MINUS | 45 | EQUAL | 61 |

Mouse: LEFT=0, RIGHT=1, MIDDLE=2

---

## Part 2: Build Scripts

### build_dll.bat (for BBS embedding)

```bat
@echo off
setlocal EnableDelayedExpansion
REM Build {gamename}.dll for BBS integration

echo Building {gamename}.dll for BBS integration...
echo.

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

REM Find g++ compiler
set "GPP_PATH="
where g++ >nul 2>&1
if !ERRORLEVEL! EQU 0 (
    set "GPP_PATH=g++"
) else if exist "C:\raylib\w64devkit\bin\g++.exe" (
    set "GPP_PATH=C:\raylib\w64devkit\bin\g++.exe"
    set "PATH=C:\raylib\w64devkit\bin;%PATH%"
) else if exist "C:\raylib\raylib\w64devkit\bin\g++.exe" (
    set "GPP_PATH=C:\raylib\raylib\w64devkit\bin\g++.exe"
    set "PATH=C:\raylib\raylib\w64devkit\bin;%PATH%"
) else if exist "C:\w64devkit\bin\g++.exe" (
    set "GPP_PATH=C:\w64devkit\bin\g++.exe"
    set "PATH=C:\w64devkit\bin;%PATH%"
) else (
    echo ERROR: g++ compiler not found
    pause & exit /b 1
)

REM Find Raylib
set "RAYLIB_PATH="
if exist "C:\raylib\include\raylib.h" (
    set "RAYLIB_PATH=C:\raylib"
) else if exist "C:\raylib\raylib\include\raylib.h" (
    set "RAYLIB_PATH=C:\raylib\raylib"
) else (
    echo ERROR: Raylib not found!
    pause & exit /b 1
)

echo Using g++: %GPP_PATH%
echo Using Raylib: %RAYLIB_PATH%

REM Check if DLL is locked
if exist "{gamename}.dll" (
    del /f /q "{gamename}.dll" >nul 2>&1
    if exist "{gamename}.dll" (
        echo ERROR: {gamename}.dll is LOCKED - close BBS first
        goto :after_build
    )
)

REM Compile as shared library (DLL)
%GPP_PATH% main.cpp -o {gamename}.dll -shared -std=c++17 -O2 -I "%RAYLIB_PATH%\include" -L "%RAYLIB_PATH%\lib" -lraylibdll -lopengl32 -lgdi32 -lwinmm

set "BUILD_RESULT=!ERRORLEVEL!"

if !BUILD_RESULT! EQU 0 (
    echo SUCCESS: {gamename}.dll created!

    REM Copy raylib.dll
    if exist "%RAYLIB_PATH%\lib\raylib.dll" (
        copy "%RAYLIB_PATH%\lib\raylib.dll" "." >nul 2>&1
    )

    REM Copy MinGW runtime DLLs
    set "ASTROMINER_DIR=%SCRIPT_DIR%..\AstroMiner"
    if exist "!ASTROMINER_DIR!\libgcc_s_seh-1.dll" (
        copy "!ASTROMINER_DIR!\libgcc_s_seh-1.dll" "." >nul 2>&1
        copy "!ASTROMINER_DIR!\libstdc++-6.dll" "." >nul 2>&1
        copy "!ASTROMINER_DIR!\libwinpthread-1.dll" "." >nul 2>&1
    )
) else (
    echo BUILD FAILED! Check errors above.
)

:after_build
echo.
pause
endlocal
```

### build_and_run.bat (standalone testing)

```bat
@echo off
REM Build and run {GameName} standalone

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

set "GPP_PATH="
where g++ >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set "GPP_PATH=g++"
) else if exist "C:\raylib\w64devkit\bin\g++.exe" (
    set "GPP_PATH=C:\raylib\w64devkit\bin\g++.exe"
    set "PATH=C:\raylib\w64devkit\bin;%PATH%"
) else if exist "C:\raylib\raylib\w64devkit\bin\g++.exe" (
    set "GPP_PATH=C:\raylib\raylib\w64devkit\bin\g++.exe"
    set "PATH=C:\raylib\raylib\w64devkit\bin;%PATH%"
) else if exist "C:\w64devkit\bin\g++.exe" (
    set "GPP_PATH=C:\w64devkit\bin\g++.exe"
    set "PATH=C:\w64devkit\bin;%PATH%"
) else (
    echo ERROR: g++ not found
    pause & exit /b 1
)

set "RAYLIB_PATH="
if exist "C:\raylib\include\raylib.h" (
    set "RAYLIB_PATH=C:\raylib"
) else if exist "C:\raylib\raylib\include\raylib.h" (
    set "RAYLIB_PATH=C:\raylib\raylib"
) else (
    echo ERROR: Raylib not found!
    pause & exit /b 1
)

if not exist "bin" mkdir bin
%GPP_PATH% -std=c++17 -O2 -I "%RAYLIB_PATH%\include" -L "%RAYLIB_PATH%\lib" main.cpp -lraylib -lwinmm -lgdi32 -o bin\{GameName}.exe

if %ERRORLEVEL% EQU 0 (
    echo Build successful!
    if exist "%RAYLIB_PATH%\lib\raylib.dll" copy "%RAYLIB_PATH%\lib\raylib.dll" "bin\" >nul 2>&1
    bin\{GameName}.exe
) else (
    echo Build failed!
    pause & exit /b 1
)
pause
```

---

## Part 3: Python Embed Wrapper ({gamename}_embed.py)

Create `Data/games/{gamename}_embed.py` with this template:

```python
"""Embedded {GameName} - loads C++ DLL and provides framebuffer access."""

import ctypes
import os
import pygame
import sys
import time
from typing import Optional, Tuple

_dll = None
_dll_path = None
_PRESET_MAP = {"low": 0, "medium": 1, "high": 2}
_render_preset: Optional[int] = None
_requested_resolution: Optional[Tuple[int, int]] = None

print(f"DEBUG: Loaded {gamename}_embed module from {__file__}")


def _find_dll() -> Optional[str]:
    """Find the game DLL."""
    try:
        base_path = os.path.dirname(os.path.abspath(__file__))
    except NameError:
        base_path = os.getcwd()

    # Environment variable override for CI/debugging
    override = os.environ.get("{GAMENAME_UPPER}_DLL_PATH", "").strip()
    if override and os.path.exists(override):
        return os.path.abspath(override)

    dll_paths = [
        os.path.join(base_path, "{GameName}", "{gamename}.dll"),
        os.path.join("Data", "games", "{GameName}", "{gamename}.dll"),
        "{gamename}.dll",
    ]
    for path in dll_paths:
        if os.path.exists(path):
            return os.path.abspath(path)
    print("DEBUG: {gamename}.dll NOT FOUND")
    return None


def _get_requested_preset() -> int:
    global _render_preset
    if _render_preset is not None:
        return _render_preset
    env_value = os.environ.get("{GAMENAME_UPPER}_RESOLUTION", "").strip().lower()
    if env_value == "auto":
        return 2
    return _PRESET_MAP.get(env_value, 1)


def set_resolution_mode(mode: str) -> bool:
    global _render_preset, _requested_resolution
    if not mode:
        return False
    preset = _PRESET_MAP.get(mode.strip().lower())
    if preset is None:
        return False
    _render_preset = preset
    _requested_resolution = None
    if _dll is not None and getattr(_dll, "_has_resolution_preset", False):
        try:
            _dll.SetRenderResolutionPreset(preset)
        except Exception:
            pass
    return True


def set_render_resolution(width: int, height: int) -> bool:
    global _requested_resolution, _render_preset
    try:
        width = max(320, int(width))
        height = max(200, int(height))
    except (TypeError, ValueError):
        return False
    _requested_resolution = (width, height)
    _render_preset = None
    if _dll is not None and getattr(_dll, "_has_resolution", False):
        try:
            _dll.SetRenderResolution(width, height)
        except Exception:
            pass
    return True


def initialize() -> bool:
    """Initialize the embedded game DLL."""
    global _dll, _dll_path

    if _dll is not None:
        return True

    _dll_path = _find_dll()
    if not _dll_path:
        print("ERROR: {gamename}.dll not found")
        return False

    # Staleness check
    try:
        mtime = os.path.getmtime(_dll_path)
        cpp_path = os.path.join(os.path.dirname(_dll_path), "main.cpp")
        if os.path.exists(cpp_path) and mtime < os.path.getmtime(cpp_path):
            print("[{gamename}_embed] WARNING: DLL is older than main.cpp - rebuild!")
    except Exception:
        pass

    dll_dir = os.path.dirname(_dll_path)

    if hasattr(os, 'add_dll_directory'):
        try:
            os.add_dll_directory(dll_dir)
        except Exception:
            pass
    os.environ['PATH'] = dll_dir + os.pathsep + os.environ['PATH']

    cwd = os.getcwd()
    try:
        os.chdir(dll_dir)

        # Pre-load MinGW runtime + Raylib dependencies
        for dep in ["libgcc_s_seh-1.dll", "libstdc++-6.dll", "libwinpthread-1.dll", "raylib.dll"]:
            if os.path.exists(dep):
                try:
                    ctypes.CDLL(dep)
                except Exception:
                    pass

        _dll = ctypes.CDLL(_dll_path)

        # ── Required function signatures ──
        _dll.InitializeGame.restype = ctypes.c_bool
        _dll.InitializeGame.argtypes = []
        _dll.GetFrameBuffer.restype = ctypes.POINTER(ctypes.c_ubyte)
        _dll.GetFrameBuffer.argtypes = []
        _dll.GetWidth.restype = ctypes.c_int
        _dll.GetWidth.argtypes = []
        _dll.GetHeight.restype = ctypes.c_int
        _dll.GetHeight.argtypes = []
        _dll.UpdateFrame.restype = None
        _dll.UpdateFrame.argtypes = []
        _dll.SetKeyState.restype = None
        _dll.SetKeyState.argtypes = [ctypes.c_int, ctypes.c_bool]
        _dll.SetMouseButtonState.restype = None
        _dll.SetMouseButtonState.argtypes = [ctypes.c_int, ctypes.c_bool]
        _dll.SetInputMousePosition.restype = None
        _dll.SetInputMousePosition.argtypes = [ctypes.c_float, ctypes.c_float]
        _dll.SetMouseDelta.restype = None
        _dll.SetMouseDelta.argtypes = [ctypes.c_float, ctypes.c_float]

        # ── Optional resolution (before InitializeGame!) ──
        for attr, rtype, atypes, flag in [
            ("SetRenderResolution", None, [ctypes.c_int, ctypes.c_int], "_has_resolution"),
            ("SetRenderResolutionPreset", None, [ctypes.c_int], "_has_resolution_preset"),
        ]:
            try:
                func = getattr(_dll, attr)
                func.restype = rtype
                func.argtypes = atypes
                setattr(_dll, flag, True)
            except AttributeError:
                setattr(_dll, flag, False)

        # Apply resolution BEFORE InitializeGame
        resolution_applied = False
        if _requested_resolution and getattr(_dll, "_has_resolution", False):
            try:
                _dll.SetRenderResolution(*_requested_resolution)
                resolution_applied = True
            except Exception:
                pass
        if not resolution_applied and getattr(_dll, "_has_resolution_preset", False):
            try:
                _dll.SetRenderResolutionPreset(_get_requested_preset())
            except Exception:
                pass

        if not _dll.InitializeGame():
            print("ERROR: Failed to initialize game")
            return False

        # ── Optional exports (after InitializeGame) ──
        _setup_optional_functions()

        print("{GameName} initialized successfully")
        return True

    except AttributeError as e:
        print(f"ERROR: Required function not found in DLL: {e}")
        return False
    except Exception as e:
        print(f"ERROR: Failed to load {gamename}.dll: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        os.chdir(cwd)


def _setup_optional_functions():
    """Set up optional DLL functions (won't fail if missing)."""
    optional_funcs = [
        ("ShouldExit",          ctypes.c_bool, [], "_has_should_exit"),
        ("ShouldCenterMouse",   ctypes.c_bool, [], "_has_center_mouse"),
        ("SetMouseWheelMove",   None, [ctypes.c_float], "_has_mouse_wheel"),
        ("GetLastFinalScore",   ctypes.c_int, [], "_has_get_score"),
        ("SetUsername",         None, [ctypes.c_char_p], "_has_set_username"),
        ("ResetGame",          None, [], "_has_reset_game"),
        ("SaveGameData",       None, [], "_has_save_game"),
        ("LoadGameData",       ctypes.c_bool, [], "_has_load_game"),
        ("CleanupGame",        None, [], "_has_cleanup"),
        ("SetCharInput",       None, [ctypes.c_int], "_has_char_input"),
    ]
    for name, rtype, atypes, flag in optional_funcs:
        setattr(_dll, flag, False)
        try:
            func = getattr(_dll, name, None)
            if func is not None:
                func.restype = rtype
                func.argtypes = atypes
                setattr(_dll, flag, True)
        except (AttributeError, OSError, TypeError):
            pass


def get_frame_surface() -> Optional[pygame.Surface]:
    """Get the current frame as a pygame Surface."""
    if _dll is None:
        if not initialize():
            return None
    try:
        _dll.UpdateFrame()
        width = _dll.GetWidth()
        height = _dll.GetHeight()
        if width <= 0 or height <= 0:
            return None

        ptr = _dll.GetFrameBuffer()
        if not ptr:
            return None

        size = width * height * 4
        address = ctypes.addressof(ptr.contents)
        array_type = ctypes.c_ubyte * size
        buf_view = memoryview(array_type.from_address(address))

        surf = pygame.image.frombuffer(buf_view, (width, height), "RGBA")
        surf = pygame.transform.flip(surf, False, True)  # OpenGL Y-flip
        return surf.convert()  # Opaque - avoids alpha=0 black-frame bugs
    except Exception as e:
        print(f"[{gamename}_embed] ERROR: {e}")
        return None


def get_size() -> Tuple[int, int]:
    if _dll is None:
        if not initialize():
            return (0, 0)
    try:
        return (_dll.GetWidth(), _dll.GetHeight())
    except Exception:
        return (0, 0)


# ── Input functions ──
def set_key_state(key: int, down: bool):
    if _dll:
        try: _dll.SetKeyState(key, down)
        except Exception: pass

def set_char_input(codepoint: int):
    if _dll and getattr(_dll, "_has_char_input", False):
        try: _dll.SetCharInput(int(codepoint))
        except Exception: pass

def set_mouse_button_state(button: int, down: bool):
    if _dll:
        try: _dll.SetMouseButtonState(button, down)
        except Exception: pass

def set_mouse_position(x: float, y: float):
    if _dll:
        try: _dll.SetInputMousePosition(x, y)
        except Exception: pass

def set_mouse_delta(dx: float, dy: float):
    if _dll:
        try: _dll.SetMouseDelta(dx, dy)
        except Exception: pass

def set_mouse_wheel(move: float):
    if _dll and getattr(_dll, "_has_mouse_wheel", False):
        try: _dll.SetMouseWheelMove(move)
        except Exception: pass


# ── Game state functions ──
def should_exit() -> bool:
    if _dll and getattr(_dll, "_has_should_exit", False):
        try: return _dll.ShouldExit()
        except Exception: pass
    return False

def should_center_mouse() -> bool:
    if _dll and getattr(_dll, "_has_center_mouse", False):
        try: return _dll.ShouldCenterMouse()
        except Exception: pass
    return False

def get_last_final_score() -> int:
    if _dll and getattr(_dll, "_has_get_score", False):
        try: return _dll.GetLastFinalScore()
        except Exception: pass
    return 0

def set_username(username: str) -> bool:
    if _dll and getattr(_dll, "_has_set_username", False):
        try:
            _dll.SetUsername(username.encode('utf-8'))
            return True
        except Exception: pass
    return False

def reset_game() -> bool:
    if _dll and getattr(_dll, "_has_reset_game", False):
        try:
            _dll.ResetGame()
            return True
        except Exception: pass
    return False

def cleanup():
    global _dll
    try:
        if _dll and getattr(_dll, "_has_cleanup", False):
            _dll.CleanupGame()
    except Exception:
        pass
    _dll = None
```

---

## Part 4: Session Adapter (in registry.py)

Add a new session class to `Data/games/registry.py`:

```python
class {GameName}Session(BaseGameSession):
    """Session adapter for {GameName} using headless framebuffer rendering."""

    KEY_MAP = {
        pygame.K_UP: 265, pygame.K_DOWN: 264,
        pygame.K_LEFT: 263, pygame.K_RIGHT: 262,
        pygame.K_SPACE: 32, pygame.K_RETURN: 257, pygame.K_ESCAPE: 256,
        pygame.K_a: 65, pygame.K_b: 66, pygame.K_c: 67, pygame.K_d: 68,
        pygame.K_e: 69, pygame.K_f: 70, pygame.K_g: 71, pygame.K_h: 72,
        pygame.K_i: 73, pygame.K_j: 74, pygame.K_k: 75, pygame.K_l: 76,
        pygame.K_m: 77, pygame.K_n: 78, pygame.K_o: 79, pygame.K_p: 80,
        pygame.K_q: 81, pygame.K_r: 82, pygame.K_s: 83, pygame.K_t: 84,
        pygame.K_u: 85, pygame.K_v: 86, pygame.K_w: 87, pygame.K_x: 88,
        pygame.K_y: 89, pygame.K_z: 90,
        pygame.K_0: 48, pygame.K_1: 49, pygame.K_2: 50, pygame.K_3: 51,
        pygame.K_4: 52, pygame.K_5: 53, pygame.K_6: 54, pygame.K_7: 55,
        pygame.K_8: 56, pygame.K_9: 57,
        pygame.K_MINUS: 45, pygame.K_EQUALS: 61,
        pygame.K_BACKSPACE: 259,
        pygame.K_LSHIFT: 340, pygame.K_RSHIFT: 344,
        pygame.K_LCTRL: 341, pygame.K_RCTRL: 345,
    }

    MOUSE_BUTTON_MAP = {1: 0, 3: 1, 2: 2}

    def __init__(self, app: "GlyphisIOBBS"):
        super().__init__(app)
        self.embed_module = None
        self.last_frame: Optional[pygame.Surface] = None
        self.last_mouse_pos = (0, 0)
        self.baseline_desktop_x = 176
        self.baseline_desktop_y = 209
        self._cursor_hidden_for_game = False

    def _get_desktop_pos(self) -> Tuple[int, int]:
        return self.app.res_manager.coords(self.baseline_desktop_x, self.baseline_desktop_y)

    def _load_base_desktop_size(self) -> Tuple[int, int]:
        if getattr(self, "_base_desktop_size", None):
            return self._base_desktop_size
        try:
            img = pygame.image.load(os.path.join("Data", "OS", "Desktop-Enviroment.png"))
            self._base_desktop_size = img.get_size()
        except Exception:
            self._base_desktop_size = (self.app.bbs_width, self.app.bbs_height)
        return self._base_desktop_size

    def _get_desktop_dimensions(self) -> Tuple[int, int]:
        if hasattr(self.app, "os_mode") and self.app.os_mode and hasattr(self.app.os_mode, "desktop_size"):
            ds = self.app.os_mode.desktop_size
            if ds:
                try: return (int(ds[0]), int(ds[1]))
                except (TypeError, ValueError): pass
        base_w, base_h = self._load_base_desktop_size()
        w = self.app.res_manager.scale(base_w)
        h = self.app.res_manager.scale(base_h)
        return (max(720, w), max(480, h))

    def _compute_presented_frame_rect(self, dx, dy, dw, dh, fw, fh):
        if fw <= 0 or fh <= 0 or dw <= 0 or dh <= 0:
            return (dx, dy, max(1, dw), max(1, dh))
        scale = min(dw / fw, dh / fh)
        draw_w = max(1, int(fw * scale))
        draw_h = max(1, int(fh * scale))
        return (dx + (dw - draw_w) // 2, dy + (dh - draw_h) // 2, draw_w, draw_h)

    def _get_game_mouse_pos(self, screen_pos):
        dx, dy = self._get_desktop_pos()
        dw, dh = self._get_desktop_dimensions()
        if self.embed_module:
            gw, gh = self.embed_module.get_size()
            if gw > 0 and gh > 0:
                rx, ry, rw, rh = self._compute_presented_frame_rect(dx, dy, dw, dh, gw, gh)
                game_x = ((screen_pos[0] - rx) / rw) * gw
                game_y = ((screen_pos[1] - ry) / rh) * gh
                return (max(0.0, min(float(gw), game_x)), max(0.0, min(float(gh), game_y)))
        return (float(screen_pos[0] - dx), float(screen_pos[1] - dy))

    def _get_presented_game_rect(self):
        dx, dy = self._get_desktop_pos()
        dw, dh = self._get_desktop_dimensions()
        fw = fh = 0
        if self.last_frame:
            fw, fh = self.last_frame.get_size()
        elif self.embed_module:
            fw, fh = self.embed_module.get_size()
        rx, ry, rw, rh = self._compute_presented_frame_rect(dx, dy, dw, dh, fw, fh)
        return pygame.Rect(rx, ry, rw, rh)

    def _is_mouse_over_game(self, pos):
        return self._get_presented_game_rect().collidepoint(pos)

    def _set_game_cursor_capture(self, capture):
        if capture != self._cursor_hidden_for_game:
            pygame.mouse.set_visible(not capture)
            self._cursor_hidden_for_game = capture

    def enter(self) -> None:
        try:
            from . import {gamename}_embed
            self.embed_module = {gamename}_embed

            desktop_w, desktop_h = self._get_desktop_dimensions()
            if hasattr({gamename}_embed, "set_render_resolution"):
                {gamename}_embed.set_render_resolution(desktop_w, desktop_h)

            if hasattr(self.app, 'get_active_user'):
                user = self.app.get_active_user()
                if user and user.get('username'):
                    {gamename}_embed.set_username(user['username'])

            if not {gamename}_embed.initialize():
                self.exit_requested = True
                return

            self._set_game_cursor_capture(True)
        except Exception as e:
            print(f"[{GameName}Session] Init failed: {e}")
            self.exit_requested = True

    def handle_event(self, event):
        if not self.embed_module:
            return None

        if event.type == pygame.KEYDOWN:
            rk = self.KEY_MAP.get(event.key)
            if rk is not None:
                self.embed_module.set_key_state(rk, True)
        elif event.type == pygame.KEYUP:
            rk = self.KEY_MAP.get(event.key)
            if rk is not None:
                self.embed_module.set_key_state(rk, False)
        elif event.type == pygame.TEXTINPUT:
            if self._is_mouse_over_game(pygame.mouse.get_pos()):
                for ch in event.text:
                    self.embed_module.set_char_input(ord(ch))

        if event.type == pygame.MOUSEBUTTONDOWN:
            if not self._is_mouse_over_game(event.pos):
                self._set_game_cursor_capture(False)
                return None
            self._set_game_cursor_capture(True)
            rb = self.MOUSE_BUTTON_MAP.get(event.button)
            if rb is not None:
                self.embed_module.set_mouse_button_state(rb, True)
                gp = self._get_game_mouse_pos(event.pos)
                self.embed_module.set_mouse_position(gp[0], gp[1])
            if event.button == 4:
                self.embed_module.set_mouse_wheel(1.0)
            elif event.button == 5:
                self.embed_module.set_mouse_wheel(-1.0)
        elif event.type == pygame.MOUSEBUTTONUP:
            rb = self.MOUSE_BUTTON_MAP.get(event.button)
            if rb is not None:
                self.embed_module.set_mouse_button_state(rb, False)

        if event.type == pygame.MOUSEMOTION:
            if not self._is_mouse_over_game(event.pos):
                self._set_game_cursor_capture(False)
                self.embed_module.set_mouse_delta(0.0, 0.0)
                return None
            self._set_game_cursor_capture(True)
            dx, dy = float(event.rel[0]), float(event.rel[1]) if hasattr(event, 'rel') and event.rel else (0.0, 0.0)
            self.embed_module.set_mouse_delta(dx, dy)
            gp = self._get_game_mouse_pos(event.pos)
            self.embed_module.set_mouse_position(gp[0], gp[1])
            self.last_mouse_pos = event.pos

        if event.type == pygame.MOUSEWHEEL:
            if self._is_mouse_over_game(pygame.mouse.get_pos()):
                self.embed_module.set_mouse_wheel(float(event.y))

        return None

    def update(self, dt: float) -> None:
        if not self.embed_module:
            return

        rel_x, rel_y = pygame.mouse.get_rel()
        if abs(rel_x) > 0.01 or abs(rel_y) > 0.01:
            self.embed_module.set_mouse_delta(float(rel_x), float(rel_y))
        else:
            self.embed_module.set_mouse_delta(0.0, 0.0)

        mouse_pos = pygame.mouse.get_pos()
        over_game = self._is_mouse_over_game(mouse_pos)
        self._set_game_cursor_capture(over_game)
        if over_game:
            gp = self._get_game_mouse_pos(mouse_pos)
            self.embed_module.set_mouse_position(gp[0], gp[1])
        self.last_mouse_pos = mouse_pos

        if hasattr(self.embed_module, 'should_center_mouse') and self.embed_module.should_center_mouse():
            dx, dy = self._get_desktop_pos()
            dw, dh = self._get_desktop_dimensions()
            pygame.mouse.set_pos(dx + dw // 2, dy + dh // 2)
            pygame.mouse.get_rel()

        if self.embed_module.should_exit():
            self.exit_requested = True

        try:
            self.last_frame = self.embed_module.get_frame_surface()
        except Exception as e:
            print(f"[{GameName}Session] Frame error: {e}")

    def draw(self) -> None:
        pass  # Drawing via get_game_frame()

    def get_game_frame(self):
        if not self.last_frame:
            return None
        dx, dy = self._get_desktop_pos()
        dw, dh = self._get_desktop_dimensions()
        fw, fh = self.last_frame.get_size()
        rx, ry, rw, rh = self._compute_presented_frame_rect(dx, dy, dw, dh, fw, fh)
        if (fw, fh) != (rw, rh):
            scaled = pygame.transform.smoothscale(self.last_frame, (rw, rh))
        else:
            scaled = self.last_frame
        return (scaled, (rx, ry))

    def exit(self) -> None:
        self._set_game_cursor_capture(False)
        if self.embed_module:
            try: self.embed_module.cleanup()
            except Exception: pass
        self.embed_module = None
        self.last_frame = None
```

### Register in GAME_DEFINITIONS

```python
GameDefinition(
    id="{game_id}",
    title="{GAME TITLE}",
    description="Description of the game.",
    tokens_required=[Tokens.{GAME_TOKEN}],  # Or [] for no unlock requirement
    session_factory={GameName}Session,
),
```

---

## Part 5: Critical Rules and Gotchas

### Rendering Rules
1. **BeginTextureMode/EndTextureMode** in DLL mode - NEVER use BeginDrawing/EndDrawing
2. **Clamp GetFrameTime()** - can return 0 in hidden-window mode, causing stuck splash screens
3. **Keep render resolution LOW** - 600x400 or 720x480. glReadPixels is the bottleneck
4. **Flip Y in Python** - OpenGL renders upside-down vs pygame convention
5. **Use surf.convert() not convert_alpha()** - some GPUs leave alpha=0 causing black frames

### Input Rules
1. **ALWAYS use Custom* input wrappers** in C++ - raw raylib input won't work with hidden window
2. **Clear one-shot flags each frame** via ClearInputFrame()
3. **Pygame->Raylib key mapping** is critical: pygame.K_a=97 -> Raylib KEY_A=65
4. **Mouse buttons differ**: Pygame 1/2/3=L/M/R, Raylib 0/1/2=L/R/M

### Build Rules
1. **DLL build** uses `-shared` and `-lraylibdll` (dynamic linking)
2. **EXE build** uses `-lraylib` (static linking)
3. **CWD must be DLL directory** during InitializeGame for resource loading
4. **Restore CWD** in Python's finally block after initialization
5. **Pre-load MinGW runtime DLLs** before loading game DLL

### Desktop Positioning
1. **Baseline coordinates**: desktop_x=176, desktop_y=209 (at 2560x1440)
2. Use `self.app.res_manager.coords()` to scale to current resolution
3. Get desktop dimensions from `self.app.os_mode.desktop_size` or fallback to Desktop-Enviroment.png
4. Aspect-fit scale the game frame into the desktop rect

### Screen Zoom (Shift++ / Shift+-)
The BBS has a global screen zoom feature. Games must be aware of how it works:

1. **Zoom keys**: `Shift+=` (or `Shift++`) zooms in, `Shift+-` (or `Shift+_`) zooms out. These are intercepted in `main.py`'s event loop **before** the game session's `handle_event()`, so the game never receives these keys.
2. **Game zoom pipeline**: During game sessions, the zoom uses a **lightweight crop-and-scale** instead of the full-screen 2x pipeline. It grabs just the desktop region via `subsurface().copy()` and scales it to fill the screen. This avoids the FPS hit that would throttle `UpdateFrame()` calls.
3. **Hotkey conflicts**: If your game needs its own zoom (e.g. CyberTrain's map zoom), use a different combo like `Ctrl+Shift++/-` or mouse wheel. `Shift++/-` is reserved for BBS zoom.
4. **Mouse coordinates**: When zoom is active, mouse events are transformed to unzoomed coordinates via `_transform_event_for_zoom()` before reaching the game session. Games receive correct positions without needing zoom awareness.
5. **Cursor behaviour**: During zoom, the system cursor is hidden. In OS Mode the OS sprite cursor is drawn at unzoomed coordinates. In BBS states no cursor is shown (keyboard-only). Game sessions handle their own cursor visibility via `_set_game_cursor_capture()`.

### Token System
- Add token constant to `tokens.py` if game requires unlock
- Grant tokens in session's update() or exit() methods when milestones are reached
- Use `self.app.grant_token(Tokens.TOKEN_NAME, reason="...")` to grant
