"""
OS Mode - Desktop Environment
A fictional desktop environment that launches the BBS.
Enhanced with visual polish, smooth interactions, and improved UX.
"""

import pygame
import os
import sys
import time
import math
import json
import random
from typing import List, Dict, Tuple, Optional
from datetime import datetime

# Visual Constants
COLOR_BG_DARK = (20, 20, 40)
COLOR_BG_TITLE = (40, 40, 60)
COLOR_CYAN = (0, 255, 255)
COLOR_GREEN = (0, 255, 0)
COLOR_RED = (255, 0, 0)
COLOR_RED_DARK = (100, 0, 0)
COLOR_WHITE = (255, 255, 255)
COLOR_BLACK = (0, 0, 0)
COLOR_BUTTON_HOVER = (60, 60, 80)
COLOR_BUTTON_ACTIVE = (80, 80, 100)
COLOR_CORAL = (255, 127, 80)  # Coral color for recording
COLOR_GREY = (128, 128, 128)  # Grey for disconnected
COLOR_YELLOW = (255, 255, 0)
COLOR_AMBER = (255, 191, 0)
COLOR_MAGENTA = (255, 0, 153)
COLOR_NEON_GREEN = (0, 255, 160)
COLOR_TEAL = (0, 200, 255)
COLOR_DEEP_BLUE = (8, 12, 24)
COLOR_SELECTION = (0, 180, 255, 120)  # Semi-transparent cyan for text selection

# Mission note template (non-deletable narrative note)
MISSION_NOTE_TITLE = "Mission Objectives"
MISSION_NOTE_CONTENT = (
    "1. Receive Invite from Glyphis\n"
    "2. Get onto the BBS (0345728891)\n"
    "3. Complete a technical challenge to prove yourself\n"
    "4. Get invited to crack some games\n"
    "5. Obtain access to the Pirate Radio Stream"
)

# Animation Constants
HOVER_ANIMATION_SPEED = 8.0  # pixels per second
ICON_LABEL_FADE_SPEED = 3.0  # alpha per second

# Try to import cv2 for video playback
try:
    import cv2
    import numpy as np
    _cv2_available = True
except ImportError:
    _cv2_available = False
    cv2 = None
    np = None

# Chess game is now in a separate module
try:
    import sys
    import os
    # Add the chess directory to the path for import
    # Get the directory containing this file (OS_Mode.py)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    chess_dir = os.path.join(current_dir, "chess")
    if chess_dir not in sys.path:
        sys.path.insert(0, chess_dir)
    # Import the chess module (renamed to chess_game.py to avoid conflict with python-chess package)
    import importlib.util
    chess_module_path = os.path.join(chess_dir, "chess_game.py")
    if os.path.exists(chess_module_path):
        spec = importlib.util.spec_from_file_location("chess_game_module", chess_module_path)
        chess_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(chess_module)
        ChessGame = chess_module.ChessGame
        _chess_available = True
    else:
        raise ImportError(f"Chess module not found at {chess_module_path}")
except Exception as e:
    _chess_available = False
    ChessGame = None
    print(f"Warning: Could not import ChessGame: {e}")

# Solitaire game is now in a separate module
try:
    import sys
    import os
    import importlib.util
    # Add the solitaire directory to the path for import
    # Get the directory containing this file (OS_Mode.py)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    solitaire_dir = os.path.join(current_dir, "Solitaire")
    if solitaire_dir not in sys.path:
        sys.path.insert(0, solitaire_dir)
    # Import the solitaire module
    solitaire_module_path = os.path.join(solitaire_dir, "solitaire.py")
    if os.path.exists(solitaire_module_path):
        spec = importlib.util.spec_from_file_location("solitaire_module", solitaire_module_path)
        solitaire_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(solitaire_module)
        SolitaireGame = solitaire_module.SolitaireGame
        _solitaire_available = True
    else:
        raise ImportError(f"Solitaire module not found at {solitaire_module_path}")
except Exception as e:
    _solitaire_available = False
    SolitaireGame = None
    print(f"Warning: Could not import SolitaireGame: {e}")

# Data path helper - works for both development and built executable
def get_data_path(*path_parts):
    """
    Returns the path to the Data folder, handling both development and built executable scenarios.
    """
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        base_path = sys._MEIPASS
    else:
        # Running as script - go up from OS to Data folder
        script_dir = os.path.dirname(os.path.abspath(__file__))
        data_folder = os.path.dirname(script_dir)  # Go up from OS to Data folder
        base_path = data_folder
    
    # Return path within Data folder
    return os.path.join(base_path, *path_parts)


