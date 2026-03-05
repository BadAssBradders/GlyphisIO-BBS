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
from typing import List, Tuple, Optional, Dict
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
FRICTION_SLOWDOWN_FACTOR = 0.88  # set this for friction of the balls glide on the table

def adjust_friction(base_friction: float) -> float:
    """Reduce friction slightly to make balls glide a bit more."""
    return 1.0 - (1.0 - base_friction) * FRICTION_SLOWDOWN_FACTOR

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
# BALL CLASS - Enhanced with Realistic Spin Physics
# =============================================================================

class Ball:
    """
    Snooker ball with realistic physics including:
    - Angular velocity (spin)
    - Top/back spin (affects forward momentum after contact)
    - Side spin (affects cushion bounce angles)
    - Sliding vs rolling friction
    - Spin decay over time
    """
    
    # Physics constants for realistic snooker
    BALL_MASS = 0.170  # kg (snooker ball mass)
    BALL_RADIUS_REAL = 0.02625  # meters (52.5mm diameter)
    SLIDING_FRICTION = 0.2  # μs - sliding friction coefficient
    ROLLING_FRICTION = 0.01  # μr - rolling friction coefficient  
    SPIN_DECAY = 0.985  # How fast spin decays per frame
    THROW_COEFFICIENT = 0.03  # How much spin affects object ball direction
    
    def __init__(self, x: float, y: float, ball_type: str, radius: float = None, scale: float = 1.0):
        self.x, self.y = x, y
        self.vx, self.vy = 0.0, 0.0
        self.radius = radius if radius is not None else 11 * scale
        self.ball_type = ball_type
        self.potted = False
        self.color = COLORS.get(f'ball_{ball_type}', (255, 255, 255))
        self.value = BALL_VALUES.get(ball_type, 0)
        
        # Spin properties (angular velocities)
        # top_spin: positive = top spin (ball runs), negative = back spin (draw)
        # side_spin: positive = right spin, negative = left spin
        self.top_spin = 0.0  # Forward/backward spin
        self.side_spin = 0.0  # Left/right spin (English)
        self.is_sliding = False  # True when ball is sliding, False when rolling
        
    def apply_spin(self, top_spin: float, side_spin: float):
        """Apply spin to the ball (called when shot is taken)."""
        self.top_spin = top_spin
        self.side_spin = side_spin
        self.is_sliding = True  # Ball starts sliding after being hit
        
    def get_spin_velocity_component(self) -> Tuple[float, float]:
        """Calculate velocity component from spin for sliding-to-rolling transition."""
        # When sliding, spin creates a force that affects the ball's motion
        # Top spin adds forward velocity, back spin subtracts
        speed = math.hypot(self.vx, self.vy)
        if speed < 0.01:
            return 0, 0
            
        # Direction of travel
        dir_x = self.vx / speed
        dir_y = self.vy / speed
        
        # Perpendicular direction (for side spin effect)
        perp_x = -dir_y
        perp_y = dir_x
        
        # Top/back spin affects forward motion
        forward_component = self.top_spin * 0.15
        # Side spin causes slight curve while sliding
        side_component = self.side_spin * 0.05
        
        return (dir_x * forward_component + perp_x * side_component,
                dir_y * forward_component + perp_y * side_component)

    def update(self, dt: float, friction: float = 0.99895):
        if self.potted:
            return
            
        speed = math.hypot(self.vx, self.vy)
        
        # Realistic snooker physics with spin effects
        if speed > 0.05:
            # Calculate effective friction based on sliding vs rolling
            if self.is_sliding:
                # Sliding friction is higher - ball slides before it rolls
                # Check if ball has transitioned to rolling (spin matches velocity)
                expected_spin = speed * 0.5  # Spin that matches rolling velocity
                spin_diff = abs(self.top_spin - expected_spin)
                
                if spin_diff < 2.0:  # Ball is now rolling naturally
                    self.is_sliding = False
                    self.top_spin = expected_spin  # Lock spin to rolling state
                else:
                    # Apply sliding physics - spin affects velocity
                    spin_vx, spin_vy = self.get_spin_velocity_component()
                    self.vx += spin_vx * dt * 2
                    self.vy += spin_vy * dt * 2
                    
                    # Sliding friction (higher than rolling)
                    slide_friction = 0.994 if speed > 30 else 0.988
                    slide_friction = adjust_friction(slide_friction)
                    self.vx *= slide_friction
                    self.vy *= slide_friction
                    
                    # Spin decays faster while sliding (friction between ball and cloth)
                    self.top_spin *= 0.97
            else:
                # Rolling friction - lower, ball rolls smoothly
                # Apply speed-dependent friction for realistic deceleration
                if speed < 15:
                    speed_factor = speed / 15.0
                    base_friction = 0.920 + (speed_factor * 0.075)
                    rolling_friction = adjust_friction(base_friction)
                elif speed < 30:
                    speed_factor = (speed - 15) / 15.0
                    base_friction = 0.995 + (speed_factor * 0.003)
                    rolling_friction = adjust_friction(base_friction)
                else:
                    rolling_friction = adjust_friction(friction)
                
                self.vx *= rolling_friction
                self.vy *= rolling_friction
            
            # Decay spin over time
            self.top_spin *= self.SPIN_DECAY
            self.side_spin *= self.SPIN_DECAY
            
            # Stop spin when very low
            if abs(self.top_spin) < 0.1:
                self.top_spin = 0
            if abs(self.side_spin) < 0.1:
                self.side_spin = 0
        else:
            # Stop when speed is very low
            self.vx = self.vy = 0
            self.top_spin = 0
            self.side_spin = 0
            self.is_sliding = False
        
        self.x += self.vx * dt * 60
        self.y += self.vy * dt * 60

    def is_moving(self) -> bool:
        return abs(self.vx) > 0.1 or abs(self.vy) > 0.1

    def draw(self, surface: pygame.Surface):
        if self.potted:
            return
        pos = (int(self.x), int(self.y))
        # Shadow - offset based on speed for motion effect
        shadow_offset = min(4, 2 + math.hypot(self.vx, self.vy) * 0.02)
        pygame.draw.circle(surface, (0, 0, 0), (pos[0] + int(shadow_offset), pos[1] + int(shadow_offset)), int(self.radius))
        # Main ball
        pygame.draw.circle(surface, self.color, pos, int(self.radius))
        # Highlight - slightly offset based on spin for visual feedback
        highlight_offset_x = int(self.radius * 0.3) + int(self.side_spin * 0.02)
        highlight_offset_y = int(self.radius * 0.3) - int(self.top_spin * 0.02)
        highlight_pos = (pos[0] - highlight_offset_x, pos[1] - highlight_offset_y)
        pygame.draw.circle(surface, (255, 255, 255), highlight_pos, max(2, int(self.radius * 0.25)))


# =============================================================================
# AI PLAYER
# =============================================================================

