---
name: school-hack-master
description: Canon guide for the Tokyo Metro High school-hack arc in Glyphis_IO BBS The Proxy Tapes. Use when answering or implementing anything about the school operation, including SCHOOL_HACK tokens, Rain and board emails, Bradsonic terminal and region-switch steps, receptionist spoofing, modem/server access, ghost-note progression, and the Telebase school database viewer.
---

# School Hack Master

Use this skill for questions or implementation work tied to the school operation.

## Workflow

1. Read [references/progression-and-tokens.md](./references/progression-and-tokens.md) for the token ladder, note progression, gating, and mission structure.
2. Read [references/mail-terminal-and-modem.md](./references/mail-terminal-and-modem.md) for the LocaleProtocols credential chain, admin terminal flow, spoofed mail rules, phone-number flow, modem timing, and Rain reply logic.
3. Read [references/telebase-school-database.md](./references/telebase-school-database.md) for the Telebase viewer, named student overrides, record content, and the current standalone-to-OS embedding model.

## Working Rules

- Treat the files cited in the references as the canon sources when details conflict with older summaries.
- Prefer exact token names, email addresses, terminal commands, subjects, and node labels when answering.
- When asked how the school hack currently works in-game, include both progression logic and where that logic lives in code.
- When asked about the school database UI, treat [Data/Social_Engineering/School_Hack/school_database_standalone.py](C:/Dev Projects/Glyphis_IO BBS The Proxy Tapes/Data/Social_Engineering/School_Hack/school_database_standalone.py) as the active implementation and note that OS mode embeds it.
- If a request is only about one slice of the arc, load only the matching reference file instead of all three.

## Quick Pointers

- Token names to expect: `SCHOOL_HACK`, `JAXGRADES`, `SCHOOL_HACK1`, `SCHOOL_HACK2`, `SCHOOL_HACK3`, `SCHOOL_HACK4`, `SCHOOL_HACK4A`, `SCHOOL_HACK4B`.
- Core credentials and commands: `admin-subset`, `general`, `louis-sonic`, school database login `admin` / `password`.
- Core contacts: `rain@ciphernet.net`, `reception@tokyometro-high.edu.api`, plus the board aliases `jaxkando` and `uncle-am`.
- Key named students inside Telebase: Rosaline Cloud, Jason Kanderton, and Bertie Vandengate.
