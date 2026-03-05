# CyberTrain Source Modules

`main.cpp` is now a thin aggregator that includes focused `.cpp` modules in original order.
This keeps runtime behavior stable while making future edits faster.

## Module Map

- `src/cybertrain_core.cpp`
  - Includes, constants, core data types, global state, helpers, rendering primitives, ticker/terminal, train/path helpers, caches.
- `src/cybertrain_economy_modals.cpp`
  - Silo recomputation, market systems, line/station/junction/demolish/stock modal drawing and actions.
- `src/cybertrain_network_worldgen.cpp`
  - Placement validation, connectivity/pathing, map drawing helpers, cluster/world generation.
- `src/cybertrain_exports.cpp`
  - DLL exports for embedded mode (`InitializeGame`, `UpdateFrame`, framebuffer + input bridge, leaderboard exports).
- `src/cybertrain_ui.cpp`
  - Asset loading/unloading, overlay UI, cursor, leaderboard file I/O + screens, splash/introduction/help flows.
- `src/cybertrain_gameloop.cpp`
  - `GameLoopBody()` frame orchestration (simulation + rendering + modal post-actions).
- `src/cybertrain_standalone_main.cpp`
  - Standalone `main()` entry point and lifecycle.

## Why this shape

- Preserves original declaration/use order.
- Keeps one translation unit (by inclusion) to avoid broad linkage regressions.
- Lets feature edits touch one module instead of a 12k-line file.
