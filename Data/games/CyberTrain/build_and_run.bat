@echo off
REM Build and run script for CyberTrain standalone version
REM Based on working Torus project pattern
REM Can be called from Notepad++
REM
REM NOTE: This uses the SAME main.cpp source as build_dll.bat
REM       For unified builds of both versions, use build_both.bat instead
echo [INFO] This script validates standalone EXE behavior only.
echo [INFO] For BBS embedding, use build_dll.bat to rebuild cybertrain.dll.
echo.

REM Get the script's directory
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo Building Wireframe City Skyline...
echo.

REM Check for g++ in common locations
set "GPP_PATH="
where g++ >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set "GPP_PATH=g++"
    echo Found g++ in PATH
) else if exist "C:\raylib\w64devkit\bin\g++.exe" (
    set "GPP_PATH=C:\raylib\w64devkit\bin\g++.exe"
    set "PATH=C:\raylib\w64devkit\bin;%PATH%"
    echo Found w64devkit g++ at C:\raylib\w64devkit\bin
) else if exist "C:\raylib\raylib\w64devkit\bin\g++.exe" (
    set "GPP_PATH=C:\raylib\raylib\w64devkit\bin\g++.exe"
    set "PATH=C:\raylib\raylib\w64devkit\bin;%PATH%"
    echo Found w64devkit g++ at C:\raylib\raylib\w64devkit\bin
) else if exist "C:\w64devkit\bin\g++.exe" (
    set "GPP_PATH=C:\w64devkit\bin\g++.exe"
    set "PATH=C:\w64devkit\bin;%PATH%"
    echo Found w64devkit g++ at C:\w64devkit\bin
) else (
    echo ERROR: g++ compiler not found
    echo Please install MinGW-w64 or w64devkit
    pause
    exit /b 1
)

REM Auto-detect Raylib location (check for include/raylib.h)
set "RAYLIB_PATH="
if exist "C:\raylib\include\raylib.h" (
    set "RAYLIB_PATH=C:\raylib"
    echo Found Raylib at C:\raylib
) else if exist "C:\raylib\raylib\include\raylib.h" (
    set "RAYLIB_PATH=C:\raylib\raylib"
    echo Found Raylib at C:\raylib\raylib
) else (
    echo ERROR: Raylib not found!
    echo Please ensure Raylib is installed at C:\raylib or C:\raylib\raylib
    echo Looking for: C:\raylib\include\raylib.h or C:\raylib\raylib\include\raylib.h
    pause
    exit /b 1
)

REM Verify Raylib files exist
if not exist "%RAYLIB_PATH%\include\raylib.h" (
    echo ERROR: raylib.h not found at %RAYLIB_PATH%\include\raylib.h
    pause
    exit /b 1
)

echo Using Raylib from: %RAYLIB_PATH%
echo.

REM Create output directory
if not exist "bin" mkdir bin

REM Build
echo Compiling...
%GPP_PATH% -std=c++17 -O2 -I "%RAYLIB_PATH%\include" -L "%RAYLIB_PATH%\lib" main.cpp -lraylib -lwinmm -lgdi32 -o bin\CyberTrain.exe

if %ERRORLEVEL% EQU 0 (
    echo Build successful!
    echo.
    echo Copying raylib.dll...
    if exist "%RAYLIB_PATH%\lib\raylib.dll" (
        copy "%RAYLIB_PATH%\lib\raylib.dll" "bin\" >nul 2>&1
        echo DLL copied successfully.
    ) else (
        echo WARNING: raylib.dll not found at %RAYLIB_PATH%\lib\raylib.dll
    )
    echo.
    echo Executable: bin\CyberTrain.exe
    echo.
    echo Running game...
    echo.
    bin\CyberTrain.exe
    echo.
    echo Game closed.
) else (
    echo.
    echo ========================================
    echo Build failed!
    echo ========================================
    echo.
    echo Common issues:
    echo   1. Make sure g++ compiler is accessible
    echo   2. Verify Raylib files exist at %RAYLIB_PATH%\include\raylib.h
    echo   3. Check error messages above for specific issues
    echo.
    pause
    exit /b 1
)

pause

