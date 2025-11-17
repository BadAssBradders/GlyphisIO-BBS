import pygame
import re
import time

# -----------------------------------------------------------------------------
# [ SIMULACRA_CORE ]
#
# This file contains the complete, self-contained game module for the
# first "test" from glyphis.
#
# --- INTEGRATION GUIDE FOR main.py ---
#
# 1. In your GlyphisIOBBS __init__():
#    Add:
#    self.simulacra_game_instance = None
#
# 2. In your GlyphisIOBBS.draw_games_module():
#    (Or wherever you handle selecting the game)
#    When the player hits ENTER on "Glyph's OnBoarding":
#
#    # --- Create a font dictionary to pass to the game ---
#    # The game needs your loaded fonts and scale
#    fonts = {
#        "large": self.font_large,
#        "medium": self.font_medium,
#        "small": self.font_small,
#        "tiny": self.font_tiny
#    }
#
#    # --- Instantiate the game ---
#    # Pass the main BBS surface, the fonts, the scale, and player name
#    from simulacra_core import SimulacraCoreGame
#    self.simulacra_game_instance = SimulacraCoreGame(
#        self.bbs_surface,
#        fonts,
#        self.scale,
#        self.player_email
#    )
#
#    # --- Change the main BBS state ---
#    self.state = "simulacra_core"
#
# 3. In your main run() loop (event handling):
#    Add a check for the new state:
#
#    elif self.state == "simulacra_core":
#        if event.type == pygame.KEYDOWN:
#            # Pass the event to the game
#            action = self.simulacra_game_instance.handle_event(event)
#            if action == "EXIT":
#                self.state = "games" # Or "main_menu"
#                self.simulacra_game_instance = None
#
# 4. In your main run() loop (drawing):
#    Add a check for the new state:
#
#    elif self.state == "simulacra_core":
#        if self.simulacra_game_instance:
#            self.simulacra_game_instance.draw()
#
# -----------------------------------------------------------------------------


