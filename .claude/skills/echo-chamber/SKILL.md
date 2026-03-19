---
name: echo-chamber
description: "Understand, extend, or modify the Echo Chamber BBS — an outside BBS experience in GlyphisIO BBS. Use this skill whenever the user wants to: add content to the Echo Chamber (tutorials, forum threads, darknet files), modify the download system, change the visual theme, add new panels or menu options, modify the connection sequence, adjust the sysop message, debug rendering or input handling, or create a new Outside BBS following the same pattern. Trigger on keywords: Echo Chamber, outside BBS, SHADOWBYTE, darknet, ASM tutorials, underground forums, pirate radio unlock, echo-banner, modem dial echo, 15050 kHz, download progress, ECHOCHAMBER token."
---

# Echo Chamber BBS Skill

This skill covers the architecture, content systems, and extension patterns for the **Echo Chamber BBS** — an underground hacker BBS experience accessed from within the main GlyphisIO BBS.

---

## What the Echo Chamber Is

The Echo Chamber is a self-contained "Outside BBS" that overlays the main BBS window. It simulates an underground bulletin board run by sysop **SHADOWBYTE**, featuring banned ASM tutorials for the fictional Bradsonic 69000 processor, underground programming forums, and a darknet file download system.

It is a single Python class (`EchoChamberBBS` in `Data/Outside_BBSs/EchoChamberBBS/EchoChamber.py`, ~1785 lines) rendered on the BBS surface with its own state machine, input handling, and visual effects.

---

## File Structure

```
Data/Outside_BBSs/EchoChamberBBS/
    EchoChamber.py          # Full implementation (~1785 lines)
    __init__.py             # Package export: EchoChamberBBS
    echo-banner.png         # Splash screen banner image

Data/Pirate_Radio/Live_Stations/
    EchoChamber-DeTuned.wav # Radio station (detuned)
    EchoChamber-Tuned.wav   # Radio station (tuned in)

Data/images/
    echo-chamber.png        # BBS menu/promotional image
    echo-chamber2.png       # Alternate image
```

---

## How the Player Reaches Echo Chamber

### Step 1: Pirate Radio Discovery
The player tunes to **15050 kHz** ("Echo Chamber" station) in Pirate Radio. On first play, the `ECHOCHAMBER` token is awarded via `self.on_token_award("ECHOCHAMBER")` in `Data/Pirate_Radio/PirateRadio.py` (~line 1566).

### Step 2: OS Mode Modem Dial
Once the player holds the `ECHOCHAMBER` token, they can dial **0757421989** from the OS Mode modem. The modem connection sequence in `Data/OS/OS_Mode.py` (~line 2088-2102) routes to `"echo_chamber"`.

### Step 3: Launch in main.py
`main.py` catches the `"echo_chamber"` external BBS identifier and calls `_launch_echo_chamber_bbs()` (~line 2053-2066):

```python
def _launch_echo_chamber_bbs(self, return_to_os: bool = False) -> None:
    self.echo_chamber_return_to_os = return_to_os
    self.echo_chamber_bbs = EchoChamberBBS(
        width=self.bbs_width,
        height=self.bbs_height,
        scale=self.scale,
        on_exit=self._exit_echo_chamber_bbs,
    )
    self.state = "echo_chamber"
```

---

## Integration with main.py

The Echo Chamber uses a callback-driven pattern shared by all Outside BBSes:

| Hook | Location | Purpose |
|------|----------|---------|
| Import | lines 54-59 | `from Outside_BBSs.EchoChamberBBS.EchoChamber import EchoChamberBBS` with try/except |
| Instance vars | lines 1064-1065 | `self.echo_chamber_bbs = None`, `self.echo_chamber_return_to_os = False` |
| Reset vars | lines 2013-2014 | Same vars reset in `_reset_to_beginning()` |
| Launch | lines 2053-2066 | `_launch_echo_chamber_bbs(return_to_os)` |
| Exit callback | lines 2068-2079 | `_exit_echo_chamber_bbs()` — returns to OS or main terminal |
| Event handling | lines 6645-6649 | Forwards events, consumes all input while active |
| Update | lines 6790-6791 | `echo_chamber_bbs.update(dt)` |
| Render | lines 6816-6817 | `echo_chamber_bbs.draw(self.bbs_surface)` |
| Cursor | lines 7189-7191 | Shows system cursor while active |

### Exit Flow
- `_end_call()` sets `request_exit = True` and calls `on_exit()` callback
- If launched from OS Mode modem: returns to OS Mode with `_set_network_disconnected()`
- If launched from normal BBS: returns to main terminal feed via `_reset_to_beginning()`

---

## State Machine

```
"connecting"  →  "splash"  →  "menu"  →  "panel"
   (auto)       (SPACE)      (ENTER)    (ESC → menu)
                (ESC → exit) (ESC → exit)
```

