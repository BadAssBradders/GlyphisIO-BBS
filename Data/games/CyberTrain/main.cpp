#include "raylib.h"
#include "raymath.h"
#include "rlgl.h"
#include <vector>
#include <random>
#include <algorithm>
#include <unordered_map>
#include <string>
#include <set>
#include <cstring>
#include <fstream>
#include <ctime>
#include <cstdarg>

// --- Debug file logging ---
static std::ofstream debugFile;
static bool debugFileInitialized = false;

// --- Font ---
static Font gameFont = { 0 };
static bool fontIsCustom = false;

// ══════════════════════════════════════════════════════════════════════════════
// EMBEDDED MODE SUPPORT (for BBS integration) - matches AstroMiner architecture
// ══════════════════════════════════════════════════════════════════════════════

static RenderTexture2D g_framebuffer = {0};
static bool g_framebuffer_initialized = false;
static Texture2D scanlineTx = {0};
static unsigned char* g_frame_buffer_data = NULL;
static int g_frame_buffer_size = 0;
static bool g_game_initialized = false;
static bool g_standalone_mode = true;
static bool g_exit_requested = false;
static bool g_audio_initialized = false;
static int g_renderWidth = 600;
static int g_renderHeight = 400;
#define VIRTUAL_WIDTH 1200
#define VIRTUAL_HEIGHT 800

struct InputState {
    bool keys[512];
    bool keysPressed[512];
    bool keysReleased[512];
    bool mouseButtons[8];
    bool mouseButtonsPressed[8];
    bool mouseButtonsReleased[8];
    Vector2 mousePosition;
    Vector2 mouseDelta;
    float mouseWheelMove;
} g_inputState = {0};

static char g_username[64] = "Player";
static bool g_shouldCenterMouse = false;
static int g_lastFinalScore = 0;

// Constants that don't depend on types
static const float g_moveSpeed = 2.0f;
static const float g_zoomSpeed = 2.0f;
static const float g_rotateSpeed = 1.4f;
static const float g_gridSpacing = 5.0f;
static const float g_dayCycleSeconds = 90.0f;

// Camera state (raylib types don't need forward declaration)
static Camera3D g_camera = {0};
static Camera2D g_mapCamera = {0};
static float g_cameraAltitude = 50.0f;
static float g_cameraYaw = 0.0f;
static float g_cameraRadius = 0.0f;
static Vector3 g_mouseWorldPos = {0.0f, 0.0f, 0.0f};

// Scalar game state
static int g_playerCredits = 100000;
static int g_nextLineId = 1;
static int g_selectedTrainIndex = -1;
static int g_nextTrainId = 1;
static int g_bureauFloorIndex = 0;
static int g_cargoPlacementTrailers = 1;
static float g_dayClock = 0.0f;

// Mode flags
static bool g_mapMode = false;
static bool g_trainPlacementMode = false;
static bool g_cargoTrainPlacementMode = false;
static bool g_depotPlacementMode = false;
static bool g_factoryPlacementMode = false;
static bool g_stationPlacementMode = false;
static bool g_stationHorizontal = true;
static bool g_bureauPlacementMode = false;
static bool g_demolishMode = false;

// Game speed
enum GameSpeedEnum { SPEED_PAUSE=0, SPEED_SLOW=1, SPEED_MEDIUM=2, SPEED_QUICK=3, SPEED_QUICKEST=4 };
static int g_currentGameSpeed = SPEED_MEDIUM;

// Colors
static Color g_platformColor = {0, 255, 255, 200};
static Color g_stationColor = {0, 128, 128, 200};
static Color g_pointsColor = {255, 0, 0, 200};

// Debug counters
static int g_debugPreviousComponentCount = 0;
static int g_debugCurrentComponentCount = 0;

// UI Globals
static Texture2D g_texUI = { 0 };
static Texture2D g_texCursor = { 0 };
static bool g_uiAssetsLoaded = false;
static bool g_isMouseOverUI = false; // Tracks if mouse is over UI (blocking 3D interaction)
static Rectangle g_viewfinderRect = { 135, 115, 930, 485 }; // Approximate 3D viewport area within UI.png (will need calibration)

// Forward declarations
static void LoadUIAssets();
static void UnloadUIAssets();
static void DrawUIOverlay();
static void DrawCustomCursor();

// Input helpers for embedded mode
static bool CustomIsKeyDown(int k) { return g_standalone_mode ? IsKeyDown(k) : (k>=0 && k<512 ? g_inputState.keys[k] : false); }
static bool CustomIsKeyPressed(int k) { return g_standalone_mode ? IsKeyPressed(k) : (k>=0 && k<512 ? g_inputState.keysPressed[k] : false); }
// Mouse clicks blocked by UI if not in viewfinder
static bool CustomIsMouseButtonPressed(int b) { 
    if (g_isMouseOverUI) return false;
    return g_standalone_mode ? IsMouseButtonPressed(b) : (b>=0 && b<8 ? g_inputState.mouseButtonsPressed[b] : false); 
}
static bool CustomIsMouseButtonDown(int b) { 
    if (g_isMouseOverUI) return false;
    return g_standalone_mode ? IsMouseButtonDown(b) : (b>=0 && b<8 ? g_inputState.mouseButtons[b] : false); 
}
static Vector2 CustomGetMousePosition() { return g_standalone_mode ? GetMousePosition() : g_inputState.mousePosition; }
static Vector2 CustomGetMouseDelta() { return g_standalone_mode ? GetMouseDelta() : g_inputState.mouseDelta; }
static float CustomGetMouseWheelMove() { return g_standalone_mode ? GetMouseWheelMove() : g_inputState.mouseWheelMove; }
static int CustomGetCharPressed() { return g_standalone_mode ? GetCharPressed() : 0; }

static float GetGameTimeScale() {
    switch (g_currentGameSpeed) {
        case SPEED_PAUSE: return 0.0f;
        case SPEED_SLOW: return 0.5f;
        case SPEED_MEDIUM: return 1.0f;
        case SPEED_QUICK: return 2.0f;
        case SPEED_QUICKEST: return 4.0f;
        default: return 1.0f;
    }
}
static const char* GetSpeedName() {
    switch (g_currentGameSpeed) {
        case SPEED_PAUSE: return "PAUSE";
        case SPEED_SLOW: return "SLOW";
        case SPEED_MEDIUM: return "MEDIUM";
        case SPEED_QUICK: return "QUICK";
        case SPEED_QUICKEST: return "QUICKEST";
        default: return "MEDIUM";
    }
}
static void ClearInputFrame() {
    memset(g_inputState.keysPressed, 0, sizeof(g_inputState.keysPressed));
    memset(g_inputState.mouseButtonsPressed, 0, sizeof(g_inputState.mouseButtonsPressed));
    g_inputState.mouseDelta = {0, 0};
    g_inputState.mouseWheelMove = 0;
}

// Draw scanline overlay (same as AstroMiner)
static void DrawScanlines() {
    if (scanlineTx.id > 0) {
        DrawTexturePro(scanlineTx, 
            (Rectangle){0, 0, (float)scanlineTx.width, (float)scanlineTx.height}, 
            (Rectangle){0, 0, (float)g_renderWidth, (float)g_renderHeight}, 
            (Vector2){0, 0}, 0.0f, (Color){255, 255, 255, 255});
    }
}

// NOTE: Type-dependent globals (g_buildings, g_placedPlatforms, etc.) are declared
// after the type definitions further down in the file.

static void InitDebugFile() {
    if (!debugFileInitialized) {
        debugFile.open("debug.log", std::ios::out | std::ios::trunc);
        debugFileInitialized = true;
        debugFile << "=== CyberTrain Debug Log ===\n";
        debugFile.flush();
    }
}

static void DebugLog(const char* message) {
    InitDebugFile();
    if (debugFile.is_open()) {
        debugFile << message << "\n";
        debugFile.flush(); // Auto-flush so file updates immediately
    }
    // Also log to console
    TraceLog(LOG_INFO, message);
}

static void DebugLogFormat(const char* format, ...) {
    char buffer[512];
    va_list args;
    va_start(args, format);
    vsnprintf(buffer, sizeof(buffer), format, args);
    va_end(args);
    DebugLog(buffer);
}

// --- Simple in-game clock / day-night helpers ---
static inline unsigned char ClampU8(int v) {
    if (v < 0) return 0;
    if (v > 255) return 255;
    return (unsigned char)v;
}

static inline Color LerpColor(Color a, Color b, float t) {
    t = Clamp(t, 0.0f, 1.0f);
    return (Color){
        ClampU8((int)roundf(a.r + (b.r - a.r) * t)),
        ClampU8((int)roundf(a.g + (b.g - a.g) * t)),
        ClampU8((int)roundf(a.b + (b.b - a.b) * t)),
        ClampU8((int)roundf(a.a + (b.a - a.a) * t))
    };
}

static inline Color MulColor(Color c, float mul) {
    return (Color){
        ClampU8((int)roundf((float)c.r * mul)),
        ClampU8((int)roundf((float)c.g * mul)),
        ClampU8((int)roundf((float)c.b * mul)),
        c.a
    };
}

static inline Color AddColor(Color c, Color add) {
    return (Color){
        ClampU8((int)c.r + (int)add.r),
        ClampU8((int)c.g + (int)add.g),
        ClampU8((int)c.b + (int)add.b),
        c.a
    };
}

// Building structure to represent city buildings
struct Building {
    Vector3 position;
    Vector3 size;
    Color color;
};

// Player-placed factory (4x4 footprint)
struct PlacedFactory {
    Vector3 position; // centered on grid
};

// Player-placed Bureau (1/4 factory footprint, variable height)
struct PlacedBureau {
    Vector3 position; // centered on grid
    int floors;       // Number of floors (1, 2, 3, 4, 5, 10, 15, 20, 30, 40, 50, 75, 100, 150, or 200)
};

// Placed platform structure
struct PlacedPlatform {
    Vector3 position;
    bool isStation;      // True if part of a Station-Track
    bool isHorizontal;   // Only used for stations
    int stationPart;     // 0, 1, 2, or 3 for the segments of a station

    bool isDepot = false;   // Materials-Depot (not part of rail path)
    int depotCargo = 0;     // 0..8 cargo stored
};

// Line structure - represents an official train line connecting stations
struct Line {
    int id;                          // Unique line ID
    std::string name;                // Line name
    Color color;                     // Line color
    int stationCount;                // Number of station components in this line
    std::set<long long> componentKeys; // Station component keys belonging to this line
    std::set<int> platformIndices;   // All platform indices (stations + track) that belong to this line
};

// Modal state for line establishment
enum class LineModalState {
    None,
    EstablishLine,      // Prompt to establish a new line
    AddToLine          // Prompt to add to existing line or create new
};

struct LineModalData {
    LineModalState state = LineModalState::None;
    int targetLineId = -1;           // For AddToLine: which line to potentially add to
    long long newComponentKey = 0;   // New station component key that triggered the modal
    std::vector<long long> connectedComponentKeys; // Components that would be connected
    char nameBuffer[64] = {0};       // Text input buffer for line name
    int nameCursorPos = 0;           // Cursor position in name buffer
    Color selectedColor = {0, 255, 255, 200}; // Currently selected color (default cyan)
    int colorIndex = 0;              // Index into predefined colors
    bool establishClicked = false;   // True if Establish button was clicked
    bool addToLineClicked = false;   // True if Add to Line button was clicked
    bool cancelClicked = false;      // True if Cancel/Continue button was clicked
};

// Junction setting for a specific train at a specific junction
struct JunctionSetting {
    float x, z;      // Junction position (we only need x,z since all platforms are at y=0)
    // Which connected exit *pair* to use at this junction (encoded as a pairIndex over the
    // stable clockwise-sorted exits). This makes the junction bidirectional: if exits (i,j)
    // are connected, travel from i goes to j and from j goes to i.
    //
    // pairIndex is in [0, nC2) where n is the number of exits at this junction.
    // -1 means "unset" (will fall back to a deterministic default pair).
    int exitIndex;
};

// Helper to create a position key for junction lookups
inline long long MakePositionKey(float x, float z) {
    // Round to nearest grid position and create a unique key
    int ix = (int)(x * 10.0f);
    int iz = (int)(z * 10.0f);
    return ((long long)ix << 32) | (unsigned int)iz;
}

// Placed train structure
struct PlacedTrain {
    enum class TrainType {
        Passenger,
        Cargo
    };

    int id = 0; // unique runtime id (used for station gate logic)
    TrainType type = TrainType::Passenger;
    int cargoTrailers = 1; // only used when type == Cargo
    int cargoTotal = 0; // pooled cargo across the whole train (0..cargoTrailers*2) when Cargo
    long long lastTransferStationKey = (long long)0x7fffffffffffffffLL; // last station COMPONENT key under this train (or none)
    Vector3 position;  // Current center position of the train
    std::vector<Vector3> path;  // Path of platform positions the train follows
    float pathProgress;  // Current progress along the path (0.0 to pathLength)
    float direction;   // Movement direction: 1.0 for forward, -1.0 for backward
    float pathLength;  // Total length of the path
    std::vector<JunctionSetting> junctionSettings;  // Per-junction routing preferences
    
    // Get junction setting for a specific position, returns -1 if not set
    int GetJunctionSetting(float x, float z) const {
        for (const auto& js : junctionSettings) {
            if (fabsf(js.x - x) < 0.1f && fabsf(js.z - z) < 0.1f) {
                return js.exitIndex;
            }
        }
        return -1; // No preference recorded yet
    }
    
    // Set junction setting for a specific position
    void SetJunctionSetting(float x, float z, int exitIndex) {
        for (auto& js : junctionSettings) {
            if (fabsf(js.x - x) < 0.1f && fabsf(js.z - z) < 0.1f) {
                js.exitIndex = exitIndex;
                return;
            }
        }
        // Not found, add new
        junctionSettings.push_back({ x, z, exitIndex });
    }
};

// Particle structure for build animation effects
struct BuildParticle {
    Vector3 position;
    Vector3 velocity;
    float lifetime;      // Current lifetime in seconds
    float maxLifetime;   // Total lifetime in seconds
    Color color;
    float size;
};

// ══════════════════════════════════════════════════════════════════════════════
// GLOBAL GAME STATE (Type-dependent globals - must be after type definitions)
// ══════════════════════════════════════════════════════════════════════════════

static std::vector<Building> g_buildings;
static std::vector<PlacedPlatform> g_placedPlatforms;
static std::vector<PlacedTrain> g_placedTrains;
static std::vector<PlacedFactory> g_placedFactories;
static std::vector<PlacedBureau> g_placedBureaus;
static std::vector<Line> g_lines;
static std::vector<BuildParticle> g_buildParticles;
static std::vector<long long> g_previousStationComponentKeys;
static LineModalData g_lineModal;
static const std::vector<int> g_bureauFloorOptions = {1, 2, 3, 4, 5, 10, 15, 20, 30, 40, 50, 75, 100, 150, 200};

static inline float GetTrainTotalLength(const PlacedTrain& train, float gridSize) {
    // Passenger train: 4 cars, each one grid tile
    if (train.type == PlacedTrain::TrainType::Passenger) return gridSize * 4.0f;
    // Cargo train: locomotive (1 tile) + N trailers (each 1 tile)
    int trailers = train.cargoTrailers;
    if (trailers < 1) trailers = 1;
    return gridSize * (1.0f + (float)trailers);
}

// For open (non-loop) paths, we clamp progress so the train's *front car center* can reach the path endpoints.
// This is important because the station prime hotspot is at a station tile center (often near an endpoint),
// and if we clamp by totalLen/2 the front car would stop half a tile short.
static inline void GetTrainProgressLimitsFrontCar(const PlacedTrain& train,
                                                  float gridSize,
                                                  float pathLength,
                                                  float& outMinProgress,
                                                  float& outMaxProgress) {
    const float totalTrainLength = GetTrainTotalLength(train, gridSize);
    const float halfCar = gridSize * 0.5f;

    // Margin from endpoints to keep "center" from running too far while allowing front car center to hit endpoints.
    // Equivalent: maxProgress = pathLen - (total/2 - halfCar), minProgress = (total/2 - halfCar)
    float margin = totalTrainLength * 0.5f - halfCar;
    if (margin < 0.0f) margin = 0.0f;

    outMinProgress = margin;
    outMaxProgress = pathLength - margin;
}

static inline void EnsureCargoArrays(PlacedTrain& train) {
    if (train.type != PlacedTrain::TrainType::Cargo) {
        train.cargoTotal = 0;
        train.lastTransferStationKey = (long long)0x7fffffffffffffffLL;
        return;
    }
    if (train.cargoTrailers < 1) train.cargoTrailers = 1;
    int cap = train.cargoTrailers * 2;
    train.cargoTotal = Clamp(train.cargoTotal, 0, cap);
}

// Get the total length of a path
float GetPathLength(const std::vector<Vector3>& path) {
    if (path.size() < 2) return 0.0f;
    float total = 0.0f;
    for (size_t i = 1; i < path.size(); i++) {
        total += Vector3Distance(path[i-1], path[i]);
    }
    return total;
}

static inline bool IsLoopPath(const std::vector<Vector3>& path) {
    if (path.size() < 3) return false;
    return Vector3Distance(path.front(), path.back()) < 0.1f;
}

static inline float WrapDistance(float d, float len) {
    if (len <= 0.0f) return 0.0f;
    float r = fmodf(d, len);
    if (r < 0.0f) r += len;
    return r;
}

static float GetClosestDistanceAlongPath(const std::vector<Vector3>& path, Vector3 point) {
    if (path.size() < 2) return 0.0f;

    float bestDistSq = 1e30f;
    float bestAlong = 0.0f;
    float accumulated = 0.0f;

    for (size_t i = 1; i < path.size(); i++) {
        Vector3 a = path[i - 1];
        Vector3 b = path[i];
        Vector3 ab = Vector3Subtract(b, a);
        float abLenSq = Vector3DotProduct(ab, ab);
        if (abLenSq < 1e-6f) continue;

        float t = Vector3DotProduct(Vector3Subtract(point, a), ab) / abLenSq;
        t = Clamp(t, 0.0f, 1.0f);
        Vector3 proj = Vector3Add(a, Vector3Scale(ab, t));

        Vector3 diff = Vector3Subtract(point, proj);
        float dSq = Vector3DotProduct(diff, diff);
        if (dSq < bestDistSq) {
            bestDistSq = dSq;
            bestAlong = accumulated + sqrtf(abLenSq) * t;
        }

        accumulated += sqrtf(abLenSq);
    }

    return bestAlong;
}

// Get position and direction at a specific distance along a path
struct PathPoint {
    Vector3 position;
    Vector3 direction;
};

PathPoint GetPathPoint(const std::vector<Vector3>& path, float distance) {
    if (path.empty()) return { {0,0,0}, {1,0,0} };
    if (path.size() == 1) return { path[0], {1,0,0} };
    
    // Clamp distance to path range
    float totalLen = GetPathLength(path);
    if (distance <= 0.0f) {
        Vector3 dir = Vector3Normalize(Vector3Subtract(path[1], path[0]));
        return { path[0], dir };
    }
    if (distance >= totalLen) {
        Vector3 dir = Vector3Normalize(Vector3Subtract(path.back(), path[path.size()-2]));
        return { path.back(), dir };
    }
    
    float currentDist = 0.0f;
    for (size_t i = 1; i < path.size(); i++) {
        float segmentLength = Vector3Distance(path[i-1], path[i]);
        if (currentDist + segmentLength >= distance) {
            float t = (distance - currentDist) / segmentLength;
            Vector3 pos = Vector3Lerp(path[i-1], path[i], t);
            Vector3 dir = Vector3Normalize(Vector3Subtract(path[i], path[i-1]));
            return { pos, dir };
        }
        currentDist += segmentLength;
    }
    
    Vector3 dir = Vector3Normalize(Vector3Subtract(path.back(), path[path.size()-2]));
    return { path.back(), dir };
}

// "Hotspot" point used for hit-testing/selection and other single-point interactions.
// All trains: hotspot is the FRONT car (front-most segment along the path direction).
static inline PathPoint GetTrainHotspotPoint(const PlacedTrain& train, float gridSize) {
    if (train.path.size() < 2) {
        return { train.position, (Vector3){ 1.0f, 0.0f, 0.0f } };
    }

    // Front-most car center = centerProgress + totalLen/2 - halfCar
    const float totalLen = GetTrainTotalLength(train, gridSize);
    float dist = train.pathProgress + totalLen * 0.5f - gridSize * 0.5f;

    float pathLen = train.pathLength;
    if (pathLen <= 0.0f) pathLen = GetPathLength(train.path);
    bool isLoop = IsLoopPath(train.path);

    if (isLoop) dist = WrapDistance(dist, pathLen);
    else dist = Clamp(dist, 0.0f, pathLen);

    return GetPathPoint(train.path, dist);
}

// Draw a rotated cube using a center position and a direction vector
void DrawRotatedCube(Vector3 position, Vector3 direction, float l, float h, float w, Color color) {
    // Calculate rotation angle around Y axis based on direction
    float angle = atan2f(direction.x, direction.z) * RAD2DEG;
    
    rlPushMatrix();
        rlTranslatef(position.x, position.y, position.z);
        rlRotatef(angle, 0, 1, 0);
        DrawCube({0,0,0}, w, h, l, color); // width is X, height is Y, length is Z in rotated space
    rlPopMatrix();
}

// Draw a platform/table shape within a grid square
// 4 legs and a flat top
void DrawPlatform(Vector3 position, float gridSize, Color color) {
    // Platform dimensions to fit within grid square (5x5x5)
    float legWidth = gridSize * 0.15f;  // Leg thickness
    float legHeight = gridSize * 0.7f;  // Leg height
    float topThickness = gridSize * 0.1f; // Top thickness
    float topSize = gridSize;            // Top size (100% of grid square)
    float legOffset = gridSize * 0.25f; // Distance from center for legs
    
    float legBaseY = position.y;
    float legTopY = position.y + legHeight;
    // Top should sit on top of the legs, so its bottom is at legTopY
    // Since DrawCube uses center position, center is at legTopY + topThickness/2
    float topY = legTopY + topThickness / 2.0f;
    
    // Draw 4 legs (rectangular cubes)
    // Front-left leg
    DrawCube(
        (Vector3){position.x - legOffset, legBaseY + legHeight / 2.0f, position.z + legOffset},
        legWidth, legHeight, legWidth,
        color
    );
    
    // Front-right leg
    DrawCube(
        (Vector3){position.x + legOffset, legBaseY + legHeight / 2.0f, position.z + legOffset},
        legWidth, legHeight, legWidth,
        color
    );
    
    // Back-left leg
    DrawCube(
        (Vector3){position.x - legOffset, legBaseY + legHeight / 2.0f, position.z - legOffset},
        legWidth, legHeight, legWidth,
        color
    );
    
    // Back-right leg
    DrawCube(
        (Vector3){position.x + legOffset, legBaseY + legHeight / 2.0f, position.z - legOffset},
        legWidth, legHeight, legWidth,
        color
    );
    
    // Draw top/seat (flat cube)
    DrawCube(
        (Vector3){position.x, topY, position.z},
        topSize, topThickness, topSize,
        color
    );
}

// Materials-Depot: same footprint as a platform but 50% shorter (legs + top thickness halved)
void DrawMaterialsDepot(Vector3 position, float gridSize, Color color, int cargoCount) {
    float legWidth = gridSize * 0.15f;
    float legHeight = gridSize * 0.35f;     // 50% of normal (0.7)
    float topThickness = gridSize * 0.05f;  // 50% of normal (0.1)
    float topSize = gridSize;
    float legOffset = gridSize * 0.25f;

    float legBaseY = position.y;
    float topY = legBaseY + legHeight + topThickness / 2.0f;

    // Legs
    DrawCube((Vector3){position.x - legOffset, legBaseY + legHeight / 2.0f, position.z + legOffset}, legWidth, legHeight, legWidth, color);
    DrawCube((Vector3){position.x + legOffset, legBaseY + legHeight / 2.0f, position.z + legOffset}, legWidth, legHeight, legWidth, color);
    DrawCube((Vector3){position.x - legOffset, legBaseY + legHeight / 2.0f, position.z - legOffset}, legWidth, legHeight, legWidth, color);
    DrawCube((Vector3){position.x + legOffset, legBaseY + legHeight / 2.0f, position.z - legOffset}, legWidth, legHeight, legWidth, color);

    // Top
    DrawCube((Vector3){position.x, topY, position.z}, topSize, topThickness, topSize, color);

    // Cargo visualization (0..8 small white blocks on top)
    cargoCount = Clamp(cargoCount, 0, 8);
    if (cargoCount > 0) {
        float blockSize = gridSize * 0.22f;
        float blockY = topY + topThickness / 2.0f + blockSize / 2.0f + 0.02f;
        Color cargoColor = (Color){ 245, 245, 245, 235 };

        // Arrange as a 4x2 grid on the depot top
        float step = gridSize * 0.18f;
        for (int i = 0; i < cargoCount; i++) {
            int col = i % 4;
            int row = i / 4; // 0..1
            float ox = (col - 1.5f) * step;
            float oz = (row == 0 ? -0.5f : 0.5f) * step;
            DrawCube((Vector3){ position.x + ox, blockY, position.z + oz }, blockSize, blockSize, blockSize, cargoColor);
        }
    }
}

