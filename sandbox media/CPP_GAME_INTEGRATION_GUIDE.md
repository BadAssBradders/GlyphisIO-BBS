# Complete C++ Game Integration Guide for GlyphisIO BBS

## Overview

This guide explains **exactly** how to integrate a C++ game (like Astro Miner or CyberTrain) into the GlyphisIO BBS system. The architecture uses a **DLL-based framebuffer sharing** approach where:

1. The C++ game renders to an **offscreen texture** (not a visible window)
2. Python loads the DLL and reads the framebuffer each frame via `ctypes`
3. Pygame displays the framebuffer at the **OS Desktop position** within the BBS
4. Input is forwarded from Pygame to the DLL via exported functions

This creates a seamless "game within the BBS" experience.

### Embedded Launch Checklist (Critical)

1. Build the DLL used by BBS, not the standalone EXE path.
2. Use `build_dll.bat` for BBS validation; `build_and_run.bat` is standalone-only.
3. Every `BeginTextureMode(g_framebuffer)` in embedded mode must close with `EndTextureMode()` (never `EndDrawing()`).
4. Keep render + input using the same presented rectangle (same scale + offset math on Python side).
5. If you get "black frame + cursor visible", treat alpha as suspect:
   - The framebuffer RGB may be valid while alpha is zero.
   - In Python, prefer an opaque `Surface` for final blit (`convert()`), unless your game explicitly guarantees alpha is fully authored.
6. Define hotkey ownership explicitly between BBS and game:
   - BBS global zoom: `Shift + =` zooms in, `Shift + -` zooms out. These are intercepted in `main.py` before the game session handler, so the game never receives them.
   - During game sessions, zoom uses a lightweight **crop-and-scale of just the desktop region** (not the full screen), so C++ game tick rate is unaffected.
   - If a game also needs zoom (e.g. CyberTrain map zoom), use a different combo (e.g. `Ctrl + Shift + +/-` or mouse wheel). `Shift + +/-` is reserved for BBS zoom.
   - Mouse events are automatically transformed to unzoomed coordinates when zoom is active (`_transform_event_for_zoom()`), so game input stays correct.
7. In embedded splash/startup phases, clamp invalid frame delta:
   - `GetFrameTime()` may return `0` in hidden-window mode.
   - If your splash/transition timers depend on `dt`, clamp to a sane default (e.g. `1/60`) or splash can remain black forever.

> **Reference Implementations:** See `astrominer_embed.py`, `cybertrain_embed.py`, and their corresponding C++ `main.cpp` files for working examples.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         main.py (Pygame)                            │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐  │
│  │ Desktop Video   │ -> │ OS Mode Desktop │ -> │ Game Frame      │  │
│  │ (mp4 background)│    │ (UI overlay)    │    │ (from DLL)      │  │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘  │
│           │                      │                      │           │
│           ▼                      ▼                      ▼           │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                    screen.blit() layers                     │    │
│  │  1. Video background (desktop_steam.mp4)                    │    │
│  │  2. OS Mode desktop environment                             │    │
│  │  3. BLACK rectangle at desktop_x, desktop_y                 │    │
│  │  4. Game frame from get_game_frame() at desktop position    │    │
│  │  5. Scanline overlay                                        │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ ctypes
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        game_embed.py                                │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐  │
│  │ initialize()    │    │ get_frame_      │    │ set_key_state() │  │
│  │ Load DLL        │    │ surface()       │    │ set_mouse_*()   │  │
│  │ Setup ctypes    │    │ Read pixels     │    │ Forward input   │  │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ DLL exports
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        game_main.cpp (DLL)                          │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐  │
│  │ InitializeGame  │    │ UpdateFrame()   │    │ GetFrameBuffer  │  │
│  │ Create window   │    │ Game logic      │    │ Return pixels   │  │
│  │ (HIDDEN!)       │    │ Render to       │    │                 │  │
│  │ Load resources  │    │ g_framebuffer   │    │                 │  │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘  │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                    RenderTexture2D g_framebuffer            │    │
│  │  - All rendering goes here via BeginTextureMode()           │    │
│  │  - Never call BeginDrawing()/EndDrawing() in DLL mode       │    │
│  │  - Pixels read via GetFrameBuffer() each frame              │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Part 1: The C++ Side (DLL)

### 1.1 Required DLL Export Functions

Your C++ game **MUST** export these functions using `__declspec(dllexport)`:

```cpp
#ifdef __cplusplus
extern "C" {
#endif

// ══════════════════════════════════════════════════════════════════
// REQUIRED EXPORTS - The BBS will not function without these
// ══════════════════════════════════════════════════════════════════
// Note: __cdecl is the default calling convention for g++ on Windows,
// so it can be omitted. These are listed here for clarity.

// Initialize the game (create hidden window, load resources, setup framebuffer)
__declspec(dllexport) bool InitializeGame();

// Run one frame of the game (update + render to framebuffer)
__declspec(dllexport) void UpdateFrame();

// Get pointer to RGBA pixel data (width * height * 4 bytes)
__declspec(dllexport) unsigned char* GetFrameBuffer();

// Get framebuffer dimensions
__declspec(dllexport) int GetWidth();
__declspec(dllexport) int GetHeight();

// Input handling - called by Python to forward pygame events
__declspec(dllexport) void SetKeyState(int key, bool down);
__declspec(dllexport) void SetMouseButtonState(int button, bool down);
__declspec(dllexport) void SetInputMousePosition(float x, float y);
__declspec(dllexport) void SetMouseDelta(float dx, float dy);
__declspec(dllexport) void SetMouseWheelMove(float move);

// ══════════════════════════════════════════════════════════════════
// OPTIONAL EXPORTS - Enhance functionality but not strictly required
// Python checks for these with getattr() and _has_* flags
// ══════════════════════════════════════════════════════════════════

// Check if game wants to exit (e.g., user selected "Quit" from menu)
__declspec(dllexport) bool ShouldExit();

// Check if mouse should be centered (for 3D/FPS controls)
__declspec(dllexport) bool ShouldCenterMouse();

// Clean up resources (called when exiting game session)
__declspec(dllexport) void CleanupGame();

// Set render resolution BEFORE InitializeGame() is called
// Presets: 0=low (480x320), 1=medium (600x400), 2=high (720x480)
__declspec(dllexport) void SetRenderResolution(int width, int height);
__declspec(dllexport) void SetRenderResolutionPreset(int preset);

// Game state management
__declspec(dllexport) void ResetGame();              // Reset to new game defaults
__declspec(dllexport) void SetUsername(const char* username);  // For leaderboard
__declspec(dllexport) int GetLastFinalScore();       // For leaderboard upload
__declspec(dllexport) void SaveGameData();           // Persist to file
__declspec(dllexport) bool LoadGameData();           // Load from file

#ifdef __cplusplus
}
#endif
```

### 1.2 Global State Variables

```cpp
// ══════════════════════════════════════════════════════════════════
// GLOBAL STATE - Required for framebuffer approach
// ══════════════════════════════════════════════════════════════════

// The offscreen render texture - ALL rendering goes here
RenderTexture2D g_framebuffer = {0};
bool g_framebuffer_initialized = false;

// Pixel buffer for Python to read
unsigned char* g_frame_buffer_data = NULL;
int g_frame_buffer_size = 0;

// Game initialization state
bool g_game_initialized = false;

// ══════════════════════════════════════════════════════════════════
// RENDER RESOLUTION - Key for performance!
// ══════════════════════════════════════════════════════════════════
// Rendering at full desktop resolution (1200x800+) is TOO SLOW because
// glReadPixels (GPU->CPU transfer) is the bottleneck.
// 
// Solution: Render at LOW resolution, Python scales it up via smoothscale.
// Astro Miner uses 600x400 (medium preset) or 720x480 (high preset).

int g_dynamicRenderWidth = 600;   // Render width (can be set before init)
int g_dynamicRenderHeight = 400;  // Render height
#define RENDER_WIDTH g_dynamicRenderWidth
#define RENDER_HEIGHT g_dynamicRenderHeight

// Virtual resolution for UI coordinate calculations
#define VIRTUAL_WIDTH 1200
#define VIRTUAL_HEIGHT 800

// ══════════════════════════════════════════════════════════════════
// INPUT STATE - Tracked manually since window is hidden
// ══════════════════════════════════════════════════════════════════

struct InputState {
    bool keys[512];              // KEY_* enum values (held state)
    bool keysPressed[512];       // One-time press events (cleared each frame)
    bool keysReleased[512];      // One-time release events (cleared each frame)
    bool mouseButtons[8];        // Mouse button held state
    bool mouseButtonsPressed[8]; // One-time click events
    bool mouseButtonsReleased[8];// One-time release events
    Vector2 mousePosition;       // Current mouse position
    Vector2 mouseDelta;          // Mouse movement this frame
    float mouseWheelMove;        // Mouse wheel movement this frame
} g_inputState = {0};

// Exit request flag (set when user wants to quit)
bool g_exit_requested = false;

// Mouse centering request (for 3D controls)
bool g_shouldCenterMouse = false;

// ══════════════════════════════════════════════════════════════════
// CRITICAL: Standalone mode flag - determines input source
// ══════════════════════════════════════════════════════════════════
// When true (standalone exe): Use raylib's built-in input functions
// When false (embedded DLL): Use g_inputState populated by Python
bool g_standalone_mode = true;
```

### 1.3 InitializeGame() Implementation

```cpp
__declspec(dllexport) bool InitializeGame() {
    // ══════════════════════════════════════════════════════════════
    // CRITICAL: Set standalone mode to FALSE
    // ══════════════════════════════════════════════════════════════
    // This switches all Custom* input functions to read from g_inputState
    // instead of calling raylib's built-in input functions.
    g_standalone_mode = false;
    
    // ══════════════════════════════════════════════════════════════
    // CRITICAL: Create a HIDDEN window
    // ══════════════════════════════════════════════════════════════
    // The window is required for OpenGL context but must be hidden
    // so it doesn't steal focus from the BBS.
    
    SetConfigFlags(FLAG_WINDOW_HIDDEN | FLAG_WINDOW_UNDECORATED);
    
    // Window size doesn't matter much since it's hidden
    // Use virtual resolution for internal coordinate space
    InitWindow(VIRTUAL_WIDTH, VIRTUAL_HEIGHT, "Game (Embedded)");
    SetTargetFPS(0);  // No FPS limit - BBS controls timing
    
    // Initialize audio device (raylib handles this)
    InitAudioDevice();
    g_audio_initialized = true;
    
    // ══════════════════════════════════════════════════════════════
    // CREATE THE OFFSCREEN FRAMEBUFFER
    // ══════════════════════════════════════════════════════════════
    // This is where ALL rendering goes. The texture is read back
    // to CPU memory each frame for Python to display.
    // 
    // Note: g_renderWidth/g_renderHeight can be set by Python
    // via SetRenderResolution() BEFORE InitializeGame() is called.
    
    g_framebuffer = LoadRenderTexture(g_renderWidth, g_renderHeight);
    g_framebuffer_initialized = true;
    
    printf("[InitializeGame] Created framebuffer: %dx%d\n", 
           g_renderWidth, g_renderHeight);
    
    // ══════════════════════════════════════════════════════════════
    // LOAD RESOURCES
    // ══════════════════════════════════════════════════════════════
    // Python changes CWD to DLL directory before calling InitializeGame,
    // so relative paths should work directly.
    
    // Load custom font (falls back to default if not found)
    g_gameFont = LoadFont("PixelifySans.ttf");
    if (g_gameFont.texture.id == 0) {
        printf("[InitializeGame] Custom font not found, using default\n");
        g_gameFont = GetFontDefault();
    }
    
    // Load textures
    const char* texturePaths[] = {
        "sprite.png",                          // Same folder as DLL
        "Data/games/YourGame/sprite.png",      // From repo root
    };
    
    bool loaded = false;
    for (int i = 0; i < 2 && !loaded; i++) {
        Texture2D tex = LoadTexture(texturePaths[i]);
        if (tex.id > 0) {
            // Store texture in global variable
            g_spriteTexture = tex;
            loaded = true;
            printf("[InitializeGame] Loaded texture from: %s\n", texturePaths[i]);
        }
    }
    
    // Load sounds, models similarly...
    
    // ══════════════════════════════════════════════════════════════
    // INITIALIZE GAME STATE
    // ══════════════════════════════════════════════════════════════
    g_playerScore = 0;
    g_playerHealth = 100;
    // Initialize all game state to defaults...
    
    g_game_initialized = true;
    return g_framebuffer_initialized && g_game_initialized;
}
```