- **connecting**: Terminal-style connection log, one line per ~0.4s (12 messages total), auto-advances to splash
- **splash**: Banner image + "PRESS SPACE TO CONNECT" prompt
- **menu**: 5 options — BANNED ASM TUTORIALS, UNDERGROUND PROG. FORUMS, DARKNET FILEZ, SYSTEM OPS, LOGOFF
- **panel**: Content view for the selected menu option

---

## Content Systems

### 1. ASM Tutorials (`self.tutorials`, built by `_build_tutorials()`)
- 10 tutorials about the Bradsonic 69000 processor
- Each has: `title`, `category` (FUNDAMENTALS/CONTROL FLOW/I/O/VIDEO/TOOLS/HARDWARE), `lines` (content array)
- Content includes ASM instruction examples, memory maps, debugging techniques
- Color-coded rendering: instructions in CYAN, labels in GOLD, comments in GREEN_DIM
- Navigation: UP/DOWN to select, ENTER to open, ESC to close, UP/DOWN/PGUP/PGDN to scroll

### 2. Forum Threads (`self.forum_threads`, built by `_build_forum_threads()`)
- 6 threads from underground community members
- Each has: `title`, `author`, `date`, `replies` (count), `lines` (content array)
- Authors: ghost_coder, silicon_dreams, SHADOWBYTE, analog_witch, void_walker, old_timer
- Dates: 1989.11.01 - 1989.11.15
- Navigation: UP/DOWN to select thread, ENTER to read, ESC to close

### 3. Darknet Files (`self.darknet_files`, built by `_build_darknet_files()`)
- 4 text/ASM files with real download-to-disk capability
- Each has: `name`, `size`, `desc`, `content` (text written to .brad file)
- Downloads are **region-gated**: requires `os_locale == 1` (US Mainland)
- When region is American Pacifica (default), shows "TRANSFER BLOCKED" error for 3 seconds
- On successful download, calls `on_download_file(filename, content)` callback which saves to `Data/OS/FILE-SYSTEM/DOWNLOADS/`
- Files appear as `.brad` files in the OS Mode file system browser
- Navigation: UP/DOWN to select, ENTER to download, ESC to go back

### 4. System Ops (hardcoded in `_draw_sysop_panel()`)
- Message from SHADOWBYTE with BBS rules and community philosophy
- Dynamic stats: random uptime (100-999h), users (5-23), files (500-2000)
- Scrollable with UP/DOWN

---

## Download System (DARKNET FILEZ)

The download system writes real `.brad` files to the OS file system, gated by the player's region setting.

### Callbacks (passed from main.py)
```python
get_region: Optional[Callable[[], int]]           # Returns os_locale (1=Mainland, 3=Pacifica)
on_download_file: Optional[Callable[[str, str], None]]  # Saves file to DOWNLOADS folder
```

### Region Gating
- Before starting any download, `get_region()` is checked
- If result != 1 (not US Mainland), sets error state: "TRANSFER BLOCKED" for 3 seconds
- No hint is given about how to change region — player must discover the forum thread
- The forum thread "HOW TO UNLOCK FILE TRANSFERS (READ THIS)" by `packet_rat` guides players to find admin credentials in the OS file system and change their region via the admin console

### State Variables
```python
self.downloading_file: Optional[int] = None  # Index of file being downloaded
self.download_progress = 0.0                  # 0-100% progress
self.download_speed = 0.0                     # KB/s speed
self.download_timer = 0.0                     # Timer for post-completion delay
self.download_error_timer = 0.0               # Error display countdown
self.download_error_message = ""              # Error text to show
```

### Download Flow
1. ENTER pressed on a file → region check
2. If blocked: show red "TRANSFER BLOCKED" + white error message for 3s
3. If allowed: progress bar animation (same as before)
4. On completion (after 1.2s hold): calls `on_download_file(filename, content)`
5. File saved to `Data/OS/FILE-SYSTEM/DOWNLOADS/` as `.txt` (displayed as `.brad` in OS Mode)

### Download UI
- **Progress**: Centered filename, green progress bar, percentage, golden "TRANSFER COMPLETE" text
- **Error**: Red "TRANSFER BLOCKED" title + white body text, centered in panel, auto-dismisses after 3s
- **Input locked** during both download and error states

---

## Visual Architecture

### Color Palette (Vegas Neon / Hacker Terminal)
```python
GREEN = (0, 200, 100)           # Primary neon green
GREEN_BRIGHT = (100, 255, 150)  # Highlights / selection
GREEN_DIM = (0, 80, 40)         # Borders, subtle elements
WHITE = (220, 220, 220)         # Off-white body text
GOLD = (255, 215, 0)            # Labels, accents, metadata
CYAN = (0, 255, 240)            # ASM instructions, special highlights
RED = (255, 50, 80)             # Warnings, errors
BG = (5, 8, 12)                 # Very dark blue-black background
BG_PANEL = (10, 15, 20)         # Panel background
STAR_COLOR = (150, 150, 150)    # Twinkling stars
```

