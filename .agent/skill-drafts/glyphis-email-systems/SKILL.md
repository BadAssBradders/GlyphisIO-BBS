---
name: glyphis-email-systems
description: "Understand, explain, debug, or modify the game's two mail systems: the main BBS email flow in `main.py`/`systems/email_db.py` and the BRADSONIC-MAIL client in `Data/OS/OS_Mode.py`. Use when a task involves inbox/outbox behavior, email delivery timing, token-gated messages, NPC email replies, School Hack mail progression, user-state persistence for either mail system, or the bridge between OS Mode mail and the main game profile."
---

# Glyphis Email Systems

Use this skill when the task touches either email surface or the token/story logic they drive.

## Workflow

1. Identify which system the user means.
   - BBS email: `main.py`, `systems/email_db.py`, `systems/enhanced_npc.py`, `Data/emails_inbox.json`, `Data/emails_outbox.json`
   - BRADSONIC-MAIL: `Data/OS/OS_Mode.py`
   - Persistence bridge: `main.py` user-state callbacks and save/load methods
2. Read only the relevant reference file first:
   - BBS flow: `references/bbs-email.md`
   - BRADSONIC flow: `references/bradsonic-mail.md`
3. Re-check source of truth before making claims:
   - Delivery and token grants in code, not only JSON or comments
   - Save/load structure in `main.py` if the task mentions persistence, duplication, deletion, or profile switching
4. If changing behavior, inspect all connected layers:
   - UI state
   - send/receive path
   - token side effects
   - persistence

## What To Check In Code

Use these search patterns:

```text
rg -n "check_email_database|deliver_email_to_player|EnhancedNPCResponder|player_email|inbox_emails|bradsonic_mail_inbox|mail_outbox|mail_trash|grant_token|SCHOOL_HACK|JAX1|RADIO_ACCESS" main.py systems/email_db.py systems/enhanced_npc.py Data/OS/OS_Mode.py
rg -n "_draw_mail_modal|_mail_handle_keydown|_handle_mail_modal_click|_start_mail_connect_sequence|_is_school_spoof_email|_deliver_rain_connected_reply" Data/OS/OS_Mode.py
```

## Guardrails

- Keep BBS email and BRADSONIC-MAIL conceptually separate. They share the active user profile but not the same inbox/outbox structures.
- Preserve token-driven story beats. Email changes often affect unlocks, pulses, modal availability, or delayed replies.
- When fixing duplication, check both runtime sets (`sent_email_ids`, `delivered_email_ids`) and saved inbox contents.
- When changing BRADSONIC-MAIL sends, verify both queued outbox behavior and connected `SEND/RX` behavior.

## References

- BBS system map: `references/bbs-email.md`
- BRADSONIC-MAIL map: `references/bradsonic-mail.md`
