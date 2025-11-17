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
    JAX1 = "JAX1"  # Volunteered to help Jaxkando with game cracking
    AUDIO_ON = "AUDIO_ON"  # Completed all 7 nodes, all LEDs green

    # Narrative/game unlocks (planned)
    OPS_ACCESS = "OPS_ACCESS"
    TEAM_ACCESS = "TEAM_ACCESS"
    RADIO_ACCESS = "RADIO_ACCESS"

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
    Tokens.JAX1: TokenMeta(
        code=Tokens.JAX1,
        label="JAX1",
        description="Volunteered to help Jaxkando crack games",
    ),
    Tokens.AUDIO_ON: TokenMeta(
        code=Tokens.AUDIO_ON,
        label="AUDIO_ON",
        description="Completed full LAPC-1 driver initialization (all nodes operational)",
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