// Factory: 4x4 footprint base with 3 roof stacks, one with a slanted roof slice
void DrawFactory(Vector3 center, float gridSize, Color color) {
    float baseW = gridSize * 4.0f;
    float baseD = gridSize * 4.0f;
    float baseH = gridSize * 1.4f;

    Vector3 baseCenter = { center.x, center.y + baseH / 2.0f, center.z };
    // Keep consistent "material" properties across base/roof/chimneys (same alpha treatment)
    Color baseColor = color;
    baseColor.a = (unsigned char)Clamp((int)baseColor.a, 0, 255);
    baseColor.a = (unsigned char)((float)baseColor.a * 0.55f);
    DrawCube(baseCenter, baseW, baseH, baseD, baseColor);

    // Slight darker roof cap
    Color roofColor = { (unsigned char)(color.r * 0.85f), (unsigned char)(color.g * 0.85f), (unsigned char)(color.b * 0.85f), baseColor.a };
    float roofH = gridSize * 0.25f;
    Vector3 roofCenter = { center.x, center.y + baseH + roofH / 2.0f, center.z };
    DrawCube(roofCenter, baseW * 0.96f, roofH, baseD * 0.96f, roofColor);

    // Three stacks on the roof (smaller rectangles)
    float stackW = gridSize * 0.9f;
    float stackD = gridSize * 0.9f;
    float stackH1 = gridSize * 1.0f;
    float stackH2 = gridSize * 1.2f;
    float stackH3 = gridSize * 0.8f;

    float roofY = center.y + baseH + roofH;

    Vector3 s1 = { center.x - gridSize * 1.2f, roofY + stackH1 / 2.0f, center.z - gridSize * 1.0f };
    Vector3 s2 = { center.x + gridSize * 1.2f, roofY + stackH2 / 2.0f, center.z - gridSize * 0.6f };
    Vector3 s3 = { center.x,               roofY + stackH3 / 2.0f, center.z + gridSize * 1.0f };

    DrawCube(s1, stackW, stackH1, stackD, roofColor);
    DrawCube(s2, stackW, stackH2, stackD, roofColor);
    DrawCube(s3, stackW, stackH3, stackD, roofColor);

    // Slanted roof slice on stack #2 (a simple wedge made from 2 triangles)
    // We'll render a sloped "cap" by drawing two triangles on the top face area.
    float capH = gridSize * 0.35f;
    float halfW = stackW / 2.0f;
    float halfD = stackD / 2.0f;

    Vector3 capBase = { s2.x, roofY + stackH2, s2.z };
    Vector3 a = { capBase.x - halfW, capBase.y,             capBase.z - halfD };
    Vector3 b = { capBase.x + halfW, capBase.y,             capBase.z - halfD };
    Vector3 c = { capBase.x + halfW, capBase.y,             capBase.z + halfD };
    Vector3 d = { capBase.x - halfW, capBase.y,             capBase.z + halfD };
    // Raise one side to create the slice/angle (towards +Z)
    Vector3 c2 = { c.x, c.y + capH, c.z };
    Vector3 d2 = { d.x, d.y + capH, d.z };

    DrawTriangle3D(a, b, c2, roofColor);
    DrawTriangle3D(a, c2, d2, roofColor);
    DrawTriangle3D(a, d2, d, roofColor); // side fill
    DrawTriangle3D(a, c, c2, roofColor); // small fill
}

// Bureau: 1/4 factory footprint (2x2), cyan, 80% transparent, variable height
void DrawBureau(Vector3 center, float gridSize, int floors, Color color) {
    // Factory footprint is 4x4, so Bureau is 2x2 (1/4 size)
    float bureauW = gridSize * 2.0f;
    float bureauD = gridSize * 2.0f;
    // Each floor is approximately gridSize * 0.3f in height
    float floorHeight = gridSize * 0.3f;
    float totalHeight = floorHeight * (float)floors;
    
    Vector3 bureauCenter = { center.x, center.y + totalHeight / 2.0f, center.z };
    // Use color exactly as passed (matches platform rendering behavior)
    DrawCube(bureauCenter, bureauW, totalHeight, bureauD, color);
}

// Particle system functions for build animations
// NOTE: g_buildParticles is declared above with other globals
static std::mt19937 particleRNG((unsigned int)time(nullptr));

#ifndef PI
#define PI 3.14159265358979323846f
#endif

// Spawn particles bursting from a build location
void SpawnBuildParticles(Vector3 position, Color baseColor, float gridSize) {
    const int particleCount = 400; // Several hundred particles
    const float burstSpeed = 8.0f; // Initial burst speed
    const float lifetime = 2.0f; // Particles live for 2 seconds
    const float particleSize = gridSize * 0.08f; // Small cubes
    
    std::uniform_real_distribution<float> angleDist(0.0f, 2.0f * PI);
    std::uniform_real_distribution<float> elevationDist(-PI / 3.0f, PI / 2.0f); // -60 to 90 degrees (mostly upward)
    std::uniform_real_distribution<float> speedDist(burstSpeed * 0.5f, burstSpeed * 1.5f);
    std::uniform_real_distribution<float> lifetimeDist(lifetime * 0.8f, lifetime * 1.2f);
    
    // Vary color slightly for visual interest
    std::uniform_int_distribution<int> colorOffset(-30, 30);
    
    for (int i = 0; i < particleCount; i++) {
        BuildParticle particle;
        particle.position = position;
        particle.position.y = 0.0f; // Start at y=0
        
        // Random direction in all directions (sphere distribution)
        float azimuth = angleDist(particleRNG); // Horizontal angle
        float elevation = elevationDist(particleRNG); // Vertical angle (biased upward)
        
        float speed = speedDist(particleRNG);
        particle.velocity.x = speed * cosf(elevation) * sinf(azimuth);
        particle.velocity.y = speed * sinf(elevation); // Upward bias
        particle.velocity.z = speed * cosf(elevation) * cosf(azimuth);
        
        particle.maxLifetime = lifetimeDist(particleRNG);
        particle.lifetime = 0.0f;
        particle.size = particleSize;
        
        // Color variation
        int rOffset = colorOffset(particleRNG);
        int gOffset = colorOffset(particleRNG);
        int bOffset = colorOffset(particleRNG);
        particle.color = (Color){
            ClampU8((int)baseColor.r + rOffset),
            ClampU8((int)baseColor.g + gOffset),
            ClampU8((int)baseColor.b + bOffset),
            baseColor.a
        };
        
        g_buildParticles.push_back(particle);
    }
}

// Update particles (move and age them)
void UpdateBuildParticles(float deltaTime) {
    const float gravity = -15.0f; // Gravity pulling particles down
    
    for (size_t i = 0; i < g_buildParticles.size(); ) {
        BuildParticle& p = g_buildParticles[i];
        
        // Update lifetime
        p.lifetime += deltaTime;
        
        // Update position with velocity
        p.position.x += p.velocity.x * deltaTime;
        p.position.y += p.velocity.y * deltaTime;
        p.position.z += p.velocity.z * deltaTime;
        
        // Apply gravity
        p.velocity.y += gravity * deltaTime;
        
        // Apply air resistance
        const float drag = 0.95f;
        p.velocity.x *= drag;
        p.velocity.y *= drag;
        p.velocity.z *= drag;
        
        // Remove dead particles
        if (p.lifetime >= p.maxLifetime || p.position.y < -5.0f) {
            // Swap with last and pop (efficient removal)
            g_buildParticles[i] = g_buildParticles.back();
            g_buildParticles.pop_back();
        } else {
            i++;
        }
    }
}

// Render particles as small cubes
void RenderBuildParticles() {
    for (const auto& p : g_buildParticles) {
        // Fade out as particle ages
        float lifeRatio = 1.0f - (p.lifetime / p.maxLifetime);
        Color renderColor = p.color;
        renderColor.a = (unsigned char)((float)renderColor.a * lifeRatio);
        
        // Draw small cube
        DrawCube(p.position, p.size, p.size, p.size, renderColor);
    }
}

// Get the Y position of the platform top surface (center of top)
float GetPlatformTopY(float baseY, float gridSize) {
    float legHeight = gridSize * 0.7f;
    float topThickness = gridSize * 0.1f;
    return baseY + legHeight + topThickness / 2.0f;
}

// Draw a monorail car with beveled front/back faces
void DrawMonorailCar(Vector3 pos, Vector3 dir, float l, float h, float w, bool isFront, bool isBack, Color color) {
    float hw = w / 2.0f;
    float hh = h / 2.0f;
    float hl = l / 2.0f;
    
    // Calculate rotation angle around Y axis based on direction
    float angle = atan2f(dir.x, dir.z) * RAD2DEG;
    
    rlPushMatrix();
    rlTranslatef(pos.x, pos.y, pos.z);
    rlRotatef(angle, 0, 1, 0);
    
    // In this rotated space:
    // Z is forward (along direction)
    // X is right
    // Y is up
    
    Vector3 v[8];
    float frontTaper = isFront ? 0.3f : 0.0f;
    float backTaper = isBack ? 0.3f : 0.0f;
    float frontRoofTaper = isFront ? 0.4f : 0.0f;
    float backRoofTaper = isBack ? 0.2f : 0.0f;

    // Bottom face vertices (Y = -hh) - No taper for square snapping
    v[0] = { -hw, -hh, -hl }; // Back-left-bottom
    v[1] = {  hw, -hh, -hl }; // Back-right-bottom
    v[2] = {  hw, -hh,  hl }; // Front-right-bottom
    v[3] = { -hw, -hh,  hl }; // Front-left-bottom
    
    // Top face vertices (Y = +hh, but with roof taper)
    v[4] = { -hw,  hh - backRoofTaper * hh, -hl + backTaper * hl }; // Back-left-top
    v[5] = {  hw,  hh - backRoofTaper * hh, -hl + backTaper * hl }; // Back-right-top
    v[6] = {  hw,  hh - frontRoofTaper * hh,  hl - frontTaper * hl }; // Front-right-top
    v[7] = { -hw,  hh - frontRoofTaper * hh,  hl - frontTaper * hl }; // Front-left-top

    // Draw triangles with CCW winding (front-facing from outside)
    
    // Bottom face (looking from below)
    DrawTriangle3D(v[0], v[1], v[2], color);
    DrawTriangle3D(v[0], v[2], v[3], color);
    
    // Top face (looking from above)
    DrawTriangle3D(v[4], v[6], v[5], color);
    DrawTriangle3D(v[4], v[7], v[6], color);
    
    // Front face
    DrawTriangle3D(v[3], v[2], v[6], color);
    DrawTriangle3D(v[3], v[6], v[7], color);
    
    // Back face
    DrawTriangle3D(v[1], v[0], v[4], color);
    DrawTriangle3D(v[1], v[4], v[5], color);
    
    // Left face
    DrawTriangle3D(v[0], v[3], v[7], color);
    DrawTriangle3D(v[0], v[7], v[4], color);
    
    // Right face
    DrawTriangle3D(v[1], v[5], v[6], color);
    DrawTriangle3D(v[1], v[6], v[2], color);
    
    rlPopMatrix();
}

// Draw a green monorail train based on exact 19.75 unit specifications
void DrawTrain(const std::vector<Vector3>& path, float progress, float gridSize, float brightnessMul = 1.0f) {
    if (path.size() < 2) return;
    
    Color trainColor = MulColor({ 0, 255, 0, 204 }, brightnessMul); // Green with 80% opacity, brightness adjusted
    
    // Specifications from documentation - adjusted for square snapping (scaled down 20%)
    const float trainScale = 0.8f;        // 20% smaller trains
    const float carL = gridSize * trainScale;          // 4.00 units
    const float carW = gridSize * trainScale;          // 4.00 units
    const float carH = gridSize * 0.60f * trainScale;  // 2.40 units
    
    const float connL = 0.0f;                          // No gap for perfect snapping
    const float connW = gridSize * 0.5f * trainScale;  // 2.00 units
    const float connH = gridSize * 0.4f * trainScale;  // 1.60 units

    // Calculate Y positions relative to platform top
    // The path points already contain the correct Y for the platform top center
    // We need to raise the car center so its bottom sits on the platform surface
    float topThickness = gridSize * 0.1f;
    float yOffset = (topThickness / 2.0f) + (carH / 2.0f);
    float connYOffset = (topThickness / 2.0f) + (connH / 2.0f);

    float totalLength = (carL * 4.0f) + (connL * 3.0f); // 20.0 units
    float startOffset = -totalLength / 2.0f + carL / 2.0f;
    float pathLen = GetPathLength(path);
    bool isLoop = IsLoopPath(path);

    for (int i = 0; i < 4; i++) {
        float carDist = progress + startOffset + i * (carL + connL);
        if (isLoop) carDist = WrapDistance(carDist, pathLen);
        else carDist = Clamp(carDist, 0.0f, pathLen);
        PathPoint carPoint = GetPathPoint(path, carDist);
        
        // Adjust Y to sit on platform surface
        carPoint.position.y += yOffset;
        
        bool isFront = (i == 3);
        bool isBack = (i == 0);
        DrawMonorailCar(carPoint.position, carPoint.direction, carL, carH, carW, isFront, isBack, trainColor);
        
        // Draw Connection Piece (Recessed)
        if (i < 3) {
            float connDist = carDist + (carL / 2.0f) + (connL / 2.0f);
            if (isLoop) connDist = WrapDistance(connDist, pathLen);
            else connDist = Clamp(connDist, 0.0f, pathLen);
            PathPoint connPoint = GetPathPoint(path, connDist);
            connPoint.position.y += connYOffset;
            
            DrawRotatedCube(connPoint.position, connPoint.direction, connL, connH, connW, trainColor);
        }
    }
}

// Cargo train: locomotive shaped like the passenger train's front car, plus N dark-grey trailers each carrying cargo
void DrawCargoTrain(const std::vector<Vector3>& path, float progress, float gridSize, int trailers, int cargoTotal = -1, float brightnessMul = 1.0f) {
    if (path.size() < 2) return;

    Color locoColor = MulColor({ 0, 255, 0, 204 }, brightnessMul);          // same green as standard train, brightness adjusted
    Color trailerColor = MulColor({ 40, 40, 40, 220 }, brightnessMul);      // dark grey trailer, brightness adjusted
    Color cargoColor = MulColor({ 245, 245, 245, 235 }, brightnessMul);     // white blocks, brightness adjusted

    const float trainScale = 0.8f;                 // 20% smaller trains
    const float carL = gridSize * trainScale;
    const float carW = gridSize * trainScale;
    const float carH = gridSize * 0.60f * trainScale;
    const float topThickness = gridSize * 0.1f;

    float yOffset = (topThickness / 2.0f) + (carH / 2.0f);

    float pathLen = GetPathLength(path);
    bool isLoop = IsLoopPath(path);

    if (trailers < 1) trailers = 1;

    // Locomotive (front) + N trailers (back)
    float totalLength = carL * (1.0f + (float)trailers);
    float startOffset = -totalLength / 2.0f + carL / 2.0f;

    // Locomotive (front)
    float locoDist = progress + startOffset + carL * (float)trailers; // loco is at the "front-most" segment
    if (isLoop) locoDist = WrapDistance(locoDist, pathLen);
    else locoDist = Clamp(locoDist, 0.0f, pathLen);
    PathPoint locoPoint = GetPathPoint(path, locoDist);
    locoPoint.position.y += yOffset;
    DrawMonorailCar(locoPoint.position, locoPoint.direction, carL, carH, carW, true, false, locoColor);

    // Trailers (back to front)
    for (int k = 0; k < trailers; k++) {
        float trailerDist = progress + startOffset + carL * (float)k;
        if (isLoop) trailerDist = WrapDistance(trailerDist, pathLen);
        else trailerDist = Clamp(trailerDist, 0.0f, pathLen);
        PathPoint trailerPoint = GetPathPoint(path, trailerDist);
        trailerPoint.position.y += yOffset;

        // Slightly shorter trailer body for visual separation
        DrawRotatedCube(trailerPoint.position, trailerPoint.direction, carL * 0.95f, carH * 0.75f, carW * 0.95f, trailerColor);

        // Cargo blocks: up to 2 cubes on top of the trailer (matches capacity)
        Vector3 f = trailerPoint.direction;
        f.y = 0.0f;
        f = Vector3Normalize(f);
        Vector3 r = { -f.z, 0.0f, f.x };

        int cargoUnits = 2;
        if (cargoTotal >= 0) {
            // Distribute pooled cargo across trailers (back to front) in chunks of 2
            int remaining = cargoTotal - (k * 2);
            cargoUnits = Clamp(remaining, 0, 2);
        }

        float blockSize = gridSize * 0.28f * trainScale;
        float blockY = trailerPoint.position.y + (carH * 0.75f) / 2.0f + blockSize / 2.0f + 0.05f;

        for (int i = 0; i < cargoUnits; i++) {
            // Spread them across the trailer width
            float t = (i == 0) ? -gridSize * 0.144f : gridSize * 0.144f;
            Vector3 blockPos = {
                trailerPoint.position.x + r.x * t,
                blockY,
                trailerPoint.position.z + r.z * t
            };
            DrawCube(blockPos, blockSize, blockSize, blockSize, cargoColor);
        }
    }
}

// Check if two platforms are adjacent (connected)
bool ArePlatformsAdjacent(const Vector3& a, const Vector3& b, float gridSize) {
    float dist = Vector3Distance(a, b);
    return dist < gridSize * 1.1f; // Allow small tolerance
}

static inline const PlacedPlatform* FindPlatformAtPos(const Vector3& position, const std::vector<PlacedPlatform>& platforms) {
    for (const auto& p : platforms) {
        if (Vector3Distance(position, p.position) < 0.1f) return &p;
    }
    return nullptr;
}

static inline bool IsRailPlatform(const PlacedPlatform& p) {
    // Stations are rail. Depots are NOT rail.
    return !p.isDepot;
}

// Build connected station components ("one station" = multi-tile Station-Track component)
// Outputs per-platform component id (-1 if not station), per-component key (min tile key), and member indices.
static void BuildStationComponents(const std::vector<PlacedPlatform>& platforms,
                                  float gridSize,
                                  std::vector<int>& outCompId,
                                  std::vector<long long>& outCompKey,
                                  std::vector<std::vector<int>>& outMembers) {
    outCompId.assign(platforms.size(), -1);
    outCompKey.clear();
    outMembers.clear();

    int stationTileCount = 0;
    int trackCount = 0;
    for (const auto& p : platforms) {
        if (p.isDepot) continue;
        if (p.isStation) stationTileCount++;
        else trackCount++;
    }
    DebugLogFormat("DEBUG BuildStationComponents: %d station tiles, %d track tiles, %d total platforms", 
                   stationTileCount, trackCount, (int)platforms.size());

    // First pass: Group all platforms (stations and track) into connected components
    // This will naturally group the 4 tiles of each station together since they're adjacent
    std::vector<char> visited(platforms.size(), 0);
    
    for (int i = 0; i < (int)platforms.size(); i++) {
        if (platforms[i].isDepot) continue; // Skip depots
        if (visited[i]) continue; // Already processed
        
        // Start a new component from this platform (station or track)
        int compId = (int)outMembers.size();
        outMembers.push_back({});
        long long bestKey = (long long)0x7fffffffffffffffLL;
        
        // BFS to find all connected platforms (stations and track)
        std::vector<int> q;
        q.push_back(i);
        visited[i] = 1;
        
        int stationsInComponent = 0;
        int trackInComponent = 0;

        while (!q.empty()) {
            int cur = q.back();
            q.pop_back();
            
            // Track which platforms are in this component
            if (platforms[cur].isStation) {
                outCompId[cur] = compId;
                outMembers[compId].push_back(cur);
                stationsInComponent++;
                long long k = MakePositionKey(platforms[cur].position.x, platforms[cur].position.z);
                if (k < bestKey) bestKey = k;
            } else {
                // Track tile - part of the component, assign component ID so we can draw line blocks
                outCompId[cur] = compId;
                trackInComponent++;
            }

            // Find all adjacent platforms (stations or track, but not depots)
            for (int j = 0; j < (int)platforms.size(); j++) {
                if (visited[j]) continue;
                if (platforms[j].isDepot) continue; // Skip depots
                // Check if adjacent (both stations and track can be adjacent)
                float dist = Vector3Distance(platforms[cur].position, platforms[j].position);
                bool isAdjacent = ArePlatformsAdjacent(platforms[cur].position, platforms[j].position, gridSize);
                if (isAdjacent) {
                    visited[j] = 1;
                    q.push_back(j);
                    if (platforms[cur].isStation && platforms[j].isStation) {
                        DebugLogFormat("DEBUG: Station tile %d (part %d) adjacent to station tile %d (part %d), dist=%.2f", 
                                       cur, platforms[cur].stationPart, j, platforms[j].stationPart, dist);
                    }
                }
            }
        }

        // Only create a component key if this component has at least one station
        if (stationsInComponent > 0) {
            DebugLogFormat("DEBUG: Component %d has %d station tiles, %d track tiles", 
                           compId, stationsInComponent, trackInComponent);
            outCompKey.push_back(bestKey);
        } else {
            // Pure track component (no stations) - remove it
            outMembers.pop_back();
            DebugLogFormat("DEBUG: Removed pure track component (no stations)");
        }
    }
    
    DebugLogFormat("DEBUG: Built %d station components (each station's 4 tiles = 1 component)", (int)outCompKey.size());
}

static std::vector<int> GetDepotClusterIndices(const std::vector<PlacedPlatform>& platforms, int startIdx, float gridSize) {
    std::vector<int> out;
    if (startIdx < 0 || startIdx >= (int)platforms.size()) return out;
    if (!platforms[startIdx].isDepot) return out;

    // Depot cluster rule: depots are pooled if they are physically connected (adjacent depot-to-depot chain).
    // Placement rules ensure these clusters are only extendable if the cluster has at least one depot
    // adjacent to a station tile.
    std::vector<char> visited(platforms.size(), 0);
    std::vector<int> q;
    q.push_back(startIdx);
    visited[startIdx] = 1;

    while (!q.empty()) {
        int cur = q.back();
        q.pop_back();
        out.push_back(cur);

        for (int otherDepot = 0; otherDepot < (int)platforms.size(); otherDepot++) {
            if (visited[otherDepot]) continue;
            if (!platforms[otherDepot].isDepot) continue;
            if (!ArePlatformsAdjacent(platforms[cur].position, platforms[otherDepot].position, gridSize)) continue;
            visited[otherDepot] = 1;
            q.push_back(otherDepot);
        }
    }

    return out;
}

static int GetClusterCargoTotal(const std::vector<PlacedPlatform>& platforms, const std::vector<int>& cluster) {
    int total = 0;
    for (int idx : cluster) total += platforms[idx].depotCargo;
    return total;
}

static int GetClusterCapacityTotal(const std::vector<int>& cluster) {
    const int kDepotCapacity = 8;
    return (int)cluster.size() * kDepotCapacity;
}

static void AddCargoToCluster(std::vector<PlacedPlatform>& platforms, const std::vector<int>& cluster, int amount) {
    const int kDepotCapacity = 8;
    if (amount <= 0) return;

    // Fill least-full depots first for stable visuals
    std::vector<int> order = cluster;
    std::sort(order.begin(), order.end(), [&](int a, int b) { return platforms[a].depotCargo < platforms[b].depotCargo; });

    for (int idx : order) {
        while (amount > 0 && platforms[idx].depotCargo < kDepotCapacity) {
            platforms[idx].depotCargo++;
            amount--;
        }
        if (amount == 0) break;
    }
}

static int RemoveCargoFromCluster(std::vector<PlacedPlatform>& platforms, const std::vector<int>& cluster, int amount) {
    if (amount <= 0) return 0;

    // Take from most-full depots first
    std::vector<int> order = cluster;
    std::sort(order.begin(), order.end(), [&](int a, int b) { return platforms[a].depotCargo > platforms[b].depotCargo; });

    int removed = 0;
    for (int idx : order) {
        while (amount > 0 && platforms[idx].depotCargo > 0) {
            platforms[idx].depotCargo--;
            amount--;
            removed++;
        }
        if (amount == 0) break;
    }
    return removed;
}

static bool HasAdjacentStation(const Vector3& pos, const std::vector<PlacedPlatform>& platforms, float gridSize) {
    for (const auto& p : platforms) {
        if (p.isDepot) continue;
        if (!p.isStation) continue;
        if (ArePlatformsAdjacent(pos, p.position, gridSize)) return true;
    }
    return false;
}

static bool DepotClusterHasStationConnection(const std::vector<PlacedPlatform>& platforms, const std::vector<int>& cluster, float gridSize) {
    for (int idx : cluster) {
        if (idx < 0 || idx >= (int)platforms.size()) continue;
        if (!platforms[idx].isDepot) continue;
        if (HasAdjacentStation(platforms[idx].position, platforms, gridSize)) return true;
    }
    return false;
}

// Line management helper functions

// Get predefined color palette for lines
static std::vector<Color> GetLineColorPalette() {
    return {
        {0, 255, 255, 200},    // Cyan (default)
        {255, 100, 100, 200},  // Red
        {100, 255, 100, 200},  // Green
        {255, 255, 100, 200},  // Yellow
        {255, 100, 255, 200},  // Magenta
        {100, 100, 255, 200},  // Blue
        {255, 200, 100, 200},  // Orange
        {100, 255, 255, 200},  // Light Cyan
        {200, 100, 255, 200},  // Purple
        {255, 255, 255, 200}   // White
    };
}

// Find which line (if any) a station component belongs to
static int GetLineIdForComponent(long long componentKey, const std::vector<Line>& lines) {
    for (const auto& line : lines) {
        if (line.componentKeys.find(componentKey) != line.componentKeys.end()) {
            return line.id;
        }
    }
    return -1;
}

// Count station components in a set of component keys
static int CountStationComponents(const std::set<long long>& componentKeys) {
    return (int)componentKeys.size();
}

