# BBS Email

## Scope

This is the main in-BBS email system, not the desktop BRADSONIC mail client.

Primary files:
- `main.py`
- `systems/email_db.py`
- `systems/enhanced_npc.py`
- `Data/emails_inbox.json`
- `Data/emails_outbox.json`

## Core Model

- Runtime inbox uses `Email` objects from `systems/email_db.py`.
- `EmailDatabase` loads template emails from JSON and decides what to auto-deliver.
- `main.py` owns compose, inbox, outbox, delayed replies, archive, user profile save/load, and token grants from player actions.

## Delivery Path

1. `main.py::check_email_database()` calls `EmailDatabase.check_and_send_emails(...)`.
2. `EmailDatabase` gates delivery on `PSEM` and optional `token_name`.
3. It avoids duplicate delivery using:
   - `sent_email_ids`
   - `delivered_email_ids`
   - current saved inbox contents passed in
4. `main.py` appends new emails to `self.inbox` and may play the mail sound.

## Player Sending Path

Compose/send lives in `main.py` around the BBS compose state.

Behavior split:
- `glyphis@ciphernet.net`: onboarding exceptions plus enhanced NPC replies when not in a scripted onboarding branch
- `jaxkando@ciphernet.net`, `rain@ciphernet.net`, `uncle-am@ciphernet.net`: enhanced NPC replies plus special-case token/story logic
- everyone else: queued to the BBS outbox only

Important special cases:
- `JAX` + subject `CRACKING ASSISTANCE` grants `JAX1`
- replying positively to Rain's school-help mail can grant `SCHOOL_HACK`
- certain uncle-am replies can grant `RADIO_ACCESS`
- many NPC replies are delayed via `self.delayed_emails`

## Persistence

Saved in the active user profile inside `user_state.json`:
- `inbox_emails`
- `sent_emails`
- `delivered_emails`
- `relationship_scores`

Load/save source of truth is `main.py`:
- `load_user_state()`
- `apply_active_user_profile()`
- `persist_active_user_profile()`
- `save_user_state()`

## Token Coupling

Common token-driven email beats:
- `PSEM`: unlocks core BBS email delivery
- `JAX`, `JAX1`
- `JEWEL_VOICE1`, `SCHOOL_HACK`, `SCHOOL_HACK1`

Always inspect actual token grant sites in `main.py`, not only `tokens.py`.
