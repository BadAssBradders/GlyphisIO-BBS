# How to Install Raylib

## Quick Installation Steps

### Step 1: Download Raylib
1. Go to: **https://github.com/raysan5/raylib/releases**
2. Look for the latest release (e.g., version 5.0 or higher)
3. Download the file: **`raylib-5.0-w64-msvc16.zip`** (or similar Windows x64 MSVC version)
   - This is the pre-compiled version for Visual Studio 2019/2022

### Step 2: Extract Raylib
1. **Create the folder** `C:\raylib` if it doesn't exist
2. **Extract** the downloaded ZIP file
3. **Copy the contents** to `C:\raylib`
   - You should have these folders:
     - `C:\raylib\include\` (contains `raylib.h`)
     - `C:\raylib\lib\` (contains `raylib.lib` and `raylib.dll`)

### Step 3: Verify Installation
After extracting, run:
```cmd
check_setup.bat
```

You should see:
- ✅ Found raylib.h
- ✅ Found raylib.lib  
- ✅ Found raylib.dll

### Step 4: Build Your Project
Once Raylib is installed, run:
```cmd
build.bat
```

## What the folder structure should look like:

```
C:\raylib\
├── include\
│   └── raylib.h          ← Header file
├── lib\
│   ├── raylib.lib        ← Library file (for linking)
│   └── raylib.dll        ← DLL file (runtime)
└── (other files...)
```

## Direct Download Link
If you want a direct link, go to:
**https://github.com/raysan5/raylib/releases/latest**

Look for a file named something like:
- `raylib-5.0-w64-msvc16.zip` (for Visual Studio 2019/2022)
- `raylib-5.0-w64-msvc15.zip` (for Visual Studio 2017)

## Troubleshooting

**If you can't find the right file:**
- Look for files with "w64" (Windows 64-bit) and "msvc" (Microsoft Visual C++)
- The number after "msvc" should match your Visual Studio version:
  - msvc15 = VS 2017
  - msvc16 = VS 2019/2022

**If extraction doesn't create the right structure:**
- Sometimes the ZIP contains a folder like `raylib-5.0-w64-msvc16\`
- Extract it, then move the contents of that folder to `C:\raylib\`
- Make sure `raylib.h` is directly in `C:\raylib\include\`, not nested deeper

