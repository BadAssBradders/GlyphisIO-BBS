import pygame
import sys
from datetime import datetime
import random
import time
import re
import json
import os
import numpy as np
from typing import Dict, List, Optional, Tuple

# Try to import fitz (PyMuPDF) for PDF rendering
try:
    import fitz  # type: ignore
    _fitz_available = True
except ImportError:
    fitz = None  # type: ignore
    _fitz_available = False

# Import configuration and utilities
from config import *
from utils import (
    get_data_path, log_event, _get_time_aware_video_name,
    get_realtime_datetime, get_tokyo_datetime, _is_tokyo_nighttime,
    format_ingame_timestamp, format_ingame_clock, normalize_timestamp_1989
)

# Add Data folder to Python path if it exists (for modules moved to Data/)
# This allows imports from Data/games, Data/tokens, etc.
_data_path = get_data_path("")
if os.path.exists(_data_path) and _data_path not in sys.path:
    sys.path.insert(0, _data_path)

# Import game systems
from games import GAME_DEFINITIONS, GameDefinition, BaseGameSession
from games.registry import launch_external_game
from tokens import Tokens, normalize_token, describe_token, sort_tokens

# Import supporting systems
from systems import Email, EmailDatabase, NPCResponder, EnhancedNPCResponder, TokenInventory, SteamManager

# Import OS Mode
from OS.OS_Mode import OSMode

# Try to import cv2 for video playback
try: 
    import cv2
    _cv2_available = True
except ImportError:
    _cv2_available = False
    print("Warning: cv2 (opencv-python) not available. Video playback will be disabled.")

# Initialize mixer early (before pygame.init() for best compatibility)
try:
    pygame.mixer.pre_init(
        frequency=AUDIO_FREQUENCY,
        size=AUDIO_SIZE,
        channels=AUDIO_CHANNELS,
        buffer=AUDIO_BUFFER
    )
except:
    pass  # If pre_init fails, we'll try init() later

# Initialize pygame
pygame.init()

_glyph_font_cache = {}


def get_selection_glyph_font(size):
    """Return a font that can render the selection glyph, caching per size."""
    if size in _glyph_font_cache:
        return _glyph_font_cache[size]

    candidate_fonts = ["Segoe UI Symbol", "Segoe UI Emoji", "Arial Unicode MS", None]
    for name in candidate_fonts:
        try:
            font_obj = pygame.font.SysFont(name, size) if name else pygame.font.Font(None, size)
        except Exception:
            continue

        metrics = font_obj.metrics(SELECTION_GLYPH)
        if metrics and metrics[0] is not None:
            _glyph_font_cache[size] = font_obj
            return font_obj

    fallback = pygame.font.SysFont(None, size)
    _glyph_font_cache[size] = fallback
    return fallback


class DocumentationViewer:
    """Stylised document viewer that renders reference PDFs alongside the BBS."""

    GRID_START = (1547, 37)        # Shifted grid start (baseline 2560x1440)
    GRID_COLUMNS = 4
    TOTAL_SLOTS = 16

    def __init__(self, docs_directory: str, scale: float):
        # Use get_data_path if docs_directory is a relative path, otherwise use as-is
        if not os.path.isabs(docs_directory):
            self.docs_directory = get_data_path(docs_directory)
        else:
            self.docs_directory = docs_directory
        # Note: Covers folder uses capital C
        self.cover_directory = os.path.join(self.docs_directory, "Covers")
        self.scale = scale
        self.visible = False
        self.mode = "grid"  # "grid" or "document"
        self.docs: List[str] = []
        self.doc_cache: Dict[str, Dict[str, object]] = {}
        self.selected_doc: Optional[str] = None
        self.selected_page: int = 0
        self.hover_index: Optional[int] = None
        self.display_items: List[Dict[str, object]] = []
        self.thumbnail_rects: List[pygame.Rect] = []
        self.grid_bounds_rect = pygame.Rect(0, 0, 0, 0)
        self.paper_rect = pygame.Rect(0, 0, 0, 0)
        self.close_rect = pygame.Rect(0, 0, 0, 0)
        self.back_rect = pygame.Rect(0, 0, 0, 0)
        self.nav_prev_rect = pygame.Rect(0, 0, 0, 0)
        self.nav_next_rect = pygame.Rect(0, 0, 0, 0)
        self.nav_return_rect = pygame.Rect(0, 0, 0, 0)
        self.thumbnail_animations: List[Dict[str, float]] = []
        self.time_active = 0.0
        self.grid_anim_duration = 0.4
        self.grid_anim_total = 0.4
        self.close_duration = 0.25
        self.button_prev_image = self._load_button_image("Page-_Button.png")
        self.button_next_image = self._load_button_image("Page+_Button.png")
        self.button_library_image = self._load_button_image("Library_Button.png")
        self.closing = False
        self.close_animation = 0.0
        self.pending_mode: Optional[str] = None
        self.zoomed = False
        self.zoom_scroll = 0
        self.zoom_scroll_max = 0
