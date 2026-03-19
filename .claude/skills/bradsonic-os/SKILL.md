---
name: bradsonic-os
description: "Understand, extend, or modify the Bradsonic 69000 OS Mode desktop environment in GlyphisIO BBS. Use this skill whenever the user wants to: add a new desktop application or modal, modify OS region behaviour, add files to the simulated filesystem, extend the terminal/admin system, work with the BRADSONIC-MAIL client, add icons to the desktop, connect OS actions to the BBS token system, write world-building content for the alternate-1989 Bradsonic hardware/software, or debug any feature inside Data/OS/OS_Mode.py. Trigger on keywords: OS mode, Bradsonic, desktop, modal, terminal, os_locale, region, FILE-SYSTEM, dotSONIC, BRADSONIC-MAIL, datasette, hard drive, HDD, modem dial, notes app, games folder, scanline, ghost sequence, SCHOOL_HACK2."
---

# Bradsonic 69000 OS Mode Skill

This skill covers the complete architecture, lore, and extension patterns for the **Bradsonic 69000** desktop environment — the simulated alternate-1989 operating system embedded inside GlyphisIO BBS.

---

## What the OS Mode Is

The Bradsonic 69000 OS is a fully rendered desktop environment that sits **inside the BBS Pygame window**. It is not a separate process — it is a Python class (`OSMode` in `Data/OS/OS_Mode.py`, ~10 000 lines) that draws on top of the BBS surface and forwards events from the main Pygame loop.

The player reaches OS Mode via:
- **F10** hotkey (`_toggle_os_mode()`, main.py ~line 7760)
- **Automatic boot** on first logout when `MODEM1ST` token is held (main.py ~line 8012)
- **LAPC1 boot sequence** triggered when `LAPC1_NODE7` token is awarded (main.py ~line 6660)

The BBS calls `os_mode.draw()` and `os_mode.update(dt)` every frame while `os_mode_active` is `True`.

---

## File & Directory Structure

```
Data/OS/
    OS_Mode.py              # The entire desktop environment (~10 000 lines)
    Desktop-Enviroment.png  # Desktop wallpaper (note the typo in the filename)
    Scanline-Desktop.png    # CRT scanline overlay
    mouse_cursor.png        # Custom phosphor cursor sprite
    dialup.wav / dialup.pkf # Modem dial-up audio
    tape-icon.png  / S-tape-icon.png       # Datasette icon (normal / small)
    hard-drive-icon.png / S-hard-drive-icon.png
    modem-iconpng.png / S-modem-iconpng.png
    games-folder.png / S-games-folder.png
    notes-icon.png / S-notes-icon.png
    sonic-icon.png / S-sonic-icon.png       # dotSONIC (Region 1 & 2 only)
    mail-icon.png                            # BRADSONIC-MAIL (Region 1 only)
    chess/      solitaire/  snooker/  mahjong/  civitas_nihilium/
    dotSONIC/
    FILE-SYSTEM/
        SECURITY/   → LocaleProtocols.txt (world-building hardware spec)
        DOWNLOADS/  → downloaded .sonic audio files from Never Again BBS
        OS DATA/    → OS system files
        ISO69000/   → ISO image directory
```

**`OS_Mode.py`** imports nothing from the BBS except what is passed in via constructor callbacks — it is deliberately self-contained.

---

## OSMode Constructor & Callbacks

The `OSMode` class receives ~30 callbacks at construction. These are the bridge between the desktop and the BBS:

| Callback | Purpose |
|---|---|
| `grant_token(token, reason)` | Award a BBS token from a desktop action |
| `has_token(token)` | Check whether a token is held |
| `get_notes() / save_notes()` | Persist Notes app content |
| `get_recording_state() / set_recording_state()` | Datasette recording |
| `get_user_credentials()` | Username + PIN for terminal admin login |
| `get_chess_stats() / save_chess_stats()` | Chess game persistence |
| `get_inbox_emails() / save_inbox_emails()` | BRADSONIC-MAIL inbox |
| `get_mail_outbox() / save_mail_outbox()` | BRADSONIC-MAIL outbox |
| `get_mail_trash() / save_mail_trash()` | BRADSONIC-MAIL trash |
| `get_downloaded_fugamatchi_tracks() / add_downloaded_fugamatchi_track()` | .sonic files |
| `reset_bbs_and_exit_os` | Factory reset — exit OS, reset BBS state |
| `open_email_callback` | Switch BBS to email module |
| `set_quit_state_callback` | Transition to quit/credits screen |
| `exit_game_callback` | Force close application |

