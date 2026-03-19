# Project Summary: GlyphisIO BBS The Proxy Tapes

## What this project is

This repository contains a narrative-driven retro BBS game built primarily in Python with Pygame, with some embedded and external minigame integrations in both Python and C++. The player moves through a faux underground bulletin board system, reads posts, exchanges email with NPC operators, completes guided technical tasks, unlocks games and outside BBSes, and eventually branches into wider narrative arcs.

The core product is an offline single-player experience with Steam support layered on top, not a live online BBS. The overall tone is 1980s/1990s hacker culture, surveillance, pirate media, and puzzle-driven progression.

## Current runtime shape

- Main entry point: `main.py`
- Core app class: `GLYPHIS_IOBBS`
- Main architecture: single-process Pygame application with a large string-based state machine
- Current size of `main.py`: about 8,637 lines, so most gameplay flow still lives there
- Important support modules:
  - `tokens.py`: canonical token catalogue and metadata
  - `config.py`: screen, colors, audio, and shared constants
  - `utils.py`: utility helpers including data path handling
  - `systems/email_db.py`: JSON-backed inbox/outbox delivery logic
  - `systems/enhanced_npc.py`: offline trait-based NPC email responses
  - `systems/token_inventory.py`: progression/token storage
  - `systems/steam_manager.py`: optional Steamworks wrapper
  - `systems/resolution.py` and `systems/resolution_manager.py`: scaling and coordinate adaptation

## Core gameplay model

The project is driven by progression tokens. Tokens unlock modules, story beats, emails, guided mission paths, outside BBS access, pirate radio, and game prototypes.

Representative flow:

1. Player boots into the BBS and logs in or creates a handle/PIN.
2. Reading specific terminal content grants onboarding tokens such as `PSEM`.
3. Tokens trigger automatic emails and unlock menu modules.
4. Guided email paths push the player into specific narrative missions.
5. Missions grant more tokens such as `GAMES1`, `JAX1`, `ASTROMINER`, `CYBERTRAIN`, `RADIO_ACCESS1`, and school-hack progression tokens.
6. The player enters embedded games, OS-mode interactions, pirate radio, and other BBS worlds as content opens up.

This token-first design is the main organizing principle of the codebase.

## Important game states and modules

From the current code and docs, the main runtime includes these major areas:

- `main_menu`: top-level BBS hub
- `main_terminal_feed` / front-post content: onboarding posts and story feed
- `email` screens: inbox, sent, archive, reading, compose, guided email missions
- `games`: launches embedded game sessions from the registry
- `urgent_ops`: narrative tasks and challenge entry points
- `os_mode`: a faux Bradsonic desktop environment inside the game
- `pirate_radio`: radio UI and streamed/triggered audio behavior
- `outside_bbs`: dial-in sequences to other BBS worlds
- `game_session`: active embedded game adapter mode

The project is effectively several sub-experiences living inside one shell application.

## Where content and state live

### Runtime data

- `Data/user_state.json`: active player/user profile state
- `Data/emails_inbox.json`: authored inbound email content and token-triggered mail
- `Data/emails_outbox.json`: authored outbox templates
- `Data/main_terminal_feed.json`: front-post / feed content
- Per-game leaderboard files in game directories

### Major content folders

- `Data/games/`: game registry, adapters, Python minigames, C++ integrations
- `Data/OS/`: Bradsonic desktop, applications, and mini-app content
- `Data/Pirate_Radio/`: pirate radio implementation and related assets
- `Data/Outside_BBSs/`: separate dial-in BBS experiences such as Paper Crane, Never Again, and Echo Chamber
- `Data/Urgent_Ops/`: mission-specific challenge scripts
- `Data/Audio/`, `Data/Videos/`, `Data/images/`, `Data/Bradsonic_Docs/`: media and presentation assets

### Non-core but relevant repo areas

- `tests/`: focused tests around NPC realism and email behavior
- `Game4/`: a separate packaged prototype/debugger-style game module and docs, not the main BBS runtime
- `sandbox media/`: integration references and staging material, especially for C++ game embedding

## Game integration architecture

The BBS supports multiple game integration styles through `Data/games/registry.py`.

### Embedded Python session

- `SIMULACRA_CORE` runs as an in-process Pygame session via `BaseGameSession`

### Embedded C++ framebuffer sessions

- `ASTRO MINER`
- `CYBERTRAIN`

These use Python wrapper modules like `astrominer_embed.py` and `cybertrain_embed.py`, with the C++ side exposing framebuffer-style rendering that gets presented inside the BBS desktop/game area.

