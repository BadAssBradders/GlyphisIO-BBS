# Vital Mission Path - Complete Process Documentation

## Overview
The "Vital Mission Path" is a guided email interaction system that uses visual indicators (pulsing/blinking) and pre-written text to guide players through critical story moments. This document details the exact process for the Astro Miner email flow and should be used as a template for all future "Vital Mission Path" implementations.

---

## Astro Miner Email Flow - Complete Process

### Phase 1: Initial Email Delivery
**Trigger:** Player has `JAX` token (read Jaxkando's "Targets Acquired" post) but NOT `JAX1` token

**Email Delivery:**
- **Sender:** `jaxkando@ciphernet.net`
- **Subject:** `"ASTRO-MINER - Ready to Crack!"`
- **Delivery Method:** `_deliver_jaxkando_astrominer_email()` function
- **Sound:** Mail notification sound plays
- **Location:** Email appears in INBOX

**Email Body Content:**
```
Hey {username}!

I was MIGHTY impressed with how quickly you got that complicated LAPC-1
Soundcard working on your Bradstation 69000! That was seriously cool!

So, I've got a game for you to crack. It's called ASTRO-MINER.
It's a game about mining asteroids, laser beams, trading, and landing...

Yes, I said landing! *slightly ironic but excited tone*

The crack file is loaded into the CRACKER IDE, and the documentation
for the copy-protection is in the manual. All you have to do is find
the loop within the code that performs the copy check and using the
BBS's reverse engineering debugger, just insert some code that will
jump over it.

I'll be in the chat to help, but once that's done, then the game will
be available for everyone to play, and I'll even wire up the global
leaderboard for extra funtimes!

Let's do this!

-jaxkando
```

---

### Phase 2: Visual Indicators - Main Menu

**Location:** Main BBS Menu (when `is_guided_email_mode_active()` returns True)

**Condition Check:**
```python
def is_guided_email_mode_active(self) -> bool:
    has_jax = self.inventory.has_token(Tokens.JAX)
    has_jax1 = self.inventory.has_token(Tokens.JAX1)
    return has_jax and not has_jax1
```

**Visual Behavior:**
- **Module Name:** `"EMAIL SYSTEM"`
- **Pulsing:** YES - Pulses between base color and light cyan
- **Pulse Color:** `(150, 255, 255)` - Light cyan
- **Base Colors:**
  - When selected: `WHITE` (255, 255, 255)
  - When not selected: `DARK_CYAN` (0, 139, 139)
- **Pulse Speed:** `1.5` Hz (1.5 cycles per second)
- **Pulse Function:** `get_pulse_color(base_color, light_cyan, speed=1.5)`
- **Implementation:** Uses sine wave interpolation between base and light colors

**Code Location:** `main.py` lines 2821-2826

---

### Phase 3: Visual Indicators - Email Menu

**Location:** Email Menu Screen (after entering EMAIL SYSTEM)

**Visual Behavior:**
- **Menu Option:** `"NEW MESSAGE"`
- **Pulsing:** YES - Same pulsing behavior as main menu
- **Pulse Color:** `(150, 255, 255)` - Light cyan
- **Base Colors:**
  - When selected: `WHITE` (255, 255, 255)
  - When not selected: `DARK_CYAN` (0, 139, 139)
- **Pulse Speed:** `1.5` Hz
- **Condition:** Only pulses when `is_guided_email_mode_active()` is True

**Code Location:** `main.py` lines 3665-3669

---

### Phase 4: Visual Indicators - Inbox

**Location:** Inbox email list

**Visual Behavior:**
- **Email Highlighting:** Unread emails show in `CYAN` (0, 255, 255)
- **Read Emails:** Show in `DARK_CYAN` (0, 139, 139)
- **Selected Email:** Highlighted with `HIGHLIGHT_BLUE` background and `ACCENT_CYAN` border
- **Prefix Icons:**
  - Unread: `[*]`
  - Read: `[ ]`
  - Selected: `[>]`

**Note:** Currently, there is NO specific pulsing for individual emails in the inbox. The pulsing only occurs at the menu level.

**Code Location:** `main.py` lines 4034-4042

---

### Phase 5: Composing Reply - Guided Email Mode

**Trigger:** Player selects "NEW MESSAGE" from email menu while `is_guided_email_mode_active()` is True

**Auto-Populated Fields:**
- **TO:** `"jaxkando@ciphernet.net"` (automatically set)
- **SUBJECT:** Empty (user must type)
- **BODY:** Empty initially, but shows placeholder text

**Guided Email Configuration:**
```python
self.guided_email_active = True
self.guided_email_body_started = False
self.guided_email_subject = "CRACKING ASSISTANCE"  # Required subject
self.guided_email_body_placeholder = "[TELL JAX THAT YOU'RE INTERESTED IN CRACKING THE GAMES HE MENTIONED]"
self.active_field = "subject"  # Starts at subject field
```

**Code Location:** `main.py` lines 5545-5557

---

### Phase 6: Subject Field - Ghost Text

**Visual Behavior:**
- **Active Field:** Subject field starts active
- **Ghost Text:** Shows `"CRACKING ASSISTANCE"` in dark grey
- **Ghost Text Color:** `(80, 80, 80)` - Dark grey
- **Ghost Text Position:** Appears after whatever the user types
- **User Text Color:** `CYAN` (0, 255, 255) when active, `DARK_CYAN` (0, 139, 139) when inactive
- **Cursor:** Blinking `|` character in body color

**Example Display:**
- User types: `"CRACK"` → Shows: `"CRACK"` (cyan) + `"ING ASSISTANCE"` (dark grey ghost text)

**Code Location:** `main.py` lines 3775-3793

---

### Phase 7: Body Field - Placeholder Text

**Visual Behavior:**
- **Placeholder Text:** `"[TELL JAX THAT YOU'RE INTERESTED IN CRACKING THE GAMES HE MENTIONED]"`
- **Placeholder Color:** `(80, 80, 80)` - Dark grey
- **Placeholder Display:** Only shows when:
  - `guided_email_active` is True
  - `guided_email_body_started` is False (user hasn't started typing)
  - `compose_body` is empty
- **Placeholder Disappears:** When user starts typing (any key press sets `guided_email_body_started = True`)
- **User Text Color:** `CYAN` (0, 255, 255) when active, `DARK_CYAN` (0, 139, 139) when inactive
- **Cursor:** Blinking `|` character when body field is active

**Code Location:** `main.py` lines 3824-3843

---

### Phase 8: Sending the Email

**Validation:**
- **Required Subject:** Must be exactly `"CRACKING ASSISTANCE"` (case-insensitive check: `email.subject.upper().strip() == "CRACKING ASSISTANCE"`)
- **Body:** Can be anything (placeholder text is just a hint, not required)

**Token Grant:**
- **Token:** `JAX1` is granted when email is sent with correct subject
- **Reason:** `"sent CRACKING ASSISTANCE email to Jaxkando"`

**Code Location:** `main.py` lines 5241-5247

---

### Phase 9: NPC Response

**Response Delivery:**
- **Sender:** `jaxkando@ciphernet.net`
- **Subject:** `"RE: CRACKING ASSISTANCE"`
- **Delay:** 8-30 seconds (random, faster than normal due to "excited gamer energy")
- **Delivery Method:** Added to `delayed_emails` queue

**Response Body Content:**
```
{USERNAME}! Perfect timing!

The ASTRO MINER cracking session is all prepped and waiting for you in URGENT OPS! 
We're gonna use the Bradsonic's insane RAM to stream the whole game in - just like how the machine 
streams radio waves. No tapes, no discs, just pure streaming goodness!

Head to URGENT OPS and fire up the ASTRO MINER CRACKER. I'll be in the chat to help!

Oh, and coding is always better with some tunes! Since it's {daytime/nighttime}, 
I'd tune into {PACIFIC WAVE/SYNTH REBELS} on the Pirate Radio. {Good vibes for cracking!/Perfect for late-night hacking!} 
The best part? So long as you stay connected to the BBS, the music keeps playing even while you're 
working in the CRACKER-PARROT IDE. It's great for coding - helps you stay in the zone!

LET'S CRACK THIS THING AND PLAY THE HELL OUT OF IT!

-jaxkando
```

**Radio Station Selection:**
- **Daytime (6:00-17:59):** `"PACIFIC WAVE"` - "Good vibes for cracking!"
- **Nighttime (18:00-5:59):** `"SYNTH REBELS"` - "Perfect for late-night hacking!"

**Code Location:** `main.py` lines 5249-5286

---

## Color Reference

### Standard Colors (from config.py)
- `BLACK` = (0, 0, 0)
- `CYAN` = (0, 255, 255)
- `DARK_CYAN` = (0, 139, 139)
- `WHITE` = (255, 255, 255)
- `HIGHLIGHT_BLUE` = (0, 70, 120)
- `ACCENT_CYAN` = (0, 196, 255)
- `PANEL_BLUE` = (8, 16, 32)
- `DARK_BLUE` = (0, 0, 139)

### Vital Mission Path Specific Colors
- **Pulse Light Cyan:** `(150, 255, 255)` - Used for pulsing effect
- **Ghost/Placeholder Grey:** `(80, 80, 80)` - Used for hint text
- **Bracketed Text Grey:** `(128, 128, 128)` - Used for bracketed pre-written text (Rain's email)

---

## Pulse Function Implementation

```python
def get_pulse_color(self, base_color: tuple, light_color: tuple, speed: float = 2.0) -> tuple:
    """Get a pulsing color that oscillates between base and light color.
    
    Args:
        base_color: The normal color (RGB tuple)
        light_color: The lighter color to pulse to (RGB tuple)
        speed: Pulse speed in Hz (default 2.0 = 2 cycles per second)
        
    Returns:
        Interpolated color between base and light based on time
    """
    # Use sine wave for smooth pulsing, oscillating between 0 and 1
    t = time.time() * speed * 2 * math.pi
    pulse = (math.sin(t) + 1) / 2  # Range 0 to 1
    
    # Interpolate between base and light colors
    r = int(base_color[0] + (light_color[0] - base_color[0]) * pulse)
    g = int(base_color[1] + (light_color[1] - base_color[1]) * pulse)
    b = int(base_color[2] + (light_color[2] - base_color[2]) * pulse)
    return (r, g, b)
```

**Code Location:** `main.py` lines 2947-2966

---

## Summary: Complete Flow Sequence

1. **Main Menu:** "EMAIL SYSTEM" pulses in light cyan `(150, 255, 255)` at 1.5 Hz
2. **Email Menu:** "NEW MESSAGE" pulses in light cyan `(150, 255, 255)` at 1.5 Hz
3. **Compose Screen Opens:**
   - TO field: Auto-filled with `"jaxkando@ciphernet.net"`
   - SUBJECT field: Active, shows ghost text `"CRACKING ASSISTANCE"` in dark grey `(80, 80, 80)`
   - BODY field: Shows placeholder `"[TELL JAX THAT YOU'RE INTERESTED IN CRACKING THE GAMES HE MENTIONED]"` in dark grey `(80, 80, 80)`
4. **User Types Subject:** Ghost text updates dynamically
5. **User Types Body:** Placeholder disappears on first keystroke
6. **User Sends Email:** Must have subject "CRACKING ASSISTANCE" (case-insensitive)
7. **Token Granted:** `JAX1` token granted
8. **NPC Response:** Jaxkando replies in 8-30 seconds with instructions

---

## Important Note: Reply vs. New Message

**Current Implementation:**
- **NEW MESSAGE (Guided Mode):** Uses placeholder text `[TELL JAX THAT YOU'RE INTERESTED IN CRACKING THE GAMES HE MENTIONED]` in dark grey
- **REPLY to Jaxkando's "ASTRO-MINER - Ready to Crack!" email:** Currently has NO pre-written body text (body starts empty)

**If you want replies to also have pre-written text:**
You would need to add a check in `start_reply_to_selected_email()` similar to Rain's school email:

```python
# Check if this is Jaxkando's Astro Miner email
is_jax_astrominer_email = (hasattr(self.selected_email, 'sender') and 
                          self.selected_email.sender == "jaxkando@ciphernet.net" and
                          hasattr(self.selected_email, 'subject') and 
                          "ASTRO-MINER" in self.selected_email.subject.upper() and
                          "Ready to Crack" in self.selected_email.subject)

if is_jax_astrominer_email:
    self.compose_body = "[PRE-WRITTEN REPLY TEXT HERE]"
```

---

## Notes for Uniform Implementation

### ⚠️ IMPORTANT: What Must Be Uniform vs. What Can Differ

**ALWAYS UNIFORM (Copy These Exactly):**
1. **Pulse Color:** `(150, 255, 255)` - Light cyan
2. **Pulse Speed:** `1.5` Hz
3. **Placeholder Text Color:** `(80, 80, 80)` - Dark grey
4. **Ghost Text Color:** `(80, 80, 80)` - Dark grey (if using ghost text)
5. **Pulse Function:** Always use `get_pulse_color()` for all pulsing effects
6. **Placeholder Pattern:** Bracketed text `[INSTRUCTION TEXT]` in dark grey
7. **Placeholder Behavior:** Disappears when user starts typing
8. **Ghost Text Pattern:** Shows remaining required text after user input (if applicable)

**CAN DIFFER (Based on Mission Requirements):**
- **Which menu item pulses:** Can be "NEW MESSAGE", "INBOX", or other options depending on the flow
- **The actual path:** Some missions require reading first (INBOX), others require composing new (NEW MESSAGE)
- **Subject validation:** Only needed if there's a required subject (like "CRACKING ASSISTANCE")
- **Additional indicators:** Extra visual cues (like "R: reply" pulsing) can be added as needed

**Examples:**
- **Astro Miner:** Main Menu → Email Menu → **NEW MESSAGE** pulses → Compose new email
- **Rain:** Main Menu → Email Menu → **INBOX** pulses → Read email → Reply

Both use the same colors, pulse rate, and placeholder styling - but the flow differs based on what makes sense for that mission.

---

## Rain's School Email Flow - Example of Different Path, Same Uniform Elements

Rain's school email uses a **similar but not identical** pattern to the Astro Miner flow:

### Similarities:
1. ✅ **Main Menu Pulsing:** "EMAIL SYSTEM" pulses in light cyan `(150, 255, 255)` at 1.5 Hz
2. ✅ **Pulse Function:** Uses same `get_pulse_color()` function
3. ✅ **Pre-written Text Color:** Dark grey `(80, 80, 80)` when not actively editing
4. ✅ **Text Color When Editing:** Normal body color (CYAN when active)

### Differences (By Design - Different Flow):
1. ✅ **Email Menu Pulsing:** Rain pulses **"INBOX"** (not "NEW MESSAGE") - because player must read email first
2. ✅ **Flow Path:** Rain's path is: Read Email → Reply (not Compose New)
3. ✅ **Placeholder Text:** Uses placeholder format `"[hey rain, count me in, what are the next steps?]"` (same as Astro Miner pattern)
4. ✅ **Additional Visual Indicator:** Rain has **pulsing "R: reply"** in the reading screen footer
   - Pulses between `DARK_CYAN` and `WHITE` (255, 255, 255)
   - Same speed: 1.5 Hz
   - Only shows when email is unread and no reply sent

### Rain's Complete Flow:
1. **Main Menu:** "EMAIL SYSTEM" pulses in light cyan `(150, 255, 255)` at 1.5 Hz
2. **Email Menu:** "INBOX" pulses in light cyan `(150, 255, 255)` at 1.5 Hz
3. **Reading Screen:** "R: reply" pulses in white (pulsing from DARK_CYAN to WHITE) at 1.5 Hz
4. **Reply Screen:** Body field shows placeholder `"[hey rain, count me in, what are the next steps?]"`
   - Placeholder shows in dark grey `(80, 80, 80)`
   - Placeholder disappears when user starts typing
   - Uses same `guided_email_active` pattern as Astro Miner

**Code Locations:**
- Main menu pulsing: `main.py` lines 2834-2838
- Email menu pulsing: `main.py` lines 3671-3675
- Reading screen pulsing: `main.py` lines 4139-4168
- Pre-written text: `main.py` lines 7156-7165, 3845-3856

### ✅ UPDATED: Rain's Flow - Uniform Visuals, Different Path

**Rain's Unique Flow:**
- **Path:** Main Menu → Email Menu → **INBOX** (pulses) → Read Email → Reply
- **Reason:** Player must read Rain's email first, then reply (different from Astro Miner's "compose new email" path)

**Uniform Elements (Same as Astro Miner):**
1. ✅ **Pulse Color:** Light cyan `(150, 255, 255)`
2. ✅ **Pulse Speed:** `1.5` Hz
3. ✅ **Placeholder Text Format:** Bracketed `"[hey rain, count me in, what are the next steps?]"`
4. ✅ **Placeholder Color:** Dark grey `(80, 80, 80)`
5. ✅ **Placeholder Behavior:** Disappears when user starts typing
6. ✅ **Uses same `guided_email_active` pattern** for placeholder handling

**Differences (By Design):**
- **Email Menu Pulsing:** Rain pulses **"INBOX"** (not "NEW MESSAGE") because player reads email first
- **Additional Indicator:** "R: reply" pulses in reading screen footer (extra visual cue)
- **No Subject Validation:** Rain's subject is pre-filled, no ghost text needed

**Note:** The uniform elements (colors, pulse rate, placeholder styling) are what make it consistent. The flow itself can differ based on the mission requirements.
