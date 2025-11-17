# Email Database System

## Overview

The email system uses JSON files to manage emails sent to and from the player. Emails can be triggered automatically based on tokens the player has acquired.

## File Structure

### `emails_inbox.json`
Contains emails that are sent TO the player (inbox emails).

### `emails_outbox.json`
Contains email templates that the player can send (outbox templates).

### `sent_emails.json`
Automatically generated file that tracks which emails have already been sent (prevents duplicates).

## Email Fields (Inbox)

- **id**: Unique identifier for the email
- **sender**: Email address of the sender
- **subject**: Email subject line
- **bodylines**: Integer count of populated body line slots
- **body1..bodyN**: Individual body lines, including blank lines represented as empty strings; unused slots can be omitted or set to `null`
- **timestamp**: When the email was sent (`null` = use current in-game time, `"realtime"` = evaluate at runtime)
- **token_required**: "yes" or "no" - whether a token is needed to trigger this email
- **token_name**: Name of the token required (if token_required is "yes")
- **auto_send**: true/false - whether to automatically send when conditions are met
- **send_on_start**: true/false - whether to send immediately when game starts
- **placeholders**: Subjects and body lines can include `{username}` which will be replaced with the player's saved handle

## Email Fields (Outbox Templates)

- **id**: Unique identifier for the template
- **recipient**: Email address to send to
- **subject**: Email subject line
- **body_template**: Email body template (can use {variables})
- **token_required**: "yes" or "no" - whether player needs a token to send this
- **token_name**: Name of the token required (if token_required is "yes")
- **auto_send**: Currently not used for outbox templates

## How It Works

1. **On Game Start**: Emails with `send_on_start: true` are automatically added to the inbox.

2. **Token-Based Triggering**: When a player acquires a token, the system checks all emails with:
   - `auto_send: true`
   - `token_required: "yes"`
   - `token_name` matching the acquired token
   
   If conditions are met, the email is automatically sent to the player's inbox.

3. **Periodic Checks**: The system checks for new emails every second (60 frames at 60fps).

4. **Persistence**: Sent email IDs are saved to `sent_emails.json` to prevent duplicates across game sessions.

## Example Email Entry

```json
{
  "id": "rain_intro_001",
  "bodylines": 11,
  "sender": "rain@ciphernet.net",
  "subject": "Hey, welcome aboard",
  "body1": "Hey there!",
  "body2": "",
  "body3": "Rain here, the taskmaster. I handle all the ops and missions around here. Glyphis mentioned you're new, so I wanted to reach out.",
  "body4": "",
  "body5": "If you're looking for work, I've got plenty of tasks that need doing. Some are simple data recovery jobs, others... well, let's just say they're more interesting.",
  "body6": "",
  "body7": "Check out the Urgent Ops module when you're ready. I'll be posting missions there regularly.",
  "body8": "",
  "body9": "Welcome to the team.",
  "body10": "",
  "body11": "-rain",
  "timestamp": null,
  "token_required": "yes",
  "token_name": "psem2",
  "auto_send": true,
  "send_on_start": false
}
```

This email will be automatically sent when the player acquires the "PSEM" token.

## Current Tokens

- **PSEM**: Granted after reviewing all Main Terminal Feed welcome threads (unlocks the Email System)
- **USERNAME_SET**: Granted when the player replies with `username: foo`; unlocks the follow-up onboarding message
- **PIN_SET**: Granted when the player creates or verifies their four-digit PIN during login (used to unlock game prototypes)
- **OPS_ACCESS** *(planned)*: Will unlock Urgent Ops later in the narrative
- **TEAM_ACCESS** *(planned)*: Will unlock Team Info later in the narrative
- **RADIO_ACCESS** *(planned)*: Will unlock Pirate Radio later in the narrative
- **SUSPICION**: For Act 4 - when glyphis suspects an infiltrator
- **PARANOIA**: For Act 4 - when tension rises
- **REVELATION**: For Act 5 - when the player's true identity is revealed

## Adding New Emails

1. Open `emails_inbox.json`
2. Add a new email object to the "emails" array
3. Set body content by:
   - Counting the intended line slots (including blank lines) and storing the value in `bodylines`
   - Populating sequential `body1`, `body2`, ... entries; use empty strings for deliberate blank lines and `null` for unused trailing slots if you want to keep a fixed layout
4. Set token requirements if needed
5. The system will automatically handle sending when conditions are met

## Notes

- Email IDs must be unique
- Tokens are case-insensitive (stored as uppercase) and may include underscores
- The system prevents duplicate emails from being sent
- Timestamps can be null to use current time
- When migrating older content that uses a single `body` string, the loader will still work, but new emails should use the structured `bodylines` format
- `body1..bodyN` slots are read sequentially until `bodylines` has been satisfied or entries stop appearing
- `{username}` will be substituted with the current player handle during email creation

