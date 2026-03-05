"""Embedded CyberTrain - loads C++ DLL and provides framebuffer access."""

import ctypes
import os
import pygame
import sys
import time
from typing import Optional, Tuple

# DLL state
_dll = None
_dll_path = None
_PRESET_MAP = {"low": 0, "medium": 1, "high": 2}
_render_preset: Optional[int] = None
_requested_resolution: Optional[Tuple[int, int]] = None
_debug_last_print_time = 0.0

print(f"DEBUG: Loaded cybertrain_embed module from {__file__}")

def _find_dll() -> Optional[str]:
    """Find the CyberTrain DLL."""
    try:
        base_path = os.path.dirname(os.path.abspath(__file__))
    except NameError:
        base_path = os.getcwd()

    # Optional explicit override for debugging and CI.
    override = os.environ.get("CYBERTRAIN_DLL_PATH", "").strip()
    if override and os.path.exists(override):
        resolved = os.path.abspath(override)
        print(f"DEBUG: Using CYBERTRAIN_DLL_PATH override: {resolved}")
        return resolved

    # Prefer project-local DLL next to this embed module.
    repo_root = os.path.dirname(base_path)  # .../Data
    repo_root = os.path.dirname(repo_root)  # project root

    dll_paths = [
        os.path.join(base_path, "CyberTrain", "cybertrain.dll"),
        os.path.join(repo_root, "Data", "games", "CyberTrain", "cybertrain.dll"),
        os.path.join(base_path, "CyberTrain", "bin", "cybertrain.dll"),
        os.path.join(os.path.dirname(base_path), "games", "CyberTrain", "cybertrain.dll"),
        os.path.join("Data", "games", "CyberTrain", "cybertrain.dll"),
        "cybertrain.dll",
    ]
    
    print(f"DEBUG: Searching for DLL in paths: {dll_paths}")
    for path in dll_paths:
        exists = os.path.exists(path)
        print(f"DEBUG: Checking {path} -> {exists}")
        if exists:
            resolved = os.path.abspath(path)
            print(f"DEBUG: Selected cybertrain.dll: {resolved}")
            return resolved
    
    print("DEBUG: DLL NOT FOUND IN ANY PATH")
    return None


def _get_requested_preset() -> int:
    global _render_preset
    if _render_preset is not None:
        return _render_preset
    env_value = os.environ.get("CYBERTRAIN_RESOLUTION", "").strip().lower()
    if env_value == "auto":
        return 2  # default to high when auto is requested and no explicit size was set
    return _PRESET_MAP.get(env_value, 1)


def set_resolution_mode(mode: str) -> bool:
    """Set desired render preset before initializing the DLL."""
    global _render_preset, _requested_resolution
    if not mode:
        return False
    preset = _PRESET_MAP.get(mode.strip().lower())
    if preset is None:
        print(f"[cybertrain_embed] Unknown resolution mode '{mode}', valid options: {list(_PRESET_MAP.keys())}")
        return False
    _render_preset = preset
    _requested_resolution = None
    if _dll is not None and getattr(_dll, "_has_resolution_preset", False):
        try:
            _dll.SetRenderResolutionPreset(preset)
        except Exception as exc:
            print(f"[cybertrain_embed] Warning: Failed to push resolution preset to DLL: {exc}")
    return True


def set_render_resolution(width: int, height: int) -> bool:
    """Request an explicit render resolution before initializing the DLL."""
    global _requested_resolution, _render_preset
    try:
        width = max(320, int(width))
        height = max(200, int(height))
    except (TypeError, ValueError):
        print("[cybertrain_embed] Invalid resolution values supplied.")
        return False
    _requested_resolution = (width, height)
    _render_preset = None
    if _dll is not None and getattr(_dll, "_has_resolution", False):
        try:
            _dll.SetRenderResolution(width, height)
        except Exception as exc:
            print(f"[cybertrain_embed] Warning: Failed to push custom resolution {width}x{height}: {exc}")
    return True


