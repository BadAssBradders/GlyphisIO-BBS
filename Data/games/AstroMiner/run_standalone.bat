@echo off
REM Quick launcher for standalone Astro Miner (for debugging)
REM Builds and runs the game outside the BBS environment

echo ========================================
echo Astro Miner - Standalone Debug Launcher
echo ========================================
echo.

REM Change to script directory
cd /d "%~dp0"

REM Always rebuild to pick up changes
echo Rebuilding astrominer.exe...
call build_standalone.bat
if %ERRORLEVEL% NEQ 0 (
    echo Build failed!
    pause
    exit /b 1
)

REM Check for required DLLs
if not exist "raylib.dll" (
    echo WARNING: raylib.dll not found in current directory
    echo The game may not run without it.
    echo.
)

REM Run the game
echo.
echo Launching Astro Miner standalone...
echo Press ESC or close window to exit
echo.
astrominer.exe

REM Check exit code
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Game exited with error code: %ERRORLEVEL%
    pause
)
