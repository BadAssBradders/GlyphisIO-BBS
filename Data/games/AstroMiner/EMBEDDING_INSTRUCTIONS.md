# Astro Miner Embedding Instructions

## Overview
This document explains how to compile Astro Miner as a DLL that can be embedded into the Pygame BBS application.

## Architecture
- **C++ Game**: Renders to an offscreen texture (RenderTexture2D) instead of a window
- **Python Module**: Loads the DLL and retrieves framebuffer data each frame
- **Pygame Integration**: Displays the framebuffer as a Surface, then draws scanlines on top

## C++ Modifications Required

### 1. Wrap the entire game loop to render to texture

The main game loop (the `while (!WindowShouldClose())` loop) needs to be wrapped like this:

```cpp
BeginTextureMode(g_framebuffer);
ClearBackground(BLACK);

// Your existing game drawing code here
// All BeginDrawing() calls should be removed
// All EndDrawing() calls should be removed
// The game should render directly to the texture

EndTextureMode();
```

### 2. Export a function to run one game frame

Create a function that runs one frame of the game:

```cpp
__declspec(dllexport) void UpdateFrame() {
    // Update game logic
    // Handle input
    // Render to g_framebuffer using BeginTextureMode/EndTextureMode
    // This will be called each frame from Python
}
```

### 3. Compile as DLL

```bash
g++ astro_miner_main.cpp -o astrominer.dll -shared -lraylib -lopengl32 -lgdi32 -lwinmm
```

Place `astrominer.dll` and `raylib.dll` in the `Data/games/AstroMiner/` directory.

## Current Status

✅ **Completed:**
- Python module (`astrominer_embed.py`) to load DLL and get frames
- Updated `AstroMinerSession` to use framebuffer approach
- C export function stubs added
- Framebuffer initialization code added

⚠️ **Still Needed:**
- Modify game loop to render to texture instead of window
- Implement `UpdateFrame()` function that runs one game frame
- Remove all `BeginDrawing()`/`EndDrawing()` calls (replace with texture rendering)
- Test compilation and DLL loading

## Notes

- The game window will be hidden (FLAG_WINDOW_HIDDEN)
- All rendering goes to the offscreen texture
- Python retrieves the texture data each frame
- Pygame displays it at the desktop position, then scanlines draw on top
- This creates a seamless integration - the game appears "within" the BBS

