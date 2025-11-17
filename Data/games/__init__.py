"""Game registry package for GlyphisIO BBS.

This package contains lightweight adapters that allow standalone prototype
games to plug into the BBS runtime with minimal coupling. Each adapter
implements a consistent session interface so games can be launched or
removed just by editing the manifest in :mod:`games.registry`.
"""

from .registry import GAME_DEFINITIONS, GameDefinition, BaseGameSession

__all__ = ["GAME_DEFINITIONS", "GameDefinition", "BaseGameSession"]

