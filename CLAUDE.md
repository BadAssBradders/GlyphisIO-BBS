# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Is

GlyphisIO BBS: The Proxy Tapes is a narrative-driven retro BBS emulator built in Python/Pygame, targeting Steam (App ID: 4179570). Players navigate a 1980s-style bulletin board system, receive emails from NPCs, complete tasks, and play embedded minigames — all gated behind a token-based progression system.

## Running the Project

```bash
# Run the BBS (main entry point)
python main.py

# Run Python tests
python -m pytest tests/

# Run a single Python test
python -m pytest tests/test_npc_realism.py
```

**C++ regression tests** (CyberTrain logic, standalone harness):
```bat
cd tests
g++ -std=c++17 -I"C:\raylib\raylib\src" -L"C:\raylib\raylib\src" test_cybertrain_regression.cpp -o test_cybertrain_regression.exe -lraylib -lopengl32 -lgdi32 -lwinmm
test_cybertrain_regression.exe
```
The harness compiles by `#include`-ing `Data/games/CyberTrain/main.cpp` directly (no window is opened). A `[PASS]` line means all tests passed; any `[FAIL]` line names the broken assertion.

No build step for the Python side. Requires Python 3.10+ and dependencies from `requirements.txt`. Font asset `Pixellari.ttf` must be in the project root.

**Important:** Always run the BBS from the project root — asset resolution depends on `utils.get_data_path()` which uses the CWD or PyInstaller bundle path.

## Building C++ Games

**CyberTrain** (preferred: builds both standalone + BBS DLL):
```bat
cd "Data/games/CyberTrain"
build_both.bat
```
Other options: `build_and_run.bat` (standalone only), `build_dll.bat` (DLL only).

**AstroMiner:**
```bat
cd "Data/games/AstroMiner"
build_dll.bat        # BBS-embedded version
build_standalone.bat # Standalone executable
```

Both use g++ -std=c++17 with Raylib. The build scripts auto-detect the compiler and Raylib at `C:\raylib` or `C:\raylib\raylib`.

## Architecture

### State Machine (main.py)
The BBS is a single Python process with a state machine. Key states: `main_menu`, `login`, `main_terminal_feed`, `email`, `games`, `urgent_ops`, `os_mode`, `simulacra_core`, `outside_bbs`, `pirate_radio`. State drives what's rendered each frame.

### Token System (tokens.py)
All progression is gated by tokens (string constants). Acquiring a token triggers: JSON state save, email auto-sends, and UI unlocks. Key tokens: `PSEM` (email), `GAMES1` (games module), `ASTROMINER`, `CYBERTRAIN`, `AUDIO_ON`. See `tokens.py` for full catalogue.

### Email System (systems/email_db.py)
JSON-backed inbox/outbox. Emails auto-send on token acquisition. Supports timestamp modes (`null` = current time, `"realtime"` = runtime eval) and `{username}` placeholder substitution. Tracks sent emails to prevent duplicates.

### Game Integration (Data/games/registry.py)
- **Embedded Python games** (`SIMULACRA_CORE.py`, `lapc1_assembler_quiz.py`): implement `BaseGameSession` interface, run within the main Pygame loop.
- **C++ DLL games** (CyberTrain, AstroMiner): launched via ctypes through `cybertrain_embed.py` / `astrominer_embed.py`. The DLL exposes a framebuffer that gets blitted into the BBS window.
- **Outside BBSes** (`Data/Outside_BBSs/` — Paper Crane, Never Again, Echo Chamber): full-screen Pygame takeovers.
- **Pending integration:** `Game4/debugger_game.py` — a BASIC debugger puzzle game; integration steps in `Game4/INTEGRATION_GUIDE.md`.

### NPC System (systems/npc.py, enhanced_npc.py)
Fully offline keyword-based pattern matching. No external API. `enhanced_npc.py` adds relationship tracking on top of the base responder.

