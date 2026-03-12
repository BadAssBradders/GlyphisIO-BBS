# Repository Guidelines

## Project Structure & Module Organization
`main.py` is the primary entry point for the game. Shared Python systems live in `systems/` and root helpers such as `config.py`, `utils.py`, and `tokens.py`. Most game content, embedded modules, and runtime assets live under `Data/`, including OS mode (`Data/OS/`), standalone games (`Data/games/`), outside BBS modules, fonts, and JSON data. Automated tests are in `tests/`. Packaging outputs go to `build/` and `dist/`; treat both as generated artifacts.

## Build, Test, and Development Commands
Use Python 3.10+ in a virtual environment.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
pytest tests -q
```

`test_local.bat` launches the game in local development mode. `build_for_steam.bat` runs PyInstaller with `build_game.spec` and creates `dist\GlyphisIO_BBS\`. `test_build.bat` starts the packaged executable for smoke testing.

## Coding Style & Naming Conventions
Follow existing Python conventions: 4-space indentation, `snake_case` for functions and variables, `PascalCase` for classes, and uppercase constants for module-level configuration. Keep modules focused and prefer extending existing subsystems over adding new root-level scripts. Preserve asset and data paths exactly; many runtime loaders depend on fixed filenames inside `Data/`.

## Testing Guidelines
This repo uses both `pytest` discovery and `unittest`-style test classes. Add tests in `tests/` with names like `test_email_feature.py` or `test_npc_relationships.py`. Cover logic changes in `systems/`, token progression, email behavior, and any regression-prone save/data handling. For UI-heavy changes that are hard to automate, include a short manual verification note in the PR.

## Commit & Pull Request Guidelines
Recent history favors short, imperative commit subjects such as `Update game files, OS mode, email system, and add test files` or `Remove node_modules from repo`. Keep subjects concise and action-oriented. PRs should state the gameplay or system impact, list test coverage, and attach screenshots or short clips for visible UI changes.

## Assets & Repository Hygiene
Do not commit generated folders like `node_modules/`, `build/`, `dist/`, logs, or large media exports covered by `.gitignore`. Be careful with binaries, PSDs, audio, and video files; only add new heavy assets when they are required for runtime or release packaging.
