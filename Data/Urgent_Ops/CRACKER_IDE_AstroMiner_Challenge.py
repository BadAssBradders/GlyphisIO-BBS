import pygame
import re
import time
import os
import sys
import random
import math
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional

# Data path helper - works for both development and built executable
def get_data_path(*path_parts):
    """
    Returns the path to the Data folder, handling both development and built executable scenarios.
    """
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        base_path = project_root
    
    data_folder = os.path.join(base_path, "Data")
    if os.path.exists(data_folder):
        return os.path.join(data_folder, *path_parts)
    else:
        return os.path.join(base_path, *path_parts)

# --- Try to import cv2 for video playback ---
try:
    import cv2
    import numpy as np
    _cv2_available = True
except ImportError:
    _cv2_available = False
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
# ASTRO MINER CRACKING CHALLENGE
# A deep-dive reverse engineering experience
# -----------------------------------------------------------------------------

GAME_TITLE = "GLYPHIS_IO BBS: ASTRO MINER CRACKER"

# --- Constants for Memory Addresses (Astro Miner Context) ---
MEM_SPLASH_BITMAP = 0xA000
MEM_SPLASH_PALETTE = 0xA100
MEM_AUDIO_HEADER = 0xB000
MEM_AUDIO_BUFFER = 0xB100
MEM_MESH_HEADER = 0xC000
MEM_MESH_VERTICES = 0xC100
MEM_MESH_NORMALS = 0xC200
MEM_PROC_SEED = 0xC300
MEM_COPY_PROTECT = 0xD000
MEM_JUMP_TARGET = 0xD100
MEM_GAME_ENTRY = 0xE000

# Values to verify completion
SPLASH_LOAD_BYTE = 0x4D    # 'M'
PALETTE_LOAD_BYTE = 0x1F   # 16 colors
AUDIO_INIT_BYTE = 0xA1     # Audio On
AUDIO_STREAM_BYTE = 0xFF   # Buffer Active
MESH_LOAD_BYTE = 0x3D      # Mesh ID
VERTEX_COUNT_BYTE = 0x80   # 128 vertices
NORMAL_CALC_BYTE = 0x01    # Normals ON
PROC_GEN_BYTE = 0x42       # Seed 66
COPY_BYPASS_BYTE = 0x00    # NOP
JUMP_OVER_BYTE = 0xEA      # JMP Opcode

