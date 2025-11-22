# PowerShell script to remove large files from Git history
# Run this script to clean up your repository

Write-Host "Removing large files from Git history..." -ForegroundColor Yellow

# Remove large file types from Git tracking
git rm --cached -r Data/Videos/*.mp4 2>$null
git rm --cached Data/Urgent_Ops/*.mp4 2>$null
git rm --cached sandbox\ media/*.mp4 2>$null
git rm --cached *.mov 2>$null
git rm --cached *.psd 2>$null
git rm --cached Data/**/*.psd 2>$null
git rm --cached sandbox\ media/*.psd 2>$null

Write-Host "Large files removed from tracking. Committing changes..." -ForegroundColor Green

git commit -m "Remove large media files from repository"

Write-Host "Done! Repository should be smaller now." -ForegroundColor Green
Write-Host "Run: git push -u origin main" -ForegroundColor Cyan

