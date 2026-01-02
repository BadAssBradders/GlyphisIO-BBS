import math
import pygame
import os
import sys
import random
from typing import Callable, Optional

try:
    from utils import get_data_path
except Exception:
    # Fallback for standalone import during development
    def get_data_path(*path_parts):
        # This file is now in Data/Outside_BBSs/PaperCraneBBS/
        # Data folder is 3 levels up
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        return os.path.join(base, *path_parts)


PINK = (255, 105, 180)  # Hot Pink
PINK_GLOW = (255, 182, 193, 100)  # Light Pink with alpha
PINK_DIM = (100, 20, 60)
BG = (15, 5, 12)  # Dark pink-black
TEXT = (255, 220, 240)
ERROR = (255, 50, 100)
ACCENT = (0, 255, 240)  # Cyan accent for contrast
GOLD = (255, 215, 0)


class PaperCraneBBS:
    """
    Lightweight outside-BBS experience for the PAPER CRANE dial-in.
    States: splash -> login -> menu -> panel. Esc/End Call exits.
    """

    def __init__(self, width: int, height: int, scale: float, on_exit: Optional[Callable[[], None]] = None):
        self.width = width
        self.height = height
        self.scale = scale
        self.on_exit = on_exit

        # Fonts
        self.font_title = self._load_font("misaki_gothic.ttf", int(32 * self.scale), bold=False)
        self.font_label = self._load_font("misaki_gothic.ttf", int(22 * self.scale), bold=False)
        self.font_body = self._load_font("misaki_gothic.ttf", int(22 * self.scale), bold=False)
        self.font_small = self._load_font("misaki_gothic.ttf", int(17 * self.scale), bold=False)
        self.font_title_fallback = self.font_title
        self.font_label_fallback = self.font_label
        self.font_body_fallback = self.font_body
        self.font_small_fallback = self.font_small

        # Assets
        self.splash_image = self._load_splash_image()
        self.splash_rows = 15
        self.splash_row_time = 2.0  # seconds per row
        self.splash_rows_shown = 0
        self.splash_row_timer = 0.0

        # State
        self.state = "splash"
        self.username = ""
        self.password = ""
        self.focus = "username"  # username | password
        self.error_message = ""
        self.menu_options = ["SYSOP", "AUDIO", "ARCHIVE", "LOGS", "END CALL"]
        self.menu_index = 0
        self.active_panel: Optional[str] = None
        self.cursor_timer = 0.0
        self.cursor_visible = True
        self.request_exit = False
        self.archive_docs = self._build_archive_docs()
        self.archive_selected_index = 0
        self.archive_open_index: Optional[int] = None
        self.archive_scroll = 0
        self.panel_scroll = 0
        self.grid_scroll_y = 0.0
        self.scanline_surf = self._create_scanline_surface()
        self.menu_glow_timer = 0.0
        self.user_logs = [
            "SYSTEM: [handshake ok]",
            "SYSTEM: [encrypted channel open]",
            "SYSTEM: [routing via node-07]",
            "SYSTEM: [ping 142ms]",
            "SYSTEM: [background scan clean]"
        ]
        self.logs_selected_index = 0
        self.logs_wiping = False
        self.logs_wipe_timer = 0.0
        self.audio_tracks = self._load_audio_tracks()
        self.audio_selected_index = 0
        self.current_playing_track: Optional[int] = None
        self.showing_lyrics = False
        self.lyrics_scroll = 0
        self.audio_welcome_scroll = 0
        self.track_list_scroll = 0
        self.archive_list_scroll = 0
        self.audio_message = "WELCOME TO THE MIAZUKI AUDIO MATRIX. MiaZuki's rebellious spirit remains a beacon in the static. She has donated these tracks so that we, the guests of Paper Crane, may have something to steel our hearts while we sift through the fragments of our destroyed culture. Listen. Remember. Rebel."

    def _create_scanline_surface(self) -> pygame.Surface:
        surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        for y in range(0, self.height, 4):
            pygame.draw.line(surf, (0, 0, 0, 40), (0, y), (self.width, y))
        return surf

    def _load_font(self, filename: str, size: int, bold: bool = False) -> pygame.font.Font:
        try:
            # Try local directory first (where this script is)
            local_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
            if os.path.exists(local_path):
                font = pygame.font.Font(local_path, max(1, size))
            else:
                # Fallback to general data path
                font = pygame.font.Font(get_data_path(filename), max(1, size))
            
            if bold and hasattr(font, "set_bold"):
                font.set_bold(True)
            return font
        except Exception:
            return pygame.font.Font(None, max(1, size))

    def _load_sys_font(self, name: str, size: int, bold: bool = False) -> pygame.font.Font:
        try:
            font = pygame.font.SysFont(name, max(1, size), bold=bold)
            return font or pygame.font.Font(None, max(1, size))
        except Exception:
            return pygame.font.Font(None, max(1, size))

    def _has_non_ascii(self, text: str) -> bool:
        return any(ord(ch) > 127 for ch in text)

    def _get_font(self, primary: pygame.font.Font, fallback: pygame.font.Font, text: str) -> pygame.font.Font:
        return fallback if self._has_non_ascii(text) else primary

    def _render_text(self, primary: pygame.font.Font, fallback: pygame.font.Font, text: str, color) -> pygame.Surface:
        text = text.upper()
        font = self._get_font(primary, fallback, text)
        return font.render(text, True, color)

    def _draw_shadowed_rect(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        *,
        color,
        shadow_color=(20, 20, 20),
        shadow_offset: Optional[int] = None,
        border: int = 2,
        fill_color: Optional[tuple[int, int, int]] = None,
        radius: int = 2,
    ) -> None:
        """Draw a simple drop-shadowed rectangle."""

        offset = shadow_offset if shadow_offset is not None else int(4 * self.scale)
        shadow_rect = rect.move(offset, offset)
        pygame.draw.rect(surface, shadow_color, shadow_rect, 0, border_radius=radius)
        if fill_color is not None:
            pygame.draw.rect(surface, fill_color, rect, 0, border_radius=radius)
        pygame.draw.rect(surface, color, rect, border, border_radius=radius)

    def _blit_text_with_shadow(
        self,
        surface: pygame.Surface,
        primary: pygame.font.Font,
        fallback: pygame.font.Font,
        text: str,
        color,
        pos,
        shadow_offset=(2, 2),
        shadow_color=(0, 0, 0),
    ) -> None:
        text = text.upper()
        font = self._get_font(primary, fallback, text)
        shadow = font.render(text, True, shadow_color)
        surface.blit(shadow, (pos[0] + shadow_offset[0], pos[1] + shadow_offset[1]))
        actual = font.render(text, True, color)
        surface.blit(actual, pos)

    def _wrap_text_lines(
        self,
        lines: list[str],
        primary: pygame.font.Font,
        fallback: pygame.font.Font,
        max_width: int,
    ) -> list[str]:
        wrapped: list[str] = []
        for line in lines:
            line = line.upper()
            # Preserve intentional blank lines
            if not line.strip():
                wrapped.append("")
                continue
            words = line.split(" ")
            current = ""
            for word in words:
                trial = word if not current else f"{current} {word}"
                font = self._get_font(primary, fallback, trial)
                if font.size(trial)[0] <= max_width:
                    current = trial
                else:
                    if current:
                        wrapped.append(current)
                    current = word
            if current:
                wrapped.append(current)
        return wrapped

    def _split_lines(self, text: str) -> list[str]:
        return text.strip("\n").splitlines()

    def _load_audio_tracks(self):
        """
        Load audio tracks from the local MiaZukiMatrix folder ONLY.
        If a matching .txt file exists, it's loaded as lyrics.
        """
        tracks = []
        
        # EXCLUSIVE FOLDER for MiaZuki Matrix
        audio_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "MiaZukiMatrix")
        
        if not os.path.isdir(audio_folder):
            # Fallback if folder not found
            return [
                {"title": "TellMeHowWeMeetYa", "file": "TellMeHowWeMeetYa"},
                {"title": "Pink Blushes on the A-Train", "file": "Pink_Blushes_on_the_A_Train"},
                {"title": "Death Certain", "file": "Death_Certain"}
            ]
            
        try:
            # Scan for .wav and .mp3 files ONLY in this folder
            files = sorted([f for f in os.listdir(audio_folder) if f.lower().endswith(('.wav', '.mp3'))])
        except Exception:
            files = []
            
        for filename in files:
            base_name = os.path.splitext(filename)[0]
            # Clean up title: remove numeric prefix (e.g. 01_Song or 1_Song) and underscores
            display_title = base_name
            if "_" in display_title:
                parts = display_title.split("_", 1)
                if parts[0].isdigit():
                    display_title = parts[1]
            display_title = display_title.replace("_", " ")
            
            track_data = {
                "title": display_title,
                "file": base_name, # Pass base name to _play_track which handles extensions
                "filename": filename
            }
            
            # Look for matching .txt file for lyrics in the SAME folder
            lyrics_path = os.path.join(audio_folder, base_name + ".txt")
            if os.path.exists(lyrics_path):
                try:
                    with open(lyrics_path, 'r', encoding='utf-8') as f:
                        track_data["lyrics"] = [line.strip() for line in f.readlines()]
                except Exception:
                    pass
                    
            tracks.append(track_data)
            
        if not tracks:
            # Final fallback if folder exists but is empty
            return [
                {"title": "TellMeHowWeMeetYa", "file": "TellMeHowWeMeetYa"},
                {"title": "Pink Blushes on the A-Train", "file": "Pink_Blushes_on_the_A_Train"},
                {"title": "Death Certain", "file": "Death_Certain"}
            ]
            
        return tracks

    def _build_archive_docs(self):
        """
        Load archive documents from external .txt files in the paper_crane_docs folder.
        
        Each file should have the format:
        TITLE: Document Title
        
        [Document content...]
        
        Files are sorted alphabetically, so prefix with numbers (01_, 02_, etc.) for ordering.
        """
        docs = []
        
        # Try multiple possible locations for the docs folder
        possible_paths = [
            get_data_path("paper_crane_docs"),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "paper_crane_docs"),
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "paper_crane_docs"),
        ]
        
        docs_folder = None
        for path in possible_paths:
            if os.path.isdir(path):
                docs_folder = path
                break
        
        if docs_folder is None:
            # Return fallback document if folder not found
            return [{
                "title": "ARCHIVE OFFLINE",
                "lines": [
                    "ERROR: Document archive not found.",
                    "",
                    "The Paper Crane archive requires",
                    "the paper_crane_docs folder to be",
                    "present in the game directory.",
                    "",
                    "Please verify installation.",
                    "",
                    "- SYSTEM"
                ]
            }]
        
        # Scan for .txt files
        try:
            files = sorted([f for f in os.listdir(docs_folder) if f.endswith('.txt')])
        except Exception:
            files = []
        
        for filename in files:
            filepath = os.path.join(docs_folder, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Parse the file - first line should be TITLE: xxx
                lines = content.split('\n')
                title = "Untitled Document"
                content_start = 0
                
                for i, line in enumerate(lines):
                    if line.strip().upper().startswith("TITLE:"):
                        title = line.split(":", 1)[1].strip()
                        content_start = i + 1
                        break
                
                # Skip empty lines after title
                while content_start < len(lines) and not lines[content_start].strip():
                    content_start += 1
                
                # Get the rest as content
                doc_lines = lines[content_start:]
                
                docs.append({
                    "title": title,
                    "lines": doc_lines,
                    "filename": filename
                })
                
            except Exception as e:
                # If a file fails to load, add error entry
                docs.append({
                    "title": f"ERROR: {filename}",
                    "lines": [f"Failed to load document: {str(e)}"],
                    "filename": filename
                })
        
        # If no documents found, return helpful message
        if not docs:
            return [{
                "title": "ARCHIVE EMPTY",
                "lines": [
                    "No documents found in archive.",
                    "",
                    "Add .txt files to the",
                    "paper_crane_docs folder.",
                    "",
                    "Format:",
                    "TITLE: Document Name",
                    "",
                    "[Document content here]",
                    "",
                    "- SYSTEM"
                ]
            }]
        
        return docs

    def _load_splash_image(self) -> Optional[pygame.Surface]:
        try:
            img_path = get_data_path("images", "BBS_PAPERCRANE.png")
            image = pygame.image.load(img_path).convert_alpha()
            img_w, img_h = image.get_size()
            max_w = int(self.width * 0.82)
            max_h = int(self.height * 0.82)
            scale = min(max_w / img_w, max_h / img_h, 1.0)
            if scale < 1.0:
                image = pygame.transform.smoothscale(image, (int(img_w * scale), int(img_h * scale)))
            return image
        except Exception:
            return None

    def _log_action(self, action: str):
        self.user_logs.append(f"TRACE: [{action}]")
        # Keep logs manageable
        if len(self.user_logs) > 50:
            self.user_logs.pop(5) # Keep original system handshakes

    def update(self, dt: float) -> None:
        self.cursor_timer += dt
        if self.cursor_timer >= 0.5:
            self.cursor_timer = 0.0
            self.cursor_visible = not self.cursor_visible

        # Only animate grid and title glow when music is playing
        if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
            self.grid_scroll_y = (self.grid_scroll_y + dt * 20.0) % 64.0
            self.menu_glow_timer += dt

        if self.logs_wiping:
            self.logs_wipe_timer += dt
            if self.logs_wipe_timer >= 0.1: # Rapid line deletion
                self.logs_wipe_timer = 0
                if len(self.user_logs) > 5:
                    self.user_logs.pop()
                else:
                    self.logs_wiping = False
                    self.user_logs.append("TRACE: [all records purged]")
                    self.user_logs.append("TRACE: [ghost protocol active]")

        if self.state == "splash" and self.splash_image and self.splash_rows_shown < self.splash_rows:
            self.splash_row_timer += dt
            while self.splash_row_timer >= self.splash_row_time and self.splash_rows_shown < self.splash_rows:
                self.splash_row_timer -= self.splash_row_time
                self.splash_rows_shown += 1

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type != pygame.KEYDOWN:
            return False

        if self.state == "splash":
            if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                self.state = "login"
                self.splash_rows_shown = self.splash_rows
                return True
            if event.key == pygame.K_ESCAPE:
                self._end_call()
                return True
            return False

        if self.state == "login":
            if event.key == pygame.K_TAB:
                self.focus = "password" if self.focus == "username" else "username"
                return True
            if event.key == pygame.K_ESCAPE:
                self._end_call()
                return True
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._attempt_login()
                return True
            if event.key == pygame.K_BACKSPACE:
                if self.focus == "username":
                    self.username = self.username[:-1]
                else:
                    self.password = self.password[:-1]
                return True
            char = event.unicode
            if char and char.isprintable() and len(char) == 1:
                if self.focus == "username" and len(self.username) < 20:
                    self.username += char
                elif self.focus == "password" and len(self.password) < 20:
                    self.password += char
                return True
            return False

        if self.state == "menu":
            if event.key in (pygame.K_UP, pygame.K_w):
                self.menu_index = (self.menu_index - 1) % len(self.menu_options)
                return True
            if event.key in (pygame.K_DOWN, pygame.K_s):
                self.menu_index = (self.menu_index + 1) % len(self.menu_options)
                return True
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                selection = self.menu_options[self.menu_index]
                if selection == "END CALL":
                    self._end_call()
                else:
                    self.active_panel = selection
                    self.panel_scroll = 0 # Reset scroll when opening a panel
                    self._log_action(f"access {selection}")
                    if selection == "ARCHIVE":
                        self.archive_selected_index = 0
                        self.archive_open_index = None
                        self.archive_scroll = 0
                    elif selection == "AUDIO":
                        self.audio_selected_index = 0
                    self.state = "panel"
                return True
            if event.key == pygame.K_ESCAPE:
                self._end_call()
                return True
            return False

        if self.state == "panel":
            if self.active_panel == "ARCHIVE":
                if self._handle_archive_event(event):
                    return True
            if self.active_panel == "AUDIO":
                if self._handle_audio_event(event):
                    return True
            if self.active_panel == "LOGS":
                if self._handle_logs_event(event):
                    return True
            
            # General Panel Scrolling
            if event.key in (pygame.K_UP, pygame.K_w):
                self.panel_scroll = max(0, self.panel_scroll - 1)
                return True
            if event.key in (pygame.K_DOWN, pygame.K_s):
                self.panel_scroll += 1
                return True

            if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                self.state = "menu"
                self.active_panel = None
                return True
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                # Return to menu on enter for simple navigation
                self.state = "menu"
                self.active_panel = None
                return True
            return False

        return False

    def _handle_archive_event(self, event: pygame.event.Event) -> bool:
        # Document list navigation
        if self.archive_open_index is None:
            if event.key in (pygame.K_UP, pygame.K_w):
                self.archive_selected_index = (self.archive_selected_index - 1) % len(self.archive_docs)
                
                # Auto-scroll archive list
                line_h = int(50 * self.scale)
                _, left_rect, _ = self._archive_geometry()
                visible_docs = (left_rect.height - int(32 * self.scale)) // line_h
                if self.archive_selected_index < self.archive_list_scroll:
                    self.archive_list_scroll = self.archive_selected_index
                elif self.archive_selected_index >= self.archive_list_scroll + visible_docs:
                    self.archive_list_scroll = self.archive_selected_index - visible_docs + 1
                return True

            if event.key in (pygame.K_DOWN, pygame.K_s):
                self.archive_selected_index = (self.archive_selected_index + 1) % len(self.archive_docs)
                
                # Auto-scroll archive list
                line_h = int(50 * self.scale)
                _, left_rect, _ = self._archive_geometry()
                visible_docs = (left_rect.height - int(32 * self.scale)) // line_h
                if self.archive_selected_index < self.archive_list_scroll:
                    self.archive_list_scroll = self.archive_selected_index
                elif self.archive_selected_index >= self.archive_list_scroll + visible_docs:
                    self.archive_list_scroll = self.archive_selected_index - visible_docs + 1
                return True
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.archive_open_index = self.archive_selected_index
                self.archive_scroll = 0
                self._clamp_archive_scroll()
                doc_title = self.archive_docs[self.archive_selected_index]['title']
                self._log_action(f"view archive: {doc_title}")
                return True
            if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                self.state = "menu"
                self.active_panel = None
                return True
            return False

        # Open document navigation
        if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE, pygame.K_RETURN, pygame.K_KP_ENTER):
            # Close document back to list
            self.archive_open_index = None
            self.archive_scroll = 0
            return True
        if event.key in (pygame.K_UP, pygame.K_w):
            self.archive_scroll -= 1
            self._clamp_archive_scroll()
            return True
        if event.key in (pygame.K_DOWN, pygame.K_s):
            self.archive_scroll += 1
            self._clamp_archive_scroll()
            return True
        if event.key == pygame.K_PAGEUP:
            self.archive_scroll -= 5
            self._clamp_archive_scroll()
            return True
        if event.key == pygame.K_PAGEDOWN:
            self.archive_scroll += 5
            self._clamp_archive_scroll()
            return True
        return False

    def _handle_audio_event(self, event: pygame.event.Event) -> bool:
        if self.showing_lyrics:
            if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE, pygame.K_l):
                self.showing_lyrics = False
                return True
            if event.key in (pygame.K_UP, pygame.K_w):
                self.lyrics_scroll = max(0, self.lyrics_scroll - 1)
                return True
            if event.key in (pygame.K_DOWN, pygame.K_s):
                self.lyrics_scroll += 1
                return True
            return False

        if event.key in (pygame.K_UP, pygame.K_w):
            self.audio_selected_index = (self.audio_selected_index - 1) % len(self.audio_tracks)
            self.audio_welcome_scroll = max(0, self.audio_welcome_scroll - 1)
            
            # Auto-scroll track list
            track_h = int(50 * self.scale)
            panel_rect_h = int(self.height * 0.7)
            list_rect_h = panel_rect_h - int(100 * self.scale)
            visible_tracks = list_rect_h // track_h
            if self.audio_selected_index < self.track_list_scroll:
                self.track_list_scroll = self.audio_selected_index
            elif self.audio_selected_index >= self.track_list_scroll + visible_tracks:
                self.track_list_scroll = self.audio_selected_index - visible_tracks + 1
            return True

        if event.key in (pygame.K_DOWN, pygame.K_s):
            self.audio_selected_index = (self.audio_selected_index + 1) % len(self.audio_tracks)
            self.audio_welcome_scroll += 1
            
            # Auto-scroll track list
            track_h = int(50 * self.scale)
            panel_rect_h = int(self.height * 0.7)
            list_rect_h = panel_rect_h - int(100 * self.scale)
            visible_tracks = list_rect_h // track_h
            if self.audio_selected_index < self.track_list_scroll:
                self.track_list_scroll = self.audio_selected_index
            elif self.audio_selected_index >= self.track_list_scroll + visible_tracks:
                self.track_list_scroll = self.audio_selected_index - visible_tracks + 1
            return True
        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            print(f"[DEBUG] Audio Matrix: Enter pressed. Attempting to play track {self.audio_selected_index}: {self.audio_tracks[self.audio_selected_index]['title']}")
            self._play_track(self.audio_selected_index)
            track_title = self.audio_tracks[self.audio_selected_index]['title']
            self._log_action(f"playback audio: {track_title}")
            return True
        if event.key == pygame.K_l:
            track = self.audio_tracks[self.audio_selected_index]
            if "lyrics" in track:
                self.showing_lyrics = True
                self.lyrics_scroll = 0
                return True
        if event.key == pygame.K_SPACE:
            print(f"[DEBUG] Audio Matrix: Space pressed. Stopping music.")
            # Stop music
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.stop()
                self.current_playing_track = None
            return True
        return False

    def _handle_logs_event(self, event: pygame.event.Event) -> bool:
        if self.logs_wiping:
            return True # Lock input during wipe

        if event.key in (pygame.K_UP, pygame.K_w):
            self.panel_scroll = max(0, self.panel_scroll - 1)
            return True
        if event.key in (pygame.K_DOWN, pygame.K_s):
            self.panel_scroll += 1
            return True
        
        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            # Only one action in logs: WIPE
            self.logs_wiping = True
            self.logs_wipe_timer = 0
            return True
            
        return False

    def _draw_logs_panel(self, surface: pygame.Surface) -> None:
        panel_rect = pygame.Rect(
            int(self.width * 0.45),
            int(160 * self.scale),
            int(self.width * 0.50),
            int(self.height * 0.55),
        )
        
        self._draw_shadowed_rect(
            surface,
            panel_rect,
            color=ERROR if self.logs_wiping else PINK,
            shadow_color=(0, 0, 0),
            fill_color=(10, 5, 8),
            border=2,
            radius=4
        )
        
        header = "CONNECTION LOGS // TRACE DATA"
        self._blit_text_with_shadow(
            surface,
            self.font_label,
            self.font_label_fallback,
            f"// {header}",
            ACCENT,
            (panel_rect.x + int(20 * self.scale), panel_rect.y + int(15 * self.scale)),
        )
        
        pygame.draw.line(surface, PINK_DIM, (panel_rect.x + int(20 * self.scale), panel_rect.y + int(45 * self.scale)), (panel_rect.right - int(20 * self.scale), panel_rect.y + int(45 * self.scale)), 1)

        text_x = panel_rect.x + int(20 * self.scale)
        text_y = panel_rect.y + int(60 * self.scale)
        line_height = int(24 * self.scale)
        visible_lines = (panel_rect.height - int(120 * self.scale)) // line_height
        
        # Draw the logs
        display_logs = self.user_logs
        max_scroll = max(0, len(display_logs) - visible_lines)
        self.panel_scroll = max(0, min(self.panel_scroll, max_scroll))
        
        start = self.panel_scroll
        end = start + visible_lines
        
        for idx, line in enumerate(display_logs[start:end]):
            color = ERROR if "purged" in line or "ghost" in line else (GOLD if "SYSTEM" in line else TEXT)
            self._blit_text_with_shadow(
                surface,
                self.font_small,
                self.font_small_fallback,
                line,
                color,
                (text_x, text_y + idx * line_height),
            )

        # WIPE TRACE BUTTON
        wipe_btn_rect = pygame.Rect(panel_rect.x + int(20 * self.scale), panel_rect.bottom - int(75 * self.scale), panel_rect.width - int(40 * self.scale), int(35 * self.scale))
        btn_color = ERROR if (int(pygame.time.get_ticks() / 500) % 2 == 0) else PINK_DIM
        if self.logs_wiping: btn_color = ERROR
        
        pygame.draw.rect(surface, (20, 5, 8), wipe_btn_rect, 0, border_radius=4)
        pygame.draw.rect(surface, btn_color, wipe_btn_rect, 1, border_radius=4)
        
        wipe_text = ">>> [PURGE ALL TRACE DATA] <<<" if not self.logs_wiping else "DELETING RECORDS..."
        w_surf = self.font_small.render(wipe_text.upper(), True, ERROR if self.logs_wiping else PINK)
        surface.blit(w_surf, (wipe_btn_rect.centerx - w_surf.get_width() // 2, wipe_btn_rect.centery - w_surf.get_height() // 2))

        # Unified Scroll Indicator
        self._draw_scroll_indicator(surface, panel_rect, self.panel_scroll, visible_lines, len(display_logs))

        # Footer
        footer_rect = pygame.Rect(panel_rect.x, panel_rect.bottom - int(25 * self.scale), panel_rect.width, int(25 * self.scale))
        pygame.draw.rect(surface, PINK_DIM, footer_rect, 0, border_bottom_left_radius=4, border_bottom_right_radius=4)
        
        prompt_text = "ENTER: PURGE | [UP/DOWN] SCROLL | ESC: MENU"
        self._blit_text_with_shadow(
            surface,
            self.font_small,
            self.font_small_fallback,
            prompt_text,
            TEXT,
            (panel_rect.x + int(15 * self.scale), panel_rect.bottom - int(20 * self.scale)),
        )

    def _play_track(self, index: int) -> None:
        track = self.audio_tracks[index]
        base_filename = track["file"]
        print(f"[DEBUG] _play_track: index={index}, base_filename={base_filename}")
        
        try:
            if not pygame.mixer.get_init():
                print(f"[DEBUG] _play_track: Initializing mixer.")
                # Initialize with standard frequency and buffer for better compatibility
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            
            # EXCLUSIVE search in local MiaZukiMatrix folder
            audio_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "MiaZukiMatrix")
            
            print(f"[DEBUG] _play_track: Searching exclusively in: {audio_dir}")
            
            audio_path = None
            # Try .wav first (preferred for reliability), then .mp3
            for ext in [".wav", ".mp3"]:
                p = os.path.join(audio_dir, base_filename + ext)
                if os.path.exists(p):
                    audio_path = p
                    break
            
            if audio_path:
                print(f"[DEBUG] _play_track: Found file at {audio_path}. Loading into mixer.music.")
                # Same method as Pirate Radio
                pygame.mixer.music.stop() 
                pygame.mixer.music.load(audio_path)
                pygame.mixer.music.set_volume(0.8) # 80% volume
                pygame.mixer.music.play(-1) # Loop indefinitely
                
                self.current_playing_track = index
                print(f"[DEBUG] _play_track: Playback started successfully.")
            else:
                print(f"[DEBUG] _play_track ERROR: Audio file not found: {base_filename} in MiaZukiMatrix.")
                # Still set as playing for UI feedback in dev if it was a fallback
                self.current_playing_track = index
        except Exception as e:
            print(f"[DEBUG] _play_track EXCEPTION: Failed to play audio '{base_filename}': {e}")
            import traceback
            traceback.print_exc()

    def _clamp_archive_scroll(self) -> None:
        if self.archive_open_index is None:
            self.archive_scroll = 0
            return
        _, _, right_rect = self._archive_geometry()
        padding = int(20 * self.scale)
        available_width = right_rect.width - padding * 2 # Match _draw_archive_panel
        lines = self._wrap_text_lines(
            self.archive_docs[self.archive_open_index]["lines"],
            self.font_small,
            self.font_small_fallback,
            available_width,
        )
        line_h = int(24 * self.scale)
        visible_height = right_rect.height - int(100 * self.scale) # Match _draw_archive_panel
        visible_lines = max(1, visible_height // line_h)
        max_scroll = max(0, len(lines) - visible_lines)
        self.archive_scroll = max(0, min(self.archive_scroll, max_scroll))

    def _draw_scroll_indicator(self, surface: pygame.Surface, rect: pygame.Rect, start_line: int, visible_lines: int, total_lines: int) -> None:
        """Draws the signature GOLD scroll bar indicator."""
        if total_lines <= visible_lines:
            return

        # Calculate bar geometry
        max_scroll = total_lines - visible_lines
        scroll_pct = start_line / max_scroll
        
        bar_w = int(4 * self.scale)
        bar_h = int(30 * self.scale) # Fixed height handle or proportional? 
        # User said "yellow line", so a fixed height handle or a thin strip.
        # Let's use a nice tactile handle.
        
        track_h = rect.height - int(20 * self.scale)
        available_track = track_h - bar_h
        
        bar_x = rect.right - bar_w - int(4 * self.scale)
        bar_y = rect.y + int(10 * self.scale) + int(scroll_pct * available_track)
        
        # Draw the handle
        pygame.draw.rect(surface, GOLD, (bar_x, bar_y, bar_w, bar_h), 0, border_radius=2)
        
        # Optional: draw a very faint track line
        pygame.draw.line(surface, (GOLD[0], GOLD[1], GOLD[2], 40), 
                         (bar_x + bar_w//2, rect.y + int(10 * self.scale)), 
                         (bar_x + bar_w//2, rect.y + rect.height - int(10 * self.scale)), 1)

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(BG)
        self._draw_grid(surface)

        if self.state == "splash":
            self._draw_splash(surface)
        elif self.state == "login":
            self._draw_login(surface)
        elif self.state in ("menu", "panel"):
            self._draw_menu(surface)
            if self.state == "panel":
                self._draw_panel(surface)

        # Apply scanline overlay
        surface.blit(self.scanline_surf, (0, 0))

    def _draw_grid(self, surface: pygame.Surface) -> None:
        step = max(24, int(48 * self.scale))
        scroll_y = int(self.grid_scroll_y)
        scroll_x = int(self.grid_scroll_y * 0.5)

        # 1. Foundation Fill
        surface.fill(BG)

        # 2. Square Texture (Floor effect)
        # Draw this first so it's behind the lines
        for x in range(-step, self.width + step, step * 2):
            for y in range(-step, self.height + step, step * 2):
                draw_x = x + (scroll_x % (step * 2))
                draw_y = y + (scroll_y % (step * 2))
                rect = pygame.Rect(draw_x, draw_y, step, step)
                # Slightly brighter than base BG to create the checkerboard
                pygame.draw.rect(surface, (BG[0] + 8, BG[1] + 3, BG[2] + 6), rect, 0)

        # 3. Bottom Glow
        glow_rect = pygame.Rect(0, self.height - int(120 * self.scale), self.width, int(120 * self.scale))
        glow_surf = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
        for i in range(glow_rect.height):
            a = int((i / glow_rect.height) * 100)
            pygame.draw.line(glow_surf, (PINK[0], PINK[1], PINK[2], a), (0, i), (self.width, i))
        surface.blit(glow_surf, glow_rect.topleft)

        # 4. Grid Lines (The prominent part)
        # We draw these after squares/glow so they are clearly visible
        pulse = int(math.sin(self.menu_glow_timer * 2) * 15 + 75)
        grid_color = (pulse, pulse // 4, pulse // 2)
        line_width = max(1, int(2 * self.scale)) # Use 2px for better visibility

        # Vertical lines
        for x in range(-step, self.width + step, step):
            draw_x = x + (scroll_x % step)
            pygame.draw.line(surface, grid_color, (draw_x, 0), (draw_x, self.height), line_width)

        # Horizontal lines
        for y in range(-step, self.height + step, step):
            draw_y = y + (scroll_y % step)
            pygame.draw.line(surface, grid_color, (0, draw_y), (self.width, draw_y), line_width)

        # 5. Master Outer Border (NO SHADOW - shadow was covering the screen)
        border_rect = surface.get_rect()
        pygame.draw.rect(surface, PINK, border_rect.inflate(-2, -2), 3)

    def _draw_splash(self, surface: pygame.Surface) -> None:
        if self.splash_image:
            rect = self.splash_image.get_rect(center=surface.get_rect().center)
            if self.splash_rows_shown > 0:
                img_w, img_h = self.splash_image.get_size()
                row_h = max(1, math.ceil(img_h / self.splash_rows))
                for row in range(self.splash_rows_shown):
                    src_y = row * row_h
                    if src_y >= img_h:
                        break
                    src_h = min(row_h, img_h - src_y)
                    dest_rect = pygame.Rect(rect.x, rect.y + src_y, img_w, src_h)
                    surface.blit(self.splash_image, dest_rect, pygame.Rect(0, src_y, img_w, src_h))
        show_prompt = self.splash_image is not None and self.splash_rows_shown >= self.splash_rows
        if show_prompt:
            prompt = "SPACE TO LOG IN"
            text = self._render_text(self.font_label, self.font_label_fallback, prompt, TEXT)
            x = self.width // 2 - text.get_width() // 2
            y = int(self.height * 0.82)
            self._blit_text_with_shadow(
                surface,
                self.font_label,
                self.font_label_fallback,
                prompt,
                TEXT,
                (x, y),
            )
            
            # Add quote below the prompt
            quote = "Fall seven times, stand up eight."
            quote_text = self._render_text(self.font_small, self.font_small_fallback, quote, PINK)
            qx = self.width // 2 - quote_text.get_width() // 2
            qy = y + int(35 * self.scale)
            self._blit_text_with_shadow(
                surface,
                self.font_small,
                self.font_small_fallback,
                quote,
                PINK,
                (qx, qy),
            )

    def _draw_login(self, surface: pygame.Surface) -> None:
        padding = int(32 * self.scale)
        top = padding * 2
        title_text = "PAPER CRANE BBS // SECURE DIAL-IN"
        title = self._render_text(self.font_label, self.font_label_fallback, title_text, PINK)
        self._blit_text_with_shadow(
            surface,
            self.font_label,
            self.font_label_fallback,
            title_text,
            PINK,
            (self.width // 2 - title.get_width() // 2, top),
        )

        # Login box backdrop
        box_w = int(self.width * 0.7)
        box_h = int(60 * self.scale)
        start_y = int(self.height * 0.35)
        
        backdrop_rect = pygame.Rect(self.width // 2 - box_w // 2 - padding, start_y - padding * 2, box_w + padding * 2, box_h * 3 + padding * 2)
        self._draw_shadowed_rect(surface, backdrop_rect, color=PINK_DIM, shadow_color=(0,0,0), fill_color=(10, 5, 8), border=1, radius=8)

        self._draw_input_box(
            surface,
            label="ID / USERNAME",
            value=self.username,
            x=self.width // 2 - box_w // 2,
            y=start_y + int(20 * self.scale),
            w=box_w,
            h=box_h,
            focused=self.focus == "username",
            mask=False,
        )
        self._draw_input_box(
            surface,
            label="ACCESS CODE / PASSWORD",
            value=self.password,
            x=self.width // 2 - box_w // 2,
            y=start_y + box_h + padding + int(20 * self.scale),
            w=box_w,
            h=box_h,
            focused=self.focus == "password",
            mask=True,
        )

        hint_text = "ENTER [SUBMIT]  -  TAB [SWITCH]  -  ESC [EXIT]"
        hint = self._render_text(self.font_small, self.font_small_fallback, hint_text, TEXT)
        self._blit_text_with_shadow(
            surface,
            self.font_small,
            self.font_small_fallback,
            hint_text,
            TEXT,
            (self.width // 2 - hint.get_width() // 2, start_y + box_h * 2 + padding * 2),
        )

        if self.error_message:
            available_width = int(self.width * 0.8)
            wrapped_err = self._wrap_text_lines([self.error_message], self.font_body, self.font_body_fallback, available_width)
            
            y = start_y - int(48 * self.scale)
            for line in wrapped_err:
                err_surf = self._render_text(self.font_body, self.font_body_fallback, line, ERROR)
                self._blit_text_with_shadow(
                    surface,
                    self.font_body,
                    self.font_body_fallback,
                    line,
                    ERROR,
                    (self.width // 2 - err_surf.get_width() // 2, y),
                )
                y += int(25 * self.scale)

    def _draw_input_box(self, surface, label, value, x, y, w, h, focused=False, mask=False):
        label_text = f"// {label}"
        color = ACCENT if focused else PINK
        
        # Consistent font for labels and values
        surface.blit(self.font_small.render(label_text.upper(), True, color), (x, y - int(24 * self.scale)))

        rect = pygame.Rect(x, y, w, h)
        bg_color = (20, 10, 15) if focused else (10, 5, 8)
        self._draw_shadowed_rect(
            surface,
            rect,
            color=color,
            shadow_color=(0, 0, 0),
            fill_color=bg_color,
            border=2 if focused else 1,
            radius=4
        )

        display_value = ("*" * len(value)) if mask else value
        if focused and self.cursor_visible:
            display_value += "█"
        
        # Use simple render, no shadow, no font switching for cleaner look
        val_surf = self.font_body.render((display_value or " ").upper(), True, TEXT)
        surface.blit(val_surf, (x + int(16 * self.scale), y + h // 2 - val_surf.get_height() // 2))

    def _draw_menu(self, surface: pygame.Surface) -> None:
        title_text = "P A P E R   C R A N E"
        title = self._render_text(self.font_title, self.font_title_fallback, title_text, PINK)
        
        # Title Glow
        glow_size = int(math.sin(self.menu_glow_timer * 4) * 5 + 5)
        for offset in range(glow_size):
            alpha = int((1 - offset / glow_size) * 100)
            glow_color = (PINK[0], PINK[1], PINK[2], alpha)
            title_glow = self.font_title.render(title_text.upper(), True, glow_color)
            surface.blit(title_glow, (self.width // 2 - title.get_width() // 2 - offset, int(40 * self.scale) - offset))
            surface.blit(title_glow, (self.width // 2 - title.get_width() // 2 + offset, int(40 * self.scale) + offset))

        self._blit_text_with_shadow(
            surface,
            self.font_title,
            self.font_title_fallback,
            title_text,
            PINK,
            (self.width // 2 - title.get_width() // 2, int(40 * self.scale)),
        )

        menu_x = int(self.width * 0.15)
        menu_y = int(160 * self.scale)
        line_h = int(60 * self.scale)

        # Menu Container
        menu_back_rect = pygame.Rect(
            menu_x - int(20 * self.scale), 
            menu_y - int(30 * self.scale), 
            int(self.width * 0.32), 
            line_h * len(self.menu_options) + int(50 * self.scale)
        )
        self._draw_shadowed_rect(
            surface,
            menu_back_rect,
            color=PINK,
            shadow_color=(0, 0, 0),
            fill_color=(10, 5, 8),
            border=2,
            radius=4,
        )

        icons = {
            "SYSOP": "> ",
            "AUDIO": "* ",
            "ARCHIVE": "[ ",
            "LOGS": "# ",
            "END CALL": "X "
        }

        for idx, option in enumerate(self.menu_options):
            is_active = idx == self.menu_index and self.state == "menu"
            color = ACCENT if is_active else TEXT
            
            icon = icons.get(option, "  ")
            display_text = f"{icon}{option}"
            
            if is_active:
                # Active option glow/box
                selection_rect = pygame.Rect(
                    menu_x - int(10 * self.scale),
                    menu_y + idx * line_h - int(10 * self.scale),
                    int(self.width * 0.28),
                    line_h - int(10 * self.scale)
                )
                
                # Pulse highlight
                pulse = int(math.sin(self.menu_glow_timer * 8) * 40 + 60)
                pygame.draw.rect(surface, (PINK[0], PINK[1], PINK[2], pulse), selection_rect, 0, border_radius=4)
                pygame.draw.rect(surface, PINK, selection_rect, 2, border_radius=4)
                
                # Add a cyan arrow on the left
                arrow_y = menu_y + idx * line_h + int(10 * self.scale)
                pygame.draw.polygon(surface, ACCENT, [
                    (menu_x - int(35 * self.scale), arrow_y - int(8 * self.scale)),
                    (menu_x - int(15 * self.scale), arrow_y),
                    (menu_x - int(35 * self.scale), arrow_y + int(8 * self.scale))
                ])

            self._blit_text_with_shadow(
                surface,
                self.font_body,
                self.font_body_fallback,
                display_text,
                color,
                (menu_x, menu_y + idx * line_h),
            )

    def _draw_panel(self, surface: pygame.Surface) -> None:
        if self.active_panel == "ARCHIVE":
            self._draw_archive_panel(surface)
            return
        if self.active_panel == "AUDIO":
            self._draw_audio_panel(surface)
            return
        if self.active_panel == "LOGS":
            self._draw_logs_panel(surface)
            return
        
        panel_rect = pygame.Rect(
            int(self.width * 0.45),
            int(160 * self.scale),
            int(self.width * 0.50), # Slightly wider to handle wrapping better
            int(self.height * 0.55),
        )
        
        self._draw_shadowed_rect(
            surface,
            panel_rect,
            color=PINK,
            shadow_color=(0, 0, 0),
            fill_color=(10, 5, 8),
            border=2,
            radius=4
        )
        
        header = self.active_panel or ""
        self._blit_text_with_shadow(
            surface,
            self.font_label,
            self.font_label_fallback,
            f"// {header}",
            ACCENT,
            (panel_rect.x + int(20 * self.scale), panel_rect.y + int(15 * self.scale)),
        )
        
        pygame.draw.line(surface, PINK_DIM, (panel_rect.x + int(20 * self.scale), panel_rect.y + int(45 * self.scale)), (panel_rect.right - int(20 * self.scale), panel_rect.y + int(45 * self.scale)), 1)

        body_lines = self._get_panel_body(self.active_panel)
        text_x = panel_rect.x + int(20 * self.scale)
        text_y = panel_rect.y + int(60 * self.scale)
        available_width = panel_rect.width - int(40 * self.scale)
        wrapped = self._wrap_text_lines(body_lines, self.font_small, self.font_small_fallback, available_width)
        
        line_height = int(30 * self.scale)
        visible_lines = max(1, (panel_rect.height - int(100 * self.scale)) // line_height)
        
        # Clamp scrolling
        max_scroll = max(0, len(wrapped) - visible_lines)
        self.panel_scroll = max(0, min(self.panel_scroll, max_scroll))
        
        start = self.panel_scroll
        end = start + visible_lines
        
        for idx, line in enumerate(wrapped[start:end]):
            self._blit_text_with_shadow(
                surface,
                self.font_small,
                self.font_small_fallback,
                line,
                TEXT,
                (text_x, text_y + idx * line_height),
            )

        # Unified Scroll Indicator
        self._draw_scroll_indicator(surface, panel_rect, self.panel_scroll, visible_lines, len(wrapped))

        # Footer
        footer_rect = pygame.Rect(panel_rect.x, panel_rect.bottom - int(25 * self.scale), panel_rect.width, int(25 * self.scale))
        pygame.draw.rect(surface, PINK_DIM, footer_rect, 0, border_bottom_left_radius=4, border_bottom_right_radius=4)
        
        prompt_text = "[UP/DOWN] SCROLL | [ENTER/ESC] MENU"
        self._blit_text_with_shadow(
            surface,
            self.font_small,
            self.font_small_fallback,
            prompt_text,
            TEXT,
            (panel_rect.x + int(15 * self.scale), panel_rect.bottom - int(20 * self.scale)),
        )

    def _archive_geometry(self):
        panel_rect = pygame.Rect(
            int(self.width * 0.05),
            int(120 * self.scale),
            int(self.width * 0.9),
            int(self.height * 0.7),
        )
        left_rect = pygame.Rect(
            panel_rect.x + int(16 * self.scale),
            panel_rect.y + int(16 * self.scale),
            int(panel_rect.width * 0.32),
            panel_rect.height - int(32 * self.scale),
        )
        right_rect = pygame.Rect(
            left_rect.right + int(18 * self.scale),
            panel_rect.y + int(16 * self.scale),
            panel_rect.width - (left_rect.width + int(34 * self.scale)),
            panel_rect.height - int(32 * self.scale),
        )
        return panel_rect, left_rect, right_rect

    def _draw_audio_panel(self, surface: pygame.Surface) -> None:
        panel_rect = pygame.Rect(
            int(self.width * 0.05),
            int(120 * self.scale),
            int(self.width * 0.9),
            int(self.height * 0.7),
        )
        
        # Main Container
        self._draw_shadowed_rect(
            surface,
            panel_rect,
            color=PINK,
            shadow_color=(0, 0, 0),
            fill_color=(5, 2, 4),
            border=2,
            radius=4
        )

        header_x = panel_rect.x + int(20 * self.scale)
        header_y = panel_rect.y + int(15 * self.scale)
        header_text = "MIAZUKI AUDIO MATRIX"
        if self.showing_lyrics:
            header_text += " // LYRICS: " + self.audio_tracks[self.audio_selected_index]["title"].upper()
            
        self._blit_text_with_shadow(
            surface,
            self.font_label,
            self.font_label_fallback,
            header_text,
            GOLD,
            (header_x, header_y),
        )

        if self.showing_lyrics:
            # Draw Lyrics View
            lyrics_rect = pygame.Rect(
                panel_rect.x + int(20 * self.scale),
                panel_rect.y + int(60 * self.scale),
                panel_rect.width - int(40 * self.scale),
                panel_rect.height - int(120 * self.scale)
            )
            # Solid lyrics box
            pygame.draw.rect(surface, (10, 5, 8), lyrics_rect, 0, border_radius=4)
            pygame.draw.rect(surface, PINK_DIM, lyrics_rect, 1, border_radius=4)
            
            track = self.audio_tracks[self.audio_selected_index]
            raw_lyrics = track["lyrics"]
            
            # Wrap lyrics
            available_width = lyrics_rect.width - int(40 * self.scale)
            wrapped_lyrics = self._wrap_text_lines(raw_lyrics, self.font_small, self.font_small_fallback, available_width)
            
            line_h = int(24 * self.scale)
            visible_lines = lyrics_rect.height // line_h - 1
            max_scroll = max(0, len(wrapped_lyrics) - visible_lines)
            self.lyrics_scroll = min(self.lyrics_scroll, max_scroll)
            
            y = lyrics_rect.y + int(10 * self.scale)
            for i in range(self.lyrics_scroll, min(len(wrapped_lyrics), self.lyrics_scroll + visible_lines)):
                line = wrapped_lyrics[i]
                color = GOLD if line.startswith("[") else TEXT
                self._blit_text_with_shadow(
                    surface,
                    self.font_small,
                    self.font_small_fallback,
                    line,
                    color,
                    (lyrics_rect.x + int(20 * self.scale), y),
                )
                y += line_h
                
            # Unified Scroll Indicator
            self._draw_scroll_indicator(surface, lyrics_rect, self.lyrics_scroll, visible_lines, len(wrapped_lyrics))

            ctrl_y = panel_rect.bottom - int(45 * self.scale)
            self._blit_text_with_shadow(
                surface,
                self.font_small,
                self.font_small_fallback,
                "[UP/DOWN] SCROLL  [L/ESC] RETURN TO LIST",
                TEXT,
                (panel_rect.x + int(20 * self.scale), ctrl_y),
            )
            return

        # Welcome Message Area
        msg_rect = pygame.Rect(
            panel_rect.x + int(20 * self.scale),
            panel_rect.y + int(60 * self.scale),
            int(panel_rect.width * 0.50), # Slightly narrower to avoid overlap
            int(panel_rect.height * 0.7)  # Taller to fit more text if needed
        )
        # Solid message box
        pygame.draw.rect(surface, (20, 10, 15), msg_rect, 0, border_radius=4)
        pygame.draw.rect(surface, PINK_DIM, msg_rect, 1, border_radius=4)

        line_h = int(24 * self.scale)
        available_width = msg_rect.width - int(30 * self.scale)
        wrapped_msg = self._wrap_text_lines([self.audio_message], self.font_small, self.font_small_fallback, available_width)
        
        visible_lines = msg_rect.height // line_h - 1
        max_scroll = max(0, len(wrapped_msg) - visible_lines)
        self.audio_welcome_scroll = min(self.audio_welcome_scroll, max_scroll)
        
        y = msg_rect.y + int(15 * self.scale)
        for i in range(self.audio_welcome_scroll, min(len(wrapped_msg), self.audio_welcome_scroll + visible_lines)):
            line = wrapped_msg[i]
            self._blit_text_with_shadow(
                surface,
                self.font_small,
                self.font_small_fallback,
                line,
                TEXT,
                (msg_rect.x + int(15 * self.scale), y),
            )
            y += line_h

        # Unified Scroll Indicator for Welcome Message
        self._draw_scroll_indicator(surface, msg_rect, self.audio_welcome_scroll, visible_lines, len(wrapped_msg))

        # Track List Area
        list_rect = pygame.Rect(
            msg_rect.right + int(20 * self.scale),
            msg_rect.y,
            panel_rect.width - (msg_rect.width + int(60 * self.scale)),
            panel_rect.height - int(100 * self.scale)
        )
        # Solid list box
        pygame.draw.rect(surface, (10, 5, 8), list_rect, 0, border_radius=4)
        pygame.draw.rect(surface, PINK_DIM, list_rect, 1, border_radius=4)

        self._blit_text_with_shadow(
            surface,
            self.font_small,
            self.font_small_fallback,
            "AVAILABLE TRACKS:",
            ACCENT,
            (list_rect.x + int(10 * self.scale), list_rect.y - int(25 * self.scale)),
        )

        track_h = int(50 * self.scale)
        visible_tracks = list_rect.height // track_h
        
        for i in range(visible_tracks):
            idx = self.track_list_scroll + i
            if idx >= len(self.audio_tracks):
                break
            
            track = self.audio_tracks[idx]
            is_selected = idx == self.audio_selected_index
            is_playing = idx == self.current_playing_track
            
            y = list_rect.y + int(10 * self.scale) + i * track_h
            if y + track_h > list_rect.bottom:
                break

            # Selection Highlight
            if is_selected:
                sel_rect = pygame.Rect(list_rect.x + 5, y, list_rect.width - 10, track_h - 5)
                pygame.draw.rect(surface, (PINK[0], PINK[1], PINK[2], 40), sel_rect, 0, border_radius=4)
                pygame.draw.rect(surface, PINK, sel_rect, 1, border_radius=4)
            
            # Track Title wrapping
            color = GOLD if is_playing else (ACCENT if is_selected else TEXT)
            prefix = ">> " if is_playing else (" > " if is_selected else "   ")
            
            # Max width for title (leaving space for prefix and [LYRICS])
            title_max_w = list_rect.width - int(120 * self.scale)
            wrapped_title = self._wrap_text_lines([track['title']], self.font_small, self.font_small_fallback, title_max_w)
            
            # Only show first line or two to fit in track_h
            display_y = y + int(8 * self.scale)
            for j, line in enumerate(wrapped_title[:2]):
                text = f"{prefix if j==0 else '   '}{line}"
                self._blit_text_with_shadow(
                    surface,
                    self.font_small,
                    self.font_small_fallback,
                    text,
                    color,
                    (list_rect.x + int(10 * self.scale), display_y),
                )
                display_y += int(18 * self.scale)
            
            if "lyrics" in track:
                lyrics_color = GOLD if is_selected else PINK_DIM
                self._blit_text_with_shadow(
                    surface,
                    self.font_small,
                    self.font_small_fallback,
                    "[LYRICS]",
                    lyrics_color,
                    (list_rect.right - int(90 * self.scale), y + int(10 * self.scale)),
                )
            
        # Unified Scroll Indicator for Track List
        self._draw_scroll_indicator(surface, list_rect, self.track_list_scroll, visible_tracks, len(self.audio_tracks))

        # Status / Controls
        ctrl_y = panel_rect.bottom - int(30 * self.scale)
        hints = "[UP/DOWN] NAVIGATE  [ENTER] PLAY  [SPACE] STOP"
        if "lyrics" in self.audio_tracks[self.audio_selected_index]:
            hints += "  [L] VIEW LYRICS"
        hints += "  [ESC] BACK"
        
        self._blit_text_with_shadow(
            surface,
            self.font_small,
            self.font_small_fallback,
            hints,
            TEXT,
            (panel_rect.x + int(20 * self.scale), ctrl_y),
        )

    def _draw_archive_panel(self, surface: pygame.Surface) -> None:
        panel_rect, left_rect, right_rect = self._archive_geometry()
        
        # We want the archive list (left) to look like the main menu
        # Match the menu box from _draw_menu
        line_h = int(50 * self.scale)
        
        # Draw the list container (matching main menu style)
        self._draw_shadowed_rect(
            surface,
            left_rect,
            color=PINK,
            shadow_color=(0, 0, 0),
            fill_color=(10, 5, 8),
            border=2,
            radius=4,
        )

        header_x = left_rect.x + int(10 * self.scale)
        header_y = left_rect.y - int(35 * self.scale)
        self._blit_text_with_shadow(
            surface,
            self.font_label,
            self.font_label_fallback,
            "ARCHIVE",
            ACCENT,
            (header_x, header_y),
        )
        
        line_h = int(50 * self.scale)
        visible_docs = (left_rect.height - int(32 * self.scale)) // line_h
        
        for i in range(visible_docs):
            idx = self.archive_list_scroll + i
            if idx >= len(self.archive_docs):
                break
            
            doc = self.archive_docs[idx]
            is_selected = idx == self.archive_selected_index and self.archive_open_index is None
            is_open = idx == self.archive_open_index
            
            y = left_rect.y + int(15 * self.scale) + i * line_h
            if y + line_h > left_rect.bottom:
                break
            
            color = ACCENT if (is_selected or is_open) else TEXT
            
            # Wrap title if too long for the menu box
            title_max_w = left_rect.width - int(45 * self.scale)
            wrapped_title = self._wrap_text_lines([doc['title']], self.font_small, self.font_small_fallback, title_max_w)
            
            if is_selected or is_open:
                # Active option glow/box (matching main menu)
                selection_rect = pygame.Rect(
                    left_rect.x + int(10 * self.scale),
                    y - int(5 * self.scale),
                    left_rect.width - int(20 * self.scale),
                    line_h - int(10 * self.scale)
                )
                
                pulse = int(math.sin(self.menu_glow_timer * 8) * 30 + 40)
                pygame.draw.rect(surface, (PINK[0], PINK[1], PINK[2], pulse), selection_rect, 0, border_radius=4)
                pygame.draw.rect(surface, PINK, selection_rect, 1, border_radius=4)

                # Add a cyan arrow on the left
                arrow_y = y + int(15 * self.scale)
                pygame.draw.polygon(surface, ACCENT, [
                    (left_rect.x - int(15 * self.scale), arrow_y - int(6 * self.scale)),
                    (left_rect.x - int(5 * self.scale), arrow_y),
                    (left_rect.x - int(15 * self.scale), arrow_y + int(6 * self.scale))
                ])

            # Draw wrapped title lines
            display_y = y
            for j, line in enumerate(wrapped_title[:2]): # Show up to 2 lines
                prefix = "[ " if j == 0 else "  "
                self._blit_text_with_shadow(
                    surface,
                    self.font_small,
                    self.font_small_fallback,
                    f"{prefix}{line}",
                    color,
                    (left_rect.x + int(25 * self.scale), display_y),
                )
                display_y += int(18 * self.scale)

        # Unified Scroll Indicator for Archive List
        self._draw_scroll_indicator(surface, left_rect, self.archive_list_scroll, visible_docs, len(self.archive_docs))

        # Right: document view
        self._draw_shadowed_rect(
            surface,
            right_rect,
            color=PINK,
            shadow_color=(0, 0, 0),
            fill_color=(5, 2, 4),
            border=2,
            radius=4
        )
        
        padding = int(20 * self.scale)
        content_width = right_rect.width - padding * 2
        line_height = int(24 * self.scale)

        if self.archive_open_index is None:
            # Welcome message in archive
            msg_header = [
                "SYSTEM: ARCHIVE CONNECTED",
                "-------------------------"
            ]
            msg_history = [
                "The documents here are",
                "fragments of a lost",
                "history. Handle with care."
            ]
            msg_keys = [
                "KEYS:",
                " [UP/DOWN] NAVIGATE",
                " [ENTER]   OPEN DATA",
                " [ESC]     BACK TO MENU"
            ]
            
            y = right_rect.y + int(40 * self.scale)
            
            # Header (Left aligned)
            for line in msg_header:
                self._blit_text_with_shadow(
                    surface, self.font_body, self.font_body_fallback,
                    line, ACCENT, (right_rect.x + padding, y)
                )
                y += int(30 * self.scale)
            
            y += int(10 * self.scale)
            
            # History (Center aligned)
            for line in msg_history:
                font = self._get_font(self.font_body, self.font_body_fallback, line.upper())
                txt_surf = font.render(line.upper(), True, TEXT)
                center_x = right_rect.x + (right_rect.width // 2) - (txt_surf.get_width() // 2)
                self._blit_text_with_shadow(
                    surface, self.font_body, self.font_body_fallback,
                    line, TEXT, (center_x, y)
                )
                y += int(30 * self.scale)
            
            y += int(20 * self.scale)
            
            # Keys (Left aligned, smaller font)
            for line in msg_keys:
                self._blit_text_with_shadow(
                    surface, self.font_small, self.font_small_fallback,
                    line, GOLD if "KEYS" in line else TEXT, (right_rect.x + padding, y)
                )
                y += int(22 * self.scale)
            return

        doc = self.archive_docs[self.archive_open_index]
        title_surf = self._render_text(self.font_label, self.font_label_fallback, doc["title"], GOLD)
        surface.blit(title_surf, (right_rect.x + padding, right_rect.y + int(15 * self.scale)))
        
        pygame.draw.line(surface, GOLD, (right_rect.x + padding, right_rect.y + int(45 * self.scale)), (right_rect.right - padding, right_rect.y + int(45 * self.scale)), 1)

        # Wrap and scroll
        wrapped = self._wrap_text_lines(doc["lines"], self.font_small, self.font_small_fallback, content_width)
        visible_height = right_rect.height - int(100 * self.scale)
        visible_lines = max(1, visible_height // line_height)
        start = max(0, min(self.archive_scroll, max(0, len(wrapped) - visible_lines)))
        end = start + visible_lines
        
        y = right_rect.y + int(60 * self.scale)
        for line in wrapped[start:end]:
            self._blit_text_with_shadow(
                surface,
                self.font_small,
                self.font_small_fallback,
                line,
                TEXT,
                (right_rect.x + padding, y),
            )
            y += line_height

        # Unified Scroll Indicator
        self._draw_scroll_indicator(surface, right_rect, start, visible_lines, len(wrapped))

        status_bar_rect = pygame.Rect(right_rect.x, right_rect.bottom - int(25 * self.scale), right_rect.width, int(25 * self.scale))
        pygame.draw.rect(surface, PINK_DIM, status_bar_rect, 0, border_bottom_left_radius=4, border_bottom_right_radius=4)
        
        instructions = "SCROLL: UP/DOWN | CLOSE: ESC/ENTER"
        self._blit_text_with_shadow(
            surface,
            self.font_small,
            self.font_small_fallback,
            instructions,
            TEXT,
            (right_rect.x + int(10 * self.scale), right_rect.bottom - int(20 * self.scale)),
        )

    def _get_panel_body(self, panel: Optional[str]):
        if panel == "SYSOP":
            return [
                "SYSOP: PAPER_CRANE",
                "",
                "Signal's clean enough for now. After that Tokyo Yamoto Forever interview, traffic exploded. Cool, but heat follows crowds. Pacifica FBI already sniffed the archive once. I'm keeping only a few docs live at a time. Ride the static, stay light, stay analog. The more they try to catch the crane, the more paper they waste. Keep your head down and your signal hopped.",
            ]
        if panel == "ARCHIVE":
            return [
                "ARCHIVE QUEUE: All entries shown here have been verified for analog authenticity. Firmware dumps, broadcast captures, and orphaned TXT files are rotated weekly to minimize exposure to Pacifica surveillance assets. If a document you are looking for is missing, check back after the next signal hop.",
            ]
        if panel == "LOGS":
            return [
                "LOG TRACE: [handshake ok] [auth guest/origami] [encrypted channel open] [analog hiss masked digital signature] [session heartbeat active] [routing via node-07] [ping 142ms] [background scan clean]",
            ]
        return []

    def _attempt_login(self) -> None:
        if self.username.strip().lower() == "guest" and self.password.strip().lower() == "origami":
            self.state = "menu"
            self.error_message = ""
            self.menu_index = 0
            self.active_panel = None
            self._log_action(f"login successful: {self.username}")
        else:
            self.error_message = "ACCESS DENIED"
            self.password = ""
            self._log_action(f"login failed: {self.username}")

    def _end_call(self) -> None:
        self.request_exit = True
        if self.on_exit:
            self.on_exit()
