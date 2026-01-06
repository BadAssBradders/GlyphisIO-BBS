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
import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple, TYPE_CHECKING

import pygame

from tokens import Tokens

# Windows API imports for window capture
try:
    import ctypes
    from ctypes import wintypes
    WINDOWS_AVAILABLE = True
except ImportError:
    WINDOWS_AVAILABLE = False

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
        self.simcore_sound: Optional[pygame.mixer.Sound] = None
        self.simcore_channel: Optional[pygame.mixer.Channel] = None

    def enter(self) -> None:
        print("[SimulacraSession] Entering session...")
        fonts = {
            "large": self.app.font_large,
            "medium": self.app.font_medium,
            "small": self.app.font_small,
            "tiny": self.app.font_tiny,
        }
        print(f"[SimulacraSession] Fonts: {fonts.keys()}")
        print(f"[SimulacraSession] Scale: {self.app.scale}")
        
        player = self.app.player_email if getattr(self.app, "player_email", None) else "operative"
        best_tcs = self.app.get_active_user_simulacra_tcs()
        
        try:
            self.game = SimulacraCoreGame(
                self.app.bbs_surface,
                fonts,
                self.app.scale,
                player,
                best_tcs=best_tcs,
                on_new_best=self._on_new_best_tcs,
                on_level_cleared=self._on_level_cleared,
                get_radio_music_callback=self.app._get_radio_music_state
            )
            print("[SimulacraSession] Game instance created successfully.")
        except Exception as e:
            print(f"[SimulacraSession] ERROR creating game instance: {e}")
            import traceback
            traceback.print_exc()
        
        # Check for audio tokens and play simcore.wav if both are present
        if self.app.inventory.has_token(Tokens.AUDIO_ON) and self.app.inventory.has_token(Tokens.LAPC1_NODE7):
            try:
                if not pygame.mixer.get_init():
                    pygame.mixer.init()
                
                from utils import get_data_path
                simcore_path = get_data_path("Audio", "simcore.wav")
                
                if os.path.exists(simcore_path):
                    self.simcore_sound = pygame.mixer.Sound(simcore_path)
                    # Play at 80% volume (0.8) in a loop
                    self.simcore_channel = self.simcore_sound.play(loops=-1)
                    if self.simcore_channel:
                        self.simcore_channel.set_volume(0.8)
                        print("[SimulacraSession] Started simcore.wav at 80% volume")
                else:
                    print(f"[SimulacraSession] simcore.wav not found at {simcore_path}")
            except Exception as e:
                print(f"[SimulacraSession] Error loading simcore.wav: {e}")
                import traceback
                traceback.print_exc()

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
            # Sync surface if it changed (e.g. resize)
            if self.game.surface != self.app.bbs_surface:
                 print("[SimulacraSession] Syncing surface reference")
                 self.game.surface = self.app.bbs_surface
                 # Update dimensions if needed
                 self.game.width = self.app.bbs_surface.get_width()
                 self.game.height = self.app.bbs_surface.get_height()

            score = self.game.take_pending_score()
            if score:
                result = self.app.record_simulacra_score(score["tcs"])
                self.game.handle_score_persisted(result, score)
            
            # Debug: Check surface state before drawing
            if hasattr(self, '_debug_draw_count'):
                self._debug_draw_count += 1
            else:
                self._debug_draw_count = 0
            
            if self._debug_draw_count % 60 == 0:
                surf_size = self.game.surface.get_size()
                surf_alpha = self.game.surface.get_flags() & pygame.SRCALPHA
                print(f"[SimulacraSession] Drawing to surface: size={surf_size}, has_alpha={bool(surf_alpha)}, surface_id={id(self.game.surface)}, bbs_surface_id={id(self.app.bbs_surface)}")
            
            self.game.draw()
            
            # Debug: Sample a pixel after drawing to verify content
            if self._debug_draw_count % 60 == 0:
                try:
                    # Sample center pixel
                    center_x, center_y = surf_size[0] // 2, surf_size[1] // 2
                    pixel = self.game.surface.get_at((center_x, center_y))
                    print(f"[SimulacraSession] Center pixel after draw: {pixel}")
                except Exception as e:
                    print(f"[SimulacraSession] Error sampling pixel: {e}")

    def exit(self) -> None:
        # Stop simcore.wav if playing
        if self.simcore_channel:
            try:
                self.simcore_channel.stop()
                print("[SimulacraSession] Stopped simcore.wav")
            except Exception as e:
                print(f"[SimulacraSession] Error stopping simcore.wav: {e}")
            self.simcore_channel = None
        self.simcore_sound = None
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
# ASTRO MINER adapter (external C++ game with window capture)
# ---------------------------------------------------------------------------


