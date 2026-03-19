import math
import pygame
import os
import sys
import json
import random
from datetime import datetime
from typing import Callable, Dict, Optional

try:
    from utils import get_data_path
except Exception:
    def get_data_path(*path_parts):
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        return os.path.join(base, *path_parts)

# ── colour palette ──────────────────────────────────────────────────
ROSE = (186, 88, 99)        # #ba5863  — primary text / frames
BLUE = (48, 149, 203)       # #3095cb  — secondary text / frames
BG = (30, 21, 65)           # #1e1541  — background
TEXT = (220, 210, 230)       # light lavender for body text
GOLD = (255, 215, 0)        # highlight / scroll indicators
ERROR = (255, 70, 70)       # error messages
DIM_ROSE = (120, 55, 65)    # muted rose for inactive elements
DIM_BLUE = (30, 90, 130)    # muted blue for inactive elements
BG_DARK = (20, 14, 45)      # darker background for panels

_DIR = os.path.dirname(os.path.abspath(__file__))
_RISE_NEW_VOICES_HOURLY_DIR = get_data_path(
    "Social_Engineering",
    "Fugamatchi_Concert",
    "Rise_New_Voices_Tracks&Tones",
)


def _get_hourly_rise_new_voices_path() -> Optional[str]:
    hour_index = datetime.now().hour + 1
    base_names = [
        f"Rise_Voices_{hour_index:02d}",
        f"Rise_New_Voices_{hour_index:02d}",
    ]
    for base_name in base_names:
        for ext in (".mp3", ".wav"):
            candidate = os.path.join(_RISE_NEW_VOICES_HOURLY_DIR, base_name + ext)
            if os.path.isfile(candidate):
                return candidate
    return None


