@echo off
REM Build script for Icosahedron using MinGW/GCC
REM This works with the MinGW version of Raylib

echo Building Icosahedron project with MinGW/GCC...
echo.

REM Check if RAYLIB_PATH is set
if "%RAYLIB_PATH%"=="" (
    echo ERROR: RAYLIB_PATH environment variable is not set!
    echo Please set it to your Raylib installation folder (e.g., C:\raylib)
    pause
    exit /b 1
)

REM Check for g++ (MinGW)
where g++ >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: g++ compiler not found in PATH
    echo.
    echo Please install MinGW-w64 and add it to your PATH, or:
    echo 1. Install w64devkit from: https://github.com/skeeto/w64devkit/releases
    echo 2. Or install MSYS2 and MinGW-w64
    echo 3. Make sure g++ is in your PATH
    echo.
    pause
    exit /b 1
)

REM Check for Raylib files
if not exist "%RAYLIB_PATH%\include\raylib.h" (
    echo ERROR: raylib.h not found at %RAYLIB_PATH%\include\raylib.h
    pause
    exit /b 1
)

if not exist "%RAYLIB_PATH%\lib\libraylib.a" (
    if not exist "%RAYLIB_PATH%\lib\raylib.dll" (
        echo ERROR: Raylib library files not found in %RAYLIB_PATH%\lib\
        echo Make sure you have the MinGW version of Raylib installed
        pause
        exit /b 1
    )
)

echo Using compiler: g++
echo Raylib path: %RAYLIB_PATH%
echo.

REM Build using Makefile
if exist "Makefile" (
    mingw32-make clean 2>nul
    mingw32-make
    set BUILD_RESULT=%ERRORLEVEL%
) else (
    echo ERROR: Makefile not found!
    pause
    exit /b 1
)

if %BUILD_RESULT% EQU 0 (
    echo.
    echo ========================================
    echo Build successful!
    echo ========================================
    echo.
    echo Executable: bin\Icosahedron.exe
    echo.
) else (
    echo.
    echo ========================================
    echo Build failed!
    echo ========================================
    echo.
)

pause

