"""Embedded Astro Miner - loads C++ DLL and provides framebuffer access."""

import ctypes
import os
import pygame
import sys
from typing import Optional, Tuple

# Try to load the DLL
_dll = None
_dll_path = None
_PRESET_MAP = {"low": 0, "medium": 1, "high": 2}
_render_preset: Optional[int] = None
_requested_resolution: Optional[Tuple[int, int]] = None

print(f"DEBUG: Loaded astrominer_embed module from {__file__}")

def _find_dll() -> Optional[str]:
    """Find the astrominer DLL."""
    # Check in the AstroMiner directory
    try:
        base_path = os.path.dirname(os.path.abspath(__file__))
    except NameError:
        base_path = os.getcwd()
    
    # HARDCODED PATH CHECK FOR DEBUGGING
    hardcoded_path = r"E:\Dev\Glyphis_IO BBS The Proxy Tapes\Data\games\AstroMiner\astrominer.dll"
    if os.path.exists(hardcoded_path):
        print(f"DEBUG: Found DLL at hardcoded path: {hardcoded_path}")
        return hardcoded_path

    dll_paths = [
        os.path.join(base_path, "AstroMiner", "astrominer.dll"),
        os.path.join(os.path.dirname(base_path), "games", "AstroMiner", "astrominer.dll"), # In case of wrong base
        os.path.join("Data", "games", "AstroMiner", "astrominer.dll"), # Relative to root
        "astrominer.dll",  # Current directory
    ]
    
    print(f"DEBUG: Searching for DLL in paths: {dll_paths}")
    for path in dll_paths:
        exists = os.path.exists(path)
        print(f"DEBUG: Checking {path} -> {exists}")
        if exists:
            return os.path.abspath(path)
    
    print("DEBUG: DLL NOT FOUND IN ANY PATH")
    return None

def _get_requested_preset() -> int:
    global _render_preset
    if _render_preset is not None:
        return _render_preset
    env_value = os.environ.get("ASTROMINER_RESOLUTION", "").strip().lower()
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
        print(f"[astrominer_embed] Unknown resolution mode '{mode}', valid options: {list(_PRESET_MAP.keys())}")
        return False
    _render_preset = preset
    _requested_resolution = None
    if _dll is not None and getattr(_dll, "_has_resolution_preset", False):
        try:
            _dll.SetRenderResolutionPreset(preset)
        except Exception as exc:
            print(f"[astrominer_embed] Warning: Failed to push resolution preset to DLL: {exc}")
    return True

def set_render_resolution(width: int, height: int) -> bool:
    """Request an explicit render resolution before initializing the DLL."""
    global _requested_resolution, _render_preset
    try:
        width = max(320, int(width))
        height = max(200, int(height))
    except (TypeError, ValueError):
        print("[astrominer_embed] Invalid resolution values supplied.")
        return False
    _requested_resolution = (width, height)
    _render_preset = None
    if _dll is not None and getattr(_dll, "_has_resolution", False):
        try:
            _dll.SetRenderResolution(width, height)
        except Exception as exc:
            print(f"[astrominer_embed] Warning: Failed to push custom resolution {width}x{height}: {exc}")
    return True

def initialize() -> bool:
    """Initialize the embedded game DLL."""
    global _dll, _dll_path
    
    if _dll is not None:
        return True
    
    _dll_path = _find_dll()
    if not _dll_path:
        print("ERROR: astrominer.dll not found")
        return False
    
    print(f"DEBUG: Found astrominer.dll at: {_dll_path}")
    try:
        import time
        mtime = os.path.getmtime(_dll_path)
        print(f"DEBUG: DLL Modification Time: {time.ctime(mtime)}")
    except Exception as e:
        print(f"DEBUG: Could not get DLL timestamp: {e}")

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
        # Change CWD to DLL dir PERMANENTLY for this session context
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
        
        # Set up function signatures
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
        
        # Initialize the game first (before optional functions)
        # NOTE: CWD is still dll_dir here, so shaders should load fine
        resolution_applied = False
        if _requested_resolution and getattr(_dll, "_has_resolution", False):
            try:
                width, height = _requested_resolution
                _dll.SetRenderResolution(int(width), int(height))
                resolution_applied = True
                print(f"[astrominer_embed] Applied custom resolution {width}x{height}")
            except Exception as exc:
                print(f"[astrominer_embed] Warning: Failed to apply custom resolution {_requested_resolution}: {exc}")
        if not resolution_applied and getattr(_dll, "_has_resolution_preset", False):
            try:
                preset_value = int(_get_requested_preset())
                _dll.SetRenderResolutionPreset(preset_value)
                resolution_applied = True
                print(f"[astrominer_embed] Applied preset resolution '{preset_value}'")
            except Exception as exc:
                print(f"[astrominer_embed] Warning: Failed to apply render resolution preset: {exc}")

        if not _dll.InitializeGame():
            print("ERROR: Failed to initialize game")
            return False
        
        # Try to set up ShouldExit function (may not exist in older DLLs)
        # This is optional and won't cause initialization to fail
        _dll._has_should_exit = False
        try:
            # Use getattr with a default to safely check if function exists
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
            
        print("Astro Miner initialized successfully")
        return True
        
    except AttributeError as e:
        # Check if it's ShouldExit (optional) - if so, continue
        error_str = str(e)
        if "ShouldExit" in error_str:
            # ShouldExit is optional, so continue initialization
            print(f"Note: Optional function not found in DLL: {e}")
            if _dll:
                _dll._has_should_exit = False
                # Check if InitializeGame was already called successfully
                try:
                    # If we got here, InitializeGame might not have been called
                    # Try to call it now
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
        print(f"ERROR: Failed to load astrominer.dll: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Restore CWD? 
        # Actually, for the game to continue loading resources in UpdateFrame (if any), 
        # it might need CWD. But usually InitializeGame loads everything.
        # Raylib might reload textures if context is lost? No, we don't lose context.
        # It's safer to restore CWD for the BBS, but if the game relies on relative paths
        # in UpdateFrame (unlikely for now), it might break.
        # Given the architecture, let's restore it.
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
        buf_view = memoryview(array_type.from_address(address))
        
        # Create pygame surface from buffer
        surf = pygame.image.frombuffer(buf_view, (width, height), "RGBA")
        surf = pygame.transform.flip(surf, False, True)  # Flip vertically
        return surf.convert_alpha()
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

def set_key_state(key: int, down: bool):
    """Set a key state in the game."""
    if _dll:
        try:
            _dll.SetKeyState(key, down)
        except Exception as e:
            print(f"ERROR: Failed to set key state: {e}")

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

def should_exit():
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
    _dll = None
