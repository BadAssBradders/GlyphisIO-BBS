"""
Configuration constants for GlyphisIO BBS.

All game constants, colors, dimensions, and configuration values are centralized here.
"""

# Screen dimensions
SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 700

# BBS window dimensions (baseline resolution: 2560x1440)
BBS_WIDTH = 872   # Width: 872 pixels
BBS_HEIGHT = 654  # Height: 654 pixels
BBS_X = 224       # Position at baseline resolution
BBS_Y = 215       # Position at baseline resolution

# Baseline resolution (reference resolution for scaling)
BASELINE_WIDTH = 2560
BASELINE_HEIGHT = 1440

# Colors
BLACK = (0, 0, 0)
CYAN = (0, 255, 255)
DARK_BLUE = (0, 0, 139)
DARK_CYAN = (0, 139, 139)
BLUE = (0, 100, 200)
RED = (255, 64, 64)
WHITE = (255, 255, 255)
GRID_BLUE = (12, 24, 48)
PANEL_BLUE = (8, 16, 32)
HIGHLIGHT_BLUE = (0, 70, 120)
ACCENT_CYAN = (0, 196, 255)
PINK = (255, 192, 203)  # Pink color for ANSI art

# UI Elements
SELECTION_GLYPH = "⦿"

# Hotspots (baseline resolution coordinates)
RESET_HOTSPOT = (551, 1404, 599 - 551, 1419 - 1404)  # x, y, width, height
OVERLAY_HOTSPOT = (1098, 1079, 1111 - 1098, 1109 - 1079)  # x, y, width, height

# Steam Configuration
STEAM_APP_ID = 4179570

# Audio Configuration
AUDIO_FREQUENCY = 22050
AUDIO_SIZE = -16
AUDIO_CHANNELS = 2
AUDIO_BUFFER = 512
AMBIENT_FADE_DURATION = 3.0  # seconds

# Animation Timings
SCROLL_SPEED_MULTIPLIER = 2  # pixels per frame (will be scaled)
SCROLL_PAUSE_Y = 660  # Y position where pause occurs (will be scaled)
GRID_ANIM_DURATION = 0.4
GRID_ANIM_TOTAL = 0.4
CLOSE_DURATION = 0.25

# Email Configuration
EMAIL_CHECK_INTERVAL = 60  # frames (at 60fps = 1 second)

# Module Names
MODULE_TERMINAL_FEED = "TERMINAL FEED: THE WALL"
MODULE_EMAIL = "EMAIL SYSTEM"
MODULE_GAMES = "GAMES"
MODULE_URGENT_OPS = "URGENT OPS"
MODULE_TEAM_INFO = "TEAM INFO"
MODULE_PIRATE_RADIO = "PIRATE RADIO"
MODULE_LOGOUT = "LOGOUT"

# Default Player Email
DEFAULT_PLAYER_EMAIL = "unknown"

# Font Sizes (will be scaled)
FONT_SIZE_LARGE = 30
FONT_SIZE_MEDIUM = 22
FONT_SIZE_MEDIUM_SMALL = 20
FONT_SIZE_SMALL = 16
FONT_SIZE_TINY = 12

# Game States
STATE_BBS_SCROLL = "bbs_scroll"
STATE_INTRO = "intro"
STATE_LOADING = "loading"
STATE_MAIN_MENU = "main_menu"
STATE_FRONT_POST = "front_post"
STATE_EMAIL_MENU = "email_menu"
STATE_COMPOSE = "compose"
STATE_INBOX = "inbox"
STATE_OUTBOX = "outbox"
STATE_SENT = "sent"
STATE_READING = "reading"
STATE_GAMES = "games"
STATE_TASKS = "tasks"
STATE_TEAM = "team"
STATE_RADIO = "radio"
STATE_GAME_SESSION = "game_session"
STATE_URGENT_OPS_SESSION = "urgent_ops_session"
STATE_LOGIN_USERNAME = "login_username"
STATE_LOGIN_PIN_CREATE = "login_pin_create"
STATE_LOGIN_PIN_VERIFY = "login_pin_verify"
STATE_LOGIN_SUCCESS = "login_success"

# Keyboard Shortcuts
KEY_QUIT = "F12"
KEY_DOCS_TOGGLE = "F4"
KEY_DELETE_USER = "F11"

