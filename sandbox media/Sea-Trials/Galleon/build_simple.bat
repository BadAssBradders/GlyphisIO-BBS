@echo off
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

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
    pause
    exit /b 1
)

if not exist "bin" mkdir bin

echo Building with %GPP_PATH%...
%GPP_PATH% -std=c++17 -O2 -I C:/raylib/include src/main.cpp src/galleon_asset.cpp src/hex_grid.cpp -L C:/raylib/lib -lraylib -lwinmm -lgdi32 -o bin/Galleon.exe

if %ERRORLEVEL% NEQ 0 (
    echo Build failed!
    pause
    exit /b 1
)

copy "C:\raylib\lib\raylib.dll" "bin\" >nul 2>&1
echo Build successful: bin\Galleon.exe
