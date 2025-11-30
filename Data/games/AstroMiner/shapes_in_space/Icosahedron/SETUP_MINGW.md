# Setting Up MinGW/GCC for Icosahedron Project

Since you're not using Visual Studio, you'll need MinGW/GCC compiler instead.

## Step 1: Install MinGW-w64

You have a few options:

### Option A: w64devkit (Easiest - Recommended)
1. Download from: https://github.com/skeeto/w64devkit/releases
2. Download the latest `w64devkit-x.x.x.zip`
3. Extract to a folder (e.g., `C:\w64devkit`)
4. Add to PATH:
   - Add `C:\w64devkit\bin` to your system PATH
   - Or run the build script from within that folder

### Option B: MSYS2
1. Download from: https://www.msys2.org/
2. Install MSYS2
3. Open MSYS2 terminal and run:
   ```bash
   pacman -S mingw-w64-x86_64-gcc make
   ```
4. Add `C:\msys64\mingw64\bin` to your PATH

### Option B: MinGW-w64 Standalone
1. Download from: https://www.mingw-w64.org/downloads/
2. Extract and add `bin` folder to PATH

## Step 2: Verify Installation

Open Command Prompt and run:
```cmd
g++ --version
```

You should see GCC version information. If you get "not recognized", add the MinGW bin folder to your PATH.

## Step 3: Verify Raylib (MinGW Version)

You already have the MinGW version of Raylib at `C:\raylib\lib\`:
- ✅ `libraylib.a` (MinGW library)
- ✅ `raylib.dll` (runtime DLL)

This is correct for MinGW!

## Step 4: Build Your Project

Now you can build using:

```cmd
build_mingw.bat
```

Or build and run:
```cmd
run_mingw.bat
```

## Alternative: Manual Build

If you prefer to build manually:

```cmd
g++ -std=c++17 -O2 -I C:/raylib/include src/main.cpp -L C:/raylib/lib -lraylib -lwinmm -lgdi32 -o bin/Icosahedron.exe
copy C:\raylib\lib\raylib.dll bin\
```

## Project Structure

```
Icosahedron/
├── src/
│   └── main.cpp          ← Your game code
├── Makefile              ← Build configuration
├── build_mingw.bat       ← Build script
├── run_mingw.bat         ← Build and run script
└── bin/
    └── Icosahedron.exe         ← Compiled game
```

## Troubleshooting

**"g++ not recognized"**
- Make sure MinGW is installed
- Add MinGW bin folder to your PATH
- Restart Command Prompt after changing PATH

**"libraylib.a not found"**
- Make sure you have the MinGW version of Raylib
- Check that `C:\raylib\lib\libraylib.a` exists

**Build errors**
- Make sure RAYLIB_PATH is set to `C:\raylib`
- Check that `C:\raylib\include\raylib.h` exists

## Next Steps

1. Install MinGW-w64 (w64devkit is easiest)
2. Verify `g++ --version` works
3. Run `build_mingw.bat`
4. Enjoy your star field game!

