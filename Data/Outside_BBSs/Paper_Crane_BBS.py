import pygame
from typing import Callable, Optional

try:
    from utils import get_data_path
except Exception:
    # Fallback for standalone import during development
    import os
    import sys

    def get_data_path(*path_parts):
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base, *path_parts)


PINK = (255, 56, 182)
PINK_DIM = (180, 30, 130)
BG = (0, 0, 0)
TEXT = (255, 200, 235)
ERROR = (255, 80, 120)
ACCENT = (120, 255, 230)


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
        self.font_title = self._load_font("PressStart2P.ttf", int(26 * self.scale), bold=False)
        self.font_label = self._load_font("PressStart2P.ttf", int(18 * self.scale), bold=False)
        self.font_body = self._load_font("Retro Gaming.ttf", int(18 * self.scale), bold=False)
        self.font_small = self._load_font("Retro Gaming.ttf", int(14 * self.scale), bold=False)

        # Assets
        self.splash_image = self._load_splash_image()

        # State
        self.state = "splash"
        self.username = ""
        self.password = ""
        self.focus = "username"  # username | password
        self.error_message = ""
        self.menu_options = ["SYSOP", "アーカイブ", "LOGS", "END CALL"]
        self.menu_index = 0
        self.active_panel: Optional[str] = None
        self.cursor_timer = 0.0
        self.cursor_visible = True
        self.request_exit = False

    def _load_font(self, filename: str, size: int, bold: bool = False) -> pygame.font.Font:
        try:
            font = pygame.font.Font(get_data_path(filename), max(1, size))
            if bold and hasattr(font, "set_bold"):
                font.set_bold(True)
            return font
        except Exception:
            return pygame.font.Font(None, max(1, size))

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

    def update(self, dt: float) -> None:
        self.cursor_timer += dt
        if self.cursor_timer >= 0.5:
            self.cursor_timer = 0.0
            self.cursor_visible = not self.cursor_visible

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type != pygame.KEYDOWN:
            return False

        if self.state == "splash":
            if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                self.state = "login"
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
                    self.state = "panel"
                return True
            if event.key == pygame.K_ESCAPE:
                self._end_call()
                return True
            return False

        if self.state == "panel":
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

    def _draw_grid(self, surface: pygame.Surface) -> None:
        step = max(24, int(32 * self.scale))
        for x in range(0, self.width, step):
            pygame.draw.line(surface, PINK_DIM, (x, 0), (x, self.height), 1)
        for y in range(0, self.height, step):
            pygame.draw.line(surface, PINK_DIM, (0, y), (self.width, y), 1)
        pygame.draw.rect(surface, PINK, surface.get_rect(), 3)

    def _draw_splash(self, surface: pygame.Surface) -> None:
        if self.splash_image:
            rect = self.splash_image.get_rect(center=surface.get_rect().center)
            surface.blit(self.splash_image, rect)
        prompt = "SPACE TO LOG IN"
        text = self.font_label.render(prompt, True, TEXT)
        surface.blit(text, (self.width // 2 - text.get_width() // 2, int(self.height * 0.82)))

    def _draw_login(self, surface: pygame.Surface) -> None:
        padding = int(32 * self.scale)
        top = padding * 2
        title = self.font_title.render("PAPER CRANE BBS", True, PINK)
        surface.blit(title, (self.width // 2 - title.get_width() // 2, top))

        box_w = int(self.width * 0.7)
        box_h = int(60 * self.scale)
        start_y = int(self.height * 0.4)

        self._draw_input_box(
            surface,
            label="USERNAME",
            value=self.username,
            x=self.width // 2 - box_w // 2,
            y=start_y,
            w=box_w,
            h=box_h,
            focused=self.focus == "username",
            mask=False,
        )
        self._draw_input_box(
            surface,
            label="PASSWORD",
            value=self.password,
            x=self.width // 2 - box_w // 2,
            y=start_y + box_h + padding,
            w=box_w,
            h=box_h,
            focused=self.focus == "password",
            mask=True,
        )

        hint = self.font_small.render("ENTER to submit • TAB to switch • ESC to hang up", True, TEXT)
        surface.blit(hint, (self.width // 2 - hint.get_width() // 2, start_y + box_h * 2 + padding))

        if self.error_message:
            err = self.font_body.render(self.error_message, True, ERROR)
            surface.blit(err, (self.width // 2 - err.get_width() // 2, start_y - int(48 * self.scale)))

    def _draw_input_box(self, surface, label, value, x, y, w, h, focused=False, mask=False):
        label_surf = self.font_body.render(label, True, PINK)
        surface.blit(label_surf, (x, y - int(26 * self.scale)))

        rect = pygame.Rect(x, y, w, h)
        pygame.draw.rect(surface, PINK if focused else PINK_DIM, rect, 2)

        display_value = ("*" * len(value)) if mask else value
        if focused and self.cursor_visible:
            display_value += "_"
        val_surf = self.font_body.render(display_value or " ", True, TEXT)
        surface.blit(val_surf, (x + int(12 * self.scale), y + h // 2 - val_surf.get_height() // 2))

    def _draw_menu(self, surface: pygame.Surface) -> None:
        title = self.font_title.render("PAPER CRANE", True, PINK)
        surface.blit(title, (self.width // 2 - title.get_width() // 2, int(40 * self.scale)))

        menu_x = int(self.width * 0.2)
        menu_y = int(140 * self.scale)
        line_h = int(48 * self.scale)

        for idx, option in enumerate(self.menu_options):
            color = ACCENT if idx == self.menu_index and self.state == "menu" else TEXT
            surf = self.font_body.render(option, True, color)
            surface.blit(surf, (menu_x, menu_y + idx * line_h))
            if idx == self.menu_index and self.state == "menu":
                pygame.draw.rect(surface, PINK, pygame.Rect(menu_x - int(14 * self.scale), menu_y + idx * line_h - int(6 * self.scale), surf.get_width() + int(28 * self.scale), surf.get_height() + int(12 * self.scale)), 1)

    def _draw_panel(self, surface: pygame.Surface) -> None:
        panel_rect = pygame.Rect(int(self.width * 0.45), int(140 * self.scale), int(self.width * 0.45), int(self.height * 0.5))
        pygame.draw.rect(surface, PINK_DIM, panel_rect, 2)
        header = self.active_panel or ""
        header_surf = self.font_label.render(header, True, PINK)
        surface.blit(header_surf, (panel_rect.x + int(16 * self.scale), panel_rect.y + int(12 * self.scale)))

        body_lines = self._get_panel_body(self.active_panel)
        y = panel_rect.y + int(52 * self.scale)
        for line in body_lines:
            body_surf = self.font_small.render(line, True, TEXT)
            surface.blit(body_surf, (panel_rect.x + int(16 * self.scale), y))
            y += int(28 * self.scale)

        prompt = self.font_small.render("ENTER / ESC to return", True, TEXT)
        surface.blit(prompt, (panel_rect.x + int(16 * self.scale), panel_rect.bottom - int(32 * self.scale)))

    def _get_panel_body(self, panel: Optional[str]):
        if panel == "SYSOP":
            return [
                "SYSOP: KITSUNE",
                "Signal tuned at midnight.",
                "Keep the line clean.",
            ]
        if panel == "アーカイブ":
            return [
                "ARCHIVE QUEUE:",
                "  • Firmware dumps",
                "  • Broadcast captures",
                "  • Orphaned TXT files",
            ]
        if panel == "LOGS":
            return [
                "LOG TRACE:",
                "  > handshake ok",
                "  > auth guest/origami",
                "  > encrypted channel open",
            ]
        return []

    def _attempt_login(self) -> None:
        if self.username.strip().lower() == "guest" and self.password.strip().lower() == "origami":
            self.state = "menu"
            self.error_message = ""
            self.menu_index = 0
            self.active_panel = None
        else:
            self.error_message = "ACCESS DENIED"
            self.password = ""

    def _end_call(self) -> None:
        self.request_exit = True
        if self.on_exit:
            self.on_exit()
