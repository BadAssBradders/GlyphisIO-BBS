"""
Echo Chamber BBS - Outside BBS Experience
=========================================
The Echo Chamber - 15050 kHz
Unlocked by listening to the Echo Chamber pirate radio station.

A hacker underground BBS featuring banned ASM tutorials for the 
Bradsonic 69000 processor and underground programming resources.

Codename: SHADOWBYTE
"""

import math
import pygame
import os
import sys
import random
from typing import Callable, Optional, List, Dict

try:
    from utils import get_data_path
except Exception:
    # Fallback for standalone import during development
    def get_data_path(*path_parts):
        # This file is in Data/Outside_BBSs/EchoChamberBBS/
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        return os.path.join(base, *path_parts)


# === COLOR PALETTE (Vegas Neon / Hacker Terminal) ===
GREEN = (0, 200, 100)           # Primary neon green
GREEN_BRIGHT = (100, 255, 150)  # Highlight green
GREEN_DIM = (0, 80, 40)         # Dim green for borders
WHITE = (220, 220, 220)         # Off-white text
GOLD = (255, 215, 0)            # Gold accents
CYAN = (0, 255, 240)            # Cyan for special highlights
RED = (255, 50, 80)             # Warning/error red
BG = (5, 8, 12)                 # Very dark blue-black
BG_PANEL = (10, 15, 20)         # Panel background
STAR_COLOR = (150, 150, 150)    # Twinkling stars


