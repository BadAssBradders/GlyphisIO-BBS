# Mail, Terminal, And Modem Flow

## Canon Sources

- `Data/OS/FILE-SYSTEM/SECURITY/LocaleProtocols.txt`
- `Data/OS/OS_Mode.py`
- `main.py`

## Locale Protocols Credential Chain

`LocaleProtocols.txt` exposes the period-separated Switch Region String:

- command: `admin-subset`
- username: `general`
- password: `louis-sonic`

This is the key bridge from the normal terminal into the admin menu that allows region switching.

## Region And Terminal Flow

1. Open Bradsonic desktop.
2. Go to `HDD > System > Terminal`.
3. Run `file-system-start`.
4. Open the locale protocols file and recover the Switch Region String values.
5. Reopen terminal and run `admin-subset`.
6. Log in with `general` and `louis-sonic`.
7. Choose the region change path and set `American Mainland`.
8. Do not factory reset.
9. Use BRADSONIC-MAIL after the region unlock.

## Rain Mail Sequence

After the player sends Rain a message to `rain@ciphernet.net` with subject containing `"I'm in"`:

- OS mail exchange injects Rain's reply.
- That reply grants `SCHOOL_HACK3`.
- Rain instructs the player to configure BRADSONIC-MAIL as a telecom engineer and spoof the school receptionist.

The spoof configuration is:

- Mail From Address: `region-support@telco-relay.bradsonic.net`
- Display Name: `TELCO RELAY ENGINEER`
- X-Signature Footer: `Regional Line Testing, BRADSONIC-TELCO RELAY.`

The spoof target is:

- `reception@tokyometro-high.edu.api`

The connected update target is:

- recipient: `rain@ciphernet.net`
- subject: `connected`

## Receptionist Spoof Rules

`OS_Mode.py` validates the spoofed mail against the expected sender identity and signature before granting `SCHOOL_HACK4`.

After that:

- the receptionist reply grants `SCHOOL_HACK4A`
- the player gets the school numbers
- the player dials outside school hours to find the modem line

## Modem And School Server Rules

Important school-server behavior in `OS_Mode.py`:

- school host identity: `tokyometro-high.edu.api`
- health monitor flips to `Network: Connected` when the school server modem succeeds
- school server access requires the modem target to be `school_server`
- if the node disconnects, the embedded Telebase terminal exits with `node disconnected`

Rain's post-connection database guidance is:

- open terminal
- run `admin-subset`
- choose `Handshake Connected Node`
- log into the school database with username `admin` and password `password`

## Search Patterns

- `admin-subset`
- `louis-sonic`
- `TELCO RELAY ENGINEER`
- `reception@tokyometro-high.edu.api`
- `connected`
- `_deliver_rain_connected_reply`
- `school_server`
