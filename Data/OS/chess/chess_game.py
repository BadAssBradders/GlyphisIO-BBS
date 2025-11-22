"""
Chess Game Module
A player vs CPU chess game for OS Mode.
"""

import pygame
import os
import sys
import time
import random
from typing import List, Dict, Tuple, Optional, Callable

try:
    import chess
except ImportError:
    chess = None

# Visual Constants (matching OS_Mode.py)
COLOR_BG_DARK = (20, 20, 40)
COLOR_BG_TITLE = (40, 40, 60)
COLOR_CYAN = (0, 255, 255)
COLOR_GREEN = (0, 255, 0)
COLOR_RED = (255, 0, 0)
COLOR_RED_DARK = (100, 0, 0)
COLOR_WHITE = (255, 255, 255)
COLOR_BLACK = (0, 0, 0)
COLOR_GREY = (128, 128, 128)
COLOR_YELLOW = (255, 255, 0)


# Data path helper - works for both development and built executable
def get_data_path(*path_parts):
    """
    Returns the path to the Data folder, handling both development and built executable scenarios.
    """
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        base_path = sys._MEIPASS
    else:
        # Running as script - go up from OS/chess to Data folder
        script_dir = os.path.dirname(os.path.abspath(__file__))
        os_dir = os.path.dirname(script_dir)  # Go up from chess to OS
        data_folder = os.path.dirname(os_dir)  # Go up from OS to Data folder
        base_path = data_folder
    
    return os.path.join(base_path, *path_parts)