All OS-originated token grants go through `grant_token()`. Never write to `user_state.json` directly from inside `OS_Mode.py`.

---

## Regional Locale System

The OS locale is the single most important state variable. It gates feature availability and drives narrative progression.

| `os_locale` | Region | Features |
|---|---|---|
| `1` | **American Mainland** | Full access. dotSONIC visible. BRADSONIC-MAIL visible. No BBS connect restrictions. |
| `2` | **Europe** | Standard. dotSONIC visible. No cross-Atlantic email. Data cap restrictions. |
| `3` | **American Pacifica Isles** (default) | Restricted. 10 MB monthly cap. 120-min daily modem limit. No dotSONIC. No BRADSONIC-MAIL. JST timezone. |

**How region changes happen:**
1. **Ghost sequence** (narrative path): Player logs out with `SCHOOL_HACK1` token but not `SCHOOL_HACK2`. BBS plays "Midnight Rootkit" and displays typed instructions to hack the region. `SCHOOL_HACK2` is auto-granted when the sequence completes (main.py ~line 7997).
2. **Terminal admin path**: Open HDD → System → Terminal. Login with admin credentials (from `get_user_credentials()`). Select region via hotkeys A / S / D in `_switch_os_region()`.
3. **Admin switch string**: `admin-subset.username.general.password.louis-sonic` — typed in the terminal to unlock admin mode.

**Effect of `SCHOOL_HACK2` on the BBS** (main.py):
- Disables pulsing/blinking hints for Email System, The Wall, and Logout (lines ~2941–2960, ~3827–3834)
- Disables school grades post pulsing (~line 3570)
- Disables `(R)eply` pulsing on Rain's school email (~line 4285)

---

## Desktop Icons & Modals

All desktop windows are called **modals**. They are stored in `active_modals[]` with a Z-order. Each modal has a position dict entry, a title bar for dragging, and close/focus behaviour.

### Datasette (`tape-icon.png`)
- Modal: `tape_modal`
- Purpose: Cassette recording device. Plays `Datasette_Load.mp4` via OpenCV. Shows recording status and timer.
- Callbacks: `get_recording_state`, `set_recording_state`

### HDD (`hard-drive-icon.png`)
- Modal chain: `hard_drive` → `system_folder` → `file_system_browser`
- Purpose: Browse the simulated FAT12-style filesystem.
- Terminal accessible at HDD > System > Terminal.
- Commands: `file-system-start`, admin login, region select.
- File browser renders `.brad` (text config) and `.sonic` (audio) files.

### Modem (`modem-iconpng.png`)
- Modal: `modem_modal`
- Purpose: Dial the BBS. Target number: `0345728891` (GLYPHIS_IO BBS).
- Dial pad, DTMF tone sounds, connection state tracking.
- `_update_modem_packet_effect()` — animated packet visualisation during connect.

### Games (`games-folder.png`)
- Modal: `games_modal`
- Available: Chess, Solitaire, Snooker, Mahjong, Civitas Nihilium.
- All games live in subdirectories under `Data/OS/` and are pure-Python Pygame games (not DLL-based).

### Notes (`notes-icon.png`)
- Modal: `notes_modal`
- Tab-based, edit/view mode. One tab is a non-deletable mission objective note.

### dotSONIC (`sonic-icon.png`)
- Modal: `dot_sonic`
- **Visible only in Region 1 (US Mainland) and Region 2 (Europe).**
- Playlist management + volume. Plays `.sonic` track files downloaded from Never Again BBS.
- Tracks stored in `Data/OS/FILE-SYSTEM/DOWNLOADS/`.

### BRADSONIC-MAIL (`mail-icon.png`)
- Modal: `mail_modal`
- **Visible only in Region 1 (US Mainland).**
- Full email client: Inbox, Compose, Outbox, Trash, Settings, Server Connect.
- Settings: 1989-style SMTP/POP3 server config (technobabble lore).
- Default sender: `user@bradsonic.net`
- Narrative purpose: Player spoofs `region-support@telco-relay.bradsonic.net` to email the school receptionist (School Hack arc).

---

## Simulated File System (`FILE-SYSTEM/`)

The filesystem is a simulated **Modified FAT12** with extended attributes. It is presented in the HDD file browser modal.

