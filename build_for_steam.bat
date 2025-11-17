@echo off
echo ========================================
echo GlyphisIO BBS - Steam Build Script
echo ========================================
echo.

REM Check if PyInstaller is installed
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo PyInstaller not found. Installing...
    pip install pyinstaller
    if errorlevel 1 (
        echo Failed to install PyInstaller. Please install manually.
        pause
        exit /b 1
    )
)

echo.
echo Building executable...
echo.

REM Run PyInstaller
pyinstaller build_game.spec

if errorlevel 1 (
    echo.
    echo Build failed! Check errors above.
    pause
    exit /b 1
)

echo.
echo ========================================
echo Build Complete!
echo ========================================
echo.
echo Your build is in: dist\GlyphisIO_BBS\
echo.
echo Next steps:
echo 1. Test the build locally
echo 2. Zip the dist\GlyphisIO_BBS\ folder
echo 3. Upload to Steam Partner Portal
echo.
echo Press any key to open the build folder...
pause >nul
explorer dist\GlyphisIO_BBS

