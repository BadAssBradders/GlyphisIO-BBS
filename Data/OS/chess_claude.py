import pygame
import sys
from copy import deepcopy

# Initialize Pygame
pygame.init()

# Constants
WIDTH, HEIGHT = 800, 800
BOARD_SIZE = 8
SQUARE_SIZE = WIDTH // BOARD_SIZE
FPS = 60

# Colors
WHITE = (240, 217, 181)
BLACK = (181, 136, 99)
HIGHLIGHT = (186, 202, 68)
SELECTED = (246, 246, 105)
MOVE_HINT = (130, 151, 105, 128)
TEXT_COLOR = (0, 0, 0)
BG_COLOR = (49, 46, 43)

# Piece values for AI evaluation
PIECE_VALUES = {
    'P': 100, 'N': 320, 'B': 330, 'R': 500, 'Q': 900, 'K': 20000,
    'p': -100, 'n': -320, 'b': -330, 'r': -500, 'q': -900, 'k': -20000
}

# Position bonuses for better piece placement
PAWN_TABLE = [
    0,  0,  0,  0,  0,  0,  0,  0,
    50, 50, 50, 50, 50, 50, 50, 50,
    10, 10, 20, 30, 30, 20, 10, 10,
    5,  5, 10, 25, 25, 10,  5,  5,
    0,  0,  0, 20, 20,  0,  0,  0,
    5, -5,-10,  0,  0,-10, -5,  5,
    5, 10, 10,-20,-20, 10, 10,  5,
    0,  0,  0,  0,  0,  0,  0,  0
]

KNIGHT_TABLE = [
    -50,-40,-30,-30,-30,-30,-40,-50,
    -40,-20,  0,  0,  0,  0,-20,-40,
    -30,  0, 10, 15, 15, 10,  0,-30,
    -30,  5, 15, 20, 20, 15,  5,-30,
    -30,  0, 15, 20, 20, 15,  0,-30,
    -30,  5, 10, 15, 15, 10,  5,-30,
    -40,-20,  0,  5,  5,  0,-20,-40,
    -50,-40,-30,-30,-30,-30,-40,-50
]

BISHOP_TABLE = [
    -20,-10,-10,-10,-10,-10,-10,-20,
    -10,  0,  0,  0,  0,  0,  0,-10,
    -10,  0,  5, 10, 10,  5,  0,-10,
    -10,  5,  5, 10, 10,  5,  5,-10,
    -10,  0, 10, 10, 10, 10,  0,-10,
    -10, 10, 10, 10, 10, 10, 10,-10,
    -10,  5,  0,  0,  0,  0,  5,-10,
    -20,-10,-10,-10,-10,-10,-10,-20
]