// Draw modal UI for line establishment
static void DrawLineModal(LineModalData& modal, const std::vector<Line>& lines, int screenWidth, int screenHeight) {
    if (modal.state == LineModalState::None) return;
    
    // Draw semi-transparent background
    DrawRectangle(0, 0, screenWidth, screenHeight, (Color){0, 0, 0, 200});
    
    float modalWidth = 500.0f;
    float modalHeight = 400.0f;
    float modalX = (screenWidth - modalWidth) / 2.0f;
    float modalY = (screenHeight - modalHeight) / 2.0f;
    
    // Draw modal background
    DrawRectangle((int)modalX, (int)modalY, (int)modalWidth, (int)modalHeight, (Color){40, 40, 40, 255});
    DrawRectangleLines((int)modalX, (int)modalY, (int)modalWidth, (int)modalHeight, WHITE);
    
    float yPos = modalY + 20.0f;
    
    if (modal.state == LineModalState::EstablishLine) {
        DrawTextEx(gameFont, "Establish New Line?", (Vector2){(float)(modalX + 20), yPos}, 24, 0.0f, WHITE);
        yPos += 50.0f;
        
        DrawTextEx(gameFont, "Name:", (Vector2){(float)(modalX + 20), yPos}, 18, 0.0f, WHITE);
        yPos += 30.0f;
        
        // Text input box
        Rectangle textBox = {modalX + 20.0f, yPos, 460.0f, 30.0f};
        DrawRectangleRec(textBox, (Color){20, 20, 20, 255});
        DrawRectangleLinesEx(textBox, 2, WHITE);
        DrawTextEx(gameFont, modal.nameBuffer, (Vector2){(float)(modalX + 25), yPos + 5}, 18, 0.0f, WHITE);
        
        // Handle text input
        int key = GetCharPressed();
        while (key > 0) {
            if (key >= 32 && key <= 126 && modal.nameCursorPos < 63) {
                modal.nameBuffer[modal.nameCursorPos] = (char)key;
                modal.nameCursorPos++;
                modal.nameBuffer[modal.nameCursorPos] = '\0';
            }
            key = GetCharPressed();
        }
        
        if (IsKeyPressed(KEY_BACKSPACE) && modal.nameCursorPos > 0) {
            modal.nameCursorPos--;
            modal.nameBuffer[modal.nameCursorPos] = '\0';
        }
        
        yPos += 50.0f;
        DrawTextEx(gameFont, "Color:", (Vector2){(float)(modalX + 20), yPos}, 18, 0.0f, WHITE);
        yPos += 30.0f;
        
        // Color picker (predefined colors)
        std::vector<Color> colors = GetLineColorPalette();
        float colorBoxSize = 40.0f;
        float colorSpacing = 10.0f;
        float startX = modalX + 20.0f;
        
        for (int i = 0; i < (int)colors.size(); i++) {
            float x = startX + i * (colorBoxSize + colorSpacing);
            Rectangle colorRect = {x, yPos, colorBoxSize, colorBoxSize};
            DrawRectangleRec(colorRect, colors[i]);
            DrawRectangleLinesEx(colorRect, 2, i == modal.colorIndex ? WHITE : GRAY);
        }
        
        // Handle color selection with arrow keys or mouse
        if (IsKeyPressed(KEY_LEFT) && modal.colorIndex > 0) modal.colorIndex--;
        if (IsKeyPressed(KEY_RIGHT) && modal.colorIndex < (int)colors.size() - 1) modal.colorIndex++;
        modal.selectedColor = colors[modal.colorIndex];
        
        yPos += 70.0f;
        
        // Buttons
        Rectangle establishBtn = {modalX + 20.0f, yPos, 220.0f, 40.0f};
        Rectangle cancelBtn = {modalX + 260.0f, yPos, 220.0f, 40.0f};
        
        bool establishHover = CheckCollisionPointRec(CustomGetMousePosition(), establishBtn);
        bool cancelHover = CheckCollisionPointRec(CustomGetMousePosition(), cancelBtn);
        
        DrawRectangleRec(establishBtn, establishHover ? (Color){100, 200, 100, 255} : (Color){80, 150, 80, 255});
        DrawRectangleRec(cancelBtn, cancelHover ? (Color){200, 100, 100, 255} : (Color){150, 80, 80, 255});
        
        DrawTextEx(gameFont, "Establish", (Vector2){establishBtn.x + 70, establishBtn.y + 10}, 20, 0.0f, WHITE);
        DrawTextEx(gameFont, "Continue Building", (Vector2){cancelBtn.x + 20, cancelBtn.y + 10}, 18, 0.0f, WHITE);
        
        if (CustomIsMouseButtonPressed(MOUSE_BUTTON_LEFT)) {
            if (establishHover) {
                modal.establishClicked = true;
            } else if (cancelHover) {
                modal.cancelClicked = true;
            }
        }
        
    } else if (modal.state == LineModalState::AddToLine) {
        DrawTextEx(gameFont, "Add to Existing Line?", (Vector2){(float)(modalX + 20), yPos}, 24, 0.0f, WHITE);
        yPos += 50.0f;
        
        if (modal.targetLineId >= 0 && modal.targetLineId < (int)g_lines.size()) {
            const Line& targetLine = g_lines[modal.targetLineId];
            char lineInfo[128];
            snprintf(lineInfo, sizeof(lineInfo), "Line: %s (%d stations)", targetLine.name.c_str(), targetLine.stationCount);
            DrawTextEx(gameFont, lineInfo, (Vector2){(float)(modalX + 20), yPos}, 18, 0.0f, WHITE);
            yPos += 40.0f;
        }
        
        DrawTextEx(gameFont, "Add this station to the existing line,", (Vector2){(float)(modalX + 20), yPos}, 16, 0.0f, GRAY);
        yPos += 25.0f;
        DrawTextEx(gameFont, "or continue building without adding?", (Vector2){(float)(modalX + 20), yPos}, 16, 0.0f, GRAY);
        yPos += 50.0f;
        
        // Buttons
        Rectangle yesBtn = {modalX + 20.0f, yPos, 220.0f, 40.0f};
        Rectangle noBtn = {modalX + 260.0f, yPos, 220.0f, 40.0f};
        
        bool yesHover = CheckCollisionPointRec(CustomGetMousePosition(), yesBtn);
        bool noHover = CheckCollisionPointRec(CustomGetMousePosition(), noBtn);
        
        DrawRectangleRec(yesBtn, yesHover ? (Color){100, 200, 100, 255} : (Color){80, 150, 80, 255});
        DrawRectangleRec(noBtn, noHover ? (Color){200, 100, 100, 255} : (Color){150, 80, 80, 255});
        
        DrawTextEx(gameFont, "Yes, Add to Line", (Vector2){yesBtn.x + 30, yesBtn.y + 10}, 18, 0.0f, WHITE);
        DrawTextEx(gameFont, "No, Continue", (Vector2){noBtn.x + 50, noBtn.y + 10}, 18, 0.0f, WHITE);
        
        if (CustomIsMouseButtonPressed(MOUSE_BUTTON_LEFT)) {
            if (yesHover) {
                modal.addToLineClicked = true;
            } else if (noHover) {
                modal.cancelClicked = true;
            }
        }
    }
}

// Depots can be extended out from each other as long as the connected depot cluster has
// at least one depot adjacent to a station tile.
static bool CanPlaceDepotAt(const Vector3& pos, const std::vector<PlacedPlatform>& platforms, float gridSize) {
    // Always allow a depot directly next to a station tile.
    if (HasAdjacentStation(pos, platforms, gridSize)) return true;

    // Otherwise, require adjacency to an existing depot cluster that is (somewhere) connected to a station.
    std::vector<char> checked(platforms.size(), 0);
    bool hasAnyAdjacentDepot = false;

    for (int d = 0; d < (int)platforms.size(); d++) {
        if (!platforms[d].isDepot) continue;
        if (!ArePlatformsAdjacent(pos, platforms[d].position, gridSize)) continue;

        hasAnyAdjacentDepot = true;
        if (checked[d]) continue;

        std::vector<int> cluster = GetDepotClusterIndices(platforms, d, gridSize);
        for (int idx : cluster) if (idx >= 0 && idx < (int)checked.size()) checked[idx] = 1;

        if (DepotClusterHasStationConnection(platforms, cluster, gridSize)) return true;
    }

    (void)hasAnyAdjacentDepot;
    return false;
}

static bool HasAdjacentDepotForFactory(const Vector3& factoryCenter, const std::vector<PlacedPlatform>& platforms, float gridSize) {
    // Factory footprint is 4x4 tiles centered on factoryCenter
    float half = gridSize * 2.0f;
    float minX = factoryCenter.x - half;
    float maxX = factoryCenter.x + half;
    float minZ = factoryCenter.z - half;
    float maxZ = factoryCenter.z + half;

    // Check if any depot tile is adjacent to the factory footprint (touching its perimeter by ~1 tile)
    for (const auto& p : platforms) {
        if (!p.isDepot) continue;

        float dx = 0.0f;
        if (p.position.x < minX) dx = minX - p.position.x;
        else if (p.position.x > maxX) dx = p.position.x - maxX;

        float dz = 0.0f;
        if (p.position.z < minZ) dz = minZ - p.position.z;
        else if (p.position.z > maxZ) dz = p.position.z - maxZ;

        float dist = sqrtf(dx*dx + dz*dz);
        if (dist <= gridSize * 1.1f) return true;
    }
    return false;
}

// Check if a position is within 2 grid spaces of a station, factory, or depot
static bool IsWithinTwoGridSpacesOfValidBuilding(const Vector3& pos, 
                                                  const std::vector<PlacedPlatform>& platforms,
                                                  const std::vector<PlacedFactory>& factories,
                                                  float gridSize) {
    float maxDist = gridSize * 2.0f + 0.1f; // Within 2 grid spaces
    
    // Check stations (station tiles)
    for (const auto& p : platforms) {
        if (p.isStation && !p.isDepot) {
            float dist = Vector3Distance((Vector3){pos.x, 0.0f, pos.z}, (Vector3){p.position.x, 0.0f, p.position.z});
            if (dist <= maxDist) return true;
        }
    }
    
    // Check depots
    for (const auto& p : platforms) {
        if (p.isDepot) {
            float dist = Vector3Distance((Vector3){pos.x, 0.0f, pos.z}, (Vector3){p.position.x, 0.0f, p.position.z});
            if (dist <= maxDist) return true;
        }
    }
    
    // Check factories
    for (const auto& f : factories) {
        float dist = Vector3Distance((Vector3){pos.x, 0.0f, pos.z}, (Vector3){f.position.x, 0.0f, f.position.z});
        if (dist <= maxDist) return true;
    }
    
    return false;
}

// Check if there are at least 5 cargo materials within 10 grid spaces radius
static bool HasEnoughCargoInRadius(const Vector3& pos, 
                                    const std::vector<PlacedPlatform>& platforms,
                                    float gridSize,
                                    int requiredCargo) {
    float maxDist = gridSize * 10.0f; // 10 grid spaces radius
    int totalCargo = 0;
    
    // Check all depots within radius
    for (const auto& p : platforms) {
        if (!p.isDepot) continue;
        
        float dist = Vector3Distance((Vector3){pos.x, 0.0f, pos.z}, (Vector3){p.position.x, 0.0f, p.position.z});
        if (dist <= maxDist) {
            // Get the depot cluster this depot belongs to
            int depotIdx = -1;
            for (int i = 0; i < (int)platforms.size(); i++) {
                if (&platforms[i] == &p) {
                    depotIdx = i;
                    break;
                }
            }
            if (depotIdx >= 0) {
                std::vector<int> cluster = GetDepotClusterIndices(platforms, depotIdx, gridSize);
                int clusterCargo = GetClusterCargoTotal(platforms, cluster);
                // Only count cargo from this cluster once
                // We'll sum all unique clusters
            }
        }
    }
    
    // Better approach: collect all unique depot clusters within radius and sum their cargo
    std::vector<char> countedCluster(platforms.size(), 0);
    for (int i = 0; i < (int)platforms.size(); i++) {
        if (!platforms[i].isDepot) continue;
        if (countedCluster[i]) continue;
        
        float dist = Vector3Distance((Vector3){pos.x, 0.0f, pos.z}, (Vector3){platforms[i].position.x, 0.0f, platforms[i].position.z});
        if (dist <= maxDist) {
            std::vector<int> cluster = GetDepotClusterIndices(platforms, i, gridSize);
            int clusterCargo = GetClusterCargoTotal(platforms, cluster);
            totalCargo += clusterCargo;
            // Mark all depots in this cluster as counted
            for (int idx : cluster) {
                if (idx >= 0 && idx < (int)countedCluster.size()) countedCluster[idx] = 1;
            }
        }
    }
    
    return totalCargo >= requiredCargo;
}

// Remove cargo from depots within radius (removes from most-filled depots first)
static bool RemoveCargoFromRadius(const Vector3& pos,
                                   std::vector<PlacedPlatform>& platforms,
                                   float gridSize,
                                   int amount) {
    float maxDist = gridSize * 10.0f; // 10 grid spaces radius
    
    // Collect all unique depot clusters within radius
    std::vector<char> processedCluster(platforms.size(), 0);
    std::vector<std::vector<int>> clustersInRange;
    
    for (int i = 0; i < (int)platforms.size(); i++) {
        if (!platforms[i].isDepot) continue;
        if (processedCluster[i]) continue;
        
        float dist = Vector3Distance((Vector3){pos.x, 0.0f, pos.z}, (Vector3){platforms[i].position.x, 0.0f, platforms[i].position.z});
        if (dist <= maxDist) {
            std::vector<int> cluster = GetDepotClusterIndices(platforms, i, gridSize);
            clustersInRange.push_back(cluster);
            // Mark all depots in this cluster as processed
            for (int idx : cluster) {
                if (idx >= 0 && idx < (int)processedCluster.size()) processedCluster[idx] = 1;
            }
        }
    }
    
    // Try to remove cargo from clusters, starting with most-filled ones
    int remaining = amount;
    while (remaining > 0 && !clustersInRange.empty()) {
        // Find cluster with most cargo
        int bestIdx = -1;
        int bestCargo = -1;
        for (int i = 0; i < (int)clustersInRange.size(); i++) {
            int cargo = GetClusterCargoTotal(platforms, clustersInRange[i]);
            if (cargo > bestCargo) {
                bestCargo = cargo;
                bestIdx = i;
            }
        }
        
        if (bestIdx < 0 || bestCargo <= 0) break;
        
        int toRemove = std::min(remaining, bestCargo);
        RemoveCargoFromCluster(platforms, clustersInRange[bestIdx], toRemove);
        remaining -= toRemove;
        
        // Remove empty clusters
        if (bestCargo - toRemove <= 0) {
            clustersInRange.erase(clustersInRange.begin() + bestIdx);
        }
    }
    
    return remaining == 0; // Return true if we removed all required cargo
}

// Count how many adjacent platforms a given platform has
int CountAdjacentPlatforms(const Vector3& position, const std::vector<PlacedPlatform>& platforms, float gridSize) {
    const PlacedPlatform* self = FindPlatformAtPos(position, platforms);
    if (self && self->isDepot) return 0;

    int count = 0;
    for (const auto& p : platforms) {
        if (p.isDepot) continue;
        // Skip self
        if (Vector3Distance(position, p.position) < 0.1f) continue;
        if (ArePlatformsAdjacent(position, p.position, gridSize)) {
            count++;
        }
    }
    return count;
}

// Determine platform type based on neighbor count
// 0 = isolated, 1 = dead end, 2 = normal track, 3+ = junction/points
enum class PlatformType {
    Isolated,   // 0 neighbors
    DeadEnd,    // 1 neighbor (terminus)
    Track,      // 2 neighbors (normal track segment)
    Points      // 3+ neighbors (junction/switch)
};

PlatformType GetPlatformType(const Vector3& position, const std::vector<PlacedPlatform>& platforms, float gridSize) {
    int neighbors = CountAdjacentPlatforms(position, platforms, gridSize);
    if (neighbors == 0) return PlatformType::Isolated;
    if (neighbors == 1) return PlatformType::DeadEnd;
    if (neighbors == 2) return PlatformType::Track;
    return PlatformType::Points;
}

// Get all adjacent platform positions for a given platform
std::vector<Vector3> GetAdjacentPositions(const Vector3& position, const std::vector<PlacedPlatform>& platforms, float gridSize) {
    const PlacedPlatform* self = FindPlatformAtPos(position, platforms);
    if (self && self->isDepot) return {};

    std::vector<Vector3> adjacent;
    for (const auto& p : platforms) {
        if (p.isDepot) continue;
        if (Vector3Distance(position, p.position) < 0.1f) continue; // Skip self
        if (ArePlatformsAdjacent(position, p.position, gridSize)) {
            adjacent.push_back(p.position);
        }
    }
    return adjacent;
}

// Get adjacent positions sorted clockwise around the platform (stable exit order)
std::vector<Vector3> GetSortedAdjacentPositions(const Vector3& position, const std::vector<PlacedPlatform>& platforms, float gridSize) {
    std::vector<Vector3> adjacent = GetAdjacentPositions(position, platforms, gridSize);
    std::sort(adjacent.begin(), adjacent.end(), [&](const Vector3& a, const Vector3& b) {
        float angleA = atan2f(a.x - position.x, a.z - position.z);
        float angleB = atan2f(b.x - position.x, b.z - position.z);
        return angleA < angleB;
    });
    return adjacent;
}

static inline int NumJunctionPairs(int exits) {
    if (exits < 2) return 0;
    return (exits * (exits - 1)) / 2;
}

// Convert a pairIndex [0..nC2) into (i,j) with 0 <= i < j < exits using lexicographic enumeration.
static inline bool PairIndexToIJ(int exits, int pairIndex, int& outI, int& outJ) {
    if (exits < 2) return false;
    int pairs = NumJunctionPairs(exits);
    if (pairIndex < 0 || pairIndex >= pairs) return false;

    int idx = pairIndex;
    for (int i = 0; i < exits - 1; i++) {
        int countForI = (exits - 1) - i; // j = i+1 .. exits-1
        if (idx < countForI) {
            outI = i;
            outJ = i + 1 + idx;
            return true;
        }
        idx -= countForI;
    }
    return false;
}

// Deterministic default "straightest" pair: pick the two exits that are most opposite.
// This gives a sensible default for T junctions: the opposite pair becomes the through route.
static inline int DefaultJunctionPairIndex(const Vector3& center, const std::vector<Vector3>& exits) {
    int n = (int)exits.size();
    int pairs = NumJunctionPairs(n);
    if (pairs <= 0) return -1;
    if (pairs == 1) return 0;

    float bestDot = 1.0f;
    int bestI = 0, bestJ = 1;
    for (int i = 0; i < n; i++) {
        Vector3 di = Vector3Normalize(Vector3Subtract(exits[i], center));
        for (int j = i + 1; j < n; j++) {
            Vector3 dj = Vector3Normalize(Vector3Subtract(exits[j], center));
            float dot = di.x * dj.x + di.y * dj.y + di.z * dj.z;
            if (dot < bestDot) {
                bestDot = dot;
                bestI = i;
                bestJ = j;
            }
        }
    }

    // Convert (bestI,bestJ) back to pairIndex.
    int idx = 0;
    for (int i = 0; i < n - 1; i++) {
        for (int j = i + 1; j < n; j++) {
            if (i == bestI && j == bestJ) return idx;
            idx++;
        }
    }
    return 0;
}

// Draw visual indicators for a Points-Platform (junction)
// If a train is selected (isEditable==true), highlight the active connected exit *pair* for that train.
void DrawPointsIndicator(const Vector3& position, const std::vector<PlacedPlatform>& platforms, float gridSize, float time, int selectedExitIndex, bool isEditable) {
    std::vector<Vector3> adjacent = GetSortedAdjacentPositions(position, platforms, gridSize);
    
    if (adjacent.size() < 3) return; // Not a points platform
    
    float topY = GetPlatformTopY(position.y, gridSize);
    float topThickness = gridSize * 0.1f;
    float indicatorY = topY + topThickness / 2.0f + 0.5f; // Slightly above platform surface
    
    // Pulsing effect
    float pulse = (sinf(time * 3.0f) + 1.0f) / 2.0f; // 0 to 1 pulsing
    unsigned char alpha = (unsigned char)(150 + pulse * 105); // 150 to 255
    
    // Draw diamond shape in the center
    float diamondSize = gridSize * 0.3f;
    
    // Change diamond color based on edit mode
    Color diamondColor;
    if (isEditable) {
        diamondColor = { 0, 255, 0, alpha }; // Green when editable (train selected)
    } else {
        diamondColor = { 255, 255, 0, alpha }; // Yellow when not editable
    }
    
    Vector3 center = { position.x, indicatorY, position.z };
    Vector3 north = { position.x, indicatorY, position.z - diamondSize };
    Vector3 south = { position.x, indicatorY, position.z + diamondSize };
    Vector3 east = { position.x + diamondSize, indicatorY, position.z };
    Vector3 west = { position.x - diamondSize, indicatorY, position.z };
    
    // Draw diamond outline
    DrawLine3D(north, east, diamondColor);
    DrawLine3D(east, south, diamondColor);
    DrawLine3D(south, west, diamondColor);
    DrawLine3D(west, north, diamondColor);
    
    // Draw lines to each connected direction with arrows
    float arrowLength = gridSize * 0.35f;
    float arrowHeadSize = gridSize * 0.1f;
    
    // Interpret selectedExitIndex as a *pairIndex* over exits (see JunctionSetting comment).
    int pairIdx = selectedExitIndex;
    int numPairs = NumJunctionPairs((int)adjacent.size());
    if (pairIdx < 0 || pairIdx >= numPairs) {
        pairIdx = DefaultJunctionPairIndex(position, adjacent);
    }

    int activeI = -1, activeJ = -1;
    (void)PairIndexToIJ((int)adjacent.size(), pairIdx, activeI, activeJ);

    int exitIdx = 0;
    for (const auto& adj : adjacent) {
        // Determine arrow color based on whether this exit is in the active connected pair
        Color arrowColor;
        bool isActiveExit = (exitIdx == activeI || exitIdx == activeJ);
        
        if (isEditable) {
            if (isActiveExit) {
                arrowColor = { 0, 255, 0, 255 }; // Bright green for active exit
            } else {
                arrowColor = { 100, 100, 100, 200 }; // Gray for inactive exits
            }
        } else {
            // When not editing, only show the active connected pair (two arrows).
            if (!isActiveExit) { exitIdx++; continue; }
            arrowColor = { 255, 200, 0, alpha }; // Orange-yellow active pair when no train selected
        }
        
        // Calculate direction to adjacent platform
        Vector3 dir = Vector3Normalize(Vector3Subtract(adj, position));
        
        // Arrow start and end points
        Vector3 arrowStart = { 
            position.x + dir.x * diamondSize * 0.7f, 
            indicatorY, 
            position.z + dir.z * diamondSize * 0.7f 
        };
        Vector3 arrowEnd = { 
            position.x + dir.x * arrowLength, 
            indicatorY, 
            position.z + dir.z * arrowLength 
        };
        
        // Draw arrow line (thicker for active exit)
        DrawLine3D(arrowStart, arrowEnd, arrowColor);
        if (isActiveExit && isEditable) {
            // Draw a second line slightly offset for thickness effect
            Vector3 offset1 = { arrowStart.x + 0.05f, arrowStart.y, arrowStart.z };
            Vector3 offset2 = { arrowEnd.x + 0.05f, arrowEnd.y, arrowEnd.z };
            DrawLine3D(offset1, offset2, arrowColor);
        }
        
        // Draw arrowhead (two lines forming a V)
        Vector3 perpDir = { -dir.z, 0.0f, dir.x }; // Perpendicular direction
        Vector3 headLeft = {
            arrowEnd.x - dir.x * arrowHeadSize + perpDir.x * arrowHeadSize * 0.5f,
            indicatorY,
            arrowEnd.z - dir.z * arrowHeadSize + perpDir.z * arrowHeadSize * 0.5f
        };
        Vector3 headRight = {
            arrowEnd.x - dir.x * arrowHeadSize - perpDir.x * arrowHeadSize * 0.5f,
            indicatorY,
            arrowEnd.z - dir.z * arrowHeadSize - perpDir.z * arrowHeadSize * 0.5f
        };
        
        DrawLine3D(arrowEnd, headLeft, arrowColor);
        DrawLine3D(arrowEnd, headRight, arrowColor);
        
        // Draw exit number near the arrow (small text would be ideal, but we'll use a sphere)
        if (isEditable) {
            float numRadius = isActiveExit ? 0.15f : 0.1f;
            Color numColor = isActiveExit ? (Color){0, 255, 0, 255} : (Color){150, 150, 150, 200};
            Vector3 numPos = { arrowEnd.x + dir.x * 0.3f, indicatorY + 0.2f, arrowEnd.z + dir.z * 0.3f };
            DrawSphere(numPos, numRadius, numColor);
        }
        
        exitIdx++;
    }
    
    // Draw a small sphere at center for emphasis
    float sphereRadius = gridSize * 0.08f * (0.8f + pulse * 0.4f); // Pulsing size
    DrawSphere(center, sphereRadius, diamondColor);
}

// Find all connected platforms starting from a given position
// Uses BFS to find all connected platforms
std::vector<Vector3> FindConnectedPlatforms(const Vector3& startPos, const std::vector<PlacedPlatform>& platforms, float gridSize) {
    std::vector<Vector3> connected;
    std::vector<bool> visited(platforms.size(), false);
    std::vector<int> queue;
    queue.reserve(platforms.size());
    size_t queueHead = 0;
    
    // Find starting platform
    int startIdx = -1;
    float minDist = gridSize * 2.0f;
    for (size_t i = 0; i < platforms.size(); i++) {
        if (platforms[i].isDepot) continue;
        float dist = Vector3Distance(startPos, platforms[i].position);
        if (dist < minDist) {
            minDist = dist;
            startIdx = i;
        }
    }
    
    if (startIdx == -1 || minDist > gridSize * 0.6f) {
        return connected;
    }
    
    // BFS to find all connected platforms
    queue.push_back(startIdx);
    visited[startIdx] = true;
    
    while (queueHead < queue.size()) {
        int currentIdx = queue[queueHead++];
        connected.push_back(platforms[currentIdx].position);
        
        // Find adjacent platforms
        for (size_t i = 0; i < platforms.size(); i++) {
            if (platforms[i].isDepot) continue;
            if (!visited[i] && ArePlatformsAdjacent(platforms[currentIdx].position, platforms[i].position, gridSize)) {
                visited[i] = true;
                queue.push_back(i);
            }
        }
    }
    
    return connected;
}

