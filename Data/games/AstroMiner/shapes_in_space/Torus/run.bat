@echo off
REM Quick run script - builds and runs the game

echo Building and running Torus...
echo.

call build.bat

if %ERRORLEVEL% EQU 0 (
    echo.
    echo Starting game...
    echo.
    start "" "bin\x64\Debug\Torus.exe"
) else (
    echo Cannot run - build failed!
    pause
)