Key world-building document: `FILE-SYSTEM/SECURITY/LocaleProtocols.txt`

**Contents (canonical lore):**
- **Bradsonic Incorporated** — founded 1947 by General Bradley Sonic, using former Matsushita Electric facilities in Osaka.
- **Bradsonic 69000** spec:
  - Processor: Single Accumulator Processor (Audio-Optimised)
  - RAM: 500 MB (justified in-world by silicon reserves from annexed Mongolia/Korean Peninsula, manufactured in Ulaanbaatar)
  - OS: BRADSONIC OS / BradCom Terminal Interface v2.1 on top of MS-DOS 3.30
  - Display: CGA+ cyan phosphor
  - Modem: Hayes-compatible 2400 baud built-in
  - Soundcard: RADLAND LAPC-1 compatible
  - CTO: **Louis Sonic** (descendant of founder; his name is the admin password component)
  - CEO: Elena Vance
- File support: `.brad` (text config), `.sonic` (audio tracks), `.wav`, `.mp3`
- **Bradsonic Transfer Protocol (BTP)** — fictional dial-up protocol with 2:1 ASCII compression

---

## Token System Integration

### Tokens Granted from OS Mode

| Token | Trigger |
|---|---|
| `SCHOOL_HACK2` | Region changed to American Mainland (via ghost sequence or terminal) |
| `ASTROMINER` | AstroMiner game session started from Games folder |
| `CYBERTRAIN` | CyberTrain game session started from Games folder |
| `AUDIO_ON` | All 7 LAPC-1 nodes operational — Fugamatchi's song plays |

### Tokens Checked by OS Mode / BBS

| Token | Effect |
|---|---|
| `MODEM1ST` | Auto-activates OS Mode on first logout |
| `LAPC1_NODE7` | Triggers OSBoot.mp4 video sequence |
| `SCHOOL_HACK1` | If held without `SCHOOL_HACK2` on logout, triggers ghost sequence |
| `SCHOOL_HACK2` | Disables BBS pulsing hints; grants full Mainland access in OS |

Always use `grant_token(Tokens.TOKEN_NAME, reason="...")` — never manipulate `user_state.json` directly.

---

## Adding a New Desktop Application

### 1. Create the modal open/close/draw/click methods

Follow the existing modal pattern in `OS_Mode.py`:

```python
# In __init__, add to active_modals-eligible names:
# modal name: "my_app_modal"

# Open it from an icon click:
def _open_modal(self, modal_name):
    ...

# Add a draw method:
def _draw_my_app_modal(self):
    pos = self.modal_positions.get("my_app_modal", (self.desktop_x + 100, self.desktop_y + 60))
    size = self._get_modal_size("my_app_modal")  # (width, height)
    # Draw title bar, content, close button using existing helpers

# Add a click handler:
def _handle_my_app_modal_click(self, rel_pos):
    ...
```

### 2. Add a desktop icon

```python
# In _load_icons(), add an icon entry:
{
    "name": "MY_APP",
    "image": pygame.image.load("Data/OS/my-app-icon.png"),
    "small_image": pygame.image.load("Data/OS/S-my-app-icon.png"),
    "pos": [self.desktop_x + 120, self.desktop_y + 220],  # baseline position
    "label": "MY APP",
    "visible": True,  # or conditional on self.os_locale
}
```

### 3. Define modal size

```python
def _get_modal_size(self, modal_name):
    sizes = {
        ...
        "my_app_modal": (600, 450),  # baseline at 2560x1440
    }
    base = sizes.get(modal_name, (400, 300))
    return (int(base[0] * self.scale), int(base[1] * self.scale))
```

### 4. Wire click → open in handle_event

```python
# Inside the icon click detection loop:
if icon["name"] == "MY_APP":
    self._open_modal("my_app_modal")
```

### 5. Wire draw call

```python
# Inside draw(), after the existing modal draw calls:
if "my_app_modal" in self.active_modals:
    self._draw_my_app_modal()
```

### 6. If region-gated, set visibility in `_update_locale_visibility()`

```python
def _update_locale_visibility(self):
    for icon in self.icons:
        if icon["name"] == "MY_APP":
            icon["visible"] = self.os_locale == 1  # US Mainland only
```

---

## Adding Files to the Simulated Filesystem

