---
name: cybertrain-expert
description: "Deep expertise on CyberTrain, the railway network simulator embedded in GlyphisIO BBS. Use this skill for: gameplay strategy and tactics, modifying game mechanics, adding new train/silo/market features, debugging economy or pathfinding, understanding the 7-system silo architecture, bureau floor bonuses, market simulation, or any CyberTrain-specific work. Trigger on keywords: CyberTrain, railway, train line, silo, bureau, platform, depot, factory, market stocks, cargo system, junction, game economy, net worth, leaderboard, year 5, bankruptcy."
---

# CyberTrain Expert Skill

CyberTrain is an isometric railway-building economic simulator set in a cyberpunk 1989. Players build rail networks connecting color-coded city clusters, establish train lines, construct industrial infrastructure, and manage a stock market - all within a 6-year (in-game) time limit. Final score = net credits at year 6.

## Source File Map

All files in `Data/games/CyberTrain/`:
| File | Lines | Purpose |
|------|-------|---------|
| `main.cpp` | ~20 | Single translation unit; `#include`s all `.cpp` in order |
| `src/cybertrain_core.cpp` | ~3370 | ALL structs, enums, globals, constants, costs |
| `src/cybertrain_economy_modals.cpp` | ~varies | Modal draw logic (station, line, junction, demolish, market) |
| `src/cybertrain_network_worldgen.cpp` | ~1614 | Cluster placement, building generation, world layout |
| `src/cybertrain_exports.cpp` | ~varies | DLL `__declspec(dllexport)` functions |
| `src/cybertrain_ui.cpp` | ~1186 | HUD, splash screen, leaderboard, options, asset loading |
| `src/cybertrain_gameloop.cpp` | ~4584 | Main loop, input, train movement, economy tick, rendering |
| `src/cybertrain_standalone_main.cpp` | ~small | Standalone `main()` entry point |

**Encoding warning:** Source files use Mojibake UTF-8 (em-dashes = `\xc3\xa2\xc2\x80\xc2\x93` bytes). Use Python scripts for edits with special characters.

## Game Architecture

### World Layout
- 40x40 grid, spacing `g_gridSpacing = 5.0f`
- Inner buildable grid: 100 units radius (`g_gridExtent`)
- Outer ring: 135 units radius (25% cost discount on placement)
- 7 city clusters placed along coasts: 1 Cargo (brown) + 6 faction colors
- Yellow forced to bottom-right corner, Red in remaining corner, others randomized
- Procedural buildings in clusters (10 per cluster, heights 5-30 units)

### The 7 Systems

| System | Color | Train Cost | Weekly Upkeep | Cluster Type |
|--------|-------|------------|---------------|--------------|
| SYS1 Cargo | Brown | 30/80/100 CR (1/2/3 trailers) | 10 CR/trailer | CARGO |
| SYS2 Green | Green | 150 CR | 25 CR | General Patriots |
| SYS3 Magenta | Magenta | 100 CR | 20 CR | AI Industrial |
| SYS4 Cyan | Cyan | 100 CR | 20 CR | AI Technology |
| SYS5 Orange | Orange | 100 CR | 20 CR | AI Administration |
| SYS6 Red | Red | 200 CR | 50 CR | Transhuman Elites |
| SYS7 Yellow | Yellow | 300 CR | 80 CR | Corporate Elite |

### Infrastructure Costs

| Structure | Build Cost | Monthly Upkeep |
|-----------|-----------|----------------|
| Track tile | 150 CR (outer: 25% discount) | 5 CR/tile |
| Station (4-tile) | 1000 CR | 100 CR |
| Depot | 1500 CR | 50 CR |
| Factory (4x4) | 10,000 CR | 200 CR |
| Bureau (per floor) | 3000-6000 CR depending on system | 20 CR/floor |

Bureau cost per floor by system: Cargo=3000, Green=3500, Magenta=4000, Cyan=5000, Orange=4500, Red=5500, Yellow=6000.

### Economy Flow
```
Factory -> Depot (cargo storage, cap 8) -> Cargo Train -> Station -> Bureau (income)
                                                                         |
                                                                    Silo activation
                                                                         |
                                                                    Market unlocks
```

Bureau income: `kBureauIncomePerFloorPerDay = 50.0f` per floor per day cycle.

### Time System
- `g_dayCycleSeconds = 20.0f` at MEDIUM speed
- Calendar: 52 weeks/year, month lengths follow 1989 layout
- Speed states: PAUSE, SLOW, MEDIUM, QUICK, QUICKEST (SPACE to cycle)
- Game ends at Year 6; Year 5 triggers warning modal

### Starting State
- `g_playerCredits = 50000`
- Speed starts at PAUSE
- No infrastructure placed

