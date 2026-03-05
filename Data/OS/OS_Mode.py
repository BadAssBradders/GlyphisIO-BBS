"""
OS Mode - Desktop Environment
A fictional desktop environment that launches the BBS.
Enhanced with visual polish, smooth interactions, and improved UX.
"""

import pygame
import os
import sys
import time
import shutil
import math
import json
import random
from typing import List, Dict, Tuple, Optional, Any
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
    "[s]1. Receive Invite from Glyphis[/s]\n"
    "[s]2. Get onto the BBS (0345728891)[/s]\n"
    "[s]3. Complete a technical challenge to prove yourself[/s]\n"
    "4. Get the audio tech's help and get the first audio stream from Glyphisis_IO. Record it using the Datasette!\n"
    "5. Get invited to crack some games\n"
    "6. Obtain access to the group's Pirate Radio Stream!\n"
)

# BBS login note template (non-deletable login information note)
BBS_LOGIN_NOTE_TITLE = "BBS Numbers and Logins"

# Notes app: tab title display and edit limit
NOTESTAB_TITLE_MAX_LEN = 20

# School op ghost sequence: bullet list typed into a new note (player's notes to self; already logged out)
SCHOOL_OP_NOTE_TITLE = "School Op - Steps"
# Ghost types this version - no credentials; player must find them in LocaleProtocols.brad
SCHOOL_HACK_NOTE_LINES_NO_CREDS = [
    "• Desktop: HDD>System>Terminal, type file-system-start",
    "• Open locale protocols file, find Switch Region String",
    "• String (period-sep):",
    "  - get admin-command...",
    "  - command: ???",
    "  - username: ???",
    "  - password: ???",
    "• Close terminal, reopen, run admin-command + user + pass",
    "• Region change → American Mainland (no factory reset)",
    "• Open email on desktop, send rain@ciphernet.net subj I'm in",
    "• Wait for Rain's reply",
]
# Version with credentials - used when player observes LocaleProtocols.brad (marks progress)
SCHOOL_HACK_NOTE_LINES_WITH_CREDS = [
    "• Desktop: HDD>System>Terminal, type file-system-start",
    "• Open locale protocols file, find Switch Region String",
    "• String (period-sep):",
    "  - get admin-command...",
    "  - command: admin-subset",
    "  - username: general",
    "  - password: louis-sonic",
    "• Close terminal, reopen, run admin-command + user + pass",
    "• Region change → American Mainland (no factory reset)",
    "• Open email on desktop, send rain@ciphernet.net subj I'm in",
    "• Wait for Rain's reply",
]
BBS_NAME = "GLYPHIS_IO BBS"
BBS_NUMBER = "0345728891"

# BRADSONIC-MAIL guided compose placeholders (faint hints)
MAIL_COMPOSE_PLACEHOLDER_TO = "rain@ci..."
MAIL_COMPOSE_PLACEHOLDER_SUBJECT = "i'm in"
MAIL_COMPOSE_PLACEHOLDER_BODY = (
    "Okay, I'm in, US MAINLAND set as my current region locale, so what are your orders?"
)
# Rain's reply after connecting and sending "I'm in" to rain@ciphernet.net
RAIN_REPLY_SUBJECT = "You're in - next steps"


def _get_rain_reply_body(username: str) -> str:
    """Build Rain's reply body with username. Only call when player sent 'I'm in' to Rain."""
    u = username or "you"
    return (
        f"There will be new games in the games folder, check em out! Also, I bet you're wondering "
        f"what the other icon is that just showed up? Well {u}, that's your dotSonic player, you can "
        f"play all of the .sonic tracks you've downloaded from the likes of Paper Crane BBS and all "
        f"of the other amazing BBSs out-there, downloads should have already gone to your media folder "
        f"and with this new player you can simply play them like a cassette, cool right?\n\n"
        "Congrats. You're inside the region-restricted area. Good work.\n\n"
        "Here's how to use this mail client to pretend to be the telephone company. In Settings, set your "
        "fake From address to: region-support@telco-relay.bradsonic.net - and add this signature: "
        "\"Regional Line Testing - BRADSONIC-TELCO RELAY.\" Then compose a new message to the school's "
        "front desk (add their address in your contacts). Request phone system numbers and PIN codes for "
        "any telephone systems, answer machines, faxes, or modems. Write a lengthy email about system "
        "security and that you need the info right away in order to test the lines and avoid any "
        "disruptions. Keep it official and urgent."
    )

# Animation Constants
HOVER_ANIMATION_SPEED = 8.0  # pixels per second
ICON_LABEL_FADE_SPEED = 3.0  # alpha per second

# Try to import cv2 for video playback
try:
    import cv2
    import numpy as np
    _cv2_available = True
    
    # Define backend constants for GPU acceleration
    # CAP_MSMF uses Microsoft Media Foundation (hardware-accelerated on Windows)
    # CAP_DSHOW uses DirectShow (can also use hardware acceleration)
    # We'll try MSMF first as it's the most modern and GPU-accelerated on Windows 10/11
    try:
        _CAP_MSMF = cv2.CAP_MSMF
    except AttributeError:
        _CAP_MSMF = 1400  # Fallback if constant not defined
        
    try:
        _CAP_DSHOW = cv2.CAP_DSHOW
    except AttributeError:
        _CAP_DSHOW = 700  # Fallback if constant not defined
        
except ImportError:
    _cv2_available = False
    cv2 = None
    np = None
    _CAP_MSMF = None
    _CAP_DSHOW = None

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

# Snooker game is now in a separate module
try:
    import sys
    import os
    import importlib.util
    # Add the snooker directory to the path for import
    # Get the directory containing this file (OS_Mode.py)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    snooker_dir = os.path.join(current_dir, "Snooker")
    if snooker_dir not in sys.path:
        sys.path.insert(0, snooker_dir)
    # Import the snooker module
    snooker_module_path = os.path.join(snooker_dir, "snooker.py")
    if os.path.exists(snooker_module_path):
        spec = importlib.util.spec_from_file_location("snooker_module", snooker_module_path)
        snooker_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(snooker_module)
        SnookerGame = snooker_module.SnookerGame
        _snooker_available = True
    else:
        raise ImportError(f"Snooker module not found at {snooker_module_path}")
except Exception as e:
    _snooker_available = False
    SnookerGame = None
    print(f"Warning: Could not import SnookerGame: {e}")

# Mahjong game is now in a separate module
try:
    import sys
    import os
    import importlib.util
    # Add the mahjong directory to the path for import
    # Get the directory containing this file (OS_Mode.py)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    mahjong_dir = os.path.join(current_dir, "Mahjong")
    if mahjong_dir not in sys.path:
        sys.path.insert(0, mahjong_dir)
    # Import the mahjong module
    mahjong_module_path = os.path.join(mahjong_dir, "mahjong.py")
    if os.path.exists(mahjong_module_path):
        spec = importlib.util.spec_from_file_location("mahjong_module", mahjong_module_path)
        mahjong_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mahjong_module)
        MahjongGame = mahjong_module.MahjongGame
        _mahjong_available = True
    else:
        raise ImportError(f"Mahjong module not found at {mahjong_module_path}")
except Exception as e:
    _mahjong_available = False
    MahjongGame = None
    print(f"Warning: Could not import MahjongGame: {e}")

# Civitas Nihilium game is now in a separate module
try:
    import sys
    import os
    import importlib.util
    current_dir = os.path.dirname(os.path.abspath(__file__))
    civitas_dir = os.path.join(current_dir, "civitas_nihilium")
    if civitas_dir not in sys.path:
        sys.path.insert(0, civitas_dir)
    civitas_module_path = os.path.join(civitas_dir, "civitas_nihilium.py")
    if os.path.exists(civitas_module_path):
        spec = importlib.util.spec_from_file_location("civitas_nihilium_module", civitas_module_path)
        civitas_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(civitas_module)
        CivitasNihiliumGame = civitas_module.CivitasNihiliumGame
        _civitas_nihilium_available = True
    else:
        raise ImportError(f"Civitas Nihilium module not found at {civitas_module_path}")
except Exception as e:
    _civitas_nihilium_available = False
    CivitasNihiliumGame = None
    print(f"Warning: Could not import CivitasNihiliumGame: {e}")

# Pirate Radio App is now in a separate module
try:
    import sys
    import os
    import importlib.util
    # Add the pirate radio directory to the path for import
    # Get the directory containing this file (OS_Mode.py)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    os_dir = os.path.dirname(current_dir)  # Data
    pirate_radio_dir = os.path.join(os_dir, "Pirate_Radio")
    if pirate_radio_dir not in sys.path:
        sys.path.insert(0, pirate_radio_dir)
    # Import the pirate radio module
    pirate_radio_module_path = os.path.join(pirate_radio_dir, "PirateRadio.py")
    if os.path.exists(pirate_radio_module_path):
        spec = importlib.util.spec_from_file_location("pirate_radio_module", pirate_radio_module_path)
        pirate_radio_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(pirate_radio_module)
        PirateRadioApp = pirate_radio_module.PirateRadioApp
        _pirate_radio_available = True
    else:
        raise ImportError(f"Pirate Radio module not found at {pirate_radio_module_path}")
except Exception as e:
    _pirate_radio_available = False
    PirateRadioApp = None
    print(f"Warning: Could not import PirateRadioApp: {e}")

# dotSONIC Media Player
try:
    dotsonic_dir = os.path.dirname(os.path.abspath(__file__))
    dotsonic_path = os.path.join(dotsonic_dir, "dotSONIC", "DotSonicMediaPlayer.py")
    if os.path.exists(dotsonic_path):
        spec = importlib.util.spec_from_file_location("dot_sonic_module", dotsonic_path)
        dot_sonic_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(dot_sonic_module)
        DotSonicMediaPlayer = dot_sonic_module.DotSonicMediaPlayer
        _dot_sonic_available = True
    else:
        _dot_sonic_available = False
        DotSonicMediaPlayer = None
except Exception as e:
    _dot_sonic_available = False
    DotSonicMediaPlayer = None
    print(f"Warning: Could not import DotSonicMediaPlayer: {e}")

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


# Import Resolution Manager
from systems.resolution import ResolutionManager

class OSMode:
    """
    Desktop Environment OS Mode
    Renders a desktop environment with draggable icons.
    """
    persisted_network_connected = False  # Persist connection state across OS Mode instances
    
    def __init__(self, screen: pygame.Surface, res_manager: ResolutionManager, reset_bbs_callback=None, bbs_x=None, bbs_y=None, bbs_width=None, has_token_callback=None, get_recording_state_callback=None, set_recording_state_callback=None, get_notes_callback=None, save_notes_callback=None, get_user_credentials_callback=None, get_chess_stats_callback=None, save_chess_stats_callback=None, grant_token_callback=None, is_audio_streaming_callback=None, get_radio_music_callback=None, stop_radio_audio_callback=None, set_quit_state_callback=None, exit_game_callback=None, open_email_callback=None, get_inbox_emails_callback=None, save_inbox_emails_callback=None, send_mail_callback=None, get_mail_outbox_callback=None, save_mail_outbox_callback=None, get_mail_trash_callback=None, save_mail_trash_callback=None, play_mail_sound_callback=None, get_downloaded_fugamatchi_tracks_callback=None, add_downloaded_fugamatchi_track_callback=None):
        """
        Initialize OS Mode.
        """
        self.screen = screen
        self.res_manager = res_manager
        self.scale = res_manager.scale_factor
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
        self.grant_token = grant_token_callback or (lambda token, reason=None: False)
        self.is_audio_streaming = is_audio_streaming_callback or (lambda: False)
        self.get_radio_music = get_radio_music_callback or (lambda: False)
        self.stop_radio_audio = stop_radio_audio_callback or (lambda close_app=True: None)
        self.set_quit_state = set_quit_state_callback or (lambda: None)
        self.exit_game = exit_game_callback or (lambda: None)
        self.open_email = open_email_callback or (lambda: None)
        self.get_inbox_emails = get_inbox_emails_callback or (lambda: [])
        self.save_inbox_emails = save_inbox_emails_callback or (lambda emails: None)
        self.send_mail = send_mail_callback or (lambda to, subject, body: None)
        self.get_mail_outbox = get_mail_outbox_callback or (lambda: [])
        self.save_mail_outbox = save_mail_outbox_callback or (lambda emails: None)
        self.get_mail_trash = get_mail_trash_callback or (lambda: [])
        self.save_mail_trash = save_mail_trash_callback or (lambda emails: None)
        self.play_mail_sound = play_mail_sound_callback or (lambda: None)
        self.get_downloaded_fugamatchi_tracks = get_downloaded_fugamatchi_tracks_callback or (lambda: [])
        self.add_downloaded_fugamatchi_track = add_downloaded_fugamatchi_track_callback or (lambda title: None)
        self.modem_tone_sounds: Dict[str, Optional[pygame.mixer.Sound]] = {}
        self._load_modem_tone_sounds()
        
        # LAPC-1 Audio Output Stream visualizer state
        self.audio_stream_pixels: List[Dict[str, Any]] = []  # List of pixel rain drops
        self.audio_stream_pixel_colors = [
            COLOR_CYAN,
            COLOR_MAGENTA,  # Pink
            COLOR_TEAL,
            COLOR_DEEP_BLUE,  # Dark blue
            COLOR_NEON_GREEN,  # Light blue (using neon green as light blue)
            COLOR_WHITE,
            COLOR_GREY
        ]
        self.audio_stream_last_update = 0
        self.audio_stream_pixel_spawn_rate = 50  # milliseconds between pixel spawns (when audio is playing)
        # Helix pattern state
        self.audio_stream_helices: List[Dict[str, Any]] = []  # List of helix patterns
        self.audio_stream_helix_last_spawn = 0
        self.audio_stream_helix_spawn_interval = 3000  # milliseconds between helix spawns (3 seconds)
        
        # Baseline coordinates (at 2560x1440 resolution)
        self.baseline_desktop_x = 176
        self.baseline_desktop_y = 209
        
        # Scaled coordinates
        # Use coords to include potential centering padding
        self.desktop_x, self.desktop_y = self.res_manager.coords(self.baseline_desktop_x, self.baseline_desktop_y)
        
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
        # Display labels under each icon (same style as file system: Pixellari, cyan, center-aligned)
        DESKTOP_ICON_LABELS = {
            "tape-icon.png": "DATASETTE",
            "hard-drive-icon.png": "HDD",
            "modem-iconpng.png": "MODEM",
            "games-folder.png": "GAMES",
            "notes-icon.png": "NOTES",
            "sonic-icon.png": "dotSONIC",
        }
        self.icons = []
        icon_files = [
            "tape-icon.png",
            "hard-drive-icon.png",
            "modem-iconpng.png",
            "games-folder.png",
            "notes-icon.png",
        ]
        if os.path.exists(get_data_path("OS", "sonic-icon.png")):
            icon_files.append("sonic-icon.png")
        
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
                
                from_saved = icon_file in saved_positions
                icon_data = {
                    "image": icon_image,  # Normal version
                    "s_image": s_icon_image,  # Selected "S" version
                    "x": icon_x,
                    "y": icon_y,
                    "width": icon_size[0],
                    "height": icon_size[1],
                    "name": icon_file,
                    "label": DESKTOP_ICON_LABELS.get(icon_file, icon_file),
                    "selected": False,  # Track if this icon is selected
                    "dragging": False,
                    "drag_offset_x": 0,
                    "drag_offset_y": 0,
                    "from_saved": from_saved,
                }
                self.icons.append(icon_data)
                
                # Move to next position (add spacing) - only if using default positions
                if icon_file not in saved_positions:
                    current_y += icon_size[1] + int(10 * self.scale)  # 10px spacing between icons
                
            except Exception as e:
                print(f"Warning: Failed to load {icon_file}: {e}")
        
        self._align_icons_to_tape_center()
        # Apply vertical offsets to reduce overlap (percent of desktop height); only when using default positions
        self._apply_desktop_icon_vertical_offsets()
        
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
        
        # Modal state - maintain z-ordered list (bottom -> top)
        self.active_modals: List[str] = []
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
        self.notes_modal_view_scroll = 0  # Scroll position for note view mode
        
        # Documentation viewer position (baseline 2560x1440)
        self.docs_viewer_baseline_x = 1547
        self.docs_viewer_baseline_y = 37
        
        # Datasette video position (baseline 2560x1440)
        self.datasette_baseline_x = 1363
        self.datasette_baseline_y = 44
        
        # Modem modal state
        self.modem_modal_dialed_sequence = ""  # Track dialed numbers
        self.modem_modal_cursor_position = 0  # Cursor position in dialed sequence (0 = before first char, len = after last char)
        self.modem_modal_cursor_blink_timer = 0.0  # Timer for cursor blinking
        self.modem_modal_target_sequence = "0345728891"  # Target sequence to dial
        self.modem_modal_connection_messages = []  # List of connection messages
        self.modem_modal_message_index = 0  # Current message index
        self.modem_modal_message_timer = 0.0  # Timer for message progression
        self.modem_modal_current_target = None  # Tracks which endpoint we are connecting to
        self.modem_modal_external_bbs = None  # Set when routing to an outside BBS
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
        self.network_connected = OSMode.persisted_network_connected
        self.modem_modal_error_message = ""
        self.modem_modal_error_timer = 0.0
        self.modem_modal_key_flash_label: Optional[str] = None
        self.modem_modal_key_flash_timer: float = 0.0
        
        # Saved regional/locale setting (must be set before _load_games_icons which filters by region)
        # 1=American Mainland, 2=Europe, 3=American Pacific Isles (default)
        self.os_locale: int = 3
        self.mail_icon_visible: bool = False  # Whether mail icon is visible on desktop (Mainland America)
        
        # BRADSONIC-MAIL client state
        self.mail_view: str = "inbox"  # "inbox", "compose", "outbox", "trash", "reading", "settings", "connect"
        self.mail_selected_index: int = -1
        self.mail_reading_email: Optional[Dict] = None
        self.mail_compose_to: str = ""
        self.mail_compose_subject: str = ""
        self.mail_compose_body: str = ""
        self.mail_compose_active_field: str = "to"  # "to", "subject", "body"
        self.mail_scroll_offset: int = 0
        self.mail_cursor_blink_timer: float = 0.0
        self.mail_compose_cursor: int = 0
        self.mail_status_message: str = ""
        self.mail_status_timer: float = 0.0
        # BRADSONIC-MAIL separate inbox (not the BBS inbox)
        self.mail_local_inbox: List[Dict] = []
        # BRADSONIC-MAIL settings (1989 mail client technobabble)
        self.mail_settings: Dict[str, Any] = {
            "mail_from": "user@bradsonic.net",
            "display_name": "BRADSONIC User",
            "reply_to": "",
            "smtp_server": "smtp.bradsonic-relay.net",
            "smtp_port": "25",
            "pop3_server": "pop3.bradsonic-relay.net",
            "pop3_port": "110",
            "protocol": "POP3",         # POP3 or IMAP
            "auth_method": "LOGIN",     # LOGIN, PLAIN, CRAM-MD5
            "encryption": "None",       # None, SSL, TLS
            "max_msg_size": "2048",
            "check_interval": "15",
            "leave_on_server": True,
            "auto_bcc": False,
            "x_mailer_header": True,
            "mime_encoding": "quoted-printable",  # quoted-printable, base64, 7bit
            "charset": "US-ASCII",      # US-ASCII, ISO-8859-1, UTF-8
            "signature": "-- \nSent via BRADSONIC-MAIL v2.1\nInterconnecting the American Mainland and beyond!",
            "line_wrap": "76",
            "delivery_receipt": False,
            "read_receipt": False,
        }
        self.mail_settings_active_field: Optional[str] = None  # Currently focused text field key
        self.mail_settings_cursor: int = 0
        self.mail_settings_scroll: int = 0
        # BRADSONIC-MAIL server connection (outbox sends only when connected)
        self.mail_server_connected: bool = False
        self.mail_connect_phase: str = "idle"  # "idle" | "connecting" | "connected"
        self.mail_connect_technobabble_timer: float = 0.0  # Show technobabble then CONNECTED
        self.mail_rain_delivery_timer: float = -1.0  # After connect+flush, deliver Rain reply
        self.mail_pulse_timer: float = 0.0  # For COMPOSE / SEND pulse animation
        self.mail_opened_once: bool = False  # True after first open (for COMPOSE pulse)
        # BRADSONIC-MAIL connect terminal (1989 modem-style)
        self.mail_connect_terminal_lines: List[str] = []
        self.mail_connect_terminal_line_index: int = 0
        self.mail_connect_terminal_timer: float = 0.0
        self.mail_connect_terminal_complete: bool = False
        self.mail_connect_dialup_started: bool = False
        self._mail_connect_steps: List[Tuple[str, float, Optional[str]]] = []
        self._mail_connect_sent_this_session: bool = False
        self.mail_connect_terminal_scroll: int = 0

        # Games modal state
        self.games_icon_defs = [
            {
                "name": "chess",
                "file": "chess.png",
                "selected_file": "S-chess.png",
                "label": "Chess",
                "default_pos": (20, 40)
            },
            {
                "name": "solitaire",
                "file": "solitaire.png",
                "selected_file": "S-solitaire.png",
                "label": "Solitaire",
                "default_pos": (140, 40)
            },
            {
                "name": "snooker",
                "file": "snooker.png",
                "selected_file": "S-snooker.png",
                "label": "Snooker",
                "default_pos": (260, 40)
            },
            {
                "name": "mahjong",
                "file": "mahjong.png",
                "selected_file": "S-mahjong.png",
                "label": "Mahjong",
                "default_pos": (380, 40)
            },
            {
                "name": "civitas_nihilium",
                "file": "civitas_nihilium.png",
                "selected_file": "S-civitas_nihilium.png",
                "label": "Civitas Nihilium",
                "default_pos": (20, 160)
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

        # Hard drive modal state
        self.hard_drive_modal_icon: Optional[Dict[str, object]] = None
        self.hard_drive_modal_file_system_icon: Optional[Dict[str, object]] = None  # File System icon (US MAINLAND only)
        self.hard_drive_modal_content_rect: Optional[pygame.Rect] = None
        self.hard_drive_modal_dragging_icon: Optional[Dict[str, object]] = None
        self.hard_drive_modal_drag_offset = (0, 0)
        self.hard_drive_modal_last_click_time: float = 0.0
        self.hard_drive_modal_last_clicked_icon: Optional[str] = None  # "system" or "file_system"
        self._load_hard_drive_icon()

        # System folder modal state
        self.system_folder_modal_icon: Optional[Dict[str, object]] = None
        self.system_folder_modal_content_rect: Optional[pygame.Rect] = None
        self.system_folder_modal_dragging_icon: Optional[Dict[str, object]] = None
        self.system_folder_modal_drag_offset = (0, 0)
        self.system_folder_modal_last_click_time: float = 0.0
        self._load_system_folder_icon()

        # File system browser modal state (double-click File System icon when US MAINLAND)
        self.file_system_browser_path: List[str] = []  # current path (folder names)
        self.file_system_browser_items: List[Dict[str, Any]] = []  # [{ "type": "folder"|"file", "display_name": str, "real_name": str }]
        self.file_system_browser_selected_index: int = -1
        self.file_system_browser_last_click_time: float = 0.0
        self.file_system_browser_last_clicked_key: Optional[str] = None
        self.file_system_browser_dragging_item: Optional[Tuple[Dict[str, Any], int, int]] = None  # (item, offset_x, offset_y) when dragging
        self.file_system_browser_folder_icon: Optional[Dict[str, object]] = None
        self.file_system_browser_brad_icon: Optional[Dict[str, object]] = None
        self.file_system_browser_font: Optional[pygame.font.Font] = None  # Pixellari
        self._load_file_system_browser_assets()

        # Multiple terminal file windows (double-click .brad in browser opens file in new window)
        self.terminal_file_windows: List[Dict[str, Any]] = []  # [{ "content": list of str, "title": str, "position": (x,y), "scroll": int, "rect": None, "dragging": False, "drag_offset": (0,0) }]

        # Terminal application state
        self.terminal_active: bool = False
        self.terminal_text: str = ""
        self.terminal_cursor_blink_timer: float = 0.0
        self.terminal_cursor_visible: bool = True
        self.terminal_font: Optional[pygame.font.Font] = None
        self.terminal_position: Optional[Tuple[int, int]] = None  # Store terminal position for dragging
        self.terminal_dragging: bool = False
        self.terminal_drag_offset: Tuple[int, int] = (0, 0)
        self.terminal_mode: str = "command"  # "command", "admin_login_username", "admin_login_password", "admin_menu", "region_select", "message"
        self.terminal_admin_menu_selection: int = 1  # Selected menu item (1-4)
        self.terminal_region_selection: int = 1  # Selected region (1-3)
        self.terminal_message: str = ""  # Temporary message to display
        self.terminal_message_timer: float = 0.0  # Timer for message display
        self.terminal_input_buffer: str = ""  # Current input being typed
        self.terminal_login_stage: int = 0  # 0 = not logging in, 1 = username, 2 = password
        
        # (os_locale and mail_icon_visible defined earlier, before _load_games_icons)
        
        # File system state
        self.terminal_file_system_mode: bool = False  # Whether in file system mode
        self.terminal_file_system_path: List[str] = []  # Current path (list of folder names)
        self.terminal_file_content: List[str] = []  # Content of currently open file
        self.terminal_file_view_filename: str = ""  # Name of file currently displayed (e.g. LocaleProtocols.brad) for pulse hints
        self.terminal_file_scroll_index: int = 0  # Scroll position in file view
        self.terminal_file_system_base_path: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "FILE-SYSTEM")
        
        # Command history (MS-DOS style)
        self.terminal_command_history: List[str] = []  # List of previous commands
        self.terminal_history_index: int = -1  # Current position in history (-1 = not browsing, 0 = most recent)
        self.terminal_current_input_line: str = ""  # Current line being typed (before Enter)
        self.terminal_cursor_index: int = 0  # Cursor position within current input line (0 = start)
        
        self._load_terminal_font()

        # Chess game instance
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
                    self.save_chess_stats,
                    self.get_radio_music
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
                    self.bbs_width or 0,
                    self.get_radio_music
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

        # Snooker game instance
        if _snooker_available and SnookerGame:
            try:
                health_monitor_y = self.bbs_y + int(10 * self.scale) if self.bbs_y else self.desktop_y + int(10 * self.scale)
                self.snooker_game = SnookerGame(
                    self.screen,
                    self.scale,
                    self.desktop_x,
                    self.desktop_y,
                    self.desktop_size,
                    health_monitor_y,
                    self.bbs_x or 0,
                    self.bbs_width or 0,
                    self.get_radio_music
                )
            except Exception as e:
                print(f"Warning: Failed to initialize SnookerGame: {e}")
                import traceback
                traceback.print_exc()
                self.snooker_game = None
        else:
            self.snooker_game = None
            if not _snooker_available:
                print(f"Warning: Snooker module not available. _snooker_available={_snooker_available}, SnookerGame={SnookerGame}")

        # Mahjong game instance
        if _mahjong_available and MahjongGame:
            try:
                health_monitor_y = self.bbs_y + int(10 * self.scale) if self.bbs_y else self.desktop_y + int(10 * self.scale)
                self.mahjong_game = MahjongGame(
                    self.screen,
                    self.scale,
                    self.desktop_x,
                    self.desktop_y,
                    self.desktop_size,
                    health_monitor_y,
                    self.bbs_x or 0,
                    self.bbs_width or 0,
                    self.get_radio_music
                )
            except Exception as e:
                print(f"Warning: Failed to initialize MahjongGame: {e}")
                import traceback
                traceback.print_exc()
                self.mahjong_game = None
        else:
            self.mahjong_game = None
            if not _mahjong_available:
                print(f"Warning: Mahjong module not available. _mahjong_available={_mahjong_available}, MahjongGame={MahjongGame}")

        # Civitas Nihilium game instance
        if _civitas_nihilium_available and CivitasNihiliumGame:
            try:
                health_monitor_y = self.bbs_y + int(10 * self.scale) if self.bbs_y else self.desktop_y + int(10 * self.scale)
                self.civitas_game = CivitasNihiliumGame(
                    self.screen,
                    self.scale,
                    self.desktop_x,
                    self.desktop_y,
                    self.desktop_size,
                    health_monitor_y,
                    self.bbs_x or 0,
                    self.bbs_width or 0,
                    self.get_radio_music,
                    exit_app_callback=self._civitas_quit_return_to_desktop,
                )
            except Exception as e:
                print(f"Warning: Failed to initialize CivitasNihiliumGame: {e}")
                import traceback
                traceback.print_exc()
                self.civitas_game = None
        else:
            self.civitas_game = None
            if not _civitas_nihilium_available:
                print(f"Warning: Civitas Nihilium module not available. _civitas_nihilium_available={_civitas_nihilium_available}, CivitasNihiliumGame={CivitasNihiliumGame}")
        
        # dotSONIC Media Player instance
        self.dot_sonic_app = None
        self.file_system_browser_opened_from_dot_sonic = False
        if _dot_sonic_available and DotSonicMediaPlayer:
            try:
                health_monitor_y = self.bbs_y + int(10 * self.scale) if self.bbs_y else self.desktop_y + int(10 * self.scale)
                self.dot_sonic_app = DotSonicMediaPlayer(
                    self.screen, self.scale,
                    self.desktop_x, self.desktop_y, self.desktop_size, health_monitor_y,
                    get_downloaded_tracks=self.get_downloaded_fugamatchi_tracks,
                    open_file_browser_callback=self._dot_sonic_open_file_browser,
                    close_callback=self._dot_sonic_closed,
                )
            except Exception as e:
                print(f"Warning: Failed to initialize DotSonicMediaPlayer: {e}")
                self.dot_sonic_app = None
        
        # Pirate Radio App instance
        self.pirate_radio_app = None
        if _pirate_radio_available and PirateRadioApp:
            try:
                self.pirate_radio_app = PirateRadioApp(
                    self.screen,
                    self.res_manager,
                    self.desktop_x,
                    self.desktop_y
                )
            except Exception as e:
                print(f"Warning: Failed to initialize PirateRadioApp: {e}")
                self.pirate_radio_app = None

    def launch_pirate_radio(self):
        """Launch the Pirate Radio application."""
        if self.pirate_radio_app:
            self.pirate_radio_app.start()
    
    def _civitas_quit_return_to_desktop(self):
        """Called when user quits Civitas Nihilium - close window and return to desktop (do NOT exit game)."""
        if self.civitas_game and self.civitas_game.active:
            self.civitas_game.close()

    def _dot_sonic_closed(self):
        """Called when dotSONIC app closes itself - sync OS modal state."""
        self.active_modals = [name for name in self.active_modals if name != "dot_sonic"]
        if "dot_sonic" in self.modal_positions:
            del self.modal_positions["dot_sonic"]
    
    def _dot_sonic_open_file_browser(self):
        """Open file system browser for loading .sonic files into dotSONIC playlist."""
        self.file_system_browser_opened_from_dot_sonic = True
        self.file_system_browser_path = []
        self.file_system_browser_items = self._list_file_system_browser_directory()
        self.file_system_browser_selected_index = -1
        self._open_modal("file_system_browser")

    def handle_event(self, event: pygame.event.Event) -> bool:
        """
        Handle pygame events for OS Mode.
        Returns True if event was handled, False otherwise.
        """
        if self.pirate_radio_app and self.pirate_radio_app.active and self.pirate_radio_app.handle_event(event):
            return True
        # dotSONIC: pass events when dragging (window/vol/bal) so it receives MOUSEMOTION/MOUSEBUTTONUP
        if (self.dot_sonic_app and self.dot_sonic_app.active and
                (self.dot_sonic_app.dragging_window or self.dot_sonic_app.dragging_vol or self.dot_sonic_app.dragging_bal)):
            if self.dot_sonic_app.handle_event(event):
                return True
        # dotSONIC: pass KEYDOWN (arrow keys for track scroll) when top-most - before games can consume them
        if (event.type == pygame.KEYDOWN and self.dot_sonic_app and self.dot_sonic_app.active and
                "dot_sonic" in self.active_modals and self.active_modals[-1] == "dot_sonic"):
            if self.dot_sonic_app.handle_event(event):
                return True
        if self.chess_game and self.chess_game.active and self.chess_game.handle_event(event):
            return True
        if self.solitaire_game and self.solitaire_game.active and self.solitaire_game.handle_event(event):
            return True
        if self.snooker_game and self.snooker_game.active and self.snooker_game.handle_event(event):
            return True
        if self.mahjong_game and self.mahjong_game.active and self.mahjong_game.handle_event(event):
            return True
        if self.civitas_game and self.civitas_game.active and self.civitas_game.handle_event(event):
            return True
        if event.type == pygame.MOUSEMOTION:
            self.mouse_pos = event.pos
            
            # Update hover states for visual feedback
            self._update_hover_states(event.pos[0], event.pos[1])
            
            # Handle terminal file window dragging
            for win in self.terminal_file_windows:
                if win.get("dragging") and self.mouse_pressed:
                    ox, oy = win["drag_offset"]
                    new_x = self.mouse_pos[0] - ox
                    new_y = self.mouse_pos[1] - oy
                    tw = int(500 * self.scale)
                    th = int(320 * self.scale)
                    new_x = max(self.desktop_x, min(new_x, self.desktop_x + self.desktop_size[0] - tw))
                    new_y = max(self.desktop_y, min(new_y, self.desktop_y + self.desktop_size[1] - th))
                    win["position"] = (new_x, new_y)
                    return True
            # Handle terminal dragging
            if self.mouse_pressed and self.terminal_dragging:
                terminal_w = int(665 * self.scale)  # 33% larger: 500 * 1.33 = 665
                terminal_h = int(375 * self.scale)  # 25% larger: 300 * 1.25 = 375
                new_x = self.mouse_pos[0] - self.terminal_drag_offset[0]
                new_y = self.mouse_pos[1] - self.terminal_drag_offset[1]
                
                # Constrain to desktop boundaries
                new_x = max(self.desktop_rect.left, 
                           min(new_x, self.desktop_rect.right - terminal_w))
                new_y = max(self.desktop_rect.top, 
                           min(new_y, self.desktop_rect.bottom - terminal_h))
                
                self.terminal_position = (new_x, new_y)
                return True
            
            # Handle modal dragging
            if self.mouse_pressed and self.modal_dragging:
                # Calculate new position
                new_x = self.mouse_pos[0] - self.modal_drag_offset[0]
                new_y = self.mouse_pos[1] - self.modal_drag_offset[1]
                
                # Get modal size (clamped to match actual drawn size)
                modal_w, modal_h = self._get_modal_size(self.modal_dragging)
                modal_w, modal_h = self._clamp_modal_to_desktop(modal_w, modal_h)
                
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
                
                # Handle hard drive modal icon dragging
                if self.hard_drive_modal_dragging_icon and self.hard_drive_modal_content_rect:
                    if self._update_hard_drive_icon_drag(self.mouse_pos[0], self.mouse_pos[1]):
                        return True
                
                # Handle system folder modal icon dragging
                if self.system_folder_modal_dragging_icon and self.system_folder_modal_content_rect:
                    if self._update_system_folder_icon_drag(self.mouse_pos[0], self.mouse_pos[1]):
                        return True
                
                # Handle hard drive modal icon dragging
                if self.hard_drive_modal_dragging_icon and self.hard_drive_modal_content_rect:
                    if self._update_hard_drive_icon_drag(self.mouse_pos[0], self.mouse_pos[1]):
                        return True
                
                # Handle system folder modal icon dragging
                if self.system_folder_modal_dragging_icon and self.system_folder_modal_content_rect:
                    if self._update_system_folder_icon_drag(self.mouse_pos[0], self.mouse_pos[1]):
                        return True
                
                # Handle games modal icon dragging
                if self.games_modal_dragging_icon and self.games_modal_content_rect:
                    if self._update_games_icon_drag(self.mouse_pos[0], self.mouse_pos[1]):
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
                
                # Focus the top-most modal under the click (like a real OS)
                focused_modal = None
                for modal_name in reversed(self.active_modals):
                    if modal_name == "dot_sonic" and self.dot_sonic_app and self.dot_sonic_app.active:
                        modal_rect = self.dot_sonic_app.window_rect
                        if modal_rect and modal_rect.collidepoint(mouse_x, mouse_y):
                            focused_modal = modal_name
                            break
                    else:
                        modal_x, modal_y = self.modal_positions.get(modal_name, (0, 0))
                        modal_w, modal_h = self._get_modal_size(modal_name)
                        modal_w, modal_h = self._clamp_modal_to_desktop(modal_w, modal_h)
                        modal_rect = pygame.Rect(modal_x, modal_y, modal_w, modal_h)
                        if modal_rect.collidepoint(mouse_x, mouse_y):
                            focused_modal = modal_name
                            break
                if focused_modal:
                    self._focus_modal(focused_modal)
                
                # Route click to dotSONIC when it's top-most (before title bar / icon checks)
                if focused_modal == "dot_sonic" and self.dot_sonic_app and self.dot_sonic_app.active:
                    if self.dot_sonic_app.handle_event(event):
                        return True
                
                # Check if clicking on a modal title bar for dragging (but exclude close buttons)
                # Check modals in reverse order (top-most first) to handle close buttons correctly
                for modal_name in reversed(self.active_modals.copy()):
                    if modal_name == "dot_sonic":
                        continue  # dotSONIC handles its own window drag
                    modal_x, modal_y = self.modal_positions.get(modal_name, (0, 0))
                    modal_w, modal_h = self._get_modal_size(modal_name)
                    # Apply clamping to match the actual drawn modal size
                    modal_w, modal_h = self._clamp_modal_to_desktop(modal_w, modal_h)
                    if modal_w > 0 and modal_h > 0:
                        title_bar_rect = pygame.Rect(
                            modal_x,
                            modal_y,
                            modal_w,
                            self.modal_title_bar_height
                        )
                        if title_bar_rect.collidepoint(mouse_x, mouse_y):
                            # Bring the clicked modal to the front
                            self._focus_modal(modal_name)
                            # Check if clicking on close button first (exclude from dragging)
                            close_btn_size = int(20 * self.scale)
                            close_btn_x = modal_x + modal_w - close_btn_size - int(5 * self.scale)
                            close_btn_y = modal_y + int(5 * self.scale)
                            close_btn_rect = pygame.Rect(close_btn_x, close_btn_y, close_btn_size, close_btn_size)
                            
                            # If clicking on close button, handle it directly here
                            if close_btn_rect.collidepoint(mouse_x, mouse_y):
                                # Close only this specific modal
                                self._close_modal(modal_name)
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
                    # Skip mail icon when not in US Mainland (no click/launch in Europe or Pacifica)
                    if icon["name"] == "mail-icon.png" and self.os_locale != 1:
                        continue
                    # Skip dotSONIC icon when in Pacifica (only visible in Europe and US Mainland)
                    if icon["name"] == "sonic-icon.png" and self.os_locale == 3:
                        continue
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
                            # Double-click detected - open modal or launch app based on icon
                            icon_name = icon["name"]
                            modal_name = None
                            if "sonic-icon" in icon_name:
                                # Launch dotSONIC Media Player
                                if _dot_sonic_available and self.dot_sonic_app:
                                    health_monitor_y = self.bbs_y + int(10 * self.scale) if self.bbs_y else self.desktop_y + int(10 * self.scale)
                                    self.dot_sonic_app.update_desktop(self.desktop_x, self.desktop_y, self.desktop_size, health_monitor_y)
                                    self.dot_sonic_app.start()
                                    self._open_modal("dot_sonic")
                                elif _dot_sonic_available and DotSonicMediaPlayer:
                                    try:
                                        health_monitor_y = self.bbs_y + int(10 * self.scale) if self.bbs_y else self.desktop_y + int(10 * self.scale)
                                        self.dot_sonic_app = DotSonicMediaPlayer(
                                            self.screen, self.scale,
                                            self.desktop_x, self.desktop_y, self.desktop_size, health_monitor_y,
                                            get_downloaded_tracks=self.get_downloaded_fugamatchi_tracks,
                                            open_file_browser_callback=self._dot_sonic_open_file_browser,
                                            close_callback=self._dot_sonic_closed,
                                        )
                                        self.dot_sonic_app.start()
                                        self._open_modal("dot_sonic")
                                    except Exception as e:
                                        print(f"Failed to launch DotSonicMediaPlayer: {e}")
                                        import traceback
                                        traceback.print_exc()
                                modal_name = None  # Don't open modal
                            elif "tape-icon" in icon_name:
                                modal_name = "tape"
                                self.tape_modal_terminal_text = ""
                                self._stop_tape_video()
                            elif "hard-drive-icon" in icon_name:
                                modal_name = "hard_drive"
                            elif "modem-iconpng" in icon_name:
                                modal_name = "modem"
                                # Initialize dial pad state
                                self.modem_modal_dialed_sequence = ""
                                self.modem_modal_cursor_position = 0
                                self.modem_modal_cursor_blink_timer = 0.0
                                self.modem_modal_connection_messages = []
                                self.modem_modal_message_index = 0
                                self.modem_modal_message_timer = 0.0
                                self.modem_modal_should_reset_bbs = False
                                self.modem_modal_should_exit_os = False
                                self.modem_modal_connection_started = False
                                self.modem_modal_key_flash_label = None
                                self.modem_modal_key_flash_timer = 0.0
                            elif "games-folder" in icon_name:
                                modal_name = "games"
                            elif "notes-icon" in icon_name:
                                modal_name = "notes"
                            elif "mail-icon" in icon_name and self.os_locale == 1:
                                # Mail icon opens BRADSONIC-MAIL client (only in US Mainland)
                                modal_name = "mail"
                                # Sync inbox from game state when opening
                                self.mail_local_inbox = list(self.get_inbox_emails())
                                self.mail_view = "inbox"
                                self.mail_selected_index = -1
                                self.mail_reading_email = None
                                self.mail_scroll_offset = 0
                                self.mail_opened_once = True
                            
                            if modal_name:
                                # Activate modal and bring it to front
                                self._open_modal(modal_name)
                            
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
                    # Check terminal file windows (multiple .brad viewers)
                    if self._handle_terminal_file_windows_click(mouse_x, mouse_y):
                        return True
                    
                    for modal_name in reversed(self.active_modals.copy()):
                        if modal_name == "terminal":
                            rect = self._get_terminal_rect()
                            if rect.collidepoint(mouse_x, mouse_y):
                                self._focus_modal("terminal")
                                if self._handle_terminal_click(mouse_x, mouse_y):
                                    return True
                        elif modal_name == "tape":
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
                        elif modal_name == "hard_drive":
                            if self._handle_hard_drive_modal_click(mouse_x, mouse_y):
                                return True
                        elif modal_name == "system_folder":
                            if self._handle_system_folder_modal_click(mouse_x, mouse_y):
                                return True
                        elif modal_name == "file_system_browser":
                            if self._handle_file_system_browser_modal_click(mouse_x, mouse_y):
                                return True
                        elif modal_name == "mail":
                            if self._handle_mail_modal_click(mouse_x, mouse_y):
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
                # Handle file system browser drop (e.g. .sonic onto dotSONIC, or file onto folder to move)
                if self.file_system_browser_dragging_item:
                    drag_item, _ox, _oy = self.file_system_browser_dragging_item
                    mx, my = event.pos
                    handled = False
                    if self.dot_sonic_app and self.dot_sonic_app.active and self.dot_sonic_app.window_rect:
                        if self.dot_sonic_app.window_rect.collidepoint(mx, my) and drag_item.get("file_type") == "sonic":
                            self.dot_sonic_app.add_track_to_playlist(
                                drag_item["display_name"],
                                drag_item["real_name"],
                                file_type="sonic",
                                file_path=drag_item.get("file_path")
                            )
                            handled = True
                    if not handled and "file_system_browser" in self.active_modals and drag_item.get("type") == "file":
                        for item in self.file_system_browser_items:
                            if item.get("type") == "folder" and item.get("rect") and item["rect"].collidepoint(mx, my):
                                src_path = drag_item.get("file_path")
                                if not src_path and drag_item.get("file_type") == "brad":
                                    browser_path = self._get_file_system_browser_path()
                                    src_path = os.path.join(browser_path, drag_item["real_name"])
                                if src_path and os.path.isfile(src_path):
                                    dest_folder = item["real_name"]
                                    if dest_folder == "..":
                                        if self.file_system_browser_path:
                                            dest_path = os.path.join(
                                                self.terminal_file_system_base_path,
                                                *self.file_system_browser_path[:-1]
                                            )
                                        else:
                                            dest_path = self.terminal_file_system_base_path
                                    else:
                                        dest_path = os.path.join(self._get_file_system_browser_path(), dest_folder)
                                    if os.path.isdir(dest_path):
                                        try:
                                            dest_file = os.path.join(dest_path, os.path.basename(src_path))
                                            shutil.move(src_path, dest_file)
                                            self.file_system_browser_items = self._list_file_system_browser_directory()
                                        except Exception as e:
                                            print(f"Could not move file: {e}")
                                break
                    self.file_system_browser_dragging_item = None
                self.mouse_pressed = False
                self.notes_modal_dragging_selection = False
                self.games_modal_dragging_icon = None
                self.hard_drive_modal_dragging_icon = None
                self.system_folder_modal_dragging_icon = None
                self.terminal_dragging = False
                for win in self.terminal_file_windows:
                    if win.get("dragging"):
                        win["dragging"] = False
                # Stop dragging all icons
                for icon in self.icons:
                    if icon["dragging"]:
                        icon["dragging"] = False
                        return True
        
        elif event.type == pygame.MOUSEWHEEL:
            mouse_x, mouse_y = pygame.mouse.get_pos()
            # Handle mouse wheel for terminal file windows (top-most first)
            for win in reversed(self.terminal_file_windows):
                r = win.get("rect")
                if r and r.collidepoint(mouse_x, mouse_y):
                    scroll_amount = int(event.y * 2)
                    win["scroll"] = max(0, min(win["scroll"] - scroll_amount, max(0, len(win["content"]) - 1)))
                    return True
            # Handle mouse wheel scrolling for mail modal
            if "mail" in self.active_modals:
                modal_x, modal_y = self.modal_positions.get("mail", (0, 0))
                modal_w, modal_h = self._get_modal_size("mail")
                modal_w, modal_h = self._clamp_modal_to_desktop(modal_w, modal_h)
                modal_rect = pygame.Rect(modal_x, modal_y, modal_w, modal_h)
                mouse_x, mouse_y = pygame.mouse.get_pos()
                if modal_rect.collidepoint(mouse_x, mouse_y):
                    if self.mail_view in ("inbox", "outbox", "trash", "reading"):
                        scroll_amount = int(event.y * 3)
                        self.mail_scroll_offset = max(0, self.mail_scroll_offset - scroll_amount)
                        return True
                    elif self.mail_view == "connect":
                        scroll_amount = int(event.y * 3)
                        max_scroll = max(0, len(self.mail_connect_terminal_lines) - 15)
                        self.mail_connect_terminal_scroll = max(0, min(
                            self.mail_connect_terminal_scroll + scroll_amount, max_scroll
                        ))
                        return True
                    elif self.mail_view == "settings":
                        scroll_amount = int(event.y * 20)
                        self.mail_settings_scroll = max(0, self.mail_settings_scroll - scroll_amount)
                        return True
            # Handle mouse wheel scrolling for notes modal
            if "notes" in self.active_modals and not self.notes_modal_edit_mode:
                modal_x, modal_y = self.modal_positions.get("notes", (0, 0))
                modal_w, modal_h = self._get_modal_size("notes")
                modal_w, modal_h = self._clamp_modal_to_desktop(modal_w, modal_h)
                modal_rect = pygame.Rect(modal_x, modal_y, modal_w, modal_h)
                mouse_x, mouse_y = pygame.mouse.get_pos()
                
                if modal_rect.collidepoint(mouse_x, mouse_y):
                    # Scroll the notes view
                    scroll_amount = int(event.y * 3)  # Scroll 3 lines per wheel tick
                    self.notes_modal_view_scroll = max(0, self.notes_modal_view_scroll - scroll_amount)
                    return True
        
        elif event.type == pygame.KEYDOWN:
            # OS-level region hotkeys (A=US Mainland, S=Europe, D=Pacifica) - only when desktop visible
            if not self.active_modals:
                if event.key == pygame.K_a:
                    self._switch_os_region(1)
                    return True
                elif event.key == pygame.K_s:
                    self._switch_os_region(2)
                    return True
                elif event.key == pygame.K_d:
                    self._switch_os_region(3)
                    return True

            # Handle terminal keyboard input only when terminal is top-most
            if self.active_modals and self.active_modals[-1] == "terminal":
                if self._handle_terminal_keydown(event):
                    return True
            
            # Handle keyboard input for modals in z-order (top-most first)
            for modal_name in reversed(self.active_modals):
                if modal_name == "dot_sonic" and self.dot_sonic_app and self.dot_sonic_app.active:
                    if self.dot_sonic_app.handle_event(event):
                        return True
                    break
                elif modal_name == "notes":
                    if self.notes_modal_edit_mode:
                        if self._notes_handle_keydown(event):
                            return True
                    else:
                        # Handle scrolling in view mode
                        if self._notes_handle_view_scroll(event):
                            return True
                    break  # Notes modal captured focus but didn't handle key
                elif modal_name == "mail" and self.mail_view in ("compose", "settings"):
                    if self._mail_handle_keydown(event):
                        return True
                    break  # Mail modal captured focus
                elif modal_name == "modem" and not self.modem_modal_connection_started:
                    if self._modem_handle_keydown(event):
                        return True
                    break  # Modem modal captured focus but didn't handle key

        # In OS mode, ESC must never open the BBS - consume any unhandled ESC
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            return True

        elif event.type == pygame.TEXTINPUT:
            # Handle text input for modals in z-order (top-most first)
            for modal_name in reversed(self.active_modals):
                if modal_name == "notes" and self.notes_modal_edit_mode:
                    if self._notes_handle_textinput(event.text):
                        return True
                    break  # Notes modal captured focus but didn't handle text
                elif modal_name == "mail" and self.mail_view in ("compose", "settings"):
                    if self._mail_handle_textinput(event.text):
                        return True
                    break  # Mail modal captured focus
                elif modal_name == "modem" and not self.modem_modal_connection_started:
                    if self._modem_handle_textinput(event.text):
                        return True
                    break  # Modem modal captured focus but didn't handle text
        
        return False
    
    def _get_modal_size(self, modal_name: str) -> Tuple[int, int]:
        """Get modal dimensions for a given modal name."""
        gap = int(20 * self.scale)
        
        if modal_name == "tape":
            # Tape modal dimensions (smaller window)
            modal_w = int(500 * self.scale)
            modal_h = int(400 * self.scale) + self.modal_title_bar_height
        elif modal_name == "modem":
            # Modem dimensions (increased height for larger terminal)
            modal_w = int(340 * self.scale)
            modal_h = int(680 * self.scale) + self.modal_title_bar_height
        elif modal_name == "notes":
            # Notes modal dimensions
            modal_w = int(700 * self.scale)
            modal_h = int(500 * self.scale) + self.modal_title_bar_height
        elif modal_name == "games":
            modal_w = int(560 * self.scale)
            modal_h = int(420 * self.scale) + self.modal_title_bar_height
        elif modal_name == "hard_drive":
            modal_w = int(400 * self.scale)
            modal_h = int(300 * self.scale) + self.modal_title_bar_height
        elif modal_name == "system_folder":
            modal_w = int(400 * self.scale)
            modal_h = int(300 * self.scale) + self.modal_title_bar_height
        elif modal_name == "file_system_browser":
            modal_w = int(480 * self.scale)
            modal_h = int(360 * self.scale) + self.modal_title_bar_height
        elif modal_name == "mail":
            modal_w = int(780 * self.scale)
            modal_h = int(580 * self.scale) + self.modal_title_bar_height
        elif modal_name == "terminal":
            modal_w = int(665 * self.scale)
            modal_h = int(375 * self.scale)
        elif modal_name == "dot_sonic" and self.dot_sonic_app and self.dot_sonic_app.active and self.dot_sonic_app.window_rect:
            return self.dot_sonic_app.window_rect.size
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
        
        # Datasette (tape) modal uses original positioning - don't move it
        if modal_name == "tape":
            # Position modal with margin from desktop edges (original behavior)
            margin = int(50 * self.scale)
            modal_x = self.desktop_x + margin
            modal_y = self.desktop_y + margin
            
            # Ensure modal doesn't extend beyond desktop boundaries
            max_x = self.desktop_x + self.desktop_size[0] - modal_w - margin
            max_y = self.desktop_y + self.desktop_size[1] - modal_h - margin
            
            modal_x = max(self.desktop_x + margin, min(modal_x, max_x))
            modal_y = max(self.desktop_y + margin, min(modal_y, max_y))
            
            return (modal_x, modal_y)
        
        # For all other modals: count how many are open (excluding tape) to determine position
        screen_w, screen_h = self.screen.get_size()
        
        # Count active modals excluding tape and the current one (if it's already in the list)
        other_modals_count = 0
        for other_modal_name in self.active_modals:
            if other_modal_name != "tape" and other_modal_name != modal_name:
                other_modals_count += 1
        
        # First modal (excluding tape): 15% from left, 18% from top
        # Second modal (excluding tape): 22% from left, 23% from top
        if other_modals_count == 0:
            # First modal
            modal_x = int(screen_w * 0.15)
            modal_y = int(screen_h * 0.18)
        else:
            # Second modal (or more - they all use the second position for now)
            modal_x = int(screen_w * 0.22)
            modal_y = int(screen_h * 0.23)
        
        # Ensure modal doesn't extend beyond desktop boundaries
        max_x = self.desktop_x + self.desktop_size[0] - modal_w
        max_y = self.desktop_y + self.desktop_size[1] - modal_h
        min_x = self.desktop_x
        min_y = self.desktop_y
        
        modal_x = max(min_x, min(modal_x, max_x))
        modal_y = max(min_y, min(modal_y, max_y))
        
        return (modal_x, modal_y)
    
    def _focus_modal(self, modal_name: str):
        """Bring a modal to the front of the z-order."""
        if modal_name not in self.active_modals:
            return
        
        self.active_modals = [name for name in self.active_modals if name != modal_name]
        self.active_modals.append(modal_name)
    
    def _open_modal(self, modal_name: str):
        """Ensure a modal is active, positioned, and top-most."""
        if modal_name == "terminal":
            if modal_name not in self.active_modals:
                self.active_modals.append(modal_name)
            self._focus_modal(modal_name)
            return
        if modal_name == "dot_sonic":
            if modal_name not in self.active_modals:
                self.active_modals.append(modal_name)
            self._focus_modal(modal_name)
            return  # dotSONIC manages its own window position
        if modal_name not in self.active_modals:
            self.active_modals.append(modal_name)
        # Always bring to front when (re)opening
        self._focus_modal(modal_name)
        
        if modal_name not in self.modal_positions:
            modal_w, modal_h = self._get_modal_size(modal_name)
            modal_x, modal_y = self._get_modal_position(modal_w, modal_h, modal_name)
            self.modal_positions[modal_name] = (modal_x, modal_y)
    
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
            # Close only the tape modal
            self._close_modal("tape")
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
            # Check if already recording - prevent starting new recording if LAPC1 is recording
            is_recording, _ = self.get_recording_state()
            if is_recording:
                # Show error message in terminal
                self.tape_modal_terminal_lines = []
                self.tape_modal_terminal_lines.append("Unable to Start Recording. Data Currently Recording")
                self.tape_modal_terminal_text = "\n".join(self.tape_modal_terminal_lines)
                self.tape_modal_message_timer = 0.0
                return True
            
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
        modal_w, modal_h = self._get_modal_size("modem")
        
        # Clamp modal to fit within desktop boundaries
        modal_w, modal_h = self._clamp_modal_to_desktop(modal_w, modal_h)
        modal_x, modal_y = self.modal_positions.get("modem", (0, 0))
        
        # Check if clicking on close button in title bar
        close_btn_size = int(20 * self.scale)
        close_btn_x = modal_x + modal_w - close_btn_size - int(5 * self.scale)
        close_btn_y = modal_y + int(5 * self.scale)
        close_btn_rect = pygame.Rect(close_btn_x, close_btn_y, close_btn_size, close_btn_size)
        if close_btn_rect.collidepoint(mouse_x, mouse_y):
            # Close only the modem modal
            self._close_modal("modem")
            return True
        
        modal_rect = pygame.Rect(modal_x, modal_y, modal_w, modal_h)
        if not modal_rect.collidepoint(mouse_x, mouse_y):
            return False
        
        gap = int(20 * self.scale)
        terminal_h = int(200 * self.scale)  # Updated to match drawing code (was 120)
        terminal_y = modal_y + self.modal_title_bar_height + gap
        
        dial_start_y = terminal_y + terminal_h + gap
        button_size = int(42 * self.scale)
        button_spacing = int(10 * self.scale)
        
        # Calculate centering for dial pad matching _draw_modem_modal
        dial_width = 3 * button_size + 2 * button_spacing
        dial_start_x = modal_x + (modal_w - dial_width) // 2

        # CONNECT and DISCONNECT buttons side by side (matching drawing code)
        action_btn_y = dial_start_y + 4 * (button_size + button_spacing) + int(5 * self.scale)
        action_btn_h = int(48 * self.scale)  # Button height (increased by 25%)
        action_btn_spacing = int(8 * self.scale)
        action_btn_w = (dial_width - action_btn_spacing) // 2
        
        call_btn_x = dial_start_x
        call_btn_y = action_btn_y
        call_btn_w = action_btn_w
        call_btn_h = action_btn_h
        
        disconnect_btn_x = dial_start_x + action_btn_w + action_btn_spacing
        disconnect_btn_y = action_btn_y
        disconnect_btn_rect = pygame.Rect(disconnect_btn_x, disconnect_btn_y, action_btn_w, action_btn_h)

        # When connection is active/connecting, only DISCONNECT remains clickable
        if self.modem_modal_connection_started:
            if disconnect_btn_rect.collidepoint(mouse_x, mouse_y):
                self._disconnect_network()
                return True
            return False

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
                    self._flash_modem_dial_key(button_label)
                    # Add to dialed sequence
                    if len(self.modem_modal_dialed_sequence) < 20:  # Limit length
                        # Insert at cursor position
                        cursor_pos = self.modem_modal_cursor_position
                        self.modem_modal_dialed_sequence = (
                            self.modem_modal_dialed_sequence[:cursor_pos] + 
                            button_label + 
                            self.modem_modal_dialed_sequence[cursor_pos:]
                        )
                        self.modem_modal_cursor_position += 1
                        self.modem_modal_cursor_blink_timer = 0.0  # Reset cursor blink
                        self._play_modem_key_tone(button_label)
                    return True
        
        # CONNECT button
        call_btn_rect = pygame.Rect(call_btn_x, call_btn_y, call_btn_w, call_btn_h)
        
        if call_btn_rect.collidepoint(mouse_x, mouse_y):
            if self.network_connected:
                self._show_modem_error("DISCONNECT BEFORE CONNECTING")
                return True
            connections = self._get_modem_connections()
            sequence = self.modem_modal_dialed_sequence
            if sequence in connections:
                self._start_modem_connection(connections[sequence])
            elif sequence:
                # Show error message for invalid number (don't clear to allow correction)
                self._show_modem_error("INVALID NUMBER")
            else:
                # No number entered
                self._show_modem_error("ENTER A NUMBER")
            return True

        # DISCONNECT button (same width under CONNECT)
        if disconnect_btn_rect.collidepoint(mouse_x, mouse_y):
            self._disconnect_network()
            return True
                
        return False

    def _get_modem_connections(self):
        """Return the set of dialable connections keyed by number."""
        connections = {
            "0345728891": {
                "target": "glyphis",
                "number": "0345728891",
                "messages": [
                    "Initializing modem connection...",
                    "Dialing 0345728891...",
                    "Establishing connection...",
                    "Handshaking...",
                    "Packets found!",
                    "Loading data...",
                    "Connection established!"
                ],
                "delays": [2.1, 2.1, 4.0, 4.0, 3.0, 4.0, 3.0],
                "grant_token": "MODEM1ST",
            }
        }

        if self.has_token("PAPERCRANEBBS"):
            connections["08277341945"] = {
                "target": "paper_crane",
                "number": "08277341945",
                "messages": [
                    "Initializing modem connection...",
                    "Dialing 08277341945...",
                    "Establishing connection...",
                    "Handshaking...",
                    "Packets found!",
                    "Routing to PAPER CRANE...",
                    "Connection established!"
                ],
                "delays": [2.1, 2.1, 4.0, 4.0, 3.0, 4.0, 3.0],
            }

        if self.has_token("ECHOCHAMBER"):
            connections["0757421989"] = {
                "target": "echo_chamber",
                "number": "0757421989",
                "messages": [
                    "Initializing modem connection...",
                    "Dialing 0757421989...",
                    "Establishing connection...",
                    "Handshaking...",
                    "Packets found!",
                    "Routing to ECHO CHAMBER...",
                    "Connection established!"
                ],
                "delays": [2.1, 2.1, 4.0, 4.0, 3.0, 4.0, 3.0],
            }

        if self.has_token("NEVERAGAINBBS"):
            connections["0340899891"] = {
                "target": "never_again",
                "number": "0340899891",
                "messages": [
                    "Initializing modem connection...",
                    "Dialing 0340899891...",
                    "Establishing connection...",
                    "Handshaking...",
                    "Packets found!",
                    "Routing to NEVER AGAIN...",
                    "Connection established!"
                ],
                "delays": [2.1, 2.1, 4.0, 4.0, 3.0, 4.0, 3.0],
            }

        return connections

    def _start_modem_connection(self, config: dict) -> None:
        """Begin modem connection sequence for the given config."""
        self.modem_modal_connection_started = True
        self.modem_modal_current_target = config.get("target")
        self.modem_modal_external_bbs = None
        self._play_modem_dial_sound()
        self.modem_packet_sprites.clear()
        self.modem_packet_spawn_timer = 0.0
        self.modem_modal_connection_messages = list(config.get("messages", []))
        self.modem_modal_message_delays = list(config.get("delays", []))
        self.modem_modal_message_index = 0
        self.modem_modal_message_timer = 0.0

        grant_token = config.get("grant_token")
        if grant_token and self.grant_token:
            self.grant_token(grant_token, "Modem connection established")

    def _load_modem_tone_sounds(self) -> None:
        """Preload modem keypad tones (0-9, *, #) if available."""
        labels = [str(i) for i in range(10)] + ["*", "#"]
        for label in labels:
            try:
                path = get_data_path("Audio", f"{label}.wav")
                if os.path.exists(path):
                    self.modem_tone_sounds[label] = pygame.mixer.Sound(path)
                else:
                    self.modem_tone_sounds[label] = None
            except Exception:
                self.modem_tone_sounds[label] = None

    def _play_modem_key_tone(self, label: str) -> None:
        """Play the keypad tone for the given label if available."""
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
        except Exception:
            return
        sound = self.modem_tone_sounds.get(label)
        if sound:
            try:
                sound.play()
            except Exception:
                pass

    def _flash_modem_dial_key(self, label: str, duration: float = 0.12) -> None:
        """Briefly highlight a dial pad key (mouse + keyboard)."""
        if self.modem_modal_connection_started:
            return
        self.modem_modal_key_flash_label = label
        self.modem_modal_key_flash_timer = max(0.0, float(duration))

    def _disconnect_network(self) -> None:
        """Tear down network link and stop any radio audio."""
        self.network_connected = False
        OSMode.persisted_network_connected = False
        self.modem_modal_dialed_sequence = ""
        self.modem_modal_cursor_position = 0
        self.modem_modal_cursor_blink_timer = 0.0
        self.modem_modal_key_flash_label = None
        self.modem_modal_key_flash_timer = 0.0
        self.modem_modal_connection_started = False
        self.modem_modal_connection_messages = []
        self.modem_modal_message_index = 0
        self.modem_modal_message_timer = 0.0
        self.modem_modal_current_target = None
        self.modem_modal_external_bbs = None
        self.modem_packet_sprites.clear()
        self.modem_wave_phase = 0.0
        self.modem_packet_spawn_timer = 0.0
        self._stop_modem_dial_sound()

        # Stop OS-mode Pirate Radio app if running
        if self.pirate_radio_app:
            try:
                self.pirate_radio_app.stop_audio()
                if self.pirate_radio_app.active:
                    self.pirate_radio_app.close()
            except Exception:
                pass

        # Notify host to halt BBS-level pirate radio audio
        try:
            self.stop_radio_audio(close_app=True)
        except Exception:
            pass

    def _show_modem_error(self, message: str, duration: float = 3.0) -> None:
        """Display a transient message in the modem console."""
        self.modem_modal_error_message = message
        self.modem_modal_error_timer = duration
    
    def _modem_handle_keydown(self, event: pygame.event.Event) -> bool:
        """Handle keyboard input for modem modal (arrow keys, backspace, enter).
        
        Returns True to consume the event when the modem modal has focus.
        """
        if self.modem_modal_connection_started:
            return False
        
        if event.key == pygame.K_BACKSPACE:
            # Delete character before cursor
            cursor_pos = self.modem_modal_cursor_position
            if cursor_pos > 0:
                self.modem_modal_dialed_sequence = (
                    self.modem_modal_dialed_sequence[:cursor_pos - 1] + 
                    self.modem_modal_dialed_sequence[cursor_pos:]
                )
                self.modem_modal_cursor_position -= 1
                self.modem_modal_cursor_blink_timer = 0.0  # Reset cursor blink
            return True
        elif event.key == pygame.K_LEFT:
            # Move cursor left
            if self.modem_modal_cursor_position > 0:
                self.modem_modal_cursor_position -= 1
                self.modem_modal_cursor_blink_timer = 0.0  # Reset cursor blink
            return True
        elif event.key == pygame.K_RIGHT:
            # Move cursor right
            if self.modem_modal_cursor_position < len(self.modem_modal_dialed_sequence):
                self.modem_modal_cursor_position += 1
                self.modem_modal_cursor_blink_timer = 0.0  # Reset cursor blink
            return True
        elif event.key == pygame.K_HOME:
            # Move cursor to start
            self.modem_modal_cursor_position = 0
            self.modem_modal_cursor_blink_timer = 0.0
            return True
        elif event.key == pygame.K_END:
            # Move cursor to end
            self.modem_modal_cursor_position = len(self.modem_modal_dialed_sequence)
            self.modem_modal_cursor_blink_timer = 0.0
            return True
        elif event.key == pygame.K_DELETE:
            # Delete character at cursor
            cursor_pos = self.modem_modal_cursor_position
            if cursor_pos < len(self.modem_modal_dialed_sequence):
                self.modem_modal_dialed_sequence = (
                    self.modem_modal_dialed_sequence[:cursor_pos] + 
                    self.modem_modal_dialed_sequence[cursor_pos + 1:]
                )
                self.modem_modal_cursor_blink_timer = 0.0  # Reset cursor blink
            return True
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            # Enter key triggers the CONNECT action
            if self.network_connected:
                self._show_modem_error("DISCONNECT BEFORE CONNECTING")
            else:
                connections = self._get_modem_connections()
                sequence = self.modem_modal_dialed_sequence
                if sequence in connections:
                    self._start_modem_connection(connections[sequence])
                elif sequence:
                    # Show error for invalid number
                    self._show_modem_error("INVALID NUMBER")
            return True
        elif event.key == pygame.K_ESCAPE:
            # Escape clears the dialed sequence
            if self.modem_modal_dialed_sequence:
                self.modem_modal_dialed_sequence = ""
                self.modem_modal_cursor_position = 0
                self.modem_modal_cursor_blink_timer = 0.0
            return True
        
        # Consume other common keys to prevent them from triggering other handlers
        # while the modem modal has focus
        return True
    
    def _modem_handle_textinput(self, text: str) -> bool:
        """Handle text input for modem modal (numbers only).
        
        Returns True to consume the event and prevent it from bubbling up
        to other handlers, even for invalid characters.
        """
        if self.modem_modal_connection_started:
            return False
        
        # Only accept digits, *, and #
        if text and text in "0123456789*#":
            self._flash_modem_dial_key(text)
            if len(self.modem_modal_dialed_sequence) < 20:  # Limit length
                cursor_pos = self.modem_modal_cursor_position
                self.modem_modal_dialed_sequence = (
                    self.modem_modal_dialed_sequence[:cursor_pos] + 
                    text + 
                    self.modem_modal_dialed_sequence[cursor_pos:]
                )
                self.modem_modal_cursor_position += 1
                self.modem_modal_cursor_blink_timer = 0.0  # Reset cursor blink
                self._play_modem_key_tone(text)
        
        # Always return True when modem modal is active to consume the event
        # and prevent keyboard input from triggering other handlers
        return True
    
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
            # Close only the games modal
            self._close_modal("games")
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
                            self.save_chess_stats,
                            self.get_radio_music
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
                            self.bbs_width or 0,
                            self.get_radio_music
                        )
                        self.solitaire_game.start()
                    except Exception as e:
                        print(f"Failed to initialize SolitaireGame on demand: {e}")
                        import traceback
                        traceback.print_exc()
        elif icon_name == "snooker":
            if self.snooker_game:
                # Calculate health monitor Y position
                health_monitor_y = self.bbs_y + int(10 * self.scale) if self.bbs_y else self.desktop_y + int(10 * self.scale)
                # Update desktop coordinates before starting
                self.snooker_game.update_desktop(self.desktop_x, self.desktop_y, self.desktop_size, health_monitor_y)
                self.snooker_game.start()
            else:
                print(f"Snooker game module not available. _snooker_available={_snooker_available}, SnookerGame={SnookerGame}, self.snooker_game={getattr(self, 'snooker_game', 'NOT SET')}")
                # Try to initialize if it wasn't initialized before
                if _snooker_available and SnookerGame:
                    try:
                        health_monitor_y = self.bbs_y + int(10 * self.scale) if self.bbs_y else self.desktop_y + int(10 * self.scale)
                        self.snooker_game = SnookerGame(
                            self.screen,
                            self.scale,
                            self.desktop_x,
                            self.desktop_y,
                            self.desktop_size,
                            health_monitor_y,
                            self.bbs_x or 0,
                            self.bbs_width or 0,
                            self.get_radio_music
                        )
                        self.snooker_game.start()
                    except Exception as e:
                        print(f"Failed to initialize SnookerGame on demand: {e}")
                        import traceback
                        traceback.print_exc()
        elif icon_name == "mahjong":
            if self.mahjong_game:
                health_monitor_y = self.bbs_y + int(10 * self.scale) if self.bbs_y else self.desktop_y + int(10 * self.scale)
                self.mahjong_game.update_desktop(self.desktop_x, self.desktop_y, self.desktop_size, health_monitor_y)
                self.mahjong_game.start()
            else:
                print(f"Mahjong game module not available. _mahjong_available={_mahjong_available}, MahjongGame={MahjongGame}, self.mahjong_game={getattr(self, 'mahjong_game', 'NOT SET')}")
                if _mahjong_available and MahjongGame:
                    try:
                        health_monitor_y = self.bbs_y + int(10 * self.scale) if self.bbs_y else self.desktop_y + int(10 * self.scale)
                        self.mahjong_game = MahjongGame(
                            self.screen,
                            self.scale,
                            self.desktop_x,
                            self.desktop_y,
                            self.desktop_size,
                            health_monitor_y,
                            self.bbs_x or 0,
                            self.bbs_width or 0,
                            self.get_radio_music
                        )
                        self.mahjong_game.start()
                    except Exception as e:
                        print(f"Failed to initialize MahjongGame on demand: {e}")
                        import traceback
                        traceback.print_exc()
        elif icon_name in ("civitas_nihilium", "civitas"):
            if self.civitas_game:
                health_monitor_y = self.bbs_y + int(10 * self.scale) if self.bbs_y else self.desktop_y + int(10 * self.scale)
                self.civitas_game.update_desktop(self.desktop_x, self.desktop_y, self.desktop_size, health_monitor_y)
                self.civitas_game.start()
            else:
                print(f"Civitas Nihilium module not available. _civitas_nihilium_available={_civitas_nihilium_available}, self.civitas_game={getattr(self, 'civitas_game', 'NOT SET')}")
                if _civitas_nihilium_available and CivitasNihiliumGame:
                    try:
                        health_monitor_y = self.bbs_y + int(10 * self.scale) if self.bbs_y else self.desktop_y + int(10 * self.scale)
                        self.civitas_game = CivitasNihiliumGame(
                            self.screen,
                            self.scale,
                            self.desktop_x,
                            self.desktop_y,
                            self.desktop_size,
                            health_monitor_y,
                            self.bbs_x or 0,
                            self.bbs_width or 0,
                            self.get_radio_music,
                            exit_app_callback=self._civitas_quit_return_to_desktop,
                        )
                        self.civitas_game.start()
                    except Exception as e:
                        print(f"Failed to initialize CivitasNihiliumGame on demand: {e}")
                        import traceback
                        traceback.print_exc()
        else:
            print(f"{icon_name.title()} is not available yet.")

    def _play_modem_dial_sound(self) -> None:
        """Play dialup.wav - mixes with background music (does not stop it)."""
        if not pygame.mixer.get_init():
            try:
                pygame.mixer.init()
            except Exception:
                print("Warning: Could not initialize mixer for dialup.wav")
                return
        try:
            # Do NOT stop music - dialup plays on a sound channel, mixes with music
            if self.modem_dial_sound:
                try:
                    self.modem_dial_sound.stop()
                except Exception:
                    pass
            
            # Load and play dialup.wav
            audio_path = get_data_path("Audio", "dialup.wav")
            if os.path.exists(audio_path):
                try:
                    self.modem_dial_sound = pygame.mixer.Sound(audio_path)
                    # Play the sound - this will interrupt other sounds
                    channel = self.modem_dial_sound.play()
                    self.modem_dial_sound_playing = True
                    print(f"DEBUG: Playing dialup.wav from {audio_path}")
                except Exception as e:
                    print(f"Warning: Failed to load/play dialup.wav: {e}")
                    self.modem_dial_sound = None
                    self.modem_dial_sound_playing = False
            else:
                print(f"Warning: dialup.wav not found at {audio_path}")
                # Try alternative path
                alt_path = get_data_path("OS", "Audio", "dialup.wav")
                if os.path.exists(alt_path):
                    try:
                        self.modem_dial_sound = pygame.mixer.Sound(alt_path)
                        channel = self.modem_dial_sound.play()
                        self.modem_dial_sound_playing = True
                        print(f"DEBUG: Playing dialup.wav from alternative path {alt_path}")
                    except Exception as e:
                        print(f"Warning: Failed to load/play dialup.wav from alt path: {e}")
        except Exception as e:
            print(f"Warning: Failed to play dialup.wav: {e}")
            import traceback
            traceback.print_exc()
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
            # Spawn packets at the top of the terminal, not outside
            packet = {
                "x": random.uniform(terminal_left, terminal_right),
                "y": terminal_top + random.uniform(5, 15),  # Start within terminal
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
            # Only keep packets that haven't completely left the terminal
            if packet["y"] < terminal_bottom:
                survivors.append(packet)
        self.modem_packet_sprites = survivors

    def _draw_modem_packet_effect(self, terminal_rect: pygame.Rect) -> None:
        """Draw packet effect only within the terminal rectangle."""
        if not self.modem_modal_connection_started or not terminal_rect:
            return

        # Clip drawing to terminal rect
        clip_rect = self.screen.get_clip()
        self.screen.set_clip(terminal_rect)
        
        try:
            # Draw packets only if they're within terminal bounds
            for packet in self.modem_packet_sprites:
                packet_y = int(packet["y"])
                # Only draw if packet is within terminal bounds
                if terminal_rect.top <= packet_y <= terminal_rect.bottom:
                    start = (int(packet["x"]), packet_y)
                    end = (int(packet["x"]), int(packet["y"] + packet["length"]))
                    # Clamp end point to terminal bottom
                    if end[1] > terminal_rect.bottom:
                        end = (end[0], terminal_rect.bottom)
                    pygame.draw.line(self.screen, packet["color"], start, end, 2)

            # Draw wave effect only within terminal
            amplitude = max(int(7 * self.scale), 3)
            wave_colors = [(0, 255, 200), (255, 80, 200)]
            width = terminal_rect.width
            if width > 1:
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
        finally:
            # Restore clip
            self.screen.set_clip(clip_rect)

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
            # Close only the notes modal (edit mode exit is handled in _close_modal)
            self._close_modal("notes")
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
                    # Reset scroll when switching notes
                    if self.notes_modal_current_tab != index:
                        self.notes_modal_view_scroll = 0
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
        """Start playing the Datasette_Load.mp4 video with chroma key using GPU acceleration."""
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
            # Try to use GPU-accelerated backend for Datasette_Load.mp4
            # MSMF (Microsoft Media Foundation) supports hardware decoding on Windows 10/11
            gpu_backend_used = False
            
            # First try MSMF backend (hardware-accelerated on Windows)
            if _CAP_MSMF is not None:
                try:
                    self.tape_modal_video_cap = cv2.VideoCapture(video_path, _CAP_MSMF)
                    if self.tape_modal_video_cap.isOpened():
                        # MSMF backend on Windows 10/11 automatically uses GPU hardware acceleration
                        # when available. The system's GPU decoder will be used automatically.
                        # We can set buffer size for smoother playback:
                        try:
                            # Minimize buffer for lower latency (1 frame buffer)
                            self.tape_modal_video_cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                        except:
                            pass  # Ignore if property setting fails
                        gpu_backend_used = True
                        print("DEBUG: Using MSMF backend (GPU hardware acceleration enabled) for Datasette_Load.mp4")
                except Exception as e:
                    print(f"Warning: Failed to use MSMF backend: {e}")
                    self.tape_modal_video_cap = None
            
            # Fallback to DirectShow (also supports hardware acceleration on Windows)
            if not gpu_backend_used and _CAP_DSHOW is not None:
                try:
                    self.tape_modal_video_cap = cv2.VideoCapture(video_path, _CAP_DSHOW)
                    if self.tape_modal_video_cap.isOpened():
                        gpu_backend_used = True
                        print("DEBUG: Using DirectShow backend (may use GPU acceleration) for Datasette_Load.mp4")
                except Exception as e:
                    print(f"Warning: Failed to use DirectShow backend: {e}")
                    self.tape_modal_video_cap = None
            
            # Final fallback to default backend (CPU-based)
            if not gpu_backend_used:
                self.tape_modal_video_cap = cv2.VideoCapture(video_path)
                print("DEBUG: Using default backend (CPU-based) for Datasette_Load.mp4")
            
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
            
            # Read first frame immediately to prevent "paused" appearance
            ret, first_frame = self.tape_modal_video_cap.read()
            if ret and first_frame is not None:
                # Process first frame immediately
                frame_rgba = self._apply_chroma_key(first_frame)
                if frame_rgba is not None:
                    if self.tape_modal_video_display_size:
                        frame_resized = cv2.resize(frame_rgba, self.tape_modal_video_display_size, interpolation=cv2.INTER_LINEAR)
                    else:
                        frame_resized = frame_rgba
                    
                    # Convert to pygame surface
                    height, width = frame_resized.shape[:2]
                    frame_resized = np.clip(frame_resized, 0, 255).astype(np.uint8)
                    rgb_data = frame_resized[:, :, :3]
                    alpha_data = frame_resized[:, :, 3]
                    # Apply initial fade alpha (0.0 for fade-in start)
                    alpha_data = (alpha_data * self.tape_modal_video_fade_alpha).astype(np.uint8)
                    rgb_swapped = np.swapaxes(rgb_data, 0, 1)
                    frame_surface = pygame.surfarray.make_surface(rgb_swapped)
                    frame_surface = frame_surface.convert_alpha()
                    alpha_swapped = np.swapaxes(alpha_data, 0, 1)
                    alpha_array = pygame.surfarray.pixels_alpha(frame_surface)
                    alpha_array[:] = alpha_swapped
                    del alpha_array
                    self.tape_modal_video_frame = frame_surface
            
            self.tape_modal_video_playing = True
        except Exception as e:
            print(f"Warning: Failed to start video: {e}")
            self._stop_tape_video()
    
    def _stop_tape_video(self):
        """Stop playing the tape video."""
        was_playing = self.tape_modal_video_playing
        self.tape_modal_video_playing = False
        if self.tape_modal_video_cap:
            self.tape_modal_video_cap.release()
            self.tape_modal_video_cap = None
        self.tape_modal_video_frame = None
        # Only stop music if the Datasette video was actually playing
        # (avoids killing pirate radio or other audio)
        if was_playing and pygame.mixer.music.get_busy():
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
        # Update Pirate Radio App if active
        if self.pirate_radio_app and self.pirate_radio_app.active:
            self.pirate_radio_app.update()

        # Decay modem modal error message timer
        if self.modem_modal_error_message:
            self.modem_modal_error_timer = max(0.0, self.modem_modal_error_timer - dt)
            if self.modem_modal_error_timer <= 0:
                self.modem_modal_error_message = ""

        # Decay BRADSONIC-MAIL status message timer
        if self.mail_status_timer > 0:
            self.mail_status_timer = max(0.0, self.mail_status_timer - dt)
            if self.mail_status_timer <= 0:
                self.mail_status_message = ""

        # BRADSONIC-MAIL: connect button technobabble then CONNECTED (legacy flow)
        if self.mail_connect_phase == "connecting" and self.mail_connect_technobabble_timer >= 0:
            self.mail_connect_technobabble_timer -= dt
            if self.mail_connect_technobabble_timer <= 0:
                self.mail_connect_phase = "connected"
                self.mail_server_connected = True
                outbox = self.get_mail_outbox()
                sent_im_in_to_rain = any(
                    (msg.get("recipient", "") or "").strip().lower() == "rain@ciphernet.net"
                    and "i'm in" in ((msg.get("subject", "") or "").lower())
                    for msg in outbox
                )
                for msg in outbox:
                    self.send_mail(msg.get("recipient", ""), msg.get("subject", ""), msg.get("body", ""))
                self.save_mail_outbox([])
                if sent_im_in_to_rain:
                    self.mail_rain_delivery_timer = 30.0  # Rain's reply takes at least 30 sec

        # BRADSONIC-MAIL: deliver Rain reply (only when "I'm in" was sent to Rain)
        if self.mail_rain_delivery_timer > 0:
            self.mail_rain_delivery_timer -= dt
            if self.mail_rain_delivery_timer <= 0:
                username, _ = self.get_user_credentials()
                rain_email = {
                    "id": f"rain_{int(time.time())}",
                    "sender": "rain@ciphernet.net",
                    "recipient": self.mail_settings.get("mail_from", "user@bradsonic.net"),
                    "subject": RAIN_REPLY_SUBJECT,
                    "body": _get_rain_reply_body(username),
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "read": False,
                }
                self.mail_local_inbox.insert(0, rain_email)
                self.save_inbox_emails(self.mail_local_inbox)
                self.play_mail_sound()
                self.mail_rain_delivery_timer = -1.0

        # Mail pulse timer for COMPOSE / SEND
        self.mail_pulse_timer += dt

        # BRADSONIC-MAIL CONNECT view: terminal sequence (Modem detected → Line detected → Dial up → send/receive)
        if (self.mail_view == "connect" and self._mail_connect_steps and
                self.mail_connect_terminal_line_index < len(self._mail_connect_steps)):
            self.mail_connect_terminal_timer -= dt
            if self.mail_connect_terminal_timer <= 0:
                line, delay, action = self._mail_connect_steps[self.mail_connect_terminal_line_index]
                if action == "play_dialup":
                    self._play_modem_dial_sound()
                    self.mail_connect_dialup_started = True
                elif action == "do_send":
                    outbox = self.get_mail_outbox()
                    self._mail_sent_im_in_to_rain = any(
                        (m.get("recipient", "") or "").strip().lower() == "rain@ciphernet.net"
                        and "i'm in" in ((m.get("subject", "") or "").lower())
                        for m in outbox
                    )
                    for msg in outbox:
                        self.send_mail(msg.get("recipient", ""), msg.get("subject", ""), msg.get("body", ""))
                    self.save_mail_outbox([])
                elif action == "do_receive":
                    inbox_before = len(self.mail_local_inbox)
                    if self._mail_sent_im_in_to_rain:
                        username, _ = self.get_user_credentials()
                        rain_email = {
                            "id": f"rain_{int(time.time())}",
                            "sender": "rain@ciphernet.net",
                            "recipient": self.mail_settings.get("mail_from", "user@bradsonic.net"),
                            "subject": RAIN_REPLY_SUBJECT,
                            "body": _get_rain_reply_body(username),
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "read": False,
                        }
                        self.mail_local_inbox.insert(0, rain_email)
                        self.save_inbox_emails(self.mail_local_inbox)
                        self.play_mail_sound()
                    new_count = len(self.mail_local_inbox) - inbox_before
                    line = f"New mail found: {new_count} message(s)." if new_count > 0 else "No new mail."
                elif action == "complete":
                    self.mail_server_connected = True
                    self.mail_connect_terminal_complete = True
                if line and line != "PLACEHOLDER_RECEIVE":
                    self.mail_connect_terminal_lines.append(line)
                self.mail_connect_terminal_line_index += 1
                if self.mail_connect_terminal_line_index < len(self._mail_connect_steps):
                    self.mail_connect_terminal_timer = delay
                else:
                    self.mail_connect_terminal_timer = 0.0

        # Update cursor blink timer for notes modal
        if "notes" in self.active_modals and self.notes_modal_edit_mode:
            self.notes_modal_cursor_blink_timer += dt
            if self.notes_modal_cursor_blink_timer > 1.0:
                self.notes_modal_cursor_blink_timer = 0.0
        
        # Update terminal cursor blink timer
        if self.terminal_active:
            if self.terminal_mode == "command":
                self.terminal_cursor_blink_timer += dt
                blink_interval = 0.5  # Blink every 0.5 seconds
                if self.terminal_cursor_blink_timer >= blink_interval:
                    self.terminal_cursor_blink_timer -= blink_interval
                    self.terminal_cursor_visible = not self.terminal_cursor_visible
            else:
                # Don't blink cursor in menu/message modes
                self.terminal_cursor_visible = False
        
        # Stop video if modal is closed (but keep recording flag)
        # However, if recording is active, allow video to continue playing even if modal is closed
        # This ensures the Datasette video plays fully during ghost user sequence
        if "tape" not in self.active_modals and self.tape_modal_video_playing:
            is_recording, _ = self.get_recording_state()
            if not is_recording:
                # Only stop video if not recording (allows video to play fully during ghost user sequence)
                self._stop_tape_video()
        
        # Update terminal message timer for delayed messages
        if "tape" in self.active_modals and self.tape_modal_video_playing:
            self.tape_modal_message_timer += dt
            # Show "YOU MAY CLOSE THE WINDOW" after 3 seconds (a couple of beats)
            if self.tape_modal_message_timer >= 3.0 and len(self.tape_modal_terminal_lines) == 2:
                self.tape_modal_terminal_lines.append("YOU MAY CLOSE THE WINDOW")
                self.tape_modal_terminal_text = "\n".join(self.tape_modal_terminal_lines)
        
        # Update modem modal cursor blink timer
        if "modem" in self.active_modals and not self.modem_modal_connection_started:
            self.modem_modal_cursor_blink_timer += dt
            if self.modem_modal_key_flash_timer > 0.0:
                self.modem_modal_key_flash_timer = max(0.0, self.modem_modal_key_flash_timer - dt)
                if self.modem_modal_key_flash_timer <= 0.0:
                    self.modem_modal_key_flash_label = None
        else:
            # Avoid keeping a stale highlight around when the modem isn't actively taking input
            if self.modem_modal_key_flash_label is not None or self.modem_modal_key_flash_timer != 0.0:
                self.modem_modal_key_flash_label = None
                self.modem_modal_key_flash_timer = 0.0
        
        # Update modem modal connection messages and FX
        if "modem" in self.active_modals and self.modem_modal_connection_started and self.modem_modal_connection_messages:
            self.modem_modal_message_timer += dt
            
            # Progress through messages
            if self.modem_modal_message_index < len(self.modem_modal_connection_messages):
                # Get delay for current message (default to 2.1 if delays list not available)
                if hasattr(self, 'modem_modal_message_delays') and self.modem_modal_message_index < len(self.modem_modal_message_delays):
                    message_delay = self.modem_modal_message_delays[self.modem_modal_message_index]
                else:
                    message_delay = 2.1  # Default delay
                
                if self.modem_modal_message_timer >= message_delay:
                    self.modem_modal_message_index += 1
                    self.modem_modal_message_timer = 0.0
                    if self.modem_modal_message_index >= len(self.modem_modal_connection_messages):
                        # Connection successful - route based on target
                        target = self.modem_modal_current_target
                        if target == "paper_crane":
                            self.modem_modal_external_bbs = "paper_crane"
                            self.modem_modal_should_exit_os = True
                        elif target == "echo_chamber":
                            self.modem_modal_external_bbs = "echo_chamber"
                            self.modem_modal_should_exit_os = True
                        elif target == "never_again":
                            self.modem_modal_external_bbs = "never_again"
                            self.modem_modal_should_exit_os = True
                        else:
                            self.modem_modal_should_reset_bbs = True
                            self.modem_modal_should_exit_os = True
                            if self.reset_bbs_callback:
                                self.reset_bbs_callback()
            if len(self.modem_modal_connection_messages) >= 2 and not self.network_connected:
                if self.modem_modal_message_index >= len(self.modem_modal_connection_messages) - 2:
                    self.network_connected = True
                    OSMode.persisted_network_connected = True
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
        # Mail icon only visible in US Mainland (os_locale == 1); hidden in Europe and Pacifica
        # dotSONIC icon only visible in Europe and US Mainland; hidden in Pacifica
        for icon in self.icons:
            if icon["name"] == "mail-icon.png" and self.os_locale != 1:
                continue
            if icon["name"] == "sonic-icon.png" and self.os_locale == 3:
                continue
            # Use S version if selected, otherwise normal version
            icon_to_draw = icon["s_image"] if icon["selected"] else icon["image"]
            self.screen.blit(icon_to_draw, (icon["x"], icon["y"]))
            # Label under icon (same font/colour/size/gap as file system; center-aligned)
            self._draw_label_under_icon(icon["x"], icon["y"], icon["width"], icon["height"], icon.get("label", ""))
        
        # Draw clock (on same layer as icons, before modals)
        self._draw_clock()
        
        # Draw LAPC-1 Audio Output Stream visualizer (on same layer as health monitor)
        self._draw_lapc1_audio_stream_visualizer()
        
        # Draw all active modals in z-order (bottom -> top)
        for modal_name in self.active_modals:
            if modal_name == "tape":
                self._draw_tape_modal()
            elif modal_name == "modem":
                self._draw_modem_modal()
            elif modal_name == "notes":
                self._draw_notes_modal()
            elif modal_name == "games":
                self._draw_games_modal()
            elif modal_name == "hard_drive":
                self._draw_hard_drive_modal()
            elif modal_name == "system_folder":
                self._draw_system_folder_modal()
            elif modal_name == "file_system_browser":
                self._draw_file_system_browser_modal()
            elif modal_name == "mail":
                self._draw_mail_modal()
            elif modal_name == "terminal":
                self._draw_terminal()
            elif modal_name == "dot_sonic" and self.dot_sonic_app and self.dot_sonic_app.active:
                self.dot_sonic_app.draw()
        
        # Draw terminal file windows (multiple .brad file viewers)
        for win in self.terminal_file_windows:
            self._draw_terminal_file_window(win)

        if self.chess_game and self.chess_game.active:
            self.chess_game.draw()
        if self.solitaire_game and self.solitaire_game.active:
            self.solitaire_game.draw()
        if self.snooker_game and self.snooker_game.active:
            self.snooker_game.update(0.016)  # Update with ~60fps delta
            self.snooker_game.draw()
        if self.mahjong_game and self.mahjong_game.active:
            self.mahjong_game.update(0.016)
            self.mahjong_game.draw()
        if self.civitas_game and self.civitas_game.active:
            self.civitas_game.draw()
        if self.pirate_radio_app and self.pirate_radio_app.active:
            self.pirate_radio_app.draw()
    
    def draw_tape_video(self):
        """Draw the Datasette_Load.mp4 video (should be called last, after scanlines and overlay)."""
        if self.tape_modal_video_playing and self.tape_modal_video_frame:
            # Render from baseline coordinates (1363, 44)
            video_x = int(self.datasette_baseline_x * self.scale)
            video_y = int(self.datasette_baseline_y * self.scale)
            
            # Move video 50px to the right (scaled)
            video_x += int(50 * self.scale)
            
            # Draw with fade alpha already applied in the surface
            self.screen.blit(self.tape_modal_video_frame, (video_x, video_y))
    
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
        
        # Note: Video drawing moved to draw_tape_video() method to be called after scanlines/overlay

    def _get_harddisk_usage_mb(self) -> Tuple[float, float]:
        """Calculate hard disk used space. .sonic = 1MB, .brad = 0.05MB. Total 50MB.
        .sonic = virtual downloads (Fugamatchi) + physical .mp3/.wav in FILE-SYSTEM.
        Returns (used_mb, total_mb)."""
        TOTAL_MB = 50
        sonic_count = len(self.get_downloaded_fugamatchi_tracks())
        brad_count = 0
        base_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "FILE-SYSTEM")
        if os.path.isdir(base_path):
            for _root, _dirs, files in os.walk(base_path):
                for f in files:
                    lower = f.lower()
                    if lower.endswith(".txt"):
                        brad_count += 1
                    elif lower.endswith((".mp3", ".wav")):
                        sonic_count += 1
        used_mb = sonic_count * 1.0 + brad_count * 0.05  # 1MB per sonic, 0.05MB per brad
        return (used_mb, TOTAL_MB)

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
        
        # Format clock as hh:mm:ss mm-dd-1989
        now = datetime.now()
        clock_text = now.strftime("%H:%M:%S %m-%d-1989")
        
        # Check LAPC-1 Soundcard status (check for AUDIO_ON token which means all 7 nodes complete)
        lapc1_activated = self.has_token("AUDIO_ON")
        lapc1_status = "ACTIVE" if lapc1_activated else "INACTIVE"
        
        # Check if tape is recording (from user profile)
        is_recording, recording_start_time = self.get_recording_state()
        if is_recording:
            datasette_status = "RECORDING"
            datasette_status_color = COLOR_CORAL
        elif recording_start_time is None or recording_start_time == 0:
            # Never recorded - show INACTIVE
            datasette_status = "INACTIVE"
            datasette_status_color = COLOR_GREY
        else:
            # Has recorded before but not currently - show DETECTED
            datasette_status = "DETECTED"
            datasette_status_color = COLOR_GREEN
        
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
        
        # HardDisk: label in cyan, remaining in red, total (50mb) in green
        # .sonic = 1MB, .brad = 0.05MB; total 50MB. Always whole numbers.
        used_mb, total_mb = self._get_harddisk_usage_mb()
        remaining_mb = max(0, total_mb - used_mb)
        harddisk_used = f"{round(remaining_mb):.0f}mb"
        harddisk_free = f"/{round(total_mb):.0f}mb"
        harddisk_label = "  HardDisk: "
        harddisk_label_surface = status_font.render(harddisk_label, True, COLOR_CYAN)
        harddisk_used_surface = status_font.render(harddisk_used, True, COLOR_RED)
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
        
        # Locale: saved region (PACIFICA / US MAINLAND / EUROPE)
        locale_label = "  Locale: "
        locale_value = "PACIFICA" if self.os_locale == 3 else "US MAINLAND" if self.os_locale == 1 else "EUROPE"
        locale_label_surface = status_font.render(locale_label, True, COLOR_CYAN)
        locale_value_surface = status_font.render(locale_value, True, COLOR_GREEN)
        
        # Calculate max width (in order: System, HardDisk, LAPC-1, Datasette, Network, Locale)
        max_width = max(
            title_surface.get_width(),
            status_label_surface.get_width(),
            system_label_surface.get_width() + system_value_surface.get_width(),
            harddisk_label_surface.get_width() + harddisk_used_surface.get_width() + harddisk_free_surface.get_width(),
            lapc1_label_surface.get_width() + lapc1_status_surface.get_width(),
            datasette_label_surface.get_width() + datasette_status_surface.get_width(),
            network_label_surface.get_width() + network_value_surface.get_width(),
            locale_label_surface.get_width() + locale_value_surface.get_width()
        )
        
        # Calculate heights
        line_height = status_font.get_height() + int(2 * self.scale)
        title_bar_height = int(22 * self.scale)
        time_bar_height = int(20 * self.scale)
        box_padding = int(12 * self.scale)
        
        # Content height (status lines in order: System, HardDisk, LAPC-1, Datasette, Network, Locale)
        content_height = (
            status_label_surface.get_height() + int(4 * self.scale) +  # Status label + spacing
            line_height +  # System
            line_height +  # HardDisk
            line_height +  # LAPC-1
            line_height +  # Datasette
            line_height +  # Network
            line_height +  # Locale
            int(20 * self.scale) +  # Padding under Locale status (20px)
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
        text_y += line_height
        
        # Locale (label cyan, value green) - Sixth
        self.screen.blit(locale_label_surface, (text_x, text_y))
        locale_value_x = text_x + locale_label_surface.get_width()
        self.screen.blit(locale_value_surface, (locale_value_x, text_y))
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
    
    def _draw_lapc1_audio_stream_visualizer(self):
        """Draw the LAPC-1 Audio Output Stream visualizer box with pixel rain effect."""
        if self.bbs_x is None or self.bbs_y is None or self.bbs_width is None:
            return
        
        # Check if RadioMusic is playing (Node7.wav from CRACKER IDE)
        is_radio_music_playing = self.get_radio_music()
        
        if not is_radio_music_playing:
            # Clear pixels and helices when RadioMusic stops
            self.audio_stream_pixels = []
            self.audio_stream_helices = []
            return
        
        # Create font for visualizer using system font (scaled)
        try:
            title_font_size = max(int(12 * self.scale), 10)
            title_font = None
            system_fonts = ["Segoe UI", "Arial", "Helvetica", None]
            for font_name in system_fonts:
                try:
                    if title_font is None:
                        title_font = pygame.font.SysFont(font_name, title_font_size)
                    if title_font:
                        break
                except Exception:
                    continue
            if title_font is None:
                title_font = pygame.font.SysFont(None, title_font_size)
        except Exception:
            return
        
        # Title text
        title_text = "LAPC-1 AUDIO OUTPUT STREAM"
        title_surface = title_font.render(title_text, True, COLOR_WHITE)
        
        # Get health monitor dimensions and position by replicating its calculation
        # This ensures we match exactly
        box_padding = int(12 * self.scale)
        title_bar_height = int(22 * self.scale)
        time_bar_height = int(20 * self.scale)
        
        # Replicate health monitor calculations exactly (from _draw_clock method)
        # Create status font to match health monitor
        status_font_size = max(int(11 * self.scale), 9)
        status_font = None
        system_fonts = ["Segoe UI", "Arial", "Helvetica", None]
        for font_name in system_fonts:
            try:
                if status_font is None:
                    status_font = pygame.font.SysFont(font_name, status_font_size)
                if status_font:
                    break
            except Exception:
                continue
        if status_font is None:
            status_font = pygame.font.SysFont(None, status_font_size)
        
        # Replicate health monitor width calculation
        status_label = "STATUS:"
        status_label_surface = status_font.render(status_label, True, COLOR_WHITE)
        system_label = "  System: "
        system_label_surface = status_font.render(system_label, True, COLOR_CYAN)
        system_value_surface = status_font.render("OPERATIONAL", True, COLOR_GREEN)
        harddisk_label = "  HardDisk: "
        harddisk_label_surface = status_font.render(harddisk_label, True, COLOR_CYAN)
        used_mb, total_mb = self._get_harddisk_usage_mb()
        remaining_mb = max(0, total_mb - used_mb)
        harddisk_used_surface = status_font.render(f"{round(remaining_mb):.0f}mb", True, COLOR_RED)
        harddisk_free_surface = status_font.render(f"/{round(total_mb):.0f}mb", True, COLOR_GREEN)
        lapc1_label = "  LAPC-1 Soundcard: "
        lapc1_label_surface = status_font.render(lapc1_label, True, COLOR_CYAN)
        lapc1_status_surface = status_font.render("ACTIVE", True, COLOR_GREEN)
        datasette_label = "  Datasette: "
        datasette_label_surface = status_font.render(datasette_label, True, COLOR_CYAN)
        datasette_status_surface = status_font.render("DETECTED", True, COLOR_GREEN)
        network_label = "  Network: "
        network_label_surface = status_font.render(network_label, True, COLOR_CYAN)
        network_value_surface = status_font.render("DISCONNECTED", True, COLOR_GREY)
        locale_label = "  Locale: "
        locale_label_surface = status_font.render(locale_label, True, COLOR_CYAN)
        locale_value_surface = status_font.render("PACIFICA", True, COLOR_GREEN)
        health_title_text = "BRADSONIC 69000 Health Monitor"
        health_title_surface = title_font.render(health_title_text, True, COLOR_WHITE)
        
        # Calculate max width (same as health monitor, including Locale)
        health_max_width = max(
            health_title_surface.get_width(),
            status_label_surface.get_width(),
            system_label_surface.get_width() + system_value_surface.get_width(),
            harddisk_label_surface.get_width() + harddisk_used_surface.get_width() + harddisk_free_surface.get_width(),
            lapc1_label_surface.get_width() + lapc1_status_surface.get_width(),
            datasette_label_surface.get_width() + datasette_status_surface.get_width(),
            network_label_surface.get_width() + network_value_surface.get_width(),
            locale_label_surface.get_width() + locale_value_surface.get_width()
        )
        health_monitor_box_width = health_max_width + 2 * box_padding
        
        # Calculate health monitor position (same as _draw_clock)
        health_monitor_padding = int(20 * self.scale)
        health_monitor_offset_right = int(89 * self.scale)  # Move 89px to the right
        health_monitor_box_x = self.bbs_x + self.bbs_width - health_monitor_box_width - health_monitor_padding + health_monitor_offset_right
        health_monitor_box_y = self.bbs_y + int(10 * self.scale)
        
        # Calculate health monitor height (including Locale line)
        line_height = status_font.get_height() + int(2 * self.scale)
        health_monitor_content_height = (
            status_label_surface.get_height() + int(4 * self.scale) +  # Status label + spacing
            line_height +  # System
            line_height +  # HardDisk
            line_height +  # LAPC-1
            line_height +  # Datasette
            line_height +  # Network
            line_height +  # Locale
            int(20 * self.scale) +  # Padding under Locale status
            int(4 * self.scale)  # Extra spacing before time bar
        )
        health_monitor_height = title_bar_height + health_monitor_content_height + time_bar_height
        
        # Position audio stream box directly under health monitor, same width
        box_width = health_monitor_box_width  # Exact same width as health monitor
        spacing_between = int(2 * self.scale)  # Small gap between health monitor and audio stream
        box_x = health_monitor_box_x  # Same X position as health monitor
        box_y = health_monitor_box_y + health_monitor_height + spacing_between  # Directly under health monitor
        
        # Calculate height to extend to bottom of desktop environment
        desktop_bottom = self.desktop_y + self.desktop_size[1]
        box_height = desktop_bottom - box_y - int(10 * self.scale)  # Leave 10px margin from bottom
        
        # Content area height (for pixel rain) is box_height minus title bar
        content_height = box_height - title_bar_height
        
        # Draw box (on same layer as health monitor)
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
        
        # Content area for pixel rain
        content_rect = pygame.Rect(
            box_x + box_padding,
            box_y + title_bar_height + int(4 * self.scale),
            box_width - 2 * box_padding,
            content_height - int(8 * self.scale)
        )
        
        # Update pixel rain (spawn new pixels and move existing ones)
        now = pygame.time.get_ticks()
        time_since_last_update = now - self.audio_stream_last_update
        
        # Spawn new pixels based on audio activity (faster when audio is active)
        if time_since_last_update >= self.audio_stream_pixel_spawn_rate:
            # Spawn 1-3 pixels at random positions across the width
            num_pixels = random.randint(1, 3)
            for _ in range(num_pixels):
                pixel = {
                    "x": content_rect.x + random.randint(0, content_rect.width - int(2 * self.scale)),
                    "y": content_rect.y - int(2 * self.scale),  # Start above the box
                    "color": random.choice(self.audio_stream_pixel_colors),
                    "speed": random.uniform(1.5, 3.0) * self.scale,  # Pixels per frame
                    "twitch": random.uniform(-0.5, 0.5) * self.scale,  # Horizontal twitch
                    "size": random.randint(int(1 * self.scale), int(3 * self.scale))
                }
                self.audio_stream_pixels.append(pixel)
            self.audio_stream_last_update = now
        
        # Update and draw existing pixels
        pixels_to_remove = []
        for i, pixel in enumerate(self.audio_stream_pixels):
            # Move pixel down (speed can vary slightly for more dynamic effect)
            pixel["y"] += pixel["speed"] + random.uniform(-0.1, 0.1) * self.scale
            
            # Apply twitching (horizontal movement) - more dynamic variation
            twitch_amount = pixel["twitch"] * (0.5 + 0.5 * random.random())  # Vary twitch strength
            pixel["x"] += twitch_amount + random.uniform(-0.4, 0.4) * self.scale
            
            # Keep within bounds horizontally
            if pixel["x"] < content_rect.x:
                pixel["x"] = content_rect.x
                pixel["twitch"] *= -0.5  # Bounce back with reduced force
            elif pixel["x"] > content_rect.right - pixel["size"]:
                pixel["x"] = content_rect.right - pixel["size"]
                pixel["twitch"] *= -0.5  # Bounce back with reduced force
            
            # Remove pixels that have fallen below the content area
            if pixel["y"] > content_rect.bottom:
                pixels_to_remove.append(i)
                continue
            
            # Draw pixel with slight size variation for flicker effect
            pixel_size = int(pixel["size"] * (0.9 + 0.2 * random.random()))
            if pixel_size > 0:
                pixel_rect = pygame.Rect(int(pixel["x"]), int(pixel["y"]), pixel_size, pixel_size)
                pygame.draw.rect(self.screen, pixel["color"], pixel_rect)
        
        # Remove pixels that have fallen out of view (in reverse order to preserve indices)
        for i in reversed(pixels_to_remove):
            self.audio_stream_pixels.pop(i)
        
        # Spawn helix patterns occasionally
        time_since_helix_spawn = now - self.audio_stream_helix_last_spawn
        if time_since_helix_spawn >= self.audio_stream_helix_spawn_interval:
            # Spawn a new helix pattern
            helix_center_x = content_rect.x + random.randint(int(content_rect.width * 0.2), int(content_rect.width * 0.8))
            helix = {
                "center_x": helix_center_x,
                "y": content_rect.y - int(20 * self.scale),  # Start above the box
                "angle": 0.0,  # Current angle in radians for helix rotation
                "radius": random.uniform(10, 30) * self.scale,  # Helix radius
                "speed": random.uniform(2.0, 3.5) * self.scale,  # Vertical speed
                "rotation_speed": random.uniform(0.08, 0.15),  # Angular speed (radians per frame)
                "particles": [],  # List of particle positions in the helix
                "color": random.choice(self.audio_stream_pixel_colors),
                "particle_count": random.randint(8, 15)  # Number of particles in helix
            }
            # Initialize particles in helix pattern
            for i in range(helix["particle_count"]):
                particle_angle = (i / helix["particle_count"]) * 2 * math.pi  # Distribute around circle
                helix["particles"].append({
                    "local_angle": particle_angle,  # Angle relative to helix center
                    "size": random.randint(int(1 * self.scale), int(3 * self.scale))
                })
            self.audio_stream_helices.append(helix)
            self.audio_stream_helix_last_spawn = now
        
        # Update and draw helix patterns
        helices_to_remove = []
        for i, helix in enumerate(self.audio_stream_helices):
            # Update helix position and rotation
            helix["y"] += helix["speed"]
            helix["angle"] += helix["rotation_speed"]
            
            # Remove helix if it's gone below the content area
            if helix["y"] > content_rect.bottom + helix["radius"] * 2:
                helices_to_remove.append(i)
                continue
            
            # Draw helix particles
            for particle in helix["particles"]:
                # Calculate particle position in helix
                # x = center_x + radius * cos(angle + local_angle)
                # y = y + radius * sin(angle + local_angle)
                particle_angle = helix["angle"] + particle["local_angle"]
                particle_x = helix["center_x"] + helix["radius"] * math.cos(particle_angle)
                particle_y = helix["y"] + helix["radius"] * math.sin(particle_angle)
                
                # Check if particle is within content bounds
                if (content_rect.x <= particle_x <= content_rect.right and
                    content_rect.y <= particle_y <= content_rect.bottom):
                    # Draw particle with slight size variation
                    particle_size = int(particle["size"] * (0.9 + 0.2 * random.random()))
                    if particle_size > 0:
                        particle_rect = pygame.Rect(int(particle_x), int(particle_y), particle_size, particle_size)
                        pygame.draw.rect(self.screen, helix["color"], particle_rect)
        
        # Remove helices that have fallen out of view (in reverse order to preserve indices)
        for i in reversed(helices_to_remove):
            self.audio_stream_helices.pop(i)
    
    def draw_scanline(self):
        """Draw the desktop scanline overlay."""
        if self.desktop_scanline_image:
            self.screen.blit(self.desktop_scanline_image, (self.desktop_x, self.desktop_y))
    
    def _draw_modem_modal(self):
        """Draw the modem icon modal with telephone dial."""
        modal_w, modal_h = self._get_modal_size("modem")
        
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
        
        # Draw terminal window (below title bar) - increased size to accommodate text
        gap = int(20 * self.scale)
        terminal_x = modal_x + gap
        terminal_y = modal_y + self.modal_title_bar_height + gap
        terminal_w = modal_w - 2 * gap
        terminal_h = int(200 * self.scale)  # Increased from 120 to 200 for more text space
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
            elif not self.modem_modal_connection_started:
                # Show dialed sequence with cursor (even if empty)
                lines_to_render = [
                    "READY FOR INPUT...",
                    "Dialed: ",  # Will be drawn with cursor in special handling
                    "Press CONNECT to connect."
                ]
                if self.modem_modal_error_message:
                    lines_to_render.append(self.modem_modal_error_message)
            else:
                lines_to_render = [
                    "BRADSONIC NETLINK 69000",
                    "RetroSecure Dialer v2.1",
                    "Awaiting dial sequence..."
                ]
            
            for i, line in enumerate(lines_to_render):
                if not line:
                    continue
                color = self.modem_terminal_palette[i % len(self.modem_terminal_palette)]
                
                # Special handling for dialed sequence line to show cursor
                if i == 1 and (line == "Dialed: " or line.startswith("Dialed:")) and not self.modem_modal_connection_started:
                    # Draw "Dialed: " prefix
                    prefix = "Dialed: "
                    prefix_surface = terminal_font.render(prefix, True, color)
                    self.screen.blit(prefix_surface, (text_x, text_y))
                    prefix_width = prefix_surface.get_width()
                    
                    # Draw dialed sequence with cursor
                    sequence = self.modem_modal_dialed_sequence
                    cursor_pos = self.modem_modal_cursor_position
                    
                    # Ensure cursor position is valid
                    cursor_pos = max(0, min(cursor_pos, len(sequence)))
                    
                    # Draw text before cursor
                    if cursor_pos > 0:
                        before_text = sequence[:cursor_pos]
                        before_surface = terminal_font.render(before_text, True, color)
                        self.screen.blit(before_surface, (text_x + prefix_width, text_y))
                        cursor_x = text_x + prefix_width + before_surface.get_width()
                    else:
                        cursor_x = text_x + prefix_width
                    
                    # Draw blinking cursor (blinks every 1.0 second, visible for 0.5 seconds)
                    cursor_visible = (self.modem_modal_cursor_blink_timer % 1.0) < 0.5
                    if cursor_visible:
                        # Use font height to match the text size
                        cursor_height = terminal_font.get_height()
                        cursor_rect = pygame.Rect(cursor_x, text_y, int(2 * self.scale), cursor_height)
                        pygame.draw.rect(self.screen, COLOR_CYAN, cursor_rect)
                    
                    # Draw text after cursor
                    if cursor_pos < len(sequence):
                        after_text = sequence[cursor_pos:]
                        after_surface = terminal_font.render(after_text, True, color)
                        self.screen.blit(after_surface, (cursor_x + int(2 * self.scale) if cursor_visible else cursor_x, text_y))
                else:
                    # Normal line rendering
                    text_surface = terminal_font.render(line, True, color)
                    self.screen.blit(text_surface, (text_x, text_y))
                
                text_y += line_height
        except Exception:
            pass
        
        if self.modem_modal_connection_started:
            self._draw_modem_packet_effect(terminal_rect)
            status_font = pygame.font.Font(None, max(int(14 * self.scale), 11))
            status_text = status_font.render("Link Negotiation...", True, COLOR_NEON_GREEN)
            # Move one character space to the right (use font width of a space character)
            char_width = status_font.size(" ")[0]
            self.screen.blit(status_text, (terminal_x + char_width, terminal_y + terminal_h - status_font.get_height() - int(6 * self.scale)))
        else:
            status_font = pygame.font.Font(None, max(int(14 * self.scale), 11))
            status_text = status_font.render("  Awaiting CONNECT command.", True, COLOR_TEAL)
            self.screen.blit(status_text, (terminal_x, terminal_y + terminal_h - status_font.get_height() - int(6 * self.scale)))
        
        # Dial/control area positions
        dial_start_y = terminal_y + terminal_h + gap
        button_size = int(42 * self.scale)
        button_spacing = int(10 * self.scale)
        dial_width = 3 * button_size + 2 * button_spacing
        dial_start_x = modal_x + (modal_w - dial_width) // 2
        
        # CONNECT and DISCONNECT buttons side by side
        action_btn_y = dial_start_y + 4 * (button_size + button_spacing) + int(5 * self.scale)
        action_btn_h = int(48 * self.scale)  # Button height (increased by 25%)
        action_btn_spacing = int(8 * self.scale)  # Space between buttons
        action_btn_w = (dial_width - action_btn_spacing) // 2  # Half width minus spacing
        
        call_btn_x = dial_start_x
        call_btn_y = action_btn_y
        call_btn_w = action_btn_w
        call_btn_h = action_btn_h
        
        disconnect_btn_x = dial_start_x + action_btn_w + action_btn_spacing
        disconnect_btn_y = action_btn_y
        disconnect_btn_rect = pygame.Rect(disconnect_btn_x, disconnect_btn_y, action_btn_w, action_btn_h)

        # Dial pad buttons (always visible)
        dial_buttons = [
            ["1", "2", "3"],
            ["4", "5", "6"],
            ["7", "8", "9"],
            ["*", "0", "#"]
        ]
        
        for row_idx, row in enumerate(dial_buttons):
            for col_idx, button_label in enumerate(row):
                btn_x = dial_start_x + col_idx * (button_size + button_spacing)
                btn_y = dial_start_y + row_idx * (button_size + button_spacing)
                btn_rect = pygame.Rect(btn_x, btn_y, button_size, button_size)
                
                # Dim buttons when connection is in progress
                if self.modem_modal_connection_started:
                    is_hovered = False
                    is_pressed = False
                    btn_color = (15, 25, 40)  # Dimmed color
                else:
                    is_hovered = self.hovered_button == ("modem", f"dial_{button_label}")
                    is_pressed = (
                        self.modem_modal_key_flash_timer > 0.0 and
                        self.modem_modal_key_flash_label == button_label
                    )
                    btn_color = (35, 65, 110) if (is_hovered or is_pressed) else (25, 35, 60)
                
                pygame.draw.rect(self.screen, btn_color, btn_rect, border_radius=8)
                border_color = COLOR_NEON_GREEN if is_pressed else COLOR_CYAN
                border_w = 3 if is_pressed else (2 if is_hovered else 1)
                pygame.draw.rect(self.screen, border_color, btn_rect, border_w, border_radius=8)
                
                try:
                    font = pygame.font.Font(None, max(int(24 * self.scale), 16))
                    text_color = COLOR_NEON_GREEN if is_pressed else COLOR_CYAN
                    text_surface = font.render(button_label, True, text_color)
                    text_rect = text_surface.get_rect(center=btn_rect.center)
                    self.screen.blit(text_surface, text_rect)
                except Exception:
                    pass
                    
        # CONNECT Button (always visible)
        call_btn_rect = pygame.Rect(call_btn_x, call_btn_y, call_btn_w, call_btn_h)
        
        # Dim button when connection is in progress
        if self.modem_modal_connection_started:
            is_hovered = False
            btn_color = (5, 20, 10)  # Dimmed color
        else:
            is_hovered = self.hovered_button == ("modem", "call")
            btn_color = (20, 60, 40) if is_hovered else (10, 35, 20)
        
        pygame.draw.rect(self.screen, btn_color, call_btn_rect, border_radius=8)
        pygame.draw.rect(self.screen, COLOR_NEON_GREEN, call_btn_rect, 2 if is_hovered else 1, border_radius=8)
        
        try:
            font = pygame.font.Font(None, max(int(16 * self.scale), 11))  # Reduced text size by 10%
            text = font.render("CONNECT", True, COLOR_NEON_GREEN)
            text_rect = text.get_rect(center=call_btn_rect.center)
            self.screen.blit(text, text_rect)
        except Exception:
            pass

        # DISCONNECT button
        is_disconnect_hovered = self.hovered_button == ("modem", "disconnect")
        btn_disconnect_color = (60, 20, 20) if is_disconnect_hovered else (35, 15, 15)
        pygame.draw.rect(self.screen, btn_disconnect_color, disconnect_btn_rect, border_radius=8)
        pygame.draw.rect(self.screen, COLOR_RED, disconnect_btn_rect, 2 if is_disconnect_hovered else 1, border_radius=8)

        try:
            font = pygame.font.Font(None, max(int(16 * self.scale), 11))  # Match CONNECT font size
            text = font.render("HANG-UP", True, COLOR_RED)
            text_rect = text.get_rect(center=disconnect_btn_rect.center)
            self.screen.blit(text, text_rect)
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
        # Only update content rect if it changed (to avoid constant re-arrangement)
        content_changed = (self.games_modal_content_rect is None or 
                          self.games_modal_content_rect.width != inner_rect.width or
                          self.games_modal_content_rect.height != inner_rect.height)
        if content_changed:
            self.games_modal_content_rect = inner_rect
            # Always check and fix overlapping icons when content rect is first set or size changes
            # This ensures icons are properly spaced even if initial positioning had issues
            self._fix_overlapping_games_icons()

        for icon in self.games_modal_icons:
            icon["rel_x"] = max(0, min(icon["rel_x"], max(0, inner_rect.width - icon["width"])))
            icon["rel_y"] = max(0, min(icon["rel_y"], max(0, inner_rect.height - icon["height"])))
            draw_x = inner_rect.x + icon["rel_x"]
            draw_y = inner_rect.y + icon["rel_y"]
            image = icon["s_image"] if icon["selected"] else icon["image"]
            self.screen.blit(image, (draw_x, draw_y))
            icon["rect"] = pygame.Rect(draw_x, draw_y, icon["width"], icon["height"])
            # Label under icon (same font/colour/size/gap as file system; center-aligned; uppercase for consistency)
            label_text = (icon.get("label") or "").upper()
            self._draw_label_under_icon(draw_x, draw_y, icon["width"], icon["height"], label_text)

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
            "format_buttons": []
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
        tab_height = int(38 * self.scale)  # Taller tabs (was 30)
        tab_area_y = modal_y + self.modal_title_bar_height + gap
        max_tabs = min(10, len(notes) + 1)
        tab_width = (modal_w - 2 * gap) // max_tabs if max_tabs > 0 else 0
        tab_start_x = modal_x + gap

        # Cache tab font by scale to avoid recreating every frame (FPS fix)
        if getattr(self, "_notes_tab_font_scale", None) != self.scale:
            try:
                self._notes_tab_font = pygame.font.SysFont("Segoe Script", max(int(14 * self.scale), 10))
            except Exception:
                self._notes_tab_font = pygame.font.Font(None, max(int(14 * self.scale), 10))
            self._notes_tab_font_scale = self.scale
        tab_font = self._notes_tab_font

        for i in range(max_tabs):
            tab_x = tab_start_x + i * tab_width
            tab_rect = pygame.Rect(tab_x, tab_area_y, tab_width - gap, tab_height)
            is_selected = i == self.notes_modal_current_tab

            tab_color = COLOR_BG_TITLE if is_selected else COLOR_BG_DARK
            pygame.draw.rect(self.screen, tab_color, tab_rect)
            pygame.draw.rect(self.screen, COLOR_CYAN, tab_rect, 2 if is_selected else 1)
            pygame.draw.rect(self.screen, COLOR_CYAN, tab_rect, 1)

            label = "+ New" if i >= len(notes) else (notes[i].get("title", "Untitled") or "Untitled")[:NOTESTAB_TITLE_MAX_LEN]
            max_label_w = max(1, tab_rect.width - int(8 * self.scale))
            # Single line only: truncate with ellipsis if too wide (no 2nd row ever)
            if tab_font.size(label)[0] > max_label_w:
                while label and tab_font.size(label + "...")[0] > max_label_w:
                    label = label[:-1]
                label = (label or "") + "..."
            line_height = tab_font.get_height()
            text_y = tab_rect.y + (tab_rect.height - line_height) // 2
            text_surface = tab_font.render(label, True, COLOR_CYAN)
            text_x = tab_rect.x + int(4 * self.scale)
            self.screen.blit(text_surface, (text_x, text_y))

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
        
    # -------------------------------------------------------------------------
    # BRADSONIC-MAIL Client
    # -------------------------------------------------------------------------

    def _draw_mail_modal(self):
        """Draw the BRADSONIC-MAIL email client modal."""
        modal_w, modal_h = self._get_modal_size("mail")
        modal_w, modal_h = self._clamp_modal_to_desktop(modal_w, modal_h)
        modal_x, modal_y = self.modal_positions.get("mail", self._get_modal_position(modal_w, modal_h, "mail"))
        if "mail" not in self.modal_positions:
            self.modal_positions["mail"] = (modal_x, modal_y)

        gap = int(10 * self.scale)
        font_size = max(int(16 * self.scale), 12)

        # Cache fonts - content fonts are 2x the original for readability
        if getattr(self, "_mail_font_scale", None) != self.scale:
            self._mail_title_font = pygame.font.Font(None, max(int(20 * self.scale), 14))
            self._mail_tagline_font = pygame.font.Font(None, max(int(12 * self.scale), 9))
            self._mail_menu_font = pygame.font.Font(None, font_size)
            # Content fonts: 200% of the original sizes for inbox/compose/reading
            self._mail_body_font = pygame.font.Font(None, max(int(26 * self.scale), 18))
            self._mail_small_font = pygame.font.Font(None, max(int(22 * self.scale), 16))
            # Settings page uses a smaller font to fit the dense controls
            self._mail_settings_font = pygame.font.Font(None, max(int(15 * self.scale), 11))
            self._mail_font_scale = self.scale

        # -- Window frame --
        modal_rect = pygame.Rect(modal_x, modal_y, modal_w, modal_h)
        pygame.draw.rect(self.screen, COLOR_BG_DARK, modal_rect)
        pygame.draw.rect(self.screen, COLOR_CYAN, modal_rect, 2)

        # -- Title bar --
        title_bar_rect = pygame.Rect(modal_x, modal_y, modal_w, self.modal_title_bar_height)
        pygame.draw.rect(self.screen, COLOR_BG_TITLE, title_bar_rect)
        pygame.draw.rect(self.screen, COLOR_CYAN, title_bar_rect, 1)

        title_text = self._mail_title_font.render("BRADSONIC-MAIL", True, COLOR_CYAN)
        self.screen.blit(title_text, (modal_x + int(10 * self.scale), modal_y + int(5 * self.scale)))

        # Close button
        close_btn_size = int(20 * self.scale)
        close_btn_x = modal_x + modal_w - close_btn_size - int(5 * self.scale)
        close_btn_y = modal_y + int(5 * self.scale)
        close_btn_rect = pygame.Rect(close_btn_x, close_btn_y, close_btn_size, close_btn_size)
        is_hovered = self.hovered_button == ("mail", "title_close")
        close_color = COLOR_RED if is_hovered else COLOR_RED_DARK
        pygame.draw.rect(self.screen, close_color, close_btn_rect)
        pygame.draw.rect(self.screen, COLOR_CYAN, close_btn_rect, 1)
        close_font = pygame.font.Font(None, max(int(14 * self.scale), 10))
        close_text = close_font.render("X", True, COLOR_WHITE)
        close_text_rect = close_text.get_rect(center=close_btn_rect.center)
        self.screen.blit(close_text, close_text_rect)

        y_cursor = modal_y + self.modal_title_bar_height

        # -- Tagline bar --
        tagline_h = int(18 * self.scale)
        tagline_rect = pygame.Rect(modal_x, y_cursor, modal_w, tagline_h)
        pygame.draw.rect(self.screen, (15, 15, 35), tagline_rect)
        pygame.draw.line(self.screen, COLOR_CYAN, (modal_x, y_cursor + tagline_h), (modal_x + modal_w, y_cursor + tagline_h), 1)
        tagline_surf = self._mail_tagline_font.render("Interconnecting the American Mainland and beyond!", True, COLOR_AMBER)
        tagline_x = modal_x + (modal_w - tagline_surf.get_width()) // 2
        self.screen.blit(tagline_surf, (tagline_x, y_cursor + (tagline_h - tagline_surf.get_height()) // 2))
        y_cursor += tagline_h

        # -- Menu bar: COMPOSE | INBOX | OUTBOX | TRASH | SETTINGS --
        menu_h = int(28 * self.scale)
        menu_rect = pygame.Rect(modal_x, y_cursor, modal_w, menu_h)
        pygame.draw.rect(self.screen, (30, 30, 55), menu_rect)
        pygame.draw.line(self.screen, COLOR_CYAN, (modal_x, y_cursor + menu_h), (modal_x + modal_w, y_cursor + menu_h), 1)

        menu_items = ["COMPOSE", "INBOX", "OUTBOX", "TRASH", "CONNECT", "SETTINGS"]
        menu_view_map = {"COMPOSE": "compose", "INBOX": "inbox", "OUTBOX": "outbox", "TRASH": "trash", "CONNECT": "connect", "SETTINGS": "settings"}
        menu_btn_w = int(72 * self.scale)
        menu_start_x = modal_x + gap
        self._mail_menu_hitboxes = []

        for i, label in enumerate(menu_items):
            btn_x = menu_start_x + i * (menu_btn_w + int(4 * self.scale))
            btn_rect = pygame.Rect(btn_x, y_cursor + int(3 * self.scale), menu_btn_w, menu_h - int(6 * self.scale))
            is_active = self.mail_view == menu_view_map[label] or (self.mail_view == "reading" and label == "INBOX") or (self.mail_view == "connect" and label == "CONNECT")
            is_hover = self.hovered_button == ("mail", f"menu_{label}")
            # Pulse COMPOSE when viewing inbox (guide player to compose first)
            pulse_compose = label == "COMPOSE" and self.mail_view == "inbox"
            pulse_alpha = 0.5 + 0.5 * math.sin(self.mail_pulse_timer * 3.0) if pulse_compose else 0.0

            if is_active:
                pygame.draw.rect(self.screen, (60, 60, 100), btn_rect)
                pygame.draw.rect(self.screen, COLOR_CYAN, btn_rect, 2)
            elif is_hover:
                pygame.draw.rect(self.screen, (45, 45, 75), btn_rect)
                pygame.draw.rect(self.screen, COLOR_CYAN, btn_rect, 1)
            else:
                pygame.draw.rect(self.screen, COLOR_CYAN, btn_rect, 1)
            if pulse_alpha > 0:
                pulse_color = (int(0 + pulse_alpha * 0), int(200 + pulse_alpha * 55), int(255))
                pygame.draw.rect(self.screen, pulse_color, btn_rect, max(1, int(2 * pulse_alpha)))

            label_surf = self._mail_menu_font.render(label, True, COLOR_CYAN if is_active else COLOR_WHITE)
            label_rect = label_surf.get_rect(center=btn_rect.center)
            self.screen.blit(label_surf, label_rect)
            self._mail_menu_hitboxes.append((btn_rect, menu_view_map[label]))

        # CONNECT TO MAIL SERVER button - visible on OUTBOX when not in connect view (legacy); CONNECT menu opens full terminal

        y_cursor += menu_h + 1  # 1px for the border line

        # -- Content area --
        content_rect = pygame.Rect(modal_x + gap, y_cursor + gap, modal_w - 2 * gap, modal_h - (y_cursor - modal_y) - 2 * gap)
        pygame.draw.rect(self.screen, COLOR_BLACK, content_rect)
        pygame.draw.rect(self.screen, COLOR_CYAN, content_rect, 1)

        # Clip to content area
        old_clip = self.screen.get_clip()
        self.screen.set_clip(content_rect)

        if self.mail_view == "inbox":
            self._draw_mail_list(content_rect, self.mail_local_inbox, "inbox")
        elif self.mail_view == "outbox":
            self._draw_mail_list(content_rect, self.get_mail_outbox(), "outbox")
        elif self.mail_view == "trash":
            self._draw_mail_list(content_rect, self.get_mail_trash(), "trash")
        elif self.mail_view == "compose":
            self._draw_mail_compose(content_rect)
        elif self.mail_view == "reading":
            self._draw_mail_reading(content_rect)
        elif self.mail_view == "connect":
            self._draw_mail_connect(content_rect)
        elif self.mail_view == "settings":
            self._draw_mail_settings(content_rect)

        self.screen.set_clip(old_clip)

        # -- Status bar --
        if self.mail_status_message and self.mail_status_timer > 0:
            status_surf = self._mail_small_font.render(self.mail_status_message, True, COLOR_AMBER)
            self.screen.blit(status_surf, (modal_x + gap, modal_y + modal_h - int(14 * self.scale)))

    def _draw_mail_list(self, content_rect: pygame.Rect, emails: list, list_type: str):
        """Draw an email list (inbox, outbox, or trash). Outbox includes STATUS column."""
        gap = int(10 * self.scale)
        row_h = int(34 * self.scale)
        font = self._mail_body_font
        small_font = self._mail_small_font
        x = content_rect.x + int(8 * self.scale)
        y_start = content_rect.y + int(5 * self.scale)

        # Column layout: outbox has STATUS column
        if list_type == "outbox":
            col_status_w = int(100 * self.scale)
            col_date_x = content_rect.right - int(130 * self.scale) - col_status_w
            col_status_x = content_rect.right - int(130 * self.scale)
        else:
            col_date_x = content_rect.right - int(130 * self.scale)
            col_status_x = None

        # Column header
        header_y = y_start
        col_from_label = "TO" if list_type == "outbox" else "FROM"
        header_from = small_font.render(col_from_label, True, COLOR_GREY)
        header_subject = small_font.render("SUBJECT", True, COLOR_GREY)
        header_date = small_font.render("DATE", True, COLOR_GREY)

        col_from_x = x
        col_subject_x = x + int(180 * self.scale)
        col_from_w = int(172 * self.scale)   # TO/FROM column width (before subject)
        col_subject_w = int(300 * self.scale)
        if list_type == "outbox":
            col_subject_x = x + int(140 * self.scale)
            col_from_w = int(132 * self.scale)  # Narrower; STATUS column takes space
            col_subject_w = int(220 * self.scale)

        self.screen.blit(header_from, (col_from_x, header_y))
        self.screen.blit(header_subject, (col_subject_x, header_y))
        self.screen.blit(header_date, (col_date_x, header_y))
        if list_type == "outbox" and col_status_x is not None:
            header_status = small_font.render("STATUS", True, COLOR_GREY)
            self.screen.blit(header_status, (col_status_x, header_y))

        # Separator line
        sep_y = header_y + small_font.get_height() + int(2 * self.scale)
        pygame.draw.line(self.screen, COLOR_CYAN, (x, sep_y), (content_rect.right - int(5 * self.scale), sep_y), 1)

        if not emails:
            empty_text = "No messages."
            empty_surf = font.render(empty_text, True, COLOR_GREY)
            self.screen.blit(empty_surf, (x, sep_y + int(10 * self.scale)))
            self._mail_list_hitboxes = []
            return

        self._mail_list_hitboxes = []
        visible_start = sep_y + int(4 * self.scale)
        max_visible = (content_rect.bottom - visible_start) // row_h

        # Clamp scroll offset
        self.mail_scroll_offset = max(0, min(self.mail_scroll_offset, max(0, len(emails) - max_visible)))

        for i in range(self.mail_scroll_offset, min(len(emails), self.mail_scroll_offset + max_visible)):
            email = emails[i]
            row_y = visible_start + (i - self.mail_scroll_offset) * row_h
            row_rect = pygame.Rect(content_rect.x + 1, row_y, content_rect.width - 2, row_h)

            is_selected = (i == self.mail_selected_index)
            is_unread = not email.get("read", True)

            if is_selected:
                pygame.draw.rect(self.screen, (40, 60, 80), row_rect)
            elif is_unread:
                pygame.draw.rect(self.screen, (20, 25, 45), row_rect)

            text_color = COLOR_CYAN if is_unread else COLOR_WHITE
            from_field = email.get("recipient", "") if list_type == "outbox" else email.get("sender", "")
            # Truncate TO/FROM: 17 chars for inbox/trash, 14 for outbox (narrower column)
            max_from = 14 if list_type == "outbox" else 17
            if len(from_field) > max_from:
                from_text = from_field[:max_from] + "..."
            else:
                from_text = from_field

            subject_text = email.get("subject", "(no subject)")
            # Truncate SUBJECT: 28 for outbox (narrower), 35 for inbox/trash
            max_subj = 28 if list_type == "outbox" else 35
            if len(subject_text) > max_subj:
                subject_text = subject_text[:max_subj] + "..."

            date_text = email.get("timestamp", "")
            if len(date_text) > 16:
                date_text = date_text[:16]

            from_surf = font.render(from_text, True, text_color)
            subj_surf = font.render(subject_text, True, text_color)
            date_surf = small_font.render(date_text, True, COLOR_GREY)

            text_y = row_y + (row_h - font.get_height()) // 2
            from_rect = pygame.Rect(col_from_x, text_y, col_from_w, row_h)
            subj_rect = pygame.Rect(col_subject_x, text_y, col_subject_w, row_h)
            old_clip = self.screen.get_clip()
            self.screen.set_clip(from_rect)
            self.screen.blit(from_surf, (col_from_x, text_y))
            self.screen.set_clip(subj_rect)
            self.screen.blit(subj_surf, (col_subject_x, text_y))
            self.screen.set_clip(old_clip)
            self.screen.blit(date_surf, (col_date_x, text_y + int(2 * self.scale)))
            if list_type == "outbox" and col_status_x is not None:
                status_text = "CONNECTED" if self.mail_server_connected else "DISCONNECTED"
                status_surf = small_font.render(status_text, True, COLOR_AMBER if self.mail_server_connected else COLOR_GREY)
                self.screen.blit(status_surf, (col_status_x, text_y + int(2 * self.scale)))

            # Unread indicator dot
            if is_unread:
                dot_x = col_from_x - int(8 * self.scale)
                dot_y = text_y + font.get_height() // 2
                pygame.draw.circle(self.screen, COLOR_CYAN, (dot_x, dot_y), int(3 * self.scale))

            self._mail_list_hitboxes.append((row_rect, i))

        # Scroll indicators
        if self.mail_scroll_offset > 0:
            arrow_surf = small_font.render("^ more ^", True, COLOR_CYAN)
            self.screen.blit(arrow_surf, (content_rect.centerx - arrow_surf.get_width() // 2, visible_start - int(2 * self.scale)))
        if self.mail_scroll_offset + max_visible < len(emails):
            arrow_surf = small_font.render("v more v", True, COLOR_CYAN)
            self.screen.blit(arrow_surf, (content_rect.centerx - arrow_surf.get_width() // 2, content_rect.bottom - int(12 * self.scale)))

    def _draw_mail_compose(self, content_rect: pygame.Rect):
        """Draw the compose email form."""
        gap = int(10 * self.scale)
        font = self._mail_body_font
        small_font = self._mail_small_font
        x = content_rect.x + int(8 * self.scale)
        y = content_rect.y + int(8 * self.scale)
        field_w = content_rect.width - int(16 * self.scale)
        field_h = int(32 * self.scale)

        # Cursor blink
        self.mail_cursor_blink_timer += 0.05
        show_cursor = (self.mail_cursor_blink_timer % 1.0) < 0.5

        # TO: field
        label_w = int(100 * self.scale)
        to_label = font.render("TO:", True, COLOR_CYAN)
        self.screen.blit(to_label, (x, y + int(4 * self.scale)))
        to_field_x = x + label_w
        to_field_rect = pygame.Rect(to_field_x, y, field_w - label_w, field_h)
        field_bg = (30, 30, 55) if self.mail_compose_active_field == "to" else (15, 15, 30)
        pygame.draw.rect(self.screen, field_bg, to_field_rect)
        border_color = COLOR_CYAN if self.mail_compose_active_field == "to" else COLOR_GREY
        pygame.draw.rect(self.screen, border_color, to_field_rect, 1)
        text_pad = int(6 * self.scale)
        to_display = self.mail_compose_to if self.mail_compose_to else MAIL_COMPOSE_PLACEHOLDER_TO
        to_color = COLOR_WHITE if self.mail_compose_to else (60, 80, 90)  # Faint placeholder
        to_text = font.render(to_display, True, to_color)
        self.screen.blit(to_text, (to_field_x + text_pad, y + text_pad))
        if show_cursor and self.mail_compose_active_field == "to":
            cursor_x = to_field_x + text_pad + font.size(self.mail_compose_to[:self.mail_compose_cursor])[0]
            pygame.draw.line(self.screen, COLOR_WHITE, (cursor_x, y + text_pad), (cursor_x, y + field_h - text_pad), 1)
        self._mail_compose_to_rect = to_field_rect
        y += field_h + int(6 * self.scale)

        # SUBJECT: field
        subj_label = font.render("SUBJECT:", True, COLOR_CYAN)
        self.screen.blit(subj_label, (x, y + int(4 * self.scale)))
        subj_field_x = x + label_w
        subj_field_rect = pygame.Rect(subj_field_x, y, field_w - label_w, field_h)
        field_bg = (30, 30, 55) if self.mail_compose_active_field == "subject" else (15, 15, 30)
        pygame.draw.rect(self.screen, field_bg, subj_field_rect)
        border_color = COLOR_CYAN if self.mail_compose_active_field == "subject" else COLOR_GREY
        pygame.draw.rect(self.screen, border_color, subj_field_rect, 1)
        subj_display = self.mail_compose_subject if self.mail_compose_subject else MAIL_COMPOSE_PLACEHOLDER_SUBJECT
        subj_color = COLOR_WHITE if self.mail_compose_subject else (60, 80, 90)
        subj_text = font.render(subj_display, True, subj_color)
        self.screen.blit(subj_text, (subj_field_x + text_pad, y + text_pad))
        if show_cursor and self.mail_compose_active_field == "subject":
            cursor_x = subj_field_x + text_pad + font.size(self.mail_compose_subject[:self.mail_compose_cursor])[0]
            pygame.draw.line(self.screen, COLOR_WHITE, (cursor_x, y + text_pad), (cursor_x, y + field_h - text_pad), 1)
        self._mail_compose_subj_rect = subj_field_rect
        y += field_h + int(6 * self.scale)

        # BODY: text area
        body_label = font.render("BODY:", True, COLOR_CYAN)
        self.screen.blit(body_label, (x, y))
        y += font.get_height() + int(4 * self.scale)
        body_h = content_rect.bottom - y - int(36 * self.scale)
        body_rect = pygame.Rect(x, y, field_w, body_h)
        field_bg = (30, 30, 55) if self.mail_compose_active_field == "body" else (15, 15, 30)
        pygame.draw.rect(self.screen, field_bg, body_rect)
        border_color = COLOR_CYAN if self.mail_compose_active_field == "body" else COLOR_GREY
        pygame.draw.rect(self.screen, border_color, body_rect, 1)

        # Render body text with word wrapping (or faint placeholder when empty)
        body_pad = int(6 * self.scale)
        body_display = self.mail_compose_body if self.mail_compose_body else MAIL_COMPOSE_PLACEHOLDER_BODY
        body_lines = self._mail_wrap_text(body_display, font, body_rect.width - 2 * body_pad)
        line_h = font.get_height()
        for li, line in enumerate(body_lines):
            line_y = y + body_pad + li * line_h
            if line_y + line_h > body_rect.bottom:
                break
            body_line_color = COLOR_WHITE if self.mail_compose_body else (60, 80, 90)
            line_surf = font.render(line, True, body_line_color)
            self.screen.blit(line_surf, (x + body_pad, line_y))

        if show_cursor and self.mail_compose_active_field == "body":
            # Find cursor position in wrapped text
            cursor_pos = min(self.mail_compose_cursor, len(self.mail_compose_body))
            text_before = self.mail_compose_body[:cursor_pos]
            before_lines = self._mail_wrap_text(text_before, font, body_rect.width - 2 * body_pad)
            if before_lines:
                cursor_line = len(before_lines) - 1
                cursor_x_offset = font.size(before_lines[-1])[0]
            else:
                cursor_line = 0
                cursor_x_offset = 0
            cx = x + body_pad + cursor_x_offset
            cy = y + body_pad + cursor_line * line_h
            if cy + line_h <= body_rect.bottom:
                pygame.draw.line(self.screen, COLOR_WHITE, (cx, cy), (cx, cy + line_h), 1)

        self._mail_compose_body_rect = body_rect

        # SEND button (pulse when subject is "i'm in" or close)
        send_btn_w = int(100 * self.scale)
        send_btn_h = int(24 * self.scale)
        send_btn_x = content_rect.right - send_btn_w - int(8 * self.scale)
        send_btn_y = content_rect.bottom - send_btn_h - int(6 * self.scale)
        send_btn_rect = pygame.Rect(send_btn_x, send_btn_y, send_btn_w, send_btn_h)
        is_hover = self.hovered_button == ("mail", "send")
        subj_lower = self.mail_compose_subject.strip().lower().replace("'", "").replace(" ", "")
        send_ready = "imin" in subj_lower or "i'm in" in self.mail_compose_subject.strip().lower()
        send_pulse = send_ready and (0.5 + 0.5 * math.sin(self.mail_pulse_timer * 3.0)) > 0.7
        btn_color = (60, 60, 100) if is_hover else (40, 40, 70)
        pygame.draw.rect(self.screen, btn_color, send_btn_rect)
        border_w = 2 if (is_hover or send_pulse) else 1
        pygame.draw.rect(self.screen, COLOR_CYAN, send_btn_rect, border_w)
        send_label = self._mail_menu_font.render("SEND", True, COLOR_CYAN)
        send_label_rect = send_label.get_rect(center=send_btn_rect.center)
        self.screen.blit(send_label, send_label_rect)
        self._mail_send_btn_rect = send_btn_rect

        # CLEAR button
        clear_btn_x = send_btn_x - send_btn_w - int(8 * self.scale)
        clear_btn_rect = pygame.Rect(clear_btn_x, send_btn_y, send_btn_w, send_btn_h)
        is_hover_clear = self.hovered_button == ("mail", "clear")
        btn_color_clear = (60, 40, 40) if is_hover_clear else (40, 30, 30)
        pygame.draw.rect(self.screen, btn_color_clear, clear_btn_rect)
        pygame.draw.rect(self.screen, COLOR_RED, clear_btn_rect, 2 if is_hover_clear else 1)
        clear_label = self._mail_menu_font.render("CLEAR", True, COLOR_RED)
        clear_label_rect = clear_label.get_rect(center=clear_btn_rect.center)
        self.screen.blit(clear_label, clear_label_rect)
        self._mail_clear_btn_rect = clear_btn_rect

    def _draw_mail_connect(self, content_rect: pygame.Rect):
        """Draw the CONNECT view - terminal-style modem connection (1989 aesthetic)."""
        if not self.terminal_font:
            self._load_terminal_font()
        mono_font = self.terminal_font or self._mail_body_font
        x = content_rect.x + int(8 * self.scale)
        y = content_rect.y + int(8 * self.scale)

        # Terminal area (modem look - dark with cyan text)
        term_h = content_rect.height - int(60 * self.scale)
        term_rect = pygame.Rect(x, y, content_rect.width - int(16 * self.scale), term_h)
        pygame.draw.rect(self.screen, (8, 12, 24), term_rect)
        pygame.draw.rect(self.screen, COLOR_CYAN, term_rect, 1)
        # Header
        header = mono_font.render("BBS POP3 International Ciphernet Client", True, COLOR_AMBER)
        self.screen.blit(header, (term_rect.x + int(6 * self.scale), term_rect.y + int(4 * self.scale)))

        # Terminal content
        line_h = mono_font.get_height() + int(2 * self.scale)
        text_x = term_rect.x + int(6 * self.scale)
        text_y = term_rect.y + int(26 * self.scale)
        max_lines = (term_rect.height - int(30 * self.scale)) // line_h

        visible_lines = self.mail_connect_terminal_lines
        max_scroll = max(0, len(visible_lines) - max_lines)
        self.mail_connect_terminal_scroll = min(self.mail_connect_terminal_scroll, max_scroll)
        start = max(0, len(visible_lines) - max_lines - self.mail_connect_terminal_scroll)
        for i in range(start, len(visible_lines)):
            line_surf = mono_font.render(visible_lines[i], True, COLOR_CYAN)
            self.screen.blit(line_surf, (text_x, text_y + (i - start) * line_h))

        # Blinking cursor when in progress
        if not self.mail_connect_terminal_complete and (
            self.mail_connect_terminal_line_index > 0 or len(self.mail_connect_terminal_lines) > 0
        ):
            cursor_blink = (self.mail_pulse_timer * 2) % 1.0 < 0.5
            if cursor_blink:
                last_line_idx = min(len(visible_lines) - 1 - start, max_lines - 1)
                if last_line_idx >= 0:
                    cur_y = text_y + last_line_idx * line_h
                    pygame.draw.line(
                        self.screen, COLOR_CYAN,
                        (text_x + int(4 * self.scale), cur_y),
                        (text_x + int(4 * self.scale), cur_y + line_h - 2), 1
                    )

        # Button row: SEND/RX (when connected) + DIAL or CONNECTED
        btn_y = content_rect.bottom - int(36 * self.scale)
        btn_h = int(28 * self.scale)
        btn_spacing = int(8 * self.scale)
        dial_btn_w = int(120 * self.scale)
        sendrx_btn_w = int(100 * self.scale)
        dial_btn_x = content_rect.right - dial_btn_w - int(12 * self.scale)
        dial_btn_rect = pygame.Rect(dial_btn_x, btn_y, dial_btn_w, btn_h)
        self._mail_dial_btn_rect = dial_btn_rect

        # SEND/RX button - next to CONNECTED, only when connected
        if self.mail_server_connected:
            sendrx_btn_x = dial_btn_x - sendrx_btn_w - btn_spacing
            sendrx_btn_rect = pygame.Rect(sendrx_btn_x, btn_y, sendrx_btn_w, btn_h)
            self._mail_sendrx_btn_rect = sendrx_btn_rect
            is_sendrx_hover = self.hovered_button == ("mail", "sendrx")
            sendrx_color = (30, 70, 80) if is_sendrx_hover else (20, 60, 70)
            pygame.draw.rect(self.screen, sendrx_color, sendrx_btn_rect)
            pygame.draw.rect(self.screen, COLOR_CYAN, sendrx_btn_rect, 2)
            sendrx_surf = self._mail_menu_font.render("SEND/RX", True, COLOR_CYAN)
            self.screen.blit(sendrx_surf, sendrx_surf.get_rect(center=sendrx_btn_rect.center))
        else:
            self._mail_sendrx_btn_rect = None

        if self.mail_connect_terminal_complete and self.mail_server_connected:
            label = "CONNECTED"
            btn_color = (20, 80, 60)
        elif self.mail_connect_terminal_line_index > 0 and not self.mail_connect_terminal_complete:
            label = "CONNECTING..."
            btn_color = (40, 60, 80)
        else:
            label = "DIAL"
            btn_color = (20, 50, 60)

        is_hover = self.hovered_button == ("mail", "dial")
        if is_hover and not (self.mail_connect_terminal_line_index > 0 and not self.mail_connect_terminal_complete):
            btn_color = (30, 70, 80)
        pygame.draw.rect(self.screen, btn_color, dial_btn_rect)
        pygame.draw.rect(self.screen, COLOR_CYAN, dial_btn_rect, 2)
        dial_surf = self._mail_menu_font.render(label, True, COLOR_CYAN)
        self.screen.blit(dial_surf, dial_surf.get_rect(center=dial_btn_rect.center))

    def _start_mail_connect_sequence(self) -> None:
        """Start the 1989-style modem connection sequence. 20 sec offline, then dial (27s audio), then send/receive."""
        self.mail_connect_terminal_lines = []
        self.mail_connect_terminal_line_index = 0
        self.mail_connect_terminal_timer = 0.4
        self.mail_connect_terminal_complete = False
        self.mail_connect_dialup_started = False
        self._mail_sent_im_in_to_rain = False
        self.mail_connect_terminal_scroll = 0
        outbox = self.get_mail_outbox()
        outbox_count = len(outbox)
        # Only deliver Rain's reply when "I'm in" was sent TO rain@ciphernet.net
        has_im_in_to_rain = any(
            (m.get("recipient", "") or "").strip().lower() == "rain@ciphernet.net"
            and "i'm in" in ((m.get("subject", "") or "").lower())
            for m in outbox
        )
        # Phase 1: ~20 sec offline technobabble (1989 modem init)
        self._mail_connect_steps = [
            ("BRADSONIC-MAIL POP3 Client v2.1 initializing...", 1.8, None),
            ("Checking serial port COM1...", 1.3, None),
            ("Hayes-compatible modem detected: 2400 baud", 1.3, None),
            ("ATZ", 0.8, None),
            ("OK", 0.6, None),
            ("ATE0", 0.6, None),
            ("OK", 0.6, None),
            ("ATM0", 0.6, None),
            ("OK", 0.6, None),
            ("AT+FCLASS=0", 0.8, None),
            ("OK", 0.6, None),
            ("Modem ready.", 1.0, None),
            ("Checking line status...", 1.2, None),
            ("Line detected. Dial tone present.", 1.2, None),
            ("Carrier detect: READY", 1.0, None),
            ("Initializing MNP error correction...", 1.2, None),
            ("LAPM negotiation complete.", 1.0, None),
            ("Configuring UART 16550...", 1.0, None),
            ("DTE rate: 9600, DCE rate: 2400", 0.9, None),
            ("Ready to dial.", 1.0, None),
            ("", 0.5, None),
            # Phase 2: Initiating dial
            ("Initiating dial sequence...", 0.8, None),
            ("Dial up!", 0.3, "play_dialup"),
            # Phase 3: Connection technobabble (during 27s dialup.wav - spread over ~22 sec)
            ("DT 0345728891", 2.2, None),
            ("RING", 1.8, None),
            ("RING", 1.8, None),
            ("CONNECT 2400", 2.0, None),
            ("Negotiating link protocol...", 2.2, None),
            ("CCITT V.42 bis compression: ON", 1.8, None),
            ("Finalizing handshake...", 2.0, None),
            ("Link established.", 1.5, None),
            ("Connecting to pop3.ciphernet-relay.net:110...", 2.2, None),
            ("+OK BBS POP3 International Ciphernet ready", 1.8, None),
            ("USER check", 1.0, None),
            ("PASS ***", 0.8, None),
            ("+OK Authenticated", 1.0, None),
            # Phase 4: Mail transfer
            ("STAT", 0.5, None),
            ("+OK Mailbox ready", 0.6, None),
        ]
        if outbox_count > 0:
            self._mail_connect_steps.append((f"Sending mail... ({outbox_count} message(s))", 0.8, None))
            self._mail_connect_steps.append((f"Mail sent: {outbox_count} message(s).", 0.6, "do_send"))
            if has_im_in_to_rain:
                self._mail_connect_steps.append(("Waiting for reply...", 30.0, None))
        else:
            self._mail_connect_steps.append(("Outbox empty.", 0.5, None))
        self._mail_connect_steps.append(("RETR - Checking for new mail...", 0.8, None))
        self._mail_connect_steps.append(("PLACEHOLDER_RECEIVE", 0.5, "do_receive"))
        self._mail_connect_steps.append(("Connection complete.", 0.4, "complete"))

    def _mail_do_send_rx(self) -> None:
        """Quick send outbox + receive when already connected (SEND/RX button). Rain's reply only when 'I'm in' sent to Rain."""
        outbox = self.get_mail_outbox()
        outbox_count = len(outbox)
        sent_im_in_to_rain = False
        if outbox_count > 0:
            sent_im_in_to_rain = any(
                (m.get("recipient", "") or "").strip().lower() == "rain@ciphernet.net"
                and "i'm in" in ((m.get("subject", "") or "").lower())
                for m in outbox
            )
            for msg in outbox:
                self.send_mail(msg.get("recipient", ""), msg.get("subject", ""), msg.get("body", ""))
            self.save_mail_outbox([])
        inbox_before = len(self.mail_local_inbox)
        if sent_im_in_to_rain:
            username, _ = self.get_user_credentials()
            rain_email = {
                "id": f"rain_{int(time.time())}",
                "sender": "rain@ciphernet.net",
                "recipient": self.mail_settings.get("mail_from", "user@bradsonic.net"),
                "subject": RAIN_REPLY_SUBJECT,
                "body": _get_rain_reply_body(username),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "read": False,
            }
            self.mail_local_inbox.insert(0, rain_email)
            self.save_inbox_emails(self.mail_local_inbox)
            self.play_mail_sound()
        new_count = len(self.mail_local_inbox) - inbox_before
        self.mail_connect_terminal_lines.append("")
        if outbox_count > 0:
            self.mail_connect_terminal_lines.append(f"Sending mail... ({outbox_count} message(s))")
            self.mail_connect_terminal_lines.append(f"Mail sent: {outbox_count} message(s).")
        else:
            self.mail_connect_terminal_lines.append("Outbox empty.")
        self.mail_connect_terminal_lines.append("RETR - Checking for new mail...")
        self.mail_connect_terminal_lines.append(
            f"New mail found: {new_count} message(s)." if new_count > 0 else "No new mail."
        )
        self.mail_connect_terminal_lines.append("Transfer complete.")

    def _draw_mail_reading(self, content_rect: pygame.Rect):
        """Draw the email reading view."""
        if not self.mail_reading_email:
            self.mail_view = "inbox"
            return

        gap = int(10 * self.scale)
        font = self._mail_body_font
        small_font = self._mail_small_font
        x = content_rect.x + int(8 * self.scale)
        y = content_rect.y + int(8 * self.scale)
        max_w = content_rect.width - int(16 * self.scale)

        email = self.mail_reading_email

        # Header: FROM / TO / SUBJECT / DATE
        from_surf = font.render(f"FROM:  {email.get('sender', 'unknown')}", True, COLOR_CYAN)
        self.screen.blit(from_surf, (x, y))
        y += font.get_height() + int(2 * self.scale)

        to_surf = font.render(f"TO:  {email.get('recipient', 'you')}", True, COLOR_CYAN)
        self.screen.blit(to_surf, (x, y))
        y += font.get_height() + int(2 * self.scale)

        subj_surf = font.render(f"SUBJ:  {email.get('subject', '(no subject)')}", True, COLOR_WHITE)
        self.screen.blit(subj_surf, (x, y))
        y += font.get_height() + int(2 * self.scale)

        date_surf = small_font.render(f"DATE:  {email.get('timestamp', '')}", True, COLOR_GREY)
        self.screen.blit(date_surf, (x, y))
        y += small_font.get_height() + int(6 * self.scale)

        # Separator
        pygame.draw.line(self.screen, COLOR_CYAN, (x, y), (content_rect.right - int(8 * self.scale), y), 1)
        y += int(6 * self.scale)

        # Body text with word wrapping
        body = email.get("body", "")
        body_lines = self._mail_wrap_text(body, font, max_w)
        line_h = font.get_height()

        # Apply scroll offset for reading
        visible_lines = (content_rect.bottom - y - int(30 * self.scale)) // line_h
        total_lines = len(body_lines)
        self.mail_scroll_offset = max(0, min(self.mail_scroll_offset, max(0, total_lines - visible_lines)))

        for li in range(self.mail_scroll_offset, min(total_lines, self.mail_scroll_offset + visible_lines)):
            line_y = y + (li - self.mail_scroll_offset) * line_h
            if line_y + line_h > content_rect.bottom - int(30 * self.scale):
                break
            line_surf = font.render(body_lines[li], True, COLOR_WHITE)
            self.screen.blit(line_surf, (x, line_y))

        # Bottom buttons: BACK, DELETE, REPLY
        btn_w = int(80 * self.scale)
        btn_h = int(22 * self.scale)
        btn_y = content_rect.bottom - btn_h - int(4 * self.scale)

        # BACK button
        back_rect = pygame.Rect(x, btn_y, btn_w, btn_h)
        is_hover = self.hovered_button == ("mail", "back")
        pygame.draw.rect(self.screen, (60, 60, 100) if is_hover else (40, 40, 70), back_rect)
        pygame.draw.rect(self.screen, COLOR_CYAN, back_rect, 2 if is_hover else 1)
        back_surf = self._mail_menu_font.render("BACK", True, COLOR_CYAN)
        self.screen.blit(back_surf, back_surf.get_rect(center=back_rect.center))
        self._mail_back_btn_rect = back_rect

        # DELETE button
        del_rect = pygame.Rect(x + btn_w + int(8 * self.scale), btn_y, btn_w, btn_h)
        is_hover = self.hovered_button == ("mail", "delete")
        pygame.draw.rect(self.screen, (60, 40, 40) if is_hover else (40, 30, 30), del_rect)
        pygame.draw.rect(self.screen, COLOR_RED, del_rect, 2 if is_hover else 1)
        del_surf = self._mail_menu_font.render("DELETE", True, COLOR_RED)
        self.screen.blit(del_surf, del_surf.get_rect(center=del_rect.center))
        self._mail_delete_btn_rect = del_rect

        # REPLY button
        reply_rect = pygame.Rect(x + 2 * (btn_w + int(8 * self.scale)), btn_y, btn_w, btn_h)
        is_hover = self.hovered_button == ("mail", "reply")
        pygame.draw.rect(self.screen, (60, 60, 100) if is_hover else (40, 40, 70), reply_rect)
        pygame.draw.rect(self.screen, COLOR_CYAN, reply_rect, 2 if is_hover else 1)
        reply_surf = self._mail_menu_font.render("REPLY", True, COLOR_CYAN)
        self.screen.blit(reply_surf, reply_surf.get_rect(center=reply_rect.center))
        self._mail_reply_btn_rect = reply_rect

    def _mail_wrap_text(self, text: str, font, max_width: int) -> List[str]:
        """Word-wrap text to fit within max_width pixels."""
        lines = []
        for paragraph in text.split("\n"):
            if not paragraph:
                lines.append("")
                continue
            words = paragraph.split(" ")
            current_line = ""
            for word in words:
                test_line = f"{current_line} {word}".strip() if current_line else word
                if font.size(test_line)[0] <= max_width:
                    current_line = test_line
                else:
                    if current_line:
                        lines.append(current_line)
                    # Handle very long words
                    if font.size(word)[0] > max_width:
                        while word:
                            for c in range(len(word), 0, -1):
                                if font.size(word[:c])[0] <= max_width:
                                    lines.append(word[:c])
                                    word = word[c:]
                                    break
                            else:
                                lines.append(word[:1])
                                word = word[1:]
                        current_line = ""
                    else:
                        current_line = word
            if current_line:
                lines.append(current_line)
        return lines if lines else [""]

    def _handle_mail_modal_click(self, mouse_x: int, mouse_y: int) -> bool:
        """Handle clicks within the BRADSONIC-MAIL modal."""
        modal_w, modal_h = self._get_modal_size("mail")
        modal_w, modal_h = self._clamp_modal_to_desktop(modal_w, modal_h)
        modal_x, modal_y = self.modal_positions.get("mail", (0, 0))
        modal_rect = pygame.Rect(modal_x, modal_y, modal_w, modal_h)

        if not modal_rect.collidepoint(mouse_x, mouse_y):
            return False

        # Close button
        close_btn_size = int(20 * self.scale)
        close_btn_x = modal_x + modal_w - close_btn_size - int(5 * self.scale)
        close_btn_y = modal_y + int(5 * self.scale)
        if pygame.Rect(close_btn_x, close_btn_y, close_btn_size, close_btn_size).collidepoint(mouse_x, mouse_y):
            self._close_modal("mail")
            return True

        # Menu bar clicks
        for btn_rect, view_name in getattr(self, "_mail_menu_hitboxes", []):
            if btn_rect.collidepoint(mouse_x, mouse_y):
                if view_name == "compose" and self.mail_view != "compose":
                    self.mail_compose_to = ""
                    self.mail_compose_subject = ""
                    self.mail_compose_body = ""
                    self.mail_compose_active_field = "to"
                    self.mail_compose_cursor = 0
                if view_name == "connect" and self.mail_view != "connect":
                    self._mail_connect_steps = []
                    self.mail_connect_terminal_lines = []
                    self.mail_connect_terminal_line_index = 0
                self.mail_view = view_name
                self.mail_selected_index = -1
                self.mail_reading_email = None
                self.mail_scroll_offset = 0
                return True

        # CONNECT view: SEND/RX and DIAL buttons
        if self.mail_view == "connect":
            if getattr(self, "_mail_sendrx_btn_rect", None) and self._mail_sendrx_btn_rect.collidepoint(mouse_x, mouse_y):
                if self.mail_server_connected:
                    self._mail_do_send_rx()
                return True
            if getattr(self, "_mail_dial_btn_rect", None) and self._mail_dial_btn_rect.collidepoint(mouse_x, mouse_y):
                in_progress = self.mail_connect_terminal_line_index > 0 and not self.mail_connect_terminal_complete
                if not in_progress:
                    self._start_mail_connect_sequence()
                return True

        if self.mail_view in ("inbox", "outbox", "trash"):
            for row_rect, idx in getattr(self, "_mail_list_hitboxes", []):
                if row_rect.collidepoint(mouse_x, mouse_y):
                    if self.mail_view == "inbox":
                        emails = self.mail_local_inbox
                    elif self.mail_view == "outbox":
                        emails = self.get_mail_outbox()
                    else:
                        emails = self.get_mail_trash()

                    if 0 <= idx < len(emails):
                        self.mail_selected_index = idx
                        email = emails[idx]
                        # Mark as read if inbox
                        if self.mail_view == "inbox" and not email.get("read", False):
                            email["read"] = True
                        self.mail_reading_email = dict(email)
                        self.mail_view = "reading"
                        self.mail_scroll_offset = 0
                    return True

        elif self.mail_view == "compose":
            # Field clicks
            if getattr(self, "_mail_compose_to_rect", None) and self._mail_compose_to_rect.collidepoint(mouse_x, mouse_y):
                self.mail_compose_active_field = "to"
                self.mail_compose_cursor = len(self.mail_compose_to)
                return True
            if getattr(self, "_mail_compose_subj_rect", None) and self._mail_compose_subj_rect.collidepoint(mouse_x, mouse_y):
                self.mail_compose_active_field = "subject"
                self.mail_compose_cursor = len(self.mail_compose_subject)
                return True
            if getattr(self, "_mail_compose_body_rect", None) and self._mail_compose_body_rect.collidepoint(mouse_x, mouse_y):
                self.mail_compose_active_field = "body"
                self.mail_compose_cursor = len(self.mail_compose_body)
                return True
            # SEND button
            if getattr(self, "_mail_send_btn_rect", None) and self._mail_send_btn_rect.collidepoint(mouse_x, mouse_y):
                self._mail_send_composed()
                return True
            # CLEAR button
            if getattr(self, "_mail_clear_btn_rect", None) and self._mail_clear_btn_rect.collidepoint(mouse_x, mouse_y):
                self.mail_compose_to = ""
                self.mail_compose_subject = ""
                self.mail_compose_body = ""
                self.mail_compose_active_field = "to"
                self.mail_compose_cursor = 0
                return True

        elif self.mail_view == "reading":
            # BACK button
            if getattr(self, "_mail_back_btn_rect", None) and self._mail_back_btn_rect.collidepoint(mouse_x, mouse_y):
                self.mail_view = "inbox"
                self.mail_reading_email = None
                self.mail_scroll_offset = 0
                return True
            # DELETE button
            if getattr(self, "_mail_delete_btn_rect", None) and self._mail_delete_btn_rect.collidepoint(mouse_x, mouse_y):
                if self.mail_reading_email:
                    self._mail_move_to_trash(self.mail_reading_email)
                self.mail_view = "inbox"
                self.mail_reading_email = None
                self.mail_scroll_offset = 0
                return True
            # REPLY button
            if getattr(self, "_mail_reply_btn_rect", None) and self._mail_reply_btn_rect.collidepoint(mouse_x, mouse_y):
                if self.mail_reading_email:
                    self.mail_compose_to = self.mail_reading_email.get("sender", "")
                    self.mail_compose_subject = "RE: " + self.mail_reading_email.get("subject", "")
                    self.mail_compose_body = ""
                    self.mail_compose_active_field = "body"
                    self.mail_compose_cursor = 0
                    self.mail_view = "compose"
                return True

        elif self.mail_view == "settings":
            if self._handle_mail_settings_click(mouse_x, mouse_y):
                return True

        return True  # Consumed click within modal

    def _mail_send_composed(self):
        """Send the composed email."""
        to = self.mail_compose_to.strip()
        subject = self.mail_compose_subject.strip()
        body = self.mail_compose_body.strip()

        if not to:
            self.mail_status_message = "Error: Recipient address required."
            self.mail_status_timer = 3.0
            return
        if not subject:
            self.mail_status_message = "Error: Subject required."
            self.mail_status_timer = 3.0
            return

        # Get sender from settings
        sender = self.mail_settings.get("mail_from", "user@bradsonic.net")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

        sent_email = {
            "id": f"sent_{int(time.time())}",
            "sender": sender,
            "recipient": to,
            "subject": subject,
            "body": body,
            "timestamp": timestamp,
            "read": True,
        }

        # Add to outbox only; actual send happens when user connects via CONNECT TO MAIL SERVER
        outbox = self.get_mail_outbox()
        outbox.insert(0, sent_email)
        self.save_mail_outbox(outbox)

        # Clear compose form and show status
        self.mail_compose_to = ""
        self.mail_compose_subject = ""
        self.mail_compose_body = ""
        self.mail_compose_active_field = "to"
        self.mail_compose_cursor = 0
        self.mail_status_message = "Message queued for send."
        self.mail_status_timer = 3.0
        self.mail_view = "outbox"

    def _mail_move_to_trash(self, email: Dict):
        """Move an email to trash."""
        trash = self.get_mail_trash()
        trash.insert(0, dict(email))
        self.save_mail_trash(trash)

        # Remove from local inbox
        self.mail_local_inbox = [e for e in self.mail_local_inbox if e.get("id") != email.get("id")]

        self.mail_status_message = "Message moved to trash."
        self.mail_status_timer = 3.0

    def _mail_handle_keydown(self, event) -> bool:
        """Handle keyboard input in compose or settings mode."""
        if self.mail_view == "settings":
            return self._mail_settings_handle_keydown(event)
        if self.mail_view != "compose":
            return False

        field = self.mail_compose_active_field
        if field == "to":
            text = self.mail_compose_to
        elif field == "subject":
            text = self.mail_compose_subject
        else:
            text = self.mail_compose_body

        cursor = min(self.mail_compose_cursor, len(text))

        if event.key == pygame.K_BACKSPACE:
            if cursor > 0:
                text = text[:cursor - 1] + text[cursor:]
                cursor -= 1
        elif event.key == pygame.K_DELETE:
            if cursor < len(text):
                text = text[:cursor] + text[cursor + 1:]
        elif event.key == pygame.K_LEFT:
            cursor = max(0, cursor - 1)
        elif event.key == pygame.K_RIGHT:
            cursor = min(len(text), cursor + 1)
        elif event.key == pygame.K_HOME:
            cursor = 0
        elif event.key == pygame.K_END:
            cursor = len(text)
        elif event.key == pygame.K_RETURN:
            if field == "body":
                text = text[:cursor] + "\n" + text[cursor:]
                cursor += 1
            elif field == "to":
                self.mail_compose_active_field = "subject"
                self.mail_compose_cursor = len(self.mail_compose_subject)
                self.mail_compose_to = text
                return True
            elif field == "subject":
                self.mail_compose_active_field = "body"
                self.mail_compose_cursor = len(self.mail_compose_body)
                self.mail_compose_subject = text
                return True
        elif event.key == pygame.K_TAB:
            # Cycle fields: to -> subject -> body -> to
            if field == "to":
                self.mail_compose_active_field = "subject"
                self.mail_compose_cursor = len(self.mail_compose_subject)
            elif field == "subject":
                self.mail_compose_active_field = "body"
                self.mail_compose_cursor = len(self.mail_compose_body)
            else:
                self.mail_compose_active_field = "to"
                self.mail_compose_cursor = len(self.mail_compose_to)
            if field == "to":
                self.mail_compose_to = text
            elif field == "subject":
                self.mail_compose_subject = text
            else:
                self.mail_compose_body = text
            return True
        elif event.key == pygame.K_v and (event.mod & pygame.KMOD_CTRL):
            # Paste from clipboard
            try:
                import subprocess
                clip_text = subprocess.check_output(['powershell', '-command', 'Get-Clipboard'], text=True).strip()
                text = text[:cursor] + clip_text + text[cursor:]
                cursor += len(clip_text)
            except Exception:
                pass
        else:
            return False  # Let TEXTINPUT handle character input

        # Save back
        if field == "to":
            self.mail_compose_to = text
        elif field == "subject":
            self.mail_compose_subject = text
        else:
            self.mail_compose_body = text
        self.mail_compose_cursor = cursor
        return True

    def _mail_handle_textinput(self, text: str) -> bool:
        """Handle text input for compose or settings fields."""
        if self.mail_view == "settings":
            return self._mail_settings_handle_textinput(text)
        if self.mail_view != "compose":
            return False

        field = self.mail_compose_active_field
        if field == "to":
            current = self.mail_compose_to
        elif field == "subject":
            current = self.mail_compose_subject
        else:
            current = self.mail_compose_body

        cursor = min(self.mail_compose_cursor, len(current))
        current = current[:cursor] + text + current[cursor:]
        cursor += len(text)

        if field == "to":
            self.mail_compose_to = current
        elif field == "subject":
            self.mail_compose_subject = current
        else:
            self.mail_compose_body = current
        self.mail_compose_cursor = cursor
        return True

    # -------------------------------------------------------------------------
    # BRADSONIC-MAIL Settings Page
    # -------------------------------------------------------------------------

    # Settings layout definition: list of (key, label, type)
    # type: "text" = editable text field, "radio" = radio button group, "check" = checkbox
    _MAIL_SETTINGS_LAYOUT = [
        ("_header_account", "── ACCOUNT SETTINGS ──", "header"),
        ("mail_from", "Mail From Address:", "text"),
        ("display_name", "Display Name:", "text"),
        ("reply_to", "Reply-To Address:", "text"),
        ("signature", "X-Signature Footer:", "text"),
        ("_header_server", "── SERVER CONFIGURATION ──", "header"),
        ("smtp_server", "SMTP Relay Host:", "text"),
        ("smtp_port", "SMTP Port:", "text"),
        ("pop3_server", "POP3/IMAP Server:", "text"),
        ("pop3_port", "POP3/IMAP Port:", "text"),
        ("protocol", "Mail Protocol:", "radio", ["POP3", "IMAP"]),
        ("auth_method", "Auth Method:", "radio", ["LOGIN", "PLAIN", "CRAM-MD5"]),
        ("encryption", "Connection Security:", "radio", ["None", "SSL", "TLS"]),
        ("_header_advanced", "── ADVANCED / MIME ──", "header"),
        ("mime_encoding", "MIME Transfer-Encoding:", "radio", ["quoted-printable", "base64", "7bit"]),
        ("charset", "Character Set:", "radio", ["US-ASCII", "ISO-8859-1", "UTF-8"]),
        ("max_msg_size", "Max Message Size (KB):", "text"),
        ("line_wrap", "Line Wrap Column:", "text"),
        ("check_interval", "Check Interval (min):", "text"),
        ("_header_options", "── OPTIONS ──", "header"),
        ("leave_on_server", "Leave Messages on Server", "check"),
        ("auto_bcc", "Auto-BCC to Self", "check"),
        ("x_mailer_header", "Include X-Mailer Header", "check"),
        ("delivery_receipt", "Request Delivery Receipt", "check"),
        ("read_receipt", "Request Read Receipt", "check"),
    ]

    def _draw_mail_settings(self, content_rect: pygame.Rect):
        """Draw the 1989-style email settings page with scrolling."""
        font = self._mail_settings_font
        x = content_rect.x + int(8 * self.scale)
        y_start = content_rect.y + int(6 * self.scale)
        field_w = content_rect.width - int(16 * self.scale)
        row_h = int(22 * self.scale)
        text_field_h = int(18 * self.scale)
        radio_size = int(12 * self.scale)
        check_size = int(12 * self.scale)
        label_w = int(180 * self.scale)

        # Cursor blink for active text field
        self.mail_cursor_blink_timer += 0.05
        show_cursor = (self.mail_cursor_blink_timer % 1.0) < 0.5

        # Calculate total height
        total_rows = len(self._MAIL_SETTINGS_LAYOUT)
        total_h = total_rows * row_h + int(10 * self.scale)
        visible_h = content_rect.height
        max_scroll = max(0, total_h - visible_h)
        self.mail_settings_scroll = max(0, min(self.mail_settings_scroll, max_scroll))

        self._mail_settings_hitboxes = []
        y = y_start - self.mail_settings_scroll

        for entry in self._MAIL_SETTINGS_LAYOUT:
            key = entry[0]
            label = entry[1]
            etype = entry[2]

            row_top = y
            if y + row_h < content_rect.y or y > content_rect.bottom:
                y += row_h
                continue  # Off-screen, skip drawing but advance

            if etype == "header":
                # Section header
                header_surf = font.render(label, True, COLOR_AMBER)
                self.screen.blit(header_surf, (x, y + int(4 * self.scale)))
                y += row_h
                continue

            # Draw label
            label_surf = font.render(label, True, COLOR_CYAN)
            self.screen.blit(label_surf, (x, y + int(3 * self.scale)))

            control_x = x + label_w

            if etype == "text":
                # Text entry field
                value = str(self.mail_settings.get(key, ""))
                is_active = self.mail_settings_active_field == key
                field_rect = pygame.Rect(control_x, y + int(1 * self.scale), field_w - label_w, text_field_h)
                bg = (30, 30, 55) if is_active else (15, 15, 30)
                pygame.draw.rect(self.screen, bg, field_rect)
                border = COLOR_CYAN if is_active else COLOR_GREY
                pygame.draw.rect(self.screen, border, field_rect, 1)

                # Render text (clip to field)
                text_surf = font.render(value, True, COLOR_WHITE)
                text_clip = field_rect.inflate(-int(4 * self.scale), 0)
                old_clip = self.screen.get_clip()
                self.screen.set_clip(text_clip)
                self.screen.blit(text_surf, (field_rect.x + int(3 * self.scale), field_rect.y + int(2 * self.scale)))
                if show_cursor and is_active:
                    cx = field_rect.x + int(3 * self.scale) + font.size(value[:self.mail_settings_cursor])[0]
                    pygame.draw.line(self.screen, COLOR_WHITE, (cx, field_rect.y + int(2 * self.scale)), (cx, field_rect.bottom - int(2 * self.scale)), 1)
                self.screen.set_clip(old_clip)

                self._mail_settings_hitboxes.append((field_rect, key, "text"))

            elif etype == "radio":
                options = entry[3]
                current_val = self.mail_settings.get(key, options[0])
                rx = control_x
                for opt in options:
                    # Radio circle
                    cy = y + row_h // 2
                    pygame.draw.circle(self.screen, COLOR_CYAN, (rx + radio_size // 2, cy), radio_size // 2, 1)
                    if current_val == opt:
                        pygame.draw.circle(self.screen, COLOR_CYAN, (rx + radio_size // 2, cy), radio_size // 2 - int(3 * self.scale))
                    opt_surf = font.render(opt, True, COLOR_WHITE)
                    self.screen.blit(opt_surf, (rx + radio_size + int(3 * self.scale), y + int(3 * self.scale)))
                    opt_w = radio_size + int(3 * self.scale) + opt_surf.get_width() + int(10 * self.scale)
                    hit_rect = pygame.Rect(rx, y, opt_w, row_h)
                    self._mail_settings_hitboxes.append((hit_rect, key, "radio", opt))
                    rx += opt_w

            elif etype == "check":
                current_val = bool(self.mail_settings.get(key, False))
                cy = y + row_h // 2
                check_rect = pygame.Rect(control_x, cy - check_size // 2, check_size, check_size)
                pygame.draw.rect(self.screen, COLOR_CYAN, check_rect, 1)
                if current_val:
                    # Draw check mark
                    inner = check_rect.inflate(-int(4 * self.scale), -int(4 * self.scale))
                    pygame.draw.rect(self.screen, COLOR_CYAN, inner)
                self._mail_settings_hitboxes.append((check_rect.inflate(int(8 * self.scale), int(4 * self.scale)), key, "check"))

            y += row_h

        # Scroll bar
        if total_h > visible_h:
            sb_x = content_rect.right - int(8 * self.scale)
            sb_w = int(6 * self.scale)
            sb_track = pygame.Rect(sb_x, content_rect.y, sb_w, content_rect.height)
            pygame.draw.rect(self.screen, (30, 30, 50), sb_track)
            thumb_h = max(int(20 * self.scale), int(content_rect.height * visible_h / total_h))
            thumb_y = content_rect.y + int((content_rect.height - thumb_h) * self.mail_settings_scroll / max_scroll) if max_scroll > 0 else content_rect.y
            thumb_rect = pygame.Rect(sb_x, thumb_y, sb_w, thumb_h)
            pygame.draw.rect(self.screen, COLOR_CYAN, thumb_rect)

    def _handle_mail_settings_click(self, mouse_x: int, mouse_y: int) -> bool:
        """Handle clicks on the settings page."""
        for entry in getattr(self, "_mail_settings_hitboxes", []):
            rect = entry[0]
            key = entry[1]
            etype = entry[2]
            if rect.collidepoint(mouse_x, mouse_y):
                if etype == "text":
                    self.mail_settings_active_field = key
                    self.mail_settings_cursor = len(str(self.mail_settings.get(key, "")))
                    return True
                elif etype == "radio":
                    opt = entry[3]
                    self.mail_settings[key] = opt
                    self.mail_settings_active_field = None
                    return True
                elif etype == "check":
                    self.mail_settings[key] = not bool(self.mail_settings.get(key, False))
                    self.mail_settings_active_field = None
                    return True
        # Clicked on empty area - deselect text field
        self.mail_settings_active_field = None
        return True

    def _mail_settings_handle_keydown(self, event) -> bool:
        """Handle keyboard input for settings text fields."""
        key = self.mail_settings_active_field
        if not key:
            return False

        text = str(self.mail_settings.get(key, ""))
        cursor = min(self.mail_settings_cursor, len(text))

        if event.key == pygame.K_BACKSPACE:
            if cursor > 0:
                text = text[:cursor - 1] + text[cursor:]
                cursor -= 1
        elif event.key == pygame.K_DELETE:
            if cursor < len(text):
                text = text[:cursor] + text[cursor + 1:]
        elif event.key == pygame.K_LEFT:
            cursor = max(0, cursor - 1)
        elif event.key == pygame.K_RIGHT:
            cursor = min(len(text), cursor + 1)
        elif event.key == pygame.K_HOME:
            cursor = 0
        elif event.key == pygame.K_END:
            cursor = len(text)
        elif event.key == pygame.K_RETURN or event.key == pygame.K_TAB:
            self.mail_settings_active_field = None
            return True
        elif event.key == pygame.K_ESCAPE:
            self.mail_settings_active_field = None
            return True
        else:
            return False

        self.mail_settings[key] = text
        self.mail_settings_cursor = cursor
        return True

    def _mail_settings_handle_textinput(self, text: str) -> bool:
        """Handle text character input for settings text fields."""
        key = self.mail_settings_active_field
        if not key:
            return False

        current = str(self.mail_settings.get(key, ""))
        cursor = min(self.mail_settings_cursor, len(current))
        current = current[:cursor] + text + current[cursor:]
        cursor += len(text)

        self.mail_settings[key] = current
        self.mail_settings_cursor = cursor
        return True

    def _get_icon_positions_file_path(self) -> str:
        """Get the path to the icon positions JSON file."""
        # Save in OS folder alongside OS_Mode.py
        os_folder = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(os_folder, "icon_positions.json")

    def _align_icons_to_tape_center(self):
        """Align every icon horizontally to the tape icon's center. Skip mail icon so it stays next to tape.
        Position dotSONIC under mail icon when mail exists."""
        if not self.icons or not self.desktop_rect:
            return
        tape_icon = next((icon for icon in self.icons if icon["name"] == "tape-icon.png"), None)
        if not tape_icon:
            return
        tape_center = tape_icon["x"] + tape_icon["width"] / 2
        for icon in self.icons:
            if icon["name"] == "mail-icon.png":
                continue  # Keep mail icon in its position next to tape, do not align to center
            if icon["name"] == "sonic-icon.png":
                mail_icon = next((i for i in self.icons if i["name"] == "mail-icon.png"), None)
                if mail_icon and not icon.get("from_saved"):
                    self._position_sonic_icon_under_mail()
                else:
                    # No mail or user saved position: align to tape center like other icons
                    aligned_x = int(tape_center - icon["width"] / 2)
                    aligned_x = max(self.desktop_rect.left, min(aligned_x, self.desktop_rect.right - icon["width"]))
                    icon["x"] = aligned_x
                continue
            aligned_x = int(tape_center - icon["width"] / 2)
            aligned_x = max(self.desktop_rect.left, min(aligned_x, self.desktop_rect.right - icon["width"]))
            icon["x"] = aligned_x

    def _apply_desktop_icon_vertical_offsets(self):
        """Apply vertical offsets to desktop icons to reduce overlap (percent of desktop height). Only applied when using default positions, not saved."""
        if not self.icons or not self.desktop_rect or not self.desktop_size[1]:
            return
        dh = self.desktop_size[1]
        # DATASETTE up 2%, NOTES down 7%, GAMES down 4.3%, MODEM down 2%, HDD unchanged
        offsets = {
            "tape-icon.png": -0.02 * dh,      # DATASETTE up 2%
            "notes-icon.png": 0.07 * dh,      # NOTES down 7%
            "games-folder.png": 0.043 * dh,   # GAMES down 4.3%
            "modem-iconpng.png": 0.02 * dh,   # MODEM down 2%
            "hard-drive-icon.png": 0,         # HDD keep where it is
        }
        top = self.desktop_rect.top
        bottom = self.desktop_rect.bottom
        for icon in self.icons:
            if icon.get("from_saved"):
                continue
            delta = offsets.get(icon["name"], 0)
            icon["y"] = int(icon["y"] + delta)
            icon["y"] = max(top, min(icon["y"], bottom - icon["height"]))

    def _load_games_icons(self, normalized_positions: Optional[Dict[str, Tuple[float, float]]] = None) -> None:
        """Load or reload the games modal icons with proper scaling.
        Civitas Nihilium is hidden unless region is US Mainland (os_locale == 1).
        Snooker is hidden unless region is Europe (os_locale == 2)."""
        icons: List[Dict[str, object]] = []
        for definition in self.games_icon_defs:
            # Region-based visibility: Civitas only on US Mainland, Snooker only on Europe
            if definition["name"] == "civitas_nihilium" and self.os_locale != 1:
                continue
            if definition["name"] == "snooker" and self.os_locale != 2:
                continue
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
        
        # Fix any overlapping icons (only if using default positions, not user-saved positions)
        if not normalized_positions:
            self._fix_overlapping_games_icons()

    def _load_hard_drive_icon(self) -> None:
        """Load the system-folder icon and (when US MAINLAND) file-system-folder icon for the hard drive modal."""
        try:
            normal_path = get_data_path("OS", "system-folder.png")
            selected_path = get_data_path("OS", "S-system-folder.png")
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
            
            self.hard_drive_modal_icon = {
                "image": normal_image,
                "s_image": selected_image,
                "width": icon_size[0],
                "height": icon_size[1],
                "rel_x": 0,  # Position relative to content rect (top-left)
                "rel_y": 0,
                "selected": False,
                "rect": None,
                "name": "SYSTEM"
            }
        except Exception as e:
            print(f"Warning: Failed to load system-folder icon: {e}")
            self.hard_drive_modal_icon = None

        # Load File System icon (file-system-folder.png) for HDD modal; shown when os_locale == US MAINLAND
        try:
            fs_normal_path = get_data_path("OS", "file-system-folder.png")
            fs_selected_path = get_data_path("OS", "S-file-system-folder.png")
            fs_normal = pygame.image.load(fs_normal_path).convert_alpha()
            fs_orig = fs_normal.get_size()
            fs_size = (int(fs_orig[0] * self.scale), int(fs_orig[1] * self.scale))
            fs_normal = pygame.transform.scale(fs_normal, fs_size)
            try:
                fs_selected = pygame.image.load(fs_selected_path).convert_alpha()
                fs_selected = pygame.transform.scale(fs_selected, fs_size)
            except Exception:
                fs_selected = fs_normal
            gap = int(10 * self.scale)
            default_rel_x = (self.hard_drive_modal_icon["width"] + gap) if self.hard_drive_modal_icon else gap
            self.hard_drive_modal_file_system_icon = {
                "image": fs_normal,
                "s_image": fs_selected,
                "width": fs_size[0],
                "height": fs_size[1],
                "rel_x": default_rel_x,
                "rel_y": 0,
                "selected": False,
                "rect": None,
                "name": "File System"
            }
        except Exception as e:
            print(f"Warning: Failed to load file-system-folder icon: {e}")
            self.hard_drive_modal_file_system_icon = None

    def _load_system_folder_icon(self) -> None:
        """Load the terminal-icon for the system folder modal."""
        try:
            normal_path = get_data_path("OS", "terminal-icon.png")
            selected_path = get_data_path("OS", "S-terminal-icon.png")
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
            
            self.system_folder_modal_icon = {
                "image": normal_image,
                "s_image": selected_image,
                "width": icon_size[0],
                "height": icon_size[1],
                "rel_x": 0,  # Position relative to content rect (top-left)
                "rel_y": 0,
                "selected": False,
                "rect": None  # Will be set when drawing
            }
        except Exception as e:
            print(f"Warning: Failed to load terminal-icon: {e}")
            self.system_folder_modal_icon = None

    def _load_file_system_browser_assets(self) -> None:
        """Load folder.png, S-folder.png, brad-file.png, S-brad-file.png, and Pixellari.ttf for file system browser."""
        try:
            folder_path = get_data_path("OS", "folder.png")
            s_folder_path = get_data_path("OS", "S-folder.png")
            folder_img = pygame.image.load(folder_path).convert_alpha()
            fw, fh = folder_img.get_size()
            fs = (int(fw * self.scale), int(fh * self.scale))
            folder_img = pygame.transform.scale(folder_img, fs)
            try:
                s_folder_img = pygame.image.load(s_folder_path).convert_alpha()
                s_folder_img = pygame.transform.scale(s_folder_img, fs)
            except Exception:
                s_folder_img = folder_img
            self.file_system_browser_folder_icon = {
                "image": folder_img, "s_image": s_folder_img, "width": fs[0], "height": fs[1]
            }
        except Exception as e:
            print(f"Warning: Failed to load folder icon: {e}")
            self.file_system_browser_folder_icon = None
        try:
            brad_path = get_data_path("OS", "brad-file.png")
            s_brad_path = get_data_path("OS", "S-brad-file.png")
            brad_img = pygame.image.load(brad_path).convert_alpha()
            bw, bh = brad_img.get_size()
            bs = (int(bw * self.scale), int(bh * self.scale))
            brad_img = pygame.transform.scale(brad_img, bs)
            try:
                s_brad_img = pygame.image.load(s_brad_path).convert_alpha()
                s_brad_img = pygame.transform.scale(s_brad_img, bs)
            except Exception:
                s_brad_img = brad_img
            self.file_system_browser_brad_icon = {
                "image": brad_img, "s_image": s_brad_img, "width": bs[0], "height": bs[1]
            }
        except Exception as e:
            print(f"Warning: Failed to load brad-file icon: {e}")
            self.file_system_browser_brad_icon = None
        try:
            sonic_path = get_data_path("OS", "sonic-file.png")
            s_sonic_path = get_data_path("OS", "S-sonic-file.png")
            if os.path.exists(sonic_path):
                sonic_img = pygame.image.load(sonic_path).convert_alpha()
                sw, sh = sonic_img.get_size()
                ss = (int(sw * self.scale), int(sh * self.scale))
                sonic_img = pygame.transform.scale(sonic_img, ss)
                try:
                    s_sonic_img = pygame.image.load(s_sonic_path).convert_alpha() if os.path.exists(s_sonic_path) else sonic_img
                    s_sonic_img = pygame.transform.scale(s_sonic_img, ss)
                except Exception:
                    s_sonic_img = sonic_img
                self.file_system_browser_sonic_icon = {
                    "image": sonic_img, "s_image": s_sonic_img, "width": ss[0], "height": ss[1]
                }
            else:
                self.file_system_browser_sonic_icon = self.file_system_browser_brad_icon
        except Exception as e:
            print(f"Warning: Failed to load sonic-file icon: {e}")
            self.file_system_browser_sonic_icon = self.file_system_browser_brad_icon
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            data_dir = os.path.dirname(script_dir)
            project_root = os.path.dirname(data_dir)
            pixellari_path = os.path.join(project_root, "Pixellari.ttf")
            font_size = max(int(16 * self.scale), 12)
            self.file_system_browser_font = pygame.font.Font(pixellari_path, font_size)
        except Exception as e:
            print(f"Warning: Failed to load Pixellari.ttf: {e}")
            self.file_system_browser_font = None

    def _add_mail_icon_to_desktop(self) -> None:
        """Add the mail icon to the desktop when Mainland America region is selected."""
        # Check if mail icon already exists
        for icon in self.icons:
            if icon["name"] == "mail-icon.png":
                return  # Already added
        
        try:
            icon_path = get_data_path("OS", "mail-icon.png")
            s_icon_path = get_data_path("OS", "S-mail-icon.png")
            
            # Load normal icon
            icon_image = pygame.image.load(icon_path).convert_alpha()
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
                print(f"Warning: Failed to load S-mail-icon.png: {e}")
                s_icon_image = icon_image
            
            # Position the mail icon next to the datasette (tape) icon - same row, no overlap
            tape_icon = next((icon for icon in self.icons if icon["name"] == "tape-icon.png"), None)
            spacing = int(10 * self.scale)
            
            # Check saved positions first
            saved_positions = self._load_icon_positions()
            if "mail-icon.png" in saved_positions:
                icon_x = saved_positions["mail-icon.png"]["x"]
                icon_y = saved_positions["mail-icon.png"]["y"]
            elif tape_icon:
                # Place to the right of the tape icon, same y (no overlapping)
                icon_x = tape_icon["x"] + tape_icon["width"] + spacing
                icon_y = tape_icon["y"]
                # Keep within desktop bounds
                icon_x = min(icon_x, self.desktop_rect.right - icon_size[0] - int(10 * self.scale)) if self.desktop_rect else icon_x
            else:
                # Fallback: below existing icons if tape icon not found
                lowest_y = self.desktop_y + int(70 * self.scale)
                for icon in self.icons:
                    icon_bottom = icon["y"] + icon["height"]
                    if icon_bottom > lowest_y:
                        lowest_y = icon_bottom
                icon_x = self.desktop_x + int(10 * self.scale)
                icon_y = lowest_y + spacing
            
            icon_data = {
                "image": icon_image,
                "s_image": s_icon_image,
                "x": icon_x,
                "y": icon_y,
                "width": icon_size[0],
                "height": icon_size[1],
                "name": "mail-icon.png",
                "label": "MAIL",
                "selected": False,
                "dragging": False,
                "drag_offset_x": 0,
                "drag_offset_y": 0,
                "from_saved": "mail-icon.png" in saved_positions,
            }
            self.icons.append(icon_data)
            self.mail_icon_visible = True
            # Position dotSONIC icon under mail icon with same spacing as other icons
            self._position_sonic_icon_under_mail()
            print("Mail icon added to desktop (Mainland America region selected)")
            
        except Exception as e:
            print(f"Warning: Failed to load mail-icon.png: {e}")

    def _position_sonic_icon_under_mail(self) -> None:
        """Position dotSONIC icon under the mail icon with same spacing (10px) as other desktop icons."""
        mail_icon = next((icon for icon in self.icons if icon["name"] == "mail-icon.png"), None)
        sonic_icon = next((icon for icon in self.icons if icon["name"] == "sonic-icon.png"), None)
        if not mail_icon or not sonic_icon or sonic_icon.get("from_saved") or not self.desktop_rect:
            return
        spacing = int(10 * self.scale)
        sonic_icon["x"] = mail_icon["x"]
        sonic_icon["y"] = mail_icon["y"] + mail_icon["height"] + spacing
        sonic_icon["y"] = max(self.desktop_rect.top, min(sonic_icon["y"], self.desktop_rect.bottom - sonic_icon["height"]))
    
    def _remove_mail_icon_from_desktop(self) -> None:
        """Remove the mail icon from the desktop when switching to Europe or Pacifica.
        Mail is only available in US Mainland (os_locale == 1)."""
        self.icons[:] = [icon for icon in self.icons if icon["name"] != "mail-icon.png"]
        self.mail_icon_visible = False

    def _switch_os_region(self, region_num: int) -> None:
        """Switch OS locale to region (1=US Mainland, 2=Europe, 3=Pacifica)."""
        self.os_locale = region_num
        if region_num == 1:
            self._add_mail_icon_to_desktop()
            if self.grant_token:
                self.grant_token("SCHOOL_HACK2", reason="region set to American Mainland / US MAINLAND")
        else:
            self._remove_mail_icon_from_desktop()
            if "mail" in self.active_modals:
                self._close_modal("mail")
        if region_num == 3 and "dot_sonic" in self.active_modals:
            self._close_modal("dot_sonic")
        self._load_games_icons()

    def _load_terminal_font(self) -> None:
        """Load VT323-Regular.ttf from the OS folder for the terminal."""
        try:
            font_path = get_data_path("OS", "VT323-Regular.ttf")
            font_size = max(int(21 * self.scale), 16)
            self.terminal_font = pygame.font.Font(font_path, font_size)
        except Exception as e:
            print(f"Warning: Failed to load terminal font (VT323-Regular.ttf): {e}")
            # Fallback to default font
            try:
                self.terminal_font = pygame.font.Font(None, max(int(21 * self.scale), 16))
            except Exception:
                self.terminal_font = None

    def _fix_overlapping_games_icons(self) -> None:
        """Check for overlapping icons and automatically arrange them to prevent overlaps."""
        if not self.games_modal_icons:
            return
        
        # Check if any icons overlap or are too close together
        has_overlap = False
        min_spacing = int(30 * self.scale)  # Minimum spacing between icons
        
        for i, icon1 in enumerate(self.games_modal_icons):
            rect1 = pygame.Rect(icon1["rel_x"], icon1["rel_y"], icon1["width"], icon1["height"])
            for icon2 in self.games_modal_icons[i + 1:]:
                rect2 = pygame.Rect(icon2["rel_x"], icon2["rel_y"], icon2["width"], icon2["height"])
                # Check for actual overlap
                if rect1.colliderect(rect2):
                    has_overlap = True
                    break
                # Also check if icons are too close (less than min_spacing apart)
                # Calculate distance between icon centers or edges
                if abs(rect1.x - rect2.x) < min_spacing and abs(rect1.y - rect2.y) < min_spacing:
                    # Icons are on same row/column and too close
                    if (rect1.y == rect2.y and abs(rect1.right - rect2.x) < min_spacing) or \
                       (rect1.x == rect2.x and abs(rect1.bottom - rect2.y) < min_spacing):
                        has_overlap = True
                        break
            if has_overlap:
                break
        
        # If there are overlaps or icons are too close, arrange icons in a grid
        if has_overlap:
            # Calculate grid layout with generous spacing
            icon_spacing = int(40 * self.scale)  # Increased spacing for better separation
            start_x = int(30 * self.scale)
            start_y = int(40 * self.scale)
            current_x = start_x
            current_y = start_y
            
            # Find the maximum icon dimensions
            max_icon_width = max(icon["width"] for icon in self.games_modal_icons) if self.games_modal_icons else 0
            max_icon_height = max(icon["height"] for icon in self.games_modal_icons) if self.games_modal_icons else 0
            
            # Use content rect width if available, otherwise estimate
            if self.games_modal_content_rect:
                content_width = self.games_modal_content_rect.width
            else:
                # Estimate based on typical modal size (will be refined when modal is drawn)
                content_width = int(500 * self.scale)
            
            # Arrange icons in a grid, wrapping to next row when needed
            for icon in self.games_modal_icons:
                # Check if this icon would go off the right edge
                if current_x + icon["width"] > content_width - int(20 * self.scale) and current_x > start_x:
                    # Move to next row
                    current_x = start_x
                    current_y += max_icon_height + icon_spacing
                
                icon["rel_x"] = current_x
                icon["rel_y"] = current_y
                
                # Move to next position with generous spacing
                current_x += icon["width"] + icon_spacing

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

    def _draw_hard_drive_modal(self) -> None:
        """Draw the hard drive modal with system-folder icon."""
        modal_w, modal_h = self._get_modal_size("hard_drive")
        modal_w, modal_h = self._clamp_modal_to_desktop(modal_w, modal_h)
        modal_x, modal_y = self.modal_positions.get("hard_drive", self._get_modal_position(modal_w, modal_h, "hard_drive"))
        if "hard_drive" not in self.modal_positions:
            self.modal_positions["hard_drive"] = (modal_x, modal_y)

        modal_rect = pygame.Rect(modal_x, modal_y, modal_w, modal_h)
        pygame.draw.rect(self.screen, COLOR_BG_DARK, modal_rect)
        pygame.draw.rect(self.screen, COLOR_CYAN, modal_rect, 2)

        title_bar_rect = pygame.Rect(modal_x, modal_y, modal_w, self.modal_title_bar_height)
        pygame.draw.rect(self.screen, COLOR_BG_TITLE, title_bar_rect)
        pygame.draw.rect(self.screen, COLOR_CYAN, title_bar_rect, 1)

        try:
            title_font = pygame.font.Font(None, max(int(16 * self.scale), 12))
            title_surface = title_font.render("HARD DRIVE", True, COLOR_WHITE)
            self.screen.blit(title_surface, (modal_x + int(10 * self.scale), modal_y + int(8 * self.scale)))
        except Exception:
            pass

        close_btn_size = int(20 * self.scale)
        close_btn_x = modal_x + modal_w - close_btn_size - int(5 * self.scale)
        close_btn_y = modal_y + int(5 * self.scale)
        close_btn_rect = pygame.Rect(close_btn_x, close_btn_y, close_btn_size, close_btn_size)
        is_hovered = self.hovered_button == ("hard_drive", "title_close")
        close_color = COLOR_RED if is_hovered else COLOR_RED_DARK
        pygame.draw.rect(self.screen, close_color, close_btn_rect)
        pygame.draw.rect(self.screen, COLOR_RED, close_btn_rect, 2 if is_hovered else 1)
        try:
            close_font = pygame.font.Font(None, max(int(14 * self.scale), 10))
            close_text = close_font.render("X", True, COLOR_WHITE)
            self.screen.blit(close_text, close_text.get_rect(center=close_btn_rect.center))
        except Exception:
            pass

        # Draw content area (matching games modal style)
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
        self.hard_drive_modal_content_rect = inner_rect

        # Draw SYSTEM icon (positioned in top-left, draggable)
        if self.hard_drive_modal_icon:
            icon = self.hard_drive_modal_icon
            icon["rel_x"] = max(0, min(icon["rel_x"], max(0, inner_rect.width - icon["width"])))
            icon["rel_y"] = max(0, min(icon["rel_y"], max(0, inner_rect.height - icon["height"])))
            draw_x = inner_rect.x + icon["rel_x"]
            draw_y = inner_rect.y + icon["rel_y"]
            image = icon["s_image"] if icon["selected"] else icon["image"]
            self.screen.blit(image, (draw_x, draw_y))
            icon["rect"] = pygame.Rect(draw_x, draw_y, icon["width"], icon["height"])
            self._draw_label_under_icon(draw_x, draw_y, icon["width"], icon["height"], "SYSTEM")

        # Draw File System icon next to SYSTEM when region is US MAINLAND or EUROPE (os_locale 1 or 2)
        if self.os_locale in (1, 2) and self.hard_drive_modal_file_system_icon:
            icon = self.hard_drive_modal_file_system_icon
            gap = int(10 * self.scale)
            max_rel_x = max(0, inner_rect.width - icon["width"])
            icon["rel_x"] = max(0, min(icon["rel_x"], max_rel_x))
            icon["rel_y"] = max(0, min(icon["rel_y"], max(0, inner_rect.height - icon["height"])))
            draw_x = inner_rect.x + icon["rel_x"]
            draw_y = inner_rect.y + icon["rel_y"]
            image = icon["s_image"] if icon["selected"] else icon["image"]
            self.screen.blit(image, (draw_x, draw_y))
            icon["rect"] = pygame.Rect(draw_x, draw_y, icon["width"], icon["height"])
            self._draw_label_under_icon(draw_x, draw_y, icon["width"], icon["height"], "FILE SYSTEM")

    def _handle_hard_drive_modal_click(self, mouse_x: int, mouse_y: int) -> bool:
        """Handle clicks within the hard drive modal."""
        modal_w, modal_h = self._get_modal_size("hard_drive")
        modal_w, modal_h = self._clamp_modal_to_desktop(modal_w, modal_h)
        modal_x, modal_y = self.modal_positions.get("hard_drive", (0, 0))

        close_btn_size = int(20 * self.scale)
        close_btn_rect = pygame.Rect(
            modal_x + modal_w - close_btn_size - int(5 * self.scale),
            modal_y + int(5 * self.scale),
            close_btn_size,
            close_btn_size
        )
        if close_btn_rect.collidepoint(mouse_x, mouse_y):
            self._close_modal("hard_drive")
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
        self.hard_drive_modal_content_rect = content_rect

        # When US MAINLAND or EUROPE: click/double-click File System icon
        if self.os_locale in (1, 2) and self.hard_drive_modal_file_system_icon:
            fs_rect = self.hard_drive_modal_file_system_icon.get("rect")
            if fs_rect and fs_rect.collidepoint(mouse_x, mouse_y):
                # Single click: select icon and deselect others
                self.hard_drive_modal_file_system_icon["selected"] = True
                if self.hard_drive_modal_icon:
                    self.hard_drive_modal_icon["selected"] = False
                self.hard_drive_modal_dragging_icon = self.hard_drive_modal_file_system_icon
                self.hard_drive_modal_drag_offset = (
                    mouse_x - fs_rect.x,
                    mouse_y - fs_rect.y
                )
                current_time = time.time()
                is_double = (self.hard_drive_modal_last_clicked_icon == "file_system" and
                             self.hard_drive_modal_last_click_time > 0 and
                             (current_time - self.hard_drive_modal_last_click_time) < self.double_click_threshold)
                self.hard_drive_modal_last_clicked_icon = "file_system"
                if is_double:
                    self.hard_drive_modal_last_click_time = 0.0
                    self.hard_drive_modal_file_system_icon["selected"] = False
                    self.file_system_browser_path = []
                    self.file_system_browser_items = self._list_file_system_browser_directory()
                    self.file_system_browser_selected_index = -1
                    self._open_modal("file_system_browser")
                else:
                    self.hard_drive_modal_last_click_time = current_time
                return True

        # Check if clicking on SYSTEM (system-folder) icon
        if self.hard_drive_modal_icon:
            icon_rect = self.hard_drive_modal_icon.get("rect")
            if icon_rect and icon_rect.collidepoint(mouse_x, mouse_y):
                self.hard_drive_modal_icon["selected"] = True
                if self.hard_drive_modal_file_system_icon:
                    self.hard_drive_modal_file_system_icon["selected"] = False
                self.hard_drive_modal_dragging_icon = self.hard_drive_modal_icon
                self.hard_drive_modal_drag_offset = (
                    mouse_x - icon_rect.x,
                    mouse_y - icon_rect.y
                )
                current_time = time.time()
                self.hard_drive_modal_last_clicked_icon = "system"
                if (self.hard_drive_modal_last_click_time > 0 and
                        (current_time - self.hard_drive_modal_last_click_time) < self.double_click_threshold):
                    self.hard_drive_modal_last_click_time = 0.0
                    self.hard_drive_modal_icon["selected"] = False
                    self._open_modal("system_folder")
                else:
                    self.hard_drive_modal_last_click_time = current_time
                return True

        if content_rect.collidepoint(mouse_x, mouse_y):
            if self.hard_drive_modal_icon:
                self.hard_drive_modal_icon["selected"] = False
            if self.hard_drive_modal_file_system_icon:
                self.hard_drive_modal_file_system_icon["selected"] = False
            self.hard_drive_modal_dragging_icon = None
            return True

        return False

    def _draw_system_folder_modal(self) -> None:
        """Draw the system folder modal with terminal-icon."""
        modal_w, modal_h = self._get_modal_size("system_folder")
        modal_w, modal_h = self._clamp_modal_to_desktop(modal_w, modal_h)
        modal_x, modal_y = self.modal_positions.get("system_folder", self._get_modal_position(modal_w, modal_h, "system_folder"))
        if "system_folder" not in self.modal_positions:
            self.modal_positions["system_folder"] = (modal_x, modal_y)

        modal_rect = pygame.Rect(modal_x, modal_y, modal_w, modal_h)
        pygame.draw.rect(self.screen, COLOR_BG_DARK, modal_rect)
        pygame.draw.rect(self.screen, COLOR_CYAN, modal_rect, 2)

        title_bar_rect = pygame.Rect(modal_x, modal_y, modal_w, self.modal_title_bar_height)
        pygame.draw.rect(self.screen, COLOR_BG_TITLE, title_bar_rect)
        pygame.draw.rect(self.screen, COLOR_CYAN, title_bar_rect, 1)

        try:
            title_font = pygame.font.Font(None, max(int(16 * self.scale), 12))
            title_surface = title_font.render("SYSTEM FOLDER", True, COLOR_WHITE)
            self.screen.blit(title_surface, (modal_x + int(10 * self.scale), modal_y + int(8 * self.scale)))
        except Exception:
            pass

        close_btn_size = int(20 * self.scale)
        close_btn_x = modal_x + modal_w - close_btn_size - int(5 * self.scale)
        close_btn_y = modal_y + int(5 * self.scale)
        close_btn_rect = pygame.Rect(close_btn_x, close_btn_y, close_btn_size, close_btn_size)
        is_hovered = self.hovered_button == ("system_folder", "title_close")
        close_color = COLOR_RED if is_hovered else COLOR_RED_DARK
        pygame.draw.rect(self.screen, close_color, close_btn_rect)
        pygame.draw.rect(self.screen, COLOR_RED, close_btn_rect, 2 if is_hovered else 1)
        try:
            close_font = pygame.font.Font(None, max(int(14 * self.scale), 10))
            close_text = close_font.render("X", True, COLOR_WHITE)
            self.screen.blit(close_text, close_text.get_rect(center=close_btn_rect.center))
        except Exception:
            pass

        # Draw content area (matching games modal style)
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
        self.system_folder_modal_content_rect = inner_rect

        # Draw terminal-icon (positioned in top-left, draggable)
        if self.system_folder_modal_icon:
            icon = self.system_folder_modal_icon
            icon["rel_x"] = max(0, min(icon["rel_x"], max(0, inner_rect.width - icon["width"])))
            icon["rel_y"] = max(0, min(icon["rel_y"], max(0, inner_rect.height - icon["height"])))
            draw_x = inner_rect.x + icon["rel_x"]
            draw_y = inner_rect.y + icon["rel_y"]
            image = icon["s_image"] if icon["selected"] else icon["image"]
            self.screen.blit(image, (draw_x, draw_y))
            icon["rect"] = pygame.Rect(draw_x, draw_y, icon["width"], icon["height"])
            self._draw_label_under_icon(draw_x, draw_y, icon["width"], icon["height"], ".TERMINAL")

    def _handle_system_folder_modal_click(self, mouse_x: int, mouse_y: int) -> bool:
        """Handle clicks within the system folder modal."""
        modal_w, modal_h = self._get_modal_size("system_folder")
        modal_w, modal_h = self._clamp_modal_to_desktop(modal_w, modal_h)
        modal_x, modal_y = self.modal_positions.get("system_folder", (0, 0))

        close_btn_size = int(20 * self.scale)
        close_btn_rect = pygame.Rect(
            modal_x + modal_w - close_btn_size - int(5 * self.scale),
            modal_y + int(5 * self.scale),
            close_btn_size,
            close_btn_size
        )
        if close_btn_rect.collidepoint(mouse_x, mouse_y):
            self._close_modal("system_folder")
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
        self.system_folder_modal_content_rect = content_rect

        # Check if clicking on terminal-icon
        if self.system_folder_modal_icon:
            icon_rect = self.system_folder_modal_icon.get("rect")
            if icon_rect and icon_rect.collidepoint(mouse_x, mouse_y):
                self.system_folder_modal_icon["selected"] = True
                self.system_folder_modal_dragging_icon = self.system_folder_modal_icon
                self.system_folder_modal_drag_offset = (
                    mouse_x - icon_rect.x,
                    mouse_y - icon_rect.y
                )
                current_time = time.time()
                # Check for double-click
                if (self.system_folder_modal_last_click_time > 0 and
                        (current_time - self.system_folder_modal_last_click_time) < self.double_click_threshold):
                    # Double-click - launch terminal or bring existing one to front
                    self.system_folder_modal_icon["selected"] = False
                    if self.terminal_active:
                        self._open_modal("terminal")
                    else:
                        self.terminal_active = True
                        self.terminal_text = ""
                        self.terminal_input_buffer = ""
                        self.terminal_cursor_blink_timer = 0.0
                        self.terminal_cursor_visible = True
                        self.terminal_position = None  # Will be centered on first draw
                        self.terminal_mode = "command"
                        self.terminal_admin_menu_selection = 1
                        self.terminal_region_selection = 1
                        self.terminal_message = ""
                        self.terminal_file_system_mode = False
                        self.terminal_file_system_path = []
                        self.terminal_file_content = []
                        self.terminal_file_view_filename = ""
                        self.terminal_file_scroll_index = 0
                        self.terminal_history_index = -1
                        self.terminal_current_input_line = ""
                        self.terminal_cursor_index = 0
                        self._open_modal("terminal")
                    self.system_folder_modal_last_click_time = 0.0
                else:
                    self.system_folder_modal_last_click_time = current_time
                return True

        if content_rect.collidepoint(mouse_x, mouse_y):
            # Deselect icon when clicking on empty area
            if self.system_folder_modal_icon:
                self.system_folder_modal_icon["selected"] = False
            self.system_folder_modal_dragging_icon = None
            return True

        return False

    def _draw_file_system_browser_modal(self) -> None:
        """Draw the file system browser modal: folders (folder.png) and .brad files (brad-file.png) with Pixellari cyan labels."""
        modal_w, modal_h = self._get_modal_size("file_system_browser")
        modal_w, modal_h = self._clamp_modal_to_desktop(modal_w, modal_h)
        modal_x, modal_y = self.modal_positions.get("file_system_browser", self._get_modal_position(modal_w, modal_h, "file_system_browser"))
        if "file_system_browser" not in self.modal_positions:
            self.modal_positions["file_system_browser"] = (modal_x, modal_y)

        modal_rect = pygame.Rect(modal_x, modal_y, modal_w, modal_h)
        pygame.draw.rect(self.screen, COLOR_BG_DARK, modal_rect)
        pygame.draw.rect(self.screen, COLOR_CYAN, modal_rect, 2)
        title_bar_rect = pygame.Rect(modal_x, modal_y, modal_w, self.modal_title_bar_height)
        pygame.draw.rect(self.screen, COLOR_BG_TITLE, title_bar_rect)
        pygame.draw.rect(self.screen, COLOR_CYAN, title_bar_rect, 1)

        title_text = "FILE-SYSTEM" + ("\\" + "\\".join(self.file_system_browser_path) if self.file_system_browser_path else "")
        try:
            title_font = pygame.font.Font(None, max(int(16 * self.scale), 12))
            title_surface = title_font.render(title_text[:50], True, COLOR_WHITE)
            self.screen.blit(title_surface, (modal_x + int(10 * self.scale), modal_y + int(8 * self.scale)))
        except Exception:
            pass

        close_btn_size = int(20 * self.scale)
        close_btn_x = modal_x + modal_w - close_btn_size - int(5 * self.scale)
        close_btn_y = modal_y + int(5 * self.scale)
        close_btn_rect = pygame.Rect(close_btn_x, close_btn_y, close_btn_size, close_btn_size)
        is_hovered = self.hovered_button == ("file_system_browser", "title_close")
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
        inner = content_rect.inflate(-int(10 * self.scale), -int(10 * self.scale))
        pygame.draw.rect(self.screen, COLOR_BG_DARK, inner)

        folder_icon = self.file_system_browser_folder_icon
        brad_icon = self.file_system_browser_brad_icon
        font = self.file_system_browser_font
        if not font:
            font = pygame.font.Font(None, max(int(14 * self.scale), 12))

        icon_gap = int(12 * self.scale)
        label_gap = int(8 * self.scale)  # Space between icon and text (match _draw_label_under_icon)
        padding_below_label = int(8 * self.scale)  # Padding just below the bottom of each label text
        cols = max(1, (inner.width + icon_gap) // (max(folder_icon["width"] if folder_icon else 64, brad_icon["width"] if brad_icon else 64) + icon_gap))
        row_height = (folder_icon["height"] if folder_icon else 48) + label_gap + (font.get_height() if font else 16) + padding_below_label

        sonic_icon = getattr(self, "file_system_browser_sonic_icon", None) or brad_icon
        for i, item in enumerate(self.file_system_browser_items):
            col = i % cols
            row = i // cols
            ix = inner.x + icon_gap + col * (inner.width // cols)
            iy = inner.y + icon_gap + row * row_height
            is_folder = item["type"] == "folder"
            is_sonic = item.get("file_type") == "sonic"
            icon_src = folder_icon if is_folder else (sonic_icon if is_sonic else brad_icon)
            icon_w = icon_src["width"] if icon_src else 48
            icon_h = icon_src["height"] if icon_src else 48
            if icon_src:
                selected = (i == self.file_system_browser_selected_index)
                img = icon_src["s_image"] if selected else icon_src["image"]
                self.screen.blit(img, (ix, iy))
            label = item["display_name"]
            display_label = self._truncate_icon_label(label) if label else ""
            label_surf = font.render(display_label, True, COLOR_CYAN) if font and display_label else None
            if label_surf:
                # Center-align label under icon (same as desktop and HDD icons)
                label_x = ix + (icon_w - label_surf.get_width()) // 2
                self.screen.blit(label_surf, (label_x, iy + icon_h + label_gap))
            w = max(icon_w, label_surf.get_width() if label_surf else 0)
            item["rect"] = pygame.Rect(ix, iy, w, row_height - icon_gap)

        # Draw ghost icon when dragging a file
        if self.file_system_browser_dragging_item:
            drag_item, ox, oy = self.file_system_browser_dragging_item
            is_sonic_drag = drag_item.get("file_type") == "sonic"
            icon_src = sonic_icon if is_sonic_drag else brad_icon
            if icon_src:
                mx, my = pygame.mouse.get_pos()
                ghost_x = mx - ox
                ghost_y = my - oy
                ghost_img = icon_src["s_image"].copy()
                ghost_img.set_alpha(180)
                self.screen.blit(ghost_img, (ghost_x, ghost_y))

    def _handle_file_system_browser_modal_click(self, mouse_x: int, mouse_y: int) -> bool:
        """Handle clicks in file system browser: single click select, double-click folder navigate, double-click .brad open in terminal window."""
        modal_w, modal_h = self._get_modal_size("file_system_browser")
        modal_w, modal_h = self._clamp_modal_to_desktop(modal_w, modal_h)
        modal_x, modal_y = self.modal_positions.get("file_system_browser", (0, 0))
        close_btn_size = int(20 * self.scale)
        close_btn_rect = pygame.Rect(
            modal_x + modal_w - close_btn_size - int(5 * self.scale),
            modal_y + int(5 * self.scale), close_btn_size, close_btn_size
        )
        if close_btn_rect.collidepoint(mouse_x, mouse_y):
            self._close_modal("file_system_browser")
            return True

        modal_rect = pygame.Rect(modal_x, modal_y, modal_w, modal_h)
        if not modal_rect.collidepoint(mouse_x, mouse_y):
            return False

        current_time = time.time()
        for i, item in enumerate(self.file_system_browser_items):
            r = item.get("rect")
            if r and r.collidepoint(mouse_x, mouse_y):
                key = f"{item['type']}:{item['display_name']}"
                is_double = (self.file_system_browser_last_clicked_key == key and
                             (current_time - self.file_system_browser_last_click_time) < self.double_click_threshold)
                self.file_system_browser_last_click_time = current_time
                self.file_system_browser_last_clicked_key = key

                if is_double:
                    self.file_system_browser_dragging_item = None
                    if item["type"] == "folder":
                        if item["real_name"] == "..":
                            if self.file_system_browser_path:
                                self.file_system_browser_path.pop()
                                self.file_system_browser_items = self._list_file_system_browser_directory()
                        else:
                            self.file_system_browser_path.append(item["real_name"])
                            self.file_system_browser_items = self._list_file_system_browser_directory()
                    elif item["type"] == "file":
                        # .sonic files: when opened from dotSONIC LOAD, add to playlist; else show info
                        if item.get("file_type") == "sonic":
                            if self.file_system_browser_opened_from_dot_sonic and self.dot_sonic_app:
                                self.dot_sonic_app.add_track_to_playlist(
                                    item["display_name"],
                                    item["real_name"],
                                    file_type="sonic",
                                    file_path=item.get("file_path")
                                )
                                # Keep browser open for adding more tracks
                            else:
                                title = item["display_name"]
                                lines = [
                                    f"  {title}",
                                    "",
                                    "  This is a .sonic audio file.",
                                    "  Play it from the Datasette."
                                ]
                                tw = int(500 * self.scale)
                                th = int(320 * self.scale)
                                tx = self.desktop_x + (self.desktop_size[0] - tw) // 2 + (len(self.terminal_file_windows) % 3) * int(30 * self.scale)
                                ty = self.desktop_y + (self.desktop_size[1] - th) // 2 + (len(self.terminal_file_windows) % 3) * int(25 * self.scale)
                                self.terminal_file_windows.append({
                                    "content": lines, "title": item["display_name"],
                                    "position": (tx, ty), "scroll": 0, "rect": None,
                                    "dragging": False, "drag_offset": (0, 0)
                                })
                        elif self.file_system_browser_opened_from_dot_sonic and self.dot_sonic_app:
                            # Physical .wav/.mp3 in DOWNLOADS - add to playlist
                            real_name = item.get("real_name", "")
                            if real_name.lower().endswith((".wav", ".mp3")):
                                browser_path = self._get_file_system_browser_path()
                                file_path = os.path.join(browser_path, real_name)
                                if os.path.isfile(file_path):
                                    self.dot_sonic_app.add_track_to_playlist(
                                        item["display_name"],
                                        real_name,
                                        file_type=None,
                                        file_path=file_path
                                    )
                        else:
                            # Double-click .brad: open file in new terminal file window
                            browser_path = self._get_file_system_browser_path()
                            file_path = os.path.join(browser_path, item["real_name"])
                            if os.path.isfile(file_path):
                                try:
                                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                                        lines = f.readlines()
                                    while lines and lines[-1].strip() == "":
                                        lines.pop()
                                    tw = int(500 * self.scale)
                                    th = int(320 * self.scale)
                                    tx = self.desktop_x + (self.desktop_size[0] - tw) // 2 + (len(self.terminal_file_windows) % 3) * int(30 * self.scale)
                                    ty = self.desktop_y + (self.desktop_size[1] - th) // 2 + (len(self.terminal_file_windows) % 3) * int(25 * self.scale)
                                    self.terminal_file_windows.append({
                                        "content": lines, "title": item["display_name"],
                                        "position": (tx, ty), "scroll": 0, "rect": None,
                                        "dragging": False, "drag_offset": (0, 0)
                                    })
                                except Exception as e:
                                    print(f"Error opening .brad file: {e}")
                else:
                    # Single click: select or deselect (toggle if already selected)
                    if self.file_system_browser_selected_index == i:
                        self.file_system_browser_selected_index = -1
                        self.file_system_browser_dragging_item = None
                    else:
                        self.file_system_browser_selected_index = i
                        if item["type"] == "file":
                            self.file_system_browser_dragging_item = (
                                item, mouse_x - r.x, mouse_y - r.y
                            )
                        else:
                            self.file_system_browser_dragging_item = None
                return True

        self.file_system_browser_selected_index = -1
        self.file_system_browser_dragging_item = None
        return True

    def _draw_terminal_file_window(self, win: Dict[str, Any]) -> None:
        """Draw a single terminal-style file viewer window (for .brad file content)."""
        # Cache title/close fonts by scale so many windows don't cause lag
        if getattr(self, "_terminal_file_window_scale", None) != self.scale:
            self._terminal_file_window_title_font = pygame.font.Font(None, max(int(14 * self.scale), 12))
            self._terminal_file_window_close_font = pygame.font.Font(None, max(int(12 * self.scale), 10))
            self._terminal_file_window_scale = self.scale
        tw = int(500 * self.scale)
        th = int(320 * self.scale)
        tx, ty = win["position"]
        tx = max(self.desktop_x, min(tx, self.desktop_x + self.desktop_size[0] - tw))
        ty = max(self.desktop_y, min(ty, self.desktop_y + self.desktop_size[1] - th))
        win["position"] = (tx, ty)
        win["rect"] = pygame.Rect(tx, ty, tw, th)
        pygame.draw.rect(self.screen, COLOR_BLACK, win["rect"])
        pygame.draw.rect(self.screen, COLOR_CYAN, win["rect"], 2)
        title_h = int(30 * self.scale)
        title_rect = pygame.Rect(tx, ty, tw, title_h)
        pygame.draw.rect(self.screen, COLOR_BG_TITLE, title_rect)
        pygame.draw.rect(self.screen, COLOR_CYAN, title_rect, 1)
        try:
            title_surf = self._terminal_file_window_title_font.render(win["title"][:40], True, COLOR_WHITE)
            self.screen.blit(title_surf, (tx + int(8 * self.scale), ty + int(6 * self.scale)))
        except Exception:
            pass
        close_sz = int(20 * self.scale)
        close_rect = pygame.Rect(tx + tw - close_sz - int(5 * self.scale), ty + int(5 * self.scale), close_sz, close_sz)
        pygame.draw.rect(self.screen, COLOR_RED, close_rect)
        pygame.draw.rect(self.screen, COLOR_WHITE, close_rect, 1)
        try:
            close_text = self._terminal_file_window_close_font.render("X", True, COLOR_WHITE)
            self.screen.blit(close_text, close_text.get_rect(center=close_rect.center))
        except Exception:
            pass
        win["close_rect"] = close_rect
        win["title_rect"] = title_rect
        content_x = tx + int(10 * self.scale)
        content_y = ty + title_h + int(10 * self.scale)
        content_w = tw - 2 * int(10 * self.scale)
        content_h = th - title_h - 2 * int(10 * self.scale)
        if not self.terminal_font:
            self._load_terminal_font()
        font = self.terminal_font or pygame.font.Font(None, max(int(18 * self.scale), 14))
        line_h = font.get_height()
        max_lines = content_h // line_h
        start = win["scroll"]
        end = min(start + max_lines, len(win["content"]))
        is_locale_protocols = "LocaleProtocols" in (win.get("title") or "")
        file_window_cyan = (0, 255, 255)
        file_window_light = (200, 255, 255)  # lighter cyan for pulse
        for i in range(start, end):
            line = win["content"][i].rstrip("\n\r")
            wrapped = self._wrap_terminal_text(line, font, content_w)
            for wline in wrapped:
                if content_y + line_h > ty + th - int(10 * self.scale):
                    break
                if is_locale_protocols:
                    segments = self._segment_line_for_locale_pulse(wline)
                    x_off = content_x
                    for seg_text, highlight in segments:
                        if seg_text:
                            color = self._get_terminal_pulse_color(file_window_cyan, file_window_light, speed=1.5) if highlight else file_window_cyan
                            surf = font.render(seg_text, True, color)
                            self.screen.blit(surf, (x_off, content_y))
                            x_off += surf.get_width()
                else:
                    surf = font.render(wline, True, file_window_cyan)
                    self.screen.blit(surf, (content_x, content_y))
                content_y += line_h

    def _handle_terminal_file_windows_click(self, mouse_x: int, mouse_y: int) -> bool:
        """Handle click on one of the terminal file windows. Returns True if a window was hit."""
        for win in reversed(self.terminal_file_windows):
            r = win.get("rect")
            if not r or not r.collidepoint(mouse_x, mouse_y):
                continue
            close_r = win.get("close_rect")
            if close_r and close_r.collidepoint(mouse_x, mouse_y):
                self.terminal_file_windows.remove(win)
                return True
            title_r = win.get("title_rect")
            if title_r and title_r.collidepoint(mouse_x, mouse_y):
                win["dragging"] = True
                win["drag_offset"] = (mouse_x - win["position"][0], mouse_y - win["position"][1])
                return True
            return True
        return False

    def _update_hard_drive_icon_drag(self, mouse_x: int, mouse_y: int) -> bool:
        """Update hard drive modal icon position while dragging."""
        if not self.hard_drive_modal_dragging_icon or not self.hard_drive_modal_content_rect:
            return False
        icon = self.hard_drive_modal_dragging_icon
        offset_x, offset_y = self.hard_drive_modal_drag_offset
        content_rect = self.hard_drive_modal_content_rect
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

    def _update_system_folder_icon_drag(self, mouse_x: int, mouse_y: int) -> bool:
        """Update system folder modal icon position while dragging."""
        if not self.system_folder_modal_dragging_icon or not self.system_folder_modal_content_rect:
            return False
        icon = self.system_folder_modal_dragging_icon
        offset_x, offset_y = self.system_folder_modal_drag_offset
        content_rect = self.system_folder_modal_content_rect
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

    def _get_prompt_text(self) -> str:
        """Get the current prompt text based on mode."""
        if self.terminal_file_system_mode:
            # Show file system path
            if self.terminal_file_system_path:
                return ".\\file-system\\" + "\\".join(self.terminal_file_system_path) + "\\"
            else:
                return ".\\file-system\\"
        else:
            return "."

    def _get_file_system_path(self) -> str:
        """Get the full file system path based on current navigation."""
        return os.path.join(self.terminal_file_system_base_path, *self.terminal_file_system_path)

    def _get_file_system_browser_path(self) -> str:
        """Get the full path for the file system browser modal."""
        return os.path.join(self.terminal_file_system_base_path, *self.file_system_browser_path)

    def _list_file_system_browser_directory(self) -> List[Dict[str, Any]]:
        """List items in current browser path. Returns list of { type, display_name, real_name, file_type? }.
        DOWNLOADS folder and .sonic files only visible when os_locale is US Mainland (1) or Europe (2)."""
        current_path = self._get_file_system_browser_path()
        items = []
        downloads_visible = self.os_locale in (1, 2)

        if self.file_system_browser_path:
            items.append({"type": "folder", "display_name": "..", "real_name": ".."})
            # Inside DOWNLOADS (match case-insensitively: downloads, DOWNLOADS, etc.)
            if len(self.file_system_browser_path) == 1 and self.file_system_browser_path[0].upper() == "DOWNLOADS":
                base_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "FILE-SYSTEM")
                # Virtual .sonic files from BBS downloads (when region allows)
                if downloads_visible:
                    for title in self.get_downloaded_fugamatchi_tracks():
                        items.append({
                            "type": "file",
                            "display_name": title + ".sonic",
                            "real_name": f"__sonic__{title}",
                            "file_type": "sonic",
                        })
                # Physical files from disk (if folder exists as downloads/DOWNLOADS etc.)
                for disk_item in (os.listdir(base_path) if os.path.isdir(base_path) else []):
                    if disk_item.upper() == "DOWNLOADS":
                        phys_path = os.path.join(base_path, disk_item)
                        if os.path.isdir(phys_path):
                            for f in sorted(os.listdir(phys_path)):
                                fp = os.path.join(phys_path, f)
                                if os.path.isfile(fp):
                                    if f.lower().endswith(".txt"):
                                        items.append({"type": "file", "display_name": f[:-4] + ".brad", "real_name": f, "file_type": "brad"})
                                    elif f.lower().endswith((".mp3", ".wav")):
                                        items.append({"type": "file", "display_name": os.path.splitext(f)[0] + ".sonic", "real_name": f, "file_type": "sonic", "file_path": fp})
                                    else:
                                        items.append({"type": "file", "display_name": f, "real_name": f})
                                elif os.path.isdir(fp):
                                    items.append({"type": "folder", "display_name": f, "real_name": f})
                        break
                return items
        if not os.path.exists(current_path):
            return items
        try:
            dir_items = sorted(os.listdir(current_path))
            has_downloads_on_disk = any(x.upper() == "DOWNLOADS" for x in dir_items)
            # Add virtual "DOWNLOADS" folder at root when region allows (US Mainland/Europe)
            # DOWNLOADS folder may not exist on disk - it shows .sonic tracks from user state
            # Use case-insensitive check to avoid duplicate when physical DOWNLOADS/downloads exists
            if not self.file_system_browser_path and downloads_visible and not has_downloads_on_disk:
                items.append({"type": "folder", "display_name": "DOWNLOADS", "real_name": "DOWNLOADS"})
            for item in dir_items:
                if item.upper() == "DOWNLOADS":
                    if downloads_visible:
                        items.append({"type": "folder", "display_name": "DOWNLOADS", "real_name": "DOWNLOADS"})
                    continue
                item_path = os.path.join(current_path, item)
                if os.path.isdir(item_path):
                    items.append({"type": "folder", "display_name": item, "real_name": item})
                elif os.path.isfile(item_path):
                    if item.lower().endswith(".txt"):
                        items.append({"type": "file", "display_name": item[:-4] + ".brad", "real_name": item, "file_type": "brad"})
                    elif item.lower().endswith((".mp3", ".wav")):
                        items.append({"type": "file", "display_name": os.path.splitext(item)[0] + ".sonic", "real_name": item, "file_type": "sonic", "file_path": item_path})
                    else:
                        items.append({"type": "file", "display_name": item, "real_name": item})
        except Exception as e:
            print(f"Error listing file system browser: {e}")
        return items
    
    def _list_file_system_directory(self) -> Tuple[List[str], List[str]]:
        """List files and folders in current directory. Returns (folders, files).
        DOWNLOADS folder and .sonic files only visible when os_locale is US Mainland (1) or Europe (2)."""
        folders = []
        files = []
        downloads_visible = self.os_locale in (1, 2)

        # Special case: inside virtual DOWNLOADS folder (shows .sonic files from user state)
        if len(self.terminal_file_system_path) == 1 and self.terminal_file_system_path[0].upper() == "DOWNLOADS":
            if downloads_visible:
                for title in self.get_downloaded_fugamatchi_tracks():
                    files.append(title + ".sonic")
            # Also list physical files from disk if DOWNLOADS folder exists
            base_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "FILE-SYSTEM")
            if os.path.isdir(base_path):
                for disk_item in os.listdir(base_path):
                    if disk_item.upper() == "DOWNLOADS":
                        phys_path = os.path.join(base_path, disk_item)
                        if os.path.isdir(phys_path):
                            for f in sorted(os.listdir(phys_path)):
                                fp = os.path.join(phys_path, f)
                                if os.path.isfile(fp):
                                    if f.lower().endswith(".txt"):
                                        files.append(f[:-4] + ".brad")
                                    elif f.lower().endswith((".mp3", ".wav")):
                                        files.append(os.path.splitext(f)[0] + ".sonic")
                                    else:
                                        files.append(f)
                                elif os.path.isdir(fp):
                                    folders.append(f)
                        break
            return sorted(folders), sorted(files)

        current_path = self._get_file_system_path()
        if not os.path.exists(current_path):
            # At root: add virtual DOWNLOADS folder when region allows
            if not self.terminal_file_system_path and downloads_visible:
                folders.append("DOWNLOADS")
            return sorted(folders), sorted(files)

        try:
            dir_items = sorted(os.listdir(current_path))
            has_downloads_on_disk = any(x.upper() == "DOWNLOADS" for x in dir_items)
            # Add virtual DOWNLOADS folder at root when region allows and not on disk
            if not self.terminal_file_system_path and downloads_visible and not has_downloads_on_disk:
                folders.append("DOWNLOADS")
            for item in dir_items:
                if item.upper() == "DOWNLOADS":
                    if downloads_visible:
                        folders.append(item if item == "DOWNLOADS" else "DOWNLOADS")
                    continue
                item_path = os.path.join(current_path, item)
                if os.path.isdir(item_path):
                    folders.append(item)
                elif os.path.isfile(item_path):
                    if item.lower().endswith('.txt'):
                        files.append(item[:-4] + '.brad')
                    elif item.lower().endswith(('.mp3', '.wav')):
                        files.append(os.path.splitext(item)[0] + '.sonic')
                    else:
                        files.append(item)
        except Exception as e:
            print(f"Error listing directory: {e}")

        return sorted(folders), sorted(files)
    
    def _get_school_op_note_content(self, with_credentials: bool = False) -> str:
        """Return School Op note content. with_credentials=False: placeholders (ghost). with_credentials=True: filled in (after observing LocaleProtocols)."""
        lines = SCHOOL_HACK_NOTE_LINES_WITH_CREDS if with_credentials else SCHOOL_HACK_NOTE_LINES_NO_CREDS
        return "\n".join(lines)

    def _replace_school_op_note_content(self) -> bool:
        """Replace the School Op - Steps note with the version that has credentials (admin-subset, username, password).
        Called when player observes LocaleProtocols.brad - marks progress."""
        notes = self._load_user_notes()
        for n in notes:
            if n.get("title") == SCHOOL_OP_NOTE_TITLE:
                new_content = self._get_school_op_note_content(with_credentials=True)
                if n.get("content") != new_content:
                    n["content"] = new_content
                    self._save_user_notes(notes)
                return True
        return False

    def _open_file_in_terminal(self, filename: str) -> bool:
        """Open a file in the terminal. Returns True if successful."""
        original_filename = filename  # Keep for display/pulse (e.g. LocaleProtocols.brad)
        # Virtual .sonic files in DOWNLOADS (when in terminal file-system and path is DOWNLOADS)
        if (self.terminal_file_system_mode and len(self.terminal_file_system_path) == 1 and
                self.terminal_file_system_path[0].upper() == "DOWNLOADS" and self.os_locale in (1, 2)):
            if filename.endswith('.sonic'):
                title = filename[:-6]  # strip .sonic
                if title in self.get_downloaded_fugamatchi_tracks():
                    lines = [
                        f"  {filename}",
                        "",
                        "  This is a .sonic audio file.",
                        "  Play it from the Datasette."
                    ]
                    self.terminal_file_content = lines
                    self.terminal_file_view_filename = filename
                    self.terminal_file_scroll_index = 0
                    self.terminal_mode = "file_view"
                    return True
        # Convert .brad to .txt for actual file lookup
        if filename.endswith('.brad'):
            filename = filename[:-5] + '.txt'
        # .sonic can be backed by .mp3 or .wav on disk
        sonic_base = None
        if filename.endswith('.sonic'):
            sonic_base = filename[:-6]
        current_path = self._get_file_system_path()
        # Resolve DOWNLOADS to physical folder name if it exists on disk
        if (len(self.terminal_file_system_path) == 1 and self.terminal_file_system_path[0].upper() == "DOWNLOADS"):
            base_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "FILE-SYSTEM")
            if os.path.isdir(base_path):
                for disk_item in os.listdir(base_path):
                    if disk_item.upper() == "DOWNLOADS":
                        current_path = os.path.join(base_path, disk_item)
                        break
        file_path = os.path.join(current_path, filename)
        if not os.path.exists(file_path) or not os.path.isfile(file_path):
            if sonic_base:
                for ext in ('.mp3', '.wav'):
                    alt_path = os.path.join(current_path, sonic_base + ext)
                    if os.path.isfile(alt_path):
                        file_path = alt_path
                        break
                else:
                    return False
            else:
                return False
        if file_path.lower().endswith(('.mp3', '.wav')):
            self.terminal_file_content = [
                f"  {original_filename}",
                "",
                "  This is a .sonic audio file.",
                "  Play it from the Datasette."
            ]
            self.terminal_file_view_filename = original_filename
            self.terminal_file_scroll_index = 0
            self.terminal_mode = "file_view"
            return True
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                self.terminal_file_content = f.readlines()
            # Remove trailing newlines and empty lines at end
            while self.terminal_file_content and self.terminal_file_content[-1].strip() == '':
                self.terminal_file_content.pop()
            self.terminal_file_view_filename = original_filename
            self.terminal_file_scroll_index = 0
            self.terminal_mode = "file_view"
            # When player observes LocaleProtocols file, replace School Op note with full list (admin-subset, username, password)
            if "LocaleProtocols" in original_filename:
                self._replace_school_op_note_content()
            return True
        except Exception as e:
            print(f"Error opening file: {e}")
            return False

    def _wrap_terminal_text(self, text: str, font: pygame.font.Font, max_width: int) -> List[str]:
        """Wrap text to fit within terminal width."""
        words = text.split(' ')
        lines = []
        current_line = ""
        
        for word in words:
            test_line = current_line + (" " if current_line else "") + word
            test_surface = font.render(test_line, True, COLOR_GREEN)
            if test_surface.get_width() <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                # If single word is too long, break it
                if font.render(word, True, COLOR_GREEN).get_width() > max_width:
                    # Word is too long, break it character by character
                    for char in word:
                        test_char = current_line + char
                        if font.render(test_char, True, COLOR_GREEN).get_width() <= max_width:
                            current_line = test_char
                        else:
                            if current_line:
                                lines.append(current_line)
                            current_line = char
                else:
                    current_line = word
        
        if current_line:
            lines.append(current_line)
        
        return lines if lines else [""]

    # Keywords to pulse when viewing LocaleProtocols.brad (admin string hints)
    # "general" is case-sensitive (only lowercase) so "General" elsewhere in text does not pulse
    _LOCALE_PULSE_KEYWORDS_CI = ["admin-subset", "louis-sonic"]  # case-insensitive
    _LOCALE_PULSE_KEYWORD_GENERAL = "general"  # case-sensitive: only pulse lowercase "general"

    def _segment_line_for_locale_pulse(self, line: str) -> List[Tuple[str, bool]]:
        """Split a line into (text, is_highlight) segments for admin-subset/general/louis-sonic."""
        line_lower = line.lower()
        ranges = []  # (start, end)
        for kw in self._LOCALE_PULSE_KEYWORDS_CI:
            start = 0
            while True:
                i = line_lower.find(kw.lower(), start)
                if i == -1:
                    break
                ranges.append((i, i + len(kw)))
                start = i + 1
        # Only pulse lowercase "general", not "General"
        start = 0
        while True:
            i = line.find(self._LOCALE_PULSE_KEYWORD_GENERAL, start)
            if i == -1:
                break
            ranges.append((i, i + len(self._LOCALE_PULSE_KEYWORD_GENERAL)))
            start = i + 1
        ranges.sort()
        merged = []
        for s, e in ranges:
            if merged and s <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], e))
            else:
                merged.append((s, e))
        segments = []
        pos = 0
        for s, e in merged:
            if pos < s:
                segments.append((line[pos:s], False))
            segments.append((line[s:e], True))
            pos = e
        if pos < len(line):
            segments.append((line[pos:], False))
        return segments if segments else [(line, False)]

    def _get_terminal_pulse_color(self, base_rgb: Tuple[int, int, int], light_rgb: Tuple[int, int, int], speed: float = 1.5) -> Tuple[int, int, int]:
        """Pulse between base and light color for terminal highlight."""
        t = time.time() * speed
        pulse = (math.sin(t) + 1) / 2
        return (
            int(base_rgb[0] + (light_rgb[0] - base_rgb[0]) * pulse),
            int(base_rgb[1] + (light_rgb[1] - base_rgb[1]) * pulse),
            int(base_rgb[2] + (light_rgb[2] - base_rgb[2]) * pulse),
        )

    def _draw_terminal(self) -> None:
        """Draw the terminal application window."""
        # Terminal window size - width increased by 33% (665x375)
        terminal_w = int(665 * self.scale)  # 33% larger: 500 * 1.33 = 665
        terminal_h = int(375 * self.scale)  # 25% larger: 300 * 1.25 = 375
        
        # Use stored position if available, otherwise center on desktop
        if self.terminal_position:
            terminal_x, terminal_y = self.terminal_position
        else:
            terminal_x = self.desktop_x + (self.desktop_size[0] - terminal_w) // 2
            terminal_y = self.desktop_y + (self.desktop_size[1] - terminal_h) // 2
        
        # Ensure terminal doesn't exceed desktop boundaries
        terminal_x = max(self.desktop_x, min(terminal_x, self.desktop_x + self.desktop_size[0] - terminal_w))
        terminal_y = max(self.desktop_y, min(terminal_y, self.desktop_y + self.desktop_size[1] - terminal_h))
        
        # Update stored position
        self.terminal_position = (terminal_x, terminal_y)
        
        # Draw terminal window background (black)
        terminal_rect = pygame.Rect(terminal_x, terminal_y, terminal_w, terminal_h)
        pygame.draw.rect(self.screen, COLOR_BLACK, terminal_rect)
        pygame.draw.rect(self.screen, COLOR_CYAN, terminal_rect, 2)  # Cyan border to match OS look
        
        # Draw title bar
        title_bar_height = int(30 * self.scale)
        title_bar_rect = pygame.Rect(terminal_x, terminal_y, terminal_w, title_bar_height)
        pygame.draw.rect(self.screen, COLOR_BG_TITLE, title_bar_rect)
        pygame.draw.rect(self.screen, COLOR_CYAN, title_bar_rect, 1)
        
        try:
            title_font = pygame.font.Font(None, max(int(16 * self.scale), 12))
            title_surface = title_font.render("TERMINAL", True, COLOR_WHITE)
            self.screen.blit(title_surface, (terminal_x + int(10 * self.scale), terminal_y + int(8 * self.scale)))
        except Exception:
            pass
        
        # Close button
        close_btn_size = int(20 * self.scale)
        close_btn_x = terminal_x + terminal_w - close_btn_size - int(5 * self.scale)
        close_btn_y = terminal_y + int(5 * self.scale)
        close_btn_rect = pygame.Rect(close_btn_x, close_btn_y, close_btn_size, close_btn_size)
        pygame.draw.rect(self.screen, COLOR_RED, close_btn_rect)
        pygame.draw.rect(self.screen, COLOR_WHITE, close_btn_rect, 1)
        try:
            close_font = pygame.font.Font(None, max(int(14 * self.scale), 10))
            close_text = close_font.render("X", True, COLOR_WHITE)
            self.screen.blit(close_text, close_text.get_rect(center=close_btn_rect.center))
        except Exception:
            pass
        
        # Draw terminal content area
        content_x = terminal_x + int(10 * self.scale)
        content_y = terminal_y + title_bar_height + int(10 * self.scale)
        content_w = terminal_w - 2 * int(10 * self.scale)
        content_h = terminal_h - title_bar_height - 2 * int(10 * self.scale)
        
        # Draw text with Paper Crane BBS font (reduced by 20% from previous)
        if not self.terminal_font:
            self._load_terminal_font()
        
        if self.terminal_font:
            line_height = self.terminal_font.get_height()
            
            # Handle different terminal modes
            if self.terminal_mode == "message":
                # Display message (with wrapping)
                message_lines = self._wrap_terminal_text(self.terminal_message, self.terminal_font, content_w)
                message_start_y = content_y + (content_h - len(message_lines) * line_height) // 2
                for i, line in enumerate(message_lines):
                    message_surface = self.terminal_font.render(line, True, COLOR_GREEN)
                    self.screen.blit(message_surface, (content_x, message_start_y + i * line_height))
                
            elif self.terminal_mode == "region_select":
                # Draw region selection menu
                title_y = content_y + int(10 * self.scale)
                title_surface = self.terminal_font.render("REGION DETECTION", True, COLOR_WHITE)
                self.screen.blit(title_surface, (content_x, title_y))
                
                regions = [
                    "01 American Mainland",
                    "02 Europe",
                    "03 American Pacific Isles (restricted cap)"
                ]
                
                menu_start_y = title_y + line_height + int(20 * self.scale)
                for i, region in enumerate(regions, 1):
                    region_y = menu_start_y + (i - 1) * (line_height + int(5 * self.scale))
                    color = COLOR_GREEN if i == self.terminal_region_selection else COLOR_CYAN
                    region_text = f"{region}"
                    region_surface = self.terminal_font.render(region_text, True, color)
                    self.screen.blit(region_surface, (content_x + int(20 * self.scale), region_y))
                
            elif self.terminal_mode == "admin_menu":
                # Draw admin menu
                title_y = content_y + int(10 * self.scale)
                title_surface = self.terminal_font.render("Bradsonic 69000 Admin Security", True, COLOR_WHITE)
                self.screen.blit(title_surface, (content_x, title_y))
                
                menu_items = [
                    "1. Perform Factory Reset",
                    "2. Region Detection",
                    "3. Handshake Connected Node",
                    "4. Shutdown System"
                ]
                
                menu_start_y = title_y + line_height + int(20 * self.scale)
                for i, item in enumerate(menu_items, 1):
                    item_y = menu_start_y + (i - 1) * (line_height + int(5 * self.scale))
                    color = COLOR_GREEN if i == self.terminal_admin_menu_selection else COLOR_CYAN
                    item_surface = self.terminal_font.render(item, True, color)
                    self.screen.blit(item_surface, (content_x + int(20 * self.scale), item_y))
            
            elif self.terminal_mode == "admin_login_username":
                # Draw username prompt
                prompt_text = "."
                prompt_surface = self.terminal_font.render(prompt_text, True, COLOR_GREEN)
                self.screen.blit(prompt_surface, (content_x, content_y + content_h - line_height))
                
                username_prompt = "username:"
                prompt_y = content_y + content_h - 2 * line_height
                username_surface = self.terminal_font.render(username_prompt, True, COLOR_CYAN)
                self.screen.blit(username_surface, (content_x, prompt_y))
                
                # Draw current input
                input_text = prompt_text + self.terminal_input_buffer
                input_surface = self.terminal_font.render(input_text, True, COLOR_GREEN)
                input_y = content_y + content_h - line_height
                self.screen.blit(input_surface, (content_x, input_y))
                
                # Draw blinking cursor
                if self.terminal_cursor_visible:
                    cursor_x = content_x + input_surface.get_width()
                    cursor_y = input_y
                    cursor_rect = pygame.Rect(cursor_x, cursor_y, int(2 * self.scale), line_height)
                    pygame.draw.rect(self.screen, COLOR_GREEN, cursor_rect)
            
            elif self.terminal_mode == "admin_login_password":
                # Draw password prompt
                prompt_text = "."
                prompt_surface = self.terminal_font.render(prompt_text, True, COLOR_GREEN)
                self.screen.blit(prompt_surface, (content_x, content_y + content_h - line_height))
                
                password_prompt = "password:"
                prompt_y = content_y + content_h - 2 * line_height
                password_surface = self.terminal_font.render(password_prompt, True, COLOR_CYAN)
                self.screen.blit(password_surface, (content_x, prompt_y))
                
                # Draw current input (masked as asterisks)
                masked_input = "*" * len(self.terminal_input_buffer)
                input_text = prompt_text + masked_input
                input_surface = self.terminal_font.render(input_text, True, COLOR_GREEN)
                input_y = content_y + content_h - line_height
                self.screen.blit(input_surface, (content_x, input_y))
                
                # Draw blinking cursor
                if self.terminal_cursor_visible:
                    cursor_x = content_x + input_surface.get_width()
                    cursor_y = input_y
                    cursor_rect = pygame.Rect(cursor_x, cursor_y, int(2 * self.scale), line_height)
                    pygame.draw.rect(self.screen, COLOR_GREEN, cursor_rect)
                
            elif self.terminal_mode == "file_view":
                # Draw file content with scrolling
                if self.terminal_file_content:
                    # Calculate how many lines can fit
                    max_lines = content_h // line_height
                    start_index = self.terminal_file_scroll_index
                    end_index = min(start_index + max_lines, len(self.terminal_file_content))
                    is_locale_protocols = "LocaleProtocols" in (self.terminal_file_view_filename or "")
                    pulse_color = self._get_terminal_pulse_color(COLOR_GREEN, COLOR_NEON_GREEN, speed=1.5) if is_locale_protocols else COLOR_GREEN
                    
                    y_offset = content_y
                    for i in range(start_index, end_index):
                        if y_offset + line_height > content_y + content_h:
                            break
                        line = self.terminal_file_content[i].rstrip('\n\r')
                        # Wrap long lines
                        wrapped = self._wrap_terminal_text(line, self.terminal_font, content_w)
                        for wrapped_line in wrapped:
                            if y_offset + line_height > content_y + content_h:
                                break
                            if is_locale_protocols:
                                segments = self._segment_line_for_locale_pulse(wrapped_line)
                                x_off = content_x
                                for seg_text, highlight in segments:
                                    if seg_text:
                                        color = self._get_terminal_pulse_color(COLOR_GREEN, COLOR_NEON_GREEN, speed=1.5) if highlight else COLOR_GREEN
                                        surf = self.terminal_font.render(seg_text, True, color)
                                        self.screen.blit(surf, (x_off, y_offset))
                                        x_off += surf.get_width()
                            else:
                                text_surface = self.terminal_font.render(wrapped_line, True, COLOR_GREEN)
                                self.screen.blit(text_surface, (content_x, y_offset))
                            y_offset += line_height
                else:
                    # No file content
                    no_content = self.terminal_font.render("No file content", True, COLOR_GREEN)
                    self.screen.blit(no_content, (content_x, content_y))
            
            else:
                # Command mode - draw prompt and text with wrapping
                prompt_text = self._get_prompt_text()
                
                # Get current input line (last line after last newline)
                lines = self.terminal_text.split('\n')
                current_input = lines[-1] if lines else ""
                previous_lines = '\n'.join(lines[:-1]) if len(lines) > 1 else ""
                
                # Display all previous lines plus current line with prompt
                if previous_lines:
                    text_to_display = previous_lines + "\n" + prompt_text + current_input
                else:
                    text_to_display = prompt_text + current_input
                
                # Wrap text to fit terminal width
                wrapped_lines = []
                for line in text_to_display.split('\n'):
                    if line.strip():
                        wrapped = self._wrap_terminal_text(line, self.terminal_font, content_w)
                        wrapped_lines.extend(wrapped)
                    else:
                        wrapped_lines.append("")
                
                # Calculate text position (start from bottom, scroll up if needed)
                max_lines = content_h // line_height
                display_lines = wrapped_lines[-max_lines:] if len(wrapped_lines) > max_lines else wrapped_lines
                
                # Start from bottom
                y_offset = content_y + content_h - line_height
                
                for line in reversed(display_lines):
                    if y_offset < content_y:
                        break
                    text_surface = self.terminal_font.render(line, True, COLOR_GREEN)
                    self.screen.blit(text_surface, (content_x, y_offset))
                    y_offset -= line_height
                
                # Draw blinking cursor at cursor position on current line
                if self.terminal_cursor_visible:
                    cursor_pos = min(self.terminal_cursor_index, len(current_input))
                    input_before_cursor = prompt_text + current_input[:cursor_pos]
                    cursor_surface = self.terminal_font.render(input_before_cursor, True, COLOR_GREEN)
                    cursor_x = content_x + cursor_surface.get_width()
                    cursor_y = content_y + content_h - line_height
                    cursor_rect = pygame.Rect(cursor_x, cursor_y, int(2 * self.scale), line_height)
                    pygame.draw.rect(self.screen, COLOR_GREEN, cursor_rect)

    def _handle_terminal_click(self, mouse_x: int, mouse_y: int) -> bool:
        """Handle clicks within the terminal window."""
        terminal_w = int(665 * self.scale)  # 33% larger: 500 * 1.33 = 665
        terminal_h = int(375 * self.scale)  # 25% larger: 300 * 1.25 = 375
        
        # Use stored position if available, otherwise center on desktop
        if self.terminal_position:
            terminal_x, terminal_y = self.terminal_position
        else:
            terminal_x = self.desktop_x + (self.desktop_size[0] - terminal_w) // 2
            terminal_y = self.desktop_y + (self.desktop_size[1] - terminal_h) // 2
        
        # Ensure terminal doesn't exceed desktop boundaries
        terminal_x = max(self.desktop_x, min(terminal_x, self.desktop_x + self.desktop_size[0] - terminal_w))
        terminal_y = max(self.desktop_y, min(terminal_y, self.desktop_y + self.desktop_size[1] - terminal_h))
        
        # Check close button first
        close_btn_size = int(20 * self.scale)
        close_btn_rect = pygame.Rect(
            terminal_x + terminal_w - close_btn_size - int(5 * self.scale),
            terminal_y + int(5 * self.scale),
            close_btn_size,
            close_btn_size
        )
        if close_btn_rect.collidepoint(mouse_x, mouse_y):
            self.terminal_active = False
            if "terminal" in self.active_modals:
                self.active_modals.remove("terminal")
            self.terminal_position = None
            self.terminal_dragging = False
            self.terminal_mode = "command"
            self.terminal_text = ""
            self.terminal_cursor_index = 0
            self.terminal_message = ""
            self.terminal_admin_menu_selection = 1
            self.terminal_region_selection = 1
            return True
        
        # Check if clicking on title bar for dragging
        title_bar_height = int(30 * self.scale)
        title_bar_rect = pygame.Rect(
            terminal_x,
            terminal_y,
            terminal_w,
            title_bar_height
        )
        if title_bar_rect.collidepoint(mouse_x, mouse_y):
            # Start dragging the terminal
            self.terminal_dragging = True
            self.terminal_drag_offset = (mouse_x - terminal_x, mouse_y - terminal_y)
            return True
        
        # Clicking anywhere in terminal gives it focus (handled by keyboard input)
        terminal_rect = pygame.Rect(terminal_x, terminal_y, terminal_w, terminal_h)
        return terminal_rect.collidepoint(mouse_x, mouse_y)

    def _get_terminal_rect(self) -> pygame.Rect:
        """Return the terminal window rect (same position/size as drawn). Used for z-order hit-testing."""
        terminal_w = int(665 * self.scale)
        terminal_h = int(375 * self.scale)
        if self.terminal_position:
            terminal_x, terminal_y = self.terminal_position
        else:
            terminal_x = self.desktop_x + (self.desktop_size[0] - terminal_w) // 2
            terminal_y = self.desktop_y + (self.desktop_size[1] - terminal_h) // 2
        terminal_x = max(self.desktop_x, min(terminal_x, self.desktop_x + self.desktop_size[0] - terminal_w))
        terminal_y = max(self.desktop_y, min(terminal_y, self.desktop_y + self.desktop_size[1] - terminal_h))
        return pygame.Rect(terminal_x, terminal_y, terminal_w, terminal_h)

    def _handle_terminal_keydown(self, event: pygame.event.Event) -> bool:
        """Handle keyboard input for the terminal."""
        if not self.terminal_active:
            return False
        
        # Handle message mode (just wait for any key to return to command)
        if self.terminal_mode == "message":
            if event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER or event.key == pygame.K_ESCAPE:
                self.terminal_mode = "command"
                self.terminal_text = ""
                self.terminal_message = ""
                return True
            return True
        
        # Handle region select mode
        if self.terminal_mode == "region_select":
            if event.key == pygame.K_UP:
                self.terminal_region_selection = max(1, self.terminal_region_selection - 1)
                return True
            elif event.key == pygame.K_DOWN:
                self.terminal_region_selection = min(3, self.terminal_region_selection + 1)
                return True
            elif event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:
                # Region selected - save until game restart
                self._switch_os_region(self.terminal_region_selection)
                self.terminal_mode = "message"
                self.terminal_message = "SYSTEM SET TO NEW REGION"
                self.terminal_message_timer = 0.0
                return True
            elif event.key == pygame.K_ESCAPE:
                # Return to admin menu
                self.terminal_mode = "admin_menu"
                return True
            return True
        
        # Handle admin menu mode
        if self.terminal_mode == "admin_menu":
            if event.key == pygame.K_UP:
                self.terminal_admin_menu_selection = max(1, self.terminal_admin_menu_selection - 1)
                return True
            elif event.key == pygame.K_DOWN:
                self.terminal_admin_menu_selection = min(4, self.terminal_admin_menu_selection + 1)
                return True
            elif event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:
                # Menu item selected
                if self.terminal_admin_menu_selection == 1:
                    # Perform Factory Reset - exit game immediately
                    self.exit_game()
                    return True
                elif self.terminal_admin_menu_selection == 2:
                    # Region Detection - show current saved locale as selected
                    self.terminal_mode = "region_select"
                    self.terminal_region_selection = self.os_locale
                    return True
                elif self.terminal_admin_menu_selection == 3:
                    # Handshake Connected Node
                    self.terminal_mode = "message"
                    self.terminal_message = "no node connected"
                    self.terminal_message_timer = 0.0
                    return True
                elif self.terminal_admin_menu_selection == 4:
                    # Shutdown System - show quit screen
                    self.set_quit_state()
                    return True
            elif event.key == pygame.K_ESCAPE:
                # Return to command mode
                self.terminal_mode = "command"
                self.terminal_text = ""
                self.terminal_input_buffer = ""
                return True
            return True
        
        # Handle admin login stages
        if self.terminal_mode == "admin_login_username":
            if event.key == pygame.K_BACKSPACE:
                if self.terminal_input_buffer:
                    self.terminal_input_buffer = self.terminal_input_buffer[:-1]
                    self.terminal_cursor_blink_timer = 0.0
                    self.terminal_cursor_visible = True
                return True
            elif event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:
                if self.terminal_input_buffer.strip().lower() == "general":
                    # Correct username, move to password prompt
                    self.terminal_text += "\nusername: " + self.terminal_input_buffer
                    self.terminal_mode = "admin_login_password"
                    self.terminal_input_buffer = ""
                else:
                    # Wrong username, return to command mode
                    self.terminal_text += "\nusername: " + self.terminal_input_buffer
                    self.terminal_text += "\nAccess denied."
                    self.terminal_mode = "command"
                    self.terminal_input_buffer = ""
                self.terminal_cursor_blink_timer = 0.0
                self.terminal_cursor_visible = True
                return True
            elif event.key == pygame.K_ESCAPE:
                # Cancel login, return to command
                self.terminal_mode = "command"
                self.terminal_input_buffer = ""
                return True
            elif event.unicode and event.unicode.isprintable():
                self.terminal_input_buffer += event.unicode
                self.terminal_cursor_blink_timer = 0.0
                self.terminal_cursor_visible = True
                return True
            return True
        
        if self.terminal_mode == "admin_login_password":
            if event.key == pygame.K_BACKSPACE:
                if self.terminal_input_buffer:
                    self.terminal_input_buffer = self.terminal_input_buffer[:-1]
                    self.terminal_cursor_blink_timer = 0.0
                    self.terminal_cursor_visible = True
                return True
            elif event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:
                if self.terminal_input_buffer.strip().lower() == "louis-sonic":
                    # Correct password, enter admin menu
                    self.terminal_text += "\npassword: " + ("*" * len(self.terminal_input_buffer))
                    self.terminal_text += "\nAccess granted."
                    self.terminal_mode = "admin_menu"
                    self.terminal_admin_menu_selection = 1
                    self.terminal_input_buffer = ""
                else:
                    # Wrong password, return to command mode
                    self.terminal_text += "\npassword: " + ("*" * len(self.terminal_input_buffer))
                    self.terminal_text += "\nAccess denied."
                    self.terminal_mode = "command"
                    self.terminal_input_buffer = ""
                self.terminal_cursor_blink_timer = 0.0
                self.terminal_cursor_visible = True
                return True
            elif event.key == pygame.K_ESCAPE:
                # Cancel login, return to command
                self.terminal_mode = "command"
                self.terminal_input_buffer = ""
                return True
            elif event.unicode and event.unicode.isprintable():
                self.terminal_input_buffer += event.unicode
                self.terminal_cursor_blink_timer = 0.0
                self.terminal_cursor_visible = True
                return True
            return True
        
        # Handle file view mode (scrolling through file content)
        if self.terminal_mode == "file_view":
            if event.key == pygame.K_UP:
                if self.terminal_file_scroll_index > 0:
                    self.terminal_file_scroll_index -= 1
                return True
            elif event.key == pygame.K_DOWN:
                max_scroll = max(0, len(self.terminal_file_content) - 1)
                if self.terminal_file_scroll_index < max_scroll:
                    self.terminal_file_scroll_index += 1
                return True
            elif event.key == pygame.K_ESCAPE:
                # Exit file view, return to file system mode
                self.terminal_mode = "command"
                self.terminal_file_content = []
                self.terminal_file_view_filename = ""
                self.terminal_file_scroll_index = 0
                return True
            return True
        
        # Command mode - normal text input (single line; left/right move cursor on current line only)
        lines = self.terminal_text.split('\n')
        current_line = lines[-1] if lines else ""
        if event.key == pygame.K_LEFT:
            if self.terminal_cursor_index > 0:
                self.terminal_cursor_index -= 1
                self.terminal_cursor_blink_timer = 0.0
                self.terminal_cursor_visible = True
            return True
        elif event.key == pygame.K_RIGHT:
            if self.terminal_cursor_index < len(current_line):
                self.terminal_cursor_index += 1
                self.terminal_cursor_blink_timer = 0.0
                self.terminal_cursor_visible = True
            return True
        elif event.key == pygame.K_UP:
            # MS-DOS style: show previous command from history (stays on main line)
            if self.terminal_command_history:
                if self.terminal_history_index == -1:
                    # First time pressing up - save current input and go to most recent
                    lines = self.terminal_text.split('\n')
                    current_line = lines[-1] if lines else ""
                    # Strip prompt to get actual command
                    if self.terminal_file_system_mode:
                        if self.terminal_file_system_path:
                            path_str = ".\\file-system\\" + "\\".join(self.terminal_file_system_path) + "\\"
                        else:
                            path_str = ".\\file-system\\"
                        if current_line.startswith(path_str):
                            self.terminal_current_input_line = current_line[len(path_str):]
                        else:
                            self.terminal_current_input_line = current_line
                    else:
                        if current_line.startswith("."):
                            self.terminal_current_input_line = current_line[1:]
                        else:
                            self.terminal_current_input_line = current_line
                    self.terminal_history_index = 0
                else:
                    # Move to older command
                    if self.terminal_history_index < len(self.terminal_command_history) - 1:
                        self.terminal_history_index += 1
                
                # Replace current line with history command (cursor at end of line)
                lines = self.terminal_text.split('\n')
                if len(lines) > 0:
                    new_line = self._get_prompt_text() + self.terminal_command_history[self.terminal_history_index]
                    lines[-1] = new_line
                    self.terminal_text = '\n'.join(lines)
                    self.terminal_cursor_index = len(new_line)
                self.terminal_cursor_blink_timer = 0.0
                self.terminal_cursor_visible = True
            return True
        elif event.key == pygame.K_DOWN:
            # MS-DOS style: show next command from history (or clear if at end)
            if self.terminal_history_index != -1:
                if self.terminal_history_index > 0:
                    # Move to newer command
                    self.terminal_history_index -= 1
                    lines = self.terminal_text.split('\n')
                    if len(lines) > 0:
                        new_line = self._get_prompt_text() + self.terminal_command_history[self.terminal_history_index]
                        lines[-1] = new_line
                        self.terminal_text = '\n'.join(lines)
                        self.terminal_cursor_index = len(new_line)
                else:
                    # At the most recent, restore original input (cursor at end)
                    self.terminal_history_index = -1
                    lines = self.terminal_text.split('\n')
                    if len(lines) > 0:
                        new_line = self._get_prompt_text() + self.terminal_current_input_line
                        lines[-1] = new_line
                        self.terminal_text = '\n'.join(lines)
                        self.terminal_cursor_index = len(new_line)
                    self.terminal_current_input_line = ""
                self.terminal_cursor_blink_timer = 0.0
                self.terminal_cursor_visible = True
            return True
        elif event.key == pygame.K_BACKSPACE:
            # Delete char before cursor on current line only (no moving to previous rows)
            if self.terminal_history_index != -1:
                self.terminal_history_index = -1
                self.terminal_current_input_line = ""
            lines = self.terminal_text.split('\n')
            current = lines[-1] if lines else ""
            if self.terminal_cursor_index > 0:
                current = current[:self.terminal_cursor_index - 1] + current[self.terminal_cursor_index:]
                self.terminal_cursor_index -= 1
                self.terminal_text = '\n'.join(lines[:-1] + [current]) if len(lines) > 1 else current
                self.terminal_cursor_blink_timer = 0.0
                self.terminal_cursor_visible = True
            return True
        elif event.key == pygame.K_DELETE:
            # Delete char after cursor on current line only
            if self.terminal_history_index != -1:
                self.terminal_history_index = -1
                self.terminal_current_input_line = ""
            lines = self.terminal_text.split('\n')
            current = lines[-1] if lines else ""
            if self.terminal_cursor_index < len(current):
                current = current[:self.terminal_cursor_index] + current[self.terminal_cursor_index + 1:]
                self.terminal_text = '\n'.join(lines[:-1] + [current]) if len(lines) > 1 else current
                self.terminal_cursor_blink_timer = 0.0
                self.terminal_cursor_visible = True
            return True
        elif event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:
            # Get the current line (last line of terminal_text)
            lines = self.terminal_text.split('\n')
            current_line = lines[-1] if lines else ""
            
            # Strip prompt from current line if in file system mode
            if self.terminal_file_system_mode:
                if self.terminal_file_system_path:
                    path_str = ".\\file-system\\" + "\\".join(self.terminal_file_system_path) + "\\"
                else:
                    path_str = ".\\file-system\\"
                if current_line.startswith(path_str):
                    command = current_line[len(path_str):].strip()
                else:
                    command = current_line.strip()
            else:
                # Remove "." prompt if present
                if current_line.startswith("."):
                    command = current_line[1:].strip()
                else:
                    command = current_line.strip()
            
            # Add command to history (if not empty and not already the last command)
            if command and (not self.terminal_command_history or self.terminal_command_history[0] != command):
                self.terminal_command_history.insert(0, command)
                # Limit history size (keep last 50 commands)
                if len(self.terminal_command_history) > 50:
                    self.terminal_command_history.pop()
            
            # Reset history browsing
            self.terminal_history_index = -1
            self.terminal_current_input_line = ""
            
            # Handle file system commands
            if self.terminal_file_system_mode:
                # Add the command to terminal_text first
                self.terminal_text += "\n"
                
                command_lower = command.lower()
                command_parts = command.split()
                cmd = command_parts[0].lower() if command_parts else ""
                
                if cmd == "dir" or cmd == "ls" or cmd == "":
                    # List directory contents (ls is Unix alias for dir)
                    folders, files = self._list_file_system_directory()
                    for folder in folders:
                        self.terminal_text += f"<DIR> {folder}\n"
                    for file in files:
                        self.terminal_text += f"      {file}\n"
                elif cmd == "cd":
                    # Change directory
                    if len(command_parts) > 1:
                        target = command_parts[1]
                    else:
                        target = ""
                    if target == "\\":
                        # Go back to root
                        self.terminal_file_system_path = []
                    elif target == "..":
                        # Go up one directory
                        if self.terminal_file_system_path:
                            self.terminal_file_system_path.pop()
                    elif target:
                        # Try to navigate to folder (support virtual DOWNLOADS, case-insensitive)
                        current_path = self._get_file_system_path()
                        target_path = os.path.join(current_path, target)
                        if os.path.exists(target_path) and os.path.isdir(target_path):
                            # Normalize to DOWNLOADS for display consistency
                            self.terminal_file_system_path.append("DOWNLOADS" if target.upper() == "DOWNLOADS" else target)
                        elif target.upper() == "DOWNLOADS" and self.os_locale in (1, 2):
                            # Virtual DOWNLOADS folder (US Mainland/Europe)
                            self.terminal_file_system_path.append("DOWNLOADS")
                        else:
                            # Case-insensitive match for physical folders (e.g. DOWNLOADS vs downloads)
                            if os.path.isdir(current_path):
                                matched = next((x for x in os.listdir(current_path) if x.upper() == target.upper()), None)
                                if matched:
                                    self.terminal_file_system_path.append(matched)
                                else:
                                    self.terminal_text += f"Directory not found: {target}\n"
                            else:
                                self.terminal_text += f"Directory not found: {target}\n"
                elif cmd == "cls" or cmd == "clear":
                    # Clear screen
                    self.terminal_text = ""
                elif cmd == "help":
                    # Show help
                    self.terminal_text += "MS-DOS Commands:\n"
                    self.terminal_text += "  DIR / LS     - List directory contents\n"
                    self.terminal_text += "  CD [dir]     - Change directory (CD \\ to root)\n"
                    self.terminal_text += "  TYPE [file]  - Display file contents\n"
                    self.terminal_text += "  CLS          - Clear screen\n"
                    self.terminal_text += "  VER          - Display version\n"
                    self.terminal_text += "  DATE         - Display date\n"
                    self.terminal_text += "  TIME         - Display time\n"
                    self.terminal_text += "  ECHO [text]  - Display text\n"
                    self.terminal_text += "  EXIT         - Exit file system mode\n"
                    self.terminal_text += "  COMMAND-SYSTEM-START - Exit file system mode\n"
                    self.terminal_text += "  HELP         - Display this help\n"
                elif cmd == "ver":
                    # Show version
                    self.terminal_text += "Bradsonic 69000 Terminal v1.0\n"
                    self.terminal_text += "Copyright (C) 2024 Bradsonic Systems\n"
                elif cmd == "date":
                    # Show date (game year is always 1989)
                    now = datetime.now()
                    game_date = now.replace(year=1989)
                    self.terminal_text += f"Current date: {game_date.strftime('%a %m/%d/%Y')}\n"
                elif cmd == "time":
                    # Show time
                    now = datetime.now()
                    self.terminal_text += f"Current time: {now.strftime('%H:%M:%S')}\n"
                elif cmd == "echo":
                    # Echo text
                    if len(command_parts) > 1:
                        echo_text = " ".join(command_parts[1:])
                        self.terminal_text += f"{echo_text}\n"
                    else:
                        self.terminal_text += "\n"
                elif cmd == "type":
                    # Display file contents (support filenames with spaces e.g. "Pacifica Sunrise.sonic")
                    if len(command_parts) > 1:
                        filename = " ".join(command_parts[1:])
                        if self._open_file_in_terminal(filename):
                            self.terminal_text += f"Contents of {filename}:\n"
                            # File will be displayed in file_view mode
                        else:
                            self.terminal_text += f"File not found: {filename}\n"
                    else:
                        self.terminal_text += "Required parameter missing.\n"
                elif cmd == "command-system-start" or cmd == "exit":
                    # Exit file system mode, return to command mode
                    self.terminal_file_system_mode = False
                    self.terminal_file_system_path = []
                    self.terminal_text += "Exiting file system mode...\n"
                elif cmd == "md" or cmd == "mkdir":
                    # Make directory (read-only file system)
                    self.terminal_text += "File system is read-only. Cannot create directory.\n"
                elif cmd == "rd" or cmd == "rmdir":
                    # Remove directory (read-only file system)
                    self.terminal_text += "File system is read-only. Cannot remove directory.\n"
                elif cmd == "del" or cmd == "erase":
                    # Delete file (read-only file system)
                    self.terminal_text += "File system is read-only. Cannot delete file.\n"
                elif cmd == "copy":
                    # Copy file (read-only file system)
                    self.terminal_text += "File system is read-only. Cannot copy file.\n"
                elif cmd == "ren" or cmd == "rename":
                    # Rename file (read-only file system)
                    self.terminal_text += "File system is read-only. Cannot rename file.\n"
                elif command:
                    # Try to open as file or folder (case-insensitive for folders, e.g. DOWNLOADS)
                    folders, files = self._list_file_system_directory()
                    folder_match = next((f for f in folders if f.upper() == command.upper()), None)
                    if folder_match:
                        # It's a folder, navigate into it (use canonical name DOWNLOADS)
                        self.terminal_file_system_path.append("DOWNLOADS" if folder_match.upper() == "DOWNLOADS" else folder_match)
                    elif command in files or (files and next((f for f in files if f.upper() == command.upper()), None)):
                        # It's a file, open it (support case-insensitive match)
                        file_to_open = next((f for f in files if f.upper() == command.upper()), command) if command not in files else command
                        if self._open_file_in_terminal(file_to_open):
                            self.terminal_text += f"Opening {file_to_open}...\n"
                        else:
                            self.terminal_text += f"Error opening file: {file_to_open}\n"
                    else:
                        # Unknown command
                        self.terminal_text += f"Bad command or file name: {command}\n"
            else:
                # Not in file system mode - check for commands
                command_lower = command.lower()
                if command_lower == "admin-subset":
                    # Start admin login sequence
                    self.terminal_text += "\n"
                    self.terminal_mode = "admin_login_username"
                    self.terminal_input_buffer = ""
                elif command_lower == "file-system-start":
                    # Enter file system mode
                    self.terminal_file_system_mode = True
                    self.terminal_file_system_path = []
                    self.terminal_text += "\n"
                else:
                    self.terminal_text += "\n"
            
            self.terminal_cursor_index = 0  # New line: cursor at start
            self.terminal_cursor_blink_timer = 0.0
            self.terminal_cursor_visible = True
            return True
        elif event.key == pygame.K_ESCAPE:
            # ESC in command mode: if in file-system go back to "."; otherwise close terminal (never exit OS/BBS)
            if self.terminal_file_system_mode:
                self.terminal_file_system_mode = False
                self.terminal_file_system_path = []
                self.terminal_file_content = []
                self.terminal_file_view_filename = ""
                self.terminal_file_scroll_index = 0
                self.terminal_text += "\n."
                self.terminal_input_buffer = ""
                self.terminal_cursor_index = 0
                return True
            # At "." (terminal start): close terminal window only, stay in OS mode
            self.terminal_active = False
            if "terminal" in self.active_modals:
                self.active_modals.remove("terminal")
            self.terminal_position = None
            self.terminal_dragging = False
            self.terminal_mode = "command"
            self.terminal_text = ""
            self.terminal_input_buffer = ""
            self.terminal_cursor_index = 0
            self.terminal_message = ""
            self.terminal_admin_menu_selection = 1
            self.terminal_region_selection = 1
            self.terminal_file_system_mode = False
            self.terminal_file_system_path = []
            self.terminal_file_content = []
            self.terminal_file_view_filename = ""
            self.terminal_file_scroll_index = 0
            return True
        elif event.unicode and event.unicode.isprintable():
            # Insert character at cursor on current line only
            if self.terminal_history_index != -1:
                self.terminal_history_index = -1
                self.terminal_current_input_line = ""
            lines = self.terminal_text.split('\n')
            current = lines[-1] if lines else ""
            current = current[:self.terminal_cursor_index] + event.unicode + current[self.terminal_cursor_index:]
            self.terminal_cursor_index += 1
            self.terminal_text = '\n'.join(lines[:-1] + [current]) if len(lines) > 1 else current
            self.terminal_cursor_blink_timer = 0.0
            self.terminal_cursor_visible = True
            return True
        
        return False

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
        """Generate mission note content dynamically based on player tokens."""
        # Check if player has tokens
        has_radio_access1 = self.has_token("RADIO_ACCESS1")
        has_jax1 = self.has_token("JAX1")
        has_papercranebbs = self.has_token("PAPERCRANEBBS")
        has_echochamber = self.has_token("ECHOCHAMBER")
        
        # Build content dynamically
        content = (
            "[s]1. Receive Invite from Glyphis[/s]\n"
            "[s]2. Get onto the BBS (0345728891)[/s]\n"
            "[s]3. Complete a technical challenge to prove yourself[/s]\n"
            "4. Get the audio tech's help and get the first audio stream from Glyphisis_IO. Record it using the Datasette!\n"
        )
        
        # Item 5: Strike through if player has JAX1
        if has_jax1:
            content += "[s]5. Get invited to crack some games[/s]\n"
        else:
            content += "5. Get invited to crack some games\n"
        
        # Item 6: Strike through if player has RADIO_ACCESS1
        if has_radio_access1:
            content += "[s]6. Obtain access to the group's Pirate Radio Stream![/s]\n"
        else:
            content += "6. Obtain access to the group's Pirate Radio Stream!\n"
        
        # Item 7: Strike through if player has both PAPERCRANEBBS and ECHOCHAMBER tokens
        if has_papercranebbs and has_echochamber:
            content += "[s]7. Observe the Underground Radio Scene and get numbers for OTHER BBS sites.[/s]\n"
        else:
            content += "7. Observe the Underground Radio Scene and get numbers for OTHER BBS sites.\n"
        
        content += "8. Dial into at least 3 more BBS sites.\n"
        content += "9. Crack games, play them and attempt to dominate the leaderboards\n"
        
        return {
            "title": MISSION_NOTE_TITLE,
            "content": content,
            "is_locked": True
        }
    
    def _get_bbs_login_note_content(self):
        """Generate BBS login note content with current user credentials and PAPER CRANE BBS if token exists."""
        username, pin = self.get_user_credentials()
        content = f"{BBS_NAME}\n"
        content += f"Dial-in: (03) 45 72 88 91\n"
        content += f"Username: {username if username else 'Not Set'}\n"
        content += f"Login PIN: {pin if pin else 'Not Set'}"
        
        # Add PAPER CRANE BBS info if player has PAPERCRANEBBS token
        if self.has_token("PAPERCRANEBBS"):
            content += f"\n\nPAPER CRANE BBS\n"
            content += f"Dial-in: (082) 77 34 19 45\n"
            content += f"Username: guest\n"
            content += f"Password: origami"
        
        # Add ECHO CHAMBER BBS info if player has ECHOCHAMBER token
        if self.has_token("ECHOCHAMBER"):
            content += f"\n\nECHO CHAMBER BBS\n"
            content += f"Dial-in: (07) 57 42 19 89"
        
        # Add NEVER AGAIN BBS info if player has NEVERAGAINBBS token
        if self.has_token("NEVERAGAINBBS"):
            content += f"\n\nNEVER AGAIN BBS\n"
            content += f"Dial-in: (034) 089 98 91"
        
        return content
    
    def _bbs_login_note_template(self):
        """Generate BBS login note with current user credentials."""
        content = self._get_bbs_login_note_content()
        return {
            "title": BBS_LOGIN_NOTE_TITLE,
            "content": content,
            "is_locked": True
        }

    def _load_user_notes(self) -> List[Dict]:
        """Load notes from user profile and ensure mission note and BBS login note exist."""
        notes = self.get_notes() or []
        mission_note = self._mission_note_template()
        bbs_login_note = self._bbs_login_note_template()
        changed = False

        if not notes:
            # No notes at all - create both permanent notes
            notes = [mission_note, bbs_login_note]
            changed = True
        else:
            # Ensure Mission Objectives is first
            mission_note_index = None
            bbs_login_note_index = None
            
            for i, note in enumerate(notes):
                if note.get("is_locked", False):
                    if note.get("title") == MISSION_NOTE_TITLE:
                        mission_note_index = i
                    elif note.get("title") == BBS_LOGIN_NOTE_TITLE:
                        bbs_login_note_index = i
            
            # Collect all non-locked notes
            other_notes = [note for note in notes if not note.get("is_locked", False)]
            
            # Ensure Mission Objectives exists and is first
            if mission_note_index is None:
                # Mission note is missing - add it first
                if notes and notes[0].get("is_locked", False) and notes[0].get("title") == BBS_LOGIN_NOTE_TITLE:
                    # BBS login note is first, swap them
                    notes = [mission_note, bbs_login_note] + other_notes
                else:
                    notes = [mission_note] + ([bbs_login_note] if bbs_login_note_index is None else []) + other_notes
                changed = True
            elif mission_note_index != 0:
                # Mission note exists but is not first - move it to first
                existing_mission = notes[mission_note_index]
                remaining_notes = [n for i, n in enumerate(notes) if i != mission_note_index]
                notes = [existing_mission] + remaining_notes
                changed = True
            else:
                # Mission note is first - ensure BBS login note is second
                if bbs_login_note_index is None:
                    # BBS login note is missing - add it second
                    notes = [notes[0], bbs_login_note] + other_notes
                    changed = True
                elif bbs_login_note_index != 1:
                    # BBS login note exists but is not second - move it to second
                    existing_bbs_login = notes[bbs_login_note_index]
                    remaining_notes = [notes[0]] + [n for i, n in enumerate(notes) if i not in (0, bbs_login_note_index)]
                    notes = [notes[0], existing_bbs_login] + remaining_notes
                    changed = True
                else:
                    # Both permanent notes are in correct positions
                    # Update BBS login note content with current credentials (it may have changed)
                    if notes[1].get("title") == BBS_LOGIN_NOTE_TITLE:
                        # Update content to reflect current credentials
                        updated_content = self._get_bbs_login_note_content()
                        if notes[1].get("content") != updated_content:
                            notes[1]["content"] = updated_content
                            changed = True
                    
                    # Ensure mission note has correct title and is_locked
                    if notes[0].get("title") != mission_note["title"]:
                        notes[0]["title"] = mission_note["title"]
                        changed = True
                    if not notes[0].get("is_locked", False):
                        notes[0]["is_locked"] = True
                        changed = True
                    
                    # Ensure BBS login note has correct title and is_locked
                    if notes[1].get("title") != bbs_login_note["title"]:
                        notes[1]["title"] = bbs_login_note["title"]
                        changed = True
                    if not notes[1].get("is_locked", False):
                        notes[1]["is_locked"] = True
                        changed = True
                    
                    # Update mission note content if token status has changed (for items 5-9)
                    # Check if tokens require content update
                    has_radio_access1 = self.has_token("RADIO_ACCESS1")
                    has_jax1 = self.has_token("JAX1")
                    has_papercranebbs = self.has_token("PAPERCRANEBBS")
                    has_echochamber = self.has_token("ECHOCHAMBER")
                    existing_content = notes[0].get("content", "")
                    
                    # Check if item 5 needs to be updated (strike through if JAX1 present)
                    item_5_struck = "[s]5. Get invited to crack some games[/s]" in existing_content
                    item_5_unstruck = "5. Get invited to crack some games" in existing_content and not item_5_struck
                    
                    # Check if item 6 needs to be updated (strike through if token present)
                    item_6_struck = "[s]6. Obtain access to the group's Pirate Radio Stream![/s]" in existing_content
                    item_6_unstruck = "6. Obtain access to the group's Pirate Radio Stream!" in existing_content and not item_6_struck
                    
                    # Check if item 7 needs to be updated (strike through if both PAPERCRANEBBS and ECHOCHAMBER present)
                    item_7_struck = "[s]7. Observe the Underground Radio Scene" in existing_content
                    item_7_unstruck = "7. Observe the Underground Radio Scene" in existing_content and not item_7_struck
                    
                    # Check if items 7-9 exist
                    has_item_7 = "7. Observe the Underground Radio Scene" in existing_content
                    has_item_8 = "8. Dial into at least 3 more BBS sites" in existing_content
                    has_item_9 = "9. Crack games, play them and attempt to dominate the leaderboards" in existing_content
                    
                    # Update content if needed
                    needs_update = False
                    updated_content = existing_content
                    
                    # Update item 5 strike-through status if token status changed
                    if has_jax1 and item_5_unstruck:
                        # Need to strike through item 5
                        updated_content = updated_content.replace(
                            "5. Get invited to crack some games\n",
                            "[s]5. Get invited to crack some games[/s]\n"
                        )
                        needs_update = True
                    elif not has_jax1 and item_5_struck:
                        # Need to remove strike-through from item 5
                        updated_content = updated_content.replace(
                            "[s]5. Get invited to crack some games[/s]\n",
                            "5. Get invited to crack some games\n"
                        )
                        needs_update = True
                    
                    # Update item 6 strike-through status if token status changed
                    if has_radio_access1 and item_6_unstruck:
                        # Need to strike through item 6
                        updated_content = updated_content.replace(
                            "6. Obtain access to the group's Pirate Radio Stream!\n",
                            "[s]6. Obtain access to the group's Pirate Radio Stream![/s]\n"
                        )
                        needs_update = True
                    elif not has_radio_access1 and item_6_struck:
                        # Need to remove strike-through from item 6
                        updated_content = updated_content.replace(
                            "[s]6. Obtain access to the group's Pirate Radio Stream![/s]\n",
                            "6. Obtain access to the group's Pirate Radio Stream!\n"
                        )
                        needs_update = True
                    
                    # Update item 7 strike-through status if token status changed
                    if has_papercranebbs and has_echochamber and item_7_unstruck:
                        # Need to strike through item 7
                        updated_content = updated_content.replace(
                            "7. Observe the Underground Radio Scene and get numbers for OTHER BBS sites.\n",
                            "[s]7. Observe the Underground Radio Scene and get numbers for OTHER BBS sites.[/s]\n"
                        )
                        needs_update = True
                    elif not (has_papercranebbs and has_echochamber) and item_7_struck:
                        # Need to remove strike-through from item 7
                        updated_content = updated_content.replace(
                            "[s]7. Observe the Underground Radio Scene and get numbers for OTHER BBS sites.[/s]\n",
                            "7. Observe the Underground Radio Scene and get numbers for OTHER BBS sites.\n"
                        )
                        needs_update = True
                    
                    # Add items 7-9 if they don't exist
                    if not has_item_7 or not has_item_8 or not has_item_9:
                        # Remove any existing items 7-9 to avoid duplicates
                        lines = updated_content.split('\n')
                        filtered_lines = []
                        for line in lines:
                            if not (line.strip().startswith("7. ") or 
                                   line.strip().startswith("[s]7. ") or
                                   line.strip().startswith("8. ") or 
                                   line.strip().startswith("[s]8. ") or
                                   line.strip().startswith("9. ") or 
                                   line.strip().startswith("[s]9. ")):
                                filtered_lines.append(line)
                        
                        # Add items 7-9 at the end
                        updated_content = '\n'.join(filtered_lines)
                        if updated_content and not updated_content.endswith('\n'):
                            updated_content += '\n'
                        # Item 7: Strike through if player has both PAPERCRANEBBS and ECHOCHAMBER tokens
                        if has_papercranebbs and has_echochamber:
                            updated_content += "[s]7. Observe the Underground Radio Scene and get numbers for OTHER BBS sites.[/s]\n"
                        else:
                            updated_content += "7. Observe the Underground Radio Scene and get numbers for OTHER BBS sites.\n"
                        updated_content += "8. Dial into at least 3 more BBS sites.\n"
                        updated_content += "9. Crack games, play them and attempt to dominate the leaderboards\n"
                        needs_update = True
                    
                    if needs_update:
                        notes[0]["content"] = updated_content
                        changed = True

        # Enforce max of 10 notes
        if len(notes) > 10:
            notes = notes[:10]
            changed = True

        if changed:
            self.save_notes(notes)

        return notes

    def _save_user_notes(self, notes: List[Dict]) -> None:
        """Persist notes back to user profile, ensuring mission note is first and BBS login note is second."""
        sanitized: List[Dict] = []
        
        # Find existing permanent notes to preserve their content
        existing_mission_note = None
        existing_bbs_login_note = None
        for note in notes:
            if note.get("is_locked", False):
                if note.get("title") == MISSION_NOTE_TITLE:
                    existing_mission_note = note
                elif note.get("title") == BBS_LOGIN_NOTE_TITLE:
                    existing_bbs_login_note = note
        
        # Use existing mission note if found, otherwise use template
        if existing_mission_note:
            sanitized.append({
                "title": existing_mission_note.get("title", MISSION_NOTE_TITLE),
                "content": existing_mission_note.get("content", MISSION_NOTE_CONTENT),
                "is_locked": True
            })
        else:
            # No existing mission note, use template
            mission_note = self._mission_note_template()
            sanitized.append(mission_note)
        
        # Use existing BBS login note if found, otherwise create new one with current credentials
        if existing_bbs_login_note:
            # Update content with current credentials (they may have changed)
            updated_content = self._get_bbs_login_note_content()
            sanitized.append({
                "title": existing_bbs_login_note.get("title", BBS_LOGIN_NOTE_TITLE),
                "content": updated_content,
                "is_locked": True
            })
        else:
            # No existing BBS login note, create new one
            bbs_login_note = self._bbs_login_note_template()
            sanitized.append(bbs_login_note)

        # Add all non-locked notes
        for note in notes:
            if note.get("is_locked", False):
                continue  # Skip locked notes (already handled above)

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
        self.notes_modal_edit_title_text = (note.get("title", "Untitled").strip() or "Untitled")[:NOTESTAB_TITLE_MAX_LEN]
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
                    note["title"] = (self.notes_modal_edit_title_text.strip() or "Untitled")[:NOTESTAB_TITLE_MAX_LEN]
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
        # Reset scroll when exiting edit mode
        self.notes_modal_view_scroll = 0

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

    def _notes_handle_view_scroll(self, event: pygame.event.Event) -> bool:
        """Handle scrolling in notes view mode (when not editing)."""
        if self.notes_modal_edit_mode:
            return False
        
        if event.key in (pygame.K_UP, pygame.K_w):
            self.notes_modal_view_scroll = max(0, self.notes_modal_view_scroll - 1)
            return True
        if event.key in (pygame.K_DOWN, pygame.K_s):
            self.notes_modal_view_scroll += 1
            return True
        if event.key == pygame.K_PAGEUP:
            self.notes_modal_view_scroll = max(0, self.notes_modal_view_scroll - 5)
            return True
        if event.key == pygame.K_PAGEDOWN:
            self.notes_modal_view_scroll += 5
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
        if self.notes_modal_edit_field == "title":
            # Tab title 20-char limit
            new_text = text[:cursor] + text_input + text[cursor:]
            new_text = new_text[:NOTESTAB_TITLE_MAX_LEN]
            cursor = min(cursor + len(text_input), len(new_text))
            self._notes_set_active_text(new_text, cursor)
        else:
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

    def _rich_text_to_lines(self, text: str, body_font: pygame.font.Font, bold_font: pygame.font.Font, 
                            max_width: int) -> List[Dict[str, Any]]:
        """Convert rich text into a list of line dictionaries for scrolling."""
        lines: List[Dict[str, Any]] = []
        line_height = body_font.get_height() + int(4 * self.scale)
        
        for paragraph in text.split("\n"):
            if not paragraph.strip():
                # Empty line
                lines.append({
                    "segments": [],
                    "line_height": line_height
                })
                continue
                
            segments = self._parse_markup_segments(paragraph)
            current_line_segments: List[Dict[str, Any]] = []
            x = 0
            
            for segment in segments:
                segment_text = segment["text"]
                seg_font = bold_font if segment["bold"] else body_font
                
                while segment_text:
                    remaining_width = max_width - x
                    if remaining_width <= 0:
                        # Start new line
                        if current_line_segments:
                            lines.append({
                                "segments": current_line_segments.copy(),
                                "line_height": line_height
                            })
                        current_line_segments = []
                        x = 0
                        remaining_width = max_width
                    
                    fit_chars = self._measure_text_fit(seg_font, segment_text, remaining_width)
                    if fit_chars <= 0:
                        # Word doesn't fit, start new line
                        if current_line_segments:
                            lines.append({
                                "segments": current_line_segments.copy(),
                                "line_height": line_height
                            })
                        current_line_segments = []
                        x = 0
                        continue
                    
                    chunk = segment_text[:fit_chars]
                    segment_text = segment_text[fit_chars:]
                    
                    # Measure chunk width
                    chunk_surface = seg_font.render(chunk, True, COLOR_WHITE)
                    chunk_width = chunk_surface.get_width()
                    
                    current_line_segments.append({
                        "text": chunk,
                        "font": seg_font,
                        "bold": segment["bold"],
                        "strike": segment["strike"],
                        "highlight": segment["highlight"],
                        "x": x,
                        "width": chunk_width
                    })
                    
                    x += chunk_width
                    
                    if segment_text:
                        # Start new line for remaining text
                        if current_line_segments:
                            lines.append({
                                "segments": current_line_segments.copy(),
                                "line_height": line_height
                            })
                        current_line_segments = []
                        x = 0
            
            # Add final line for this paragraph
            if current_line_segments:
                lines.append({
                    "segments": current_line_segments.copy(),
                    "line_height": line_height
                })
        
        return lines

    def _draw_scroll_indicator(self, surface: pygame.Surface, rect: pygame.Rect, 
                               start_line: int, visible_lines: int, total_lines: int) -> None:
        """Draw a scroll indicator with pink scroll bar."""
        if total_lines <= visible_lines:
            return
        
        # Calculate bar geometry
        max_scroll = total_lines - visible_lines
        scroll_pct = start_line / max_scroll if max_scroll > 0 else 0
        
        bar_w = int(4 * self.scale)
        bar_h = int(30 * self.scale)
        
        track_h = rect.height - int(20 * self.scale)
        available_track = track_h - bar_h
        
        bar_x = rect.right - bar_w - int(4 * self.scale)
        bar_y = rect.y + int(10 * self.scale) + int(scroll_pct * available_track)
        
        # Pink color (Hot Pink similar to PaperCraneBBS)
        COLOR_PINK = (255, 105, 180)
        
        # Draw the handle (pink scroll bar)
        pygame.draw.rect(surface, COLOR_PINK, (bar_x, bar_y, bar_w, bar_h), 0, border_radius=2)
        
        # Optional: draw a very faint track line
        track_surf = pygame.Surface((1, track_h), pygame.SRCALPHA)
        pygame.draw.line(track_surf, (COLOR_PINK[0], COLOR_PINK[1], COLOR_PINK[2], 40), 
                         (0, 0), (0, track_h), 1)
        surface.blit(track_surf, (bar_x + bar_w // 2, rect.y + int(10 * self.scale)))

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
        
        # Double-check: never delete index 0 (mission note) or index 1 (BBS login note)
        if index == 0:
            return  # Mission note is always protected
        if index == 1:
            return  # BBS login note is always protected
        
        del notes[index]
        self._save_user_notes(notes)
        self.notes_modal_edit_mode = False
        self.notes_modal_edit_index = None
        self.notes_modal_current_tab = min(self.notes_modal_current_tab, len(notes) - 1)

    def _draw_note_view(self, note: Dict, content_area_rect: pygame.Rect, modal_x: int, modal_y: int, modal_w: int) -> None:
        """Draw note content in view mode (not editing) with scrolling support."""
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
        title_height = title_surface.get_height() + gap
        text_y += title_height

        # Calculate available space for content (accounting for title and button panel)
        button_panel_height = int(45 * self.scale) if not note.get("is_locked", False) else 0
        available_width = content_area_rect.width - gap * 2 - int(10 * self.scale)  # Extra space for scrollbar
        content_start_y = text_y
        content_available_height = content_area_rect.bottom - content_start_y - button_panel_height - gap
        
        try:
            bold_font = pygame.font.SysFont("Segoe Script", body_font_size, bold=True)
        except Exception:
            bold_font = pygame.font.Font(None, body_font_size)
            bold_font.set_bold(True)

        # Convert rich text to lines
        note_content = self._resolve_note_tokens(note.get("content", ""))
        all_lines = self._rich_text_to_lines(note_content, body_font, bold_font, available_width)
        
        if not all_lines:
            # Empty note
            return
        
        # Calculate visible lines
        line_height = all_lines[0]["line_height"] if all_lines else (body_font.get_height() + int(4 * self.scale))
        visible_lines = max(1, content_available_height // line_height)
        
        # Clamp scroll position
        max_scroll = max(0, len(all_lines) - visible_lines)
        self.notes_modal_view_scroll = max(0, min(self.notes_modal_view_scroll, max_scroll))
        
        # Draw visible lines
        start_line = self.notes_modal_view_scroll
        end_line = start_line + visible_lines
        current_y = content_start_y
        
        for line_idx in range(start_line, min(end_line, len(all_lines))):
            line_data = all_lines[line_idx]
            for segment in line_data["segments"]:
                # Render text segment
                text_surface = segment["font"].render(segment["text"], True, COLOR_WHITE)
                
                # Draw highlight if needed
                if segment["highlight"]:
                    highlight_rect = pygame.Rect(
                        text_x + segment["x"],
                        current_y,
                        segment["width"],
                        line_data["line_height"]
                    )
                    highlight_rect.inflate_ip(4, 4)
                    highlight_surf = pygame.Surface(highlight_rect.size, pygame.SRCALPHA)
                    highlight_surf.fill((255, 255, 0, 90))
                    self.screen.blit(highlight_surf, highlight_rect.topleft)
                
                # Draw text
                self.screen.blit(text_surface, (text_x + segment["x"], current_y))
                
                # Draw strikethrough if needed
                if segment["strike"]:
                    line_y = current_y + text_surface.get_height() // 2
                    pygame.draw.line(
                        self.screen,
                        COLOR_WHITE,
                        (text_x + segment["x"], line_y),
                        (text_x + segment["x"] + segment["width"], line_y),
                        2
                    )
            
            current_y += line_data["line_height"]
        
        # Draw scroll indicator
        content_rect = pygame.Rect(
            content_area_rect.x + gap,
            content_start_y,
            content_area_rect.width - gap * 2,
            content_available_height
        )
        self._draw_scroll_indicator(self.screen, content_rect, start_line, visible_lines, len(all_lines))

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

        # Cache fonts by scale to avoid recreating every frame (major FPS fix when notes modal is open)
        if getattr(self, "_notes_editor_font_scale", None) != self.scale:
            title_font_size = max(int(20 * self.scale), 14)
            body_font_size = max(int(16 * self.scale), 12)
            try:
                self._notes_editor_title_font = pygame.font.SysFont("Segoe Script", title_font_size)
            except Exception:
                self._notes_editor_title_font = pygame.font.Font(None, title_font_size)
            try:
                self._notes_editor_body_font = pygame.font.SysFont("Segoe Script", body_font_size)
            except Exception:
                self._notes_editor_body_font = pygame.font.Font(None, body_font_size)
            try:
                self._notes_editor_fmt_font = pygame.font.Font(None, max(int(18 * self.scale), 12))
            except Exception:
                self._notes_editor_fmt_font = pygame.font.Font(None, 18)
            self._notes_editor_font_scale = self.scale
        title_font = self._notes_editor_title_font
        body_font = self._notes_editor_body_font
        fmt_font = self._notes_editor_fmt_font

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
    
    def _close_modal(self, modal_name: str):
        """Close a specific modal and perform necessary cleanup."""
        if modal_name not in self.active_modals:
            return
        
        if modal_name == "file_system_browser":
            self.file_system_browser_opened_from_dot_sonic = False
            self.file_system_browser_dragging_item = None
        
        # Remove modal from active list
        self.active_modals = [name for name in self.active_modals if name != modal_name]
        
        # Remove modal position
        if modal_name in self.modal_positions:
            del self.modal_positions[modal_name]
        
        # Stop dragging if this modal was being dragged
        if self.modal_dragging == modal_name:
            self.modal_dragging = None
            self.modal_drag_offset = (0, 0)
        
        # Modal-specific cleanup
        if modal_name == "tape":
            # Stop video if modal is closed (but keep recording flag)
            is_recording, _ = self.get_recording_state()
            if not is_recording:
                self._stop_tape_video()
        elif modal_name == "modem":
            # Don't reset modem state when closing - allow reconnection
            # Just stop any active dial sound
            self._stop_modem_dial_sound()
        elif modal_name == "notes":
            # Exit edit mode if active
            if self.notes_modal_edit_mode:
                self._exit_notes_edit_mode(save_changes=False)
        elif modal_name == "mail":
            # Reset compose state when closing
            if self.mail_view == "compose":
                self.mail_compose_to = ""
                self.mail_compose_subject = ""
                self.mail_compose_body = ""
                self.mail_compose_active_field = "to"
            self.mail_view = "inbox"
            self.mail_reading_email = None
            self.mail_settings_active_field = None
        elif modal_name == "dot_sonic":
            if self.dot_sonic_app and self.dot_sonic_app.active:
                self.dot_sonic_app.close()
        # Other modals don't need special cleanup
    
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
        self.modem_modal_cursor_position = 0
        self.modem_modal_cursor_blink_timer = 0.0
        self.modem_modal_connection_messages = []
        self.modem_modal_message_index = 0
        self.modem_modal_message_timer = 0.0
        self.modem_modal_connection_started = False
        self.modem_modal_current_target = None
        self.modem_modal_external_bbs = None
        self.modem_modal_should_reset_bbs = False
        self.modem_modal_should_exit_os = False
        self.modem_terminal_rect = None
        self.modem_packet_sprites.clear()
        self.modem_wave_phase = 0.0
        self.modem_packet_spawn_timer = 0.0
        # Preserve network state unless explicitly disconnected
        self.network_connected = OSMode.persisted_network_connected
        self.modem_modal_error_message = ""
        
        # Reset BRADSONIC-MAIL state
        self.mail_view = "inbox"
        self.mail_selected_index = -1
        self.mail_reading_email = None
        self.mail_compose_to = ""
        self.mail_compose_subject = ""
        self.mail_compose_body = ""
        self.mail_compose_active_field = "to"
        self.mail_compose_cursor = 0
        self.mail_scroll_offset = 0
        self.mail_status_message = ""
        self.mail_status_timer = 0.0
        self.mail_settings_active_field = None
        self.mail_settings_cursor = 0
        self.mail_settings_scroll = 0
        self.mail_local_inbox = []
        self.modem_modal_error_timer = 0.0
        self._stop_modem_dial_sound()
        
        # Reset icon states and restore positions from saved file (or defaults if none saved)
        saved_positions = self._load_icon_positions()
        current_y = self.desktop_y + int(70 * self.scale)  # Start 70px down from desktop top
        icon_spacing = int(10 * self.scale)
        
        for icon in self.icons:
            # Restore from saved position if available, otherwise use default stacked position
            icon["from_saved"] = icon["name"] in saved_positions
            if icon["from_saved"]:
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
        self._apply_desktop_icon_vertical_offsets()
        
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
        # Close snooker game if active
        if self.snooker_game and self.snooker_game.active:
            self.snooker_game.close()
        # Close mahjong game if active
        if self.mahjong_game and self.mahjong_game.active:
            self.mahjong_game.close()
        # Close civitas game if active
        if self.civitas_game and self.civitas_game.active:
            self.civitas_game.close()
    
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

        # Update snooker game desktop coordinates and scale
        if self.snooker_game:
            health_monitor_y = self.bbs_y + int(10 * self.scale) if self.bbs_y else self.desktop_y + int(10 * self.scale)
            self.snooker_game.update_desktop(self.desktop_x, self.desktop_y, self.desktop_size, health_monitor_y)
            self.snooker_game.scale = self.scale
            # Update fonts after scale is set
            self.snooker_game._update_fonts()

        # Update mahjong game desktop coordinates and scale
        if self.mahjong_game:
            health_monitor_y = self.bbs_y + int(10 * self.scale) if self.bbs_y else self.desktop_y + int(10 * self.scale)
            self.mahjong_game.update_desktop(self.desktop_x, self.desktop_y, self.desktop_size, health_monitor_y)
            self.mahjong_game.scale = self.scale
            if self.mahjong_game.active:
                try:
                    self.mahjong_game._load_assets()
                except Exception as e:
                    print(f"Warning: Failed to reload mahjong assets: {e}")

        # Update civitas game desktop coordinates and scale
        if self.civitas_game:
            health_monitor_y = self.bbs_y + int(10 * self.scale) if self.bbs_y else self.desktop_y + int(10 * self.scale)
            self.civitas_game.update_desktop(self.desktop_x, self.desktop_y, self.desktop_size, health_monitor_y)
            self.civitas_game.scale = self.scale
            if self.civitas_game.active:
                try:
                    self.civitas_game._load_assets()
                except Exception as e:
                    print(f"Warning: Failed to reload civitas assets: {e}")
        
        # Update dotSONIC Media Player
        if self.dot_sonic_app:
            health_monitor_y = self.bbs_y + int(10 * self.scale) if self.bbs_y else self.desktop_y + int(10 * self.scale)
            self.dot_sonic_app.update_desktop(self.desktop_x, self.desktop_y, self.desktop_size, health_monitor_y)
            self.dot_sonic_app.scale = self.scale
    
    def _update_hover_states(self, mouse_x: int, mouse_y: int):
        """Update hover states for icons and buttons based on mouse position."""
        # Reset hover states
        self.hovered_icon = None
        self.hovered_button = None
        
        # Check icon hovers (only if not dragging)
        if not self.mouse_pressed:
            for icon in self.icons:
                if icon["name"] == "mail-icon.png" and self.os_locale != 1:
                    continue
                if icon["name"] == "sonic-icon.png" and self.os_locale == 3:
                    continue
                icon_rect = pygame.Rect(icon["x"], icon["y"], icon["width"], icon["height"])
                if icon_rect.collidepoint(mouse_x, mouse_y):
                    self.hovered_icon = icon
                    break
        
        # Check button hovers in modals (check top-most first)
        for modal_name in reversed(self.active_modals.copy()):
            if modal_name == "dot_sonic":
                continue  # dotSONIC has its own UI/hover handling
            modal_x, modal_y = self.modal_positions.get(modal_name, (0, 0))
            modal_w, modal_h = self._get_modal_size(modal_name)
            # Apply clamping to match the actual drawn modal size
            modal_w, modal_h = self._clamp_modal_to_desktop(modal_w, modal_h)
            
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
                gap = int(20 * self.scale)
                terminal_h = int(200 * self.scale)  # Match drawing/click handling terminal height
                button_size = int(42 * self.scale)
                button_spacing = int(10 * self.scale)
                
                # Title bar close button
                close_btn_size = int(20 * self.scale)
                close_btn_x = modal_x + modal_w - close_btn_size - int(5 * self.scale)
                close_btn_y = modal_y + int(5 * self.scale)
                close_btn_rect = pygame.Rect(close_btn_x, close_btn_y, close_btn_size, close_btn_size)
                if close_btn_rect.collidepoint(mouse_x, mouse_y):
                    self.hovered_button = ("modem", "title_close")
                    return
                
                # Dial/call/disconnect buttons
                terminal_y = modal_y + self.modal_title_bar_height + gap
                dial_start_y = terminal_y + terminal_h + gap
                
                # Calculate centering for dial pad matching _draw_modem_modal
                dial_width = 3 * button_size + 2 * button_spacing
                dial_start_x = modal_x + (modal_w - dial_width) // 2
                
                # Side-by-side button layout (matching drawing/click code)
                action_btn_y = dial_start_y + 4 * (button_size + button_spacing) + int(5 * self.scale)
                action_btn_h = int(48 * self.scale)  # Button height (increased by 25%)
                action_btn_spacing = int(8 * self.scale)
                action_btn_w = (dial_width - action_btn_spacing) // 2
                
                call_btn_x = dial_start_x
                disconnect_btn_x = dial_start_x + action_btn_w + action_btn_spacing
                
                if not self.modem_modal_connection_started:
                    dial_buttons = [["1", "2", "3"], ["4", "5", "6"], ["7", "8", "9"], ["*", "0", "#"]]
                    for row_idx, row in enumerate(dial_buttons):
                        for col_idx, button_label in enumerate(row):
                            btn_x = dial_start_x + col_idx * (button_size + button_spacing)
                            btn_y = dial_start_y + row_idx * (button_size + button_spacing)
                            btn_rect = pygame.Rect(btn_x, btn_y, button_size, button_size)
                            if btn_rect.collidepoint(mouse_x, mouse_y):
                                self.hovered_button = ("modem", f"dial_{button_label}")
                                return
                
                    # CONNECT button (left side)
                    call_btn_rect = pygame.Rect(call_btn_x, action_btn_y, action_btn_w, action_btn_h)
                    if call_btn_rect.collidepoint(mouse_x, mouse_y):
                        self.hovered_button = ("modem", "call")
                        return
                
                # DISCONNECT button (right side, always hoverable)
                disconnect_btn_rect = pygame.Rect(disconnect_btn_x, action_btn_y, action_btn_w, action_btn_h)
                if disconnect_btn_rect.collidepoint(mouse_x, mouse_y):
                    self.hovered_button = ("modem", "disconnect")
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
            elif modal_name == "mail":
                # Title bar close button
                close_btn_size = int(20 * self.scale)
                close_btn_x = modal_x + modal_w - close_btn_size - int(5 * self.scale)
                close_btn_y = modal_y + int(5 * self.scale)
                close_btn_rect = pygame.Rect(close_btn_x, close_btn_y, close_btn_size, close_btn_size)
                if close_btn_rect.collidepoint(mouse_x, mouse_y):
                    self.hovered_button = ("mail", "title_close")
                    return
                # Menu bar buttons
                for btn_rect, view_name in getattr(self, "_mail_menu_hitboxes", []):
                    if btn_rect.collidepoint(mouse_x, mouse_y):
                        label = [k for k, v in {"COMPOSE": "compose", "INBOX": "inbox", "OUTBOX": "outbox", "TRASH": "trash", "CONNECT": "connect", "SETTINGS": "settings"}.items() if v == view_name]
                        if label:
                            self.hovered_button = ("mail", f"menu_{label[0]}")
                        return
                # CONNECT view: SEND/RX and DIAL buttons
                if self.mail_view == "connect":
                    if getattr(self, "_mail_sendrx_btn_rect", None) and self._mail_sendrx_btn_rect.collidepoint(mouse_x, mouse_y):
                        self.hovered_button = ("mail", "sendrx")
                        return
                    if getattr(self, "_mail_dial_btn_rect", None) and self._mail_dial_btn_rect.collidepoint(mouse_x, mouse_y):
                        self.hovered_button = ("mail", "dial")
                        return
                # Compose view buttons
                if self.mail_view == "compose":
                    if getattr(self, "_mail_send_btn_rect", None) and self._mail_send_btn_rect.collidepoint(mouse_x, mouse_y):
                        self.hovered_button = ("mail", "send")
                        return
                    if getattr(self, "_mail_clear_btn_rect", None) and self._mail_clear_btn_rect.collidepoint(mouse_x, mouse_y):
                        self.hovered_button = ("mail", "clear")
                        return
                # Reading view buttons
                if self.mail_view == "reading":
                    if getattr(self, "_mail_back_btn_rect", None) and self._mail_back_btn_rect.collidepoint(mouse_x, mouse_y):
                        self.hovered_button = ("mail", "back")
                        return
                    if getattr(self, "_mail_delete_btn_rect", None) and self._mail_delete_btn_rect.collidepoint(mouse_x, mouse_y):
                        self.hovered_button = ("mail", "delete")
                        return
                    if getattr(self, "_mail_reply_btn_rect", None) and self._mail_reply_btn_rect.collidepoint(mouse_x, mouse_y):
                        self.hovered_button = ("mail", "reply")
                        return
            elif modal_name == "games":
                close_btn_size = int(20 * self.scale)
                close_btn_x = modal_x + modal_w - close_btn_size - int(5 * self.scale)
                close_btn_y = modal_y + int(5 * self.scale)
                close_btn_rect = pygame.Rect(close_btn_x, close_btn_y, close_btn_size, close_btn_size)
                if close_btn_rect.collidepoint(mouse_x, mouse_y):
                    self.hovered_button = ("games", "title_close")
                    return
            elif modal_name == "hard_drive":
                close_btn_size = int(20 * self.scale)
                close_btn_x = modal_x + modal_w - close_btn_size - int(5 * self.scale)
                close_btn_y = modal_y + int(5 * self.scale)
                close_btn_rect = pygame.Rect(close_btn_x, close_btn_y, close_btn_size, close_btn_size)
                if close_btn_rect.collidepoint(mouse_x, mouse_y):
                    self.hovered_button = ("hard_drive", "title_close")
                    return
            elif modal_name == "system_folder":
                close_btn_size = int(20 * self.scale)
                close_btn_x = modal_x + modal_w - close_btn_size - int(5 * self.scale)
                close_btn_y = modal_y + int(5 * self.scale)
                close_btn_rect = pygame.Rect(close_btn_x, close_btn_y, close_btn_size, close_btn_size)
                if close_btn_rect.collidepoint(mouse_x, mouse_y):
                    self.hovered_button = ("system_folder", "title_close")
                    return
            elif modal_name == "file_system_browser":
                close_btn_size = int(20 * self.scale)
                close_btn_x = modal_x + modal_w - close_btn_size - int(5 * self.scale)
                close_btn_y = modal_y + int(5 * self.scale)
                close_btn_rect = pygame.Rect(close_btn_x, close_btn_y, close_btn_size, close_btn_size)
                if close_btn_rect.collidepoint(mouse_x, mouse_y):
                    self.hovered_button = ("file_system_browser", "title_close")
                    return
    
    def _truncate_icon_label(self, text: str, max_len: int = 9) -> str:
        """Truncate label text for icons: if exceeds max_len chars, cut and add '...'."""
        if not text or len(text) <= max_len:
            return text or ""
        return text[:max_len] + "..."

    def _draw_label_under_icon(self, icon_x: int, icon_y: int, icon_w: int, icon_h: int, label_text: str) -> None:
        """Draw a label below an icon (same font, colour, size and gap as file system icons; center-aligned).
        Labels exceeding 9 characters are truncated with '...'."""
        if not label_text:
            return
        font = self.file_system_browser_font
        if not font:
            font = pygame.font.Font(None, max(int(16 * self.scale), 12))
        label_gap = int(8 * self.scale)  # Space between icon and text
        try:
            display_text = self._truncate_icon_label(label_text)
            text_surface = font.render(display_text, True, COLOR_CYAN)
            label_x = icon_x + (icon_w - text_surface.get_width()) // 2
            label_y = icon_y + icon_h + label_gap
            self.screen.blit(text_surface, (label_x, label_y))
        except Exception:
            pass

    def _draw_icon_label(self, icon_x: int, icon_y: int, icon_w: int, icon_h: int, label_text: str):
        """Draw a label below an icon with fade animation. Labels >9 chars truncated with '...'."""
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
            display_text = self._truncate_icon_label(label_text)
            # Create text surface with alpha
            text_surface = label_font.render(display_text, True, COLOR_CYAN)
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
    
    # -------------------------------------------------------------------------
    # Ghost User Methods (for Node 7 completion sequence)
    # -------------------------------------------------------------------------
    
    def _set_ghost_user_health_state(self):
        """Set health monitor state for ghost user sequence."""
        # System is already OPERATIONAL (hardcoded)
        # HardDisk is already 50/50 (hardcoded)
        # LAPC-1 Soundcard will show ACTIVE if AUDIO_ON token exists (handled in draw)
        # Datasette will be updated when recording starts
        # Network will be set to DISCONNECTED by _set_network_disconnected()
        pass
    
    def _set_network_disconnected(self):
        """Set network status to DISCONNECTED."""
        # Use full disconnect flow so the modem modal returns to idle
        # and shows the CONNECT / DISCONNECT buttons after exiting a BBS.
        self._disconnect_network()
    
    def _ghost_open_notes_mission(self):
        """Open Notes app and switch to mission tab (first tab)."""
        # Open notes modal
        self._open_modal("notes")
        # Ensure mission tab is selected (tab 0)
        self.notes_modal_current_tab = 0
    
    def _ghost_strike_through_mission_point(self, point_number: int):
        """Strike through a specific mission point in the notes."""
        notes = self._load_user_notes()
        if not notes:
            return
        
        mission_note = notes[0]
        if not mission_note.get("is_locked", False):
            return
        
        content = mission_note.get("content", "")
        lines = content.split("\n")
        
        # Find and strike through the specified point (check if already struck)
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith(f"{point_number}.") and not stripped.startswith("[s]"):
                # Add strike tags around the line if not already struck
                lines[i] = f"[s]{line}[/s]"
                break
        
        # Update content
        mission_note["content"] = "\n".join(lines)
        notes[0] = mission_note
        self.save_notes(notes)
    
    def _ghost_click_datasette_icon(self):
        """Simulate double-click on Datasette icon."""
        # Find tape icon
        tape_icon = next((icon for icon in self.icons if "tape-icon" in icon["name"]), None)
        if not tape_icon:
            return
        
        # Simulate double-click by opening the modal
        if "tape" not in self.active_modals:
            self._open_modal("tape")
            self.tape_modal_terminal_text = ""
            self._stop_tape_video()
    
    def _ghost_click_record_data(self):
        """Simulate click on Record Data button in Datasette modal."""
        # Clear terminal and start recording sequence
        self.tape_modal_terminal_lines = []
        self.tape_modal_message_timer = 0.0
        
        # Reset video completion flag so video can play again
        self.tape_modal_video_completed = False
        
        # Start recording (this will update the health monitor status)
        if self.set_recording_state:
            self.set_recording_state(True, pygame.time.get_ticks() / 1000.0)
        
        # Start video playback
        self._start_tape_video()
        
        # Close the modal after a short delay (handled in update)
        # We'll close it in the ghost user sequence after the animation starts

    # -------------------------------------------------------------------------
    # Ghost User Methods (School Hack logout sequence - Notes typing)
    # -------------------------------------------------------------------------

    def _ghost_open_notes_for_school_hack(self) -> bool:
        """Create a new note 'School Op - Steps', open Notes modal, select it, enter edit mode on content.
        Returns True if the school op note was created and is ready for typing."""
        notes = self._load_user_notes()
        # Avoid duplicate school op note - if exists, open it (don't overwrite - player may have credentials)
        for n in notes:
            if n.get("title") == SCHOOL_OP_NOTE_TITLE:
                self._open_modal("notes")
                idx = next((i for i, n2 in enumerate(notes) if n2.get("title") == SCHOOL_OP_NOTE_TITLE), 0)
                self.notes_modal_current_tab = idx
                self._enter_notes_edit_mode(idx, is_new=False)
                self.notes_modal_edit_field = "content"
                return True
        new_note = {"title": SCHOOL_OP_NOTE_TITLE, "content": "", "is_locked": False}
        notes.append(new_note)
        self._save_user_notes(notes)
        self._open_modal("notes")
        self.notes_modal_current_tab = len(notes) - 1
        self._enter_notes_edit_mode(len(notes) - 1, is_new=True)
        self.notes_modal_edit_field = "content"
        self.notes_modal_content_cursor = len(self.notes_modal_edit_content_text)
        self.notes_modal_content_selection = (self.notes_modal_content_cursor, self.notes_modal_content_cursor)
        return True

    def _ghost_append_school_op_line(self, line_index: int) -> bool:
        """Set or replace the school op note with the no-credentials version (placeholders).
        If note already has credentials (player found them), don't overwrite - preserve progress."""
        if line_index < 0 or line_index >= len(SCHOOL_HACK_NOTE_LINES_NO_CREDS):
            return False
        # Don't overwrite if player already found credentials
        content = self.notes_modal_edit_content_text or ""
        if "admin-subset" in content and "general" in content and "louis-sonic" in content:
            return True  # Consume beat, preserve player progress
        # Replace with no-creds version (never append to avoid duplicates)
        self.notes_modal_edit_content_text = self._get_school_op_note_content(with_credentials=False)
        self.notes_modal_content_cursor = len(self.notes_modal_edit_content_text)
        self.notes_modal_content_selection = (self.notes_modal_content_cursor, self.notes_modal_content_cursor)
        return True

    def _ghost_finish_school_op_note(self) -> None:
        """Save the school op note and exit edit mode. Notes modal stays open."""
        self._exit_notes_edit_mode(save_changes=True)

    def get_school_hack_note_line_count(self) -> int:
        """Return number of bullet lines for the school op ghost sequence."""
        return len(SCHOOL_HACK_NOTE_LINES_NO_CREDS)

    def is_school_op_note_visible(self) -> bool:
        """True if the Notes modal is open and the current note is the School Op - Steps note."""
        if "notes" not in self.active_modals:
            return False
        notes = self._load_user_notes()
        if not notes or self.notes_modal_current_tab < 0 or self.notes_modal_current_tab >= len(notes):
            return False
        return (notes[self.notes_modal_current_tab].get("title") or "").strip() == SCHOOL_OP_NOTE_TITLE

    def is_terminal_open(self) -> bool:
        """True if the OS terminal (file-system / admin) is open."""
        return getattr(self, "terminal_active", False)

