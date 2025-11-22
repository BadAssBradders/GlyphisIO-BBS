"""
Solitaire Game Module
Klondike-style solitaire for the OS Mode desktop environment.

- Designed to sit in the same 'health monitor' strip as the chess game.
- Uses Data/OS/solitaire for assets.
- Works without assets (draws simple rectangles); auto-uses PNGs if found.

Expected folder layout (relative to the executable/script):
    Data/OS/solitaire/solitaire.py
    Data/OS/solitaire/card_back.png                (optional)
    Data/OS/solitaire/cards/card_AH.png, ...       (optional card faces)
"""

import pygame
import os
import sys
import random
import time
from typing import List, Dict, Tuple, Optional

# Visual constants (match OS_Mode style)
COLOR_BG_DARK = (20, 20, 40)
COLOR_BG_TITLE = (40, 40, 60)
COLOR_CYAN = (0, 255, 255)
COLOR_GREEN = (0, 255, 0)
COLOR_RED = (255, 0, 0)
COLOR_WHITE = (255, 255, 255)
COLOR_BLACK = (0, 0, 0)
COLOR_GREY = (128, 128, 128)
COLOR_YELLOW = (255, 255, 0)
COLOR_DARK_CYAN = (0, 180, 180)
COLOR_BUTTON_HOVER = (60, 60, 80)  # Button hover color
COLOR_HIGHLIGHT = (100, 255, 255, 60)  # Semi-transparent highlight
COLOR_SHADOW = (0, 0, 0, 80)  # Semi-transparent shadow

RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
SUITS = ["H", "D", "C", "S"]  # Hearts, Diamonds, Clubs, Spades


# Data path helper - mirrors chess_game.get_data_path
def get_data_path(*path_parts) -> str:
    """
    Returns the path to the Data folder, handling both development and built executable scenarios.
    Assumes this file lives in Data/OS/solitaire.
    """
    if getattr(sys, "frozen", False):
        base_path = sys._MEIPASS  # type: ignore[attr-defined]
    else:
        script_dir = os.path.dirname(os.path.abspath(__file__))      # .../Data/OS/solitaire
        os_dir = os.path.dirname(script_dir)                         # .../Data/OS
        data_folder = os.path.dirname(os_dir)                        # .../Data
        base_path = data_folder
    return os.path.join(base_path, *path_parts)


class Card:
    """Simple card model used by SolitaireGame."""
    __slots__ = ("rank", "suit", "face_up")

    def __init__(self, rank: str, suit: str, face_up: bool = False):
        self.rank = rank
        self.suit = suit
        self.face_up = face_up

    def color(self) -> str:
        return "red" if self.suit in ("H", "D") else "black"

    def value(self) -> int:
        # For tableau descending sequences (K..A)
        return RANKS.index(self.rank)

    def __repr__(self) -> str:
        return f"{self.rank}{self.suit}{'^' if self.face_up else 'v'}"


