# Trigger Map

## Read Order

1. `tokens.py`
2. `main.py`
3. `Data/OS/OS_Mode.py`
4. `systems/email_db.py`
5. Authored JSON in `Data/emails_inbox.json` and `Data/main_terminal_feed.json`

## Global Rules

- `main.py:grant_token()` is the main side-effect hub.
- New tokens trigger save, feed refresh, and `_handle_token_acquired(code)`.
- Inbox emails only auto-send when the player already has `PSEM`.
- Many unlocks are read-driven: reading an email can award the next token.

## Grant Sources By System

### Main BBS (`main.py`)

- `PSEM`: granted after the player clears the unread welcome threads.
- `USERNAME_SET`: granted when onboarding mail body contains `username: ...`.
- `PIN_SET`: granted on PIN create, PIN verify, or profile restore.
- `JAX`: granted when reading Jax's `TARGETS ACQUIRED` Wall post.
- `JEWEL_VOICE1`: granted when reading Glyphis' school grades Wall post.
- `JAX1`: granted when sending Jax an email with subject `CRACKING ASSISTANCE`.
- `SCHOOL_HACK`: granted when replying positively to Rain's `A cry for help`.
- `RADIO_ACCESS`: granted when agreeing to become a relay node in an email to uncle-am.
- `JAX2`: granted when reading Jaxkando mail after the Jax path is active.
- `JAXGRADES`: granted when reading uncle-am's school grades email.
- `SCHOOL_HACK1`: granted when reading Rain's school plan email.
- `GAMES1`: granted through `self.email_token_rewards` when `glyphis_username_ack_001` is read.
- `AUDIO1` and `LAPC1`: granted through `self.email_token_rewards` when `uncle_am_audio_ops_001` is read.
- `LAPC1_NODE*` and `LAPC1A`: granted from `pending_token_grants` emitted by the active urgent-ops session.

### Bradsonic OS (`Data/OS/OS_Mode.py`)

- `MODEM1ST`: granted when a modem connection succeeds through the OS modem flow.
- `SCHOOL_HACK2`: granted when region is switched to `American Mainland / US MAINLAND`.
- `SCHOOL_HACK3`: granted when BRADSONIC-MAIL sees the sent `I'm in` message and delivers Rain's reply.
- `SCHOOL_HACK4`: granted when the receptionist spoof email matches the required criteria.
- `SCHOOL_HACK4A`: granted when the receptionist reply is delivered.
- `SCHOOL_HACK4B`: granted when the `connected` update to Rain is sent and the login reply is delivered.

### Game And World Hooks

- `UNCLEAM1`: granted from `Data/games/registry.py` on SIMULACRA level 1 clear.
- `ASTROMINER1`: granted from `Data/games/registry.py` when Astro Miner exits for the first time.
- `JEWEL_VOICE`: granted from `Data/Outside_BBSs/PaperCraneBBS/Paper_Crane_BBS.py` when the song is played.
- `PAPERCRANEBBS`: granted from `Data/Pirate_Radio/PirateRadio.py` on first play of `Tokyo Yamoto Forever`.
- `ECHOCHAMBER`: granted from `Data/Pirate_Radio/PirateRadio.py` on first play of `Echo Chamber`.
- `RADIO_ACCESS1`: granted from `Data/Pirate_Radio/PirateRadio.py` when the tone-patching challenge completes.
- `PAPERCRANEBBS_IN`: granted when Paper Crane is dialed successfully.
- `NEVERAGAINBBS_IN`: granted when Never Again is dialed successfully.

## Reaction Sites

### Email Delivery

- `systems/email_db.py` auto-sends authored inbox mail when `auto_send` is true and `token_name` is present.
- Current important JSON token-driven mail includes `PSEM`, `USERNAME_SET`, `MODEM1ST`, `RADIO_ACCESS1`, `ASTROMINER1`, `ASTROMINER`, `PAPERCRANEBBS`, `SCHOOL_HACK1`, and `JAXGRADES`.
- `JEWEL_VOICE1` is special-cased in `main.py` to deliver Rain's school-help email rather than relying on inbox JSON alone.

### Feed / Menu / Unlocks

- `Data/main_terminal_feed.json` gates Wall posts with `required_tokens`, `forbidden_tokens`, and `exclusive_tokens`.
- `main.py` uses tokens to unlock modules:
  - `PSEM` -> email
  - `GAMES1` -> games
  - `AUDIO1` -> urgent ops
  - `TEAM_ACCESS` -> team info
  - `RADIO_ACCESS` -> pirate radio

### Bradsonic Notes / Desktop

- `Data/OS/OS_Mode.py` mission notes strike through or expand based on `RADIO_ACCESS1`, `PAPERCRANEBBS`, `ECHOCHAMBER`, `NEVERAGAINBBS`, `SCHOOL_HACK2`, `SCHOOL_HACK3`, and `SCHOOL_HACK4B`.
- The dotSONIC icon is visible only when locale allows it and `DOTSONIC` is present.
- The modem app and BRADSONIC-MAIL use tokens to decide when to pulse, prefill, or reveal follow-up school-hack steps.

### NPC Behavior

- `systems/enhanced_npc.py` uses token presence to shape topic awareness.
- It also uses `PARANOIA1` specifically for Glyphis paranoia behavior, which currently drifts from `tokens.py`.

## Debugging Checklist

- Confirm the token exists in `tokens.py`.
- Confirm the grant path is actually reachable in the current mission state.
- Check whether the content path expects a different token spelling.
- Check `Data/emails_inbox.json` or `Data/main_terminal_feed.json` for token gates.
- Check whether `PSEM` is missing; without it, token-gated inbox emails will not auto-deliver.
- For School Hack, verify both BBS-side and BRADSONIC-side tokens in order: `JEWEL_VOICE1 -> SCHOOL_HACK -> JAXGRADES/SCHOOL_HACK1 -> SCHOOL_HACK2 -> SCHOOL_HACK3 -> SCHOOL_HACK4 -> SCHOOL_HACK4A -> SCHOOL_HACK4B`.
