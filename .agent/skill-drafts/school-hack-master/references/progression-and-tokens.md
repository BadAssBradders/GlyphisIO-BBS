# School Hack Progression And Tokens

## Canon Sources

- `tokens.py`
- `main.py`
- `Data/emails_inbox.json`
- `Data/OS/OS_Mode.py`

## Token Ladder

- `SCHOOL_HACK`: player agrees to help Rain with the school grades task.
- `JAXGRADES`: player reads uncle-am's grades email.
- `SCHOOL_HACK1`: player reads Rain's school-op plan email.
- `SCHOOL_HACK2`: player changes OS region to American Mainland / US Mainland.
- `SCHOOL_HACK3`: player sends the `"I'm in"` mail and receives Rain's next-steps reply.
- `SCHOOL_HACK4`: player sends the receptionist spoof mail with the correct sender identity and signature.
- `SCHOOL_HACK4A`: receptionist replies with the school's reception, fax, and server numbers.
- `SCHOOL_HACK4B`: player sends Rain the `connected` update and receives school database login instructions.

## Key Progression Beats

- The arc begins after the player agrees to help Rain and then reads the school-op plan mail.
- Rain's plan explicitly pushes the player out of the BBS and onto the Bradsonic desktop.
- Logging out with `SCHOOL_HACK1` active triggers the school-hack ghost-note sequence that writes a mission checklist into Notes.
- Reading `LocaleProtocols.txt` upgrades the note from placeholder `???` values to the real `admin-subset / general / louis-sonic` credentials.
- Switching region to American Mainland unlocks BRADSONIC-MAIL and grants `SCHOOL_HACK2`.
- Sending Rain the `"I'm in"` message grants `SCHOOL_HACK3` and injects Rain's next-steps reply into inbox.
- Sending the spoofed receptionist message grants `SCHOOL_HACK4`; the reply mail then grants `SCHOOL_HACK4A`.
- Sending Rain the `connected` message grants `SCHOOL_HACK4B` and delivers the school database login instructions.

## Named Grade Targets

- Rain asks for grade changes for herself.
- Uncle AM asks for Bertie Vandengate's English and History to become A grades.
- Jaxkando asks for Jason Kanderton's English and History to become A grades.

## Notes Behavior

`OS_Mode.py` maintains multiple note variants:

- `SCHOOL_HACK_NOTE_LINES_NO_CREDS`: early mission checklist with unknown credentials.
- `SCHOOL_HACK_NOTE_LINES_WITH_CREDS`: same list, but filled with `admin-subset`, `general`, and `louis-sonic`.
- `SCHOOL_HACK_NOTE_LINES_CONDENSED_HACK3`: condensed post-`I'm in` progress note.
- `SCHOOL_HACK_NOTE_LINES_CONDENSED_HACK4B`: condensed post-`connected` progress note.
- `SCHOOL_HACK3_NOTE_LINES`: Rain's receptionist-spoof instructions.
- `SCHOOL_HACK4B_NOTE_LINES`: Rain's school database login guess and final breach instructions.

## Email IDs Worth Knowing

In `Data/emails_inbox.json`, the important school-hack mails include:

- `rain_school_plan_001`
- `uncle_am_school_grades_001`
- `jaxkando_school_grades_001`

## Search Patterns

- `rain_school_plan_001`
- `uncle_am_school_grades_001`
- `jaxkando_school_grades_001`
- `SCHOOL_HACK1`
- `SCHOOL_HACK4B`
