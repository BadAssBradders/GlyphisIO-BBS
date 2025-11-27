# Quick Build Guide for astrominer.dll

## The Problem
The C++ code needs to be compiled into a DLL, but raylib headers need to be available.

## Option 1: Install Raylib System-Wide

1. **Download Raylib for Windows:**
   - Go to: https://github.com/raysan5/raylib/releases
   - Download the latest Windows release (e.g., `raylib-5.0_win64_mingw-w64.zip`)

2. **Extract and Install:**
   - Extract to a location like `C:\raylib`
   - Add `C:\raylib\include` to your compiler's include path
   - Add `C:\raylib\lib` to your compiler's library path

3. **Compile:**
   ```bash
   cd "E:\Dev\Glyphis_IO BBS The Proxy Tapes\Data\games\AstroMiner"
   g++ astro_miner_main.cpp -o astrominer.dll -shared -lraylib -lopengl32 -lgdi32 -lwinmm -std=c++11
   ```

## Option 2: Use Local Raylib (Recommended)

1. **Download Raylib:**
   - Download from: https://github.com/raysan5/raylib/releases
   - Extract to `Data/games/AstroMiner/raylib/`

2. **Compile with paths:**
   ```bash
   cd "E:\Dev\Glyphis_IO BBS The Proxy Tapes\Data\games\AstroMiner"
   g++ astro_miner_main.cpp -o astrominer.dll -shared -I"./raylib/include" -L"./raylib/lib" -lraylib -lopengl32 -lgdi32 -lwinmm -std=c++11
   ```

## Option 3: Use the Batch File

Just run:
```bash
build_dll.bat
```

(You'll need to edit it first to add raylib paths if needed)

## Important Notes

⚠️ **The C++ code still needs modifications!**

The current code has the export functions, but the game loop still renders to a window. You need to:

1. Wrap the entire game loop to render to `g_framebuffer` using `BeginTextureMode()`/`EndTextureMode()`
2. Implement the `UpdateFrame()` function that runs one game frame
3. Remove `BeginDrawing()`/`EndDrawing()` calls (render directly to texture)

See `EMBEDDING_INSTRUCTIONS.md` for details.

## After Building

Once `astrominer.dll` is created, make sure:
- `astrominer.dll` is in `Data/games/AstroMiner/`
- `raylib.dll` is in `Data/games/AstroMiner/` (should already be there)

Then the Python code should be able to load it!

