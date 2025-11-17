"""
Utility functions for GlyphisIO BBS.

Common helper functions used throughout the application.
"""

import sys
import os
from datetime import datetime
from typing import Optional

# Try to import zoneinfo for timezone support (Python 3.9+)
try:
    from zoneinfo import ZoneInfo
except ImportError:
    # Fallback for Python < 3.9 - use pytz if available, otherwise approximate
    try:
        import pytz
        ZoneInfo = lambda tz: pytz.timezone(tz)
    except ImportError:
        ZoneInfo = None


def get_data_path(*path_parts):
    """
    Returns the path to the Data folder, handling both development and built executable scenarios.
    
    In development: returns "Data/..." relative to script directory
    In built exe: returns path to Data folder bundled with executable
    """
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        # PyInstaller sets sys._MEIPASS to the temp folder where it extracts files
        base_path = sys._MEIPASS
    else:
        # Running as script
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    # Check if Data folder exists, if not fall back to root (for backwards compatibility)
    data_folder = os.path.join(base_path, "Data")
    if os.path.exists(data_folder):
        return os.path.join(data_folder, *path_parts)
    else:
        # Fallback: look in root directory (for backwards compatibility during transition)
        return os.path.join(base_path, *path_parts)


def log_event(message: str) -> None:
    """Simple logging helper for terminal output."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[BBS {timestamp}] {message}")


def get_realtime_datetime():
    """Get current real-world datetime."""
    return datetime.now()


def get_tokyo_datetime():
    """Get current datetime in Tokyo timezone."""
    if ZoneInfo:
        try:
            tokyo_tz = ZoneInfo("Asia/Tokyo")
            return datetime.now(tokyo_tz)
        except Exception:
            pass
    # Fallback: approximate Tokyo time (UTC+9)
    from datetime import timezone, timedelta
    tokyo_offset = timezone(timedelta(hours=9))
    return datetime.now(tokyo_offset)


def _is_tokyo_nighttime():
    """Check if it's nighttime in Tokyo (between 18:00 and 6:00)."""
    tokyo_dt = get_tokyo_datetime()
    hour = tokyo_dt.hour
    return hour >= 18 or hour < 6


def format_ingame_timestamp(dt=None):
    """Format datetime as in-game timestamp (1989 format)."""
    if dt is None:
        dt = get_realtime_datetime()
    return dt.strftime("%Y-%m-%d %H:%M")


def format_ingame_clock(dt=None):
    """Format datetime as in-game clock display."""
    if dt is None:
        dt = get_realtime_datetime()
    return dt.strftime("%H:%M")


def normalize_timestamp_1989(timestamp_str):
    """Normalize timestamp string to 1989 format if needed."""
    if not timestamp_str:
        return format_ingame_timestamp()
    if timestamp_str.startswith("1989-"):
        return timestamp_str
    try:
        if " " in timestamp_str:
            date_part, time_part = timestamp_str.split(" ", 1)
        else:
            date_part, time_part = timestamp_str, ""
        date_parts = date_part.split("-")
        if len(date_parts) >= 3:
            date_parts[0] = "1989"
            date_part = "-".join(date_parts)
        timestamp_str = f"{date_part} {time_part}".strip()
    except Exception:
        timestamp_str = format_ingame_timestamp()
    if not timestamp_str.startswith("1989-"):
        timestamp_str = format_ingame_timestamp()
    return timestamp_str


def _is_tokyo_nighttime():
    """
    Determine if it's currently nighttime using local system time.
    Uses Tokyo's sunrise/sunset times as a reference for day/night transitions.
    Returns True if it's after sunset or before sunrise.
    """
    local_time = get_realtime_datetime()
    month = local_time.month
    hour = local_time.hour
    minute = local_time.minute
    current_time_minutes = hour * 60 + minute
    
    # Tokyo sunrise and sunset times by month
    sunrise_sunset_times = {
        1: (6, 48, 16, 52),   # January
        2: (6, 26, 17, 23),   # February
        3: (5, 50, 17, 49),   # March
        4: (5, 7, 18, 15),    # April
        5: (4, 34, 18, 40),   # May
        6: (4, 23, 19, 0),    # June
        7: (4, 35, 18, 59),   # July
        8: (4, 58, 18, 32),   # August
        9: (5, 22, 17, 50),   # September
        10: (5, 46, 17, 7),   # October
        11: (6, 15, 16, 35),  # November
        12: (6, 42, 16, 30),  # December
    }
    
    sunrise_hour, sunrise_minute, sunset_hour, sunset_minute = sunrise_sunset_times.get(month, (6, 0, 18, 0))
    sunrise_minutes = sunrise_hour * 60 + sunrise_minute
    sunset_minutes = sunset_hour * 60 + sunset_minute
    
    return current_time_minutes < sunrise_minutes or current_time_minutes >= sunset_minutes


def _get_time_aware_video_name(base_filename: str) -> str:
    """
    Returns the appropriate video filename based on local system time.
    Uses Tokyo sunrise/sunset times as reference for day/night transitions.
    """
    if _is_tokyo_nighttime():
        if '/' in base_filename or '\\' in base_filename:
            parts = base_filename.replace('\\', '/').rsplit('/', 1)
            if len(parts) == 2:
                return f"{parts[0]}/night-{parts[1]}"
            else:
                return f"night-{base_filename}"
        else:
            return f"night-{base_filename}"
    return base_filename


# Import re for normalize_timestamp_1989
import re

