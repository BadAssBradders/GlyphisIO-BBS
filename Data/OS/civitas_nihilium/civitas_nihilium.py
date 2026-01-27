"""
Civitas Nihilium Game Module
Investigation and trial card/dice game for the OS Mode desktop environment.

- Renders inside OS Mode desktop bounds; same resolution, scaling, clipping, and
  window framing as Solitaire.
- Uses Data/OS/civitas_nihilium/assets/ (optional) and Data/OS/Civitas Nihilium/
  (existing Cards, Dice) when present. Works without assets (vector fallback).

Expected layout:
    Data/OS/civitas_nihilium/civitas_nihilium.py
    Data/OS/civitas_nihilium/assets/cards/  (optional)
    Data/OS/Civitas Nihilium/Cards/         (optional, existing)
    Data/OS/Civitas Nihilium/Dice/D10/      (optional, for D10 faces)
"""

import pygame
import os
import sys
import random
import time
from typing import List, Dict, Tuple, Optional

# Visual constants (match OS_Mode / Solitaire)
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

RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
SUITS = ["H", "D", "C", "S"]  # Hearts, Diamonds, Clubs, Spades


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


# -----------------------------------------------------------------------------
# Data models
# -----------------------------------------------------------------------------

class Card:
    __slots__ = ("rank", "suit")

    def __init__(self, rank: str, suit: str):
        self.rank = rank
        self.suit = suit

    @property
    def numeric_value(self) -> int:
        if self.rank == "A":
            return 1
        if self.rank in ("J", "Q", "K"):
            return 10
        return int(self.rank)

    @property
    def display_string(self) -> str:
        return f"{self.rank}{self.suit}"

    def is_modifier_card(self) -> bool:
        """Diamond or Heart 7–10: attach-once modifier."""
        return self.suit in ("D", "H") and self.rank in ("7", "8", "9", "10")

    def modifier_bonus(self) -> int:
        if not self.is_modifier_card():
            return 0
        return {"7": 1, "8": 2, "9": 3, "10": 4}.get(self.rank, 0)


class Deck:
    def __init__(self, cards: List[Card]):
        self.cards = list(cards)

    def shuffle(self) -> None:
        random.shuffle(self.cards)

    def draw(self) -> Optional[Card]:
        if not self.cards:
            return None
        return self.cards.pop()

    def replenish(self, from_cards: List[Card]) -> None:
        self.cards.extend(from_cards)
        random.shuffle(self.cards)


class PlayerState:
    def __init__(self, rep: int = 3, ion: int = 2, hp: int = 4, ether: int = 2):
        self.rep = rep
        self.ion = ion
        self.hp = hp
        self.ether = ether

    def clamp(self) -> None:
        self.rep = max(0, self.rep)
        self.ion = max(0, self.ion)
        self.hp = max(0, self.hp)
        self.ether = max(0, self.ether)


# -----------------------------------------------------------------------------
# Game state
# -----------------------------------------------------------------------------

PHASE_SETUP = "setup"
PHASE_INVESTIGATION = "investigation"
PHASE_SELECT_CARD = "select_card"
PHASE_ENCOUNTER = "encounter"
PHASE_TRIAL = "trial"
PHASE_ATTACH_MODIFIER = "attach_modifier"
PHASE_NEXT_INV = "next_inv"
PHASE_ROUND_ADV = "round_adv"
PHASE_GAME_OVER_VICTORY = "game_over_victory"
PHASE_GAME_OVER_DEFEAT = "game_over_defeat"

INV_PER_ROUND = 2
ROUNDS = 3
FEC_VALUES = [5, 6, 5, 7, 6, 8]
WEAPON_COST_ETHER = 2
WEAPON_BONUS = 2
WEAPON_ION_COST = 1
ASSISTANCE_BONUS = 1


