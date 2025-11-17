#!/usr/bin/env python3
"""
DEBUGGER.BAS - A BBS Game for GlyphisIO
========================================

A retro BASIC debugging game where players must fix corrupted code
to extract an access token.

INTEGRATION WITH MAIN BBS:
--------------------------
This file should be called from main.py when the player selects the 
DEBUGGER.BAS game from the Games menu.

To integrate into main.py:
1. Import this file: `import debugger_game`
2. When player selects the game, call: `debugger_game.run_debugger_game()`
3. The function returns a dict with:
   {
     'completed': True/False,
     'token': 'GPGLPH' or None,
     'score': 87,
     'time': 263 (seconds),
     'edits': 4
   }
4. If completed=True and token is not None, grant the token to player inventory
5. Save completion stats for leaderboard

The game runs in its own pygame window and returns control when done.
"""

import pygame
import sys
import time
import random
import re
import math
from datetime import datetime

# Initialize Pygame
pygame.init()

# Constants
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 700
BLACK = (0, 0, 0)
DARK_GRAY = (20, 20, 30)
CYAN = (0, 255, 255)
DARK_CYAN = (0, 180, 180)
GREEN = (0, 255, 0)
DARK_GREEN = (0, 180, 0)
RED = (255, 100, 100)
YELLOW = (255, 255, 100)
WHITE = (255, 255, 255)
BLUE = (100, 150, 255)

# Fonts
FONT_MONO = None
FONT_MONO_SMALL = None
FONT_MONO_TINY = None

def init_fonts():
    """Initialize fonts for the game"""
    global FONT_MONO, FONT_MONO_SMALL, FONT_MONO_TINY
    
    # Try to load a monospace font
    font_names = ['Courier New', 'Courier', 'Monaco', 'Consolas', 'monospace']
    for name in font_names:
        try:
            FONT_MONO = pygame.font.SysFont(name, 16)
            FONT_MONO_SMALL = pygame.font.SysFont(name, 14)
            FONT_MONO_TINY = pygame.font.SysFont(name, 12)
            break
        except:
            continue
    
    if not FONT_MONO:
        FONT_MONO = pygame.font.Font(None, 18)
        FONT_MONO_SMALL = pygame.font.Font(None, 16)
        FONT_MONO_TINY = pygame.font.Font(None, 14)