class AstroMinerSession(BaseGameSession):
    """Session adapter for Astro Miner using headless framebuffer rendering."""
    
    # Mapping from pygame key codes to raylib key codes
    # Raylib key codes match ASCII/Unicode values for letters/numbers
    # Special keys are defined in raylib.h
    KEY_MAP = {
        # Arrow keys
        pygame.K_UP: 265,      # KEY_UP
        pygame.K_DOWN: 264,    # KEY_DOWN
        pygame.K_LEFT: 263,    # KEY_LEFT
        pygame.K_RIGHT: 262,   # KEY_RIGHT
        # Modifier keys
        pygame.K_SPACE: 32,    # KEY_SPACE
        pygame.K_RETURN: 257,  # KEY_ENTER
        pygame.K_ESCAPE: 256,  # KEY_ESCAPE
        # Letters (A-Z map to ASCII 65-90)
        pygame.K_a: 65, pygame.K_b: 66, pygame.K_c: 67, pygame.K_d: 68,
        pygame.K_e: 69, pygame.K_f: 70, pygame.K_g: 71, pygame.K_h: 72,
        pygame.K_i: 73, pygame.K_j: 74, pygame.K_k: 75, pygame.K_l: 76,
        pygame.K_m: 77, pygame.K_n: 78, pygame.K_o: 79, pygame.K_p: 80,
        pygame.K_q: 81, pygame.K_r: 82, pygame.K_s: 83, pygame.K_t: 84,
        pygame.K_u: 85, pygame.K_v: 86, pygame.K_w: 87, pygame.K_x: 88,
        pygame.K_y: 89, pygame.K_z: 90,
        # Numbers (0-9 map to ASCII 48-57)
        pygame.K_0: 48, pygame.K_1: 49, pygame.K_2: 50, pygame.K_3: 51,
        pygame.K_4: 52, pygame.K_5: 53, pygame.K_6: 54, pygame.K_7: 55,
        pygame.K_8: 56, pygame.K_9: 57,
    }
    
    # Mouse button mapping (raylib: 0=LEFT, 1=RIGHT, 2=MIDDLE)
    MOUSE_BUTTON_MAP = {
        1: 0,  # pygame MOUSEBUTTONDOWN/UP button 1 = LEFT
        3: 1,  # pygame MOUSEBUTTONDOWN/UP button 3 = RIGHT
        2: 2,  # pygame MOUSEBUTTONDOWN/UP button 2 = MIDDLE
    }
    
    def __init__(self, app: "GlyphisIOBBS"):
        super().__init__(app)
        self.embed_module = None
        self.last_frame: Optional[pygame.Surface] = None
        self.last_mouse_pos = (0, 0)
        # Desktop area position (where the game is rendered)
        self.baseline_desktop_x = 176
        self.baseline_desktop_y = 209
        # Leaderboard tracking
        self.last_uploaded_score = 0
        self.score_check_counter = 0
    
    def _get_desktop_pos(self) -> Tuple[int, int]:
        """Get the desktop area position in screen coordinates."""
        # Use centralized ResolutionManager to ensure alignment with OSMode
        return self.app.res_manager.coords(self.baseline_desktop_x, self.baseline_desktop_y)

    def _load_base_desktop_size(self) -> Tuple[int, int]:
        if getattr(self, "_base_desktop_size", None):
            return self._base_desktop_size
        desktop_path = os.path.join("Data", "OS", "Desktop-Enviroment.png")
        try:
            desktop_image = pygame.image.load(desktop_path)
            self._base_desktop_size = desktop_image.get_size()
        except Exception:
            self._base_desktop_size = (self.app.bbs_width, self.app.bbs_height)
        return self._base_desktop_size

    def _get_desktop_dimensions(self) -> Tuple[int, int]:
        width = height = None
        if hasattr(self.app, "os_mode") and self.app.os_mode and hasattr(self.app.os_mode, "desktop_size"):
            ds = self.app.os_mode.desktop_size
            if ds:
                try:
                    width = int(ds[0])
                    height = int(ds[1])
                except (TypeError, ValueError):
                    width = height = None
        if width is None or height is None:
            base_w, base_h = self._load_base_desktop_size()
            width = self.app.res_manager.scale(base_w)
            height = self.app.res_manager.scale(base_h)
        width = max(720, width)
        height = max(480, height)
        return (width, height)
    
    def _get_game_mouse_pos(self, screen_pos: Tuple[int, int]) -> Tuple[float, float]:
        """Convert screen mouse position to game-relative position."""
        desktop_x, desktop_y = self._get_desktop_pos()
        # Get game size
        desktop_w, desktop_h = self._get_desktop_dimensions()
        rel_x = screen_pos[0] - desktop_x
        rel_y = screen_pos[1] - desktop_y
        
        if self.embed_module:
            game_width, game_height = self.embed_module.get_size()
            if game_width > 0 and game_height > 0 and desktop_w > 0 and desktop_h > 0:
                game_x = (rel_x / desktop_w) * game_width
                game_y = (rel_y / desktop_h) * game_height
                return (
                    max(0.0, min(float(game_width), float(game_x))),
                    max(0.0, min(float(game_height), float(game_y)))
                )
        # Fallback: just subtract desktop offset
        return (float(rel_x), float(rel_y))
            
    def enter(self) -> None:
        """Initialize the embedded game DLL."""
        try:
            from . import astrominer_embed
            self.embed_module = astrominer_embed
            desired_mode = (getattr(self.app, "astro_render_mode", "auto") or "auto").strip().lower()
            resolution_applied = False
            if desired_mode in ("low", "medium", "high") and hasattr(astrominer_embed, "set_resolution_mode"):
                resolution_applied = astrominer_embed.set_resolution_mode(desired_mode)
            if not resolution_applied and hasattr(astrominer_embed, "set_render_resolution"):
                # Get desktop dimensions (where the game will be rendered)
                # This ensures the C++ render resolution matches the final display size
                # and maintains correct aspect ratio
                desktop_width, desktop_height = self._get_desktop_dimensions()
                print(f"[AstroMinerSession] Setting DLL resolution to match desktop: {desktop_width}x{desktop_height}")
                astrominer_embed.set_render_resolution(desktop_width, desktop_height)
            
            # Reset game to ensure fresh start when launching from BBS
            print("[AstroMinerSession] Resetting game to new game defaults...")
            astrominer_embed.reset_game()
            
            # Set current username from BBS before initializing (ALWAYS refresh from BBS)
            if hasattr(self.app, 'get_active_user'):
                active_user = self.app.get_active_user()
                if active_user and active_user.get('username'):
                    username = active_user.get('username')
                    print(f"[AstroMinerSession.enter] Setting username from BBS: {username}")
                    astrominer_embed.set_username(username)
                else:
                    print("[AstroMinerSession.enter] WARNING: No active user or username found!")
            
            if not astrominer_embed.initialize():
                print("Failed to initialize Astro Miner DLL")
                self.exit_requested = True
                return
            
            # Hide pygame cursor - game will handle its own cursor
            pygame.mouse.set_visible(False)
            print("[AstroMinerSession.enter] Cursor hidden, mouse input now controlled by game")
            
            # Grant ASTROMINER1 token when player enters the game
            if hasattr(self.app, 'grant_token'):
                from tokens import Tokens
                self.app.grant_token(Tokens.ASTROMINER1, reason="player entered AstroMiner game")
            
        except ImportError as e:
            print(f"Failed to import astrominer_embed: {e}")
            self.exit_requested = True
        except Exception as e:
            print(f"Failed to initialize Astro Miner: {e}")
            self.exit_requested = True
    
    def _find_game_window(self) -> None:
        """Find the game window by title."""
        if not WINDOWS_AVAILABLE:
            return
        
        windows_found = []
        
        def enum_windows_callback(hwnd, lParam):
            if self.user32.IsWindowVisible(hwnd):
                window_title = ctypes.create_unicode_buffer(512)
                self.user32.GetWindowTextW(hwnd, window_title, 512)
                title = window_title.value
                # Look for raylib window (Astro Miner uses raylib)
                if "Astro Miner" in title or "raylib" in title.lower() or title.strip() == "":
                    # Empty title might be the game window too
                    windows_found.append(hwnd)
            return True
        
        EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        self.user32.EnumWindows(EnumWindowsProc(enum_windows_callback), 0)
        
        if windows_found:
            # Try to find the one that matches best (prefer "Astro Miner" in title)
            for hwnd in windows_found:
                window_title = ctypes.create_unicode_buffer(512)
                self.user32.GetWindowTextW(hwnd, window_title, 512)
                if "Astro Miner" in window_title.value:
                    self.game_window_handle = hwnd
                    return
            # Fallback to first found
            if windows_found:
                self.game_window_handle = windows_found[0]
    
    def _log_window_position(self) -> None:
        """Log the current window position for debugging."""
        if not WINDOWS_AVAILABLE or not self.game_window_handle:
            return
        try:
            rect = wintypes.RECT()
            self.user32.GetWindowRect(self.game_window_handle, ctypes.byref(rect))
            print(f"Game window initial position: x={rect.left}, y={rect.top}, width={rect.right - rect.left}, height={rect.bottom - rect.top}")
        except Exception as e:
            print(f"Failed to get window position: {e}")
    
    def _hide_game_window(self) -> None:
        """Remove window frame, prevent focus stealing, and position at desktop location."""
        if not WINDOWS_AVAILABLE or not self.game_window_handle:
            return
        
        try:
            # Get pygame window handle to make game window a child
            pygame_hwnd = None
            try:
                # Try to get pygame window handle from display
                pygame_hwnd = pygame.display.get_wm_info()['window']
            except:
                pass
            
            # Try to make it a child window of pygame first (true embedding)
            if pygame_hwnd:
                try:
                    # Make it a child window - this embeds it within pygame
                    self.user32.SetParent(self.game_window_handle, pygame_hwnd)
                    print("Made game window a child of pygame window")
                except Exception as e:
                    print(f"SetParent failed (may not work with raylib): {e}")
            
            # Remove window frame completely
            new_style = self.WS_POPUP | self.WS_VISIBLE  # Keep visible if child window works
            self.user32.SetWindowLongW(self.game_window_handle, self.GWL_STYLE, new_style)
            
            # Set extended style to prevent focus stealing and hide from taskbar
            current_exstyle = self.user32.GetWindowLongW(self.game_window_handle, self.GWL_EXSTYLE)
            new_exstyle = (current_exstyle | self.WS_EX_TOOLWINDOW | self.WS_EX_NOACTIVATE) & ~self.WS_EX_TRANSPARENT
            self.user32.SetWindowLongW(self.game_window_handle, self.GWL_EXSTYLE, new_exstyle)
            
            # Position window at desktop location (exact same as OS_Mode.py uses)
            baseline_desktop_x = 176
            baseline_desktop_y = 209
            desktop_x = int(baseline_desktop_x * self.app.scale)
            desktop_y = int(baseline_desktop_y * self.app.scale)
            
            # SetWindowPos flags
            SWP_NOSIZE = 0x0001
            SWP_NOZORDER = 0x0004
            SWP_NOACTIVATE = 0x0010  # Critical: don't activate
            SWP_SHOWWINDOW = 0x0040  # Show it (if SetParent worked, it's embedded)
            SWP_FRAMECHANGED = 0x0020
            flags = SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_SHOWWINDOW | SWP_FRAMECHANGED
            
            # Position window so its top-left corner matches desktop environment position
            # If SetParent worked, coordinates are relative to pygame window
            # If not, they're screen coordinates
            self.user32.SetWindowPos(
                self.game_window_handle,
                0,
                desktop_x,
                desktop_y,
                0,
                0,
                flags
            )
            
            # Try to make it a child of pygame window if we have the handle
            if pygame_hwnd:
                try:
                    self.user32.SetParent(self.game_window_handle, pygame_hwnd)
                except:
                    pass
            
            # Ensure pygame window stays on top and focused
            try:
                if pygame_hwnd:
                    self.user32.SetForegroundWindow(pygame_hwnd)
                    self.user32.SetFocus(pygame_hwnd)
            except:
                pass
            
            print(f"Game window configured: position=({desktop_x}, {desktop_y}), frameless, no-focus")
        except Exception as e:
            print(f"Failed to configure game window: {e}")
    
    def handle_event(self, event: pygame.event.Event) -> Optional[str]:
        """Forward input events to the embedded game DLL."""
        if not self.embed_module:
            return None
        
        # ESC is now handled by the game itself (navigation, closing modals, etc.)
        # Only exit when the game signals it wants to exit via should_exit()
        # (which happens when user selects QUIT GAME from the menu)
        
        # Forward keyboard events
        if event.type == pygame.KEYDOWN:
            raylib_key = self.KEY_MAP.get(event.key)
            if raylib_key is not None:
                print(f"[AstroMinerSession.handle_event] KEYDOWN: pygame_key={event.key}, raylib_key={raylib_key}")
                self.embed_module.set_key_state(raylib_key, True)
        elif event.type == pygame.KEYUP:
            raylib_key = self.KEY_MAP.get(event.key)
            if raylib_key is not None:
                print(f"[AstroMinerSession.handle_event] KEYUP: pygame_key={event.key}, raylib_key={raylib_key}")
                self.embed_module.set_key_state(raylib_key, False)
        
        # Forward mouse button events
        if event.type == pygame.MOUSEBUTTONDOWN:
            raylib_button = self.MOUSE_BUTTON_MAP.get(event.button)
            if raylib_button is not None:
                self.embed_module.set_mouse_button_state(raylib_button, True)
                # Also update mouse position (relative to game area)
                game_pos = self._get_game_mouse_pos(event.pos)
                self.embed_module.set_mouse_position(game_pos[0], game_pos[1])
        elif event.type == pygame.MOUSEBUTTONUP:
            raylib_button = self.MOUSE_BUTTON_MAP.get(event.button)
            if raylib_button is not None:
                self.embed_module.set_mouse_button_state(raylib_button, False)
        
        # Forward mouse motion - CRITICAL: Use relative movement for ship control
        if event.type == pygame.MOUSEMOTION:
            # Use relative movement (event.rel) for delta - this gives true mouse movement
            # regardless of cursor position, which is what we need for ship control
            dx, dy = 0.0, 0.0
            if hasattr(event, 'rel') and event.rel:
                # event.rel is the relative movement since last event
                # This is what we want for ship rotation control
                dx = float(event.rel[0])
                dy = float(event.rel[1])
            else:
                # Fallback: calculate from position change
                game_pos = self._get_game_mouse_pos(event.pos)
                last_game_pos = self._get_game_mouse_pos(self.last_mouse_pos)
                dx = game_pos[0] - last_game_pos[0]
                dy = game_pos[1] - last_game_pos[1]
            
            if abs(dx) > 0.1 or abs(dy) > 0.1:
                print(f"[AstroMinerSession.handle_event] MOUSEMOTION dx=({dx:.2f},{dy:.2f})")
            
            # Set delta FIRST (this is what controls ship rotation)
            self.embed_module.set_mouse_delta(float(dx), float(dy))
            
            # Also update position for any position-based logic
            game_pos = self._get_game_mouse_pos(event.pos)
            self.embed_module.set_mouse_position(game_pos[0], game_pos[1])
            self.last_mouse_pos = event.pos
        
        return None
    
    def update(self, dt: float) -> None:
        """Update game frame from DLL framebuffer."""
        if not self.embed_module:
            print("[AstroMinerSession.update] ERROR: embed_module is None!")
            return
        
        # Get relative mouse movement (works even when cursor is hidden)
        # This is the key to getting mouse control working!
        rel_x, rel_y = pygame.mouse.get_rel()
        
        static_update_count = getattr(self, '_update_count', 0)
        self._update_count = static_update_count + 1
        
        # Check if mouse should be centered (for 3D lander environment)
        if hasattr(self.embed_module, 'should_center_mouse') and self.embed_module.should_center_mouse():
            # Center mouse in the desktop area
            desktop_x, desktop_y = self._get_desktop_pos()
            desktop_w, desktop_h = self._get_desktop_dimensions()
            center_x = desktop_x + desktop_w // 2
            center_y = desktop_y + desktop_h // 2
            pygame.mouse.set_pos(center_x, center_y)
            pygame.mouse.get_rel()  # Reset relative movement after centering
            print(f"[AstroMinerSession.update] Mouse centered at ({center_x}, {center_y})")
        
        # Set mouse delta from relative movement (this is what controls ship rotation)
        if abs(rel_x) > 0.01 or abs(rel_y) > 0.01:
            if self._update_count % 60 == 0 or (abs(rel_x) > 1.0 or abs(rel_y) > 1.0):
                print(f"[AstroMinerSession.update] Frame {self._update_count}, mouse rel=({rel_x:.2f},{rel_y:.2f})")
            self.embed_module.set_mouse_delta(float(rel_x), float(rel_y))
        else:
            # No movement, set delta to 0
            self.embed_module.set_mouse_delta(0.0, 0.0)
        
        # Also update position
        mouse_pos = pygame.mouse.get_pos()
        game_pos = self._get_game_mouse_pos(mouse_pos)
        self.embed_module.set_mouse_position(game_pos[0], game_pos[1])
        
        if self._update_count % 60 == 0:
            print(f"[AstroMinerSession.update] Frame {self._update_count}, mouse screen=({mouse_pos[0]},{mouse_pos[1]}), game=({game_pos[0]:.2f},{game_pos[1]:.2f})")
        
        self.last_mouse_pos = mouse_pos
        
        # Periodically refresh username from BBS (every 300 frames = ~5 seconds)
        # This ensures username is always current even if user switches accounts
        self.score_check_counter += 1
        if self.score_check_counter % 300 == 0:
            if hasattr(self.app, 'get_active_user'):
                active_user = self.app.get_active_user()
                if active_user and active_user.get('username'):
                    username = active_user.get('username')
                    if hasattr(self.embed_module, 'set_username'):
                        self.embed_module.set_username(username)
                        print(f"[AstroMinerSession.update] Refreshed username from BBS: {username}")
        
        # Check for new score and upload to Steam leaderboard (every 60 frames = ~1 second)
        if self.score_check_counter >= 60:
            if self.embed_module:
                try:
                    new_score = self.embed_module.get_last_final_score()
                    if new_score > 0 and new_score != self.last_uploaded_score:
                        # Upload to Steam leaderboard
                        if hasattr(self.app, 'steam') and self.app.steam.is_available():
                            self.app.steam.upload_leaderboard_score("AstroMinerLeaderboard", new_score)
                            self.last_uploaded_score = new_score
                            print(f"[AstroMinerSession] Uploaded score {new_score} to Steam leaderboard")
                except Exception as e:
                    # Silently fail if function doesn't exist yet (DLL not recompiled)
                    pass
        
        # Check if game wants to exit (from menu quit option)
        if self.embed_module:
            try:
                if hasattr(self.embed_module, 'should_exit') and callable(self.embed_module.should_exit):
                    if self.embed_module.should_exit():
                        self.exit_requested = True
            except Exception as e:
                pass  # Ignore errors checking exit flag
        
        try:
            # Get latest frame from the embedded game
            if self._update_count % 60 == 0:
                print(f"[AstroMinerSession.update] Calling get_frame_surface()...")
            self.last_frame = self.embed_module.get_frame_surface()
            if self._update_count % 60 == 0:
                print(f"[AstroMinerSession.update] Got frame: {self.last_frame is not None}")
        except Exception as e:
            # Print error every time to see what's happening
            print(f"[AstroMinerSession.update] ERROR getting frame: {e}")
            import traceback
            traceback.print_exc()
    
    def draw(self) -> None:
        """Prepare frame for rendering - actual drawing happens in main loop at correct layer."""
        # Frame is captured in update(), drawing happens in main loop after OS mode
        pass
    
    def get_game_frame(self) -> Optional[pygame.Surface]:
        """Get the current game frame for rendering at desktop layer."""
        if not self.last_frame:
            return None
            
        # Get desktop position (same as OS mode uses)
        baseline_desktop_x = 176
        baseline_desktop_y = 209
        desktop_x = int(baseline_desktop_x * self.app.scale)
        desktop_y = int(baseline_desktop_y * self.app.scale)
        
        desktop_width, desktop_height = self._get_desktop_dimensions()
        frame_width, frame_height = self.last_frame.get_size()
        
        # Scale preserving aspect ratio to fit within desktop dimensions
        if (frame_width, frame_height) != (desktop_width, desktop_height):
            # Calculate scale factors for both dimensions
            scale_x = desktop_width / frame_width
            scale_y = desktop_height / frame_height
            # Use the smaller scale to fit within bounds (letterbox/pillarbox)
            scale = min(scale_x, scale_y)
            
            new_width = int(frame_width * scale)
            new_height = int(frame_height * scale)
            
            scaled_frame = pygame.transform.smoothscale(self.last_frame, (new_width, new_height))
        else:
            scaled_frame = self.last_frame
        
        return (scaled_frame, (desktop_x, desktop_y))
    
    def exit(self) -> None:
        """Cleanup embedded game resources."""
        # Show pygame cursor again
        pygame.mouse.set_visible(True)
        print("[AstroMinerSession.exit] Cursor restored")
        
        if self.embed_module:
            try:
                self.embed_module.cleanup()
            except Exception as e:
                print(f"Error cleaning up Astro Miner: {e}")
        self.embed_module = None
        self.last_frame = None
        if hasattr(self, '_frame_error_logged'):
            delattr(self, '_frame_error_logged')


