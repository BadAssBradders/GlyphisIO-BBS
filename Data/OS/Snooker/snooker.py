"""
ULTIMATE SNOOKER PRO
Complete snooker simulation with official rules, AI opponent, and 2-player mode.

Rules implemented:
- Alternate red/color during red phase
- Colors respot while reds remain
- Final clearance: colors in order (yellow→green→brown→blue→pink→black)
- Colors don't respot during clearance
- Foul penalties (4 points minimum, or ball value if higher)
- First ball hit tracking for fouls
"""

import pygame
import math
import random
import os
import sys
from typing import List, Tuple, Optional
from enum import Enum

# Data path helper - works for both development and built executable
def get_data_path(*path_parts):
    """
    Returns the path to the Data folder, handling both development and built executable scenarios.
    """
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        base_path = sys._MEIPASS
    else:
        # Running as script - go up from OS/Snooker to Data folder
        script_dir = os.path.dirname(os.path.abspath(__file__))
        os_dir = os.path.dirname(script_dir)  # Go up from Snooker to OS
        data_folder = os.path.dirname(os_dir)  # Go up from OS to Data folder
        base_path = data_folder
    
    return os.path.join(base_path, *path_parts)

# Initialize
pygame.init()

# =============================================================================
# CONSTANTS & CONFIGURATION
# =============================================================================
WINDOW_WIDTH, WINDOW_HEIGHT = 1280, 800
FPS = 60

COLORS = {
    'bg_dark': (12, 15, 18),
    'bg_panel': (20, 25, 30),
    'bg_gradient_top': (15, 40, 35),
    'bg_gradient_bottom': (8, 18, 15),
    'gold': (218, 165, 32),
    'gold_bright': (255, 215, 0),
    'gold_dark': (160, 120, 20),
    'text_primary': (255, 255, 255),
    'text_secondary': (180, 180, 180),
    'text_foul': (255, 80, 80),
    'text_success': (80, 255, 120),
    'table_cloth': (15, 75, 50),
    'table_cloth_mark': (20, 90, 60),
    'wood': (80, 45, 25),
    'wood_light': (100, 60, 35),
    'pocket': (5, 5, 5),
    'pocket_rim': (40, 25, 15),
    'ball_white': (255, 255, 255),
    'ball_red': (200, 25, 25),
    'ball_yellow': (240, 200, 20),
    'ball_green': (0, 110, 45),
    'ball_brown': (120, 70, 35),
    'ball_blue': (25, 80, 180),
    'ball_pink': (255, 140, 170),
    'ball_black': (20, 20, 20),
}

# CGA Color Palette
CGA_COLORS = {
    'black': (0, 0, 0),
    'cyan': (0, 255, 255),
    'magenta': (255, 0, 255),
    'white': (255, 255, 255),
    'cyan_dark': (0, 170, 170),
    'magenta_dark': (170, 0, 170),
    'yellow': (255, 255, 0),
    'green': (0, 255, 0),
    'red': (255, 0, 0),
    'blue': (0, 0, 255),
}

BALL_VALUES = {'red': 1, 'yellow': 2, 'green': 3, 'brown': 4, 'blue': 5, 'pink': 6, 'black': 7}
COLOR_SEQUENCE = ['yellow', 'green', 'brown', 'blue', 'pink', 'black']  # Final clearance order


class GameState(Enum):
    LOADING = -2
    NAME_INPUT = -1
    SPLASH = 0
    RULES = 1
    PLAYING = 2
    GAME_OVER = 3


class GameMode(Enum):
    VS_AI = 0
    TWO_PLAYER = 1
    TOURNAMENT = 2


class TurnPhase(Enum):
    PLACING_CUE = 0
    AIMING = 1
    BALLS_MOVING = 2


# =============================================================================
# BALL CLASS
# =============================================================================

class Ball:
    def __init__(self, x: float, y: float, ball_type: str, radius: float = None, scale: float = 1.0):
        self.x, self.y = x, y
        self.vx, self.vy = 0.0, 0.0
        self.radius = radius if radius is not None else 11 * scale
        self.ball_type = ball_type
        self.potted = False
        self.color = COLORS.get(f'ball_{ball_type}', (255, 255, 255))
        self.value = BALL_VALUES.get(ball_type, 0)

    def update(self, dt: float, friction: float = 0.99895):
        if self.potted:
            return
        speed = math.hypot(self.vx, self.vy)
        
        # Realistic snooker/pool ball physics - 30% less friction (longer movement)
        # Rolling resistance coefficient (μ) for pool balls is 0.005-0.015
        # At 60fps, this translates to ~0.997-0.998 velocity retention per frame
        # Using 0.99895 for 30% less friction (0.105% energy loss per frame instead of 0.15%)
        # Apply more aggressive friction at low speeds to stop balls faster
        
        if speed > 0.05:
            # Apply speed-dependent friction - moderately aggressive at lower speeds
            # 30% less friction across all speed ranges
            if speed < 15:
                # Very slow speeds: apply moderate aggressive friction (30% less than before)
                # Old: 0.87-0.987 (13% to 1.3% energy loss)
                # New: 0.909-0.9909 (9.1% to 0.91% energy loss - 30% reduction)
                # At speed 15: friction ~0.9909, at speed 5: friction ~0.936, at speed 1: friction ~0.909
                speed_factor = speed / 15.0  # Normalize to 0-1 range
                aggressive_friction = 0.909 + (speed_factor * 0.0819)  # Ranges from 0.909 to 0.9909 (30% less friction)
                self.vx *= aggressive_friction
                self.vy *= aggressive_friction
            elif speed < 30:
                # Moderate speeds: slightly more friction (30% less than before)
                # Old: 0.987-0.9985 (1.3% to 0.15% energy loss)
                # New: 0.9909-0.99895 (0.91% to 0.105% energy loss - 30% reduction)
                speed_factor = (speed - 15) / 15.0  # Normalize 15-30 to 0-1
                moderate_friction = 0.9909 + (speed_factor * 0.00805)  # Ranges from 0.9909 to 0.99895 (30% less friction)
                self.vx *= moderate_friction
                self.vy *= moderate_friction
            else:
                # High speeds: standard rolling friction (30% less friction - less energy loss)
                self.vx *= friction
                self.vy *= friction
        else:
            # Stop when speed is very low
            self.vx = self.vy = 0
        
        self.x += self.vx * dt * 60
        self.y += self.vy * dt * 60

    def is_moving(self) -> bool:
        return abs(self.vx) > 0.1 or abs(self.vy) > 0.1

    def draw(self, surface: pygame.Surface):
        if self.potted:
            return
        pos = (int(self.x), int(self.y))
        # Shadow
        pygame.draw.circle(surface, (0, 0, 0), (pos[0] + 3, pos[1] + 3), int(self.radius))
        # Main ball
        pygame.draw.circle(surface, self.color, pos, int(self.radius))
        # Highlight
        highlight_pos = (pos[0] - int(self.radius * 0.3), pos[1] - int(self.radius * 0.3))
        pygame.draw.circle(surface, (255, 255, 255), highlight_pos, max(2, int(self.radius * 0.25)))


# =============================================================================
# AI PLAYER
# =============================================================================

class AIPlayer:
    def __init__(self, skill: float = 0.85):
        self.skill = skill  # 0.0 to 1.0

    def calculate_shot(self, cue: Ball, balls: List[Ball], ball_on: str, pockets: List[Tuple[int, int]]) -> Tuple[float, float]:
        """Calculate best shot angle and power."""
        # Get valid target balls
        if ball_on == "red":
            valid = [b for b in balls if not b.potted and b.ball_type == 'red']
        elif ball_on == "color":
            # Any color is valid
            valid = [b for b in balls if not b.potted and b.ball_type in COLOR_SEQUENCE]
        else:
            # Specific color required (clearance phase)
            valid = [b for b in balls if not b.potted and b.ball_type == ball_on]

        if not valid:
            # Fallback: hit any ball
            valid = [b for b in balls if not b.potted and b.ball_type != 'white']

        if not valid:
            # Scale fallback power to new max of 30
            return random.uniform(0, 2 * math.pi), 30 * (40.0 / 90.0)  # Scale 40 to ~13

        # Evaluate shots to find best option (including combination shots)
        best_shot = None
        best_score = -float('inf')

        # First, evaluate direct shots (cue → target → pocket)
        for target in valid:
            for pocket in pockets:
                shot = self._evaluate_shot(cue, target, pocket)
                if shot and shot['score'] > best_score:
                    best_score = shot['score']
                    best_shot = shot
        
        # Also evaluate combination shots (cue → first ball → second ball → pocket)
        for first_target in valid:
            for second_target in valid:
                if first_target == second_target:
                    continue
                if second_target.potted:
                    continue
                # Check if first target could hit second target
                combination_shot = self._evaluate_combination_shot(cue, first_target, second_target, balls, pockets)
                if combination_shot and combination_shot['score'] > best_score:
                    best_score = combination_shot['score']
                    best_shot = combination_shot

        if best_shot:
            # Apply skill-based error (reduced for excellent players)
            error = (1 - self.skill) * 0.10  # Reduced from 0.15 to 0.10 for better precision
            angle = best_shot['angle'] + random.gauss(0, error)
            # Use absolute minimum power - no variance, just the calculated minimum
            # Scale power to new max of 30 (old max was ~90, so scale by 30/90 = 1/3)
            power = best_shot['power'] * (30.0 / 90.0)  # Scale down to new max of 30
            return angle, max(9, min(30, power))  # New max is 30 (was 90)

        # Fallback: aim at highest value valid ball (more accurate for excellent AI)
        target = max(valid, key=lambda b: b.value)
        angle = math.atan2(target.y - cue.y, target.x - cue.x)
        error = (1 - self.skill) * 0.03  # Very small error for excellent players
        # Calculate absolute minimum power for fallback shot
        distance = math.hypot(target.x - cue.x, target.y - cue.y)
        min_power = (20 + distance / 12) * (30.0 / 90.0)  # Scale to new max of 30
        return angle + random.gauss(0, error), max(9, min(30, min_power))  # New max is 30

    def _evaluate_shot(self, cue: Ball, target: Ball, pocket: Tuple[int, int]) -> Optional[dict]:
        """Evaluate a potential shot using ghost ball method."""
        # Direction from target to pocket
        to_pocket_x = pocket[0] - target.x
        to_pocket_y = pocket[1] - target.y
        to_pocket_dist = math.hypot(to_pocket_x, to_pocket_y)

        if to_pocket_dist < 1:
            return None

        # Normalize
        to_pocket_x /= to_pocket_dist
        to_pocket_y /= to_pocket_dist

        # Ghost ball position
        ghost_x = target.x - to_pocket_x * (target.radius + cue.radius) * 1.05
        ghost_y = target.y - to_pocket_y * (target.radius + cue.radius) * 1.05

        # Angle from cue to ghost
        angle = math.atan2(ghost_y - cue.y, ghost_x - cue.x)
        cue_to_ghost = math.hypot(ghost_x - cue.x, ghost_y - cue.y)

        # Calculate cut angle for difficulty
        cue_to_target = math.atan2(target.y - cue.y, target.x - cue.x)
        target_to_pocket = math.atan2(to_pocket_y, to_pocket_x)
        cut_angle = abs(cue_to_target - target_to_pocket)
        if cut_angle > math.pi:
            cut_angle = 2 * math.pi - cut_angle

        # Score the shot (higher is better)
        score = 100
        score -= cut_angle * 20  # Penalize difficult cuts
        score -= cue_to_ghost / 30  # Penalize long shots
        score -= to_pocket_dist / 50  # Penalize far pockets
        score += target.value * 4  # Strongly prefer high-value balls (increased from 3)
        
        # Bonus for reds when many remain (strategic play)
        if target.ball_type == 'red':
            score += 5
        
        # Prefer shots that leave good position
        score += 3 if cut_angle < 0.3 else 0  # Small bonus for straight shots

        # Power calculation - absolute minimum needed for the shot
        # Calculate minimum power: distance / speed_factor, with minimal base
        # Ball speed = power * 2.0, so power = distance_needed / 2.0 (with safety margin)
        total_distance = cue_to_ghost + to_pocket_dist  # Total distance ball needs to travel
        # Minimum power calculation: base + distance factor (conservative minimum)
        # Using minimal base (20) and distance factor that ensures ball reaches target
        min_power = 20 + total_distance / 12  # Minimum power needed - just enough
        power = min_power

        return {'angle': angle, 'power': power, 'score': score, 'type': 'direct'}
    
    def _evaluate_combination_shot(self, cue: Ball, first_target: Ball, second_target: Ball, 
                                   all_balls: List[Ball], pockets: List[Tuple[int, int]]) -> Optional[dict]:
        """Evaluate a combination shot: cue → first ball → second ball → pocket."""
        # Calculate if first target could hit second target
        # Direction from first target to second target
        to_second_x = second_target.x - first_target.x
        to_second_y = second_target.y - first_target.y
        to_second_dist = math.hypot(to_second_x, to_second_y)
        
        if to_second_dist < 1:
            return None
        
        # Normalize
        to_second_x /= to_second_dist
        to_second_y /= to_second_dist
        
        # Calculate where second target would go after being hit by first target
        # For each pocket, see if the combination shot is possible
        best_combination = None
        best_score = -float('inf')
        
        for pocket in pockets:
            # Direction from second target to pocket
            to_pocket_x = pocket[0] - second_target.x
            to_pocket_y = pocket[1] - second_target.y
            to_pocket_dist = math.hypot(to_pocket_x, to_pocket_y)
            
            if to_pocket_dist < 1:
                continue
            
            # Normalize
            to_pocket_x /= to_pocket_dist
            to_pocket_y /= to_pocket_dist
            
            # Check if second target could reach pocket from first target's impact direction
            # Angle from second target to pocket
            pocket_angle = math.atan2(to_pocket_y, to_pocket_x)
            # Angle from first to second target (direction second target will move)
            impact_angle = math.atan2(to_second_y, to_second_x)
            
            # Calculate angle difference (cut angle for second ball)
            angle_diff = abs(pocket_angle - impact_angle)
            if angle_diff > math.pi:
                angle_diff = 2 * math.pi - angle_diff
            
            # If the angle is reasonable (within 60 degrees), consider the shot
            if angle_diff < math.pi / 3:  # 60 degrees
                # Calculate ghost ball for first target to hit second target
                # First target needs to hit second target in direction that sends it to pocket
                # Reverse engineer: second target needs to go to pocket, so first target hits it that way
                
                # Ghost ball position for second target (where first target should contact it)
                ghost_x = second_target.x - to_pocket_x * (first_target.radius + second_target.radius) * 1.05
                ghost_y = second_target.y - to_pocket_y * (first_target.radius + second_target.radius) * 1.05
                
                # Now calculate ghost ball for cue to hit first target (to send first target to ghost position)
                to_ghost_x = ghost_x - first_target.x
                to_ghost_y = ghost_y - first_target.y
                to_ghost_dist = math.hypot(to_ghost_x, to_ghost_y)
                
                if to_ghost_dist < 1:
                    continue
                
                to_ghost_x /= to_ghost_dist
                to_ghost_y /= to_ghost_dist
                
                # Ghost ball for cue to first target
                cue_ghost_x = first_target.x - to_ghost_x * (cue.radius + first_target.radius) * 1.05
                cue_ghost_y = first_target.y - to_ghost_y * (first_target.radius + cue.radius) * 1.05
                
                # Angle from cue to ghost
                angle = math.atan2(cue_ghost_y - cue.y, cue_ghost_x - cue.x)
                cue_to_ghost = math.hypot(cue_ghost_x - cue.x, cue_ghost_y - cue.y)
                
                # Check if path is clear (cue to first target, first target to second target)
                # Simplified check - make sure balls aren't blocking the path
                path_clear = True
                
                # Check for balls blocking cue → first target
                for ball in all_balls:
                    if ball.potted or ball == cue or ball == first_target:
                        continue
                    # Simple line-ball intersection check
                    dist_to_line = self._point_to_line_distance(ball.x, ball.y, 
                                                               cue.x, cue.y, 
                                                               first_target.x, first_target.y)
                    if dist_to_line < (ball.radius + cue.radius) * 1.2:
                        path_clear = False
                        break
                
                if not path_clear:
                    continue
                
                # Score the combination shot (higher is better)
                combo_score = 100
                combo_score -= angle_diff * 25  # Penalize difficult cuts on second ball
                combo_score -= cue_to_ghost / 25  # Penalize long first shot
                combo_score -= to_second_dist / 40  # Penalize long second shot
                combo_score -= to_pocket_dist / 50  # Penalize far pocket
                combo_score += second_target.value * 6  # Strongly prefer high-value second ball (bonus for combinations)
                
                # Bonus for combination shots (they're impressive!)
                combo_score += 15
                
                # Prefer shots where second ball is closer to pocket
                if to_pocket_dist < 100 * (1.0 if not hasattr(cue, 'scale') else cue.radius / 11):
                    combo_score += 10
                
                if combo_score > best_score:
                    best_score = combo_score
                    # Calculate total power needed
                    total_distance = cue_to_ghost + to_second_dist + to_pocket_dist
                    min_power = 25 + total_distance / 10  # Slightly more power for combination
                    best_combination = {
                        'angle': angle, 
                        'power': min_power, 
                        'score': combo_score,
                        'type': 'combination',
                        'first_target': first_target,
                        'second_target': second_target
                    }
        
        return best_combination
    
    def _point_to_line_distance(self, px: float, py: float, 
                                x1: float, y1: float, x2: float, y2: float) -> float:
        """Calculate distance from a point to a line segment."""
        # Vector from line start to end
        dx = x2 - x1
        dy = y2 - y1
        line_length_sq = dx * dx + dy * dy
        
        if line_length_sq < 0.001:
            # Line is a point, return distance to point
            return math.hypot(px - x1, py - y1)
        
        # Vector from line start to point
        to_point_x = px - x1
        to_point_y = py - y1
        
        # Project point onto line
        t = max(0, min(1, (to_point_x * dx + to_point_y * dy) / line_length_sq))
        
        # Closest point on line
        closest_x = x1 + t * dx
        closest_y = y1 + t * dy
        
        # Return distance from point to closest point on line
        return math.hypot(px - closest_x, py - closest_y)