### 1.4 UpdateFrame() Implementation

```cpp
__declspec(dllexport) __cdecl void UpdateFrame() {
    // ══════════════════════════════════════════════════════════════
    // SAFETY CHECK
    // ══════════════════════════════════════════════════════════════
    if (!g_framebuffer_initialized || !g_game_initialized) {
        return;
    }
    
    // ══════════════════════════════════════════════════════════════
    // TIME DELTA CALCULATION
    // ══════════════════════════════════════════════════════════════
    float dt = GetFrameTime();
    if (dt <= 0.0f || dt > 0.1f) {
        dt = 1.0f / 60.0f;  // Clamp to reasonable value
    }
    
    // ══════════════════════════════════════════════════════════════
    // UPDATE GAME LOGIC
    // ══════════════════════════════════════════════════════════════
    // Use custom input functions that read from g_inputState
    // (raylib's built-in input won't work with hidden window!)
    
    UpdateGameLogic(dt);
    UpdateMusicStream(g_backgroundMusic);  // Keep music playing
    
    // ══════════════════════════════════════════════════════════════
    // RENDER TO FRAMEBUFFER (Not to screen!)
    // ══════════════════════════════════════════════════════════════
    // CRITICAL: Use BeginTextureMode, NOT BeginDrawing!
    
    BeginTextureMode(g_framebuffer);
    ClearBackground(BLACK);
    
    // Scale from virtual coordinates to render coordinates
    float scaleX = (float)RENDER_WIDTH / (float)VIRTUAL_WIDTH;
    float scaleY = (float)RENDER_HEIGHT / (float)VIRTUAL_HEIGHT;
    
    // Use Camera2D for proper scaling
    Camera2D cam = {0};
    cam.zoom = scaleX;  // Assuming square pixels
    
    BeginMode2D(cam);
    
    // === YOUR GAME RENDERING CODE HERE ===
    // Draw everything as if rendering to VIRTUAL_WIDTH x VIRTUAL_HEIGHT
    // The Camera2D will scale it down to RENDER_WIDTH x RENDER_HEIGHT
    
    DrawYourGame();
    
    EndMode2D();
    EndTextureMode();  // NOT EndDrawing!
    
    // ══════════════════════════════════════════════════════════════
    // CLEAR INPUT FRAME FLAGS
    // ══════════════════════════════════════════════════════════════
    // Clear the "pressed this frame" flags so they only trigger once
    
    ClearInputFrame();
}
```

### 1.5 GetFrameBuffer() Implementation

```cpp
__declspec(dllexport) __cdecl unsigned char* GetFrameBuffer() {
    if (!g_framebuffer_initialized || g_framebuffer.texture.id == 0) {
        return NULL;
    }
    
    // ══════════════════════════════════════════════════════════════
    // PERFORMANCE NOTE: This is the BOTTLENECK
    // ══════════════════════════════════════════════════════════════
    // glReadPixels forces GPU->CPU transfer which stalls the pipeline.
    // At 600x400 RGBA = 960KB per frame. At 60fps = 57.6 MB/s transfer.
    // 
    // Mitigation strategies:
    // 1. Keep render resolution LOW (600x400 or 720x480)
    // 2. Reuse the pixel buffer (don't reallocate every frame)
    // 3. Consider PBO double-buffering for async readback (advanced)
    
    int width = g_framebuffer.texture.width;
    int height = g_framebuffer.texture.height;
    int size = width * height * 4;  // RGBA = 4 bytes per pixel
    
    // Allocate/resize buffer if needed
    if (g_frame_buffer_size != size) {
        if (g_frame_buffer_data) {
            MemFree(g_frame_buffer_data);
        }
        g_frame_buffer_data = (unsigned char*)MemAlloc(size);
        g_frame_buffer_size = size;
    }
    
    // Read pixels from GPU texture
    void* pixels = rlReadTexturePixels(
        g_framebuffer.texture.id, 
        width, height, 
        g_framebuffer.texture.format
    );
    
    if (pixels) {
        memcpy(g_frame_buffer_data, pixels, size);
        MemFree(pixels);  // rlReadTexturePixels allocates internally
    }
    
    return g_frame_buffer_data;
}
```

### 1.6 Input Handling Implementation

```cpp
// ══════════════════════════════════════════════════════════════════
// INPUT FROM PYTHON
// ══════════════════════════════════════════════════════════════════
// Since the window is hidden, raylib's IsKeyDown() etc won't work.
// Python forwards input via these functions.

__declspec(dllexport) void SetKeyState(int key, bool down) {
    if (key >= 0 && key < 512) {
        if (down && !g_inputState.keys[key]) {
            g_inputState.keysPressed[key] = true;  // Just pressed
        }
        g_inputState.keys[key] = down;
    }
}

__declspec(dllexport) void SetMouseButtonState(int button, bool down) {
    if (button >= 0 && button < 8) {
        if (down && !g_inputState.mouseButtons[button]) {
            g_inputState.mouseButtonsPressed[button] = true;
        }
        if (!down && g_inputState.mouseButtons[button]) {
            g_inputState.mouseButtonsReleased[button] = true;
        }
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

// Called internally at end of each frame to clear one-shot events
static void ClearInputFrame() {
    memset(g_inputState.keysPressed, 0, sizeof(g_inputState.keysPressed));
    memset(g_inputState.keysReleased, 0, sizeof(g_inputState.keysReleased));
    memset(g_inputState.mouseButtonsPressed, 0, sizeof(g_inputState.mouseButtonsPressed));
    memset(g_inputState.mouseButtonsReleased, 0, sizeof(g_inputState.mouseButtonsReleased));
    g_inputState.mouseDelta = (Vector2){0, 0};
    g_inputState.mouseWheelMove = 0;
}

// ══════════════════════════════════════════════════════════════════
// CRITICAL: CUSTOM INPUT WRAPPER FUNCTIONS
// ══════════════════════════════════════════════════════════════════
// 
// *** YOU MUST USE THESE INSTEAD OF RAYLIB'S BUILT-IN FUNCTIONS! ***
// 
// In standalone mode (g_standalone_mode = true), these call raylib directly.
// In embedded mode (g_standalone_mode = false), these read from g_inputState.
// 
// WRONG: if (IsMouseButtonPressed(MOUSE_BUTTON_LEFT)) { ... }
// RIGHT: if (CustomIsMouseButtonPressed(MOUSE_BUTTON_LEFT)) { ... }
// 
// This is a common source of bugs! If input doesn't work in embedded mode,
// search for raw raylib input calls and replace them with Custom* versions.

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

static int CustomGetCharPressed() {
    return g_standalone_mode ? GetCharPressed() : 0;
}
```

### 1.7 Raylib Key Code Reference

The Python side uses raylib key codes (not pygame). Here's the mapping:

| Key          | Raylib Code | Key          | Raylib Code |
|--------------|-------------|--------------|-------------|
| KEY_UP       | 265         | KEY_A        | 65          |
| KEY_DOWN     | 264         | KEY_B        | 66          |
| KEY_LEFT     | 263         | KEY_C        | 67          |
| KEY_RIGHT    | 262         | KEY_D        | 68          |
| KEY_SPACE    | 32          | KEY_E        | 69          |
| KEY_ENTER    | 257         | KEY_W        | 87          |
| KEY_ESCAPE   | 256         | KEY_S        | 83          |
| KEY_0-9      | 48-57       | KEY_Z        | 90          |
| KEY_MINUS    | 45          | KEY_EQUAL    | 61          |
| KEY_LSHIFT   | 340         | KEY_RSHIFT   | 344         |

**Mouse Buttons (Raylib constants):**
| Button           | Raylib Code |
|------------------|-------------|
| MOUSE_BUTTON_LEFT   | 0        |
| MOUSE_BUTTON_RIGHT  | 1        |
| MOUSE_BUTTON_MIDDLE | 2        |

See `raylib.h` for complete list.

---

## Part 2: The Python Side

### 2.1 Create the Embed Module (`yourgame_embed.py`)

Create `Data/games/yourgame_embed.py`:

