@echo off
echo ========================================
echo Icosahedron Project Setup Diagnostic
echo ========================================
echo.

echo [1] Checking RAYLIB_PATH environment variable...
if "%RAYLIB_PATH%"=="" (
    echo    [X] RAYLIB_PATH is NOT set
    echo    Please set it using: setx RAYLIB_PATH "C:\raylib"
) else (
    echo    [OK] RAYLIB_PATH = %RAYLIB_PATH%
    
    echo.
    echo [2] Checking Raylib installation...
    if exist "%RAYLIB_PATH%\include\raylib.h" (
        echo    [OK] Found raylib.h
    ) else (
        echo    [X] raylib.h NOT found at %RAYLIB_PATH%\include\raylib.h
    )
    
    if exist "%RAYLIB_PATH%\lib\raylib.lib" (
        echo    [OK] Found raylib.lib
    ) else (
        echo    [X] raylib.lib NOT found at %RAYLIB_PATH%\lib\raylib.lib
    )
    
    if exist "%RAYLIB_PATH%\lib\raylib.dll" (
        echo    [OK] Found raylib.dll
    ) else (
        echo    [X] raylib.dll NOT found at %RAYLIB_PATH%\lib\raylib.dll
    )
)

echo.
echo [3] Checking for MSBuild...
set "MSBUILD_FOUND=0"

REM Try vswhere first
if exist "%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe" (
    "%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe" -latest -products * -requires Microsoft.Component.MSBuild -find MSBuild\**\Bin\MSBuild.exe >nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        echo    [OK] Found MSBuild via vswhere
        set "MSBUILD_FOUND=1"
    )
)

REM Check common paths
if "%MSBUILD_FOUND%"=="0" (
    if exist "C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\MSBuild.exe" (
        echo    [OK] Found MSBuild: C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\MSBuild.exe
        set "MSBUILD_FOUND=1"
    ) else if exist "C:\Program Files\Microsoft Visual Studio\2022\Professional\MSBuild\Current\Bin\MSBuild.exe" (
        echo    [OK] Found MSBuild: C:\Program Files\Microsoft Visual Studio\2022\Professional\MSBuild\Current\Bin\MSBuild.exe
        set "MSBUILD_FOUND=1"
    ) else if exist "C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\MSBuild\Current\Bin\MSBuild.exe" (
        echo    [OK] Found MSBuild: C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\MSBuild\Current\Bin\MSBuild.exe
        set "MSBUILD_FOUND=1"
    ) else (
        echo    [X] MSBuild NOT found
        echo    Please install Visual Studio 2019 or 2022 with C++ development tools
    )
)

echo.
echo [4] Checking project files...
if exist "Icosahedron.sln" (
    echo    [OK] Found Icosahedron.sln
) else (
    echo    [X] Icosahedron.sln NOT found
)

if exist "Icosahedron.vcxproj" (
    echo    [OK] Found Icosahedron.vcxproj
) else (
    echo    [X] Icosahedron.vcxproj NOT found
)

if exist "src\main.cpp" (
    echo    [OK] Found src\main.cpp
) else (
    echo    [X] src\main.cpp NOT found
)

echo.
echo ========================================
echo Diagnostic complete
echo ========================================
echo.
pause

