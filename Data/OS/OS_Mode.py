"""
OS Mode - Desktop Environment
A fictional desktop environment that launches the BBS.
Enhanced with visual polish, smooth interactions, and improved UX.
"""

import pygame
import os
import sys
import time
import math
import json
from typing import List, Dict, Tuple, Optional

# Visual Constants
COLOR_BG_DARK = (20, 20, 40)
COLOR_BG_TITLE = (40, 40, 60)
COLOR_CYAN = (0, 255, 255)
COLOR_GREEN = (0, 255, 0)
COLOR_RED = (255, 0, 0)
COLOR_RED_DARK = (100, 0, 0)
COLOR_WHITE = (255, 255, 255)
COLOR_BLACK = (0, 0, 0)
COLOR_BUTTON_HOVER = (60, 60, 80)
COLOR_BUTTON_ACTIVE = (80, 80, 100)

# Animation Constants
HOVER_ANIMATION_SPEED = 8.0  # pixels per second
ICON_LABEL_FADE_SPEED = 3.0  # alpha per second

# Try to import cv2 for video playback
try:
    import cv2
    import numpy as np
    _cv2_available = True
except ImportError:
    _cv2_available = False
    cv2 = None
    np = None

# Data path helper - works for both development and built executable
def get_data_path(*path_parts):
    """
    Returns the path to the Data folder, handling both development and built executable scenarios.
    """
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        base_path = sys._MEIPASS
    else:
        # Running as script - go up from OS to Data folder
        script_dir = os.path.dirname(os.path.abspath(__file__))
        data_folder = os.path.dirname(script_dir)  # Go up from OS to Data folder
        base_path = data_folder
    
    # Return path within Data folder
    return os.path.join(base_path, *path_parts)