## Silo System (Core Progression Mechanic)

Silos are the key unlock mechanism. Each silo type requires specific infrastructure combinations on an **established line** (2+ connected stations).

### SYS1 (Cargo) Silo
- **Requires:** Cargo train + active factory with depot + station in cargo cluster, all on same established line
- **Unlocks:** Commodity market listings (1 per silo, max 6)
- **Bonus:** Factory double output when magenta train present on line

### SYS2 (Green) Silo
- **Requires:** Green train + green-near station + bureau linked to hub station, same line
- **Unlocks:** Green stock listings (1 per silo, max 6)
- **Bureau bonus:** +10% bullish odds per bureau floor
- **Rule:** 1:1 fairness - one qualifying bureau = one silo

### SYS3 (Magenta) Silo
- **Requires:** Magenta train + magenta-cluster station + industry station (within 2 grid of factory)
- **Unlocks:** Magenta stock listings
- **Bureau bonus:** +10% magenta + commodity share performance per floor

### SYS4 (Cyan) Silo
- **Requires:** Cyan train + cyan-cluster station + bureau on same line
- **Unlocks:** Cyan stock listings
- **Bureau bonus:** -5% running cost reduction per floor (capped 95%)

### SYS5 (Orange) Silo
- **Requires:** Orange train + orange-cluster station + bureau on same line
- **Unlocks:** Orange stock listings
- **Bureau bonus:** -10% build cost reduction per floor (capped 90%)

### SYS6 (Red) Silo
- **Requires:** Red train + red-cluster station + bureau on same line
- **Unlocks:** Red stock listings
- **Bureau bonus:** Increases red growth odds

### SYS7 (Yellow) Silo - THE KEY UNLOCK
- **Requires:** Yellow train + yellow-near station + eligible bureau on established line
- **Unlocks:** THE MARKET (first SYS7 silo enables all stock trading)
- **Market chaos:** `max(0, 50 - total_yellow_bureau_floors)` - more yellow floors = less chaos = more stable market

## Market System

Unlocked by first SYS7 (Yellow) silo. Contains 6 tabs: Commodities + 5 faction stocks.

### Listings per Tab (6 each, 36 total)
**Commodities:** CMP-SYC, CMP-QFL, CMP-NCS, CMP-PGR, CMP-DMA, CMP-ARC (base ~50 CR, vol 0.08)
**Green stocks:** SUSH, RCHN, ALSY, NCOM, ENMD, BMLG (base ~120 CR, vol 0.05)
**Magenta stocks:** RBFD, HMWK, DDSS, ATRG, EXTT, OSCP (base ~200 CR, vol 0.04)
**Cyan stocks:** NROS, QCOM, MCLB, PAIN, CLSP, BICE (base ~300 CR, vol 0.04)
**Orange stocks:** SVGD, PPRI, CPSC, HASY, PCBR, SECT (base ~250 CR, vol 0.05)
**Red stocks:** LXTN, AUGC, GNSC, MBVL, NMTR, SULB (base ~400 CR, vol 0.03)

### Price Mechanics
- Each listing: price, volatility, trend (-1/0/+1), trendDaysLeft (2-6 days)
- Price delta = drift (trend * volatility * 0.3) + noise (volatility * chaos_factor)
- Bureau floor bonus: +10% drift on bullish trends
- Chaos: 0-50, controlled by yellow bureau floors

### Market Events (random)
| Event | Effect | Duration |
|-------|--------|----------|
| Sector Boom | +15-18% price | 2-5 days |
| Sector Crash | -12-15% price | 2-4 days |
| Cargo Shortage | +10% commodities | 3 days |
| Bureau Dividend | +20-50% dividend | 1 day |

Event threshold: `12 + chaos/3`, max 3 active events.

### Market Revenue (daily)
- Commodity prices * 0.5 * stabilityFactor
- Stock prices * 0.3 * stabilityFactor
- Dividend yield: 0.02 * stabilityFactor (+ event bonuses)

## Train Pathfinding & Movement

### Path System
- Trains follow `std::vector<Vector3> path` built via BFS through connected platforms
- On established lines: trains restricted to line's platform set
- Progress tracked as float distance along path
- Open paths: train reverses at endpoints
- Loop paths: train wraps continuously

### Junction Routing
- Junctions = platforms with 3+ neighbors
- Per-train `JunctionSetting`: stores (position_key, exit_pair_index)
- Default pair = straightest (opposite exits)
- Crossing junctions (from "NO CONTINUE") don't auto-merge
- Player edits junction routing by clicking junction cross when train selected

