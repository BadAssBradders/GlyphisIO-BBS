# Token Catalog

## Canonical Source

- Primary file: `tokens.py`
- Grant side effect: `main.py` `grant_token()` saves state, refreshes feed, and runs token-acquired handlers.
- Treat `Data/user_state.json` as persistence, not the source of truth.

## Onboarding And Core Access

- `PSEM`: email system unlocked after all welcome threads are read.
- `USERNAME_SET`: player sent `username: ...` during onboarding email flow.
- `PIN_SET`: player created, verified, or restored a four-digit PIN.
- `GAMES1`: games module unlocked by reading Glyphis' onboarding acknowledgment email.
- `AUDIO1`: urgent ops unlocked by reading uncle-am's audio ops email.
- `LAPC1`: briefing token for the LAPC-1 challenge, granted with `AUDIO1`.

## LAPC-1 / Audio Ops Arc

- `LAPC1A`: first milestone in the LAPC-1 challenge; also gates Jax's Wall post.
- `LAPC1_NODE1` to `LAPC1_NODE7`: per-node completion markers from the urgent-ops challenge session.
- `AUDIO_ON`: full LAPC-1 initialization complete; used by game and audio unlock logic.
- `MODEM1ST`: first successful modem connection from the Bradsonic OS.

## Jax / Astro Miner Arc

- `JAX`: read the `TARGETS ACQUIRED` post on The Wall.
- `JAX1`: sent `CRACKING ASSISTANCE` to Jaxkando.
- `JAX2`: read Jaxkando's cracking offer email; challenge fully unlocked.
- `ASTROMINER`: Astro Miner prototype/game access granted after the crack path.
- `ASTROMINER1`: first time the player exits Astro Miner after launch.
- `CYBERTRAIN`: defined as a gate for CyberTrain, but no clear in-repo grant site was found in current code.
- `UNCLEAM1`: granted on level 1 clear in SIMULACRA core session.

## Radio / External Worlds

- `RADIO_ACCESS`: agreed to join uncle-am's relay network by email.
- `RADIO_ACCESS1`: completed Pirate Radio tone patching.
- `PAPERCRANEBBS`: first play of `Tokyo Yamoto Forever` in Pirate Radio unlocks the Paper Crane route.
- `PAPERCRANEBBS_IN`: dialed into Paper Crane BBS.
- `JEWEL_VOICE`: played `Jewel Voice` inside Paper Crane BBS.
- `NEVERAGAINBBS`: defined and consumed by OS notes, but no clear grant site was found in current code.
- `NEVERAGAINBBS_IN`: dialed into Never Again BBS.
- `DOTSONIC`: used as a Bradsonic desktop icon gate; no clear grant site was found in current code.

## School Hack Arc

- `JEWEL_VOICE1`: read Glyphis' school grades post on The Wall.
- `SCHOOL_HACK`: agreed to help Rain in reply to `A cry for help`.
- `JAXGRADES`: read uncle-am's school grades request email.
- `SCHOOL_HACK1`: read Rain's school op plan email.
- `SCHOOL_HACK2`: changed Bradsonic region to `American Mainland / US MAINLAND`.
- `SCHOOL_HACK3`: sent `I'm in` through BRADSONIC-MAIL and received Rain's reply.
- `SCHOOL_HACK4`: sent the correctly spoofed receptionist email.
- `SCHOOL_HACK4A`: received the receptionist reply with school numbers.
- `SCHOOL_HACK4B`: sent `connected` to Rain and received database login guidance.

## Planned / Drifted / Partial

- `OPS_ACCESS`, `TEAM_ACCESS`: defined as unlock concepts; little or no active grant logic in current code.
- `SUSPICION`, `PARANOIA`, `REVELATION`, `PSEM2`: defined/planned story arc tokens, but current authored content often references different names or future flow.
- `PARANOIA1`: not canonical in `tokens.py`, but used in `Data/emails_inbox.json`, `systems/enhanced_npc.py`, and tests.
- `ECHOCHAMBER`: not canonical in `tokens.py`, but awarded in `Data/Pirate_Radio/PirateRadio.py` and consumed in `Data/OS/OS_Mode.py`.