class SolitaireGame:
    """
    Klondike Solitaire game for OS Mode.
    API is deliberately similar in spirit to ChessGame:

    - update_desktop(desktop_x, desktop_y, desktop_size, health_monitor_y)
    - start()
    - close()
    - handle_event(event) -> bool
    - draw()

    To integrate:
      - Create one SolitaireGame instance in OS_Mode.__init__ (like ChessGame).
      - Wire _launch_games_app("solitaire") to call its start().
      - Call solitaire_game.handle_event in OSMode.handle_event, similar to chess.
    """

    def __init__(
        self,
        screen: pygame.Surface,
        scale: float,
        desktop_x: int,
        desktop_y: int,
        desktop_size: Tuple[int, int],
        health_monitor_y: int,
        bbs_x: int = 0,
        bbs_width: int = 0,
    ):
        self.screen = screen
        self.scale = scale
        self.desktop_x = desktop_x
        self.desktop_y = desktop_y
        self.desktop_size = desktop_size
        # health_monitor_y is no longer used - everything is positioned relative to desktop
        self.bbs_x = bbs_x
        self.bbs_width = bbs_width

        # Game state
        self.active: bool = False
        self.game_over: bool = False
        self.win: bool = False

        # Card layout
        self.stock: List[Card] = []          # Face-down draw pile
        self.waste: List[Card] = []          # Face-up discard
        self.foundations: List[List[Card]] = [[], [], [], []]  # 4 foundations
        self.tableaus: List[List[Card]] = [[] for _ in range(7)]  # 7 columns

        # Drag state
        self.dragged_cards: List[Card] = []
        self.drag_from: Optional[Tuple[str, int]] = None  # ("tableau", idx) or ("waste", 0)
        self.drag_offset: Tuple[int, int] = (0, 0)
        self.dragging: bool = False

        # Layout rects - ensure no overlapping
        self.card_width = int(70 * self.scale)
        self.card_height = int(100 * self.scale)
        self.card_spacing_x = int(20 * self.scale)  # Adequate spacing to prevent overlap
        self.card_spacing_y = int(28 * self.scale)  # Adequate spacing to prevent overlap
        self.tableaus_top_y = 0
        self.window_rect: Optional[pygame.Rect] = None
        self.title_bar_rect: Optional[pygame.Rect] = None
        self.stats_panel_rect: Optional[pygame.Rect] = None
        self.stock_rect: Optional[pygame.Rect] = None
        self.waste_rect: Optional[pygame.Rect] = None
        self.foundation_rects: List[pygame.Rect] = []
        
        # Hover state for visual feedback
        self.hovered_stock = False
        self.hovered_waste = False
        self.hovered_foundation: Optional[int] = None
        self.hovered_tableau: Optional[int] = None

        # Timer / moves
        self.start_time: float = 0.0
        self.elapsed_time: float = 0.0
        self.moves: int = 0

        # Hover
        self.hovered_button: Optional[str] = None
        self.exit_button_rect: Optional[pygame.Rect] = None

        # Assets
        self.card_back_surface: Optional[pygame.Surface] = None
        # key: "AS", "10H" etc -> pygame.Surface
        self.card_face_surfaces: Dict[str, pygame.Surface] = {}

        # Pre-calc layout based on current desktop + monitor
        self._update_layout()
        self._load_assets()

    # -------------------------------------------------------------------------
    # Desktop / layout
    # -------------------------------------------------------------------------

    def update_desktop(
        self,
        desktop_x: int,
        desktop_y: int,
        desktop_size: Tuple[int, int],
        health_monitor_y: int,
    ) -> None:
        """Update desktop coordinates and layout."""
        self.desktop_x = desktop_x
        self.desktop_y = desktop_y
        self.desktop_size = desktop_size
        # health_monitor_y is no longer used
        self._update_layout()

    def _update_layout(self) -> None:
        """
        Set up the solitaire game window entirely within desktop bounds.
        Creates a beautiful unified window with title bar, game area, and stats panel.
        """
        # Title bar height
        title_bar_height = int(35 * self.scale)
        
        # Margins from desktop edges
        margin = int(20 * self.scale)
        
        # Stats panel width - ensure it's wide enough for help text like "  Waste → Foundation"
        # Use a fixed width that should accommodate the longest text lines
        stats_panel_width = int(240 * self.scale)  # 20% smaller (was 300)
        
        # Game window dimensions - match OS_mode desktop size exactly
        window_width = self.desktop_size[0]
        window_height = self.desktop_size[1]
        
        # Position window at desktop position (matches OS_mode window)
        window_x = self.desktop_x
        window_y = self.desktop_y
        
        # Full window rect (includes title bar)
        self.window_rect = pygame.Rect(window_x, window_y, window_width, window_height)
        
        # Title bar rect (inside window)
        self.title_bar_rect = pygame.Rect(
            window_x,
            window_y,
            window_width,
            title_bar_height
        )
        
        # Exit button in title bar (right side)
        exit_button_width = int(60 * self.scale)
        exit_button_height = int(25 * self.scale)
        exit_button_x = window_x + window_width - exit_button_width - int(15 * self.scale)
        exit_button_y = window_y + (title_bar_height - exit_button_height) // 2
        self.exit_button_rect = pygame.Rect(
            exit_button_x,
            exit_button_y,
            exit_button_width,
            exit_button_height
        )
        
        # Content area (below title bar)
        content_y = window_y + title_bar_height
        content_height = window_height - title_bar_height
        
        # Stats panel on the right
        self.stats_panel_rect = pygame.Rect(
            window_x + window_width - stats_panel_width,
            content_y,
            stats_panel_width,
            content_height
        )
        
        # Game play area (left of stats panel)
        play_area_margin = int(15 * self.scale)
        play_area_x = window_x + play_area_margin
        play_area_width = window_width - stats_panel_width - (play_area_margin * 2)  # Margin on both sides
        play_area_height = content_height - int(20 * self.scale)
        
        self.play_area_rect = pygame.Rect(
            play_area_x,
            content_y + int(10 * self.scale),
            play_area_width,
            play_area_height
        )

        # Playing card area inset from play area
        card_area_x = self.play_area_rect.x + int(15 * self.scale)
        card_area_y = self.play_area_rect.y + int(15 * self.scale)
        card_area_width = self.play_area_rect.width - int(30 * self.scale)
        card_area_height = self.play_area_rect.height - int(30 * self.scale)

        # Top row layout:
        #   [Stock] [Waste]    gap    [F1] [F2] [F3] [F4]
        gap_x = int(25 * self.scale)  # Increased gap
        
        # Stock and Waste positioned 20px from edge
        stock_x = card_area_x
        stock_y = card_area_y
        self.stock_rect = pygame.Rect(stock_x, stock_y, self.card_width, self.card_height)

        waste_x = stock_x + self.card_width + gap_x
        self.waste_rect = pygame.Rect(waste_x, stock_y, self.card_width, self.card_height)

        # Foundations on the right half of the card area
        foundations_start_x = card_area_x + card_area_width - (
            4 * self.card_width + 3 * gap_x
        )
        foundations_y = card_area_y
        self.foundation_rects = []
        for i in range(4):
            rect = pygame.Rect(
                foundations_start_x + i * (self.card_width + gap_x),
                foundations_y,
                self.card_width,
                self.card_height,
            )
            self.foundation_rects.append(rect)

        # Tableau columns - positioned below stock/waste/foundations
        tableau_spacing = int(15 * self.scale)
        self.tableaus_top_y = card_area_y + self.card_height + tableau_spacing
        self.tableau_base_x = card_area_x
        self.tableau_count = 7
        
        # Calculate available height for tableaus
        max_tableau_height = card_area_height - (self.card_height + tableau_spacing)
        # Ensure we don't exceed available space

    # -------------------------------------------------------------------------
    # Assets
    # -------------------------------------------------------------------------

    def _load_assets(self) -> None:
        """Try to load card back and faces. Falls back to colored rects if missing."""
        solitaire_dir = get_data_path("OS", "solitaire")

        # Card back
        back_path = os.path.join(solitaire_dir, "card_back.png")
        if os.path.exists(back_path):
            try:
                img = pygame.image.load(back_path).convert_alpha()
                self.card_back_surface = pygame.transform.smoothscale(
                    img, (self.card_width, self.card_height)
                )
            except Exception as e:
                print(f"Warning: failed to load card_back.png: {e}")
                self.card_back_surface = None
        else:
            self.card_back_surface = None

        # Card faces
        cards_dir = os.path.join(solitaire_dir, "cards")
        self.card_face_surfaces.clear()
        if os.path.isdir(cards_dir):
            for rank in RANKS:
                for suit in SUITS:
                    name = f"card_{rank}{suit}.png"
                    path = os.path.join(cards_dir, name)
                    key = f"{rank}{suit}"
                    if os.path.exists(path):
                        try:
                            img = pygame.image.load(path).convert_alpha()
                            self.card_face_surfaces[key] = pygame.transform.smoothscale(
                                img, (self.card_width, self.card_height)
                            )
                        except Exception as e:
                            print(f"Warning: failed to load {name}: {e}")
        # If nothing loaded, that's fine; we'll draw vector cards

    # -------------------------------------------------------------------------
    # Game start / reset / close
    # -------------------------------------------------------------------------

    def start(self) -> None:
        """Start a new game of solitaire."""
        self._deal_new_game()
        self.active = True
        self.game_over = False
        self.win = False
        self.start_time = time.time()
        self.moves = 0

    def _deal_new_game(self) -> None:
        """Create and shuffle a full deck, then deal into tableaus."""
        deck: List[Card] = [Card(rank, suit, face_up=False) for suit in SUITS for rank in RANKS]
        random.shuffle(deck)

        # Clear piles
        self.stock = []
        self.waste = []
        self.foundations = [[], [], [], []]
        self.tableaus = [[] for _ in range(7)]

        # Deal to tableaus: 1..7 cards, last card face-up
        for col in range(7):
            for i in range(col + 1):
                card = deck.pop()
                card.face_up = (i == col)
                self.tableaus[col].append(card)

        # Remaining cards go to stock face-down
        self.stock = deck

    def close(self) -> None:
        """Hide the game and clear drag state."""
        self.active = False
        self.dragging = False
        self.dragged_cards = []
        self.drag_from = None

    # -------------------------------------------------------------------------
    # Helpers for rules
    # -------------------------------------------------------------------------

    def _can_place_on_tableau(self, moving: Card, target: Optional[Card]) -> bool:
        """Check if `moving` can be placed on tableau top `target`."""
        if target is None:
            # Only kings can go on empty tableau
            return moving.rank == "K"
        # Alternating colours, descending rank
        if moving.color() == target.color():
            return False
        return moving.value() + 1 == target.value()

    def _can_place_on_foundation(self, moving: Card, foundation_index: int) -> bool:
        """Check if `moving` can go to foundation."""
        pile = self.foundations[foundation_index]
        if not pile:
            # Only Aces start a foundation
            return moving.rank == "A"
        top = pile[-1]
        if moving.suit != top.suit:
            return False
        # Ascending ranks
        return moving.value() == top.value() + 1

    def _card_rect_in_tableau(self, col_index: int, row_index: int) -> pygame.Rect:
        """Return a rect for the given card in the tableau grid."""
        # Spread columns across card area width (20px inset from play area)
        card_area_x = self.play_area_rect.x + int(20 * self.scale)
        card_area_width = self.play_area_rect.width - int(40 * self.scale)
        total_width = self.tableau_count * self.card_width + (self.tableau_count - 1) * self.card_spacing_x
        
        # Center tableau columns within card area
        left = card_area_x + (card_area_width - total_width) // 2

        x = left + col_index * (self.card_width + self.card_spacing_x)
        # vertical offset: each card in column is offset down a bit
        y = self.tableaus_top_y + row_index * self.card_spacing_y
        return pygame.Rect(x, y, self.card_width, self.card_height)

    # -------------------------------------------------------------------------
    # Event handling
    # -------------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handle events. Returns True if the event was consumed."""
        if not self.active:
            return False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                # ESC closes solitaire
                self.close()
                return True

        if event.type == pygame.MOUSEMOTION:
            mx, my = event.pos
            # Update hover states for visual feedback
            self.hovered_stock = self.stock_rect.collidepoint(mx, my) if self.stock_rect else False
            self.hovered_waste = self.waste_rect.collidepoint(mx, my) if self.waste_rect else False
            self.hovered_foundation = None
            self.hovered_tableau = None
            
            # Check exit button hover
            if self.exit_button_rect:
                self.hovered_button = "exit" if self.exit_button_rect.collidepoint(mx, my) else None
            else:
                self.hovered_button = None
            
            # Check foundation hover
            for i, rect in enumerate(self.foundation_rects):
                if rect.collidepoint(mx, my):
                    self.hovered_foundation = i
                    break
            
            # Check tableau hover
            for col_idx in range(self.tableau_count):
                pile = self.tableaus[col_idx]
                if pile:
                    top_rect = self._card_rect_in_tableau(col_idx, len(pile) - 1)
                    if top_rect.collidepoint(mx, my):
                        self.hovered_tableau = col_idx
                        break
                else:
                    empty_rect = self._card_rect_in_tableau(col_idx, 0)
                    if empty_rect.collidepoint(mx, my):
                        self.hovered_tableau = col_idx
                        break
            
            if self.dragging and self.dragged_cards:
                # Just keep the drag offset; the card position is computed in draw()
                return True

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos

            # Click exit button
            if self.exit_button_rect and self.exit_button_rect.collidepoint(mx, my):
                self.close()
                return True

            # Click stock: draw a card or recycle waste
            if self.stock_rect and self.stock_rect.collidepoint(mx, my):
                self._click_stock()
                return True

            # Click waste top card -> begin drag
            if self.waste and self.waste_rect and self.waste_rect.collidepoint(mx, my):
                top_card_rect = self.waste_rect
                if top_card_rect.collidepoint(mx, my):
                    self.dragging = True
                    self.drag_from = ("waste", 0)
                    self.dragged_cards = [self.waste[-1]]
                    self.drag_offset = (mx - top_card_rect.x, my - top_card_rect.y)
                    return True

            # Click tableau columns
            for col_idx, pile in enumerate(self.tableaus):
                if not pile:
                    # Click empty tableau area?
                    # Only meaningful when we drop something, not on mousedown.
                    continue
                for row_idx in range(len(pile)):
                    card = pile[row_idx]
                    if not card.face_up:
                        continue
                    rect = self._card_rect_in_tableau(col_idx, row_idx)
                    if rect.collidepoint(mx, my):
                        # Drag card + all above it (i.e., from row_idx to end)
                        self.dragging = True
                        self.drag_from = ("tableau", col_idx)
                        self.dragged_cards = pile[row_idx:]
                        self.drag_offset = (mx - rect.x, my - rect.y)
                        return True

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.dragging and self.dragged_cards:
                mx, my = event.pos
                # Try to drop onto tableau or foundation
                if self._drop_on_any_foundation(mx, my):
                    self.moves += 1
                    self._check_win()
                    self.dragging = False
                    self.dragged_cards = []
                    self.drag_from = None
                    return True
                if self._drop_on_any_tableau(mx, my):
                    self.moves += 1
                    self._check_win()
                    self.dragging = False
                    self.dragged_cards = []
                    self.drag_from = None
                    return True
                # If we get here, drop was illegal: revert
                self._cancel_drag()
                return True

        return False

    def _click_stock(self) -> None:
        """Handle clicking the stock pile."""
        if self.stock:
            # Draw one card to waste, turning it face up
            card = self.stock.pop()
            card.face_up = True
            self.waste.append(card)
            self.moves += 1
        else:
            # Recycle waste back to stock, turning face-down (keep order)
            if self.waste:
                self.stock = [Card(c.rank, c.suit, face_up=False) for c in reversed(self.waste)]
                self.waste = []
                self.moves += 1

    def _drop_on_any_tableau(self, mx: int, my: int) -> bool:
        """Try to drop dragged cards onto one of the 7 tableaus."""
        moving = self.dragged_cards[0]
        # First, check if we're over any column
        for col_idx in range(self.tableau_count):
            # Determine target rect:
            pile = self.tableaus[col_idx]
            if pile:
                # Top card rect -> we allow dropping slightly below
                target_rect = self._card_rect_in_tableau(col_idx, len(pile) - 1)
                drop_rect = pygame.Rect(
                    target_rect.x,
                    target_rect.y,
                    target_rect.width,
                    target_rect.height + self.card_spacing_y * 3,
                )
                top_card = pile[-1]
            else:
                # Empty column: use base rect
                base_rect = self._card_rect_in_tableau(col_idx, 0)
                drop_rect = base_rect
                top_card = None

            if drop_rect.collidepoint(mx, my):
                if self._can_place_on_tableau(moving, top_card):
                    self._complete_drop_to_tableau(col_idx)
                    return True
        return False

    def _drop_on_any_foundation(self, mx: int, my: int) -> bool:
        """Try to drop a single card on a foundation pile."""
        if len(self.dragged_cards) != 1:
            return False
        moving = self.dragged_cards[0]

        for i, rect in enumerate(self.foundation_rects):
            if rect.collidepoint(mx, my):
                if self._can_place_on_foundation(moving, i):
                    self._complete_drop_to_foundation(i)
                    return True
        return False

    def _complete_drop_to_tableau(self, dest_col: int) -> None:
        """Move dragged_cards onto tableau column dest_col."""
        src_type, src_index = self.drag_from or ("", -1)

        # Remove from source
        if src_type == "waste":
            # moving from waste: only top card
            if self.waste and self.waste[-1] == self.dragged_cards[0]:
                self.waste.pop()
        elif src_type == "tableau":
            # moving from tableau column
            pile = self.tableaus[src_index]
            # Remove from first occurrence of dragged_cards[0] to end
            if self.dragged_cards[0] in pile:
                idx = pile.index(self.dragged_cards[0])
                del pile[idx:]

                # Turn new top card face-up if needed
                if pile and not pile[-1].face_up:
                    pile[-1].face_up = True

        # Place onto destination
        self.tableaus[dest_col].extend(self.dragged_cards)

    def _complete_drop_to_foundation(self, foundation_index: int) -> None:
        """Move dragged_cards[0] into foundation index."""
        moving = self.dragged_cards[0]
        src_type, src_index = self.drag_from or ("", -1)

        if src_type == "waste":
            if self.waste and self.waste[-1] == moving:
                self.waste.pop()
        elif src_type == "tableau":
            pile = self.tableaus[src_index]
            if moving in pile:
                idx = pile.index(moving)
                del pile[idx:]
                # Turn new top card face-up
                if pile and not pile[-1].face_up:
                    pile[-1].face_up = True

        self.foundations[foundation_index].append(moving)

    def _cancel_drag(self) -> None:
        """Cancel drag without changing piles."""
        self.dragging = False
        self.drag_from = None
        self.dragged_cards = []

    def _check_win(self) -> None:
        """Set win flag if all cards are in the foundations."""
        total_foundation_cards = sum(len(p) for p in self.foundations)
        if total_foundation_cards == 52:
            self.game_over = True
            self.win = True
            self.elapsed_time = time.time() - self.start_time

    # -------------------------------------------------------------------------
    # Drawing
    # -------------------------------------------------------------------------

    def draw(self) -> None:
        """Draw solitaire game window entirely within desktop bounds."""
        if not self.active:
            return

        now = time.time()
        if not self.game_over and self.start_time:
            self.elapsed_time = now - self.start_time

        try:
            # Use Verdana system font
            title_font = pygame.font.SysFont("verdana", max(int(26 * self.scale), 16))
            body_font = pygame.font.SysFont("verdana", max(int(18 * self.scale), 12))
            small_font = pygame.font.SysFont("verdana", max(int(16 * self.scale), 10))
        except Exception:
            # Fallback to default font if Verdana not available
            try:
                title_font = pygame.font.Font(None, max(int(26 * self.scale), 16))
                body_font = pygame.font.Font(None, max(int(18 * self.scale), 12))
                small_font = pygame.font.Font(None, max(int(16 * self.scale), 10))
            except Exception:
                return
        
        # Set clipping to window bounds to prevent any rendering outside
        old_clip = self.screen.get_clip()
        self.screen.set_clip(self.window_rect)
        
        # Draw main window background (dark with border)
        pygame.draw.rect(self.screen, COLOR_BG_DARK, self.window_rect)
        pygame.draw.rect(self.screen, COLOR_CYAN, self.window_rect, 2)
        
        # Draw title bar inside window (inside desktop bounds)
        pygame.draw.rect(self.screen, COLOR_BG_TITLE, self.title_bar_rect)
        pygame.draw.line(self.screen, COLOR_CYAN, 
                        (self.title_bar_rect.x, self.title_bar_rect.bottom - 1), 
                        (self.title_bar_rect.right, self.title_bar_rect.bottom - 1), 2)
        
        # Title text
        title_text = title_font.render("SOLITAIRE", True, COLOR_WHITE)
        title_x = self.title_bar_rect.x + int(15 * self.scale)
        title_y = self.title_bar_rect.y + (self.title_bar_rect.height - title_text.get_height()) // 2
        self.screen.blit(title_text, (title_x, title_y))
        
        # Draw exit button on right side of title bar
        if self.exit_button_rect:
            # Button background with hover effect
            button_color = COLOR_BUTTON_HOVER if self.hovered_button == "exit" else COLOR_BG_TITLE
            pygame.draw.rect(self.screen, button_color, self.exit_button_rect)
            pygame.draw.rect(self.screen, COLOR_CYAN, self.exit_button_rect, 2)
            
            # Button text
            exit_text = small_font.render("EXIT", True, COLOR_WHITE)
            exit_text_x = self.exit_button_rect.x + (self.exit_button_rect.width - exit_text.get_width()) // 2
            exit_text_y = self.exit_button_rect.y + (self.exit_button_rect.height - exit_text.get_height()) // 2
            self.screen.blit(exit_text, (exit_text_x, exit_text_y))
        
        # Draw play area background
        pygame.draw.rect(self.screen, (15, 15, 35), self.play_area_rect)
        pygame.draw.rect(self.screen, COLOR_DARK_CYAN, self.play_area_rect, 1)

        # Draw stock with hover effect
        if self.hovered_stock and not self.dragging:
            hover_surface = pygame.Surface((self.stock_rect.width, self.stock_rect.height), pygame.SRCALPHA)
            hover_surface.fill((0, 255, 255, 40))
            self.screen.blit(hover_surface, self.stock_rect.topleft)
        
        if self.stock:
            self._draw_card_back(self.stock_rect)
            # Show card count on stock
            count_text = small_font.render(str(len(self.stock)), True, COLOR_WHITE)
            count_bg = pygame.Surface((count_text.get_width() + 4, count_text.get_height() + 2), pygame.SRCALPHA)
            count_bg.fill((0, 0, 0, 180))
            self.screen.blit(count_bg, (self.stock_rect.right - count_text.get_width() - 6, self.stock_rect.top + 2))
            self.screen.blit(count_text, (self.stock_rect.right - count_text.get_width() - 4, self.stock_rect.top + 3))
        else:
            # Draw empty outline when stock is empty
            self._draw_empty_slot(self.stock_rect)
        
        # Draw waste with hover effect
        if self.hovered_waste and not self.dragging:
            hover_surface = pygame.Surface((self.waste_rect.width, self.waste_rect.height), pygame.SRCALPHA)
            hover_surface.fill((0, 255, 255, 40))
            self.screen.blit(hover_surface, self.waste_rect.topleft)
        
        # Check if we're dragging from waste
        is_dragging_from_waste = self.dragging and self.drag_from and self.drag_from[0] == "waste"
        
        if self.waste:
            if is_dragging_from_waste:
                # If dragging from waste, show the card underneath (if there is one)
                if len(self.waste) > 1:
                    # Show the card that's underneath the dragged card (second from top)
                    self._draw_card(self.waste[-2], self.waste_rect)
                else:
                    # Dragging the only card, show empty slot
                    self._draw_empty_slot(self.waste_rect)
            else:
                # Not dragging from waste, show top card normally
                self._draw_card(self.waste[-1], self.waste_rect)
        else:
            # Draw empty outline when waste is empty
            self._draw_empty_slot(self.waste_rect)

        # Draw foundations with labels below and hover effects
        foundation_suits = ["♠", "♥", "♦", "♣"]  # Spades, Hearts, Diamonds, Clubs
        for i, rect in enumerate(self.foundation_rects):
            # Hover effect and valid drop highlight
            if self.dragging and self.dragged_cards and len(self.dragged_cards) == 1:
                moving = self.dragged_cards[0]
                if self._can_place_on_foundation(moving, i):
                    highlight_surface = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
                    highlight_surface.fill((0, 255, 0, 60))
                    self.screen.blit(highlight_surface, rect.topleft)
            elif self.hovered_foundation == i and not self.dragging:
                hover_surface = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
                hover_surface.fill((0, 255, 255, 40))
                self.screen.blit(hover_surface, rect.topleft)
            
            if self.foundations[i]:
                self._draw_card(self.foundations[i][-1], rect)
                # Show count on foundation
                count_text = small_font.render(str(len(self.foundations[i])), True, COLOR_WHITE)
                count_bg = pygame.Surface((count_text.get_width() + 4, count_text.get_height() + 2), pygame.SRCALPHA)
                count_bg.fill((0, 0, 0, 180))
                self.screen.blit(count_bg, (rect.right - count_text.get_width() - 6, rect.top + 2))
                self.screen.blit(count_text, (rect.right - count_text.get_width() - 4, rect.top + 3))
            else:
                # Draw empty foundation with suit indicator
                self._draw_empty_foundation(rect, foundation_suits[i])

        # Draw tableau columns with hover effects
        for col_idx, pile in enumerate(self.tableaus):
            if not pile:
                # Draw placeholder empty slot with hover
                rect = self._card_rect_in_tableau(col_idx, 0)
                if self.hovered_tableau == col_idx and self.dragging and self.dragged_cards:
                    # Highlight valid drop zone
                    moving = self.dragged_cards[0]
                    if self._can_place_on_tableau(moving, None):
                        highlight_surface = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
                        highlight_surface.fill((0, 255, 0, 60))
                        self.screen.blit(highlight_surface, rect.topleft)
                self._draw_empty_slot(rect)
                continue
            
            # Highlight top card on hover
            top_rect = self._card_rect_in_tableau(col_idx, len(pile) - 1)
            if self.hovered_tableau == col_idx and not self.dragging:
                hover_surface = pygame.Surface((top_rect.width, top_rect.height), pygame.SRCALPHA)
                hover_surface.fill((0, 255, 255, 40))
                self.screen.blit(hover_surface, top_rect.topleft)
            
            for row_idx, card in enumerate(pile):
                rect = self._card_rect_in_tableau(col_idx, row_idx)
                if self.dragging and card in self.dragged_cards:
                    # Dragged cards are drawn later
                    continue
                
                # Highlight valid drop zones when dragging
                if self.dragging and self.dragged_cards and row_idx == len(pile) - 1:
                    moving = self.dragged_cards[0]
                    if self._can_place_on_tableau(moving, card):
                        highlight_surface = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
                        highlight_surface.fill((0, 255, 0, 60))
                        self.screen.blit(highlight_surface, rect.topleft)
                
                if card.face_up:
                    self._draw_card(card, rect)
                else:
                    self._draw_card_back(rect)

        # Draw dragged cards on top with enhanced shadow
        if self.dragging and self.dragged_cards:
            mx, my = pygame.mouse.get_pos()
            base_x = mx - self.drag_offset[0]
            base_y = my - self.drag_offset[1]
            for i, card in enumerate(self.dragged_cards):
                rect = pygame.Rect(
                    base_x,
                    base_y + i * self.card_spacing_y,
                    self.card_width,
                    self.card_height,
                )
                # Enhanced shadow for dragged cards
                shadow_offset = int(5 * self.scale)
                shadow_rect = pygame.Rect(rect.x + shadow_offset, rect.y + shadow_offset, rect.width, rect.height)
                shadow_surface = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
                shadow_surface.fill((0, 0, 0, 150))
                self.screen.blit(shadow_surface, shadow_rect.topleft)
                # Draw card with slight scale up for emphasis
                self._draw_card(card, rect)
                # Highlight border
                pygame.draw.rect(self.screen, COLOR_YELLOW, rect, 3)

        # Draw status / stats strip to the right of the play area (with labels)
        self._draw_stats_panel(body_font, small_font)
        
        # Restore clipping
        self.screen.set_clip(old_clip)

    def _draw_pile_outline(self, rect: Optional[pygame.Rect], label: str, font: pygame.font.Font) -> None:
        if not rect:
            return
        pygame.draw.rect(self.screen, COLOR_BG_TITLE, rect)
        pygame.draw.rect(self.screen, COLOR_CYAN, rect, 2)
        text = font.render(label, True, COLOR_CYAN)
        self.screen.blit(text, (rect.x + 4, rect.y + 4))

    def _draw_empty_slot(self, rect: pygame.Rect) -> None:
        """Draw an empty tableau slot."""
        pygame.draw.rect(self.screen, COLOR_BG_TITLE, rect)
        pygame.draw.rect(self.screen, COLOR_DARK_CYAN, rect, 2)
        # Dashed border effect
        dash_length = int(8 * self.scale)
        for i in range(0, rect.width, dash_length * 2):
            pygame.draw.line(self.screen, COLOR_GREY, 
                           (rect.x + i, rect.y), 
                           (rect.x + min(i + dash_length, rect.width), rect.y), 1)
            pygame.draw.line(self.screen, COLOR_GREY, 
                           (rect.x + i, rect.bottom - 1), 
                           (rect.x + min(i + dash_length, rect.width), rect.bottom - 1), 1)
        for i in range(0, rect.height, dash_length * 2):
            pygame.draw.line(self.screen, COLOR_GREY, 
                           (rect.x, rect.y + i), 
                           (rect.x, rect.y + min(i + dash_length, rect.height)), 1)
            pygame.draw.line(self.screen, COLOR_GREY, 
                           (rect.right - 1, rect.y + i), 
                           (rect.right - 1, rect.y + min(i + dash_length, rect.height)), 1)
    
    def _draw_empty_foundation(self, rect: pygame.Rect, suit_char: str) -> None:
        """Draw an empty foundation slot with suit indicator."""
        pygame.draw.rect(self.screen, COLOR_BG_TITLE, rect)
        pygame.draw.rect(self.screen, COLOR_DARK_CYAN, rect, 2)
        # Draw suit symbol in center
        try:
            font = pygame.font.SysFont("verdana", max(int(32 * self.scale), 20))
            suit_surface = font.render(suit_char, True, COLOR_GREY)
            suit_x = rect.x + (rect.width - suit_surface.get_width()) // 2
            suit_y = rect.y + (rect.height - suit_surface.get_height()) // 2
            self.screen.blit(suit_surface, (suit_x, suit_y))
        except:
            pass

    def _draw_card_back(self, rect: Optional[pygame.Rect]) -> None:
        """Draw a card back with shadow effect."""
        if not rect:
            return
        
        # Draw shadow offset
        shadow_offset = int(3 * self.scale)
        shadow_rect = pygame.Rect(rect.x + shadow_offset, rect.y + shadow_offset, rect.width, rect.height)
        shadow_surface = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        shadow_surface.fill((0, 0, 0, 100))
        self.screen.blit(shadow_surface, shadow_rect.topleft)
        
        if self.card_back_surface:
            self.screen.blit(self.card_back_surface, rect.topleft)
        else:
            pygame.draw.rect(self.screen, COLOR_BLACK, rect)
            pygame.draw.rect(self.screen, COLOR_CYAN, rect, 2)
            # Enhanced diagonal pattern
            center_x, center_y = rect.centerx, rect.centery
            pygame.draw.line(self.screen, COLOR_CYAN, rect.topleft, rect.bottomright, 2)
            pygame.draw.line(self.screen, COLOR_CYAN, rect.topright, rect.bottomleft, 2)
            # Add corner decorations
            corner_size = int(8 * self.scale)
            pygame.draw.circle(self.screen, COLOR_CYAN, (rect.x + corner_size, rect.y + corner_size), corner_size // 2, 1)
            pygame.draw.circle(self.screen, COLOR_CYAN, (rect.right - corner_size, rect.y + corner_size), corner_size // 2, 1)
            pygame.draw.circle(self.screen, COLOR_CYAN, (rect.x + corner_size, rect.bottom - corner_size), corner_size // 2, 1)
            pygame.draw.circle(self.screen, COLOR_CYAN, (rect.right - corner_size, rect.bottom - corner_size), corner_size // 2, 1)

    def _draw_card(self, card: Card, rect: pygame.Rect) -> None:
        """Draw a card face with shadow and enhanced styling."""
        # Draw shadow offset
        shadow_offset = int(3 * self.scale)
        shadow_rect = pygame.Rect(rect.x + shadow_offset, rect.y + shadow_offset, rect.width, rect.height)
        shadow_surface = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        shadow_surface.fill((0, 0, 0, 100))
        self.screen.blit(shadow_surface, shadow_rect.topleft)
        
        key = f"{card.rank}{card.suit}"
        surf = self.card_face_surfaces.get(key)
        if surf:
            self.screen.blit(surf, rect.topleft)
            return

        # Fallback: enhanced vector card
        bg_color = (255, 255, 255) if card.color() == "black" else (255, 245, 245)
        border_color = COLOR_RED if card.color() == "red" else COLOR_BLACK
        suit_color = COLOR_RED if card.suit in ("H", "D") else COLOR_BLACK
        
        # Card background
        pygame.draw.rect(self.screen, bg_color, rect)
        pygame.draw.rect(self.screen, border_color, rect, 2)
        
        # Inner border for depth
        inner_rect = pygame.Rect(rect.x + 2, rect.y + 2, rect.width - 4, rect.height - 4)
        pygame.draw.rect(self.screen, (240, 240, 240), inner_rect, 1)

        try:
            rank_font = pygame.font.SysFont("verdana", max(int(22 * self.scale), 14))
            suit_font = pygame.font.SysFont("verdana", max(int(24 * self.scale), 16))
            small_suit_font = pygame.font.SysFont("verdana", max(int(16 * self.scale), 10))
        except Exception:
            # Fallback to default font
            try:
                rank_font = pygame.font.Font(None, max(int(22 * self.scale), 14))
                suit_font = pygame.font.Font(None, max(int(24 * self.scale), 16))
                small_suit_font = pygame.font.Font(None, max(int(16 * self.scale), 10))
            except Exception:
                return

        label = f"{card.rank}"
        suit_char = {
            "H": "♥",
            "D": "♦",
            "C": "♣",
            "S": "♠",
        }.get(card.suit, "?")

        # Top-left rank and suit
        label_surface = rank_font.render(label, True, suit_color)
        suit_surface = suit_font.render(suit_char, True, suit_color)
        padding = int(6 * self.scale)
        self.screen.blit(label_surface, (rect.x + padding, rect.y + padding))
        self.screen.blit(suit_surface, (rect.x + padding, rect.y + padding + label_surface.get_height()))
        
        # Bottom-right rank and suit (upside down)
        bottom_label = rank_font.render(label, True, suit_color)
        bottom_suit = small_suit_font.render(suit_char, True, suit_color)
        bottom_label = pygame.transform.rotate(bottom_label, 180)
        bottom_suit = pygame.transform.rotate(bottom_suit, 180)
        self.screen.blit(bottom_label, (rect.right - padding - bottom_label.get_width(), rect.bottom - padding - bottom_label.get_height()))
        self.screen.blit(bottom_suit, (rect.right - padding - bottom_suit.get_width(), rect.bottom - padding - bottom_suit.get_height() - bottom_label.get_height()))
        
        # Center suit for face cards and 10s
        if card.rank in ("J", "Q", "K", "10"):
            center_suit = suit_font.render(suit_char, True, suit_color)
            center_x = rect.x + (rect.width - center_suit.get_width()) // 2
            center_y = rect.y + (rect.height - center_suit.get_height()) // 2
            self.screen.blit(center_suit, (center_x, center_y))

    def _draw_stats_panel(self, body_font: pygame.font.Font, small_font: pygame.font.Font) -> None:
        """Draw stats panel integrated inside the game window."""
        # Use the pre-calculated stats panel rect (inside the game window)
        panel_rect = self.stats_panel_rect
        
        # Background with border
        pygame.draw.rect(self.screen, COLOR_BG_DARK, panel_rect)
        pygame.draw.rect(self.screen, COLOR_DARK_CYAN, panel_rect, 1)
        
        # Separator line between play area and stats
        pygame.draw.line(self.screen, COLOR_CYAN,
                        (panel_rect.x, panel_rect.y),
                        (panel_rect.x, panel_rect.bottom), 2)
        
        # Title section
        title_height = int(24 * self.scale)  # 20% smaller (was 30)
        title_rect = pygame.Rect(panel_rect.x, panel_rect.y, panel_rect.width, title_height)
        pygame.draw.rect(self.screen, COLOR_BG_TITLE, title_rect)
        pygame.draw.line(self.screen, COLOR_CYAN,
                        (panel_rect.x, title_rect.bottom),
                        (panel_rect.right, title_rect.bottom), 1)
        
        title = body_font.render("GAME STATS", True, COLOR_WHITE)
        title_x = panel_rect.x + (panel_rect.width - title.get_width()) // 2
        title_y = title_rect.y + (title_height - title.get_height()) // 2
        self.screen.blit(title, (title_x, title_y))

        # Content area
        y = panel_rect.y + title_height + int(12 * self.scale)  # 20% smaller (was 15)
        line_h = int(21 * self.scale)  # 20% smaller (was 26)
        content_x = panel_rect.x + int(10 * self.scale)  # 20% smaller (was 12)
        
        # Ensure content stays within panel bounds
        max_y = panel_rect.bottom - int(8 * self.scale)  # 20% smaller (was 10)

        # Time
        if y < max_y:
            mins = int(self.elapsed_time // 60)
            secs = int(self.elapsed_time % 60)
            time_label = small_font.render("Time:", True, COLOR_CYAN)
            time_value = small_font.render(f"{mins:02d}:{secs:02d}", True, COLOR_WHITE)
            self.screen.blit(time_label, (content_x, y))
            self.screen.blit(time_value, (content_x + time_label.get_width() + int(6 * self.scale), y))  # 20% smaller (was 8)
            y += line_h

        # Moves
        if y < max_y:
            moves_label = small_font.render("Moves:", True, COLOR_CYAN)
            moves_value = small_font.render(str(self.moves), True, COLOR_WHITE)
            self.screen.blit(moves_label, (content_x, y))
            self.screen.blit(moves_value, (content_x + moves_label.get_width() + int(6 * self.scale), y))  # 20% smaller (was 8)
            y += line_h

        # Separator line
        if y < max_y:
            y += int(4 * self.scale)  # 20% smaller (was 5)
            pygame.draw.line(self.screen, COLOR_DARK_CYAN, 
                            (panel_rect.x + int(8 * self.scale), y),  # 20% smaller (was 10)
                            (panel_rect.right - int(8 * self.scale), y), 1)  # 20% smaller (was 10)
            y += int(12 * self.scale)  # 20% smaller (was 15)

        # Help section
        if y < max_y:
            help_title = small_font.render("HOW TO PLAY", True, COLOR_YELLOW)
            self.screen.blit(help_title, (content_x, y))
            y += line_h

            help_lines = [
                "• Click STOCK to draw",
                "",
                "Rules:",
                "• Build down, alt colors",
                "• Aces start foundations",
                "• Kings fill empty columns",
            ]
            
            # Calculate line height based on font to ensure everything fits
            line_spacing = int(15 * self.scale)  # 20% smaller (was 19)
            for line in help_lines:
                # Check if we have room for this line
                if y + line_spacing > max_y:
                    break
                if line:
                    color = COLOR_GREY if line.startswith("•") or line.startswith("  ") else COLOR_WHITE
                    txt = small_font.render(line, True, color)
                    # Ensure text fits within panel width
                    text_width = txt.get_width()
                    max_text_width = panel_rect.width - (content_x - panel_rect.x) - int(8 * self.scale)  # 20% smaller (was 10)
                    
                    # If text is too wide, skip rendering it (or we could wrap it, but for now skip)
                    if text_width <= max_text_width:
                        indent = int(16 * self.scale) if line.startswith("  ") else content_x  # 20% smaller (was 20)
                        self.screen.blit(txt, (indent, y))
                    # Still increment y even if we skip rendering to maintain spacing
                y += line_spacing

        # Win/Loss message at bottom
        if self.game_over:
            msg = "YOU WIN!" if self.win else "GAME OVER"
            msg_color = COLOR_GREEN if self.win else COLOR_RED
            msg_surface = body_font.render(msg, True, msg_color)
            msg_bg = pygame.Surface((msg_surface.get_width() + int(16 * self.scale),  # 20% smaller (was 20)
                                    msg_surface.get_height() + int(8 * self.scale)), pygame.SRCALPHA)  # 20% smaller (was 10)
            msg_bg.fill((*msg_color[:3], 30))
            msg_bg_x = panel_rect.x + (panel_rect.width - msg_bg.get_width()) // 2
            msg_bg_y = panel_rect.bottom - msg_bg.get_height() - int(12 * self.scale)  # 20% smaller (was 15)
            
            # Ensure message stays within bounds
            if msg_bg_y >= panel_rect.y:
                self.screen.blit(msg_bg, (msg_bg_x, msg_bg_y))
                pygame.draw.rect(self.screen, msg_color, 
                               (msg_bg_x, msg_bg_y, msg_bg.get_width(), msg_bg.get_height()), 2)
                self.screen.blit(msg_surface, 
                               (panel_rect.x + (panel_rect.width - msg_surface.get_width()) // 2, 
                                msg_bg_y + int(4 * self.scale)))  # 20% smaller (was 5)