### Train Mechanics
- Speed varies by type and game speed multiplier
- Dwell modes at stations: FLOW (no stop), SHORT_WAIT (2s), LONG_WAIT (10s)
- Collision detection: trains jam when overlapping, `jamTimer` counts duration
- Paused trains: created when their line is demolished, can be deleted via modal

### Cargo Train Specifics
- 1-3 trailers, each holds 2 cargo units
- Pick up from best depot by free space
- Drop off at stations adjacent to depots with capacity
- `lastTransferStationKey` prevents re-transfer at same station

## Controls Reference

### Keyboard
| Key | Action |
|-----|--------|
| SPACE | Cycle game speed |
| T | Track/Platform placement |
| S | Station placement |
| D | Depot placement |
| F | Factory placement |
| B | Bureau placement |
| X | Demolish mode |
| C | Stock & Commodities Market |
| M | Toggle 2D Map mode |
| H | Help modal (10 pages) |
| Arrows | Camera pan |
| Shift+Arrows | Camera rotate/altitude |
| Ctrl+Shift+=/- | Zoom in/out |
| ESC | Exit CyberTrain cam / close modals |
| O | Options (from splash) |

### Mouse
- Left click: Place structures, interact with modals, select trains
- Click+drag: Draw continuous platform lines (L-shape paths)
- Click junction cross: Edit routing (when train selected)

## Win Conditions & Scoring

- **Game length:** 6 in-game years
- **Final score:** `g_playerCredits` at Year 6 end
- **Bankruptcy:** Credits < 0 triggers grace period; failure to recover = game over (score 0)
- **Year 5 warning:** Modal warns "You have 1 more year" + lore about Quadtron replacement
- **Leaderboard:** Top 10, stored in `leaderboard.json` (line-delimited JSON: `{"username":"x","score":n}`)
- **Steam integration:** Optional upload to Steam leaderboard "CyberTrainLeaderboard"

## Optimal Strategy Guide

### Early Game (Year 1-2): Foundation
1. **Start paused.** Survey the map - find clusters near each other for efficient routing
2. **Build cargo first:** Factory + depot chain + cargo train = SYS1 silo = commodity listings
3. **Establish 2+ station lines early** - lines need 2 connected stations to be "established"
4. **Place depots adjacent to stations** - they auto-link to the nearest factory cluster
5. **Use outer ring discount** (25% off) when possible for track placement

### Mid Game (Year 2-4): Silo Activation Sprint
6. **Priority order for silos:**
   - SYS1 (Cargo) first - enables commodity income
   - SYS5 (Orange) second - build cost reduction compounds over time (-10%/floor, cap 90%)
   - SYS4 (Cyan) third - running cost reduction (-5%/floor, cap 95%)
   - SYS6 (Red) fourth - build discount stacks with Orange
   - SYS2 (Green) - solid passive income
   - SYS3 (Magenta) - factory double bonus is powerful
   - SYS7 (Yellow) LAST - unlocks market but costs most (300 CR/train, 6000 CR/bureau floor)

7. **Bureau floor strategy:**
   - Orange bureaus: stack floors early = massive build savings
   - Cyan bureaus: stack floors = running cost savings compound
   - Yellow bureaus: more floors = less market chaos = more stable/profitable market
   - Target: 50+ total yellow bureau floors to reach chaos = 0

### Late Game (Year 4-6): Market Exploitation
8. **Once market unlocks (SYS7):**
   - Buy during Sector Crash events (-12-15%)
   - Sell during Sector Boom events (+15-18%)
   - Commodities have highest volatility (0.08) = most trading opportunity
   - Red stocks have lowest volatility (0.03) but highest base price (400 CR)

9. **Maximize bureau income:** 50 CR/floor/day adds up fast with many floors
10. **Avoid bankruptcy at all costs** - even brief negative balance starts grace timer

### Advanced Tactics
- **Line crossing ("NO CONTINUE"):** Creates separate lines at crossroads, useful for dedicated routes
- **Junction routing:** Set per-train paths through complex junctions to avoid collisions
- **Dwell modes:** SHORT_WAIT (2s) at busy stations prevents jams; LONG_WAIT (10s) for cargo loading
- **Factory placement near multiple depot chains** maximizes cargo throughput
- **Magenta train on cargo line** = factory double production bonus
- **Monitor net worth** (credits + structure value) as the true score indicator

### Common Mistakes to Avoid
- Building too much track early (5 CR/tile/month upkeep adds up)
- Ignoring Orange/Cyan bureau bonuses (cost reduction is multiplicative over time)
- Placing Yellow infrastructure before other systems (most expensive, least immediate ROI)
- Not establishing lines (unestablished lines generate zero revenue)
- Over-investing in market during high chaos (chaos > 30 = very volatile/risky)
- Forgetting to set junction routing on new trains (they may loop uselessly)

