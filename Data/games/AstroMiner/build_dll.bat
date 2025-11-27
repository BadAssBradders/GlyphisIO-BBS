@echo off
REM Build script for Astro Miner DLL
REM This compiles astro_miner_main.cpp into astrominer.dll

echo Building astrominer.dll...

REM Check if g++ is available
where g++ >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: g++ not found in PATH
    echo Please install MinGW-w64 or MSYS2 and add it to your PATH
    pause
    exit /b 1
)

REM Compile to DLL
REM Note: You may need to adjust the raylib include and library paths
REM If raylib is installed system-wide, this should work
REM If not, you may need: -I"path/to/raylib/include" -L"path/to/raylib/lib"

g++ astro_miner_main.cpp ^
    -o astrominer.dll ^
    -shared ^
    -I"E:\Dev\raylib\include" ^
    -L"E:\Dev\raylib\lib" ^
    -lraylibdll ^
    -lopengl32 ^
    -lgdi32 ^
    -lwinmm ^
    -std=c++11

if %ERRORLEVEL% EQU 0 (
    echo.
    echo SUCCESS: astrominer.dll created!
    echo.
    echo Make sure raylib.dll is in the same directory as astrominer.dll
    echo The DLL should be at: Data\games\AstroMiner\astrominer.dll
) else (
    echo.
    echo ERROR: Compilation failed
    echo.
    echo Common issues:
    echo 1. raylib not found - install raylib or specify include/lib paths
    echo 2. Missing raylib.dll - copy raylib.dll to this directory
    echo 3. Wrong compiler - make sure you're using g++ from MinGW-w64
)

pause

