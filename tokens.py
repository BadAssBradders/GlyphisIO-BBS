"""Token catalogue for GlyphisIO BBS.

Centralises metadata and normalisation for gameplay tokens so that unlocking
behaviour remains consistent across the application.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Optional


@dataclass(frozen=True)
class TokenMeta:
    code: str
    label: str
    description: str


class Tokens:
    """Canonical token codes used throughout the BBS."""

    PSEM = "PSEM"  # Email system enablement
    USERNAME_SET = "USERNAME_SET"  # Player has supplied their handle
    PIN_SET = "PIN_SET"  # Four digit PIN configured during login
    GAMES1 = "GAMES1"  # Games module unlocked
    AUDIO1 = "AUDIO1"  # Audio operations briefing acknowledged
    LAPC1_BRIEF = "LAPC1"  # CRACKER IDE driver briefing received
    LAPC1A = "LAPC1A"  # Node 1 power LED activated (first milestone)
    LAPC1_NODE1 = "LAPC1_NODE1"  # Node 1 power LED lit
    LAPC1_NODE2 = "LAPC1_NODE2"  # Node 2 left channel LED lit
    LAPC1_NODE3 = "LAPC1_NODE3"  # Node 3 right channel LED lit
    LAPC1_NODE4 = "LAPC1_NODE4"  # Node 4 both channels at default volume
    LAPC1_NODE5 = "LAPC1_NODE5"  # Node 5 stream entry reached
    LAPC1_NODE6 = "LAPC1_NODE6"  # Node 6 data check loop reached
    LAPC1_NODE7 = "LAPC1_NODE7"  # Node 7 output sample loop reached
    JAX = "JAX"  # Read the "Targets Acquired" post from The Wall
    JAX1 = "JAX1"  # Volunteered to help Jaxkando with game cracking
    JAX2 = "JAX2"  # Received cracking instructions from Jaxkando - unlocks challenge
    ASTROMINER = "ASTROMINER"
    ASTROMINER1 = "ASTROMINER1"  # Player has played AstroMiner game
    CYBERTRAIN = "CYBERTRAIN"
    PAPERCRANEBBS = "PAPERCRANEBBS"
    PAPERCRANEBBS_IN = "PAPERCRANEBBS_IN"  # Player has dialed into Paper Crane BBS
    NEVERAGAINBBS = "NEVERAGAINBBS"
    NEVERAGAINBBS_IN = "NEVERAGAINBBS_IN"  # Player has dialed into Never Again BBS
    JEWEL_VOICE = "JEWEL_VOICE"  # Played "Jewel Voice" on Paper Crane BBS
    JEWEL_VOICE1 = "JEWEL_VOICE1"  # Read Glyphis' school grades post on The Wall
    SCHOOL_HACK = "SCHOOL_HACK"  # Agreed to help Rain with school grades task
    JAXGRADES = "JAXGRADES"  # Read uncle-am's email about school grades (after SCHOOL_HACK)
    SCHOOL_HACK1 = "SCHOOL_HACK1"  # Read Rain's school op plan (region switch, email receptionist, etc.)
    SCHOOL_HACK2 = "SCHOOL_HACK2"  # Changed OS region to American Mainland / US Mainland (no BBS pulse, no logout ghost)
    SCHOOL_HACK3 = "SCHOOL_HACK3"  # Sent "I'm in" email via BRADSONIC-MAIL; Rain's next-steps reply received
    SCHOOL_HACK4 = "SCHOOL_HACK4"  # Composed and sent spoofed receptionist email with correct from/signature
    SCHOOL_HACK4A = "SCHOOL_HACK4A"  # Receptionist replied with the three school numbers
    SCHOOL_HACK4B = "SCHOOL_HACK4B"  # Sent "connected" update to Rain and received database login guidance
    SCHOOL_HACK5 = "SCHOOL_HACK5"  # All mission grades changed to A in school database
    SCHOOL_HACK_FAIL1 = "SCHOOL_HACK_FAIL1"  # First failed Telebase grade attempt; Rain allows a retry
    SCHOOL_HACK_FAIL2 = "SCHOOL_HACK_FAIL2"  # Second failed Telebase grade attempt; Glyphis issues a warning
    GAMEOVER_SCHOOLHACK = "GAMEOVER_SCHOOLHACK"  # Third failed Telebase grade attempt; school-hack arc hard-fails
    RAINSINVITE_1 = "RAINSINVITE_1"  # Accepted Rain's secret Fugamatchi gig invitation
    RAINSINVITE_2 = "RAINSINVITE_2"  # Played Rise New Voices in dotSONIC and primed the courier call
    RAINSINVITE_3 = "RAINSINVITE_3"  # Completed the payphone courier check and secured the ticket
    DOTSONIC = "DOTSONIC"  # dotSONIC media player unlocked
    AUDIO_ON = "AUDIO_ON"  # Completed all 7 nodes, all LEDs green
    MODEM1ST = "MODEM1ST"  # First successful modem connection established

    # Narrative/game unlocks (planned)
    OPS_ACCESS = "OPS_ACCESS"
    TEAM_ACCESS = "TEAM_ACCESS"
    RADIO_ACCESS = "RADIO_ACCESS"
    RADIO_ACCESS1 = "RADIO_ACCESS1"  # Completed pirate radio tone patching

    # Story arc tokens referenced by content JSON
    SUSPICION = "SUSPICION"
    PARANOIA = "PARANOIA"
    REVELATION = "REVELATION"
    PSEM_STAGE2 = "PSEM2"
    UNCLE_AM_1 = "UNCLEAM1"


TOKEN_METADATA: Dict[str, TokenMeta] = {
    Tokens.PSEM: TokenMeta(
        code=Tokens.PSEM,
        label="PSEM",
        description="Primary System Enablement Module - unlocks core communications",
    ),
    Tokens.USERNAME_SET: TokenMeta(
        code=Tokens.USERNAME_SET,
        label="USERNAME_SET",
        description="Player handle registered with Glyphis",
    ),
    Tokens.PIN_SET: TokenMeta(
        code=Tokens.PIN_SET,
        label="PIN_SET",
        description="Secure login PIN configured",
    ),
    Tokens.GAMES1: TokenMeta(
        code=Tokens.GAMES1,
        label="GAMES1",
        description="Primary games vault access",
    ),
    Tokens.AUDIO1: TokenMeta(
        code=Tokens.AUDIO1,
        label="AUDIO1",
        description="Granted access to urgent operations briefing channel",
    ),
    Tokens.LAPC1_BRIEF: TokenMeta(
        code=Tokens.LAPC1_BRIEF,
        label="LAPC1",
        description="Unlocked LAPC-1 driver challenge brief from Uncle-am",
    ),
    Tokens.OPS_ACCESS: TokenMeta(
        code=Tokens.OPS_ACCESS,
        label="OPS_ACCESS",
        description="Granted access to urgent operations module",
    ),
    Tokens.TEAM_ACCESS: TokenMeta(
        code=Tokens.TEAM_ACCESS,
        label="TEAM_ACCESS",
        description="Unlocked internal team dossier",
    ),
    Tokens.RADIO_ACCESS: TokenMeta(
        code=Tokens.RADIO_ACCESS,
        label="RADIO_ACCESS",
        description="Approved for pirate radio transmissions",
    ),
    Tokens.RADIO_ACCESS1: TokenMeta(
        code=Tokens.RADIO_ACCESS1,
        label="RADIO_ACCESS1",
        description="Completed pirate radio tone patching - full station access granted",
    ),
    Tokens.UNCLE_AM_1: TokenMeta(
        code=Tokens.UNCLE_AM_1,
        label="UNCLEAM1",
        description="Earned Uncle-am's trust via SIMULACRA core progress",
    ),
    Tokens.LAPC1A: TokenMeta(
        code=Tokens.LAPC1A,
        label="LAPC1A",
        description="Activated LAPC-1 power rail (Node 1 complete)",
    ),
    Tokens.LAPC1_NODE1: TokenMeta(
        code=Tokens.LAPC1_NODE1,
        label="LAPC1_NODE1",
        description="LAPC-1 Node 1 power LED lit",
    ),
    Tokens.LAPC1_NODE2: TokenMeta(
        code=Tokens.LAPC1_NODE2,
        label="LAPC1_NODE2",
        description="LAPC-1 Node 2 left channel LED lit",
    ),
    Tokens.LAPC1_NODE3: TokenMeta(
        code=Tokens.LAPC1_NODE3,
        label="LAPC1_NODE3",
        description="LAPC-1 Node 3 right channel LED lit",
    ),
    Tokens.LAPC1_NODE4: TokenMeta(
        code=Tokens.LAPC1_NODE4,
        label="LAPC1_NODE4",
        description="LAPC-1 Node 4 both channels at default volume",
    ),
    Tokens.LAPC1_NODE5: TokenMeta(
        code=Tokens.LAPC1_NODE5,
        label="LAPC1_NODE5",
        description="LAPC-1 Node 5 stream entry reached",
    ),
    Tokens.LAPC1_NODE6: TokenMeta(
        code=Tokens.LAPC1_NODE6,
        label="LAPC1_NODE6",
        description="LAPC-1 Node 6 data check loop reached",
    ),
    Tokens.LAPC1_NODE7: TokenMeta(
        code=Tokens.LAPC1_NODE7,
        label="LAPC1_NODE7",
        description="LAPC-1 Node 7 output sample loop reached",
    ),
    Tokens.JAX: TokenMeta(
        code=Tokens.JAX,
        label="JAX",
        description="Read the 'Targets Acquired' post from The Wall",
    ),
    Tokens.JAX1: TokenMeta(
        code=Tokens.JAX1,
        label="JAX1",
        description="Volunteered to help Jaxkando crack games",
    ),
    Tokens.JAX2: TokenMeta(
        code=Tokens.JAX2,
        label="JAX2",
        description="Received cracking instructions - ASTRO MINER challenge unlocked",
    ),
    Tokens.ASTROMINER: TokenMeta(
        code=Tokens.ASTROMINER,
        label="ASTROMINER",
        description="Access to the Astro Miner prototype",
    ),
    Tokens.ASTROMINER1: TokenMeta(
        code=Tokens.ASTROMINER1,
        label="ASTROMINER1",
        description="Player has played AstroMiner game",
    ),
    Tokens.CYBERTRAIN: TokenMeta(
        code=Tokens.CYBERTRAIN,
        label="CYBERTRAIN",
        description="Access to the CyberTrain railway builder prototype",
    ),
    Tokens.PAPERCRANEBBS: TokenMeta(
        code=Tokens.PAPERCRANEBBS,
        label="PAPERCRANEBBS",
        description="Access to the Paper Crane BBS dial-in frequency",
    ),
    Tokens.PAPERCRANEBBS_IN: TokenMeta(
        code=Tokens.PAPERCRANEBBS_IN,
        label="PAPERCRANEBBS_IN",
        description="Dialed into Paper Crane BBS",
    ),
    Tokens.NEVERAGAINBBS: TokenMeta(
        code=Tokens.NEVERAGAINBBS,
        label="NEVERAGAINBBS",
        description="Access to the Never Again BBS dial-in frequency",
    ),
    Tokens.NEVERAGAINBBS_IN: TokenMeta(
        code=Tokens.NEVERAGAINBBS_IN,
        label="NEVERAGAINBBS_IN",
        description="Dialed into Never Again BBS",
    ),
    Tokens.JEWEL_VOICE: TokenMeta(
        code=Tokens.JEWEL_VOICE,
        label="JEWEL_VOICE",
        description="Played Jewel Voice on Paper Crane BBS",
    ),
    Tokens.JEWEL_VOICE1: TokenMeta(
        code=Tokens.JEWEL_VOICE1,
        label="JEWEL_VOICE1",
        description="Read Glyphis' school grades post on The Wall",
    ),
    Tokens.SCHOOL_HACK: TokenMeta(
        code=Tokens.SCHOOL_HACK,
        label="SCHOOL_HACK",
        description="Agreed to help Rain with the school grades task",
    ),
    Tokens.JAXGRADES: TokenMeta(
        code=Tokens.JAXGRADES,
        label="JAXGRADES",
        description="Read uncle-am's email about school grades",
    ),
    Tokens.SCHOOL_HACK1: TokenMeta(
        code=Tokens.SCHOOL_HACK1,
        label="SCHOOL_HACK1",
        description="Read Rain's school op plan (region switch, email receptionist)",
    ),
    Tokens.SCHOOL_HACK2: TokenMeta(
        code=Tokens.SCHOOL_HACK2,
        label="SCHOOL_HACK2",
        description="Changed OS region to American Mainland / US Mainland",
    ),
    Tokens.SCHOOL_HACK3: TokenMeta(
        code=Tokens.SCHOOL_HACK3,
        label="SCHOOL_HACK3",
        description="Sent I'm in email via BRADSONIC-MAIL; Rain's next-steps reply received",
    ),
    Tokens.SCHOOL_HACK4: TokenMeta(
        code=Tokens.SCHOOL_HACK4,
        label="SCHOOL_HACK4",
        description="Composed and sent spoofed receptionist email with correct from/signature",
    ),
    Tokens.SCHOOL_HACK4A: TokenMeta(
        code=Tokens.SCHOOL_HACK4A,
        label="SCHOOL_HACK4A",
        description="Receptionist replied with the school's reception, fax, and server numbers",
    ),
    Tokens.SCHOOL_HACK4B: TokenMeta(
        code=Tokens.SCHOOL_HACK4B,
        label="SCHOOL_HACK4B",
        description="Reported the connection to Rain and received school database login instructions",
    ),
    Tokens.SCHOOL_HACK5: TokenMeta(
        code=Tokens.SCHOOL_HACK5,
        label="SCHOOL_HACK5",
        description="Successfully changed all required school grades to A",
    ),
    Tokens.SCHOOL_HACK_FAIL1: TokenMeta(
        code=Tokens.SCHOOL_HACK_FAIL1,
        label="SCHOOL_HACK_FAIL1",
        description="First failed school-hack Telebase attempt; Rain noticed and offered another try",
    ),
    Tokens.SCHOOL_HACK_FAIL2: TokenMeta(
        code=Tokens.SCHOOL_HACK_FAIL2,
        label="SCHOOL_HACK_FAIL2",
        description="Second failed school-hack Telebase attempt; Glyphis warned the player to stop being a liability",
    ),
    Tokens.GAMEOVER_SCHOOLHACK: TokenMeta(
        code=Tokens.GAMEOVER_SCHOOLHACK,
        label="GAMEOVER_SCHOOLHACK",
        description="Third failed school-hack Telebase attempt; Glyphis cut the player off from the network",
    ),
    Tokens.RAINSINVITE_1: TokenMeta(
        code=Tokens.RAINSINVITE_1,
        label="RAINSINVITE_1",
        description="Accepted Rain's invitation to the secret Fugamatchi gig",
    ),
    Tokens.RAINSINVITE_2: TokenMeta(
        code=Tokens.RAINSINVITE_2,
        label="RAINSINVITE_2",
        description="Played Rise New Voices on dotSONIC and decoded the courier call setup",
    ),
    Tokens.RAINSINVITE_3: TokenMeta(
        code=Tokens.RAINSINVITE_3,
        label="RAINSINVITE_3",
        description="Passed the payphone courier check and secured the underground gig ticket",
    ),
    Tokens.DOTSONIC: TokenMeta(
        code=Tokens.DOTSONIC,
        label="DOTSONIC",
        description="dotSONIC media player access granted",
    ),
    Tokens.AUDIO_ON: TokenMeta(
        code=Tokens.AUDIO_ON,
        label="AUDIO_ON",
        description="Completed full LAPC-1 driver initialization (all nodes operational)",
    ),
    Tokens.MODEM1ST: TokenMeta(
        code=Tokens.MODEM1ST,
        label="MODEM1ST",
        description="First successful modem connection to GLYPHIS_IO BBS established",
    ),
}


def normalize_token(token: Optional[str]) -> Optional[str]:
    """Return a canonical uppercase token string or ``None`` for empty input."""

    if not token:
        return None
    token = str(token).strip()
    if not token:
        return None
    return token.upper()


def describe_token(token: str, *, fallback: bool = True) -> str:
    """Return a friendly label for a token code."""

    code = normalize_token(token)
    if not code:
        return "Unknown token"
    meta = TOKEN_METADATA.get(code)
    if meta:
        return meta.label
    return code if fallback else "Unknown token"


def sort_tokens(tokens: Iterable[str]) -> Iterable[str]:
    """Return tokens sorted with known tokens first (stable order)."""

    normalised = [normalize_token(tok) for tok in tokens if normalize_token(tok)]

    def sort_key(token: str) -> tuple[int, str]:
        return (0 if token in TOKEN_METADATA else 1, token)

    return sorted(set(normalised), key=sort_key)

