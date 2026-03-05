from dataclasses import dataclass
from typing import Tuple
import pygame

# --- Normalized display resolution (avoids stretch/hotspot issues on odd resolutions) ---
# Preferred: game runs at this even on 4K+.
PREFERRED_WIDTH = 2560
PREFERRED_HEIGHT = 1440
# Fallback: used for any non-blessed resolution (e.g. 2304x1536) so layout stays correct.
FALLBACK_WIDTH = 1920
FALLBACK_HEIGHT = 1080

BLESSED_RESOLUTIONS = (
    (PREFERRED_WIDTH, PREFERRED_HEIGHT),
    (FALLBACK_WIDTH, FALLBACK_HEIGHT),
)


def get_effective_resolution(display_width: int, display_height: int) -> Tuple[int, int]:
    """
    Return a resolution the game should actually use for the display.
    - If display is >= 2560x1440 (e.g. 4K): use 2560x1440 (cap).
    - If display is exactly 1920x1080 or 2560x1440: use it.
    - Otherwise (e.g. 2304x1536): use 1920x1080 so layout and hotspots stay correct.
    """
    if display_width >= PREFERRED_WIDTH and display_height >= PREFERRED_HEIGHT:
        return (PREFERRED_WIDTH, PREFERRED_HEIGHT)
    if (display_width, display_height) in BLESSED_RESOLUTIONS:
        return (display_width, display_height)
    return (FALLBACK_WIDTH, FALLBACK_HEIGHT)


@dataclass
class ResolutionManager:
    """
    Centralized manager for screen resolution, scaling, and positioning.
    Maintains a consistent aspect ratio relative to a baseline resolution (1440p).
    """
    screen_width: int
    screen_height: int
    baseline_width: int = 2560
    baseline_height: int = 1440
    
    def __post_init__(self):
        self._calculate_metrics()

    def update_screen_dimensions(self, width: int, height: int):
        """Update screen dimensions and recalculate scaling metrics."""
        self.screen_width = width
        self.screen_height = height
        self._calculate_metrics()

    def _calculate_metrics(self):
        # Calculate scale factor to fit baseline into current screen while maintaining aspect ratio
        scale_x = self.screen_width / self.baseline_width
        scale_y = self.screen_height / self.baseline_height
        self.scale_factor = min(scale_x, scale_y)
        
        # Calculate scaled dimensions of the baseline area
        self.scaled_width = int(self.baseline_width * self.scale_factor)
        self.scaled_height = int(self.baseline_height * self.scale_factor)
        
        # Calculate padding to center the content
        self.padding_x = (self.screen_width - self.scaled_width) // 2
        self.padding_y = (self.screen_height - self.scaled_height) // 2

    def scale(self, value: float) -> int:
        """Scale a value by the global scale factor."""
        return int(value * self.scale_factor)

    def coords(self, x: float, y: float) -> Tuple[int, int]:
        """
        Convert baseline coordinates to current screen coordinates.
        Applies scaling and centering offset.
        """
        scaled_x = int(x * self.scale_factor) + self.padding_x
        scaled_y = int(y * self.scale_factor) + self.padding_y
        return (scaled_x, scaled_y)

    def rect(self, x: float, y: float, w: float, h: float) -> pygame.Rect:
        """
        Create a pygame.Rect from baseline coordinates and dimensions.
        """
        sx, sy = self.coords(x, y)
        sw = self.scale(w)
        sh = self.scale(h)
        return pygame.Rect(sx, sy, sw, sh)

    def get_desktop_rect(self) -> pygame.Rect:
        """
        Get the standard desktop area rect.
        Based on OS Mode baseline: x=176, y=209 overlay on 2560x1440.
        Note: The actual desktop image size might be different, but this is the placement.
        """
        # Original logic was:
        # self.baseline_desktop_x = 176
        # self.baseline_desktop_y = 209
        # But we need the width/height too.
        # In OS_Mode: 
        # desktop_path = get_data_path("OS", "Desktop-Enviroment.png")
        # Image loaded then scaled.
        # Let's assume the desktop fills the rest or has a specific size.
        # Looking at OS_Mode.py:
        # self.desktop_size = (int(original_size[0] * scale), ...)
        # We might need to standardize this. For now, let's provide the origin.
        
        # NOTE: This method might need adjustment if the desktop image size is fixed/known.
        # For now, returning the top-left coordinate helper.
        return self.rect(176, 209, 0, 0) # width/height 0 for now, just for pos

    def get_bbs_rect(self) -> pygame.Rect:
        """
        Get the standard BBS window rect.
        Baseline: 1920x1080 usually centered or at specific pos.
        In main.py: BASELINE_BBS_WIDTH = 1000, BASELINE_BBS_HEIGHT = 800 (examples need verification)
        Actaully main.py imports `config`. Let's assume standard behavior.
        """
        # We default to 0,0,0,0 here, trusting the caller to pass specific baseline constants
        # if they differ from the defaults.
        return self.rect(0, 0, 0, 0)
