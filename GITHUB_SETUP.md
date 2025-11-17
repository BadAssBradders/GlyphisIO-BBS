# GitHub Setup Instructions

Your repository has been initialized and your first commit has been created! Follow these steps to push to GitHub:

## Step 1: Create a GitHub Repository

1. Go to [GitHub.com](https://github.com) and sign in
2. Click the **"+"** icon in the top right corner
3. Select **"New repository"**
4. Fill in the repository details:
   - **Repository name**: `GlyphisIO-BBS` (or your preferred name)
   - **Description**: "A retro BBS-style terminal game featuring an underground hacker community"
   - **Visibility**: Choose Public or Private
   - **DO NOT** initialize with README, .gitignore, or license (we already have these)
5. Click **"Create repository"**

## Step 2: Connect Your Local Repository to GitHub

After creating the repository, GitHub will show you commands. Use these commands (replace `YOUR_USERNAME` with your GitHub username):

```bash
# Add the remote repository
git remote add origin https://github.com/YOUR_USERNAME/GlyphisIO-BBS.git

# Rename the default branch to 'main' (if needed)
git branch -M main

# Push your code to GitHub
git push -u origin main
```

## Alternative: Using SSH (if you have SSH keys set up)

```bash
git remote add origin git@github.com:YOUR_USERNAME/GlyphisIO-BBS.git
git branch -M main
git push -u origin main
```

## Step 3: Verify

After pushing, refresh your GitHub repository page. You should see all your files!

## What Was Committed

✅ All source code (Python files)
✅ Configuration files (config.py, utils.py)
✅ Systems modules (systems/ directory)
✅ Game data (Data/ folder)
✅ Documentation (README.md, STORY.txt, etc.)
✅ Assets (images, fonts, audio, videos)

## What Was Excluded (via .gitignore)

❌ Build artifacts (build/, dist/)
❌ Python cache files (__pycache__/)
❌ User state files (user_state.json)
❌ Adobe Premiere Pro files
❌ Temporary test files (Claude.py, GPT*.py, etc.)
❌ Steam app ID file (steam_appid.txt)

## Future Updates

To push future changes:

```bash
git add .
git commit -m "Description of your changes"
git push
```

## Troubleshooting

**If you get authentication errors:**
- GitHub now requires a Personal Access Token instead of passwords
- Go to GitHub Settings → Developer settings → Personal access tokens
- Generate a new token with `repo` permissions
- Use the token as your password when pushing

**If you need to change the remote URL:**
```bash
git remote set-url origin https://github.com/YOUR_USERNAME/REPO_NAME.git
```

