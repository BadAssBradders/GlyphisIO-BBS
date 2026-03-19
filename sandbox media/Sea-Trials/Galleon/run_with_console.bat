@echo off
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

call "%SCRIPT_DIR%build_simple.bat"
if %ERRORLEVEL% NEQ 0 exit /b %ERRORLEVEL%

if exist "bin\Galleon.exe" (
    "bin\Galleon.exe"
) else (
    echo ERROR: bin\Galleon.exe was not created
)

echo.
echo Galleon closed. Press any key to continue...
pause >nul
