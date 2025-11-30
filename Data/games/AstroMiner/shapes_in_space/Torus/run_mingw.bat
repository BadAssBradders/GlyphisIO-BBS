@echo off
REM Build and run script for MinGW
REM Keeps terminal open while game runs

call build_mingw.bat

if %ERRORLEVEL% EQU 0 (
    if exist "bin\Torus.exe" (
        echo.
        echo Starting game (terminal will stay open)...
        echo Press any key after closing the game to exit this window.
        echo.
        "bin\Torus.exe"
        echo.
        echo Game closed.
        pause
    ) else (
        echo ERROR: Executable not found!
        pause
    )
) else (
    echo Build failed - cannot run game.
    pause
)