### Data Persistence
All state in JSON files: `Data/user_state.json`, `Data/emails_inbox.json`, `Data/emails_outbox.json`, per-game `leaderboard.json`. No database.

### Shared Utilities (utils.py)
Critical helpers used throughout: `get_data_path()` resolves asset paths for both dev and PyInstaller builds, `is_daytime()` drives time-of-day narrative branches (daytime = 6:00–17:59 Tokyo time), and `log_event()` is the standard logging call.

### Vital Mission Path
A UI pattern for guided story moments. When a token gate triggers a required email interaction, the relevant BBS menu item pulses between its base color and `(150, 255, 255)` at 1.5 Hz using `get_pulse_color()`. Subject fields show ghost text in `(80, 80, 80)` for required content; body fields show bracketed placeholder text that disappears on first keystroke. Full specification in `VITAL_MISSION_PATH_DOCUMENTATION.md`.

## CyberTrain C++ Architecture

**Single translation unit:** `Data/games/CyberTrain/main.cpp` `#include`s all `.cpp` files in order:
1. `src/cybertrain_core.cpp` — all game state globals, structs, modal definitions
2. `src/cybertrain_economy_modals.cpp` — modal draw logic
3. `src/cybertrain_network_worldgen.cpp` — world generation
4. `src/cybertrain_exports.cpp` — DLL export functions
5. `src/cybertrain_ui.cpp` — HUD and UI overlays
6. `src/cybertrain_gameloop.cpp` — main game loop, input, per-frame logic
7. `src/cybertrain_standalone_main.cpp` — standalone entry point

**File encoding:** Source files use **Mojibake UTF-8** — em-dashes are stored as `â€"` bytes. Use Python scripts for edits involving these characters; the Edit tool may corrupt them.

**Key globals** (all in `cybertrain_core.cpp`): `g_placedPlatforms`, `g_placedTrains`, `g_lines`, `g_demolishNeutralizedPlatformKeys`. Two render paths: map mode (~line 3600) and 3D mode (~line 3927) in `cybertrain_gameloop.cpp`.

### Resolution Scaling (systems/resolution.py)
`ResolutionManager` handles all coordinate translation. The baseline design resolution is 2560×1440; all coordinates in code are specified at this baseline and scaled at runtime via `coords()`, `scale()`, and `rect()` helpers. Blessed resolutions: 2560×1440, 1920×1080 — others use fallback scaling. Any UI positioning or game framebuffer blitting must go through the resolution manager.

### OS Mode (Data/OS/OS_Mode.py)
A full simulated desktop environment ("Bradsonic 69000") with draggable windows, a filesystem, terminal, mail client, and mini-apps. Launched from the `os_mode` BBS state. Uses PIL for image handling alongside Pygame.

**Desktop apps:** Chess, Mahjong, Solitaire, Snooker, Civitas Nihilium, Notes (tabbed editor with strikethrough), Datasette (video recording/playback), dotSONIC media player (`Data/OS/dotSONIC/DotSonicMediaPlayer.py` — plays `.sonic` files with frequency visualization), and BRADSONIC-MAIL (full email client with inbox/compose/outbox/trash/settings).

**Regional localization:** Three network regions (American Mainland=1, Europe=2, American Pacific Isles=3) gate which apps and content are visible. Set via `admin-subset` terminal command with admin credentials. Region credentials are found in `LocaleProtocols.brad` within the OS filesystem.

**Terminal:** Navigable filesystem, admin commands, and packet visualization. The `admin-subset` command changes the OS locale/region.

**Modem/Phone dialing:** A modal that simulates DTMF phone dialing with multiple audio channels (dial tone, pickup, ringing, busy, modem). Used in the School Hack mission arc for calling school phone lines at specific times.