# -----------------------------------------------------------------------------
# CivitasNihiliumGame
# -----------------------------------------------------------------------------

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
    ):
        self.screen = screen
        self.scale = scale
        self.desktop_x = desktop_x
        self.desktop_y = desktop_y
        self.desktop_size = desktop_size
        self.bbs_x = bbs_x
        self.bbs_width = bbs_width
        self.get_radio_music = get_radio_music_callback or (lambda: False)

        self.active = False
        self.hovered_button: Optional[str] = None
        self.hovered_card_index: Optional[int] = None

        # Layout
        self.window_rect: Optional[pygame.Rect] = None
        self.title_bar_rect: Optional[pygame.Rect] = None
        self.exit_button_rect: Optional[pygame.Rect] = None
        self.stats_panel_rect: Optional[pygame.Rect] = None
        self.play_area_rect: Optional[pygame.Rect] = None

        self.card_width = int(52 * self.scale)
        self.card_height = int(72 * self.scale)
        self.card_rects: List[pygame.Rect] = []  # 6 for witness+location

        # Buttons (set in _update_layout / _update_play_rects)
        self.roll_rect: Optional[pygame.Rect] = None
        self.continue_rect: Optional[pygame.Rect] = None
        self.assistance_rect: Optional[pygame.Rect] = None
        self.use_weapon_rect: Optional[pygame.Rect] = None
        self.buy_weapon_rect: Optional[pygame.Rect] = None
        self.attach_mc_rect: Optional[pygame.Rect] = None
        self.attach_rookie_rect: Optional[pygame.Rect] = None

        # Fonts (cached)
        self.title_font: Optional[pygame.font.Font] = None
        self.body_font: Optional[pygame.font.Font] = None
        self.small_font: Optional[pygame.font.Font] = None

        # Assets
        self.card_face_surfaces: Dict[str, pygame.Surface] = {}
        self.d10_surfaces: Dict[int, pygame.Surface] = {}
        self.bg_surface: Optional[pygame.Surface] = None

        # Game state (reset in start)
        self.phase = PHASE_SETUP
        self.round_num = 1
        self.investigation_count = 0
        self.mc = PlayerState()
        self.rookie = PlayerState()
        self.witness_deck: Optional[Deck] = None
        self.location_deck: Optional[Deck] = None
        self.encounter_deck: List[int] = []
        self.witness_pool: List[Card] = []
        self.location_pool: List[Card] = []
        self.selected_card: Optional[Card] = None
        self.qualified = False
        self.encounter_effect = ""
        self.fec_values: List[int] = []
        self.fec_index = 0
        self.evidence_remaining = 0
        self.assistance_on = False
        self.use_weapon_on = False
        self.weapons: List[str] = []
        self.modifiers_mc: List[int] = []
        self.modifiers_rookie: List[int] = []
        self.pending_modifier: Optional[int] = None
        self.combat_log: List[str] = []
        self.last_roll: Optional[int] = None
        self.last_d10_base: Optional[int] = None  # 1–10 for D10 display
        self.purchased_weapons: int = 0

        self.dice_rect: Optional[pygame.Rect] = None
        self.log_start_y: int = 0

        self._update_layout()
        self._update_fonts()
        self._load_assets()

    def _update_fonts(self) -> None:
        try:
            self.title_font = pygame.font.SysFont("verdana", max(int(26 * self.scale), 16))
            self.body_font = pygame.font.SysFont("verdana", max(int(18 * self.scale), 12))
            self.small_font = pygame.font.SysFont("verdana", max(int(16 * self.scale), 10))
        except Exception:
            try:
                self.title_font = pygame.font.Font(None, max(int(26 * self.scale), 16))
                self.body_font = pygame.font.Font(None, max(int(18 * self.scale), 12))
                self.small_font = pygame.font.Font(None, max(int(16 * self.scale), 10))
            except Exception:
                self.title_font = self.body_font = self.small_font = None

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
        self._update_fonts()
        if self.active:
            self._load_assets()

    def _update_layout(self) -> None:
        title_bar_height = int(35 * self.scale)
        stats_panel_width = int(240 * self.scale)

        window_width = self.desktop_size[0]
        window_height = self.desktop_size[1]
        window_x = self.desktop_x
        window_y = self.desktop_y

        self.window_rect = pygame.Rect(window_x, window_y, window_width, window_height)
        self.title_bar_rect = pygame.Rect(window_x, window_y, window_width, title_bar_height)

        exit_w = int(60 * self.scale)
        exit_h = int(25 * self.scale)
        self.exit_button_rect = pygame.Rect(
            window_x + window_width - exit_w - int(15 * self.scale),
            window_y + (title_bar_height - exit_h) // 2,
            exit_w, exit_h,
        )

        content_y = window_y + title_bar_height
        content_height = window_height - title_bar_height

        self.stats_panel_rect = pygame.Rect(
            window_x + window_width - stats_panel_width,
            content_y,
            stats_panel_width,
            content_height,
        )

        play_margin = int(15 * self.scale)
        self.play_area_rect = pygame.Rect(
            window_x + play_margin,
            content_y + int(10 * self.scale),
            window_width - stats_panel_width - play_margin * 2,
            content_height - int(20 * self.scale),
        )
        self._update_play_rects()

    def _update_play_rects(self) -> None:
        if not self.play_area_rect:
            return
        pa = self.play_area_rect
        pad = int(12 * self.scale)
        cw, ch = self.card_width, self.card_height
        gap = int(8 * self.scale)

        # 6 cards: 3 witness (0–2), 3 location (3–5). Two rows. Labels above each row.
        label_above = int(24 * self.scale)  # leave room for header
        row1_y = pa.y + pad + label_above
        row2_y = pa.y + pad + label_above + ch + gap
        start_x = pa.x + pad
        self.card_rects = []
        for i in range(6):
            x = start_x + (i % 3) * (cw + gap)
            y = row1_y if i < 3 else row2_y
            self.card_rects.append(pygame.Rect(x, y, cw, ch))

        # Selected/qual text: row2_y+ch+6 and +20. Buttons start below with clear gap.
        btn_h = int(26 * self.scale)
        btn_w = int(100 * self.scale)
        db = btn_h + gap
        btn_y = row2_y + ch + int(38 * self.scale)

        self.roll_rect = pygame.Rect(pa.x + pad, btn_y, btn_w, btn_h)
        self.continue_rect = pygame.Rect(pa.x + pad + btn_w + gap, btn_y, btn_w, btn_h)
        d10_sz = int(40 * self.scale)
        self.dice_rect = pygame.Rect(self.continue_rect.right + gap, btn_y, d10_sz, d10_sz)

        self.assistance_rect = pygame.Rect(pa.x + pad, btn_y + db, int(120 * self.scale), btn_h)
        self.use_weapon_rect = pygame.Rect(pa.x + pad + int(124 * self.scale), btn_y + db, int(90 * self.scale), btn_h)
        self.buy_weapon_rect = pygame.Rect(pa.x + pad + int(218 * self.scale), btn_y + db, int(80 * self.scale), btn_h)
        attach_y = btn_y + db * 2
        self.attach_mc_rect = pygame.Rect(pa.x + pad, attach_y, int(70 * self.scale), btn_h)
        self.attach_rookie_rect = pygame.Rect(pa.x + pad + int(76 * self.scale), attach_y, int(84 * self.scale), btn_h)

        self.log_start_y = btn_y + db * 3 + int(8 * self.scale)

    def _load_assets(self) -> None:
        self.card_face_surfaces.clear()
        self.d10_surfaces.clear()

        for base in [
            get_data_path("OS", "civitas_nihilium", "assets", "cards"),
            get_data_path("OS", "Civitas Nihilium", "Cards"),
        ]:
            if not os.path.isdir(base):
                continue
            for r in RANKS:
                for s in SUITS:
                    key = f"{r}{s}"
                    if key in self.card_face_surfaces:
                        continue
                    path = os.path.join(base, f"card_{r}{s}.png")
                    if os.path.exists(path):
                        try:
                            img = pygame.image.load(path).convert_alpha()
                            self.card_face_surfaces[key] = pygame.transform.smoothscale(
                                img, (self.card_width, self.card_height)
                            )
                        except Exception:
                            pass
            if self.card_face_surfaces:
                break

        for base in [
            get_data_path("OS", "civitas_nihilium", "assets", "dice", "D10"),
            get_data_path("OS", "Civitas Nihilium", "Dice", "D10"),
        ]:
            if not os.path.isdir(base):
                continue
            for v in range(1, 11):
                path = os.path.join(base, f"{v}.png")
                if os.path.exists(path):
                    try:
                        img = pygame.image.load(path).convert_alpha()
                        sz = int(40 * self.scale)
                        self.d10_surfaces[v] = pygame.transform.smoothscale(img, (sz, sz))
                    except Exception:
                        pass
            if self.d10_surfaces:
                break

        bg_path = get_data_path("OS", "civitas_nihilium", "assets", "bg.png")
        if os.path.exists(bg_path):
            try:
                self.bg_surface = pygame.image.load(bg_path).convert_alpha()
            except Exception:
                self.bg_surface = None
        else:
            self.bg_surface = None

    def start(self) -> None:
        self._setup_game()
        self.active = True

    def _setup_game(self) -> None:
        self.phase = PHASE_SETUP
        self.round_num = 1
        self.investigation_count = 0
        self.mc = PlayerState(3, 2, 4, 2)
        self.rookie = PlayerState(3, 2, 4, 2)
        self.witness_pool = []
        self.location_pool = []
        self.selected_card = None
        self.qualified = False
        self.encounter_effect = ""
        self.fec_values = list(FEC_VALUES)
        self.fec_index = 0
        self.evidence_remaining = 0
        self.assistance_on = False
        self.use_weapon_on = False
        self.weapons = []
        self.modifiers_mc = []
        self.modifiers_rookie = []
        self.pending_modifier = None
        self.combat_log = ["Civitas Nihilium begun."]
        self.last_roll = None
        self.last_d10_base = None
        self.purchased_weapons = 0

        # Witness: H+D (26). Location: C+S (26).
        witness_cards = [Card(r, s) for s in ("H", "D") for r in RANKS]
        location_cards = [Card(r, s) for s in ("C", "S") for r in RANKS]
        self.witness_deck = Deck(witness_cards)
        self.location_deck = Deck(location_cards)
        self.witness_deck.shuffle()
        self.location_deck.shuffle()

        # Encounter: 6 effects
        self.encounter_deck = [1, 2, 3, 4, 5, 6]
        random.shuffle(self.encounter_deck)

        self.phase = PHASE_INVESTIGATION
        self._do_investigation_draw()

    def _do_investigation_draw(self) -> None:
        self.witness_pool = []
        self.location_pool = []
        for _ in range(3):
            c = self.witness_deck.draw()
            if c is None:
                self.witness_deck.replenish([Card(r, s) for s in ("H", "D") for r in RANKS])
                c = self.witness_deck.draw()
            if c:
                self.witness_pool.append(c)
        for _ in range(3):
            c = self.location_deck.draw()
            if c is None:
                self.location_deck.replenish([Card(r, s) for s in ("C", "S") for r in RANKS])
                c = self.location_deck.draw()
            if c:
                self.location_pool.append(c)
        self.selected_card = None
        self.qualified = False
        self.last_roll = None
        self.last_d10_base = None
        self.evidence_remaining = self.fec_values[self.fec_index]
        self.phase = PHASE_SELECT_CARD
        self._log(f"Round {self.round_num} – Investigation {self.investigation_count + 1}. Select a card.")

    def _log(self, msg: str) -> None:
        self.combat_log.append(msg)
        while len(self.combat_log) > 10:
            self.combat_log.pop(0)

    def _combined_resources(self) -> int:
        return self.mc.rep + self.mc.ion + self.rookie.rep + self.rookie.ion

    def _apply_encounter(self) -> None:
        if not self.encounter_deck:
            self.encounter_deck = [1, 2, 3, 4, 5, 6]
            random.shuffle(self.encounter_deck)
        eff = self.encounter_deck.pop()
        if eff == 1:
            self.mc.hp -= 1
            self.encounter_effect = "MC –1 HP"
        elif eff == 2:
            self.rookie.hp -= 1
            self.encounter_effect = "Rookie –1 HP"
        elif eff == 3:
            self.mc.ether -= 1
            self.encounter_effect = "MC –1 Ether"
        elif eff == 4:
            self.rookie.ether -= 1
            self.encounter_effect = "Rookie –1 Ether"
        elif eff == 5:
            self.mc.rep -= 1
            self.encounter_effect = "MC –1 Rep"
        else:
            self.rookie.rep -= 1
            self.encounter_effect = "Rookie –1 Rep"
        self.mc.clamp()
        self.rookie.clamp()
        self._log(f"Encounter: {self.encounter_effect}")

        if self.mc.hp <= 0 or self.rookie.hp <= 0:
            self.phase = PHASE_GAME_OVER_DEFEAT
            self._log("Defeat: a character has fallen.")
        else:
            self.phase = PHASE_ENCOUNTER  # show effect; Continue -> TRIAL

    def _trial_roll(self) -> None:
        base = random.randint(1, 10)
        self.last_d10_base = base
        mod = sum(self.modifiers_mc) + sum(self.modifiers_rookie)
        if self.assistance_on:
            mod += ASSISTANCE_BONUS
        if self.use_weapon_on and self.purchased_weapons > 0 and self.mc.ion >= WEAPON_ION_COST:
            mod += WEAPON_BONUS
            self.mc.ion -= WEAPON_ION_COST
            self.mc.clamp()
        self.use_weapon_on = False
        total = base + mod
        self.last_roll = total
        self._log(f"Roll: D10={base} + mods={mod} → {total}. FEC evidence={self.evidence_remaining}")

        self.evidence_remaining = max(0, self.evidence_remaining - total)
        if self.evidence_remaining <= 0:
            self._log("FEC defeated. Resource+")
            self.mc.rep += 1
            self.mc.ion += 1
            self.rookie.rep += 1
            self.rookie.ion += 1
            self.mc.clamp()
            self.rookie.clamp()

            if self.selected_card and self.selected_card.is_modifier_card():
                self.pending_modifier = self.selected_card.modifier_bonus()
                self.phase = PHASE_ATTACH_MODIFIER
            else:
                self._to_next_inv()
        else:
            self.mc.hp -= 1
            self.mc.clamp()
            self._log("FEC holds. MC –1 HP.")
            if self.mc.hp <= 0:
                self.phase = PHASE_GAME_OVER_DEFEAT
                self._log("Defeat: MC has fallen.")

    def _to_next_inv(self) -> None:
        self.pending_modifier = None
        self.investigation_count += 1
        self.fec_index += 1

        if self.investigation_count >= 6:
            self.phase = PHASE_GAME_OVER_VICTORY
            self._log("All 6 FECs defeated. Victory.")
            return

        inv_in_round = self.investigation_count % INV_PER_ROUND
        if inv_in_round == 0:
            self.phase = PHASE_ROUND_ADV
            self.round_num += 1
        else:
            self.phase = PHASE_INVESTIGATION
            self._do_investigation_draw()

    def close(self) -> None:
        self.active = False
        self.selected_card = None
        self.hovered_button = None
        self.hovered_card_index = None

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.active:
            return False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.close()
                return True
            if event.key == pygame.K_r and self.phase == PHASE_TRIAL:
                self._trial_roll()
                return True
            if event.key == pygame.K_SPACE and self.phase in (PHASE_ATTACH_MODIFIER, PHASE_NEXT_INV, PHASE_ROUND_ADV, PHASE_ENCOUNTER):
                self._handle_continue_action()
                return True

        if event.type == pygame.MOUSEMOTION:
            mx, my = event.pos
            self.hovered_button = None
            self.hovered_card_index = None
            if self.exit_button_rect and self.exit_button_rect.collidepoint(mx, my):
                self.hovered_button = "exit"
            elif self.roll_rect and self.roll_rect.collidepoint(mx, my):
                self.hovered_button = "roll"
            elif self.continue_rect and self.continue_rect.collidepoint(mx, my):
                self.hovered_button = "continue"
            elif self.assistance_rect and self.assistance_rect.collidepoint(mx, my):
                self.hovered_button = "assistance"
            elif self.use_weapon_rect and self.use_weapon_rect.collidepoint(mx, my):
                self.hovered_button = "use_weapon"
            elif self.buy_weapon_rect and self.buy_weapon_rect.collidepoint(mx, my):
                self.hovered_button = "buy_weapon"
            elif self.attach_mc_rect and self.attach_mc_rect.collidepoint(mx, my):
                self.hovered_button = "attach_mc"
            elif self.attach_rookie_rect and self.attach_rookie_rect.collidepoint(mx, my):
                self.hovered_button = "attach_rookie"
            else:
                all_cards = self.witness_pool + self.location_pool
                for i, r in enumerate(self.card_rects):
                    if i < len(all_cards) and r.collidepoint(mx, my):
                        self.hovered_card_index = i
                        break
            return False

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos

            if self.exit_button_rect and self.exit_button_rect.collidepoint(mx, my):
                self.close()
                return True

            if self.phase == PHASE_SELECT_CARD and self.hovered_card_index is not None:
                all_cards = self.witness_pool + self.location_pool
                if 0 <= self.hovered_card_index < len(all_cards):
                    c = all_cards[self.hovered_card_index]
                    self.selected_card = c
                    self.qualified = self._combined_resources() >= c.numeric_value
                    if self.qualified:
                        self._log(f"Selected {c.display_string} (value {c.numeric_value}). Qualified.")
                        self.phase = PHASE_TRIAL
                    else:
                        self._log(f"Selected {c.display_string}. Not qualified. Encounter.")
                        self.phase = PHASE_ENCOUNTER
                        self._apply_encounter()
                    return True

            if self.phase == PHASE_TRIAL:
                if self.roll_rect and self.roll_rect.collidepoint(mx, my):
                    self._trial_roll()
                    return True
                if self.assistance_rect and self.assistance_rect.collidepoint(mx, my):
                    self.assistance_on = not self.assistance_on
                    return True
                if self.use_weapon_rect and self.use_weapon_rect.collidepoint(mx, my):
                    if self.purchased_weapons > 0 and self.mc.ion >= WEAPON_ION_COST:
                        self.use_weapon_on = not self.use_weapon_on
                    return True
                if self.buy_weapon_rect and self.buy_weapon_rect.collidepoint(mx, my):
                    if self.mc.ether >= WEAPON_COST_ETHER and self.purchased_weapons < 2:
                        self.mc.ether -= WEAPON_COST_ETHER
                        self.purchased_weapons += 1
                        self._log("Weapon purchased.")
                    return True

            if self.phase == PHASE_ENCOUNTER and self.continue_rect and self.continue_rect.collidepoint(mx, my):
                self.phase = PHASE_TRIAL
                return True

            if self.phase == PHASE_ATTACH_MODIFIER:
                if self.attach_mc_rect and self.attach_mc_rect.collidepoint(mx, my) and self.pending_modifier is not None:
                    self.modifiers_mc.append(self.pending_modifier)
                    self._log(f"+{self.pending_modifier} to MC.")
                    self._to_next_inv()
                    return True
                if self.attach_rookie_rect and self.attach_rookie_rect.collidepoint(mx, my) and self.pending_modifier is not None:
                    self.modifiers_rookie.append(self.pending_modifier)
                    self._log(f"+{self.pending_modifier} to Rookie.")
                    self._to_next_inv()
                    return True

            if self.phase == PHASE_ROUND_ADV and self.continue_rect and self.continue_rect.collidepoint(mx, my):
                self.phase = PHASE_INVESTIGATION
                self._do_investigation_draw()
                return True

        return False

    def _handle_continue_action(self) -> None:
        if self.phase == PHASE_ATTACH_MODIFIER and self.pending_modifier is not None:
            self.modifiers_mc.append(self.pending_modifier)
            self._to_next_inv()
        elif self.phase == PHASE_ROUND_ADV:
            self.phase = PHASE_INVESTIGATION
            self._do_investigation_draw()
        elif self.phase == PHASE_ENCOUNTER:
            self.phase = PHASE_TRIAL

    def draw(self) -> None:
        if not self.active:
            return

        if not self.window_rect or not self.title_font or not self.body_font or not self.small_font:
            return

        old_clip = self.screen.get_clip()
        self.screen.set_clip(self.window_rect)

        if self.bg_surface:
            try:
                self.screen.blit(
                    pygame.transform.smoothscale(self.bg_surface, (self.window_rect.width, self.window_rect.height)),
                    self.window_rect.topleft,
                )
            except Exception:
                pass
        pygame.draw.rect(self.screen, COLOR_BG_DARK, self.window_rect)
        pygame.draw.rect(self.screen, COLOR_CYAN, self.window_rect, 2)

        pygame.draw.rect(self.screen, COLOR_BG_TITLE, self.title_bar_rect)
        pygame.draw.line(
            self.screen, COLOR_CYAN,
            (self.title_bar_rect.x, self.title_bar_rect.bottom - 1),
            (self.title_bar_rect.right, self.title_bar_rect.bottom - 1), 2,
        )
        tit = self.title_font.render("CIVITAS NIHILIUM", True, COLOR_WHITE)
        self.screen.blit(tit, (self.title_bar_rect.x + int(15 * self.scale), self.title_bar_rect.centery - tit.get_height() // 2))

        if self.exit_button_rect:
            bc = COLOR_BUTTON_HOVER if self.hovered_button == "exit" else COLOR_BG_TITLE
            pygame.draw.rect(self.screen, bc, self.exit_button_rect)
            pygame.draw.rect(self.screen, COLOR_CYAN, self.exit_button_rect, 2)
            ex = self.small_font.render("EXIT", True, COLOR_WHITE)
            self.screen.blit(ex, ex.get_rect(center=self.exit_button_rect.center))

        pygame.draw.rect(self.screen, (15, 15, 35), self.play_area_rect)
        pygame.draw.rect(self.screen, COLOR_DARK_CYAN, self.play_area_rect, 1)

        self._draw_play_area()
        self._draw_stats_panel()

        self.screen.set_clip(old_clip)

    def _draw_play_area(self) -> None:
        pa = self.play_area_rect
        sf = self.small_font
        if not pa or not sf:
            return

        # Header
        inv = self.investigation_count + 1
        hdr = f"Round {self.round_num} – Investigation {inv}/6"
        self.screen.blit(sf.render(hdr, True, COLOR_CYAN), (pa.x + int(12 * self.scale), pa.y + int(4 * self.scale)))

        # Witness / Location labels (above each row)
        if self.card_rects:
            self.screen.blit(sf.render("Witness", True, COLOR_GREY), (self.card_rects[0].x, self.card_rects[0].y - int(14 * self.scale)))
            if len(self.card_rects) > 3:
                self.screen.blit(sf.render("Location", True, COLOR_GREY), (self.card_rects[3].x, self.card_rects[3].y - int(14 * self.scale)))

        all_cards = self.witness_pool + self.location_pool
        for i, r in enumerate(self.card_rects):
            if i >= len(all_cards):
                pygame.draw.rect(self.screen, COLOR_BG_TITLE, r)
                pygame.draw.rect(self.screen, COLOR_DARK_CYAN, r, 2)
                continue
            c = all_cards[i]
            hl = (self.hovered_card_index == i and self.phase == PHASE_SELECT_CARD)
            if hl:
                surf = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
                surf.fill((0, 255, 255, 50))
                self.screen.blit(surf, r.topleft)
            self._draw_card(c, r)
            if c == self.selected_card:
                pygame.draw.rect(self.screen, COLOR_YELLOW, r.inflate(6, 6), 3)

        # Selected / qualification (below cards, above buttons)
        base_y = self.card_rects[5].bottom if len(self.card_rects) > 5 else pa.y + int(100 * self.scale)
        if self.selected_card:
            qual_col = COLOR_GREEN if self.qualified else COLOR_RED
            self.screen.blit(sf.render(f"Selected: {self.selected_card.display_string} (value {self.selected_card.numeric_value})", True, COLOR_WHITE),
                            (pa.x + int(12 * self.scale), base_y + int(6 * self.scale)))
            self.screen.blit(sf.render("Qualified" if self.qualified else "Not qualified", True, qual_col),
                            (pa.x + int(12 * self.scale), base_y + int(20 * self.scale)))

        # Encounter / Round-advance message (in the gap between qual and buttons)
        if self.phase == PHASE_ENCOUNTER and self.encounter_effect:
            self.screen.blit(sf.render(f"Encounter: {self.encounter_effect}", True, COLOR_YELLOW),
                            (pa.x + int(12 * self.scale), base_y + int(32 * self.scale)))
        if self.phase == PHASE_ROUND_ADV and self.attach_mc_rect:
            self.screen.blit(sf.render("Round complete. Continue.", True, COLOR_YELLOW),
                            (pa.x + int(12 * self.scale), self.attach_mc_rect.y - int(18 * self.scale)))

        # Buttons
        if self.phase == PHASE_TRIAL:
            if self.roll_rect:
                bc = COLOR_BUTTON_HOVER if self.hovered_button == "roll" else COLOR_BG_TITLE
                pygame.draw.rect(self.screen, bc, self.roll_rect)
                pygame.draw.rect(self.screen, COLOR_CYAN, self.roll_rect, 2)
                self.screen.blit(sf.render("ROLL", True, COLOR_WHITE), sf.render("ROLL", True, COLOR_WHITE).get_rect(center=self.roll_rect.center))

            if self.assistance_rect:
                bc = COLOR_BUTTON_HOVER if self.hovered_button == "assistance" else COLOR_BG_TITLE
                if self.assistance_on:
                    pygame.draw.rect(self.screen, (50, 70, 50), self.assistance_rect)
                else:
                    pygame.draw.rect(self.screen, bc, self.assistance_rect)
                pygame.draw.rect(self.screen, COLOR_CYAN, self.assistance_rect, 2)
                lbl = "Assist ON" if self.assistance_on else "Assist +1"
                self.screen.blit(sf.render(lbl, True, COLOR_WHITE), (self.assistance_rect.x + 4, self.assistance_rect.centery - sf.get_height() // 2))

            if self.use_weapon_rect:
                bc = COLOR_BUTTON_HOVER if self.hovered_button == "use_weapon" else COLOR_BG_TITLE
                can = self.purchased_weapons > 0 and self.mc.ion >= WEAPON_ION_COST
                if self.use_weapon_on:
                    pygame.draw.rect(self.screen, (50, 70, 50), self.use_weapon_rect)
                else:
                    pygame.draw.rect(self.screen, bc, self.use_weapon_rect)
                pygame.draw.rect(self.screen, COLOR_GREEN if can else COLOR_RED, self.use_weapon_rect, 2)
                self.screen.blit(sf.render("Use +2", True, COLOR_WHITE), (self.use_weapon_rect.x + 4, self.use_weapon_rect.centery - sf.get_height() // 2))

            if self.buy_weapon_rect:
                bc = COLOR_BUTTON_HOVER if self.hovered_button == "buy_weapon" else COLOR_BG_TITLE
                can = self.mc.ether >= WEAPON_COST_ETHER and self.purchased_weapons < 2
                pygame.draw.rect(self.screen, bc, self.buy_weapon_rect)
                pygame.draw.rect(self.screen, COLOR_GREEN if can else COLOR_GREY, self.buy_weapon_rect, 2)
                self.screen.blit(sf.render("Buy 2E", True, COLOR_WHITE), (self.buy_weapon_rect.x + 4, self.buy_weapon_rect.centery - sf.get_height() // 2))

        if self.phase in (PHASE_ENCOUNTER, PHASE_ROUND_ADV):
            if self.continue_rect:
                bc = COLOR_BUTTON_HOVER if self.hovered_button == "continue" else COLOR_BG_TITLE
                pygame.draw.rect(self.screen, bc, self.continue_rect)
                pygame.draw.rect(self.screen, COLOR_CYAN, self.continue_rect, 2)
                self.screen.blit(sf.render("CONTINUE", True, COLOR_WHITE), sf.render("CONTINUE", True, COLOR_WHITE).get_rect(center=self.continue_rect.center))

        # Dice (D10) and roll total
        if self.dice_rect and self.last_d10_base is not None and self.last_roll is not None:
            surf = self.d10_surfaces.get(self.last_d10_base)
            if surf:
                self.screen.blit(surf, self.dice_rect.topleft)
            else:
                pygame.draw.rect(self.screen, COLOR_BG_TITLE, self.dice_rect)
                pygame.draw.rect(self.screen, COLOR_CYAN, self.dice_rect, 2)
                t = sf.render(str(self.last_d10_base), True, COLOR_WHITE)
                self.screen.blit(t, t.get_rect(center=self.dice_rect.center))
            tot = sf.render(f"Total: {self.last_roll}", True, COLOR_YELLOW)
            self.screen.blit(tot, (self.dice_rect.right + int(6 * self.scale), self.dice_rect.centery - tot.get_height() // 2))

        if self.phase == PHASE_ATTACH_MODIFIER and self.pending_modifier is not None:
            self.screen.blit(sf.render(f"Attach +{self.pending_modifier} to:", True, COLOR_YELLOW), (self.attach_mc_rect.x, self.attach_mc_rect.y - int(18 * self.scale)))
            if self.attach_mc_rect:
                bc = COLOR_BUTTON_HOVER if self.hovered_button == "attach_mc" else COLOR_BG_TITLE
                pygame.draw.rect(self.screen, bc, self.attach_mc_rect)
                pygame.draw.rect(self.screen, COLOR_CYAN, self.attach_mc_rect, 2)
                self.screen.blit(sf.render("MC", True, COLOR_WHITE), sf.render("MC", True, COLOR_WHITE).get_rect(center=self.attach_mc_rect.center))
            if self.attach_rookie_rect:
                bc = COLOR_BUTTON_HOVER if self.hovered_button == "attach_rookie" else COLOR_BG_TITLE
                pygame.draw.rect(self.screen, bc, self.attach_rookie_rect)
                pygame.draw.rect(self.screen, COLOR_CYAN, self.attach_rookie_rect, 2)
                self.screen.blit(sf.render("Rookie", True, COLOR_WHITE), sf.render("Rookie", True, COLOR_WHITE).get_rect(center=self.attach_rookie_rect.center))

        # Log (in reserved band, from bottom up to avoid overlap)
        log_bottom = pa.bottom - int(8 * self.scale)
        lh = int(14 * self.scale)
        for i, line in enumerate(reversed(self.combat_log[-6:])):
            y = log_bottom - (i + 1) * lh
            if y < self.log_start_y:
                break
            self.screen.blit(sf.render(line, True, COLOR_GREY), (pa.x + int(12 * self.scale), y))

    def _draw_card(self, card: Card, rect: pygame.Rect) -> None:
        key = card.display_string
        surf = self.card_face_surfaces.get(key)
        if surf:
            self.screen.blit(surf, rect.topleft)
            return
        # Vector fallback: clean rect with rank and suit (Solitaire-style)
        bc = (255, 250, 250) if card.suit in ("H", "D") else (248, 248, 255)
        pygame.draw.rect(self.screen, bc, rect)
        pygame.draw.rect(self.screen, COLOR_RED if card.suit in ("H", "D") else COLOR_BLACK, rect, 2)
        if self.small_font:
            suit_char = {"H": "♥", "D": "♦", "C": "♣", "S": "♠"}.get(card.suit, "?")
            txt = self.small_font.render(f"{card.rank}{suit_char}", True, COLOR_RED if card.suit in ("H", "D") else COLOR_BLACK)
            self.screen.blit(txt, txt.get_rect(center=rect.center))

    def _draw_stats_panel(self) -> None:
        sp = self.stats_panel_rect
        bf = self.body_font
        sf = self.small_font
        if not sp or not bf or not sf:
            return

        pygame.draw.rect(self.screen, COLOR_BG_DARK, sp)
        pygame.draw.rect(self.screen, COLOR_DARK_CYAN, sp, 1)
        pygame.draw.line(self.screen, COLOR_CYAN, (sp.x, sp.y), (sp.x, sp.bottom), 2)

        th = int(24 * self.scale)
        tr = pygame.Rect(sp.x, sp.y, sp.width, th)
        pygame.draw.rect(self.screen, COLOR_BG_TITLE, tr)
        pygame.draw.line(self.screen, COLOR_CYAN, (sp.x, tr.bottom), (sp.right, tr.bottom), 1)
        t = bf.render("GAME STATS", True, COLOR_WHITE)
        self.screen.blit(t, (sp.x + (sp.width - t.get_width()) // 2, tr.centery - t.get_height() // 2))

        y = sp.y + th + int(10 * self.scale)
        lh = int(18 * self.scale)
        x = sp.x + int(10 * self.scale)

        def row(lbl: str, val: str, color=COLOR_WHITE) -> None:
            nonlocal y
            self.screen.blit(sf.render(lbl, True, COLOR_CYAN), (x, y))
            self.screen.blit(sf.render(val, True, color), (x + int(70 * self.scale), y))
            y += lh

        row("MC Rep:", str(self.mc.rep))
        row("MC Ion:", str(self.mc.ion))
        row("MC HP:", str(self.mc.hp), COLOR_GREEN if self.mc.hp > 2 else COLOR_RED)
        row("MC Ether:", str(self.mc.ether))
        y += 4
        row("Rookie Rep:", str(self.rookie.rep))
        row("Rookie Ion:", str(self.rookie.ion))
        row("Rookie HP:", str(self.rookie.hp), COLOR_GREEN if self.rookie.hp > 2 else COLOR_RED)
        row("Rookie Ether:", str(self.rookie.ether))
        y += 6
        pygame.draw.line(self.screen, COLOR_DARK_CYAN, (sp.x + 8, y), (sp.right - 8, y), 1)
        y += 8
        row("Weapons:", str(self.purchased_weapons))
        row("MC mods:", "+" + "+".join(map(str, self.modifiers_mc)) if self.modifiers_mc else "0")
        row("Rook mods:", "+" + "+".join(map(str, self.modifiers_rookie)) if self.modifiers_rookie else "0")
        y += 6
        pygame.draw.line(self.screen, COLOR_DARK_CYAN, (sp.x + 8, y), (sp.right - 8, y), 1)
        y += 8
        self.screen.blit(sf.render("FEC", True, COLOR_YELLOW), (x, y))
        y += lh
        if self.phase in (PHASE_TRIAL, PHASE_ATTACH_MODIFIER, PHASE_NEXT_INV, PHASE_ROUND_ADV) or (self.phase == PHASE_SELECT_CARD and self.selected_card):
            self.screen.blit(sf.render(f"Evidence: {self.evidence_remaining}", True, COLOR_WHITE), (x, y))
        else:
            self.screen.blit(sf.render("(face-down)", True, COLOR_GREY), (x, y))
        y += lh

        # How to Play
        y += int(6 * self.scale)
        pygame.draw.line(self.screen, COLOR_DARK_CYAN, (sp.x + 8, y), (sp.right - 8, y), 1)
        y += int(8 * self.scale)
        self.screen.blit(sf.render("HOW TO PLAY", True, COLOR_YELLOW), (x, y))
        y += int(16 * self.scale)
        help_lh = int(14 * self.scale)
        help_lines = [
            "1. Click a card (Witness/Location).",
            "2. Qualified if Rep+Ion >= value.",
            "3. If not: Encounter (penalty).",
            "4. ROLL: D10+mods vs FEC evidence.",
            "5. Assist +1, Weapon 2E, Use +2 (1 Ion).",
            "6. D/H 7-10: attach +1 to +4.",
            "7. Beat 6 FECs = Victory.",
        ]
        for line in help_lines:
            if y + help_lh > sp.bottom - int(55 * self.scale):
                break
            self.screen.blit(sf.render(line, True, COLOR_GREY), (x, y))
            y += help_lh

        # Victory / Defeat
        if self.phase == PHASE_GAME_OVER_VICTORY:
            v = bf.render("VICTORY", True, COLOR_GREEN)
            self.screen.blit(v, (sp.x + (sp.width - v.get_width()) // 2, sp.bottom - int(50 * self.scale)))
        elif self.phase == PHASE_GAME_OVER_DEFEAT:
            v = bf.render("DEFEAT", True, COLOR_RED)
            self.screen.blit(v, (sp.x + (sp.width - v.get_width()) // 2, sp.bottom - int(50 * self.scale)))
