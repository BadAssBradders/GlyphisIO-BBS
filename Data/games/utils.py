from __future__ import annotations

from pathlib import Path
from typing import Union
import os
import sys

import pygame

_PACKAGE_ROOT = Path(__file__).resolve().parent
ROOT_DIR = _PACKAGE_ROOT.parent


def get_data_path(*path_parts):
    """Helper to get data path - works for both dev and built exe"""
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = str(ROOT_DIR)
    data_folder = os.path.join(base_path, "Data")
    if os.path.exists(data_folder):
        return os.path.join(data_folder, *path_parts)
    else:
        return os.path.join(base_path, *path_parts)


def resolve_asset_path(relative_path: Union[str, Path]) -> Path:
    """Return an absolute path inside the Data folder for game assets."""

    if isinstance(relative_path, Path):
        relative = relative_path
    else:
        relative = Path(relative_path)
    # Try Data folder first, then fall back to root
    data_path = Path(get_data_path(str(relative)))
    if data_path.exists():
        return data_path
    return ROOT_DIR / relative


def load_root_font(font_name: Union[str, Path], size: int) -> pygame.font.Font:
    """Load a TTF font from the Data folder, gracefully falling back to default."""

    # Try Data folder first
    try:
        font_path = get_data_path(str(font_name))
        if os.path.exists(font_path):
            return pygame.font.Font(font_path, size)
    except:
        pass
    
    # Fallback to root directory
    font_path = resolve_asset_path(font_name)
    try:
        return pygame.font.Font(str(font_path), size)
    except (FileNotFoundError, OSError):
        return pygame.font.Font(None, size)

