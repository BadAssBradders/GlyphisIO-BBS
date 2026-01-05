@echo off
setlocal EnableDelayedExpansion
REM Build script for CyberTrain DLL (for BBS embedding)
REM This compiles main.cpp into cybertrain.dll for framebuffer-based embedding

echo Building cybertrain.dll for BBS integration...
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

REM Compile as DLL
echo Compiling to DLL...
REM Keep output clean: always build to cybertrain.dll.
REM If cybertrain.dll is locked by a running BBS / python.exe, fail fast with a clear message.
if exist "cybertrain.dll" (
    attrib -r "cybertrain.dll" >nul 2>&1
    del /f /q "cybertrain.dll" >nul 2>&1
    if exist "cybertrain.dll" (
        echo.
        echo ========================================
        echo ERROR: cybertrain.dll is LOCKED
        echo ========================================
        REM NOTE: Do not use unescaped ')' inside a parenthesized block; it breaks parsing.
        echo Close the BBS / python.exe (anything using cybertrain.dll^) and run build_dll.bat again.
        goto :after_build
    )
)

%GPP_PATH% main.cpp -o cybertrain.dll -shared -std=c++17 -O2 -I "%RAYLIB_PATH%\include" -L "%RAYLIB_PATH%\lib" -lraylibdll -lopengl32 -lgdi32 -lwinmm

REM Capture the result immediately
set "BUILD_RESULT=!ERRORLEVEL!"

if !BUILD_RESULT! EQU 0 (
    echo.
    echo ========================================
    echo SUCCESS: cybertrain.dll created!
    echo ========================================
    echo.
    echo Copying raylib.dll...
    if exist "%RAYLIB_PATH%\lib\raylib.dll" (
        copy "%RAYLIB_PATH%\lib\raylib.dll" "." >nul 2>&1
        echo raylib.dll copied successfully.
    ) else (
        echo WARNING: raylib.dll not found at %RAYLIB_PATH%\lib\raylib.dll
        echo You may need to copy it manually.
    )
    
    REM Copy MinGW runtime DLLs from AstroMiner (shared dependencies)
    echo Copying MinGW runtime DLLs...
    set "ASTROMINER_DIR=%SCRIPT_DIR%..\AstroMiner"
    if exist "!ASTROMINER_DIR!\libgcc_s_seh-1.dll" (
        copy "!ASTROMINER_DIR!\libgcc_s_seh-1.dll" "." >nul 2>&1
        copy "!ASTROMINER_DIR!\libstdc++-6.dll" "." >nul 2>&1
        copy "!ASTROMINER_DIR!\libwinpthread-1.dll" "." >nul 2>&1
        echo MinGW runtime DLLs copied from AstroMiner.
    ) else (
        echo NOTE: MinGW runtime DLLs not found in AstroMiner folder.
        echo If loading fails, copy libgcc_s_seh-1.dll, libstdc++-6.dll, libwinpthread-1.dll
    )
    echo.
    echo Required files for BBS integration:
    echo   - cybertrain.dll [just created]
    echo   - raylib.dll [should be in same folder]
    echo   - PixelifySans.ttf [font file]
    echo.
    echo The DLL is ready for BBS integration!
) else (
    echo.
    echo ========================================
    echo BUILD FAILED!
    echo ========================================
    echo.
    echo Common issues:
    echo   1. Make sure g++ compiler is accessible
    echo   2. Verify Raylib files exist
    echo   3. Check error messages above
)

:after_build
echo.
pause
endlocal
