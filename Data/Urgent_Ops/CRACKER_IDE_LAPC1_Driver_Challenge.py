import pygame
import re
import time
import os
import sys
import random
from typing import List, Dict, Any, Tuple, Optional

# Data path helper - works for both development and built executable
def get_data_path(*path_parts):
    """
    Returns the path to the Data folder, handling both development and built executable scenarios.
    In development: returns "Data/..." relative to script directory
    In built exe: returns path to Data folder bundled with executable
    """
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        base_path = sys._MEIPASS
    else:
        # Running as script - go up from Urgent_Ops to project root, then to Data
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)  # Go up from Urgent_Ops to project root
        base_path = project_root
    
    # Check if Data folder exists, if not fall back to root (for backwards compatibility)
    data_folder = os.path.join(base_path, "Data")
    if os.path.exists(data_folder):
        return os.path.join(data_folder, *path_parts)
    else:
        # Fallback: look in root directory (for backwards compatibility during transition)
        return os.path.join(base_path, *path_parts)

# --- Try to import cv2 for video playback (as per main.py logic) ---
try:
    import cv2
    import numpy as np
    _cv2_available = True
except ImportError:
    _cv2_available = False
    print("Warning: cv2 (opencv-python) not available. Video playback will be disabled.")
    # Define mocks for compatibility
    class MockCap:
        def isOpened(self): return False
        def read(self): return False, None
        def release(self): pass
        def set(self, prop, value): pass
    cv2 = type('MockCV2', (object,), {'VideoCapture': lambda x: MockCap()})()
    np = None

# -----------------------------------------------------------------------------
# [ GLYPHIS_IO BBS: The Proxy Tapes 1989 ]
#
# This file contains the complete, self-contained game module for the
# LAPC-1 Assembly programming challenge.
#
# **NARRATIVE GOAL: Write the LAPC-1 driver code to power on the sound card
# and begin streaming data.**
#
# --- INTEGRATION GUIDE FOR main.py ---
#
# 1. Initialization:
#    Add an instance variable in GlyphisIOBBS.__init__():
#    self.lapc1_game_instance = None
#
# 2. Launching the Game Session (in draw_tasks_module, on ENTER key):
#    Instantiate and set the state:
#    # NOTE: Class name changed to CRACKER_IDE_LAPC1_Driver_Challenge
#    self.lapc1_game_instance = CRACKER_IDE_LAPC1_Driver_Challenge(self.bbs_surface, fonts, self.scale, self.player_email)
#    self.state = "lapc1_quiz_session"
#
# 3. Game Loop Integration (Event Handling, in main run() loop):
#    Check for the state and pass events:
#    elif self.state == "lapc1_quiz_session":
#        action = self.lapc1_game_instance.handle_event(event)
#        if action == "EXIT":
#            self.state = "tasks" # Return to URGENT OPS module
#            self.lapc1_game_instance = None
#
# 4. Drawing (in main run() loop):
#    Draw the game onto the BBS surface:
#    elif self.state == "lapc1_quiz_session":
#        if self.lapc1_game_instance:
#            self.lapc1_game_instance.draw()
#
GAME_TITLE = "GLYPHIS_IO BBS: The Proxy Tapes 1989"

# --- Constants for LAPC-1 Registers and Addresses ---
REG_MASTER_POWER = 0xC400
REG_LEFT_CHANNEL = 0xC401
REG_RIGHT_CHANNEL = 0xC402
REG_DATA_READY = 0xC403
REG_PACKET_BUFFER = 0xC800
ACTIVATION_BYTE = 0x01
READY_STATE = 0x01
DEFAULT_VOLUME = 0x80

# --- Uncle-Am's Narrative Questions (for Modal) ---
UNCLE_AM_Q1 = ">> Task 1: Power on the LAPC-1 chip on RADLAND Soundcard? (Hint: See $C400 & Activation Byte $01)"
UNCLE_AM_Q2 = ">> Task 2: Set the volume and stream the data to the speakers output lines, then setup the busy-wait for new samples."