class OSMode:
    """
    Desktop Environment OS Mode
    Renders a desktop environment with draggable icons.
    """
    
    def __init__(self, screen: pygame.Surface, scale: float, reset_bbs_callback=None, bbs_x=None, bbs_y=None, bbs_width=None, has_token_callback=None, get_recording_state_callback=None, set_recording_state_callback=None, get_notes_callback=None, save_notes_callback=None, get_user_credentials_callback=None, get_chess_stats_callback=None, save_chess_stats_callback=None):
        """
        Initialize OS Mode.
        
        Args:
            screen: The main screen surface to draw on
            scale: Scale factor for proportional scaling
            reset_bbs_callback: Optional callback function to reset BBS and exit OS mode
            bbs_x: BBS window X position (for clock positioning)
            bbs_y: BBS window Y position (for clock positioning)
            bbs_width: BBS window width (for clock positioning)
            has_token_callback: Optional callback function to check if player has a token
            get_recording_state_callback: Optional callback to get recording state (returns (is_recording, start_time))
            set_recording_state_callback: Optional callback to set recording state (is_recording, start_time)
            get_notes_callback: Optional callback to get notes list
            save_notes_callback: Optional callback to save notes list
        """
        self.screen = screen
        self.scale = scale
        self.reset_bbs_callback = reset_bbs_callback
        self.bbs_x = bbs_x
        self.bbs_y = bbs_y
        self.bbs_width = bbs_width
        self.has_token = has_token_callback or (lambda token: False)
        self.get_recording_state = get_recording_state_callback or (lambda: (False, None))
        self.set_recording_state = set_recording_state_callback or (lambda is_rec, start_time=None: None)
        self.get_notes = get_notes_callback or (lambda: [])
        self.save_notes = save_notes_callback or (lambda notes: None)
        self.get_user_credentials = get_user_credentials_callback or (lambda: ("", ""))
        self.get_chess_stats = get_chess_stats_callback or (lambda: {})
        self.save_chess_stats = save_chess_stats_callback or (lambda stats: None)
        
        # Baseline coordinates (at 2560x1440 resolution)
        self.baseline_desktop_x = 176
        self.baseline_desktop_y = 209
        
        # Scaled coordinates
        self.desktop_x = int(self.baseline_desktop_x * self.scale)
        self.desktop_y = int(self.baseline_desktop_y * self.scale)
        
        # Load desktop background
        desktop_path = get_data_path("OS", "Desktop-Enviroment.png")
        try:
            self.desktop_image = pygame.image.load(desktop_path).convert_alpha()
            # Scale desktop image
            original_size = self.desktop_image.get_size()
            self.desktop_size = (
                int(original_size[0] * self.scale),
                int(original_size[1] * self.scale)
            )
            self.desktop_image = pygame.transform.scale(self.desktop_image, self.desktop_size)
        except Exception as e:
            print(f"Warning: Failed to load Desktop-Enviroment.png: {e}")
            self.desktop_image = None
            self.desktop_size = (0, 0)
        
        # Desktop boundaries (for icon dragging)
        self.desktop_rect = pygame.Rect(
            self.desktop_x,
            self.desktop_y,
            self.desktop_size[0],
            self.desktop_size[1]
        )
        
        # Load icons (both normal and selected "S" versions)
        self.icons = []
        icon_files = [
            "tape-icon.png",
            "hard-drive-icon.png",
            "modem-iconpng.png",
            "games-folder.png",
            "notes-icon.png"
        ]
        
        icon_spacing = 0  # Will be calculated based on icon height
        current_y = self.desktop_y + int(70 * self.scale)  # Start 70px down from desktop top
        
        # Load saved icon positions if they exist
        saved_positions = self._load_icon_positions()
        
        for icon_file in icon_files:
            icon_path = get_data_path("OS", icon_file)
            # Get the "S" version filename (e.g., "tape-icon.png" -> "S-tape-icon.png")
            s_icon_file = "S-" + icon_file
            s_icon_path = get_data_path("OS", s_icon_file)
            
            try:
                # Load normal icon
                icon_image = pygame.image.load(icon_path).convert_alpha()
                # Scale icon
                original_icon_size = icon_image.get_size()
                icon_size = (
                    int(original_icon_size[0] * self.scale),
                    int(original_icon_size[1] * self.scale)
                )
                icon_image = pygame.transform.scale(icon_image, icon_size)
                
                # Load selected "S" version icon
                s_icon_image = None
                try:
                    s_icon_image = pygame.image.load(s_icon_path).convert_alpha()
                    s_icon_image = pygame.transform.scale(s_icon_image, icon_size)
                except Exception as e:
                    print(f"Warning: Failed to load {s_icon_file}: {e}")
                    # If S version doesn't exist, use normal icon as fallback
                    s_icon_image = icon_image
                
                # Position icon - use saved position if available, otherwise default stacked position
                if icon_file in saved_positions:
                    # Use saved position (already scaled)
                    icon_x = saved_positions[icon_file]["x"]
                    icon_y = saved_positions[icon_file]["y"]
                else:
                    # Default position: top-left corner, stacked vertically
                    icon_x = self.desktop_x + int(10 * self.scale)  # Small margin from left
                    icon_y = current_y
                
                icon_data = {
                    "image": icon_image,  # Normal version
                    "s_image": s_icon_image,  # Selected "S" version
                    "x": icon_x,
                    "y": icon_y,
                    "width": icon_size[0],
                    "height": icon_size[1],
                    "name": icon_file,
                    "selected": False,  # Track if this icon is selected
                    "dragging": False,
                    "drag_offset_x": 0,
                    "drag_offset_y": 0
                }
                self.icons.append(icon_data)
                
                # Move to next position (add spacing) - only if using default positions
                if icon_file not in saved_positions:
                    current_y += icon_size[1] + int(10 * self.scale)  # 10px spacing between icons
                
            except Exception as e:
                print(f"Warning: Failed to load {icon_file}: {e}")
        
        self._align_icons_to_tape_center()
        
        # Load custom mouse cursor
        cursor_path = get_data_path("OS", "mouse_cursor.png")
        try:
            cursor_image = pygame.image.load(cursor_path).convert_alpha()
            # Scale cursor
            original_cursor_size = cursor_image.get_size()
            cursor_size = (
                int(original_cursor_size[0] * self.scale),
                int(original_cursor_size[1] * self.scale)
            )
            cursor_image = pygame.transform.scale(cursor_image, cursor_size)
            # Create cursor with hotspot at top-left (0, 0)
            self.custom_cursor = pygame.cursors.Cursor((0, 0), cursor_image)
            self.cursor_image = cursor_image
        except Exception as e:
            print(f"Warning: Failed to load mouse_cursor.png: {e}")
            self.custom_cursor = None
            self.cursor_image = None
        
        # Load desktop scanline overlay
        scanline_path = get_data_path("OS", "Scanline-Desktop.png")
        try:
            self.desktop_scanline_image = pygame.image.load(scanline_path).convert_alpha()
            # Scale scanline to match desktop size
            self.desktop_scanline_image = pygame.transform.scale(
                self.desktop_scanline_image, 
                self.desktop_size
            )
        except Exception as e:
            print(f"Warning: Failed to load Scanline-Desktop.png: {e}")
            self.desktop_scanline_image = None
        
        # Mouse state
        self.mouse_pos = (0, 0)
        self.mouse_pressed = False
        self.hovered_icon = None  # Currently hovered icon
        self.hovered_button = None  # Currently hovered button (modal_name, button_type)
        self.icon_label_alpha = {}  # Alpha values for icon labels
        self.button_hover_offset = {}  # Hover animation offset for buttons
        
        # Overlay state
        self.overlay_active = False
        
        # Double-click detection
        self.last_click_time = 0.0
        self.last_click_pos = None
        self.double_click_threshold = 0.5  # seconds
        
        # Modal state - support multiple modals open at once
        self.active_modals = set()  # Set of active modal names: {"tape", "modem", etc.}
        self.modal_positions = {}  # Dict mapping modal name to (x, y) position
        self.modal_dragging = None  # Currently dragging modal name, or None
        self.modal_drag_offset = (0, 0)  # Offset from mouse to modal top-left when dragging
        self.modal_title_bar_height = int(30 * self.scale)  # Height of title bar for dragging
        self.tape_modal_terminal_text = ""
        self.tape_modal_terminal_lines = []  # List of terminal lines to display
        self.tape_modal_message_timer = 0.0  # Timer for delayed messages
        self.tape_modal_video_playing = False
        self.tape_modal_video_cap = None
        self.tape_modal_video_frame = None
        self.tape_modal_video_audio_channel = None
        self.tape_modal_video_original_size = None  # (width, height) of original video
        self.tape_modal_video_display_size = None  # (width, height) of displayed video (maintaining aspect ratio)
        self.tape_modal_video_fade_state = "none"  # "fade_in", "playing", "fade_out", "none"
        self.tape_modal_video_fade_alpha = 0.0  # 0.0 to 1.0
        self.tape_modal_video_fade_duration = 1.0  # seconds for fade in/out
        self.tape_modal_video_fade_timer = 0.0
        self.tape_modal_video_completed = False  # Track if video has finished playing
        self.tape_modal_video_last_frame_time = 0.0  # Track last frame update time for FPS throttling
        self.tape_modal_video_target_fps = 30.0  # Target FPS for video playback (will be set from video file)
        
        # Notes modal state
        self.notes_modal_current_tab = 0  # Currently selected tab index
        self.notes_modal_edit_mode = False  # Whether currently editing a note
        self.notes_modal_edit_index = None  # Index of note being edited
        self.notes_modal_edit_field = "content"  # "title" or "content"
        self.notes_modal_edit_title_text = ""
        self.notes_modal_edit_content_text = ""
        self.notes_modal_title_cursor = 0
        self.notes_modal_content_cursor = 0
        self.notes_modal_cursor_blink_timer = 0.0
        self.notes_modal_title_selection = (0, 0)
        self.notes_modal_content_selection = (0, 0)
        self.notes_modal_selection_anchor = 0
        self.notes_modal_selection_field = None
        self.notes_modal_dragging_selection = False
        self.notes_modal_title_field_rect = None
        self.notes_modal_content_field_rect = None
        self.notes_modal_title_font = None
        self.notes_modal_content_font = None
        self.notes_modal_title_text_origin = (0, 0)
        self.notes_modal_content_text_origin = (0, 0)
        self.notes_modal_content_available_width = 0
        self.notes_modal_content_line_height = 0
        self.notes_modal_content_layout_info: List[Dict[str, object]] = []
        self.notes_modal_content_cursor_aim_x: Optional[int] = None
        self.notes_modal_hitboxes = {}  # Cached rects for click handling
        self.notes_modal_message = ""
        
        # Documentation viewer position (baseline 2560x1440)
        self.docs_viewer_baseline_x = 1547
        self.docs_viewer_baseline_y = 37
        
        # Datasette video position (baseline 2560x1440)
        self.datasette_baseline_x = 1363
        self.datasette_baseline_y = 44
        
        # Modem modal state
        self.modem_modal_dialed_sequence = ""  # Track dialed numbers
        self.modem_modal_target_sequence = "0345728891"  # Target sequence to dial
        self.modem_modal_connection_messages = []  # List of connection messages
        self.modem_modal_message_index = 0  # Current message index
        self.modem_modal_message_timer = 0.0  # Timer for message progression
        self.modem_modal_should_reset_bbs = False  # Flag to signal BBS reset
        self.modem_modal_should_exit_os = False  # Flag to signal OS mode exit
        self.modem_modal_connection_started = False  # Whether connection sequence has started
        self.modem_terminal_rect = None
        self.modem_packet_sprites: List[Dict[str, float]] = []
        self.modem_packet_spawn_timer = 0.0
        self.modem_wave_phase = 0.0
        self.modem_dial_sound = None
        self.modem_dial_sound_playing = False
        self.modem_terminal_palette = [
            COLOR_NEON_GREEN,
            COLOR_CYAN,
            COLOR_AMBER,
            COLOR_MAGENTA,
            COLOR_TEAL
        ]
        self.network_connected = False
        
        # Games modal state
        self.games_icon_defs = [
            {
                "name": "chess",
                "file": "chess.png",
                "selected_file": "S-chess.png",
                "label": "Chess",
                "default_pos": (30, 40)
            },
            {
                "name": "solitaire",
                "file": "solitaire.png",
                "selected_file": "S-solitaire.png",
                "label": "Solitaire",
                "default_pos": (200, 40)
            },
            {
                "name": "civitas",
                "file": "civitas_nihilium.png",
                "selected_file": "S-civitas_nihilium.png",
                "label": "Civitas Nihilium",
                "default_pos": (280, 40)
            }
        ]
        self.games_modal_icons: List[Dict[str, object]] = []
        self.games_modal_selected_icon: Optional[str] = None
        self.games_modal_dragging_icon: Optional[Dict[str, object]] = None
        self.games_modal_drag_offset = (0, 0)
        self.games_modal_content_rect: Optional[pygame.Rect] = None
        self.games_modal_last_click_name: Optional[str] = None
        self.games_modal_last_click_time: float = 0.0
        self._load_games_icons()

        # Chess game instance
        if _chess_available and ChessGame:
            try:
                self.chess_game = ChessGame(
                    self.screen,
                    self.scale,
                    self.desktop_x,
                    self.desktop_y,
                    self.desktop_size
                )
            except Exception as e:
                print(f"Warning: Failed to initialize ChessGame: {e}")
                import traceback
                traceback.print_exc()
                self.chess_game = None
        else:
            self.chess_game = None
            if not _chess_available:
                print(f"Warning: Chess module not available. _chess_available={_chess_available}, ChessGame={ChessGame}")
        
        # Solitaire game instance
        if _solitaire_available and SolitaireGame:
            try:
                health_monitor_y = self.bbs_y + int(10 * self.scale) if self.bbs_y else self.desktop_y + int(10 * self.scale)
                self.solitaire_game = SolitaireGame(
                    self.screen,
                    self.scale,
                    self.desktop_x,
                    self.desktop_y,
                    self.desktop_size,
                    health_monitor_y,
                    self.bbs_x or 0,
                    self.bbs_width or 0
                )
            except Exception as e:
                print(f"Warning: Failed to initialize SolitaireGame: {e}")
                import traceback
                traceback.print_exc()
                self.solitaire_game = None
        else:
            self.solitaire_game = None
            if not _solitaire_available:
                print(f"Warning: Solitaire module not available. _solitaire_available={_solitaire_available}, SolitaireGame={SolitaireGame}")
        
    def handle_event(self, event: pygame.event.Event) -> bool:
        """
        Handle pygame events for OS Mode.
        Returns True if event was handled, False otherwise.
        """
        if self.chess_game and self.chess_game.active and self.chess_game.handle_event(event):
            return True
        if self.solitaire_game and self.solitaire_game.active and self.solitaire_game.handle_event(event):
            return True
        if event.type == pygame.MOUSEMOTION:
            self.mouse_pos = event.pos
            
            # Update hover states for visual feedback
            self._update_hover_states(event.pos[0], event.pos[1])
            
            # Handle modal dragging
            if self.mouse_pressed and self.modal_dragging:
                # Calculate new position
                new_x = self.mouse_pos[0] - self.modal_drag_offset[0]
                new_y = self.mouse_pos[1] - self.modal_drag_offset[1]
                
                # Get modal size
                modal_w, modal_h = self._get_modal_size(self.modal_dragging)
                
                # Constrain to desktop boundaries
                new_x = max(self.desktop_rect.left, 
                           min(new_x, self.desktop_rect.right - modal_w))
                new_y = max(self.desktop_rect.top, 
                           min(new_y, self.desktop_rect.bottom - modal_h))
                
                self.modal_positions[self.modal_dragging] = (new_x, new_y)
                return True
            
            # Handle icon dragging
            if self.mouse_pressed:
                for icon in self.icons:
                    if icon["dragging"]:
                        # Calculate new position
                        new_x = self.mouse_pos[0] - icon["drag_offset_x"]
                        new_y = self.mouse_pos[1] - icon["drag_offset_y"]
                        
                        # Constrain to desktop boundaries
                        new_x = max(self.desktop_rect.left, 
                                   min(new_x, self.desktop_rect.right - icon["width"]))
                        new_y = max(self.desktop_rect.top, 
                                   min(new_y, self.desktop_rect.bottom - icon["height"]))
                        
                        icon["x"] = new_x
                        icon["y"] = new_y
                        return True

            if (self.notes_modal_dragging_selection and
                    "notes" in self.active_modals and
                    self.notes_modal_edit_mode and
                    self._notes_update_drag_selection(event.pos[0], event.pos[1])):
                return True
            if (self.mouse_pressed and
                    "games" in self.active_modals and
                    self.games_modal_dragging_icon and
                    self._update_games_icon_drag(event.pos[0], event.pos[1])):
                return True
        
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left mouse button
                self.mouse_pressed = True
                mouse_x, mouse_y = event.pos
                current_time = time.time()
                
                # Check if clicking on a modal title bar for dragging (but exclude close buttons)
                # Check modals in reverse order (top-most first) to handle close buttons correctly
                for modal_name in reversed(list(self.active_modals)):
                    modal_x, modal_y = self.modal_positions.get(modal_name, (0, 0))
                    modal_w, modal_h = self._get_modal_size(modal_name)
                    if modal_w > 0 and modal_h > 0:
                        title_bar_rect = pygame.Rect(
                            modal_x,
                            modal_y,
                            modal_w,
                            self.modal_title_bar_height
                        )
                        if title_bar_rect.collidepoint(mouse_x, mouse_y):
                            # Check if clicking on close button first (exclude from dragging)
                            close_btn_size = int(20 * self.scale)
                            close_btn_x = modal_x + modal_w - close_btn_size - int(5 * self.scale)
                            close_btn_y = modal_y + int(5 * self.scale)
                            close_btn_rect = pygame.Rect(close_btn_x, close_btn_y, close_btn_size, close_btn_size)
                            
                            # If clicking on close button, handle it directly here
                            if close_btn_rect.collidepoint(mouse_x, mouse_y):
                                # Close the modal
                                # Reset entire OS Mode when any modal closes
                                self._reset_os_mode()
                                return True
                            else:
                                # Start dragging this modal
                                self.modal_dragging = modal_name
                                self.modal_drag_offset = (mouse_x - modal_x, mouse_y - modal_y)
                                return True
                
                # Check if clicking on an icon FIRST (icons should be clickable even when modals are open)
                icon_clicked = False
                clicked_icon = None
                for icon in self.icons:
                    icon_rect = pygame.Rect(
                        icon["x"],
                        icon["y"],
                        icon["width"],
                        icon["height"]
                    )
                    if icon_rect.collidepoint(mouse_x, mouse_y):
                        icon_clicked = True
                        clicked_icon = icon
                        
                        # Check for double-click
                        is_double_click = (
                            self.last_click_pos is not None and
                            abs(self.last_click_pos[0] - mouse_x) < 5 and
                            abs(self.last_click_pos[1] - mouse_y) < 5 and
                            (current_time - self.last_click_time) < self.double_click_threshold
                        )
                        
                        if is_double_click:
                            # Double-click detected - open modal based on icon
                            icon_name = icon["name"]
                            modal_name = None
                            if "tape-icon" in icon_name:
                                modal_name = "tape"
                                self.tape_modal_terminal_text = ""
                                self._stop_tape_video()
                            elif "hard-drive-icon" in icon_name:
                                modal_name = "hard_drive"
                            elif "modem-iconpng" in icon_name:
                                modal_name = "modem"
                                # Initialize dial pad state
                                self.modem_modal_dialed_sequence = ""
                                self.modem_modal_connection_messages = []
                                self.modem_modal_message_index = 0
                                self.modem_modal_message_timer = 0.0
                                self.modem_modal_should_reset_bbs = False
                                self.modem_modal_should_exit_os = False
                                self.modem_modal_connection_started = False
                            elif "games-folder" in icon_name:
                                modal_name = "games"
                            elif "notes-icon" in icon_name:
                                modal_name = "notes"
                            
                            if modal_name:
                                # Add modal to active set
                                self.active_modals.add(modal_name)
                                # Set initial position if not already set
                                if modal_name not in self.modal_positions:
                                    modal_w, modal_h = self._get_modal_size(modal_name)
                                    modal_x, modal_y = self._get_modal_position(modal_w, modal_h, modal_name)
                                    self.modal_positions[modal_name] = (modal_x, modal_y)
                            
                            # Reset double-click tracking
                            self.last_click_time = 0.0
                            self.last_click_pos = None
                            return True
                        else:
                            # Single click - select icon
                            # Deselect all icons first
                            for other_icon in self.icons:
                                other_icon["selected"] = False
                            # Select the clicked icon
                            icon["selected"] = True
                            icon["dragging"] = True
                            icon["drag_offset_x"] = mouse_x - icon["x"]
                            icon["drag_offset_y"] = mouse_y - icon["y"]
                            
                            # Update double-click tracking
                            self.last_click_time = current_time
                            self.last_click_pos = (mouse_x, mouse_y)
                            return True
                
                # Handle modal button clicks (check modals in reverse order for top-most first)
                # Only check modals if we didn't click on an icon
                if not icon_clicked:
                    for modal_name in reversed(list(self.active_modals)):
                        if modal_name == "tape":
                            if self._handle_tape_modal_click(mouse_x, mouse_y):
                                return True
                        elif modal_name == "modem":
                            if self._handle_modem_modal_click(mouse_x, mouse_y):
                                return True
                        elif modal_name == "notes":
                            if self._handle_notes_modal_click(mouse_x, mouse_y):
                                return True
                        elif modal_name == "games":
                            if self._handle_games_modal_click(mouse_x, mouse_y):
                                return True
                
                # If clicking on desktop (not on an icon), deselect all icons
                if not icon_clicked and self.desktop_rect.collidepoint(mouse_x, mouse_y):
                    for icon in self.icons:
                        icon["selected"] = False
                    # Reset double-click tracking
                    self.last_click_time = 0.0
                    self.last_click_pos = None
                    return True
        
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:  # Left mouse button
                self.mouse_pressed = False
                self.notes_modal_dragging_selection = False
                self.games_modal_dragging_icon = None
                # Stop dragging all icons
                for icon in self.icons:
                    if icon["dragging"]:
                        icon["dragging"] = False
                        return True
        
        elif event.type == pygame.KEYDOWN:
            if "notes" in self.active_modals and self.notes_modal_edit_mode:
                if self._notes_handle_keydown(event):
                    return True

        elif event.type == pygame.TEXTINPUT:
            if "notes" in self.active_modals and self.notes_modal_edit_mode:
                if self._notes_handle_textinput(event.text):
                    return True
        
        return False
    
    def _get_modal_size(self, modal_name: str) -> Tuple[int, int]:
        """Get modal dimensions for a given modal name."""
        gap = int(20 * self.scale)
        
        if modal_name == "tape":
            # Tape modal dimensions (smaller window)
            modal_w = int(500 * self.scale)
            modal_h = int(400 * self.scale) + self.modal_title_bar_height
        elif modal_name == "modem":
            layout = self._get_modem_layout_metrics()
            modal_w = layout["modal_w"]
            modal_h = layout["modal_h"]
        elif modal_name == "notes":
            # Notes modal dimensions
            modal_w = int(700 * self.scale)
            modal_h = int(500 * self.scale) + self.modal_title_bar_height
        elif modal_name == "games":
            modal_w = int(560 * self.scale)
            modal_h = int(420 * self.scale) + self.modal_title_bar_height
        else:
            # Default dimensions
            modal_w = int(400 * self.scale)
            modal_h = int(300 * self.scale) + self.modal_title_bar_height
        
        return (modal_w, modal_h)
    
    def _get_modal_position(self, modal_w: int, modal_h: int, modal_name: str = None) -> Tuple[int, int]:
        """Calculate modal position within desktop boundaries. Uses stored position if available."""
        # If modal has a stored position, use it
        if modal_name and modal_name in self.modal_positions:
            stored_x, stored_y = self.modal_positions[modal_name]
            # Ensure it's still within bounds
            max_x = self.desktop_x + self.desktop_size[0] - modal_w
            max_y = self.desktop_y + self.desktop_size[1] - modal_h
            stored_x = max(self.desktop_x, min(stored_x, max_x))
            stored_y = max(self.desktop_y, min(stored_y, max_y))
            return (stored_x, stored_y)
        
        # Position modal with margin from desktop edges
        margin = int(50 * self.scale)
        modal_x = self.desktop_x + margin
        modal_y = self.desktop_y + margin
        
        # Ensure modal doesn't extend beyond desktop boundaries
        max_x = self.desktop_x + self.desktop_size[0] - modal_w - margin
        max_y = self.desktop_y + self.desktop_size[1] - modal_h - margin
        
        modal_x = max(self.desktop_x + margin, min(modal_x, max_x))
        modal_y = max(self.desktop_y + margin, min(modal_y, max_y))
        
        return (modal_x, modal_y)
    
    def _clamp_modal_to_desktop(self, modal_w: int, modal_h: int) -> Tuple[int, int]:
        """Clamp modal dimensions to fit within desktop boundaries."""
        margin = int(100 * self.scale)  # Total margin (50px on each side)
        max_w = self.desktop_size[0] - margin
        max_h = self.desktop_size[1] - margin
        
        clamped_w = min(modal_w, max_w)
        clamped_h = min(modal_h, max_h)
        
        return (clamped_w, clamped_h)
    
    def _handle_tape_modal_click(self, mouse_x: int, mouse_y: int) -> bool:
        """Handle clicks within the tape modal. Returns True if click was handled."""
        # Modal dimensions (scaled)
        modal_w = int(800 * self.scale)
        modal_h = int(500 * self.scale) + self.modal_title_bar_height
        
        # Clamp modal to fit within desktop boundaries (same as drawing)
        modal_w, modal_h = self._clamp_modal_to_desktop(modal_w, modal_h)
        modal_x, modal_y = self.modal_positions.get("tape", (0, 0))
        
        # Check if clicking on close button in title bar
        close_btn_size = int(20 * self.scale)
        close_btn_x = modal_x + modal_w - close_btn_size - int(5 * self.scale)
        close_btn_y = modal_y + int(5 * self.scale)
        close_btn_rect = pygame.Rect(close_btn_x, close_btn_y, close_btn_size, close_btn_size)
        if close_btn_rect.collidepoint(mouse_x, mouse_y):
            # Reset entire OS Mode when modal closes
            self._reset_os_mode()
            return True
        
        modal_rect = pygame.Rect(modal_x, modal_y, modal_w, modal_h)
        if not modal_rect.collidepoint(mouse_x, mouse_y):
            return False
        
        # Button dimensions (accounting for title bar) - centered, no CLOSE button
        button_y = modal_y + self.modal_title_bar_height + int(220 * self.scale)  # Closer to terminal
        button_h = int(35 * self.scale)
        button_w = int(140 * self.scale)
        button_spacing = int(15 * self.scale)
        
        # Calculate total width of buttons and spacing for centering
        total_buttons_width = 2 * button_w + button_spacing  # Two buttons (LOAD and RECORD)
        buttons_start_x = modal_x + (modal_w - total_buttons_width) // 2  # Center align
        
        # LOAD DATA button
        load_btn_x = buttons_start_x
        load_btn_rect = pygame.Rect(load_btn_x, button_y, button_w, button_h)
        
        # RECORD DATA button
        record_btn_x = load_btn_x + button_w + button_spacing
        record_btn_rect = pygame.Rect(record_btn_x, button_y, button_w, button_h)
        
        if load_btn_rect.collidepoint(mouse_x, mouse_y):
            self.tape_modal_terminal_lines = ["No data to load"]
            self.tape_modal_terminal_text = "\n".join(self.tape_modal_terminal_lines)
            self.tape_modal_message_timer = 0.0
            self._stop_tape_video()
            return True
        elif record_btn_rect.collidepoint(mouse_x, mouse_y):
            # Clear terminal and start recording sequence
            self.tape_modal_terminal_lines = []
            self.tape_modal_message_timer = 0.0
            
            # Reset video completion flag so video can play again
            self.tape_modal_video_completed = False
            
            # Get current datetime and format as 1989 date with month and year
            from datetime import datetime
            current_dt = datetime.now()
            # Format as 1989-MM-DD HH:MM (replace year with 1989)
            date_str = current_dt.strftime("1989-%m-%d %H:%M")
            
            # Set recording flag in user profile
            import time
            recording_start_time = time.time()
            self.set_recording_state(True, recording_start_time)
            
            # First message immediately
            self.tape_modal_terminal_lines.append("Datasette Tape Detected Recoding Started")
            self.tape_modal_terminal_lines.append(date_str)
            
            # Update terminal text display
            self.tape_modal_terminal_text = "\n".join(self.tape_modal_terminal_lines)
            
            self._start_tape_video()
            return True
        
        return False
    
    def _handle_modem_modal_click(self, mouse_x: int, mouse_y: int) -> bool:
        """Handle clicks within the modem modal. Returns True if click was handled."""
        layout = self._get_modem_layout_metrics()
        button_size = layout["button_size"]
        button_spacing = layout["button_spacing"]
        gap = layout["gap"]
        terminal_h = layout["terminal_h"]
        dial_pad_h = layout["dial_pad_h"]
        spacing = layout["spacing"]
        call_btn_h = layout["call_btn_h"]
        modal_w, modal_h = self._clamp_modal_to_desktop(layout["modal_w"], layout["modal_h"])
        modal_x, modal_y = self.modal_positions.get("modem", (0, 0))
        
        # Check if clicking on close button in title bar
        close_btn_size = int(20 * self.scale)
        close_btn_x = modal_x + modal_w - close_btn_size - int(5 * self.scale)
        close_btn_y = modal_y + int(5 * self.scale)
        close_btn_rect = pygame.Rect(close_btn_x, close_btn_y, close_btn_size, close_btn_size)
        if close_btn_rect.collidepoint(mouse_x, mouse_y):
            # Reset entire OS Mode when modal closes
            self._reset_os_mode()
            return True
        
        modal_rect = pygame.Rect(modal_x, modal_y, modal_w, modal_h)
        if not modal_rect.collidepoint(mouse_x, mouse_y):
            return False
        
        # Don't handle clicks if connection sequence has started
        if self.modem_modal_connection_started:
            return False
        
        # Calculate positions (accounting for title bar)
        dial_start_x = modal_x + gap
        dial_start_y = modal_y + self.modal_title_bar_height + gap + terminal_h + spacing
        
        # Dial pad buttons: 1-9, *, 0, #
        dial_buttons = [
            ["1", "2", "3"],
            ["4", "5", "6"],
            ["7", "8", "9"],
            ["*", "0", "#"]
        ]
        
        # Check if clicking on a dial button
        for row_idx, row in enumerate(dial_buttons):
            for col_idx, button_label in enumerate(row):
                btn_x = dial_start_x + col_idx * (button_size + button_spacing)
                btn_y = dial_start_y + row_idx * (button_size + button_spacing)
                btn_rect = pygame.Rect(btn_x, btn_y, button_size, button_size)
                
                if btn_rect.collidepoint(mouse_x, mouse_y):
                    # Add to dialed sequence
                    self.modem_modal_dialed_sequence += button_label
                    return True
        
        # CALL button (between dial pad and close button)
        call_btn_x = modal_x + gap
        call_btn_y = modal_y + self.modal_title_bar_height + gap + terminal_h + spacing + dial_pad_h + spacing
        call_btn_w = modal_w - 2 * gap
        call_btn_rect = pygame.Rect(call_btn_x, call_btn_y, call_btn_w, call_btn_h)
        
        if call_btn_rect.collidepoint(mouse_x, mouse_y):
            # Check if sequence matches target
            if self.modem_modal_dialed_sequence == self.modem_modal_target_sequence:
                # Start connection sequence
                self.modem_modal_connection_started = True
                self._play_modem_dial_sound()
                self.modem_packet_sprites.clear()
                self.modem_packet_spawn_timer = 0.0
                self.modem_modal_connection_messages = [
                    "Initializing modem connection...",
                    "Dialing 0345728891...",
                    "Establishing connection...",
                    "Handshaking...",
                    "Packets found!",
                    "Loading data...",
                    "Connection established!"
                ]
                self.modem_modal_message_index = 0
                self.modem_modal_message_timer = 0.0
            else:
                # Show error message if wrong number
                self.modem_modal_dialed_sequence = ""  # Clear sequence
            return True
        
        return False

    def _handle_games_modal_click(self, mouse_x: int, mouse_y: int) -> bool:
        """Handle clicks within the games modal."""
        modal_w, modal_h = self._get_modal_size("games")
        modal_w, modal_h = self._clamp_modal_to_desktop(modal_w, modal_h)
        modal_x, modal_y = self.modal_positions.get("games", (0, 0))

        close_btn_size = int(20 * self.scale)
        close_btn_rect = pygame.Rect(
            modal_x + modal_w - close_btn_size - int(5 * self.scale),
            modal_y + int(5 * self.scale),
            close_btn_size,
            close_btn_size
        )
        if close_btn_rect.collidepoint(mouse_x, mouse_y):
            self._reset_os_mode()
            return True

        modal_rect = pygame.Rect(modal_x, modal_y, modal_w, modal_h)
        if not modal_rect.collidepoint(mouse_x, mouse_y):
            return False

        gap = int(20 * self.scale)
        content_rect = pygame.Rect(
            modal_x + gap,
            modal_y + self.modal_title_bar_height + gap,
            modal_w - 2 * gap,
            modal_h - self.modal_title_bar_height - 2 * gap
        ).inflate(-int(10 * self.scale), -int(10 * self.scale))
        self.games_modal_content_rect = content_rect

        for icon in reversed(self.games_modal_icons):
            icon_rect = icon.get("rect")
            if icon_rect and icon_rect.collidepoint(mouse_x, mouse_y):
                self._select_games_icon(icon)
                self.games_modal_dragging_icon = icon
                self.games_modal_drag_offset = (
                    mouse_x - icon_rect.x,
                    mouse_y - icon_rect.y
                )
                current_time = time.time()
                if (self.games_modal_last_click_name == icon["name"] and
                        (current_time - self.games_modal_last_click_time) < self.double_click_threshold):
                    self._launch_games_app(icon["name"])
                    self.games_modal_last_click_name = None
                else:
                    self.games_modal_last_click_name = icon["name"]
                    self.games_modal_last_click_time = current_time
                return True

        if content_rect.collidepoint(mouse_x, mouse_y):
            self._clear_games_icon_selection()
            self.games_modal_dragging_icon = None
            return True

        return False

    def _launch_games_app(self, icon_name: str) -> None:
        if icon_name == "chess":
            if self.chess_game:
                # Calculate health monitor Y position
                health_monitor_y = self.bbs_y + int(10 * self.scale) if self.bbs_y else self.desktop_y + int(10 * self.scale)
                # Update desktop coordinates before starting
                self.chess_game.update_desktop(self.desktop_x, self.desktop_y, self.desktop_size, health_monitor_y)
                self.chess_game.start()
            else:
                print(f"Chess game module not available. _chess_available={_chess_available}, ChessGame={ChessGame}, self.chess_game={getattr(self, 'chess_game', 'NOT SET')}")
                # Try to initialize if it wasn't initialized before
                if _chess_available and ChessGame:
                    try:
                        health_monitor_y = self.bbs_y + int(10 * self.scale) if self.bbs_y else self.desktop_y + int(10 * self.scale)
                        self.chess_game = ChessGame(
                            self.screen,
                            self.scale,
                            self.desktop_x,
                            self.desktop_y,
                            self.desktop_size,
                            health_monitor_y,
                            self.bbs_x or 0,
                            self.bbs_width or 0,
                            self.get_chess_stats,
                            self.save_chess_stats
                        )
                        self.chess_game.start()
                    except Exception as e:
                        print(f"Failed to initialize ChessGame on demand: {e}")
                        import traceback
                        traceback.print_exc()
        elif icon_name == "solitaire":
            if self.solitaire_game:
                # Calculate health monitor Y position
                health_monitor_y = self.bbs_y + int(10 * self.scale) if self.bbs_y else self.desktop_y + int(10 * self.scale)
                # Update desktop coordinates before starting
                self.solitaire_game.update_desktop(self.desktop_x, self.desktop_y, self.desktop_size, health_monitor_y)
                self.solitaire_game.start()
            else:
                print(f"Solitaire game module not available. _solitaire_available={_solitaire_available}, SolitaireGame={SolitaireGame}, self.solitaire_game={getattr(self, 'solitaire_game', 'NOT SET')}")
                # Try to initialize if it wasn't initialized before
                if _solitaire_available and SolitaireGame:
                    try:
                        health_monitor_y = self.bbs_y + int(10 * self.scale) if self.bbs_y else self.desktop_y + int(10 * self.scale)
                        self.solitaire_game = SolitaireGame(
                            self.screen,
                            self.scale,
                            self.desktop_x,
                            self.desktop_y,
                            self.desktop_size,
                            health_monitor_y,
                            self.bbs_x or 0,
                            self.bbs_width or 0
                        )
                        self.solitaire_game.start()
                    except Exception as e:
                        print(f"Failed to initialize SolitaireGame on demand: {e}")
                        import traceback
                        traceback.print_exc()
        else:
            print(f"{icon_name.title()} is not available yet.")

    def _play_modem_dial_sound(self) -> None:
        if self.modem_dial_sound_playing or not pygame.mixer.get_init():
            return
        try:
            if self.modem_dial_sound is None:
                audio_path = get_data_path("Audio", "dial.wav")
                if os.path.exists(audio_path):
                    self.modem_dial_sound = pygame.mixer.Sound(audio_path)
            if self.modem_dial_sound:
                self.modem_dial_sound.play()
                self.modem_dial_sound_playing = True
        except Exception as e:
            print(f"Warning: Failed to play dial.wav: {e}")
            self.modem_dial_sound = None
            self.modem_dial_sound_playing = False

    def _stop_modem_dial_sound(self) -> None:
        try:
            if self.modem_dial_sound:
                self.modem_dial_sound.stop()
        except Exception:
            pass
        self.modem_dial_sound_playing = False

    def _update_modem_packet_effect(self, dt: float) -> None:
        if not self.modem_terminal_rect or not self.modem_modal_connection_started:
            self.modem_packet_sprites.clear()
            self.modem_wave_phase = 0.0
            return

        self.modem_wave_phase = (self.modem_wave_phase + dt * 2.5) % (math.tau if hasattr(math, "tau") else (math.pi * 2))
        self.modem_packet_spawn_timer += dt
        spawn_interval = max(0.04, 0.12 / max(self.scale, 0.1))
        terminal_left = self.modem_terminal_rect.left + int(8 * self.scale)
        terminal_right = self.modem_terminal_rect.right - int(8 * self.scale)
        terminal_top = self.modem_terminal_rect.top
        terminal_bottom = self.modem_terminal_rect.bottom

        while self.modem_packet_spawn_timer >= spawn_interval:
            self.modem_packet_spawn_timer -= spawn_interval
            packet = {
                "x": random.uniform(terminal_left, terminal_right),
                "y": terminal_top - random.uniform(5, 25),
                "speed": random.uniform(110, 190) * self.scale,
                "length": random.uniform(12, 26) * self.scale,
                "color": random.choice([
                    (0, 255, 200),
                    (255, 80, 200),
                    (0, 200, 255)
                ])
            }
            self.modem_packet_sprites.append(packet)

        survivors = []
        for packet in self.modem_packet_sprites:
            packet["y"] += packet["speed"] * dt
            if packet["y"] < terminal_bottom + packet["length"]:
                survivors.append(packet)
        self.modem_packet_sprites = survivors

    def _draw_modem_packet_effect(self, terminal_rect: pygame.Rect) -> None:
        if not self.modem_modal_connection_started:
            return

        for packet in self.modem_packet_sprites:
            start = (int(packet["x"]), int(packet["y"]))
            end = (int(packet["x"]), int(packet["y"] + packet["length"]))
            pygame.draw.line(self.screen, packet["color"], start, end, 2)

        amplitude = max(int(7 * self.scale), 3)
        wave_colors = [(0, 255, 200), (255, 80, 200)]
        width = terminal_rect.width
        if width <= 1:
            return
        for idx, color in enumerate(wave_colors):
            points = []
            freq = 4 + idx * 2
            for x in range(width):
                norm = x / (width - 1)
                phase = self.modem_wave_phase * (1 + idx * 0.35)
                y = terminal_rect.y + terminal_rect.height / 2 + math.sin(phase + norm * math.pi * freq) * amplitude * (1 + idx * 0.3)
                points.append((terminal_rect.x + x, y))
            if len(points) >= 2:
                pygame.draw.lines(self.screen, color, False, points, 1)

    def _handle_notes_modal_click(self, mouse_x: int, mouse_y: int) -> bool:
        """Handle clicks within the revamped notes modal."""
        modal_w, modal_h = self._get_modal_size("notes")
        modal_w, modal_h = self._clamp_modal_to_desktop(modal_w, modal_h)
        modal_x, modal_y = self.modal_positions.get("notes", (0, 0))

        close_btn_size = int(20 * self.scale)
        close_btn_rect = pygame.Rect(
            modal_x + modal_w - close_btn_size - int(5 * self.scale),
            modal_y + int(5 * self.scale),
            close_btn_size,
            close_btn_size
        )
        if close_btn_rect.collidepoint(mouse_x, mouse_y):
            if self.notes_modal_edit_mode:
                self._exit_notes_edit_mode(save_changes=False)
            self._reset_os_mode()
            return True

        modal_rect = pygame.Rect(modal_x, modal_y, modal_w, modal_h)
        if not modal_rect.collidepoint(mouse_x, mouse_y):
            return False

        notes = self._load_user_notes()
        self._ensure_notes_tab_index(notes)

        # Tabs
        for tab_rect, index in self.notes_modal_hitboxes.get("tabs", []):
            if tab_rect.collidepoint(mouse_x, mouse_y):
                if index >= len(notes):
                    self._create_new_note()
                else:
                    if self.notes_modal_edit_mode:
                        self._exit_notes_edit_mode(save_changes=False)
                    self.notes_modal_current_tab = index
                return True

        # Edit mode interactions
        if self.notes_modal_edit_mode:
            save_btn = self.notes_modal_hitboxes.get("save_button")
            cancel_btn = self.notes_modal_hitboxes.get("cancel_button")
            title_field = self.notes_modal_hitboxes.get("title_field")
            content_field = self.notes_modal_hitboxes.get("content_field")
            format_buttons = self.notes_modal_hitboxes.get("format_buttons", [])

            if save_btn and save_btn.collidepoint(mouse_x, mouse_y):
                self._exit_notes_edit_mode(save_changes=True)
                return True

            if cancel_btn and cancel_btn.collidepoint(mouse_x, mouse_y):
                self._exit_notes_edit_mode(save_changes=False)
                return True

            if title_field and title_field.collidepoint(mouse_x, mouse_y):
                self.notes_modal_edit_field = "title"
                self.notes_modal_cursor_blink_timer = 0.0
                cursor = self._notes_cursor_from_position("title", mouse_x, mouse_y)
                self.notes_modal_title_cursor = cursor
                self.notes_modal_title_selection = (cursor, cursor)
                self.notes_modal_selection_field = "title"
                self.notes_modal_selection_anchor = cursor
                self.notes_modal_dragging_selection = True
                return True

            if content_field and content_field.collidepoint(mouse_x, mouse_y):
                self.notes_modal_edit_field = "content"
                self.notes_modal_cursor_blink_timer = 0.0
                cursor = self._notes_cursor_from_position("content", mouse_x, mouse_y)
                self.notes_modal_content_cursor = cursor
                self.notes_modal_content_selection = (cursor, cursor)
                self.notes_modal_selection_field = "content"
                self.notes_modal_selection_anchor = cursor
                self.notes_modal_dragging_selection = True
                self.notes_modal_content_cursor_aim_x = None
                return True

            for rect, action in format_buttons:
                if rect.collidepoint(mouse_x, mouse_y):
                    self._notes_apply_format_action(action)
                    return True
        else:
            # View mode buttons
            edit_rect = self.notes_modal_hitboxes.get("edit_button")
            delete_rect = self.notes_modal_hitboxes.get("delete_button")

            if edit_rect and edit_rect.collidepoint(mouse_x, mouse_y):
                self._enter_notes_edit_mode(self.notes_modal_current_tab)
                return True

            if delete_rect and delete_rect.collidepoint(mouse_x, mouse_y):
                self._delete_note_at_index(self.notes_modal_current_tab)
                return True

        return False
    
    
    def _start_tape_video(self):
        """Start playing the Datasette_Load.mp4 video with chroma key."""
        if not _cv2_available:
            print("Warning: cv2 not available, cannot play video")
            return
        
        if self.tape_modal_video_playing:
            return  # Already playing
        
        # Don't restart if video has already completed
        if self.tape_modal_video_completed:
            return
        
        video_path = get_data_path("OS", "Datasette_Load.mp4")
        if not os.path.exists(video_path):
            print(f"Warning: Video file not found: {video_path}")
            return
        
        try:
            self.tape_modal_video_cap = cv2.VideoCapture(video_path)
            if not self.tape_modal_video_cap.isOpened():
                print(f"Warning: Could not open video: {video_path}")
                return
            
            # Get video properties
            fps = self.tape_modal_video_cap.get(cv2.CAP_PROP_FPS)
            width = int(self.tape_modal_video_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.tape_modal_video_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self.tape_modal_video_original_size = (width, height)
            
            # Set target FPS for video playback throttling (to prevent lag when games are running)
            self.tape_modal_video_target_fps = fps if fps > 0 else 30.0
            self.tape_modal_video_last_frame_time = time.time()
            
            # Calculate display size maintaining aspect ratio
            # Target area: documentation viewer area (doubled)
            target_w = int(800 * self.scale * 2)  # Doubled docs viewer width
            target_h = int(600 * self.scale * 2)  # Doubled docs viewer height
            
            # Calculate aspect ratios
            video_aspect = width / height
            target_aspect = target_w / target_h
            
            # Scale to fit within target area while maintaining aspect ratio
            if video_aspect > target_aspect:
                # Video is wider - fit to width
                display_w = target_w
                display_h = int(target_w / video_aspect)
            else:
                # Video is taller - fit to height
                display_h = target_h
                display_w = int(target_h * video_aspect)
            
            self.tape_modal_video_display_size = (display_w, display_h)
            
            # Initialize fade state
            self.tape_modal_video_fade_state = "fade_in"
            self.tape_modal_video_fade_alpha = 0.0
            self.tape_modal_video_fade_timer = 0.0
            
            # Play audio from video file using pygame mixer
            # Note: cv2 doesn't handle audio, so we need a separate audio file
            # Try common audio formats
            audio_extensions = ['.wav', '.mp3', '.ogg']
            audio_loaded = False
            for ext in audio_extensions:
                audio_path = video_path.replace('.mp4', ext)
                if os.path.exists(audio_path):
                    try:
                        # Use pygame.mixer.music for longer audio files
                        pygame.mixer.music.load(audio_path)
                        pygame.mixer.music.play(0)  # Play once, don't loop
                        audio_loaded = True
                        break
                    except Exception as e:
                        print(f"Warning: Could not load audio file {audio_path}: {e}")
                        continue
            
            if not audio_loaded:
                print(f"Warning: Audio file not found for {video_path}. Video will play without sound.")
                print("  Expected audio file: Datasette_Load.wav, Datasette_Load.mp3, or Datasette_Load.ogg")
            
            self.tape_modal_video_playing = True
        except Exception as e:
            print(f"Warning: Failed to start video: {e}")
            self._stop_tape_video()
    
    def _stop_tape_video(self):
        """Stop playing the tape video."""
        self.tape_modal_video_playing = False
        if self.tape_modal_video_cap:
            self.tape_modal_video_cap.release()
            self.tape_modal_video_cap = None
        self.tape_modal_video_frame = None
        # Stop audio playback
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
        self.tape_modal_video_audio_channel = None
        # Reset fade state
        self.tape_modal_video_fade_state = "none"
        self.tape_modal_video_fade_alpha = 0.0
        self.tape_modal_video_fade_timer = 0.0
    
    def _mark_video_completed(self):
        """Mark the video as completed to prevent looping."""
        self.tape_modal_video_completed = True
        self._stop_tape_video()
    
    def _apply_chroma_key(self, frame):
        """Apply chroma key to remove green (#00FF00) from frame with improved edge removal."""
        if frame is None or not _cv2_available:
            return None
        
        # Convert BGR to RGB (cv2 uses BGR, pygame uses RGB)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Convert to HSV for better color matching
        frame_hsv = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2HSV)
        
        # Define green color (#00FF00) in HSV
        # Pure green in HSV: H=120, S=255, V=255
        # Use wider range for better edge removal
        green_lower_hsv = np.array([50, 50, 50], dtype=np.uint8)   # Lower bound for green hue
        green_upper_hsv = np.array([80, 255, 255], dtype=np.uint8)  # Upper bound for green hue
        
        # Create mask for green pixels in HSV space
        mask_hsv = cv2.inRange(frame_hsv, green_lower_hsv, green_upper_hsv)
        
        # Also check RGB space for pure green (#00FF00)
        green_lower_rgb = np.array([0, 200, 0], dtype=np.uint8)
        green_upper_rgb = np.array([50, 255, 50], dtype=np.uint8)
        mask_rgb = cv2.inRange(frame_rgb, green_lower_rgb, green_upper_rgb)
        
        # Combine both masks
        mask = cv2.bitwise_or(mask_hsv, mask_rgb)
        
        # Apply morphological operations to clean up edges
        kernel = np.ones((3, 3), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)  # Close small holes
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)   # Remove small noise
        
        # Apply Gaussian blur for smoother edges
        mask = cv2.GaussianBlur(mask, (7, 7), 2)
        
        # Expand the mask slightly to remove edge artifacts
        mask = cv2.dilate(mask, kernel, iterations=1)
        
        # Invert mask (we want to keep non-green pixels)
        mask_inv = cv2.bitwise_not(mask)
        
        # Create alpha channel: 255 for non-green pixels, 0 for green pixels
        alpha = mask_inv
        
        # Combine RGB with alpha
        frame_rgba = np.dstack((frame_rgb, alpha))
        
        return frame_rgba
    
    def update(self, dt: float):
        """Update OS Mode state (call this every frame)."""
        # Update cursor blink timer for notes modal
        if "notes" in self.active_modals and self.notes_modal_edit_mode:
            self.notes_modal_cursor_blink_timer += dt
            if self.notes_modal_cursor_blink_timer > 1.0:
                self.notes_modal_cursor_blink_timer = 0.0
        
        # Stop video if modal is closed (but keep recording flag)
        if "tape" not in self.active_modals and self.tape_modal_video_playing:
            self._stop_tape_video()
        
        # Update terminal message timer for delayed messages
        if "tape" in self.active_modals and self.tape_modal_video_playing:
            self.tape_modal_message_timer += dt
            # Show "YOU MAY CLOSE THE WINDOW" after 3 seconds (a couple of beats)
            if self.tape_modal_message_timer >= 3.0 and len(self.tape_modal_terminal_lines) == 2:
                self.tape_modal_terminal_lines.append("YOU MAY CLOSE THE WINDOW")
                self.tape_modal_terminal_text = "\n".join(self.tape_modal_terminal_lines)
        
        # Update modem modal connection messages and FX
        if "modem" in self.active_modals and self.modem_modal_connection_started and self.modem_modal_connection_messages:
            self.modem_modal_message_timer += dt
            message_delay = 1.4  # Show each message for ~1.4 seconds
            
            # Progress through messages
            if self.modem_modal_message_index < len(self.modem_modal_connection_messages):
                if self.modem_modal_message_timer >= message_delay:
                    self.modem_modal_message_index += 1
                    self.modem_modal_message_timer = 0.0
                    if self.modem_modal_message_index >= len(self.modem_modal_connection_messages):
                        self.modem_modal_should_reset_bbs = True
                        self.modem_modal_should_exit_os = True
                        if self.reset_bbs_callback:
                            self.reset_bbs_callback()
            if len(self.modem_modal_connection_messages) >= 2 and not self.network_connected:
                if self.modem_modal_message_index >= len(self.modem_modal_connection_messages) - 2:
                    self.network_connected = True
            self._update_modem_packet_effect(dt)
        else:
            self.modem_packet_sprites.clear()
            self.modem_wave_phase = 0.0
        
        # Update fade state
        if self.tape_modal_video_fade_state == "fade_in":
            self.tape_modal_video_fade_timer += dt
            if self.tape_modal_video_fade_timer >= self.tape_modal_video_fade_duration:
                self.tape_modal_video_fade_alpha = 1.0
                self.tape_modal_video_fade_state = "playing"
            else:
                self.tape_modal_video_fade_alpha = min(1.0, self.tape_modal_video_fade_timer / self.tape_modal_video_fade_duration)
        elif self.tape_modal_video_fade_state == "fade_out":
            self.tape_modal_video_fade_timer += dt
            if self.tape_modal_video_fade_timer >= self.tape_modal_video_fade_duration:
                self.tape_modal_video_fade_alpha = 0.0
                self._stop_tape_video()
            else:
                self.tape_modal_video_fade_alpha = max(0.0, 1.0 - (self.tape_modal_video_fade_timer / self.tape_modal_video_fade_duration))
        
        # Update video playback (throttled to video FPS to avoid lag)
        if self.tape_modal_video_playing and self.tape_modal_video_cap:
            # Check if video has ended (for fade out)
            total_frames = int(self.tape_modal_video_cap.get(cv2.CAP_PROP_FRAME_COUNT))
            current_frame = int(self.tape_modal_video_cap.get(cv2.CAP_PROP_POS_FRAMES))
            
            # Start fade out near the end of video
            if self.tape_modal_video_fade_state == "playing" and total_frames > 0:
                frames_until_end = total_frames - current_frame
                fps = self.tape_modal_video_cap.get(cv2.CAP_PROP_FPS)
                if fps > 0:
                    seconds_until_end = frames_until_end / fps
                    if seconds_until_end <= self.tape_modal_video_fade_duration:
                        self.tape_modal_video_fade_state = "fade_out"
                        self.tape_modal_video_fade_timer = 0.0
            
            # Only read frames if not fading out after video ended
            # Throttle frame reading to match video FPS (prevents lag when games are running)
            current_time = time.time()
            time_since_last_frame = current_time - self.tape_modal_video_last_frame_time
            frame_interval = 1.0 / self.tape_modal_video_target_fps if self.tape_modal_video_target_fps > 0 else 1.0 / 30.0
            
            # Only read a new frame if enough time has passed (throttle to video FPS)
            should_read_frame = (time_since_last_frame >= frame_interval) or (self.tape_modal_video_frame is None)
            
            if should_read_frame and (self.tape_modal_video_fade_state != "fade_out" or self.tape_modal_video_frame is not None):
                ret, frame = self.tape_modal_video_cap.read()
                if ret:
                    # Update last frame time
                    self.tape_modal_video_last_frame_time = current_time
                    # Apply chroma key
                    frame_rgba = self._apply_chroma_key(frame)
                    if frame_rgba is not None:
                        # Resize frame maintaining aspect ratio
                        if self.tape_modal_video_display_size:
                            frame_resized = cv2.resize(frame_rgba, self.tape_modal_video_display_size, interpolation=cv2.INTER_LINEAR)
                        else:
                            frame_resized = frame_rgba
                        
                        # Convert RGBA numpy array to pygame surface
                        height, width = frame_resized.shape[:2]
                        
                        # Ensure values are in correct range (0-255) and correct dtype
                        frame_resized = np.clip(frame_resized, 0, 255).astype(np.uint8)
                        
                        # Extract RGB and alpha channels
                        rgb_data = frame_resized[:, :, :3]  # RGB channels (height, width, 3)
                        alpha_data = frame_resized[:, :, 3]  # Alpha channel (height, width)
                        
                        # Apply fade alpha to the alpha channel
                        alpha_data = (alpha_data * self.tape_modal_video_fade_alpha).astype(np.uint8)
                        
                        # Swap axes for pygame (pygame expects (width, height, channels))
                        rgb_swapped = np.swapaxes(rgb_data, 0, 1)  # (width, height, 3)
                        
                        # Create RGB surface
                        frame_surface = pygame.surfarray.make_surface(rgb_swapped)
                        
                        # Convert to alpha surface
                        frame_surface = frame_surface.convert_alpha()
                        
                        # Set alpha channel (with fade applied)
                        alpha_swapped = np.swapaxes(alpha_data, 0, 1)  # (width, height)
                        alpha_array = pygame.surfarray.pixels_alpha(frame_surface)
                        alpha_array[:] = alpha_swapped
                        del alpha_array  # Release the array lock
                        
                        self.tape_modal_video_frame = frame_surface
                else:
                    # Video ended - start fade out if not already fading
                    if self.tape_modal_video_fade_state == "playing":
                        self.tape_modal_video_fade_state = "fade_out"
                        self.tape_modal_video_fade_timer = 0.0
            
            # Check if fade out is complete
            if self.tape_modal_video_fade_state == "fade_out" and self.tape_modal_video_fade_alpha <= 0.0:
                # Fade out complete, mark video as completed and stop
                self._mark_video_completed()
    
    def draw(self):
        """Draw the OS Mode desktop environment."""
        if not self.desktop_image:
            return
        
        # Draw desktop background
        self.screen.blit(self.desktop_image, (self.desktop_x, self.desktop_y))
        
        # Draw icons (use selected "S" version if selected, otherwise normal version)
        for icon in self.icons:
            # Use S version if selected, otherwise normal version
            icon_to_draw = icon["s_image"] if icon["selected"] else icon["image"]
            self.screen.blit(icon_to_draw, (icon["x"], icon["y"]))
        
        # Draw clock (on same layer as icons, before modals)
        self._draw_clock()
        
        # Draw all active modals (in order they were opened)
        for modal_name in list(self.active_modals):
            if modal_name == "tape":
                self._draw_tape_modal()
            elif modal_name == "modem":
                self._draw_modem_modal()
            elif modal_name == "notes":
                self._draw_notes_modal()
            elif modal_name == "games":
                self._draw_games_modal()

        if self.chess_game and self.chess_game.active:
            self.chess_game.draw()
        if self.solitaire_game and self.solitaire_game.active:
            self.solitaire_game.draw()
    
    def _draw_tape_modal(self):
        """Draw the tape icon modal."""
        # Modal dimensions (scaled)
        modal_w = int(800 * self.scale)
        modal_h = int(500 * self.scale) + self.modal_title_bar_height
        
        # Clamp modal to fit within desktop boundaries
        modal_w, modal_h = self._clamp_modal_to_desktop(modal_w, modal_h)
        
        # Get position from stored position or calculate new one
        modal_x, modal_y = self.modal_positions.get("tape", self._get_modal_position(modal_w, modal_h, "tape"))
        if "tape" not in self.modal_positions:
            self.modal_positions["tape"] = (modal_x, modal_y)
        
        # Draw modal background (dark blue/black with border)
        modal_rect = pygame.Rect(modal_x, modal_y, modal_w, modal_h)
        pygame.draw.rect(self.screen, COLOR_BG_DARK, modal_rect)
        pygame.draw.rect(self.screen, COLOR_CYAN, modal_rect, 2)  # Cyan border
        
        # Draw title bar
        title_bar_rect = pygame.Rect(modal_x, modal_y, modal_w, self.modal_title_bar_height)
        pygame.draw.rect(self.screen, COLOR_BG_TITLE, title_bar_rect)
        pygame.draw.rect(self.screen, COLOR_CYAN, title_bar_rect, 1)  # Cyan border
        
        # Draw title text
        try:
            font_size = max(int(16 * self.scale), 12)
            title_font = pygame.font.Font(None, font_size)
            title_text = title_font.render("DATASETTE MONITOR", True, COLOR_CYAN)
            self.screen.blit(title_text, (modal_x + int(10 * self.scale), modal_y + int(5 * self.scale)))
        except Exception:
            pass
        
        # Draw close button in title bar with hover effect
        close_btn_size = int(20 * self.scale)
        close_btn_x = modal_x + modal_w - close_btn_size - int(5 * self.scale)
        close_btn_y = modal_y + int(5 * self.scale)
        close_btn_rect = pygame.Rect(close_btn_x, close_btn_y, close_btn_size, close_btn_size)
        is_hovered = self.hovered_button == ("tape", "title_close")
        close_color = COLOR_RED if is_hovered else COLOR_RED_DARK
        pygame.draw.rect(self.screen, close_color, close_btn_rect)
        pygame.draw.rect(self.screen, COLOR_RED, close_btn_rect, 2 if is_hovered else 1)
        try:
            close_font = pygame.font.Font(None, max(int(14 * self.scale), 10))
            close_text = close_font.render("X", True, COLOR_WHITE)
            close_text_rect = close_text.get_rect(center=close_btn_rect.center)
            self.screen.blit(close_text, close_text_rect)
        except Exception:
            pass
        
        # Draw terminal window (below title bar) - smaller and closer to buttons
        terminal_x = modal_x + int(20 * self.scale)
        terminal_y = modal_y + self.modal_title_bar_height + int(20 * self.scale)
        terminal_w = modal_w - int(40 * self.scale)
        terminal_h = int(180 * self.scale)  # Smaller terminal height
        
        terminal_rect = pygame.Rect(terminal_x, terminal_y, terminal_w, terminal_h)
        pygame.draw.rect(self.screen, COLOR_BLACK, terminal_rect)
        pygame.draw.rect(self.screen, COLOR_CYAN, terminal_rect, 1)  # Cyan border
        
        # Draw terminal text (multi-line support) - larger font
        if self.tape_modal_terminal_lines:
            # Create a simple font for terminal text - larger size
            try:
                font_size = max(int(22 * self.scale), 18)  # Increased from 16 to 22
                terminal_font = pygame.font.Font(None, font_size)
                text_x = terminal_x + int(10 * self.scale)
                text_y = terminal_y + int(10 * self.scale)
                line_height = int(26 * self.scale)  # Increased from 20 to 26
                
                # Draw each line
                for line in self.tape_modal_terminal_lines:
                    if line:  # Only draw non-empty lines
                        text_surface = terminal_font.render(line, True, COLOR_GREEN)  # Green text
                        self.screen.blit(text_surface, (text_x, text_y))
                        text_y += line_height
            except Exception:
                pass
        
        # Draw recording status and timer
        is_recording, recording_start_time = self.get_recording_state()
        if is_recording and recording_start_time:
            try:
                import time
                # Calculate elapsed time from the saved start timestamp
                current_time = time.time()
                recording_duration = current_time - recording_start_time
                hours = int(recording_duration // 3600)
                minutes = int((recording_duration % 3600) // 60)
                seconds = int(recording_duration % 60)
                timer_text = f"RECORDING TIME: {hours:02d}:{minutes:02d}:{seconds:02d}"
                
                status_font_size = max(int(18 * self.scale), 14)
                status_font = pygame.font.Font(None, status_font_size)
                
                # Status text (red for recording)
                status_text = "Status: RECORDING"
                status_surface = status_font.render(status_text, True, COLOR_RED)
                timer_surface = status_font.render(timer_text, True, COLOR_CYAN)
                
                # Position status and timer below terminal
                status_x = terminal_x
                status_y = terminal_y + terminal_h + int(15 * self.scale)
                timer_y = status_y + status_surface.get_height() + int(5 * self.scale)
                
                self.screen.blit(status_surface, (status_x, status_y))
                self.screen.blit(timer_surface, (status_x, timer_y))
            except Exception:
                pass
        
        # Draw buttons (below terminal, closer and centered)
        button_y = modal_y + self.modal_title_bar_height + int(220 * self.scale)  # Closer to terminal
        button_h = int(35 * self.scale)
        button_w = int(140 * self.scale)
        button_spacing = int(15 * self.scale)
        
        # Calculate total width of buttons and spacing for centering
        total_buttons_width = 2 * button_w + button_spacing  # Two buttons (LOAD and RECORD)
        buttons_start_x = modal_x + (modal_w - total_buttons_width) // 2  # Center align
        
        # LOAD DATA button
        load_btn_x = buttons_start_x
        load_btn_rect = pygame.Rect(load_btn_x, button_y, button_w, button_h)
        is_hovered = self.hovered_button == ("tape", "load")
        btn_color = COLOR_BUTTON_HOVER if is_hovered else COLOR_BG_TITLE
        pygame.draw.rect(self.screen, btn_color, load_btn_rect)
        pygame.draw.rect(self.screen, COLOR_CYAN, load_btn_rect, 2 if is_hovered else 1)
        try:
            font_size = max(int(14 * self.scale), 10)
            button_font = pygame.font.Font(None, font_size)
            load_text = button_font.render("LOAD DATA", True, COLOR_CYAN)
            load_text_rect = load_text.get_rect(center=load_btn_rect.center)
            self.screen.blit(load_text, load_text_rect)
        except Exception:
            pass
        
        # RECORD DATA button
        record_btn_x = load_btn_x + button_w + button_spacing
        record_btn_rect = pygame.Rect(record_btn_x, button_y, button_w, button_h)
        is_hovered = self.hovered_button == ("tape", "record")
        btn_color = COLOR_BUTTON_HOVER if is_hovered else COLOR_BG_TITLE
        pygame.draw.rect(self.screen, btn_color, record_btn_rect)
        pygame.draw.rect(self.screen, COLOR_CYAN, record_btn_rect, 2 if is_hovered else 1)
        try:
            record_text = button_font.render("RECORD DATA", True, COLOR_CYAN)
            record_text_rect = record_text.get_rect(center=record_btn_rect.center)
            self.screen.blit(record_text, record_text_rect)
        except Exception:
            pass
        
        # Draw video if playing (at specified Datasette position)
        if self.tape_modal_video_playing and self.tape_modal_video_frame:
            # Render from baseline coordinates (1363, 44)
            video_x = int(self.datasette_baseline_x * self.scale)
            video_y = int(self.datasette_baseline_y * self.scale)
            
            # Move video 50px to the right (scaled)
            video_x += int(50 * self.scale)
            
            # Draw with fade alpha already applied in the surface
            self.screen.blit(self.tape_modal_video_frame, (video_x, video_y))
    
    def _draw_clock(self):
        """Draw the BRADSONIC 69000 Health Monitor in OS mode."""
        if self.bbs_x is None or self.bbs_y is None or self.bbs_width is None:
            return
        
        # Create font for monitor using system font (scaled)
        try:
            title_font_size = max(int(12 * self.scale), 10)
            status_font_size = max(int(11 * self.scale), 9)
            # Use system font - try common system fonts, fallback to default
            title_font = None
            status_font = None
            system_fonts = ["Segoe UI", "Arial", "Helvetica", None]
            for font_name in system_fonts:
                try:
                    if title_font is None:
                        title_font = pygame.font.SysFont(font_name, title_font_size)
                    if status_font is None:
                        status_font = pygame.font.SysFont(font_name, status_font_size)
                    if title_font and status_font:
                        break
                except Exception:
                    continue
            if title_font is None:
                title_font = pygame.font.SysFont(None, title_font_size)
            if status_font is None:
                status_font = pygame.font.SysFont(None, status_font_size)
        except Exception:
            return
        
        # Format clock as hh:mm:ss mm-dd-yyyy
        now = datetime.now()
        clock_text = now.strftime("%H:%M:%S %m-%d-%Y")
        
        # Check LAPC-1 Soundcard status (check for AUDIO_ON token which means all 7 nodes complete)
        lapc1_activated = self.has_token("AUDIO_ON")
        lapc1_status = "ACTIVATED" if lapc1_activated else "INACTIVE"
        
        # Check if tape is recording (from user profile)
        is_recording, recording_start_time = self.get_recording_state()
        datasette_status = "RECORDING" if is_recording else "DETECTED"
        datasette_status_color = COLOR_CORAL if is_recording else COLOR_GREEN
        
        # Network status
        if self.network_connected:
            network_status = "CONNECTED"
            network_color = COLOR_NEON_GREEN
        else:
            network_status = "DISCONNECTED"
            network_color = COLOR_GREY
        
        # Title text (white)
        title_text = "BRADSONIC 69000 Health Monitor"
        title_surface = title_font.render(title_text, True, COLOR_WHITE)
        
        # Status lines - we'll render them with different colors
        status_label = "STATUS:"
        status_label_surface = status_font.render(status_label, True, COLOR_WHITE)
        
        # Build status items with proper colors (in order: System, HardDisk, LAPC-1 Soundcard, Datasette, Network)
        # System: label in cyan, value in green
        system_label = "  System: "
        system_label_surface = status_font.render(system_label, True, COLOR_CYAN)
        system_value_surface = status_font.render("OPERATIONAL", True, COLOR_GREEN)
        
        # HardDisk: label in cyan, first value in red, second value in green
        harddisk_label = "  HardDisk: "
        harddisk_label_surface = status_font.render(harddisk_label, True, COLOR_CYAN)
        harddisk_used = "50mb"
        harddisk_used_surface = status_font.render(harddisk_used, True, COLOR_RED)
        harddisk_free = "/50mb"
        harddisk_free_surface = status_font.render(harddisk_free, True, COLOR_GREEN)
        
        # LAPC-1: label in cyan, status in red if inactive, green if activated
        lapc1_label = "  LAPC-1 Soundcard: "
        lapc1_label_surface = status_font.render(lapc1_label, True, COLOR_CYAN)
        lapc1_status_color = COLOR_GREEN if lapc1_activated else COLOR_RED
        lapc1_status_surface = status_font.render(lapc1_status, True, lapc1_status_color)
        
        # Datasette: label in cyan, status in green (DETECTED) or coral (RECORDING)
        datasette_label = "  Datasette: "
        datasette_label_surface = status_font.render(datasette_label, True, COLOR_CYAN)
        datasette_status_surface = status_font.render(datasette_status, True, datasette_status_color)
        
        # Network: label in cyan, value in grey (DISCONNECTED)
        network_label = "  Network: "
        network_label_surface = status_font.render(network_label, True, COLOR_CYAN)
        network_value_surface = status_font.render(network_status, True, network_color)
        
        # Calculate max width (in order: System, HardDisk, LAPC-1, Datasette, Network)
        max_width = max(
            title_surface.get_width(),
            status_label_surface.get_width(),
            system_label_surface.get_width() + system_value_surface.get_width(),
            harddisk_label_surface.get_width() + harddisk_used_surface.get_width() + harddisk_free_surface.get_width(),
            lapc1_label_surface.get_width() + lapc1_status_surface.get_width(),
            datasette_label_surface.get_width() + datasette_status_surface.get_width(),
            network_label_surface.get_width() + network_value_surface.get_width()
        )
        
        # Calculate heights
        line_height = status_font.get_height() + int(2 * self.scale)
        title_bar_height = int(22 * self.scale)
        time_bar_height = int(20 * self.scale)
        box_padding = int(12 * self.scale)
        
        # Content height (status lines in order: System, HardDisk, LAPC-1, Datasette, Network)
        content_height = (
            status_label_surface.get_height() + int(4 * self.scale) +  # Status label + spacing
            line_height +  # System
            line_height +  # HardDisk
            line_height +  # LAPC-1
            line_height +  # Datasette
            line_height +  # Network
            int(20 * self.scale) +  # Padding under Network status (20px)
            int(4 * self.scale)  # Extra spacing before time bar
        )
        
        box_width = max_width + 2 * box_padding
        box_height = title_bar_height + content_height + time_bar_height
        
        # Calculate position (same as BBS clock: top-right of BBS window, moved 89px to the right)
        padding = int(20 * self.scale)
        offset_right = int(89 * self.scale)  # Move 89px to the right (111px - 22px = 89px)
        box_x = self.bbs_x + self.bbs_width - box_width - padding + offset_right
        box_y = self.bbs_y + int(10 * self.scale)
        
        # Draw box (on same layer as icons)
        box_rect = pygame.Rect(box_x, box_y, box_width, box_height)
        pygame.draw.rect(self.screen, COLOR_BG_DARK, box_rect)
        pygame.draw.rect(self.screen, COLOR_CYAN, box_rect, 2)  # Cyan border
        
        # Draw title bar
        title_bar_rect = pygame.Rect(box_x, box_y, box_width, title_bar_height)
        pygame.draw.rect(self.screen, COLOR_BG_TITLE, title_bar_rect)
        pygame.draw.line(self.screen, COLOR_CYAN, (box_x, box_y + title_bar_height), 
                        (box_x + box_width, box_y + title_bar_height), 1)
        
        # Draw title text in title bar (centered, white)
        title_x = box_x + (box_width - title_surface.get_width()) // 2
        title_y = box_y + (title_bar_height - title_surface.get_height()) // 2
        self.screen.blit(title_surface, (title_x, title_y))
        
        # Draw status lines
        text_x = box_x + box_padding
        text_y = box_y + title_bar_height + int(6 * self.scale)
        
        # Status label (white)
        self.screen.blit(status_label_surface, (text_x, text_y))
        text_y += status_label_surface.get_height() + int(4 * self.scale)
        
        # System (label cyan, value green) - First
        self.screen.blit(system_label_surface, (text_x, text_y))
        system_value_x = text_x + system_label_surface.get_width()
        self.screen.blit(system_value_surface, (system_value_x, text_y))
        text_y += line_height
        
        # HardDisk (label cyan, used red, free green) - Second
        self.screen.blit(harddisk_label_surface, (text_x, text_y))
        harddisk_used_x = text_x + harddisk_label_surface.get_width()
        self.screen.blit(harddisk_used_surface, (harddisk_used_x, text_y))
        harddisk_free_x = harddisk_used_x + harddisk_used_surface.get_width()
        self.screen.blit(harddisk_free_surface, (harddisk_free_x, text_y))
        text_y += line_height
        
        # LAPC-1 Soundcard (label cyan, status red/green) - Third
        self.screen.blit(lapc1_label_surface, (text_x, text_y))
        lapc1_status_x = text_x + lapc1_label_surface.get_width()
        self.screen.blit(lapc1_status_surface, (lapc1_status_x, text_y))
        text_y += line_height
        
        # Datasette (label cyan, status green/coral) - Fourth
        self.screen.blit(datasette_label_surface, (text_x, text_y))
        datasette_status_x = text_x + datasette_label_surface.get_width()
        self.screen.blit(datasette_status_surface, (datasette_status_x, text_y))
        text_y += line_height
        
        # Network (label cyan, value grey) - Fifth
        self.screen.blit(network_label_surface, (text_x, text_y))
        network_value_x = text_x + network_label_surface.get_width()
        self.screen.blit(network_value_surface, (network_value_x, text_y))
        text_y += int(4 * self.scale)
        
        # Draw time bar at bottom (similar shaded section as title)
        time_bar_y = box_y + box_height - time_bar_height
        time_bar_rect = pygame.Rect(box_x, time_bar_y, box_width, time_bar_height)
        pygame.draw.rect(self.screen, COLOR_BG_TITLE, time_bar_rect)
        pygame.draw.line(self.screen, COLOR_CYAN, (box_x, time_bar_y), 
                        (box_x + box_width, time_bar_y), 1)
        
        # Draw time text (cyan)
        time_text = f"Time: {clock_text}"
        time_surface = status_font.render(time_text, True, COLOR_CYAN)
        time_x = box_x + box_padding
        time_y = time_bar_y + (time_bar_height - time_surface.get_height()) // 2
        self.screen.blit(time_surface, (time_x, time_y))
    
    def draw_scanline(self):
        """Draw the desktop scanline overlay."""
        if self.desktop_scanline_image:
            self.screen.blit(self.desktop_scanline_image, (self.desktop_x, self.desktop_y))
    
    def _get_modem_layout_metrics(self) -> Dict[str, int]:
        button_size = int(58 * self.scale)
        button_spacing = int(12 * self.scale)
        gap = int(24 * self.scale)
        terminal_h = int(170 * self.scale)
        spacing = int(24 * self.scale)
        call_btn_h = int(40 * self.scale)
        dial_pad_h = 4 * button_size + 3 * button_spacing
        modal_w = 3 * button_size + 2 * button_spacing + 2 * gap
        modal_h = (
            self.modal_title_bar_height
            + gap
            + terminal_h
            + spacing
            + dial_pad_h
            + spacing
            + call_btn_h
            + gap
        )
        return {
            "button_size": button_size,
            "button_spacing": button_spacing,
            "gap": gap,
            "terminal_h": terminal_h,
            "spacing": spacing,
            "call_btn_h": call_btn_h,
            "dial_pad_h": dial_pad_h,
            "modal_w": modal_w,
            "modal_h": modal_h,
        }
    
    def _draw_modem_modal(self):
        """Draw the modem icon modal with telephone dial."""
        layout = self._get_modem_layout_metrics()
        button_size = layout["button_size"]
        button_spacing = layout["button_spacing"]
        gap = layout["gap"]
        terminal_h = layout["terminal_h"]
        dial_pad_h = layout["dial_pad_h"]
        call_btn_h = layout["call_btn_h"]
        spacing = layout["spacing"]
        modal_w = layout["modal_w"]
        modal_h = layout["modal_h"]
        
        # Clamp modal to fit within desktop boundaries
        modal_w, modal_h = self._clamp_modal_to_desktop(modal_w, modal_h)
        modal_x, modal_y = self.modal_positions.get("modem", self._get_modal_position(modal_w, modal_h, "modem"))
        if "modem" not in self.modal_positions:
            self.modal_positions["modem"] = (modal_x, modal_y)
        
        # Draw modal background with a subtle neon gradient
        modal_rect = pygame.Rect(modal_x, modal_y, modal_w, modal_h)
        pygame.draw.rect(self.screen, COLOR_DEEP_BLUE, modal_rect)
        pygame.draw.rect(self.screen, COLOR_CYAN, modal_rect, 2)  # Cyan border
        gradient_surface = pygame.Surface((modal_w, modal_h), pygame.SRCALPHA)
        for i in range(modal_h):
            mix = i / max(modal_h - 1, 1)
            gradient_color = (int(15 + 40 * mix), int(35 + 80 * mix), int(90 + 120 * mix), 70)
            pygame.draw.line(gradient_surface, gradient_color, (0, i), (modal_w, i))
        self.screen.blit(gradient_surface, (modal_x, modal_y))
        
        # Draw title bar
        title_bar_rect = pygame.Rect(modal_x, modal_y, modal_w, self.modal_title_bar_height)
        pygame.draw.rect(self.screen, COLOR_BG_TITLE, title_bar_rect)
        pygame.draw.rect(self.screen, COLOR_CYAN, title_bar_rect, 1)  # Cyan border
        
        # Draw title text and subtitle
        try:
            font_size = max(int(16 * self.scale), 12)
            subtitle_size = max(int(11 * self.scale), 9)
            title_font = pygame.font.Font(None, font_size)
            subtitle_font = pygame.font.Font(None, subtitle_size)
            title_text = title_font.render("BRADSONIC NETLINK 69000", True, COLOR_WHITE)
            subtitle_text = subtitle_font.render("RetroSecure Dialer // 1989", True, COLOR_CYAN)
            title_pos = (modal_x + int(10 * self.scale), modal_y + int(3 * self.scale))
            subtitle_pos = (modal_x + int(12 * self.scale), modal_y + int(18 * self.scale))
            self.screen.blit(title_text, title_pos)
            self.screen.blit(subtitle_text, subtitle_pos)
        except Exception:
            pass
        
        # Draw close button in title bar with hover effect
        close_btn_size = int(20 * self.scale)
        close_btn_x = modal_x + modal_w - close_btn_size - int(5 * self.scale)
        close_btn_y = modal_y + int(5 * self.scale)
        close_btn_rect = pygame.Rect(close_btn_x, close_btn_y, close_btn_size, close_btn_size)
        is_hovered = self.hovered_button == ("modem", "title_close")
        close_color = COLOR_RED if is_hovered else COLOR_RED_DARK
        pygame.draw.rect(self.screen, close_color, close_btn_rect)
        pygame.draw.rect(self.screen, COLOR_RED, close_btn_rect, 2 if is_hovered else 1)
        try:
            close_font = pygame.font.Font(None, max(int(14 * self.scale), 10))
            close_text = close_font.render("X", True, COLOR_WHITE)
            close_text_rect = close_text.get_rect(center=close_btn_rect.center)
            self.screen.blit(close_text, close_text_rect)
        except Exception:
            pass
        
        # Draw terminal window (below title bar)
        terminal_x = modal_x + gap
        terminal_y = modal_y + self.modal_title_bar_height + gap
        terminal_w = modal_w - 2 * gap
        terminal_rect = pygame.Rect(terminal_x, terminal_y, terminal_w, terminal_h)
        pygame.draw.rect(self.screen, (5, 10, 25), terminal_rect)
        pygame.draw.rect(self.screen, COLOR_CYAN, terminal_rect, 1)  # Cyan border
        self.modem_terminal_rect = terminal_rect
        
        # Draw terminal text
        try:
            font_size = max(int(17 * self.scale), 14)
            terminal_font = pygame.font.Font(None, font_size)
            text_x = terminal_x + int(10 * self.scale)
            text_y = terminal_y + int(10 * self.scale)
            line_height = int(22 * self.scale)
            
            lines_to_render: List[str] = []
            if self.modem_modal_connection_started and self.modem_modal_connection_messages:
                visible = min(self.modem_modal_message_index + 1, len(self.modem_modal_connection_messages))
                lines_to_render = self.modem_modal_connection_messages[:visible]
            elif self.modem_modal_dialed_sequence:
                lines_to_render = [
                    "READY FOR INPUT...",
                    f"Dialed: {self.modem_modal_dialed_sequence}",
                    "Press CALL to attempt handshake."
                ]
            else:
                lines_to_render = [
                    "READY FOR INPUT...",
                    "Dial Sequence:",
                    "Awaiting user input..."
                ]
            
            for i, line in enumerate(lines_to_render):
                if not line:
                    continue
                color = self.modem_terminal_palette[i % len(self.modem_terminal_palette)]
                text_surface = terminal_font.render(line, True, color)
                self.screen.blit(text_surface, (text_x, text_y))
                text_y += line_height
        except Exception:
            pass
        
        if self.modem_modal_connection_started:
            self._draw_modem_packet_effect(terminal_rect)
            status_font = pygame.font.Font(None, max(int(14 * self.scale), 11))
            status_text = status_font.render("Link Negotiation...", True, COLOR_NEON_GREEN)
            self.screen.blit(status_text, (terminal_x, terminal_y + terminal_h - status_font.get_height() - int(6 * self.scale)))
        else:
            status_font = pygame.font.Font(None, max(int(14 * self.scale), 11))
            status_text = status_font.render("  Awaiting CALL command.", True, COLOR_TEAL)
            self.screen.blit(status_text, (terminal_x, terminal_y + terminal_h - status_font.get_height() - int(6 * self.scale)))
        
        # Dial pad base position
        dial_start_x = modal_x + gap
        dial_start_y = modal_y + self.modal_title_bar_height + gap + terminal_h + spacing
        dial_buttons = [
            ["1", "2", "3"],
            ["4", "5", "6"],
            ["7", "8", "9"],
            ["*", "0", "#"]
        ]
        
        try:
            button_font = pygame.font.Font(None, max(int(24 * self.scale), 16))
            label_font = pygame.font.Font(None, max(int(12 * self.scale), 9))
        except Exception:
            button_font = None
            label_font = None
        keypad_labels = {
            "1": "",
            "2": "ABC",
            "3": "DEF",
            "4": "GHI",
            "5": "JKL",
            "6": "MNO",
            "7": "PRS",
            "8": "TUV",
            "9": "WXY",
            "0": "OPR",
            "*": "",
            "#": ""
        }
        
        if not self.modem_modal_connection_started:
            for row_idx, row in enumerate(dial_buttons):
                for col_idx, button_label in enumerate(row):
                    btn_x = dial_start_x + col_idx * (button_size + button_spacing)
                    btn_y = dial_start_y + row_idx * (button_size + button_spacing)
                    btn_rect = pygame.Rect(btn_x, btn_y, button_size, button_size)
                    
                    # Check if button is hovered
                    is_hovered = self.hovered_button == ("modem", f"dial_{button_label}")
                    btn_color = (25, 35, 60) if not is_hovered else (35, 65, 110)
                    
                    pygame.draw.rect(self.screen, (5, 0, 15), btn_rect, border_radius=8)
                    pygame.draw.rect(self.screen, btn_color, btn_rect.inflate(-6, -6), border_radius=8)
                    pygame.draw.rect(self.screen, COLOR_CYAN, btn_rect, 2, border_radius=8)
                    
                    # Draw button label
                    if button_font:
                        text_surface = button_font.render(button_label, True, COLOR_CYAN)
                        text_rect = text_surface.get_rect(center=btn_rect.center)
                        self.screen.blit(text_surface, text_rect)
                    label_text = keypad_labels.get(button_label, "")
                    if label_font and label_text:
                        label_surface = label_font.render(label_text, True, COLOR_GREY)
                        label_rect = label_surface.get_rect(center=(btn_rect.centerx, btn_rect.centery + int(18 * self.scale)))
                        self.screen.blit(label_surface, label_rect)
        
        # Draw CALL button
        if not self.modem_modal_connection_started:
            call_btn_x = modal_x + gap
            call_btn_y = modal_y + self.modal_title_bar_height + gap + terminal_h + spacing + dial_pad_h + spacing
            call_btn_w = modal_w - 2 * gap
            call_btn_rect = pygame.Rect(call_btn_x, call_btn_y, call_btn_w, call_btn_h)
            is_hovered = self.hovered_button == ("modem", "call")
            btn_color = (20, 60, 40) if is_hovered else (10, 35, 20)
            pygame.draw.rect(self.screen, COLOR_NEON_GREEN, call_btn_rect.inflate(8, 8), 2, border_radius=12)
            pygame.draw.rect(self.screen, btn_color, call_btn_rect, border_radius=12)
            glow_color = (0, 120, 80) if is_hovered else (0, 70, 40)
            pygame.draw.rect(self.screen, glow_color, call_btn_rect.inflate(-8, -8), border_radius=10)
            
            try:
                button_font = pygame.font.Font(None, max(int(18 * self.scale), 13))
                call_text = button_font.render("CALL / CONNECT", True, COLOR_NEON_GREEN)
                call_text_rect = call_text.get_rect(center=call_btn_rect.center)
                self.screen.blit(call_text, call_text_rect)
            except Exception:
                pass

    def _draw_games_modal(self):
        """Draw the games library modal."""
        modal_w, modal_h = self._get_modal_size("games")
        modal_w, modal_h = self._clamp_modal_to_desktop(modal_w, modal_h)
        modal_x, modal_y = self.modal_positions.get("games", self._get_modal_position(modal_w, modal_h, "games"))
        if "games" not in self.modal_positions:
            self.modal_positions["games"] = (modal_x, modal_y)

        modal_rect = pygame.Rect(modal_x, modal_y, modal_w, modal_h)
        pygame.draw.rect(self.screen, COLOR_BG_DARK, modal_rect)
        pygame.draw.rect(self.screen, COLOR_CYAN, modal_rect, 2)

        title_bar_rect = pygame.Rect(modal_x, modal_y, modal_w, self.modal_title_bar_height)
        pygame.draw.rect(self.screen, COLOR_BG_TITLE, title_bar_rect)
        pygame.draw.rect(self.screen, COLOR_CYAN, title_bar_rect, 1)

        try:
            title_font = pygame.font.Font(None, max(int(16 * self.scale), 12))
            subtitle_font = pygame.font.Font(None, max(int(12 * self.scale), 9))
            title_surface = title_font.render("GAMES LIBRARY", True, COLOR_WHITE)
            subtitle_surface = subtitle_font.render("BRADSONIC CLASSICS", True, COLOR_CYAN)
            self.screen.blit(title_surface, (modal_x + int(10 * self.scale), modal_y + int(3 * self.scale)))
            self.screen.blit(subtitle_surface, (modal_x + int(12 * self.scale), modal_y + int(18 * self.scale)))
        except Exception:
            pass

        close_btn_size = int(20 * self.scale)
        close_btn_x = modal_x + modal_w - close_btn_size - int(5 * self.scale)
        close_btn_y = modal_y + int(5 * self.scale)
        close_btn_rect = pygame.Rect(close_btn_x, close_btn_y, close_btn_size, close_btn_size)
        is_hovered = self.hovered_button == ("games", "title_close")
        close_color = COLOR_RED if is_hovered else COLOR_RED_DARK
        pygame.draw.rect(self.screen, close_color, close_btn_rect)
        pygame.draw.rect(self.screen, COLOR_RED, close_btn_rect, 2 if is_hovered else 1)
        try:
            close_font = pygame.font.Font(None, max(int(14 * self.scale), 10))
            close_text = close_font.render("X", True, COLOR_WHITE)
            self.screen.blit(close_text, close_text.get_rect(center=close_btn_rect.center))
        except Exception:
            pass

        gap = int(20 * self.scale)
        content_rect = pygame.Rect(
            modal_x + gap,
            modal_y + self.modal_title_bar_height + gap,
            modal_w - 2 * gap,
            modal_h - self.modal_title_bar_height - 2 * gap
        )
        pygame.draw.rect(self.screen, COLOR_BG_TITLE, content_rect)
        pygame.draw.rect(self.screen, COLOR_CYAN, content_rect, 1)
        inner_rect = content_rect.inflate(-int(10 * self.scale), -int(10 * self.scale))
        pygame.draw.rect(self.screen, COLOR_BG_DARK, inner_rect)
        self.games_modal_content_rect = inner_rect

        label_font = pygame.font.Font(None, max(int(14 * self.scale), 10))
        for icon in self.games_modal_icons:
            icon["rel_x"] = max(0, min(icon["rel_x"], max(0, inner_rect.width - icon["width"])))
            icon["rel_y"] = max(0, min(icon["rel_y"], max(0, inner_rect.height - icon["height"])))
            draw_x = inner_rect.x + icon["rel_x"]
            draw_y = inner_rect.y + icon["rel_y"]
            image = icon["s_image"] if icon["selected"] else icon["image"]
            self.screen.blit(image, (draw_x, draw_y))
            icon["rect"] = pygame.Rect(draw_x, draw_y, icon["width"], icon["height"])
            icon["label"] = icon["label"]  # Preserve data even though not rendered

    def _draw_notes_modal(self):
        """Draw the revamped notes application modal."""
        modal_w, modal_h = self._get_modal_size("notes")
        modal_w, modal_h = self._clamp_modal_to_desktop(modal_w, modal_h)
        modal_x, modal_y = self.modal_positions.get("notes", self._get_modal_position(modal_w, modal_h, "notes"))
        if "notes" not in self.modal_positions:
            self.modal_positions["notes"] = (modal_x, modal_y)

        self.notes_modal_hitboxes = {
            "tabs": [],
            "edit_button": None,
            "delete_button": None,
            "title_field": None,
            "content_field": None,
            "save_button": None,
            "cancel_button": None,
            "format_buttons": [],
            "scroll_arrow": None
        }

        modal_rect = pygame.Rect(modal_x, modal_y, modal_w, modal_h)
        pygame.draw.rect(self.screen, COLOR_BG_DARK, modal_rect)
        pygame.draw.rect(self.screen, COLOR_CYAN, modal_rect, 2)

        title_bar_rect = pygame.Rect(modal_x, modal_y, modal_w, self.modal_title_bar_height)
        pygame.draw.rect(self.screen, COLOR_BG_TITLE, title_bar_rect)
        pygame.draw.rect(self.screen, COLOR_CYAN, title_bar_rect, 1)

        try:
            font_size = max(int(16 * self.scale), 12)
            title_font = pygame.font.Font(None, font_size)
            title_text = title_font.render("Notes", True, COLOR_CYAN)
            self.screen.blit(title_text, (modal_x + int(10 * self.scale), modal_y + int(5 * self.scale)))
        except Exception:
            pass

        close_btn_size = int(20 * self.scale)
        close_btn_x = modal_x + modal_w - close_btn_size - int(5 * self.scale)
        close_btn_y = modal_y + int(5 * self.scale)
        close_btn_rect = pygame.Rect(close_btn_x, close_btn_y, close_btn_size, close_btn_size)
        is_hovered = self.hovered_button == ("notes", "title_close")
        close_color = COLOR_RED if is_hovered else COLOR_RED_DARK
        pygame.draw.rect(self.screen, close_color, close_btn_rect)
        pygame.draw.rect(self.screen, COLOR_RED, close_btn_rect, 2 if is_hovered else 1)
        pygame.draw.rect(self.screen, COLOR_CYAN, close_btn_rect, 1)
        try:
            close_font = pygame.font.Font(None, max(int(14 * self.scale), 10))
            close_text = close_font.render("X", True, COLOR_WHITE)
            close_text_rect = close_text.get_rect(center=close_btn_rect.center)
            self.screen.blit(close_text, close_text_rect)
        except Exception:
            pass

        notes = self._load_user_notes()
        self._ensure_notes_tab_index(notes)

        gap = int(10 * self.scale)
        tab_height = int(30 * self.scale)
        tab_area_y = modal_y + self.modal_title_bar_height + gap
        max_tabs = min(10, len(notes) + 1)
        tab_width = (modal_w - 2 * gap) // max_tabs if max_tabs > 0 else 0
        tab_start_x = modal_x + gap

        try:
            tab_font = pygame.font.SysFont("Segoe Script", max(int(14 * self.scale), 10))
        except Exception:
            tab_font = pygame.font.Font(None, max(int(14 * self.scale), 10))

        for i in range(max_tabs):
            tab_x = tab_start_x + i * tab_width
            tab_rect = pygame.Rect(tab_x, tab_area_y, tab_width - gap, tab_height)
            is_selected = i == self.notes_modal_current_tab

            tab_color = COLOR_BG_TITLE if is_selected else COLOR_BG_DARK
            pygame.draw.rect(self.screen, tab_color, tab_rect)
            pygame.draw.rect(self.screen, COLOR_CYAN, tab_rect, 2 if is_selected else 1)
            pygame.draw.rect(self.screen, COLOR_CYAN, tab_rect, 1)

            label = "+ New" if i >= len(notes) else notes[i].get("title", "Untitled")
            lines = self._wrap_text_lines(label, tab_font, max(tab_rect.width - int(8 * self.scale), 1))[:2]
            if not lines:
                lines = [label]
            line_height = tab_font.get_height()
            total_height = line_height * len(lines)
            text_y = tab_rect.y + (tab_rect.height - total_height) // 2

            for line in lines:
                text_surface = tab_font.render(line, True, COLOR_CYAN)
                text_x = tab_rect.x + int(4 * self.scale)
                self.screen.blit(text_surface, (text_x, text_y))
                text_y += line_height

            self.notes_modal_hitboxes["tabs"].append((tab_rect, i))

        self.notes_modal_hitboxes["add_button"] = None

        content_area_y = tab_area_y + tab_height + gap
        content_area_h = modal_h - self.modal_title_bar_height - tab_height - 2 * gap - int(30 * self.scale)
        content_area_rect = pygame.Rect(modal_x + gap, content_area_y, modal_w - 2 * gap, content_area_h)
        pygame.draw.rect(self.screen, COLOR_BLACK, content_area_rect)
        pygame.draw.rect(self.screen, COLOR_CYAN, content_area_rect, 1)

        if not notes:
            return

        note = notes[self.notes_modal_current_tab]
        if self.notes_modal_edit_mode and self.notes_modal_edit_index == self.notes_modal_current_tab:
            self._draw_note_editor(note, content_area_rect, modal_x, modal_y, modal_w)
        else:
            self._draw_note_view(note, content_area_rect, modal_x, modal_y, modal_w)

        scroll_arrow_size = int(30 * self.scale)
        scroll_arrow_x = modal_x + modal_w - gap - scroll_arrow_size
        scroll_arrow_y = modal_y + modal_h - gap - scroll_arrow_size
        scroll_arrow_rect = pygame.Rect(scroll_arrow_x, scroll_arrow_y, scroll_arrow_size, scroll_arrow_size)
        pygame.draw.polygon(self.screen, COLOR_GREY, [
            (scroll_arrow_x + scroll_arrow_size // 2, scroll_arrow_y + scroll_arrow_size),
            (scroll_arrow_x, scroll_arrow_y),
            (scroll_arrow_x + scroll_arrow_size, scroll_arrow_y)
        ])
        pygame.draw.rect(self.screen, COLOR_GREY, scroll_arrow_rect, 1)
        self.notes_modal_hitboxes["scroll_arrow"] = scroll_arrow_rect
        
    def _get_icon_positions_file_path(self) -> str:
        """Get the path to the icon positions JSON file."""
        # Save in OS folder alongside OS_Mode.py
        os_folder = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(os_folder, "icon_positions.json")

    def _align_icons_to_tape_center(self):
        """Align every icon horizontally to the tape icon's center."""
        if not self.icons or not self.desktop_rect:
            return
        tape_icon = next((icon for icon in self.icons if icon["name"] == "tape-icon.png"), None)
        if not tape_icon:
            return
        tape_center = tape_icon["x"] + tape_icon["width"] / 2
        for icon in self.icons:
            aligned_x = int(tape_center - icon["width"] / 2)
            aligned_x = max(self.desktop_rect.left, min(aligned_x, self.desktop_rect.right - icon["width"]))
            icon["x"] = aligned_x

    def _load_games_icons(self, normalized_positions: Optional[Dict[str, Tuple[float, float]]] = None) -> None:
        """Load or reload the games modal icons with proper scaling."""
        icons: List[Dict[str, object]] = []
        for definition in self.games_icon_defs:
            try:
                normal_path = get_data_path("OS", definition["file"])
                selected_path = get_data_path("OS", definition["selected_file"])
                normal_image = pygame.image.load(normal_path).convert_alpha()
                original_size = normal_image.get_size()
                icon_size = (
                    int(original_size[0] * self.scale),
                    int(original_size[1] * self.scale)
                )
                normal_image = pygame.transform.scale(normal_image, icon_size)
                try:
                    selected_image = pygame.image.load(selected_path).convert_alpha()
                    selected_image = pygame.transform.scale(selected_image, icon_size)
                except Exception:
                    selected_image = normal_image
            except Exception as e:
                print(f"Warning: Failed to load games icon {definition['file']}: {e}")
                continue

            if normalized_positions and definition["name"] in normalized_positions:
                norm_x, norm_y = normalized_positions[definition["name"]]
                rel_x = int(norm_x * self.scale)
                rel_y = int(norm_y * self.scale)
            else:
                default_x, default_y = definition["default_pos"]
                rel_x = int(default_x * self.scale)
                rel_y = int(default_y * self.scale)

            icon_data = {
                "name": definition["name"],
                "label": definition["label"],
                "image": normal_image,
                "s_image": selected_image,
                "width": icon_size[0],
                "height": icon_size[1],
                "rel_x": rel_x,
                "rel_y": rel_y,
                "selected": False,
                "rect": None
            }
            icons.append(icon_data)

        self.games_modal_icons = icons
        self.games_modal_selected_icon = None
        self.games_modal_dragging_icon = None
        self.games_modal_content_rect = None

    def _clear_games_icon_selection(self) -> None:
        self.games_modal_selected_icon = None
        for icon in self.games_modal_icons:
            icon["selected"] = False

    def _select_games_icon(self, target_icon: Dict[str, object]) -> None:
        for icon in self.games_modal_icons:
            icon["selected"] = icon is target_icon
        self.games_modal_selected_icon = target_icon["name"]

    def _update_games_icon_drag(self, mouse_x: int, mouse_y: int) -> bool:
        if not self.games_modal_dragging_icon or not self.games_modal_content_rect:
            return False
        icon = self.games_modal_dragging_icon
        offset_x, offset_y = self.games_modal_drag_offset
        content_rect = self.games_modal_content_rect
        new_rel_x = mouse_x - content_rect.x - offset_x
        new_rel_y = mouse_y - content_rect.y - offset_y
        max_x = max(0, content_rect.width - icon["width"])
        max_y = max(0, content_rect.height - icon["height"])
        icon["rel_x"] = max(0, min(new_rel_x, max_x))
        icon["rel_y"] = max(0, min(new_rel_y, max_y))
        icon["rect"] = pygame.Rect(
            content_rect.x + icon["rel_x"],
            content_rect.y + icon["rel_y"],
            icon["width"],
            icon["height"]
        )
        return True


    def _get_note_button_rects(self, content_rect: pygame.Rect) -> Tuple[pygame.Rect, pygame.Rect, pygame.Rect]:
        """Helper to calculate edit/delete button rects anchored to bottom-left of content area."""
        gap = int(10 * self.scale)
        button_panel_padding = int(5 * self.scale)
        edit_button_width = int(55 * self.scale)
        delete_button_width = int(95 * self.scale)
        button_height = int(25 * self.scale)
        button_spacing = int(5 * self.scale)
        panel_width = edit_button_width + delete_button_width + button_spacing + button_panel_padding * 2
        panel_height = button_height + button_panel_padding * 2

        panel_x = content_rect.x + gap
        panel_y = content_rect.bottom - panel_height - gap

        edit_btn_rect = pygame.Rect(
            panel_x + button_panel_padding,
            panel_y + button_panel_padding,
            edit_button_width,
            button_height
        )
        delete_btn_rect = pygame.Rect(
            edit_btn_rect.right + button_spacing,
            panel_y + button_panel_padding,
            delete_button_width,
            button_height
        )
        panel_rect = pygame.Rect(panel_x, panel_y, panel_width, panel_height)
        return edit_btn_rect, delete_btn_rect, panel_rect

    def _mission_note_template(self):
        return {
            "title": MISSION_NOTE_TITLE,
            "content": MISSION_NOTE_CONTENT,
            "is_locked": True
        }

    def _load_user_notes(self) -> List[Dict]:
        """Load notes from user profile and ensure mission note exists."""
        notes = self.get_notes() or []
        mission_note = self._mission_note_template()
        changed = False

        if not notes:
            # No notes at all - create mission note
            notes = [mission_note]
            changed = True
        else:
            first = notes[0]
            # Check if first note is the locked mission note
            is_mission_note = (first.get("is_locked", False) and 
                              first.get("title") == mission_note["title"])
            
            if not is_mission_note:
                # Mission note is missing or not first - restore it
                # Remove any other locked notes (shouldn't exist, but be safe)
                other_notes = [note for note in notes if not note.get("is_locked", False)]
                notes = [mission_note] + other_notes
                changed = True
            else:
                # Mission note exists - ensure content is up to date
                if first.get("content") != mission_note["content"]:
                    notes[0]["title"] = mission_note["title"]
                    notes[0]["content"] = mission_note["content"]
                    notes[0]["is_locked"] = True
                    changed = True

        # Enforce max of 10 notes
        if len(notes) > 10:
            notes = notes[:10]
            changed = True

        if changed:
            self.save_notes(notes)

        return notes

    def _save_user_notes(self, notes: List[Dict]) -> None:
        """Persist notes back to user profile, ensuring mission note is first."""
        sanitized: List[Dict] = []
        mission_note = self._mission_note_template()

        # Always ensure mission note is first
        sanitized.append(mission_note)

        for note in notes[1:]:
            if note.get("is_locked", False):
                continue  # Skip any other locked notes to avoid duplicates

            sanitized.append({
                "title": note.get("title", "Untitled").strip() or "Untitled",
                "content": note.get("content", ""),
                "is_locked": False
            })

        # Cap at 10
        sanitized = sanitized[:10]
        self.save_notes(sanitized)

    def _ensure_notes_tab_index(self, notes: List[Dict]) -> None:
        if not notes:
            self.notes_modal_current_tab = 0
            return
        if self.notes_modal_current_tab >= len(notes):
            self.notes_modal_current_tab = len(notes) - 1
        if self.notes_modal_current_tab < 0:
            self.notes_modal_current_tab = 0

    def _enter_notes_edit_mode(self, note_index: int, is_new: bool = False) -> None:
        notes = self._load_user_notes()
        if note_index >= len(notes):
            return
        note = notes[note_index]
        if note.get("is_locked", False):
            return  # Locked notes cannot be edited

        self.notes_modal_edit_mode = True
        self.notes_modal_edit_index = note_index
        self.notes_modal_edit_field = "title" if is_new else "content"
        self.notes_modal_edit_title_text = note.get("title", "Untitled").strip() or "Untitled"
        self.notes_modal_edit_content_text = note.get("content", "")
        self.notes_modal_title_cursor = len(self.notes_modal_edit_title_text)
        self.notes_modal_content_cursor = len(self.notes_modal_edit_content_text)
        self.notes_modal_title_selection = (self.notes_modal_title_cursor, self.notes_modal_title_cursor)
        self.notes_modal_content_selection = (self.notes_modal_content_cursor, self.notes_modal_content_cursor)
        self.notes_modal_selection_field = None
        self.notes_modal_selection_anchor = 0
        self.notes_modal_dragging_selection = False
        self.notes_modal_cursor_blink_timer = 0.0
        self.notes_modal_message = ""

    def _exit_notes_edit_mode(self, save_changes: bool) -> None:
        if not self.notes_modal_edit_mode or self.notes_modal_edit_index is None:
            return

        if save_changes:
            notes = self._load_user_notes()
            if self.notes_modal_edit_index < len(notes):
                note = notes[self.notes_modal_edit_index]
                if not note.get("is_locked", False):
                    note["title"] = self.notes_modal_edit_title_text.strip() or "Untitled"
                    note["content"] = self.notes_modal_edit_content_text
                    self._save_user_notes(notes)
        self.notes_modal_edit_mode = False
        self.notes_modal_edit_index = None
        self.notes_modal_edit_title_text = ""
        self.notes_modal_edit_content_text = ""
        self.notes_modal_title_cursor = 0
        self.notes_modal_content_cursor = 0
        self.notes_modal_title_selection = (0, 0)
        self.notes_modal_content_selection = (0, 0)
        self.notes_modal_selection_anchor = 0
        self.notes_modal_selection_field = None
        self.notes_modal_dragging_selection = False
        self.notes_modal_content_cursor_aim_x = None
        self.notes_modal_message = ""

    def _notes_active_text(self) -> Tuple[str, int, Tuple[int, int]]:
        if self.notes_modal_edit_field == "title":
            text = self.notes_modal_edit_title_text
            cursor = max(0, min(len(text), self.notes_modal_title_cursor))
            sel_start, sel_end = self.notes_modal_title_selection
        else:
            text = self.notes_modal_edit_content_text
            cursor = max(0, min(len(text), self.notes_modal_content_cursor))
            sel_start, sel_end = self.notes_modal_content_selection
        start = max(0, min(len(text), min(sel_start, sel_end)))
        end = max(start, min(len(text), max(sel_start, sel_end)))
        return text, cursor, (start, end)

    def _notes_get_field_state(self, field: str) -> Tuple[str, int, Tuple[int, int]]:
        if field == "title":
            text = self.notes_modal_edit_title_text
            cursor = self.notes_modal_title_cursor
            selection = self.notes_modal_title_selection
        else:
            text = self.notes_modal_edit_content_text
            cursor = self.notes_modal_content_cursor
            selection = self.notes_modal_content_selection
        return text, cursor, selection

    def _notes_set_active_text(self, text: str, cursor: int, selection: Optional[Tuple[int, int]] = None) -> None:
        cursor = max(0, min(len(text), cursor))
        if self.notes_modal_edit_field == "title":
            self.notes_modal_edit_title_text = text
            self.notes_modal_title_cursor = cursor
            if selection:
                start = max(0, min(len(text), selection[0]))
                end = max(0, min(len(text), selection[1]))
                self.notes_modal_title_selection = (start, end)
            else:
                self.notes_modal_title_selection = (cursor, cursor)
        else:
            self.notes_modal_edit_content_text = text
            self.notes_modal_content_cursor = cursor
            if selection:
                start = max(0, min(len(text), selection[0]))
                end = max(0, min(len(text), selection[1]))
                self.notes_modal_content_selection = (start, end)
            else:
                self.notes_modal_content_selection = (cursor, cursor)
            self.notes_modal_content_cursor_aim_x = None

    def _notes_set_cursor_for_field(self, field: str, cursor: int) -> None:
        if field == "title":
            text = self.notes_modal_edit_title_text
            cursor = max(0, min(len(text), cursor))
            self.notes_modal_title_cursor = cursor
            self.notes_modal_title_selection = (cursor, cursor)
        else:
            text = self.notes_modal_edit_content_text
            cursor = max(0, min(len(text), cursor))
            self.notes_modal_content_cursor = cursor
            self.notes_modal_content_selection = (cursor, cursor)
            self.notes_modal_content_cursor_aim_x = None

    def _notes_set_selection_for_field(self, field: str, start: int, end: int) -> None:
        if field == "title":
            text_len = len(self.notes_modal_edit_title_text)
            start = max(0, min(text_len, start))
            end = max(0, min(text_len, end))
            self.notes_modal_title_selection = (start, end)
        else:
            text_len = len(self.notes_modal_edit_content_text)
            start = max(0, min(text_len, start))
            end = max(0, min(text_len, end))
            self.notes_modal_content_selection = (start, end)

    def _notes_clear_selection(self, field: str) -> None:
        if field == "title":
            cursor = self.notes_modal_title_cursor
            self.notes_modal_title_selection = (cursor, cursor)
        else:
            cursor = self.notes_modal_content_cursor
            self.notes_modal_content_selection = (cursor, cursor)

    def _notes_delete_selection(self) -> bool:
        text, cursor, (start, end) = self._notes_active_text()
        if start == end:
            return False
        new_text = text[:start] + text[end:]
        self._notes_set_active_text(new_text, start)
        self.notes_modal_selection_field = None
        self.notes_modal_selection_anchor = 0
        return True

    def _wrap_text_lines(self, text: str, font: pygame.font.Font, max_width: int) -> List[str]:
        """Wrap text to fit within max_width, preserving newlines."""
        if max_width <= 0:
            return [text]

        wrapped_lines: List[str] = []
        paragraphs = text.split("\n")

        for paragraph in paragraphs:
            if not paragraph:
                wrapped_lines.append("")
                continue

            words = paragraph.split(" ")
            current_line = ""
            for word in words:
                if not current_line:
                    candidate = word
                else:
                    candidate = f"{current_line} {word}"

                if font.size(candidate)[0] <= max_width:
                    current_line = candidate
                else:
                    if current_line:
                        wrapped_lines.append(current_line)
                    current_line = word

            wrapped_lines.append(current_line)

        return wrapped_lines

    def _wrap_text_for_editing(self, text: str, font: pygame.font.Font, max_width: int) -> List[Dict[str, object]]:
        """Wrap text for editing, preserving original indices per line."""
        if max_width <= 0:
            return [{"text": text, "start": 0, "end": len(text)}]

        lines: List[Dict[str, object]] = []
        line_start = 0
        i = 0
        line_width = 0
        last_space_index = -1

        while i < len(text):
            ch = text[i]
            if ch == "\n":
                lines.append({"text": text[line_start:i], "start": line_start, "end": i})
                i += 1
                line_start = i
                line_width = 0
                last_space_index = -1
                continue

            char_width = font.size(ch)[0]
            if line_width + char_width <= max_width:
                line_width += char_width
                if ch == " ":
                    last_space_index = i
                i += 1
            else:
                if last_space_index >= line_start:
                    wrap_pos = last_space_index + 1
                    lines.append({"text": text[line_start:wrap_pos], "start": line_start, "end": wrap_pos})
                    i = wrap_pos
                else:
                    wrap_pos = i
                    lines.append({"text": text[line_start:wrap_pos], "start": line_start, "end": wrap_pos})
                line_start = i
                line_width = 0
                last_space_index = -1

        lines.append({"text": text[line_start:len(text)], "start": line_start, "end": len(text)})
        if text.endswith("\n"):
            lines.append({"text": "", "start": len(text), "end": len(text)})
        return lines
    
    def _resolve_note_tokens(self, text: str) -> str:
        """Replace placeholder tokens (e.g., <username>, <pin>) with actual user data."""
        if not text:
            return text
        username, pin = self.get_user_credentials()
        replacements = {
            "<username>": username or "",
            "<pin>": pin or ""
        }
        for placeholder, value in replacements.items():
            text = text.replace(placeholder, value)
        return text

    def _notes_cursor_from_position(self, field: str, mouse_x: int, mouse_y: int) -> int:
        """Convert mouse coordinates to a cursor index within the active field."""
        if field == "title":
            if not self.notes_modal_title_field_rect or not self.notes_modal_title_font:
                return len(self.notes_modal_edit_title_text)
            rect = self.notes_modal_title_field_rect
            font = self.notes_modal_title_font
            origin_x, origin_y = self.notes_modal_title_text_origin
            text = self.notes_modal_edit_title_text
            if mouse_y <= rect.top:
                return 0
            if mouse_y >= rect.bottom:
                return len(text)
            relative_x = mouse_x - origin_x
            if relative_x <= 0:
                return 0
            accum = 0
            for idx, ch in enumerate(text):
                ch_width = font.size(ch)[0]
                if relative_x <= accum + ch_width / 2:
                    return idx
                accum += ch_width
            return len(text)

        # Content field
        if not self.notes_modal_content_field_rect or not self.notes_modal_content_font:
            return len(self.notes_modal_edit_content_text)
        font = self.notes_modal_content_font
        origin_x, origin_y = self.notes_modal_content_text_origin
        layout = self.notes_modal_content_layout_info or [{"start": 0, "end": len(self.notes_modal_edit_content_text), "text": self.notes_modal_edit_content_text, "y": origin_y}]
        if not layout:
            layout = [{"start": 0, "end": 0, "text": "", "y": origin_y}]

        target_line = None
        line_height = font.get_height()
        for line in layout:
            line_top = line["y"]
            line_rect = pygame.Rect(origin_x, line_top, self.notes_modal_content_field_rect.width, line_height)
            if line_rect.collidepoint(mouse_x, mouse_y):
                target_line = line
                break

        if target_line is None:
            if mouse_y < layout[0]["y"]:
                return 0
            return len(self.notes_modal_edit_content_text)

        relative_x = mouse_x - origin_x
        if relative_x <= 0:
            return target_line["start"]

        accum = 0
        line_text = target_line["text"]
        for idx, ch in enumerate(line_text):
            ch_width = font.size(ch)[0]
            if relative_x <= accum + ch_width / 2:
                return target_line["start"] + idx
            accum += ch_width
        return target_line["end"]

    def _notes_update_drag_selection(self, mouse_x: int, mouse_y: int) -> bool:
        """Update selection while the user drags inside a text field."""
        if not self.notes_modal_dragging_selection or not self.notes_modal_selection_field:
            return False
        field = self.notes_modal_selection_field
        cursor = self._notes_cursor_from_position(field, mouse_x, mouse_y)
        if field == "title":
            self.notes_modal_title_cursor = cursor
        else:
            self.notes_modal_content_cursor = cursor
        self._notes_set_selection_for_field(field, self.notes_modal_selection_anchor, cursor)
        if self.notes_modal_edit_field != field:
            self.notes_modal_edit_field = field
        return True

    def _notes_move_cursor_to(self, new_cursor: int, shift_held: bool) -> None:
        """Move cursor while respecting selection anchors."""
        text, cursor, (sel_start, sel_end) = self._notes_active_text()
        new_cursor = max(0, min(len(text), new_cursor))
        if shift_held:
            if self.notes_modal_selection_field != self.notes_modal_edit_field or self.notes_modal_selection_field is None:
                self.notes_modal_selection_field = self.notes_modal_edit_field
                self.notes_modal_selection_anchor = cursor
            selection = (self.notes_modal_selection_anchor, new_cursor)
        else:
            self.notes_modal_selection_field = None
            self.notes_modal_selection_anchor = 0
            selection = (new_cursor, new_cursor)
        self._notes_set_active_text(text, new_cursor, selection)

    def _notes_find_line_index(self, cursor: int) -> int:
        layout = self.notes_modal_content_layout_info
        if not layout:
            return 0
        for idx, line in enumerate(layout):
            start = line["start"]
            end = line["end"]
            if start <= cursor <= end:
                if cursor == end and idx + 1 < len(layout) and layout[idx + 1]["start"] == end:
                    return idx + 1
                return idx
        return len(layout) - 1

    def _notes_index_from_line_x(self, line: Dict[str, object], target_x: int) -> int:
        font = self.notes_modal_content_font
        if not font:
            return line["start"]
        line_text = line["text"]
        accum = 0
        for idx, ch in enumerate(line_text):
            ch_width = font.size(ch)[0]
            if target_x <= accum + ch_width / 2:
                return line["start"] + idx
            accum += ch_width
        return line["end"]

    def _notes_move_cursor_vertical(self, direction: int, shift_held: bool) -> bool:
        """Move cursor up/down within the wrapped content."""
        if self.notes_modal_edit_field != "content":
            return False
        layout = self.notes_modal_content_layout_info
        if not layout:
            return False
        text, cursor, _ = self._notes_active_text()
        cursor = max(0, min(len(text), cursor))
        current_line_index = self._notes_find_line_index(cursor)
        target_index = current_line_index + direction
        if target_index < 0 or target_index >= len(layout):
            return False

        if self.notes_modal_content_cursor_aim_x is None:
            current_line = layout[current_line_index]
            prefix = self.notes_modal_edit_content_text[current_line["start"]:cursor]
            self.notes_modal_content_cursor_aim_x = self.notes_modal_content_font.size(prefix)[0] if self.notes_modal_content_font else 0

        target_line = layout[target_index]
        aim_x = self.notes_modal_content_cursor_aim_x or 0
        new_cursor = self._notes_index_from_line_x(target_line, aim_x)
        self._notes_move_cursor_to(new_cursor, shift_held)
        self.notes_modal_content_cursor_aim_x = aim_x
        return True

    def _notes_handle_keydown(self, event: pygame.event.Event) -> bool:
        """Handle keyboard input while editing notes."""
        if not self.notes_modal_edit_mode:
            return False

        text, cursor, _ = self._notes_active_text()
        shift_held = bool(event.mod & pygame.KMOD_SHIFT)

        if event.key == pygame.K_ESCAPE:
            self._exit_notes_edit_mode(save_changes=False)
            return True

        if event.key == pygame.K_TAB:
            self._notes_set_active_text(text, cursor)
            if self.notes_modal_edit_field == "title":
                self.notes_modal_edit_field = "content"
                cursor = self.notes_modal_content_cursor
                text = self.notes_modal_edit_content_text
            else:
                self.notes_modal_edit_field = "title"
                cursor = self.notes_modal_title_cursor
                text = self.notes_modal_edit_title_text
            self.notes_modal_selection_field = None
            self.notes_modal_selection_anchor = 0
            self.notes_modal_cursor_blink_timer = 0.0
            return True

        if self.notes_modal_edit_field == "title" and event.key == pygame.K_RETURN:
            # Ignore enter in title field
            return True
        if self.notes_modal_edit_field == "content" and event.key == pygame.K_RETURN:
            if self._notes_delete_selection():
                text, cursor, _ = self._notes_active_text()
            text = text[:cursor] + "\n" + text[cursor:]
            cursor += 1
            self._notes_set_active_text(text, cursor)
            return True

        if event.key == pygame.K_BACKSPACE:
            if self._notes_delete_selection():
                return True
            if cursor > 0:
                text = text[:cursor - 1] + text[cursor:]
                cursor -= 1
                self._notes_set_active_text(text, cursor)
            return True

        if event.key == pygame.K_DELETE:
            if self._notes_delete_selection():
                return True
            if cursor < len(text):
                text = text[:cursor] + text[cursor + 1:]
                self._notes_set_active_text(text, cursor)
            return True

        if event.key == pygame.K_LEFT:
            if cursor > 0:
                self._notes_move_cursor_to(cursor - 1, shift_held)
            return True

        if event.key == pygame.K_RIGHT:
            if cursor < len(text):
                self._notes_move_cursor_to(cursor + 1, shift_held)
            return True

        if event.key == pygame.K_HOME:
            if self.notes_modal_edit_field == "content":
                line_start = text.rfind("\n", 0, cursor)
                cursor = line_start + 1 if line_start >= 0 else 0
            else:
                cursor = 0
            self._notes_move_cursor_to(cursor, shift_held)
            return True

        if event.key == pygame.K_END:
            if self.notes_modal_edit_field == "content":
                line_end = text.find("\n", cursor)
                cursor = line_end if line_end != -1 else len(text)
            else:
                cursor = len(text)
            self._notes_move_cursor_to(cursor, shift_held)
            return True

        if event.key == pygame.K_UP:
            if self._notes_move_cursor_vertical(-1, shift_held):
                return True

        if event.key == pygame.K_DOWN:
            if self._notes_move_cursor_vertical(1, shift_held):
                return True

        return False

    def _notes_handle_textinput(self, text_input: str) -> bool:
        """Handle TEXTINPUT events while editing notes."""
        if not self.notes_modal_edit_mode:
            return False

        if not text_input:
            return True

        text, cursor, _ = self._notes_active_text()
        if self._notes_delete_selection():
            text, cursor, _ = self._notes_active_text()
        text = text[:cursor] + text_input + text[cursor:]
        cursor += len(text_input)
        self._notes_set_active_text(text, cursor)
        return True

    def _notes_apply_format_action(self, action: str) -> None:
        """Apply formatting actions within the content field."""
        if action in {"bold", "highlight", "strike", "numbered"} and self.notes_modal_edit_field != "content":
            self.notes_modal_message = "Formatting tools only work in the content field."
            return

        self.notes_modal_message = ""
        if action == "bold":
            self._notes_insert_tag("b")
        elif action == "highlight":
            self._notes_insert_tag("hl")
        elif action == "strike":
            self._notes_insert_tag("s")
        elif action == "numbered":
            self._notes_insert_numbered_bullet()

    def _notes_insert_tag(self, tag: str) -> None:
        text, cursor, (sel_start, sel_end) = self._notes_active_text()
        start = f"[{tag}]"
        end = f"[/{tag}]"
        if sel_start != sel_end:
            start_index = min(sel_start, sel_end)
            end_index = max(sel_start, sel_end)
            new_text = text[:start_index] + start + text[start_index:end_index] + end + text[end_index:]
            cursor = start_index + len(start) + (end_index - start_index) + len(end)
            self._notes_set_active_text(new_text, cursor)
        else:
            new_text = text[:cursor] + start + end + text[cursor:]
            cursor += len(start)
            self._notes_set_active_text(new_text, cursor)
        self.notes_modal_selection_field = None
        self.notes_modal_selection_anchor = 0

    def _notes_insert_numbered_bullet(self) -> None:
        text, cursor, _ = self._notes_active_text()
        if self._notes_delete_selection():
            text, cursor, _ = self._notes_active_text()
        line_start = text.rfind("\n", 0, cursor)
        line_start = line_start + 1 if line_start >= 0 else 0

        prefix = ""
        if cursor > 0 and text[cursor - 1] != "\n":
            prefix = "\n"

        next_num = self._notes_next_bullet_number(text[:cursor])
        insert = f"{prefix}{next_num}. "
        new_text = text[:cursor] + insert + text[cursor:]
        cursor += len(insert)
        self._notes_set_active_text(new_text, cursor)
        self.notes_modal_selection_field = None
        self.notes_modal_selection_anchor = 0

    def _notes_next_bullet_number(self, existing_text: str) -> int:
        number = 1
        lines = [line.strip() for line in existing_text.split("\n") if line.strip()]
        for line in reversed(lines):
            if "." in line:
                prefix = line.split(".", 1)[0]
                if prefix.isdigit():
                    number = int(prefix) + 1
                    break
        return number

    def _parse_markup_segments(self, text: str) -> List[Dict[str, object]]:
        """Parse simple markup tags into styled text segments."""
        segments: List[Dict[str, object]] = []
        i = 0
        bold = False
        strike = False
        highlight = False
        current = ""

        def flush():
            nonlocal current
            if current:
                segments.append({
                    "text": current,
                    "bold": bold,
                    "strike": strike,
                    "highlight": highlight
                })
                current = ""

        tags = {
            "[b]": ("bold", True),
            "[/b]": ("bold", False),
            "[s]": ("strike", True),
            "[/s]": ("strike", False),
            "[hl]": ("highlight", True),
            "[/hl]": ("highlight", False),
        }

        while i < len(text):
            matched = False
            for tag, (attr, state) in tags.items():
                if text.startswith(tag, i):
                    flush()
                    if attr == "bold":
                        bold = state
                    elif attr == "strike":
                        strike = state
                    elif attr == "highlight":
                        highlight = state
                    i += len(tag)
                    matched = True
                    break
            if matched:
                continue
            current += text[i]
            i += 1

        flush()
        return segments or [{"text": "", "bold": False, "strike": False, "highlight": False}]

    def _measure_text_fit(self, font: pygame.font.Font, text: str, max_width: int) -> int:
        """Return number of characters from text that fit within max_width."""
        if max_width <= 0:
            return 0
        if font.size(text)[0] <= max_width:
            return len(text)
        low, high = 1, len(text)
        fit = 1
        while low <= high:
            mid = (low + high) // 2
            width = font.size(text[:mid])[0]
            if width <= max_width:
                fit = mid
                low = mid + 1
            else:
                high = mid - 1
        # Try to break at space
        space_index = text.rfind(" ", 0, fit)
        if space_index > 0:
            return space_index + 1
        return fit

    def _render_rich_text(self, text: str, body_font: pygame.font.Font, bold_font: pygame.font.Font,
                          start_x: int, start_y: int, max_width: int, max_height: int) -> None:
        """Render text with simple markup (bold, highlight, strikethrough)."""
        line_height = body_font.get_height() + int(4 * self.scale)
        x = start_x
        y = start_y

        for paragraph in text.split("\n"):
            segments = self._parse_markup_segments(paragraph)
            for segment in segments:
                segment_text = segment["text"]
                seg_font = bold_font if segment["bold"] else body_font
                while segment_text:
                    remaining_width = max_width - (x - start_x)
                    if remaining_width <= 0:
                        x = start_x
                        y += line_height
                        if y > max_height:
                            return
                        remaining_width = max_width

                    fit_chars = self._measure_text_fit(seg_font, segment_text, remaining_width)
                    if fit_chars <= 0:
                        x = start_x
                        y += line_height
                        if y > max_height:
                            return
                        continue

                    chunk = segment_text[:fit_chars]
                    segment_text = segment_text[fit_chars:]
                    text_surface = seg_font.render(chunk, True, COLOR_WHITE)

                    if segment["highlight"]:
                        highlight_rect = text_surface.get_rect(topleft=(x, y))
                        highlight_rect.inflate_ip(4, 4)
                        highlight_surface = pygame.Surface(highlight_rect.size, pygame.SRCALPHA)
                        highlight_surface.fill((255, 255, 0, 90))
                        self.screen.blit(highlight_surface, highlight_rect.topleft)

                    self.screen.blit(text_surface, (x, y))

                    if segment["strike"]:
                        line_y = y + text_surface.get_height() // 2
                        pygame.draw.line(self.screen, COLOR_WHITE, (x, line_y), (x + text_surface.get_width(), line_y), 2)

                    x += text_surface.get_width()

                    if segment_text:
                        x = start_x
                        y += line_height
                        if y > max_height:
                            return

            x = start_x
            y += line_height
            if y > max_height:
                return

    def _create_new_note(self):
        """Create a new note and immediately enter edit mode."""
        notes = self._load_user_notes()
        if len(notes) >= 10:
            return

        notes.append({
            "title": "New Note",
            "content": "",
            "is_locked": False
        })
        self._save_user_notes(notes)
        self.notes_modal_current_tab = len(notes) - 1
        self._enter_notes_edit_mode(self.notes_modal_current_tab, is_new=True)

    def _delete_note_at_index(self, index: int):
        """Delete note at index if allowed."""
        notes = self._load_user_notes()
        if index < 0 or index >= len(notes):
            return  # Invalid index
        
        # Check if note is locked - locked notes cannot be deleted
        note = notes[index]
        if note.get("is_locked", False):
            return  # Locked notes cannot be deleted
        
        # Double-check: never delete index 0 (mission note)
        if index == 0:
            return  # Mission note is always protected

        del notes[index]
        self._save_user_notes(notes)
        self.notes_modal_edit_mode = False
        self.notes_modal_edit_index = None
        self.notes_modal_current_tab = min(self.notes_modal_current_tab, len(notes) - 1)

    def _draw_note_view(self, note: Dict, content_area_rect: pygame.Rect, modal_x: int, modal_y: int, modal_w: int) -> None:
        """Draw note content in view mode (not editing)."""
        gap = int(10 * self.scale)
        text_x = content_area_rect.x + gap
        text_y = content_area_rect.y + gap

        title_font_size = max(int(24 * self.scale), 16)
        body_font_size = max(int(16 * self.scale), 12)

        try:
            title_font = pygame.font.SysFont("Segoe Script", title_font_size)
        except Exception:
            title_font = pygame.font.Font(None, title_font_size)

        try:
            body_font = pygame.font.SysFont("Segoe Script", body_font_size)
        except Exception:
            body_font = pygame.font.Font(None, body_font_size)

        # Draw title
        title_surface = title_font.render(note.get("title", "Untitled"), True, COLOR_CYAN)
        self.screen.blit(title_surface, (text_x, text_y))
        text_y += title_surface.get_height() + gap

        available_width = content_area_rect.width - gap * 2
        max_y = content_area_rect.bottom - gap
        try:
            bold_font = pygame.font.SysFont("Segoe Script", body_font_size, bold=True)
        except Exception:
            bold_font = pygame.font.Font(None, body_font_size)
            bold_font.set_bold(True)

        note_content = self._resolve_note_tokens(note.get("content", ""))
        self._render_rich_text(
            note_content,
            body_font,
            bold_font,
            text_x,
            text_y,
            available_width,
            max_y
        )

        # Draw floating panel for edit/delete (if allowed)
        if not note.get("is_locked", False):
            edit_rect, delete_rect, panel_rect = self._get_note_button_rects(content_area_rect)
            pygame.draw.rect(self.screen, COLOR_BG_DARK, panel_rect)
            pygame.draw.rect(self.screen, COLOR_CYAN, panel_rect, 2)

            # DELETE button
            is_hovered = self.hovered_button == ("notes", "delete")
            delete_color = COLOR_RED if is_hovered else COLOR_RED_DARK
            pygame.draw.rect(self.screen, delete_color, delete_rect)
            pygame.draw.rect(self.screen, COLOR_RED, delete_rect, 2 if is_hovered else 1)
            pygame.draw.rect(self.screen, COLOR_CYAN, delete_rect, 1)
            try:
                btn_font = pygame.font.Font(None, max(int(12 * self.scale), 8))
                delete_text = btn_font.render("DELETE", True, COLOR_WHITE)
                text_rect = delete_text.get_rect(center=delete_rect.center)
                self.screen.blit(delete_text, text_rect)
            except Exception:
                pass

            # EDIT button
            is_hovered = self.hovered_button == ("notes", "edit")
            edit_color = COLOR_CYAN if is_hovered else COLOR_BG_TITLE
            pygame.draw.rect(self.screen, edit_color, edit_rect)
            pygame.draw.rect(self.screen, COLOR_CYAN, edit_rect, 2 if is_hovered else 1)
            pygame.draw.rect(self.screen, COLOR_CYAN, edit_rect, 1)
            try:
                btn_font = pygame.font.Font(None, max(int(12 * self.scale), 8))
                edit_text = btn_font.render("EDIT", True, COLOR_CYAN)
                text_rect = edit_text.get_rect(center=edit_rect.center)
                self.screen.blit(edit_text, text_rect)
            except Exception:
                pass

            # Cache hitboxes
            self.notes_modal_hitboxes["edit_button"] = edit_rect
            self.notes_modal_hitboxes["delete_button"] = delete_rect
        else:
            self.notes_modal_hitboxes["edit_button"] = None
            self.notes_modal_hitboxes["delete_button"] = None

    def _draw_note_editor(self, note: Dict, content_area_rect: pygame.Rect, modal_x: int, modal_y: int, modal_w: int) -> None:
        """Draw editable fields for the active note."""
        gap = int(10 * self.scale)
        label_color = COLOR_CYAN

        title_font_size = max(int(20 * self.scale), 14)
        body_font_size = max(int(16 * self.scale), 12)

        try:
            title_font = pygame.font.SysFont("Segoe Script", title_font_size)
        except Exception:
            title_font = pygame.font.Font(None, title_font_size)

        try:
            body_font = pygame.font.SysFont("Segoe Script", body_font_size)
        except Exception:
            body_font = pygame.font.Font(None, body_font_size)

        # Title field
        title_label = title_font.render("Title", True, label_color)
        title_label_pos = (content_area_rect.x + gap, content_area_rect.y + gap)
        self.screen.blit(title_label, title_label_pos)

        title_field_rect = pygame.Rect(
            content_area_rect.x + gap,
            title_label_pos[1] + title_label.get_height() + int(4 * self.scale),
            content_area_rect.width - gap * 2,
            title_font.get_height() + int(8 * self.scale)
        )
        pygame.draw.rect(self.screen, COLOR_BG_DARK, title_field_rect)
        pygame.draw.rect(self.screen, COLOR_CYAN, title_field_rect, 2 if self.notes_modal_edit_field == "title" else 1)

        text_start = (title_field_rect.x + int(6 * self.scale), title_field_rect.y + int(2 * self.scale))
        self.notes_modal_title_field_rect = title_field_rect
        self.notes_modal_title_font = title_font
        self.notes_modal_title_text_origin = text_start

        title_text = self.notes_modal_edit_title_text or ""
        sel_start, sel_end = sorted(self.notes_modal_title_selection)
        if sel_start != sel_end:
            prefix = title_text[:sel_start]
            selected = title_text[sel_start:sel_end]
            prefix_width = title_font.size(prefix)[0]
            highlight_width = title_font.size(selected or " ")[0]
            if highlight_width <= 0:
                highlight_width = int(4 * self.scale)
            highlight_rect = pygame.Rect(
                text_start[0] + prefix_width,
                text_start[1],
                highlight_width,
                title_font.get_height()
            )
            highlight_surface = pygame.Surface(highlight_rect.size, pygame.SRCALPHA)
            highlight_surface.fill(COLOR_SELECTION)
            self.screen.blit(highlight_surface, highlight_rect.topleft)

        title_text_surface = title_font.render(title_text, True, COLOR_WHITE)
        self.screen.blit(title_text_surface, text_start)

        # Title cursor
        if self.notes_modal_edit_field == "title" and int(self.notes_modal_cursor_blink_timer * 2) % 2 == 0:
            cursor_prefix = title_font.render(title_text[:self.notes_modal_title_cursor], True, COLOR_WHITE)
            cursor_x = text_start[0] + cursor_prefix.get_width()
            cursor_y = text_start[1]
            pygame.draw.line(self.screen, COLOR_CYAN, (cursor_x, cursor_y), (cursor_x, cursor_y + title_font.get_height()), 2)

        self.notes_modal_hitboxes["title_field"] = title_field_rect

        # Content field label
        content_label_y = title_field_rect.bottom + gap
        content_label = body_font.render("Content", True, label_color)
        self.screen.blit(content_label, (content_area_rect.x + gap, content_label_y))

        format_btn_h = int(32 * self.scale)
        format_btn_w = int(54 * self.scale)
        format_btn_gap = int(6 * self.scale)
        format_toolbar_y = content_label_y + content_label.get_height() + int(4 * self.scale)
        format_toolbar_x = content_area_rect.x + gap
        format_actions = [("B", "bold"), ("HL", "highlight"), ("S", "strike"), ("1.", "numbered")]
        self.notes_modal_hitboxes["format_buttons"] = []
        try:
            fmt_font = pygame.font.Font(None, max(int(18 * self.scale), 12))
        except Exception:
            fmt_font = pygame.font.Font(None, 18)

        for idx, (label, action) in enumerate(format_actions):
            rect = pygame.Rect(
                format_toolbar_x + idx * (format_btn_w + format_btn_gap),
                format_toolbar_y,
                format_btn_w,
                format_btn_h
            )
            pygame.draw.rect(self.screen, COLOR_BG_TITLE, rect)
            pygame.draw.rect(self.screen, COLOR_CYAN, rect, 2)
            if action == "strike":
                label_surface = fmt_font.render("S", True, COLOR_CYAN)
                self.screen.blit(label_surface, label_surface.get_rect(center=rect.center))
                strike_y = rect.centery
                line_margin = int(8 * self.scale)
                line_width = max(2, int(2 * self.scale))
                pygame.draw.line(
                    self.screen,
                    COLOR_CYAN,
                    (rect.left + line_margin, strike_y),
                    (rect.right - line_margin, strike_y),
                    line_width
                )
            else:
                label_surface = fmt_font.render(label, True, COLOR_CYAN)
                self.screen.blit(label_surface, label_surface.get_rect(center=rect.center))
            self.notes_modal_hitboxes["format_buttons"].append((rect, action))

        content_field_top = format_toolbar_y + format_btn_h + int(6 * self.scale)
        content_field_rect = pygame.Rect(
            content_area_rect.x + gap,
            content_field_top,
            content_area_rect.width - gap * 2,
            content_area_rect.bottom - content_field_top - gap
        )
        pygame.draw.rect(self.screen, COLOR_BG_DARK, content_field_rect)
        pygame.draw.rect(self.screen, COLOR_CYAN, content_field_rect, 2 if self.notes_modal_edit_field == "content" else 1)

        text_start_x = content_field_rect.x + int(6 * self.scale)
        text_start_y = content_field_rect.y + int(4 * self.scale)
        available_width = content_field_rect.width - int(12 * self.scale)
        line_height = body_font.get_height() + int(4 * self.scale)
        max_y = content_field_rect.bottom - int(4 * self.scale)

        self.notes_modal_content_field_rect = content_field_rect
        self.notes_modal_content_font = body_font
        self.notes_modal_content_text_origin = (text_start_x, text_start_y)
        self.notes_modal_content_available_width = available_width
        self.notes_modal_content_line_height = line_height

        wrapped_infos = self._wrap_text_for_editing(self.notes_modal_edit_content_text, body_font, available_width)
        content_layout: List[Dict[str, object]] = []
        current_y = text_start_y
        for info in wrapped_infos:
            content_layout.append({
                "start": info["start"],
                "end": info["end"],
                "text": info["text"],
                "y": current_y
            })
            current_y += line_height
        if not content_layout:
            content_layout.append({"start": 0, "end": 0, "text": "", "y": text_start_y})
        self.notes_modal_content_layout_info = content_layout

        # Draw selection highlight first
        sel_start, sel_end = sorted(self.notes_modal_content_selection)
        if sel_start != sel_end:
            for line in content_layout:
                line_top = line["y"]
                if line_top > content_field_rect.bottom:
                    break
                line_bottom = line_top + body_font.get_height()
                if line_bottom < content_field_rect.top:
                    continue

                overlap_start = max(sel_start, line["start"])
                overlap_end = min(sel_end, line["end"])
                if line["start"] == line["end"] and sel_start <= line["start"] < sel_end:
                    overlap_start = line["start"]
                    overlap_end = line["start"] + 1

                if overlap_start >= overlap_end:
                    continue

                relative_start = overlap_start - line["start"]
                relative_end = overlap_end - line["start"]
                line_text = line["text"]
                prefix = line_text[:relative_start]
                # highlight_text might be empty if selection spans newline; ensure minimal width
                highlight_text = line_text[relative_start:relative_end]
                prefix_width = body_font.size(prefix)[0]
                highlight_width = body_font.size(highlight_text or " ")[0]
                if highlight_width <= 0:
                    highlight_width = int(4 * self.scale)

                highlight_rect = pygame.Rect(
                    text_start_x + prefix_width,
                    line_top,
                    highlight_width,
                    body_font.get_height()
                )
                if highlight_rect.bottom > content_field_rect.bottom:
                    highlight_rect.height = content_field_rect.bottom - highlight_rect.top
                highlight_rect = highlight_rect.clip(content_field_rect)
                if highlight_rect.width > 0 and highlight_rect.height > 0:
                    highlight_surface = pygame.Surface((highlight_rect.width, highlight_rect.height), pygame.SRCALPHA)
                    highlight_surface.fill(COLOR_SELECTION)
                    self.screen.blit(highlight_surface, highlight_rect.topleft)

        # Draw wrapped text
        for line in content_layout:
            if line["y"] + body_font.get_height() > max_y:
                break
            line_surface = body_font.render(line["text"], True, COLOR_WHITE)
            self.screen.blit(line_surface, (text_start_x, line["y"]))

        # Content cursor
        if self.notes_modal_edit_field == "content" and int(self.notes_modal_cursor_blink_timer * 2) % 2 == 0:
            caret_index = max(0, min(len(self.notes_modal_edit_content_text), self.notes_modal_content_cursor))
            caret_x = text_start_x
            caret_y = text_start_y
            cursor_drawn = False
            for i, line in enumerate(content_layout):
                start = line["start"]
                end = line["end"]
                if start <= caret_index <= end:
                    relative_len = caret_index - start
                    caret_x = text_start_x + body_font.size(line["text"][:relative_len])[0]
                    caret_y = line["y"]
                    # If cursor sits exactly at line end and next line starts there, move caret down
                    if caret_index == end and i + 1 < len(content_layout) and content_layout[i + 1]["start"] == end:
                        caret_y = content_layout[i + 1]["y"]
                        caret_x = text_start_x
                    cursor_drawn = True
                    break
            if not cursor_drawn and content_layout:
                last_line = content_layout[-1]
                caret_x = text_start_x + body_font.size(last_line["text"])[0]
                caret_y = last_line["y"]
            if caret_y + body_font.get_height() <= content_field_rect.bottom:
                pygame.draw.line(self.screen, COLOR_CYAN, (caret_x, caret_y), (caret_x, caret_y + body_font.get_height()), 2)

        self.notes_modal_hitboxes["content_field"] = content_field_rect

        # Save/Cancel buttons
        button_w = int(110 * self.scale)
        button_h = int(32 * self.scale)
        button_gap = int(12 * self.scale)
        button_y = content_area_rect.bottom - button_h - gap
        cancel_rect = pygame.Rect(content_area_rect.x + gap, button_y, button_w, button_h)
        save_rect = pygame.Rect(cancel_rect.right + button_gap, button_y, button_w, button_h)

        pygame.draw.rect(self.screen, COLOR_BG_TITLE, cancel_rect)
        pygame.draw.rect(self.screen, COLOR_CYAN, cancel_rect, 2)
        pygame.draw.rect(self.screen, COLOR_BG_TITLE, save_rect)
        pygame.draw.rect(self.screen, COLOR_CYAN, save_rect, 2)

        try:
            btn_font = pygame.font.Font(None, max(int(14 * self.scale), 10))
            cancel_text = btn_font.render("Cancel", True, COLOR_CYAN)
            save_text = btn_font.render("Save Note", True, COLOR_GREEN)
            self.screen.blit(cancel_text, cancel_text.get_rect(center=cancel_rect.center))
            self.screen.blit(save_text, save_text.get_rect(center=save_rect.center))
        except Exception:
            pass

        self.notes_modal_hitboxes["cancel_button"] = cancel_rect
        self.notes_modal_hitboxes["save_button"] = save_rect
        self.notes_modal_hitboxes["edit_button"] = None
        self.notes_modal_hitboxes["delete_button"] = None
        self.notes_modal_hitboxes["format_buttons"] = self.notes_modal_hitboxes.get("format_buttons", [])

        if self.notes_modal_message:
            try:
                msg_font = pygame.font.Font(None, max(int(14 * self.scale), 10))
                msg_surface = msg_font.render(self.notes_modal_message, True, COLOR_RED)
                msg_pos = (content_area_rect.x + gap, cancel_rect.y - msg_surface.get_height() - int(4 * self.scale))
                self.screen.blit(msg_surface, msg_pos)
            except Exception:
                pass
    
    def _load_icon_positions(self) -> Dict[str, Dict[str, int]]:
        """Load saved icon positions from JSON file. Returns empty dict if file doesn't exist."""
        file_path = self._get_icon_positions_file_path()
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    # Validate data structure
                    if isinstance(data, dict):
                        return data
            return {}
        except Exception as e:
            print(f"Warning: Failed to load icon positions: {e}")
            return {}
    
    def _save_icon_positions(self):
        """Save current icon positions to JSON file, overwriting previous data."""
        file_path = self._get_icon_positions_file_path()
        try:
            # Capture current icon positions (overwriting, not appending)
            positions = {}
            for icon in self.icons:
                positions[icon["name"]] = {
                    "x": icon["x"],
                    "y": icon["y"]
                }
            
            # Write to file (overwrites existing file)
            with open(file_path, 'w') as f:
                json.dump(positions, f, indent=2)
        except Exception as e:
            print(f"Warning: Failed to save icon positions: {e}")
    
    def _reset_os_mode(self):
        """Reset OS Mode to its initial state - resets icons, modals, and all state."""
        # Reset all modals
        self.active_modals.clear()
        self.modal_positions.clear()
        self.modal_dragging = None
        self.modal_drag_offset = (0, 0)
        
        # Reset tape modal state
        self.tape_modal_terminal_text = ""
        self.tape_modal_terminal_lines = []
        self.tape_modal_message_timer = 0.0
        self.tape_modal_video_completed = False  # Reset completion flag when modal resets
        self._stop_tape_video()
        
        # Reset modem modal state
        self.modem_modal_dialed_sequence = ""
        self.modem_modal_connection_messages = []
        self.modem_modal_message_index = 0
        self.modem_modal_message_timer = 0.0
        self.modem_modal_connection_started = False
        self.modem_modal_should_reset_bbs = False
        self.modem_modal_should_exit_os = False
        self.modem_terminal_rect = None
        self.modem_packet_sprites.clear()
        self.modem_wave_phase = 0.0
        self.modem_packet_spawn_timer = 0.0
        self.network_connected = False
        self._stop_modem_dial_sound()
        
        # Reset icon states and restore positions from saved file (or defaults if none saved)
        saved_positions = self._load_icon_positions()
        current_y = self.desktop_y + int(70 * self.scale)  # Start 70px down from desktop top
        icon_spacing = int(10 * self.scale)
        
        for icon in self.icons:
            # Restore from saved position if available, otherwise use default stacked position
            if icon["name"] in saved_positions:
                # Use saved position (already scaled)
                icon["x"] = saved_positions[icon["name"]]["x"]
                icon["y"] = saved_positions[icon["name"]]["y"]
            else:
                # Default position: top-left corner, stacked vertically
                icon["x"] = self.desktop_x + int(10 * self.scale)  # Small margin from left
                icon["y"] = current_y
                # Move to next position for next icon
                current_y += icon["height"] + icon_spacing
            
            # Reset icon state
            icon["selected"] = False
            icon["dragging"] = False
            icon["drag_offset_x"] = 0
            icon["drag_offset_y"] = 0
        
        self._clear_games_icon_selection()
        self.games_modal_dragging_icon = None
        self.games_modal_content_rect = None
        
        self._align_icons_to_tape_center()
        
        # Reset hover states
        self.hovered_icon = None
        self.hovered_button = None
        self.icon_label_alpha.clear()
        
        # Reset overlay state
        self.overlay_active = False
        
        # Reset double-click tracking
        self.last_click_time = 0.0
        self.last_click_pos = None

        # Reset notes modal state
        self.notes_modal_current_tab = 0
        self.notes_modal_edit_mode = False
        self.notes_modal_edit_index = None
        self.notes_modal_edit_field = "content"
        self.notes_modal_edit_title_text = ""
        self.notes_modal_edit_content_text = ""
        self.notes_modal_title_cursor = 0
        self.notes_modal_content_cursor = 0
        self.notes_modal_title_selection = (0, 0)
        self.notes_modal_content_selection = (0, 0)
        self.notes_modal_selection_anchor = 0
        self.notes_modal_selection_field = None
        self.notes_modal_dragging_selection = False
        self.notes_modal_title_field_rect = None
        self.notes_modal_content_field_rect = None
        self.notes_modal_title_font = None
        self.notes_modal_content_font = None
        self.notes_modal_title_text_origin = (0, 0)
        self.notes_modal_content_text_origin = (0, 0)
        self.notes_modal_content_available_width = 0
        self.notes_modal_content_line_height = 0
        self.notes_modal_content_layout_info = []
        self.notes_modal_content_cursor_aim_x = None
        self.notes_modal_cursor_blink_timer = 0.0
        self.notes_modal_hitboxes = {}
        self.notes_modal_message = ""
        # Close chess game if active
        if self.chess_game and self.chess_game.active:
            self.chess_game.close()
        # Close solitaire game if active
        if self.solitaire_game and self.solitaire_game.active:
            self.solitaire_game.close()
        # Close solitaire game if active
        if self.solitaire_game and self.solitaire_game.active:
            self.solitaire_game.close()
    
    def toggle_overlay(self):
        """Toggle the overlay rectangle state."""
        self.overlay_active = not self.overlay_active
    
    def draw_overlay(self):
        """Draw the overlay rectangle matching desktop dimensions."""
        if self.overlay_active:
            overlay_rect = pygame.Rect(
                self.desktop_x,
                self.desktop_y,
                self.desktop_size[0],
                self.desktop_size[1]
            )
            pygame.draw.rect(self.screen, (0, 0, 0), overlay_rect)  # Black rectangle
    
    def is_mouse_in_desktop(self, mouse_x: int, mouse_y: int) -> bool:
        """Check if mouse position is within desktop boundaries."""
        return (self.desktop_x <= mouse_x < self.desktop_x + self.desktop_size[0] and
                self.desktop_y <= mouse_y < self.desktop_y + self.desktop_size[1])
    
    def set_cursor(self, mouse_x: int, mouse_y: int):
        """Set the cursor based on mouse position relative to desktop."""
        if self.is_mouse_in_desktop(mouse_x, mouse_y):
            # Mouse is inside desktop - use OS cursor
            if self.custom_cursor:
                try:
                    pygame.mouse.set_cursor(self.custom_cursor)
                except Exception:
                    pass
        # If mouse is outside desktop, don't set cursor here - let main.py handle it
    
    def draw_cursor(self, mouse_x: int, mouse_y: int):
        """Draw the custom OS mouse cursor as a sprite (under scanlines)."""
        if self.cursor_image and self.is_mouse_in_desktop(mouse_x, mouse_y):
            # Draw cursor image at mouse position (offset by cursor size for better positioning)
            cursor_w, cursor_h = self.cursor_image.get_size()
            # Draw cursor centered on mouse position (or adjust offset as needed)
            self.screen.blit(self.cursor_image, (mouse_x, mouse_y))
    
    def update_bbs_position(self, bbs_x: int, bbs_y: int, bbs_width: int):
        """Update BBS position info for clock positioning."""
        self.bbs_x = bbs_x
        self.bbs_y = bbs_y
        self.bbs_width = bbs_width
    
    def update_scale(self, new_scale: float):
        """Update scale factor and recalculate positions/sizes."""
        # Capture old scale before updating
        old_scale = self.scale
        self.scale = new_scale
        
        # Recalculate desktop position
        self.desktop_x = int(self.baseline_desktop_x * self.scale)
        self.desktop_y = int(self.baseline_desktop_y * self.scale)
        
        # Reload and rescale desktop image
        desktop_path = get_data_path("OS", "Desktop-Enviroment.png")
        try:
            self.desktop_image = pygame.image.load(desktop_path).convert_alpha()
            original_size = self.desktop_image.get_size()
            self.desktop_size = (
                int(original_size[0] * self.scale),
                int(original_size[1] * self.scale)
            )
            self.desktop_image = pygame.transform.scale(self.desktop_image, self.desktop_size)
        except Exception as e:
            print(f"Warning: Failed to reload Desktop-Enviroment.png: {e}")
            self.desktop_image = None
        
        # Update desktop rect
        self.desktop_rect = pygame.Rect(
            self.desktop_x,
            self.desktop_y,
            self.desktop_size[0],
            self.desktop_size[1]
        )
        
        # Reload and rescale icons (both normal and selected versions)
        # Preserve current icon positions and scale them proportionally
        scale_ratio = new_scale / old_scale if old_scale > 0 else 1.0
        previous_game_positions = None
        if self.games_modal_icons:
            previous_game_positions = {}
            for icon in self.games_modal_icons:
                norm_x = icon["rel_x"] / old_scale if old_scale else icon["rel_x"]
                norm_y = icon["rel_y"] / old_scale if old_scale else icon["rel_y"]
                previous_game_positions[icon["name"]] = (norm_x, norm_y)
        
        for icon in self.icons:
            icon_path = get_data_path("OS", icon["name"])
            # Get the "S" version filename
            s_icon_file = "S-" + icon["name"]
            s_icon_path = get_data_path("OS", s_icon_file)
            
            # Save current position before reloading
            old_x = icon["x"]
            old_y = icon["y"]
            
            try:
                # Reload normal icon
                icon_image = pygame.image.load(icon_path).convert_alpha()
                original_icon_size = icon_image.get_size()
                icon_size = (
                    int(original_icon_size[0] * self.scale),
                    int(original_icon_size[1] * self.scale)
                )
                icon_image = pygame.transform.scale(icon_image, icon_size)
                
                # Reload selected "S" version icon
                s_icon_image = None
                try:
                    s_icon_image = pygame.image.load(s_icon_path).convert_alpha()
                    s_icon_image = pygame.transform.scale(s_icon_image, icon_size)
                except Exception as e:
                    print(f"Warning: Failed to reload {s_icon_file}: {e}")
                    # If S version doesn't exist, use normal icon as fallback
                    s_icon_image = icon_image
                
                icon["image"] = icon_image
                icon["s_image"] = s_icon_image
                icon["width"] = icon_size[0]
                icon["height"] = icon_size[1]
                
                # Scale icon position proportionally to maintain relative position
                # Calculate position relative to OLD desktop position, then scale to NEW desktop position
                old_desktop_x = int(self.baseline_desktop_x * old_scale)
                old_desktop_y = int(self.baseline_desktop_y * old_scale)
                rel_x = old_x - old_desktop_x
                rel_y = old_y - old_desktop_y
                icon["x"] = self.desktop_x + int(rel_x * scale_ratio)
                icon["y"] = self.desktop_y + int(rel_y * scale_ratio)
            except Exception as e:
                print(f"Warning: Failed to reload {icon['name']}: {e}")
        
        # Reload and rescale cursor
        cursor_path = get_data_path("OS", "mouse_cursor.png")
        try:
            cursor_image = pygame.image.load(cursor_path).convert_alpha()
            original_cursor_size = cursor_image.get_size()
            cursor_size = (
                int(original_cursor_size[0] * self.scale),
                int(original_cursor_size[1] * self.scale)
            )
            cursor_image = pygame.transform.scale(cursor_image, cursor_size)
            self.custom_cursor = pygame.cursors.Cursor((0, 0), cursor_image)
            self.cursor_image = cursor_image
        except Exception as e:
            print(f"Warning: Failed to reload mouse_cursor.png: {e}")
        
        # Reload and rescale desktop scanline
        scanline_path = get_data_path("OS", "Scanline-Desktop.png")
        try:
            self.desktop_scanline_image = pygame.image.load(scanline_path).convert_alpha()
            self.desktop_scanline_image = pygame.transform.scale(
                self.desktop_scanline_image, 
                self.desktop_size
            )
        except Exception as e:
            print(f"Warning: Failed to reload Scanline-Desktop.png: {e}")
            self.desktop_scanline_image = None

        self._load_games_icons(previous_game_positions)
        
        # Update chess game desktop coordinates and scale
        if self.chess_game:
            health_monitor_y = self.bbs_y + int(10 * self.scale) if self.bbs_y else self.desktop_y + int(10 * self.scale)
            self.chess_game.update_desktop(self.desktop_x, self.desktop_y, self.desktop_size, health_monitor_y)
            self.chess_game.scale = self.scale
            # Reload chess assets with new scale if game is active
            if self.chess_game.active:
                try:
                    self.chess_game._load_assets()
                except Exception as e:
                    print(f"Warning: Failed to reload chess assets: {e}")
        
        # Update solitaire game desktop coordinates and scale
        if self.solitaire_game:
            health_monitor_y = self.bbs_y + int(10 * self.scale) if self.bbs_y else self.desktop_y + int(10 * self.scale)
            self.solitaire_game.update_desktop(self.desktop_x, self.desktop_y, self.desktop_size, health_monitor_y)
            self.solitaire_game.scale = self.scale
            # Reload solitaire assets with new scale if game is active
            if self.solitaire_game.active:
                try:
                    self.solitaire_game._load_assets()
                except Exception as e:
                    print(f"Warning: Failed to reload solitaire assets: {e}")
    
    def _update_hover_states(self, mouse_x: int, mouse_y: int):
        """Update hover states for icons and buttons based on mouse position."""
        # Reset hover states
        self.hovered_icon = None
        self.hovered_button = None
        
        # Check icon hovers (only if not dragging)
        if not self.mouse_pressed:
            for icon in self.icons:
                icon_rect = pygame.Rect(icon["x"], icon["y"], icon["width"], icon["height"])
                if icon_rect.collidepoint(mouse_x, mouse_y):
                    self.hovered_icon = icon
                    break
        
        # Check button hovers in modals (check top-most first)
        for modal_name in reversed(list(self.active_modals)):
            modal_x, modal_y = self.modal_positions.get(modal_name, (0, 0))
            modal_w, modal_h = self._get_modal_size(modal_name)
            
            if modal_name == "tape":
                # Check tape modal buttons
                button_y = modal_y + self.modal_title_bar_height + int(390 * self.scale)
                button_h = int(40 * self.scale)
                button_w = int(180 * self.scale)
                button_spacing = int(20 * self.scale)
                
                # Title bar close button
                close_btn_size = int(20 * self.scale)
                close_btn_x = modal_x + modal_w - close_btn_size - int(5 * self.scale)
                close_btn_y = modal_y + int(5 * self.scale)
                close_btn_rect = pygame.Rect(close_btn_x, close_btn_y, close_btn_size, close_btn_size)
                if close_btn_rect.collidepoint(mouse_x, mouse_y):
                    self.hovered_button = ("tape", "title_close")
                    return
                
                # LOAD DATA button
                load_btn_x = modal_x + int(50 * self.scale)
                load_btn_rect = pygame.Rect(load_btn_x, button_y, button_w, button_h)
                if load_btn_rect.collidepoint(mouse_x, mouse_y):
                    self.hovered_button = ("tape", "load")
                    return
                
                # RECORD DATA button
                record_btn_x = load_btn_x + button_w + button_spacing
                record_btn_rect = pygame.Rect(record_btn_x, button_y, button_w, button_h)
                if record_btn_rect.collidepoint(mouse_x, mouse_y):
                    self.hovered_button = ("tape", "record")
                    return
            
            elif modal_name == "modem":
                # Check modem modal buttons
                layout = self._get_modem_layout_metrics()
                button_size = layout["button_size"]
                button_spacing = layout["button_spacing"]
                gap = layout["gap"]
                terminal_h = layout["terminal_h"]
                spacing = layout["spacing"]
                dial_pad_h = layout["dial_pad_h"]
                call_btn_h = layout["call_btn_h"]
                
                # Title bar close button
                close_btn_size = int(20 * self.scale)
                close_btn_x = modal_x + modal_w - close_btn_size - int(5 * self.scale)
                close_btn_y = modal_y + int(5 * self.scale)
                close_btn_rect = pygame.Rect(close_btn_x, close_btn_y, close_btn_size, close_btn_size)
                if close_btn_rect.collidepoint(mouse_x, mouse_y):
                    self.hovered_button = ("modem", "title_close")
                    return
                
                # Dial pad buttons
                if not self.modem_modal_connection_started:
                    dial_start_x = modal_x + gap
                    dial_start_y = modal_y + self.modal_title_bar_height + gap + terminal_h + spacing
                    dial_buttons = [["1", "2", "3"], ["4", "5", "6"], ["7", "8", "9"], ["*", "0", "#"]]
                    for row_idx, row in enumerate(dial_buttons):
                        for col_idx, button_label in enumerate(row):
                            btn_x = dial_start_x + col_idx * (button_size + button_spacing)
                            btn_y = dial_start_y + row_idx * (button_size + button_spacing)
                            btn_rect = pygame.Rect(btn_x, btn_y, button_size, button_size)
                            if btn_rect.collidepoint(mouse_x, mouse_y):
                                self.hovered_button = ("modem", f"dial_{button_label}")
                                return
                
                # CALL button
                if not self.modem_modal_connection_started:
                    call_btn_x = modal_x + gap
                    call_btn_y = modal_y + self.modal_title_bar_height + gap + terminal_h + spacing + dial_pad_h + spacing
                    call_btn_w = modal_w - 2 * gap
                    call_btn_rect = pygame.Rect(call_btn_x, call_btn_y, call_btn_w, call_btn_h)
                    if call_btn_rect.collidepoint(mouse_x, mouse_y):
                        self.hovered_button = ("modem", "call")
                        return
            
            elif modal_name == "notes":
                notes = self._load_user_notes()
                close_btn_size = int(20 * self.scale)
                
                # Title bar close button
                close_btn_x = modal_x + modal_w - close_btn_size - int(5 * self.scale)
                close_btn_y = modal_y + int(5 * self.scale)
                close_btn_rect = pygame.Rect(close_btn_x, close_btn_y, close_btn_size, close_btn_size)
                if close_btn_rect.collidepoint(mouse_x, mouse_y):
                    self.hovered_button = ("notes", "title_close")
                    return
                # Hover states for buttons stored during draw
                edit_rect = self.notes_modal_hitboxes.get("edit_button")
                delete_rect = self.notes_modal_hitboxes.get("delete_button")
                if edit_rect and edit_rect.collidepoint(mouse_x, mouse_y):
                    self.hovered_button = ("notes", "edit")
                    return
                if delete_rect and delete_rect.collidepoint(mouse_x, mouse_y):
                    self.hovered_button = ("notes", "delete")
                    return
            elif modal_name == "games":
                close_btn_size = int(20 * self.scale)
                close_btn_x = modal_x + modal_w - close_btn_size - int(5 * self.scale)
                close_btn_y = modal_y + int(5 * self.scale)
                close_btn_rect = pygame.Rect(close_btn_x, close_btn_y, close_btn_size, close_btn_size)
                if close_btn_rect.collidepoint(mouse_x, mouse_y):
                    self.hovered_button = ("games", "title_close")
                    return
    
    def _draw_icon_label(self, icon_x: int, icon_y: int, icon_w: int, icon_h: int, label_text: str):
        """Draw a label below an icon with fade animation."""
        icon_id = None
        for icon in self.icons:
            if icon["x"] == icon_x and icon["y"] == icon_y:
                icon_id = id(icon)
                break
        
        if icon_id is None or icon_id not in self.icon_label_alpha:
            return
        
        alpha = int(self.icon_label_alpha[icon_id])
        if alpha <= 0:
            return
        
        try:
            font_size = max(int(12 * self.scale), 10)
            label_font = pygame.font.Font(None, font_size)
            
            # Create text surface with alpha
            text_surface = label_font.render(label_text, True, COLOR_CYAN)
            text_surface.set_alpha(alpha)
            
            # Position label below icon
            label_x = icon_x + (icon_w - text_surface.get_width()) // 2
            label_y = icon_y + icon_h + int(5 * self.scale)
            
            # Draw semi-transparent background for readability
            bg_rect = pygame.Rect(
                label_x - int(4 * self.scale),
                label_y - int(2 * self.scale),
                text_surface.get_width() + int(8 * self.scale),
                text_surface.get_height() + int(4 * self.scale)
            )
            bg_surface = pygame.Surface((bg_rect.width, bg_rect.height))
            bg_surface.set_alpha(alpha // 2)
            bg_surface.fill(COLOR_BLACK)
            self.screen.blit(bg_surface, bg_rect)
            
            # Draw text
            self.screen.blit(text_surface, (label_x, label_y))
        except Exception:
            pass

