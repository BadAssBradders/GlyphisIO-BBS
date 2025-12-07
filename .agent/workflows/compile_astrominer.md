---
description: How to compile and test the Astro Miner C++ game integration
---

# Compiling and Testing Astro Miner (C++)

The Astro Miner game is a C++ application that runs embedded within the main BBS interface using a DLL and shared memory framebuffer.

## Prerequisites

-   **MinGW-w64** (g++) installed and in your PATH.
-   **Raylib** installed (headers and libraries).
    -   The build scripts expect Raylib at `E:\Dev\raylib`.
    -   If your Raylib is elsewhere, edit `build_dll.bat`.

## Compilation Workflow

1.  **Navigate to the game directory**:
    Open a terminal and go to:
    `e:\Dev\Glyphis_IO BBS The Proxy Tapes\Data\games\AstroMiner`

2.  **Compile the DLL**:
    Run the build script:
    ```cmd
    build_dll.bat
    ```
    -   This compiles `astro_miner_main.cpp` into `astrominer.dll`.
    -   **Success**: You should see "SUCCESS: astrominer.dll created!".
    -   **Failure**: Check error messages. Common issues include missing `g++` or incorrect Raylib paths.

3.  **Verify DLL Location**:
    Ensure `astrominer.dll` is located in `Data\games\AstroMiner\`. The build script should place it there automatically.

## Testing via Main.py

1.  **Run the BBS**:
    Execute `main.py` from the root directory:
    ```cmd
    python main.py
    ```

2.  **Unlock the Game**:
    You need the `ASTROMINER` token to see the game in the menu.
    -   **Method A (Gameplay)**: Complete the required in-game tasks (Audio Ops + Jaxkando email).
    -   **Method B (Dev Shortcut)**:
        -   Open the terminal in the BBS (press `~` or `TAB` if available, or use the in-game shell).
        -   Or, temporarily modify `main.py` to grant the token on startup.
        -   *Tip*: You can check `sent_emails.json` or user state to see if you have the token.

3.  **Launch the Game**:
    -   Navigate to the **GAMES** module in the BBS.
    -   Select **ASTRO MINER**.
    -   Press **ENTER** to launch.

4.  **Verify Integration**:
    -   The game should appear *inside* the BBS monitor frame.
    -   Controls (Arrow keys, Space, etc.) should work.
    -   If it fails to load, check the console output for errors from `astrominer_embed.py` (e.g., "Failed to initialize Astro Miner DLL").

## Troubleshooting

-   **"DLL not found"**: Ensure `astrominer.dll` and `raylib.dll` are in `Data\games\AstroMiner\`.
-   **"Access Violation"**: This might happen if the C++ code tries to access memory it shouldn't, or if the framebuffer size doesn't match what Python expects.
-   **Black Screen**: The game might be running but not rendering. Check if `UpdateFrame` is being called and if the framebuffer is being populated.