```python
"""Embedded Game - loads C++ DLL and provides framebuffer access."""

import ctypes
import os
import pygame
import sys
import time
from typing import Optional, Tuple

# DLL state
_dll = None
_dll_path = None

# Resolution settings (applied before InitializeGame)
_PRESET_MAP = {"low": 0, "medium": 1, "high": 2}
_render_preset: Optional[int] = None
_requested_resolution: Optional[Tuple[int, int]] = None

# Debug: Print module load location for troubleshooting
print(f"DEBUG: Loaded yourgame_embed module from {__file__}")

def _find_dll() -> Optional[str]:
    """Find the game DLL."""
    try:
        base_path = os.path.dirname(os.path.abspath(__file__))
    except NameError:
        base_path = os.getcwd()
    
    # Hardcoded path for debugging (adjust for your system)
    hardcoded_path = r"E:\Dev\Glyphis_IO BBS The Proxy Tapes\Data\games\YourGame\yourgame.dll"
    if os.path.exists(hardcoded_path):
        print(f"DEBUG: Found DLL at hardcoded path: {hardcoded_path}")
        return hardcoded_path
    
    dll_paths = [
        os.path.join(base_path, "YourGame", "yourgame.dll"),
        os.path.join("Data", "games", "YourGame", "yourgame.dll"),
        "yourgame.dll",
    ]
    
    print(f"DEBUG: Searching for DLL in paths: {dll_paths}")
    for path in dll_paths:
        exists = os.path.exists(path)
        print(f"DEBUG: Checking {path} -> {exists}")
        if exists:
            return os.path.abspath(path)
    
    print("DEBUG: DLL NOT FOUND IN ANY PATH")
    return None

def _get_requested_preset() -> int:
    """Get the resolution preset to use."""
    global _render_preset
    if _render_preset is not None:
        return _render_preset
    env_value = os.environ.get("YOURGAME_RESOLUTION", "").strip().lower()
    if env_value == "auto":
        return 2  # default to high when auto
    return _PRESET_MAP.get(env_value, 1)  # default to medium

def set_resolution_mode(mode: str) -> bool:
    """Set desired render preset before initializing the DLL."""
    global _render_preset, _requested_resolution
    if not mode:
        return False
    preset = _PRESET_MAP.get(mode.strip().lower())
    if preset is None:
        print(f"[yourgame_embed] Unknown resolution mode '{mode}', valid: {list(_PRESET_MAP.keys())}")
        return False
    _render_preset = preset
    _requested_resolution = None
    if _dll is not None and getattr(_dll, "_has_resolution_preset", False):
        try:
            _dll.SetRenderResolutionPreset(preset)
        except Exception as exc:
            print(f"[yourgame_embed] Warning: Failed to push resolution preset: {exc}")
    return True

def set_render_resolution(width: int, height: int) -> bool:
    """Request an explicit render resolution before initializing the DLL."""
    global _requested_resolution, _render_preset
    try:
        width = max(320, int(width))
        height = max(200, int(height))
    except (TypeError, ValueError):
        print("[yourgame_embed] Invalid resolution values supplied.")
        return False
    _requested_resolution = (width, height)
    _render_preset = None
    if _dll is not None and getattr(_dll, "_has_resolution", False):
        try:
            _dll.SetRenderResolution(width, height)
        except Exception as exc:
            print(f"[yourgame_embed] Warning: Failed to push custom resolution: {exc}")
    return True

def initialize() -> bool:
    """Initialize the embedded game DLL."""
    global _dll, _dll_path
    
    if _dll is not None:
        return True
    
    _dll_path = _find_dll()
    if not _dll_path:
        print("ERROR: yourgame.dll not found")
        return False
    
    print(f"DEBUG: Found yourgame.dll at: {_dll_path}")
    
    # Check DLL staleness (helpful warning if C++ source is newer)
    try:
        mtime = os.path.getmtime(_dll_path)
        dll_size = os.path.getsize(_dll_path)
        print(f"DEBUG: DLL Modification Time: {time.ctime(mtime)} | size: {dll_size} bytes")
        cpp_path = os.path.join(os.path.dirname(_dll_path), "main.cpp")
        if os.path.exists(cpp_path):
            cpp_mtime = os.path.getmtime(cpp_path)
            if mtime < cpp_mtime:
                print(
                    "[yourgame_embed] WARNING: yourgame.dll is older than main.cpp. "
                    "Rebuild the DLL (build_dll.bat) or you won't see recent C++ fixes."
                )
    except Exception as e:
        print(f"DEBUG: Could not get DLL/source timestamp: {e}")
    
    dll_dir = os.path.dirname(_dll_path)
    
    # Add DLL directory to search path (Python 3.8+)
    if hasattr(os, 'add_dll_directory'):
        try:
            os.add_dll_directory(dll_dir)
        except Exception as e:
            print(f"Warning: Failed to add DLL directory: {e}")
    
    # Also add to PATH
    os.environ['PATH'] = dll_dir + os.pathsep + os.environ['PATH']
    
    # Change CWD to DLL dir for resource loading
    original_cwd = os.getcwd()
    try:
        os.chdir(dll_dir)
        print(f"[initialize] Changed CWD to {dll_dir}")
        
        # Pre-load dependencies (MinGW runtime + Raylib)
        dependencies = [
            "libgcc_s_seh-1.dll",   # MinGW runtime
            "libstdc++-6.dll",      # MinGW C++ runtime
            "libwinpthread-1.dll",  # MinGW threading
            "raylib.dll"            # Raylib
        ]
        for dep in dependencies:
            if os.path.exists(dep):
                try:
                    ctypes.CDLL(dep)
                    print(f"Pre-loaded dependency: {dep}")
                except Exception as e:
                    print(f"Warning: Failed to pre-load {dep}: {e}")
            else:
                print(f"Warning: Dependency not found: {dep}")
        
        # Load main DLL
        _dll = ctypes.CDLL(_dll_path)
        
        # ════════════════════════════════════════════════════════════════
        # REQUIRED FUNCTION SIGNATURES
        # ════════════════════════════════════════════════════════════════
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
        
        # ════════════════════════════════════════════════════════════════
        # OPTIONAL RESOLUTION FUNCTIONS (before InitializeGame!)
        # ════════════════════════════════════════════════════════════════
        try:
            _dll.SetRenderResolution.restype = None
            _dll.SetRenderResolution.argtypes = [ctypes.c_int, ctypes.c_int]
            _dll._has_resolution = True
        except AttributeError:
            _dll._has_resolution = False

        try:
            _dll.SetRenderResolutionPreset.restype = None
            _dll.SetRenderResolutionPreset.argtypes = [ctypes.c_int]
            _dll._has_resolution_preset = True
        except AttributeError:
            _dll._has_resolution_preset = False
        
        # Apply resolution settings BEFORE InitializeGame
        resolution_applied = False
        if _requested_resolution and getattr(_dll, "_has_resolution", False):
            try:
                width, height = _requested_resolution
                _dll.SetRenderResolution(int(width), int(height))
                resolution_applied = True
                print(f"[yourgame_embed] Applied custom resolution {width}x{height}")
            except Exception as exc:
                print(f"[yourgame_embed] Warning: Failed to apply custom resolution: {exc}")
        if not resolution_applied and getattr(_dll, "_has_resolution_preset", False):
            try:
                preset_value = int(_get_requested_preset())
                _dll.SetRenderResolutionPreset(preset_value)
                resolution_applied = True
                print(f"[yourgame_embed] Applied preset resolution '{preset_value}'")
            except Exception as exc:
                print(f"[yourgame_embed] Warning: Failed to apply resolution preset: {exc}")
        
        # Initialize the game
        if not _dll.InitializeGame():
            print("ERROR: Failed to initialize game")
            return False
        
        # Set up optional functions (after InitializeGame)
        _setup_optional_functions()
        
        print("Game initialized successfully")
        return True
        
    except AttributeError as e:
        error_str = str(e)
        if "ShouldExit" in error_str:
            # ShouldExit is optional, continue
            print(f"Note: Optional function not found: {e}")
            return True
        else:
            print(f"ERROR: Required function not found in DLL: {e}")
            return False
    except Exception as e:
        print(f"ERROR: Failed to load DLL: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # CRITICAL: Restore CWD for the BBS
        os.chdir(original_cwd)

def _setup_optional_functions():
    """Set up optional DLL functions (won't fail if missing)."""
    global _dll
    
    # Pattern: Try to get function, set flag if successful
    # This allows graceful degradation when DLL doesn't have all features
    
    # ShouldExit - game requests to exit
    _dll._has_should_exit = False
    try:
        if getattr(_dll, 'ShouldExit', None):
            _dll.ShouldExit.restype = ctypes.c_bool
            _dll.ShouldExit.argtypes = []
            _dll._has_should_exit = True
    except (AttributeError, OSError, TypeError):
        pass
    
    # ShouldCenterMouse - for 3D camera controls
    _dll._has_center_mouse = False
    try:
        if getattr(_dll, 'ShouldCenterMouse', None):
            _dll.ShouldCenterMouse.restype = ctypes.c_bool
            _dll.ShouldCenterMouse.argtypes = []
            _dll._has_center_mouse = True
    except (AttributeError, OSError, TypeError):
        pass
    
    # SetMouseWheelMove - mouse wheel input
    _dll._has_mouse_wheel = False
    try:
        if getattr(_dll, 'SetMouseWheelMove', None):
            _dll.SetMouseWheelMove.restype = None
            _dll.SetMouseWheelMove.argtypes = [ctypes.c_float]
            _dll._has_mouse_wheel = True
    except (AttributeError, OSError, TypeError):
        pass
    
    # GetLastFinalScore - leaderboard integration
    _dll._has_get_score = False
    try:
        if getattr(_dll, 'GetLastFinalScore', None):
            _dll.GetLastFinalScore.restype = ctypes.c_int
            _dll.GetLastFinalScore.argtypes = []
            _dll._has_get_score = True
    except (AttributeError, OSError, TypeError):
        pass
    
    # SetUsername - BBS username sync
    _dll._has_set_username = False
    try:
        if getattr(_dll, 'SetUsername', None):
            _dll.SetUsername.restype = None
            _dll.SetUsername.argtypes = [ctypes.c_char_p]
            _dll._has_set_username = True
    except (AttributeError, OSError, TypeError):
        pass
    
    # ResetGame - fresh start from BBS
    _dll._has_reset_game = False
    try:
        if getattr(_dll, 'ResetGame', None):
            _dll.ResetGame.restype = None
            _dll.ResetGame.argtypes = []
            _dll._has_reset_game = True
    except (AttributeError, OSError, TypeError):
        pass
    
    # SaveGameData / LoadGameData - persistence
    _dll._has_save_game = False
    try:
        if getattr(_dll, 'SaveGameData', None):
            _dll.SaveGameData.restype = None
            _dll.SaveGameData.argtypes = []
            _dll._has_save_game = True
    except (AttributeError, OSError, TypeError):
        pass
    
    _dll._has_load_game = False
    try:
        if getattr(_dll, 'LoadGameData', None):
            _dll.LoadGameData.restype = ctypes.c_bool
            _dll.LoadGameData.argtypes = []
            _dll._has_load_game = True
    except (AttributeError, OSError, TypeError):
        pass
    
    # CleanupGame - resource cleanup
    _dll._has_cleanup = False
    try:
        if getattr(_dll, 'CleanupGame', None):
            _dll.CleanupGame.restype = None
            _dll.CleanupGame.argtypes = []
            _dll._has_cleanup = True
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
        
        # Create zero-copy view over DLL buffer
        size = width * height * 4  # RGBA
        address = ctypes.addressof(ptr.contents)
        array_type = ctypes.c_ubyte * size
        buf_view = memoryview(array_type.from_address(address))
        
        # Create pygame surface
        surf = pygame.image.frombuffer(buf_view, (width, height), "RGBA")
        surf = pygame.transform.flip(surf, False, True)  # Flip Y (OpenGL convention)
        return surf.convert_alpha()
        
    except Exception as e:
        print(f"ERROR: {e}")
        return None

def get_size() -> Tuple[int, int]:
    """Get the framebuffer size."""
    if _dll is None:
        if not initialize():
            return (0, 0)
    try:
        return (_dll.GetWidth(), _dll.GetHeight())
    except:
        return (0, 0)

# ════════════════════════════════════════════════════════════════
# INPUT FUNCTIONS - All have try/except for robustness
# ════════════════════════════════════════════════════════════════

def set_key_state(key: int, down: bool):
    """Set a key state in the game."""
    if _dll:
        try:
            _dll.SetKeyState(key, down)
        except Exception as e:
            print(f"ERROR: Failed to set key state: {e}")

def set_mouse_button_state(button: int, down: bool):
    """Set a mouse button state in the game."""
    if _dll:
        try:
            _dll.SetMouseButtonState(button, down)
        except Exception as e:
            print(f"ERROR: Failed to set mouse button state: {e}")

def set_mouse_position(x: float, y: float):
    """Set mouse position in the game."""
    if _dll:
        try:
            _dll.SetInputMousePosition(x, y)
        except Exception as e:
            print(f"ERROR: Failed to set mouse position: {e}")

def set_mouse_delta(dx: float, dy: float):
    """Set mouse delta (movement) in the game."""
    if _dll:
        try:
            _dll.SetMouseDelta(dx, dy)
        except Exception as e:
            print(f"ERROR: Failed to set mouse delta: {e}")

def set_mouse_wheel(move: float):
    """Set mouse wheel movement in the game."""
    if _dll and hasattr(_dll, '_has_mouse_wheel') and _dll._has_mouse_wheel:
        try:
            _dll.SetMouseWheelMove(move)
        except Exception as e:
            print(f"ERROR: Failed to set mouse wheel: {e}")

# ════════════════════════════════════════════════════════════════
# GAME STATE FUNCTIONS
# ════════════════════════════════════════════════════════════════

def should_exit() -> bool:
    """Check if the game wants to exit."""
    if _dll and hasattr(_dll, '_has_should_exit') and _dll._has_should_exit:
        try:
            return _dll.ShouldExit()
        except Exception:
            return False
    return False

def should_center_mouse() -> bool:
    """Check if mouse should be centered (for 3D controls)."""
    if _dll and hasattr(_dll, '_has_center_mouse') and _dll._has_center_mouse:
        try:
            return _dll.ShouldCenterMouse()
        except Exception:
            return False
    return False

def get_last_final_score() -> int:
    """Get the last final score (for leaderboard integration)."""
    if _dll and hasattr(_dll, '_has_get_score') and _dll._has_get_score:
        try:
            return _dll.GetLastFinalScore()
        except Exception:
            return 0
    return 0

def set_username(username: str) -> bool:
    """Set the current BBS username for leaderboard entries."""
    if _dll and hasattr(_dll, '_has_set_username') and _dll._has_set_username:
        try:
            username_bytes = username.encode('utf-8')
            _dll.SetUsername(username_bytes)
            return True
        except Exception as e:
            print(f"[yourgame_embed] Failed to set username: {e}")
            return False
    return False

def reset_game() -> bool:
    """Reset all player stats to new game defaults. Call when launching from BBS."""
    if _dll and hasattr(_dll, '_has_reset_game') and _dll._has_reset_game:
        try:
            _dll.ResetGame()
            print("[yourgame_embed] Game reset - all stats reset to new game defaults")
            return True
        except Exception as e:
            print(f"[yourgame_embed] Failed to reset game: {e}")
            return False
    return False

def save_game_data():
    """Save game data to file."""
    if _dll and hasattr(_dll, '_has_save_game') and _dll._has_save_game:
        try:
            _dll.SaveGameData()
        except Exception as e:
            print(f"[yourgame_embed] Failed to save game data: {e}")

def load_game_data() -> bool:
    """Load game data from file."""
    if _dll and hasattr(_dll, '_has_load_game') and _dll._has_load_game:
        try:
            return _dll.LoadGameData()
        except Exception as e:
            print(f"[yourgame_embed] Failed to load game data: {e}")
            return False
    return False

def cleanup():
    """Cleanup resources."""
    global _dll
    try:
        if _dll and hasattr(_dll, "_has_cleanup") and _dll._has_cleanup:
            _dll.CleanupGame()
    except Exception as exc:
        print(f"[yourgame_embed] CleanupGame failed: {exc}")
    _dll = None
```

