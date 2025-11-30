# Icosahedron - Raylib C++ Game Project

A game project using Raylib and C++ in Visual Studio.

## Prerequisites

- Visual Studio 2019 or later (with C++ desktop development workload)
- Raylib library

## Setup Instructions

### 1. Download Raylib

1. Visit the [Raylib releases page](https://github.com/raysan5/raylib/releases)
2. Download the latest Windows release (e.g., `raylib-5.0-w64-msvc16.zip` for Visual Studio 2019/2022)
3. Extract the downloaded ZIP file to a convenient location (e.g., `C:\raylib`)

### 2. Configure Visual Studio Environment Variable

You need to set the `RAYLIB_PATH` environment variable to point to your Raylib installation:

1. Open Visual Studio
2. Go to **Project** → **Properties** (or right-click the project → **Properties**)
3. Navigate to **Configuration Properties** → **VC++ Directories**
4. Alternatively, you can set a user environment variable:
   - Press `Win + R`, type `sysdm.cpl`, press Enter
   - Go to **Advanced** tab → **Environment Variables**
   - Under **User variables**, click **New**
   - Variable name: `RAYLIB_PATH`
   - Variable value: Path to your Raylib folder (e.g., `C:\raylib`)

### 3. Alternative: Manual Configuration (if environment variable doesn't work)

If you prefer not to use an environment variable, you can manually edit the project file:

1. Right-click the project in Solution Explorer → **Properties**
2. Go to **Configuration Properties** → **C/C++** → **General**
3. In **Additional Include Directories**, add: `C:\raylib\include` (or your Raylib path)
4. Go to **Configuration Properties** → **Linker** → **General**
5. In **Additional Library Directories**, add: `C:\raylib\lib` (or your Raylib path)
6. Go to **Configuration Properties** → **Linker** → **Input**
7. In **Additional Dependencies**, ensure `raylib.lib` and `winmm.lib` are present

### 4. Copy DLL to Output Directory

1. Copy `raylib.dll` from your Raylib `lib` folder to:
   - `bin\x64\Debug\` (for Debug builds)
   - `bin\x64\Release\` (for Release builds)

Or set up a post-build event in Visual Studio:
1. Right-click project → **Properties**
2. Go to **Configuration Properties** → **Build Events** → **Post-Build Event**
3. Add command: `copy "$(RAYLIB_PATH)\lib\raylib.dll" "$(OutDir)"`

### 5. Build and Run

1. Open `Icosahedron.sln` in Visual Studio
2. Select **x64** as the platform (important!)
3. Build the solution (F7 or **Build** → **Build Solution**)
4. Run the project (F5 or **Debug** → **Start Debugging**)

## Project Structure

```
Icosahedron/
├── src/
│   ├── main.cpp      # Main game code
│   └── main.h        # Header file
├── bin/              # Output directory (created on build)
├── obj/              # Intermediate files (created on build)
├── Icosahedron.sln         # Visual Studio solution file
├── Icosahedron.vcxproj     # Visual Studio project file
└── README.md         # This file
```

## Building with Notepad++ (or any text editor)

If you prefer to edit code in Notepad++ or another text editor:

1. **Edit your code** in Notepad++ (or your preferred editor)
   - Main game code: `src/main.cpp`

2. **Build the project** using one of these methods:
   - **Double-click `build.bat`** - Builds Debug version
   - **Double-click `build_release.bat`** - Builds Release version (optimized)
   - **Double-click `run.bat`** - Builds and runs the game automatically

3. **Run the game**:
   - After building, run: `bin\x64\Debug\Icosahedron.exe` (or Release version)
   - Or use `run.bat` to build and run in one step

The build scripts will automatically:
- Check for RAYLIB_PATH environment variable
- Find MSBuild (Visual Studio compiler)
- Build the project
- Copy raylib.dll to the output directory

**Note:** You still need Visual Studio (or Visual Studio Build Tools) installed for the compiler, but you don't need to open the IDE - just use the build scripts!

## Next Steps

- Start coding your game in `src/main.cpp`
- Edit in Notepad++, then run `build.bat` to compile
- Check out the [Raylib documentation](https://www.raylib.com/cheatsheet/cheatsheet.html) for API reference
- Visit [Raylib examples](https://www.raylib.com/examples.html) for inspiration

## Troubleshooting

- **"Cannot open include file: 'raylib.h'"**: Make sure `RAYLIB_PATH` is set correctly or manually configure include directories
- **"Unresolved external symbol" errors**: Check that `raylib.lib` is in Additional Dependencies and the library path is correct
- **"raylib.dll not found"**: Copy the DLL to your output directory (see step 4 above)
- **Build fails with x86**: Make sure you're building for x64 platform, not x86

## Resources

- [Raylib Official Website](https://www.raylib.com/)
- [Raylib GitHub](https://github.com/raysan5/raylib)
- [Raylib Cheat Sheet](https://www.raylib.com/cheatsheet/cheatsheet.html)

