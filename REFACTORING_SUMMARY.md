# Refactoring Summary

This document describes the modular refactoring of `main.py` into a cleaner, more maintainable structure.

## New Directory Structure

```
.
├── config.py                 # All constants and configuration
├── utils.py                  # Utility functions (data paths, logging, time)
├── main.py                   # Thin entry point (imports and runs game)
├── systems/                  # Supporting systems
│   ├── __init__.py
│   ├── email_db.py          # Email and EmailDatabase classes
│   ├── npc.py                # NPCResponder class
│   ├── token_inventory.py    # TokenInventory class
│   └── steam_manager.py      # SteamManager class
├── ui/                       # UI components
│   ├── __init__.py
│   ├── documentation_viewer.py  # DocumentationViewer (extracted from main.py)
│   └── renderers/            # Module-specific renderers (future)
│       └── __init__.py
├── modules/                   # BBS module handlers (future)
│   └── __init__.py
└── core/                      # Core game logic (future)
    ├── __init__.py
    └── game.py               # Main GLYPHIS_IOBBS class (future)
```

## What Was Moved

### config.py
- All color constants (BLACK, CYAN, etc.)
- Screen and BBS window dimensions
- Module names
- Game states
- Keyboard shortcuts
- Animation timings
- Hotspot coordinates

### utils.py
- `get_data_path()` - Data folder path resolution
- `log_event()` - Logging helper
- `get_realtime_datetime()` - Current datetime
- `get_tokyo_datetime()` - Tokyo timezone datetime
- `_is_tokyo_nighttime()` - Nighttime detection
- `_get_time_aware_video_name()` - Time-aware video selection
- `format_ingame_timestamp()` - In-game timestamp formatting
- `format_ingame_clock()` - In-game clock formatting
- `normalize_timestamp_1989()` - Timestamp normalization

### systems/email_db.py
- `Email` class
- `EmailDatabase` class

### systems/npc.py
- `NPCResponder` class

### systems/token_inventory.py
- `TokenInventory` class

### systems/steam_manager.py
- `SteamManager` class
- Steam API availability check

## Import Changes

The refactored `main.py` now imports from these modules:

```python
from config import *
from utils import get_data_path, log_event, _get_time_aware_video_name
from systems import Email, EmailDatabase, NPCResponder, TokenInventory, SteamManager
```

## Benefits

1. **Maintainability**: Code is organized by responsibility
2. **Readability**: Easier to find specific functionality
3. **Testability**: Individual modules can be tested in isolation
4. **Scalability**: Easy to add new modules or systems
5. **Reduced File Size**: `main.py` is now much smaller and focused

## Next Steps (Future Refactoring)

1. Extract UI rendering methods into separate renderer classes
2. Move module-specific logic (email, games, tasks, etc.) to `modules/`
3. Extract core game loop and state management to `core/game.py`
4. Create input handler module for keyboard/mouse handling

## Migration Notes

- All existing functionality is preserved
- No changes to game behavior
- Imports updated to use new module structure
- Backward compatibility maintained where possible

