"""Steam integration manager for achievements and stats."""

from typing import Optional

from utils import log_event
from config import STEAM_APP_ID

# Try to import Steamworks API
try:
    import steamworks
    STEAMWORKS_AVAILABLE = True
except ImportError:
    STEAMWORKS_AVAILABLE = False
    steamworks = None
    print("Warning: steamworks library not available. Steam integration disabled.")


class SteamManager:
    """Manages Steam API integration for achievements and stats."""
    
    def __init__(self, app_id: Optional[int] = None):
        self.steam_api = None
        self.app_id = app_id or STEAM_APP_ID
        self.initialized = False
        
        if not STEAMWORKS_AVAILABLE:
            log_event("Steam integration unavailable (steamworks library not installed)")
            return
        
        try:
            # Initialize Steamworks API
            # Note: app_id should be your Steam App ID from Steam Partner portal
            if self.app_id:
                self.steam_api = steamworks.STEAMWORKS(self.app_id)
            else:
                # Try to initialize without explicit app_id (uses steam_appid.txt if present)
                self.steam_api = steamworks.STEAMWORKS()
            
            if self.steam_api.initialize():
                self.initialized = True
                log_event("Steam API initialized successfully")
            else:
                log_event("Steam API initialization failed (Steam client may not be running)")
                self.steam_api = None
        except Exception as exc:
            log_event(f"Steam API initialization error: {exc}")
            self.steam_api = None
    
    def is_available(self) -> bool:
        """Check if Steam API is available and initialized."""
        return self.initialized and self.steam_api is not None
    
    def run_callbacks(self) -> None:
        """Run Steam API callbacks. Should be called every frame."""
        if self.is_available():
            try:
                self.steam_api.run_callbacks()
            except Exception as exc:
                log_event(f"Steam callback error: {exc}")
    
    def unlock_achievement(self, achievement_id: str) -> bool:
        """Unlock a Steam achievement by ID.
        
        Args:
            achievement_id: The achievement API name from Steam Partner portal
            
        Returns:
            True if achievement was unlocked successfully, False otherwise
        """
        if not self.is_available():
            return False
        
        try:
            result = self.steam_api.Achievements.trigger(achievement_id)
            if result:
                log_event(f"Steam achievement unlocked: {achievement_id}")
            return result
        except Exception as exc:
            log_event(f"Failed to unlock Steam achievement '{achievement_id}': {exc}")
            return False
    
    def set_stat(self, stat_name: str, value: int) -> bool:
        """Set a Steam stat value.
        
        Args:
            stat_name: The stat API name from Steam Partner portal
            value: Integer value to set
            
        Returns:
            True if stat was set successfully, False otherwise
        """
        if not self.is_available():
            return False
        
        try:
            result = self.steam_api.Stats.set(stat_name, value)
            if result:
                self.steam_api.Stats.store()
            return result
        except Exception as exc:
            log_event(f"Failed to set Steam stat '{stat_name}': {exc}")
            return False
    
    def increment_stat(self, stat_name: str, amount: int = 1) -> bool:
        """Increment a Steam stat value.
        
        Args:
            stat_name: The stat API name from Steam Partner portal
            amount: Amount to increment by (default: 1)
            
        Returns:
            True if stat was incremented successfully, False otherwise
        """
        if not self.is_available():
            return False
        
        try:
            current_value = self.steam_api.Stats.get(stat_name)
            new_value = current_value + amount
            return self.set_stat(stat_name, new_value)
        except Exception as exc:
            log_event(f"Failed to increment Steam stat '{stat_name}': {exc}")
            return False
    
    def shutdown(self) -> None:
        """Shutdown Steam API. Should be called on application exit."""
        if self.is_available():
            try:
                self.steam_api.quit()
                log_event("Steam API shut down")
            except Exception as exc:
                log_event(f"Error shutting down Steam API: {exc}")
        self.initialized = False
        self.steam_api = None