class BASICInterpreter:
    """A simple BASIC interpreter for running the debugger program"""
    
    def __init__(self, output_callback=None, graphics_callback=None):
        self.lines = {}
        self.variables = {}
        self.arrays = {}
        self.pc = 0  # Program counter
        self.stack = []  # For FOR loops and GOSUB
        self.output = []
        self.output_callback = output_callback
        self.graphics_callback = graphics_callback
        self.running = False
        self.error = None
        self.graphics_commands = []
        
    def load_program(self, code_lines):
        """Load BASIC program from list of lines"""
        self.lines = {}
        for line in code_lines:
            line = line.strip()
            if not line:
                continue
            
            # Parse line number
            match = re.match(r'^(\d+)\s+(.*)$', line)
            if match:
                line_num = int(match.group(1))
                code = match.group(2)
                self.lines[line_num] = code
    
    def get_line_numbers(self):
        """Return sorted list of line numbers"""
        return sorted(self.lines.keys())
    
    def execute(self):
        """Execute the BASIC program"""
        self.variables = {}
        self.arrays = {}
        self.stack = []
        self.output = []
        self.error = None
        self.running = True
        self.graphics_commands = []
        
        line_numbers = self.get_line_numbers()
        if not line_numbers:
            self.error = "No program loaded"
            return False
        
        self.pc = 0
        
        try:
            while self.running and self.pc < len(line_numbers):
                line_num = line_numbers[self.pc]
                code = self.lines[line_num]
                
                if not self.execute_line(line_num, code):
                    return False
                
                self.pc += 1
                
            return True
            
        except Exception as e:
            self.error = f"Runtime error: {str(e)}"
            return False
    
    def execute_line(self, line_num, code):
        """Execute a single line of BASIC code"""
        code = code.strip()
        
        if not code:
            return True
        
        # REM - Comment
        if code.upper().startswith('REM'):
            return True
        
        # DIM - Dimension array
        if code.upper().startswith('DIM '):
            return self.cmd_dim(code[4:])
        
        # FOR - Start loop (check before LET because FOR contains '=')
        if code.upper().startswith('FOR '):
            return self.cmd_for(line_num, code[4:])
        
        # NEXT - End loop
        if code.upper().startswith('NEXT'):
            return self.cmd_next(line_num, code[4:].strip())
        
        # LET - Assignment (LET is optional)
        if code.upper().startswith('LET '):
            return self.cmd_let(code[4:])
        elif '=' in code and not any(op in code.split('=')[0] for op in ['<', '>', '=']):
            return self.cmd_let(code)
        
        # IF - Conditional
        if code.upper().startswith('IF '):
            return self.cmd_if(code[3:])
        
        # GOTO - Jump
        if code.upper().startswith('GOTO '):
            return self.cmd_goto(code[5:])
        
        # CLS - Clear screen
        if code.upper() == 'CLS':
            return self.cmd_cls()
        
        # CIRCLE - Draw circle
        if code.upper().startswith('CIRCLE '):
            return self.cmd_circle(code[7:])
        
        # LINE - Draw line
        if code.upper().startswith('LINE '):
            return self.cmd_line(code[5:])
        
        # LOCATE - Position cursor
        if code.upper().startswith('LOCATE '):
            return self.cmd_locate(code[7:])
        
        # PRINT - Output
        if code.upper().startswith('PRINT '):
            return self.cmd_print(code[6:])
        
        # SLEEP - Delay
        if code.upper().startswith('SLEEP '):
            return self.cmd_sleep(code[6:])
        
        # END - Stop execution
        if code.upper() == 'END':
            self.running = False
            return True
        
        # If we get here, unknown command
        self.error = f"Line {line_num}: Unknown command"
        return False
    
    def evaluate(self, expr):
        """Evaluate an expression"""
        expr = expr.strip()
        
        # Handle string literals
        if expr.startswith('"') and expr.endswith('"'):
            return expr[1:-1]
        
        # Handle CHR$ function
        if 'CHR$' in expr.upper():
            expr = self.handle_chr(expr)
        
        # Handle RND function
        if 'RND' in expr.upper():
            expr = self.handle_rnd(expr)
        
        # Handle INT and MOD functions
        if 'INT' in expr.upper() or 'MOD' in expr.upper():
            expr = self.handle_functions(expr)
        
        # Replace variables with values
        for var_name in self.variables:
            if var_name in expr:
                val = self.variables[var_name]
                if isinstance(val, str):
                    expr = expr.replace(var_name, f'"{val}"')
                else:
                    expr = expr.replace(var_name, str(val))
        
        # Handle array access
        expr = self.handle_arrays(expr)
        
        try:
            # Evaluate the expression
            result = eval(expr)
            return result
        except:
            return 0
    
    def handle_chr(self, expr):
        """Handle CHR$ function"""
        pattern = r'CHR\$\(([^)]+)\)'
        
        def replace_chr(match):
            val = self.evaluate(match.group(1))
            return f'"{chr(int(val))}"'
        
        return re.sub(pattern, replace_chr, expr, flags=re.IGNORECASE)
    
    def handle_rnd(self, expr):
        """Handle RND function"""
        pattern = r'RND\(([^)]+)\)'
        
        def replace_rnd(match):
            max_val = self.evaluate(match.group(1))
            return str(random.randint(0, int(max_val)))
        
        return re.sub(pattern, replace_rnd, expr, flags=re.IGNORECASE)
    
    def handle_functions(self, expr):
        """Handle INT and MOD functions"""
        # INT function
        pattern_int = r'INT\(([^)]+)\)'
        def replace_int(match):
            val = self.evaluate(match.group(1))
            return str(int(float(val)))
        expr = re.sub(pattern_int, replace_int, expr, flags=re.IGNORECASE)
        
        # MOD operator (as function or infix)
        # Handle "X MOD Y" as "X % Y"
        expr = re.sub(r'(\d+)\s+MOD\s+(\d+)', r'(\1 % \2)', expr, flags=re.IGNORECASE)
        
        return expr
    
    def handle_arrays(self, expr):
        """Replace array access with values"""
        pattern = r'(\w+)\(([^)]+)\)'
        
        def replace_array(match):
            arr_name = match.group(1)
            if arr_name.upper() in ['CHR', 'RND', 'INT', 'MOD']:
                return match.group(0)
            
            indices = match.group(2)
            if ',' in indices:
                idx_parts = [self.evaluate(p.strip()) for p in indices.split(',')]
                key = tuple([arr_name] + [int(i) for i in idx_parts])
            else:
                idx = self.evaluate(indices)
                key = (arr_name, int(idx))
            
            if key in self.arrays:
                val = self.arrays[key]
                if isinstance(val, str):
                    return f'"{val}"'
                return str(val)
            return '0'
        
        return re.sub(pattern, replace_array, expr)
    
    def cmd_dim(self, args):
        """DIM command - dimension an array"""
        # Parse: ARRAY(size) or ARRAY(size1,size2)
        match = re.match(r'(\w+)\(([^)]+)\)', args)
        if not match:
            self.error = "Invalid DIM syntax"
            return False
        
        arr_name = match.group(1)
        sizes = [int(self.evaluate(s.strip())) for s in match.group(2).split(',')]
        
        # Initialize array (just track the dimensions, we'll create entries as needed)
        self.variables[f'{arr_name}_dims'] = sizes
        return True
    
    def cmd_let(self, args):
        """LET command - assignment"""
        if '=' not in args:
            self.error = "Invalid LET syntax"
            return False
        
        parts = args.split('=', 1)
        target = parts[0].strip()
        value = self.evaluate(parts[1].strip())
        
        # Check if it's an array assignment
        if '(' in target:
            match = re.match(r'(\w+)\(([^)]+)\)', target)
            if match:
                arr_name = match.group(1)
                indices = match.group(2)
                
                if ',' in indices:
                    idx_parts = [int(self.evaluate(p.strip())) for p in indices.split(',')]
                    key = tuple([arr_name] + idx_parts)
                else:
                    idx = int(self.evaluate(indices))
                    key = (arr_name, idx)
                
                self.arrays[key] = value
                return True
        
        # Regular variable
        self.variables[target] = value
        return True
    
    def cmd_for(self, line_num, args):
        """FOR command - start loop"""
        # Parse: var=start TO end
        # Use non-greedy match for start value so it doesn't consume the space before TO
        match = re.match(r'(\w+)\s*=\s*(.+?)\s+TO\s+(.+)', args, re.IGNORECASE)
        if not match:
            self.error = f"Line {line_num}: Invalid FOR syntax: {args}"
            return False
        
        var = match.group(1)
        start = int(self.evaluate(match.group(2)))
        end = int(self.evaluate(match.group(3)))
        
        self.variables[var] = start
        self.stack.append({
            'type': 'FOR',
            'var': var,
            'end': end,
            'line': self.pc
        })
        return True
    
    def cmd_next(self, line_num, var_name):
        """NEXT command - end loop"""
        if not self.stack:
            self.error = f"Line {line_num}: NEXT without FOR"
            return False
        
        loop = self.stack[-1]
        if loop['type'] != 'FOR':
            self.error = f"Line {line_num}: NEXT without FOR"
            return False
        
        # Check variable name matches (if provided)
        if var_name and var_name.upper() != loop['var'].upper():
            self.error = f"Line {line_num}: NEXT variable mismatch (got '{var_name}', expected '{loop['var']}')"
            return False
        
        # Increment loop variable
        self.variables[loop['var']] += 1
        
        # Check if loop should continue
        if self.variables[loop['var']] <= loop['end']:
            # Jump back to the line after FOR (loop['line'] + 1)
            # But since main loop will increment PC after this, we set to loop['line']
            # so after increment it becomes loop['line'] + 1
            self.pc = loop['line']
        else:
            self.stack.pop()
        
        return True
    
    def cmd_if(self, args):
        """IF command - conditional"""
        # Parse: condition THEN action
        if 'THEN' not in args.upper():
            self.error = "Invalid IF syntax"
            return False
        
        parts = re.split(r'\s+THEN\s+', args, flags=re.IGNORECASE)
        condition = parts[0].strip()
        action = parts[1].strip()
        
        # Evaluate condition
        result = self.evaluate_condition(condition)
        
        if result:
            # Execute the THEN clause
            if action.upper().startswith('GOTO '):
                return self.cmd_goto(action[5:])
            else:
                return self.execute_line(-1, action)
        
        return True
    
    def evaluate_condition(self, condition):
        """Evaluate a boolean condition"""
        # Check for invalid operators first (common bugs)
        if '=>' in condition:
            # This is a bug - should be >=
            # We'll let it fail naturally by not matching any operator
            return False
        
        # Handle different comparison operators (order matters!)
        for op in ['<=', '>=', '<>', '!=', '==', '=', '<', '>']:
            if op in condition:
                parts = condition.split(op, 1)
                left = self.evaluate(parts[0].strip())
                right = self.evaluate(parts[1].strip())
                
                if op == '=' or op == '==':
                    return left == right
                elif op == '<>':
                    return left != right
                elif op == '!=':
                    return left != right
                elif op == '<':
                    return left < right
                elif op == '>':
                    return left > right
                elif op == '<=':
                    return left <= right
                elif op == '>=':
                    return left >= right
                break
        
        return False
    
    def cmd_goto(self, line_num_str):
        """GOTO command - jump to line"""
        target = int(self.evaluate(line_num_str.strip()))
        line_numbers = self.get_line_numbers()
        
        try:
            self.pc = line_numbers.index(target)
            return True
        except ValueError:
            self.error = f"Line {target} not found"
            return False
    
    def cmd_cls(self):
        """CLS command - clear screen"""
        self.graphics_commands.append({'cmd': 'cls'})
        if self.graphics_callback:
            self.graphics_callback('cls', {})
        return True
    
    def cmd_circle(self, args):
        """CIRCLE command - draw circle"""
        # Parse: NODE(x,y),radius,color
        # Simplified: just extract the array access and draw
        self.graphics_commands.append({'cmd': 'circle', 'args': args})
        if self.graphics_callback:
            self.graphics_callback('circle', args)
        return True
    
    def cmd_line(self, args):
        """LINE command - draw line"""
        self.graphics_commands.append({'cmd': 'line', 'args': args})
        if self.graphics_callback:
            self.graphics_callback('line', args)
        return True
    
    def cmd_locate(self, args):
        """LOCATE command - position cursor"""
        # Not implemented for graphics mode
        return True
    
    def cmd_print(self, args):
        """PRINT command - output text"""
        # Parse the print arguments
        parts = args.split(';')
        output = ""
        
        for part in parts:
            part = part.strip()
            val = self.evaluate(part)
            output += str(val)
        
        self.output.append(output)
        if self.output_callback:
            self.output_callback(output)
        return True
    
    def cmd_sleep(self, args):
        """SLEEP command - delay"""
        # We'll handle this in the main game loop
        return True