class OSMode:
    """
    Desktop Environment OS Mode
    Renders a desktop environment with draggable icons.
    """
    
    def __init__(self, screen: pygame.Surface, scale: float, reset_bbs_callback=None):
        """
        Initialize OS Mode.
        
        Args:
            screen: The main screen surface to draw on
            scale: Scale factor for proportional scaling
            reset_bbs_callback: Optional callback function to reset BBS and exit OS mode
        """
        self.screen = screen
        self.scale = scale
        self.reset_bbs_callback = reset_bbs_callback
        
        # Baseline coordinates (at 2560x1440 resolution)
        self.baseline_desktop_x = 176
        self.baseline_desktop_y = 209
        
        # Scaled coordinates
        self.desktop_x = int(self.baseline_desktop_x * self.scale)
        self.desktop_y = int(self.baseline_desktop_y * self.scale)
        
        # Load desktop background
        desktop_path = get_data_path("OS", "Desktop-Enviroment.png")
        try:
            self.desktop_image = pygame.image.load(desktop_path).convert_alpha()
            # Scale desktop image
            original_size = self.desktop_image.get_size()
            self.desktop_size = (
                int(original_size[0] * self.scale),
                int(original_size[1] * self.scale)
            )
            self.desktop_image = pygame.transform.scale(self.desktop_image, self.desktop_size)
        except Exception as e:
            print(f"Warning: Failed to load Desktop-Enviroment.png: {e}")
            self.desktop_image = None
            self.desktop_size = (0, 0)
        
        # Desktop boundaries (for icon dragging)
        self.desktop_rect = pygame.Rect(
            self.desktop_x,
            self.desktop_y,
            self.desktop_size[0],
            self.desktop_size[1]
        )
        
        # Load icons (both normal and selected "S" versions)
        self.icons = []
        icon_files = [
            "tape-icon.png",
            "hard-drive-icon.png",
            "modem-iconpng.png",
            "games-folder.png",
            "notes-icon.png"
        ]
        
        icon_spacing = 0  # Will be calculated based on icon height
        current_y = self.desktop_y + int(70 * self.scale)  # Start 70px down from desktop top
        
        # Load saved icon positions if they exist
        saved_positions = self._load_icon_positions()
        
        for icon_file in icon_files:
            icon_path = get_data_path("OS", icon_file)
            # Get the "S" version filename (e.g., "tape-icon.png" -> "S-tape-icon.png")
            s_icon_file = "S-" + icon_file
            s_icon_path = get_data_path("OS", s_icon_file)
            
            try:
                # Load normal icon
                icon_image = pygame.image.load(icon_path).convert_alpha()
                # Scale icon
                original_icon_size = icon_image.get_size()
                icon_size = (
                    int(original_icon_size[0] * self.scale),
                    int(original_icon_size[1] * self.scale)
                )
                icon_image = pygame.transform.scale(icon_image, icon_size)
                
                # Load selected "S" version icon
                s_icon_image = None
                try:
                    s_icon_image = pygame.image.load(s_icon_path).convert_alpha()
                    s_icon_image = pygame.transform.scale(s_icon_image, icon_size)
                except Exception as e:
                    print(f"Warning: Failed to load {s_icon_file}: {e}")
                    # If S version doesn't exist, use normal icon as fallback
                    s_icon_image = icon_image
                
                # Position icon - use saved position if available, otherwise default stacked position
                if icon_file in saved_positions:
                    # Use saved position (already scaled)
                    icon_x = saved_positions[icon_file]["x"]
                    icon_y = saved_positions[icon_file]["y"]
                else:
                    # Default position: top-left corner, stacked vertically
                    icon_x = self.desktop_x + int(10 * self.scale)  # Small margin from left
                    icon_y = current_y
                
                icon_data = {
                    "image": icon_image,  # Normal version
                    "s_image": s_icon_image,  # Selected "S" version
                    "x": icon_x,
                    "y": icon_y,
                    "width": icon_size[0],
                    "height": icon_size[1],
                    "name": icon_file,
                    "selected": False,  # Track if this icon is selected
                    "dragging": False,
                    "drag_offset_x": 0,
                    "drag_offset_y": 0
                }
                self.icons.append(icon_data)
                
                # Move to next position (add spacing) - only if using default positions
                if icon_file not in saved_positions:
                    current_y += icon_size[1] + int(10 * self.scale)  # 10px spacing between icons
                
            except Exception as e:
                print(f"Warning: Failed to load {icon_file}: {e}")
        
        # Load custom mouse cursor
        cursor_path = get_data_path("OS", "mouse_cursor.png")
        try:
            cursor_image = pygame.image.load(cursor_path).convert_alpha()
            # Scale cursor
            original_cursor_size = cursor_image.get_size()
            cursor_size = (
                int(original_cursor_size[0] * self.scale),
                int(original_cursor_size[1] * self.scale)
            )
            cursor_image = pygame.transform.scale(cursor_image, cursor_size)
            # Create cursor with hotspot at top-left (0, 0)
            self.custom_cursor = pygame.cursors.Cursor((0, 0), cursor_image)
            self.cursor_image = cursor_image
        except Exception as e:
            print(f"Warning: Failed to load mouse_cursor.png: {e}")
            self.custom_cursor = None
            self.cursor_image = None
        
        # Load desktop scanline overlay
        scanline_path = get_data_path("OS", "Scanline-Desktop.png")
        try:
            self.desktop_scanline_image = pygame.image.load(scanline_path).convert_alpha()
            # Scale scanline to match desktop size
            self.desktop_scanline_image = pygame.transform.scale(
                self.desktop_scanline_image, 
                self.desktop_size
            )
        except Exception as e:
            print(f"Warning: Failed to load Scanline-Desktop.png: {e}")
            self.desktop_scanline_image = None
        
        # Mouse state
        self.mouse_pos = (0, 0)
        self.mouse_pressed = False
        self.hovered_icon = None  # Currently hovered icon
        self.hovered_button = None  # Currently hovered button (modal_name, button_type)
        self.icon_label_alpha = {}  # Alpha values for icon labels
        self.button_hover_offset = {}  # Hover animation offset for buttons
        
        # Overlay state
        self.overlay_active = False
        
        # Double-click detection
        self.last_click_time = 0.0
        self.last_click_pos = None
        self.double_click_threshold = 0.5  # seconds
        
        # Modal state - support multiple modals open at once
        self.active_modals = set()  # Set of active modal names: {"tape", "modem", etc.}
        self.modal_positions = {}  # Dict mapping modal name to (x, y) position
        self.modal_dragging = None  # Currently dragging modal name, or None
        self.modal_drag_offset = (0, 0)  # Offset from mouse to modal top-left when dragging
        self.modal_title_bar_height = int(30 * self.scale)  # Height of title bar for dragging
        self.tape_modal_terminal_text = ""
        self.tape_modal_terminal_lines = []  # List of terminal lines to display
        self.tape_modal_message_timer = 0.0  # Timer for delayed messages
        self.tape_modal_video_playing = False
        self.tape_modal_video_cap = None
        self.tape_modal_video_frame = None
        self.tape_modal_video_audio_channel = None
        self.tape_modal_video_original_size = None  # (width, height) of original video
        self.tape_modal_video_display_size = None  # (width, height) of displayed video (maintaining aspect ratio)
        self.tape_modal_video_fade_state = "none"  # "fade_in", "playing", "fade_out", "none"
        self.tape_modal_video_fade_alpha = 0.0  # 0.0 to 1.0
        self.tape_modal_video_fade_duration = 1.0  # seconds for fade in/out
        self.tape_modal_video_fade_timer = 0.0
        
        # Documentation viewer position (baseline 2560x1440)
        self.docs_viewer_baseline_x = 1547
        self.docs_viewer_baseline_y = 37
        
        # Datasette video position (baseline 2560x1440)
        self.datasette_baseline_x = 1363
        self.datasette_baseline_y = 44
        
        # Modem modal state
        self.modem_modal_dialed_sequence = ""  # Track dialed numbers
        self.modem_modal_target_sequence = "0345728891"  # Target sequence to dial
        self.modem_modal_connection_messages = []  # List of connection messages
        self.modem_modal_message_index = 0  # Current message index
        self.modem_modal_message_timer = 0.0  # Timer for message progression
        self.modem_modal_should_reset_bbs = False  # Flag to signal BBS reset
        self.modem_modal_should_exit_os = False  # Flag to signal OS mode exit
        self.modem_modal_connection_started = False  # Whether connection sequence has started
        
    def handle_event(self, event: pygame.event.Event) -> bool:
        """
        Handle pygame events for OS Mode.
        Returns True if event was handled, False otherwise.
        """
        if event.type == pygame.MOUSEMOTION:
            self.mouse_pos = event.pos
            
            # Update hover states for visual feedback
            self._update_hover_states(event.pos[0], event.pos[1])
            
            # Handle modal dragging
            if self.mouse_pressed and self.modal_dragging:
                # Calculate new position
                new_x = self.mouse_pos[0] - self.modal_drag_offset[0]
                new_y = self.mouse_pos[1] - self.modal_drag_offset[1]
                
                # Get modal size
                modal_w, modal_h = self._get_modal_size(self.modal_dragging)
                
                # Constrain to desktop boundaries
                new_x = max(self.desktop_rect.left, 
                           min(new_x, self.desktop_rect.right - modal_w))
                new_y = max(self.desktop_rect.top, 
                           min(new_y, self.desktop_rect.bottom - modal_h))
                
                self.modal_positions[self.modal_dragging] = (new_x, new_y)
                return True
            
            # Handle icon dragging
            if self.mouse_pressed:
                for icon in self.icons:
                    if icon["dragging"]:
                        # Calculate new position
                        new_x = self.mouse_pos[0] - icon["drag_offset_x"]
                        new_y = self.mouse_pos[1] - icon["drag_offset_y"]
                        
                        # Constrain to desktop boundaries
                        new_x = max(self.desktop_rect.left, 
                                   min(new_x, self.desktop_rect.right - icon["width"]))
                        new_y = max(self.desktop_rect.top, 
                                   min(new_y, self.desktop_rect.bottom - icon["height"]))
                        
                        icon["x"] = new_x
                        icon["y"] = new_y
                        return True
        
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left mouse button
                self.mouse_pressed = True
                mouse_x, mouse_y = event.pos
                current_time = time.time()
                
                # Check if clicking on a modal title bar for dragging (but exclude close buttons)
                # Check modals in reverse order (top-most first) to handle close buttons correctly
                for modal_name in reversed(list(self.active_modals)):
                    modal_x, modal_y = self.modal_positions.get(modal_name, (0, 0))
                    modal_w, modal_h = self._get_modal_size(modal_name)
                    if modal_w > 0 and modal_h > 0:
                        title_bar_rect = pygame.Rect(
                            modal_x,
                            modal_y,
                            modal_w,
                            self.modal_title_bar_height
                        )
                        if title_bar_rect.collidepoint(mouse_x, mouse_y):
                            # Check if clicking on close button first (exclude from dragging)
                            close_btn_size = int(20 * self.scale)
                            close_btn_x = modal_x + modal_w - close_btn_size - int(5 * self.scale)
                            close_btn_y = modal_y + int(5 * self.scale)
                            close_btn_rect = pygame.Rect(close_btn_x, close_btn_y, close_btn_size, close_btn_size)
                            
                            # If clicking on close button, handle it directly here
                            if close_btn_rect.collidepoint(mouse_x, mouse_y):
                                # Close the modal
                                # Reset entire OS Mode when any modal closes
                                self._reset_os_mode()
                                return True
                            else:
                                # Start dragging this modal
                                self.modal_dragging = modal_name
                                self.modal_drag_offset = (mouse_x - modal_x, mouse_y - modal_y)
                                return True
                
                # Check if clicking on an icon FIRST (icons should be clickable even when modals are open)
                icon_clicked = False
                clicked_icon = None
                for icon in self.icons:
                    icon_rect = pygame.Rect(
                        icon["x"],
                        icon["y"],
                        icon["width"],
                        icon["height"]
                    )
                    if icon_rect.collidepoint(mouse_x, mouse_y):
                        icon_clicked = True
                        clicked_icon = icon
                        
                        # Check for double-click
                        is_double_click = (
                            self.last_click_pos is not None and
                            abs(self.last_click_pos[0] - mouse_x) < 5 and
                            abs(self.last_click_pos[1] - mouse_y) < 5 and
                            (current_time - self.last_click_time) < self.double_click_threshold
                        )
                        
                        if is_double_click:
                            # Double-click detected - open modal based on icon
                            icon_name = icon["name"]
                            modal_name = None
                            if "tape-icon" in icon_name:
                                modal_name = "tape"
                                self.tape_modal_terminal_text = ""
                                self._stop_tape_video()
                            elif "hard-drive-icon" in icon_name:
                                modal_name = "hard_drive"
                            elif "modem-iconpng" in icon_name:
                                modal_name = "modem"
                                # Initialize dial pad state
                                self.modem_modal_dialed_sequence = ""
                                self.modem_modal_connection_messages = []
                                self.modem_modal_message_index = 0
                                self.modem_modal_message_timer = 0.0
                                self.modem_modal_should_reset_bbs = False
                                self.modem_modal_should_exit_os = False
                                self.modem_modal_connection_started = False
                            elif "games-folder" in icon_name:
                                modal_name = "games"
                            elif "notes-icon" in icon_name:
                                modal_name = "notes"
                            
                            if modal_name:
                                # Add modal to active set
                                self.active_modals.add(modal_name)
                                # Set initial position if not already set
                                if modal_name not in self.modal_positions:
                                    modal_w, modal_h = self._get_modal_size(modal_name)
                                    modal_x, modal_y = self._get_modal_position(modal_w, modal_h, modal_name)
                                    self.modal_positions[modal_name] = (modal_x, modal_y)
                            
                            # Reset double-click tracking
                            self.last_click_time = 0.0
                            self.last_click_pos = None
                            return True
                        else:
                            # Single click - select icon
                            # Deselect all icons first
                            for other_icon in self.icons:
                                other_icon["selected"] = False
                            # Select the clicked icon
                            icon["selected"] = True
                            icon["dragging"] = True
                            icon["drag_offset_x"] = mouse_x - icon["x"]
                            icon["drag_offset_y"] = mouse_y - icon["y"]
                            
                            # Update double-click tracking
                            self.last_click_time = current_time
                            self.last_click_pos = (mouse_x, mouse_y)
                            return True
                
                # Handle modal button clicks (check modals in reverse order for top-most first)
                # Only check modals if we didn't click on an icon
                if not icon_clicked:
                    for modal_name in reversed(list(self.active_modals)):
                        if modal_name == "tape":
                            if self._handle_tape_modal_click(mouse_x, mouse_y):
                                return True
                        elif modal_name == "modem":
                            if self._handle_modem_modal_click(mouse_x, mouse_y):
                                return True
                
                # If clicking on desktop (not on an icon), deselect all icons
                if not icon_clicked and self.desktop_rect.collidepoint(mouse_x, mouse_y):
                    for icon in self.icons:
                        icon["selected"] = False
                    # Reset double-click tracking
                    self.last_click_time = 0.0
                    self.last_click_pos = None
                    return True
        
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:  # Left mouse button
                self.mouse_pressed = False
                # Stop dragging all icons
                for icon in self.icons:
                    if icon["dragging"]:
                        icon["dragging"] = False
                        return True
        
        return False
    
    def _get_modal_size(self, modal_name: str) -> Tuple[int, int]:
        """Get modal dimensions for a given modal name."""
        gap = int(20 * self.scale)
        
        if modal_name == "tape":
            # Tape modal dimensions (smaller window)
            modal_w = int(500 * self.scale)
            modal_h = int(400 * self.scale) + self.modal_title_bar_height
        elif modal_name == "modem":
            # Modem modal dimensions
            button_size = int(60 * self.scale)
            button_spacing = int(10 * self.scale)
            terminal_h = int(150 * self.scale)
            dial_pad_h = 4 * button_size + 3 * button_spacing
            call_btn_h = int(30 * self.scale)
            spacing = int(20 * self.scale)
            modal_w = 3 * button_size + 2 * button_spacing + 2 * gap
            modal_h = gap + terminal_h + spacing + dial_pad_h + spacing + call_btn_h + gap + self.modal_title_bar_height
        else:
            # Default dimensions
            modal_w = int(400 * self.scale)
            modal_h = int(300 * self.scale) + self.modal_title_bar_height
        
        return (modal_w, modal_h)
    
    def _get_modal_position(self, modal_w: int, modal_h: int, modal_name: str = None) -> Tuple[int, int]:
        """Calculate modal position within desktop boundaries. Uses stored position if available."""
        # If modal has a stored position, use it
        if modal_name and modal_name in self.modal_positions:
            stored_x, stored_y = self.modal_positions[modal_name]
            # Ensure it's still within bounds
            max_x = self.desktop_x + self.desktop_size[0] - modal_w
            max_y = self.desktop_y + self.desktop_size[1] - modal_h
            stored_x = max(self.desktop_x, min(stored_x, max_x))
            stored_y = max(self.desktop_y, min(stored_y, max_y))
            return (stored_x, stored_y)
        
        # Position modal with margin from desktop edges
        margin = int(50 * self.scale)
        modal_x = self.desktop_x + margin
        modal_y = self.desktop_y + margin
        
        # Ensure modal doesn't extend beyond desktop boundaries
        max_x = self.desktop_x + self.desktop_size[0] - modal_w - margin
        max_y = self.desktop_y + self.desktop_size[1] - modal_h - margin
        
        modal_x = max(self.desktop_x + margin, min(modal_x, max_x))
        modal_y = max(self.desktop_y + margin, min(modal_y, max_y))
        
        return (modal_x, modal_y)
    
    def _clamp_modal_to_desktop(self, modal_w: int, modal_h: int) -> Tuple[int, int]:
        """Clamp modal dimensions to fit within desktop boundaries."""
        margin = int(100 * self.scale)  # Total margin (50px on each side)
        max_w = self.desktop_size[0] - margin
        max_h = self.desktop_size[1] - margin
        
        clamped_w = min(modal_w, max_w)
        clamped_h = min(modal_h, max_h)
        
        return (clamped_w, clamped_h)
    
    def _handle_tape_modal_click(self, mouse_x: int, mouse_y: int) -> bool:
        """Handle clicks within the tape modal. Returns True if click was handled."""
        # Modal dimensions (scaled)
        modal_w = int(800 * self.scale)
        modal_h = int(500 * self.scale) + self.modal_title_bar_height
        
        # Clamp modal to fit within desktop boundaries (same as drawing)
        modal_w, modal_h = self._clamp_modal_to_desktop(modal_w, modal_h)
        modal_x, modal_y = self.modal_positions.get("tape", (0, 0))
        
        # Check if clicking on close button in title bar
        close_btn_size = int(20 * self.scale)
        close_btn_x = modal_x + modal_w - close_btn_size - int(5 * self.scale)
        close_btn_y = modal_y + int(5 * self.scale)
        close_btn_rect = pygame.Rect(close_btn_x, close_btn_y, close_btn_size, close_btn_size)
        if close_btn_rect.collidepoint(mouse_x, mouse_y):
            # Reset entire OS Mode when modal closes
            self._reset_os_mode()
            return True
        
        modal_rect = pygame.Rect(modal_x, modal_y, modal_w, modal_h)
        if not modal_rect.collidepoint(mouse_x, mouse_y):
            return False
        
        # Button dimensions (accounting for title bar) - centered, no CLOSE button
        button_y = modal_y + self.modal_title_bar_height + int(220 * self.scale)  # Closer to terminal
        button_h = int(35 * self.scale)
        button_w = int(140 * self.scale)
        button_spacing = int(15 * self.scale)
        
        # Calculate total width of buttons and spacing for centering
        total_buttons_width = 2 * button_w + button_spacing  # Two buttons (LOAD and RECORD)
        buttons_start_x = modal_x + (modal_w - total_buttons_width) // 2  # Center align
        
        # LOAD DATA button
        load_btn_x = buttons_start_x
        load_btn_rect = pygame.Rect(load_btn_x, button_y, button_w, button_h)
        
        # RECORD DATA button
        record_btn_x = load_btn_x + button_w + button_spacing
        record_btn_rect = pygame.Rect(record_btn_x, button_y, button_w, button_h)
        
        if load_btn_rect.collidepoint(mouse_x, mouse_y):
            self.tape_modal_terminal_lines = ["No data to load"]
            self.tape_modal_terminal_text = "\n".join(self.tape_modal_terminal_lines)
            self.tape_modal_message_timer = 0.0
            self._stop_tape_video()
            return True
        elif record_btn_rect.collidepoint(mouse_x, mouse_y):
            # Clear terminal and start recording sequence
            self.tape_modal_terminal_lines = []
            self.tape_modal_message_timer = 0.0
            
            # Get current datetime and format as 1989 date with month and year
            from datetime import datetime
            current_dt = datetime.now()
            # Format as 1989-MM-DD HH:MM (replace year with 1989)
            date_str = current_dt.strftime("1989-%m-%d %H:%M")
            
            # First message immediately
            self.tape_modal_terminal_lines.append("Datasette Tape Detected Recoding Started")
            self.tape_modal_terminal_lines.append(date_str)
            
            # Update terminal text display
            self.tape_modal_terminal_text = "\n".join(self.tape_modal_terminal_lines)
            
            self._start_tape_video()
            return True
        
        return False
    
    def _handle_modem_modal_click(self, mouse_x: int, mouse_y: int) -> bool:
        """Handle clicks within the modem modal. Returns True if click was handled."""
        # Calculate modal dimensions based on dial pad with 20px gaps
        button_size = int(60 * self.scale)
        button_spacing = int(10 * self.scale)
        gap = int(20 * self.scale)  # 20px gap on each side
        
        # Width: 3 buttons + 2 gaps between + 2 side gaps
        modal_w = 3 * button_size + 2 * button_spacing + 2 * gap
        # Height: title bar + terminal + spacing + dial pad + spacing + close button + gaps
        terminal_h = int(150 * self.scale)
        dial_pad_h = 4 * button_size + 3 * button_spacing
        close_btn_h = int(30 * self.scale)
        spacing = int(20 * self.scale)
        modal_h = self.modal_title_bar_height + gap + terminal_h + spacing + dial_pad_h + spacing + close_btn_h + gap
        
        # Clamp modal to fit within desktop boundaries
        modal_w, modal_h = self._clamp_modal_to_desktop(modal_w, modal_h)
        modal_x, modal_y = self.modal_positions.get("modem", (0, 0))
        
        # Check if clicking on close button in title bar
        close_btn_size = int(20 * self.scale)
        close_btn_x = modal_x + modal_w - close_btn_size - int(5 * self.scale)
        close_btn_y = modal_y + int(5 * self.scale)
        close_btn_rect = pygame.Rect(close_btn_x, close_btn_y, close_btn_size, close_btn_size)
        if close_btn_rect.collidepoint(mouse_x, mouse_y):
            # Reset entire OS Mode when modal closes
            self._reset_os_mode()
            return True
        
        modal_rect = pygame.Rect(modal_x, modal_y, modal_w, modal_h)
        if not modal_rect.collidepoint(mouse_x, mouse_y):
            return False
        
        # Don't handle clicks if connection sequence has started
        if self.modem_modal_connection_started:
            return False
        
        # Calculate positions (accounting for title bar)
        dial_start_x = modal_x + gap
        dial_start_y = modal_y + self.modal_title_bar_height + gap + terminal_h + spacing
        
        # Dial pad buttons: 1-9, *, 0, #
        dial_buttons = [
            ["1", "2", "3"],
            ["4", "5", "6"],
            ["7", "8", "9"],
            ["*", "0", "#"]
        ]
        
        # Check if clicking on a dial button
        for row_idx, row in enumerate(dial_buttons):
            for col_idx, button_label in enumerate(row):
                btn_x = dial_start_x + col_idx * (button_size + button_spacing)
                btn_y = dial_start_y + row_idx * (button_size + button_spacing)
                btn_rect = pygame.Rect(btn_x, btn_y, button_size, button_size)
                
                if btn_rect.collidepoint(mouse_x, mouse_y):
                    # Add to dialed sequence
                    self.modem_modal_dialed_sequence += button_label
                    return True
        
        # CALL button (between dial pad and close button)
        call_btn_h = int(30 * self.scale)
        call_btn_x = modal_x + gap
        call_btn_y = modal_y + self.modal_title_bar_height + gap + terminal_h + spacing + dial_pad_h + spacing
        call_btn_w = modal_w - 2 * gap
        call_btn_rect = pygame.Rect(call_btn_x, call_btn_y, call_btn_w, call_btn_h)
        
        if call_btn_rect.collidepoint(mouse_x, mouse_y):
            # Check if sequence matches target
            if self.modem_modal_dialed_sequence == self.modem_modal_target_sequence:
                # Start connection sequence
                self.modem_modal_connection_started = True
                self.modem_modal_connection_messages = [
                    "Initializing modem connection...",
                    "Dialing 0345728891...",
                    "Establishing connection...",
                    "Handshaking...",
                    "Packets found!",
                    "Loading data...",
                    "Connection established!"
                ]
                self.modem_modal_message_index = 0
                self.modem_modal_message_timer = 0.0
            else:
                # Show error message if wrong number
                self.modem_modal_dialed_sequence = ""  # Clear sequence
            return True
        
        return False
    
    def _start_tape_video(self):
        """Start playing the Datasette_Load.mp4 video with chroma key."""
        if not _cv2_available:
            print("Warning: cv2 not available, cannot play video")
            return
        
        if self.tape_modal_video_playing:
            return  # Already playing
        
        video_path = get_data_path("OS", "Datasette_Load.mp4")
        if not os.path.exists(video_path):
            print(f"Warning: Video file not found: {video_path}")
            return
        
        try:
            self.tape_modal_video_cap = cv2.VideoCapture(video_path)
            if not self.tape_modal_video_cap.isOpened():
                print(f"Warning: Could not open video: {video_path}")
                return
            
            # Get video properties
            fps = self.tape_modal_video_cap.get(cv2.CAP_PROP_FPS)
            width = int(self.tape_modal_video_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.tape_modal_video_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self.tape_modal_video_original_size = (width, height)
            
            # Calculate display size maintaining aspect ratio
            # Target area: documentation viewer area (doubled)
            target_w = int(800 * self.scale * 2)  # Doubled docs viewer width
            target_h = int(600 * self.scale * 2)  # Doubled docs viewer height
            
            # Calculate aspect ratios
            video_aspect = width / height
            target_aspect = target_w / target_h
            
            # Scale to fit within target area while maintaining aspect ratio
            if video_aspect > target_aspect:
                # Video is wider - fit to width
                display_w = target_w
                display_h = int(target_w / video_aspect)
            else:
                # Video is taller - fit to height
                display_h = target_h
                display_w = int(target_h * video_aspect)
            
            self.tape_modal_video_display_size = (display_w, display_h)
            
            # Initialize fade state
            self.tape_modal_video_fade_state = "fade_in"
            self.tape_modal_video_fade_alpha = 0.0
            self.tape_modal_video_fade_timer = 0.0
            
            # Play audio from video file using pygame mixer
            # Note: cv2 doesn't handle audio, so we need a separate audio file
            # Try common audio formats
            audio_extensions = ['.wav', '.mp3', '.ogg']
            audio_loaded = False
            for ext in audio_extensions:
                audio_path = video_path.replace('.mp4', ext)
                if os.path.exists(audio_path):
                    try:
                        # Use pygame.mixer.music for longer audio files
                        pygame.mixer.music.load(audio_path)
                        pygame.mixer.music.play(0)  # Play once, don't loop
                        audio_loaded = True
                        break
                    except Exception as e:
                        print(f"Warning: Could not load audio file {audio_path}: {e}")
                        continue
            
            if not audio_loaded:
                print(f"Warning: Audio file not found for {video_path}. Video will play without sound.")
                print("  Expected audio file: Datasette_Load.wav, Datasette_Load.mp3, or Datasette_Load.ogg")
            
            self.tape_modal_video_playing = True
        except Exception as e:
            print(f"Warning: Failed to start video: {e}")
            self._stop_tape_video()
    
    def _stop_tape_video(self):
        """Stop playing the tape video."""
        self.tape_modal_video_playing = False
        if self.tape_modal_video_cap:
            self.tape_modal_video_cap.release()
            self.tape_modal_video_cap = None
        self.tape_modal_video_frame = None
        # Stop audio playback
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
        self.tape_modal_video_audio_channel = None
        # Reset fade state
        self.tape_modal_video_fade_state = "none"
        self.tape_modal_video_fade_alpha = 0.0
        self.tape_modal_video_fade_timer = 0.0
    
    def _apply_chroma_key(self, frame):
        """Apply chroma key to remove green (#00FF00) from frame with improved edge removal."""
        if frame is None or not _cv2_available:
            return None
        
        # Convert BGR to RGB (cv2 uses BGR, pygame uses RGB)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Convert to HSV for better color matching
        frame_hsv = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2HSV)
        
        # Define green color (#00FF00) in HSV
        # Pure green in HSV: H=120, S=255, V=255
        # Use wider range for better edge removal
        green_lower_hsv = np.array([50, 50, 50], dtype=np.uint8)   # Lower bound for green hue
        green_upper_hsv = np.array([80, 255, 255], dtype=np.uint8)  # Upper bound for green hue
        
        # Create mask for green pixels in HSV space
        mask_hsv = cv2.inRange(frame_hsv, green_lower_hsv, green_upper_hsv)
        
        # Also check RGB space for pure green (#00FF00)
        green_lower_rgb = np.array([0, 200, 0], dtype=np.uint8)
        green_upper_rgb = np.array([50, 255, 50], dtype=np.uint8)
        mask_rgb = cv2.inRange(frame_rgb, green_lower_rgb, green_upper_rgb)
        
        # Combine both masks
        mask = cv2.bitwise_or(mask_hsv, mask_rgb)
        
        # Apply morphological operations to clean up edges
        kernel = np.ones((3, 3), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)  # Close small holes
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)   # Remove small noise
        
        # Apply Gaussian blur for smoother edges
        mask = cv2.GaussianBlur(mask, (7, 7), 2)
        
        # Expand the mask slightly to remove edge artifacts
        mask = cv2.dilate(mask, kernel, iterations=1)
        
        # Invert mask (we want to keep non-green pixels)
        mask_inv = cv2.bitwise_not(mask)
        
        # Create alpha channel: 255 for non-green pixels, 0 for green pixels
        alpha = mask_inv
        
        # Combine RGB with alpha
        frame_rgba = np.dstack((frame_rgb, alpha))
        
        return frame_rgba
    
    def update(self, dt: float):
        """Update OS Mode state (call this every frame)."""
        # Stop video if modal is closed
        if "tape" not in self.active_modals and self.tape_modal_video_playing:
            self._stop_tape_video()
        
        # Update terminal message timer for delayed messages
        if "tape" in self.active_modals and self.tape_modal_video_playing:
            self.tape_modal_message_timer += dt
            # Show "YOU MAY CLOSE THE WINDOW" after 3 seconds (a couple of beats)
            if self.tape_modal_message_timer >= 3.0 and len(self.tape_modal_terminal_lines) == 2:
                self.tape_modal_terminal_lines.append("YOU MAY CLOSE THE WINDOW")
                self.tape_modal_terminal_text = "\n".join(self.tape_modal_terminal_lines)
        
        # Update modem modal connection messages
        if "modem" in self.active_modals and self.modem_modal_connection_started and self.modem_modal_connection_messages:
            self.modem_modal_message_timer += dt
            message_delay = 1.5  # Show each message for 1.5 seconds
            
            # Progress through messages
            if self.modem_modal_message_index < len(self.modem_modal_connection_messages):
                # Move to next message after delay
                if self.modem_modal_message_timer >= message_delay:
                    self.modem_modal_message_index += 1
                    self.modem_modal_message_timer = 0.0
                    
                    # If all messages shown, trigger reset
                    if self.modem_modal_message_index >= len(self.modem_modal_connection_messages):
                        self.modem_modal_should_reset_bbs = True
                        self.modem_modal_should_exit_os = True
                        # Call callback if available
                        if self.reset_bbs_callback:
                            self.reset_bbs_callback()
        
        # Update fade state
        if self.tape_modal_video_fade_state == "fade_in":
            self.tape_modal_video_fade_timer += dt
            if self.tape_modal_video_fade_timer >= self.tape_modal_video_fade_duration:
                self.tape_modal_video_fade_alpha = 1.0
                self.tape_modal_video_fade_state = "playing"
            else:
                self.tape_modal_video_fade_alpha = min(1.0, self.tape_modal_video_fade_timer / self.tape_modal_video_fade_duration)
        elif self.tape_modal_video_fade_state == "fade_out":
            self.tape_modal_video_fade_timer += dt
            if self.tape_modal_video_fade_timer >= self.tape_modal_video_fade_duration:
                self.tape_modal_video_fade_alpha = 0.0
                self._stop_tape_video()
            else:
                self.tape_modal_video_fade_alpha = max(0.0, 1.0 - (self.tape_modal_video_fade_timer / self.tape_modal_video_fade_duration))
        
        # Update video playback
        if self.tape_modal_video_playing and self.tape_modal_video_cap:
            # Check if video has ended (for fade out)
            total_frames = int(self.tape_modal_video_cap.get(cv2.CAP_PROP_FRAME_COUNT))
            current_frame = int(self.tape_modal_video_cap.get(cv2.CAP_PROP_POS_FRAMES))
            
            # Start fade out near the end of video
            if self.tape_modal_video_fade_state == "playing" and total_frames > 0:
                frames_until_end = total_frames - current_frame
                fps = self.tape_modal_video_cap.get(cv2.CAP_PROP_FPS)
                if fps > 0:
                    seconds_until_end = frames_until_end / fps
                    if seconds_until_end <= self.tape_modal_video_fade_duration:
                        self.tape_modal_video_fade_state = "fade_out"
                        self.tape_modal_video_fade_timer = 0.0
            
            # Only read frames if not fading out after video ended
            if self.tape_modal_video_fade_state != "fade_out" or self.tape_modal_video_frame is not None:
                ret, frame = self.tape_modal_video_cap.read()
                if ret:
                    # Apply chroma key
                    frame_rgba = self._apply_chroma_key(frame)
                    if frame_rgba is not None:
                        # Resize frame maintaining aspect ratio
                        if self.tape_modal_video_display_size:
                            frame_resized = cv2.resize(frame_rgba, self.tape_modal_video_display_size, interpolation=cv2.INTER_LINEAR)
                        else:
                            frame_resized = frame_rgba
                        
                        # Convert RGBA numpy array to pygame surface
                        height, width = frame_resized.shape[:2]
                        
                        # Ensure values are in correct range (0-255) and correct dtype
                        frame_resized = np.clip(frame_resized, 0, 255).astype(np.uint8)
                        
                        # Extract RGB and alpha channels
                        rgb_data = frame_resized[:, :, :3]  # RGB channels (height, width, 3)
                        alpha_data = frame_resized[:, :, 3]  # Alpha channel (height, width)
                        
                        # Apply fade alpha to the alpha channel
                        alpha_data = (alpha_data * self.tape_modal_video_fade_alpha).astype(np.uint8)
                        
                        # Swap axes for pygame (pygame expects (width, height, channels))
                        rgb_swapped = np.swapaxes(rgb_data, 0, 1)  # (width, height, 3)
                        
                        # Create RGB surface
                        frame_surface = pygame.surfarray.make_surface(rgb_swapped)
                        
                        # Convert to alpha surface
                        frame_surface = frame_surface.convert_alpha()
                        
                        # Set alpha channel (with fade applied)
                        alpha_swapped = np.swapaxes(alpha_data, 0, 1)  # (width, height)
                        alpha_array = pygame.surfarray.pixels_alpha(frame_surface)
                        alpha_array[:] = alpha_swapped
                        del alpha_array  # Release the array lock
                        
                        self.tape_modal_video_frame = frame_surface
                else:
                    # Video ended - start fade out if not already fading
                    if self.tape_modal_video_fade_state == "playing":
                        self.tape_modal_video_fade_state = "fade_out"
                        self.tape_modal_video_fade_timer = 0.0
            
            # Check if fade out is complete
            if self.tape_modal_video_fade_state == "fade_out" and self.tape_modal_video_fade_alpha <= 0.0:
                # Fade out complete, stop video
                self._stop_tape_video()
    
    def draw(self):
        """Draw the OS Mode desktop environment."""
        if not self.desktop_image:
            return
        
        # Draw desktop background
        self.screen.blit(self.desktop_image, (self.desktop_x, self.desktop_y))
        
        # Draw icons (use selected "S" version if selected, otherwise normal version)
        for icon in self.icons:
            # Use S version if selected, otherwise normal version
            icon_to_draw = icon["s_image"] if icon["selected"] else icon["image"]
            self.screen.blit(icon_to_draw, (icon["x"], icon["y"]))
        
        # Draw all active modals (in order they were opened)
        for modal_name in list(self.active_modals):
            if modal_name == "tape":
                self._draw_tape_modal()
            elif modal_name == "modem":
                self._draw_modem_modal()
    
    def _draw_tape_modal(self):
        """Draw the tape icon modal."""
        # Modal dimensions (scaled)
        modal_w = int(800 * self.scale)
        modal_h = int(500 * self.scale) + self.modal_title_bar_height
        
        # Clamp modal to fit within desktop boundaries
        modal_w, modal_h = self._clamp_modal_to_desktop(modal_w, modal_h)
        
        # Get position from stored position or calculate new one
        modal_x, modal_y = self.modal_positions.get("tape", self._get_modal_position(modal_w, modal_h, "tape"))
        if "tape" not in self.modal_positions:
            self.modal_positions["tape"] = (modal_x, modal_y)
        
        # Draw modal background (dark blue/black with border)
        modal_rect = pygame.Rect(modal_x, modal_y, modal_w, modal_h)
        pygame.draw.rect(self.screen, COLOR_BG_DARK, modal_rect)
        pygame.draw.rect(self.screen, COLOR_CYAN, modal_rect, 2)  # Cyan border
        
        # Draw title bar
        title_bar_rect = pygame.Rect(modal_x, modal_y, modal_w, self.modal_title_bar_height)
        pygame.draw.rect(self.screen, COLOR_BG_TITLE, title_bar_rect)
        pygame.draw.rect(self.screen, COLOR_CYAN, title_bar_rect, 1)  # Cyan border
        
        # Draw title text
        try:
            font_size = max(int(16 * self.scale), 12)
            title_font = pygame.font.Font(None, font_size)
            title_text = title_font.render("Tape Drive", True, COLOR_CYAN)
            self.screen.blit(title_text, (modal_x + int(10 * self.scale), modal_y + int(5 * self.scale)))
        except Exception:
            pass
        
        # Draw close button in title bar with hover effect
        close_btn_size = int(20 * self.scale)
        close_btn_x = modal_x + modal_w - close_btn_size - int(5 * self.scale)
        close_btn_y = modal_y + int(5 * self.scale)
        close_btn_rect = pygame.Rect(close_btn_x, close_btn_y, close_btn_size, close_btn_size)
        is_hovered = self.hovered_button == ("tape", "title_close")
        close_color = COLOR_RED if is_hovered else COLOR_RED_DARK
        pygame.draw.rect(self.screen, close_color, close_btn_rect)
        pygame.draw.rect(self.screen, COLOR_RED, close_btn_rect, 2 if is_hovered else 1)
        try:
            close_font = pygame.font.Font(None, max(int(14 * self.scale), 10))
            close_text = close_font.render("X", True, COLOR_WHITE)
            close_text_rect = close_text.get_rect(center=close_btn_rect.center)
            self.screen.blit(close_text, close_text_rect)
        except Exception:
            pass
        
        # Draw terminal window (below title bar) - smaller and closer to buttons
        terminal_x = modal_x + int(20 * self.scale)
        terminal_y = modal_y + self.modal_title_bar_height + int(20 * self.scale)
        terminal_w = modal_w - int(40 * self.scale)
        terminal_h = int(180 * self.scale)  # Smaller terminal height
        
        terminal_rect = pygame.Rect(terminal_x, terminal_y, terminal_w, terminal_h)
        pygame.draw.rect(self.screen, COLOR_BLACK, terminal_rect)
        pygame.draw.rect(self.screen, COLOR_CYAN, terminal_rect, 1)  # Cyan border
        
        # Draw terminal text (multi-line support) - larger font
        if self.tape_modal_terminal_lines:
            # Create a simple font for terminal text - larger size
            try:
                font_size = max(int(22 * self.scale), 18)  # Increased from 16 to 22
                terminal_font = pygame.font.Font(None, font_size)
                text_x = terminal_x + int(10 * self.scale)
                text_y = terminal_y + int(10 * self.scale)
                line_height = int(26 * self.scale)  # Increased from 20 to 26
                
                # Draw each line
                for line in self.tape_modal_terminal_lines:
                    if line:  # Only draw non-empty lines
                        text_surface = terminal_font.render(line, True, COLOR_GREEN)  # Green text
                        self.screen.blit(text_surface, (text_x, text_y))
                        text_y += line_height
            except Exception:
                pass
        
        # Draw buttons (below terminal, closer and centered)
        button_y = modal_y + self.modal_title_bar_height + int(220 * self.scale)  # Closer to terminal
        button_h = int(35 * self.scale)
        button_w = int(140 * self.scale)
        button_spacing = int(15 * self.scale)
        
        # Calculate total width of buttons and spacing for centering
        total_buttons_width = 2 * button_w + button_spacing  # Two buttons (LOAD and RECORD)
        buttons_start_x = modal_x + (modal_w - total_buttons_width) // 2  # Center align
        
        # LOAD DATA button
        load_btn_x = buttons_start_x
        load_btn_rect = pygame.Rect(load_btn_x, button_y, button_w, button_h)
        is_hovered = self.hovered_button == ("tape", "load")
        btn_color = COLOR_BUTTON_HOVER if is_hovered else COLOR_BG_TITLE
        pygame.draw.rect(self.screen, btn_color, load_btn_rect)
        pygame.draw.rect(self.screen, COLOR_CYAN, load_btn_rect, 2 if is_hovered else 1)
        try:
            font_size = max(int(14 * self.scale), 10)
            button_font = pygame.font.Font(None, font_size)
            load_text = button_font.render("LOAD DATA", True, COLOR_CYAN)
            load_text_rect = load_text.get_rect(center=load_btn_rect.center)
            self.screen.blit(load_text, load_text_rect)
        except Exception:
            pass
        
        # RECORD DATA button
        record_btn_x = load_btn_x + button_w + button_spacing
        record_btn_rect = pygame.Rect(record_btn_x, button_y, button_w, button_h)
        is_hovered = self.hovered_button == ("tape", "record")
        btn_color = COLOR_BUTTON_HOVER if is_hovered else COLOR_BG_TITLE
        pygame.draw.rect(self.screen, btn_color, record_btn_rect)
        pygame.draw.rect(self.screen, COLOR_CYAN, record_btn_rect, 2 if is_hovered else 1)
        try:
            record_text = button_font.render("RECORD DATA", True, COLOR_CYAN)
            record_text_rect = record_text.get_rect(center=record_btn_rect.center)
            self.screen.blit(record_text, record_text_rect)
        except Exception:
            pass
        
        # Draw video if playing (at specified Datasette position)
        if self.tape_modal_video_playing and self.tape_modal_video_frame:
            # Render from baseline coordinates (1363, 44)
            video_x = int(self.datasette_baseline_x * self.scale)
            video_y = int(self.datasette_baseline_y * self.scale)
            
            # Move video 50px to the right (scaled)
            video_x += int(50 * self.scale)
            
            # Draw with fade alpha already applied in the surface
            self.screen.blit(self.tape_modal_video_frame, (video_x, video_y))
    
    def draw_scanline(self):
        """Draw the desktop scanline overlay."""
        if self.desktop_scanline_image:
            self.screen.blit(self.desktop_scanline_image, (self.desktop_x, self.desktop_y))
    
    def _draw_modem_modal(self):
        """Draw the modem icon modal with telephone dial."""
        # Calculate modal dimensions based on dial pad with 20px gaps
        button_size = int(60 * self.scale)
        button_spacing = int(10 * self.scale)
        gap = int(20 * self.scale)  # 20px gap on each side
        
        # Width: 3 buttons + 2 gaps between + 2 side gaps
        modal_w = 3 * button_size + 2 * button_spacing + 2 * gap
        # Height: title bar + terminal + spacing + dial pad + spacing + call button + gaps (no CLOSE button)
        terminal_h = int(150 * self.scale)
        dial_pad_h = 4 * button_size + 3 * button_spacing
        call_btn_h = int(30 * self.scale)
        spacing = int(20 * self.scale)
        modal_h = self.modal_title_bar_height + gap + terminal_h + spacing + dial_pad_h + spacing + call_btn_h + gap
        
        # Clamp modal to fit within desktop boundaries
        modal_w, modal_h = self._clamp_modal_to_desktop(modal_w, modal_h)
        modal_x, modal_y = self.modal_positions.get("modem", self._get_modal_position(modal_w, modal_h, "modem"))
        if "modem" not in self.modal_positions:
            self.modal_positions["modem"] = (modal_x, modal_y)
        
        # Draw modal background (dark blue/black with border)
        modal_rect = pygame.Rect(modal_x, modal_y, modal_w, modal_h)
        pygame.draw.rect(self.screen, COLOR_BG_DARK, modal_rect)
        pygame.draw.rect(self.screen, COLOR_CYAN, modal_rect, 2)  # Cyan border
        
        # Draw title bar
        title_bar_rect = pygame.Rect(modal_x, modal_y, modal_w, self.modal_title_bar_height)
        pygame.draw.rect(self.screen, COLOR_BG_TITLE, title_bar_rect)
        pygame.draw.rect(self.screen, COLOR_CYAN, title_bar_rect, 1)  # Cyan border
        
        # Draw title text
        try:
            font_size = max(int(16 * self.scale), 12)
            title_font = pygame.font.Font(None, font_size)
            title_text = title_font.render("Modem", True, COLOR_CYAN)
            self.screen.blit(title_text, (modal_x + int(10 * self.scale), modal_y + int(5 * self.scale)))
        except Exception:
            pass
        
        # Draw close button in title bar with hover effect
        close_btn_size = int(20 * self.scale)
        close_btn_x = modal_x + modal_w - close_btn_size - int(5 * self.scale)
        close_btn_y = modal_y + int(5 * self.scale)
        close_btn_rect = pygame.Rect(close_btn_x, close_btn_y, close_btn_size, close_btn_size)
        is_hovered = self.hovered_button == ("modem", "title_close")
        close_color = COLOR_RED if is_hovered else COLOR_RED_DARK
        pygame.draw.rect(self.screen, close_color, close_btn_rect)
        pygame.draw.rect(self.screen, COLOR_RED, close_btn_rect, 2 if is_hovered else 1)
        try:
            close_font = pygame.font.Font(None, max(int(14 * self.scale), 10))
            close_text = close_font.render("X", True, COLOR_WHITE)
            close_text_rect = close_text.get_rect(center=close_btn_rect.center)
            self.screen.blit(close_text, close_text_rect)
        except Exception:
            pass
        
        # Draw terminal window (below title bar)
        terminal_x = modal_x + gap
        terminal_y = modal_y + self.modal_title_bar_height + gap
        terminal_w = modal_w - 2 * gap
        
        terminal_rect = pygame.Rect(terminal_x, terminal_y, terminal_w, terminal_h)
        pygame.draw.rect(self.screen, COLOR_BLACK, terminal_rect)
        pygame.draw.rect(self.screen, COLOR_CYAN, terminal_rect, 1)  # Cyan border
        
        # Draw terminal text
        try:
            font_size = max(int(18 * self.scale), 14)
            terminal_font = pygame.font.Font(None, font_size)
            text_x = terminal_x + int(10 * self.scale)
            text_y = terminal_y + int(10 * self.scale)
            line_height = int(22 * self.scale)
            
            # Show dialed sequence or connection messages
            if self.modem_modal_connection_started and self.modem_modal_connection_messages:
                # Show connection messages
                for i in range(min(self.modem_modal_message_index + 1, len(self.modem_modal_connection_messages))):
                    line = self.modem_modal_connection_messages[i]
                    if line:
                        text_surface = terminal_font.render(line, True, COLOR_GREEN)  # Green text
                        self.screen.blit(text_surface, (text_x, text_y))
                        text_y += line_height
            elif self.modem_modal_dialed_sequence:
                # Show dialed sequence
                text_surface = terminal_font.render(f"Dialed: {self.modem_modal_dialed_sequence}", True, COLOR_GREEN)
                self.screen.blit(text_surface, (text_x, text_y))
        except Exception:
            pass
        
        # Draw telephone dial pad (only if connection hasn't started, accounting for title bar)
        if not self.modem_modal_connection_started:
            dial_start_x = modal_x + gap
            dial_start_y = modal_y + self.modal_title_bar_height + gap + terminal_h + spacing
            
            # Dial pad buttons: 1-9, *, 0, #
            dial_buttons = [
                ["1", "2", "3"],
                ["4", "5", "6"],
                ["7", "8", "9"],
                ["*", "0", "#"]
            ]
            
            try:
                font_size = max(int(20 * self.scale), 14)
                button_font = pygame.font.Font(None, font_size)
            except Exception:
                button_font = None
            
            for row_idx, row in enumerate(dial_buttons):
                for col_idx, button_label in enumerate(row):
                    btn_x = dial_start_x + col_idx * (button_size + button_spacing)
                    btn_y = dial_start_y + row_idx * (button_size + button_spacing)
                    btn_rect = pygame.Rect(btn_x, btn_y, button_size, button_size)
                    
                    # Check if button is hovered
                    is_hovered = self.hovered_button == ("modem", f"dial_{button_label}")
                    btn_color = COLOR_BUTTON_HOVER if is_hovered else COLOR_BG_TITLE
                    
                    # Draw button with hover effect
                    pygame.draw.rect(self.screen, btn_color, btn_rect)
                    pygame.draw.rect(self.screen, COLOR_CYAN, btn_rect, 2 if is_hovered else 2)
                    
                    # Draw button label
                    if button_font:
                        text_surface = button_font.render(button_label, True, COLOR_CYAN)
                        text_rect = text_surface.get_rect(center=btn_rect.center)
                        self.screen.blit(text_surface, text_rect)
        
        # Draw CALL button (only if connection hasn't started, accounting for title bar)
        if not self.modem_modal_connection_started:
            call_btn_x = modal_x + gap
            call_btn_y = modal_y + self.modal_title_bar_height + gap + terminal_h + spacing + dial_pad_h + spacing
            call_btn_w = modal_w - 2 * gap
            call_btn_h = int(30 * self.scale)
            call_btn_rect = pygame.Rect(call_btn_x, call_btn_y, call_btn_w, call_btn_h)
            is_hovered = self.hovered_button == ("modem", "call")
            btn_color = COLOR_BUTTON_HOVER if is_hovered else COLOR_BG_TITLE
            pygame.draw.rect(self.screen, btn_color, call_btn_rect)
            pygame.draw.rect(self.screen, COLOR_CYAN, call_btn_rect, 2 if is_hovered else 1)
            
            try:
                font_size = max(int(16 * self.scale), 12)
                button_font = pygame.font.Font(None, font_size)
                call_text = button_font.render("CALL", True, COLOR_CYAN)
                call_text_rect = call_text.get_rect(center=call_btn_rect.center)
                self.screen.blit(call_text, call_text_rect)
            except Exception:
                pass
        
    
    def _get_icon_positions_file_path(self) -> str:
        """Get the path to the icon positions JSON file."""
        # Save in OS folder alongside OS_Mode.py
        os_folder = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(os_folder, "icon_positions.json")
    
    def _load_icon_positions(self) -> Dict[str, Dict[str, int]]:
        """Load saved icon positions from JSON file. Returns empty dict if file doesn't exist."""
        file_path = self._get_icon_positions_file_path()
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    # Validate data structure
                    if isinstance(data, dict):
                        return data
            return {}
        except Exception as e:
            print(f"Warning: Failed to load icon positions: {e}")
            return {}
    
    def _save_icon_positions(self):
        """Save current icon positions to JSON file, overwriting previous data."""
        file_path = self._get_icon_positions_file_path()
        try:
            # Capture current icon positions (overwriting, not appending)
            positions = {}
            for icon in self.icons:
                positions[icon["name"]] = {
                    "x": icon["x"],
                    "y": icon["y"]
                }
            
            # Write to file (overwrites existing file)
            with open(file_path, 'w') as f:
                json.dump(positions, f, indent=2)
        except Exception as e:
            print(f"Warning: Failed to save icon positions: {e}")
    
    def _reset_os_mode(self):
        """Reset OS Mode to its initial state - resets icons, modals, and all state."""
        # Reset all modals
        self.active_modals.clear()
        self.modal_positions.clear()
        self.modal_dragging = None
        self.modal_drag_offset = (0, 0)
        
        # Reset tape modal state
        self.tape_modal_terminal_text = ""
        self.tape_modal_terminal_lines = []
        self.tape_modal_message_timer = 0.0
        self._stop_tape_video()
        
        # Reset modem modal state
        self.modem_modal_dialed_sequence = ""
        self.modem_modal_connection_messages = []
        self.modem_modal_message_index = 0
        self.modem_modal_message_timer = 0.0
        self.modem_modal_connection_started = False
        self.modem_modal_should_reset_bbs = False
        self.modem_modal_should_exit_os = False
        
        # Reset icon states and restore positions from saved file (or defaults if none saved)
        saved_positions = self._load_icon_positions()
        current_y = self.desktop_y + int(70 * self.scale)  # Start 70px down from desktop top
        icon_spacing = int(10 * self.scale)
        
        for icon in self.icons:
            # Restore from saved position if available, otherwise use default stacked position
            if icon["name"] in saved_positions:
                # Use saved position (already scaled)
                icon["x"] = saved_positions[icon["name"]]["x"]
                icon["y"] = saved_positions[icon["name"]]["y"]
            else:
                # Default position: top-left corner, stacked vertically
                icon["x"] = self.desktop_x + int(10 * self.scale)  # Small margin from left
                icon["y"] = current_y
                # Move to next position for next icon
                current_y += icon["height"] + icon_spacing
            
            # Reset icon state
            icon["selected"] = False
            icon["dragging"] = False
            icon["drag_offset_x"] = 0
            icon["drag_offset_y"] = 0
        
        # Reset hover states
        self.hovered_icon = None
        self.hovered_button = None
        self.icon_label_alpha.clear()
        
        # Reset overlay state
        self.overlay_active = False
        
        # Reset double-click tracking
        self.last_click_time = 0.0
        self.last_click_pos = None
    
    def toggle_overlay(self):
        """Toggle the overlay rectangle state."""
        self.overlay_active = not self.overlay_active
    
    def draw_overlay(self):
        """Draw the overlay rectangle matching desktop dimensions."""
        if self.overlay_active:
            overlay_rect = pygame.Rect(
                self.desktop_x,
                self.desktop_y,
                self.desktop_size[0],
                self.desktop_size[1]
            )
            pygame.draw.rect(self.screen, (0, 0, 0), overlay_rect)  # Black rectangle
    
    def is_mouse_in_desktop(self, mouse_x: int, mouse_y: int) -> bool:
        """Check if mouse position is within desktop boundaries."""
        return (self.desktop_x <= mouse_x < self.desktop_x + self.desktop_size[0] and
                self.desktop_y <= mouse_y < self.desktop_y + self.desktop_size[1])
    
    def set_cursor(self, mouse_x: int, mouse_y: int):
        """Set the cursor based on mouse position relative to desktop."""
        if self.is_mouse_in_desktop(mouse_x, mouse_y):
            # Mouse is inside desktop - use OS cursor
            if self.custom_cursor:
                try:
                    pygame.mouse.set_cursor(self.custom_cursor)
                except Exception:
                    pass
        # If mouse is outside desktop, don't set cursor here - let main.py handle it
    
    def draw_cursor(self, mouse_x: int, mouse_y: int):
        """Draw the custom OS mouse cursor as a sprite (under scanlines)."""
        if self.cursor_image and self.is_mouse_in_desktop(mouse_x, mouse_y):
            # Draw cursor image at mouse position (offset by cursor size for better positioning)
            cursor_w, cursor_h = self.cursor_image.get_size()
            # Draw cursor centered on mouse position (or adjust offset as needed)
            self.screen.blit(self.cursor_image, (mouse_x, mouse_y))
    
    def update_scale(self, new_scale: float):
        """Update scale factor and recalculate positions/sizes."""
        # Capture old scale before updating
        old_scale = self.scale
        self.scale = new_scale
        
        # Recalculate desktop position
        self.desktop_x = int(self.baseline_desktop_x * self.scale)
        self.desktop_y = int(self.baseline_desktop_y * self.scale)
        
        # Reload and rescale desktop image
        desktop_path = get_data_path("OS", "Desktop-Enviroment.png")
        try:
            self.desktop_image = pygame.image.load(desktop_path).convert_alpha()
            original_size = self.desktop_image.get_size()
            self.desktop_size = (
                int(original_size[0] * self.scale),
                int(original_size[1] * self.scale)
            )
            self.desktop_image = pygame.transform.scale(self.desktop_image, self.desktop_size)
        except Exception as e:
            print(f"Warning: Failed to reload Desktop-Enviroment.png: {e}")
            self.desktop_image = None
        
        # Update desktop rect
        self.desktop_rect = pygame.Rect(
            self.desktop_x,
            self.desktop_y,
            self.desktop_size[0],
            self.desktop_size[1]
        )
        
        # Reload and rescale icons (both normal and selected versions)
        # Preserve current icon positions and scale them proportionally
        scale_ratio = new_scale / old_scale if old_scale > 0 else 1.0
        
        for icon in self.icons:
            icon_path = get_data_path("OS", icon["name"])
            # Get the "S" version filename
            s_icon_file = "S-" + icon["name"]
            s_icon_path = get_data_path("OS", s_icon_file)
            
            # Save current position before reloading
            old_x = icon["x"]
            old_y = icon["y"]
            
            try:
                # Reload normal icon
                icon_image = pygame.image.load(icon_path).convert_alpha()
                original_icon_size = icon_image.get_size()
                icon_size = (
                    int(original_icon_size[0] * self.scale),
                    int(original_icon_size[1] * self.scale)
                )
                icon_image = pygame.transform.scale(icon_image, icon_size)
                
                # Reload selected "S" version icon
                s_icon_image = None
                try:
                    s_icon_image = pygame.image.load(s_icon_path).convert_alpha()
                    s_icon_image = pygame.transform.scale(s_icon_image, icon_size)
                except Exception as e:
                    print(f"Warning: Failed to reload {s_icon_file}: {e}")
                    # If S version doesn't exist, use normal icon as fallback
                    s_icon_image = icon_image
                
                icon["image"] = icon_image
                icon["s_image"] = s_icon_image
                icon["width"] = icon_size[0]
                icon["height"] = icon_size[1]
                
                # Scale icon position proportionally to maintain relative position
                # Calculate position relative to OLD desktop position, then scale to NEW desktop position
                old_desktop_x = int(self.baseline_desktop_x * old_scale)
                old_desktop_y = int(self.baseline_desktop_y * old_scale)
                rel_x = old_x - old_desktop_x
                rel_y = old_y - old_desktop_y
                icon["x"] = self.desktop_x + int(rel_x * scale_ratio)
                icon["y"] = self.desktop_y + int(rel_y * scale_ratio)
            except Exception as e:
                print(f"Warning: Failed to reload {icon['name']}: {e}")
        
        # Reload and rescale cursor
        cursor_path = get_data_path("OS", "mouse_cursor.png")
        try:
            cursor_image = pygame.image.load(cursor_path).convert_alpha()
            original_cursor_size = cursor_image.get_size()
            cursor_size = (
                int(original_cursor_size[0] * self.scale),
                int(original_cursor_size[1] * self.scale)
            )
            cursor_image = pygame.transform.scale(cursor_image, cursor_size)
            self.custom_cursor = pygame.cursors.Cursor((0, 0), cursor_image)
            self.cursor_image = cursor_image
        except Exception as e:
            print(f"Warning: Failed to reload mouse_cursor.png: {e}")
        
        # Reload and rescale desktop scanline
        scanline_path = get_data_path("OS", "Scanline-Desktop.png")
        try:
            self.desktop_scanline_image = pygame.image.load(scanline_path).convert_alpha()
            self.desktop_scanline_image = pygame.transform.scale(
                self.desktop_scanline_image, 
                self.desktop_size
            )
        except Exception as e:
            print(f"Warning: Failed to reload Scanline-Desktop.png: {e}")
            self.desktop_scanline_image = None
    
    def _update_hover_states(self, mouse_x: int, mouse_y: int):
        """Update hover states for icons and buttons based on mouse position."""
        # Reset hover states
        self.hovered_icon = None
        self.hovered_button = None
        
        # Check icon hovers (only if not dragging)
        if not self.mouse_pressed:
            for icon in self.icons:
                icon_rect = pygame.Rect(icon["x"], icon["y"], icon["width"], icon["height"])
                if icon_rect.collidepoint(mouse_x, mouse_y):
                    self.hovered_icon = icon
                    break
        
        # Check button hovers in modals (check top-most first)
        for modal_name in reversed(list(self.active_modals)):
            modal_x, modal_y = self.modal_positions.get(modal_name, (0, 0))
            modal_w, modal_h = self._get_modal_size(modal_name)
            
            if modal_name == "tape":
                # Check tape modal buttons
                button_y = modal_y + self.modal_title_bar_height + int(390 * self.scale)
                button_h = int(40 * self.scale)
                button_w = int(180 * self.scale)
                button_spacing = int(20 * self.scale)
                
                # Title bar close button
                close_btn_size = int(20 * self.scale)
                close_btn_x = modal_x + modal_w - close_btn_size - int(5 * self.scale)
                close_btn_y = modal_y + int(5 * self.scale)
                close_btn_rect = pygame.Rect(close_btn_x, close_btn_y, close_btn_size, close_btn_size)
                if close_btn_rect.collidepoint(mouse_x, mouse_y):
                    self.hovered_button = ("tape", "title_close")
                    return
                
                # LOAD DATA button
                load_btn_x = modal_x + int(50 * self.scale)
                load_btn_rect = pygame.Rect(load_btn_x, button_y, button_w, button_h)
                if load_btn_rect.collidepoint(mouse_x, mouse_y):
                    self.hovered_button = ("tape", "load")
                    return
                
                # RECORD DATA button
                record_btn_x = load_btn_x + button_w + button_spacing
                record_btn_rect = pygame.Rect(record_btn_x, button_y, button_w, button_h)
                if record_btn_rect.collidepoint(mouse_x, mouse_y):
                    self.hovered_button = ("tape", "record")
                    return
            
            elif modal_name == "modem":
                # Check modem modal buttons
                button_size = int(60 * self.scale)
                button_spacing = int(10 * self.scale)
                gap = int(20 * self.scale)
                terminal_h = int(150 * self.scale)
                spacing = int(20 * self.scale)
                
                # Title bar close button
                close_btn_size = int(20 * self.scale)
                close_btn_x = modal_x + modal_w - close_btn_size - int(5 * self.scale)
                close_btn_y = modal_y + int(5 * self.scale)
                close_btn_rect = pygame.Rect(close_btn_x, close_btn_y, close_btn_size, close_btn_size)
                if close_btn_rect.collidepoint(mouse_x, mouse_y):
                    self.hovered_button = ("modem", "title_close")
                    return
                
                # Dial pad buttons
                if not self.modem_modal_connection_started:
                    dial_start_x = modal_x + gap
                    dial_start_y = modal_y + self.modal_title_bar_height + gap + terminal_h + spacing
                    dial_buttons = [["1", "2", "3"], ["4", "5", "6"], ["7", "8", "9"], ["*", "0", "#"]]
                    for row_idx, row in enumerate(dial_buttons):
                        for col_idx, button_label in enumerate(row):
                            btn_x = dial_start_x + col_idx * (button_size + button_spacing)
                            btn_y = dial_start_y + row_idx * (button_size + button_spacing)
                            btn_rect = pygame.Rect(btn_x, btn_y, button_size, button_size)
                            if btn_rect.collidepoint(mouse_x, mouse_y):
                                self.hovered_button = ("modem", f"dial_{button_label}")
                                return
                
                # CALL button
                if not self.modem_modal_connection_started:
                    call_btn_h = int(30 * self.scale)
                    dial_pad_h = 4 * button_size + 3 * button_spacing
                    call_btn_x = modal_x + gap
                    call_btn_y = modal_y + self.modal_title_bar_height + gap + terminal_h + spacing + dial_pad_h + spacing
                    call_btn_w = modal_w - 2 * gap
                    call_btn_rect = pygame.Rect(call_btn_x, call_btn_y, call_btn_w, call_btn_h)
                    if call_btn_rect.collidepoint(mouse_x, mouse_y):
                        self.hovered_button = ("modem", "call")
                        return
    
    def _draw_icon_label(self, icon_x: int, icon_y: int, icon_w: int, icon_h: int, label_text: str):
        """Draw a label below an icon with fade animation."""
        icon_id = None
        for icon in self.icons:
            if icon["x"] == icon_x and icon["y"] == icon_y:
                icon_id = id(icon)
                break
        
        if icon_id is None or icon_id not in self.icon_label_alpha:
            return
        
        alpha = int(self.icon_label_alpha[icon_id])
        if alpha <= 0:
            return
        
        try:
            font_size = max(int(12 * self.scale), 10)
            label_font = pygame.font.Font(None, font_size)
            
            # Create text surface with alpha
            text_surface = label_font.render(label_text, True, COLOR_CYAN)
            text_surface.set_alpha(alpha)
            
            # Position label below icon
            label_x = icon_x + (icon_w - text_surface.get_width()) // 2
            label_y = icon_y + icon_h + int(5 * self.scale)
            
            # Draw semi-transparent background for readability
            bg_rect = pygame.Rect(
                label_x - int(4 * self.scale),
                label_y - int(2 * self.scale),
                text_surface.get_width() + int(8 * self.scale),
                text_surface.get_height() + int(4 * self.scale)
            )
            bg_surface = pygame.Surface((bg_rect.width, bg_rect.height))
            bg_surface.set_alpha(alpha // 2)
            bg_surface.fill(COLOR_BLACK)
            self.screen.blit(bg_surface, bg_rect)
            
            # Draw text
            self.screen.blit(text_surface, (label_x, label_y))
        except Exception:
            pass

