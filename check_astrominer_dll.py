
import ctypes
import os
import sys

def check_dll():
    dll_path = r"e:\Dev\Glyphis_IO BBS The Proxy Tapes\Data\games\AstroMiner\astrominer.dll"
    if not os.path.exists(dll_path):
        print(f"DLL not found at {dll_path}")
        return

    try:
        # Load dependencies if possible (Raylib) - we might need to change dir
        dll_dir = os.path.dirname(dll_path)
        os.chdir(dll_dir)
        
        # Load DLL
        print(f"Loading {dll_path}...")
        dll = ctypes.CDLL(dll_path)
        
        functions_to_check = [
            "InitializeGame",
            "UpdateFrame",
            "GetFrameBuffer",
            "SetRenderResolution",
            "SetRenderResolutionPreset",
            "ResetGame",
            "CleanupGame",
            "SetUsername",
            "IsShipDestroyed",
            "ShouldExit"
        ]
        
        print("\nChecking exports:")
        all_present = True
        for func_name in functions_to_check:
            if hasattr(dll, func_name):
                print(f"[OK] {func_name} found.")
            else:
                print(f"[MISSING] {func_name} NOT found.")
                all_present = False
                
        if all_present:
            print("\nSUCCESS: All newer API functions are present.")
        else:
            print("\nWARNING: Some functions are missing. The DLL might be outdated.")

    except Exception as e:
        print(f"Error checking DLL: {e}")

if __name__ == "__main__":
    check_dll()
