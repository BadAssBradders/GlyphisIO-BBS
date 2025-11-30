# PowerShell script to set RAYLIB_PATH environment variable
# Run this script as Administrator, or it will set it for the current user only

param(
    [Parameter(Mandatory=$true)]
    [string]$RaylibPath
)

# Validate that the path exists
if (-not (Test-Path $RaylibPath)) {
    Write-Host "Error: The path '$RaylibPath' does not exist!" -ForegroundColor Red
    Write-Host "Please provide a valid path to your Raylib installation." -ForegroundColor Yellow
    exit 1
}

# Set the environment variable for the current user
[System.Environment]::SetEnvironmentVariable("RAYLIB_PATH", $RaylibPath, [System.EnvironmentVariableTarget]::User)

Write-Host "Successfully set RAYLIB_PATH to: $RaylibPath" -ForegroundColor Green
Write-Host "Please restart Visual Studio for the changes to take effect." -ForegroundColor Yellow

