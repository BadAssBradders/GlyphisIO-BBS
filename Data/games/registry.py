"""Centralised game registry and adapters for GlyphisIOBBS.

Each entry in :data:`GAME_DEFINITIONS` describes a prototype game that can be
launched from the BBS "GAMES" module.  Embedded games expose a lightweight
session object so the main loop can delegate rendering and input while keeping
cleanup contained.  External prototypes (that expect to own the pygame window)
can be launched as a separate process, making them simple to add or remove.
"""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Callable, List, Optional, TYPE_CHECKING

import pygame

from tokens import Tokens

try:
    from .SIMULACRA_CORE import SimulacraCoreGame
except ImportError:
    from SIMULACRA_CORE import SimulacraCoreGame

if TYPE_CHECKING:  # pragma: no cover - only for type checkers
    from main import GlyphisIOBBS  # Local project import (avoids circular at runtime)


# ---------------------------------------------------------------------------
# Base session infrastructure
# ---------------------------------------------------------------------------


class BaseGameSession:
    """Common interface for embedded game sessions."""

    def __init__(self, app: "GlyphisIOBBS"):
        self.app = app
        self.exit_requested = False

    def enter(self) -> None:
        """Called immediately after the session becomes active."""

    def handle_event(self, event: pygame.event.Event) -> Optional[str]:
        """Forward pygame events to the session.

        Return ``"exit"`` to request closing the session.
        """

    def update(self, dt: float) -> None:
        """Advance simulation using the frame delta time in seconds."""

    def draw(self) -> None:
        """Render the game to ``app.bbs_surface`` (and optionally ``app.screen``)."""

    def should_exit(self) -> bool:
        """Utility so callers can poll for completion."""

        return self.exit_requested

    def exit(self) -> None:
        """Cleanup hook when leaving the session."""


# ---------------------------------------------------------------------------
# SIMULACRA_CORE adapter (embedded pygame experience)
# ---------------------------------------------------------------------------


class SimulacraSession(BaseGameSession):
    def __init__(self, app: "GlyphisIOBBS"):
        super().__init__(app)
        self.game: Optional[SimulacraCoreGame] = None

    def enter(self) -> None:
        fonts = {
            "large": self.app.font_large,
            "medium": self.app.font_medium,
            "small": self.app.font_small,
            "tiny": self.app.font_tiny,
        }
        player = self.app.player_email if getattr(self.app, "player_email", None) else "operative"
        best_tcs = self.app.get_active_user_simulacra_tcs()
        self.game = SimulacraCoreGame(
            self.app.bbs_surface,
            fonts,
            self.app.scale,
            player,
            best_tcs=best_tcs,
            on_new_best=self._on_new_best_tcs,
            on_level_cleared=self._on_level_cleared
        )

    def handle_event(self, event: pygame.event.Event) -> Optional[str]:
        if not self.game:
            return None
        if event.type == pygame.KEYDOWN:
            action = self.game.handle_event(event)
            if action == "EXIT":
                self.exit_requested = True
                return "exit"
        return None

    def draw(self) -> None:
        if self.game:
            score = self.game.take_pending_score()
            if score:
                result = self.app.record_simulacra_score(score["tcs"])
                self.game.handle_score_persisted(result, score)
            self.game.draw()

    def exit(self) -> None:
        self.game = None

    def _on_new_best_tcs(self, tcs_value: float) -> None:
        if not self.app:
            return
        placeholders = {"tcs": f"{tcs_value:.2f}"}
        self.app.deliver_email_to_player("glyphis_simulacra_congrats_001", placeholders=placeholders)

    def _on_level_cleared(self, level_number: int) -> None:
        if not self.app:
            return
        if level_number == 1:
            self.app.grant_token(Tokens.UNCLE_AM_1, reason="breached SIMULACRA core array 01")


# ---------------------------------------------------------------------------
# Data definitions
# ---------------------------------------------------------------------------


@dataclass
class GameDefinition:
    id: str
    title: str
    description: str
    tokens_required: List[str] = field(default_factory=list)
    type: str = "session"  # "session" or "external"
    session_factory: Optional[Callable[["GlyphisIOBBS"], BaseGameSession]] = None
    external_path: Optional[str] = None


def _resolve(path: str) -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, path))


GAME_DEFINITIONS: List[GameDefinition] = [
    GameDefinition(
        id="simulacra_core",
        title="SIMULACRA_CORE",
        description="Glyphis' payload simulator: edit code, outsmart the warden, deliver the packet.",
        tokens_required=[Tokens.GAMES1],
        session_factory=SimulacraSession,
    ),
]


# ---------------------------------------------------------------------------
# Helper for external launcher (used by main application)
# ---------------------------------------------------------------------------


def launch_external_game(defn: GameDefinition) -> int:
    """Launch an external prototype in a subprocess.

    Returns the subprocess return code. Raises ``RuntimeError`` if the
    definition does not refer to an external title.
    """

    if defn.type != "external" or not defn.external_path:
        raise RuntimeError("Game definition is not external")

    cmd = [sys.executable, defn.external_path]
    try:
        completed = subprocess.run(cmd, check=False)
        return completed.returncode
    except FileNotFoundError as exc:  # pragma: no cover - depends on filesystem
        raise RuntimeError(f"Unable to launch external game: {exc}") from exc