# --- Core Game Class ---
class CRACKER_IDE_LAPC1_Driver_Challenge:
    """
    A self-contained Pygame module for the LAPC-1 Assembler Quiz.
    Simulates a constrained CPU environment (Bradsonic 69000) within the CRACKER-PARROT IDE.
    """
    
    VIDEO_FPS = 30.0 # Standard FPS for video playback timing
    ANIMATION_DURATION = 4.0 # Seconds the video plays per module jump

    def __init__(self, surface, fonts, scale, player_username, token_checker=None, token_remover=None):
        self.surface = surface
        self.fonts = fonts
        self.scale = scale
        self.player_username = player_username
        self.token_checker = token_checker  # Function to check if user has a token
        self.token_remover = token_remover  # Function to remove a token from user's inventory

        # Normalised font references for convenience
        self.font_large = self.fonts["large"]
        self.font_medium = self.fonts["medium"]
        self.font_small = self.fonts["small"]
        self.font_tiny = self.fonts["tiny"]
        # Create a slightly smaller font for the parrot caption (1pt smaller than medium)
        try:
            medium_height = self.font_medium.get_height()
            # Reduce by approximately 1-2 pixels (roughly 1pt at typical DPI)
            caption_size = max(1, medium_height - 2)
            self.font_caption = pygame.font.Font(None, caption_size)
        except:
            self.font_caption = self.font_medium  # Fallback to medium if creation fails
        
        self.width = self.surface.get_width()
        self.height = self.surface.get_height()

        # --- Colors (Matching BBS style) ---
        self.BLACK = (0, 0, 0)
        self.WHITE = (255, 255, 255)
        self.CYAN = (0, 255, 255)
        self.DARK_CYAN = (0, 139, 139)
        self.GREEN = (0, 255, 0)
        self.DARK_GREEN = (0, 128, 0)
        self.RED = (255, 64, 64)
        self.YELLOW = (255, 255, 0)
        self.HIGHLIGHT_CYAN = (0, 70, 120)
        self.PINK = (255, 105, 180)
        self.PANEL_GRADIENT_TOP = (16, 28, 52)
        self.PANEL_GRADIENT_BOTTOM = (6, 12, 28)
        self.HEADER_GRADIENT_TOP = (12, 96, 144)
        self.HEADER_GRADIENT_BOTTOM = (8, 48, 88)
        self.SHADOW_COLOR = (0, 0, 0, 130)

        # --- UI Layout ---
        self.padding = max(int(8 * self.scale), 8)
        self.panel_padding = max(int(10 * self.scale), 8)
        self.panel_shadow_offset = max(int(3 * self.scale), 2)
        self.page_titles = [
            "NODE 01",
            "NODE 02",
            "NODE 03",
            "NODE 04",
            "NODE 05",
            "NODE 06",
            "NODE 07",
        ]
        self.page_index = 0
        self.base_parrot_size = 260
        self.parrot_anchor_local = (-11.0, -13.0)
        self.focus_target = "editor"
        self.control_focus = 0
        self.control_labels = ["RUN"]
        self.parrot_overlay = None
        self.node_briefings = [
            "Power rail first. Follow that pseudo-code: load literal 01 into A, push it to $C400, verify the LED flips, then ride the jump into the left-channel test.",
            "Left channel diagnostic next. Pump #$FF into $C401, mute $C402 with #$00, listen for the pop, then jump forward, mirror logic hits on the next node.",
            "Right channel mirror time. Swap the roles: drive $C402 hot with #$FF, silence $C401, confirm both speakers responded before you advance.",
            "Now set the baseline gain. Load #$80 once, store it to $C401 and $C402, confirm both registers sit at mid volume, and lock it in.",
            "Initialization is stitched up. Keep this node lean, just route execution into DATA_CHECK so the loop can spin.",
            "Busy wait comes alive here. Read $C403, compare with #$01, branch back until the flag is true. Only fall through when the buffer shouts READY.",
            "Sample transfer finishes the cycle. Pull the byte from $C800, write it to both channels, kick back to DATA_CHECK, and let the loop breathe.",
            "",
            "WARNING: The audio stream contains banned content. Keep your volume low and make sure nobody's listening. What you're about to hear was never supposed to survive the purge.",
        ]
        self.node_help_messages: Dict[int, List[str]] = {
            0: [
                "Pretty sure section 4 of the Getting Started guide (F4) has the power-on snippet, load #$01 into A and push it into $C400.",
                "From memory the LAPC-1 quick reference puts the master power rail at $C400 and wants byte #$01 to light the card up.",
                "Stick with the LDA then STA pattern. Needs the literal #$01 to flip the power LED.",
            ],
            1: [
                "I remember the Radland supplement (F4) saying Node 2 blasts the left channel, load #$FF and shove it into $C401.",
                "Mute the right side while you test the left. That means drop #$00 into $C402 before you bounce onward.",
                "Jot down: max value into $C401, zero into $C402, then jump forward.",
            ],
            2: [
                "Mirror that left-channel test. Section 3.1 step 3 (F4) rings a bell, drive $C402 with #$FF this time.",
                "While you pump the right channel, keep the left muted with #$00 in $C401.",
                "Accumulator only holds one byte, so reload between the left and right writes.",
            ],
            3: [
                "The supplement’s next step (F4) resets both channels to a neutral #$80. Load it once, then store to $C401 and $C402.",
                "You only need one LDA #$80. After that it’s just two STA writes, left then right.",
                "Default gain is #$80, make sure both registers land on that value before you leave.",
            ],
            4: [
                "Wisdom is sometimes in the knowledge of knowing when to do the simplest thing.",
                "Just jump us to the next part of the code {username} which is the label DATA_CHECK.",
                "Just a jump, nothing else. JMP DATA_CHECK - that's all you need.",
            ],
            5: [
                "Busy-wait loop lives here, pull the flag from $C403 and compare it against #$01.",
                "If it isn’t ready, branch right back to DATA_CHECK. That keeps the poll tight.",
                "Only fall through when the compare says equal, then you’re straight into OUTPUT_SAMPLE.",
            ],
            6: [
                "Once $C403 says ready, pull a byte from $C800, that buffer is read-only so just LDA it.",
                "Store that sample into both $C401 and $C402. One load, two writes.",
                "Close it with a JMP back to DATA_CHECK so the loop keeps streaming.",
            ],
        }
        self.chat_busy_messages = [
            "Sorry Neck-deep wiring the dispatch, keep volume up but not blasting.",
            "Juggling homework and ops. I'll circle back when I come up for air.",
            "Busy spinning up pirate radio feeds. Give me a sec.",
            "Swamped on my end. You got this.",
            "Tuning circuits here. Just keep coding.",
            "Homework hell right now. Stay sharp.",
        ]
        self.chat_messages: List[Tuple[str, str]] = []
        self.chat_input = ""
        self.chat_cursor_visible = True
        self.last_chat_cursor_toggle = pygame.time.get_ticks()
        self.last_briefing_node: Optional[int] = None
        self.chat_typing_state: Optional[Dict[str, Any]] = None
        self.chat_scroll_offset = 0
        self.chat_scroll_limit = 0
        self.modal_scroll_offset = 0
        self.modal_scroll_limit = 0
        self.editor_scroll_offset = 0
        self.editor_scroll_limit = 0
        self.chat_message_queue: List[Dict[str, str]] = []
        self.chat_next_queue_time = 0
        self.intro_sequence_started = False
        self.chat_follow_latest = True
        self.modal_step = 0
        self.modal_data: List[Dict[str, Any]] = []
        # Success modal state
        self.success_modal_active = False
        self.success_modal_data: List[Dict[str, Any]] = []
        self.success_modal_step = 0
        self.pending_node_switch: Optional[int] = None  # Node to switch to after success modal

        header_base = self.padding * 2 + self.font_small.get_linesize() * 2
        self.parrot_display_size = int(self.base_parrot_size * self.scale)
        self.header_height = max(header_base, self.parrot_display_size + int(30 * self.scale))

        monitor_x = int(205 * self.scale)
        monitor_y = int(14 * self.scale)
        monitor_right = int(853 * self.scale)
        monitor_width = max(monitor_right - monitor_x, int(220 * self.scale))
        monitor_bottom_target = int((200 - 10) * self.scale)
        max_monitor_height = max(self.height - monitor_y - int(12 * self.scale), int(60 * self.scale))
        desired_monitor_height = max(monitor_bottom_target - monitor_y, int(120 * self.scale))
        monitor_height = min(max_monitor_height, desired_monitor_height)

        self.monitor_pane_rect = pygame.Rect(
            monitor_x,
            monitor_y,
            monitor_width,
            monitor_height,
        )
        editor_width = max(int((444 - 6) * self.scale), int(200 * self.scale))
        editor_height = max(int((614 - 200) * self.scale), int(120 * self.scale))
        self.editor_pane_rect = pygame.Rect(
            int(6 * self.scale),
            int(200 * self.scale),
            editor_width,
            editor_height,
        )
        team_width = max(int((853 - 446) * self.scale), int(200 * self.scale))
        team_height = max(int((395 - 200) * self.scale), int(120 * self.scale))
        self.team_window_rect = pygame.Rect(
            int(446 * self.scale),
            int(200 * self.scale),
            team_width,
            team_height,
        )
        self.line_height = self.font_small.get_linesize() + 2

        # --- Game State ---
        self.game_state = "EDITING"  # EDITING, RUNNING, PAUSED, ERROR, SUCCESS
        self.modal_active = True     
        self.clock = pygame.time.Clock()
        self.sim_speed = 100 
        self.last_tick_time = 0
        self.exit_requested = False

        # --- CPU State ---
        self.cpu_state = {}
        self.code_areas_content: List[List[str]] = []
        self.code_lines_flat: List[Dict[str, Any]] = []
        self.labels: Dict[str, int] = {}
        self.editor_focus_node = 0  # 0-6
        self.cursor_pos = (0, 0)    # (row in node, char index)
        self.zero_flag = False      
        self.packet_queue = []
        self.data_ticks = 0

        # --- Visualizer ---
        self.waveform_history: List[int] = []
        self.max_wave_samples = 80
        self._power_led_prev_state: bool = False
        self.power_on_sound: Optional[pygame.mixer.Sound] = None
        self.left_test_sound: Optional[pygame.mixer.Sound] = None
        self.right_test_sound: Optional[pygame.mixer.Sound] = None
        self.u1_sound: Optional[pygame.mixer.Sound] = None
        self.node7_sound: Optional[pygame.mixer.Sound] = None
        # Track audio channels for video switching
        self.active_audio_channels: List[pygame.mixer.Channel] = []
        
        # --- Video/Image Resources ---
        self.challenge_completed = False # Flag for total completion (SUCCESS state)
        self.pending_token_grants = []  # List of tokens to grant (checked by main.py)
        self.module_animation_timer = 0.0 # NEW: Timer for per-module video animation
        self.parrot_logo_png = None 
        self.video_cap = None      
        self.video_frame = None    
        self.video_playback_timing = 0 
        self.target_logo_size = None 
        self.static_mock_surface = None 
        self.parrot_logo_png = self._load_and_process_parrot_logo()
        self.node_badges: Dict[str, Optional[pygame.Surface]] = {}
        self._load_node_badges()

        # --- Editor Setup ---
        self.node_titles = [
            "NODE 01",
            "NODE 02",
            "NODE 03",
            "NODE 04",
            "NODE 05",
            "NODE 06",
            "NODE 07",
        ]
        self.node_labels = [
            "INIT_POWER", "DIAG_LEFT", "DIAG_RIGHT", "INIT_VOL",
            "STREAM_ENTRY", "DATA_CHECK", "OUTPUT_SAMPLE"
        ]
        
        self.default_code = self._get_default_code()
        self.reset_state()
        # Restore LED states from tokens after reset
        self._restore_led_states_from_tokens()
        # Determine starting node based on completed progress
        starting_node = self._determine_starting_node()
        self.page_index = starting_node
        self.editor_focus_node = starting_node
        
        # Set initial cursor position based on node type
        node_lines = self.code_areas_content[starting_node]
        if starting_node == 5:  # Node 6 (index 5) - has DATA_CHECK: label
            # Find the label line and position cursor on the blank line after it
            label_line_idx = -1
            for i, line in enumerate(node_lines):
                if line.strip().endswith(":"):
                    label_line_idx = i
                    break
            if label_line_idx >= 0 and label_line_idx + 1 < len(node_lines):
                self.cursor_pos = (label_line_idx + 1, 0)  # Position after label
            else:
                self.cursor_pos = (2, 0)  # Fallback to line 2
        elif starting_node == 6:  # Node 7 (index 6) - has OUTPUT_SAMPLE: label
            # Find the label line and position cursor on the blank line after it
            label_line_idx = -1
            for i, line in enumerate(node_lines):
                if line.strip().endswith(":"):
                    label_line_idx = i
                    break
            if label_line_idx >= 0 and label_line_idx + 1 < len(node_lines):
                self.cursor_pos = (label_line_idx + 1, 0)  # Position after label
            else:
                self.cursor_pos = (2, 0)  # Fallback to line 2
        else:
            # For nodes without labels (1-5), cursor goes to line 1 (blank line after comment)
            self.cursor_pos = (1, 0)
        
        # Prepare modal for the starting node (not Node 1)
        self._prepare_modal_for_current_node()
        # If starting at Node 1, intro sequence will be triggered when modal is dismissed
        # If starting at a later node, skip intro sequence and show briefing immediately
        if starting_node > 0:
            self.intro_sequence_started = True  # Skip intro sequence for later nodes
            # Set last_briefing_node to one before starting node so briefing will show
            # (push_node_briefing checks if node_idx == last_briefing_node and skips if so)
            self.last_briefing_node = starting_node - 1
            self._push_node_briefing()  # Show briefing for the starting node

    def _draw_text_on_surface(self, surface, text, pos, font_key, color):
        """Helper to draw text on an arbitrary surface."""
        try:
            text_surface = self.fonts[font_key].render(text, True, color, self.BLACK)
            surface.blit(text_surface, pos)
        except Exception:
            pass

    def _wrap_text(self, text: str, font: pygame.font.Font, max_width: int) -> List[str]:
        """Wrap text to fit within max_width pixels. Preserves double newlines as blank lines."""
        if not text:
            return []
        
        # First split by newlines to preserve paragraph structure and consecutive newlines
        paragraphs = text.split('\n')
        lines: List[str] = []
        
        for paragraph in paragraphs:
            # Empty paragraph means a blank line (from \n\n)
            if paragraph == "":
                lines.append("")
                continue
            
            # Wrap this paragraph
            words = paragraph.split()
            if not words:
                continue
            
            current = words[0]
            for word in words[1:]:
                candidate = f"{current} {word}"
                if font.size(candidate)[0] <= max_width:
                    current = candidate
                else:
                    lines.append(current)
                    current = word
            if current:
                lines.append(current)
        
        return lines

    def _draw_panel(self, rect: pygame.Rect, title: Optional[str] = None, subtitle: Optional[str] = None,
                    accent: Optional[tuple[int, int, int]] = None, border_width: int = 2) -> tuple[pygame.Rect, Optional[pygame.Rect]]:
        """Render a glassy panel with optional title and return the content area."""
        accent = accent or self.CYAN
        shadow_surface = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        shadow_surface.fill(self.SHADOW_COLOR)
        self.surface.blit(shadow_surface, (rect.x + self.panel_shadow_offset, rect.y + self.panel_shadow_offset))

        base_surface = pygame.Surface((rect.width, rect.height))
        base_surface.fill(self.BLACK)
        self.surface.blit(base_surface, rect.topleft)
        pygame.draw.rect(self.surface, accent, rect, border_width)

        header_rect: Optional[pygame.Rect] = None
        content_top = rect.y + 2
        if title:
            header_height = self.font_small.get_linesize() + self.panel_padding // 2
            header_rect = pygame.Rect(rect.x + 2, rect.y + 2, rect.width - 4, header_height)
            header_surface = pygame.Surface((header_rect.width, header_rect.height), pygame.SRCALPHA)
            for y in range(header_rect.height):
                blend = y / max(1, header_rect.height - 1)
                color = (
                    int(self.HEADER_GRADIENT_TOP[0] + (self.HEADER_GRADIENT_BOTTOM[0] - self.HEADER_GRADIENT_TOP[0]) * blend),
                    int(self.HEADER_GRADIENT_TOP[1] + (self.HEADER_GRADIENT_BOTTOM[1] - self.HEADER_GRADIENT_TOP[1]) * blend),
                    int(self.HEADER_GRADIENT_TOP[2] + (self.HEADER_GRADIENT_BOTTOM[2] - self.HEADER_GRADIENT_TOP[2]) * blend),
                )
                pygame.draw.line(header_surface, color, (0, y), (header_rect.width, y))
            pygame.draw.rect(header_surface, accent, header_surface.get_rect(), 1)
            title_surface = self.font_small.render(title, True, self.WHITE)
            title_x = self.panel_padding
            title_y = max(0, header_rect.height // 2 - title_surface.get_height() // 2)
            header_surface.blit(title_surface, (title_x, title_y))
            if subtitle:
                subtitle_surface = self.font_tiny.render(subtitle, True, self.YELLOW)
                gap = int(12 * self.scale)
                sub_x = title_x + title_surface.get_width() + gap
                sub_y = title_y + max(0, (title_surface.get_height() - subtitle_surface.get_height()) // 2)
                header_surface.blit(subtitle_surface, (sub_x, sub_y))
            self.surface.blit(header_surface, header_rect.topleft)
            content_top = header_rect.bottom + self.panel_padding
        content_rect = pygame.Rect(
            rect.x + self.panel_padding,
            content_top,
            rect.width - self.panel_padding * 2,
            max(rect.bottom - content_top - self.panel_padding, 0),
        )
        return content_rect, header_rect

    def _get_node_indices_for_page(self, page_index: int) -> List[int]:
        if page_index < 0 or page_index >= len(self.code_areas_content):
            return []
        return [page_index]

    def _reset_cursor_for_focus(self):
        lines = self.code_areas_content[self.editor_focus_node]
        if not lines:
            lines = [""]
            self.code_areas_content[self.editor_focus_node] = lines
        row = min(self.cursor_pos[0], max(len(lines) - 1, 0))
        col = min(self.cursor_pos[1], len(lines[row]))
        self.cursor_pos = (row, col)

    def _reset_chat_state(self):
        self.chat_messages.clear()
        self.chat_input = ""
        self.chat_cursor_visible = True
        self.last_chat_cursor_toggle = pygame.time.get_ticks()
        self.last_briefing_node = None
        self.chat_typing_state = None
        self.chat_scroll_offset = 0
        self.chat_scroll_limit = 0
        self.modal_scroll_offset = 0
        self.modal_scroll_limit = 0
        self.editor_scroll_offset = 0
        self.editor_scroll_limit = 0
        self.chat_message_queue.clear()
        self.chat_next_queue_time = 0
        self.intro_sequence_started = False
        self.chat_follow_latest = True

    def _append_chat(self, speaker: str, text: str):
        self.chat_messages.append((speaker, text.upper()))
        if len(self.chat_messages) > 30:
            self.chat_messages = self.chat_messages[-30:]
        self.chat_scroll_offset = 0
        self.chat_scroll_limit = 0
        self.modal_scroll_offset = 0
        self.modal_scroll_limit = 0
        self.editor_scroll_offset = 0
        self.editor_scroll_limit = 0
        self.chat_follow_latest = True

    def _push_node_briefing(self):
        node_idx = self.page_index
        if node_idx == self.last_briefing_node:
            return

        prev_node_idx = node_idx - 1
        if prev_node_idx >= 0 and prev_node_idx < len(self.node_labels):
            ack_message = None
            mem = self.cpu_state["Memory"]

            if prev_node_idx == 0 and mem.get(REG_MASTER_POWER) == ACTIVATION_BYTE:
                ack_message = "I see the $C400 master power LED is green! Nice work, the card is live and the left channel test is next."
            elif prev_node_idx == 3 and mem.get(REG_LEFT_CHANNEL) == DEFAULT_VOLUME and mem.get(REG_RIGHT_CHANNEL) == DEFAULT_VOLUME:
                ack_message = "Gain check is nominal. $C401 and $C402 are logged to $80. We're ready for the continuous streaming loop."
            elif prev_node_idx == 4 and self.cpu_state["cycles"] > 5:
                ack_message = "Initialization is complete. We've entered the main loop. Now the real-time clock race starts."

            if ack_message:
                self._append_chat("UNCLE-AM", ack_message.upper())

        if 0 <= node_idx < len(self.node_briefings):
            self._append_chat("UNCLE-AM", self.node_briefings[node_idx].upper())
            self.last_briefing_node = node_idx

    def _queue_chat_message(self, message: str, speaker: str = "UNCLE-AM") -> None:
        self.chat_message_queue.append({"speaker": speaker, "message": message})

    def _begin_next_queued_message(self) -> None:
        if self.chat_typing_state or not self.chat_message_queue:
            return
        next_item = self.chat_message_queue.pop(0)
        now = pygame.time.get_ticks()
        self.chat_typing_state = {
            "message": next_item["message"].upper(),
            "speaker": next_item.get("speaker", "UNCLE-AM"),
            "start": now,
            "last_stage": now,
            "stage": 0,
            "from_queue": True,
        }

    def _start_intro_sequence(self) -> None:
        if self.intro_sequence_started:
            return
        self.intro_sequence_started = True
        self.chat_message_queue.clear()
        
        # Only show intro sequence if starting at Node 1 (index 0)
        # For later nodes, the briefing will be shown instead
        if self.page_index == 0:
            intro_lines = [
                "HEY THERE {player}! GLAD YOU MADE IT INTO THE CRACKER IDE FEED.",
                "We spun this console up so the crew can crack locked-down games together.",
                "It's also a cozy driver lab when you need to nurse finicky hardware.",
                "I've already patched the backend into your local sound card - enter the right bytes and audio will sing.",
                "First tip for Node 01: power rail first. Write #$01 (that's 1 byte) into memory address $C400 before poking anything else.",
            ]
            for line in intro_lines:
                if "{player}" in line:
                    raw_name = self.player_username or ""
                    if "@" in raw_name:
                        raw_name = raw_name.split("@", 1)[0]
                    friendly_name = raw_name.strip() or "OPERATIVE"
                    cleaned_name = re.sub(r"[^A-Za-z0-9_\- ]", "", friendly_name).strip() or "OPERATIVE"
                    line = line.replace("{player}", cleaned_name.upper())
                self._queue_chat_message(line, "UNCLE-AM")
            self.chat_next_queue_time = pygame.time.get_ticks() + 600
            self._begin_next_queued_message()
            self.last_briefing_node = 0
        else:
            # For later nodes, just show the briefing for the current node
            self._push_node_briefing()

    def _submit_chat_message(self):
        text = self.chat_input.strip()
        if not text:
            return
        if self.chat_typing_state:
            self._append_chat("UNCLE-AM", self.chat_typing_state["message"])
            self.chat_typing_state = None

        self._append_chat("YOU", text.upper())
        self.chat_input = ""
        normalized = text.lower()
        clean_text = re.sub(r"[^a-z0-9\s]", " ", normalized)
        clean_text = re.sub(r"\s+", " ", clean_text).strip()
        if self._is_help_request(clean_text):
            messages = self.node_help_messages.get(self.page_index)
            if messages:
                reply = random.choice(messages)
                # Replace {username} placeholder with player's username
                if "{username}" in reply:
                    raw_name = self.player_username or ""
                    if "@" in raw_name:
                        raw_name = raw_name.split("@", 1)[0]
                    friendly_name = raw_name.strip() or "OPERATIVE"
                    cleaned_name = re.sub(r"[^A-Za-z0-9_\- ]", "", friendly_name).strip() or "OPERATIVE"
                    reply = reply.replace("{username}", cleaned_name)
            else:
                reply = "Wish I could dig up docs for this node, but homework's crushing me, keep probing the manuals and stay focused."
        elif self._is_status_check(clean_text):
            reply = "Yeah, I'm good, just buried under wiring and homework right now."
        else:
            reply = random.choice(self.chat_busy_messages)
        now = pygame.time.get_ticks()
        self.chat_typing_state = {
            "message": reply.upper(),
            "start": now,
            "last_stage": now,
            "stage": 0,
        }
        self.chat_scroll_offset = 0

    def _advance_focus_cycle(self, backwards: bool = False):
        if backwards:
            if self.focus_target == "controls":
                if self.control_focus > 0:
                    self.control_focus -= 1
                else:
                    self.focus_target = "chat"
                return
            if self.focus_target == "chat":
                self.focus_target = "editor"
                self._ensure_focus_visible()
                return
            if self.focus_target == "editor":
                self.focus_target = "controls"
                self.control_focus = len(self.control_labels) - 1
                return
        else:
            if self.focus_target == "editor":
                self.focus_target = "chat"
                return
            if self.focus_target == "chat":
                self.focus_target = "controls"
                self.control_focus = 0
                return
            if self.focus_target == "controls":
                self.control_focus += 1
                if self.control_focus >= len(self.control_labels):
                    self.control_focus = 0
                    self.focus_target = "editor"
                    self._ensure_focus_visible()
                return

    def _is_status_check(self, clean_text: str) -> bool:
        if not clean_text:
            return False
        phrases = [
            "are you ok",
            "are you okay",
            "are you good",
            "you ok",
            "you okay",
            "you good",
            "you doing ok",
            "you doing okay",
            "how are you",
            "how are ya",
            "how are u",
        ]
        return any(phrase in clean_text for phrase in phrases)

    def _is_help_request(self, clean_text: str) -> bool:
        if not clean_text:
            return False
        if clean_text == "help":
            return True
        phrases = [
            "need help",
            "can you help",
            "help me",
            "please help",
            "give me a hint",
            "what should i do",
            "i am stuck",
            "i'm stuck",
            "stuck here",
            "how do i",
            "what do i do",
            "any hints",
            "any tips",
        ]
        return any(phrase in clean_text for phrase in phrases)

    def _ensure_focus_visible(self):
        visible = self._get_node_indices_for_page(self.page_index)
        if not visible:
            return
        if self.editor_focus_node not in visible:
            self.editor_focus_node = visible[0]
            self.cursor_pos = (0, 0)
        self._reset_cursor_for_focus()
            
    def _load_and_process_parrot_logo(self):
        """
        Loads the IDE-Parrot-logo.png, scales it to 55% (100% - 45% reduction),
        and initializes the video capture object.
        """
        static_img = None
        
        # Use get_data_path to find files in Data/Urgent_Ops/
        try:
            # 1. Load and Scale the static image (IDE-Parrot-logo.png)
            image_path = get_data_path("Urgent_Ops", "IDE-Parrot-logo.png")
            loaded_image = pygame.image.load(image_path).convert_alpha()
            
            original_w, original_h = loaded_image.get_size()
            scale_factor = 0.55
            new_w = int(original_w * scale_factor)
            new_h = int(original_h * scale_factor)
            
            static_img = pygame.transform.scale(loaded_image, (new_w, new_h))
            self.target_logo_size = (new_w, new_h)
            self.static_mock_surface = static_img
            
        except pygame.error:
            print("WARNING: IDE-Parrot-logo.png not found or failed to load. Using mock image.")
            mock_size = 64
            surf = pygame.Surface((mock_size, mock_size), pygame.SRCALPHA)
            surf.fill((0, 0, 0, 0))
            self._draw_text_on_surface(surf, "PARROT", (5, mock_size // 2 - self.line_height // 2), "tiny", self.CYAN)
            static_img = surf
            self.target_logo_size = (mock_size, mock_size)
            self.static_mock_surface = surf

        # 2. Initialize Video Capture (Parrot-Mov.mp4)
        if _cv2_available and self.target_logo_size:
            video_path = get_data_path("Urgent_Ops", "Parrot-Mov.mp4")
            try:
                self.video_cap = cv2.VideoCapture(video_path)
                if not self.video_cap.isOpened():
                    print(f"ERROR: Could not open video file: {video_path}")
                    self.video_cap = None
            except Exception as e:
                print(f"Exception during cv2.VideoCapture init: {e}")
                self.video_cap = None
        
        return static_img

    def _load_node_badges(self):
        for idx in range(1, 11):
            key = f"NODE_{idx}"
            path = get_data_path("Urgent_Ops", f"NODE-{idx}.png")
            surface = None
            try:
                image = pygame.image.load(path).convert_alpha()
                surface = pygame.transform.smoothscale(image, (int(280 * self.scale), int(96 * self.scale)))
            except Exception:
                surface = None
            self.node_badges[key] = surface
        self.placeholder_lines = {
            "JMP DIAG_LEFT",
            "JMP DIAG_RIGHT",
            "JMP INIT_VOL",
            "JMP STREAM_ENTRY",
            "JMP DATA_CHECK",
            "BNE DATA_CHECK",
            "JMP OUTPUT_SAMPLE",
            "DATA_CHECK:",
            "OUTPUT_SAMPLE:",
        }
        self._prepare_modal_for_current_node()
        self._init_audio_assets()

    def _prepare_modal_for_current_node(self):
        node_number = self.page_index + 1
        node_entries: Dict[int, Dict[str, Any]] = {
            1: {
                "title": "NODE 01 // INIT_POWER",
                "lines": [
                    "Bring the LAPC-1 online by enabling $C400.",
                    "The card requires the activation byte #$01 to start the circuit logic. Load this immediate value into the Accumulator, then store it into the Master Power Register at $C400.",
                    "Code outline:",
                    "Typing in assmebly code on the first line type in the code that loads the accumulator with a single byte of data.",
                    "Then on the next line store that data into the Master Power Register at memory location $C400.",
                    "Press RUN (F5) to execute the code and two things should happen, firstly the simulated LED in Monitor should",
                    "turn green, then your local audio system should power up as well and the program will advance to the next Node.",
                    "DO NOT DELETE placeholder JMP this enables the execution to advance until INIT_POWER is written.",
                ],
            },
            2: {
                "title": "NODE 02 // DIAG_LEFT",
                "lines": [
                    "Time for the left channel diagnostic. Drive the speaker hot, keep the right side quiet, then advance.",
                    "Load #$FF into the accumulator and store it to $C401 to fire the loud test tone on the left speaker.",
                    "Swap to #$00 and store that value into $C402 so the right channel stays muted while you listen.",
                    "Glance at the monitor window, the left channel LED should light while the right stays dark.",
                    "Once you confirm the behavior, keep the placeholder jump in place so execution flows into Node 03.",
                ],
            },
            3: {
                "title": "NODE 03 // DIAG_RIGHT",
                "lines": [
                    "Mirror the diagnostic on the right channel so both speakers get checked before volume staging.",
                    "Reload #$FF and push it into $C402 to send the tone out of the right speaker.",
                    "Mute the left side by loading #$00 and storing it to $C401, keeps the test focused on the right.",
                    "Verify in the monitor that the right channel indicator pulses while the left remains quiet.",
                    "Leave the jump at the end so control proceeds into Node 04 once the test concludes.",
                ],
            },
            4: {
                "title": "NODE 04 // INIT_VOL",
                "lines": [
                    "Lock both channels to the neutral mix level before handing off to the streaming loop.",
                    "Load #$80 into the accumulator once, then store it into $C401 for the left channel.",
                    "Without reloading, store the same value into $C402 so the right matches the left.",
                    "Check the monitor registers, both channels should read #$80 when the writes land.",
                    "Keep the trailing jump that routes execution into Node 05; you need that pathway intact.",
                ],
            },
            5: {
                "title": "NODE 05 // STREAM_ENTRY",
                "lines": [
                    "Initialization sequence complete. This node transitions to the streaming loop.",
                    "The driver initialization (Nodes 1-4) is finished. Now we hand control to the",
                    "continuous packet streaming loop that will process audio data in real-time.",
                    "",
                    "Type a single instruction.",
                    "This unconditional jump routes execution to the DATA_CHECK label where the",
                    "streaming loop begins. Simple, but essential - don't overlook it!",
                ],
            },
            6: {
                "title": "NODE 06 // DATA_CHECK",
                "lines": [
                    "Here’s the busy-wait loop. Poll the data-ready register until a fresh sample arrives.",
                    "Read $C403 into the accumulator and compare it against the ready flag value #$01.",
                    "If the compare says not ready, branch straight back to the DATA_CHECK label and keep spinning.",
                    "When the flag finally equals #$01, fall through to Node 07 so you can process the waiting sample.",
                    "Keep the label and branch structure intact, they anchor the loop timing for the audio stream.",
                ],
            },
            7: {
                "title": "NODE 07 // OUTPUT_SAMPLE",
                "lines": [
                    "Move the audio packet from the buffer to both channels, then swing back to poll for the next byte.",
                    "Read the sample from $C800 into the accumulator, remember that register is read-only.",
                    "Store the value to $C401 for the left speaker, then immediately to $C402 for the right.",
                    "Kick execution back to DATA_CHECK so the loop keeps tempo with incoming packets.",
                    "Watch the monitor LEDs, both channels should pulse in sync as the loop runs.",
                    "",
                    "IMPORTANT: The audio stream you're about to enable contains banned content.",
                    "Keep your volume low and ensure you're alone. This transmission was never supposed to exist.",
                ],
            },
        }

        entries: List[Dict[str, Any]] = []
        node_entry = node_entries.get(node_number)
        if node_entry:
            entries.append(node_entry)
        entries.append(
            {
                "title": "IMPORTANT",
                "title_color": self.PINK,
                "lines": [
                    "Do not delete the pink placeholder code.",
                    "",
                    "SHORTCUTS",
                    "Scroll the chat dialogue with Up / Down arrows.",
                    "",
                    "F4: VIEW DOCUMENTATION",
                    "F7: RESET STATE",
                    "ESC: EXIT TO URGENT OPS",
                ],
                "line_color": self.PINK,
            }
        )
        self.modal_data = entries
        self.modal_step = 0
        self.modal_active = True

    def _prepare_success_modal_for_node(self, completed_node: int):
        """Prepare success modal content for a completed node."""
        success_messages: Dict[int, Dict[str, Any]] = {
            1: {
                "title": "NODE 01 COMPLETE // POWER ONLINE",
                "lines": [
                    "The LAPC-1 sound card is now powered and ready.",
                    "The master power register at $C400 is active, and the card's LED indicator confirms the circuit is live.",
                    "",
                    "You've successfully initialized the power rail. The system is ready for audio channel diagnostics.",
                ],
            },
            2: {
                "title": "NODE 02 COMPLETE // LEFT CHANNEL TESTED",
                "lines": [
                    "Left channel diagnostic complete. The speaker responded correctly to the test signal.",
                    "$C401 is configured and the right channel has been muted for isolation testing.",
                    "",
                    "Ready to mirror this test on the right channel.",
                ],
            },
            3: {
                "title": "NODE 03 COMPLETE // RIGHT CHANNEL TESTED",
                "lines": [
                    "Right channel diagnostic complete. Both speakers have been verified.",
                    "$C402 is configured and the left channel was properly muted during the test.",
                    "",
                    "Both audio channels are confirmed operational. Proceeding to volume initialization.",
                ],
            },
            4: {
                "title": "NODE 04 COMPLETE // VOLUME INITIALIZED",
                "lines": [
                    "Default stereo volume has been set. Both channels are locked to neutral gain ($80).",
                    "$C401 and $C402 are configured with baseline levels for clean audio streaming.",
                    "",
                    "Initialization sequence complete. Ready to enter the continuous streaming loop.",
                ],
            },
            5: {
                "title": "NODE 05 COMPLETE // STREAM ENTRY ESTABLISHED",
                "lines": [
                    "Stream entry point configured. Execution is now routed into the data polling loop.",
                    "The handoff from initialization to continuous operation is complete.",
                    "",
                    "The busy-wait loop is ready to begin monitoring for incoming audio packets.",
                ],
            },
            6: {
                "title": "NODE 06 COMPLETE // DATA CHECK LOOP ACTIVE",
                "lines": [
                    "Busy-wait polling loop is operational. The system is monitoring $C403 for data-ready signals.",
                    "The loop will spin until a packet arrives, then hand control to the output routine.",
                    "",
                    "Real-time packet detection is now active.",
                ],
            },
            7: {
                "title": "NODE 07 COMPLETE // OUTPUT STREAM ACTIVE",
                "lines": [
                    "Sample transfer routine is complete. The loop is reading from $C800 and driving both channels.",
                    "Audio packets are flowing through the system in real-time.",
                    "",
                    "The continuous streaming loop is fully operational.",
                ],
            },
        }
        
        entry = success_messages.get(completed_node)
        if entry:
            self.success_modal_data = [entry]
        else:
            self.success_modal_data = []
        self.success_modal_step = 0
        self.success_modal_active = True

    def _init_audio_assets(self):
        # Load Node 1 power-on sound
        sound_path = get_data_path("Urgent_Ops", "Audio", "On-Test.wav")
        print(f"DEBUG: Looking for audio file at: {sound_path}")
        print(f"DEBUG: File exists: {os.path.exists(sound_path)}")
        
        if os.path.exists(sound_path):
            try:
                if not pygame.mixer.get_init():
                    try:
                        pygame.mixer.init()
                        print("DEBUG: Mixer initialized successfully")
                    except Exception as mixer_error:
                        print(f"Warning: Unable to initialize mixer for On-Test.wav playback: {mixer_error}")
                        return
                else:
                    print("DEBUG: Mixer already initialized")
                self.power_on_sound = pygame.mixer.Sound(sound_path)
                print(f"DEBUG: Sound loaded successfully: {self.power_on_sound}")
            except Exception as sound_error:
                print(f"Warning: Failed to load On-Test.wav: {sound_error}")
                self.power_on_sound = None
        else:
            print(f"Warning: Audio/On-Test.wav not found at {sound_path}. Node 1 power-on sound disabled.")
            self.power_on_sound = None
        
        # Load Node 2 left channel test sound
        left_sound_path = get_data_path("Urgent_Ops", "Audio", "left-test-tune.wav")
        print(f"DEBUG: Looking for left test audio file at: {left_sound_path}")
        print(f"DEBUG: File exists: {os.path.exists(left_sound_path)}")
        
        if os.path.exists(left_sound_path):
            try:
                if not pygame.mixer.get_init():
                    try:
                        pygame.mixer.init()
                        print("DEBUG: Mixer initialized successfully for left test sound")
                    except Exception as mixer_error:
                        print(f"Warning: Unable to initialize mixer for left-test-tune.wav playback: {mixer_error}")
                        self.left_test_sound = None
                    else:
                        self.left_test_sound = pygame.mixer.Sound(left_sound_path)
                        print(f"DEBUG: Left test sound loaded successfully: {self.left_test_sound}")
                else:
                    self.left_test_sound = pygame.mixer.Sound(left_sound_path)
                    print(f"DEBUG: Left test sound loaded successfully: {self.left_test_sound}")
            except Exception as sound_error:
                print(f"Warning: Failed to load left-test-tune.wav: {sound_error}")
                self.left_test_sound = None
        else:
            print(f"Warning: Audio/left-test-tune.wav not found at {left_sound_path}. Node 2 left channel sound disabled.")
            self.left_test_sound = None
        
        # Load Node 3 right channel test sound
        right_sound_path = get_data_path("Urgent_Ops", "Audio", "right-test-tune.wav")
        print(f"DEBUG: Looking for right test audio file at: {right_sound_path}")
        print(f"DEBUG: File exists: {os.path.exists(right_sound_path)}")
        
        if os.path.exists(right_sound_path):
            try:
                if not pygame.mixer.get_init():
                    try:
                        pygame.mixer.init()
                        print("DEBUG: Mixer initialized successfully for right test sound")
                    except Exception as mixer_error:
                        print(f"Warning: Unable to initialize mixer for right-test-tune.wav playback: {mixer_error}")
                        self.right_test_sound = None
                    else:
                        self.right_test_sound = pygame.mixer.Sound(right_sound_path)
                        print(f"DEBUG: Right test sound loaded successfully: {self.right_test_sound}")
                else:
                    self.right_test_sound = pygame.mixer.Sound(right_sound_path)
                    print(f"DEBUG: Right test sound loaded successfully: {self.right_test_sound}")
            except Exception as sound_error:
                print(f"Warning: Failed to load right-test-tune.wav: {sound_error}")
                self.right_test_sound = None
        else:
            print(f"Warning: Audio/right-test-tune.wav not found at {right_sound_path}. Node 3 right channel sound disabled.")
            self.right_test_sound = None
        
        # Load Node 4 completion sound
        u1_sound_path = get_data_path("Urgent_Ops", "Audio", "u1.wav")
        print(f"DEBUG: Looking for u1 audio file at: {u1_sound_path}")
        print(f"DEBUG: File exists: {os.path.exists(u1_sound_path)}")
        
        if os.path.exists(u1_sound_path):
            try:
                if not pygame.mixer.get_init():
                    try:
                        pygame.mixer.init()
                        print("DEBUG: Mixer initialized successfully for u1 sound")
                    except Exception as mixer_error:
                        print(f"Warning: Unable to initialize mixer for u1.wav playback: {mixer_error}")
                        self.u1_sound = None
                    else:
                        self.u1_sound = pygame.mixer.Sound(u1_sound_path)
                        print(f"DEBUG: u1 sound loaded successfully: {self.u1_sound}")
                else:
                    self.u1_sound = pygame.mixer.Sound(u1_sound_path)
                    print(f"DEBUG: u1 sound loaded successfully: {self.u1_sound}")
            except Exception as sound_error:
                print(f"Warning: Failed to load u1.wav: {sound_error}")
                self.u1_sound = None
        else:
            print(f"Warning: Audio/u1.wav not found at {u1_sound_path}. Node 4 completion sound disabled.")
            self.u1_sound = None
        
        # Load Node 7 completion sound
        node7_sound_path = get_data_path("Urgent_Ops", "Audio", "NODE7.wav")
        print(f"DEBUG: Looking for NODE7 audio file at: {node7_sound_path}")
        print(f"DEBUG: File exists: {os.path.exists(node7_sound_path)}")
        
        if os.path.exists(node7_sound_path):
            try:
                if not pygame.mixer.get_init():
                    try:
                        pygame.mixer.init()
                        print("DEBUG: Mixer initialized successfully for NODE7 sound")
                    except Exception as mixer_error:
                        print(f"Warning: Unable to initialize mixer for NODE7.wav playback: {mixer_error}")
                        self.node7_sound = None
                    else:
                        self.node7_sound = pygame.mixer.Sound(node7_sound_path)
                        print(f"DEBUG: NODE7 sound loaded successfully: {self.node7_sound}")
                else:
                    self.node7_sound = pygame.mixer.Sound(node7_sound_path)
                    print(f"DEBUG: NODE7 sound loaded successfully: {self.node7_sound}")
            except Exception as sound_error:
                print(f"Warning: Failed to load NODE7.wav: {sound_error}")
                self.node7_sound = None
        else:
            print(f"Warning: Audio/NODE7.wav not found at {node7_sound_path}. Node 7 completion sound disabled.")
            self.node7_sound = None

    def _parse_immediate_byte(self, operand: str) -> int:
        if not operand or not operand.startswith('#'):
            raise ValueError("Immediate operand must begin with '#'.")
        literal = operand[1:]
        if literal.startswith('$'):
            literal = literal[1:]
        elif literal.lower().startswith('0x'):
            literal = literal[2:]
        literal = literal.strip()
        if not literal:
            raise ValueError("Immediate operand is missing a value.")
        return int(literal, 16) & 0xFF

    def _parse_absolute_address(self, operand: str) -> int:
        if not operand:
            raise ValueError("Address operand missing.")
        if operand.startswith('$'):
            literal = operand[1:]
        elif operand.lower().startswith('0x'):
            literal = operand[2:]
        else:
            raise ValueError("Absolute operand must use '$' or '0x' prefix.")
        literal = literal.strip()
        if not literal:
            raise ValueError("Absolute operand is missing a value.")
        return int(literal, 16)

    def _get_default_code(self):
        # *** CHALLENGE MODE: COMPLETELY BLANK. USER MUST TYPE EVERYTHING. ***
        return [
            [
                "; NODE 01: INIT_POWER (Power On Soundcard)",
                "",
                "JMP DIAG_LEFT",
            ],
            [
                "; NODE 02: DIAG_LEFT (Test Left Channel)",
                "",
                "JMP DIAG_RIGHT",
            ],
            [
                "; NODE 03: DIAG_RIGHT (Test Right Channel)",
                "",
                "JMP INIT_VOL",
            ],
            [
                "; NODE 04: INIT_VOL (Set Default Volume)",
                "",
                "JMP STREAM_ENTRY",
            ],
            [
                "; NODE 05: STREAM_ENTRY (Data Loop Start)",
                "",
                "",
            ],
            [
                "; NODE 06: DATA_CHECK (Busy Wait for $C403)",
                "",
                "DATA_CHECK:",
                "",
                "BNE DATA_CHECK",
                "JMP OUTPUT_SAMPLE",
            ],
            [
                "; NODE 07: OUTPUT_SAMPLE (Transfer Data $C800)",
                "",
                "OUTPUT_SAMPLE:",
                "",
                "JMP DATA_CHECK",
            ],
        ]

    def reset_state(self):
        """Re-initializes the CPU and simulation state."""
        self.cpu_state = {
            "A": 0x00,
            "PC": 0,
            "cycles": 0,
            "isRunning": False,
            "instructionIndex": 0,
            "Memory": {
                REG_MASTER_POWER: 0x00,
                REG_LEFT_CHANNEL: 0x00,
                REG_RIGHT_CHANNEL: 0x00,
                REG_DATA_READY: 0x00,
                REG_PACKET_BUFFER: 0x00,
            },
        }
        self.game_state = "EDITING"
        self.last_tick_time = pygame.time.get_ticks()
        self.zero_flag = False
        
        # Reset Code Editor to blanks
        self.code_areas_content = [lines[:] for lines in self._get_default_code()]
        
        self.editor_focus_node = 0
        self.cursor_pos = (1, 0)
        
        # Reset Data Stream (Initial samples)
        self.packet_queue = [0xAA, 0x99, 0xCC, 0x80, 0x70, 0x60, 0x55, 0x66] 
        self.data_ticks = 10 
        self.waveform_history = []
        
        # Reset video/completion state
        self.challenge_completed = False
        self.module_animation_timer = 0.0 # Reset animation timer
        self.video_frame = None # Clear video frame to show static logo instead
        if self.video_cap:
            self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, 0) # Reset video position
        
        # Note: Token removal is handled separately - only when F7 is pressed (explicit reset)
        # During initialization, tokens are preserved so progress can be restored

        self._power_led_prev_state = False

        # Reset to Node 1 (starting node)
        self.page_index = 0
        self.editor_focus_node = 0
        self.cursor_pos = (1, 0)  # Position cursor on first editable line (after comment)
        self.focus_target = "editor"
        self.control_focus = 0
        self._ensure_focus_visible()
        self._reset_chat_state()
        
        # Reset modal and briefing state - start fresh at Node 1
        self.modal_active = True
        self.modal_step = 0
        self.modal_scroll_offset = 0
        self.last_briefing_node = -1  # Reset so briefing will show for Node 1
        self.intro_sequence_started = False  # Reset intro sequence
        self._prepare_modal_for_current_node()
        
        # Reset success modal state
        self.success_modal_active = False
        self.success_modal_data = []
        self.success_modal_step = 0
        self.pending_node_switch = None
        
        # Reset node completion flags
        if hasattr(self, '_node_2_completed'):
            delattr(self, '_node_2_completed')
        if hasattr(self, '_node_3_completed'):
            delattr(self, '_node_3_completed')
        if hasattr(self, '_node_4_completed'):
            delattr(self, '_node_4_completed')
        if hasattr(self, '_node_5_completed'):
            delattr(self, '_node_5_completed')
        if hasattr(self, '_node_6_completed'):
            delattr(self, '_node_6_completed')
        if hasattr(self, '_node_7_completed'):
            delattr(self, '_node_7_completed')
        
        # Reset pending token grants
        self.pending_token_grants = []
        
        # Reset scroll offsets
        self.editor_scroll_offset = 0

        self.parse_code() # Initial parse
        self.cpu_state["instructionIndex"] = self.labels.get(self.node_labels[0], 0)
    
    def _remove_progress_tokens(self):
        """Remove all node completion tokens - only called when user explicitly resets (F7)."""
        if self.token_remover:
            node_tokens_to_remove = [
                "LAPC1A",
                "LAPC1_NODE1",
                "LAPC1_NODE2",
                "LAPC1_NODE3",
                "LAPC1_NODE4",
                "LAPC1_NODE5",
                "LAPC1_NODE6",
                "LAPC1_NODE7",
                "AUDIO_ON",
            ]
            for token in node_tokens_to_remove:
                self.token_remover(token)
    
    def _restore_led_states_from_tokens(self):
        """Restore LED states based on tokens the user has earned."""
        if not self.token_checker:
            return
        
        # Node 1: Power LED (C400)
        if self.token_checker("LAPC1_NODE1"):
            self.cpu_state["Memory"][REG_MASTER_POWER] = ACTIVATION_BYTE
            self._power_led_prev_state = True
        
        # Node 4 takes precedence over nodes 2-3 (if node 4 is complete, channels are at DEFAULT_VOLUME)
        # Node 4: Both channels at default volume
        if self.token_checker("LAPC1_NODE4"):
            if self.cpu_state["Memory"][REG_MASTER_POWER] == ACTIVATION_BYTE:
                self.cpu_state["Memory"][REG_LEFT_CHANNEL] = DEFAULT_VOLUME
                self.cpu_state["Memory"][REG_RIGHT_CHANNEL] = DEFAULT_VOLUME
        else:
            # Node 2: Left channel LED (C401) - requires power on, only if node 4 not complete
            if self.token_checker("LAPC1_NODE2"):
                if self.cpu_state["Memory"][REG_MASTER_POWER] == ACTIVATION_BYTE:
                    # Set left channel to a value that lights the LED (non-zero)
                    self.cpu_state["Memory"][REG_LEFT_CHANNEL] = 0xFF
            
            # Node 3: Right channel LED (C402) - requires power on, only if node 4 not complete
            if self.token_checker("LAPC1_NODE3"):
                if self.cpu_state["Memory"][REG_MASTER_POWER] == ACTIVATION_BYTE:
                    # Set right channel to a value that lights the LED (non-zero)
                    self.cpu_state["Memory"][REG_RIGHT_CHANNEL] = 0xFF
        
        # Node 5: Stream entry reached - no LED, but mark as completed
        if self.token_checker("LAPC1_NODE5"):
            if not hasattr(self, '_node_5_completed'):
                self._node_5_completed = True
        
        # Node 6: Data check loop reached - no LED, but mark as completed
        if self.token_checker("LAPC1_NODE6"):
            if not hasattr(self, '_node_6_completed'):
                self._node_6_completed = True
        
        # Node 7: Output sample loop reached - no LED, but mark as completed
        if self.token_checker("LAPC1_NODE7"):
            if not hasattr(self, '_node_7_completed'):
                self._node_7_completed = True
        
        # If all nodes completed (AUDIO_ON), ensure full state is restored
        if self.token_checker("AUDIO_ON"):
            if self.cpu_state["Memory"][REG_MASTER_POWER] == ACTIVATION_BYTE:
                self.cpu_state["Memory"][REG_LEFT_CHANNEL] = DEFAULT_VOLUME
                self.cpu_state["Memory"][REG_RIGHT_CHANNEL] = DEFAULT_VOLUME
                # Mark all nodes as completed
                self._node_2_completed = True
                self._node_3_completed = True
                self._node_4_completed = True
                self._node_5_completed = True
                self._node_6_completed = True
                self._node_7_completed = True
    
    def _determine_starting_node(self) -> int:
        """Determine which node to start on based on completed tokens.
        Returns the index (0-6) of the first incomplete node, or 0 if all complete."""
        if not self.token_checker:
            return 0
        
        # Check each node in order (1-7, indices 0-6)
        # Node 1 (index 0)
        if not self.token_checker("LAPC1_NODE1"):
            return 0
        
        # Node 2 (index 1)
        if not self.token_checker("LAPC1_NODE2"):
            return 1
        
        # Node 3 (index 2)
        if not self.token_checker("LAPC1_NODE3"):
            return 2
        
        # Node 4 (index 3)
        if not self.token_checker("LAPC1_NODE4"):
            return 3
        
        # Node 5 (index 4)
        if not self.token_checker("LAPC1_NODE5"):
            return 4
        
        # Node 6 (index 5)
        if not self.token_checker("LAPC1_NODE6"):
            return 5
        
        # Node 7 (index 6)
        if not self.token_checker("LAPC1_NODE7"):
            return 6
        
        # All nodes completed - start at node 1 (index 0) for review
        return 0

    # ... (parse_code, tick_data_stream remain the same) ...

    def parse_code(self) -> None:
        """Parses the multi-module code into a single instruction list and label map."""
        self.code_lines_flat = []
        self.labels = {}
        instruction_index = 0
        
        for node_idx, node_lines in enumerate(self.code_areas_content):
            node_label_name = self.node_labels[node_idx]
            
            # The label for the Node start is implicitly the first executable instruction in the node
            self.labels[node_label_name] = instruction_index

            for line_idx, line in enumerate(node_lines):
                line = line.split(';')[0].strip()
                if not line: continue

                parts = line.split()
                if not parts: continue
                
                # Handle standalone labels (e.g., 'DATA_CHECK:')
                if parts[0].endswith(':'):
                    label = parts[0][:-1].upper()
                    self.labels[label] = instruction_index
                    parts.pop(0)
                    if not parts: continue 

                if not parts: continue

                opcode = parts[0].upper()
                operand = parts[1] if len(parts) > 1 else None

                self.code_lines_flat.append({
                    "opcode": opcode,
                    "operand_str": operand,
                    "node_idx": node_idx,
                    "line_idx": line_idx,
                    "global_idx": instruction_index
                })
                instruction_index += 1
        
        # Second pass to resolve JMP/BNE targets
        for instr in self.code_lines_flat:
            operand = instr.get("operand_str")
            if not operand: continue
                
            if instr["opcode"] in ["JMP", "BNE"]:
                target = operand.upper()
                if target in self.labels:
                    instr["target_index"] = self.labels[target]
                else:
                    self.set_error(f"Unresolved label: {target}", instr["node_idx"], instr["line_idx"])
                    return

    def tick_data_stream(self):
        """Simulates incoming data packets."""
        if self.game_state not in ("RUNNING", "PAUSED", "EDITING"): return
        
        if self.cpu_state["Memory"][REG_MASTER_POWER] == ACTIVATION_BYTE:
            self.data_ticks -= 1
            if self.data_ticks <= 0:
                # Use self.packet_queue, not self.packetQueue
                if self.packet_queue:
                    next_sample = self.packet_queue.pop(0)
                    self.cpu_state["Memory"][REG_PACKET_BUFFER] = next_sample
                    self.cpu_state["Memory"][REG_DATA_READY] = READY_STATE
                    
                    # Loop the packet queue for continuous streaming
                    self.packet_queue.append(next_sample)
                    
                    self.data_ticks = pygame.time.get_ticks() % 9 + 12
                else:
                    self.cpu_state["Memory"][REG_DATA_READY] = 0x00 # No more data
            else:
                self.cpu_state["Memory"][REG_DATA_READY] = 0x00

    def execute_instruction(self):
        """Executes one assembly instruction."""
        idx = self.cpu_state["instructionIndex"]
        if idx >= len(self.code_lines_flat):
            self.set_error("Execution terminated: End of program reached.", 0, 0)
            return

        instr = self.code_lines_flat[idx]
        self.cpu_state["cycles"] += 1
        next_idx = idx + 1
        
        # Check if the current instruction is a terminating jump (JMP or BNE) for a module
        # and calculate the destination index BEFORE execution.
        current_node = instr["node_idx"]
        jumped_to_new_module = False
        
        if instr["opcode"] in ["JMP", "BNE"]:
            target_idx = instr["target_index"]
            if target_idx < len(self.code_lines_flat):
                target_node = self.code_lines_flat[target_idx]["node_idx"]
                if target_node > current_node:
                    # Successful jump from Module X to Module Y where Y > X
                    jumped_to_new_module = True

        
        opcode = instr["opcode"]
        operand_str = instr["operand_str"]
        
        zero_flag_check = self.zero_flag
        
        try:
            if opcode == "LDA":
                if operand_str and operand_str.startswith('#'):
                    self.cpu_state["A"] = self._parse_immediate_byte(operand_str)
                elif operand_str and (operand_str.startswith('$') or operand_str.lower().startswith('0x')):
                    addr = self._parse_absolute_address(operand_str)
                    # Check if address is a known register
                    if addr in self.cpu_state["Memory"]:
                        self.cpu_state["A"] = self.cpu_state["Memory"][addr] & 0xFF
                    else:
                        raise ValueError(f"Invalid Address: {operand_str}")
                else:
                    raise ValueError("LDA requires immediate (#$XX) or absolute ($C400) addressing.")
            
            elif opcode == "STA":
                if not operand_str or not (operand_str.startswith('$') or operand_str.lower().startswith('0x')):
                    raise ValueError("STA requires absolute address ($C400).")
                addr = self._parse_absolute_address(operand_str)
                if addr in [REG_DATA_READY, REG_PACKET_BUFFER]:
                    raise ValueError("STA: Write attempt to read-only register.")
                if addr in self.cpu_state["Memory"]:
                    if addr == REG_MASTER_POWER and self.cpu_state["A"] not in (0x00, ACTIVATION_BYTE):
                        raise ValueError("Power rail requires byte literal: use '#$01' for ON.")
                    self.cpu_state["Memory"][addr] = self.cpu_state["A"]
                    
                    # Check for node completion after STA operations
                    if self.game_state not in ("SUCCESS", "ERROR") and not self.success_modal_active:
                        # Node 2 completion: Left channel written (C401) while executing Node 2's code (index 1)
                        if addr == REG_LEFT_CHANNEL and current_node == 1 and not hasattr(self, '_node_2_completed'):
                            self._node_2_completed = True
                            # Play left channel test sound
                            print(f"DEBUG: Node 2 completed! Attempting to play left test sound...")
                            print(f"DEBUG: left_test_sound is: {self.left_test_sound}")
                            if self.left_test_sound:
                                try:
                                    # Ensure mixer is initialized before playing
                                    if not pygame.mixer.get_init():
                                        print("DEBUG: Mixer not initialized, initializing now...")
                                        pygame.mixer.init()
                                    print("DEBUG: Calling left_test_sound.play()...")
                                    channel = self.left_test_sound.play()
                                    if channel:
                                        self.active_audio_channels.append(channel)
                                    print("DEBUG: Left test sound play() called successfully")
                                except Exception as play_error:
                                    print(f"Warning: Unable to play left-test-tune.wav: {play_error}")
                                    import traceback
                                    traceback.print_exc()
                            else:
                                print("DEBUG: left_test_sound is None, skipping playback")
                            # Grant token for Node 2 LED
                            if "LAPC1_NODE2" not in self.pending_token_grants:
                                self.pending_token_grants.append("LAPC1_NODE2")
                            self._prepare_success_modal_for_node(2)
                            self.pending_node_switch = 3 - 1  # Switch to node 3 (0-based index 2) after completing node 2
                            # No parrot animation for individual node completion
                        
                        # Node 3 completion: Right channel written (C402) while executing Node 3's code (index 2)
                        elif addr == REG_RIGHT_CHANNEL and current_node == 2 and not hasattr(self, '_node_3_completed'):
                            self._node_3_completed = True
                            # Play right channel test sound
                            print(f"DEBUG: Node 3 completed! Attempting to play right test sound...")
                            print(f"DEBUG: right_test_sound is: {self.right_test_sound}")
                            if self.right_test_sound:
                                try:
                                    # Ensure mixer is initialized before playing
                                    if not pygame.mixer.get_init():
                                        print("DEBUG: Mixer not initialized, initializing now...")
                                        pygame.mixer.init()
                                    print("DEBUG: Calling right_test_sound.play()...")
                                    channel = self.right_test_sound.play()
                                    if channel:
                                        self.active_audio_channels.append(channel)
                                    print("DEBUG: Right test sound play() called successfully")
                                except Exception as play_error:
                                    print(f"Warning: Unable to play right-test-tune.wav: {play_error}")
                                    import traceback
                                    traceback.print_exc()
                            else:
                                print("DEBUG: right_test_sound is None, skipping playback")
                            # Grant token for Node 3 LED
                            if "LAPC1_NODE3" not in self.pending_token_grants:
                                self.pending_token_grants.append("LAPC1_NODE3")
                            self._prepare_success_modal_for_node(3)
                            self.pending_node_switch = 4 - 1  # Switch to node 4 (0-based index 3) after completing node 3
                            # No parrot animation for individual node completion
                        
                        # Node 4 completion: Both channels set to default volume while executing Node 4's code (index 3)
                        elif addr in (REG_LEFT_CHANNEL, REG_RIGHT_CHANNEL) and current_node == 3 and \
                             self.cpu_state["Memory"].get(REG_LEFT_CHANNEL) == DEFAULT_VOLUME and \
                             self.cpu_state["Memory"].get(REG_RIGHT_CHANNEL) == DEFAULT_VOLUME and \
                             not hasattr(self, '_node_4_completed'):
                            self._node_4_completed = True
                            # Play u1.wav sound
                            print(f"DEBUG: Node 4 completed! Attempting to play u1 sound...")
                            print(f"DEBUG: u1_sound is: {self.u1_sound}")
                            if self.u1_sound:
                                try:
                                    # Ensure mixer is initialized before playing
                                    if not pygame.mixer.get_init():
                                        print("DEBUG: Mixer not initialized, initializing now...")
                                        pygame.mixer.init()
                                    print("DEBUG: Calling u1_sound.play()...")
                                    channel = self.u1_sound.play()
                                    if channel:
                                        self.active_audio_channels.append(channel)
                                    print("DEBUG: u1 sound play() called successfully")
                                except Exception as play_error:
                                    print(f"Warning: Unable to play u1.wav: {play_error}")
                                    import traceback
                                    traceback.print_exc()
                            else:
                                print("DEBUG: u1_sound is None, skipping playback")
                            # Grant token for Node 4 LED
                            if "LAPC1_NODE4" not in self.pending_token_grants:
                                self.pending_token_grants.append("LAPC1_NODE4")
                            self._prepare_success_modal_for_node(4)
                            self.pending_node_switch = 5 - 1  # Switch to node 5 (0-based index 4) after completing node 4
                            # No parrot animation for individual node completion
                else:
                    raise ValueError(f"Invalid Address: {operand_str}")

            elif opcode == "CMP":
                if operand_str and operand_str.startswith('#'):
                    val = self._parse_immediate_byte(operand_str)
                    self.zero_flag = (self.cpu_state["A"] == val)
                else:
                    raise ValueError(f"CMP requires immediate value.")
            
            elif opcode == "JMP":
                next_idx = instr["target_index"]
            
            elif opcode == "BNE":
                if not zero_flag_check:
                    next_idx = instr["target_index"]
            
            elif opcode == "NOP":
                # No operation, PC increments
                pass
            
            else:
                raise ValueError(f"Invalid Opcode: {opcode}")
            
        except Exception as e:
            self.set_error(f"Runtime Error: {str(e)}", instr["node_idx"], instr["line_idx"])
            return

        self.cpu_state["instructionIndex"] = next_idx
        
        # NOTE: Animation is only triggered on final challenge completion, not on individual node jumps
        # Individual node completion animations were removed to reduce frequency
        
        # Check for individual node completion (Nodes 5-7 via jumps)
        # Nodes 2-4 are handled in STA handler above
        # Only check if we haven't already completed this node and we're not in SUCCESS state
        if self.game_state not in ("SUCCESS", "ERROR") and not self.success_modal_active and jumped_to_new_module:
            # Determine target node if we jumped to a new module
            target_node_idx = None
            if next_idx < len(self.code_lines_flat):
                target_node_idx = self.code_lines_flat[next_idx]["node_idx"]
            
            completed_node = None
            
            # Node 5 completion: Execution reaches STREAM_ENTRY (jump to node 5, which is index 4)
            if target_node_idx == 4 and not hasattr(self, '_node_5_completed'):
                completed_node = 5
                self._node_5_completed = True
                # Grant token for Node 5 LED
                if "LAPC1_NODE5" not in self.pending_token_grants:
                    self.pending_token_grants.append("LAPC1_NODE5")
            
            # Node 6 completion: Execution reaches DATA_CHECK (jump to node 6, which is index 5)
            elif target_node_idx == 5 and not hasattr(self, '_node_6_completed'):
                completed_node = 6
                self._node_6_completed = True
                # Grant token for Node 6 LED
                if "LAPC1_NODE6" not in self.pending_token_grants:
                    self.pending_token_grants.append("LAPC1_NODE6")
            
            # Node 7 completion: Execution reaches OUTPUT_SAMPLE (jump to node 7, which is index 6)
            elif target_node_idx == 6 and not hasattr(self, '_node_7_completed'):
                completed_node = 7
                self._node_7_completed = True
                # Grant token for Node 7 LED
                if "LAPC1_NODE7" not in self.pending_token_grants:
                    self.pending_token_grants.append("LAPC1_NODE7")
                # Warning about banned content before audio starts
                self._queue_chat_message("FINAL WARNING: The stream is about to go live. Banned content incoming. Keep it quiet and make sure you're alone.", "UNCLE-AM")
                self.chat_next_queue_time = pygame.time.get_ticks() + 100
                self._begin_next_queued_message()
                # Play Node 7 completion sound (banned song)
                print(f"DEBUG: Node 7 completed! Attempting to play NODE7.wav...")
                print(f"DEBUG: node7_sound is: {self.node7_sound}")
                if self.node7_sound:
                    try:
                        # Ensure mixer is initialized before playing
                        if not pygame.mixer.get_init():
                            print("DEBUG: Mixer not initialized, initializing now...")
                            pygame.mixer.init()
                        print("DEBUG: Calling node7_sound.play()...")
                        channel = self.node7_sound.play()
                        if channel:
                            self.active_audio_channels.append(channel)
                        print("DEBUG: NODE7.wav play() called successfully")
                    except Exception as play_error:
                        print(f"Warning: Unable to play NODE7.wav: {play_error}")
                        import traceback
                        traceback.print_exc()
                else:
                    print("DEBUG: node7_sound is None, skipping playback")
            
            # Trigger success modal for completed node
            if completed_node:
                self._prepare_success_modal_for_node(completed_node)
                self.pending_node_switch = completed_node  # Move to next node (0-based index)
                # No parrot animation for individual node completion
        
        # Check for SUCCESS (Full Challenge Completion)
        if next_idx == self.labels.get("DATA_CHECK", -1) and self.cpu_state["cycles"] > 10:
            if self.cpu_state["Memory"][REG_MASTER_POWER] == ACTIVATION_BYTE and \
               self.cpu_state["Memory"][REG_LEFT_CHANNEL] == DEFAULT_VOLUME and \
               self.cpu_state["Memory"][REG_RIGHT_CHANNEL] == DEFAULT_VOLUME and \
               self.game_state != "SUCCESS":

                self.game_state = "SUCCESS"
                self.cpu_state["isRunning"] = False

                self.challenge_completed = True
                # Start parrot animation for full challenge completion
                self.module_animation_timer = self.ANIMATION_DURATION
                if self.video_cap:
                    self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

                self._queue_chat_message("LAPC-1 DRIVER ONLINE. I'M GETTING AUDIO FROM YOUR END, FULL STEREO! AMAZING.", "UNCLE-AM")
                self._queue_chat_message("That's the entire driver, from power-on to a continuous, real-time sample loop. Flawless I/O timing.", "UNCLE-AM")
                self._queue_chat_message("With the audio sub-system online, we can finally get the BBS Radio feed going. Stand by for the next operational brief, hacker. That was seriously impressive work.", "UNCLE-AM")
                self.chat_next_queue_time = pygame.time.get_ticks() + 100
                self._begin_next_queued_message()

                # Grant AUDIO_ON token for completing all 7 nodes
                if "AUDIO_ON" not in self.pending_token_grants:
                    self.pending_token_grants.append("AUDIO_ON")

                self.set_success("Initialization complete! Driver ready for continuous streaming. (Task 101 Cleared)")


    # --- Pygame Lifecycle Methods ---

    def handle_event(self, event):
        """Handles Pygame events for the game."""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self.success_modal_active or self.modal_active:
                    self.exit_requested = True
                    return "EXIT" # Exit from modal
                
                self.exit_requested = True
                return "EXIT"
            
            # Success Modal Handling (takes priority)
            if self.success_modal_active:
                if event.key in (pygame.K_TAB, pygame.K_RETURN, pygame.K_SPACE):
                    if self.success_modal_step < len(self.success_modal_data) - 1:
                        self.success_modal_step += 1
                        self.modal_scroll_offset = 0  # Reset scroll when moving to next modal step
                    else:
                        self.success_modal_active = False
                        self.success_modal_step = 0
                        self.modal_scroll_offset = 0  # Reset scroll when modal closes
                        # Switch to pending node and show its modal
                        if self.pending_node_switch is not None:
                            self._switch_to_page(self.pending_node_switch)
                            self.pending_node_switch = None
                return
            
            # Regular Modal Handling
            if self.modal_active:
                if event.key in (pygame.K_TAB, pygame.K_RETURN, pygame.K_SPACE):
                    if self.modal_step < len(self.modal_data) - 1:
                        self.modal_step += 1
                        self.modal_scroll_offset = 0  # Reset scroll when moving to next modal step
                    else:
                        self.modal_active = False
                        self.modal_step = 0
                        self.modal_scroll_offset = 0  # Reset scroll when modal closes
                        # Only start intro sequence if at Node 1 and not already started
                        # For later nodes, briefing was already shown during initialization
                        if self.page_index == 0 and not self.intro_sequence_started:
                            self._start_intro_sequence()
                return
            
            if event.key == pygame.K_TAB:
                shift = bool(pygame.key.get_mods() & pygame.KMOD_SHIFT)
                self._advance_focus_cycle(backwards=shift)
                return

            if self.focus_target == "chat":
                if event.key == pygame.K_BACKSPACE:
                    if self.chat_input:
                        self.chat_input = self.chat_input[:-1]
                    return
                if event.key == pygame.K_RETURN:
                    self._submit_chat_message()
                    return
                if event.key == pygame.K_UP:
                    scroll_step = max(self.font_tiny.get_linesize(), 1)
                    self.chat_follow_latest = False
                    self.chat_scroll_offset = max(0, self.chat_scroll_offset - scroll_step)
                    return
                if event.key == pygame.K_DOWN:
                    scroll_step = max(self.font_tiny.get_linesize(), 1)
                    self.chat_follow_latest = False
                    self.chat_scroll_offset = min(self.chat_scroll_offset + scroll_step, self.chat_scroll_limit)
                    if self.chat_scroll_offset >= self.chat_scroll_limit:
                        self.chat_follow_latest = True
                    return
                # Handle text input for chat
                if event.unicode and event.unicode not in ("\r", "\n") and event.unicode.isprintable():
                    if len(self.chat_input) < 120:
                        self.chat_input += event.unicode
                    return
            
            # Handle scrolling for modals only (editor uses arrows for cursor movement)
            if event.key == pygame.K_UP:
                if self.modal_active or self.success_modal_active:
                    scroll_step = max(self.font_tiny.get_linesize(), 1)
                    self.modal_scroll_offset = max(0, self.modal_scroll_offset - scroll_step)
                    return
                # Editor focus: let cursor movement handle UP arrow (don't scroll)
            if event.key == pygame.K_DOWN:
                if self.modal_active or self.success_modal_active:
                    scroll_step = max(self.font_tiny.get_linesize(), 1)
                    self.modal_scroll_offset = min(self.modal_scroll_offset + scroll_step, self.modal_scroll_limit)
                    return
                # Editor focus: let cursor movement handle DOWN arrow (don't scroll)
            
            if self.focus_target == "controls":
                if event.key in (pygame.K_LEFT, pygame.K_UP):
                    self.control_focus = (self.control_focus - 1) % len(self.control_labels)
                    return
                if event.key in (pygame.K_RIGHT, pygame.K_DOWN):
                    self.control_focus = (self.control_focus + 1) % len(self.control_labels)
                    return
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    control = self.control_labels[self.control_focus]
                    self._activate_control(control)
                    return

            # F5: Run/Pause
            if event.key == pygame.K_F5:
                if self.game_state == "RUNNING":
                    self.cpu_state["isRunning"] = False
                    self.game_state = "PAUSED"
                elif self.game_state in ("EDITING", "PAUSED", "ERROR"):
                    self.parse_code()
                    if self.game_state != "ERROR":
                        self.cpu_state["isRunning"] = True
                        self.game_state = "RUNNING"
            
            
            # F7: Reset (full reset including token removal)
            elif event.key == pygame.K_F7:
                self._remove_progress_tokens()  # Remove tokens first
                self.reset_state()  # Then reset state
                # Don't restore LED states after reset - user is starting fresh
                # All LEDs should be off, power is shut down

            # Handle editor input - also allow ERROR state for TAB/ENTER handling
            if self.focus_target == "editor" or self.game_state == "ERROR":
                self._handle_editor_input(event)
            
        return None

    # --- External Interface for main.py ---
    def _handle_editor_input(self, event):
        """Handles text input and navigation within the editor modules."""
        if event.type == pygame.KEYDOWN:
            key_name = pygame.key.name(event.key) if hasattr(pygame.key, 'name') else str(event.key)
            print(f"[DEBUG] _handle_editor_input called: key={key_name} (K_RETURN={pygame.K_RETURN}), game_state={self.game_state}, focus_target={self.focus_target}")
        # Allow ERROR state for TAB navigation and ENTER to clear error
        # Also allow if focus_target is not editor but we're in ERROR state (for TAB/ENTER handling)
        if self.game_state not in ("EDITING", "PAUSED", "ERROR"):
            print(f"[DEBUG] _handle_editor_input: Early return - game_state {self.game_state} not in allowed states")
            return
        
        # Handle TAB in ERROR state to focus on error node
        if self.game_state == "ERROR" and event.type == pygame.KEYDOWN and event.key == pygame.K_TAB:
            print(f"[DEBUG] TAB pressed in ERROR state")
            print(f"[DEBUG] Error node/line: {getattr(self, 'error_node_idx', 'N/A')}/{getattr(self, 'error_line_idx', 'N/A')}")
            self.focus_target = "editor"  # Ensure editor is focused
            if hasattr(self, 'error_node_idx') and hasattr(self, 'error_line_idx'):
                self.editor_focus_node = self.error_node_idx
                # Position cursor at end of error line
                node_lines = self.code_areas_content[self.editor_focus_node]
                safe_line_idx = max(0, min(self.error_line_idx, len(node_lines) - 1))
                error_line = node_lines[safe_line_idx]
                self.cursor_pos = (safe_line_idx, len(error_line))
                print(f"[DEBUG] TAB: Focused node {self.editor_focus_node}, positioned cursor at line {safe_line_idx}, pos {len(error_line)}")
            else:
                print(f"[DEBUG] TAB: WARNING - error_node_idx or error_line_idx not found!")
            return
        
        # Handle ENTER in ERROR state to reset CPU and return to editing
        if self.game_state == "ERROR" and event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            print(f"[DEBUG] ENTER pressed in ERROR state")
            print(f"[DEBUG] Current game_state: {self.game_state}")
            print(f"[DEBUG] Current editor_focus_node: {self.editor_focus_node}")
            print(f"[DEBUG] Error node/line: {getattr(self, 'error_node_idx', 'N/A')}/{getattr(self, 'error_line_idx', 'N/A')}")
            
            # Reset all CPU state except code text
            # Reset Accumulator
            self.cpu_state["A"] = 0x00
            print(f"[DEBUG] Reset A to: {self.cpu_state['A']}")
            
            # Reset PC INDEX (instructionIndex)
            self.cpu_state["instructionIndex"] = 0
            print(f"[DEBUG] Reset instructionIndex to: {self.cpu_state['instructionIndex']}")
            
            # Reset CYCLES
            self.cpu_state["cycles"] = 0
            print(f"[DEBUG] Reset cycles to: {self.cpu_state['cycles']}")
            
            # Reset zero flag
            self.zero_flag = False
            print(f"[DEBUG] Reset zero_flag to: {self.zero_flag}")
            
            # Reset Memory registers (but keep code text intact)
            self.cpu_state["Memory"][REG_MASTER_POWER] = 0x00
            self.cpu_state["Memory"][REG_LEFT_CHANNEL] = 0x00
            self.cpu_state["Memory"][REG_RIGHT_CHANNEL] = 0x00
            self.cpu_state["Memory"][REG_DATA_READY] = 0x00
            self.cpu_state["Memory"][REG_PACKET_BUFFER] = 0x00
            print(f"[DEBUG] Reset all memory registers")
            
            # Reset isRunning flag
            self.cpu_state["isRunning"] = False
            print(f"[DEBUG] Reset isRunning to: {self.cpu_state['isRunning']}")
            
            # Clear error state and return to EDITING
            self.game_state = "EDITING"
            self.focus_target = "editor"  # Ensure editor is focused
            print(f"[DEBUG] Changed game_state to: {self.game_state}")
            
            # Restore normal status message
            if hasattr(self, '_original_get_status_message'):
                self._get_status_message = self._original_get_status_message
                print(f"[DEBUG] Restored original status message")
            
            # Position cursor at end of error line
            if hasattr(self, 'error_node_idx') and hasattr(self, 'error_line_idx'):
                self.editor_focus_node = self.error_node_idx
                node_lines = self.code_areas_content[self.editor_focus_node]
                safe_line_idx = max(0, min(self.error_line_idx, len(node_lines) - 1))
                error_line = node_lines[safe_line_idx]
                self.cursor_pos = (safe_line_idx, len(error_line))
                print(f"[DEBUG] Positioned cursor at node {self.editor_focus_node}, line {safe_line_idx}, pos {len(error_line)}")
            else:
                print(f"[DEBUG] WARNING: error_node_idx or error_line_idx not found!")
            
            print(f"[DEBUG] ENTER handler complete, returning early")
            return
        
        # Normal editor input handling - require focus_target to be "editor"
        if self.focus_target != "editor":
            return

        node_idx = self.editor_focus_node
        lines = self.code_areas_content[node_idx]
        current_line_idx, cursor_char_idx = self.cursor_pos
        
        # Ensure indices are within bounds
        current_line_idx = max(0, min(len(lines) - 1, current_line_idx))
        current_line = lines[current_line_idx]
        cursor_char_idx = max(0, min(len(current_line), cursor_char_idx))
        
        # Update line content and cursor pos
        self.cursor_pos = self._update_cursor_and_line(event, lines, current_line_idx, cursor_char_idx, node_idx)

    def _update_cursor_and_line(self, event, lines, current_line_idx, cursor_char_idx, node_idx):
        """Helper function for editor input logic."""
        new_row = current_line_idx
        new_char_idx = cursor_char_idx
        
        current_line = lines[current_line_idx]

        if event.key == pygame.K_UP:
            # Move cursor up within current node only
            if current_line_idx > 0:
                new_row = current_line_idx - 1
                new_char_idx = min(cursor_char_idx, len(lines[new_row]))
            # Stay at top line if already at first line

        elif event.key == pygame.K_DOWN:
            # Move cursor down within current node only
            if current_line_idx < len(lines) - 1:
                new_row = current_line_idx + 1
                new_char_idx = min(cursor_char_idx, len(lines[new_row]))
            # Stay at bottom line if already at last line
        
        elif event.key == pygame.K_BACKSPACE:
            if cursor_char_idx > 0:
                current_line = current_line[:cursor_char_idx - 1] + current_line[cursor_char_idx:]
                lines[current_line_idx] = current_line
                new_char_idx = cursor_char_idx - 1
            # Merge line up if at start of line
            elif current_line_idx > 0:
                 prev_line = lines.pop(current_line_idx - 1)
                 lines[current_line_idx - 1] = prev_line + current_line
                 new_row = current_line_idx - 1
                 new_char_idx = len(prev_line)

        elif event.key == pygame.K_RETURN:
            before_cursor = current_line[:cursor_char_idx].rstrip() # Trim right space/tab on current line
            after_cursor = current_line[cursor_char_idx:].lstrip() # Trim left space/tab on new line
            
            lines[current_line_idx] = before_cursor
            lines.insert(current_line_idx + 1, after_cursor)
            new_row = current_line_idx + 1
            new_char_idx = 0

        elif event.key == pygame.K_LEFT:
            new_char_idx = max(0, cursor_char_idx - 1)
        elif event.key == pygame.K_RIGHT:
            new_char_idx = min(len(current_line), cursor_char_idx + 1)
        elif event.unicode and event.unicode.isprintable():
            # Only allow a maximum number of lines (12 per node)
            if len(lines) < 12:
                new_line = current_line[:cursor_char_idx] + event.unicode.upper() + current_line[cursor_char_idx:]
                lines[current_line_idx] = new_line
                new_char_idx = cursor_char_idx + 1
                
        return (new_row, new_char_idx)

    def _cycle_editor_focus(self, step: int):
        """Move the editor focus between modules using TAB navigation."""
        visible = self._get_node_indices_for_page(self.page_index)
        if not visible:
            return

        if self.editor_focus_node not in visible:
            self.editor_focus_node = visible[0]
        else:
            index = visible.index(self.editor_focus_node)
            index = (index + step) % len(visible)
            self.editor_focus_node = visible[index]

        self.cursor_pos = (0, 0)
        self._reset_cursor_for_focus()

    def _advance_page(self, delta: int):
        """Move to another node page."""
        total = len(self.code_areas_content)
        if total == 0:
            return
        self.page_index = (self.page_index + delta) % total
        self.editor_focus_node = self.page_index
        
        # Set cursor position based on node type
        node_lines = self.code_areas_content[self.page_index]
        if self.page_index == 5:  # Node 6 (index 5) - has DATA_CHECK: label
            # Find the label line and position cursor on the blank line after it
            label_line_idx = -1
            for i, line in enumerate(node_lines):
                if line.strip().endswith(":"):
                    label_line_idx = i
                    break
            if label_line_idx >= 0 and label_line_idx + 1 < len(node_lines):
                self.cursor_pos = (label_line_idx + 1, 0)  # Position after label
            else:
                self.cursor_pos = (2, 0)  # Fallback to line 2
        elif self.page_index == 6:  # Node 7 (index 6) - has OUTPUT_SAMPLE: label
            # Find the label line and position cursor on the blank line after it
            label_line_idx = -1
            for i, line in enumerate(node_lines):
                if line.strip().endswith(":"):
                    label_line_idx = i
                    break
            if label_line_idx >= 0 and label_line_idx + 1 < len(node_lines):
                self.cursor_pos = (label_line_idx + 1, 0)  # Position after label
            else:
                self.cursor_pos = (2, 0)  # Fallback to line 2
        else:
            # For nodes without labels (1-5), cursor goes to line 1 (blank line after comment)
            self.cursor_pos = (1, 0)
        
        # Ensure focus is on editor and game state allows editing
        self.focus_target = "editor"
        self.game_state = "EDITING"  # Set to editing mode so cursor is visible
        self._ensure_focus_visible()
        self._push_node_briefing()
        self._prepare_modal_for_current_node()

    def _switch_to_page(self, target_index: int):
        """Jump directly to the specified node page."""
        if not (0 <= target_index < len(self.code_areas_content)):
            return
        if self.page_index == target_index:
            return
        self.page_index = target_index
        self.editor_focus_node = target_index
        self.editor_scroll_offset = 0  # Reset scroll when switching pages
        
        # Set cursor position: skip comment (line 0) and blank line (line 1)
        # For nodes with labels (6, 7), position cursor after the label
        node_lines = self.code_areas_content[target_index]
        if target_index == 5:  # Node 6 (index 5) - has DATA_CHECK: label
            # Find the label line and position cursor on the blank line after it
            label_line_idx = -1
            for i, line in enumerate(node_lines):
                if line.strip().endswith(":"):
                    label_line_idx = i
                    break
            if label_line_idx >= 0 and label_line_idx + 1 < len(node_lines):
                self.cursor_pos = (label_line_idx + 1, 0)  # Position after label
            else:
                self.cursor_pos = (2, 0)  # Fallback to line 2
        elif target_index == 6:  # Node 7 (index 6) - has OUTPUT_SAMPLE: label
            # Find the label line and position cursor on the blank line after it
            label_line_idx = -1
            for i, line in enumerate(node_lines):
                if line.strip().endswith(":"):
                    label_line_idx = i
                    break
            if label_line_idx >= 0 and label_line_idx + 1 < len(node_lines):
                self.cursor_pos = (label_line_idx + 1, 0)  # Position after label
            else:
                self.cursor_pos = (2, 0)  # Fallback to line 2
        else:
            # For nodes without labels (1-5), cursor goes to line 1 (blank line after comment)
            self.cursor_pos = (1, 0)
        
        # Ensure focus is on editor and game state allows editing
        self.focus_target = "editor"
        self.game_state = "EDITING"  # Set to editing mode so cursor is visible
        self._ensure_focus_visible()
        self._push_node_briefing()
        self._prepare_modal_for_current_node()

    def _activate_control(self, label: str):
        """Execute the action associated with a control button."""
        label = label.upper()
        if label == "RUN":
            if self.game_state == "RUNNING":
                self.cpu_state["isRunning"] = False
                self.game_state = "PAUSED"
            else:
                self.parse_code()
                if self.game_state != "ERROR":
                    self.cpu_state["isRunning"] = True
                    self.game_state = "RUNNING"
        else:
            return

    def _update_video_frame(self, dt):
        """
        Reads the next frame from the video capture object and updates self.video_frame.
        Handles looping and scaling to the target size.
        """
        if not self.video_cap or not (self.challenge_completed or self.module_animation_timer > 0):
            return

        self.video_playback_timing += dt
        
        # Calculate how many frames to skip based on delta time (dt)
        frame_interval = 1.0 / self.VIDEO_FPS 
        
        if self.video_playback_timing >= frame_interval:
            self.video_playback_timing -= frame_interval
            
            ret, frame = self.video_cap.read()
            
            if ret:
                # 1. Convert BGR to RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # 2. Resize to target size (55% scaled size)
                frame_resized = cv2.resize(frame_rgb, self.target_logo_size)
                
                # 3. Convert NumPy array to Pygame Surface
                frame_swapped = np.swapaxes(frame_resized, 0, 1)
                self.video_frame = pygame.surfarray.make_surface(frame_swapped)
                
            else:
                # Video ended, loop back to the beginning
                self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                # Read the first frame immediately for smooth loop start (optional, but cleaner)
                ret, frame = self.video_cap.read()
                if ret:
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    frame_resized = cv2.resize(frame_rgb, self.target_logo_size)
                    frame_swapped = np.swapaxes(frame_resized, 0, 1)
                    self.video_frame = pygame.surfarray.make_surface(frame_swapped)
                else:
                    self.video_frame = self.static_mock_surface # Fallback to static if read fails

    def update(self, dt):
        """Updates the game logic."""
        # Clean up finished audio channels periodically
        if self.active_audio_channels:
            self.active_audio_channels = [
                ch for ch in self.active_audio_channels 
                if ch is not None and ch.get_busy()
            ]
        
        # Decrement module animation timer
        if self.module_animation_timer > 0:
            self.module_animation_timer -= dt
            if self.module_animation_timer < 0:
                self.module_animation_timer = 0.0

        if self.game_state == "RUNNING":
            if pygame.time.get_ticks() - self.last_tick_time > self.sim_speed:
                self.last_tick_time = pygame.time.get_ticks()
                self.tick_data_stream()
                self.execute_instruction()
                # Pause immediately if an error occurred or a node switch is pending
                if self.game_state == "ERROR" or self.pending_node_switch is not None or self.success_modal_active:
                    self.cpu_state["isRunning"] = False
                    self.game_state = "PAUSED"
        
        # Update the video frame if the challenge is completed OR the module animation is active
        if self.challenge_completed or self.module_animation_timer > 0:
            self._update_video_frame(dt)

        # Auto-advance to NODE 02 when the C400 power rail goes live
        power_led_on = self.is_c400_power_led_on()
        if power_led_on and not self._power_led_prev_state:
            print(f"DEBUG: Power LED turned on! Attempting to play sound...")
            print(f"DEBUG: power_on_sound is: {self.power_on_sound}")
            if self.power_on_sound:
                try:
                    # Ensure mixer is initialized before playing
                    if not pygame.mixer.get_init():
                        print("DEBUG: Mixer not initialized, initializing now...")
                        pygame.mixer.init()
                    print("DEBUG: Calling power_on_sound.play()...")
                    channel = self.power_on_sound.play()
                    if channel:
                        self.active_audio_channels.append(channel)
                    print("DEBUG: Sound play() called successfully")
                except Exception as play_error:
                    print(f"Warning: Unable to play On-Test.wav: {play_error}")
                    import traceback
                    traceback.print_exc()
            else:
                print("DEBUG: power_on_sound is None, skipping playback")
            # Grant tokens for Node 1 completion
            if "LAPC1A" not in self.pending_token_grants:
                self.pending_token_grants.append("LAPC1A")
            if "LAPC1_NODE1" not in self.pending_token_grants:
                self.pending_token_grants.append("LAPC1_NODE1")
            # Show success modal first, then switch to next node after dismissal
            self._prepare_success_modal_for_node(1)
            self.pending_node_switch = 1
            # Pause execution immediately when Node 1 completes
            if self.game_state == "RUNNING":
                self.cpu_state["isRunning"] = False
                self.game_state = "PAUSED"
            # No parrot animation for individual node completion
        self._power_led_prev_state = power_led_on
        
        now = pygame.time.get_ticks()
        if now - self.last_chat_cursor_toggle > 400:
            self.chat_cursor_visible = not self.chat_cursor_visible
            self.last_chat_cursor_toggle = now
        if self.chat_typing_state:
            if now - self.chat_typing_state["last_stage"] > 400:
                self.chat_typing_state["stage"] = (self.chat_typing_state["stage"] + 1) % 3
                self.chat_typing_state["last_stage"] = now
            if now - self.chat_typing_state["start"] > 2200:
                speaker = self.chat_typing_state.get("speaker", "UNCLE-AM")
                message = self.chat_typing_state["message"]
                from_queue = self.chat_typing_state.get("from_queue", False)
                self._append_chat(speaker, message)
                self.chat_typing_state = None
                if from_queue:
                    self.chat_next_queue_time = now + 900
        elif self.chat_message_queue and now >= self.chat_next_queue_time:
            self._begin_next_queued_message()
    
    def should_exit(self):
        if self.exit_requested:
            self._stop_start_video()
        return self.exit_requested

    # --- Drawing Methods ---

    def draw(self):
        """Main drawing loop."""
        self.surface.fill(self.BLACK)
        self.parrot_overlay = None
        parrot_rect = pygame.Rect(
            int(-62 * self.scale),
            int(self.parrot_anchor_local[1] * self.scale),
            self.parrot_display_size,
            self.parrot_display_size,
        )
        self._draw_editor_pane()
        self._draw_team_messages()
        self._draw_monitor_pane()
        self._draw_control_strip()
        self._draw_parrot_logo(parrot_rect)
        self._draw_footer_instructions()

        if self.success_modal_active:
            self._draw_success_modal()
        elif self.modal_active:
            self._draw_initial_modal()

    def _draw_parrot_logo(self, container_rect: pygame.Rect):
        """Draw the CRACKER-PARROT video/logo within the provided rectangle."""

        self.parrot_overlay = None
        if container_rect.width <= 0 or container_rect.height <= 0:
            return

        display_surface = self.parrot_logo_png or self.static_mock_surface
        is_video_active = self.challenge_completed or self.module_animation_timer > 0

        if is_video_active and self.video_cap:
            if not self.video_frame:
                self._update_video_frame(0)
            if self.video_frame:
                display_surface = self.video_frame

        if not display_surface:
            return

        max_width = container_rect.width - int(10 * self.scale)
        max_height = container_rect.height - int(16 * self.scale) - self.font_tiny.get_linesize()
        if max_width <= 0 or max_height <= 0:
            return

        surface = display_surface
        target_ratio = min(max_width / surface.get_width(), max_height / surface.get_height(), 1.0)
        target_size = (
            max(1, int(surface.get_width() * target_ratio)),
            max(1, int(surface.get_height() * target_ratio)),
        )
        if target_size != surface.get_size():
            surface = pygame.transform.smoothscale(surface, target_size)

        border_color = self.CYAN if is_video_active and (pygame.time.get_ticks() % 1000 < 800) else self.DARK_CYAN
        caption_surface = self.font_caption.render("CRACKER IDE FEED", True, self.CYAN)

        border = int(4 * self.scale)
        caption_gap = int(6 * self.scale)
        overlay_width = surface.get_width() + border * 2
        overlay_height = surface.get_height() + border * 3 + caption_surface.get_height() + caption_gap

        overlay_surface = pygame.Surface((overlay_width, overlay_height), pygame.SRCALPHA)
        pygame.draw.rect(overlay_surface, self.BLACK, overlay_surface.get_rect())
        pygame.draw.rect(overlay_surface, border_color, overlay_surface.get_rect(), 1)
        overlay_surface.blit(surface, (border, border))
        caption_y = overlay_height - caption_surface.get_height() - border
        caption_x = (overlay_width - caption_surface.get_width()) // 2
        overlay_surface.blit(caption_surface, (caption_x, caption_y))

        overlay_rect = overlay_surface.get_rect()
        overlay_rect.topleft = (container_rect.x, container_rect.y)

        offset_x = container_rect.x
        offset_y = container_rect.y
        self.parrot_overlay = (overlay_surface, (offset_x, offset_y))

    def _draw_team_messages(self):
        """Render the Uncle-am briefing window."""

        subtitle = "IDE Controller // Audio Ops"
        accent_color = self.HIGHLIGHT_CYAN if self.focus_target == "chat" and not (self.modal_active or self.success_modal_active) else self.DARK_CYAN
        content_rect, _ = self._draw_panel(
            self.team_window_rect,
            title="TEAM MSGs...",
            subtitle=subtitle,
            accent=accent_color,
            border_width=2,
        )

        body_padding = max(int(10 * self.scale), 8)
        gap = int(8 * self.scale)
        input_height = self.font_small.get_linesize() + int(12 * self.scale)
        input_rect = pygame.Rect(
            content_rect.x,
            content_rect.bottom - input_height,
            content_rect.width,
            input_height,
        )
        message_area_height = max(0, input_rect.top - content_rect.y - gap)
        message_area = pygame.Rect(
            content_rect.x,
            content_rect.y,
            content_rect.width,
            message_area_height,
        )

        message_x = message_area.x + body_padding
        available_width = message_area.width - body_padding * 2
        label_gap = int(6 * self.scale)
        font_message = self.font_tiny
        line_height = font_message.get_linesize()
        entry_gap = int(8 * self.scale)

        entries: List[Dict[str, Any]] = []

        def build_entry(speaker: str, text: str, label_color, text_color):
            label_surface = font_message.render(f"{speaker}:", True, label_color)
            text_width = max(0, available_width - label_surface.get_width() - label_gap)
            wrapped = self._wrap_text(text.upper(), font_message, text_width)
            if not wrapped:
                wrapped = [""]
            lines: List[Dict[str, Any]] = []
            text_x = message_x + label_surface.get_width() + label_gap
            first_surface = font_message.render(wrapped[0], True, text_color)
            lines.append({
                "height": line_height,
                "surfaces": [
                    (label_surface, message_x),
                    (first_surface, text_x),
                ],
            })
            for line_text in wrapped[1:]:
                surface = font_message.render(line_text.upper(), True, text_color)
                lines.append({
                    "height": line_height,
                    "surfaces": [
                        (surface, text_x),
                    ],
                })
            entries.append({"lines": lines})

        for speaker, text in self.chat_messages[-40:]:
            label_color = self.YELLOW if speaker == "UNCLE-AM" else self.DARK_CYAN
            text_color = self.CYAN if speaker == "UNCLE-AM" else self.WHITE
            build_entry(speaker, text, label_color, text_color)

        if self.chat_typing_state:
            stage = self.chat_typing_state["stage"]
            dots = "." * (stage + 1)
            build_entry("UNCLE-AM", dots, self.YELLOW, self.CYAN)

        render_rows: List[Dict[str, Any]] = []
        running_total = 0
        for idx, entry in enumerate(entries):
            for line in entry["lines"]:
                render_rows.append(line)
                running_total += line["height"]
            if idx < len(entries) - 1:
                render_rows.append({"height": entry_gap, "surfaces": []})
                running_total += entry_gap

        total_height = running_total

        visible_height = max(message_area.height - body_padding * 2, 0)
        self.chat_scroll_limit = max(0, total_height - visible_height)
        if self.chat_follow_latest:
            self.chat_scroll_offset = self.chat_scroll_limit
        else:
            self.chat_scroll_offset = max(0, min(self.chat_scroll_offset, self.chat_scroll_limit))

        # Set clipping rectangle to prevent overflow
        old_clip = self.surface.get_clip()
        self.surface.set_clip(message_area)
        
        if not render_rows:
            placeholder = font_message.render("<< awaiting link-up >>", True, self.DARK_CYAN)
            placeholder_y = message_area.bottom - body_padding - placeholder.get_height()
            if placeholder_y < message_area.y + body_padding:
                placeholder_y = message_area.y + body_padding
            self.surface.blit(placeholder, (message_x, placeholder_y))
        else:
            top_bound = message_area.y + body_padding
            bottom_bound = message_area.bottom - body_padding
            cursor_y = top_bound - self.chat_scroll_offset
            for row in render_rows:
                row_top = cursor_y
                row_bottom = row_top + row["height"]
                cursor_y += row["height"]
                if row["height"] <= 0:
                    continue
                if row_bottom <= top_bound or row_top >= bottom_bound:
                    continue
                for surface, x in row.get("surfaces", []):
                    y_offset = row_top + (row["height"] - surface.get_height()) // 2
                    self.surface.blit(surface, (x, y_offset))
        
        # Restore clipping
        self.surface.set_clip(old_clip)

        pygame.draw.rect(self.surface, self.BLACK, input_rect)
        border_color = self.HIGHLIGHT_CYAN if self.focus_target == "chat" else self.DARK_CYAN
        pygame.draw.rect(self.surface, border_color, input_rect, 1)

        if self.chat_input:
            input_text = self.chat_input.upper()
            input_color = self.CYAN
        elif self.focus_target == "chat":
            input_text = ""
            input_color = self.CYAN
        else:
            input_text = "TYPE TO CHAT..."
            input_color = self.DARK_CYAN

        text_x = input_rect.x + body_padding
        baseline_y = input_rect.y + max(0, (input_rect.height - self.font_small.get_height()) // 2)
        text_width = 0

        if input_text:
            text_surface = self.font_small.render(input_text, True, input_color)
            text_y = input_rect.y + max(0, (input_rect.height - text_surface.get_height()) // 2)
            self.surface.blit(text_surface, (text_x, text_y))
            text_width = text_surface.get_width()
        else:
            text_surface = None
            text_y = baseline_y

        if self.focus_target == "chat" and self.chat_cursor_visible:
            cursor_x = text_x + text_width
            cursor_y_top = input_rect.y + int(input_rect.height * 0.25)
            cursor_y_bottom = input_rect.bottom - int(input_rect.height * 0.25)
            pygame.draw.line(self.surface, self.CYAN, (cursor_x + 2, cursor_y_top), (cursor_x + 2, cursor_y_bottom), 1)

    def _draw_control_strip(self):
        """Draw the interactive control buttons under the messaging window."""

        if not self.control_labels:
            return

        start_y = self.team_window_rect.bottom + int(32 * self.scale)
        button_width = max(int(100 * self.scale), 78)
        button_height = max(int(34 * self.scale), 26)
        gap = int(18 * self.scale)
        total_width = len(self.control_labels) * button_width + (len(self.control_labels) - 1) * gap
        start_x = self.team_window_rect.centerx - total_width // 2

        strip_label = self.font_tiny.render("SIM CONTROL SURFACE", True, self.DARK_CYAN)
        label_x = self.team_window_rect.centerx - strip_label.get_width() // 2
        label_y = start_y - strip_label.get_height() - int(10 * self.scale)
        self.surface.blit(strip_label, (label_x, label_y))

        for idx, label in enumerate(self.control_labels):
            x = start_x + idx * (button_width + gap)
            color = self.CYAN
            render_label = label
            if label == "RUN":
                if self.game_state == "RUNNING":
                    color = self.GREEN
                    render_label = "PAUSE"
                else:
                    color = self.GREEN
            is_active = self.focus_target == "controls" and self.control_focus == idx and not (self.modal_active or self.success_modal_active)
            self._draw_button(render_label, (x, start_y, button_width, button_height), color, active=is_active)

        box_width = max(int(320 * self.scale), 240)
        box_height = max(int(120 * self.scale), 80)
        box_x = self.team_window_rect.centerx - box_width // 2
        box_y = start_y + button_height + int(24 * self.scale)
        node_rect = pygame.Rect(box_x, box_y, box_width, box_height)
        pygame.draw.rect(self.surface, self.BLACK, node_rect)
        pygame.draw.rect(self.surface, self.HIGHLIGHT_CYAN, node_rect, 2)

        if self.code_areas_content:
            node_number = min(max(self.page_index + 1, 1), 10)
            badge_surface = self.node_badges.get(f"NODE_{node_number}")
            if badge_surface:
                scaled_image = pygame.transform.smoothscale(
                    badge_surface,
                    (
                        max(box_width - int(16 * self.scale), 1),
                        max(box_height - int(16 * self.scale), 1),
                    ),
                )
                image_rect = scaled_image.get_rect()
                image_rect.center = node_rect.center
                self.surface.blit(scaled_image, image_rect.topleft)

    def _draw_footer_instructions(self):
        footer_text = "F7 RESET   ESC EXIT"
        text_surface = self.font_tiny.render(footer_text, True, self.DARK_CYAN)
        x = int(8 * self.scale)
        y = self.height - text_surface.get_height() - int(6 * self.scale)
        self.surface.blit(text_surface, (x, y))

    def _render_modal_entry(self, modal_rect: pygame.Rect, content_x: int, content_width: int, start_y: int, entry: Dict[str, Any]) -> int:
        # Calculate total content height first
        y = start_y
        total_height = 0
        
        title = entry.get("title")
        if title:
            total_height += self.font_small.get_linesize() + int(6 * self.scale)
        
        line_color = entry.get("line_color", self.CYAN)
        shortcuts_seen = False
        
        for raw_line in entry.get("lines", []):
            if not raw_line:
                total_height += self.font_tiny.get_linesize()
                continue
            if raw_line.startswith("    "):
                total_height += self.font_tiny.get_linesize()
                continue
            if raw_line.strip() == "SHORTCUTS":
                total_height += self.font_small.get_linesize() + int(6 * self.scale)
                continue
            
            wrapped = self._wrap_text(raw_line, self.font_tiny, content_width)
            if not wrapped:
                wrapped = [raw_line]
            total_height += len(wrapped) * self.font_tiny.get_linesize()
        
        # Calculate visible area and scroll limits
        prompt_height = self.font_tiny.get_linesize() + self.padding * 2
        visible_height = modal_rect.height - (start_y - modal_rect.y) - prompt_height - self.padding * 2
        self.modal_scroll_limit = max(0, total_height - visible_height)
        self.modal_scroll_offset = max(0, min(self.modal_scroll_offset, self.modal_scroll_limit))
        
        # Set clipping rectangle to prevent overflow
        clip_rect = pygame.Rect(
            modal_rect.x + 1,
            start_y,
            modal_rect.width - 2,
            visible_height
        )
        old_clip = self.surface.get_clip()
        self.surface.set_clip(clip_rect)
        
        # Render content with scroll offset
        y = start_y - self.modal_scroll_offset
        bottom_limit = modal_rect.bottom - prompt_height - self.padding
        
        if title:
            title_color = entry.get("title_color", self.CYAN)
            title_surface = self.font_small.render(title, True, title_color)
            if y + title_surface.get_height() >= start_y and y <= bottom_limit:
                self.surface.blit(title_surface, (content_x, y))
            y += self.font_small.get_linesize() + int(6 * self.scale)
        
        line_color = entry.get("line_color", self.CYAN)
        shortcuts_seen = False
        
        for raw_line in entry.get("lines", []):
            if y > bottom_limit:
                break
            if not raw_line:
                y += self.font_tiny.get_linesize()
                continue
            if raw_line.startswith("    "):
                code_surface = self.font_tiny.render(raw_line, True, self.PINK)
                if y + code_surface.get_height() >= start_y and y <= bottom_limit:
                    self.surface.blit(code_surface, (content_x, y))
                y += self.font_tiny.get_linesize()
                continue
            
            if raw_line.strip() == "SHORTCUTS":
                shortcuts_seen = True
                shortcuts_surface = self.font_small.render(raw_line, True, self.CYAN)
                if y + shortcuts_surface.get_height() >= start_y and y <= bottom_limit:
                    self.surface.blit(shortcuts_surface, (content_x, y))
                y += self.font_small.get_linesize() + int(6 * self.scale)
                continue
            
            current_color = self.CYAN if shortcuts_seen else line_color
            wrapped = self._wrap_text(raw_line, self.font_tiny, content_width)
            if not wrapped:
                wrapped = [raw_line]
            for segment in wrapped:
                if y > bottom_limit:
                    break
                text_surface = self.font_tiny.render(segment, True, current_color)
                if y + text_surface.get_height() >= start_y and y <= bottom_limit:
                    self.surface.blit(text_surface, (content_x, y))
                y += self.font_tiny.get_linesize()
        
        # Restore clipping
        self.surface.set_clip(old_clip)
        
        return y + self.modal_scroll_offset

    def _draw_initial_modal(self):
        """Draws the narrative modal with uncle-am's questions."""
        
        # Black transparent overlay
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        self.surface.blit(overlay, (0, 0))
        
        # Modal box dimensions
        modal_w = int(self.width * 0.7)
        modal_h = int(self.height * 0.5)
        modal_x = int(130 * self.scale)
        modal_y = int(204 * self.scale)
        modal_rect = pygame.Rect(modal_x, modal_y, modal_w, modal_h)
        
        pygame.draw.rect(self.surface, self.BLACK, modal_rect)
        pygame.draw.rect(self.surface, self.CYAN, modal_rect, 2)
        
        text_x = modal_x + self.padding * 2
        text_y = modal_y + self.padding * 2

        # Instructions
        content_width = modal_w - self.padding * 4
        if 0 <= self.modal_step < len(self.modal_data):
            entry = self.modal_data[self.modal_step]
            self._render_modal_entry(modal_rect, text_x, content_width, text_y, entry)
            prompt = "PRESS SPACE TO CONTINUE"
            prompt_surface = self.font_tiny.render(prompt, True, self.YELLOW)
            prompt_y = modal_rect.bottom - self.padding * 2 - prompt_surface.get_height()
            self.surface.blit(prompt_surface, (modal_rect.centerx - prompt_surface.get_width() // 2, prompt_y))
        else:
            self._draw_text("Press [SPACE], [ENTER], or [TAB] to start the challenge.", (text_x, text_y), "medium", self.YELLOW)

    def _draw_success_modal(self):
        """Draws the success modal when a node completes."""
        
        # Black transparent overlay
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        self.surface.blit(overlay, (0, 0))
        
        # Modal box dimensions
        modal_w = int(self.width * 0.7)
        modal_h = int(self.height * 0.5)
        modal_x = int(130 * self.scale)
        modal_y = int(204 * self.scale)
        modal_rect = pygame.Rect(modal_x, modal_y, modal_w, modal_h)
        
        pygame.draw.rect(self.surface, self.BLACK, modal_rect)
        pygame.draw.rect(self.surface, self.GREEN, modal_rect, 2)  # Green border for success
        
        text_x = modal_x + self.padding * 2
        text_y = modal_y + self.padding * 2

        # Instructions
        content_width = modal_w - self.padding * 4
        if 0 <= self.success_modal_step < len(self.success_modal_data):
            entry = self.success_modal_data[self.success_modal_step]
            self._render_modal_entry(modal_rect, text_x, content_width, text_y, entry)
            prompt = "PRESS SPACE TO CONTINUE"
            prompt_surface = self.font_tiny.render(prompt, True, self.GREEN)
            prompt_y = modal_rect.bottom - self.padding * 2 - prompt_surface.get_height()
            self.surface.blit(prompt_surface, (modal_rect.centerx - prompt_surface.get_width() // 2, prompt_y))
        else:
            self._draw_text("Press [SPACE], [ENTER], or [TAB] to continue.", (text_x, text_y), "medium", self.GREEN)

    def get_screen_overlays(self):
        """Return list of (surface, offset) tuples for screen-level overlays."""

        if self.parrot_overlay:
            surface, offset = self.parrot_overlay
            return [(surface, offset)]
        return []


    def _draw_editor_pane(self):
        """Draw the single-node coding window."""

        if not (0 <= self.page_index < len(self.code_areas_content)):
            return

        node_idx = self.page_index
        accent_color = self.HIGHLIGHT_CYAN if self.focus_target == "editor" and not (self.modal_active or self.success_modal_active) else self.DARK_CYAN
        content_rect, _ = self._draw_panel(
            self.editor_pane_rect,
            title=self.page_titles[node_idx],
            subtitle=None,
            accent=accent_color,
        )

        node_lines = self.code_areas_content[node_idx]
        inner_padding = max(int(8 * self.scale), 6)
        text_x = content_rect.x + inner_padding
        max_text_width = content_rect.width - inner_padding * 2
        cursor_visible = (pygame.time.get_ticks() % 1000) < 500
        
        # Calculate total content height
        total_height = 0
        for line in node_lines:
            font_to_use = self.font_small
            if font_to_use.size(line)[0] > max_text_width:
                font_to_use = self.font_tiny
            total_height += font_to_use.get_linesize() + int(4 * self.scale)
        
        # Calculate visible area and scroll limits
        visible_height = content_rect.height - inner_padding * 2
        self.editor_scroll_limit = max(0, total_height - visible_height)
        self.editor_scroll_offset = max(0, min(self.editor_scroll_offset, self.editor_scroll_limit))
        
        # Set clipping rectangle to prevent overflow
        clip_rect = pygame.Rect(
            content_rect.x + 1,
            content_rect.y + inner_padding,
            content_rect.width - 2,
            visible_height
        )
        old_clip = self.surface.get_clip()
        self.surface.set_clip(clip_rect)
        
        # Render content with scroll offset
        start_y = content_rect.y + inner_padding
        line_y = start_y - self.editor_scroll_offset
        bottom_limit = content_rect.bottom - inner_padding

        for line_idx, line in enumerate(node_lines):
            node_label_index = self.labels.get(self.node_labels[node_idx], -1)
            global_idx = node_label_index + line_idx if node_label_index >= 0 else -1
            is_current_pc = global_idx == self.cpu_state["instructionIndex"] and self.game_state != "EDITING"

            line_clean = line.strip()
            text_color = self.CYAN
            if line_clean.startswith(";"):
                text_color = self.DARK_CYAN
            elif line_clean.upper() in self.placeholder_lines:
                text_color = self.PINK

            font_to_use = self.font_small
            if font_to_use.size(line)[0] > max_text_width:
                font_to_use = self.font_tiny
            
            # Only render if line is visible
            if line_y + font_to_use.get_linesize() >= start_y and line_y <= bottom_limit:
                if is_current_pc:
                    highlight_rect = pygame.Rect(
                        text_x - int(6 * self.scale),
                        line_y - int(2 * self.scale),
                        max(content_rect.width - inner_padding, 1),
                        font_to_use.get_linesize(),
                    )
                    pygame.draw.rect(self.surface, self.HIGHLIGHT_CYAN, highlight_rect)

                text_surface = font_to_use.render(line, True, text_color)
                self.surface.blit(text_surface, (text_x, line_y))

                if (
                    self.game_state in ("EDITING", "PAUSED", "ERROR")
                    and self.focus_target == "editor"
                    and node_idx == self.editor_focus_node
                    and line_idx == self.cursor_pos[0]
                    and not (self.modal_active or self.success_modal_active)
                    and cursor_visible
                ):
                    cursor_font = font_to_use
                    cursor_x = text_x + cursor_font.size(line[: self.cursor_pos[1]])[0]
                    pygame.draw.line(
                        self.surface,
                        self.CYAN,
                        (cursor_x, line_y),
                        (cursor_x, line_y + cursor_font.get_linesize() - 1),
                        2,
                    )

            line_y += font_to_use.get_linesize() + int(4 * self.scale)
            if line_y > bottom_limit:
                break
        
        # Restore clipping
        self.surface.set_clip(old_clip)

    def _draw_monitor_pane(self):
        """Draw CPU instrumentation, waveform visualiser, and parrot feed."""

        subtitle = "live metrics // diag feed"
        content_rect, _ = self._draw_panel(
            self.monitor_pane_rect,
            title="LAPC-1 MONITOR",
            subtitle=subtitle,
            accent=self.DARK_CYAN,
            border_width=1,
        )
        inner_padding = max(int(10 * self.scale), 8)
        metrics_rect = content_rect.inflate(-inner_padding, -inner_padding)
        stats_height = max(int(metrics_rect.height * 0.55), self.font_small.get_linesize() * 10)
        stats_rect = pygame.Rect(
            metrics_rect.x,
            metrics_rect.y,
            metrics_rect.width,
            min(stats_height, metrics_rect.height - self.font_small.get_linesize() * 3),
        )
        
        # Set clipping rectangle to prevent overflow
        old_clip = self.surface.get_clip()
        self.surface.set_clip(metrics_rect)

        half_split = stats_rect.x + stats_rect.width // 2
        left_x = stats_rect.x + int(12 * self.scale)
        right_x = half_split + int(14 * self.scale)
        metrics_right = half_split - int(14 * self.scale)
        registers_right = stats_rect.right - int(12 * self.scale)
        y_metrics = stats_rect.y + int(6 * self.scale)
        self._draw_key_value(left_x, y_metrics, "ACCUM", self.cpu_state["A"], metrics_right - int(40 * self.scale), self.YELLOW)
        y_metrics += self.font_small.get_linesize()
        self._draw_key_value(left_x, y_metrics, "PC IDX", self.cpu_state["instructionIndex"], metrics_right - int(40 * self.scale), self.YELLOW)
        y_metrics += self.font_small.get_linesize()
        self._draw_key_value(left_x, y_metrics, "CYCLES", self.cpu_state["cycles"], metrics_right - int(40 * self.scale), self.YELLOW)
        y_metrics += self.font_small.get_linesize()
        zero_flag_color = self.GREEN if self.zero_flag else self.RED
        self._draw_text(f"ZERO FLAG: {'SET' if self.zero_flag else 'CLEAR'}", (left_x, y_metrics), "tiny", zero_flag_color)

        y_registers = stats_rect.y + int(6 * self.scale)

        for addr, value in self.cpu_state["Memory"].items():
            reg_name = {
                REG_MASTER_POWER: "C400 PWR",
                REG_LEFT_CHANNEL: "C401 L",
                REG_RIGHT_CHANNEL: "C402 R",
                REG_DATA_READY: "C403 RDY",
                REG_PACKET_BUFFER: "C800 BUF",
            }.get(addr, hex(addr).upper())

            is_active = False
            if addr == REG_MASTER_POWER:
                is_active = value == ACTIVATION_BYTE
            elif addr == REG_DATA_READY:
                is_active = value == READY_STATE
            elif addr in [REG_LEFT_CHANNEL, REG_RIGHT_CHANNEL]:
                is_active = value > 0 and self.cpu_state["Memory"][REG_MASTER_POWER] == ACTIVATION_BYTE

            self._draw_key_value(right_x, y_registers, reg_name, value, registers_right, self.DARK_CYAN)
            self._draw_led(registers_right - int(20 * self.scale), y_registers + self.font_small.get_linesize() // 2, is_active, addr)
            y_registers += self.font_small.get_linesize()

        y = max(y_metrics, y_registers) + int(8 * self.scale)
        visualizer_height = metrics_rect.bottom - y - self.font_small.get_linesize() * 3
        if visualizer_height > self.font_small.get_linesize() * 4:
            visualizer_rect = pygame.Rect(
                metrics_rect.x + int(4 * self.scale),
                y + int(4 * self.scale),
                metrics_rect.width - int(8 * self.scale),
                visualizer_height,
            )
            self._draw_text("DIAGNOSTIC VISUALIZER", (visualizer_rect.x + int(6 * self.scale), visualizer_rect.y + int(4 * self.scale)), "tiny", self.CYAN)
            self._draw_waveform_canvas(visualizer_rect)

            controls_y = visualizer_rect.bottom + int(8 * self.scale)
            button_height = int(24 * self.scale)
            button_width = (visualizer_rect.width - int(8 * self.scale)) // 2
            self._draw_button("F5 RUN/PAUSE", (visualizer_rect.x, controls_y, button_width, button_height), self.GREEN)
            self._draw_button("F7 RESET", (visualizer_rect.x + button_width + int(4 * self.scale), controls_y, button_width, button_height), self.RED)
        
        # Restore clipping
        self.surface.set_clip(old_clip)

    def _draw_waveform_canvas(self, pane_rect: pygame.Rect):
        """Draws the audio waveform using Pygame drawing primitives."""
        canvas_rect = pane_rect.inflate(-int(8 * self.scale), -int(12 * self.scale))
        if canvas_rect.width <= 0 or canvas_rect.height <= 0:
            return
        pygame.draw.rect(self.surface, self.BLACK, canvas_rect)
        pygame.draw.rect(self.surface, self.DARK_CYAN, canvas_rect, 1)

        # Combine channels to simulate output: only if power is on
        if self.cpu_state["Memory"][REG_MASTER_POWER] == ACTIVATION_BYTE:
            # Simple average for a mono waveform display
            combined_value = (self.cpu_state["Memory"][REG_LEFT_CHANNEL] + self.cpu_state["Memory"][REG_RIGHT_CHANNEL]) / 2
        else:
            combined_value = 0x80 # Mid-point (silence) when off
            
        self.waveform_history.append(combined_value)
        if len(self.waveform_history) > self.max_wave_samples:
            self.waveform_history.pop(0)

        if len(self.waveform_history) < 2: return
        
        w, h = canvas_rect.width, canvas_rect.height
        center_y = canvas_rect.centery
        
        points = []
        for i, val in enumerate(self.waveform_history):
            x = canvas_rect.x + int(i / self.max_wave_samples * w)
            # Normalize volume value (0x00-0xFF) around 0x80 (midpoint) to a y-coordinate
            y_norm = (val - 0x80) / 0x80 
            y = center_y - int(y_norm * h / 2)
            
            points.append((x, y))

        if points:
            pygame.draw.aalines(self.surface, self.GREEN, False, points)
        
    def _draw_text(self, text, pos, font_key, color):
        """Helper to draw text using the stored fonts."""
        try:
            surface = self.fonts[font_key].render(text, True, color, self.BLACK)
            self.surface.blit(surface, pos)
        except Exception:
            pass

    def _draw_key_value(self, x, y, key, value, right_x, color):
        """Draws key on left, value on right."""
        val_str = hex(value).upper()[2:].zfill(2) if isinstance(value, int) else str(value)
        
        self._draw_text(f"{key}:", (x, y), "small", self.DARK_CYAN)
        
        font = self.fonts["small"]
        val_w = font.size(val_str)[0]
        self._draw_text(val_str, (right_x - val_w, y), "small", color)

    def _draw_led(self, x, center_y, is_active, addr):
        """Draws a simple LED."""
        radius = int(8 * self.scale)
        color = self.GREEN if is_active else self.DARK_GREEN
        
        if not is_active:
            color = (0x44, 0x00, 0x00)

        if is_active:
            glow_radius = int(12 * self.scale)
            # Use cyan/blue glow for the tech theme
            glow_color = (0, 70, 70) 
            pygame.draw.circle(self.surface, glow_color, (x, center_y), glow_radius)

        pygame.draw.circle(self.surface, color, (x, center_y), radius)

    def is_cracker_ide_audio_playing(self) -> bool:
        """Check if any CRACKER IDE audio from Urgent_Ops/Audio folder is currently playing."""
        if not self.active_audio_channels:
            return False
        
        # Clean up finished channels and check if any are still playing
        self.active_audio_channels = [
            ch for ch in self.active_audio_channels 
            if ch is not None and ch.get_busy()
        ]
        
        return len(self.active_audio_channels) > 0
    
    def is_c400_power_led_on(self) -> bool:
        """Return True when the C400 power rail is active (LED shown as green)."""
        memory = getattr(self, "cpu_state", {}).get("Memory", {}) if hasattr(self, "cpu_state") else {}
        return memory.get(REG_MASTER_POWER) == ACTIVATION_BYTE

    def _draw_button(self, text, rect_tuple, color, active: bool = False):
        """Draws a placeholder button for visual continuity."""
        rect = pygame.Rect(rect_tuple)
        fill_color = self.HIGHLIGHT_CYAN if active else self.BLACK
        pygame.draw.rect(self.surface, fill_color, rect)
        pygame.draw.rect(self.surface, color, rect, 2)
        
        font = self.fonts["small"]
        text_surface = font.render(text, True, color)
        self.surface.blit(text_surface, (rect.centerx - text_surface.get_width() // 2, rect.centery - text_surface.get_height() // 2))

    def _get_status_message(self):
        if self.modal_active:
            return "AWAITING UNCLE-AM'S INSTRUCTIONS. PRESS SPACE/ENTER TO START."
        if self.game_state == "SUCCESS":
            return "SUCCESS: RADLAND DRIVER INITIALIZATION COMPLETE. REPORTING FOR DUTY. (Task 101 Cleared)"
        if self.game_state == "ERROR":
            return f"ERROR: CRITICAL FAULT. CHECK CODE MODULES. F7 TO RESET."
        if self.game_state == "RUNNING":
            return f"SIMULATION RUNNING: EXECUTION CYCLE {self.cpu_state['cycles']}"
        if self.game_state == "PAUSED":
            return f"SIMULATION PAUSED: CYCLE {self.cpu_state['cycles']}. Press F5 to resume or F7 to reset."
        
        return "EDITING: TAB to switch modules. Enter LAPC-1 assembly for nodes 01-07. F5 to compile/run."

    def set_error(self, message, node_idx, line_idx):
        print(f"[DEBUG] set_error called: {message}, node {node_idx}, line {line_idx}")
        self.game_state = "ERROR"
        self.cpu_state["isRunning"] = False
        self.focus_target = "editor"
        self.control_focus = 0
        # Store error location for TAB navigation
        self.error_node_idx = node_idx
        self.error_line_idx = line_idx
        print(f"[DEBUG] set_error: Stored error_node_idx={self.error_node_idx}, error_line_idx={self.error_line_idx}")
        fallback_message = f"{message} in Node {node_idx+1}, Line {line_idx+1}"
        self.error_message = f"ERROR: {fallback_message}"
        # Store reference to original method if not already stored
        if not hasattr(self, '_original_get_status_message'):
            self._original_get_status_message = self._get_status_message
        self._get_status_message = lambda: self.error_message
        self._push_uncle_am_error(fallback_message)

    def set_success(self, message):
        self.game_state = "SUCCESS"
        self.cpu_state["isRunning"] = False
        self.success_message = message
        self._get_status_message = lambda: f"SUCCESS: {self.success_message}"
        
        # *** FULL CHALLENGE COMPLETION: Trigger continuous video playback ***
        self.challenge_completed = True
        self.module_animation_timer = 0.0 # Stop module animation timer

        # Force video to start on frame 0 immediately upon success
        if self.video_cap:
            self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            self._update_video_frame(0.0)
        
    def set_status_bar_message(self, message, color):
        pass # Status drawing relies on _get_status_message based on game_state/error_message.

    def _push_uncle_am_error(self, message: str) -> None:
        encouragement = random.choice(
            [
                "We'll crack it together, you're close!",
                "Don't sweat it, adjust and rerun.",
                "That's the spirit, iterate & conquer!",
                "Reset, breathe, tweak. I'm with you.",
            ]
        )
        self.chat_typing_state = {
            "message": f"Runtime flagged: {message}\n\n{encouragement}".upper(),
            "start": pygame.time.get_ticks(),
            "last_stage": pygame.time.get_ticks(),
            "stage": 0,
            "speaker": "UNCLE-AM",
        }

# -----------------------------------------------------------------------------
# Standalone test runner (if you want to run this file directly)
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    try:
        pygame.init()
    except Exception as e:
        print(f"Pygame initialization failed. Run this file in an environment with Pygame installed: {e}")
        exit()

    # --- Setup a test environment ---
    SCREEN_WIDTH = 1200
    SCREEN_HEIGHT = 800
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("CRACKER-PARROT IDE Standalone Test")

    # --- Create mock fonts and scale ---
    try:
        test_fonts = {
            "large": pygame.font.Font(None, 40), 
            "medium": pygame.font.Font(None, 24),
            "small": pygame.font.Font(None, 18),
            "tiny": pygame.font.Font(None, 14)
        }
    except:
        test_fonts = {
            "large": pygame.font.Font(None, 40),
            "medium": pygame.font.Font(None, 24),
            "small": pygame.font.Font(None, 18),
            "tiny": pygame.font.Font(None, 14)
        }
    test_scale = 1.0

    # --- Instantiate the game ---
    game = CRACKER_IDE_LAPC1_Driver_Challenge(screen, test_fonts, test_scale, "YOUR_USERNAME")

    clock = pygame.time.Clock()
    running = True

    print("\n--- STANDALONE TEST INSTRUCTIONS ---")
    print("F9: Trigger success (continuous video loop).")
    print("F10: Trigger 1.5s module completion video burst.")
    print("F7: Reset state.")
    print("--------------------------------------\n")


    while running:
        # --- Event Loop ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            if event.type == pygame.KEYDOWN and event.key == pygame.K_F8:
                game.toggle_docs()
                game.modal_active = False 
            
            # Custom test key to trigger SUCCESS/video display
            if event.type == pygame.KEYDOWN and event.key == pygame.K_F9:
                if game.game_state != "SUCCESS":
                    print("TEST: Triggering SUCCESS state and continuous video playback.")
                    game.set_success("Simulated successful driver initialization.")
                else:
                    print("TEST: Resetting state.")
                    game.reset_state()
            
            # Custom test key to trigger 1.5s module animation
            if event.type == pygame.KEYDOWN and event.key == pygame.K_F10:
                if game.game_state != "SUCCESS":
                    print("TEST: Triggering 1.5s module completion video burst.")
                    game.module_animation_timer = game.ANIMATION_DURATION
                    if game.video_cap:
                         game.video_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                else:
                    print("TEST: Cannot trigger module animation in SUCCESS state.")


            if event.type == pygame.KEYDOWN:
                action = game.handle_event(event)
                if action == "EXIT":
                    running = False
        
        # --- Update Game ---
        # Pass delta time in seconds (dt) to the update function
        dt = clock.get_time() / 1000.0
        game.update(dt)

        # --- Draw Game ---
        game.draw()
        
        # --- Mock External Doc Renderer for Standalone Test ---
        # (Docs overlay removed)
        # --- Update Display ---
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()