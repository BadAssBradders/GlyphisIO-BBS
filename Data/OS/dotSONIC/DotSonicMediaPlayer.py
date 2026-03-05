"""
dotSONIC MEDIA PLAYER
Plays .sonic files from the DOWNLOADS folder within the OS Mode desktop.
Launched via double-click on sonic-icon.png from the desktop.
"""

import pygame
import os
import sys
import time
import math
import threading
from typing import List, Dict, Tuple, Optional, Callable

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

# Data path helper (matches utils.get_data_path / OS_Mode)
def get_data_path(*path_parts) -> str:
    if getattr(sys, "frozen", False):
        base_path = sys._MEIPASS
    else:
        script_dir = os.path.dirname(os.path.abspath(__file__))  # Data/OS/dotSONIC
        os_dir = os.path.dirname(script_dir)  # Data/OS
        data_folder = os.path.dirname(os_dir)  # Data
        base_path = os.path.join(data_folder, "Data") if os.path.basename(data_folder) != "Data" else data_folder
        if not os.path.exists(base_path):
            base_path = data_folder
    return os.path.join(base_path, *path_parts)


def get_dotsonic_path(*path_parts) -> str:
    """Path within dotSONIC folder."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_dir, *path_parts)


# Slider debugging: set True to show hit rects, values, and print events
SLIDER_DEBUG = True

# Colors (match retro aesthetic)
COLOR_BG_DARK = (8, 12, 32)
COLOR_DISPLAY = (15, 25, 55)
COLOR_CYAN = (0, 255, 255)
COLOR_WHITE = (255, 255, 255)
COLOR_RED = (220, 50, 50)
COLOR_BLUE = (40, 80, 180)
COLOR_MAGENTA = (180, 50, 150)
COLOR_TITLE = (255, 255, 255)

NUM_VIZ_BARS = 32
VIZ_SEGMENT_H = 3
VIZ_SEGMENT_GAP = 1


class DotSonicMediaPlayer:
    """
    dotSONIC Media Player - full desktop app for OS Mode.
    API matches other apps: update_desktop, start, close, handle_event, draw.
    """
    
    # Button IDs
    BTN_LOAD = "load"
    BTN_PREV = "prev"
    BTN_REWIND = "rewind"
    BTN_PLAY = "play"
    BTN_FFWD = "ffwd"
    BTN_NEXT = "next"
    BTN_STOP = "stop"
    
    def __init__(
        self,
        screen: pygame.Surface,
        scale: float,
        desktop_x: int,
        desktop_y: int,
        desktop_size: Tuple[int, int],
        health_monitor_y: int,
        get_downloaded_tracks: Callable[[], List[str]] = None,
        open_file_browser_callback: Callable[[], None] = None,
        close_callback: Callable[[], None] = None,
    ):
        self.screen = screen
        self.scale = scale
        self.desktop_x = desktop_x
        self.desktop_y = desktop_y
        self.desktop_size = desktop_size
        self.get_downloaded_tracks = get_downloaded_tracks or (lambda: [])
        self.open_file_browser_callback = open_file_browser_callback or (lambda: None)
        self.close_callback = close_callback or (lambda: None)
        
        self.active = False
        self.window_rect: Optional[pygame.Rect] = None
        
        # Playlist: list of {"title": str, "real_name": str, "file_type": str|None, "file_path": str|None}
        # real_name is __sonic__{title} for virtual, or filename for physical
        self.playlist: List[Dict] = []
        self.current_index = -1
        self.playing = False
        self.paused = False
        
        # Volume 0.0-1.0, Balance -1.0 (left) to 1.0 (right)
        self.volume = 0.8
        self.balance = 0.0
        
        # Slider drag state
        self.dragging_vol = False
        self.dragging_bal = False
        
        # Window drag state
        self.dragging_window = False
        self.drag_offset = (0, 0)
        self._window_x: Optional[int] = None
        self._window_y: Optional[int] = None
        
        # Visualizer state (spectrum analyzer + oscilloscope)
        self.viz_bars = [0.0] * NUM_VIZ_BARS
        self.viz_targets = [0.0] * NUM_VIZ_BARS
        self.viz_peaks = [0.0] * NUM_VIZ_BARS
        self.viz_peak_vel = [0.0] * NUM_VIZ_BARS
        self.viz_waveform = [0.0] * 64
        self.viz_wave_targets = [0.0] * 64
        self._viz_last_time = 0.0
        
        # Pre-computed audio analysis data (real FFT when numpy available)
        self._audio_bands = None
        self._audio_wave = None
        self._audio_fps = 20
        self._audio_analyzed = False
        self._analysis_generation = 0
        
        # Cached render surfaces (rebuilt on size change)
        self._viz_cache_key = None
        self._viz_bg_surf = None
        self._viz_scan_surf = None
        self._viz_vig_l = None
        self._viz_vig_r = None
        self._viz_bar_grad = None
        self._viz_bar_grad_key = None
        
        # Playlist scroll (for viewing when > 10 tracks)
        self.playlist_scroll = 0
        
        # Font
        self.font: Optional[pygame.font.Font] = None
        self._load_font()
        
        # Backdrop: dict of button-state -> scaled Surface (playing-gui, paused-gui, stop-pressed-gui, etc.)
        self.backdrops: Dict[str, pygame.Surface] = {}
        self._load_backdrops()
        
        # Slider PNGs
        self.vol_slider_img: Optional[pygame.Surface] = None
        self.bal_slider_img: Optional[pygame.Surface] = None
        self._load_slider_images()
        
        # Button pressed state
        self.pressed_button: Optional[str] = None
        # Non-play buttons (prev, next, rewind, ffwd, stop) revert backdrop after this time
        self.pressed_button_revert_at: float = 0.0
        
        # Track elapsed time
        self.track_start_time = 0.0
        self.pause_elapsed = 0.0
        
        self._update_layout()
    
    def _load_font(self) -> None:
        """Load VT323-Regular from OS folder."""
        vt_path = get_data_path("OS", "VT323-Regular.ttf")
        if os.path.exists(vt_path):
            try:
                self.font = pygame.font.Font(vt_path, max(int(20 * self.scale), 16))
            except Exception:
                self.font = pygame.font.Font(None, int(24 * self.scale))
        else:
            self.font = pygame.font.Font(None, int(24 * self.scale))
    
    def _load_backdrops(self) -> None:
        """Load all button-pressed GUI images from dotSONIC folder."""
        gui_names = [
            "playing-gui.png", "paused-gui.png", "stop-pressed-gui.png",
            "left-pressed-playing-gui.png", "left-pressed-paused-gui.png",
            "right-pressed-playing-gui.png", "right-pressed-paused-gui.png",
            "left-rwd-gui.png", "right-fwd-gui.png",
        ]
        for name in gui_names:
            path = get_dotsonic_path(name)
            if os.path.exists(path):
                try:
                    img = pygame.image.load(path).convert_alpha()
                    key = name.replace(".png", "")
                    self.backdrops[key] = img
                except Exception as e:
                    print(f"DotSonic: Could not load {name}: {e}")
    
    def _get_backdrop_key(self) -> Optional[str]:
        """Return backdrop key for current pressed button and play state."""
        btn = self.pressed_button
        is_playing = self.playing and not self.paused
        if btn == self.BTN_STOP:
            return "stop-pressed-gui"
        if btn == self.BTN_PREV:
            return "left-pressed-playing-gui" if is_playing else "left-pressed-paused-gui"
        if btn == self.BTN_NEXT:
            return "right-pressed-playing-gui" if is_playing else "right-pressed-paused-gui"
        if btn == self.BTN_PLAY:
            return "playing-gui" if is_playing else "paused-gui"
        if btn == self.BTN_REWIND:
            return "left-rwd-gui"
        if btn == self.BTN_FFWD:
            return "right-fwd-gui"
        # No button pressed or LOAD: use playing/paused by state
        return "playing-gui" if is_playing else "paused-gui"
    
    def _load_slider_images(self) -> None:
        """Load volSwitch.png and balanceSwitch.png for sliders."""
        for name, attr in [("volSwitch.png", "vol_slider_img"), ("balanceSwitch.png", "bal_slider_img")]:
            path = get_dotsonic_path(name)
            if os.path.exists(path):
                try:
                    img = pygame.image.load(path).convert_alpha()
                    setattr(self, attr, img)
                except Exception as e:
                    print(f"DotSonic: Could not load {name}: {e}")
    
    def _update_layout(self) -> None:
        """Compute rects for window, display areas, buttons, sliders.
        Positions use % of window (0-100): x% from left, y% from top.
        Window position: use _window_x/_window_y if set (user-dragged), else centered."""
        ww = int(self.desktop_size[0] * 0.4)
        wh = int(self.desktop_size[1] * 0.4)
        default_wx = self.desktop_x + (self.desktop_size[0] - ww) // 2
        default_wy = self.desktop_y + (self.desktop_size[1] - wh) // 2
        if self._window_x is not None and self._window_y is not None:
            wx = self._window_x
            wy = self._window_y
            # Keep within desktop bounds
            wx = max(self.desktop_x, min(wx, self.desktop_x + self.desktop_size[0] - ww))
            wy = max(self.desktop_y, min(wy, self.desktop_y + self.desktop_size[1] - wh))
            self._window_x, self._window_y = wx, wy
        else:
            wx, wy = default_wx, default_wy
        self.window_rect = pygame.Rect(wx, wy, ww, wh)
        
        def pct_x(pct: float) -> int:
            return wx + int(ww * pct / 100)
        def pct_y(pct: float) -> int:
            return wy + int(wh * pct / 100)
        def pct_w(pct: float) -> int:
            return max(1, int(ww * pct / 100))
        def pct_h(pct: float) -> int:
            return max(1, int(wh * pct / 100))
        
        self._layout_scale = min(ww / 699, wh / 767)
        
        # Equalizer: top-left (7.3, 30.7), bottom-right (93.0, 50.4)
        self.eq_display = pygame.Rect(
            pct_x(7.3), pct_y(30.7),
            pct_w(93.0 - 7.3), pct_h(50.4 - 30.7)
        )
        
        # Buttons - hotspots only (no draw). Bottom-right corners for stretched buttons.
        self.btn_rects = {
            self.BTN_LOAD: pygame.Rect(pct_x(4.8), pct_y(57.4), pct_w(10), pct_h(6)),
            self.BTN_PREV: pygame.Rect(pct_x(15.8), pct_y(57.4), pct_w(24.8 - 15.8), pct_h(62.6 - 57.4)),   # left back, br 24.8x62.6
            self.BTN_NEXT: pygame.Rect(pct_x(26.8), pct_y(57.4), pct_w(34.6 - 26.8), pct_h(62.6 - 57.4)),   # right forward, br 34.6x62.6
            self.BTN_PLAY: pygame.Rect(pct_x(38), pct_y(57.4), pct_w(47.6 - 38), pct_h(62.2 - 57.4)),      # play, br 47.6x62.2
            self.BTN_REWIND: pygame.Rect(pct_x(51), pct_y(56.7), pct_w(59.6 - 51), pct_h(62.6 - 56.7)),   # left rewind, br 59.6x62.6
            self.BTN_FFWD: pygame.Rect(pct_x(62.9), pct_y(56.7), pct_w(72.2 - 62.9), pct_h(62.6 - 56.7)),  # right ffwd, br 72.2x62.6
            self.BTN_STOP: pygame.Rect(pct_x(75.4), pct_y(57.4), pct_w(6), pct_h(6)),  # stop unchanged
        }
        
        # Track list: top-left (6.8, 68.5) to bottom-right (70.2, 91.9), at least 3 tracks visible
        self.lower_display = pygame.Rect(
            pct_x(6.8), pct_y(68.5),
            pct_w(70.2 - 6.8), pct_h(91.9 - 68.5)
        )
        
        # Sliders - VOL 76.4 x 71.5, BAL 87.7 x 71.5 (top-left). Wider hit area for easier click.
        slider_w = pct_w(8)
        slider_h = pct_h(18)
        self.vol_slider_rect = pygame.Rect(pct_x(75), pct_y(71.5), slider_w, slider_h)
        self.bal_slider_rect = pygame.Rect(pct_x(86), pct_y(71.5), slider_w, slider_h)
        
        # Exit button (top-right) - match OS modal close buttons (Datasette, etc.)
        exit_sz = int(20 * self.scale)
        self.exit_rect = pygame.Rect(wx + ww - exit_sz - int(5 * self.scale), wy + int(5 * self.scale), exit_sz, exit_sz)
        
        # Visible track count (for scroll max) - at least 3
        list_h = self.lower_display.height - int(10 * self._layout_scale)
        row_h = (self.font.get_height() if self.font else 20) + int(3 * self._layout_scale)
        self.visible_track_count = max(3, min(10, list_h // row_h) if row_h else 3)
    
    def update_desktop(
        self,
        desktop_x: int,
        desktop_y: int,
        desktop_size: Tuple[int, int],
        health_monitor_y: int,
    ) -> None:
        """Update desktop coordinates."""
        self.desktop_x = desktop_x
        self.desktop_y = desktop_y
        self.desktop_size = desktop_size
        self._update_layout()
    
    def start(self) -> None:
        """Launch the player."""
        self.active = True
        if not pygame.mixer.get_init():
            try:
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            except Exception as e:
                print(f"DotSonic: Mixer init failed: {e}")
    
    def close(self) -> None:
        """Close the player."""
        self.active = False
        self.playing = False
        self.paused = False
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass
        self.close_callback()
    
    def add_track_to_playlist(self, title: str, real_name: str, file_type: Optional[str] = None, file_path: Optional[str] = None) -> None:
        """Add a track from file browser (called by OS_Mode when LOAD adds .sonic)."""
        entry = {"title": title, "real_name": real_name, "file_type": file_type, "file_path": file_path}
        if entry not in self.playlist:
            self.playlist.append(entry)
    
    def _resolve_track_path(self, entry: Dict) -> Optional[str]:
        """Resolve track to actual audio file path."""
        real_name = entry.get("real_name", "")
        title = entry.get("title", "").replace(".sonic", "")
        file_path = entry.get("file_path")
        if file_path and os.path.isfile(file_path):
            return file_path
        # Virtual __sonic__{title} - look in Fugamatchi folder
        if real_name.startswith("__sonic__"):
            title_clean = real_name.replace("__sonic__", "")
            fugamatchi_dir = get_data_path("Outside_BBSs", "NeverAgainBBS", "Fugamatchi")
            if os.path.isdir(fugamatchi_dir):
                for fn in os.listdir(fugamatchi_dir):
                    if fn.lower().endswith((".wav", ".mp3")):
                        base = os.path.splitext(fn)[0]
                        # Strip numeric prefix like "01_"
                        if "_" in base:
                            parts = base.split("_", 1)
                            if parts[0].isdigit():
                                base = parts[1]
                        base_clean = base.replace("_", " ").strip()
                        if base_clean.lower() == title_clean.lower():
                            return os.path.join(fugamatchi_dir, fn)
        return None
    
    # ------------------------------------------------------------------
    #  Audio-reactive visualization
    # ------------------------------------------------------------------
    
    def _start_audio_analysis(self, file_path: str) -> None:
        """Launch FFT analysis on a background thread so playback starts instantly."""
        self._audio_bands = None
        self._audio_wave = None
        self._audio_analyzed = False
        
        if not file_path or not HAS_NUMPY:
            return
        
        self._analysis_generation += 1
        gen = self._analysis_generation
        t = threading.Thread(
            target=self._precompute_audio_analysis,
            args=(file_path, gen),
            daemon=True,
        )
        t.start()
    
    def _precompute_audio_analysis(self, file_path: str, generation: int) -> None:
        """Pre-compute FFT frequency band and waveform data for the entire track.
        Runs on a background thread. Uses batch numpy FFT for speed.
        Results are discarded if a newer generation has been requested."""
        try:
            sound = pygame.mixer.Sound(file_path)
            arr = pygame.sndarray.array(sound)
            del sound
            
            if self._analysis_generation != generation:
                return
            
            if arr.ndim == 2:
                samples = arr.mean(axis=1).astype(np.float32)
            else:
                samples = arr.astype(np.float32)
            del arr
            
            peak = np.abs(samples).max()
            if peak > 0:
                samples /= peak
            
            sample_rate = pygame.mixer.get_init()[0]
            frame_size = sample_rate // self._audio_fps
            num_frames = len(samples) // frame_size
            if num_frames < 2:
                return
            
            # Reshape into (num_frames, frame_size) for batch processing
            frames = samples[:num_frames * frame_size].reshape(num_frames, frame_size)
            del samples
            
            if self._analysis_generation != generation:
                return
            
            window = np.hanning(frame_size).astype(np.float32)
            frames *= window
            
            # Waveform: downsample each frame to 64 points
            wave_idx = np.linspace(0, frame_size - 1, 64, dtype=int)
            waves = frames[:, wave_idx].copy()
            
            # Batch FFT across all frames at once
            fft_all = np.abs(np.fft.rfft(frames, axis=1))
            del frames
            
            if self._analysis_generation != generation:
                return
            
            # Pre-compute frequency bin indices for each band (done once)
            num_bands = NUM_VIZ_BARS
            freqs = np.fft.rfftfreq(frame_size, 1.0 / sample_rate)
            freq_min, freq_max = 30, min(sample_rate // 2, 16000)
            band_edges = np.logspace(np.log10(freq_min), np.log10(freq_max), num_bands + 1)
            
            bands = np.zeros((num_frames, num_bands), dtype=np.float32)
            for b in range(num_bands):
                idx = np.where((freqs >= band_edges[b]) & (freqs < band_edges[b + 1]))[0]
                if len(idx) > 0:
                    bands[:, b] = np.sqrt(np.mean(fft_all[:, idx] ** 2, axis=1))
            del fft_all
            
            if self._analysis_generation != generation:
                return
            
            # Normalize per-band (98th percentile to avoid one loud hit flattening everything)
            for b in range(num_bands):
                p98 = np.percentile(bands[:, b], 98) if num_frames > 10 else bands[:, b].max()
                if p98 > 0:
                    bands[:, b] = np.clip(bands[:, b] / p98, 0, 1)
            
            bands = np.power(bands, 0.7)
            
            if self._analysis_generation != generation:
                return
            
            self._audio_bands = bands
            self._audio_wave = waves
            self._audio_analyzed = True
        except Exception as e:
            print(f"DotSonic: Audio analysis failed (simulation mode): {e}")
    
    def _get_simulated_bands(self, now: float) -> list:
        """Generate musically convincing simulated spectrum when real data unavailable."""
        bars = []
        beat = max(0, 1.0 - ((now * 2.0) % 1.0) * 4.0)
        accent = max(0, 1.0 - ((now * 1.0) % 1.0) * 3.0) * 0.3
        
        for i in range(NUM_VIZ_BARS):
            freq_weight = max(0.15, 1.0 - (i / (NUM_VIZ_BARS - 1)) * 0.7)
            h1 = math.sin(now * 3.7 + i * 0.41) * 0.25
            h2 = math.sin(now * 5.3 + i * 0.73) * 0.15
            h3 = math.sin(now * 8.1 + i * 0.29) * 0.10
            beat_w = max(0, 1.0 - i / 6.0) * beat * 0.45
            accent_w = max(0, 1.0 - abs(i - 12) / 8.0) * accent
            flutter = math.sin(now * 17.3 + i * 2.7) * 0.06
            val = (0.2 + h1 + h2 + h3 + beat_w + accent_w + flutter) * freq_weight
            bars.append(max(0.02, min(1.0, val)))
        return bars
    
    def _get_simulated_wave(self, now: float) -> list:
        """Generate simulated oscilloscope waveform."""
        wave = []
        env = 0.5 + 0.5 * math.sin(now * 1.5)
        for i in range(64):
            t = i / 63.0
            v = (math.sin(now * 6.0 + t * math.pi * 4) * 0.4
                 + math.sin(now * 9.5 + t * math.pi * 7) * 0.2
                 + math.sin(now * 2.3 + t * math.pi * 2) * 0.3)
            wave.append(v * env * 0.8)
        return wave
    
    def _rebuild_viz_caches(self, w: int, h: int, bar_w: int, bar_h: int,
                            seg_h_px: int, seg_gap_px: int) -> None:
        """Rebuild all cached visualization surfaces when dimensions change."""
        self._viz_bg_surf = pygame.Surface((w, h))
        self._viz_bg_surf.fill((5, 8, 22))
        grid_c = (12, 20, 40)
        sy = max(8, h // 8)
        sx = max(8, w // 16)
        for gy in range(sy, h, sy):
            pygame.draw.line(self._viz_bg_surf, grid_c, (0, gy), (w - 1, gy))
        for gx in range(sx, w, sx):
            pygame.draw.line(self._viz_bg_surf, grid_c, (gx, 0), (gx, h - 1))
        
        self._viz_scan_surf = pygame.Surface((w, h), pygame.SRCALPHA)
        for sly in range(0, h, 2):
            pygame.draw.line(self._viz_scan_surf, (0, 0, 0, 20), (0, sly), (w - 1, sly))
        
        vig_w = max(4, w // 20)
        self._viz_vig_l = pygame.Surface((vig_w, h), pygame.SRCALPHA)
        for vx in range(vig_w):
            a = int(50 * (1.0 - vx / vig_w))
            pygame.draw.line(self._viz_vig_l, (0, 0, 0, a), (vx, 0), (vx, h - 1))
        self._viz_vig_r = pygame.transform.flip(self._viz_vig_l, True, False)
        self._viz_cache_key = (w, h)
        
        seg_step = seg_h_px + seg_gap_px
        self._viz_bar_grad = pygame.Surface((bar_w, bar_h), pygame.SRCALPHA)
        for y in range(bar_h):
            from_bottom = bar_h - 1 - y
            if from_bottom % seg_step >= seg_h_px:
                continue
            ratio = y / max(1, bar_h - 1)
            if ratio < 0.5:
                t = ratio / 0.5
                cr, cg = 255, int(255 * t)
            else:
                t = (ratio - 0.5) / 0.5
                cr, cg = int(255 * (1 - t)), 255
            pygame.draw.line(self._viz_bar_grad, (cr, cg, 0, 255), (0, y), (bar_w - 1, y))
        self._viz_bar_grad_key = (bar_w, bar_h, seg_h_px, seg_gap_px)
    
    def _draw_visualizer(self, eq_inner: pygame.Rect) -> None:
        """Draw retro CRT spectrum analyzer with waveform oscilloscope."""
        now = time.time()
        dt = min(0.1, now - self._viz_last_time) if self._viz_last_time > 0 else 0.016
        self._viz_last_time = now
        
        is_active = self.playing and not self.paused
        w, h = eq_inner.size
        if w <= 4 or h <= 4:
            return
        
        # ---- Update targets from real audio data or simulation ----
        if is_active:
            got_real = False
            if self._audio_bands is not None:
                try:
                    pos_ms = pygame.mixer.music.get_pos()
                    if pos_ms >= 0:
                        frame = int((pos_ms / 1000.0) * self._audio_fps)
                        frame = max(0, min(frame, len(self._audio_bands) - 1))
                        self.viz_targets = list(self._audio_bands[frame])
                        if self._audio_wave is not None and frame < len(self._audio_wave):
                            self.viz_wave_targets = list(self._audio_wave[frame])
                        got_real = True
                except Exception:
                    pass
            if not got_real:
                self.viz_targets = self._get_simulated_bands(now)
                self.viz_wave_targets = self._get_simulated_wave(now)
        else:
            self.viz_targets = [0.0] * NUM_VIZ_BARS
            self.viz_wave_targets = [0.0] * 64
        
        # ---- Smooth interpolation (fast rise, slow fall like real hardware) ----
        for i in range(NUM_VIZ_BARS):
            target = self.viz_targets[i]
            speed = 14.0 if target > self.viz_bars[i] else 4.0
            self.viz_bars[i] += (target - self.viz_bars[i]) * min(1.0, speed * dt)
            self.viz_bars[i] = max(0.0, min(1.0, self.viz_bars[i]))
            
            if self.viz_bars[i] >= self.viz_peaks[i]:
                self.viz_peaks[i] = self.viz_bars[i]
                self.viz_peak_vel[i] = 0.0
            else:
                self.viz_peak_vel[i] += 4.0 * dt
                self.viz_peaks[i] -= self.viz_peak_vel[i] * dt
                self.viz_peaks[i] = max(0.0, self.viz_peaks[i])
        
        for i in range(64):
            self.viz_waveform[i] += (self.viz_wave_targets[i] - self.viz_waveform[i]) * min(1.0, 18.0 * dt)
        
        # ---- Layout ----
        margin = max(2, int(3 * self._layout_scale))
        wave_h = max(8, int(h * 0.22))
        bar_top_y = eq_inner.y + wave_h + margin
        bar_h = max(4, eq_inner.bottom - margin - bar_top_y)
        
        num_bars = NUM_VIZ_BARS
        bar_gap = max(1, int(1.5 * self._layout_scale))
        usable_w = w - margin * 2
        bw = max(2, (usable_w - bar_gap * (num_bars - 1)) // num_bars)
        total_bars_w = bw * num_bars + bar_gap * (num_bars - 1)
        bx_start = eq_inner.x + margin + (usable_w - total_bars_w) // 2
        
        seg_h_px = max(2, int(VIZ_SEGMENT_H * self._layout_scale))
        seg_gap_px = max(1, int(VIZ_SEGMENT_GAP * self._layout_scale))
        
        # ---- Rebuild cached surfaces if size changed ----
        if getattr(self, '_viz_cache_key', None) != (w, h):
            self._rebuild_viz_caches(w, h, bw, bar_h, seg_h_px, seg_gap_px)
        if getattr(self, '_viz_bar_grad_key', None) != (bw, bar_h, seg_h_px, seg_gap_px):
            self._rebuild_viz_caches(w, h, bw, bar_h, seg_h_px, seg_gap_px)
        
        ox, oy = eq_inner.topleft
        
        # ---- Background (dark blue-black with subtle grid) ----
        self.screen.blit(self._viz_bg_surf, (ox, oy))
        
        # ---- Waveform oscilloscope (phosphor green) ----
        wave_cy = oy + wave_h // 2
        wave_amp = max(2, wave_h // 2 - 2)
        pts = []
        for i in range(64):
            px = ox + margin + int(i * (w - margin * 2) / 63)
            py = wave_cy + int(self.viz_waveform[i] * wave_amp)
            py = max(oy + 1, min(oy + wave_h - 1, py))
            pts.append((px, py))
        if len(pts) > 1:
            glow_w = max(1, int(3 * self._layout_scale))
            pygame.draw.lines(self.screen, (0, 60, 30), False, pts, glow_w)
            pygame.draw.lines(self.screen, (0, 255, 100), False, pts, max(1, glow_w // 2))
            if glow_w >= 2:
                pygame.draw.lines(self.screen, (140, 255, 180), False, pts, 1)
        
        # Divider line
        div_y = oy + wave_h
        pygame.draw.line(self.screen, (20, 50, 70), (ox + margin, div_y), (ox + w - margin, div_y))
        
        # ---- Spectrum bars (segmented gradient, one blit per bar) ----
        bar_bottom = bar_top_y + bar_h
        for i in range(num_bars):
            bx = bx_start + i * (bw + bar_gap)
            fill_h = max(0, int(self.viz_bars[i] * bar_h))
            if fill_h > 0:
                src_y = bar_h - fill_h
                self.screen.blit(self._viz_bar_grad, (bx, bar_bottom - fill_h), (0, src_y, bw, fill_h))
            
            if self.viz_peaks[i] > 0.02:
                peak_h = int(self.viz_peaks[i] * bar_h)
                peak_y = bar_bottom - peak_h - max(1, seg_h_px // 2)
                if peak_y >= bar_top_y:
                    pulse = int(200 + 55 * math.sin(now * 4.0 + i * 0.5))
                    pygame.draw.rect(self.screen, (pulse, 255, pulse),
                                     (bx, peak_y, bw, max(1, seg_h_px // 2)))
        
        # ---- CRT overlay effects ----
        self.screen.blit(self._viz_scan_surf, (ox, oy))
        vig_w = self._viz_vig_l.get_width()
        self.screen.blit(self._viz_vig_l, (ox, oy))
        self.screen.blit(self._viz_vig_r, (ox + w - vig_w, oy))
    
    def _play_track_at(self, index: int) -> None:
        """Start playing track at index."""
        if index < 0 or index >= len(self.playlist):
            return
        self.current_index = index
        path = self._resolve_track_path(self.playlist[index])
        if path:
            try:
                pygame.mixer.music.load(path)
                pygame.mixer.music.set_volume(self._effective_volume())
                pygame.mixer.music.play()
                self.playing = True
                self.paused = False
                self.track_start_time = time.time()
                self.pause_elapsed = 0.0
                self._start_audio_analysis(path)
            except Exception as e:
                print(f"DotSonic: Could not play {path}: {e}")
        else:
            self.playing = True
            self.paused = False
    
    def _effective_volume(self) -> float:
        """Volume with balance applied (simplified)."""
        return self.volume
    
    def _stop_playback(self) -> None:
        """Stop playback."""
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass
        self.playing = False
        self.paused = False
        self._analysis_generation += 1
        self._audio_bands = None
        self._audio_wave = None
        self._audio_analyzed = False
    
    def _toggle_play_pause(self) -> None:
        """Toggle play/pause."""
        if self.playing:
            if self.paused:
                pygame.mixer.music.unpause()
                self.paused = False
                self.track_start_time = time.time() - self.pause_elapsed
            else:
                pygame.mixer.music.pause()
                self.paused = True
                self.pause_elapsed = time.time() - self.track_start_time
        else:
            if self.playlist:
                if self.current_index < 0:
                    self._play_track_at(0)
                else:
                    self._play_track_at(self.current_index)
    
    def _prev_track(self) -> None:
        """Previous track."""
        if self.playlist:
            self.current_index = max(0, self.current_index - 1)
            self._play_track_at(self.current_index)
    
    def _next_track(self) -> None:
        """Next track."""
        if self.playlist:
            self.current_index = min(len(self.playlist) - 1, self.current_index + 1)
            self._play_track_at(self.current_index)
    
    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handle input. Returns True if consumed."""
        if not self.active or not self.window_rect:
            return False
        
        mouse_x, mouse_y = pygame.mouse.get_pos()
        
        # When dragging window, handle motion and button-up even outside window
        if self.dragging_window:
            if event.type == pygame.MOUSEMOTION:
                new_x = mouse_x - self.drag_offset[0]
                new_y = mouse_y - self.drag_offset[1]
                ww, wh = self.window_rect.size
                new_x = max(self.desktop_x, min(new_x, self.desktop_x + self.desktop_size[0] - ww))
                new_y = max(self.desktop_y, min(new_y, self.desktop_y + self.desktop_size[1] - wh))
                self._window_x, self._window_y = new_x, new_y
                self._update_layout()
                return True
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self.dragging_window = False
                return True
        
        # When dragging sliders, handle motion and button-up even outside window (same as window drag)
        if self.dragging_vol or self.dragging_bal:
            if event.type == pygame.MOUSEMOTION:
                if self.dragging_vol:
                    self._set_volume_from_slider(mouse_y)
                if self.dragging_bal:
                    self._set_balance_from_slider(mouse_y)
                return True
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if SLIDER_DEBUG:
                    print(f"[dotSONIC] Slider drag ended: vol={self.volume:.2f} bal={self.balance:.2f}")
                self.dragging_vol = False
                self.dragging_bal = False
                return True
        
        # Arrow keys (and W/S like Paper Crane BBS) for playlist scroll
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self.playlist_scroll = max(0, self.playlist_scroll - 1)
                return True
            if event.key in (pygame.K_DOWN, pygame.K_s):
                visible = getattr(self, "visible_track_count", 10)
                max_scroll = max(0, len(self.playlist) - visible)
                self.playlist_scroll = min(max_scroll, self.playlist_scroll + 1)
                return True
        
        # Must be inside window to capture (except when dragging)
        if not self.window_rect.collidepoint(mouse_x, mouse_y):
            if event.type == pygame.MOUSEBUTTONUP:
                self.dragging_vol = False
                self.dragging_bal = False
                if self.pressed_button in (self.BTN_PLAY, self.BTN_LOAD):
                    self.pressed_button = None
            return False
        
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if SLIDER_DEBUG:
                print(f"[dotSONIC] MOUSEBUTTONDOWN in window: ({mouse_x},{mouse_y}) vol_rect={self.vol_slider_rect} bal_rect={self.bal_slider_rect}")
            # Exit
            if self.exit_rect.collidepoint(mouse_x, mouse_y):
                self.close()
                return True
            
            # Sliders
            if self.vol_slider_rect.collidepoint(mouse_x, mouse_y):
                if SLIDER_DEBUG:
                    print(f"[dotSONIC] VOL slider hit: mouse=({mouse_x},{mouse_y}) rect={self.vol_slider_rect}")
                self.dragging_vol = True
                self._set_volume_from_slider(mouse_y)
                return True
            if self.bal_slider_rect.collidepoint(mouse_x, mouse_y):
                if SLIDER_DEBUG:
                    print(f"[dotSONIC] BAL slider hit: mouse=({mouse_x},{mouse_y}) rect={self.bal_slider_rect}")
                self.dragging_bal = True
                self._set_balance_from_slider(mouse_y)
                return True
            
            # Buttons
            for btn_id, rect in self.btn_rects.items():
                if rect.collidepoint(mouse_x, mouse_y):
                    self.pressed_button = btn_id
                    # Prev, next, rewind, ffwd, stop: revert backdrop after ~2.5s
                    if btn_id in (self.BTN_PREV, self.BTN_NEXT, self.BTN_REWIND, self.BTN_FFWD, self.BTN_STOP):
                        self.pressed_button_revert_at = time.time() + 2.5
                    if btn_id == self.BTN_LOAD:
                        self.open_file_browser_callback()
                    elif btn_id == self.BTN_PLAY:
                        self._toggle_play_pause()
                    elif btn_id == self.BTN_STOP:
                        self._stop_playback()
                    elif btn_id == self.BTN_PREV:
                        self._prev_track()
                    elif btn_id == self.BTN_NEXT:
                        self._next_track()
                    elif btn_id in (self.BTN_REWIND, self.BTN_FFWD):
                        # Rewind/FFWD - seek (simplified: prev/next for now)
                        if btn_id == self.BTN_REWIND:
                            self._prev_track()
                        else:
                            self._next_track()
                    return True
            
            # Click on window background (not exit, sliders, buttons) -> start window drag
            self.dragging_window = True
            wx, wy = self.window_rect.topleft
            self.drag_offset = (mouse_x - wx, mouse_y - wy)
            if self._window_x is None:
                self._window_x, self._window_y = wx, wy
            return True
        
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging_vol = False
            self.dragging_bal = False
            # Play and load revert immediately; prev/next/rewind/ffwd/stop revert after timer
            if self.pressed_button in (self.BTN_PLAY, self.BTN_LOAD):
                self.pressed_button = None
            return True
        
        elif event.type == pygame.MOUSEMOTION:
            if self.dragging_vol:
                self._set_volume_from_slider(mouse_y)
                return True
            if self.dragging_bal:
                self._set_balance_from_slider(mouse_y)
                return True
        
        return True
    
    def _set_volume_from_slider(self, mouse_y: int) -> None:
        r = self.vol_slider_rect
        t = (r.bottom - mouse_y) / r.height if r.height else 0
        self.volume = max(0.0, min(1.0, t))
        try:
            pygame.mixer.music.set_volume(self._effective_volume())
        except Exception:
            pass
    
    def _set_balance_from_slider(self, mouse_y: int) -> None:
        """Up = left speaker, Down = right speaker, Middle = 50/50. Balance -1 (left) to 1 (right)."""
        r = self.bal_slider_rect
        t = (r.bottom - mouse_y) / r.height if r.height else 0  # t=0 at bottom, t=1 at top
        self.balance = max(-1.0, min(1.0, 1 - 2 * t))  # top=left(-1), bottom=right(1), middle=0
    
    def draw(self) -> None:
        """Draw the player."""
        if not self.active or not self.window_rect:
            return
        
        wx, wy = self.window_rect.topleft
        ww, wh = self.window_rect.size
        
        # Revert non-play button backdrop after a few seconds
        revert_buttons = (self.BTN_PREV, self.BTN_NEXT, self.BTN_REWIND, self.BTN_FFWD, self.BTN_STOP)
        if self.pressed_button in revert_buttons and time.time() > self.pressed_button_revert_at:
            self.pressed_button = None
            self.pressed_button_revert_at = 0.0
        
        # Backdrop: swap by pressed button and play state
        key = self._get_backdrop_key()
        backdrop_img = self.backdrops.get(key) if key else None
        if backdrop_img:
            scaled = pygame.transform.scale(backdrop_img, (ww, wh))
            self.screen.blit(scaled, self.window_rect.topleft)
        else:
            pygame.draw.rect(self.screen, COLOR_BG_DARK, self.window_rect)
        
        # Equalizer display (7.3, 30.7) to (93.0, 50.4) - track name + animation in same box
        pygame.draw.rect(self.screen, COLOR_DISPLAY, self.eq_display)
        
        # Track name at top of eq_display box (28 char limit, truncate with "...sonic")
        track_text = "No track loaded"
        if self.playlist and 0 <= self.current_index < len(self.playlist):
            track_text = self.playlist[self.current_index]["title"]
        if self.playing and self.paused:
            track_text += " [PAUSED]"
        if len(track_text) > 28:
            track_text = track_text[:28] + "...sonic"
        t_surf = self.font.render(track_text, True, COLOR_WHITE)
        tw, th = t_surf.get_size()
        tx = self.eq_display.x + (self.eq_display.width - tw) // 2
        ty = self.eq_display.y + int(4 * self._layout_scale)
        self.screen.blit(t_surf, (tx, ty))
        
        # Spectrum analyzer / oscilloscope visualizer
        eq_inner = self.eq_display.inflate(-int(4 * self._layout_scale), -int(4 * self._layout_scale))
        reserve_top = th + int(6 * self._layout_scale)
        eq_inner.top += reserve_top
        eq_inner.height -= reserve_top
        if eq_inner.height > 0 and eq_inner.width > 0:
            self._draw_visualizer(eq_inner)
        
        # Lower display: track list (1. 2. 3. etc) - up to 10 visible, no cyan rim
        pygame.draw.rect(self.screen, COLOR_DISPLAY, self.lower_display)
        list_rect = pygame.Rect(
            self.lower_display.x + int(5 * self._layout_scale),
            self.lower_display.y + int(5 * self._layout_scale),
            self.lower_display.width - int(10 * self._layout_scale),
            self.lower_display.height - int(10 * self._layout_scale)
        )
        font_h = self.font.get_height()
        row_h = font_h + int(3 * self._layout_scale)
        visible_count = max(3, min(10, list_rect.height // row_h) if row_h else 3)
        for row in range(visible_count):
            i = self.playlist_scroll + row
            if i >= len(self.playlist):
                break
            entry = self.playlist[i]
            row_y = list_rect.y + row * row_h
            ly = row_y + (row_h - font_h) // 2
            is_playing = (i == self.current_index and self.playing)
            num_surf = self.font.render(f"{i + 1}. ", True, COLOR_MAGENTA)
            title = entry["title"]
            if len(title) > 22:
                title = title[:22] + "..."
            title_surf = self.font.render(title, True, COLOR_CYAN if is_playing else COLOR_WHITE)
            self.screen.blit(num_surf, (list_rect.x, ly))
            self.screen.blit(title_surf, (list_rect.x + num_surf.get_width(), ly))
        
        # Scroll indicator (Paper Crane style) when more than 10 tracks
        if len(self.playlist) > visible_count:
            max_scroll = max(0, len(self.playlist) - visible_count)
            scroll_pct = self.playlist_scroll / max_scroll if max_scroll else 0
            bar_w = max(2, int(4 * self._layout_scale))
            bar_h = max(8, int(20 * self._layout_scale))
            track_h = list_rect.height - int(10 * self._layout_scale)
            available_track = max(1, track_h - bar_h)
            bar_x = list_rect.right - bar_w - int(4 * self._layout_scale)
            bar_y = list_rect.y + int(5 * self._layout_scale) + int(scroll_pct * available_track)
            pygame.draw.rect(self.screen, COLOR_CYAN, (bar_x, bar_y, bar_w, bar_h), 0, border_radius=2)
        
        # Buttons: hotspots only (no text, outline, or fill - all invisible)
        
        # Sliders (volSwitch.png, balanceSwitch.png - no rects, no VOL/BAL text)
        self._draw_slider_png(self.vol_slider_rect, self.volume, self.vol_slider_img)
        # Balance: left(-1)=knob at top, right(1)=knob at bottom, middle=0=knob at center
        bal_value = (1 - self.balance) / 2  # -1->1(top), 1->0(bottom), 0->0.5(center)
        self._draw_slider_png(self.bal_slider_rect, bal_value, self.bal_slider_img)
        
        # Slider debug: hit rects, values, hover state
        if SLIDER_DEBUG:
            mx, my = pygame.mouse.get_pos()
            in_vol = self.vol_slider_rect.collidepoint(mx, my)
            in_bal = self.bal_slider_rect.collidepoint(mx, my)
            pygame.draw.rect(self.screen, (255, 255, 0), self.vol_slider_rect, 2)  # Yellow = VOL hit area
            pygame.draw.rect(self.screen, (255, 128, 0), self.bal_slider_rect, 2)  # Orange = BAL hit area
            pct_x = ((mx - self.window_rect.x) / self.window_rect.width * 100) if self.window_rect.width else 0
            pct_y = ((my - self.window_rect.y) / self.window_rect.height * 100) if self.window_rect.height else 0
            dbg_lines = [
                f"VOL:{self.volume:.2f} BAL:{self.balance:.2f}",
                f"drag_v:{self.dragging_vol} drag_b:{self.dragging_bal}",
                f"in_vol:{in_vol} in_bal:{in_bal} pos:{pct_x:.0f}%x{pct_y:.0f}%",
                f"VOLrect:{self.vol_slider_rect} BALrect:{self.bal_slider_rect}",
            ]
            for i, line in enumerate(dbg_lines):
                s = self.font.render(line, True, (255, 255, 0))
                self.screen.blit(s, (self.window_rect.x + 5, self.window_rect.bottom - 75 + i * 18))
        
        # Exit button
        pygame.draw.rect(self.screen, COLOR_RED, self.exit_rect)
        pygame.draw.rect(self.screen, COLOR_WHITE, self.exit_rect, 1)
        ex = self.font.render("X", True, COLOR_WHITE)
        self.screen.blit(ex, (self.exit_rect.centerx - ex.get_width() // 2, self.exit_rect.centery - ex.get_height() // 2))
        
        # Mouse position debug overlay (%) - when not in slider debug mode
        if not SLIDER_DEBUG and self.window_rect.collidepoint(pygame.mouse.get_pos()):
            mx, my = pygame.mouse.get_pos()
            pct_x = ((mx - self.window_rect.x) / self.window_rect.width * 100) if self.window_rect.width else 0
            pct_y = ((my - self.window_rect.y) / self.window_rect.height * 100) if self.window_rect.height else 0
            debug_text = f"{pct_x:.1f}, {pct_y:.1f}"
            dbg_surf = self.font.render(debug_text, True, COLOR_CYAN)
            self.screen.blit(dbg_surf, (self.window_rect.x + 5, self.window_rect.bottom - 25))
        
        # Check end of track - remove finished track, next moves up and plays
        if self.playing and not self.paused:
            try:
                if not pygame.mixer.music.get_busy():
                    if self.playlist and 0 <= self.current_index < len(self.playlist):
                        had_next = self.current_index < len(self.playlist) - 1
                        self.playlist.pop(self.current_index)
                        vis = getattr(self, "visible_track_count", 10)
                        self.playlist_scroll = max(0, min(self.playlist_scroll, max(0, len(self.playlist) - vis)))
                        if had_next and self.playlist:
                            # Next track moved up to current_index
                            self._play_track_at(self.current_index)
                        else:
                            # Was last track or playlist empty - stop
                            self.current_index = -1
                            self.playing = False
                            self.paused = False
                    else:
                        self.playing = False
                        self.paused = False
            except Exception:
                pass
    
    def _draw_slider_png(self, rect: pygame.Rect, value: float, img: Optional[pygame.Surface]) -> None:
        """Draw slider knob only. Track is blank. Hit area = rect (unchanged, still functional)."""
        if not img or rect.width <= 0 or rect.height <= 0:
            return
        # Scale knob to fit track width, preserve aspect ratio
        iw, ih = img.get_size()
        if iw <= 0:
            return
        knob_w = rect.width
        knob_h = int(ih * knob_w / iw)
        if knob_h > rect.height:
            knob_h = rect.height
            knob_w = int(iw * knob_h / ih)
        scaled = pygame.transform.smoothscale(img, (knob_w, knob_h))
        # Position: value 0 = bottom, value 1 = top; center horizontally
        knob_x = rect.centerx - knob_w // 2
        knob_y = rect.bottom - knob_h - int(value * (rect.height - knob_h))
        knob_y = max(rect.top, min(knob_y, rect.bottom - knob_h))
        self.screen.blit(scaled, (knob_x, knob_y))
