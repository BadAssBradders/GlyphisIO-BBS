"""Systems package for GlyphisIO BBS.

Contains supporting systems like email database, NPC responder, token inventory, and Steam integration.
"""

from .email_db import Email, EmailDatabase
from .npc import NPCResponder
from .token_inventory import TokenInventory
from .steam_manager import SteamManager

__all__ = [
    "Email",
    "EmailDatabase",
    "NPCResponder",
    "TokenInventory",
    "SteamManager",
]

