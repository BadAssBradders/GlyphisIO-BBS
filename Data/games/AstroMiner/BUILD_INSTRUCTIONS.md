# Building astrominer.dll

## Prerequisites

1. **C++ Compiler**: MinGW-w64 (g++) or MSVC
2. **Raylib**: The raylib library and headers
3. **raylib.dll**: Must be in the same directory as the compiled DLL

## Option 1: Using MinGW-w64 (Recommended)

### Install MinGW-w64
- Download from: https://www.mingw-w64.org/downloads/
- Or use MSYS2: https://www.msys2.org/
- Make sure `g++` is in your PATH

### Compile

```bash
cd Data/games/AstroMiner
g++ astro_miner_main.cpp -o astrominer.dll -shared -lraylib -lopengl32 -lgdi32 -lwinmm -std=c++11
```

Or use the provided batch file:
```bash
build_dll.bat
```

### If raylib is not in system paths

If raylib is installed locally, you may need to specify paths:

```bash
g++ astro_miner_main.cpp ^
    -o astrominer.dll ^
    -shared ^
    -I"C:/path/to/raylib/include" ^
    -L"C:/path/to/raylib/lib" ^
    -lraylib ^
    -lopengl32 ^
    -lgdi32 ^
    -lwinmm ^
    -std=c++11
```

## Option 2: Using MSVC (Visual Studio)

```cmd
cl /LD astro_miner_main.cpp /Fe:astrominer.dll /link raylib.lib opengl32.lib gdi32.lib winmm.lib
```

## Required Files

After compilation, you need:
- `astrominer.dll` - The compiled game DLL
- `raylib.dll` - Raylib runtime (should already be in the directory)

Both files should be in: `Data/games/AstroMiner/`

## Troubleshooting

### "raylib.h: No such file or directory"
- Install raylib or specify the include path with `-I`
- Download raylib from: https://github.com/raysan5/raylib/releases

### "undefined reference to raylib functions"
- Link against raylib library with `-lraylib`
- Make sure raylib is compiled or use a pre-built version

### "raylib.dll not found"
- Copy `raylib.dll` to `Data/games/AstroMiner/`
- The DLL should be in the same directory as `astrominer.dll`

### "g++ not found"
- Add MinGW-w64 bin directory to your PATH
- Or use the full path to g++.exe

## Testing

After building, the Python code should be able to load the DLL:
```python
from games.astrominer_embed import initialize
if initialize():
    print("DLL loaded successfully!")
```

