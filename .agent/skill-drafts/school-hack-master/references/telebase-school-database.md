# Telebase School Database

## Canon Sources

- `Data/Social_Engineering/School_Hack/school_database_standalone.py`
- `Data/Social_Engineering/School_Hack/school_database_state.json`
- `Data/OS/OS_Mode.py`

## Active Runtime Model

The standalone school database file is the active implementation.

- `OS_Mode.py` imports `SchoolDatabaseApp` from `Data/Social_Engineering/School_Hack/school_database_standalone.py`
- the in-game terminal embeds that app rather than maintaining a separate live school-database implementation

When asked whether OS mode uses the standalone implementation, the correct answer is yes.

## Telebase Sections

Current sections in the viewer:

- `ATTENDANCE SCORES`
- `REPORT CARDS`
- `DISCIPLINARY RECORDS`
- `COUNSELOR NOTES`
- `SATURDAY CLUBS`

## Named Character Overrides

Three mug filenames map to explicit school-hack characters:

- `1m_BRADSONIC_mosaic_reveal.gif` -> Bertie Vandengate
- `2m_BRADSONIC_mosaic_reveal.gif` -> Jason Kanderton
- `1f_BRADSONIC_mosaic_reveal.gif` -> Rosaline Cloud

These students get bespoke:

- names
- grade patterns
- club memberships
- disciplinary incidents
- counselor notes

## School Database Login

The Telebase school login uses:

- username: `admin`
- password: `password`

## Saturday Clubs Canon

Generic pool:

- Computer Club
- Amateur Radio Club
- Chess Club
- Art Club
- Drama Society
- Science Olympiad
- Music Club
- Photography Club
- Peace Committee
- Library Volunteers

Named overrides:

- Bertie: Computer Club, Amateur Radio Club
- Jason: Computer Club, Chess Club
- Rosaline: Computer Club, Drama Society

## Disciplinary And Counselor Narrative

Named students have explicit narrative records, including:

- modem misuse and server-room incidents for Bertie
- unauthorized software and anti-Pacifica material for Jason
- terminal bypasses and coordination suspicion for Rosaline

Counselor notes include `[FLAGGED]` entries that render in red in the viewer.

## UI And Navigation

The standalone app supports:

- left/right/tab: cycle students
- up/down: field movement or scroll, depending on the active screen
- escape: back out to the school home screen or leave the app entirely

The newer record screens reuse a common record-shell layout that draws:

- outer frame
- `RECORD ##/##`
- footer
- mugshot and left-side info
- right-side content panel

## Search Patterns

- `SATURDAY_CLUBS_OVERRIDES`
- `DISCIPLINARY_OVERRIDES`
- `COUNSELOR_OVERRIDES`
- `school_db_disciplinary`
- `school_db_counselor`
- `school_db_clubs`
- `Bertie Vandengate`
- `Jason Kanderton`
- `Rosaline Cloud`
