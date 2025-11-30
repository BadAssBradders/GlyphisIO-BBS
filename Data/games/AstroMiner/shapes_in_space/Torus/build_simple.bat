@echo off
REM Simple build script that works from any directory
REM Can be called from Notepad++

REM Get the script's directory
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

REM Check for g++ in common locations
set "GPP_PATH="
where g++ >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set "GPP_PATH=g++"
) else if exist "C:\raylib\w64devkit\bin\g++.exe" (
    set "GPP_PATH=C:\raylib\w64devkit\bin\g++.exe"
    set "PATH=C:\raylib\w64devkit\bin;%PATH%"
) else if exist "C:\w64devkit\bin\g++.exe" (
    set "GPP_PATH=C:\w64devkit\bin\g++.exe"
    set "PATH=C:\w64devkit\bin;%PATH%"
) else (
    echo ERROR: g++ compiler not found
    echo Please install MinGW-w64 or w64devkit
    pause
    exit /b 1
)

REM Create directories
if not exist "bin" mkdir bin
if not exist "build" mkdir build

REM Build
echo Building with %GPP_PATH%...
%GPP_PATH% -std=c++17 -O2 -I C:/raylib/include src/main.cpp -L C:/raylib/lib -lraylib -lwinmm -lgdi32 -o bin/Torus.exe

if %ERRORLEVEL% EQU 0 (
    echo Build successful!
    copy "C:\raylib\lib\raylib.dll" "bin\" >nul 2>&1
    echo Executable: bin\Torus.exe
) else (
    echo Build failed!
    pause
    exit /b 1
)

