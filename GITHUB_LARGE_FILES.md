# Handling Large Files on GitHub

## The Problem

Your repository is **915 MB**, which is too large for a standard Git push. GitHub has limits:
- **Individual files**: Max 100 MB (hard limit)
- **Recommended**: Use Git LFS for files over 50 MB
- **Push timeout**: Large pushes can timeout (HTTP 408 error)

## What Happened

The error `HTTP 408` means the push timed out because:
1. Your repository contains large video files (.mp4, .mov)
2. Large Photoshop files (.psd)
3. Total size exceeds GitHub's recommended limits

## Solutions

### Option 1: Use Git LFS (Recommended for Large Media Files)

Git LFS (Large File Storage) stores large files separately:

```bash
# Install Git LFS (if not installed)
# Windows: Download from https://git-lfs.github.com/

# Initialize Git LFS in your repo
git lfs install

# Track large file types
git lfs track "*.mp4"
git lfs track "*.mov"
git lfs track "*.psd"

# Add the .gitattributes file
git add .gitattributes

# Remove large files from regular git tracking
git rm --cached Data/Videos/*.mp4
git rm --cached Data/Urgent_Ops/*.mp4
git rm --cached *.mov
git rm --cached *.psd

# Re-add them (they'll be tracked by LFS)
git add Data/Videos/
git add Data/Urgent_Ops/
git add *.mov
git add *.psd

# Commit
git commit -m "Use Git LFS for large media files"

# Push (LFS files will upload separately)
git push -u origin main
```

**Note**: Git LFS has free tier limits (1 GB storage, 1 GB bandwidth/month)

### Option 2: Exclude Large Files (Simplest)

Keep large files local, don't commit them:

1. ✅ Already done: Updated `.gitignore` to exclude `.mp4`, `.mov`, `.psd`
2. Remove from Git history (if already committed):

```bash
# Remove large files from Git history (creates new commit)
git filter-branch --force --index-filter "git rm --cached --ignore-unmatch Data/Videos/*.mp4 Data/Urgent_Ops/*.mp4 *.mov *.psd" --prune-empty --tag-name-filter cat -- --all

# Force push (WARNING: This rewrites history)
git push origin --force --all
```

**OR** simpler approach - start fresh:

```bash
# Create a new branch without large files
git checkout --orphan main-clean
git add .
git commit -m "Initial commit without large files"
git branch -D main
git branch -m main
git push -u origin main --force
```

### Option 3: Increase Buffer Size (Temporary Fix)

Try pushing with increased buffer (may still timeout):

```bash
git config http.postBuffer 524288000  # 500 MB buffer
git push -u origin main
```

### Option 4: Push in Smaller Chunks

Split your push into multiple commits:

```bash
# Push without large files first
git push -u origin main --exclude="*.mp4" --exclude="*.mov"
```

## Recommended Approach

**For a game project**, I recommend:

1. **Use Git LFS** for essential game assets (videos, large images)
2. **Exclude** development/preview files (.psd, test videos)
3. **Store** large build artifacts elsewhere (not in Git)

## Current Status

✅ `.gitignore` updated to exclude `.mp4`, `.mov`, `.psd`  
✅ Git buffer increased to 500 MB  
⚠️ Large files still in commit history (need to remove)

## Next Steps

1. **If you want to keep videos in the repo**: Use Git LFS (Option 1)
2. **If videos aren't essential**: Remove them from history (Option 2)
3. **If you just want to push**: Try Option 3 (may still timeout)

## Alternative: External Storage

Consider storing large media files on:
- **GitHub Releases**: Upload as release assets
- **Cloud Storage**: Google Drive, Dropbox, etc.
- **CDN**: For production assets
- **Steam**: For game distribution