# ---------------------------------------------------------------------------
# CYBERTRAIN adapter (embedded C++ game with framebuffer rendering)
# ---------------------------------------------------------------------------


class CyberTrainSession(BaseGameSession):
    """Session adapter for CyberTrain using headless framebuffer rendering."""
    
    # Mapping from pygame key codes to raylib key codes
    KEY_MAP = {
        pygame.K_UP: 265, pygame.K_DOWN: 264,
        pygame.K_LEFT: 263, pygame.K_RIGHT: 262,
        pygame.K_SPACE: 32, pygame.K_RETURN: 257, pygame.K_ESCAPE: 256,
        pygame.K_a: 65, pygame.K_b: 66, pygame.K_c: 67, pygame.K_d: 68,
        pygame.K_e: 69, pygame.K_f: 70, pygame.K_g: 71, pygame.K_h: 72,
        pygame.K_i: 73, pygame.K_j: 74, pygame.K_k: 75, pygame.K_l: 76,
        pygame.K_m: 77, pygame.K_n: 78, pygame.K_o: 79, pygame.K_p: 80,
        pygame.K_q: 81, pygame.K_r: 82, pygame.K_s: 83, pygame.K_t: 84,
        pygame.K_u: 85, pygame.K_v: 86, pygame.K_w: 87, pygame.K_x: 88,
        pygame.K_y: 89, pygame.K_z: 90,
        pygame.K_0: 48, pygame.K_1: 49, pygame.K_2: 50, pygame.K_3: 51,
        pygame.K_4: 52, pygame.K_5: 53, pygame.K_6: 54, pygame.K_7: 55,
        pygame.K_8: 56, pygame.K_9: 57,
        pygame.K_MINUS: 45, pygame.K_EQUALS: 61,
        pygame.K_LSHIFT: 340, pygame.K_RSHIFT: 344,
    }
    
    MOUSE_BUTTON_MAP = {1: 0, 3: 1, 2: 2}
    
    def __init__(self, app: "GlyphisIOBBS"):
        super().__init__(app)
        self.embed_module = None
        self.last_frame: Optional[pygame.Surface] = None
        self.last_mouse_pos = (0, 0)
        self.baseline_desktop_x = 176
        self.baseline_desktop_y = 209
    
    def _get_desktop_pos(self) -> Tuple[int, int]:
        return self.app.res_manager.coords(self.baseline_desktop_x, self.baseline_desktop_y)
    
    def _load_base_desktop_size(self) -> Tuple[int, int]:
        if getattr(self, "_base_desktop_size", None):
            return self._base_desktop_size
        desktop_path = os.path.join("Data", "OS", "Desktop-Enviroment.png")
        try:
            desktop_image = pygame.image.load(desktop_path)
            self._base_desktop_size = desktop_image.get_size()
        except Exception:
            self._base_desktop_size = (self.app.bbs_width, self.app.bbs_height)
        return self._base_desktop_size
    
    def _get_desktop_dimensions(self) -> Tuple[int, int]:
        width = height = None
        if hasattr(self.app, "os_mode") and self.app.os_mode and hasattr(self.app.os_mode, "desktop_size"):
            ds = self.app.os_mode.desktop_size
            if ds:
                try:
                    width = int(ds[0])
                    height = int(ds[1])
                except (TypeError, ValueError):
                    width = height = None
        if width is None or height is None:
            base_w, base_h = self._load_base_desktop_size()
            width = self.app.res_manager.scale(base_w)
            height = self.app.res_manager.scale(base_h)
        width = max(720, width)
        height = max(480, height)
        return (width, height)
    
    def _get_game_mouse_pos(self, screen_pos: Tuple[int, int]) -> Tuple[float, float]:
        desktop_x, desktop_y = self._get_desktop_pos()
        desktop_w, desktop_h = self._get_desktop_dimensions()
        rel_x = screen_pos[0] - desktop_x
        rel_y = screen_pos[1] - desktop_y
        
        if self.embed_module:
            game_width, game_height = self.embed_module.get_size()
            if game_width > 0 and game_height > 0 and desktop_w > 0 and desktop_h > 0:
                game_x = (rel_x / desktop_w) * game_width
                game_y = (rel_y / desktop_h) * game_height
                return (
                    max(0.0, min(float(game_width), float(game_x))),
                    max(0.0, min(float(game_height), float(game_y)))
                )
        return (float(rel_x), float(rel_y))
    
    def enter(self) -> None:
        """Initialize the embedded game DLL."""
        try:
            from . import cybertrain_embed
            self.embed_module = cybertrain_embed
            
            # Set resolution to match desktop
            desktop_width, desktop_height = self._get_desktop_dimensions()
            print(f"[CyberTrainSession] Setting DLL resolution: {desktop_width}x{desktop_height}")
            if hasattr(cybertrain_embed, "set_render_resolution"):
                cybertrain_embed.set_render_resolution(desktop_width, desktop_height)
            
            # Sync username from BBS before initializing
            if hasattr(self.app, 'get_active_user'):
                active_user = self.app.get_active_user()
                if active_user and active_user.get('username'):
                    username = active_user.get('username')
                    print(f"[CyberTrainSession.enter] Setting username from BBS: {username}")
                    if hasattr(cybertrain_embed, 'set_username'):
                        cybertrain_embed.set_username(username)

            if not cybertrain_embed.initialize():
                print("[CyberTrainSession] Failed to initialize CyberTrain DLL")
                self.exit_requested = True
                return
            
            pygame.mouse.set_visible(False)
            print("[CyberTrainSession] CyberTrain started successfully")
            
        except ImportError as e:
            print(f"[CyberTrainSession] Failed to import cybertrain_embed: {e}")
            self.exit_requested = True
        except Exception as e:
            print(f"[CyberTrainSession] Failed to initialize CyberTrain: {e}")
            self.exit_requested = True
    
    def handle_event(self, event: pygame.event.Event) -> Optional[str]:
        if not self.embed_module:
            return None
        
        if event.type == pygame.KEYDOWN:
            raylib_key = self.KEY_MAP.get(event.key)
            if raylib_key is not None:
                self.embed_module.set_key_state(raylib_key, True)
        elif event.type == pygame.KEYUP:
            raylib_key = self.KEY_MAP.get(event.key)
            if raylib_key is not None:
                self.embed_module.set_key_state(raylib_key, False)
        
        if event.type == pygame.MOUSEBUTTONDOWN:
            raylib_button = self.MOUSE_BUTTON_MAP.get(event.button)
            if raylib_button is not None:
                self.embed_module.set_mouse_button_state(raylib_button, True)
                game_pos = self._get_game_mouse_pos(event.pos)
                self.embed_module.set_mouse_position(game_pos[0], game_pos[1])
            # Handle mouse wheel
            if event.button == 4:  # Scroll up
                if hasattr(self.embed_module, 'set_mouse_wheel'):
                    self.embed_module.set_mouse_wheel(1.0)
            elif event.button == 5:  # Scroll down
                if hasattr(self.embed_module, 'set_mouse_wheel'):
                    self.embed_module.set_mouse_wheel(-1.0)
        elif event.type == pygame.MOUSEBUTTONUP:
            raylib_button = self.MOUSE_BUTTON_MAP.get(event.button)
            if raylib_button is not None:
                self.embed_module.set_mouse_button_state(raylib_button, False)
        
        if event.type == pygame.MOUSEMOTION:
            dx, dy = 0.0, 0.0
            if hasattr(event, 'rel') and event.rel:
                dx, dy = float(event.rel[0]), float(event.rel[1])
            self.embed_module.set_mouse_delta(dx, dy)
            game_pos = self._get_game_mouse_pos(event.pos)
            self.embed_module.set_mouse_position(game_pos[0], game_pos[1])
            self.last_mouse_pos = event.pos
        
        if event.type == pygame.MOUSEWHEEL:
            if hasattr(self.embed_module, 'set_mouse_wheel'):
                self.embed_module.set_mouse_wheel(float(event.y))
        
        return None
    
    def update(self, dt: float) -> None:
        if not self.embed_module:
            return
        
        rel_x, rel_y = pygame.mouse.get_rel()
        if abs(rel_x) > 0.01 or abs(rel_y) > 0.01:
            self.embed_module.set_mouse_delta(float(rel_x), float(rel_y))
        else:
            self.embed_module.set_mouse_delta(0.0, 0.0)
        
        mouse_pos = pygame.mouse.get_pos()
        game_pos = self._get_game_mouse_pos(mouse_pos)
        self.embed_module.set_mouse_position(game_pos[0], game_pos[1])
        self.last_mouse_pos = mouse_pos
        
        # Sync username from BBS
        if hasattr(self.app, 'get_active_user'):
            active_user = self.app.get_active_user()
            if active_user and active_user.get('username'):
                self.embed_module.set_username(active_user.get('username'))

        # Upload score to Steam leaderboard
        try:
            credits = self.embed_module.get_last_final_score()
            if credits > 0:
                if hasattr(self.app, 'steam') and self.app.steam.is_available():
                    self.app.steam.upload_leaderboard_score("CyberTrainLeaderboard", credits)
        except Exception:
            pass

        if self.embed_module.should_exit():
            self.exit_requested = True
        
        try:
            self.last_frame = self.embed_module.get_frame_surface()
        except Exception as e:
            print(f"[CyberTrainSession] ERROR getting frame: {e}")
    
    def draw(self) -> None:
        pass
    
    def get_game_frame(self) -> Optional[Tuple[pygame.Surface, Tuple[int, int]]]:
        if not self.last_frame:
            return None
        
        desktop_x, desktop_y = self._get_desktop_pos()
        desktop_width, desktop_height = self._get_desktop_dimensions()
        frame_width, frame_height = self.last_frame.get_size()
        
        if (frame_width, frame_height) != (desktop_width, desktop_height):
            scale_x = desktop_width / frame_width
            scale_y = desktop_height / frame_height
            scale = min(scale_x, scale_y)
            new_width = int(frame_width * scale)
            new_height = int(frame_height * scale)
            scaled_frame = pygame.transform.smoothscale(self.last_frame, (new_width, new_height))
        else:
            scaled_frame = self.last_frame
        
        return (scaled_frame, (desktop_x, desktop_y))
    
    def exit(self) -> None:
        pygame.mouse.set_visible(True)
        print("[CyberTrainSession] Exiting, cursor restored")
        
        if self.embed_module:
            try:
                self.embed_module.cleanup()
            except Exception as e:
                print(f"[CyberTrainSession] Error cleaning up: {e}")
        self.embed_module = None
        self.last_frame = None


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
    GameDefinition(
        id="astro_miner",
        title="ASTRO MINER",
        description="Deep space mining simulator. Extract resources, upgrade ship, survive.",
        tokens_required=[Tokens.ASTROMINER],
        session_factory=AstroMinerSession,
    ),
    GameDefinition(
        id="cyber_train",
        title="CYBERTRAIN",
        description="Isometric railway builder. Lay tracks, build stations, manage trains.",
        tokens_required=[Tokens.CYBERTRAIN],
        session_factory=CyberTrainSession,
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

    if defn.type == "external_compiled":
        # ... (compilation logic preserved for future reference if needed) ...
        pass

    if defn.type != "external" or not defn.external_path:
        raise RuntimeError("Game definition is not external")

    target_path = os.path.abspath(defn.external_path)
    if not os.path.exists(target_path):
         if os.path.exists(defn.external_path):
             target_path = os.path.abspath(defn.external_path)
         else:
             # Try relative to repo root
             pass 

    working_dir = os.path.dirname(target_path)
    
    if target_path.lower().endswith(".exe"):
        cmd = [target_path]
        try:
            completed = subprocess.run(cmd, cwd=working_dir, check=False)
            return completed.returncode
        except Exception as exc:
             raise RuntimeError(f"Unable to launch external executable: {exc}") from exc
    else:
        # Assume Python script
        cmd = [sys.executable, defn.external_path]
        try:
            completed = subprocess.run(cmd, check=False)
            return completed.returncode
        except FileNotFoundError as exc:  # pragma: no cover - depends on filesystem
            raise RuntimeError(f"Unable to launch external game: {exc}") from exc

