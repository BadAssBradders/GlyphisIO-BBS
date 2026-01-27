"""
Mahjong Game Module
Riichi Mahjong duel for the OS Mode desktop environment (PyRiichi-backed).

- Uses tile assets from Data/OS/Mahjong/mahjong_tiles
- Optional audio from Data/OS/Mahjong/Audio (if present)
- Supports three opponent levels: Easy, Medium, Hard
"""

import pygame
import os
import sys
import random
import time
from typing import Dict, List, Tuple, Optional

try:
    from pyriichi import RuleEngine, GameAction
    from pyriichi.tiles import Tile as RiichiTile, Suit
    PYRIICHI_AVAILABLE = True
except Exception as e:
    PYRIICHI_AVAILABLE = False
    RuleEngine = None
    GameAction = None
    RiichiTile = None
    Suit = None
    PYRIICHI_IMPORT_ERROR = str(e)

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
COLOR_BUTTON_HOVER = (60, 60, 80)


# Data path helper - mirrors chess/solitaire layout
def get_data_path(*path_parts) -> str:
    """
    Returns the path to the Data folder, handling both development and built executable scenarios.
    Assumes this file lives in Data/OS/Mahjong.
    """
    if getattr(sys, "frozen", False):
        base_path = sys._MEIPASS  # type: ignore[attr-defined]
    else:
        script_dir = os.path.dirname(os.path.abspath(__file__))  # .../Data/OS/Mahjong
        os_dir = os.path.dirname(script_dir)  # .../Data/OS
        data_folder = os.path.dirname(os_dir)  # .../Data
        base_path = data_folder
    return os.path.join(base_path, *path_parts)