## Key Data Structures (for code modifications)

### PlacedPlatform
```cpp
struct PlacedPlatform {
    Vector3 position;
    bool isStation;           // Part of 4-tile station
    int placementOrientation; // 0=+X, 1=+Z, 2=-X, 3=-Z
    int stationPart;          // 0-3 (station segment)
    bool isDepot;
    int depotCargo;           // 0-8
    int lineOwnerId;
    int placementGroupId;
    bool isJunction;
    char stationName[64];
    int stationDelayMode;     // 0=flow, 1=short(2s), 2=long(10s)
};
```

### PlacedTrain
```cpp
struct PlacedTrain {
    int id;
    TrainType type;           // Passenger/Magenta/Cyan/Orange/Red/Yellow/Cargo
    int lineId;
    int cargoTrailers;        // 1-3 (cargo only)
    int cargoTotal;           // 0..trailers*2
    Vector3 position;
    std::vector<Vector3> path;
    float pathProgress;
    float direction;          // 1.0 fwd, -1.0 back
    DwellMode dwellMode;      // FLOW/SHORT_WAIT/LONG_WAIT
    bool isJammed;
    bool isPaused;            // Line demolished
    std::vector<JunctionSetting> junctionSettings;
};
```

### Key Globals (in cybertrain_core.cpp)
```cpp
int g_playerCredits = 50000;
GameSpeedEnum g_currentGameSpeed;
std::vector<PlacedPlatform> g_placedPlatforms;
std::vector<PlacedTrain> g_placedTrains;
std::vector<Line> g_lines;
std::vector<PlacedFactory> g_placedFactories;
std::vector<PlacedBureau> g_placedBureaus;
std::vector<Silo> g_silos;
int g_siloCountBySystem[7];
bool g_marketUnlocked;
int g_marketChaos;           // 0-50
float g_dayCount;
int g_year, g_weekOfYear;
```

### Key Helper Functions
```cpp
int OuterGridCost(int baseCost, float x, float z);  // 25% discount in outer ring
int ApplyBuildDiscount(int cost);                     // Red bureau bonus
float GetBuildCostMultiplier();                       // Orange bureau bonus
float GetRunningCostMultiplier();                     // Cyan bureau bonus
long long GridCellKey(float x, float z, float gridSize);
long long MakePositionKey(float x, float z);
bool ArePlatformsAdjacent(const Vector3& a, const Vector3& b, float gridSize);
float GetPathLength(const std::vector<Vector3>& path);
PathPoint GetPathPoint(const std::vector<Vector3>& path, float distance);
```

## Rendering (for visual modifications)

### Two Render Modes
1. **3D Mode** (default): Isometric camera, full 3D buildings/trains/platforms
2. **Map Mode** (M key): 2D top-down, trains as triangles, bureaus as circles

### Visual Constants
- Platform legs: gridSize * 0.7 tall, 0.15 wide
- Factory: 4x4 footprint, 1.4 gridSize tall, 3 smoke stacks
- Bureau: 2x2 footprint, 0.3 gridSize per floor
- Train: 4 cars, each gridSize * 0.8 long
- Scanline overlay applied every frame for retro effect
- Day/night cycle: brightness varies with `g_dayCycleSeconds`

### Particle Systems
- Build particles: 50 per placement, gravity -15.0, drag 0.95
- Factory smoke: 2-4 per spawn, rise velocity 1.5-3.0, max 100 active

## Integration with BBS

### DLL API Surface (key exports)
- `InitializeGame()` / `UpdateFrame()` / `CleanupGame()` - lifecycle
- `GetFrameBuffer()` / `GetWidth()` / `GetHeight()` - pixel access
- `SetKeyState()` / `SetMouseButtonState()` / `SetInputMousePosition()` - input bridge
- `IsGameOver()` / `GetFinalScore()` / `GetLastFinalScore()` - scoring
- `SetUsername()` / `PushLeaderboardEntry()` - leaderboard
- `ShouldExit()` / `ShouldCenterMouse()` - UI control

### Python Wrapper: `sandbox media/cybertrain_embed.py`
- Loads DLL via ctypes with MinGW runtime pre-loading
- Zero-copy framebuffer via `memoryview` over ctypes buffer
- Vertical flip (OpenGL Y convention) via `pygame.transform.flip`
- Resolution presets: 0=480x320, 1=1200x800 (default), 2=720x480

### BBS Session: `CyberTrainSession` in `Data/games/registry.py`
- Desktop position: baseline (176, 209) at 2560x1440
- Aspect-fit scaling into desktop rect
- Pygame-to-Raylib key mapping (97->65 for letters, etc.)
- Mouse coordinate transformation: screen -> game space
- Steam leaderboard upload on game-over
