# GlyphisIO BBS

A retro BBS-style terminal game featuring an underground hacker community and mysterious AI NPC interactions.

## Overview

GlyphisIO BBS is an immersive, keyboard-controlled BBS simulation where you interact with an underground hacker group. The game features a mysterious NPC called "GlyphisIO" - an all-seeing, impersonal force that sets the tone for the entire experience.

## Features

- **Full Keyboard Navigation**: No mouse required - navigate with TAB, arrow keys, ENTER, and ESC
- **BBS Loading Screen**: Authentic connection sequence
- **Multiple Modules**:
  - Front Post Board - Community news and announcements
  - Email System - Communicate with GlyphisIO and other members
  - Games - Coming soon
  - Urgent Tasks - BBS jobs and side quests
  - Team Info - Member bios and dossiers
  - Pirate Radio - Simulated underground radio stream
- **AI NPC Interactions**: GlyphisIO responds to your messages using keyword-based NLP
- **Retro Aesthetic**: Cyan text on black background with Pixellari font

## Tokens

- `PSEM` - granted after reviewing all welcome threads; unlocks the email system.
- `USERNAME_SET` - set once you register a handle with Glyphis.
- `PIN_SET` - records that your login PIN is configured.
- `GAMES1` - earned via Glyphis' onboarding follow-up; unlocks the games vault.

## Installation

1. Install Python 3.10 or higher
2. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Ensure `Pixellari.ttf` is in the project directory

## Running the Game

```bash
python main.py
```

## Controls

- **TAB**: Switch between menu items/modules
- **UP/DOWN Arrow Keys**: Navigate lists and options
- **ENTER**: Select/open items
- **ESC**: Return to previous menu or close current view
- **SPACE**: Toggle Pirate Radio playback (when in Radio module)
- **Text Input**: When composing emails, type normally. Use TAB to switch between subject and body fields.

## Game Flow

1. **Loading Screen**: Watch the BBS connection sequence
2. **Main Menu**: Navigate between modules using TAB and arrow keys
3. **Email System**: 
   - Start by checking your INBOX for the welcome message from GlyphisIO
   - Compose a NEW MESSAGE to thank GlyphisIO for the invitation
   - Send the message and wait for a response
   - GlyphisIO will respond based on keyword detection in your message

## Story

The game follows your journey as a new member of the GlyphisIO underground hacker group. You start by thanking GlyphisIO for the invitation, but as the story progresses, things become more serious. The full story outline is available in `STORY.txt`.

## Current Status

- ✅ BBS interface with keyboard navigation
- ✅ Loading screen
- ✅ Email system with GlyphisIO NPC responder
- ✅ Front Post Board module
- ✅ Task and Team Info modules
- ✅ Pirate Radio module (placeholder)
- ⏳ Games module (coming soon)
- ⏳ Full story implementation
- ⏳ Audio playback for Pirate Radio

## Technical Details

- Built with Pygame
- Uses keyword-based NLP for NPC responses (no external API required)
- All interactions are keyboard-only for authentic BBS experience
- Modular design for easy expansion

## Notes

- The game is designed to be fully offline
- All NPC responses are generated locally using pattern matching
- The aesthetic is based on 1980s-1990s BBS systems
- Future updates will include more sophisticated NLP and story progression

---

**Welcome to GlyphisIO. I will be watching.**