class MahjongGame:
    """
    Riichi Mahjong game for OS Mode.

    API mirrors SolitaireGame:
    - update_desktop(...)
    - start()
    - close()
    - handle_event(event) -> bool
    - update(dt)
    - draw()
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
    ):
        self.screen = screen
        self.scale = scale
        self.desktop_x = desktop_x
        self.desktop_y = desktop_y
        self.desktop_size = desktop_size
        self.bbs_x = bbs_x
        self.bbs_width = bbs_width
        self.get_radio_music = get_radio_music_callback or (lambda: False)

        # Game state
        self.active: bool = False
        self.game_over: bool = False
        self.win_state: Optional[str] = None  # "player", "ai", "draw"
        self.engine_error: Optional[str] = None

        # Turn state
        self.players = [0, 1]
        self.human_player = 0
        self.ai_player = 1
        self.current_player = 0
        self.turn_phase = "draw"  # "draw" or "discard"
        self.awaiting_discard = False

        # Scores and turns
        self.player_score = 0
        self.ai_score = 0
        self.moves = 0
        self.start_time = 0.0
        self.elapsed_time = 0.0
        self.wall_remaining = 0
        self.last_result = None

        # AI
        self.ai_level = "Easy"
        self.ai_skill = 0.35
        self.ai_next_action_time = 0.0
        self.ai_delay = 0.6

        # Layout rects
        self.window_rect: Optional[pygame.Rect] = None
        self.title_bar_rect: Optional[pygame.Rect] = None
        self.stats_panel_rect: Optional[pygame.Rect] = None
        self.play_area_rect: Optional[pygame.Rect] = None
        self.exit_button_rect: Optional[pygame.Rect] = None
        self.new_game_rect: Optional[pygame.Rect] = None
        self.level_button_rects: Dict[str, pygame.Rect] = {}
        self.draw_button_rect: Optional[pygame.Rect] = None

        # Hover states
        self.hovered_button: Optional[str] = None
        self.hovered_tile_index: Optional[int] = None

        # Assets
        self.tile_surfaces: Dict[str, pygame.Surface] = {}
        self.tile_image_by_spec: Dict[Tuple[str, int], pygame.Surface] = {}
        self.tile_width = 0
        self.tile_height = 0

        # Engine
        self.engine = None
        self.discards: Dict[int, List[object]] = {0: [], 1: []}

        # Audio
        self.sound_draw: Optional[pygame.mixer.Sound] = None
        self.sound_discard: Optional[pygame.mixer.Sound] = None
        self.sound_win: Optional[pygame.mixer.Sound] = None

        self._update_layout()
        self._load_assets()
        self._load_audio()

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
        self.desktop_x = desktop_x
        self.desktop_y = desktop_y
        self.desktop_size = desktop_size
        self._update_layout()

    def _update_layout(self) -> None:
        title_bar_height = int(35 * self.scale)
        stats_panel_width = int(260 * self.scale)

        window_width = self.desktop_size[0]
        window_height = self.desktop_size[1]
        window_x = self.desktop_x
        window_y = self.desktop_y

        self.window_rect = pygame.Rect(window_x, window_y, window_width, window_height)
        self.title_bar_rect = pygame.Rect(window_x, window_y, window_width, title_bar_height)

        exit_button_width = int(60 * self.scale)
        exit_button_height = int(25 * self.scale)
        exit_button_x = window_x + window_width - exit_button_width - int(15 * self.scale)
        exit_button_y = window_y + (title_bar_height - exit_button_height) // 2
        self.exit_button_rect = pygame.Rect(
            exit_button_x,
            exit_button_y,
            exit_button_width,
            exit_button_height,
        )

        content_y = window_y + title_bar_height
        content_height = window_height - title_bar_height

        self.stats_panel_rect = pygame.Rect(
            window_x + window_width - stats_panel_width,
            content_y,
            stats_panel_width,
            content_height,
        )

        play_area_margin = int(15 * self.scale)
        play_area_x = window_x + play_area_margin
        play_area_width = window_width - stats_panel_width - (play_area_margin * 2)
        play_area_height = content_height - int(20 * self.scale)
        self.play_area_rect = pygame.Rect(
            play_area_x,
            content_y + int(10 * self.scale),
            play_area_width,
            play_area_height,
        )

        # Tile sizing based on hand width (max 14 tiles)
        usable_w = self.play_area_rect.width - int(40 * self.scale)
        self.tile_width = max(18, int(usable_w / 14))
        self.tile_height = max(26, int(self.tile_width * 1.35))

        # Buttons on stats panel
        if self.stats_panel_rect:
            button_w = int(160 * self.scale)
            button_h = int(28 * self.scale)
            btn_x = self.stats_panel_rect.x + (self.stats_panel_rect.width - button_w) // 2
            btn_y = self.stats_panel_rect.y + int(210 * self.scale)
            self.new_game_rect = pygame.Rect(btn_x, btn_y, button_w, button_h)

            level_btn_y = btn_y + int(46 * self.scale)
            level_btn_w = int(70 * self.scale)
            level_btn_h = int(26 * self.scale)
            gap = int(8 * self.scale)
            start_x = self.stats_panel_rect.x + (self.stats_panel_rect.width - (level_btn_w * 3 + gap * 2)) // 2
            self.level_button_rects = {
                "Easy": pygame.Rect(start_x, level_btn_y, level_btn_w, level_btn_h),
                "Medium": pygame.Rect(start_x + level_btn_w + gap, level_btn_y, level_btn_w, level_btn_h),
                "Hard": pygame.Rect(start_x + (level_btn_w + gap) * 2, level_btn_y, level_btn_w, level_btn_h),
            }

            draw_btn_y = level_btn_y + int(42 * self.scale)
            self.draw_button_rect = pygame.Rect(btn_x, draw_btn_y, button_w, button_h)

    # -------------------------------------------------------------------------
    # Assets
    # -------------------------------------------------------------------------
    def _load_assets(self) -> None:
        """Load and scale tile assets."""
        self.tile_surfaces.clear()
        self.tile_image_by_spec.clear()
        tiles_dir = get_data_path("OS", "Mahjong", "mahjong_tiles")
        if os.path.isdir(tiles_dir):
            for filename in sorted(os.listdir(tiles_dir)):
                if not filename.lower().endswith(".png"):
                    continue
                tile_id = os.path.splitext(filename)[0]
                path = os.path.join(tiles_dir, filename)
                try:
                    img = pygame.image.load(path).convert_alpha()
                    img = pygame.transform.smoothscale(img, (self.tile_width, self.tile_height))
                    self.tile_surfaces[tile_id] = img
                    spec = self._tile_id_to_spec(tile_id)
                    if spec:
                        self.tile_image_by_spec[spec] = img
                except Exception as e:
                    print(f"Warning: failed to load {filename}: {e}")

    def _load_audio(self) -> None:
        """Load optional audio from Data/OS/Mahjong/Audio. Uses exact filenames: draw, mahjong_tile_1, ron, chow, pung, kong, riichi, roll_two_dice_1."""
        self.sound_draw = None
        self.sound_discard = None
        self.sound_win = None
        self.sound_chow = None
        self.sound_pung = None
        self.sound_kong = None
        self.sound_riichi = None
        self.sound_roll_dice = None
        self.sound_tile_variants: List[pygame.mixer.Sound] = []  # mahjong_tile_1..4 for discard variety
        audio_dir = get_data_path("OS", "Mahjong", "Audio")
        if not os.path.isdir(audio_dir):
            return
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
        except Exception:
            return

        # Map game events to filenames in Data/OS/Mahjong/Audio
        self.sound_draw = self._safe_load_audio("draw.mp3", audio_dir)
        self.sound_win = self._safe_load_audio("ron.mp3", audio_dir)
        for i in range(1, 5):
            s = self._safe_load_audio(f"mahjong_tile_{i}.mp3", audio_dir)
            if s:
                self.sound_tile_variants.append(s)
        self.sound_discard = self.sound_tile_variants[0] if self.sound_tile_variants else None
        self.sound_chow = self._safe_load_audio("chow.mp3", audio_dir)
        self.sound_pung = self._safe_load_audio("pung.mp3", audio_dir)
        self.sound_kong = self._safe_load_audio("kong.mp3", audio_dir)
        self.sound_riichi = self._safe_load_audio("riichi.mp3", audio_dir)
        self.sound_roll_dice = self._safe_load_audio("roll_two_dice_1.mp3", audio_dir)

        for sound in (self.sound_draw, self.sound_discard, self.sound_win, self.sound_chow,
                      self.sound_pung, self.sound_kong, self.sound_riichi, self.sound_roll_dice) + tuple(self.sound_tile_variants):
            if sound:
                sound.set_volume(0.4)

    def _safe_load_audio(self, filename: str, audio_dir: str) -> Optional[pygame.mixer.Sound]:
        try:
            return pygame.mixer.Sound(os.path.join(audio_dir, filename))
        except Exception:
            return None

    # -------------------------------------------------------------------------
    # Tile mapping helpers
    # -------------------------------------------------------------------------
    def _tile_id_to_spec(self, tile_id: str) -> Optional[Tuple[str, int]]:
        if tile_id.startswith("Bamboo"):
            return ("souzu", int(tile_id.replace("Bamboo", "")))
        if tile_id.startswith("Characters"):
            return ("manzu", int(tile_id.replace("Characters", "")))
        if tile_id.startswith("Circles"):
            return ("pinzu", int(tile_id.replace("Circles", "")))
        honors = {
            "East": 1,
            "South": 2,
            "West": 3,
            "North": 4,
            "White": 5,
            "Green": 6,
            "Red": 7,
        }
        if tile_id in honors:
            return ("honor", honors[tile_id])
        return None

    def _spec_to_tile_id(self, spec: Tuple[str, int]) -> str:
        suit, value = spec
        if suit == "souzu":
            return f"Bamboo{value}"
        if suit == "manzu":
            return f"Characters{value}"
        if suit == "pinzu":
            return f"Circles{value}"
        honors = {1: "East", 2: "South", 3: "West", 4: "North", 5: "White", 6: "Green", 7: "Red"}
        return honors.get(value, "East")

    def _resolve_suits(self) -> Dict[str, object]:
        if Suit is None:
            return {}
        suit_map = {}
        for s in Suit:
            name = getattr(s, "name", "").lower()
            if "man" in name or "char" in name:
                suit_map["manzu"] = s
            elif "pin" in name or "cir" in name:
                suit_map["pinzu"] = s
            elif "sou" in name or "bam" in name:
                suit_map["souzu"] = s
            elif "honor" in name or "jihai" in name or "wind" in name or "zi" in name:
                suit_map["honor"] = s
        return suit_map

    def _create_engine_tile(self, spec: Tuple[str, int]) -> Optional[object]:
        if not PYRIICHI_AVAILABLE or RiichiTile is None or Suit is None:
            return None
        suit_key, value = spec
        suit_map = self._resolve_suits()
        suit = suit_map.get(suit_key)
        if not suit:
            return None
        try:
            return RiichiTile(suit, value)
        except Exception:
            return None

    def _tile_to_spec(self, tile: object) -> Optional[Tuple[str, int]]:
        if tile is None:
            return None
        suit = getattr(tile, "suit", None)
        value = getattr(tile, "value", None)
        if value is None:
            value = getattr(tile, "rank", None)
        if value is None:
            value = getattr(tile, "number", None)
        if suit is None or value is None:
            return None
        if isinstance(suit, str):
            suit_name = suit.lower()
        else:
            suit_name = getattr(suit, "name", "").lower()
        if "man" in suit_name or "char" in suit_name:
            return ("manzu", int(value))
        if "pin" in suit_name or "cir" in suit_name:
            return ("pinzu", int(value))
        if "sou" in suit_name or "bam" in suit_name:
            return ("souzu", int(value))
        if "honor" in suit_name or "jihai" in suit_name or "wind" in suit_name or "zi" in suit_name:
            return ("honor", int(value))
        return None

    def _tile_to_key(self, tile: object) -> str:
        spec = self._tile_to_spec(tile)
        if not spec:
            return "unknown"
        return f"{spec[0]}-{spec[1]}"

    # -------------------------------------------------------------------------
    # Engine helpers
    # -------------------------------------------------------------------------
    def _get_game_action(self, *names: str):
        if GameAction is None:
            return None
        for name in names:
            action = getattr(GameAction, name, None)
            if action is not None:
                return action
        return None

    def _get_hand_tiles(self, player: int) -> List[object]:
        if not self.engine:
            return []
        try:
            hand = self.engine.get_hand(player)
            if isinstance(hand, list):
                return hand
            tiles = getattr(hand, "tiles", None)
            return tiles if tiles is not None else []
        except Exception:
            return []

    def _get_wall_remaining(self) -> int:
        if not self.engine:
            return 0
        for attr in ("get_wall_remaining", "wall_remaining", "get_wall_count"):
            method = getattr(self.engine, attr, None)
            if callable(method):
                try:
                    return int(method())
                except Exception:
                    continue
            if isinstance(method, int):
                return int(method)
        return 0

    # -------------------------------------------------------------------------
    # Game start / reset / close
    # -------------------------------------------------------------------------
    def start(self) -> None:
        self._load_assets()
        self._new_game(reset_scores=True)
        self.active = True
        self.game_over = False
        self.win_state = None
        self.start_time = time.time()
        self.moves = 0

    def _new_game(self, reset_scores: bool = True) -> None:
        if reset_scores:
            self.player_score = 0
            self.ai_score = 0
        self.discards = {0: [], 1: []}
        self.current_player = self.human_player
        self.turn_phase = "draw"
        self.awaiting_discard = False
        self.game_over = False
        self.win_state = None
        self.last_result = None

        if not PYRIICHI_AVAILABLE:
            self.engine_error = f"PyRiichi not available: {PYRIICHI_IMPORT_ERROR}"
            self.engine = None
            return

        try:
            self.engine_error = None
            self.engine = RuleEngine(num_players=len(self.players))
            if hasattr(self.engine, "start_game"):
                self.engine.start_game()
            if hasattr(self.engine, "start_round"):
                self.engine.start_round()
            if hasattr(self.engine, "deal"):
                self.engine.deal()
            if hasattr(self.engine, "get_current_player"):
                self.current_player = self.engine.get_current_player()
            self.wall_remaining = self._get_wall_remaining()
        except Exception as e:
            self.engine_error = f"Engine init failed: {e}"
            self.engine = None

    def close(self) -> None:
        self.active = False

    # -------------------------------------------------------------------------
    # Event handling
    # -------------------------------------------------------------------------
    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.active:
            return False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.close()
                return True

        if event.type == pygame.MOUSEMOTION:
            mx, my = event.pos
            self.hovered_button = None
            self.hovered_tile_index = None
            if self.exit_button_rect and self.exit_button_rect.collidepoint(mx, my):
                self.hovered_button = "exit"
            elif self.new_game_rect and self.new_game_rect.collidepoint(mx, my):
                self.hovered_button = "new_game"
            elif self.draw_button_rect and self.draw_button_rect.collidepoint(mx, my):
                self.hovered_button = "draw"
            else:
                for level, rect in self.level_button_rects.items():
                    if rect.collidepoint(mx, my):
                        self.hovered_button = f"level_{level}"
                        break
            if self.play_area_rect and self.play_area_rect.collidepoint(mx, my):
                if self.current_player == self.human_player and self.awaiting_discard:
                    hand = self._get_hand_tiles(self.human_player)
                    for idx, rect in self._player_hand_rects(hand):
                        if rect.collidepoint(mx, my):
                            self.hovered_tile_index = idx
                            break
            return False

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos

            if self.exit_button_rect and self.exit_button_rect.collidepoint(mx, my):
                self.close()
                return True

            if self.new_game_rect and self.new_game_rect.collidepoint(mx, my):
                self._new_game(reset_scores=True)
                return True

            for level, rect in self.level_button_rects.items():
                if rect.collidepoint(mx, my):
                    if level != self.ai_level:
                        self._set_ai_level(level)
                        self._new_game(reset_scores=True)
                    return True

            if self.draw_button_rect and self.draw_button_rect.collidepoint(mx, my):
                if self.current_player == self.human_player and self.turn_phase == "draw":
                    self._start_turn(self.human_player)
                return True

            if self.current_player != self.human_player or not self.awaiting_discard:
                return False

            hand = self._get_hand_tiles(self.human_player)
            for idx, rect in self._player_hand_rects(hand):
                if rect.collidepoint(mx, my):
                    self._player_discard(hand[idx])
                    return True

        return False

    # -------------------------------------------------------------------------
    # Game flow
    # -------------------------------------------------------------------------
    def _set_ai_level(self, level: str) -> None:
        self.ai_level = level
        if level == "Easy":
            self.ai_skill = 0.35
        elif level == "Medium":
            self.ai_skill = 0.65
        else:
            self.ai_skill = 0.9
        self.ai_delay = 0.8 if level == "Easy" else 0.6 if level == "Medium" else 0.4

    def _start_turn(self, player: int) -> None:
        if not self.engine:
            return
        draw_action = self._get_game_action("DRAW", "DRAW_TILE")
        if draw_action and hasattr(self.engine, "execute_action"):
            try:
                result = self.engine.execute_action(player, draw_action)
                self.last_result = result
            except Exception as e:
                self.engine_error = f"Draw failed: {e}"
                return
        self.wall_remaining = self._get_wall_remaining()
        self.turn_phase = "discard"
        self.awaiting_discard = True
        if self.sound_draw:
            try:
                self.sound_draw.play()
            except Exception:
                pass
        self._check_draw_win(player)

    def _check_draw_win(self, player: int) -> None:
        if not self.engine:
            return
        check_win = getattr(self.engine, "check_win", None)
        drawn_tile = getattr(self.last_result, "drawn_tile", None)
        if callable(check_win) and drawn_tile is not None:
            try:
                win_result = check_win(player, drawn_tile)
            except Exception:
                return
            if win_result:
                self._set_win(player, win_result)

    def _player_discard(self, tile: object) -> None:
        if not self.engine:
            return
        discard_action = self._get_game_action("DISCARD", "DROP")
        if discard_action and hasattr(self.engine, "execute_action"):
            try:
                self.engine.execute_action(self.human_player, discard_action, tile=tile)
            except Exception as e:
                self.engine_error = f"Discard failed: {e}"
                return
        self.discards[self.human_player].append(tile)
        self.moves += 1
        self.turn_phase = "draw"
        self.awaiting_discard = False
        if self.sound_discard:
            try:
                self.sound_discard.play()
            except Exception:
                pass
        self._advance_turn()

    def _advance_turn(self) -> None:
        next_index = (self.players.index(self.current_player) + 1) % len(self.players)
        self.current_player = self.players[next_index]
        self.turn_phase = "draw"
        self.awaiting_discard = False
        if self.engine and hasattr(self.engine, "get_current_player"):
            try:
                self.current_player = self.engine.get_current_player()
            except Exception:
                pass

    def _set_win(self, player: int, win_result: object = None) -> None:
        self.game_over = True
        if player == self.human_player:
            self.win_state = "player"
            self.player_score += 1
        else:
            self.win_state = "ai"
            self.ai_score += 1
        if self.sound_win:
            try:
                self.sound_win.play()
            except Exception:
                pass
        self.last_result = win_result

    def _ai_choose_discard(self, hand_tiles: List[object]) -> Optional[object]:
        if not hand_tiles:
            return None
        if self.ai_level == "Easy":
            return random.choice(hand_tiles)

        counts: Dict[str, int] = {}
        for tile in hand_tiles:
            key = self._tile_to_key(tile)
            counts[key] = counts.get(key, 0) + 1

        def score(tile: object) -> float:
            spec = self._tile_to_spec(tile)
            key = self._tile_to_key(tile)
            value = spec[1] if spec else 0
            suit = spec[0] if spec else "honor"
            s = 0.0
            if counts.get(key, 0) == 1:
                s += 1.5
            if suit == "honor":
                s += 2.2
            if value in (1, 9):
                s += 0.8
            if counts.get(key, 0) >= 2:
                s -= 1.0
            if suit in ("manzu", "pinzu", "souzu"):
                values = [self._tile_to_spec(t)[1] for t in hand_tiles if self._tile_to_spec(t) and self._tile_to_spec(t)[0] == suit]
                if value - 1 in values or value + 1 in values:
                    s -= 0.6
                if value - 2 in values or value + 2 in values:
                    s -= 0.3
            return s

        scored = sorted(hand_tiles, key=score, reverse=True)
        if self.ai_level == "Medium":
            return scored[0] if random.random() < self.ai_skill else random.choice(hand_tiles)
        return scored[0]

    def _ai_turn(self) -> None:
        if self.current_player != self.ai_player or self.game_over:
            return
        now = time.time()
        if now < self.ai_next_action_time:
            return
        if self.turn_phase == "draw":
            self._start_turn(self.ai_player)
            self.ai_next_action_time = now + self.ai_delay
            return
        if self.turn_phase == "discard":
            hand = self._get_hand_tiles(self.ai_player)
            tile = self._ai_choose_discard(hand)
            if tile:
                discard_action = self._get_game_action("DISCARD", "DROP")
                if discard_action and hasattr(self.engine, "execute_action"):
                    try:
                        self.engine.execute_action(self.ai_player, discard_action, tile=tile)
                    except Exception as e:
                        self.engine_error = f"AI discard failed: {e}"
                        return
                self.discards[self.ai_player].append(tile)
                if self.sound_discard:
                    try:
                        self.sound_discard.play()
                    except Exception:
                        pass
            self.turn_phase = "draw"
            self.awaiting_discard = False
            self._advance_turn()
            self.ai_next_action_time = now + self.ai_delay

    def update(self, dt: float) -> None:
        if not self.active:
            return
        if not self.game_over and self.start_time:
            self.elapsed_time = time.time() - self.start_time
        if self.engine:
            self.wall_remaining = self._get_wall_remaining()
        if self.current_player == self.human_player:
            if self.turn_phase == "draw" and not self.awaiting_discard and not self.game_over:
                # Wait for player to click draw
                pass
        else:
            self._ai_turn()

    # -------------------------------------------------------------------------
    # Drawing
    # -------------------------------------------------------------------------
    def draw(self) -> None:
        if not self.active:
            return

        try:
            title_font = pygame.font.SysFont("verdana", max(int(26 * self.scale), 16))
            body_font = pygame.font.SysFont("verdana", max(int(18 * self.scale), 12))
            small_font = pygame.font.SysFont("verdana", max(int(16 * self.scale), 10))
        except Exception:
            try:
                title_font = pygame.font.Font(None, max(int(26 * self.scale), 16))
                body_font = pygame.font.Font(None, max(int(18 * self.scale), 12))
                small_font = pygame.font.Font(None, max(int(16 * self.scale), 10))
            except Exception:
                return

        old_clip = self.screen.get_clip()
        self.screen.set_clip(self.window_rect)

        pygame.draw.rect(self.screen, COLOR_BG_DARK, self.window_rect)
        pygame.draw.rect(self.screen, COLOR_CYAN, self.window_rect, 2)

        pygame.draw.rect(self.screen, COLOR_BG_TITLE, self.title_bar_rect)
        pygame.draw.line(
            self.screen,
            COLOR_CYAN,
            (self.title_bar_rect.x, self.title_bar_rect.bottom - 1),
            (self.title_bar_rect.right, self.title_bar_rect.bottom - 1),
            2,
        )
        title_text = title_font.render("MAHJONG", True, COLOR_WHITE)
        title_x = self.title_bar_rect.x + int(15 * self.scale)
        title_y = self.title_bar_rect.y + (self.title_bar_rect.height - title_text.get_height()) // 2
        self.screen.blit(title_text, (title_x, title_y))

        if self.exit_button_rect:
            button_color = COLOR_BUTTON_HOVER if self.hovered_button == "exit" else COLOR_BG_TITLE
            pygame.draw.rect(self.screen, button_color, self.exit_button_rect)
            pygame.draw.rect(self.screen, COLOR_CYAN, self.exit_button_rect, 2)
            exit_text = small_font.render("EXIT", True, COLOR_WHITE)
            exit_text_x = self.exit_button_rect.x + (self.exit_button_rect.width - exit_text.get_width()) // 2
            exit_text_y = self.exit_button_rect.y + (self.exit_button_rect.height - exit_text.get_height()) // 2
            self.screen.blit(exit_text, (exit_text_x, exit_text_y))

        pygame.draw.rect(self.screen, (15, 15, 35), self.play_area_rect)
        pygame.draw.rect(self.screen, COLOR_DARK_CYAN, self.play_area_rect, 1)

        self._draw_play_area(small_font)
        self._draw_stats_panel(body_font, small_font)

        self.screen.set_clip(old_clip)

    def _draw_play_area(self, font: pygame.font.Font) -> None:
        if not self.play_area_rect:
            return
        padding = int(15 * self.scale)
        area = self.play_area_rect

        # AI discards (top)
        ai_discards = self.discards.get(self.ai_player, [])
        discards_rect = pygame.Rect(area.x + padding, area.y + padding, area.width - padding * 2, self.tile_height + int(10 * self.scale))
        self._draw_tile_row(ai_discards, discards_rect, face_up=True)

        # AI hand (hidden)
        ai_hand = self._get_hand_tiles(self.ai_player)
        ai_hand_rect = pygame.Rect(area.x + padding, discards_rect.bottom + int(10 * self.scale),
                                   area.width - padding * 2, self.tile_height + int(10 * self.scale))
        self._draw_tile_row(ai_hand, ai_hand_rect, face_up=False)

        # Player discards (middle)
        player_discards = self.discards.get(self.human_player, [])
        player_discards_rect = pygame.Rect(area.x + padding, ai_hand_rect.bottom + int(15 * self.scale),
                                           area.width - padding * 2, self.tile_height + int(10 * self.scale))
        self._draw_tile_row(player_discards, player_discards_rect, face_up=True)

        # Player hand (bottom)
        hand = self._get_hand_tiles(self.human_player)
        hand_rect = pygame.Rect(area.x + padding, area.bottom - self.tile_height - int(20 * self.scale),
                                area.width - padding * 2, self.tile_height + int(10 * self.scale))
        for idx, rect in self._player_hand_rects(hand, hand_rect):
            tile = hand[idx]
            if self.hovered_tile_index == idx and self.current_player == self.human_player and self.awaiting_discard:
                hover_surface = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
                hover_surface.fill((0, 255, 255, 40))
                self.screen.blit(hover_surface, rect.topleft)
            self._draw_tile(tile, rect, face_up=True)

        # Labels
        try:
            label_ai = font.render("OPPONENT", True, COLOR_CYAN)
            self.screen.blit(label_ai, (discards_rect.x, discards_rect.y - int(18 * self.scale)))
            label_player = font.render("PLAYER", True, COLOR_CYAN)
            self.screen.blit(label_player, (player_discards_rect.x, player_discards_rect.y - int(18 * self.scale)))
        except Exception:
            pass

    def _draw_tile_row(self, tiles: List[object], rect: pygame.Rect, face_up: bool) -> None:
        if rect.width <= 0 or rect.height <= 0:
            return
        spacing = int(6 * self.scale)
        x = rect.x
        for tile in tiles[:14]:
            tile_rect = pygame.Rect(x, rect.y, self.tile_width, self.tile_height)
            self._draw_tile(tile, tile_rect, face_up=face_up)
            x += self.tile_width + spacing
            if x + self.tile_width > rect.right:
                break

    def _player_hand_rects(self, hand: List[object], rect_override: Optional[pygame.Rect] = None):
        rect = rect_override or pygame.Rect(
            self.play_area_rect.x + int(15 * self.scale),
            self.play_area_rect.bottom - self.tile_height - int(20 * self.scale),
            self.play_area_rect.width - int(30 * self.scale),
            self.tile_height + int(10 * self.scale),
        )
        spacing = int(6 * self.scale)
        x = rect.x
        for idx, _ in enumerate(hand):
            tile_rect = pygame.Rect(x, rect.y, self.tile_width, self.tile_height)
            yield idx, tile_rect
            x += self.tile_width + spacing

    def _draw_tile(self, tile: object, rect: pygame.Rect, face_up: bool = True) -> None:
        if not face_up:
            self._draw_tile_back(rect)
            return
        spec = self._tile_to_spec(tile)
        if spec and spec in self.tile_image_by_spec:
            self.screen.blit(self.tile_image_by_spec[spec], rect.topleft)
            return
        self._draw_tile_fallback(tile, rect)

    def _draw_tile_back(self, rect: pygame.Rect) -> None:
        pygame.draw.rect(self.screen, COLOR_BG_TITLE, rect)
        pygame.draw.rect(self.screen, COLOR_CYAN, rect, 2)
        inner = rect.inflate(-int(8 * self.scale), -int(8 * self.scale))
        pygame.draw.rect(self.screen, COLOR_DARK_CYAN, inner, 1)

    def _draw_tile_fallback(self, tile: object, rect: pygame.Rect) -> None:
        pygame.draw.rect(self.screen, COLOR_WHITE, rect)
        pygame.draw.rect(self.screen, COLOR_DARK_CYAN, rect, 2)
        spec = self._tile_to_spec(tile)
        label = "?"
        if spec:
            label = f"{spec[0][0].upper()}{spec[1]}"
        try:
            font = pygame.font.SysFont("verdana", max(int(14 * self.scale), 9))
            txt = font.render(label, True, COLOR_BLACK)
            self.screen.blit(txt, txt.get_rect(center=rect.center))
        except Exception:
            pass

    def _draw_stats_panel(self, body_font: pygame.font.Font, small_font: pygame.font.Font) -> None:
        panel_rect = self.stats_panel_rect
        pygame.draw.rect(self.screen, COLOR_BG_DARK, panel_rect)
        pygame.draw.rect(self.screen, COLOR_DARK_CYAN, panel_rect, 1)
        pygame.draw.line(
            self.screen,
            COLOR_CYAN,
            (panel_rect.x, panel_rect.y),
            (panel_rect.x, panel_rect.bottom),
            2,
        )

        title_height = int(24 * self.scale)
        title_rect = pygame.Rect(panel_rect.x, panel_rect.y, panel_rect.width, title_height)
        pygame.draw.rect(self.screen, COLOR_BG_TITLE, title_rect)
        pygame.draw.line(self.screen, COLOR_CYAN, (panel_rect.x, title_rect.bottom), (panel_rect.right, title_rect.bottom), 1)
        title = body_font.render("GAME STATS", True, COLOR_WHITE)
        self.screen.blit(title, (panel_rect.x + (panel_rect.width - title.get_width()) // 2, title_rect.y + 2))

        y = panel_rect.y + title_height + int(12 * self.scale)
        line_h = int(21 * self.scale)
        content_x = panel_rect.x + int(10 * self.scale)
        max_y = panel_rect.bottom - int(10 * self.scale)

        if y < max_y:
            mins = int(self.elapsed_time // 60)
            secs = int(self.elapsed_time % 60)
            time_label = small_font.render("Time:", True, COLOR_CYAN)
            time_value = small_font.render(f"{mins:02d}:{secs:02d}", True, COLOR_WHITE)
            self.screen.blit(time_label, (content_x, y))
            self.screen.blit(time_value, (content_x + time_label.get_width() + int(6 * self.scale), y))
            y += line_h

        if y < max_y:
            wall_label = small_font.render("Wall:", True, COLOR_CYAN)
            wall_value = small_font.render(str(self.wall_remaining), True, COLOR_WHITE)
            self.screen.blit(wall_label, (content_x, y))
            self.screen.blit(wall_value, (content_x + wall_label.get_width() + int(6 * self.scale), y))
            y += line_h

        if y < max_y:
            turn_label = small_font.render("Turn:", True, COLOR_CYAN)
            turn_value = "Player" if self.current_player == self.human_player else "Opponent"
            self.screen.blit(turn_label, (content_x, y))
            self.screen.blit(small_font.render(turn_value, True, COLOR_WHITE), (content_x + turn_label.get_width() + int(6 * self.scale), y))
            y += line_h

        if y < max_y:
            player_label = small_font.render("Wins:", True, COLOR_CYAN)
            player_value = small_font.render(str(self.player_score), True, COLOR_WHITE)
            self.screen.blit(player_label, (content_x, y))
            self.screen.blit(player_value, (content_x + player_label.get_width() + int(6 * self.scale), y))
            y += line_h

        if y < max_y:
            ai_label = small_font.render("Opp Wins:", True, COLOR_CYAN)
            ai_value = small_font.render(str(self.ai_score), True, COLOR_WHITE)
            self.screen.blit(ai_label, (content_x, y))
            self.screen.blit(ai_value, (content_x + ai_label.get_width() + int(6 * self.scale), y))
            y += line_h

        if y < max_y:
            y += int(6 * self.scale)
            pygame.draw.line(self.screen, COLOR_DARK_CYAN, (panel_rect.x + int(8 * self.scale), y),
                             (panel_rect.right - int(8 * self.scale), y), 1)
            y += int(12 * self.scale)

        # Buttons
        if self.new_game_rect:
            new_color = COLOR_BUTTON_HOVER if self.hovered_button == "new_game" else COLOR_BG_TITLE
            pygame.draw.rect(self.screen, new_color, self.new_game_rect)
            pygame.draw.rect(self.screen, COLOR_CYAN, self.new_game_rect, 2)
            new_text = small_font.render("NEW GAME", True, COLOR_WHITE)
            self.screen.blit(new_text, new_text.get_rect(center=self.new_game_rect.center))

        for level, rect in self.level_button_rects.items():
            is_active = (level == self.ai_level)
            is_hover = self.hovered_button == f"level_{level}"
            color = (70, 70, 100) if is_active else COLOR_BG_TITLE
            if is_hover:
                color = COLOR_BUTTON_HOVER
            pygame.draw.rect(self.screen, color, rect)
            pygame.draw.rect(self.screen, COLOR_CYAN if is_active else COLOR_DARK_CYAN, rect, 2)
            label = small_font.render(level.upper(), True, COLOR_WHITE)
            self.screen.blit(label, label.get_rect(center=rect.center))

        if self.draw_button_rect:
            draw_color = COLOR_BUTTON_HOVER if self.hovered_button == "draw" else COLOR_BG_TITLE
            pygame.draw.rect(self.screen, draw_color, self.draw_button_rect)
            pygame.draw.rect(self.screen, COLOR_CYAN, self.draw_button_rect, 2)
            label = small_font.render("DRAW", True, COLOR_WHITE)
            self.screen.blit(label, label.get_rect(center=self.draw_button_rect.center))

        # Rules
        rules_y = panel_rect.y + int(320 * self.scale)
        if rules_y < max_y:
            header = small_font.render("HOW TO PLAY", True, COLOR_YELLOW)
            self.screen.blit(header, (content_x, rules_y))
            rules_y += int(20 * self.scale)
            rules = [
                "- Click DRAW to take a tile",
                "- Click a tile to discard",
                "- First to win the round scores",
            ]
            for line in rules:
                if rules_y > max_y:
                    break
                text = small_font.render(line, True, COLOR_GREY)
                self.screen.blit(text, (content_x, rules_y))
                rules_y += int(16 * self.scale)

        if self.engine_error:
            err = small_font.render("ENGINE ERROR", True, COLOR_RED)
            self.screen.blit(err, (content_x, panel_rect.bottom - int(40 * self.scale)))
            details = small_font.render("Check PyRiichi install", True, COLOR_GREY)
            self.screen.blit(details, (content_x, panel_rect.bottom - int(22 * self.scale)))

        # Win message
        if self.game_over:
            if self.win_state == "player":
                msg = "PLAYER WINS!"
                msg_color = COLOR_GREEN
            elif self.win_state == "ai":
                msg = "OPPONENT WINS"
                msg_color = COLOR_RED
            else:
                msg = "DRAW GAME"
                msg_color = COLOR_YELLOW
            msg_surface = body_font.render(msg, True, msg_color)
            msg_bg = pygame.Surface(
                (msg_surface.get_width() + int(16 * self.scale), msg_surface.get_height() + int(8 * self.scale)),
                pygame.SRCALPHA,
            )
            msg_bg.fill((*msg_color[:3], 30))
            msg_bg_x = panel_rect.x + (panel_rect.width - msg_bg.get_width()) // 2
            msg_bg_y = panel_rect.bottom - msg_bg.get_height() - int(12 * self.scale)
            if msg_bg_y >= panel_rect.y:
                self.screen.blit(msg_bg, (msg_bg_x, msg_bg_y))
                pygame.draw.rect(self.screen, msg_color, (msg_bg_x, msg_bg_y, msg_bg.get_width(), msg_bg.get_height()), 2)
                self.screen.blit(
                    msg_surface,
                    (panel_rect.x + (panel_rect.width - msg_surface.get_width()) // 2, msg_bg_y + int(4 * self.scale)),
                )