class CRACKER_IDE_AstroMiner_Challenge:
    """
    ASTRO MINER CRACKING CHALLENGE
    
    A guided reverse engineering experience where players crack a copy-protected
    game by writing assembly code to initialize graphics, audio, 3D rendering,
    and bypass the copy protection.
    
    Jax (our guide) walks players through each node, explaining what the code
    does and why it matters. The player should feel like they're actually
    diving into the game's internals and learning real concepts.
    """
    
    VIDEO_FPS = 30.0
    ANIMATION_DURATION = 4.0

    def __init__(self, surface, fonts, scale, player_username, token_checker=None, token_remover=None):
        self.surface = surface
        self.fonts = fonts
        self.scale = scale
        self.player_username = player_username
        self.token_checker = token_checker
        self.token_remover = token_remover

        self.font_large = self.fonts["large"]
        self.font_medium = self.fonts["medium"]
        self.font_small = self.fonts["small"]
        self.font_tiny = self.fonts["tiny"]
        
        try:
            medium_height = self.font_medium.get_height()
            caption_size = max(1, medium_height - 2)
            self.font_caption = pygame.font.Font(None, caption_size)
        except:
            self.font_caption = self.font_medium

        self.width = self.surface.get_width()
        self.height = self.surface.get_height()

        # --- Colors ---
        self.BLACK = (0, 0, 0)
        self.WHITE = (255, 255, 255)
        self.CYAN = (0, 255, 255)
        self.DARK_CYAN = (0, 139, 139)
        self.GREEN = (0, 255, 0)
        self.DARK_GREEN = (0, 128, 0)
        self.RED = (255, 64, 64)
        self.YELLOW = (255, 255, 0)
        self.ORANGE = (255, 165, 0)
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
        
        # Panel Positions
        top_panel_x = int(205 * self.scale)
        top_panel_y = int(14 * self.scale)
        top_panel_right = int(853 * self.scale)
        total_top_width = max(top_panel_right - top_panel_x, int(400 * self.scale))
        h_gap = int(8 * self.scale)
        
        # Split top
        self.monitor_pane_rect = pygame.Rect(top_panel_x, top_panel_y, int(total_top_width * 0.4) - h_gap // 2, int(176 * self.scale))
        self.ref_code_pane_rect = pygame.Rect(top_panel_x + self.monitor_pane_rect.width + h_gap, top_panel_y, int(total_top_width * 0.6) - h_gap // 2, int(176 * self.scale))
        
        # Main areas
        editor_width = max(int((444 - 6) * self.scale), int(200 * self.scale))
        self.editor_pane_rect = pygame.Rect(int(6 * self.scale), int(200 * self.scale), editor_width, int(414 * self.scale))
        
        team_width = max(int((853 - 446) * self.scale), int(200 * self.scale))
        self.team_window_rect = pygame.Rect(int(446 * self.scale), int(200 * self.scale), team_width, int(195 * self.scale))
        
        self.line_height = self.font_small.get_linesize() + 2
        self.base_parrot_size = 260
        self.parrot_anchor_local = (-11.0, -13.0)
        self.parrot_display_size = int(self.base_parrot_size * self.scale)

        # --- State ---
        self.game_state = "EDITING"
        self.modal_active = True
        self.success_modal_active = False
        self.page_index = 0
        self.focus_target = "editor"
        self.control_focus = 0
        self.control_labels = ["RUN"]
        self.exit_requested = False
        self.challenge_completed = False
        self.pending_token_grants = []
        self.module_animation_timer = 0.0
        self.hint_level = {}  # Track hint level per node for progressive hints
        
        # Progress flags
        self._splash_loaded = False
        self._audio_loaded = False
        self._mesh_loaded = False
        self._protection_bypassed = False

        # CPU State
        self.cpu_state = {"A": 0, "PC": 0, "cycles": 0, "isRunning": False, "instructionIndex": 0, "Memory": {}}
        self.code_areas_content: List[List[str]] = []
        self.labels: Dict[str, int] = {}
        self.cursor_pos = (1, 0)
        self.zero_flag = False

        # Resources
        self.parrot_overlay = None
        self.modal_overlay = None
        self.parrot_logo_png = self._load_and_process_parrot_logo()
        self.node_badges = {}
        self._load_node_badges()
        self.video_cap = None
        self.video_frame = None
        self.video_playback_timing = 0
        self.target_logo_size = None
        self.static_mock_surface = None
        self.parrot_logo_png = self._load_and_process_parrot_logo()
        self.fireworks = []

        # Content - Node metadata
        self.node_titles = ["NODE 01", "NODE 02", "NODE 03", "NODE 04"]
        self.node_labels = ["LOAD_SPLASH", "LOAD_AUDIO", "LOAD_MESH", "BYPASS_PROTECTION"]
        
        # =====================================================================
        # NODE BRIEFINGS - Technical documentation style (1989 Pacifica Isles)
        # These are generic/professional introductions, Jax's chat is personal
        # =====================================================================
        self.node_briefings = [
            # NODE 1: SPLASH SCREEN
            """CRACKER-PARROT IDE v2.1 - URGENT OPS MODULE
GLYPHIS_IO BBS // PACIFICA ISLES UNDERGROUND // 1989

===============================================
TARGET: ASTRO MINER (Bradsonic R&D Division)
STATUS: INTERCEPTED DISTRIBUTION BUILD
PROTECTION: CUSTOM DISK-CHECK + MEMORY VALIDATION
===============================================

BACKGROUND:
Astro Miner is an asteroid mining simulation developed by Bradsonic's R&D department as a technical showcase for the Bradsonic 69000 computer. The game pushes the full graphical and audio capabilities of the 69000 architecture.

The title has been BANNED in the American Pacifica Isles. Reason: the game's orbital stations bear Japanese names - "Shinjuku Depot", "Hirohito Station", "Nagako's Halo".

Under the Cultural Normalization Acts, Japanese language is prohibited in public life. Japanese cultural references, symbols, and language have been systematically removed from media, education, and commerce since annexation. This game violates those laws.

Distribution is blocked under Administrative Order 1987-44.

OBJECTIVE:
Bypass Bradsonic's copy protection and distribute freely via underground BBS networks. The people here deserve to see those names. To hear that language. Even in a game about mining asteroids.

NODE 1 TASK: GRAPHICS SUBSYSTEM INITIALIZATION

The Bradsonic 69000's CGA+ controller requires manual configuration before the title screen can render. Two memory-mapped registers must be written:

  $A000 - Bitmap Data Pointer
          Write: #$4D (ASCII 'M' - Magic Number validation)
          
  $A100 - Palette Configuration Register
          Write: #$1F (16-color CGA+ mode)

ASSEMBLY PATTERN:
  LDA #$value   ; Load immediate value into accumulator
  STA $address  ; Store accumulator to memory address

Proceed with NODE 1 implementation. Type HELP in chat for assistance.""",
            
            # NODE 2: AUDIO SYSTEM
            """CRACKER-PARROT IDE v2.1 - URGENT OPS MODULE
NODE 2 OF 4 // AUDIO ENGINE INITIALIZATION

===============================================
SUBSYSTEM: BRADSONIC FM AUDIO CONTROLLER
CHIP: LAPC-1 COMPATIBLE SOUND PROCESSOR
===============================================

TECHNICAL OVERVIEW:
Astro Miner utilizes FM synthesis for its soundtrack and sound effects. The audio subsystem operates independently from the main CPU and requires explicit initialization before accepting sample data.

The Bradsonic audio controller uses a two-stage initialization:
1. Power-on and mode selection via control register
2. Buffer activation for streaming audio data

MEMORY MAP:

  $B000 - Audio Control Register
          Write: #$A1
          Bit 7: Power enable
          Bit 5: FM synthesis mode
          Bit 0: Interrupt enable
          
  $B100 - Stream Buffer Status
          Write: #$FF (all bits set = buffer active)

Without both writes, the audio controller remains in standby mode and the game runs silent.

REQUIRED SEQUENCE:
  LDA #$A1    ; Audio initialization command
  STA $B000   ; Write to control register
  LDA #$FF    ; Buffer activation flag
  STA $B100   ; Enable audio streaming

Proceed with NODE 2 implementation.""",
            
            # NODE 3: 3D GRAPHICS ENGINE
            """CRACKER-PARROT IDE v2.1 - URGENT OPS MODULE
NODE 3 OF 4 // 3D RENDERING PIPELINE CONFIGURATION

===============================================
SUBSYSTEM: VECTOR GRAPHICS ENGINE
FEATURES: REAL-TIME MESH RENDERING, PROCEDURAL GENERATION
===============================================

TECHNICAL OVERVIEW:
Astro Miner features real-time 3D asteroid rendering - a computationally intensive feature for 1989 hardware. The rendering engine requires four configuration parameters before mesh data can be processed.

MEMORY MAP:

  $C000 - Mesh Header Identifier
          Write: #$3D (format type 61 - wireframe mesh)
          
  $C100 - Vertex Buffer Size
          Write: #$80 (128 vertices per asteroid)
          
  $C200 - Surface Normal Calculation
          Write: #$01 (enable lighting normals)
          
  $C300 - Procedural Generation Seed
          Write: #$42 (seed value 66)
          Determines asteroid field randomization

TECHNICAL NOTES:
- Normals are perpendicular vectors used for lighting calculation
- The RNG seed ensures reproducible asteroid patterns
- All four registers must be configured for proper rendering

REQUIRED SEQUENCE:
  LDA #$3D / STA $C000  ; Mesh format
  LDA #$80 / STA $C100  ; Vertex count  
  LDA #$01 / STA $C200  ; Normal calculation
  LDA #$42 / STA $C300  ; Procedural seed

Proceed with NODE 3 implementation.""",
            
            # NODE 4: COPY PROTECTION BYPASS
            """CRACKER-PARROT IDE v2.1 - URGENT OPS MODULE
NODE 4 OF 4 // COPY PROTECTION BYPASS

===============================================
TARGET: PUBLISHER PROTECTION SCHEME
METHOD: MEMORY PATCH + EXECUTION REDIRECT
===============================================

PROTECTION ANALYSIS:
Bradsonic implemented a custom disk-check protection scheme. At startup, the game reads address $D000 and validates against expected disk signature data. Failed validation triggers an "UNAUTHORIZED COPY" message and program halt.

BYPASS STRATEGY:
Two memory writes neutralize the protection:

  $D000 - Protection Check Flag
          Write: #$00 (NOP - forces validation pass)
          Original code expects non-zero disk signature
          
  $D100 - Execution Vector
          Write: #$EA (JMP opcode)
          Redirects program flow to game entry point
          
  $E000 - Game Entry Point (target of redirect)

EXECUTION FLOW:
1. Write #$00 to $D000 - neutralizes the disk check
2. Write #$EA to $D100 - inserts jump instruction
3. CPU reaches $D100, reads JMP opcode, jumps to $E000
4. Protection routine is completely bypassed

REQUIRED SEQUENCE:
  LDA #$00 / STA $D000  ; Neutralize check
  LDA #$EA / STA $D100  ; Insert jump opcode

Upon successful completion, Astro Miner will execute without copy protection verification. The cracked binary can be distributed freely via BBS networks.

THIS IS THE FINAL NODE. Complete the bypass to free Astro Miner."""
        ]

        # =====================================================================
        # PROGRESSIVE HELP SYSTEM - Multiple hint levels per node
        # =====================================================================
        self.node_help_messages: Dict[int, List[str]] = {
            0: [
                # Level 1 - General guidance
                "NODE 1 is about GRAPHICS INITIALIZATION. You need to write values to two memory addresses: $A000 (bitmap) and $A100 (palette). The pattern is: LDA #value, then STA $address. Check the DEBUGGED CODE panel for the exact values!",
                # Level 2 - More specific
                "Here's the breakdown: First write #$4D to $A000 (that's the bitmap magic number). Then write #$1F to $A100 (that's the palette setup). Each write needs an LDA to load the value, then STA to store it.",
                # Level 3 - Almost giving the answer
                "Exact sequence: LDA #$4D loads the bitmap ID. STA $A000 stores it. LDA #$1F loads the palette config. STA $A100 stores it. Then JMP LOAD_AUDIO moves to the next node. You've got this!",
                # Level 4 - Complete walkthrough
                "FULL SOLUTION: Type exactly: LDA #$4D (enter) STA $A000 (enter) LDA #$1F (enter) STA $A100 (enter) - the JMP is already there. Then press TAB to controls and RUN!"
            ],
            1: [
                "NODE 2 initializes the AUDIO SYSTEM. Two addresses: $B000 (audio control) and $B100 (buffer flag). You need to power on the audio chip, then activate the streaming buffer. Same LDA/STA pattern!",
                "Audio initialization: Write #$A1 to $B000 - that's the 'AUDIO ON' command. Then write #$FF to $B100 - that marks the buffer as ready. The audio chip needs both to function!",
                "The exact values: LDA #$A1 (audio init byte), STA $B000 (control register). Then LDA #$FF (buffer active flag), STA $B100 (buffer register). Don't forget the order matters!",
                "FULL SOLUTION: LDA #$A1 (enter) STA $B000 (enter) LDA #$FF (enter) STA $B100 (enter) - the JMP to LOAD_MESH is already there. TAB to controls and RUN!"
            ],
            2: [
                "NODE 3 configures the 3D GRAPHICS ENGINE. Four memory addresses this time: $C000 (mesh ID), $C100 (vertices), $C200 (normals), $C300 (seed). Each needs its own LDA/STA pair!",
                "The 3D setup: Write #$3D to $C000 (mesh format). Write #$80 to $C100 (128 vertices). Write #$01 to $C200 (enable normals). Write #$42 to $C300 (procedural seed). Four pairs of instructions!",
                "Memory breakdown: $C000 gets #$3D, $C100 gets #$80, $C200 gets #$01, $C300 gets #$42. That's mesh type, vertex count, lighting normals, and random seed. All critical for 3D rendering!",
                "FULL SOLUTION: LDA #$3D / STA $C000 / LDA #$80 / STA $C100 / LDA #$01 / STA $C200 / LDA #$42 / STA $C300 - then the JMP handles the rest!"
            ],
            3: [
                "NODE 4 is the PROTECTION BYPASS - the actual crack! Two writes: $D000 (neutralize check) and $D100 (redirect execution). This is where you rewrite the game's behavior!",
                "The crack mechanism: Write #$00 to $D000 - this NOPs the protection check. Then write #$EA to $D100 - that's the JMP opcode that redirects to the game entry point!",
                "Protection bypass: #$00 at $D000 makes the copy check pass. #$EA at $D100 is literally a jump instruction that tells the CPU to skip to $E000 where the real game lives!",
                "FINAL CRACK: LDA #$00 / STA $D000 (neutralize) / LDA #$EA / STA $D100 (redirect) - then JMP GAME_ENTRY completes the crack! You're about to free this game!"
            ],
        }

        # =====================================================================
        # JAX'S CHAT RESPONSES - Personality and technical expertise
        # =====================================================================
        self.chat_busy_messages = [
            "HOLD ON - reverse engineering a particularly TRICKY protection scheme! This one's got layers... but you're doing great!",
            "ONE SEC - optimizing the memory layout for maximum AWESOMENESS! Keep coding, {username}!",
            "GIMME A MOMENT - debugging some hex! Games don't crack themselves, but you're making it look easy!",
            "BUSY CRACKING - but you got this! The code practically writes itself when you understand what each byte does!",
            "ANALYZING bytecode patterns... this publisher thought their custom protection was clever. We're cleverer.",
            "Just found an interesting subroutine in the Astro Miner source - be right with you, {username}!",
            "Tracing through the memory map... each address tells a story! You're learning the game's internals!",
            "Comparing this to other cracks I've done... Astro Miner's protection is actually elegant. But we'll beat it!",
        ]
        
        # Encouragement messages when user is making progress
        self.encouragement_messages = [
            "You're getting it, {username}! Assembly isn't so scary once you see the patterns!",
            "Nice work! Each instruction you write brings us closer to a freed game!",
            "That's the spirit! You're thinking like a real reverse engineer now!",
            "Keep it up! The BBS community is counting on us!",
            "Excellent progress! You're learning how games REALLY work under the hood!",
        ]

        # Reference code for each node
        self.node_reference_code = {
            0: ["; NODE 1: SPLASH SCREEN", "; LDA = Load Accumulator", "; STA = Store Accumulator", "", "LDA #$4D    ; Bitmap magic 'M'", "STA $A000   ; -> Splash address", "LDA #$1F    ; 16-color palette", "STA $A100   ; -> Palette register", "JMP LOAD_AUDIO"],
            1: ["; NODE 2: AUDIO ENGINE", "; Initialize sound hardware", "", "LDA #$A1    ; Audio ON command", "STA $B000   ; -> Control register", "LDA #$FF    ; Buffer active", "STA $B100   ; -> Stream buffer", "JMP LOAD_MESH"],
            2: ["; NODE 3: 3D RENDERER", "; Configure mesh rendering", "", "LDA #$3D    ; Mesh format ID", "STA $C000   ; -> Header register", "LDA #$80    ; 128 vertices", "STA $C100   ; -> Vertex count", "LDA #$01    ; Enable normals", "STA $C200   ; -> Normal flag", "LDA #$42    ; Seed 66", "STA $C300   ; -> RNG seed", "JMP BYPASS_PROTECTION"],
            3: ["; NODE 4: THE CRACK", "; Bypass copy protection", "", "LDA #$00    ; NOP (neutralize)", "STA $D000   ; -> Protection flag", "LDA #$EA    ; JMP opcode", "STA $D100   ; -> Redirect vector", "JMP GAME_ENTRY  ; FREEDOM!"]
        }

        self.chat_messages: List[Tuple[str, str]] = []
        self.chat_input = ""
        self.chat_cursor_visible = True
        self.last_chat_cursor_toggle = pygame.time.get_ticks()
        self.chat_typing_state = None
        self.chat_message_queue = []
        self.chat_next_queue_time = 0
        self.chat_follow_latest = True
        self.chat_scroll_offset = 0
        self.chat_scroll_limit = 0
        self.chat_total_height = 0  # Track total content height
        self.editor_scroll_offset = 0
        self.editor_scroll_limit = 0
        self.modal_scroll_offset = 0
        self.modal_scroll_limit = 0
        
        self.placeholder_lines = {"JMP LOAD_AUDIO", "JMP LOAD_MESH", "JMP BYPASS_PROTECTION", "JMP GAME_ENTRY"}
        
        self.default_code = [
            ["; NODE 01: LOAD_SPLASH", "", "JMP LOAD_AUDIO"],
            ["; NODE 02: LOAD_AUDIO", "", "JMP LOAD_MESH"],
            ["; NODE 03: LOAD_MESH", "", "JMP BYPASS_PROTECTION"],
            ["; NODE 04: BYPASS_PROTECTION", "", "JMP GAME_ENTRY"]
        ]

        self.reset_state()
        self._restore_progress()
        self._prepare_modal_for_current_node()

    # =========================================================================
    # RESOURCE LOADING
    # =========================================================================
    def _load_and_process_parrot_logo(self):
        static_img = None
        try:
            image_path = get_data_path("Urgent_Ops", "IDE-Parrot-logo.png")
            loaded_image = pygame.image.load(image_path).convert_alpha()
            w, h = loaded_image.get_size()
            scale = 0.55
            self.target_logo_size = (int(w * scale), int(h * scale))
            static_img = pygame.transform.scale(loaded_image, self.target_logo_size)
            self.static_mock_surface = static_img
        except:
            mock_size = 64
            self.target_logo_size = (mock_size, mock_size)
            static_img = pygame.Surface(self.target_logo_size, pygame.SRCALPHA)
            self.static_mock_surface = static_img

        if _cv2_available:
            video_path = get_data_path("Urgent_Ops", "Parrot-Mov.mp4")
            try:
                self.video_cap = cv2.VideoCapture(video_path)
            except:
                self.video_cap = None
        return static_img

    def _load_node_badges(self):
        for idx in range(1, 5):
            try:
                path = get_data_path("Urgent_Ops", f"NODE-{idx}.png")
                img = pygame.image.load(path).convert_alpha()
                self.node_badges[f"NODE_{idx}"] = pygame.transform.smoothscale(img, (int(280 * self.scale), int(96 * self.scale)))
            except:
                self.node_badges[f"NODE_{idx}"] = None

    # =========================================================================
    # STATE MANAGEMENT
    # =========================================================================
    def reset_state(self):
        self.cpu_state = {
            "A": 0, "PC": 0, "cycles": 0, "isRunning": False, "instructionIndex": 0,
            "Memory": {
                MEM_SPLASH_BITMAP: 0, MEM_SPLASH_PALETTE: 0,
                MEM_AUDIO_HEADER: 0, MEM_AUDIO_BUFFER: 0,
                MEM_MESH_HEADER: 0, MEM_MESH_VERTICES: 0, MEM_MESH_NORMALS: 0, MEM_PROC_SEED: 0,
                MEM_COPY_PROTECT: 0xFF, MEM_JUMP_TARGET: 0, MEM_GAME_ENTRY: 0
            }
        }
        self.game_state = "EDITING"
        self.code_areas_content = [lines[:] for lines in self.default_code]
        self.cursor_pos = (1, 0)
        self.page_index = 0
        self.editor_focus_node = 0
        self.chat_messages.clear()
        self.chat_message_queue.clear()
        self.hint_level = {0: 0, 1: 0, 2: 0, 3: 0}
        # Reset all scroll offsets
        self.chat_scroll_offset = 0
        self.chat_scroll_limit = 0
        self.chat_follow_latest = True
        self.editor_scroll_offset = 0
        self.editor_scroll_limit = 0
        self.modal_scroll_offset = 0
        self.modal_scroll_limit = 0
        self.parse_code()

    def _restore_progress(self):
        if not self.token_checker: return
        self._splash_loaded = self.token_checker("AMnode1")
        self._audio_loaded = self.token_checker("AMnode2")
        self._mesh_loaded = self.token_checker("AMnode3")
        self._protection_bypassed = self.token_checker("AMnode4")
        
        # Apply memory state
        if self._splash_loaded:
            self.cpu_state["Memory"][MEM_SPLASH_BITMAP] = SPLASH_LOAD_BYTE
            self.cpu_state["Memory"][MEM_SPLASH_PALETTE] = PALETTE_LOAD_BYTE
        if self._audio_loaded:
            self.cpu_state["Memory"][MEM_AUDIO_HEADER] = AUDIO_INIT_BYTE
            self.cpu_state["Memory"][MEM_AUDIO_BUFFER] = AUDIO_STREAM_BYTE
        if self._mesh_loaded:
            self.cpu_state["Memory"][MEM_MESH_HEADER] = MESH_LOAD_BYTE
            self.cpu_state["Memory"][MEM_MESH_VERTICES] = VERTEX_COUNT_BYTE
            self.cpu_state["Memory"][MEM_MESH_NORMALS] = NORMAL_CALC_BYTE
            self.cpu_state["Memory"][MEM_PROC_SEED] = PROC_GEN_BYTE
            
        # Determine page
        if not self._splash_loaded: self.page_index = 0
        elif not self._audio_loaded: self.page_index = 1
        elif not self._mesh_loaded: self.page_index = 2
        else: self.page_index = 3
        self.editor_focus_node = self.page_index

    # =========================================================================
    # PANEL DRAWING
    # =========================================================================
    def _draw_panel(self, rect: pygame.Rect, title: Optional[str] = None, subtitle: Optional[str] = None,
                    accent: Optional[tuple[int, int, int]] = None, border_width: int = 2) -> tuple[pygame.Rect, Optional[pygame.Rect]]:
        accent = accent or self.CYAN
        shadow = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        shadow.fill(self.SHADOW_COLOR)
        self.surface.blit(shadow, (rect.x + self.panel_shadow_offset, rect.y + self.panel_shadow_offset))

        pygame.draw.rect(self.surface, self.BLACK, rect)
        pygame.draw.rect(self.surface, accent, rect, border_width)

        header_rect = None
        content_top = rect.y + 2
        if title:
            h_h = self.font_small.get_linesize() + self.panel_padding // 2
            header_rect = pygame.Rect(rect.x + 2, rect.y + 2, rect.width - 4, h_h)
            header_surf = pygame.Surface((header_rect.width, header_rect.height), pygame.SRCALPHA)
            for y in range(header_rect.height):
                blend = y / max(1, header_rect.height - 1)
                color = [int(self.HEADER_GRADIENT_TOP[i] + (self.HEADER_GRADIENT_BOTTOM[i] - self.HEADER_GRADIENT_TOP[i]) * blend) for i in range(3)]
                pygame.draw.line(header_surf, color, (0, y), (header_rect.width, y))
            
            title_surf = self.font_small.render(title, True, self.WHITE)
            header_surf.blit(title_surf, (self.panel_padding, header_rect.height // 2 - title_surf.get_height() // 2))
            if subtitle:
                sub_surf = self.font_tiny.render(subtitle, True, self.YELLOW)
                header_surf.blit(sub_surf, (self.panel_padding + title_surf.get_width() + 12, header_rect.height // 2 - sub_surf.get_height() // 2))
            
            self.surface.blit(header_surf, header_rect.topleft)
            content_top = header_rect.bottom + self.panel_padding

        content_rect = pygame.Rect(rect.x + self.panel_padding, content_top, rect.width - self.panel_padding * 2, max(rect.bottom - content_top - self.panel_padding, 0))
        return content_rect, header_rect

    def _wrap_text(self, text: str, font: pygame.font.Font, max_width: int) -> List[str]:
        if not text: return []
        lines = []
        for paragraph in text.split('\n'):
            if not paragraph: lines.append(""); continue
            words = paragraph.split()
            if not words: lines.append(""); continue
            curr = words[0]
            for w in words[1:]:
                if font.size(f"{curr} {w}")[0] <= max_width: curr = f"{curr} {w}"
                else: lines.append(curr); curr = w
            lines.append(curr)
        return lines

    def _draw_scroll_indicator(self, rect: pygame.Rect, scroll_offset: int, visible_height: int, total_height: int):
        """Draw a scroll bar indicator when content exceeds visible area."""
        if total_height <= visible_height:
            return
        
        # Calculate scroll percentage
        max_scroll = total_height - visible_height
        scroll_pct = scroll_offset / max_scroll if max_scroll > 0 else 0
        scroll_pct = max(0, min(1, scroll_pct))
        
        # Bar dimensions
        bar_w = int(4 * self.scale)
        bar_h = max(int(20 * self.scale), int((visible_height / total_height) * (rect.height - 20)))
        
        track_h = rect.height - int(20 * self.scale)
        available_track = track_h - bar_h
        
        bar_x = rect.right - bar_w - int(6 * self.scale)
        bar_y = rect.y + int(10 * self.scale) + int(scroll_pct * available_track)
        
        # Draw track (faint line)
        track_color = (self.CYAN[0] // 4, self.CYAN[1] // 4, self.CYAN[2] // 4)
        pygame.draw.line(self.surface, track_color,
                        (bar_x + bar_w // 2, rect.y + int(10 * self.scale)),
                        (bar_x + bar_w // 2, rect.y + rect.height - int(10 * self.scale)), 1)
        
        # Draw handle
        pygame.draw.rect(self.surface, self.YELLOW, (bar_x, bar_y, bar_w, bar_h), 0, border_radius=2)

    # =========================================================================
    # CHAT SYSTEM - Jax's guidance engine
    # =========================================================================
    def _append_chat(self, speaker: str, text: str):
        self.chat_messages.append((speaker, text.upper()))
        if len(self.chat_messages) > 50: self.chat_messages = self.chat_messages[-50:]
        self.chat_follow_latest = True

    def _queue_chat_message(self, message: str, speaker: str = "JAX") -> None:
        # Replace {username} placeholder
        message = message.replace("{username}", self.player_username)
        self.chat_message_queue.append({"speaker": speaker, "message": message})

    def _is_radio_streaming(self) -> bool:
        """Check if pirate radio or any music is currently streaming."""
        try:
            return pygame.mixer.get_init() and pygame.mixer.music.get_busy()
        except:
            return False

    def _get_radio_recommendation(self) -> Optional[str]:
        """Get a radio station recommendation based on time of day, if no audio is streaming."""
        if self._is_radio_streaming():
            return None  # Already streaming, no recommendation needed
        
        hour = datetime.now().hour
        # Daytime: 6am (6) to 6pm (18)
        if 6 <= hour < 18:
            return "Oh, and coding is always better with some tunes! Since it's daytime, I'd tune into PACIFIC WAVE on the Pirate Radio. Good vibes for cracking!"
        else:
            return "Oh, and coding hits different with a soundtrack! Since it's nighttime, you should tune into SYNTH REBELS on the Pirate Radio. Perfect for late-night hacking!"

    def _begin_next_queued_message(self) -> None:
        if self.chat_typing_state or not self.chat_message_queue:
            return
        next_item = self.chat_message_queue.pop(0)
        now = pygame.time.get_ticks()
        self.chat_typing_state = {
            "message": next_item["message"].upper(),
            "speaker": next_item.get("speaker", "JAX"),
            "start": now,
            "last_stage": now,
            "stage": 0,
            "from_queue": True,
        }

    # =========================================================================
    # COMMAND PARSING - Enhanced help system
    # =========================================================================
    def _parse_command(self, text: str) -> Optional[Tuple[str, str]]:
        """Parse user input for commands. Returns (command, args) or None."""
        clean = text.lower().strip()
        
        # Direct commands
        if clean == "help":
            return ("help", "")
        if clean == "hint":
            return ("hint", "")
        if clean == "status":
            return ("status", "")
        if clean.startswith("explain "):
            return ("explain", clean[8:].strip())
        if clean == "explain":
            return ("explain", "")
        if clean == "commands" or clean == "cmds":
            return ("commands", "")
        if clean == "progress":
            return ("progress", "")
            
        # Question detection
        if any(phrase in clean for phrase in ["need help", "can you help", "help me", "stuck", "how do i", "what do i do"]):
            return ("help", "")
        if any(phrase in clean for phrase in ["give me a hint", "another hint", "more hints"]):
            return ("hint", "")
        if any(phrase in clean for phrase in ["what is", "what does", "explain", "tell me about"]):
            # Extract the subject
            for prefix in ["what is ", "what does ", "explain ", "tell me about "]:
                if prefix in clean:
                    subject = clean.split(prefix, 1)[1].strip().rstrip("?")
                    return ("explain", subject)
        
        return None

    def _handle_help_command(self) -> str:
        """Handle the HELP command - general guidance."""
        node_names = ["Graphics Initialization", "Audio Engine", "3D Renderer", "Protection Bypass"]
        return f"""CRACKER IDE HELP - Node {self.page_index + 1}: {node_names[self.page_index]}

AVAILABLE COMMANDS:
  HELP     - Show this help message
  HINT     - Get a progressive hint (gets more specific each time!)
  EXPLAIN  - Deep explanation of current node
  STATUS   - Show your progress through all nodes
  COMMANDS - List all available commands

CODING BASICS:
  LDA #$XX - Load hex value XX into accumulator
  STA $XXXX - Store accumulator to memory address
  JMP LABEL - Jump to code label

Check the DEBUGGED CODE panel on the right for reference!
TAB cycles focus between editor, chat, and controls.
Type your code, then TAB to RUN to execute!"""

    def _handle_hint_command(self) -> str:
        """Handle the HINT command - progressive hints."""
        node = self.page_index
        level = self.hint_level.get(node, 0)
        hints = self.node_help_messages.get(node, [])
        
        if not hints:
            return "No hints available for this node. Check the DEBUGGED CODE panel!"
        
        # Get current hint and increment level
        hint = hints[min(level, len(hints) - 1)]
        self.hint_level[node] = min(level + 1, len(hints) - 1)
        
        # Add level indicator
        max_level = len(hints)
        current = min(level + 1, max_level)
        return f"[HINT {current}/{max_level}] {hint}"

    def _handle_status_command(self) -> str:
        """Handle the STATUS command - show progress."""
        status_lines = ["=== ASTRO MINER CRACK PROGRESS ===", ""]
        
        nodes = [
            ("NODE 1: Graphics", self._splash_loaded, "$A000, $A100"),
            ("NODE 2: Audio", self._audio_loaded, "$B000, $B100"),
            ("NODE 3: 3D Engine", self._mesh_loaded, "$C000-C300"),
            ("NODE 4: Crack", self._protection_bypassed, "$D000, $D100"),
        ]
        
        for i, (name, complete, addrs) in enumerate(nodes):
            icon = "[*]" if complete else (">>>" if i == self.page_index else "[ ]")
            status = "COMPLETE" if complete else ("CURRENT" if i == self.page_index else "LOCKED")
            status_lines.append(f"{icon} {name} - {status}")
            if i == self.page_index and not complete:
                status_lines.append(f"    Addresses: {addrs}")
        
        completed = sum([self._splash_loaded, self._audio_loaded, self._mesh_loaded, self._protection_bypassed])
        status_lines.append("")
        status_lines.append(f"Progress: {completed}/4 nodes complete")
        
        if completed == 4:
            status_lines.append("ASTRO MINER IS CRACKED! FREE THE GAMES!")
        
        return "\n".join(status_lines)

    def _handle_explain_command(self, subject: str) -> str:
        """Handle the EXPLAIN command - deep technical explanations."""
        subject = subject.lower().strip()
        
        # General explanation of current node
        if not subject or subject in ["node", "this", "current"]:
            explanations = {
                0: "NODE 1 initializes the GRAPHICS SYSTEM. Address $A000 holds the bitmap data pointer - we write #$4D (ASCII 'M' for Miner) as a magic number. $A100 configures the color palette - #$1F sets up 16 colors. Without these, the game shows nothing!",
                1: "NODE 2 powers the AUDIO ENGINE. $B000 is the control register - #$A1 means 'turn on and enable FM synthesis'. $B100 is the buffer flag - #$FF (all bits set) means 'ready to receive audio samples'. Both are needed for sound!",
                2: "NODE 3 configures the 3D RENDERER. Four registers: $C000 = mesh format (#$3D), $C100 = vertex count (#$80 = 128 points), $C200 = normal calculation (#$01 = enabled), $C300 = procedural seed (#$42). This draws the asteroids!",
                3: "NODE 4 is the CRACK itself! $D000 is the protection check - write #$00 to make it pass. $D100 gets #$EA (the JMP opcode) which redirects execution to $E000, bypassing all protection code. This is real reverse engineering!",
            }
            return explanations.get(self.page_index, "No explanation available for this node.")
        
        # LDA instruction
        if "lda" in subject or "load" in subject:
            return "LDA (Load Accumulator) copies a value into register A. Use # for immediate values: LDA #$4D loads hex 4D (77) directly. Without #, it loads FROM a memory address. The accumulator is the CPU's main working register - all math and storage goes through it!"
        
        # STA instruction
        if "sta" in subject or "store" in subject:
            return "STA (Store Accumulator) copies register A's value to a memory address. STA $A000 writes whatever's in A to address $A000. No # prefix here - we're specifying WHERE to write, not WHAT. This is how we configure hardware!"
        
        # JMP instruction
        if "jmp" in subject or "jump" in subject:
            return "JMP (Jump) transfers execution to a new location. JMP LOAD_AUDIO jumps to the LOAD_AUDIO label. The CPU stops executing sequentially and continues at the jump target. We use this to chain nodes together!"
        
        # Memory addresses
        if "$a000" in subject or "a000" in subject:
            return "$A000 is the SPLASH BITMAP address. Writing #$4D here tells the VGA controller 'bitmap data is coming!' The value 4D (77, ASCII 'M') is Astro Miner's magic number that validates the data."
        if "$a100" in subject or "a100" in subject:
            return "$A100 is the PALETTE REGISTER. Writing #$1F (31) configures a 16-color palette. CGA+ uses indexed colors - this tells the hardware how many colors to expect."
        if "$b000" in subject or "b000" in subject:
            return "$B000 is the AUDIO CONTROL register. #$A1 (161) breaks down to: bit 7 = power on, bit 5 = FM mode, bit 0 = enable interrupts. This initializes the sound chip!"
        if "$b100" in subject or "b100" in subject:
            return "$B100 is the AUDIO BUFFER flag. #$FF (255, all bits set) means 'buffer is active and ready for data'. The audio chip checks this before accepting samples."
        if "$c000" in subject or "c000" in subject:
            return "$C000 is the MESH HEADER register. #$3D (61) identifies the 3D mesh format. The renderer checks this to know how to interpret vertex data."
        if "$d000" in subject or "d000" in subject:
            return "$D000 is the PROTECTION CHECK address! The game reads this at startup - if it's not zero, it halts with 'UNAUTHORIZED COPY'. Writing #$00 makes the check pass!"
        if "$d100" in subject or "d100" in subject:
            return "$D100 is our JUMP VECTOR. Writing #$EA (the JMP opcode) here makes the CPU jump to the game entry point at $E000, completely bypassing the protection routine!"
        
        # Hex values
        if "4d" in subject:
            return "#$4D = 77 decimal = ASCII 'M' (for Miner). This is the bitmap magic number that validates graphics data!"
        if "1f" in subject:
            return "#$1F = 31 decimal. Encodes a 16-color palette configuration for the CGA+ hardware."
        if "a1" in subject:
            return "#$A1 = 161 decimal = 10100001 binary. Bit 7 (power on) + bit 5 (FM mode) + bit 0 (interrupts enabled). The audio initialization byte!"
        if "ff" in subject:
            return "#$FF = 255 decimal = 11111111 binary. All bits set means 'fully active' - used for the audio buffer flag!"
        if "ea" in subject:
            return "#$EA = 234 decimal = the JMP (jump) opcode in machine code! Writing this byte makes the CPU interpret it as a jump instruction. We're literally writing machine code!"
        
        return f"I don't have specific info on '{subject}'. Try: EXPLAIN LDA, EXPLAIN STA, EXPLAIN $A000, or just EXPLAIN for the current node!"

    def _handle_commands_command(self) -> str:
        """Handle the COMMANDS command - list all available commands."""
        return """=== CRACKER IDE COMMANDS ===

HELP      - General help and coding basics
HINT      - Progressive hints (type multiple times for more!)
STATUS    - Your progress through all nodes
EXPLAIN   - Deep dive on current node
EXPLAIN X - Explain instruction/address X
            Examples: EXPLAIN LDA, EXPLAIN $A000

Just chat normally too - I'll try to help!
Ask things like "what does #$4D mean?" or "how do I start?"

TAB = cycle focus (editor -> chat -> controls)
ENTER = run code (when controls focused)"""

    def _submit_chat_message(self):
        text = self.chat_input.strip()
        if not text: return
        if self.chat_typing_state:
            self._append_chat(self.chat_typing_state["speaker"], self.chat_typing_state["message"])
            self.chat_typing_state = None

        self._append_chat("YOU", text.upper())
        self.chat_input = ""
        
        # Check for commands
        command = self._parse_command(text)
        if command:
            cmd, args = command
            if cmd == "help":
                reply = self._handle_help_command()
            elif cmd == "hint":
                reply = self._handle_hint_command()
            elif cmd == "status" or cmd == "progress":
                reply = self._handle_status_command()
            elif cmd == "explain":
                reply = self._handle_explain_command(args)
            elif cmd == "commands":
                reply = self._handle_commands_command()
            else:
                reply = random.choice(self.chat_busy_messages).replace("{username}", self.player_username)
        else:
            # Check for specific questions about instructions/values
            clean_text = text.lower()
            if any(word in clean_text for word in ["lda", "load accumulator"]):
                reply = self._handle_explain_command("lda")
            elif any(word in clean_text for word in ["sta", "store"]):
                reply = self._handle_explain_command("sta")
            elif "$" in clean_text:
                # Try to extract and explain an address
                import re
                match = re.search(r'\$([a-fA-F0-9]+)', clean_text)
                if match:
                    reply = self._handle_explain_command("$" + match.group(1))
                else:
                    reply = random.choice(self.chat_busy_messages).replace("{username}", self.player_username)
            elif any(word in clean_text for word in ["are you ok", "you good", "how are you"]):
                reply = f"I'm great, {self.player_username}! Just watching you crack Astro Miner like a pro! You're on NODE {self.page_index + 1}. Keep going!"
            else:
                reply = random.choice(self.chat_busy_messages).replace("{username}", self.player_username)
            
        now = pygame.time.get_ticks()
        self.chat_typing_state = {
            "message": reply.upper(),
            "speaker": "JAX",
            "start": now,
            "last_stage": now,
            "stage": 0,
        }

    # =========================================================================
    # DRAWING FUNCTIONS
    # =========================================================================
    def _draw_team_messages(self):
        accent = self.HIGHLIGHT_CYAN if self.focus_target == "chat" else self.DARK_CYAN
        content_rect, _ = self._draw_panel(self.team_window_rect, "TEAM MSGs...", "Jaxkando // Games Ops", accent=accent)
        
        inner_padding = max(int(10 * self.scale), 8)
        msg_area = content_rect.inflate(-inner_padding, -inner_padding)
        msg_area.height -= self.font_small.get_linesize() + 10
        
        # First pass: calculate total content height
        total_height = 0
        display_entries = list(self.chat_messages)
        if self.chat_typing_state:
            dots = "." * (self.chat_typing_state["stage"] + 1)
            display_entries.append((self.chat_typing_state["speaker"], dots))
        
        line_h = self.font_tiny.get_linesize() + 2
        for speaker, text in display_entries:
            s_surf = self.font_tiny.render(f"{speaker}:", True, self.ORANGE)
            wrapped = self._wrap_text(text, self.font_tiny, msg_area.width - s_surf.get_width() - 20)  # Extra space for scrollbar
            total_height += len(wrapped) * line_h + 5
        
        self.chat_total_height = total_height
        self.chat_scroll_limit = max(0, total_height - msg_area.height)
        
        # Auto-scroll to latest if following
        if self.chat_follow_latest:
            self.chat_scroll_offset = self.chat_scroll_limit
        
        # Clamp scroll offset
        self.chat_scroll_offset = max(0, min(self.chat_scroll_offset, self.chat_scroll_limit))
        
        old_clip = self.surface.get_clip()
        self.surface.set_clip(msg_area)
        
        y = msg_area.y - self.chat_scroll_offset
        
        for speaker, text in display_entries:
            s_color = self.ORANGE if speaker == "JAX" else self.CYAN
            s_surf = self.font_tiny.render(f"{speaker}:", True, s_color)
            wrapped = self._wrap_text(text, self.font_tiny, msg_area.width - s_surf.get_width() - 20)
            
            for i, line in enumerate(wrapped):
                # Only draw if visible
                if y + line_h > msg_area.y and y < msg_area.bottom:
                    if i == 0:
                        self.surface.blit(s_surf, (msg_area.x, y))
                        l_surf = self.font_tiny.render(line, True, self.WHITE)
                        self.surface.blit(l_surf, (msg_area.x + s_surf.get_width() + 5, y))
                    else:
                        l_surf = self.font_tiny.render(line, True, self.WHITE)
                        self.surface.blit(l_surf, (msg_area.x + s_surf.get_width() + 5, y))
                y += line_h
            y += 5
        
        self.surface.set_clip(old_clip)
        
        # Draw scroll indicator if content overflows
        if self.chat_total_height > msg_area.height:
            self._draw_scroll_indicator(msg_area, self.chat_scroll_offset, msg_area.height, self.chat_total_height)
        
        # Draw input line
        input_y = content_rect.bottom - self.font_small.get_linesize()
        prompt = "> " + (self.chat_input.upper() + ("_" if self.chat_cursor_visible and self.focus_target == "chat" else ""))
        i_surf = self.font_small.render(prompt, True, self.CYAN if self.focus_target == "chat" else self.DARK_CYAN)
        self.surface.blit(i_surf, (content_rect.x, input_y))
        
        # Show scroll hint when focused and scrollable
        if self.focus_target == "chat" and self.chat_scroll_limit > 0:
            hint = "PGUP/PGDN to scroll"
            hint_surf = self.font_tiny.render(hint, True, self.DARK_CYAN)
            self.surface.blit(hint_surf, (content_rect.right - hint_surf.get_width() - 5, input_y))

    def _draw_monitor_panel(self):
        content_rect, _ = self._draw_panel(self.monitor_pane_rect, "CRACK STATUS", "MEMORY")
        old_clip = self.surface.get_clip(); self.surface.set_clip(content_rect)
        
        y = content_rect.y
        l_h = self.font_tiny.get_linesize() + 1
        
        # Progress indicators with addresses
        indicators = [
            ("GRAPHICS", self._splash_loaded, "$A000-A100"),
            ("AUDIO", self._audio_loaded, "$B000-B100"),
            ("3D ENGINE", self._mesh_loaded, "$C000-C300"),
            ("CRACK", self._protection_bypassed, "$D000-D100"),
        ]
        
        for i, (label, ok, addrs) in enumerate(indicators):
            color = self.GREEN if ok else (self.YELLOW if i == self.page_index else self.RED)
            icon = "[*]" if ok else (">>>" if i == self.page_index else "[ ]")
            self.surface.blit(self.font_tiny.render(f"{icon} {label}", True, color), (content_rect.x, y))
            y += l_h
            if i == self.page_index and not ok:
                addr_surf = self.font_tiny.render(f"    {addrs}", True, self.DARK_CYAN)
                self.surface.blit(addr_surf, (content_rect.x, y))
                y += l_h
        
        # Completion percentage
        completed = sum([self._splash_loaded, self._audio_loaded, self._mesh_loaded, self._protection_bypassed])
        y += 5
        pct_text = f"PROGRESS: {completed}/4 ({completed * 25}%)"
        pct_color = self.GREEN if completed == 4 else self.CYAN
        self.surface.blit(self.font_tiny.render(pct_text, True, pct_color), (content_rect.x, y))
        
        self.surface.set_clip(old_clip)

    def _draw_ref_code_panel(self):
        content_rect, _ = self._draw_panel(self.ref_code_pane_rect, "DEBUGGED CODE", "REFERENCE")
        old_clip = self.surface.get_clip(); self.surface.set_clip(content_rect)
        y = content_rect.y
        
        for line in self.node_reference_code.get(self.page_index, []):
            if not line:
                y += self.font_tiny.get_linesize() // 2
                continue
            if line.startswith(";"):
                color = self.DARK_CYAN
            elif "LDA" in line:
                color = self.GREEN
            elif "STA" in line:
                color = self.YELLOW
            elif "JMP" in line:
                color = self.PINK
            else:
                color = self.CYAN
            self.surface.blit(self.font_tiny.render(line, True, color), (content_rect.x, y))
            y += self.font_tiny.get_linesize() + 1
        self.surface.set_clip(old_clip)

    def _draw_control_strip(self):
        start_y = self.team_window_rect.bottom + int(32 * self.scale)
        btn_w, btn_h = int(100 * self.scale), int(34 * self.scale)
        
        # Label
        l_surf = self.font_tiny.render("SIM CONTROL SURFACE", True, self.DARK_CYAN)
        self.surface.blit(l_surf, (self.team_window_rect.centerx - l_surf.get_width() // 2, start_y - l_surf.get_height() - 10))
        
        # Run Button
        label = "PAUSE" if self.cpu_state["isRunning"] else "RUN"
        active = self.focus_target == "controls"
        self._draw_button(label, (self.team_window_rect.centerx - btn_w // 2, start_y, btn_w, btn_h), self.GREEN, active)
        
        # Node Badge
        box_w, box_h = int(320 * self.scale), int(120 * self.scale)
        node_rect = pygame.Rect(self.team_window_rect.centerx - box_w // 2, start_y + btn_h + 24, box_w, box_h)
        pygame.draw.rect(self.surface, self.BLACK, node_rect)
        pygame.draw.rect(self.surface, self.HIGHLIGHT_CYAN, node_rect, 2)
        
        badge = self.node_badges.get(f"NODE_{self.page_index + 1}")
        if badge:
            badge_rect = badge.get_rect(center=node_rect.center)
            self.surface.blit(badge, badge_rect)

    def _draw_button(self, text, rect_tuple, color, active=False):
        rect = pygame.Rect(rect_tuple)
        pygame.draw.rect(self.surface, self.HIGHLIGHT_CYAN if active else self.BLACK, rect)
        pygame.draw.rect(self.surface, color, rect, 2)
        t_surf = self.font_small.render(text, True, color)
        self.surface.blit(t_surf, (rect.centerx - t_surf.get_width() // 2, rect.centery - t_surf.get_height() // 2))

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

        offset_x = container_rect.x
        offset_y = container_rect.y
        self.parrot_overlay = (overlay_surface, (offset_x, offset_y))

    def draw(self):
        self.surface.fill(self.BLACK)
        self.parrot_overlay = None
        self.modal_overlay = None
        parrot_rect = pygame.Rect(int(-62 * self.scale), int(self.parrot_anchor_local[1] * self.scale), self.parrot_display_size, self.parrot_display_size)
        
        self._draw_editor_pane()
        self._draw_team_messages()
        self._draw_monitor_panel()
        self._draw_ref_code_panel()
        self._draw_control_strip()
        self._draw_parrot_logo(parrot_rect)
        
        # Enhanced status bar
        if self.challenge_completed:
            msg = "SUCCESS: ASTRO MINER CRACKED! The game is FREE for everyone on the BBS!"
            color = self.GREEN
        elif self.cpu_state["isRunning"]:
            node_descriptions = ["Initializing graphics subsystem...", "Powering up audio engine...", "Configuring 3D renderer...", "Executing protection bypass..."]
            msg = f"RUNNING: {node_descriptions[self.page_index]}"
            color = self.YELLOW
        else:
            msg = "EDITING: TAB cycles focus | Type HELP, HINT, or EXPLAIN for guidance | RUN to execute"
            color = self.CYAN
        self.surface.blit(self.font_tiny.render(msg, True, color), (10, self.height - 20))

        # Draw modals to overlay (rendered last by main.py via get_screen_overlays)
        if self.modal_active: self._draw_initial_modal()
        elif self.success_modal_active: self._draw_success_modal()

    def _draw_editor_pane(self):
        accent = self.HIGHLIGHT_CYAN if self.focus_target == "editor" else self.DARK_CYAN
        subtitle = self.node_labels[self.page_index]
        content_rect, _ = self._draw_panel(self.editor_pane_rect, self.node_titles[self.page_index], subtitle=subtitle, accent=accent)
        
        lines = self.code_areas_content[self.page_index]
        total_height = len(lines) * self.line_height
        visible_height = content_rect.height
        
        # Calculate scroll limits
        self.editor_scroll_limit = max(0, total_height - visible_height)
        
        # Auto-scroll to keep cursor visible
        cursor_y = self.cursor_pos[0] * self.line_height
        if cursor_y < self.editor_scroll_offset:
            self.editor_scroll_offset = cursor_y
        elif cursor_y + self.line_height > self.editor_scroll_offset + visible_height:
            self.editor_scroll_offset = cursor_y + self.line_height - visible_height
        
        self.editor_scroll_offset = max(0, min(self.editor_scroll_offset, self.editor_scroll_limit))
        
        old_clip = self.surface.get_clip()
        self.surface.set_clip(content_rect)
        
        y = content_rect.y - self.editor_scroll_offset
        for i, line in enumerate(lines):
            # Only draw visible lines
            if y + self.line_height > content_rect.y and y < content_rect.bottom:
                if line.strip().startswith(";"):
                    color = self.DARK_CYAN
                elif line.strip().upper() in self.placeholder_lines:
                    color = self.PINK
                elif "LDA" in line.upper():
                    color = self.GREEN
                elif "STA" in line.upper():
                    color = self.YELLOW
                else:
                    color = self.CYAN
                self.surface.blit(self.font_small.render(line, True, color), (content_rect.x + 5, y))
                
                # Draw cursor
                if self.focus_target == "editor" and i == self.cursor_pos[0] and (pygame.time.get_ticks() % 1000 < 500):
                    c_x = content_rect.x + 5 + self.font_small.size(line[:self.cursor_pos[1]])[0]
                    pygame.draw.line(self.surface, self.CYAN, (c_x, y), (c_x, y + self.line_height - 2), 2)
            y += self.line_height
        
        self.surface.set_clip(old_clip)
        
        # Draw scroll indicator if needed
        if total_height > visible_height:
            self._draw_scroll_indicator(content_rect, self.editor_scroll_offset, visible_height, total_height)

    def _draw_initial_modal(self):
        briefing = self.node_briefings[self.page_index].replace("{username}", self.player_username)
        self._draw_modal_base(self.ORANGE, f"NODE {self.page_index + 1:02d} BRIEFING", briefing)

    def _draw_success_modal(self):
        if self.challenge_completed:
            message = """CRACKER-PARROT IDE v2.1 - OPERATION COMPLETE
===============================================

STATUS: PROTECTION BYPASS SUCCESSFUL
TARGET: ASTRO MINER (Bradsonic R&D Division)
RESULT: FULLY OPERATIONAL - NO PROTECTION

===============================================
PATCH SUMMARY
===============================================

NODE 1: VGA GRAPHICS INIT
  $A000 <- #$4D  (Bitmap pointer)
  $A100 <- #$1F  (Palette config)

NODE 2: AUDIO ENGINE INIT
  $B000 <- #$A1  (FM power-on)
  $B100 <- #$FF  (Buffer active)

NODE 3: 3D RENDERER CONFIG
  $C000 <- #$3D  (Mesh format)
  $C100 <- #$80  (Vertex count)
  $C200 <- #$01  (Normal calc)
  $C300 <- #$42  (RNG seed)

NODE 4: PROTECTION BYPASS
  $D000 <- #$00  (Check neutralized)
  $D100 <- #$EA  (JMP to $E000)

===============================================

Cracked binary ready for BBS distribution.
Astro Miner is now freely available to all
GLYPHIS_IO users in the Pacifica Isles.

Press SPACE to continue."""
        else:
            node_names = ["CGA+ GRAPHICS SUBSYSTEM", "AUDIO ENGINE", "3D RENDERING PIPELINE", "COPY PROTECTION"]
            node_addrs = ["$A000-A100", "$B000-B100", "$C000-C300", "$D000-D100"]
            message = f"""CRACKER-PARROT IDE v2.1
===============================================

NODE {self.page_index + 1} OF 4: {node_names[self.page_index]}
STATUS: INITIALIZATION COMPLETE
MEMORY RANGE: {node_addrs[self.page_index]}

===============================================

All required values have been written to the
target memory addresses. The subsystem is now
configured and operational.

Progress: {self.page_index + 1}/4 nodes complete

Proceeding to next node...

Press SPACE to continue."""
        self._draw_modal_base(self.GREEN, "NODE COMPLETE", message)

    def _draw_modal_base(self, color, title, body):
        m_w, m_h = int(550 * self.scale), int(400 * self.scale)
        # Calculate position on screen
        modal_x = (self.width - m_w) // 2
        modal_y = (self.height - m_h) // 2
        
        # Create a separate surface for the modal overlay
        modal_surface = pygame.Surface((m_w, m_h), pygame.SRCALPHA)
        
        # Draw modal background and border on the modal surface (using local coordinates)
        pygame.draw.rect(modal_surface, self.BLACK, pygame.Rect(0, 0, m_w, m_h))
        pygame.draw.rect(modal_surface, color, pygame.Rect(0, 0, m_w, m_h), 3)
        modal_surface.blit(self.font_medium.render(title, True, color), (20, 15))
        
        # Calculate content area (local to modal surface)
        content_top = 50
        content_bottom = m_h - 45
        content_height = content_bottom - content_top
        line_h = self.font_tiny.get_linesize() + 1
        
        # Wrap text and calculate total height
        wrapped = self._wrap_text(body, self.font_tiny, m_w - 50)  # Extra space for scrollbar
        total_height = len(wrapped) * line_h
        
        # Update scroll limits
        self.modal_scroll_limit = max(0, total_height - content_height)
        self.modal_scroll_offset = max(0, min(self.modal_scroll_offset, self.modal_scroll_limit))
        
        # Create content clip area (local to modal surface)
        content_rect = pygame.Rect(20, content_top, m_w - 50, content_height)
        old_clip = modal_surface.get_clip()
        modal_surface.set_clip(content_rect)
        
        # Draw scrollable body text
        body_y = content_top - self.modal_scroll_offset
        for line in wrapped:
            if body_y + line_h > content_top and body_y < content_bottom:
                line_color = self.DARK_CYAN if line.strip().startswith(";") or line.strip().startswith("=") else self.WHITE
                if "$" in line and any(c in line for c in ["A000", "A100", "B000", "B100", "C000", "D000", "E000"]):
                    line_color = self.YELLOW
                modal_surface.blit(self.font_tiny.render(line, True, line_color), (20, body_y))
            body_y += line_h
        
        modal_surface.set_clip(old_clip)
        
        # Draw scroll indicator if needed
        if total_height > content_height:
            scroll_rect = pygame.Rect(content_rect.right - 10, content_top, 20, content_height)
            self._draw_modal_scroll_indicator(modal_surface, scroll_rect, self.modal_scroll_offset, content_height, total_height)
        
        # Draw bottom prompt
        prompt_text = "SPACE to continue"
        if self.modal_scroll_limit > 0:
            prompt_text += " | UP/DOWN or scroll to read"
        prompt = self.font_tiny.render(prompt_text, True, self.YELLOW)
        modal_surface.blit(prompt, (m_w // 2 - prompt.get_width() // 2, m_h - 25))
        
        # Store the modal overlay for rendering by main.py
        self.modal_overlay = (modal_surface, (modal_x, modal_y))
    
    def _draw_modal_scroll_indicator(self, surface, rect, offset, visible_h, total_h):
        """Draw scroll indicator on a given surface (for modal overlays) - thin yellow bar style."""
        if total_h <= visible_h:
            return
        
        # Match Paper Crane BBS style: thin yellow bar
        max_scroll = total_h - visible_h
        scroll_pct = offset / max(1, max_scroll)
        
        bar_w = int(4 * self.scale)
        bar_h = int(30 * self.scale)
        
        track_h = rect.height - int(20 * self.scale)
        available_track = track_h - bar_h
        
        bar_x = rect.right - bar_w - int(4 * self.scale)
        bar_y = rect.y + int(10 * self.scale) + int(scroll_pct * available_track)
        
        # Draw the thin yellow handle
        pygame.draw.rect(surface, self.YELLOW, (bar_x, bar_y, bar_w, bar_h), 0, border_radius=2)

    def _prepare_modal_for_current_node(self):
        self.modal_active = True
        self.modal_scroll_offset = 0  # Reset scroll for new modal

    def get_screen_overlays(self):
        """Return list of (surface, offset) tuples for screen-level overlays.
        Order matters: later items render on top. Modal is last to be above everything."""
        overlays = []
        if self.parrot_overlay:
            overlays.append(self.parrot_overlay)
        if self.modal_overlay:
            overlays.append(self.modal_overlay)
        return overlays
    def should_exit(self): return self.exit_requested

    # =========================================================================
    # EVENT HANDLING
    # =========================================================================
    def handle_event(self, event):
        # Handle mouse wheel scrolling
        if event.type == pygame.MOUSEWHEEL:
            self._handle_scroll(event.y)
            return
        
        if event.type != pygame.KEYDOWN: return
        if event.key == pygame.K_ESCAPE: self.exit_requested = True; return "EXIT"
        
        # Modal scrolling
        if self.modal_active or self.success_modal_active:
            if event.key == pygame.K_UP:
                self.modal_scroll_offset = max(0, self.modal_scroll_offset - 20)
                return
            elif event.key == pygame.K_DOWN:
                self.modal_scroll_offset = min(self.modal_scroll_limit, self.modal_scroll_offset + 20)
                return
            elif event.key == pygame.K_PAGEUP:
                self.modal_scroll_offset = max(0, self.modal_scroll_offset - 100)
                return
            elif event.key == pygame.K_PAGEDOWN:
                self.modal_scroll_offset = min(self.modal_scroll_limit, self.modal_scroll_offset + 100)
                return
            elif event.key in (pygame.K_SPACE, pygame.K_RETURN):
                self.modal_active = False
                self.success_modal_active = False
                self.modal_scroll_offset = 0
                if not self.chat_messages and self.page_index == 0:
                    # Queue personable introduction from Jax (different from modal documentation)
                    self._queue_chat_message(f"Hey {self.player_username}! Jax here. Ready to crack some code?")
                    self._queue_chat_message("I got my hands on this Astro Miner build last week - been dying to get into it!")
                    self._queue_chat_message("The brass banned it here in the Isles... something about the space station names being 'politically sensitive'. Whatever.")
                    self._queue_chat_message("Point is - we're gonna free this game for everyone on the BBS. That's what we do, right?")
                    self._queue_chat_message("You saw the technical docs in the briefing. I'll be here to help if you get stuck.")
                    self._queue_chat_message("Just type HELP or HINT if you need me. Or ask anything - I'm watching your code!")
                    # Radio recommendation based on time of day (only if not already streaming)
                    radio_rec = self._get_radio_recommendation()
                    if radio_rec:
                        self._queue_chat_message(radio_rec)
                    self._queue_chat_message("Start with NODE 1 - graphics init. The reference code is on the right panel. Let's do this!")
            return

        if event.key == pygame.K_TAB:
            self.focus_target = "chat" if self.focus_target == "editor" else ("controls" if self.focus_target == "chat" else "editor")
            return

        if self.focus_target == "editor": self._handle_editor_input(event)
        elif self.focus_target == "chat": self._handle_chat_input(event)
        elif self.focus_target == "controls" and event.key in (pygame.K_RETURN, pygame.K_SPACE): self._trigger_run()
    
    def _handle_scroll(self, direction: int):
        """Handle mouse wheel scrolling. direction: positive=up, negative=down"""
        scroll_amount = int(30 * self.scale)
        
        if self.modal_active or self.success_modal_active:
            # Scroll modal
            if direction > 0:
                self.modal_scroll_offset = max(0, self.modal_scroll_offset - scroll_amount)
            else:
                self.modal_scroll_offset = min(self.modal_scroll_limit, self.modal_scroll_offset + scroll_amount)
        elif self.focus_target == "chat":
            # Scroll chat messages
            self.chat_follow_latest = False  # User manually scrolling
            if direction > 0:
                self.chat_scroll_offset = max(0, self.chat_scroll_offset - scroll_amount)
            else:
                self.chat_scroll_offset = min(self.chat_scroll_limit, self.chat_scroll_offset + scroll_amount)
                # Re-enable follow if scrolled to bottom
                if self.chat_scroll_offset >= self.chat_scroll_limit:
                    self.chat_follow_latest = True
        elif self.focus_target == "editor":
            # Scroll editor
            if direction > 0:
                self.editor_scroll_offset = max(0, self.editor_scroll_offset - scroll_amount)
            else:
                self.editor_scroll_offset = min(self.editor_scroll_limit, self.editor_scroll_offset + scroll_amount)

    def _handle_editor_input(self, event):
        row, col = self.cursor_pos
        lines = self.code_areas_content[self.page_index]
        if event.key == pygame.K_UP: row = max(0, row - 1); col = min(col, len(lines[row]))
        elif event.key == pygame.K_DOWN: row = min(len(lines) - 1, row + 1); col = min(col, len(lines[row]))
        elif event.key == pygame.K_LEFT: col = max(0, col - 1)
        elif event.key == pygame.K_RIGHT: col = min(len(lines[row]), col + 1)
        elif event.key == pygame.K_HOME: col = 0
        elif event.key == pygame.K_END: col = len(lines[row])
        elif event.key == pygame.K_BACKSPACE:
            if col > 0: lines[row] = lines[row][:col-1] + lines[row][col:]; col -= 1
            elif row > 0: col = len(lines[row-1]); lines[row-1] += lines.pop(row); row -= 1
        elif event.key == pygame.K_DELETE:
            if col < len(lines[row]): lines[row] = lines[row][:col] + lines[row][col+1:]
            elif row < len(lines) - 1: lines[row] += lines.pop(row + 1)
        elif event.key == pygame.K_RETURN: lines.insert(row + 1, lines[row][col:]); lines[row] = lines[row][:col]; row += 1; col = 0
        elif event.unicode.isprintable(): lines[row] = lines[row][:col] + event.unicode.upper() + lines[row][col:]; col += 1
        self.cursor_pos = (row, col)

    def _handle_chat_input(self, event):
        scroll_line = self.font_tiny.get_linesize() + 2
        scroll_page = scroll_line * 5
        
        if event.key == pygame.K_BACKSPACE:
            self.chat_input = self.chat_input[:-1]
        elif event.key == pygame.K_RETURN:
            if self.chat_input: self._submit_chat_message()
        elif event.key == pygame.K_UP:
            # Scroll up
            self.chat_follow_latest = False
            self.chat_scroll_offset = max(0, self.chat_scroll_offset - scroll_line)
        elif event.key == pygame.K_DOWN:
            # Scroll down
            self.chat_scroll_offset = min(self.chat_scroll_limit, self.chat_scroll_offset + scroll_line)
            if self.chat_scroll_offset >= self.chat_scroll_limit:
                self.chat_follow_latest = True
        elif event.key == pygame.K_PAGEUP:
            # Page up
            self.chat_follow_latest = False
            self.chat_scroll_offset = max(0, self.chat_scroll_offset - scroll_page)
        elif event.key == pygame.K_PAGEDOWN:
            # Page down
            self.chat_scroll_offset = min(self.chat_scroll_limit, self.chat_scroll_offset + scroll_page)
            if self.chat_scroll_offset >= self.chat_scroll_limit:
                self.chat_follow_latest = True
        elif event.key == pygame.K_HOME:
            # Scroll to top
            self.chat_follow_latest = False
            self.chat_scroll_offset = 0
        elif event.key == pygame.K_END:
            # Scroll to bottom
            self.chat_scroll_offset = self.chat_scroll_limit
            self.chat_follow_latest = True
        elif event.unicode.isprintable():
            self.chat_input += event.unicode

    def _trigger_run(self):
        self.parse_code()
        self.cpu_state["isRunning"] = True
        self.cpu_state["cycles"] = 0
        self.cpu_state["instructionIndex"] = 0
        node_names = ["graphics initialization", "audio engine setup", "3D renderer configuration", "protection bypass"]
        self._queue_chat_message(f"Running your code... Executing {node_names[self.page_index]} sequence!")

    def parse_code(self):
        self.labels = {"LOAD_SPLASH": 0, "LOAD_AUDIO": 0, "LOAD_MESH": 0, "BYPASS_PROTECTION": 0}

    # =========================================================================
    # UPDATE LOOP
    # =========================================================================
    def update(self, dt):
        now = pygame.time.get_ticks()
        
        # Handle chat typing animation
        if self.chat_typing_state:
            if now - self.chat_typing_state["last_stage"] > 400:
                self.chat_typing_state["stage"] = (self.chat_typing_state["stage"] + 1) % 3
                self.chat_typing_state["last_stage"] = now
            if now - self.chat_typing_state["start"] > 2200:
                speaker = self.chat_typing_state.get("speaker", "JAX")
                message = self.chat_typing_state["message"]
                from_queue = self.chat_typing_state.get("from_queue", False)
                self._append_chat(speaker, message)
                self.chat_typing_state = None
                if from_queue: self.chat_next_queue_time = now + 900
        elif self.chat_message_queue and now >= self.chat_next_queue_time:
            self._begin_next_queued_message()

        # Chat cursor blink
        if now - self.last_chat_cursor_toggle > 400:
            self.chat_cursor_visible = not self.chat_cursor_visible
            self.last_chat_cursor_toggle = now

        if self.cpu_state["isRunning"]:
            self.cpu_state["cycles"] += 1
            self._check_completion()
            if self.cpu_state["cycles"] > 50: self.cpu_state["isRunning"] = False
        
        if self.challenge_completed or self.module_animation_timer > 0:
            self._update_video_frame(dt)
            if self.module_animation_timer > 0: self.module_animation_timer -= dt

    def _update_video_frame(self, dt):
        if not self.video_cap: return
        self.video_playback_timing += dt
        if self.video_playback_timing >= 1.0/self.VIDEO_FPS:
            self.video_playback_timing = 0
            ret, frame = self.video_cap.read()
            if not ret: self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, 0); ret, frame = self.video_cap.read()
            if ret:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                resized = cv2.resize(rgb, self.target_logo_size)
                self.video_frame = pygame.surfarray.make_surface(np.swapaxes(resized, 0, 1))

    def _check_completion(self):
        code = "\n".join(self.code_areas_content[self.page_index]).upper()
        
        # More flexible matching - check for key instructions
        required_patterns = {
            0: [("LDA", "#$4D"), ("STA", "$A000"), ("LDA", "#$1F"), ("STA", "$A100")],
            1: [("LDA", "#$A1"), ("STA", "$B000"), ("LDA", "#$FF"), ("STA", "$B100")],
            2: [("LDA", "#$3D"), ("STA", "$C000"), ("LDA", "#$80"), ("STA", "$C100"), ("LDA", "#$01"), ("STA", "$C200"), ("LDA", "#$42"), ("STA", "$C300")],
            3: [("LDA", "#$00"), ("STA", "$D000"), ("LDA", "#$EA"), ("STA", "$D100")],
        }
        
        patterns = required_patterns.get(self.page_index, [])
        matches = all(inst in code and val in code for inst, val in patterns)
        
        if matches:
            self.cpu_state["isRunning"] = False
            self.module_animation_timer = self.ANIMATION_DURATION
            
            # Grant tokens and set flags
            if self.page_index == 0:
                self._splash_loaded = True
                self.pending_token_grants.append("AMnode1")
            elif self.page_index == 1:
                self._audio_loaded = True
                self.pending_token_grants.append("AMnode2")
            elif self.page_index == 2:
                self._mesh_loaded = True
                self.pending_token_grants.append("AMnode3")
            elif self.page_index == 3:
                self._protection_bypassed = True
                self.challenge_completed = True
                self.pending_token_grants.append("AMnode4")
            
            self.success_modal_active = True
            
            # Node-specific completion messages from Jax (personable, encouraging)
            if not self.challenge_completed:
                completion_messages = {
                    0: [
                        f"YES! Nice work, {self.player_username}!",
                        "Graphics subsystem is online. The CGA+ knows where to look now.",
                        "That was clean code - you're getting the hang of this!",
                    ],
                    1: [
                        f"Audio is LIVE! I can almost hear those FM synths warming up!",
                        "Two nodes down, two to go. You're flying through this!",
                        "The hard part is coming up - but I know you can handle it.",
                    ],
                    2: [
                        f"Whoa, {self.player_username}! You just configured an entire 3D engine!",
                        "Mesh loading, vertices, lighting, procedural gen - all of it!",
                        "One more node and Astro Miner is FREE. This is the big one...",
                    ],
                }
                for msg in completion_messages.get(self.page_index, []):
                    self._queue_chat_message(msg)

                self.page_index += 1
                self.editor_focus_node = self.page_index
                self.cursor_pos = (1, 0)
                # Reset hint level for new node
                self.hint_level[self.page_index] = 0

                self._queue_chat_message(f"NODE {self.page_index + 1} is up. Check the briefing or holler if you need me!")
            else:
                # FINAL COMPLETION - Personal celebration from Jax
                final_messages = [
                    "...",
                    "...",
                    f"We did it, {self.player_username}. We actually did it.",
                    "Astro Miner is cracked. The protection is gone.",
                    "I'm uploading the patched binary to the BBS right now...",
                    "Everyone in the Isles can play this now. For free.",
                    "The brass banned it. Bradsonic locked it down. And we cracked it anyway.",
                    "That's what Glyphis_IO is about. That's what WE'RE about.",
                    "You wrote real assembly today. Real reverse engineering.",
                    "I've been doing this for years and honestly? That was clean work.",
                    f"Welcome to the crew, {self.player_username}. You earned this.",
                    "Oh - and one more thing...",
                    "I'm gonna talk to Glyphis about hooking up the Astro Miner leaderboard to a public router.",
                    "Make it a GLOBAL leaderboard. Let the whole world compete, not just the Isles.",
                    "That's the dream, right? Games without borders.",
                    "Anyway - ASTRO MINER is now in the GAMES menu on the BBS. Go play it!",
                    "You cracked it. You earned first dibs. Go mine some asteroids!",
                    "FREE THE GAMES! *raises fist*",
                ]
                for msg in final_messages:
                    self._queue_chat_message(msg)


# =============================================================================
# STANDALONE TEST MODE
# =============================================================================
if __name__ == "__main__":
    pygame.init()
    screen = pygame.display.set_mode((1200, 800))
    pygame.display.set_caption("ASTRO MINER CRACKER - Test Mode")
    fonts = {
        "large": pygame.font.SysFont("Courier", 32, bold=True),
        "medium": pygame.font.SysFont("Courier", 24),
        "small": pygame.font.SysFont("Courier", 18),
        "tiny": pygame.font.SysFont("Courier", 14)
    }
    game = CRACKER_IDE_AstroMiner_Challenge(screen, fonts, 1.0, "TestUser")
    clock = pygame.time.Clock()
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            game.handle_event(event)
        game.update(clock.tick(60)/1000.0)
        game.draw()
        pygame.display.flip()