### 2.2 Create the Session Adapter (in `registry.py`)

Add to `Data/games/registry.py`:

```python
class YourGameSession(BaseGameSession):
    """Session adapter for YourGame using headless framebuffer rendering."""
    
    # ════════════════════════════════════════════════════════════════
    # KEY MAPPING: Pygame key codes -> Raylib key codes
    # ════════════════════════════════════════════════════════════════
    KEY_MAP = {
        # Arrow keys
        pygame.K_UP: 265, pygame.K_DOWN: 264,
        pygame.K_LEFT: 263, pygame.K_RIGHT: 262,
        # Special keys
        pygame.K_SPACE: 32, pygame.K_RETURN: 257, pygame.K_ESCAPE: 256,
        # Letters (A-Z = 65-90)
        pygame.K_a: 65, pygame.K_b: 66, pygame.K_c: 67, pygame.K_d: 68,
        pygame.K_e: 69, pygame.K_f: 70, pygame.K_g: 71, pygame.K_h: 72,
        pygame.K_i: 73, pygame.K_j: 74, pygame.K_k: 75, pygame.K_l: 76,
        pygame.K_m: 77, pygame.K_n: 78, pygame.K_o: 79, pygame.K_p: 80,
        pygame.K_q: 81, pygame.K_r: 82, pygame.K_s: 83, pygame.K_t: 84,
        pygame.K_u: 85, pygame.K_v: 86, pygame.K_w: 87, pygame.K_x: 88,
        pygame.K_y: 89, pygame.K_z: 90,
        # Numbers (0-9 = 48-57)
        pygame.K_0: 48, pygame.K_1: 49, pygame.K_2: 50, pygame.K_3: 51,
        pygame.K_4: 52, pygame.K_5: 53, pygame.K_6: 54, pygame.K_7: 55,
        pygame.K_8: 56, pygame.K_9: 57,
        # Modifiers
        pygame.K_MINUS: 45, pygame.K_EQUALS: 61,
        pygame.K_LSHIFT: 340, pygame.K_RSHIFT: 344,
    }
    
    # ════════════════════════════════════════════════════════════════
    # MOUSE BUTTON MAPPING: Pygame button -> Raylib button
    # ════════════════════════════════════════════════════════════════
    # Pygame: 1=LEFT, 2=MIDDLE, 3=RIGHT, 4=SCROLL_UP, 5=SCROLL_DOWN
    # Raylib: 0=LEFT, 1=RIGHT, 2=MIDDLE
    MOUSE_BUTTON_MAP = {1: 0, 3: 1, 2: 2}  # LEFT=0, RIGHT=1, MIDDLE=2
    
    def __init__(self, app: "GlyphisIOBBS"):
        super().__init__(app)
        self.embed_module = None
        self.last_frame: Optional[pygame.Surface] = None
        self.last_mouse_pos = (0, 0)
        
        # ════════════════════════════════════════════════════════════
        # CRITICAL: Desktop position constants
        # ════════════════════════════════════════════════════════════
        # These are the BASELINE coordinates (at 2560x1440 resolution)
        # for where the OS desktop area starts.
        self.baseline_desktop_x = 176
        self.baseline_desktop_y = 209
    
    def _get_desktop_pos(self) -> Tuple[int, int]:
        """Get desktop position scaled to current resolution."""
        return self.app.res_manager.coords(
            self.baseline_desktop_x, 
            self.baseline_desktop_y
        )
    
    def _get_desktop_dimensions(self) -> Tuple[int, int]:
        """Get desktop dimensions (where game will render)."""
        if hasattr(self.app, "os_mode") and self.app.os_mode:
            ds = self.app.os_mode.desktop_size
            if ds:
                return (int(ds[0]), int(ds[1]))
        
        # Fallback: load desktop image to get size
        try:
            desktop_path = os.path.join("Data", "OS", "Desktop-Enviroment.png")
            desktop_image = pygame.image.load(desktop_path)
            base_w, base_h = desktop_image.get_size()
            return (
                self.app.res_manager.scale(base_w),
                self.app.res_manager.scale(base_h)
            )
        except:
            return (max(720, int(848 * self.app.scale)), 
                    max(480, int(382 * self.app.scale)))
    
    def _get_game_mouse_pos(self, screen_pos: Tuple[int, int]) -> Tuple[float, float]:
        """Convert screen mouse position to game-relative position."""
        desktop_x, desktop_y = self._get_desktop_pos()
        desktop_w, desktop_h = self._get_desktop_dimensions()
        
        rel_x = screen_pos[0] - desktop_x
        rel_y = screen_pos[1] - desktop_y
        
        if self.embed_module:
            game_w, game_h = self.embed_module.get_size()
            if game_w > 0 and game_h > 0 and desktop_w > 0 and desktop_h > 0:
                # Scale from desktop coords to game coords
                game_x = (rel_x / desktop_w) * game_w
                game_y = (rel_y / desktop_h) * game_h
                return (
                    max(0.0, min(float(game_w), float(game_x))),
                    max(0.0, min(float(game_h), float(game_y)))
                )
        
        return (float(rel_x), float(rel_y))
    
    def enter(self) -> None:
        """Initialize the embedded game DLL."""
        try:
            from . import yourgame_embed
            self.embed_module = yourgame_embed
            
            # Set resolution to match desktop before init
            desktop_w, desktop_h = self._get_desktop_dimensions()
            if hasattr(yourgame_embed, "set_render_resolution"):
                yourgame_embed.set_render_resolution(desktop_w, desktop_h)
            
            if not yourgame_embed.initialize():
                print("Failed to initialize game DLL")
                self.exit_requested = True
                return
            
            # Hide pygame cursor (game will handle its own)
            pygame.mouse.set_visible(False)
            
        except Exception as e:
            print(f"Failed to initialize game: {e}")
            self.exit_requested = True
    
    def handle_event(self, event: pygame.event.Event) -> Optional[str]:
        """Forward input events to the embedded game DLL."""
        if not self.embed_module:
            return None
        
        # ════════════════════════════════════════════════════════════════
        # KEYBOARD EVENTS
        # ════════════════════════════════════════════════════════════════
        if event.type == pygame.KEYDOWN:
            raylib_key = self.KEY_MAP.get(event.key)
            if raylib_key is not None:
                self.embed_module.set_key_state(raylib_key, True)
        elif event.type == pygame.KEYUP:
            raylib_key = self.KEY_MAP.get(event.key)
            if raylib_key is not None:
                self.embed_module.set_key_state(raylib_key, False)
        
        # ════════════════════════════════════════════════════════════════
        # MOUSE BUTTON EVENTS
        # ════════════════════════════════════════════════════════════════
        if event.type == pygame.MOUSEBUTTONDOWN:
            raylib_btn = self.MOUSE_BUTTON_MAP.get(event.button)
            if raylib_btn is not None:
                self.embed_module.set_mouse_button_state(raylib_btn, True)
                game_pos = self._get_game_mouse_pos(event.pos)
                self.embed_module.set_mouse_position(game_pos[0], game_pos[1])
            # Handle scroll wheel via MOUSEBUTTONDOWN (older pygame versions)
            if event.button == 4:  # Scroll up
                if hasattr(self.embed_module, 'set_mouse_wheel'):
                    self.embed_module.set_mouse_wheel(1.0)
            elif event.button == 5:  # Scroll down
                if hasattr(self.embed_module, 'set_mouse_wheel'):
                    self.embed_module.set_mouse_wheel(-1.0)
        elif event.type == pygame.MOUSEBUTTONUP:
            raylib_btn = self.MOUSE_BUTTON_MAP.get(event.button)
            if raylib_btn is not None:
                self.embed_module.set_mouse_button_state(raylib_btn, False)
        
        # ════════════════════════════════════════════════════════════════
        # MOUSE WHEEL EVENT (newer pygame versions)
        # ════════════════════════════════════════════════════════════════
        if event.type == pygame.MOUSEWHEEL:
            if hasattr(self.embed_module, 'set_mouse_wheel'):
                self.embed_module.set_mouse_wheel(float(event.y))
        
        # ════════════════════════════════════════════════════════════════
        # MOUSE MOTION - use relative movement for delta
        # ════════════════════════════════════════════════════════════════
        if event.type == pygame.MOUSEMOTION:
            dx, dy = 0.0, 0.0
            if hasattr(event, 'rel') and event.rel:
                dx, dy = float(event.rel[0]), float(event.rel[1])
            else:
                game_pos = self._get_game_mouse_pos(event.pos)
                last_game_pos = self._get_game_mouse_pos(self.last_mouse_pos)
                dx = game_pos[0] - last_game_pos[0]
                dy = game_pos[1] - last_game_pos[1]
            
            self.embed_module.set_mouse_delta(dx, dy)
            
            game_pos = self._get_game_mouse_pos(event.pos)
            self.embed_module.set_mouse_position(game_pos[0], game_pos[1])
            self.last_mouse_pos = event.pos
        
        return None
    
    def update(self, dt: float) -> None:
        """Update game frame from DLL framebuffer."""
        if not self.embed_module:
            return
        
        # ════════════════════════════════════════════════════════════════
        # MOUSE INPUT HANDLING
        # ════════════════════════════════════════════════════════════════
        rel_x, rel_y = pygame.mouse.get_rel()
        
        # Handle mouse centering for 3D controls
        if (hasattr(self.embed_module, 'should_center_mouse') and 
            self.embed_module.should_center_mouse()):
            desktop_x, desktop_y = self._get_desktop_pos()
            desktop_w, desktop_h = self._get_desktop_dimensions()
            center_x = desktop_x + desktop_w // 2
            center_y = desktop_y + desktop_h // 2
            pygame.mouse.set_pos(center_x, center_y)
            pygame.mouse.get_rel()  # Reset relative movement
        
        # Send mouse delta
        if abs(rel_x) > 0.01 or abs(rel_y) > 0.01:
            self.embed_module.set_mouse_delta(float(rel_x), float(rel_y))
        else:
            self.embed_module.set_mouse_delta(0.0, 0.0)
        
        # Update mouse position
        mouse_pos = pygame.mouse.get_pos()
        game_pos = self._get_game_mouse_pos(mouse_pos)
        self.embed_module.set_mouse_position(game_pos[0], game_pos[1])
        self.last_mouse_pos = mouse_pos
        
        # ════════════════════════════════════════════════════════════════
        # USERNAME SYNC (periodically refresh from BBS)
        # ════════════════════════════════════════════════════════════════
        self.score_check_counter = getattr(self, 'score_check_counter', 0) + 1
        if self.score_check_counter % 300 == 0:  # Every ~5 seconds at 60fps
            if hasattr(self.app, 'get_active_user'):
                active_user = self.app.get_active_user()
                if active_user and active_user.get('username'):
                    if hasattr(self.embed_module, 'set_username'):
                        self.embed_module.set_username(active_user.get('username'))
        
        # ════════════════════════════════════════════════════════════════
        # LEADERBOARD INTEGRATION (upload scores to Steam)
        # ════════════════════════════════════════════════════════════════
        if self.score_check_counter >= 60:  # Every second
            try:
                new_score = self.embed_module.get_last_final_score()
                last_uploaded = getattr(self, 'last_uploaded_score', 0)
                if new_score > 0 and new_score != last_uploaded:
                    if hasattr(self.app, 'steam') and self.app.steam.is_available():
                        self.app.steam.upload_leaderboard_score("YourGameLeaderboard", new_score)
                        self.last_uploaded_score = new_score
            except Exception:
                pass  # Silently fail if function doesn't exist
        
        # ════════════════════════════════════════════════════════════════
        # EXIT DETECTION
        # ════════════════════════════════════════════════════════════════
        if self.embed_module.should_exit():
            self.exit_requested = True
        
        # ════════════════════════════════════════════════════════════════
        # GET FRAME FROM DLL
        # ════════════════════════════════════════════════════════════════
        try:
            self.last_frame = self.embed_module.get_frame_surface()
        except Exception as e:
            print(f"ERROR getting frame: {e}")
    
    def draw(self) -> None:
        """Prepare frame - actual drawing happens via get_game_frame()."""
        pass  # Drawing handled by main loop
    
    def get_game_frame(self) -> Optional[Tuple[pygame.Surface, Tuple[int, int]]]:
        """Get the current game frame for rendering at desktop layer."""
        if not self.last_frame:
            return None
        
        desktop_x, desktop_y = self._get_desktop_pos()
        desktop_w, desktop_h = self._get_desktop_dimensions()
        frame_w, frame_h = self.last_frame.get_size()
        
        # Scale to fit desktop, preserving aspect ratio
        if (frame_w, frame_h) != (desktop_w, desktop_h):
            scale_x = desktop_w / frame_w
            scale_y = desktop_h / frame_h
            scale = min(scale_x, scale_y)
            
            new_w = int(frame_w * scale)
            new_h = int(frame_h * scale)
            
            scaled = pygame.transform.smoothscale(self.last_frame, (new_w, new_h))
        else:
            scaled = self.last_frame
        
        return (scaled, (desktop_x, desktop_y))
    
    def exit(self) -> None:
        """Cleanup embedded game resources."""
        pygame.mouse.set_visible(True)
        
        if self.embed_module:
            try:
                self.embed_module.cleanup()
            except Exception as e:
                print(f"Error cleaning up: {e}")
        
        self.embed_module = None
        self.last_frame = None
```

