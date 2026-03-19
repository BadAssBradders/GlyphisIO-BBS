# GlyphisIO BBS: The Proxy Tapes

## Project Overview

GlyphisIO BBS: The Proxy Tapes is a narrative-driven retro BBS emulator built in Python and Pygame. It simulates an underground 1980s-style hacker community, featuring AI NPC interactions, keyboard-controlled terminal interfaces, and a distinct retro aesthetic. The game is designed for Steam (App ID: 4179570) and uses a token-based progression system to gate story beats, modules, and minigames.

The architecture centers on a single-process Pygame state machine (`main.py`) supported by modular systems in the `systems/` directory.

## Core Architecture & Systems

### 1. Token-Gated Progression (`tokens.py`, `systems/token_inventory.py`)
All gameplay progression is driven by **Tokens**. Acquiring a token (e.g., `PSEM`, `GAMES1`, `ASTROMINER`) triggers:
*   Automatic email delivery (inbox updates).
*   UI module unlocks (pulsing menu items).
*   Narrative branch activation.

### 2. Email & NPC Systems (`systems/email_db.py`, `systems/enhanced_npc.py`)
*   **Email Database:** JSON-backed inbox/outbox handling with placeholder substitution (`{username}`).
*   **Enhanced NPC Responder:** Personality-driven, offline keyword matching. NPCs (Glyphis, Rain, Jaxkando, Uncle-am) have distinct traits, tones, and simulated response delays (30–180s) for realism.
*   **Vital Mission Path:** A guided UI pattern (pulsing menu items at 1.5Hz, ghost text in fields) used to lead players through critical story moments.

### 3. Game Integration (`Data/games/registry.py`)
The BBS supports three integration styles:
*   **Embedded Python:** Games like *Simulacra Core* run directly in the Pygame loop.
*   **C++ DLL Games:** *Astro Miner* and *CyberTrain* (built with Raylib/C++) expose framebuffers blitted into the BBS via `ctypes`.
*   **Outside BBSes:** Full-screen takeovers simulating separate dial-in worlds (e.g., *Paper Crane*, *Echo Chamber*).

### 4. OS Mode & Bradsonic 69000 (`Data/OS/`)
A simulated desktop environment ("Bradsonic 69000") featuring:
*   **Mini-Apps:** Chess, Mahjong, dotSONIC Media Player, Notes, and a full Mail client.
*   **Regional Localization:** Content is gated by network regions (Mainland, Europe, Pacific Isles), switchable via terminal commands.
*   **Social Engineering:** Mission arcs like the *School Hack* involve phishing, phone spoofing via modem dialing, and database manipulation.

## Building and Running

### Dependencies
Install requirements via:
```bash
pip install -r requirements.txt
```
Key libraries: `pygame`, `numpy`, `PyMuPDF`, `opencv-python`, `python-chess`, `pyriichi`, `steamworks`.

### Running the Game
Execute from the project root:
```bash
python main.py
```

### Testing
*   **Python Tests:** `python -m pytest tests/` (covers NPC realism, email logic).
*   **C++ Regression Tests:** Located in `tests/test_cybertrain_regression.cpp` (requires Raylib/g++).

## Development Conventions

*   **Keyboard-Only UI:** The BBS interface is strictly keyboard-driven (TAB, Arrows, ENTER, ESC). OS Mode is the exception, supporting mouse interaction.
*   **Resolution Scaling:** Use `systems/resolution_manager.py` for all UI positioning. Baseline resolution is 2560x1440.
*   **Assets:** All game data lives in `Data/`. Asset resolution must use `utils.get_data_path()`.
*   **Modularity:** New features should be extracted from `main.py` into `systems/` or `modules/` to manage technical debt.

## Key Documentation
*   `CLAUDE.md`: Detailed architectural summary and developer guide.
*   `VITAL_MISSION_PATH_DOCUMENTATION.md`: Implementation specs for guided missions.
*   `EMAIL_SYSTEM_README.md`: JSON schema for email triggers.
*   `PROJECT_SUMMARY.md`: High-level narrative and gameplay flow.
