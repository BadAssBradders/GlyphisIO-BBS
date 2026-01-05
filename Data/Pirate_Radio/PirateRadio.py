"""
Pirate Radio App for OS Mode
Radio packet sniffer tool that runs within the OS environment.
Features real-time radio station playback after completing tone patterns.
"""

import pygame
import random
import sys
import os
import math
import time
from typing import List, Dict, Tuple, Optional, Callable
from datetime import datetime
from systems.resolution import ResolutionManager

# Try to import cv2 for video playback
try:
    import cv2
    import numpy as np
    _cv2_available = True
except ImportError:
    _cv2_available = False
    cv2 = None
    np = None

# ------------- CONFIG -----------------

# Intro video and splash screen
INTRO_VIDEO = "Intro1.mp4"
INTRO_AUDIO = "TSW.wav"
SPLASH_IMAGE = "SPASH1.png"

# Overlay image
OVERLAY_IMAGE = "OVERLAY-Radio.png"

# Background animation frames
BACKGROUND_FRAMES = [
    "PirateRadio-Still1.png",
    "PirateRadio-Still2.png",
    "PirateRadio-Still3.png",
    "PirateRadio-Still4.png",
    "PirateRadio-Still5.png",
    "PirateRadio-Still6.png",
]
BACKGROUND_FRAME_DURATION = 300  # ms per frame

NOISE_FILE = "noise.wav"
NOISE_BASE_VOLUME = 0.45
STATION_DIR = "Live_Stations"
TONE_FILES = {
    "low": "low.wav",
    "mid": "mid.wav",
    "high": "high.wav",
    "whistle": "whistle.wav",
}

PATTERN_LENGTHS = [4, 7, 10]

# Grid Animation
GRID_CELL_SIZE = 30
# Equalizer
EQ_COLOR_START = (0x31, 0x59, 0x57)  # #315957
EQ_COLOR_END = (0x00, 0xff, 0xf0)    # #00fff0
EQ_BAR_WIDTH = 7.5  # Increased by 25% (from 6 to 7.5)
EQ_BAR_ALPHA = 217  # 85% opacity (0.85 * 255)
EQ_SPAWN_INTERVAL = 120  # ms between new bars when active

# Colors
CYAN = (0, 255, 255)
MAGENTA = (255, 0, 255)
WHITE = (255, 255, 255)
GREEN = (0, 255, 128)
YELLOW = (255, 255, 0)
BLACK = (0, 0, 0)
DARK = (0, 10, 20)
UNCLE_AM_COLOR = (119, 93, 182)  # #775db6
HACK_STATUS_COLOR = (107, 220, 128)  # #6bdc80
HEADER_PURPLE = (142, 93, 200)  # #8e5dc8
OPERATOR_GREEN = (125, 215, 141)  # #7dd78d
LIVE_MSG_PINK = (255, 0, 255)  # Bright Magenta for live line
HISTORY_PURPLE = (134, 66, 164)  # #8642a4
DARK_CYAN = (0, 60, 80)  # Dark cyan for selection highlight

# Radio Station Definitions
# All stations have -DeTuned (default) and -Tuned variants
# User presses right arrow 3 times to switch from DeTuned to Tuned
NIGHT_STATIONS = [
    {"name": "Tokyo Yamoto Forever", "file": "TokyoYamoto-DeTuned.wav", "tuned_file": "TokyoYamoto-Tuned.wav", "freq": 9970},
    {"name": "Hotline Underground", "file": "HotlineUnderground-DeTuned.wav", "tuned_file": "HotlineUnderground-Tuned.wav", "freq": 7425},
    {"name": "Radio Nippon", "file": "RadioNippon-DeTuned.wav", "tuned_file": "RadioNippon-Tuned.wav", "freq": 558},
    {"name": "Shojo AM", "file": "ShojoAM-DeTuned.wav", "tuned_file": "ShojoAM-Tuned.wav", "freq": 1242},
    {"name": "Synth Rebels", "file": "SynthRebels-DeTuned.wav", "tuned_file": "SynthRebels-Tuned.wav", "freq": 9150},
]

DAY_STATIONS = [
    {"name": "Morning Drift", "file": "MorningDrift-DeTuned.wav", "tuned_file": "MorningDrift-Tuned.wav", "freq": 6045},
    {"name": "Pacific Wave", "file": "PacificWave-DeTuned.wav", "tuned_file": "PacificWave-Tuned.wav", "freq": 1314},
    {"name": "Sunrise Radio", "file": "SunriseRadio-DeTuned.wav", "tuned_file": "SunriseRadio-Tuned.wav", "freq": 909},
    {"name": "Coast FM", "file": "CoastFM-DeTuned.wav", "tuned_file": "CoastFM-Tuned.wav", "freq": 1017},
    {"name": "Echo Chamber", "file": "EchoChamber-DeTuned.wav", "tuned_file": "EchoChamber-Tuned.wav", "freq": 15050},
]


def get_data_path(*path_parts):
    """
    Returns the path to the Data folder, handling both development and built executable scenarios.
    Assumes this file lives in Data/Pirate_Radio.
    """
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        # Script dir is Data/Pirate_Radio
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # Base path is Data/Pirate_Radio (assets are here)
        base_path = script_dir
    
    return os.path.join(base_path, *path_parts)


def _is_nighttime():
    """
    Determine if it's currently nighttime using local system time.
    Uses Tokyo's sunrise/sunset times as a reference for day/night transitions.
    Returns True if it's after sunset or before sunrise.
    """
    local_time = datetime.now()
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