class ChessGame:
    def __init__(self):
        self.board = self.init_board()
        self.selected_piece = None
        self.valid_moves = []
        self.white_turn = True
        self.move_history = []
        self.white_king_pos = (7, 4)
        self.black_king_pos = (0, 4)
        self.white_can_castle_kingside = True
        self.white_can_castle_queenside = True
        self.black_can_castle_kingside = True
        self.black_can_castle_queenside = True
        self.en_passant_target = None
        self.halfmove_clock = 0
        self.game_over = False
        self.winner = None
        
    def init_board(self):
        """Initialize the chess board with starting position"""
        board = [['' for _ in range(8)] for _ in range(8)]
        
        # Black pieces (uppercase = white, lowercase = black)
        board[0] = ['r', 'n', 'b', 'q', 'k', 'b', 'n', 'r']
        board[1] = ['p'] * 8
        
        # White pieces
        board[6] = ['P'] * 8
        board[7] = ['R', 'N', 'B', 'Q', 'K', 'B', 'N', 'R']
        
        return board
    
    def is_white_piece(self, piece):
        return piece.isupper()
    
    def get_piece_moves(self, row, col):
        """Get all valid moves for a piece at position"""
        piece = self.board[row][col]
        if not piece:
            return []
        
        moves = []
        is_white = self.is_white_piece(piece)
        piece_type = piece.upper()
        
        if piece_type == 'P':
            moves = self.get_pawn_moves(row, col, is_white)
        elif piece_type == 'N':
            moves = self.get_knight_moves(row, col, is_white)
        elif piece_type == 'B':
            moves = self.get_bishop_moves(row, col, is_white)
        elif piece_type == 'R':
            moves = self.get_rook_moves(row, col, is_white)
        elif piece_type == 'Q':
            moves = self.get_queen_moves(row, col, is_white)
        elif piece_type == 'K':
            moves = self.get_king_moves(row, col, is_white)
        
        # Filter out moves that would put own king in check
        valid_moves = []
        for move in moves:
            if self.is_legal_move(row, col, move[0], move[1]):
                valid_moves.append(move)
        
        return valid_moves
    
    def get_pawn_moves(self, row, col, is_white):
        moves = []
        direction = -1 if is_white else 1
        start_row = 6 if is_white else 1
        
        # Forward move
        new_row = row + direction
        if 0 <= new_row < 8 and not self.board[new_row][col]:
            moves.append((new_row, col))
            
            # Double move from start
            if row == start_row:
                new_row2 = row + 2 * direction
                if not self.board[new_row2][col]:
                    moves.append((new_row2, col))
        
        # Captures
        for dc in [-1, 1]:
            new_row = row + direction
            new_col = col + dc
            if 0 <= new_row < 8 and 0 <= new_col < 8:
                target = self.board[new_row][new_col]
                if target and self.is_white_piece(target) != is_white:
                    moves.append((new_row, new_col))
                # En passant
                elif self.en_passant_target == (new_row, new_col):
                    moves.append((new_row, new_col))
        
        return moves
    
    def get_knight_moves(self, row, col, is_white):
        moves = []
        knight_moves = [(-2,-1), (-2,1), (-1,-2), (-1,2), (1,-2), (1,2), (2,-1), (2,1)]
        
        for dr, dc in knight_moves:
            new_row, new_col = row + dr, col + dc
            if 0 <= new_row < 8 and 0 <= new_col < 8:
                target = self.board[new_row][new_col]
                if not target or self.is_white_piece(target) != is_white:
                    moves.append((new_row, new_col))
        
        return moves
    
    def get_bishop_moves(self, row, col, is_white):
        return self.get_sliding_moves(row, col, is_white, [(1,1), (1,-1), (-1,1), (-1,-1)])
    
    def get_rook_moves(self, row, col, is_white):
        return self.get_sliding_moves(row, col, is_white, [(0,1), (0,-1), (1,0), (-1,0)])
    
    def get_queen_moves(self, row, col, is_white):
        return self.get_sliding_moves(row, col, is_white, 
            [(0,1), (0,-1), (1,0), (-1,0), (1,1), (1,-1), (-1,1), (-1,-1)])
    
    def get_sliding_moves(self, row, col, is_white, directions):
        moves = []
        for dr, dc in directions:
            for i in range(1, 8):
                new_row = row + dr * i
                new_col = col + dc * i
                if not (0 <= new_row < 8 and 0 <= new_col < 8):
                    break
                target = self.board[new_row][new_col]
                if not target:
                    moves.append((new_row, new_col))
                else:
                    if self.is_white_piece(target) != is_white:
                        moves.append((new_row, new_col))
                    break
        return moves
    
    def get_king_moves(self, row, col, is_white):
        moves = []
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                if dr == 0 and dc == 0:
                    continue
                new_row, new_col = row + dr, col + dc
                if 0 <= new_row < 8 and 0 <= new_col < 8:
                    target = self.board[new_row][new_col]
                    if not target or self.is_white_piece(target) != is_white:
                        moves.append((new_row, new_col))
        
        # Castling
        if is_white and self.white_can_castle_kingside:
            if not self.board[7][5] and not self.board[7][6]:
                if not self.is_square_attacked(7, 4, False) and \
                   not self.is_square_attacked(7, 5, False) and \
                   not self.is_square_attacked(7, 6, False):
                    moves.append((7, 6))
        
        if is_white and self.white_can_castle_queenside:
            if not self.board[7][3] and not self.board[7][2] and not self.board[7][1]:
                if not self.is_square_attacked(7, 4, False) and \
                   not self.is_square_attacked(7, 3, False) and \
                   not self.is_square_attacked(7, 2, False):
                    moves.append((7, 2))
        
        if not is_white and self.black_can_castle_kingside:
            if not self.board[0][5] and not self.board[0][6]:
                if not self.is_square_attacked(0, 4, True) and \
                   not self.is_square_attacked(0, 5, True) and \
                   not self.is_square_attacked(0, 6, True):
                    moves.append((0, 6))
        
        if not is_white and self.black_can_castle_queenside:
            if not self.board[0][3] and not self.board[0][2] and not self.board[0][1]:
                if not self.is_square_attacked(0, 4, True) and \
                   not self.is_square_attacked(0, 3, True) and \
                   not self.is_square_attacked(0, 2, True):
                    moves.append((0, 2))
        
        return moves
    
    def is_square_attacked(self, row, col, by_white):
        """Check if a square is attacked by the given color"""
        for r in range(8):
            for c in range(8):
                piece = self.board[r][c]
                if piece and self.is_white_piece(piece) == by_white:
                    # Get moves without legal check to avoid recursion
                    piece_type = piece.upper()
                    if piece_type == 'P':
                        moves = self.get_pawn_attacks(r, c, by_white)
                    elif piece_type == 'N':
                        moves = self.get_knight_moves(r, c, by_white)
                    elif piece_type == 'B':
                        moves = self.get_bishop_moves(r, c, by_white)
                    elif piece_type == 'R':
                        moves = self.get_rook_moves(r, c, by_white)
                    elif piece_type == 'Q':
                        moves = self.get_queen_moves(r, c, by_white)
                    elif piece_type == 'K':
                        moves = self.get_king_attacks(r, c)
                    else:
                        moves = []
                    
                    if (row, col) in moves:
                        return True
        return False
    
    def get_pawn_attacks(self, row, col, is_white):
        """Get pawn attack squares only"""
        attacks = []
        direction = -1 if is_white else 1
        for dc in [-1, 1]:
            new_row = row + direction
            new_col = col + dc
            if 0 <= new_row < 8 and 0 <= new_col < 8:
                attacks.append((new_row, new_col))
        return attacks
    
    def get_king_attacks(self, row, col):
        """Get king attack squares only"""
        attacks = []
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                if dr == 0 and dc == 0:
                    continue
                new_row, new_col = row + dr, col + dc
                if 0 <= new_row < 8 and 0 <= new_col < 8:
                    attacks.append((new_row, new_col))
        return attacks
    
    def is_legal_move(self, from_row, from_col, to_row, to_col):
        """Check if move doesn't leave king in check"""
        # Make move temporarily
        piece = self.board[from_row][from_col]
        captured = self.board[to_row][to_col]
        self.board[to_row][to_col] = piece
        self.board[from_row][from_col] = ''
        
        # Find king position
        is_white = self.is_white_piece(piece)
        if piece.upper() == 'K':
            king_pos = (to_row, to_col)
        else:
            king_pos = self.white_king_pos if is_white else self.black_king_pos
        
        # Check if king is in check
        in_check = self.is_square_attacked(king_pos[0], king_pos[1], not is_white)
        
        # Undo move
        self.board[from_row][from_col] = piece
        self.board[to_row][to_col] = captured
        
        return not in_check
    
    def make_move(self, from_row, from_col, to_row, to_col):
        """Execute a move on the board"""
        piece = self.board[from_row][from_col]
        captured = self.board[to_row][to_col]
        is_white = self.is_white_piece(piece)
        
        # Handle en passant capture
        if piece.upper() == 'P' and self.en_passant_target == (to_row, to_col):
            capture_row = to_row + (1 if is_white else -1)
            self.board[capture_row][to_col] = ''
        
        # Handle castling
        if piece.upper() == 'K' and abs(to_col - from_col) == 2:
            if to_col == 6:  # Kingside
                rook = self.board[to_row][7]
                self.board[to_row][7] = ''
                self.board[to_row][5] = rook
            else:  # Queenside
                rook = self.board[to_row][0]
                self.board[to_row][0] = ''
                self.board[to_row][3] = rook
        
        # Make the move
        self.board[to_row][to_col] = piece
        self.board[from_row][from_col] = ''
        
        # Update king position
        if piece.upper() == 'K':
            if is_white:
                self.white_king_pos = (to_row, to_col)
            else:
                self.black_king_pos = (to_row, to_col)
        
        # Update castling rights
        if piece == 'K':
            self.white_can_castle_kingside = False
            self.white_can_castle_queenside = False
        elif piece == 'k':
            self.black_can_castle_kingside = False
            self.black_can_castle_queenside = False
        elif piece == 'R':
            if from_row == 7 and from_col == 7:
                self.white_can_castle_kingside = False
            elif from_row == 7 and from_col == 0:
                self.white_can_castle_queenside = False
        elif piece == 'r':
            if from_row == 0 and from_col == 7:
                self.black_can_castle_kingside = False
            elif from_row == 0 and from_col == 0:
                self.black_can_castle_queenside = False
        
        # Set en passant target
        if piece.upper() == 'P' and abs(to_row - from_row) == 2:
            self.en_passant_target = ((from_row + to_row) // 2, to_col)
        else:
            self.en_passant_target = None
        
        # Handle pawn promotion
        if piece.upper() == 'P' and (to_row == 0 or to_row == 7):
            self.board[to_row][to_col] = 'Q' if is_white else 'q'
        
        # Switch turn
        self.white_turn = not self.white_turn
        
        # Check for game over
        if not self.has_legal_moves():
            self.game_over = True
            if self.is_in_check():
                self.winner = "White" if not self.white_turn else "Black"
            else:
                self.winner = "Stalemate"
    
    def is_in_check(self):
        """Check if current player's king is in check"""
        if self.white_turn:
            king_pos = self.white_king_pos
            return self.is_square_attacked(king_pos[0], king_pos[1], False)
        else:
            king_pos = self.black_king_pos
            return self.is_square_attacked(king_pos[0], king_pos[1], True)
    
    def has_legal_moves(self):
        """Check if current player has any legal moves"""
        for row in range(8):
            for col in range(8):
                piece = self.board[row][col]
                if piece and self.is_white_piece(piece) == self.white_turn:
                    if self.get_piece_moves(row, col):
                        return True
        return False
    
    def evaluate_board(self):
        """Evaluate board position for AI"""
        score = 0
        
        for row in range(8):
            for col in range(8):
                piece = self.board[row][col]
                if piece:
                    piece_value = PIECE_VALUES[piece]
                    position_bonus = 0
                    
                    # Add position bonuses
                    if piece.upper() == 'P':
                        idx = row * 8 + col if piece.isupper() else (7 - row) * 8 + col
                        position_bonus = PAWN_TABLE[idx] * (1 if piece.isupper() else -1)
                    elif piece.upper() == 'N':
                        idx = row * 8 + col if piece.isupper() else (7 - row) * 8 + col
                        position_bonus = KNIGHT_TABLE[idx] * (1 if piece.isupper() else -1)
                    elif piece.upper() == 'B':
                        idx = row * 8 + col if piece.isupper() else (7 - row) * 8 + col
                        position_bonus = BISHOP_TABLE[idx] * (1 if piece.isupper() else -1)
                    
                    score += piece_value + position_bonus
        
        return score
    
    def minimax(self, depth, alpha, beta, maximizing):
        """Minimax algorithm with alpha-beta pruning"""
        if depth == 0 or self.game_over:
            return self.evaluate_board()
        
        if maximizing:
            max_eval = float('-inf')
            for row in range(8):
                for col in range(8):
                    piece = self.board[row][col]
                    if piece and not self.is_white_piece(piece):
                        moves = self.get_piece_moves(row, col)
                        for move in moves:
                            # Make move
                            game_copy = self.copy_game_state()
                            self.make_move(row, col, move[0], move[1])
                            
                            eval_score = self.minimax(depth - 1, alpha, beta, False)
                            
                            # Undo move
                            self.restore_game_state(game_copy)
                            
                            max_eval = max(max_eval, eval_score)
                            alpha = max(alpha, eval_score)
                            if beta <= alpha:
                                return max_eval
            return max_eval
        else:
            min_eval = float('inf')
            for row in range(8):
                for col in range(8):
                    piece = self.board[row][col]
                    if piece and self.is_white_piece(piece):
                        moves = self.get_piece_moves(row, col)
                        for move in moves:
                            # Make move
                            game_copy = self.copy_game_state()
                            self.make_move(row, col, move[0], move[1])
                            
                            eval_score = self.minimax(depth - 1, alpha, beta, True)
                            
                            # Undo move
                            self.restore_game_state(game_copy)
                            
                            min_eval = min(min_eval, eval_score)
                            beta = min(beta, eval_score)
                            if beta <= alpha:
                                return min_eval
            return min_eval
    
    def get_best_move(self, depth=3):
        """Get the best move for AI (Black)"""
        best_move = None
        best_eval = float('-inf')
        alpha = float('-inf')
        beta = float('inf')
        
        for row in range(8):
            for col in range(8):
                piece = self.board[row][col]
                if piece and not self.is_white_piece(piece):
                    moves = self.get_piece_moves(row, col)
                    for move in moves:
                        # Make move
                        game_copy = self.copy_game_state()
                        self.make_move(row, col, move[0], move[1])
                        
                        eval_score = self.minimax(depth - 1, alpha, beta, False)
                        
                        # Undo move
                        self.restore_game_state(game_copy)
                        
                        if eval_score > best_eval:
                            best_eval = eval_score
                            best_move = ((row, col), move)
                        
                        alpha = max(alpha, eval_score)
        
        return best_move
    
    def copy_game_state(self):
        """Create a copy of current game state"""
        return {
            'board': deepcopy(self.board),
            'white_turn': self.white_turn,
            'white_king_pos': self.white_king_pos,
            'black_king_pos': self.black_king_pos,
            'white_can_castle_kingside': self.white_can_castle_kingside,
            'white_can_castle_queenside': self.white_can_castle_queenside,
            'black_can_castle_kingside': self.black_can_castle_kingside,
            'black_can_castle_queenside': self.black_can_castle_queenside,
            'en_passant_target': self.en_passant_target,
            'game_over': self.game_over,
            'winner': self.winner
        }
    
    def restore_game_state(self, state):
        """Restore game state from copy"""
        self.board = state['board']
        self.white_turn = state['white_turn']
        self.white_king_pos = state['white_king_pos']
        self.black_king_pos = state['black_king_pos']
        self.white_can_castle_kingside = state['white_can_castle_kingside']
        self.white_can_castle_queenside = state['white_can_castle_queenside']
        self.black_can_castle_kingside = state['black_can_castle_kingside']
        self.black_can_castle_queenside = state['black_can_castle_queenside']
        self.en_passant_target = state['en_passant_target']
        self.game_over = state['game_over']
        self.winner = state['winner']


def draw_board(screen, game):
    """Draw the chess board"""
    for row in range(BOARD_SIZE):
        for col in range(BOARD_SIZE):
            color = WHITE if (row + col) % 2 == 0 else BLACK
            
            # Highlight selected square
            if game.selected_piece and game.selected_piece == (row, col):
                color = SELECTED
            # Highlight valid moves
            elif (row, col) in game.valid_moves:
                color = HIGHLIGHT
            
            pygame.draw.rect(screen, color, (col * SQUARE_SIZE, row * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))
            
            # Draw move hints for valid moves
            if (row, col) in game.valid_moves:
                center_x = col * SQUARE_SIZE + SQUARE_SIZE // 2
                center_y = row * SQUARE_SIZE + SQUARE_SIZE // 2
                if game.board[row][col]:
                    # Capture indicator (ring)
                    pygame.draw.circle(screen, MOVE_HINT, (center_x, center_y), SQUARE_SIZE // 2 - 5, 8)
                else:
                    # Move indicator (dot)
                    pygame.draw.circle(screen, MOVE_HINT, (center_x, center_y), SQUARE_SIZE // 6)


def draw_pieces(screen, game):
    """Draw chess pieces"""
    font = pygame.font.Font(None, 80)
    
    piece_symbols = {
        'K': '♔', 'Q': '♕', 'R': '♖', 'B': '♗', 'N': '♘', 'P': '♙',
        'k': '♚', 'q': '♛', 'r': '♜', 'b': '♝', 'n': '♞', 'p': '♟'
    }
    
    for row in range(BOARD_SIZE):
        for col in range(BOARD_SIZE):
            piece = game.board[row][col]
            if piece:
                symbol = piece_symbols.get(piece, piece)
                text = font.render(symbol, True, (255, 255, 255) if game.is_white_piece(piece) else (0, 0, 0))
                text_rect = text.get_rect(center=(col * SQUARE_SIZE + SQUARE_SIZE // 2, 
                                                  row * SQUARE_SIZE + SQUARE_SIZE // 2))
                screen.blit(text, text_rect)


def draw_ui(screen, game):
    """Draw UI elements"""
    font = pygame.font.Font(None, 36)
    
    # Draw turn indicator
    turn_text = "White's Turn" if game.white_turn else "Black's Turn (AI)"
    text = font.render(turn_text, True, (255, 255, 255))
    screen.blit(text, (10, HEIGHT + 10))
    
    # Draw game over message
    if game.game_over:
        font_large = pygame.font.Font(None, 72)
        if game.winner == "Stalemate":
            text = font_large.render("Stalemate!", True, (255, 255, 0))
        else:
            text = font_large.render(f"{game.winner} Wins!", True, (255, 255, 255))
        text_rect = text.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        
        # Draw semi-transparent background
        s = pygame.Surface((WIDTH, HEIGHT))
        s.set_alpha(200)
        s.fill((0, 0, 0))
        screen.blit(s, (0, 0))
        screen.blit(text, text_rect)
        
        # Draw restart instruction
        restart_text = font.render("Press R to restart", True, (255, 255, 255))
        restart_rect = restart_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 60))
        screen.blit(restart_text, restart_rect)


def main():
    screen = pygame.display.set_mode((WIDTH, HEIGHT + 50))
    pygame.display.set_caption("Chess Game with AI")
    clock = pygame.time.Clock()
    
    game = ChessGame()
    ai_thinking = False
    
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    game = ChessGame()
                    ai_thinking = False
            
            elif event.type == pygame.MOUSEBUTTONDOWN and not game.game_over and not ai_thinking:
                if game.white_turn:  # Only allow player input on white's turn
                    x, y = event.pos
                    if y < HEIGHT:
                        col = x // SQUARE_SIZE
                        row = y // SQUARE_SIZE
                        
                        if game.selected_piece:
                            # Try to move
                            if (row, col) in game.valid_moves:
                                from_row, from_col = game.selected_piece
                                game.make_move(from_row, from_col, row, col)
                                game.selected_piece = None
                                game.valid_moves = []
                            else:
                                # Select new piece
                                piece = game.board[row][col]
                                if piece and game.is_white_piece(piece):
                                    game.selected_piece = (row, col)
                                    game.valid_moves = game.get_piece_moves(row, col)
                                else:
                                    game.selected_piece = None
                                    game.valid_moves = []
                        else:
                            # Select piece
                            piece = game.board[row][col]
                            if piece and game.is_white_piece(piece):
                                game.selected_piece = (row, col)
                                game.valid_moves = game.get_piece_moves(row, col)
        
        # AI move
        if not game.white_turn and not game.game_over and not ai_thinking:
            ai_thinking = True
            pygame.display.set_caption("Chess Game with AI - AI Thinking...")
            
        if ai_thinking:
            best_move = game.get_best_move(depth=3)
            if best_move:
                from_pos, to_pos = best_move
                game.make_move(from_pos[0], from_pos[1], to_pos[0], to_pos[1])
            ai_thinking = False
            pygame.display.set_caption("Chess Game with AI")
        
        # Draw everything
        screen.fill(BG_COLOR)
        draw_board(screen, game)
        draw_pieces(screen, game)
        draw_ui(screen, game)
        
        pygame.display.flip()
        clock.tick(FPS)
    
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()