# =============================================================================
# MAIN GAME CLASS
# =============================================================================

class SnookerGame:
    """
    Snooker game for OS Mode.
    API is similar to SolitaireGame and ChessGame:
    
    - update_desktop(desktop_x, desktop_y, desktop_size, health_monitor_y)
    - start()
    - close()
    - handle_event(event) -> bool
    - draw()
    - update(dt)
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
        get_radio_music_callback = None,
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
        self.running = True
        self.state = GameState.LOADING  # Start with loading screen
        self.mode = GameMode.VS_AI
        
        # Loading screen state
        self.loading_timer = 0
        self.cga_message_timer = 0
        self.cga_message_shown = False
        self.loading_duration = 180  # 3 seconds at 60fps
        self.cga_message_duration = 120  # 2 seconds for CGA+ message
        
        # Player name
        self.player_name = ""  # Player's entered name
        self.name_input_active = False
        self.name_input_text = ""

        # Scaled dimensions
        base_width = 1280
        base_height = 800
        self.game_width = int(base_width * self.scale)
        self.game_height = int(base_height * self.scale)

        # Fonts (scaled) - will be updated when scale changes
        self._update_fonts()
        
        # CGA+ message font (Retro Gaming.ttf, 50% smaller)
        self._load_cga_font()

        # Table geometry (will be recalculated in _update_layout)
        self.table_rect: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self.baulk_x = 0
        self.d_radius = int(70 * self.scale)
        self.d_center_y = 0

        # Pocket positions (relative to table, will be recalculated)
        self.pockets: List[Tuple[int, int]] = []

        # Ball spots (relative to table, will be recalculated)
        self.spots: Dict[str, Tuple[int, int]] = {}

        # Window layout
        self.window_rect: Optional[pygame.Rect] = None
        self.title_bar_rect: Optional[pygame.Rect] = None
        self.exit_button_rect: Optional[pygame.Rect] = None

        # Game objects
        self.balls: List[Ball] = []
        self.cue_ball: Optional[Ball] = None
        self.ai = AIPlayer(skill=0.96)  # Excellent AI player - very skilled
        
        # Tournament AI players
        self.ai_louis = AIPlayer(skill=0.90)  # Mst. Louis Sonic - strong opponent
        self.ai_bradley = AIPlayer(skill=0.98)  # Gen. Bradley Sonic - final boss, extremely skilled
        
        # Tournament state
        self.tournament_active = False
        self.tournament_match = 0  # 0 = vs Louis, 1 = vs Bradley
        self.tournament_won_match_1 = False

        # UI state
        self.animation_tick = 0
        self.btn_ai = pygame.Rect(0, 0, 0, 0)
        self.btn_pvp = pygame.Rect(0, 0, 0, 0)
        self.btn_tournament = pygame.Rect(0, 0, 0, 0)
        self.btn_rules = pygame.Rect(0, 0, 0, 0)
        self.name_continue_btn = pygame.Rect(0, 0, 0, 0)
        self.hovered_button: Optional[str] = None

        # Update layout based on desktop
        self._update_layout()
        self.reset_match()

    def _update_layout(self) -> None:
        """Update the game window layout based on desktop coordinates."""
        # Title bar height
        title_bar_height = int(35 * self.scale)
        
        # Window dimensions - use full desktop size to fit perfectly
        window_width = self.desktop_size[0]
        window_height = self.desktop_size[1]
        
        # Position window at desktop origin to fit perfectly
        window_x = self.desktop_x
        window_y = self.desktop_y
        
        # Full window rect
        self.window_rect = pygame.Rect(window_x, window_y, window_width, window_height)
        
        # Title bar rect
        self.title_bar_rect = pygame.Rect(
            window_x,
            window_y,
            window_width,
            title_bar_height
        )
        
        # Exit button in title bar
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
        
        # Table geometry (scaled and positioned)
        margin = int(20 * self.scale)
        table_x = window_x + margin
        table_y = content_y + int(60 * self.scale)  # Space for UI panel
        table_width = window_width - margin * 2
        table_height = content_height - int(150 * self.scale)  # Space for UI
        
        self.table_rect = pygame.Rect(table_x, table_y, table_width, table_height)
        
        # Baulk line and D
        self.baulk_x = table_x + int(200 * self.scale)
        self.d_center_y = table_y + table_height // 2
        self.d_radius = int(70 * self.scale)
        
        # Pocket positions (relative to window)
        pocket_size = int(24 * self.scale)
        self.pockets = [
            (table_x, table_y),                                    # Top-left
            (table_x + table_width // 2, table_y - int(8 * self.scale)),  # Top-center
            (table_x + table_width, table_y),                     # Top-right
            (table_x, table_y + table_height),                    # Bottom-left
            (table_x + table_width // 2, table_y + table_height + int(8 * self.scale)),  # Bottom-center
            (table_x + table_width, table_y + table_height),      # Bottom-right
        ]
        
        # Ball spots (relative to window)
        self.spots = {
            'yellow': (self.baulk_x, self.d_center_y - self.d_radius),
            'green': (self.baulk_x, self.d_center_y + self.d_radius),
            'brown': (self.baulk_x, self.d_center_y),
            'blue': (table_x + table_width // 2, self.d_center_y),
            'pink': (table_x + int(615 * self.scale), self.d_center_y),
            'black': (table_x + int(910 * self.scale), self.d_center_y),
        }

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
        self._update_layout()
        
        # Update fonts when resolution/scale changes (scale is set by OS_Mode after this call)
        # We'll update fonts in a property setter or check if scale changed
        # For now, update fonts here - scale should be updated by OS_Mode before or after this call
        self._update_fonts()
        
        # Update ball positions if game is active
        if self.active and self.balls:
            self.reset_match()
    
    def _update_fonts(self) -> None:
        """Recreate fonts with current scale factor."""
        self.fonts = {
            'title': pygame.font.SysFont("Georgia", int(72 * self.scale), bold=True),
            'subtitle': pygame.font.SysFont("Georgia", int(36 * self.scale)),
            'large': pygame.font.SysFont("Verdana", int(32 * self.scale), bold=True),
            'medium': pygame.font.SysFont("Verdana", int(24 * self.scale), bold=True),
            'small': pygame.font.SysFont("Verdana", int(18 * self.scale)),
            'tiny': pygame.font.SysFont("Verdana", int(14 * self.scale)),
        }
        # Update CGA font as well
        self._load_cga_font()
    
    def _load_cga_font(self) -> None:
        """Load Retro Gaming.ttf font for CGA+ message at 50% size."""
        try:
            font_path = get_data_path("Retro Gaming.ttf")
            if os.path.exists(font_path):
                # 50% of title font size (72 * 0.5 = 36)
                cga_font_size = int(36 * self.scale)
                self.cga_font = pygame.font.Font(font_path, cga_font_size)
                # Smaller font for second line
                self.cga_font_small = pygame.font.Font(font_path, int(24 * self.scale))
            else:
                # Fallback to system font if Retro Gaming.ttf not found
                self.cga_font = pygame.font.SysFont("Verdana", int(36 * self.scale), bold=True)
                self.cga_font_small = pygame.font.SysFont("Verdana", int(24 * self.scale), bold=True)
        except Exception as e:
            print(f"Warning: Failed to load Retro Gaming.ttf: {e}")
            # Fallback to system font
            self.cga_font = pygame.font.SysFont("Verdana", int(36 * self.scale), bold=True)
            self.cga_font_small = pygame.font.SysFont("Verdana", int(24 * self.scale), bold=True)

    def start(self) -> None:
        """Start the game."""
        self.active = True
        # Always start with loading screen, then transition to name input or splash
        self.state = GameState.LOADING
        self.loading_timer = 0
        self.cga_message_timer = 0
        self.cga_message_shown = False
        if self.player_name:
            # If player already has a name, skip to splash after loading
            pass

    def close(self) -> None:
        """Close the game."""
        self.active = False

    def reset_match(self):
        """Reset for a new match."""
        self.balls.clear()

        # Scaled ball spacing
        ball_spacing = 22 * self.scale

        # Create cue ball
        self.cue_ball = Ball(self.baulk_x - int(50 * self.scale), self.d_center_y, 'white', scale=self.scale)
        self.balls.append(self.cue_ball)

        # Create 15 red balls in triangle
        start_x = self.table_rect.x + int(640 * self.scale)
        start_y = self.d_center_y
        for row in range(5):
            for col in range(row + 1):
                x = start_x + row * ball_spacing * 0.866
                y = start_y + (col - row / 2) * ball_spacing
                self.balls.append(Ball(x, y, 'red', scale=self.scale))

        # Create colored balls on spots
        for ball_type, pos in self.spots.items():
            self.balls.append(Ball(pos[0], pos[1], ball_type, scale=self.scale))

        # Game state
        self.scores = [0, 0]
        self.current_player = 0
        # Use player's entered name, default to "Player" if not set
        player_name = self.player_name if self.player_name else "Player"
        # Set AI name based on mode (will be updated in reset_match if needed)
        if self.mode == GameMode.VS_AI:
            ai_name = "AI Opponent"
        elif self.mode == GameMode.TOURNAMENT:
            if self.tournament_match == 0:
                ai_name = "Mst. Louis Sonic"
            else:
                ai_name = "Gen. Bradley Sonic"
        else:
            ai_name = "Player 2"
        self.player_names = [player_name, ai_name]

        # Snooker-specific state
        self.ball_on = "red"  # What must be potted: "red", "color", or specific color name
        self.in_clearance = False  # True when potting colors in sequence
        self.reds_remaining = 15

        # Turn state
        self.turn_phase = TurnPhase.PLACING_CUE
        self.is_charging = False
        self.cue_power = 0
        self.cue_angle = 0

        # Shot tracking
        self.first_ball_hit: Optional[Ball] = None
        self.potted_this_turn: List[Ball] = []
        self.shot_started = False

        # AI
        self.ai_timer = 0
        self.ai_shot_calculated = False
        self.ai_angle = 0
        self.ai_power = 0
        self.ai_power_charging = 0  # AI's current power while "charging"
        self.ai_preparing = False  # AI is in preparation phase
        # Clean up AI placement timer if it exists
        if hasattr(self, 'ai_placing_cue_timer'):
            del self.ai_placing_cue_timer

        # Messages
        self.message = ""
        self.message_timer = 0
        self.message_color = COLORS['text_primary']

        # Stats
        self.current_break = [0, 0]
        self.highest_break = [0, 0]

        self.show_message("Place the cue ball in the D", 180)

    def show_message(self, msg: str, duration: int = 120, color: Tuple[int, int, int] = None):
        """Display a message."""
        self.message = msg
        self.message_timer = duration
        self.message_color = color or COLORS['text_primary']

    def count_reds(self) -> int:
        """Count remaining reds on table."""
        return sum(1 for b in self.balls if b.ball_type == 'red' and not b.potted)

    def get_next_clearance_color(self) -> Optional[str]:
        """Get the next color to pot in clearance sequence."""
        for color in COLOR_SEQUENCE:
            ball = next((b for b in self.balls if b.ball_type == color and not b.potted), None)
            if ball:
                return color
        return None  # All colors potted

    def resolve_physics(self, dt: float):
        """Handle all physics: movement, collisions, pocketing."""
        # Multiple passes for collision resolution to ensure all collisions are handled
        # This prevents balls from passing through each other
        max_iterations = 5
        
        for iteration in range(max_iterations):
            collision_occurred = False
            
            for i, b1 in enumerate(self.balls):
                if b1.potted:
                    continue

                # Cushion collisions
                if b1.x - b1.radius < self.table_rect.left:
                    b1.x = self.table_rect.left + b1.radius
                    b1.vx = abs(b1.vx) * 0.8
                elif b1.x + b1.radius > self.table_rect.right:
                    b1.x = self.table_rect.right - b1.radius
                    b1.vx = -abs(b1.vx) * 0.8

                if b1.y - b1.radius < self.table_rect.top:
                    b1.y = self.table_rect.top + b1.radius
                    b1.vy = abs(b1.vy) * 0.8
                elif b1.y + b1.radius > self.table_rect.bottom:
                    b1.y = self.table_rect.bottom - b1.radius
                    b1.vy = -abs(b1.vy) * 0.8

                # Ball-to-ball collisions - use sweep test for fast-moving balls
                for b2 in self.balls[i + 1:]:
                    if b2.potted:
                        continue

                    # Continuous collision detection - check if balls will collide this frame
                    # Calculate relative velocity
                    rel_vx = (b1.vx - b2.vx) * dt * 60
                    rel_vy = (b1.vy - b2.vy) * dt * 60
                    
                    # Current positions
                    dx = b2.x - b1.x
                    dy = b2.y - b1.y
                    dist_sq = dx * dx + dy * dy
                    min_dist = b1.radius + b2.radius
                    min_dist_sq = min_dist * min_dist
                    
                    # Check if balls are already overlapping or will overlap
                    if dist_sq < min_dist_sq:
                        dist = math.sqrt(dist_sq) if dist_sq > 0 else min_dist
                        
                        # Record first ball hit by cue ball
                        if b1.ball_type == 'white' and self.first_ball_hit is None:
                            self.first_ball_hit = b2
                        elif b2.ball_type == 'white' and self.first_ball_hit is None:
                            self.first_ball_hit = b1

                        # Collision response - ensure 100% solid balls
                        if dist > 0.001:  # Avoid division by zero
                            nx, ny = dx / dist, dy / dist
                        else:
                            # If balls are exactly on top of each other, use random direction
                            nx, ny = random.uniform(-1, 1), random.uniform(-1, 1)
                            length = math.hypot(nx, ny)
                            if length > 0:
                                nx /= length
                                ny /= length

                        # Calculate overlap - ensure complete separation (100% solid)
                        overlap = min_dist - dist
                        # Add extra margin to ensure balls separate completely
                        separation_margin = 1.0
                        total_overlap = overlap + separation_margin
                        
                        # Separate balls completely - move them apart
                        # Ensure 100% solid balls - move them apart by the full overlap amount
                        separation_amount = total_overlap / 2
                        b1.x -= nx * separation_amount
                        b1.y -= ny * separation_amount
                        b2.x += nx * separation_amount
                        b2.y += ny * separation_amount
                        
                        # Additional safety check: ensure balls are never closer than min_dist
                        new_dx = b2.x - b1.x
                        new_dy = b2.y - b1.y
                        new_dist = math.hypot(new_dx, new_dy)
                        if new_dist < min_dist and new_dist > 0:
                            # Force separation if still too close
                            correction = (min_dist - new_dist) / 2
                            correction_nx = new_dx / new_dist
                            correction_ny = new_dy / new_dist
                            b1.x -= correction_nx * correction
                            b1.y -= correction_ny * correction
                            b2.x += correction_nx * correction
                            b2.y += correction_ny * correction

                        # Velocity exchange - improved energy transfer for more realistic ball movement
                        rel_vx = b1.vx - b2.vx
                        rel_vy = b1.vy - b2.vy
                        v_dot_n = rel_vx * nx + rel_vy * ny

                        if v_dot_n > 0:
                            # Standard elastic collision with full energy preservation
                            # This ensures red balls get proper momentum transfer from white ball
                            energy_preservation = 1.0  # Full elastic collision
                            b1.vx -= v_dot_n * nx * energy_preservation
                            b1.vy -= v_dot_n * ny * energy_preservation
                            b2.vx += v_dot_n * nx * energy_preservation
                            b2.vy += v_dot_n * ny * energy_preservation
                        
                        collision_occurred = True
            
            # If no collisions occurred this iteration, we're done
            if not collision_occurred:
                break
        
        # Final pass: pocket detection (after all collisions resolved)
        for b1 in self.balls:
            if b1.potted:
                continue

            # Pocket detection (scaled pocket size)
            pocket_size = int(24 * self.scale)
            ball_speed = math.hypot(b1.vx, b1.vy)
            # Very high speed threshold - balls going too fast need precise pocketing
            very_high_speed = 100  # Above this speed, require more precise pocketing
            
            for px, py in self.pockets:
                dist_to_pocket_center = math.hypot(b1.x - px, b1.y - py)
                
                # If ball is traveling at very high speed, use tighter detection (ball center must be within pocket)
                if ball_speed > very_high_speed:
                    # High speed: require ball center to be within pocket
                    if dist_to_pocket_center < pocket_size:
                        b1.potted = True
                        b1.vx = b1.vy = 0
                        self.potted_this_turn.append(b1)
                        break
                else:
                    # Normal/medium speed: if ANY part of ball touches pocket, it goes in
                    # Check if distance from pocket center to ball center is less than (pocket_size + ball_radius)
                    effective_pocket_radius = pocket_size + b1.radius
                    if dist_to_pocket_center < effective_pocket_radius:
                        b1.potted = True
                        b1.vx = b1.vy = 0
                        self.potted_this_turn.append(b1)
                        break

    def respot_ball(self, ball: Ball):
        """Return a colored ball to its spot."""
        if ball.ball_type not in self.spots:
            return

        spot = self.spots[ball.ball_type]
        ball.x, ball.y = spot
        ball.vx = ball.vy = 0
        ball.potted = False

        # Check if spot is occupied and find alternative
        for other in self.balls:
            if other != ball and not other.potted:
                if math.hypot(other.x - ball.x, other.y - ball.y) < ball.radius + other.radius:
                    # Move towards black spot, then towards pink, etc.
                    ball.x += ball.radius * 2.5

    def evaluate_turn(self):
        """Evaluate the completed shot and determine next state."""
        foul = False
        foul_value = 4  # Minimum foul penalty
        points_scored = 0

        # Count reds for state tracking
        self.reds_remaining = self.count_reds()

        # === Check for cue ball potted ===
        if self.cue_ball.potted:
            foul = True
            self.cue_ball.potted = False
            self.turn_phase = TurnPhase.PLACING_CUE
            self.show_message("FOUL! Cue ball potted - place in the D", 180, COLORS['text_foul'])

        # === Check first ball hit ===
        if not foul and self.first_ball_hit:
            hit_type = self.first_ball_hit.ball_type

            if self.ball_on == "red":
                if hit_type != "red":
                    foul = True
                    foul_value = max(4, self.first_ball_hit.value)
                    self.show_message(f"FOUL! Hit {hit_type} instead of red", 150, COLORS['text_foul'])
            elif self.ball_on == "color":
                if hit_type == "red":
                    foul = True
                    self.show_message("FOUL! Hit red instead of color", 150, COLORS['text_foul'])
            else:
                # Specific color required (clearance)
                if hit_type != self.ball_on:
                    foul = True
                    foul_value = max(4, BALL_VALUES.get(hit_type, 4), BALL_VALUES.get(self.ball_on, 4))
                    self.show_message(f"FOUL! Hit {hit_type} instead of {self.ball_on}", 150, COLORS['text_foul'])

        elif not foul and self.first_ball_hit is None:
            # Missed all balls
            foul = True
            if self.ball_on in BALL_VALUES:
                foul_value = max(4, BALL_VALUES[self.ball_on])
            self.show_message("FOUL! No ball hit", 150, COLORS['text_foul'])

        # === Process potted balls ===
        potted_objects = [b for b in self.potted_this_turn if b.ball_type != 'white']
        legal_pot = False

        if not foul and potted_objects:
            if self.ball_on == "red":
                # Must pot only reds
                reds_potted = [b for b in potted_objects if b.ball_type == 'red']
                others_potted = [b for b in potted_objects if b.ball_type != 'red']

                if others_potted:
                    foul = True
                    foul_value = max(4, max(b.value for b in others_potted))
                    self.show_message("FOUL! Potted wrong ball", 150, COLORS['text_foul'])
                    # Respot any colors potted
                    for b in others_potted:
                        self.respot_ball(b)
                elif reds_potted:
                    points_scored = len(reds_potted)
                    legal_pot = True
                    self.ball_on = "color"
                    self.show_message(f"+{points_scored}! Now pot a color", 120, COLORS['text_success'])

            elif self.ball_on == "color":
                # Must pot exactly one color (any color allowed)
                colors_potted = [b for b in potted_objects if b.ball_type in COLOR_SEQUENCE]
                reds_potted = [b for b in potted_objects if b.ball_type == 'red']

                if reds_potted:
                    foul = True
                    self.show_message("FOUL! Potted red when on color", 150, COLORS['text_foul'])
                elif len(colors_potted) > 1:
                    foul = True
                    foul_value = max(b.value for b in colors_potted)
                    self.show_message("FOUL! Potted multiple colors", 150, COLORS['text_foul'])
                    for b in colors_potted:
                        self.respot_ball(b)
                elif len(colors_potted) == 1:
                    color_ball = colors_potted[0]
                    points_scored = color_ball.value
                    legal_pot = True

                    # Respot the color if reds remain
                    if self.reds_remaining > 0:
                        self.respot_ball(color_ball)
                        self.ball_on = "red"
                        self.show_message(f"+{points_scored}! Now pot a red", 120, COLORS['text_success'])
                    else:
                        # Enter clearance or continue it
                        self.in_clearance = True
                        next_color = self.get_next_clearance_color()
                        if next_color:
                            self.ball_on = next_color
                            self.show_message(f"+{points_scored}! Now pot {next_color}", 120, COLORS['text_success'])
                        else:
                            self.ball_on = "done"

            else:
                # Clearance: must pot specific color
                target_ball = next((b for b in potted_objects if b.ball_type == self.ball_on), None)
                wrong_balls = [b for b in potted_objects if b.ball_type != self.ball_on]

                if wrong_balls:
                    foul = True
                    foul_value = max(4, BALL_VALUES.get(self.ball_on, 4), max(b.value for b in wrong_balls))
                    self.show_message(f"FOUL! Wrong ball potted", 150, COLORS['text_foul'])
                    for b in wrong_balls:
                        if b.ball_type in COLOR_SEQUENCE:
                            self.respot_ball(b)
                elif target_ball:
                    points_scored = target_ball.value
                    legal_pot = True
                    # Don't respot - it stays potted
                    next_color = self.get_next_clearance_color()
                    if next_color:
                        self.ball_on = next_color
                        self.show_message(f"+{points_scored}! Now pot {next_color}", 120, COLORS['text_success'])
                    else:
                        self.ball_on = "done"
                        self.show_message(f"+{points_scored}! All balls potted!", 180, COLORS['text_success'])

        # === Apply results ===
        if foul:
            # Award foul points to opponent
            opponent = 1 - self.current_player
            self.scores[opponent] += foul_value

            # Reset break
            self.current_break[self.current_player] = 0

            # Switch player
            self.current_player = opponent

            # Reset ball_on state
            if self.reds_remaining > 0:
                self.ball_on = "red"
                self.in_clearance = False
            else:
                self.in_clearance = True
                next_color = self.get_next_clearance_color()
                self.ball_on = next_color if next_color else "done"

        elif legal_pot:
            # Award points
            self.scores[self.current_player] += points_scored
            self.current_break[self.current_player] += points_scored
            self.highest_break[self.current_player] = max(
                self.highest_break[self.current_player],
                self.current_break[self.current_player]
            )
            # Player continues

        else:
            # No pot, no foul - switch player
            self.current_break[self.current_player] = 0
            self.current_player = 1 - self.current_player

            if self.reds_remaining > 0:
                self.ball_on = "red"
            else:
                self.in_clearance = True
                next_color = self.get_next_clearance_color()
                self.ball_on = next_color if next_color else "done"

            self.show_message(f"{self.player_names[self.current_player]}'s turn", 90)

        # === Check for game over ===
        if self.ball_on == "done":
            self.state = GameState.GAME_OVER
            # Tournament progression handled in handle_event when clicking after game over
            return

        # === Reset for next shot ===
        self.potted_this_turn.clear()
        self.first_ball_hit = None
        self.shot_started = False

        # Setup AI if needed
        if (self.mode == GameMode.VS_AI or self.mode == GameMode.TOURNAMENT) and self.current_player == 1:
            # Much slower AI - gives time to show preparation (180-300 frames = 3-5 seconds at 60fps)
            self.ai_timer = random.randint(180, 300)
            self.ai_shot_calculated = False
            self.ai_preparing = True
            self.ai_power_charging = 0

        if self.turn_phase != TurnPhase.PLACING_CUE:
            self.turn_phase = TurnPhase.AIMING

    def get_ball_on_color(self) -> Tuple[int, int, int]:
        """Get color for current ball-on indicator."""
        if self.ball_on == "red":
            return COLORS['ball_red']
        elif self.ball_on == "color":
            return COLORS['gold_bright']
        elif self.ball_on in COLORS:
            return COLORS[f'ball_{self.ball_on}']
        return COLORS['text_primary']

    # =========================================================================
    # DRAWING METHODS
    # =========================================================================

    def _draw_window_frame(self):
        """Draw the window frame and title bar."""
        if not self.window_rect:
            return

        # Window background
        pygame.draw.rect(self.screen, COLORS['bg_dark'], self.window_rect)

        # Title bar
        if self.title_bar_rect:
            pygame.draw.rect(self.screen, COLORS['bg_panel'], self.title_bar_rect)
            pygame.draw.line(self.screen, COLORS['gold_dark'],
                           (self.title_bar_rect.left, self.title_bar_rect.bottom),
                           (self.title_bar_rect.right, self.title_bar_rect.bottom), 2)

            # Title text
            title_text = "ULTIMATE SNOOKER PRO"
            title_surf = self.fonts['medium'].render(title_text, True, COLORS['gold'])
            title_x = self.title_bar_rect.x + int(15 * self.scale)
            title_y = self.title_bar_rect.centery - title_surf.get_height() // 2
            self.screen.blit(title_surf, (title_x, title_y))

            # Exit button
            if self.exit_button_rect:
                hover = self.exit_button_rect.collidepoint(pygame.mouse.get_pos())
                btn_color = COLORS['text_foul'] if hover else COLORS['text_secondary']
                pygame.draw.rect(self.screen, COLORS['bg_panel'], self.exit_button_rect, border_radius=5)
                pygame.draw.rect(self.screen, btn_color, self.exit_button_rect, 2, border_radius=5)
                exit_text = self.fonts['small'].render("X", True, btn_color)
                self.screen.blit(exit_text, exit_text.get_rect(center=self.exit_button_rect.center))

    def _window_relative_pos(self, x: float, y: float) -> Tuple[int, int]:
        """Convert window-relative coordinates to screen coordinates."""
        if not self.window_rect:
            return (int(x), int(y))
        # Content area starts below title bar
        title_bar_height = int(35 * self.scale)
        return (int(self.window_rect.x + x), int(self.window_rect.y + title_bar_height + y))

    def draw_loading(self):
        """Draw the CGA-style loading screen with CGA+ detection message."""
        if not self.window_rect:
            return
        
        # Fill entire window with CGA black background
        pygame.draw.rect(self.screen, CGA_COLORS['black'], self.window_rect)
        
        # Draw CGA-style border pattern
        border_width = int(4 * self.scale)
        # Top border - cyan
        pygame.draw.rect(self.screen, CGA_COLORS['cyan'], 
                        (self.window_rect.x, self.window_rect.y, 
                         self.window_rect.width, border_width))
        # Bottom border - magenta
        pygame.draw.rect(self.screen, CGA_COLORS['magenta'], 
                        (self.window_rect.x, self.window_rect.bottom - border_width, 
                         self.window_rect.width, border_width))
        # Left border - cyan
        pygame.draw.rect(self.screen, CGA_COLORS['cyan'], 
                        (self.window_rect.x, self.window_rect.y, 
                         border_width, self.window_rect.height))
        # Right border - magenta
        pygame.draw.rect(self.screen, CGA_COLORS['magenta'], 
                        (self.window_rect.right - border_width, self.window_rect.y, 
                         border_width, self.window_rect.height))
        
        center_x = self.window_rect.centerx
        center_y = self.window_rect.centery
        
        # Show loading text initially
        if not self.cga_message_shown:
            loading_text = "LOADING..."
            loading_surf = self.fonts['large'].render(loading_text, True, CGA_COLORS['cyan'])
            self.screen.blit(loading_surf, loading_surf.get_rect(center=(center_x, center_y - int(50 * self.scale))))
        
        # Flash CGA+ detection message (50% smaller, using Retro Gaming.ttf)
        if self.cga_message_shown:
            # Flash effect - alternate between white and cyan/magenta
            flash_cycle = (self.cga_message_timer // 10) % 4
            if flash_cycle < 2:
                # Show message in white (bright flash)
                message_color = CGA_COLORS['white']
            else:
                # Show message in cyan (dim flash)
                message_color = CGA_COLORS['cyan']
            
            cga_message = "CGA+ MONITOR DETECTED"
            switch_message = "SWITCHING TO CGA+"
            
            # Render messages using Retro Gaming font (50% smaller - 36 instead of 72)
            msg1_surf = self.cga_font.render(cga_message, True, message_color)
            msg2_surf = self.cga_font_small.render(switch_message, True, message_color)
            
            # Draw with glow effect for flash
            for offset in range(3, 0, -1):
                glow_color = tuple(max(0, min(255, c - offset * 20)) for c in message_color)
                glow1 = self.cga_font.render(cga_message, True, glow_color)
                glow2 = self.cga_font_small.render(switch_message, True, glow_color)
                self.screen.blit(glow1, glow1.get_rect(center=(center_x + offset, center_y - int(30 * self.scale) + offset)))
                self.screen.blit(glow2, glow2.get_rect(center=(center_x + offset, center_y + int(30 * self.scale) + offset)))
            
            self.screen.blit(msg1_surf, msg1_surf.get_rect(center=(center_x, center_y - int(30 * self.scale))))
            self.screen.blit(msg2_surf, msg2_surf.get_rect(center=(center_x, center_y + int(30 * self.scale))))
        
        # Draw CGA-style scanlines effect (subtle dark lines)
        scanline_spacing = int(4 * self.scale)
        for y in range(self.window_rect.y, self.window_rect.bottom, scanline_spacing * 2):
            pygame.draw.line(self.screen, (0, 0, 0), 
                           (self.window_rect.x, y), 
                           (self.window_rect.right, y), 1)

    def draw_name_input(self):
        """Draw the name input modal."""
        self._draw_window_frame()
        
        if not self.window_rect:
            return
        
        content_rect = pygame.Rect(
            self.window_rect.x,
            self.window_rect.y + int(35 * self.scale),
            self.window_rect.width,
            self.window_rect.height - int(35 * self.scale)
        )
        
        # Gradient background
        for y_offset in range(content_rect.height):
            t = y_offset / content_rect.height
            r = int(COLORS['bg_gradient_top'][0] * (1 - t) + COLORS['bg_gradient_bottom'][0] * t)
            g = int(COLORS['bg_gradient_top'][1] * (1 - t) + COLORS['bg_gradient_bottom'][1] * t)
            b = int(COLORS['bg_gradient_top'][2] * (1 - t) + COLORS['bg_gradient_bottom'][2] * t)
            pygame.draw.line(self.screen, (r, g, b),
                           (content_rect.x, content_rect.y + y_offset),
                           (content_rect.right, content_rect.y + y_offset))
        
        center_x = content_rect.centerx
        base_y = content_rect.y + content_rect.height // 2 - int(100 * self.scale)
        
        # Title
        title = self.fonts['large'].render("ENTER YOUR NAME", True, COLORS['gold'])
        self.screen.blit(title, title.get_rect(center=(center_x, base_y)))
        
        # Input box
        input_width = int(400 * self.scale)
        input_height = int(50 * self.scale)
        input_x = center_x - input_width // 2
        input_y = base_y + int(60 * self.scale)
        input_rect = pygame.Rect(input_x, input_y, input_width, input_height)
        
        # Draw input box
        pygame.draw.rect(self.screen, COLORS['bg_panel'], input_rect, border_radius=int(8 * self.scale))
        pygame.draw.rect(self.screen, COLORS['gold_bright'] if self.name_input_active else COLORS['gold'], 
                        input_rect, 3, border_radius=int(8 * self.scale))
        
        # Draw input text
        display_text = self.name_input_text if self.name_input_text else "Type your name..."
        text_color = COLORS['text_primary'] if self.name_input_text else COLORS['text_secondary']
        input_surf = self.fonts['medium'].render(display_text, True, text_color)
        text_x = input_rect.x + int(15 * self.scale)
        text_y = input_rect.centery - input_surf.get_height() // 2
        # Clip text to input box
        max_width = input_width - int(30 * self.scale)
        final_text = display_text
        if input_surf.get_width() > max_width:
            # Truncate text
            truncated = display_text
            while self.fonts['medium'].render(truncated, True, text_color).get_width() > max_width and len(truncated) > 0:
                truncated = truncated[:-1]
            final_text = truncated
            input_surf = self.fonts['medium'].render(truncated, True, text_color)
        self.screen.blit(input_surf, (text_x, text_y))
        
        # Cursor (blinking) - use actual text width
        if self.name_input_active:
            # Get full text width for cursor positioning (not truncated)
            full_text_width = self.fonts['medium'].render(self.name_input_text if self.name_input_text else "", True, text_color).get_width()
            cursor_x = text_x + min(full_text_width, max_width)
            cursor_height = input_surf.get_height()
            # Blink cursor every 30 frames
            if (self.animation_tick // 30) % 2 == 0:
                pygame.draw.line(self.screen, COLORS['text_primary'],
                               (cursor_x, text_y), (cursor_x, text_y + cursor_height), int(2 * self.scale))
        
        # Continue button
        btn_width = int(200 * self.scale)
        btn_height = int(45 * self.scale)
        btn_x = center_x - btn_width // 2
        btn_y = input_y + input_height + int(40 * self.scale)
        btn_rect = pygame.Rect(btn_x, btn_y, btn_width, btn_height)
        
        mouse_pos = pygame.mouse.get_pos()
        hover = btn_rect.collidepoint(mouse_pos)
        btn_enabled = len(self.name_input_text.strip()) > 0
        btn_color = COLORS['gold_bright'] if (hover and btn_enabled) else (COLORS['gold'] if btn_enabled else COLORS['text_secondary'])
        bg_color = (35, 50, 45) if (hover and btn_enabled) else COLORS['bg_panel']
        
        pygame.draw.rect(self.screen, bg_color, btn_rect, border_radius=int(8 * self.scale))
        pygame.draw.rect(self.screen, btn_color, btn_rect, 3, border_radius=int(8 * self.scale))
        
        btn_text = self.fonts['medium'].render("CONTINUE", True, btn_color)
        self.screen.blit(btn_text, btn_text.get_rect(center=btn_rect.center))
        
        self.name_continue_btn = btn_rect

    def draw_splash(self):
        """Draw the splash/menu screen."""
        self._draw_window_frame()
        
        if not self.window_rect:
            return
        
        content_rect = pygame.Rect(
            self.window_rect.x,
            self.window_rect.y + int(35 * self.scale),  # Below title bar
            self.window_rect.width,
            self.window_rect.height - int(35 * self.scale)
        )
        
        # Gradient background in content area
        for y_offset in range(content_rect.height):
            t = y_offset / content_rect.height
            r = int(COLORS['bg_gradient_top'][0] * (1 - t) + COLORS['bg_gradient_bottom'][0] * t)
            g = int(COLORS['bg_gradient_top'][1] * (1 - t) + COLORS['bg_gradient_bottom'][1] * t)
            b = int(COLORS['bg_gradient_top'][2] * (1 - t) + COLORS['bg_gradient_bottom'][2] * t)
            pygame.draw.line(self.screen, (r, g, b),
                           (content_rect.x, content_rect.y + y_offset),
                           (content_rect.right, content_rect.y + y_offset))

        self.animation_tick += 1

        # Content area coordinates
        content_w = content_rect.width
        content_h = content_rect.height
        center_x = content_rect.x + content_w // 2
        base_y = content_rect.y
        
        # Move text up by 10% of content height (but not buttons)
        text_offset = int(content_h * 0.1)

        # Decorative floating balls (scaled and positioned relative to content)
        ball_deco = [
            (int(100 * self.scale), int(150 * self.scale), 'red'),
            (int(200 * self.scale), int(100 * self.scale), 'yellow'),
            (content_w - int(100 * self.scale), int(200 * self.scale), 'blue'),
            (content_w - int(180 * self.scale), int(100 * self.scale), 'pink'),
            (int(150 * self.scale), content_h - int(150 * self.scale), 'green'),
            (content_w - int(130 * self.scale), content_h - int(130 * self.scale), 'black')
        ]
        ball_size = int(28 * self.scale)
        for x_rel, y_rel, c in ball_deco:
            x = content_rect.x + x_rel
            y = base_y + y_rel
            offset = math.sin(self.animation_tick * 0.025 + x * 0.01) * (12 * self.scale)
            pygame.draw.circle(self.screen, COLORS[f'ball_{c}'], (x, int(y + offset)), ball_size)
            pygame.draw.circle(self.screen, (255, 255, 255), (x - int(8 * self.scale), int(y + offset - 8 * self.scale)), int(6 * self.scale))

        # Title - moved up 10%
        title = self.fonts['title'].render("ULTIMATE SNOOKER", True, COLORS['gold'])
        title_y = base_y + int(180 * self.scale) - text_offset
        title_rect = title.get_rect(center=(center_x, title_y))
        # Glow effect
        for i in range(3, 0, -1):
            glow = self.fonts['title'].render("ULTIMATE SNOOKER", True, (50 + i * 20, 40 + i * 10, 0))
            self.screen.blit(glow, glow.get_rect(center=(center_x + i, title_y + i)))
        self.screen.blit(title, title_rect)

        # Subtitle - moved up 10%
        sub = self.fonts['subtitle'].render("Championship Edition", True, COLORS['text_secondary'])
        self.screen.blit(sub, sub.get_rect(center=(center_x, base_y + int(240 * self.scale) - text_offset)))

        # Intro message - moved up 10%
        intro_text = "OPTIMIZED FOR CGA+ FULL COLOUR AND SPRITE DISTRIBUTION"
        intro_surf = self.fonts['small'].render(intro_text, True, COLORS['gold_bright'])
        self.screen.blit(intro_surf, intro_surf.get_rect(center=(center_x, base_y + int(280 * self.scale) - text_offset)))

        # Decorative line - moved up 10%
        line_y = base_y + int(310 * self.scale) - text_offset
        pygame.draw.line(self.screen, COLORS['gold_dark'],
                         (center_x - int(180 * self.scale), line_y),
                         (center_x + int(180 * self.scale), line_y), 2)

        # Footer text under the line - moved up 10%
        footer = self.fonts['tiny'].render("Mouse to aim • Hold click for power • ESC for menu", True, COLORS['text_secondary'])
        self.screen.blit(footer, footer.get_rect(center=(center_x, line_y + int(30 * self.scale))))

        # Buttons (absolute screen coordinates) - widened by 10%
        btn_width = int(320 * self.scale * 1.1)  # 10% wider
        btn_height = int(55 * self.scale)
        # Move buttons up by 10% of content height
        btn_y_base = base_y + int(400 * self.scale) - int(content_h * 0.1)
        btn_spacing = int(70 * self.scale)
        self.btn_ai = pygame.Rect(center_x - btn_width // 2, btn_y_base, btn_width, btn_height)
        self.btn_pvp = pygame.Rect(center_x - btn_width // 2, btn_y_base + btn_spacing, btn_width, btn_height)
        self.btn_tournament = pygame.Rect(center_x - btn_width // 2, btn_y_base + btn_spacing * 2, btn_width, btn_height)
        self.btn_rules = pygame.Rect(center_x - btn_width // 2, btn_y_base + btn_spacing * 3, btn_width, btn_height)

        mouse_pos = pygame.mouse.get_pos()
        for btn, text in [(self.btn_ai, "VS COMPUTER"), (self.btn_pvp, "2 PLAYERS"), (self.btn_tournament, "LIVE AT THE CRUCIBLE"), (self.btn_rules, "RULES")]:
            hover = btn.collidepoint(mouse_pos)
            bg_color = (35, 50, 45) if hover else COLORS['bg_panel']
            border_color = COLORS['gold_bright'] if hover else COLORS['gold']

            pygame.draw.rect(self.screen, bg_color, btn, border_radius=int(10 * self.scale))
            pygame.draw.rect(self.screen, border_color, btn, 3, border_radius=int(10 * self.scale))

            txt = self.fonts['medium'].render(text, True, border_color)
            self.screen.blit(txt, txt.get_rect(center=btn.center))

    def draw_rules(self):
        """Draw the rules screen."""
        self._draw_window_frame()
        if not self.window_rect:
            return
        
        content_rect = pygame.Rect(
            self.window_rect.x,
            self.window_rect.y + int(35 * self.scale),
            self.window_rect.width,
            self.window_rect.height - int(35 * self.scale)
        )
        
        # Background
        pygame.draw.rect(self.screen, COLORS['bg_dark'], content_rect)

        title = self.fonts['large'].render("SNOOKER RULES & SCORING", True, COLORS['gold'])
        self.screen.blit(title, title.get_rect(center=(content_rect.centerx, content_rect.y + int(50 * self.scale))))

        pygame.draw.line(self.screen, COLORS['gold_dark'],
                         (content_rect.x + int(100 * self.scale), content_rect.y + int(85 * self.scale)),
                         (content_rect.right - int(100 * self.scale), content_rect.y + int(85 * self.scale)), 2)

        rules = [
            ("OBJECTIVE", COLORS['gold']),
            ("Score more points than your opponent by potting balls in the correct sequence.", COLORS['text_secondary']),
            ("", None),
            ("BALL VALUES", COLORS['gold']),
            ("Red = 1  |  Yellow = 2  |  Green = 3  |  Brown = 4  |  Blue = 5  |  Pink = 6  |  Black = 7", COLORS['text_primary']),
            ("", None),
            ("GAMEPLAY", COLORS['gold']),
            ("1. Pot a RED (1 point), then pot any COLOR (2-7 points).", COLORS['text_secondary']),
            ("2. Colors are re-spotted while reds remain on the table.", COLORS['text_secondary']),
            ("3. Continue alternating red/color until all 15 reds are potted.", COLORS['text_secondary']),
            ("4. After the last red's color, pot colors IN ORDER: Yellow → Green → Brown → Blue → Pink → Black", COLORS['text_secondary']),
            ("5. During clearance, colors stay potted (not re-spotted).", COLORS['text_secondary']),
            ("", None),
            ("FOULS (4+ points to opponent)", COLORS['text_foul']),
            ("• Potting the cue ball  • Hitting wrong ball first  • Potting wrong ball  • Missing all balls", COLORS['text_secondary']),
            ("", None),
            ("CONTROLS", COLORS['gold']),
            ("Mouse = Aim  |  Hold Left Click = Power  |  Release = Shoot  |  ESC = Menu", COLORS['text_primary']),
        ]

        y = content_rect.y + int(120 * self.scale)
        for text, color in rules:
            if color:
                surf = self.fonts['small'].render(text, True, color)
                self.screen.blit(surf, (content_rect.x + int(120 * self.scale), y))
            y += int(32 * self.scale)

        prompt = self.fonts['medium'].render("Click or press any key to return", True, COLORS['gold'])
        self.screen.blit(prompt, prompt.get_rect(center=(content_rect.centerx, content_rect.bottom - int(60 * self.scale))))

    def draw_table(self):
        """Draw the snooker table."""
        # Wood frame (scaled)
        frame_inflate = int(40 * self.scale)
        frame = self.table_rect.inflate(frame_inflate, frame_inflate)
        border_radius = int(12 * self.scale)
        pygame.draw.rect(self.screen, COLORS['wood'], frame, border_radius=border_radius)
        pygame.draw.rect(self.screen, COLORS['wood_light'], frame, 4, border_radius=border_radius)

        # Cloth
        pygame.draw.rect(self.screen, COLORS['table_cloth'], self.table_rect)

        # Baulk line (scaled)
        line_margin = int(5 * self.scale)
        pygame.draw.line(self.screen, COLORS['table_cloth_mark'],
                         (self.baulk_x, self.table_rect.top + line_margin),
                         (self.baulk_x, self.table_rect.bottom - line_margin), 2)

        # D arc (scaled)
        d_rect = pygame.Rect(self.baulk_x - self.d_radius, self.d_center_y - self.d_radius,
                             self.d_radius * 2, self.d_radius * 2)
        pygame.draw.arc(self.screen, COLORS['table_cloth_mark'], d_rect, math.pi / 2, 3 * math.pi / 2, 2)

        # Spots (scaled)
        spot_size = int(3 * self.scale)
        for pos in self.spots.values():
            pygame.draw.circle(self.screen, COLORS['table_cloth_mark'], (int(pos[0]), int(pos[1])), spot_size)

        # Pockets (scaled)
        pocket_rim_size = int(28 * self.scale)
        pocket_size = int(24 * self.scale)
        for px, py in self.pockets:
            pygame.draw.circle(self.screen, COLORS['pocket_rim'], (px, py), pocket_rim_size)
            pygame.draw.circle(self.screen, COLORS['pocket'], (px, py), pocket_size)

    def draw_aiming_line(self):
        """Draw the aiming guide line with enhanced geometry visualization: cue → first ball → second ball."""
        if not self.cue_ball or self.cue_ball.potted:
            return

        mx, my = pygame.mouse.get_pos()
        angle = math.atan2(my - self.cue_ball.y, mx - self.cue_ball.x)

        # Draw dotted line and check for ball intersections
        hit_ball = None
        hit_point = None
        for i in range(1, 80):  # Extended range to find intersections
            t = i / 80
            x = self.cue_ball.x + math.cos(angle) * ((30 + i * 12) * self.scale)
            y = self.cue_ball.y + math.sin(angle) * ((30 + i * 12) * self.scale)

            if not self.table_rect.collidepoint(x, y):
                break

            # Check if this point hits a ball
            if not hit_ball:
                for ball in self.balls:
                    if ball.potted or ball.ball_type == 'white':
                        continue
                    dist = math.hypot(x - ball.x, y - ball.y)
                    if dist < ball.radius + self.cue_ball.radius:
                        hit_ball = ball
                        hit_point = (x, y)
                        break
            
            if i <= 25:  # Only draw first part of line
                alpha = int(180 * (1 - t * 0.7))
                pygame.draw.circle(self.screen, (alpha, alpha, alpha), (int(x), int(y)), int(2 * self.scale))
        
        # Enhanced geometry visualization: cue → first ball → second ball
        if hit_ball and hit_point:
            # Draw solid line from cue ball to first ball hit (cyan)
            pygame.draw.line(self.screen, COLORS['gold_bright'], 
                           (int(self.cue_ball.x), int(self.cue_ball.y)),
                           (int(hit_ball.x), int(hit_ball.y)), 3)
            
            # Calculate the direction the first ball will travel (using ghost ball method)
            # Direction from cue to hit ball
            cue_to_ball_dx = hit_ball.x - self.cue_ball.x
            cue_to_ball_dy = hit_ball.y - self.cue_ball.y
            cue_to_ball_dist = math.hypot(cue_to_ball_dx, cue_to_ball_dy)
            
            if cue_to_ball_dist > 0:
                # Normalize
                cue_to_ball_nx = cue_to_ball_dx / cue_to_ball_dist
                cue_to_ball_ny = cue_to_ball_dy / cue_to_ball_dist
                
                # The first ball will move approximately in the direction of impact
                # Calculate where the hit ball will go (in direction of collision)
                first_ball_angle = math.atan2(cue_to_ball_ny, cue_to_ball_nx)
                
                # Draw trajectory from first ball showing where it will go (yellow/cyan)
                trajectory_length = 300 * self.scale
                end_x = hit_ball.x + math.cos(first_ball_angle) * trajectory_length
                end_y = hit_ball.y + math.sin(first_ball_angle) * trajectory_length
                
                # Draw first ball trajectory (cyan dashed line)
                for j in range(0, 30):
                    t = j / 30
                    tx = hit_ball.x + math.cos(first_ball_angle) * (trajectory_length * t)
                    ty = hit_ball.y + math.sin(first_ball_angle) * (trajectory_length * t)
                    if self.table_rect.collidepoint(tx, ty):
                        alpha = int(150 * (1 - t * 0.3))
                        if j % 3 == 0:  # Dashed effect
                            pygame.draw.circle(self.screen, (alpha, 255, 255), (int(tx), int(ty)), int(3 * self.scale))
                
                # Check for potential second ball hits along first ball's trajectory
                second_ball_hits = []
                for second_ball in self.balls:
                    if second_ball.potted or second_ball == hit_ball or second_ball.ball_type == 'white':
                        continue
                    
                    # Check if second ball is in the path of first ball's trajectory
                    # Vector from hit_ball to second_ball
                    to_second_dx = second_ball.x - hit_ball.x
                    to_second_dy = second_ball.y - hit_ball.y
                    to_second_dist = math.hypot(to_second_dx, to_second_dy)
                    
                    if to_second_dist < trajectory_length:
                        # Check if second ball is approximately in the trajectory direction
                        to_second_angle = math.atan2(to_second_dy, to_second_dx)
                        angle_diff = abs(to_second_angle - first_ball_angle)
                        # Normalize angle difference to 0-PI range
                        if angle_diff > math.pi:
                            angle_diff = 2 * math.pi - angle_diff
                        
                        # If angle is close (within 45 degrees) and distance is reasonable
                        if angle_diff < math.pi / 4 and to_second_dist < 200 * self.scale:
                            # Check if second ball is actually in path (not behind)
                            dot_product = (to_second_dx * math.cos(first_ball_angle) + 
                                         to_second_dy * math.sin(first_ball_angle))
                            if dot_product > 0:  # In forward direction
                                # Calculate where second ball might be hit
                                # Project second ball position onto trajectory line
                                proj_length = dot_product
                                proj_x = hit_ball.x + math.cos(first_ball_angle) * proj_length
                                proj_y = hit_ball.y + math.sin(first_ball_angle) * proj_length
                                dist_to_trajectory = math.hypot(second_ball.x - proj_x, second_ball.y - proj_y)
                                
                                # If second ball is close enough to trajectory
                                if dist_to_trajectory < (hit_ball.radius + second_ball.radius) * 1.5:
                                    second_ball_hits.append((second_ball, proj_x, proj_y))
                
                # Draw potential second ball hits
                for second_ball, proj_x, proj_y in second_ball_hits:
                    # Draw line from first ball to second ball (magenta/cyan)
                    pygame.draw.line(self.screen, COLORS['gold'], 
                                   (int(hit_ball.x), int(hit_ball.y)),
                                   (int(second_ball.x), int(second_ball.y)), 2)
                    
                    # Draw potential trajectory from second ball (shows where it might go)
                    second_ball_angle = math.atan2(second_ball.y - hit_ball.y, 
                                                  second_ball.x - hit_ball.x)
                    second_trajectory_length = 200 * self.scale
                    
                    # Draw second ball trajectory (magenta dashed)
                    for k in range(0, 20):
                        t = k / 20
                        tx = second_ball.x + math.cos(second_ball_angle) * (second_trajectory_length * t)
                        ty = second_ball.y + math.sin(second_ball_angle) * (second_trajectory_length * t)
                        if self.table_rect.collidepoint(tx, ty):
                            alpha = int(120 * (1 - t * 0.4))
                            if k % 3 == 0:  # Dashed effect
                                pygame.draw.circle(self.screen, (255, alpha, 255), (int(tx), int(ty)), int(2 * self.scale))
                    
                    # Highlight second ball with a ring
                    pygame.draw.circle(self.screen, COLORS['gold_bright'], 
                                     (int(second_ball.x), int(second_ball.y)), 
                                     int(second_ball.radius + 2 * self.scale), 2)

    def draw_ai_aiming_line(self):
        """Draw the AI's aiming guide line with enhanced geometry: cue → first ball → second ball."""
        if not self.cue_ball or self.cue_ball.potted or not self.ai_shot_calculated:
            return

        angle = self.ai_angle

        # Draw dotted line and check for ball intersections
        hit_ball = None
        hit_point = None
        for i in range(1, 80):
            t = i / 80
            x = self.cue_ball.x + math.cos(angle) * ((30 + i * 12) * self.scale)
            y = self.cue_ball.y + math.sin(angle) * ((30 + i * 12) * self.scale)

            if not self.table_rect.collidepoint(x, y):
                break

            # Check if this point hits a ball
            if not hit_ball:
                for ball in self.balls:
                    if ball.potted or ball.ball_type == 'white':
                        continue
                    dist = math.hypot(x - ball.x, y - ball.y)
                    if dist < ball.radius + self.cue_ball.radius:
                        hit_ball = ball
                        hit_point = (x, y)
                        break
            
            if i <= 25:
                alpha = int(180 * (1 - t * 0.7))
                pygame.draw.circle(self.screen, (alpha, alpha, alpha), (int(x), int(y)), int(2 * self.scale))
        
        # Enhanced geometry visualization: cue → first ball → second ball
        if hit_ball and hit_point:
            # Draw solid line from cue ball to first ball hit (cyan)
            pygame.draw.line(self.screen, COLORS['gold_bright'], 
                           (int(self.cue_ball.x), int(self.cue_ball.y)),
                           (int(hit_ball.x), int(hit_ball.y)), 3)
            
            # Calculate the direction the first ball will travel
            cue_to_ball_dx = hit_ball.x - self.cue_ball.x
            cue_to_ball_dy = hit_ball.y - self.cue_ball.y
            cue_to_ball_dist = math.hypot(cue_to_ball_dx, cue_to_ball_dy)
            
            if cue_to_ball_dist > 0:
                cue_to_ball_nx = cue_to_ball_dx / cue_to_ball_dist
                cue_to_ball_ny = cue_to_ball_dy / cue_to_ball_dist
                first_ball_angle = math.atan2(cue_to_ball_ny, cue_to_ball_nx)
                
                # Draw trajectory from first ball (cyan dashed)
                trajectory_length = 300 * self.scale
                for j in range(0, 30):
                    t = j / 30
                    tx = hit_ball.x + math.cos(first_ball_angle) * (trajectory_length * t)
                    ty = hit_ball.y + math.sin(first_ball_angle) * (trajectory_length * t)
                    if self.table_rect.collidepoint(tx, ty):
                        alpha = int(150 * (1 - t * 0.3))
                        if j % 3 == 0:
                            pygame.draw.circle(self.screen, (alpha, 255, 255), (int(tx), int(ty)), int(3 * self.scale))
                
                # Check for potential second ball hits
                for second_ball in self.balls:
                    if second_ball.potted or second_ball == hit_ball or second_ball.ball_type == 'white':
                        continue
                    
                    to_second_dx = second_ball.x - hit_ball.x
                    to_second_dy = second_ball.y - hit_ball.y
                    to_second_dist = math.hypot(to_second_dx, to_second_dy)
                    
                    if to_second_dist < trajectory_length:
                        to_second_angle = math.atan2(to_second_dy, to_second_dx)
                        angle_diff = abs(to_second_angle - first_ball_angle)
                        if angle_diff > math.pi:
                            angle_diff = 2 * math.pi - angle_diff
                        
                        if angle_diff < math.pi / 4 and to_second_dist < 200 * self.scale:
                            dot_product = (to_second_dx * math.cos(first_ball_angle) + 
                                         to_second_dy * math.sin(first_ball_angle))
                            if dot_product > 0:
                                proj_length = dot_product
                                proj_x = hit_ball.x + math.cos(first_ball_angle) * proj_length
                                proj_y = hit_ball.y + math.sin(first_ball_angle) * proj_length
                                dist_to_trajectory = math.hypot(second_ball.x - proj_x, second_ball.y - proj_y)
                                
                                if dist_to_trajectory < (hit_ball.radius + second_ball.radius) * 1.5:
                                    # Draw line from first ball to second ball
                                    pygame.draw.line(self.screen, COLORS['gold'], 
                                                   (int(hit_ball.x), int(hit_ball.y)),
                                                   (int(second_ball.x), int(second_ball.y)), 2)
                                    
                                    # Draw trajectory from second ball (magenta dashed)
                                    second_ball_angle = math.atan2(second_ball.y - hit_ball.y, 
                                                                  second_ball.x - hit_ball.x)
                                    second_trajectory_length = 200 * self.scale
                                    for k in range(0, 20):
                                        t = k / 20
                                        tx = second_ball.x + math.cos(second_ball_angle) * (second_trajectory_length * t)
                                        ty = second_ball.y + math.sin(second_ball_angle) * (second_trajectory_length * t)
                                        if self.table_rect.collidepoint(tx, ty):
                                            alpha = int(120 * (1 - t * 0.4))
                                            if k % 3 == 0:
                                                pygame.draw.circle(self.screen, (255, alpha, 255), (int(tx), int(ty)), int(2 * self.scale))
                                    
                                    # Highlight second ball
                                    pygame.draw.circle(self.screen, COLORS['gold_bright'], 
                                                     (int(second_ball.x), int(second_ball.y)), 
                                                     int(second_ball.radius + 2 * self.scale), 2)

    def draw_cue_stick(self):
        """Draw the cue stick during aiming/charging."""
        if not self.cue_ball:
            return

        mx, my = pygame.mouse.get_pos()
        angle = math.atan2(my - self.cue_ball.y, mx - self.cue_ball.x)

        # Pull back based on power (scaled)
        pullback = (25 + self.cue_power * 0.8) * self.scale
        stick_length = 220 * self.scale

        start_x = self.cue_ball.x - math.cos(angle) * pullback
        start_y = self.cue_ball.y - math.sin(angle) * pullback
        end_x = start_x - math.cos(angle) * stick_length
        end_y = start_y - math.sin(angle) * stick_length

        # Draw stick (scaled thickness)
        pygame.draw.line(self.screen, COLORS['wood_light'], (start_x, start_y), (end_x, end_y), int(8 * self.scale))
        pygame.draw.line(self.screen, COLORS['wood'], (start_x, start_y), (end_x, end_y), int(5 * self.scale))

        # Tip (scaled)
        tip_x = self.cue_ball.x - math.cos(angle) * (pullback - 8 * self.scale)
        tip_y = self.cue_ball.y - math.sin(angle) * (pullback - 8 * self.scale)
        pygame.draw.circle(self.screen, (100, 140, 170), (int(tip_x), int(tip_y)), int(5 * self.scale))

    def draw_ai_cue_stick(self):
        """Draw the AI's cue stick during preparation."""
        if not self.cue_ball or not self.ai_shot_calculated:
            return

        angle = self.ai_angle

        # Pull back based on AI's charging power (scaled)
        pullback = (25 + self.ai_power_charging * 0.8) * self.scale
        stick_length = 220 * self.scale

        start_x = self.cue_ball.x - math.cos(angle) * pullback
        start_y = self.cue_ball.y - math.sin(angle) * pullback
        end_x = start_x - math.cos(angle) * stick_length
        end_y = start_y - math.sin(angle) * stick_length

        # Draw stick (scaled thickness) - slightly different color to distinguish
        pygame.draw.line(self.screen, COLORS['wood_light'], (start_x, start_y), (end_x, end_y), int(8 * self.scale))
        pygame.draw.line(self.screen, (80, 60, 40), (start_x, start_y), (end_x, end_y), int(5 * self.scale))

        # Tip (scaled)
        tip_x = self.cue_ball.x - math.cos(angle) * (pullback - 8 * self.scale)
        tip_y = self.cue_ball.y - math.sin(angle) * (pullback - 8 * self.scale)
        pygame.draw.circle(self.screen, (100, 140, 170), (int(tip_x), int(tip_y)), int(5 * self.scale))

    def draw_ui(self):
        """Draw UI elements: scores, info, power bar."""
        if not self.window_rect:
            return
        
        # UI panel at top of content area (below title bar)
        title_bar_height = int(35 * self.scale)
        ui_panel_y = self.window_rect.y + title_bar_height
        ui_panel_height = int(65 * self.scale)
        ui_panel_rect = pygame.Rect(self.window_rect.x, ui_panel_y, self.window_rect.width, ui_panel_height)
        
        # Top panel
        pygame.draw.rect(self.screen, COLORS['bg_panel'], ui_panel_rect)
        pygame.draw.line(self.screen, COLORS['gold_dark'],
                         (ui_panel_rect.left, ui_panel_rect.bottom),
                         (ui_panel_rect.right, ui_panel_rect.bottom), 2)

        # Player 1 score
        p1_color = COLORS['gold_bright'] if self.current_player == 0 else COLORS['text_secondary']
        p1_name = self.fonts['medium'].render(self.player_names[0], True, p1_color)
        p1_score = self.fonts['large'].render(str(self.scores[0]), True, COLORS['text_primary'])
        self.screen.blit(p1_name, (ui_panel_rect.x + int(30 * self.scale), ui_panel_rect.y + int(8 * self.scale)))
        self.screen.blit(p1_score, (ui_panel_rect.x + int(30 * self.scale), ui_panel_rect.y + int(32 * self.scale)))

        if self.current_break[0] > 0:
            brk = self.fonts['tiny'].render(f"Break: {self.current_break[0]}", True, COLORS['text_success'])
            self.screen.blit(brk, (ui_panel_rect.x + int(130 * self.scale), ui_panel_rect.y + int(40 * self.scale)))

        # Player 2 score
        p2_color = COLORS['gold_bright'] if self.current_player == 1 else COLORS['text_secondary']
        p2_name = self.fonts['medium'].render(self.player_names[1], True, p2_color)
        p2_score = self.fonts['large'].render(str(self.scores[1]), True, COLORS['text_primary'])
        self.screen.blit(p2_name, (ui_panel_rect.right - p2_name.get_width() - int(30 * self.scale), ui_panel_rect.y + int(8 * self.scale)))
        self.screen.blit(p2_score, (ui_panel_rect.right - p2_score.get_width() - int(30 * self.scale), ui_panel_rect.y + int(32 * self.scale)))

        if self.current_break[1] > 0:
            brk = self.fonts['tiny'].render(f"Break: {self.current_break[1]}", True, COLORS['text_success'])
            self.screen.blit(brk, (ui_panel_rect.right - int(130 * self.scale), ui_panel_rect.y + int(40 * self.scale)))

        # Ball on indicator
        ball_on_text = self.ball_on.upper() if self.ball_on != "color" else "ANY COLOR"
        on_color = self.get_ball_on_color()
        on_surf = self.fonts['medium'].render(f"ON: {ball_on_text}", True, on_color)
        self.screen.blit(on_surf, on_surf.get_rect(center=(ui_panel_rect.centerx, ui_panel_rect.y + int(25 * self.scale))))

        # Reds remaining
        reds_text = f"Reds: {self.reds_remaining}"
        reds_surf = self.fonts['small'].render(reds_text, True, COLORS['ball_red'])
        self.screen.blit(reds_surf, reds_surf.get_rect(center=(ui_panel_rect.centerx, ui_panel_rect.y + int(50 * self.scale))))

        # Power bar (when charging) - positioned at bottom of window
        # Show for human player charging
        if self.is_charging:
            bar_width = int(250 * self.scale)
            bar_height = int(18 * self.scale)
            bar_x = ui_panel_rect.centerx - bar_width // 2
            bar_y = self.window_rect.bottom - int(55 * self.scale)

            # Background
            pygame.draw.rect(self.screen, COLORS['bg_panel'], 
                           (bar_x - int(5 * self.scale), bar_y - int(5 * self.scale),
                            bar_width + int(10 * self.scale), bar_height + int(10 * self.scale)),
                           border_radius=int(5 * self.scale))

            # Fill - power max is 30, display as percentage (30 = 100%)
            power_percent = int((self.cue_power / 30) * 100) if self.cue_power > 0 else 0
            fill_width = int(bar_width * (self.cue_power / 30))
            if power_percent < 40:
                fill_color = COLORS['text_success']
            elif power_percent < 75:
                fill_color = COLORS['gold']
            else:
                fill_color = COLORS['text_foul']

            pygame.draw.rect(self.screen, fill_color, (bar_x, bar_y, fill_width, bar_height), border_radius=int(3 * self.scale))
            pygame.draw.rect(self.screen, COLORS['text_primary'], (bar_x, bar_y, bar_width, bar_height), 2, border_radius=int(3 * self.scale))

            # Power text - show as percentage (30 = 100%)
            pwr_text = self.fonts['small'].render(f"POWER: {power_percent}%", True, COLORS['text_primary'])
            self.screen.blit(pwr_text, pwr_text.get_rect(center=(ui_panel_rect.centerx, bar_y - int(15 * self.scale))))
        
        # AI power bar (when AI is preparing)
        if (self.mode == GameMode.VS_AI or self.mode == GameMode.TOURNAMENT) and self.current_player == 1 and self.ai_preparing and self.ai_shot_calculated:
            bar_width = int(250 * self.scale)
            bar_height = int(18 * self.scale)
            bar_x = ui_panel_rect.centerx - bar_width // 2
            bar_y = self.window_rect.bottom - int(55 * self.scale)

            # Background
            pygame.draw.rect(self.screen, COLORS['bg_panel'], 
                           (bar_x - int(5 * self.scale), bar_y - int(5 * self.scale),
                            bar_width + int(10 * self.scale), bar_height + int(10 * self.scale)),
                           border_radius=int(5 * self.scale))

            # Fill - power max is 30, display as percentage (30 = 100%)
            ai_power_percent = int((self.ai_power_charging / 30) * 100) if self.ai_power_charging > 0 else 0
            fill_width = int(bar_width * (self.ai_power_charging / 30))
            if ai_power_percent < 40:
                fill_color = COLORS['text_success']
            elif ai_power_percent < 75:
                fill_color = COLORS['gold']
            else:
                fill_color = COLORS['text_foul']

            pygame.draw.rect(self.screen, fill_color, (bar_x, bar_y, fill_width, bar_height), border_radius=int(3 * self.scale))
            pygame.draw.rect(self.screen, COLORS['text_primary'], (bar_x, bar_y, bar_width, bar_height), 2, border_radius=int(3 * self.scale))

            # Power text - show as percentage (30 = 100%)
            pwr_text = self.fonts['small'].render(f"{self.player_names[1]} POWER: {ai_power_percent}%", True, COLORS['text_primary'])
            self.screen.blit(pwr_text, pwr_text.get_rect(center=(ui_panel_rect.centerx, bar_y - int(15 * self.scale))))

        # Message - positioned below UI panel
        if self.message and self.message_timer > 0:
            msg_surf = self.fonts['medium'].render(self.message, True, self.message_color)
            msg_rect = msg_surf.get_rect(center=(ui_panel_rect.centerx, ui_panel_rect.bottom + int(45 * self.scale)))

            # Background
            bg_rect = msg_rect.inflate(int(30 * self.scale), int(15 * self.scale))
            pygame.draw.rect(self.screen, COLORS['bg_panel'], bg_rect, border_radius=int(8 * self.scale))
            pygame.draw.rect(self.screen, self.message_color, bg_rect, 2, border_radius=int(8 * self.scale))
            self.screen.blit(msg_surf, msg_rect)

        # Bottom hint
        hint = self.fonts['tiny'].render("ESC: Menu", True, COLORS['text_secondary'])
        self.screen.blit(hint, (self.window_rect.x + int(10 * self.scale), self.window_rect.bottom - int(25 * self.scale)))

        # AI thinking indicator
        if (self.mode == GameMode.VS_AI or self.mode == GameMode.TOURNAMENT) and self.current_player == 1 and self.ai_timer > 0:
            dots = "." * ((self.animation_tick // 15) % 4)
            think = self.fonts['small'].render(f"Computer thinking{dots}", True, COLORS['gold'])
            self.screen.blit(think, think.get_rect(center=(ui_panel_rect.centerx, ui_panel_rect.bottom + int(80 * self.scale))))

    def draw_game(self):
        """Draw the main game screen."""
        self._draw_window_frame()
        if not self.window_rect:
            return
        
        self.draw_table()

        # Draw aiming line (when human player aiming, or AI preparing)
        is_human_turn = not ((self.mode == GameMode.VS_AI or self.mode == GameMode.TOURNAMENT) and self.current_player == 1)
        balls_moving = any(b.is_moving() for b in self.balls if not b.potted)

        if not balls_moving and self.turn_phase == TurnPhase.AIMING:
            if is_human_turn:
                self.draw_aiming_line()
            elif (self.mode == GameMode.VS_AI or self.mode == GameMode.TOURNAMENT) and self.current_player == 1 and self.ai_shot_calculated:
                # Draw AI's aiming line (use same method but with AI angle)
                self.draw_ai_aiming_line()

        # Draw balls
        for ball in self.balls:
            ball.draw(self.screen)

        # Draw cue stick (human or AI)
        if self.turn_phase == TurnPhase.AIMING and not balls_moving:
            if is_human_turn:
                self.draw_cue_stick()
            elif (self.mode == GameMode.VS_AI or self.mode == GameMode.TOURNAMENT) and self.current_player == 1:
                # Draw AI's cue stick
                self.draw_ai_cue_stick()

        # Draw placement guide when placing cue ball
        if self.turn_phase == TurnPhase.PLACING_CUE:
            # Highlight D zone
            d_rect = pygame.Rect(self.baulk_x - self.d_radius, self.d_center_y - self.d_radius,
                                 self.d_radius, self.d_radius * 2)
            s = pygame.Surface((self.d_radius, self.d_radius * 2), pygame.SRCALPHA)
            s.fill((255, 255, 100, 40))
            self.screen.blit(s, d_rect.topleft)

        self.draw_ui()

    def draw_game_over(self):
        """Draw game over screen."""
        self.draw_game()
        
        if not self.window_rect:
            return

        # Overlay
        overlay = pygame.Surface((self.window_rect.width, self.window_rect.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        self.screen.blit(overlay, self.window_rect.topleft)

        # Winner
        player_won = self.scores[0] > self.scores[1]
        if player_won:
            winner_text = f"{self.player_names[0]} WINS!"
        elif self.scores[1] > self.scores[0]:
            winner_text = f"{self.player_names[1]} WINS!"
        else:
            winner_text = "IT'S A TIE!"

        title_bar_height = int(35 * self.scale)
        content_y = self.window_rect.y + title_bar_height
        center_x = self.window_rect.centerx
        
        winner = self.fonts['title'].render(winner_text, True, COLORS['gold'])
        self.screen.blit(winner, winner.get_rect(center=(center_x, content_y + int(200 * self.scale))))

        # Tournament-specific messages
        if self.mode == GameMode.TOURNAMENT and self.tournament_active:
            if player_won:
                if self.tournament_match == 0:
                    # Won first match
                    tourney_text = "SEMI-FINAL VICTORY! On to the Final..."
                    tourney_surf = self.fonts['medium'].render(tourney_text, True, COLORS['gold_bright'])
                    self.screen.blit(tourney_surf, tourney_surf.get_rect(center=(center_x, content_y + int(260 * self.scale))))
                elif self.tournament_match == 1:
                    # Won tournament!
                    tourney_text = "CHAMPION! You've won LIVE AT THE CRUCIBLE!"
                    tourney_surf = self.fonts['large'].render(tourney_text, True, COLORS['gold_bright'])
                    self.screen.blit(tourney_surf, tourney_surf.get_rect(center=(center_x, content_y + int(260 * self.scale))))
            else:
                # Lost tournament match
                tourney_text = "Tournament Over"
                tourney_surf = self.fonts['medium'].render(tourney_text, True, COLORS['text_foul'])
                self.screen.blit(tourney_surf, tourney_surf.get_rect(center=(center_x, content_y + int(260 * self.scale))))

        # Final scores
        y = content_y + int(320 * self.scale)
        for i, name in enumerate(self.player_names):
            line = f"{name}: {self.scores[i]} pts  |  Best Break: {self.highest_break[i]}"
            surf = self.fonts['medium'].render(line, True, COLORS['text_primary'])
            self.screen.blit(surf, surf.get_rect(center=(center_x, y + i * int(50 * self.scale))))

        # Prompt
        if (self.animation_tick // 30) % 2 == 0:
            if self.mode == GameMode.TOURNAMENT and self.tournament_active and player_won and self.tournament_match == 0:
                prompt = self.fonts['medium'].render("Click to continue to Final", True, COLORS['gold'])
            else:
                prompt = self.fonts['medium'].render("Click to continue", True, COLORS['gold'])
            self.screen.blit(prompt, prompt.get_rect(center=(center_x, content_y + int(520 * self.scale))))

    # =========================================================================
    # EMBEDDED COMPONENT METHODS
    # =========================================================================

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handle events. Returns True if the event was consumed."""
        if not self.active:
            return False

        # Check if event is within window bounds
        if hasattr(event, 'pos') and self.window_rect:
            if not self.window_rect.collidepoint(event.pos):
                # Event is outside window - only handle exit button which is at screen coords
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.exit_button_rect and self.exit_button_rect.collidepoint(event.pos):
                        self.close()
                        return True
                return False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.close()
                return True

        # Click exit button
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.exit_button_rect and hasattr(event, 'pos'):
                if self.exit_button_rect.collidepoint(event.pos):
                    self.close()
                    return True

        # State-specific events (coordinates are relative to screen, rects are absolute)
        if self.state == GameState.LOADING:
            # Loading screen - no interaction, just wait for timer
            return False
        
        if self.state == GameState.NAME_INPUT:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if not self.window_rect:
                    return False
                
                # Calculate input box position exactly as in draw_name_input()
                content_rect = pygame.Rect(
                    self.window_rect.x,
                    self.window_rect.y + int(35 * self.scale),
                    self.window_rect.width,
                    self.window_rect.height - int(35 * self.scale)
                )
                center_x = content_rect.centerx
                base_y = content_rect.y + content_rect.height // 2 - int(100 * self.scale)
                input_width = int(400 * self.scale)
                input_height = int(50 * self.scale)
                input_x = center_x - input_width // 2
                input_y = base_y + int(60 * self.scale)
                input_rect = pygame.Rect(input_x, input_y, input_width, input_height)
                
                if input_rect.collidepoint(event.pos):
                    self.name_input_active = True
                    return True
                elif self.name_continue_btn.collidepoint(event.pos) and len(self.name_input_text.strip()) > 0:
                    self.player_name = self.name_input_text.strip()
                    self.name_input_active = False
                    self.state = GameState.SPLASH
                    return True
                else:
                    self.name_input_active = False
                    return True
            
            if event.type == pygame.KEYDOWN:
                if self.name_input_active:
                    if event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:
                        if len(self.name_input_text.strip()) > 0:
                            self.player_name = self.name_input_text.strip()
                            self.name_input_active = False
                            self.state = GameState.SPLASH
                            return True
                    elif event.key == pygame.K_BACKSPACE:
                        self.name_input_text = self.name_input_text[:-1]
                        return True
                    elif event.key == pygame.K_ESCAPE:
                        self.name_input_active = False
                        return True
                    elif event.unicode and event.unicode.isprintable() and len(self.name_input_text) < 20:
                        self.name_input_text += event.unicode
                        return True
        
        if self.state == GameState.SPLASH:
            if event.type == pygame.MOUSEBUTTONDOWN:
                if self.btn_ai.collidepoint(event.pos):
                    self.mode = GameMode.VS_AI
                    player_name = self.player_name if self.player_name else "Player"
                    self.player_names = [player_name, "AI Opponent"]
                    self.state = GameState.PLAYING
                    self.reset_match()
                    return True
                elif self.btn_pvp.collidepoint(event.pos):
                    self.mode = GameMode.TWO_PLAYER
                    player_name = self.player_name if self.player_name else "Player"
                    self.player_names = [player_name, "Player 2"]
                    self.state = GameState.PLAYING
                    self.reset_match()
                    return True
                elif self.btn_tournament.collidepoint(event.pos):
                    # Start tournament
                    self.mode = GameMode.TOURNAMENT
                    self.tournament_active = True
                    self.tournament_match = 0  # Start with first match vs Louis
                    self.tournament_won_match_1 = False
                    player_name = self.player_name if self.player_name else "Player"
                    self.player_names = [player_name, "Mst. Louis Sonic"]
                    self.state = GameState.PLAYING
                    self.reset_match()
                    return True
                elif self.btn_rules.collidepoint(event.pos):
                    self.state = GameState.RULES
                    return True

        elif self.state == GameState.RULES:
            if event.type in [pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN]:
                self.state = GameState.SPLASH
                return True

        elif self.state == GameState.GAME_OVER:
            if event.type == pygame.MOUSEBUTTONDOWN:
                # Handle tournament progression
                if self.mode == GameMode.TOURNAMENT and self.tournament_active:
                    if self.tournament_match == 0 and self.scores[0] > self.scores[1]:
                        # Won first match, advance to final
                        self.tournament_match = 1
                        player_name = self.player_name if self.player_name else "Player"
                        self.player_names = [player_name, "Gen. Bradley Sonic"]
                        self.state = GameState.PLAYING
                        self.reset_match()
                    else:
                        # Tournament ended (won or lost)
                        self.state = GameState.SPLASH
                        self.tournament_active = False
                else:
                    self.state = GameState.SPLASH
                return True

        elif self.state == GameState.PLAYING:
            consumed = self.handle_game_event(event)
            return consumed

        return False

    def update(self, dt: float) -> None:
        """Update game state. Called each frame."""
        if not self.active:
            return

        self.animation_tick += 1

        # Handle loading screen state
        if self.state == GameState.LOADING:
            self.loading_timer += 1
            
            # Show CGA+ message after 1 second (60 frames)
            if self.loading_timer >= 60 and not self.cga_message_shown:
                self.cga_message_shown = True
                self.cga_message_timer = 0
            
            # Update CGA message timer if shown
            if self.cga_message_shown:
                self.cga_message_timer += 1
                
                # After showing CGA+ message for 2 seconds, transition to name input
                if self.cga_message_timer >= self.cga_message_duration:
                    if not self.player_name:
                        self.state = GameState.NAME_INPUT
                    else:
                        self.state = GameState.SPLASH
                        self.reset_match()

        # Update
        if self.state == GameState.PLAYING:
            self.update_game(dt)

        # Message timer
        if self.message_timer > 0:
            self.message_timer -= 1

    def draw(self) -> None:
        """Draw the game. Called each frame."""
        if not self.active:
            return

        # Clip drawing to window
        if self.window_rect:
            old_clip = self.screen.get_clip()
            self.screen.set_clip(self.window_rect)

        # Draw based on state
        if self.state == GameState.LOADING:
            self.draw_loading()
        elif self.state == GameState.NAME_INPUT:
            self.draw_name_input()
        elif self.state == GameState.SPLASH:
            self.draw_splash()
        elif self.state == GameState.RULES:
            self.draw_rules()
        elif self.state == GameState.PLAYING:
            self.draw_game()
        elif self.state == GameState.GAME_OVER:
            self.draw_game_over()

        # Restore clip
        if self.window_rect:
            self.screen.set_clip(old_clip)

    def handle_game_event(self, event: pygame.event.Event) -> bool:
        """Handle events during gameplay. Returns True if event was consumed."""
        is_human_turn = not ((self.mode == GameMode.VS_AI or self.mode == GameMode.TOURNAMENT) and self.current_player == 1)
        balls_moving = any(b.is_moving() for b in self.balls if not b.potted)

        if balls_moving:
            return False

        if self.turn_phase == TurnPhase.PLACING_CUE:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                # Check if in D zone
                dist = math.hypot(mx - self.baulk_x, my - self.d_center_y)
                if mx <= self.baulk_x and dist <= self.d_radius:
                    self.cue_ball.x, self.cue_ball.y = mx, my
                    self.turn_phase = TurnPhase.AIMING
                    self.show_message("", 0)

                    if (self.mode == GameMode.VS_AI or self.mode == GameMode.TOURNAMENT) and self.current_player == 1:
                        # Much slower AI preparation
                        self.ai_timer = random.randint(180, 300)
                        self.ai_shot_calculated = False
                        self.ai_preparing = True
                        self.ai_power_charging = 0
                    return True

        elif is_human_turn and self.turn_phase == TurnPhase.AIMING:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.is_charging = True
                self.cue_power = 0
                return True

            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if self.is_charging and self.cue_power > 1.5:  # Adjusted threshold for new max of 30
                    # Shoot!
                    mx, my = event.pos
                    angle = math.atan2(my - self.cue_ball.y, mx - self.cue_ball.x)
                    speed = self.cue_power * 2.0  # Power max is now 30 (was 100)

                    self.cue_ball.vx = math.cos(angle) * speed
                    self.cue_ball.vy = math.sin(angle) * speed

                    self.turn_phase = TurnPhase.BALLS_MOVING
                    self.first_ball_hit = None
                    self.potted_this_turn.clear()
                    self.shot_started = True

                self.is_charging = False
                self.cue_power = 0
                return True
        
        return False

    def update_game(self, dt: float):
        """Update game state."""
        balls_moving = any(b.is_moving() for b in self.balls if not b.potted)

        # Cue ball placement
        if self.turn_phase == TurnPhase.PLACING_CUE:
            # AI placement (automatic)
            if (self.mode == GameMode.VS_AI or self.mode == GameMode.TOURNAMENT) and self.current_player == 1:
                # AI automatically places cue ball in D zone after a short delay
                if not hasattr(self, 'ai_placing_cue_timer'):
                    self.ai_placing_cue_timer = 60  # 1 second at 60fps
                
                self.ai_placing_cue_timer -= 1
                if self.ai_placing_cue_timer <= 0:
                    # Place cue ball in a good position in the D (slightly left of center, near middle)
                    # Randomize position slightly for variety
                    offset_x = random.uniform(-self.d_radius * 0.3, -self.d_radius * 0.1)
                    offset_y = random.uniform(-self.d_radius * 0.4, self.d_radius * 0.4)
                    
                    # Ensure within D bounds
                    placement_x = self.baulk_x + offset_x
                    placement_y = self.d_center_y + offset_y
                    dist_from_center = math.hypot(placement_x - self.baulk_x, placement_y - self.d_center_y)
                    
                    if dist_from_center > self.d_radius:
                        # Clamp to D arc
                        angle = math.atan2(placement_y - self.d_center_y, placement_x - self.baulk_x)
                        placement_x = self.baulk_x + math.cos(angle) * self.d_radius
                        placement_y = self.d_center_y + math.sin(angle) * self.d_radius
                    
                    # Keep within table bounds
                    placement_y = max(self.table_rect.top + self.cue_ball.radius,
                                    min(placement_y, self.table_rect.bottom - self.cue_ball.radius))
                    
                    self.cue_ball.x = placement_x
                    self.cue_ball.y = placement_y
                    self.turn_phase = TurnPhase.AIMING
                    self.show_message("", 0)
                    
                    # Start AI preparation
                    self.ai_timer = random.randint(180, 300)
                    self.ai_shot_calculated = False
                    self.ai_preparing = True
                    self.ai_power_charging = 0
                    del self.ai_placing_cue_timer
            else:
                # Human placement (mouse follow)
                mx, my = pygame.mouse.get_pos()
                # Mouse coordinates are absolute, table coordinates are absolute (set in _update_layout)
                dist = math.hypot(mx - self.baulk_x, my - self.d_center_y)

                # Constrain to D zone
                if mx <= self.baulk_x and dist <= self.d_radius:
                    # Also keep within table bounds
                    new_y = max(self.table_rect.top + self.cue_ball.radius,
                                min(my, self.table_rect.bottom - self.cue_ball.radius))
                    self.cue_ball.x = mx
                    self.cue_ball.y = new_y
                elif mx > self.baulk_x:
                    # Clamp to baulk line
                    self.cue_ball.x = self.baulk_x
                elif dist > self.d_radius:
                    # Clamp to D arc
                    angle = math.atan2(my - self.d_center_y, mx - self.baulk_x)
                    self.cue_ball.x = self.baulk_x + math.cos(angle) * self.d_radius
                    self.cue_ball.y = self.d_center_y + math.sin(angle) * self.d_radius

        # AI turn
        if (self.mode == GameMode.VS_AI or self.mode == GameMode.TOURNAMENT) and self.current_player == 1:
            if not balls_moving and self.turn_phase == TurnPhase.AIMING:
                if not self.ai_shot_calculated:
                    # Select appropriate AI based on mode
                    if self.mode == GameMode.TOURNAMENT:
                        if self.tournament_match == 0:
                            ai_player = self.ai_louis  # First match
                        else:
                            ai_player = self.ai_bradley  # Final match
                    else:
                        ai_player = self.ai  # Regular AI match
                    
                    self.ai_angle, self.ai_power = ai_player.calculate_shot(
                        self.cue_ball, self.balls, self.ball_on, self.pockets
                    )
                    self.ai_shot_calculated = True
                    self.ai_preparing = True
                    self.ai_power_charging = 0
                
                # AI preparation phase - simulate "charging" power
                if self.ai_preparing and self.ai_shot_calculated:
                    # Charge power over time (faster than human but visible)
                    # Max power is now 30 (was 90), so scale charging rate proportionally
                    if self.ai_power_charging < self.ai_power:
                        self.ai_power_charging = min(self.ai_power_charging + 0.24, self.ai_power)  # Scaled from 0.8 to 0.24 (30/90 ratio)
                    else:
                        # Once power is "charged", countdown to shot
                        self.ai_timer -= 1
                        if self.ai_timer <= 0:
                            # Execute AI shot
                            speed = self.ai_power_charging * 2.0
                            self.cue_ball.vx = math.cos(self.ai_angle) * speed
                            self.cue_ball.vy = math.sin(self.ai_angle) * speed

                            self.turn_phase = TurnPhase.BALLS_MOVING
                            self.first_ball_hit = None
                            self.potted_this_turn.clear()
                            self.shot_started = True
                            self.ai_preparing = False

        # Power charging (slowed down)
        # Max power is now 30 (which represents 100% power)
        if self.is_charging:
            self.cue_power = min(self.cue_power + 0.18, 30)  # Max power is 30 (100%)

        # Physics update - use sub-stepping for better collision detection with fast balls
        if balls_moving or self.turn_phase == TurnPhase.BALLS_MOVING:
            # Use sub-stepping to prevent fast balls from passing through
            # Update physics in smaller steps for better accuracy
            sub_steps = 2
            sub_dt = dt / sub_steps
            
            for _ in range(sub_steps):
                # Update ball positions and apply friction in smaller increments
                for ball in self.balls:
                    if not ball.potted:
                        # Apply friction (30% less friction)
                        speed = math.hypot(ball.vx, ball.vy)
                        if speed > 0.05:
                            # Apply speed-dependent friction (30% less than before)
                            if speed < 15:
                                speed_factor = speed / 15.0
                                aggressive_friction = 0.909 + (speed_factor * 0.0819)  # 30% less friction (9.1% to 0.91% energy loss)
                                ball.vx *= aggressive_friction
                                ball.vy *= aggressive_friction
                            elif speed < 30:
                                speed_factor = (speed - 15) / 15.0
                                moderate_friction = 0.9909 + (speed_factor * 0.00805)  # 30% less friction (0.91% to 0.105% energy loss)
                                ball.vx *= moderate_friction
                                ball.vy *= moderate_friction
                            else:
                                ball.vx *= 0.99895  # 30% less friction
                                ball.vy *= 0.99895
                            
                            # Update position
                            ball.x += ball.vx * sub_dt * 60
                            ball.y += ball.vy * sub_dt * 60
                        else:
                            ball.vx = ball.vy = 0
                
                # Resolve collisions after each sub-step
                self.resolve_physics(sub_dt)

            # Check if all stopped
            if not any(b.is_moving() for b in self.balls if not b.potted):
                if self.shot_started:
                    self.evaluate_turn()


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    # Standalone test mode
    screen = pygame.display.set_mode((1280, 800))
    game = SnookerGame(screen, 1.0, 0, 0, (1280, 800), 0)
    game.start()
    clock = pygame.time.Clock()
    
    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            game.handle_event(event)
        
        game.update(dt)
        game.draw()
        pygame.display.flip()
    
    pygame.quit()