class NeverAgainBBS:
    """
    Outside-BBS experience for the NEVER AGAIN dial-in.

    States
    ------
    connecting       Loading bar + technobabble
    startscreen      startscreen.png with NEW USER / LOGIN / EXIT
    new_user         Username + 4-digit PIN creation
    login            Username + 4-digit PIN verification
    ansi_scroll      Auto-scroll ansi-scroll.png top→bottom
    ansi_pause       Bottom of scroll; "PRESS SPACE" flashing
    menu             Main menu: TRANSMISSIONS / FUGAMATCHI / END CALL
    panel            Active content panel
    """

    # ────────────────────────────────────────────────────────────────
    #  INIT
    # ────────────────────────────────────────────────────────────────
    def __init__(
        self,
        width: int,
        height: int,
        scale: float,
        on_exit: Optional[Callable[[], None]] = None,
        on_grant_token: Optional[Callable[[str, Optional[str]], bool]] = None,
        on_download_track: Optional[Callable[[str], None]] = None,
        get_region: Optional[Callable[[], int]] = None,
        has_token: Optional[Callable[[str], bool]] = None,
    ):
        self.width = width
        self.height = height
        self.scale = scale
        self.on_exit = on_exit
        self.on_grant_token = on_grant_token
        self.on_download_track = on_download_track
        self.get_region = get_region
        self.has_token = has_token or (lambda token: False)
        self.download_error_timer = 0.0
        self.download_error_message = ""

        # fonts
        self.font_title = self._load_font("misaki_gothic_2nd.ttf", int(32 * self.scale))
        self.font_label = self._load_font("misaki_gothic_2nd.ttf", int(22 * self.scale))
        self.font_body  = self._load_font("misaki_gothic_2nd.ttf", int(22 * self.scale))
        self.font_small = self._load_font("misaki_gothic_2nd.ttf", int(17 * self.scale))

        # images
        self.startscreen_image = self._load_image("startscreen.png", 0.82)
        self.ansi_image = self._load_scroll_image("ansi-scroll.png")
        self.layer_background = self._load_image("never-againlayer-background.png", 1.0)

        # scanline overlay
        self.scanline_surf = self._create_scanline_surface()

        # ── connection state ────────────────────────────────────────
        self.state = "connecting"
        self.connect_messages = [
            "CARRIER DETECT... 9600 BAUD",
            "NEGOTIATING ANALOG HANDSHAKE...",
            "RESOLVING FREQUENCY: 03-4089-9891...",
            "BYPASSING PACIFICA SURVEILLANCE LAYER...",
            "ROUTING VIA KANTO RELAY NODE-7...",
            "ENCRYPTING SIGNAL PATH...",
            "SYNCHRONIZING WITH HOST...",
            "HANDSHAKE COMPLETE // WELCOME TO NEVER AGAIN",
        ]
        self.connect_index = 0
        self.connect_timer = 0.0
        self.connect_delay = 0.6  # seconds between messages

        # ── startscreen state ───────────────────────────────────────
        self.start_options = ["NEW USER", "LOGIN", "EXIT"]
        self.start_index = 0

        # ── login / new-user state ──────────────────────────────────
        self.input_username = ""
        self.input_pin = ""
        self.input_pin_confirm = ""
        self.input_focus = "username"  # username | pin | pin_confirm
        self.error_message = ""
        self.cursor_timer = 0.0
        self.cursor_visible = True
        self.logged_in_user: Optional[str] = None

        # ── ansi-scroll state (matches main.py BBS scroll behaviour) ─
        self.scroll_y: Optional[float] = None   # current y position of image (starts at self.height)
        self.scroll_speed = int(2 * self.scale)  # pixels per frame, same as main BBS
        self.scroll_pause_frames = 0             # frames remaining in temporary pause
        self.scroll_pause_y = int(660 * self.scale)  # bottom-of-image y where pause triggers
        self.scroll_pause_triggered = False
        self.scroll_final_paused = False
        self.ansi_flash_timer = 0.0

        # ── menu state ──────────────────────────────────────────────
        self.menu_options = ["TRANSMISSIONS", "FUGAMATCHI", "END CALL"]
        self.menu_index = 0
        self.menu_glow_timer = 0.0
        self.active_panel: Optional[str] = None

        # ── transmissions (wall) state ──────────────────────────────
        self.all_posts = self._load_wall_posts()
        self.visible_posts: list = []
        self.trans_selected = 0
        self.trans_list_scroll = 0
        self.trans_open_post: Optional[dict] = None
        self.trans_detail_scroll = 0
        self.replying = False
        self.reply_text = ""

        # ── fugamatchi music state ──────────────────────────────────
        self.audio_tracks = self._load_audio_tracks()
        self.audio_selected = 0
        self.current_playing_track: Optional[int] = None
        self.showing_lyrics = False
        self.lyrics_scroll = 0
        self.track_list_scroll = 0
        self.audio_welcome_scroll = 0
        self.fugamatchi_focus = "tracks"  # "tracks" | "welcome" — TAB to switch
        self.fugamatchi_sub = "play"  # "play" | "lyrics" | "download" — when on track row
        self.downloading_tracks: Dict[int, float] = {}  # track index -> progress 0.0–1.0 (multiple concurrent)
        self.download_duration = 25.0  # base seconds per file; +33% per extra concurrent download
        self.audio_message = (
            "WELCOME TO THE FUGAMATCHI ARCHIVE. "
            "You found us — maybe through Hotline Underground at 74.25 kHz, "
            "maybe a friend slipped you the number. However you got here — welcome. "
            "Never Again was built by seniors at Tokyo Metro. "
            "Riley shared the number live on air because Fugamatchi's music "
            "deserves to be heard. His voice carried the truth when every other "
            "channel was silenced. The American administration banned his records, "
            "shut down his broadcasts, but they cannot stop the signal. "
            "Download his tracks. Read his lyrics. Share your story. "
            "\"We do not forget. We do not comply.\" — THE NEVER AGAIN CREW"
        )

        self.request_exit = False

    # ────────────────────────────────────────────────────────────────
    #  ASSET HELPERS
    # ────────────────────────────────────────────────────────────────
    def _load_font(self, filename: str, size: int) -> pygame.font.Font:
        try:
            path = os.path.join(_DIR, filename)
            if os.path.exists(path):
                return pygame.font.Font(path, max(1, size))
            return pygame.font.Font(get_data_path(filename), max(1, size))
        except Exception:
            return pygame.font.Font(None, max(1, size))

    def _load_image(self, filename: str, max_frac: float) -> Optional[pygame.Surface]:
        try:
            path = os.path.join(_DIR, filename)
            img = pygame.image.load(path).convert_alpha()
            iw, ih = img.get_size()
            mw = int(self.width * max_frac)
            mh = int(self.height * max_frac)
            s = min(mw / iw, mh / ih, 1.0)
            if s < 1.0:
                img = pygame.transform.smoothscale(img, (int(iw * s), int(ih * s)))
            return img
        except Exception:
            return None

    def _load_scroll_image(self, filename: str) -> Optional[pygame.Surface]:
        """Load an image and scale it to the exact BBS width (like main.py scroll)."""
        try:
            path = os.path.join(_DIR, filename)
            img = pygame.image.load(path).convert_alpha()
            iw, ih = img.get_size()
            if iw != self.width:
                scale_factor = self.width / iw
                new_h = int(ih * scale_factor)
                img = pygame.transform.scale(img, (self.width, new_h))
            return img
        except Exception:
            return None

    def _create_scanline_surface(self) -> pygame.Surface:
        surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        for y in range(0, self.height, 4):
            pygame.draw.line(surf, (0, 0, 0, 40), (0, y), (self.width, y))
        return surf

    # ────────────────────────────────────────────────────────────────
    #  USER / CREDENTIAL MANAGEMENT
    # ────────────────────────────────────────────────────────────────
    def _users_path(self) -> str:
        return os.path.join(_DIR, "users.json")

    def _load_users(self) -> dict:
        p = self._users_path()
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"users": {}}

    def _save_users(self, data: dict) -> None:
        try:
            with open(self._users_path(), "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def _create_user(self, username: str, pin: str) -> bool:
        data = self._load_users()
        key = username.strip().upper()
        if key in data["users"]:
            self.error_message = "USERNAME ALREADY EXISTS"
            return False
        data["users"][key] = {"pin": pin, "replies": {}}
        self._save_users(data)
        return True

    def _verify_login(self, username: str, pin: str) -> bool:
        data = self._load_users()
        key = username.strip().upper()
        user = data["users"].get(key)
        if user and user.get("pin") == pin:
            return True
        return False

    def _save_user_reply(self, post_id: int, text: str) -> None:
        if not self.logged_in_user:
            return
        data = self._load_users()
        key = self.logged_in_user
        user = data["users"].get(key)
        if user is None:
            return
        replies = user.setdefault("replies", {})
        post_replies = replies.setdefault(str(post_id), [])
        post_replies.append(text)
        self._save_users(data)

    def _get_user_replies(self, post_id: int) -> list:
        if not self.logged_in_user:
            return []
        data = self._load_users()
        user = data["users"].get(self.logged_in_user, {})
        return user.get("replies", {}).get(str(post_id), [])

    # ────────────────────────────────────────────────────────────────
    #  WALL POSTS
    # ────────────────────────────────────────────────────────────────
    def _load_wall_posts(self) -> list:
        p = os.path.join(_DIR, "wall_posts.json")
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return data.get("posts", [])
            except Exception:
                pass
        return []

    def _randomise_wall(self) -> None:
        """Pick a random selection of 15-20 posts for this session."""
        pool = list(self.all_posts)
        count = min(len(pool), random.randint(15, 20))
        self.visible_posts = random.sample(pool, count)
        self.trans_selected = 0
        self.trans_list_scroll = 0
        self.trans_open_post = None
        self.trans_detail_scroll = 0

    # ────────────────────────────────────────────────────────────────
    #  AUDIO TRACKS
    # ────────────────────────────────────────────────────────────────
    def _load_audio_tracks(self) -> list:
        tracks: list = []
        rise_track_found = False
        audio_folder = os.path.join(_DIR, "Fugamatchi")
        if not os.path.isdir(audio_folder):
            return tracks
        try:
            files = sorted(
                f for f in os.listdir(audio_folder)
                if f.lower().endswith((".wav", ".mp3"))
            )
        except Exception:
            files = []
        for fn in files:
            base = os.path.splitext(fn)[0]
            title = base
            if "_" in title:
                parts = title.split("_", 1)
                if parts[0].isdigit():
                    title = parts[1]
            title = title.replace("_", " ")
            entry: dict = {"title": title, "file": base, "filename": fn}
            if title.lower().startswith("rise new voices"):
                rise_track_found = True
                if self.has_token("SCHOOL_HACK5"):
                    entry["hourly_variant"] = True
            # Try lyrics: same dir as audio (base.txt), then Lyrics subfolder (title)
            lyrics_path = os.path.join(audio_folder, base + ".txt")
            if not os.path.exists(lyrics_path):
                lyrics_path = os.path.join(audio_folder, "Lyrics", title + ".txt")
            if os.path.exists(lyrics_path):
                try:
                    with open(lyrics_path, "r", encoding="utf-8") as lf:
                        entry["lyrics"] = [ln.strip() for ln in lf.readlines()]
                except Exception:
                    pass
            tracks.append(entry)
        if self.has_token("SCHOOL_HACK5") and not rise_track_found:
            hourly_entry = {"title": "Rise New Voices", "hourly_variant": True}
            lyrics_path = os.path.join(audio_folder, "Lyrics", "Rise New Voices.txt")
            if os.path.exists(lyrics_path):
                try:
                    with open(lyrics_path, "r", encoding="utf-8") as lf:
                        hourly_entry["lyrics"] = [ln.strip() for ln in lf.readlines()]
                except Exception:
                    pass
            tracks.append(hourly_entry)
        return tracks

    def _play_track(self, index: int) -> None:
        if index < 0 or index >= len(self.audio_tracks):
            return
        track = self.audio_tracks[index]
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            audio_dir = os.path.join(_DIR, "Fugamatchi")
            audio_path = None
            if track.get("hourly_variant"):
                audio_path = _get_hourly_rise_new_voices_path()
            if not audio_path and track.get("file"):
                for ext in (".wav", ".mp3"):
                    p = os.path.join(audio_dir, track["file"] + ext)
                    if os.path.exists(p):
                        audio_path = p
                        break
            if audio_path:
                pygame.mixer.music.stop()
                pygame.mixer.music.load(audio_path)
                pygame.mixer.music.set_volume(0.8)
                pygame.mixer.music.play(-1)
                self.current_playing_track = index
        except Exception:
            self.current_playing_track = index

    # ────────────────────────────────────────────────────────────────
    #  TEXT HELPERS
    # ────────────────────────────────────────────────────────────────
    def _render(self, font: pygame.font.Font, text: str, color) -> pygame.Surface:
        return font.render(text.upper(), True, color)

    def _shadow(self, surface: pygame.Surface, font: pygame.font.Font,
                text: str, color, pos, off=(2, 2), scol=(0, 0, 0)):
        t = text.upper()
        sh = font.render(t, True, scol)
        surface.blit(sh, (pos[0] + off[0], pos[1] + off[1]))
        surface.blit(font.render(t, True, color), pos)

    def _wrap(self, lines: list, font: pygame.font.Font, max_w: int) -> list:
        out: list = []
        for line in lines:
            line = line.upper()
            if not line.strip():
                out.append("")
                continue
            words = line.split(" ")
            cur = ""
            for w in words:
                trial = w if not cur else f"{cur} {w}"
                if font.size(trial)[0] <= max_w:
                    cur = trial
                else:
                    if cur:
                        out.append(cur)
                    cur = w
            if cur:
                out.append(cur)
        return out

    def _draw_box(self, surface, rect, color, *, fill=None, border=2, radius=2):
        off = int(4 * self.scale)
        pygame.draw.rect(surface, (10, 5, 20), rect.move(off, off), 0, border_radius=radius)
        if fill:
            pygame.draw.rect(surface, fill, rect, 0, border_radius=radius)
        pygame.draw.rect(surface, color, rect, border, border_radius=radius)

    def _scroll_indicator(self, surface, rect, start, visible, total):
        if total <= visible:
            return
        mx = total - visible
        pct = start / mx if mx else 0
        bw = int(4 * self.scale)
        bh = int(30 * self.scale)
        th = rect.height - int(20 * self.scale)
        avail = th - bh
        bx = rect.right - bw - int(4 * self.scale)
        by = rect.y + int(10 * self.scale) + int(pct * avail)
        pygame.draw.rect(surface, GOLD, (bx, by, bw, bh), 0, border_radius=2)

    # ────────────────────────────────────────────────────────────────
    #  UPDATE
    # ────────────────────────────────────────────────────────────────
    def update(self, dt: float) -> None:
        # cursor blink
        self.cursor_timer += dt
        if self.cursor_timer >= 0.5:
            self.cursor_timer = 0.0
            self.cursor_visible = not self.cursor_visible

        # glow timer (always tick for menu pulse)
        self.menu_glow_timer += dt

        # download error timer
        if self.download_error_timer > 0:
            self.download_error_timer -= dt
            if self.download_error_timer <= 0:
                self.download_error_timer = 0.0
                self.download_error_message = ""

        # download progress — slow while connected; +33% total time per extra concurrent download
        n = len(self.downloading_tracks)
        if n > 0:
            slowdown = 1.0 + 0.33 * (n - 1)
            effective_duration = self.download_duration * slowdown
            for idx in list(self.downloading_tracks.keys()):
                self.downloading_tracks[idx] = min(1.0, self.downloading_tracks[idx] + dt / effective_duration)
                if self.downloading_tracks[idx] >= 1.0:
                    self._complete_download(idx)
                    del self.downloading_tracks[idx]

        # connecting auto-advance
        if self.state == "connecting":
            self.connect_timer += dt
            if self.connect_timer >= self.connect_delay and self.connect_index < len(self.connect_messages):
                self.connect_timer = 0.0
                self.connect_index += 1
                if self.connect_index >= len(self.connect_messages):
                    # short pause then show startscreen
                    self.connect_timer = -0.8

            # transition to startscreen after all messages + pause
            if self.connect_index >= len(self.connect_messages) and self.connect_timer >= 0.0:
                self.state = "startscreen"

        # ansi scroll — matches main.py BBS scroll exactly (per-frame, scrolls upward)
        if self.state == "ansi_scroll" and self.ansi_image:
            if self.scroll_y is None:
                self.scroll_y = float(self.height)  # start image below visible area

            if not self.scroll_final_paused:
                img_h = self.ansi_image.get_height()
                image_bottom = self.scroll_y + img_h

                if self.scroll_pause_frames > 0:
                    # temporary pause — count down then enter final state
                    self.scroll_pause_frames -= 1
                    if self.scroll_pause_frames == 0:
                        self.scroll_final_paused = True
                        self.state = "ansi_pause"
                        self.ansi_flash_timer = 0.0
                else:
                    if not self.scroll_pause_triggered and image_bottom <= self.scroll_pause_y:
                        self.scroll_pause_frames = 20
                        self.scroll_pause_triggered = True
                    elif not self.scroll_pause_triggered:
                        self.scroll_y -= self.scroll_speed

                    # fallback: image scrolled entirely off the top
                    if self.scroll_y + img_h <= 0:
                        self.scroll_final_paused = True
                        self.state = "ansi_pause"
                        self.ansi_flash_timer = 0.0

        # flash timer for "PRESS SPACE"
        if self.state == "ansi_pause":
            self.ansi_flash_timer += dt

    # ────────────────────────────────────────────────────────────────
    #  EVENT HANDLING
    # ────────────────────────────────────────────────────────────────
    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type != pygame.KEYDOWN:
            return False

        handler = {
            "connecting":   self._ev_connecting,
            "startscreen":  self._ev_startscreen,
            "new_user":     self._ev_new_user,
            "login":        self._ev_login,
            "ansi_scroll":  self._ev_ansi_scroll,
            "ansi_pause":   self._ev_ansi_pause,
            "menu":         self._ev_menu,
            "panel":        self._ev_panel,
        }.get(self.state)
        if handler:
            return handler(event)
        return False

    # ── connecting ──────────────────────────────────────────────────
    def _ev_connecting(self, event) -> bool:
        if event.key == pygame.K_ESCAPE:
            self._end_call()
            return True
        return False

    # ── startscreen ─────────────────────────────────────────────────
    def _ev_startscreen(self, event) -> bool:
        if event.key in (pygame.K_UP, pygame.K_w):
            self.start_index = (self.start_index - 1) % len(self.start_options)
            return True
        if event.key in (pygame.K_DOWN, pygame.K_s):
            self.start_index = (self.start_index + 1) % len(self.start_options)
            return True
        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            sel = self.start_options[self.start_index]
            if sel == "NEW USER":
                self.state = "new_user"
                self._reset_input()
            elif sel == "LOGIN":
                self.state = "login"
                self._reset_input()
            elif sel == "EXIT":
                self._end_call()
            return True
        if event.key == pygame.K_ESCAPE:
            self._end_call()
            return True
        return False

    # ── new user ────────────────────────────────────────────────────
    def _ev_new_user(self, event) -> bool:
        if event.key == pygame.K_ESCAPE:
            self.state = "startscreen"
            return True
        if event.key == pygame.K_TAB:
            fields = ["username", "pin", "pin_confirm"]
            idx = fields.index(self.input_focus)
            self.input_focus = fields[(idx + 1) % len(fields)]
            return True
        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            return self._submit_new_user()
        if event.key == pygame.K_BACKSPACE:
            self._backspace()
            return True
        char = event.unicode
        if char and char.isprintable() and len(char) == 1:
            self._type_char(char)
            return True
        return False

    # ── login ───────────────────────────────────────────────────────
    def _ev_login(self, event) -> bool:
        if event.key == pygame.K_ESCAPE:
            self.state = "startscreen"
            return True
        if event.key == pygame.K_TAB:
            self.input_focus = "pin" if self.input_focus == "username" else "username"
            return True
        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            return self._submit_login()
        if event.key == pygame.K_BACKSPACE:
            self._backspace()
            return True
        char = event.unicode
        if char and char.isprintable() and len(char) == 1:
            self._type_char(char)
            return True
        return False

    # ── ansi scroll ─────────────────────────────────────────────────
    def _ev_ansi_scroll(self, event) -> bool:
        if event.key == pygame.K_ESCAPE:
            self._end_call()
            return True
        if event.key == pygame.K_SPACE:
            # skip to end — jump to final paused position
            if self.ansi_image:
                img_h = self.ansi_image.get_height()
                # position so the bottom of the image sits at scroll_pause_y
                self.scroll_y = float(self.scroll_pause_y - img_h)
            self.scroll_final_paused = True
            self.scroll_pause_triggered = True
            self.scroll_pause_frames = 0
            self.state = "ansi_pause"
            self.ansi_flash_timer = 0.0
            return True
        return False

    # ── ansi pause ──────────────────────────────────────────────────
    def _ev_ansi_pause(self, event) -> bool:
        if event.key == pygame.K_ESCAPE:
            self._end_call()
            return True
        if event.key == pygame.K_SPACE:
            self.state = "menu"
            return True
        return False

    # ── menu ────────────────────────────────────────────────────────
    def _ev_menu(self, event) -> bool:
        if event.key in (pygame.K_UP, pygame.K_w):
            self.menu_index = (self.menu_index - 1) % len(self.menu_options)
            return True
        if event.key in (pygame.K_DOWN, pygame.K_s):
            self.menu_index = (self.menu_index + 1) % len(self.menu_options)
            return True
        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            sel = self.menu_options[self.menu_index]
            if sel == "END CALL":
                self._end_call()
            else:
                self.active_panel = sel
                self.state = "panel"
                if sel == "TRANSMISSIONS":
                    if not self.visible_posts:
                        self._randomise_wall()
                elif sel == "FUGAMATCHI":
                    self.audio_selected = 0
                    self.showing_lyrics = False
                    self.fugamatchi_focus = "tracks"
                    self.fugamatchi_sub = "play"
            return True
        if event.key == pygame.K_ESCAPE:
            self._end_call()
            return True
        return False

    # ── panel ───────────────────────────────────────────────────────
    def _ev_panel(self, event) -> bool:
        if self.active_panel == "TRANSMISSIONS":
            return self._ev_transmissions(event)
        if self.active_panel == "FUGAMATCHI":
            return self._ev_fugamatchi(event)
        return False

    # ── transmissions sub-events ────────────────────────────────────
    def _ev_transmissions(self, event) -> bool:
        # replying mode
        if self.replying:
            if event.key == pygame.K_ESCAPE:
                self.replying = False
                self.reply_text = ""
                return True
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                if self.reply_text.strip() and self.trans_open_post:
                    pid = self.trans_open_post.get("id", 0)
                    self._save_user_reply(pid, self.reply_text.strip())
                    self.replying = False
                    self.reply_text = ""
                return True
            if event.key == pygame.K_BACKSPACE:
                self.reply_text = self.reply_text[:-1]
                return True
            ch = event.unicode
            if ch and ch.isprintable() and len(ch) == 1 and len(self.reply_text) < 200:
                self.reply_text += ch
                return True
            return False

        # detail view
        if self.trans_open_post is not None:
            if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                self.trans_open_post = None
                self.trans_detail_scroll = 0
                return True
            if event.key in (pygame.K_UP, pygame.K_w):
                self.trans_detail_scroll = max(0, self.trans_detail_scroll - 1)
                return True
            if event.key in (pygame.K_DOWN, pygame.K_s):
                self.trans_detail_scroll += 1
                return True
            if event.key == pygame.K_r:
                self.replying = True
                self.reply_text = ""
                return True
            return False

        # list view
        if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
            self.state = "menu"
            self.active_panel = None
            return True
        if event.key in (pygame.K_UP, pygame.K_w):
            if self.visible_posts:
                self.trans_selected = (self.trans_selected - 1) % len(self.visible_posts)
                self._clamp_trans_list_scroll()
            return True
        if event.key in (pygame.K_DOWN, pygame.K_s):
            if self.visible_posts:
                self.trans_selected = (self.trans_selected + 1) % len(self.visible_posts)
                self._clamp_trans_list_scroll()
            return True
        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            if self.visible_posts:
                self.trans_open_post = self.visible_posts[self.trans_selected]
                self.trans_detail_scroll = 0
            return True
        return False

    def _clamp_trans_list_scroll(self):
        lh = int(50 * self.scale)
        vis = max(1, (int(self.height * 0.65) - int(80 * self.scale)) // lh)
        if self.trans_selected < self.trans_list_scroll:
            self.trans_list_scroll = self.trans_selected
        elif self.trans_selected >= self.trans_list_scroll + vis:
            self.trans_list_scroll = self.trans_selected - vis + 1

    # ── fugamatchi sub-events ───────────────────────────────────────
    def _ev_fugamatchi(self, event) -> bool:
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

        # TAB — switch between track list and welcome text
        if event.key == pygame.K_TAB:
            self.fugamatchi_focus = "welcome" if self.fugamatchi_focus == "tracks" else "tracks"
            return True

        if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
            self.state = "menu"
            self.active_panel = None
            return True

        if self.fugamatchi_focus == "welcome":
            if event.key in (pygame.K_UP, pygame.K_w):
                self.audio_welcome_scroll = max(0, self.audio_welcome_scroll - 1)
                return True
            if event.key in (pygame.K_DOWN, pygame.K_s):
                self.audio_welcome_scroll += 1
                return True
            return False

        # Track list focus — cycle play / lyrics / download
        if event.key in (pygame.K_LEFT, pygame.K_a):
            if self.fugamatchi_sub == "download":
                self.fugamatchi_sub = "lyrics" if (self.audio_tracks and "lyrics" in self.audio_tracks[self.audio_selected]) else "play"
            elif self.fugamatchi_sub == "lyrics":
                self.fugamatchi_sub = "play"
            return True
        if event.key == pygame.K_RIGHT:
            if self.fugamatchi_sub == "play":
                self.fugamatchi_sub = "lyrics" if (self.audio_tracks and "lyrics" in self.audio_tracks[self.audio_selected]) else "download"
            elif self.fugamatchi_sub == "lyrics":
                self.fugamatchi_sub = "download"
            return True
        if event.key in (pygame.K_UP, pygame.K_w):
            if self.audio_tracks:
                self.audio_selected = (self.audio_selected - 1) % len(self.audio_tracks)
                self._clamp_track_scroll()
            return True
        if event.key in (pygame.K_DOWN, pygame.K_s):
            if self.audio_tracks:
                self.audio_selected = (self.audio_selected + 1) % len(self.audio_tracks)
                self._clamp_track_scroll()
            return True
        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            if self.audio_tracks:
                if self.fugamatchi_sub == "play":
                    self._play_track(self.audio_selected)
                elif self.fugamatchi_sub == "lyrics" and "lyrics" in self.audio_tracks[self.audio_selected]:
                    self.showing_lyrics = True
                    self.lyrics_scroll = 0
                elif self.fugamatchi_sub == "download":
                    self._start_download(self.audio_selected)
            return True
        if event.key == pygame.K_l:
            if self.audio_tracks and "lyrics" in self.audio_tracks[self.audio_selected]:
                self.showing_lyrics = True
                self.lyrics_scroll = 0
            return True
        if event.key == pygame.K_SPACE:
            try:
                if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
                    pygame.mixer.music.stop()
                    self.current_playing_track = None
            except Exception:
                pass
            return True
        if event.key == pygame.K_d:
            if self.audio_tracks:
                self._start_download(self.audio_selected)
            return True
        return False

    def _clamp_track_scroll(self):
        if not self.audio_tracks:
            return
        th = int(56 * self.scale)  # two rows per track
        ph = int(self.height * 0.7)
        lh = ph - int(100 * self.scale)
        vis = max(1, lh // th)
        if self.audio_selected < self.track_list_scroll:
            self.track_list_scroll = self.audio_selected
        elif self.audio_selected >= self.track_list_scroll + vis:
            self.track_list_scroll = self.audio_selected - vis + 1

    # ── input helpers ───────────────────────────────────────────────
    def _reset_input(self):
        self.input_username = ""
        self.input_pin = ""
        self.input_pin_confirm = ""
        self.input_focus = "username"
        self.error_message = ""

    def _backspace(self):
        if self.input_focus == "username":
            self.input_username = self.input_username[:-1]
        elif self.input_focus == "pin":
            self.input_pin = self.input_pin[:-1]
        elif self.input_focus == "pin_confirm":
            self.input_pin_confirm = self.input_pin_confirm[:-1]

    def _type_char(self, ch: str):
        if self.input_focus == "username" and len(self.input_username) < 20:
            self.input_username += ch
        elif self.input_focus == "pin" and len(self.input_pin) < 4 and ch.isdigit():
            self.input_pin += ch
        elif self.input_focus == "pin_confirm" and len(self.input_pin_confirm) < 4 and ch.isdigit():
            self.input_pin_confirm += ch

    def _submit_new_user(self) -> bool:
        u = self.input_username.strip()
        p = self.input_pin.strip()
        pc = self.input_pin_confirm.strip()
        if len(u) < 2:
            self.error_message = "USERNAME MUST BE AT LEAST 2 CHARACTERS"
            return True
        if len(p) != 4:
            self.error_message = "PIN MUST BE EXACTLY 4 DIGITS"
            return True
        if p != pc:
            self.error_message = "PINS DO NOT MATCH"
            self.input_pin = ""
            self.input_pin_confirm = ""
            return True
        if self._create_user(u, p):
            self.logged_in_user = u.upper()
            self._on_login_success()
        return True

    def _submit_login(self) -> bool:
        u = self.input_username.strip()
        p = self.input_pin.strip()
        if not u or not p:
            self.error_message = "ENTER USERNAME AND PIN"
            return True
        if self._verify_login(u, p):
            self.logged_in_user = u.upper()
            self._on_login_success()
        else:
            self.error_message = "ACCESS DENIED"
            self.input_pin = ""
        return True

    def _on_login_success(self):
        self.error_message = ""
        self._randomise_wall()
        if self.ansi_image:
            # reset scroll state — image starts below the screen, scrolls up
            self.scroll_y = None
            self.scroll_pause_frames = 0
            self.scroll_pause_triggered = False
            self.scroll_final_paused = False
            self.ansi_flash_timer = 0.0
            self.state = "ansi_scroll"
        else:
            self.state = "menu"
        if self.on_grant_token:
            self.on_grant_token("NEVERAGAINBBS_IN", reason="dialed into Never Again BBS")

    def _complete_download(self, track_index: int) -> None:
        """Finish a single download and add to user's library."""
        if self.on_download_track and self.audio_tracks and 0 <= track_index < len(self.audio_tracks):
            track_title = self.audio_tracks[track_index]["title"]
            self.on_download_track(track_title)

    def _start_download(self, track_index: int) -> None:
        """Start downloading a track (or add to queue if already downloading others)."""
        if not self.audio_tracks or not self.on_download_track:
            return
        # Region check
        if self.get_region and self.get_region() != 1:
            self.download_error_message = "Region American Pacifica Isles does not permit file transfers at this time."
            self.download_error_timer = 3.0
            return
        if 0 <= track_index < len(self.audio_tracks) and track_index not in self.downloading_tracks:
            self.downloading_tracks[track_index] = 0.0

    def _end_call(self):
        # Complete any in-progress downloads instantly on logoff
        for idx in list(self.downloading_tracks.keys()):
            self._complete_download(idx)
        self.downloading_tracks.clear()
        try:
            if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
                pygame.mixer.music.stop()
        except Exception:
            pass
        self.current_playing_track = None
        self.request_exit = True
        if self.on_exit:
            self.on_exit()

    # ────────────────────────────────────────────────────────────────
    #  DRAW — MAIN ENTRY
    # ────────────────────────────────────────────────────────────────
    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(BG)

        dispatch = {
            "connecting":  self._draw_connecting,
            "startscreen": self._draw_startscreen,
            "new_user":    self._draw_new_user,
            "login":       self._draw_login,
            "ansi_scroll": self._draw_ansi,
            "ansi_pause":  self._draw_ansi,
            "menu":        self._draw_menu_screen,
            "panel":       self._draw_panel_screen,
        }
        fn = dispatch.get(self.state)
        if fn:
            fn(surface)

        surface.blit(self.scanline_surf, (0, 0))

    # ── connecting ──────────────────────────────────────────────────
    def _draw_connecting(self, surface: pygame.Surface):
        pad = int(40 * self.scale)
        y = int(self.height * 0.25)

        # title
        self._shadow(surface, self.font_title, "NEVER AGAIN BBS", ROSE,
                      (self.width // 2 - self.font_title.size("NEVER AGAIN BBS")[0] // 2, y))
        y += int(50 * self.scale)

        self._shadow(surface, self.font_small, "ESTABLISHING SECURE CONNECTION...", BLUE,
                      (pad, y))
        y += int(40 * self.scale)

        # messages
        for i in range(min(self.connect_index, len(self.connect_messages))):
            msg = self.connect_messages[i]
            color = GOLD if i == self.connect_index - 1 else TEXT
            self._shadow(surface, self.font_small, f"> {msg}", color, (pad, y))
            y += int(24 * self.scale)

        # progress bar
        y += int(20 * self.scale)
        bar_w = self.width - pad * 2
        bar_h = int(20 * self.scale)
        bar_rect = pygame.Rect(pad, y, bar_w, bar_h)
        pygame.draw.rect(surface, DIM_BLUE, bar_rect, 0, border_radius=3)
        progress = self.connect_index / max(1, len(self.connect_messages))
        fill_w = int(bar_w * progress)
        if fill_w > 0:
            fill_rect = pygame.Rect(pad, y, fill_w, bar_h)
            pygame.draw.rect(surface, BLUE, fill_rect, 0, border_radius=3)
        pygame.draw.rect(surface, ROSE, bar_rect, 2, border_radius=3)

        pct_text = f"{int(progress * 100)}%"
        ps = self._render(self.font_small, pct_text, TEXT)
        surface.blit(ps, (pad + bar_w // 2 - ps.get_width() // 2, y + bar_h // 2 - ps.get_height() // 2))

    # ── startscreen ─────────────────────────────────────────────────
    def _draw_startscreen(self, surface: pygame.Surface):
        # background image
        if self.startscreen_image:
            r = self.startscreen_image.get_rect(center=surface.get_rect().center)
            surface.blit(self.startscreen_image, r)

        # welcome message
        wmsg = "// AS HEARD ON HOTLINE UNDERGROUND 74.25 KHz — DIAL 03-4089-9891"
        ws = self._render(self.font_small, wmsg, ROSE)
        surface.blit(ws, (self.width // 2 - ws.get_width() // 2, int(20 * self.scale)))

        # menu box — tight around NEW USER / LOGIN / EXIT, bottom just under EXIT
        box_w = int(self.width * 0.4)
        lh = int(60 * self.scale)
        top_pad = int(25 * self.scale)
        bottom_pad = int(15 * self.scale)
        box_h = top_pad + lh * len(self.start_options) + bottom_pad
        box_x = self.width // 2 - box_w // 2
        box_y = int(self.height * 0.60)
        box = pygame.Rect(box_x, box_y, box_w, box_h)
        self._draw_box(surface, box, ROSE, fill=BG_DARK)
        for i, opt in enumerate(self.start_options):
            is_sel = i == self.start_index
            oy = box_y + top_pad + i * lh
            if is_sel:
                sel_r = pygame.Rect(box_x + int(10 * self.scale), oy - int(5 * self.scale),
                                    box_w - int(20 * self.scale), lh - int(10 * self.scale))
                pulse = int(math.sin(self.menu_glow_timer * 8) * 30 + 50)
                pygame.draw.rect(surface, (ROSE[0], ROSE[1], ROSE[2], pulse), sel_r, 0, border_radius=4)
                pygame.draw.rect(surface, ROSE, sel_r, 2, border_radius=4)
            color = BLUE if is_sel else TEXT
            ts = self._render(self.font_body, opt, color)
            surface.blit(ts, (box_x + box_w // 2 - ts.get_width() // 2, oy + int(5 * self.scale)))

        # hint
        hint = "UP/DOWN NAVIGATE | ENTER SELECT | ESC EXIT"
        hs = self._render(self.font_small, hint, DIM_ROSE)
        surface.blit(hs, (self.width // 2 - hs.get_width() // 2, self.height - int(40 * self.scale)))

    # ── new user ────────────────────────────────────────────────────
    def _draw_new_user(self, surface: pygame.Surface):
        self._draw_form(surface, "NEW USER REGISTRATION",
                        [("USERNAME", self.input_username, "username", False),
                         ("4-DIGIT PIN", self.input_pin, "pin", True),
                         ("CONFIRM PIN", self.input_pin_confirm, "pin_confirm", True)],
                        "ENTER [SUBMIT]  TAB [NEXT FIELD]  ESC [BACK]")

    def _draw_login(self, surface: pygame.Surface):
        self._draw_form(surface, "SECURE LOGIN",
                        [("USERNAME", self.input_username, "username", False),
                         ("4-DIGIT PIN", self.input_pin, "pin", True)],
                        "ENTER [SUBMIT]  TAB [SWITCH]  ESC [BACK]")

    def _draw_form(self, surface, title, fields, hint):
        pad = int(32 * self.scale)
        top = pad * 2
        ts = self._render(self.font_label, f"// {title}", ROSE)
        surface.blit(ts, (self.width // 2 - ts.get_width() // 2, top))

        box_w = int(self.width * 0.65)
        field_h = int(55 * self.scale)
        start_y = int(self.height * 0.30)

        back_h = field_h * len(fields) + pad * (len(fields) + 1)
        back = pygame.Rect(self.width // 2 - box_w // 2 - pad, start_y - pad,
                           box_w + pad * 2, back_h)
        self._draw_box(surface, back, DIM_ROSE, fill=BG_DARK)

        for i, (label, value, field_id, mask) in enumerate(fields):
            y = start_y + i * (field_h + pad)
            focused = self.input_focus == field_id
            self._draw_input(surface, label, value, self.width // 2 - box_w // 2, y,
                             box_w, field_h, focused, mask)

        # error
        if self.error_message:
            es = self._render(self.font_body, self.error_message, ERROR)
            surface.blit(es, (self.width // 2 - es.get_width() // 2, start_y - int(50 * self.scale)))

        # hint
        hs = self._render(self.font_small, hint, TEXT)
        surface.blit(hs, (self.width // 2 - hs.get_width() // 2,
                          start_y + len(fields) * (field_h + pad) + pad))

    def _draw_input(self, surface, label, value, x, y, w, h, focused, mask):
        color = BLUE if focused else ROSE
        lbl = self.font_small.render(f"// {label}".upper(), True, color)
        surface.blit(lbl, (x, y - int(22 * self.scale)))
        rect = pygame.Rect(x, y, w, h)
        bg = (25, 18, 55) if focused else BG_DARK
        self._draw_box(surface, rect, color, fill=bg, border=2 if focused else 1)
        display = ("*" * len(value)) if mask else value
        if focused and self.cursor_visible:
            display += "\u2588"
        vs = self.font_body.render((display or " ").upper(), True, TEXT)
        surface.blit(vs, (x + int(14 * self.scale), y + h // 2 - vs.get_height() // 2))

    # ── ansi scroll / pause ─────────────────────────────────────────
    def _draw_ansi(self, surface: pygame.Surface):
        """Draw ansi-scroll.png exactly like main.py's draw_bbs_scroll — full
        BBS width, image scrolls upward from below the screen."""
        if not self.ansi_image:
            self.state = "menu"
            return

        if self.scroll_y is not None:
            surface.blit(self.ansi_image, (0, int(self.scroll_y)))

        # flash prompt at bottom when paused
        if self.state == "ansi_pause":
            show = int(self.ansi_flash_timer * 2) % 2 == 0
            if show:
                txt = "PRESS SPACE TO CONTINUE"
                ts = self._render(self.font_label, txt, GOLD)
                tx = self.width // 2 - ts.get_width() // 2
                ty = self.height - int(60 * self.scale)
                br = pygame.Rect(tx - int(10 * self.scale), ty - int(5 * self.scale),
                                 ts.get_width() + int(20 * self.scale),
                                 ts.get_height() + int(10 * self.scale))
                pygame.draw.rect(surface, BG, br, 0, border_radius=4)
                self._shadow(surface, self.font_label, txt, GOLD, (tx, ty))

    # ── menu ────────────────────────────────────────────────────────
    def _draw_menu_screen(self, surface: pygame.Surface):
        self._draw_menu_bg(surface)
        self._draw_menu_items(surface)

    def _draw_panel_screen(self, surface: pygame.Surface):
        self._draw_menu_bg(surface)
        self._draw_menu_items(surface)
        if self.active_panel == "TRANSMISSIONS":
            self._draw_transmissions(surface)
        elif self.active_panel == "FUGAMATCHI":
            self._draw_fugamatchi(surface)

    def _draw_menu_bg(self, surface: pygame.Surface):
        """Subtle grid background for menu / panel states."""
        step = max(24, int(48 * self.scale))
        for x in range(0, self.width, step):
            pygame.draw.line(surface, (BG[0] + 8, BG[1] + 6, BG[2] + 12), (x, 0), (x, self.height), 1)
        for y in range(0, self.height, step):
            pygame.draw.line(surface, (BG[0] + 8, BG[1] + 6, BG[2] + 12), (0, y), (self.width, y), 1)
        # layer background (renders just after the grid, behind the boxes)
        if self.layer_background:
            r = self.layer_background.get_rect(center=surface.get_rect().center)
            surface.blit(self.layer_background, r)
        # border
        pygame.draw.rect(surface, ROSE, surface.get_rect().inflate(-2, -2), 2)

    def _draw_menu_items(self, surface: pygame.Surface):
        # subtitle
        sub = f"LOGGED IN AS: {self.logged_in_user or 'GUEST'}"
        ss = self._render(self.font_small, sub, BLUE)
        surface.blit(ss, (self.width // 2 - ss.get_width() // 2, int(35 * self.scale)))

        # menu container
        # Bottom edge extends to give similar spacing between options and room for two text
        # lines below "END CALL" (same gap as between options ~lh, plus ~2 line heights)
        mx = int(self.width * 0.05)
        my = int(140 * self.scale)
        lh = int(55 * self.scale)
        menu_w = int(self.width * 0.30)
        top_pad = int(20 * self.scale)
        bottom_pad = lh + int(50 * self.scale)  # similar to inter-option gap + ~2 text lines
        menu_h = top_pad + lh * len(self.menu_options) + bottom_pad
        mr = pygame.Rect(mx, my, menu_w, menu_h)
        self._draw_box(surface, mr, ROSE, fill=BG_DARK)

        for i, opt in enumerate(self.menu_options):
            is_sel = i == self.menu_index and self.state == "menu"
            oy = my + int(20 * self.scale) + i * lh
            if is_sel:
                sr = pygame.Rect(mx + int(8 * self.scale), oy - int(5 * self.scale),
                                 menu_w - int(16 * self.scale), lh - int(10 * self.scale))
                pulse = int(math.sin(self.menu_glow_timer * 8) * 30 + 50)
                pygame.draw.rect(surface, (ROSE[0], ROSE[1], ROSE[2], pulse), sr, 0, border_radius=4)
                pygame.draw.rect(surface, ROSE, sr, 2, border_radius=4)
                # arrow
                ay = oy + int(15 * self.scale)
                pygame.draw.polygon(surface, BLUE, [
                    (mx - int(25 * self.scale), ay - int(7 * self.scale)),
                    (mx - int(8 * self.scale), ay),
                    (mx - int(25 * self.scale), ay + int(7 * self.scale)),
                ])
            color = BLUE if is_sel else TEXT
            self._shadow(surface, self.font_body, opt, color, (mx + int(16 * self.scale), oy))

    # ── transmissions panel ─────────────────────────────────────────
    def _draw_transmissions(self, surface: pygame.Surface):
        if self.trans_open_post is not None:
            self._draw_post_detail(surface)
            return

        # list panel
        px = int(self.width * 0.38)
        py = int(100 * self.scale)
        pw = int(self.width * 0.58)
        ph = int(self.height * 0.75)
        pr = pygame.Rect(px, py, pw, ph)
        self._draw_box(surface, pr, BLUE, fill=BG_DARK)

        # header
        self._shadow(surface, self.font_label, "// TRANSMISSIONS", BLUE,
                      (px + int(16 * self.scale), py + int(12 * self.scale)))
        pygame.draw.line(surface, DIM_BLUE,
                         (px + int(16 * self.scale), py + int(42 * self.scale)),
                         (px + pw - int(16 * self.scale), py + int(42 * self.scale)), 1)

        lh = int(50 * self.scale)
        content_y = py + int(55 * self.scale)
        content_h = ph - int(100 * self.scale)
        vis = max(1, content_h // lh)

        old_clip = surface.get_clip()
        clip_r = pygame.Rect(px, content_y, pw, content_h)
        surface.set_clip(clip_r)

        for i in range(vis):
            idx = self.trans_list_scroll + i
            if idx >= len(self.visible_posts):
                break
            post = self.visible_posts[idx]
            is_sel = idx == self.trans_selected
            iy = content_y + i * lh

            if is_sel:
                sr = pygame.Rect(px + 4, iy, pw - 8, lh - 4)
                pygame.draw.rect(surface, (ROSE[0], ROSE[1], ROSE[2], 40), sr, 0, border_radius=4)
                pygame.draw.rect(surface, ROSE, sr, 1, border_radius=4)

            ucolor = BLUE if is_sel else DIM_BLUE
            tcolor = GOLD if is_sel else TEXT
            prefix = "> " if is_sel else "  "
            # username
            self._shadow(surface, self.font_small, f"{prefix}{post.get('username', '???')}", ucolor,
                          (px + int(12 * self.scale), iy + int(2 * self.scale)))
            # title (truncated)
            title = post.get("title", "")
            max_title_w = pw - int(40 * self.scale)
            ttl_surf = self.font_small.render(title.upper(), True, tcolor)
            if ttl_surf.get_width() > max_title_w:
                # truncate
                while ttl_surf.get_width() > max_title_w and len(title) > 3:
                    title = title[:-1]
                    ttl_surf = self.font_small.render((title + "...").upper(), True, tcolor)
                title += "..."
            self._shadow(surface, self.font_small, title, tcolor,
                          (px + int(12 * self.scale), iy + int(24 * self.scale)))

        surface.set_clip(old_clip)

        # scroll indicator
        self._scroll_indicator(surface, pr, self.trans_list_scroll, vis, len(self.visible_posts))

        # footer
        fr = pygame.Rect(px, pr.bottom - int(25 * self.scale), pw, int(25 * self.scale))
        pygame.draw.rect(surface, DIM_ROSE, fr, 0, border_bottom_left_radius=4, border_bottom_right_radius=4)
        self._shadow(surface, self.font_small,
                      "UP/DOWN NAVIGATE | ENTER VIEW | ESC MENU", TEXT,
                      (px + int(12 * self.scale), pr.bottom - int(22 * self.scale)))

    def _draw_post_detail(self, surface: pygame.Surface):
        post = self.trans_open_post
        if not post:
            return

        px = int(self.width * 0.05)
        py = int(100 * self.scale)
        pw = int(self.width * 0.9)
        ph = int(self.height * 0.78)
        pr = pygame.Rect(px, py, pw, ph)
        self._draw_box(surface, pr, BLUE, fill=BG_DARK)

        pad = int(16 * self.scale)
        lh = int(22 * self.scale)
        max_w = pw - pad * 2

        # build content lines
        lines: list = []
        lines.append(("GOLD", f"[{post.get('username', '???')}]  {post.get('title', '')}"))
        lines.append(("LINE", ""))
        for bl in post.get("body", "").split("\n"):
            lines.append(("TEXT", bl))
        lines.append(("BLANK", ""))
        lines.append(("LINE", ""))
        # replies
        for rep in post.get("replies", []):
            lines.append(("BLUE", f"  [{rep.get('username', '???')}]"))
            for rl in rep.get("body", "").split("\n"):
                lines.append(("TEXT", f"    {rl}"))
            lines.append(("BLANK", ""))
        # user replies
        user_reps = self._get_user_replies(post.get("id", 0))
        if user_reps:
            lines.append(("LINE", ""))
            lines.append(("ROSE", "// YOUR REPLIES"))
            for ur in user_reps:
                lines.append(("GOLD", f"  [{self.logged_in_user}]"))
                for ul in ur.split("\n"):
                    lines.append(("TEXT", f"    {ul}"))
                lines.append(("BLANK", ""))

        # wrap all text lines
        wrapped: list = []
        for (kind, txt) in lines:
            if kind in ("BLANK", "LINE"):
                wrapped.append((kind, ""))
            else:
                wl = self._wrap([txt], self.font_small, max_w)
                for w in wl:
                    wrapped.append((kind, w))

        vis = max(1, (ph - int(90 * self.scale)) // lh)
        mx_scroll = max(0, len(wrapped) - vis)
        self.trans_detail_scroll = max(0, min(self.trans_detail_scroll, mx_scroll))

        # draw
        content_y = py + int(12 * self.scale)
        old_clip = surface.get_clip()
        surface.set_clip(pygame.Rect(px, content_y, pw, ph - int(80 * self.scale)))

        for i in range(vis):
            li = self.trans_detail_scroll + i
            if li >= len(wrapped):
                break
            kind, txt = wrapped[li]
            dy = content_y + i * lh
            if kind == "LINE":
                pygame.draw.line(surface, DIM_BLUE, (px + pad, dy + lh // 2),
                                 (px + pw - pad, dy + lh // 2), 1)
            elif kind == "BLANK":
                pass
            else:
                c = {"GOLD": GOLD, "BLUE": BLUE, "ROSE": ROSE, "TEXT": TEXT}.get(kind, TEXT)
                self._shadow(surface, self.font_small, txt, c, (px + pad, dy))

        surface.set_clip(old_clip)

        # scroll indicator
        self._scroll_indicator(surface, pr, self.trans_detail_scroll, vis, len(wrapped))

        # reply input
        if self.replying:
            ry = pr.bottom - int(60 * self.scale)
            rr = pygame.Rect(px + pad, ry, pw - pad * 2, int(28 * self.scale))
            pygame.draw.rect(surface, (25, 18, 55), rr, 0, border_radius=3)
            pygame.draw.rect(surface, BLUE, rr, 2, border_radius=3)
            display = self.reply_text
            if self.cursor_visible:
                display += "\u2588"
            rs = self.font_small.render(display.upper() or " ", True, TEXT)
            surface.blit(rs, (rr.x + int(8 * self.scale), rr.y + rr.height // 2 - rs.get_height() // 2))

        # footer
        fr = pygame.Rect(px, pr.bottom - int(25 * self.scale), pw, int(25 * self.scale))
        pygame.draw.rect(surface, DIM_ROSE, fr, 0, border_bottom_left_radius=4, border_bottom_right_radius=4)
        if self.replying:
            hint = "ENTER SUBMIT | ESC CANCEL"
        else:
            hint = "UP/DOWN SCROLL | R REPLY | ESC BACK"
        self._shadow(surface, self.font_small, hint, TEXT,
                      (px + int(12 * self.scale), pr.bottom - int(22 * self.scale)))

    # ── fugamatchi music panel ──────────────────────────────────────
    def _draw_fugamatchi(self, surface: pygame.Surface):
        panel_rect = pygame.Rect(
            int(self.width * 0.05), int(100 * self.scale),
            int(self.width * 0.9), int(self.height * 0.75))
        self._draw_box(surface, panel_rect, BLUE, fill=BG_DARK)

        # header
        htxt = "FUGAMATCHI ARCHIVE"
        if self.showing_lyrics and self.audio_tracks:
            # Lyrics header: title only, no extension
            htxt += " // LYRICS: " + self.audio_tracks[self.audio_selected]["title"].upper()
        self._shadow(surface, self.font_label, htxt, GOLD,
                      (panel_rect.x + int(16 * self.scale), panel_rect.y + int(12 * self.scale)))

        if self.showing_lyrics:
            self._draw_lyrics(surface, panel_rect)
            return

        if not self.audio_tracks:
            # no tracks message (files on disk: .mp3/.wav; displayed as .sonic)
            msg_lines = [
                "NO TRACKS FOUND IN THE FUGAMATCHI ARCHIVE.",
                "",
                "ADD .MP3 OR .WAV FILES TO THE",
                "FUGAMATCHI FOLDER. THEY WILL APPEAR",
                "AS .SONIC TRACKS IN THE ARCHIVE.",
                "",
                "LYRICS: ADD FILES TO FUGAMATCHI/LYRICS",
                "WITH TITLES MATCHING TRACK NAMES.",
            ]
            y = panel_rect.y + int(60 * self.scale)
            for line in msg_lines:
                self._shadow(surface, self.font_small, line, TEXT,
                              (panel_rect.x + int(20 * self.scale), y))
                y += int(24 * self.scale)

            # footer
            fr = pygame.Rect(panel_rect.x, panel_rect.bottom - int(25 * self.scale),
                             panel_rect.width, int(25 * self.scale))
            pygame.draw.rect(surface, DIM_ROSE, fr, 0,
                             border_bottom_left_radius=4, border_bottom_right_radius=4)
            esc_surf = self._render(self.font_small, "[ESC] BACK", TEXT)
            self._shadow(surface, self.font_small, "[ESC] BACK", TEXT,
                          (self.width - esc_surf.get_width() - int(12 * self.scale),
                           self.height - int(28 * self.scale)))
            return

        # welcome message area (left) — TAB to focus and scroll
        msg_r = pygame.Rect(
            panel_rect.x + int(16 * self.scale),
            panel_rect.y + int(50 * self.scale),
            int(panel_rect.width * 0.48),
            int(panel_rect.height * 0.72))
        welcome_focused = self.fugamatchi_focus == "welcome"
        pygame.draw.rect(surface, (BG[0] + 5, BG[1] + 3, BG[2] + 8), msg_r, 0, border_radius=4)
        border_c = ROSE if welcome_focused else DIM_BLUE
        pygame.draw.rect(surface, border_c, msg_r, 2 if welcome_focused else 1, border_radius=4)

        mlh = int(22 * self.scale)
        max_msg_w = msg_r.width - int(24 * self.scale)
        wm = self._wrap([self.audio_message], self.font_small, max_msg_w)
        vis_msg = max(1, msg_r.height // mlh - 1)
        mx_s = max(0, len(wm) - vis_msg)
        self.audio_welcome_scroll = min(self.audio_welcome_scroll, mx_s)

        old_clip = surface.get_clip()
        surface.set_clip(msg_r)
        my = msg_r.y + int(10 * self.scale)
        for i in range(self.audio_welcome_scroll, min(len(wm), self.audio_welcome_scroll + vis_msg)):
            self._shadow(surface, self.font_small, wm[i], TEXT,
                          (msg_r.x + int(12 * self.scale), my))
            my += mlh
        surface.set_clip(old_clip)
        self._scroll_indicator(surface, msg_r, self.audio_welcome_scroll, vis_msg, len(wm))

        # track list area (right)
        list_r = pygame.Rect(
            msg_r.right + int(16 * self.scale),
            msg_r.y,
            panel_rect.width - (msg_r.width + int(48 * self.scale)),
            panel_rect.height - int(80 * self.scale))
        tracks_focused = self.fugamatchi_focus == "tracks"
        pygame.draw.rect(surface, (BG[0] + 3, BG[1] + 2, BG[2] + 6), list_r, 0, border_radius=4)
        list_border_c = ROSE if tracks_focused else DIM_BLUE
        pygame.draw.rect(surface, list_border_c, list_r, 2 if tracks_focused else 1, border_radius=4)

        self._shadow(surface, self.font_small, "AVAILABLE TRACKS:", BLUE,
                      (list_r.x + int(8 * self.scale), list_r.y - int(22 * self.scale)))

        th = int(56 * self.scale)
        vis_tracks = max(1, list_r.height // th)
        old_clip2 = surface.get_clip()
        surface.set_clip(list_r)

        for i in range(vis_tracks):
            idx = self.track_list_scroll + i
            if idx >= len(self.audio_tracks):
                break
            trk = self.audio_tracks[idx]
            is_sel = idx == self.audio_selected
            is_play = idx == self.current_playing_track
            is_dl = idx in self.downloading_tracks
            ty = list_r.y + int(8 * self.scale) + i * th
            if ty + th > list_r.bottom:
                break
            if is_sel:
                sr = pygame.Rect(list_r.x + 4, ty, list_r.width - 8, th - 4)
                pygame.draw.rect(surface, (ROSE[0], ROSE[1], ROSE[2], 35), sr, 0, border_radius=4)
                pygame.draw.rect(surface, ROSE, sr, 1, border_radius=4)
            color = GOLD if is_play else (BLUE if is_sel else TEXT)
            prefix = ">> " if is_play else (" > " if is_sel else "   ")
            display_name = trk["title"] + ".sonic"
            self._shadow(surface, self.font_small, f"{prefix}{display_name}", color,
                          (list_r.x + int(8 * self.scale), ty + int(4 * self.scale)))
            row2_y = ty + int(26 * self.scale)
            play_sel = is_sel and self.fugamatchi_sub == "play"
            lyrics_sel = is_sel and self.fugamatchi_sub == "lyrics"
            dl_sel = is_sel and self.fugamatchi_sub == "download"
            item_gap = int(80 * self.scale)
            x_off = list_r.x + int(8 * self.scale)
            pc = GOLD if play_sel else (DIM_ROSE if is_sel else DIM_BLUE)
            self._shadow(surface, self.font_small, "[PLAY]", pc, (x_off, row2_y))
            x_off += item_gap
            if "lyrics" in trk:
                lc = GOLD if lyrics_sel else (DIM_ROSE if is_sel else DIM_BLUE)
                self._shadow(surface, self.font_small, "[LYRICS]", lc, (x_off, row2_y))
                x_off += item_gap
            if is_dl:
                prog = self.downloading_tracks.get(idx, 0.0)
                bar_w = int(80 * self.scale)
                bar_x = list_r.right - bar_w - int(8 * self.scale)
                pygame.draw.rect(surface, DIM_BLUE, (bar_x, row2_y, bar_w, int(14 * self.scale)), 1, border_radius=2)
                fill_w = int(bar_w * prog)
                if fill_w > 0:
                    pygame.draw.rect(surface, GOLD, (bar_x, row2_y, fill_w, int(14 * self.scale)), 0, border_radius=2)
                self._shadow(surface, self.font_small, f"{int(prog * 100)}%", GOLD,
                              (bar_x + bar_w // 2 - int(15 * self.scale), row2_y - 2))
            else:
                dc = GOLD if dl_sel else (DIM_ROSE if is_sel else DIM_BLUE)
                self._shadow(surface, self.font_small, "[DOWNLOAD]", dc, (x_off, row2_y))
        surface.set_clip(old_clip2)
        self._scroll_indicator(surface, list_r, self.track_list_scroll, vis_tracks, len(self.audio_tracks))

        # footer
        fr = pygame.Rect(panel_rect.x, panel_rect.bottom - int(25 * self.scale),
                         panel_rect.width, int(25 * self.scale))
        pygame.draw.rect(surface, DIM_ROSE, fr, 0,
                         border_bottom_left_radius=4, border_bottom_right_radius=4)
        hints = "[TAB] SIDE BOX  [UP/DOWN] NAVIGATE  [ENTER] PLAY/LYRICS/DL  [D] DOWNLOAD"
        if self.audio_tracks and "lyrics" in self.audio_tracks[self.audio_selected]:
            hints += "  [L] LYRICS"
        self._shadow(surface, self.font_small, hints, TEXT,
                      (panel_rect.x + int(12 * self.scale), panel_rect.bottom - int(22 * self.scale)))
        esc_surf = self._render(self.font_small, "[ESC] BACK", TEXT)
        self._shadow(surface, self.font_small, "[ESC] BACK", TEXT,
                      (self.width - esc_surf.get_width() - int(12 * self.scale),
                       self.height - int(28 * self.scale)))

        # Download error overlay
        if self.download_error_timer > 0:
            overlay = pygame.Surface((panel_rect.width, int(60 * self.scale)), pygame.SRCALPHA)
            overlay.fill((30, 21, 65, 220))
            err_y = panel_rect.y + panel_rect.height // 2 - int(30 * self.scale)
            surface.blit(overlay, (panel_rect.x, err_y))
            self._shadow(surface, self.font_label, "TRANSFER BLOCKED", ERROR,
                          (panel_rect.x + int(20 * self.scale), err_y + int(5 * self.scale)))
            self._shadow(surface, self.font_small, self.download_error_message, TEXT,
                          (panel_rect.x + int(20 * self.scale), err_y + int(32 * self.scale)))

    def _draw_lyrics(self, surface: pygame.Surface, panel_rect: pygame.Rect):
        if not self.audio_tracks:
            return
        track = self.audio_tracks[self.audio_selected]
        raw = track.get("lyrics", [])

        lr = pygame.Rect(
            panel_rect.x + int(16 * self.scale),
            panel_rect.y + int(50 * self.scale),
            panel_rect.width - int(32 * self.scale),
            panel_rect.height - int(100 * self.scale))
        pygame.draw.rect(surface, (BG[0] + 3, BG[1] + 2, BG[2] + 6), lr, 0, border_radius=4)
        pygame.draw.rect(surface, DIM_BLUE, lr, 1, border_radius=4)

        lh = int(22 * self.scale)
        max_w = lr.width - int(30 * self.scale)
        wrapped = self._wrap(raw, self.font_small, max_w)
        vis = max(1, lr.height // lh - 1)
        mx_s = max(0, len(wrapped) - vis)
        self.lyrics_scroll = min(self.lyrics_scroll, mx_s)

        old_clip = surface.get_clip()
        surface.set_clip(lr)
        y = lr.y + int(8 * self.scale)
        for i in range(self.lyrics_scroll, min(len(wrapped), self.lyrics_scroll + vis)):
            line = wrapped[i]
            c = GOLD if line.startswith("[") else TEXT
            self._shadow(surface, self.font_small, line, c,
                          (lr.x + int(15 * self.scale), y))
            y += lh
        surface.set_clip(old_clip)
        self._scroll_indicator(surface, lr, self.lyrics_scroll, vis, len(wrapped))

        # footer
        fr = pygame.Rect(panel_rect.x, panel_rect.bottom - int(25 * self.scale),
                         panel_rect.width, int(25 * self.scale))
        pygame.draw.rect(surface, DIM_ROSE, fr, 0,
                         border_bottom_left_radius=4, border_bottom_right_radius=4)
        self._shadow(surface, self.font_small,
                      "[UP/DOWN] SCROLL  [L] RETURN TO LIST", TEXT,
                      (panel_rect.x + int(12 * self.scale), panel_rect.bottom - int(22 * self.scale)))
        esc_surf = self._render(self.font_small, "[ESC] BACK", TEXT)
        self._shadow(surface, self.font_small, "[ESC] BACK", TEXT,
                      (self.width - esc_surf.get_width() - int(12 * self.scale),
                       self.height - int(28 * self.scale)))
