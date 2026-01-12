@echo off
setlocal EnableDelayedExpansion
REM Unified build script for CyberTrain
REM Builds BOTH standalone (bin\CyberTrain.exe) AND BBS DLL (cybertrain.dll) from the same main.cpp
REM This ensures both versions are always in sync!

echo ========================================
echo CyberTrain Unified Build Script
echo Building BOTH standalone and BBS versions
echo ========================================
echo.

REM Get the script's directory
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

REM Check for g++ in common locations
set "GPP_PATH="
where g++ >nul 2>&1
if !ERRORLEVEL! EQU 0 (
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

REM Auto-detect Raylib location
set "RAYLIB_PATH="
if exist "E:\Dev\raylib\include\raylib.h" (
    set "RAYLIB_PATH=E:\Dev\raylib"
    echo Found Raylib at E:\Dev\raylib
) else if exist "C:\raylib\include\raylib.h" (
    set "RAYLIB_PATH=C:\raylib"
    echo Found Raylib at C:\raylib
) else if exist "C:\raylib\raylib\include\raylib.h" (
    set "RAYLIB_PATH=C:\raylib\raylib"
    echo Found Raylib at C:\raylib\raylib
) else (
    echo ERROR: Raylib not found!
    echo Please ensure Raylib is installed
    pause
    exit /b 1
)

echo Using Raylib from: %RAYLIB_PATH%
echo.
echo Source file: main.cpp (shared by both builds)
echo.

REM ========================================
REM STEP 1: Build Standalone Version
REM ========================================
echo ========================================
echo STEP 1: Building Standalone Version
echo ========================================
echo.

REM Create output directory
if not exist "bin" mkdir bin

echo Compiling standalone executable...
%GPP_PATH% -std=c++17 -O2 -I "%RAYLIB_PATH%\include" -L "%RAYLIB_PATH%\lib" main.cpp -lraylib -lwinmm -lgdi32 -o bin\CyberTrain.exe

set "STANDALONE_RESULT=!ERRORLEVEL!"

if !STANDALONE_RESULT! EQU 0 (
    echo [SUCCESS] Standalone build completed: bin\CyberTrain.exe
    echo Copying raylib.dll for standalone...
    if exist "%RAYLIB_PATH%\lib\raylib.dll" (
        copy "%RAYLIB_PATH%\lib\raylib.dll" "bin\" >nul 2>&1
        echo [OK] raylib.dll copied to bin\
    ) else (
        echo [WARNING] raylib.dll not found at %RAYLIB_PATH%\lib\raylib.dll
    )
) else (
    echo [FAILED] Standalone build failed!
    set "BUILD_FAILED=1"
)

echo.

REM ========================================
REM STEP 2: Build BBS DLL Version
REM ========================================
echo ========================================
echo STEP 2: Building BBS DLL Version
echo ========================================
echo.

REM Check if DLL is locked
if exist "cybertrain.dll" (
    attrib -r "cybertrain.dll" >nul 2>&1
    del /f /q "cybertrain.dll" >nul 2>&1
    if exist "cybertrain.dll" (
        echo.
        echo ========================================
        echo ERROR: cybertrain.dll is LOCKED
        echo ========================================
        echo Close the BBS / python.exe (anything using cybertrain.dll^) and run build_both.bat again.
        set "BUILD_FAILED=1"
        goto :after_dll_build
    )
)

echo Compiling BBS DLL...
%GPP_PATH% main.cpp -o cybertrain.dll -shared -std=c++17 -O2 -I "%RAYLIB_PATH%\include" -L "%RAYLIB_PATH%\lib" -lraylibdll -lopengl32 -lgdi32 -lwinmm

set "DLL_RESULT=!ERRORLEVEL!"

if !DLL_RESULT! EQU 0 (
    echo [SUCCESS] BBS DLL build completed: cybertrain.dll
    echo Copying raylib.dll for BBS...
    if exist "%RAYLIB_PATH%\lib\raylib.dll" (
        copy "%RAYLIB_PATH%\lib\raylib.dll" "." >nul 2>&1
        echo [OK] raylib.dll copied to CyberTrain folder
    ) else (
        echo [WARNING] raylib.dll not found at %RAYLIB_PATH%\lib\raylib.dll
    )
    
    REM Copy MinGW runtime DLLs from AstroMiner (shared dependencies)
    echo Copying MinGW runtime DLLs...
    set "ASTROMINER_DIR=%SCRIPT_DIR%..\AstroMiner"
    if exist "!ASTROMINER_DIR!\libgcc_s_seh-1.dll" (
        copy "!ASTROMINER_DIR!\libgcc_s_seh-1.dll" "." >nul 2>&1
        copy "!ASTROMINER_DIR!\libstdc++-6.dll" "." >nul 2>&1
        copy "!ASTROMINER_DIR!\libwinpthread-1.dll" "." >nul 2>&1
        echo [OK] MinGW runtime DLLs copied from AstroMiner
    ) else (
        echo [NOTE] MinGW runtime DLLs not found in AstroMiner folder.
        echo If loading fails, copy libgcc_s_seh-1.dll, libstdc++-6.dll, libwinpthread-1.dll
    )
) else (
    echo [FAILED] BBS DLL build failed!
    set "BUILD_FAILED=1"
)

:after_dll_build
echo.

REM ========================================
REM SUMMARY
REM ========================================
echo ========================================
echo BUILD SUMMARY
echo ========================================
echo.

if defined BUILD_FAILED (
    echo [RESULT] Build completed with ERRORS
    echo.
    echo Please check the error messages above.
) else (
    echo [RESULT] Both builds completed successfully!
    echo.
    echo Standalone version: bin\CyberTrain.exe
    echo BBS DLL version: cybertrain.dll
    echo.
    echo Both versions are built from the same main.cpp source file.
    echo Changes to main.cpp will affect both versions when you rebuild.
    echo.
    echo To test standalone: bin\CyberTrain.exe
    echo To test in BBS: Launch the BBS and play CyberTrain
)

echo.
pause
endlocal
