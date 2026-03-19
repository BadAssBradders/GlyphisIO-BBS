# BRADSONIC-MAIL

## Scope

This is the desktop mail client inside OS Mode, implemented entirely in `Data/OS/OS_Mode.py`.

It is separate from the BBS inbox UI, but it persists through the active user profile owned by `main.py`.

## Data Ownership

`main.py` passes callbacks into `OSMode` for:
- `get_inbox_emails` / `save_inbox_emails`
- `get_mail_outbox` / `save_mail_outbox`
- `get_mail_trash` / `save_mail_trash`
- `send_mail`
- `grant_token`
- `open_email`

Saved profile keys:
- `bradsonic_mail_inbox`
- `mail_outbox`
- `mail_trash`

## UI / State Machine

Main state fields in `OS_Mode.py`:
- `mail_view`
- `mail_local_inbox`
- `mail_compose_to`
- `mail_compose_subject`
- `mail_compose_body`
- `mail_settings`
- `mail_server_connected`
- connect-terminal fields such as `mail_connect_terminal_lines`

Main UI handlers:
- `_draw_mail_modal()`
- `_handle_mail_modal_click()`
- `_mail_handle_keydown()`
- `_mail_handle_textinput()`

## Send / Receive Model

- Compose does not immediately hit a network API.
- Outgoing messages are queued into `mail_outbox`.
- Delivery happens when the player uses `CONNECT` / `DIAL` / `SEND-RX`.
- `_start_mail_connect_sequence()` simulates a modem session, flushes outbox, and conditionally inserts reply mail into `mail_local_inbox`.
- `_mail_do_send_rx()` does the same fast-path when already connected.

`send_mail_callback()` from `main.py` is currently just a hook/logger. Story progression is mostly driven inside `OS_Mode.py`.

## School Hack Mail Arc

Key tokens:
- `SCHOOL_HACK2`: American Mainland region set; mail icon available
- `SCHOOL_HACK3`: sent "I'm in" mail to Rain, reply delivered
- `SCHOOL_HACK4`: sent valid spoofed receptionist email
- `SCHOOL_HACK4A`: receptionist reply with school numbers delivered
- `SCHOOL_HACK4B`: sent `connected` mail to Rain and received database-login reply

Key functions:
- `_is_school_spoof_email()`
- `_is_rain_connected_email()`
- `_build_receptionist_reply()`
- `_deliver_rain_connected_reply()`

The compose placeholders and pulsing UI are story-guidance tools. If you change those, verify the School Hack objective flow still makes sense.

## Persistence / Bridge Notes

- Opening the desktop mail client copies saved inbox data into `mail_local_inbox`.
- Saving inbox/outbox/trash writes directly into the active user profile and calls `save_user_state()`.
- Closing mail or opening modem can drop the mail server connection state.

If a bug mentions “email disappeared,” “duplicated,” “reply never arrived,” or “token didn’t fire,” check both `OS_Mode.py` state transitions and the callback-backed saved lists in `main.py`.