// Build a path through connected platforms using a simple pathfinding algorithm
// Tries to create a continuous path from one end to the other
// If train is provided, uses its junction settings to determine path through junctions
std::vector<Vector3> BuildPlatformPath(const Vector3& startPos, const std::vector<PlacedPlatform>& platforms, float gridSize, const PlacedTrain* train = nullptr) {
    std::vector<Vector3> connected = FindConnectedPlatforms(startPos, platforms, gridSize);
    
    if (connected.size() < 4) {
        return std::vector<Vector3>(); // Need at least 4 platforms
    }
    
    // Helper: find the closest connected node to a position
    auto findClosestIdx = [&](const Vector3& pos) -> int {
        int best = 0;
        float bestDist = 1e9f;
        for (int i = 0; i < (int)connected.size(); i++) {
            float d = Vector3Distance(pos, connected[i]);
            if (d < bestDist) { bestDist = d; best = i; }
        }
        return best;
    };

    // Helper: is a position in the connected set?
    auto inConnected = [&](const Vector3& pos) -> bool {
        for (const auto& c : connected) {
            if (Vector3Distance(c, pos) < 0.1f) return true;
        }
        return false;
    };

    // Precompute degrees in this connected component
    std::vector<int> degree(connected.size(), 0);
    for (int i = 0; i < (int)connected.size(); i++) {
        for (int j = 0; j < (int)connected.size(); j++) {
            if (i == j) continue;
            if (ArePlatformsAdjacent(connected[i], connected[j], gridSize)) degree[i]++;
        }
    }
    bool hasEndpoint = false;
    for (int d : degree) { if (d == 1) { hasEndpoint = true; break; } }

    // Choose start: endpoint if present, otherwise closest to startPos (loop case)
    int startIdx = -1;
    if (hasEndpoint) {
        for (int i = 0; i < (int)connected.size(); i++) {
            if (degree[i] == 1) { startIdx = i; break; }
        }
    }
    if (startIdx == -1) startIdx = findClosestIdx(startPos);

    // Walk the graph deterministically:
    // - degree 2: continue forward (don't U-turn)
    // - degree 3+: use per-train junction setting (stable clockwise order), avoiding U-turn if possible
    // - endpoint: stop (for non-loop paths)
    std::vector<Vector3> path;
    path.reserve(connected.size() + 2);

    Vector3 start = connected[startIdx];
    Vector3 current = start;
    Vector3 prev = { 1e9f, 1e9f, 1e9f }; // sentinel

    auto samePos = [&](const Vector3& a, const Vector3& b) -> bool {
        return Vector3Distance(a, b) < 0.1f;
    };

    auto isSentinelPrev = [&](const Vector3& p) -> bool {
        return (p.x > 9e8f && p.y > 9e8f && p.z > 9e8f);
    };

    auto chooseNext = [&](const Vector3& cur, const Vector3& prevPos) -> Vector3 {
        // Get stable neighbors, but only those inside this connected component
        std::vector<Vector3> neighborsAll = GetSortedAdjacentPositions(cur, platforms, gridSize);
        std::vector<Vector3> neighbors;
        for (const auto& n : neighborsAll) {
            if (inConnected(n)) neighbors.push_back(n);
        }
        if (neighbors.empty()) return prevPos; // no move possible

        // Endpoint stop handled by caller (we need neighbors list for that check)
        if (neighbors.size() == 1) return neighbors[0];

        // Junction (degree 3+): treat setting as a connected *pair* of exits.
        // This makes the junction bidirectional and guarantees two "active" directions.
        if (neighbors.size() >= 3) {
            int pairIdx = -1;
            if (train != nullptr) pairIdx = train->GetJunctionSetting(cur.x, cur.z);
            int numPairs = NumJunctionPairs((int)neighbors.size());
            if (pairIdx < 0 || pairIdx >= numPairs) {
                pairIdx = DefaultJunctionPairIndex(cur, neighbors);
            }

            int i = -1, j = -1;
            if (PairIndexToIJ((int)neighbors.size(), pairIdx, i, j)) {
                // No incoming direction yet (start node): just pick one side of the active pair.
                if (isSentinelPrev(prevPos)) return neighbors[i];

                // If we arrived from one side of the active pair, we must exit via the other side.
                if (samePos(prevPos, neighbors[i])) return neighbors[j];
                if (samePos(prevPos, neighbors[j])) return neighbors[i];

                // Arrived from a non-connected leg: no forward move (dead end under current switch state).
                return prevPos;
            }
        }

        // Normal track: avoid U-turn if possible
        for (const auto& n : neighbors) {
            if (!samePos(n, prevPos)) return n;
        }
        return neighbors[0];
    };

    path.push_back(current);
    const int maxSteps = (int)connected.size() + 5; // safety
    for (int step = 0; step < maxSteps; step++) {
        // Stable neighbor list within component (for endpoint detection)
        std::vector<Vector3> neighborsAll = GetSortedAdjacentPositions(current, platforms, gridSize);
        std::vector<Vector3> neighbors;
        for (const auto& n : neighborsAll) {
            if (inConnected(n)) neighbors.push_back(n);
        }

        // If this is a true endpoint (non-loop), stop instead of bouncing back
        if (hasEndpoint && !samePos(prev, (Vector3){1e9f,1e9f,1e9f}) && neighbors.size() == 1) {
            break;
        }

        Vector3 next = chooseNext(current, prev);

        // If we couldn't advance (e.g., hit a junction leg that isn't connected in the current switch state),
        // stop the walk for open networks instead of bouncing and creating a bogus one-way artifact.
        if (samePos(next, prev) && !samePos(prev, (Vector3){1e9f,1e9f,1e9f})) {
            break;
        }

        // Loop closure: when there are no endpoints, close the ring when we return to start
        if (!hasEndpoint && !samePos(prev, (Vector3){1e9f,1e9f,1e9f}) && samePos(next, start)) {
            path.push_back(start);
            break;
        }

        // Prevent infinite tiny loops if something goes wrong
        if (!hasEndpoint) {
            bool already = false;
            for (const auto& p : path) {
                if (samePos(p, next)) { already = true; break; }
            }
            if (already) break;
        }

        prev = current;
        current = next;
        path.push_back(current);
    }

    return path;
}

static bool RebuildTrainPath(PlacedTrain& train, const std::vector<PlacedPlatform>& platforms, float gridSize) {
    if (platforms.size() < 4) return false;

    // Build a new path starting from wherever the train currently is (projected to y=0 for platform lookup)
    Vector3 startPos = { train.position.x, 0.0f, train.position.z };
    std::vector<Vector3> newPath = BuildPlatformPath(startPos, platforms, gridSize, &train);
    if (newPath.size() < 4) return false;

    // Convert to platform top Y positions (same convention as existing paths)
    std::vector<Vector3> pathWithY;
    pathWithY.reserve(newPath.size());
    for (const auto& pos : newPath) {
        float topY = GetPlatformTopY(pos.y, gridSize);
        pathWithY.push_back({ pos.x, topY, pos.z });
    }

    float newLen = GetPathLength(pathWithY);
    if (newLen <= 0.0f) return false;

    // Preserve the train's location on the route as best as possible by snapping progress
    // to the closest point on the new path.
    Vector3 trainPoint = { train.position.x, pathWithY[0].y, train.position.z };
    float newProgress = GetClosestDistanceAlongPath(pathWithY, trainPoint);

    train.path = pathWithY;
    train.pathLength = newLen;

    // Ensure progress is valid for this train type (open paths clamp based on front-car reach)
    float minProgress = 0.0f;
    float maxProgress = train.pathLength;
    GetTrainProgressLimitsFrontCar(train, gridSize, train.pathLength, minProgress, maxProgress);

    if (maxProgress <= minProgress) {
        train.pathProgress = train.pathLength / 2.0f;
        train.direction = 0.0f;
    } else if (IsLoopPath(train.path)) {
        train.pathProgress = WrapDistance(newProgress, train.pathLength);
        if (train.direction == 0.0f) train.direction = 1.0f;
    } else {
        train.pathProgress = Clamp(newProgress, minProgress, maxProgress);
        if (train.direction == 0.0f) train.direction = 1.0f;
    }

    // Update center position immediately so selection/hit testing stays correct this frame
    PathPoint centerPoint = GetPathPoint(train.path, train.pathProgress);
    train.position = centerPoint.position;
    return true;
}

// --- 2D Map helpers (top-down XZ plane) ---
static inline Vector2 WorldToMap(Vector3 worldPos) {
    // Map coordinates: X right, Z up (so north feels up on screen)
    return { worldPos.x, -worldPos.z };
}

static inline Vector2 WorldDirToMap(Vector3 dir) {
    return { dir.x, -dir.z };
}

static void DrawTrainOnMap(const PlacedTrain& train, float gridSize, Color color, float brightnessMul = 1.0f) {
    if (train.path.size() < 2) return;
    PathPoint center = GetPathPoint(train.path, train.pathProgress);
    Vector2 p = WorldToMap(center.position);

    Vector2 f = WorldDirToMap(center.direction);
    float fl = sqrtf(f.x*f.x + f.y*f.y);
    if (fl < 0.0001f) f = { 1.0f, 0.0f };
    else { f.x /= fl; f.y /= fl; }
    Vector2 r = { -f.y, f.x };

    const float trainScale = 0.8f;  // 20% smaller trains
    float tipLen = gridSize * 0.60f * trainScale;
    float backLen = gridSize * 0.45f * trainScale;
    float halfW  = gridSize * 0.25f * trainScale;

    Vector2 tip   = { p.x + f.x * tipLen,              p.y + f.y * tipLen };
    Vector2 baseC = { p.x - f.x * backLen,             p.y - f.y * backLen };
    Vector2 b1    = { baseC.x + r.x * halfW,           baseC.y + r.y * halfW };
    Vector2 b2    = { baseC.x - r.x * halfW,           baseC.y - r.y * halfW };

    // Apply brightness multiplier to the color
    Color drawColor = MulColor(color, brightnessMul);
    DrawTriangle(tip, b1, b2, drawColor);
}

// Get the start and end positions of a platform line
// Returns true if valid, and outputs the line start and end positions
bool GetPlatformLineEndpoints(const Vector3& position, const std::vector<PlacedPlatform>& platforms, float gridSize, bool isHorizontal, Vector3& outLineStart, Vector3& outLineEnd) {
    // Find the nearest platform to the position
    const PlacedPlatform* nearestPlatform = nullptr;
    float nearestDist = gridSize * 2.0f;
    
    for (const auto& platform : platforms) {
        float dist = Vector3Distance(position, platform.position);
        if (dist < nearestDist) {
            nearestDist = dist;
            nearestPlatform = &platform;
        }
    }
    
    if (nearestPlatform == nullptr || nearestDist > gridSize * 0.6f) {
        return false;
    }
    
    if (isHorizontal) {
        // Collect all platforms on the same Z coordinate
        std::vector<Vector3> horizontalPlatforms;
        for (const auto& platform : platforms) {
            if (fabsf(platform.position.z - nearestPlatform->position.z) < gridSize * 0.1f) {
                horizontalPlatforms.push_back(platform.position);
            }
        }
        
        // Sort by X coordinate
        std::sort(horizontalPlatforms.begin(), horizontalPlatforms.end(), 
            [](const Vector3& a, const Vector3& b) { return a.x < b.x; });
        
        if (horizontalPlatforms.size() >= 4) {
            outLineStart = horizontalPlatforms[0];
            outLineEnd = horizontalPlatforms[horizontalPlatforms.size() - 1];
            return true;
        }
    } else {
        // Collect all platforms on the same X coordinate
        std::vector<Vector3> verticalPlatforms;
        for (const auto& platform : platforms) {
            if (fabsf(platform.position.x - nearestPlatform->position.x) < gridSize * 0.1f) {
                verticalPlatforms.push_back(platform.position);
            }
        }
        
        // Sort by Z coordinate
        std::sort(verticalPlatforms.begin(), verticalPlatforms.end(), 
            [](const Vector3& a, const Vector3& b) { return a.z < b.z; });
        
        if (verticalPlatforms.size() >= 4) {
            outLineStart = verticalPlatforms[0];
            outLineEnd = verticalPlatforms[verticalPlatforms.size() - 1];
            return true;
        }
    }
    
    return false;
}

// Check if there are at least 4 platforms connected in a straight line
// Returns true if valid, and outputs the line direction (true = horizontal/X axis, false = vertical/Z axis)
// Also outputs the center position of the line
bool CheckPlatformsInLine(const Vector3& position, const std::vector<PlacedPlatform>& platforms, float gridSize, bool& outIsHorizontal, Vector3& outLineCenter) {
    // Find the nearest platform to the position
    const PlacedPlatform* nearestPlatform = nullptr;
    float nearestDist = gridSize * 2.0f;
    
    for (const auto& platform : platforms) {
        float dist = Vector3Distance(position, platform.position);
        if (dist < nearestDist) {
            nearestDist = dist;
            nearestPlatform = &platform;
        }
    }
    
    // If no platform found nearby, return false
    if (nearestPlatform == nullptr || nearestDist > gridSize * 0.6f) {
        return false;
    }
    
    // Check horizontal line (same Z, different X)
    std::vector<Vector3> horizontalPlatforms;
    for (const auto& platform : platforms) {
        if (fabsf(platform.position.z - nearestPlatform->position.z) < gridSize * 0.1f) {
            horizontalPlatforms.push_back(platform.position);
        }
    }
    
    // Sort by X coordinate
    std::sort(horizontalPlatforms.begin(), horizontalPlatforms.end(), 
        [](const Vector3& a, const Vector3& b) { return a.x < b.x; });
    
    // Check if they form a continuous line of at least 4 platforms
    if (horizontalPlatforms.size() >= 4) {
        float minX = horizontalPlatforms[0].x;
        float maxX = horizontalPlatforms[horizontalPlatforms.size() - 1].x;
        
        // Verify continuity (check if all positions are properly spaced)
        bool isContinuous = true;
        for (size_t i = 1; i < horizontalPlatforms.size(); i++) {
            float spacing = fabsf(horizontalPlatforms[i].x - horizontalPlatforms[i-1].x);
            if (spacing > gridSize * 1.1f) { // Allow small tolerance
                isContinuous = false;
                break;
            }
        }
        
        if (isContinuous && (int)horizontalPlatforms.size() >= 4) {
            outIsHorizontal = true;
            outLineCenter = { (minX + maxX) / 2.0f, nearestPlatform->position.y, nearestPlatform->position.z };
            return true;
        }
    }
    
    // Check vertical line (same X, different Z)
    std::vector<Vector3> verticalPlatforms;
    for (const auto& platform : platforms) {
        if (fabsf(platform.position.x - nearestPlatform->position.x) < gridSize * 0.1f) {
            verticalPlatforms.push_back(platform.position);
        }
    }
    
    // Sort by Z coordinate
    std::sort(verticalPlatforms.begin(), verticalPlatforms.end(), 
        [](const Vector3& a, const Vector3& b) { return a.z < b.z; });
    
    // Check if they form a continuous line of at least 4 platforms
    if (verticalPlatforms.size() >= 4) {
        float minZ = verticalPlatforms[0].z;
        float maxZ = verticalPlatforms[verticalPlatforms.size() - 1].z;
        
        // Verify continuity
        bool isContinuous = true;
        for (size_t i = 1; i < verticalPlatforms.size(); i++) {
            float spacing = fabsf(verticalPlatforms[i].z - verticalPlatforms[i-1].z);
            if (spacing > gridSize * 1.1f) {
                isContinuous = false;
                break;
            }
        }
        
        if (isContinuous && (int)verticalPlatforms.size() >= 4) {
            outIsHorizontal = false;
            outLineCenter = { nearestPlatform->position.x, nearestPlatform->position.y, (minZ + maxZ) / 2.0f };
            return true;
        }
    }
    
    return false;
}

// Check if there are at least 4 connected platforms (can go around corners)
// Returns true if valid, and outputs a path center position
bool CheckConnectedPlatforms(const Vector3& position, const std::vector<PlacedPlatform>& platforms, float gridSize, Vector3& outPathCenter) {
    std::vector<Vector3> connected = FindConnectedPlatforms(position, platforms, gridSize);
    
    if (connected.size() < 4) {
        return false;
    }
    
    // Calculate center of connected platforms
    Vector3 center = { 0.0f, 0.0f, 0.0f };
    for (const auto& platform : connected) {
        center.x += platform.x;
        center.y += platform.y;
        center.z += platform.z;
    }
    center.x /= connected.size();
    center.y /= connected.size();
    center.z /= connected.size();
    
    outPathCenter = center;
    return true;
}

// Check if two buildings overlap (on XZ plane, ignoring height)
// Returns true if they overlap (allows touching edges)
bool buildingsOverlap(const Building& a, const Building& b) {
    // Calculate bounding boxes on XZ plane
    float aLeft = a.position.x - a.size.x / 2.0f;
    float aRight = a.position.x + a.size.x / 2.0f;
    float aFront = a.position.z - a.size.z / 2.0f;
    float aBack = a.position.z + a.size.z / 2.0f;
    
    float bLeft = b.position.x - b.size.x / 2.0f;
    float bRight = b.position.x + b.size.x / 2.0f;
    float bFront = b.position.z - b.size.z / 2.0f;
    float bBack = b.position.z + b.size.z / 2.0f;
    
    // Check for overlap (standard AABB collision)
    // This allows touching edges (when aRight == bLeft, no overlap)
    // But prevents actual overlapping
    bool overlapsX = (aLeft < bRight) && (aRight > bLeft);
    bool overlapsZ = (aFront < bBack) && (aBack > bFront);
    
    return overlapsX && overlapsZ;
}

// Check if a building overlaps with any existing building
bool overlapsWithAny(const Building& newBuilding, const std::vector<Building>& existingBuildings) {
    for (const auto& existing : existingBuildings) {
        if (buildingsOverlap(newBuilding, existing)) {
            return true;
        }
    }
    return false;
}

// Generate a random city skyline
std::vector<Building> generateCitySkyline() {
    std::vector<Building> buildings;
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_real_distribution<float> heightDist(5.0f, 30.0f);
    
    // Grid spacing (matches DrawGrid spacing)
    const float gridSize = 5.0f;
    
    // Footprint sizes: 1x, 4x, or 6x grid squares
    const float footprintSizes[] = { gridSize, gridSize * 4.0f, gridSize * 6.0f };
    
    // Create a grid of buildings, snapped to grid intersections (like bureaus)
    // Grid intersections are at multiples of gridSize (5.0)
    for (int gridX = -40; gridX < 40; gridX += 5) {
        for (int gridZ = -40; gridZ < 40; gridZ += 5) {
            // Random chance to place a building (reduced probability)
            if (gen() % 6 == 0) {
                Building building;
                
                // Randomly choose footprint size (1x, 4x, or 6x grid)
                int sizeIndex = gen() % 3;
                float footprintSize = footprintSizes[sizeIndex];
                
                // Use same size for width and depth (square footprint)
                float width = footprintSize;
                float depth = footprintSize;
                float height = heightDist(gen);
                
                // Position snapped to grid intersections (multiples of gridSize, like bureaus)
                float x = (float)gridX;
                float z = (float)gridZ;
                
                // Position at center of cube (height/2 for ground placement)
                building.position = { 
                    x, 
                    height / 2.0f, 
                    z 
                };
                building.size = { width, height, depth };
                building.color = (Color){ 255, 0, 0, 200 }; // Red with slight transparency
                
                // Only add if it doesn't overlap with existing buildings
                if (!overlapsWithAny(building, buildings)) {
                    buildings.push_back(building);
                }
            }
        }
    }
    
    // Add some taller buildings in the center (snapped to grid intersections)
    int attempts = 0;
    int maxAttempts = 50; // Limit attempts to avoid infinite loop
    for (int i = 0; i < 2 && attempts < maxAttempts; attempts++) {
        Building building;
        
        // Randomly choose footprint size
        int sizeIndex = gen() % 3;
        float footprintSize = footprintSizes[sizeIndex];
        float width = footprintSize;
        float depth = footprintSize;
        float height = heightDist(gen) * 2.0f; // Taller buildings
        
        // Snap to grid intersections (multiples of gridSize, like bureaus)
        int gridX = ((gen() % 20 - 10) / 5) * 5;
        int gridZ = ((gen() % 20 - 10) / 5) * 5;
        
        building.position = { 
            (float)gridX, 
            height / 2.0f, 
            (float)gridZ 
        };
        building.size = { width, height, depth };
        building.color = (Color){ 255, 0, 0, 200 }; // Red with slight transparency
        
        // Only add if it doesn't overlap with existing buildings
        if (!overlapsWithAny(building, buildings)) {
            buildings.push_back(building);
            i++; // Only increment when successfully placed
        }
    }
    
    return buildings;
}

// ══════════════════════════════════════════════════════════════════════════════
// DLL EXPORTS (for BBS embedded mode)
// ══════════════════════════════════════════════════════════════════════════════

extern "C" {

// Forward declaration of the game loop body function
static void GameLoopBody();

__declspec(dllexport) bool InitializeGame() {
    printf("[InitializeGame] Starting CyberTrain unified initialization...\n");
    fflush(stdout);
    g_standalone_mode = false;
    g_exit_requested = false;
    
    SetTraceLogLevel(LOG_NONE);
    
    if (!IsWindowReady()) {
        printf("[InitializeGame] Creating hidden window...\n");
        fflush(stdout);
        SetConfigFlags(FLAG_WINDOW_UNDECORATED | FLAG_WINDOW_HIDDEN);
        InitWindow(VIRTUAL_WIDTH, VIRTUAL_HEIGHT, "CyberTrain_Embedded");
        DisableCursor();
        SetTargetFPS(0); // Unlimited FPS for embedded mode
    }
    
    printf("[InitializeGame] Creating framebuffer %dx%d...\n", g_renderWidth, g_renderHeight);
    fflush(stdout);
    g_framebuffer = LoadRenderTexture(g_renderWidth, g_renderHeight);
    g_framebuffer_initialized = true;
    
    // Embedded mode: skip InitAudioDevice() to avoid conflicts with pygame
    g_audio_initialized = false;
    printf("[InitializeGame] Embedded mode: skipping InitAudioDevice()\n");
    fflush(stdout);
    
    printf("[InitializeGame] Loading font...\n");
    fflush(stdout);
    const char* fontPaths[] = {"PixelifySans.ttf", "Data/games/CyberTrain/PixelifySans.ttf", "static/PixelifySans-Regular.ttf"};
    bool fontLoaded = false;
    for (int i = 0; i < 3 && !fontLoaded; i++) {
        gameFont = LoadFont(fontPaths[i]);
        if (gameFont.texture.id != 0) { fontIsCustom = true; fontLoaded = true; }
    }
    if (!fontLoaded) gameFont = GetFontDefault();
    
    // Load UI Assets
    LoadUIAssets();
    
    // Load scanline texture (from main Data/images folder)
    printf("[InitializeGame] Loading scanline texture...\n");
    fflush(stdout);
    scanlineTx = LoadTexture("../../images/scanline.png");
    if (scanlineTx.id == 0) {
        // Try alternative paths
        scanlineTx = LoadTexture("Data/images/scanline.png");
    }
    if (scanlineTx.id == 0) {
        printf("[InitializeGame] Warning: Could not load scanline.png\n");
    } else {
        printf("[InitializeGame] Scanline texture loaded: %dx%d\n", scanlineTx.width, scanlineTx.height);
    }
    fflush(stdout);
    
    // Initialize global game state
    printf("[InitializeGame] Generating skyline...\n");
    fflush(stdout);
    g_buildings = generateCitySkyline();
    printf("[InitializeGame] Skyline generated: %d buildings\n", (int)g_buildings.size());
    fflush(stdout);
    
    // Initialize camera
    g_camera.position = (Vector3){ 60.0f, 50.0f, 60.0f };
    g_camera.target = (Vector3){ 0.0f, 0.0f, 0.0f };
    g_camera.up = (Vector3){ 0.0f, 1.0f, 0.0f };
    g_camera.fovy = 45.0f;
    g_camera.projection = CAMERA_PERSPECTIVE;
    g_cameraAltitude = g_camera.position.y;
    g_cameraYaw = atan2f(g_camera.position.x - g_camera.target.x, g_camera.position.z - g_camera.target.z);
    g_cameraRadius = sqrtf((g_camera.position.x - g_camera.target.x) * (g_camera.position.x - g_camera.target.x) +
                           (g_camera.position.z - g_camera.target.z) * (g_camera.position.z - g_camera.target.z));
    
    // Initialize 2D map camera
    g_mapCamera.target = { 0.0f, 0.0f };
    g_mapCamera.offset = { (float)g_renderWidth * 0.5f, (float)g_renderHeight * 0.5f };
    g_mapCamera.rotation = 0.0f;
    g_mapCamera.zoom = 6.0f;
    
    g_game_initialized = true; 
    printf("[InitializeGame] CyberTrain initialized successfully.\n");
    fflush(stdout);
    return true;
}

__declspec(dllexport) void UpdateFrame() { 
    if (!g_game_initialized || !g_framebuffer_initialized) return;
    
    // Run one iteration of the game loop
    GameLoopBody();
    
    // Clear one-shot input events
    ClearInputFrame();
}

__declspec(dllexport) unsigned char* GetFrameBuffer() {
    if (!g_framebuffer_initialized) return NULL;
    int w = g_framebuffer.texture.width, h = g_framebuffer.texture.height, sz = w*h*4;
    if (g_frame_buffer_size != sz) { if (g_frame_buffer_data) MemFree(g_frame_buffer_data); g_frame_buffer_data = (unsigned char*)MemAlloc(sz); g_frame_buffer_size = sz; }
    void* px = rlReadTexturePixels(g_framebuffer.texture.id, w, h, g_framebuffer.texture.format);
    if (px) { memcpy(g_frame_buffer_data, px, sz); MemFree(px); }
    return g_frame_buffer_data;
}

__declspec(dllexport) int GetWidth() { return g_framebuffer_initialized ? g_framebuffer.texture.width : 0; }
__declspec(dllexport) int GetHeight() { return g_framebuffer_initialized ? g_framebuffer.texture.height : 0; }
__declspec(dllexport) void SetKeyState(int k, bool d) { if (k>=0 && k<512) { if (d && !g_inputState.keys[k]) g_inputState.keysPressed[k]=true; g_inputState.keys[k]=d; } }
__declspec(dllexport) void SetMouseButtonState(int b, bool d) { if (b>=0 && b<8) { if (d && !g_inputState.mouseButtons[b]) g_inputState.mouseButtonsPressed[b]=true; g_inputState.mouseButtons[b]=d; } }
__declspec(dllexport) void SetInputMousePosition(float x, float y) { g_inputState.mousePosition = {x, y}; }
__declspec(dllexport) void SetMouseDelta(float dx, float dy) { g_inputState.mouseDelta = {dx, dy}; }
__declspec(dllexport) void SetMouseWheelMove(float m) { g_inputState.mouseWheelMove = m; }
// ClearInputFrame is already defined above as a static function
__declspec(dllexport) bool ShouldExit() { return g_exit_requested; }
__declspec(dllexport) void CleanupGame() { if (g_framebuffer_initialized) UnloadRenderTexture(g_framebuffer); UnloadUIAssets(); if (g_frame_buffer_data) MemFree(g_frame_buffer_data); g_game_initialized = false; if (g_audio_initialized) CloseAudioDevice(); }
__declspec(dllexport) void SetRenderResolution(int width, int height) { if (!g_framebuffer_initialized) { g_renderWidth = width; g_renderHeight = height; } }
__declspec(dllexport) unsigned int GetFrameTextureHandle() { return g_framebuffer_initialized ? g_framebuffer.texture.id : 0; }
__declspec(dllexport) void SetRenderResolutionPreset(int preset) { 
    if (g_framebuffer_initialized) return;
    if (preset == 0) { g_renderWidth = 480; g_renderHeight = 320; }
    else if (preset == 2) { g_renderWidth = 720; g_renderHeight = 480; }
    else { g_renderWidth = 600; g_renderHeight = 400; }
}
__declspec(dllexport) bool ShouldCenterMouse() { bool r = g_shouldCenterMouse; g_shouldCenterMouse = false; return r; }
__declspec(dllexport) void SetUsername(const char* name) { if(name) { strncpy(g_username, name, 63); g_username[63] = '\0'; } }
__declspec(dllexport) int GetLastFinalScore() { return g_lastFinalScore; }
__declspec(dllexport) void SaveGameData() { /* TODO: implement */ }
__declspec(dllexport) bool LoadGameData() { /* TODO: implement */ return false; }

}