class DebuggerGame:
    """Main game class for the DEBUGGER.BAS challenge"""
    
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("DEBUGGER.BAS - GlyphisIO BBS")
        self.clock = pygame.time.Clock()
        
        init_fonts()
        
        # Game state
        self.state = 'editor'  # editor, running, complete
        self.start_time = time.time()
        self.edits_made = 0
        self.completion_time = 0
        
        # Code editor
        self.code_lines = self.get_initial_buggy_code()
        self.original_code = self.code_lines.copy()
        self.current_line = 0
        self.scroll_offset = 0
        self.edit_mode = False
        self.edit_buffer = ""
        self.edit_line_num = 0
        
        # BASIC interpreter
        self.interpreter = BASICInterpreter(
            output_callback=self.handle_output,
            graphics_callback=self.handle_graphics
        )
        
        # Program output
        self.output_text = []
        self.output_graphics = []
        self.program_running = False
        self.run_step = 0
        self.animation_frame = 0
        
        # Help screen
        self.show_help = False
        
        # Command input
        self.command_input = ""
        self.status_message = "Type HELP for instructions, RUN to execute, EDIT <line> to modify"
        self.error_message = ""
        
        # For visualization
        self.nodes = []
        self.trace_progress = 0
        self.trace_complete = False
        self.extracted_token = None
        
    def get_initial_buggy_code(self):
        """Return the initial buggy BASIC program"""
        return [
            "10 REM NETWORK TRACE SIMULATOR",
            "20 REM BY: GLYPHIS",
            "30 DIM NODE(10,2)",
            "40 LET TRACE=0",
            "50 LET SPEED=5",
            "60 REM INIT NETWORK",
            "70 FOR I=1 TO 10",
            "80   LET NODE(I,0)=RND(400)+50",
            "90   LET NODE(I,1)=RND(300)+50",
            "100 NEXT I",
            "110 REM MAIN LOOP",
            "120 CLS",
            "130 FOR I=1 TO 10",
            "140   CIRCLE NODE(I,0),NODE(I,1),8,2",
            "150 NEXT I",
            "160 REM DRAW CONNECTIONS",
            "170 FOR I=1 TO 9",
            "180   LINE NODE(I,0),NODE(I,1),NODE(I+1,0),NODE(I+1,1),1",
            "190 NEXT",  # BUG #1: Missing loop variable (should be "NEXT I")
            "200 REM TRACE PROGRESS",
            "210 LET TRACE=TRACE+SPEED",
            "220 IF TRACE=>100 THEN GOTO 260",  # BUG #2: Wrong operator (=> should be >=)
            "230 SLEEP 0.1",
            "240 GOTO 120",
            "250 REM TRACE COMPLETE",
            "260 CLS",
            "270 PRINT \"TRACE COMPLETE\"",
            "280 PRINT \"TARGET LOCATED\"",
            "290 REM DECODE COORDINATES",
            "300 LET X=NODE(5,0)",
            "310 LET Y=NODE(5,1)",
            "320 PRINT \"COORDS: \";X;\",\";Y",
            "330 PRINT \"ACCESS TOKEN: \";",
            "340 LET C1=CHR$(71)",  # BUG #3: Token should be constructed from node data
            "350 LET C2=CHR$(80)",  # These are hard-coded when they should derive from X,Y
            "360 PRINT C1;C2;\"GLPH\"",
            "370 END",
        ]
    
    def handle_output(self, text):
        """Callback for PRINT commands"""
        self.output_text.append(text)
    
    def handle_graphics(self, cmd, args):
        """Callback for graphics commands"""
        self.output_graphics.append({'cmd': cmd, 'args': args})
    
    def handle_events(self):
        """Handle pygame events"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            
            if event.type == pygame.KEYDOWN:
                if self.edit_mode:
                    self.handle_edit_input(event)
                else:
                    self.handle_command_input(event)
        
        return True
    
    def handle_edit_input(self, event):
        """Handle keyboard input while editing a line"""
        if event.key == pygame.K_RETURN:
            # Save the edited line
            new_line = f"{self.edit_line_num} {self.edit_buffer}"
            
            # Find and replace the line
            found = False
            for i, line in enumerate(self.code_lines):
                if line.startswith(f"{self.edit_line_num} "):
                    if self.code_lines[i] != new_line:
                        self.code_lines[i] = new_line
                        self.edits_made += 1
                        self.status_message = f"Line {self.edit_line_num} updated. Edits: {self.edits_made}"
                    found = True
                    break
            
            if not found:
                self.code_lines.append(new_line)
                self.code_lines.sort(key=lambda x: int(x.split()[0]))
                self.edits_made += 1
            
            self.edit_mode = False
            self.edit_buffer = ""
            
        elif event.key == pygame.K_ESCAPE:
            self.edit_mode = False
            self.edit_buffer = ""
            self.status_message = "Edit cancelled"
            
        elif event.key == pygame.K_BACKSPACE:
            self.edit_buffer = self.edit_buffer[:-1]
            
        elif event.unicode and event.unicode.isprintable():
            self.edit_buffer += event.unicode
    
    def handle_command_input(self, event):
        """Handle keyboard input for commands"""
        if event.key == pygame.K_RETURN:
            self.process_command(self.command_input)
            self.command_input = ""
            
        elif event.key == pygame.K_BACKSPACE:
            self.command_input = self.command_input[:-1]
            
        elif event.key == pygame.K_ESCAPE:
            return False
            
        elif event.unicode and event.unicode.isprintable():
            self.command_input += event.unicode
    
    def process_command(self, cmd):
        """Process a user command"""
        cmd = cmd.strip().upper()
        
        if not cmd:
            return
        
        if cmd == 'HELP':
            self.show_help = not self.show_help
            self.status_message = "Help toggled"
            
        elif cmd == 'RUN':
            self.run_program()
            
        elif cmd == 'LIST':
            self.scroll_offset = 0
            self.status_message = "Showing full program listing"
            
        elif cmd == 'QUIT' or cmd == 'EXIT':
            pygame.quit()
            sys.exit()
            
        elif cmd.startswith('EDIT '):
            try:
                line_num = int(cmd[5:].strip())
                self.start_edit(line_num)
            except ValueError:
                self.error_message = "Invalid line number"
                
        else:
            self.error_message = f"Unknown command: {cmd}"
    
    def start_edit(self, line_num):
        """Start editing a specific line"""
        # Find the line
        for line in self.code_lines:
            if line.startswith(f"{line_num} "):
                # Extract the code part (after line number)
                self.edit_line_num = line_num
                self.edit_buffer = line[len(str(line_num))+1:]
                self.edit_mode = True
                self.status_message = f"Editing line {line_num}. Press ENTER to save, ESC to cancel"
                return
        
        self.error_message = f"Line {line_num} not found"
    
    def run_program(self):
        """Execute the BASIC program"""
        self.output_text = []
        self.output_graphics = []
        self.error_message = ""
        self.nodes = []
        self.trace_progress = 0
        self.trace_complete = False
        
        # Load program into interpreter
        self.interpreter.load_program(self.code_lines)
        
        # Execute
        self.status_message = "Running program..."
        self.program_running = True
        self.run_step = 0
        self.animation_frame = 0
        
        # Run in a separate "thread" (actually we'll step through it)
        success = self.interpreter.execute()
        
        if not success:
            self.error_message = self.interpreter.error or "Program failed to execute"
            self.program_running = False
        else:
            self.status_message = "Program executed successfully"
            self.check_completion()
    
    def check_completion(self):
        """Check if the program completed successfully and extract token"""
        # Look for the token in the output
        for line in self.output_text:
            # Token should be in format: XX-YYGLPH or similar
            # We need to check if the output contains a valid-looking token
            if 'GLPH' in line.upper():
                # Extract potential token
                parts = line.split()
                for part in parts:
                    if 'GLPH' in part.upper() and len(part) >= 4:
                        self.extracted_token = part
                        self.trace_complete = True
                        self.completion_time = time.time() - self.start_time
                        self.state = 'complete'
                        self.status_message = f"TOKEN EXTRACTED! Time: {self.completion_time:.1f}s, Edits: {self.edits_made}"
                        return
        
        # Check if trace reached 100
        if self.interpreter.variables.get('TRACE', 0) >= 100:
            self.trace_complete = True
    
    def draw(self):
        """Main draw function"""
        self.screen.fill(DARK_GRAY)
        
        # Split screen layout
        left_width = SCREEN_WIDTH // 2 - 10
        right_width = SCREEN_WIDTH // 2 - 10
        
        # Draw code editor (left side)
        self.draw_code_editor(10, 10, left_width, SCREEN_HEIGHT - 100)
        
        # Draw output (right side)
        self.draw_output_panel(SCREEN_WIDTH // 2 + 10, 10, right_width, SCREEN_HEIGHT - 100)
        
        # Draw command/status bar at bottom
        self.draw_status_bar(10, SCREEN_HEIGHT - 80, SCREEN_WIDTH - 20, 70)
        
        # Draw help overlay if active
        if self.show_help:
            self.draw_help_overlay()
        
        pygame.display.flip()
    
    def draw_code_editor(self, x, y, width, height):
        """Draw the code editor panel"""
        # Draw border
        pygame.draw.rect(self.screen, CYAN, (x, y, width, height), 2)
        
        # Draw title
        title = "DEBUGGER.BAS - EDIT MODE"
        title_surf = FONT_MONO.render(title, True, CYAN)
        self.screen.blit(title_surf, (x + 10, y + 5))
        
        # Draw separator line
        pygame.draw.line(self.screen, DARK_CYAN, (x, y + 30), (x + width, y + 30), 1)
        
        # Draw code lines
        line_y = y + 40
        line_height = 20
        visible_lines = (height - 50) // line_height
        
        for i, line in enumerate(self.code_lines[self.scroll_offset:]):
            if i >= visible_lines:
                break
            
            # Highlight if editing this line
            if self.edit_mode and line.startswith(f"{self.edit_line_num} "):
                pygame.draw.rect(self.screen, DARK_CYAN, (x + 5, line_y, width - 10, line_height))
                display_line = f"{self.edit_line_num} {self.edit_buffer}_"
                color = BLACK
            else:
                # Color code the line
                if line.strip().startswith(('REM', '#')):
                    color = DARK_GREEN
                elif 'ERROR' in line.upper() or 'BUG' in line.upper():
                    color = RED
                else:
                    color = GREEN
                display_line = line
            
            line_surf = FONT_MONO_SMALL.render(display_line, True, color)
            self.screen.blit(line_surf, (x + 10, line_y))
            line_y += line_height
        
        # Draw scroll indicator
        if len(self.code_lines) > visible_lines:
            scroll_text = f"[Lines {self.scroll_offset + 1}-{min(self.scroll_offset + visible_lines, len(self.code_lines))} of {len(self.code_lines)}]"
            scroll_surf = FONT_MONO_TINY.render(scroll_text, True, DARK_CYAN)
            self.screen.blit(scroll_surf, (x + width - 200, y + 8))
    
    def draw_output_panel(self, x, y, width, height):
        """Draw the program output panel"""
        # Draw border
        pygame.draw.rect(self.screen, CYAN, (x, y, width, height), 2)
        
        # Draw title
        title = "PROGRAM OUTPUT"
        title_surf = FONT_MONO.render(title, True, CYAN)
        self.screen.blit(title_surf, (x + 10, y + 5))
        
        # Draw separator
        pygame.draw.line(self.screen, DARK_CYAN, (x, y + 30), (x + width, y + 30), 1)
        
        # Draw graphics area
        graphics_area = pygame.Rect(x + 10, y + 40, width - 20, height - 150)
        pygame.draw.rect(self.screen, BLACK, graphics_area)
        
        # Draw visualizations if program has run
        if self.interpreter.variables:
            self.draw_network_visualization(graphics_area)
        
        # Draw text output below graphics
        text_y = graphics_area.bottom + 10
        for line in self.output_text[-5:]:  # Show last 5 lines
            text_surf = FONT_MONO_SMALL.render(line, True, GREEN)
            self.screen.blit(text_surf, (x + 10, text_y))
            text_y += 18
        
        # Draw error if present
        if self.error_message:
            error_surf = FONT_MONO.render(f"ERROR: {self.error_message}", True, RED)
            self.screen.blit(error_surf, (x + 10, y + height - 25))
    
    def draw_network_visualization(self, rect):
        """Draw the network trace visualization"""
        # Get node positions from interpreter
        nodes = []
        for i in range(1, 11):
            x_key = ('NODE', i, 0)
            y_key = ('NODE', i, 1)
            if x_key in self.interpreter.arrays and y_key in self.interpreter.arrays:
                x = int(self.interpreter.arrays[x_key])
                y = int(self.interpreter.arrays[y_key])
                # Scale to fit in graphics area
                scaled_x = int(rect.x + (x / 500.0) * rect.width)
                scaled_y = int(rect.y + (y / 400.0) * rect.height)
                nodes.append((scaled_x, scaled_y))
        
        # Draw connections
        for i in range(len(nodes) - 1):
            pygame.draw.line(self.screen, DARK_CYAN, nodes[i], nodes[i + 1], 2)
        
        # Draw nodes
        for i, (nx, ny) in enumerate(nodes):
            color = CYAN if i == 4 else BLUE  # Highlight node 5 (target)
            pygame.draw.circle(self.screen, color, (nx, ny), 8)
            pygame.draw.circle(self.screen, WHITE, (nx, ny), 8, 1)
        
        # Draw trace progress bar
        trace_val = self.interpreter.variables.get('TRACE', 0)
        bar_width = rect.width - 40
        bar_x = rect.x + 20
        bar_y = rect.bottom - 30
        
        # Background
        pygame.draw.rect(self.screen, DARK_GRAY, (bar_x, bar_y, bar_width, 20))
        
        # Progress
        progress = min(trace_val / 100.0, 1.0)
        pygame.draw.rect(self.screen, GREEN, (bar_x, bar_y, int(bar_width * progress), 20))
        
        # Border
        pygame.draw.rect(self.screen, CYAN, (bar_x, bar_y, bar_width, 20), 2)
        
        # Text
        trace_text = f"TRACE: {int(trace_val)}%"
        trace_surf = FONT_MONO.render(trace_text, True, WHITE)
        self.screen.blit(trace_surf, (bar_x + 5, bar_y + 2))
    
    def draw_status_bar(self, x, y, width, height):
        """Draw the status/command bar"""
        # Draw border
        pygame.draw.rect(self.screen, CYAN, (x, y, width, height), 2)
        
        # Draw status message
        status_surf = FONT_MONO_SMALL.render(self.status_message, True, YELLOW)
        self.screen.blit(status_surf, (x + 10, y + 5))
        
        # Draw stats
        elapsed = time.time() - self.start_time
        stats = f"Time: {elapsed:.1f}s | Edits: {self.edits_made}"
        stats_surf = FONT_MONO_SMALL.render(stats, True, DARK_CYAN)
        self.screen.blit(stats_surf, (x + width - 250, y + 5))
        
        # Draw command prompt
        if not self.edit_mode:
            prompt = f"> {self.command_input}_"
            prompt_surf = FONT_MONO.render(prompt, True, GREEN)
            self.screen.blit(prompt_surf, (x + 10, y + 30))
        
        # Draw completion message if done
        if self.state == 'complete' and self.extracted_token:
            msg = f"★ TOKEN EXTRACTED: {self.extracted_token} ★"
            msg_surf = FONT_MONO.render(msg, True, YELLOW)
            msg_rect = msg_surf.get_rect(center=(x + width // 2, y + 50))
            
            # Draw background
            bg_rect = msg_rect.inflate(20, 10)
            pygame.draw.rect(self.screen, DARK_CYAN, bg_rect)
            pygame.draw.rect(self.screen, CYAN, bg_rect, 2)
            
            self.screen.blit(msg_surf, msg_rect)
    
    def draw_help_overlay(self):
        """Draw the help screen overlay"""
        # Semi-transparent background
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(230)
        overlay.fill(BLACK)
        self.screen.blit(overlay, (0, 0))
        
        # Help box
        box_width = 800
        box_height = 600
        box_x = (SCREEN_WIDTH - box_width) // 2
        box_y = (SCREEN_HEIGHT - box_height) // 2
        
        pygame.draw.rect(self.screen, DARK_GRAY, (box_x, box_y, box_width, box_height))
        pygame.draw.rect(self.screen, CYAN, (box_x, box_y, box_width, box_height), 3)
        
        # Title
        title = "DEBUGGER.BAS - HELP & DOCUMENTATION"
        title_surf = FONT_MONO.render(title, True, CYAN)
        self.screen.blit(title_surf, (box_x + 20, box_y + 15))
        
        pygame.draw.line(self.screen, CYAN, (box_x + 20, box_y + 40), (box_x + box_width - 20, box_y + 40), 2)
        
        # Help text
        help_lines = [
            "",
            "OBJECTIVE:",
            "Fix the corrupted BASIC program to extract an access token.",
            "",
            "COMMANDS:",
            "  RUN          - Execute the program",
            "  EDIT <n>     - Edit line number n",
            "  LIST         - Show full program listing",
            "  HELP         - Toggle this help screen",
            "  QUIT         - Exit the game",
            "",
            "EXPECTED BEHAVIOR:",
            "  1. Initialize 10 network nodes at random positions",
            "  2. Draw nodes as circles connected by lines",
            "  3. Animate a trace progress bar from 0% to 100%",
            "  4. When complete, display coordinates and access token",
            "  5. Token format: [characters]GLPH",
            "",
            "KNOWN BUGS:",
            "  - Program has syntax and logic errors",
            "  - Multiple bugs prevent successful execution",
            "  - Token generation is incorrect",
            "",
            "BASIC SYNTAX REMINDERS:",
            "  FOR var=start TO end ... NEXT var",
            "  IF condition THEN action",
            "  Operators: = (assign), >= <= <> (compare)",
            "",
            "Press HELP again to close this screen.",
        ]
        
        text_y = box_y + 60
        for line in help_lines:
            if line.startswith('  '):
                color = DARK_CYAN
            elif line.isupper() and line.endswith(':'):
                color = YELLOW
            else:
                color = GREEN
            
            line_surf = FONT_MONO_SMALL.render(line, True, color)
            self.screen.blit(line_surf, (box_x + 30, text_y))
            text_y += 20
    
    def run(self):
        """Main game loop"""
        running = True
        
        while running:
            running = self.handle_events()
            self.draw()
            self.clock.tick(60)
            
            # Check for completion
            if self.state == 'complete':
                # Wait a bit then exit
                pygame.time.delay(100)
        
        # Return completion stats
        return {
            'completed': self.state == 'complete',
            'token': self.extracted_token,
            'score': self.calculate_score(),
            'time': self.completion_time,
            'edits': self.edits_made
        }
    
    def calculate_score(self):
        """Calculate efficiency score"""
        if self.state != 'complete':
            return 0
        
        # Optimal solution: 2 edits in under 2 minutes
        optimal_edits = 2
        optimal_time = 120
        
        # Score based on edits (50 points)
        edit_score = max(0, 50 - (self.edits_made - optimal_edits) * 10)
        
        # Score based on time (50 points)
        time_score = max(0, 50 - (self.completion_time - optimal_time) / 10)
        
        return int(edit_score + time_score)


def run_debugger_game():
    """
    Entry point for the game - call this from main.py
    Returns completion stats
    """
    game = DebuggerGame()
    result = game.run()
    pygame.quit()
    return result


# For testing standalone
if __name__ == "__main__":
    result = run_debugger_game()
    print("\n" + "=" * 60)
    print("GAME RESULTS")
    print("=" * 60)
    print(f"Completed: {result['completed']}")
    print(f"Token: {result['token']}")
    print(f"Score: {result['score']}/100")
    print(f"Time: {result['time']:.1f} seconds")
    print(f"Edits: {result['edits']}")
    print("=" * 60)