def initialize() -> bool:
    """Initialize the embedded game DLL."""
    global _dll, _dll_path
    
    if _dll is not None:
        return True
    
    _dll_path = _find_dll()
    if not _dll_path:
        print("ERROR: cybertrain.dll not found")
        return False
    
    print(f"DEBUG: Found cybertrain.dll at: {_dll_path}")
    try:
        mtime = os.path.getmtime(_dll_path)
        dll_size = os.path.getsize(_dll_path)
        print(f"DEBUG: DLL Modification Time: {time.ctime(mtime)} | size: {dll_size} bytes")
        # Helpful sanity check: if the DLL is older than the C++ source, you're running stale code.
        cpp_path = os.path.join(os.path.dirname(_dll_path), "main.cpp")
        if os.path.exists(cpp_path):
            cpp_mtime = os.path.getmtime(cpp_path)
            if mtime < cpp_mtime:
                print(
                    "[cybertrain_embed] WARNING: cybertrain.dll is older than main.cpp. "
                    "Rebuild the DLL (build_dll.bat) or you won't see recent C++ fixes."
                )
    except Exception as e:
        print(f"DEBUG: Could not get DLL/source timestamp: {e}")

    dll_dir = os.path.dirname(_dll_path)
    
    # Python 3.8+ DLL loading security
    if hasattr(os, 'add_dll_directory'):
        try:
            os.add_dll_directory(dll_dir)
        except Exception as e:
            print(f"Warning: Failed to add DLL directory {dll_dir}: {e}")
            
    # Also add to PATH for good measure (and legacy systems)
    os.environ['PATH'] = dll_dir + os.pathsep + os.environ['PATH']
    
    cwd = os.getcwd()
    try:
        # Change CWD to DLL dir for this initialization context
        # This is critical for:
        # 1. Loading dependencies (libwinpthread-1.dll, raylib.dll)
        # 2. Game resource loading (shaders, textures) which use relative paths
        os.chdir(dll_dir)
        print(f"[initialize] Changed CWD to {dll_dir}")
        
        # Load dependencies explicitly (including MinGW runtime DLLs)
        dependencies = [
            "libgcc_s_seh-1.dll",  # MinGW runtime
            "libstdc++-6.dll",     # MinGW C++ runtime
            "libwinpthread-1.dll", # MinGW threading
            "raylib.dll"           # Raylib
        ]
        for dep in dependencies:
            if os.path.exists(dep):
                try:
                    ctypes.CDLL(dep)
                    print(f"Pre-loaded dependency: {dep}")
                except Exception as dep_err:
                    print(f"Warning: Failed to pre-load {dep}: {dep_err}")
            else:
                print(f"Warning: Dependency not found: {dep}")
        
        # Load Main DLL
        _dll = ctypes.CDLL(_dll_path)
        
        # Set up required function signatures
        _dll.InitializeGame.restype = ctypes.c_bool
        _dll.InitializeGame.argtypes = []
        
        _dll.GetFrameBuffer.restype = ctypes.POINTER(ctypes.c_ubyte)
        _dll.GetFrameBuffer.argtypes = []
        
        _dll.GetWidth.restype = ctypes.c_int
        _dll.GetWidth.argtypes = []
        
        _dll.GetHeight.restype = ctypes.c_int
        _dll.GetHeight.argtypes = []
        
        _dll.UpdateFrame.restype = None
        _dll.UpdateFrame.argtypes = []
        
        _dll.SetKeyState.restype = None
        _dll.SetKeyState.argtypes = [ctypes.c_int, ctypes.c_bool]
        
        _dll.SetMouseButtonState.restype = None
        _dll.SetMouseButtonState.argtypes = [ctypes.c_int, ctypes.c_bool]
        
        _dll.SetInputMousePosition.restype = None
        _dll.SetInputMousePosition.argtypes = [ctypes.c_float, ctypes.c_float]
        
        _dll.SetMouseDelta.restype = None
        _dll.SetMouseDelta.argtypes = [ctypes.c_float, ctypes.c_float]

        # Optional character-input bridge for embedded text entry
        _dll._has_char_input = False
        try:
            char_input_func = getattr(_dll, "SetCharInput", None)
            if char_input_func is not None:
                _dll.SetCharInput.restype = None
                _dll.SetCharInput.argtypes = [ctypes.c_int]
                _dll._has_char_input = True
        except (AttributeError, OSError, TypeError):
            _dll._has_char_input = False
        
        # Optional resolution functions
        try:
            _dll.SetRenderResolution.restype = None
            _dll.SetRenderResolution.argtypes = [ctypes.c_int, ctypes.c_int]
            _dll._has_resolution = True
        except AttributeError:
            _dll._has_resolution = False

        try:
            _dll.SetRenderResolutionPreset.restype = None
            _dll.SetRenderResolutionPreset.argtypes = [ctypes.c_int]
            _dll._has_resolution_preset = True
        except AttributeError:
            _dll._has_resolution_preset = False
        
        # Apply resolution settings before InitializeGame
        resolution_applied = False
        if _requested_resolution and getattr(_dll, "_has_resolution", False):
            try:
                width, height = _requested_resolution
                _dll.SetRenderResolution(int(width), int(height))
                resolution_applied = True
                print(f"[cybertrain_embed] Applied custom resolution {width}x{height}")
            except Exception as exc:
                print(f"[cybertrain_embed] Warning: Failed to apply custom resolution {_requested_resolution}: {exc}")
        if not resolution_applied and getattr(_dll, "_has_resolution_preset", False):
            try:
                preset_value = int(_get_requested_preset())
                _dll.SetRenderResolutionPreset(preset_value)
                resolution_applied = True
                print(f"[cybertrain_embed] Applied preset resolution '{preset_value}'")
            except Exception as exc:
                print(f"[cybertrain_embed] Warning: Failed to apply render resolution preset: {exc}")

        # Initialize the game
        if not _dll.InitializeGame():
            print("ERROR: Failed to initialize game")
            return False
        
        # Try to set up ShouldExit function (may not exist in older DLLs)
        _dll._has_should_exit = False
        try:
            should_exit_func = getattr(_dll, 'ShouldExit', None)
            if should_exit_func is not None:
                _dll.ShouldExit.restype = ctypes.c_bool
                _dll.ShouldExit.argtypes = []
                _dll._has_should_exit = True
            else:
                print("Note: ShouldExit function not available in DLL (will be available after recompiling)")
        except (AttributeError, OSError, TypeError) as e:
            _dll._has_should_exit = False
            print(f"Note: Could not set up ShouldExit function: {e}")
        
        # Try to set up GetLastFinalScore function (optional)
        _dll._has_get_score = False
        try:
            get_score_func = getattr(_dll, 'GetLastFinalScore', None)
            if get_score_func is not None:
                _dll.GetLastFinalScore.restype = ctypes.c_int
                _dll.GetLastFinalScore.argtypes = []
                _dll._has_get_score = True
        except (AttributeError, OSError, TypeError) as e:
            _dll._has_get_score = False
        
        # Try to set up SetUsername function (optional)
        _dll._has_set_username = False
        try:
            set_username_func = getattr(_dll, 'SetUsername', None)
            if set_username_func is not None:
                _dll.SetUsername.restype = None
                _dll.SetUsername.argtypes = [ctypes.c_char_p]
                _dll._has_set_username = True
        except (AttributeError, OSError, TypeError) as e:
            _dll._has_set_username = False
        
        # Try to set up ResetGame function (optional)
        _dll._has_reset_game = False
        try:
            reset_game_func = getattr(_dll, 'ResetGame', None)
            if reset_game_func is not None:
                _dll.ResetGame.restype = None
                _dll.ResetGame.argtypes = []
                _dll._has_reset_game = True
        except (AttributeError, OSError, TypeError) as e:
            _dll._has_reset_game = False
        
        # Try to set up ShouldCenterMouse function (optional)
        _dll._has_center_mouse = False
        try:
            center_mouse_func = getattr(_dll, 'ShouldCenterMouse', None)
            if center_mouse_func is not None:
                _dll.ShouldCenterMouse.restype = ctypes.c_bool
                _dll.ShouldCenterMouse.argtypes = []
                _dll._has_center_mouse = True
        except (AttributeError, OSError, TypeError) as e:
            _dll._has_center_mouse = False

        # Try to set up SetMouseWheelMove function (optional)
        _dll._has_mouse_wheel = False
        try:
            mouse_wheel_func = getattr(_dll, 'SetMouseWheelMove', None)
            if mouse_wheel_func is not None:
                _dll.SetMouseWheelMove.restype = None
                _dll.SetMouseWheelMove.argtypes = [ctypes.c_float]
                _dll._has_mouse_wheel = True
        except (AttributeError, OSError, TypeError) as e:
            _dll._has_mouse_wheel = False

        # Optional cleanup hook so the BBS can tear down the DLL cleanly
        _dll._has_cleanup = False
        try:
            cleanup_func = getattr(_dll, 'CleanupGame', None)
            if cleanup_func is not None:
                _dll.CleanupGame.restype = None
                _dll.CleanupGame.argtypes = []
                _dll._has_cleanup = True
        except (AttributeError, OSError, TypeError):
            _dll._has_cleanup = False

        # Optional debug exports (used to diagnose black-frame issues in BBS embedding)
        debug_int_exports = [
            "GetDebugFrameCounter",
            "GetDebugRenderStage",
            "GetDebugSplashPhase",
            "GetDebugIntroModalOpen",
            "GetDebugHelpModalOpen",
            "GetDebugUIAssetsLoaded",
            "GetDebugTextureIdUI",
            "GetDebugTextureIdCursor",
            "GetDebugTextureIdSplash1",
            "GetDebugTextureIdSplash2",
            "GetDebugTextureIdSplash3",
            "GetDebugTextureIdModal",
            "GetDebugTextureIdLargeModal",
            "GetDebugFramebufferTextureId",
        ]
        _dll._debug_exports = {}
        for export_name in debug_int_exports:
            try:
                func = getattr(_dll, export_name, None)
                if func is not None:
                    func.restype = ctypes.c_int
                    func.argtypes = []
                    _dll._debug_exports[export_name] = func
            except (AttributeError, OSError, TypeError):
                pass

        # IsGameOver — signals year 6 reached
        _dll._has_is_game_over = False
        try:
            if getattr(_dll, 'IsGameOver', None) is not None:
                _dll.IsGameOver.restype = ctypes.c_bool
                _dll.IsGameOver.argtypes = []
                _dll._has_is_game_over = True
        except (AttributeError, OSError, TypeError):
            pass

        # GetFinalScore — credits at game-over
        _dll._has_get_final_score = False
        try:
            if getattr(_dll, 'GetFinalScore', None) is not None:
                _dll.GetFinalScore.restype = ctypes.c_int
                _dll.GetFinalScore.argtypes = []
                _dll._has_get_final_score = True
        except (AttributeError, OSError, TypeError):
            pass

        # PushLeaderboardEntry — inject Steam entries into the DLL display
        _dll._has_push_leaderboard = False
        try:
            if getattr(_dll, 'PushLeaderboardEntry', None) is not None:
                _dll.PushLeaderboardEntry.restype = None
                _dll.PushLeaderboardEntry.argtypes = [ctypes.c_char_p, ctypes.c_int]
                _dll._has_push_leaderboard = True
        except (AttributeError, OSError, TypeError):
            pass

        # GetLeaderboardCount / GetLeaderboardEntry — read DLL leaderboard
        _dll._has_get_lb_count = False
        try:
            if getattr(_dll, 'GetLeaderboardCount', None) is not None:
                _dll.GetLeaderboardCount.restype = ctypes.c_int
                _dll.GetLeaderboardCount.argtypes = []
                _dll._has_get_lb_count = True
        except (AttributeError, OSError, TypeError):
            pass

        print("CyberTrain initialized successfully")
        return True
        
    except AttributeError as e:
        # Check if it's an optional function - if so, continue
        error_str = str(e)
        if "ShouldExit" in error_str:
            print(f"Note: Optional function not found in DLL: {e}")
            if _dll:
                _dll._has_should_exit = False
                try:
                    if hasattr(_dll, 'InitializeGame'):
                        if _dll.InitializeGame():
                            print("Continuing without ShouldExit function...")
                            return True
                except:
                    pass
            return False
        else:
            print(f"ERROR: Required function not found in DLL: {e}")
            print(f"DLL path: {_dll_path}")
            return False
    except Exception as e:
        print(f"ERROR: Failed to load cybertrain.dll: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Restore CWD for the BBS
        os.chdir(cwd)


def get_frame_surface() -> Optional[pygame.Surface]:
    """Get the current frame as a pygame Surface."""
    static_call_count = getattr(get_frame_surface, '_call_count', 0)
    get_frame_surface._call_count = static_call_count + 1
    
    if _dll is None:
        print("[get_frame_surface] ERROR: DLL is None!")
        if not initialize():
            return None
    
    try:
        _dll.UpdateFrame()
        
        # Get framebuffer info
        width = _dll.GetWidth()
        height = _dll.GetHeight()
        
        if width <= 0 or height <= 0:
            if static_call_count % 60 == 0:
                print(f"[get_frame_surface] ERROR: Invalid size: {width}x{height}")
            return None
        
        # Get framebuffer pointer
        ptr = _dll.GetFrameBuffer()
        if not ptr:
            if static_call_count % 60 == 0:
                print(f"[get_frame_surface] ERROR: GetFrameBuffer returned NULL")
            return None
        
        # Read the pixel data (zero-copy view over DLL buffer)
        size = width * height * 4  # RGBA
        address = ctypes.addressof(ptr.contents)
        array_type = ctypes.c_ubyte * size
        raw_array = array_type.from_address(address)
        buf_view = memoryview(raw_array)
        
        # Create pygame surface from buffer
        surf = pygame.image.frombuffer(buf_view, (width, height), "RGBA")
        surf = pygame.transform.flip(surf, False, True)  # Flip vertically
        # Embedded composition should be opaque; do not rely on render-target alpha.
        # Some GPU paths leave RGB valid but alpha at 0, which appears as black-only with cursor.
        out = surf.convert()

        # Periodic diagnostic: sample a small number of pixels to detect black/transparent frames.
        global _debug_last_print_time
        now = time.time()
        if now - _debug_last_print_time >= 1.0:
            _debug_last_print_time = now
            sample_count = 0
            non_black = 0
            alpha_non_zero = 0
            step = max(4, (size // 4096 // 4) * 4)
            for i in range(0, size, step):
                r = raw_array[i]
                g = raw_array[i + 1]
                b = raw_array[i + 2]
                a = raw_array[i + 3]
                sample_count += 1
                if r or g or b:
                    non_black += 1
                if a:
                    alpha_non_zero += 1
            dbg = get_debug_state()
            print(
                "[cybertrain_embed][frame_debug] "
                f"size={width}x{height} samples={sample_count} "
                f"non_black={non_black} alpha_non_zero={alpha_non_zero} "
                f"stage={dbg.get('render_stage')} splash={dbg.get('splash_phase')} "
                f"intro={dbg.get('intro_modal')} help={dbg.get('help_modal')} "
                f"ui_loaded={dbg.get('ui_loaded')} "
                f"tex(ui/cursor/s1/s2/s3/modal/lmodal/fb)="
                f"{dbg.get('tex_ui')}/{dbg.get('tex_cursor')}/{dbg.get('tex_splash1')}/"
                f"{dbg.get('tex_splash2')}/{dbg.get('tex_splash3')}/{dbg.get('tex_modal')}/"
                f"{dbg.get('tex_large_modal')}/{dbg.get('tex_framebuffer')}"
            )
        return out
    except Exception as e:
        print(f"[get_frame_surface] ERROR: Exception: {e}")
        import traceback
        traceback.print_exc()
        return None


def get_size() -> Tuple[int, int]:
    """Get the framebuffer size."""
    if _dll is None:
        if not initialize():
            return (0, 0)
    
    try:
        width = _dll.GetWidth()
        height = _dll.GetHeight()
        return (width, height)
    except:
        return (0, 0)


def get_debug_state() -> dict:
    """Return debug state from optional DLL exports."""
    state = {
        "frame_counter": -1,
        "render_stage": -1,
        "splash_phase": -1,
        "intro_modal": -1,
        "help_modal": -1,
        "ui_loaded": -1,
        "tex_ui": -1,
        "tex_cursor": -1,
        "tex_splash1": -1,
        "tex_splash2": -1,
        "tex_splash3": -1,
        "tex_modal": -1,
        "tex_large_modal": -1,
        "tex_framebuffer": -1,
    }
    if _dll is None:
        return state
    exports = getattr(_dll, "_debug_exports", {}) or {}
    mapping = {
        "GetDebugFrameCounter": "frame_counter",
        "GetDebugRenderStage": "render_stage",
        "GetDebugSplashPhase": "splash_phase",
        "GetDebugIntroModalOpen": "intro_modal",
        "GetDebugHelpModalOpen": "help_modal",
        "GetDebugUIAssetsLoaded": "ui_loaded",
        "GetDebugTextureIdUI": "tex_ui",
        "GetDebugTextureIdCursor": "tex_cursor",
        "GetDebugTextureIdSplash1": "tex_splash1",
        "GetDebugTextureIdSplash2": "tex_splash2",
        "GetDebugTextureIdSplash3": "tex_splash3",
        "GetDebugTextureIdModal": "tex_modal",
        "GetDebugTextureIdLargeModal": "tex_large_modal",
        "GetDebugFramebufferTextureId": "tex_framebuffer",
    }
    for export_name, key in mapping.items():
        func = exports.get(export_name)
        if func is None:
            continue
        try:
            state[key] = int(func())
        except Exception:
            pass
    return state


def set_key_state(key: int, down: bool):
    """Set a key state in the game."""
    if _dll:
        try:
            _dll.SetKeyState(key, down)
        except Exception as e:
            print(f"ERROR: Failed to set key state: {e}")


def set_char_input(codepoint: int):
    """Push a typed character codepoint into the game's input queue."""
    if _dll and hasattr(_dll, "_has_char_input") and _dll._has_char_input:
        try:
            _dll.SetCharInput(int(codepoint))
        except Exception as e:
            print(f"ERROR: Failed to set char input: {e}")


def set_mouse_button_state(button: int, down: bool):
    """Set a mouse button state in the game."""
    if _dll:
        try:
            _dll.SetMouseButtonState(button, down)
        except Exception as e:
            print(f"ERROR: Failed to set mouse button state: {e}")


def set_mouse_position(x: float, y: float):
    """Set mouse position in the game."""
    if _dll:
        try:
            _dll.SetInputMousePosition(x, y)
        except Exception as e:
            print(f"ERROR: Failed to set mouse position: {e}")


def set_mouse_delta(dx: float, dy: float):
    """Set mouse delta (movement) in the game."""
    if _dll:
        try:
            _dll.SetMouseDelta(dx, dy)
        except Exception as e:
            print(f"ERROR: Failed to set mouse delta: {e}")


def set_mouse_wheel(move: float):
    """Set mouse wheel movement in the game."""
    if _dll and hasattr(_dll, '_has_mouse_wheel') and _dll._has_mouse_wheel:
        try:
            _dll.SetMouseWheelMove(move)
        except Exception as e:
            print(f"ERROR: Failed to set mouse wheel: {e}")


def set_username(username: str) -> bool:
    """Set the current BBS username for leaderboard entries."""
    if _dll and hasattr(_dll, '_has_set_username') and _dll._has_set_username:
        try:
            username_bytes = username.encode('utf-8')
            _dll.SetUsername(username_bytes)
            return True
        except Exception as e:
            print(f"[cybertrain_embed] Failed to set username: {e}")
            return False
    return False


def get_last_final_score() -> int:
    """Get the last final score calculated (0 if no score yet)."""
    if _dll and hasattr(_dll, '_has_get_score') and _dll._has_get_score:
        try:
            return _dll.GetLastFinalScore()
        except Exception:
            return 0
    return 0


def should_center_mouse() -> bool:
    """Check if the mouse should be centered (for 3D environments)."""
    if _dll and hasattr(_dll, '_has_center_mouse') and _dll._has_center_mouse:
        try:
            return _dll.ShouldCenterMouse()
        except Exception:
            return False
    return False


def reset_game() -> bool:
    """Reset all player stats to new game defaults. Call this when launching from BBS."""
    if _dll and hasattr(_dll, '_has_reset_game') and _dll._has_reset_game:
        try:
            _dll.ResetGame()
            print("[cybertrain_embed] Game reset - all stats reset to new game defaults")
            return True
        except Exception as e:
            print(f"[cybertrain_embed] Failed to reset game: {e}")
            return False
    return False


def should_exit() -> bool:
    """Check if the game wants to exit."""
    if _dll and hasattr(_dll, '_has_should_exit') and _dll._has_should_exit:
        try:
            return _dll.ShouldExit()
        except Exception:
            return False
    return False


def cleanup():
    """Cleanup resources."""
    global _dll
    try:
        if _dll and hasattr(_dll, "_has_cleanup") and _dll._has_cleanup:
            _dll.CleanupGame()
    except Exception as exc:
        print(f"[cybertrain_embed] CleanupGame failed: {exc}")
    _dll = None


# ── Year-6 game-over / leaderboard helpers ────────────────────────────────────

STEAM_APP_ID           = 4179570
STEAM_LEADERBOARD_NAME = "CyberTrain Best City Planners"


def is_game_over() -> bool:
    """Return True when CyberTrain has reached Year 6 (game over)."""
    if _dll and getattr(_dll, '_has_is_game_over', False):
        try:
            return bool(_dll.IsGameOver())
        except Exception:
            pass
    return False


def get_final_score() -> int:
    """Return the player's final net income (credits) at game-over."""
    if _dll and getattr(_dll, '_has_get_final_score', False):
        try:
            return int(_dll.GetFinalScore())
        except Exception:
            pass
    return 0


def push_leaderboard_entry(username: str, score: int) -> bool:
    """Push a single Steam leaderboard entry into the DLL for on-screen display."""
    if _dll and getattr(_dll, '_has_push_leaderboard', False):
        try:
            _dll.PushLeaderboardEntry(username.encode('utf-8'), score)
            return True
        except Exception as exc:
            print(f"[cybertrain_embed] push_leaderboard_entry failed: {exc}")
    return False


def submit_steam_leaderboard(username: str, score: int) -> bool:
    """Submit *score* to the Steam leaderboard then pull the global top-10 back
    into the DLL so it appears in the end-game / splash screen display.

    Requires the ``steamworks`` Python package (pip install steamworks).
    Silently skips if the package is absent or Steam is not running — the local
    JSON leaderboard still works independently.

    Steam partner portal settings for "CyberTrain Best City Planners":
      Sort method:      Descending
      Display type:     Numeric
      Global Top Limit: 10000
      Range Around User:10
      Lobby:            (blank)
      Reads:            (blank)  — public, all players can read
      Writes:           (blank)  — game client writes directly
      App ID:           4179570
    """
    try:
        import steamworks  # pip install steamworks
    except ImportError:
        print("[cybertrain_embed] 'steamworks' package not installed — Steam submission skipped.")
        return False

    import time

    # steamworks reads steam_appid.txt from the current working directory;
    # temporarily switch to the CyberTrain folder where that file lives.
    _prev_cwd = os.getcwd()
    try:
        _ct_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "CyberTrain")
        if os.path.isdir(_ct_dir):
            os.chdir(_ct_dir)
    except Exception:
        pass

    try:
        sw = steamworks.STEAMWORKS()
        sw.initialize()

        # ── Find the leaderboard (created on partner portal, not at runtime) ──
        find_result: dict = {'done': False, 'handle': None}

        def _on_find(result_data, io_failure):
            if not io_failure and result_data.m_bLeaderboardFound:
                find_result['handle'] = result_data.m_hSteamLeaderboard
            find_result['done'] = True

        sw.UserStats.FindLeaderboard(STEAM_LEADERBOARD_NAME, _on_find)

        import time
        deadline = time.time() + 5.0
        while not find_result['done'] and time.time() < deadline:
            sw.run_callbacks()
            time.sleep(0.05)

        if not find_result['handle']:
            print(f"[cybertrain_embed] Steam leaderboard '{STEAM_LEADERBOARD_NAME}' not found.")
            sw.unload()
            return False

        handle = find_result['handle']

        # ── Upload score (keep best) ──────────────────────────────────────────
        upload_done: dict = {'done': False}

        def _on_upload(r, fail):
            upload_done['done'] = True

        sw.UserStats.UploadLeaderboardScore(
            handle,
            steamworks.defines.ELeaderboardUploadScoreMethod['KeepBest'],
            score,
            None,
            _on_upload,
        )
        deadline = time.time() + 5.0
        while not upload_done['done'] and time.time() < deadline:
            sw.run_callbacks()
            time.sleep(0.05)

        # ── Download global top-10 ────────────────────────────────────────────
        dl_result: dict = {'done': False, 'entries_handle': None, 'count': 0}

        def _on_download(r, fail):
            if not fail:
                dl_result['entries_handle'] = r.m_hSteamLeaderboardEntries
                dl_result['count'] = r.m_cEntryCount
            dl_result['done'] = True

        sw.UserStats.DownloadLeaderboardEntries(
            handle,
            steamworks.defines.ELeaderboardDataRequest['Global'],
            1, 10,
            _on_download,
        )
        deadline = time.time() + 5.0
        while not dl_result['done'] and time.time() < deadline:
            sw.run_callbacks()
            time.sleep(0.05)

        # ── Push entries into DLL display ─────────────────────────────────────
        if dl_result['entries_handle'] and dl_result['count'] > 0:
            for i in range(dl_result['count']):
                entry = sw.UserStats.GetDownloadedLeaderboardEntry(
                    dl_result['entries_handle'], i)
                if entry:
                    name = sw.Friends.GetFriendPersonaName(entry.m_steamIDUser) or "Unknown"
                    push_leaderboard_entry(name, entry.m_nScore)

        sw.unload()
        print(f"[cybertrain_embed] Steam leaderboard submission complete. Score: {score}")
        return True

    except Exception as exc:
        print(f"[cybertrain_embed] Steam leaderboard error: {exc}")
        return False
    finally:
        os.chdir(_prev_cwd)