### 2.3 Register the Game in `GAME_DEFINITIONS`

```python
from tokens import Tokens

GAME_DEFINITIONS: List[GameDefinition] = [
    # ... existing games ...
    GameDefinition(
        id="your_game",
        title="YOUR GAME",
        description="Description of your game.",
        tokens_required=[Tokens.YOUR_GAME_TOKEN],  # Or [] for no requirements
        session_factory=YourGameSession,
    ),
]
```

---

## Part 3: Video/MP4 Handling When Game is Active

### 3.1 What Happens to Background Videos

When a game session is active, the main loop in `main.py` continues to:

1. **Read the background video** (`desktop_steam.mp4` or variant) and render it
2. **Draw the OS Mode desktop** (if active)
3. **Draw a BLACK rectangle** at the desktop position (to cover the video behind the game)
4. **Draw the game frame** at the desktop position (on top of the black rectangle)
5. **Draw scanlines** over everything

Relevant code from `main.py`:

```python
# Draw black rectangle behind game session
if self.state == "game_session" and self.active_game_session:
    baseline_desktop_x = 176
    baseline_desktop_y = 209
    desktop_x = int(baseline_desktop_x * self.scale)
    desktop_y = int(baseline_desktop_y * self.scale)
    
    # Get desktop size
    if self.os_mode and hasattr(self.os_mode, 'desktop_size'):
        desktop_size = self.os_mode.desktop_size
    else:
        # Fallback...
    
    # Draw black rectangle (covers video)
    pygame.draw.rect(self.screen, BLACK, (desktop_x, desktop_y, desktop_size[0], desktop_size[1]))

# Draw game session frame (on top of black)
if self.state == "game_session" and self.active_game_session:
    frame_data = getattr(self.active_game_session, "get_game_frame", None)
    if frame_data and callable(frame_data):
        result = frame_data()
        if result:
            frame, pos = result
            self.screen.blit(frame, pos)
```

### 3.2 Video State Detection

The system uses `_is_astro_miner_session_active()` to detect game state:

```python
def _is_astro_miner_session_active(self) -> bool:
    return (
        self.state == "game_session"
        and self.active_game_session is not None
        and isinstance(self.active_game_session, AstroMinerSession)
    )
```

When active, the desktop video selection may change (e.g., to `Audio-Desktop-os.mp4`).

---

## Part 4: Resolution and Positioning Deep Dive

### 4.1 Baseline vs Scaled Coordinates

The BBS uses a **baseline resolution** of **2560x1440**. All coordinates are defined at this baseline and scaled to the actual screen size.

```python
# In resolution.py
@dataclass
class ResolutionManager:
    screen_width: int
    screen_height: int
    baseline_width: int = 2560
    baseline_height: int = 1440
    
    def coords(self, x: float, y: float) -> Tuple[int, int]:
        """Convert baseline coordinates to screen coordinates."""
        scaled_x = int(x * self.scale_factor) + self.padding_x
        scaled_y = int(y * self.scale_factor) + self.padding_y
        return (scaled_x, scaled_y)
```

### 4.2 Desktop Position Constants

```python
# The OS Desktop area starts at these BASELINE coordinates:
baseline_desktop_x = 176   # X offset from left edge
baseline_desktop_y = 209   # Y offset from top edge

# At 2560x1440 (scale=1.0):
# Desktop is at (176, 209)

# At 1920x1080 (scale=0.75):
# Desktop is at (132, 157) approximately

# At 1280x720 (scale=0.5):
# Desktop is at (88, 105) approximately
```

### 4.3 Desktop Size

The desktop size is determined by the `Desktop-Enviroment.png` image:

```python
desktop_path = get_data_path("OS", "Desktop-Enviroment.png")
desktop_image = pygame.image.load(desktop_path)
original_size = desktop_image.get_size()  # e.g., (1200, 800) at baseline
desktop_size = (
    int(original_size[0] * self.scale),
    int(original_size[1] * self.scale)
)
```

### 4.4 Mouse Coordinate Transformation

When the user clicks/moves mouse, screen coordinates must be transformed to game coordinates:

```
Screen Position (1920x1080)
         │
         ▼
     Subtract desktop offset
         │
         ▼
Relative to Desktop (e.g., 800x600)
         │
         ▼
     Scale to game resolution
         │
         ▼
Game Coordinates (e.g., 600x400)
```

```python
def _get_game_mouse_pos(self, screen_pos):
    # 1. Get desktop position
    desktop_x, desktop_y = self._get_desktop_pos()
    
    # 2. Get desktop dimensions  
    desktop_w, desktop_h = self._get_desktop_dimensions()
    
    # 3. Calculate relative position
    rel_x = screen_pos[0] - desktop_x
    rel_y = screen_pos[1] - desktop_y
    
    # 4. Scale to game coordinates
    game_w, game_h = self.embed_module.get_size()
    game_x = (rel_x / desktop_w) * game_w
    game_y = (rel_y / desktop_h) * game_h
    
    return (game_x, game_y)
```

### 4.5 Aspect-Fit Contract (Critical for Correct Scaling + Input)

When the displayed game frame uses aspect-fit scaling (letterbox/pillarbox), you must use the **same presented rect** for:

1. frame blit position
2. frame scaled size
3. mouse-to-game coordinate mapping

If these are not identical, the game appears offset/scaled incorrectly and mouse input drifts.

```python
def _compute_presented_frame_rect(desktop_x, desktop_y, desktop_w, desktop_h, frame_w, frame_h):
    if frame_w <= 0 or frame_h <= 0:
        return (desktop_x, desktop_y, max(1, desktop_w), max(1, desktop_h))

    scale = min(desktop_w / frame_w, desktop_h / frame_h)
    draw_w = max(1, int(frame_w * scale))
    draw_h = max(1, int(frame_h * scale))
    draw_x = desktop_x + (desktop_w - draw_w) // 2
    draw_y = desktop_y + (desktop_h - draw_h) // 2
    return (draw_x, draw_y, draw_w, draw_h)
```

Use that rect for both drawing and input conversion:

```python
draw_x, draw_y, draw_w, draw_h = _compute_presented_frame_rect(
    desktop_x, desktop_y, desktop_w, desktop_h, frame_w, frame_h
)

# Render
scaled = pygame.transform.smoothscale(frame, (draw_w, draw_h))
screen.blit(scaled, (draw_x, draw_y))

# Input mapping
rel_x = mouse_x - draw_x
rel_y = mouse_y - draw_y
game_x = (rel_x / draw_w) * frame_w
game_y = (rel_y / draw_h) * frame_h
```

---

## Part 5: Memory Management for Performance

### 5.1 The GPU->CPU Bottleneck

The main performance bottleneck is `GetFrameBuffer()` which calls `glReadPixels`:

```
GPU renders to texture (fast, milliseconds)
         │
         ▼
glReadPixels copies to CPU (SLOW, stalls pipeline)
         │
         ▼
Python reads buffer (fast, zero-copy memoryview)
         │
         ▼
pygame.image.frombuffer creates Surface (fast)
         │
         ▼
pygame.transform.smoothscale to desktop size (moderate)
```

### 5.2 Resolution Presets

Astro Miner uses preset resolutions to balance quality vs performance:

| Preset | Resolution | Pixels    | Transfer/frame |
|--------|------------|-----------|----------------|
| Low    | 480x320    | 153,600   | ~600KB         |
| Medium | 600x400    | 240,000   | ~960KB         |
| High   | 720x480    | 345,600   | ~1.38MB        |

At 60 FPS:
- Low: 36 MB/s
- Medium: 57.6 MB/s  
- High: 82.8 MB/s

### 5.3 Buffer Reuse

The C++ side reuses the pixel buffer to avoid allocation churn:

```cpp
// Allocate once, reuse every frame
if (g_frame_buffer_size != size) {
    if (g_frame_buffer_data) {
        MemFree(g_frame_buffer_data);
    }
    g_frame_buffer_data = (unsigned char*)MemAlloc(size);
    g_frame_buffer_size = size;
}
```

The Python side uses a zero-copy memoryview:

```python
# Zero-copy view into DLL memory
address = ctypes.addressof(ptr.contents)
array_type = ctypes.c_ubyte * size
buf_view = memoryview(array_type.from_address(address))

# pygame creates surface from buffer without copying
surf = pygame.image.frombuffer(buf_view, (width, height), "RGBA")
```

---

## Part 6: Building the DLL

### 6.1 Prerequisites

1. **MinGW-w64** (g++) - Download from https://www.msys2.org/ or use w64devkit
2. **Raylib** - Download from https://github.com/raysan5/raylib/releases

### 6.2 Expected Paths

The build scripts expect:
- Raylib at `E:\Dev\raylib` or `C:\raylib`
- `raylib.h` at `{RAYLIB_PATH}/include/raylib.h`
- `raylib.dll` at `{RAYLIB_PATH}/lib/raylib.dll`

### 6.3 Build Command

```bash
cd Data/games/YourGame

g++ main.cpp ^
    -o yourgame.dll ^
    -shared ^
    -I "E:\Dev\raylib\include" ^
    -L "E:\Dev\raylib\lib" ^
    -lraylibdll ^
    -lopengl32 ^
    -lgdi32 ^
    -lwinmm ^
    -std=c++11
```

### 6.4 build_dll.bat Template

```batch
@echo off
echo Building yourgame.dll...

where g++ >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: g++ not found
    pause
    exit /b 1
)

g++ main.cpp ^
    -o yourgame.dll ^
    -shared ^
    -I "E:\Dev\raylib\include" ^
    -L "E:\Dev\raylib\lib" ^
    -lraylibdll ^
    -lopengl32 ^
    -lgdi32 ^
    -lwinmm ^
    -std=c++11

if %ERRORLEVEL% EQU 0 (
    echo SUCCESS: yourgame.dll created!
) else (
    echo ERROR: Compilation failed
)
pause
```

### 6.5 Required Files After Build

Your game folder should contain:
```
Data/games/YourGame/
├── main.cpp              # Source code
├── build_dll.bat         # Build script
├── yourgame.dll          # Compiled game (AFTER build)
├── raylib.dll            # Raylib runtime (REQUIRED)
├── libgcc_s_seh-1.dll    # MinGW runtime (may be needed)
├── libstdc++-6.dll       # MinGW C++ runtime
├── libwinpthread-1.dll   # MinGW threading
├── resources/            # Game assets
│   ├── sprites/
│   ├── sounds/
│   └── ...
└── README.md
```

---

## Part 7: Step-by-Step Integration Checklist

### Phase 1: C++ Game Development

- [ ] Create game folder at `Data/games/YourGame/`
- [ ] Implement game logic in `main.cpp`
- [ ] Add DLL export declarations at top of file
- [ ] Implement `InitializeGame()` with hidden window
- [ ] Implement `UpdateFrame()` rendering to framebuffer
- [ ] Implement `GetFrameBuffer()`, `GetWidth()`, `GetHeight()`
- [ ] Implement input handlers (`SetKeyState`, `SetMouseButtonState`, etc.)
- [ ] Replace all raylib input calls with custom input functions
- [ ] Add `main()` function for standalone testing
- [ ] Create `build_dll.bat`
- [ ] Copy `raylib.dll` and MinGW runtime DLLs to game folder
- [ ] Build and test standalone mode
- [ ] Build DLL mode

### Phase 2: Python Integration

- [ ] Create `Data/games/yourgame_embed.py`
- [ ] Implement `initialize()`, `get_frame_surface()`, etc.
- [ ] Add session class to `Data/games/registry.py`
- [ ] Implement key/mouse mapping in session class
- [ ] Add game definition to `GAME_DEFINITIONS`
- [ ] Create unlock token in `tokens.py` (if needed)
- [ ] Test in BBS environment

### Phase 3: Testing

- [ ] Launch game from BBS GAMES menu
- [ ] Verify rendering at correct desktop position
- [ ] Test keyboard input
- [ ] Test mouse input (position and delta)
- [ ] Test game exit (ESC or menu quit)
- [ ] Verify cursor visibility toggle
- [ ] Test at multiple resolutions
- [ ] Profile performance (check for frame drops)

---

## Appendix A: Debugging Tips and Common Pitfalls

### A.1 DLL Not Loading

```python
# Check if DLL exists
import os
print(os.path.exists("Data/games/YourGame/yourgame.dll"))

# Try loading manually
import ctypes
ctypes.CDLL("Data/games/YourGame/raylib.dll")  # Load dependency first
ctypes.CDLL("Data/games/YourGame/yourgame.dll")
```

**Common causes:**
- DLL not built (run `build_dll.bat`)
- DLL named incorrectly (e.g., `yourgame.new.dll` instead of `yourgame.dll`)
- Missing dependencies (raylib.dll, libgcc_s_seh-1.dll, etc.)
- Python 3.8+ DLL loading security (use `os.add_dll_directory()`)

### A.2 Black Screen

- Check if `UpdateFrame()` is being called (add `printf`)
- Check if `g_framebuffer_initialized` is `true`
- Check if rendering is inside `BeginTextureMode()`/`EndTextureMode()`
- Verify `GetFrameBuffer()` returns non-NULL
- Ensure `g_standalone_mode = false` is set when called from Python

**CyberTrain embedded incidents (March 3, 2026):**
- **Symptom:** black screen with cursor visible, logs show splash/UI texture IDs are valid.
  - **Cause:** Python-side debug sampler read a `memoryview` with unsupported format (`NotImplementedError: memoryview: unsupported format <B`) and `get_frame_surface()` returned `None`.
  - **Fix:** keep `memoryview(...)` only for `pygame.image.frombuffer`, but sample bytes from the backing ctypes array (`raw_array[i]`) instead.
- **Symptom:** frame fetch succeeds but frame is almost fully black (`non_black` near zero) even though render stage advances.
  - **Cause:** readback used runtime texture format directly, which can be backend-dependent in embedded mode.
  - **Fix:** force framebuffer readback to `PIXELFORMAT_UNCOMPRESSED_R8G8B8A8` in `GetFrameBuffer()`.
- **Symptom:** stuck at splash phase 0 (`stage=10`, `splash=0`) with persistent black output.
  - **Cause:** `GetFrameTime()` returning invalid/zero values during hidden-window startup; splash timer never advanced.
  - **Fix:** clamp splash `dt` (`if dt <= 0 || dt > 0.1 -> dt = 1/60`).

### A.3 Input Not Working (CRITICAL!)

**⚠️ MOST COMMON BUG:** Using raw Raylib input functions instead of Custom* wrappers!

```cpp
// WRONG - Won't work in embedded mode!
if (IsMouseButtonPressed(MOUSE_BUTTON_LEFT)) { ... }
if (IsKeyPressed(KEY_SPACE)) { ... }
Vector2 mousePos = GetMousePosition();

// RIGHT - Works in both standalone and embedded modes!
if (CustomIsMouseButtonPressed(MOUSE_BUTTON_LEFT)) { ... }
if (CustomIsKeyPressed(KEY_SPACE)) { ... }
Vector2 mousePos = CustomGetMousePosition();
```

**How to find this bug:**
```bash
# Search for raw Raylib input calls that should be replaced
grep -n "IsMouseButtonPressed\|IsMouseButtonDown\|IsKeyPressed\|IsKeyDown\|GetMousePosition\|GetMouseDelta" main.cpp
```

**Other causes:**
- Print key codes in `handle_event()` to verify mapping
- Verify `ClearInputFrame()` is called at end of `UpdateFrame()`
- Check pygame event handling for missing event types (MOUSEWHEEL vs MOUSEBUTTONDOWN)

### A.4 Performance Issues

- Check render resolution (should be 600x400 or similar)
- Profile `GetFrameBuffer()` call time
- Consider reducing resolution further
- Check for memory leaks (buffer not being reused)
- Avoid high MSAA in embedded mode
- **Screen zoom lag**: The BBS zoom feature uses a cheap crop-and-scale of only the desktop region during game sessions (not the full-screen 2x pipeline). If you still see FPS drops when zoomed, ensure the desktop region dimensions are reasonable. The zoom crops via `subsurface().copy()` then scales to screen size — much cheaper than the full-screen copy+scale used outside of game sessions.

### A.5 DLL Out of Date

**Symptom:** Changes to C++ code don't appear in game.

The Python embed module checks for this and prints a warning:
```
WARNING: yourgame.dll is older than main.cpp. Rebuild the DLL...
```

**Solution:** Run `build_dll.bat` after every C++ change!

### A.6 Game State Not Resetting

**Symptom:** Starting game from BBS shows previous session's state.

**Solution:** Implement `ResetGame()` and call it from session's `enter()`:
```cpp
__declspec(dllexport) void ResetGame() {
    g_playerScore = 0;
    g_playerHealth = 100;
    // Reset all game state to defaults
}
```

```python
def enter(self) -> None:
    # ...
    self.embed_module.reset_game()
    # ...
```

### A.7 Global State Variables

**Symptom:** Variables declared inside functions don't persist between frames.

**Solution:** Use `static` keyword or global `g_` prefixed variables:
```cpp
// WRONG - reset every frame
void UpdateGame() {
    std::vector<Particle> particles;  // Empty every frame!
}

// RIGHT - persists between frames
static std::vector<Particle> g_particles;  // Global
void UpdateGame() {
    // g_particles keeps its state
}
```

---

## Appendix B: Token-Gated Access

To require a token to unlock the game:

1. Add token to `tokens.py`:
```python
YOUR_GAME_TOKEN = "YOURGAME"
```

2. Add to game definition:
```python
GameDefinition(
    id="your_game",
    title="YOUR GAME",
    tokens_required=[Tokens.YOUR_GAME_TOKEN],
    # ...
)
```

3. Grant token via email, quest completion, etc.:
```python
self.app.grant_token(Tokens.YOUR_GAME_TOKEN, reason="quest completed")
```

---

## Appendix C: Save/Load Game State

For games with persistent state:

```cpp
// C++ side
__declspec(dllexport) void SaveGame() {
    FILE* f = fopen("yourgame_save.json", "w");
    // Write game state...
    fclose(f);
}

__declspec(dllexport) bool LoadGame() {
    FILE* f = fopen("yourgame_save.json", "r");
    if (!f) return false;
    // Read game state...
    fclose(f);
    return true;
}
```

