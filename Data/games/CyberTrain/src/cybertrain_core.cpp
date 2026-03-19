#include "raylib.h"
#include "raymath.h"
#include "rlgl.h"
#include <vector>
#include <random>
#include <algorithm>
#include <array>
#include <unordered_map>
#include <unordered_set>
#include <string>
#include <set>
#include <cstring>
#include <fstream>
#include <ctime>
#include <cstdarg>
#include <cfloat>
#include <cctype>
#include <tuple>
#ifdef _WIN32
// Forward declare only what we need - avoid including windows.h to prevent conflicts
extern "C" {
    __declspec(dllimport) unsigned long __stdcall GetModuleFileNameA(void*, char*, unsigned long);
    __declspec(dllimport) int __stdcall SetCurrentDirectoryA(const char*);
}
#define MAX_PATH 260
#include <direct.h>
#else
#include <unistd.h>
#include <limits.h>
#endif

// --- Debug file logging ---
static std::ofstream debugFile;
static bool debugFileInitialized = false;

// --- Font ---
static Font gameFont = { 0 };
static bool fontIsCustom = false;

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
// EMBEDDED MODE SUPPORT (for BBS integration) - matches AstroMiner architecture
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

static RenderTexture2D g_framebuffer = {0};
static bool g_framebuffer_initialized = false;
static Texture2D scanlineTx = {0};
static unsigned char* g_frame_buffer_data = NULL;
static int g_frame_buffer_size = 0;
static bool g_game_initialized = false;
static bool g_standalone_mode = true;
static bool g_exit_requested = false;
static bool g_audio_initialized = false;

// ── Audio assets ──────────────────────────────────────────────────────────────
static Music g_musicTracks[3] = {};
static bool g_musicLoaded = false;
static int g_currentTrack = 0;

static Sound g_sfxBuildTrain = {};
static Sound g_sfxBuildSys = {};
static Sound g_sfxFactoryBuilt = {};
static Sound g_sfxBureauBuilt = {};
static Sound g_sfxSiloBuilt = {};
static bool g_sfxLoaded = false;

// Pending SFX (for factory/bureau delayed second sound)
static float g_pendingSfxTimer = 0.0f;
static bool g_pendingSfxActive = false;

// ── Options state ─────────────────────────────────────────────────────────────
enum class OptionsScreen { Hidden, Visible };
static OptionsScreen g_optionsScreen = OptionsScreen::Hidden;
static int g_optionsSelection = 0;  // 0=music, 1=sfx, 2=gamma
static int g_musicVolume = 1;       // 0=low, 1=mid, 2=high
static int g_sfxVolume = 1;         // 0=low, 1=mid, 2=high
static int g_gammaLevel = 1;        // 0=low, 1=mid, 2=high
static int g_renderWidth = 1200;
static int g_renderHeight = 800;
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
    int charQueue[64];
    int charQueueHead;
    int charQueueTail;
} g_inputState = {0};

static char g_username[64] = "Player";
static bool g_shouldCenterMouse = false;
static int g_lastFinalScore = 0;

static void SanitizeCyberTrainUsername(const char* source, char* dest, size_t destSize) {
    if (!dest || destSize == 0) return;
    dest[0] = '\0';
    if (!source) return;

    size_t out = 0;
    for (size_t i = 0; source[i] != '\0' && out + 1 < destSize; i++) {
        unsigned char c = (unsigned char)source[i];
        if (c < 32 || c == 127) {
            if (out > 0 && dest[out - 1] != ' ') dest[out++] = ' ';
            continue;
        }
        dest[out++] = (char)c;
    }

    while (out > 0 && dest[out - 1] == ' ') out--;
    dest[out] = '\0';
    if (out == 0) {
        strncpy(dest, "Player", destSize - 1);
        dest[destSize - 1] = '\0';
    }
}

// â”€â”€ Leaderboard â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
struct CyberTrainLBEntry { char username[64]; int score; };
static std::vector<CyberTrainLBEntry> g_leaderboard;
static constexpr int kLBMaxEntries = 10;

// â”€â”€ Year-boundary / game-over state â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
static bool  g_year5WarningShown = false;
static bool  g_year5ModalOpen    = false;
static int   g_year5ModalFrames  = 0;
static bool  g_gameOver          = false;
static int   g_finalScore        = 0;
static float g_gameOverTimer     = 0.0f;
static int   g_gameOverPhase     = 0;     // 0=transition, 1=leaderboard
static bool  g_bankruptcyGraceActive = false;
static int   g_bankruptcyDeadlineYear = -1;

// â”€â”€ Intro / Help modal state â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
static bool g_introModalOpen   = false;
static int  g_introModalFrames = 0;
static bool g_helpModalOpen    = false;
static int  g_helpModalFrames  = 0;
static int  g_helpPage         = 0;
static constexpr int kHelpPageCount = 16;

// ── Intro zoom animation (fires once when the first modal closes) ─────────────
static bool g_zoomIntroActive  = false;  // currently animating
static bool g_zoomIntroDone    = false;  // prevents re-trigger on subsequent H presses

// ── CyberTrain follow-cam (activated when a silo is created) ─────────────────
static bool    g_cyberTrainCamActive     = false;
static int     g_cyberTrainCamTrainId    = -1;
static int     g_cyberTrainCamSavedSpeed = 0;
static Vector3 g_cyberTrainCamSavedPos   = {};
static Vector3 g_cyberTrainCamSavedTarget= {};
static float   g_cyberTrainCamSavedAlt   = 50.0f;
static float   g_cyberTrainCamSavedRadius= 172.0f;
static float   g_cyberTrainCamSavedYaw   = 0.0f;

// Constants that don't depend on types
static const float g_moveSpeed = 2.0f;
static const float g_zoomSpeed = 2.0f;
static const float g_rotateSpeed = 1.4f;
static const float g_gridSpacing = 5.0f;
static const float g_gridExtent = 100.0f;      // Inner buildable grid: -100..+100
static const float g_gridExtentOuter = 135.0f;  // Outer coastal ring extends 35% beyond the inner grid
static const float g_dayCycleSeconds = 20.0f;  // 1 week = 5s at QUICKEST (4x); 10s at QUICK; 20s at MEDIUM; 40s at SLOW
static const float kBureauIncomePerFloorPerDay = 50.0f;

// Returns true if the given position with footprint halfExtent is fully within the buildable grid (includes outer grey ring)
static bool IsWithinGridBounds(float x, float z, float halfExtent) {
    const float eps = 0.001f;
    return (x - halfExtent >= -g_gridExtentOuter - eps && x + halfExtent <= g_gridExtentOuter + eps &&
            z - halfExtent >= -g_gridExtentOuter - eps && z + halfExtent <= g_gridExtentOuter + eps);
}

// True when a world position is in the outer coastal ring (outside inner grid, inside buildable bounds)
static bool IsInOuterGrid(float x, float z) {
    return (fabsf(x) > g_gridExtent || fabsf(z) > g_gridExtent);
}
// Apply 25% discount for outer grid placements
static int OuterGridCost(int baseCost, float x, float z) {
    return IsInOuterGrid(x, z) ? (int)(baseCost * 0.75f) : baseCost;
}

// Camera state (raylib types don't need forward declaration)
static Camera3D g_camera = {0};
static Camera2D g_mapCamera = {0};
static float g_cameraAltitude = 50.0f;
static float g_cameraYaw = 0.0f;
static float g_cameraRadius = 0.0f;
static Vector3 g_mouseWorldPos = {0.0f, 0.0f, 0.0f};

// Scrolling ticker for game tips and controls
static float g_tickerPosition = 0.0f;
static const char* g_baseTickerText = "H FOR HELP | KEY EL=EST LINE | MAT=CARGO MATERIALS | CR=CREDITS | NS=NEARBY STATION | LB=LINKED BUREAU | HUB=INNER CITY HUB | OOB=OUT OF BOUNDS | OVR=OVERLAP | IR/OR=BUREAU RINGS | ARROWS MOVE CAMERA | SHIFT+LEFT/RIGHT ROTATES CAMERA | CTRL+SHIFT+/- ZOOMS | B CYCLES BUREAU FLOOR SIZE | GREEN: GREEN TRAIN + GREEN STATION + HUB-LINKED BUREAU | MAGENTA: MAGENTA STATION + INDUSTRY STATION | CYAN: CYAN TRAIN + CYAN STATION + LINKED BUREAU | ORANGE: ORANGE TRAIN + ORANGE STATION + LINKED BUREAU | RED: RED TRAIN + RED STATION + LINKED BUREAU | YELLOW: YELLOW TRAIN + YELLOW STATION + LINKED BUREAU";
static char g_tickerTextBuf[2048];
static const char* g_tickerText = g_tickerTextBuf;
static const float g_tickerSpeed = 80.0f; // pixels per second
struct TickerChunk {
    std::string text;
    Color color;
};
static std::vector<TickerChunk> g_tickerChunks;

static void RebuildTickerText();

// Terminal feedback system
struct TerminalMessage {
    char text[128];
    float age; // Time since message was added
    int visibleChars; // Number of characters currently visible (for typing effect)
    float typingProgress; // Progress of typing animation (0.0 to 1.0)
};
static std::vector<TerminalMessage> g_terminalMessages;
static const float g_terminalCursorX = 0.66f; // 66% of screen width
static const float g_terminalCursorY = 0.96f; // 96% of screen height (main text line at bottom)
static const float g_terminalLineHeight = 25.0f; // Line spacing
static const int g_terminalMaxRows = 6;      // 5 rows of terminal text + 1 dedicated build-status row
static const float g_terminalTypingSpeed = 30.0f; // Characters per second
static char g_liveCostPreview[128] = "";     // "New extended network line cost: ####" when in platform placement/drag
enum class BuildStatusState {
    None = 0,
    Possible,
    Blocked
};
static BuildStatusState g_buildStatusState = BuildStatusState::None;
static char g_buildStatusText[160] = "NO TARGET BUILD";

// Scalar game state
static int g_playerCredits = 50000;
static int g_nextLineId = 1;
static int g_selectedTrainIndex = -1;
// Small transient helper badge after auto-selecting a newly placed train.
static int g_junctionSetupTrainId = -1;
static float g_junctionSetupBadgeTimer = 0.0f;
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
// Placement orientation: 0=+X, 1=+Z, 2=-X, 3=-Z (cycles through all 4 cardinal directions)
static int g_placementOrientation = 0;
static bool g_bureauPlacementMode = false;
static bool g_demolishMode = false;

// Game speed
enum GameSpeedEnum { SPEED_PAUSE=0, SPEED_SLOW=1, SPEED_MEDIUM=2, SPEED_QUICK=3, SPEED_QUICKEST=4 };
static int g_currentGameSpeed = SPEED_PAUSE;

// Colors
static Color g_platformColor = {0, 255, 255, 200};
static Color g_stationColor = {0, 128, 128, 200};
static Color g_pointsColor = {0, 255, 255, 200};

// Debug counters
static int g_debugPreviousComponentCount = 0;
static int g_debugCurrentComponentCount = 0;
static int g_debugRenderStage = 0;   // 0=unknown, 1=splash, 2=gameover, 3=map, 4=3d
static int g_debugFrameCounter = 0;
static bool g_cameraDebugOverlay = false;
// 0=none,1=pan_lr,2=rot_lr,3=pan_ud,4=alt_ud,5=zoom
static int g_camDbgControlMode = 0;
static float g_camDbgStep = 0.0f;
static Vector3 g_camDbgMoveVector = {0.0f, 0.0f, 0.0f};
static int g_camDbgLogCounter = 0;

// UI Globals
static Texture2D g_texUI = { 0 };
static Texture2D g_texCursor = { 0 };
static bool g_uiAssetsLoaded = false;
static bool g_isMouseOverUI = false; // Tracks if mouse is over UI (blocking 3D interaction)
static Rectangle g_viewfinderRect = { 143, 81, 823, 429 }; // 3D viewport area within UI.png: from (143, 81) to (966, 510)
static Rectangle g_viewfinderCutoutRect = { 0, 0, 0, 0 };  // Bottom-left square cutout (6% of viewfinder)
static bool g_mouseInEffective3DArea = false;  // True when mouse is in viewfinder but NOT in cutout

// â”€â”€ Splash Screen â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
#define SPLASH_MOSAIC_LEVELS 6
enum class SplashPhase { FadeIn1, Mosaic2, Mosaic3, DimType, WaitSpace, Done };
static SplashPhase g_splashPhase     = SplashPhase::FadeIn1;
static float  g_splashTimer          = 0.0f;
static Texture2D g_splashTex1        = {0};
static Texture2D g_splashTex2        = {0};
static Texture2D g_splashTex3        = {0};
static Texture2D g_splashMosaicTex2[SPLASH_MOSAIC_LEVELS] = {};
static Texture2D g_splashMosaicTex3[SPLASH_MOSAIC_LEVELS] = {};
static float  g_splash12Bright       = 1.0f;  // brightness of SPLASH1+2 during dim phase
static int    g_splashTypeChars      = 0;
static float  g_splashTypeTimer      = 0.0f;
static bool   g_splashAssetsLoaded   = false;

// System hotspots: system1..system7, column at 2.6% x, 10.6% width, 22% height each, 2% gap
static Rectangle g_systemHotspots[7];
// Bottom icon hotspots: system8..system13
static Rectangle g_bottomHotspots[6];
static int g_selectedBottomHotspot = -1;  // 0-5 for system8-13, -1 = none

// system1 cargo UI cycle: 0=UI.png, 1=UI_cargo1_selected.png, 2=UI_cargo2_selected.png, 3=UI_cargo3_selected.png
static int g_system1CargoState = 0;
// Selected system hotspot (0-6) for PNG display only - NOT tied to placement modes
static int g_selectedSystemHotspot = -1;
// Train color for placement: 0=green/Passenger, 1=magenta, 2=cyan, 3=orange, 4=red, 5=yellow (sys2-7)
static int g_trainColorIndex = 0;
static Texture2D g_texUICargo1 = { 0 };
static Texture2D g_texUICargo2 = { 0 };
static Texture2D g_texUICargo3 = { 0 };
static Texture2D g_texUIGreen = { 0 };      // UI_green_selected_sys2.png for system2
static Texture2D g_texUISys3 = { 0 };  // UI_magenta_selected_sys3.png for system3
static Texture2D g_texUISys4 = { 0 };  // UI_cyan_selected_sys4.png
static Texture2D g_texUISys5 = { 0 };  // UI_orange_selected_sys5.png
static Texture2D g_texUISys6 = { 0 };  // UI_red_selected_sys6.png
static Texture2D g_texUISys7 = { 0 };  // UI_yellow_selected_sys7.png
static Texture2D g_texModalTemplate = { 0 };
static Texture2D g_texLargeModalTemplate = { 0 };
static Texture2D g_texModalConfirmSelected = { 0 };
static Texture2D g_texModalConfirmNotSelected = { 0 };
static Texture2D g_texGameOver1 = { 0 };
static Texture2D g_texGameOver2 = { 0 };
static int g_modalClickBlockFrames = 0;

// Forward declarations
static void LoadUIAssets();
static void UnloadUIAssets();
static void DrawUIOverlay();
static void DrawCustomCursor();
static void RestartToSplashAfterGameOver();

// Input helpers for embedded mode
static bool CustomIsKeyDown(int k) { return g_standalone_mode ? IsKeyDown(k) : (k>=0 && k<512 ? g_inputState.keys[k] : false); }
static bool CustomIsKeyPressed(int k) { return g_standalone_mode ? IsKeyPressed(k) : (k>=0 && k<512 ? g_inputState.keysPressed[k] : false); }
// Mouse clicks blocked by UI if not in viewfinder
static bool CustomIsMouseButtonPressed(int b) { 
    if (g_modalClickBlockFrames > 0) return false;
    if (g_isMouseOverUI) return false;
    return g_standalone_mode ? IsMouseButtonPressed(b) : (b>=0 && b<8 ? g_inputState.mouseButtonsPressed[b] : false); 
}
static bool RawIsMouseButtonPressed(int b) {
    if (g_modalClickBlockFrames > 0) return false;
    return g_standalone_mode ? IsMouseButtonPressed(b) : (b>=0 && b<8 ? g_inputState.mouseButtonsPressed[b] : false);
}
static void BlockMouseClicksAfterModalClose(int frames = 3) {
    if (frames > g_modalClickBlockFrames) g_modalClickBlockFrames = frames;
}
static bool CustomIsMouseButtonDown(int b) { 
    if (g_isMouseOverUI) return false;
    return g_standalone_mode ? IsMouseButtonDown(b) : (b>=0 && b<8 ? g_inputState.mouseButtons[b] : false); 
}
static bool CustomIsMouseButtonReleased(int b) {
    if (g_isMouseOverUI) return false;
    return g_standalone_mode ? IsMouseButtonReleased(b) : (b>=0 && b<8 ? g_inputState.mouseButtonsReleased[b] : false);
}
static Vector2 CustomGetMousePosition() { return g_standalone_mode ? GetMousePosition() : g_inputState.mousePosition; }
static Vector2 CustomGetMouseDelta() { return g_standalone_mode ? GetMouseDelta() : g_inputState.mouseDelta; }
static float CustomGetMouseWheelMove() { return g_standalone_mode ? GetMouseWheelMove() : g_inputState.mouseWheelMove; }

// Resolution-relative font size calculation
// Base resolution is 1200x800, font sizes are scaled proportionally
static float GetScaledFontSize(float baseSize) {
    // Scale based on height (800 is base height)
    float scaleFactor = (float)g_renderHeight / 800.0f;
    return baseSize * scaleFactor;
}