#        Cursor handling
        self.cursor_default = pygame.cursors.Cursor(pygame.SYSTEM_CURSOR_ARROW)
        self.cursor_hand = pygame.cursors.Cursor(pygame.SYSTEM_CURSOR_HAND)
        self.cursor_zoom_in = self._load_cursor_cursor("mouse-mag-glass+.png")
        self.cursor_zoom_out = self._load_cursor_cursor("mouse-mag-glass-.png")
        self.cursor_state: Optional[str] = None
        self._load_fonts()

    def _load_fonts(self) -> None:
        title_size = max(int(30 * self.scale), 18)
        body_size = max(int(20 * self.scale), 14)
        caption_size = max(int(16 * self.scale), 12)
        self.font_title = pygame.font.SysFont("Segoe UI", title_size, bold=True)
        self.font_body = pygame.font.SysFont("Calibri", body_size)
        self.font_bold = pygame.font.SysFont("Calibri", body_size, bold=True)
        self.font_caption = pygame.font.SysFont("Calibri", caption_size)
        self._update_layout_metrics()
        self.refresh_docs()

    def _update_layout_metrics(self) -> None:
        self.thumbnail_width = max(int(320 * 0.385 * self.scale), 140)
        self.thumbnail_height = max(int(452 * 0.385 * self.scale), 200)
        self.frame_padding = max(int(14 * self.scale), 6)
        self.grid_padding = max(int(36 * self.scale), 16)
        self.shadow_offset = (
            max(int(12 * self.scale), 6),
            max(int(18 * self.scale), 8),
        )
        self.page_width = max(int(700 * self.scale), 260)
        self.page_height = max(int(960 * self.scale), 360)

    def set_scale(self, scale: float) -> None:
        if self.scale == scale:
            return
        self.scale = scale
        self._load_fonts()
        self.doc_cache.clear()  # Surfaces depend on scale

    def refresh_docs(self) -> None:
        if not os.path.isdir(self.docs_directory):
            self.docs = []
            self.display_items = []
            self.thumbnail_rects = []
            return
        docs = [
            file
            for file in os.listdir(self.docs_directory)
            if file.lower().endswith(".pdf")
        ]
        docs.sort(key=str.lower)
        self.docs = docs
        items: List[Dict[str, object]] = []
        for doc in docs:
            cover_surface = self._load_cover_surface(doc)
            items.append({"type": "doc", "filename": doc, "cover": cover_surface})

        placeholder_needed = max(0, self.TOTAL_SLOTS - len(items))
        for idx in range(placeholder_needed):
            slot_number = len(items) + 1
            placeholder_surface = self._create_placeholder_surface(slot_number)
            items.append(
                {"type": "placeholder", "filename": None, "cover": placeholder_surface}
            )

        self.display_items = items[: self.TOTAL_SLOTS]
        self.thumbnail_rects = [pygame.Rect(0, 0, 0, 0) for _ in self.display_items]
        self._reset_thumbnail_animation()

    def toggle_visibility(self) -> None:
        if self.visible:
            if not self.closing:
                self.zoomed = False
                self.zoom_scroll = 0
                self.zoom_scroll_max = 0
                self.closing = True
                self.close_animation = 0.0
                self.close_duration = (
                    max(self.grid_anim_total, 0.4) if self.mode == "grid" else 0.25
                )
                self.pending_mode = None
                return
            return
        self.refresh_docs()
        self.visible = True
        self.mode = "grid"
        self.selected_doc = None
        self.selected_page = 0
        self.hover_index = None
        self.closing = False
        self.close_animation = 0.0
        self.pending_mode = None

    def close(self) -> None:
        self.closing = True
        self.close_animation = 0.0
        self.close_duration = 0.25
        self.pending_mode = None
        self.zoomed = False
        self.zoom_scroll = 0
        self.zoom_scroll_max = 0

    def _return_to_grid(self) -> None:
        self.mode = "grid"
        self.selected_doc = None
        self.selected_page = 0
        self.hover_index = None
        self.zoomed = False
        self.zoom_scroll = 0
        self.zoom_scroll_max = 0
        self.pending_mode = None
        self._reset_thumbnail_animation()
        self.thumbnail_animations = [
            {"delay": idx * 0.05} for idx in range(len(self.display_items))
        ]

    def open_document(self, filename: str) -> None:
        if filename not in self.docs:
            return
        if filename not in self.doc_cache:
            self.doc_cache[filename] = self._load_document_surfaces(filename)
        self.selected_doc = filename
        self.selected_page = 0
        self.mode = "document"
        self.hover_index = None
        self.time_active = 0.0
        self.pending_mode = None
        self.close_duration = 0.25
        self.zoomed = False
        self.zoom_scroll = 0
        self.zoom_scroll_max = 0

    def _load_document_surfaces(self, filename: str) -> Dict[str, object]:
        paper_width = self.page_width
        paper_height = self.page_height
        pages: List[pygame.Surface] = []
        # docs_directory is already set to use get_data_path in __init__
        full_path = os.path.join(self.docs_directory, filename)

        if _fitz_available:
            try:
                document = fitz.open(full_path)  # type: ignore[call-arg]
                for page in document:
                    rect = page.rect
                    if rect.width == 0 or rect.height == 0:
                        continue
                    zoom = self.page_width / rect.width
                    matrix = fitz.Matrix(zoom, zoom)
                    pix = page.get_pixmap(matrix=matrix, alpha=True)
                    mode = "RGBA" if pix.alpha else "RGB"
                    surface = pygame.image.frombuffer(pix.samples, (pix.width, pix.height), mode)
                    surface = surface.convert_alpha() if pix.alpha else surface.convert()
                    pages.append(surface.copy())
                document.close()
            except Exception as exc:
                error_text = f"Unable to render PDF via PyMuPDF:\n{exc}"
                pages = [self._render_page_surface(error_text, paper_width, paper_height)]

        if not pages:
            fallback_text = (
                "PDF renderer unavailable.\n\n"
                "Install PyMuPDF (pip install pymupdf) to render the actual document pages.\n\n"
                f"File: {filename}"
            )
            pages.append(self._render_page_surface(fallback_text, paper_width, paper_height))

        if not pages:
            pages.append(
                self._render_page_surface("Document is empty.", paper_width, paper_height)
            )
        return {
            "pages": pages,
            "size": (paper_width, paper_height),
            "zoom_pages": None,
            "zoom_cache": {},
            "path": full_path,
        }

    def _render_page_surface(self, text: str, width: int, height: int) -> pygame.Surface:
        surface = pygame.Surface((width, height), pygame.SRCALPHA)
        paper_color = (250, 252, 255)
        pygame.draw.rect(surface, paper_color, surface.get_rect(), border_radius=18)
        pygame.draw.rect(surface, (210, 218, 230), surface.get_rect(), 3, border_radius=18)

        header_height = int(40 * self.scale)
        header_rect = pygame.Rect(0, 0, width, header_height)
        header_gradient = pygame.Surface(header_rect.size, pygame.SRCALPHA)
        for x in range(header_rect.width):
            blend = x / max(1, header_rect.width - 1)
            color = (
                int(224 + (245 - 224) * blend),
                int(232 + (249 - 232) * blend),
                int(242 + (255 - 242) * blend),
                240,
            )
            pygame.draw.line(header_gradient, color, (x, 0), (x, header_rect.height))
        surface.blit(header_gradient, header_rect)

        footer_height = int(28 * self.scale)
        footer_rect = pygame.Rect(0, height - footer_height, width, footer_height)
        footer_surface = pygame.Surface(footer_rect.size, pygame.SRCALPHA)
        footer_surface.fill((235, 240, 246, 235))
        surface.blit(footer_surface, footer_rect)

        margin_x = int(36 * self.scale)
        margin_y = header_height + int(22 * self.scale)
        column_width = width - margin_x * 2
        y = margin_y
        line_height = self.font_body.get_linesize()

        content_color = (35, 43, 60)
        for chunk in self._wrap_text(text, self.font_body, column_width):
            rendered = self.font_body.render(chunk, True, content_color)
            surface.blit(rendered, (margin_x, y))
            y += line_height + int(2 * self.scale)
            if y > height - margin_y - line_height:
                overflow = self.font_caption.render("…", True, (120, 127, 140))
                surface.blit(overflow, (margin_x, height - footer_height - overflow.get_height() - int(6 * self.scale)))
                break
        footer_text = self.font_caption.render("FIELD REFERENCE COPY", True, (140, 149, 165))
        footer_x = margin_x
        footer_y = height - footer_height + (footer_height - footer_text.get_height()) // 2
        surface.blit(footer_text, (footer_x, footer_y))

        return surface

    def _load_cover_surface(self, filename: str) -> pygame.Surface:
        base_name = os.path.splitext(filename)[0]
        cover_filename = f"cover-{base_name}.png"
        cover_path = os.path.join(self.cover_directory, cover_filename)
        try:
            image = pygame.image.load(cover_path).convert_alpha()
            surface = pygame.transform.smoothscale(
                image, (self.thumbnail_width, self.thumbnail_height)
            )
            return surface
        except Exception:
            return self._create_placeholder_surface(label=base_name)

    def _load_button_image(self, filename: str) -> Optional[pygame.Surface]:
        path = get_data_path("images", filename)
        try:
            image = pygame.image.load(path).convert_alpha()
            return image
        except Exception:
            return None

    def _load_cursor_cursor(self, filename: str) -> Optional[pygame.cursors.Cursor]:
        path = get_data_path("images", filename)
        try:
            image = pygame.image.load(path).convert_alpha()
            size = max(int(48 * self.scale), 24)
            image = pygame.transform.smoothscale(image, (size, size))
            hotspot = (size // 2, size // 2)
            try:
                return pygame.cursors.Cursor(hotspot, image)
            except Exception:
                return None
        except Exception:
            return None
    
    def _reset_thumbnail_animation(self) -> None:
        count = len(self.display_items)
        self.thumbnail_animations = [{"delay": idx * 0.05} for idx in range(count)]
        last_delay = self.thumbnail_animations[-1]["delay"] if count else 0.0
        self.grid_anim_duration = 0.4
        self.grid_anim_total = self.grid_anim_duration + last_delay
        self.time_active = 0.0
        self.cursor_state = None

    def _create_placeholder_surface(
        self, slot_number: Optional[int] = None, label: Optional[str] = None
    ) -> pygame.Surface:
        surface = pygame.Surface((self.thumbnail_width, self.thumbnail_height), pygame.SRCALPHA)
        base_color = (82, 86, 96, 230)
        pygame.draw.rect(surface, base_color, surface.get_rect(), border_radius=18)
        pygame.draw.rect(surface, (120, 126, 140), surface.get_rect(), 4, border_radius=18)

        caption = label or (f"DOCUMENT SLOT {slot_number:02d}" if slot_number else "DOCUMENT SLOT")
        wrapped = self._wrap_text(caption, self.font_bold, self.thumbnail_width - int(40 * self.scale))

        text_y = surface.get_height() // 2 - (len(wrapped) * self.font_bold.get_linesize()) // 2
        for line in wrapped:
            rendered = self.font_bold.render(line, True, (230, 234, 242))
            surface.blit(
                rendered,
                (
                    (surface.get_width() - rendered.get_width()) // 2,
                    text_y,
                ),
            )
            text_y += self.font_bold.get_linesize()

        return surface

    def _draw_soft_button(self, screen: pygame.Surface, rect: pygame.Rect, label: str) -> None:
        button_surface = pygame.Surface(rect.size, pygame.SRCALPHA)
        for y in range(rect.height):
            blend = y / max(1, rect.height - 1)
            color = (
                int(210 + (175 - 210) * blend),
                int(230 + (205 - 230) * blend),
                int(242 + (225 - 242) * blend),
                int(185 + (215 - 185) * blend),
            )
            pygame.draw.line(button_surface, color, (0, y), (rect.width, y))
        pygame.draw.rect(button_surface, (130, 156, 186), button_surface.get_rect(), 3, border_radius=22)
        text_surface = self.font_caption.render(label, True, (24, 36, 54))
        button_surface.blit(
            text_surface,
            (
                (rect.width - text_surface.get_width()) // 2,
                (rect.height - text_surface.get_height()) // 2,
            ),
        )
        screen.blit(button_surface, rect.topleft)
    def _draw_button_image(self, screen: pygame.Surface, rect: pygame.Rect, image: Optional[pygame.Surface]) -> None:
        if image:
            img_width, img_height = image.get_size()
            scale = min(rect.width / img_width, rect.height / img_height)
            target_size = (max(1, int(img_width * scale)), max(1, int(img_height * scale)))
            scaled = pygame.transform.smoothscale(image, target_size)
            offset_x = rect.x + (rect.width - scaled.get_width()) // 2
            offset_y = rect.y + (rect.height - scaled.get_height()) // 2
            screen.blit(scaled, (offset_x, offset_y))
        else:
            self._draw_soft_button(screen, rect, "UNAVAILABLE")

    def _ensure_zoom_pages(self, cache: Dict[str, object]) -> List[pygame.Surface]:
        zoom_pages = cache.get("zoom_pages")
        if zoom_pages is not None:
            return zoom_pages  # type: ignore[return-value]
        pages = cache.get("pages", [])
        if not _fitz_available:
            cache["zoom_pages"] = pages
            return pages  # type: ignore[return-value]
        full_path = cache.get("path")
        zoom_results: List[pygame.Surface] = []
        try:
            document = fitz.open(full_path)  # type: ignore[arg-type]
            for page in document:
                rect = page.rect
                if rect.width == 0 or rect.height == 0:
                    continue
                zoom_factor = max(2.5, (self.page_width * 3) / rect.width)
                matrix = fitz.Matrix(zoom_factor, zoom_factor)
                pix = page.get_pixmap(matrix=matrix, alpha=True)
                mode = "RGBA" if pix.alpha else "RGB"
                surface = pygame.image.frombuffer(pix.samples, (pix.width, pix.height), mode)
                surface = surface.convert_alpha() if pix.alpha else surface.convert()
                zoom_results.append(surface.copy())
            document.close()
        except Exception:
            zoom_results = list(pages)
        if not zoom_results:
            zoom_results = list(pages)
        cache["zoom_pages"] = zoom_results
        cache["zoom_cache"] = {}
        return zoom_results  # type: ignore[return-value]

    def _get_zoom_scaled_surface(
        self, cache: Dict[str, object], page_index: int, target_width: int
    ) -> pygame.Surface:
        zoom_pages: List[pygame.Surface] = self._ensure_zoom_pages(cache)
        base_surface = zoom_pages[min(page_index, len(zoom_pages) - 1)]
        zoom_cache: Dict[tuple, List[Optional[pygame.Surface]]] = cache.setdefault("zoom_cache", {})  # type: ignore[assignment]
        cache_key = (target_width,)
        scaled_list = zoom_cache.get(cache_key)
        if scaled_list is None:
            scaled_list = [None] * len(zoom_pages)
            zoom_cache[cache_key] = scaled_list
        scaled_surface = scaled_list[page_index]
        if scaled_surface is None:
            base_width, base_height = base_surface.get_size()
            if base_width == 0 or base_height == 0:
                return base_surface
            scale = min(target_width / base_width, 1.0)
            scaled_width = max(1, int(base_width * scale))
            scaled_height = max(1, int(base_height * scale))
            scaled_surface = pygame.transform.smoothscale(base_surface, (scaled_width, scaled_height))
            scaled_list[page_index] = scaled_surface
        return scaled_surface

    def _adjust_zoom_scroll(self, delta: int) -> None:
        if not self.zoomed:
            return
        if self.zoom_scroll_max <= 0:
            self.zoom_scroll = 0
            return
        self.zoom_scroll = max(0, min(self.zoom_scroll + delta, self.zoom_scroll_max))

    def _zoom_scroll_step(self) -> int:
        return max(int(80 * self.scale), 30)

    def apply_cursor(self) -> None:
        desired_state = "arrow"
        desired_cursor = self.cursor_default
        focused = pygame.mouse.get_focused()
        if focused and self.visible and not self.closing and self.mode == "document":
            pos = pygame.mouse.get_pos()
            if self.paper_rect.collidepoint(pos):
                desired_state = "zoom_out" if self.zoomed else "zoom_in"
                desired_cursor = (
                    self.cursor_zoom_out if self.zoomed else self.cursor_zoom_in
                )
                if desired_cursor is None:
                    desired_cursor = self.cursor_hand
        if desired_cursor and self.cursor_state != desired_state:
            try:
                pygame.mouse.set_cursor(desired_cursor)
                self.cursor_state = desired_state
            except Exception:
                pass

    def _draw_fadeout(self, screen: pygame.Surface) -> None:
        if self.close_animation <= 0.0:
            return
        if self.mode == "grid" and self.pending_mode is None:
            return
        duration = self.close_duration if self.close_duration else 0.25
        alpha = max(0, min(200, int(255 * (self.close_animation / duration))))
        fade_surface = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        fade_surface.fill((0, 0, 0, alpha))
        screen.blit(fade_surface, (0, 0))

    @staticmethod
    def _wrap_text(text: str, font: pygame.font.Font, max_width: int) -> List[str]:
        """Wrap text to fit within max_width pixels. Preserves double newlines as blank lines."""
        if not text:
            return []
        lines: List[str] = []
        # Split by newlines to preserve paragraph structure and consecutive newlines
        paragraphs = text.split('\n')
        for paragraph in paragraphs:
            # Empty paragraph means a blank line (from \n\n)
            if paragraph == "":
                lines.append("")
                continue
            words = paragraph.split()
            if not words:
                continue
            current = words[0]
            for word in words[1:]:
                candidate = f"{current} {word}"
                if font.size(candidate)[0] <= max_width:
                    current = candidate
                else:
                    lines.append(current)
                    current = word
            lines.append(current)
        return lines

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.visible:
            return False

        if self.mode == "grid":
            if event.type == pygame.MOUSEMOTION:
                self.hover_index = None
                for idx, rect in enumerate(self.thumbnail_rects):
                    if rect.collidepoint(event.pos):
                        self.hover_index = idx
                        break
                return self.grid_bounds_rect.collidepoint(event.pos)

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if not self.grid_bounds_rect.collidepoint(event.pos):
                    return False
                for idx, rect in enumerate(self.thumbnail_rects):
                    if rect.collidepoint(event.pos):
                        item = self.display_items[idx]
                        if item.get("type") == "doc" and item.get("filename"):
                            self.open_document(item["filename"])  # type: ignore[index]
                        return True
                return True

        elif self.mode == "document":
            if self.closing:
                return True

            if event.type == pygame.MOUSEWHEEL and self.zoomed:
                self._adjust_zoom_scroll(-event.y * self._zoom_scroll_step())
                return True

            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1 and self.paper_rect.collidepoint(event.pos):
                    if self.zoomed:
                        self.zoomed = False
                        self.zoom_scroll = 0
                        self.zoom_scroll_max = 0
                    else:
                        self.zoomed = True
                        self.zoom_scroll = 0
                    return True
                if event.button == 4 and self.zoomed:
                    self._adjust_zoom_scroll(-self._zoom_scroll_step())
                    return True
                if event.button == 5 and self.zoomed:
                    self._adjust_zoom_scroll(self._zoom_scroll_step())
                    return True
                if event.button == 1:
                    if self.nav_prev_rect.collidepoint(event.pos):
                        self._advance_page(-1)
                        return True
                    if self.nav_return_rect.collidepoint(event.pos):
                        self.pending_mode = "grid"
                        self.close_duration = 0.25
                        self.closing = True
                        self.close_animation = 0.0
                        return True
                    if self.nav_next_rect.collidepoint(event.pos):
                        self._advance_page(1)
                        return True
                    return True

            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_F4):
                    self.close()
                    return True
                if event.key == pygame.K_LEFT and not self.zoomed:
                    self._advance_page(-1)
                    return True
                if event.key == pygame.K_RIGHT and not self.zoomed:
                    self._advance_page(1)
                    return True
                if event.key in (pygame.K_RETURN, pygame.K_BACKSPACE):
                    self.pending_mode = "grid"
                    self.close_duration = 0.25
                    self.closing = True
                    self.close_animation = 0.0
                    return True

        return False

    def _advance_page(self, step: int) -> None:
        if not self.selected_doc:
            return
        cache = self.doc_cache.get(self.selected_doc, {})
        pages: List[pygame.Surface] = cache.get("pages", [])  # type: ignore[assignment]
        if not pages:
            return
        self.selected_page = (self.selected_page + step) % len(pages)

    def update(self, dt: float) -> None:
        # Placeholder for future animated flourishes (page flip etc.)
        if self.visible or self.closing:
            if self.visible and not self.closing:
                if self.grid_anim_total > 0:
                    self.time_active = min(self.time_active + dt, self.grid_anim_total)
            if self.closing:
                self.close_animation += dt
                duration = self.close_duration if self.close_duration else 0.25
                if self.close_animation >= duration:
                    if self.pending_mode == "grid":
                        self._return_to_grid()
                        self.closing = False
                        self.close_animation = 0.0
                        self.pending_mode = None
                        self.visible = True
                    else:
                        self.visible = False
                        self.closing = False
                        self.close_animation = 0.0
                        self.pending_mode = None
                        self._return_to_grid()

    def draw(self, screen: pygame.Surface) -> None:
        if self.visible:
            if self.mode == "grid":
                self._draw_grid_mode(screen)
            else:
                self._draw_document_mode(screen)

        if self.closing:
            self._draw_fadeout(screen)

    def _draw_grid_mode(self, screen: pygame.Surface) -> None:
        if not self.display_items:
            return

        start_x = int(self.GRID_START[0] * self.scale)
        start_y = int(self.GRID_START[1] * self.scale)
        screen_rect = screen.get_rect()
        max_width = (
            self.GRID_COLUMNS * (self.thumbnail_width + self.frame_padding * 2)
            + (self.GRID_COLUMNS - 1) * self.grid_padding
        )
        rows = (len(self.display_items) + self.GRID_COLUMNS - 1) // self.GRID_COLUMNS
        total_height = (
            rows * (self.thumbnail_height + self.frame_padding * 2)
            + max(0, rows - 1) * self.grid_padding
        )

        if start_x + max_width > screen_rect.width:
            start_x = max(screen_rect.width - max_width - int(20 * self.scale), int(20 * self.scale))
        if start_y + total_height > screen_rect.height:
            start_y = max(screen_rect.height - total_height - int(20 * self.scale), int(20 * self.scale))

        self.grid_bounds_rect = pygame.Rect(start_x, start_y, max_width, total_height)

        if self.grid_anim_duration <= 0:
            self.grid_anim_duration = 0.4
        if self.closing and self.pending_mode is None:
            anim_time = max(0.0, self.grid_anim_total - self.close_animation)
        else:
            anim_time = min(self.time_active, self.grid_anim_total)

        self.thumbnail_rects = []
        for idx, item in enumerate(self.display_items):
            row = idx // self.GRID_COLUMNS
            col = idx % self.GRID_COLUMNS

            frame_width = self.thumbnail_width + self.frame_padding * 2
            frame_height = self.thumbnail_height + self.frame_padding * 2
            x = start_x + col * (frame_width + self.grid_padding)
            y = start_y + row * (frame_height + self.grid_padding)

            delay = self.thumbnail_animations[idx]["delay"] if idx < len(self.thumbnail_animations) else 0.0
            progress = max(0.0, min(1.0, (anim_time - delay) / self.grid_anim_duration))
            eased = progress * progress * (3 - 2 * progress)

            current_width = max(1, int(frame_width * eased))
            current_height = max(1, int(frame_height * eased))
            offset_x = (frame_width - current_width) // 2
            offset_y = (frame_height - current_height) // 2

            frame_surface = pygame.Surface((current_width, current_height), pygame.SRCALPHA)
            base_color = (68, 72, 80, 170) if self.hover_index == idx else (52, 56, 64, 150)
            pygame.draw.rect(frame_surface, base_color, frame_surface.get_rect(), border_radius=22)
            pygame.draw.rect(frame_surface, (120, 124, 134), frame_surface.get_rect(), 2, border_radius=22)
            screen.blit(frame_surface, (x + offset_x, y + offset_y))

            cover: pygame.Surface = item.get("cover")  # type: ignore[assignment]
            cover_scaled = pygame.transform.smoothscale(
                cover,
                (
                    max(1, current_width - self.frame_padding * 2),
                    max(1, current_height - self.frame_padding * 2),
                ),
            )
            screen.blit(
                cover_scaled,
                (
                    x + offset_x + self.frame_padding,
                    y + offset_y + self.frame_padding,
                ),
            )

            thumb_rect = pygame.Rect(
                x + offset_x + self.frame_padding,
                y + offset_y + self.frame_padding,
                max(1, current_width - self.frame_padding * 2),
                max(1, current_height - self.frame_padding * 2),
            )
            self.thumbnail_rects.append(thumb_rect)

    def _draw_document_mode(self, screen: pygame.Surface) -> None:
        if not self.selected_doc:
            self.mode = "grid"
            return

        cache = self.doc_cache.get(self.selected_doc)
        if not cache:
            self.mode = "grid"
            return

        pages: List[pygame.Surface] = cache.get("pages", [])  # type: ignore[assignment]
        if not pages:
            self.mode = "grid"
            return

        screen_rect = screen.get_rect()
        overlay = pygame.Surface(screen_rect.size, pygame.SRCALPHA)
        for y in range(screen_rect.height):
            blend = y / max(1, screen_rect.height - 1)
            alpha = int(160 + 70 * blend)
            color = (12, 18, 32, alpha)
            pygame.draw.line(overlay, color, (0, y), (screen_rect.width, y))
        screen.blit(overlay, (0, 0))

        if self.zoomed:
            zoom_target_width = max(int(screen_rect.width * 0.8), 200)
            zoom_surface = self._get_zoom_scaled_surface(cache, self.selected_page, zoom_target_width)
            viewport_width = zoom_surface.get_width()
            viewport_height = min(zoom_surface.get_height(), int(screen_rect.height * 0.85))
            viewport_x = screen_rect.centerx - viewport_width // 2
            viewport_y = screen_rect.centery - viewport_height // 2
            self.paper_rect = pygame.Rect(viewport_x, viewport_y, viewport_width, viewport_height)

            self.zoom_scroll_max = max(0, zoom_surface.get_height() - viewport_height)
            self.zoom_scroll = max(0, min(self.zoom_scroll, self.zoom_scroll_max))

            source_rect = pygame.Rect(0, self.zoom_scroll, viewport_width, viewport_height)
            visible_surface = zoom_surface.subsurface(source_rect)

            shadow = pygame.Surface((viewport_width + int(100 * self.scale), viewport_height + int(100 * self.scale)), pygame.SRCALPHA)
            pygame.draw.rect(
                shadow,
                (0, 0, 0, 120),
                shadow.get_rect(),
                border_radius=int(40 * self.scale),
            )
            shadow_pos = (
                self.paper_rect.x - int(50 * self.scale),
                self.paper_rect.y - int(20 * self.scale),
            )
            screen.blit(shadow, shadow_pos)

            halo_rect = self.paper_rect.inflate(int(34 * self.scale), int(34 * self.scale))
            halo_surface = pygame.Surface(halo_rect.size, pygame.SRCALPHA)
            pygame.draw.rect(halo_surface, (80, 162, 205, 45), halo_surface.get_rect(), border_radius=32)
            pygame.draw.rect(halo_surface, (120, 198, 240, 120), halo_surface.get_rect(), 3, border_radius=32)
            screen.blit(halo_surface, halo_rect.topleft)

            screen.blit(visible_surface, self.paper_rect.topleft)
        else:
            page_surface_original = pages[self.selected_page]
            page_width, page_height = page_surface_original.get_size()

            target_width = max(int(screen_rect.width * 0.33), 200)
            scale_ratio = target_width / page_width
            page_width = int(page_width * scale_ratio)
            page_height = int(page_height * scale_ratio)
            page_surface = pygame.transform.smoothscale(
                page_surface_original, (page_width, page_height)
            )

            offset_left = int(50 * self.scale)
            offset_down = int((50 - 0) * self.scale)
            if self.thumbnail_rects:
                first_rect = self.thumbnail_rects[0]
                anchor_x = first_rect.left - offset_left
                anchor_y = first_rect.top + offset_down
            else:
                anchor_x = int(self.GRID_START[0] * self.scale) - offset_left
                anchor_y = int(self.GRID_START[1] * self.scale) + offset_down

            center_x = anchor_x + page_width // 2
            center_y = anchor_y + page_height // 2
            self.paper_rect = pygame.Rect(
                center_x - page_width // 2,
                center_y - page_height // 2,
                page_width,
                page_height,
            )

            shadow = pygame.Surface((page_width + int(60 * self.scale), page_height + int(60 * self.scale)), pygame.SRCALPHA)
            pygame.draw.ellipse(
                shadow,
                (0, 0, 0, 110),
                shadow.get_rect(),
            )
            shadow_pos = (
                self.paper_rect.centerx - shadow.get_width() // 2,
                self.paper_rect.bottom - int(40 * self.scale),
            )
            screen.blit(shadow, shadow_pos)

            halo_rect = self.paper_rect.inflate(int(34 * self.scale), int(34 * self.scale))
            halo_surface = pygame.Surface(halo_rect.size, pygame.SRCALPHA)
            pygame.draw.rect(halo_surface, (80, 162, 205, 55), halo_surface.get_rect(), border_radius=28)
            pygame.draw.rect(halo_surface, (120, 198, 240, 120), halo_surface.get_rect(), 3, border_radius=28)
            screen.blit(halo_surface, halo_rect.topleft)

            screen.blit(page_surface, self.paper_rect.topleft)
            self.zoom_scroll = 0
            self.zoom_scroll_max = 0

        self.close_rect = pygame.Rect(0, 0, 0, 0)

        button_width = max(int(400 * self.scale), 280)
        button_height = max(int(140 * self.scale), 80)
        control_y = self.paper_rect.bottom + int(42 * self.scale)
        if control_y + button_height > screen_rect.height - int(20 * self.scale):
            control_y = screen_rect.height - button_height - int(20 * self.scale)

        prev_rect = pygame.Rect(self.paper_rect.left, control_y, button_width, button_height)
        return_rect = pygame.Rect(self.paper_rect.centerx - button_width // 2, control_y, button_width, button_height)
        next_rect = pygame.Rect(self.paper_rect.right - button_width, control_y, button_width, button_height)

        self.nav_prev_rect = prev_rect
        self.nav_return_rect = return_rect
        self.nav_next_rect = next_rect

        self._draw_button_image(screen, prev_rect, self.button_prev_image)
        self._draw_button_image(screen, return_rect, self.button_library_image)
        self._draw_button_image(screen, next_rect, self.button_next_image)

# All utility functions and system classes are now imported from their respective modules
# See imports at top of file for details


# Main BBS Application
class GLYPHIS_IOBBS:
    def __init__(self):
        log_event("Initialising GLYPHIS_IO BBS client")
        # Start in fullscreen mode
        self.fullscreen = True
        self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        # Get actual screen dimensions
        self.screen_width = self.screen.get_width()
        self.screen_height = self.screen.get_height()
        pygame.display.set_caption("GLYPHIS_IO BBS")
        self.clock = pygame.time.Clock()
        
        # Baseline resolution and dimensions (2560x1440)
        # This is the reference resolution where the position and size were originally set
        self.baseline_width = BASELINE_WIDTH
        self.baseline_height = BASELINE_HEIGHT
        self.baseline_bbs_width = BBS_WIDTH
        self.baseline_bbs_height = BBS_HEIGHT
        self.baseline_bbs_x = BBS_X
        self.baseline_bbs_y = BBS_Y
        
        # Calculate scale factor based on current screen resolution
        # Use uniform scale to maintain aspect ratio (use minimum to ensure it fits)
        scale_x = self.screen_width / self.baseline_width
        scale_y = self.screen_height / self.baseline_height
        self.scale = min(scale_x, scale_y)  # Use minimum to maintain aspect ratio and fit on screen
        # Store scale as instance variable so we can use it for fonts, images, etc.
        
        # Scale the BBS window dimensions and position proportionally (maintaining aspect ratio)
        self.bbs_width = int(self.baseline_bbs_width * self.scale)
        self.bbs_height = int(self.baseline_bbs_height * self.scale)
        self.bbs_x = int(self.baseline_bbs_x * self.scale)
        self.bbs_y = int(self.baseline_bbs_y * self.scale)
        
        # General scroll offset for BBS window content (like a text document)
        # All content can be scrolled if it exceeds window height
        self.content_scroll_y = 0
        
        # Load desktop background with alpha support
        try:
            desktop_path = get_data_path("images", "desktop.png")
            self.desktop_bg = pygame.image.load(desktop_path).convert_alpha()
            # Scale desktop to fit screen if needed
            if self.desktop_bg.get_width() != self.screen_width or self.desktop_bg.get_height() != self.screen_height:
                self.desktop_bg = pygame.transform.scale(self.desktop_bg, (self.screen_width, self.screen_height))
        except Exception:
            print("Warning: images/desktop.png not found, using black background")
            self.desktop_bg = None
        
        # Create a surface for the BBS window (with alpha support for transparency)
        self.bbs_surface = pygame.Surface((self.bbs_width, self.bbs_height), pygame.SRCALPHA)
        
        # Load font (scaled based on resolution)
        try:
            self.font_large = pygame.font.Font(get_data_path("Retro Gaming.ttf"), int(30 * self.scale))
            self.font_medium = pygame.font.Font(get_data_path("Retro Gaming.ttf"), int(22 * self.scale))
            self.font_medium_small = pygame.font.Font(get_data_path("Retro Gaming.ttf"), max(1, int(20 * self.scale)))
            self.font_small = pygame.font.Font(get_data_path("Retro Gaming.ttf"), int(16 * self.scale))
            self.font_tiny = pygame.font.Font(get_data_path("Retro Gaming.ttf"), int(12 * self.scale))
        except:
            print("Warning: Retro Gaming.ttf not found, using default font")
            self.font_large = pygame.font.Font(None, int(30 * self.scale))
            self.font_medium = pygame.font.Font(None, int(22 * self.scale))
            self.font_medium_small = pygame.font.Font(None, max(1, int(20 * self.scale)))
            self.font_small = pygame.font.Font(None, int(16 * self.scale))
            self.font_tiny = pygame.font.Font(None, int(12 * self.scale))

        self.documentation_viewer = DocumentationViewer("Bradsonic_Docs", self.scale)
        self.start_video_playing = False
        self.start_video_cap = None
        self.start_video_frame = None
        self.start_video_rect = None
        self.start_video_timer = 0.0
        self.start_video_duration = 0.0
        
        # Game state
        self.state = "bbs_scroll"  # bbs_scroll, intro, loading, main_menu, module, compose, inbox, reading
        
        # BBS Scroll animation state
        self.scroll_image = None
        self.scroll_y = None  # Current scroll position (will be set to start below screen)
        self.scroll_speed = int(2 * self.scale)  # Pixels per frame (scaled)
        self.scroll_pause_frames = 0  # Frames remaining in pause
        self.scroll_pause_y = int(660 * self.scale)  # Y position where pause occurs (bottom of image, scaled)
        self.scroll_pause_triggered = False  # Track if pause has been triggered
        try:
            scroll_path = get_data_path("images", "BBS_Scroll.png")
            self.scroll_image = pygame.image.load(scroll_path).convert_alpha()
            # Scale image to fit BBS window width if needed
            if self.scroll_image.get_width() != self.bbs_width:
                scale_factor = self.bbs_width / self.scroll_image.get_width()
                new_height = int(self.scroll_image.get_height() * scale_factor)
                self.scroll_image = pygame.transform.scale(self.scroll_image, (self.bbs_width, new_height))
        except Exception:
            print("Warning: images/BBS_Scroll.png not found, skipping scroll animation")
            self.state = "intro"  # Skip to intro if image not found
        
        # Intro screen state
        self.intro_timer = 0
        self.intro_duration = 0  # No auto-advance, wait for keypress only
        
        # Loading screen state
        self.loading_progress = 0
        self.loading_complete = False
        
        # Main menu state
        self.current_module = 0  # Index of selected module
        self.modules = [
            "TERMINAL FEED: THE WALL",
            "EMAIL SYSTEM",
            "GAMES",
            "URGENT OPS",
            "TEAM INFO",
            "PIRATE RADIO",
            "LOGOUT"
        ]
        self.main_menu_message = ""
        self.main_menu_message_timer = 0
        self.module_token_requirements = {
            "EMAIL SYSTEM": Tokens.PSEM,
            "GAMES": Tokens.GAMES1,
            "URGENT OPS": Tokens.AUDIO1,
            "TEAM INFO": Tokens.TEAM_ACCESS,
            "PIRATE RADIO": Tokens.RADIO_ACCESS,
        }
        self.module_lock_messages = {
            "EMAIL SYSTEM": None,
            "GAMES": None,
            "URGENT OPS": None,
            "TEAM INFO": None,
            "PIRATE RADIO": None
        }

        # Token-driven unlock mappings
        self.email_token_rewards = {
            "glyphis_username_ack_001": {
                "tokens": [Tokens.GAMES1],
                "reason": "Glyphis onboarding acknowledgment read",
            },
            "uncle_am_audio_ops_001": {
                "tokens": [Tokens.AUDIO1, Tokens.LAPC1_BRIEF],
                "reasons": {
                    Tokens.AUDIO1: "Uncle-am audio ops briefing reviewed",
                    Tokens.LAPC1_BRIEF: "CRACKER IDE driver briefing received",
                },
            },
        }
        self.token_unlock_messages = {
            Tokens.GAMES1: "prototype library unlocked",
            Tokens.AUDIO1: "urgent ops dispatch unlocked",
            Tokens.LAPC1_BRIEF: "CRACKER IDE // LAPC-1 challenge ready",
        }
        
        # Email data
        self.inbox = []
        self.outbox = []
        self.sent = []
        self.player_email = "unknown"
        
        # NPC Responder - Enhanced trait-based system
        self.npc = EnhancedNPCResponder()
        
        # Token Inventory System
        self.inventory = TokenInventory()
        
        # Steam Integration
        self.steam = SteamManager(app_id=STEAM_APP_ID)
        
        # Terminal Feed (formerly Front Post Board)
        self.front_post_data = self.load_main_terminal_feed()
        self.posts = []
        self.active_post_signature = None

        # Email Database System
        self.email_db = EmailDatabase()
        self.user_state = self.load_user_state()
        self.apply_active_user_profile()
        self._email_check_counter = 0  # Counter for periodic email checks
        
        # Compose email fields
        self.compose_to = "glyphis@ciphernet.net"  # glyphis is the sysop
        self.compose_subject = ""
        self.compose_body = ""
        self.active_field = None  # subject, body, or send
        
        # Selected email
        self.selected_email = None
        self.previous_email_state = None  # Track which list we came from

        # User deletion confirmation modal
        self.delete_confirmation_active = False
        self.delete_confirmation_username = None

        # Email deletion confirmation modal
        self.delete_email_modal_active = False
        self.delete_email_source_list = None
        self.delete_email_index = None
        self.delete_email_origin_state = None
        
        # BBS window overlay state (for black rectangle overlay)
        self.bbs_overlay_active = False

        # OS Mode state
        self.os_mode_active = False
        self.os_mode = None  # Will be initialized when first activated

        # Logout confirmation modal
        self.logout_modal_active = False

        # Login workflow state
        self.login_input = ""
        self.login_error = ""
        self.login_message = ""
        self.login_focus = "input"
        
        # Load initial emails from database (emails with send_on_start = true)
        self.check_email_database()
        
        # Current post being viewed
        self.current_post = None
        
        # Scroll positions for long content
        self.email_scroll_y = 0  # Scroll position for email reading
        self.post_scroll_y = 0   # Scroll position for post reading
        self.bio_scroll_y = 0    # Scroll position for team bio

        # Game management
        self.game_definitions = GAME_DEFINITIONS
        self.current_game_index = 0
        self.active_game_session: Optional[BaseGameSession] = None
        
        # Load custom mouse cursors for outside BBS window (day and night versions)
        self.mouse_hand_cursor = self._load_hand_cursor("mouse-hand-pointer.png")
        self.mouse_hand_cursor_click = self._load_hand_cursor_click("mouse-hand-pointer-click.png")
        self.mouse_hand_cursor_night = self._load_hand_cursor("night-mouse-hand-pointer.png")
        self.mouse_hand_cursor_click_night = self._load_hand_cursor_click("night-mouse-hand-pointer-click.png")
        
        # Module content states
        self.current_task = 0
        self.urgent_ops_task_definitions = [
            {
                "id": "ops_lapc1_driver",
                "title": "Compile LAPC-1 Driver // CRACKER-PARROT IDE",
                "description": (
                    "Bring the RADLAND soundcard online. Implement the LAPC-1 assembly driver "
                    "so Uncle-am can route audio through the BBS stack."
                ),
                "token_required": Tokens.LAPC1_BRIEF,
                "launch_method": "_start_lapc1_driver_challenge",
                "status": "Press ENTER to launch the IDE.",
            },
        ]
        self.visible_ops_tasks: List[dict] = []
        self.active_ops_session = None
        self.ops_docs_overlay_image = None
        
        self.current_team_member = 0
        self.team_members = [
            {
                "handle": "glyphis",
                "role": "sysop",
                "tag": "[INTERNAL TEAM]",
                "bio": "GLYPHIS // SYSOP \"THE QUIET NODE\"\n\nI am the sysop.\n\nThe keeper of the lines.\n\nThe one who listens when no one else should.\n\nBefore this city was renamed, before the signs changed and the old words were forbidden, I worked behind terminals no one admits existed. Not military. Not civilian. Something in the cracks between them. Back when certain men believed information could still be caged.\n\nIt couldn't.\n\nI learned early that networks have ghosts. Faint traces of the people who built them, fought through them, hid inside them. Some of us never stopped drifting. Some of us never quite came back out.\n\nI've walked through systems that no longer appear on maps. I've seen archives that were never supposed to survive the fires. I've watched the same lie rewritten a dozen different ways. And every time the truth leaves a shadow long enough for someone to follow.\n\nIf you're here, you already know this: connections are dangerous. Not because of who uses them but because of who watches them.\n\nAnd sometimes I wonder when I scan these frequencies, when I patch the broken nodes, when I trace the quiet pulses from apartments just like yours whether the network remembers me too. Whether it still recognizes the ones who refused to disappear.\n\nThe sysop is not meant to take sides. Not meant to show fear.\n\nHe's meant to maintain the signal, keep the static low and ensure the doors stay open for those who still dare to step through.\n\nSo welcome to GLYPHIS_IO.\n\nWhatever you're looking for, truth, trouble or something in between, you'll find it here.\n\nI'll be watching.\n\nAlways."
            },
            {
                "handle": "rain",
                "role": "taskmaster",
                "tag": "[INTERNAL TEAM]",
                "bio": "RAIN // OPERATIONS COORDINATOR \"THE STATIC RUNNER\"\n\nHey, I'm Rain. I keep things moving around here. Glyphis handles the heavy quiet stuff but I handle the part you actually feel. The tasks, the ops, the late night panic messages when something breaks. If this place has a pulse I'm the one keeping it steady.\n\nI got into the underground early. I was the kid who poked systems just to see how far the wires ran. Banks, telecom nodes, a few locked government terminals that were supposed to be impossible. I never took anything. I just left little notes like a prankster breaking curfew. Half warning, half joke. They thought it was a whole crew. It was just me with cold tea and a cheap keyboard.\n\nI'm not the mysterious type and I know it. My room is a mess. I wear shirts inside out sometimes. I still get nervous before launching a big op. But when my fingers hit the keys everything lines up. The noise fades. The path clears. I can see exactly what needs to be done.\n\nI coordinate the urgent ops for Glyphis_IO. If you get a job, it probably came from me. If you complete it, I probably watched every packet like it was a firework. This network may look quiet but there are people out there who want cracks opened and locks lifted. They want to push back. They want to know what was erased from this city before we were even born.\n\nI try not to think too hard about what side I am on. Not yet. But I know this much. Something out there is wrong and someone has to do something about it. Maybe that someone is you. Maybe it is me. Or maybe it is all of us tripping over each other in the dark trying to rediscover a history none of us were allowed to learn.\n\nAnyway. If you need an op, I can make it happen.\n\nJust do me a favor and try not to get caught. I do enough worrying for both of us."
            },
            {
                "handle": "jaxkando",
                "role": "gamesmaster",
                "tag": "[INTERNAL TEAM]",
                "bio": "JAXKANDO // GAMESMASTER \"THE BUTTON MASHER WHO NEVER SLEEPS\"\n\nJAXKANDO HERE. ALL CAPS BECAUSE GAMES DESERVE IT. HACKING TOO, BUT MOSTLY GAMES.\n\nI reverse engineered the entire firmware of the Bradsonic Home Console in two weeks. Just because someone told me it was locked down. I proved it wasn't. Then I made it run a prototype shooter the devs swore could never run on that hardware. They sent me hate mail. I printed it and stuck it on my wall.\n\nI have cracked pretty much every protection system the big studios tried to put on their software. The ones made in the States, the ones rushed out in the Pacifica Isles, the ones built by companies that thought they understood security. They didn't. I showed them. I always show them.\n\nGames are my fuel. Games are the best thing humans ever invented. When I break a game open, I am not stealing it. I am freeing it. I am turning it into something anyone can explore. If you call that a crime, fine. I call it joy.\n\nI run the games module here. I design challenges, break hardware limits, push the emulator cores, and keep the scene alive. Because hacking should be fun. It should feel like plugging into something electric. Like you are learning a secret meant only for you.\n\nAnd yes, I may have crashed Bradsonic's main development server once. That was not planned. They got it back online. Eventually. I think.\n\nCOME PLAY GAMES WITH ME. THEY ARE BETTER WHEN YOU BREAK THEM FIRST."
            },
            {
                "handle": "uncle-am",
                "role": "pinky",
                "tag": "[INTERNAL TEAM]",
                "bio": "UNCLE-AM // RADIO ENGINEER \"THE FIRE IN THE STATIC\"\n\nuncle-am here. I'm the system's Pinky. I run the radio spine of this place. If a pirate broadcast cuts through the air in the Pacifica Isles you can bet it passed through one of my repeaters.\n\nI know the history they buried. The banned language, the stripped flags, the Shogun family propped up as a trophy. I know the names of the broadcasters who tried to fight it. Some are still locked away in the political prison in Hawaii. I send them signals when the noise is low.\n\nI wire terminals and rooftops and old telephone stations into a chain of digital repeaters. When one goes dark another lights up. Other BBS sysops try to do the same but the FBI raids are getting worse. Three boards shut down this month. One operator vanished.\n\nI am not here to make anyone feel safe. I am here to keep the truth alive. If a signal survives then the story survives with it.\n\nI broadcast from my grandmother's garage with car batteries and scrap parts. She thinks I am doing homework. I am sending banned history across half the country.\n\nIf you can hear this you are part of the fight whether you want to be or not.\n\nI am Uncle-AM. My signal stays open."
            }
        ]
        
        # Radio state
        self.radio_playing = False
        self.current_track = "Static Transmission - Frequency Unknown"
        self.dj_text = [
            "You're listening to the underground frequency...",
            "The truth is out there, if you know where to look...",
            "Trust no one. Question everything...",
            "The network sees all, but who watches the watchers?"
        ]
        self.dj_index = 0
        
        # Video playback state (default mode, fallback to normal if unavailable)
        self.video_cap = None
        self.video_frame = None
        self.scanline_image = None
        self.desktop_video_filename: Optional[str] = None
        self.desktop_state = "default"
        
        # Load video and scanline if available (video mode is default)
        if _cv2_available:
            # Use time-aware video selection (daytime/nighttime based on Tokyo time)
            base_video = "desktop_steam.mp4"
            time_aware_video = _get_time_aware_video_name(base_video)
            self._set_desktop_video(time_aware_video)
        
        # Load scanline overlay
        try:
            scanline_path = get_data_path("images", "scanline.png")
            self.scanline_image = pygame.image.load(scanline_path).convert_alpha()
        except Exception:
            print("Warning: images/scanline.png not found")
            self.scanline_image = None
        
        # Initialize audio mixer for ambient track
        try:
            if not pygame.mixer.get_init():
                try:
                    pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
                    print("DEBUG: Mixer initialized successfully for ambient track")
                except Exception as mixer_error:
                    print(f"Warning: Unable to initialize mixer for ambient track: {mixer_error}")
                    self.ambient_sound = None
                    self.ambient_channel = None
                    return
            else:
                print(f"DEBUG: Mixer already initialized: {pygame.mixer.get_init()}")
            
            # Load ambient track (window-loop.wav)
            ambient_path = get_data_path("Audio", "window-loop.wav")
            print(f"DEBUG: Looking for ambient audio file at: {ambient_path}")
            print(f"DEBUG: File exists: {os.path.exists(ambient_path)}")
            
            if os.path.exists(ambient_path):
                try:
                    self.ambient_sound = pygame.mixer.Sound(ambient_path)
                    print(f"DEBUG: Ambient sound loaded successfully: {self.ambient_sound}")
                    # Start playing immediately - this is room ambiance, not BBS audio
                    # Initialize fade-in variables
                    self.ambient_fade_in = False
                    self.ambient_fade_start_time = None
                    self.ambient_fade_duration = 3.0  # 3 seconds fade-in
                    try:
                        # Ensure mixer is initialized before playing
                        if not pygame.mixer.get_init():
                            pygame.mixer.init()
                        print("DEBUG: Starting ambient room track immediately with fade-in")
                        self.ambient_channel = self.ambient_sound.play(loops=-1)  # Loop indefinitely
                        if self.ambient_channel:
                            self.ambient_channel.set_volume(0.0)  # Start at 0 for fade-in
                            self.ambient_playing = True
                            self.ambient_fade_in = True
                            self.ambient_fade_start_time = pygame.time.get_ticks() / 1000.0
                            print("DEBUG: Ambient room track started, fade-in beginning at volume 0.0")
                        else:
                            print("DEBUG: Warning: play() returned None, no channel available")
                            self.ambient_playing = False
                    except Exception as play_error:
                        print(f"Warning: Failed to start ambient room track: {play_error}")
                        import traceback
                        traceback.print_exc()
                        self.ambient_channel = None
                        self.ambient_playing = False
                except Exception as sound_error:
                    print(f"Warning: Failed to load window-loop.wav: {sound_error}")
                    self.ambient_sound = None
                    self.ambient_channel = None
                    self.ambient_playing = False
            else:
                print(f"Warning: Audio/window-loop.wav not found at {ambient_path}")
                self.ambient_sound = None
                self.ambient_channel = None
        except Exception as e:
            print(f"Warning: Failed to initialize ambient audio: {e}")
            import traceback
            traceback.print_exc()
            self.ambient_sound = None
            self.ambient_channel = None
        
        
    def _wrap_text(self, text, font, max_width):
        """Helper to wrap text into lines, returns list of lines. Preserves double newlines as blank lines."""
        if text is None:
            return []
        
        # First split by newlines to preserve paragraph structure and consecutive newlines
        paragraphs = text.split('\n')
        lines = []
        
        for para_idx, paragraph in enumerate(paragraphs):
            # Empty paragraph means a blank line (from \n\n)
            if paragraph == "":
                lines.append("")
                continue
            
            # Wrap this paragraph
            words = paragraph.split(' ')
            current_line = []
            
            for word in words:
                if not word:  # Skip empty strings from multiple spaces
                    continue
                    
                test_line = ' '.join(current_line + [word]) if current_line else word
                if font.size(test_line)[0] <= max_width:
                    current_line.append(word)
                else:
                    if current_line:
                        lines.append(' '.join(current_line))
                    current_line = [word]
            
            if current_line:
                lines.append(' '.join(current_line))
        
        return lines
    
    def draw_text(self, text, font, color, x, y, max_width=None):
        """Draw text with optional word wrapping - flows like a document"""
        # Apply scroll offset (allows scrolling if content exceeds window)
        y = y + self.content_scroll_y
        if text is None:
            return y - self.content_scroll_y
        if max_width is None:
            surface = font.render(text, True, color)
            self.bbs_surface.blit(surface, (x, y))
            return y + surface.get_height() - self.content_scroll_y  # Return position without scroll offset
        else:
            lines = self._wrap_text(text, font, max_width)
            
            y_offset = y
            for line in lines:
                surface = font.render(line, True, color)
                self.bbs_surface.blit(surface, (x, y_offset))
                y_offset += surface.get_height() + 5
            
            return y_offset - self.content_scroll_y  # Return position without scroll offset
    
    def _load_hand_cursor(self, filename: str) -> Optional[pygame.cursors.Cursor]:
        """Load a hand cursor image with hotspot at top-left corner"""
        path = get_data_path("images", filename)
        try:
            image = pygame.image.load(path).convert_alpha()
            # Don't scale - use original size for cursor
            # Hotspot is at top-left corner (0, 0)
            try:
                return pygame.cursors.Cursor((0, 0), image)
            except Exception:
                return None
        except Exception:
            return None
    
    def _load_hand_cursor_click(self, filename: str) -> Optional[pygame.cursors.Cursor]:
        """Load a hand cursor click image with hotspot at top-left corner"""
        path = get_data_path("images", filename)
        try:
            image = pygame.image.load(path).convert_alpha()
            # Don't scale - use original size for cursor
            # Hotspot is at top-left corner (0, 0)
            try:
                return pygame.cursors.Cursor((0, 0), image)
            except Exception:
                return None
        except Exception:
            return None
    
    def _is_mouse_in_bbs_window(self) -> bool:
        """Check if mouse is inside the BBS window"""
        mouse_x, mouse_y = pygame.mouse.get_pos()
        return (self.bbs_x <= mouse_x < self.bbs_x + self.bbs_width and
                self.bbs_y <= mouse_y < self.bbs_y + self.bbs_height)
    
    def _update_cursor(self) -> None:
        """Update cursor based on mouse position and game state"""
        # If a game session is active, let the game handle cursor
        if self.state == "game_session" and self.active_game_session:
            return  # Game will handle its own cursor
        
        # Check if mouse is inside BBS window
        if self._is_mouse_in_bbs_window():
            # Hide cursor inside BBS window
            try:
                # Create a transparent cursor to hide it
                blank_cursor = pygame.cursors.Cursor((0, 0), pygame.Surface((1, 1), pygame.SRCALPHA))
                pygame.mouse.set_cursor(blank_cursor)
            except Exception:
                pass
        else:
            # Show custom hand cursor outside BBS window
            # Use night versions if it's nighttime, otherwise use day versions
            is_night = _is_tokyo_nighttime()
            mouse_buttons = pygame.mouse.get_pressed()
            
            if is_night:
                # Use night cursor versions
                if mouse_buttons[0] and self.mouse_hand_cursor_click_night:
                    cursor_to_use = self.mouse_hand_cursor_click_night
                else:
                    cursor_to_use = self.mouse_hand_cursor_night
            else:
                # Use day cursor versions
                if mouse_buttons[0] and self.mouse_hand_cursor_click:
                    cursor_to_use = self.mouse_hand_cursor_click
                else:
                    cursor_to_use = self.mouse_hand_cursor
            
            if cursor_to_use:
                try:
                    pygame.mouse.set_cursor(cursor_to_use)
                except Exception:
                    pass
    
    def _reset_to_beginning(self) -> None:
        """Reset the BBS back to the beginning of the game loop"""
        # Reset game state to initial scroll animation
        self.state = "bbs_scroll"
        
        # Reset scroll animation state
        self.scroll_y = None  # Will be set to start below screen
        self.scroll_pause_frames = 0
        self.scroll_pause_triggered = False
        
        # Reset intro state
        self.intro_timer = 0
        
        # Reset content scroll positions
        self.content_scroll_y = 0
        self.email_scroll_y = 0
        self.post_scroll_y = 0
        self.bio_scroll_y = 0
        
        # Reset module selection
        self.current_module = 0
        
        # Close any active sessions
        if self.active_game_session:
            self.active_game_session.exit()
            self.active_game_session = None
        
        if self.active_ops_session:
            self._end_ops_session()
        
        # Reset modals
        self.delete_confirmation_active = False
        self.logout_modal_active = False
        self.delete_email_modal_active = False
        
        log_event("BBS reset to beginning")
    
    def draw_line(self, y, x1=50, x2=None):
        """Draw a horizontal separator line"""
        # Apply scroll offset (allows scrolling if content exceeds window)
        y = y + self.content_scroll_y
        if x2 is None:
            x2 = self.bbs_width - 50
        pygame.draw.line(self.bbs_surface, DARK_BLUE, (x1, y), (x2, y), 2)

    def _set_desktop_video(self, filename: str) -> None:
        """Load or switch the desktop background video."""
        if not _cv2_available:
            return

        filename = filename.strip()
        if not filename:
            return

        if self.desktop_video_filename == filename and self.video_cap:
            return

        video_path = get_data_path("videos", filename)

        new_capture = None
        try:
            new_capture = cv2.VideoCapture(video_path)
            if not new_capture.isOpened():
                print(f"Warning: {video_path} not found or could not be opened, using normal mode")
                new_capture.release()
                return
        except Exception as exc:
            if new_capture:
                new_capture.release()
            print(f"Warning: Could not load {video_path}: {exc}, using normal mode")
            return

        if self.video_cap:
            self.video_cap.release()

        self.video_cap = new_capture
        self.desktop_video_filename = filename
        self.video_frame = None
        self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

    def _is_audio_power_led_green(self) -> bool:
        """Check the urgent ops session for the C400 power LED state."""
        session = self.active_ops_session
        if not session:
            return False

        power_checker = getattr(session, "is_c400_power_led_on", None)
        if not callable(power_checker):
            return False

        try:
            return bool(power_checker())
        except Exception:
            return False

    def _update_audio_power_state(self) -> None:
        """Maintain the desktop video state based on CRACKER IDE audio playback and time of day."""
        # Check if CRACKER IDE audio is playing (from Urgent_Ops/Audio folder)
        cracker_audio_playing = False
        if self.state == "urgent_ops_session" and self.active_ops_session:
            audio_checker = getattr(self.active_ops_session, "is_cracker_ide_audio_playing", None)
            if callable(audio_checker):
                try:
                    cracker_audio_playing = bool(audio_checker())
                except Exception:
                    cracker_audio_playing = False
        
        desired_state = "audio-playing" if cracker_audio_playing else "default"
        
        # Determine base video filename based on state
        if desired_state == "audio-playing":
            base_video = "Audio-Desktop.mp4"
        else:
            base_video = "desktop_steam.mp4"
        
        # Get time-aware video name (adds 'night-' prefix if nighttime in Tokyo)
        time_aware_video = _get_time_aware_video_name(base_video)
        
        # Only update if state changed OR if time of day changed (video filename changed)
        if desired_state != self.desktop_state or time_aware_video != self.desktop_video_filename:
            self.desktop_state = desired_state
            self._set_desktop_video(time_aware_video)

    # ------------------------------------------------------------------
    # Game registry helpers
    # ------------------------------------------------------------------

    def _get_unlocked_games(self) -> List[GameDefinition]:
        tokens = getattr(self.inventory, "tokens", set())
        available: List[GameDefinition] = []
        for definition in self.game_definitions:
            if all(token.upper() in tokens for token in definition.tokens_required):
                available.append(definition)
        if available:
            self.current_game_index = max(0, min(self.current_game_index, len(available) - 1))
        else:
            self.current_game_index = 0
            # Fallback: if core games token is present but definitions didn't match
            if self.inventory.has_token(Tokens.GAMES1):
                available = [
                    definition
                    for definition in self.game_definitions
                    if Tokens.GAMES1 in definition.tokens_required
                ]
        return available

    def launch_game(self, definition: GameDefinition) -> None:
        if definition.type == "external":
            self._show_external_launch_message(definition.title)
            try:
                launch_external_game(definition)
            except RuntimeError as exc:
                log_event(str(exc))
                self.show_main_menu_message("Unable to launch external prototype.")
            else:
                self.show_main_menu_message(f"{definition.title} closed.")
            return

        if not definition.session_factory:
            self.show_main_menu_message("Game session unavailable.")
            return

        self.active_game_session = definition.session_factory(self)
        self.state = "game_session"
        self.active_game_session.enter()

    def end_game_session(self) -> None:
        if self.active_game_session:
            self.active_game_session.exit()
        self.active_game_session = None
        self.state = "games"

    def _show_external_launch_message(self, title: str) -> None:
        self.bbs_surface.fill(BLACK)
        header = self.font_medium.render(f"Launching {title}...", True, CYAN)
        sub = self.font_small.render("The BBS will resume when the prototype window closes.", True, DARK_CYAN)
        self.bbs_surface.blit(header, (int(50 * self.scale), int(80 * self.scale)))
        self.bbs_surface.blit(sub, (int(50 * self.scale), int(130 * self.scale)))

        self.screen.fill(BLACK)
        self.screen.blit(self.bbs_surface, (self.bbs_x, self.bbs_y))
        pygame.display.flip()
    
    def check_email_database(self):
        """Check email database for new emails based on tokens and add them to inbox"""
        new_emails = self.email_db.check_and_send_emails(self.inventory, self.player_email)
        for email in new_emails:
            self.inbox.append(email)
        # Save sent email IDs
        if new_emails:
            self.save_user_state()
    
    def draw_bbs_scroll(self):
        """Draw the BBS scroll animation"""
        self.bbs_surface.fill(BLACK)
        
        if self.scroll_image:
            # Initialize scroll position if not set (start image below the visible area)
            if self.scroll_y is None:
                img_height = self.scroll_image.get_height()
                self.scroll_y = self.bbs_height  # Start at bottom of window
            
            # Get image dimensions
            img_height = self.scroll_image.get_height()
            
            # Calculate bottom of image
            image_bottom = self.scroll_y + img_height
            
            # Check if we're in pause state
            if self.scroll_pause_frames > 0:
                # Pause - don't scroll, just draw
                self.bbs_surface.blit(self.scroll_image, (0, self.scroll_y))
                self.scroll_pause_frames -= 1
                # After pause completes, end animation
                if self.scroll_pause_frames == 0:
                    self.state = "intro"
                    self.scroll_y = None
                    self.scroll_pause_frames = 0
                    self.scroll_pause_triggered = False
            else:
                # Draw the scroll image at the current scroll position
                # Image scrolls upward (classic BBS style - content appears from bottom)
                self.bbs_surface.blit(self.scroll_image, (0, self.scroll_y))
                
                # Check if bottom of image has reached or just passed the pause line
                # Only trigger once, when the bottom reaches 868 or below
                if not self.scroll_pause_triggered and image_bottom <= self.scroll_pause_y:
                    # Start pause - set to 20 frames
                    self.scroll_pause_frames = 20
                    self.scroll_pause_triggered = True
                else:
                    # Update scroll position (scroll upward) only if not paused
                    if not self.scroll_pause_triggered:
                        self.scroll_y -= self.scroll_speed
                    
                    # Check if scroll is complete (image has scrolled completely off the top)
                    # This is a fallback in case pause doesn't trigger
                    if self.scroll_y + img_height <= 0:
                        self.state = "intro"
                        self.scroll_y = None
                        self.scroll_pause_frames = 0
                        self.scroll_pause_triggered = False
        else:
            # If no image, skip directly to intro
            self.state = "intro"
    
    def draw_intro_screen(self):
        """Draw the intro screen with ANSI art"""
        self.bbs_surface.fill(BLACK)
        
        # ANSI art for "GLYPHIS"
        # Using monospace rendering for proper alignment
        ascii_art = [
            " _____ _             _     _       _       ",
            "|  __ \\ |           | |   (_)     (_)      ",
            "| |  \\/ |_   _ _ __ | |__  _ ___   _  ___ ",
            "| | __| | | | | '_ \\| '_ \\| / __| | |/ _ \\",
            "| |_\\ \\ | |_| | |_) | | | | \\__ \\ | | (_) |",
            " \\____/_|\\__, | .__/|_| |_|_|___/ |_|\\___/",
            "          __/ | |                          ",
            "         |___/|_|                          "
        ]
        
        # Use a monospace font for ASCII art to ensure proper alignment
        try:
            # Try Courier New or similar monospace font (scaled)
            ascii_font = pygame.font.SysFont("courier", int(16 * self.scale))
        except:
            try:
                # Fallback to Retro Gaming if Courier not available
                ascii_font = pygame.font.Font(get_data_path("Retro Gaming.ttf"), int(16 * self.scale))
            except:
                # Final fallback
                ascii_font = self.font_small
        
        # Draw ASCII art - center it vertically and horizontally (scaled)
        start_y = int(120 * self.scale)
        line_height = int(24 * self.scale)
        
        for i, line in enumerate(ascii_art):
            # Calculate x position to center
            text_width = ascii_font.size(line)[0]
            x_pos = (self.bbs_width - text_width) // 2
            y_pos = start_y + (i * line_height)
            
            # Render with cyan color
            text_surface = ascii_font.render(line, True, CYAN)
            # Apply scroll offset (allows scrolling if content exceeds window)
            self.bbs_surface.blit(text_surface, (x_pos, y_pos + self.content_scroll_y))
        
        # "WELCOME TO OUR BBS" text below the art
        welcome_y = start_y + (len(ascii_art) * line_height) + int(30 * self.scale)
        welcome_text = "WELCOME TO OUR BBS"
        welcome_width = self.font_medium.size(welcome_text)[0]
        welcome_x = (self.bbs_width - welcome_width) // 2
        self.draw_text(welcome_text, self.font_medium, CYAN, welcome_x, welcome_y)
        
        # Subtitle - next line under welcome
        subtitle_y = welcome_y + int(35 * self.scale)
        subtitle_text = "ROOT ACCESS FOR THE FORGOTTEN"
        subtitle_width = self.font_small.size(subtitle_text)[0]
        subtitle_x = (self.bbs_width - subtitle_width) // 2
        self.draw_text(subtitle_text, self.font_small, DARK_CYAN, subtitle_x, subtitle_y)
        
        # System operators list
        sysop_y = subtitle_y + int(50 * self.scale)
        sysop_lines = [
            "sysop: glyphis",
            "taskmaster: rain",
            "gamesmaster: jaxkando",
            "pinky: uncle-am"
        ]
        
        for line in sysop_lines:
            line_width = self.font_small.size(line)[0]
            line_x = (self.bbs_width - line_width) // 2
            self.draw_text(line, self.font_small, DARK_CYAN, line_x, sysop_y)
            sysop_y += int(25 * self.scale)
        
        # Instructions at bottom
        instruction_y = self.bbs_height - int(50 * self.scale)
        instruction_text = "Press any key to continue..."
        instruction_width = self.font_small.size(instruction_text)[0]
        instruction_x = (self.bbs_width - instruction_width) // 2
        self.draw_text(instruction_text, self.font_small, DARK_CYAN, instruction_x, instruction_y)
    
    def draw_loading_screen(self):
        """Draw the BBS connection/loading screen"""
        self.bbs_surface.fill(BLACK)
        
        # Title - centered (scaled)
        title_text = "GLYPHIS_IO BBS"
        title_width = self.font_large.size(title_text)[0]
        title_x = (self.bbs_width - title_width) // 2
        self.draw_text(title_text, self.font_large, CYAN, title_x, int(180 * self.scale))
        
        # Connecting text - centered (scaled)
        connecting_text = "CONNECTING TO NETWORK..."
        connecting_width = self.font_medium.size(connecting_text)[0]
        connecting_x = (self.bbs_width - connecting_width) // 2
        self.draw_text(connecting_text, self.font_medium, CYAN, connecting_x, int(230 * self.scale))
        
        # Loading bar - centered, scaled to window
        bar_width = min(int(600 * self.scale), self.bbs_width - int(100 * self.scale))  # Max 600px scaled, but fit within window
        bar_height = int(30 * self.scale)
        bar_x = (self.bbs_width - bar_width) // 2
        bar_y = int(280 * self.scale)  # Adjusted for better centering (scaled)
        
        # Draw bar outline
        pygame.draw.rect(self.bbs_surface, DARK_BLUE, (bar_x, bar_y + self.content_scroll_y, bar_width, bar_height), 2)
        
        # Draw progress
        if self.loading_progress > 0:
            progress_width = int(bar_width * (self.loading_progress / 100))
            pygame.draw.rect(self.bbs_surface, CYAN, (bar_x, bar_y + self.content_scroll_y, progress_width, bar_height))
        
        # Status text - centered
        if self.loading_progress < 30:
            status = "Establishing connection..."
        elif self.loading_progress < 60:
            status = "Authenticating credentials..."
        elif self.loading_progress < 90:
            status = "Loading modules..."
        else:
            status = "Connection established!"
        
        status_width = self.font_small.size(status)[0]
        status_x = (self.bbs_width - status_width) // 2
        self.draw_text(status, self.font_small, DARK_CYAN, status_x, int(330 * self.scale))
        
        # Progress percentage - centered (scaled)
        progress_text = f"{int(self.loading_progress)}%"
        progress_width = self.font_small.size(progress_text)[0]
        progress_x = (self.bbs_width - progress_width) // 2
        self.draw_text(progress_text, self.font_small, CYAN, progress_x, int(360 * self.scale))
        
        # Update loading progress
        if not self.loading_complete:
            self.loading_progress += 0.5
            if self.loading_progress >= 100:
                self.loading_progress = 100
                self.loading_complete = True
                # Wait a moment then switch to Terminal Feed
                pygame.time.wait(500)
                self.state = "front_post"
                self.current_module = 0
                self.current_post = None
                self.refresh_main_terminal_feed()
    
    def _draw_background_grid(self):
        stripe_step = max(10, int(24 * self.scale))
        for offset in range(0, self.bbs_height, stripe_step):
            pygame.draw.line(self.bbs_surface, GRID_BLUE, (0, offset), (self.bbs_width, offset), 1)

    def _draw_header_panel(self, title, instructions=None):
        instruction_count = len(instructions) if instructions else 0
        # Check if first instruction is actually a subtitle (for THE WALL)
        has_subtitle = instructions and len(instructions) > 0 and instructions[0] and instructions[0].isupper() and len(instructions[0]) < 20
        if has_subtitle:
            # Subtitle takes up space like a title line
            header_height = int(90 * self.scale) + (instruction_count - 1) * int(20 * self.scale)
        else:
            header_height = int(70 * self.scale) + instruction_count * int(20 * self.scale)
        
        header_rect = pygame.Rect(
            int(40 * self.scale),
            int(30 * self.scale),
            self.bbs_width - int(80 * self.scale),
            header_height,
        )
        pygame.draw.rect(self.bbs_surface, PANEL_BLUE, header_rect)
        pygame.draw.rect(self.bbs_surface, CYAN, header_rect, 2)
        
        # Main title - wrap if needed
        max_title_width = header_rect.width - int(40 * self.scale)
        title_wrapped = self._wrap_text(title, self.font_large, max_title_width)
        title_y = header_rect.y + int(8 * self.scale)
        if title_wrapped:
            for idx, line in enumerate(title_wrapped):
                self.draw_text(
                    line,
                    self.font_large,
                    ACCENT_CYAN,
                    header_rect.x + int(20 * self.scale),
                    title_y + idx * int(28 * self.scale),
                )
        
        if instructions:
            if has_subtitle:
                # First instruction is a subtitle - render as second title line
                subtitle_y = title_y + int(32 * self.scale)
                subtitle_wrapped = self._wrap_text(instructions[0], self.font_large, max_title_width)
                if subtitle_wrapped:
                    for idx, line in enumerate(subtitle_wrapped):
                        self.draw_text(
                            line,
                            self.font_large,
                            ACCENT_CYAN,
                            header_rect.x + int(20 * self.scale),
                            subtitle_y + idx * int(28 * self.scale),
                        )
                # Remaining instructions are actual instructions
                base_y = subtitle_y + int(35 * self.scale)
                line_height = int(18 * self.scale)
                for idx, line in enumerate(instructions[1:], start=0):
                    self.draw_text(
                        line,
                        self.font_tiny,
                        DARK_CYAN,
                        header_rect.x + int(20 * self.scale),
                        base_y + idx * line_height,
                    )
            else:
                # All instructions are regular instructions
                base_y = header_rect.y + int(48 * self.scale)
                line_height = int(18 * self.scale)
                for idx, line in enumerate(instructions):
                    self.draw_text(
                        line,
                        self.font_tiny,
                        DARK_CYAN,
                        header_rect.x + int(20 * self.scale),
                        base_y + idx * line_height,
                    )
        return header_rect

    def _draw_panel_layout(self, header_rect, include_info=True, left_ratio=0.58):
        panel_margin = int(40 * self.scale)
        panel_top = header_rect.bottom + int(20 * self.scale)
        panel_height = self.bbs_height - panel_top - int(120 * self.scale)
        panel_height = max(panel_height, int(150 * self.scale))
        panel_width = self.bbs_width - panel_margin * 2

        if include_info:
            left_width = int(panel_width * left_ratio)
            modules_rect = pygame.Rect(panel_margin, panel_top, left_width, panel_height)
            spacing = int(16 * self.scale)
            info_rect = pygame.Rect(
                modules_rect.right + spacing,
                panel_top,
                panel_width - left_width - spacing,
                panel_height,
            )
            pygame.draw.rect(self.bbs_surface, PANEL_BLUE, info_rect)
            pygame.draw.rect(self.bbs_surface, BLUE, info_rect, 2)
        else:
            modules_rect = pygame.Rect(panel_margin, panel_top, panel_width, panel_height)
            info_rect = None

        pygame.draw.rect(self.bbs_surface, PANEL_BLUE, modules_rect)
        pygame.draw.rect(self.bbs_surface, CYAN, modules_rect, 2)
        return modules_rect, info_rect

    def _prepare_bbs_screen(self, title, instructions=None, include_info=True, left_ratio=0.58):
        self.bbs_surface.fill(BLACK)
        self._draw_background_grid()
        header_rect = self._draw_header_panel(title, instructions)
        modules_rect, info_rect = self._draw_panel_layout(header_rect, include_info=include_info, left_ratio=left_ratio)
        return header_rect, modules_rect, info_rect

    def _draw_footer_status(self):
        footer_y = self.bbs_height - int(60 * self.scale)
        self.draw_line(footer_y)
        self.draw_text(f"USER: {self.player_email}", self.font_small, CYAN, int(50 * self.scale), footer_y + int(10 * self.scale))
        self.draw_text("SYSTEM STATUS: ONLINE", self.font_small, CYAN, int(50 * self.scale), footer_y + int(30 * self.scale))

    def draw_main_menu(self):
        """Draw the main BBS menu"""
        self.content_scroll_y = 0
        _, modules_rect, info_rect = self._prepare_bbs_screen(
            "GLYPHIS_IO BBS // ACCESS NODE",
            ["TAB: cycle modules   ENTER: engage   ESC: dismiss to desktop"],
            include_info=True,
        )

        email_unread_count = len([e for e in self.inbox if not e.read])

        self.draw_text(
            "[ MODULE ACCESS ]",
            self.font_small,
            ACCENT_CYAN,
            modules_rect.x + int(20 * self.scale),
            modules_rect.y + int(20 * self.scale),
        )

        y = modules_rect.y + int(60 * self.scale)
        row_height = max(int(46 * self.scale), 32)

        for i, module in enumerate(self.modules):
            locked = self.is_module_locked(module)
            base_label = module
            if module == "EMAIL SYSTEM" and email_unread_count > 0:
                base_label = f"{module} ({email_unread_count})"
            label = base_label + (" (LOCKED)" if locked else "")
            module_font = self.font_medium_small if module == "TERMINAL FEED: THE WALL" else self.font_medium
            entry_rect = pygame.Rect(
                modules_rect.x + int(16 * self.scale),
                y - int(10 * self.scale),
                modules_rect.width - int(32 * self.scale),
                row_height,
            )
            if i == self.current_module:
                pygame.draw.rect(self.bbs_surface, HIGHLIGHT_BLUE, entry_rect)
                pygame.draw.rect(self.bbs_surface, ACCENT_CYAN, entry_rect, 2)
                color = RED if locked else WHITE
                tag = "[>]"
            else:
                pygame.draw.rect(self.bbs_surface, PANEL_BLUE, entry_rect, 1)
                color = RED if locked else DARK_CYAN
                tag = "[ ]"

            text_x = entry_rect.x + int(14 * self.scale)
            self.draw_text(f"{tag} {label}", module_font, color, text_x, y)
            y += row_height

        if info_rect:
            info_x = info_rect.x + int(20 * self.scale)
            info_y = info_rect.y + int(20 * self.scale)

            self.draw_text("[ SESSION TELEMETRY ]", self.font_small, ACCENT_CYAN, info_x, info_y)
            info_y += int(35 * self.scale)
            self.draw_text(f"CURRENT USER: {self.player_email}", self.font_small, CYAN, info_x, info_y)
            info_y += int(28 * self.scale)
            self.draw_text("SYS CLOCK:", self.font_small, ACCENT_CYAN, info_x, info_y)
            info_y += int(24 * self.scale)
            self.draw_text(format_ingame_clock(), self.font_small, CYAN, info_x, info_y)
            info_y += int(28 * self.scale)
            self.draw_text("[ INTERNAL COMMS ]", self.font_small, ACCENT_CYAN, info_x, info_y)
            info_y += int(28 * self.scale)
            unread = len([e for e in self.inbox if not e.read])
            unread_text = f"UNREAD MAIL: {unread}" if unread else "UNREAD MAIL: --"
            self.draw_text(unread_text, self.font_small, CYAN, info_x, info_y)
            info_y += int(28 * self.scale)
            if hasattr(self, "wall_posts"):
                unread_wall = len([post for post in self.wall_posts if not post.get("read", False)])
            else:
                unread_wall = 0
            unread_wall_text = f"UNREAD WALL: {unread_wall}" if unread_wall else "UNREAD WALL: --"
            self.draw_text(unread_wall_text, self.font_small, CYAN, info_x, info_y)
            info_y += int(28 * self.scale)
            self.draw_text("[ ACTIVE OPS ]", self.font_small, ACCENT_CYAN, info_x, info_y)
            info_y += int(28 * self.scale)
            available_games = 0
            try:
                available_games = len(self._get_unlocked_games())
            except Exception:
                available_games = 0
            games_locked = not getattr(self.inventory, "has_token", lambda *_: False)(Tokens.GAMES1)
            self.draw_text(
                f"CRACKED GAMES: {available_games}" if available_games else "CRACKED GAMES: --",
                self.font_small,
                RED if games_locked else CYAN,
                info_x,
                info_y,
            )
            info_y += int(28 * self.scale)
            urgent_count = len(self.urgent_ops_task_definitions or [])
            self.draw_text(
                f"URGENT OPS: {urgent_count}" if urgent_count else "URGENT OPS: --",
                self.font_small,
                CYAN if urgent_count else RED,
                info_x,
                info_y,
            )
            info_y += int(28 * self.scale)
            self.draw_text("[ EXTERNAL COMMS ]", self.font_small, ACCENT_CYAN, info_x, info_y)
            info_y += int(28 * self.scale)
            station = getattr(self, "current_frequency", None)
            radio_unlocked = getattr(self.inventory, "has_token", lambda *_: False)(Tokens.RADIO_ACCESS)
            station_text = f"RADIO TUNED: {station} kHz" if station else "RADIO TUNED: -- kHz"
            self.draw_text(station_text, self.font_small, CYAN if radio_unlocked and station else RED, info_x, info_y)
            info_y += int(28 * self.scale)

        self._draw_footer_status()

        if self.main_menu_message_timer > 0 and self.main_menu_message:
            footer_y = self.bbs_height - int(60 * self.scale)
            message_y = footer_y - int(40 * self.scale)
            self.draw_text(self.main_menu_message, self.font_small, RED, int(50 * self.scale), message_y)
            self.main_menu_message_timer -= 1
            if self.main_menu_message_timer <= 0:
                self.main_menu_message = ""

    def show_main_menu_message(self, text, duration=180):
        self.main_menu_message = text
        self.main_menu_message_timer = max(0, duration)

    def module_required_token(self, module_name):
        token = self.module_token_requirements.get(module_name)
        if token:
            return token.upper()
        return None

    def is_module_locked(self, module_name):
        token = self.module_required_token(module_name)
        if not token:
            return False
        return not self.inventory.has_token(token)

    def get_module_lock_hint(self, module_name):
        placeholder_username = self.player_email or "operative"
        default_message = f"System integrity preserved. {placeholder_username} remains outside."
        custom_message = self.module_lock_messages.get(module_name)
        if isinstance(custom_message, str) and custom_message:
            return custom_message.replace("{username}", placeholder_username)
        return default_message

    def load_main_terminal_feed(self):
        default_posts = [
            {
                "id": "mtf_welcome_sysop",
                "header": "[SYSOP] glyphis  |  03.07.96  |  WELCOME NEW OPERATORS",
                "body": (
                    "Acknowledge your presence. Observe the rules. Read all welcome threads to\n\n"
                    "initiate onboarding."
                ),
                "required_tokens": [],
                "forbidden_tokens": [],
                "exclusive_tokens": []
            },
            {
                "id": "mtf_status_sysop",
                "header": "[SYSOP] glyphis  |  03.07.96  |  NETWORK STATUS: STABLE",
                "body": (
                    "Secure channels remain hardened. Surveillance nodes report silence.\n\n"
                    "Stay quiet. Stay unseen."
                ),
                "required_tokens": [],
                "forbidden_tokens": [],
                "exclusive_tokens": []
            },
            {
                "id": "mtf_protocol_rain",
                "header": "[TASKMASTER] rain  |  03.07.96  |  APPLICATION PROTOCOL",
                "body": (
                    "Complete your introduction. Prove you can follow directives.\n\n"
                    "Ping Glyphis once the Wall acknowledges you."
                ),
                "required_tokens": [],
                "forbidden_tokens": [],
                "exclusive_tokens": []
            },
            {
                "id": "mtf_clearance_sysop",
                "header": "[SYSOP] glyphis  |  03.07.96  |  CLEARANCE UNDER REVIEW",
                "body": (
                    "Your presence is logged. Access remains conditional.\n\n"
                    "Hold position until the network issues a directive."
                ),
                "required_tokens": [Tokens.PSEM, Tokens.USERNAME_SET],
                "forbidden_tokens": [],
                "exclusive_tokens": [Tokens.PSEM, Tokens.USERNAME_SET]
            },
            {
                "id": "mtf_games_cracking_jaxkando",
                "header": "[GAMESMASTER] jaxkando  |  03.07.96  |  GAMES NEED CRACKING!",
                "body": (
                    "HEY EVERYONE! So I just acquired a bunch of games that need cracking\n"
                    "before we can distribute them into the Games section of the BBS.\n\n"
                    "This is SUPER FUN! I'm really excited about this!\n\n"
                    "Uncle-am is busy getting the pirate radio packet decompressor online,\n"
                    "so if anyone else wants to help, ALL YOU NEED TO DO is email me\n"
                    "(jaxkando@ciphernet.net) stating that you want to help with the games\n"
                    "cracking and I'll get you set up!\n\n"
                    "Come on, it'll be fun! Promise!"
                ),
                "required_tokens": [Tokens.LAPC1A],
                "forbidden_tokens": [],
                "exclusive_tokens": []
            }
        ]

        posts = default_posts
        try:
            feed_path = get_data_path("main_terminal_feed.json")
            if os.path.exists(feed_path):
                with open(feed_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict) and isinstance(data.get("posts"), list):
                        posts = data.get("posts", default_posts)
        except Exception as e:
            log_event(f"Error loading main_terminal_feed.json: {e}")

        sanitized = []
        for post in posts:
            if not isinstance(post, dict):
                continue
            
            # Handle bodylines structure (like emails)
            body = post.get("body")
            if body is None:
                body_lines = []
                bodyline_count = post.get("bodylines")
                
                # Attempt to coerce the declared count into an int if provided
                try:
                    declared_count = int(bodyline_count) if bodyline_count is not None else None
                except (TypeError, ValueError):
                    declared_count = None
                
                index = 1
                while True:
                    key = f"body{index}"
                    has_key = key in post
                    
                    # If a count was provided, stop once we've processed that many entries
                    if declared_count is not None and index > declared_count:
                        break
                    
                    if not has_key:
                        # No explicit key and no remaining expected entries -> terminate
                        if declared_count is None:
                            break
                        # If keys are missing but a count was declared, treat as empty string placeholders
                        value = ""
                    else:
                        value = post.get(key)
                    
                    if value is not None:
                        body_lines.append(str(value))
                    
                    index += 1
                
                body = "\n".join(body_lines) if body_lines else ""
            else:
                body = str(body).strip()
            
            sanitized.append({
                "id": post.get("id"),
                "header": str(post.get("header", "")).strip(),
                "body": body,
                "required_tokens": [str(t).upper() for t in post.get("required_tokens", []) if isinstance(t, str)],
                "forbidden_tokens": [str(t).upper() for t in post.get("forbidden_tokens", []) if isinstance(t, str)],
                "exclusive_tokens": [str(t).upper() for t in post.get("exclusive_tokens", []) if isinstance(t, str)]
            })

        return {"posts": sanitized}

    def refresh_main_terminal_feed(self, initial=False):
        templates = self.front_post_data.get("posts", [])
        # Normalize all tokens in inventory for comparison
        token_set = {normalize_token(t) for t in self.inventory.tokens if normalize_token(t)}

        exclusive_matches = []
        general_matches = []

        for template in templates:
            required = {normalize_token(t) for t in template.get("required_tokens", []) if normalize_token(t)}
            forbidden = {normalize_token(t) for t in template.get("forbidden_tokens", []) if normalize_token(t)}
            exclusive = {normalize_token(t) for t in template.get("exclusive_tokens", []) if normalize_token(t)}

            if required and not required.issubset(token_set):
                continue
            if forbidden and token_set.intersection(forbidden):
                continue

            post_entry = {
                "id": template.get("id"),
                "header": template.get("header", ""),
                "body": template.get("body", ""),
                "read": False
            }

            if exclusive:
                # Exclusive posts show ONLY if user has exactly these tokens (no more, no less)
                if token_set == exclusive:
                    exclusive_matches.append(post_entry)
                continue

            general_matches.append(post_entry)

        # Combine exclusive and general matches - exclusive posts are special but don't hide general ones
        visible_posts = general_matches + exclusive_matches
        if not visible_posts:
            # Fallback: show templates with no requirements AND no forbidden tokens
            fallback = []
            for t in templates:
                required = {normalize_token(tok) for tok in t.get("required_tokens", []) if normalize_token(tok)}
                forbidden = {normalize_token(tok) for tok in t.get("forbidden_tokens", []) if normalize_token(tok)}
                if required:
                    continue
                if forbidden and token_set.intersection(forbidden):
                    continue
                fallback.append(t)

            visible_posts = [
                {
                    "id": t.get("id"),
                    "header": t.get("header", ""),
                    "body": t.get("body", ""),
                    "read": False
                }
                for t in fallback
            ]

        signature = tuple(post.get("id") or post.get("header") for post in visible_posts)
        if signature == self.active_post_signature and not initial:
            return

        self.posts = visible_posts
        self.active_post_signature = signature
        self.current_post = None
        self.post_scroll_y = 0
        if self.state == "front_post":
            self.current_module = 0
    
    def draw_front_post_board(self):
        """Draw the Main Terminal Feed module"""
        # Ensure posts are refreshed when viewing THE WALL
        if not self.posts:
            self.refresh_main_terminal_feed()
        
        self.bbs_surface.fill(BLACK)
        self._draw_background_grid()
        
        # Header panel - with ASCII art for THE WALL
        header_rect = self._draw_header_panel(
            "GLYPHIS_IO BBS // TERMINAL FEED",
            None  # We'll draw ASCII art and instructions manually
        )
        
        # Draw THE WALL ASCII art in white
        wall_ascii_lines = [
            "'########:'##::::'##:'########::::'##:::::'##::::'###::::'##:::::::'##:::::::",
            "... ##..:: ##:::: ##: ##.....::::: ##:'##: ##:::'## ##::: ##::::::: ##:::::::",
            "::: ##:::: ##:::: ##: ##:::::::::: ##: ##: ##::'##:. ##:: ##::::::: ##:::::::",
            "::: ##:::: #########: ######:::::: ##: ##: ##:'##:::. ##: ##::::::: ##:::::::",
            "::: ##:::: ##.... ##: ##...::::::: ##: ##: ##: #########: ##::::::: ##:::::::",
            "::: ##:::: ##:::: ##: ##:::::::::: ##: ##: ##: ##.... ##: ##::::::: ##:::::::",
            "::: ##:::: ##:::: ##: ########::::. ###. ###:: ##:::: ##: ########: ########:",
            ":::..:::::..:::::..::........::::::...::...:::..:::::..::........::........::"
        ]
        
        # Find a monospaced font that can render the ASCII art (4pt larger than original)
        wall_ascii_font = None
        font_names = ["Consolas", "Courier New", "Lucida Console", "DejaVu Sans Mono", "Courier"]
        for font_name in font_names:
            try:
                test_font = pygame.font.SysFont(font_name, int(16 * self.scale))
                test_surface = test_font.render("'", True, (255, 255, 255))
                if test_surface.get_width() > 0:
                    wall_ascii_font = test_font
                    break
            except:
                continue
        if wall_ascii_font is None:
            wall_ascii_font = pygame.font.SysFont("courier", int(16 * self.scale))
        
        # Calculate ASCII art height (8 lines)
        ascii_line_height = wall_ascii_font.get_linesize()
        ascii_total_height = len(wall_ascii_lines) * ascii_line_height
        nav_text_height = int(20 * self.scale)  # Height for navigation text line
        warning_text_height = int(18 * self.scale)  # Height for warning text line (font_tiny)
        padding_bottom = int(10 * self.scale)  # Padding below warning
        spacing = int(10 * self.scale) + int(20 * self.scale)  # Spacing between elements
        extra_line_height = self.font_small.get_linesize()  # One extra character line for moving text down
        
        # Extend header panel to accommodate ASCII art, navigation text, warning, and extra line
        # Reduced by 5 character rows (5 * ascii_line_height), but add one line for moving text down
        original_header_bottom = header_rect.bottom
        header_rect.height += ascii_total_height + nav_text_height + warning_text_height + spacing - (5 * ascii_line_height) + extra_line_height
        
        # Redraw header panel border to match new height
        pygame.draw.rect(self.bbs_surface, PANEL_BLUE, header_rect)
        pygame.draw.rect(self.bbs_surface, CYAN, header_rect, 2)
        
        # Draw ASCII art in the header area - moved up 10px
        title_y = header_rect.y + int(8 * self.scale)
        subtitle_y = title_y + int(32 * self.scale)
        wall_ascii_x = header_rect.x + int(20 * self.scale)
        wall_ascii_y = subtitle_y + ascii_line_height - (2 * ascii_line_height) - 10  # Moved up 10px
        for line in wall_ascii_lines:
            self.draw_text(line, wall_ascii_font, WHITE, wall_ascii_x, wall_ascii_y)
            wall_ascii_y += ascii_line_height
        
        # Navigation text below ASCII art (moved down 1 character line from previous position)
        nav_y = wall_ascii_y + int(10 * self.scale) - self.font_small.get_linesize() - 10 + 7 + self.font_small.get_linesize()
        nav_x = header_rect.x + int(20 * self.scale)
        
        # Draw "Sysop News - Team Requests - On-Boarding" with color changes (centered)
        sysop_text = "Sysop News"
        team_text = "Team Requests"
        onboard_text = "On-Boarding"
        separator = " - "
        
        # Calculate positions for multi-color text
        sysop_surface = self.font_small.render(sysop_text, True, CYAN)
        separator1_surface = self.font_small.render(separator, True, CYAN)
        team_surface = self.font_small.render(team_text, True, WHITE)
        separator2_surface = self.font_small.render(separator, True, CYAN)
        onboard_surface = self.font_small.render(onboard_text, True, CYAN)
        
        # Calculate total width of navigation text for centering
        total_nav_width = (sysop_surface.get_width() + separator1_surface.get_width() + 
                          team_surface.get_width() + separator2_surface.get_width() + 
                          onboard_surface.get_width())
        nav_x_centered = header_rect.x + (header_rect.width - total_nav_width) // 2
        
        current_x = nav_x_centered
        self.bbs_surface.blit(sysop_surface, (current_x, nav_y))
        current_x += sysop_surface.get_width()
        self.bbs_surface.blit(separator1_surface, (current_x, nav_y))
        current_x += separator1_surface.get_width()
        self.bbs_surface.blit(team_surface, (current_x, nav_y))
        current_x += team_surface.get_width()
        self.bbs_surface.blit(separator2_surface, (current_x, nav_y))
        current_x += separator2_surface.get_width()
        self.bbs_surface.blit(onboard_surface, (current_x, nav_y))
        
        # Warning message in white, centered (moved down 1 character line along with nav text)
        warning_y = nav_y + int(20 * self.scale) - 10 + 7
        warning_text = "Shhhh... you found us cuz we invited you, don't forget to NOT spread the word!"
        warning_surface = self.font_tiny.render(warning_text, True, WHITE)
        warning_x_centered = header_rect.x + (header_rect.width - warning_surface.get_width()) // 2
        self.bbs_surface.blit(warning_surface, (warning_x_centered, warning_y))
        
        # Main content panel - adjusted for shorter header, taller by 5 character rows
        # Bottom line brought up 5px above the blue footer line
        panel_top = header_rect.bottom + int(20 * self.scale)
        footer_y = self.bbs_height - int(50 * self.scale)
        panel_height = footer_y - panel_top - 5  # 5px above the blue line
        content_rect = pygame.Rect(
            int(50 * self.scale),
            panel_top,
            self.bbs_width - int(100 * self.scale),
            panel_height
        )
        pygame.draw.rect(self.bbs_surface, PANEL_BLUE, content_rect)
        pygame.draw.rect(self.bbs_surface, CYAN, content_rect, 2)
        
        if self.current_post is None:
            # Section header
            section_y = content_rect.y + int(15 * self.scale)
            self.draw_text("[ UNREAD POSTS ]", self.font_small, ACCENT_CYAN, content_rect.x + int(20 * self.scale), section_y)
            
            # Warning message if email locked
            if self.is_module_locked("EMAIL SYSTEM"):
                warning_y = section_y + int(30 * self.scale)
                warning_rect = pygame.Rect(
                    content_rect.x + int(20 * self.scale),
                    warning_y,
                    content_rect.width - int(40 * self.scale),
                    int(30 * self.scale)
                )
                pygame.draw.rect(self.bbs_surface, (32, 8, 8), warning_rect)
                pygame.draw.rect(self.bbs_surface, RED, warning_rect, 1)
                self.draw_text("System onboarding will commence after you've reviewed all welcome threads.",
                              self.font_tiny, RED, warning_rect.x + int(10 * self.scale), warning_y + int(8 * self.scale))
                post_start_y = warning_y + int(40 * self.scale)
            else:
                post_start_y = section_y + int(35 * self.scale)
            
            # Filter to show only unread posts
            unread_posts = [i for i, post in enumerate(self.posts) if not post.get("read", False)]
            if unread_posts:
                y = post_start_y
                for idx, post_idx in enumerate(unread_posts):
                    post = self.posts[post_idx]
                    
                    # Parse header to extract date stamp and title
                    header_full = post.get("header", "")
                    header_parts = [part.strip() for part in header_full.split("|")]
                    
                    if len(header_parts) >= 3:
                        # Format: "[TAG] author | date | title"
                        date_stamp = f"{header_parts[0]} | {header_parts[1]}"
                        title = header_parts[2]
                    elif len(header_parts) == 2:
                        # Fallback: assume "tag | title" or "tag | date"
                        date_stamp = header_parts[0]
                        title = header_parts[1] if len(header_parts) > 1 else ""
                    else:
                        # Fallback: use whole header as date stamp
                        date_stamp = header_full
                        title = ""
                    
                    # Post entry box - increased height to fit all elements with medium fonts
                    post_rect = pygame.Rect(
                        content_rect.x + int(15 * self.scale),
                        y,
                        content_rect.width - int(30 * self.scale),
                        int(105 * self.scale)  # Increased to accommodate 3 lines with medium fonts
                    )
                    
                    if idx == self.current_module:  # Selected
                        pygame.draw.rect(self.bbs_surface, HIGHLIGHT_BLUE, post_rect)
                        pygame.draw.rect(self.bbs_surface, ACCENT_CYAN, post_rect, 2)
                        date_color = ACCENT_CYAN
                        title_color = WHITE
                        preview_color = CYAN
                        prefix = "[>]"
                    else:
                        pygame.draw.rect(self.bbs_surface, PANEL_BLUE, post_rect, 1)
                        date_color = DARK_CYAN
                        title_color = DARK_CYAN
                        preview_color = DARK_CYAN
                        prefix = "[ ]"
                    
                    # Text positioning within post box
                    text_x = post_rect.x + int(12 * self.scale)
                    text_y = post_rect.y + int(8 * self.scale)
                    line_spacing = int(22 * self.scale)  # Increased for medium font
                    
                    # Calculate max width to prevent overflow
                    max_text_width = post_rect.width - int(24 * self.scale)
                    
                    # Date stamp (first line) - medium font
                    date_text = f"{prefix} {date_stamp}"
                    date_wrapped = self._wrap_text(date_text, self.font_medium, max_text_width)
                    if date_wrapped:
                        self.draw_text(date_wrapped[0], self.font_medium, date_color, text_x, text_y)
                    
                    # Title (second line) - medium font
                    if title:
                        title_y = text_y + line_spacing
                        title_wrapped = self._wrap_text(title, self.font_medium, max_text_width)
                        if title_wrapped:
                            self.draw_text(title_wrapped[0], self.font_medium, title_color, text_x, title_y)
                    else:
                        title_y = text_y + line_spacing
                    
                    # Body preview (third line) - small font
                    preview = post.get("body", "").splitlines()[0] if post.get("body") else ""
                    if preview:
                        preview_y = title_y + line_spacing
                        preview_with_indent = f"  {preview}"
                        preview_wrapped = self._wrap_text(preview_with_indent, self.font_small, max_text_width)
                        if preview_wrapped:
                            # Show first line, truncate if needed
                            preview_display = preview_wrapped[0]
                            if len(preview_wrapped) > 1 or len(preview) > 50:
                                # Add ellipsis if truncated or long
                                if preview_display.endswith("..."):
                                    pass  # Already has ellipsis from wrapping
                                else:
                                    preview_display = preview_display.rstrip() + "..."
                            self.draw_text(preview_display, self.font_small, preview_color, text_x, preview_y)
                    
                    y += int(110 * self.scale)  # Increased spacing to match new height
                    if y > content_rect.bottom - int(20 * self.scale):
                        break  # Stop if we've reached the bottom
            else:
                # No posts message
                empty_y = post_start_y + int(50 * self.scale)
                # Draw text without box
                no_unread_y = empty_y + int(15 * self.scale)
                text_x = content_rect.x + int(20 * self.scale)
                self.draw_text("No unread posts.", self.font_medium, DARK_CYAN, text_x, no_unread_y)
                # Add one character line spacing between the two texts
                self.draw_text("Press SPACEBAR to return to the main menu.", self.font_small, DARK_CYAN, text_x, no_unread_y + self.font_medium.get_linesize())
            
            # Footer
            footer_y = self.bbs_height - int(50 * self.scale)
            self.draw_line(footer_y)
            # Terminal feed header text above POSTS (white, same font and size)
            terminal_feed_text = "TERMINAL FEED: THE WALL.... GLYPHIS_IO BBS"
            footer_x = int(50 * self.scale)
            terminal_feed_y = footer_y + int(10 * self.scale)
            self.draw_text(terminal_feed_text, self.font_tiny, WHITE, footer_x, terminal_feed_y)
            # Posts count and TAB instructions on same line (moved down 1 row)
            posts_text = f"POSTS: {len(unread_posts)} unread"
            tab_text = "   TAB: cycle posts   ENTER: read   SPACEBAR: main menu"
            footer_text_y = terminal_feed_y + self.font_tiny.get_linesize()
            self.draw_text(posts_text + tab_text, self.font_tiny, DARK_CYAN, footer_x, footer_text_y)
        else:
            # Show post content (scaled)
            post = self.posts[self.current_post]
            post["read"] = True
            
            # Parse header to extract date stamp and title
            header_full = post.get("header", "")
            header_parts = [part.strip() for part in header_full.split("|")]
            
            if len(header_parts) >= 3:
                # Format: "[TAG] author | date | title"
                date_stamp = f"{header_parts[0]} | {header_parts[1]}"
                title = header_parts[2]
            elif len(header_parts) == 2:
                # Fallback: assume "tag | title" or "tag | date"
                date_stamp = header_parts[0]
                title = header_parts[1] if len(header_parts) > 1 else ""
            else:
                # Fallback: use whole header as date stamp
                date_stamp = header_full
                title = ""
            
            # Post header panel - increased height to fit two lines with bottom padding
            header_y = content_rect.y + int(15 * self.scale)
            header_panel_height = int(80 * self.scale) if title else int(60 * self.scale)  # Added 10px bottom padding
            header_panel = pygame.Rect(
                content_rect.x + int(15 * self.scale),
                header_y,
                content_rect.width - int(30 * self.scale),
                header_panel_height
            )
            pygame.draw.rect(self.bbs_surface, PANEL_BLUE, header_panel)
            pygame.draw.rect(self.bbs_surface, ACCENT_CYAN, header_panel, 2)
            
            # Section label
            self.draw_text("[ POST VIEW ]", self.font_small, ACCENT_CYAN, header_panel.x + int(12 * self.scale), header_panel.y + int(8 * self.scale))
            
            # Date stamp (first line) - wrapped to prevent overflow
            date_y = header_panel.y + int(25 * self.scale)
            max_header_width = header_panel.width - int(24 * self.scale)
            date_wrapped = self._wrap_text(date_stamp, self.font_medium, max_header_width)
            if date_wrapped:
                self.draw_text(date_wrapped[0], self.font_medium, ACCENT_CYAN, header_panel.x + int(12 * self.scale), date_y)
            
            # Title (second line) - wrapped to prevent overflow
            if title:
                title_y = date_y + int(22 * self.scale)
                title_wrapped = self._wrap_text(title, self.font_medium, max_header_width)
                if title_wrapped:
                    self.draw_text(title_wrapped[0], self.font_medium, CYAN, header_panel.x + int(12 * self.scale), title_y)
            
            # Content area
            content_start_y = header_panel.bottom + int(20 * self.scale)
            content_area = pygame.Rect(
                content_rect.x + int(15 * self.scale),
                content_start_y,
                content_rect.width - int(30 * self.scale),
                content_rect.bottom - content_start_y - int(20 * self.scale)
            )
            pygame.draw.rect(self.bbs_surface, PANEL_BLUE, content_area)
            pygame.draw.rect(self.bbs_surface, CYAN, content_area, 1)
            
            # Post body content
            post_content_width = content_area.width - int(40 * self.scale)
            post_lines = self._wrap_text(post.get("body", ""), self.font_small, post_content_width)
            line_height = int(20 * self.scale)
            max_visible_height = content_area.height - int(20 * self.scale)
            max_visible_lines = max_visible_height // line_height
            
            # Calculate scroll limits
            max_scroll_lines = max(0, len(post_lines) - max_visible_lines)
            self.post_scroll_y = max(0, min(max_scroll_lines, self.post_scroll_y))
            
            # Draw visible lines
            start_line = int(self.post_scroll_y)
            end_line = min(len(post_lines), start_line + max_visible_lines)
            
            draw_y = content_area.y + int(15 * self.scale)
            for i in range(start_line, end_line):
                if draw_y < content_area.bottom - int(10 * self.scale):
                    self.draw_text(post_lines[i], self.font_small, CYAN, content_area.x + int(15 * self.scale), draw_y)
                draw_y += line_height
            
            # Scroll indicator
            if max_scroll_lines > 0:
                scroll_indicator_y = content_area.bottom - int(15 * self.scale)
                scroll_text = f"SCROLL: {self.post_scroll_y}/{max_scroll_lines} (UP/DOWN)"
                self.draw_text(scroll_text, self.font_tiny, DARK_CYAN, content_area.x + int(15 * self.scale), scroll_indicator_y)
            
            # Mark as read when viewing
            post["read"] = True
            
            # Assign guest credentials when first post is read
            if self.player_email == "unknown":
                self.player_email = "guest"
            
            # Grant PSEM token after all welcome posts are read
            unread_count = len([p for p in self.posts if not p.get("read", False)])
            if unread_count == 0 and not self.inventory.has_token(Tokens.PSEM):
                if self.grant_token(Tokens.PSEM, reason="reviewed all welcome threads"):
                    self.check_email_database()
            
            # Footer
            footer_y = self.bbs_height - int(50 * self.scale)
            self.draw_line(footer_y)
            instruction_text = "ESC: return   SPACEBAR: main menu"
            if len(post_lines) > max_visible_lines:
                instruction_text += "   UP/DOWN: scroll"
            self.draw_text(instruction_text, self.font_tiny, DARK_CYAN, int(50 * self.scale), footer_y + int(10 * self.scale))
    
    def draw_email_system(self):
        """Draw the Email System module"""
        if self.state == "compose":
            self.draw_compose_screen()
        elif self.state == "inbox":
            self.draw_email_list(self.inbox, "INBOX")
        elif self.state == "outbox":
            self.draw_email_list(self.outbox, "OUTBOX")
        elif self.state == "sent":
            self.draw_email_list(self.sent, "SENT MESSAGES")
        elif self.state == "reading":
            self.draw_reading_screen()
        else:
            self._draw_email_menu_screen()

    def _draw_email_menu_screen(self):
        unread_count = len([e for e in self.inbox if not e.read])
        _, modules_rect, info_rect = self._prepare_bbs_screen(
            "EMAIL SYSTEM // INTERNAL MAIL",
            ["TAB: switch folders   ENTER: open selection   ESC: return to main menu"],
            include_info=True,
        )

        options = [
            "NEW MESSAGE",
            f"INBOX ({unread_count})",
            f"OUTBOX ({len(self.outbox)})",
            f"SENT ({len(self.sent)})",
        ]

        label_x = modules_rect.x + int(20 * self.scale)
        self.draw_text("[ MAIL OPERATIONS ]", self.font_small, ACCENT_CYAN, label_x, modules_rect.y + int(20 * self.scale))

        y = modules_rect.y + int(60 * self.scale)
        row_height = max(int(46 * self.scale), 32)
        for i, option in enumerate(options):
            entry_rect = pygame.Rect(
                modules_rect.x + int(16 * self.scale),
                y - int(10 * self.scale),
                modules_rect.width - int(32 * self.scale),
                row_height,
            )
            if i == self.current_module:
                pygame.draw.rect(self.bbs_surface, HIGHLIGHT_BLUE, entry_rect)
                pygame.draw.rect(self.bbs_surface, ACCENT_CYAN, entry_rect, 2)
                color = WHITE
                tag = "[>]"
            else:
                pygame.draw.rect(self.bbs_surface, PANEL_BLUE, entry_rect, 1)
                color = DARK_CYAN
                tag = "[ ]"

            module_font = self.font_medium_small if option.startswith("INBOX") else self.font_medium
            self.draw_text(f"{tag} {option}", module_font, color, entry_rect.x + int(14 * self.scale), y)
            y += row_height

        if info_rect:
            info_x = info_rect.x + int(20 * self.scale)
            info_y = info_rect.y + int(20 * self.scale)
            self.draw_text("[ INBOX STATUS ]", self.font_small, ACCENT_CYAN, info_x, info_y)
            info_y += int(30 * self.scale)
            self.draw_text(f"Unread messages: {unread_count}", self.font_small, CYAN, info_x, info_y)
            info_y += int(24 * self.scale)
            self.draw_text(f"Outbox size: {len(self.outbox)}", self.font_tiny, DARK_CYAN, info_x, info_y)
            info_y += int(20 * self.scale)
            self.draw_text(f"Sent archive: {len(self.sent)}", self.font_tiny, DARK_CYAN, info_x, info_y)
            info_y += int(30 * self.scale)
            if self.inbox:
                latest = self.inbox[-1]
                self.draw_text("Last received:", self.font_tiny, ACCENT_CYAN, info_x, info_y)
                info_y += int(20 * self.scale)
                self.draw_text(f"{latest.sender}", self.font_tiny, CYAN, info_x, info_y, max_width=info_rect.width - int(40 * self.scale))
                info_y += int(18 * self.scale)
                self.draw_text(f"{latest.subject}", self.font_tiny, DARK_CYAN, info_x, info_y, max_width=info_rect.width - int(40 * self.scale))
            else:
                self.draw_text("Inbox empty.", self.font_tiny, DARK_CYAN, info_x, info_y)

        self._draw_footer_status()
    
    def draw_compose_screen(self):
        """Draw the email composition screen"""
        _, panel_rect, _ = self._prepare_bbs_screen(
            "EMAIL // COMPOSE MESSAGE",
            ["TAB: switch fields   ENTER: send   ESC: cancel"],
            include_info=False,
            left_ratio=1.0,
        )

        panel_x = panel_rect.x + int(20 * self.scale)
        panel_width = panel_rect.width - int(40 * self.scale)
        cursor_y = panel_rect.y + int(20 * self.scale)

        if not self.inventory.has_token(Tokens.PSEM):
            self.draw_text("EMAIL SYSTEM LOCKED", self.font_medium, CYAN, panel_x, cursor_y)
            cursor_y += int(40 * self.scale)
            self.draw_text(
                "Review every welcome thread on the Terminal Feed to unlock email access.",
                self.font_small,
                DARK_CYAN,
                panel_x,
                cursor_y,
                max_width=panel_width,
            )
            self._draw_footer_status()
            return
        
        # To field
        self.draw_text("TO:", self.font_small, ACCENT_CYAN, panel_x, cursor_y)
        self.draw_text(self.compose_to, self.font_small, DARK_CYAN, panel_x + int(120 * self.scale), cursor_y)
        cursor_y += int(40 * self.scale)

        # Subject field
        self.draw_text("SUBJECT:", self.font_small, ACCENT_CYAN, panel_x, cursor_y)
        subject_color = CYAN if self.active_field == "subject" else DARK_CYAN
        cursor = "|" if self.active_field == "subject" else ""
        subject_field_x = panel_x + int(140 * self.scale)
        subject_field_width = panel_width - int(160 * self.scale)
        pygame.draw.rect(
            self.bbs_surface,
            DARK_BLUE,
            (
                subject_field_x,
                cursor_y + self.content_scroll_y,
                subject_field_width,
                int(34 * self.scale),
            ),
            1,
        )
        self.draw_text(self.compose_subject + cursor, self.font_small, subject_color, subject_field_x + int(8 * self.scale), cursor_y + int(6 * self.scale))
        cursor_y += int(60 * self.scale)

        # Body field
        self.draw_text("MESSAGE:", self.font_small, ACCENT_CYAN, panel_x, cursor_y)
        body_color = CYAN if self.active_field == "body" else DARK_CYAN
        
        body_text = self.compose_body
        if self.active_field == "body":
            body_text += "|"
        
        body_y = cursor_y + int(30 * self.scale)
        body_field_height = panel_rect.bottom - body_y - int(140 * self.scale)
        body_field_height = max(body_field_height, int(120 * self.scale))
        pygame.draw.rect(
            self.bbs_surface,
            DARK_BLUE,
            (
                panel_x,
                body_y + self.content_scroll_y,
                panel_width,
                body_field_height,
            ),
            1,
        )
        self.draw_text(
            body_text,
            self.font_small,
            body_color,
            panel_x + int(10 * self.scale),
            body_y + int(10 * self.scale),
            panel_width - int(20 * self.scale),
        )

        send_y = body_y + body_field_height + int(20 * self.scale)
        button_x = panel_x
        if self.active_field == "send":
            base_color = CYAN
            left_text = "( "
            right_text = " ) SEND"
            left_surface = self.font_medium.render(left_text, True, base_color)
            self.bbs_surface.blit(left_surface, (button_x, send_y))

            circle_font = get_selection_glyph_font(self.font_medium.get_height())
            circle_surface = circle_font.render(SELECTION_GLYPH, True, base_color)
            circle_x = button_x + left_surface.get_width()
            self.bbs_surface.blit(circle_surface, (circle_x, send_y - 6))

            right_surface = self.font_medium.render(right_text, True, base_color)
            self.bbs_surface.blit(right_surface, (circle_x + circle_surface.get_width(), send_y))
        else:
            indicator = "(   ) SEND"
            self.draw_text(indicator, self.font_medium, DARK_CYAN, button_x, send_y)

        hint_y = send_y + int(40 * self.scale)
        self.draw_text("TAB to target SEND, ENTER to transmit", self.font_tiny, DARK_CYAN, panel_x, hint_y)

        self._draw_footer_status()
    
    def draw_email_list(self, emails, title):
        """Draw a list of emails"""
        _, panel_rect, _ = self._prepare_bbs_screen(
            f"EMAIL // {title}",
            ["UP/DOWN: navigate mail   ENTER: read   ESC: return"],
            include_info=False,
            left_ratio=1.0,
        )

        panel_x = panel_rect.x + int(20 * self.scale)
        panel_width = panel_rect.width - int(40 * self.scale)
        y = panel_rect.y + int(20 * self.scale)

        if not emails:
            self.draw_text("No messages.", self.font_medium, DARK_CYAN, panel_x, y + int(40 * self.scale))
            self._draw_footer_status()
            return

        entry_height = int(80 * self.scale)
        gap = int(12 * self.scale)

        for i, email in enumerate(emails[:12]):
            entry_rect = pygame.Rect(
                panel_rect.x + int(16 * self.scale),
                y,
                panel_rect.width - int(32 * self.scale),
                entry_height,
            )
            if i == self.current_module:
                pygame.draw.rect(self.bbs_surface, HIGHLIGHT_BLUE, entry_rect)
                pygame.draw.rect(self.bbs_surface, ACCENT_CYAN, entry_rect, 2)
                header_color = WHITE
                prefix = "[>]"
            else:
                pygame.draw.rect(self.bbs_surface, PANEL_BLUE, entry_rect, 1)
                header_color = DARK_CYAN if email.read else CYAN
                prefix = "[*]" if not email.read else "[ ]"

            text_x = entry_rect.x + int(14 * self.scale)
            line_y = y + int(10 * self.scale)
            self.draw_text(
                f"{prefix} FROM: {email.sender}",
                self.font_small,
                header_color,
                text_x,
                line_y,
                max_width=panel_width - int(40 * self.scale),
            )
            line_y += int(24 * self.scale)
            self.draw_text(
                f"SUBJECT: {email.subject}",
                self.font_small,
                header_color,
                text_x,
                line_y,
                max_width=panel_width - int(40 * self.scale),
            )
            line_y += int(24 * self.scale)
            self.draw_text(f"TIME: {email.timestamp}", self.font_tiny, DARK_CYAN, text_x, line_y)

            y += entry_height + gap
            if y + entry_height > panel_rect.bottom - int(20 * self.scale):
                break

        self._draw_footer_status()
    
    def draw_reading_screen(self):
        """Draw the email reading screen"""
        if not self.selected_email:
            self.state = "inbox"
            return

        email = self.selected_email
        _, panel_rect, _ = self._prepare_bbs_screen(
            "EMAIL // READ MESSAGE",
            ["ESC: return   R: reply   D: delete   UP/DOWN: scroll"],
            include_info=False,
            left_ratio=1.0,
        )

        panel_x = panel_rect.x + int(20 * self.scale)
        panel_width = panel_rect.width - int(40 * self.scale)
        y = panel_rect.y + int(20 * self.scale)

        self.draw_text(f"FROM: {email.sender}", self.font_small, CYAN, panel_x, y)
        y += int(28 * self.scale)
        self.draw_text(f"TO: {email.recipient}", self.font_small, CYAN, panel_x, y)
        y += int(28 * self.scale)
        self.draw_text(f"TIME: {email.timestamp}", self.font_small, CYAN, panel_x, y)
        y += int(28 * self.scale)
        self.draw_text(f"SUBJECT: {email.subject}", self.font_medium, CYAN, panel_x, y)
        y += int(36 * self.scale)

        separator_start = (panel_x, y)
        separator_end = (panel_x + panel_width, y)
        pygame.draw.line(self.bbs_surface, DARK_BLUE, separator_start, separator_end, 2)
        y += int(16 * self.scale)

        body_text = email.body or ""
        paragraphs = body_text.split("\n")
        body_lines = []
        for paragraph in paragraphs:
            if paragraph == "":
                body_lines.append("")
            else:
                body_lines.extend(self._wrap_text(paragraph, self.font_small, panel_width))

        line_height = int(20 * self.scale)
        max_visible_height = panel_rect.bottom - y - int(20 * self.scale)
        max_visible_lines = max_visible_height // line_height
        max_scroll_lines = max(0, len(body_lines) - max_visible_lines)
        self.email_scroll_y = max(0, min(max_scroll_lines, self.email_scroll_y))

        start_line = int(self.email_scroll_y)
        end_line = min(len(body_lines), start_line + max_visible_lines)
        draw_y = y
        for i in range(start_line, end_line):
            if draw_y > panel_rect.bottom - int(20 * self.scale):
                break
            line_text = body_lines[i]
            if line_text == "":
                draw_y += line_height
                continue
            self.draw_text(line_text, self.font_small, CYAN, panel_x, draw_y)
            draw_y += line_height

        if len(body_lines) > max_visible_lines:
            hint_y = panel_rect.bottom - int(30 * self.scale)
            self.draw_text("Scroll for additional content", self.font_tiny, DARK_CYAN, panel_x, hint_y)

        self._draw_footer_status()

    def _on_email_marked_read(self, email):
        email_id = getattr(email, "email_id", None)
        if not email_id:
            return

        reward = self.email_token_rewards.get(email_id)
        if not reward:
            return

        tokens = reward.get("tokens")
        if tokens is None:
            single = reward.get("token")
            if single:
                tokens = [single]

        if not tokens:
            return

        if not isinstance(tokens, (list, tuple, set)):
            tokens = [tokens]

        reasons_map = reward.get("reasons") or {}
        default_reason = reward.get("reason")

        for token in tokens:
            if not token:
                continue
            reason = reasons_map.get(token, default_reason)
            self.grant_token(token, reason=reason)
    
    def _get_visible_ops_tasks(self) -> List[dict]:
        tasks: List[dict] = []
        for task in self.urgent_ops_task_definitions:
            token = task.get("token_required")
            if token and not self.inventory.has_token(token):
                continue
            tasks.append(task)

        if not tasks:
            tasks = [
                {
                    "id": "ops_standby",
                    "title": "Awaiting dispatch authorisation",
                    "description": "No urgent assignments have been issued. Stand by for Uncle-am's signal.",
                    "status": "Status: stand by.",
                    "launch_method": None,
                }
            ]

        self.visible_ops_tasks = tasks
        if tasks:
            self.current_task = max(0, min(self.current_task, len(tasks) - 1))
        else:
            self.current_task = 0
        return tasks

    def _play_ops_intro_video(self, video_path: str) -> None:
        if not os.path.exists(video_path):
            return

        cap = None
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap or not cap.isOpened():
                if cap:
                    cap.release()
                return

            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            frame_delay = 1.0 / fps
            last_time = time.time()

            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame_resized = cv2.resize(frame_rgb, (self.bbs_width, self.bbs_height))
                frame_surface = pygame.surfarray.make_surface(np.swapaxes(frame_resized, 0, 1))

                self.bbs_surface.blit(frame_surface, (0, 0))

                # Keep desktop background video playing instead of using static desktop.png
                if self.video_cap and _cv2_available:
                    # Read next frame from desktop background video
                    ret_bg, frame_bg = self.video_cap.read()
                    if ret_bg:
                        frame_bg_rgb = cv2.cvtColor(frame_bg, cv2.COLOR_BGR2RGB)
                        frame_bg_resized = cv2.resize(frame_bg_rgb, (self.screen_width, self.screen_height))
                        frame_bg_surface = pygame.surfarray.make_surface(np.swapaxes(frame_bg_resized, 0, 1))
                        self.screen.blit(frame_bg_surface, (0, 0))
                    else:
                        # Video ended, loop back to beginning
                        self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        ret_bg, frame_bg = self.video_cap.read()
                        if ret_bg:
                            frame_bg_rgb = cv2.cvtColor(frame_bg, cv2.COLOR_BGR2RGB)
                            frame_bg_resized = cv2.resize(frame_bg_rgb, (self.screen_width, self.screen_height))
                            frame_bg_surface = pygame.surfarray.make_surface(np.swapaxes(frame_bg_resized, 0, 1))
                            self.screen.blit(frame_bg_surface, (0, 0))
                else:
                    self.screen.fill(BLACK)

                self.screen.blit(self.bbs_surface, (self.bbs_x, self.bbs_y))
                pygame.display.flip()

                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        cap.release()
                        pygame.quit()
                        sys.exit()

                elapsed = time.time() - last_time
                if elapsed < frame_delay:
                    time.sleep(frame_delay - elapsed)
                last_time = time.time()
        except Exception as exc:
            log_event(f"Intro video playback failed: {exc}")
        finally:
            if cap:
                try:
                    cap.release()
                except Exception:
                    pass

    def _start_lapc1_driver_challenge(self):
        if self.active_ops_session:
            return

        try:
            from Urgent_Ops.CRACKER_IDE_LAPC1_Driver_Challenge import (
                CRACKER_IDE_LAPC1_Driver_Challenge,
            )
        except Exception as exc:  # pragma: no cover - import guard
            log_event(f"Failed to import LAPC1 driver challenge: {exc}")
            self.show_main_menu_message("Unable to load CRACKER IDE module.")
            return

        fonts = {
            "large": self.font_large,
            "medium": self.font_medium,
            "small": self.font_small,
            "tiny": self.font_tiny,
        }
        player = self.player_email if self.player_email not in (None, "", "unknown") else "operative"

        try:
            # Pass token checker function to restore LED states
            def has_token(token):
                return self.inventory.has_token(token)
            
            # Pass token remover function to remove tokens on reset
            def remove_token(token):
                if self.inventory.remove_token(token):
                    log_event(f"Removed token {token} due to CRACKER IDE reset")
                    self.save_user_state()
            
            self.active_ops_session = CRACKER_IDE_LAPC1_Driver_Challenge(
                self.bbs_surface,
                fonts,
                self.scale,
                player,
                token_checker=has_token,
                token_remover=remove_token,
            )
        except Exception as exc:
            self.active_ops_session = None
            log_event(f"Error launching LAPC1 driver challenge: {exc}")
            self.show_main_menu_message("CRACKER IDE initialisation failed.")
            return

        if _cv2_available:
            self._play_ops_intro_video(get_data_path("Videos", "IDE-START.mp4"))

        self.state = "urgent_ops_session"

    def _end_ops_session(self):
        # Reset achievement unlock flag when session ends
        self._lapc1_achievement_unlocked = False
        self.active_ops_session = None
        self.state = "tasks"
        self.current_task = 0

    def _draw_ops_docs_overlay(self):
        overlay = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 210))
        self.screen.blit(overlay, (0, 0))

        title_font = self.font_large
        body_font = self.font_small

        x = int(80 * self.scale)
        y = int(80 * self.scale)

        self.screen.blit(
            title_font.render("CRACKER-PARROT FIELD REFERENCES", True, ACCENT_CYAN),
            (x, y),
        )
        y += int(50 * self.scale)

        if self.ops_docs_overlay_image is None:
            try:
                doc_image_path = get_data_path("Images", "Bradsonic Doc Image.png")
                self.ops_docs_overlay_image = pygame.image.load(doc_image_path).convert()
            except Exception:
                self.ops_docs_overlay_image = False

        if self.ops_docs_overlay_image:
            image_surface = self.ops_docs_overlay_image
            max_width = int(self.screen_width * 0.35)
            scale_ratio = min(1.0, max_width / image_surface.get_width())
            if scale_ratio != 1.0:
                new_size = (
                    int(image_surface.get_width() * scale_ratio),
                    int(image_surface.get_height() * scale_ratio),
                )
                image_surface = pygame.transform.scale(image_surface, new_size)
            self.screen.blit(image_surface, (x, y))
            y += image_surface.get_height() + int(30 * self.scale)

        lines = [
            "Refer to the following briefing packets:",
            "• Bradsonic_Docs/Getting_Started_with_Bradsonic_ASM.pdf",
            "• Bradsonic_Docs/Radland_LAPC-1_Audio_Chipset_Supplement.pdf",
            "",
            "Use these manuals to complete the LAPC-1 driver. Press F8 to return to the IDE.",
        ]
        for line in lines:
            self.screen.blit(body_font.render(line, True, WHITE), (x, y))
            y += int(28 * self.scale)

    def draw_games_module(self):
        """Draw the Games module"""
        self.content_scroll_y = 0
        _, modules_rect, info_rect = self._prepare_bbs_screen(
            "GAMES // PROTOTYPE LIBRARY",
            ["UP/DOWN: navigate prototypes   ENTER: launch   ESC: return"],
            include_info=True,
        )

        games = self._get_unlocked_games()
        label_x = modules_rect.x + int(20 * self.scale)
        self.draw_text("[ PROTOTYPES ]", self.font_small, ACCENT_CYAN, label_x, modules_rect.y + int(20 * self.scale))

        y = modules_rect.y + int(60 * self.scale)
        row_height = max(int(46 * self.scale), 32)

        if not games:
            self.draw_text(
                "No prototypes unlocked yet. Complete onboarding posts and submissions to access the sim vault.",
                self.font_small,
                DARK_CYAN,
                label_x,
                y,
                max_width=modules_rect.width - int(40 * self.scale),
            )
        else:
            for i, definition in enumerate(games):
                entry_rect = pygame.Rect(
                    modules_rect.x + int(16 * self.scale),
                    y - int(10 * self.scale),
                    modules_rect.width - int(32 * self.scale),
                    row_height,
                )
                if i == self.current_game_index:
                    pygame.draw.rect(self.bbs_surface, HIGHLIGHT_BLUE, entry_rect)
                    pygame.draw.rect(self.bbs_surface, ACCENT_CYAN, entry_rect, 2)
                    color = WHITE
                    prefix = "[>]"
                else:
                    pygame.draw.rect(self.bbs_surface, PANEL_BLUE, entry_rect, 1)
                    color = DARK_CYAN
                    prefix = "[ ]"

                self.draw_text(
                    f"{prefix} {definition.title}",
                    self.font_medium,
                    color,
                    entry_rect.x + int(14 * self.scale),
                    y,
                )
                y += row_height

        if info_rect:
            info_x = info_rect.x + int(20 * self.scale)
            info_y = info_rect.y + int(20 * self.scale)
            self.draw_text("[ PROTOTYPE DETAILS ]", self.font_small, ACCENT_CYAN, info_x, info_y)
            info_y += int(30 * self.scale)

            if games:
                selected = games[self.current_game_index]
                self.draw_text(selected.title, self.font_small, CYAN, info_x, info_y)
                info_y += int(24 * self.scale)
                tokens_required = getattr(selected, "tokens_required", []) or []
                if tokens_required:
                    token_text = ", ".join(tokens_required)
                else:
                    token_text = "--"
                self.draw_text(f"Tokens required: {token_text}", self.font_tiny, DARK_CYAN, info_x, info_y)
                info_y += int(24 * self.scale)
                self.draw_text("Description:", self.font_tiny, ACCENT_CYAN, info_x, info_y)
                info_y += int(20 * self.scale)
                self.draw_text(
                    selected.description,
                    self.font_tiny,
                    DARK_CYAN,
                    info_x,
                    info_y,
                    max_width=info_rect.width - int(40 * self.scale),
                )
            else:
                self.draw_text("Awaiting unlock sequence.", self.font_tiny, DARK_CYAN, info_x, info_y)

        self._draw_footer_status()
    
    def draw_tasks_module(self):
        """Draw the Urgent Ops module"""
        self.content_scroll_y = 0
        _, modules_rect, info_rect = self._prepare_bbs_screen(
            "URGENT OPS // DISPATCH BOARD",
            ["UP/DOWN: navigate assignments   ESC: return"],
            include_info=True,
        )

        label_x = modules_rect.x + int(20 * self.scale)
        self.draw_text("[ ACTIVE TASKS ]", self.font_small, ACCENT_CYAN, label_x, modules_rect.y + int(20 * self.scale))

        y = modules_rect.y + int(60 * self.scale)
        row_height = max(int(46 * self.scale), 32)

        tasks = self._get_visible_ops_tasks()

        for i, task in enumerate(tasks):
            title = task.get("title", "Unknown assignment")
            entry_rect = pygame.Rect(
                modules_rect.x + int(16 * self.scale),
                y - int(10 * self.scale),
                modules_rect.width - int(32 * self.scale),
                row_height,
            )
            if i == self.current_task:
                pygame.draw.rect(self.bbs_surface, HIGHLIGHT_BLUE, entry_rect)
                pygame.draw.rect(self.bbs_surface, ACCENT_CYAN, entry_rect, 2)
                color = WHITE
                prefix = "[>]"
            else:
                pygame.draw.rect(self.bbs_surface, PANEL_BLUE, entry_rect, 1)
                color = DARK_CYAN
                prefix = "[ ]"

            self.draw_text(
                f"{prefix} {title}",
                self.font_medium,
                color,
                entry_rect.x + int(14 * self.scale),
                y,
                max_width=modules_rect.width - int(48 * self.scale),
            )
            y += row_height

        if info_rect:
            info_x = info_rect.x + int(20 * self.scale)
            info_y = info_rect.y + int(20 * self.scale)
            self.draw_text("[ TASK BRIEFING ]", self.font_small, ACCENT_CYAN, info_x, info_y)
            info_y += int(30 * self.scale)
            if tasks:
                active_task = tasks[self.current_task]
                description = active_task.get("description", active_task.get("title", ""))
                lines = self._wrap_text(description, self.font_tiny, info_rect.width - int(40 * self.scale))
                for line in lines:
                    self.draw_text(line, self.font_tiny, CYAN, info_x, info_y)
                    info_y += self.font_tiny.get_linesize()
                info_y += int(8 * self.scale)
                launch_method = active_task.get("launch_method")
                status_text = active_task.get("status")
                if launch_method and not status_text:
                    status_text = "Press ENTER to deploy response."
                elif not status_text:
                    status_text = "Status: awaiting operator confirmation."
                status_lines = self._wrap_text(status_text, self.font_tiny, info_rect.width - int(40 * self.scale))
                for line in status_lines[:-1]:
                    self.draw_text(line, self.font_tiny, DARK_CYAN, info_x, info_y)
                    info_y += self.font_tiny.get_linesize()
                if status_lines:
                    info_y += self.font_tiny.get_linesize()
                    self.draw_text(
                        status_lines[-1],
                        self.font_tiny,
                        WHITE,
                        info_x,
                        info_y,
                    )
            else:
                self.draw_text("No active assignments.", self.font_tiny, DARK_CYAN, info_x, info_y)

        self._draw_footer_status()
    
    def draw_team_module(self):
        """Draw the Team Info module"""
        self.content_scroll_y = 0
        _, content_rect, _ = self._prepare_bbs_screen(
            "TEAM INFO // PERSONNEL FILES",
            ["LEFT/RIGHT: cycle roster   UP/DOWN: scroll bio   ESC: return"],
            include_info=False,
            left_ratio=1.0,
        )

        member = self.team_members[self.current_team_member]
        x = content_rect.x + int(20 * self.scale)
        y = content_rect.y + int(20 * self.scale)
        self.draw_text(f"Handle: {member['handle']}", self.font_medium, CYAN, x, y)
        y += int(30 * self.scale)
        if "tag" in member:
            self.draw_text(member["tag"], self.font_small, ACCENT_CYAN, x, y)
            y += int(25 * self.scale)
        self.draw_text(f"Role: {member['role']}", self.font_small, DARK_CYAN, x, y)
        y += int(30 * self.scale)
        self.draw_line(y)
        y += int(20 * self.scale)
        self.draw_text("Bio:", self.font_small, ACCENT_CYAN, x, y)
        bio_start_y = y + int(25 * self.scale)
        bio_width = content_rect.width - int(40 * self.scale)
        bio_lines = self._wrap_text(member['bio'], self.font_small, bio_width)
        line_height = int(20 * self.scale)
        max_visible_height = content_rect.bottom - bio_start_y - int(20 * self.scale)
        max_visible_lines = max_visible_height // line_height
        
        # Calculate scroll limits (scroll_y is number of lines scrolled, starts at 0)
        max_scroll_lines = max(0, len(bio_lines) - max_visible_lines)
        
        # Clamp scroll position (0 = top, positive = scrolled down)
        self.bio_scroll_y = max(0, min(max_scroll_lines, self.bio_scroll_y))
        
        # Draw visible lines based on scroll position
        start_line = int(self.bio_scroll_y)
        end_line = min(len(bio_lines), start_line + max_visible_lines)
        
        # Draw lines starting at fixed position, filling downward
        draw_y = bio_start_y
        for i in range(start_line, end_line):
            if draw_y < content_rect.bottom - int(20 * self.scale):
                self.draw_text(bio_lines[i], self.font_small, DARK_CYAN, x, draw_y)
            draw_y += line_height

        if len(bio_lines) > max_visible_lines:
            hint_y = content_rect.bottom - int(30 * self.scale)
            self.draw_text("Scroll for more...", self.font_tiny, DARK_CYAN, x, hint_y)

        self._draw_footer_status()
    
    def draw_radio_module(self):
        """Draw the Pirate Radio module"""
        self.content_scroll_y = 0
        _, content_rect, _ = self._prepare_bbs_screen(
            "PIRATE RADIO // SIGNAL NODE",
            ["SPACE: toggle playback   ESC: return"],
            include_info=False,
            left_ratio=1.0,
        )

        x = content_rect.x + int(20 * self.scale)
        y = content_rect.y + int(20 * self.scale)
        status = "PLAYING" if self.radio_playing else "STOPPED"
        self.draw_text(f"Status: {status}", self.font_medium, CYAN, x, y)
        y += int(40 * self.scale)
        self.draw_text(f"Now Playing: {self.current_track}", self.font_small, DARK_CYAN, x, y)
        y += int(40 * self.scale)
        self.draw_line(y)
        y += int(30 * self.scale)
        
        # DJ text (scaled)
        self.draw_text("DJ TRANSMISSION:", self.font_small, ACCENT_CYAN, x, y)
        y += int(30 * self.scale)
        dj_text_width = content_rect.width - int(40 * self.scale)
        self.draw_text(self.dj_text[self.dj_index], self.font_small, DARK_CYAN, x, y, dj_text_width)

        self._draw_footer_status()
    
    def handle_text_input(self, event):
        """Handle text input for compose screen"""
        if event.key == pygame.K_ESCAPE:
            # ESC always returns to email menu, even if locked
            self.state = "email_menu"
            self.current_module = 0
            return
        elif event.key == pygame.K_BACKSPACE:
            if self.active_field == "subject" and self.compose_subject:
                self.compose_subject = self.compose_subject[:-1]
            elif self.active_field == "body" and self.compose_body:
                self.compose_body = self.compose_body[:-1]
        elif event.key == pygame.K_TAB:
            # Switch fields: subject -> body -> send -> subject
            if self.active_field == "subject":
                self.active_field = "body"
            elif self.active_field == "body":
                self.active_field = "send"
            else:  # send or None
                self.active_field = "subject"
        elif event.key == pygame.K_RETURN:
            if self.active_field == "send":
                # Require PSEM token before outbound email is available
                if not self.inventory.has_token(Tokens.PSEM):
                    # Email system is locked - cannot send
                    return
                
                # Send the message
                if self.compose_subject.strip() or self.compose_body.strip():
                    # Parse username from email body if present
                    email_body = self.compose_body.strip()
                    email_subject = self.compose_subject.strip()
                    
                    # Extract username from "username: " pattern
                    username_pattern = r"username:\s*(\S+)"
                    match = re.search(username_pattern, email_body, re.IGNORECASE)
                    if match:
                        new_username = match.group(1).lower()  # Convert to lowercase
                        if new_username and new_username not in ["unknown", "guest"]:
                            self.player_email = new_username
                            # Grant username_set token to trigger next email
                            if not self.inventory.has_token(Tokens.USERNAME_SET):
                                granted_username = self.grant_token(Tokens.USERNAME_SET, reason="username registered via email")
                                if granted_username:
                                    self.check_email_database()
                            log_event(f"Username set to '{self.player_email}'")
                            self.save_user_state()
                    
                    # Create email
                    email = Email(
                        self.player_email,
                        self.compose_to,
                        email_subject or "(no subject)",
                        email_body or "(empty message)"
                    )
                    
                    # If sending to glyphis (sysop), handle onboarding responses
                    if self.compose_to == "glyphis@ciphernet.net":
                        # Add to sent immediately
                        self.sent.append(email)
                        log_event(f"Email sent to {self.compose_to} | Subject: '{email.subject}'")
                        
                        # For onboarding, don't generate NPC response - let email database handle it
                        # Only generate NPC response for non-onboarding emails
                        if not match:
                            # Generate response from glyphis (sysop) using enhanced trait-based system
                            player_tokens = self.inventory.get_all_tokens()
                            response_body = self.npc.generate_response(
                                sender_email="glyphis@ciphernet.net",
                                email_subject=email.subject,
                                email_body=email.body,
                                player_tokens=player_tokens,
                                player_username=self.player_email
                            )
                            response = Email(
                                "glyphis@ciphernet.net",
                                self.player_email,
                                f"RE: {email.subject}",
                                response_body
                            )
                            self.inbox.append(response)
                    elif self.compose_to in ["jaxkando@ciphernet.net", "rain@ciphernet.net", "uncle-am@ciphernet.net"]:
                        # Handle emails to other NPCs using enhanced trait-based system
                        self.sent.append(email)
                        log_event(f"Email sent to {self.compose_to} | Subject: '{email.subject}'")
                        
                        # Check for help-related keywords (for Jaxkando volunteering)
                        if self.compose_to == "jaxkando@ciphernet.net":
                            email_text = (email.subject + " " + email.body).lower()
                            help_keywords = ["i want to help", "i'd like to help", "i would like to help", 
                                            "help", "crack games", "crack games for you", "help with games",
                                            "help cracking", "want to help", "like to help", "volunteer"]
                            
                            if any(keyword in email_text for keyword in help_keywords):
                                # Grant JAX1 token if not already granted
                                if not self.inventory.has_token(Tokens.JAX1):
                                    self.grant_token(Tokens.JAX1, reason="volunteered to help Jaxkando crack games")
                        
                        # Generate response using enhanced trait-based system
                        player_tokens = self.inventory.get_all_tokens()
                        response_body = self.npc.generate_response(
                            sender_email=self.compose_to,
                            email_subject=email.subject,
                            email_body=email.body,
                            player_tokens=player_tokens,
                            player_username=self.player_email
                        )
                        response = Email(
                            self.compose_to,
                            self.player_email,
                            f"RE: {email.subject}",
                            response_body
                        )
                        self.inbox.append(response)
                    else:
                        # For other recipients, add to outbox
                        self.outbox.append(email)
                        log_event(f"Email queued for {self.compose_to} | Subject: '{email.subject}'")
                    
                    # Clear compose fields
                    self.compose_subject = ""
                    self.compose_body = ""
                    self.active_field = None
                    
                    # Return to email menu
                    self.state = "email_menu"
                    self.current_module = 0
            elif self.active_field == "body":
                self.compose_body += "\n"
        else:
            # Add character (only if not on send button)
            if self.active_field != "send" and event.unicode.isprintable():
                if self.active_field == "subject" and len(self.compose_subject) < 100:
                    self.compose_subject += event.unicode
                elif self.active_field == "body" and len(self.compose_body) < 2000:
                    self.compose_body += event.unicode
    
    def handle_keyboard_navigation(self, event):
        """Handle keyboard navigation"""
        if event.key == pygame.K_r:
            if self.state == "reading" and self.selected_email:
                log_event("Reply hotkey pressed (R)")
                self.start_reply_to_selected_email()
            return

        if event.key == pygame.K_d:
            if self.state == "reading" and self.selected_email:
                log_event("Delete hotkey pressed (D)")
                self.prompt_delete_email()
            return

        if event.key == pygame.K_TAB:
            if self.state == "login_username":
                self.login_focus = "new_session" if self.login_focus == "input" else "input"
                return
            elif self.state in ("login_pin_create", "login_pin_verify", "login_success"):
                return
            elif self.state == "main_menu":
                self.current_module = (self.current_module + 1) % len(self.modules)
            elif self.state == "email_menu":
                self.current_module = (self.current_module + 1) % 4
            elif self.state == "tasks":
                tasks = self._get_visible_ops_tasks()
                if tasks:
                    self.current_task = (self.current_task + 1) % len(tasks)
            elif self.state == "team":
                self.current_team_member = (self.current_team_member + 1) % len(self.team_members)
            return

        if event.key == pygame.K_UP:
            # Handle scrolling for long content first
            if self.state == "reading":
                self.email_scroll_y -= 1  # Scroll up (decrease line offset)
                self.email_scroll_y = max(0, self.email_scroll_y)  # Don't scroll past top
            elif self.state == "front_post" and self.current_post is not None:
                self.post_scroll_y -= 1  # Scroll up (decrease line offset)
                self.post_scroll_y = max(0, self.post_scroll_y)  # Don't scroll past top
            elif self.state == "team":
                # Scroll up the bio
                self.bio_scroll_y -= 1  # Scroll up (decrease line offset)
                self.bio_scroll_y = max(0, self.bio_scroll_y)  # Don't scroll past top
            elif self.state == "main_menu":
                self.current_module = (self.current_module - 1) % len(self.modules)
            elif self.state == "email_menu":
                self.current_module = (self.current_module - 1) % 4
            elif self.state == "tasks":
                tasks = self._get_visible_ops_tasks()
                if tasks:
                    self.current_task = (self.current_task - 1) % len(tasks)
            elif self.state == "games":
                games = self._get_unlocked_games()
                if games:
                    self.current_game_index = (self.current_game_index - 1) % len(games)
            elif self.state == "inbox" or self.state == "outbox" or self.state == "sent":
                emails = self.inbox if self.state == "inbox" else (self.outbox if self.state == "outbox" else self.sent)
                if emails:
                    self.current_module = max(0, self.current_module - 1)
            elif self.state == "front_post":
                if self.current_post is None:
                    # Get list of unread posts
                    unread_posts = [i for i, post in enumerate(self.posts) if not post.get("read", False)]
                    if unread_posts:
                        self.current_module = max(0, self.current_module - 1)
        
        elif event.key == pygame.K_DOWN:
            # Handle scrolling for long content
            if self.state == "reading":
                self.email_scroll_y += 1  # Scroll down (increase line offset)
                # Limit scroll based on content length (will be calculated in draw function)
            elif self.state == "front_post" and self.current_post is not None:
                self.post_scroll_y += 1  # Scroll down (increase line offset)
            elif self.state == "team":
                # Scroll down the bio
                self.bio_scroll_y += 1  # Scroll down (increase line offset)
            elif self.state == "main_menu":
                self.current_module = (self.current_module + 1) % len(self.modules)
            elif self.state == "email_menu":
                self.current_module = (self.current_module + 1) % 4
            elif self.state == "tasks":
                tasks = self._get_visible_ops_tasks()
                if tasks:
                    self.current_task = (self.current_task + 1) % len(tasks)
            elif self.state == "games":
                games = self._get_unlocked_games()
                if games:
                    self.current_game_index = (self.current_game_index + 1) % len(games)
            elif self.state == "inbox" or self.state == "outbox" or self.state == "sent":
                emails = self.inbox if self.state == "inbox" else (self.outbox if self.state == "outbox" else self.sent)
                if emails:
                    self.current_module = min(len(emails) - 1, self.current_module + 1)
            elif self.state == "front_post":
                if self.current_post is None:
                    # Get list of unread posts
                    unread_posts = [i for i, post in enumerate(self.posts) if not post.get("read", False)]
                    if unread_posts:
                        self.current_module = min(len(unread_posts) - 1, self.current_module + 1)
        
        elif event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:
            if self.state == "main_menu":
                module_name = self.modules[self.current_module]
                if self.is_module_locked(module_name):
                    hint = self.get_module_lock_hint(module_name)
                    self.show_main_menu_message(hint)
                    return
                if module_name == "TERMINAL FEED: THE WALL":
                    self.state = "front_post"
                    self.current_module = 0
                    self.current_post = None
                    self.refresh_main_terminal_feed()
                elif module_name == "EMAIL SYSTEM":
                    self.state = "email_menu"
                    self.current_module = 0
                elif module_name == "GAMES":
                    self.state = "games"
                elif module_name == "URGENT OPS":
                    self.state = "tasks"
                    self.current_task = 0
                elif module_name == "TEAM INFO":
                    self.state = "team"
                    self.current_team_member = 0
                    self.bio_scroll_y = 0  # Reset scroll
                elif module_name == "PIRATE RADIO":
                    self.state = "radio"
                elif module_name == "LOGOUT":
                    self.prompt_logout_confirmation()
            
            elif self.state == "email_menu":
                if self.current_module == 0:
                    self.state = "compose"
                    self.compose_subject = ""
                    self.compose_body = ""
                    self.active_field = "subject"  # Start with subject field
                elif self.current_module == 1:
                    self.state = "inbox"
                    self.current_module = 0
                elif self.current_module == 2:
                    self.state = "outbox"
                    self.current_module = 0
                elif self.current_module == 3:
                    self.state = "sent"
                    self.current_module = 0
            
            elif self.state == "inbox" or self.state == "outbox" or self.state == "sent":
                emails = self.inbox if self.state == "inbox" else (self.outbox if self.state == "outbox" else self.sent)
                if emails and 0 <= self.current_module < len(emails):
                    email_obj = emails[self.current_module]
                    self.selected_email = email_obj
                    self.previous_email_state = self.state  # Remember where we came from
                    self.state = "reading"
                    self.email_scroll_y = 0  # Reset scroll when opening email
                    email_obj.read = True
                    self._on_email_marked_read(email_obj)
                    self.save_user_state()
            elif self.state == "tasks":
                tasks = self._get_visible_ops_tasks()
                if tasks:
                    selected = tasks[self.current_task]
                    method_name = selected.get("launch_method")
                    if method_name:
                        launch = getattr(self, method_name, None)
                        if callable(launch):
                            launch()
                        else:
                            self.show_main_menu_message("Assignment console unavailable.")
                return
            elif self.state == "games":
                games = self._get_unlocked_games()
                if games:
                    self.launch_game(games[self.current_game_index])
                return
            
            elif self.state == "reading":
                log_event("Opening reply from reading view via ENTER")
                self.start_reply_to_selected_email()
            
            elif self.state == "front_post":
                if self.current_post is None:
                    # Get list of unread posts
                    unread_posts = [i for i, post in enumerate(self.posts) if not post.get("read", False)]
                    if unread_posts and 0 <= self.current_module < len(unread_posts):
                        self.current_post = unread_posts[self.current_module]
                        self.post_scroll_y = 0  # Reset scroll when opening post
                        # Mark as read when viewing
                        self.posts[self.current_post]["read"] = True
            
        elif event.key == pygame.K_LEFT:
            # Navigate to previous team member
            if self.state == "team":
                self.current_team_member = (self.current_team_member - 1) % len(self.team_members)
                self.bio_scroll_y = 0  # Reset scroll when changing member
        
        elif event.key == pygame.K_RIGHT:
            # Navigate to next team member
            if self.state == "team":
                self.current_team_member = (self.current_team_member + 1) % len(self.team_members)
                self.bio_scroll_y = 0  # Reset scroll when changing member
        
        elif event.key == pygame.K_ESCAPE:
            if self.state == "compose":
                self.state = "email_menu"
                self.current_module = 0
            elif self.state == "inbox" or self.state == "outbox" or self.state == "sent":
                self.state = "email_menu"
                self.current_module = 0
            elif self.state == "reading":
                # Go back to the list we came from
                if self.previous_email_state:
                    self.state = self.previous_email_state
                else:
                    # Fallback: try to find which list contains the email
                    if self.selected_email in self.inbox:
                        self.state = "inbox"
                    elif self.selected_email in self.outbox:
                        self.state = "outbox"
                    elif self.selected_email in self.sent:
                        self.state = "sent"
                    else:
                        self.state = "email_menu"
                self.selected_email = None
                self.previous_email_state = None
                self.email_scroll_y = 0  # Reset scroll when leaving
            elif self.state == "front_post" and self.current_post is not None:
                self.current_post = None
                self.post_scroll_y = 0  # Reset scroll when leaving post
            elif self.state == "email_menu":
                self.state = "main_menu"
                self.current_module = 0
            elif self.state == "front_post":
                if self.current_post is not None:
                    self.current_post = None
                    # Reset selection to first unread post
                    unread_posts = [i for i, post in enumerate(self.posts) if not post.get("read", False)]
                    if unread_posts:
                        self.current_module = 0
                # On front post list, ESC doesn't do anything (use SPACEBAR for menu)
            elif self.state in ["games", "tasks", "team", "radio"]:
                if self.state == "games":
                    self.current_game_index = 0
                elif self.state == "tasks":
                    self.current_task = 0
                self.state = "main_menu"
                self.current_module = 0
        
        elif event.key == pygame.K_F5:
            # Toggle fullscreen/windowed mode
            self.fullscreen = not self.fullscreen
            if self.fullscreen:
                self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
            else:
                self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
            # Update screen dimensions
            self.screen_width = self.screen.get_width()
            self.screen_height = self.screen.get_height()
            # Recalculate BBS window dimensions and position using proportional scaling (maintaining aspect ratio)
            scale_x = self.screen_width / self.baseline_width
            scale_y = self.screen_height / self.baseline_height
            self.scale = min(scale_x, scale_y)  # Use minimum to maintain aspect ratio and fit on screen
            self.bbs_width = int(self.baseline_bbs_width * self.scale)
            self.bbs_height = int(self.baseline_bbs_height * self.scale)
            self.bbs_x = int(self.baseline_bbs_x * self.scale)
            self.bbs_y = int(self.baseline_bbs_y * self.scale)
            self.documentation_viewer.set_scale(self.scale)
            # Update OS mode scale if active
            if self.os_mode_active and self.os_mode:
                self.os_mode.update_scale(self.scale)
            # Reset content scroll (can be adjusted per screen if needed)
            self.content_scroll_y = 0
            # Recreate BBS surface with new dimensions
            self.bbs_surface = pygame.Surface((self.bbs_width, self.bbs_height), pygame.SRCALPHA)
            # Recreate fonts with new scale
            try:
                self.font_large = pygame.font.Font(get_data_path("Retro Gaming.ttf"), int(30 * self.scale))
                self.font_medium = pygame.font.Font(get_data_path("Retro Gaming.ttf"), int(22 * self.scale))
                self.font_medium_small = pygame.font.Font(get_data_path("Retro Gaming.ttf"), max(1, int(20 * self.scale)))
                self.font_small = pygame.font.Font(get_data_path("Retro Gaming.ttf"), int(16 * self.scale))
                self.font_tiny = pygame.font.Font(get_data_path("Retro Gaming.ttf"), int(12 * self.scale))
            except:
                self.font_large = pygame.font.Font(None, int(30 * self.scale))
                self.font_medium = pygame.font.Font(None, int(22 * self.scale))
                self.font_medium_small = pygame.font.Font(None, max(1, int(20 * self.scale)))
                self.font_small = pygame.font.Font(None, int(16 * self.scale))
                self.font_tiny = pygame.font.Font(None, int(12 * self.scale))
            # Rescale scroll values
            self.scroll_speed = int(2 * self.scale)
            self.scroll_pause_y = int(660 * self.scale)
            # Rescale scroll image if it exists
            if self.scroll_image:
                try:
                    original_scroll = pygame.image.load(get_data_path("images", "BBS_Scroll.png")).convert_alpha()
                    if original_scroll.get_width() != self.bbs_width:
                        scale_factor = self.bbs_width / original_scroll.get_width()
                        new_height = int(original_scroll.get_height() * scale_factor)
                        self.scroll_image = pygame.transform.scale(original_scroll, (self.bbs_width, new_height))
                except:
                    pass  # If we can't reload, keep the existing scaled image
        
        elif event.key == pygame.K_SPACE:
            if self.state == "front_post":
                # Spacebar takes us to main menu from Terminal Feed
                self.state = "main_menu"
                self.current_module = 0
            elif self.state == "radio":
                self.radio_playing = not self.radio_playing
                if self.radio_playing:
                    # Cycle DJ text
                    self.dj_index = (self.dj_index + 1) % len(self.dj_text)
    
    def run(self):
        """Main game loop"""
        running = True
        
        while running:
            dt = self.clock.tick(60) / 1000.0

            # Ensure ambient track keeps playing and update fade-in
            if self.ambient_sound:
                # Check if channel stopped playing (shouldn't happen with loops=-1, but just in case)
                if self.ambient_playing and self.ambient_channel and not self.ambient_channel.get_busy():
                    print("DEBUG: Ambient track stopped unexpectedly, restarting...")
                    try:
                        if not pygame.mixer.get_init():
                            pygame.mixer.init()
                        self.ambient_channel = self.ambient_sound.play(loops=-1)
                        if self.ambient_channel:
                            self.ambient_channel.set_volume(0.0)
                            self.ambient_fade_in = True
                            self.ambient_fade_start_time = pygame.time.get_ticks() / 1000.0
                    except Exception as e:
                        print(f"Warning: Failed to restart ambient track: {e}")
                
                # Update fade-in
                if self.ambient_fade_in and self.ambient_playing and self.ambient_channel:
                    current_time = pygame.time.get_ticks() / 1000.0
                    elapsed = current_time - self.ambient_fade_start_time
                    if elapsed < self.ambient_fade_duration:
                        # Fade in from 0.0 to 1.0 over fade_duration seconds
                        volume = min(1.0, elapsed / self.ambient_fade_duration)
                        self.ambient_channel.set_volume(volume)
                    else:
                        # Fade-in complete, set to full volume
                        self.ambient_channel.set_volume(1.0)
                        self.ambient_fade_in = False
                        print("DEBUG: Ambient room track fade-in complete, volume at 1.0")

            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                
                # Check for hotspot clicks
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mouse_x, mouse_y = pygame.mouse.get_pos()
                    
                    # Reset hotspot (scaled from baseline coordinates)
                    reset_x, reset_y, reset_w, reset_h = RESET_HOTSPOT
                    reset_hotspot_rect = pygame.Rect(
                        int(reset_x * self.scale),
                        int(reset_y * self.scale),
                        int(reset_w * self.scale),
                        int(reset_h * self.scale)
                    )
                    if reset_hotspot_rect.collidepoint(mouse_x, mouse_y):
                        self._reset_to_beginning()
                        continue
                    
                    # Overlay toggle hotspot (scaled from baseline coordinates)
                    overlay_x, overlay_y, overlay_w, overlay_h = OVERLAY_HOTSPOT
                    overlay_hotspot_rect = pygame.Rect(
                        int(overlay_x * self.scale),
                        int(overlay_y * self.scale),
                        int(overlay_w * self.scale),
                        int(overlay_h * self.scale)
                    )
                    if overlay_hotspot_rect.collidepoint(mouse_x, mouse_y):
                        # If OS mode is active, toggle OS mode overlay instead
                        if self.os_mode_active and self.os_mode:
                            self.os_mode.toggle_overlay()
                        else:
                            self.bbs_overlay_active = not self.bbs_overlay_active
                        continue
                
                # F12 quits the program
                if event.type == pygame.KEYDOWN and event.key == pygame.K_F12:
                    running = False
                    break

                if event.type == pygame.KEYDOWN and event.key == pygame.K_F4:
                    self.documentation_viewer.toggle_visibility()
                    continue

                if self.documentation_viewer.visible and self.documentation_viewer.handle_event(event):
                    continue

                if self.delete_confirmation_active:
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_y:
                            self.confirm_delete_user()
                        elif event.key in (pygame.K_n, pygame.K_ESCAPE):
                            self.cancel_delete_user()
                    continue

                if self.logout_modal_active:
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_y:
                            self.confirm_logout()
                        elif event.key in (pygame.K_n, pygame.K_ESCAPE):
                            self.cancel_logout_modal()
                    continue

                if self.delete_email_modal_active:
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_y:
                            self.confirm_delete_email()
                        elif event.key in (pygame.K_n, pygame.K_ESCAPE):
                            self.cancel_delete_email_modal()
                    continue

                if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                    self.prompt_delete_user()
                    continue
                
                # F10: Toggle OS Mode
                if event.type == pygame.KEYDOWN and event.key == pygame.K_F10:
                    self.os_mode_active = not self.os_mode_active
                    if self.os_mode_active:
                        # Initialize OS mode if not already initialized
                        if self.os_mode is None:
                            try:
                                # Create callback function to reset BBS and exit OS mode
                                def reset_bbs_and_exit_os():
                                    self._reset_to_beginning()
                                    self.os_mode_active = False
                                
                                self.os_mode = OSMode(self.screen, self.scale, reset_bbs_and_exit_os)
                            except Exception as e:
                                print(f"Warning: Failed to initialize OS Mode: {e}")
                                self.os_mode_active = False
                        else:
                            # Update scale if it changed
                            self.os_mode.update_scale(self.scale)
                    # Ensure cursor is visible (OS mode will handle its own cursor switching)
                    pygame.mouse.set_visible(True)
                    continue

                # Handle OS Mode events
                if self.os_mode_active and self.os_mode:
                    # ESC to exit OS mode
                    if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                        self.os_mode_active = False
                        pygame.mouse.set_visible(True)
                        continue
                    if self.os_mode.handle_event(event):
                        continue

                if self.state == "game_session" and self.active_game_session:
                    result = self.active_game_session.handle_event(event)
                    if result == "exit" or self.active_game_session.should_exit():
                        self.end_game_session()
                    continue

                if self.state == "urgent_ops_session" and self.active_ops_session:
                    result = self.active_ops_session.handle_event(event)
                    if result == "EXIT" or self.active_ops_session.should_exit():
                        self._end_ops_session()
                    continue
                
                # Allow skipping scroll animation with any key
                if self.state == "bbs_scroll" and event.type == pygame.KEYDOWN:
                    self.state = "intro"
                    self.scroll_y = None
                    self.scroll_pause_frames = 0
                    self.scroll_pause_triggered = False
                
                # Handle intro screen - advance on any keypress
                if self.state == "intro" and event.type == pygame.KEYDOWN:
                    active_user = self.get_active_user()
                    if active_user and active_user.get("username"):
                        self.state = "login_username"
                        self.login_input = ""
                        self.login_error = ""
                        self.login_message = ""
                    else:
                        self.state = "loading"
                        self.intro_timer = 0
                    continue
                
                if event.type == pygame.KEYDOWN:
                    if self.state in ("login_username", "login_pin_create", "login_pin_verify", "login_success"):
                        self.handle_login_input(event)
                        continue
                    if self.state == "compose":
                        self.handle_text_input(event)
                    else:
                        self.handle_keyboard_navigation(event)
            
            if self.state == "game_session" and self.active_game_session:
                self.active_game_session.update(dt)
                if self.active_game_session.should_exit():
                    self.end_game_session()

            if self.state == "urgent_ops_session" and self.active_ops_session:
                self.active_ops_session.update(dt)
                
                # Check for pending token grants from CRACKER IDE
                if hasattr(self.active_ops_session, 'pending_token_grants') and self.active_ops_session.pending_token_grants:
                    for token in self.active_ops_session.pending_token_grants[:]:  # Copy list to iterate safely
                        self.grant_token(token, reason=f"LAPC-1 challenge milestone: {token}")
                        self.active_ops_session.pending_token_grants.remove(token)
                
                # Check if LAPC-1 challenge is completed (all 7 nodes working)
                if hasattr(self.active_ops_session, 'challenge_completed') and self.active_ops_session.challenge_completed:
                    if hasattr(self, 'steam') and not getattr(self, '_lapc1_achievement_unlocked', False):
                        self.steam.unlock_achievement("ACH_LAPC1_READY")
                        self._lapc1_achievement_unlocked = True
                        log_event("Steam achievement unlocked: ACH_LAPC1_READY (All 7 nodes completed)")
                
                if self.active_ops_session.should_exit():
                    self._end_ops_session()

            self.documentation_viewer.update(dt)
            
            # Update OS Mode if active
            if self.os_mode_active and self.os_mode:
                self.os_mode.update(dt)
                # Check if modem modal requested BBS reset and OS exit
                if hasattr(self.os_mode, 'modem_modal_should_reset_bbs') and self.os_mode.modem_modal_should_reset_bbs:
                    if hasattr(self.os_mode, 'modem_modal_should_exit_os') and self.os_mode.modem_modal_should_exit_os:
                        self._reset_to_beginning()
                        self.os_mode_active = False
                        self.os_mode.modem_modal_should_reset_bbs = False
                        self.os_mode.modem_modal_should_exit_os = False
            
            # Run Steam API callbacks (required for achievements/stats to work)
            if hasattr(self, 'steam'):
                self.steam.run_callbacks()

            # Clear BBS surface
            self.bbs_surface.fill(BLACK)
            
            # Draw current state (BBS content)
            if self.state == "bbs_scroll":
                self.draw_bbs_scroll()
            elif self.state == "intro":
                self.draw_intro_screen()
                # No auto-advance - wait for keypress only
            elif self.state == "loading":
                self.draw_loading_screen()
            elif self.state == "main_menu":
                self.draw_main_menu()
            elif self.state == "front_post":
                self.draw_front_post_board()
            elif self.state == "email_menu" or self.state == "compose" or self.state == "inbox" or self.state == "outbox" or self.state == "sent" or self.state == "reading":
                self.draw_email_system()
            elif self.state == "games":
                self.draw_games_module()
            elif self.state == "tasks":
                self.draw_tasks_module()
            elif self.state == "team":
                self.draw_team_module()
            elif self.state == "radio":
                self.draw_radio_module()
            elif self.state == "game_session":
                if self.active_game_session:
                    self.active_game_session.draw()
                else:
                    self.state = "games"
            elif self.state == "urgent_ops_session":
                if self.active_ops_session:
                    self.active_ops_session.draw()
                else:
                    self.state = "tasks"
            elif self.state == "login_username":
                self.draw_login_username_screen()
            elif self.state == "login_pin_create":
                self.draw_login_pin_screen(create_mode=True)
            elif self.state == "login_pin_verify":
                self.draw_login_pin_screen(create_mode=False)
            elif self.state == "login_success":
                self.draw_login_success_screen()
 
            # Overlay in-game clock on the BBS window (skip during urgent ops IDE session)
            if self.state != "urgent_ops_session":
                self.draw_system_clock()

            if self.delete_confirmation_active:
                self.draw_delete_confirmation_modal()
            if self.delete_email_modal_active:
                self.draw_delete_email_modal()
            if self.logout_modal_active:
                self.draw_logout_modal()
            
            # Update desktop background/video state before rendering layers
            self._update_audio_power_state()

            # Draw BBS window first (before desktop background)
            if self.video_cap and _cv2_available:
                # Video mode: render video frame, then BBS window, then scanline overlay
                # Read next frame from video
                ret, frame = self.video_cap.read()
                if ret:
                    # Convert BGR to RGB (OpenCV uses BGR, pygame uses RGB)
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    # Resize video frame to match screen size
                    frame_resized = cv2.resize(frame_rgb, (self.screen_width, self.screen_height))
                    # Convert numpy array to pygame surface
                    # pygame.surfarray expects (width, height) format, so we need to swap axes
                    frame_swapped = np.swapaxes(frame_resized, 0, 1)
                    self.video_frame = pygame.surfarray.make_surface(frame_swapped)
                    # Draw video frame as background
                    self.screen.blit(self.video_frame, (0, 0))
                else:
                    # Video ended, loop back to beginning
                    self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ret, frame = self.video_cap.read()
                    if ret:
                        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        frame_resized = cv2.resize(frame_rgb, (self.screen_width, self.screen_height))
                        frame_swapped = np.swapaxes(frame_resized, 0, 1)
                        self.video_frame = pygame.surfarray.make_surface(frame_swapped)
                        self.screen.blit(self.video_frame, (0, 0))
                    else:
                        # Fallback if video can't be read
                        self.screen.fill(BLACK)
                
                # Draw BBS window on top of video
                self.screen.blit(self.bbs_surface, (self.bbs_x, self.bbs_y))
                
            else:
                # Normal mode: render desktop background, then BBS window
                # Draw desktop background
                if self.desktop_bg:
                    self.screen.blit(self.desktop_bg, (0, 0))
                else:
                    self.screen.fill(BLACK)
                
                # Draw BBS window on top
                self.screen.blit(self.bbs_surface, (self.bbs_x, self.bbs_y))
            
            # Draw OS Mode desktop environment (after BBS window)
            if self.os_mode_active and self.os_mode:
                self.os_mode.draw()

            overlays: list[tuple[pygame.Surface, tuple[int, int]]] = []
            if self.state == "urgent_ops_session" and self.active_ops_session:
                overlay_getter = getattr(self.active_ops_session, "get_screen_overlays", None)
                if overlay_getter:
                    try:
                        overlays = overlay_getter() or []
                    except Exception:
                        overlays = []
            # Draw thin cyan border around BBS window (on top of everything, unless OS mode is active)
            if not self.os_mode_active:
                pygame.draw.rect(self.screen, CYAN,
                                 (self.bbs_x, self.bbs_y, self.bbs_width, self.bbs_height), 1)

            for overlay_surface, (offset_x, offset_y) in overlays:
                if overlay_surface:
                    screen_pos = (self.bbs_x + offset_x, self.bbs_y + offset_y)
                    self.screen.blit(overlay_surface, screen_pos)

            # Draw OS Mode cursor (before scanlines) if in OS mode and mouse is in desktop
            if self.os_mode_active and self.os_mode:
                mouse_x, mouse_y = pygame.mouse.get_pos()
                if self.os_mode.is_mouse_in_desktop(mouse_x, mouse_y):
                    # Draw OS cursor as sprite (under scanlines)
                    self.os_mode.draw_cursor(mouse_x, mouse_y)
                    # Hide system cursor when using OS cursor
                    pygame.mouse.set_visible(False)
                else:
                    # Mouse outside desktop - show system cursor
                    pygame.mouse.set_visible(True)
            
            # Draw scanline overlay (BBS scanline when not in OS mode, desktop scanline when in OS mode)
            if self.os_mode_active and self.os_mode:
                # Draw desktop scanline in OS mode (over cursor)
                self.os_mode.draw_scanline()
                # Draw OS mode overlay rectangle (after scanline)
                self.os_mode.draw_overlay()
            elif self.scanline_image:
                # Draw BBS scanline when not in OS mode
                scanline_scaled = pygame.transform.scale(self.scanline_image, (self.bbs_width, self.bbs_height))
                self.screen.blit(scanline_scaled, (self.bbs_x, self.bbs_y))

            # Draw mouse coordinates
            mouse_x, mouse_y = pygame.mouse.get_pos()
            mouse_text = f"Mouse: {mouse_x}, {mouse_y}"
            mouse_surface = self.font_tiny.render(mouse_text, True, CYAN)
            self.screen.blit(mouse_surface, (10, 10))

            bbs_local_x = (mouse_x - self.bbs_x) / self.scale
            bbs_local_y = (mouse_y - self.bbs_y) / self.scale
            bbs_text = f"BBS Window: {int(bbs_local_x)}, {int(bbs_local_y)}"
            bbs_surface = self.font_tiny.render(bbs_text, True, CYAN)
            self.screen.blit(bbs_surface, (10, 10 + mouse_surface.get_height() + int(4 * self.scale)))
            
            self.documentation_viewer.draw(self.screen)
            self.documentation_viewer.apply_cursor()
            
            # Update cursor based on mouse position (only for areas outside OS desktop)
            if self.os_mode_active and self.os_mode:
                # OS mode is active - cursor drawing is handled above (before scanlines)
                # Only update system cursor when mouse is outside desktop
                mouse_x, mouse_y = pygame.mouse.get_pos()
                if not self.os_mode.is_mouse_in_desktop(mouse_x, mouse_y):
                    # Mouse is outside desktop - use default cursor (hand cursor)
                    is_night = _is_tokyo_nighttime()
                    mouse_buttons = pygame.mouse.get_pressed()
                    
                    if is_night:
                        if mouse_buttons[0] and self.mouse_hand_cursor_click_night:
                            cursor_to_use = self.mouse_hand_cursor_click_night
                        else:
                            cursor_to_use = self.mouse_hand_cursor_night
                    else:
                        if mouse_buttons[0] and self.mouse_hand_cursor_click:
                            cursor_to_use = self.mouse_hand_cursor_click
                        else:
                            cursor_to_use = self.mouse_hand_cursor
                    
                    if cursor_to_use:
                        try:
                            pygame.mouse.set_cursor(cursor_to_use)
                        except Exception:
                            pass
            else:
                # OS mode not active - use normal cursor logic
                self._update_cursor()
            
            # Draw black rectangles if overlay is active
            overlay_x, overlay_y, overlay_w, overlay_h = OVERLAY_HOTSPOT
            overlay_hotspot_rect = pygame.Rect(
                int(overlay_x * self.scale),
                int(overlay_y * self.scale),
                int(overlay_w * self.scale),
                int(overlay_h * self.scale)
            )
            if self.bbs_overlay_active:
                # Black rectangle covering entire BBS window
                bbs_overlay_rect = pygame.Rect(self.bbs_x, self.bbs_y, self.bbs_width, self.bbs_height)
                pygame.draw.rect(self.screen, BLACK, bbs_overlay_rect)
                
                # Black rectangle covering the overlay hotspot (stretched right 20px and down 15px, scaled)
                stretched_hotspot_rect = pygame.Rect(
                    int(overlay_x * self.scale),
                    int(overlay_y * self.scale),
                    int((overlay_w + 20) * self.scale),
                    int((overlay_h + 15) * self.scale)
                )
                pygame.draw.rect(self.screen, BLACK, stretched_hotspot_rect)
            
            # Periodically check for new emails (every 60 frames = ~1 second at 60fps)
            self._email_check_counter += 1
            if self._email_check_counter >= 60:
                self.check_email_database()
                self._email_check_counter = 0
            
            # Update display
            pygame.display.flip()
        
        # Save email state before quitting
        if hasattr(self, 'email_db'):
            self.email_db.save_sent_emails()
        
        # Cleanup video capture
        if self.video_cap:
            self.video_cap.release()
        
        # Shutdown Steam API
        if hasattr(self, 'steam'):
            self.steam.shutdown()

        try:
            pygame.mouse.set_cursor(pygame.cursors.Cursor(pygame.SYSTEM_CURSOR_ARROW))
        except Exception:
            pass
        
        pygame.quit()
        sys.exit()

    def start_reply_to_selected_email(self):
        """Open compose screen replying to the currently selected email"""
        if not self.selected_email:
            return
        recipient = self.selected_email.sender
        subject = self.selected_email.subject or ""
        if not subject.lower().startswith("re:"):
            subject = f"RE: {subject}" if subject else "RE:"
        self.compose_to = recipient
        self.compose_subject = subject
        self.compose_body = ""
        self.state = "compose"
        self.active_field = "body"
        self.current_module = 0
        log_event(f"Replying to {recipient} with subject '{subject}'")

    def draw_system_clock(self):
        """Render the system clock on the BBS window"""
        clock_text = format_ingame_clock()
        clock_surface = self.font_tiny.render(clock_text, True, CYAN)
        x = self.bbs_width - clock_surface.get_width() - int(20 * self.scale)
        y = int(10 * self.scale)
        self.bbs_surface.blit(clock_surface, (x, y))

    def prompt_delete_email(self):
        """Open confirmation modal to delete the currently viewed email."""
        if self.state != "reading" or not self.selected_email:
            return

        origin_state = self.previous_email_state
        if origin_state not in ("inbox", "outbox", "sent"):
            log_event("Delete email requested but origin mailbox unknown.")
            return

        source_list = self.inbox if origin_state == "inbox" else (self.outbox if origin_state == "outbox" else self.sent)
        if source_list is None:
            return

        try:
            index = source_list.index(self.selected_email)
        except ValueError:
            log_event("Delete email requested but message not found in mailbox.")
            return

        self.delete_email_modal_active = True
        self.delete_email_source_list = source_list
        self.delete_email_index = index
        self.delete_email_origin_state = origin_state
        log_event("Delete email confirmation opened.")

    def _reset_delete_email_modal(self):
        self.delete_email_modal_active = False
        self.delete_email_source_list = None
        self.delete_email_index = None
        self.delete_email_origin_state = None

    def cancel_delete_email_modal(self):
        """Dismiss the delete email confirmation modal."""
        if not self.delete_email_modal_active:
            return
        log_event("Email deletion cancelled.")
        self._reset_delete_email_modal()

    def confirm_delete_email(self):
        """Delete the selected email from its mailbox after confirmation."""
        if not self.delete_email_modal_active or not self.selected_email:
            return

        source_list = self.delete_email_source_list
        index = self.delete_email_index if self.delete_email_index is not None else 0
        origin_state = self.delete_email_origin_state
        email_to_remove = self.selected_email

        deleted = False
        if source_list is not None:
            if 0 <= index < len(source_list) and source_list[index] is email_to_remove:
                source_list.pop(index)
                deleted = True
            else:
                try:
                    source_list.remove(email_to_remove)
                    deleted = True
                except ValueError:
                    deleted = False

        self._reset_delete_email_modal()

        if not deleted:
            log_event("Failed to delete email; message not found in mailbox.")
            return

        log_event("Email deleted from mailbox.")
        self.selected_email = None
        self.previous_email_state = None
        self.email_scroll_y = 0

        if origin_state in ("inbox", "outbox", "sent"):
            target_list = self.inbox if origin_state == "inbox" else (self.outbox if origin_state == "outbox" else self.sent)
            self.state = origin_state
            if target_list:
                self.current_module = max(0, min(index, len(target_list) - 1))
            else:
                self.current_module = 0
        else:
            self.state = "email_menu"
            self.current_module = 0

        # Persist state (especially inbox changes)
        self.save_user_state()

    def draw_delete_email_modal(self):
        """Render the delete email confirmation overlay."""
        overlay = pygame.Surface((self.bbs_width, self.bbs_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        self.bbs_surface.blit(overlay, (0, 0))

        modal_width = int(self.bbs_width * 0.72)
        modal_height = int(self.bbs_height * 0.28)
        modal_x = (self.bbs_width - modal_width) // 2
        modal_y = (self.bbs_height - modal_height) // 2
        modal_rect = pygame.Rect(modal_x, modal_y, modal_width, modal_height)

        pygame.draw.rect(self.bbs_surface, DARK_BLUE, modal_rect)
        pygame.draw.rect(self.bbs_surface, CYAN, modal_rect, 3)

        header_text = "DELETE EMAIL"
        header_surface = self.font_medium.render(header_text, True, CYAN)
        header_pos = (
            modal_x + (modal_width - header_surface.get_width()) // 2,
            modal_y + int(20 * self.scale)
        )
        self.bbs_surface.blit(header_surface, header_pos)

        subject = ""
        if isinstance(self.selected_email, Email) and self.selected_email.subject:
            subject = self.selected_email.subject.strip()
        if not subject:
            subject = "this message"

        message_lines = [
            (f"Delete '{subject}'?", CYAN),
            ("This will remove the email from your mailbox.", RED),
            ("Press Y to confirm or N to cancel.", WHITE),
        ]

        line_y = header_pos[1] + header_surface.get_height() + int(24 * self.scale)
        for text, colour in message_lines:
            text_surface = self.font_small.render(text, True, colour)
            text_x = modal_x + (modal_width - text_surface.get_width()) // 2
            self.bbs_surface.blit(text_surface, (text_x, line_y))
            line_y += text_surface.get_height() + int(12 * self.scale)

    def prompt_logout_confirmation(self):
        """Open the confirmation modal before exiting the application."""
        if self.logout_modal_active:
            return
        self.logout_modal_active = True
        log_event("Logout confirmation opened.")

    def cancel_logout_modal(self):
        if not self.logout_modal_active:
            return
        log_event("Logout cancelled.")
        self.logout_modal_active = False

    def confirm_logout(self):
        if not self.logout_modal_active:
            return
        log_event("Logout confirmed by user.")
        self.logout_modal_active = False
        pygame.quit()
        sys.exit()

    def draw_logout_modal(self):
        """Render the logout confirmation overlay."""
        overlay = pygame.Surface((self.bbs_width, self.bbs_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        self.bbs_surface.blit(overlay, (0, 0))

        modal_width = int(self.bbs_width * 0.68)
        modal_height = int(self.bbs_height * 0.24) + int(30 * self.scale)
        modal_x = (self.bbs_width - modal_width) // 2
        modal_y = (self.bbs_height - modal_height) // 2
        modal_rect = pygame.Rect(modal_x, modal_y, modal_width, modal_height)

        pygame.draw.rect(self.bbs_surface, DARK_BLUE, modal_rect)
        pygame.draw.rect(self.bbs_surface, CYAN, modal_rect, 3)

        header_text = "CONFIRM LOGOUT"
        header_surface = self.font_medium.render(header_text, True, CYAN)
        header_pos = (
            modal_x + (modal_width - header_surface.get_width()) // 2,
            modal_y + int(20 * self.scale)
        )
        self.bbs_surface.blit(header_surface, header_pos)

        message_lines = [
            ("Logout of GLYPHIS_IO BBS?", CYAN),
            ("Press Y to confirm or N to cancel.", WHITE),
        ]

        line_y = header_pos[1] + header_surface.get_height() + int(24 * self.scale)
        for text, colour in message_lines:
            text_surface = self.font_small.render(text, True, colour)
            text_x = modal_x + (modal_width - text_surface.get_width()) // 2
            self.bbs_surface.blit(text_surface, (text_x, line_y))
            line_y += text_surface.get_height() + int(12 * self.scale)

    def prompt_delete_user(self):
        """Show confirmation modal for deleting the active user profile."""
        user = self.get_active_user()
        username = (user or {}).get("username")
        if not username:
            log_event("Delete user requested but no registered profile is active.")
            if self.state == "main_menu":
                self.show_main_menu_message("No registered user profile loaded.")
            return
        self.delete_confirmation_active = True
        self.delete_confirmation_username = username
        log_event(f"Delete user confirmation opened for '{username}'.")

    def cancel_delete_user(self):
        """Dismiss the delete user confirmation modal."""
        if not self.delete_confirmation_active:
            return
        log_event("Delete user cancelled.")
        self.delete_confirmation_active = False
        self.delete_confirmation_username = None

    def confirm_delete_user(self):
        """Delete active user and restart the BBS experience."""
        if not self.delete_confirmation_active:
            return

        target_username = self.delete_confirmation_username or "unknown"

        # Ensure any active game sessions have a chance to exit cleanly.
        if self.state == "game_session" and self.active_game_session:
            self.end_game_session()

        success = self._remove_active_user_profile()

        # Reset modal state before restarting to avoid post-reinit access.
        self.delete_confirmation_active = False
        self.delete_confirmation_username = None

        if not success:
            self.show_main_menu_message("Unable to delete user profile.")
            log_event(f"Failed to delete user profile '{target_username}'.")
            return

        log_event(f"User profile deleted: '{target_username}'. Restarting client.")
        # Reinitialise the application to reboot the experience.
        self.__init__()

    def _remove_active_user_profile(self):
        """Remove the active user record from state and persist to disk."""
        users = self.user_state.get("users", [])
        if not users:
            return False

        index = self.user_state.get("active_user_index", 0)
        if index < 0 or index >= len(users):
            index = 0

        removed_user = users.pop(index)
        username = (removed_user or {}).get("username") or "unknown"
        if users:
            self.user_state["active_user_index"] = min(index, len(users) - 1)
        else:
            self.user_state["active_user_index"] = 0

        data = {
            "users": users,
            "active_user_index": self.user_state.get("active_user_index", 0)
        }

        try:
            state_path = get_data_path("user_state.json")
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as exc:
            log_event(f"Error saving user_state.json after deleting '{username}': {exc}")
            return False

        return True

    def draw_delete_confirmation_modal(self):
        """Render the delete confirmation overlay onto the BBS surface."""
        overlay = pygame.Surface((self.bbs_width, self.bbs_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        self.bbs_surface.blit(overlay, (0, 0))

        modal_width = int(self.bbs_width * 0.75)
        modal_height = int(self.bbs_height * 0.32)
        modal_x = (self.bbs_width - modal_width) // 2
        modal_y = (self.bbs_height - modal_height) // 2
        modal_rect = pygame.Rect(modal_x, modal_y, modal_width, modal_height)

        pygame.draw.rect(self.bbs_surface, DARK_BLUE, modal_rect)
        pygame.draw.rect(self.bbs_surface, CYAN, modal_rect, 3)

        header_text = "CONFIRM USER DELETION"
        header_surface = self.font_medium.render(header_text, True, CYAN)
        header_pos = (
            modal_x + (modal_width - header_surface.get_width()) // 2,
            modal_y + int(24 * self.scale)
        )
        self.bbs_surface.blit(header_surface, header_pos)

        username = self.delete_confirmation_username or "this profile"
        message_lines = [
            (f"Delete '{username}' from GLYPHIS_IO?", CYAN),
            ("This action permanently removes the profile.", RED),
            ("Press Y to confirm or N to cancel.", WHITE),
        ]

        line_y = header_pos[1] + header_surface.get_height() + int(28 * self.scale)
        for text, colour in message_lines:
            text_surface = self.font_small.render(text, True, colour)
            text_x = modal_x + (modal_width - text_surface.get_width()) // 2
            self.bbs_surface.blit(text_surface, (text_x, line_y))
            line_y += text_surface.get_height() + int(12 * self.scale)

    def _create_blank_user(self):
        return {
            "username": None,
            "pin": None,
            "sent_emails": [],
            "tokens": [],
            "inbox_emails": [],
            "username_simulacra_tcs": None
        }

    def load_user_state(self):
        state = {"users": [], "active_user_index": 0}
        try:
            state_path = get_data_path("user_state.json")
            if os.path.exists(state_path):
                with open(state_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        if isinstance(data.get("users"), list):
                            cleaned_users = []
                            for user in data.get("users", []):
                                if not isinstance(user, dict):
                                    continue
                                cleaned = self._create_blank_user()
                                cleaned["username"] = user.get("username")
                                cleaned["pin"] = user.get("pin")
                                cleaned["sent_emails"] = list(user.get("sent_emails", []))
                                user_tokens = [normalize_token(t) for t in user.get("tokens", [])]
                                cleaned["tokens"] = list(sort_tokens(tok for tok in user_tokens if tok))
                                cleaned["inbox_emails"] = []
                                for stored_email in user.get("inbox_emails", []):
                                    if not isinstance(stored_email, dict):
                                        continue
                                    sanitized_email = {
                                        "id": stored_email.get("id"),
                                        "sender": stored_email.get("sender"),
                                        "recipient": stored_email.get("recipient"),
                                        "subject": stored_email.get("subject"),
                                        "body": stored_email.get("body"),
                                        "timestamp": stored_email.get("timestamp"),
                                        "read": bool(stored_email.get("read", False)),
                                    }
                                    cleaned["inbox_emails"].append(sanitized_email)
                                try:
                                    best_tcs = user.get("username_simulacra_tcs")
                                    cleaned["username_simulacra_tcs"] = float(best_tcs) if best_tcs is not None else None
                                except (TypeError, ValueError):
                                    cleaned["username_simulacra_tcs"] = None
                                cleaned_users.append(cleaned)
                            if cleaned_users:
                                state["users"] = cleaned_users
                                if isinstance(data.get("active_user_index"), int):
                                    idx = data.get("active_user_index", 0)
                                    idx = max(0, min(idx, len(cleaned_users) - 1))
                                    state["active_user_index"] = idx
                        else:
                            migrated_user = self._create_blank_user()
                            migrated_user["username"] = data.get("username")
                            migrated_user["pin"] = data.get("pin")
                            migrated_user["sent_emails"] = list(data.get("sent_emails", []))
                            migrated_tokens = [normalize_token(t) for t in data.get("tokens", [])]
                            migrated_user["tokens"] = list(sort_tokens(tok for tok in migrated_tokens if tok))
                            migrated_user["inbox_emails"] = []
                            for stored_email in data.get("inbox_emails", []):
                                if not isinstance(stored_email, dict):
                                    continue
                                sanitized_email = {
                                    "id": stored_email.get("id"),
                                    "sender": stored_email.get("sender"),
                                    "recipient": stored_email.get("recipient"),
                                    "subject": stored_email.get("subject"),
                                    "body": stored_email.get("body"),
                                    "timestamp": stored_email.get("timestamp"),
                                    "read": bool(stored_email.get("read", False)),
                                }
                                migrated_user["inbox_emails"].append(sanitized_email)
                            try:
                                best_tcs = data.get("username_simulacra_tcs")
                                migrated_user["username_simulacra_tcs"] = float(best_tcs) if best_tcs is not None else None
                            except (TypeError, ValueError):
                                migrated_user["username_simulacra_tcs"] = None
                            state["users"] = [migrated_user]
                            state["active_user_index"] = 0
        except Exception as e:
            log_event(f"Error loading user_state.json: {e}")

        if state["users"] and state["active_user_index"] >= len(state["users"]):
            state["active_user_index"] = 0

        return state

    def get_active_user(self):
        users = self.user_state.get("users", [])
        if not users:
            return None
        idx = self.user_state.get("active_user_index", 0)
        if idx < 0 or idx >= len(users):
            idx = 0
            self.user_state["active_user_index"] = idx
        return users[idx]

    def apply_active_user_profile(self):
        user = self.get_active_user()
        if user:
            username = user.get("username")
            self.player_email = username if username else "unknown"
            self.player_pin = user.get("pin")
            tokens = [normalize_token(t) for t in user.get("tokens", [])]
            self.inventory.tokens = set(tok for tok in tokens if tok)
            user["tokens"] = list(sort_tokens(self.inventory.tokens))
            self.email_db.sent_email_ids = set(user.get("sent_emails", []))
            self.inbox = []
            for stored_email in user.get("inbox_emails", []):
                if not isinstance(stored_email, dict):
                    continue
                email_payload = dict(stored_email)
                email_payload.setdefault("recipient", self.player_email)
                email = Email.from_dict(email_payload)
                if email:
                    self.inbox.append(email)
        else:
            self.player_email = "unknown"
            self.player_pin = None
            self.inventory.tokens = set()
            self.email_db.sent_email_ids = set()
            self.inbox = []

        if self.player_pin and not self.inventory.has_token(Tokens.PIN_SET):
            self.grant_token(Tokens.PIN_SET, reason="restored from profile")
        self.refresh_main_terminal_feed(initial=True)

    def persist_active_user_profile(self):
        users = self.user_state.setdefault("users", [])
        real_username = self.player_email
        if not real_username or real_username in ("unknown", "guest"):
            idx = self.user_state.get("active_user_index", 0)
            if users and 0 <= idx < len(users) and not users[idx].get("username"):
                users.pop(idx)
                if users:
                    self.user_state["active_user_index"] = min(idx, len(users) - 1)
                else:
                    self.user_state["active_user_index"] = 0
            return

        idx = self.user_state.get("active_user_index", 0)
        if not users or not (0 <= idx < len(users)):
            users.append(self._create_blank_user())
            idx = len(users) - 1
            self.user_state["active_user_index"] = idx

        user = users[idx]
        user["username"] = real_username
        user["pin"] = self.player_pin
        user["tokens"] = list(sort_tokens(self.inventory.tokens))
        user["sent_emails"] = sorted(self.email_db.sent_email_ids)
        serialized_inbox = []
        for email in self.inbox:
            if isinstance(email, Email):
                serialized_inbox.append(email.to_dict())
            elif isinstance(email, dict):
                serialized_inbox.append(
                    {
                        "id": email.get("id"),
                        "sender": email.get("sender"),
                        "recipient": email.get("recipient", real_username),
                        "subject": email.get("subject"),
                        "body": email.get("body"),
                        "timestamp": email.get("timestamp"),
                        "read": bool(email.get("read", False)),
                    }
                )
        user["inbox_emails"] = serialized_inbox

    def set_active_user_index(self, index):
        users = self.user_state.get("users", [])
        if not users:
            return
        index = max(0, min(index, len(users) - 1))
        current_index = self.user_state.get("active_user_index", 0)
        if index == current_index:
            self.apply_active_user_profile()
            return
        self.persist_active_user_profile()
        self.user_state["active_user_index"] = index
        self.apply_active_user_profile()

    def get_active_user_simulacra_tcs(self):
        user = self.get_active_user()
        if not user:
            return None
        value = user.get("username_simulacra_tcs")
        try:
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    def record_simulacra_score(self, tcs_value):
        result = {
            "stored": None,
            "updated": False,
            "persisted": False
        }

        try:
            attempt = float(tcs_value)
        except (TypeError, ValueError):
            return result

        user = self.get_active_user()
        if not user or not user.get("username"):
            return result

        existing_raw = user.get("username_simulacra_tcs")
        try:
            existing = float(existing_raw) if existing_raw is not None else None
        except (TypeError, ValueError):
            existing = None

        if existing is None or attempt < existing:
            user["username_simulacra_tcs"] = attempt
            self.save_user_state()
            result["stored"] = attempt
            result["updated"] = True
            result["persisted"] = True
        else:
            result["stored"] = existing

        return result

    def find_user_index(self, username):
        if not username:
            return None
        target = username.strip().lower()
        for idx, user in enumerate(self.user_state.get("users", [])):
            existing = (user.get("username") or "").strip().lower()
            if existing == target:
                return idx
        return None

    def create_new_user_profile(self):
        self.persist_active_user_profile()
        users = self.user_state.setdefault("users", [])
        users.append(self._create_blank_user())
        self.user_state["active_user_index"] = len(users) - 1
        self.apply_active_user_profile()

    def save_user_state(self):
        self.persist_active_user_profile()
        users = [u for u in self.user_state.get("users", []) if u.get("username")]

        active_username = self.player_email if self.player_email not in ("unknown", "guest") else None
        active_index = 0
        if active_username:
            for i, user in enumerate(users):
                if user.get("username") == active_username:
                    active_index = i
                    break
        elif users:
            active_index = min(self.user_state.get("active_user_index", 0), len(users) - 1)

        self.user_state["users"] = users
        self.user_state["active_user_index"] = active_index if users else 0

        data = {
            "users": users,
            "active_user_index": active_index
        }
        try:
            state_path = get_data_path("user_state.json")
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            log_event(f"Error saving user_state.json: {e}")

    def draw_login_username_screen(self):
        self.bbs_surface.fill(BLACK)
        self._draw_background_grid()
        
        # Header panel
        header_rect = self._draw_header_panel(
            "GLYPHIS_IO BBS // SYSTEM LOGIN",
            ["REGISTERED ACCOUNT DETECTED. ENTER USERNAME TO CONTINUE."]
        )
        
        # Main content panel (wider box with less margin on sides)
        panel_top = header_rect.bottom + int(30 * self.scale)
        panel_height = self.bbs_height - panel_top - int(100 * self.scale)
        content_rect = pygame.Rect(
            int(30 * self.scale),
            panel_top,
            self.bbs_width - int(60 * self.scale),
            panel_height
        )
        pygame.draw.rect(self.bbs_surface, PANEL_BLUE, content_rect)
        pygame.draw.rect(self.bbs_surface, CYAN, content_rect, 2)
        
        # Section header - ASCII art
        section_y = content_rect.y + int(25 * self.scale)
        ascii_art_lines = [
            " █████╗ ██╗   ██╗████████╗██╗  ██╗███████╗███╗   ██╗████████╗██╗ ██████╗ █████╗ ████████╗██╗ ██████╗ ███╗   ██╗",
            "██╔══██╗██║   ██║╚══██╔══╝██║  ██║██╔════╝████╗  ██║╚══██╔══╝██║██╔════╝██╔══██╗╚══██╔══╝██║██╔═══██╗████╗  ██║",
            "███████║██║   ██║   ██║   ███████║█████╗  ██╔██╗ ██║   ██║   ██║██║     ███████║   ██║   ██║██║   ██║██╔██╗ ██║",
            "██╔══██║██║   ██║   ██║   ██╔══██║██╔══╝  ██║╚██╗██║   ██║   ██║██║     ██╔══██║   ██║   ██║██║   ██║██║╚██╗██║",
            "██║  ██║╚██████╔╝   ██║   ██║  ██║███████╗██║ ╚████║   ██║   ██║╚██████╗██║  ██║   ██║   ██║╚██████╔╝██║ ╚████║",
            "╚═╝  ╚═╝ ╚═════╝    ╚═╝   ╚═╝  ╚═╝╚══════╝╚═╝  ╚═══╝   ╚═╝   ╚═╝ ╚═════╝╚═╝  ╚═╝   ╚═╝   ╚═╝ ╚═════╝ ╚═╝  ╚═══╝"
        ]
        ascii_x = content_rect.x + int(20 * self.scale)
        ascii_y = section_y
        # Use monospaced font with good Unicode support for ANSI/box-drawing characters
        # Try fonts in order of preference for box-drawing character support
        ascii_font = None
        font_names = ["Consolas", "Courier New", "Lucida Console", "DejaVu Sans Mono", "Courier"]
        for font_name in font_names:
            try:
                test_font = pygame.font.SysFont(font_name, int(12 * self.scale))
                # Test if font can render box-drawing characters
                test_surface = test_font.render("█", True, (255, 255, 255))
                if test_surface.get_width() > 0:
                    ascii_font = test_font
                    break
            except:
                continue
        # Fallback to default monospaced font if none worked
        if ascii_font is None:
            ascii_font = pygame.font.SysFont("courier", int(12 * self.scale))
        for line in ascii_art_lines:
            self.draw_text(line, ascii_font, ACCENT_CYAN, ascii_x, ascii_y)
            ascii_y += ascii_font.get_linesize()
        
        # Username input area (positioned below ASCII art)
        prompt_y = ascii_y + int(15 * self.scale)
        self.draw_text("WHAT'S YOUR NAME STRANGER:", self.font_small, CYAN, content_rect.x + int(20 * self.scale), prompt_y)
        
        # Input box
        input_box_y = prompt_y + int(35 * self.scale)
        input_box_rect = pygame.Rect(
            content_rect.x + int(20 * self.scale),
            input_box_y,
            content_rect.width - int(40 * self.scale),
            int(40 * self.scale)
        )
        box_color = ACCENT_CYAN if self.login_focus == "input" else CYAN
        pygame.draw.rect(self.bbs_surface, PANEL_BLUE, input_box_rect)
        pygame.draw.rect(self.bbs_surface, box_color, input_box_rect, 2)
        
        # Input text
        input_display = self.login_input if len(self.login_input) < 24 else self.login_input[-24:]
        caret_visible = self.login_focus == "input" and (pygame.time.get_ticks() // 500) % 2 == 0
        prefix_surface = self.font_medium.render("> ", True, CYAN)
        base_x = input_box_rect.x + int(10 * self.scale)
        render_y = input_box_y + int(8 * self.scale)
        self.bbs_surface.blit(prefix_surface, (base_x, render_y))
        x_cursor = base_x + prefix_surface.get_width()

        input_color = CYAN if self.login_focus == "input" else DARK_CYAN
        if input_display:
            input_surface = self.font_medium.render(input_display, True, input_color)
            self.bbs_surface.blit(input_surface, (x_cursor, render_y))
            x_cursor += input_surface.get_width()
        if caret_visible:
            caret_surface = self.font_medium.render("_", True, CYAN)
            self.bbs_surface.blit(caret_surface, (x_cursor, render_y))

        # Error message
        if self.login_error:
            error_y = input_box_rect.bottom + int(15 * self.scale)
            error_rect = pygame.Rect(
                content_rect.x + int(20 * self.scale),
                error_y,
                content_rect.width - int(40 * self.scale),
                int(30 * self.scale)
            )
            pygame.draw.rect(self.bbs_surface, (32, 8, 8), error_rect)
            pygame.draw.rect(self.bbs_surface, RED, error_rect, 1)
            self.draw_text(self.login_error, self.font_small, RED, error_rect.x + int(10 * self.scale), error_y + int(8 * self.scale))

        # New session option
        indicator_y = (error_y if self.login_error else input_box_rect.bottom) + int(30 * self.scale)
        self.draw_text("[ OPTIONS ]", self.font_small, ACCENT_CYAN, content_rect.x + int(20 * self.scale), indicator_y)
        
        option_y = indicator_y + int(30 * self.scale)
        base_color = CYAN if self.login_focus == "new_session" else DARK_CYAN
        if self.login_focus == "new_session":
            option_rect = pygame.Rect(
                content_rect.x + int(20 * self.scale),
                option_y - int(5 * self.scale),
                int(200 * self.scale),
                int(30 * self.scale)
            )
            pygame.draw.rect(self.bbs_surface, HIGHLIGHT_BLUE, option_rect)
            pygame.draw.rect(self.bbs_surface, ACCENT_CYAN, option_rect, 1)
        
        left_surface = self.font_small.render("( ", True, base_color)
        circle_font = get_selection_glyph_font(self.font_small.get_height())
        circle_surface = circle_font.render(SELECTION_GLYPH, True, base_color)
        right_surface = self.font_small.render(" ) NEW SESSION", True, base_color)
        base_x = content_rect.x + int(30 * self.scale)
        self.bbs_surface.blit(left_surface, (base_x, option_y))
        x_cursor = base_x + left_surface.get_width()
        self.bbs_surface.blit(circle_surface, (x_cursor, option_y - 6))
        x_cursor += circle_surface.get_width()
        self.bbs_surface.blit(right_surface, (x_cursor, option_y))

        # Footer
        footer_y = self.bbs_height - int(50 * self.scale)
        self.draw_line(footer_y)
        self.draw_text("PRESS ENTER TO SUBMIT | TAB FOR NEW SESSION | ESC TO QUIT", self.font_tiny, DARK_CYAN, int(60 * self.scale), footer_y + int(10 * self.scale))

    def draw_login_pin_screen(self, create_mode=True):
        self.bbs_surface.fill(BLACK)
        self._draw_background_grid()
        
        title = "GLYPHIS_IO BBS // PIN CONFIGURATION" if create_mode else "GLYPHIS_IO BBS // PIN AUTHENTICATION"
        
        # Header panel (no subtitle - removed "ENTER YOUR PIN" text)
        header_rect = self._draw_header_panel(title, [])
        
        # Main content panel
        panel_top = header_rect.bottom + int(30 * self.scale)
        panel_height = self.bbs_height - panel_top - int(100 * self.scale)
        content_rect = pygame.Rect(
            int(60 * self.scale),
            panel_top,
            self.bbs_width - int(120 * self.scale),
            panel_height
        )
        pygame.draw.rect(self.bbs_surface, PANEL_BLUE, content_rect)
        pygame.draw.rect(self.bbs_surface, CYAN, content_rect, 2)
        
        # Section header - ASCII art
        section_y = content_rect.y + int(25 * self.scale)
        security_ascii_lines = [
            "███████╗███████╗ ██████╗██╗   ██╗██████╗ ██╗████████╗██╗   ██╗",
            "██╔════╝██╔════╝██╔════╝██║   ██║██╔══██╗██║╚══██╔══╝╚██╗ ██╔╝",
            "███████╗█████╗  ██║     ██║   ██║██████╔╝██║   ██║    ╚████╔╝ ",
            "╚════██║██╔══╝  ██║     ██║   ██║██╔══██╗██║   ██║     ╚██╔╝  ",
            "███████║███████╗╚██████╗╚██████╔╝██║  ██║██║   ██║      ██║   ",
            "╚══════╝╚══════╝ ╚═════╝ ╚═════╝ ╚═╝  ╚═╝╚═╝   ╚═╝      ╚═╝   "
        ]
        security_ascii_x = content_rect.x + int(20 * self.scale)
        security_ascii_y = section_y
        # Use monospaced font with good Unicode support for ANSI/box-drawing characters
        security_ascii_font = None
        font_names = ["Consolas", "Courier New", "Lucida Console", "DejaVu Sans Mono", "Courier"]
        for font_name in font_names:
            try:
                test_font = pygame.font.SysFont(font_name, int(12 * self.scale))
                test_surface = test_font.render("█", True, (255, 255, 255))
                if test_surface.get_width() > 0:
                    security_ascii_font = test_font
                    break
            except:
                continue
        if security_ascii_font is None:
            security_ascii_font = pygame.font.SysFont("courier", int(12 * self.scale))
        for line in security_ascii_lines:
            self.draw_text(line, security_ascii_font, PINK, security_ascii_x, security_ascii_y)
            security_ascii_y += security_ascii_font.get_linesize()
        
        # PIN input area (positioned below ASCII art)
        prompt_y = security_ascii_y + int(15 * self.scale)
        self.draw_text("PIN:", self.font_small, CYAN, content_rect.x + int(20 * self.scale), prompt_y)
        
        # Input box
        input_box_y = prompt_y + int(35 * self.scale)
        input_box_rect = pygame.Rect(
            content_rect.x + int(20 * self.scale),
            input_box_y,
            int(200 * self.scale),
            int(40 * self.scale)
        )
        pygame.draw.rect(self.bbs_surface, PANEL_BLUE, input_box_rect)
        pygame.draw.rect(self.bbs_surface, CYAN, input_box_rect, 2)
        
        # PIN input display
        caret_visible = (pygame.time.get_ticks() // 500) % 2 == 0
        base_x = input_box_rect.x + int(10 * self.scale)
        render_y = input_box_y + int(8 * self.scale)
        prefix_surface = self.font_medium.render("> ", True, CYAN)
        self.bbs_surface.blit(prefix_surface, (base_x, render_y))
        x_cursor = base_x + prefix_surface.get_width()

        pin_font = pygame.font.SysFont(None, self.font_medium.get_height())
        for _ in self.login_input:
            bullet_surface = pin_font.render("•", True, CYAN)
            self.bbs_surface.blit(bullet_surface, (x_cursor, render_y))
            x_cursor += bullet_surface.get_width()

        if caret_visible and len(self.login_input) < 4:
            caret_surface = pin_font.render("_", True, CYAN)
            self.bbs_surface.blit(caret_surface, (x_cursor, render_y))

        # Error message
        if self.login_error:
            error_y = input_box_rect.bottom + int(15 * self.scale)
            error_rect = pygame.Rect(
                content_rect.x + int(20 * self.scale),
                error_y,
                content_rect.width - int(40 * self.scale),
                int(30 * self.scale)
            )
            pygame.draw.rect(self.bbs_surface, (32, 8, 8), error_rect)
            pygame.draw.rect(self.bbs_surface, RED, error_rect, 1)
            self.draw_text(self.login_error, self.font_small, RED, error_rect.x + int(10 * self.scale), error_y + int(8 * self.scale))

        # Footer
        footer_y = self.bbs_height - int(50 * self.scale)
        self.draw_line(footer_y)
        self.draw_text("PRESS ENTER TO SUBMIT | ESC TO QUIT", self.font_tiny, DARK_CYAN, int(60 * self.scale), footer_y + int(10 * self.scale))

    def draw_login_success_screen(self):
        self.bbs_surface.fill(BLACK)
        self._draw_background_grid()
        
        # Header panel
        header_rect = self._draw_header_panel(
            "GLYPHIS_IO BBS // ACCESS GRANTED",
            ["AUTHENTICATION SUCCESSFUL"]
        )
        
        # Success panel (matching AUTHENTICATION page box size)
        panel_top = header_rect.bottom + int(30 * self.scale)
        panel_height = self.bbs_height - panel_top - int(100 * self.scale)
        success_rect = pygame.Rect(
            int(30 * self.scale),
            panel_top,
            self.bbs_width - int(60 * self.scale),
            panel_height
        )
        pygame.draw.rect(self.bbs_surface, PANEL_BLUE, success_rect)
        pygame.draw.rect(self.bbs_surface, ACCENT_CYAN, success_rect, 3)
        
        # Status ASCII art
        status_ascii_lines = [
            "███████╗████████╗ █████╗ ████████╗██╗   ██╗███████╗        ██████╗ ███╗   ██╗██╗     ██╗███╗   ██╗███████╗",
            "██╔════╝╚══██╔══╝██╔══██╗╚══██╔══╝██║   ██║██╔════╝██╗    ██╔═══██╗████╗  ██║██║     ██║████╗  ██║██╔════╝",
            "███████╗   ██║   ███████║   ██║   ██║   ██║███████╗╚═╝    ██║   ██║██╔██╗ ██║██║     ██║██╔██╗ ██║█████╗  ",
            "╚════██║   ██║   ██╔══██║   ██║   ██║   ██║╚════██║██╗    ██║   ██║██║╚██╗██║██║     ██║██║╚██╗██║██╔══╝  ",
            "███████║   ██║   ██║  ██║   ██║   ╚██████╔╝███████║╚═╝    ╚██████╔╝██║ ╚████║███████╗██║██║ ╚████║███████╗",
            "╚══════╝   ╚═╝   ╚═╝  ╚═╝   ╚═╝    ╚═════╝ ╚══════╝        ╚═════╝ ╚═╝  ╚═══╝╚══════╝╚═╝╚═╝  ╚═══╝╚══════╝"
        ]
        status_ascii_x = success_rect.x + int(20 * self.scale)
        status_ascii_y = success_rect.y + int(25 * self.scale)
        # Use monospaced font with good Unicode support for ANSI/box-drawing characters
        status_ascii_font = None
        font_names = ["Consolas", "Courier New", "Lucida Console", "DejaVu Sans Mono", "Courier"]
        for font_name in font_names:
            try:
                test_font = pygame.font.SysFont(font_name, int(12 * self.scale))
                test_surface = test_font.render("█", True, (255, 255, 255))
                if test_surface.get_width() > 0:
                    status_ascii_font = test_font
                    break
            except:
                continue
        if status_ascii_font is None:
            status_ascii_font = pygame.font.SysFont("courier", int(12 * self.scale))
        for line in status_ascii_lines:
            self.draw_text(line, status_ascii_font, CYAN, status_ascii_x, status_ascii_y)
            status_ascii_y += status_ascii_font.get_linesize()
        
        # Success message
        message = self.login_message or "WELCOME BACK. PRESS ENTER TO CONTINUE."
        message_y = status_ascii_y + int(15 * self.scale)
        self.draw_text(message, self.font_medium, CYAN, success_rect.x + int(20 * self.scale), message_y)
        
        # Continue prompt
        prompt_y = success_rect.bottom - int(50 * self.scale)
        prompt_rect = pygame.Rect(
            success_rect.x + int(20 * self.scale),
            prompt_y,
            success_rect.width - int(40 * self.scale),
            int(35 * self.scale)
        )
        pygame.draw.rect(self.bbs_surface, HIGHLIGHT_BLUE, prompt_rect)
        pygame.draw.rect(self.bbs_surface, ACCENT_CYAN, prompt_rect, 1)
        self.draw_text("PRESS ENTER TO CONTINUE", self.font_small, CYAN, prompt_rect.x + int(10 * self.scale), prompt_y + int(8 * self.scale))
        
        # Footer
        footer_y = self.bbs_height - int(50 * self.scale)
        self.draw_line(footer_y)
        self.draw_text(f"USER: {self.player_email}", self.font_tiny, DARK_CYAN, int(60 * self.scale), footer_y + int(10 * self.scale))

    def handle_login_input(self, event):
        if event.key == pygame.K_TAB:
            log_event(f"TAB pressed during login state '{self.state}' (focus='{self.login_focus}')")
            if self.state == "login_username":
                previous_focus = self.login_focus
                self.login_focus = "new_session" if self.login_focus == "input" else "input"
                log_event(f"Login focus changed from '{previous_focus}' to '{self.login_focus}'")
            return

        if event.key == pygame.K_ESCAPE:
            pygame.quit()
            sys.exit()

        if event.key == pygame.K_BACKSPACE:
            self.login_input = self.login_input[:-1]
            return

        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            if self.state == "login_username":
                if self.login_focus == "new_session":
                    log_event("Starting new session from login screen")
                    self.start_new_session()
                    return
                entered_username = self.login_input.strip()
                if not entered_username:
                    self.login_error = "ENTER USERNAME."
                    return
                user_index = self.find_user_index(entered_username)
                if user_index is None:
                    self.login_error = "USERNAME NOT RECOGNISED."
                    return
                log_event(f"User '{entered_username}' selected from login screen")
                self.set_active_user_index(user_index)
                self.login_error = ""
                self.login_input = ""
                self.login_focus = "input"
                self.save_user_state()
                if self.player_pin:
                    self.state = "login_pin_verify"
                else:
                    self.state = "login_pin_create"
            elif self.state == "login_pin_create":
                if len(self.login_input) == 4 and self.login_input.isdigit():
                    self.player_pin = self.login_input
                    self.save_user_state()
                    if not self.inventory.has_token(Tokens.PIN_SET):
                        self.grant_token(Tokens.PIN_SET, reason="login PIN configured")
                    self.login_message = "PIN SAVED. PRESS ENTER TO CONTINUE."
                    self.login_input = ""
                    self.login_error = ""
                    self.state = "login_success"
                else:
                    self.login_error = "PIN MUST BE 4 DIGITS."
            elif self.state == "login_pin_verify":
                stored_pin = self.player_pin or ""
                if self.login_input == stored_pin:
                    self.player_pin = stored_pin
                    if not self.inventory.has_token(Tokens.PIN_SET):
                        self.grant_token(Tokens.PIN_SET, reason="login PIN verified")
                    self.login_message = "ACCESS GRANTED. PRESS ENTER TO CONTINUE."
                    self.login_input = ""
                    self.login_error = ""
                    self.state = "login_success"
                else:
                    self.login_error = "INCORRECT PIN." 
                    self.login_input = ""
            elif self.state == "login_success":
                self.login_input = ""
                self.login_error = ""
                self.login_message = ""
                self.loading_progress = 0
                self.loading_complete = False
                self.state = "loading"
            return

        if event.type == pygame.KEYDOWN and event.unicode:
            char = event.unicode
            if self.state == "login_username":
                if self.login_focus != "input":
                    return
                if char.isprintable() and len(self.login_input) < 32:
                    self.login_input += char
                    self.login_error = ""
            elif self.state in ("login_pin_create", "login_pin_verify"):
                if char.isdigit() and len(self.login_input) < 4:
                    self.login_input += char
                    self.login_error = ""

    def send_glyphis_username_reply(self, original_email):
        body_lower = (original_email.body or "").lower()
        username = self.player_email
        if any(word in body_lower for word in ["thank", "thanks", "thx", "appreciate"]):
            reply_body = (
                "APPRECIATED. GRATITUDE IS OPTIONAL, RESULTS AREN'T.\n\n"
                f"ACCOUNT '{username}' IS ACTIVE. NEXT TIME YOU LOG IN, THE SYSTEM WILL PROMPT YOU TO SET A FOUR-DIGIT PIN. "
                "COMMIT IT TO MEMORY - THAT PIN IS YOUR KEY INTO THE BBS.\n\n"
                "- GLYPHIS"
            )
        else:
            reply_body = (
                f"A USER OF LITTLE WORDS. THAT SUITS ME JUST FINE. I DO THE TALKING AROUND HERE.\n\n"
                f"ACCOUNT '{username}' IS ACTIVE. NEXT LOGIN WILL ASK YOU FOR A FOUR-DIGIT PIN. "
                "ENTER IT ONCE AND IT BECOMES YOUR ACCESS CODE.\n\n"
                "- GLYPHIS"
            )

        original_subject = original_email.subject or ""
        if original_subject.lower().startswith("re:"):
            reply_subject = original_subject
        else:
            reply_subject = f"RE: {original_subject}" if original_subject else "RE:"

        reply = Email("glyphis@ciphernet.net", username, reply_subject, reply_body)
        self.inbox.append(reply)
        log_event("Glyphis auto-replied to username registration")

    def _handle_token_acquired(self, token: str) -> None:
        message = self.token_unlock_messages.get(token)
        if message:
            self.show_main_menu_message(message)

        if token == Tokens.UNCLE_AM_1:
            self.deliver_email_to_player("uncle_am_audio_ops_001")
        
        # Check if user has both JAX1 and AUDIO_ON tokens (after granting AUDIO_ON)
        if token == Tokens.AUDIO_ON:
            if self.inventory.has_token(Tokens.JAX1):
                # User has both tokens - deliver Jaxkando's ASTRO-MINER email
                self._deliver_jaxkando_astrominer_email()
    
    def _deliver_jaxkando_astrominer_email(self):
        """Deliver Jaxkando's email introducing ASTRO-MINER game cracking task."""
        username = self.player_email.split("@")[0] if "@" in self.player_email else self.player_email
        
        subject = "ASTRO-MINER - Ready to Crack!"
        body = (
            f"Hey {username}!\n\n"
            "I was MIGHTY impressed with how quickly you got that complicated LAPC-1\n"
            "Soundcard working on your Bradstation 69000! That was seriously cool!\n\n"
            "So, I've got a game for you to crack. It's called ASTRO-MINER.\n"
            "It's a game about mining asteroids, laser beams, trading, and landing...\n\n"
            "Yes, I said landing! *slightly ironic but excited tone*\n\n"
            "The crack file is loaded into the CRACKER IDE, and the documentation\n"
            "for the copy-protection is in the manual. All you have to do is find\n"
            "the loop within the code that performs the copy check and using the\n"
            "BBS's reverse engineering debugger, just insert some code that will\n"
            "jump over it.\n\n"
            "I'll be in the chat to help, but once that's done, then the game will\n"
            "be available for everyone to play, and I'll even wire up the global\n"
            "leaderboard for extra funtimes!\n\n"
            "Let's do this!\n\n"
            "-jaxkando"
        )
        
        email = Email(
            "jaxkando@ciphernet.net",
            self.player_email,
            subject,
            body
        )
        self.inbox.append(email)
        log_event("Jaxkando delivered ASTRO-MINER cracking task email")

    def grant_token(self, token: str, *, reason: Optional[str] = None) -> bool:
        code = normalize_token(token)
        if not code:
            return False
        added = self.inventory.add_token(code)
        if added:
            label = describe_token(code)
            if reason:
                log_event(f"Token acquired: {label} ({reason})")
            else:
                log_event(f"Token acquired: {label}")
            self.save_user_state()
            self.refresh_main_terminal_feed()
            self._handle_token_acquired(code)
            
            # Unlock Steam achievements for key milestones
            if hasattr(self, 'steam'):
                achievement_map = {
                    Tokens.PSEM: "ACH_FIRST_STEPS",  # Email system unlocked
                    Tokens.USERNAME_SET: "ACH_REGISTERED",  # Username registered
                    Tokens.GAMES1: "ACH_GAMES_UNLOCKED",  # Games module unlocked
                    Tokens.AUDIO1: "ACH_AUDIO_OPS",  # Audio ops unlocked
                    # Note: ACH_LAPC1_READY is unlocked when all 7 nodes are completed, not here
                }
                achievement_id = achievement_map.get(code)
                if achievement_id:
                    self.steam.unlock_achievement(achievement_id)
        return added

    def start_new_session(self):
        log_event("Starting new session")
        self.create_new_user_profile()
        self.player_email = "unknown"
        self.player_pin = None
        self.inbox.clear()
        self.outbox.clear()
        self.sent.clear()
        self.email_db.sent_email_ids.clear()
        self.inventory.clear()
        self.login_input = ""
        self.login_error = ""
        self.login_message = ""
        self.login_focus = "input"
        self.save_user_state()
        self.state = "loading"
        self.loading_progress = 0
        self.loading_complete = False

    def deliver_email_to_player(self, email_id, placeholders=None):
        email = self.email_db.deliver_email_by_id(email_id, self.player_email, placeholders=placeholders)
        if email:
            self.inbox.append(email)
            self.save_user_state()
            log_event(f"Delivered email '{email.subject}' from {email.sender}")
            return True
        return False

if __name__ == "__main__":
    app = GLYPHIS_IOBBS()
    app.run()