```python
# Python side (optional wrapper)
def save_game():
    if _dll and hasattr(_dll, 'SaveGame'):
        _dll.SaveGame()

def load_game() -> bool:
    if _dll and hasattr(_dll, 'LoadGame'):
        return _dll.LoadGame()
    return False
```

---

## Appendix D: Audio System (Raylib Audio in Embedded DLL Mode)

Raylib's audio subsystem works fully inside a DLL alongside pygame — proven by both AstroMiner and CyberTrain. Audio is **not** affected by the hidden window. The BBS uses pygame.mixer for its own audio; Raylib audio coexists without conflict.

### D.1 Audio Device Initialization

**Critical:** Call `SetAudioStreamBufferSizeDefault(16384)` before `InitAudioDevice()`. The larger buffer prevents crackling/stuttering that occurs with the default 4096 buffer when running inside a DLL alongside pygame.

#### Embedded Mode (`InitializeGame()` DLL export)
```cpp
__declspec(dllexport) bool InitializeGame() {
    // ... window setup ...

    // Audio init — MUST match this exact pattern
    SetAudioStreamBufferSizeDefault(16384);
    InitAudioDevice();
    g_audio_initialized = true;

    // ... load other assets ...
    LoadAudioAssets();  // Load music + SFX after audio device is ready

    return true;
}
```

#### Standalone Mode (`main()`)
```cpp
int main() {
    InitWindow(screenWidth, screenHeight, "YourGame");
    SetAudioStreamBufferSizeDefault(16384);
    InitAudioDevice();
    // ... rest of init ...
    LoadAudioAssets();
    // ... game loop ...
    UnloadAudioAssets();
    CloseAudioDevice();
    CloseWindow();
}
```

#### Forward Declarations (Unity Build)

Because the unity build includes files in order (`exports.cpp` before `ui.cpp`), you need forward declarations in the exports file:

```cpp
// At top of cybertrain_exports.cpp (before extern "C" block)
static void LoadAudioAssets();
static void UnloadAudioAssets();
```

### D.2 Audio Globals

Declare all audio state in your core globals file so every translation unit can access them:

```cpp
// ── Audio assets ──
static Music g_musicTracks[3] = {};    // Up to 3 background music tracks
static bool g_musicLoaded = false;
static int g_currentTrack = 0;         // Index of currently playing track

static Sound g_sfxBuildTrain = {};     // Example: train-built sound
static Sound g_sfxBuildSys = {};       // Example: generic system sound
static Sound g_sfxFactoryBuilt = {};   // Example: factory-built sound
static Sound g_sfxBureauBuilt = {};    // Example: bureau-built sound
static Sound g_sfxSiloBuilt = {};      // Example: silo announcement
static bool g_sfxLoaded = false;

// ── Pending SFX (for delayed/chained sounds) ──
static float g_pendingSfxTimer = 0.0f;
static bool g_pendingSfxActive = false;

// ── Volume/Options state ──
static int g_musicVolume = 1;   // 0=LOW, 1=MID, 2=HIGH
static int g_sfxVolume = 1;     // 0=LOW, 1=MID, 2=HIGH
static int g_gammaLevel = 1;    // 0=LOW, 1=MID, 2=HIGH
```

### D.3 Multi-Path Asset Loading

Audio files live in an `Audio/` subdirectory under the game folder. Use the same multi-path fallback pattern used for textures and fonts:

```cpp
static Music TryLoadMusic(const char* filename) {
    const char* prefixes[] = { "Audio/", "../Audio/",
                                "Data/games/YourGame/Audio/", "../../Audio/" };
    for (int i = 0; i < 4; i++) {
        char path[512];
        snprintf(path, sizeof(path), "%s%s", prefixes[i], filename);
        if (FileExists(path)) {
            Music m = LoadMusicStream(path);
            if (m.ctxData != NULL) {
                m.looping = false;  // We handle track advancement manually
                return m;
            }
        }
    }
    return {};
}

static Sound TryLoadSound(const char* filename) {
    const char* prefixes[] = { "Audio/", "../Audio/",
                                "Data/games/YourGame/Audio/", "../../Audio/" };
    for (int i = 0; i < 4; i++) {
        char path[512];
        snprintf(path, sizeof(path), "%s%s", prefixes[i], filename);
        if (FileExists(path)) {
            Sound s = LoadSound(path);
            if (s.frameCount > 0) return s;
        }
    }
    return {};
}
```

### D.4 LoadAudioAssets / UnloadAudioAssets

```cpp
static float GetVolumeFloat(int level) {
    if (level <= 0) return 0.25f;  // LOW
    if (level >= 2) return 1.0f;   // HIGH
    return 0.5f;                   // MID
}

static void ApplyMusicVolume() {
    float vol = GetVolumeFloat(g_musicVolume);
    for (int i = 0; i < 3; i++) {
        if (g_musicTracks[i].ctxData) SetMusicVolume(g_musicTracks[i], vol);
    }
}

static void ApplySfxVolume() {
    float vol = GetVolumeFloat(g_sfxVolume);
    if (g_sfxBuildTrain.frameCount)   SetSoundVolume(g_sfxBuildTrain, vol);
    if (g_sfxBuildSys.frameCount)     SetSoundVolume(g_sfxBuildSys, vol);
    if (g_sfxFactoryBuilt.frameCount) SetSoundVolume(g_sfxFactoryBuilt, vol);
    if (g_sfxBureauBuilt.frameCount)  SetSoundVolume(g_sfxBureauBuilt, vol);
    if (g_sfxSiloBuilt.frameCount)    SetSoundVolume(g_sfxSiloBuilt, vol);
}

static void LoadAudioAssets() {
    g_musicTracks[0] = TryLoadMusic("YourGame_Track1.mp3");
    g_musicTracks[1] = TryLoadMusic("YourGame_Track2.mp3");
    g_musicTracks[2] = TryLoadMusic("YourGame_Track3.mp3");
    g_musicLoaded = (g_musicTracks[0].ctxData != NULL);

    g_sfxBuildTrain   = TryLoadSound("BUILD-Train.wav");
    g_sfxBuildSys     = TryLoadSound("BUILD-Sys.wav");
    g_sfxFactoryBuilt = TryLoadSound("Factory-Built.wav");
    g_sfxBureauBuilt  = TryLoadSound("Bureau-BUILT.wav");
    g_sfxSiloBuilt    = TryLoadSound("SILO-Built.wav");
    g_sfxLoaded = (g_sfxBuildTrain.frameCount > 0);

    ApplyMusicVolume();
    ApplySfxVolume();
}

static void UnloadAudioAssets() {
    for (int i = 0; i < 3; i++) {
        if (g_musicTracks[i].ctxData) {
            StopMusicStream(g_musicTracks[i]);
            UnloadMusicStream(g_musicTracks[i]);
            g_musicTracks[i] = {};
        }
    }
    g_musicLoaded = false;
    if (g_sfxBuildTrain.frameCount)   UnloadSound(g_sfxBuildTrain);
    if (g_sfxBuildSys.frameCount)     UnloadSound(g_sfxBuildSys);
    if (g_sfxFactoryBuilt.frameCount) UnloadSound(g_sfxFactoryBuilt);
    if (g_sfxBureauBuilt.frameCount)  UnloadSound(g_sfxBureauBuilt);
    if (g_sfxSiloBuilt.frameCount)    UnloadSound(g_sfxSiloBuilt);
    g_sfxLoaded = false;
}
```

### D.5 Music Streaming (Manual Track Advancement)

Set `m.looping = false` on each Music stream. Each frame, call `UpdateMusicStream()`. When a track finishes, advance to the next and loop back to track 0:

```cpp
static void UpdateMusic() {
    if (!g_musicLoaded || !g_audio_initialized) return;

    // Update the active stream
    Music& current = g_musicTracks[g_currentTrack];
    if (current.ctxData) UpdateMusicStream(current);

    // If not playing, advance to next track
    if (current.ctxData && !IsMusicStreamPlaying(current)) {
        g_currentTrack = (g_currentTrack + 1) % 3;
        Music& next = g_musicTracks[g_currentTrack];
        if (next.ctxData) {
            StopMusicStream(next);   // Reset to beginning
            PlayMusicStream(next);
        }
    }

    // Start music if nothing is playing yet (first frame)
    if (current.ctxData && !IsMusicStreamPlaying(current)) {
        PlayMusicStream(current);
    }
}
```

**Important:** Call `UpdateMusic()` at the top of your game loop body — including during splash screens. If your splash screen returns early from the main game loop (before the normal UpdateMusic call point), add an extra `UpdateMusic()` call inside the splash drawing function.

### D.6 Sound Effects — Triggering at Events

Play sounds at game events using `PlaySound()`:

```cpp
// Simple immediate SFX
if (trainBuiltSuccessfully) {
    if (g_sfxBuildTrain.frameCount) PlaySound(g_sfxBuildTrain);
}

// Chained SFX with delay (e.g., factory built → then system sound 0.15s later)
if (factoryBuiltSuccessfully) {
    if (g_sfxFactoryBuilt.frameCount) PlaySound(g_sfxFactoryBuilt);
    g_pendingSfxActive = true;
    g_pendingSfxTimer = 0.15f;
}
```

Process the pending SFX timer at the top of your game loop:

```cpp
// In GameLoopBody(), near the top:
float dt = GetFrameTime();
if (g_pendingSfxActive) {
    g_pendingSfxTimer -= dt;
    if (g_pendingSfxTimer <= 0.0f) {
        g_pendingSfxActive = false;
        if (g_sfxBuildSys.frameCount) PlaySound(g_sfxBuildSys);
    }
}
```

### D.7 Volume System (3-Level: LOW / MID / HIGH)

Use a simple 3-level system mapped to float values:

| Level | Value | Float |
|-------|-------|-------|
| LOW   | 0     | 0.25f |
| MID   | 1     | 0.50f |
| HIGH  | 2     | 1.00f |

Apply with `SetMusicVolume(track, vol)` and `SetSoundVolume(sfx, vol)`. Call `ApplyMusicVolume()` / `ApplySfxVolume()` whenever the user changes settings.

### D.8 Options Screen Pattern

Provide an in-game options overlay accessible via a hotkey (e.g., O). Implementation pattern:

```cpp
enum class OptionsScreen { Hidden, Visible };
static OptionsScreen g_optionsScreen = OptionsScreen::Hidden;
static int g_optionsSelection = 0;  // 0=music, 1=sfx, 2=gamma

static void HandleOptionsInput() {
    // UP/DOWN to change row
    if (CustomIsKeyPressed(KEY_UP))   g_optionsSelection = (g_optionsSelection + 2) % 3;
    if (CustomIsKeyPressed(KEY_DOWN)) g_optionsSelection = (g_optionsSelection + 1) % 3;

    // LEFT/RIGHT to change value
    int* target = nullptr;
    if (g_optionsSelection == 0) target = &g_musicVolume;
    else if (g_optionsSelection == 1) target = &g_sfxVolume;
    else target = &g_gammaLevel;

    if (CustomIsKeyPressed(KEY_LEFT)  && *target > 0) (*target)--;
    if (CustomIsKeyPressed(KEY_RIGHT) && *target < 2) (*target)++;

    ApplyMusicVolume();
    ApplySfxVolume();

    // ESC or ENTER or O to close
    if (CustomIsKeyPressed(KEY_ESCAPE) || CustomIsKeyPressed(KEY_ENTER) ||
        CustomIsKeyPressed(KEY_O)) {
        g_optionsScreen = OptionsScreen::Hidden;
    }
}

static void DrawOptionsScreen() {
    // Semi-transparent dark overlay
    DrawRectangle(0, 0, g_renderWidth, g_renderHeight, (Color){0, 0, 0, 180});

    // Draw title, rows with [LOW] [MID] [HIGH] indicators
    // Highlight selected row and current value
    // (Use DrawTextEx with your game font for consistent style)
}
```