// ══════════════════════════════════════════════════════════════════════════════
// UI IMPLEMENTATION
// ══════════════════════════════════════════════════════════════════════════════

static void LoadUIAssets() {
    if (g_uiAssetsLoaded) return;
    
    printf("[LoadUIAssets] Loading UI textures...\n");
    
    // Try multiple paths
    const char* uiPaths[] = { "images/UI.png", "Data/games/CyberTrain/images/UI.png", "../../images/UI.png" };
    const char* cursorPaths[] = { "images/mouse_cursor.png", "Data/games/CyberTrain/images/mouse_cursor.png", "../../images/mouse_cursor.png" };
    
    // Load UI BG
    for (int i = 0; i < 3; i++) {
        if (FileExists(uiPaths[i])) {
            g_texUI = LoadTexture(uiPaths[i]);
            if (g_texUI.id != 0) {
                printf("[LoadUIAssets] Loaded UI BG from %s (%dx%d)\n", uiPaths[i], g_texUI.width, g_texUI.height);
                // Set texture filter to bilinear for smoother scaling if needed, or point for pixel art
                SetTextureFilter(g_texUI, TEXTURE_FILTER_POINT); 
                break;
            }
        }
    }
    
    // Load Cursor
    for (int i = 0; i < 3; i++) {
        if (FileExists(cursorPaths[i])) {
            g_texCursor = LoadTexture(cursorPaths[i]);
            if (g_texCursor.id != 0) {
                printf("[LoadUIAssets] Loaded Cursor from %s (%dx%d)\n", cursorPaths[i], g_texCursor.width, g_texCursor.height);
                SetTextureFilter(g_texCursor, TEXTURE_FILTER_POINT);
                break;
            }
        }
    }
    
    if (g_texUI.id == 0) printf("[LoadUIAssets] WARNING: Failed to load UI.png\n");
    else g_uiAssetsLoaded = true;
}

static void UnloadUIAssets() {
    if (g_texUI.id != 0) UnloadTexture(g_texUI);
    if (g_texCursor.id != 0) UnloadTexture(g_texCursor);
    g_texUI = { 0 };
    g_texCursor = { 0 };
    g_uiAssetsLoaded = false;
}

static void DrawUIOverlay() {
    if (!g_uiAssetsLoaded) return;

    // Use render dimensions to ensure UI matches BBS screen dimensions exactly
    int sw = g_renderWidth;
    int sh = g_renderHeight;
    
    // Draw UI background scaled to match BBS screen dimensions
    // UI.png should be designed to match the BBS screen size (BBS_WIDTH x BBS_HEIGHT)
    Rectangle src = { 0, 0, (float)g_texUI.width, (float)g_texUI.height };
    Rectangle dst = { 0, 0, (float)sw, (float)sh };
    DrawTexturePro(g_texUI, src, dst, {0,0}, 0.0f, WHITE);
    
    // Update g_viewfinderRect based on scale?
    // If we stretch the UI, we must stretch the viewfinder rect too.
    // Original UI size = ? (we don't know until loaded, but let's assume the user provided values match the image)
    // g_viewfinderRect = { 135, 115, 930, 485 };
    // We need to scale this rect relative to the screen size vs original text size.
    // Let's assume the original image size corresponds to the coordinates.
    // If g_texUI is loaded, we can calculate ratios.
    if (g_texUI.width > 0 && g_texUI.height > 0) {
        float scaleX = (float)sw / (float)g_texUI.width;
        float scaleY = (float)sh / (float)g_texUI.height;
        
        // Transform the hardcoded viewfinder rect to current screen space
        // Base coords are 135, 115, 930(w), 485(h)
        Rectangle scaledViewfinder = {
            135.0f * scaleX,
            115.0f * scaleY,
            930.0f * scaleX,
            485.0f * scaleY
        };
        
        // Debug draw viewfinder bounds (toggle via key?)
        // DrawRectangleLinesEx(scaledViewfinder, 1, RED);
        
        // Update global mouse-over-UI state
        Vector2 m = CustomGetMousePosition();
        if (CheckCollisionPointRec(m, scaledViewfinder)) {
            g_isMouseOverUI = false; // Inside viewfinder = interacting with world
        } else {
            g_isMouseOverUI = true; // Outside viewfinder = interacting with UI
        }
    }
}

static void DrawCustomCursor() {
    // Always hide system cursor (it disappears in 3D environment)
    if (IsCursorHidden() == false) HideCursor();
    
    Vector2 cursorPos;
    bool shouldShowCursor = false;
    
    // In map mode, always show cursor at mouse position
    if (g_mapMode) {
        cursorPos = CustomGetMousePosition();
        shouldShowCursor = true;
    }
    // In 3D mode
    else {
        if (g_isMouseOverUI) {
            // When hovering over non-transparent UI areas, cursor is visible at mouse position
            cursorPos = CustomGetMousePosition();
            shouldShowCursor = true;
        } else {
            // When in 3D viewport, cursor follows mouse position directly
            // The 3D world position (g_mouseWorldPos) is already synced with the mouse ray,
            // so we use the actual mouse screen position to keep cursor aligned with what the user sees
            cursorPos = CustomGetMousePosition();
            shouldShowCursor = true;
        }
    }
    
    // Draw cursor when it should be visible
    if (shouldShowCursor) {
        if (g_texCursor.id != 0) {
            DrawTexture(g_texCursor, (int)cursorPos.x, (int)cursorPos.y, WHITE);
        } else {
            // Fallback cursor
            DrawCircleV(cursorPos, 5, RED);
        }
    }
}

// ══════════════════════════════════════════════════════════════════════════════
// GAME LOOP BODY - Called once per frame by UpdateFrame() or main()
// This is the heart of the game - all rendering and logic happens here
// ══════════════════════════════════════════════════════════════════════════════

