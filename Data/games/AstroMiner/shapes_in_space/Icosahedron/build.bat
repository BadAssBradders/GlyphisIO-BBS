@echo off
REM Build script for Icosahedron Raylib project
REM Edit your code in Notepad++, then run this script to build

echo Building Icosahedron project...
echo.

REM Check if RAYLIB_PATH is set
if "%RAYLIB_PATH%"=="" (
    echo ERROR: RAYLIB_PATH environment variable is not set!
    echo Please set it to your Raylib installation folder (e.g., C:\raylib)
    pause
    exit /b 1
)

REM Find MSBuild (Visual Studio compiler)
set "MSBUILD_PATH="

REM Try to find MSBuild using vswhere (most reliable method)
if exist "%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe" (
    for /f "usebackq tokens=*" %%i in (`"%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe" -latest -products * -requires Microsoft.Component.MSBuild -find MSBuild\**\Bin\MSBuild.exe`) do set "MSBUILD_PATH=%%i"
)

REM Fallback to common paths if vswhere didn't find it
if "%MSBUILD_PATH%"=="" (
    if exist "C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\MSBuild.exe" (
        set "MSBUILD_PATH=C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\MSBuild.exe"
    ) else if exist "C:\Program Files\Microsoft Visual Studio\2022\Professional\MSBuild\Current\Bin\MSBuild.exe" (
        set "MSBUILD_PATH=C:\Program Files\Microsoft Visual Studio\2022\Professional\MSBuild\Current\Bin\MSBuild.exe"
    ) else if exist "C:\Program Files\Microsoft Visual Studio\2022\Enterprise\MSBuild\Current\Bin\MSBuild.exe" (
        set "MSBUILD_PATH=C:\Program Files\Microsoft Visual Studio\2022\Enterprise\MSBuild\Current\Bin\MSBuild.exe"
    ) else if exist "C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\MSBuild\Current\Bin\MSBuild.exe" (
        set "MSBUILD_PATH=C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\MSBuild\Current\Bin\MSBuild.exe"
    ) else if exist "C:\Program Files (x86)\Microsoft Visual Studio\2019\Professional\MSBuild\Current\Bin\MSBuild.exe" (
        set "MSBUILD_PATH=C:\Program Files (x86)\Microsoft Visual Studio\2019\Professional\MSBuild\Current\Bin\MSBuild.exe"
    )
)

REM Check if MSBuild was found
if "%MSBUILD_PATH%"=="" (
    echo.
    echo ERROR: Could not find MSBuild.exe
    echo.
    echo Please install one of the following:
    echo   - Visual Studio 2019 or 2022 with "Desktop development with C++" workload
    echo   - Visual Studio Build Tools with C++ build tools
    echo.
    pause
    exit /b 1
)

REM Build the project
echo Using MSBuild: %MSBUILD_PATH%
echo.
echo Building Debug x64 configuration...
echo.
"%MSBUILD_PATH%" Icosahedron.sln /p:Configuration=Debug /p:Platform=x64 /m /v:minimal

set BUILD_RESULT=%ERRORLEVEL%

if %BUILD_RESULT% EQU 0 (
    echo.
    echo ========================================
    echo Build successful!
    echo ========================================
    echo.
    echo Copying raylib.dll to output directory...
    if not exist "bin\x64\Debug\" mkdir "bin\x64\Debug\"
    if exist "%RAYLIB_PATH%\lib\raylib.dll" (
        copy "%RAYLIB_PATH%\lib\raylib.dll" "bin\x64\Debug\" >nul 2>&1
        echo DLL copied successfully.
    ) else (
        echo WARNING: raylib.dll not found at %RAYLIB_PATH%\lib\raylib.dll
        echo You may need to copy it manually to bin\x64\Debug\
    )
    echo.
    echo Executable location: bin\x64\Debug\Icosahedron.exe
    echo.
    echo To run the game, execute: bin\x64\Debug\Icosahedron.exe
) else (
    echo.
    echo ========================================
    echo Build failed! (Error code: %BUILD_RESULT%)
    echo ========================================
    echo.
    echo Common issues:
    echo   1. Make sure Visual Studio with C++ tools is installed
    echo   2. Check that RAYLIB_PATH is set correctly (currently: %RAYLIB_PATH%)
    echo   3. Verify Raylib files exist at %RAYLIB_PATH%\include\raylib.h
    echo   4. Look at the error messages above for specific issues
    echo.
)

pause