class ChessGame:
    """Chess game for OS Mode Desktop Environment."""
    
    def __init__(self, screen: pygame.Surface, scale: float, desktop_x: int, desktop_y: int, desktop_size: Tuple[int, int],
                 health_monitor_y: int, bbs_x: int, bbs_width: int,
                 get_chess_stats_callback: Optional[Callable] = None,
                 save_chess_stats_callback: Optional[Callable] = None):
        """
        Initialize the chess game.
        
        Args:
            screen: The pygame surface to draw on
            scale: UI scaling factor
            desktop_x: X position of desktop area
            desktop_y: Y position of desktop area
            desktop_size: (width, height) of desktop area
            health_monitor_y: Y position of health monitor (where board should start)
            bbs_x: X position of BBS window
            bbs_width: Width of BBS window
            get_chess_stats_callback: Function to get chess stats from user profile
            save_chess_stats_callback: Function to save chess stats to user profile
        """
        self.screen = screen
        self.scale = scale
        self.desktop_x = desktop_x
        self.desktop_y = desktop_y
        self.desktop_size = desktop_size
        self.health_monitor_y = health_monitor_y
        self.bbs_x = bbs_x
        self.bbs_width = bbs_width
        self.get_chess_stats = get_chess_stats_callback or (lambda: {})
        self.save_chess_stats = save_chess_stats_callback or (lambda stats: None)
        
        # Game state
        self.active = False
        self.phase = "hidden"  # hidden, color_select, playing, game_over
        self.board = None
        self.player_color = chess.WHITE if chess else True
        self.cpu_color = chess.BLACK if chess else False
        self.selected_square = None
        self.valid_targets: List[int] = []
        self.last_move = None
        self.status_message = ""
        self.error_message = None if chess else "python-chess is not installed. Run 'pip install python-chess'."
        
        # Stats
        self.stats = self.get_chess_stats()
        if not self.stats:
            self.stats = {
                "games_played": 0,
                "wins": 0,
                "losses": 0,
                "draws": 0,
                "resignations": 0,
                "last_game_result": None
            }
        
        # Assets
        self.board_surface = None
        self.piece_surfaces: Dict[str, pygame.Surface] = {}
        self.piece_heights: Dict[str, int] = {}  # Store piece heights for bottom anchoring
        self.board_rect = None
        self.board_inner_size = 0
        self.board_border = 0
        self.square_size = 0
        
        # UI (ai_depth now controlled by ai_difficulty)
        self.waiting_for_ai = False
        self.ai_move_delay_start = None
        self.ai_move_delay_duration = 0.0
        self.pending_ai_move = None
        self.color_buttons: Dict[str, pygame.Rect] = {}
        self.color_select_quit_button_rect: Optional[pygame.Rect] = None
        self.close_button_rect: Optional[pygame.Rect] = None
        self.resign_button_rect: Optional[pygame.Rect] = None
        self.wipe_stats_button_rect: Optional[pygame.Rect] = None
        self.exit_button_rect: Optional[pygame.Rect] = None
        
        # Button hover states
        self.hovered_button: Optional[str] = None
        
        # AI thinking terminal
        self.ai_thinking_exposed = True
        self.ai_thinking_log: List[str] = []
        self.ai_terminal_scroll_y = 0
        self.ai_terminal_rect: Optional[pygame.Rect] = None
        self.ai_radio_on_rect: Optional[pygame.Rect] = None
        self.ai_radio_off_rect: Optional[pygame.Rect] = None
        
        # Game features
        self.move_history: List[str] = []  # Store move history in notation
        self.captured_pieces: Dict[str, List[int]] = {"w": [], "b": []}  # Track captured pieces by type
        self.all_legal_moves: List[int] = []  # All legal moves for current position
        self.show_all_legal_moves = True
        
        # Pawn promotion modal
        self.show_promotion_modal = False
        self.promotion_square: Optional[int] = None
        self.promotion_target: Optional[int] = None
        self.promotion_selection = chess.QUEEN  # Default to queen
        self.promotion_modal_ok_rect: Optional[pygame.Rect] = None
        self.promotion_modal_left_arrow_rect: Optional[pygame.Rect] = None
        self.promotion_modal_right_arrow_rect: Optional[pygame.Rect] = None
        self.promotion_pieces = [chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT]
        
        # AI difficulty controls
        self.ai_difficulty = 3  # Depth (1-5)
        self.ai_difficulty_down_rect: Optional[pygame.Rect] = None
        self.ai_difficulty_up_rect: Optional[pygame.Rect] = None
        
        # Modal state
        self.show_exit_modal = False
        self.show_wipe_stats_modal = False
        self.modal_yes_button_rect: Optional[pygame.Rect] = None
        self.modal_no_button_rect: Optional[pygame.Rect] = None
        
        # Load assets
        self._load_assets()
    
    def _load_assets(self):
        """Load chess board and piece assets."""
        chess_dir = get_data_path("OS", "chess")
        board_path = os.path.join(chess_dir, "board.png")
        try:
            board_image = pygame.image.load(board_path).convert_alpha()
            original_size = board_image.get_size()
            scaled_size = (
                int(original_size[0] * self.scale),
                int(original_size[1] * self.scale)
            )
            board_image = pygame.transform.scale(board_image, scaled_size)
            self.board_surface = board_image
            # Board inner measurements (given 490px play area with 56px border)
            self.board_inner_size = int(490 * self.scale)
            self.board_border = max(0, (scaled_size[0] - self.board_inner_size) // 2)
            self.square_size = max(1, self.board_inner_size // 8)
        except Exception as e:
            print(f"Warning: Failed to load chess board image: {e}")
            self.board_surface = None

        if chess is None:
            return

        piece_files = {
            ("w", chess.PAWN): "w-pawn.png",
            ("w", chess.ROOK): "w-rook.png",
            ("w", chess.KNIGHT, "l"): "w-knight-l.png",
            ("w", chess.KNIGHT, "r"): "w-knight-r.png",
            ("w", chess.BISHOP): "w-bishop.png",
            ("w", chess.QUEEN): "w-queen.png",
            ("w", chess.KING): "w-king.png",
            ("b", chess.PAWN): "b-pawn.png",
            ("b", chess.ROOK): "b-rook.png",
            ("b", chess.KNIGHT, "l"): "b-knight-l.png",
            ("b", chess.KNIGHT, "r"): "b-knight-r.png",
            ("b", chess.BISHOP): "b-bishop.png",
            ("b", chess.QUEEN): "b-queen.png",
            ("b", chess.KING): "b-king.png",
        }

        self.piece_surfaces.clear()
        self.piece_heights.clear()
        for key, filename in piece_files.items():
            try:
                piece_path = os.path.join(chess_dir, filename)
                surface = pygame.image.load(piece_path).convert_alpha()
                original_size = surface.get_size()
                target_size = (
                    int(original_size[0] * self.scale),
                    int(original_size[1] * self.scale)
                )
                surface = pygame.transform.smoothscale(surface, target_size)
                if len(key) == 2:
                    color, piece_type = key
                    dict_key = f"{color}_{piece_type}"
                else:
                    color, piece_type, variant = key
                    dict_key = f"{color}_{piece_type}_{variant}"
                self.piece_surfaces[dict_key] = surface
                self.piece_heights[dict_key] = target_size[1]  # Store height for bottom anchoring
            except Exception as e:
                print(f"Warning: Failed to load chess piece {filename}: {e}")
    
    def update_desktop(self, desktop_x: int, desktop_y: int, desktop_size: Tuple[int, int], health_monitor_y: int):
        """Update desktop coordinates and size."""
        self.desktop_x = desktop_x
        self.desktop_y = desktop_y
        self.desktop_size = desktop_size
        self.health_monitor_y = health_monitor_y
    
    def start(self):
        """Start the chess game."""
        if chess is None:
            self.error_message = "python-chess is not installed. Run 'pip install python-chess'."
            return
        # Reload stats from user profile when starting a new game
        self.stats = self.get_chess_stats()
        if not self.stats:
            self.stats = {
                "games_played": 0,
                "wins": 0,
                "losses": 0,
                "draws": 0,
                "resignations": 0,
                "last_game_result": None
            }
        self._load_assets()
        self._reset()
    
    def _reset(self):
        """Reset the game to initial state (returns to color selection)."""
        if chess is None:
            self.active = False
            self.phase = "hidden"
            return
        self.board = chess.Board()
        self.player_color = chess.WHITE
        self.cpu_color = chess.BLACK
        self.selected_square = None
        self.valid_targets = []
        self.last_move = None
        self.status_message = "Choose your color to begin."
        self.phase = "color_select"
        self.active = True
        self.waiting_for_ai = False
        self.ai_move_delay_start = None
        self.ai_move_delay_duration = 0.0
        self.pending_ai_move = None
        # Reset game features
        self.move_history = []
        self.captured_pieces = {"w": [], "b": []}
        self.all_legal_moves = []
        # Close any open modals
        self.show_exit_modal = False
        self.show_wipe_stats_modal = False
        self.show_promotion_modal = False
    
    def _update_stats(self, result: str):
        """Update chess stats after game ends."""
        self.stats["games_played"] = self.stats.get("games_played", 0) + 1
        self.stats["last_game_result"] = result
        if result == "win":
            self.stats["wins"] = self.stats.get("wins", 0) + 1
        elif result == "loss":
            self.stats["losses"] = self.stats.get("losses", 0) + 1
        elif result == "draw":
            self.stats["draws"] = self.stats.get("draws", 0) + 1
        elif result == "resignation":
            self.stats["resignations"] = self.stats.get("resignations", 0) + 1
        self.save_chess_stats(self.stats)
    
    def close(self):
        """Close the chess game."""
        self.active = False
        self.phase = "hidden"
        self.selected_square = None
        self.valid_targets = []
    
    def _square_rect(self, square: int, board_rect: pygame.Rect) -> Optional[pygame.Rect]:
        """Convert a chess square to a pygame Rect."""
        if chess is None or not board_rect or self.board_surface is None:
            return None
        border = self.board_border
        square_size = self.square_size
        if self.player_color == chess.WHITE:
            col = chess.square_file(square)
            row = 7 - chess.square_rank(square)
        else:
            col = 7 - chess.square_file(square)
            row = chess.square_rank(square)
        x = board_rect.x + border + col * square_size
        y = board_rect.y + border + row * square_size
        return pygame.Rect(x, y, square_size, square_size)
    
    def _square_from_pos(self, mouse_x: int, mouse_y: int) -> Optional[int]:
        """Convert mouse position to chess square."""
        if chess is None or not self.board_rect:
            return None
        border = self.board_border
        square_size = self.square_size
        board_inner = pygame.Rect(
            self.board_rect.x + border,
            self.board_rect.y + border,
            square_size * 8,
            square_size * 8
        )
        if not board_inner.collidepoint(mouse_x, mouse_y):
            return None
        col = (mouse_x - board_inner.x) // square_size
        row = (mouse_y - board_inner.y) // square_size
        col = max(0, min(7, int(col)))
        row = max(0, min(7, int(row)))
        if self.player_color == chess.WHITE:
            file_idx = col
            rank_idx = 7 - row
        else:
            file_idx = 7 - col
            rank_idx = row
        return chess.square(file_idx, rank_idx)
    
    def _legal_targets(self, square: int) -> List[int]:
        """Get all legal target squares for a piece on the given square."""
        if chess is None or not self.board:
            return []
        targets = []
        for move in self.board.legal_moves:
            if move.from_square == square:
                targets.append(move.to_square)
        return targets
    
    def _update_all_legal_moves(self):
        """Update the list of all legal moves for the current position."""
        if chess is None or not self.board:
            self.all_legal_moves = []
            return
        self.all_legal_moves = [move.to_square for move in self.board.legal_moves if self.board.turn == self.player_color]
    
    def _make_move(self, move: chess.Move, captured_piece):
        """Make a move and update game state."""
        if chess is None or not self.board:
            return
        
        # Track captured piece
        if captured_piece:
            color = "w" if captured_piece.color == chess.WHITE else "b"
            piece_type = captured_piece.piece_type
            self.captured_pieces[color].append(piece_type)
        
        # Make the move
        self.board.push(move)
        self.last_move = move
        
        # Add to move history in notation
        try:
            move_san = self.board.san(move)
            if self.board.turn == chess.BLACK:  # White just moved
                move_number = len(self.move_history) // 2 + 1
                self.move_history.append(f"{move_number}. {move_san}")
            else:  # Black just moved, append to last entry
                if self.move_history and "." in self.move_history[-1]:
                    self.move_history[-1] += f" {move_san}"
                else:
                    move_number = len(self.move_history) // 2 + 1
                    self.move_history.append(f"{move_number}... {move_san}")
        except:
            # Fallback if SAN notation fails
            self.move_history.append(str(move))
        
        self.selected_square = None
        self.valid_targets = []
        self.status_message = "CPU thinking..." if self.board.turn == self.cpu_color else "Your move."
        self._check_game_over()
        
        if self.phase == "playing" and self.board.turn == self.cpu_color:
            self._trigger_ai_move()
    
    def _trigger_ai_move(self):
        """Trigger the CPU to make a move with a 2-5 second delay."""
        if chess is None or not self.board:
            return
        if self.board.is_game_over():
            self._check_game_over()
            return
        if self.board.turn != self.cpu_color:
            return
        
        # Clear previous thinking log and add header
        self.ai_thinking_log = []
        if self.ai_thinking_exposed:
            self.ai_thinking_log.append("AI Thinking Process:")
            self.ai_thinking_log.append("=" * 30)
        self.ai_terminal_scroll_y = 0
        
        # Calculate the best move immediately but delay execution
        self.ai_depth = self.ai_difficulty
        _, best_move = self._find_best_move(self.board, self.ai_depth, -float("inf"), float("inf"), True)
        if best_move is None:
            try:
                best_move = next(iter(self.board.legal_moves))
            except StopIteration:
                best_move = None
        
        if best_move:
            # Store the move and set delay timer (2-5 seconds)
            self.pending_ai_move = best_move
            self.ai_move_delay_start = time.time()
            self.ai_move_delay_duration = random.uniform(2.0, 5.0)
            self.waiting_for_ai = True
            self.status_message = "CPU thinking..."
            self._update_all_legal_moves()
        else:
            self._check_game_over()
            if self.phase == "playing":
                self.status_message = "Your move."
    
    def _check_ai_move_delay(self):
        """Check if AI move delay has elapsed and execute the move."""
        if not self.waiting_for_ai or self.ai_move_delay_start is None:
            return
        
        elapsed = time.time() - self.ai_move_delay_start
        if elapsed >= self.ai_move_delay_duration:
            # Delay has passed, execute the move
            if self.pending_ai_move and self.board:
                # Track captured piece
                captured = self.board.piece_at(self.pending_ai_move.to_square)
                if captured:
                    color = "w" if captured.color == chess.WHITE else "b"
                    piece_type = captured.piece_type
                    self.captured_pieces[color].append(piece_type)
                
                self.board.push(self.pending_ai_move)
                self.last_move = self.pending_ai_move
                
                # Add to move history
                try:
                    move_san = self.board.san(self.pending_ai_move)
                    if self.board.turn == chess.WHITE:  # Black just moved
                        if self.move_history and "." in self.move_history[-1] and "..." not in self.move_history[-1]:
                            self.move_history[-1] += f" {move_san}"
                        else:
                            move_number = len(self.move_history) // 2 + 1
                            self.move_history.append(f"{move_number}... {move_san}")
                except:
                    self.move_history.append(str(self.pending_ai_move))
                
                self.pending_ai_move = None
                self.waiting_for_ai = False
                self.ai_move_delay_start = None
                self._update_all_legal_moves()
                self._check_game_over()
                if self.phase == "playing":
                    self.status_message = "Your move."
    
    def _check_game_over(self):
        """Check if the game is over and update status."""
        if chess is None or not self.board:
            return
        if self.board.is_game_over():
            if self.board.is_checkmate():
                if self.board.turn == self.player_color:
                    self.status_message = "Checkmate! CPU wins."
                    self._update_stats("loss")
                else:
                    self.status_message = "Checkmate! You win."
                    self._update_stats("win")
            elif self.board.is_stalemate():
                self.status_message = "Stalemate."
                self._update_stats("draw")
            elif self.board.is_insufficient_material():
                self.status_message = "Draw by insufficient material."
                self._update_stats("draw")
            else:
                self.status_message = "Game over."
                self._update_stats("draw")
            self.phase = "game_over"
        else:
            if self.board.turn == self.player_color:
                self.status_message = "Your move."
            else:
                self.status_message = "CPU thinking..."
    
    def _find_best_move(self, board: "chess.Board", depth: int, alpha: float, beta: float, maximizing: bool):
        """Minimax with alpha-beta pruning to find the best move."""
        if chess is None:
            return 0, None
        if depth == 0 or board.is_game_over():
            return self._evaluate_board(board), None

        best_move = None
        if maximizing:
            best_score = -float("inf")
            move_list = list(board.legal_moves)
            analyzed_count = 0
            
            for move in move_list:
                analyzed_count += 1
                # Log move being analyzed (only at top level, limit to first few moves for performance)
                if self.ai_thinking_exposed and depth == self.ai_depth and analyzed_count <= 10:
                    try:
                        move_str = board.san(move)
                    except:
                        move_str = str(move)
                    if len(self.ai_thinking_log) < 40:
                        self.ai_thinking_log.append(f"Analyzing: {move_str}...")
                
                board.push(move)
                score, _ = self._find_best_move(board, depth - 1, alpha, beta, False)
                board.pop()
                
                # Log evaluation result (only at top level, limit to first few moves)
                if self.ai_thinking_exposed and depth == self.ai_depth and analyzed_count <= 10:
                    try:
                        move_str = board.san(move)
                    except:
                        move_str = str(move)
                    score_str = f"{score:.0f}"
                    if len(self.ai_thinking_log) < 40:
                        # Update or add evaluation
                        self.ai_thinking_log.append(f"  -> {move_str}: Score {score_str}")
                
                if score > best_score:
                    best_score = score
                    best_move = move
                alpha = max(alpha, best_score)
                if beta <= alpha:
                    if self.ai_thinking_exposed and depth == self.ai_depth:
                        if len(self.ai_thinking_log) < 50:
                            self.ai_thinking_log.append("  -> Alpha-beta cutoff")
                    break
            
            # Log best move found
            if self.ai_thinking_exposed and depth == self.ai_depth and best_move:
                try:
                    best_move_str = board.san(best_move)
                except:
                    best_move_str = str(best_move)
                if len(self.ai_thinking_log) < 40:
                    self.ai_thinking_log.append("")
                    self.ai_thinking_log.append(f">> Selected: {best_move_str} (Score: {best_score:.0f})")
            
            return best_score, best_move
        else:
            best_score = float("inf")
            for move in board.legal_moves:
                board.push(move)
                score, _ = self._find_best_move(board, depth - 1, alpha, beta, True)
                board.pop()
                
                if score < best_score:
                    best_score = score
                    best_move = move
                beta = min(beta, best_score)
                if beta <= alpha:
                    break
            return best_score, best_move
    
    def _evaluate_board(self, board: "chess.Board") -> float:
        """Evaluate the board position for the CPU."""
        if chess is None:
            return 0
        if board.is_checkmate():
            if board.turn == self.cpu_color:
                return float("-inf")
            else:
                return float("inf")
        if board.is_stalemate():
            return 0
        piece_values = {
            chess.PAWN: 100,
            chess.KNIGHT: 320,
            chess.BISHOP: 330,
            chess.ROOK: 500,
            chess.QUEEN: 900,
            chess.KING: 20000
        }
        score = 0
        for piece_type, value in piece_values.items():
            score += value * len(board.pieces(piece_type, self.cpu_color))
            score -= value * len(board.pieces(piece_type, self.player_color))
        return score
    
    def get_position_evaluation(self) -> float:
        """Get the current position evaluation from player's perspective."""
        if chess is None or not self.board:
            return 0.0
        # Evaluate from player's perspective (negate CPU evaluation)
        eval_score = -self._evaluate_board(self.board)
        # Convert to pawns (divide by 100)
        return eval_score / 100.0
    
    def handle_event(self, event: pygame.event.Event) -> bool:
        """
        Handle pygame events for the chess game.
        Returns True if event was handled, False otherwise.
        """
        if not self.active:
            return False
        
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if self.phase == "playing":
                self.status_message = "Resigned."
                self._update_stats("resignation")
                self.phase = "game_over"
            elif self.phase == "color_select":
                # ESC during color selection closes without resignation
                self.close()
            else:
                self.close()
            return True
        
        # Handle mouse hover for buttons
        if event.type == pygame.MOUSEMOTION:
            mouse_x, mouse_y = event.pos
            self.hovered_button = None
            
            # Check color selection buttons
            if self.phase == "color_select":
                for color, rect in self.color_buttons.items():
                    if rect.collidepoint(mouse_x, mouse_y):
                        self.hovered_button = f"color_{color}"
                        break
                if not self.hovered_button and self.color_select_quit_button_rect and self.color_select_quit_button_rect.collidepoint(mouse_x, mouse_y):
                    self.hovered_button = "quit_color"
            
            # Check other buttons
            if self.resign_button_rect and self.resign_button_rect.collidepoint(mouse_x, mouse_y):
                self.hovered_button = "resign"
            elif self.wipe_stats_button_rect and self.wipe_stats_button_rect.collidepoint(mouse_x, mouse_y):
                self.hovered_button = "wipe_stats"
            elif self.exit_button_rect and self.exit_button_rect.collidepoint(mouse_x, mouse_y):
                self.hovered_button = "exit"
            elif self.ai_radio_on_rect and self.ai_radio_on_rect.collidepoint(mouse_x, mouse_y):
                self.hovered_button = "ai_radio_on"
            elif self.ai_radio_off_rect and self.ai_radio_off_rect.collidepoint(mouse_x, mouse_y):
                self.hovered_button = "ai_radio_off"
            
            # Handle terminal scrolling
            if self.ai_terminal_rect and self.ai_terminal_rect.collidepoint(mouse_x, mouse_y):
                # Mouse wheel scrolling handled separately
                pass
        
        # Handle mouse wheel for terminal scrolling
        if event.type == pygame.MOUSEWHEEL:
            if self.ai_terminal_rect:
                mouse_x, mouse_y = pygame.mouse.get_pos()
                if self.ai_terminal_rect.collidepoint(mouse_x, mouse_y):
                    try:
                        temp_font = pygame.font.Font(None, max(int(17 * self.scale), 11))
                        line_spacing = int(5 * self.scale)  # 5px spacing between lines
                        line_height = temp_font.get_height() + line_spacing
                        scroll_amount = int(event.y * 15 * self.scale)
                        max_scroll = max(0, len(self.ai_thinking_log) * line_height - int(120 * self.scale))
                        self.ai_terminal_scroll_y = max(0, min(max_scroll, self.ai_terminal_scroll_y - scroll_amount))
                    except:
                        pass
        
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_x, mouse_y = event.pos
            
            # Handle AI radio buttons
            if self.ai_radio_on_rect and self.ai_radio_on_rect.collidepoint(mouse_x, mouse_y):
                self.ai_thinking_exposed = True
                return True
            elif self.ai_radio_off_rect and self.ai_radio_off_rect.collidepoint(mouse_x, mouse_y):
                self.ai_thinking_exposed = False
                return True
            
            # Handle modal buttons first
            if self.show_exit_modal:
                if self.modal_yes_button_rect and self.modal_yes_button_rect.collidepoint(mouse_x, mouse_y):
                    # Confirm exit - count as resignation (only shown if 10+ moves)
                    if self.phase == "playing":
                        self._update_stats("resignation")
                    self.close()
                    self.show_exit_modal = False
                    return True
                elif self.modal_no_button_rect and self.modal_no_button_rect.collidepoint(mouse_x, mouse_y):
                    self.show_exit_modal = False
                    return True
                # Don't handle other clicks when modal is open
                return True
            
            if self.show_wipe_stats_modal:
                if self.modal_yes_button_rect and self.modal_yes_button_rect.collidepoint(mouse_x, mouse_y):
                    # Confirm wipe stats
                    self.stats = {
                        "games_played": 0,
                        "wins": 0,
                        "losses": 0,
                        "draws": 0,
                        "resignations": 0,
                        "last_game_result": None
                    }
                    self.save_chess_stats(self.stats)
                    self.show_wipe_stats_modal = False
                    return True
                elif self.modal_no_button_rect and self.modal_no_button_rect.collidepoint(mouse_x, mouse_y):
                    self.show_wipe_stats_modal = False
                    return True
                # Don't handle other clicks when modal is open
                return True
            
            # Handle main buttons
            if self.exit_button_rect and self.exit_button_rect.collidepoint(mouse_x, mouse_y):
                # Check if 10+ moves have been made
                move_count = len(self.board.move_stack) if self.board else 0
                if move_count >= 10:
                    self.show_exit_modal = True
                else:
                    # Less than 10 moves - just quit without resignation
                    self.close()
                return True
            
            if self.wipe_stats_button_rect and self.wipe_stats_button_rect.collidepoint(mouse_x, mouse_y):
                self.show_wipe_stats_modal = True
                return True
            
            if self.resign_button_rect and self.resign_button_rect.collidepoint(mouse_x, mouse_y):
                # Resign and return to color selection
                if self.phase == "playing":
                    self._update_stats("resignation")
                self._reset()
                return True

            if self.phase == "color_select" and hasattr(self, "color_buttons"):
                # Check quit button first
                if self.color_select_quit_button_rect and self.color_select_quit_button_rect.collidepoint(mouse_x, mouse_y):
                    # Quit during color selection - no resignation
                    self.close()
                    return True
                
                # Check color selection buttons
                for color, rect in self.color_buttons.items():
                    if rect.collidepoint(mouse_x, mouse_y):
                        self.player_color = chess.WHITE if color == "white" else chess.BLACK
                        self.cpu_color = not self.player_color
                        self.phase = "playing"
                        self.status_message = "Your move." if self.board.turn == self.player_color else "CPU thinking..."
                        self.selected_square = None
                        self.valid_targets = []
                        if self.board.turn == self.cpu_color:
                            self._trigger_ai_move()
                        return True
                return False

            if self.phase != "playing":
                return False
            
            # Handle promotion modal clicks
            if self.show_promotion_modal:
                if self.promotion_modal_left_arrow_rect and self.promotion_modal_left_arrow_rect.collidepoint(mouse_x, mouse_y):
                    # Cycle left
                    idx = self.promotion_pieces.index(self.promotion_selection)
                    self.promotion_selection = self.promotion_pieces[(idx - 1) % len(self.promotion_pieces)]
                    return True
                elif self.promotion_modal_right_arrow_rect and self.promotion_modal_right_arrow_rect.collidepoint(mouse_x, mouse_y):
                    # Cycle right
                    idx = self.promotion_pieces.index(self.promotion_selection)
                    self.promotion_selection = self.promotion_pieces[(idx + 1) % len(self.promotion_pieces)]
                    return True
                elif self.promotion_modal_ok_rect and self.promotion_modal_ok_rect.collidepoint(mouse_x, mouse_y):
                    # Confirm promotion
                    if self.promotion_square is not None and self.promotion_target is not None:
                        move = chess.Move(self.promotion_square, self.promotion_target, promotion=self.promotion_selection)
                        if move in self.board.legal_moves:
                            captured = self.board.piece_at(self.promotion_target)
                            self._make_move(move, captured)
                    self.show_promotion_modal = False
                    self.promotion_square = None
                    self.promotion_target = None
                    return True
                # Don't handle other clicks when promotion modal is open
                return True
            
            # Handle AI difficulty controls
            if self.ai_difficulty_down_rect and self.ai_difficulty_down_rect.collidepoint(mouse_x, mouse_y):
                old_difficulty = self.ai_difficulty
                self.ai_difficulty = max(1, self.ai_difficulty - 1)
                if old_difficulty != self.ai_difficulty:
                    # Add difficulty change message to terminal
                    difficulty_names = {1: "Easy", 2: "Medium", 3: "Hard", 4: "Expert", 5: "Master"}
                    difficulty_name = difficulty_names.get(self.ai_difficulty, "Unknown")
                    self.ai_thinking_log.append(f"Difficulty {self.ai_difficulty} {difficulty_name}")
                return True
            elif self.ai_difficulty_up_rect and self.ai_difficulty_up_rect.collidepoint(mouse_x, mouse_y):
                old_difficulty = self.ai_difficulty
                self.ai_difficulty = min(5, self.ai_difficulty + 1)
                if old_difficulty != self.ai_difficulty:
                    # Add difficulty change message to terminal
                    difficulty_names = {1: "Easy", 2: "Medium", 3: "Hard", 4: "Expert", 5: "Master"}
                    difficulty_name = difficulty_names.get(self.ai_difficulty, "Unknown")
                    self.ai_thinking_log.append(f"Difficulty {self.ai_difficulty} {difficulty_name}")
                return True

            if self.board_rect and self.board_rect.collidepoint(mouse_x, mouse_y):
                square = self._square_from_pos(mouse_x, mouse_y)
                if square is None:
                    return False
                piece = self.board.piece_at(square)
                if self.selected_square is None:
                    if piece and piece.color == self.player_color and self.board.turn == self.player_color:
                        self.selected_square = square
                        self.valid_targets = self._legal_targets(square)
                        self._update_all_legal_moves()
                    return True

                if piece and piece.color == self.player_color:
                    self.selected_square = square
                    self.valid_targets = self._legal_targets(square)
                    self._update_all_legal_moves()
                    return True

                if square in self.valid_targets:
                    # Check if this is a pawn promotion
                    selected_piece = self.board.piece_at(self.selected_square)
                    is_promotion = (selected_piece and selected_piece.piece_type == chess.PAWN and
                                   ((self.player_color == chess.WHITE and chess.square_rank(square) == 7) or
                                    (self.player_color == chess.BLACK and chess.square_rank(square) == 0)))
                    
                    if is_promotion:
                        # Show promotion modal
                        self.promotion_square = self.selected_square
                        self.promotion_target = square
                        self.promotion_selection = chess.QUEEN
                        self.show_promotion_modal = True
                        return True
                    else:
                        # Regular move
                        move = chess.Move(self.selected_square, square)
                        if move in self.board.legal_moves:
                            captured = self.board.piece_at(square)
                            self._make_move(move, captured)
                    return True

                self.selected_square = None
                self.valid_targets = []
                return True
        
        return False
    
    def _draw_stats_window(self, board_right: int, board_top: int, board_height: int):
        """Draw the stats window next to the chess board."""
        stats_width = int(280 * self.scale)
        stats_height = board_height
        stats_x = board_right + int(20 * self.scale)
        stats_y = board_top
        
        # Draw main window
        stats_rect = pygame.Rect(stats_x, stats_y, stats_width, stats_height)
        pygame.draw.rect(self.screen, COLOR_BG_DARK, stats_rect)
        pygame.draw.rect(self.screen, COLOR_CYAN, stats_rect, 2)
        
        try:
            # Increased font sizes: stats text +5pt, larger title
            title_font = pygame.font.Font(None, max(int(20 * self.scale), 14))  # Larger title
            body_font = pygame.font.Font(None, max(int(19 * self.scale), 13))  # +5pt from 14
            small_font = pygame.font.Font(None, max(int(17 * self.scale), 11))  # +5pt from 12
        except Exception:
            return
        
        # Title "CHESS STATS" - center aligned, no box
        title_text = title_font.render("CHESS STATS", True, COLOR_WHITE)
        title_x = stats_x + (stats_width - title_text.get_width()) // 2
        title_y = stats_y + int(15 * self.scale)
        self.screen.blit(title_text, (title_x, title_y))
        
        # Content area
        content_x = stats_x + int(15 * self.scale)
        content_y = title_y + title_text.get_height() + int(15 * self.scale)
        line_height = int(24 * self.scale)
        
        # Current game status and AI Difficulty side by side
        status_label = body_font.render("CURRENT GAME:", True, COLOR_CYAN)
        self.screen.blit(status_label, (content_x, content_y))
        
        # AI Difficulty box - aligned with terminal left edge
        # Calculate content width first
        diff_label_text = small_font.render("AI:", True, COLOR_CYAN)
        arrow_size = int(12 * self.scale)
        level_text = small_font.render(str(self.ai_difficulty), True, COLOR_WHITE)
        content_width = diff_label_text.get_width() + int(8 * self.scale) + arrow_size + int(5 * self.scale) + level_text.get_width() + int(5 * self.scale) + arrow_size
        
        # Box should be 5px padding on each side, so add 10px total
        difficulty_box_width = content_width + int(10 * self.scale)
        # Align left edge with terminal left edge (content_x)
        difficulty_box_x = content_x
        difficulty_box_y = content_y
        difficulty_box_height = int(28 * self.scale)
        difficulty_box_rect = pygame.Rect(difficulty_box_x, difficulty_box_y, difficulty_box_width, difficulty_box_height)
        pygame.draw.rect(self.screen, COLOR_BLACK, difficulty_box_rect)
        pygame.draw.rect(self.screen, COLOR_CYAN, difficulty_box_rect, 1)
        
        # Difficulty label and controls inside box - 5px padding
        self.screen.blit(diff_label_text, (difficulty_box_x + int(5 * self.scale), difficulty_box_y + (difficulty_box_height - diff_label_text.get_height()) // 2))
        
        # Difficulty controls
        arrow_y = difficulty_box_y + (difficulty_box_height - arrow_size) // 2
        down_arrow_x = difficulty_box_x + int(5 * self.scale) + diff_label_text.get_width() + int(8 * self.scale)
        self.ai_difficulty_down_rect = pygame.Rect(down_arrow_x - int(2 * self.scale), arrow_y - int(2 * self.scale), 
                                                    arrow_size + int(4 * self.scale), arrow_size + int(4 * self.scale))
        pygame.draw.polygon(self.screen, COLOR_CYAN, [
            (down_arrow_x + arrow_size // 2, arrow_y),
            (down_arrow_x, arrow_y + arrow_size),
            (down_arrow_x + arrow_size, arrow_y + arrow_size)
        ])
        
        level_x = down_arrow_x + arrow_size + int(5 * self.scale)
        level_text = small_font.render(str(self.ai_difficulty), True, COLOR_WHITE)
        self.screen.blit(level_text, (level_x, arrow_y))
        
        up_arrow_x = level_x + level_text.get_width() + int(5 * self.scale)
        self.ai_difficulty_up_rect = pygame.Rect(up_arrow_x - int(2 * self.scale), arrow_y - int(2 * self.scale), 
                                                  arrow_size + int(4 * self.scale), arrow_size + int(4 * self.scale))
        pygame.draw.polygon(self.screen, COLOR_CYAN, [
            (up_arrow_x + arrow_size // 2, arrow_y + arrow_size),
            (up_arrow_x, arrow_y),
            (up_arrow_x + arrow_size, arrow_y)
        ])
        
        content_y += line_height
        
        status_text = small_font.render(self.status_message, True, COLOR_WHITE)
        self.screen.blit(status_text, (content_x + int(5 * self.scale), content_y))
        content_y += int(line_height * 1.2)
        
        # AI Terminal - moved up to be just under "Your move."
        terminal_height = int(120 * self.scale)
        terminal_y = content_y
        terminal_rect = pygame.Rect(content_x, terminal_y, stats_width - int(30 * self.scale), terminal_height)
        self.ai_terminal_rect = terminal_rect
        
        # Terminal background
        pygame.draw.rect(self.screen, COLOR_BLACK, terminal_rect)
        pygame.draw.rect(self.screen, COLOR_CYAN, terminal_rect, 1)
        
        # Terminal content (scrollable)
        terminal_padding = int(5 * self.scale)
        terminal_inner_y = terminal_rect.y + terminal_padding - self.ai_terminal_scroll_y
        terminal_inner_x = terminal_rect.x + terminal_padding
        
        if self.ai_thinking_exposed and self.ai_thinking_log:
            max_width = terminal_rect.width - terminal_padding * 2
            line_spacing = int(5 * self.scale)  # 5px spacing between lines
            for log_line in self.ai_thinking_log:
                # Only render if within terminal bounds (clip to terminal)
                if terminal_inner_y < terminal_rect.y:
                    terminal_inner_y += small_font.get_height() + line_spacing
                    continue
                if terminal_inner_y + small_font.get_height() > terminal_rect.bottom:
                    break
                
                # Wrap text if too long
                words = log_line.split(' ')
                current_line = ""
                for word in words:
                    test_line = current_line + (" " if current_line else "") + word
                    test_surface = small_font.render(test_line, True, COLOR_CYAN)
                    if test_surface.get_width() <= max_width:
                        current_line = test_line
                    else:
                        if current_line:
                            log_surface = small_font.render(current_line, True, COLOR_CYAN)
                            # Clip to terminal bounds
                            if terminal_inner_y >= terminal_rect.y and terminal_inner_y + small_font.get_height() <= terminal_rect.bottom:
                                self.screen.blit(log_surface, (terminal_inner_x, terminal_inner_y))
                            terminal_inner_y += small_font.get_height() + line_spacing
                            if terminal_inner_y + small_font.get_height() > terminal_rect.bottom:
                                break
                        current_line = word
                if current_line:
                    log_surface = small_font.render(current_line, True, COLOR_CYAN)
                    # Clip to terminal bounds
                    if terminal_inner_y >= terminal_rect.y and terminal_inner_y + small_font.get_height() <= terminal_rect.bottom:
                        self.screen.blit(log_surface, (terminal_inner_x, terminal_inner_y))
                terminal_inner_y += small_font.get_height() + line_spacing
        else:
            # Show placeholder when thinking is off or no log yet
            if not self.ai_thinking_log:
                placeholder = small_font.render("Waiting for AI move...", True, COLOR_GREY)
            else:
                placeholder = small_font.render("AI thinking hidden", True, COLOR_GREY)
            self.screen.blit(placeholder, (terminal_inner_x, terminal_inner_y))
        
        content_y = terminal_rect.bottom + int(10 * self.scale)
        
        # Radio buttons for AI Thinking Exposed - 10px under label
        radio_label_x = content_x
        radio_label_y = content_y
        
        # Label
        radio_label = small_font.render("AI Thinking Exposed:", True, COLOR_CYAN)
        self.screen.blit(radio_label, (radio_label_x, radio_label_y))
        radio_y = radio_label_y + radio_label.get_height() + int(10 * self.scale)
        radio_size = int(12 * self.scale)
        
        # ON radio button
        radio_on_x = radio_label_x + int(10 * self.scale)
        radio_on_rect = pygame.Rect(radio_on_x, radio_y, radio_size, radio_size)
        self.ai_radio_on_rect = pygame.Rect(radio_on_x - int(5 * self.scale), radio_y - int(2 * self.scale), 
                                           int(80 * self.scale), int(16 * self.scale))  # Larger clickable area
        is_on_hovered = self.hovered_button == "ai_radio_on"
        pygame.draw.circle(self.screen, COLOR_CYAN if self.ai_thinking_exposed else COLOR_GREY, 
                          radio_on_rect.center, radio_size // 2, 1)
        if self.ai_thinking_exposed:
            pygame.draw.circle(self.screen, COLOR_CYAN, radio_on_rect.center, radio_size // 3)
        on_label = small_font.render("ON", True, COLOR_CYAN if self.ai_thinking_exposed else COLOR_GREY)
        self.screen.blit(on_label, (radio_on_x + radio_size + int(5 * self.scale), radio_y))
        
        # OFF radio button
        radio_off_x = radio_on_x + int(60 * self.scale)
        radio_off_rect = pygame.Rect(radio_off_x, radio_y, radio_size, radio_size)
        self.ai_radio_off_rect = pygame.Rect(radio_off_x - int(5 * self.scale), radio_y - int(2 * self.scale), 
                                             int(80 * self.scale), int(16 * self.scale))  # Larger clickable area
        is_off_hovered = self.hovered_button == "ai_radio_off"
        pygame.draw.circle(self.screen, COLOR_CYAN if not self.ai_thinking_exposed else COLOR_GREY, 
                          radio_off_rect.center, radio_size // 2, 1)
        if not self.ai_thinking_exposed:
            pygame.draw.circle(self.screen, COLOR_CYAN, radio_off_rect.center, radio_size // 3)
        off_label = small_font.render("OFF", True, COLOR_CYAN if not self.ai_thinking_exposed else COLOR_GREY)
        self.screen.blit(off_label, (radio_off_x + radio_size + int(5 * self.scale), radio_y))
        
        # Radio button hotspots - cover circle shapes with padding
        self.ai_radio_on_rect = pygame.Rect(radio_on_x - int(4 * self.scale), radio_y - int(4 * self.scale), 
                                           radio_size + int(8 * self.scale), radio_size + int(8 * self.scale))
        self.ai_radio_off_rect = pygame.Rect(radio_off_x - int(4 * self.scale), radio_y - int(4 * self.scale), 
                                             radio_size + int(8 * self.scale), radio_size + int(8 * self.scale))
        
        content_y = radio_y + int(radio_size * 1.5) + int(10 * self.scale) + int(line_height) - int(30 * self.scale)  # Moved up 30px
        
        # Position Evaluation Display - in terminal-esque box
        eval_box_height = int(24 * self.scale)
        eval_box_y = content_y
        eval_box_rect = pygame.Rect(content_x, eval_box_y, stats_width - int(30 * self.scale), eval_box_height)
        pygame.draw.rect(self.screen, COLOR_BLACK, eval_box_rect)
        pygame.draw.rect(self.screen, COLOR_CYAN, eval_box_rect, 1)
        
        eval_label_text = small_font.render("Eval:", True, COLOR_CYAN)
        self.screen.blit(eval_label_text, (content_x + int(5 * self.scale), eval_box_y + (eval_box_height - eval_label_text.get_height()) // 2))
        
        eval_score = self.get_position_evaluation()
        if abs(eval_score) > 1000:  # Checkmate
            eval_text = "M+" if eval_score > 0 else "M-"
        else:
            eval_text = f"{eval_score:+.1f}"
        eval_color = COLOR_GREEN if eval_score > 0 else COLOR_RED if eval_score < 0 else COLOR_GREY
        eval_surface = small_font.render(eval_text, True, eval_color)
        self.screen.blit(eval_surface, (content_x + eval_label_text.get_width() + int(10 * self.scale), 
                                        eval_box_y + (eval_box_height - eval_surface.get_height()) // 2))
        
        content_y = eval_box_y + eval_box_height + int(5 * self.scale)
        
        # Move History Display - in terminal-esque box
        history_box_height = int(24 * self.scale)
        history_box_y = content_y
        history_box_rect = pygame.Rect(content_x, history_box_y, stats_width - int(30 * self.scale), history_box_height)
        pygame.draw.rect(self.screen, COLOR_BLACK, history_box_rect)
        pygame.draw.rect(self.screen, COLOR_CYAN, history_box_rect, 1)
        
        if self.move_history:
            history_label_text = small_font.render("History:", True, COLOR_CYAN)
            self.screen.blit(history_label_text, (content_x + int(5 * self.scale), 
                                                  history_box_y + (history_box_height - history_label_text.get_height()) // 2))
            
            # Show last moves that fit
            history_text = " ".join(self.move_history[-8:])
            history_surface = small_font.render(history_text, True, COLOR_WHITE)
            max_width = stats_width - int(30 * self.scale) - history_label_text.get_width() - int(15 * self.scale)
            if history_surface.get_width() > max_width:
                # Truncate
                while history_surface.get_width() > max_width and len(history_text) > 0:
                    history_text = history_text[:-1]
                    history_surface = small_font.render(history_text + "...", True, COLOR_WHITE)
            self.screen.blit(history_surface, (content_x + history_label_text.get_width() + int(10 * self.scale), 
                                               history_box_y + (history_box_height - history_surface.get_height()) // 2))
        
        content_y = history_box_y + history_box_height + int(10 * self.scale)
        
        # Stats
        stats_label = body_font.render("CAREER STATS:", True, COLOR_CYAN)
        self.screen.blit(stats_label, (content_x, content_y))
        content_y += line_height
        
        games_played = self.stats.get("games_played", 0)
        wins = self.stats.get("wins", 0)
        losses = self.stats.get("losses", 0)
        draws = self.stats.get("draws", 0)
        resignations = self.stats.get("resignations", 0)
        
        win_rate = (wins / games_played * 100) if games_played > 0 else 0
        
        # First row: Games Played, Resignations (same vertical line)
        games_text = small_font.render(f"Games Played: {games_played}", True, COLOR_WHITE)
        games_x = content_x + int(5 * self.scale)
        self.screen.blit(games_text, (games_x, content_y))
        
        # 5 spaces after Games Played
        space_width = small_font.size("     ")[0]
        resignations_text = small_font.render(f"Resignations: {resignations}", True, COLOR_YELLOW)
        resignations_x = games_x + games_text.get_width() + space_width
        self.screen.blit(resignations_text, (resignations_x, content_y))
        
        content_y += int(line_height * 0.9)
        
        # Second row: Win Rate under Resignations, align R with W
        win_rate_text = small_font.render(f"Win Rate: {win_rate:.1f}%", True, COLOR_CYAN)
        # Align the "W" in "Win Rate" with the "R" in "Resignations"
        resignations_r_x = resignations_x + small_font.size("Resignations: ")[0]  # X position of "R"
        win_rate_w_x = resignations_r_x - small_font.size("Win ")[0]  # Position so "W" aligns with "R"
        win_rate_x = win_rate_w_x
        self.screen.blit(win_rate_text, (win_rate_x, content_y))
        
        content_y += int(line_height * 0.9)
        
        # Remaining stats on separate lines
        remaining_stats = [
            (f"Wins: {wins}", COLOR_GREEN),
            (f"Losses: {losses}", COLOR_RED),
            (f"Draws: {draws}", COLOR_GREY),
        ]
        
        for text, color in remaining_stats:
            stat_surface = small_font.render(text, True, color)
            self.screen.blit(stat_surface, (content_x + int(5 * self.scale), content_y))
            content_y += int(line_height * 0.9)
        
        # Last game result
        content_y += int(line_height * 0.5)
        last_result = self.stats.get("last_game_result")
        if last_result:
            result_text = f"Last Game: {last_result.upper()}"
            result_color = COLOR_GREEN if last_result == "win" else COLOR_RED if last_result == "loss" else COLOR_GREY
            result_surface = small_font.render(result_text, True, result_color)
            self.screen.blit(result_surface, (content_x, content_y))
            content_y += int(line_height * 1.2)
        
        # Buttons area - inside window, not overlapping text, positioned above bottom bar
        bottom_bar_height = int(22 * self.scale)
        bottom_bar_y = stats_y + stats_height - bottom_bar_height
        button_width = int(100 * self.scale)
        button_height = int(28 * self.scale)
        button_spacing = int(8 * self.scale)
        button_x = stats_x + (stats_width - button_width) // 2
        
        # Calculate button area - ensure it fits above bottom bar
        total_button_height = button_height * 3 + button_spacing * 2  # 3 buttons
        button_y = bottom_bar_y - total_button_height - int(10 * self.scale)
        
        # Resign button (only show when playing) - with hover
        if self.phase == "playing":
            self.resign_button_rect = pygame.Rect(button_x, button_y, button_width, button_height)
            is_resign_hovered = self.hovered_button == "resign"
            resign_bg = COLOR_CYAN if is_resign_hovered else COLOR_BG_TITLE
            pygame.draw.rect(self.screen, resign_bg, self.resign_button_rect)
            pygame.draw.rect(self.screen, COLOR_CYAN, self.resign_button_rect, 2)
            resign_text = small_font.render("RESIGN", True, COLOR_WHITE if is_resign_hovered else COLOR_CYAN)
            self.screen.blit(resign_text, resign_text.get_rect(center=self.resign_button_rect.center))
            button_y += button_height + button_spacing
        else:
            self.resign_button_rect = None
        
        # Wipe Stats button - with hover
        self.wipe_stats_button_rect = pygame.Rect(button_x, button_y, button_width, button_height)
        is_wipe_hovered = self.hovered_button == "wipe_stats"
        wipe_bg = COLOR_RED if is_wipe_hovered else COLOR_BG_TITLE
        pygame.draw.rect(self.screen, wipe_bg, self.wipe_stats_button_rect)
        pygame.draw.rect(self.screen, COLOR_RED, self.wipe_stats_button_rect, 2)
        wipe_text = small_font.render("WIPE STATS", True, COLOR_WHITE if is_wipe_hovered else COLOR_RED)
        self.screen.blit(wipe_text, wipe_text.get_rect(center=self.wipe_stats_button_rect.center))
        button_y += button_height + button_spacing
        
        # Exit button - with hover
        self.exit_button_rect = pygame.Rect(button_x, button_y, button_width, button_height)
        is_exit_hovered = self.hovered_button == "exit"
        exit_bg = COLOR_CYAN if is_exit_hovered else COLOR_BG_TITLE
        pygame.draw.rect(self.screen, exit_bg, self.exit_button_rect)
        pygame.draw.rect(self.screen, COLOR_CYAN, self.exit_button_rect, 2)
        exit_text = small_font.render("EXIT", True, COLOR_WHITE if is_exit_hovered else COLOR_CYAN)
        self.screen.blit(exit_text, exit_text.get_rect(center=self.exit_button_rect.center))
        
        # BRADSONIC // CHESS at bottom (like health monitor style)
        bottom_bar_rect = pygame.Rect(stats_x, bottom_bar_y, stats_width, bottom_bar_height)
        pygame.draw.rect(self.screen, COLOR_BG_TITLE, bottom_bar_rect)
        pygame.draw.line(self.screen, COLOR_CYAN, (stats_x, bottom_bar_y), 
                        (stats_x + stats_width, bottom_bar_y), 1)
        
        brand_text = small_font.render("BRADSONIC // CHESS", True, COLOR_CYAN)
        brand_x = stats_x + (stats_width - brand_text.get_width()) // 2
        brand_y = bottom_bar_y + (bottom_bar_height - brand_text.get_height()) // 2
        self.screen.blit(brand_text, (brand_x, brand_y))
    
    def _draw_exit_modal(self):
        """Draw exit confirmation modal."""
        if not self.show_exit_modal:
            return
        
        modal_width = int(400 * self.scale)
        modal_height = int(150 * self.scale)
        modal_x = self.desktop_x + (self.desktop_size[0] - modal_width) // 2
        modal_y = self.desktop_y + (self.desktop_size[1] - modal_height) // 2
        
        # Modal background
        modal_rect = pygame.Rect(modal_x, modal_y, modal_width, modal_height)
        pygame.draw.rect(self.screen, COLOR_BG_DARK, modal_rect)
        pygame.draw.rect(self.screen, COLOR_CYAN, modal_rect, 2)
        
        try:
            body_font = pygame.font.Font(None, max(int(16 * self.scale), 12))
            button_font = pygame.font.Font(None, max(int(14 * self.scale), 10))
        except Exception:
            return
        
        # Message
        message = "This will count as a resignation\nagainst your stats, confirm?"
        lines = message.split('\n')
        text_y = modal_y + int(20 * self.scale)
        for line in lines:
            text_surface = body_font.render(line, True, COLOR_WHITE)
            text_x = modal_x + (modal_width - text_surface.get_width()) // 2
            self.screen.blit(text_surface, (text_x, text_y))
            text_y += body_font.get_height() + int(5 * self.scale)
        
        # YES/NO buttons
        button_width = int(80 * self.scale)
        button_height = int(32 * self.scale)
        button_spacing = int(20 * self.scale)
        total_width = button_width * 2 + button_spacing
        start_x = modal_x + (modal_width - total_width) // 2
        button_y = modal_y + modal_height - button_height - int(15 * self.scale)
        
        self.modal_yes_button_rect = pygame.Rect(start_x, button_y, button_width, button_height)
        pygame.draw.rect(self.screen, COLOR_BG_TITLE, self.modal_yes_button_rect)
        pygame.draw.rect(self.screen, COLOR_GREEN, self.modal_yes_button_rect, 2)
        yes_text = button_font.render("YES", True, COLOR_GREEN)
        self.screen.blit(yes_text, yes_text.get_rect(center=self.modal_yes_button_rect.center))
        
        self.modal_no_button_rect = pygame.Rect(start_x + button_width + button_spacing, button_y, button_width, button_height)
        pygame.draw.rect(self.screen, COLOR_BG_TITLE, self.modal_no_button_rect)
        pygame.draw.rect(self.screen, COLOR_RED, self.modal_no_button_rect, 2)
        no_text = button_font.render("NO", True, COLOR_RED)
        self.screen.blit(no_text, no_text.get_rect(center=self.modal_no_button_rect.center))
    
    def _draw_wipe_stats_modal(self):
        """Draw wipe stats confirmation modal."""
        if not self.show_wipe_stats_modal:
            return
        
        modal_width = int(400 * self.scale)
        modal_height = int(150 * self.scale)
        modal_x = self.desktop_x + (self.desktop_size[0] - modal_width) // 2
        modal_y = self.desktop_y + (self.desktop_size[1] - modal_height) // 2
        
        # Modal background
        modal_rect = pygame.Rect(modal_x, modal_y, modal_width, modal_height)
        pygame.draw.rect(self.screen, COLOR_BG_DARK, modal_rect)
        pygame.draw.rect(self.screen, COLOR_RED, modal_rect, 2)
        
        try:
            body_font = pygame.font.Font(None, max(int(16 * self.scale), 12))
            button_font = pygame.font.Font(None, max(int(14 * self.scale), 10))
        except Exception:
            return
        
        # Message
        message = "Wipe all chess stats?\nThis cannot be undone."
        lines = message.split('\n')
        text_y = modal_y + int(20 * self.scale)
        for line in lines:
            text_surface = body_font.render(line, True, COLOR_WHITE)
            text_x = modal_x + (modal_width - text_surface.get_width()) // 2
            self.screen.blit(text_surface, (text_x, text_y))
            text_y += body_font.get_height() + int(5 * self.scale)
        
        # YES/NO buttons
        button_width = int(80 * self.scale)
        button_height = int(32 * self.scale)
        button_spacing = int(20 * self.scale)
        total_width = button_width * 2 + button_spacing
        start_x = modal_x + (modal_width - total_width) // 2
        button_y = modal_y + modal_height - button_height - int(15 * self.scale)
        
        self.modal_yes_button_rect = pygame.Rect(start_x, button_y, button_width, button_height)
        pygame.draw.rect(self.screen, COLOR_BG_TITLE, self.modal_yes_button_rect)
        pygame.draw.rect(self.screen, COLOR_RED, self.modal_yes_button_rect, 2)
        yes_text = button_font.render("YES", True, COLOR_RED)
        self.screen.blit(yes_text, yes_text.get_rect(center=self.modal_yes_button_rect.center))
        
        self.modal_no_button_rect = pygame.Rect(start_x + button_width + button_spacing, button_y, button_width, button_height)
        pygame.draw.rect(self.screen, COLOR_BG_TITLE, self.modal_no_button_rect)
        pygame.draw.rect(self.screen, COLOR_CYAN, self.modal_no_button_rect, 2)
        no_text = button_font.render("NO", True, COLOR_CYAN)
        self.screen.blit(no_text, no_text.get_rect(center=self.modal_no_button_rect.center))
    
    def _draw_promotion_modal(self):
        """Draw pawn promotion modal with piece selection."""
        if not self.show_promotion_modal:
            return
        
        modal_width = int(350 * self.scale)
        modal_height = int(200 * self.scale)
        modal_x = self.desktop_x + (self.desktop_size[0] - modal_width) // 2
        modal_y = self.desktop_y + (self.desktop_size[1] - modal_height) // 2
        
        # Modal background
        modal_rect = pygame.Rect(modal_x, modal_y, modal_width, modal_height)
        pygame.draw.rect(self.screen, COLOR_BG_DARK, modal_rect)
        pygame.draw.rect(self.screen, COLOR_CYAN, modal_rect, 2)
        
        try:
            title_font = pygame.font.Font(None, max(int(18 * self.scale), 14))
            button_font = pygame.font.Font(None, max(int(14 * self.scale), 10))
        except Exception:
            return
        
        # Title
        title_text = title_font.render("Choose Promotion", True, COLOR_WHITE)
        title_x = modal_x + (modal_width - title_text.get_width()) // 2
        title_y = modal_y + int(15 * self.scale)
        self.screen.blit(title_text, (title_x, title_y))
        
        # Piece selection area
        piece_area_y = title_y + title_text.get_height() + int(15 * self.scale)
        piece_area_height = int(80 * self.scale)
        piece_size = int(60 * self.scale)
        
        # Left arrow
        arrow_size = int(24 * self.scale)
        left_arrow_x = modal_x + int(20 * self.scale)
        left_arrow_y = piece_area_y + (piece_area_height - arrow_size) // 2
        self.promotion_modal_left_arrow_rect = pygame.Rect(left_arrow_x - int(5 * self.scale), left_arrow_y - int(5 * self.scale), 
                                                           arrow_size + int(10 * self.scale), arrow_size + int(10 * self.scale))
        pygame.draw.polygon(self.screen, COLOR_CYAN, [
            (left_arrow_x + arrow_size, left_arrow_y),
            (left_arrow_x, left_arrow_y + arrow_size // 2),
            (left_arrow_x + arrow_size, left_arrow_y + arrow_size)
        ])
        
        # Selected piece
        piece_x = modal_x + (modal_width - piece_size) // 2
        piece_y = piece_area_y + (piece_area_height - piece_size) // 2
        
        # Get piece surface
        color = "w" if self.player_color == chess.WHITE else "b"
        piece_map = {
            chess.QUEEN: chess.QUEEN,
            chess.ROOK: chess.ROOK,
            chess.BISHOP: chess.BISHOP,
            chess.KNIGHT: chess.KNIGHT
        }
        piece_type = self.promotion_selection
        if piece_type == chess.KNIGHT:
            dict_key = f"{color}_{chess.KNIGHT}_l"
        else:
            dict_key = f"{color}_{piece_type}"
        
        piece_surface = self.piece_surfaces.get(dict_key)
        if piece_surface:
            scaled_piece = pygame.transform.smoothscale(piece_surface, (piece_size, piece_size))
            self.screen.blit(scaled_piece, (piece_x, piece_y))
        
        # Right arrow
        right_arrow_x = modal_x + modal_width - int(20 * self.scale) - arrow_size
        right_arrow_y = piece_area_y + (piece_area_height - arrow_size) // 2
        self.promotion_modal_right_arrow_rect = pygame.Rect(right_arrow_x - int(5 * self.scale), right_arrow_y - int(5 * self.scale), 
                                                            arrow_size + int(10 * self.scale), arrow_size + int(10 * self.scale))
        pygame.draw.polygon(self.screen, COLOR_CYAN, [
            (right_arrow_x, right_arrow_y),
            (right_arrow_x + arrow_size, right_arrow_y + arrow_size // 2),
            (right_arrow_x, right_arrow_y + arrow_size)
        ])
        
        # OK button
        button_width = int(80 * self.scale)
        button_height = int(32 * self.scale)
        button_x = modal_x + (modal_width - button_width) // 2
        button_y = modal_y + modal_height - button_height - int(15 * self.scale)
        self.promotion_modal_ok_rect = pygame.Rect(button_x, button_y, button_width, button_height)
        pygame.draw.rect(self.screen, COLOR_BG_TITLE, self.promotion_modal_ok_rect)
        pygame.draw.rect(self.screen, COLOR_GREEN, self.promotion_modal_ok_rect, 2)
        ok_text = button_font.render("OK", True, COLOR_GREEN)
        self.screen.blit(ok_text, ok_text.get_rect(center=self.promotion_modal_ok_rect.center))
    
    def draw(self):
        """Draw the chess game within the desktop environment."""
        if not self.active:
            return
        
        # Check if AI move delay has elapsed
        if self.waiting_for_ai:
            self._check_ai_move_delay()

        if self.error_message:
            # Just show error message, no overlay
            try:
                error_font = pygame.font.Font(None, max(int(16 * self.scale), 12))
                error_surface = error_font.render(self.error_message, True, COLOR_RED)
                error_x = self.desktop_x + int(20 * self.scale)
                error_y = self.health_monitor_y
                self.screen.blit(error_surface, (error_x, error_y))
            except Exception:
                pass
            return

        if not self.board_surface:
            return

        # Position board at health monitor Y position
        board_x = self.desktop_x + int(20 * self.scale)
        board_y = self.health_monitor_y
        
        # Board is 490x490px inner area with 56px border on all sides
        # The grid starts 56px from top and bottom
        # Pieces on bottom row should render 20px below the grid
        board_rect = self.board_surface.get_rect()
        board_rect.x = board_x
        board_rect.y = board_y
        
        # Draw board
        self.screen.blit(self.board_surface, board_rect.topleft)
        self.board_rect = board_rect
        
        # Calculate the inner grid area (490x490px scaled)
        grid_top = board_rect.y + self.board_border
        grid_left = board_rect.x + self.board_border
        grid_bottom = grid_top + self.board_inner_size
        grid_right = grid_left + self.board_inner_size
        
        try:
            body_font = pygame.font.Font(None, max(int(14 * self.scale), 10))
        except Exception:
            return

        if self.phase == "color_select":
            # Color selection buttons - increased font size by 5pt
            try:
                button_font = pygame.font.Font(None, max(int(19 * self.scale), 15))  # +5pt from 14
            except Exception:
                button_font = body_font
            
            btn_w = int(140 * self.scale)
            btn_h = int(36 * self.scale)
            btn_spacing = int(20 * self.scale)
            total_width = btn_w * 2 + btn_spacing
            start_x = board_rect.centerx - total_width // 2
            btn_y = grid_bottom + int(20 * self.scale)
            self.color_buttons = {
                "white": pygame.Rect(start_x, btn_y, btn_w, btn_h),
                "black": pygame.Rect(start_x + btn_w + btn_spacing, btn_y, btn_w, btn_h)
            }
            for color, rect in self.color_buttons.items():
                is_hovered = self.hovered_button == f"color_{color}"
                bg_color = COLOR_CYAN if is_hovered else COLOR_BG_TITLE
                pygame.draw.rect(self.screen, bg_color, rect)
                pygame.draw.rect(self.screen, COLOR_CYAN, rect, 2)
                label = "Play as White" if color == "white" else "Play as Blue"
                text = button_font.render(label, True, COLOR_WHITE if is_hovered else COLOR_CYAN)
                self.screen.blit(text, text.get_rect(center=rect.center))
            
            # Quit button (doesn't count as resignation) - increased font size by 5pt
            quit_btn_w = int(100 * self.scale)
            quit_btn_h = int(32 * self.scale)
            quit_btn_x = board_rect.centerx - quit_btn_w // 2
            quit_btn_y = btn_y + btn_h + int(15 * self.scale)
            self.color_select_quit_button_rect = pygame.Rect(quit_btn_x, quit_btn_y, quit_btn_w, quit_btn_h)
            is_quit_hovered = self.hovered_button == "quit_color"
            quit_bg = COLOR_GREY if is_quit_hovered else COLOR_BG_TITLE
            pygame.draw.rect(self.screen, quit_bg, self.color_select_quit_button_rect)
            pygame.draw.rect(self.screen, COLOR_GREY, self.color_select_quit_button_rect, 2)
            quit_text = button_font.render("QUIT", True, COLOR_WHITE if is_quit_hovered else COLOR_GREY)
            self.screen.blit(quit_text, quit_text.get_rect(center=self.color_select_quit_button_rect.center))
            return

        if self.board:
            # Last move highlighting disabled
            # Only show dots for selected piece's valid targets
            if self.selected_square is not None and self.valid_targets:
                for target_square in self.valid_targets:
                    rect = self._square_rect(target_square, board_rect)
                    if rect:
                        # Center of square
                        center_x = rect.centerx + int(7 * self.scale)
                        center_y = rect.centery + int(7 * self.scale)
                        dot_radius = int(6 * self.scale)
                        # Semi-transparent dot
                        dot_surface = pygame.Surface((dot_radius * 2, dot_radius * 2), pygame.SRCALPHA)
                        pygame.draw.circle(dot_surface, (0, 255, 255, 120), (dot_radius, dot_radius), dot_radius)
                        self.screen.blit(dot_surface, (center_x - dot_radius, center_y - dot_radius))
            
            # Draw captured pieces - under bottom player, above top pieces (25% smaller)
            captured_size = 0.75  # 25% smaller
            piece_spacing = int(10 * self.scale)
            piece_size = int(self.square_size * captured_size)
            
            # Captured by player (bottom)
            player_captured = self.captured_pieces["b" if self.player_color == chess.WHITE else "w"]
            if player_captured:
                start_x = grid_left
                y_pos = grid_bottom + int(10 * self.scale)
                x_offset = 0
                for piece_type in player_captured:
                    color = "b" if self.player_color == chess.WHITE else "w"
                    if piece_type == chess.KNIGHT:
                        dict_key = f"{color}_{chess.KNIGHT}_l"  # Default to left variant
                    else:
                        dict_key = f"{color}_{piece_type}"
                    
                    surface = self.piece_surfaces.get(dict_key)
                    if surface:
                        scaled_surface = pygame.transform.smoothscale(surface, (piece_size, piece_size))
                        self.screen.blit(scaled_surface, (start_x + x_offset, y_pos))
                        x_offset += piece_size + piece_spacing
            
            # Captured by CPU (top)
            cpu_captured = self.captured_pieces["w" if self.player_color == chess.WHITE else "b"]
            if cpu_captured:
                start_x = grid_left
                y_pos = grid_top - piece_size - int(10 * self.scale)
                x_offset = 0
                for piece_type in cpu_captured:
                    color = "w" if self.player_color == chess.WHITE else "b"
                    if piece_type == chess.KNIGHT:
                        dict_key = f"{color}_{chess.KNIGHT}_l"  # Default to left variant
                    else:
                        dict_key = f"{color}_{piece_type}"
                    
                    surface = self.piece_surfaces.get(dict_key)
                    if surface:
                        scaled_surface = pygame.transform.smoothscale(surface, (piece_size, piece_size))
                        self.screen.blit(scaled_surface, (start_x + x_offset, y_pos))
                        x_offset += piece_size + piece_spacing

            # Draw pieces with proper z-ordering: render from top to bottom
            # This ensures pieces at the bottom of the board render last (appear on top)
            # Pawns still render before other pieces for proper layering
            piece_map = self.board.piece_map()
            
            # Separate pawns from other pieces and collect rendering info
            pawns_data = []
            other_pieces_data = []
            
            for square, piece in piece_map.items():
                color = "w" if piece.color == chess.WHITE else "b"
                
                if piece.piece_type == chess.PAWN:
                    dict_key = f"{color}_{chess.PAWN}"
                elif piece.piece_type == chess.KNIGHT:
                    file_idx = chess.square_file(square)
                    variant = "l" if file_idx <= 3 else "r"
                    dict_key = f"{color}_{chess.KNIGHT}_{variant}"
                else:
                    dict_key = f"{color}_{piece.piece_type}"
                
                surface = self.piece_surfaces.get(dict_key)
                if not surface:
                    continue
                
                square_rect = self._square_rect(square, board_rect)
                if not square_rect:
                    continue
                
                piece_height = self.piece_heights.get(dict_key, surface.get_height())
                rank = chess.square_rank(square)
                
                # Determine if this is a bottom row piece (visually at the bottom of the board)
                is_bottom_row = False
                if self.player_color == chess.WHITE:
                    visual_row = 7 - rank
                    is_bottom_row = (visual_row == 7)
                else:
                    visual_row = rank
                    is_bottom_row = (visual_row == 7)
                
                # Calculate final piece Y position
                if is_bottom_row:
                    piece_y = grid_bottom + int(20 * self.scale) - piece_height - int(15 * self.scale)
                else:
                    piece_y = square_rect.bottom - piece_height
                
                piece_x = square_rect.centerx - surface.get_width() // 2
                
                # Store rendering data with Y position for sorting
                render_data = {
                    "square": square,
                    "piece": piece,
                    "surface": surface,
                    "dict_key": dict_key,
                    "piece_x": piece_x,
                    "piece_y": piece_y,
                    "visual_y": piece_y  # Use piece_y for sorting (bottom of piece)
                }
                
                if piece.piece_type == chess.PAWN:
                    pawns_data.append(render_data)
                else:
                    other_pieces_data.append(render_data)
            
            # Sort by visual Y position (ascending: top pieces first, bottom pieces last)
            # This ensures pieces at the bottom render last and appear on top
            pawns_data.sort(key=lambda x: x["visual_y"])
            other_pieces_data.sort(key=lambda x: x["visual_y"])
            
            # Draw pawns first (sorted by Y position)
            for data in pawns_data:
                self.screen.blit(data["surface"], (data["piece_x"], data["piece_y"]))
            
            # Draw other pieces after pawns (sorted by Y position)
            for data in other_pieces_data:
                self.screen.blit(data["surface"], (data["piece_x"], data["piece_y"]))
        
        # Draw stats window next to board
        self._draw_stats_window(board_rect.right, board_rect.y, board_rect.height)
        
        # Draw modals on top
        self._draw_exit_modal()
        self._draw_wipe_stats_modal()
        self._draw_promotion_modal()