class SimulacraCoreGame:
    """
    A self-contained Pygame module for the SIMULACRA_CORE hacking puzzle.
    It is designed to be "plugged into" the main GlyphisIOBBS class.
    It receives a surface to draw on and fonts to use, and handles
    its own input, logic, and drawing within that surface.
    """

    def __init__(self, surface, fonts, scale, player_username, best_tcs=None, on_new_best=None, on_level_cleared=None):
        self.surface = surface
        self.fonts = fonts  # Expects a dict: {"small": font, "medium": font, ...}
        self.scale = scale
        self.player_username = player_username
        self.best_recorded_tcs = best_tcs if best_tcs is not None else None
        self.on_new_best = on_new_best
        self.on_level_cleared = on_level_cleared

        # Get dimensions from the passed surface
        self.width = self.surface.get_width()
        self.height = self.surface.get_height()

        # --- Colors (to match main.py) ---
        self.BLACK = (0, 0, 0)
        self.CYAN = (0, 255, 255)
        self.DARK_BLUE = (0, 0, 139)
        self.DARK_CYAN = (0, 139, 139)
        self.RED = (255, 64, 64)
        self.GREEN = (0, 255, 0)
        self.YELLOW = (255, 255, 0)
        self.WHITE = (220, 220, 220)
        self.CORAL = (255, 127, 80)

        # --- UI Pane Layout ---
        # Using pygame.Rect for cleaner management
        padding = int(10 * self.scale)
        header_height = int(68 * self.scale)
        footer_height = int(40 * self.scale)
        console_height = int(230 * self.scale)
        sim_width = int(self.width * 0.44) - int(padding * 1.2)

        vertical_gap = int(28 * self.scale)
        available_height = self.height - header_height - console_height - footer_height - vertical_gap
        editor_height = int(available_height * 0.5)
        editor_height = max(editor_height, int(230 * self.scale))
        sim_height = available_height - editor_height
        sim_height = max(sim_height, int(230 * self.scale))

        self.editor_pane = pygame.Rect(
            padding,
            header_height,
            self.width - sim_width - (padding * 3),
            editor_height
        )
        self.sim_pane = pygame.Rect(
            self.editor_pane.right + padding,
            header_height,
            sim_width,
            sim_height
        )
        bottom_y = max(self.editor_pane.bottom, self.sim_pane.bottom)

        self.console_pane = pygame.Rect(
            padding,
            bottom_y + vertical_gap,
            self.width - (padding * 2),
            console_height
        )

        # --- Game State ---
        self.game_state = "EDITING"  # Primary states: EDITING, RUNNING, FAILED, SUCCESS
        self.debug_log = []
        self.active_file = "PAYLOAD.SIM"

        # --- Code Editor State ---
        self.code_lines = [] # This now stores *only* the command string, not the line number
        self.active_line = 0 # This is the list index
        self.cursor_pos = 0  # This is the string index in code_lines[active_line]
        self.editor_scroll_y = 0

        # --- Simulation State ---
        self.sim_cycle = 0
        self.sim_pc = 0  # Program Counter (list index)
        self.line_number_map = {} # Maps BASIC line number (10, 20...) to list index (0, 1...)
        self.sim_player_pos = [0, 0]
        self.sim_warden_pos = [0, 0]
        self.last_tick_time = 0
        self.sim_speed = 400  # Milliseconds per cycle

        # --- Multi-level tracking ---
        self.current_level = 1
        self.max_levels = 3
        self.level_definitions = self._build_levels()
        self.level_files = {}

        self.total_cycle_count = 0
        self.total_instruction_count = 0
        self.total_timer_start = None
        self.total_timer_end = None
        self.pending_score = None
        self.final_summary = None
        self.leaderboard_visible = False

        # --- Leaderboard placeholder ---
        self.leaderboard = self._build_default_leaderboard()

        # Startup presentation (loading screen + ASCII intro)
        self.level_pending_id = None
        self.level_preserve_log = False
        self.startup_phase = "loading"  # loading -> ascii -> active
        self.loading_start_time = pygame.time.get_ticks()
        self.loading_duration = 5000 # milliseconds
        self.ascii_display_start = None

        ascii_font_size = max(12, int(14 * self.scale))
        try:
            self.ascii_font = pygame.font.SysFont("Courier New", ascii_font_size)
        except Exception:
            self.ascii_font = self.fonts["tiny"]
        self.ascii_lines = self._build_ascii_lines()

        # Prime the first array (deferred until intro completes)
        self.load_level(self.current_level, preserve_log=False, defer=True)

    def _build_levels(self):
        base_readme = [
            "OPERATIVE:",
            "",
            "This is the SIMULACRA_CORE. It tests payload",
            "logic against hostile networks.",
            "",
            "OBJECTIVE: Guide the packet [S] to [E] without", 
            "triggering the Warden.",
            "TIMER: Starts when you edit PAYLOAD.SIM and runs",
            "until the third array is breached.",
            "SCORE: Time Cycle Score (seconds + total cycles).",
            "Lower is better.",
            "",
            "COMMANDS: MOV <UP|DOWN|LEFT|RIGHT>",
            "          WAIT",
            "          GOTO <LINE_NUM>",
            "          // (Comment)",
            "-glyphis"
        ]

        return [
            {
                "id": 1,
                "name": "TEST_ARRAY_01",
                "readme": base_readme,
                "payload": [
                    "// PAYLOAD.SIM - ARRAY 01",
                    "// STATUS: BROKEN",
                    "",
                    "MOV RIGHT",
                    "MOV RIGHT",
                    "MOV DOWN",
                    "MOV RIGHT",
                    "GOTO 80"
                ],
                "grid": [
                    [0, 0, 0, 0],
                    [1, 0, 0, 1],
                    [0, 0, 0, 2]
                ],
                "start": [0, 0],
                "end": [3, 2],
                "warden_path": [[1, 1], [2, 1]]
            },
            {
                "id": 2,
                "name": "TEST_ARRAY_02",
                "readme": [
                    "OPERATIVE:",
                    "",
                    "ARRAY 02 extends the lattice.",
                    "Central columns are patrolled by the Warden.",
                    "Stagger your waits and loops.",
                    "",
                    "Remember: the timer is still running.",
                    "",
                    "-glyphis"
                ],
                "payload": [
                    "// PAYLOAD.SIM - ARRAY 02",
                    "// STATUS: BROKEN",
                    "",
                    "MOV RIGHT",
                    "MOV RIGHT",
                    "MOV DOWN",
                    "WAIT",
                    "MOV RIGHT",
                    "GOTO 40"
                ],
                "grid": [
                    [0, 0, 0, 0, 0],
                    [0, 1, 0, 1, 0],
                    [0, 0, 0, 0, 0],
                    [1, 0, 1, 0, 2]
                ],
                "start": [0, 0],
                "end": [4, 3],
                "warden_path": [[2, 0], [2, 1], [2, 2], [2, 1]]
            },
            {
                "id": 3,
                "name": "TEST_ARRAY_03",
                "readme": [
                    "OPERATIVE:",
                    "",
                    "Final array. Split corridors, double backs.",
                    "Warden sweeps a long loop. Watch the cadence.",
                    "",
                    "Deliver the payload and seal the run.",
                    "",
                    "-glyphis"
                ],
                "payload": [
                    "// PAYLOAD.SIM - ARRAY 03",
                    "// STATUS: BROKEN",
                    "",
                    "MOV RIGHT",
                    "MOV DOWN",
                    "MOV RIGHT",
                    "MOV UP",
                    "MOV RIGHT",
                    "GOTO 60"
                ],
                "grid": [
                    [0, 0, 0, 1, 0, 0],
                    [1, 0, 0, 1, 0, 1],
                    [0, 0, 0, 0, 0, 0],
                    [0, 1, 1, 0, 1, 2]
                ],
                "start": [0, 0],
                "end": [5, 3],
                "warden_path": [
                    [2, 0], [2, 1], [2, 2], [3, 2], [4, 2], [4, 1],
                    [4, 2], [3, 2], [2, 2], [1, 2], [1, 1], [2, 1]
                ]
            }
        ]

    def _build_default_leaderboard(self):
        return [
            {"username": "glyphis", "time": 64.2, "cycles": 45, "instructions": 24, "tcs": 109.2},
            {"username": "rain", "time": 72.8, "cycles": 49, "instructions": 26, "tcs": 121.8},
            {"username": "jaxkando", "time": 85.5, "cycles": 55, "instructions": 29, "tcs": 140.5},
            {"username": "uncle-am", "time": 99.0, "cycles": 64, "instructions": 32, "tcs": 163.0}
        ]

    def _build_ascii_lines(self):
        return [
            "███████╗██║███╗   ███╗██╗   ██╗██╗      █████╗  ██████╗██████╗  █████╗  ",
            "██╔════╝██║████╗ ████║██║   ██║██║     ██╔══██╗██╔════╝██╔══██╗██╔══██╗ ",
            "███████╗██║██╔████╔██║██║   ██║██║     ███████║██║     ██████╔╝███████║ ",
            "╚════██║██║██║╚██╔╝██║██║   ██║██║     ██╔══██║██║     ██╔══██╗██╔══██║",
            "███████║██║██║ ╚═╝ ██║╚██████╔╝███████╗██║  ██║╚██████╗██║  ██║██║  ██║",
            "╚══════╝╚═╝╚═╝     ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝",
            "",
            "        ██████╗ ██████╗ ██████╗ ███████╗",
            "        ██╔════╝██╔═══██╗██╔══██╗██╔════╝",
            "        ██║     ██║   ██║██████╔╝█████╗  ",
            "        ██║     ██║   ██║██╔══██╗██╔══╝  ",
            "███████╗╚██████╗╚██████╔╝██║  ██║███████╗",
            "╚══════╝ ╚═════╝ ╚═════╝ ╚═╝  ╚═╝╚══════╝"
        ]

    def load_level(self, level_id, *, preserve_log=False, defer=False):
        """Initialises the given array definition."""
        if level_id < 1 or level_id > len(self.level_definitions):
            level_id = 1

        if defer:
            self.level_pending_id = level_id
            self.level_preserve_log = preserve_log
            return

        level = self.level_definitions[level_id - 1]

        if not preserve_log:
            self.debug_log = [
                "SIMULACRA_CORE v1.0",
                f"Loaded '{level['name']}'.",
                f"BEST TIME CYCLE SCORE: {self._format_tcs(self.best_recorded_tcs)}",
                "Timer engages on first PAYLOAD.SIM edit.",
                "F1:README | F2:PAYLOAD | F5:RUN | F8:RESET RUN | ESC:EXIT",
                f"Glyphis: Greetings {self.player_username}. Three arrays await.",
                "Glyphis: TCS = seconds elapsed + total cycles.",
                "Glyphis: BREACH ALL THREE ARRAYS TO REGISTER YOUR SCORE."
            ]
        else:
            self.add_log("")
            self.add_log(f"--- {level['name']} ---")
            self.add_log("Glyphis: Clock still running. Deliver the payload.")

        self.game_state = "EDITING"
        self.current_level = level_id
        self.leaderboard_visible = False

        # File definitions
        self.level_pending_id = None
        self.level_preserve_log = False

        self.level_files = {
            "README.TXT": list(level["readme"]),
            "PAYLOAD.SIM": list(level["payload"])
        }
        self.active_file = "PAYLOAD.SIM"
        self.code_lines = self.level_files[self.active_file][:]
        self.active_line = 0
        self.cursor_pos = 0
        self.editor_scroll_y = 0

        # Grid and entities
        self.grid_map = [row[:] for row in level["grid"]]
        self.grid_size_y = len(self.grid_map)
        self.grid_size_x = len(self.grid_map[0]) if self.grid_map else 0
        self.start_pos = list(level["start"])
        self.end_pos = list(level["end"])
        self.sim_player_pos = list(self.start_pos)

        self.warden_patrol_path = [list(pos) for pos in level["warden_path"]]
        self.warden_start_pos = list(self.warden_patrol_path[0]) if self.warden_patrol_path else [0, 0]
        self.sim_warden_pos = list(self.warden_start_pos)
        self.warden_path_index = 0

        # Simulation reset
        self.reset_sim_vars()

    def reset_level(self):
        """Resets the full run back to array 1."""
        self.add_log("F8: Resetting run. Timer cleared.")
        self.current_level = 1
        self.total_cycle_count = 0
        self.total_instruction_count = 0
        self.total_timer_start = None
        self.total_timer_end = None
        self.pending_score = None
        self.final_summary = None
        self.leaderboard_visible = False
        self.startup_phase = "active"
        self.load_level(1, preserve_log=False)

    def reset_sim_vars(self):
        """Resets the simulation variables to their start state."""
        self.sim_cycle = 0
        self.sim_pc = 0
        self.sim_player_pos = list(self.start_pos)
        self.sim_warden_pos = list(self.warden_start_pos)
        self.warden_path_index = 0
        self.game_state = "EDITING"

    def handle_event(self, event):
        """Handles a single Pygame event passed from the main BBS loop."""
        if event.type != pygame.KEYDOWN:
            return None

        if event.key == pygame.K_ESCAPE:
            return "EXIT"  # Signal to main loop to close the game

        if self.startup_phase == "loading":
            return None

        if self.startup_phase == "ascii":
            if event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_F5):
                self._complete_startup()
            return None

        if event.key == pygame.K_l and self.startup_phase == "active":
            if not (self.game_state == "EDITING" and self.active_file == "PAYLOAD.SIM"):
                self.leaderboard_visible = not self.leaderboard_visible
                return None

        if event.key == pygame.K_F5:
            if self.game_state in ("EDITING", "FAILED"):
                if self.total_timer_start is None and self.active_file == "PAYLOAD.SIM":
                    self._start_total_timer()
                self.run_simulation()
            return

        if event.key == pygame.K_F8:
            if self.game_state in ("EDITING", "SUCCESS", "FAILED"):
                self.reset_level()
            return
        
        # --- File Switching ---
        if event.key == pygame.K_F1:
            if self.game_state == "EDITING":
                self.active_file = "README.TXT"
                # No code editing on README, so we don't copy
                self.code_lines = self.level_files[self.active_file]
                self.active_line = 0
                self.cursor_pos = 0
            return
        if event.key == pygame.K_F2:
            if self.game_state == "EDITING":
                self.active_file = "PAYLOAD.SIM"
                # Copy the script for editing
                self.code_lines = self.level_files[self.active_file][:]
                self.active_line = 0
                self.cursor_pos = 0
            return

        # --- Stop input if simulation is running ---
        if self.game_state != "EDITING" or self.active_file != "PAYLOAD.SIM":
            # Allow scrolling in README
            if self.active_file == "README.TXT":
                if event.key == pygame.K_UP:
                    self.editor_scroll_y = max(0, self.editor_scroll_y - 1)
                elif event.key == pygame.K_DOWN:
                    self.editor_scroll_y += 1 # Will be clamped in draw
            return

        # --- Text Editor Logic ---
        if self.total_timer_start is None and self._event_starts_edit(event):
            self._start_total_timer()

        current_line = self.code_lines[self.active_line]

        if event.key == pygame.K_BACKSPACE:
            if self.cursor_pos > 0:
                # Regular backspace
                self.code_lines[self.active_line] = current_line[:self.cursor_pos - 1] + current_line[self.cursor_pos:]
                self.cursor_pos -= 1
            elif self.active_line > 0:
                # Backspace at start of line, merge with line above
                prev_line = self.code_lines[self.active_line - 1]
                self.cursor_pos = len(prev_line)
                self.code_lines[self.active_line - 1] = prev_line + current_line
                self.code_lines.pop(self.active_line)
                self.active_line -= 1
        
        elif event.key == pygame.K_RETURN:
            # --- MODIFIED: Insert new line, split text at cursor ---
            before_cursor = current_line[:self.cursor_pos]
            after_cursor = current_line[self.cursor_pos:]
            self.code_lines[self.active_line] = before_cursor # Current line becomes text before cursor
            self.active_line += 1
            self.code_lines.insert(self.active_line, after_cursor) # New line gets text after cursor
            self.cursor_pos = 0

        elif event.key == pygame.K_UP:
            self.active_line = max(0, self.active_line - 1)
            self.cursor_pos = min(self.cursor_pos, len(self.code_lines[self.active_line]))
        
        elif event.key == pygame.K_DOWN:
            self.active_line = min(len(self.code_lines) - 1, self.active_line + 1)
            self.cursor_pos = min(self.cursor_pos, len(self.code_lines[self.active_line]))

        elif event.key == pygame.K_LEFT:
            self.cursor_pos = max(0, self.cursor_pos - 1)
        
        elif event.key == pygame.K_RIGHT:
            self.cursor_pos = min(len(current_line), self.cursor_pos + 1)
        
        elif event.key == pygame.K_HOME:
            self.cursor_pos = 0
        
        elif event.key == pygame.K_END:
            self.cursor_pos = len(current_line)

        elif event.unicode.isprintable():
            # Add typed character
            self.code_lines[self.active_line] = current_line[:self.cursor_pos] + event.unicode + current_line[self.cursor_pos:]
            self.cursor_pos += 1

    def _event_starts_edit(self, event):
        if getattr(event, "key", None) is None:
            return False
        if event.key in (pygame.K_BACKSPACE, pygame.K_RETURN, pygame.K_DELETE):
            return True
        if getattr(event, "unicode", "") and event.unicode.strip():
            return True
        return False

    def _start_total_timer(self):
        if self.total_timer_start is None:
            self.total_timer_start = pygame.time.get_ticks()
            self.total_timer_end = None
            self.add_log("Timer engaged. Time Cycle Score tracking active.")

    def run_simulation(self):
        """Prepares and starts the simulation."""
        # --- MODIFIED: Save the edited script back to the file list ---
        # This makes F8 (Reset) feel like reloading from "disk"
        self.level_files["PAYLOAD.SIM"] = self.code_lines[:]

        self.add_log("F5: Running 'PAYLOAD.SIM'...")
        self.reset_sim_vars()
        self.game_state = "RUNNING"
        self.last_tick_time = pygame.time.get_ticks()
        
        # --- MODIFIED: Build GOTO map ---
        # Maps the *BASIC line number* (e.g., 80) to the *list index* (e.g., 7)
        self.line_number_map = {}
        for i, line in enumerate(self.code_lines):
            line_num = (i + 1) * 10 # 10, 20, 30...
            self.line_number_map[line_num] = i
        
        self.add_log("Built GOTO map. Starting simulation...")
        # Start at the first line
        self.sim_pc = 0

    def tick_simulation(self):
        """Executes a single cycle of the simulation."""
        if self.game_state != "RUNNING":
            return

        self.sim_cycle += 1
        
        # --- 1. Check for end-of-program ---
        if self.sim_pc >= len(self.code_lines):
            self.fail_simulation("EXECUTION FINISHED", "Payload ended without reaching [E].")
            return

        # Get current line number for logging
        current_basic_line = (self.sim_pc + 1) * 10
        log_msg = f"CYCLE {self.sim_cycle} (L{current_basic_line}): "

        # --- 2. Check for initial collision/win ---
        if self.sim_player_pos == self.sim_warden_pos:
            self.fail_simulation("PACKET COLLISION", f"Intercepted by [W] at {self.sim_player_pos}.")
            return
        if self.sim_player_pos == self.end_pos:
            self.succeed_simulation()
            return

        # --- 3. Parse and Execute Player Command ---
        line = self.code_lines[self.sim_pc]
        command = self.parse_line(line)
        
        next_pc = self.sim_pc + 1 # Default next line
        
        if command["type"] == "ERROR":
            self.fail_simulation("SYNTAX ERROR", f"L{current_basic_line}: {command['msg']}")
            return
        
        elif command["type"] == "MOV":
            dx, dy = command["dir"]
            new_x = self.sim_player_pos[0] + dx
            new_y = self.sim_player_pos[1] + dy
            log_msg += f"[S] MOV {command['str']}. "
            
            # Check bounds
            if 0 <= new_y < self.grid_size_y and 0 <= new_x < self.grid_size_x:
                # Check for wall
                if self.grid_map[new_y][new_x] == 1:
                    wall_pos = [x for x in [[0,1], [3,1]] if new_x == x[0] and new_y == x[1]]
                    log_msg += f"Hit firewall at {wall_pos}!"
                    self.fail_simulation("RUNTIME ERROR", f"Payload collided with firewall at {wall_pos}.")
                    return
                else:
                    self.sim_player_pos = [new_x, new_y]
            else:
                self.fail_simulation("RUNTIME ERROR", "Payload moved out of bounds.")
                return

        elif command["type"] == "WAIT":
            log_msg += "[S] WAIT. "

        elif command["type"] == "GOTO":
            target_line_num = command["target"]
            if target_line_num in self.line_number_map:
                next_pc = self.line_number_map[target_line_num]
                log_msg += f"[S] GOTO {target_line_num}. "
            else:
                self.fail_simulation("RUNTIME ERROR", f"GOTO target '{target_line_num}' not found.")
                return

        # --- 4. Move Warden ---
        self.warden_path_index = (self.warden_path_index + 1) % len(self.warden_patrol_path)
        self.sim_warden_pos = list(self.warden_patrol_path[self.warden_path_index])
        log_msg += f"[W] -> {self.sim_warden_pos}."

        # --- 5. Add log and update PC ---
        self.add_log(log_msg)
        self.sim_pc = next_pc

        # --- 6. Check for post-move collision/win ---
        if self.sim_player_pos == self.sim_warden_pos:
            self.fail_simulation("PACKET COLLISION", f"Intercepted by [W] at {self.sim_player_pos}.")
            return
        if self.sim_player_pos == self.end_pos:
            self.succeed_simulation()
            return
            
    def parse_line(self, line):
        """Parses a line of SIM_BASIC. Returns a command dictionary."""
        
        # --- MODIFIED: Line no longer has number prefix ---
        line_content = line.split("//")[0].strip()
        cmd = line_content.upper()

        if cmd == "":
            return {"type": "WAIT"} # Empty lines are treated as WAIT

        if cmd.startswith("MOV"):
            parts = cmd.split()
            if len(parts) != 2:
                return {"type": "ERROR", "msg": "MOV requires 1 argument"}
            direction = parts[1]
            if direction == "UP": return {"type": "MOV", "dir": [0, -1], "str": "UP"}
            if direction == "DOWN": return {"type": "MOV", "dir": [0, 1], "str": "DOWN"}
            if direction == "LEFT": return {"type": "MOV", "dir": [-1, 0], "str": "LEFT"}
            if direction == "RIGHT": return {"type": "MOV", "dir": [1, 0], "str": "RIGHT"}
            return {"type": "ERROR", "msg": f"Unknown MOV direction '{direction}'"}
        
        if cmd == "WAIT":
            return {"type": "WAIT"}

        if cmd.startswith("GOTO"):
            parts = cmd.split()
            if len(parts) != 2:
                return {"type": "ERROR", "msg": "GOTO requires 1 argument"}
            if parts[1].isdigit():
                return {"type": "GOTO", "target": int(parts[1])}
            else:
                return {"type": "ERROR", "msg": f"GOTO target must be a line number"}
        
        return {"type": "ERROR", "msg": f"Unknown command '{cmd}'"}

    def fail_simulation(self, title, message):
        """Stops the simulation on failure."""
        self.game_state = "FAILED"
        self.add_log("")
        self.add_log(f"--- {title} ---")
        self.add_log(message)
        self.add_log("Press F8 to reset.")

    def succeed_simulation(self):
        """Handles success, advancing arrays or finalising the run."""
        cycles = self.sim_cycle
        instructions = 0
        for line in self.code_lines:
            line_content = line.split("//")[0].strip()
            if line_content:
                instructions += 1

        self.total_cycle_count += cycles
        self.total_instruction_count += instructions

        if self.current_level < self.max_levels:
            cleared_level = self.current_level
            self.add_log("")
            self.add_log(f"--- PAYLOAD DELIVERED: ARRAY {self.current_level:02d} ---")
            self.add_log(f"Cycles: {cycles} | Instructions: {instructions}")
            self.add_log("Glyphis: Next array online. Timer continues.")
            if self.on_level_cleared:
                try:
                    self.on_level_cleared(cleared_level)
                except Exception as exc:
                    print(f"[SIMULACRA_CORE] Error notifying level clear: {exc}")
            self.current_level += 1
            self.load_level(self.current_level, preserve_log=True)
            return

        # Final array breached
        self.game_state = "SUCCESS"
        if self.total_timer_start is not None and self.total_timer_end is None:
            self.total_timer_end = pygame.time.get_ticks()

        total_time = self.get_total_elapsed_seconds()
        tcs = total_time + self.total_cycle_count

        self.final_summary = {
            "time": total_time,
            "cycles": self.total_cycle_count,
            "instructions": self.total_instruction_count,
            "tcs": tcs,
            "best_tcs": self.best_recorded_tcs
        }

        self.add_log("")
        self.add_log("--- FINAL ARRAY BREACHED ---")
        self.add_log(f"Total Time: {self._format_time(total_time)} | Total Cycles: {self.total_cycle_count}")
        self.add_log(f"Time Cycle Score: {tcs:.2f} (lower is better)")
        self.add_log("Glyphis: Upload complete. Press F8 for a fresh run.")

        attempt_entry = {
            "username": self.player_username,
            "time": total_time,
            "cycles": self.total_cycle_count,
            "instructions": self.total_instruction_count,
            "tcs": tcs
        }

        recorded = False
        for entry in self.leaderboard:
            if entry["username"] == self.player_username:
                if tcs < entry["tcs"]:
                    entry.update(attempt_entry)
                recorded = True
                break
        if not recorded:
            self.leaderboard.append(attempt_entry)

        self.leaderboard.sort(key=lambda e: e["tcs"])
        self.pending_score = attempt_entry.copy()
    
    def add_log(self, message):
        """Adds a message to the debug log."""
        self.debug_log.append(message)
        if len(self.debug_log) > 100: # Prevent memory leak
            self.debug_log.pop(0)

    def take_pending_score(self):
        score = self.pending_score
        self.pending_score = None
        return score

    def handle_score_persisted(self, result, attempt):
        stored = result.get("stored") if isinstance(result, dict) else None
        updated = result.get("updated") if isinstance(result, dict) else False

        if stored is None:
            self.add_log("Glyphis: Guest sessions do not retain Time Cycle Scores.")
            return

        if updated:
            self.add_log(f"Glyphis: New Time Cycle Score recorded: {stored:.2f}.")
            if self.on_new_best:
                try:
                    self.on_new_best(attempt.get("tcs", stored))
                except Exception as exc:
                    print(f"[SIMULACRA_CORE] Error notifying new best TCS: {exc}")
        else:
            self.add_log(f"Glyphis: BEST TIME CYCLE SCORE REMAINS {stored:.2f}.")

        self.best_recorded_tcs = stored
        if self.final_summary is not None:
            self.final_summary["best_tcs"] = stored

    def get_total_elapsed_seconds(self):
        if self.total_timer_start is None:
            return 0.0
        end_ms = self.total_timer_end if self.total_timer_end is not None else pygame.time.get_ticks()
        elapsed = max(0, end_ms - self.total_timer_start)
        return elapsed / 1000.0

    def get_current_tcs(self):
        time_component = self.get_total_elapsed_seconds()
        cycle_component = self.total_cycle_count
        if self.game_state == "RUNNING":
            cycle_component += self.sim_cycle
        return time_component + cycle_component

    def _format_time(self, seconds):
        seconds = max(0.0, seconds)
        minutes = int(seconds // 60)
        remainder = seconds - (minutes * 60)
        return f"{minutes:02d}:{remainder:04.1f}"

    def _format_tcs(self, value):
        if value is None:
            return "--"
        try:
            return f"{float(value):.2f}"
        except (TypeError, ValueError):
            return "--"

    def _draw_loading_screen(self, now):
        header = "SIMULACRA_CORE :: LINK NEGOTIATION"
        self._draw_text(header, (int(40 * self.scale), int(80 * self.scale)), "medium", self.CYAN)

        status_lines = [
            "Establishing secure uplink...",
            "Preparing payload arrays...",
            "Calibrating warden telemetry..."
        ]
        for idx, line in enumerate(status_lines):
            self._draw_text(line, (int(40 * self.scale), int((130 + idx * 24) * self.scale)), "small", self.DARK_CYAN)

        progress = min(1.0, max(0.0, (now - self.loading_start_time) / max(1, self.loading_duration)))
        bar_x = int(40 * self.scale)
        bar_y = int(220 * self.scale)
        bar_w = int(self.width - 2 * bar_x)
        bar_h = int(32 * self.scale)
        pygame.draw.rect(self.surface, self.DARK_BLUE, (bar_x, bar_y, bar_w, bar_h), 2)
        fill_w = int((bar_w - int(4 * self.scale)) * progress)
        if fill_w > 0:
            pygame.draw.rect(
                self.surface,
                self.CYAN,
                (bar_x + int(2 * self.scale), bar_y + int(2 * self.scale), fill_w, bar_h - int(4 * self.scale))
            )

        pct_text = f"{int(progress * 100):02d}%"
        pct_width = self.fonts["small"].size(pct_text)[0]
        pct_x = bar_x + (bar_w - pct_width) // 2
        self._draw_text(pct_text, (pct_x, bar_y + bar_h + int(6 * self.scale)), "small", self.CYAN)

        hint = "Glyphis: Stand by. SIMULACRA Core will engage momentarily."
        self._draw_text(hint, (int(40 * self.scale), int(280 * self.scale)), "tiny", self.WHITE)

        special_msg = "BRADSONIC Radland LAPC-1 Sound Card Detected!"
        if (now - self.loading_start_time) % 1400 < 700:
            self._draw_text(special_msg, (int(40 * self.scale), int(312 * self.scale)), "small", self.GREEN)

    def _draw_ascii_intro(self, now):
        title = "SIMULACRA_CORE :: ACCESS GRANTED"
        self._draw_text(title, (int(20 * self.scale), int(40 * self.scale)), "medium", self.CYAN)

        art_start_y = int(90 * self.scale)
        art_offset_x = -40
        line_spacing = int(4 * self.scale)
        current_y = art_start_y
        for line in self.ascii_lines:
            line_width, line_height = self.ascii_font.size(line)
            x = max(0, (self.width - line_width) // 2 + int(art_offset_x * self.scale))
            cursor_x = x
            for ch in line:
                color = self.CYAN if ch == "█" else self.DARK_CYAN
                glyph = self.ascii_font.render(ch, True, color)
                self.surface.blit(glyph, (cursor_x, current_y))
                cursor_x += glyph.get_width()
            current_y += line_height + line_spacing

        coral_lines = [
            "+-+ +-+-+-+-+-+-+-+-+-+-+ +-+-+-+-+ +-+-+-+-+-+ +-+-+ +-+-+-+-+-+-+-+",
            " |A| |S|I|M|U|L|A|T|I|O|N| |T|E|S|T| |A|R|R|A|Y| |B|Y| |G|L|Y|P|H|I|S|",
            " +-+ +-+-+-+-+-+-+-+-+-+-+ +-+-+-+-+ +-+-+-+-+-+ +-+-+ +-+-+-+-+-+-+-+"
        ]
        coral_font_size = max(12, self.fonts["tiny"].get_height() + 3)
        try:
            coral_font = pygame.font.SysFont("Courier New", coral_font_size)
        except Exception:
            coral_font = pygame.font.Font(None, coral_font_size)
        coral_spacing = int(6 * self.scale)
        band_colors = [
            (35, 80, 81),
            (0, 251, 255),
            (255, 255, 255),
            (0, 251, 255),
            (35, 80, 81)
        ]
        non_empty_lengths = [len(line) for line in coral_lines if line]
        max_len = max(non_empty_lengths) if non_empty_lengths else 1
        band_width = max(1, (max_len + len(band_colors) - 1) // len(band_colors))
        band_period = band_width * len(band_colors)
        phase = int((now // 80) % band_period)

        for line in coral_lines:
            if not line:
                current_y += coral_font.get_height() + coral_spacing
                continue

            text_width, text_height = coral_font.size(line)
            x = max(0, (self.width - text_width) // 2)
            cursor_x = x
            for idx, ch in enumerate(line):
                band_index = ((idx - phase) // band_width) % len(band_colors)
                color = band_colors[band_index]
                glyph = coral_font.render(ch, True, color)
                self.surface.blit(glyph, (cursor_x, current_y))
                cursor_x += glyph.get_width()

            current_y += text_height + coral_spacing

        info_y = current_y + int(20 * self.scale)
        self._draw_text(
            f"BEST RECORDED TCS: {self._format_tcs(self.best_recorded_tcs)}",
            (int(40 * self.scale), info_y),
            "small",
            self.WHITE
        )
        self._draw_text(
            "TIMER ENGAGES WHEN YOU EDIT PAYLOAD.SIM.\nBREACH ALL THREE ARRAYS TO POST A SCORE.",
            (int(40 * self.scale), info_y + int(26 * self.scale)),
            "small",
            self.DARK_CYAN
        )

        if (now // 500) % 2 == 0:
            prompt = "Press ENTER to launch ARRAY 01"
            prompt_width = self.fonts["small"].size(prompt)[0]
            prompt_x = max(0, (self.width - prompt_width) // 2)
            self._draw_text(prompt, (prompt_x, info_y + int(76 * self.scale)), "small", self.WHITE)

    def _complete_startup(self):
        if self.startup_phase == "active":
            return

        target_level = self.level_pending_id or self.current_level
        self.startup_phase = "active"
        self.leaderboard_visible = False
        if target_level is not None:
            self.load_level(target_level, preserve_log=self.level_preserve_log, defer=False)

    def draw(self):
        """Main draw call from the BBS loop."""
        now = pygame.time.get_ticks()

        if self.startup_phase == "loading":
            if now - self.loading_start_time >= self.loading_duration:
                self.startup_phase = "ascii"
                self.ascii_display_start = now
            self.surface.fill(self.BLACK)
            self._draw_loading_screen(now)
            return

        if self.startup_phase == "ascii":
            self.surface.fill(self.BLACK)
            self._draw_ascii_intro(now)
            return

        self.surface.fill(self.BLACK)

        # --- Run simulation tick if active ---
        if self.game_state == "RUNNING":
            if now - self.last_tick_time > self.sim_speed:
                self.last_tick_time = now
                self.tick_simulation()

        # --- Draw Panes ---
        self._draw_editor_pane()
        self._draw_sim_pane()
        self._draw_console_pane()
        self._draw_header_footer()

    def _draw_text(self, text, pos, font_key, color, bg_color=None):
        """Helper to draw text using the stored fonts."""
        try:
            surface = self.fonts[font_key].render(text, True, color, bg_color)
            self.surface.blit(surface, pos)
            return surface.get_rect(topleft=pos)
        except Exception as e:
            # Fallback in case font is missing
            print(f"Error rendering text: {e}")
            return pygame.Rect(pos, (10, 10))

    def _draw_pane_border(self, rect, title):
        """Draws a styled border and title for a pane."""
        pygame.draw.rect(self.surface, self.DARK_BLUE, rect, 1)
        # Draw title on top border with adjusted vertical positioning
        title_text = f"--- {title} ---"

        # Default offset keeps label just above the border
        title_offset = -int(8 * self.scale)

        normalized_title = title.upper()
        if normalized_title in {"PAYLOAD.SIM", "README.TXT", "SIMULATION MONITOR"}:
            # Lift file/sim titles slightly to avoid overlapping interior content
            title_offset = -int(12 * self.scale)
        elif normalized_title == "DEBUGGER CONSOLE":
            # Raise console title above the border for separation
            title_offset = -int(16 * self.scale)

        title_rect = self._draw_text(title_text, (rect.x + 10, rect.y + title_offset), "tiny", self.CYAN, self.BLACK)
        # Erase the part of the rect line under the text
        pygame.draw.line(self.surface, self.BLACK, (title_rect.x, rect.y), (title_rect.right, rect.y), 1)

    def _draw_header_footer(self):
        """Draws the main title and keymap."""
        if self.game_state == "SUCCESS" and self.final_summary is not None:
            title = "SIMULACRA_CORE :: RUN COMPLETE"
        else:
            level = self.level_definitions[min(self.current_level - 1, len(self.level_definitions) - 1)]
            title = f"SIMULACRA_CORE :: {level['name']}"

        self._draw_text(title, (int(10 * self.scale), int(10 * self.scale)), "medium", self.CYAN)

        stats_y = int(36 * self.scale)
        label_font = "tiny"
        label_color = self.WHITE

        level_text = f"LEVEL {min(self.current_level, self.max_levels)}/{self.max_levels}"
        timer_text = f"TIMER {self._format_time(self.get_total_elapsed_seconds()) if self.total_timer_start else '--:--.-'}"
        cycles_running = self.total_cycle_count + (self.sim_cycle if self.game_state == "RUNNING" else 0)
        cycles_text = f"TOTAL CYCLES {int(cycles_running)}"
        tcs_text = f"CURRENT TCS {self._format_tcs(self.get_current_tcs()) if self.total_timer_start else '--'}"
        best_text = f"BEST TCS {self._format_tcs(self.best_recorded_tcs)}"

        self._draw_text(level_text, (int(10 * self.scale), stats_y), label_font, label_color)
        self._draw_text(timer_text, (int(160 * self.scale), stats_y), label_font, label_color)
        self._draw_text(cycles_text, (int(320 * self.scale), stats_y), label_font, label_color)
        self._draw_text(tcs_text, (int(470 * self.scale), stats_y), label_font, label_color)
        self._draw_text(best_text, (int(620 * self.scale), stats_y), label_font, label_color)
        
        keymap = "F1:README | F2:PAYLOAD | F5:RUN | F8:RESET RUN | ESC:EXIT"
        if self.game_state == "RUNNING":
            keymap = "SIMULATION RUNNING..."
        elif self.active_file == "README.TXT":
            keymap = "F1:README | F2:PAYLOAD | (Use UP/DOWN to scroll) | ESC:EXIT"

        self._draw_text(keymap, (int(10 * self.scale), self.height - int(30 * self.scale)), "small", self.DARK_CYAN)

    def _draw_editor_pane(self):
        """Draws the code editor pane."""
        self._draw_pane_border(self.editor_pane, self.active_file)
        
        line_height = self.fonts["small"].get_height() + 2
        max_lines_visible = self.editor_pane.height // line_height
        
        # Clamp scroll
        self.editor_scroll_y = max(0, min(len(self.code_lines) - max_lines_visible, self.editor_scroll_y))
        
        start_line = 0
        if self.active_file == "PAYLOAD.SIM":
            # Center scroll on active line
            if self.active_line < self.editor_scroll_y:
                self.editor_scroll_y = self.active_line
            if self.active_line >= self.editor_scroll_y + max_lines_visible:
                self.editor_scroll_y = self.active_line - max_lines_visible + 1
            start_line = self.editor_scroll_y
        elif self.active_file == "README.TXT":
            start_line = self.editor_scroll_y

        y = self.editor_pane.y + 5
        line_num_prefix_width = int(50 * self.scale)

        for i in range(start_line, min(len(self.code_lines), start_line + max_lines_visible)):
            line = self.code_lines[i]
            x = self.editor_pane.x + 5
            
            # --- MODIFIED: Draw Line Number ---
            if self.active_file == "PAYLOAD.SIM":
                line_num = (i + 1) * 10
                num_text = f"{line_num}"
                num_color = self.DARK_CYAN
                if i == self.active_line:
                    num_color = self.CYAN
                # Right-align the line number for a clean look
                num_width = self.fonts["small"].size(num_text)[0]
                self._draw_text(num_text, (x + (line_num_prefix_width - num_width - 5), y), "small", num_color)
                x += line_num_prefix_width
            
            # --- MODIFIED: Draw Line Content with Syntax Highlighting ---
            content_text = line
            content_x = x

            if content_text.strip().startswith("//"):
                # It's a comment, draw all in DARK_CYAN
                self._draw_text(content_text, (content_x, y), "small", self.DARK_CYAN)
            else:
                parts = content_text.split(" ", 1)
                cmd = parts[0].upper()
                
                if cmd in ["MOV", "WAIT", "GOTO"]:
                    # Draw Command
                    cmd_rect = self._draw_text(parts[0] + (" " if len(parts) > 1 else ""), (content_x, y), "small", self.CYAN)
                    # Draw Arguments
                    if len(parts) > 1:
                        self._draw_text(parts[1], (cmd_rect.right, y), "small", self.WHITE)
                else:
                    # Not a known command, just draw as white
                    self._draw_text(content_text, (content_x, y), "small", self.WHITE)

            # --- MODIFIED: Draw Cursor ---
            if self.game_state == "EDITING" and i == self.active_line and self.active_file == "PAYLOAD.SIM":
                # Blinking cursor
                if pygame.time.get_ticks() % 1000 < 500:
                    cursor_text_before = content_text[:self.cursor_pos]
                    cursor_x = content_x + self.fonts["small"].size(cursor_text_before)[0]
                    pygame.draw.rect(self.surface, self.CYAN, (cursor_x, y, 2, line_height))
            
            y += line_height

    def _draw_sim_pane(self):
        """Draws the simulation monitor and leaderboard."""
        if self.leaderboard_visible or self.game_state == "SUCCESS":
            self._draw_leaderboard_pane()
            return

        self._draw_pane_border(self.sim_pane, "SIMULATION MONITOR")
        
        # --- Draw Grid ---
        # Calculate cell size to fit pane
        cell_w = (self.sim_pane.width - int(10*self.scale)) // self.grid_size_x
        cell_h = (self.sim_pane.height - int(10*self.scale)) // self.grid_size_y
        cell_size = min(cell_w, cell_h) - int(8 * self.scale) # Padded
        
        # Center the grid
        offset_x = self.sim_pane.x + (self.sim_pane.width - (cell_size * self.grid_size_x) - (int(4*self.scale) * (self.grid_size_x-1))) // 2
        offset_y = self.sim_pane.y + (self.sim_pane.height - (cell_size * self.grid_size_y) - (int(4*self.scale) * (self.grid_size_y-1))) // 2
        
        cell_gap = cell_size + int(4 * self.scale)

        for y, row in enumerate(self.grid_map):
            for x, cell in enumerate(row):
                px = offset_x + (x * cell_gap)
                py = offset_y + (y * cell_gap)
                rect = pygame.Rect(px, py, cell_size, cell_size)
                
                if cell == 1: # Wall
                    pygame.draw.rect(self.surface, self.DARK_BLUE, rect)
                    self._draw_text("#", (px + cell_size//3, py + cell_size//4), "medium", self.CYAN)
                elif cell == 2: # End
                    pygame.draw.rect(self.surface, self.DARK_BLUE, rect, 1)
                    self._draw_text("[E]", (px + cell_size//4, py + cell_size//4), "medium", self.GREEN)
                else: # Empty
                    pygame.draw.rect(self.surface, self.DARK_BLUE, rect, 1)

        # --- Draw Packets ---
        # Warden [W]
        wx = offset_x + (self.sim_warden_pos[0] * cell_gap)
        wy = offset_y + (self.sim_warden_pos[1] * cell_gap)
        w_rect = pygame.Rect(wx, wy, cell_size, cell_size)
        pygame.draw.rect(self.surface, self.RED, w_rect)
        self._draw_text("[W]", (wx + cell_size//4, wy + cell_size//4), "medium", self.BLACK)

        # Player [S]
        px = offset_x + (self.sim_player_pos[0] * cell_gap)
        py = offset_y + (self.sim_player_pos[1] * cell_gap)
        p_rect = pygame.Rect(px, py, cell_size, cell_size)
        pygame.draw.rect(self.surface, self.CYAN, p_rect)
        self._draw_text("[S]", (px + cell_size//4, py + cell_size//4), "medium", self.BLACK)
        
        # --- Draw Status Overlay ---
        if self.game_state == "FAILED":
            overlay = pygame.Surface((self.sim_pane.width, self.sim_pane.height), pygame.SRCALPHA)
            overlay.fill((139, 0, 0, 180)) # Dark red tint
            self.surface.blit(overlay, self.sim_pane.topleft)
            self._draw_text("TRACE COMPLETE", (self.sim_pane.centerx - int(100*self.scale), self.sim_pane.centery - int(20*self.scale)), "large", self.RED)

    def _draw_leaderboard_pane(self):
        """Draws the leaderboard on success."""
        header_rect = self._draw_pane_border(self.sim_pane, "GLOBAL LEADERBOARD: TCS")

        column_start_y = header_rect.bottom + int(8 * self.scale)
        if self.final_summary:
            summary = self.final_summary
            best_value = summary.get("best_tcs")
            best_text = f"BEST TCS: {self._format_tcs(best_value)}" if best_value is not None else ""
            self._draw_text(
                f"FINAL RUN - TIME {self._format_time(summary['time'])} | CYCLES {int(summary['cycles'])} | TCS {summary['tcs']:.2f}",
                (self.sim_pane.x + int(20 * self.scale), self.sim_pane.y + int(22 * self.scale)),
                "small",
                self.CYAN
            )
            if best_text:
                self._draw_text(
                    best_text,
                    (self.sim_pane.x + int(20 * self.scale), self.sim_pane.y + int(22 * self.scale) + int(18 * self.scale)),
                    "small",
                    self.DARK_CYAN
                )
            column_start_y = self.sim_pane.y + int(22 * self.scale) + int(18 * self.scale) + int(22 * self.scale)

        x_rank = self.sim_pane.x + int(20 * self.scale)
        x_name = self.sim_pane.x + int(70 * self.scale)
        x_time = self.sim_pane.x + int(220 * self.scale)
        x_cycles = self.sim_pane.x + int(360 * self.scale)
        x_tcs = self.sim_pane.x + int(480 * self.scale)

        self._draw_text("#", (x_rank, column_start_y), "small", self.DARK_CYAN)
        self._draw_text("HANDLE", (x_name, column_start_y), "small", self.DARK_CYAN)
        self._draw_text("TIME", (x_time, column_start_y), "small", self.DARK_CYAN)
        self._draw_text("CYC", (x_cycles, column_start_y), "small", self.DARK_CYAN)
        self._draw_text("TCS", (x_tcs, column_start_y), "small", self.DARK_CYAN)
        y = column_start_y + int(26 * self.scale)

        for index, entry in enumerate(self.leaderboard[:10], start=1):
            name = entry.get("username", "?")
            time_val = self._format_time(entry.get("time", 0.0))
            cycles_val = int(entry.get("cycles", 0))
            tcs_val = entry.get("tcs", 0.0)
            color = self.CYAN if name == self.player_username else self.WHITE

            self._draw_text(str(index), (x_rank, y), "small", color)
            self._draw_text(name, (x_name, y), "small", color)
            self._draw_text(time_val, (x_time, y), "small", color)
            self._draw_text(str(cycles_val), (x_cycles, y), "small", color)
            self._draw_text(f"{tcs_val:.2f}", (x_tcs, y), "small", color)

            y += int(26 * self.scale)

    def _draw_console_pane(self):
        """Draws the debugger console pane."""
        self._draw_pane_border(self.console_pane, "DEBUGGER CONSOLE")
        
        line_height = self.fonts["tiny"].get_height()
        max_lines = self.console_pane.height // line_height
        
        y = self.console_pane.bottom - line_height - int(6 * self.scale)
        
        # Draw logs from the bottom up
        for line in reversed(self.debug_log[-max_lines:]):
            color = self.WHITE
            if "ERROR" in line or "FAILED" in line or "COLLISION" in line:
                color = self.RED
            elif "SUCCESS" in line or "DELIVERED" in line:
                color = self.GREEN
            elif line.startswith("CYCLE"):
                color = self.YELLOW
            elif line.startswith("GLYPHIS") or line.startswith("F5") or line.startswith("F8"):
                color = self.CYAN
                
            self._draw_text(line, (self.console_pane.x + int(8 * self.scale), y), "tiny", color)
            y -= line_height
            if y < self.console_pane.y + int(8 * self.scale):
                break


# -----------------------------------------------------------------------------
# Standalone test runner (if you want to run this file directly)
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    pygame.init()

    # --- Setup a test environment ---
    SCREEN_WIDTH = 1000
    SCREEN_HEIGHT = 700
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("SIMULACRA_CORE Standalone Test")

    # --- Create mock fonts and scale ---
    try:
        # Import get_data_path helper
        import sys
        import os
        
        def get_data_path(*path_parts):
            """Helper to get data path - works for both dev and built exe"""
            if getattr(sys, 'frozen', False):
                base_path = sys._MEIPASS
            else:
                script_dir = os.path.dirname(os.path.abspath(__file__))
                project_root = os.path.dirname(script_dir)  # Go up from games to project root
                base_path = project_root
            data_folder = os.path.join(base_path, "Data")
            if os.path.exists(data_folder):
                return os.path.join(data_folder, *path_parts)
            else:
                return os.path.join(base_path, *path_parts)
        
        try:
            font_path = get_data_path("Retro Gaming.ttf")
            test_fonts = {
                "large": pygame.font.Font(font_path, 30),
                "medium": pygame.font.Font(font_path, 22),
                "small": pygame.font.Font(font_path, 16),
                "tiny": pygame.font.Font(font_path, 12)
            }
        except:
            test_fonts = {
                "large": pygame.font.Font("Retro Gaming.ttf", 30),
                "medium": pygame.font.Font("Retro Gaming.ttf", 22),
                "small": pygame.font.Font("Retro Gaming.ttf", 16),
                "tiny": pygame.font.Font("Retro Gaming.ttf", 12)
            }
        test_scale = 1.0
    except:
        print("Retro Gaming.ttf not found. Using default font.")
        test_fonts = {
            "large": pygame.font.Font(None, 30),
            "medium": pygame.font.Font(None, 22),
            "small": pygame.font.Font(None, 16),
            "tiny": pygame.font.Font(None, 12)
        }
        test_scale = 1.0

    # --- Instantiate the game ---
    # We pass the main screen as the surface
    game = SimulacraCoreGame(screen, test_fonts, test_scale, "test_player", best_tcs=None)

    clock = pygame.time.Clock()
    running = True

    while running:
        # --- Event Loop ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if game.handle_event(event) == "EXIT":
                    running = False
        
        # --- Draw Game ---
        game.draw()

        # --- Update Display ---
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()