"""
utils.py - shared helpers for GlyphisIO BBS

Stuff I use everywhere: paths, timestamps, day/night logic, etc.
"""

import sys
import os
from datetime import datetime
from typing import Optional

# Need zoneinfo for Tokyo timezone - Python 3.9+ has it built in
try:
    from zoneinfo import ZoneInfo
except ImportError:
    # Older Python - try pytz, otherwise we fall back to UTC+9
    try:
        import pytz
        ZoneInfo = lambda tz: pytz.timezone(tz)
    except ImportError:
        ZoneInfo = None


def get_data_path(*path_parts):
    """
    Get path to Data folder - works when running as script or as built exe.
    Dev: Data/... relative to script. Exe: PyInstaller unpacks to sys._MEIPASS.
    """
    if getattr(sys, 'frozen', False):
        # Built exe - PyInstaller extracts assets to a temp folder
        base_path = sys._MEIPASS
    else:
        # Running from source
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    # Prefer Data subfolder, fall back to root if it doesn't exist
    data_folder = os.path.join(base_path, "Data")
    if os.path.exists(data_folder):
        return os.path.join(data_folder, *path_parts)
    else:
        return os.path.join(base_path, *path_parts)


def log_event(message: str) -> None:
    """Print to terminal with BBS timestamp prefix."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[BBS {timestamp}] {message}")


def get_realtime_datetime():
    """Current real-world time (user's local machine)."""
    return datetime.now()


def get_tokyo_datetime():
    """Current time in Tokyo - for anything that needs JP timezone."""
    if ZoneInfo:
        try:
            tokyo_tz = ZoneInfo("Asia/Tokyo")
            return datetime.now(tokyo_tz)
        except Exception:
            pass
    # No zoneinfo - use UTC+9 as approximation
    from datetime import timezone, timedelta
    tokyo_offset = timezone(timedelta(hours=9))
    return datetime.now(tokyo_offset)


def _is_tokyo_nighttime():
    """
    Is it nighttime right now? I use the user's local time but compare against
    Tokyo sunrise/sunset times (varies by month). Returns True if it's dark.
    """
    local_time = get_realtime_datetime()
    month = local_time.month
    hour = local_time.hour
    minute = local_time.minute
    current_time_minutes = hour * 60 + minute
    
    # Tokyo sunrise/sunset by month - (sunrise_hr, sunrise_min, sunset_hr, sunset_min)
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


def format_ingame_timestamp(dt=None):
    """Format as in-game timestamp - always shows 1989 for the year."""
    if dt is None:
        dt = get_realtime_datetime()
    try:
        dt = dt.replace(year=1989)
    except ValueError:
        pass  # edge case for leap years
    return dt.strftime("%Y-%m-%d %H:%M")


def format_ingame_clock(dt=None):
    """Just the time (HH:MM) for in-game clock display."""
    if dt is None:
        dt = get_realtime_datetime()
    return dt.strftime("%H:%M")


def normalize_timestamp_1989(timestamp_str):
    """Force any timestamp string into 1989 format - used for consistency."""
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


def _get_time_aware_video_name(base_filename: str) -> str:
    """
    Pick the right video filename for day vs night. If it's nighttime (based on
    my Tokyo sunrise/sunset logic above), I stick "night-" in front of the name
    so we load the dark version. Uses local time, not actual Tokyo timezone.
    """
    if _is_tokyo_nighttime():
        # Handle paths - only add night- to the filename part
        if '/' in base_filename or '\\' in base_filename:
            parts = base_filename.replace('\\', '/').rsplit('/', 1)
            if len(parts) == 2:
                return f"{parts[0]}/night-{parts[1]}"
            else:
                return f"night-{base_filename}"
        else:
            return f"night-{base_filename}"
    return base_filename


import re