Files live in `Data/OS/FILE-SYSTEM/`. The HDD browser reads them via `_list_file_system_browser_directory()` and `_read_file_content()`.

- `.brad` files — plain text, opened in the terminal file viewer
- `.sonic` files — audio tracks playable in dotSONIC
- Subdirectories create nested folder navigation in the browser

To make a file narratively significant (e.g., a secret document the player finds), just add it to the appropriate subdirectory and add any relevant response to the `_read_file_content()` dispatch if special behaviour is needed.

---

## Terminal / Admin System

Terminal is accessed at HDD → System → Terminal.

**Terminal modes** (state variable `terminal_mode`):
- `"command"` — normal command prompt
- `"admin_login_username"` — waiting for username entry
- `"admin_login_password"` — waiting for password entry
- `"admin_menu"` — admin options shown
- `"region_select"` — press A / S / D to switch locale

**Admin credentials**: provided via `get_user_credentials()` callback. Password component includes `louis-sonic`.

**To add a new terminal command**, add a branch in `_terminal_execute_command()`:

```python
elif command == "my-command":
    self.terminal_output.append("> Executing my command...")
    # Perform action
```

---

## World-Building Rules for OS Content

When writing new OS content — file text, modal copy, terminal output, modal titles, app names — apply these principles:

1. **All software names avoid Japanese brands.** Instead: Bradsonic, NeoDrive, Western Beam, BradCom, RADLAND.

2. **The OS is American corporate but built on Japanese engineering.** Chunky, practical, slightly over-engineered. No kawaii aesthetics. Heavier than you'd expect.

3. **Region 3 (Pacifica Isles) feels restricted and surveilled.** Missing features, terse system messages, monthly cap warnings. Software licences denied "on political grounds."

4. **Region 1 (US Mainland) feels expansive and slightly menacing.** More features, but also more tracking. The freedom is ambiguous.

5. **The admin password (`louis-sonic`) is a breadcrumb.** Louis Sonic is the CTO — son of the company's founder. This detail rewards players who read `LocaleProtocols.txt`.

6. **Terminal output is terse ANSI/VT100 style.** Short lines, all-caps commands, no friendly help text. Feels like BradCom Terminal v2.1.

7. **dotSONIC tracks are culturally contraband.** `.sonic` files are banned music — treat them with narrative weight equal to the pirate radio.

---

## Rendering & Scale

All baseline coordinates are authored at **2560×1440**. Scale everything via `self.scale = res_manager.scale_factor`.

```python
scaled_x = int(baseline_x * self.scale)
scaled_value = int(baseline_value * self.scale)
```

**Desktop baseline position**: `desktop_x = 176`, `desktop_y = 209`
**Desktop baseline size**: `~1200 × 900`
**BBS window**: `872 × 654`

The scanline overlay (`Scanline-Desktop.png`) draws on top of everything for the CRT phosphor effect. The custom cursor (`mouse_cursor.png`) replaces the system pointer while OS Mode is active.

**Color palette:**
- `COLOR_CYAN` (0, 255, 255) — primary UI
- `COLOR_GREEN` (0, 255, 0)
- `COLOR_AMBER` (255, 191, 0) — highlights, warnings
- `COLOR_NEON_GREEN` (0, 255, 160) — terminal text
- `COLOR_MAGENTA` (255, 0, 153) — accent
- `COLOR_BLACK` (0, 0, 0) — background

Font: **Pixellari** (loaded in `_load_terminal_font()`). Use this for all OS modal text.

---

## Persistence

OS-originated data is stored in `Data/user_state.json` via callbacks. Never write JSON directly. Persisted fields:

| Data | Callback |
|---|---|
| Notes app content | `get_notes()` / `save_notes()` |
| Datasette recording | `get_recording_state()` / `set_recording_state()` |
| Chess game stats | `get_chess_stats()` / `save_chess_stats()` |
| BRADSONIC-MAIL inbox | `get_inbox_emails()` / `save_inbox_emails()` |
| BRADSONIC-MAIL outbox | `get_mail_outbox()` / `save_mail_outbox()` |
| BRADSONIC-MAIL trash | `get_mail_trash()` / `save_mail_trash()` |
| Downloaded .sonic tracks | `get_downloaded_fugamatchi_tracks()` / `add_downloaded_fugamatchi_track()` |

Icon positions persist across sessions via `_load_icon_positions()` / `_save_icon_positions()` (stored in `user_state.json`).
