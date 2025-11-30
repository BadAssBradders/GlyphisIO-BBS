@echo off
REM Build script for Icosahedron Raylib project (Release configuration)
REM Edit your code in Notepad++, then run this script to build

echo Building Icosahedron project (Release)...
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
) else (
    echo ERROR: Could not find MSBuild.exe
    echo Please install Visual Studio with C++ development tools
    pause
    exit /b 1
)

REM Build the project
echo Using MSBuild: %MSBUILD_PATH%
echo Building Release x64 configuration...
"%MSBUILD_PATH%" Icosahedron.sln /p:Configuration=Release /p:Platform=x64 /m

if %ERRORLEVEL% EQU 0 (
    echo.
    echo Build successful!
    echo.
    echo Copying raylib.dll to output directory...
    if not exist "bin\x64\Release\" mkdir "bin\x64\Release\"
    copy "%RAYLIB_PATH%\lib\raylib.dll" "bin\x64\Release\" >nul 2>&1
    echo.
    echo Executable location: bin\x64\Release\Icosahedron.exe
    echo.
    echo To run the game, execute: bin\x64\Release\Icosahedron.exe
) else (
    echo.
    echo Build failed! Check the errors above.
)

pause