static void GameLoopBody() {
    // Toggle 2D map view (disabled when modal is open)
    if (CustomIsKeyPressed(KEY_M) && g_lineModal.state == LineModalState::None) {
        g_mapMode = !g_mapMode;
        // Recenter map to current 3D camera target when opening
        if (g_mapMode) {
            g_mapCamera.target = WorldToMap(g_camera.target);
        }
    }

    // Update map camera controls (pan/zoom)
    float deltaTime = GetFrameTime();
    if (deltaTime <= 0.0f || deltaTime > 0.1f) deltaTime = 1.0f/60.0f;
    
    // Handle spacebar to cycle game speed
    if (CustomIsKeyPressed(KEY_SPACE)) {
        g_currentGameSpeed = (g_currentGameSpeed + 1) % 5;
    }
        
    // Calculate scaled delta time based on game speed
    float timeScale = GetGameTimeScale();
    float scaledDeltaTime = deltaTime * timeScale;

    // Advance in-game clock (always advances, even in map mode) - uses scaled time
    float prevDayClock = g_dayClock;
    g_dayClock += scaledDeltaTime;

    int dayCyclesPassed = 0;
    if (g_dayCycleSeconds > 0.0f) {
        dayCyclesPassed = (int)floorf((prevDayClock + scaledDeltaTime) / g_dayCycleSeconds);
        if (g_dayClock >= g_dayCycleSeconds) g_dayClock = fmodf(g_dayClock, g_dayCycleSeconds);
    }

    // Factory production: when a new day-cycle begins, each factory produces 2 cargo into its connected depot cluster.
    if (dayCyclesPassed > 0 && !g_placedFactories.empty() && !g_placedPlatforms.empty()) {
        int producedPerFactory = 2 * dayCyclesPassed;

        for (const auto& f : g_placedFactories) {
            // Find depots adjacent to this factory footprint (same logic as HasAdjacentDepotForFactory)
            float half = g_gridSpacing * 2.0f;
            float minX = f.position.x - half;
            float maxX = f.position.x + half;
            float minZ = f.position.z - half;
            float maxZ = f.position.z + half;

            std::vector<int> adjacentDepotIdxs;
            adjacentDepotIdxs.reserve(8);
            for (int i = 0; i < (int)g_placedPlatforms.size(); i++) {
                const auto& p = g_placedPlatforms[i];
                if (!p.isDepot) continue;

                float dx = 0.0f;
                if (p.position.x < minX) dx = minX - p.position.x;
                else if (p.position.x > maxX) dx = p.position.x - maxX;

                float dz = 0.0f;
                if (p.position.z < minZ) dz = minZ - p.position.z;
                else if (p.position.z > maxZ) dz = p.position.z - maxZ;

                float dist = sqrtf(dx*dx + dz*dz);
                if (dist <= g_gridSpacing * 1.1f) adjacentDepotIdxs.push_back(i);
            }

            if (adjacentDepotIdxs.empty()) continue;

            // Choose the best adjacent depot cluster (most free space)
            int bestStartIdx = adjacentDepotIdxs[0];
            int bestFree = -1;
            for (int startIdx : adjacentDepotIdxs) {
                std::vector<int> cluster = GetDepotClusterIndices(g_placedPlatforms, startIdx, g_gridSpacing);
                if (cluster.empty()) continue;
                int cargo = GetClusterCargoTotal(g_placedPlatforms, cluster);
                int cap = GetClusterCapacityTotal(cluster);
                int free = cap - cargo;
                if (free > bestFree) { bestFree = free; bestStartIdx = startIdx; }
            }

            if (bestFree <= 0) continue;

                std::vector<int> bestCluster = GetDepotClusterIndices(g_placedPlatforms, bestStartIdx, g_gridSpacing);
                if (bestCluster.empty()) continue;

                int add = std::min(producedPerFactory, bestFree);
                AddCargoToCluster(g_placedPlatforms, bestCluster, add);
            }
        }

        // Compute day phase + scene tinting
        // Morning [0..1/3), Noon [1/3..2/3), Night [2/3..1)
        float dayT = (g_dayCycleSeconds > 0.0f) ? (g_dayClock / g_dayCycleSeconds) : 0.0f;
        int phase = (dayT < (1.0f / 3.0f)) ? 0 : (dayT < (2.0f / 3.0f) ? 1 : 2);
        float phaseT = (phase == 0) ? (dayT * 3.0f) : (phase == 1 ? ((dayT - 1.0f/3.0f) * 3.0f) : ((dayT - 2.0f/3.0f) * 3.0f));

        const char* phaseName = (phase == 0) ? "MORNING" : (phase == 1 ? "NOON" : "NIGHT");

        // Visual palette
        Color skyMorning = (Color){ 14, 10, 22, 255 };
        Color skyNoon    = (Color){ 28, 28, 36, 255 };
        Color skyNight   = (Color){ 0,  0,  0,  255 };
        Color skyColor = (phase == 0) ? LerpColor(skyMorning, skyNoon, phaseT)
                        : (phase == 1) ? LerpColor(skyNoon, skyNight, phaseT)
                                       : LerpColor(skyNight, skyMorning, phaseT);

        float brightness = (phase == 0) ? (0.75f + 0.20f * phaseT)   // 0.75 -> 0.95
                        : (phase == 1) ? (0.95f - 0.35f * phaseT)   // 0.95 -> 0.60
                                       : (0.60f + 0.15f * phaseT);  // 0.60 -> 0.75
        Color nightBlue = (Color){ 0, 0, (unsigned char)(phase == 1 ? (int)(12 * phaseT) : (phase == 2 ? 12 : 0)), 255 };

        Color g_platformColorEff = AddColor(MulColor(g_platformColor, brightness), nightBlue);
        Color g_stationColorEff  = AddColor(MulColor(g_stationColor,  brightness), nightBlue);
        Color g_pointsColorEff   = AddColor(MulColor(g_pointsColor,   brightness), nightBlue);
        if (g_mapMode) {
            // Keep offset centered in case window size changes
            g_mapCamera.offset = { (float)g_renderWidth * 0.5f, (float)g_renderHeight * 0.5f };

            // Zoom with mouse wheel
            float wheel = CustomGetMouseWheelMove();
            if (wheel != 0.0f) {
                float zoomFactor = 1.0f + wheel * 0.15f;
                g_mapCamera.zoom = Clamp(g_mapCamera.zoom * zoomFactor, 1.0f, 40.0f);
            }

            // Pan with arrows or WASD (faster when zoomed in) - not affected by game speed
            float panSpeed = (250.0f / g_mapCamera.zoom) * deltaTime;
            if (CustomIsKeyDown(KEY_LEFT) || CustomIsKeyDown(KEY_A)) g_mapCamera.target.x -= panSpeed;
            if (CustomIsKeyDown(KEY_RIGHT) || CustomIsKeyDown(KEY_D)) g_mapCamera.target.x += panSpeed;
            if (CustomIsKeyDown(KEY_UP) || CustomIsKeyDown(KEY_W)) g_mapCamera.target.y -= panSpeed;
            if (CustomIsKeyDown(KEY_DOWN) || CustomIsKeyDown(KEY_S)) g_mapCamera.target.y += panSpeed;

            // Pan by dragging with middle mouse
            if (CustomIsMouseButtonDown(MOUSE_BUTTON_MIDDLE)) {
                Vector2 d = CustomGetMouseDelta();
                g_mapCamera.target.x -= d.x / g_mapCamera.zoom;
                g_mapCamera.target.y -= d.y / g_mapCamera.zoom;
            }
        }

        // Get mouse position in 3D world space
        Vector2 mousePos = CustomGetMousePosition();
        Ray mouseRay = GetMouseRay(mousePos, g_camera);
        
        // Calculate intersection with ground plane (y=0) manually
        if (mouseRay.direction.y < -0.0001f || mouseRay.direction.y > 0.0001f) {
            float t = -mouseRay.position.y / mouseRay.direction.y;
            
            if (t > 0.0f) {
                Vector3 hitPoint = Vector3Add(mouseRay.position, Vector3Scale(mouseRay.direction, t));
                
                // Snap to center of grid squares (not intersections)
                float gridCellX = floorf(hitPoint.x / g_gridSpacing);
                float gridCellZ = floorf(hitPoint.z / g_gridSpacing);
                float snappedX = gridCellX * g_gridSpacing + g_gridSpacing / 2.0f;
                float snappedZ = gridCellZ * g_gridSpacing + g_gridSpacing / 2.0f;
                
                // For factory placement (4x4 footprint), center should snap to grid intersections
                if (g_factoryPlacementMode) {
                    float snappedXI = roundf(hitPoint.x / g_gridSpacing) * g_gridSpacing;
                    float snappedZI = roundf(hitPoint.z / g_gridSpacing) * g_gridSpacing;
                    g_mouseWorldPos = { snappedXI, 0.0f, snappedZI };
                }
                // For bureau placement (2x2 footprint), center should snap to grid intersections
                else if (g_bureauPlacementMode) {
                    float snappedXI = roundf(hitPoint.x / g_gridSpacing) * g_gridSpacing;
                    float snappedZI = roundf(hitPoint.z / g_gridSpacing) * g_gridSpacing;
                    g_mouseWorldPos = { snappedXI, 0.0f, snappedZI };
                }
                // For station placement, if length is 4, center should be between grid squares
                // or offset so it spans exactly 4 grid cells
                else if (g_stationPlacementMode) {
                    if (g_stationHorizontal) {
                        // Offset by 1.5 grid squares to center the 4-square station
                        g_mouseWorldPos = { snappedX + g_gridSpacing * 1.5f, 0.0f, snappedZ };
                    } else {
                        g_mouseWorldPos = { snappedX, 0.0f, snappedZ + g_gridSpacing * 1.5f };
                    }
                } else {
                    g_mouseWorldPos = { snappedX, 0.0f, snappedZ };
                }
            }
        }
        
        // Handle T key to toggle train placement mode (disabled in map mode and when modal is open)
        if (!g_mapMode && g_lineModal.state == LineModalState::None && CustomIsKeyPressed(KEY_T)) {
            g_trainPlacementMode = !g_trainPlacementMode;
            if (g_trainPlacementMode) { g_stationPlacementMode = false; g_cargoTrainPlacementMode = false; g_depotPlacementMode = false; g_factoryPlacementMode = false; g_bureauPlacementMode = false; g_demolishMode = false; }
        }

        // Handle C key to toggle cargo train placement mode (disabled in map mode and when modal is open)
        if (!g_mapMode && g_lineModal.state == LineModalState::None && CustomIsKeyPressed(KEY_C)) {
            if (!g_cargoTrainPlacementMode) {
                g_cargoTrainPlacementMode = true;
                g_cargoPlacementTrailers = 1;
                g_stationPlacementMode = false;
                g_trainPlacementMode = false;
                g_depotPlacementMode = false;
                g_factoryPlacementMode = false;
                g_bureauPlacementMode = false;
                g_demolishMode = false;
            } else {
                // Already in cargo mode: cycle number of trailers
                g_cargoPlacementTrailers++;
                if (g_cargoPlacementTrailers > 3) g_cargoPlacementTrailers = 1;
            }
        }

        // Handle D key to toggle Materials-Depot placement mode (disabled in map mode and when modal is open)
        if (!g_mapMode && g_lineModal.state == LineModalState::None && CustomIsKeyPressed(KEY_D)) {
            g_depotPlacementMode = !g_depotPlacementMode;
            if (g_depotPlacementMode) { g_stationPlacementMode = false; g_trainPlacementMode = false; g_cargoTrainPlacementMode = false; g_factoryPlacementMode = false; g_bureauPlacementMode = false; g_demolishMode = false; }
        }

        // Handle F key to toggle Factory placement mode (disabled in map mode and when modal is open)
        if (!g_mapMode && g_lineModal.state == LineModalState::None && CustomIsKeyPressed(KEY_F)) {
            g_factoryPlacementMode = !g_factoryPlacementMode;
            if (g_factoryPlacementMode) { g_stationPlacementMode = false; g_trainPlacementMode = false; g_cargoTrainPlacementMode = false; g_depotPlacementMode = false; g_bureauPlacementMode = false; g_demolishMode = false; }
        }
        
        // Handle B key to toggle Bureau placement mode (disabled in map mode and when modal is open)
        if (!g_mapMode && g_lineModal.state == LineModalState::None && CustomIsKeyPressed(KEY_B)) {
            if (!g_bureauPlacementMode) {
                g_bureauPlacementMode = true;
                g_bureauFloorIndex = 0; // Start at 1 floor
            } else {
                // Cycle through floor options
                g_bureauFloorIndex = (g_bureauFloorIndex + 1) % g_bureauFloorOptions.size();
            }
            if (g_bureauPlacementMode) { g_stationPlacementMode = false; g_trainPlacementMode = false; g_cargoTrainPlacementMode = false; g_depotPlacementMode = false; g_factoryPlacementMode = false; g_demolishMode = false; }
        }
        
        // Handle S key to toggle station placement mode (disabled in map mode and when modal is open)
        if (!g_mapMode && g_lineModal.state == LineModalState::None && CustomIsKeyPressed(KEY_S)) {
            g_stationPlacementMode = !g_stationPlacementMode;
            if (g_stationPlacementMode) { g_trainPlacementMode = false; g_cargoTrainPlacementMode = false; g_depotPlacementMode = false; g_factoryPlacementMode = false; g_bureauPlacementMode = false; g_demolishMode = false; }
        }

        // Handle R key to rotate station (disabled in map mode and when modal is open)
        if (!g_mapMode && g_lineModal.state == LineModalState::None && CustomIsKeyPressed(KEY_R)) {
            g_stationHorizontal = !g_stationHorizontal;
        }
        
        // Handle ESC key to deselect train
        if (CustomIsKeyPressed(KEY_ESCAPE)) {
            g_selectedTrainIndex = -1;
        }
        
        // Handle mouse click to place platform, train, select train, configure junction, or demolish (disabled in map mode and when modal is open)
        if (!g_mapMode && g_lineModal.state == LineModalState::None && CustomIsMouseButtonPressed(MOUSE_BUTTON_LEFT)) {
            bool clickHandled = false;
            
            // Demolish mode: remove anything at the clicked grid square
            if (g_demolishMode) {
                bool demolished = false;
                
                // Check for platforms/depots/stations at this position
                for (int i = (int)g_placedPlatforms.size() - 1; i >= 0; i--) {
                    float dist = Vector3Distance(g_mouseWorldPos, g_placedPlatforms[i].position);
                    if (dist < g_gridSpacing * 0.6f) {
                        g_placedPlatforms.erase(g_placedPlatforms.begin() + i);
                        demolished = true;
                        // Rebuild train paths since network changed
                        for (auto& train : g_placedTrains) {
                            RebuildTrainPath(train, g_placedPlatforms, g_gridSpacing);
                        }
                        break;
                    }
                }
                
                // Check for factories at this position
                if (!demolished) {
                    float factoryHalf = g_gridSpacing * 2.0f;
                    for (int i = (int)g_placedFactories.size() - 1; i >= 0; i--) {
                        float dx = fabsf(g_placedFactories[i].position.x - g_mouseWorldPos.x);
                        float dz = fabsf(g_placedFactories[i].position.z - g_mouseWorldPos.z);
                        if (dx <= factoryHalf && dz <= factoryHalf) {
                            g_placedFactories.erase(g_placedFactories.begin() + i);
                            demolished = true;
                            break;
                        }
                    }
                }
                
                // Check for bureaus at this position
                if (!demolished) {
                    float bureauHalf = g_gridSpacing * 1.0f;
                    for (int i = (int)g_placedBureaus.size() - 1; i >= 0; i--) {
                        float dx = fabsf(g_placedBureaus[i].position.x - g_mouseWorldPos.x);
                        float dz = fabsf(g_placedBureaus[i].position.z - g_mouseWorldPos.z);
                        if (dx <= bureauHalf && dz <= bureauHalf) {
                            g_placedBureaus.erase(g_placedBureaus.begin() + i);
                            demolished = true;
                            break;
                        }
                    }
                }
                
                // Check for trains at this position
                if (!demolished) {
                    for (int i = (int)g_placedTrains.size() - 1; i >= 0; i--) {
                        // Check if clicking on any platform the train is on
                        for (const auto& pathPos : g_placedTrains[i].path) {
                            if (Vector3Distance(g_mouseWorldPos, (Vector3){pathPos.x, 0, pathPos.z}) < g_gridSpacing * 0.6f) {
                                g_placedTrains.erase(g_placedTrains.begin() + i);
                                if (g_selectedTrainIndex == i) g_selectedTrainIndex = -1;
                                else if (g_selectedTrainIndex > i) g_selectedTrainIndex--;
                                demolished = true;
                                break;
                            }
                        }
                        if (demolished) break;
                    }
                }
                
                // Deduct credits if something was demolished
                if (demolished && g_playerCredits >= 100) {
                    g_playerCredits -= 100;
                }
                
                clickHandled = true;
            }
            
            // First, check if clicking on an existing train to select it
            if (!clickHandled && !g_trainPlacementMode && !g_stationPlacementMode && !g_bureauPlacementMode && !g_demolishMode) {
                for (size_t i = 0; i < g_placedTrains.size(); i++) {
                    // Check if clicking near the train's hotspot (cargo = back car)
                    PathPoint hot = GetTrainHotspotPoint(g_placedTrains[i], g_gridSpacing);
                    Vector3 hotXZ = { hot.position.x, 0.0f, hot.position.z };
                    if (Vector3Distance(g_mouseWorldPos, hotXZ) < g_gridSpacing * 2.5f) {
                        // Check if we're clicking on any platform the train is on
                        for (const auto& pathPos : g_placedTrains[i].path) {
                            if (Vector3Distance(g_mouseWorldPos, (Vector3){pathPos.x, 0, pathPos.z}) < g_gridSpacing * 0.6f) {
                                if (g_selectedTrainIndex == (int)i) {
                                    g_selectedTrainIndex = -1; // Deselect if clicking same train
                                } else {
                                    g_selectedTrainIndex = (int)i; // Select this train
                                }
                                clickHandled = true;
                                break;
                            }
                        }
                    }
                    if (clickHandled) break;
                }
            }
            
            // If a train is selected, check if clicking on a junction to configure it
            if (!clickHandled && g_selectedTrainIndex >= 0 && g_selectedTrainIndex < (int)g_placedTrains.size()) {
                // Check if clicking on a Points-Platform
                for (const auto& platform : g_placedPlatforms) {
                    if (Vector3Distance(g_mouseWorldPos, platform.position) < g_gridSpacing * 0.6f) {
                        PlatformType pType = GetPlatformType(platform.position, g_placedPlatforms, g_gridSpacing);
                        if (pType == PlatformType::Points) {
                            // Cycle the junction setting for this train
                            std::vector<Vector3> adjacent = GetSortedAdjacentPositions(platform.position, g_placedPlatforms, g_gridSpacing);
            int numExits = (int)adjacent.size();
            int numPairs = NumJunctionPairs(numExits);
            if (numPairs <= 0) numPairs = 1;
                            int currentSetting = g_placedTrains[g_selectedTrainIndex].GetJunctionSetting(platform.position.x, platform.position.z);
            int newSetting = (currentSetting + 1);
            if (newSetting < 0) newSetting = 0;
            newSetting = newSetting % numPairs;
                            g_placedTrains[g_selectedTrainIndex].SetJunctionSetting(platform.position.x, platform.position.z, newSetting);
                            
                            // Rebuild the train's path with the new junction settings.
                            // NOTE: Use the shared helper to correctly account for train length (cargo vs passenger),
                            // loop paths, and progress snapping.
                            PlacedTrain& train = g_placedTrains[g_selectedTrainIndex];
                            if (!train.path.empty()) {
                                (void)RebuildTrainPath(train, g_placedPlatforms, g_gridSpacing);
                            }
                            
                            clickHandled = true;
                            break;
                        }
                    }
                }
            }
            
            if (!clickHandled && (g_trainPlacementMode || g_cargoTrainPlacementMode)) {
                // Place passenger or cargo train
                // Check if the platform under mouse is a station
                const PlacedPlatform* targetPlatform = nullptr;
                for (const auto& p : g_placedPlatforms) {
                    if (Vector3Distance(g_mouseWorldPos, p.position) < 0.1f) {
                        targetPlatform = &p;
                        break;
                    }
                }

                if (targetPlatform && targetPlatform->isStation) {
                    // Check if there are at least 4 connected platforms
                    Vector3 pathCenter;
                    
                    if (CheckConnectedPlatforms(g_mouseWorldPos, g_placedPlatforms, g_gridSpacing, pathCenter)) {
                        // Build path through connected platforms
                        std::vector<Vector3> path = BuildPlatformPath(g_mouseWorldPos, g_placedPlatforms, g_gridSpacing);
                        
                        if (path.size() >= 4) {
                            // Spawn ONLY on the clicked station platform (never at "path center")
                            Vector3 spawnPlatformPos = targetPlatform->position;
                            float platformTopY = GetPlatformTopY(spawnPlatformPos.y, g_gridSpacing);
                            std::vector<Vector3> pathWithY;
                            for (const auto& pos : path) {
                                float topY = GetPlatformTopY(pos.y, g_gridSpacing);
                                pathWithY.push_back({ pos.x, topY, pos.z });
                            }
                            
                            float totalLength = GetPathLength(pathWithY);
                            
                            PlacedTrain newTrain;
                            newTrain.id = g_nextTrainId++;
                            newTrain.type = g_cargoTrainPlacementMode ? PlacedTrain::TrainType::Cargo : PlacedTrain::TrainType::Passenger;
                            newTrain.cargoTrailers = g_cargoTrainPlacementMode ? g_cargoPlacementTrailers : 1;
                            newTrain.position = { spawnPlatformPos.x, platformTopY, spawnPlatformPos.z };
                            newTrain.path = pathWithY;
                            newTrain.direction = 1.0f;
                            newTrain.pathLength = totalLength;
                            EnsureCargoArrays(newTrain);
                            if (newTrain.type == PlacedTrain::TrainType::Cargo) {
                                // Start loaded so players can deliver materials immediately
                                newTrain.cargoTotal = newTrain.cargoTrailers * 2;
                            }

                            // Set progress so the train is centered on the station tile it was placed on
                            float spawnProgress = GetClosestDistanceAlongPath(pathWithY, newTrain.position);
                            float minProgress = 0.0f;
                            float maxProgress = newTrain.pathLength;
                            GetTrainProgressLimitsFrontCar(newTrain, g_gridSpacing, newTrain.pathLength, minProgress, maxProgress);
                            if (maxProgress <= minProgress) {
                                newTrain.pathProgress = newTrain.pathLength / 2.0f;
                                newTrain.direction = 0.0f;
                            } else if (IsLoopPath(newTrain.path)) {
                                newTrain.pathProgress = WrapDistance(spawnProgress, newTrain.pathLength);
                            } else {
                                newTrain.pathProgress = Clamp(spawnProgress, minProgress, maxProgress);
                            }

                            // Snap the train center to the path at that progress
                            PathPoint centerPoint = GetPathPoint(newTrain.path, newTrain.pathProgress);
                            newTrain.position = centerPoint.position;
                            
                            bool canPlace = true;
                            float placeRadius = GetTrainTotalLength(newTrain, g_gridSpacing) * 0.6f;
                            for (const auto& existingTrain : g_placedTrains) {
                                float otherRadius = GetTrainTotalLength(existingTrain, g_gridSpacing) * 0.6f;
                                if (Vector3Distance(newTrain.position, existingTrain.position) < (placeRadius + otherRadius)) {
                                    canPlace = false;
                                    break;
                                }
                            }
                            
                            if (canPlace) {
                                g_placedTrains.push_back(newTrain);
                                // Auto-select the newly placed train
                                g_selectedTrainIndex = (int)g_placedTrains.size() - 1;
                            }
                        }
                    }
                }
            } else if (!clickHandled && g_stationPlacementMode) {
                // Place Station-Track
                bool canPlace = true;
                std::vector<Vector3> segments;
                for (int i = 0; i < 4; i++) {
                    Vector3 pos = g_mouseWorldPos;
                    if (g_stationHorizontal) pos.x += (i - 1.5f) * g_gridSpacing;
                    else pos.z += (i - 1.5f) * g_gridSpacing;
                    segments.push_back(pos);

                    // Check overlap with buildings
                    Building testBuilding;
                    testBuilding.position = pos;
                    testBuilding.size = { g_gridSpacing, g_gridSpacing, g_gridSpacing };
                    if (overlapsWithAny(testBuilding, g_buildings)) canPlace = false;

                    // Check overlap with other platforms
                    for (const auto& p : g_placedPlatforms) {
                        if (Vector3Distance(pos, p.position) < g_gridSpacing * 0.9f) canPlace = false;
                    }
                }

                // Check credits (Stations cost 1000 credits)
                if (canPlace && g_playerCredits < 1000) {
                    canPlace = false;
                }

                if (canPlace) {
                    g_playerCredits -= 1000; // Deduct station cost
                    for (int i = 0; i < 4; i++) {
                        PlacedPlatform p;
                        p.position = segments[i];
                        p.isStation = true;
                        p.isHorizontal = g_stationHorizontal;
                        p.stationPart = i;
                        p.isDepot = false;
                        p.depotCargo = 0;
                        g_placedPlatforms.push_back(p);
                        
                        // Spawn build particles for each station segment
                        SpawnBuildParticles(segments[i], g_stationColor, g_gridSpacing);
                    }

                    // Network expanded: rebuild existing train paths so they can use newly connected track
                    for (auto& train : g_placedTrains) {
                        RebuildTrainPath(train, g_placedPlatforms, g_gridSpacing);
                    }
                }
            } else if (!clickHandled && g_depotPlacementMode) {
                // Place Materials-Depot
                bool canPlace = true;

                // Check overlap with buildings
                Building testBuilding;
                testBuilding.position = g_mouseWorldPos;
                testBuilding.size = { g_gridSpacing, g_gridSpacing, g_gridSpacing };
                if (overlapsWithAny(testBuilding, g_buildings)) {
                    canPlace = false;
                }

                // Check overlap with other placed platforms/depots
                for (const auto& placed : g_placedPlatforms) {
                    float dist = Vector3Distance(g_mouseWorldPos, placed.position);
                    if (dist < g_gridSpacing * 0.9f) {
                        canPlace = false;
                        break;
                    }
                }

                // Must be connected (directly or via a depot chain) to at least one station tile
                if (canPlace && !CanPlaceDepotAt(g_mouseWorldPos, g_placedPlatforms, g_gridSpacing)) {
                    canPlace = false;
                }

                // Check credits (Depots cost 1500 credits)
                if (canPlace && g_playerCredits < 1500) {
                    canPlace = false;
                }

                if (canPlace) {
                    g_playerCredits -= 1500; // Deduct depot cost
                    PlacedPlatform depot;
                    depot.position = g_mouseWorldPos;
                    depot.isStation = false;
                    depot.isHorizontal = false;
                    depot.stationPart = 0;
                    depot.isDepot = true;
                    depot.depotCargo = 0;
                    g_placedPlatforms.push_back(depot);
                    
                    // Spawn build particles
                    Color depotColor = (Color){ 160, 160, 160, 220 };
                    SpawnBuildParticles(g_mouseWorldPos, depotColor, g_gridSpacing);
                }
            } else if (!clickHandled && g_factoryPlacementMode) {
                // Place Factory (must be adjacent to a depot)
                bool canPlace = true;

                Vector3 factoryPos = g_mouseWorldPos; // already snapped to grid cell center

                // Overlap with skyline buildings (treat footprint as 4x4 tile AABB)
                float half = g_gridSpacing * 2.0f;
                BoundingBox factoryBox = {
                    (Vector3){ factoryPos.x - half, 0.0f, factoryPos.z - half },
                    (Vector3){ factoryPos.x + half, g_gridSpacing * 3.0f, factoryPos.z + half }
                };

                for (const auto& b : g_buildings) {
                    BoundingBox bb = {
                        (Vector3){ b.position.x - b.size.x/2.0f, b.position.y - b.size.y/2.0f, b.position.z - b.size.z/2.0f },
                        (Vector3){ b.position.x + b.size.x/2.0f, b.position.y + b.size.y/2.0f, b.position.z + b.size.z/2.0f }
                    };
                    if (CheckCollisionBoxes(factoryBox, bb)) { canPlace = false; break; }
                }

                // Overlap with any platform/depot tile inside footprint (or touching)
                if (canPlace) {
                    for (const auto& p : g_placedPlatforms) {
                        if (p.position.x >= factoryPos.x - half - 0.1f && p.position.x <= factoryPos.x + half + 0.1f &&
                            p.position.z >= factoryPos.z - half - 0.1f && p.position.z <= factoryPos.z + half + 0.1f) {
                            canPlace = false;
                            break;
                        }
                    }
                }

                // Overlap with other factories (simple AABB)
                if (canPlace) {
                    for (const auto& f : g_placedFactories) {
                        if (fabsf(f.position.x - factoryPos.x) <= (half * 2.0f) &&
                            fabsf(f.position.z - factoryPos.z) <= (half * 2.0f)) {
                            canPlace = false;
                            break;
                        }
                    }
                }

                // Must be adjacent to a depot
                if (canPlace && !HasAdjacentDepotForFactory(factoryPos, g_placedPlatforms, g_gridSpacing)) {
                    canPlace = false;
                }

                // Check credits (Factories cost 10,000 credits)
                if (canPlace && g_playerCredits < 10000) {
                    canPlace = false;
                }

                if (canPlace) {
                    g_playerCredits -= 10000; // Deduct factory cost
                    g_placedFactories.push_back({ factoryPos });
                    
                    // Spawn build particles
                    Color factoryColor = (Color){ 130, 130, 130, 220 };
                    SpawnBuildParticles(factoryPos, factoryColor, g_gridSpacing);
                }
            } else if (!clickHandled && g_bureauPlacementMode) {
                // Place Bureau
                bool canPlace = true;
                Vector3 bureauPos = g_mouseWorldPos; // already snapped to grid intersection (2x2 footprint aligns with grid squares)
                int selectedFloors = g_bureauFloorOptions[g_bureauFloorIndex];
                
                // Bureau footprint is 1/4 factory size (2x2 tiles)
                float bureauHalf = g_gridSpacing * 1.0f; // 2x2 means half is 1 grid
                
                // Overlap with skyline buildings
                BoundingBox bureauBox = {
                    (Vector3){ bureauPos.x - bureauHalf, 0.0f, bureauPos.z - bureauHalf },
                    (Vector3){ bureauPos.x + bureauHalf, g_gridSpacing * 60.0f, bureauPos.z + bureauHalf } // Max height for 200 floors
                };
                
                for (const auto& b : g_buildings) {
                    BoundingBox bb = {
                        (Vector3){ b.position.x - b.size.x/2.0f, b.position.y - b.size.y/2.0f, b.position.z - b.size.z/2.0f },
                        (Vector3){ b.position.x + b.size.x/2.0f, b.position.y + b.size.y/2.0f, b.position.z + b.size.z/2.0f }
                    };
                    if (CheckCollisionBoxes(bureauBox, bb)) { canPlace = false; break; }
                }
                
                // Overlap with platforms/depots
                if (canPlace) {
                    for (const auto& p : g_placedPlatforms) {
                        if (p.position.x >= bureauPos.x - bureauHalf - 0.1f && p.position.x <= bureauPos.x + bureauHalf + 0.1f &&
                            p.position.z >= bureauPos.z - bureauHalf - 0.1f && p.position.z <= bureauPos.z + bureauHalf + 0.1f) {
                            canPlace = false;
                            break;
                        }
                    }
                }
                
                // Overlap with factories
                if (canPlace) {
                    float factoryHalf = g_gridSpacing * 2.0f;
                    for (const auto& f : g_placedFactories) {
                        if (fabsf(f.position.x - bureauPos.x) <= (factoryHalf + bureauHalf) &&
                            fabsf(f.position.z - bureauPos.z) <= (factoryHalf + bureauHalf)) {
                            canPlace = false;
                            break;
                        }
                    }
                }
                
                // Overlap with other bureaus
                if (canPlace) {
                    for (const auto& b : g_placedBureaus) {
                        if (fabsf(b.position.x - bureauPos.x) <= (bureauHalf * 2.0f) &&
                            fabsf(b.position.z - bureauPos.z) <= (bureauHalf * 2.0f)) {
                            canPlace = false;
                            break;
                        }
                    }
                }
                
                // Must be within 2 grid spaces of station, factory, or depot
                if (canPlace && !IsWithinTwoGridSpacesOfValidBuilding(bureauPos, g_placedPlatforms, g_placedFactories, g_gridSpacing)) {
                    canPlace = false;
                }
                
                // Check cargo requirement: 5 cargo materials within 10 grid radius
                if (canPlace && !HasEnoughCargoInRadius(bureauPos, g_placedPlatforms, g_gridSpacing, 5)) {
                    canPlace = false;
                }
                
                // Check credits: 10,000 credits per floor stage
                int costPerFloor = 10000;
                int totalCost = selectedFloors * costPerFloor;
                if (canPlace && g_playerCredits < totalCost) {
                    canPlace = false;
                }
                
                if (canPlace) {
                    // Deduct credits and cargo
                    g_playerCredits -= totalCost;
                    RemoveCargoFromRadius(bureauPos, g_placedPlatforms, g_gridSpacing, 5);
                    
                    PlacedBureau bureau;
                    bureau.position = bureauPos;
                    bureau.floors = selectedFloors;
                    g_placedBureaus.push_back(bureau);
                    
                    // Spawn build particles
                    Color bureauColor = (Color){ 0, 255, 255, 200 };
                    SpawnBuildParticles(bureauPos, bureauColor, g_gridSpacing);
                }
            } else {
                // Place platform (rail track)
                // Check if position is valid (not overlapping with buildings)
                bool canPlace = true;
                
                // Check overlap with buildings
                Building testBuilding;
                testBuilding.position = g_mouseWorldPos;
                testBuilding.size = { g_gridSpacing, g_gridSpacing, g_gridSpacing };
                if (overlapsWithAny(testBuilding, g_buildings)) {
                    canPlace = false;
                }
                
                // Check overlap with other placed platforms
                for (const auto& placed : g_placedPlatforms) {
                    float dist = Vector3Distance(g_mouseWorldPos, placed.position);
                    if (dist < g_gridSpacing * 0.9f) {
                        canPlace = false;
                        break;
                    }
                }
                
                // Check credits (Platforms cost 150 credits)
                if (canPlace && g_playerCredits < 150) {
                    canPlace = false;
                }

                if (canPlace) {
                    g_playerCredits -= 150; // Deduct platform cost
                    PlacedPlatform newPlatform;
                    newPlatform.position = g_mouseWorldPos;
                    newPlatform.isStation = false;
                    newPlatform.isHorizontal = false;
                    newPlatform.stationPart = 0;
                    newPlatform.isDepot = false;
                    newPlatform.depotCargo = 0;
                    g_placedPlatforms.push_back(newPlatform);

                    // Spawn build particles
                    SpawnBuildParticles(g_mouseWorldPos, g_platformColor, g_gridSpacing);

                    // Network expanded: rebuild existing train paths so they can use newly connected track
                    for (auto& train : g_placedTrains) {
                        RebuildTrainPath(train, g_placedPlatforms, g_gridSpacing);
                    }
                }
            }
        }
        
        // Camera controls (isometric - rotation) (disabled in map mode)
        // Calculate forward and right vectors for movement
        Vector3 forward = Vector3Normalize(Vector3Subtract(g_camera.target, g_camera.position));
        Vector3 right = Vector3Normalize(Vector3CrossProduct(forward, g_camera.up));
        
        // Zoom in/out with +/- keys (adjust distance from target) (disabled when modal is open)
        if (!g_mapMode && g_lineModal.state == LineModalState::None && (CustomIsKeyDown(KEY_EQUAL) || CustomIsKeyDown(KEY_MINUS))) {
            float zoomDirection = CustomIsKeyDown(KEY_MINUS) ? -1.0f : 1.0f; // - zooms in (closer), + zooms out (farther)
            Vector3 zoomVector = Vector3Scale(forward, g_zoomSpeed * zoomDirection);
            g_camera.position = Vector3Add(g_camera.position, zoomVector);
            // Maintain fixed altitude after zoom
            g_camera.position.y = g_cameraAltitude;
        }
        
        // Move left/right with Left/Right arrows (disabled when modal is open)
        if (!g_mapMode && g_lineModal.state == LineModalState::None && (CustomIsKeyDown(KEY_LEFT) || CustomIsKeyDown(KEY_RIGHT))) {
            bool shift = CustomIsKeyDown(KEY_LEFT_SHIFT) || CustomIsKeyDown(KEY_RIGHT_SHIFT);
            if (shift) {
                // Orbit-rotate around the target (not affected by game speed)
                float dir = CustomIsKeyDown(KEY_LEFT) ? -1.0f : 1.0f;
                g_cameraYaw += dir * g_rotateSpeed * deltaTime;
                g_camera.position.x = g_camera.target.x + sinf(g_cameraYaw) * g_cameraRadius;
                g_camera.position.z = g_camera.target.z + cosf(g_cameraYaw) * g_cameraRadius;
                g_camera.position.y = g_cameraAltitude;
            } else {
                // Pan left/right
                float moveDirection = CustomIsKeyDown(KEY_LEFT) ? -1.0f : 1.0f;
                Vector3 moveVector = Vector3Scale(right, g_moveSpeed * moveDirection);
                
                // Move both camera position and target together (panning)
                g_camera.position = Vector3Add(g_camera.position, moveVector);
                g_camera.target = Vector3Add(g_camera.target, moveVector);

                // Keep orbit parameters consistent after pan
                g_cameraYaw = atan2f(g_camera.position.x - g_camera.target.x, g_camera.position.z - g_camera.target.z);
                g_cameraRadius = sqrtf((g_camera.position.x - g_camera.target.x) * (g_camera.position.x - g_camera.target.x) +
                                     (g_camera.position.z - g_camera.target.z) * (g_camera.position.z - g_camera.target.z));
            }
        }
        
        // Move forward/backward with Up/Down arrows at fixed altitude (disabled when modal is open)
        if (!g_mapMode && g_lineModal.state == LineModalState::None && (CustomIsKeyDown(KEY_UP) || CustomIsKeyDown(KEY_DOWN))) {
            // Project forward vector onto XZ plane (remove Y component) for horizontal movement
            Vector3 forwardXZ = { forward.x, 0.0f, forward.z };
            float forwardXZLength = Vector3Length(forwardXZ);
            if (forwardXZLength > 0.0001f) {
                forwardXZ = Vector3Scale(forwardXZ, 1.0f / forwardXZLength); // Normalize
            }
            
            // Move forward or backward
            float moveDirection = CustomIsKeyDown(KEY_UP) ? 1.0f : -1.0f;
            Vector3 moveVector = Vector3Scale(forwardXZ, g_moveSpeed * moveDirection);
            
            // Move both camera position and target together, but maintain fixed altitude
            g_camera.position = Vector3Add(g_camera.position, moveVector);
            g_camera.position.y = g_cameraAltitude; // Maintain fixed altitude
            g_camera.target = Vector3Add(g_camera.target, moveVector);

            // Keep orbit parameters consistent after pan
            g_cameraYaw = atan2f(g_camera.position.x - g_camera.target.x, g_camera.position.z - g_camera.target.z);
            g_cameraRadius = sqrtf((g_camera.position.x - g_camera.target.x) * (g_camera.position.x - g_camera.target.x) +
                                 (g_camera.position.z - g_camera.target.z) * (g_camera.position.z - g_camera.target.z));
        }
        
        // Update train positions (move along platform paths)
        const float trainSpeed = 2.0f; // Units per second
        // deltaTime already computed above

        // Build station components once per frame (whole 4-tile station counts as one "station gate")
        std::vector<int> stationCompId;
        std::vector<long long> stationCompKey;
        std::vector<std::vector<int>> stationMembers;
        BuildStationComponents(g_placedPlatforms, g_gridSpacing, stationCompId, stationCompKey, stationMembers);
        
        // Detect station connections for line establishment
        // New approach: Detect when a component has 2+ stations (8+ station tiles) that aren't in a line yet
        static int previousComponentCount = 0;
        static int previousTotalStationTiles = 0;
        int currentComponentCount = (int)stationCompKey.size();
        
        // Count total station tiles across all components
        int currentTotalStationTiles = 0;
        for (const auto& members : stationMembers) {
            int stationTilesInComponent = 0;
            for (int idx : members) {
                if (idx >= 0 && idx < (int)g_placedPlatforms.size() && g_placedPlatforms[idx].isStation) {
                    stationTilesInComponent++;
                }
            }
            currentTotalStationTiles += stationTilesInComponent;
        }
        
        // Update debug variables for display
        g_debugPreviousComponentCount = previousComponentCount;
        g_debugCurrentComponentCount = currentComponentCount;
        
        // DEBUG: Show component counts
        DebugLogFormat("DEBUG: Components: prev=%d, curr=%d, station tiles: prev=%d, curr=%d, modal=%d", 
                      previousComponentCount, currentComponentCount, previousTotalStationTiles, currentTotalStationTiles, (int)g_lineModal.state);
        
        // Check each component to see if it has 2+ stations (8+ station tiles) and isn't in a line
        if (g_lineModal.state == LineModalState::None && currentComponentCount > 0) {
            for (int cid = 0; cid < (int)stationMembers.size(); cid++) {
                if (cid >= (int)stationCompKey.size()) continue;
                
                long long compKey = stationCompKey[cid];
                
                // Count station tiles in this component
                int stationTilesInComponent = 0;
                for (int idx : stationMembers[cid]) {
                    if (idx >= 0 && idx < (int)g_placedPlatforms.size() && g_placedPlatforms[idx].isStation) {
                        stationTilesInComponent++;
                    }
                }
                
                // Check if this component has 2+ stations (8+ station tiles = 2 stations of 4 tiles each)
                bool hasMultipleStations = (stationTilesInComponent >= 8);
                
                // Check if ANY platform in this component belongs to an existing line
                // AND count how many are already in the line vs how many are new
                int existingLineId = -1;
                int platformsInLine = 0;
                int totalPlatformsInComponent = 0;
                
                for (int pi = 0; pi < (int)g_placedPlatforms.size(); pi++) {
                    if (pi < (int)stationCompId.size() && stationCompId[pi] == cid && !g_placedPlatforms[pi].isDepot) {
                        totalPlatformsInComponent++;
                        for (int li = 0; li < (int)g_lines.size(); li++) {
                            if (g_lines[li].platformIndices.find(pi) != g_lines[li].platformIndices.end()) {
                                if (existingLineId < 0) existingLineId = li;
                                if (li == existingLineId) platformsInLine++;
                                break;
                            }
                        }
                    }
                }
                
                bool alreadyInLine = (existingLineId >= 0);
                // Check if there are NEW platforms in this component that aren't in the line yet
                bool hasNewPlatforms = (totalPlatformsInComponent > platformsInLine);
                
                // Check if we just added a new station (station tile count increased)
                bool stationCountIncreased = (currentTotalStationTiles > previousTotalStationTiles);
                
                DebugLogFormat("DEBUG: Component %d: %d station tiles, inLine=%d (lineId=%d), countIncreased=%d, hasNew=%d (total=%d, inLine=%d)", 
                               cid, stationTilesInComponent, alreadyInLine ? 1 : 0, existingLineId, stationCountIncreased ? 1 : 0,
                               hasNewPlatforms ? 1 : 0, totalPlatformsInComponent, platformsInLine);
                
                // Trigger modal if: component has 2+ stations, not in ANY line, and we just added stations
                if (hasMultipleStations && !alreadyInLine && stationCountIncreased) {
                    DebugLog("DEBUG: MODAL TRIGGERED! Component has 2+ stations and not in a line!");
                    
                    // New connection - show EstablishLine modal
                    DebugLogFormat("DEBUG: Showing EstablishLine modal for component %d with key %lld", cid, compKey);
                    g_lineModal.state = LineModalState::EstablishLine;
                    g_lineModal.newComponentKey = compKey;
                    // Store all connected component keys for this component
                    g_lineModal.connectedComponentKeys.clear();
                    g_lineModal.connectedComponentKeys.push_back(compKey);
                    g_lineModal.establishClicked = false;
                    g_lineModal.cancelClicked = false;
                    g_lineModal.nameCursorPos = 0;
                    memset(g_lineModal.nameBuffer, 0, sizeof(g_lineModal.nameBuffer));
                    break; // Only show one modal
                } else if (hasMultipleStations && alreadyInLine && hasNewPlatforms && stationCountIncreased) {
                    // Connecting to an existing line - show AddToLine modal
                    // ONLY triggers when there are actually NEW platforms connecting to the line
                    DebugLogFormat("DEBUG: Showing AddToLine modal for line %d (new platforms connecting)", existingLineId);
                    g_lineModal.state = LineModalState::AddToLine;
                    g_lineModal.targetLineId = existingLineId;
                    g_lineModal.newComponentKey = compKey;
                    g_lineModal.addToLineClicked = false;
                    g_lineModal.cancelClicked = false;
                    break; // Only show one modal
                }
            }
        }
        
        // Update previous state for next frame
        if (previousComponentCount != currentComponentCount) {
            DebugLogFormat("DEBUG: Component count changed: %d -> %d", previousComponentCount, currentComponentCount);
        }
        if (previousTotalStationTiles != currentTotalStationTiles) {
            DebugLogFormat("DEBUG: Station tile count changed: %d -> %d", previousTotalStationTiles, currentTotalStationTiles);
        }
        previousComponentCount = currentComponentCount;
        previousTotalStationTiles = currentTotalStationTiles;
        g_previousStationComponentKeys.assign(stationCompKey.begin(), stationCompKey.end());
        
        // Handle modal responses
        if (g_lineModal.state == LineModalState::EstablishLine && g_lineModal.establishClicked) {
            // Establish new line
            if (g_lineModal.nameCursorPos > 0) { // Only if name was entered
                Line newLine;
                newLine.id = g_nextLineId++;
                newLine.name = std::string(g_lineModal.nameBuffer);
                newLine.color = g_lineModal.selectedColor;
                // Add the component key - find the CURRENT component key from stationCompKey
                // (the modal key might be stale if components were rebuilt)
                if (g_lineModal.newComponentKey != 0) {
                    // First, try to find the component ID that matches the modal key
                    int matchingCid = -1;
                    for (int cid = 0; cid < (int)stationCompKey.size(); cid++) {
                        if (stationCompKey[cid] == g_lineModal.newComponentKey) {
                            matchingCid = cid;
                            break;
                        }
                    }
                    
                    if (matchingCid >= 0) {
                        // Found matching component, use its CURRENT key
                        long long currentKey = stationCompKey[matchingCid];
                        newLine.componentKeys.insert(currentKey);
                        
                        // Record ALL platform indices in this component (stations + track)
                        // Find all platforms that belong to this component
                        for (int pi = 0; pi < (int)g_placedPlatforms.size(); pi++) {
                            if (pi < (int)stationCompId.size() && stationCompId[pi] == matchingCid) {
                                // This platform belongs to the component
                                if (!g_placedPlatforms[pi].isDepot) { // Don't include depots
                                    newLine.platformIndices.insert(pi);
                                }
                            }
                        }
                        
                        DebugLogFormat("DEBUG: Created line '%s' with component key %lld (from cid %d, modal had %lld), %d platforms", 
                                       newLine.name.c_str(), currentKey, matchingCid, g_lineModal.newComponentKey, (int)newLine.platformIndices.size());
                    } else {
                        // Component not found, use modal key as fallback
                        newLine.componentKeys.insert(g_lineModal.newComponentKey);
                        DebugLogFormat("DEBUG: Created line '%s' with component key %lld (fallback, component not found)", 
                                       newLine.name.c_str(), g_lineModal.newComponentKey);
                    }
                    
                    // Also add all connected component keys
                    for (long long connectedKey : g_lineModal.connectedComponentKeys) {
                        newLine.componentKeys.insert(connectedKey);
                        DebugLogFormat("DEBUG: Added connected component key %lld to line", connectedKey);
                    }
                } else {
                    // Fallback: add all component keys if newComponentKey wasn't set
                    for (long long key : stationCompKey) {
                        newLine.componentKeys.insert(key);
                    }
                    DebugLogFormat("DEBUG: Created line '%s' with all component keys (fallback)", newLine.name.c_str());
                }
                newLine.stationCount = (int)newLine.componentKeys.size();
                g_lines.push_back(newLine);
                DebugLogFormat("DEBUG: Line created id=%d, name=%s, %d component keys, color R=%d G=%d B=%d A=%d", 
                               newLine.id, newLine.name.c_str(), (int)newLine.componentKeys.size(), 
                               newLine.color.r, newLine.color.g, newLine.color.b, newLine.color.a);
                // Log first few component keys for debugging
                int keyCount = 0;
                for (long long key : newLine.componentKeys) {
                    if (keyCount < 5) {
                        DebugLogFormat("DEBUG: Line %d component key %d: %lld", newLine.id, keyCount, key);
                        keyCount++;
                    }
                }
            }
            // Reset modal
            g_lineModal.state = LineModalState::None;
            g_lineModal.establishClicked = false;
            g_lineModal.cancelClicked = false;
        } else if (g_lineModal.state == LineModalState::EstablishLine && g_lineModal.cancelClicked) {
            // Continue building without establishing
            g_lineModal.state = LineModalState::None;
            g_lineModal.cancelClicked = false;
        } else if (g_lineModal.state == LineModalState::AddToLine && g_lineModal.addToLineClicked) {
            // Add to existing line - update the line to use new merged component keys AND platform indices
            if (g_lineModal.targetLineId >= 0 && g_lineModal.targetLineId < (int)g_lines.size()) {
                Line& targetLine = g_lines[g_lineModal.targetLineId];
                
                // Find which component ID contains platforms from this line
                int matchingCid = -1;
                for (int cid = 0; cid < (int)stationCompKey.size(); cid++) {
                    // Check if any platform in this component is in the line
                    for (int pi = 0; pi < (int)g_placedPlatforms.size(); pi++) {
                        if (pi < (int)stationCompId.size() && stationCompId[pi] == cid) {
                            if (targetLine.platformIndices.find(pi) != targetLine.platformIndices.end()) {
                                matchingCid = cid;
                                break;
                            }
                        }
                    }
                    if (matchingCid >= 0) break;
                }
                
                if (matchingCid >= 0) {
                    // Clear old component keys and add the merged one
                    targetLine.componentKeys.clear();
                    targetLine.componentKeys.insert(stationCompKey[matchingCid]);
                    
                    // Add ALL platform indices from the merged component (including new ones)
                    for (int pi = 0; pi < (int)g_placedPlatforms.size(); pi++) {
                        if (pi < (int)stationCompId.size() && stationCompId[pi] == matchingCid) {
                            if (!g_placedPlatforms[pi].isDepot) {
                                targetLine.platformIndices.insert(pi);
                            }
                        }
                    }
                    
                    targetLine.stationCount = (int)targetLine.componentKeys.size();
                    DebugLogFormat("DEBUG: Extended line '%s' (id=%d) to include %d platforms", 
                                   targetLine.name.c_str(), targetLine.id, (int)targetLine.platformIndices.size());
                }
            }
            g_lineModal.state = LineModalState::None;
            g_lineModal.addToLineClicked = false;
            g_lineModal.cancelClicked = false;
        } else if (g_lineModal.state == LineModalState::AddToLine && g_lineModal.cancelClicked) {
            // Continue building without adding
            g_lineModal.state = LineModalState::None;
            g_lineModal.cancelClicked = false;
        }
        
        // Update lines when components merge (even if modal wasn't shown)
        // This ensures lines stay synchronized with component changes
        // Also update platformIndices to include any new platforms in merged components
        for (Line& line : g_lines) {
            // Find which component ID contains platforms from this line
            int matchingCid = -1;
            for (int cid = 0; cid < (int)stationCompKey.size(); cid++) {
                // Check if any platform in this component is in the line
                for (int pi : line.platformIndices) {
                    if (pi < (int)stationCompId.size() && stationCompId[pi] == cid) {
                        matchingCid = cid;
                        break;
                    }
                }
                if (matchingCid >= 0) break;
            }
            
            if (matchingCid >= 0) {
                // Update component key
                line.componentKeys.clear();
                line.componentKeys.insert(stationCompKey[matchingCid]);
                
                // Update platform indices to include all platforms in this component
                // (keeps existing ones and adds any new ones from merging)
                for (int pi = 0; pi < (int)g_placedPlatforms.size(); pi++) {
                    if (pi < (int)stationCompId.size() && stationCompId[pi] == matchingCid) {
                        if (!g_placedPlatforms[pi].isDepot) {
                            line.platformIndices.insert(pi);
                        }
                    }
                }
                
                line.stationCount = (int)line.componentKeys.size();
            }
        }

        // Station prime hotspot: the "front" tile of the station component.
        // We define "front" as the station tile with the highest stationPart (0..3).
        std::vector<int> stationPrimePlatformIdx(stationMembers.size(), -1);
        std::vector<Vector3> stationPrimePos(stationMembers.size(), (Vector3){0,0,0});
        std::vector<char> stationHasAdjacentDepot(stationMembers.size(), 0);
        for (int cid = 0; cid < (int)stationMembers.size(); cid++) {
            int bestPi = -1;
            int bestPart = -999999;
            for (int pi : stationMembers[cid]) {
                if (pi < 0 || pi >= (int)g_placedPlatforms.size()) continue;
                const auto& p = g_placedPlatforms[pi];
                if (p.isDepot) continue;
                if (!p.isStation) continue;
                if (bestPi < 0 || p.stationPart > bestPart) {
                    bestPi = pi;
                    bestPart = p.stationPart;
                }
            }
            stationPrimePlatformIdx[cid] = bestPi;
            if (bestPi >= 0) stationPrimePos[cid] = g_placedPlatforms[bestPi].position;
        }

        // If ANY depot is adjacent to ANY station tile in this station component, flag it.
        for (int cid = 0; cid < (int)stationMembers.size(); cid++) {
            for (int di = 0; di < (int)g_placedPlatforms.size(); di++) {
                if (!g_placedPlatforms[di].isDepot) continue;
                for (int si : stationMembers[cid]) {
                    if (ArePlatformsAdjacent(g_placedPlatforms[di].position, g_placedPlatforms[si].position, g_gridSpacing)) {
                        stationHasAdjacentDepot[cid] = 1;
                        break;
                    }
                }
                if (stationHasAdjacentDepot[cid]) break;
            }
        }

        const long long kNoStation = (long long)0x7fffffffffffffffLL;

        auto GetStationComponentIndexAtXZ = [&](Vector3 xz) -> int {
            if (g_placedPlatforms.empty()) return -1;
            xz.y = 0.0f;
            for (int pi = 0; pi < (int)g_placedPlatforms.size(); pi++) {
                const auto& p = g_placedPlatforms[pi];
                if (p.isDepot) continue;
                if (!p.isStation) continue;
                if (Vector3Distance(xz, p.position) < 0.25f) {
                    if (pi < (int)stationCompId.size()) return stationCompId[pi];
                    return -1;
                }
            }
            return -1;
        };

        auto GetStationComponentIndexFromKey = [&](long long key) -> int {
            for (int i = 0; i < (int)stationCompKey.size(); i++) {
                if (stationCompKey[i] == key) return i;
            }
            return -1;
        };

        // Station gate logic (ONLY):
        // - Gates are CLOSED by default
        // - Gate becomes OPEN if ANY train hotspot is on the station PRIME tile hotspot
        // - If no train hotspot is on the station PRIME hotspot, the gate is CLOSED
        std::vector<char> stationGateOpen(stationMembers.size(), 0);
        
        for (auto& train : g_placedTrains) {
            if (train.path.size() < 2) {
                continue;
            }

            // Keep cargo bookkeeping consistent
            EnsureCargoArrays(train);
            
            // Update path progress based on direction (uses scaled time)
            float trainMoveDistance = train.direction * trainSpeed * scaledDeltaTime;
            train.pathProgress += trainMoveDistance;
            
            // Account for train length (differs by train type)
            float totalTrainLength = GetTrainTotalLength(train, g_gridSpacing);
            bool isLoop = IsLoopPath(train.path);
            float minProgress = 0.0f;
            float maxProgress = train.pathLength;
            GetTrainProgressLimitsFrontCar(train, g_gridSpacing, train.pathLength, minProgress, maxProgress);
            
            // If path is too short for movement, just stay centered
            if (maxProgress <= minProgress) {
                train.pathProgress = train.pathLength / 2.0f;
                train.direction = 0.0f; // Stop movement
            } else {
                if (isLoop) {
                    // Closed loop: wrap around instead of reversing
                    train.pathProgress = WrapDistance(train.pathProgress, train.pathLength);
                } else {
                    // Open path: reverse direction only at true ends (dead-ends)
                    if (train.pathProgress > maxProgress) {
                        train.pathProgress = maxProgress;
                        train.direction = -1.0f;
                    } else if (train.pathProgress < minProgress) {
                        train.pathProgress = minProgress;
                        train.direction = 1.0f;
                    }
                }
            }
            
            // Update position (center point of the train)
            PathPoint centerPoint = GetPathPoint(train.path, train.pathProgress);
            train.position = centerPoint.position;


            // Gate opens if train HOTSPOT overlaps the station PRIME hotspot tile.
            {
                PathPoint hot = GetTrainHotspotPoint(train, g_gridSpacing);
                Vector3 hotXZ = { hot.position.x, 0.0f, hot.position.z };

                for (int cid = 0; cid < (int)stationPrimePos.size(); cid++) {
                    Vector3 prime = stationPrimePos[cid];
                    Vector3 primeXZ = { prime.x, 0.0f, prime.z };
                    if (Vector3Distance(hotXZ, primeXZ) < 0.25f) {
                        stationGateOpen[cid] = 1;
                    }
                }
            }
        }

        // Cargo transfer: ONLY when station gate is OPEN (i.e., train hotspot is on station prime hotspot).
        for (auto& train : g_placedTrains) {
            if (train.type != PlacedTrain::TrainType::Cargo || train.cargoTrailers <= 0) continue;
            if (train.path.size() < 2) continue;

            // Train hotspot vs station prime hotspot determines which station (if any) we're on.
            PathPoint hot = GetTrainHotspotPoint(train, g_gridSpacing);
            Vector3 hotXZ = { hot.position.x, 0.0f, hot.position.z };

            int enteredComp = -1;
            for (int cid = 0; cid < (int)stationPrimePos.size(); cid++) {
                Vector3 prime = stationPrimePos[cid];
                Vector3 primeXZ = { prime.x, 0.0f, prime.z };
                if (Vector3Distance(hotXZ, primeXZ) < 0.25f) { enteredComp = cid; break; }
            }

            if (enteredComp < 0 || enteredComp >= (int)stationCompKey.size()) {
                train.lastTransferStationKey = kNoStation;
                continue;
            }

            long long stationKey = stationCompKey[enteredComp];

            // Gate must be OPEN for cargo transfer to happen.
            if (!(enteredComp >= 0 && enteredComp < (int)stationGateOpen.size() && stationGateOpen[enteredComp])) {
                train.lastTransferStationKey = stationKey;
                continue;
            }

            // Debounce: do at most one transfer per "on hotspot" period (prevents frame-to-frame ping-pong).
            if (train.lastTransferStationKey == stationKey) {
                continue;
            }
            train.lastTransferStationKey = stationKey;

            // Find a depot adjacent to ANY tile of this station component; depot clustering already pools all depots for this station.
            int startDepotIdx = -1;
            for (int di = 0; di < (int)g_placedPlatforms.size(); di++) {
                if (!g_placedPlatforms[di].isDepot) continue;
                for (int si : stationMembers[enteredComp]) {
                    if (ArePlatformsAdjacent(g_placedPlatforms[di].position, g_placedPlatforms[si].position, g_gridSpacing)) { startDepotIdx = di; break; }
                }
                if (startDepotIdx >= 0) break;
            }
            if (startDepotIdx < 0) {
                continue;
            }

            std::vector<int> cluster = GetDepotClusterIndices(g_placedPlatforms, startDepotIdx, g_gridSpacing);
            if (!cluster.empty()) {
                int clusterCargo = GetClusterCargoTotal(g_placedPlatforms, cluster);
                int clusterCap = GetClusterCapacityTotal(cluster);
                int clusterFree = clusterCap - clusterCargo;

                int trainCap = train.cargoTrailers * 2;
                train.cargoTotal = Clamp(train.cargoTotal, 0, trainCap);

                if (train.cargoTotal > 0) {
                    // Drop as much as possible (attempt to empty the train)
                    int drop = std::min(train.cargoTotal, clusterFree);
                    if (drop > 0) {
                        AddCargoToCluster(g_placedPlatforms, cluster, drop);
                        train.cargoTotal -= drop;
                    }
                } else {
                    // Pick up as much as possible (attempt to fill the train)
                    int takeReq = trainCap;
                    int taken = RemoveCargoFromCluster(g_placedPlatforms, cluster, std::min(takeReq, clusterCargo));
                    train.cargoTotal = taken;
                }
            }
        }
        
        // Update particles
        UpdateBuildParticles(deltaTime);
        
        // Begin drawing (to window in standalone, to framebuffer in embedded)
        if (!g_standalone_mode && g_framebuffer_initialized) {
            BeginTextureMode(g_framebuffer);
        } else {
            BeginDrawing();
        }

        // Clear background (map keeps a flat black background for readability)
        ClearBackground(g_mapMode ? BLACK : skyColor);

        // 2D Map Mode
        if (g_mapMode) {
            BeginMode2D(g_mapCamera);

            // Draw grid (same extents as 3D)
            const float gridSize = 100.0f;
            Color mapGrid = (Color){ 80, 0, 0, 255 };

            for (float z = -gridSize; z <= gridSize; z += g_gridSpacing) {
                Vector2 a = WorldToMap((Vector3){ -gridSize, 0.0f, z });
                Vector2 b = WorldToMap((Vector3){  gridSize, 0.0f, z });
                DrawLineV(a, b, mapGrid);
            }
            for (float x = -gridSize; x <= gridSize; x += g_gridSpacing) {
                Vector2 a = WorldToMap((Vector3){ x, 0.0f, -gridSize });
                Vector2 b = WorldToMap((Vector3){ x, 0.0f,  gridSize });
                DrawLineV(a, b, mapGrid);
            }

            // Buildings
            for (const auto& building : g_buildings) {
                Vector2 p = WorldToMap(building.position);
                Rectangle r = { p.x - building.size.x * 0.5f, p.y - building.size.z * 0.5f, building.size.x, building.size.z };
                DrawRectangleRec(r, AddColor(MulColor(building.color, brightness), nightBlue));
            }

            // Platforms (top-down squares)
            for (int pi = 0; pi < (int)g_placedPlatforms.size(); pi++) {
                const auto& platform = g_placedPlatforms[pi];
                PlatformType pType = GetPlatformType(platform.position, g_placedPlatforms, g_gridSpacing);
                Color c;
                if (platform.isDepot) {
                    c = AddColor(MulColor((Color){ 160, 160, 160, 220 }, brightness), nightBlue);
                } else if (pType == PlatformType::Points) {
                    c = g_pointsColorEff;
                } else {
                    // Check if this platform belongs to a line by checking platform indices
                    int lineId = -1;
                    for (int li = 0; li < (int)g_lines.size(); li++) {
                        if (g_lines[li].platformIndices.find(pi) != g_lines[li].platformIndices.end()) {
                            lineId = li;
                            break;
                        }
                    }
                    
                    if (lineId >= 0 && lineId < (int)g_lines.size()) {
                        // Use line color - adjust brightness based on platform type
                        const Line& line = g_lines[lineId];
                        Color lineColorBase = line.color;
                        
                        if (platform.isStation) {
                            // Stations: 10% darker, 90% transparent
                            c = MulColor(lineColorBase, 0.9f);
                            c.a = 230; // 90% transparent (0.9 * 255 = 230)
                        } else {
                            // Track/platforms: 20% brighter, 78% transparent
                            c = MulColor(lineColorBase, 1.2f);
                            c.a = 199; // 78% transparent (0.78 * 255 = 199)
                        }
                        
                        // Apply brightness and night effects
                        c = AddColor(MulColor(c, brightness), nightBlue);
                    } else if (platform.isStation) {
                        c = g_stationColorEff;
                    } else {
                        c = g_platformColorEff;
                    }
                }

                Vector2 p = WorldToMap(platform.position);
                Rectangle r = { p.x - g_gridSpacing * 0.5f, p.y - g_gridSpacing * 0.5f, g_gridSpacing, g_gridSpacing };
                DrawRectangleRec(r, c);

                // Outline junctions more clearly
                if (!platform.isDepot && pType == PlatformType::Points) {
                    DrawRectangleLinesEx(r, 2.0f, (Color){ 255, 255, 255, 180 });
                }

                // Depot cargo indicator
                if (platform.isDepot && platform.depotCargo > 0) {
                    int cargoCount = Clamp(platform.depotCargo, 0, 8);
                    float step = g_gridSpacing * 0.18f;
                    for (int i = 0; i < cargoCount; i++) {
                        int col = i % 4;
                        int row = i / 4;
                        Vector2 dot = { p.x + (col - 1.5f) * step, p.y + (row == 0 ? -0.5f : 0.5f) * step };
                        DrawCircleV(dot, 0.18f, (Color){ 245, 245, 245, 230 });
                    }
                }
            }

            // Factories (4x4 footprint)
            for (const auto& f : g_placedFactories) {
                Vector2 p = WorldToMap(f.position);
                float half = g_gridSpacing * 2.0f;
                Rectangle r = { p.x - half, p.y - half, half * 2.0f, half * 2.0f };
                Color fc = (Color){ 130, 130, 130, 220 };
                DrawRectangleRec(r, fc);
                DrawRectangleLinesEx(r, 2.0f, (Color){ 30, 30, 30, 220 });
            }

            // Bureaus (2x2 footprint)
            for (const auto& b : g_placedBureaus) {
                Vector2 p = WorldToMap(b.position);
                float half = g_gridSpacing * 1.0f; // 2x2 means half is 1 grid
                Rectangle r = { p.x - half, p.y - half, half * 2.0f, half * 2.0f };
                Color bc = (Color){ 0, 255, 255, 204 }; // Cyan, 80% transparent
                DrawRectangleRec(r, bc);
                DrawRectangleLinesEx(r, 2.0f, (Color){ 0, 200, 200, 220 });
            }

            // Trains
            float realTime = (float)GetTime(); // Real time for pulsing (ignores game speed/pause)
            for (size_t i = 0; i < g_placedTrains.size(); i++) {
                Color trainC = (Color){ 0, 255, 0, 220 };
                float trainBrightness = 1.0f;
                if ((int)i == g_selectedTrainIndex) {
                    trainC = (Color){ 0, 255, 255, 240 };
                    // Pulse from 0.7 (-30%) to 2.3 (+230%) brightness (~1.25 seconds per cycle)
                    float pulse = (sinf(realTime * 5.0f) + 1.0f) / 2.0f; // 0 to 1
                    trainBrightness = 0.7f + pulse * 1.6f; // 0.7 to 2.3
                }
                DrawTrainOnMap(g_placedTrains[i], g_gridSpacing, trainC, trainBrightness);
            }

            // Origin marker
            DrawCircleV({0.0f, 0.0f}, 0.35f, (Color){ 255, 255, 255, 200 });

            EndMode2D();

            // Draw UI Overlay first (before all text)
            DrawUIOverlay();
            
            // Now draw all text on top of UI overlay
            DrawTextEx(gameFont, "MAP VIEW (M to return)", (Vector2){10, 10}, 20, 0.0f, WHITE);
            DrawTextEx(gameFont, "Pan: WASD/Arrows or Middle-Mouse Drag | Zoom: Mouse Wheel", (Vector2){10, 36}, 16, 0.0f, GRAY);
            DrawTextEx(gameFont, "Pulsing cyan train = selected", (Vector2){10, 56}, 16, 0.0f, DARKGRAY);
            
            // Display mouse coordinates in map mode
            Vector2 mousePos = CustomGetMousePosition();
            char mouseCoordText[64];
            snprintf(mouseCoordText, sizeof(mouseCoordText), "Mouse: X:%.0f Y:%.0f", mousePos.x, mousePos.y);
            DrawTextEx(gameFont, mouseCoordText, (Vector2){(float)(g_renderWidth - 200), 10}, 14, 0.0f, (Color){ 200, 200, 255, 255 });
            
            // Draw cursor after all text
            DrawCustomCursor();
            
            // Draw scanline overlay
            DrawScanlines();

            EndDrawing();
            return; // skip 3D draw while in map mode
        }
        
        // Begin 3D mode
        BeginMode3D(g_camera);
        
        // Draw grid at sea level (y=0) in dark red
        Color gridColor = AddColor(MulColor((Color){ 139, 0, 0, 255 }, brightness), nightBlue); // Dark red, tinted
        const float gridSize = 100.0f;
        
        // Draw grid lines in X direction (lines parallel to X axis)
        for (float z = -gridSize; z <= gridSize; z += g_gridSpacing) {
            DrawLine3D(
                (Vector3){ -gridSize, 0.0f, z },
                (Vector3){ gridSize, 0.0f, z },
                gridColor
            );
        }
        
        // Draw grid lines in Z direction (lines parallel to Z axis)
        for (float x = -gridSize; x <= gridSize; x += g_gridSpacing) {
            DrawLine3D(
                (Vector3){ x, 0.0f, -gridSize },
                (Vector3){ x, 0.0f, gridSize },
                gridColor
            );
        }
        
        // Draw all buildings with red transparent shading
        for (const auto& building : g_buildings) {
            // Draw filled cube with red transparent color
            DrawCube(
                building.position,
                building.size.x,
                building.size.y,
                building.size.z,
                AddColor(MulColor(building.color, brightness), nightBlue)
            );
        }

        // Draw placed factories
        for (const auto& f : g_placedFactories) {
            DrawFactory(f.position, g_gridSpacing, AddColor(MulColor((Color){ 130, 130, 130, 220 }, brightness), nightBlue));
        }
        
        // Draw placed bureaus (match platform color and transparency exactly)
        Color bureauColor = (Color){ 0, 255, 255, 200 }; // Cyan, same as g_platformColor
        Color bureauColorEff = AddColor(MulColor(bureauColor, brightness), nightBlue); // Same processing as platforms
        for (const auto& b : g_placedBureaus) {
            DrawBureau(b.position, g_gridSpacing, b.floors, bureauColorEff);
        }
        
        // Draw placed platforms
        bool mouseOverPlatform = false;
        int hoveredPlatformIndex = -1;
        float currentTime = (float)GetTime(); // For animation effects
        bool hasSelectedTrain = (g_selectedTrainIndex >= 0 && g_selectedTrainIndex < (int)g_placedTrains.size());
        
        for (int pi = 0; pi < (int)g_placedPlatforms.size(); pi++) {
            const auto& platform = g_placedPlatforms[pi];
            // Determine platform color based on type
            PlatformType pType = GetPlatformType(platform.position, g_placedPlatforms, g_gridSpacing);
            Color drawColor;
            
            if (platform.isDepot) {
                // Materials-Depot
                drawColor = AddColor(MulColor((Color){ 160, 160, 160, 220 }, brightness), nightBlue);
            } else if (pType == PlatformType::Points) {
                // Junction/Points platform - always red regardless of station status
                drawColor = g_pointsColorEff;
            } else {
                // Check if this platform belongs to a line by checking platform indices
                int lineId = -1;
                for (int li = 0; li < (int)g_lines.size(); li++) {
                    if (g_lines[li].platformIndices.find(pi) != g_lines[li].platformIndices.end()) {
                        lineId = li;
                        break;
                    }
                }
                
                if (lineId >= 0 && lineId < (int)g_lines.size()) {
                    // Use line color - adjust brightness based on platform type
                    const Line& line = g_lines[lineId];
                    Color lineColorBase = line.color;
                    
                    if (platform.isStation) {
                        // Stations: 10% darker, 90% transparent
                        drawColor = MulColor(lineColorBase, 0.9f);
                        drawColor.a = 230; // 90% transparent (0.9 * 255 = 230)
                    } else {
                        // Track/platforms: 20% brighter, 78% transparent
                        drawColor = MulColor(lineColorBase, 1.2f);
                        drawColor.a = 199; // 78% transparent (0.78 * 255 = 199)
                    }
                    
                    // Apply brightness and night effects
                    drawColor = AddColor(MulColor(drawColor, brightness), nightBlue);
                    
                    // Debug: Log when platform is colored with line color (only once per platform)
                    static std::set<int> loggedPlatforms; // Track which platforms we've logged
                    if (loggedPlatforms.find(pi) == loggedPlatforms.end()) {
                        DebugLogFormat("DEBUG: Platform %d colored with line %d (%s), isStation=%d, color=(%d,%d,%d,%d)", 
                                       pi, line.id, line.name.c_str(), platform.isStation ? 1 : 0, drawColor.r, drawColor.g, drawColor.b, drawColor.a);
                        loggedPlatforms.insert(pi);
                    }
                } else if (platform.isStation) {
                    // Station-Track segment (no line assigned)
                    drawColor = g_stationColorEff;
                } else {
                    // Normal platform (no line assigned)
                    drawColor = g_platformColorEff;
                }
            }
            
            if (platform.isDepot) {
                DrawMaterialsDepot(platform.position, g_gridSpacing, drawColor, platform.depotCargo);
            } else {
                DrawPlatform(platform.position, g_gridSpacing, drawColor);
            }

            // If this station has a depot next to it, always highlight the station PRIME tile.
            if (!platform.isDepot && platform.isStation) {
                int cid = (pi < (int)stationCompId.size()) ? stationCompId[pi] : -1;
                if (cid >= 0 &&
                    cid < (int)stationPrimePlatformIdx.size() &&
                    cid < (int)stationHasAdjacentDepot.size() &&
                    stationHasAdjacentDepot[cid] &&
                    stationPrimePlatformIdx[cid] == pi) {

                    float topY = GetPlatformTopY(platform.position.y, g_gridSpacing);
                    float topThickness = g_gridSpacing * 0.1f;
                    // Slightly larger yellow outline so it's visible even with other highlights.
                    DrawCubeWires((Vector3){platform.position.x, topY, platform.position.z},
                                 g_gridSpacing * 1.08f, topThickness * 1.35f, g_gridSpacing * 1.08f,
                                 (Color){ 255, 215, 0, 255 });
                }
            }
            
            // Draw visual indicators for Points-Platforms
            if (!platform.isDepot && pType == PlatformType::Points) {
                int exitSetting = -1; // -1 = use deterministic default pair
                if (hasSelectedTrain) {
                    exitSetting = g_placedTrains[g_selectedTrainIndex].GetJunctionSetting(platform.position.x, platform.position.z);
                }
                DrawPointsIndicator(platform.position, g_placedPlatforms, g_gridSpacing, currentTime, exitSetting, hasSelectedTrain);
            }
            
            // Check if mouse is over this platform for highlighting
            if (Vector3Distance(g_mouseWorldPos, platform.position) < 0.1f) {
                mouseOverPlatform = true;
                hoveredPlatformIndex = pi;
                float topY = GetPlatformTopY(platform.position.y, g_gridSpacing);
                float topThickness = g_gridSpacing * 0.1f;
                // Highlight with a white wireframe box on the top surface
                DrawCubeWires((Vector3){platform.position.x, topY, platform.position.z}, g_gridSpacing * 1.02f, topThickness * 1.2f, g_gridSpacing * 1.02f, WHITE);
            }
        }
        
        // Draw placed trains (with selection pulsing brightness)
        for (size_t i = 0; i < g_placedTrains.size(); i++) {
            // Calculate brightness for selected train (uses real time, ignores game speed/pause)
            float trainBrightness = 1.0f;
            if ((int)i == g_selectedTrainIndex) {
                // Pulse from 0.7 (-30%) to 2.3 (+230%) brightness (~1.25 seconds per cycle)
                float pulse = (sinf(currentTime * 5.0f) + 1.0f) / 2.0f; // 0 to 1
                trainBrightness = 0.7f + pulse * 1.6f; // 0.7 to 2.3
            }
            
            if (g_placedTrains[i].type == PlacedTrain::TrainType::Cargo) {
                DrawCargoTrain(g_placedTrains[i].path, g_placedTrains[i].pathProgress, g_gridSpacing, g_placedTrains[i].cargoTrailers, g_placedTrains[i].cargoTotal, trainBrightness);
            } else {
                DrawTrain(g_placedTrains[i].path, g_placedTrains[i].pathProgress, g_gridSpacing, trainBrightness);
            }
        }
        
        // Draw preview (platform or train) at mouse position
        if (g_trainPlacementMode || g_cargoTrainPlacementMode) {
            // Check if valid placement location
            Vector3 pathCenter;
            bool canPlaceTrain = false;
            
            // Check if the platform under mouse is a station
            const PlacedPlatform* targetPlatform = nullptr;
            for (const auto& p : g_placedPlatforms) {
                if (Vector3Distance(g_mouseWorldPos, p.position) < 0.1f) {
                    targetPlatform = &p;
                    break;
                }
            }

            if (targetPlatform && targetPlatform->isStation && g_placedPlatforms.size() >= 4) {
                if (CheckConnectedPlatforms(g_mouseWorldPos, g_placedPlatforms, g_gridSpacing, pathCenter)) {
                    std::vector<Vector3> path = BuildPlatformPath(g_mouseWorldPos, g_placedPlatforms, g_gridSpacing);
                    if (path.size() >= 4) {
                        canPlaceTrain = true;
                        // For preview, we need to build a path with Y positions
                        std::vector<Vector3> previewPath;
                        for (const auto& pos : path) {
                            previewPath.push_back({ pos.x, GetPlatformTopY(pos.y, g_gridSpacing), pos.z });
                        }
                        // Preview should match placement rule: centered on the station platform under the cursor
                        float previewProgress = GetClosestDistanceAlongPath(previewPath, (Vector3){ targetPlatform->position.x, GetPlatformTopY(targetPlatform->position.y, g_gridSpacing), targetPlatform->position.z });
                        if (g_cargoTrainPlacementMode) {
                            // Preview cargo as fully loaded so it's obvious it's a cargo train
                            DrawCargoTrain(previewPath, previewProgress, g_gridSpacing, g_cargoPlacementTrailers, g_cargoPlacementTrailers * 2);
                        }
                        else DrawTrain(previewPath, previewProgress, g_gridSpacing);
                    }
                }
            }
            
            // If not over a station or can't place train, show invalid indicator
            if (!canPlaceTrain && mouseOverPlatform) {
                float topY = GetPlatformTopY(g_mouseWorldPos.y, g_gridSpacing);
                float topThickness = g_gridSpacing * 0.1f;
                DrawCubeWires((Vector3){g_mouseWorldPos.x, topY, g_mouseWorldPos.z}, g_gridSpacing * 1.05f, topThickness * 1.5f, g_gridSpacing * 1.05f, RED);
            }
        } else if (g_bureauPlacementMode) {
            int selectedFloors = g_bureauFloorOptions[g_bureauFloorIndex];
            bool canPlaceBureau = IsWithinTwoGridSpacesOfValidBuilding(g_mouseWorldPos, g_placedPlatforms, g_placedFactories, g_gridSpacing);
            bool hasCargo = HasEnoughCargoInRadius(g_mouseWorldPos, g_placedPlatforms, g_gridSpacing, 5);
            int totalCost = selectedFloors * 10000;
            bool hasCredits = (g_playerCredits >= totalCost);
            
            Color bureauPreviewColor;
            if (canPlaceBureau && hasCargo && hasCredits) {
                // Match platform color exactly (same base color and processing)
                Color baseColor = (Color){ 0, 255, 255, 200 }; // Cyan, same as g_platformColor
                bureauPreviewColor = AddColor(MulColor(baseColor, brightness), nightBlue);
            } else {
                bureauPreviewColor = (Color){ 255, 0, 0, 200 }; // Red for invalid
            }
            DrawBureau(g_mouseWorldPos, g_gridSpacing, selectedFloors, bureauPreviewColor);
        } else if (g_demolishMode) {
            // Draw demolish preview (red wireframe box)
            float topY = GetPlatformTopY(g_mouseWorldPos.y, g_gridSpacing);
            float topThickness = g_gridSpacing * 0.1f;
            DrawCubeWires((Vector3){g_mouseWorldPos.x, topY, g_mouseWorldPos.z}, g_gridSpacing * 1.1f, topThickness * 2.0f, g_gridSpacing * 1.1f, RED);
        } else if (g_factoryPlacementMode) {
            bool canPlaceFactory = HasAdjacentDepotForFactory(g_mouseWorldPos, g_placedPlatforms, g_gridSpacing);
            Color fc = canPlaceFactory ? (Color){ 130, 130, 130, 220 } : (Color){ 255, 0, 0, 200 };
            DrawFactory(g_mouseWorldPos, g_gridSpacing, fc);
        } else if (g_depotPlacementMode) {
            bool canPlaceDepot = CanPlaceDepotAt(g_mouseWorldPos, g_placedPlatforms, g_gridSpacing);
            Color depotColor = canPlaceDepot ? (Color){ 160, 160, 160, 220 } : (Color){ 255, 0, 0, 200 };
            DrawMaterialsDepot(g_mouseWorldPos, g_gridSpacing, depotColor, 0);
        } else if (g_stationPlacementMode) {
            // Draw preview Station-Track (4 platforms in dark cyan)
            for (int i = 0; i < 4; i++) {
                Vector3 pos = g_mouseWorldPos;
                if (g_stationHorizontal) pos.x += (i - 1.5f) * g_gridSpacing;
                else pos.z += (i - 1.5f) * g_gridSpacing;
                DrawPlatform(pos, g_gridSpacing, g_stationColor);
            }
        } else if (g_demolishMode) {
            // Draw demolish preview (red X or highlight)
            float topY = GetPlatformTopY(g_mouseWorldPos.y, g_gridSpacing);
            float topThickness = g_gridSpacing * 0.1f;
            DrawCubeWires((Vector3){g_mouseWorldPos.x, topY, g_mouseWorldPos.z}, g_gridSpacing * 1.1f, topThickness * 2.0f, g_gridSpacing * 1.1f, RED);
        } else {
            // Draw preview platform at mouse position
            DrawPlatform(g_mouseWorldPos, g_gridSpacing, g_platformColor);
        }
        
        // Render build particles
        RenderBuildParticles();
        
        // End 3D mode
        EndMode3D();

        // Debug: station gate status (hover a station tile, or a depot adjacent to that station)
        {
            long long gateKey = kNoStation;
            int gateComp = -1;

            if (hoveredPlatformIndex >= 0 && hoveredPlatformIndex < (int)g_placedPlatforms.size()) {
                const PlacedPlatform& hp = g_placedPlatforms[hoveredPlatformIndex];

                if (!hp.isDepot && hp.isStation) {
                    int cid = (hoveredPlatformIndex < (int)stationCompId.size()) ? stationCompId[hoveredPlatformIndex] : -1;
                    // Only the PRIME station tile is the "hotspot" for station interactions/debug.
                    if (cid >= 0 && cid < (int)stationCompKey.size() &&
                        cid < (int)stationPrimePlatformIdx.size() &&
                        stationPrimePlatformIdx[cid] == hoveredPlatformIndex) {
                        gateKey = stationCompKey[cid];
                        gateComp = cid;
                    }
                } else if (hp.isDepot) {
                    // Show the station gate for ANY station tile adjacent to this depot's connected depot cluster (if any)
                    int startDepotIdx = hoveredPlatformIndex;
                    std::vector<int> cluster = GetDepotClusterIndices(g_placedPlatforms, startDepotIdx, g_gridSpacing);
                    bool found = false;
                    for (int di : cluster) {
                        if (di < 0 || di >= (int)g_placedPlatforms.size()) continue;
                        const Vector3 dpos = g_placedPlatforms[di].position;
                        for (int si = 0; si < (int)g_placedPlatforms.size(); si++) {
                            const auto& sp = g_placedPlatforms[si];
                            if (sp.isDepot) continue;
                            if (!sp.isStation) continue;
                            if (!ArePlatformsAdjacent(dpos, sp.position, g_gridSpacing)) continue;
                            int cid = (si < (int)stationCompId.size()) ? stationCompId[si] : -1;
                            if (cid >= 0 && cid < (int)stationCompKey.size()) {
                                gateKey = stationCompKey[cid];
                                gateComp = cid;
                                found = true;
                                break;
                            }
                        }
                        if (found) break;
                    }
                }
            }

            // Store gate status for drawing after UI overlay
            bool gateOpen = false;
            bool hasGate = false;
            if (gateKey != kNoStation) {
                hasGate = true;
                gateOpen = (gateComp >= 0 && gateComp < (int)stationGateOpen.size() && stationGateOpen[gateComp] != 0);
            }
            
            // Draw UI Overlay first (before all text)
            DrawUIOverlay();
            
            // Now draw all text on top of UI overlay
            if (hasGate) {
                if (gateOpen) {
                    DrawTextEx(gameFont, "STATION GATE: OPEN", (Vector2){10, 110}, 16, 0.0f, (Color){ 120, 255, 120, 255 });
                } else {
                    DrawTextEx(gameFont, "STATION GATE: CLOSED", (Vector2){10, 110}, 16, 0.0f, (Color){ 255, 140, 140, 255 });
                }
            }
        }
        
        // Draw UI text
        DrawTextEx(gameFont, "CyberTrain - Railway Builder", (Vector2){10, 10}, 20, 0.0f, WHITE);
        
        // Display credits
        const char* creditsText = TextFormat("Credits: %d", g_playerCredits);
        DrawTextEx(gameFont, creditsText, (Vector2){(float)(g_renderWidth - 150), 10}, 18, 0.0f, (Color){ 255, 255, 0, 255 });

        // In-game clock UI (top-right)
        // Map 0..1 cycle to 0..24 hours for a readable clock
        int clockMinutesTotal = (int)floorf(dayT * 24.0f * 60.0f) % (24 * 60);
        int clockH = clockMinutesTotal / 60;
        int clockM = clockMinutesTotal % 60;
        const char* clockText = TextFormat("%02d:%02d  %s", clockH, clockM, phaseName);
        int clockW = (int)MeasureTextEx(gameFont, clockText, 18, 0.0f).x;
        DrawTextEx(gameFont, clockText, (Vector2){(float)(g_renderWidth - clockW - 10), 35}, 18, 0.0f, (Color){ 220, 220, 220, 255 });
        
        // Display game speed
        const char* speedText = TextFormat("Speed: %s (SPACE)", GetSpeedName());
        int speedW = (int)MeasureTextEx(gameFont, speedText, 16, 0.0f).x;
        DrawTextEx(gameFont, speedText, (Vector2){(float)(g_renderWidth - speedW - 10), 60}, 16, 0.0f, (Color){ 255, 255, 0, 255 });
        
        // Display mouse coordinates
        mousePos = CustomGetMousePosition(); // Reuse variable declared earlier in function
        char mouseCoordText[64];
        snprintf(mouseCoordText, sizeof(mouseCoordText), "Mouse: X:%.0f Y:%.0f", mousePos.x, mousePos.y);
        DrawTextEx(gameFont, mouseCoordText, (Vector2){(float)(g_renderWidth - 200), 85}, 14, 0.0f, (Color){ 200, 200, 255, 255 });
        
        // Draw line modal (on top of everything)
        DrawLineModal(g_lineModal, g_lines, g_renderWidth, g_renderHeight);
        if (g_trainPlacementMode) {
            DrawTextEx(gameFont, "Mode: Train Placement | LEFT CLICK = Place Train (REQUIRES STATION-TRACK)", (Vector2){10, 35}, 16, 0.0f, YELLOW);
            DrawTextEx(gameFont, "Controls: T = Exit Train Mode | C = Cargo Train | D = Depot | ARROWS = Move | +/- = Zoom", (Vector2){10, 55}, 16, 0.0f, GRAY);
        } else if (g_cargoTrainPlacementMode) {
            DrawTextEx(gameFont, TextFormat("Mode: Cargo Train Placement (%d trailer%s) | LEFT CLICK = Place Cargo Train (REQUIRES STATION-TRACK)",
                                g_cargoPlacementTrailers, g_cargoPlacementTrailers == 1 ? "" : "s"),
                     (Vector2){10, 35}, 16, 0.0f, YELLOW);
            DrawTextEx(gameFont, "Controls: C = Cycle Trailers | T = Passenger Train | D = Depot | S = Station | ARROWS = Move | +/- = Zoom", (Vector2){10, 55}, 16, 0.0f, GRAY);
        } else if (g_depotPlacementMode) {
            DrawTextEx(gameFont, "Mode: Materials-Depot Placement | LEFT CLICK = Place Depot (must connect to a Station, directly or via Depots) | Cost: 1,500 credits", (Vector2){10, 35}, 16, 0.0f, LIGHTGRAY);
            DrawTextEx(gameFont, "Controls: D = Exit Depot Mode | T = Train | C = Cargo | S = Station | F = Factory | B = Bureau | ARROWS = Move | +/- = Zoom", (Vector2){10, 55}, 16, 0.0f, GRAY);
        } else if (g_factoryPlacementMode) {
            DrawTextEx(gameFont, "Mode: Factory Placement | LEFT CLICK = Place Factory (MUST be adjacent to a Depot) | Cost: 10,000 credits", (Vector2){10, 35}, 16, 0.0f, LIGHTGRAY);
            DrawTextEx(gameFont, "Controls: F = Exit Factory Mode | D = Depot | S = Station | T = Train | C = Cargo | B = Bureau | ARROWS = Move | +/- = Zoom", (Vector2){10, 55}, 16, 0.0f, GRAY);
        } else if (g_bureauPlacementMode) {
            int selectedFloors = g_bureauFloorOptions[g_bureauFloorIndex];
            int totalCost = selectedFloors * 10000;
            DrawTextEx(gameFont, TextFormat("Mode: Bureau Placement (%d floors) | LEFT CLICK = Place Bureau | Cost: %d credits + 5 cargo", selectedFloors, totalCost), (Vector2){10, 35}, 16, 0.0f, (Color){ 0, 255, 255, 255 });
            DrawTextEx(gameFont, "Requirements: Within 2 grid spaces of Station/Factory/Depot | B = Cycle Floors | ARROWS = Move | +/- = Zoom", (Vector2){10, 55}, 16, 0.0f, GRAY);
        } else if (g_stationPlacementMode) {
            DrawTextEx(gameFont, "Mode: Station Placement | LEFT CLICK = Place Station-Track | Cost: 1,000 credits", (Vector2){10, 35}, 16, 0.0f, LIME);
            DrawTextEx(gameFont, "Controls: S = Exit Station Mode | R = Rotate | ARROWS = Move | +/- = Zoom", (Vector2){10, 55}, 16, 0.0f, GRAY);
        } else if (g_demolishMode) {
            DrawTextEx(gameFont, "Mode: Demolish | LEFT CLICK = Remove object at grid square | Cost: 100 credits per demolition", (Vector2){10, 35}, 16, 0.0f, RED);
            DrawTextEx(gameFont, "Controls: X = Exit Demolish Mode | ARROWS = Move | +/- = Zoom", (Vector2){10, 55}, 16, 0.0f, GRAY);
        } else if (hasSelectedTrain) {
            DrawTextEx(gameFont, TextFormat("TRAIN #%d SELECTED - Click JUNCTIONS to configure routes!", g_selectedTrainIndex + 1), (Vector2){10, 35}, 16, 0.0f, (Color){0, 255, 255, 255});
            DrawTextEx(gameFont, "Controls: CLICK Junction = Change Route | CLICK Train = Deselect | ESC = Deselect", (Vector2){10, 55}, 16, 0.0f, GRAY);
        } else {
            DrawTextEx(gameFont, "Controls: ARROWS = Move | SHIFT+LEFT/RIGHT = Rotate | +/- = Zoom | CLICK = Place/Select | T = Train | C = Cargo | D = Depot | F = Factory | S = Station | B = Bureau | X = Demolish", (Vector2){10, 35}, 16, 0.0f, GRAY);
            DrawTextEx(gameFont, "Click on a placed TRAIN to select it and configure its junction routes!", (Vector2){10, 55}, 14, 0.0f, DARKGRAY);
        }
        DrawTextEx(gameFont, "Colors: CYAN = Track/Bureau | DARK CYAN = Station | GRAY = Depot/Factory | RED = Junction | GREEN = Editable Junction", (Vector2){10, 75}, 14, 0.0f, DARKGRAY);
        DrawFPS(10, 95);
        
        // DEBUG: Show component counts and modal state on screen
        char debugOnScreen[256];
        snprintf(debugOnScreen, sizeof(debugOnScreen), "DEBUG: Components prev=%d curr=%d | Modal=%d", 
                 g_debugPreviousComponentCount, g_debugCurrentComponentCount, (int)g_lineModal.state);
        DrawTextEx(gameFont, debugOnScreen, (Vector2){10, 115}, 14, 0.0f, YELLOW);
        
        // Count stations and track
        int debugStationCount = 0;
        int debugTrackCount = 0;
        for (const auto& p : g_placedPlatforms) {
            if (p.isDepot) continue;
            if (p.isStation) debugStationCount++;
            else debugTrackCount++;
        }
        char debugPlatforms[256];
        snprintf(debugPlatforms, sizeof(debugPlatforms), "DEBUG: Platforms: %d stations, %d track, %d total", 
                 debugStationCount, debugTrackCount, (int)g_placedPlatforms.size());
        DrawTextEx(gameFont, debugPlatforms, (Vector2){10, 135}, 14, 0.0f, YELLOW);
        
        // Draw cursor after all text
        DrawCustomCursor();
        
        // Draw scanline overlay
        DrawScanlines();
        
        // End drawing
        if (!g_standalone_mode && g_framebuffer_initialized) {
            EndTextureMode();
        } else {
            EndDrawing();
        }
} // End of GameLoopBody()