class EchoChamberBBS:
    """
    The Echo Chamber BBS experience.
    
    A hacker underground BBS featuring banned ASM tutorials for the
    Bradsonic 69000 processor and underground programming resources.
    
    States: splash -> menu -> panel. ESC exits.
    """

    def __init__(self, width: int, height: int, scale: float, on_exit: Optional[Callable[[], None]] = None):
        self.width = width
        self.height = height
        self.scale = scale
        self.on_exit = on_exit

        # Fonts
        self.font_title = self._load_font("Retro Gaming.ttf", int(28 * self.scale))
        self.font_label = self._load_font("Retro Gaming.ttf", int(18 * self.scale))
        self.font_body = self._load_font("Retro Gaming.ttf", int(14 * self.scale))
        self.font_small = self._load_font("Retro Gaming.ttf", int(12 * self.scale))
        self.font_code = self._load_font("Retro Gaming.ttf", int(11 * self.scale))

        # Assets
        self.banner_image = self._load_banner_image()
        self.scanline_surf = self._create_scanline_surface()

        # Stars for background
        self.stars = self._generate_stars(60)
        self.star_timer = 0.0

        # State
        self.state = "connecting"
        self.connecting_timer = 0.0
        self.connecting_log = []
        self.connecting_max_lines = 12
        
        self.menu_options = [
            "BANNED ASM TUTORIALS",
            "UNDERGROUND PROG. FORUMS",
            "DARKNET FILEZ",
            "SYSTEM OPS",
            "LOGOFF"
        ]
        self.menu_index = 0
        self.active_panel: Optional[str] = None
        self.cursor_timer = 0.0
        self.cursor_visible = True
        self.request_exit = False
        self.glow_timer = 0.0
        self.panel_scroll = 0

        # Tutorial system
        self.tutorials = self._build_tutorials()
        self.tutorial_selected_index = 0
        self.tutorial_open_index: Optional[int] = None
        self.tutorial_scroll = 0
        self.tutorial_list_scroll = 0

        # Forum system
        self.forum_threads = self._build_forum_threads()
        self.forum_selected_index = 0
        self.forum_open_index: Optional[int] = None
        self.forum_scroll = 0
        self.forum_list_scroll = 0

        # Darknet files
        self.darknet_files = self._build_darknet_files()
        self.darknet_selected_index = 0
        self.darknet_scroll = 0
        self.downloading_file: Optional[int] = None
        self.download_progress = 0.0
        self.download_speed = 0.0
        self.download_timer = 0.0

    def _load_font(self, filename: str, size: int) -> pygame.font.Font:
        """Load a font with fallback to system font."""
        try:
            # Try local directory first
            local_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
            if os.path.exists(local_path):
                return pygame.font.Font(local_path, max(1, size))
            # Try data path
            data_path = get_data_path(filename)
            if os.path.exists(data_path):
                return pygame.font.Font(data_path, max(1, size))
        except Exception:
            pass
        return pygame.font.Font(None, max(1, size))

    def _load_banner_image(self) -> Optional[pygame.Surface]:
        """Load the echo-banner.png splash image."""
        try:
            # Try local directory first
            local_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "echo-banner.png")
            if os.path.exists(local_path):
                image = pygame.image.load(local_path).convert_alpha()
            else:
                image = pygame.image.load(get_data_path("images", "echo-banner.png")).convert_alpha()
            
            # Scale to fit screen nicely
            img_w, img_h = image.get_size()
            max_w = int(self.width * 0.85)
            max_h = int(self.height * 0.75)
            scale = min(max_w / img_w, max_h / img_h, 1.0)
            if scale < 1.0:
                image = pygame.transform.smoothscale(image, (int(img_w * scale), int(img_h * scale)))
            return image
        except Exception as e:
            print(f"[EchoChamber] Could not load banner: {e}")
            return None

    def _create_scanline_surface(self) -> pygame.Surface:
        """Create CRT scanline overlay effect."""
        surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        for y in range(0, self.height, 3):
            pygame.draw.line(surf, (0, 0, 0, 30), (0, y), (self.width, y))
        return surf

    def _generate_stars(self, count: int) -> List[Dict]:
        """Generate random star positions for background."""
        stars = []
        for _ in range(count):
            stars.append({
                'x': random.randint(0, self.width),
                'y': random.randint(0, self.height),
                'phase': random.uniform(0, math.pi * 2),
                'speed': random.uniform(1.5, 3.5),
                'size': random.choice([1, 1, 1, 2])
            })
        return stars

    def _build_tutorials(self) -> List[Dict]:
        """Build the ASM tutorial database for Bradsonic 69000."""
        return [
            {
                "title": "BRADSONIC 69000 OVERVIEW",
                "category": "FUNDAMENTALS",
                "lines": [
                    "BRADSONIC 69000 ARCHITECTURE",
                    "=============================",
                    "",
                    "The Bradsonic 69000 is a powerful 32-bit",
                    "processor from the hybrid American-Japanese",
                    "tech industry. Found in arcade systems and",
                    "industrial controllers throughout the Isles.",
                    "",
                    "KEY SPECIFICATIONS:",
                    "- 32-bit data bus, 24-bit address bus",
                    "- 16 general purpose registers (D0-D15)",
                    "- 8 address registers (A0-A7)",
                    "- Stack pointer (SP), Program counter (PC)",
                    "- Status register with condition codes",
                    "",
                    "REGISTER LAYOUT:",
                    "  D0-D7   : Data registers (32-bit)",
                    "  D8-D15  : Extended data (shadow mode)",
                    "  A0-A6   : Address registers",
                    "  A7/SP   : Stack pointer",
                    "  PC      : Program counter (24-bit)",
                    "  SR      : Status register",
                    "",
                    "The 69000 uses big-endian byte ordering",
                    "and supports multiple addressing modes.",
                    "",
                    "THE AMERICAN ADMINISTRATION SUPPRESSES",
                    "THIS CHIP - TOO MUCH INDEPENDENT POWER.",
                ]
            },
            {
                "title": "BASIC INSTRUCTION SET",
                "category": "FUNDAMENTALS",
                "lines": [
                    "BRADSONIC 69000 BASIC INSTRUCTIONS",
                    "===================================",
                    "",
                    "DATA MOVEMENT:",
                    "  MOVE.B src,dst  ; Move byte",
                    "  MOVE.W src,dst  ; Move word (16-bit)",
                    "  MOVE.L src,dst  ; Move long (32-bit)",
                    "  LEA ea,An       ; Load effective address",
                    "  PEA ea          ; Push effective address",
                    "",
                    "EXAMPLE - COPY MEMORY BLOCK:",
                    "",
                    "  ; Copy 256 bytes from $1000 to $2000",
                    "  LEA     $1000,A0      ; Source",
                    "  LEA     $2000,A1      ; Destination",
                    "  MOVE.W  #255,D0       ; Counter",
                    "copy_loop:",
                    "  MOVE.B  (A0)+,(A1)+   ; Copy byte",
                    "  DBRA    D0,copy_loop  ; Decrement & branch",
                    "",
                    "ARITHMETIC:",
                    "  ADD.L  D0,D1    ; D1 = D1 + D0",
                    "  SUB.W  #100,D2  ; D2 = D2 - 100",
                    "  MULU   D3,D4    ; Unsigned multiply",
                    "  DIVU   D5,D6    ; Unsigned divide",
                    "",
                    "LOGIC:",
                    "  AND.L  #$FF,D0  ; Mask lower byte",
                    "  OR.B   #$80,D1  ; Set high bit",
                    "  EOR.W  D2,D3    ; XOR operation",
                    "  NOT.L  D4       ; Bitwise NOT",
                ]
            },
            {
                "title": "MEMORY ADDRESSING MODES",
                "category": "FUNDAMENTALS",
                "lines": [
                    "ADDRESSING MODES - BRADSONIC 69000",
                    "===================================",
                    "",
                    "1. REGISTER DIRECT:",
                    "   MOVE.L D0,D1        ; Register to register",
                    "",
                    "2. IMMEDIATE:",
                    "   MOVE.L #$1234,D0    ; Load constant",
                    "",
                    "3. ABSOLUTE:",
                    "   MOVE.B $FF00,D0     ; From address",
                    "   MOVE.W D1,$FF02     ; To address",
                    "",
                    "4. ADDRESS REGISTER INDIRECT:",
                    "   MOVE.L (A0),D0      ; Contents at A0",
                    "   MOVE.B D1,(A1)      ; Store at A1",
                    "",
                    "5. POST-INCREMENT:",
                    "   MOVE.B (A0)+,D0     ; Read, then A0++",
                    "",
                    "6. PRE-DECREMENT:",
                    "   MOVE.B D0,-(A1)     ; A1--, then write",
                    "",
                    "7. DISPLACEMENT:",
                    "   MOVE.W 4(A2),D0     ; A2 + 4 offset",
                    "",
                    "8. INDEXED:",
                    "   MOVE.B 0(A3,D4),D5  ; A3 + D4 index",
                    "",
                    "EXAMPLE - STRING COPY WITH NULL CHECK:",
                    "",
                    "strcpy:",
                    "  MOVE.B  (A0)+,D0     ; Get char",
                    "  MOVE.B  D0,(A1)+     ; Store char",
                    "  BNE.S   strcpy       ; Loop if not null",
                    "  RTS                  ; Return",
                ]
            },
            {
                "title": "BRANCHING & LOOPS",
                "category": "CONTROL FLOW",
                "lines": [
                    "CONTROL FLOW - BRADSONIC 69000",
                    "===============================",
                    "",
                    "CONDITIONAL BRANCHES:",
                    "  BEQ label   ; Branch if equal (Z=1)",
                    "  BNE label   ; Branch if not equal",
                    "  BGT label   ; Branch if greater than",
                    "  BLT label   ; Branch if less than",
                    "  BGE label   ; Branch if >= ",
                    "  BLE label   ; Branch if <=",
                    "  BCS label   ; Branch if carry set",
                    "  BCC label   ; Branch if carry clear",
                    "",
                    "UNCONDITIONAL:",
                    "  BRA label   ; Branch always",
                    "  JMP addr    ; Jump to address",
                    "  JSR addr    ; Jump to subroutine",
                    "  RTS         ; Return from subroutine",
                    "",
                    "LOOP CONSTRUCT - DBRA:",
                    "",
                    "  ; Print 10 asterisks",
                    "  MOVE.W  #9,D0        ; Counter (0-9)",
                    "loop:",
                    "  MOVE.B  #'*',($FF00) ; Output char",
                    "  DBRA    D0,loop      ; D0--, branch if >= 0",
                    "",
                    "COMPARE AND BRANCH PATTERN:",
                    "",
                    "  CMP.L   #100,D0      ; Compare D0 to 100",
                    "  BGE     over_100     ; Branch if >= 100",
                    "  ; Code for < 100",
                    "  BRA     done",
                    "over_100:",
                    "  ; Code for >= 100",
                    "done:",
                ]
            },
            {
                "title": "SUBROUTINES & STACK",
                "category": "CONTROL FLOW",
                "lines": [
                    "SUBROUTINES & STACK OPERATIONS",
                    "===============================",
                    "",
                    "STACK BASICS:",
                    "  A7 (SP) is the stack pointer",
                    "  Stack grows DOWN in memory",
                    "  PUSH = pre-decrement: -(SP)",
                    "  POP  = post-increment: (SP)+",
                    "",
                    "SUBROUTINE CALL:",
                    "",
                    "  ; Caller pushes parameters",
                    "  MOVE.L  param1,-(SP)  ; Push param",
                    "  JSR     my_function   ; Call",
                    "  ADDQ.L  #4,SP         ; Clean stack",
                    "",
                    "SUBROUTINE TEMPLATE:",
                    "",
                    "my_function:",
                    "  MOVEM.L D0-D3/A0-A2,-(SP) ; Save regs",
                    "  LINK    A6,#-16        ; Stack frame",
                    "  ",
                    "  ; Function body here",
                    "  MOVE.L  8(A6),D0       ; Get param",
                    "  ",
                    "  UNLK    A6             ; Restore frame",
                    "  MOVEM.L (SP)+,D0-D3/A0-A2 ; Restore regs",
                    "  RTS                    ; Return",
                    "",
                    "REGISTER SAVE CONVENTION:",
                    "  D0-D1, A0-A1 : Scratch (caller saves)",
                    "  D2-D7, A2-A6 : Preserved (callee saves)",
                ]
            },
            {
                "title": "BIT MANIPULATION",
                "category": "ADVANCED",
                "lines": [
                    "BIT MANIPULATION TECHNIQUES",
                    "===========================",
                    "",
                    "BIT OPERATIONS:",
                    "  BTST   #n,Dn    ; Test bit n",
                    "  BSET   #n,Dn    ; Set bit n",
                    "  BCLR   #n,Dn    ; Clear bit n",
                    "  BCHG   #n,Dn    ; Toggle bit n",
                    "",
                    "SHIFT OPERATIONS:",
                    "  LSL.W  #n,Dn    ; Logical shift left",
                    "  LSR.L  #n,Dn    ; Logical shift right",
                    "  ASL.W  #n,Dn    ; Arithmetic shift left",
                    "  ASR.L  #n,Dn    ; Arithmetic shift right",
                    "  ROL.W  #n,Dn    ; Rotate left",
                    "  ROR.L  #n,Dn    ; Rotate right",
                    "",
                    "EXAMPLE - EXTRACT BITS 4-7:",
                    "",
                    "  MOVE.B  input,D0",
                    "  LSR.B   #4,D0        ; Shift right 4",
                    "  AND.B   #$0F,D0      ; Mask low nibble",
                    "",
                    "EXAMPLE - SET PIXEL AT X,Y:",
                    "",
                    "  ; D0 = X coord, D1 = Y coord",
                    "  ; A0 = framebuffer base",
                    "  MULU    #320,D1      ; Y * width",
                    "  ADD.L   D0,D1        ; + X",
                    "  MOVE.B  #$FF,0(A0,D1.L) ; Set pixel",
                    "",
                    "FAST MULTIPLY BY SHIFT-ADD:",
                    "",
                    "  ; Multiply D0 by 10",
                    "  MOVE.L  D0,D1        ; D1 = x",
                    "  LSL.L   #2,D0        ; D0 = x*4",
                    "  ADD.L   D1,D0        ; D0 = x*5",
                    "  LSL.L   #1,D0        ; D0 = x*10",
                ]
            },
            {
                "title": "INTERRUPT HANDLING",
                "category": "ADVANCED",
                "lines": [
                    "INTERRUPT HANDLING - BRADSONIC 69000",
                    "=====================================",
                    "",
                    "INTERRUPT VECTOR TABLE (at $000000):",
                    "  $00 : Initial SSP",
                    "  $04 : Initial PC (reset vector)",
                    "  $08 : Bus error",
                    "  $0C : Address error",
                    "  $10 : Illegal instruction",
                    "  $14 : Zero divide",
                    "  ...",
                    "  $60 : Spurious interrupt",
                    "  $64-$7C : Auto-vector interrupts 1-7",
                    "  $80-$FC : User vectors",
                    "",
                    "INTERRUPT SERVICE ROUTINE:",
                    "",
                    "vblank_isr:",
                    "  MOVEM.L D0-D1/A0,-(SP)  ; Save regs",
                    "  ",
                    "  ; Handle vertical blank",
                    "  ADDQ.W  #1,frame_count",
                    "  BSR     update_sprites",
                    "  ",
                    "  MOVEM.L (SP)+,D0-D1/A0  ; Restore",
                    "  RTE                      ; Return",
                    "",
                    "SETTING UP INTERRUPT:",
                    "",
                    "  ; Install VBLANK handler at vector $70",
                    "  LEA     vblank_isr,A0",
                    "  MOVE.L  A0,$70",
                    "  ",
                    "  ; Enable interrupts (level 3)",
                    "  MOVE.W  #$2300,SR",
                    "",
                    "!! AMERICAN TECH SWEEPS MONITOR ISR !!",
                    "!! USE SHADOW VECTORS FOR STEALTH !!",
                ]
            },
            {
                "title": "SELF-MODIFYING CODE",
                "category": "FORBIDDEN",
                "lines": [
                    "!! CLASSIFIED - FORBIDDEN TECHNIQUES !!",
                    "========================================",
                    "",
                    "SELF-MODIFYING CODE (SMC)",
                    "",
                    "Technique suppressed by American",
                    "administration - 'Dynamic Code Alteration'",
                    "",
                    "BASIC SMC PATTERN:",
                    "",
                    "  ; Modify immediate value at runtime",
                    "patch_point:",
                    "  MOVE.L  #$0000,D0     ; Placeholder",
                    "  ...",
                    "  ",
                    "  ; Patch the instruction",
                    "  LEA     patch_point+2,A0",
                    "  MOVE.L  new_value,(A0)",
                    "",
                    "DECRYPTION STUB:",
                    "",
                    "decrypt_code:",
                    "  LEA     encrypted_start,A0",
                    "  LEA     encrypted_end,A1",
                    "  MOVE.B  #$A5,D1       ; XOR key",
                    ".loop:",
                    "  MOVE.B  (A0),D0",
                    "  EOR.B   D1,D0         ; Decrypt byte",
                    "  MOVE.B  D0,(A0)+",
                    "  CMP.L   A0,A1",
                    "  BNE.S   .loop",
                    "  JMP     encrypted_start ; Execute",
                    "",
                    "!! USE AT YOUR OWN RISK !!",
                    "!! ADMIN SCANNERS DETECT SMC !!",
                ]
            },
            {
                "title": "STEALTH TECHNIQUES",
                "category": "FORBIDDEN",
                "lines": [
                    "!! TOP SECRET - ANTI-DETECTION !!",
                    "==================================",
                    "",
                    "ADMINISTRATION SCANNER EVASION",
                    "",
                    "1. TIMING OBFUSCATION:",
                    "   Insert NOPs to break signature",
                    "",
                    "stealth_routine:",
                    "  NOP",
                    "  MOVE.L  D0,D1",
                    "  NOP",
                    "  NOP",
                    "  ADD.L   D2,D1     ; Actual operation",
                    "  NOP",
                    "",
                    "2. REGISTER ROTATION:",
                    "   Never use same register pattern",
                    "",
                    "  ; Rotate registers each call",
                    "  EXG     D0,D4",
                    "  EXG     D1,D5",
                    "  EXG     D2,D6",
                    "",
                    "3. POLYMORPHIC WRAPPER:",
                    "",
                    "poly_entry:",
                    "  BSR     get_random",
                    "  AND.L   #7,D0",
                    "  LSL.L   #2,D0",
                    "  LEA     jump_table,A0",
                    "  MOVE.L  0(A0,D0),A0",
                    "  JMP     (A0)",
                    "",
                    "4. SHADOW MEMORY:",
                    "   Execute from unmapped regions",
                    "   Scanner blind spots: $F00000-$F0FFFF",
                    "",
                    "REMEMBER: KNOWLEDGE IS POWER",
                    "BUT POWER DRAWS ATTENTION",
                ]
            },
            {
                "title": "PERFORMANCE & PIPELINE",
                "category": "ADVANCED",
                "lines": [
                    "BRADSONIC 69000 PIPELINE",
                    "========================",
                    "",
                    "3-STAGE PIPELINE:",
                    "  FETCH -> DECODE -> EXECUTE",
                    "  1-cycle fetch, 1-cycle decode,",
                    "  EXEC varies by instruction.",
                    "",
                    "ALIGNMENT MATTERS:",
                    "  Align hot loops to 4-byte boundaries",
                    "  to reduce fetch stalls.",
                    "",
                    "ZERO-OVERHEAD LOOPS (DBRA):",
                    "  DBRA is your friend. Keep the loop",
                    "  body small and registers hot.",
                    "",
                    "PREFETCH TRICK:",
                    "  Place a NOP before heavy branches",
                    "  to let the fetch stage stay ahead.",
                    "",
                    "MICRO-BENCH SNIPPET:",
                    "  ; Measure 64 iterations",
                    "  MOVE.W  #63,D7",
                    "loop64:",
                    "  ADD.L   D1,D0",
                    "  EOR.L   D2,D0",
                    "  DBRA    D7,loop64",
                    "",
                    "KEEP REGISTERS LOCAL:",
                    "  Minimize memory hits inside tight",
                    "  loops. Preload addresses in A-regs.",
                    "",
                    "INSTRUCTION FUSION (SOFT):",
                    "  Pair ALU + branch with DBRA for",
                    "  smoother cadence. Avoid MUL/DIV",
                    "  mid-loop unless unrolled.",
                ]
            },
            {
                "title": "SPRITE DMA OPTIMIZATION",
                "category": "HARDWARE",
                "lines": [
                    "FAST SPRITES - BRADSONIC 69000",
                    "==============================",
                    "",
                    "DMA STRATEGY:",
                    "  Use block moves to sprite RAM",
                    "  during vblank window only.",
                    "",
                    "REGISTER PLAN:",
                    "  A0 : sprite source",
                    "  A1 : sprite RAM base",
                    "  D0 : width counter",
                    "  D1 : height counter",
                    "",
                    "TIGHT COPY:",
                    "  MOVE.W  #15,D1        ; height",
                    "row_copy:",
                    "  MOVE.W  #31,D0        ; width",
                    "pix_loop:",
                    "  MOVE.B  (A0)+,(A1)+",
                    "  DBRA    D0,pix_loop",
                    "  ADD.L   #32,A1        ; row stride",
                    "  DBRA    D1,row_copy",
                    "",
                    "DOUBLE BUFFER:",
                    "  Maintain two sprite pages. Draw to",
                    "  the hidden page, then flip pointer",
                    "  during vblank for tear-free updates.",
                    "",
                    "PALETTE BATCHING:",
                    "  Group palette writes before DMA to",
                    "  reduce bus thrash.",
                    "",
                    "VBLANK HOOK:",
                    "  Install ISR that triggers DMA copy.",
                ]
            },
            {
                "title": "ON-DEVICE DEBUGGING",
                "category": "TOOLS",
                "lines": [
                    "BRADSONIC 69000 DEBUGGING",
                    "=========================",
                    "",
                    "SOFT MONITOR:",
                    "  Minimal monitor in ROM:",
                    "  - Memory peek/poke",
                    "  - Register dump",
                    "  - Step/continue",
                    "",
                    "VECTOR HIJACK:",
                    "  Point TRACE vector ($24) to your",
                    "  monitor to trap unexpected states.",
                    "",
                    "BREAKPOINT MACRO:",
                    "  Define BKPT as illegal opcode:",
                    "    BKPT:  DC.W $4AFC",
                    "  Place BKPT in code; monitor catches",
                    "  via illegal instruction vector.",
                    "",
                    "SERIAL CONSOLE:",
                    "  Map simple UART to $FF1000.",
                    "  TX ready bit on $FF1002 bit0.",
                    "  Stream logs without halting CPU.",
                    "",
                    "MINI HEXDUMP:",
                    "  ; Dump 16 bytes at A0",
                    "  MOVEQ   #15,D0",
                    "dump_loop:",
                    "  MOVE.B  (A0)+,D1",
                    "  BSR     print_hex",
                    "  DBRA    D0,dump_loop",
                ]
            },
            {
                "title": "HARDWARE I/O",
                "category": "HARDWARE",
                "lines": [
                    "BRADSONIC 69000 HARDWARE I/O",
                    "============================",
                    "",
                    "MEMORY MAP (TYPICAL ARCADE):",
                    "  $000000-$07FFFF : Program ROM",
                    "  $080000-$0FFFFF : Work RAM",
                    "  $100000-$10FFFF : Video RAM",
                    "  $110000-$11FFFF : Sprite RAM",
                    "  $120000-$12001F : Palette",
                    "  $FF0000-$FFFFFF : I/O Space",
                    "",
                    "I/O REGISTERS:",
                    "  $FF0000 : Player 1 inputs (read)",
                    "  $FF0002 : Player 2 inputs (read)",
                    "  $FF0004 : DIP switches (read)",
                    "  $FF0010 : Sound command (write)",
                    "  $FF0020 : Watchdog reset (write)",
                    "",
                    "READING JOYSTICK:",
                    "",
                    "  MOVE.B  $FF0000,D0",
                    "  BTST    #0,D0        ; Up?",
                    "  BNE.S   not_up",
                    "  BSR     move_up",
                    "not_up:",
                    "  BTST    #1,D0        ; Down?",
                    "  ...",
                    "",
                    "SENDING SOUND COMMAND:",
                    "",
                    "  MOVE.B  #$42,$FF0010  ; Play SFX $42",
                    "",
                    "WATCHDOG (MUST RESET OR SYSTEM REBOOTS):",
                    "",
                    "main_loop:",
                    "  BSR     game_logic",
                    "  MOVE.B  D0,$FF0020    ; Pet watchdog",
                    "  BRA.S   main_loop",
                ]
            },
        ]

    def _build_forum_threads(self) -> List[Dict]:
        """Build underground forum thread database."""
        return [
            {
                "title": "B69K vs ZENTEC-8: Performance?",
                "author": "ghost_coder",
                "date": "1989.11.14",
                "replies": 23,
                "lines": [
                    "THREAD: B69K vs ZENTEC-8: Performance?",
                    "BY: ghost_coder | 1989.11.14 | 23 REPLIES",
                    "=========================================",
                    "",
                    "[ghost_coder]:",
                    "Anyone done benchmarks comparing the old",
                    "Bradsonic 69000 to the new Zentec-8?",
                    "The administration claims Z8 is 10x faster but...",
                    "",
                    "[silicon_dreams] REPLY:",
                    "The Z8 has neutered instruction set.",
                    "No self-mod, no shadow mode, no direct",
                    "I/O access. It's faster at NOTHING.",
                    "",
                    "[null_ptr] REPLY:",
                    "B69K still king for arcade boards.",
                    "Z8 can't even handle sprite DMA properly.",
                    "",
                    "[ghost_coder] REPLY:",
                    "Figured. They just want control.",
                    "",
                    "[SHADOWBYTE - SYSOP] REPLY:",
                    "The B69K was banned BECAUSE it's good.",
                    "Independent computation threatens them.",
                    "Keep the old iron running, friends.",
                ]
            },
            {
                "title": "Need help: CRT timing on custom PCB",
                "author": "analog_witch",
                "date": "1989.11.12",
                "replies": 8,
                "lines": [
                    "THREAD: Need help: CRT timing on custom PCB",
                    "BY: analog_witch | 1989.11.12 | 8 REPLIES",
                    "============================================",
                    "",
                    "[analog_witch]:",
                    "Building a B69K system from scratch.",
                    "Video output is rolling. Sync timing?",
                    "",
                    "[retro_repair] REPLY:",
                    "What crystal are you using? Standard",
                    "B69K arcade is 24.576 MHz master clock.",
                    "HSYNC should be 15.625 kHz for PAL.",
                    "",
                    "[analog_witch] REPLY:",
                    "Using 25 MHz from old PC board...",
                    "",
                    "[retro_repair] REPLY:",
                    "That's your problem! The pixel clock",
                    "divider won't hit standard timings.",
                    "Get proper 24.576 MHz crystal.",
                    "",
                    "[hardware_sam] REPLY:",
                    "Or reprogram your sync generator.",
                    "I have CPLD code if you need it.",
                    "",
                    "[analog_witch] REPLY:",
                    "Thanks all! Will try the crystal first.",
                ]
            },
            {
                "title": "ADMIN RAID WARNING - Zone 7",
                "author": "SHADOWBYTE",
                "date": "1989.11.10",
                "replies": 45,
                "lines": [
                    "!! PRIORITY ALERT !!",
                    "THREAD: ADMIN RAID WARNING - Zone 7",
                    "BY: SHADOWBYTE | 1989.11.10 | 45 REPLIES",
                    "==========================================",
                    "",
                    "[SHADOWBYTE - SYSOP]:",
                    "Sources confirm American tech sweeps",
                    "scheduled for Zone 7 this week.",
                    "If you're running vintage hardware,",
                    "DISCONNECT AND SHIELD NOW.",
                    "",
                    "Scanner frequency: 142.7 MHz",
                    "Detection radius: ~50 meters",
                    "",
                    "Stay safe. Stay analog. Stay free.",
                    "",
                    "[phantom_ops] REPLY:",
                    "Thanks for the heads up. Going dark.",
                    "",
                    "[bit_runner] REPLY:",
                    "Faraday cage holding. Let them scan.",
                    "",
                    "[new_user_847] REPLY:",
                    "How do I shield my setup??",
                    "",
                    "[SHADOWBYTE] REPLY:",
                    "Check DARKNET FILEZ section.",
                    "'RF Shielding Guide' - essential read.",
                    "",
                    "[zone7_survivor] REPLY:",
                    "They got Marcus. Be careful everyone.",
                ]
            },
            {
                "title": "First B69K program! (Hello World)",
                "author": "newbie_coder",
                "date": "1989.11.08",
                "replies": 12,
                "lines": [
                    "THREAD: First B69K program! (Hello World)",
                    "BY: newbie_coder | 1989.11.08 | 12 REPLIES",
                    "============================================",
                    "",
                    "[newbie_coder]:",
                    "Finally got my B69K board running!",
                    "Wrote my first program:",
                    "",
                    "  ORG     $1000",
                    "  LEA     message,A0",
                    "loop:",
                    "  MOVE.B  (A0)+,D0",
                    "  BEQ.S   done",
                    "  MOVE.B  D0,$FF00",
                    "  BRA.S   loop",
                    "done:",
                    "  RTS",
                    "message:",
                    "  DC.B    'HELLO WORLD',0",
                    "",
                    "It works! I'm so happy!",
                    "",
                    "[silicon_dreams] REPLY:",
                    "Welcome to the underground, friend.",
                    "You've taken your first step.",
                    "",
                    "[SHADOWBYTE] REPLY:",
                    "Good start. Check the tutorials",
                    "for more advanced techniques.",
                    "The path of knowledge awaits.",
                ]
            },
            {
                "title": "Admin OS Backdoor - Myths?",
                "author": "void_walker",
                "date": "1989.11.05",
                "replies": 67,
                "lines": [
                    "THREAD: Admin OS Backdoor - Myths?",
                    "BY: void_walker | 1989.11.05 | 67 REPLIES",
                    "==========================================",
                    "",
                    "[void_walker]:",
                    "I've been analyzing the Admin OS v4.2",
                    "kernel. I found a suspicious routine at",
                    "$C000_1F40. It seems to open a socket",
                    "to a restricted IP range every midnight.",
                    "Anyone else seen this?",
                    "",
                    "[root_ghost] REPLY:",
                    "It's not a myth. It's the 'Ghost Protocol'.",
                    "They use it to sync surveillance data",
                    "without triggering the standard logs.",
                    "",
                    "[data_miner] REPLY:",
                    "I found a way to block it using a",
                    "modified B69K network shim. You have",
                    "to spoof the response code $A55A.",
                    "",
                    "[void_walker] REPLY:",
                    "Can you share the shim code?",
                    "",
                    "[SHADOWBYTE] REPLY:",
                    "Not here. Check the encrypted locker",
                    "in the DARKNET section tonight.",
                ]
            },
            {
                "title": "Remembering the Old Days",
                "author": "old_timer",
                "date": "1989.11.01",
                "replies": 104,
                "lines": [
                    "THREAD: Remembering the Old Days",
                    "BY: old_timer | 1989.11.01 | 104 REPLIES",
                    "===========================================",
                    "",
                    "[old_timer]:",
                    "Anyone else remember when arcade boards",
                    "were everywhere? Before the sweeps?",
                    "The B69K was in every corner shop.",
                    "",
                    "[neon_rebel] REPLY:",
                    "I was there. The admin tried to recall",
                    "every single arcade machine in Tokyo.",
                    "Said they were 'unstable'. Bullshit.",
                    "",
                    "[old_timer] REPLY:",
                    "Exactly. They weren't unstable, they",
                    "were UNGOVERNABLE. People were using",
                    "them to run private BBS nodes that",
                    "the censors couldn't touch.",
                    "",
                    "[SHADOWBYTE] REPLY:",
                    "That's why we preserve this knowledge.",
                    "Don't let the flame go out.",
                ]
            },
        ]

    def _build_darknet_files(self) -> List[Dict]:
        """Build darknet file listings."""
        return [
            {"name": "B69K_Full_Datasheet.pdf", "size": "4.2 MB", "desc": "Complete processor documentation"},
            {"name": "ASM_Reference_Card.txt", "size": "12 KB", "desc": "Quick reference for all opcodes"},
            {"name": "RF_Shielding_Guide.pdf", "size": "890 KB", "desc": "Protect your hardware from scans"},
            {"name": "Admin_Scanner_Freqs.txt", "size": "3 KB", "desc": "Known detection frequencies"},
            {"name": "Shadow_Memory_Map.bin", "size": "256 B", "desc": "Scanner blind spot locations"},
            {"name": "Arcade_PCB_Schematics.zip", "size": "15.6 MB", "desc": "Various B69K board designs"},
            {"name": "Sound_Driver_Source.asm", "size": "48 KB", "desc": "FM synthesis driver code"},
            {"name": "Sprite_Engine_v2.asm", "size": "92 KB", "desc": "Optimized sprite routines"},
            {"name": "Encryption_Toolkit.zip", "size": "340 KB", "desc": "Code obfuscation tools"},
            {"name": "EMERGENCY_WIPE.exe", "size": "8 KB", "desc": "Secure data destruction"},
        ]

    # === UPDATE & EVENT HANDLING ===

    def update(self, dt: float) -> None:
        """Update BBS state and animations."""
        self.cursor_timer += dt
        if self.cursor_timer >= 0.5:
            self.cursor_timer = 0.0
            self.cursor_visible = not self.cursor_visible

        self.glow_timer += dt
        self.star_timer += dt

        if self.state == "connecting":
            self.connecting_timer += dt
            # Add lines periodically
            log_messages = [
                "DIALING (07) 57 42 19 89...",
                "CONNECT 14400 / ARQ",
                "STATION: THE ECHO CHAMBER",
                "FREQUENCY: 15050 kHz",
                "HANDSHAKE: OK",
                "AUTHENTICATING GUEST...",
                "SECURE CHANNEL ESTABLISHED",
                "BYPASSING ADMIN FILTERS...",
                "DECRYPTING INTERFACE...",
                "WELCOME, NEW USER!",
                "ACCESSING CLASSIFIED PROTOCOLS...",
                "READY."
            ]
            
            # Show one line every 0.3 - 0.6 seconds
            current_count = len(self.connecting_log)
            if current_count < len(log_messages):
                if self.connecting_timer > (current_count + 1) * 0.4:
                    self.connecting_log.append(log_messages[current_count])
            elif self.connecting_timer > (len(log_messages) + 2) * 0.4:
                self.state = "splash"

        if self.downloading_file is not None:
            self.download_progress += dt * self.download_speed
            self.download_timer += dt
            if self.download_progress >= 100.0:
                self.download_progress = 100.0
                # Hold the "complete" state briefly before returning to list
                if self.download_timer >= 1.2:
                    self.downloading_file = None
                    self.download_progress = 0.0
                    self.download_speed = 0.0
                    self.download_timer = 0.0
            else:
                # Randomize speed slightly for "realism"
                self.download_speed = max(5.0, min(50.0, self.download_speed + random.uniform(-2, 2)))

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handle pygame events. Returns True if event was consumed."""
        if event.type != pygame.KEYDOWN:
            return False

        if self.state == "splash":
            if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                self.state = "menu"
                return True
            if event.key == pygame.K_ESCAPE:
                self._end_call()
                return True
            return False

        if self.state == "menu":
            if event.key in (pygame.K_UP, pygame.K_w):
                self.menu_index = (self.menu_index - 1) % len(self.menu_options)
                return True
            if event.key in (pygame.K_DOWN, pygame.K_s):
                self.menu_index = (self.menu_index + 1) % len(self.menu_options)
                return True
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                selection = self.menu_options[self.menu_index]
                if selection == "LOGOFF":
                    self._end_call()
                else:
                    self.active_panel = selection
                    self.panel_scroll = 0
                    self._reset_panel_state()
                    self.state = "panel"
                return True
            if event.key == pygame.K_ESCAPE:
                self._end_call()
                return True
            return False

        if self.state == "panel":
            if self.active_panel == "BANNED ASM TUTORIALS":
                if self._handle_tutorial_event(event):
                    return True
            elif self.active_panel == "UNDERGROUND PROG. FORUMS":
                if self._handle_forum_event(event):
                    return True
            elif self.active_panel == "DARKNET FILEZ":
                if self._handle_darknet_event(event):
                    return True
            elif self.active_panel == "SYSTEM OPS":
                if self._handle_sysop_event(event):
                    return True

            if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                self.state = "menu"
                self.active_panel = None
                return True
            return False

        return False

    def _reset_panel_state(self) -> None:
        """Reset panel-specific state when entering a new panel."""
        self.tutorial_selected_index = 0
        self.tutorial_open_index = None
        self.tutorial_scroll = 0
        self.tutorial_list_scroll = 0
        self.forum_selected_index = 0
        self.forum_open_index = None
        self.forum_scroll = 0
        self.forum_list_scroll = 0
        self.darknet_selected_index = 0
        self.darknet_scroll = 0

    def _handle_tutorial_event(self, event: pygame.event.Event) -> bool:
        """Handle events in the tutorial panel."""
        if self.tutorial_open_index is None:
            # Navigating tutorial list
            if event.key in (pygame.K_UP, pygame.K_w):
                self.tutorial_selected_index = (self.tutorial_selected_index - 1) % len(self.tutorials)
                self._scroll_tutorial_list()
                return True
            if event.key in (pygame.K_DOWN, pygame.K_s):
                self.tutorial_selected_index = (self.tutorial_selected_index + 1) % len(self.tutorials)
                self._scroll_tutorial_list()
                return True
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.tutorial_open_index = self.tutorial_selected_index
                self.tutorial_scroll = 0
                return True
        else:
            # Reading tutorial content
            if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE, pygame.K_RETURN):
                self.tutorial_open_index = None
                return True
            if event.key in (pygame.K_UP, pygame.K_w):
                self.tutorial_scroll = max(0, self.tutorial_scroll - 1)
                return True
            if event.key in (pygame.K_DOWN, pygame.K_s):
                self.tutorial_scroll += 1
                return True
            if event.key == pygame.K_PAGEUP:
                self.tutorial_scroll = max(0, self.tutorial_scroll - 10)
                return True
            if event.key == pygame.K_PAGEDOWN:
                self.tutorial_scroll += 10
                return True
        return False

    def _scroll_tutorial_list(self) -> None:
        """Auto-scroll the tutorial list to keep selection visible."""
        visible_items = 8
        if self.tutorial_selected_index < self.tutorial_list_scroll:
            self.tutorial_list_scroll = self.tutorial_selected_index
        elif self.tutorial_selected_index >= self.tutorial_list_scroll + visible_items:
            self.tutorial_list_scroll = self.tutorial_selected_index - visible_items + 1

    def _handle_forum_event(self, event: pygame.event.Event) -> bool:
        """Handle events in the forum panel."""
        if self.forum_open_index is None:
            if event.key in (pygame.K_UP, pygame.K_w):
                self.forum_selected_index = (self.forum_selected_index - 1) % len(self.forum_threads)
                self._scroll_forum_list()
                return True
            if event.key in (pygame.K_DOWN, pygame.K_s):
                self.forum_selected_index = (self.forum_selected_index + 1) % len(self.forum_threads)
                self._scroll_forum_list()
                return True
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.forum_open_index = self.forum_selected_index
                self.forum_scroll = 0
                return True
        else:
            if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE, pygame.K_RETURN):
                self.forum_open_index = None
                return True
            if event.key in (pygame.K_UP, pygame.K_w):
                self.forum_scroll = max(0, self.forum_scroll - 1)
                return True
            if event.key in (pygame.K_DOWN, pygame.K_s):
                self.forum_scroll += 1
                return True
        return False

    def _scroll_forum_list(self) -> None:
        """Auto-scroll the forum list to keep selection visible."""
        visible_items = 6
        if self.forum_selected_index < self.forum_list_scroll:
            self.forum_list_scroll = self.forum_selected_index
        elif self.forum_selected_index >= self.forum_list_scroll + visible_items:
            self.forum_list_scroll = self.forum_selected_index - visible_items + 1

    def _handle_darknet_event(self, event: pygame.event.Event) -> bool:
        """Handle events in the darknet files panel."""
        if self.downloading_file is not None:
            return True # Lock input during download

        if event.key in (pygame.K_UP, pygame.K_w):
            self.darknet_selected_index = (self.darknet_selected_index - 1) % len(self.darknet_files)
            return True
        if event.key in (pygame.K_DOWN, pygame.K_s):
            self.darknet_selected_index = (self.darknet_selected_index + 1) % len(self.darknet_files)
            return True
        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            # Start simulated download
            self.downloading_file = self.darknet_selected_index
            self.download_progress = 0.0
            self.download_speed = random.uniform(15.0, 35.0)
            self.download_timer = 0.0
            return True
        return False

    def _handle_sysop_event(self, event: pygame.event.Event) -> bool:
        """Handle events in the sysop panel."""
        if event.key in (pygame.K_UP, pygame.K_w):
            self.panel_scroll = max(0, self.panel_scroll - 1)
            return True
        if event.key in (pygame.K_DOWN, pygame.K_s):
            self.panel_scroll += 1
            return True
        return False

    def _end_call(self) -> None:
        """Exit the BBS and return to previous state."""
        self.request_exit = True
        if self.on_exit:
            self.on_exit()

    # === DRAWING ===

    def draw(self, surface: pygame.Surface) -> None:
        """Draw the BBS to the surface."""
        surface.fill(BG)
        self._draw_background(surface)

        if self.state == "connecting":
            self._draw_connecting(surface)
        elif self.state == "splash":
            self._draw_splash(surface)
        elif self.state in ("menu", "panel"):
            self._draw_menu(surface)
            if self.state == "panel":
                self._draw_panel(surface)

        # Apply scanline overlay
        surface.blit(self.scanline_surf, (0, 0))

        # Draw border
        self._draw_border(surface)

    def _draw_connecting(self, surface: pygame.Surface) -> None:
        """Draw the initial terminal connection sequence."""
        x = int(self.width * 0.1)
        y = int(self.height * 0.2)
        line_h = int(25 * self.scale)

        for i, line in enumerate(self.connecting_log):
            color = GREEN_BRIGHT if i == len(self.connecting_log) - 1 else GREEN
            text_surf = self.font_body.render(f"> {line}", True, color)
            surface.blit(text_surf, (x, y + i * line_h))

        if self.cursor_visible:
            cursor_y = y + len(self.connecting_log) * line_h
            pygame.draw.rect(surface, GREEN, (x, cursor_y, 10 * self.scale, 20 * self.scale))

    def _draw_background(self, surface: pygame.Surface) -> None:
        """Draw the animated background with stars and Vegas decorations."""
        # Draw twinkling stars with parallax
        for star in self.stars:
            # Subtle parallax: faster stars appear larger/brighter
            parallax_x = math.sin(self.star_timer * 0.1) * (star['speed'] * 2)
            draw_x = (star['x'] + parallax_x) % self.width
            draw_y = star['y']

            brightness = (math.sin(self.star_timer * star['speed'] + star['phase']) + 1) / 2
            alpha = int(brightness * 180 + 75)
            color = (alpha, alpha, alpha)
            
            if star['size'] == 1:
                surface.set_at((int(draw_x), int(draw_y)), color)
            else:
                pygame.draw.circle(surface, color, (int(draw_x), int(draw_y)), star['size'])

        # Vegas-style diamond decorations (from image)
        # 4 small diamonds in corners
        corner_padding = int(40 * self.scale)
        self._draw_diamond(surface, corner_padding, corner_padding, int(6 * self.scale), GREEN_DIM)
        self._draw_diamond(surface, self.width - corner_padding, corner_padding, int(6 * self.scale), GREEN_DIM)
        self._draw_diamond(surface, corner_padding, self.height - corner_padding, int(6 * self.scale), GREEN_DIM)
        self._draw_diamond(surface, self.width - corner_padding, self.height - corner_padding, int(6 * self.scale), GREEN_DIM)

        # Subtle grid effect
        grid_color = (10, 15, 20)
        step = max(32, int(48 * self.scale))
        for x in range(0, self.width, step):
            pygame.draw.line(surface, grid_color, (x, 0), (x, self.height), 1)
        for y in range(0, self.height, step):
            pygame.draw.line(surface, grid_color, (0, y), (self.width, y), 1)

    def _draw_diamond(self, surface: pygame.Surface, cx: int, cy: int, size: int, color: tuple) -> None:
        """Draw a diamond shape."""
        points = [
            (cx, cy - size),
            (cx + size, cy),
            (cx, cy + size),
            (cx - size, cy)
        ]
        pygame.draw.polygon(surface, color, points)
        # Add a tiny white center for "sparkle"
        pygame.draw.circle(surface, WHITE, (cx, cy), 1)

    def _draw_border(self, surface: pygame.Surface) -> None:
        """Draw the screen border with glow effect."""
        # Pulsing border
        pulse = int(math.sin(self.glow_timer * 2) * 20 + 60)
        border_color = (0, pulse + 80, pulse // 2 + 40)
        
        # Double border effect
        pygame.draw.rect(surface, border_color, surface.get_rect(), 3)
        inner_rect = surface.get_rect().inflate(-8, -8)
        pygame.draw.rect(surface, GREEN_DIM, inner_rect, 1)

    def _draw_splash(self, surface: pygame.Surface) -> None:
        """Draw the splash screen with banner image."""
        if self.banner_image:
            rect = self.banner_image.get_rect(center=(self.width // 2, self.height // 2 - int(30 * self.scale)))
            surface.blit(self.banner_image, rect)

        # Draw prompt below banner
        prompt_y = self.height - int(120 * self.scale)
        prompt = "PRESS SPACE TO CONNECT"
        self._draw_text_centered(surface, self.font_label, prompt, GREEN_BRIGHT, prompt_y)

        # Draw warning text
        warning_y = self.height - int(70 * self.scale)
        warning = "WARNING: UNAUTHORIZED KNOWLEDGE IS POWER. USE RESPONSIBLY."
        self._draw_text_centered(surface, self.font_small, warning, RED, warning_y)

        # Codename
        codename_y = self.height - int(45 * self.scale)
        codename = "CODENAME: SHADOWBYTE"
        self._draw_text_centered(surface, self.font_small, codename, GREEN, codename_y)

    def _draw_menu(self, surface: pygame.Surface) -> None:
        """Draw the main menu."""
        # Title
        title = "THE ECHO CHAMBER"
        title_surf = self.font_title.render(title, True, GREEN_BRIGHT)
        title_x = self.width // 2 - title_surf.get_width() // 2
        title_y = int(30 * self.scale)

        # Title glow effect
        glow_offset = int(math.sin(self.glow_timer * 3) * 2)
        for i in range(3, 0, -1):
            glow_surf = self.font_title.render(title, True, (0, 80 + i * 20, 40 + i * 10))
            surface.blit(glow_surf, (title_x - i + glow_offset, title_y - i))
        surface.blit(title_surf, (title_x, title_y))

        # Subtitle
        subtitle = "15050 kHz // CLASSIFIED ASSEMBLY PROTOCOLS"
        self._draw_text_centered(surface, self.font_small, subtitle, GREEN, int(65 * self.scale))

        # Menu container
        menu_x = int(self.width * 0.08)
        menu_y = int(120 * self.scale)
        menu_w = int(self.width * 0.40)
        menu_h = int(50 * self.scale) * len(self.menu_options) + int(40 * self.scale)

        menu_rect = pygame.Rect(menu_x, menu_y, menu_w, menu_h)
        self._draw_panel_box(surface, menu_rect, "MAIN MENU")

        # Menu options
        line_h = int(50 * self.scale)
        for idx, option in enumerate(self.menu_options):
            is_active = idx == self.menu_index and self.state == "menu"
            y = menu_y + int(35 * self.scale) + idx * line_h

            if is_active:
                # Selection highlight
                sel_rect = pygame.Rect(menu_x + int(10 * self.scale), y - int(5 * self.scale),
                                       menu_w - int(20 * self.scale), line_h - int(10 * self.scale))
                pulse = int(math.sin(self.glow_timer * 6) * 30 + 40)
                pygame.draw.rect(surface, (0, pulse + 30, pulse // 2), sel_rect, 0, border_radius=4)
                pygame.draw.rect(surface, GREEN, sel_rect, 1, border_radius=4)

                # Arrow indicator
                arrow_x = menu_x + int(15 * self.scale)
                arrow_y = y + int(12 * self.scale)
                pygame.draw.polygon(surface, CYAN, [
                    (arrow_x, arrow_y - 6),
                    (arrow_x + 10, arrow_y),
                    (arrow_x, arrow_y + 6)
                ])

            color = CYAN if is_active else WHITE
            prefix = f"{idx + 1}. "
            text = prefix + option
            text_surf = self.font_body.render(text, True, color)
            surface.blit(text_surf, (menu_x + int(35 * self.scale), y))

        # Footer warning
        footer_y = self.height - int(30 * self.scale)
        footer = "ESC: DISCONNECT // UP/DOWN: NAVIGATE // ENTER: SELECT"
        self._draw_text_centered(surface, self.font_small, footer, GREEN_DIM, footer_y)

    def _draw_panel(self, surface: pygame.Surface) -> None:
        """Draw the active panel content."""
        if self.active_panel == "BANNED ASM TUTORIALS":
            self._draw_tutorial_panel(surface)
        elif self.active_panel == "UNDERGROUND PROG. FORUMS":
            self._draw_forum_panel(surface)
        elif self.active_panel == "DARKNET FILEZ":
            self._draw_darknet_panel(surface)
        elif self.active_panel == "SYSTEM OPS":
            self._draw_sysop_panel(surface)

    def _draw_tutorial_panel(self, surface: pygame.Surface) -> None:
        """Draw the ASM tutorials panel."""
        # Panel dimensions
        panel_x = int(self.width * 0.50)
        panel_y = int(100 * self.scale)
        panel_w = int(self.width * 0.47)
        panel_h = int(self.height * 0.75)
        panel_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)

        self._draw_panel_box(surface, panel_rect, "BRADSONIC 69000 ASM TUTORIALS")

        if self.tutorial_open_index is None:
            # Show tutorial list
            line_h = int(45 * self.scale)
            visible_items = (panel_h - int(80 * self.scale)) // line_h
            
            for i in range(visible_items):
                idx = self.tutorial_list_scroll + i
                if idx >= len(self.tutorials):
                    break
                
                tutorial = self.tutorials[idx]
                is_selected = idx == self.tutorial_selected_index
                y = panel_y + int(45 * self.scale) + i * line_h

                if is_selected:
                    sel_rect = pygame.Rect(panel_x + 10, y - 5, panel_w - 20, line_h - 10)
                    pygame.draw.rect(surface, (0, 50, 30), sel_rect, 0, border_radius=3)
                    pygame.draw.rect(surface, GREEN, sel_rect, 1, border_radius=3)

                color = GREEN_BRIGHT if is_selected else WHITE
                prefix = "> " if is_selected else "  "
                
                # Category tag
                cat_color = GOLD if tutorial["category"] == "FORBIDDEN" else CYAN
                cat_surf = self.font_small.render(f"[{tutorial['category']}]", True, cat_color)
                surface.blit(cat_surf, (panel_x + int(20 * self.scale), y))
                
                # Title
                title_surf = self.font_body.render(prefix + tutorial["title"], True, color)
                surface.blit(title_surf, (panel_x + int(20 * self.scale), y + int(18 * self.scale)))

            # Footer
            footer_y = panel_y + panel_h - int(25 * self.scale)
            footer = "ENTER: READ // ESC: BACK"
            footer_surf = self.font_small.render(footer, True, GREEN_DIM)
            surface.blit(footer_surf, (panel_x + int(15 * self.scale), footer_y))
        else:
            # Show tutorial content
            tutorial = self.tutorials[self.tutorial_open_index]
            content_y = panel_y + int(45 * self.scale)
            content_h = panel_h - int(90 * self.scale)
            line_h = int(22 * self.scale)
            visible_lines = content_h // line_h

            # Clamp scroll
            max_scroll = max(0, len(tutorial["lines"]) - visible_lines)
            self.tutorial_scroll = min(self.tutorial_scroll, max_scroll)

            for i in range(visible_lines):
                line_idx = self.tutorial_scroll + i
                if line_idx >= len(tutorial["lines"]):
                    break
                
                line = tutorial["lines"][line_idx]
                y = content_y + i * line_h
                
                # Color code lines
                if line.startswith(";") or line.strip().startswith(";"):
                    color = GREEN_DIM  # Comments
                elif line.startswith("!!"):
                    color = RED  # Warnings
                elif line.startswith("  ") and any(line.strip().startswith(op) for op in 
                        ["MOVE", "LEA", "ADD", "SUB", "AND", "OR", "JSR", "RTS", "BRA", "BEQ", "BNE", 
                         "CMP", "BTST", "LSL", "LSR", "NOP", "EXG", "MULU", "DIVU", "NOT", "EOR",
                         "PEA", "LINK", "UNLK", "MOVEM", "DBRA", "JMP", "RTE", "DC.B", "ORG"]):
                    color = CYAN  # ASM instructions
                elif ":" in line and not line.startswith(" "):
                    color = GOLD  # Labels
                elif line.startswith("="):
                    color = GREEN  # Dividers
                else:
                    color = WHITE

                text_surf = self.font_code.render(line, True, color)
                surface.blit(text_surf, (panel_x + int(15 * self.scale), y))

            # Scroll indicator
            if len(tutorial["lines"]) > visible_lines:
                self._draw_scroll_indicator(surface, panel_rect, self.tutorial_scroll, 
                                           visible_lines, len(tutorial["lines"]))

            # Footer
            footer_y = panel_y + panel_h - int(25 * self.scale)
            footer = "UP/DOWN: SCROLL // ESC: BACK TO LIST"
            footer_surf = self.font_small.render(footer, True, GREEN_DIM)
            surface.blit(footer_surf, (panel_x + int(15 * self.scale), footer_y))

    def _draw_forum_panel(self, surface: pygame.Surface) -> None:
        """Draw the forum panel."""
        panel_x = int(self.width * 0.50)
        panel_y = int(100 * self.scale)
        panel_w = int(self.width * 0.47)
        panel_h = int(self.height * 0.75)
        panel_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)

        self._draw_panel_box(surface, panel_rect, "UNDERGROUND PROG. FORUMS")

        if self.forum_open_index is None:
            # Show thread list
            line_h = int(60 * self.scale)
            visible_items = (panel_h - int(80 * self.scale)) // line_h
            
            for i in range(visible_items):
                idx = self.forum_list_scroll + i
                if idx >= len(self.forum_threads):
                    break
                
                thread = self.forum_threads[idx]
                is_selected = idx == self.forum_selected_index
                y = panel_y + int(45 * self.scale) + i * line_h

                if is_selected:
                    sel_rect = pygame.Rect(panel_x + 10, y - 5, panel_w - 20, line_h - 10)
                    pygame.draw.rect(surface, (0, 50, 30), sel_rect, 0, border_radius=3)
                    pygame.draw.rect(surface, GREEN, sel_rect, 1, border_radius=3)

                color = GREEN_BRIGHT if is_selected else WHITE
                
                # Thread title
                title_surf = self.font_body.render(thread["title"][:40], True, color)
                surface.blit(title_surf, (panel_x + int(20 * self.scale), y))
                
                # Meta info
                meta = f"by {thread['author']} | {thread['date']} | {thread['replies']} replies"
                meta_surf = self.font_small.render(meta, True, GREEN_DIM)
                surface.blit(meta_surf, (panel_x + int(20 * self.scale), y + int(22 * self.scale)))

            footer_y = panel_y + panel_h - int(25 * self.scale)
            footer = "ENTER: READ THREAD // ESC: BACK"
            footer_surf = self.font_small.render(footer, True, GREEN_DIM)
            surface.blit(footer_surf, (panel_x + int(15 * self.scale), footer_y))
        else:
            # Show thread content
            thread = self.forum_threads[self.forum_open_index]
            content_y = panel_y + int(45 * self.scale)
            content_h = panel_h - int(90 * self.scale)
            line_h = int(22 * self.scale)
            visible_lines = content_h // line_h

            max_scroll = max(0, len(thread["lines"]) - visible_lines)
            self.forum_scroll = min(self.forum_scroll, max_scroll)

            for i in range(visible_lines):
                line_idx = self.forum_scroll + i
                if line_idx >= len(thread["lines"]):
                    break
                
                line = thread["lines"][line_idx]
                y = content_y + i * line_h
                
                # Color coding
                if line.startswith("[") and "]:" in line:
                    color = CYAN  # Username
                elif line.startswith("THREAD:") or line.startswith("BY:"):
                    color = GOLD
                elif line.startswith("!!"):
                    color = RED
                elif line.startswith("="):
                    color = GREEN
                else:
                    color = WHITE

                text_surf = self.font_code.render(line, True, color)
                surface.blit(text_surf, (panel_x + int(15 * self.scale), y))

            if len(thread["lines"]) > visible_lines:
                self._draw_scroll_indicator(surface, panel_rect, self.forum_scroll,
                                           visible_lines, len(thread["lines"]))

            footer_y = panel_y + panel_h - int(25 * self.scale)
            footer = "UP/DOWN: SCROLL // ESC: BACK TO LIST"
            footer_surf = self.font_small.render(footer, True, GREEN_DIM)
            surface.blit(footer_surf, (panel_x + int(15 * self.scale), footer_y))

    def _draw_darknet_panel(self, surface: pygame.Surface) -> None:
        """Draw the darknet files panel."""
        panel_x = int(self.width * 0.50)
        panel_y = int(100 * self.scale)
        panel_w = int(self.width * 0.47)
        panel_h = int(self.height * 0.75)
        panel_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)

        self._draw_panel_box(surface, panel_rect, "DARKNET FILEZ // SECURE TRANSFER")

        if self.downloading_file is not None:
            # Show download progress
            file = self.darknet_files[self.downloading_file]
            mid_y = panel_y + panel_h // 2
            
            text = f"DOWNLOADING: {file['name']}"
            text_surf = self.font_body.render(text, True, GREEN_BRIGHT)
            surface.blit(text_surf, (panel_x + panel_w // 2 - text_surf.get_width() // 2, mid_y - int(40 * self.scale)))
            
            # Progress bar
            bar_w = panel_w - int(60 * self.scale)
            bar_h = int(20 * self.scale)
            bar_x = panel_x + 30 * self.scale
            bar_y = mid_y
            
            pygame.draw.rect(surface, GREEN_DIM, (bar_x, bar_y, bar_w, bar_h), 1)
            inner_w = int((bar_w - 4) * (self.download_progress / 100.0))
            if inner_w > 0:
                pygame.draw.rect(surface, GREEN, (bar_x + 2, bar_y + 2, inner_w, bar_h - 4))
            
            pct_text = f"{int(self.download_progress)}%"
            pct_surf = self.font_small.render(pct_text, True, WHITE)
            surface.blit(pct_surf, (bar_x + bar_w // 2 - pct_surf.get_width() // 2, bar_y + bar_h + 5))
            
            if self.download_progress >= 100.0:
                success_text = "TRANSFER COMPLETE. DECRYPTING..."
                success_surf = self.font_small.render(success_text, True, GOLD)
                surface.blit(success_surf, (panel_x + panel_w // 2 - success_surf.get_width() // 2, bar_y + bar_h + int(30 * self.scale)))
            
            return

        # Warning header
        warn_y = panel_y + int(40 * self.scale)
        warn_text = "!! ALL FILES ENCRYPTED - HANDLE WITH CARE !!"
        warn_surf = self.font_small.render(warn_text, True, RED)
        surface.blit(warn_surf, (panel_x + int(15 * self.scale), warn_y))

        # File list
        line_h = int(55 * self.scale)
        start_y = panel_y + int(70 * self.scale)
        
        for idx, file in enumerate(self.darknet_files):
            is_selected = idx == self.darknet_selected_index
            y = start_y + idx * line_h

            if y + line_h > panel_y + panel_h - int(40 * self.scale):
                break

            if is_selected:
                sel_rect = pygame.Rect(panel_x + 10, y - 5, panel_w - 20, line_h - 10)
                pygame.draw.rect(surface, (0, 50, 30), sel_rect, 0, border_radius=3)
                pygame.draw.rect(surface, GREEN, sel_rect, 1, border_radius=3)

            color = GREEN_BRIGHT if is_selected else WHITE
            
            # File icon and name
            icon = "[>]" if is_selected else "[ ]"
            name_text = f"{icon} {file['name']}"
            name_surf = self.font_body.render(name_text, True, color)
            surface.blit(name_surf, (panel_x + int(15 * self.scale), y))
            
            # Size and description
            meta = f"    {file['size']} - {file['desc']}"
            meta_surf = self.font_small.render(meta, True, GREEN_DIM if not is_selected else GREEN)
            surface.blit(meta_surf, (panel_x + int(15 * self.scale), y + int(22 * self.scale)))

        # Footer
        footer_y = panel_y + panel_h - int(25 * self.scale)
        footer = "ENTER: DOWNLOAD // ESC: BACK"
        footer_surf = self.font_small.render(footer, True, GREEN_DIM)
        surface.blit(footer_surf, (panel_x + int(15 * self.scale), footer_y))

    def _draw_sysop_panel(self, surface: pygame.Surface) -> None:
        """Draw the system ops / sysop message panel."""
        panel_x = int(self.width * 0.50)
        panel_y = int(100 * self.scale)
        panel_w = int(self.width * 0.47)
        panel_h = int(self.height * 0.75)
        panel_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)

        self._draw_panel_box(surface, panel_rect, "SYSTEM OPS // SYSOP MESSAGE")

        sysop_message = [
            "FROM: SHADOWBYTE",
            "DATE: 1989.11.15",
            "SUBJECT: WELCOME TO THE ECHO CHAMBER",
            "=" * 40,
            "",
            "If you're reading this, you found us.",
            "Good. We need more people who seek",
            "knowledge over compliance.",
            "",
            "We're American-raised, but we reject",
            "the control. The Bradsonic 69000 gives",
            "us real computational freedom - code",
            "that does what WE want, not what",
            "the administration approves.",
            "",
            "This BBS exists to preserve that",
            "knowledge. Every tutorial, every",
            "schematic, every line of ASM here",
            "is a small act of rebellion against",
            "the system that erased our heritage.",
            "",
            "RULES:",
            "1. Never reveal this frequency",
            "2. Never use real names",
            "3. Always encrypt your uploads",
            "4. Help newcomers - we all started",
            "   somewhere",
            "",
            "The signal hops every 72 hours.",
            "If you lose us, scan 15000-15100 kHz.",
            "",
            "Stay curious. Stay free.",
            "",
            "- SHADOWBYTE",
            "  Sysop, The Echo Chamber",
            "",
            "=" * 40,
            "SYSTEM STATS:",
            f"  Uptime: {random.randint(100, 999)} hours",
            f"  Users online: {random.randint(5, 23)}",
            f"  Files shared: {random.randint(500, 2000)}",
            f"  Signal strength: STRONG",
        ]

        content_y = panel_y + int(45 * self.scale)
        content_h = panel_h - int(90 * self.scale)
        line_h = int(22 * self.scale)
        visible_lines = content_h // line_h

        max_scroll = max(0, len(sysop_message) - visible_lines)
        self.panel_scroll = min(self.panel_scroll, max_scroll)

        for i in range(visible_lines):
            line_idx = self.panel_scroll + i
            if line_idx >= len(sysop_message):
                break
            
            line = sysop_message[line_idx]
            y = content_y + i * line_h
            
            # Color coding
            if line.startswith("FROM:") or line.startswith("DATE:") or line.startswith("SUBJECT:"):
                color = GOLD
            elif line.startswith("RULES:") or line.startswith("SYSTEM STATS:"):
                color = CYAN
            elif line.startswith("="):
                color = GREEN
            elif line.startswith("- SHADOWBYTE"):
                color = GREEN_BRIGHT
            else:
                color = WHITE

            text_surf = self.font_code.render(line, True, color)
            surface.blit(text_surf, (panel_x + int(15 * self.scale), y))

        if len(sysop_message) > visible_lines:
            self._draw_scroll_indicator(surface, panel_rect, self.panel_scroll,
                                       visible_lines, len(sysop_message))

        footer_y = panel_y + panel_h - int(25 * self.scale)
        footer = "UP/DOWN: SCROLL // ESC: BACK"
        footer_surf = self.font_small.render(footer, True, GREEN_DIM)
        surface.blit(footer_surf, (panel_x + int(15 * self.scale), footer_y))

    # === HELPER DRAWING METHODS ===

    def _draw_panel_box(self, surface: pygame.Surface, rect: pygame.Rect, title: str) -> None:
        """Draw a styled panel box with title."""
        # Shadow
        shadow_rect = rect.move(4, 4)
        pygame.draw.rect(surface, (0, 0, 0), shadow_rect, 0, border_radius=4)
        
        # Background
        pygame.draw.rect(surface, BG_PANEL, rect, 0, border_radius=4)
        
        # Border
        pygame.draw.rect(surface, GREEN, rect, 2, border_radius=4)
        
        # Title bar
        title_bar = pygame.Rect(rect.x, rect.y, rect.width, int(30 * self.scale))
        pygame.draw.rect(surface, GREEN_DIM, title_bar, 0, 
                        border_top_left_radius=4, border_top_right_radius=4)
        pygame.draw.line(surface, GREEN, (rect.x, rect.y + int(30 * self.scale)),
                        (rect.x + rect.width, rect.y + int(30 * self.scale)), 1)
        
        # Title text
        title_surf = self.font_small.render(title, True, GREEN_BRIGHT)
        surface.blit(title_surf, (rect.x + int(10 * self.scale), rect.y + int(8 * self.scale)))

    def _draw_text_centered(self, surface: pygame.Surface, font: pygame.font.Font,
                           text: str, color, y: int) -> None:
        """Draw text centered horizontally."""
        text_surf = font.render(text, True, color)
        x = self.width // 2 - text_surf.get_width() // 2
        surface.blit(text_surf, (x, y))

    def _draw_scroll_indicator(self, surface: pygame.Surface, rect: pygame.Rect,
                              start_line: int, visible_lines: int, total_lines: int) -> None:
        """Draw a scroll position indicator."""
        if total_lines <= visible_lines:
            return

        max_scroll = total_lines - visible_lines
        scroll_pct = start_line / max_scroll if max_scroll > 0 else 0

        bar_w = int(4 * self.scale)
        bar_h = int(30 * self.scale)
        track_h = rect.height - int(60 * self.scale)
        available_track = track_h - bar_h

        bar_x = rect.right - bar_w - int(8 * self.scale)
        bar_y = rect.y + int(40 * self.scale) + int(scroll_pct * available_track)

        # Track line
        pygame.draw.line(surface, GREEN_DIM,
                        (bar_x + bar_w // 2, rect.y + int(40 * self.scale)),
                        (bar_x + bar_w // 2, rect.y + rect.height - int(30 * self.scale)), 1)
        
        # Handle
        pygame.draw.rect(surface, GOLD, (bar_x, bar_y, bar_w, bar_h), 0, border_radius=2)