### Social Engineering / School Hack (Data/Social_Engineering/)
A multi-phase mission arc involving phishing, phone spoofing, and database manipulation:
1. Change OS locale/region via terminal (admin credentials from `LocaleProtocols.brad`)
2. Send guided email to Rain via BRADSONIC-MAIL saying "I'm in"
3. Spoof email identity to school receptionist (TELCO RELAY ENGINEER role) to extract phone numbers
4. Use modem to dial school phone lines at correct times
5. Connect to school server and modify grades in the database (`Data/Social_Engineering/School_Hack/school_database_standalone.py`)

Tokens: `SCHOOL_HACK`, `SCHOOL_HACK1`, `SCHOOL_HACK2`, `SCHOOL_HACK3`, `SCHOOL_HACK4B`, etc. BRADSONIC-MAIL supports guided compose with placeholders and sender spoofing specifically for this arc.

### Urgent Ops Challenges (Data/games/)
Not just story gates — these are interactive assembly/machine-code puzzle games:
- `CRACKER_IDE_AstroMiner_Challenge.py` — patch copy protection in hex
- `CRACKER_IDE_LAPC1_Driver_Challenge.py` — fix a soundcard driver

### Pirate Radio (Data/Pirate_Radio/)
Multiple station types (PACIFIC WAVE, SYNTH REBELS, etc.) with time-of-day based station selection. `PirateRadio.py` handles UI. `Live_Stations/` contains broadcast audio, WAV files, and still images. Background audio persists across BBS states when `AUDIO_ON` token is held.

## Config Constants (config.py)

- Screen: 1000×700 (baseline 2560×1440)
- BBS window: 872×654
- Colors: `BLACK`, `CYAN`, `DARK_BLUE`, `RED`, `WHITE`, `PINK`
- Audio: 22050 Hz, 16-bit, 2 channels
- State constants: `STATE_GAMES`, `STATE_TASKS`, `STATE_TEAM`, `STATE_RADIO`, etc.
- Module name constants: `MODULE_TERMINAL_FEED`, `MODULE_GAMES`, etc.

## Steam Integration

`systems/steam_manager.py` wraps Steamworks. Place `steam_appid.txt` (contains `4179570`) in the project root for local testing without uploading. Steam is optional — all systems degrade gracefully if unavailable.

## Linting and Formatting

No linting or formatting tools are configured. There is no `pyproject.toml`, `.flake8`, or `ruff.toml`.

## Key Dependencies (requirements.txt)

Core: `pygame>=2.5.2`, `numpy>=1.26.0`. Media: `PyMuPDF`, `opencv-python`. Optional: `steamworks>=1.0.0`, `pytz>=2024.1`. Games: `python-chess`, `pyriiichi`.

## Adding a New C++ Game

See `sandbox media/CPP_GAME_INTEGRATION_GUIDE.md` for the full walkthrough. The pattern is: build a DLL with a framebuffer export → write a Python embed wrapper (like `cybertrain_embed.py`) → register it in `Data/games/registry.py`.

## UI Design Principle

All gameplay is **keyboard-only** for authentic BBS experience — TAB switches modules, arrow keys navigate, ENTER selects, ESC goes back. No mouse interaction in the BBS UI. OS Mode is the exception: it uses mouse for draggable windows and desktop interaction.

## .gitignore Notes

User state/save files, large media (PSD, MP4, MP3, WAV, FLAC), build artifacts, and `node_modules/` are all ignored. Check `.gitignore` before adding new asset types.

## Gotchas

- **CyberTrain Mojibake:** The C++ source files contain corrupted UTF-8 em-dashes (`â€"` instead of `—`). Do not attempt to "fix" these — the compiler handles them fine. Editing these characters with text tools can introduce worse corruption.
- **node_modules:** A `node_modules/` directory exists in the repo (used for Orchid markdown rendering) despite being gitignored. Do not delete it.
- **No hot reload:** The BBS must be restarted after Python code changes. C++ games require a DLL rebuild + BBS restart.
- **JSON state files:** `Data/user_state.json`, `Data/emails_inbox.json`, etc. are player save data. They exist at runtime but are gitignored. Don't check them in or rely on their presence for tests.