class RadioStationManager:
    """
    Manages real-time radio station time tracking with precise seconds.
    Creates the illusion of live radio by tracking elapsed time across all stations.
    All stations play simultaneously with volume control.
    """
    def __init__(self):
        # Precise time positions for each station (in seconds, 0-3599 for 60 minutes)
        self.station_seconds: Dict[str, float] = {}
        self.initialized = False
        self.last_tick_time = 0.0
        
        # Simultaneous playback: all stations play at once
        # Maps station_name -> {"detuned_channel": Channel, "tuned_channel": Channel, 
        #                        "detuned_sound": Sound, "tuned_sound": Sound,
        #                        "detuned_volume": float, "tuned_volume": float,
        #                        "playback_start_time": float, "playback_start_seconds": float}
        self.station_channels: Dict[str, Dict] = {}
        
        # Currently selected station (for volume control)
        self.selected_station: Optional[str] = None
        
        # Fine-tuning state: 0 = detuned at 80%, 1 = 50% detuned + 30% tuned, 
        # 2 = 20% detuned + 60% tuned, 3 = 0% detuned + 80% tuned
        self.tune_level = 0  # 0-3, where 3 is fully tuned
        
    def initialize_minutes(self, stations: List[Dict]):
        """Initialize deterministic starting positions for all stations based on real-world time."""
        for station in stations:
            station_name = station["name"]
            if station_name not in self.station_seconds:
                # Use a deterministic offset based on name so different app instances stay in sync
                name_hash = sum(ord(c) * (i + 1) for i, c in enumerate(station_name))
                self.station_seconds[station_name] = float(name_hash % 3600)
        
        if not self.initialized:
            # Anchor to epoch for true "live" behavior that persists across restarts/instances
            self.last_tick_time = 0.0 
            self.initialized = True
            # First tick will catch up from epoch to current time
            self.tick()
        
    def tick(self):
        """
        Update all station times with precise second tracking. Called every frame.
        All stations tick up together continuously once initialized, simulating live radio.
        """
        if not self.initialized:
            return
            
        current_time = time.time()
        
        # Initialize last_tick_time if not set
        if self.last_tick_time == 0.0:
            self.last_tick_time = current_time
            return
        
        elapsed = current_time - self.last_tick_time
        
        # Update all stations by exact elapsed seconds
        if elapsed > 0.0:
            for station_name in self.station_seconds:
                # Use modulo for efficient wrap-around at 3600 seconds (60 minutes)
                self.station_seconds[station_name] = (self.station_seconds[station_name] + elapsed) % 3600.0
            self.last_tick_time = current_time
            
    def get_station_minute(self, station_name: str) -> int:
        """Get the current minute position for a station (1-60)."""
        self.tick()  # Ensure time is up to date
        seconds = self.station_seconds.get(station_name, 0.0)
        # Convert seconds to minute (1-60)
        minute = int(seconds // 60) + 1
        return minute if minute <= 60 else 60
    
    def get_station_seconds(self, station_name: str) -> float:
        """Get the precise current time position in seconds (0.0-3599.99)."""
        self.tick()  # Ensure time is up to date
        return self.station_seconds.get(station_name, 0.0)
    
    def get_station_time_formatted(self, station_name: str) -> Tuple[int, int]:
        """Get the current time as (minutes, seconds) tuple. Minutes are 0-59, seconds are 0-59."""
        self.tick()  # Ensure time is up to date
        total_seconds = self.station_seconds.get(station_name, 0.0)
        minutes = int(total_seconds // 60) % 60
        seconds = int(total_seconds % 60)
        return (minutes, seconds)
        
    def initialize_station_playback(self, station: Dict, detuned_sound: pygame.mixer.Sound, 
                                    tuned_sound: Optional[pygame.mixer.Sound], 
                                    station_path_func: Callable) -> bool:
        """
        Initialize playback for a station (both detuned and tuned versions).
        All stations start playing at 0% volume and will be controlled via volume.
        
        Args:
            station: Station dictionary
            detuned_sound: Sound object for detuned version
            tuned_sound: Sound object for tuned version (can be None)
            station_path_func: Function to resolve station file paths (not currently used, kept for compatibility)
        
        Returns:
            True if initialization was successful, False otherwise
        """
        station_name = station["name"]
        
        # Safety check: detuned_sound must exist
        if not detuned_sound:
            print(f"Warning: No detuned sound for station {station_name}")
            return False
        
        self.tick()  # Ensure time is up to date
        
        # Get precise seconds position
        start_seconds = self.get_station_seconds(station_name)
        
        # Get sound length
        try:
            sound_length = detuned_sound.get_length()
        except Exception as e:
            print(f"Warning: Could not get length for {station_name} detuned sound: {e}")
            return False
        
        # Wrap start position if beyond sound length
        if start_seconds >= sound_length:
            start_seconds = start_seconds % max(1, sound_length)
        
        # Play detuned version (looping)
        try:
            # Get a free channel explicitly
            detuned_channel = pygame.mixer.find_channel()
            if not detuned_channel:
                print(f"Warning: No free channel available for {station_name} detuned sound")
                return False
            detuned_channel.play(detuned_sound, loops=-1)
            detuned_channel.set_volume(0.0)  # Start at 0%
            # Verify it's actually playing
            if not detuned_channel.get_busy():
                print(f"Warning: {station_name} detuned channel not playing after start")
                return False
        except Exception as e:
            print(f"Warning: Could not play {station_name} detuned sound: {e}")
            return False
        
        # Play tuned version if available (looping)
        tuned_channel = None
        if tuned_sound:
            try:
                # Get a free channel explicitly
                tuned_channel = pygame.mixer.find_channel()
                if tuned_channel:
                    tuned_channel.play(tuned_sound, loops=-1)
                    tuned_channel.set_volume(0.0)  # Start at 0%
                    # Verify it's actually playing
                    if not tuned_channel.get_busy():
                        print(f"Warning: {station_name} tuned channel not playing after start")
                        tuned_channel = None
                else:
                    print(f"Warning: No free channel available for {station_name} tuned sound")
            except Exception as e:
                print(f"Warning: Could not play {station_name} tuned sound: {e}")
        
        # Store channel references and state
        self.station_channels[station_name] = {
            "detuned_channel": detuned_channel,
            "tuned_channel": tuned_channel,
            "detuned_sound": detuned_sound,
            "tuned_sound": tuned_sound,
            "detuned_volume": 0.0,
            "tuned_volume": 0.0,
            "playback_start_time": time.time(),
            "playback_start_seconds": start_seconds
        }
        
        return True
    
    def select_station(self, station_name: str):
        """
        Select a station - sets its detuned version to 80% volume, all others to 0%.
        Resets fine-tuning level to 0.
        """
        # Set all stations to 0% volume first
        for name, channels in self.station_channels.items():
            if channels["detuned_channel"]:
                try:
                    # Check if channel is still playing, restart if needed
                    if not channels["detuned_channel"].get_busy():
                        # Channel stopped, restart it
                        channels["detuned_channel"] = channels["detuned_sound"].play(-1)
                    if channels["detuned_channel"]:
                        channels["detuned_channel"].set_volume(0.0)
                        channels["detuned_volume"] = 0.0
                except Exception as e:
                    print(f"Warning: Error setting volume for {name} detuned: {e}")
            if channels["tuned_channel"]:
                try:
                    # Check if channel is still playing, restart if needed
                    if not channels["tuned_channel"].get_busy():
                        # Channel stopped, restart it
                        if channels["tuned_sound"]:
                            channels["tuned_channel"] = channels["tuned_sound"].play(-1)
                    if channels["tuned_channel"]:
                        channels["tuned_channel"].set_volume(0.0)
                        channels["tuned_volume"] = 0.0
                except Exception as e:
                    print(f"Warning: Error setting volume for {name} tuned: {e}")
        
        # Set selected station detuned to 80%
        if station_name in self.station_channels:
            channels = self.station_channels[station_name]
            if channels["detuned_channel"]:
                try:
                    # Ensure channel is playing
                    if not channels["detuned_channel"].get_busy():
                        channels["detuned_channel"] = channels["detuned_sound"].play(-1)
                    if channels["detuned_channel"]:
                        # Verify channel is actually playing
                        if not channels["detuned_channel"].get_busy():
                            print(f"Warning: {station_name} detuned channel not busy, restarting...")
                            new_channel = pygame.mixer.find_channel()
                            if new_channel:
                                new_channel.play(channels["detuned_sound"], loops=-1)
                                channels["detuned_channel"] = new_channel
                            else:
                                channels["detuned_channel"] = channels["detuned_sound"].play(-1)
                        if channels["detuned_channel"] and channels["detuned_channel"].get_busy():
                            channels["detuned_channel"].set_volume(0.8)
                            channels["detuned_volume"] = 0.8
                            # Double-check volume was set
                            actual_vol = channels["detuned_channel"].get_volume()
                            is_busy = channels["detuned_channel"].get_busy()
                            print(f"Selected station {station_name}, set detuned volume to 0.8 (actual: {actual_vol:.2f}, busy: {is_busy})")
                        else:
                            print(f"Error: Could not get working channel for {station_name} detuned")
                except Exception as e:
                    print(f"Warning: Error setting volume for {station_name} detuned: {e}")
        else:
            print(f"Warning: Station {station_name} not found in station_channels")
        
        self.selected_station = station_name
        self.tune_level = 0  # Reset fine-tuning
    
    def fine_tune_right(self):
        """
        Fine tune to the right: increase tuned volume by 30%, decrease detuned by 30%.
        Final press (level 3): detuned at 0%, tuned at 80%.
        """
        if not self.selected_station or self.selected_station not in self.station_channels:
            return
        
        channels = self.station_channels[self.selected_station]
        
        # Can't tune if no tuned version available
        if not channels["tuned_channel"] or not channels["tuned_sound"]:
            print(f"Warning: No tuned version available for {self.selected_station}")
            return
        
        # Increment tune level (0 -> 1 -> 2 -> 3, max 3)
        if self.tune_level < 3:
            self.tune_level += 1
        
        # Calculate volumes based on tune level
        # Level 0: 80% detuned, 0% tuned
        # Level 1: 50% detuned, 30% tuned
        # Level 2: 20% detuned, 60% tuned
        # Level 3: 0% detuned, 80% tuned
        detuned_vol = max(0.0, 0.8 - (self.tune_level * 0.3))
        tuned_vol = min(0.8, self.tune_level * 0.3)
        
        # Ensure channels are playing
        try:
            if channels["detuned_channel"]:
                if not channels["detuned_channel"].get_busy():
                    channels["detuned_channel"] = channels["detuned_sound"].play(-1)
                if channels["detuned_channel"]:
                    channels["detuned_channel"].set_volume(detuned_vol)
                    channels["detuned_volume"] = detuned_vol
            
            if channels["tuned_channel"]:
                if not channels["tuned_channel"].get_busy():
                    channels["tuned_channel"] = channels["tuned_sound"].play(-1)
                if channels["tuned_channel"]:
                    channels["tuned_channel"].set_volume(tuned_vol)
                    channels["tuned_volume"] = tuned_vol
                    print(f"Fine tuning {self.selected_station}: detuned={detuned_vol:.1f}, tuned={tuned_vol:.1f}")
        except Exception as e:
            print(f"Warning: Error fine-tuning {self.selected_station}: {e}")
    
    def fine_tune_left(self):
        """
        Fine tune to the left: decrease tuned volume, increase detuned volume.
        """
        if not self.selected_station or self.selected_station not in self.station_channels:
            return
        
        channels = self.station_channels[self.selected_station]
        
        # Decrement tune level (min 0)
        if self.tune_level > 0:
            self.tune_level -= 1
        
        # Calculate volumes based on tune level
        detuned_vol = max(0.0, 0.8 - (self.tune_level * 0.3))
        tuned_vol = min(0.8, self.tune_level * 0.3)
        
        # Apply volumes
        if channels["detuned_channel"]:
            channels["detuned_channel"].set_volume(detuned_vol)
            channels["detuned_volume"] = detuned_vol
        if channels["tuned_channel"]:
            channels["tuned_channel"].set_volume(tuned_vol)
            channels["tuned_volume"] = tuned_vol
        
    def stop_all(self):
        """Stop all station playback."""
        for channels in self.station_channels.values():
            if channels["detuned_channel"]:
                channels["detuned_channel"].stop()
            if channels["tuned_channel"]:
                channels["tuned_channel"].stop()
        self.station_channels.clear()
        self.selected_station = None
        self.tune_level = 0
        
    def stop_current(self):
        """Stop the currently selected station (set all volumes to 0)."""
        if self.selected_station and self.selected_station in self.station_channels:
            channels = self.station_channels[self.selected_station]
            if channels["detuned_channel"]:
                channels["detuned_channel"].set_volume(0.0)
                channels["detuned_volume"] = 0.0
            if channels["tuned_channel"]:
                channels["tuned_channel"].set_volume(0.0)
                channels["tuned_volume"] = 0.0
        self.selected_station = None
        self.tune_level = 0
        
    def is_playing(self) -> bool:
        """Check if any station is currently playing (has volume > 0)."""
        for channels in self.station_channels.values():
            if channels["detuned_volume"] > 0.0 or channels["tuned_volume"] > 0.0:
                return True
        return False
    
    @property
    def current_playing_station(self) -> Optional[str]:
        """Get the currently selected/playing station name."""
        return self.selected_station


class ChatSystem:
    def __init__(self, font, max_x, start_x, live_y, header_pos):
        self.queue = []
        self.history = []
        self.live_text = ""
        self.current_full_msg = ""
        self.state = "IDLE"  # IDLE, ANIM_DOTS, TYPING, WAIT_WRAP, WAIT_NEXT
        self.timer = 0
        self.typing_idx = 0
        self.wrap_pause = 2000
        self.msg_pause = 2000
        self.anim_duration = 3000
        self.dot_cycles = 1
        self.max_x = max_x
        self.start_x = start_x
        self.live_y = live_y
        self.font = font
        self.header_pos = header_pos
        self.scroll_offset = 0
        self.cursor_blink_state = True
        self.cursor_blink_timer = 0
        self.on_message_complete: Optional[Callable[[str], None]] = None

    def queue_message(self, msg):
        self.queue.append(msg)
        if self.state == "IDLE":
            self.start_anim()

    def start_anim(self):
        self.state = "ANIM_DOTS"
        self.timer = pygame.time.get_ticks()
        self.live_text = ""
        
        if self.history:
            last_msg = self.history[-1]
            if last_msg.strip().endswith("."):
                self.dot_cycles = 8
            else:
                self.dot_cycles = 2
        else:
            self.dot_cycles = 2
            
        self.anim_duration = self.dot_cycles * 900

    def update(self):
        now = pygame.time.get_ticks()
        
        if now - self.cursor_blink_timer > 500:
            self.cursor_blink_state = not self.cursor_blink_state
            self.cursor_blink_timer = now
        
        if self.state == "IDLE":
            if self.queue:
                self.start_anim()
        
        elif self.state == "ANIM_DOTS":
            elapsed = now - self.timer
            if elapsed >= self.anim_duration:
                self.state = "TYPING"
                if self.queue:
                    self.current_full_msg = self.queue.pop(0)
                    self.live_text = ""
                    self.typing_idx = 0
                    self.timer = now
                else:
                    self.state = "IDLE"
            else:
                step = int(elapsed / 300) % 3
                if step == 0: self.live_text = "..."
                elif step == 1: self.live_text = ".."
                elif step == 2: self.live_text = "."

        elif self.state == "TYPING":
            if now - self.timer > 40:
                self.timer = now
                if self.typing_idx < len(self.current_full_msg):
                    self.live_text += self.current_full_msg[self.typing_idx]
                    self.typing_idx += 1
                    
                    full_line = "> " + self.live_text
                    if self.start_x + self.font.size(full_line)[0] > self.max_x:
                        split_idx = self.live_text.rfind(" ")
                        if split_idx != -1:
                            part1 = self.live_text[:split_idx]
                            part2 = self.live_text[split_idx+1:]
                            self.add_to_history(part1)
                            self.live_text = part2
                            self.state = "TYPING" 
                            self.timer = now
                        else:
                            self.add_to_history(self.live_text)
                            self.live_text = ""
                            self.state = "TYPING"
                            self.timer = now
                else:
                    self.add_to_history(self.live_text)
                    # Callback for message completion
                    if self.on_message_complete:
                        self.on_message_complete(self.current_full_msg)
                    self.state = "WAIT_NEXT"
                    self.timer = now

        elif self.state == "WAIT_NEXT":
            elapsed = now - self.timer
            if elapsed > self.msg_pause:
                self.live_text = ""
                if self.queue:
                    self.state = "TYPING"
                    self.current_full_msg = self.queue.pop(0)
                    self.typing_idx = 0
                    self.timer = now
                else:
                    self.state = "IDLE"
            else:
                step = int(elapsed / 300) % 3
                if step == 0: self.live_text = "..."
                elif step == 1: self.live_text = ".."
                elif step == 2: self.live_text = "."

    def add_to_history(self, text):
        self.history.append(text)
        if len(self.history) > 50:
            self.history.pop(0)
        self.scroll_offset = 0

    def scroll(self, direction):
        if not self.history:
            return
            
        max_visible_lines = 7
        total_lines = len(self.history)
        max_offset = max(0, total_lines - max_visible_lines)
        
        self.scroll_offset += direction
        
        if self.scroll_offset < 0:
            self.scroll_offset = 0
        elif self.scroll_offset > max_offset:
            self.scroll_offset = max_offset

    def draw(self, surface, offset_x=0, offset_y=0):
        # Apply window offset to drawing positions
        header_x, header_y = self.header_pos
        surface.blit(self.font.render("<MESSAGE LOG...>", True, HEADER_PURPLE), (header_x + offset_x, header_y + offset_y))
        
        prompt_surf = self.font.render("> ", True, OPERATOR_GREEN)
        prompt_w = prompt_surf.get_width()

        y = self.live_y - 15
        
        base_r, base_g, base_b = HISTORY_PURPLE
        
        visible_count = 7
        if not self.history:
            visible_slice = []
        else:
            end_idx = len(self.history) - self.scroll_offset
            start_idx = max(0, end_idx - visible_count)
            visible_slice = self.history[start_idx:end_idx]
            
        for i, msg in enumerate(reversed(visible_slice)):
            factor = 1.0 - (i * 0.1)
            if factor < 0.2: factor = 0.2
            
            curr_color = (
                int(base_r * factor),
                int(base_g * factor),
                int(base_b * factor)
            )
            
            prompt_color = curr_color
            prompt_surf_faded = self.font.render("> ", True, prompt_color)
            
            surface.blit(prompt_surf_faded, (self.start_x + offset_x, y + offset_y))
            surface.blit(self.font.render(msg, True, curr_color), (self.start_x + prompt_w + offset_x, y + offset_y))
            y -= 15
            
        surface.blit(prompt_surf, (self.start_x + offset_x, self.live_y + offset_y))
        
        if self.live_text:
            surface.blit(self.font.render(self.live_text, True, LIVE_MSG_PINK), (self.start_x + prompt_w + offset_x, self.live_y + offset_y))


class PirateRadioApp:
    def __init__(self, screen: pygame.Surface, res_manager: ResolutionManager, desktop_x: int, desktop_y: int):
        self.screen = screen
        self.res_manager = res_manager
        self.scale = res_manager.scale_factor
        
        # Window dimensions
        self.width = self.res_manager.scale(820)
        self.height = self.res_manager.scale(547)
        
        # Initial position (relative to desktop)
        self.x = desktop_x + int(50 * self.scale)
        self.y = desktop_y + int(50 * self.scale)
        
        self.active = False
        self.minimized = False
        
        # External intro sound reference (set by main.py for immediate playback)
        self.external_intro_sound = None
        
        # Callbacks for main.py integration
        self.on_token_award: Optional[Callable[[str], None]] = None
        self.get_username: Optional[Callable[[], str]] = None
        self.on_station_tune: Optional[Callable[[Dict], None]] = None
        self.on_station_stop: Optional[Callable[[], None]] = None
        
        # Initialize station sounds dict before loading resources (needed by _load_station_sounds)
        self.station_sounds: Dict[str, pygame.mixer.Sound] = {}

        # Noise/tuner state (must exist before loading resources)
        self.noise_base_volume = NOISE_BASE_VOLUME
        self.noise_channel: Optional[pygame.mixer.Channel] = None
        self.tuner_reduction_levels = [0.10, 0.15, 0.30]  # 10%, 15%, 30%
        self.tuner_index = 0
        
        # Load resources
        self._load_resources()
        
        # State
        self.game_state = "INTRO" # INTRO -> PLAY_PATTERN -> AWAIT_INPUT -> CHECK -> DONE -> RADIO_STATIONS
        self.current_bg_frame = 0
        self.bg_frame_timer = 0
        self.intro_wait_start = 0
        self.intro_messages_added = False
        self.app_started = False
        
        self.grid_scroll_x = 0
        self.transmission_power = 40
        self.hack_status_dot_state = 0
        self.hack_status_dot_timer = 0
        # Equalizer state
        self.eq_bars: List[Dict] = []
        self.eq_last_spawn = 0
        self.eq_speed_px = max(1, int(1 * self.scale))  # track movement vs grid
        self.eq_current_level = 0.0
        self.transmission_power_timer = 0
        self.transmission_power_interval = 140  # ms jitter cadence for live streams
        
        # Access flags
        self.skip_challenge = False  # when True, bypass tone patterns (RADIO_ACCESS1)
        self.force_intro_with_skip = False  # when True, still show intro/video even if skipping patterns
        self.skip_challenge_active = False
        self.skip_challenge_unlock_done = False
        self.skip_intro_messages = False
        self.current_station = None
        
        # Pattern logic
        self.tone_names = ["low", "mid", "high", "whistle"]
        self.patterns = []
        for length in PATTERN_LENGTHS:
            pattern = []
            for i in range(length):
                while True:
                    new_tone = random.choice(self.tone_names)
                    if new_tone == "whistle" and pattern and pattern[-1] == "whistle":
                        continue
                    pattern.append(new_tone)
                    break
            self.patterns.append(pattern)
            
        self.current_pattern_index = 0
        self.current_pattern = self.patterns[self.current_pattern_index]
        self.player_input = []
        self.replay_chances = 3
        self.current_button_index = 0
        
        self.button_labels = ["LOW", "MID", "HIGH", "WHISTLE"]
        
        # Playback state
        self.playback_index = 0
        self.playback_timer = 0
        self.playback_channel = None
        self.PLAYBACK_INTERVAL = 2000
        self.PLAYBACK_PAUSE_BEFORE = 1000
        
        # Areas (unscaled coordinates from original, will be scaled in draw)
        self.orig_button_area = pygame.Rect(30, 300, 390, 180)
        self.orig_grid_area = pygame.Rect(31, 51, 385, 189)
        
        # Initialize chat
        # Original coords: max_x=765, start_x=435, live_y=459, header=(435, 337)
        self.chat = ChatSystem(
            self.font_hack_status,
            max_x=int(765 * self.scale),
            start_x=int(435 * self.scale),
            live_y=int(459 * self.scale),
            header_pos=(int(435 * self.scale), int(337 * self.scale))
        )
        # Set up message completion callback
        self.chat.on_message_complete = self._on_message_complete
        
        # Sound state
        self.noise_started = False
        
        # Video state
        self.video_cap = None
        self.video_playing = False
        self.video_frame = None
        self.intro_delay = 3000
        
        # Radio stations state
        self.radio_manager = RadioStationManager()
        # Initialize all possible stations immediately so they start "ticking" right away
        # This provides the "live" feeling as soon as the BBS is launched.
        self.radio_manager.initialize_minutes(NIGHT_STATIONS + DAY_STATIONS)
        
        self.current_stations: List[Dict] = []
        self.selected_station_index = 0
        # self.station_sounds is initialized earlier before _load_resources()
        self.radio_ui_active = False  # True when showing station list instead of tone buttons
        self.final_message_delivered = False
        self.uncle_am_message_queued = False
        self.token_awarded = False
        self.tokyo_yamoto_first_play = False  # Track if Tokyo Yamoto has been played for first time this session
        self.echo_chamber_first_play = False  # Track if Echo Chamber has been played for first time this session
        self.current_station_tuned = False  # Track if user has tuned the current station to clear signal
        self.station_tuner_presses = 0  # Count right arrow presses for station tuning
        
    def _load_resources(self):
        # Fonts
        self.font_small = pygame.font.Font(get_data_path("PressStart2P-Regular.ttf"), int(12 * self.scale))
        self.font_sniffer = pygame.font.Font(get_data_path("PressStart2P-Regular.ttf"), int(11 * self.scale))
        self.font_power = pygame.font.Font(get_data_path("PressStart2P-Regular.ttf"), int(14 * self.scale))
        self.font_sys = pygame.font.Font(get_data_path("PressStart2P-Regular.ttf"), int(9 * self.scale))
        self.font_med = pygame.font.Font(get_data_path("PressStart2P-Regular.ttf"), int(16 * self.scale))
        self.font_large = pygame.font.Font(get_data_path("PressStart2P-Regular.ttf"), int(20 * self.scale))
        self.font_hack_status = pygame.font.Font(get_data_path("PressStart2P-Regular.ttf"), int(10 * self.scale))
        self.font_pattern_status = pygame.font.Font(get_data_path("PressStart2P-Regular.ttf"), int(18 * self.scale))
        self.font_whistle = pygame.font.Font(get_data_path("PressStart2P-Regular.ttf"), int(10 * self.scale))
        self.font_station = pygame.font.Font(get_data_path("PressStart2P-Regular.ttf"), int(11 * self.scale))
        self.font_radio_help = pygame.font.Font(get_data_path("PressStart2P-Regular.ttf"), int(10 * self.scale))  # 2pt smaller than font_small
        
        # Images
        self.bg_frames = []
        for frame_path in BACKGROUND_FRAMES:
            img = pygame.image.load(get_data_path(frame_path)).convert()
            img = pygame.transform.scale(img, (self.width, self.height))
            self.bg_frames.append(img)
            
        try:
            self.overlay = pygame.image.load(get_data_path(OVERLAY_IMAGE)).convert_alpha()
            self.overlay = pygame.transform.scale(self.overlay, (self.width, self.height))
        except:
            self.overlay = None
            
        self.splash_image = pygame.image.load(get_data_path(SPLASH_IMAGE)).convert()
        self.splash_image = pygame.transform.scale(self.splash_image, (self.width, self.height))
            
        # Sounds
        self.noise_sound = pygame.mixer.Sound(get_data_path(NOISE_FILE))
        self.noise_sound.set_volume(self.noise_base_volume)
        
        self.tone_sounds = {name: pygame.mixer.Sound(get_data_path(path)) for name, path in TONE_FILES.items()}
        # Set volume to 80% for all tone sounds
        for tone_sound in self.tone_sounds.values():
            tone_sound.set_volume(0.8)
        
        self.intro_audio = pygame.mixer.Sound(get_data_path(INTRO_AUDIO))
        self.intro_audio.set_volume(0.8)  # Set volume to 80%
        
        # Try to load radio station sounds
        self._load_station_sounds()

    def _load_station_sounds(self):
        """Load radio station audio files (both detuned and tuned versions) if they exist."""
        all_stations = NIGHT_STATIONS + DAY_STATIONS
        for station in all_stations:
            station_name = station["name"]
            
            # Load detuned version
            detuned_path = self._station_path(station["file"])
            detuned_sound = None
            if os.path.exists(detuned_path):
                try:
                    detuned_sound = pygame.mixer.Sound(detuned_path)
                    # Don't set volume on the Sound object - we'll control it via Channel
                except Exception as e:
                    print(f"Warning: Could not load detuned {station['file']}: {e}")
            else:
                # Try alternative file names (case-insensitive, without -DeTuned suffix)
                base_name = station["file"].replace("-DeTuned.wav", ".wav").replace("-Tuned.wav", ".wav")
                alt_path = self._station_path(base_name)
                if os.path.exists(alt_path):
                    try:
                        detuned_sound = pygame.mixer.Sound(alt_path)
                        print(f"Loaded {station_name} detuned from alternative path: {base_name}")
                    except Exception as e:
                        print(f"Warning: Could not load detuned {base_name}: {e}")
                else:
                    print(f"Warning: Detuned file not found: {detuned_path} or {alt_path}")
            
            # Load tuned version
            tuned_sound = None
            tuned_file = station.get("tuned_file")
            if tuned_file:
                tuned_path = self._station_path(tuned_file)
                if os.path.exists(tuned_path):
                    try:
                        tuned_sound = pygame.mixer.Sound(tuned_path)
                        # Don't set volume on the Sound object - we'll control it via Channel
                    except Exception as e:
                        print(f"Warning: Could not load tuned {tuned_file}: {e}")
                else:
                    # Try alternative file names (case-insensitive)
                    base_name = tuned_file.replace("-Tuned.wav", ".wav")
                    alt_path = self._station_path(base_name)
                    if os.path.exists(alt_path):
                        try:
                            tuned_sound = pygame.mixer.Sound(alt_path)
                            print(f"Loaded {station_name} tuned from alternative path: {base_name}")
                        except Exception as e:
                            print(f"Warning: Could not load tuned {base_name}: {e}")
                    else:
                        print(f"Warning: Tuned file not found: {tuned_path} or {alt_path}")
            
            # Store both sounds (for backward compatibility, also store detuned as main)
            if detuned_sound:
                self.station_sounds[station_name] = detuned_sound
                # Also store tuned version with a key suffix for easy access
                if tuned_sound:
                    self.station_sounds[f"{station_name}_tuned"] = tuned_sound

    def _on_message_complete(self, message: str):
        """Callback when a chat message finishes displaying."""
        # Check if this was the final message that triggers radio UI
        if "you did great, thank you!" in message:
            self.final_message_delivered = True
            self._activate_radio_ui()

    def _activate_radio_ui(self):
        """Switch to the radio station selection UI and initialize all stations for simultaneous playback."""
        self.radio_ui_active = True
        self.game_state = "RADIO_STATIONS"
        
        # Determine day/night stations
        if _is_nighttime():
            self.current_stations = NIGHT_STATIONS
        else:
            self.current_stations = DAY_STATIONS
            
        # Radio manager is already initialized in __init__ with all stations
        
        # Ensure we have enough mixer channels for all stations (5 stations × 2 versions = 10 channels minimum)
        # Plus some extra for noise, tones, etc. - request 16 channels
        try:
            current_channels = pygame.mixer.get_num_channels()
            if current_channels < 16:
                pygame.mixer.set_num_channels(16)
                print(f"Increased mixer channels to 16 (was {current_channels})")
        except Exception as e:
            print(f"Warning: Could not increase mixer channels: {e}")
        
        # Initialize all stations for simultaneous playback (all at 0% volume initially)
        initialized_count = 0
        for station in self.current_stations:
            station_name = station["name"]
            detuned_sound = self.station_sounds.get(station_name)
            tuned_sound = self.station_sounds.get(f"{station_name}_tuned")
            
            if detuned_sound:
                print(f"Initializing station: {station_name} (detuned: {detuned_sound is not None}, tuned: {tuned_sound is not None})")
                # Initialize playback for this station
                success = self.radio_manager.initialize_station_playback(
                    station, 
                    detuned_sound, 
                    tuned_sound,
                    self._station_path
                )
                if success:
                    initialized_count += 1
                    print(f"Successfully initialized {station_name}")
                else:
                    print(f"Warning: Failed to initialize playback for {station_name}")
            else:
                print(f"Warning: No detuned sound loaded for {station_name}")
        
        print(f"Initialized {initialized_count}/{len(self.current_stations)} stations")
        
        self.selected_station_index = 0
        
        # Queue chat guidance: concise status if already unlocked, otherwise story message
        if not self.uncle_am_message_queued:
            self.uncle_am_message_queued = True
            if self.skip_challenge_active or self.skip_challenge:
                # Clear prior challenge narrative when returning with the token
                self.chat.queue.clear()
                self.chat.history.clear()
                self.chat.queue_message("Stations live. UP/DOWN to browse, ENTER to tune, SPACE to stop.")
                self.chat.queue_message("LEFT/RIGHT to fine tune signal. ESC to leave; audio stays live while connected.")
            else:
                self.chat.queue_message(
                    "Here are the stations we have on the network as of now, it changes throughout the day, "
                    "just select the one you want and it'll link to your BBS account, provided you stay connected "
                    "the audio stream will continue, you want to change the station just come back here to do that "
                    "via the Pirate Radio menu option on the BBS home screen! Really pleased we got this working, Uncle-AM :)"
                )

    def start(self):
        self.active = True
        self.minimized = False
        self.current_station = None
        self.skip_challenge_active = self.skip_challenge
        self.skip_challenge_unlock_done = False
        # tokyo_yamoto_first_play is persistent throughout the app instance session
        self.skip_intro_messages = self.skip_challenge_active

        # If skipping challenge without intro, keep previous fast-path behavior
        if self.skip_challenge and not self.force_intro_with_skip:
            # Stop any intro audio that might be playing
            try:
                if self.external_intro_sound:
                    self.external_intro_sound.stop()
                self.intro_audio.stop()
            except Exception:
                pass
            self.video_playing = False
            self.app_started = True
            self.intro_messages_added = True
            self.final_message_delivered = True
            self.token_awarded = True  # Don't award again
            self.radio_ui_active = True
            self.game_state = "RADIO_STATIONS"
            self.start_noise()
            self._activate_radio_ui()
            return

        self.video_playing = True
        self.app_started = False
        self.intro_messages_added = False
        
        # NOTE: Intro audio (TSW.wav) is played by main.py immediately on Enter press
        # to avoid any delay from video initialization
        
        # Open video (this can take time to initialize)
        if _cv2_available:
            self.video_cap = cv2.VideoCapture(get_data_path(INTRO_VIDEO))
            if not self.video_cap.isOpened():
                print("Warning: Could not open intro video")
                self.video_playing = False
        else:
            self.video_playing = False

    def close(self):
        self.active = False
        self.stop_audio()
        self.intro_audio.stop()
        # Don't stop external_intro_sound - let TSW.wav play to completion
        if self.video_cap:
            self.video_cap.release()
            self.video_cap = None
        self.noise_started = False
        
    def start_noise(self):
        if not self.noise_started:
            self.noise_channel = self.noise_sound.play(-1)
            self.noise_started = True
        self._apply_noise_volume()

    def stop_audio(self):
        """Stop station + noise playback and notify host app."""
        self.radio_manager.stop_current()
        self._notify_station_stop()

    def queue_intro_messages(self):
        if self.intro_messages_added:
            return
        self.intro_messages_added = True

        msgs = [
            "Ah, you figured out you needed to press space on that intro. I hope you didn't spit on the screen... I usually do!",
            "Glyphis managed to jack this tool prior to unloading a worm into the CIA's main network software distribution library.",
            "We can now access the underground radio network using the exact tool that was created to sniff our people out!",
            "Your LAPC-1 soundcard is fully streaming now so you should be hearing noise from both your speakers.",
            "Your BRADSONIC will act as a conduit for the rest of the network to link up, you'll be able to enjoy what the underground pirate broadcasters have to offer, even when you're not in this tool!",
            "Right sorry. This message area is slow! It wasn't built for chatter. First we have to TONE PATCH YOUR system in, your going to hear a series of tones.",
            "When you're ready just press the space bar and the tones will come!"
        ]
        for m in msgs:
            self.chat.queue_message(m)

    def start_pattern_playback(self):
        self.game_state = "PLAY_PATTERN"
        self.playback_index = -1
        self.playback_timer = pygame.time.get_ticks()
        self.playback_channel = None

    def update_pattern_playback(self):
        now = pygame.time.get_ticks()

        if self.playback_index == -1:
            if now - self.playback_timer >= self.PLAYBACK_PAUSE_BEFORE:
                self.playback_index = 0
                self.playback_timer = now
        elif self.playback_index < len(self.current_pattern):
            if self.playback_channel and self.playback_channel.get_busy():
                return

            if now - self.playback_timer >= self.PLAYBACK_INTERVAL:
                tone_name = self.current_pattern[self.playback_index]
                self.playback_channel = self.tone_sounds[tone_name].play()
                self._push_eq_level_for_tone(tone_name)
                self.transmission_power = min(99, self.transmission_power + 20)
                self.playback_index += 1
                self.playback_timer = now
        else:
            if self.playback_channel and self.playback_channel.get_busy():
                return
            self.game_state = "AWAIT_INPUT"

    def handle_event(self, event):
        if not self.active:
            return False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                # Minimize UI but keep audio streaming
                self.minimized = True
                self.active = False
                return True

            if self.video_playing:
                if event.key == pygame.K_SPACE:
                    self.video_playing = False
                    self.intro_audio.stop()
                    # Don't stop external_intro_sound - let TSW.wav play to completion
                    return True
                return True

            if not self.app_started:
                if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                    self.app_started = True
                    self.start_noise()
                    if not self.skip_intro_messages:
                        self.queue_intro_messages()
                    return True
                return True # Swallow events on splash

            # Chat scrolling (always available)
            if event.key == pygame.K_UP and not self.radio_ui_active:
                self.chat.scroll(1)
            elif event.key == pygame.K_DOWN and not self.radio_ui_active:
                self.chat.scroll(-1)

            # Radio station selection mode
            if self.game_state == "RADIO_STATIONS" and self.radio_ui_active:
                if event.key == pygame.K_UP:
                    self.selected_station_index = (self.selected_station_index - 1) % len(self.current_stations)
                elif event.key == pygame.K_DOWN:
                    self.selected_station_index = (self.selected_station_index + 1) % len(self.current_stations)
                elif event.key == pygame.K_LEFT:
                    self._adjust_tuner(-1)
                elif event.key == pygame.K_RIGHT:
                    self._adjust_tuner(1)
                elif event.key == pygame.K_RETURN:
                    self._play_selected_station()
                elif event.key == pygame.K_SPACE:
                    # Stop current playback
                    self.radio_manager.stop_current()
                    self._notify_station_stop()
                    self.chat.queue_message("Radio stream paused.")
                return True

            if self.game_state == "AWAIT_INPUT":
                if event.key == pygame.K_LEFT:
                    self.current_button_index = (self.current_button_index - 1) % len(self.button_labels)
                elif event.key == pygame.K_RIGHT:
                    self.current_button_index = (self.current_button_index + 1) % len(self.button_labels)
                
                elif event.key == pygame.K_SPACE:
                    if self.replay_chances > 0:
                        self.replay_chances -= 1
                        self.chat.queue_message(f"Replaying pattern. {self.replay_chances} replay chances remaining.")
                        self.start_pattern_playback()
                    else:
                        self.chat.queue_message("No replay chances remaining.")

                elif event.key == pygame.K_RETURN:
                    chosen_label = self.button_labels[self.current_button_index]
                    label_to_tone = {
                        "LOW": "low", "MID": "mid", "HIGH": "high", "WHISTLE": "whistle"
                    }
                    tone_name = label_to_tone[chosen_label]
                    self.player_input.append(tone_name)
                    self.tone_sounds[tone_name].play()
                    self._push_eq_level_for_tone(tone_name)
                    self.transmission_power = min(99, self.transmission_power + 15)

                    if len(self.player_input) == len(self.current_pattern):
                        self.game_state = "CHECK"
            
            if self.game_state == "INTRO" and self.current_pattern_index == 0:
                if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                    self.start_pattern_playback()
                    
            return True
        return False

    def _play_selected_station(self):
        """Select and play the currently selected radio station."""
        if not self.current_stations:
            return
            
        station = self.current_stations[self.selected_station_index]
        station_name = station["name"]
        
        # Check if station is initialized
        if station_name not in self.radio_manager.station_channels:
            self.chat.queue_message(f"Station '{station_name}' not initialized.")
            return
        
        # Reset tuning state when switching to any station
        self.current_station_tuned = False
        self.station_tuner_presses = 0
        
        # Special handling for Tokyo Yamoto Forever (09:04 first-time start rule)
        if station_name == "Tokyo Yamoto Forever" and not self.tokyo_yamoto_first_play:
            # Force first play to start at 09:04
            override_start = 544.0
            self.tokyo_yamoto_first_play = True
            
            # Synchronize the radio manager's tracked time to this forced start position 
            # so it "becomes live" from this point forward.
            self.radio_manager.station_seconds[station_name] = 544.0
            
            # Award token ONLY on first play
            if self.on_token_award:
                try:
                    self.on_token_award("PAPERCRANEBBS")
                except Exception:
                    pass
        
        # Award ECHOCHAMBER token on first play of Echo Chamber station
        if station_name == "Echo Chamber" and not self.echo_chamber_first_play:
            self.echo_chamber_first_play = True
            if self.on_token_award:
                try:
                    self.on_token_award("ECHOCHAMBER")
                except Exception:
                    pass
        
        # Select the station (this sets volumes appropriately)
        self.radio_manager.select_station(station_name)
        self.start_noise()
        self.current_station = station
        
        # Debug: Verify channel is actually playing
        if station_name in self.radio_manager.station_channels:
            channels = self.radio_manager.station_channels[station_name]
            if channels["detuned_channel"]:
                is_busy = channels["detuned_channel"].get_busy()
                print(f"Debug: {station_name} detuned channel busy: {is_busy}, volume: {channels['detuned_volume']}")
            else:
                print(f"Debug: {station_name} detuned channel is None!")
        
        # Give EQ a boost when tuning
        self.eq_current_level = max(self.eq_current_level, 0.7)
        
        # Get formatted time for display
        minutes, seconds = self.radio_manager.get_station_time_formatted(station_name)
        freq = station.get("freq")
        freq_suffix = f" ({freq} kHz)" if freq else ""
        self.chat.queue_message(f"Now tuned to: {station_name}{freq_suffix} ({minutes:02d}:{seconds:02d})")
        if self.on_station_tune:
            try:
                self.on_station_tune(station)
            except Exception:
                pass

    def update(self):
        # Always update radio manager even if UI is minimized (audio may still be playing)
        # This ensures minutes continue ticking while in BBS
        if self.radio_manager.initialized:
            self.radio_manager.tick()
        
        if not self.active:
            return

        now = pygame.time.get_ticks()

        # Update video
        if self.video_playing and _cv2_available:
            ret, frame = self.video_cap.read()
            if ret:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame_surface = pygame.surfarray.make_surface(frame_rgb.swapaxes(0, 1))
                self.video_frame = pygame.transform.scale(frame_surface, (self.width, self.height))
            else:
                self.video_playing = False
                self.intro_audio.stop()
                # Don't stop external_intro_sound - let TSW.wav play to completion
            return # Don't update game logic while video plays

        if not self.app_started:
            return

        # Background animation
        if now - self.bg_frame_timer >= BACKGROUND_FRAME_DURATION:
            self.current_bg_frame = (self.current_bg_frame + 1) % len(self.bg_frames)
            self.bg_frame_timer = now

        # Logic
        self.chat.update()

        # Hack status
        if now - self.hack_status_dot_timer >= 500:
            self.hack_status_dot_state = (self.hack_status_dot_state + 1) % 4
            self.hack_status_dot_timer = now

        # Transmission power decay
        if self.radio_manager.is_playing():
            # Animate transmission power between 88-98% while streaming
            if now - self.transmission_power_timer >= self.transmission_power_interval:
                self.transmission_power = random.randint(88, 98)
                self.transmission_power_timer = now
        else:
            if self.transmission_power > 40:
                self.transmission_power = max(40, self.transmission_power - 0.1)

        # State machine
        if self.game_state == "INTRO":
            if self.current_pattern_index > 0:
                if now - self.intro_wait_start > self.intro_delay:
                    self.start_pattern_playback()

        elif self.game_state == "PLAY_PATTERN":
            self.update_pattern_playback()

        elif self.game_state == "WAIT_RETRY":
            if not self.chat.queue and self.chat.state == "IDLE":
                self.start_pattern_playback()

        elif self.game_state == "CHECK":
            if self.player_input == self.current_pattern:
                self.chat.queue_message(f"Pattern {self.current_pattern_index + 1} locked.")
                if self.current_pattern_index == 0:
                    self.chat.queue_message("Good. The signal is stabilizing.")
                
                self.current_pattern_index += 1
                if self.current_pattern_index >= len(self.patterns):
                    self.game_state = "DONE"
                    self._on_all_patterns_complete()
                else:
                    next_len = len(self.patterns[self.current_pattern_index])
                    self.chat.queue_message(f"Stand by for pattern {self.current_pattern_index + 1}. Expecting {next_len} tones.")
                    self.current_pattern = self.patterns[self.current_pattern_index]
                    self.player_input = []
                    self.current_button_index = 0
                    self.replay_chances = 3
                    self.intro_wait_start = now
                    self.game_state = "INTRO"
            else:
                self.chat.queue_message("Incorrect sequence detected. Signal lost.")
                self.chat.queue_message("Reseting frequency patch. Listen again.")
                self.player_input = []
                self.current_button_index = 0
                self.game_state = "WAIT_RETRY"

        # Auto-unlock path: user has token, we still showed intro/video, now skip patterns
        if (
            self.skip_challenge_active
            and self.force_intro_with_skip
            and self.app_started
            and not self.video_playing
            and not self.radio_ui_active
            and not self.skip_challenge_unlock_done
        ):
            self.skip_challenge_unlock_done = True
            self.final_message_delivered = True
            self.token_awarded = True
            self.game_state = "RADIO_STATIONS"
            self.radio_ui_active = True
            self.start_noise()
            self._activate_radio_ui()

        # Grid scroll
        self.grid_scroll_x = (self.grid_scroll_x + 1) % GRID_CELL_SIZE
        # Equalizer update
        audio_active, audio_level = self._compute_audio_level()
        self._update_equalizer(audio_active, audio_level)

    def _on_all_patterns_complete(self):
        """Called when all 3 patterns are successfully completed."""
        # Award token
        if not self.token_awarded and self.on_token_award:
            self.on_token_award("RADIO_ACCESS1")
            self.token_awarded = True
        
        # Queue completion messages
        self.chat.queue_message("All patterns secured. Relay access granted.")
        
        # Get username for personalized message
        username = "operator"
        if self.get_username:
            try:
                username = self.get_username() or "operator"
            except:
                pass
        
        # The final message that triggers radio UI activation
        self.chat.queue_message(
            f"Standby for transmission power breach, and squelch filter activation. "
            f"We now have airwaves {username}, you did great, thank you!"
        )

    def draw(self):
        if not self.active:
            return

        if self.video_playing and self.video_frame:
            self.screen.blit(self.video_frame, (self.x, self.y))
            return
        elif self.video_playing: # fallback if frame not ready
            return

        if not self.app_started:
            self.screen.blit(self.splash_image, (self.x, self.y))
            return

        # Main Draw
        self.screen.blit(self.bg_frames[self.current_bg_frame], (self.x, self.y))

        # Helpers for scaling relative to self.x/y
        # Note: Chat system uses internal relative coords + self.x/y offset passed to draw
        
        # 1. Hack Status (436, 106)
        sx, sy = self.x + int(436 * self.scale), self.y + int(106 * self.scale)
        status_text = "HACK STATUS: ACCESS GRANTED"
        status_img = self.font_hack_status.render(status_text, True, HACK_STATUS_COLOR)
        self.screen.blit(status_img, (sx, sy))
        
        sy += self.font_hack_status.get_height() + 4
        dots = "." * (self.hack_status_dot_state + 1) if self.hack_status_dot_state < 3 else "..."
        decoding_text = "DECODING PACKETS" + dots
        decoding_img = self.font_hack_status.render(decoding_text, True, HACK_STATUS_COLOR)
        self.screen.blit(decoding_img, (sx, sy))

        # 2. Sys Message (436, 144)
        sx, sy = self.x + int(436 * self.scale), self.y + int(144 * self.scale)
        lines = ["Connection sniff complete.", "Relay locked: AMERICAN PACIFICA", "VHF/AM"]
        self.screen.blit(self.font_sys.render("[SYSOP]", True, CYAN), (sx, sy))
        for i, line in enumerate(lines):
            self.screen.blit(self.font_sys.render(line, True, CYAN), (sx, sy + (i+1)*16))

        # 3. Chat
        # Pass offset to draw method
        self.chat.draw(self.screen, offset_x=self.x, offset_y=self.y)

        # 4. Radio Buttons OR Radio Stations
        if self.radio_ui_active:
            self._draw_radio_stations()
        else:
            self._draw_tone_buttons()

        # 5. Transmission Power (240, 492)
        px = self.x + int(240 * self.scale)
        py = self.y + int(492 * self.scale)
        sniffer_img = self.font_sniffer.render("PATTERN SNIFFER ACTIVE", True, GREEN)
        self.screen.blit(sniffer_img, (px, py))
        power_img = self.font_power.render(f"TRANSMISSION POWER: {int(self.transmission_power)}%", True, GREEN)
        self.screen.blit(power_img, (px, py + int(17 * self.scale)))

        # 6. Pattern Status (434, 55)
        if self.game_state == "RADIO_STATIONS":
            status_text = "STREAMING LIVE"
        elif self.game_state != "DONE":
            status_text = f"PATTERN {self.current_pattern_index + 1} OF {len(self.patterns)}"
        else:
            status_text = "SNIFFER ONLINE"
        self.screen.blit(self.font_pattern_status.render(status_text, True, GREEN), (self.x + int(434 * self.scale), self.y + int(55 * self.scale)))

        # 7. Scrolling Grid (31, 51, 385, 189)
        grid_rect = self._get_grid_rect()
        original_clip = self.screen.get_clip()
        self.screen.set_clip(grid_rect)
        
        scaled_cell_size = int(GRID_CELL_SIZE * self.scale)
        scaled_scroll_x = int(self.grid_scroll_x * self.scale)
        
        start_x = grid_rect.right - scaled_scroll_x
        gx = start_x
        while gx >= grid_rect.left - scaled_cell_size:
            pygame.draw.line(self.screen, MAGENTA, (gx, grid_rect.top), (gx, grid_rect.bottom), 1)
            gx -= scaled_cell_size
            
        gy = grid_rect.top
        while gy <= grid_rect.bottom:
            pygame.draw.line(self.screen, MAGENTA, (grid_rect.left, gy), (grid_rect.right, gy), 1)
            gy += scaled_cell_size
            
        # 7b. Equalizer bars (on top of grid)
        self._draw_equalizer(grid_rect)
        
        self.screen.set_clip(original_clip)

        # 8. Overlay
        if self.overlay:
            self.screen.blit(self.overlay, (self.x, self.y))

    def _get_grid_rect(self) -> pygame.Rect:
        """Return the scaled grid rect used for both grid and equalizer."""
        grid_x = self.x + int(31 * self.scale)
        grid_y = self.y + int(51 * self.scale)
        grid_w = int(385 * self.scale)
        grid_h = int(189 * self.scale)
        return pygame.Rect(grid_x, grid_y, grid_w, grid_h)

    def _compute_audio_level(self) -> Tuple[bool, float]:
        """
        Return (active, level) for the equalizer.
        Level decays over time; bumps come from tone playback and radio streams.
        """
        # Decay the current visual level slightly each frame
        self.eq_current_level = max(0.0, self.eq_current_level - 0.01)

        playing_station = self.radio_manager.is_playing()
        tone_playing = self.playback_channel is not None and self.playback_channel.get_busy()

        if playing_station:
            # Simulate rolling amplitude from the stream
            self.eq_current_level = max(self.eq_current_level, 0.6 + random.random() * 0.3)

        active = playing_station or tone_playing
        level = max(0.0, min(1.0, self.eq_current_level))
        return active, level

    def _push_eq_level_for_tone(self, tone_name: str):
        """Bump eq level based on which tone was played."""
        tone_levels = {
            "low": 0.45,
            "mid": 0.6,
            "high": 0.8,
            "whistle": 1.0,
        }
        self.eq_current_level = max(self.eq_current_level, tone_levels.get(tone_name, 0.5))

    def _station_path(self, filename: str) -> str:
        """Resolve station audio path inside Live_Stations (fallback to root if missing)."""
        primary = get_data_path(STATION_DIR, filename)
        if os.path.exists(primary):
            return primary
        return get_data_path(filename)

    def _update_equalizer(self, active: bool, level: float):
        """Spawn and move equalizer bars from right to left over the grid."""
        grid_rect = self._get_grid_rect()
        now = pygame.time.get_ticks()

        # Spawn new bar when audio is active
        if active and now - self.eq_last_spawn >= EQ_SPAWN_INTERVAL:
            eq_width = int(EQ_BAR_WIDTH * self.scale)
            max_height = grid_rect.height
            min_height = int(max_height * 0.18)
            target = min_height + int(level * (max_height - min_height))
            jitter = int(max_height * 0.1)
            height = max(min_height, min(max_height, target + random.randint(-jitter, jitter)))
            # Reduce height by 33% (multiply by 0.67)
            height = int(height * 0.67)
            intensity = max(0.0, min(1.0, level + random.uniform(-0.05, 0.05)))
            spawn_x = grid_rect.right + eq_width  # just outside, will scroll in
            self.eq_bars.append({
                "x": spawn_x,
                "h": height,
                "intensity": intensity
            })
            self.eq_last_spawn = now

        # Move bars left and drop them when past the grid
        eq_speed = self.eq_speed_px
        for bar in self.eq_bars:
            bar["x"] -= eq_speed

        # Remove bars fully off-screen
        left_bound = grid_rect.left - int(EQ_BAR_WIDTH * self.scale) * 2
        self.eq_bars = [b for b in self.eq_bars if b["x"] > left_bound]

    def _notify_station_stop(self):
        """Reset station-related state and notify main when audio stops."""
        self.current_station = None
        self.eq_current_level = 0.0
        if self.noise_started:
            try:
                self.noise_sound.stop()
            except Exception:
                pass
            self.noise_started = False
        self.noise_channel = None
        if self.on_station_stop:
            try:
                self.on_station_stop()
            except Exception:
                pass

    def _draw_equalizer(self, grid_rect: pygame.Rect):
        """Render equalizer bars clipped to the grid area."""
        if not self.eq_bars:
            return

        base_y = grid_rect.bottom
        eq_width = int(EQ_BAR_WIDTH * self.scale)

        def lerp_color(start, end, t):
            return (
                int(start[0] + (end[0] - start[0]) * t),
                int(start[1] + (end[1] - start[1]) * t),
                int(start[2] + (end[2] - start[2]) * t),
            )

        for bar in self.eq_bars:
            height = min(bar["h"], grid_rect.height)
            color = lerp_color(EQ_COLOR_START, EQ_COLOR_END, max(0.0, min(1.0, bar["intensity"])))
            rect = pygame.Rect(
                int(bar["x"]),
                int(base_y - height),
                eq_width,
                int(height)
            )
            # Only draw the portion that overlaps the grid
            clipped_rect = rect.clip(grid_rect)
            if clipped_rect.height > 0 and clipped_rect.width > 0:
                # Create a temporary surface with alpha for transparency
                temp_surface = pygame.Surface((clipped_rect.width, clipped_rect.height), pygame.SRCALPHA)
                # Add alpha to color
                color_with_alpha = (*color, EQ_BAR_ALPHA)
                pygame.draw.rect(temp_surface, color_with_alpha, temp_surface.get_rect())
                # Blit with alpha blending
                self.screen.blit(temp_surface, clipped_rect.topleft)

    def _draw_tone_buttons(self):
        """Draw the original tone patch bay UI."""
        btn_y = self.y + int(313 * self.scale)
        btn_x = self.x + int(43 * self.scale)
        
        btn_w = int(82 * self.scale)
        btn_h = int(40 * self.scale)
        padding = int(12 * self.scale)
        
        # Draw title (117, 267)
        title = self.font_med.render("TONE PATCH BAY", True, YELLOW)
        self.screen.blit(title, (self.x + int(117 * self.scale), self.y + int(267 * self.scale)))

        for i, label in enumerate(self.button_labels):
            rect = pygame.Rect(btn_x, btn_y, btn_w, btn_h)
            
            border_colour = MAGENTA
            if i == self.current_button_index:
                border_colour = YELLOW
                pygame.draw.rect(self.screen, (0, 40, 60), rect)
            
            pygame.draw.rect(self.screen, border_colour, rect, 2)
            
            colour = CYAN
            if label == "WHISTLE":
                text_img = self.font_whistle.render(label, True, colour)
            else:
                text_img = self.font_small.render(label, True, colour)
                
            self.screen.blit(
                text_img,
                (rect.centerx - text_img.get_width() // 2, rect.centery - text_img.get_height() // 2)
            )
            btn_x += btn_w + padding
            
        # Help text
        base_y = self.y + int((300 + 180 - 20) * self.scale)
        help_x = self.x + int((30 + 10) * self.scale)
        line_height = int(20 * self.scale)
        self.screen.blit(self.font_small.render("LEFT / RIGHT: select button", True, WHITE), (help_x, base_y - (line_height * 3)))
        self.screen.blit(self.font_small.render("ENTER: patch tone", True, WHITE), (help_x, base_y - (line_height * 2)))
        self.screen.blit(self.font_small.render("SPACE: Replay tone (3 chances)", True, WHITE), (help_x, base_y - line_height))
        self.screen.blit(self.font_small.render("UP / DOWN: Browse msg logs", True, WHITE), (help_x, base_y))

    def _draw_radio_stations(self):
        """Draw the radio station selection UI."""
        # Title - PIRATE RADIO CHANNELS in cyan
        title = self.font_med.render("PIRATE RADIO CHANNELS", True, CYAN)
        self.screen.blit(title, (self.x + int(65 * self.scale), self.y + int(267 * self.scale)))
        
        # Station list starting at (265, 569) relative - but we need to fit in button area
        # Let's use coordinates that fit within the button area
        list_x = self.x + int(43 * self.scale)
        list_y = self.y + int(300 * self.scale)
        
        # Find longest station name for highlight width
        max_width = 0
        for station in self.current_stations:
            text_width = self.font_station.size(f"X. {station['name']}")[0]
            if text_width > max_width:
                max_width = text_width
        
        highlight_width = max_width + int(20 * self.scale)
        highlight_height = int(22 * self.scale)
        
        for i, station in enumerate(self.current_stations):
            station_y = list_y + (i * int(26 * self.scale))
            
            # Draw highlight for selected station
            if i == self.selected_station_index:
                highlight_rect = pygame.Rect(list_x - int(5 * self.scale), station_y - int(2 * self.scale), highlight_width, highlight_height)
                pygame.draw.rect(self.screen, DARK_CYAN, highlight_rect)
                pygame.draw.rect(self.screen, CYAN, highlight_rect, 1)
            
            # Station number and name
            station_text = f"{i + 1}. {station['name']}"
            
            # Color based on selection and if currently playing
            if self.radio_manager.current_playing_station == station["name"]:
                color = GREEN  # Currently playing
            elif i == self.selected_station_index:
                color = WHITE  # Selected
            else:
                color = CYAN  # Normal
                
            station_surf = self.font_station.render(station_text, True, color)
            self.screen.blit(station_surf, (list_x, station_y))
        
        # Help text for radio mode - 3px below station 5 (last station)
        # Station 5 is at list_y + 4*26, plus station height (~22px), plus 3px gap
        last_station_y = list_y + (4 * 26) + 22 + 3
        help_x = self.x + 30 + 10
        help_line_spacing = 16  # Smaller spacing for smaller font
        self.screen.blit(self.font_radio_help.render("UP / DOWN: select station", True, WHITE), (help_x, last_station_y))
        self.screen.blit(self.font_radio_help.render("ENTER: tune to station", True, WHITE), (help_x, last_station_y + help_line_spacing))
        tune_label = "SPACE: stop playback   <-FINE TUNE+>"
        self.screen.blit(self.font_radio_help.render(tune_label, True, WHITE), (help_x, last_station_y + help_line_spacing * 2))

    def _apply_noise_volume(self):
        """Apply the current tuner setting to the looping noise channel."""
        reduction = self.tuner_reduction_levels[self.tuner_index]
        target_volume = self.noise_base_volume * (1.0 - reduction)
        try:
            self.noise_sound.set_volume(target_volume)
            if self.noise_channel:
                self.noise_channel.set_volume(target_volume)
        except Exception:
            # Keep audio running even if a channel update fails
            pass

    def _adjust_tuner(self, direction: int):
        """Fine tune the currently selected station: right increases tuned volume, left decreases it."""
        # Check if a station is selected and playing
        if not self.radio_manager.selected_station or not self.current_station:
            # If no station selected, adjust noise volume (legacy behavior)
            if not self.tuner_reduction_levels:
                return
            self.tuner_index = (self.tuner_index + direction) % len(self.tuner_reduction_levels)
            self._apply_noise_volume()
            self.chat.queue_message("Fine tuning noise")
            return
        
        # Fine tune the selected station
        if direction == 1:  # Right arrow - increase tuned, decrease detuned
            self.radio_manager.fine_tune_right()
            tune_level = self.radio_manager.tune_level
            if tune_level == 0:
                self.chat.queue_message("Signal: Detuned (80%)")
            elif tune_level == 1:
                self.chat.queue_message("Signal: Tuning... (50% detuned, 30% tuned)")
            elif tune_level == 2:
                self.chat.queue_message("Signal: Almost there... (20% detuned, 60% tuned)")
            elif tune_level == 3:
                self.chat.queue_message("Signal locked! Clear transmission (0% detuned, 80% tuned)")
        else:  # Left arrow - decrease tuned, increase detuned
            self.radio_manager.fine_tune_left()
            tune_level = self.radio_manager.tune_level
            if tune_level == 0:
                self.chat.queue_message("Signal: Detuned (80%)")
            elif tune_level == 1:
                self.chat.queue_message("Signal: Tuning... (50% detuned, 30% tuned)")
            elif tune_level == 2:
                self.chat.queue_message("Signal: Almost there... (20% detuned, 60% tuned)")
            else:
                self.chat.queue_message("Signal locked! Clear transmission (0% detuned, 80% tuned)")
    
