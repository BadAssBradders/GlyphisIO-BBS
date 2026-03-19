# CyberTrain Summary Map (`data/games/cybertrain/src`)

`main.cpp` (in `data/games/cybertrain/`) aggregates these `.cpp` modules into one translation unit.
That means symbols are shared across modules through file-scope globals and static helpers.

## Module Inventory

- `src/cybertrain_core.cpp` (~3024 lines)
  - Core data model and global runtime state.
  - Input abstraction (`CustomIsKeyDown`, `CustomGetMousePosition`, queue-based char input).
  - Rendering primitives for rails, trains, factories, bureaus, particles, terminal, ticker.
  - Core economy math helpers (build/running cost multipliers, discounts).
  - Path geometry/path sampling (`GetPathLength`, `GetPathPoint`, loop and distance helpers).
  - Network/cache utility and platform adjacency logic used by multiple modules.

- `src/cybertrain_network_worldgen.cpp` (~1463 lines)
  - Placement/connectivity rules and path building.
  - `CanPlaceDepotAt`, `FindConnectedPlatforms`, `BuildPlatformPath`, `RebuildTrainPath`.
  - 2D map transforms + rendering helpers (`WorldToMap`, `DrawTrainOnMap`, `DrawJunctionOnMap`).
  - World generation.
  - `GenerateClusters`, `ValidateClusters`, `generateCitySkyline`, `AddClusterBuildings`, `AddOuterRingBuildings`.

- `src/cybertrain_economy_modals.cpp` (~2330 lines)
  - Silo/market simulation loop.
  - `RecomputeSilosAndMarket`, `InitializeMarketPrices`, `UpdateMarketPrices`, `UpdateMarketEvents`, `CalculateMarketRevenue`, `CalculateNetWorth`.
  - **Magenta line bonuses (2026-03-09):** established magenta lines double factory output for SYS1 cargo silos; bureau floors on magenta lines boost magenta+commodity share performance by 10% per floor (capped 3x). Green bureau floors likewise boost green share performance by 10% per floor via `g_greenGrowthFloorBonus`.
  - Buy/sell interaction (`MarketBuyShare`, `MarketSellShare`).
  - Modal state transitions and drawing for station, line, junction, demolish, silo announce, and stock/commodities.
  - Rebuilds ticker text from gameplay/economy state (`RebuildTickerText`).

- `src/cybertrain_ui.cpp` (~1104 lines)
  - Asset lifecycle.
  - `LoadUIAssets`/`UnloadUIAssets`, splash texture lifecycle, audio asset lifecycle.
  - Audio runtime control: volume mapping, applying music/SFX volumes, track update, options handling.
  - Front-end overlays/screens: HUD overlay, custom cursor, splash, intro/help modal, year-5 warning, end-game screen.
  - Leaderboard persistence/UI: `LoadCyberTrainLeaderboard`, `SaveAndMergeLBEntry`, table rendering.

- `src/cybertrain_gameloop.cpp` (~4248 lines)
  - Frame orchestration entrypoint: `GameLoopBody()`.
  - Per-frame order (high level): input -> simulation/economy -> modal/input actions -> render.
  - Game lifecycle transitions: restart/reset pipeline (`RestartToSplashAfterGameOver`) and CyberTrain follow-cam toggles.
  - Coordinates all subsystems defined in other modules.

- `src/cybertrain_exports.cpp` (~249 lines)
  - Embedded-mode DLL bridge (`extern "C"` exports).
  - Host-facing lifecycle: `InitializeGame`, `UpdateFrame`, `CleanupGame`.
  - Host input bridge: `SetKeyState`, `SetCharInput`, mouse setters.
  - Host output bridge: `GetFrameBuffer`, `GetWidth`/`GetHeight`, texture handle, game-over/leaderboard/debug exports.

- `src/cybertrain_standalone_main.cpp` (~176 lines)
  - Native executable entrypoint (`main`).
  - Standalone init (window/audio/font/assets/world/camera) and main loop calling `GameLoopBody()`.
  - Mirrors embedded init flow where practical for parity.

## Runtime Entry Flows

- Standalone:
  - `main()` -> initialize platform/window/audio/assets/state -> `while (!WindowShouldClose()) GameLoopBody()` -> cleanup.

- Embedded (DLL):
  - `InitializeGame()` -> host repeatedly calls `UpdateFrame()` -> host reads framebuffer via `GetFrameBuffer()` -> `CleanupGame()`.

## Ownership Map (Practical)

- Add/update gameplay state structs + shared globals:
  - start in `cybertrain_core.cpp`.
- Change route/pathing, adjacency, map projection, cluster generation:
  - `cybertrain_network_worldgen.cpp`.
- Change market pricing/events or modal business rules:
  - `cybertrain_economy_modals.cpp`.
- Change splash/help/options/audio/leaderboard UI:
  - `cybertrain_ui.cpp`.
- Change frame order, high-level input handling, reset flow:
  - `cybertrain_gameloop.cpp`.
- Change integration API to BBS/Python host:
  - `cybertrain_exports.cpp`.
- Change standalone bootstrap behavior:
  - `cybertrain_standalone_main.cpp`.

## Key Coupling Notes

- Single-translation-unit architecture intentionally allows cross-module `static` usage via include order.
- `GameLoopBody()` is the behavioral hub; most regressions surface there first.
- `RestartToSplashAfterGameOver()` is the authoritative full-state reset routine.
- Embedded and standalone flows should stay behaviorally aligned; when touching init/reset logic, verify both.
