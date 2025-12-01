@echo off
REM Build script for Astro Miner Standalone Executable
REM This compiles astro_miner_main.cpp into astrominer.exe for standalone debugging

echo Building astrominer.exe (standalone)...

REM Check if g++ is available
where g++ >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: g++ not found in PATH
    echo Please install MinGW-w64 or MSYS2 and add it to your PATH
    pause
    exit /b 1
)

REM Compile to standalone executable (not DLL)
g++ astro_miner_main.cpp ^
    -o astrominer.exe ^
    -I"E:\Dev\raylib\include" ^
    -L"E:\Dev\raylib\lib" ^
    -lraylib ^
    -lopengl32 ^
    -lgdi32 ^
    -lwinmm ^
    -std=c++11

if %ERRORLEVEL% EQU 0 (
    echo.
    echo SUCCESS: astrominer.exe created!
    echo.
    echo You can now run it standalone for debugging:
    echo   - Double-click astrominer.exe
    echo   - Or run: run_standalone.bat
    echo.
    echo Make sure raylib.dll and MinGW runtime DLLs are in the same directory:
    echo   - raylib.dll
    echo   - libgcc_s_seh-1.dll
    echo   - libstdc++-6.dll
    echo   - libwinpthread-1.dll
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