### Visual Effects
- **Twinkling stars**: 60 particles with parallax scrolling, sine-wave brightness
- **CRT scanlines**: 3px spacing, alpha 30 overlay
- **Pulsing border**: Double border with sine-wave glow animation
- **Diamond decorations**: 4 corner diamonds with sparkle centers
- **Subtle grid**: Background grid lines in (10, 15, 20)
- **Blinking cursor**: 0.5s interval toggle

### Font System
All using "Retro Gaming.ttf", scaled by `self.scale`:
- `font_title`: 28pt — titles
- `font_label`: 18pt — labels, prompts
- `font_body`: 14pt — body text, file names
- `font_small`: 12pt — metadata, footers
- `font_code`: 11pt — tutorial/forum content

### Panel Layout
- **Menu** (left): ~50% width, starts at x=30, renders menu options vertically
- **Content panels** (right): x=50% of width, w=47% of width, h=75% of height, y=100*scale
- Panels use `_draw_panel_box()` for consistent styled containers with shadow, title bar

---

## Adding New Content

### Adding a Tutorial
In `_build_tutorials()`, append to the returned list:
```python
{
    "title": "YOUR TUTORIAL TITLE",
    "category": "CATEGORY_NAME",  # e.g. FUNDAMENTALS, HARDWARE, etc.
    "lines": [
        "Line 1 of content",
        "Line 2 of content",
        # Color coding is automatic based on content:
        # Lines with ASM-like patterns → CYAN
        # Lines starting with labels → GOLD
        # Lines starting with ; → GREEN_DIM (comments)
    ]
}
```

### Adding a Forum Thread
In `_build_forum_threads()`, append:
```python
{
    "title": "THREAD TITLE",
    "author": "username",
    "date": "1989.MM.DD",
    "replies": 42,
    "lines": [
        "[username] ORIGINAL POST:",
        "Post content...",
        "",
        "[other_user] REPLY:",
        "Reply content...",
    ]
}
```

### Adding a Darknet File
In `_build_darknet_files()`, append:
```python
{
    "name": "filename.txt", "size": "X KB",
    "desc": "Short description",
    "content": "The actual text content that gets saved as a .brad file..."
}
```
Only text files (.txt, .asm) are supported — the `content` field is what gets written to disk via `on_download_file()`.

### Adding a New Menu Panel
1. Add the option string to `self.menu_options` list
2. Add an `elif` branch in `handle_event()` panel state (~line 1031-1043)
3. Create `_handle_{panel}_event()` method for input
4. Add an `elif` branch in `_draw_panel()` to call the draw method
5. Create `_draw_{panel}_panel()` method for rendering

---

## Creating a New Outside BBS (Following This Pattern)

To create a new Outside BBS using the Echo Chamber as a template:

### 1. Create the package
```
Data/Outside_BBSs/YourBBSName/
    YourBBS.py       # Main class
    __init__.py      # Export: from .YourBBS import YourBBSClass
    banner.png       # Splash image (optional)
```

### 2. Class constructor signature
```python
class YourBBSClass:
    def __init__(self, width: int, height: int, scale: float,
                 on_exit: Optional[Callable[[], None]] = None,
                 get_region: Optional[Callable[[], int]] = None,
                 on_download_file: Optional[Callable[[str, str], None]] = None):
```
The `get_region` callback returns the player's OS locale (1=Mainland, 2=Europe, 3=Pacifica). Use it to gate downloads — only allow when region == 1. The `on_download_file(filename, content)` callback saves a .brad file to the OS DOWNLOADS folder.

### 3. Required interface methods
```python
def update(self, dt: float) -> None:     # Called every frame
def handle_event(self, event) -> bool:   # Returns True if event consumed
def draw(self, surface) -> None:         # Render to BBS surface
```

### 4. Integration in main.py
- Add import with try/except fallback (like lines 54-59)
- Add instance variables: `self.your_bbs = None`, `self.your_bbs_return_to_os = False`
- Add launch method: `_launch_your_bbs(return_to_os)`
- Add exit callback: `_exit_your_bbs()`
- Wire into event loop, update loop, render loop, and cursor handling
- Add reset in `_reset_to_beginning()`

### 5. Token gate (optional)
- Add token to `tokens.py` or use a hardcoded string
- Award token from Pirate Radio, email, or other trigger
- Check token in OS Mode modem for dial access

---

## Key Design Patterns

1. **Callback-driven exit**: Uses `on_exit` callback — never manages main BBS state directly
2. **Stateless content**: All tutorials, forums, files are hardcoded data structures (no JSON persistence)
3. **Region-gated downloads**: Downloads require US Mainland region (os_locale==1); blocked in Pacifica (default)
4. **Download-to-disk**: Successful downloads call `on_download_file()` which saves .brad files to OS DOWNLOADS folder
5. **Scale-aware rendering**: All dimensions multiplied by `self.scale` for resolution independence
6. **Input consumption**: Returns `True` from `handle_event()` to swallow input from main loop
7. **CRT aesthetic**: Scanline overlay + star background + pulsing border applied in `draw()` after content