// ══════════════════════════════════════════════════════════════════════════════
// MAIN FUNCTION - Entry point for standalone mode (not called in embedded mode)
// ══════════════════════════════════════════════════════════════════════════════

int main() {
    // Standalone mode: initialize everything ourselves
    g_standalone_mode = true;
    
    // Initialize window
    const int screenWidth = 1200;
    const int screenHeight = 800;
    InitWindow(screenWidth, screenHeight, "CyberTrain - Railway Builder");
    SetTargetFPS(60);
    
    // Load custom font
    gameFont = LoadFont("PixelifySans.ttf");
    if (gameFont.texture.id == 0) {
        TraceLog(LOG_WARNING, "Failed to load PixelifySans.ttf, using default font");
        gameFont = GetFontDefault();
        fontIsCustom = false;
    } else {
        fontIsCustom = true;
    }
    
    // Initialize debug file
    InitDebugFile();
    DebugLog("=== Game Started (Standalone) ===");
    
    // Initialize game state (same initialization as InitializeGame())
    g_buildings = generateCitySkyline();
    
    // Initialize camera
    g_camera.position = (Vector3){ 60.0f, 50.0f, 60.0f };
    g_camera.target = (Vector3){ 0.0f, 0.0f, 0.0f };
    g_camera.up = (Vector3){ 0.0f, 1.0f, 0.0f };
    g_camera.fovy = 45.0f;
    g_camera.projection = CAMERA_PERSPECTIVE;
    g_cameraAltitude = g_camera.position.y;
    g_cameraYaw = atan2f(g_camera.position.x - g_camera.target.x, g_camera.position.z - g_camera.target.z);
    g_cameraRadius = sqrtf((g_camera.position.x - g_camera.target.x) * (g_camera.position.x - g_camera.target.x) +
                           (g_camera.position.z - g_camera.target.z) * (g_camera.position.z - g_camera.target.z));
    
    // Initialize 2D map camera
    g_mapCamera.target = { 0.0f, 0.0f };
    g_mapCamera.offset = { (float)GetScreenWidth() * 0.5f, (float)GetScreenHeight() * 0.5f };
    g_mapCamera.rotation = 0.0f;
    g_mapCamera.zoom = 6.0f;
    
    g_game_initialized = true;
    
    // Load UI Assets (Standalone)
    LoadUIAssets();
    
    // Main game loop
    while (!WindowShouldClose()) {
        GameLoopBody();
    }
    
    // Cleanup
    UnloadUIAssets();
    DebugLog("=== Game Ended ===");
    if (debugFile.is_open()) {
        debugFile.close();
    }
    if (fontIsCustom) {
        UnloadFont(gameFont);
    }
    CloseWindow();
    
    return 0;
}
