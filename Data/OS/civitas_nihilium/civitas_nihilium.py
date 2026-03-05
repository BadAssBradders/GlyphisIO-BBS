"""
Civitas Nihilium Game Module
Investigation and trial card/dice game for the OS Mode desktop environment.

- Uses Data/OS/civitas_nihilium/assets/ when present. Works without assets (vector fallback).
- D10 dice are rendered as stylish animated teal diamonds (no PNG required).

Expected layout:
    Data/OS/civitas_nihilium/civitas_nihilium.py
    Data/OS/civitas_nihilium/assets/cards/  (optional)
    Data/OS/civitas_nihilium/assets/bg.png  (optional)
"""

import pygame
import os
import sys
import random
import json
import math
from typing import Dict, Optional, Tuple, List

RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
SUITS = ["H", "D", "C", "S"]  # Hearts, Diamonds, Clubs, Spades


class Card:
    """Represents a playing card."""
    def __init__(self, rank: str, suit: str):
        self.rank = rank
        self.suit = suit
    
    @property
    def key(self) -> str:
        """Returns the asset key for this card (e.g., 'KS', 'AH')."""
        return f"{self.rank}{self.suit}"


def get_data_path(*path_parts) -> str:
    """
    Returns the path to the Data folder. Same behaviour as Solitaire.
    Assumes this file lives in Data/OS/civitas_nihilium.
    """
    if getattr(sys, "frozen", False):
        base_path = sys._MEIPASS  # type: ignore[attr-defined]
    else:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        os_dir = os.path.dirname(script_dir)
        data_folder = os.path.dirname(os_dir)
        base_path = data_folder
    return os.path.join(base_path, *path_parts)


def load_assets(scale: float, card_width: int, card_height: int) -> Dict:
    """
    Load all game assets (cards, dice, background).
    
    Returns a dictionary with:
    - card_face_surfaces: Dict[str, pygame.Surface] - card images keyed by "rank+suit"
    - d10_surfaces: Dict[int, pygame.Surface] - (deprecated, D10 now drawn as vector diamond)
    - bg_surface: Optional[pygame.Surface] - background image
    """
    card_face_surfaces: Dict[str, pygame.Surface] = {}
    d10_surfaces: Dict[int, pygame.Surface] = {}
    bg_surface: Optional[pygame.Surface] = None

    # Load card assets
    cards_base = get_data_path("OS", "civitas_nihilium", "assets", "cards")
    if os.path.isdir(cards_base):
        for r in RANKS:
            for s in SUITS:
                key = f"{r}{s}"
                if key in card_face_surfaces:
                    continue
                path = os.path.join(cards_base, f"card_{r}{s}.png")
                if os.path.exists(path):
                    try:
                        img = pygame.image.load(path).convert_alpha()
                        card_face_surfaces[key] = pygame.transform.smoothscale(
                            img, (card_width, card_height)
                        )
                    except Exception:
                        pass

    # Load dice assets
    dice_base = get_data_path("OS", "civitas_nihilium", "assets", "dice", "D10")
    if os.path.isdir(dice_base):
        for v in range(1, 11):
            path = os.path.join(dice_base, f"{v}.png")
            if os.path.exists(path):
                try:
                    img = pygame.image.load(path).convert_alpha()
                    sz = int(40 * scale)
                    d10_surfaces[v] = pygame.transform.scale(img, (sz, sz))  # Nearest neighbor for pixelated look
                except Exception:
                    pass

    # Load background
    bg_path = get_data_path("OS", "civitas_nihilium", "assets", "bg.png")
    if os.path.exists(bg_path):
        try:
            bg_surface = pygame.image.load(bg_path).convert_alpha()
        except Exception:
            bg_surface = None
    else:
        bg_surface = None

    # Load skyline for welcome modal
    skyline_surface: Optional[pygame.Surface] = None
    skyline_path = get_data_path("OS", "civitas_nihilium", "assets", "skyline.png")
    if os.path.exists(skyline_path):
        try:
            skyline_surface = pygame.image.load(skyline_path).convert_alpha()
        except Exception:
            skyline_surface = None

    return {
        "card_face_surfaces": card_face_surfaces,
        "d10_surfaces": d10_surfaces,
        "bg_surface": bg_surface,
        "skyline_surface": skyline_surface,
    }


