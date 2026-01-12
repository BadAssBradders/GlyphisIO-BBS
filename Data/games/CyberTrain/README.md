# CyberTrain - Railway Builder (Raylib C++)

`CyberTrain` is a small 3D railway/route-building sandbox built with Raylib. You place track tiles, stations, depots, and trains, then configure junction routing per-train.

The scene includes a procedurally generated “cyber city” skyline backdrop (red buildings on a black background).

## Features

- **Track building**: Place cyan track tiles on a 5×5 grid.
- **Stations**: Place 4-tile Station-Track segments (dark cyan).
- **Trains**:
  - **Passenger trains**: 4-car green train (spans 4 tiles).
  - **Cargo trains**: Locomotive + 1–3 trailers (each trailer adds capacity).
- **Junctions (Points platforms)**: Any rail tile with 3+ neighbors becomes a junction (red); when a train is selected, it shows green “editable” indicators and you can cycle that train’s exit choice by clicking the junction.
- **Materials depots**: Place depot tiles (gray) adjacent to station tiles; adjacent depots merge into a shared storage cluster.
- **Cargo transfer**: Cargo trains start loaded; when passing a station, they drop cargo into the best adjacent depot cluster (by free space). When empty, they pick up cargo from the best adjacent cluster (by stored cargo).
- **Map view**: Toggle a top-down 2D map with panning/zooming.

## Requirements

- C++17 or later
- A C++ compiler (MinGW g++, MSVC cl.exe, or clang++)
- Raylib library

## Building

### Windows (Notepad++) - RECOMMENDED

**No CMake required!** Uses the same pattern as the working Torus project:

1. **Install Raylib** (if not already installed):
   - Download from https://www.raylib.com/
   - Extract to `C:\raylib` or `C:\raylib\raylib` (script auto-detects both)

2. **Install a C++ compiler** (if not already installed):
   - **w64devkit**: Often comes with Raylib at `C:\raylib\w64devkit\`
   - **MinGW-w64**: Download from https://www.mingw-w64.org/
   - Or add g++ to your system PATH

3. **Build and run**:
   - **Double-click `build_both.bat`** - **RECOMMENDED**: Builds BOTH standalone AND BBS versions from the same source (ensures they stay in sync!)
   - **Double-click `build_and_run.bat`** - Builds and runs the standalone version only
   - **Double-click `build_dll.bat`** - Builds the BBS DLL version only
   - **Double-click `run.bat`** - Runs the standalone game (after building)

4. **Or use Notepad++ with NppExec**:
   - Open `main.cpp` in Notepad++
   - Press F6 to open NppExec
   - Run: `cd "$(CURRENT_DIRECTORY)" && build_and_run.bat`
   - Or create a macro to run the batch file

**Note**: The build script automatically:
- Detects g++ compiler (checks PATH, w64devkit, and common locations)
- Finds Raylib at `C:\raylib` or `C:\raylib\raylib`
- Compiles the game
- Copies raylib.dll
- Runs the game

### Windows (Command Line - CMake Method)

**Note**: This requires CMake. If CMake is not installed, use the direct compilation method above.

1. Install Raylib and CMake:
   - Download Raylib from https://www.raylib.com/
   - Download CMake from https://cmake.org/

2. Build the project:
```bash
mkdir build
cd build
cmake ..
cmake --build .
```

### Linux

1. Install Raylib:
```bash
# Ubuntu/Debian
sudo apt-get install libraylib-dev

# Or build from source
git clone https://github.com/raysan5/raylib.git
cd raylib/src
make PLATFORM=PLATFORM_DESKTOP
sudo make install
```

2. Build the project:
```bash
mkdir build
cd build
cmake ..
make
```

### macOS

1. Install Raylib:
```bash
brew install raylib
# Or build from source (see Linux instructions)
```

2. Build the project:
```bash
mkdir build
cd build
cmake ..
make
```

## Running

After building, run the executable:
- **Windows (Easiest)**: Double-click `build_and_run.bat` (builds and runs) or `run.bat` (runs only)
- Windows (Manual): `bin\CyberTrain.exe`
- Linux/macOS: `./bin/CyberTrain`

## Controls

- **General / Camera**
  - **Arrows**: Pan camera
  - **Shift + Left/Right**: Rotate camera around the target
  - **+ / -**: Zoom
  - **ESC**: Deselect selected train (and Raylib also allows closing the window to exit)

- **Build / Place**
  - **Left Click** (default mode): Place a track tile
  - **T**: Toggle passenger train placement mode (requires Station-Track under the click)
  - **C**: Toggle cargo train placement mode; while in cargo mode press **C** again to cycle trailers (1–3) (requires Station-Track under the click)
  - **S**: Toggle Station-Track placement mode (places a 4-tile segment)
  - **R**: Rotate station orientation (while in station mode)
  - **D**: Toggle Materials-Depot placement mode (must be adjacent to a station tile)
  - **F**: Toggle Factory placement mode (must be adjacent to a depot; currently visual-only)

- **Selection / Routing**
  - **Click a train**: Select/deselect that train
  - **While a train is selected, click a junction (red tile)**: Cycle that train’s route choice at that junction

- **2D Map View**
  - **M**: Toggle map view
  - **WASD / Arrows**: Pan
  - **Middle-mouse drag**: Pan
  - **Mouse wheel**: Zoom

## Notes

- The world is grid-based: **grid size = 5.0 units**.
- Junction routing is **per train** (each train remembers its own junction exit settings).
- Track and stations are “rail”; depots are not part of the rail graph.