// Base font sizes (will be scaled based on resolution)
#define BASE_FONT_SIZE 18.0f
#define BASE_FONT_SIZE_LARGE 27.0f  // 50% larger than base (for mouse coordinates)

// Flag to track if line modal is open (set by modal code, checked by cursor code)
static bool g_lineModalOpen = false;
// Flag for junction modal (set when junction modal open/close; used by cursor code which runs before g_junctionModal is in scope)
static bool g_junctionModalOpen = false;
// Flag for Stock & Commodities Market modal
static bool g_stockModalOpen = false;
// Flag for Station configuration modal
static bool g_stationModalOpen = false;
// Flag for demolish-station confirmation modal
static bool g_demolishConfirmModalOpen = false;

// Check if cursor is visible (mouse is outside the 3D viewport, or in the bottom-left cutout)
static bool IsCursorVisible() {
    if (g_lineModalOpen) return true;
    if (g_junctionModalOpen) return true;
    if (g_stockModalOpen) return true;
    if (g_stationModalOpen) return true;
    if (g_demolishConfirmModalOpen) return true;
    if (g_mapMode) return true;
    Vector2 mousePos = CustomGetMousePosition();
    if (CheckCollisionPointRec(mousePos, g_viewfinderCutoutRect)) return true;  // Cutout = cursor visible
    return !CheckCollisionPointRec(mousePos, g_viewfinderRect);
}
static int CustomGetCharPressed() {
    if (g_standalone_mode) return GetCharPressed();
    if (g_inputState.charQueueHead == g_inputState.charQueueTail) return 0;
    int value = g_inputState.charQueue[g_inputState.charQueueHead];
    g_inputState.charQueueHead = (g_inputState.charQueueHead + 1) % 64;
    return value;
}
static void ClearCharInputQueue() {
    g_inputState.charQueueHead = 0;
    g_inputState.charQueueTail = 0;
}

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
        case SPEED_PAUSE: return "WORLD SPEED: PAUSED";
        case SPEED_SLOW: return "WORLD SPEED: SLOW";
        case SPEED_MEDIUM: return "WORLD SPEED: MEDIUM";
        case SPEED_QUICK: return "WORLD SPEED: QUICK";
        case SPEED_QUICKEST: return "WORLD SPEED: QUICKEST";
        default: return "WORLD SPEED: MEDIUM";
    }
}
static void ClearInputFrame() {
    memset(g_inputState.keysPressed, 0, sizeof(g_inputState.keysPressed));
    memset(g_inputState.keysReleased, 0, sizeof(g_inputState.keysReleased));
    memset(g_inputState.mouseButtonsPressed, 0, sizeof(g_inputState.mouseButtonsPressed));
    memset(g_inputState.mouseButtonsReleased, 0, sizeof(g_inputState.mouseButtonsReleased));
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

// --- Yearly calendar clock (1989 week layout) ---
// Each game "day cycle" is one week. Weeks per month = number of Mondays in that
// month of 1989 (Jan 1 1989 = Sunday). Gives exactly 52 weeks per year.
// Jan=5 Feb=4 Mar=4 Apr=4 May=5 Jun=4 Jul=5 Aug=4 Sep=4 Oct=5 Nov=4 Dec=4 â†’ 52 wks/yr
static const int kWeeksPerMonth1989[12] = { 5,4,4,4,5,4,5,4,4,5,4,4 };
static const int kWeeksPerYear1989 = 52; // sum of above

static void GetYearClock(int totalWeeks, int& outWk, int& outMonth, int& outYear) {
    outYear  = totalWeeks / kWeeksPerYear1989 + 1;
    int rem  = totalWeeks % kWeeksPerYear1989;
    outMonth = 1;
    for (int m = 0; m < 12; m++) {
        if (rem < kWeeksPerMonth1989[m]) { outMonth = m + 1; outWk = rem + 1; return; }
        rem -= kWeeksPerMonth1989[m];
    }
    outMonth = 12; outWk = kWeeksPerMonth1989[11]; // clamp
}

// Returns total elapsed months from week 0 (for monthly cost detection)
static int GetTotalMonths(int totalWeeks) {
    int year = totalWeeks / kWeeksPerYear1989;
    int rem  = totalWeeks % kWeeksPerYear1989;
    int month = 11;
    for (int m = 0; m < 12; m++) {
        if (rem < kWeeksPerMonth1989[m]) { month = m; break; }
        rem -= kWeeksPerMonth1989[m];
    }
    return year * 12 + month;
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

// Invalid placement preview: pulse between black and dark red.
static inline Color GetInvalidPreviewColor() {
    float pulse = (sinf((float)GetTime() * 4.0f) + 1.0f) * 0.5f;
    return LerpColor((Color){ 0, 0, 0, 220 }, (Color){ 120, 0, 0, 220 }, pulse);
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

// Cluster types for procedural generation (world-building / faction zones)
enum class ClusterType {
    CARGO,         // Raw materials cluster
    ClusterGreen,  // General Patriots (avoid Raylib GREEN macro)
    ClusterMagenta, // AI Industrial Workforce
    ClusterCyan,   // AI Technology Workforce
    ClusterOrange, // AI Administration Workforce
    ClusterRed,    // Transhuman Elites
    ClusterYellow  // Corporate Elite Executives
};

// Generated cluster: 5x5 block of grid cells, single type
struct Cluster {
    ClusterType type = ClusterType::CARGO;
    int x = 0;  // Top-left cell X
    int y = 0;  // Top-left cell Y
    int size = 5;  // Always 5x5
};

// Result of cluster generation: grid and cluster list
// Grid: -1 = empty, 0..9 = cluster index
struct ClusterGenResult {
    std::vector<std::vector<int>> grid;
    std::vector<Cluster> clusters;
};

// Player-placed factory (4x4 footprint)
struct PlacedFactory {
    Vector3 position; // centered on grid
    int lineOwnerId = -1; // Deterministic SYS1 ownership (assigned in recompute)
    int depotOwnerId = -1; // Deterministic parent depot (assigned in recompute)
    float productionCarry = 0.0f; // Fractional production carry for silo speed multipliers
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
    int placementOrientation;  // 0=+X, 1=+Z, 2=-X, 3=-Z (only used for stations; enables 4-way hotspot alignment)
    int stationPart;     // 0, 1, 2, or 3 for the segments of a station

    bool isDepot = false;   // Materials-Depot (not part of rail path)
    int depotCargo = 0;     // 0..8 cargo stored
    int lineOwnerId = -1;   // Deterministic SYS1 depot line ownership (assigned in recompute)
    int placementGroupId = -1;  // -1 = legacy (connects to all); else only connects to same group or at junctions
    bool isJunction = false;    // True when track crosses at this cell (multiple placement groups meet)
    // Station identity (stored on all 4 parts; authoritative on stationPart==0)
    char stationName[64] = {0};  // Player-assigned station name
    int stationDelayMode = 0;    // 0=flow (no pause), 1=short dwell (2s), 2=long dwell (10s)
};

// Line structure - represents an official train line connecting stations
struct Line {
    int id;                          // Unique line ID
    std::string name;                // Line name
    Color color;                     // Line color
    int chosenSystem = -1;           // Player-chosen or detected system identity for mixed-cluster lines
    int stationCount;                // Number of station components in this line
    std::set<long long> componentKeys; // Station component keys belonging to this line
    std::set<int> platformIndices;   // All platform indices (stations + track) that belong to this line
    std::set<long long> declinedComponentKeys; // User clicked "NO CONTINUE" on AddToLine for these components - never merge them into this line (any colour)
    std::set<long long> declinedBranchPlatformKeys; // Seed platform position keys for NO CONTINUE branches; survives component key churn
    bool isCrossingLine = false;     // True when created via "NO CONTINUE" - crossing line keeps only its explicit platforms, never merges whole component
};

// Modal state for line establishment
enum class LineModalState {
    None,
    ChooseSilo,         // Prompt to choose silo system when stations span multiple clusters
    EstablishLine,      // Prompt to establish a new line
    AddToLine          // Prompt to add to existing line or create new
};

// Stock & Commodities Market modal (launched by system13)
enum class MarketTab {
    Commodities = 0,
    Green,
    Magenta,
    Cyan,
    Orange,
    Red,
    COUNT
};

struct MarketListingState {
    float price = 100.0f;
    float previousPrice = 100.0f;
    float volatility = 0.05f;
    int trend = 0;           // -1 bear, 0 neutral, +1 bull
    int trendDaysLeft = 0;
    int sharesOwned = 0;
    float avgBuyPrice = 0.0f;
};

enum class MarketEventType {
    None = 0,
    SectorBoom,
    SectorCrash,
    CargoShortage,
    BureauDividend
};

struct MarketEvent {
    MarketEventType type = MarketEventType::None;
    int tabIndex = 0;
    int daysLeft = 0;
    float modifier = 0.0f;
    char description[128] = {};
};

struct StockCommoditiesModalData {
    bool open = false;
    int framesOpen = 0;
    bool closeClicked = false;
    MarketTab activeTab = MarketTab::Commodities;
    float scrollOffset = 0.0f;
    int selectedListing = -1;
};
static StockCommoditiesModalData g_stockModal;

static MarketListingState g_commodityStates[6];
static MarketListingState g_greenStockStates[6];
static MarketListingState g_magentaStockStates[6];
static MarketListingState g_cyanStockStates[6];
static MarketListingState g_orangeStockStates[6];
static MarketListingState g_redStockStates[6];

static std::vector<MarketEvent> g_activeMarketEvents;
static int g_dayCount = 0;
static int g_marketRevenueLast = 0;

static char g_dynamicTickerBuf[512] = "";
static bool g_hasDynamicTicker = false;

static std::mt19937 g_marketRng(12345);

enum class SiloSystem {
    SYS1_CARGO = 0,
    SYS2_GREEN = 1,
    SYS3_MAGENTA = 2,
    SYS4_CYAN = 3,
    SYS5_ORANGE = 4,
    SYS6_RED = 5,
    SYS7_YELLOW = 6
};

struct Silo {
    int id = 0;
    SiloSystem system = SiloSystem::SYS1_CARGO;
    int lineId = -1;
    int stationAId = -1;
    int stationBId = -1;
    int bureauStationId = -1;
    int bureauHeight = 0;
};

struct MarketListing {
    const char* symbol;
    const char* name;
};

static const MarketListing kCommodityListings[6] = {
    { "CMP-SYC", "Synthetic Concrete" },
    { "CMP-QFL", "Quantum Fibre Lattice" },
    { "CMP-NCS", "Nanocarbon Struts" },
    { "CMP-PGR", "Programmable Graphene" },
    { "CMP-DMA", "Dark Matter Aggregate" },
    { "CMP-ARC", "Arcology Seed Modules" }
};

static const MarketListing kGreenCorpListings[6] = {
    { "SUSH", "SunShine Synthetic Protien Corp" },
    { "RCHN", "Shoppe Til-Thee-Dye Inc" },
    { "ALSY", "Primate Grain Vodkas Inc" },
    { "NCOM", "Drinkable Toxins Inc" },
    { "ENMD", "PreFrontalMushFlix Inc" },
    { "BMLG", "Goliath Ion-Trucking Syndiacte" }
};

static const MarketListing kMagentaCorpListings[6] = {
    { "RBFD", "Kirby Robotics Foundry Inc" },
    { "HMWK", "Armaro Heavy Mech Works Inc" },
    { "DDSS", "Daisy Defense Systems Syndiacte" },
    { "ATRG", "Kinder Armoured Transit Group" },
    { "EXTT", "Bronze Rock Titan Rode Corp" },
    { "OSCP", "Statis Supply Corp" }
};

static const MarketListing kCyanCorpListings[6] = {
    { "NROS", "Neural OS Updates Inc" },
    { "QCOM", "Quantum Communications Inc" },
    { "MCLB", "Memory Crystal Labs" },
    { "PAIN", "Cardio Analytics Inc" },
    { "CLSP", "Concorde Copiers Inc" },
    { "BICE", "Black ICE Security Corp" }
};

static const MarketListing kOrangeCorpListings[6] = {
    { "SVGD", "Surveillance Grid" },
    { "PPRI", "Private Prisons" },
    { "CPSC", "Compliance Schools" },
    { "HASY", "Health Authority Systems" },
    { "PCBR", "Population Control Bureau" },
    { "SECT", "Security Contractors" }
};

static const MarketListing kRedCorpListings[6] = {
    { "LXTN", "Vanillia Sky Life Extension Inc" },
    { "AUGC", "Maxis Augmentation Clinics Corp" },
    { "GNSC", "Fire Third Gene Sculptors Inc" },
    { "MBVL", "The Mind-Backup Vaults Inner City Corp" },
    { "NMTR", "The Nano-Medicine Trust Inc" },
    { "SULB", "Hawk & Sonar Sensory Upgrade Labs Inc" }
};

static std::vector<Silo> g_silos;
static int g_siloCountBySystem[7] = { 0, 0, 0, 0, 0, 0, 0 };
static int g_previousSiloCountBySystem[7] = { 0, 0, 0, 0, 0, 0, 0 };

// Silo-created announcement modal (uses modal_template.png, one button to dismiss)
struct SiloAnnounceModalData {
    bool open = false;
    int system = 0;           // SiloSystem that was just created
    int framesOpen = 0;
    bool gotItClicked = false;
};
static SiloAnnounceModalData g_siloAnnounceModal;
static int g_commoditiesUnlocked = 0;
static int g_greenStocksUnlocked = 0;
static int g_magentaStocksUnlocked = 0;
static int g_cyanStocksUnlocked = 0;
static int g_orangeStocksUnlocked = 0;
static int g_redStocksUnlocked = 0;
static int g_greenGrowthFloorBonus = 0;  // Sum of bureau floors used by SYS2 silos; increases green growth odds
static int g_cyanGrowthFloorBonus = 0; // Sum of bureau floors used by SYS4 silos; increases cyan growth odds
static int g_orangeGrowthFloorBonus = 0; // Sum of bureau floors used by SYS5 silos; increases orange growth odds
static int g_redGrowthFloorBonus = 0; // Sum of bureau floors used by SYS6 silos; increases red growth odds
static int g_magentaGrowthFloorBonus = 0; // Sum of bureau floors linked to SYS3 magenta lines; boosts magenta+commodity share performance by 10% per floor
static bool g_marketUnlocked = false;
static int g_marketChaos = 50;
static int g_yellowEligibleBureauCount = 0;
static int g_yellowStationsOnEstablishedLinesCount = 0;
static int g_yellowTrainsOnEstablishedLinesCount = 0;
static int g_totalStationsOnEstablishedLines = 0;
static bool g_sysTrainMoving[7] = {false}; // indexed by SiloSystem enum value (0=cargo, 1=green, etc.)
static bool g_sysTrainWasMoving[7] = {false};
static int g_establishedLineCount = 0;
static std::set<int> g_establishedLineIds;  // Line IDs that have 2+ stations (established); used for platform color
static char g_sys7DiagnosticMsg[256] = "No established lines";
// When >= 0: the ID of a newly established line that has not yet received a matching-colour train.
// While set, sys8-12 bottom hotspots (platform/station/depot/factory/bureau) are locked with a grey overlay.
static int g_awaitingTrainForLineId = -1;

// Per-line bitmask of silo systems that need a bureau on that line (for preview coloring).
// Bit N = SiloSystem N could benefit from a bureau linked (via inner-ring station detection) to this line.
static std::unordered_map<int, int> g_lineBureauSiloPotential;

struct LineModalData {
    LineModalState state = LineModalState::None;
    int framesOpen = 0;              // Frames since modal opened; ignore clicks until >= 2 (avoids click-stomp)
    int targetLineId = -1;           // For AddToLine: which line to potentially add to
    long long newComponentKey = 0;   // New station component key that triggered the modal
    std::vector<long long> connectedComponentKeys; // Components that would be connected
    char nameBuffer[64] = {0};       // Text input buffer for line name
    int nameCursorPos = 0;           // Cursor position in name buffer
    Color selectedColor = {0, 255, 255, 200}; // Currently selected color (default cyan)
    int colorIndex = 0;              // Index into predefined colors
    int detectedSystem = -1;         // Silo system detected from cluster proximity (-1 = none, use default palette)
    std::vector<int> detectedSystems; // All silo systems detected (for ChooseSilo modal when 2+)
    int siloChoiceIndex = 0;         // Currently highlighted silo in ChooseSilo modal
    bool siloChoiceClicked = false;  // True if player confirmed silo choice
    bool establishClicked = false;   // True if Establish button was clicked
    bool addToLineClicked = false;   // True if Add to Line button was clicked
    bool cancelClicked = false;      // True if Cancel/Continue button was clicked
    std::vector<int> pendingNewPlatforms;   // Snapshot when AddToLine shown - platforms NOT in target (sync pollutes target before user clicks)
    std::vector<int> pendingJunctions;     // Snapshot when AddToLine shown - junctions between new and target
    std::set<int> targetPlatformIndicesAtShow;  // Target line's platform count at show time (survives sync pollution)
    int pendingCid = -1;                   // Component id when modal shown (fallback when compKey changes)
    std::vector<int> pendingEstablishPlatforms; // When establishing crossing: use these platforms instead of component
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
    // Persist the selected pair by exit position as well so settings survive
    // adjacency reordering when a junction gains or loses legs later.
    float exitAx = 0.0f, exitAz = 0.0f;
    float exitBx = 0.0f, exitBz = 0.0f;
    bool hasStoredPair = false;
};

// Helper to create a position key for junction lookups
inline long long MakePositionKey(float x, float z) {
    // Round to nearest grid position and create a unique key
    int ix = (int)(x * 10.0f);
    int iz = (int)(z * 10.0f);
    return ((long long)ix << 32) | (unsigned int)iz;
}

// Junction modal: shown when a track drag would cross existing track (same cell). User chooses BUILD JUNCTION or DO NOT BUILD.
struct JunctionModalData {
    bool open = false;
    int framesOpen = 0;
    bool buildJunctionClicked = false;
    bool doNotBuildClicked = false;
    Vector3 pendingStartPos = {0, 0, 0};
    Vector3 pendingEndPos = {0, 0, 0};
};
static JunctionModalData g_junctionModal;

// Junction configuration modal: opened when clicking a junction without a train selected.
// Lists all trains that pass through this junction and lets the player cycle each train's exit pair.
struct JunctionConfigModal {
    bool open = false;
    int  framesOpen = 0;
    int  junctionPlatformIndex = -1;   // index into g_placedPlatforms
    Vector3 junctionPos = {0, 0, 0};
    int  selectedTrainSlot = -1;       // which slot in trainIndices is selected
    std::vector<int> trainIndices;     // indices into g_placedTrains that use this junction
    bool doneClicked = false;
    bool switchClicked = false;        // user clicked SWITCH for selected train
};
static JunctionConfigModal g_junctionConfigModal;
static bool g_junctionConfigModalOpen = false;

// Station configuration modal: opened on station build and on neutral-click of a station tile.
struct StationModalData {
    bool open = false;
    int framesOpen = 0;
    bool confirmClicked = false;
    bool cancelClicked = false;
    int anchorPlatformIndex = -1;  // index of the stationPart==0 tile being configured
    char nameBuffer[64] = {0};
    int nameCursorPos = 0;
    int delayMode = 0;             // 0=flow, 1=short dwell (2s), 2=long dwell (10s)
    bool isNewBuild = false;       // true when opened immediately after a build (cancel refunds + removes)
};
static StationModalData g_stationModal;

// Modal: confirm demolishing a station or established-line track section
struct DemolishConfirmModal {
    bool open              = false;
    int  framesOpen        = 0;
    bool confirmClicked    = false;
    bool cancelClicked     = false;
    bool isStationDemolish = true;  // true=station, false=track section
    int  anchorIdx         = -1;    // stationPart==0 tile index (station demolish only)
    int  platformIdx       = -1;    // platform index to remove (track demolish only)
    int  lineIdx           = -1;    // first affected line (for display name only)
    char lineName[128]     = {0};
    char siloWarning[256]  = {0};   // non-empty if affected line(s) own silos
    bool hasAffectedTrains = false;
    int  affectedTrainCount = 0;
};
static DemolishConfirmModal g_demolishConfirmModal;

// Paused-train delete modal: shown when player clicks a paused (infrastructure-reset) train
struct PausedTrainDeleteModal {
    bool open           = false;
    int  framesOpen     = 0;
    bool confirmClicked = false;
    bool cancelClicked  = false;
    int  trainIndex     = -1;
};
static PausedTrainDeleteModal g_pausedTrainDeleteModal;

// Quit confirmation modal: shown when player presses ESC in 3D view or splash screen
struct QuitConfirmModal {
    bool open       = false;
    int  framesOpen = 0;
    bool yesClicked = false;
    bool noClicked  = false;
    bool quitToDesktop = false; // true = exit game entirely (splash), false = return to menu (in-game)
};
static QuitConfirmModal g_quitConfirmModal;
static bool g_quitConfirmModalOpen = false;

static int g_nextPlacementGroupId = 1;  // New track placements get this group; increments after each drag placement.

// Platform drag state (click-drag to place multiple track along a line)
static bool g_platformDragActive = false;
static Vector3 g_platformDragStartPos = {0, 0, 0};
static std::set<long long> g_platformDragPlacedKeys;
inline long long GridCellKey(float x, float z, float gridSize) {
    int ix = (int)roundf(x / gridSize);
    int iz = (int)roundf(z / gridSize);
    return ((long long)(ix + 10000) << 32) | (unsigned int)(iz + 10000);
}

// Collect all grid cell centers along a line from start to end (for drag-to-place).
// Uses DDA-style stepping so we never miss a cell the line passes through.
// Snapping: floor(cell)*gridSize + gridSize/2 = cell center (matches platform placement).
static void GetGridCellsAlongLine(Vector3 start, Vector3 end, float gridSize, std::vector<Vector3>& out) {
    out.clear();
    float dx = end.x - start.x;
    float dz = end.z - start.z;
    float len = sqrtf(dx*dx + dz*dz);
    if (len < 0.001f) {
        int cellIx = (int)floorf(start.x / gridSize);
        int cellIz = (int)floorf(start.z / gridSize);
        float halfGrid = gridSize / 2.0f;
        float cx = (float)cellIx * gridSize + halfGrid;
        float cz = (float)cellIz * gridSize + halfGrid;
        out.push_back({ cx, 0.0f, cz });
        return;
    }
    float halfGrid = gridSize / 2.0f;
    std::set<long long> seen;
    // Step by dt such that we move at most one cell per step (guarantees no missed cells)
    float absDx = fabsf(dx);
    float absDz = fabsf(dz);
    float maxDelta = fmaxf(absDx, absDz);
    float dt = (maxDelta < 0.001f) ? 1.0f : (gridSize / maxDelta);
    if (dt > 1.0f) dt = 1.0f;
    int maxSteps = (int)(1.0f / dt) + 3;
    if (maxSteps > 500) maxSteps = 500;  // Cap for very long lines
    for (int i = 0; i <= maxSteps; i++) {
        float t = (float)i * dt;
        if (t > 1.0f) t = 1.0f;
        float x = start.x + dx * t;
        float z = start.z + dz * t;
        int cellIx = (int)floorf(x / gridSize);
        int cellIz = (int)floorf(z / gridSize);
        float cellCenterX = (float)cellIx * gridSize + halfGrid;
        float cellCenterZ = (float)cellIz * gridSize + halfGrid;
        long long key = GridCellKey(cellCenterX, cellCenterZ, gridSize);
        if (seen.insert(key).second) {
            out.push_back({ cellCenterX, 0.0f, cellCenterZ });
        }
        if (t >= 1.0f) break;
    }
}

// Generate a connected L-shaped (or straight) path from start to end.
// Diagonal drags produce an L with the corner placed based on camera facing:
//   camera aligned more along Z â†’ horizontal (X) segment runs first (corner at far-X end)
//   camera aligned more along X â†’ vertical  (Z) segment runs first (corner at far-Z end)
// All cells are edge-connected â€” no diagonal steps.
static void GetGridCellsLShape(Vector3 start, Vector3 end, float gridSize, Vector3 cameraFwd,
                                std::vector<Vector3>& out) {
    out.clear();
    float halfGrid = gridSize * 0.5f;

    int sX = (int)floorf(start.x / gridSize);
    int sZ = (int)floorf(start.z / gridSize);
    int eX = (int)floorf(end.x / gridSize);
    int eZ = (int)floorf(end.z / gridSize);

    int dX = eX - sX;
    int dZ = eZ - sZ;

    auto addCell = [&](int cx, int cz) {
        out.push_back({ cx * gridSize + halfGrid, 0.0f, cz * gridSize + halfGrid });
    };

    if (dX == 0 && dZ == 0) { addCell(sX, sZ); return; }

    if (dX == 0) {  // pure vertical
        int step = (dZ > 0) ? 1 : -1;
        for (int z = sZ; z != eZ + step; z += step) addCell(sX, z);
        return;
    }
    if (dZ == 0) {  // pure horizontal
        int step = (dX > 0) ? 1 : -1;
        for (int x = sX; x != eX + step; x += step) addCell(x, sZ);
        return;
    }

    // Diagonal: build L-shape. Camera facing more along Z â†’ X first; more along X â†’ Z first.
    bool goXFirst = fabsf(cameraFwd.z) >= fabsf(cameraFwd.x);
    int stepX = (dX > 0) ? 1 : -1;
    int stepZ = (dZ > 0) ? 1 : -1;

    if (goXFirst) {
        for (int x = sX; x != eX + stepX; x += stepX) addCell(x, sZ);           // horizontal leg
        for (int z = sZ + stepZ; z != eZ + stepZ; z += stepZ) addCell(eX, z);   // vertical leg
    } else {
        for (int z = sZ; z != eZ + stepZ; z += stepZ) addCell(sX, z);           // vertical leg
        for (int x = sX + stepX; x != eX + stepX; x += stepX) addCell(x, eZ);  // horizontal leg
    }
}

// Placed train structure
struct PlacedTrain {
    enum class TrainType {
        Passenger,  // Green (sys2)
        Magenta,    // sys3
        Cyan,       // sys4
        Orange,     // sys5
        Red,        // sys6
        Yellow,     // sys7
        Cargo
    };

    int id = 0; // unique runtime id (used for station gate logic)
    TrainType type = TrainType::Passenger;
    int lineId = -1; // Explicit line ownership for deterministic silo calculations
    int cargoTrailers = 1; // only used when type == Cargo
    int cargoTotal = 0; // pooled cargo across the whole train (0..cargoTrailers*2) when Cargo
    long long lastTransferStationKey = (long long)0x7fffffffffffffffLL; // last station COMPONENT key under this train (or none)
    Vector3 position;  // Current center position of the train
    std::vector<Vector3> path;  // Path of platform positions the train follows
    float pathProgress;  // Current progress along the path (0.0 to pathLength)
    float direction;   // Movement direction: 1.0 for forward, -1.0 for backward
    float pathLength;  // Total length of the path
    std::vector<JunctionSetting> junctionSettings;  // Per-junction routing preferences

    // Dwell mode: pause at stations
    enum class DwellMode { FLOW = 0, SHORT_WAIT = 1, LONG_WAIT = 2 };
    DwellMode dwellMode = DwellMode::FLOW;
    float dwellTimer = 0.0f;
    bool isDwelling = false;
    float savedDirection = 1.0f;

    // Jam state: collision detection
    bool isJammed = false;
    float jamTimer = 0.0f;

    // Infrastructure pause state: train is stationary due to line demolish
    bool isPaused = false;           // stationary due to infrastructure reset
    Color pausedColor = {128,128,128,255}; // color of the line that was destroyed

    // Get junction setting for a specific position, returns -1 if not set
    int GetJunctionSetting(float x, float z, const std::vector<Vector3>* adjacent = nullptr) const {
        for (const auto& js : junctionSettings) {
            if (fabsf(js.x - x) < 0.1f && fabsf(js.z - z) < 0.1f) {
                if (adjacent != nullptr) {
                    if (js.hasStoredPair) {
                        int exitA = -1;
                        int exitB = -1;
                        for (int i = 0; i < (int)adjacent->size(); i++) {
                            const Vector3& pos = (*adjacent)[i];
                            if (fabsf(pos.x - js.exitAx) < 0.1f && fabsf(pos.z - js.exitAz) < 0.1f) exitA = i;
                            if (fabsf(pos.x - js.exitBx) < 0.1f && fabsf(pos.z - js.exitBz) < 0.1f) exitB = i;
                        }
                        if (exitA >= 0 && exitB >= 0 && exitA != exitB) {
                            if (exitA > exitB) std::swap(exitA, exitB);
                            int pairIndex = 0;
                            for (int i = 0; i < (int)adjacent->size() - 1; i++) {
                                for (int j = i + 1; j < (int)adjacent->size(); j++) {
                                    if (i == exitA && j == exitB) return pairIndex;
                                    pairIndex++;
                                }
                            }
                        }
                        return -1;
                    }
                }
                return js.exitIndex;
            }
        }
        return -1; // No preference recorded yet
    }
    
    // Set junction setting for a specific position
    void SetJunctionSetting(float x, float z, int exitIndex, const std::vector<Vector3>* adjacent = nullptr) {
        float exitAx = 0.0f, exitAz = 0.0f;
        float exitBx = 0.0f, exitBz = 0.0f;
        bool hasStoredPair = false;
        if (adjacent != nullptr && exitIndex >= 0) {
            int pairIndex = 0;
            for (int i = 0; i < (int)adjacent->size() - 1 && !hasStoredPair; i++) {
                for (int j = i + 1; j < (int)adjacent->size(); j++) {
                    if (pairIndex == exitIndex) {
                        exitAx = (*adjacent)[i].x;
                        exitAz = (*adjacent)[i].z;
                        exitBx = (*adjacent)[j].x;
                        exitBz = (*adjacent)[j].z;
                        hasStoredPair = true;
                        break;
                    }
                    pairIndex++;
                }
            }
        }
        for (auto& js : junctionSettings) {
            if (fabsf(js.x - x) < 0.1f && fabsf(js.z - z) < 0.1f) {
                js.exitIndex = exitIndex;
                js.exitAx = exitAx;
                js.exitAz = exitAz;
                js.exitBx = exitBx;
                js.exitBz = exitBz;
                js.hasStoredPair = hasStoredPair;
                return;
            }
        }
        // Not found, add new
        JunctionSetting js;
        js.x = x;
        js.z = z;
        js.exitIndex = exitIndex;
        js.exitAx = exitAx;
        js.exitAz = exitAz;
        js.exitBx = exitBx;
        js.exitBz = exitBz;
        js.hasStoredPair = hasStoredPair;
        junctionSettings.push_back(js);
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

// Factory smoke: white/grey cubes floating up from cylinder tops
struct FactorySmokeParticle {
    Vector3 position;
    Vector3 velocity;
    float lifetime;
    float maxLifetime;
    Color color;
    float size;
};

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
// GLOBAL GAME STATE (Type-dependent globals - must be after type definitions)
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

static std::vector<Building> g_buildings;
static std::vector<Cluster> g_clusters;
static std::vector<std::vector<int>> g_clusterGrid;  // -1 = empty, 0..9 = cluster index
static std::vector<PlacedPlatform> g_placedPlatforms;
static std::vector<PlacedTrain> g_placedTrains;
static std::vector<PlacedFactory> g_placedFactories;
static std::vector<PlacedBureau> g_placedBureaus;
static std::vector<Line> g_lines;
static std::vector<BuildParticle> g_buildParticles;
static std::vector<FactorySmokeParticle> g_factorySmokeParticles;
static float g_factorySmokeSpawnTimer = 0.0f;
static std::vector<long long> g_previousStationComponentKeys;

// â”€â”€ Performance caches (invalidated when platforms/lines change) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
static bool g_platformCacheDirty = true;
static bool g_lineCacheDirty = true;

static std::vector<int> g_cachedStationCompId;
static std::vector<long long> g_cachedStationCompKey;
static std::vector<std::vector<int>> g_cachedStationMembers;
static std::vector<int> g_cachedPlatformTypes;
static std::vector<int> g_cachedPlatformLineId;
static std::vector<std::vector<int>> g_cachedStationPrimePlatformIdx;
static std::vector<std::vector<Vector3>> g_cachedStationPrimePos;
static std::vector<char> g_cachedStationHasAdjacentDepot;
static std::vector<int> g_cachedBureauLineId;
static std::set<long long> g_declinedComponentKeys;
static std::set<long long> g_declinedNeutralBranchPlatformKeys;
static std::unordered_map<long long, int> g_lockedBranchOwnerLineId; // platform posKey -> owning crossing line id
// Platform position keys freshly reset to neutral by demolish.
// Prevents auto-merge with adjacent established lines on next cache rebuild.
// Cleared when new platforms are placed.
static std::set<long long> g_demolishNeutralizedPlatformKeys;
// Overpass model for pure X crossings: position key -> placement groups that pass through without connecting.
static std::unordered_map<long long, std::unordered_set<int>> g_overpassGroupsByPosKey;

// Weekly upkeep: trains only
static int CalculateWeeklyRunningCosts() {
    int total = 0;
    for (const auto& t : g_placedTrains) {
        switch (t.type) {
            case PlacedTrain::TrainType::Cargo:     total += 10 * t.cargoTrailers; break;
            case PlacedTrain::TrainType::Passenger: total += 25; break;
            case PlacedTrain::TrainType::Magenta:   total += 20; break;
            case PlacedTrain::TrainType::Cyan:      total += 20; break;
            case PlacedTrain::TrainType::Orange:    total += 20; break;
            case PlacedTrain::TrainType::Red:       total += 50; break;
            case PlacedTrain::TrainType::Yellow:    total += 80; break;
            default: break;
        }
    }
    return total;
}

static int GetTrainBuildCost(PlacedTrain::TrainType type, int cargoTrailers = 1) {
    switch (type) {
        case PlacedTrain::TrainType::Cargo:
            if (cargoTrailers <= 1) return 30;
            if (cargoTrailers == 2) return 80;
            return 100; // 3 trailers
        case PlacedTrain::TrainType::Passenger: return 150; // Green
        case PlacedTrain::TrainType::Magenta:   return 100;
        case PlacedTrain::TrainType::Cyan:      return 100;
        case PlacedTrain::TrainType::Orange:    return 100;
        case PlacedTrain::TrainType::Red:       return 200;
        case PlacedTrain::TrainType::Yellow:    return 300;
        default: return 0;
    }
}

// Monthly upkeep: track tiles, stations, depots, factories, bureaus
static int CalculateMonthlyRunningCosts() {
    int total = 0;
    int stationCount = 0;
    int trackCount   = 0;
    int depotCount   = 0;
    for (const auto& p : g_placedPlatforms) {
        if (p.isDepot) { depotCount++; continue; }
        if (p.isStation) { if (p.stationPart == 0) stationCount++; }
        else trackCount++;
    }
    total += trackCount   *   5;   // 5 CR/track tile/month
    total += stationCount * 100;   // 100 CR/station/month
    total += depotCount   *  50;   // 50 CR/depot/month
    total += (int)g_placedFactories.size() * 200; // 200 CR/factory/month
    for (const auto& b : g_placedBureaus) {
        total += b.floors * 20;    // 20 CR/floor/month
    }
    return total;
}


static void InvalidatePlatformCaches() { g_platformCacheDirty = true; g_lineCacheDirty = true; }
static void InvalidateLineCaches() { g_lineCacheDirty = true; }

static void ClearAllPlacementModes() {
    g_trainPlacementMode = false;
    g_cargoTrainPlacementMode = false;
    g_stationPlacementMode = false;
    g_depotPlacementMode = false;
    g_factoryPlacementMode = false;
    g_bureauPlacementMode = false;
    g_demolishMode = false;
    g_selectedBottomHotspot = -1;
    g_selectedSystemHotspot = -1;
    g_platformDragActive = false;
    g_liveCostPreview[0] = '\0';
}

static bool IsPassengerTrainPlacementSelected() {
    return g_trainPlacementMode && g_selectedSystemHotspot >= 1 && g_selectedSystemHotspot <= 6;
}

static bool IsTrackPlacementSelected() {
    return g_trainPlacementMode && !IsPassengerTrainPlacementSelected();
}
// â”€â”€ End performance caches â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
static LineModalData g_lineModal;
static const std::vector<int> g_bureauFloorOptions = {1, 2, 3, 4, 5, 10, 15, 20, 30, 40, 50, 75, 100, 150, 200};

static int GetBureauCargoCost(int floorIndex) {
    switch (floorIndex) {
        case 0: return 1;
        case 1: return 2;
        case 2: return 3;
        case 3: return 4;
        case 4: return 8;
        case 5: return 10;
        default: return 10 + (floorIndex - 5) * 3;
    }
}

// Bureau build cost scales by line/system importance.
// Fallback (neutral/cargo) stays cheapest because it does not directly unlock non-cargo bureau income.
static int GetBureauCostPerFloorForSystem(int system) {
    switch (system) {
        case (int)SiloSystem::SYS2_GREEN:   return 3500;
        case (int)SiloSystem::SYS3_MAGENTA: return 4000;
        case (int)SiloSystem::SYS4_CYAN:    return 5000;
        case (int)SiloSystem::SYS5_ORANGE:  return 4500;
        case (int)SiloSystem::SYS6_RED:     return 5500;
        case (int)SiloSystem::SYS7_YELLOW:  return 6000;
        case (int)SiloSystem::SYS1_CARGO:   return 3000;
        default:                            return 3000;
    }
}

// Cyan silo bonus: 5% running cost reduction per bureau floor, capped at 95%
static float GetRunningCostMultiplier() {
    float reduction = g_cyanGrowthFloorBonus * 0.05f;
    if (reduction > 0.95f) reduction = 0.95f;
    return 1.0f - reduction;
}
// Red silo bonus: 10% build credit reduction per bureau floor, capped at 90%
static float GetBuildCostMultiplier() {
    float reduction = g_redGrowthFloorBonus * 0.10f;
    if (reduction > 0.90f) reduction = 0.90f;
    return 1.0f - reduction;
}
static int ApplyBuildDiscount(int cost) {
    return (int)ceilf((float)cost * GetBuildCostMultiplier());
}
// Orange silo bonus: 1 cargo reduction per bureau floor on bureau placement, min 0
static int ApplyOrangeBureauDiscount(int cargoCost) {
    int reduced = cargoCost - g_orangeGrowthFloorBonus;
    return reduced < 0 ? 0 : reduced;
}

static inline bool IsPassengerStyleTrain(PlacedTrain::TrainType type) {
    return type == PlacedTrain::TrainType::Passenger || type == PlacedTrain::TrainType::Magenta
        || type == PlacedTrain::TrainType::Cyan || type == PlacedTrain::TrainType::Orange
        || type == PlacedTrain::TrainType::Red || type == PlacedTrain::TrainType::Yellow;
}
static inline Color GetTrainColorForType(PlacedTrain::TrainType type, float brightnessMul = 1.0f) {
    Color base;
    switch (type) {
        case PlacedTrain::TrainType::Passenger: base = (Color){   0, 255,   0, 204 }; break; // Green
        case PlacedTrain::TrainType::Magenta:   base = (Color){ 255,   0, 255, 204 }; break;
        case PlacedTrain::TrainType::Cyan:      base = (Color){   0, 255, 255, 204 }; break;
        case PlacedTrain::TrainType::Orange:    base = (Color){ 255, 165,   0, 204 }; break;
        case PlacedTrain::TrainType::Red:       base = (Color){ 255,   0,   0, 204 }; break;
        case PlacedTrain::TrainType::Yellow:    base = (Color){ 255, 255,   0, 204 }; break;
        default: base = (Color){ 0, 255, 0, 204 }; break;
    }
    return MulColor(base, brightnessMul);
}
static inline float GetTrainTotalLength(const PlacedTrain& train, float gridSize) {
    // Passenger-style trains: 4 cars (green, magenta, cyan, orange, red, yellow)
    if (IsPassengerStyleTrain(train.type)) return gridSize * 4.0f;
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
// 4 legs and a flat top.  Optional basePlateOverride replaces the default grey base plate colour.
void DrawPlatform(Vector3 position, float gridSize, Color color, bool invalidPreview = false, Color basePlateOverride = {0,0,0,0}) {
    if (invalidPreview) color = GetInvalidPreviewColor();
    float legWidth = gridSize * 0.15f;
    float legHeight = gridSize * 0.7f;
    float topThickness = gridSize * 0.1f;
    float topSize = gridSize;
    float legOffset = gridSize * 0.25f;
    
    float baseThickness = gridSize * 0.07f;
    float baseY = position.y + baseThickness / 2.0f;
    Color baseColor;
    if (invalidPreview)
        baseColor = color;
    else if (basePlateOverride.a > 0)
        baseColor = basePlateOverride;
    else
        baseColor = (Color){ 128, 128, 128, 179 };
    DrawCube((Vector3){position.x, baseY, position.z}, topSize, baseThickness, topSize, baseColor);
    
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

// Draw animated cyberpunk billboards on stations
void DrawStationBillboards(Vector3 position, float gridSize, float currentTime) {
    // Calculate top platform position
    float legHeight = gridSize * 0.7f;
    float topThickness = gridSize * 0.1f;
    float topY = position.y + legHeight + topThickness / 2.0f;
    float billboardHeight = gridSize * 0.4f;  // Height of billboard
    float billboardWidth = gridSize * 0.3f;   // Width of billboard
    float billboardThickness = gridSize * 0.05f; // Thickness/depth
    
    // Billboard positions around the station (one on each side)
    // Using offset from center to position billboards at edges
    float offset = gridSize * 0.35f; // Position near edge of platform
    
    // Define billboard colors: pink, blue (yellow and orange removed)
    Color billboardColors[2] = {
        {255, 20, 147, 255},  // Pink (DeepPink)
        {0, 191, 255, 255}    // Blue (DeepSkyBlue)
    };
    
    // Positions: front (pink), back (blue) - keeping exact positions
    Vector3 billboardPositions[2] = {
        {position.x, topY + billboardHeight / 2.0f, position.z + offset},      // Front (+Z) - Pink
        {position.x, topY + billboardHeight / 2.0f, position.z - offset}       // Back (-Z) - Blue
    };
    
    // Draw 2 billboards (pink front, blue back), each with different animation phases
    for (int i = 0; i < 2; i++) {
        // Create pulsing/flashing effect with different phases for each billboard
        // Each billboard pulses at slightly different rate for variety
        float pulseSpeed = 3.0f + i * 0.5f; // Different speed per billboard (3.0, 3.5)
        float phase = currentTime * pulseSpeed + i * 1.57f; // Different phase offset
        
        // Pulsing brightness: oscillates between 0.4 and 1.0
        float pulse = (sinf(phase) + 1.0f) / 2.0f; // 0 to 1
        float minBrightness = 0.4f;
        float brightness = minBrightness + pulse * (1.0f - minBrightness);
        
        // Flashing effect: occasionally flash bright
        float flashPhase = currentTime * 8.0f + i * 2.0f; // Fast flash cycle
        float flash = sinf(flashPhase);
        if (flash > 0.9f) { // Flash when sine is near peak
            brightness = 1.0f + (flash - 0.9f) * 5.0f; // Extra bright flash
            brightness = Clamp(brightness, 0.0f, 1.5f);
        }
        
        // Apply brightness to color
        Color billboardColor = billboardColors[i];
        billboardColor.r = (unsigned char)Clamp((int)(billboardColor.r * brightness), 0, 255);
        billboardColor.g = (unsigned char)Clamp((int)(billboardColor.g * brightness), 0, 255);
        billboardColor.b = (unsigned char)Clamp((int)(billboardColor.b * brightness), 0, 255);
        
        // Add a subtle glow effect by drawing a slightly larger, more transparent version first (behind)
        Color glowColor = billboardColors[i];
        float glowBrightness = brightness * 0.4f; // Glow is dimmer
        glowColor.r = (unsigned char)Clamp((int)(glowColor.r * glowBrightness), 0, 255);
        glowColor.g = (unsigned char)Clamp((int)(glowColor.g * glowBrightness), 0, 255);
        glowColor.b = (unsigned char)Clamp((int)(glowColor.b * glowBrightness), 0, 255);
        glowColor.a = (unsigned char)(150 * brightness); // Semi-transparent glow
        
        // Draw glow behind billboard (slightly offset back)
        Vector3 glowPos = billboardPositions[i];
        if (i == 0) {
            glowPos.z -= billboardThickness * 0.3f; // Front billboard (pink) - move glow back
        } else {
            glowPos.z += billboardThickness * 0.3f; // Back billboard (blue) - move glow forward
        }
        
        // Both billboards face forward/back (not sideways)
        DrawCube(glowPos, billboardWidth * 1.15f, billboardHeight * 1.1f, billboardThickness * 0.6f, glowColor);
        
        // Draw billboard as a thin vertical rectangle (simple 3D form)
        // Both front and back face forward/back (toward/away from center)
        DrawCube(billboardPositions[i], billboardWidth, billboardHeight, billboardThickness, billboardColor);
    }
}

// Materials-Depot: same footprint as a platform but 50% shorter (legs + top thickness halved)
void DrawMaterialsDepot(Vector3 position, float gridSize, Color color, int cargoCount, bool invalidPreview = false) {
    Color useColor = invalidPreview ? GetInvalidPreviewColor() : color;
    float legWidth = gridSize * 0.15f;
    float legHeight = gridSize * 0.35f;     // 50% of normal (0.7)
    float topThickness = gridSize * 0.05f;  // 50% of normal (0.1)
    float topSize = gridSize;
    float legOffset = gridSize * 0.25f;

    Color legColor = invalidPreview ? useColor : (Color){ 255, 255, 0, 220 };   // Yellow legs (or red when invalid)
    Color topColor = invalidPreview ? useColor : (Color){ 139, 90, 43, 220 };  // Brown top slab (or red when invalid)

    float legBaseY = position.y;
    float topY = legBaseY + legHeight + topThickness / 2.0f;

    // Legs (yellow)
    DrawCube((Vector3){position.x - legOffset, legBaseY + legHeight / 2.0f, position.z + legOffset}, legWidth, legHeight, legWidth, legColor);
    DrawCube((Vector3){position.x + legOffset, legBaseY + legHeight / 2.0f, position.z + legOffset}, legWidth, legHeight, legWidth, legColor);
    DrawCube((Vector3){position.x - legOffset, legBaseY + legHeight / 2.0f, position.z - legOffset}, legWidth, legHeight, legWidth, legColor);
    DrawCube((Vector3){position.x + legOffset, legBaseY + legHeight / 2.0f, position.z - legOffset}, legWidth, legHeight, legWidth, legColor);

    // Top slab (brown)
    DrawCube((Vector3){position.x, topY, position.z}, topSize, topThickness, topSize, topColor);

    // Decorative cubes under the top slab, at the edges: 2 green on one pair of opposite sides, 2 orange on the other
    float decoBlockSize = gridSize * 0.11f;
    float edgeOffset = gridSize * 0.42f;
    float pairSpacing = decoBlockSize * 1.02f;  // Two cubes next to each other, hardly any gap
    float decoY = legBaseY + legHeight / 2.0f;
    Color greenColor = invalidPreview ? useColor : (Color){ 0, 255, 0, 235 };
    Color orangeColor = invalidPreview ? useColor : (Color){ 255, 165, 0, 235 };
    // Green cubes: -Z and +Z edges (2 per edge, side by side)
    DrawCube((Vector3){ position.x - pairSpacing / 2.0f, decoY, position.z - edgeOffset }, decoBlockSize, decoBlockSize, decoBlockSize, greenColor);
    DrawCube((Vector3){ position.x + pairSpacing / 2.0f, decoY, position.z - edgeOffset }, decoBlockSize, decoBlockSize, decoBlockSize, greenColor);
    DrawCube((Vector3){ position.x - pairSpacing / 2.0f, decoY, position.z + edgeOffset }, decoBlockSize, decoBlockSize, decoBlockSize, greenColor);
    DrawCube((Vector3){ position.x + pairSpacing / 2.0f, decoY, position.z + edgeOffset }, decoBlockSize, decoBlockSize, decoBlockSize, greenColor);
    // Orange cubes: -X and +X edges (2 per edge, side by side)
    DrawCube((Vector3){ position.x - edgeOffset, decoY, position.z - pairSpacing / 2.0f }, decoBlockSize, decoBlockSize, decoBlockSize, orangeColor);
    DrawCube((Vector3){ position.x - edgeOffset, decoY, position.z + pairSpacing / 2.0f }, decoBlockSize, decoBlockSize, decoBlockSize, orangeColor);
    DrawCube((Vector3){ position.x + edgeOffset, decoY, position.z - pairSpacing / 2.0f }, decoBlockSize, decoBlockSize, decoBlockSize, orangeColor);
    DrawCube((Vector3){ position.x + edgeOffset, decoY, position.z + pairSpacing / 2.0f }, decoBlockSize, decoBlockSize, decoBlockSize, orangeColor);

    // Cargo visualization (0..8 small white blocks on top)
    cargoCount = Clamp(cargoCount, 0, 8);
    if (cargoCount > 0) {
        float blockSize = gridSize * 0.22f;
        float blockY = topY + topThickness / 2.0f + blockSize / 2.0f + 0.02f;
        Color cargoColor = invalidPreview ? useColor : (Color){ 245, 245, 245, 235 };

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
void DrawFactory(Vector3 center, float gridSize, Color color, bool invalidPreview = false) {
    Color invColor = invalidPreview ? GetInvalidPreviewColor() : color;
    float baseW = gridSize * 4.0f;
    float baseD = gridSize * 4.0f;
    float baseH = gridSize * 1.4f;

    // Brown base (slightly shorter to leave room for grey top face)
    float topFaceH = gridSize * 0.08f;
    float brownH = baseH - topFaceH;
    Vector3 baseCenter = { center.x, center.y + brownH / 2.0f, center.z };
    float factoryAlpha = 0.70f;  // 15% less transparent than 0.55
    Color baseColor = invalidPreview ? invColor : (Color){ 139, 90, 43, (unsigned char)(220 * factoryAlpha) };  // Brown base (or red when invalid)
    DrawCube(baseCenter, baseW, brownH, baseD, baseColor);

    // Grey top face of base (darkened by 25% from 154 -> ~115)
    Color topFaceGrey = invalidPreview ? invColor : (Color){ 115, 115, 115, (unsigned char)(220 * factoryAlpha) };
    Vector3 topCapCenter = { center.x, center.y + brownH + topFaceH / 2.0f, center.z };
    DrawCube(topCapCenter, baseW * 0.98f, topFaceH, baseD * 0.98f, topFaceGrey);

    // Roof cap (grey)
    Color roofColor = invalidPreview ? invColor : (Color){ (unsigned char)(color.r * 0.85f), (unsigned char)(color.g * 0.85f), (unsigned char)(color.b * 0.85f), baseColor.a };
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

    Color stackColor = invalidPreview ? invColor : (Color){ 139, 90, 43, (unsigned char)(220 * factoryAlpha) };
    DrawCube(s1, stackW, stackH1, stackD, stackColor);
    DrawCube(s2, stackW, stackH2, stackD, stackColor);
    DrawCube(s3, stackW, stackH3, stackD, stackColor);

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

    DrawTriangle3D(a, b, c2, stackColor);
    DrawTriangle3D(a, c2, d2, stackColor);
    DrawTriangle3D(a, d2, d, stackColor); // side fill
    DrawTriangle3D(a, c, c2, stackColor); // small fill

    // Two red cylinder stacks: diameter 60% of stack 2 width, 20% taller, side by side
    float cylinderRadius = (stackW * 0.6f) / 2.0f;
    float cylinderHeight = stackH2 * 1.2f;
    float cylinderSpacing = cylinderRadius * 2.12f;  // 5% more separation (was 2.02)
    Color cylinderColor = invalidPreview ? invColor : (Color){ 255, 0, 0, 220 };
    Color cylinderBlack = invalidPreview ? invColor : (Color){ 0, 0, 0, 255 };
    float blackHeight = cylinderHeight * 0.2f;
    float topRedHeight = cylinderHeight * 0.25f;
    Vector3 cyl1Base = { center.x - cylinderSpacing / 2.0f, roofY, center.z + gridSize * 0.4f };
    Vector3 cyl2Base = { center.x + cylinderSpacing / 2.0f, roofY, center.z + gridSize * 0.4f };
    DrawCylinder(cyl1Base, cylinderRadius, cylinderRadius, cylinderHeight, 16, cylinderColor);
    DrawCylinder(cyl2Base, cylinderRadius, cylinderRadius, cylinderHeight, 16, cylinderColor);
    // Black ring on top of each (20% height)
    Vector3 cyl1Black = { cyl1Base.x, roofY + cylinderHeight, cyl1Base.z };
    Vector3 cyl2Black = { cyl2Base.x, roofY + cylinderHeight, cyl2Base.z };
    DrawCylinder(cyl1Black, cylinderRadius, cylinderRadius, blackHeight, 16, cylinderBlack);
    DrawCylinder(cyl2Black, cylinderRadius, cylinderRadius, blackHeight, 16, cylinderBlack);
    // Red cap on top of black (10% height)
    Vector3 cyl1Top = { cyl1Base.x, roofY + cylinderHeight + blackHeight, cyl1Base.z };
    Vector3 cyl2Top = { cyl2Base.x, roofY + cylinderHeight + blackHeight, cyl2Base.z };
    DrawCylinder(cyl1Top, cylinderRadius, cylinderRadius, topRedHeight, 16, cylinderColor);
    DrawCylinder(cyl2Top, cylinderRadius, cylinderRadius, topRedHeight, 16, cylinderColor);

    // Three cubes on +Z side: green, brown, yellow (200% of depot cargo size), close together
    float cargoBlockSize = gridSize * 0.22f * 2.0f;
    float cubeSpacing = cargoBlockSize * 1.02f;
    float cubeY = center.y + baseH * 0.25f;
    float faceZ = center.z + baseD / 2.0f + cargoBlockSize / 2.0f;
    DrawCube((Vector3){ center.x - cubeSpacing, cubeY, faceZ }, cargoBlockSize, cargoBlockSize, cargoBlockSize, invalidPreview ? invColor : (Color){ 0, 255, 0, (unsigned char)(255 * factoryAlpha) });
    DrawCube((Vector3){ center.x, cubeY, faceZ }, cargoBlockSize, cargoBlockSize, cargoBlockSize, invalidPreview ? invColor : (Color){ 139, 90, 43, (unsigned char)(255 * factoryAlpha) });
    DrawCube((Vector3){ center.x + cubeSpacing, cubeY, faceZ }, cargoBlockSize, cargoBlockSize, cargoBlockSize, invalidPreview ? invColor : (Color){ 255, 255, 0, (unsigned char)(255 * factoryAlpha) });

    // Cyan rectangle on opposite side (-Z): lifted 20% above grid, 15% of factory height
    float rectHeight = baseH * 0.15f;
    float rectW = gridSize * 1.2f;
    float rectD = gridSize * 0.12f;
    float rectLift = baseH * 0.2f;
    float rectY = center.y + rectLift + rectHeight / 2.0f;
    float rectZ = center.z - baseD / 2.0f - rectD / 2.0f;
    DrawCube((Vector3){ center.x, rectY, rectZ }, rectW, rectHeight, rectD, invalidPreview ? invColor : (Color){ 0, 255, 255, (unsigned char)(220 * factoryAlpha) });
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
    const int particleCount = 50;
    const int MAX_TOTAL_PARTICLES = 300;
    const float burstSpeed = 8.0f;
    const float lifetime = 1.2f;
    const float particleSize = gridSize * 0.12f;

    // If already at the cap, cull oldest particles to make room
    if ((int)g_buildParticles.size() + particleCount > MAX_TOTAL_PARTICLES) {
        int toRemove = (int)g_buildParticles.size() + particleCount - MAX_TOTAL_PARTICLES;
        if (toRemove > (int)g_buildParticles.size()) toRemove = (int)g_buildParticles.size();
        g_buildParticles.erase(g_buildParticles.begin(), g_buildParticles.begin() + toRemove);
    }
    
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
static void UpdateTicker(float deltaTime) {
    if (g_marketUnlocked) RebuildTickerText();

    // Update ticker position (scrolls right to left)
    g_tickerPosition -= g_tickerSpeed * deltaTime;
    
    // Calculate ticker text width to determine when to loop
    float tickerFontSize = GetScaledFontSize(BASE_FONT_SIZE) * 2.0f; // 200% larger
    float textWidth = 0.0f;
    if (!g_tickerChunks.empty()) {
        for (const auto& ch : g_tickerChunks) textWidth += MeasureTextEx(gameFont, ch.text.c_str(), tickerFontSize, 0.0f).x;
    } else {
        textWidth = MeasureTextEx(gameFont, g_tickerText, tickerFontSize, 0.0f).x;
    }
    
    // Calculate ticker area (top-left: 6% X, 94.2% Y)
    float tickerStartX = (float)g_renderWidth * 0.06f;
    float tickerEndX = (float)g_renderWidth * 0.608f;
    float tickerWidth = tickerEndX - tickerStartX;
    
    // Reset position when text has scrolled completely off screen
    if (g_tickerPosition + textWidth < tickerStartX) {
        g_tickerPosition = tickerEndX; // Start from right side
    }
    
    // Initialize position on first frame
    if (g_tickerPosition == 0.0f) {
        g_tickerPosition = tickerEndX;
    }
}

static void DrawTicker() {
    // Calculate ticker area (top-left: 6% X, 94.2% Y)
    float tickerStartX = (float)g_renderWidth * 0.06f;
    float tickerEndX = (float)g_renderWidth * 0.608f;
    float tickerStartY = (float)g_renderHeight * 0.9545f;
    float tickerEndY = (float)g_renderHeight * 0.9805f;
    float tickerCenterY = (tickerStartY + tickerEndY) * 0.5f;
    
    // Calculate font size (200% larger)
    float tickerFontSize = GetScaledFontSize(BASE_FONT_SIZE) * 2.0f;
    
    // Pre-market ticker text is white as requested.
    Color tickerColor = WHITE;
    
    // Set up scissor mode to clip text to ticker area
    Rectangle tickerRect = { tickerStartX, tickerStartY, tickerEndX - tickerStartX, tickerEndY - tickerStartY };
    BeginScissorMode((int)tickerRect.x, (int)tickerRect.y, (int)tickerRect.width, (int)tickerRect.height);
    
    // Compute pulsing red/white color for "H FOR HELP" hint
    float pulseT = (sinf((float)GetTime() * 4.0f * PI) + 1.0f) * 0.5f; // 0..1, 2 Hz cycle
    Color helpPulseColor = {
        255,
        (unsigned char)(255.0f * pulseT),
        (unsigned char)(255.0f * pulseT),
        255
    }; // Lerps from RED (255,0,0) to WHITE (255,255,255)

    // Draw ticker text (centered vertically in the ticker area)
    if (!g_tickerChunks.empty()) {
        float x = g_tickerPosition;
        for (size_t ci = 0; ci < g_tickerChunks.size(); ci++) {
            const auto& ch = g_tickerChunks[ci];
            // First chunk is always "H FOR HELP | " â€“ pulse its color
            Color drawColor = (ci == 0) ? helpPulseColor : ch.color;
            DrawTextEx(gameFont, ch.text.c_str(), (Vector2){x, tickerCenterY - tickerFontSize * 0.5f}, tickerFontSize, 0.0f, drawColor);
            x += MeasureTextEx(gameFont, ch.text.c_str(), tickerFontSize, 0.0f).x;
        }
    } else {
        // Plain-text path (pre-market): draw "H FOR HELP" prefix with pulse, rest in white
        const char* helpPrefix = "H FOR HELP";
        size_t prefixLen = strlen(helpPrefix);
        float helpW = 0.0f;
        if (strncmp(g_tickerText, helpPrefix, prefixLen) == 0) {
            // Draw the "H FOR HELP" portion pulsing
            char helpBuf[16];
            strncpy(helpBuf, g_tickerText, prefixLen);
            helpBuf[prefixLen] = '\0';
            DrawTextEx(gameFont, helpBuf, (Vector2){g_tickerPosition, tickerCenterY - tickerFontSize * 0.5f}, tickerFontSize, 0.0f, helpPulseColor);
            helpW = MeasureTextEx(gameFont, helpBuf, tickerFontSize, 0.0f).x;
            // Draw the remainder in white
            DrawTextEx(gameFont, g_tickerText + prefixLen, (Vector2){g_tickerPosition + helpW, tickerCenterY - tickerFontSize * 0.5f}, tickerFontSize, 0.0f, tickerColor);
        } else {
            DrawTextEx(gameFont, g_tickerText, (Vector2){g_tickerPosition, tickerCenterY - tickerFontSize * 0.5f}, tickerFontSize, 0.0f, tickerColor);
        }
    }
    
    EndScissorMode();
}

// Returns the y position just below the last drawn line (start-of-next-line).
static float DrawWrappedText(const char* text, float x, float y, float maxW, float maxY,
                             float fontSize, Color color) {
    float lineHeight = fontSize * 1.3f;
    float lastY = y;
    float curX = x;
    float spaceW = MeasureTextEx(gameFont, " ", fontSize, 0.0f).x;
    
    char word[256];
    int wlen = 0;

    for (const char* p = text; ; p++) {
        if (*p == ' ' || *p == '\0') {
            if (wlen > 0) {
                word[wlen] = '\0';
                float addW = MeasureTextEx(gameFont, word, fontSize, 0.0f).x;
                
                if (curX > x && curX + addW > x + maxW) {
                    if (y > maxY) return lastY + lineHeight;
                    y += lineHeight;
                    lastY = y;
                    curX = x;
                }
                
                Color c = color;
                char clean[256];
                int cidx = 0;
                for (int i = 0; i < wlen; i++) {
                    if ((word[i] >= 'A' && word[i] <= 'Z') || (word[i] >= 'a' && word[i] <= 'z')) {
                        clean[cidx++] = (word[i] >= 'a' && word[i] <= 'z') ? word[i] - 32 : word[i];
                    }
                }
                clean[cidx] = '\0';

                if (strcmp(clean, "GREEN") == 0) c = (Color){120, 255, 120, 255};
                else if (strcmp(clean, "MAGENTA") == 0) c = (Color){255, 80, 255, 255};
                else if (strcmp(clean, "CYAN") == 0) c = (Color){0, 255, 255, 255};
                else if (strcmp(clean, "ORANGE") == 0) c = (Color){255, 165, 0, 255};
                else if (strcmp(clean, "YELLOW") == 0) c = (Color){255, 215, 60, 255};
                else if (strcmp(clean, "RED") == 0) c = (Color){255, 80, 80, 255};
                else if (strcmp(clean, "CARGO") == 0) c = (Color){170, 140, 100, 255};

                DrawTextEx(gameFont, word, (Vector2){curX, y}, fontSize, 0.0f, c);
                curX += addW + spaceW;
                wlen = 0;
            }
            if (!*p) break;
        } else {
            if (wlen < (int)sizeof(word) - 1) word[wlen++] = *p;
        }
    }
    return lastY + lineHeight;
}

// Terminal feedback system - STRICT: exactly 5 lines total, no more
static int CountWrappedLines(const char* text, float fontSize, float maxWidth) {
    float terminalFontSize = fontSize * 1.125f;
    char lineBuf[128];
    int lineLen = 0;
    lineBuf[0] = '\0';
    int lineCount = 0;
    const char* wordStart = text;
    for (const char* p = text; ; p++) {
        bool atWordEnd = (!*p || *p == ' ');
        if (atWordEnd && wordStart < p) {
            char word[64];
            size_t wlen = (size_t)(p - wordStart);
            if (wlen >= sizeof(word)) wlen = sizeof(word) - 1;
            memcpy(word, wordStart, wlen);
            word[wlen] = '\0';
            float addW = MeasureTextEx(gameFont, word, terminalFontSize, 0.0f).x;
            float curW = (lineLen > 0) ? MeasureTextEx(gameFont, lineBuf, terminalFontSize, 0.0f).x : 0.0f;
            if (lineLen > 0 && curW + addW + 2.0f > maxWidth) {
                lineCount++;
                lineLen = 0;
                lineBuf[0] = '\0';
            }
            if (lineLen > 0) { lineBuf[lineLen++] = ' '; lineBuf[lineLen] = '\0'; }
            for (size_t i = 0; word[i] && lineLen < (int)sizeof(lineBuf) - 1; i++) lineBuf[lineLen++] = word[i];
            lineBuf[lineLen] = '\0';
            wordStart = p;
        }
        if (!*p) break;
        if (*p == ' ') wordStart = p + 1;
    }
    if (lineLen > 0) lineCount++;
    return (lineCount > 0) ? lineCount : 1;
}

static std::vector<std::string> WrapTerminalTextLines(const char* text, float fontSize, float maxWidth) {
    float terminalFontSize = fontSize * 1.125f;
    std::vector<std::string> lines;
    char lineBuf[128];
    int lineLen = 0;
    lineBuf[0] = '\0';
    const char* wordStart = text;
    for (const char* p = text; ; p++) {
        bool atWordEnd = (!*p || *p == ' ');
        if (atWordEnd && wordStart < p) {
            char word[64];
            size_t wlen = (size_t)(p - wordStart);
            if (wlen >= sizeof(word)) wlen = sizeof(word) - 1;
            memcpy(word, wordStart, wlen);
            word[wlen] = '\0';
            float addW = MeasureTextEx(gameFont, word, terminalFontSize, 0.0f).x;
            float curW = (lineLen > 0) ? MeasureTextEx(gameFont, lineBuf, terminalFontSize, 0.0f).x : 0.0f;
            if (lineLen > 0 && curW + addW + 2.0f > maxWidth) {
                lines.push_back(lineBuf);
                lineLen = 0;
                lineBuf[0] = '\0';
            }
            if (lineLen > 0) { lineBuf[lineLen++] = ' '; lineBuf[lineLen] = '\0'; }
            for (size_t i = 0; word[i] && lineLen < (int)sizeof(lineBuf) - 1; i++) lineBuf[lineLen++] = word[i];
            lineBuf[lineLen] = '\0';
            wordStart = p;
        }
        if (!*p) break;
        if (*p == ' ') wordStart = p + 1;
    }
    if (lineLen > 0) lines.push_back(lineBuf);
    if (lines.empty()) lines.push_back("");
    return lines;
}

static void AddTerminalMessage(const char* message) {
    g_terminalMessages.clear();
    TerminalMessage msg;
    snprintf(msg.text, sizeof(msg.text), "%s", message);
    msg.age = 0.0f;
    msg.visibleChars = 0;
    msg.typingProgress = 0.0f;
    g_terminalMessages.push_back(msg);
}

static void AppendTerminalMessage(const char* message) {
    // Unlike AddTerminalMessage, this does NOT clear existing messages
    TerminalMessage msg;
    snprintf(msg.text, sizeof(msg.text), "%s", message);
    msg.age = 0.0f;
    msg.visibleChars = 0;
    msg.typingProgress = 0.0f;
    g_terminalMessages.push_back(msg);
    // Trim to max rows
    if (g_terminalMessages.size() > (size_t)g_terminalMaxRows * 2) {
        g_terminalMessages.erase(g_terminalMessages.begin());
    }
}

static void SetBuildStatusNone() {
    g_buildStatusState = BuildStatusState::None;
    snprintf(g_buildStatusText, sizeof(g_buildStatusText), "NO TARGET BUILD");
}

static void SetBuildStatusPossible() {
    g_buildStatusState = BuildStatusState::Possible;
    snprintf(g_buildStatusText, sizeof(g_buildStatusText), "BUILD STATUS: POSSIBLE");
}

static void SetBuildStatusBlocked(const char* reason) {
    g_buildStatusState = BuildStatusState::Blocked;
    if (!reason || !reason[0]) reason = "IMPOSSIBLE";
    snprintf(g_buildStatusText, sizeof(g_buildStatusText), "BUILD STATUS: %s", reason);
}

static void UpdateTerminal(float deltaTime) {
    for (auto& msg : g_terminalMessages) {
        msg.age += deltaTime;
        int textLength = (int)strlen(msg.text);
        if (msg.typingProgress < 1.0f) {
            msg.typingProgress += deltaTime * g_terminalTypingSpeed / (float)(textLength > 0 ? textLength : 1);
            if (msg.typingProgress > 1.0f) msg.typingProgress = 1.0f;
            msg.visibleChars = (int)(msg.typingProgress * (float)textLength);
        } else {
            msg.visibleChars = textLength;
        }
    }
    
    // STRICT: keep only messages that fit in exactly 5 lines total
    float terminalX = (float)g_renderWidth * g_terminalCursorX;
    float terminalMaxWidth = (float)g_renderWidth - terminalX - 20.0f;
    float fontSize = GetScaledFontSize(BASE_FONT_SIZE);
    int statusLines = CountWrappedLines(g_buildStatusText, fontSize, terminalMaxWidth);
    if (statusLines < 1) statusLines = 1;
    if (statusLines > g_terminalMaxRows) statusLines = g_terminalMaxRows;
    int maxLines = g_terminalMaxRows - statusLines;

    int totalLines = 0;
    int eraseCount = 0;
    for (int i = (int)g_terminalMessages.size() - 1; i >= 0; i--) {
        int msgLines = CountWrappedLines(g_terminalMessages[i].text, fontSize, terminalMaxWidth);
        if (totalLines + msgLines <= maxLines) {
            totalLines += msgLines;
        } else {
            // Erase only OLDER messages (indices [0, i)); keep current so overflow is clipped to 5 lines
            eraseCount = i;
            break;
        }
    }
    if (eraseCount > 0 && eraseCount < (int)g_terminalMessages.size()) {
        g_terminalMessages.erase(g_terminalMessages.begin(), g_terminalMessages.begin() + eraseCount);
    }
}

// Returns short "how to build the silo for this train colour" tip for the feedback line when a train is selected.
// Cargo = Materials Silo; Passenger = Green; others = colour-name silos. Wording matches RecomputeSilos logic.
static const char* GetSiloBuildTipForTrainType(PlacedTrain::TrainType type) {
    switch (type) {
        case PlacedTrain::TrainType::Cargo:
            return "MATERIALS SILO: Build factory+depot cargo clusters, then establish a cargo line with at least 1 station in the cluster and a cargo train. Factory bonus only applies when this line has bureaus.";
        case PlacedTrain::TrainType::Passenger:
            return "GREEN SILO: Requires a green train. One bureau linked to an established line in the INNER CITY HUB unlocks one listing (capped by green stations). More linked bureau floors increase green growth odds.";
        case PlacedTrain::TrainType::Magenta:
            return "MAGENTA SILO: Requires a magenta train + a magenta-cluster station + an industry station within 2 grid spaces of a factory on the same established line. Factory bonus only applies when this line has bureaus.";
        case PlacedTrain::TrainType::Cyan:
            return "CYAN SILO: Requires cyan train + cyan station + linked bureau. Each bureau floor used by cyan silos raises cyan stock growth odds.";
        case PlacedTrain::TrainType::Orange:
            return "ORANGE SILO: Requires orange train + orange station + linked bureau on that established line. More linked bureau floors increase orange growth odds.";
        case PlacedTrain::TrainType::Red:
            return "RED SILO: Requires red train + red station + linked bureau on that established line. More linked bureau floors increase red growth odds.";
        case PlacedTrain::TrainType::Yellow:
            return "YELLOW SILO: Requires yellow train + yellow station + bureau linked to that established line via the bureau inner ring. Unlocks the Market.";
        default:
            return "Click junctions to set route. Build silos to unlock commodities and stock listings.";
    }
}

static void DrawTerminal() {
    float terminalX = (float)g_renderWidth * g_terminalCursorX;
    float terminalStartY = (float)g_renderHeight * g_terminalCursorY;
    float fontSize = GetScaledFontSize(BASE_FONT_SIZE);
    float terminalFontSize = fontSize * 1.125f;
    float scaledLineHeight = g_terminalLineHeight * (fontSize / BASE_FONT_SIZE);
    float terminalMaxWidth = (float)g_renderWidth - terminalX - 20.0f;
    std::vector<std::string> buildStatusLines = WrapTerminalTextLines(g_buildStatusText, fontSize, terminalMaxWidth);
    if ((int)buildStatusLines.size() > g_terminalMaxRows) buildStatusLines.resize(g_terminalMaxRows);
    const int statusLineCount = (int)buildStatusLines.size();
    const int messageAreaRows = g_terminalMaxRows - statusLineCount;
    float buildStatusBottomY = terminalStartY;

    // When a train is selected or cost preview is active, show feedback on the TOP line of the terminal
    // so the bottom row stays free for the newest messages (terminal reads top-to-bottom, newest at bottom).
    bool usedFirstLine = false;
    float feedbackY = terminalStartY - (float)(g_terminalMaxRows - 1) * scaledLineHeight;  // Top line of terminal
    auto drawFeedbackLine = [&](const char* text) {
        float ellipsisW = MeasureTextEx(gameFont, "...", terminalFontSize, 0.0f).x;
        char oneLine[256];
        int len = (int)strlen(text);
        if (len >= (int)sizeof(oneLine) - 4) len = (int)sizeof(oneLine) - 4;  // leave room for "..."
        strncpy(oneLine, text, (size_t)len);
        oneLine[len] = '\0';
        while (len > 0 && MeasureTextEx(gameFont, oneLine, terminalFontSize, 0.0f).x + ellipsisW > terminalMaxWidth) {
            oneLine[--len] = '\0';
        }
        if (len < (int)strlen(text) && len > 0) {
            oneLine[len++] = '.'; oneLine[len++] = '.'; oneLine[len++] = '.'; oneLine[len] = '\0';
        }
        DrawTextEx(gameFont, oneLine, (Vector2){terminalX, feedbackY}, terminalFontSize, 0.0f, (Color){ 0, 255, 0, 255 });
    };
    bool hasTerminalMessages = !g_terminalMessages.empty();
    if (!hasTerminalMessages && g_selectedTrainIndex >= 0 && g_selectedTrainIndex < (int)g_placedTrains.size()) {
        drawFeedbackLine(GetSiloBuildTipForTrainType(g_placedTrains[g_selectedTrainIndex].type));
        usedFirstLine = true;
    } else if (g_liveCostPreview[0] != '\0') {
        drawFeedbackLine(g_liveCostPreview);
        usedFirstLine = true;
    }
    if (g_terminalMessages.empty()) {
        Color statusColor = (Color){ 180, 180, 180, 255 };
        if (g_buildStatusState == BuildStatusState::Possible) {
            statusColor = (Color){ 0, 255, 255, 255 };
        } else if (g_buildStatusState == BuildStatusState::Blocked) {
            float pulse = (sinf((float)GetTime() * 4.0f) + 1.0f) * 0.5f;
            statusColor = LerpColor(BLACK, RED, pulse);
        }
        for (int i = 0; i < statusLineCount; i++) {
            float lineY = buildStatusBottomY - (float)(statusLineCount - 1 - i) * scaledLineHeight;
            DrawTextEx(gameFont, buildStatusLines[i].c_str(), (Vector2){terminalX, lineY}, terminalFontSize, 0.0f, statusColor);
        }
        return;
    }

    // Fixed slots above build status: feedback uses top line when present; messages use bottom N lines with newest
    // on the row immediately above the build-status line.
    const int maxMessageLines = messageAreaRows - (usedFirstLine ? 1 : 0);
    float bottomSlotY = terminalStartY - (float)statusLineCount * scaledLineHeight;

    struct LineSlot { std::string text; bool fromNewestMessage; bool fromNewestAndTyping; };
    std::vector<LineSlot> allLines;
    for (size_t mi = 0; mi < g_terminalMessages.size(); mi++) {
        const TerminalMessage& msg = g_terminalMessages[mi];
        char visibleText[129];
        int textLen = (int)strlen(msg.text);
        int charsToShow = (msg.visibleChars < textLen) ? msg.visibleChars : textLen;
        strncpy(visibleText, msg.text, charsToShow);
        visibleText[charsToShow] = '\0';
        bool fromNewest = (mi == g_terminalMessages.size() - 1);
        bool typing = fromNewest && msg.typingProgress < 1.0f;

        std::vector<std::string> wrappedLines = WrapTerminalTextLines(visibleText, fontSize, terminalMaxWidth);
        for (const auto& wrapped : wrappedLines)
            allLines.push_back({ wrapped, fromNewest, typing });
    }

    // Take last maxMessageLines; draw so newest is on bottom line, older lines fill upward (fixed slots)
    int start = (int)allLines.size() - maxMessageLines;
    if (start < 0) start = 0;
    int numToDraw = (int)allLines.size() - start;
    if (numToDraw <= 0) return;

    for (int i = 0; i < numToDraw; i++) {
        // Put line i in slot (maxMessageLines - numToDraw + i) so newest is at bottom slot
        int slot = maxMessageLines - numToDraw + i;
        float lineY = bottomSlotY - (float)(maxMessageLines - 1 - slot) * scaledLineHeight;
        const LineSlot& ls = allLines[start + i];
        // Do not fade lines unless they form part of the newest message (then optional fade)
        unsigned char greenValue = 255;
        DrawTextEx(gameFont, ls.text.c_str(), (Vector2){terminalX, lineY}, terminalFontSize, 0.0f, (Color){ 0, greenValue, 0, 255 });
        if (ls.fromNewestAndTyping) {
            float realTime = (float)GetTime();
            if (sinf(realTime * 4.0f) > 0.0f) {
                float endX = terminalX + MeasureTextEx(gameFont, ls.text.c_str(), terminalFontSize, 0.0f).x;
                DrawTextEx(gameFont, "_", (Vector2){endX, lineY}, terminalFontSize, 0.0f, (Color){ 0, 255, 0, 255 });
            }
        }
    }

    Color statusColor = (Color){ 180, 180, 180, 255 };
    if (g_buildStatusState == BuildStatusState::Possible) {
        statusColor = (Color){ 0, 255, 255, 255 };
    } else if (g_buildStatusState == BuildStatusState::Blocked) {
        float pulse = (sinf((float)GetTime() * 4.0f) + 1.0f) * 0.5f;
        statusColor = LerpColor(BLACK, RED, pulse);
    }
    for (int i = 0; i < statusLineCount; i++) {
        float lineY = buildStatusBottomY - (float)(statusLineCount - 1 - i) * scaledLineHeight;
        DrawTextEx(gameFont, buildStatusLines[i].c_str(), (Vector2){terminalX, lineY}, terminalFontSize, 0.0f, statusColor);
    }
}

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

// Factory smoke: get cylinder top Y for a factory (matches DrawFactory geometry)
static float GetFactoryCylinderTopY(Vector3 center, float gridSize) {
    float baseH = gridSize * 1.4f;
    float roofH = gridSize * 0.25f;
    float stackH2 = gridSize * 1.2f;
    float cylinderHeight = stackH2 * 1.2f;
    float blackHeight = cylinderHeight * 0.2f;
    float topRedHeight = cylinderHeight * 0.25f;
    float roofY = center.y + baseH + roofH;
    return roofY + cylinderHeight + blackHeight + topRedHeight;
}

static void SpawnFactorySmoke(Vector3 center, float gridSize) {
    const int toSpawn = 2;  // 1-2 per spawn; ~20 total across factories over time
    const int MAX_FACTORY_SMOKE = 100;
    float cargoBlockSize = gridSize * 0.22f * 2.0f * 0.67f;  // 33% smaller than material cubes
    float topY = GetFactoryCylinderTopY(center, gridSize);
    float cylinderRadius = (gridSize * 0.9f * 0.6f) / 2.0f;
    float cylinderSpacing = cylinderRadius * 2.12f;
    Vector3 cyl1 = { center.x - cylinderSpacing / 2.0f, topY, center.z + gridSize * 0.4f };
    Vector3 cyl2 = { center.x + cylinderSpacing / 2.0f, topY, center.z + gridSize * 0.4f };
    if ((int)g_factorySmokeParticles.size() + toSpawn * 2 > MAX_FACTORY_SMOKE) return;
    std::uniform_real_distribution<float> driftDist(-0.3f, 0.3f);
    std::uniform_real_distribution<float> riseDist(1.5f, 3.0f);
    std::uniform_real_distribution<float> lifeDist(2.0f, 4.0f);
    for (int i = 0; i < toSpawn * 2; i++) {
        FactorySmokeParticle p;
        p.size = cargoBlockSize;
        p.maxLifetime = lifeDist(particleRNG);
        p.lifetime = 0.0f;
        bool white = (particleRNG() % 2) == 0;
        p.color = white ? (Color){ 255, 255, 255, 128 } : (Color){ 180, 180, 180, 128 };  // 50% transparency
        Vector3 spawn = (i % 2 == 0) ? cyl1 : cyl2;
        p.position = spawn;
        p.velocity = { driftDist(particleRNG), riseDist(particleRNG), driftDist(particleRNG) };
        g_factorySmokeParticles.push_back(p);
    }
}

static void UpdateFactorySmoke(float deltaTime) {
    for (size_t i = 0; i < g_factorySmokeParticles.size(); ) {
        FactorySmokeParticle& p = g_factorySmokeParticles[i];
        p.lifetime += deltaTime;
        p.position.x += p.velocity.x * deltaTime;
        p.position.y += p.velocity.y * deltaTime;
        p.position.z += p.velocity.z * deltaTime;
        p.velocity.y *= 0.98f;  // Slight slowdown as it rises
        if (p.lifetime >= p.maxLifetime || p.position.y > 80.0f) {
            g_factorySmokeParticles[i] = g_factorySmokeParticles.back();
            g_factorySmokeParticles.pop_back();
        } else {
            i++;
        }
    }
}

static void RenderFactorySmoke() {
    for (const auto& p : g_factorySmokeParticles) {
        float lifeRatio = 1.0f - (p.lifetime / p.maxLifetime);
        Color c = p.color;
        c.a = (unsigned char)((float)c.a * lifeRatio);  // Fade out
        DrawCube(p.position, p.size, p.size, p.size, c);
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

// Draw a monorail train (passenger-style, 4 cars) - color from train type
void DrawTrain(const std::vector<Vector3>& path, float progress, float gridSize, float brightnessMul = 1.0f, bool invalidPreview = false, PlacedTrain::TrainType trainType = PlacedTrain::TrainType::Passenger, float whitePulse = 0.0f) {
    if (path.size() < 2) return;
    
    Color trainColor = invalidPreview ? GetInvalidPreviewColor() : GetTrainColorForType(trainType, brightnessMul);
    if (!invalidPreview && whitePulse > 0.0f) trainColor = LerpColor(trainColor, WHITE, Clamp(whitePulse, 0.0f, 1.0f));
    
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
void DrawCargoTrain(const std::vector<Vector3>& path, float progress, float gridSize, int trailers, int cargoTotal = -1, float brightnessMul = 1.0f, bool invalidPreview = false, float whitePulse = 0.0f) {
    if (path.size() < 2) return;

    Color invColor = invalidPreview ? GetInvalidPreviewColor() : (Color){0,0,0,0};
    Color locoColor = invalidPreview ? invColor : MulColor({ 0, 255, 0, 204 }, brightnessMul);          // same green as standard train (or red when invalid)
    Color trailerColor = invalidPreview ? invColor : MulColor({ 40, 40, 40, 220 }, brightnessMul);      // dark grey trailer (or red when invalid)
    Color cargoColor = invalidPreview ? invColor : MulColor({ 245, 245, 245, 235 }, brightnessMul);     // white blocks (or red when invalid)
    if (!invalidPreview && whitePulse > 0.0f) {
        float t = Clamp(whitePulse, 0.0f, 1.0f);
        locoColor = LerpColor(locoColor, WHITE, t);
        trailerColor = LerpColor(trailerColor, WHITE, t);
        cargoColor = LerpColor(cargoColor, WHITE, t);
    }

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
// Stations must never connect to other stations. Two station tiles are "the same station" if they belong to the same 4-tile building.
// Returns true only when both are station tiles and their station "center" (by placementOrientation + stationPart) matches.
static bool SamePhysicalStation(const PlacedPlatform& a, const PlacedPlatform& b, float gridSize) {
    if (!a.isStation || !b.isStation || a.isDepot || b.isDepot) return false;
    if (a.placementOrientation != b.placementOrientation) return false;
    float cxA, czA, cxB, czB;
    float offA = (a.stationPart - 1.5f) * gridSize;
    float offB = (b.stationPart - 1.5f) * gridSize;
    switch (a.placementOrientation) {
        case 0: cxA = a.position.x - offA; czA = a.position.z; cxB = b.position.x - offB; czB = b.position.z; break;
        case 1: cxA = a.position.x; czA = a.position.z - offA; cxB = b.position.x; czB = b.position.z - offB; break;
        case 2: cxA = a.position.x + offA; czA = a.position.z; cxB = b.position.x + offB; czB = b.position.z; break;
        case 3: cxA = a.position.x; czA = a.position.z + offA; cxB = b.position.x; czB = b.position.z + offB; break;
        default: cxA = a.position.x; czA = a.position.z; cxB = b.position.x; czB = b.position.z; break;
    }
    return (fabsf(cxA - cxB) < 0.1f && fabsf(czA - czB) < 0.1f);
}

static std::vector<int> CollectPhysicalStationTileIndices(int stationPlatformIdx,
                                                          const std::vector<PlacedPlatform>& platforms,
                                                          float gridSize) {
    std::vector<int> tiles;
    if (stationPlatformIdx < 0 || stationPlatformIdx >= (int)platforms.size()) return tiles;
    const PlacedPlatform& anchor = platforms[stationPlatformIdx];
    if (!anchor.isStation || anchor.isDepot) return tiles;

    for (int i = 0; i < (int)platforms.size(); i++) {
        if (SamePhysicalStation(anchor, platforms[i], gridSize)) tiles.push_back(i);
    }
    return tiles;
}

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
static inline int FindPlatformIndexAtPos(const Vector3& position, const std::vector<PlacedPlatform>& platforms) {
    for (size_t i = 0; i < platforms.size(); i++) {
        if (Vector3Distance(position, platforms[i].position) < 0.1f) return (int)i;
    }
    return -1;
}

static bool IsOverpassSkipConnected(int idxA, int idxB, const std::vector<PlacedPlatform>& platforms, float gridSize) {
    if (idxA < 0 || idxA >= (int)platforms.size() || idxB < 0 || idxB >= (int)platforms.size()) return false;
    const PlacedPlatform& a = platforms[idxA];
    const PlacedPlatform& b = platforms[idxB];
    if (a.isDepot || b.isDepot) return false;
    if (a.placementGroupId < 0 || b.placementGroupId < 0) return false;
    if (a.placementGroupId != b.placementGroupId) return false;
    if (a.isJunction || b.isJunction) return false; // real junctions already handle connectivity

    float dx = b.position.x - a.position.x;
    float dz = b.position.z - a.position.z;
    bool sameX = fabsf(dx) < 0.1f;
    bool sameZ = fabsf(dz) < 0.1f;
    if (!(sameX || sameZ)) return false;
    float axisDist = sameX ? fabsf(dz) : fabsf(dx);
    if (axisDist < gridSize * 1.8f || axisDist > gridSize * 2.2f) return false; // exactly one skipped cell

    Vector3 mid = { (a.position.x + b.position.x) * 0.5f, 0.0f, (a.position.z + b.position.z) * 0.5f };
    int midIdx = FindPlatformIndexAtPos(mid, platforms);
    if (midIdx < 0) return false;
    long long midKey = MakePositionKey(platforms[midIdx].position.x, platforms[midIdx].position.z);
    auto it = g_overpassGroupsByPosKey.find(midKey);
    if (it == g_overpassGroupsByPosKey.end()) return false;
    return (it->second.find(a.placementGroupId) != it->second.end());
}

static bool ArePlatformsConnectedForNetwork(int idxA, int idxB, const std::vector<PlacedPlatform>& platforms, float gridSize) {
    if (idxA < 0 || idxA >= (int)platforms.size() || idxB < 0 || idxB >= (int)platforms.size()) return false;
    if (idxA == idxB) return false;
    const PlacedPlatform& a = platforms[idxA];
    const PlacedPlatform& b = platforms[idxB];
    if (a.isDepot || b.isDepot) return false;

    if (ArePlatformsAdjacent(a.position, b.position, gridSize)) {
        if (a.isStation && b.isStation && !SamePhysicalStation(a, b, gridSize)) return false;
        // Default: adjacent rail is connected (matches original forgiving build behavior).
        // Exception: overpass centers explicitly block cross-group adjacency so X crossings stay separated.
        if (a.placementGroupId != b.placementGroupId
            && a.placementGroupId >= 0 && b.placementGroupId >= 0
            && !a.isJunction && !b.isJunction) {
            long long keyA = MakePositionKey(a.position.x, a.position.z);
            long long keyB = MakePositionKey(b.position.x, b.position.z);
            bool aIsOverpassCenter = (g_overpassGroupsByPosKey.find(keyA) != g_overpassGroupsByPosKey.end());
            bool bIsOverpassCenter = (g_overpassGroupsByPosKey.find(keyB) != g_overpassGroupsByPosKey.end());
            if (aIsOverpassCenter || bIsOverpassCenter) return false;
        }
        return true;
    }

    return IsOverpassSkipConnected(idxA, idxB, platforms, gridSize);
}

static bool IsStraightThroughTrackCell(int idx, const std::vector<PlacedPlatform>& platforms, float gridSize, bool& outHorizontal) {
    outHorizontal = false;
    if (idx < 0 || idx >= (int)platforms.size()) return false;
    if (platforms[idx].isDepot) return false;
    bool hasLeft = false, hasRight = false, hasUp = false, hasDown = false;
    const Vector3& p = platforms[idx].position;
    for (int j = 0; j < (int)platforms.size(); j++) {
        if (j == idx) continue;
        if (!ArePlatformsConnectedForNetwork(idx, j, platforms, gridSize)) continue;
        float dx = platforms[j].position.x - p.x;
        float dz = platforms[j].position.z - p.z;
        if (fabsf(dx) > fabsf(dz)) {
            if (dx < 0.0f) hasLeft = true; else hasRight = true;
        } else {
            if (dz < 0.0f) hasUp = true; else hasDown = true;
        }
    }
    bool horizontal = hasLeft && hasRight && !hasUp && !hasDown;
    bool vertical = hasUp && hasDown && !hasLeft && !hasRight;
    if (horizontal) { outHorizontal = true; return true; }
    if (vertical) { outHorizontal = false; return true; }
    return false;
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
        // Track ALL tiles visited in this BFS so we can reset their compIds if the
        // component turns out to be pure-track (no stations) and gets removed.
        // Without this, popped pure-track tiles retain the compId that equals the
        // NEXT component's compId (since outMembers.size() is reused), which causes
        // those tiles to appear in the wrong component and falsely trigger AddToLine.
        std::vector<int> allTilesInBFS;

        while (!q.empty()) {
            int cur = q.back();
            q.pop_back();

            allTilesInBFS.push_back(cur);

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

            // Find all adjacent platforms (stations or track, but not depots).
            // CRITICAL: Stations never connect to other stations. Only traverse station->station when same physical 4-tile station.
            for (int j = 0; j < (int)platforms.size(); j++) {
                if (visited[j]) continue;
                if (platforms[j].isDepot) continue; // Skip depots
                if (!ArePlatformsConnectedForNetwork(cur, j, platforms, gridSize)) continue;
                visited[j] = 1;
                q.push_back(j);
            }
        }

        // Only create a component key if this component has at least one station
        if (stationsInComponent > 0) {
            DebugLogFormat("DEBUG: Component %d has %d station tiles, %d track tiles",
                           compId, stationsInComponent, trackInComponent);
            outCompKey.push_back(bestKey);
        } else {
            // Pure track component (no stations) - remove it.
            // CRITICAL: reset compIds for all tiles in this BFS back to -1.
            // If we don't, those tiles keep compId == outMembers.size()-1 after pop_back,
            // which is the same value the NEXT component will use, causing false
            // "component membership" detection for unrelated station components.
            for (int tile : allTilesInBFS) outCompId[tile] = -1;
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

static int RemoveCargoFromLineOwnedDepots(std::vector<PlacedPlatform>& platforms, int lineId, int amount) {
    if (amount <= 0 || lineId < 0) return 0;

    std::vector<int> order;
    for (int i = 0; i < (int)platforms.size(); i++) {
        if (!platforms[i].isDepot) continue;
        if (platforms[i].lineOwnerId != lineId) continue;
        if (platforms[i].depotCargo <= 0) continue;
        order.push_back(i);
    }

    std::sort(order.begin(), order.end(), [&](int a, int b) {
        if (platforms[a].depotCargo != platforms[b].depotCargo)
            return platforms[a].depotCargo > platforms[b].depotCargo;
        return a < b;
    });

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
        {255, 165,   0, 200},  // Orange
        {100, 255, 255, 200},  // Light Cyan
        {200, 100, 255, 200},  // Purple
        {255, 255, 255, 200}   // White
    };
}

static const char* GetLineColorName(int index) {
    static const char* names[] = { "Cyan", "Red", "Green", "Yellow", "Magenta", "Blue", "Orange", "Light Cyan", "Purple", "White" };
    if (index >= 0 && index < 10) return names[index];
    return "Cyan";
}

struct SystemColorShades {
    Color colors[4];
    const char* names[4];
    const char* systemLabel;
};

static SystemColorShades GetSystemColorShades(int siloSystem) {
    SystemColorShades s;
    switch (siloSystem) {
        case (int)SiloSystem::SYS1_CARGO:
            s.colors[0] = (Color){110,  70,  30, 200};
            s.colors[1] = (Color){139,  90,  43, 200};
            s.colors[2] = (Color){165, 110,  60, 200};
            s.colors[3] = (Color){190, 135,  80, 200};
            s.names[0] = "Dark Brown"; s.names[1] = "Brown"; s.names[2] = "Light Brown"; s.names[3] = "Pale Brown";
            s.systemLabel = "Materials Industry";
            break;
        case (int)SiloSystem::SYS2_GREEN:
            s.colors[0] = (Color){  0, 200,   0, 200};
            s.colors[1] = (Color){ 50, 255,  50, 200};
            s.colors[2] = (Color){100, 255, 100, 200};
            s.colors[3] = (Color){150, 255, 150, 200};
            s.names[0] = "Dark Green"; s.names[1] = "Green"; s.names[2] = "Light Green"; s.names[3] = "Pale Green";
            s.systemLabel = "General Patriots";
            break;
        case (int)SiloSystem::SYS3_MAGENTA:
            s.colors[0] = (Color){180,   0, 180, 200};
            s.colors[1] = (Color){255,   0, 255, 200};
            s.colors[2] = (Color){255, 100, 255, 200};
            s.colors[3] = (Color){255, 170, 255, 200};
            s.names[0] = "Dark Magenta"; s.names[1] = "Magenta"; s.names[2] = "Light Magenta"; s.names[3] = "Pale Magenta";
            s.systemLabel = "AI Industrial";
            break;
        case (int)SiloSystem::SYS4_CYAN:
            s.colors[0] = (Color){  0, 160, 180, 200};
            s.colors[1] = (Color){  0, 220, 255, 200};
            s.colors[2] = (Color){ 80, 255, 255, 200};
            s.colors[3] = (Color){160, 255, 255, 200};
            s.names[0] = "Dark Cyan"; s.names[1] = "Cyan"; s.names[2] = "Light Cyan"; s.names[3] = "Pale Cyan";
            s.systemLabel = "AI Technology";
            break;
        case (int)SiloSystem::SYS5_ORANGE:
            s.colors[0] = (Color){180, 100,   0, 200};
            s.colors[1] = (Color){255, 165,   0, 200};
            s.colors[2] = (Color){255, 200,  60, 200};
            s.colors[3] = (Color){255, 220, 120, 200};
            s.names[0] = "Dark Orange"; s.names[1] = "Orange"; s.names[2] = "Light Orange"; s.names[3] = "Pale Orange";
            s.systemLabel = "AI Administration";
            break;
        case (int)SiloSystem::SYS6_RED:
            s.colors[0] = (Color){160,   0,   0, 200};
            s.colors[1] = (Color){255,  30,  30, 200};
            s.colors[2] = (Color){255, 100, 100, 200};
            s.colors[3] = (Color){255, 160, 160, 200};
            s.names[0] = "Dark Red"; s.names[1] = "Red"; s.names[2] = "Light Red"; s.names[3] = "Pale Red";
            s.systemLabel = "Transhuman Elites";
            break;
        case (int)SiloSystem::SYS7_YELLOW:
            s.colors[0] = (Color){180, 180,   0, 200};
            s.colors[1] = (Color){255, 255,   0, 200};
            s.colors[2] = (Color){255, 255, 100, 200};
            s.colors[3] = (Color){255, 255, 170, 200};
            s.names[0] = "Dark Yellow"; s.names[1] = "Yellow"; s.names[2] = "Light Yellow"; s.names[3] = "Pale Yellow";
            s.systemLabel = "Corporate Executives";
            break;
        default:
            s.colors[0] = (Color){  0, 200, 200, 200};
            s.colors[1] = (Color){  0, 255, 255, 200};
            s.colors[2] = (Color){100, 255, 255, 200};
            s.colors[3] = (Color){200, 255, 255, 200};
            s.names[0] = "Dark Cyan"; s.names[1] = "Cyan"; s.names[2] = "Light Cyan"; s.names[3] = "Pale Cyan";
            s.systemLabel = "";
            break;
    }
    return s;
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

static int CountPhysicalStationsInLine(const Line& line, const std::vector<PlacedPlatform>& platforms) {
    std::set<long long> uniquePrimeKeys;
    for (int pi : line.platformIndices) {
        if (pi < 0 || pi >= (int)platforms.size()) continue;
        const PlacedPlatform& p = platforms[pi];
        if (p.isDepot || !p.isStation) continue;
        if (p.stationPart != 3) continue;  // One prime tile per physical station
        uniquePrimeKeys.insert(MakePositionKey(p.position.x, p.position.z));
    }
    return (int)uniquePrimeKeys.size();
}

struct BureauChoice {
    int bureauIndex = -1;
    int floors = 0;
};

static inline long long PackIntPair(int a, int b) {
    return ((long long)a << 32) | (unsigned int)b;
}

static inline int WorldToGridCell(float v) {
    return (int)floorf((v + g_gridExtent) / g_gridSpacing);
}

static inline bool IsGridCellInBounds(int gx, int gz) {
    if (g_clusterGrid.empty()) return false;
    int h = (int)g_clusterGrid.size();
    int w = (h > 0) ? (int)g_clusterGrid[0].size() : 0;
    return gx >= 0 && gx < w && gz >= 0 && gz < h;
}

static inline int HalfGridCoord(float v) {
    return (int)roundf(v / (g_gridSpacing * 0.5f));
}

static inline bool IsOneTileManhattanAdjacent(const Vector3& a, const Vector3& b) {
    int ax = HalfGridCoord(a.x);
    int az = HalfGridCoord(a.z);
    int bx = HalfGridCoord(b.x);
    int bz = HalfGridCoord(b.z);
    return (abs(ax - bx) + abs(az - bz)) <= 2;
}

// Bureau has a 2x2 grid footprint (bureauHalf = g_gridSpacing).
// Measures Manhattan distance from station tile center to bureau EDGE, not center.
static inline bool IsBureauAdjacentToStationTile(const Vector3& bureauPos, const Vector3& stationTilePos) {
    float bureauHalf = g_gridSpacing * 1.0f;
    float dx = std::max(0.0f, fabsf(stationTilePos.x - bureauPos.x) - bureauHalf);
    float dz = std::max(0.0f, fabsf(stationTilePos.z - bureauPos.z) - bureauHalf);
    return (dx + dz) <= g_gridSpacing * 2.0f + 0.1f;
}

// Inner ring rule for all bureaus: +15% over prior 6-grid rule.
static inline float GetBureauInnerRingRadius() {
    return g_gridSpacing * (6.0f * 1.15f);
}

// Returns true when a bureau's inner ring touches at least one station tile that belongs
// to an established line. If outLineIndex is provided, returns the closest qualifying line.
static bool DetectClosestEstablishedLineForBureauInnerRing(const Vector3& bureauPos, int* outLineIndex = nullptr) {
    float innerRingRadius = GetBureauInnerRingRadius();
    float bureauHalf = g_gridSpacing * 1.0f;
    float bestDistSq = 1e30f;
    int bestLineIndex = -1;
    int bestLineId = -1;

    for (int pi = 0; pi < (int)g_placedPlatforms.size(); pi++) {
        const auto& p = g_placedPlatforms[pi];
        if (!p.isStation || p.isDepot) continue; // Any station part counts.
        int li = (pi < (int)g_cachedPlatformLineId.size()) ? g_cachedPlatformLineId[pi] : -1;
        if (li < 0 || li >= (int)g_lines.size()) continue;
        int lineId = g_lines[li].id;
        if (g_establishedLineIds.find(lineId) == g_establishedLineIds.end()) continue;

        float dx = std::max(0.0f, fabsf(bureauPos.x - p.position.x) - bureauHalf);
        float dz = std::max(0.0f, fabsf(bureauPos.z - p.position.z) - bureauHalf);
        float distSq = dx * dx + dz * dz;
        if (distSq > innerRingRadius * innerRingRadius) continue;

        bool better = (distSq < bestDistSq - 0.0001f);
        bool tie = fabsf(distSq - bestDistSq) <= 0.0001f;
        if (better || (tie && (bestLineId < 0 || lineId < bestLineId))) {
            bestDistSq = distSq;
            bestLineIndex = li;
            bestLineId = lineId;
        }
    }

    if (outLineIndex) *outLineIndex = bestLineIndex;
    return bestLineIndex >= 0;
}

// INNER CITY HUB: the central city (middle of map). Buildings are white; no colour in name.
static bool IsBuildingInnerCityHub(const Building& b) {
    return b.color.r >= 200 && b.color.g >= 200 && b.color.b >= 200;
}

static bool IsStationInsideCluster(const int sx, const int sz, ClusterType t) {
    for (const auto& cl : g_clusters) {
        if (cl.type != t) continue;
        if (sx >= cl.x && sx < (cl.x + cl.size) && sz >= cl.y && sz < (cl.y + cl.size)) return true;
    }
    return false;
}

static bool IsStationNearCluster(const int sx, const int sz, ClusterType t) {
    for (const auto& cl : g_clusters) {
        if (cl.type != t) continue;
        int minX = cl.x;
        int maxX = cl.x + cl.size - 1;
        int minZ = cl.y;
        int maxZ = cl.y + cl.size - 1;
        if (sx >= minX && sx <= maxX && sz >= minZ && sz <= maxZ) return true;
    }
    return false;
}

// Match a building colour to a cluster type (building colours use alpha 220)
static ClusterType BuildingColorToClusterType(Color c) {
    if (c.r == 0   && c.g == 200 && c.b == 80)  return ClusterType::ClusterGreen;
    if (c.r == 255 && c.g == 0   && c.b == 255) return ClusterType::ClusterMagenta;
    if (c.r == 0   && c.g == 200 && c.b == 255) return ClusterType::ClusterCyan;
    if (c.r == 255 && c.g == 165 && c.b == 0)   return ClusterType::ClusterOrange;
    if (c.r == 230 && c.g == 41  && c.b == 55)  return ClusterType::ClusterRed;
    if (c.r == 253 && c.g == 249 && c.b == 0)   return ClusterType::ClusterYellow;
    return ClusterType::CARGO;
}

// World-space proximity: check if a position is within range of any building of a given cluster type
static bool IsNearClusterBuilding(float wx, float wz, ClusterType t, float radius) {
    for (const auto& b : g_buildings) {
        if (BuildingColorToClusterType(b.color) != t) continue;
        float dx = fabsf(wx - b.position.x) - b.size.x * 0.5f;
        float dz = fabsf(wz - b.position.z) - b.size.z * 0.5f;
        if (dx < 0.0f) dx = 0.0f;
        if (dz < 0.0f) dz = 0.0f;
        if (dx <= radius && dz <= radius) return true;
    }
    return false;
}

static void CollectInnerCityHubTiles(std::set<long long>& outTiles) {
    outTiles.clear();
    for (const auto& b : g_buildings) {
        if (!IsBuildingInnerCityHub(b)) continue;
        if (fabsf(b.position.x) > 20.0f || fabsf(b.position.z) > 20.0f) continue;

        float minX = b.position.x - b.size.x * 0.5f;
        float maxX = b.position.x + b.size.x * 0.5f;
        float minZ = b.position.z - b.size.z * 0.5f;
        float maxZ = b.position.z + b.size.z * 0.5f;

        int cellMinX = WorldToGridCell(minX);
        int cellMaxX = WorldToGridCell(maxX - 0.001f);
        int cellMinZ = WorldToGridCell(minZ);
        int cellMaxZ = WorldToGridCell(maxZ - 0.001f);

        for (int gx = cellMinX; gx <= cellMaxX; gx++) {
            for (int gz = cellMinZ; gz <= cellMaxZ; gz++) {
                if (!IsGridCellInBounds(gx, gz)) continue;
                outTiles.insert(PackIntPair(gx, gz));
            }
        }
    }
}

static bool IsStationNearInnerCityHubTile(int sx, int sz, const std::set<long long>& cityTiles) {
    for (int dx = -1; dx <= 1; dx++) {
        for (int dz = -1; dz <= 1; dz++) {
            int tx = sx + dx;
            int tz = sz + dz;
            if (!IsGridCellInBounds(tx, tz)) continue;
            if (cityTiles.find(PackIntPair(tx, tz)) != cityTiles.end()) return true;
        }
    }
    return false;
}

// Returns the cluster type if the station is inside or near a passenger cluster.
// Uses grid-cell check first, then falls back to world-space building proximity.
static ClusterType GetClusterTypeForStation(int sx, int sz) {
    // Grid-cell check (reliable for inner grid). Check Inside for all types so stations fully in a cluster are detected.
    if (IsStationInsideCluster(sx, sz, ClusterType::ClusterMagenta)) return ClusterType::ClusterMagenta;
    if (IsStationInsideCluster(sx, sz, ClusterType::ClusterCyan)) return ClusterType::ClusterCyan;
    if (IsStationInsideCluster(sx, sz, ClusterType::ClusterOrange)) return ClusterType::ClusterOrange;
    if (IsStationInsideCluster(sx, sz, ClusterType::ClusterRed)) return ClusterType::ClusterRed;
    if (IsStationInsideCluster(sx, sz, ClusterType::ClusterGreen)) return ClusterType::ClusterGreen;
    if (IsStationInsideCluster(sx, sz, ClusterType::ClusterYellow)) return ClusterType::ClusterYellow;
    if (IsStationNearCluster(sx, sz, ClusterType::ClusterGreen)) return ClusterType::ClusterGreen;
    if (IsStationNearCluster(sx, sz, ClusterType::ClusterYellow)) return ClusterType::ClusterYellow;

    // World-space fallback: check proximity to actual cluster buildings (covers outer ring)
    float wx = -g_gridExtent + ((float)sx + 0.5f) * g_gridSpacing;
    float wz = -g_gridExtent + ((float)sz + 0.5f) * g_gridSpacing;
    float nearDist = g_gridSpacing * 1.5f;
    if (IsNearClusterBuilding(wx, wz, ClusterType::ClusterMagenta, nearDist)) return ClusterType::ClusterMagenta;
    if (IsNearClusterBuilding(wx, wz, ClusterType::ClusterCyan,    nearDist)) return ClusterType::ClusterCyan;
    if (IsNearClusterBuilding(wx, wz, ClusterType::ClusterOrange,  nearDist)) return ClusterType::ClusterOrange;
    if (IsNearClusterBuilding(wx, wz, ClusterType::ClusterRed,     nearDist)) return ClusterType::ClusterRed;
    if (IsNearClusterBuilding(wx, wz, ClusterType::ClusterGreen,   nearDist)) return ClusterType::ClusterGreen;
    if (IsNearClusterBuilding(wx, wz, ClusterType::ClusterYellow,  nearDist)) return ClusterType::ClusterYellow;

    return ClusterType::CARGO;
}

// Returns short silo name for terminal message when a station is built in a qualifying cluster; nullptr if not a silo cluster.
static const char* GetSiloNameForClusterType(ClusterType ct) {
    switch (ct) {
        case ClusterType::ClusterGreen:  return "GREEN SILO";
        case ClusterType::ClusterMagenta: return "MAGENTA SILO";
        case ClusterType::ClusterCyan:   return "CYAN SILO";
        case ClusterType::ClusterOrange: return "ORANGE SILO";
        case ClusterType::ClusterRed:    return "RED SILO";
        case ClusterType::ClusterYellow: return "YELLOW SILO";
        default: return nullptr;
    }
}

static bool IsDepotAdjacentToFactoryFootprint(const Vector3& depotPos, const Vector3& factoryCenter) {
    float half = g_gridSpacing * 2.0f;
    float minX = factoryCenter.x - half;
    float maxX = factoryCenter.x + half;
    float minZ = factoryCenter.z - half;
    float maxZ = factoryCenter.z + half;

    float dx = 0.0f;
    if (depotPos.x < minX) dx = minX - depotPos.x;
    else if (depotPos.x > maxX) dx = depotPos.x - maxX;

    float dz = 0.0f;
    if (depotPos.z < minZ) dz = minZ - depotPos.z;
    else if (depotPos.z > maxZ) dz = depotPos.z - maxZ;

    float dist = sqrtf(dx * dx + dz * dz);
    return dist <= g_gridSpacing * 3.1f;
}

static bool IsStationNearFactoryForIndustry(const Vector3& stationPos, const Vector3& factoryCenter) {
    // Industry station qualifier should measure from station tile to FACTORY FOOTPRINT edge.
    // This matches player expectation of "next to factory" better than center-to-center distance.
    const float half = g_gridSpacing * 2.0f;      // factory 4x4 footprint half-size
    const float nearRadius = g_gridSpacing * 2.0f + 0.1f; // within 2 grid spaces
    const float minX = factoryCenter.x - half;
    const float maxX = factoryCenter.x + half;
    const float minZ = factoryCenter.z - half;
    const float maxZ = factoryCenter.z + half;

    float dx = 0.0f;
    if (stationPos.x < minX) dx = minX - stationPos.x;
    else if (stationPos.x > maxX) dx = stationPos.x - maxX;

    float dz = 0.0f;
    if (stationPos.z < minZ) dz = minZ - stationPos.z;
    else if (stationPos.z > maxZ) dz = stationPos.z - maxZ;

    const float dist = sqrtf(dx * dx + dz * dz);
    return dist <= nearRadius;
}

static bool IsWorldPosInActivatedCargoCluster(float wx, float wz) {
    // Cargo cluster activates from a factory + adjacent depot, then extends via that depot's connected chain.
    // Rule 1: larger base radius around factory center (4 grid spaces).
    // Rule 2: cluster follows connected depot chain extent (within 2 grid spaces of any depot in that chain).
    const float factoryClusterHalf = g_gridSpacing * 4.0f;
    const float depotChainHalf = g_gridSpacing * 2.0f;
    for (const auto& f : g_placedFactories) {
        std::set<int> clusterDepotIndices;
        for (int pi = 0; pi < (int)g_placedPlatforms.size(); pi++) {
            if (!g_placedPlatforms[pi].isDepot) continue;
            if (!IsDepotAdjacentToFactoryFootprint(g_placedPlatforms[pi].position, f.position)) continue;
            std::vector<int> depotCluster = GetDepotClusterIndices(g_placedPlatforms, pi, g_gridSpacing);
            for (int idx : depotCluster) clusterDepotIndices.insert(idx);
        }
        if (clusterDepotIndices.empty()) continue;

        if (fabsf(wx - f.position.x) <= factoryClusterHalf && fabsf(wz - f.position.z) <= factoryClusterHalf) return true;

        for (int di : clusterDepotIndices) {
            if (di < 0 || di >= (int)g_placedPlatforms.size()) continue;
            const Vector3& dp = g_placedPlatforms[di].position;
            if (fabsf(wx - dp.x) <= depotChainHalf && fabsf(wz - dp.z) <= depotChainHalf) return true;
        }
    }
    return false;
}

static int GetLineIndexFromPlatformIndex(int pi) {
    if (pi < 0 || pi >= (int)g_cachedPlatformLineId.size()) return -1;
    int lineIndex = g_cachedPlatformLineId[pi];
    if (lineIndex < 0 || lineIndex >= (int)g_lines.size()) return -1;
    return lineIndex;
}

static int ClusterTypeToSiloSystemStrict(ClusterType t) {
    switch (t) {
        case ClusterType::ClusterYellow: return (int)SiloSystem::SYS7_YELLOW;
        case ClusterType::ClusterRed: return (int)SiloSystem::SYS6_RED;
        case ClusterType::ClusterOrange: return (int)SiloSystem::SYS5_ORANGE;
        case ClusterType::ClusterCyan: return (int)SiloSystem::SYS4_CYAN;
        case ClusterType::ClusterMagenta: return (int)SiloSystem::SYS3_MAGENTA;
        case ClusterType::ClusterGreen: return (int)SiloSystem::SYS2_GREEN;
        default: return -1;
    }
}

static ClusterType GetClusterTypeAtGridCellStrict(int gx, int gz) {
    if (!IsGridCellInBounds(gx, gz)) return ClusterType::CARGO;
    int clusterIndex = g_clusterGrid[gz][gx];
    if (clusterIndex < 0 || clusterIndex >= (int)g_clusters.size()) return ClusterType::CARGO;
    return g_clusters[clusterIndex].type;
}

static int DetectStrictClusterSystemForStationPos(float wx, float wz) {
    int cx = WorldToGridCell(wx);
    int cz = WorldToGridCell(wz);
    if (IsWorldPosInActivatedCargoCluster(wx, wz)) return (int)SiloSystem::SYS1_CARGO;
    // Must exactly match station base pulse area logic.
    ClusterType pulseClusterType = GetClusterTypeForStation(cx, cz);
    int pulseDetected = ClusterTypeToSiloSystemStrict(pulseClusterType);
    if (pulseDetected >= 0) return pulseDetected;
    return -1;
}

static int DetectStrictClusterSystemFromPlatforms(const std::vector<int>& platformIndices) {
    int bestSystem = -1;
    for (int pi : platformIndices) {
        if (pi < 0 || pi >= (int)g_placedPlatforms.size()) continue;
        const PlacedPlatform& p = g_placedPlatforms[pi];
        if (p.isDepot || !p.isStation) continue;
        int detected = DetectStrictClusterSystemForStationPos(p.position.x, p.position.z);
        if (detected > bestSystem) bestSystem = detected;
    }
    return bestSystem;
}

static std::vector<int> DetectAllClusterSystemsFromPlatforms(const std::vector<int>& platformIndices) {
    std::set<int> found;
    for (int pi : platformIndices) {
        if (pi < 0 || pi >= (int)g_placedPlatforms.size()) continue;
        const PlacedPlatform& p = g_placedPlatforms[pi];
        if (p.isDepot || !p.isStation) continue;
        int detected = DetectStrictClusterSystemForStationPos(p.position.x, p.position.z);
        if (detected >= 0) found.insert(detected);
    }
    return std::vector<int>(found.begin(), found.end());
}

static bool IsLineEstablishedByIndex(int lineIndex) {
    if (lineIndex < 0 || lineIndex >= (int)g_lines.size()) return false;
    return (g_establishedLineIds.find(g_lines[lineIndex].id) != g_establishedLineIds.end());
}

static int FindLineIndexById(int lineId) {
    for (int li = 0; li < (int)g_lines.size(); li++) {
        if (g_lines[li].id == lineId) return li;
    }
    return -1;
}

static int DetectStrictClusterSystemForLine(int lineIndex) {
    if (lineIndex < 0 || lineIndex >= (int)g_lines.size()) return -1;
    if (g_lines[lineIndex].chosenSystem >= (int)SiloSystem::SYS1_CARGO) {
        return g_lines[lineIndex].chosenSystem;
    }
    std::vector<int> stationPlatforms;
    stationPlatforms.reserve(g_lines[lineIndex].platformIndices.size());
    for (int pi : g_lines[lineIndex].platformIndices) {
        if (pi < 0 || pi >= (int)g_placedPlatforms.size()) continue;
        const PlacedPlatform& p = g_placedPlatforms[pi];
        if (!p.isDepot && p.isStation) stationPlatforms.push_back(pi);
    }
    return DetectStrictClusterSystemFromPlatforms(stationPlatforms);
}

static int GetBureauCostPerFloorForLineIndex(int lineIndex) {
    int system = DetectStrictClusterSystemForLine(lineIndex);
    if (system < 0) system = (int)SiloSystem::SYS1_CARGO;
    return GetBureauCostPerFloorForSystem(system);
}

static int RequiredSiloSystemForTrainType(PlacedTrain::TrainType type) {
    switch (type) {
        case PlacedTrain::TrainType::Cargo:     return (int)SiloSystem::SYS1_CARGO;
        case PlacedTrain::TrainType::Passenger: return (int)SiloSystem::SYS2_GREEN;
        case PlacedTrain::TrainType::Magenta:   return (int)SiloSystem::SYS3_MAGENTA;
        case PlacedTrain::TrainType::Cyan:      return (int)SiloSystem::SYS4_CYAN;
        case PlacedTrain::TrainType::Orange:    return (int)SiloSystem::SYS5_ORANGE;
        case PlacedTrain::TrainType::Red:       return (int)SiloSystem::SYS6_RED;
        case PlacedTrain::TrainType::Yellow:    return (int)SiloSystem::SYS7_YELLOW;
        default: return -1;
    }
}

static bool DoesEstablishedLineMatchTrainType(int lineIndex, PlacedTrain::TrainType type) {
    if (!IsLineEstablishedByIndex(lineIndex)) return false;
    int requiredSystem = RequiredSiloSystemForTrainType(type);
    if (requiredSystem < 0) return false;
    if (lineIndex < 0 || lineIndex >= (int)g_lines.size()) return false;
    if (g_lines[lineIndex].chosenSystem >= (int)SiloSystem::SYS1_CARGO) {
        return g_lines[lineIndex].chosenSystem == requiredSystem;
    }
    // Fallback for legacy lines with no persisted system identity: accept any station-matching system.
    std::vector<int> stationPlatforms;
    for (int pi : g_lines[lineIndex].platformIndices) {
        if (pi < 0 || pi >= (int)g_placedPlatforms.size()) continue;
        const PlacedPlatform& p = g_placedPlatforms[pi];
        if (!p.isDepot && p.isStation) stationPlatforms.push_back(pi);
    }
    std::vector<int> allSystems = DetectAllClusterSystemsFromPlatforms(stationPlatforms);
    // If no systems detected, default to cargo (matches establish-line fallback)
    if (allSystems.empty()) return requiredSystem == (int)SiloSystem::SYS1_CARGO;
    for (int sys : allSystems) {
        if (sys == requiredSystem) return true;
    }
    return false;
}

static bool RebuildTrainPath(PlacedTrain& train, const std::vector<PlacedPlatform>& platforms, float gridSize);

static bool AwaitedLineAcceptsTrainType(PlacedTrain::TrainType type) {
    if (g_awaitingTrainForLineId < 0) return true;
    int awaitedLineIndex = FindLineIndexById(g_awaitingTrainForLineId);
    return DoesEstablishedLineMatchTrainType(awaitedLineIndex, type);
}

static void RefreshAwaitingTrainLock() {
    g_awaitingTrainForLineId = -1;
    for (int li = 0; li < (int)g_lines.size(); li++) {
        if (!IsLineEstablishedByIndex(li)) continue;
        bool hasActiveTrain = false;
        for (const auto& train : g_placedTrains) {
            if (!train.isPaused && train.lineId == g_lines[li].id) {
                hasActiveTrain = true;
                break;
            }
        }
        if (!hasActiveTrain) {
            g_awaitingTrainForLineId = g_lines[li].id;
            return;
        }
    }
}

static void RebuildTrainsForLineIds(const std::set<int>& affectedLineIds) {
    if (affectedLineIds.empty()) return;
    for (auto& train : g_placedTrains) {
        if (train.isPaused) continue;
        if (!affectedLineIds.count(train.lineId)) continue;
        RebuildTrainPath(train, g_placedPlatforms, g_gridSpacing);
    }
}

static bool IsJunctionSwitchable(int junctionPlatformIndex, int* outReasonCode = nullptr, int* outEstablishedLineCount = nullptr) {
    // reason codes: 0=switchable, 1=invalid index, 2=no exits, 3=no established exits, 4=neutral/unestablished exit present, 5=established colors differ
    if (junctionPlatformIndex < 0 || junctionPlatformIndex >= (int)g_placedPlatforms.size()) {
        if (outReasonCode) *outReasonCode = 1;
        if (outEstablishedLineCount) *outEstablishedLineCount = 0;
        return false;
    }
    std::set<int> establishedLinesAtJunction;
    bool hasNeutralOrUnestablishedExit = false;
    bool hasAnyExit = false;
    const Vector3& junctionPos = g_placedPlatforms[junctionPlatformIndex].position;
    for (int neighborPi = 0; neighborPi < (int)g_placedPlatforms.size(); neighborPi++) {
        if (neighborPi == junctionPlatformIndex) continue;
        if (!ArePlatformsAdjacent(junctionPos, g_placedPlatforms[neighborPi].position, g_gridSpacing)) continue;
        hasAnyExit = true;
        int lineIndex = GetLineIndexFromPlatformIndex(neighborPi);
        if (!IsLineEstablishedByIndex(lineIndex)) {
            hasNeutralOrUnestablishedExit = true;
            continue;
        }
        establishedLinesAtJunction.insert(lineIndex);
    }
    if (outEstablishedLineCount) *outEstablishedLineCount = (int)establishedLinesAtJunction.size();
    if (!hasAnyExit) {
        if (outReasonCode) *outReasonCode = 2;
        return false;
    }
    if (establishedLinesAtJunction.empty()) {
        if (outReasonCode) *outReasonCode = 3;
        return false;
    }
    if (hasNeutralOrUnestablishedExit) {
        if (outReasonCode) *outReasonCode = 4;
        return false;
    }
    int baseLineIndex = *establishedLinesAtJunction.begin();
    Color baseColor = g_lines[baseLineIndex].color;
    for (int lineIndex : establishedLinesAtJunction) {
        const Color& c = g_lines[lineIndex].color;
        if (c.r != baseColor.r || c.g != baseColor.g || c.b != baseColor.b) {
            if (outReasonCode) *outReasonCode = 5;
            return false;
        }
    }
    if (outReasonCode) *outReasonCode = 0;
    return true;
}

