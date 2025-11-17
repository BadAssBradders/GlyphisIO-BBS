import pygame
import re
import time
from typing import List, Dict, Any, Tuple, Optional

# -----------------------------------------------------------------------------
# [ CRACKER-PARROT IDE: LAPC-1 Driver Challenge ]
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
# --- CRITICAL F8 EXTERNAL DOCUMENT INTEGRATION ---
#
# The F8 key press *in this game module* sets the boolean flag `self.lapc1_game_instance.docs_active`.
#
# The engineer working on main.py must add the following logic inside the main run() loop
# (after the BBS surface is drawn but before pygame.display.flip()):
#
# if self.state == "lapc1_quiz_session" and self.lapc1_game_instance:
#     if self.lapc1_game_instance.docs_active:
#         # This is the moment to render the external documents onto the main screen (self.screen).
#         # Documents to render are:
#         # - Getting_Started_with_Bradsonic_ASM.pdf
#         # - Radland_LAPC-1_Audio_Chipset_Supplement.pdf
#         self._draw_external_docs_overlay()
#
# -----------------------------------------------------------------------------


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

    def __init__(self, surface, fonts, scale, player_username):
        self.surface = surface
        self.fonts = fonts
        self.scale = scale
        self.player_username = player_username
        
        self.width = self.surface.get_width()
        self.height = self.surface.get_height()

        # --- Colors (Matching BBS style) ---
        self.BLACK = (0, 0, 0)
        self.CYAN = (0, 255, 255)
        self.DARK_CYAN = (0, 139, 139)
        self.GREEN = (0, 255, 0)
        self.DARK_GREEN = (0, 128, 0)
        self.RED = (255, 64, 64)
        self.YELLOW = (255, 255, 0)
        self.HIGHLIGHT_CYAN = (0, 70, 120)

        # --- UI Layout ---
        self.padding = int(12 * self.scale)
        self.editor_pane_rect = pygame.Rect(
            self.padding, self.padding * 4,
            self.width * 0.65, self.height - self.padding * 8
        )
        self.monitor_pane_rect = pygame.Rect(
            self.editor_pane_rect.right + self.padding, self.padding * 4,
            self.width - self.editor_pane_rect.right - self.padding * 2, self.height - self.padding * 8
        )
        self.line_height = self.fonts["small"].get_height() + 2

        # --- Game State ---
        self.game_state = "EDITING"  # EDITING, RUNNING, PAUSED, ERROR, SUCCESS
        self.modal_active = True     # NEW: Start with the modal active
        self.clock = pygame.time.Clock()
        self.sim_speed = 100 # Milliseconds per instruction when running
        self.last_tick_time = 0
        self.exit_requested = False
        self.docs_active = False # CRITICAL FLAG: Toggled by F8, signals main.py to draw docs!

        # --- CPU State (Migration from HTML) ---
        self.cpu_state = {}
        self.code_areas_content: List[List[str]] = []
        self.code_lines_flat: List[Dict[str, Any]] = []
        self.labels: Dict[str, int] = {}
        self.editor_focus_node = 0  # 0-6
        self.cursor_pos = (0, 0)    # (row in node, char index)
        self.zero_flag = False      # Implicit flag state after CMP
        self.packet_queue = []
        self.data_ticks = 0

        # --- Visualizer ---
        self.waveform_history: List[int] = []
        self.max_wave_samples = 80
        
        # --- Editor Setup ---
        self.node_titles = [
            "NODE 01: INIT_POWER (Power On Soundcard)",
            "NODE 02: DIAG_LEFT (Test Left Channel)",
            "NODE 03: DIAG_RIGHT (Test Right Channel)",
            "NODE 04: INIT_VOL (Set Default Volume)",
            "NODE 05: STREAM_ENTRY (Data Loop Start)",
            "NODE 06: DATA_CHECK (Busy Wait for $C403)",
            "NODE 07: OUTPUT_SAMPLE (Transfer Data $C800)",
        ]
        self.node_labels = [
            "INIT_POWER", "DIAG_LEFT", "DIAG_RIGHT", "INIT_VOL",
            "STREAM_ENTRY", "DATA_CHECK", "OUTPUT_SAMPLE"
        ]
        
        # Load the parrot logo for the IDE
        # In a real environment, you'd load the image here
        # self.parrot_logo = pygame.image.load("IDE-Parrot-logo.png") 
        # For this context, we will skip the actual image loading which requires the Pygame image module,
        # but include a placeholder for where it would be drawn.
        self.parrot_logo = self._get_mock_parrot_surface()
        
        self.default_code = self._get_default_code()
        self.reset_state()
        
    def _get_mock_parrot_surface(self):
        """Creates a mock surface for the parrot logo to avoid file dependencies in abstract code."""
        # Using a small placeholder surface since we cannot load images here
        surf = pygame.Surface((64, 64), pygame.SRCALPHA)
        surf.fill((0, 0, 0, 0))
        # Draw a small cyan box as a placeholder for the actual image
        pygame.draw.rect(surf, self.CYAN, (0, 0, 64, 64), 1)
        self._draw_text_on_surface(surf, "PARROT", (5, 25), "tiny", self.CYAN)
        return surf

    def _draw_text_on_surface(self, surface, text, pos, font_key, color):
        """Helper to draw text on an arbitrary surface."""
        try:
            text_surface = self.fonts[font_key].render(text, True, color, self.BLACK)
            surface.blit(text_surface, pos)
        except Exception:
            pass
            
    def _get_default_code(self):
        # *** CHALLENGE MODE: COMPLETELY BLANK. USER MUST TYPE EVERYTHING. ***
        return [
            ["", "", "JMP DIAG_LEFT"],
            ["", "", "", "", "; Max volume L, Mute R", "JMP DIAG_RIGHT"],
            ["", "", "", "", "; Max volume R, Mute L", "JMP INIT_VOL"],
            ["", "", "", "JMP STREAM_ENTRY"],
            ["JMP DATA_CHECK"],
            [f"DATA_CHECK:", "", "", f"BNE DATA_CHECK", "JMP OUTPUT_SAMPLE"],
            [f"OUTPUT_SAMPLE:", "", "", f"JMP DATA_CHECK"]
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
        # Ensure we keep the existing JMPs and Labels if they are present in the default structure
        self.code_areas_content = [lines[:] for lines in self._get_default_code()]
        
        self.editor_focus_node = 0
        self.cursor_pos = (0, 0)
        
        # Reset Data Stream (Initial samples)
        self.packet_queue = [0xAA, 0x99, 0xCC, 0x80, 0x70, 0x60, 0x55, 0x66] 
        self.data_ticks = 10 
        self.waveform_history = []
        
        self.parse_code() # Initial parse
        self.cpu_state["instructionIndex"] = self.labels.get(self.node_labels[0], 0)

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
        
        opcode = instr["opcode"]
        operand_str = instr["operand_str"]
        
        zero_flag_check = self.zero_flag
        
        try:
            if opcode == "LDA":
                if operand_str.startswith('#$'):
                    self.cpu_state["A"] = int(operand_str[2:], 16) & 0xFF
                elif operand_str.startswith('$'):
                    addr = int(operand_str[1:], 16)
                    # Check if address is a known register
                    if addr in self.cpu_state["Memory"]:
                        self.cpu_state["A"] = self.cpu_state["Memory"][addr] & 0xFF
                    else:
                        raise ValueError(f"Invalid Address: {operand_str}")
                else:
                    raise ValueError(f"LDA: Invalid operand format.")
            
            elif opcode == "STA":
                if operand_str.startswith('$'):
                    addr = int(operand_str[1:], 16)
                    if addr in [REG_DATA_READY, REG_PACKET_BUFFER]:
                        raise ValueError(f"STA: Write attempt to read-only register.")
                    if addr in self.cpu_state["Memory"]:
                        self.cpu_state["Memory"][addr] = self.cpu_state["A"]
                    else:
                        raise ValueError(f"Invalid Address: {operand_str}")
                else:
                    raise ValueError(f"STA requires absolute address.")

            elif opcode == "CMP":
                if operand_str.startswith('#$'):
                    val = int(operand_str[2:], 16) & 0xFF
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

        # Check for SUCCESS - The initialization routine is complete when control jumps to STREAM_ENTRY
        if next_idx == self.labels.get("DATA_CHECK", -1) and self.cpu_state["cycles"] > 10:
            if self.cpu_state["Memory"][REG_MASTER_POWER] == ACTIVATION_BYTE and \
               self.cpu_state["Memory"][REG_LEFT_CHANNEL] == DEFAULT_VOLUME and \
               self.cpu_state["Memory"][REG_RIGHT_CHANNEL] == DEFAULT_VOLUME:
                self.game_state = "SUCCESS"
                self.set_success("Initialization complete! Driver ready for continuous streaming. (Task 101 Cleared)")


    # --- Pygame Lifecycle Methods ---

    def handle_event(self, event):
        """Handles Pygame events for the game."""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self.modal_active:
                    self.exit_requested = True
                    return "EXIT" # Exit from modal
                
                self.exit_requested = True
                return "EXIT"
            
            # Modal Handling
            if self.modal_active:
                if event.key == pygame.K_TAB or event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                    self.modal_active = False # Start the game
                return

            if event.key == pygame.K_F8:
                # Toggle the external docs flag
                self.docs_active = not self.docs_active
                if self.cpu_state["isRunning"] and self.docs_active:
                    self.cpu_state["isRunning"] = False
                    self.game_state = "PAUSED"
                return
            
            # Block all other input if docs are active
            if self.docs_active: return

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
            
            # F6: Step (TICK)
            elif event.key == pygame.K_F6:
                if self.game_state in ("EDITING", "PAUSED", "ERROR"):
                    self.parse_code()
                    if self.game_state != "ERROR":
                        self.tick_data_stream()
                        self.execute_instruction()
            
            # F7: Reset
            elif event.key == pygame.K_F7:
                self.reset_state()

            self._handle_editor_input(event)
            
        return None

    # --- External Interface for main.py ---
    def toggle_docs(self):
        """Allows main.py to manage the docs state if needed."""
        self.docs_active = not self.docs_active
    # -------------------------------------


    def _handle_editor_input(self, event):
        """Handles text input and navigation within the editor modules."""
        if self.game_state not in ("EDITING", "PAUSED"): return

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
            if current_line_idx > 0:
                new_row = current_line_idx - 1
                new_char_idx = min(cursor_char_idx, len(lines[new_row]))
            elif node_idx > 0:
                self.editor_focus_node = node_idx - 1
                new_lines = self.code_areas_content[node_idx - 1]
                new_row = len(new_lines) - 1
                new_char_idx = len(new_lines[new_row])

        elif event.key == pygame.K_DOWN:
            if current_line_idx < len(lines) - 1:
                new_row = current_line_idx + 1
                new_char_idx = min(cursor_char_idx, len(lines[new_row]))
            elif node_idx < len(self.code_areas_content) - 1:
                self.editor_focus_node = node_idx + 1
                new_row = 0
                new_char_idx = 0
        
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
            # Only allow a maximum number of lines (e.g., 8 per node)
            if len(lines) < 8:
                new_line = current_line[:cursor_char_idx] + event.unicode.upper() + current_line[cursor_char_idx:]
                lines[current_line_idx] = new_line
                new_char_idx = cursor_char_idx + 1
                
        return (new_row, new_char_idx)

    def update(self, dt):
        """Updates the game logic."""
        if self.game_state == "RUNNING":
            if pygame.time.get_ticks() - self.last_tick_time > self.sim_speed:
                self.last_tick_time = pygame.time.get_ticks()
                self.tick_data_stream()
                self.execute_instruction()
    
    def should_exit(self):
        return self.exit_requested

    # --- Drawing Methods ---

    def draw(self):
        """Main drawing loop."""
        self.surface.fill(self.BLACK)
        self._draw_text("CRACKER-PARROT IDE: LAPC-1 DRIVER CHALLENGE", (self.padding, self.padding), "medium", self.CYAN)
        self._draw_text(f"USER: {self.player_username} | F8: MANUAL | F5: RUN/PAUSE | F6: STEP | F7: RESET | ESC: EXIT", (self.padding, self.padding * 2), "tiny", self.DARK_CYAN)

        self._draw_editor_pane()
        self._draw_monitor_pane()
        self._draw_parrot_logo() # Draw the IDE logo

        status_text = self._get_status_message()
        status_color = self.CYAN if self.game_state == "EDITING" else (self.RED if "ERROR" in status_text else self.GREEN)
        self._draw_text(status_text, (self.padding, self.height - self.padding * 2), "small", status_color)
        
        if self.modal_active:
            self._draw_initial_modal()


    def _draw_parrot_logo(self):
        """Draws the CRACKER-PARROT IDE logo in the bottom left."""
        logo_rect = self.parrot_logo.get_rect()
        logo_rect.bottomleft = (self.padding, self.height - self.padding * 3) # Position above status bar
        
        # Ensure the logo is scaled and drawn with the correct cyan color if possible
        # Since we can't do image processing in this environment, we just draw the mock surface
        self.surface.blit(self.parrot_logo, logo_rect.topleft)
        self._draw_text("CRACKER-PARROT IDE", (logo_rect.right + 5, logo_rect.centery - self.line_height // 2), "tiny", self.CYAN)


    def _draw_initial_modal(self):
        """Draws the narrative modal with uncle-am's questions."""
        
        # Black transparent overlay
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        self.surface.blit(overlay, (0, 0))
        
        # Modal box dimensions
        modal_w = int(self.width * 0.7)
        modal_h = int(self.height * 0.5)
        modal_x = (self.width - modal_w) // 2
        modal_y = (self.height - modal_h) // 2
        modal_rect = pygame.Rect(modal_x, modal_y, modal_w, modal_h)
        
        pygame.draw.rect(self.surface, self.BLACK, modal_rect)
        pygame.draw.rect(self.surface, self.CYAN, modal_rect, 2)
        
        text_x = modal_x + self.padding * 2
        text_y = modal_y + self.padding * 2

        self._draw_text("<< INCOMING TRANSMISSION: uncle-am@ciphernet.net >>", (text_x, text_y), "medium", self.YELLOW)
        text_y += self.line_height * 2
        
        # Uncle-am's context
        context_lines = [
            "Hey Cracker! Glad you made it to the editor.",
            "I've set up the nodes. Now for the core driver logic.",
            "Remember: RADLAND manual (F8) has all the addresses and values.",
            "",
            "// Let's get this soundcard singing for the BBS!",
        ]
        
        for line in context_lines:
            self._draw_text(line, (text_x, text_y), "small", self.CYAN)
            text_y += self.line_height
        
        text_y += self.line_height
        
        # The Challenge Questions
        self._draw_text(UNCLE_AM_Q1, (text_x, text_y), "small", self.GREEN)
        text_y += self.line_height
        self._draw_text(UNCLE_AM_Q2, (text_x, text_y), "small", self.GREEN)
        
        text_y += self.line_height * 3
        
        # Instructions
        self._draw_text("Press [SPACE], [ENTER], or [TAB] to start the challenge.", (text_x, text_y), "medium", self.YELLOW)
        text_y += self.line_height * 2
        self._draw_text("Press [ESC] to quit and return to URGENT OPS.", (text_x, text_y), "small", self.RED)


    def _draw_editor_pane(self):
        """Draws the 7 module editor sections."""
        
        node_margin = int(5 * self.scale)
        col1_w = int(self.editor_pane_rect.width / 3) - node_margin
        col2_w = int(self.editor_pane_rect.width * 2 / 3) - node_margin
        row_h = int(self.editor_pane_rect.height / 4) - node_margin
        
        for i in range(7):
            is_col1 = i < 4
            row_idx = i if is_col1 else i - 4
            
            x_offset = self.editor_pane_rect.x + (0 if is_col1 else col1_w + node_margin)
            y_offset = self.editor_pane_rect.y + row_idx * (row_h + node_margin)
            
            # Recalculate node height for the two columns if necessary to fit (keeping the original ratio)
            if i >= 4:
                # The last 3 nodes share the space of 4 smaller nodes on the left side
                node_h = ((self.editor_pane_rect.height - 4 * node_margin) / 3) - node_margin
                y_offset = self.editor_pane_rect.y + row_idx * (node_h + node_margin)
            else:
                 node_h = row_h # row_h already includes a margin calculation, so use it as the base

            node_rect = pygame.Rect(
                x_offset, y_offset,
                (col1_w if is_col1 else col2_w),
                node_h
            )
            
            # Highlight the focused node
            border_color = self.CYAN if i == self.editor_focus_node and not self.modal_active else self.DARK_CYAN
            pygame.draw.rect(self.surface, border_color, node_rect, 1)
            
            self._draw_text(self.node_titles[i], (node_rect.x + 5, node_rect.y + 5), "tiny", self.YELLOW)
            
            code_y = node_rect.y + int(20 * self.scale)
            for line_idx, line in enumerate(self.code_areas_content[i]):
                
                line_color = self.GREEN
                
                # Check if this line is part of a resolved label
                is_label_start = any(v == self.labels.get(self.node_labels[i], -1) + line_idx for v in self.labels.values()) and line_idx == 0
                
                # Check if line is the current instruction (PC)
                instruction_global_idx = self.labels.get(self.node_labels[i], -1) + line_idx
                is_current_pc = instruction_global_idx == self.cpu_state["instructionIndex"] and self.game_state != "EDITING"

                if is_current_pc:
                    line_color = self.CYAN
                    # Draw a highlight rectangle for the currently executing instruction
                    pygame.draw.rect(self.surface, self.HIGHLIGHT_CYAN, (node_rect.x + 2, code_y, node_rect.width - 4, self.line_height))
                elif is_label_start:
                    line_color = self.YELLOW # Highlight node starting labels
                
                text_rect = self.fonts["small"].render(line, True, line_color)
                self.surface.blit(text_rect, (node_rect.x + 5, code_y))
                
                # Draw Cursor
                if self.game_state in ("EDITING", "PAUSED") and i == self.editor_focus_node and line_idx == self.cursor_pos[0] and not self.modal_active:
                    if pygame.time.get_ticks() % 1000 < 500: # Blinking cursor
                        cursor_x = node_rect.x + 5 + self.fonts["small"].size(line[:self.cursor_pos[1]])[0]
                        pygame.draw.line(self.surface, self.CYAN, (cursor_x, code_y), (cursor_x, code_y + self.line_height - 1), 2)
                        
                code_y += self.line_height
                if code_y > node_rect.bottom - self.line_height: break

    def _draw_monitor_pane(self):
        """Draws CPU state, registers, and visualizer."""
        
        monitor_h = int(self.monitor_pane_rect.height * 0.45)
        monitor_rect = pygame.Rect(self.monitor_pane_rect.x, self.monitor_pane_rect.y, self.monitor_pane_rect.width, monitor_h)
        pygame.draw.rect(self.surface, self.DARK_GREEN, monitor_rect, 1)
        self._draw_text("BRADSONIC CPU MONITOR", (monitor_rect.x + 5, monitor_rect.y + 5), "medium", self.CYAN)
        
        text_x = monitor_rect.x + 10
        y = monitor_rect.y + int(35 * self.scale)
        
        self._draw_key_value(text_x, y, "A (ACCUMULATOR)", self.cpu_state["A"], monitor_rect.right - 10, self.YELLOW)
        y += self.line_height
        self._draw_key_value(text_x, y, "PC (GLOBAL INDEX)", self.cpu_state["instructionIndex"], monitor_rect.right - 10, self.YELLOW)
        y += self.line_height
        self._draw_key_value(text_x, y, "CYCLES", self.cpu_state["cycles"], monitor_rect.right - 10, self.YELLOW)
        y += int(20 * self.scale)

        self._draw_text("LAPC-1 Memory Map", (text_x, y), "small", self.CYAN)
        y += self.line_height
        
        # Check Zero Flag State
        zero_flag_color = self.GREEN if self.zero_flag else self.RED
        self._draw_text(f"Z: {'SET' if self.zero_flag else 'CLEAR'}", (monitor_rect.x + monitor_rect.width - 70, y), "small", zero_flag_color)
        y += self.line_height

        
        for addr, value in self.cpu_state["Memory"].items():
            reg_name = {
                REG_MASTER_POWER: "C400 (PWR)", REG_LEFT_CHANNEL: "C401 (L)",
                REG_RIGHT_CHANNEL: "C402 (R)", REG_DATA_READY: "C403 (RDY)",
                REG_PACKET_BUFFER: "C800 (BUF)"
            }.get(addr, hex(addr).upper())
            
            is_active = False
            if addr == REG_MASTER_POWER: is_active = value == ACTIVATION_BYTE
            elif addr == REG_DATA_READY: is_active = value == READY_STATE
            elif addr in [REG_LEFT_CHANNEL, REG_RIGHT_CHANNEL]: is_active = value > 0x00 and self.cpu_state["Memory"][REG_MASTER_POWER] == ACTIVATION_BYTE
            
            self._draw_key_value(text_x, y, reg_name, value, monitor_rect.right - 40, self.DARK_CYAN)
            self._draw_led(monitor_rect.right - 30, y + self.line_height // 2, is_active, addr)
            y += self.line_height

        # --- Visualizer ---
        visualizer_h = int(self.monitor_pane_rect.height * 0.45)
        visualizer_rect = pygame.Rect(self.monitor_pane_rect.x, monitor_rect.bottom + self.padding, self.monitor_pane_rect.width, visualizer_h)
        pygame.draw.rect(self.surface, self.DARK_GREEN, visualizer_rect, 1)
        self._draw_text("DIAGNOSTIC VISUALIZER", (visualizer_rect.x + 5, visualizer_rect.y + 5), "medium", self.CYAN)
        
        self._draw_waveform_canvas(visualizer_rect)

        # Draw Controls 
        controls_y = visualizer_rect.bottom + self.padding
        self._draw_button("F6 STEP", (visualizer_rect.x, controls_y, visualizer_rect.width // 3 - 5, int(25 * self.scale)), self.CYAN)
        self._draw_button("F5 RUN/PAUSE", (visualizer_rect.x + visualizer_rect.width // 3, controls_y, visualizer_rect.width // 3 - 5, int(25 * self.scale)), self.GREEN)
        self._draw_button("F7 RESET", (visualizer_rect.x + visualizer_rect.width * 2 // 3, controls_y, visualizer_rect.width // 3, int(25 * self.scale)), self.RED)

    def _draw_waveform_canvas(self, pane_rect: pygame.Rect):
        """Draws the audio waveform using Pygame drawing primitives."""
        canvas_rect = pane_rect.inflate(-10, -30)
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

    def _draw_button(self, text, rect_tuple, color):
        """Draws a placeholder button for visual continuity."""
        rect = pygame.Rect(rect_tuple)
        pygame.draw.rect(self.surface, self.BLACK, rect)
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
            # Append the error message stored in the status bar (which is currently just a string, handled by set_error)
            # For simplicity, we just return a generic error message here as the full message is handled by set_error's call.
            return f"ERROR: CRITICAL FAULT. CHECK CODE MODULES. F7 TO RESET."
        if self.game_state == "RUNNING":
            return f"SIMULATION RUNNING: EXECUTION CYCLE {self.cpu_state['cycles']}"
        if self.game_state == "PAUSED":
            return f"SIMULATION PAUSED: CYCLE {self.cpu_state['cycles']}. Press F5 to resume or F7 to reset."
        
        return "EDITING: TYPE LAPC-1 ASSEMBLY CODE INTO MODULES 01-07. F5 TO COMPILE/RUN."

    def set_error(self, message, node_idx, line_idx):
        self.game_state = "ERROR"
        self.cpu_state["isRunning"] = False
        # Store the error message to be displayed later
        self.error_message = f"ERROR: {message} in Node {node_idx+1}, Line {line_idx+1}"
        # We modify _get_status_message to check for and return the self.error_message
        self._get_status_message = lambda: self.error_message

    def set_success(self, message):
        self.game_state = "SUCCESS"
        self.cpu_state["isRunning"] = False
        # Store the success message
        self.success_message = message
        # We modify _get_status_message to check for and return the self.success_message
        self._get_status_message = lambda: f"SUCCESS: {self.success_message}"
        
    def set_status_bar_message(self, message, color):
        pass # Status drawing relies on _get_status_message based on game_state/error_message.

# -----------------------------------------------------------------------------
# Standalone test runner (if you want to run this file directly)
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    # This mock environment is crucial for running the code block in isolation
    # In a real setup, main.py would handle this.
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
        # Attempt to load a real font for better retro look
        test_fonts = {
            "large": pygame.font.Font(None, 40), # Using None for default if "Retro Gaming.ttf" is missing
            "medium": pygame.font.Font(None, 24),
            "small": pygame.font.Font(None, 18),
            "tiny": pygame.font.Font(None, 14)
        }
    except:
        # Fallback to default if even default font fails (unlikely)
        test_fonts = {
            "large": pygame.font.Font(None, 40),
            "medium": pygame.font.Font(None, 24),
            "small": pygame.font.Font(None, 18),
            "tiny": pygame.font.Font(None, 14)
        }
    test_scale = 1.0

    # --- Instantiate the game ---
    game = CRACKER_IDE_LAPC1_Driver_Challenge(screen, test_fonts, test_scale, "test_uncle_am_user")

    clock = pygame.time.Clock()
    running = True

    while running:
        # --- Event Loop ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            if event.type == pygame.KEYDOWN and event.key == pygame.K_F8:
                # Mock handling for F8 in standalone mode
                game.toggle_docs()
                # Ensure the modal is dismissed if F8 is pressed
                game.modal_active = False 

            if event.type == pygame.KEYDOWN:
                action = game.handle_event(event)
                if action == "EXIT":
                    running = False
        
        # --- Update Game ---
        game.update(clock.get_time() / 1000.0)

        # --- Draw Game ---
        game.draw()
        
        # --- Mock External Doc Renderer for Standalone Test ---
        if game.docs_active:
             overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
             overlay.fill((0, 0, 0, 200))
             screen.blit(overlay, (0, 0))
             game._draw_text_on_surface(screen, "EXTERNAL DOCS ARE OPEN NOW (Press F8/ESC to close)", (100, 100), "medium", game.CYAN)


        # --- Update Display ---
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()