class AIPlayer:
    def __init__(
        self,
        skill: float = 0.85,
        aggression: float = 0.5,
        safety_bias: float = 0.5,
        combo_bias: float = 0.5,
        pot_bias: float = 0.5,
    ):
        self.skill = self._clamp01(skill)  # 0.0 to 1.0
        self.aggression = self._clamp01(aggression)  # 0.0 to 1.0
        self.safety_bias = self._clamp01(safety_bias)  # 0.0 to 1.0
        self.combo_bias = self._clamp01(combo_bias)  # 0.0 to 1.0
        self.pot_bias = self._clamp01(pot_bias)  # 0.0 to 1.0

    def _clamp01(self, value: float) -> float:
        return max(0.0, min(1.0, value))

    def _get_next_ball_on(self, ball_on: str, reds_remaining: int, potted_ball_type: str) -> Optional[str]:
        """Determine the next required ball after a successful pot."""
        if ball_on == "red":
            return "color"
        if ball_on == "color":
            if reds_remaining > 0:
                return "red"
            return "yellow"
        if ball_on in COLOR_SEQUENCE:
            try:
                idx = COLOR_SEQUENCE.index(potted_ball_type)
            except ValueError:
                return ball_on
            if idx + 1 < len(COLOR_SEQUENCE):
                return COLOR_SEQUENCE[idx + 1]
            return "done"
        return ball_on
    
    def _evaluate_position_quality(self, cue_end_x: float, cue_end_y: float,
                                   target_ball: Ball, balls: List[Ball],
                                   pockets: List[Tuple[int, int]], ball_on: str,
                                   table_bounds: Optional[Tuple[float, float, float, float]] = None) -> float:
        """Evaluate how good the cue ball position is for the next shot."""
        position_score = 0.0
        
        # Check if cue ball is close to next target (good position)
        if ball_on == "red":
            # After potting a color, want cue ball near a red
            reds = [b for b in balls if not b.potted and b.ball_type == 'red']
            if reds:
                min_dist_to_red = min(math.hypot(cue_end_x - r.x, cue_end_y - r.y) for r in reds)
                if min_dist_to_red < 150:
                    position_score += 50 - (min_dist_to_red / 3)  # Closer is better
        elif ball_on == "color":
            # After potting a red, want cue ball near a color (prefer high-value colors)
            colors = [b for b in balls if not b.potted and b.ball_type in COLOR_SEQUENCE]
            if colors:
                # Prefer being near high-value colors
                best_color = max(colors, key=lambda b: b.value)
                dist_to_color = math.hypot(cue_end_x - best_color.x, cue_end_y - best_color.y)
                if dist_to_color < 150:
                    position_score += 40 - (dist_to_color / 4)
                    position_score += best_color.value * 5  # Bonus for high-value colors
        
        # Check if cue ball is in a good position for a pot
        for target in balls:
            if target.potted or target.ball_type == 'white':
                continue
            for pocket in pockets:
                to_pocket_x = pocket[0] - target.x
                to_pocket_y = pocket[1] - target.y
                to_pocket_dist = math.hypot(to_pocket_x, to_pocket_y)
                if to_pocket_dist < 1:
                    continue
                to_pocket_x /= to_pocket_dist
                to_pocket_y /= to_pocket_dist
                
                ghost_x = target.x - to_pocket_x * (target.radius + target.radius) * 1.05
                ghost_y = target.y - to_pocket_y * (target.radius + target.radius) * 1.05
                
                dist_to_ghost = math.hypot(cue_end_x - ghost_x, cue_end_y - ghost_y)
                if dist_to_ghost < 100:
                    position_score += 30 - (dist_to_ghost / 3)
        
        # Penalize being too close to cushions (harder to control)
        cushion_margin = target_ball.radius * 3
        if table_bounds:
            left, top, right, bottom = table_bounds
            if (cue_end_x < left + cushion_margin or cue_end_x > right - cushion_margin or
                cue_end_y < top + cushion_margin or cue_end_y > bottom - cushion_margin):
                position_score -= 20
        else:
            table_width = 1280
            table_height = 800
            if (cue_end_x < cushion_margin or cue_end_x > table_width - cushion_margin or
                cue_end_y < cushion_margin or cue_end_y > table_height - cushion_margin):
                position_score -= 20
        
        return position_score
    
    def _evaluate_safety_shot(self, cue: Ball, balls: List[Ball],
                             pockets: List[Tuple[int, int]], ball_on: str, reds_remaining: int = 15) -> Optional[dict]:
        """Evaluate a safety shot when no pot is available or strategically better."""
        best_safety = None
        best_safety_score = -float('inf')
        
        # Get valid target balls (must hit one of them)
        if ball_on == "red":
            valid = [b for b in balls if not b.potted and b.ball_type == 'red']
        elif ball_on == "color":
            valid = [b for b in balls if not b.potted and b.ball_type in COLOR_SEQUENCE]
        else:
            valid = [b for b in balls if not b.potted and b.ball_type == ball_on]
        
        if not valid:
            return None
        
        # Determine what the opponent will be on after a safety (no pot)
        if reds_remaining > 0:
            next_ball_on = "red"
        else:
            remaining_colors = [c for c in COLOR_SEQUENCE if any(
                b.ball_type == c and not b.potted for b in balls
            )]
            next_ball_on = remaining_colors[0] if remaining_colors else "done"
        
        # Try different safety approaches
        for target in valid:
            # Approach 1: Hit target softly, leave cue ball far from any pottable ball
            angle = math.atan2(target.y - cue.y, target.x - cue.x)
            distance = math.hypot(target.x - cue.x, target.y - cue.y)
            
            # Estimate cue ball end position (soft hit, minimal follow-through)
            # Use a thin cut to minimize cue ball movement
            target_to_cue_x = cue.x - target.x
            target_to_cue_y = cue.y - target.y
            target_to_cue_dist = math.hypot(target_to_cue_x, target_to_cue_y)
            if target_to_cue_dist < 1:
                continue
            target_to_cue_x /= target_to_cue_dist
            target_to_cue_y /= target_to_cue_dist
            
            # Hit target with thin cut (aim slightly off-center)
            cut_factor = 0.3  # Thin cut
            ghost_x = target.x + target_to_cue_x * (target.radius + cue.radius) * 1.05 * (1 - cut_factor)
            ghost_y = target.y + target_to_cue_y * (target.radius + cue.radius) * 1.05 * (1 - cut_factor)
            
            angle = math.atan2(ghost_y - cue.y, ghost_x - cue.x)
            cue_end_x, cue_end_y = self._estimate_cue_ball_end(cue, target, ghost_x, ghost_y, angle)
            
            # Score this safety shot
            safety_score = 0
            
            # Maximize distance from cue ball to any pottable ball
            min_dist_to_pottable = float('inf')
            for other_ball in balls:
                if other_ball.potted or other_ball.ball_type == 'white' or other_ball == target:
                    continue
                dist = math.hypot(cue_end_x - other_ball.x, cue_end_y - other_ball.y)
                min_dist_to_pottable = min(min_dist_to_pottable, dist)
            
            if min_dist_to_pottable < float('inf'):
                safety_score += min_dist_to_pottable / 2  # Further is better
            
            # Minimize opponent's pot risk
            opponent_risk = self._opponent_pot_risk(cue_end_x, cue_end_y, balls, pockets)
            safety_score += (1.0 - opponent_risk) * 200  # Lower risk is better
            
            # Avoid leaving cue ball near pockets
            min_dist_to_pocket = min(math.hypot(cue_end_x - px, cue_end_y - py) for px, py in pockets)
            safety_score += min_dist_to_pocket / 3  # Further from pockets is better
            
            # Avoid cue ball scratches
            if self._cue_ball_scratch_risk(cue, target, ghost_x, ghost_y, angle, pockets):
                safety_score -= 500
            
            # Prefer leaving cue ball behind other balls (snooker)
            balls_blocking = 0
            for other_ball in balls:
                if other_ball.potted or other_ball.ball_type == 'white' or other_ball == target:
                    continue
                # Check if this ball could block a pot from cue position
                for pot_target in balls:
                    if pot_target.potted or pot_target.ball_type == 'white' or pot_target == other_ball:
                        continue
                    # Only consider blocking if pot_target is a valid next target
                    is_valid_next = False
                    if next_ball_on == "red" and pot_target.ball_type == 'red':
                        is_valid_next = True
                    elif next_ball_on == "color" and pot_target.ball_type in COLOR_SEQUENCE:
                        is_valid_next = True
                    elif pot_target.ball_type == next_ball_on:
                        is_valid_next = True
                    
                    if not is_valid_next:
                        continue
                    
                    for pocket in pockets:
                        # Check if other_ball is between cue_end and a line from pot_target to pocket
                        line_dist = self._point_to_line_distance(
                            other_ball.x, other_ball.y,
                            cue_end_x, cue_end_y,
                            pot_target.x, pot_target.y
                        )
                        if line_dist < other_ball.radius * 2:
                            balls_blocking += 1
                            break
                    if balls_blocking > 0:
                        break
            
            safety_score += balls_blocking * 40  # More blocking balls is better (increased from 30)
            
            # Evaluate position quality for next shot (but we want it to be bad for opponent)
            # Actually, we want to leave the cue ball in a position that makes it hard for opponent
            # So we want to minimize position quality from opponent's perspective
            # This is already handled by opponent_pot_risk, but we can add more
            
            if safety_score > best_safety_score:
                best_safety_score = safety_score
                # Use minimal power for safety (just enough to hit the ball)
                min_power = max(8, distance / 20)
                best_safety = {
                    'angle': angle,
                    'power': min_power,
                    'score': safety_score,
                    'type': 'safety'
                }
        
        return best_safety

    def _estimate_cue_ball_end(self, cue: Ball, target: Ball, ghost_x: float, ghost_y: float, angle: float) -> Tuple[float, float]:
        """Estimate cue ball end position after contacting the target ball."""
        n_x = ghost_x - target.x
        n_y = ghost_y - target.y
        n_len = math.hypot(n_x, n_y)
        if n_len <= 0.001:
            return ghost_x, ghost_y
        n_x /= n_len
        n_y /= n_len

        v_x = math.cos(angle)
        v_y = math.sin(angle)
        dot = v_x * n_x + v_y * n_y
        t_x = v_x - dot * n_x
        t_y = v_y - dot * n_y
        t_len = math.hypot(t_x, t_y)
        if t_len <= 0.05:
            return ghost_x, ghost_y  # Near full-ball hit; cue likely stops
        t_x /= t_len
        t_y /= t_len

        travel = cue.radius * (8 + t_len * 18)
        end_x = ghost_x + t_x * travel
        end_y = ghost_y + t_y * travel
        return end_x, end_y

    def _cue_ball_scratch_risk(self, cue: Ball, target: Ball, ghost_x: float, ghost_y: float,
                               angle: float, pockets: List[Tuple[int, int]]) -> bool:
        """Heuristic: avoid cue ball trajectory into a pocket after contact."""
        n_x = ghost_x - target.x
        n_y = ghost_y - target.y
        n_len = math.hypot(n_x, n_y)
        if n_len <= 0.001:
            return False
        n_x /= n_len
        n_y /= n_len

        v_x = math.cos(angle)
        v_y = math.sin(angle)
        dot = v_x * n_x + v_y * n_y
        t_x = v_x - dot * n_x
        t_y = v_y - dot * n_y
        t_len = math.hypot(t_x, t_y)
        if t_len <= 0.05:
            return False  # Near full-ball hit; cue likely stops
        t_x /= t_len
        t_y /= t_len

        pocket_radius = cue.radius * 2.2

        for px, py in pockets:
            dx = px - ghost_x
            dy = py - ghost_y
            proj = dx * t_x + dy * t_y
            if proj <= 0:
                continue
            perp = abs(dx * t_y - dy * t_x)
            if perp <= pocket_radius:
                return True
        return False

    def _opponent_pot_risk(self, cue_x: float, cue_y: float, balls: List[Ball],
                            pockets: List[Tuple[int, int]]) -> float:
        """Estimate how easy a pot would be for the opponent from this cue position."""
        best_risk = 0.0
        for target in balls:
            if target.potted or target.ball_type == 'white':
                continue
            for pocket in pockets:
                to_pocket_x = pocket[0] - target.x
                to_pocket_y = pocket[1] - target.y
                to_pocket_dist = math.hypot(to_pocket_x, to_pocket_y)
                if to_pocket_dist < 1:
                    continue
                to_pocket_x /= to_pocket_dist
                to_pocket_y /= to_pocket_dist

                ghost_x = target.x - to_pocket_x * (target.radius + target.radius) * 1.05
                ghost_y = target.y - to_pocket_y * (target.radius + target.radius) * 1.05

                cue_to_ghost = math.hypot(ghost_x - cue_x, ghost_y - cue_y)
                if cue_to_ghost < 1:
                    continue

                cue_angle = math.atan2(ghost_y - cue_y, ghost_x - cue_x)
                target_angle = math.atan2(to_pocket_y, to_pocket_x)
                cut_angle = abs(cue_angle - target_angle)
                if cut_angle > math.pi:
                    cut_angle = 2 * math.pi - cut_angle

                if cut_angle > 0.45:
                    continue

                risk = (1.0 - (cut_angle / 0.45)) * max(0.0, 1.0 - (cue_to_ghost / 420.0))
                best_risk = max(best_risk, risk)
        return best_risk

    def calculate_shot(self, cue: Ball, balls: List[Ball], ball_on: str, pockets: List[Tuple[int, int]],
                      reds_remaining: int = 15, ai_score: int = 0, opponent_score: int = 0,
                      table_bounds: Optional[Tuple[float, float, float, float]] = None) -> Tuple[float, float]:
        """Calculate best shot - ALWAYS prioritize potting with clearest path."""
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

        # Strategic context (used only for tiebreakers, not for pot vs safety decision)
        score_diff = ai_score - opponent_score
        is_behind = score_diff < -20
        is_ahead = score_diff > 20
        is_clearance = reds_remaining == 0
        
        # =====================================================================
        # TOP PRIORITY: Find the BEST pottable shot with clearest path
        # AI will ALWAYS try to pot if any clear shot exists
        # =====================================================================
        best_pot_shot = None
        best_pot_score = -float('inf')
        
        # Evaluate all direct pot shots - prioritize by:
        # 1. Clear path (not blocked)
        # 2. Easiest angle (straighter = better)
        # 3. Shortest distance
        # 4. Ball value (for colors)
        for target in valid:
            for pocket in pockets:
                shot = self._evaluate_shot(cue, target, pocket, balls, pockets, ball_on,
                                          reds_remaining, score_diff, is_behind, is_ahead,
                                          table_bounds)
                if shot and shot['type'] == 'direct' and not shot.get('blocked', False):
                    # Boost score significantly for clear, pottable shots
                    pot_score = shot['score']
                    # Extra bonus for clearer/easier shots
                    if pot_score > 0:
                        pot_score += 200  # Big bonus for any pottable shot
                    if pot_score > best_pot_score:
                        best_pot_score = pot_score
                        best_pot_shot = shot
        
        # Also check combination shots (but direct pots are preferred)
        for first_target in valid:
            for second_target in valid:
                if first_target == second_target or second_target.potted:
                    continue
                combination_shot = self._evaluate_combination_shot(cue, first_target, second_target,
                                                                  balls, pockets, ball_on,
                                                                  reds_remaining, score_diff,
                                                                  table_bounds)
                if combination_shot and not combination_shot.get('blocked', False):
                    combo_score = combination_shot['score']
                    if combo_score > 0:
                        combo_score += 100  # Bonus for pottable combo (less than direct)
                    if combo_score > best_pot_score:
                        best_pot_score = combo_score
                        best_pot_shot = combination_shot

        # =====================================================================
        # If ANY pottable shot exists with clear path, ALWAYS take it
        # Only consider safety if NO pot is possible
        # =====================================================================
        if best_pot_shot and best_pot_score > 0:
            # We have a pottable shot - use it!
            best_shot = best_pot_shot
            best_score = best_pot_score
        else:
            # No clear pot available - fall back to safety or best available
            best_shot = best_pot_shot  # May be None or a difficult shot
            best_score = best_pot_score if best_pot_shot else -float('inf')
            
            # Only now consider safety shots (when no pot is available)
            safety_shot = self._evaluate_safety_shot(cue, balls, pockets, ball_on, reds_remaining)
            if safety_shot:
                if best_shot is None or safety_shot['score'] > best_score:
                    best_shot = safety_shot
                    best_score = safety_shot['score']

        if best_shot:
            # Perfect players (skill = 1.0) have ZERO error
            # Other high-skill players have minimal error
            if self.skill >= 1.0:
                # PERFECT: 100% accuracy - no error at all
                error = 0.0
            elif self.skill > 0.95:
                # Near-perfect: ~99% accurate
                error = 0.0003
            elif self.skill > 0.9:
                # Excellent: ~98% accurate
                error = 0.0006
            else:
                # Good: ~97% accurate
                error = 0.001
            angle = best_shot['angle'] + (random.gauss(0, error) if error > 0 else 0)
            
            # Power calculation - AI uses optimal power with minimal variance
            power = best_shot['power'] * (30.0 / 90.0)  # Scale down to new max of 30
            
            # Slight power adjustment based on skill (high skill = optimal power)
            power_multiplier = 1.0 + (self.skill * 0.05)  # Small boost for skill
            power *= power_multiplier
            
            # Minimal style influence on power (1-2% max)
            if self.aggression > 0.6:
                power *= 1.0 + ((self.aggression - 0.6) * 0.03)
            if self.safety_bias > 0.6:
                power *= 1.0 - ((self.safety_bias - 0.6) * 0.02)

            # No random power variance - AI is precise
            
            return angle, max(8, min(30, power))

        # Fallback: aim at highest value valid ball with perfect accuracy
        target = max(valid, key=lambda b: b.value)
        angle = math.atan2(target.y - cue.y, target.x - cue.x)
        # Perfect players have ZERO error
        error = 0.0 if self.skill >= 1.0 else (0.0003 if self.skill > 0.95 else 0.0006)
        # Calculate optimal power for fallback shot
        distance = math.hypot(target.x - cue.x, target.y - cue.y)
        min_power = (20 + distance / 12) * (30.0 / 90.0)  # Scale to new max of 30
        min_power *= 1.0 + (self.skill * 0.05)  # Small skill boost
        return angle + (random.gauss(0, error) if error > 0 else 0), max(8, min(30, min_power))

    def _evaluate_shot(self, cue: Ball, target: Ball, pocket: Tuple[int, int],
                       balls: List[Ball], pockets: List[Tuple[int, int]],
                       ball_on: str = "red", reds_remaining: int = 15,
                       score_diff: int = 0, is_behind: bool = False, is_ahead: bool = False,
                       table_bounds: Optional[Tuple[float, float, float, float]] = None) -> Optional[dict]:
        """Evaluate a potential shot using ghost ball method with strategic context."""
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

        # Check if path is clear
        path_blocked = False
        for ball in balls:
            if ball.potted or ball == cue or ball == target:
                continue
            dist_to_line = self._point_to_line_distance(ball.x, ball.y, cue.x, cue.y, target.x, target.y)
            if dist_to_line < (ball.radius + cue.radius) * 1.3:
                path_blocked = True
                break
        
        if path_blocked:
            return None  # Path is blocked, skip this shot

        # Calculate cut angle for difficulty
        cue_to_target = math.atan2(target.y - cue.y, target.x - cue.x)
        target_to_pocket = math.atan2(to_pocket_y, to_pocket_x)
        cut_angle = abs(cue_to_target - target_to_pocket)
        if cut_angle > math.pi:
            cut_angle = 2 * math.pi - cut_angle

        # Score the shot (higher is better)
        score = 150  # Base score (increased from 100)
        
        # Difficulty penalties (more nuanced, adjusted by style)
        cut_difficulty = cut_angle / (math.pi / 2)  # Normalize to 0-1
        cut_penalty_scale = 1.0 - (self.aggression * 0.35) + (self.safety_bias * 0.2)
        cut_penalty_scale = max(0.6, min(1.4, cut_penalty_scale))
        score -= cut_difficulty * 40 * cut_penalty_scale
        score -= min(cue_to_ghost / 25, 30)  # Penalize long shots (capped)
        score -= min(to_pocket_dist / 40, 25)  # Penalize far pockets (capped)
        
        # Ball value (strongly prefer high-value balls, adjusted by style)
        value_multiplier = 8 * (1.0 + (self.pot_bias * 0.5) + (self.aggression * 0.2))
        score += target.value * value_multiplier
        
        # Strategic bonuses based on game state
        if target.ball_type == 'red':
            # Early game: prefer reds (build breaks)
            if reds_remaining > 8:
                score += 15
            # Late game: still prefer reds but less bonus
            elif reds_remaining > 0:
                score += 8
        else:
            # Colors: prefer high-value colors, especially in clearance
            if reds_remaining == 0:
                score += target.value * 3  # Extra bonus in clearance
            elif ball_on == "color":
                # After potting red, prefer colors that leave good position
                score += target.value * 2
        
        # Position play - evaluate cue ball end position for the next ball on
        cue_end_x, cue_end_y = self._estimate_cue_ball_end(cue, target, ghost_x, ghost_y, angle)
        next_ball_on = self._get_next_ball_on(ball_on, reds_remaining, target.ball_type)
        if next_ball_on and next_ball_on != "done":
            position_score = self._evaluate_position_quality(
                cue_end_x, cue_end_y, target, balls, pockets, next_ball_on, table_bounds
            )
            position_weight = 0.8 + (self.safety_bias * 0.2) - (self.aggression * 0.1)
            score += position_score * position_weight
        
        # Prefer shots that leave good position for next shot
        if cut_angle < 0.25:  # Very straight shots (good position control)
            score += 15
        elif cut_angle < 0.4:  # Moderately straight
            score += 8

        # Avoid cue ball scratches (critical)
        if self._cue_ball_scratch_risk(cue, target, ghost_x, ghost_y, angle, pockets):
            score -= 1500  # Massive penalty

        # Safety consideration - avoid leaving easy pots for opponent
        leave_risk = self._opponent_pot_risk(cue_end_x, cue_end_y, balls, pockets)
        leave_risk_penalty = 250 * (1.0 + (self.safety_bias * 0.6) - (self.aggression * 0.3))
        score -= leave_risk * leave_risk_penalty
        
        # Strategic adjustments based on score
        if is_behind:
            # When behind, take more risks (less penalty for difficult shots)
            if cut_angle < 0.6:
                score += 20 + (self.aggression * 10)
        elif is_ahead:
            # When ahead, prefer safer shots (more penalty for risky shots)
            if cut_angle > 0.4:
                score -= 15 + (self.safety_bias * 10)
            # Prefer shots that leave safe position
            if leave_risk < 0.2:
                score += 25 + (self.safety_bias * 10)

        # Power calculation - more precise
        total_distance = cue_to_ghost + to_pocket_dist
        # Calculate optimal power (not just minimum)
        # Account for cut angle (thinner cuts need more power)
        cut_power_factor = 1.0 + (cut_angle * 0.3)  # Thinner cuts need more power
        min_power = 18 + (total_distance / 11) * cut_power_factor
        power = min_power

        return {'angle': angle, 'power': power, 'score': score, 'type': 'direct'}
    
    def _evaluate_combination_shot(self, cue: Ball, first_target: Ball, second_target: Ball,
                                   all_balls: List[Ball], pockets: List[Tuple[int, int]],
                                   ball_on: str = "red", reds_remaining: int = 15,
                                   score_diff: int = 0,
                                   table_bounds: Optional[Tuple[float, float, float, float]] = None) -> Optional[dict]:
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
                combo_score = 140  # Base score (increased from 100)
                
                # Difficulty penalties (more nuanced, adjusted by style)
                angle_diff_normalized = angle_diff / (math.pi / 3)  # Normalize to 0-1
                combo_cut_scale = 1.0 - (self.aggression * 0.3) + (self.safety_bias * 0.2)
                combo_cut_scale = max(0.6, min(1.4, combo_cut_scale))
                combo_score -= angle_diff_normalized * 35 * combo_cut_scale
                combo_score -= min(cue_to_ghost / 20, 30)  # Penalize long first shot (capped)
                combo_score -= min(to_second_dist / 35, 25)  # Penalize long second shot (capped)
                combo_score -= min(to_pocket_dist / 45, 20)  # Penalize far pocket (capped)
                
                # Ball value (strongly prefer high-value second ball)
                combo_value_multiplier = 10 * (1.0 + (self.pot_bias * 0.5) + (self.aggression * 0.2))
                combo_score += second_target.value * combo_value_multiplier
                
                # Bonus for combination shots (they're impressive and show skill!)
                combo_score += 25 + (self.combo_bias * 30) - (self.safety_bias * 10)
                
                # Prefer shots where second ball is closer to pocket
                if to_pocket_dist < 100:
                    combo_score += 20  # Increased from 10
                
                # Position play for combination shots
                cue_end_x, cue_end_y = self._estimate_cue_ball_end(cue, first_target, cue_ghost_x, cue_ghost_y, angle)
                next_ball_on = self._get_next_ball_on(ball_on, reds_remaining, second_target.ball_type)
                if next_ball_on and next_ball_on != "done":
                    position_score = self._evaluate_position_quality(
                        cue_end_x, cue_end_y, second_target, all_balls, pockets, next_ball_on, table_bounds
                    )
                    combo_position_weight = 0.6 + (self.safety_bias * 0.2) - (self.aggression * 0.1)
                    combo_score += position_score * combo_position_weight

                # Avoid cue ball scratches (critical)
                if self._cue_ball_scratch_risk(cue, first_target, cue_ghost_x, cue_ghost_y, angle, pockets):
                    combo_score -= 1500  # Massive penalty

                # Favor safety: avoid leaving easy pots for the opponent
                leave_risk = self._opponent_pot_risk(cue_end_x, cue_end_y, all_balls, pockets)
                combo_leave_penalty = 250 * (1.0 + (self.safety_bias * 0.6) - (self.aggression * 0.3))
                combo_score -= leave_risk * combo_leave_penalty
                
                # Strategic adjustments
                if score_diff < -20:  # Behind
                    # When behind, combinations can be worth the risk
                    if second_target.value >= 5:  # High-value target
                        combo_score += 15 + (self.aggression * 10)
                elif score_diff > 20:  # Ahead
                    # When ahead, be more cautious with combinations
                    if angle_diff > 0.3:  # Difficult combination
                        combo_score -= 20 + (self.safety_bias * 10)
                
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
        self.ai = AIPlayer(
            skill=1.0,  # PERFECT player
            aggression=0.55,
            safety_bias=0.55,
            combo_bias=0.45,
            pot_bias=0.6,
        )  # Perfect AI player - never misses
        
        # Tournament AI players - ALL PERFECT
        self.ai_louis = AIPlayer(
            skill=1.0,  # PERFECT player
            aggression=0.4,
            safety_bias=0.7,
            combo_bias=0.35,
            pot_bias=0.5,
        )  # Mst. Louis Sonic - perfect tactical player
        self.ai_bradley = AIPlayer(
            skill=1.0,  # PERFECT player
            aggression=0.75,
            safety_bias=0.35,
            combo_bias=0.7,
            pot_bias=0.8,
        )  # Gen. Bradley Sonic - perfect aggressive finisher
        
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

        # Sound effects
        self._load_sounds()
        
        # Sound state tracking
        self.collision_count_this_frame = 0
        self.last_collision_time = 0
        
        # Spin control UI state
        self.spin_control_radius = int(35 * self.scale)  # Size of the spin control circle
        self.spin_dot_radius = int(8 * self.scale)  # Size of the draggable dot
        self.spin_dot_x = 0.0  # Dot position relative to center (-1 to 1)
        self.spin_dot_y = 0.0  # Dot position relative to center (-1 to 1)
        self.spin_dragging = False  # Is the user dragging the spin dot?
        self.spin_control_rect = pygame.Rect(0, 0, 0, 0)  # Will be set in draw

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
        
        # Ball spots (relative to window) - proper snooker positions
        # Using proportions of table width for correct positioning:
        # - Blue: center of table (50%)
        # - Pink: between blue and black (70% along)
        # - Black: near far cushion (92% along)
        blue_x = table_x + table_width // 2
        pink_x = table_x + int(table_width * 0.70)
        black_x = table_x + int(table_width * 0.92)
        
        self.spots = {
            'yellow': (self.baulk_x, self.d_center_y - self.d_radius),
            'green': (self.baulk_x, self.d_center_y + self.d_radius),
            'brown': (self.baulk_x, self.d_center_y),
            'blue': (blue_x, self.d_center_y),
            'pink': (pink_x, self.d_center_y),
            'black': (black_x, self.d_center_y),
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

    def _load_sounds(self) -> None:
        """Load sound effects for the snooker game."""
        self.sounds = {}
        
        # Define sound files
        sound_files = {
            'cue_hit': 'cue-ball-hit-by-cue.wav',
            'ball_hit': 'ball-hits-ball.wav',
            'multi_hit': 'multi-ball-hit.wav',
            'pot': 'applause-ball-in-pocket.wav',
            'foul': 'miss-foul.wav',
        }
        
        # Try to load each sound
        for sound_name, filename in sound_files.items():
            try:
                # Build path to audio folder inside Snooker folder
                script_dir = os.path.dirname(os.path.abspath(__file__))
                sound_path = os.path.join(script_dir, 'audio', filename)
                
                if os.path.exists(sound_path):
                    self.sounds[sound_name] = pygame.mixer.Sound(sound_path)
                    # Set default volumes
                    if sound_name == 'cue_hit':
                        self.sounds[sound_name].set_volume(0.6)
                    elif sound_name == 'ball_hit':
                        self.sounds[sound_name].set_volume(0.4)
                    elif sound_name == 'multi_hit':
                        self.sounds[sound_name].set_volume(0.5)
                    elif sound_name == 'pot':
                        self.sounds[sound_name].set_volume(0.7)
                    elif sound_name == 'foul':
                        self.sounds[sound_name].set_volume(0.6)
                else:
                    self.sounds[sound_name] = None
            except Exception as e:
                print(f"Warning: Failed to load sound {filename}: {e}")
                self.sounds[sound_name] = None

    def _play_sound(self, sound_name: str) -> None:
        """Play a sound effect if it's loaded and radio is not playing."""
        # Don't play game sounds if radio is playing (optional - you can remove this check)
        # if self.get_radio_music():
        #     return
        
        if sound_name in self.sounds and self.sounds[sound_name] is not None:
            try:
                self.sounds[sound_name].play()
            except Exception:
                pass  # Silently fail if sound can't be played

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
        # Red triangle apex is just behind (towards black) the pink spot
        # Pink is at 70% of table width, so reds start at ~72%
        table_width = self.table_rect.width
        start_x = self.table_rect.x + int(table_width * 0.72)
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
        
        # Reset spin control
        self.spin_dot_x = 0.0
        self.spin_dot_y = 0.0
        self.spin_dragging = False

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
        
        # AI studying behavior - reset for new match
        self.ai_studying = False
        self.ai_study_timer = 0
        self.ai_potential_shots = []
        self.ai_current_study_index = 0
        self.ai_study_angle = 0
        self.ai_final_shot = None
        self.ai_simulated_results = []  # Results from simulating all shots
        self.ai_best_simulated_shot = None  # The shot that scored most points in simulation

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

    def calculate_ai_potential_shots(self) -> List[dict]:
        """
        Calculate all potential shots the AI could consider, for visual study effect.
        
        CRITICAL: AI should prioritize EASIEST LEGAL POT first!
        Shot difficulty (ease of pot) should heavily outweigh ball value.
        """
        if not self.cue_ball:
            return []
        
        potential_shots = []
        
        # Get valid target balls based on current ball_on
        if self.ball_on == "red":
            valid_targets = [b for b in self.balls if not b.potted and b.ball_type == 'red']
        elif self.ball_on == "color":
            valid_targets = [b for b in self.balls if not b.potted and b.ball_type in COLOR_SEQUENCE]
        else:
            # Specific color required (clearance)
            valid_targets = [b for b in self.balls if not b.potted and b.ball_type == self.ball_on]
        
        if not valid_targets:
            valid_targets = [b for b in self.balls if not b.potted and b.ball_type != 'white']
        
        # Evaluate each target ball to each pocket
        for target in valid_targets:
            for pocket in self.pockets:
                # Calculate angle from cue to target via ghost ball position
                to_pocket_x = pocket[0] - target.x
                to_pocket_y = pocket[1] - target.y
                to_pocket_dist = math.hypot(to_pocket_x, to_pocket_y)
                
                if to_pocket_dist < 1:
                    continue
                
                # Normalize
                to_pocket_x /= to_pocket_dist
                to_pocket_y /= to_pocket_dist
                
                # Ghost ball position
                ghost_x = target.x - to_pocket_x * (target.radius + self.cue_ball.radius) * 1.05
                ghost_y = target.y - to_pocket_y * (target.radius + self.cue_ball.radius) * 1.05
                
                # Angle from cue to ghost
                angle = math.atan2(ghost_y - self.cue_ball.y, ghost_x - self.cue_ball.x)
                cue_to_ghost = math.hypot(ghost_x - self.cue_ball.x, ghost_y - self.cue_ball.y)
                
                # Check if path is clear (cue ball to target ball)
                path_blocked = False
                for ball in self.balls:
                    if ball.potted or ball == self.cue_ball or ball == target:
                        continue
                    # Point to line distance
                    ax, ay = self.cue_ball.x, self.cue_ball.y
                    bx, by = target.x, target.y
                    px, py = ball.x, ball.y
                    ab_x, ab_y = bx - ax, by - ay
                    ap_x, ap_y = px - ax, py - ay
                    ab_len_sq = ab_x * ab_x + ab_y * ab_y
                    if ab_len_sq > 0:
                        t = max(0, min(1, (ap_x * ab_x + ap_y * ab_y) / ab_len_sq))
                        closest_x = ax + t * ab_x
                        closest_y = ay + t * ab_y
                        dist_to_line = math.hypot(px - closest_x, py - closest_y)
                        if dist_to_line < (ball.radius + self.cue_ball.radius) * 1.1:
                            path_blocked = True
                            break
                
                # Also check if path from target to pocket is clear
                pocket_path_blocked = False
                for ball in self.balls:
                    if ball.potted or ball == self.cue_ball or ball == target:
                        continue
                    ax, ay = target.x, target.y
                    bx, by = pocket[0], pocket[1]
                    px, py = ball.x, ball.y
                    ab_x, ab_y = bx - ax, by - ay
                    ap_x, ap_y = px - ax, py - ay
                    ab_len_sq = ab_x * ab_x + ab_y * ab_y
                    if ab_len_sq > 0:
                        t = max(0, min(1, (ap_x * ab_x + ap_y * ab_y) / ab_len_sq))
                        closest_x = ax + t * ab_x
                        closest_y = ay + t * ab_y
                        dist_to_line = math.hypot(px - closest_x, py - closest_y)
                        if dist_to_line < (ball.radius + target.radius) * 1.1:
                            pocket_path_blocked = True
                            break
                
                # Calculate shot difficulty/score
                # CRITICAL: Use proper cut angle calculation
                # Cut angle = angle between (cue->target) and (target->pocket)
                cue_to_target_angle = math.atan2(target.y - self.cue_ball.y, target.x - self.cue_ball.x)
                target_to_pocket_angle = math.atan2(to_pocket_y, to_pocket_x)
                
                # The cut angle is how much the cue ball needs to "cut" the object ball
                cut_angle = abs(cue_to_target_angle - target_to_pocket_angle)
                if cut_angle > math.pi:
                    cut_angle = 2 * math.pi - cut_angle
                # Adjust: A straight shot (cue-ball-pocket aligned) should have cut_angle near pi
                # Convert so that 0 = straight in, higher = harder cut
                if cut_angle > math.pi / 2:
                    cut_angle = math.pi - cut_angle
                
                # =====================================================================
                # SCORING: PRIORITIZE EASE OF POT - Ball value is secondary tiebreaker
                # =====================================================================
                
                # Skip blocked shots entirely
                if path_blocked or pocket_path_blocked:
                    score = -1000  # Severely penalize blocked shots
                elif cut_angle > 1.2:  # ~70 degrees - very difficult cut
                    score = -500  # Still penalize heavily but consider if no alternatives
                else:
                    # BASE SCORE: Start high, subtract for difficulty
                    score = 500
                    
                    # EASE OF POT is the PRIMARY factor (worth up to 400 points):
                    
                    # 1. Cut angle penalty - HEAVILY penalize difficult cuts (0-200 points penalty)
                    # Straight shot (0 rad) = 0 penalty, 60 deg cut (1.05 rad) = 200 penalty
                    cut_penalty = (cut_angle / 1.2) * 200
                    score -= cut_penalty
                    
                    # 2. Distance penalty - closer is easier (0-100 points penalty)
                    # Max penalty at 400+ pixels distance
                    distance_penalty = min(cue_to_ghost / 400, 1.0) * 100
                    score -= distance_penalty
                    
                    # 3. Ball-to-pocket distance penalty (0-50 points penalty)
                    # Balls already near pocket are easier to pot
                    pocket_distance_penalty = min(to_pocket_dist / 300, 1.0) * 50
                    score -= pocket_distance_penalty
                    
                    # 4. BONUS for very easy shots (straight-in, close range)
                    if cut_angle < 0.2 and cue_to_ghost < 150:  # Nearly straight, close shot
                        score += 100  # Big bonus for "gimme" shots
                    elif cut_angle < 0.4 and cue_to_ghost < 200:  # Easy shot
                        score += 50
                    elif cut_angle < 0.3:  # Straight shot any distance
                        score += 30
                    
                    # SECONDARY: Ball value is only a small tiebreaker (0-7 points)
                    # This prevents high-value balls from overriding ease of pot
                    value_bonus = target.value  # Just 1-7 points, not 10-70
                    score += value_bonus
                
                potential_shots.append({
                    'target': target,
                    'pocket': pocket,
                    'angle': angle,
                    'score': score,
                    'distance': cue_to_ghost,
                    'cut_angle': cut_angle,
                    'blocked': path_blocked or pocket_path_blocked
                })
        
        # Sort by score (easiest pots first!)
        potential_shots.sort(key=lambda x: x['score'], reverse=True)
        
        # Add safety shot options for when no good pots exist
        # Safety: just roll toward the target ball (legal hit, minimal movement)
        if valid_targets:
            for target in valid_targets[:3]:  # Top 3 legal targets for safety
                # Angle directly at target (just to make legal contact)
                safety_angle = math.atan2(target.y - self.cue_ball.y, target.x - self.cue_ball.x)
                dist_to_target = math.hypot(target.x - self.cue_ball.x, target.y - self.cue_ball.y)
                
                # Check if path is clear
                path_blocked = False
                for ball in self.balls:
                    if ball.potted or ball == self.cue_ball or ball == target:
                        continue
                    ax, ay = self.cue_ball.x, self.cue_ball.y
                    bx, by = target.x, target.y
                    px, py = ball.x, ball.y
                    ab_x, ab_y = bx - ax, by - ay
                    ap_x, ap_y = px - ax, py - ay
                    ab_len_sq = ab_x * ab_x + ab_y * ab_y
                    if ab_len_sq > 0:
                        t = max(0, min(1, (ap_x * ab_x + ap_y * ab_y) / ab_len_sq))
                        closest_x = ax + t * ab_x
                        closest_y = ay + t * ab_y
                        dist_to_line = math.hypot(px - closest_x, py - closest_y)
                        if dist_to_line < (ball.radius + self.cue_ball.radius) * 1.1:
                            path_blocked = True
                            break
                
                if not path_blocked:
                    potential_shots.append({
                        'target': target,
                        'pocket': None,  # No specific pocket - safety shot
                        'angle': safety_angle,
                        'score': 10,  # Low score but legal
                        'distance': dist_to_target,
                        'cut_angle': 0,
                        'blocked': False,
                        'is_safety': True
                    })
        
        # Return more shots to ensure we test easy pots even if they score lower
        # Filter out severely blocked shots first
        viable_shots = [s for s in potential_shots if s['score'] > -500]
        if len(viable_shots) < 5:
            # If not enough viable shots, include some difficult ones
            viable_shots = potential_shots[:12]
        
        return viable_shots[:12]  # Study up to 12 potential shots (increased from 8)

    def simulate_shot_with_angle_power(self, angle: float, power: float, target_ball: Ball = None) -> dict:
        """
        Simulate a shot at a specific angle and power.
        This is the core simulation that runs physics in the background.
        
        The AI uses this to "mentally play" every possible shot and find the best one.
        
        CRITICAL: This must accurately track:
        1. The cue ball trajectory
        2. The OBJECT BALL trajectory after being hit (this is what scores!)
        3. Whether the object ball enters a pocket
        4. Whether it's a legal shot (correct ball hit first)
        
        Returns complete shot outcome for AI decision making.
        """
        if not self.cue_ball:
            return {'points': 0, 'potted': [], 'foul': True, 'foul_points': 4, 'opponent_points': 4}
        
        # Save original ball states - we'll restore these after simulation
        original_states = []
        for ball in self.balls:
            original_states.append({
                'ball': ball,
                'x': ball.x,
                'y': ball.y,
                'vx': ball.vx,
                'vy': ball.vy,
                'potted': ball.potted,
                'top_spin': ball.top_spin,
                'side_spin': ball.side_spin,
                'is_sliding': ball.is_sliding
            })
        
        # Apply the shot to cue ball
        speed = power * 2.0
        self.cue_ball.vx = math.cos(angle) * speed
        self.cue_ball.vy = math.sin(angle) * speed
        self.cue_ball.top_spin = 0
        self.cue_ball.side_spin = 0
        self.cue_ball.is_sliding = True
        
        # Track first ball hit by cue ball (for foul detection)
        first_ball_hit = None
        
        # Track object ball trajectories for debugging/verification
        object_ball_potted_in_pocket = None
        
        # Run physics simulation - MUST match real game physics exactly!
        max_steps = 1000  # Enough for any shot to complete
        dt = 1/60.0
        
        for step in range(max_steps):
            # Check if all balls stopped
            any_moving = False
            for ball in self.balls:
                if not ball.potted and (abs(ball.vx) > 0.1 or abs(ball.vy) > 0.1):
                    any_moving = True
                    break
            
            if not any_moving and step > 10:
                break
            
            # Update ball positions with EXACT friction matching real game
            for ball in self.balls:
                if ball.potted:
                    continue
                
                spd = math.hypot(ball.vx, ball.vy)
                if spd > 0.05:
                    # Use IDENTICAL friction model to real game
                    if spd < 15:
                        speed_factor = spd / 15.0
                        base_friction = 0.909 + (speed_factor * 0.0819)
                    elif spd < 30:
                        speed_factor = (spd - 15) / 15.0
                        base_friction = 0.9909 + (speed_factor * 0.00805)
                    else:
                        base_friction = 0.99895
                    friction = adjust_friction(base_friction)
                    ball.vx *= friction
                    ball.vy *= friction
                else:
                    ball.vx = ball.vy = 0
                
                ball.x += ball.vx * dt * 60
                ball.y += ball.vy * dt * 60
            
            # Resolve collisions
            for i, b1 in enumerate(self.balls):
                if b1.potted:
                    continue
                
                # Cushion collisions - match real game restitution
                cushion_restitution = 0.82
                if b1.x - b1.radius < self.table_rect.left:
                    b1.x = self.table_rect.left + b1.radius
                    b1.vx = abs(b1.vx) * cushion_restitution
                elif b1.x + b1.radius > self.table_rect.right:
                    b1.x = self.table_rect.right - b1.radius
                    b1.vx = -abs(b1.vx) * cushion_restitution
                if b1.y - b1.radius < self.table_rect.top:
                    b1.y = self.table_rect.top + b1.radius
                    b1.vy = abs(b1.vy) * cushion_restitution
                elif b1.y + b1.radius > self.table_rect.bottom:
                    b1.y = self.table_rect.bottom - b1.radius
                    b1.vy = -abs(b1.vy) * cushion_restitution
                
                # Ball-to-ball collisions
                for b2 in self.balls[i + 1:]:
                    if b2.potted:
                        continue
                    dx = b2.x - b1.x
                    dy = b2.y - b1.y
                    dist = math.hypot(dx, dy)
                    min_dist = b1.radius + b2.radius
                    
                    if dist < min_dist and dist > 0:
                        nx, ny = dx / dist, dy / dist
                        overlap = min_dist - dist
                        b1.x -= nx * overlap / 2
                        b1.y -= ny * overlap / 2
                        b2.x += nx * overlap / 2
                        b2.y += ny * overlap / 2
                        
                        rel_vx = b1.vx - b2.vx
                        rel_vy = b1.vy - b2.vy
                        v_dot_n = rel_vx * nx + rel_vy * ny
                        if v_dot_n > 0:
                            # Energy transfer
                            energy_preservation = 0.96
                            b1.vx -= v_dot_n * nx * energy_preservation
                            b1.vy -= v_dot_n * ny * energy_preservation
                            b2.vx += v_dot_n * nx * energy_preservation
                            b2.vy += v_dot_n * ny * energy_preservation
                            
                            # Track first ball hit by cue ball
                            if first_ball_hit is None:
                                if b1.ball_type == 'white':
                                    first_ball_hit = b2
                                elif b2.ball_type == 'white':
                                    first_ball_hit = b1
                
                # Pocket detection - CRITICAL for scoring
                pocket_size = int(24 * self.scale)
                for pocket_idx, (px, py) in enumerate(self.pockets):
                    dist_to_pocket = math.hypot(b1.x - px, b1.y - py)
                    if dist_to_pocket < pocket_size + b1.radius:
                        b1.potted = True
                        b1.vx = b1.vy = 0
                        # Track which pocket the object ball went into
                        if b1.ball_type != 'white' and object_ball_potted_in_pocket is None:
                            object_ball_potted_in_pocket = pocket_idx
                        break
        
        # =====================================================================
        # CALCULATE RESULTS - Determine score and fouls
        # =====================================================================
        potted_balls = []
        ai_points = 0
        foul = False
        foul_points = 0
        
        # Check what was potted
        for state in original_states:
            ball = state['ball']
            if ball.potted and not state['potted']:
                potted_balls.append(ball)
        
        # FOUL CHECK 1: Cue ball potted (scratch)
        cue_potted = any(b.ball_type == 'white' for b in potted_balls)
        if cue_potted:
            foul = True
            foul_points = max(foul_points, 4)
        
        # FOUL CHECK 2: No ball hit
        if first_ball_hit is None:
            foul = True
            if self.ball_on in BALL_VALUES:
                foul_points = max(foul_points, max(4, BALL_VALUES[self.ball_on]))
            else:
                foul_points = max(foul_points, 4)
        
        # FOUL CHECK 3: Wrong ball hit first
        if first_ball_hit and not foul:
            hit_type = first_ball_hit.ball_type
            if self.ball_on == "red" and hit_type != "red":
                foul = True
                foul_points = max(foul_points, max(4, first_ball_hit.value))
            elif self.ball_on == "color" and hit_type == "red":
                foul = True
                foul_points = max(foul_points, 4)
            elif self.ball_on not in ["red", "color"] and hit_type != self.ball_on:
                # Clearance - must hit specific color
                foul = True
                foul_points = max(foul_points, max(4, BALL_VALUES.get(hit_type, 4), BALL_VALUES.get(self.ball_on, 4)))
        
        # FOUL CHECK 4: Potted wrong ball
        object_balls_potted = [b for b in potted_balls if b.ball_type != 'white']
        if not foul and object_balls_potted:
            if self.ball_on == "red":
                wrong_potted = [b for b in object_balls_potted if b.ball_type != 'red']
                if wrong_potted:
                    foul = True
                    foul_points = max(foul_points, max(4, max(b.value for b in wrong_potted)))
            elif self.ball_on == "color":
                reds_potted = [b for b in object_balls_potted if b.ball_type == 'red']
                if reds_potted:
                    foul = True
                    foul_points = max(foul_points, 4)
                elif len([b for b in object_balls_potted if b.ball_type in COLOR_SEQUENCE]) > 1:
                    foul = True
                    foul_points = max(foul_points, max(b.value for b in object_balls_potted))
            else:
                # Clearance - must pot specific color
                wrong_potted = [b for b in object_balls_potted if b.ball_type != self.ball_on]
                if wrong_potted:
                    foul = True
                    foul_points = max(foul_points, max(4, BALL_VALUES.get(self.ball_on, 4), max(b.value for b in wrong_potted)))
        
        # Calculate AI points (only if no foul)
        if not foul:
            for ball in object_balls_potted:
                if self.ball_on == 'red' and ball.ball_type == 'red':
                    ai_points += 1
                elif self.ball_on == 'color' and ball.ball_type in COLOR_SEQUENCE:
                    ai_points += ball.value
                elif ball.ball_type == self.ball_on:  # Clearance
                    ai_points += ball.value
        
        # Restore all original ball states
        for state in original_states:
            ball = state['ball']
            ball.x = state['x']
            ball.y = state['y']
            ball.vx = state['vx']
            ball.vy = state['vy']
            ball.potted = state['potted']
            ball.top_spin = state['top_spin']
            ball.side_spin = state['side_spin']
            ball.is_sliding = state['is_sliding']
        
        return {
            'points': ai_points,
            'potted': [b.ball_type for b in potted_balls],  # List of ball types potted
            'potted_count': len(object_balls_potted),
            'foul': foul,
            'foul_points': foul_points,
            'opponent_points': foul_points if foul else 0,
            'angle': angle,
            'power': power,
            'target_ball': target_ball,
            'first_hit': first_ball_hit.ball_type if first_ball_hit else None,
            'pocket_used': object_ball_potted_in_pocket
        }

    def simulate_shot(self, shot: dict, power: float = 20.0) -> dict:
        """
        Wrapper to simulate a shot from a shot dict (for compatibility).
        Calls the core simulation with the shot's angle.
        """
        angle = shot.get('angle', 0)
        target = shot.get('target')
        result = self.simulate_shot_with_angle_power(angle, power, target)
        result['shot'] = shot  # Include original shot data
        return result

    def find_best_scoring_shot(self) -> dict:
        """
        AI "MENTALLY PLAYS" EVERY POSSIBLE SHOT before making a decision.
        
        This method:
        1. Generates ALL possible legal shot combinations (ball + pocket + power)
        2. Simulates each one in the background (hidden from player)
        3. Records the outcome of every shot
        4. Returns the BEST legal scoring shot
        
        The AI focuses on:
        - LEGAL shots only (hitting correct ball first)
        - HIGH SCORING (most points per shot)
        - EASIEST pots (when scores are equal, prefer easier shots)
        
        Returns the complete shot data needed to "replay" it for the player.
        """
        if not self.cue_ball:
            return None
        
        # Get valid target balls based on ball_on
        if self.ball_on == "red":
            valid_targets = [b for b in self.balls if not b.potted and b.ball_type == 'red']
        elif self.ball_on == "color":
            valid_targets = [b for b in self.balls if not b.potted and b.ball_type in COLOR_SEQUENCE]
        else:
            # Clearance - specific color required
            valid_targets = [b for b in self.balls if not b.potted and b.ball_type == self.ball_on]
        
        if not valid_targets:
            # Fallback to any non-white ball
            valid_targets = [b for b in self.balls if not b.potted and b.ball_type != 'white']
        
        if not valid_targets:
            return None
        
        # =====================================================================
        # PHASE 1: Generate ALL possible shot combinations
        # =====================================================================
        all_shots_to_test = []
        
        for target in valid_targets:
            for pocket in self.pockets:
                # Calculate the ghost ball position (where cue ball needs to hit target)
                to_pocket_x = pocket[0] - target.x
                to_pocket_y = pocket[1] - target.y
                to_pocket_dist = math.hypot(to_pocket_x, to_pocket_y)
                
                if to_pocket_dist < 1:
                    continue
                
                # Normalize direction to pocket
                to_pocket_x /= to_pocket_dist
                to_pocket_y /= to_pocket_dist
                
                # Ghost ball position - where cue ball should contact target
                ghost_x = target.x - to_pocket_x * (target.radius + self.cue_ball.radius) * 1.05
                ghost_y = target.y - to_pocket_y * (target.radius + self.cue_ball.radius) * 1.05
                
                # Angle from cue ball to ghost ball
                angle = math.atan2(ghost_y - self.cue_ball.y, ghost_x - self.cue_ball.x)
                
                # Distance from cue ball to target (for power calculation)
                cue_to_target = math.hypot(target.x - self.cue_ball.x, target.y - self.cue_ball.y)
                
                # Calculate cut angle (difficulty measure)
                cue_to_target_angle = math.atan2(target.y - self.cue_ball.y, target.x - self.cue_ball.x)
                target_to_pocket_angle = math.atan2(to_pocket_y, to_pocket_x)
                cut_angle = abs(cue_to_target_angle - target_to_pocket_angle)
                if cut_angle > math.pi:
                    cut_angle = 2 * math.pi - cut_angle
                if cut_angle > math.pi / 2:
                    cut_angle = math.pi - cut_angle
                
                # Skip impossibly difficult shots (> 80 degree cut)
                if cut_angle > 1.4:
                    continue
                
                # Check if path is blocked
                path_blocked = False
                for ball in self.balls:
                    if ball.potted or ball == self.cue_ball or ball == target:
                        continue
                    # Check cue-to-target path
                    ax, ay = self.cue_ball.x, self.cue_ball.y
                    bx, by = target.x, target.y
                    px, py = ball.x, ball.y
                    ab_x, ab_y = bx - ax, by - ay
                    ap_x, ap_y = px - ax, py - ay
                    ab_len_sq = ab_x * ab_x + ab_y * ab_y
                    if ab_len_sq > 0:
                        t = max(0, min(1, (ap_x * ab_x + ap_y * ab_y) / ab_len_sq))
                        closest_x = ax + t * ab_x
                        closest_y = ay + t * ab_y
                        dist_to_line = math.hypot(px - closest_x, py - closest_y)
                        if dist_to_line < (ball.radius + self.cue_ball.radius) * 1.2:
                            path_blocked = True
                            break
                
                if path_blocked:
                    continue
                
                # Also check target-to-pocket path
                for ball in self.balls:
                    if ball.potted or ball == self.cue_ball or ball == target:
                        continue
                    ax, ay = target.x, target.y
                    bx, by = pocket[0], pocket[1]
                    px, py = ball.x, ball.y
                    ab_x, ab_y = bx - ax, by - ay
                    ap_x, ap_y = px - ax, py - ay
                    ab_len_sq = ab_x * ab_x + ab_y * ab_y
                    if ab_len_sq > 0:
                        t = max(0, min(1, (ap_x * ab_x + ap_y * ab_y) / ab_len_sq))
                        closest_x = ax + t * ab_x
                        closest_y = ay + t * ab_y
                        dist_to_line = math.hypot(px - closest_x, py - closest_y)
                        if dist_to_line < (ball.radius + target.radius) * 1.2:
                            path_blocked = True
                            break
                
                if path_blocked:
                    continue
                
                # Calculate power levels to test based on distance
                total_distance = cue_to_target + to_pocket_dist
                if total_distance < 150:
                    power_levels = [10, 12, 14, 16]
                elif total_distance < 300:
                    power_levels = [14, 16, 18, 20, 22]
                elif total_distance < 450:
                    power_levels = [18, 20, 22, 25, 28]
                else:
                    power_levels = [22, 25, 28, 30]
                
                all_shots_to_test.append({
                    'target': target,
                    'pocket': pocket,
                    'angle': angle,
                    'distance': cue_to_target,
                    'cut_angle': cut_angle,
                    'to_pocket_dist': to_pocket_dist,
                    'power_levels': power_levels,
                    'ball_value': target.value
                })
        
        # Also add safety shots (just hitting the ball legally)
        for target in valid_targets[:5]:  # Top 5 closest legal targets
            safety_angle = math.atan2(target.y - self.cue_ball.y, target.x - self.cue_ball.x)
            dist_to_target = math.hypot(target.x - self.cue_ball.x, target.y - self.cue_ball.y)
            
            # Check if direct path is clear
            path_blocked = False
            for ball in self.balls:
                if ball.potted or ball == self.cue_ball or ball == target:
                    continue
                ax, ay = self.cue_ball.x, self.cue_ball.y
                bx, by = target.x, target.y
                px, py = ball.x, ball.y
                ab_x, ab_y = bx - ax, by - ay
                ap_x, ap_y = px - ax, py - ay
                ab_len_sq = ab_x * ab_x + ab_y * ab_y
                if ab_len_sq > 0:
                    t = max(0, min(1, (ap_x * ab_x + ap_y * ab_y) / ab_len_sq))
                    closest_x = ax + t * ab_x
                    closest_y = ay + t * ab_y
                    dist_to_line = math.hypot(px - closest_x, py - closest_y)
                    if dist_to_line < (ball.radius + self.cue_ball.radius) * 1.2:
                        path_blocked = True
                        break
            
            if not path_blocked:
                all_shots_to_test.append({
                    'target': target,
                    'pocket': None,
                    'angle': safety_angle,
                    'distance': dist_to_target,
                    'cut_angle': 0,
                    'to_pocket_dist': 0,
                    'power_levels': [8, 10, 12],  # Low power for safety
                    'ball_value': target.value,
                    'is_safety': True
                })
        
        # =====================================================================
        # PHASE 2: Simulate EVERY shot and record results
        # =====================================================================
        all_results = []
        
        for shot in all_shots_to_test:
            angle = shot['angle']
            target = shot['target']
            is_safety = shot.get('is_safety', False)
            
            best_result_for_shot = None
            
            for power in shot['power_levels']:
                # Run the full simulation
                result = self.simulate_shot_with_angle_power(angle, power, target)
                result['is_safety'] = is_safety
                result['shot_data'] = shot
                
                # Skip fouls if we have better options
                if result['foul']:
                    if best_result_for_shot is None:
                        best_result_for_shot = result
                    continue
                
                # Non-foul result - check if it's better
                if best_result_for_shot is None or best_result_for_shot['foul']:
                    best_result_for_shot = result
                elif result['points'] > best_result_for_shot['points']:
                    best_result_for_shot = result
                elif result['points'] == best_result_for_shot['points'] and result['points'] > 0:
                    # Same points - prefer lower power for control
                    if result['power'] < best_result_for_shot['power']:
                        best_result_for_shot = result
            
            if best_result_for_shot:
                all_results.append(best_result_for_shot)
        
        # =====================================================================
        # PHASE 3: Select the BEST legal scoring shot
        # =====================================================================
        def score_result(r):
            # Primary: NO FOULS (massive penalty for fouls)
            foul_penalty = -100000 if r['foul'] else 0
            
            # Secondary: POINTS SCORED (higher is better)
            points_score = r['points'] * 10000
            
            # Tertiary: Ball value (for equal-point shots, prefer higher value balls)
            ball_value = r.get('shot_data', {}).get('ball_value', 0) * 100
            
            # Quaternary: Ease of shot (prefer straight, close shots)
            cut_angle = r.get('shot_data', {}).get('cut_angle', 1.0)
            distance = r.get('shot_data', {}).get('distance', 500)
            ease_score = 50 - (cut_angle * 30) - (distance / 20)
            
            # Safety shots get a small bonus when no pots available
            safety_bonus = 10 if r.get('is_safety') and not r['foul'] else 0
            
            return foul_penalty + points_score + ball_value + ease_score + safety_bonus
        
        all_results.sort(key=score_result, reverse=True)
        
        if all_results:
            return all_results[0]
        return None

    def simulate_all_potential_shots(self) -> List[dict]:
        """
        Simulate ALL potential shots and return results sorted by:
        1. NO FOUL shots first (we NEVER want to give opponent points)
        2. Then by AI points scored (highest first)
        3. Safety shots as fallback (legal hit, 0 points but no foul)
        
        This runs during AI "thinking" phase - fast, no rendering.
        """
        potential_shots = self.calculate_ai_potential_shots()
        results = []
        
        for shot in potential_shots:
            if shot.get('blocked', False):
                continue
            
            is_safety = shot.get('is_safety', False)
            shot_distance = shot.get('distance', 200)  # Distance from cue to target
            
            # Calculate optimal power range based on shot distance
            # Closer shots need less power, longer shots need more
            if is_safety:
                power_levels = [8, 10, 12, 14]  # Gentle rolls for safety
            else:
                # Dynamic power levels based on distance
                # Short shots (< 100px): lower power range
                # Medium shots (100-250px): medium power range
                # Long shots (> 250px): higher power range
                if shot_distance < 100:
                    power_levels = [10, 12, 14, 16, 18]  # Close shots
                elif shot_distance < 200:
                    power_levels = [14, 16, 18, 20, 22]  # Medium shots
                elif shot_distance < 300:
                    power_levels = [16, 18, 20, 22, 25, 28]  # Long shots
                else:
                    power_levels = [18, 20, 23, 25, 28, 30]  # Very long shots
            
            best_result = None
            best_potting_power = None  # Track the power that pots the ball
            
            for power in power_levels:
                result = self.simulate_shot(shot, power)
                result['is_safety'] = is_safety
                
                # Skip fouls unless we have no other choice
                if result['foul']:
                    # Only keep foul results if we haven't found anything better
                    if best_result is None:
                        best_result = result
                        best_result['power'] = power
                    # Never prefer a foul over a non-foul
                    continue
                
                # Non-foul result - check if it's better
                if best_result is None or best_result['foul']:
                    # First non-foul result, take it
                    best_result = result
                    best_result['power'] = power
                    if result['points'] > 0:
                        best_potting_power = power
                elif result['points'] > best_result['points']:
                    # More points without fouling
                    best_result = result
                    best_result['power'] = power
                    best_potting_power = power
                elif result['points'] == best_result['points'] and result['points'] > 0:
                    # Same points - prefer lower power for control
                    if best_potting_power is None or power < best_potting_power:
                        best_result = result
                        best_result['power'] = power
                        best_potting_power = power
            
            if best_result:
                results.append(best_result)
        
        # Sort by: NO FOUL first, then by AI points (highest first), 
        # then by ease-of-pot (as tiebreaker), then safety as fallback
        def score_shot(r):
            # Primary: Foul status (non-foul = 10000 bonus)
            foul_penalty = 0 if not r['foul'] else -10000
            # Secondary: AI points gained (potting shots preferred)
            ai_score = r['points'] * 100
            # Tertiary: Ease of pot as tiebreaker (use pre-calculated shot score)
            # This ensures among equal-point shots, the easiest pot wins
            shot_data = r.get('shot', {})
            ease_score = shot_data.get('score', 0) / 100  # Scale down to 0-5 range as tiebreaker
            ease_score = max(0, min(5, ease_score))  # Clamp to avoid overwhelming other factors
            # Quaternary: Safety shots are acceptable fallback (0 points but legal)
            safety_bonus = 50 if r.get('is_safety') and not r['foul'] and r['points'] == 0 else 0
            # Quinary: Opponent points avoided (negative = bad)
            opponent_penalty = -r['opponent_points'] * 50
            return foul_penalty + ai_score + ease_score + safety_bonus + opponent_penalty
        
        results.sort(key=score_shot, reverse=True)
        return results

    def resolve_physics(self, dt: float):
        """Handle all physics: movement, collisions, pocketing."""
        # Reset collision counter for this physics step
        self.collision_count_this_frame = 0
        
        # Multiple passes for collision resolution to ensure all collisions are handled
        # This prevents balls from passing through each other
        max_iterations = 5
        
        for iteration in range(max_iterations):
            collision_occurred = False
            
            for i, b1 in enumerate(self.balls):
                if b1.potted:
                    continue

                # Cushion collisions with realistic spin effects
                # Side spin affects the angle of reflection off cushions
                # Cushion coefficient of restitution is typically 0.75-0.85 for snooker
                cushion_restitution = 0.82
                cushion_spin_effect = 0.15  # How much side spin affects reflection angle
                
                if b1.x - b1.radius < self.table_rect.left:
                    b1.x = self.table_rect.left + b1.radius
                    # Side spin affects vertical velocity when hitting side cushion
                    spin_adjustment = b1.side_spin * cushion_spin_effect
                    b1.vy += spin_adjustment
                    b1.vx = abs(b1.vx) * cushion_restitution
                    # Cushion contact reduces spin
                    b1.side_spin *= 0.6
                    b1.top_spin *= 0.85
                elif b1.x + b1.radius > self.table_rect.right:
                    b1.x = self.table_rect.right - b1.radius
                    spin_adjustment = -b1.side_spin * cushion_spin_effect
                    b1.vy += spin_adjustment
                    b1.vx = -abs(b1.vx) * cushion_restitution
                    b1.side_spin *= 0.6
                    b1.top_spin *= 0.85

                if b1.y - b1.radius < self.table_rect.top:
                    b1.y = self.table_rect.top + b1.radius
                    # Side spin affects horizontal velocity when hitting top/bottom cushion
                    spin_adjustment = -b1.side_spin * cushion_spin_effect
                    b1.vx += spin_adjustment
                    b1.vy = abs(b1.vy) * cushion_restitution
                    b1.side_spin *= 0.6
                    b1.top_spin *= 0.85
                elif b1.y + b1.radius > self.table_rect.bottom:
                    b1.y = self.table_rect.bottom - b1.radius
                    spin_adjustment = b1.side_spin * cushion_spin_effect
                    b1.vx += spin_adjustment
                    b1.vy = -abs(b1.vy) * cushion_restitution
                    b1.side_spin *= 0.6
                    b1.top_spin *= 0.85

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

                        # Velocity exchange - improved energy transfer with spin effects
                        rel_vx = b1.vx - b2.vx
                        rel_vy = b1.vy - b2.vy
                        v_dot_n = rel_vx * nx + rel_vy * ny

                        if v_dot_n > 0:
                            # Standard elastic collision with realistic energy preservation
                            # Snooker balls have coefficient of restitution ~0.95
                            energy_preservation = 0.96
                            
                            # Calculate base velocity changes
                            b1.vx -= v_dot_n * nx * energy_preservation
                            b1.vy -= v_dot_n * ny * energy_preservation
                            b2.vx += v_dot_n * nx * energy_preservation
                            b2.vy += v_dot_n * ny * energy_preservation
                            
                            # THROW EFFECT: Side spin on cue ball transfers to object ball direction
                            # This causes the object ball to slightly deviate from the expected path
                            if b1.ball_type == 'white' and abs(b1.side_spin) > 0.5:
                                throw_amount = b1.side_spin * Ball.THROW_COEFFICIENT
                                # Perpendicular direction to collision normal
                                perp_x = -ny
                                perp_y = nx
                                b2.vx += perp_x * throw_amount
                                b2.vy += perp_y * throw_amount
                            elif b2.ball_type == 'white' and abs(b2.side_spin) > 0.5:
                                throw_amount = b2.side_spin * Ball.THROW_COEFFICIENT
                                perp_x = -ny
                                perp_y = nx
                                b1.vx -= perp_x * throw_amount
                                b1.vy -= perp_y * throw_amount
                            
                            # TOP/BACK SPIN EFFECT: Affects cue ball motion after collision
                            if b1.ball_type == 'white':
                                # Top spin makes cue ball follow through
                                # Back spin makes cue ball draw back
                                spin_effect = b1.top_spin * 0.08
                                b1.vx += nx * spin_effect
                                b1.vy += ny * spin_effect
                                # Reduce spin after collision
                                b1.top_spin *= 0.5
                                b1.side_spin *= 0.7
                            elif b2.ball_type == 'white':
                                spin_effect = b2.top_spin * 0.08
                                b2.vx -= nx * spin_effect
                                b2.vy -= ny * spin_effect
                                b2.top_spin *= 0.5
                                b2.side_spin *= 0.7
                            
                            # Play collision sound (based on collision intensity)
                            collision_speed = abs(v_dot_n)
                            if collision_speed > 2.0:  # Only play for significant collisions
                                self.collision_count_this_frame += 1
                                current_time = pygame.time.get_ticks()
                                # Avoid playing too many sounds in quick succession
                                if current_time - self.last_collision_time > 50:  # 50ms cooldown
                                    if self.collision_count_this_frame > 2:
                                        self._play_sound('multi_hit')
                                    else:
                                        self._play_sound('ball_hit')
                                    self.last_collision_time = current_time
                        
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
                        # Sound is played in evaluate_turn() - only for legal pots, not fouls
                        break
                else:
                    # Normal/medium speed: if ANY part of ball touches pocket, it goes in
                    # Check if distance from pocket center to ball center is less than (pocket_size + ball_radius)
                    effective_pocket_radius = pocket_size + b1.radius
                    if dist_to_pocket_center < effective_pocket_radius:
                        b1.potted = True
                        b1.vx = b1.vy = 0
                        self.potted_this_turn.append(b1)
                        # Sound is played in evaluate_turn() - only for legal pots, not fouls
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
            
            # Play foul sound
            self._play_sound('foul')

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
            # Play pot applause for legal pots only
            self._play_sound('pot')
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
            # Reset AI studying state for new turn
            self.ai_studying = False
            self.ai_study_timer = 0
            self.ai_potential_shots = []
            self.ai_current_study_index = 0
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
        footer = self.fonts['tiny'].render("Mouse to aim • Hold click for power • Drag spin control for english • ESC for menu", True, COLORS['text_secondary'])
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
            ("Mouse = Aim  |  Hold Left Click = Power  |  Release = Shoot", COLORS['text_primary']),
            ("Spin Control (bottom-left) = Drag dot for top/back/side spin  |  Right-click = Reset spin", COLORS['text_primary']),
            ("ESC = Menu", COLORS['text_primary']),
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

    def _ray_circle_intersection(self, origin_x: float, origin_y: float, dir_x: float, dir_y: float,
                                 center_x: float, center_y: float, radius: float) -> Optional[float]:
        """Return the nearest ray-circle intersection distance, or None."""
        fx = origin_x - center_x
        fy = origin_y - center_y
        b = 2.0 * (fx * dir_x + fy * dir_y)
        c = fx * fx + fy * fy - radius * radius
        discriminant = b * b - 4.0 * c
        if discriminant < 0:
            return None
        sqrt_disc = math.sqrt(discriminant)
        t1 = (-b - sqrt_disc) / 2.0
        t2 = (-b + sqrt_disc) / 2.0
        if t1 >= 0:
            return t1
        if t2 >= 0:
            return t2
        return None

    def _ray_rect_intersection_distance(self, origin_x: float, origin_y: float,
                                        dir_x: float, dir_y: float) -> float:
        """Return distance to the table boundary along a ray."""
        candidates = []
        if abs(dir_x) > 1e-6:
            t = (self.table_rect.left - origin_x) / dir_x
            y = origin_y + dir_y * t
            if t > 0 and self.table_rect.top <= y <= self.table_rect.bottom:
                candidates.append(t)
            t = (self.table_rect.right - origin_x) / dir_x
            y = origin_y + dir_y * t
            if t > 0 and self.table_rect.top <= y <= self.table_rect.bottom:
                candidates.append(t)
        if abs(dir_y) > 1e-6:
            t = (self.table_rect.top - origin_y) / dir_y
            x = origin_x + dir_x * t
            if t > 0 and self.table_rect.left <= x <= self.table_rect.right:
                candidates.append(t)
            t = (self.table_rect.bottom - origin_y) / dir_y
            x = origin_x + dir_x * t
            if t > 0 and self.table_rect.left <= x <= self.table_rect.right:
                candidates.append(t)
        return min(candidates) if candidates else 0.0

    def _ray_table_intersection(self, origin_x: float, origin_y: float,
                                dir_x: float, dir_y: float) -> Tuple[Optional[float], Optional[str]]:
        """Return distance and side for first table boundary hit."""
        best_t = None
        best_side = None

        if abs(dir_x) > 1e-6:
            t = (self.table_rect.left - origin_x) / dir_x
            y = origin_y + dir_y * t
            if t > 0 and self.table_rect.top <= y <= self.table_rect.bottom:
                if best_t is None or t < best_t:
                    best_t, best_side = t, "left"
            t = (self.table_rect.right - origin_x) / dir_x
            y = origin_y + dir_y * t
            if t > 0 and self.table_rect.top <= y <= self.table_rect.bottom:
                if best_t is None or t < best_t:
                    best_t, best_side = t, "right"

        if abs(dir_y) > 1e-6:
            t = (self.table_rect.top - origin_y) / dir_y
            x = origin_x + dir_x * t
            if t > 0 and self.table_rect.left <= x <= self.table_rect.right:
                if best_t is None or t < best_t:
                    best_t, best_side = t, "top"
            t = (self.table_rect.bottom - origin_y) / dir_y
            x = origin_x + dir_x * t
            if t > 0 and self.table_rect.left <= x <= self.table_rect.right:
                if best_t is None or t < best_t:
                    best_t, best_side = t, "bottom"

        return best_t, best_side

    def _get_first_ball_intersection(self, origin_x: float, origin_y: float,
                                     dir_x: float, dir_y: float) -> Tuple[Optional[Ball], Optional[float], Optional[float], Optional[float]]:
        """Find the first ball intersected by the cue ray."""
        hit_ball = None
        hit_t = None
        for ball in self.balls:
            if ball.potted or ball.ball_type == 'white':
                continue
            radius = ball.radius + self.cue_ball.radius
            t = self._ray_circle_intersection(origin_x, origin_y, dir_x, dir_y, ball.x, ball.y, radius)
            if t is None:
                continue
            if hit_t is None or t < hit_t:
                hit_t = t
                hit_ball = ball
        if hit_ball is None or hit_t is None:
            return None, None, None, None
        hit_x = origin_x + dir_x * hit_t
        hit_y = origin_y + dir_y * hit_t
        return hit_ball, hit_x, hit_y, hit_t

    def _balls_on_line(self, origin_x: float, origin_y: float, dir_x: float, dir_y: float,
                       exclude: Optional[Ball] = None) -> List[Tuple[Ball, float]]:
        """Return balls that lie along a line (sorted by projection distance)."""
        aligned: List[Tuple[Ball, float]] = []
        for ball in self.balls:
            if ball.potted or ball.ball_type == 'white' or ball == exclude:
                continue
            dx = ball.x - origin_x
            dy = ball.y - origin_y
            proj = dx * dir_x + dy * dir_y
            if proj <= 0:
                continue
            perp = abs(dx * dir_y - dy * dir_x)
            if perp <= (ball.radius + self.cue_ball.radius) * 0.9:
                aligned.append((ball, proj))
        aligned.sort(key=lambda item: item[1])
        return aligned

    def _draw_potential_ball_trajectories(self, origin_x: float, origin_y: float,
                                          dir_x: float, dir_y: float):
        """Draw trajectories only for balls aligned with the cue direction."""
        line_color = (110, 170, 210)
        dash_spacing = 14 * self.scale
        max_length = 180 * self.scale

        for ball in self.balls:
            if ball.potted or ball.ball_type == 'white':
                continue
            dx = ball.x - origin_x
            dy = ball.y - origin_y
            proj = dx * dir_x + dy * dir_y
            if proj <= 0:
                continue
            # Perpendicular distance from cue ray to ball center
            perp = abs(dx * dir_y - dy * dir_x)
            if perp > (ball.radius + self.cue_ball.radius) * 0.9:
                continue

            boundary_t = self._ray_rect_intersection_distance(ball.x, ball.y, dir_x, dir_y)
            line_t = min(boundary_t, max_length) if boundary_t > 0 else max_length
            if line_t <= 0:
                continue

            step = dash_spacing
            d = 0
            while d <= line_t:
                x = ball.x + dir_x * d
                y = ball.y + dir_y * d
                if not self.table_rect.collidepoint(x, y):
                    break
                if int(d / step) % 2 == 0:
                    pygame.draw.circle(self.screen, line_color, (int(x), int(y)), int(2 * self.scale))
                d += step

    def draw_aiming_line(self):
        """Draw the aiming guide line with precise cue → first ball geometry."""
        if not self.cue_ball or self.cue_ball.potted:
            return

        mx, my = pygame.mouse.get_pos()
        angle = math.atan2(my - self.cue_ball.y, mx - self.cue_ball.x)
        dir_x = math.cos(angle)
        dir_y = math.sin(angle)

        # Subtle potential trajectories for every ball
        self._draw_potential_ball_trajectories(self.cue_ball.x, self.cue_ball.y, dir_x, dir_y)

        # Find precise first-ball hit using ray-circle intersection
        hit_ball, hit_x, hit_y, hit_t = self._get_first_ball_intersection(
            self.cue_ball.x, self.cue_ball.y, dir_x, dir_y
        )

        # Draw dotted aiming line up to the hit point or table boundary
        boundary_t, boundary_side = self._ray_table_intersection(self.cue_ball.x, self.cue_ball.y, dir_x, dir_y)
        line_t = hit_t if hit_t is not None else boundary_t
        if line_t and line_t > 0:
            start_offset = self.cue_ball.radius + 8 * self.scale
            dot_spacing = 12 * self.scale
            dist = start_offset
            while dist <= line_t:
                t = dist / max(line_t, 1.0)
                x = self.cue_ball.x + dir_x * dist
                y = self.cue_ball.y + dir_y * dist
                if not self.table_rect.collidepoint(x, y):
                    break
                alpha = int(180 * (1 - t * 0.7))
                pygame.draw.circle(self.screen, (alpha, alpha, alpha), (int(x), int(y)), int(2 * self.scale))
                dist += dot_spacing

        # Cushion reflection line (light orange) when cue path reaches the cushion first
        if boundary_t and boundary_side and (hit_t is None or boundary_t < hit_t):
            hit_x = self.cue_ball.x + dir_x * boundary_t
            hit_y = self.cue_ball.y + dir_y * boundary_t
            refl_x, refl_y = dir_x, dir_y
            if boundary_side in ("left", "right"):
                refl_x = -refl_x
            else:
                refl_y = -refl_y

            bounce_length = 240 * self.scale
            bounce_spacing = 12 * self.scale
            bounce_color = (255, 190, 120)
            d = 0
            while d <= bounce_length:
                x = hit_x + refl_x * d
                y = hit_y + refl_y * d
                if not self.table_rect.collidepoint(x, y):
                    break
                if int(d / bounce_spacing) % 2 == 0:
                    pygame.draw.circle(self.screen, bounce_color, (int(x), int(y)), int(2 * self.scale))
                d += bounce_spacing
        
        # Enhanced geometry visualization: cue → first ball
        if hit_ball and hit_x is not None and hit_y is not None:
            # Draw solid line from cue ball to first ball hit (cyan)
            pygame.draw.line(self.screen, COLORS['gold_bright'], 
                           (int(self.cue_ball.x), int(self.cue_ball.y)),
                           (int(hit_x), int(hit_y)), 3)
            
            # Calculate the direction the first ball will travel (using ghost ball method)
            # Direction from hit point to target center defines object ball path
            obj_dx = hit_ball.x - hit_x
            obj_dy = hit_ball.y - hit_y
            obj_dist = math.hypot(obj_dx, obj_dy)
            if obj_dist > 0:
                obj_nx = obj_dx / obj_dist
                obj_ny = obj_dy / obj_dist
                first_ball_angle = math.atan2(obj_ny, obj_nx)

                # Draw first ball trajectory (match hit ball color)
                trajectory_length = 300 * self.scale
                traj_color = hit_ball.color
                for j in range(0, 30):
                    t = j / 30
                    tx = hit_ball.x + math.cos(first_ball_angle) * (trajectory_length * t)
                    ty = hit_ball.y + math.sin(first_ball_angle) * (trajectory_length * t)
                    if self.table_rect.collidepoint(tx, ty):
                        if j % 3 == 0:  # Dashed effect
                            pygame.draw.circle(self.screen, traj_color, (int(tx), int(ty)), int(3 * self.scale))

                # Show trajectories for any balls affected along this line
                affected = self._balls_on_line(hit_ball.x, hit_ball.y, obj_nx, obj_ny, exclude=hit_ball)
                for affected_ball, proj in affected:
                    impact_x = hit_ball.x + obj_nx * proj
                    impact_y = hit_ball.y + obj_ny * proj
                    # Draw a short line from hit ball to affected ball
                    pygame.draw.line(self.screen, hit_ball.color,
                                     (int(hit_ball.x), int(hit_ball.y)),
                                     (int(affected_ball.x), int(affected_ball.y)), 2)

                    # Draw affected ball trajectory in its own color
                    traj_color = affected_ball.color
                    for j in range(0, 24):
                        t = j / 24
                        tx = impact_x + obj_nx * (trajectory_length * 0.7 * t)
                        ty = impact_y + obj_ny * (trajectory_length * 0.7 * t)
                        if self.table_rect.collidepoint(tx, ty):
                            if j % 3 == 0:
                                pygame.draw.circle(self.screen, traj_color, (int(tx), int(ty)), int(3 * self.scale))

    def draw_ai_studying(self):
        """Draw visualization of AI studying different potential shots - cue stick moves around table."""
        if not self.cue_ball or self.cue_ball.potted or not self.ai_studying:
            return
        
        if not self.ai_potential_shots or self.ai_current_study_index >= len(self.ai_potential_shots):
            return
        
        # Get current shot being studied
        current_shot = self.ai_potential_shots[self.ai_current_study_index]
        target = current_shot['target']
        pocket = current_shot['pocket']
        angle = current_shot['angle']
        
        pulse = (math.sin(self.animation_tick * 0.15) + 1) * 0.3 + 0.4  # Pulsing effect
        
        # Draw faded consideration markers on all potential targets
        for i, shot in enumerate(self.ai_potential_shots):
            if shot['blocked']:
                continue
            target_ball = shot['target']
            if i != self.ai_current_study_index:
                # Draw small faded circle around other potential targets
                pygame.draw.circle(self.screen, (100, 100, 100), 
                                  (int(target_ball.x), int(target_ball.y)), 
                                  int(target_ball.radius * 1.3), 1)
        
        # MAIN FEATURE: Draw AI cue stick pointing at current shot being studied
        # This shows the AI "walking around" and lining up different shots
        dir_x = math.cos(angle)
        dir_y = math.sin(angle)
        
        # Calculate ghost ball position for this shot
        to_pocket_x = pocket[0] - target.x
        to_pocket_y = pocket[1] - target.y
        to_pocket_dist = math.hypot(to_pocket_x, to_pocket_y)
        if to_pocket_dist > 0:
            to_pocket_x /= to_pocket_dist
            to_pocket_y /= to_pocket_dist
        
        ghost_x = target.x - to_pocket_x * (target.radius + self.cue_ball.radius) * 1.05
        ghost_y = target.y - to_pocket_y * (target.radius + self.cue_ball.radius) * 1.05
        
        # Draw the AI's cue stick pointing at this potential shot (semi-transparent)
        # Pullback oscillates slightly as if AI is "feeling" the shot
        pullback_base = 30 * self.scale
        pullback_wobble = math.sin(self.animation_tick * 0.1) * 5 * self.scale
        pullback = pullback_base + pullback_wobble
        stick_length = 220 * self.scale
        
        start_x = self.cue_ball.x - dir_x * pullback
        start_y = self.cue_ball.y - dir_y * pullback
        end_x = start_x - dir_x * stick_length
        end_y = start_y - dir_y * stick_length
        
        # Draw semi-transparent cue stick (studying position)
        pygame.draw.line(self.screen, (140, 100, 60), (start_x, start_y), (end_x, end_y), int(8 * self.scale))
        pygame.draw.line(self.screen, (100, 70, 40), (start_x, start_y), (end_x, end_y), int(5 * self.scale))
        
        # Cue tip
        tip_x = self.cue_ball.x - dir_x * (pullback - 8 * self.scale)
        tip_y = self.cue_ball.y - dir_y * (pullback - 8 * self.scale)
        pygame.draw.circle(self.screen, (80, 120, 150), (int(tip_x), int(tip_y)), int(5 * self.scale))
        
        # Draw studying aim line (golden animated dots)
        cue_to_ghost = math.hypot(ghost_x - self.cue_ball.x, ghost_y - self.cue_ball.y)
        spacing = 14 * self.scale
        for d in range(int(self.cue_ball.radius), int(cue_to_ghost), int(spacing)):
            x = self.cue_ball.x + dir_x * d
            y = self.cue_ball.y + dir_y * d
            wave = (math.sin((d / spacing) * 0.5 + self.animation_tick * 0.2) + 1) * 0.5
            brightness = int(150 + wave * 100 * pulse)
            color = (brightness, int(brightness * 0.8), int(brightness * 0.2))
            size = int((2 + wave) * self.scale)
            pygame.draw.circle(self.screen, color, (int(x), int(y)), size)
        
        # Draw target ball highlight (pulsing circle around it)
        highlight_radius = int(target.radius * (1.5 + pulse * 0.3))
        pygame.draw.circle(self.screen, (255, 200, 50), (int(target.x), int(target.y)), highlight_radius, 2)
        
        # Draw arrow from target to pocket (trajectory prediction)
        trajectory_length = to_pocket_dist * 0.8
        for j in range(0, int(trajectory_length), int(spacing)):
            t = j / max(trajectory_length, 1)
            tx = target.x + to_pocket_x * j
            ty = target.y + to_pocket_y * j
            if self.table_rect.collidepoint(tx, ty):
                wave = (math.sin(t * 3 + self.animation_tick * 0.15) + 1) * 0.5
                brightness = int(100 + wave * 80 * pulse)
                color = (brightness, int(brightness * 0.5), int(brightness * 0.3))
                pygame.draw.circle(self.screen, color, (int(tx), int(ty)), int(2 * self.scale))
        
        # Draw pocket highlight
        pocket_radius = int(24 * self.scale * (1.1 + pulse * 0.2))
        pygame.draw.circle(self.screen, (200, 150, 50), (pocket[0], pocket[1]), pocket_radius, 3)
        
        # Show "considering" text near the target ball
        shot_value = target.value if target.value > 0 else 1
        consider_text = f"+{shot_value}?"
        text_surf = self.fonts['small'].render(consider_text, True, COLORS['gold_bright'])
        text_x = int(target.x + target.radius * 2)
        text_y = int(target.y - target.radius)
        
        # Background for text
        bg_rect = text_surf.get_rect(topleft=(text_x, text_y))
        bg_rect.inflate_ip(8, 4)
        pygame.draw.rect(self.screen, (0, 0, 0, 180), bg_rect, border_radius=3)
        self.screen.blit(text_surf, (text_x, text_y))
        
        # Draw shot quality indicator
        score = current_shot['score']
        if score > 70:
            quality = "EXCELLENT"
            quality_color = COLORS['text_success']
        elif score > 40:
            quality = "GOOD"
            quality_color = COLORS['gold']
        elif score > 0:
            quality = "POSSIBLE"
            quality_color = COLORS['text_secondary']
        else:
            quality = "DIFFICULT"
            quality_color = COLORS['text_foul']
        
        quality_surf = self.fonts['tiny'].render(quality, True, quality_color)
        self.screen.blit(quality_surf, (text_x, text_y + text_surf.get_height() + 2))
        
        # Show which shot number is being studied
        study_text = f"Studying shot {self.ai_current_study_index + 1}/{min(len(self.ai_potential_shots), 4)}"
        study_surf = self.fonts['tiny'].render(study_text, True, COLORS['gold'])
        self.screen.blit(study_surf, (self.window_rect.x + int(10 * self.scale), 
                                      self.table_rect.bottom + int(10 * self.scale)))

    def draw_ai_aiming_line(self):
        """Draw the AI's aiming guide line with precise cue → first ball geometry."""
        if not self.cue_ball or self.cue_ball.potted or not self.ai_shot_calculated:
            return

        angle = self.ai_angle
        dir_x = math.cos(angle)
        dir_y = math.sin(angle)

        # Subtle potential trajectories for every ball
        self._draw_potential_ball_trajectories(self.cue_ball.x, self.cue_ball.y, dir_x, dir_y)

        # Find precise first-ball hit using ray-circle intersection
        hit_ball, hit_x, hit_y, hit_t = self._get_first_ball_intersection(
            self.cue_ball.x, self.cue_ball.y, dir_x, dir_y
        )

        # Draw dotted aiming line up to the hit point or table boundary
        boundary_t, boundary_side = self._ray_table_intersection(self.cue_ball.x, self.cue_ball.y, dir_x, dir_y)
        line_t = hit_t if hit_t is not None else boundary_t
        if line_t and line_t > 0:
            start_offset = self.cue_ball.radius + 8 * self.scale
            dot_spacing = 12 * self.scale
            dist = start_offset
            while dist <= line_t:
                t = dist / max(line_t, 1.0)
                x = self.cue_ball.x + dir_x * dist
                y = self.cue_ball.y + dir_y * dist
                if not self.table_rect.collidepoint(x, y):
                    break
                alpha = int(180 * (1 - t * 0.7))
                pygame.draw.circle(self.screen, (alpha, alpha, alpha), (int(x), int(y)), int(2 * self.scale))
                dist += dot_spacing

        # Cushion reflection line (light orange) when cue path reaches the cushion first
        if boundary_t and boundary_side and (hit_t is None or boundary_t < hit_t):
            hit_x = self.cue_ball.x + dir_x * boundary_t
            hit_y = self.cue_ball.y + dir_y * boundary_t
            refl_x, refl_y = dir_x, dir_y
            if boundary_side in ("left", "right"):
                refl_x = -refl_x
            else:
                refl_y = -refl_y

            bounce_length = 240 * self.scale
            bounce_spacing = 12 * self.scale
            bounce_color = (255, 190, 120)
            d = 0
            while d <= bounce_length:
                x = hit_x + refl_x * d
                y = hit_y + refl_y * d
                if not self.table_rect.collidepoint(x, y):
                    break
                if int(d / bounce_spacing) % 2 == 0:
                    pygame.draw.circle(self.screen, bounce_color, (int(x), int(y)), int(2 * self.scale))
                d += bounce_spacing
        
        # Enhanced geometry visualization: cue → first ball
        if hit_ball and hit_x is not None and hit_y is not None:
            # Draw solid line from cue ball to first ball hit (cyan)
            pygame.draw.line(self.screen, COLORS['gold_bright'], 
                           (int(self.cue_ball.x), int(self.cue_ball.y)),
                           (int(hit_x), int(hit_y)), 3)
            
            # Direction from hit point to target center defines object ball path
            obj_dx = hit_ball.x - hit_x
            obj_dy = hit_ball.y - hit_y
            obj_dist = math.hypot(obj_dx, obj_dy)
            if obj_dist > 0:
                obj_nx = obj_dx / obj_dist
                obj_ny = obj_dy / obj_dist
                first_ball_angle = math.atan2(obj_ny, obj_nx)
                
                # Draw trajectory from first ball (match hit ball color)
                trajectory_length = 300 * self.scale
                traj_color = hit_ball.color
                for j in range(0, 30):
                    t = j / 30
                    tx = hit_ball.x + math.cos(first_ball_angle) * (trajectory_length * t)
                    ty = hit_ball.y + math.sin(first_ball_angle) * (trajectory_length * t)
                    if self.table_rect.collidepoint(tx, ty):
                        if j % 3 == 0:
                            pygame.draw.circle(self.screen, traj_color, (int(tx), int(ty)), int(3 * self.scale))

                # Show trajectories for any balls affected along this line
                affected = self._balls_on_line(hit_ball.x, hit_ball.y, obj_nx, obj_ny, exclude=hit_ball)
                for affected_ball, proj in affected:
                    impact_x = hit_ball.x + obj_nx * proj
                    impact_y = hit_ball.y + obj_ny * proj
                    pygame.draw.line(self.screen, hit_ball.color,
                                     (int(hit_ball.x), int(hit_ball.y)),
                                     (int(affected_ball.x), int(affected_ball.y)), 2)

                    traj_color = affected_ball.color
                    for j in range(0, 24):
                        t = j / 24
                        tx = impact_x + obj_nx * (trajectory_length * 0.7 * t)
                        ty = impact_y + obj_ny * (trajectory_length * 0.7 * t)
                        if self.table_rect.collidepoint(tx, ty):
                            if j % 3 == 0:
                                pygame.draw.circle(self.screen, traj_color, (int(tx), int(ty)), int(3 * self.scale))

    def draw_cue_stick(self):
        """Draw the cue stick during aiming/charging."""
        if not self.cue_ball:
            return

        mx, my = pygame.mouse.get_pos()
        angle = math.atan2(my - self.cue_ball.y, mx - self.cue_ball.x)

        # Pull back based on power (scaled)
        pullback = (25 + self.cue_power * 0.8) * self.scale
        stick_length = 440 * self.scale  # Doubled from 220

        start_x = self.cue_ball.x - math.cos(angle) * pullback
        start_y = self.cue_ball.y - math.sin(angle) * pullback
        end_x = start_x - math.cos(angle) * stick_length
        end_y = start_y - math.sin(angle) * stick_length

        # Draw stick (scaled thickness)
        pygame.draw.line(self.screen, COLORS['wood_light'], (start_x, start_y), (end_x, end_y), int(8 * self.scale))
        pygame.draw.line(self.screen, COLORS['wood'], (start_x, start_y), (end_x, end_y), int(5 * self.scale))

        # Tip - semi-circle nib effect (closer to cue ball, scaled)
        tip_radius = 5 * self.scale
        tip_offset = 3 * self.scale  # Closer to cue ball (reduced from 8)
        tip_x = self.cue_ball.x - math.cos(angle) * (pullback - tip_offset)
        tip_y = self.cue_ball.y - math.sin(angle) * (pullback - tip_offset)
        
        # Draw semi-circle facing the cue ball (nib effect)
        # The arc should be on the side facing away from the cue ball direction
        tip_rect = pygame.Rect(int(tip_x - tip_radius), int(tip_y - tip_radius), 
                               int(tip_radius * 2), int(tip_radius * 2))
        # Arc from angle - π/2 to angle + π/2 (semi-circle facing cue ball)
        start_angle = angle - math.pi / 2
        stop_angle = angle + math.pi / 2
        pygame.draw.arc(self.screen, (100, 140, 170), tip_rect, start_angle, stop_angle, int(3 * self.scale))

    def draw_ai_cue_stick(self):
        """Draw the AI's cue stick during preparation."""
        if not self.cue_ball or not self.ai_shot_calculated:
            return

        angle = self.ai_angle

        # Pull back based on AI's charging power (scaled)
        pullback = (25 + self.ai_power_charging * 0.8) * self.scale
        stick_length = 440 * self.scale  # Doubled from 220

        start_x = self.cue_ball.x - math.cos(angle) * pullback
        start_y = self.cue_ball.y - math.sin(angle) * pullback
        end_x = start_x - math.cos(angle) * stick_length
        end_y = start_y - math.sin(angle) * stick_length

        # Draw stick (scaled thickness) - slightly different color to distinguish
        pygame.draw.line(self.screen, COLORS['wood_light'], (start_x, start_y), (end_x, end_y), int(8 * self.scale))
        pygame.draw.line(self.screen, (80, 60, 40), (start_x, start_y), (end_x, end_y), int(5 * self.scale))

        # Tip - semi-circle nib effect (closer to cue ball, scaled)
        tip_radius = 5 * self.scale
        tip_offset = 3 * self.scale  # Closer to cue ball (reduced from 8)
        tip_x = self.cue_ball.x - math.cos(angle) * (pullback - tip_offset)
        tip_y = self.cue_ball.y - math.sin(angle) * (pullback - tip_offset)
        
        # Draw semi-circle facing the cue ball (nib effect)
        # The arc should be on the side facing away from the cue ball direction
        tip_rect = pygame.Rect(int(tip_x - tip_radius), int(tip_y - tip_radius), 
                               int(tip_radius * 2), int(tip_radius * 2))
        # Arc from angle - π/2 to angle + π/2 (semi-circle facing cue ball)
        start_angle = angle - math.pi / 2
        stop_angle = angle + math.pi / 2
        pygame.draw.arc(self.screen, (100, 140, 170), tip_rect, start_angle, stop_angle, int(3 * self.scale))

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

        # Bottom hint - right side
        hint = self.fonts['tiny'].render("ESC: Menu | Right-click: Reset spin", True, COLORS['text_secondary'])
        self.screen.blit(hint, (self.window_rect.right - hint.get_width() - int(10 * self.scale), self.window_rect.bottom - int(25 * self.scale)))

        # AI thinking indicator
        if (self.mode == GameMode.VS_AI or self.mode == GameMode.TOURNAMENT) and self.current_player == 1 and self.ai_timer > 0:
            dots = "." * ((self.animation_tick // 15) % 4)
            think = self.fonts['small'].render(f"Computer thinking{dots}", True, COLORS['gold'])
            self.screen.blit(think, think.get_rect(center=(ui_panel_rect.centerx, ui_panel_rect.bottom + int(80 * self.scale))))
        
        # Draw spin control when human player is aiming (not during ball movement)
        is_human_turn = not ((self.mode == GameMode.VS_AI or self.mode == GameMode.TOURNAMENT) and self.current_player == 1)
        balls_moving = any(b.is_moving() for b in self.balls if not b.potted)
        if is_human_turn and self.turn_phase == TurnPhase.AIMING and not balls_moving:
            self.draw_spin_control()

    def draw_spin_control(self):
        """Draw the interactive spin control - white ball with draggable black dot."""
        if not self.window_rect or not self.table_rect:
            return
        
        # Position the spin control BELOW the table, in the left area of the bottom UI space
        # The table leaves 150*scale pixels at the bottom for UI
        control_x = self.table_rect.x + int(60 * self.scale)
        control_y = self.table_rect.bottom + int(50 * self.scale)  # 50 pixels below the table
        
        # Store the control rect for mouse interaction
        self.spin_control_rect = pygame.Rect(
            control_x - self.spin_control_radius,
            control_y - self.spin_control_radius,
            self.spin_control_radius * 2,
            self.spin_control_radius * 2
        )
        
        # Draw outer ring (table green)
        pygame.draw.circle(self.screen, COLORS['table_cloth'], 
                          (control_x, control_y), self.spin_control_radius + int(4 * self.scale))
        
        # Draw the main white ball
        pygame.draw.circle(self.screen, COLORS['ball_white'], 
                          (control_x, control_y), self.spin_control_radius)
        
        # Draw subtle inner gradient/shading for 3D effect
        for i in range(3):
            shade = 240 - i * 15
            inner_radius = self.spin_control_radius - int((i + 1) * 3 * self.scale)
            if inner_radius > 0:
                pygame.draw.circle(self.screen, (shade, shade, shade), 
                                  (control_x - int(2 * self.scale), control_y - int(2 * self.scale)), 
                                  inner_radius)
        
        # Draw crosshairs for reference
        crosshair_color = (200, 200, 200)
        crosshair_length = self.spin_control_radius - int(5 * self.scale)
        # Horizontal line
        pygame.draw.line(self.screen, crosshair_color,
                        (control_x - crosshair_length, control_y),
                        (control_x + crosshair_length, control_y), 1)
        # Vertical line
        pygame.draw.line(self.screen, crosshair_color,
                        (control_x, control_y - crosshair_length),
                        (control_x, control_y + crosshair_length), 1)
        
        # Draw zone labels
        label_font = self.fonts['tiny']
        # Top spin label
        top_label = label_font.render("TOP", True, (150, 150, 150))
        self.screen.blit(top_label, (control_x - top_label.get_width() // 2, 
                                     control_y - self.spin_control_radius - int(18 * self.scale)))
        # Draw label (back spin)
        draw_label = label_font.render("DRAW", True, (150, 150, 150))
        self.screen.blit(draw_label, (control_x - draw_label.get_width() // 2,
                                      control_y + self.spin_control_radius + int(5 * self.scale)))
        # Left spin label
        left_label = label_font.render("L", True, (150, 150, 150))
        self.screen.blit(left_label, (control_x - self.spin_control_radius - int(15 * self.scale),
                                      control_y - left_label.get_height() // 2))
        # Right spin label
        right_label = label_font.render("R", True, (150, 150, 150))
        self.screen.blit(right_label, (control_x + self.spin_control_radius + int(8 * self.scale),
                                       control_y - right_label.get_height() // 2))
        
        # Calculate dot position in screen coordinates
        dot_screen_x = control_x + int(self.spin_dot_x * (self.spin_control_radius - self.spin_dot_radius))
        dot_screen_y = control_y + int(self.spin_dot_y * (self.spin_control_radius - self.spin_dot_radius))
        
        # Draw the draggable black dot (strike point)
        # Shadow
        pygame.draw.circle(self.screen, (30, 30, 30),
                          (dot_screen_x + 2, dot_screen_y + 2), self.spin_dot_radius)
        # Main dot
        dot_color = (60, 60, 60) if self.spin_dragging else (20, 20, 20)
        pygame.draw.circle(self.screen, dot_color,
                          (dot_screen_x, dot_screen_y), self.spin_dot_radius)
        # Highlight on dot
        pygame.draw.circle(self.screen, (80, 80, 80),
                          (dot_screen_x - int(2 * self.scale), dot_screen_y - int(2 * self.scale)), 
                          int(self.spin_dot_radius * 0.4))
        
        # Draw spin info text
        if abs(self.spin_dot_x) > 0.1 or abs(self.spin_dot_y) > 0.1:
            spin_text = []
            if self.spin_dot_y < -0.1:
                spin_text.append("TOP")
            elif self.spin_dot_y > 0.1:
                spin_text.append("DRAW")
            if self.spin_dot_x < -0.1:
                spin_text.append("LEFT")
            elif self.spin_dot_x > 0.1:
                spin_text.append("RIGHT")
            
            if spin_text:
                info = label_font.render(" ".join(spin_text), True, COLORS['gold'])
                self.screen.blit(info, (control_x - info.get_width() // 2,
                                       control_y + self.spin_control_radius + int(22 * self.scale)))
        
        # Draw "SPIN" title above control
        title = self.fonts['small'].render("SPIN", True, COLORS['text_primary'])
        self.screen.blit(title, (control_x - title.get_width() // 2,
                                control_y - self.spin_control_radius - int(35 * self.scale)))

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
            elif (self.mode == GameMode.VS_AI or self.mode == GameMode.TOURNAMENT) and self.current_player == 1:
                # Draw AI's studying visualization or aiming line
                if self.ai_studying and not self.ai_shot_calculated:
                    # AI is studying the table - show consideration of different shots
                    self.draw_ai_studying()
                elif self.ai_shot_calculated:
                    # AI has decided - show final aiming line
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
                        # Reset AI studying state
                        self.ai_studying = False
                        self.ai_study_timer = 0
                        self.ai_potential_shots = []
                        self.ai_current_study_index = 0
                        # Much slower AI preparation
                        self.ai_timer = random.randint(180, 300)
                        self.ai_shot_calculated = False
                        self.ai_preparing = True
                        self.ai_power_charging = 0
                    return True

        elif is_human_turn and self.turn_phase == TurnPhase.AIMING:
            # Handle spin control interaction
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                
                # Check if clicking on spin control
                if self.spin_control_rect.collidepoint(mx, my):
                    # Calculate distance from spin control center
                    control_x = self.spin_control_rect.centerx
                    control_y = self.spin_control_rect.centery
                    dist = math.hypot(mx - control_x, my - control_y)
                    
                    if dist <= self.spin_control_radius:
                        self.spin_dragging = True
                        # Update dot position
                        max_offset = self.spin_control_radius - self.spin_dot_radius
                        self.spin_dot_x = (mx - control_x) / max_offset if max_offset > 0 else 0
                        self.spin_dot_y = (my - control_y) / max_offset if max_offset > 0 else 0
                        # Clamp to unit circle
                        dist_normalized = math.hypot(self.spin_dot_x, self.spin_dot_y)
                        if dist_normalized > 1.0:
                            self.spin_dot_x /= dist_normalized
                            self.spin_dot_y /= dist_normalized
                        return True
                
                # Not on spin control, start charging
                self.is_charging = True
                self.cue_power = 0
                return True
            
            elif event.type == pygame.MOUSEMOTION:
                # Handle spin control dragging
                if self.spin_dragging:
                    mx, my = event.pos
                    control_x = self.spin_control_rect.centerx
                    control_y = self.spin_control_rect.centery
                    max_offset = self.spin_control_radius - self.spin_dot_radius
                    
                    self.spin_dot_x = (mx - control_x) / max_offset if max_offset > 0 else 0
                    self.spin_dot_y = (my - control_y) / max_offset if max_offset > 0 else 0
                    
                    # Clamp to unit circle
                    dist_normalized = math.hypot(self.spin_dot_x, self.spin_dot_y)
                    if dist_normalized > 1.0:
                        self.spin_dot_x /= dist_normalized
                        self.spin_dot_y /= dist_normalized
                    return True

            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                # Stop spin dragging
                if self.spin_dragging:
                    self.spin_dragging = False
                    return True
                
                if self.is_charging and self.cue_power > 1.5:  # Adjusted threshold for new max of 30
                    # Shoot!
                    mx, my = event.pos
                    angle = math.atan2(my - self.cue_ball.y, mx - self.cue_ball.x)
                    speed = self.cue_power * 2.0  # Power max is now 30 (was 100)

                    self.cue_ball.vx = math.cos(angle) * speed
                    self.cue_ball.vy = math.sin(angle) * speed
                    
                    # Apply spin from the spin control UI
                    # spin_dot_y: negative = top spin, positive = back spin
                    # spin_dot_x: negative = left spin, positive = right spin
                    # Scale spin based on power (more power = more spin effect)
                    power_factor = self.cue_power / 15.0  # Normalize power
                    top_spin = -self.spin_dot_y * 25 * power_factor  # Invert Y for intuitive control
                    side_spin = self.spin_dot_x * 20 * power_factor
                    self.cue_ball.apply_spin(top_spin, side_spin)

                    self.turn_phase = TurnPhase.BALLS_MOVING
                    self.first_ball_hit = None
                    self.potted_this_turn.clear()
                    self.shot_started = True
                    self.collision_count_this_frame = 0
                    
                    # Reset spin control for next shot
                    self.spin_dot_x = 0.0
                    self.spin_dot_y = 0.0
                    
                    # Play cue hit sound
                    self._play_sound('cue_hit')

                self.is_charging = False
                self.cue_power = 0
                return True
            
            # Right-click to reset spin
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
                self.spin_dot_x = 0.0
                self.spin_dot_y = 0.0
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
                    
                    # Reset AI studying state and start preparation
                    self.ai_studying = False
                    self.ai_study_timer = 0
                    self.ai_potential_shots = []
                    self.ai_current_study_index = 0
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

        # AI turn - Uses comprehensive shot simulation system
        # The AI "mentally plays" EVERY possible shot and replays the best one
        if (self.mode == GameMode.VS_AI or self.mode == GameMode.TOURNAMENT) and self.current_player == 1:
            if not balls_moving and self.turn_phase == TurnPhase.AIMING:
                
                # =====================================================================
                # PHASE 1: AI "MENTALLY" SIMULATES ALL POSSIBLE SHOTS
                # This happens instantly in the background - player sees "thinking"
                # =====================================================================
                if not self.ai_studying and not self.ai_shot_calculated:
                    # AI plays EVERY possible shot in its mind and finds the best one
                    # This is completely hidden from the player
                    self.ai_best_simulated_shot = self.find_best_scoring_shot()
                    
                    # Get some shots for visual display (AI "studying" animation)
                    self.ai_potential_shots = self.calculate_ai_potential_shots()
                    
                    self.ai_studying = True
                    self.ai_current_study_index = 0
                    self.ai_study_timer = 60  # Study animation duration
                    
                    # Show thinking message
                    self.show_message(f"{self.player_names[1]} is analyzing every shot...", 300, COLORS['gold'])
                
                # =====================================================================
                # PHASE 2: Visual "studying" animation (AI already knows the best shot)
                # =====================================================================
                if self.ai_studying and not self.ai_shot_calculated:
                    self.ai_study_timer -= 1
                    
                    if self.ai_study_timer <= 0:
                        # Move to next potential shot in the visual animation
                        self.ai_current_study_index += 1
                        
                        # Finished studying animation - NOW use the pre-calculated best shot
                        if self.ai_current_study_index >= min(len(self.ai_potential_shots), 3):
                            self.ai_studying = False
                            
                            # =========================================================
                            # USE THE BEST SHOT FROM COMPREHENSIVE SIMULATION
                            # The AI already knows this shot WILL score (or is best safety)
                            # =========================================================
                            best_shot = self.ai_best_simulated_shot
                            
                            if best_shot:
                                # Extract the winning shot parameters
                                self.ai_angle = best_shot.get('angle', 0)
                                self.ai_power = best_shot.get('power', 20)
                                
                                # Get shot details for message
                                expected_points = best_shot.get('points', 0)
                                is_foul = best_shot.get('foul', False)
                                is_safety = best_shot.get('is_safety', False)
                                
                                target_ball = best_shot.get('target_ball')
                                target_name = target_ball.ball_type if target_ball else 'ball'
                                
                                # Show what AI is going to do
                                if expected_points > 0 and not is_foul:
                                    self.show_message(f"{self.player_names[1]} has spotted +{expected_points} on the {target_name}!", 90, COLORS['gold_bright'])
                                elif not is_foul and is_safety:
                                    self.show_message(f"{self.player_names[1]} plays safe", 90, COLORS['gold'])
                                elif not is_foul:
                                    self.show_message(f"{self.player_names[1]} goes for the {target_name}", 90, COLORS['gold'])
                                else:
                                    self.show_message(f"{self.player_names[1]} is in trouble!", 90, COLORS['text_foul'])
                            else:
                                # Fallback: No simulation found any valid shot
                                # Just hit the nearest legal ball
                                if self.ball_on == "red":
                                    targets = [b for b in self.balls if not b.potted and b.ball_type == 'red']
                                elif self.ball_on == "color":
                                    targets = [b for b in self.balls if not b.potted and b.ball_type in COLOR_SEQUENCE]
                                else:
                                    targets = [b for b in self.balls if not b.potted and b.ball_type == self.ball_on]
                                
                                if not targets:
                                    targets = [b for b in self.balls if not b.potted and b.ball_type != 'white']
                                
                                if targets:
                                    nearest = min(targets, key=lambda b: math.hypot(b.x - self.cue_ball.x, b.y - self.cue_ball.y))
                                    self.ai_angle = math.atan2(nearest.y - self.cue_ball.y, nearest.x - self.cue_ball.x)
                                    self.ai_power = 15
                                    self.show_message(f"{self.player_names[1]} plays cautiously", 90, COLORS['gold'])
                                else:
                                    self.ai_angle = 0
                                    self.ai_power = 10
                            
                            self.ai_shot_calculated = True
                            self.ai_preparing = True
                            self.ai_power_charging = 0
                            self.ai_timer = random.randint(45, 90)  # Brief pause before executing
                        else:
                            # Continue studying animation
                            self.ai_study_timer = 30 + random.randint(0, 15)
                
                # =====================================================================
                # PHASE 3: REPLAY the winning shot for the player to see
                # The AI executes the exact shot it simulated would score
                # =====================================================================
                if self.ai_preparing and self.ai_shot_calculated:
                    # Visual charging animation
                    if self.ai_power_charging < self.ai_power:
                        self.ai_power_charging = min(self.ai_power_charging + 0.3, self.ai_power)
                    else:
                        # Execute the shot - this is the REPLAY of the simulated winning shot
                        self.ai_timer -= 1
                        if self.ai_timer <= 0:
                            # Execute shot with exact angle and power from simulation
                            speed = self.ai_power_charging * 2.0
                            self.cue_ball.vx = math.cos(self.ai_angle) * speed
                            self.cue_ball.vy = math.sin(self.ai_angle) * speed
                            
                            # Minimal spin (simulation didn't use spin)
                            self.cue_ball.apply_spin(0, 0)

                            self.turn_phase = TurnPhase.BALLS_MOVING
                            self.first_ball_hit = None
                            self.potted_this_turn.clear()
                            self.shot_started = True
                            self.ai_preparing = False
                            self.ai_studying = False
                            self.collision_count_this_frame = 0
                            
                            # Play cue hit sound
                            self._play_sound('cue_hit')

        # Power charging (slowed down)
        # Max power is now 30 (which represents 100% power)
        if self.is_charging:
            self.cue_power = min(self.cue_power + 0.18, 30)  # Max power is 30 (100%)

        # Physics update - use sub-stepping for better collision detection with fast balls
        if balls_moving or self.turn_phase == TurnPhase.BALLS_MOVING:
            # Use sub-stepping to prevent fast balls from passing through
            # Update physics in smaller steps for better accuracy
            sub_steps = 3
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
                                base_friction = 0.909 + (speed_factor * 0.0819)  # 30% less friction (9.1% to 0.91% energy loss)
                                aggressive_friction = adjust_friction(base_friction)
                                ball.vx *= aggressive_friction
                                ball.vy *= aggressive_friction
                            elif speed < 30:
                                speed_factor = (speed - 15) / 15.0
                                base_friction = 0.9909 + (speed_factor * 0.00805)  # 30% less friction (0.91% to 0.105% energy loss)
                                moderate_friction = adjust_friction(base_friction)
                                ball.vx *= moderate_friction
                                ball.vy *= moderate_friction
                            else:
                                adjusted_friction = adjust_friction(0.99895)
                                ball.vx *= adjusted_friction
                                ball.vy *= adjusted_friction
                            
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