class CivitasNihiliumGame:
    """
    Civitas Nihilium for OS Mode. Same public API as SolitaireGame:
    update_desktop, start, close, handle_event, draw.
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
        get_radio_music_callback=None,
        exit_app_callback=None,
    ):
        self.screen = screen
        self.scale = scale
        self.desktop_x = desktop_x
        self.desktop_y = desktop_y
        self.desktop_size = desktop_size
        self.bbs_x = bbs_x
        self.bbs_width = bbs_width
        self.get_radio_music = get_radio_music_callback or (lambda: False)
        self.exit_app_callback = exit_app_callback

        self.active = False
        self.mouse_x_percent = 0.0
        self.mouse_y_percent = 0.0

        # Card dimensions - sized to fit within 999x675 desktop area
        # Desktop is 999x675 original, cards should be ~7% width (~70px) with 1:1.4 aspect ratio
        # Using desktop_size which is already scaled, so we calculate proportionally
        self.card_width = int(self.desktop_size[0] * 0.07)
        self.card_height = int(self.card_width * 1.43)  # Standard playing card aspect ratio

        # Load assets
        assets = load_assets(self.scale, self.card_width, self.card_height)
        self.card_face_surfaces = assets["card_face_surfaces"]
        self.d10_surfaces = assets["d10_surfaces"]
        self.bg_surface = assets["bg_surface"]
        self.skyline_surface = assets.get("skyline_surface")

        # Create card back surface (face-down card)
        self.card_back_surface = self._create_card_back()

        # Fonts
        try:
            self.debug_font = pygame.font.SysFont("verdana", max(int(12 * self.scale), 10))
            self.label_font = pygame.font.SysFont("verdana", max(int(14 * self.scale), 12))
        except Exception:
            try:
                self.debug_font = pygame.font.Font(None, max(int(12 * self.scale), 10))
                self.label_font = pygame.font.Font(None, max(int(14 * self.scale), 12))
            except Exception:
                self.debug_font = None
                self.label_font = None

        # Window rect and close button
        self.window_rect: Optional[pygame.Rect] = None
        self.title_bar_rect: Optional[pygame.Rect] = None
        self.close_button_rect: Optional[pygame.Rect] = None
        self.complete_upgrades_button_rect: Optional[pygame.Rect] = None
        self.hovered_button: Optional[str] = None
        self._update_layout()
        
        # Character dice values (from image: King=4,1,3; Jack=1,6,1)
        self.king_dice = [4, 1, 3]  # Blue, Green, Magenta
        self.jack_dice = [1, 6, 1]  # Blue, Green, Magenta

        # Track card positions and face states (initialize before _setup_decks)
        self.card_positions: Dict[Card, Tuple[int, int]] = {}
        self.card_face_up: Dict[Card, bool] = {}
        self.deck_positions: Dict[str, Tuple[int, int]] = {}
        
        # Setup card decks
        self._setup_decks()
        
        # Card interaction state - completely reworked for fluid mechanics
        self.selected_cards: List[Card] = []  # Currently selected cards
        self.dragging = False
        self.drag_start_pos: Optional[Tuple[int, int]] = None
        self.drag_card_offsets: Dict[Card, Tuple[int, int]] = {}  # Offset from mouse for each dragged card
        
        # Z-order management - cards at end of list are on top
        self.card_z_order: List[Card] = []
        
        # Double-click detection
        self.last_click_time = 0
        self.last_click_pos = (0, 0)
        self.double_click_threshold = 400  # milliseconds
        
        # Selection box state
        self.selection_box_start: Optional[Tuple[int, int]] = None
        self.selection_box_end: Optional[Tuple[int, int]] = None
        self.drawing_selection_box = False
        
        # Hover state
        self.hovered_card: Optional[Card] = None
        
        # Initialize positions
        self._initialize_positions()
        
        # Setup modal state
        self.setup_complete = False
        self.setup_modal_stage = 0  # 0=welcome, 1=reputation, 2=ether, 3=ion, 4=evidence, 5=encounter
        self.show_setup_modal = True
        
        # Setup modal data
        self.welcome_choice = None  # True=yes, False=no
        self.reputation_rolls = [0, 0]  # Two blue d6 rolls
        self.reputation_choice = None  # "die1" or "die2" for King's die
        self.ether_rolls = [0, 0]  # Two green dice rolls
        self.ether_choice = None  # "king" or "jack" for first die
        self.ion_rolls = [0, 0]  # Two purple dice rolls
        self.ion_choice = None  # "king" or "jack" for first die
        self.evidence_required = 25  # Hardcoded to 25 for first crime
        self.encounter_deck: List[Card] = []  # Cards drawn for encounter deck
        self.encounter_deck_built = False
        
        # D10 die below character cards
        self.character_d10_value = 0  # 0 means not rolled yet, 1-10 when rolled
        self.character_d10_rect: Optional[pygame.Rect] = None
        
        # Character stats
        self.king_stats = {"Engagement": 3, "Analysis": 2, "Charisma": 2, "HP": 6}
        self.rookie_stats = {"Engagement": 1, "Analysis": 2, "Charisma": 2, "HP": 4}
        
        # Attached upgrades (cards attached to each character)
        self.king_attached_upgrades: List[Card] = []
        self.rookie_attached_upgrades: List[Card] = []
        
        # Draw phase after encounter deck (tutorial sequence)
        self.draw_phase_stage = 0  # 0=not started, 1=draw upgrades, 2=draw witnesses, 3=draw locations, 4=rules, 5=encounter rules, 6=end rules, 7=gameplay
        self.upgrade_slots: List[Optional[Card]] = [None, None, None]  # 3 slots to left of upgrades
        self.witness_slots: List[Optional[Card]] = [None, None, None]  # 3 slots to right of witness
        self.location_slots: List[Optional[Card]] = [None, None, None]  # 3 slots to right of location
        self.encounter_slot: Optional[Card] = None  # Single slot next to encounter deck for drawn encounter card
        
        # Timeline cards (cards placed for trials)
        self.timeline_cards: List[Card] = []
        
        # Trial system
        self.active_trial_card: Optional[Card] = None  # Card currently being trialed
        self.trial_character_choice: Optional[str] = None  # "main", "rookie", "both" (both = half bonuses)
        self.trial_skill_selected: Optional[str] = None  # "ENG", "CHA", "ANA"
        self.trial_result: Optional[int] = None  # Result of the trial roll
        self.show_trial_modal = False
        self.trial_character_buttons: Dict[str, pygame.Rect] = {}  # "main", "rookie", "both"
        self.trial_skill_buttons: Dict[str, pygame.Rect] = {}
        self.trial_cancel_btn: Optional[pygame.Rect] = None
        self.trial_d10_rect: Optional[pygame.Rect] = None
        # D10 roll animation: cycle through images before landing on result
        self.trial_d10_animating = False
        self.trial_d10_anim_start = 0
        self.trial_d10_display_value = 10  # Shown before roll (10.png)
        # Step 3: separate modal for success/failure with reward choice
        self.show_trial_result_modal = False
        self.trial_result_choice_buttons: Dict[str, pygame.Rect] = {}
        self.trial_result_confirm_rect: Optional[pygame.Rect] = None
        self.trial_result_choice: Optional[str] = None  # "evidence", "reputation", "ion"
        
        # Ether is tracked per character via green dice (king_dice[1] and jack_dice[1])
        
        # Hand system for purchased upgrades
        self.hand_cards: List[Card] = []  # Upgrades in hand waiting to be attached
        self.hand_card_skills: Dict[Card, str] = {}  # Skill enhancement choice for each card in hand
        
        # Upgrade purchase modal
        self.show_upgrade_modal = False
        
        # Crime progression and end state
        self.crime_stage = 0  # 0=25 evidence, 1=35 evidence, 2=45 evidence, 3=win
        self.show_game_over_modal = False
        self.game_over_title = ""
        self.game_over_lines: List[str] = []
        self.game_over_button_rect: Optional[pygame.Rect] = None

        self.upgrade_modal_card: Optional[Card] = None
        self.upgrade_skill_selected: Optional[str] = None  # Selected skill enhancement
        self.upgrade_slot_index: Optional[int] = None  # Which slot the card came from
        self.upgrade_skill_buttons: Dict[str, pygame.Rect] = {}
        self.upgrade_place_btn: Optional[pygame.Rect] = None
        self.upgrade_cancel_btn: Optional[pygame.Rect] = None
        
        # Game phase system
        self.game_phase = "UPGRADE"  # "UPGRADE" or "TIMELINE"
        self.phase_confirm_btn: Optional[pygame.Rect] = None
        
        # Tutorial system
        self.show_tutorial_modal = False
        self.tutorial_title = ""
        self.tutorial_message = ""
        self.tutorial_ok_button_rect: Optional[pygame.Rect] = None
        self.tutorial_completed_steps = set()  # Track which tutorial steps have been shown
        
        # Fireworks system for end game
        self.fireworks: List[Dict] = []
        self.show_fireworks = False
        
        # Flashing text for end game
        self.end_game_flash_timer = 0.0
        self.end_game_flash_visible = True
        
        # === CYBERPUNK VISUAL EFFECTS ===
        # Scanline overlay
        self.scanline_surface: Optional[pygame.Surface] = None
        self.scanline_offset = 0.0
        
        # Neon border glow animation
        self.neon_glow_time = 0.0
        self.neon_pulse_speed = 2.0  # Cycles per second
        
        # Ambient data particles (floating bits)
        self.ambient_particles: List[Dict] = []
        self.particle_spawn_timer = 0.0
        self._init_ambient_particles()
        
        # Card hover glow effect
        self.card_hover_glow_time = 0.0
        
        # Dice roll particle burst
        self.dice_particles: List[Dict] = []
        
        # Animated grid background
        self.grid_offset = 0.0
        self.grid_speed = 15.0  # Pixels per second
        
        # Glitch effect for damage/failures
        self.glitch_active = False
        self.glitch_timer = 0.0
        self.glitch_duration = 0.3
        self.glitch_intensity = 0.0
        
        # CRT flicker effect
        self.crt_flicker_time = 0.0
        
        # Crime investigation congratulations
        self.show_crime_congrats_modal = False
        self.crime_congrats_title = ""
        self.crime_congrats_message = ""
        self.crime_congrats_button_rect: Optional[pygame.Rect] = None
        
        # Modal button rects
        self.modal_yes_rect: Optional[pygame.Rect] = None
        self.modal_no_rect: Optional[pygame.Rect] = None
        self.modal_roll_button_rect: Optional[pygame.Rect] = None
        self.modal_continue_rect: Optional[pygame.Rect] = None
        self.modal_die1_rect: Optional[pygame.Rect] = None
        self.modal_die2_rect: Optional[pygame.Rect] = None

    def _update_layout(self) -> None:
        window_width = self.desktop_size[0]
        window_height = self.desktop_size[1]
        window_x = self.desktop_x
        window_y = self.desktop_y

        self.window_rect = pygame.Rect(window_x, window_y, window_width, window_height)
        
        # Title bar and close button
        title_bar_height = int(35 * self.scale)
        self.title_bar_rect = pygame.Rect(window_x, window_y, window_width, title_bar_height)

        close_w = int(60 * self.scale)
        close_h = int(25 * self.scale)
        self.close_button_rect = pygame.Rect(
            window_x + window_width - close_w - int(15 * self.scale),
            window_y + (title_bar_height - close_h) // 2,
            close_w, close_h
        )
        
        # Complete upgrades button (to the left of close button)
        complete_w = int(200 * self.scale)
        complete_h = int(28 * self.scale)
        button_gap = int(10 * self.scale)
        self.complete_upgrades_button_rect = pygame.Rect(
            window_x + window_width - close_w - int(15 * self.scale) - complete_w - button_gap,
            window_y + (title_bar_height - complete_h) // 2,
            complete_w, complete_h
        )

    def _create_card_back(self) -> pygame.Surface:
        """Load or create a face-down card back surface."""
        # Try to load card_back.png from assets/cards
        card_back_path = get_data_path("OS", "civitas_nihilium", "assets", "cards", "card_back.png")
        if os.path.exists(card_back_path):
            try:
                back_img = pygame.image.load(card_back_path).convert_alpha()
                back = pygame.transform.smoothscale(back_img, (self.card_width, self.card_height))
                return back
            except Exception:
                pass
        
        # Fallback: create a CYBERPUNK vector card back!
        back = pygame.Surface((self.card_width, self.card_height), pygame.SRCALPHA)
        
        # Gradient background (dark purple to dark blue)
        for y in range(self.card_height):
            progress = y / self.card_height
            r = int(20 + 15 * progress)
            g = int(15 + 10 * (1 - progress))
            b = int(40 + 30 * progress)
            pygame.draw.line(back, (r, g, b, 255), (0, y), (self.card_width, y))
        
        # Center emblem - stylized "CN" for Civitas Nihilium
        center_x = self.card_width // 2
        center_y = self.card_height // 2
        emblem_size = min(self.card_width, self.card_height) // 3
        
        # Draw diamond shape
        points = [
            (center_x, center_y - emblem_size // 2),
            (center_x + emblem_size // 2, center_y),
            (center_x, center_y + emblem_size // 2),
            (center_x - emblem_size // 2, center_y),
        ]
        pygame.draw.polygon(back, (0, 150, 200, 150), points)
        pygame.draw.polygon(back, (0, 255, 255, 255), points, 2)
        
        # Corner accents
        corner_size = int(10 * self.scale)
        accent_color = (255, 0, 255, 200)
        # Top-left
        pygame.draw.line(back, accent_color, (4, 4), (4 + corner_size, 4), 2)
        pygame.draw.line(back, accent_color, (4, 4), (4, 4 + corner_size), 2)
        # Top-right
        pygame.draw.line(back, accent_color, (self.card_width - 5, 4), (self.card_width - 5 - corner_size, 4), 2)
        pygame.draw.line(back, accent_color, (self.card_width - 5, 4), (self.card_width - 5, 4 + corner_size), 2)
        # Bottom-left
        pygame.draw.line(back, accent_color, (4, self.card_height - 5), (4 + corner_size, self.card_height - 5), 2)
        pygame.draw.line(back, accent_color, (4, self.card_height - 5), (4, self.card_height - 5 - corner_size), 2)
        # Bottom-right
        pygame.draw.line(back, accent_color, (self.card_width - 5, self.card_height - 5), (self.card_width - 5 - corner_size, self.card_height - 5), 2)
        pygame.draw.line(back, accent_color, (self.card_width - 5, self.card_height - 5), (self.card_width - 5, self.card_height - 5 - corner_size), 2)
        
        # Neon border
        pygame.draw.rect(back, (0, 255, 255, 255), (0, 0, self.card_width, self.card_height), 2)
        
        return back

    def _setup_decks(self) -> None:
        """Separate cards into different decks according to game rules."""
        # Create full deck
        all_cards = [Card(r, s) for r in RANKS for s in SUITS]
        
        # Remove King and Jack of Spades (these are character cards, placed separately)
        self.king_spades = None
        self.jack_spades = None
        for card in all_cards[:]:
            if card.rank == "K" and card.suit == "S":
                self.king_spades = card
                all_cards.remove(card)
            elif card.rank == "J" and card.suit == "S":
                self.jack_spades = card
                all_cards.remove(card)
        
        # Separate upgrade cards (A, 2, 3, 4 of all suits)
        upgrade_cards = []
        upgrade_ranks = ["A", "2", "3", "4"]
        for card in all_cards[:]:
            if card.rank in upgrade_ranks:
                upgrade_cards.append(card)
                all_cards.remove(card)
        
        # Separate remaining cards into witness (Diamonds + Hearts) and location (Spades + Clubs)
        witness_cards = []
        location_cards = []
        for card in all_cards:
            if card.suit in ("D", "H"):  # Diamonds and Hearts are Witnesses
                witness_cards.append(card)
            elif card.suit in ("S", "C"):  # Spades and Clubs are Locations
                location_cards.append(card)
        
        # Shuffle decks
        random.shuffle(witness_cards)
        random.shuffle(location_cards)
        
        # Store decks
        self.upgrade_cards = upgrade_cards
        self.witness_deck = witness_cards
        self.location_deck = location_cards
        
        # Initialize face states
        for card in upgrade_cards:
            self.card_face_up[card] = False  # Face down
        for card in witness_cards:
            self.card_face_up[card] = False  # Face down
        for card in location_cards:
            self.card_face_up[card] = False  # Face down
        if self.king_spades:
            self.card_face_up[self.king_spades] = True
        if self.jack_spades:
            self.card_face_up[self.jack_spades] = True

    def _initialize_positions(self) -> None:
        """Initialize card and deck positions."""
        # Account for title bar offset
        title_bar_offset = self.title_bar_rect.height if self.title_bar_rect else 0
        
        # Character cards (aligned with Location deck at Y 38%)
        if self.king_spades:
            kx, ky = self._percent_to_pixel(9.0, 38.0)
            ky += title_bar_offset
            self.card_positions[self.king_spades] = (kx, ky)
        if self.jack_spades:
            jx, jy = self._percent_to_pixel(24.0, 38.0)
            jy += title_bar_offset
            self.card_positions[self.jack_spades] = (jx, jy)
        
        # Upgrade deck position
        upgrade_x, upgrade_y = self._percent_to_pixel(34.0, 5.0)
        upgrade_y += title_bar_offset
        self.deck_positions["upgrade"] = (upgrade_x, upgrade_y)
        # Position upgrade cards in a tidy stack (minimal offset like encounter deck)
        for i, card in enumerate(self.upgrade_cards):
            offset_x = upgrade_x + (i * 1)  # Tighter stack
            offset_y = upgrade_y + (i * 1)
            self.card_positions[card] = (offset_x, offset_y)
        
        # Witness deck position
        witness_x, witness_y = self._percent_to_pixel(50.0, 11.0)
        witness_y += title_bar_offset
        self.deck_positions["witness"] = (witness_x, witness_y)
        # Position witness cards in a tidy stack
        for i, card in enumerate(self.witness_deck):
            offset_x = witness_x + (i * 1)  # Tighter stack
            offset_y = witness_y + (i * 1)
            self.card_positions[card] = (offset_x, offset_y)
        
        # Location deck position
        location_x, location_y = self._percent_to_pixel(50.0, 40.0)
        location_y += title_bar_offset
        self.deck_positions["location"] = (location_x, location_y)
        # Position location cards in a tidy stack
        for i, card in enumerate(self.location_deck):
            offset_x = location_x + (i * 1)  # Tighter stack
            offset_y = location_y + (i * 1)
            self.card_positions[card] = (offset_x, offset_y)

    def _percent_to_pixel(self, x_percent: float, y_percent: float) -> Tuple[int, int]:
        """Convert percentage coordinates to pixel coordinates."""
        if not self.window_rect:
            return (0, 0)
        x = int(self.window_rect.x + (x_percent / 100.0) * self.window_rect.width)
        y = int(self.window_rect.y + (y_percent / 100.0) * self.window_rect.height)
        return (x, y)

    def _pixel_to_percent(self, x: int, y: int) -> Tuple[float, float]:
        """Convert pixel coordinates to percentage coordinates."""
        if not self.window_rect or self.window_rect.width == 0 or self.window_rect.height == 0:
            return (0.0, 0.0)
        rel_x = x - self.window_rect.x
        rel_y = y - self.window_rect.y
        x_percent = (rel_x / self.window_rect.width) * 100.0
        y_percent = (rel_y / self.window_rect.height) * 100.0
        return (x_percent, y_percent)

    def _save_positions_to_json(self) -> None:
        """Save all card positions to a JSON file."""
        if not self.window_rect:
            return
        
        positions_data = {
            "character_cards": {},
            "upgrade_deck": {
                "position": None,
                "cards": []
            },
            "witness_deck": {
                "position": None,
                "cards": []
            },
            "location_deck": {
                "position": None,
                "cards": []
            }
        }
        
        # Save character cards
        if self.king_spades and self.king_spades in self.card_positions:
            kx, ky = self.card_positions[self.king_spades]
            kx_pct, ky_pct = self._pixel_to_percent(kx, ky)
            positions_data["character_cards"]["king_spades"] = {
                "x_percent": round(kx_pct, 2),
                "y_percent": round(ky_pct, 2)
            }
        
        if self.jack_spades and self.jack_spades in self.card_positions:
            jx, jy = self.card_positions[self.jack_spades]
            jx_pct, jy_pct = self._pixel_to_percent(jx, jy)
            positions_data["character_cards"]["jack_spades"] = {
                "x_percent": round(jx_pct, 2),
                "y_percent": round(jy_pct, 2)
            }
        
        # Save upgrade deck
        if "upgrade" in self.deck_positions:
            dx, dy = self.deck_positions["upgrade"]
            dx_pct, dy_pct = self._pixel_to_percent(dx, dy)
            positions_data["upgrade_deck"]["position"] = {
                "x_percent": round(dx_pct, 2),
                "y_percent": round(dy_pct, 2)
            }
            
            for i, card in enumerate(self.upgrade_cards):
                if card in self.card_positions:
                    cx, cy = self.card_positions[card]
                    cx_pct, cy_pct = self._pixel_to_percent(cx, cy)
                    positions_data["upgrade_deck"]["cards"].append({
                        "index": i,
                        "x_percent": round(cx_pct, 2),
                        "y_percent": round(cy_pct, 2)
                    })
        
        # Save witness deck
        if "witness" in self.deck_positions:
            dx, dy = self.deck_positions["witness"]
            dx_pct, dy_pct = self._pixel_to_percent(dx, dy)
            positions_data["witness_deck"]["position"] = {
                "x_percent": round(dx_pct, 2),
                "y_percent": round(dy_pct, 2)
            }
            
            for i, card in enumerate(self.witness_deck):
                if card in self.card_positions:
                    cx, cy = self.card_positions[card]
                    cx_pct, cy_pct = self._pixel_to_percent(cx, cy)
                    positions_data["witness_deck"]["cards"].append({
                        "index": i,
                        "x_percent": round(cx_pct, 2),
                        "y_percent": round(cy_pct, 2)
                    })
        
        # Save location deck
        if "location" in self.deck_positions:
            dx, dy = self.deck_positions["location"]
            dx_pct, dy_pct = self._pixel_to_percent(dx, dy)
            positions_data["location_deck"]["position"] = {
                "x_percent": round(dx_pct, 2),
                "y_percent": round(dy_pct, 2)
            }
            
            for i, card in enumerate(self.location_deck):
                if card in self.card_positions:
                    cx, cy = self.card_positions[card]
                    cx_pct, cy_pct = self._pixel_to_percent(cx, cy)
                    positions_data["location_deck"]["cards"].append({
                        "index": i,
                        "x_percent": round(cx_pct, 2),
                        "y_percent": round(cy_pct, 2)
                    })
        
        # Save to JSON file
        json_path = get_data_path("OS", "civitas_nihilium", "card_positions.json")
        try:
            with open(json_path, 'w') as f:
                json.dump(positions_data, f, indent=2)
            print(f"Card positions saved to: {json_path}")
        except Exception as e:
            print(f"Error saving card positions: {e}")

    def _draw_d10_diamond(self, value: int, rect: pygame.Rect, animating: bool = False, 
                          can_roll: bool = False, hovered: bool = False) -> None:
        """Draw a stylish teal diamond D10 with the given value (1-10).
        
        Args:
            value: The number to display (1-10)
            rect: The bounding rectangle for the diamond
            animating: Whether the die is currently rolling (triggers spin animation)
            can_roll: Whether the die can be clicked to roll
            hovered: Whether the mouse is hovering over the die
        """
        import math
        
        # Animation time
        anim_time = self.neon_glow_time
        
        # Calculate diamond center and size
        cx, cy = rect.centerx, rect.centery
        half_w = rect.width // 2
        half_h = rect.height // 2
        
        # Teal color scheme
        teal_base = (0, 180, 180)
        teal_light = (0, 255, 255)
        teal_dark = (0, 120, 130)
        
        # Pulsing glow effect
        pulse = (math.sin(anim_time * 3) + 1) / 2
        
        # Animation effects when rolling
        if animating:
            # Spinning rotation effect
            spin_angle = anim_time * 15  # Fast spin
            scale_pulse = 0.9 + 0.2 * abs(math.sin(anim_time * 8))  # Size pulsing
            half_w = int(half_w * scale_pulse)
            half_h = int(half_h * scale_pulse)
            # Color shift during animation
            r_shift = int(50 * abs(math.sin(anim_time * 10)))
            teal_base = (r_shift, 180 + int(40 * pulse), 180 + int(40 * pulse))
            teal_light = (r_shift + 50, 255, 255)
        
        # Diamond points (top, right, bottom, left)
        points = [
            (cx, cy - half_h),  # Top
            (cx + half_w, cy),  # Right
            (cx, cy + half_h),  # Bottom
            (cx - half_w, cy),  # Left
        ]
        
        # Outer glow effect
        glow_size = int(6 + 4 * pulse)
        glow_surf = pygame.Surface((rect.width + glow_size * 2, rect.height + glow_size * 2), pygame.SRCALPHA)
        glow_points = [
            (half_w + glow_size, glow_size),
            (rect.width + glow_size, half_h + glow_size),
            (half_w + glow_size, rect.height + glow_size),
            (glow_size, half_h + glow_size),
        ]
        glow_alpha = int(80 + 60 * pulse) if (animating or hovered) else int(40 + 30 * pulse)
        pygame.draw.polygon(glow_surf, (*teal_light, glow_alpha), glow_points)
        self.screen.blit(glow_surf, (rect.x - glow_size, rect.y - glow_size))
        
        # Main diamond body with gradient effect
        diamond_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        diamond_points = [
            (half_w, 0),
            (rect.width, half_h),
            (half_w, rect.height),
            (0, half_h),
        ]
        
        # Draw layered gradient (darker at bottom for 3D effect)
        for i in range(3):
            shrink = i * 4
            inner_points = [
                (half_w, shrink),
                (rect.width - shrink, half_h),
                (half_w, rect.height - shrink),
                (shrink, half_h),
            ]
            layer_color = (
                teal_dark[0] + (teal_base[0] - teal_dark[0]) * i // 3,
                teal_dark[1] + (teal_base[1] - teal_dark[1]) * i // 3,
                teal_dark[2] + (teal_base[2] - teal_dark[2]) * i // 3,
                255
            )
            pygame.draw.polygon(diamond_surf, layer_color, inner_points)
        
        self.screen.blit(diamond_surf, rect.topleft)
        
        # Highlight line (top-left facet shine)
        highlight_alpha = int(100 + 80 * pulse)
        highlight_points = [
            (cx, cy - half_h + 3),
            (cx - half_w + 8, cy),
            (cx - half_w // 2, cy - half_h // 2),
        ]
        highlight_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        pygame.draw.polygon(highlight_surf, (255, 255, 255, highlight_alpha), [
            (half_w, 3),
            (8, half_h),
            (half_w // 2 + 4, half_h // 2),
        ])
        self.screen.blit(highlight_surf, rect.topleft)
        
        # Neon border
        border_color = (255, 255, 0) if hovered else teal_light if (animating or can_roll) else (200, 255, 255)
        border_width = 3 if (hovered or animating) else 2
        pygame.draw.polygon(self.screen, border_color, points, border_width)
        
        # Inner border for depth
        inner_shrink = 4
        inner_points = [
            (cx, cy - half_h + inner_shrink),
            (cx + half_w - inner_shrink, cy),
            (cx, cy + half_h - inner_shrink),
            (cx - half_w + inner_shrink, cy),
        ]
        pygame.draw.polygon(self.screen, (*teal_dark, 150), inner_points, 1)
        
        # Number display
        display_val = value if 1 <= value <= 10 else 10
        if animating:
            # Shimmer effect on number during animation
            text_alpha = int(180 + 75 * abs(math.sin(anim_time * 12)))
        else:
            text_alpha = 255
        
        # Draw number with shadow for depth
        if self.label_font:
            # Shadow
            num_text = str(display_val)
            shadow_surf = self.label_font.render(num_text, True, (0, 50, 50))
            shadow_rect = shadow_surf.get_rect(center=(cx + 2, cy + 2))
            shadow_surf.set_alpha(120)
            self.screen.blit(shadow_surf, shadow_rect)
            
            # Main number
            num_surf = self.label_font.render(num_text, True, (255, 255, 255))
            num_surf.set_alpha(text_alpha)
            num_rect = num_surf.get_rect(center=(cx, cy))
            self.screen.blit(num_surf, num_rect)
        
        # Sparkle particles during animation
        if animating:
            for _ in range(2):
                sparkle_x = cx + random.randint(-half_w + 5, half_w - 5)
                sparkle_y = cy + random.randint(-half_h + 5, half_h - 5)
                sparkle_size = random.randint(1, 3)
                sparkle_alpha = random.randint(100, 255)
                sparkle_surf = pygame.Surface((sparkle_size * 2, sparkle_size * 2), pygame.SRCALPHA)
                pygame.draw.circle(sparkle_surf, (255, 255, 255, sparkle_alpha), 
                                 (sparkle_size, sparkle_size), sparkle_size)
                self.screen.blit(sparkle_surf, (sparkle_x - sparkle_size, sparkle_y - sparkle_size))

    def _draw_d6(self, value: int, color: Tuple[int, int, int], rect: pygame.Rect) -> None:
        """Draw a cyberpunk-styled D6 die with pips showing the value (1-6)."""
        import math
        
        # Animated glow effect based on time
        glow_pulse = (math.sin(self.neon_glow_time * 2 + hash(color) * 0.1) + 1) / 2
        
        # Draw outer glow
        glow_size = int(3 + 2 * glow_pulse)
        glow_rect = pygame.Rect(rect.x - glow_size, rect.y - glow_size, 
                                rect.width + glow_size * 2, rect.height + glow_size * 2)
        glow_surf = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
        glow_alpha = int(60 * glow_pulse)
        pygame.draw.rect(glow_surf, (*color, glow_alpha), (0, 0, glow_rect.width, glow_rect.height), glow_size)
        self.screen.blit(glow_surf, glow_rect.topleft)
        
        # Die background with subtle gradient
        die_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        for y in range(rect.height):
            progress = y / rect.height
            # Darken towards bottom for 3D effect
            r = int(color[0] * (0.8 + 0.2 * (1 - progress)))
            g = int(color[1] * (0.8 + 0.2 * (1 - progress)))
            b = int(color[2] * (0.8 + 0.2 * (1 - progress)))
            pygame.draw.line(die_surf, (r, g, b, 255), (0, y), (rect.width, y))
        self.screen.blit(die_surf, rect.topleft)
        
        # Neon border
        pygame.draw.rect(self.screen, (255, 255, 255), rect, 2)
        
        # Draw pips based on value (1-6) with glow
        pip_size = int(4 * self.scale)
        pip_radius = pip_size // 2
        center_x = rect.centerx
        center_y = rect.centery
        margin = int(8 * self.scale)
        
        pip_positions = {
            1: [(center_x, center_y)],
            2: [(center_x - margin, center_y - margin), (center_x + margin, center_y + margin)],
            3: [(center_x - margin, center_y - margin), (center_x, center_y), (center_x + margin, center_y + margin)],
            4: [(center_x - margin, center_y - margin), (center_x + margin, center_y - margin),
                (center_x - margin, center_y + margin), (center_x + margin, center_y + margin)],
            5: [(center_x - margin, center_y - margin), (center_x + margin, center_y - margin),
                (center_x, center_y),
                (center_x - margin, center_y + margin), (center_x + margin, center_y + margin)],
            6: [(center_x - margin, center_y - margin), (center_x + margin, center_y - margin),
                (center_x - margin, center_y), (center_x + margin, center_y),
                (center_x - margin, center_y + margin), (center_x + margin, center_y + margin)],
        }
        
        # Draw pips with glow for values 1-6
        display_value = max(1, min(6, value))
        for pos in pip_positions.get(display_value, []):
            # Pip glow
            glow_surf = pygame.Surface((pip_radius * 4, pip_radius * 4), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (255, 255, 255, int(80 * glow_pulse)), 
                             (pip_radius * 2, pip_radius * 2), pip_radius * 2)
            self.screen.blit(glow_surf, (pos[0] - pip_radius * 2, pos[1] - pip_radius * 2))
            # Main pip
            pygame.draw.circle(self.screen, (255, 255, 255), pos, pip_radius)

    def _draw_card(self, card: Card, x: int, y: int, face_up: bool = True) -> None:
        """Draw a card at the specified position."""
        if face_up:
            key = card.key
            if key in self.card_face_surfaces:
                # Scale the card surface to the new size
                scaled_card = pygame.transform.smoothscale(
                    self.card_face_surfaces[key],
                    (self.card_width, self.card_height)
                )
                self.screen.blit(scaled_card, (x, y))
            else:
                # Fallback: draw simple card
                pygame.draw.rect(self.screen, (255, 250, 250), (x, y, self.card_width, self.card_height))
                pygame.draw.rect(self.screen, (0, 0, 0), (x, y, self.card_width, self.card_height), 2)
                if self.debug_font:
                    text = self.debug_font.render(card.key, True, (0, 0, 0))
                    self.screen.blit(text, (x + 5, y + 5))
        else:
            # Draw face-down card (scale the back surface)
            scaled_back = pygame.transform.smoothscale(
                self.card_back_surface,
                (self.card_width, self.card_height)
            )
            self.screen.blit(scaled_back, (x, y))

    def _advance_text_y(self, y_cursor: int, text_surface: pygame.Surface, min_gap: int = 4) -> int:
        """
        Advance y_cursor by at least the text height plus minimum gap.
        Ensures text never overlaps by always using actual text height.
        
        Args:
            y_cursor: Current Y position
            text_surface: The text surface that was just drawn
            min_gap: Minimum gap in pixels (scaled)
        
        Returns:
            New y_cursor position
        """
        text_height = text_surface.get_height()
        gap = max(int(min_gap * self.scale), 2)  # Ensure at least 2 pixels gap
        return y_cursor + text_height + gap

    def update_desktop(
        self,
        desktop_x: int,
        desktop_y: int,
        desktop_size: Tuple[int, int],
        health_monitor_y: int,
    ) -> None:
        self.desktop_x = desktop_x
        self.desktop_y = desktop_y
        self.desktop_size = desktop_size
        
        # Recalculate card dimensions based on new desktop size
        old_card_width = self.card_width
        self.card_width = int(self.desktop_size[0] * 0.07)
        self.card_height = int(self.card_width * 1.43)
        
        # Reload assets if card dimensions changed significantly
        if abs(self.card_width - old_card_width) > 2:
            assets = load_assets(self.scale, self.card_width, self.card_height)
            self.card_face_surfaces = assets["card_face_surfaces"]
            self.d10_surfaces = assets["d10_surfaces"]
            self.card_back_surface = self._create_card_back()
        
        self._update_layout()

    def start(self) -> None:
        self.active = True

    def close(self) -> None:
        self.active = False
    
    def update(self, dt: float) -> None:
        """Update game state - called each frame."""
        if not self.active:
            return
        
        # Update fireworks
        if self.show_fireworks:
            self._update_fireworks(dt)
        
        # Update flashing text for end game
        if self.show_game_over_modal and self.show_fireworks:
            self.end_game_flash_timer += dt
            # Flash every 0.3 seconds
            if self.end_game_flash_timer >= 0.3:
                self.end_game_flash_timer = 0.0
                self.end_game_flash_visible = not self.end_game_flash_visible
        
        # === UPDATE CYBERPUNK VISUAL EFFECTS ===
        # Neon border glow animation
        self.neon_glow_time += dt
        
        # Card hover glow
        self.card_hover_glow_time += dt
        
        # Animated grid
        self.grid_offset += self.grid_speed * dt
        
        # Scanline offset (subtle movement)
        self.scanline_offset += dt * 0.5
        
        # CRT flicker
        self.crt_flicker_time += dt
        
        # Ambient particles
        self._update_ambient_particles(dt)
        
        # Dice particles
        self._update_dice_particles(dt)
        
        # Glitch effect
        self._update_glitch(dt)

    def _init_z_order(self) -> None:
        """Initialize z-order with all cards."""
        self.card_z_order = []
        # Add cards in order: decks first (bottom), then character cards (top)
        self.card_z_order.extend(self.upgrade_cards)
        self.card_z_order.extend(self.witness_deck)
        self.card_z_order.extend(self.location_deck)
        self.card_z_order.extend(self.encounter_deck)
        if self.jack_spades:
            self.card_z_order.append(self.jack_spades)
        if self.king_spades:
            self.card_z_order.append(self.king_spades)

    def _bring_to_front(self, cards: List[Card]) -> None:
        """Bring specified cards to the front of z-order."""
        for card in cards:
            if card in self.card_z_order:
                self.card_z_order.remove(card)
            self.card_z_order.append(card)

    def _get_card_at_position(self, x: int, y: int) -> Optional[Card]:
        """Get the topmost card at the given position using z-order."""
        # Check in reverse z-order (top to bottom)
        for card in reversed(self.card_z_order):
            if card in self.card_positions:
                cx, cy = self.card_positions[card]
                if cx <= x <= cx + self.card_width and cy <= y <= cy + self.card_height:
                    return card
        return None

    def _get_cards_in_rect(self, x1: int, y1: int, x2: int, y2: int) -> List[Card]:
        """Get all cards that intersect with the given rectangle."""
        box_left = min(x1, x2)
        box_right = max(x1, x2)
        box_top = min(y1, y2)
        box_bottom = max(y1, y2)
        
        selected = []
        for card in self.card_z_order:
            if card in self.card_positions:
                cx, cy = self.card_positions[card]
                card_right = cx + self.card_width
                card_bottom = cy + self.card_height
                
                # Check if card intersects with box
                if not (card_right < box_left or cx > box_right or card_bottom < box_top or cy > box_bottom):
                    selected.append(card)
        return selected

    def _get_deck_for_card(self, card: Card) -> Optional[str]:
        """Get which deck a card belongs to."""
        if card in self.upgrade_cards:
            return "upgrade"
        elif card in self.witness_deck:
            return "witness"
        elif card in self.location_deck:
            return "location"
        elif card in self.encounter_deck:
            return "encounter"
        return None

    def _get_deck_cards(self, deck_name: str) -> List[Card]:
        """Get all cards in a deck."""
        if deck_name == "upgrade":
            return self.upgrade_cards[:]
        elif deck_name == "witness":
            return self.witness_deck[:]
        elif deck_name == "location":
            return self.location_deck[:]
        elif deck_name == "encounter":
            return self.encounter_deck[:]
        return []

    def _select_card(self, card: Card, add_to_selection: bool = False) -> None:
        """Select a card, optionally adding to existing selection."""
        if add_to_selection:
            if card not in self.selected_cards:
                self.selected_cards.append(card)
        else:
            self.selected_cards = [card]
        self._bring_to_front(self.selected_cards)

    def _select_cards(self, cards: List[Card], add_to_selection: bool = False) -> None:
        """Select multiple cards."""
        if add_to_selection:
            for card in cards:
                if card not in self.selected_cards:
                    self.selected_cards.append(card)
        else:
            self.selected_cards = cards[:]
        self._bring_to_front(self.selected_cards)

    def _clear_selection(self) -> None:
        """Clear the current selection."""
        self.selected_cards = []

    def _start_drag(self, mx: int, my: int) -> None:
        """Start dragging selected cards."""
        if not self.selected_cards:
            return
        self.dragging = True
        self.drag_start_pos = (mx, my)
        self.drag_card_offsets = {}
        for card in self.selected_cards:
            if card in self.card_positions:
                cx, cy = self.card_positions[card]
                self.drag_card_offsets[card] = (mx - cx, my - cy)

    def _update_drag(self, mx: int, my: int) -> None:
        """Update card positions while dragging."""
        if not self.dragging or not self.selected_cards:
            return
        
        for card in self.selected_cards:
            if card in self.drag_card_offsets:
                offset_x, offset_y = self.drag_card_offsets[card]
                new_x = mx - offset_x
                new_y = my - offset_y
                
                # Keep within window bounds
                if self.window_rect:
                    new_x = max(self.window_rect.x, min(new_x, self.window_rect.right - self.card_width))
                    new_y = max(self.window_rect.y, min(new_y, self.window_rect.bottom - self.card_height))
                
                self.card_positions[card] = (new_x, new_y)

    def _end_drag(self) -> None:
        """End dragging."""
        self.dragging = False
        self.drag_start_pos = None
        self.drag_card_offsets = {}

    def _flip_card(self, card: Card) -> None:
        """Flip a card face up/down."""
        if card in self.card_face_up:
            self.card_face_up[card] = not self.card_face_up[card]

    def _flip_selected_cards(self) -> None:
        """Flip all selected cards."""
        for card in self.selected_cards:
            self._flip_card(card)

    def _handle_setup_modal_event(self, event: pygame.event.Event) -> bool:
        """Handle events for setup modals."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            print(f"[DEBUG] Modal click at ({mx}, {my}), stage: {self.setup_modal_stage}")
            
            # Welcome modal (PLAY = begin game, QUIT = close entire app)
            if self.setup_modal_stage == 0:
                if self.modal_yes_rect and self.modal_yes_rect.collidepoint(mx, my):
                    self.welcome_choice = True
                    self.setup_modal_stage = 1
                    return True
                elif self.modal_no_rect and self.modal_no_rect.collidepoint(mx, my):
                    self.welcome_choice = False
                    self.show_setup_modal = False
                    self.close()
                    if self.exit_app_callback:
                        self.exit_app_callback()
                    else:
                        pygame.quit()
                        sys.exit(0)
                    return True
            
            # Reputation modal
            elif self.setup_modal_stage == 1:
                print(f"[DEBUG] Reputation modal - Roll rect: {self.modal_roll_button_rect}, Continue rect: {self.modal_continue_rect}")
                print(f"[DEBUG] Reputation rolls: {self.reputation_rolls}, choice: {self.reputation_choice}")
                if self.modal_roll_button_rect and self.modal_roll_button_rect.collidepoint(mx, my):
                    print("[DEBUG] ROLL button clicked")
                    if self.reputation_rolls[0] == 0 or self.reputation_rolls[1] == 0:
                        self.reputation_rolls[0] = random.randint(1, 6)
                        self.reputation_rolls[1] = random.randint(1, 6)
                        print(f"[DEBUG] Rolled: {self.reputation_rolls}")
                        # Spawn dice particles for visual flair!
                        if self.modal_die1_rect:
                            self._spawn_dice_particles(self.modal_die1_rect.centerx, self.modal_die1_rect.centery, (0, 100, 255))
                        if self.modal_die2_rect:
                            self._spawn_dice_particles(self.modal_die2_rect.centerx, self.modal_die2_rect.centery, (0, 100, 255))
                    return True
                elif self.modal_die1_rect and self.modal_die1_rect.collidepoint(mx, my):
                    print("[DEBUG] Die 1 clicked")
                    if self.reputation_rolls[0] > 0 and self.reputation_rolls[1] > 0:
                        self.reputation_choice = "die1"
                        self.king_dice[0] = self.reputation_rolls[0]
                        self.jack_dice[0] = self.reputation_rolls[1]
                        print(f"[DEBUG] Assigned - King: {self.king_dice[0]}, Rookie: {self.jack_dice[0]}")
                    return True
                elif self.modal_die2_rect and self.modal_die2_rect.collidepoint(mx, my):
                    print("[DEBUG] Die 2 clicked")
                    if self.reputation_rolls[0] > 0 and self.reputation_rolls[1] > 0:
                        self.reputation_choice = "die2"
                        self.king_dice[0] = self.reputation_rolls[1]
                        self.jack_dice[0] = self.reputation_rolls[0]
                        print(f"[DEBUG] Assigned - King: {self.king_dice[0]}, Rookie: {self.jack_dice[0]}")
                    return True
                elif self.modal_continue_rect and self.modal_continue_rect.collidepoint(mx, my):
                    print(f"[DEBUG] CONTINUE button clicked, reputation_choice: {self.reputation_choice}")
                    if self.reputation_choice:
                        print("[DEBUG] Advancing to stage 2 (Ether)")
                        self.setup_modal_stage = 2
                    else:
                        print(f"[DEBUG] Cannot continue - reputation not selected yet")
                    return True
            
            # Ether modal
            elif self.setup_modal_stage == 2:
                print(f"[DEBUG] Ether modal - Roll rect: {self.modal_roll_button_rect}, Continue rect: {self.modal_continue_rect}")
                print(f"[DEBUG] Ether rolls: {self.ether_rolls}, choice: {self.ether_choice}")
                if self.modal_roll_button_rect and self.modal_roll_button_rect.collidepoint(mx, my):
                    print("[DEBUG] ROLL button clicked")
                    if self.ether_rolls[0] == 0 or self.ether_rolls[1] == 0:
                        self.ether_rolls[0] = random.randint(1, 6)
                        self.ether_rolls[1] = random.randint(1, 6)
                        print(f"[DEBUG] Rolled: {self.ether_rolls}")
                        # Spawn green dice particles!
                        if self.modal_die1_rect:
                            self._spawn_dice_particles(self.modal_die1_rect.centerx, self.modal_die1_rect.centery, (0, 255, 100))
                        if self.modal_die2_rect:
                            self._spawn_dice_particles(self.modal_die2_rect.centerx, self.modal_die2_rect.centery, (0, 255, 100))
                    return True
                elif self.modal_die1_rect and self.modal_die1_rect.collidepoint(mx, my):
                    print("[DEBUG] Die 1 clicked")
                    if self.ether_rolls[0] > 0 and self.ether_rolls[1] > 0:
                        self.ether_choice = "die1"
                        self.king_dice[1] = self.ether_rolls[0]
                        self.jack_dice[1] = self.ether_rolls[1]
                        print(f"[DEBUG] Assigned - King: {self.king_dice[1]}, Rookie: {self.jack_dice[1]}")
                    return True
                elif self.modal_die2_rect and self.modal_die2_rect.collidepoint(mx, my):
                    print("[DEBUG] Die 2 clicked")
                    if self.ether_rolls[0] > 0 and self.ether_rolls[1] > 0:
                        self.ether_choice = "die2"
                        self.king_dice[1] = self.ether_rolls[1]
                        self.jack_dice[1] = self.ether_rolls[0]
                        print(f"[DEBUG] Assigned - King: {self.king_dice[1]}, Rookie: {self.jack_dice[1]}")
                    return True
                elif self.modal_continue_rect and self.modal_continue_rect.collidepoint(mx, my):
                    print(f"[DEBUG] CONTINUE button clicked, ether_choice: {self.ether_choice}")
                    if self.ether_choice:
                        print("[DEBUG] Advancing to stage 3 (Ion)")
                        self.setup_modal_stage = 3
                    else:
                        print("[DEBUG] Cannot continue - ether choice not made yet")
                    return True
                else:
                    print(f"[DEBUG] Click not on any button")
            
            # Ion modal
            elif self.setup_modal_stage == 3:
                print(f"[DEBUG] Ion modal - Roll rect: {self.modal_roll_button_rect}, Continue rect: {self.modal_continue_rect}")
                print(f"[DEBUG] Ion rolls: {self.ion_rolls}, choice: {self.ion_choice}")
                if self.modal_roll_button_rect and self.modal_roll_button_rect.collidepoint(mx, my):
                    print("[DEBUG] ROLL button clicked")
                    if self.ion_rolls[0] == 0 or self.ion_rolls[1] == 0:
                        self.ion_rolls[0] = random.randint(1, 6)
                        self.ion_rolls[1] = random.randint(1, 6)
                        print(f"[DEBUG] Rolled: {self.ion_rolls}")
                        # Spawn magenta dice particles!
                        if self.modal_die1_rect:
                            self._spawn_dice_particles(self.modal_die1_rect.centerx, self.modal_die1_rect.centery, (255, 0, 255))
                        if self.modal_die2_rect:
                            self._spawn_dice_particles(self.modal_die2_rect.centerx, self.modal_die2_rect.centery, (255, 0, 255))
                    return True
                elif self.modal_die1_rect and self.modal_die1_rect.collidepoint(mx, my):
                    print("[DEBUG] Die 1 clicked")
                    if self.ion_rolls[0] > 0 and self.ion_rolls[1] > 0:
                        self.ion_choice = "die1"
                        self.king_dice[2] = self.ion_rolls[0]
                        self.jack_dice[2] = self.ion_rolls[1]
                        print(f"[DEBUG] Assigned - King: {self.king_dice[2]}, Rookie: {self.jack_dice[2]}")
                    return True
                elif self.modal_die2_rect and self.modal_die2_rect.collidepoint(mx, my):
                    print("[DEBUG] Die 2 clicked")
                    if self.ion_rolls[0] > 0 and self.ion_rolls[1] > 0:
                        self.ion_choice = "die2"
                        self.king_dice[2] = self.ion_rolls[1]
                        self.jack_dice[2] = self.ion_rolls[0]
                        print(f"[DEBUG] Assigned - King: {self.king_dice[2]}, Rookie: {self.jack_dice[2]}")
                    return True
                elif self.modal_continue_rect and self.modal_continue_rect.collidepoint(mx, my):
                    print(f"[DEBUG] CONTINUE button clicked, ion_choice: {self.ion_choice}")
                    if self.ion_choice:
                        print("[DEBUG] Advancing to stage 4 (Encounter)")
                        self.setup_modal_stage = 4
                    else:
                        print("[DEBUG] Cannot continue - ion choice not made yet")
                    return True
                else:
                    print(f"[DEBUG] Click not on any button")
            
            # Encounter modal (stage 4, evidence modal removed)
            elif self.setup_modal_stage == 4:
                print(f"[DEBUG] Encounter modal - Build rect: {self.modal_roll_button_rect}, Continue rect: {self.modal_continue_rect}")
                print(f"[DEBUG] Encounter deck built: {self.encounter_deck_built}, deck size: {len(self.encounter_deck)}")
                if self.modal_roll_button_rect and self.modal_roll_button_rect.collidepoint(mx, my):
                    print("[DEBUG] PREPARE DECK button clicked")
                    if not self.encounter_deck_built:
                        # Shuffle decks
                        random.shuffle(self.upgrade_cards)
                        random.shuffle(self.witness_deck)
                        random.shuffle(self.location_deck)
                        
                        # Draw top 2 from each
                        self.encounter_deck = []
                        if len(self.upgrade_cards) >= 2:
                            self.encounter_deck.extend(self.upgrade_cards[:2])
                        if len(self.witness_deck) >= 2:
                            self.encounter_deck.extend(self.witness_deck[:2])
                        if len(self.location_deck) >= 2:
                            self.encounter_deck.extend(self.location_deck[:2])
                        
                        # Remove drawn cards from decks
                        for card in self.encounter_deck:
                            if card in self.upgrade_cards:
                                self.upgrade_cards.remove(card)
                            if card in self.witness_deck:
                                self.witness_deck.remove(card)
                            if card in self.location_deck:
                                self.location_deck.remove(card)
                        
                        # Position encounter cards in marked area
                        # Find location deck position and place encounters below it
                        if "location" in self.deck_positions:
                            loc_x, loc_y = self.deck_positions["location"]
                            encounter_x = loc_x
                            # Move down by 4% of window height from current position (additional 4% down)
                            down_offset = int(self.window_rect.height * 0.04) if self.window_rect else 0
                            additional_down = int(self.window_rect.height * 0.04) if self.window_rect else 0  # Additional 4% down
                            encounter_y = loc_y + self.card_height + int(50 * self.scale) + down_offset + additional_down
                            
                            # Store encounter deck position for label
                            self.deck_positions["encounter"] = (encounter_x, encounter_y)
                            
                            # Stack encounter cards face-down like other decks
                            for i, card in enumerate(self.encounter_deck):
                                offset_x = encounter_x + (i * 2)
                                offset_y = encounter_y + (i * 2)
                                self.card_positions[card] = (offset_x, offset_y)
                                self.card_face_up[card] = False  # Face down like other decks
                        
                        self.encounter_deck_built = True
                        # Set all cards except MC and Rookie to face down
                        for card in self.card_face_up:
                            if card != self.king_spades and card != self.jack_spades:
                                self.card_face_up[card] = False
                        print(f"[DEBUG] Built encounter deck with {len(self.encounter_deck)} cards, all cards except MC/Rookie set to face down")
                        # Reinitialize z-order to include encounter deck
                        self._init_z_order()
                    return True
                elif self.modal_continue_rect and self.modal_continue_rect.collidepoint(mx, my):
                    print(f"[DEBUG] START GAME button clicked, encounter_deck_built: {self.encounter_deck_built}")
                    if self.encounter_deck_built:
                        print("[DEBUG] Encounter deck built! Starting draw phase...")
                        self.setup_complete = True
                        self.show_setup_modal = False
                        self.draw_phase_stage = 1  # Start with draw upgrades
                        # Ether is tracked per character via green dice (king_dice[1] and jack_dice[1])
                        # Initialize z-order for gameplay
                        self._init_z_order()
                        # Show first tutorial for drawing upgrades
                        self._show_tutorial(
                            "DRAW UPGRADES",
                            "Click the Upgrade deck to draw 3 upgrade cards. Upgrades enhance your characters' skills and cost Ether (green dice) to purchase.",
                            "tutorial_draw_upgrades"
                        )
                    else:
                        print("[DEBUG] Cannot continue - encounter deck not built yet")
                    return True
                else:
                    print(f"[DEBUG] Click not on any button")
        
        return False

    def _draw_modal_background(self, modal_rect: pygame.Rect) -> None:
        """Draw a cyberpunk modal background with gradient and glow."""
        import math
        
        # Create gradient background
        modal_surface = pygame.Surface((modal_rect.width, modal_rect.height), pygame.SRCALPHA)
        
        # Vertical gradient from dark purple to dark blue
        for y in range(modal_rect.height):
            progress = y / modal_rect.height
            r = int(15 + 10 * progress)
            g = int(12 + 15 * (1 - progress))
            b = int(35 + 20 * progress)
            pygame.draw.line(modal_surface, (r, g, b, 245), (0, y), (modal_rect.width, y))
        
        self.screen.blit(modal_surface, modal_rect.topleft)
        
        # Animated neon border glow
        glow_pulse = (math.sin(self.neon_glow_time * 2) + 1) / 2
        
        # Outer glow layers
        for i in range(3):
            offset = 3 - i
            glow_rect = pygame.Rect(
                modal_rect.x - offset,
                modal_rect.y - offset,
                modal_rect.width + offset * 2,
                modal_rect.height + offset * 2
            )
            alpha = int(40 * glow_pulse * (1 - i * 0.3))
            glow_surf = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
            pygame.draw.rect(glow_surf, (0, 255, 255, alpha), (0, 0, glow_rect.width, glow_rect.height), 2)
            self.screen.blit(glow_surf, glow_rect.topleft)
        
        # Main border with color pulse
        border_color = (
            int(0 + 50 * glow_pulse),
            int(200 + 55 * glow_pulse),
            255
        )
        pygame.draw.rect(self.screen, border_color, modal_rect, 3)
        
        # Corner accents (cyberpunk style)
        corner_size = int(15 * self.scale)
        accent_color = (255, 0, 255) if glow_pulse > 0.5 else (0, 255, 255)
        # Top-left
        pygame.draw.line(self.screen, accent_color, modal_rect.topleft, (modal_rect.left + corner_size, modal_rect.top), 2)
        pygame.draw.line(self.screen, accent_color, modal_rect.topleft, (modal_rect.left, modal_rect.top + corner_size), 2)
        # Top-right
        pygame.draw.line(self.screen, accent_color, (modal_rect.right, modal_rect.top), (modal_rect.right - corner_size, modal_rect.top), 2)
        pygame.draw.line(self.screen, accent_color, (modal_rect.right - 1, modal_rect.top), (modal_rect.right - 1, modal_rect.top + corner_size), 2)
        # Bottom-left
        pygame.draw.line(self.screen, accent_color, (modal_rect.left, modal_rect.bottom - 1), (modal_rect.left + corner_size, modal_rect.bottom - 1), 2)
        pygame.draw.line(self.screen, accent_color, (modal_rect.left, modal_rect.bottom - 1), (modal_rect.left, modal_rect.bottom - corner_size - 1), 2)
        # Bottom-right
        pygame.draw.line(self.screen, accent_color, (modal_rect.right - 1, modal_rect.bottom - 1), (modal_rect.right - corner_size - 1, modal_rect.bottom - 1), 2)
        pygame.draw.line(self.screen, accent_color, (modal_rect.right - 1, modal_rect.bottom - 1), (modal_rect.right - 1, modal_rect.bottom - corner_size - 1), 2)

    def _draw_welcome_modal(self) -> None:
        """Draw the welcome modal with story introduction."""
        if not self.window_rect:
            return
        
        # Compact modal dimensions
        modal_width = int(620 * self.scale)
        modal_height = int(480 * self.scale)
        modal_x = self.window_rect.centerx - modal_width // 2
        modal_y = self.window_rect.centery - modal_height // 2
        modal_rect = pygame.Rect(modal_x, modal_y, modal_width, modal_height)
        
        self._draw_modal_background(modal_rect)
        
        # Consistent padding values
        pad_x = int(25 * self.scale)
        pad_top = int(18 * self.scale)
        line_gap = int(16 * self.scale)
        
        # Title
        title_y = modal_y + pad_top
        title_height = int(20 * self.scale)
        if self.label_font:
            title = self.label_font.render("Welcome to Civitas Nihilium", True, (255, 255, 255))
            title_x = modal_x + (modal_width - title.get_width()) // 2
            self.screen.blit(title, (title_x, title_y))
            title_height = title.get_height()
        
        # Skyline image (compact gap after title)
        skyline_y = title_y + title_height + int(12 * self.scale)
        skyline_max_height = int(100 * self.scale)  # Cap skyline height
        if self.skyline_surface:
            max_w = modal_width - pad_x * 2
            orig_w, orig_h = self.skyline_surface.get_size()
            scale_factor = min(1.0, max_w / orig_w, skyline_max_height / orig_h) if orig_w > 0 and orig_h > 0 else 1.0
            skyline_w = int(orig_w * scale_factor)
            skyline_h = int(orig_h * scale_factor)
            skyline_scaled = pygame.transform.smoothscale(
                self.skyline_surface, (skyline_w, skyline_h)
            )
            skyline_x = modal_x + (modal_width - skyline_w) // 2
            self.screen.blit(skyline_scaled, (skyline_x, skyline_y))
            text_start_y = skyline_y + skyline_h + int(10 * self.scale)
        else:
            text_start_y = skyline_y + int(30 * self.scale)
        
        # Story text (word wrapped, below skyline)
        story_text = (
            "Welcome to Civitas Nihilium, a cyberpunk city where dystopia feigns utopia. "
            "You play a senior detective (King of Spades) on his last investigations "
            "before retirement, alongside his Rookie partner (Jack of Spades). "
            "Fight crime, investigate locations, speak to witnesses, and engage in combat. "
            "Build a timeline from witnesses and locations, buy upgrades to boost skills, "
            "and resolve trials with the FateD10 as you clear evidence and survive."
        )
        
        if self.debug_font:
            # Word wrap the text
            words = story_text.split()
            lines = []
            current_line = []
            max_text_width = modal_width - pad_x * 2
            
            for word in words:
                test_line = ' '.join(current_line + [word])
                if self.debug_font.size(test_line)[0] <= max_text_width:
                    current_line.append(word)
                else:
                    if current_line:
                        lines.append(' '.join(current_line))
                    current_line = [word]
            if current_line:
                lines.append(' '.join(current_line))
            
            # Draw lines with consistent spacing
            text_y = text_start_y
            for line in lines:
                text_surface = self.debug_font.render(line, True, (255, 255, 255))
                self.screen.blit(text_surface, (modal_x + pad_x, text_y))
                text_y = self._advance_text_y(text_y, text_surface, max(line_gap - text_surface.get_height(), 2))
        
        # PLAY / QUIT buttons - positioned with proper spacing from bottom
        button_width = int(100 * self.scale)
        button_height = int(36 * self.scale)
        button_gap = int(30 * self.scale)
        button_y = modal_y + modal_height - button_height - int(20 * self.scale)
        
        yes_x = modal_x + (modal_width // 2) - button_width - button_gap // 2
        self.modal_yes_rect = pygame.Rect(yes_x, button_y, button_width, button_height)
        yes_color = (0, 200, 0) if self.modal_yes_rect.collidepoint(pygame.mouse.get_pos()) else (0, 150, 0)
        pygame.draw.rect(self.screen, yes_color, self.modal_yes_rect)
        pygame.draw.rect(self.screen, (255, 255, 255), self.modal_yes_rect, 2)
        if self.debug_font:
            yes_text = self.debug_font.render("PLAY", True, (255, 255, 255))
            self.screen.blit(yes_text, yes_text.get_rect(center=self.modal_yes_rect.center))
        
        no_x = modal_x + (modal_width // 2) + button_gap // 2
        self.modal_no_rect = pygame.Rect(no_x, button_y, button_width, button_height)
        no_color = (200, 0, 0) if self.modal_no_rect.collidepoint(pygame.mouse.get_pos()) else (150, 0, 0)
        pygame.draw.rect(self.screen, no_color, self.modal_no_rect)
        pygame.draw.rect(self.screen, (255, 255, 255), self.modal_no_rect, 2)
        if self.debug_font:
            no_text = self.debug_font.render("QUIT", True, (255, 255, 255))
            self.screen.blit(no_text, no_text.get_rect(center=self.modal_no_rect.center))

    def _draw_reputation_modal(self) -> None:
        """Draw the reputation roll modal (2 blue d6s)."""
        if not self.window_rect:
            return
        
        # Compact modal with consistent spacing
        modal_width = int(520 * self.scale)
        modal_height = int(320 * self.scale)
        modal_x = self.window_rect.centerx - modal_width // 2
        modal_y = self.window_rect.centery - modal_height // 2
        modal_rect = pygame.Rect(modal_x, modal_y, modal_width, modal_height)
        
        self._draw_modal_background(modal_rect)
        
        # Consistent spacing
        pad_top = int(16 * self.scale)
        line_gap = int(18 * self.scale)
        
        # Title
        y_cursor = modal_y + pad_top
        if self.label_font:
            title = self.label_font.render("Roll for Reputation", True, (255, 255, 255))
            title_x = modal_x + (modal_width - title.get_width()) // 2
            self.screen.blit(title, (title_x, y_cursor))
            y_cursor = self._advance_text_y(y_cursor, title, 8)
        
        # Instructions (combined into single line when possible)
        if self.debug_font:
            inst_text = self.debug_font.render("Roll two blue d6s. Select the Main Character's starting Reputation.", True, (255, 255, 255))
            inst_x = modal_x + (modal_width - inst_text.get_width()) // 2
            self.screen.blit(inst_text, (inst_x, y_cursor))
            y_cursor = self._advance_text_y(y_cursor, inst_text, 4)
            
            inst2_text = self.debug_font.render("The Rookie gets the other value.", True, (200, 200, 200))
            inst2_x = modal_x + (modal_width - inst2_text.get_width()) // 2
            self.screen.blit(inst2_text, (inst2_x, y_cursor))
            y_cursor = self._advance_text_y(y_cursor, inst2_text, 12)
        
        # Dice - centered with proper gap
        dice_size = int(55 * self.scale)
        dice_gap = int(35 * self.scale)
        dice_y = y_cursor
        
        die1_x = modal_x + (modal_width // 2) - dice_size - dice_gap // 2
        die2_x = modal_x + (modal_width // 2) + dice_gap // 2
        
        self.modal_die1_rect = None
        self.modal_die2_rect = None
        
        die1_rect = pygame.Rect(die1_x, dice_y, dice_size, dice_size)
        die2_rect = pygame.Rect(die2_x, dice_y, dice_size, dice_size)
        self.modal_die1_rect = die1_rect
        self.modal_die2_rect = die2_rect
        
        if self.reputation_rolls[0] > 0:
            self._draw_d6(self.reputation_rolls[0], (0, 100, 255), die1_rect)
            if self.reputation_choice == "die1":
                pygame.draw.rect(self.screen, (255, 255, 0), die1_rect, 3)
        else:
            pygame.draw.rect(self.screen, (50, 50, 70), die1_rect)
            pygame.draw.rect(self.screen, (0, 100, 255), die1_rect, 2)
            if self.debug_font:
                text = self.debug_font.render("?", True, (255, 255, 255))
                self.screen.blit(text, text.get_rect(center=die1_rect.center))
        
        if self.reputation_rolls[1] > 0:
            self._draw_d6(self.reputation_rolls[1], (0, 100, 255), die2_rect)
            if self.reputation_choice == "die2":
                pygame.draw.rect(self.screen, (255, 255, 0), die2_rect, 3)
        else:
            pygame.draw.rect(self.screen, (50, 50, 70), die2_rect)
            pygame.draw.rect(self.screen, (0, 100, 255), die2_rect, 2)
            if self.debug_font:
                text = self.debug_font.render("?", True, (255, 255, 255))
                self.screen.blit(text, text.get_rect(center=die2_rect.center))
        
        y_cursor = dice_y + dice_size + int(6 * self.scale)
        
        # Labels under dice (only show when rolled)
        if self.debug_font and self.reputation_rolls[0] > 0 and self.reputation_rolls[1] > 0:
            label = self.debug_font.render("Click to select", True, (180, 180, 180))
            self.screen.blit(label, (die1_x + (dice_size - label.get_width()) // 2, y_cursor))
            self.screen.blit(label, (die2_x + (dice_size - label.get_width()) // 2, y_cursor))
            y_cursor = self._advance_text_y(y_cursor, label, 6)
        
        # Show assignment if made
        if self.reputation_choice and self.debug_font:
            king_val = self.reputation_rolls[0] if self.reputation_choice == "die1" else self.reputation_rolls[1]
            jack_val = self.reputation_rolls[1] if self.reputation_choice == "die1" else self.reputation_rolls[0]
            assign_text = f"Main Character (King): {king_val}  |  Rookie (Jack): {jack_val}"
            assign_surface = self.debug_font.render(assign_text, True, (0, 255, 255))
            assign_x = modal_x + (modal_width - assign_surface.get_width()) // 2
            self.screen.blit(assign_surface, (assign_x, y_cursor))
        
        # Roll button or Continue button - fixed at bottom
        button_width = int(130 * self.scale)
        button_height = int(36 * self.scale)
        button_y = modal_y + modal_height - button_height - int(16 * self.scale)
        button_x = modal_x + (modal_width - button_width) // 2
        
        self.modal_roll_button_rect = None
        self.modal_continue_rect = None
        
        if self.reputation_rolls[0] == 0 or self.reputation_rolls[1] == 0:
            self.modal_roll_button_rect = pygame.Rect(button_x, button_y, button_width, button_height)
            roll_color = (100, 200, 100) if self.modal_roll_button_rect.collidepoint(pygame.mouse.get_pos()) else (80, 180, 80)
            pygame.draw.rect(self.screen, roll_color, self.modal_roll_button_rect)
            pygame.draw.rect(self.screen, (255, 255, 255), self.modal_roll_button_rect, 2)
            if self.debug_font:
                roll_text = self.debug_font.render("ROLL", True, (255, 255, 255))
                self.screen.blit(roll_text, roll_text.get_rect(center=self.modal_roll_button_rect.center))
        elif self.reputation_choice:
            self.modal_continue_rect = pygame.Rect(button_x, button_y, button_width, button_height)
            cont_color = (100, 200, 100) if self.modal_continue_rect.collidepoint(pygame.mouse.get_pos()) else (80, 180, 80)
            pygame.draw.rect(self.screen, cont_color, self.modal_continue_rect)
            pygame.draw.rect(self.screen, (255, 255, 255), self.modal_continue_rect, 2)
            if self.debug_font:
                cont_text = self.debug_font.render("CONTINUE", True, (255, 255, 255))
                self.screen.blit(cont_text, cont_text.get_rect(center=self.modal_continue_rect.center))

    def _draw_end_rules_modal(self) -> None:
        """Draw end conditions and victory rules modal."""
        if not self.window_rect:
            return
        
        # Compact modal
        modal_width = int(560 * self.scale)
        modal_height = int(320 * self.scale)
        modal_x = self.window_rect.centerx - modal_width // 2
        modal_y = self.window_rect.centery - modal_height // 2
        modal_rect = pygame.Rect(modal_x, modal_y, modal_width, modal_height)
        
        self._draw_modal_background(modal_rect)
        
        pad_x = int(20 * self.scale)
        line_height = int(18 * self.scale)
        section_gap = int(8 * self.scale)
        y_cursor = modal_y + int(14 * self.scale)
        
        # Title
        if self.label_font:
            title = self.label_font.render("HOW THE GAME ENDS", True, (255, 215, 0))
            self.screen.blit(title, (modal_x + (modal_width - title.get_width()) // 2, y_cursor))
            y_cursor = self._advance_text_y(y_cursor, title, 10)
        
        rules = [
            ("GAME OVER", (255, 100, 100)),
            ("  • No Encounter cards AND no playable cards", (220, 220, 220)),
            ("  • Main Character or Rookie reaches 0 HP or Reputation", (220, 220, 220)),
            ("", None),
            ("EVIDENCE PROGRESSION", (100, 255, 200)),
            ("  • Crime 1: 25 - Crime 2: 50 - Crime 3: 75", (220, 220, 220)),
            ("  • Clear 75 Evidence to win!", (220, 220, 220)),
        ]
        
        if self.debug_font:
            for line, color in rules:
                if line and color:
                    text_surface = self.debug_font.render(line, True, color)
                    self.screen.blit(text_surface, (modal_x + pad_x, y_cursor))
                    y_cursor = self._advance_text_y(y_cursor, text_surface, max(line_height - text_surface.get_height(), 2))
                elif not line:
                    y_cursor += section_gap
        
        # Continue button - fixed at bottom
        button_width = int(180 * self.scale)
        button_height = int(36 * self.scale)
        button_x = modal_x + (modal_width - button_width) // 2
        button_y = modal_y + modal_height - button_height - int(14 * self.scale)
        
        self.modal_continue_rect = pygame.Rect(button_x, button_y, button_width, button_height)
        cont_color = (100, 200, 100) if self.modal_continue_rect.collidepoint(pygame.mouse.get_pos()) else (80, 180, 80)
        pygame.draw.rect(self.screen, cont_color, self.modal_continue_rect)
        pygame.draw.rect(self.screen, (255, 255, 255), self.modal_continue_rect, 2)
        if self.debug_font:
            cont_text = self.debug_font.render("BEGIN INVESTIGATION", True, (255, 255, 255))
            self.screen.blit(cont_text, cont_text.get_rect(center=self.modal_continue_rect.center))

    def _draw_game_over_modal(self) -> None:
        """Draw game over or victory modal."""
        if not self.window_rect or not self.show_game_over_modal:
            return
        
        # Compact modal
        modal_width = int(480 * self.scale)
        modal_height = int(220 * self.scale)
        modal_x = self.window_rect.centerx - modal_width // 2
        modal_y = self.window_rect.centery - modal_height // 2
        modal_rect = pygame.Rect(modal_x, modal_y, modal_width, modal_height)
        
        self._draw_modal_background(modal_rect)
        
        pad_x = int(20 * self.scale)
        y_cursor = modal_y + int(16 * self.scale)
        
        if self.label_font:
            # Flashing text for victory
            if self.show_fireworks and self.end_game_flash_visible:
                flash_colors = [(255, 215, 0), (255, 100, 100), (100, 255, 100), (100, 150, 255)]
                import math
                color_index = int(self.end_game_flash_timer * 2) % len(flash_colors)
                title_color = flash_colors[color_index]
            else:
                title_color = (255, 100, 100)
            
            title = self.label_font.render(self.game_over_title, True, title_color)
            self.screen.blit(title, (modal_x + (modal_width - title.get_width()) // 2, y_cursor))
            y_cursor = self._advance_text_y(y_cursor, title, 14)
        
        if self.debug_font:
            line_height = int(18 * self.scale)
            for line in self.game_over_lines:
                text_surface = self.debug_font.render(line, True, (255, 255, 255))
                self.screen.blit(text_surface, (modal_x + pad_x, y_cursor))
                y_cursor = self._advance_text_y(y_cursor, text_surface, max(line_height - text_surface.get_height(), 2))
        
        # Close button - fixed at bottom
        button_width = int(120 * self.scale)
        button_height = int(36 * self.scale)
        button_x = modal_x + (modal_width - button_width) // 2
        button_y = modal_y + modal_height - button_height - int(14 * self.scale)
        
        self.game_over_button_rect = pygame.Rect(button_x, button_y, button_width, button_height)
        btn_color = (100, 200, 100) if self.game_over_button_rect.collidepoint(pygame.mouse.get_pos()) else (80, 180, 80)
        pygame.draw.rect(self.screen, btn_color, self.game_over_button_rect)
        pygame.draw.rect(self.screen, (255, 255, 255), self.game_over_button_rect, 2)
        if self.debug_font:
            btn_text = self.debug_font.render("CLOSE", True, (255, 255, 255))
            self.screen.blit(btn_text, btn_text.get_rect(center=self.game_over_button_rect.center))

    def _handle_game_over_modal_event(self, event: pygame.event.Event) -> bool:
        if not self.show_game_over_modal:
            return False
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return True
        mx, my = event.pos
        if self.game_over_button_rect and self.game_over_button_rect.collidepoint(mx, my):
            self.close()
            return True
        return True
    
    def _show_tutorial(self, title: str, message: str, step_key: str) -> None:
        """Show a tutorial modal with OK button. Only shows once per step_key."""
        if step_key in self.tutorial_completed_steps:
            return
        self.show_tutorial_modal = True
        self.tutorial_title = title
        self.tutorial_message = message
        self.tutorial_completed_steps.add(step_key)
    
    def _draw_tutorial_modal(self) -> None:
        """Draw the tutorial modal with OK button."""
        if not self.show_tutorial_modal or not self.window_rect:
            return
        
        # Compact modal
        modal_width = int(480 * self.scale)
        modal_height = int(220 * self.scale)
        modal_x = self.window_rect.centerx - modal_width // 2
        modal_y = self.window_rect.centery - modal_height // 2
        modal_rect = pygame.Rect(modal_x, modal_y, modal_width, modal_height)
        
        self._draw_modal_background(modal_rect)
        
        pad_x = int(25 * self.scale)
        y_cursor = modal_y + int(16 * self.scale)
        
        # Title
        if self.label_font:
            title = self.label_font.render(self.tutorial_title, True, (0, 255, 255))
            self.screen.blit(title, (modal_x + (modal_width - title.get_width()) // 2, y_cursor))
            y_cursor = self._advance_text_y(y_cursor, title, 12)
        
        # Message (word wrap)
        if self.debug_font:
            line_height = int(18 * self.scale)
            max_width = modal_width - pad_x * 2
            
            words = self.tutorial_message.split()
            lines = []
            current_line = ""
            for word in words:
                test_line = current_line + (" " if current_line else "") + word
                test_surface = self.debug_font.render(test_line, True, (255, 255, 255))
                if test_surface.get_width() <= max_width:
                    current_line = test_line
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = word
            if current_line:
                lines.append(current_line)
            
            for line in lines:
                text_surface = self.debug_font.render(line, True, (255, 255, 255))
                self.screen.blit(text_surface, (modal_x + (modal_width - text_surface.get_width()) // 2, y_cursor))
                y_cursor = self._advance_text_y(y_cursor, text_surface, max(line_height - text_surface.get_height(), 2))
        
        # OK button - fixed at bottom
        button_width = int(100 * self.scale)
        button_height = int(36 * self.scale)
        button_x = modal_x + (modal_width - button_width) // 2
        button_y = modal_y + modal_height - button_height - int(14 * self.scale)
        
        self.tutorial_ok_button_rect = pygame.Rect(button_x, button_y, button_width, button_height)
        mouse_pos = pygame.mouse.get_pos()
        btn_color = (100, 200, 100) if self.tutorial_ok_button_rect.collidepoint(mouse_pos) else (80, 180, 80)
        pygame.draw.rect(self.screen, btn_color, self.tutorial_ok_button_rect)
        pygame.draw.rect(self.screen, (255, 255, 255), self.tutorial_ok_button_rect, 2)
        if self.debug_font:
            btn_text = self.debug_font.render("OK", True, (255, 255, 255))
            self.screen.blit(btn_text, btn_text.get_rect(center=self.tutorial_ok_button_rect.center))
    
    def _handle_tutorial_modal_event(self, event: pygame.event.Event) -> bool:
        """Handle events for tutorial modal."""
        if not self.show_tutorial_modal:
            return False
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return True
        mx, my = event.pos
        if self.tutorial_ok_button_rect and self.tutorial_ok_button_rect.collidepoint(mx, my):
            self.show_tutorial_modal = False
            return True
        return True
    
    def _show_crime_congratulations(self, crime_number: int) -> None:
        """Show congratulations modal after completing a crime investigation."""
        self.show_crime_congrats_modal = True
        self.crime_congrats_title = f"CRIME {crime_number} SOLVED!"
        self.crime_congrats_message = f"Excellent work! You've cleared crime {crime_number}. The investigation continues..."
    
    def _draw_crime_congrats_modal(self) -> None:
        """Draw the crime congratulations modal."""
        if not self.show_crime_congrats_modal or not self.window_rect:
            return
        
        # Compact modal
        modal_width = int(420 * self.scale)
        modal_height = int(180 * self.scale)
        modal_x = self.window_rect.centerx - modal_width // 2
        modal_y = self.window_rect.centery - modal_height // 2
        modal_rect = pygame.Rect(modal_x, modal_y, modal_width, modal_height)
        
        self._draw_modal_background(modal_rect)
        
        y_cursor = modal_y + int(16 * self.scale)
        
        # Title
        if self.label_font:
            title = self.label_font.render(self.crime_congrats_title, True, (100, 255, 100))
            self.screen.blit(title, (modal_x + (modal_width - title.get_width()) // 2, y_cursor))
            y_cursor = self._advance_text_y(y_cursor, title, 14)
        
        # Message
        if self.debug_font:
            message_surface = self.debug_font.render(self.crime_congrats_message, True, (255, 255, 255))
            self.screen.blit(message_surface, (modal_x + (modal_width - message_surface.get_width()) // 2, y_cursor))
        
        # OK button - fixed at bottom
        button_width = int(100 * self.scale)
        button_height = int(36 * self.scale)
        button_x = modal_x + (modal_width - button_width) // 2
        button_y = modal_y + modal_height - button_height - int(14 * self.scale)
        
        self.crime_congrats_button_rect = pygame.Rect(button_x, button_y, button_width, button_height)
        mouse_pos = pygame.mouse.get_pos()
        btn_color = (100, 200, 100) if self.crime_congrats_button_rect.collidepoint(mouse_pos) else (80, 180, 80)
        pygame.draw.rect(self.screen, btn_color, self.crime_congrats_button_rect)
        pygame.draw.rect(self.screen, (255, 255, 255), self.crime_congrats_button_rect, 2)
        if self.debug_font:
            btn_text = self.debug_font.render("OK", True, (255, 255, 255))
            self.screen.blit(btn_text, btn_text.get_rect(center=self.crime_congrats_button_rect.center))
    
    def _handle_crime_congrats_modal_event(self, event: pygame.event.Event) -> bool:
        """Handle events for crime congratulations modal."""
        if not self.show_crime_congrats_modal:
            return False
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return True
        mx, my = event.pos
        if self.crime_congrats_button_rect and self.crime_congrats_button_rect.collidepoint(mx, my):
            self.show_crime_congrats_modal = False
            return True
        return True
    
    def _init_fireworks(self) -> None:
        """Initialize firework particles for end game celebration."""
        import math
        self.fireworks = []
        if not self.window_rect:
            return
        
        # Create multiple firework bursts
        for _ in range(10):
            x = random.randint(self.window_rect.left + int(100 * self.scale), 
                             self.window_rect.right - int(100 * self.scale))
            y = random.randint(self.window_rect.top + int(100 * self.scale), 
                             self.window_rect.centery)
            # Create burst of particles
            colors = [
                (255, 215, 0),  # Gold
                (255, 100, 100),  # Red
                (100, 255, 100),  # Green
                (100, 150, 255),  # Blue
                (255, 255, 255),  # White
                (255, 200, 0),  # Orange
            ]
            for _ in range(25):
                color = random.choice(colors)
                angle = random.uniform(0, 2 * math.pi)
                speed = random.uniform(3, 8)
                self.fireworks.append({
                    "x": float(x),
                    "y": float(y),
                    "vx": speed * math.cos(angle),
                    "vy": speed * math.sin(angle),
                    "color": color,
                    "life": 1.0,
                    "decay": random.uniform(0.015, 0.035),
                    "size": random.randint(2, 5),
                })
    
    def _update_fireworks(self, dt: float) -> None:
        """Update firework particle positions and lifetimes."""
        import math
        if not self.show_fireworks:
            return
        
        for fw in self.fireworks[:]:
            fw["x"] += fw["vx"]
            fw["y"] += fw["vy"]
            fw["vy"] += 0.3  # Gravity
            fw["life"] -= fw["decay"]
            if fw["life"] <= 0:
                self.fireworks.remove(fw)
        
        # Occasionally add new bursts
        if len(self.fireworks) < 60 and random.random() < 0.12:
            if self.window_rect:
                x = random.randint(self.window_rect.left + int(100 * self.scale), 
                                 self.window_rect.right - int(100 * self.scale))
                y = random.randint(self.window_rect.top + int(100 * self.scale), 
                                 self.window_rect.centery)
                colors = [
                    (255, 215, 0),  # Gold
                    (255, 100, 100),  # Red
                    (100, 255, 100),  # Green
                    (100, 150, 255),  # Blue
                    (255, 255, 255),  # White
                    (255, 200, 0),  # Orange
                ]
                for _ in range(20):
                    color = random.choice(colors)
                    angle = random.uniform(0, 2 * math.pi)
                    speed = random.uniform(3, 8)
                    self.fireworks.append({
                        "x": float(x),
                        "y": float(y),
                        "vx": speed * math.cos(angle),
                        "vy": speed * math.sin(angle),
                        "color": color,
                        "life": 1.0,
                        "decay": random.uniform(0.015, 0.035),
                        "size": random.randint(2, 5),
                    })
    
    def _draw_fireworks(self) -> None:
        """Draw firework particles with alpha blending."""
        if not self.show_fireworks:
            return
        
        for fw in self.fireworks:
            alpha = int(255 * fw["life"])
            if alpha > 0:
                size = int(fw["size"] * fw["life"])
                if size > 0:
                    # Create surface with alpha for each particle
                    particle_surface = pygame.Surface((size * 2 + 2, size * 2 + 2), pygame.SRCALPHA)
                    color_with_alpha = (*fw["color"][:3], alpha)
                    pygame.draw.circle(
                        particle_surface,
                        color_with_alpha,
                        (size + 1, size + 1),
                        size
                    )
                    self.screen.blit(particle_surface, (int(fw["x"]) - size - 1, int(fw["y"]) - size - 1))

    # === CYBERPUNK VISUAL EFFECTS METHODS ===
    
    def _init_ambient_particles(self) -> None:
        """Initialize ambient floating data particles."""
        import math
        self.ambient_particles = []
        if not self.window_rect:
            return
        
        # Create initial batch of particles
        for _ in range(30):
            self.ambient_particles.append(self._create_ambient_particle())
    
    def _create_ambient_particle(self) -> Dict:
        """Create a single ambient particle."""
        import math
        if not self.window_rect:
            return {}
        
        # Particle types: data bits, small circles, squares
        particle_types = ["bit", "circle", "square", "line"]
        ptype = random.choice(particle_types)
        
        # Cyberpunk colors: cyan, magenta, green, white
        colors = [
            (0, 255, 255),    # Cyan
            (255, 0, 255),    # Magenta
            (0, 255, 100),    # Green
            (255, 255, 255),  # White
            (100, 200, 255),  # Light blue
            (255, 100, 200),  # Pink
        ]
        
        return {
            "x": float(random.randint(self.window_rect.left, self.window_rect.right)),
            "y": float(random.randint(self.window_rect.top, self.window_rect.bottom)),
            "vx": random.uniform(-0.3, 0.3),
            "vy": random.uniform(-0.5, -0.1),  # Float upward
            "color": random.choice(colors),
            "alpha": random.randint(30, 100),
            "size": random.randint(2, 6),
            "type": ptype,
            "life": random.uniform(3.0, 8.0),
            "rotation": random.uniform(0, 360),
            "spin": random.uniform(-30, 30),  # Degrees per second
            "char": random.choice(["0", "1", "•", "◦", "○", "▪", "▫"]) if ptype == "bit" else None,
        }
    
    def _update_ambient_particles(self, dt: float) -> None:
        """Update ambient particle positions."""
        if not self.window_rect:
            return
        
        # Update existing particles
        for p in self.ambient_particles[:]:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["rotation"] += p["spin"] * dt
            p["life"] -= dt
            
            # Remove dead particles or those out of bounds
            if (p["life"] <= 0 or 
                p["y"] < self.window_rect.top - 20 or
                p["x"] < self.window_rect.left - 20 or
                p["x"] > self.window_rect.right + 20):
                self.ambient_particles.remove(p)
        
        # Spawn new particles
        self.particle_spawn_timer += dt
        if self.particle_spawn_timer > 0.1 and len(self.ambient_particles) < 40:
            self.particle_spawn_timer = 0.0
            # Spawn at bottom or sides
            new_p = self._create_ambient_particle()
            new_p["y"] = float(self.window_rect.bottom + 10)
            new_p["x"] = float(random.randint(self.window_rect.left, self.window_rect.right))
            self.ambient_particles.append(new_p)
    
    def _draw_ambient_particles(self) -> None:
        """Draw ambient data particles."""
        if not self.debug_font:
            return
        
        for p in self.ambient_particles:
            alpha = int(p["alpha"] * min(1.0, p["life"]))
            if alpha <= 0:
                continue
            
            x, y = int(p["x"]), int(p["y"])
            color = p["color"]
            size = p["size"]
            
            if p["type"] == "bit" and p["char"]:
                # Draw data character
                try:
                    char_surf = self.debug_font.render(p["char"], True, (*color, alpha))
                    char_surf.set_alpha(alpha)
                    self.screen.blit(char_surf, (x, y))
                except:
                    pass
            elif p["type"] == "circle":
                surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
                pygame.draw.circle(surf, (*color, alpha), (size, size), size)
                self.screen.blit(surf, (x - size, y - size))
            elif p["type"] == "square":
                surf = pygame.Surface((size, size), pygame.SRCALPHA)
                surf.fill((*color, alpha))
                self.screen.blit(surf, (x, y))
            elif p["type"] == "line":
                surf = pygame.Surface((size * 3, 2), pygame.SRCALPHA)
                pygame.draw.line(surf, (*color, alpha), (0, 1), (size * 3, 1), 1)
                self.screen.blit(surf, (x, y))
    
    def _draw_scanline_overlay(self) -> None:
        """Draw CRT-style scanline overlay for cyberpunk effect."""
        if not self.window_rect:
            return
        
        # Create or update scanline surface
        if (self.scanline_surface is None or 
            self.scanline_surface.get_size() != (self.window_rect.width, self.window_rect.height)):
            self.scanline_surface = pygame.Surface(
                (self.window_rect.width, self.window_rect.height), 
                pygame.SRCALPHA
            )
            # Draw horizontal lines
            for y in range(0, self.window_rect.height, 3):
                pygame.draw.line(
                    self.scanline_surface,
                    (0, 0, 0, 25),  # Very subtle dark lines
                    (0, y),
                    (self.window_rect.width, y),
                    1
                )
        
        self.screen.blit(self.scanline_surface, self.window_rect.topleft)
    
    def _draw_neon_border(self) -> None:
        """Draw animated neon glow border around the window."""
        if not self.window_rect:
            return
        
        import math
        
        # Pulsing glow intensity
        pulse = (math.sin(self.neon_glow_time * self.neon_pulse_speed * 2 * math.pi) + 1) / 2
        glow_alpha = int(100 + 80 * pulse)
        
        # Cycling color hue for rainbow effect
        hue_offset = (self.neon_glow_time * 0.1) % 1.0
        
        # Create glow layers (outer to inner)
        glow_colors = [
            (0, int(200 * pulse), 255, int(30 * pulse)),      # Outer cyan glow
            (int(100 * pulse), 0, 255, int(50 * pulse)),      # Middle purple
            (0, 255, 255, glow_alpha),                         # Inner cyan (main)
        ]
        
        for i, (r, g, b, a) in enumerate(glow_colors):
            offset = (3 - i) * 3
            rect = pygame.Rect(
                self.window_rect.x - offset,
                self.window_rect.y - offset,
                self.window_rect.width + offset * 2,
                self.window_rect.height + offset * 2
            )
            surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            pygame.draw.rect(surf, (r, g, b, a), (0, 0, rect.width, rect.height), max(1, 3 - i))
            self.screen.blit(surf, rect.topleft)
    
    def _draw_animated_grid(self) -> None:
        """Draw animated cyberpunk grid background."""
        if not self.window_rect:
            return
        
        # Grid parameters
        grid_spacing = int(40 * self.scale)
        grid_color = (0, 60, 80, 40)  # Dark cyan, semi-transparent
        highlight_color = (0, 200, 255, 20)  # Brighter highlight for moving line
        
        content_rect = pygame.Rect(
            self.window_rect.x,
            self.window_rect.y + (self.title_bar_rect.height if self.title_bar_rect else 0),
            self.window_rect.width,
            self.window_rect.height - (self.title_bar_rect.height if self.title_bar_rect else 0)
        )
        
        # Create grid surface
        grid_surface = pygame.Surface((content_rect.width, content_rect.height), pygame.SRCALPHA)
        
        # Draw vertical lines
        for x in range(0, content_rect.width, grid_spacing):
            pygame.draw.line(grid_surface, grid_color, (x, 0), (x, content_rect.height), 1)
        
        # Draw horizontal lines with animated highlight
        animated_y = int(self.grid_offset) % grid_spacing
        for y in range(0, content_rect.height, grid_spacing):
            adjusted_y = y + animated_y
            if adjusted_y < content_rect.height:
                # Highlight line closest to animated position
                if abs(adjusted_y - (self.grid_offset % content_rect.height)) < grid_spacing:
                    pygame.draw.line(grid_surface, highlight_color, (0, adjusted_y), (content_rect.width, adjusted_y), 2)
                else:
                    pygame.draw.line(grid_surface, grid_color, (0, adjusted_y), (content_rect.width, adjusted_y), 1)
        
        self.screen.blit(grid_surface, content_rect.topleft)
    
    def _draw_card_hover_glow(self, card: 'Card', x: int, y: int) -> None:
        """Draw pulsing glow effect for hovered card."""
        import math
        
        # Pulsing glow
        pulse = (math.sin(self.card_hover_glow_time * 4) + 1) / 2
        glow_size = int(6 + 4 * pulse)
        glow_alpha = int(100 + 100 * pulse)
        
        # Draw multiple glow layers
        for i in range(3):
            offset = glow_size - i * 2
            if offset > 0:
                glow_rect = pygame.Rect(
                    x - offset,
                    y - offset,
                    self.card_width + offset * 2,
                    self.card_height + offset * 2
                )
                glow_surf = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
                alpha = int(glow_alpha * (1 - i * 0.3))
                pygame.draw.rect(glow_surf, (0, 255, 255, alpha), (0, 0, glow_rect.width, glow_rect.height), 2)
                self.screen.blit(glow_surf, glow_rect.topleft)
    
    def _spawn_dice_particles(self, x: int, y: int, color: Tuple[int, int, int]) -> None:
        """Spawn particle burst for dice roll."""
        import math
        
        for _ in range(15):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(2, 6)
            self.dice_particles.append({
                "x": float(x),
                "y": float(y),
                "vx": speed * math.cos(angle),
                "vy": speed * math.sin(angle),
                "color": color,
                "life": 1.0,
                "decay": random.uniform(0.03, 0.06),
                "size": random.randint(2, 4),
            })
    
    def _update_dice_particles(self, dt: float) -> None:
        """Update dice particle positions."""
        for p in self.dice_particles[:]:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["vy"] += 0.2  # Gravity
            p["life"] -= p["decay"]
            if p["life"] <= 0:
                self.dice_particles.remove(p)
    
    def _draw_dice_particles(self) -> None:
        """Draw dice roll particles."""
        for p in self.dice_particles:
            alpha = int(255 * p["life"])
            if alpha > 0:
                size = max(1, int(p["size"] * p["life"]))
                surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
                pygame.draw.circle(surf, (*p["color"], alpha), (size, size), size)
                self.screen.blit(surf, (int(p["x"]) - size, int(p["y"]) - size))
    
    def _trigger_glitch(self, intensity: float = 1.0) -> None:
        """Trigger glitch effect (for damage/failures). Persists until next success."""
        self.glitch_active = True
        self.glitch_timer = 0.0
        self.glitch_intensity = intensity

    def _clear_glitch(self) -> None:
        """Clear the glitch effect (called on trial success)."""
        self.glitch_active = False
        self.glitch_timer = 0.0
        self.glitch_intensity = 0.0

    def _update_glitch(self, dt: float) -> None:
        """Update glitch effect timer. Glitch persists until cleared by success."""
        if self.glitch_active:
            self.glitch_timer += dt
            # Glitch persists indefinitely - only cleared by _clear_glitch() on success
    
    def _draw_glitch_effect(self) -> None:
        """Draw RGB split glitch effect. Persists until cleared by success."""
        if not self.glitch_active or not self.window_rect:
            return
        
        # Pulsing intensity that cycles over time (persists until success)
        pulse = 0.4 + 0.6 * abs(math.sin(self.glitch_timer * 2.5))  # Pulse between 0.4 and 1.0
        intensity = self.glitch_intensity * pulse
        
        if random.random() < 0.25:  # Intermittent effect
            # Create offset rectangles for RGB channels
            offset = int(random.randint(2, 6) * intensity)
            
            # Draw colored overlay strips
            for _ in range(int(3 * intensity)):
                strip_y = random.randint(self.window_rect.top, self.window_rect.bottom - 10)
                strip_height = random.randint(2, 6)
                strip_rect = pygame.Rect(self.window_rect.x, strip_y, self.window_rect.width, strip_height)
                
                color = random.choice([
                    (255, 0, 0, 50),   # Red
                    (0, 255, 0, 50),   # Green
                    (0, 0, 255, 50),   # Blue
                    (255, 0, 100, 60), # Magenta-ish
                ])
                
                strip_surf = pygame.Surface((strip_rect.width, strip_rect.height), pygame.SRCALPHA)
                strip_surf.fill(color)
                
                # Offset the strip
                self.screen.blit(strip_surf, (strip_rect.x + random.randint(-offset, offset), strip_rect.y))
    
    def _draw_crt_vignette(self) -> None:
        """Draw CRT-style vignette (darker corners)."""
        if not self.window_rect:
            return
        
        # Create vignette surface
        vignette_surf = pygame.Surface((self.window_rect.width, self.window_rect.height), pygame.SRCALPHA)
        
        # Draw radial gradient from center (clear) to edges (dark)
        center_x = self.window_rect.width // 2
        center_y = self.window_rect.height // 2
        max_dist = ((center_x ** 2 + center_y ** 2) ** 0.5)
        
        # Simplified vignette - just darken corners
        for corner_x, corner_y in [(0, 0), (self.window_rect.width, 0), 
                                    (0, self.window_rect.height), (self.window_rect.width, self.window_rect.height)]:
            corner_size = int(150 * self.scale)
            for i in range(corner_size, 0, -10):
                alpha = int(30 * (1 - i / corner_size))
                pygame.draw.circle(vignette_surf, (0, 0, 0, alpha), (corner_x, corner_y), i)
        
        self.screen.blit(vignette_surf, self.window_rect.topleft)

    def _draw_ether_modal(self) -> None:
        """Draw the Ether roll modal (2 green dice, player chooses)."""
        if not self.window_rect:
            return
        
        # Compact modal with consistent spacing
        modal_width = int(520 * self.scale)
        modal_height = int(320 * self.scale)
        modal_x = self.window_rect.centerx - modal_width // 2
        modal_y = self.window_rect.centery - modal_height // 2
        modal_rect = pygame.Rect(modal_x, modal_y, modal_width, modal_height)
        
        self._draw_modal_background(modal_rect)
        
        # Consistent spacing
        pad_top = int(16 * self.scale)
        
        # Title
        y_cursor = modal_y + pad_top
        if self.label_font:
            title = self.label_font.render("Roll for Ether (Money)", True, (255, 255, 255))
            title_x = modal_x + (modal_width - title.get_width()) // 2
            self.screen.blit(title, (title_x, y_cursor))
            y_cursor = self._advance_text_y(y_cursor, title, 8)
        
        # Instructions
        if self.debug_font:
            inst_text = self.debug_font.render("Roll two green d6s. Select the Main Character's starting Ether.", True, (255, 255, 255))
            inst_x = modal_x + (modal_width - inst_text.get_width()) // 2
            self.screen.blit(inst_text, (inst_x, y_cursor))
            y_cursor = self._advance_text_y(y_cursor, inst_text, 4)
            
            inst2_text = self.debug_font.render("The Rookie gets the other value.", True, (200, 200, 200))
            inst2_x = modal_x + (modal_width - inst2_text.get_width()) // 2
            self.screen.blit(inst2_text, (inst2_x, y_cursor))
            y_cursor = self._advance_text_y(y_cursor, inst2_text, 12)
        
        # Dice - centered with proper gap
        dice_size = int(55 * self.scale)
        dice_gap = int(35 * self.scale)
        dice_y = y_cursor
        
        die1_x = modal_x + (modal_width // 2) - dice_size - dice_gap // 2
        die2_x = modal_x + (modal_width // 2) + dice_gap // 2
        
        self.modal_die1_rect = None
        self.modal_die2_rect = None
        
        die1_rect = pygame.Rect(die1_x, dice_y, dice_size, dice_size)
        die2_rect = pygame.Rect(die2_x, dice_y, dice_size, dice_size)
        self.modal_die1_rect = die1_rect
        self.modal_die2_rect = die2_rect
        
        if self.ether_rolls[0] > 0:
            self._draw_d6(self.ether_rolls[0], (0, 255, 100), die1_rect)
            if self.ether_choice == "die1":
                pygame.draw.rect(self.screen, (255, 255, 0), die1_rect, 3)
        else:
            pygame.draw.rect(self.screen, (50, 50, 70), die1_rect)
            pygame.draw.rect(self.screen, (0, 255, 100), die1_rect, 2)
            if self.debug_font:
                text = self.debug_font.render("?", True, (255, 255, 255))
                self.screen.blit(text, text.get_rect(center=die1_rect.center))
        
        if self.ether_rolls[1] > 0:
            self._draw_d6(self.ether_rolls[1], (0, 255, 100), die2_rect)
            if self.ether_choice == "die2":
                pygame.draw.rect(self.screen, (255, 255, 0), die2_rect, 3)
        else:
            pygame.draw.rect(self.screen, (50, 50, 70), die2_rect)
            pygame.draw.rect(self.screen, (0, 255, 100), die2_rect, 2)
            if self.debug_font:
                text = self.debug_font.render("?", True, (255, 255, 255))
                self.screen.blit(text, text.get_rect(center=die2_rect.center))
        
        y_cursor = dice_y + dice_size + int(6 * self.scale)
        
        # Labels under dice (only show when rolled)
        if self.debug_font and self.ether_rolls[0] > 0 and self.ether_rolls[1] > 0:
            label = self.debug_font.render("Click to select", True, (180, 180, 180))
            self.screen.blit(label, (die1_x + (dice_size - label.get_width()) // 2, y_cursor))
            self.screen.blit(label, (die2_x + (dice_size - label.get_width()) // 2, y_cursor))
            y_cursor = self._advance_text_y(y_cursor, label, 6)
        
        # Show assignment if made
        if self.ether_choice and self.debug_font:
            king_val = self.ether_rolls[0] if self.ether_choice == "die1" else self.ether_rolls[1]
            jack_val = self.ether_rolls[1] if self.ether_choice == "die1" else self.ether_rolls[0]
            assign_text = f"Main Character (King): {king_val}  |  Rookie (Jack): {jack_val}"
            assign_surface = self.debug_font.render(assign_text, True, (0, 255, 255))
            assign_x = modal_x + (modal_width - assign_surface.get_width()) // 2
            self.screen.blit(assign_surface, (assign_x, y_cursor))
        
        # Roll button or Continue button - fixed at bottom
        button_width = int(130 * self.scale)
        button_height = int(36 * self.scale)
        button_y = modal_y + modal_height - button_height - int(16 * self.scale)
        button_x = modal_x + (modal_width - button_width) // 2
        
        self.modal_roll_button_rect = None
        self.modal_continue_rect = None
        
        if self.ether_rolls[0] == 0 or self.ether_rolls[1] == 0:
            self.modal_roll_button_rect = pygame.Rect(button_x, button_y, button_width, button_height)
            roll_color = (100, 200, 100) if self.modal_roll_button_rect.collidepoint(pygame.mouse.get_pos()) else (80, 180, 80)
            pygame.draw.rect(self.screen, roll_color, self.modal_roll_button_rect)
            pygame.draw.rect(self.screen, (255, 255, 255), self.modal_roll_button_rect, 2)
            if self.debug_font:
                roll_text = self.debug_font.render("ROLL", True, (255, 255, 255))
                self.screen.blit(roll_text, roll_text.get_rect(center=self.modal_roll_button_rect.center))
        elif self.ether_choice:
            self.modal_continue_rect = pygame.Rect(button_x, button_y, button_width, button_height)
            cont_color = (100, 200, 100) if self.modal_continue_rect.collidepoint(pygame.mouse.get_pos()) else (80, 180, 80)
            pygame.draw.rect(self.screen, cont_color, self.modal_continue_rect)
            pygame.draw.rect(self.screen, (255, 255, 255), self.modal_continue_rect, 2)
            if self.debug_font:
                cont_text = self.debug_font.render("CONTINUE", True, (255, 255, 255))
                self.screen.blit(cont_text, cont_text.get_rect(center=self.modal_continue_rect.center))

    def _draw_ion_modal(self) -> None:
        """Draw the Ion roll modal (2 purple dice, player chooses)."""
        if not self.window_rect:
            return
        
        # Compact modal with consistent spacing
        modal_width = int(520 * self.scale)
        modal_height = int(320 * self.scale)
        modal_x = self.window_rect.centerx - modal_width // 2
        modal_y = self.window_rect.centery - modal_height // 2
        modal_rect = pygame.Rect(modal_x, modal_y, modal_width, modal_height)
        
        self._draw_modal_background(modal_rect)
        
        # Consistent spacing
        pad_top = int(16 * self.scale)
        
        # Title
        y_cursor = modal_y + pad_top
        if self.label_font:
            title = self.label_font.render("Roll for Ion (Energy)", True, (255, 255, 255))
            title_x = modal_x + (modal_width - title.get_width()) // 2
            self.screen.blit(title, (title_x, y_cursor))
            y_cursor = self._advance_text_y(y_cursor, title, 8)
        
        # Instructions
        if self.debug_font:
            inst_text = self.debug_font.render("Roll two purple d6s. Select the Main Character's starting Ion.", True, (255, 255, 255))
            inst_x = modal_x + (modal_width - inst_text.get_width()) // 2
            self.screen.blit(inst_text, (inst_x, y_cursor))
            y_cursor = self._advance_text_y(y_cursor, inst_text, 4)
            
            inst2_text = self.debug_font.render("The Rookie gets the other value.", True, (200, 200, 200))
            inst2_x = modal_x + (modal_width - inst2_text.get_width()) // 2
            self.screen.blit(inst2_text, (inst2_x, y_cursor))
            y_cursor = self._advance_text_y(y_cursor, inst2_text, 12)
        
        # Dice - centered with proper gap
        dice_size = int(55 * self.scale)
        dice_gap = int(35 * self.scale)
        dice_y = y_cursor
        
        die1_x = modal_x + (modal_width // 2) - dice_size - dice_gap // 2
        die2_x = modal_x + (modal_width // 2) + dice_gap // 2
        
        self.modal_die1_rect = None
        self.modal_die2_rect = None
        
        die1_rect = pygame.Rect(die1_x, dice_y, dice_size, dice_size)
        die2_rect = pygame.Rect(die2_x, dice_y, dice_size, dice_size)
        self.modal_die1_rect = die1_rect
        self.modal_die2_rect = die2_rect
        
        if self.ion_rolls[0] > 0:
            self._draw_d6(self.ion_rolls[0], (255, 0, 255), die1_rect)
            if self.ion_choice == "die1":
                pygame.draw.rect(self.screen, (255, 255, 0), die1_rect, 3)
        else:
            pygame.draw.rect(self.screen, (50, 50, 70), die1_rect)
            pygame.draw.rect(self.screen, (255, 0, 255), die1_rect, 2)
            if self.debug_font:
                text = self.debug_font.render("?", True, (255, 255, 255))
                self.screen.blit(text, text.get_rect(center=die1_rect.center))
        
        if self.ion_rolls[1] > 0:
            self._draw_d6(self.ion_rolls[1], (255, 0, 255), die2_rect)
            if self.ion_choice == "die2":
                pygame.draw.rect(self.screen, (255, 255, 0), die2_rect, 3)
        else:
            pygame.draw.rect(self.screen, (50, 50, 70), die2_rect)
            pygame.draw.rect(self.screen, (255, 0, 255), die2_rect, 2)
            if self.debug_font:
                text = self.debug_font.render("?", True, (255, 255, 255))
                self.screen.blit(text, text.get_rect(center=die2_rect.center))
        
        y_cursor = dice_y + dice_size + int(6 * self.scale)
        
        # Labels under dice (only show when rolled)
        if self.debug_font and self.ion_rolls[0] > 0 and self.ion_rolls[1] > 0:
            label = self.debug_font.render("Click to select", True, (180, 180, 180))
            self.screen.blit(label, (die1_x + (dice_size - label.get_width()) // 2, y_cursor))
            self.screen.blit(label, (die2_x + (dice_size - label.get_width()) // 2, y_cursor))
            y_cursor = self._advance_text_y(y_cursor, label, 6)
        
        # Show assignment if made
        if self.ion_choice and self.debug_font:
            king_val = self.ion_rolls[0] if self.ion_choice == "die1" else self.ion_rolls[1]
            jack_val = self.ion_rolls[1] if self.ion_choice == "die1" else self.ion_rolls[0]
            assign_text = f"Main Character (King): {king_val}  |  Rookie (Jack): {jack_val}"
            assign_surface = self.debug_font.render(assign_text, True, (0, 255, 255))
            assign_x = modal_x + (modal_width - assign_surface.get_width()) // 2
            self.screen.blit(assign_surface, (assign_x, y_cursor))
        
        # Roll button or Continue button - fixed at bottom
        button_width = int(130 * self.scale)
        button_height = int(36 * self.scale)
        button_y = modal_y + modal_height - button_height - int(16 * self.scale)
        button_x = modal_x + (modal_width - button_width) // 2
        
        self.modal_roll_button_rect = None
        self.modal_continue_rect = None
        
        if self.ion_rolls[0] == 0 or self.ion_rolls[1] == 0:
            self.modal_roll_button_rect = pygame.Rect(button_x, button_y, button_width, button_height)
            roll_color = (200, 100, 200) if self.modal_roll_button_rect.collidepoint(pygame.mouse.get_pos()) else (180, 80, 180)
            pygame.draw.rect(self.screen, roll_color, self.modal_roll_button_rect)
            pygame.draw.rect(self.screen, (255, 255, 255), self.modal_roll_button_rect, 2)
            if self.debug_font:
                roll_text = self.debug_font.render("ROLL", True, (255, 255, 255))
                self.screen.blit(roll_text, roll_text.get_rect(center=self.modal_roll_button_rect.center))
        elif self.ion_choice:
            self.modal_continue_rect = pygame.Rect(button_x, button_y, button_width, button_height)
            cont_color = (100, 200, 100) if self.modal_continue_rect.collidepoint(pygame.mouse.get_pos()) else (80, 180, 80)
            pygame.draw.rect(self.screen, cont_color, self.modal_continue_rect)
            pygame.draw.rect(self.screen, (255, 255, 255), self.modal_continue_rect, 2)
            if self.debug_font:
                cont_text = self.debug_font.render("CONTINUE", True, (255, 255, 255))
                self.screen.blit(cont_text, cont_text.get_rect(center=self.modal_continue_rect.center))

    def _draw_evidence_modal(self) -> None:
        """Draw the evidence requirement roll modal (2 d10s)."""
        if not self.window_rect:
            return
        
        modal_width = int(600 * self.scale)
        modal_height = int(400 * self.scale)
        modal_x = self.window_rect.centerx - modal_width // 2
        modal_y = self.window_rect.centery - modal_height // 2
        modal_rect = pygame.Rect(modal_x, modal_y, modal_width, modal_height)
        
        self._draw_modal_background(modal_rect)
        
        # Title
        if self.label_font:
            title = self.label_font.render("Roll for Evidence Required", True, (255, 255, 255))
            title_x = modal_x + (modal_width - title.get_width()) // 2
            title_y = modal_y + int(30 * self.scale)
            self.screen.blit(title, (title_x, title_y))
        
        # Instructions
        if self.debug_font:
            instruction = "Roll two d10s. First is tens, second is units."
            inst_text = self.debug_font.render(instruction, True, (255, 255, 255))
            inst_x = modal_x + (modal_width - inst_text.get_width()) // 2
            inst_y = modal_y + int(70 * self.scale)
            self.screen.blit(inst_text, (inst_x, inst_y))
        
        # Dice
        dice_size = int(60 * self.scale)
        dice_y = modal_y + int(120 * self.scale)
        dice_gap = int(40 * self.scale)
        
        die1_x = modal_x + (modal_width // 2) - dice_size - dice_gap // 2
        die2_x = modal_x + (modal_width // 2) + dice_gap // 2
        
        # Draw d10 diamond dice
        die1_rect = pygame.Rect(die1_x, dice_y, dice_size, dice_size)
        die2_rect = pygame.Rect(die2_x, dice_y, dice_size, dice_size)
        
        if self.evidence_rolls[0] > 0:
            self._draw_d10_diamond(self.evidence_rolls[0], die1_rect)
        else:
            # Draw placeholder diamond
            self._draw_d10_diamond(10, die1_rect)
            # Overlay a "?" indicator
            if self.debug_font:
                q_surf = self.debug_font.render("?", True, (255, 255, 255))
                self.screen.blit(q_surf, q_surf.get_rect(center=die1_rect.center))
        
        if self.evidence_rolls[1] > 0:
            self._draw_d10_diamond(self.evidence_rolls[1], die2_rect)
        else:
            # Draw placeholder diamond
            self._draw_d10_diamond(10, die2_rect)
            # Overlay a "?" indicator
            if self.debug_font:
                q_surf = self.debug_font.render("?", True, (255, 255, 255))
                self.screen.blit(q_surf, q_surf.get_rect(center=die2_rect.center))
        
        # Labels
        if self.debug_font:
            label1 = self.debug_font.render("Tens", True, (255, 255, 255))
            label2 = self.debug_font.render("Units", True, (255, 255, 255))
            label_y = dice_y + dice_size + int(10 * self.scale)
            self.screen.blit(label1, (die1_x + (dice_size - label1.get_width()) // 2, label_y))
            self.screen.blit(label2, (die2_x + (dice_size - label2.get_width()) // 2, label_y))
        
        # Show result
        if self.evidence_required > 0 and self.debug_font:
            result_text = f"Evidence Required: {self.evidence_required}"
            result_surface = self.debug_font.render(result_text, True, (0, 255, 255))
            result_x = modal_x + (modal_width - result_surface.get_width()) // 2
            result_y = dice_y + dice_size + int(40 * self.scale)
            self.screen.blit(result_surface, (result_x, result_y))
        
        # Roll button or Continue button
        button_width = int(150 * self.scale)
        button_height = int(40 * self.scale)
        button_y = modal_y + modal_height - int(60 * self.scale)
        button_x = modal_x + (modal_width - button_width) // 2
        
        # Clear both rects first to avoid overlap
        self.modal_roll_button_rect = None
        self.modal_continue_rect = None
        
        print(f"[DEBUG EVIDENCE MODAL] Rolls: {self.evidence_rolls}, Roll[0]==0: {self.evidence_rolls[0] == 0}, Roll[1]==0: {self.evidence_rolls[1] == 0}, Required: {self.evidence_required}")
        
        if self.evidence_rolls[0] == 0 or self.evidence_rolls[1] == 0:
            print("[DEBUG EVIDENCE MODAL] Showing ROLL button")
            self.modal_roll_button_rect = pygame.Rect(button_x, button_y, button_width, button_height)
            roll_color = (100, 100, 200) if self.modal_roll_button_rect.collidepoint(pygame.mouse.get_pos()) else (80, 80, 180)
            pygame.draw.rect(self.screen, roll_color, self.modal_roll_button_rect)
            pygame.draw.rect(self.screen, (255, 255, 255), self.modal_roll_button_rect, 2)
            if self.debug_font:
                roll_text = self.debug_font.render("ROLL", True, (255, 255, 255))
                self.screen.blit(roll_text, roll_text.get_rect(center=self.modal_roll_button_rect.center))
        else:
            print("[DEBUG EVIDENCE MODAL] Rolls are done, showing CONTINUE button")
            self.modal_continue_rect = pygame.Rect(button_x, button_y, button_width, button_height)
            print(f"[DEBUG EVIDENCE MODAL] Continue rect created: {self.modal_continue_rect}")
            cont_color = (100, 200, 100) if self.modal_continue_rect.collidepoint(pygame.mouse.get_pos()) else (80, 180, 80)
            pygame.draw.rect(self.screen, cont_color, self.modal_continue_rect)
            pygame.draw.rect(self.screen, (255, 255, 255), self.modal_continue_rect, 2)
            if self.debug_font:
                cont_text = self.debug_font.render("CONTINUE", True, (255, 255, 255))
                self.screen.blit(cont_text, cont_text.get_rect(center=self.modal_continue_rect.center))
                print(f"[DEBUG EVIDENCE MODAL] Continue button drawn at {self.modal_continue_rect}")

    def _draw_encounter_modal(self) -> None:
        """Draw the encounter deck building modal."""
        if not self.window_rect:
            return
        
        # Compact modal
        modal_width = int(560 * self.scale)
        modal_height = int(220 * self.scale)
        modal_x = self.window_rect.centerx - modal_width // 2
        modal_y = self.window_rect.centery - modal_height // 2
        modal_rect = pygame.Rect(modal_x, modal_y, modal_width, modal_height)
        
        self._draw_modal_background(modal_rect)
        
        # Consistent spacing
        pad_top = int(16 * self.scale)
        pad_x = int(25 * self.scale)
        
        # Title
        y_cursor = modal_y + pad_top
        if self.label_font:
            title = self.label_font.render("Prepare Your Investigation", True, (255, 255, 255))
            title_x = modal_x + (modal_width - title.get_width()) // 2
            self.screen.blit(title, (title_x, y_cursor))
            y_cursor += title.get_height() + int(10 * self.scale)
        
        # Instructions
        if self.debug_font:
            if not self.encounter_deck_built:
                lines = [
                    ("Prepare your encounter deck before you begin.", (255, 255, 255)),
                    ("Shuffle Upgrade, Witness, and Location decks.", (200, 200, 200)),
                    ("Draw 2 cards from each to form the Encounter deck.", (200, 200, 200)),
                    ("THIS WILL BE DONE AUTOMATICALLY FOR YOU NOW", (0, 255, 200)),
                ]
            else:
                lines = [
                    ("Your Encounter deck is ready!", (0, 255, 255)),
                    ("6 cards stacked face-down below the Location deck.", (200, 200, 200)),
                ]
            
            for text, color in lines:
                text_surf = self.debug_font.render(text, True, color)
                text_x = modal_x + (modal_width - text_surf.get_width()) // 2
                self.screen.blit(text_surf, (text_x, y_cursor))
                y_cursor += text_surf.get_height() + int(4 * self.scale)
        
        # Build button or Continue button - fixed at bottom
        button_width = int(140 * self.scale)
        button_height = int(36 * self.scale)
        button_y = modal_y + modal_height - button_height - int(16 * self.scale)
        button_x = modal_x + (modal_width - button_width) // 2
        
        self.modal_roll_button_rect = None
        self.modal_continue_rect = None
        
        if not self.encounter_deck_built:
            self.modal_roll_button_rect = pygame.Rect(button_x, button_y, button_width, button_height)
            build_color = (100, 100, 200) if self.modal_roll_button_rect.collidepoint(pygame.mouse.get_pos()) else (80, 80, 180)
            pygame.draw.rect(self.screen, build_color, self.modal_roll_button_rect)
            pygame.draw.rect(self.screen, (255, 255, 255), self.modal_roll_button_rect, 2)
            if self.debug_font:
                build_text = self.debug_font.render("PREPARE DECK", True, (255, 255, 255))
                self.screen.blit(build_text, build_text.get_rect(center=self.modal_roll_button_rect.center))
        else:
            self.modal_continue_rect = pygame.Rect(button_x, button_y, button_width, button_height)
            cont_color = (100, 200, 100) if self.modal_continue_rect.collidepoint(pygame.mouse.get_pos()) else (80, 180, 80)
            pygame.draw.rect(self.screen, cont_color, self.modal_continue_rect)
            pygame.draw.rect(self.screen, (255, 255, 255), self.modal_continue_rect, 2)
            if self.debug_font:
                cont_text = self.debug_font.render("START GAME", True, (255, 255, 255))
                self.screen.blit(cont_text, cont_text.get_rect(center=self.modal_continue_rect.center))

    def _draw_draw_phase_modal(self) -> None:
        """Draw the draw phase tutorial modals (upgrades, witnesses, locations)."""
        if not self.window_rect:
            return
        
        # Small instruction modal with arrow pointing to deck
        modal_width = int(350 * self.scale)
        modal_height = int(120 * self.scale)
        
        # Get deck position based on current stage
        if self.draw_phase_stage == 1 and "upgrade" in self.deck_positions:
            deck_x, deck_y = self.deck_positions["upgrade"]
            deck_name = "UPGRADE"
            instruction = "Click the Upgrade deck to draw 3 cards"
        elif self.draw_phase_stage == 2 and "witness" in self.deck_positions:
            deck_x, deck_y = self.deck_positions["witness"]
            deck_name = "WITNESS"
            instruction = "Click the Witness deck to draw 3 cards"
        elif self.draw_phase_stage == 3 and "location" in self.deck_positions:
            deck_x, deck_y = self.deck_positions["location"]
            deck_name = "LOCATION"
            instruction = "Click the Location deck to draw 3 cards"
        else:
            return
        
        # Position modal above the deck
        modal_x = deck_x + self.card_width // 2 - modal_width // 2
        modal_y = deck_y - modal_height - int(30 * self.scale)
        
        # Ensure modal stays within window
        if modal_x < self.window_rect.x + 10:
            modal_x = self.window_rect.x + 10
        if modal_x + modal_width > self.window_rect.right - 10:
            modal_x = self.window_rect.right - modal_width - 10
        if modal_y < self.window_rect.y + 50:
            modal_y = deck_y + self.card_height + int(30 * self.scale)  # Put below instead
        
        modal_rect = pygame.Rect(modal_x, modal_y, modal_width, modal_height)
        
        # Draw modal background
        modal_surface = pygame.Surface((modal_width, modal_height), pygame.SRCALPHA)
        modal_surface.fill((30, 30, 50, 240))
        self.screen.blit(modal_surface, modal_rect.topleft)
        pygame.draw.rect(self.screen, (0, 200, 255), modal_rect, 3)
        
        # Draw title
        if self.label_font:
            title = self.label_font.render(f"Draw {deck_name}S", True, (0, 255, 255))
            title_x = modal_x + (modal_width - title.get_width()) // 2
            title_y = modal_y + int(15 * self.scale)
            self.screen.blit(title, (title_x, title_y))
        
        # Draw instruction
        if self.debug_font:
            inst_text = self.debug_font.render(instruction, True, (255, 255, 255))
            inst_x = modal_x + (modal_width - inst_text.get_width()) // 2
            inst_y = modal_y + int(55 * self.scale)
            self.screen.blit(inst_text, (inst_x, inst_y))
        
        # Draw arrow pointing to deck
        arrow_start_x = deck_x + self.card_width // 2
        if modal_y < deck_y:  # Modal is above deck
            arrow_start_y = modal_y + modal_height
            arrow_end_y = deck_y - int(5 * self.scale)
        else:  # Modal is below deck
            arrow_start_y = modal_y
            arrow_end_y = deck_y + self.card_height + int(5 * self.scale)
        
        pygame.draw.line(self.screen, (0, 255, 255), (arrow_start_x, arrow_start_y), (arrow_start_x, arrow_end_y), 3)
        # Arrow head
        if modal_y < deck_y:
            pygame.draw.polygon(self.screen, (0, 255, 255), [
                (arrow_start_x, arrow_end_y),
                (arrow_start_x - 8, arrow_end_y - 12),
                (arrow_start_x + 8, arrow_end_y - 12)
            ])
        else:
            pygame.draw.polygon(self.screen, (0, 255, 255), [
                (arrow_start_x, arrow_end_y),
                (arrow_start_x - 8, arrow_end_y + 12),
                (arrow_start_x + 8, arrow_end_y + 12)
            ])
        
        # Pulse the deck with same frame style as upgrade slots (glowing teal frame)
        import math
        t = pygame.time.get_ticks() / 1000.0
        pulse = (math.sin(t * 4) + 1) / 2
        inflate = int(6 + 6 * pulse)
        deck_highlight = pygame.Rect(deck_x - inflate, deck_y - inflate, self.card_width + inflate * 2, self.card_height + inflate * 2)
        glow_surf = pygame.Surface((deck_highlight.width, deck_highlight.height), pygame.SRCALPHA)
        alpha = int(40 + 80 * pulse)
        glow_surf.fill((100, 255, 200, alpha))
        self.screen.blit(glow_surf, deck_highlight.topleft)
        border_alpha = int(150 + 105 * pulse)
        border_surf = pygame.Surface((deck_highlight.width, deck_highlight.height), pygame.SRCALPHA)
        pygame.draw.rect(border_surf, (100, 255, 200, border_alpha), border_surf.get_rect(), 3)
        self.screen.blit(border_surf, deck_highlight.topleft)

    def _draw_rules_modal(self) -> None:
        """Draw THE RULES modal explaining game mechanics."""
        if not self.window_rect:
            return
        
        # Compact modal
        modal_width = int(680 * self.scale)
        modal_height = int(480 * self.scale)
        modal_x = self.window_rect.centerx - modal_width // 2
        modal_y = self.window_rect.centery - modal_height // 2
        modal_rect = pygame.Rect(modal_x, modal_y, modal_width, modal_height)
        
        self._draw_modal_background(modal_rect)
        
        # Consistent spacing
        pad_x = int(20 * self.scale)
        line_height = int(17 * self.scale)
        section_gap = int(8 * self.scale)
        
        y_cursor = modal_y + int(14 * self.scale)
        
        # Title
        if self.label_font:
            title = self.label_font.render("THE RULES", True, (255, 215, 0))
            self.screen.blit(title, (modal_x + (modal_width - title.get_width()) // 2, y_cursor))
            y_cursor += title.get_height() + int(10 * self.scale)
        
        # Compact rules text
        rules = [
            ("WITNESSES (Hearts & Diamonds)", (255, 100, 100)),
            ("  Reputation ≥ card value to add. Hearts=CHA, Diamonds=ENG", (220, 220, 220)),
            ("", None),
            ("LOCATIONS (Spades & Clubs)", (100, 200, 100)),
            ("  Ion ≥ card value to add. Spades=ENG, Clubs=ANA", (220, 220, 220)),
            ("", None),
            ("UPGRADES (A,2,3,4 cards)", (100, 255, 200)),
            ("  Card value = Ether cost = Skill bonus", (220, 220, 220)),
            ("  Hearts: HP or CHA | Diamonds: ENG or ANA", (200, 200, 200)),
            ("", None),
            ("TRIALS (Click timeline card)", (0, 255, 255)),
            ("  Choose who faces: Main Character, Rookie, or Both.", (220, 220, 220)),
            ("  Both = half bonuses. Then select skill, roll FateD10.", (200, 200, 200)),
            ("  Win: Remove card, reduce Evidence by value", (100, 255, 100)),
            ("  Fail CHA/ENG: Diff damages HP | Fail ANA: +Evidence", (255, 150, 150)),
            ("", None),
            ("REWARDS (On success)", (255, 215, 0)),
            ("  Witness: +Rep | Location: +Ion | Encounter: +Ether", (200, 200, 200)),
        ]
        
        if self.debug_font:
            for line, color in rules:
                if line and color:
                    text_surface = self.debug_font.render(line, True, color)
                    self.screen.blit(text_surface, (modal_x + pad_x, y_cursor))
                    y_cursor += line_height
                elif not line:
                    y_cursor += section_gap
        
        # Continue button - fixed at bottom
        button_width = int(140 * self.scale)
        button_height = int(36 * self.scale)
        button_x = modal_x + (modal_width - button_width) // 2
        button_y = modal_y + modal_height - button_height - int(14 * self.scale)
        
        self.modal_continue_rect = pygame.Rect(button_x, button_y, button_width, button_height)
        cont_color = (100, 200, 100) if self.modal_continue_rect.collidepoint(pygame.mouse.get_pos()) else (80, 180, 80)
        pygame.draw.rect(self.screen, cont_color, self.modal_continue_rect)
        pygame.draw.rect(self.screen, (255, 255, 255), self.modal_continue_rect, 2)
        if self.debug_font:
            cont_text = self.debug_font.render("NEXT", True, (255, 255, 255))
            self.screen.blit(cont_text, cont_text.get_rect(center=self.modal_continue_rect.center))

    def _draw_encounter_rules_modal(self) -> None:
        """Draw encounter rules modal."""
        if not self.window_rect:
            return
        
        # Compact modal
        modal_width = int(580 * self.scale)
        modal_height = int(240 * self.scale)
        modal_x = self.window_rect.centerx - modal_width // 2
        modal_y = self.window_rect.centery - modal_height // 2
        modal_rect = pygame.Rect(modal_x, modal_y, modal_width, modal_height)
        
        self._draw_modal_background(modal_rect)
        
        pad_x = int(20 * self.scale)
        y_cursor = modal_y + int(14 * self.scale)
        
        # Title
        if self.label_font:
            title = self.label_font.render("ENCOUNTER RULES", True, (255, 200, 100))
            self.screen.blit(title, (modal_x + (modal_width - title.get_width()) // 2, y_cursor))
            y_cursor += title.get_height() + int(12 * self.scale)
        
        rules_lines = [
            "• No playable cards? Click Encounter deck to draw.",
            "• Encounter card goes to timeline face-up.",
            "• Trial: Choose Main Character, Rookie, or Both (½ bonuses).",
            "• Slots auto-refill after trial.",
        ]
        
        line_height = int(20 * self.scale)
        if self.debug_font:
            for line in rules_lines:
                text_surface = self.debug_font.render(line, True, (200, 200, 200))
                self.screen.blit(text_surface, (modal_x + pad_x, y_cursor))
                y_cursor += line_height
        
        # Continue button - fixed at bottom
        button_width = int(140 * self.scale)
        button_height = int(36 * self.scale)
        button_x = modal_x + (modal_width - button_width) // 2
        button_y = modal_y + modal_height - button_height - int(14 * self.scale)
        
        self.modal_continue_rect = pygame.Rect(button_x, button_y, button_width, button_height)
        cont_color = (100, 200, 100) if self.modal_continue_rect.collidepoint(pygame.mouse.get_pos()) else (80, 180, 80)
        pygame.draw.rect(self.screen, cont_color, self.modal_continue_rect)
        pygame.draw.rect(self.screen, (255, 255, 255), self.modal_continue_rect, 2)
        if self.debug_font:
            cont_text = self.debug_font.render("NEXT", True, (255, 255, 255))
            self.screen.blit(cont_text, cont_text.get_rect(center=self.modal_continue_rect.center))

    def _draw_trial_modal(self) -> None:
        """Draw the trial modal for challenging a timeline card with integrated FateD10."""
        if not self.window_rect or not self.active_trial_card:
            return
        
        # Compact modal - taller to fit character choice step
        modal_width = int(480 * self.scale)
        modal_height = int(420 * self.scale)
        modal_x = self.window_rect.centerx - modal_width // 2
        modal_y = self.window_rect.centery - modal_height // 2
        modal_rect = pygame.Rect(modal_x, modal_y, modal_width, modal_height)
        
        self._draw_modal_background(modal_rect)
        
        card = self.active_trial_card
        card_value = self._get_card_value(card)
        mouse_pos = pygame.mouse.get_pos()
        
        # Consistent spacing
        pad_x = int(20 * self.scale)
        y_cursor = modal_y + int(12 * self.scale)
        
        # Title
        if self.label_font:
            title = self.label_font.render(f"TRIAL: {card.rank} of {self._suit_name(card.suit)}", True, (255, 215, 0))
            self.screen.blit(title, (modal_x + (modal_width - title.get_width()) // 2, y_cursor))
            y_cursor += title.get_height() + int(6 * self.scale)
        
        # Card value and type info (combined into one section)
        if self.debug_font:
            # Card type determines skill
            skill_map = {"H": "CHARISMA", "D": "ENGAGEMENT", "S": "ENGAGEMENT", "C": "ANALYSIS"}
            req_skill = skill_map.get(card.suit, "Any Skill")
            info_text = f"Target: {card_value}  |  Use: {req_skill}"
            info_surface = self.debug_font.render(info_text, True, (200, 200, 200))
            self.screen.blit(info_surface, (modal_x + (modal_width - info_surface.get_width()) // 2, y_cursor))
            y_cursor += info_surface.get_height() + int(8 * self.scale)
        
        # Step 0: Choose who faces this location
        if self.debug_font:
            step0_color = (0, 255, 255) if not self.trial_character_choice else (150, 150, 150)
            step0 = self.debug_font.render("0. Who faces this location?", True, step0_color)
            self.screen.blit(step0, (modal_x + pad_x, y_cursor))
            y_cursor += step0.get_height() + int(6 * self.scale)
        
        char_btn_w = int(130 * self.scale)
        char_btn_h = int(28 * self.scale)
        char_btn_gap = int(8 * self.scale)
        char_total_w = 3 * char_btn_w + 2 * char_btn_gap
        char_start_x = modal_x + (modal_width - char_total_w) // 2
        
        self.trial_character_buttons = {}
        char_options = [
            ("main", "Main Character"),
            ("rookie", "Rookie"),
            ("both", "Both (½ bonuses)"),
        ]
        for i, (key, label) in enumerate(char_options):
            btn_x = char_start_x + i * (char_btn_w + char_btn_gap)
            btn_rect = pygame.Rect(btn_x, y_cursor, char_btn_w, char_btn_h)
            self.trial_character_buttons[key] = btn_rect
            if self.trial_character_choice == key:
                btn_color = (100, 180, 100)
            elif btn_rect.collidepoint(mouse_pos):
                btn_color = (100, 100, 180)
            else:
                btn_color = (70, 70, 140)
            pygame.draw.rect(self.screen, btn_color, btn_rect)
            pygame.draw.rect(self.screen, (255, 255, 255) if self.trial_character_choice == key else (150, 150, 150), btn_rect, 2)
            if self.debug_font:
                lbl = self.debug_font.render(label, True, (255, 255, 255))
                self.screen.blit(lbl, lbl.get_rect(center=btn_rect.center))
        y_cursor += char_btn_h + int(10 * self.scale)
        
        # Determine available skills based on card type
        available_skills = self._get_available_skills_for_card(card)
        
        # Step 1: Skill selection buttons (only meaningful after character choice)
        if self.debug_font:
            step1_color = (0, 255, 255) if self.trial_character_choice and not self.trial_skill_selected else (100, 100, 100) if not self.trial_character_choice else (150, 150, 150)
            step1 = self.debug_font.render("1. Select Skill", True, step1_color)
            self.screen.blit(step1, (modal_x + pad_x, y_cursor))
            y_cursor += step1.get_height() + int(6 * self.scale)
        
        button_width = int(120 * self.scale)
        button_height = int(34 * self.scale)
        button_gap = int(10 * self.scale)
        total_width = len(available_skills) * button_width + (len(available_skills) - 1) * button_gap
        start_x = modal_x + (modal_width - total_width) // 2
        
        self.trial_skill_buttons = {}
        for i, skill in enumerate(available_skills):
            btn_x = start_x + i * (button_width + button_gap)
            btn_rect = pygame.Rect(btn_x, y_cursor, button_width, button_height)
            self.trial_skill_buttons[skill] = btn_rect
            
            skill_full = {"ENG": "Engagement", "CHA": "Charisma", "ANA": "Analysis"}[skill]
            combined_value = self._get_trial_skill_bonus(skill_full)
            
            if self.trial_skill_selected == skill:
                btn_color = (100, 180, 100)
            elif btn_rect.collidepoint(mouse_pos) and self.trial_character_choice:
                btn_color = (100, 100, 180)
            else:
                btn_color = (70, 70, 140)
            
            pygame.draw.rect(self.screen, btn_color, btn_rect)
            pygame.draw.rect(self.screen, (255, 255, 255) if self.trial_skill_selected == skill else (150, 150, 150), btn_rect, 2)
            
            if self.debug_font:
                skill_text = self.debug_font.render(f"{skill}: +{combined_value}", True, (255, 255, 255))
                self.screen.blit(skill_text, skill_text.get_rect(center=btn_rect.center))
        
        y_cursor += button_height + int(10 * self.scale)
        
        # Step 2: FateD10 Roll
        if self.debug_font:
            step2_color = (0, 255, 255) if self.trial_skill_selected else (100, 100, 100)
            step2 = self.debug_font.render("2. Roll FateD10", True, step2_color)
            self.screen.blit(step2, (modal_x + pad_x, y_cursor))
            y_cursor += step2.get_height() + int(6 * self.scale)
        
        # Draw FateD10 - smaller size
        die_size = int(60 * self.scale)
        die_x = modal_x + (modal_width - die_size) // 2
        die_y = y_cursor
        self.trial_d10_rect = pygame.Rect(die_x, die_y, die_size, die_size)
        
        can_roll = self.trial_character_choice and self.trial_skill_selected and self.trial_result is None and not self.trial_d10_animating
        is_d10_hovered = self.trial_d10_rect.collidepoint(mouse_pos) and can_roll
        
        # Animation handling
        now = pygame.time.get_ticks()
        if self.trial_d10_animating:
            anim_elapsed = now - self.trial_d10_anim_start
            if anim_elapsed >= 1200:
                self.trial_d10_animating = False
                self.trial_result = random.randint(1, 10)
                self.trial_d10_display_value = self.trial_result
                self.trial_result_choice = None
                self.show_trial_modal = False
                self.show_trial_result_modal = True
                if self.trial_d10_rect:
                    self._spawn_dice_particles(self.trial_d10_rect.centerx, self.trial_d10_rect.centery, (180, 100, 255))
                    self._spawn_dice_particles(self.trial_d10_rect.centerx, self.trial_d10_rect.centery, (0, 255, 255))
            else:
                self.trial_d10_display_value = random.randint(1, 10)
                if random.random() < 0.3 and self.trial_d10_rect:
                    self._spawn_dice_particles(
                        self.trial_d10_rect.centerx + random.randint(-20, 20), 
                        self.trial_d10_rect.centery + random.randint(-20, 20), 
                        (180, 100, 255)
                    )
        
        # Determine D10 value to display
        if self.trial_result is not None:
            display_val = self.trial_result
        elif self.trial_d10_animating:
            display_val = self.trial_d10_display_value
        else:
            display_val = 10
        
        # Draw stylish teal diamond D10
        self._draw_d10_diamond(
            display_val, 
            self.trial_d10_rect, 
            animating=self.trial_d10_animating,
            can_roll=can_roll,
            hovered=is_d10_hovered
        )
        
        # Click instruction under die
        if self.debug_font:
            if can_roll:
                click_surface = self.debug_font.render("CLICK TO ROLL!", True, (255, 255, 0))
            elif self.trial_d10_animating:
                click_surface = self.debug_font.render("Rolling...", True, (255, 255, 200))
            else:
                click_surface = None
            if click_surface:
                self.screen.blit(click_surface, (modal_x + (modal_width - click_surface.get_width()) // 2, die_y + die_size + int(4 * self.scale)))
        
        # Cancel button - fixed at bottom left
        cancel_w = int(70 * self.scale)
        cancel_h = int(32 * self.scale)
        cancel_btn = pygame.Rect(modal_x + pad_x, modal_y + modal_height - cancel_h - int(14 * self.scale), cancel_w, cancel_h)
        self.trial_cancel_btn = cancel_btn
        cancel_color = (180, 80, 80) if cancel_btn.collidepoint(mouse_pos) else (140, 60, 60)
        pygame.draw.rect(self.screen, cancel_color, cancel_btn)
        pygame.draw.rect(self.screen, (255, 255, 255), cancel_btn, 2)
        if self.debug_font:
            cancel_text = self.debug_font.render("Cancel", True, (255, 255, 255))
            self.screen.blit(cancel_text, cancel_text.get_rect(center=cancel_btn.center))

    def _draw_trial_result_modal(self) -> None:
        """Step 3: Separate modal showing success/failure and reward choice."""
        if not self.show_trial_result_modal or not self.active_trial_card or self.trial_result is None:
            return
        card = self.active_trial_card
        card_value = self._get_card_value(card)
        skill_full = {"ENG": "Engagement", "CHA": "Charisma", "ANA": "Analysis"}[self.trial_skill_selected]
        combined_skill = self._get_trial_skill_bonus(skill_full)
        total = self.trial_result + combined_skill
        success = total >= card_value
        diff = max(0, total - card_value) if success else max(0, card_value - total)
        
        # Compact modal - size varies based on content
        modal_width = int(440 * self.scale)
        modal_height = int(320 * self.scale) if success else int(240 * self.scale)
        modal_x = self.window_rect.centerx - modal_width // 2
        modal_y = self.window_rect.centery - modal_height // 2
        modal_rect = pygame.Rect(modal_x, modal_y, modal_width, modal_height)
        self._draw_modal_background(modal_rect)
        
        mouse_pos = pygame.mouse.get_pos()
        y_cursor = modal_y + int(14 * self.scale)
        
        # Title
        if self.label_font:
            title = self.label_font.render("TRIAL RESULT", True, (255, 215, 0))
            self.screen.blit(title, (modal_x + (modal_width - title.get_width()) // 2, y_cursor))
            y_cursor += title.get_height() + int(8 * self.scale)
        
        # Calculation breakdown
        if self.debug_font:
            calc_text = f"{self.trial_result} + {combined_skill} = {total} vs {card_value}"
            calc_surface = self.debug_font.render(calc_text, True, (255, 255, 255))
            self.screen.blit(calc_surface, (modal_x + (modal_width - calc_surface.get_width()) // 2, y_cursor))
            y_cursor += calc_surface.get_height() + int(6 * self.scale)
        
        # Outcome
        if self.label_font:
            if success:
                outcome_text = self.label_font.render("SUCCESS!", True, (100, 255, 100))
            else:
                outcome_text = self.label_font.render("FAILED!", True, (255, 100, 100))
            self.screen.blit(outcome_text, (modal_x + (modal_width - outcome_text.get_width()) // 2, y_cursor))
            y_cursor += outcome_text.get_height() + int(10 * self.scale)
        
        if success:
            # Reward choice
            if self.debug_font:
                inst = "Choose your reward:"
                inst_surface = self.debug_font.render(inst, True, (200, 200, 200))
                self.screen.blit(inst_surface, (modal_x + (modal_width - inst_surface.get_width()) // 2, y_cursor))
                y_cursor += inst_surface.get_height() + int(8 * self.scale)
            
            self.trial_result_choice_buttons = {}
            btn_w = int(200 * self.scale)
            btn_h = int(32 * self.scale)
            btn_gap = int(6 * self.scale)
            
            options = []
            if card.suit in ["H", "D"]:
                options.append(("evidence", f"-{card_value + diff} Evidence"))
                options.append(("reputation", f"+{diff} Reputation"))
            elif card.suit in ["S", "C"]:
                options.append(("evidence", f"-{card_value + diff} Evidence"))
                options.append(("ion", f"+{diff} Ion"))
            else:
                options.append(("evidence", f"-{card_value} Evidence"))
                if diff > 0:
                    options.append(("ether", f"+{diff} Ether"))
            
            for i, (key, label) in enumerate(options):
                btn_x = modal_x + (modal_width - btn_w) // 2
                btn_y = y_cursor + i * (btn_h + btn_gap)
                btn_rect = pygame.Rect(btn_x, btn_y, btn_w, btn_h)
                self.trial_result_choice_buttons[key] = btn_rect
                is_selected = self.trial_result_choice == key
                btn_color = (100, 180, 100) if is_selected else (80, 120, 80) if btn_rect.collidepoint(mouse_pos) else (60, 80, 60)
                pygame.draw.rect(self.screen, btn_color, btn_rect)
                pygame.draw.rect(self.screen, (255, 255, 255) if is_selected else (120, 120, 120), btn_rect, 2)
                if self.debug_font:
                    lbl = self.debug_font.render(label, True, (255, 255, 255))
                    self.screen.blit(lbl, lbl.get_rect(center=btn_rect.center))
            
            y_cursor += len(options) * (btn_h + btn_gap) + int(10 * self.scale)
            
            # Bonus note
            if diff > 5 and self.debug_font:
                bonus = self.debug_font.render("+1 Ether bonus!", True, (100, 255, 200))
                self.screen.blit(bonus, (modal_x + (modal_width - bonus.get_width()) // 2, y_cursor))
                y_cursor += bonus.get_height() + int(6 * self.scale)
            
            # Confirm button - fixed at bottom
            confirm_w = int(120 * self.scale)
            confirm_h = int(34 * self.scale)
            confirm_btn = pygame.Rect(modal_x + (modal_width - confirm_w) // 2, modal_y + modal_height - confirm_h - int(14 * self.scale), confirm_w, confirm_h)
            self.trial_result_confirm_rect = confirm_btn
            can_confirm = self.trial_result_choice is not None
            conf_color = (100, 200, 100) if can_confirm and confirm_btn.collidepoint(mouse_pos) else (80, 160, 80) if can_confirm else (60, 60, 60)
            pygame.draw.rect(self.screen, conf_color, confirm_btn)
            pygame.draw.rect(self.screen, (255, 255, 255), confirm_btn, 2)
            if self.debug_font:
                conf_text = self.debug_font.render("CONFIRM", True, (255, 255, 255) if can_confirm else (120, 120, 120))
                self.screen.blit(conf_text, conf_text.get_rect(center=confirm_btn.center))
        else:
            # Failure consequences
            if self.debug_font:
                if self.trial_skill_selected == "ANA":
                    fail_text = f"Analysis failure: +{diff} Evidence"
                else:
                    fail_text = f"Combat failure: {diff} damage"
                fail_surface = self.debug_font.render(fail_text, True, (255, 150, 100))
                self.screen.blit(fail_surface, (modal_x + (modal_width - fail_surface.get_width()) // 2, y_cursor))
                y_cursor += fail_surface.get_height() + int(4 * self.scale)
                
                disc_surface = self.debug_font.render("Card discarded.", True, (200, 200, 200))
                self.screen.blit(disc_surface, (modal_x + (modal_width - disc_surface.get_width()) // 2, y_cursor))
            
            self.trial_result_choice = "failed"
            confirm_w = int(110 * self.scale)
            confirm_h = int(34 * self.scale)
            confirm_btn = pygame.Rect(modal_x + (modal_width - confirm_w) // 2, modal_y + modal_height - confirm_h - int(14 * self.scale), confirm_w, confirm_h)
            self.trial_result_confirm_rect = confirm_btn
            pygame.draw.rect(self.screen, (120, 80, 80) if confirm_btn.collidepoint(mouse_pos) else (100, 60, 60), confirm_btn)
            pygame.draw.rect(self.screen, (255, 255, 255), confirm_btn, 2)
            if self.debug_font:
                conf_text = self.debug_font.render("CONTINUE", True, (255, 255, 255))
                self.screen.blit(conf_text, conf_text.get_rect(center=confirm_btn.center))

    def _handle_trial_result_modal_event(self, event: pygame.event.Event) -> bool:
        """Handle events for the trial result modal."""
        if not self.show_trial_result_modal:
            return False
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return True
        mx, my = event.pos
        
        card = self.active_trial_card
        success = False
        if card and self.trial_result is not None:
            card_value = self._get_card_value(card)
            skill_full = {"ENG": "Engagement", "CHA": "Charisma", "ANA": "Analysis"}[self.trial_skill_selected]
            total = self.trial_result + self._get_trial_skill_bonus(skill_full)
            success = total >= card_value
        
        if success:
            for choice_key, btn_rect in self.trial_result_choice_buttons.items():
                if btn_rect.collidepoint(mx, my):
                    self.trial_result_choice = choice_key
                    return True
            
            if self.trial_result_confirm_rect and self.trial_result_confirm_rect.collidepoint(mx, my) and self.trial_result_choice:
                self._apply_trial_result()
                self._close_trial_result_modal()
                return True
        else:
            if self.trial_result_confirm_rect and self.trial_result_confirm_rect.collidepoint(mx, my):
                self._apply_trial_result()
                self._close_trial_result_modal()
                return True
        return True

    def _close_trial_result_modal(self) -> None:
        """Reset trial state after result modal is closed."""
        self.show_trial_result_modal = False
        self.active_trial_card = None
        self.trial_character_choice = None
        self.trial_skill_selected = None
        self.trial_result = None
        self.trial_result_choice = None
        self.trial_d10_animating = False
        self.modal_continue_rect = None

    def _has_playable_witness_location(self) -> bool:
        total_rep = self.king_dice[0] + self.jack_dice[0]
        for card in self.witness_slots:
            if card and total_rep >= self._get_card_value(card):
                return True
        total_ion = self.king_dice[2] + self.jack_dice[2]
        for card in self.location_slots:
            if card and total_ion >= self._get_card_value(card):
                return True
        return False

    def _refill_empty_slots(self) -> None:
        for i in range(3):
            if self.upgrade_slots[i] is None and self.upgrade_cards:
                self.upgrade_slots[i] = self.upgrade_cards.pop(0)
                self.card_face_up[self.upgrade_slots[i]] = True
        for i in range(3):
            if self.witness_slots[i] is None and self.witness_deck:
                self.witness_slots[i] = self.witness_deck.pop(0)
                self.card_face_up[self.witness_slots[i]] = True
        for i in range(3):
            if self.location_slots[i] is None and self.location_deck:
                self.location_slots[i] = self.location_deck.pop(0)
                self.card_face_up[self.location_slots[i]] = True

    def _advance_crime_if_needed(self) -> None:
        if self.evidence_required > 0:
            return
        if self.crime_stage == 0:
            self.crime_stage = 1
            self.evidence_required = 50  # Second crime requires 50 evidence
            self._show_crime_congratulations(1)
            self._reset_for_new_crime()
        elif self.crime_stage == 1:
            self.crime_stage = 2
            self.evidence_required = 75  # Final crime requires 75 evidence
            self._show_crime_congratulations(2)
            self._reset_for_new_crime()
        elif self.crime_stage == 2:
            self.crime_stage = 3
            self._set_game_over(
                "YOU WIN!",
                [
                    "You cleared the final crime.",
                    "The main detective retires a legend!",
                ],
                is_victory=True,
            )

    def _reset_for_new_crime(self) -> None:
        # Discard any timeline cards and restart draw phase sequence.
        self.timeline_cards.clear()
        self.upgrade_slots = [None, None, None]
        self.witness_slots = [None, None, None]
        self.location_slots = [None, None, None]
        self.encounter_slot = None  # Clear encounter slot
        self.game_phase = "UPGRADE"
        self.draw_phase_stage = 1

    def _set_game_over(self, title: str, lines: List[str], is_victory: bool = False) -> None:
        if self.show_game_over_modal:
            return
        self.show_game_over_modal = True
        self.game_over_title = title
        self.game_over_lines = lines
        if is_victory:
            self.game_over_title = "VICTORY!"
            # Initialize fireworks and flashing text for victory
            self.show_fireworks = True
            self._init_fireworks()
            self.end_game_flash_timer = 0.0
            self.end_game_flash_visible = True

    def _check_end_conditions(self) -> None:
        if self.show_game_over_modal or not self.setup_complete:
            return
        if self.king_stats["HP"] <= 0 or self.rookie_stats["HP"] <= 0:
            self._set_game_over("GAME OVER", ["A detective has fallen in the line of duty."])
            return
        if self.king_dice[0] <= 0 or self.jack_dice[0] <= 0:
            self._set_game_over("GAME OVER", ["A detective's Reputation has collapsed to zero."])
            return
        if not self.timeline_cards and not self.encounter_deck and not self._has_playable_witness_location():
            self._set_game_over(
                "GAME OVER",
                [
                    "No encounters remain and no qualifying cards can be played.",
                    "There is no way to initiate another trial.",
                ],
            )

    def _draw_upgrade_modal(self) -> None:
        """Draw the upgrade purchase modal with skill selection."""
        if not self.window_rect or not self.upgrade_modal_card:
            return
        
        card = self.upgrade_modal_card
        card_value = self._get_card_value(card)
        
        # Compact modal
        modal_width = int(380 * self.scale)
        modal_height = int(300 * self.scale)
        modal_x = self.window_rect.centerx - modal_width // 2
        modal_y = self.window_rect.centery - modal_height // 2
        modal_rect = pygame.Rect(modal_x, modal_y, modal_width, modal_height)
        
        self._draw_modal_background(modal_rect)
        
        pad_x = int(20 * self.scale)
        y_cursor = modal_y + int(12 * self.scale)
        
        # Title
        if self.label_font:
            title = self.label_font.render("Purchase Upgrade", True, (100, 255, 200))
            self.screen.blit(title, (modal_x + (modal_width - title.get_width()) // 2, y_cursor))
            y_cursor += title.get_height() + int(8 * self.scale)
        
        # Card info - compact
        if self.debug_font:
            info_text = f"{card.rank} of {self._suit_name(card.suit)}  |  Cost: {card_value} Ether"
            info_surface = self.debug_font.render(info_text, True, (255, 255, 255))
            self.screen.blit(info_surface, (modal_x + (modal_width - info_surface.get_width()) // 2, y_cursor))
            y_cursor += info_surface.get_height() + int(4 * self.scale)
            
            # Ether amounts
            ether_text = f"Main Character: {self.king_dice[1]} | Rookie: {self.jack_dice[1]}"
            ether_surface = self.debug_font.render(ether_text, True, (150, 255, 150))
            self.screen.blit(ether_surface, (modal_x + (modal_width - ether_surface.get_width()) // 2, y_cursor))
            y_cursor += ether_surface.get_height() + int(10 * self.scale)
            
            # Skill title
            skill_title = self.debug_font.render("Choose Enhancement:", True, (200, 200, 200))
            self.screen.blit(skill_title, (modal_x + (modal_width - skill_title.get_width()) // 2, y_cursor))
            y_cursor += skill_title.get_height() + int(8 * self.scale)
        
        # Skills based on suit
        if card.suit == "H":
            available_skills = [("HP", f"HP +{card_value}"), ("CHA", f"CHA +{card_value}")]
        elif card.suit == "D":
            available_skills = [("ENG", f"ENG +{card_value}"), ("ANA", f"ANA +{card_value}")]
        else:
            available_skills = [("HP", f"HP +{card_value}"), ("CHA", f"CHA +{card_value}"), ("ENG", f"ENG +{card_value}"), ("ANA", f"ANA +{card_value}")]
        
        # Skill buttons - 2 per row
        btn_w = int(120 * self.scale)
        btn_h = int(32 * self.scale)
        btn_gap_x = int(10 * self.scale)
        btn_gap_y = int(6 * self.scale)
        
        self.upgrade_skill_buttons = {}
        for i, (skill_key, skill_name) in enumerate(available_skills):
            row = i // 2
            col = i % 2
            btn_x = modal_x + (modal_width - 2 * btn_w - btn_gap_x) // 2 + col * (btn_w + btn_gap_x)
            btn_y = y_cursor + row * (btn_h + btn_gap_y)
            btn_rect = pygame.Rect(btn_x, btn_y, btn_w, btn_h)
            self.upgrade_skill_buttons[skill_key] = btn_rect
            
            if self.upgrade_skill_selected == skill_key:
                btn_color = (150, 200, 150)
            elif btn_rect.collidepoint(pygame.mouse.get_pos()):
                btn_color = (100, 150, 100)
            else:
                btn_color = (70, 120, 70)
            
            pygame.draw.rect(self.screen, btn_color, btn_rect)
            pygame.draw.rect(self.screen, (255, 255, 255), btn_rect, 2)
            
            if self.debug_font:
                skill_text = self.debug_font.render(skill_name, True, (255, 255, 255))
                self.screen.blit(skill_text, skill_text.get_rect(center=btn_rect.center))
        
        # Bottom buttons - fixed at bottom
        btn_row_y = modal_y + modal_height - int(36 * self.scale) - int(14 * self.scale)
        
        # Check affordability
        can_afford = self.king_dice[1] >= card_value or self.jack_dice[1] >= card_value
        can_place = self.upgrade_skill_selected is not None and can_afford
        
        # Place button
        place_w = int(110 * self.scale)
        place_btn = pygame.Rect(modal_x + pad_x, btn_row_y, place_w, int(36 * self.scale))
        self.upgrade_place_btn = place_btn
        place_color = (100, 200, 100) if can_place and place_btn.collidepoint(pygame.mouse.get_pos()) else (80, 180, 80) if can_place else (60, 60, 60)
        pygame.draw.rect(self.screen, place_color, place_btn)
        pygame.draw.rect(self.screen, (255, 255, 255), place_btn, 2)
        if self.debug_font:
            place_text = self.debug_font.render("PLACE", True, (255, 255, 255) if can_place else (150, 150, 150))
            self.screen.blit(place_text, place_text.get_rect(center=place_btn.center))
        
        # Warning if can't afford
        if self.debug_font and self.upgrade_skill_selected and not can_afford:
            warn = self.debug_font.render("Can't afford!", True, (255, 100, 100))
            self.screen.blit(warn, (modal_x + (modal_width - warn.get_width()) // 2, btn_row_y - int(18 * self.scale)))
        
        # Cancel button
        cancel_w = int(70 * self.scale)
        cancel_btn = pygame.Rect(modal_x + modal_width - pad_x - cancel_w, btn_row_y, cancel_w, int(36 * self.scale))
        self.upgrade_cancel_btn = cancel_btn
        cancel_color = (180, 80, 80) if cancel_btn.collidepoint(pygame.mouse.get_pos()) else (140, 60, 60)
        pygame.draw.rect(self.screen, cancel_color, cancel_btn)
        pygame.draw.rect(self.screen, (255, 255, 255), cancel_btn, 2)
        if self.debug_font:
            cancel_text = self.debug_font.render("Cancel", True, (255, 255, 255))
            self.screen.blit(cancel_text, cancel_text.get_rect(center=cancel_btn.center))

    def _get_card_value(self, card: Card) -> int:
        """Get the numeric value of a card for trials."""
        if card.rank == "A":
            return 1
        elif card.rank in ["2", "3", "4", "5", "6", "7", "8", "9", "10"]:
            return int(card.rank)
        elif card.rank == "J":
            return 11
        elif card.rank in ["Q", "K"]:
            return 12
        return 0

    def _suit_name(self, suit: str) -> str:
        """Get full name of suit."""
        return {"H": "Hearts", "D": "Diamonds", "S": "Spades", "C": "Clubs"}.get(suit, suit)

    def _get_trial_skill_bonus(self, skill_full: str) -> int:
        """Get skill bonus for trial based on character choice. Both = half bonuses (floor)."""
        if not self.trial_character_choice:
            return 0
        king_val = self.king_stats.get(skill_full, 0)
        rookie_val = self.rookie_stats.get(skill_full, 0)
        if self.trial_character_choice == "main":
            return king_val
        if self.trial_character_choice == "rookie":
            return rookie_val
        # both: half bonuses (floor division)
        return (king_val + rookie_val) // 2

    def _get_available_skills_for_card(self, card: Card) -> List[str]:
        """Get available skills for trialing a card based on its suit."""
        # Hearts = Charisma, Diamonds = Engagement
        # Spades = Engagement, Clubs = Analysis
        if card.suit == "H":
            return ["CHA"]
        elif card.suit == "D":
            return ["ENG"]
        elif card.suit == "S":
            return ["ENG"]
        elif card.suit == "C":
            return ["ANA"]
        return ["ENG", "CHA", "ANA"]  # Encounters can use any

    def _is_encounter_card(self, card: Card) -> bool:
        """Check if a card is an encounter (was drawn from encounter deck)."""
        return card in self.encounter_deck

    def _apply_upgrade_skill(self, stats: Dict[str, int], skill: str, value: int) -> None:
        """Apply an upgrade skill enhancement to a character's stats."""
        if skill == "HP":
            stats["HP"] = stats.get("HP", 0) + value
        elif skill == "CHA":
            stats["Charisma"] = stats.get("Charisma", 0) + value
        elif skill == "ENG":
            stats["Engagement"] = stats.get("Engagement", 0) + value
        elif skill == "ANA":
            stats["Analysis"] = stats.get("Analysis", 0) + value
        print(f"[DEBUG] Applied upgrade: +{value} {skill}, new stats: {stats}")
    
    def _should_prompt_complete_upgrades(self) -> bool:
        """Check if we should prompt the user to click COMPLETE UPGRADES.
        
        Returns True only when:
        - All 3 upgrade slots are empty (nothing to buy), OR
        - No upgrades can be afforded (hand + slots: nothing either character can buy/attach)
        """
        king_ether = self.king_dice[1]
        rookie_ether = self.jack_dice[1]
        
        def can_afford(card):
            return king_ether >= self._get_card_value(card) or rookie_ether >= self._get_card_value(card)
        
        # All upgrade slots empty - nothing to buy
        if all(slot is None for slot in self.upgrade_slots):
            return True
        
        # Check if any slot card can be afforded
        for slot in self.upgrade_slots:
            if slot and can_afford(slot):
                return False
        
        # Check if any hand card can be afforded
        for card in self.hand_cards:
            if can_afford(card):
                return False
        
        # Nothing can be afforded
        return True
    
    def _check_and_show_complete_upgrades_tutorial(self) -> None:
        """Show tutorial prompting user to click COMPLETE UPGRADES if appropriate."""
        if self.game_phase == "UPGRADE" and self._should_prompt_complete_upgrades():
            self._show_tutorial(
                "COMPLETE UPGRADES",
                "You've finished attaching upgrades (or can't afford the remaining ones). Click the 'COMPLETE UPGRADES' button to enter the TIMELINE phase and start investigating!",
                "tutorial_complete_upgrades"
            )

    def _check_and_show_start_trial_tutorial(self) -> None:
        """Show START TRIAL tutorial when all qualifying cards are in timeline."""
        if (self.game_phase == "TIMELINE" and self.timeline_cards and
                not self._has_playable_witness_location() and
                "tutorial_start_trial" not in self.tutorial_completed_steps):
            self._show_tutorial(
                "START TRIAL",
                "Click the cards in the timeline to begin each trial.",
                "tutorial_start_trial"
            )

    def _handle_upgrade_modal_event(self, event: pygame.event.Event) -> bool:
        """Handle events for the upgrade purchase modal."""
        if not self.show_upgrade_modal or not self.upgrade_modal_card:
            return False
        
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            
            # Check skill selection buttons
            if hasattr(self, 'upgrade_skill_buttons'):
                for skill, btn_rect in self.upgrade_skill_buttons.items():
                    if btn_rect.collidepoint(mx, my):
                        print(f"[DEBUG] Upgrade skill selected: {skill}")
                        self.upgrade_skill_selected = skill
                        return True
            
            # Check place button
            if hasattr(self, 'upgrade_place_btn') and self.upgrade_place_btn.collidepoint(mx, my):
                card = self.upgrade_modal_card
                card_value = self._get_card_value(card)
                king_can_afford = self.king_dice[1] >= card_value
                rookie_can_afford = self.jack_dice[1] >= card_value
                can_afford = king_can_afford or rookie_can_afford
                
                if self.upgrade_skill_selected and can_afford:
                    # Place in hand (no cost yet - cost paid when attaching to character)
                    self.upgrade_slots[self.upgrade_slot_index] = None
                    self.hand_cards.append(card)
                    self.hand_card_skills[card] = self.upgrade_skill_selected
                    print(f"[DEBUG] Upgrade placed in hand: {card.key}, skill: {self.upgrade_skill_selected} (cost will be paid on attach)")
                    # Show tutorial for attaching upgrade
                    if len(self.hand_cards) == 1:  # First upgrade purchased
                        self._show_tutorial(
                            "ATTACH UPGRADE",
                            "Great! Your upgrade is in your hand. Click on the 'Attached Upgrade' area below a character card to attach it. The cost will be deducted from that character's Ether.",
                            "tutorial_attach_upgrade"
                        )
                    # Close modal
                    self.show_upgrade_modal = False
                    self.upgrade_modal_card = None
                    self.upgrade_skill_selected = None
                    self.upgrade_slot_index = None
                elif not can_afford:
                    print(f"[DEBUG] Cannot place upgrade in hand: Neither character can afford {card_value} Ether (King: {self.king_dice[1]}, Rookie: {self.jack_dice[1]})")
                return True
            
            # Check cancel button
            if hasattr(self, 'upgrade_cancel_btn') and self.upgrade_cancel_btn.collidepoint(mx, my):
                print("[DEBUG] Upgrade modal cancelled")
                self.show_upgrade_modal = False
                self.upgrade_modal_card = None
                self.upgrade_skill_selected = None
                self.upgrade_slot_index = None
                return True
        
        return True  # Block other events during modal

    def _handle_draw_phase_event(self, event: pygame.event.Event) -> bool:
        """Handle events during the draw phase (drawing cards from decks)."""
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return False
        
        mx, my = event.pos
        
        # Handle rules modal continue button
        if self.draw_phase_stage == 4:
            if self.modal_continue_rect and self.modal_continue_rect.collidepoint(mx, my):
                print("[DEBUG] Rules modal continue clicked, showing encounter rules")
                self.draw_phase_stage = 5  # Encounter rules modal
                self.modal_continue_rect = None
                return True
            return True  # Block other clicks during rules modal
        if self.draw_phase_stage == 5:
            if self.modal_continue_rect and self.modal_continue_rect.collidepoint(mx, my):
                print("[DEBUG] Encounter rules modal continue clicked, showing end rules")
                self.draw_phase_stage = 6  # End rules modal
                self.modal_continue_rect = None
                return True
            return True  # Block other clicks during encounter rules modal
        if self.draw_phase_stage == 6:
            if self.modal_continue_rect and self.modal_continue_rect.collidepoint(mx, my):
                print("[DEBUG] End rules modal continue clicked, starting gameplay")
                self.draw_phase_stage = 7  # Gameplay phase
                self.modal_continue_rect = None
                # Show tutorial for upgrade phase gameplay
                self._show_tutorial(
                    "UPGRADE PHASE",
                    "You're now in the UPGRADE phase. Click on upgrade cards in the top-left slots to purchase them. Select a skill enhancement and place them in your hand. Then attach upgrades to your characters by clicking the 'Attached Upgrade' area below them. When ready, click 'COMPLETE UPGRADES' to enter the TIMELINE phase.",
                    "tutorial_upgrade_phase"
                )
                return True
            return True  # Block other clicks during end rules modal
        
        # Handle deck clicks for drawing cards
        if self.draw_phase_stage == 1:  # Draw upgrades
            if "upgrade" in self.deck_positions:
                deck_x, deck_y = self.deck_positions["upgrade"]
                deck_rect = pygame.Rect(deck_x, deck_y, self.card_width, self.card_height)
                if deck_rect.collidepoint(mx, my) and len(self.upgrade_cards) >= 3:
                    print("[DEBUG] Upgrade deck clicked, drawing 3 cards")
                    # Draw 3 cards from upgrade deck to slots
                    for i in range(3):
                        if self.upgrade_cards:
                            card = self.upgrade_cards.pop(0)  # Take from top
                            self.upgrade_slots[i] = card
                            self.card_face_up[card] = True  # Face up in slot
                            # Remove from card positions (will be repositioned)
                            if card in self.card_positions:
                                del self.card_positions[card]
                    self.draw_phase_stage = 2  # Move to witness
                    self._init_z_order()
                    # Show tutorial for drawing witnesses
                    self._show_tutorial(
                        "DRAW WITNESSES",
                        "Now click the Witness deck to draw 3 witness cards. Witnesses help you gather evidence by using Reputation (blue dice).",
                        "tutorial_draw_witnesses"
                    )
                    return True
        
        elif self.draw_phase_stage == 2:  # Draw witnesses
            if "witness" in self.deck_positions:
                deck_x, deck_y = self.deck_positions["witness"]
                deck_rect = pygame.Rect(deck_x, deck_y, self.card_width, self.card_height)
                if deck_rect.collidepoint(mx, my) and len(self.witness_deck) >= 3:
                    print("[DEBUG] Witness deck clicked, drawing 3 cards")
                    for i in range(3):
                        if self.witness_deck:
                            card = self.witness_deck.pop(0)
                            self.witness_slots[i] = card
                            self.card_face_up[card] = True
                            if card in self.card_positions:
                                del self.card_positions[card]
                    self.draw_phase_stage = 3  # Move to location
                    self._init_z_order()
                    # Show tutorial for drawing locations
                    self._show_tutorial(
                        "DRAW LOCATIONS",
                        "Now click the Location deck to draw 3 location cards. Locations help you gather evidence by using Ion (purple dice).",
                        "tutorial_draw_locations"
                    )
                    return True
        
        elif self.draw_phase_stage == 3:  # Draw locations
            if "location" in self.deck_positions:
                deck_x, deck_y = self.deck_positions["location"]
                deck_rect = pygame.Rect(deck_x, deck_y, self.card_width, self.card_height)
                if deck_rect.collidepoint(mx, my) and len(self.location_deck) >= 3:
                    print("[DEBUG] Location deck clicked, drawing 3 cards")
                    for i in range(3):
                        if self.location_deck:
                            card = self.location_deck.pop(0)
                            self.location_slots[i] = card
                            self.card_face_up[card] = True
                            if card in self.card_positions:
                                del self.card_positions[card]
                    self.draw_phase_stage = 4  # Move to rules
                    self._init_z_order()
                    return True
        
        return False

    def _handle_trial_event(self, event: pygame.event.Event) -> bool:
        """Handle events during a trial."""
        if not self.show_trial_modal or not self.active_trial_card:
            return False
        
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            
            # Check cancel button
            if hasattr(self, 'trial_cancel_btn') and self.trial_cancel_btn.collidepoint(mx, my):
                print("[DEBUG] Trial cancelled")
                self.show_trial_modal = False
                self.active_trial_card = None
                self.trial_character_choice = None
                self.trial_skill_selected = None
                self.trial_result = None
                return True
            
            # Check character choice buttons (must choose before skill)
            if hasattr(self, 'trial_character_buttons') and self.trial_result is None:
                for choice_key, btn_rect in self.trial_character_buttons.items():
                    if btn_rect.collidepoint(mx, my):
                        print(f"[DEBUG] Character choice: {choice_key}")
                        self.trial_character_choice = choice_key
                        self.trial_skill_selected = None
                        return True
            
            # Check skill buttons (only after character choice)
            if hasattr(self, 'trial_skill_buttons') and self.trial_character_choice and self.trial_result is None:
                for skill, btn_rect in self.trial_skill_buttons.items():
                    if btn_rect.collidepoint(mx, my):
                        print(f"[DEBUG] Skill selected: {skill}")
                        self.trial_skill_selected = skill
                        return True
            
            # Check FateD10 click in modal - start roll animation
            if hasattr(self, 'trial_d10_rect') and self.trial_character_choice and self.trial_skill_selected and self.trial_result is None and not self.trial_d10_animating:
                if self.trial_d10_rect.collidepoint(mx, my):
                    self.trial_d10_animating = True
                    self.trial_d10_anim_start = pygame.time.get_ticks()
                    print("[DEBUG] FateD10 roll animation started")
                    return True
        
        return True  # Block other events during trial

    def _apply_trial_result(self) -> None:
        """Apply the result of a trial. Uses trial_result_choice for success rewards."""
        if not self.active_trial_card or self.trial_result is None:
            return
        card = self.active_trial_card
        card_value = self._get_card_value(card)
        skill_full = {"ENG": "Engagement", "CHA": "Charisma", "ANA": "Analysis"}[self.trial_skill_selected]
        combined_skill = self._get_trial_skill_bonus(skill_full)
        total = self.trial_result + combined_skill
        success = total >= card_value
        diff = max(0, total - card_value)  # Margin of success
        
        if success:
            if card in self.timeline_cards:
                self.timeline_cards.remove(card)
            choice = self.trial_result_choice or "evidence"
            if choice == "evidence":
                old_evidence = self.evidence_required
                self.evidence_required = max(0, self.evidence_required - card_value - diff)
                # Spawn success particles proportional to evidence cleared!
                evidence_cleared = old_evidence - self.evidence_required
                if evidence_cleared > 0 and self.window_rect:
                    # Spawn particles at evidence display location
                    for _ in range(min(evidence_cleared * 2, 30)):
                        self._spawn_dice_particles(
                            self.window_rect.right - int(100 * self.scale),
                            self.window_rect.bottom - int(150 * self.scale),
                            random.choice([(0, 255, 255), (100, 255, 100), (255, 215, 0)])
                        )
            elif choice == "reputation":
                self.evidence_required = max(0, self.evidence_required - card_value)
                current_rep = self.king_dice[0] + self.jack_dice[0]
                add_rep = min(diff, 12 - current_rep)
                for _ in range(add_rep):
                    if self.king_dice[0] < 6:
                        self.king_dice[0] += 1
                    elif self.jack_dice[0] < 6:
                        self.jack_dice[0] += 1
            elif choice == "ion":
                self.evidence_required = max(0, self.evidence_required - card_value)
                current_ion = self.king_dice[2] + self.jack_dice[2]
                add_ion = min(diff, 12 - current_ion)
                for _ in range(add_ion):
                    if self.king_dice[2] < 6:
                        self.king_dice[2] += 1
                    elif self.jack_dice[2] < 6:
                        self.jack_dice[2] += 1
            elif choice == "ether":
                self.evidence_required = max(0, self.evidence_required - card_value)
                current_ether = self.king_dice[1] + self.jack_dice[1]
                add_ether = min(diff, 12 - current_ether)
                for _ in range(add_ether):
                    if self.king_dice[1] < 6:
                        self.king_dice[1] += 1
                    elif self.jack_dice[1] < 6:
                        self.jack_dice[1] += 1
            if diff > 5:
                current_ether = self.king_dice[1] + self.jack_dice[1]
                if current_ether < 12:
                    if self.king_dice[1] < 6:
                        self.king_dice[1] += 1
                    elif self.jack_dice[1] < 6:
                        self.jack_dice[1] += 1
            # Clear any active glitch effect on success
            self._clear_glitch()
            self._advance_crime_if_needed()
            if self._is_encounter_card(card):
                self._refill_empty_slots()
                self.game_phase = "UPGRADE"
        else:
            if card in self.timeline_cards:
                self.timeline_cards.remove(card)
            if self.trial_skill_selected == "ANA":
                self.evidence_required += diff
                # Trigger glitch effect for evidence increase
                self._trigger_glitch(0.7)
            else:
                # Combat failure: damage based on character choice, and BOTH lose at least 1 HP
                choice = self.trial_character_choice or "both"
                if choice == "main":
                    self.king_stats["HP"] = max(0, self.king_stats["HP"] - diff)
                    self.rookie_stats["HP"] = max(0, self.rookie_stats["HP"] - 1)
                elif choice == "rookie":
                    self.king_stats["HP"] = max(0, self.king_stats["HP"] - 1)
                    self.rookie_stats["HP"] = max(0, self.rookie_stats["HP"] - diff)
                else:
                    dmg_each = (diff + 1) // 2
                    self.king_stats["HP"] = max(0, self.king_stats["HP"] - max(dmg_each, 1))
                    self.rookie_stats["HP"] = max(0, self.rookie_stats["HP"] - max(diff - dmg_each, 1))
                # Trigger intense glitch effect for combat damage!
                self._trigger_glitch(1.0)
            if self._is_encounter_card(card):
                self._refill_empty_slots()
                self.game_phase = "UPGRADE"
        self._check_end_conditions()

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.active:
            return False

        # Close button always works - check first before any modal consumes the event
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.close_button_rect and self.close_button_rect.collidepoint(event.pos):
                self.close()
                return True

        if self.show_game_over_modal:
            return self._handle_game_over_modal_event(event)

        # Handle crime congratulations modal (before other modals)
        if self.show_crime_congrats_modal:
            return self._handle_crime_congrats_modal_event(event)
        
        # Handle tutorial modal (before other modals)
        if self.show_tutorial_modal:
            return self._handle_tutorial_modal_event(event)

        # Handle setup modals first
        if self.show_setup_modal and not self.setup_complete:
            return self._handle_setup_modal_event(event)
        
        # Handle draw phase
        if self.draw_phase_stage in [1, 2, 3, 4, 5, 6]:
            return self._handle_draw_phase_event(event)
        
        # Handle trial result modal (Step 3)
        if self.show_trial_result_modal:
            return self._handle_trial_result_modal_event(event)
        
        # Handle trial modal
        if self.show_trial_modal:
            return self._handle_trial_event(event)
        
        # Handle upgrade modal
        if self.show_upgrade_modal:
            return self._handle_upgrade_modal_event(event)

        # Initialize z-order if needed
        if not self.card_z_order:
            self._init_z_order()

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self.selected_cards:
                    self._clear_selection()
                else:
                    self.close()
                return True
            elif event.key == pygame.K_SPACE:
                # Flip selected cards only (no hovered card flip)
                print(f"[DEBUG] Space key pressed. Selected: {len(self.selected_cards)}")
                if self.selected_cards:
                    print(f"[DEBUG] Flipping {len(self.selected_cards)} selected cards")
                    self._flip_selected_cards()
                    return True
            elif event.key == pygame.K_a and pygame.key.get_mods() & pygame.KMOD_CTRL:
                # Ctrl+A: Select all cards
                self._select_cards(self.card_z_order[:])
                return True
            elif event.key == pygame.K_DELETE or event.key == pygame.K_BACKSPACE:
                # Deselect all
                self._clear_selection()
                return True

        if event.type == pygame.MOUSEMOTION:
            mx, my = event.pos
            
            # Check for button hover
            self.hovered_button = None
            if self.complete_upgrades_button_rect and self.complete_upgrades_button_rect.collidepoint(mx, my):
                self.hovered_button = "complete_upgrades"
            elif self.close_button_rect and self.close_button_rect.collidepoint(mx, my):
                self.hovered_button = "close"
            
            # Update hovered card
            self.hovered_card = self._get_card_at_position(mx, my)
            
            # Calculate percentage relative to window (for debug display)
            if self.window_rect and self.window_rect.width > 0 and self.window_rect.height > 0:
                rel_x = mx - self.window_rect.x
                rel_y = my - self.window_rect.y
                self.mouse_x_percent = max(0.0, min(100.0, (rel_x / self.window_rect.width) * 100.0))
                self.mouse_y_percent = max(0.0, min(100.0, (rel_y / self.window_rect.height) * 100.0))
            
            # Handle dragging cards
            if self.dragging:
                self._update_drag(mx, my)
                return True
            
            # Handle selection box
            if self.drawing_selection_box and self.selection_box_start:
                self.selection_box_end = (mx, my)
                # Update selection based on box
                sx, sy = self.selection_box_start
                cards_in_box = self._get_cards_in_rect(sx, sy, mx, my)
                self.selected_cards = cards_in_box
                return True

        if event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = event.pos
            
            # Check for complete upgrades button click
            if self.complete_upgrades_button_rect and self.complete_upgrades_button_rect.collidepoint(mx, my):
                if self.draw_phase_stage == 7 and self.game_phase == "UPGRADE":
                    print("[DEBUG] Complete upgrades clicked: Moving from UPGRADE to TIMELINE")
                    self.game_phase = "TIMELINE"
                    # Show tutorial for timeline phase
                    self._show_tutorial(
                        "TIMELINE PHASE",
                        "You're now in the TIMELINE phase! Click on witness or location cards in the middle slots to add them to the timeline (if you have enough Reputation or Ion). Green Text = You Qualify, Red Text = You don't.",
                        "tutorial_timeline_phase"
                    )
                return True
            
            # Check for close button click
            if self.close_button_rect and self.close_button_rect.collidepoint(mx, my):
                self.close()
                return True
            
            # Check for timeline card click to start trial (only during TIMELINE phase)
            if self.draw_phase_stage == 7 and not self.show_trial_modal and self.game_phase == "TIMELINE":
                # Check if clicked on a timeline card (same positioning as draw - anchored right)
                if "encounter" in self.deck_positions and self.window_rect:
                    enc_x, enc_y = self.deck_positions["encounter"]
                    timeline_y = enc_y
                    card_gap = int(10 * self.scale)
                    timeline_width = self.card_width * 4 + card_gap * 3
                    padding = int(30 * self.scale)
                    timeline_x = self.window_rect.right - timeline_width - padding
                    
                    for i, card in enumerate(self.timeline_cards):
                        card_x = timeline_x + i * (self.card_width + card_gap)
                        card_rect = pygame.Rect(card_x, timeline_y, self.card_width, self.card_height)
                        if card_rect.collidepoint(mx, my):
                            print(f"[DEBUG] Timeline card clicked: {card.key}")
                            self.active_trial_card = card
                            self.trial_character_choice = None
                            self.trial_skill_selected = None
                            self.trial_result = None
                            self.show_trial_modal = True
                            # Show tutorial for first trial
                            if "tutorial_first_trial" not in self.tutorial_completed_steps:
                                self._show_tutorial(
                                    "START TRIAL",
                                    "Choose who faces: Main Character, Rookie, or Both (half bonuses). Then select a skill and roll the FateD10. Beat the target to reduce evidence and win rewards!",
                                    "tutorial_first_trial"
                                )
                            return True
            
            # Check for phase confirm button click
            if self.draw_phase_stage == 7 and self.phase_confirm_btn and self.phase_confirm_btn.collidepoint(mx, my):
                if self.game_phase == "UPGRADE":
                    print("[DEBUG] Phase confirmed: Moving from UPGRADE to TIMELINE")
                    self.game_phase = "TIMELINE"
                return True
            
            # Check for slot card click (during gameplay)
            if self.draw_phase_stage == 7 and not self.show_trial_modal and not self.show_upgrade_modal:
                # UPGRADE PHASE: Can buy upgrades and attach them
                if self.game_phase == "UPGRADE":
                    # Check upgrade slots - show purchase modal
                    title_bar_offset = self.title_bar_rect.height if self.title_bar_rect else 0
                    slot_start_x, slot_start_y = self._percent_to_pixel(5.0, 5.0)
                    slot_start_y += title_bar_offset
                    upgrade_card_gap = int(34 * self.scale)
                    for i, card in enumerate(self.upgrade_slots):
                        if card:
                            slot_x = slot_start_x + (self.card_width + upgrade_card_gap) * i
                            slot_rect = pygame.Rect(slot_x, slot_start_y, self.card_width, self.card_height)
                            if slot_rect.collidepoint(mx, my):
                                print(f"[DEBUG] Upgrade slot card clicked: {card.key}")
                                # Show upgrade purchase modal
                                self.upgrade_modal_card = card
                                self.upgrade_slot_index = i
                                self.upgrade_skill_selected = None
                                self.show_upgrade_modal = True
                                return True
                    
                    # Check ATTACHED UPGRADE slots to attach cards from hand
                    if self.hand_cards:
                        # King's attached upgrade slot
                        if self.king_spades and self.king_spades in self.card_positions:
                            kx, ky = self.card_positions[self.king_spades]
                            stats_start_y = ky + self.card_height + int(20 * self.scale)
                            stat_line_height = int(18 * self.scale)
                            stat_y = stats_start_y + len(self.king_stats) * stat_line_height
                            upgrade_area_y = stat_y + int(10 * self.scale)
                            upgrade_rect = pygame.Rect(kx, upgrade_area_y, self.card_width, self.card_height)
                            if upgrade_rect.collidepoint(mx, my):
                                # Check if King can afford the upgrade
                                card = self.hand_cards[0]  # Check first card without removing yet
                                card_value = self._get_card_value(card)
                                king_ether = self.king_dice[1]
                                
                                if king_ether >= card_value:
                                    # Attach card to King and pay cost
                                    card = self.hand_cards.pop(0)
                                    skill = self.hand_card_skills.get(card)
                                    self.king_attached_upgrades.append(card)
                                    
                                    # Deduct cost from King's Ether die
                                    self.king_dice[1] = max(0, king_ether - card_value)
                                    
                                    if skill:
                                        self._apply_upgrade_skill(self.king_stats, skill, card_value)
                                        del self.hand_card_skills[card]
                                    print(f"[DEBUG] Attached {card.key} to King, +{card_value} {skill}, paid {card_value} Ether (King Ether: {king_ether} → {self.king_dice[1]})")
                                    # Check if we should prompt to complete upgrades
                                    self._check_and_show_complete_upgrades_tutorial()
                                else:
                                    print(f"[DEBUG] King cannot afford upgrade: needs {card_value} Ether, has {king_ether}")
                                return True
                        
                        # Rookie's attached upgrade slot
                        if self.jack_spades and self.jack_spades in self.card_positions:
                            jx, jy = self.card_positions[self.jack_spades]
                            stats_start_y = jy + self.card_height + int(20 * self.scale)
                            stat_line_height = int(18 * self.scale)
                            stat_y = stats_start_y + len(self.rookie_stats) * stat_line_height
                            upgrade_area_y = stat_y + int(10 * self.scale)
                            upgrade_rect = pygame.Rect(jx, upgrade_area_y, self.card_width, self.card_height)
                            if upgrade_rect.collidepoint(mx, my):
                                # Check if Rookie can afford the upgrade
                                card = self.hand_cards[0]  # Check first card without removing yet
                                card_value = self._get_card_value(card)
                                rookie_ether = self.jack_dice[1]
                                
                                if rookie_ether >= card_value:
                                    # Attach card to Rookie and pay cost
                                    card = self.hand_cards.pop(0)
                                    skill = self.hand_card_skills.get(card)
                                    self.rookie_attached_upgrades.append(card)
                                    
                                    # Deduct cost from Rookie's Ether die
                                    self.jack_dice[1] = max(0, rookie_ether - card_value)
                                    
                                    if skill:
                                        self._apply_upgrade_skill(self.rookie_stats, skill, card_value)
                                        del self.hand_card_skills[card]
                                    print(f"[DEBUG] Attached {card.key} to Rookie, +{card_value} {skill}, paid {card_value} Ether (Rookie Ether: {rookie_ether} → {self.jack_dice[1]})")
                                    # Check if we should prompt to complete upgrades
                                    self._check_and_show_complete_upgrades_tutorial()
                                else:
                                    print(f"[DEBUG] Rookie cannot afford upgrade: needs {card_value} Ether, has {rookie_ether}")
                                return True
                
                # TIMELINE PHASE: Can add cards to timeline and do trials
                if self.game_phase == "TIMELINE":
                    # Allow clicking encounter deck to draw a card to the encounter slot
                    if (
                        self.encounter_deck
                        and self.encounter_slot is None  # Only if slot is empty
                        and "encounter" in self.deck_positions
                    ):
                        enc_x, enc_y = self.deck_positions["encounter"]
                        enc_rect = pygame.Rect(enc_x, enc_y, self.card_width, self.card_height)
                        if enc_rect.collidepoint(mx, my):
                            encounter_card = self.encounter_deck.pop(0)
                            self.encounter_slot = encounter_card
                            self.card_face_up[encounter_card] = True
                            print(f"[DEBUG] Drew encounter card to slot: {encounter_card.key}")
                            return True
                    
                    # Check encounter slot - click adds to timeline AND opens trial immediately
                    if self.encounter_slot and "encounter" in self.deck_positions:
                        enc_x, enc_y = self.deck_positions["encounter"]
                        encounter_slot_offset = int(30 * self.scale)
                        slot_x = enc_x + self.card_width + encounter_slot_offset
                        slot_rect = pygame.Rect(slot_x, enc_y, self.card_width, self.card_height)
                        if slot_rect.collidepoint(mx, my):
                            print(f"[DEBUG] Encounter slot card clicked: {self.encounter_slot.key}")
                            card = self.encounter_slot
                            self.encounter_slot = None
                            self.timeline_cards.append(card)
                            # Immediately open trial modal (saves a click)
                            self.active_trial_card = card
                            self.trial_character_choice = None
                            self.trial_skill_selected = None
                            self.trial_result = None
                            self.show_trial_modal = True
                            if "tutorial_first_trial" not in self.tutorial_completed_steps:
                                self._show_tutorial(
                                    "START TRIAL",
                                    "Choose who faces: Main Character, Rookie, or Both (half bonuses). Then select a skill and roll the FateD10. Beat the target to reduce evidence and win rewards!",
                                    "tutorial_first_trial"
                                )
                            return True
                    # Check witness slots
                    if "witness" in self.deck_positions:
                        wit_x, wit_y = self.deck_positions["witness"]
                        card_gap = int(10 * self.scale)
                        slot_right_offset = int(self.window_rect.width * 0.05) if self.window_rect else int(50 * self.scale)
                        start_x = wit_x + self.card_width + card_gap + slot_right_offset
                        for i, card in enumerate(self.witness_slots):
                            if card:
                                slot_x = start_x + (self.card_width + card_gap) * i
                                slot_rect = pygame.Rect(slot_x, wit_y, self.card_width, self.card_height)
                                if slot_rect.collidepoint(mx, my):
                                    print(f"[DEBUG] Witness slot card clicked: {card.key}")
                                    # Witnesses need Rep
                                    card_value = self._get_card_value(card)
                                    total_rep = self.king_dice[0] + self.jack_dice[0]
                                    if total_rep >= card_value:
                                        self.witness_slots[i] = None
                                        self.timeline_cards.append(card)
                                        print(f"[DEBUG] Witness added to timeline (Rep: {total_rep} >= {card_value})")
                                        self._check_and_show_start_trial_tutorial()
                                    else:
                                        print(f"[DEBUG] Not enough Rep ({total_rep} < {card_value})")
                                    return True
                    
                    # Check location slots
                    if "location" in self.deck_positions:
                        loc_x, loc_y = self.deck_positions["location"]
                        card_gap = int(10 * self.scale)
                        slot_right_offset = int(self.window_rect.width * 0.05) if self.window_rect else int(50 * self.scale)
                        start_x = loc_x + self.card_width + card_gap + slot_right_offset
                        for i, card in enumerate(self.location_slots):
                            if card:
                                slot_x = start_x + (self.card_width + card_gap) * i
                                slot_rect = pygame.Rect(slot_x, loc_y, self.card_width, self.card_height)
                                if slot_rect.collidepoint(mx, my):
                                    print(f"[DEBUG] Location slot card clicked: {card.key}")
                                    # Locations need Ion
                                    card_value = self._get_card_value(card)
                                    total_ion = self.king_dice[2] + self.jack_dice[2]
                                    if total_ion >= card_value:
                                        self.location_slots[i] = None
                                        self.timeline_cards.append(card)
                                        print(f"[DEBUG] Location added to timeline (Ion: {total_ion} >= {card_value})")
                                        self._check_and_show_start_trial_tutorial()
                                    else:
                                        print(f"[DEBUG] Not enough Ion ({total_ion} < {card_value})")
                                    return True
            
            # Left click
            if event.button == 1:
                # Update click tracking (no double-click flip)
                current_time = pygame.time.get_ticks()
                self.last_click_time = current_time
                self.last_click_pos = (mx, my)
                
                card = self._get_card_at_position(mx, my)
                
                if card:
                    # Check modifiers
                    mods = pygame.key.get_mods()
                    shift_held = mods & pygame.KMOD_SHIFT
                    ctrl_held = mods & pygame.KMOD_CTRL
                    
                    if ctrl_held:
                        # Ctrl+click: select entire deck this card belongs to
                        deck = self._get_deck_for_card(card)
                        if deck:
                            deck_cards = self._get_deck_cards(deck)
                            self._select_cards(deck_cards, add_to_selection=shift_held)
                        else:
                            self._select_card(card, add_to_selection=shift_held)
                    elif shift_held:
                        # Shift+click: add to selection
                        self._select_card(card, add_to_selection=True)
                    else:
                        # Regular click
                        if card in self.selected_cards:
                            # Clicked on already selected card - start dragging
                            pass
                        else:
                            # Select this card
                            self._select_card(card, add_to_selection=False)
                    
                    # Start dragging
                    self._start_drag(mx, my)
                    return True
                else:
                    # Clicked on empty space
                    mods = pygame.key.get_mods()
                    if not (mods & pygame.KMOD_SHIFT):
                        self._clear_selection()
                    
                    # Start selection box
                    self.selection_box_start = (mx, my)
                    self.selection_box_end = (mx, my)
                    self.drawing_selection_box = True
                    return True
            
            # Right click - no action (flip removed)
            elif event.button == 3:
                # Right-click functionality removed - only spacebar flip for selected cards
                return False

        if event.type == pygame.MOUSEBUTTONUP:
            mx, my = event.pos
            
            if event.button == 1:
                # Stop dragging
                if self.dragging:
                    self._end_drag()
                
                # Finalize selection box
                if self.drawing_selection_box:
                    self.drawing_selection_box = False
                    if self.selection_box_start and self.selection_box_end:
                        sx, sy = self.selection_box_start
                        ex, ey = self.selection_box_end
                        # Only select if box is meaningful size
                        if abs(ex - sx) > 5 or abs(ey - sy) > 5:
                            cards_in_box = self._get_cards_in_rect(sx, sy, ex, ey)
                            if cards_in_box:
                                mods = pygame.key.get_mods()
                                self._select_cards(cards_in_box, add_to_selection=mods & pygame.KMOD_SHIFT)
                    self.selection_box_start = None
                    self.selection_box_end = None
                return True

        return False

    def draw(self) -> None:
        if not self.active:
            return

        if not self.window_rect:
            return

        old_clip = self.screen.get_clip()
        self.screen.set_clip(self.window_rect)

        # Draw title bar with cyberpunk gradient
        if self.title_bar_rect:
            # Create gradient surface
            title_surf = pygame.Surface((self.title_bar_rect.width, self.title_bar_rect.height), pygame.SRCALPHA)
            for y in range(self.title_bar_rect.height):
                # Gradient from dark purple to dark blue
                progress = y / self.title_bar_rect.height
                r = int(25 + 15 * progress)
                g = int(15 + 20 * progress)
                b = int(40 + 30 * progress)
                pygame.draw.line(title_surf, (r, g, b, 255), (0, y), (self.title_bar_rect.width, y))
            self.screen.blit(title_surf, self.title_bar_rect.topleft)
            
            # Animated neon line at bottom
            import math
            glow_intensity = (math.sin(self.neon_glow_time * 3) + 1) / 2
            line_color = (
                int(0 + 100 * glow_intensity),
                int(200 + 55 * glow_intensity),
                255
            )
            pygame.draw.line(
                self.screen, line_color,
                (self.title_bar_rect.x, self.title_bar_rect.bottom - 1),
                (self.title_bar_rect.right, self.title_bar_rect.bottom - 1), 2
            )
            # Glow effect under line
            glow_surf = pygame.Surface((self.title_bar_rect.width, 4), pygame.SRCALPHA)
            glow_surf.fill((*line_color, int(50 * glow_intensity)))
            self.screen.blit(glow_surf, (self.title_bar_rect.x, self.title_bar_rect.bottom))
            
            if self.label_font:
                # Title with subtle glow
                title_text = self.label_font.render("CIVITAS NIHILIUM", True, (0, 255, 255))
                title_x = self.title_bar_rect.x + int(15 * self.scale)
                title_y = self.title_bar_rect.centery - title_text.get_height() // 2
                # Draw glow behind text
                glow_text = self.label_font.render("CIVITAS NIHILIUM", True, (0, 150, 200))
                self.screen.blit(glow_text, (title_x + 1, title_y + 1))
                self.screen.blit(title_text, (title_x, title_y))
                if self.debug_font:
                    card_values_text = "CARD VALUES: A=1, 2-10=face, J=11, Q=12, K=12"
                    card_values_surf = self.debug_font.render(card_values_text, True, (100, 180, 200))
                    card_values_y = self.title_bar_rect.bottom + int(2 * self.scale)
                    self.screen.blit(card_values_surf, (title_x, card_values_y))
        
        # Draw mouse coordinates at top left
        if self.debug_font and self.window_rect:
            # Get current mouse position and update percentages
            mx, my = pygame.mouse.get_pos()
            if self.window_rect.width > 0 and self.window_rect.height > 0:
                rel_x = mx - self.window_rect.x
                rel_y = my - self.window_rect.y
                x_percent = max(0.0, min(100.0, (rel_x / self.window_rect.width) * 100.0))
                y_percent = max(0.0, min(100.0, (rel_y / self.window_rect.height) * 100.0))
            else:
                x_percent = 0.0
                y_percent = 0.0
            
            coord_text = f"X: {x_percent:.1f}%  Y: {y_percent:.1f}%"
            coord_surf = self.debug_font.render(coord_text, True, (0, 255, 255))
            # Position just under the title bar line
            coord_x = self.window_rect.x + int(5 * self.scale)
            coord_y = (self.title_bar_rect.bottom + int(2 * self.scale)) if self.title_bar_rect else self.window_rect.y + int(5 * self.scale)
            self.screen.blit(coord_surf, (coord_x, coord_y))
        
        # Draw complete upgrades button (cyberpunk style, pulses to draw attention)
        if self.complete_upgrades_button_rect and self.draw_phase_stage == 7:
            import math
            # Use pygame time for reliable animation (neon_glow_time may not update if update() has low dt)
            t = pygame.time.get_ticks() / 1000.0
            btn_pulse = (math.sin(t * 5) + 1) / 2  # 0 to 1, ~0.6 sec cycle
            is_hovered = self.hovered_button == "complete_upgrades"
            should_pulse = self.game_phase == "UPGRADE" and (len(self.hand_cards) > 0 or self._should_prompt_complete_upgrades())
            
            # Glow effect when hovered or when player should click (visible pulse)
            if is_hovered or should_pulse:
                inflate = int(6 + 12 * btn_pulse) if should_pulse else 6
                glow_rect = self.complete_upgrades_button_rect.inflate(inflate, inflate)
                glow_surf = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
                alpha = int(40 + 120 * btn_pulse) if should_pulse else int(60 + 40 * btn_pulse)
                glow_surf.fill((0, 255, 120, alpha))
                self.screen.blit(glow_surf, glow_rect.topleft)
            
            # Button background gradient
            btn_surf = pygame.Surface((self.complete_upgrades_button_rect.width, self.complete_upgrades_button_rect.height), pygame.SRCALPHA)
            for y in range(self.complete_upgrades_button_rect.height):
                progress = y / self.complete_upgrades_button_rect.height
                if is_hovered:
                    r, g, b = 0, int(100 + 50 * (1 - progress)), int(50 * progress)
                elif should_pulse:
                    pulse_boost = int(25 * btn_pulse)
                    r, g, b = 0, int(60 + 30 * (1 - progress) + pulse_boost), int(30 * progress + pulse_boost)
                else:
                    r, g, b = 0, int(60 + 30 * (1 - progress)), int(30 * progress)
                pygame.draw.line(btn_surf, (r, g, b, 255), (0, y), (self.complete_upgrades_button_rect.width, y))
            self.screen.blit(btn_surf, self.complete_upgrades_button_rect.topleft)
            
            border_pulse = int(75 * btn_pulse) if should_pulse and not is_hovered else 0
            border_color = (0, 255, 100) if is_hovered else (0, min(255, 180 + border_pulse), min(255, 80 + border_pulse))
            pygame.draw.rect(self.screen, border_color, self.complete_upgrades_button_rect, 2)
            
            if self.debug_font:
                if self.game_phase == "UPGRADE":
                    button_text = self.debug_font.render("COMPLETE UPGRADES", True, (200, 255, 200))
                else:  # TIMELINE
                    button_text = self.debug_font.render("TRIAL PHASE", True, (200, 255, 200))
                self.screen.blit(button_text, button_text.get_rect(center=self.complete_upgrades_button_rect.center))
        
        # Draw close button (cyberpunk style!)
        if self.close_button_rect:
            import math
            btn_pulse = (math.sin(self.neon_glow_time * 3 + 1) + 1) / 2
            is_hovered = self.hovered_button == "close"
            
            # Glow effect when hovered
            if is_hovered:
                glow_rect = self.close_button_rect.inflate(6, 6)
                glow_surf = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
                glow_surf.fill((255, 100, 100, int(60 + 40 * btn_pulse)))
                self.screen.blit(glow_surf, glow_rect.topleft)
            
            # Button background gradient
            btn_surf = pygame.Surface((self.close_button_rect.width, self.close_button_rect.height), pygame.SRCALPHA)
            for y in range(self.close_button_rect.height):
                progress = y / self.close_button_rect.height
                if is_hovered:
                    r, g, b = int(80 + 40 * (1 - progress)), int(30 * (1 - progress)), int(40 * progress)
                else:
                    r, g, b = int(40 + 20 * (1 - progress)), int(30 + 15 * progress), int(50 + 20 * progress)
                pygame.draw.line(btn_surf, (r, g, b, 255), (0, y), (self.close_button_rect.width, y))
            self.screen.blit(btn_surf, self.close_button_rect.topleft)
            
            border_color = (255, 100, 100) if is_hovered else (0, 255, 255)
            pygame.draw.rect(self.screen, border_color, self.close_button_rect, 2)
            
            if self.debug_font:
                close_text = self.debug_font.render("CLOSE", True, (255, 200, 200) if is_hovered else (200, 255, 255))
                self.screen.blit(close_text, close_text.get_rect(center=self.close_button_rect.center))
        
        # Draw background (content area below title bar)
        content_rect = pygame.Rect(
            self.window_rect.x,
            self.window_rect.y + (self.title_bar_rect.height if self.title_bar_rect else 0),
            self.window_rect.width,
            self.window_rect.height - (self.title_bar_rect.height if self.title_bar_rect else 0)
        )
        if self.bg_surface:
            try:
                scaled_bg = pygame.transform.smoothscale(
                    self.bg_surface, 
                    (content_rect.width, content_rect.height)
                )
                self.screen.blit(scaled_bg, content_rect.topleft)
            except Exception:
                pygame.draw.rect(self.screen, (12, 15, 25), content_rect)  # Darker cyberpunk bg
        else:
            pygame.draw.rect(self.screen, (12, 15, 25), content_rect)  # Darker cyberpunk bg
        
        # === CYBERPUNK BACKGROUND EFFECTS ===
        # (Ambient particles, grid, scanline removed - cleaner look)
        
        # Draw neon border (instead of simple border)
        self._draw_neon_border()
        pygame.draw.rect(self.screen, (0, 255, 255), self.window_rect, 2)

        # Initialize z-order if needed
        if not self.card_z_order:
            self._init_z_order()
        
        # Draw deck labels
        def draw_deck_label(deck_name: str, deck_list: List, label_text: str):
            if deck_list and deck_name in self.deck_positions:
                dx, dy = self.deck_positions[deck_name]
                if self.label_font:
                    label_surf = self.label_font.render(label_text, True, (255, 255, 255))
                    label_x = dx + (self.card_width - label_surf.get_width()) // 2
                    # Just under the deck - minimal gap (increased by 10%)
                    label_y = dy + self.card_height + int(6 * self.scale * 1.1)
                    self.screen.blit(label_surf, (label_x, label_y))
        
        # Draw three card-shaped outlines at 5%, 5%, evenly spaced horizontally
        title_bar_offset = self.title_bar_rect.height if self.title_bar_rect else 0
        slot_start_x, slot_start_y = self._percent_to_pixel(5.0, 5.0)
        slot_start_y += title_bar_offset
        upgrade_card_gap = int(34 * self.scale)  # Wider spacing for upgrade slots
        # Position three cards starting at 5%, 5%, evenly spaced horizontally
        for i in range(3):
            outline_x = slot_start_x + (self.card_width + upgrade_card_gap) * i
            outline_y = slot_start_y
            outline_rect = pygame.Rect(outline_x, outline_y, self.card_width, self.card_height)
            # Draw card outline
            pygame.draw.rect(self.screen, (60, 60, 80), outline_rect, 2)
        
        # Draw three card-shaped outlines to the right of witness and location decks, evenly spaced (5% more to the right)
        right_offset_5pct = int(self.window_rect.width * 0.05) if self.window_rect else int(50 * self.scale)
        if "witness" in self.deck_positions and "location" in self.deck_positions:
            wit_x, wit_y = self.deck_positions["witness"]
            loc_x, loc_y = self.deck_positions["location"]
            card_gap = int(10 * self.scale)  # Gap between cards
            # Use the rightmost deck (witness) as reference, 5% more to the right
            start_x = wit_x + self.card_width + card_gap + right_offset_5pct
            # Position three cards to the right, evenly spaced
            for i in range(3):
                outline_x = start_x + (self.card_width + card_gap) * i
                outline_y = wit_y  # Align with witness deck
                outline_rect = pygame.Rect(outline_x, outline_y, self.card_width, self.card_height)
                # Draw card outline
                pygame.draw.rect(self.screen, (60, 60, 80), outline_rect, 2)
                
                # Also draw at location deck Y position
                outline_y2 = loc_y
                outline_rect2 = pygame.Rect(outline_x, outline_y2, self.card_width, self.card_height)
                # Draw card outline
                pygame.draw.rect(self.screen, (60, 60, 80), outline_rect2, 2)
        
        # Draw Investigation Timeline area (anchored to right edge so it stays on screen)
        if "encounter" in self.deck_positions and self.window_rect:
            enc_x, enc_y = self.deck_positions["encounter"]
            timeline_y = enc_y
            # Pulse encounter deck when: (1) "Your Encounter deck is ready!" modal, or
            # (2) TIMELINE phase, timeline empty, no playable witness/location, encounter has cards
            pulse_encounter = (
                (self.show_setup_modal and self.setup_modal_stage == 4 and self.encounter_deck_built) or
                (self.draw_phase_stage == 7 and self.game_phase == "TIMELINE" and self.encounter_deck and
                 self.encounter_slot is None and not self.timeline_cards and not self._has_playable_witness_location())
            )
            if pulse_encounter:
                import math
                t = pygame.time.get_ticks() / 1000.0
                pulse = (math.sin(t * 4) + 1) / 2
                glow_rect = pygame.Rect(enc_x - int(8 * self.scale), enc_y - int(8 * self.scale),
                                        self.card_width + int(16 * self.scale), self.card_height + int(16 * self.scale))
                glow_surf = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
                alpha = int(40 + 100 * pulse)
                glow_surf.fill((0, 255, 200, alpha))
                self.screen.blit(glow_surf, glow_rect.topleft)
                border_alpha = int(150 + 105 * pulse)
                border_surf = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
                pygame.draw.rect(border_surf, (0, 255, 200, border_alpha), border_surf.get_rect(), 3)
                self.screen.blit(border_surf, glow_rect.topleft)
            # 4 card widths wide (with gaps between cards)
            card_gap = int(10 * self.scale)
            timeline_width = self.card_width * 4 + card_gap * 3
            padding = int(30 * self.scale)
            # Anchor timeline right edge to window right, keep on screen
            timeline_x = self.window_rect.right - timeline_width - padding
            timeline_height = self.card_height
            
            # Draw timeline cards
            for i, card in enumerate(self.timeline_cards):
                card_x = timeline_x + i * (self.card_width + card_gap)
                if card_x + self.card_width <= timeline_x + timeline_width:  # Only draw if fits
                    self._draw_card(card, card_x, timeline_y, face_up=True)
        
        # Draw slot cards (upgrade slots at 5%, 5%, evenly spaced horizontally)
        title_bar_offset = self.title_bar_rect.height if self.title_bar_rect else 0
        slot_start_x, slot_start_y = self._percent_to_pixel(5.0, 5.0)
        slot_start_y += title_bar_offset
        upgrade_card_gap = int(34 * self.scale)  # Wider spacing for upgrade slots
        # Pulse upgrade slots when in UPGRADE phase
        pulse_upgrade_slots = (self.draw_phase_stage == 7 and self.game_phase == "UPGRADE")
        for i, card in enumerate(self.upgrade_slots):
            slot_x = slot_start_x + (self.card_width + upgrade_card_gap) * i
            if pulse_upgrade_slots and card:
                import math
                t = pygame.time.get_ticks() / 1000.0
                pulse = (math.sin(t * 4) + 1) / 2
                glow_rect = pygame.Rect(slot_x - int(6 * self.scale), slot_start_y - int(6 * self.scale),
                                        self.card_width + int(12 * self.scale), self.card_height + int(12 * self.scale))
                glow_surf = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
                alpha = int(40 + 80 * pulse)
                glow_surf.fill((100, 255, 200, alpha))
                self.screen.blit(glow_surf, glow_rect.topleft)
            if card:
                self._draw_card(card, slot_x, slot_start_y, face_up=True)
                # Draw card value overlay with skill type
                if self.debug_font:
                    value = self._get_card_value(card)
                    # Check if either character can afford it
                    king_can_afford = self.king_dice[1] >= value
                    rookie_can_afford = self.jack_dice[1] >= value
                    can_afford = king_can_afford or rookie_can_afford
                    cost_color = (100, 255, 100) if can_afford else (255, 100, 100)
                    value_text = self.debug_font.render(f"Cost: {value} Ether", True, cost_color)
                    self.screen.blit(value_text, (slot_x, slot_start_y + self.card_height + 2))
                    # Show skill options based on suit (card value = skill bonus)
                    if card.suit == "H":
                        skill_info = "HP or CHA"
                    elif card.suit == "D":
                        skill_info = "ENG or ANA"
                    else:
                        skill_info = "Any skill"
                    skill_text = self.debug_font.render(f"+{value} {skill_info}", True, (200, 200, 200))
                    skill_y = slot_start_y + self.card_height + int(16 * self.scale)
                    self.screen.blit(skill_text, (slot_x, skill_y))
                    # Show who can afford (below skill text)
                    if can_afford:
                        afford_text = f"K:{self.king_dice[1]} R:{self.jack_dice[1]}"
                        afford_color = (150, 255, 150)
                    else:
                        afford_text = f"K:{self.king_dice[1]} R:{self.jack_dice[1]}"
                        afford_color = (255, 150, 150)
                    afford_surface = self.debug_font.render(afford_text, True, afford_color)
                    afford_y = skill_y + skill_text.get_height() + int(2 * self.scale)
                    self.screen.blit(afford_surface, (slot_x, afford_y))
        
        # Draw slot cards (witness slots to right of witness deck, 5% more to the right)
        if "witness" in self.deck_positions:
            wit_x, wit_y = self.deck_positions["witness"]
            card_gap = int(10 * self.scale)
            start_x = wit_x + self.card_width + card_gap + right_offset_5pct
            for i, card in enumerate(self.witness_slots):
                slot_x = start_x + (self.card_width + card_gap) * i
                if card:
                    self._draw_card(card, slot_x, wit_y, face_up=True)
                    # Draw card value and requirement
                    if self.debug_font:
                        value = self._get_card_value(card)
                        total_rep = self.king_dice[0] + self.jack_dice[0]
                        color = (100, 255, 100) if total_rep >= value else (255, 100, 100)
                        value_text = self.debug_font.render(f"Rep: {value}", True, color)
                        self.screen.blit(value_text, (slot_x, wit_y + self.card_height + 2))
        
        # Draw slot cards (location slots to right of location deck, 5% more to the right)
        if "location" in self.deck_positions:
            loc_x, loc_y = self.deck_positions["location"]
            card_gap = int(10 * self.scale)
            start_x = loc_x + self.card_width + card_gap + right_offset_5pct
            for i, card in enumerate(self.location_slots):
                slot_x = start_x + (self.card_width + card_gap) * i
                if card:
                    self._draw_card(card, slot_x, loc_y, face_up=True)
                    # Draw card value and requirement
                    if self.debug_font:
                        value = self._get_card_value(card)
                        total_ion = self.king_dice[2] + self.jack_dice[2]
                        color = (100, 255, 100) if total_ion >= value else (255, 100, 100)
                        value_text = self.debug_font.render(f"Ion: {value}", True, color)
                        self.screen.blit(value_text, (slot_x, loc_y + self.card_height + 2))
        
        # Draw encounter slot (single card slot to the right of encounter deck)
        if "encounter" in self.deck_positions:
            enc_x, enc_y = self.deck_positions["encounter"]
            encounter_slot_offset = int(30 * self.scale)  # More space from encounter deck
            slot_x = enc_x + self.card_width + encounter_slot_offset
            
            # Draw slot outline (empty or with card)
            slot_rect = pygame.Rect(slot_x, enc_y, self.card_width, self.card_height)
            if self.encounter_slot:
                # Draw the encounter card
                self._draw_card(self.encounter_slot, slot_x, enc_y, face_up=True)
                # Draw label showing it can be clicked to add to timeline
                if self.debug_font:
                    value = self._get_card_value(self.encounter_slot)
                    # Encounters always go to timeline (use any skill in trial)
                    label_text = self.debug_font.render(f"Val: {value} (Any)", True, (255, 200, 100))
                    self.screen.blit(label_text, (slot_x, enc_y + self.card_height + 2))
                    hint_text = self.debug_font.render("Click → Timeline", True, (150, 150, 150))
                    self.screen.blit(hint_text, (slot_x, enc_y + self.card_height + int(16 * self.scale)))
            else:
                # Draw empty slot outline with dashed effect
                pygame.draw.rect(self.screen, (60, 60, 80), slot_rect, 2)
                # Draw "ENCOUNTER" label
                if self.debug_font:
                    slot_label = self.debug_font.render("Encounter", True, (100, 100, 120))
                    label_x = slot_x + (self.card_width - slot_label.get_width()) // 2
                    label_y = enc_y + (self.card_height - slot_label.get_height()) // 2
                    self.screen.blit(slot_label, (label_x, label_y))
        
        # Draw all cards in z-order
        for card in self.card_z_order:
            if card not in self.card_positions:
                continue
            
            cx, cy = self.card_positions[card]
            face_up = self.card_face_up.get(card, True)
            
            # Draw hover glow effect BEFORE the card (so it appears behind)
            if card == self.hovered_card and card not in self.selected_cards:
                self._draw_card_hover_glow(card, cx, cy)
            
            # Draw the card
            self._draw_card(card, cx, cy, face_up=face_up)
            
            # Draw hover highlight (subtle cyan glow) - enhanced
            if card == self.hovered_card and card not in self.selected_cards:
                pygame.draw.rect(self.screen, (0, 255, 255), (cx - 2, cy - 2, self.card_width + 4, self.card_height + 4), 2)
            
            # Draw selection highlight (animated yellow/cyan border)
            if card in self.selected_cards:
                import math
                pulse = (math.sin(self.card_hover_glow_time * 6) + 1) / 2
                r = int(255 * (0.8 + 0.2 * pulse))
                g = int(255 * (0.9 + 0.1 * pulse))
                b = int(100 + 155 * pulse)
                pygame.draw.rect(self.screen, (r, g, b), (cx - 3, cy - 3, self.card_width + 6, self.card_height + 6), 3)
        
        # Display evidence remaining - CIVITAS COURT just above timeline (with cyberpunk glow!)
        if self.evidence_required > 0 and self.label_font:
            import math
            glow_pulse = (math.sin(self.neon_glow_time * 2) + 1) / 2
            
            # Evidence text with pulsing color
            evidence_color = (
                int(0 + 100 * glow_pulse),
                int(200 + 55 * glow_pulse),
                255
            )
            evidence_text = self.label_font.render(f"{self.evidence_required} Evidence Remains", True, evidence_color)
            
            # Court title with alternating color
            court_color = (255, int(200 + 55 * glow_pulse), int(255 * (1 - glow_pulse * 0.3)))
            court_text = self.label_font.render("CIVITAS COURT", True, court_color)
            
            padding = int(20 * self.scale)
            court_evidence_gap = int(4 * self.scale)  # Minimal gap between Evidence Remains and CIVITAS COURT
            if "encounter" in self.deck_positions:
                enc_x, enc_y = self.deck_positions["encounter"]
                right_offset = int(self.window_rect.width * 0.04) if self.window_rect else int(40 * self.scale)
                timeline_y = enc_y
                court_y = timeline_y - court_evidence_gap - court_text.get_height()
                evidence_text_y = court_y - court_evidence_gap - evidence_text.get_height()
            else:
                court_y = self.window_rect.bottom - padding - court_text.get_height() if self.window_rect else 0
                evidence_text_y = court_y - court_evidence_gap - evidence_text.get_height()
            evidence_text_x = self.window_rect.right - evidence_text.get_width() - padding if self.window_rect else 0
            court_x = self.window_rect.right - court_text.get_width() - padding if self.window_rect else 0
            
            # Draw glow behind text
            glow_alpha = int(80 * glow_pulse)
            evidence_glow = self.label_font.render(f"{self.evidence_required} Evidence Remains", True, (0, 150, 200))
            court_glow = self.label_font.render("CIVITAS COURT", True, (200, 150, 100))
            self.screen.blit(evidence_glow, (evidence_text_x + 1, evidence_text_y + 1))
            self.screen.blit(court_glow, (court_x + 1, court_y + 1))
            
            self.screen.blit(evidence_text, (evidence_text_x, evidence_text_y))
            self.screen.blit(court_text, (court_x, court_y))
        
        # Phase UI removed per request
        self.phase_confirm_btn = None
        
        # Draw dice next to character cards
        if self.king_spades and self.king_spades in self.card_positions:
            kx, ky = self.card_positions[self.king_spades]
            dice_size = int(30 * self.scale)
            dice_gap = int(8 * self.scale)
            dice_x = kx + self.card_width + dice_gap
            dice_y = ky
            
            blue_rect = pygame.Rect(dice_x, dice_y, dice_size, dice_size)
            self._draw_d6(self.king_dice[0], (0, 100, 255), blue_rect)
            green_rect = pygame.Rect(dice_x, dice_y + dice_size + int(4 * self.scale), dice_size, dice_size)
            self._draw_d6(self.king_dice[1], (0, 255, 100), green_rect)
            magenta_rect = pygame.Rect(dice_x, dice_y + (dice_size + int(4 * self.scale)) * 2, dice_size, dice_size)
            self._draw_d6(self.king_dice[2], (255, 0, 255), magenta_rect)
        
        if self.jack_spades and self.jack_spades in self.card_positions:
            jx, jy = self.card_positions[self.jack_spades]
            dice_size = int(30 * self.scale)
            dice_gap = int(8 * self.scale)
            dice_x = jx + self.card_width + dice_gap
            dice_y = jy
            
            blue_rect = pygame.Rect(dice_x, dice_y, dice_size, dice_size)
            self._draw_d6(self.jack_dice[0], (0, 100, 255), blue_rect)
            green_rect = pygame.Rect(dice_x, dice_y + dice_size + int(4 * self.scale), dice_size, dice_size)
            self._draw_d6(self.jack_dice[1], (0, 255, 100), green_rect)
            magenta_rect = pygame.Rect(dice_x, dice_y + (dice_size + int(4 * self.scale)) * 2, dice_size, dice_size)
            self._draw_d6(self.jack_dice[2], (255, 0, 255), magenta_rect)
        
        # Draw stats and attached upgrade areas under character cards
        if self.king_spades and self.king_spades in self.card_positions:
            kx, ky = self.card_positions[self.king_spades]
            
            # Calculate starting Y position (below the card, accounting for D10 if present)
            stats_start_y = ky + self.card_height + int(20 * self.scale)  # Space for D10
            
            # Draw stats for King
            if self.debug_font:
                stat_y = stats_start_y
                stat_line_height = int(18 * self.scale)
                
                for stat_name, stat_value in self.king_stats.items():
                    stat_text = f"{stat_name}: {stat_value}"
                    text_surface = self.debug_font.render(stat_text, True, (255, 255, 255))
                    self.screen.blit(text_surface, (kx, stat_y))
                    stat_y = self._advance_text_y(stat_y, text_surface, max(stat_line_height - text_surface.get_height(), 2))
                
                # Draw "Attached Upgrade" area (card-sized shaded rectangle)
                upgrade_area_y = stat_y + int(10 * self.scale)
                upgrade_area_rect = pygame.Rect(kx, upgrade_area_y, self.card_width, self.card_height)
                
                # Draw shaded background - highlight if hand cards available and character can afford it
                has_hand_cards = len(self.hand_cards) > 0
                can_afford = False
                if has_hand_cards:
                    card = self.hand_cards[0]
                    card_value = self._get_card_value(card)
                    can_afford = self.king_dice[1] >= card_value
                can_attach = has_hand_cards and can_afford
                bg_color = (60, 80, 60) if can_attach else (80, 60, 60) if has_hand_cards and not can_afford else (40, 40, 60)
                border_color = (100, 255, 100) if can_attach else (255, 100, 100) if has_hand_cards and not can_afford else (100, 100, 120)
                # Pulse attached upgrade slot when hand has cards (ATTACH UPGRADE)
                if has_hand_cards and self.draw_phase_stage == 7 and self.game_phase == "UPGRADE":
                    import math
                    t = pygame.time.get_ticks() / 1000.0
                    pulse = (math.sin(t * 4) + 1) / 2
                    infl = int(8 + 8 * pulse)
                    glow_rect = upgrade_area_rect.inflate(infl, infl)
                    glow_surf = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
                    alpha = int(50 + 90 * pulse)
                    glow_surf.fill((100, 255, 200, alpha))
                    self.screen.blit(glow_surf, glow_rect.topleft)
                pygame.draw.rect(self.screen, bg_color, upgrade_area_rect)
                pygame.draw.rect(self.screen, border_color, upgrade_area_rect, 3 if can_attach else 2)
                
                # Draw "Attached Upgrade" label (stacked vertically)
                if self.label_font and not self.king_attached_upgrades:
                    label_color = (100, 255, 100) if can_attach else (200, 200, 200)
                    attached_text = self.label_font.render("Attached", True, label_color)
                    upgrade_text = self.label_font.render("Upgrade", True, label_color)
                    # Center both lines horizontally
                    attached_x = kx + (self.card_width - attached_text.get_width()) // 2
                    upgrade_x = kx + (self.card_width - upgrade_text.get_width()) // 2
                    # Center both lines vertically in the area
                    total_text_height = attached_text.get_height() + upgrade_text.get_height() + int(4 * self.scale)
                    label_start_y = upgrade_area_y + (self.card_height - total_text_height) // 2
                    self.screen.blit(attached_text, (attached_x, label_start_y))
                    self.screen.blit(upgrade_text, (upgrade_x, label_start_y + attached_text.get_height() + int(4 * self.scale)))
                
                # Draw attached upgrade cards if any exist
                if self.king_attached_upgrades:
                    for i, card in enumerate(self.king_attached_upgrades):
                        offset = int(i * 3 * self.scale)
                        self._draw_card(
                            card,
                            kx + offset,
                            upgrade_area_y + offset,
                            self.card_face_up.get(card, True)
                        )
        
        if self.jack_spades and self.jack_spades in self.card_positions:
            jx, jy = self.card_positions[self.jack_spades]
            
            # Calculate starting Y position (below the card, accounting for D10 if present)
            stats_start_y = jy + self.card_height + int(20 * self.scale)  # Space for D10
            
            # Draw stats for Rookie
            if self.debug_font:
                stat_y = stats_start_y
                stat_line_height = int(18 * self.scale)
                
                for stat_name, stat_value in self.rookie_stats.items():
                    stat_text = f"{stat_name}: {stat_value}"
                    text_surface = self.debug_font.render(stat_text, True, (255, 255, 255))
                    self.screen.blit(text_surface, (jx, stat_y))
                    stat_y = self._advance_text_y(stat_y, text_surface, max(stat_line_height - text_surface.get_height(), 2))
                
                # Draw "Attached Upgrade" area (card-sized shaded rectangle)
                upgrade_area_y = stat_y + int(10 * self.scale)
                upgrade_area_rect = pygame.Rect(jx, upgrade_area_y, self.card_width, self.card_height)
                
                # Draw shaded background - highlight if hand cards available and character can afford it
                has_hand_cards = len(self.hand_cards) > 0
                can_afford = False
                if has_hand_cards:
                    card = self.hand_cards[0]
                    card_value = self._get_card_value(card)
                    can_afford = self.jack_dice[1] >= card_value
                can_attach = has_hand_cards and can_afford
                bg_color = (60, 80, 60) if can_attach else (80, 60, 60) if has_hand_cards and not can_afford else (40, 40, 60)
                border_color = (100, 255, 100) if can_attach else (255, 100, 100) if has_hand_cards and not can_afford else (100, 100, 120)
                # Pulse attached upgrade slot when hand has cards (ATTACH UPGRADE)
                if has_hand_cards and self.draw_phase_stage == 7 and self.game_phase == "UPGRADE":
                    import math
                    t = pygame.time.get_ticks() / 1000.0
                    pulse = (math.sin(t * 4) + 1) / 2
                    infl = int(8 + 8 * pulse)
                    glow_rect = upgrade_area_rect.inflate(infl, infl)
                    glow_surf = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
                    alpha = int(50 + 90 * pulse)
                    glow_surf.fill((100, 255, 200, alpha))
                    self.screen.blit(glow_surf, glow_rect.topleft)
                pygame.draw.rect(self.screen, bg_color, upgrade_area_rect)
                pygame.draw.rect(self.screen, border_color, upgrade_area_rect, 3 if can_attach else 2)
                
                # Draw "Attached Upgrade" label (stacked vertically)
                if self.label_font and not self.rookie_attached_upgrades:
                    label_color = (100, 255, 100) if can_attach else (200, 200, 200)
                    attached_text = self.label_font.render("Attached", True, label_color)
                    upgrade_text = self.label_font.render("Upgrade", True, label_color)
                    # Center both lines horizontally
                    attached_x = jx + (self.card_width - attached_text.get_width()) // 2
                    upgrade_x = jx + (self.card_width - upgrade_text.get_width()) // 2
                    # Center both lines vertically in the area
                    total_text_height = attached_text.get_height() + upgrade_text.get_height() + int(4 * self.scale)
                    label_start_y = upgrade_area_y + (self.card_height - total_text_height) // 2
                    self.screen.blit(attached_text, (attached_x, label_start_y))
                    self.screen.blit(upgrade_text, (upgrade_x, label_start_y + attached_text.get_height() + int(4 * self.scale)))
                
                # Draw attached upgrade cards if any exist
                if self.rookie_attached_upgrades:
                    for i, card in enumerate(self.rookie_attached_upgrades):
                        offset = int(i * 3 * self.scale)
                        self._draw_card(
                            card,
                            jx + offset,
                            upgrade_area_y + offset,
                            self.card_face_up.get(card, True)
                        )
        
        if self.setup_complete and self.draw_phase_stage == 7:
            self._check_end_conditions()

        # Draw selection box
        if self.drawing_selection_box and self.selection_box_start and self.selection_box_end:
            sx, sy = self.selection_box_start
            ex, ey = self.selection_box_end
            box_rect = pygame.Rect(
                min(sx, ex),
                min(sy, ey),
                abs(ex - sx),
                abs(ey - sy)
            )
            # Draw semi-transparent fill
            box_surface = pygame.Surface((box_rect.width, box_rect.height), pygame.SRCALPHA)
            box_surface.fill((0, 255, 255, 50))
            self.screen.blit(box_surface, box_rect.topleft)
            # Draw border
            pygame.draw.rect(self.screen, (255, 255, 0), box_rect, 2)

        # Draw help text and selection info in corners
        if self.debug_font:
            title_bar_offset = self.title_bar_rect.height if self.title_bar_rect else 0
            
            # Selection info in top-right
            if self.selected_cards:
                sel_text = f"Selected: {len(self.selected_cards)} card(s)"
            else:
                sel_text = "No selection"
            text_surface = self.debug_font.render(sel_text, True, (255, 255, 255))
            text_x = self.window_rect.right - text_surface.get_width() - int(10 * self.scale)
            text_down_offset = int(self.window_rect.height * 0.05) if self.window_rect else 0
            text_y = self.window_rect.y + title_bar_offset + int(20 * self.scale) + text_down_offset
            
            # Draw background for text readability
            bg_rect = pygame.Rect(
                text_x - int(4 * self.scale),
                text_y - int(2 * self.scale),
                text_surface.get_width() + int(8 * self.scale),
                text_surface.get_height() + int(4 * self.scale)
            )
            bg_surface = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
            bg_surface.fill((0, 0, 0, 180))
            self.screen.blit(bg_surface, bg_rect.topleft)
            pygame.draw.rect(self.screen, (0, 255, 255), bg_rect, 1)
            self.screen.blit(text_surface, (text_x, text_y))

        # Draw setup modals on top of everything
        if self.show_setup_modal and not self.setup_complete:
            if self.setup_modal_stage == 0:
                self._draw_welcome_modal()
            elif self.setup_modal_stage == 1:
                self._draw_reputation_modal()
            elif self.setup_modal_stage == 2:
                self._draw_ether_modal()
            elif self.setup_modal_stage == 3:
                self._draw_ion_modal()
            elif self.setup_modal_stage == 4:
                self._draw_encounter_modal()
        
        # Draw hand cards (upgrades waiting to be attached)
        if self.hand_cards:
            # Draw hand area in bottom-left corner, moved down to avoid overlap with attached upgrade slot
            hand_x = self.window_rect.x + int(10 * self.scale)
            hand_y = self.window_rect.bottom - int(140 * self.scale)
            
            if self.label_font:
                hand_label = self.label_font.render("HAND:", True, (100, 255, 200))
                self.screen.blit(hand_label, (hand_x, hand_y - int(25 * self.scale)))
            
            card_gap = int(8 * self.scale)
            mini_card_width = int(self.card_width * 0.6)
            mini_card_height = int(self.card_height * 0.6)
            
            for i, card in enumerate(self.hand_cards):
                card_x = hand_x + i * (mini_card_width + card_gap)
                # Draw mini card
                
                if self.debug_font:
                    # Show card name
                    card_text = f"{card.rank}{card.suit}"
                    text_surf = self.debug_font.render(card_text, True, (255, 255, 255))
                    self.screen.blit(text_surf, (card_x + 4, hand_y + 4))
                    
                    # Show skill enhancement with card value
                    skill = self.hand_card_skills.get(card)
                    if skill:
                        card_value = self._get_card_value(card)
                        skill_surf = self.debug_font.render(f"+{card_value} {skill}", True, (100, 255, 100))
                        self.screen.blit(skill_surf, (card_x + 4, hand_y + mini_card_height - int(20 * self.scale)))
        
        # Draw rules modals
        if self.setup_complete and self.draw_phase_stage == 4:
            self._draw_rules_modal()
        if self.setup_complete and self.draw_phase_stage == 5:
            self._draw_encounter_rules_modal()
        if self.setup_complete and self.draw_phase_stage == 6:
            self._draw_end_rules_modal()
        
        # Draw trial modal
        if self.show_trial_modal:
            self._draw_trial_modal()
        if self.show_trial_result_modal:
            self._draw_trial_result_modal()
        
        # Draw upgrade purchase modal
        if self.show_upgrade_modal:
            self._draw_upgrade_modal()

        # Draw crime congratulations modal
        if self.show_crime_congrats_modal:
            self._draw_crime_congrats_modal()
        
        # Draw tutorial modal
        if self.show_tutorial_modal:
            self._draw_tutorial_modal()

        # Draw and update fireworks (update integrated into draw for animation)
        if self.show_fireworks:
            # Update fireworks animation (use approx 16ms for 60fps if update() not called externally)
            self._update_fireworks(0.016)
            # Update flashing text
            self.end_game_flash_timer += 0.016
            if self.end_game_flash_timer >= 0.3:
                self.end_game_flash_timer = 0.0
                self.end_game_flash_visible = not self.end_game_flash_visible
            self._draw_fireworks()

        if self.show_game_over_modal:
            self._draw_game_over_modal()
        
        # === CYBERPUNK OVERLAY EFFECTS (drawn on top of everything) ===
        self._draw_crt_vignette()  # Darker corners
        self._draw_glitch_effect()  # Glitch effect (when active)

        self.screen.set_clip(old_clip)


# -----------------------------------------------------------------------------
# Standalone test runner (if you want to run this file directly)
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    try:
        pygame.init()
    except Exception as e:
        print(f"Pygame initialization failed. Run this file in an environment with Pygame installed: {e}")
        sys.exit(1)

    # Setup a standalone window
    SCREEN_WIDTH = 1200
    SCREEN_HEIGHT = 800
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Civitas Nihilium - Mouse Coordinates Test")

    # Desktop coordinates and size for the game
    desktop_x = 0
    desktop_y = 0
    desktop_size = (SCREEN_WIDTH, SCREEN_HEIGHT)
    health_monitor_y = 10
    scale = 1.0

    # Create game instance
    game = CivitasNihiliumGame(
        screen,
        scale,
        desktop_x,
        desktop_y,
        desktop_size,
        health_monitor_y,
        bbs_x=0,
        bbs_width=0,
        get_radio_music_callback=None,
    )

    # Start the game
    game.start()

    clock = pygame.time.Clock()
    running = True

    print("\n--- CIVITAS NIHILIUM MOUSE COORDINATES TEST ---")
    print("Move your mouse to see coordinates displayed as percentages")
    print("ESC: Exit")
    print("----------------------------------------\n")

    while running:
        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
                break
            else:
                game.handle_event(event)

        # Exit when game is closed (in-game Close button or ESC)
        if not game.active:
            running = False

        # Draw
        screen.fill((0, 0, 0))
        game.draw()
        pygame.display.flip()

        clock.tick(60)

    # Cleanup
    game.close()
    pygame.quit()
    print("Game closed.")
