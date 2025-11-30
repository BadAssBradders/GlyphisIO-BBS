@echo off
REM Run the game with terminal/console open
REM Shows output and keeps terminal visible

REM Ensure we are running from the script's directory
cd /d "%~dp0"

if not exist "bin\Icosahedron.exe" (
    echo Executable not found. Building first...
    call build_simple.bat
    echo.
)

if exist "bin\Icosahedron.exe" (
    echo.
    echo ========================================
    echo Running Icosahedron Game
    echo ========================================
    echo Terminal will stay open while game runs.
    echo Close the game window, then press any key here to exit.
    echo.
    "bin\Icosahedron.exe"
    echo.
    echo Game closed.
    pause
) else (
    echo ERROR: Could not build or find Icosahedron.exe
    pause
)

