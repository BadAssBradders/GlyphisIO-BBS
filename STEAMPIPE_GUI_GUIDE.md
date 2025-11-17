# SteamPipe GUI Tool - Step-by-Step Guide

## Finding the GUI Tool

1. **Navigate to your SDK folder:**
   - Go to `E:/SDK/tools/`
   - Look for a folder or zip file named:
     - `SteamPipeGUI`
     - `SteamPipeGUI.zip`
     - Or similar GUI-related folder

2. **If it's a zip file:**
   - Extract it
   - You should see an `.exe` file (like `SteamPipeGUI.exe`)

3. **If you can't find it:**
   - It might be in `E:/SDK/tools/ContentBuilder/`
   - Or check the main `tools` folder

## Using the GUI Tool

### Step 1: Launch the GUI

1. **Double-click `SteamPipeGUI.exe`**
2. **Login:**
   - Enter your Steam username
   - Enter your password
   - Enter Steam Guard code if prompted

### Step 2: Select Your App

1. **App ID:** Enter `4179570`
2. **Click "Load App"** or similar button
3. The GUI should load your app's depots

### Step 3: Configure Build

1. **Select Depot:**
   - Choose depot `4179571` (your content depot)
   - Or create a new one if needed

2. **Set Content Root:**
   - Click "Browse" or "Select Folder"
   - Navigate to your **unzipped** game folder
   - Select the folder containing your game files
   - **Important:** Use the unzipped folder, not the zip file

3. **Build Description:**
   - Enter something like: `Playtest Build v0.1`
   - Or `Initial Test Build`

### Step 4: Upload

1. **Click "Build" or "Upload" button**
2. **Wait for upload:**
   - Progress bar will show upload status
   - This can take several minutes depending on file size
   - Don't close the window!

3. **When complete:**
   - You should see "Build Complete" or similar message
   - Note the Build ID if shown

### Step 5: Set Build Live (for Playtest)

1. **Go back to Steam Partner Portal:**
   - Navigate to: https://partner.steamgames.com/apps/builds/4179570
   - Or: Your App → SteamPipe → Builds

2. **Find your new build:**
   - Should appear in the builds list
   - Look for the description you entered

3. **Set it live:**
   - Click on the build
   - Look for "Set Live" or "Set as Active Build"
   - Choose a branch (create "playtest" branch if needed)

## Alternative: If GUI Tool Not Found

If you can't find the GUI tool, you can use the web interface method:

### Web Interface Method:

1. **Go to Steam Partner Portal:**
   - https://partner.steamgames.com/apps/depotuploads/4179570

2. **Upload via HTTP:**
   - Select your zip file
   - Choose "Standard" option
   - Click "Upload"

3. **Then create build manually:**
   - Go to SteamPipe → Builds
   - Click "Create Build"
   - Select the depot you uploaded to
   - Save

## Troubleshooting

**GUI won't launch:**
- Make sure you have .NET Framework installed
- Try running as Administrator

**Can't find GUI tool:**
- Check `E:/SDK/tools/` folder
- Look for any `.exe` files
- Check if there's a `readme.txt` in the tools folder

**Upload fails:**
- Make sure you're logged in with correct account
- Verify account has "Edit App Metadata" permissions
- Check that depot 4179571 exists

**Build doesn't appear:**
- Wait a few minutes (can take time to process)
- Refresh the builds page
- Check if you need to publish changes first

## Quick Checklist

- [ ] Found SteamPipeGUI.exe
- [ ] Launched GUI tool
- [ ] Logged in with Steam account
- [ ] Entered App ID: 4179570
- [ ] Selected depot: 4179571
- [ ] Selected unzipped game folder (not zip!)
- [ ] Entered build description
- [ ] Clicked Build/Upload
- [ ] Waited for upload to complete
- [ ] Went to Steam Partner Portal → Builds
- [ ] Found new build and set it live

---

**Note:** The GUI tool makes it much easier than command-line! If you can't find it, let me know and we can use the web upload method instead.

