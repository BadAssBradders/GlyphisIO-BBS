import pygame
import json
import os
import logging
from typing import Tuple, Union

logger = logging.getLogger("ResolutionManager")

class ResolutionManager:
    def __init__(self, config_path="user_resolution.json"):
        self.config_path = config_path
        # Default baseline resolution (what the game was designed for)
        self.baseline_width = 2560
        self.baseline_height = 1440
        
        # Default current resolution (fallback)
        self.current_width = 1152
        self.current_height = 768
        self.fullscreen = False
        self.aspect_ratio = 1152/768
        
        # Centering offsets (updated when resolution changes)
        self.offset_x = 0
        self.offset_y = 0
        
        # Load saved settings
        self.load_settings()
        # Update offsets after loading
        self._update_offsets()

    def load_settings(self):
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    data = json.load(f)
                    self.current_width = data.get('width', self.current_width)
                    self.current_height = data.get('height', self.current_height)
                    self.fullscreen = data.get('fullscreen', self.fullscreen)
                    logger.info(f"Loaded resolution settings: {self.current_width}x{self.current_height}, Fullscreen: {self.fullscreen}")
            else:
                logger.info("No resolution settings found, using defaults.")
        except Exception as e:
            logger.error(f"Failed to load resolution settings: {e}")

    def save_settings(self):
        try:
            data = {
                'width': self.current_width,
                'height': self.current_height,
                'fullscreen': self.fullscreen
            }
            with open(self.config_path, 'w') as f:
                json.dump(data, f)
            logger.info("Saved resolution settings.")
        except Exception as e:
            logger.error(f"Failed to save resolution settings: {e}")

    def set_resolution(self, width, height, fullscreen=False):
        self.current_width = width
        self.current_height = height
        self.fullscreen = fullscreen
        self.aspect_ratio = width / height if height > 0 else 1.77
        self._update_offsets()
        self.save_settings()

    def _update_offsets(self):
        """Update centering offsets based on current resolution."""
        self.offset_x, self.offset_y = self.get_centering_offsets()

    def get_resolution(self):
        return (self.current_width, self.current_height)

    def is_fullscreen(self):
        return self.fullscreen

    def apply(self):
        flags = pygame.RESIZABLE
        if self.fullscreen:
            flags |= pygame.FULLSCREEN
        
        try:
            screen = pygame.display.set_mode((self.current_width, self.current_height), flags)
            logger.info(f"Display mode set to {self.current_width}x{self.current_height}")
            
            # Recalculate aspect ratio and centering if actual resolution differs (e.g. fullscreen 0,0)
            if self.current_width == 0:
                w, h = screen.get_size()
                self.current_width = w
                self.current_height = h
                self._update_offsets()
            
            return screen
        except Exception as e:
            logger.error(f"Failed to set display mode: {e}")
            # Fallback
            return pygame.display.set_mode((1152, 768), pygame.RESIZABLE)

    def get_scale_factors(self):
        """Get separate X and Y scale factors."""
        scale_x = self.current_width / self.baseline_width
        scale_y = self.current_height / self.baseline_height
        return scale_x, scale_y

    def get_ui_scale(self):
        """Returns a single scale factor for uniform UI scaling (preserves aspect ratio)."""
        scale_x, scale_y = self.get_scale_factors()
        return min(scale_x, scale_y)
        
    def get_centering_offsets(self):
        """
        Calculate offsets to center the content (16:9 baseline) on the current screen.
        Returns (offset_x, offset_y)
        """
        scale = self.get_ui_scale()
        content_width = int(self.baseline_width * scale)
        content_height = int(self.baseline_height * scale)
        
        offset_x = (self.current_width - content_width) // 2
        offset_y = (self.current_height - content_height) // 2
        
        return max(0, offset_x), max(0, offset_y)

    # ============================================================================
    # COORDINATE TRANSFORMATION METHODS
    # ============================================================================
    # These methods transform coordinates from baseline (2560x1440) to current resolution
    # All methods account for uniform scaling and centering offsets

    def transform_x(self, baseline_x: float) -> int:
        """
        Transform X coordinate from baseline to current resolution.
        
        Args:
            baseline_x: X coordinate in baseline resolution (2560x1440)
            
        Returns:
            Transformed X coordinate in current resolution
        """
        scale = self.get_ui_scale()
        return int(baseline_x * scale) + self.offset_x

    def transform_y(self, baseline_y: float) -> int:
        """
        Transform Y coordinate from baseline to current resolution.
        
        Args:
            baseline_y: Y coordinate in baseline resolution (2560x1440)
            
        Returns:
            Transformed Y coordinate in current resolution
        """
        scale = self.get_ui_scale()
        return int(baseline_y * scale) + self.offset_y

    def transform_pos(self, baseline_x: float, baseline_y: float) -> Tuple[int, int]:
        """
        Transform position (x, y) from baseline to current resolution.
        
        Args:
            baseline_x: X coordinate in baseline resolution
            baseline_y: Y coordinate in baseline resolution
            
        Returns:
            Tuple of (transformed_x, transformed_y) in current resolution
        """
        return (self.transform_x(baseline_x), self.transform_y(baseline_y))

    def transform_width(self, baseline_width: float) -> int:
        """
        Transform width from baseline to current resolution.
        
        Args:
            baseline_width: Width in baseline resolution
            
        Returns:
            Transformed width in current resolution
        """
        scale = self.get_ui_scale()
        return int(baseline_width * scale)

    def transform_height(self, baseline_height: float) -> int:
        """
        Transform height from baseline to current resolution.
        
        Args:
            baseline_height: Height in baseline resolution
            
        Returns:
            Transformed height in current resolution
        """
        scale = self.get_ui_scale()
        return int(baseline_height * scale)

    def transform_size(self, baseline_width: float, baseline_height: float) -> Tuple[int, int]:
        """
        Transform size (width, height) from baseline to current resolution.
        
        Args:
            baseline_width: Width in baseline resolution
            baseline_height: Height in baseline resolution
            
        Returns:
            Tuple of (transformed_width, transformed_height) in current resolution
        """
        return (self.transform_width(baseline_width), self.transform_height(baseline_height))

    def transform_rect(self, baseline_rect: Union[pygame.Rect, Tuple[float, float, float, float]]) -> pygame.Rect:
        """
        Transform a rectangle from baseline to current resolution.
        
        Args:
            baseline_rect: Either a pygame.Rect or tuple (x, y, width, height) in baseline resolution
            
        Returns:
            pygame.Rect in current resolution
        """
        if isinstance(baseline_rect, pygame.Rect):
            x, y, w, h = baseline_rect.x, baseline_rect.y, baseline_rect.width, baseline_rect.height
        else:
            x, y, w, h = baseline_rect
        
        return pygame.Rect(
            self.transform_x(x),
            self.transform_y(y),
            self.transform_width(w),
            self.transform_height(h)
        )

    def transform_hotspot(self, hotspot: Tuple[float, float, float, float]) -> pygame.Rect:
        """
        Transform a hotspot (x, y, width, height) from baseline to current resolution.
        
        Args:
            hotspot: Tuple of (x, y, width, height) in baseline resolution
            
        Returns:
            pygame.Rect in current resolution (for use with collidepoint)
        """
        x, y, w, h = hotspot
        return pygame.Rect(
            self.transform_x(x),
            self.transform_y(y),
            self.transform_width(w),
            self.transform_height(h)
        )

    # ============================================================================
    # REVERSE TRANSFORMATION METHODS (for mouse coordinates)
    # ============================================================================
    # These methods transform coordinates from current resolution back to baseline

    def reverse_transform_x(self, current_x: float) -> float:
        """
        Transform X coordinate from current resolution back to baseline.
        
        Args:
            current_x: X coordinate in current resolution
            
        Returns:
            X coordinate in baseline resolution
        """
        scale = self.get_ui_scale()
        if scale == 0:
            return 0.0
        return (current_x - self.offset_x) / scale

    def reverse_transform_y(self, current_y: float) -> float:
        """
        Transform Y coordinate from current resolution back to baseline.
        
        Args:
            current_y: Y coordinate in current resolution
            
        Returns:
            Y coordinate in baseline resolution
        """
        scale = self.get_ui_scale()
        if scale == 0:
            return 0.0
        return (current_y - self.offset_y) / scale

    def reverse_transform_pos(self, current_x: float, current_y: float) -> Tuple[float, float]:
        """
        Transform position (x, y) from current resolution back to baseline.
        
        Args:
            current_x: X coordinate in current resolution
            current_y: Y coordinate in current resolution
            
        Returns:
            Tuple of (baseline_x, baseline_y)
        """
        return (self.reverse_transform_x(current_x), self.reverse_transform_y(current_y))

    def reverse_transform_rect(self, current_rect: pygame.Rect) -> pygame.Rect:
        """
        Transform a rectangle from current resolution back to baseline.
        
        Args:
            current_rect: pygame.Rect in current resolution
            
        Returns:
            pygame.Rect in baseline resolution
        """
        scale = self.get_ui_scale()
        if scale == 0:
            return pygame.Rect(0, 0, 0, 0)
        
        return pygame.Rect(
            self.reverse_transform_x(current_rect.x),
            self.reverse_transform_y(current_rect.y),
            current_rect.width / scale,
            current_rect.height / scale
        )

# Global instance
resolution_manager = ResolutionManager()