In your game loop, toggle with O and add to your modal guard:

```cpp
bool anyModalOpen = g_helpModalOpen || g_introModalOpen ||
                    (g_optionsScreen == OptionsScreen::Visible);

// O key handler (allow toggle even when options is the active modal)
if (CustomIsKeyPressed(KEY_O) && (!anyModalOpen ||
    g_optionsScreen == OptionsScreen::Visible)) {
    g_optionsScreen = (g_optionsScreen == OptionsScreen::Visible)
        ? OptionsScreen::Hidden : OptionsScreen::Visible;
}
```

### D.9 Gamma Overlay

Simple gamma control using a fullscreen rectangle overlay drawn last (before the cursor):

```cpp
static void DrawGammaOverlay() {
    if (g_gammaLevel == 0) {
        // LOW gamma = darken screen
        DrawRectangle(0, 0, g_renderWidth, g_renderHeight, (Color){0, 0, 0, 120});
    } else if (g_gammaLevel == 2) {
        // HIGH gamma = brighten screen
        DrawRectangle(0, 0, g_renderWidth, g_renderHeight, (Color){255, 255, 255, 60});
    }
    // MID (1) = no overlay, normal brightness
}
```

Draw this **after** all game content but **before** the custom cursor, in every render path (3D view, map view, and splash screens).

### D.10 Audio Cleanup

#### Embedded Mode (`CleanupGame()`)
```cpp
__declspec(dllexport) void CleanupGame() {
    UnloadAudioAssets();   // Stop and unload all music/sfx FIRST
    UnloadUIAssets();
    // ... framebuffer cleanup ...
    if (g_audio_initialized) {
        CloseAudioDevice();
        g_audio_initialized = false;
    }
}
```

#### Game-Over / Restart Reset
When restarting to splash after game over, reset audio state:

```cpp
static void RestartToSplashAfterGameOver() {
    // Stop current music, reset to track 0
    for (int i = 0; i < 3; i++) {
        if (g_musicTracks[i].ctxData) StopMusicStream(g_musicTracks[i]);
    }
    g_currentTrack = 0;
    if (g_musicTracks[0].ctxData) PlayMusicStream(g_musicTracks[0]);

    // Reset volumes to defaults
    g_musicVolume = 1;  // MID
    g_sfxVolume = 1;    // MID
    g_gammaLevel = 1;   // MID
    ApplyMusicVolume();
    ApplySfxVolume();

    // Reset pending SFX
    g_pendingSfxActive = false;
    g_pendingSfxTimer = 0.0f;

    // ... rest of restart logic ...
}
```

### D.11 Audio File Organization

```
Data/games/YourGame/
├── Audio/
│   ├── YourGame_Track1.mp3    # Background music (MP3 for size)
│   ├── YourGame_Track2.mp3
│   ├── YourGame_Track3.mp3
│   ├── BUILD-Train.wav        # Sound effects (WAV for low latency)
│   ├── BUILD-Sys.wav
│   ├── Factory-Built.wav
│   ├── Bureau-BUILT.wav
│   └── SILO-Built.wav
├── src/
│   ├── cybertrain_core.cpp    # Audio globals here
│   ├── cybertrain_exports.cpp # InitAudioDevice + LoadAudioAssets
│   ├── cybertrain_ui.cpp      # Audio functions + options screen
│   └── cybertrain_gameloop.cpp# UpdateMusic + SFX triggers
└── main.cpp                   # Unity build includes all src/*.cpp
```

**Format guidance:**
- Use **MP3** for music tracks (smaller files, streaming playback)
- Use **WAV** for sound effects (zero decode latency, instant playback)

### D.12 Common Audio Pitfalls

| Problem | Cause | Fix |
|---------|-------|-----|
| Crackling/stuttering music | Default 4096 buffer too small | `SetAudioStreamBufferSizeDefault(16384)` before `InitAudioDevice()` |
| Sounds don't play in embedded mode | `InitAudioDevice()` never called | Add it to `InitializeGame()` DLL export |
| Music stops after first track | `m.looping = true` (default) causes single-track loop | Set `m.looping = false`, implement manual track advancement |
| Linker error: undefined LoadAudioAssets | Unity build order: exports before ui | Add `static void LoadAudioAssets();` forward declaration in exports |
| Audio files not found | CWD differs between standalone and embedded | Use multi-path fallback pattern (4 prefixes) |
| Volume changes don't take effect | Forgot to call Apply after changing level | Always call `ApplyMusicVolume()` / `ApplySfxVolume()` after changes |
| Crash on cleanup | Unloading already-freed audio | Check `ctxData != NULL` / `frameCount > 0` before unloading |

---

## Part 8: Advanced Optimization & BBS Integration

### 8.1 "Heavy Session" Optimization (`main.py`)

For games with high GPU/CPU demand, the BBS core (`main.py`) supports a "Heavy Session" mode that freezes background processing:

1.  **Background Freeze:** The BBS captures a freeze-frame of the desktop and pauses background `.mp4` video decoding. This frees up GPU bandwidth for the DLL's `rlReadTexturePixels` calls.
2.  **Video Switching:** The system automatically switches to the `-os` variant of background videos (e.g., `Audio-Desktop-os.mp4`) when an embedded game is active to ensure visual consistency.

Implementation in `main.py`:
```python
def _is_embedded_dll_game_active(self) -> bool:
    return (self.state == "game_session" and 
            isinstance(self.active_game_session, (AstroMinerSession, CyberTrainSession)))
```

### 8.2 Robust DLL Handshake (`game_embed.py`)

1.  **CWD Persistence:** Your Python embed module must change the current working directory to the game's folder *before* initialization and keep it there or handle relative paths carefully. This is critical for loading shaders, textures, and fonts.
2.  **Resolution Handshake:** Call `SetRenderResolution` *before* `InitializeGame`. This allows the C++ engine to allocate the correct buffer size from the start, avoiding costly reallocations.

### 8.3 Performance Engine Settings (`main.cpp`)

To achieve AstroMiner-level performance:

1.  **Unlimited FPS:** In embedded mode, use `SetTargetFPS(0)`. The BBS handles the loop timing; limiting FPS in the DLL creates artificial latency.
2.  **Audio Initialization:** Always call `InitAudioDevice()` inside `InitializeGame`. Raylib may hang if it attempts to load sounds without an active audio context.
3.  **MSAA Warning:** Avoid high MSAA (Multi-Sampling) levels in embedded mode, as they significantly increase the time `rlReadTexturePixels` takes to transfer data from GPU to CPU.

### 8.4 UI Scaling with Camera2D

Since the game renders at a low resolution (e.g., 600x400) but uses a virtual coordinate space (1200x800), use a dedicated `Camera2D` for UI elements:

```cpp
// UI Scaling Camera (Virtual 1200x800 -> Render Width/Height)
float uiScaleX = (float)g_renderWidth / (float)VIRTUAL_WIDTH;
Camera2D uiCam = { 0 };
uiCam.zoom = g_standalone_mode ? 1.0f : uiScaleX;

BeginMode2D(uiCam);
DrawTextEx(gameFont, "HUD Element", (Vector2){10, 10}, 20, 0, WHITE);
EndMode2D();
```

### 8.5 Live BBS Synchronization

1.  **Username Sync:** The BBS periodically calls `SetUsername`. Display this in your HUD to increase immersion.
2.  **Leaderboard Integration:** Use `GetLastFinalScore` to report scores to the BBS. The BBS will automatically handle uploading these to the Steam Leaderboard API.

---

## Summary

The key principles for BBS C++ game integration:

1. **Hidden Window**: Create raylib window with `FLAG_WINDOW_HIDDEN`
2. **Framebuffer Rendering**: All drawing to `RenderTexture2D` via `BeginTextureMode()`
3. **Input Forwarding**: Use custom input state, not raylib's built-in functions
4. **Low Resolution**: Render at 600x400 or similar for performance
5. **Desktop Positioning**: Game renders at baseline (176, 209) scaled to screen
6. **Clean Separation**: DLL handles game logic, Python handles OS integration
7. **Zoom Awareness**: BBS zoom (`Shift++/-`) is handled by `main.py` before game events. During game sessions it uses a lightweight desktop-region crop-and-scale (no FPS impact). Mouse events are auto-transformed to unzoomed coordinates. If your game needs its own zoom, use `Ctrl+Shift++/-` or mouse wheel.

### Critical Checklist (Common Mistakes)

| ✅ Do | ❌ Don't |
|-------|---------|
| Use `CustomIsMouseButtonPressed()` | Use `IsMouseButtonPressed()` |
| Use `CustomGetMousePosition()` | Use `GetMousePosition()` |
| Set `g_standalone_mode = false` in DLL mode | Leave it `true` |
| Call `ClearInputFrame()` at end of frame | Forget to clear one-shot events |
| Restore CWD in `finally` block | Leave CWD changed after init |
| Set resolution BEFORE `InitializeGame()` | Set it after |
| Use global `g_` prefixed variables | Use local static in wrong scope |
| Export functions with `extern "C"` | Let C++ mangle function names |
| Check `_has_*` flags before optional calls | Assume all DLL functions exist |
| Rebuild DLL after C++ changes | Test with stale DLL |

### Quick Reference: File Locations

```
Data/games/
├── registry.py              # Session adapters (KEY_MAP, MOUSE_BUTTON_MAP)
├── yourgame_embed.py        # Python-DLL bridge (ctypes)
└── YourGame/
    ├── main.cpp             # C++ game source
    ├── build_dll.bat        # Build script
    ├── yourgame.dll         # Compiled game (build output)
    ├── raylib.dll           # Raylib runtime (required)
    ├── libgcc_s_seh-1.dll   # MinGW runtime
    ├── libstdc++-6.dll      # MinGW C++ runtime
    └── libwinpthread-1.dll  # MinGW threading
```

### Quick Reference: Function Signatures

| Python Function | C++ Export | Purpose |
|-----------------|------------|---------|
| `initialize()` | `InitializeGame()` | Create framebuffer, load resources |
| `get_frame_surface()` | `UpdateFrame()` + `GetFrameBuffer()` | Get rendered frame |
| `set_key_state(key, down)` | `SetKeyState(int, bool)` | Forward keyboard |
| `set_mouse_button_state(btn, down)` | `SetMouseButtonState(int, bool)` | Forward mouse click |
| `set_mouse_position(x, y)` | `SetInputMousePosition(float, float)` | Forward mouse pos |
| `set_mouse_delta(dx, dy)` | `SetMouseDelta(float, float)` | Forward mouse movement |
| `set_mouse_wheel(move)` | `SetMouseWheelMove(float)` | Forward scroll wheel |
| `should_exit()` | `ShouldExit()` | Check if game wants quit |
| `cleanup()` | `CleanupGame()` | Release resources |

Follow this guide to integrate any C++ raylib game seamlessly into the GlyphisIO BBS!

