@echo off
REM Run script for Wireframe City Skyline
REM Can be called from Notepad++

echo Running Wireframe City Skyline...
echo.

REM Check if executable exists
if exist "bin\CyberTrain.exe" (
    bin\CyberTrain.exe
) else (
    echo Executable not found! Please build the project first.
    echo Run build_and_run.bat to compile and run the project.
    pause
    exit /b 1
)