### Outside BBS takeovers

Separate BBS experiences can take over the screen and act like their own worlds. These are still part of the main narrative ecosystem.

## Narrative and mission design patterns

Two patterns show up repeatedly:

### 1. Token-triggered authored content

Narrative beats are often implemented by:

- grant token
- auto-send email
- pulse/highlight a UI target
- guide the player to the next action

### 2. Vital Mission Path

The repository has a clearly documented guided-flow pattern in `VITAL_MISSION_PATH_DOCUMENTATION.md`. This is the house style for critical story guidance:

- pulse relevant menu items
- pre-fill or hint required email text
- validate the player action
- grant a new token
- queue the follow-up email or unlock

This is a key design convention and should be preserved when adding new critical-path content.

## Email and NPC system summary

The email system is one of the strongest structured subsystems in the repo.

- Authored email content lives in JSON
- Dynamic NPC responses are generated locally with no external API
- NPCs have distinct traits and tones:
  - Glyphis: cryptic, formal, surveillance-heavy
  - Rain: direct, friendly, mission-focused
  - Jaxkando: excited, game-obsessed, louder voice
  - Uncle-am: nostalgic, warm, emotionally human
- Delayed email delivery is part of the realism model
- Placeholder substitution such as `{username}` is supported
- Sent/delivered IDs are tracked to avoid duplication

The email system is also tightly coupled to progression. In practice, it is not just messaging UI; it is one of the main narrative controllers.

## Documentation already present in the repo

The existing markdown files are useful because they capture both intended design and historical refactoring context.

Most relevant high-signal docs:

- `README.md`: basic pitch and onboarding
- `CLAUDE.md`: most accurate concise architecture summary currently present
- `EMAIL_SYSTEM_README.md`: JSON email schema and triggers
- `ENHANCED_EMAIL_SYSTEM.md`: NPC response design
- `VITAL_MISSION_PATH_DOCUMENTATION.md`: guided mission implementation pattern
- `IMPROVEMENTS.md`: desired future direction
- `CODE_REVIEW.md`: identifies the monolithic structure and technical debt in `main.py`
- `EMAIL_SYSTEM_COMPREHENSIVE_REVIEW.md`: strengths and weaknesses of the current email model
- Steam and build docs: useful when packaging or shipping, but secondary for understanding gameplay architecture

## Technical reality and risks

This codebase is functional, ambitious, and content-rich, but it is not heavily modular yet.

Important practical realities:

- `main.py` is still the dominant source of truth for runtime behavior
- state handling is string-driven and spread across a very large class
- some docs describe planned content that is only partially implemented
- there are prototype/experiment files in the root that are not part of the main runtime
- the repo includes large media/design/build artifacts alongside game code
- Windows assumptions are present in several places, especially around C++ integrations and embedding

If making changes, verify behavior in code rather than trusting a single document.

## What appears to be actively important vs. peripheral

### Actively important

- `main.py`
- `tokens.py`
- `config.py`
- `utils.py`
- `systems/`
- `Data/`
- `tests/`

### Peripheral, historical, or experimental

- standalone experiment scripts in the repo root such as `GPT4O.py`, `GPT5.py`, `handshake_001.py`, `retro_core_breach.py`, `LANDER TRIAL.py`
- large PSD/video/premiere assets
- some planning/review docs that describe aspirations rather than current truth

## How to run and validate

### Run

```bash
python main.py
```

### Tests

```bash
python -m pytest tests/
```

Current test coverage is narrow and mostly focused on email/NPC systems rather than full end-to-end gameplay flow.

## Working assumptions for future edits

When returning to this project later, these are safe baseline assumptions:

- This is a narrative BBS shell first, not just a collection of minigames.
- Tokens are the central progression API.
- Email content and guided UI pulses are core storytelling tools.
- `main.py` still needs to be read for any substantial behavior change.
- `Data/` JSON and authored content are part of the game logic, not just assets.
- C++ game integration is a first-class feature, especially for Astro Miner and CyberTrain.
- Existing docs are helpful but sometimes lag behind the code; cross-check important claims.

## Short version

GlyphisIO BBS The Proxy Tapes is a retro-styled, offline, narrative-driven Pygame BBS that uses token-gated progression, authored JSON content, offline NPC email interactions, faux operating-system sequences, pirate radio, and embedded Python/C++ minigames to deliver a larger story world. The project is content-rich and structurally ambitious, but most runtime behavior still lives in a large `main.py`, so future work should treat the existing docs as guides and the code as the final authority.
