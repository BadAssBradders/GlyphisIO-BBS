"""Embedded Astro Miner - loads C++ DLL and provides framebuffer access."""

import ctypes
import os
import pygame
from typing import Optional, Tuple

# Try to load the DLL
_dll = None
_dll_path = None

def _find_dll() -> Optional[str]:
    """Find the astrominer DLL."""
    # Check in the AstroMiner directory
    base_path = os.path.dirname(__file__)
    dll_paths = [
        os.path.join(base_path, "AstroMiner", "astrominer.dll"),
        os.path.join(os.path.dirname(base_path), "AstroMiner", "astrominer.dll"),
        "astrominer.dll",  # Current directory
    ]
    
    for path in dll_paths:
        if os.path.exists(path):
            return os.path.abspath(path)
    return None

def initialize() -> bool:
    """Initialize the embedded game DLL."""
    global _dll, _dll_path
    
    if _dll is not None:
        return True
    
    _dll_path = _find_dll()
    if not _dll_path:
        print("ERROR: astrominer.dll not found")
        return False
    
    try:
        # Load DLL - use CDLL for __cdecl calling convention
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
        
        # Initialize the game
        if not _dll.InitializeGame():
            print("ERROR: Failed to initialize game")
            return False
        
        return True
    except AttributeError as e:
        print(f"ERROR: Function not found in DLL: {e}")
        print(f"DLL path: {_dll_path}")
        return False
    except Exception as e:
        print(f"ERROR: Failed to load astrominer.dll: {e}")
        import traceback
        traceback.print_exc()
        return False

def get_frame_surface() -> Optional[pygame.Surface]:
    """Get the current frame as a pygame Surface."""
    static_call_count = getattr(get_frame_surface, '_call_count', 0)
    get_frame_surface._call_count = static_call_count + 1
    
    if _dll is None:
        print("[get_frame_surface] ERROR: DLL is None!")
        if not initialize():
            return None
    
    try:
        # Update the game frame (runs one frame of game logic and rendering)
        if static_call_count % 60 == 0:
            print(f"[get_frame_surface] Calling UpdateFrame() (call #{static_call_count})...")
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
        
        # Read the pixel data
        size = width * height * 4  # RGBA
        buf = ctypes.string_at(ptr, size)
        
        if static_call_count % 60 == 0:
            print(f"[get_frame_surface] Got framebuffer: {width}x{height}, size={size}, buffer_len={len(buf)}")
        
        # Create pygame surface from buffer
        # Note: framebuffer is flipped vertically, so we need to flip it
        surf = pygame.image.frombuffer(buf, (width, height), "RGBA")
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

def cleanup():
    """Cleanup resources."""
    global _dll
    _dll = None

