#include "raylib.h"
#include "raymath.h"
#include "rlgl.h"
#include <math.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <vector>
#include <cmath>

// Export functions for Python embedding
#ifdef __cplusplus
extern "C" {
#endif

// Global framebuffer (declared early, initialized later)
RenderTexture2D g_framebuffer = {0};
bool g_framebuffer_initialized = false;
unsigned char* g_frame_buffer_data = NULL;
int g_frame_buffer_size = 0;
bool g_game_initialized = false;

// Optimization: Render at half resolution (dynamically adjustable)
int g_dynamicRenderWidth = 600;
int g_dynamicRenderHeight = 400;
#define RENDER_WIDTH g_dynamicRenderWidth
#define RENDER_HEIGHT g_dynamicRenderHeight
#define VIRTUAL_WIDTH 1200
#define VIRTUAL_HEIGHT 800

// Input state tracking (for headless mode)
struct InputState {
    bool keys[512];  // KEY_* enum values
    bool keysPressed[512];  // One-time press events
    bool mouseButtons[8];  // MOUSE_BUTTON_* enum values
    bool mouseButtonsPressed[8];  // One-time press events
    bool mouseButtonsReleased[8];  // One-time release events
    Vector2 mousePosition;
    Vector2 mouseDelta;
    bool inputUpdated;  // Flag to clear pressed/released after one frame
} g_inputState = {0};

// C export functions for Python (use __cdecl calling convention)
__declspec(dllexport) __cdecl unsigned char* GetFrameBuffer() {
    if (!g_framebuffer_initialized || g_framebuffer.texture.id == 0) {
        return NULL;
    }
    
    // Read pixels from the render texture
    // PERFORMANCE NOTE: This is the bottleneck - glReadPixels forces GPU->CPU transfer
    // The game renders fast on GPU, but reading back 600x400x4 bytes (960KB) every frame
    // causes pipeline stalls. Ideal solution: Share OpenGL texture directly with Pygame
    // to avoid CPU readback entirely. Current workaround: Keep resolution low (600x400).
    
    // OPTIMIZATION: Use rlReadTexturePixels directly to avoid Image struct overhead
    // This still does glReadPixels internally, but avoids one allocation/free cycle
    int width = g_framebuffer.texture.width;
    int height = g_framebuffer.texture.height;
    int size = width * height * 4; // RGBA
    
    // Allocate persistent buffer if needed
    if (g_frame_buffer_size != size) {
        if (g_frame_buffer_data) {
            MemFree(g_frame_buffer_data);
        }
        g_frame_buffer_data = (unsigned char*)MemAlloc(size);
        g_frame_buffer_size = size;
    }
    
    // Read texture pixels directly into our buffer
    // This internally uses glReadPixels which is slow, but we avoid Image allocation
    void* pixels = rlReadTexturePixels(g_framebuffer.texture.id, width, height, g_framebuffer.texture.format);
    if (pixels) {
        memcpy(g_frame_buffer_data, pixels, size);
        MemFree(pixels); // rlReadTexturePixels allocates, we must free
    } else {
        // Fallback to LoadImageFromTexture if rlReadTexturePixels fails
        Image img = LoadImageFromTexture(g_framebuffer.texture);
    memcpy(g_frame_buffer_data, img.data, size);
    UnloadImage(img);
    }
    
    return g_frame_buffer_data;
}

__declspec(dllexport) __cdecl int GetWidth() {
    if (!g_framebuffer_initialized) return 0;
    return g_framebuffer.texture.width;
}

__declspec(dllexport) __cdecl int GetHeight() {
    if (!g_framebuffer_initialized) return 0;
    return g_framebuffer.texture.height;
}

__declspec(dllexport) __cdecl unsigned int GetFrameTextureHandle() {
    return g_framebuffer.texture.id;
}

__declspec(dllexport) __cdecl void SetRenderResolution(int width, int height) {
    if (g_framebuffer_initialized || g_game_initialized) {
        printf("[SetRenderResolution] Warning: Attempted to change resolution after initialization - request ignored.\n");
        return;
    }
    if (width < 320) width = 320;
    if (height < 200) height = 200;
    g_dynamicRenderWidth = width;
    g_dynamicRenderHeight = height;
    printf("[SetRenderResolution] Using custom %dx%d render resolution.\n", width, height);
}

__declspec(dllexport) __cdecl void SetRenderResolutionPreset(int preset) {
    if (g_framebuffer_initialized || g_game_initialized) {
        printf("[SetRenderResolutionPreset] Warning: Attempted to change resolution after initialization - request ignored.\n");
        return;
    }
    
    int newWidth = 600;
    int newHeight = 400;
    
    switch (preset) {
        case 0: // Low
            newWidth = 480;
            newHeight = 320;
            break;
        case 2: // High
            newWidth = 720;
            newHeight = 480;
            break;
        default: // Medium / fallback
            newWidth = 600;
            newHeight = 400;
            break;
    }
    
    g_dynamicRenderWidth = newWidth;
    g_dynamicRenderHeight = newHeight;
    printf("[SetRenderResolutionPreset] Using %dx%d render resolution preset (%d).\n", newWidth, newHeight, preset);
}

// Forward declarations for functions defined later
__declspec(dllexport) __cdecl bool InitializeGame();
__declspec(dllexport) __cdecl void UpdateFrame();
__declspec(dllexport) __cdecl void SetKeyState(int key, bool down);
__declspec(dllexport) __cdecl void SetMouseButtonState(int button, bool down);
__declspec(dllexport) __cdecl void SetInputMousePosition(float x, float y);
__declspec(dllexport) __cdecl void SetMouseDelta(float dx, float dy);
__declspec(dllexport) __cdecl void ClearInputFrame();  // Call at end of frame to clear pressed/released flags
__declspec(dllexport) __cdecl bool ShouldExit();  // Check if game wants to exit
__declspec(dllexport) __cdecl bool ShouldCenterMouse();  // Check if mouse should be centered (returns true once, then resets)
__declspec(dllexport) __cdecl void CleanupGame();  // Tear down window/audio so BBS can relaunch cleanly

Mesh CreateStationMesh(); // Added forward decl

// Forward declarations for leaderboard functions
int CalculateFinalScore(int credits, int rank);
void LoadLeaderboard();
void SaveLeaderboard();
void SaveGame();  // Save game state to file
bool LoadGame();  // Load game state from file, returns true if successful
void DrawNoSaveModal();  // Draw modal when save game not found
void AddToLeaderboard(int score, int credits, int rank);
void DrawLeaderboardModal();
void SetUsername(const char* username);
void ResetPlayerStats();  // Reset all player stats to new game defaults

#ifdef __cplusplus
}
#endif

// ------------------------------------------------------------
// GAME STATES & SHARED DATA
// ------------------------------------------------------------
typedef enum {
    STATE_SPLASH,
    STATE_DEPOT_HOME,
    STATE_LANDER,
    STATE_DEBRIS,
    STATE_DEPOT_SELECT,
    STATE_BAR,
    STATE_SHIPYARD,
    STATE_MARKET,
    STATE_LODGINGS,
    STATE_NAV_SCREEN,
    STATE_STATION_HOME,
    STATE_HALO_HOME,
    STATE_GAME_OVER
} GameState;

// ------------------------------------------------------------
// COMMODITIES SYSTEM
// ------------------------------------------------------------
typedef enum {
    COMMODITY_WATER_ICE = 0,
    COMMODITY_LUNAR_REGOLITH,
    COMMODITY_HYDROCARBONS,
    COMMODITY_CRYOGENIC_FLUIDS,
    COMMODITY_HELIUM_4,
    COMMODITY_HYDROGEN_ISOTOPES,
    COMMODITY_ARCANITE,
    COMMODITY_PYROTHITE,
    COMMODITY_CHRONITE,
    COMMODITY_XENON_CRYSTALS,
    COMMODITY_PLASMATIC_DIAMONDS,
    NUM_COMMODITIES
} CommodityType;

const char* g_commodityNames[NUM_COMMODITIES] = {
    "WATER ICE", "LUNAR REGOLITH", "HYDROCARBONS", 
    "CRYOGENIC FLUIDS", "HELIUM-4 ISOTOPES", "HYDROGEN ISOTOPES",
    "ARCANITE", "PYROTHITE GEODES", "CHRONITE",
    "XENON CRYSTALS", "PLASMATIC DIAMONDS"
};

// Base prices for commodities (in credits per unit)
int g_commodityBasePrices[NUM_COMMODITIES] = {
    5, 10, 15,    // Low: Water Ice, Lunar Regolith, Hydrocarbons
    30, 50, 70,   // Medium: Cryogenic Fluids, Helium-4, Hydrogen Isotopes
    120, 180, 250,// High: Arcanite, Pyrothite Geodes, Chronite
    400, 800      // Very High: Xenon Crystals, Plasmatic Diamonds
};

// Asteroid-to-Commodity Abundance Matrix
// Each asteroid (index 0-5 = A-F) has a distribution of commodities
// Values represent relative abundance (0-100), higher = more common
// Based on Oort Cloud science: ice/volatiles common, exotic materials rare
int g_asteroidCommodityAbundance[6][NUM_COMMODITIES] = {
    // Asteroid A (Low prosperity): More common materials, rare materials very rare
    // Water Ice, Regolith, Hydrocarbons, Cryogenic Fluids, Helium-4, Hydrogen Isotopes, Arcanite, Pyrothite, Chronite, Xenon, Plasmatic
    {80, 70, 60, 40, 30, 25, 5, 4, 3, 1, 1},  // Hundreds: 5-3%, Thousands: 1%
    // Asteroid B
    {75, 65, 55, 45, 35, 30, 8, 6, 4, 1, 1},  // Hundreds: 8-4%, Thousands: 1%
    // Asteroid C (Medium prosperity): Balanced
    {70, 60, 50, 50, 40, 35, 12, 10, 7, 2, 1},  // Hundreds: 12-7%, Thousands: 2-1%
    // Asteroid D
    {65, 55, 45, 55, 45, 40, 15, 12, 9, 2, 1},  // Hundreds: 15-9%, Thousands: 2-1%
    // Asteroid E (High prosperity): More rare materials but still rare
    {60, 50, 40, 60, 50, 45, 18, 15, 12, 3, 2},  // Hundreds: 18-12%, Thousands: 3-2%
    // Asteroid F (Very high prosperity): Exotic materials slightly more common but still rare
    {55, 45, 35, 65, 55, 50, 20, 18, 15, 4, 3}   // Hundreds: 20-15%, Thousands: 4-3%
};

// Station-specific buy prices (calculated based on available asteroids)
int g_stationBuyPrices[3][NUM_COMMODITIES];  // [location][commodity]

typedef struct {
    float fuel;
    float maxFuel;
    float hull;
    float maxHull;
    float power;      // Current thrust power
    float maxPower;   // Max thrust power (100)
    int rank;         // Rank level (1-5)
    int credits;
    int maxCredits;   // Max credits (100000)
    int totalCreditsEarned;  // Lifetime total credits earned (for rank progression)
    int cargoSpace;
    int cargoFilled;
    // Market Goods - REPLACED with Inventory Array
    int inventory[NUM_COMMODITIES];
    bool hasLaser;  // Whether player has a laser equipped
    bool hasCollector;  // Whether player has collector upgrade
    float thrusterBoost;  // Thruster boost multiplier (1.0 = no boost, 1.2 = 20% boost)
    float hullResistance;  // Hull damage reduction multiplier (1.0 = normal, 0.8 = 20% less damage)
    bool hasGoldCard;  // Whether player has the Commodities Gold Card
    // Laser Heat System
    float laserHeat;        // Current heat (0.0 to 100.0)
    float maxLaserHeat;     // Max heat (100.0)
    float laserCooldown;    // Timer for overheat cooldown
    bool laserOverheated;   // Flag if overheated
    // Ship upgrades
    bool hasFuelTankUpgrade;  // Station: Increased fuel capacity
    bool hasCargoBlackHole;  // Station: 50 cargo capacity
    bool hasBetterLaser;      // Halo: Better laser
    bool hasBetterCollector;  // Halo: Better collector
    int shipColor;            // 0=Blue (default), 1=Red, 2=Green, 3=Purple
} PlayerData;

// Global Player Instance - New game defaults
// cargoSpace = 50 (max cargo capacity) - actually used as 25 for debris
// hasLaser = false (new players start with no laser)
PlayerData G_Player = { 
    100.0f, 100.0f, 100.0f, 100.0f, 20.0f, 100.0f, // fuel, maxFuel, hull, maxHull, power, maxPower
    1, 1000, 100000, 0, // rank, credits, maxCredits, totalCreditsEarned
    25, 0, // cargoSpace, cargoFilled
    {0,0,0,0,0,0,0,0,0,0,0}, // Inventory initialized to 0
    false, false, // hasLaser, hasCollector
    1.0f, 1.0f, // thrusterBoost, hullResistance
    false, // hasGoldCard
    0.0f, 100.0f, 0.0f, false, // laserHeat, maxLaserHeat, laserCooldown, laserOverheated
    false, false, false, false, 0 // hasFuelTankUpgrade, hasCargoBlackHole, hasBetterLaser, hasBetterCollector, shipColor
};

// ------------------------------------------------------------
// ROCKS & DEBRIS SYSTEM
// ------------------------------------------------------------
// (Moved to correct location after constants and helper functions)

// Global game state variables (declared after types/constants)
GameState g_currentState = STATE_SPLASH;  // Start with splash screens
GameState g_previousState = STATE_SPLASH;  // Track previous state for ESC navigation
bool g_isPaused = false;  // Pause state for 3D environment
int g_menuSelection = 0;
Vector3 g_shipPos = {0, 60, 0};  // Will be initialized properly in InitializeGame()
Vector3 g_shipVel = {0, 0, 10};
float g_shipPitch = 0.0f;
float g_shipRoll = 0.0f;
float g_shipYaw = 0.0f;
int g_yawDirection = 1;
Camera3D g_camera = {0};
Model g_ship = {0};
Model g_rockModel = {0};
Model g_shopItemModels[6] = {0};  // Shop item models: A=Laser, B=Collector, C=Thruster, D=ExoPlating, E=Fuel, F=Repairs
Model g_stationShopModels[6] = {0};  // Station shop models: A=FuelTank, B=CargoBlackHole, C=Fuel, D=RedShip, E=GreenShip, F=PurpleShip
Model g_haloShopModels[6] = {0};  // Halo shop models: A=BetterLaser, B=BetterCollector, C=Fuel, D=RedShip, E=GreenShip, F=PurpleShip
Model g_goldShipModel = {0};  // Gold ship model (50% better, available at Halo)
Texture2D scanlineTx = {0};
Texture2D guiHudTx = {0};
Texture2D splash0Tx = {0};
Texture2D splash1Tx = {0};
Texture2D splash2Tx = {0};
Texture2D splashNewGameTx = {0};
Texture2D splashLoadGameTx = {0};
Texture2D splashQuitGameTx = {0};
// Depot home page PNGs
Texture2D prospectGuiTx = {0};
Texture2D asteroidProspectsBgTx = {0}; // Astriod_Prospects.png background
Texture2D shipyardGuiTx = {0};
Texture2D upgradesShinjukuTx = {0}; // upgrades_shijuku.png for Depot
Texture2D upgradesHirohitoTx = {0}; // upgrades_hirohito.png for Station
Texture2D upgradesNagakoTx = {0}; // upgrades_nagako.png for Halo
Texture2D commoditiesGuiTx = {0};
Texture2D commoditiesMarketTx = {0}; // New market background
Texture2D barGuiTx = {0};
// Prospect page overlays (base + A-F variants)
Texture2D prospectPageTx = {0};  // Base prospect_page.png
Texture2D prospectPageATx = {0}; // prospect_page_A.png
Texture2D prospectPageBTx = {0}; // prospect_page_B.png
Texture2D prospectPageCTx = {0}; // prospect_page_C.png
Texture2D prospectPageDTx = {0}; // prospect_page_D.png
Texture2D prospectPageETx = {0}; // prospect_page_E.png
Texture2D prospectPageFTx = {0}; // prospect_page_F.png
int g_depotHomePage = 1;  // Current page (1-4)
bool g_showProspectAsteroids = false;  // Show asteroid prospects when Enter pressed on page 1
int g_prospectPageOverlay = 0;  // 0=base, 1=A, 2=B, 3=C, 4=D, 5=E, 6=F
bool g_showAsteroidModal = false;  // Show modal when asteroid letter is pressed
int g_modalSelection = 0;  // 0=Launch, 1=Exit
int g_selectedAsteroidIndex = 0;  // Which asteroid (0-5 = A-F)
int g_selectedAsteroidFuelCost = 0;  // Random fuel cost (20-50)
int g_selectedAsteroidGravity = 0;  // Gravity percentage of selected asteroid
int g_selectedAsteroidProspect = 0;  // Prosperity percentage of selected asteroid
bool g_fuelCheckFailed = false;  // Flag for fuel check failure
bool g_showFuelWarningModal = false;  // Show separate fuel warning modal
float g_fuelWarningTimer = 0.0f;  // Timer for fuel warning modal (3 seconds)
bool g_missionInProgress = false;  // Track if player is on a mission (for return fuel deduction)
bool g_wasInsideCylinder = false;  // Track if ship was inside exit cylinder to play beam-up sound once
float g_asteroidRotation = 0.0f;  // Rotation angle for spinning asteroids
bool g_showGetReady = false;  // Show "GET READY" splash screen before lander
float g_getReadyTimer = 0.0f;  // Timer for GET READY screen (2 seconds)
RenderTexture2D g_asteroidViewport = {0};  // Render texture for asteroid view (like StationViewport)
RenderTexture2D g_navViewport = {0};  // Render texture for navigation screen
bool g_navViewportInitialized = false;
bool g_asteroidViewportInitialized = false;

// Audio
Sound g_terminalTypeSound = {0};  // Sound for terminal typing
Sound g_laserSound = {0};         // Sound for laser firing
Sound g_thrusterSound = {0};      // Sound for thrusters firing
Sound g_saleSound = {0};          // Sound for selling commodities
Sound g_fuelSound = {0};          // Sound for purchasing fuel
Sound g_noSound = {0};            // Sound for when trying to sell commodities you don't have
Sound g_crashSound = {0};         // Sound for when hull point is lost
Sound g_explodeSound = {0};       // Sound for when ship is destroyed
Sound g_enteringStationSound = {0}; // Sound for entering station/halo/depot
Sound g_beamUpSound = {0};        // Sound for beam-up when entering red cylinder
Sound g_launchSequenceSound = {0}; // Sound for launch sequence when entering 3D environment
Sound g_collectSound = {0};       // Sound for when cargo is collected
Sound g_rockSound = {0};          // Sound for when rock is destroyed and debris is released
Sound g_fixingOnSound = {0};      // Sound for when upgrade is purchased
Sound g_barSound = {0};           // Sound for entering bar
Sound g_levelupSound = {0};       // Sound for leveling up
Music g_backgroundMusic = {0};  // Background music (AstroMiner.mp3)
Music g_backgroundMusic2 = {0}; // Background music 2 (AstroMiner2.mp3)
Music g_splashMusic = {0};       // Background music for splash screen (bostonpump.wav)
int g_currentTrack = 0; // 0=AstroMiner, 1=AstroMiner2
bool g_splashMusicFadingOut = false; // Flag to track if splash music is fading out
float g_splashMusicFadeOutTime = 0.0f; // Time elapsed during fade out
float g_splashMusicFadeOutDuration = 1.0f; // Duration of fade out in seconds

// Shipyard shop system
bool g_showShipyardShop = false;  // Show shipyard shop when Enter pressed on page 2
int g_shipyardPageOverlay = 0;  // 0=base, 1=A, 2=B, 3=C, 4=D, 5=E, 6=F
bool g_showShopModal = false;  // Show modal when shop item letter is pressed
bool g_showCommoditiesMarket = false;  // Show commodities market when Enter pressed on page 3
int g_commoditiesMarketSelection = 0;  // Selected commodity index (0-NUM_COMMODITIES)
bool g_showNoCommodityModal = false;  // Show modal when trying to sell commodity you don't have
char g_noCommodityName[64] = "";  // Name of commodity you tried to sell
bool g_showNoSaveModal = false;  // Show modal when save game not found
int g_shopModalSelection = 0;  // 0=Purchase, 1=Exit
int g_selectedShopItemIndex = 0;  // Which shop item (0-5 = A-F)
bool g_purchaseFailed = false;  // Flag for purchase failure (insufficient credits)
char g_purchaseFailReason[64] = "INSUFFICIENT CREDITS";  // Reason for purchase failure
RenderTexture2D g_shipyardShopViewport = {0};  // Render texture for shop view
bool g_shipyardShopViewportInitialized = false;
float g_shopItemRotation = 0.0f;  // Rotation angle for shop items
RenderTexture2D g_commoditiesMarketViewport = {0};  // Render texture for commodities market view
bool g_commoditiesMarketViewportInitialized = false;

// Asteroid Data (Persistent for Bar events)
// Depot asteroids (lower prosperity, lower fuel)
int g_prospectScores[6] = {10, 22, 34, 46, 58, 70};
int g_gravityScores[6] = {25, 38, 51, 64, 76, 88};
int g_fuelCosts[6] = {0}; // Persistent fuel costs per asteroid (initialized in InitializeGame)

// Station asteroids (higher prosperity, higher fuel)
int g_stationProspectScores[6] = {35, 48, 62, 75, 85, 95};
int g_stationGravityScores[6] = {45, 58, 71, 84, 90, 95};
// Halo asteroids (highest prosperity, highest fuel)
int g_haloProspectScores[6] = {50, 65, 78, 88, 95, 100};
int g_haloGravityScores[6] = {55, 68, 81, 90, 95, 98};

// Forward declarations for commodity functions
void ConvertDebrisToCommodity();
void CalculateStationPrices();
void RenderCommoditiesMarket();

// Shop item overlay textures
Texture2D shipyardPageTx = {0};  // Base shipyard_page.png
Texture2D shipyardPageATx = {0}; // shipyard_page_A.png
Texture2D shipyardPageBTx = {0}; // shipyard_page_B.png
Texture2D shipyardPageCTx = {0}; // shipyard_page_C.png
Texture2D shipyardPageDTx = {0}; // shipyard_page_D.png
Texture2D shipyardPageETx = {0}; // shipyard_page_E.png
Texture2D shipyardPageFTx = {0}; // shipyard_page_F.png

// Bar system
Texture2D barPageTx = {0}; // bar_page.png
// Station, Halo, and Depot overlays
Texture2D hirohitoOverlayTx = {0}; // Hirohito_overlay.png
Texture2D nagakoOverlayTx = {0};  // Nagako_overlay.png
Texture2D shinjukuOverlayTx = {0}; // Shinjuku_overlay.png
// Track current location for customization
int g_currentLocation = 0; // 0=Depot, 1=Station, 2=Halo
bool g_showBarView = false;
float g_barModalTimer = 0.0f; // Delay timer for modal appearance
int g_barDrinksPurchased = 0;
bool g_barJustOpened = false; // Flag to prevent Enter key from immediately purchasing after opening bar
bool g_showBarRumorModal = false;
bool g_showBarGoldCardModal = false;
bool g_showBarGamblingModal = false;
bool g_showBarScientistModal = false;
bool g_showBarSuccessModal = false;  // Success modal for 5 drinks reward
bool g_showExitToMainMenuModal = false;  // Show exit to main menu confirmation modal
float g_barModalDelayTimer = 0.0f;  // Timer for 1 second delay before showing bar modals
int g_barModalPendingType = 0;  // 0=none, 1=rumor, 2=goldcard, 3=gambling, 4=scientist, 5=success, 6=laserUpgrade
int g_exitModalSelection = 0;  // 0=YES, 1=NO
bool g_showWelcomeModal = false;  // Show welcome modal when starting new game
char g_barRumorText[512] = {0};
char g_barGamblingText[512] = {0};
char g_barScientistText[512] = {0};
char g_barSuccessText[512] = {0};
char g_barLaserUpgradeText[512] = {0};
int g_barMenuSelection = 0; // Menu selection (varies by location)
int g_barRandomMood = 0; // Random mood index for bar atmosphere
int g_barMaxMenuItems = 4; // Number of menu items (varies by location)
// Bar visit tracking for special options (3rd visit unlocks)
int g_barVisitCounts[3] = {0, 0, 0}; // [0]=Depot, [1]=Station, [2]=Halo
bool g_barScientistUsed = false; // Station bar scientist option used
bool g_barStoriesUsed = false; // Halo bar stories option used
bool g_barLaserUpgradeUsed = false; // Depot bar laser upgrade option used
bool g_showBarLaserUpgradeModal = false; // Modal for laser upgrade
bool g_isDrunk = false;  // Drunk state from too many drinks
int g_drunkGravityIncrease = 0;  // Gravity increase percentage (10-30%)
int g_drunkThreshold = 0;  // Random threshold for getting drunk (5-10 drinks)
bool g_showDrunkModal = false;  // Show drunk modal
char g_drunkText[512] = {0};
bool g_shouldCenterMouse = false;  // Flag to signal mouse should be centered (for 3D lander)
bool g_showRankUpModal = false;  // Show rank-up celebration modal
int g_newRank = 0;  // New rank achieved
char g_rankUpMessage[512] = {0};
float g_rankUpFireworksTimer = 0.0f;  // Timer for fireworks animation
const char* g_barMoods[] = {
    "THE AIR IS THICK WITH SMOKE AND THE SMELL OF OZONE.",
    "A ROWDY GROUP OF MINERS ARE SINGING SHANTIES IN THE CORNER.",
    "THE BARTENDER WIPES A GLASS, LOOKING BORED.",
    "A HOLOGRAPHIC DANCER FLICKERS INTERMITTENTLY ON THE STAGE.",
    "YOU HEAR WHISPERS OF A BIG STRIKE IN SECTOR 7.",
    "THE JUKEBOX IS PLAYING A SCRATCHY OLD JAZZ TUNE."
};
int g_numBarMoods = 6;

// Retro font for stats overlay
Font retroFont = {0};

// Splash screen state
int g_splashIndex = 0;  // 0=splash0, 1=splash1, 2=splash2, 3=menu
float g_splashTimer = 0.0f;
float g_splashBeatDuration = 1.0f;  // 1 second per beat
int g_menuOption = 0;  // 0=new game, 1=load game, 2=quit
bool g_exit_requested = false;  // Flag to signal exit to BBS

// Leaderboard system
#define MAX_LEADERBOARD_ENTRIES 10
#define MAX_USERNAME_LENGTH 32
typedef struct {
    int score;
    int credits;
    int rank;
    char rankName[32];
    char username[MAX_USERNAME_LENGTH];
} LeaderboardEntry;

LeaderboardEntry g_leaderboard[MAX_LEADERBOARD_ENTRIES];
int g_leaderboardCount = 0;
int g_lastFinalScore = 0;  // Last calculated final score
bool g_showLeaderboard = false;  // Show leaderboard modal after splash2
bool g_leaderboardDismissed = false;  // Track if leaderboard was dismissed
char g_currentUsername[MAX_USERNAME_LENGTH] = "PLAYER";  // Current BBS username

void DrawScanlines() {
    if (scanlineTx.id > 0) {
        DrawTexturePro(scanlineTx, 
            (Rectangle){0, 0, (float)scanlineTx.width, (float)scanlineTx.height}, 
            (Rectangle){0, 0, VIRTUAL_WIDTH, VIRTUAL_HEIGHT}, 
            (Vector2){0, 0}, 0.0f, (Color){255, 255, 255, 255});
    }
}

// ------------------------------------------------------------
// CONSTANTS (LANDER)
// ------------------------------------------------------------
#define NUM_ROCKS 1000
#define TRIS_PER_ROCK 36
#define ROCK_TRI_COUNT (NUM_ROCKS * TRIS_PER_ROCK)
#define PROSPECT_PERIMETER 120.0f 
#define RENDER_DISTANCE 15
#define CHUNK_SIZE 8 
#define CHUNKS_AXIS (int)((PROSPECT_PERIMETER * 2) / CHUNK_SIZE)
#define TOTAL_CHUNKS (CHUNKS_AXIS * CHUNKS_AXIS)
#define GRID_CELL_SIZE 16.0f
#define GRID_DIM (int)((PROSPECT_PERIMETER * 2.0f) / GRID_CELL_SIZE) + 2
#define MAX_ROCKS_PER_CELL 128

// Global arrays (declared after TOTAL_CHUNKS is defined)
Model g_chunkModels[TOTAL_CHUNKS] = {0};
Vector2 g_chunkCenters[TOTAL_CHUNKS] = {0};

// --- SHIP ENGINE STATS (UPGRADEABLE) ---
float SHIP_GRAVITY = -12.0f;
float SHIP_THRUST_POWER = 24.0f;  // 20% stronger than before (20.0f * 1.2 = 24.0f) 
float SHIP_DRAG_FACTOR = 0.985f;
float SHIP_FUEL_BURN_RATE = 1.0f / 10.0f; 

// ------------------------------------------------------------
// DATA STRUCTURES (LANDER)
// ------------------------------------------------------------
typedef struct Tri { Vector3 a; Vector3 b; Vector3 c; } Tri;
Tri G_RockTris[ROCK_TRI_COUNT];

struct RockInstance {
    Vector3 position;
    Vector3 axis;
    float angle;
    float scale;
    Color color;
    bool active;
    int prosperityPercentage;  // Prosperity percentage of the asteroid this rock came from
};
RockInstance G_Rocks[NUM_ROCKS];

struct GridCell {
    int count;
    int rockIndices[MAX_ROCKS_PER_CELL];
};
GridCell G_CollisionGrid[GRID_DIM][GRID_DIM];

struct Particle { Vector3 pos; Vector3 vel; Color color; float life; bool onGround; };
#define MAX_PARTICLES 5000  // Increased for thousands of explosion cubes
Particle particles[MAX_PARTICLES] = {0};

// ------------------------------------------------------------
// LANDER MATH & PHYSICS
// ------------------------------------------------------------
float GetTerrainHeight(float x, float z) {
    return 1.2f * sinf(x * 0.15f) + 0.8f * cosf(z * 0.12f) + 0.4f * sinf((x + z) * 0.08f);
}

bool GetHeightOnTriangle(Vector3 p1, Vector3 p2, Vector3 p3, float x, float z, float* outY) {
    float det = (p2.z - p3.z) * (p1.x - p3.x) + (p3.x - p2.x) * (p1.z - p3.z);
    if (fabs(det) < 0.0001f) return false;
    float l1 = ((p2.z - p3.z) * (x - p3.x) + (p3.x - p2.x) * (z - p3.z)) / det;
    float l2 = ((p3.z - p1.z) * (x - p3.x) + (p1.x - p3.x) * (z - p3.z)) / det;
    float l3 = 1.0f - l1 - l2;
    if (l1 >= 0.0f && l1 <= 1.0f && l2 >= 0.0f && l2 <= 1.0f && l3 >= 0.0f && l3 <= 1.0f) {
        *outY = l1 * p1.y + l2 * p2.y + l3 * p3.y;
        return true;
    }
    return false;
}

float GetWorldHeight(float x, float z) {
    float height = GetTerrainHeight(x, z);
    float offset = PROSPECT_PERIMETER;
    int cellX = (int)((x + offset) / GRID_CELL_SIZE);
    int cellZ = (int)((z + offset) / GRID_CELL_SIZE);

    if (cellX >= 0 && cellX < GRID_DIM && cellZ >= 0 && cellZ < GRID_DIM) {
        GridCell* cell = &G_CollisionGrid[cellX][cellZ];
        for(int i = 0; i < cell->count; i++) {
            int rockIdx = cell->rockIndices[i];
            // Fix: Check if rock is active before using its collision mesh
            if (!G_Rocks[rockIdx].active) continue;
            
            int startTri = rockIdx * TRIS_PER_ROCK;
            // Fix: Check if rock is active before using its collision mesh
            if (!G_Rocks[rockIdx].active) continue;
            
            int endTri = startTri + TRIS_PER_ROCK;
            for (int t = startTri; t < endTri; t++) {
                float triH;
                if (GetHeightOnTriangle(G_RockTris[t].a, G_RockTris[t].b, G_RockTris[t].c, x, z, &triH)) {
                    if (triH > height) height = triH;
                }
            }
        }
    }
    return height;
}

// ------------------------------------------------------------
// INITIALIZATION HELPERS
// ------------------------------------------------------------
void InitCollisionGrid() {
    for(int i=0; i<GRID_DIM; i++) for(int j=0; j<GRID_DIM; j++) G_CollisionGrid[i][j].count = 0;
    float offset = PROSPECT_PERIMETER;
    for (int r = 0; r < NUM_ROCKS; r++) {
        float radius = G_Rocks[r].scale * 1.5f;
        int startX = (int)((G_Rocks[r].position.x - radius + offset) / GRID_CELL_SIZE);
        int endX = (int)((G_Rocks[r].position.x + radius + offset) / GRID_CELL_SIZE);
        int startZ = (int)((G_Rocks[r].position.z - radius + offset) / GRID_CELL_SIZE);
        int endZ = (int)((G_Rocks[r].position.z + radius + offset) / GRID_CELL_SIZE);
        if (startX < 0) startX = 0; if (startX >= GRID_DIM) startX = GRID_DIM - 1;
        if (endX < 0) endX = 0; if (endX >= GRID_DIM) endX = GRID_DIM - 1;
        if (startZ < 0) startZ = 0; if (startZ >= GRID_DIM) startZ = GRID_DIM - 1;
        if (endZ < 0) endZ = 0; if (endZ >= GRID_DIM) endZ = GRID_DIM - 1;
        for (int x = startX; x <= endX; x++) {
            for (int z = startZ; z <= endZ; z++) {
                if (G_CollisionGrid[x][z].count < MAX_ROCKS_PER_CELL) {
                    G_CollisionGrid[x][z].rockIndices[G_CollisionGrid[x][z].count] = r;
                    G_CollisionGrid[x][z].count++;
                }
            }
        }
    }
}

// ------------------------------------------------------------
// RESTORED: MESH & PARTICLE HELPERS
// ------------------------------------------------------------

Mesh CreateSolidShip() {
    Vector3 nose={0,0,1.0f}, tail={0,0,-1.0f}, left={-0.8f,0,-0.5f}, right={0.8f,0,-0.5f}, top={0,0.3f,-0.2f}, bottom={0,-0.3f,-0.2f};
    Vector3 tris[8][3]={{top,left,nose},{top,nose,right},{top,tail,left},{top,right,tail},{bottom,nose,left},{bottom,right,nose},{bottom,left,tail},{bottom,tail,right}};
    Color col[8]={{135,206,250,255},{70,170,240,255},{30,144,255,255},{0,100,220,255},{0,60,180,255},{0,40,140,255},{0,20,100,255},{0,5,60,255}};
    Mesh mesh={0}; mesh.triangleCount=8; mesh.vertexCount=24;
    mesh.vertices=(float*)MemAlloc(mesh.vertexCount*3*sizeof(float));
    mesh.normals=(float*)MemAlloc(mesh.vertexCount*3*sizeof(float));
    mesh.colors=(unsigned char*)MemAlloc(mesh.vertexCount*4);
    int idx=0;
    for(int t=0;t<8;t++){
        Vector3 n=Vector3Normalize(Vector3CrossProduct(Vector3Subtract(tris[t][1],tris[t][0]), Vector3Subtract(tris[t][2],tris[t][0])));
        for(int k=0;k<3;k++){
            mesh.vertices[idx*3+0]=tris[t][k].x; mesh.vertices[idx*3+1]=tris[t][k].y; mesh.vertices[idx*3+2]=tris[t][k].z;
            mesh.normals[idx*3+0]=n.x; mesh.normals[idx*3+1]=n.y; mesh.normals[idx*3+2]=n.z;
            mesh.colors[idx*4+0]=col[t].r; mesh.colors[idx*4+1]=col[t].g; mesh.colors[idx*4+2]=col[t].b; mesh.colors[idx*4+3]=col[t].a;
            idx++;
        }
    }
    UploadMesh(&mesh,false); return mesh;
}

Mesh CreateStationMesh() {
    // Legacy function, might not be needed if using StationViewport
    return (Mesh){0};
}

Mesh CreateBaseRockMesh() {
    float phi = 1.61803398875f; float inv = 1.0f/phi;
    Vector3 vLocal[20] = {{1,1,1},{1,1,-1},{1,-1,1},{1,-1,-1},{-1,1,1},{-1,1,-1},{-1,-1,1},{-1,-1,-1},{0,inv,phi},{0,inv,-phi},{0,-inv,phi},{0,-inv,-phi},{inv,phi,0},{inv,-phi,0},{-inv,phi,0},{-inv,-phi,0},{phi,0,inv},{phi,0,-inv},{-phi,0,inv},{-phi,0,-inv}};
    int faces[12][5] = {{0,16,2,10,8},{0,8,4,14,12},{16,17,1,12,0},{1,9,11,3,17},{1,12,14,5,9},{2,13,15,6,10},{13,3,11,7,15},{4,8,10,6,18},{14,4,18,19,5},{5,19,7,11,9},{15,7,19,18,6},{2,16,17,3,13}};
    Color rockPalette[12] = {{80,80,80,255},{100,100,105,255},{90,85,80,255},{70,70,70,255},{60,60,65,255},{110,110,110,255},{55,55,55,255},{75,70,65,255},{65,65,65,255},{85,85,90,255},{45,45,50,255},{95,95,95,255}};
    
    Mesh mesh = {0}; mesh.triangleCount=36; mesh.vertexCount=mesh.triangleCount*3;
    mesh.vertices=(float*)MemAlloc(mesh.vertexCount*3*sizeof(float));
    mesh.normals=(float*)MemAlloc(mesh.vertexCount*3*sizeof(float));
    mesh.colors=(unsigned char*)MemAlloc(mesh.vertexCount*4);
    
    int idx=0;
    for(int f=0;f<12;f++){
        Color faceCol=rockPalette[f];
        Vector3 pLocal[5]; for(int i=0;i<5;i++) pLocal[i]=vLocal[faces[f][i]];
        Vector3 n=Vector3Normalize(Vector3CrossProduct(Vector3Subtract(pLocal[1],pLocal[0]), Vector3Subtract(pLocal[2],pLocal[0])));
        int tris[3][3]={{0,1,2},{0,2,3},{0,3,4}};
        for(int t=0;t<3;t++){
            for(int k=0;k<3;k++){
                int ptIndex=tris[t][k];
                mesh.vertices[idx*3+0]=pLocal[ptIndex].x; mesh.vertices[idx*3+1]=pLocal[ptIndex].y; mesh.vertices[idx*3+2]=pLocal[ptIndex].z;
                mesh.normals[idx*3+0]=n.x; mesh.normals[idx*3+1]=n.y; mesh.normals[idx*3+2]=n.z;
                mesh.colors[idx*4+0]=faceCol.r; mesh.colors[idx*4+1]=faceCol.g; mesh.colors[idx*4+2]=faceCol.b; mesh.colors[idx*4+3]=255; idx++;
            }
        }
    }
    UploadMesh(&mesh,false); return mesh;
}

// Shop item mesh creation functions
Mesh CreateLaserMesh() {
    // Laser: High-tech dual barrel cannon
    Mesh mesh = {0};
    
    // Main housing (Dark Grey Box)
    Mesh housing = GenMeshCube(0.5f, 0.4f, 0.6f);
    // Barrel 1 (Red Cylinder)
    Mesh barrel1 = GenMeshCylinder(0.1f, 1.2f, 16);
    // Barrel 2 (Red Cylinder)
    Mesh barrel2 = GenMeshCylinder(0.1f, 1.2f, 16);
    // Side Power Unit (Blue Box)
    Mesh powerUnit = GenMeshCube(0.7f, 0.2f, 0.3f);
    
    // Calculate total vertices
    int v1 = housing.vertexCount;
    int v2 = barrel1.vertexCount;
    int v3 = barrel2.vertexCount;
    int v4 = powerUnit.vertexCount;
    int totalVerts = v1 + v2 + v3 + v4;
    
    mesh.vertexCount = totalVerts;
    mesh.triangleCount = housing.triangleCount + barrel1.triangleCount + barrel2.triangleCount + powerUnit.triangleCount;
    mesh.vertices = (float*)MemAlloc(totalVerts * 3 * sizeof(float));
    mesh.normals = (float*)MemAlloc(totalVerts * 3 * sizeof(float));
    mesh.colors = (unsigned char*)MemAlloc(totalVerts * 4);
    
    int idx = 0;
    
    // Add Housing
    for(int i=0; i<v1; i++) {
        mesh.vertices[idx*3+0] = housing.vertices[i*3+0];
        mesh.vertices[idx*3+1] = housing.vertices[i*3+1];
        mesh.vertices[idx*3+2] = housing.vertices[i*3+2];
        mesh.normals[idx*3+0] = housing.normals[i*3+0];
        mesh.normals[idx*3+1] = housing.normals[i*3+1];
        mesh.normals[idx*3+2] = housing.normals[i*3+2];
        mesh.colors[idx*4+0]=40; mesh.colors[idx*4+1]=40; mesh.colors[idx*4+2]=40; mesh.colors[idx*4+3]=255; // Dark Grey
        idx++;
    }
    
    // Add Barrel 1 (Left)
    for(int i=0; i<v2; i++) {
        // Rotate cylinder to point forward (Z-axis)
        // Default cylinder is along Y. Rotate 90 deg X.
        float y = barrel1.vertices[i*3+1];
        float z = barrel1.vertices[i*3+2];
        float newY = -z;
        float newZ = y;
        
        mesh.vertices[idx*3+0] = barrel1.vertices[i*3+0] - 0.15f; // Left offset
        mesh.vertices[idx*3+1] = newY;
        mesh.vertices[idx*3+2] = newZ + 0.3f; // Forward offset
        
        // Rotate normal
        float ny = barrel1.normals[i*3+1];
        float nz = barrel1.normals[i*3+2];
        mesh.normals[idx*3+0] = barrel1.normals[i*3+0];
        mesh.normals[idx*3+1] = -nz;
        mesh.normals[idx*3+2] = ny;
        
        mesh.colors[idx*4+0]=220; mesh.colors[idx*4+1]=20; mesh.colors[idx*4+2]=20; mesh.colors[idx*4+3]=255; // Red
        idx++;
    }

    // Add Barrel 2 (Right)
    for(int i=0; i<v3; i++) {
        float y = barrel2.vertices[i*3+1];
        float z = barrel2.vertices[i*3+2];
        float newY = -z;
        float newZ = y;
        
        mesh.vertices[idx*3+0] = barrel2.vertices[i*3+0] + 0.15f; // Right offset
        mesh.vertices[idx*3+1] = newY;
        mesh.vertices[idx*3+2] = newZ + 0.3f;
        
        float ny = barrel2.normals[i*3+1];
        float nz = barrel2.normals[i*3+2];
        mesh.normals[idx*3+0] = barrel2.normals[i*3+0];
        mesh.normals[idx*3+1] = -nz;
        mesh.normals[idx*3+2] = ny;
        
        mesh.colors[idx*4+0]=220; mesh.colors[idx*4+1]=20; mesh.colors[idx*4+2]=20; mesh.colors[idx*4+3]=255; // Red
        idx++;
    }
    
    // Add Power Unit
    for(int i=0; i<v4; i++) {
        mesh.vertices[idx*3+0] = powerUnit.vertices[i*3+0];
        mesh.vertices[idx*3+1] = powerUnit.vertices[i*3+1];
        mesh.vertices[idx*3+2] = powerUnit.vertices[i*3+2] - 0.2f;
        mesh.normals[idx*3+0] = powerUnit.normals[i*3+0];
        mesh.normals[idx*3+1] = powerUnit.normals[i*3+1];
        mesh.normals[idx*3+2] = powerUnit.normals[i*3+2];
        mesh.colors[idx*4+0]=50; mesh.colors[idx*4+1]=100; mesh.colors[idx*4+2]=255; mesh.colors[idx*4+3]=255; // Blue
        idx++;
    }
    
    UnloadMesh(housing);
    UnloadMesh(barrel1);
    UnloadMesh(barrel2);
    UnloadMesh(powerUnit);
    UploadMesh(&mesh, false);
    return mesh;
}

Mesh CreateCollectorMesh() {
    // Collector: Industrial Scoop/Hopper
    Mesh mesh = {0};
    
    // Main Hopper (Inverted Pyramid style, approximated with 5 cubes)
    Mesh cube = GenMeshCube(0.3f, 0.3f, 0.3f);
    
    // 5 cubes: Bottom center, 4 surrounding top
    int totalVerts = cube.vertexCount * 5;
    
    mesh.vertexCount = totalVerts;
    mesh.triangleCount = cube.triangleCount * 5;
    mesh.vertices = (float*)MemAlloc(totalVerts * 3 * sizeof(float));
    mesh.normals = (float*)MemAlloc(totalVerts * 3 * sizeof(float));
    mesh.colors = (unsigned char*)MemAlloc(totalVerts * 4);
    
    int idx = 0;
    
    Vector3 offsets[5] = {
        {0, -0.3f, 0},      // Bottom Center
        {-0.35f, 0.1f, -0.35f}, // Top corners...
        {0.35f, 0.1f, -0.35f},
        {-0.35f, 0.1f, 0.35f},
        {0.35f, 0.1f, 0.35f}
    };
    
    Color cols[5] = {
        {50, 50, 50, 255},      // Dark Grey Bottom
        {0, 200, 0, 255},       // Green Tops
        {0, 200, 0, 255},
        {0, 200, 0, 255},
        {0, 200, 0, 255}
    };
    
    for(int k=0; k<5; k++) {
        for(int i=0; i<cube.vertexCount; i++) {
            mesh.vertices[idx*3+0] = cube.vertices[i*3+0] + offsets[k].x;
            mesh.vertices[idx*3+1] = cube.vertices[i*3+1] + offsets[k].y;
            mesh.vertices[idx*3+2] = cube.vertices[i*3+2] + offsets[k].z;
            
            mesh.normals[idx*3+0] = cube.normals[i*3+0];
            mesh.normals[idx*3+1] = cube.normals[i*3+1];
            mesh.normals[idx*3+2] = cube.normals[i*3+2];
            
            mesh.colors[idx*4+0] = cols[k].r;
            mesh.colors[idx*4+1] = cols[k].g;
            mesh.colors[idx*4+2] = cols[k].b;
            mesh.colors[idx*4+3] = 255;
            idx++;
        }
    }
    
    UnloadMesh(cube);
    UploadMesh(&mesh, false);
    return mesh;
}

Mesh CreateThrusterMesh() {
    // Thruster: Engine Nozzle + Blue Flame
    Mesh mesh = {0};
    
    // Main Engine Body (Grey Cylinder)
    Mesh body = GenMeshCylinder(0.25f, 0.5f, 16);
    // Nozzle Cone (Blue-ish) - Use cylinder with different top/bottom radius if possible, but GenMeshCylinder is uniform.
    // We'll use a larger cylinder at the bottom.
    Mesh nozzle = GenMeshCylinder(0.35f, 0.2f, 16);
    // Flame (Inverted Cone/Pyramid) - Use thin cylinder or just a cube for "plasma" look
    Mesh flame = GenMeshCube(0.2f, 0.6f, 0.2f); // Long flame
    
    int totalVerts = body.vertexCount + nozzle.vertexCount + flame.vertexCount;
    mesh.vertexCount = totalVerts;
    mesh.triangleCount = body.triangleCount + nozzle.triangleCount + flame.triangleCount;
    mesh.vertices = (float*)MemAlloc(totalVerts * 3 * sizeof(float));
    mesh.normals = (float*)MemAlloc(totalVerts * 3 * sizeof(float));
    mesh.colors = (unsigned char*)MemAlloc(totalVerts * 4);
    
    int idx = 0;
    
    // Body
    for(int i=0; i<body.vertexCount; i++) {
        mesh.vertices[idx*3+0] = body.vertices[i*3+0];
        mesh.vertices[idx*3+1] = body.vertices[i*3+1] + 0.2f; // Shift up
        mesh.vertices[idx*3+2] = body.vertices[i*3+2];
        mesh.normals[idx*3+0] = body.normals[i*3+0];
        mesh.normals[idx*3+1] = body.normals[i*3+1];
        mesh.normals[idx*3+2] = body.normals[i*3+2];
        mesh.colors[idx*4+0] = 100; mesh.colors[idx*4+1] = 100; mesh.colors[idx*4+2] = 100; mesh.colors[idx*4+3] = 255;
        idx++;
    }
    
    // Nozzle
    for(int i=0; i<nozzle.vertexCount; i++) {
        mesh.vertices[idx*3+0] = nozzle.vertices[i*3+0];
        mesh.vertices[idx*3+1] = nozzle.vertices[i*3+1] - 0.2f; // Shift down
        mesh.vertices[idx*3+2] = nozzle.vertices[i*3+2];
        mesh.normals[idx*3+0] = nozzle.normals[i*3+0];
        mesh.normals[idx*3+1] = nozzle.normals[i*3+1];
        mesh.normals[idx*3+2] = nozzle.normals[i*3+2];
        mesh.colors[idx*4+0] = 50; mesh.colors[idx*4+1] = 50; mesh.colors[idx*4+2] = 80; mesh.colors[idx*4+3] = 255;
        idx++;
    }
    
    // Flame
    for(int i=0; i<flame.vertexCount; i++) {
        mesh.vertices[idx*3+0] = flame.vertices[i*3+0];
        mesh.vertices[idx*3+1] = flame.vertices[i*3+1] - 0.5f; // Below nozzle
        mesh.vertices[idx*3+2] = flame.vertices[i*3+2];
        mesh.normals[idx*3+0] = flame.normals[i*3+0];
        mesh.normals[idx*3+1] = flame.normals[i*3+1];
        mesh.normals[idx*3+2] = flame.normals[i*3+2];
        mesh.colors[idx*4+0] = 0; mesh.colors[idx*4+1] = 255; mesh.colors[idx*4+2] = 255; mesh.colors[idx*4+3] = 255; // Cyan
        idx++;
    }
    
    UnloadMesh(body);
    UnloadMesh(nozzle);
    UnloadMesh(flame);
    UploadMesh(&mesh, false);
    return mesh;
}

Mesh CreateExoPlatingMesh() {
    // Exo-Plating: Hexagonal Shield Plate
    // Use a 6-sided cylinder (hexagon)
    // Radius 0.5f -> Diameter 1.0f (Tall when standing up)
    Mesh mesh = GenMeshCylinder(0.5f, 0.15f, 6); 
    
    if (!mesh.colors) mesh.colors = (unsigned char*)MemAlloc(mesh.vertexCount * 4);
    
    // Rotate 90 degrees around X to stand it up, then rotate 15 degrees around Z
    Matrix rotX = MatrixRotateX(90.0f * DEG2RAD); // Stand upright
    Matrix rotZ = MatrixRotateZ(15.0f * DEG2RAD); // Tilt slightly
    Matrix rot = MatrixMultiply(rotX, rotZ);
    
    for(int i=0; i<mesh.vertexCount; i++) {
        // Gold/Yellow color
        mesh.colors[i*4+0] = 255;
        mesh.colors[i*4+1] = 215;
        mesh.colors[i*4+2] = 0;
        mesh.colors[i*4+3] = 255;
        
        Vector3 v = {mesh.vertices[i*3+0], mesh.vertices[i*3+1], mesh.vertices[i*3+2]};
        Vector3 vRot = Vector3Transform(v, rot);
        mesh.vertices[i*3+0] = vRot.x;
        mesh.vertices[i*3+1] = vRot.y;
        mesh.vertices[i*3+2] = vRot.z;
        
        // Rotate normals too
        Vector3 n = {mesh.normals[i*3+0], mesh.normals[i*3+1], mesh.normals[i*3+2]};
        Vector3 nRot = Vector3Transform(n, rot);
        mesh.normals[i*3+0] = nRot.x;
        mesh.normals[i*3+1] = nRot.y;
        mesh.normals[i*3+2] = nRot.z;
    }
    
    UploadMesh(&mesh, false);
    return mesh;
}

Mesh CreateFuelMesh() {
    // Fuel: Cluster of 3 drums (Pyramid)
    Mesh mesh = {0};
    Mesh drum = GenMeshCylinder(0.2f, 0.6f, 16);
    
    int totalVerts = drum.vertexCount * 3;
    
    mesh.vertexCount = totalVerts;
    mesh.triangleCount = drum.triangleCount * 3;
    mesh.vertices = (float*)MemAlloc(totalVerts * 3 * sizeof(float));
    mesh.normals = (float*)MemAlloc(totalVerts * 3 * sizeof(float));
    mesh.colors = (unsigned char*)MemAlloc(totalVerts * 4);
    
    int idx = 0;
    Vector3 offsets[3] = {
        {-0.21f, -0.2f, 0}, // Bottom Left
        {0.21f, -0.2f, 0},  // Bottom Right
        {0, 0.25f, 0}       // Top Center
    };
    
    for(int k=0; k<3; k++) {
        for(int i=0; i<drum.vertexCount; i++) {
            mesh.vertices[idx*3+0] = drum.vertices[i*3+0] + offsets[k].x;
            mesh.vertices[idx*3+1] = drum.vertices[i*3+1] + offsets[k].y;
            mesh.vertices[idx*3+2] = drum.vertices[i*3+2] + offsets[k].z;
            
            mesh.normals[idx*3+0] = drum.normals[i*3+0];
            mesh.normals[idx*3+1] = drum.normals[i*3+1];
            mesh.normals[idx*3+2] = drum.normals[i*3+2];
            
            // Orange body, dark caps? Vertices are sorted by cap usually in raylib? 
            // Simplified: All orange
            mesh.colors[idx*4+0] = 255;
            mesh.colors[idx*4+1] = 140;
            mesh.colors[idx*4+2] = 0;
            mesh.colors[idx*4+3] = 255;
            idx++;
        }
    }
    
    UnloadMesh(drum);
    UploadMesh(&mesh, false);
    return mesh;
}

// Create colored ship mesh (red, green, purple, or gold)
Mesh CreateColoredShipMesh(int colorType) {  // 0=red, 1=green, 2=purple, 3=gold
    Vector3 nose={0,0,1.0f}, tail={0,0,-1.0f}, left={-0.8f,0,-0.5f}, right={0.8f,0,-0.5f}, top={0,0.3f,-0.2f}, bottom={0,-0.3f,-0.2f};
    Vector3 tris[8][3]={{top,left,nose},{top,nose,right},{top,tail,left},{top,right,tail},{bottom,nose,left},{bottom,right,nose},{bottom,left,tail},{bottom,tail,right}};
    
    // Color palettes for different ship colors
    Color col[8];
    if (colorType == 0) {  // Red ship
        Color redPalette[8] = {{255,50,50,255},{220,30,30,255},{200,20,20,255},{180,10,10,255},{160,5,5,255},{140,0,0,255},{120,0,0,255},{100,0,0,255}};
        for(int i=0;i<8;i++) col[i]=redPalette[i];
    } else if (colorType == 1) {  // Green ship
        Color greenPalette[8] = {{50,255,50,255},{30,220,30,255},{20,200,20,255},{10,180,10,255},{5,160,5,255},{0,140,0,255},{0,120,0,255},{0,100,0,255}};
        for(int i=0;i<8;i++) col[i]=greenPalette[i];
    } else if (colorType == 2) {  // Purple ship
        Color purplePalette[8] = {{200,50,255,255},{180,30,220,255},{160,20,200,255},{140,10,180,255},{120,5,160,255},{100,0,140,255},{80,0,120,255},{60,0,100,255}};
        for(int i=0;i<8;i++) col[i]=purplePalette[i];
    } else {  // Gold ship (colorType == 3)
        Color goldPalette[8] = {{255,215,0,255},{255,200,0,255},{255,185,0,255},{255,170,0,255},{255,155,0,255},{255,140,0,255},{255,125,0,255},{255,110,0,255}};
        for(int i=0;i<8;i++) col[i]=goldPalette[i];
    }
    
    Mesh mesh={0}; mesh.triangleCount=8; mesh.vertexCount=24;
    mesh.vertices=(float*)MemAlloc(mesh.vertexCount*3*sizeof(float));
    mesh.normals=(float*)MemAlloc(mesh.vertexCount*3*sizeof(float));
    mesh.colors=(unsigned char*)MemAlloc(mesh.vertexCount*4);
    int idx=0;
    for(int t=0;t<8;t++){
        Vector3 n=Vector3Normalize(Vector3CrossProduct(Vector3Subtract(tris[t][1],tris[t][0]), Vector3Subtract(tris[t][2],tris[t][0])));
        for(int k=0;k<3;k++){
            mesh.vertices[idx*3+0]=tris[t][k].x; mesh.vertices[idx*3+1]=tris[t][k].y; mesh.vertices[idx*3+2]=tris[t][k].z;
            mesh.normals[idx*3+0]=n.x; mesh.normals[idx*3+1]=n.y; mesh.normals[idx*3+2]=n.z;
            mesh.colors[idx*4+0]=col[t].r; mesh.colors[idx*4+1]=col[t].g; mesh.colors[idx*4+2]=col[t].b; mesh.colors[idx*4+3]=col[t].a;
            idx++;
        }
    }
    UploadMesh(&mesh,false); return mesh;
}

// Create Fuel Tank Upgrade mesh (larger fuel tank)
Mesh CreateFuelTankUpgradeMesh() {
    // Similar to fuel mesh but larger
    Mesh mesh = CreateFuelMesh();
    // Scale it up slightly
    for(int i=0; i<mesh.vertexCount*3; i++) {
        mesh.vertices[i] *= 1.3f;
    }
    UploadMesh(&mesh,false);
    return mesh;
}

// Create Cargo Black Hole mesh (dark sphere with glow effect)
Mesh CreateCargoBlackHoleMesh() {
    // Create a dark sphere-like mesh
    Mesh mesh = {0};
    mesh.triangleCount = 32;
    mesh.vertexCount = mesh.triangleCount * 3;
    mesh.vertices = (float*)MemAlloc(mesh.vertexCount * 3 * sizeof(float));
    mesh.normals = (float*)MemAlloc(mesh.vertexCount * 3 * sizeof(float));
    mesh.colors = (unsigned char*)MemAlloc(mesh.vertexCount * 4);
    
    float radius = 0.6f;
    int idx = 0;
    for(int i=0; i<16; i++) {
        float theta1 = (float)i * 2.0f * PI / 16.0f;
        float theta2 = (float)(i+1) * 2.0f * PI / 16.0f;
        for(int j=0; j<2; j++) {
            float phi1 = (float)j * PI / 2.0f - PI/4.0f;
            float phi2 = (float)(j+1) * PI / 2.0f - PI/4.0f;
            
            Vector3 v1 = {radius*cos(phi1)*cos(theta1), radius*sin(phi1), radius*cos(phi1)*sin(theta1)};
            Vector3 v2 = {radius*cos(phi1)*cos(theta2), radius*sin(phi1), radius*cos(phi1)*sin(theta2)};
            Vector3 v3 = {radius*cos(phi2)*cos(theta1), radius*sin(phi2), radius*cos(phi2)*sin(theta1)};
            
            Vector3 n = Vector3Normalize(Vector3CrossProduct(Vector3Subtract(v2, v1), Vector3Subtract(v3, v1)));
            Color c = {10, 5, 20, 255};  // Dark purple/black
            
            for(int k=0; k<3; k++) {
                Vector3 v = (k==0) ? v1 : (k==1) ? v2 : v3;
                mesh.vertices[idx*3+0] = v.x; mesh.vertices[idx*3+1] = v.y; mesh.vertices[idx*3+2] = v.z;
                mesh.normals[idx*3+0] = n.x; mesh.normals[idx*3+1] = n.y; mesh.normals[idx*3+2] = n.z;
                mesh.colors[idx*4+0] = c.r; mesh.colors[idx*4+1] = c.g; mesh.colors[idx*4+2] = c.b; mesh.colors[idx*4+3] = c.a;
                idx++;
            }
        }
    }
    UploadMesh(&mesh,false);
    return mesh;
}

Mesh CreateRepairsMesh() {
    // Repairs: Double Gear (Large + Small) - Increased size by 100% (Double size)
    // GenMeshTorus(radius, size, radSeg, sides)
    Mesh gear1 = GenMeshTorus(0.8f, 0.24f, 16, 12); // Large gear (2x previous 0.4, 0.12)
    Mesh gear2 = GenMeshTorus(0.5f, 0.2f, 16, 8); // Small gear on top (2x previous 0.25, 0.1)
    
    Mesh mesh = {0};
    mesh.vertexCount = gear1.vertexCount + gear2.vertexCount;
    mesh.triangleCount = gear1.triangleCount + gear2.triangleCount;
    mesh.vertices = (float*)MemAlloc(mesh.vertexCount * 3 * sizeof(float));
    mesh.normals = (float*)MemAlloc(mesh.vertexCount * 3 * sizeof(float));
    mesh.colors = (unsigned char*)MemAlloc(mesh.vertexCount * 4);
    
    int idx = 0;
    
    // Large Gear
    for(int i=0; i<gear1.vertexCount; i++) {
        mesh.vertices[idx*3+0] = gear1.vertices[i*3+0];
        mesh.vertices[idx*3+1] = gear1.vertices[i*3+1];
        mesh.vertices[idx*3+2] = gear1.vertices[i*3+2];
        mesh.normals[idx*3+0] = gear1.normals[i*3+0];
        mesh.normals[idx*3+1] = gear1.normals[i*3+1];
        mesh.normals[idx*3+2] = gear1.normals[i*3+2];
        mesh.colors[idx*4+0] = 150; mesh.colors[idx*4+1] = 150; mesh.colors[idx*4+2] = 150; mesh.colors[idx*4+3] = 255;
        idx++;
    }
    
    // Small Gear
    for(int i=0; i<gear2.vertexCount; i++) {
        mesh.vertices[idx*3+0] = gear2.vertices[i*3+0] + 0.3f; // Offset X (2x previous 0.15)
        mesh.vertices[idx*3+1] = gear2.vertices[i*3+1];
        mesh.vertices[idx*3+2] = gear2.vertices[i*3+2] + 0.3f; // Offset Z (2x previous 0.15)
        mesh.normals[idx*3+0] = gear2.normals[i*3+0];
        mesh.normals[idx*3+1] = gear2.normals[i*3+1];
        mesh.normals[idx*3+2] = gear2.normals[i*3+2];
        mesh.colors[idx*4+0] = 200; mesh.colors[idx*4+1] = 200; mesh.colors[idx*4+2] = 200; mesh.colors[idx*4+3] = 255;
        idx++;
    }
    
    UnloadMesh(gear1);
    UnloadMesh(gear2);
    UploadMesh(&mesh, false);
    return mesh;
}

void GenerateRocksAndCollision() {
    // Set random seed based on current time to ensure unique environment each time
    // This ensures every asteroid launch has a different 3D environment
    unsigned int seed = (unsigned int)(GetTime() * 1000.0);  // Use milliseconds for seed
    SetRandomSeed(seed);
    printf("[GenerateRocksAndCollision] Generated new environment with seed %u\n", seed);
    
    float phi = 1.61803398875f; float inv = 1.0f/phi;
    Vector3 vLocal[20] = {{1,1,1},{1,1,-1},{1,-1,1},{1,-1,-1},{-1,1,1},{-1,1,-1},{-1,-1,1},{-1,-1,-1},{0,inv,phi},{0,inv,-phi},{0,-inv,phi},{0,-inv,-phi},{inv,phi,0},{inv,-phi,0},{-inv,phi,0},{-inv,-phi,0},{phi,0,inv},{phi,0,-inv},{-phi,0,inv},{-phi,0,-inv}};
    int faces[12][5] = {{0,16,2,10,8},{0,8,4,14,12},{16,17,1,12,0},{1,9,11,3,17},{1,12,14,5,9},{2,13,15,6,10},{13,3,11,7,15},{4,8,10,6,18},{14,4,18,19,5},{5,19,7,11,9},{15,7,19,18,6},{2,16,17,3,13}};
    int globalTriIdx = 0;
    int limit = (int)PROSPECT_PERIMETER;
    Vector3 clusterCenter = {0};

    for (int r = 0; r < NUM_ROCKS; r++) {
        float scale = (float)GetRandomValue(50, 300) / 100.0f;
        float rx, rz;
        if (r % 2 == 0) { rx = (float)GetRandomValue(-limit, limit); rz = (float)GetRandomValue(-limit, limit); clusterCenter = (Vector3){rx, 0, rz}; } 
        else { float angle = (float)GetRandomValue(0, 360) * DEG2RAD; float dist = (float)GetRandomValue(20, 60) / 10.0f; rx = clusterCenter.x + cosf(angle) * dist; rz = clusterCenter.z + sinf(angle) * dist; if(rx > limit) rx = limit; if(rx < -limit) rx = -limit; if(rz > limit) rz = limit; if(rz < -limit) rz = -limit; }
        
        G_Rocks[r].position = (Vector3){rx, GetTerrainHeight(rx, rz) + (0.2f * scale), rz};
        G_Rocks[r].scale = scale;
        G_Rocks[r].axis = Vector3Normalize((Vector3){(float)GetRandomValue(-1,1),(float)GetRandomValue(-1,1),(float)GetRandomValue(-1,1)});
        G_Rocks[r].angle = (float)GetRandomValue(0, 360);
        int tintVal = GetRandomValue(200, 255);
        G_Rocks[r].color = (Color){(unsigned char)tintVal, (unsigned char)tintVal, (unsigned char)tintVal, 255};
        G_Rocks[r].active = true;
        G_Rocks[r].prosperityPercentage = g_selectedAsteroidProspect;  // Set prosperity from current asteroid

        Matrix matScale = MatrixScale(scale, scale, scale);
        Matrix matRot = MatrixRotate(G_Rocks[r].axis, G_Rocks[r].angle * DEG2RAD);
        Matrix matTrans = MatrixTranslate(G_Rocks[r].position.x, G_Rocks[r].position.y, G_Rocks[r].position.z);
        Matrix matWorld = MatrixMultiply(MatrixMultiply(matScale, matRot), matTrans);

        for(int f=0;f<12;f++){
            Vector3 pWorld[5]; for(int i=0;i<5;i++) pWorld[i] = Vector3Transform(vLocal[faces[f][i]], matWorld);
            int tris[3][3]={{0,1,2},{0,2,3},{0,3,4}};
            for(int t=0;t<3;t++){
                G_RockTris[globalTriIdx].a = pWorld[tris[t][0]]; G_RockTris[globalTriIdx].b = pWorld[tris[t][1]]; G_RockTris[globalTriIdx].c = pWorld[tris[t][2]]; globalTriIdx++;
            }
        }
    }
}

Mesh CreateTerrainChunk(float startX, float startZ, float size) {
    Mesh mesh = { 0 };
    int range = (int)size;
    
    mesh.triangleCount = range * range * 2;
    mesh.vertexCount = mesh.triangleCount * 3;
    
    mesh.vertices = (float *)MemAlloc(mesh.vertexCount * 3 * sizeof(float));
    mesh.normals = (float *)MemAlloc(mesh.vertexCount * 3 * sizeof(float));
    mesh.colors = (unsigned char *)MemAlloc(mesh.vertexCount * 4 * sizeof(unsigned char));

    int vCounter = 0;
    Color grey1 = {80, 80, 80, 255};
    Color grey2 = {50, 50, 50, 255};

    for (int z = 0; z < range; z++) {
        for (int x = 0; x < range; x++) {
            float xf = startX + (float)x; 
            float zf = startZ + (float)z;

            // Heights
            float y0 = GetTerrainHeight(xf, zf);
            float y1 = GetTerrainHeight(xf, zf + 1);
            float y2 = GetTerrainHeight(xf + 1, zf + 1);
            float y3 = GetTerrainHeight(xf + 1, zf);

            // Vertices
            Vector3 vA = { xf, y0, zf };
            Vector3 vB = { xf, y1, zf + 1 };
            Vector3 vC = { xf + 1, y2, zf + 1 };
            Vector3 vD = { xf + 1, y3, zf };

            // Color Logic
            int wx = (int)xf; int wz = (int)zf;
            Color gc = (abs(wx) % 2 == abs(wz) % 2) ? grey1 : grey2;

            // Tri 1
            mesh.vertices[vCounter*3+0] = vA.x; mesh.vertices[vCounter*3+1] = vA.y; mesh.vertices[vCounter*3+2] = vA.z;
            mesh.normals[vCounter*3+0] = 0.0f; mesh.normals[vCounter*3+1] = 1.0f; mesh.normals[vCounter*3+2] = 0.0f; 
            mesh.colors[vCounter*4+0] = gc.r; mesh.colors[vCounter*4+1] = gc.g; mesh.colors[vCounter*4+2] = gc.b; mesh.colors[vCounter*4+3] = gc.a;
            vCounter++;
            mesh.vertices[vCounter*3+0] = vB.x; mesh.vertices[vCounter*3+1] = vB.y; mesh.vertices[vCounter*3+2] = vB.z;
            mesh.normals[vCounter*3+0] = 0.0f; mesh.normals[vCounter*3+1] = 1.0f; mesh.normals[vCounter*3+2] = 0.0f;
            mesh.colors[vCounter*4+0] = gc.r; mesh.colors[vCounter*4+1] = gc.g; mesh.colors[vCounter*4+2] = gc.b; mesh.colors[vCounter*4+3] = gc.a;
            vCounter++;
            mesh.vertices[vCounter*3+0] = vC.x; mesh.vertices[vCounter*3+1] = vC.y; mesh.vertices[vCounter*3+2] = vC.z;
            mesh.normals[vCounter*3+0] = 0.0f; mesh.normals[vCounter*3+1] = 1.0f; mesh.normals[vCounter*3+2] = 0.0f;
            mesh.colors[vCounter*4+0] = gc.r; mesh.colors[vCounter*4+1] = gc.g; mesh.colors[vCounter*4+2] = gc.b; mesh.colors[vCounter*4+3] = gc.a;
            vCounter++;

            // Tri 2
            mesh.vertices[vCounter*3+0] = vA.x; mesh.vertices[vCounter*3+1] = vA.y; mesh.vertices[vCounter*3+2] = vA.z;
            mesh.normals[vCounter*3+0] = 0.0f; mesh.normals[vCounter*3+1] = 1.0f; mesh.normals[vCounter*3+2] = 0.0f;
            mesh.colors[vCounter*4+0] = gc.r; mesh.colors[vCounter*4+1] = gc.g; mesh.colors[vCounter*4+2] = gc.b; mesh.colors[vCounter*4+3] = gc.a;
            vCounter++;
            mesh.vertices[vCounter*3+0] = vC.x; mesh.vertices[vCounter*3+1] = vC.y; mesh.vertices[vCounter*3+2] = vC.z;
            mesh.normals[vCounter*3+0] = 0.0f; mesh.normals[vCounter*3+1] = 1.0f; mesh.normals[vCounter*3+2] = 0.0f;
            mesh.colors[vCounter*4+0] = gc.r; mesh.colors[vCounter*4+1] = gc.g; mesh.colors[vCounter*4+2] = gc.b; mesh.colors[vCounter*4+3] = gc.a;
            vCounter++;
            mesh.vertices[vCounter*3+0] = vD.x; mesh.vertices[vCounter*3+1] = vD.y; mesh.vertices[vCounter*3+2] = vD.z;
            mesh.normals[vCounter*3+0] = 0.0f; mesh.normals[vCounter*3+1] = 1.0f; mesh.normals[vCounter*3+2] = 0.0f;
            mesh.colors[vCounter*4+0] = gc.r; mesh.colors[vCounter*4+1] = gc.g; mesh.colors[vCounter*4+2] = gc.b; mesh.colors[vCounter*4+3] = gc.a;
            vCounter++;
        }
    }
    UploadMesh(&mesh, false);
    return mesh;
}

void DrawPerimeterBorder(Vector3 shipPos) {
    Color col = {0, 255, 255, 128}; 
    float halfWidth = 1.0f; 
    float step = 2.0f; 
    float limit = PROSPECT_PERIMETER;
    float minRenderX = shipPos.x - RENDER_DISTANCE;
    float maxRenderX = shipPos.x + RENDER_DISTANCE;
    float minRenderZ = shipPos.z - RENDER_DISTANCE;
    float maxRenderZ = shipPos.z + RENDER_DISTANCE;

    rlBegin(RL_QUADS);
    rlColor4ub(col.r, col.g, col.b, col.a);

    float startZ = fmaxf(-limit, minRenderZ);
    float endZ   = fminf(limit, maxRenderZ);
    if (startZ < endZ) {
        if (-limit >= minRenderX && -limit <= maxRenderX) {
            for (float z = startZ; z < endZ; z += step) {
                float zNext = (z + step > endZ) ? endZ : z + step;
                float h1 = GetTerrainHeight(-limit - halfWidth, z);
                float h2 = GetTerrainHeight(-limit + halfWidth, z);
                float h3 = GetTerrainHeight(-limit + halfWidth, zNext);
                float h4 = GetTerrainHeight(-limit - halfWidth, zNext);
                rlVertex3f(-limit - halfWidth, h1 + 0.1f, z);
                rlVertex3f(-limit + halfWidth, h2 + 0.1f, z);
                rlVertex3f(-limit + halfWidth, h3 + 0.1f, zNext);
                rlVertex3f(-limit - halfWidth, h4 + 0.1f, zNext);
            }
        }
        if (limit >= minRenderX && limit <= maxRenderX) {
            for (float z = startZ; z < endZ; z += step) {
                float zNext = (z + step > endZ) ? endZ : z + step;
                float h1 = GetTerrainHeight(limit - halfWidth, z);
                float h2 = GetTerrainHeight(limit + halfWidth, z);
                float h3 = GetTerrainHeight(limit + halfWidth, zNext);
                float h4 = GetTerrainHeight(limit - halfWidth, zNext);
                rlVertex3f(limit - halfWidth, h1 + 0.1f, z);
                rlVertex3f(limit + halfWidth, h2 + 0.1f, z);
                rlVertex3f(limit + halfWidth, h3 + 0.1f, zNext);
                rlVertex3f(limit - halfWidth, h4 + 0.1f, zNext);
            }
        }
    }

    float startX = fmaxf(-limit, minRenderX);
    float endX   = fminf(limit, maxRenderX);
    if (startX < endX) {
        if (-limit >= minRenderZ && -limit <= maxRenderZ) {
            for (float x = startX; x < endX; x += step) {
                float xNext = (x + step > endX) ? endX : x + step;
                float h1 = GetTerrainHeight(x, -limit - halfWidth);
                float h2 = GetTerrainHeight(x, -limit + halfWidth);
                float h3 = GetTerrainHeight(xNext, -limit + halfWidth);
                float h4 = GetTerrainHeight(xNext, -limit - halfWidth);
                rlVertex3f(x, h1 + 0.1f, -limit - halfWidth);
                rlVertex3f(x, h2 + 0.1f, -limit + halfWidth);
                rlVertex3f(xNext, h3 + 0.1f, -limit + halfWidth);
                rlVertex3f(xNext, h4 + 0.1f, -limit - halfWidth);
            }
        }
        if (limit >= minRenderZ && limit <= maxRenderZ) {
            for (float x = startX; x < endX; x += step) {
                float xNext = (x + step > endX) ? endX : x + step;
                float h1 = GetTerrainHeight(x, limit - halfWidth);
                float h2 = GetTerrainHeight(x, limit + halfWidth);
                float h3 = GetTerrainHeight(xNext, limit + halfWidth);
                float h4 = GetTerrainHeight(xNext, limit - halfWidth);
                rlVertex3f(x, h1 + 0.1f, limit - halfWidth);
                rlVertex3f(x, h2 + 0.1f, limit + halfWidth);
                rlVertex3f(xNext, h3 + 0.1f, limit + halfWidth);
                rlVertex3f(xNext, h4 + 0.1f, limit - halfWidth);
            }
        }
    }
    rlEnd();
}

void DrawProjectedShadow(Vector3 shipPos) {
    float groundY = GetWorldHeight(shipPos.x, shipPos.z);
    float altitude = shipPos.y - groundY;
    if (altitude < 0) altitude = 0;
    float radius = 0.6f + (altitude * 0.075f);
    if (radius > 2.5f) radius = 2.5f;
    float heightFactor = Clamp(altitude / 12.0f, 0.0f, 1.0f);
    unsigned char alpha = (unsigned char)Lerp(220, 60, heightFactor);
    unsigned char greyVal = (unsigned char)Lerp(0, 80, heightFactor);
    Color shadowCol = (Color){greyVal, greyVal, greyVal, alpha}; 
    float step = 0.5f; 
    rlBegin(RL_QUADS);
    rlColor4ub(shadowCol.r, shadowCol.g, shadowCol.b, shadowCol.a);
    float startX = shipPos.x - radius; float endX = shipPos.x + radius;
    float startZ = shipPos.z - radius; float endZ = shipPos.z + radius;
    for (float x = startX; x < endX; x += step) {
        for (float z = startZ; z < endZ; z += step) {
            float dx = x - shipPos.x; float dz = z - shipPos.z;
            if ((dx*dx + dz*dz) > (radius*radius)) continue;
            float lift = 0.15f; // Increased lift to prevent shadow collision with ship
            float y0 = GetWorldHeight(x, z) + lift;
            float y1 = GetWorldHeight(x, z + step) + lift;
            float y2 = GetWorldHeight(x + step, z + step) + lift;
            float y3 = GetWorldHeight(x + step, z) + lift;
            rlVertex3f(x, y0, z);
            rlVertex3f(x, y1, z + step);
            rlVertex3f(x + step, y2, z + step);
            rlVertex3f(x + step, y3, z);
        }
    }
    rlEnd();
}

Color thrusterPalette[10] = { WHITE, WHITE, RAYWHITE, (Color){0, 255, 255, 255}, (Color){100, 255, 255, 255}, SKYBLUE, WHITE, ORANGE, RED, GOLD };

void SpawnThrustParticles(Vector3 nozzlePos, Vector3 shipUpVector) {
    // Particles spray outwards immediately in a wide cone towards the surface
    // Eject opposite to ship's thrust direction (downward towards surface)
    Vector3 ejectDir = Vector3Normalize(shipUpVector);
    ejectDir = Vector3Scale(ejectDir, -1.0f); // Eject opposite to thrust direction (downward)
    
    int particlesPerFrame = 4;
    for (int k = 0; k < particlesPerFrame; k++) {
        for (int i = 0; i < MAX_PARTICLES; i++) {
            if (particles[i].life <= 0) {
                // Spawn particles lower and push them away from ship center immediately
                Vector3 offsetFromShip = Vector3Subtract(nozzlePos, g_shipPos);
                float distFromShip = Vector3Length(offsetFromShip);
                // Push spawn position further away if too close to ship center (at least 0.9 units)
                if (distFromShip < 0.9f) {
                    Vector3 pushDir = Vector3Normalize(offsetFromShip);
                    if (Vector3Length(pushDir) < 0.1f) pushDir = ejectDir; // Fallback if offset is zero
                    nozzlePos = Vector3Add(g_shipPos, Vector3Scale(pushDir, 0.9f));
                }
                
                particles[i].pos = nozzlePos; particles[i].onGround = false;
                
                // Create cone spray: particles spread out in a narrower cone
                // Reduced noise range and scale for tighter cone (50% narrower than previous)
                Vector3 noise = { 
                    (GetRandomValue(-20, 20)) / 100.0f,  // Narrower horizontal spread
                    (GetRandomValue(-8, 8)) / 100.0f,     // Less vertical variation
                    (GetRandomValue(-20, 20)) / 100.0f    // Narrower horizontal spread
                };
                // Reduced scale factor (1.0f) creates narrower cone spread
                Vector3 spreadDir = Vector3Add(ejectDir, Vector3Scale(noise, 1.0f));
                spreadDir = Vector3Normalize(spreadDir);
                
                // Strong velocity: particles spray out immediately with high speed
                float ejectSpeed = (float)GetRandomValue(200, 400) / 10.0f; // 20-40 units/sec (much stronger)
                Vector3 ejectVel = Vector3Scale(spreadDir, ejectSpeed);
                particles[i].vel = Vector3Add(g_shipVel, ejectVel);
                
                particles[i].color = thrusterPalette[GetRandomValue(0,9)];
                particles[i].life = 1.5f; break;
            }
        }
    }
}

// Spawn bright teal collision particles from ship
void SpawnCollisionParticles(Vector3 collisionPos, Vector3 collisionNormal) {
    Color brightTeal = (Color){0, 255, 255, 255};  // Bright teal
    int particlesToSpawn = 15;
    for (int k = 0; k < particlesToSpawn; k++) {
        for (int i = 0; i < MAX_PARTICLES; i++) {
            if (particles[i].life <= 0) {
                particles[i].pos = collisionPos;
                particles[i].onGround = false;
                Vector3 noise = { (GetRandomValue(-100,100))/100.0f, (GetRandomValue(-100,100))/100.0f, (GetRandomValue(-100,100))/100.0f };
                Vector3 spreadDir = Vector3Add(collisionNormal, Vector3Scale(noise, 0.8f));
                spreadDir = Vector3Normalize(spreadDir);
                particles[i].vel = Vector3Scale(spreadDir, (float)GetRandomValue(50, 200) / 10.0f);
                particles[i].color = brightTeal;
                particles[i].life = 2.0f;
                break;
            }
        }
    }
}

// Spawn grey debris from asteroid
void SpawnAsteroidDebris(Vector3 debrisPos) {
    Color greyDebris = (Color){128, 128, 128, 255};  // Grey (unchanged - this is asteroid debris, not collection)
    int particlesToSpawn = 5;  // Not much debris
    for (int k = 0; k < particlesToSpawn; k++) {
        for (int i = 0; i < MAX_PARTICLES; i++) {
            if (particles[i].life <= 0) {
                particles[i].pos = debrisPos;
                particles[i].onGround = false;
                Vector3 randomDir = { (GetRandomValue(-100,100))/100.0f, (GetRandomValue(0,50))/100.0f, (GetRandomValue(-100,100))/100.0f };
                randomDir = Vector3Normalize(randomDir);
                particles[i].vel = Vector3Scale(randomDir, (float)GetRandomValue(30, 80) / 10.0f);
                particles[i].color = greyDebris;
                particles[i].life = 3.0f;
                break;
            }
        }
    }
}

// Spawn explosion particles (blue, light blue, white) - thousands of cubes at high velocity
void SpawnExplosionParticles(Vector3 explosionPos) {
    Color explosionColors[] = {
        (Color){0, 100, 255, 255},      // Blue
        (Color){100, 200, 255, 255},    // Light blue
        (Color){255, 255, 255, 255}     // White
    };
    
    // Spawn thousands of particles (2000-3000 cubes)
    int particlesToSpawn = 2500;
    int spawned = 0;
    
    // Clear all existing particles to make room for explosion
    for (int i = 0; i < MAX_PARTICLES && spawned < particlesToSpawn; i++) {
        particles[i].pos = explosionPos;
        particles[i].onGround = false;
        
        // Random direction in all directions (spherical distribution)
        float theta = (float)GetRandomValue(0, 360) * DEG2RAD;  // Azimuth angle
        float phi = (float)GetRandomValue(0, 180) * DEG2RAD;    // Polar angle
        
        Vector3 randomDir = {
            sinf(phi) * cosf(theta),
            cosf(phi),
            sinf(phi) * sinf(theta)
        };
        randomDir = Vector3Normalize(randomDir);
        
        // High velocity: 50-200 units/sec (much faster than before)
        float velocity = (float)GetRandomValue(500, 2000) / 10.0f;  // 50-200 units/sec
        particles[i].vel = Vector3Scale(randomDir, velocity);
        
        particles[i].color = explosionColors[GetRandomValue(0, 2)];
        particles[i].life = 5.0f;  // Longer life for particles to travel far
        spawned++;
    }
}

void UpdateParticles(float dt) {
    float gravity = -9.0f;
    for (int i = 0; i < MAX_PARTICLES; i++) {
        if (particles[i].life > 0) {
            particles[i].life -= dt;
            if (particles[i].life < 0.5f) {
                float alpha = (particles[i].life / 0.5f);
                particles[i].color.a = (unsigned char)(255 * alpha);
            }
            if (!particles[i].onGround) {
                particles[i].vel.y += gravity * dt;
                Vector3 nextPos = Vector3Add(particles[i].pos, Vector3Scale(particles[i].vel, dt));
                
                // Particles disappear immediately if they touch the ship (not just collide)
                if (Vector3Distance(nextPos, g_shipPos) < 0.7f) {
                     // Kill particle immediately
                     particles[i].life = 0.0f;
                     continue; // Skip to next particle
                }
                
                particles[i].pos = nextPos;
                
                float worldH = GetWorldHeight(particles[i].pos.x, particles[i].pos.z);
                if (particles[i].pos.y <= worldH + 0.05f) {
                    particles[i].pos.y = worldH + 0.05f; particles[i].onGround = true;
                    particles[i].vel.y = 0; particles[i].vel.x *= 0.5f; particles[i].vel.z *= 0.5f;
                }
            } else {
                particles[i].vel.x *= 0.90f; particles[i].vel.z *= 0.90f;
                particles[i].pos = Vector3Add(particles[i].pos, Vector3Scale(particles[i].vel, dt));
            }
        }
    }
}

void DrawParticles() {
    float pSize = 0.0832f; // Increased by 30% from 0.064f 
    for (int i = 0; i < MAX_PARTICLES; i++) {
        if (particles[i].life > 0) {
            DrawCube(particles[i].pos, pSize, pSize, pSize, particles[i].color);
        }
    }
}

// Check if any explosion particles are still active (have life > 0)
bool HasActiveExplosionParticles() {
    // Explosion particles are: Blue (0, 100, 255), Light Blue (100, 200, 255), or White (255, 255, 255)
    for (int i = 0; i < MAX_PARTICLES; i++) {
        if (particles[i].life > 0) {
            Color c = particles[i].color;
            // Check if this is an explosion particle (blue, light blue, or white)
            bool isBlue = (c.r == 0 && c.g == 100 && c.b == 255);
            bool isLightBlue = (c.r == 100 && c.g == 200 && c.b == 255);
            bool isWhite = (c.r == 255 && c.g == 255 && c.b == 255);
            
            if (isBlue || isLightBlue || isWhite) {
                return true;  // Found an active explosion particle
            }
        }
    }
    return false;  // No active explosion particles found
}

// ------------------------------------------------------------
// HELPER: STATE RESET
// ------------------------------------------------------------
void ResetState(GameState* currentState, int* menuSelection, GameState newState) {
    // Calculate final score when transitioning to game over
    if (newState == STATE_GAME_OVER && *currentState != STATE_GAME_OVER) {
        int finalScore = CalculateFinalScore(G_Player.credits, G_Player.rank);
        g_lastFinalScore = finalScore;
        
        // Add to leaderboard
        AddToLeaderboard(finalScore, G_Player.credits, G_Player.rank);
        
        // Reset leaderboard display flags for next game
        g_showLeaderboard = false;
        g_leaderboardDismissed = false;
        
        printf("[ResetState] Game Over! Final Score: %d (Credits: %d × Rank: %d)\n", 
               finalScore, G_Player.credits, G_Player.rank);
    }
    
    // Show leaderboard after returning to splash from game over
    if (newState == STATE_SPLASH && *currentState == STATE_GAME_OVER) {
        g_showLeaderboard = true;
        g_leaderboardDismissed = false;
        printf("[ResetState] Showing leaderboard after game over\n");
    }
    
    g_previousState = *currentState;  // Store previous state for ESC navigation
    *currentState = newState;
    *menuSelection = 0;
    // Reset depot_home page to 1 when entering DEPOT_HOME state
    if (newState == STATE_DEPOT_HOME) {
        g_depotHomePage = 1;
        // Close any open overlays when returning to depot
        g_showProspectAsteroids = false;
        g_showShipyardShop = false;
        g_showBarView = false;
        g_showAsteroidModal = false;
        g_showShopModal = false;
        g_showExitToMainMenuModal = false; // Close exit modal
        // Simulate left arrow key press to exit previous page
        if (KEY_LEFT >= 0 && KEY_LEFT < 512) {
            g_inputState.keysPressed[KEY_LEFT] = true;
        }
    } else if (newState == STATE_STATION_HOME || newState == STATE_HALO_HOME) {
        // Close any open overlays when returning to station or halo
        g_showProspectAsteroids = false;
        g_showShipyardShop = false;
        g_showBarView = false;
        g_showAsteroidModal = false;
        g_showShopModal = false;
        g_showExitToMainMenuModal = false; // Close exit modal
        // Simulate left arrow key press to exit previous page
        if (KEY_LEFT >= 0 && KEY_LEFT < 512) {
            g_inputState.keysPressed[KEY_LEFT] = true;
        }
    } else {
        // Close exit modal when leaving home states
        g_showExitToMainMenuModal = false;
    }
}

// ------------------------------------------------------------
// INPUT WRAPPER FUNCTIONS (use custom input state instead of raylib)
// Must be defined before Draw functions that use them
// ------------------------------------------------------------
static bool CustomIsKeyDown(int key) {
    if (key >= 0 && key < 512) {
        return g_inputState.keys[key];
    }
    return false;
}

static bool CustomIsKeyPressed(int key) {
    if (key >= 0 && key < 512) {
        return g_inputState.keysPressed[key];
    }
    return false;
}

// Helper function to play terminal type sound
static void PlayTerminalTypeSound() {
    if (g_terminalTypeSound.frameCount > 0) {
        PlaySound(g_terminalTypeSound);
    }
}

static bool CustomIsMouseButtonDown(int button) {
    if (button >= 0 && button < 8) {
        return g_inputState.mouseButtons[button];
    }
    return false;
}

static bool CustomIsMouseButtonPressed(int button) {
    if (button >= 0 && button < 8) {
        return g_inputState.mouseButtonsPressed[button];
    }
    return false;
}

static bool CustomIsMouseButtonReleased(int button) {
    if (button >= 0 && button < 8) {
        return g_inputState.mouseButtonsReleased[button];
    }
    return false;
}

static Vector2 CustomGetMouseDelta() {
    return g_inputState.mouseDelta;
}

static Vector2 CustomGetMousePosition() {
    return g_inputState.mousePosition;
}

// ------------------------------------------------------------
// HELPER: ESC NAVIGATION (go back to previous state)
// ------------------------------------------------------------
void HandleESCNavigation(GameState* currentState, int* menuSelection) {
    if (CustomIsKeyPressed(KEY_ESCAPE)) {
        // From splash screen menu, ESC is handled in DrawPageSplash (can quit if QUIT GAME selected)
        // ESC should only take player back to Depot, Station, or Halo, never to navigation or 3D environment
        if (*currentState != STATE_SPLASH) {
            // Always go back to the appropriate home state based on current location
            // Never go back to navigation screen or 3D environment
            if (g_currentLocation == 1) {
                // Currently at Station - go back to Station Home
                ResetState(currentState, menuSelection, STATE_STATION_HOME);
            } else if (g_currentLocation == 2) {
                // Currently at Halo - go back to Halo Home
                ResetState(currentState, menuSelection, STATE_HALO_HOME);
            } else {
                // Currently at Depot (default) - go back to Depot Home
                ResetState(currentState, menuSelection, STATE_DEPOT_HOME);
            }
        }
    }
}

// ------------------------------------------------------------
// INPUT SETTING FUNCTIONS (called from Python)
// ------------------------------------------------------------
// NOTE: These are defined outside extern "C" because they implement forward declarations
// that were inside extern "C". The linker should match them.
// If not, we can wrap them in extern "C" too.

__declspec(dllexport) __cdecl void SetKeyState(int key, bool down) {
    static int key_event_count = 0;
    if (key >= 0 && key < 512) {
        bool wasDown = g_inputState.keys[key];
        g_inputState.keys[key] = down;
        // Set pressed flag if just pressed (wasn't down, now is)
        if (!wasDown && down) {
            g_inputState.keysPressed[key] = true;
            key_event_count++;
        }
    }
}

__declspec(dllexport) __cdecl void SetMouseButtonState(int button, bool down) {
    if (button >= 0 && button < 8) {
        bool wasDown = g_inputState.mouseButtons[button];
        g_inputState.mouseButtons[button] = down;
        // Set pressed/released flags
        if (!wasDown && down) {
            g_inputState.mouseButtonsPressed[button] = true;
        } else if (wasDown && !down) {
            g_inputState.mouseButtonsReleased[button] = true;
        }
    }
}

__declspec(dllexport) __cdecl void SetInputMousePosition(float x, float y) {
    g_inputState.mousePosition = (Vector2){x, y};
}

__declspec(dllexport) __cdecl void SetMouseDelta(float dx, float dy) {
    g_inputState.mouseDelta = (Vector2){dx, dy};
}

__declspec(dllexport) __cdecl void ClearInputFrame() {
    // Clear one-time press/release flags at end of frame
    memset(g_inputState.keysPressed, 0, sizeof(g_inputState.keysPressed));
    memset(g_inputState.mouseButtonsPressed, 0, sizeof(g_inputState.mouseButtonsPressed));
    memset(g_inputState.mouseButtonsReleased, 0, sizeof(g_inputState.mouseButtonsReleased));
}

__declspec(dllexport) __cdecl bool ShouldExit() {
    return g_exit_requested;
}

__declspec(dllexport) __cdecl bool ShouldCenterMouse() {
    // Returns true once when mouse should be centered, then resets flag
    if (g_shouldCenterMouse) {
        g_shouldCenterMouse = false;
        return true;
    }
    return false;
}

__declspec(dllexport) __cdecl int GetLastFinalScore() {
    return g_lastFinalScore;
}

__declspec(dllexport) __cdecl void SetUsername(const char* username) {
    if (username) {
        strncpy(g_currentUsername, username, MAX_USERNAME_LENGTH - 1);
        g_currentUsername[MAX_USERNAME_LENGTH - 1] = '\0';
        printf("[SetUsername] Username set to: %s\n", g_currentUsername);
    }
}

__declspec(dllexport) __cdecl void ResetGame() {
    // Reset all player stats to new game defaults
    ResetPlayerStats();
    
    // Also reset any state that might persist between launches
    g_shouldCenterMouse = false;  // Reset mouse centering flag
    g_previousState = STATE_SPLASH;  // Reset previous state
    g_exit_requested = false;  // Ensure quit flag is cleared before relaunch
    
    printf("[ResetGame] Game reset called from Python - all stats and state reset to new game defaults\n");
}

__declspec(dllexport) __cdecl void CleanupGame() {
    // Stop and unload audio so the next launch starts fresh
    if (IsAudioDeviceReady()) {
        StopMusicStream(g_backgroundMusic);
        StopMusicStream(g_backgroundMusic2);
        StopMusicStream(g_splashMusic);
        if (g_backgroundMusic.stream.buffer) { UnloadMusicStream(g_backgroundMusic); g_backgroundMusic = (Music){0}; }
        if (g_backgroundMusic2.stream.buffer) { UnloadMusicStream(g_backgroundMusic2); g_backgroundMusic2 = (Music){0}; }
        if (g_splashMusic.stream.buffer) { UnloadMusicStream(g_splashMusic); g_splashMusic = (Music){0}; }
        if (g_terminalTypeSound.frameCount > 0) { StopSound(g_terminalTypeSound); UnloadSound(g_terminalTypeSound); g_terminalTypeSound = (Sound){0}; }
        if (g_laserSound.frameCount > 0) { StopSound(g_laserSound); UnloadSound(g_laserSound); g_laserSound = (Sound){0}; }
        if (g_thrusterSound.frameCount > 0) { StopSound(g_thrusterSound); UnloadSound(g_thrusterSound); g_thrusterSound = (Sound){0}; }
        if (g_saleSound.frameCount > 0) { StopSound(g_saleSound); UnloadSound(g_saleSound); g_saleSound = (Sound){0}; }
        if (g_fuelSound.frameCount > 0) { StopSound(g_fuelSound); UnloadSound(g_fuelSound); g_fuelSound = (Sound){0}; }
        if (g_noSound.frameCount > 0) { StopSound(g_noSound); UnloadSound(g_noSound); g_noSound = (Sound){0}; }
        if (g_crashSound.frameCount > 0) { StopSound(g_crashSound); UnloadSound(g_crashSound); g_crashSound = (Sound){0}; }
        if (g_explodeSound.frameCount > 0) { StopSound(g_explodeSound); UnloadSound(g_explodeSound); g_explodeSound = (Sound){0}; }
        if (g_enteringStationSound.frameCount > 0) { StopSound(g_enteringStationSound); UnloadSound(g_enteringStationSound); g_enteringStationSound = (Sound){0}; }
        if (g_beamUpSound.frameCount > 0) { StopSound(g_beamUpSound); UnloadSound(g_beamUpSound); g_beamUpSound = (Sound){0}; }
        if (g_launchSequenceSound.frameCount > 0) { StopSound(g_launchSequenceSound); UnloadSound(g_launchSequenceSound); g_launchSequenceSound = (Sound){0}; }
        if (g_collectSound.frameCount > 0) { StopSound(g_collectSound); UnloadSound(g_collectSound); g_collectSound = (Sound){0}; }
        if (g_rockSound.frameCount > 0) { StopSound(g_rockSound); UnloadSound(g_rockSound); g_rockSound = (Sound){0}; }
        if (g_fixingOnSound.frameCount > 0) { StopSound(g_fixingOnSound); UnloadSound(g_fixingOnSound); g_fixingOnSound = (Sound){0}; }
        if (g_barSound.frameCount > 0) { StopSound(g_barSound); UnloadSound(g_barSound); g_barSound = (Sound){0}; }
        if (g_levelupSound.frameCount > 0) { StopSound(g_levelupSound); UnloadSound(g_levelupSound); g_levelupSound = (Sound){0}; }
        CloseAudioDevice();
    }

    // Release framebuffer resources
    if (g_framebuffer_initialized && g_framebuffer.texture.id != 0) {
        UnloadRenderTexture(g_framebuffer);
        g_framebuffer = (RenderTexture2D){0};
        g_framebuffer_initialized = false;
    }
    if (g_frame_buffer_data) {
        MemFree(g_frame_buffer_data);
        g_frame_buffer_data = NULL;
        g_frame_buffer_size = 0;
    }

    // Close window so the next launch can recreate cleanly
    if (IsWindowReady()) {
        CloseWindow();
    }

    // Reset persistent flags so a relaunch starts from a clean slate
    g_exit_requested = false;
    g_game_initialized = false;
    g_shouldCenterMouse = false;
    g_previousState = STATE_SPLASH;
}

// ------------------------------------------------------------
// DRAWING HELPERS (Shared UI)
// ------------------------------------------------------------

// Forward declarations
void DrawTextWithFont(const char* text, int posX, int posY, int fontSize, Color color);
int MeasureTextWithFont(const char* text, int fontSize);
void DrawWordWrappedText(const char* text, int x, int y, int maxWidth, int fontSize, Color color, int* outY);

// Universal modal button positioning rule: ensures buttons are always fixed 25px from bottom edge
// This provides consistent button placement across all modals
// Parameters:
//   modalY: The top Y position of the modal window
//   modalHeight: The height of the modal window
//   buttonHeight: Height of the button(s) to be positioned
// Returns: The Y position where buttons should be placed
inline int CalculateModalButtonY(int modalY, int modalHeight, int buttonHeight) {
    // Universal rule: buttons are positioned 25px from the bottom edge of the modal
    return modalY + modalHeight - buttonHeight - 25;
}

// Calculate required modal height to accommodate text and buttons without overlap
// Parameters:
//   textBottomY: The bottom Y position of the text content (relative to modal top)
//   buttonHeight: Height of the button(s)
//   topPadding: Padding at top of modal (default: 50px) - NOT used in calculation as textBottomY includes it
// Returns: Minimum required modal height
inline int CalculateRequiredModalHeight(int textBottomY, int buttonHeight, int topPadding = 50) {
    // Calculate total height needed: text + 25px spacing + buttons + 25px bottom margin
    // Note: textBottomY already includes the top padding
    return textBottomY + 25 + buttonHeight + 25;
}

void DrawRetroWindow(const char* title, int x, int y, int w, int h, int titleFontSize = 12) {
    Color panelFill = {10, 15, 30, 240};
    Color border = {0, 255, 255, 255};
    DrawRectangle(x, y, w, h, panelFill);
    DrawRectangleLines(x, y, w, h, border);
    DrawRectangle(x, y, w, 30, border);
    DrawTextWithFont(title, x + 10, y + 5, titleFontSize, BLACK);
}

// KEYBOARD NAVIGATION BUTTON
bool DrawButton(const char* text, int x, int y, int w, int h, bool selected, int fontSize = 12) {
    Color fill = selected ? (Color){0, 100, 100, 255} : (Color){0, 40, 40, 255};
    Color border = selected ? WHITE : (Color){0, 255, 255, 255};
    
    DrawRectangle(x, y, w, h, fill);
    DrawRectangleLines(x, y, w, h, border);
    
    if (retroFont.texture.id > 0) {
        Vector2 textSize = MeasureTextEx(retroFont, text, (float)fontSize, 0);
        Vector2 pos = {(float)(x + (w - textSize.x) / 2), (float)(y + (h - textSize.y) / 2)};
        DrawTextEx(retroFont, text, pos, (float)fontSize, 0, border);
    } else {
        int textW = MeasureTextWithFont(text, fontSize);
        DrawTextWithFont(text, x + (w-textW)/2, y + (h-fontSize)/2, fontSize, border);
    }
    
    if (selected && (CustomIsKeyPressed(KEY_ENTER) || CustomIsKeyPressed(KEY_SPACE))) {
        PlayTerminalTypeSound();
        return true;
    }
    return false;
}

// Helper function to draw text using retroFont if available, otherwise default font
void DrawTextWithFont(const char* text, int posX, int posY, int fontSize, Color color) {
    if (retroFont.texture.id > 0) {
        DrawTextEx(retroFont, text, (Vector2){(float)posX, (float)posY}, (float)fontSize, 0, color);
    } else {
        DrawText(text, posX, posY, fontSize, color);
    }
}

// Helper function to measure text width using retroFont if available
int MeasureTextWithFont(const char* text, int fontSize) {
    if (retroFont.texture.id > 0) {
        Vector2 size = MeasureTextEx(retroFont, text, (float)fontSize, 0);
        return (int)size.x;
    } else {
        return MeasureText(text, fontSize);
    }
}

// ------------------------------------------------------------
// STATION VIEWPORT MODULE
// ------------------------------------------------------------

enum StationType {
    STATION_ALPHA,  // Torus
    STATION_BETA,   // Icosahedron
    STATION_GAMMA,  // Torus (Variant)
    STATION_DELTA   // Icosahedron (Variant)
};

struct Star {
    float x;
    float y;
    float z;        // Depth (0 = far, 1 = close)
    float speed;
    Color color;
};

// MESH GENERATION FUNCTIONS (ADAPTED FROM SHAPES_IN_SPACE)

Mesh GenFlatShadedTorus(float radius, float size, int radSeg, int sides)
{
    Mesh mesh = { 0 };
    
    int numFaces = radSeg * sides;
    int numVertices = numFaces * 4; // 4 vertices per face (quads)
    int numIndices = numFaces * 6;  // 6 indices per face (2 triangles)
    
    mesh.vertexCount = numVertices;
    mesh.triangleCount = numFaces * 2;
    
    mesh.vertices = (float *)MemAlloc(mesh.vertexCount * 3 * sizeof(float));
    mesh.normals = (float *)MemAlloc(mesh.vertexCount * 3 * sizeof(float));
    mesh.texcoords = (float *)MemAlloc(mesh.vertexCount * 2 * sizeof(float));
    mesh.colors = (unsigned char *)MemAlloc(mesh.vertexCount * 4 * sizeof(unsigned char));
    mesh.indices = (unsigned short *)MemAlloc(numIndices * sizeof(unsigned short));
    
    int vIndex = 0;
    int iIndex = 0;
    
    for (int i = 0; i < radSeg; i++)
    {
        for (int j = 0; j < sides; j++)
        {
            float v = (float)j / sides * PI * 2.0f;
            float sinV = sinf(v); 
            
            Color faceColor;
            if (sinV > 0.2f)       faceColor = LIGHTGRAY; 
            else if (sinV < -0.2f) faceColor = DARKGRAY;  
            else                   faceColor = GRAY;      
            
            int iNext = (i + 1) % radSeg;
            int jNext = (j + 1) % sides;
            
            auto GetPos = [&](int seg, int side) -> Vector3 {
                float u = (float)seg / radSeg * PI * 2.0f;
                float v = (float)side / sides * PI * 2.0f;
                
                float x = (radius + size * cosf(v)) * cosf(u);
                float y = size * sinf(v); 
                float z = (radius + size * cosf(v)) * sinf(u);
                return (Vector3){x, y, z};
            };
            
            Vector3 p0 = GetPos(i, j);
            Vector3 p1 = GetPos(iNext, j);
            Vector3 p2 = GetPos(iNext, jNext);
            Vector3 p3 = GetPos(i, jNext);
            
            Vector3 normal = Vector3Normalize(Vector3CrossProduct(Vector3Subtract(p1, p0), Vector3Subtract(p2, p0))); 
            
            auto AddVertex = [&](Vector3 p) {
                mesh.vertices[vIndex*3] = p.x;
                mesh.vertices[vIndex*3+1] = p.y;
                mesh.vertices[vIndex*3+2] = p.z;
                
                mesh.normals[vIndex*3] = normal.x;
                mesh.normals[vIndex*3+1] = normal.y;
                mesh.normals[vIndex*3+2] = normal.z;
                
                mesh.colors[vIndex*4] = faceColor.r;
                mesh.colors[vIndex*4+1] = faceColor.g;
                mesh.colors[vIndex*4+2] = faceColor.b;
                mesh.colors[vIndex*4+3] = faceColor.a;
                
                mesh.texcoords[vIndex*2] = 0.0f;
                mesh.texcoords[vIndex*2+1] = 0.0f;
                
                vIndex++;
            };
            
            int baseIndex = vIndex;
            AddVertex(p0); AddVertex(p1); AddVertex(p2); AddVertex(p3);
            
            mesh.indices[iIndex++] = baseIndex;
            mesh.indices[iIndex++] = baseIndex + 1;
            mesh.indices[iIndex++] = baseIndex + 2;
            
            mesh.indices[iIndex++] = baseIndex;
            mesh.indices[iIndex++] = baseIndex + 2;
            mesh.indices[iIndex++] = baseIndex + 3;
        }
    }
    
    UploadMesh(&mesh, false);
    return mesh;
}

Mesh GenFlatShadedIcosahedron(float scale)
{
    Mesh mesh = { 0 };
    float phi = (1.0f + sqrtf(5.0f)) / 2.0f;
    Vector3 verts[12] = {
        {-1,  phi, 0}, { 1,  phi, 0}, {-1, -phi, 0}, { 1, -phi, 0},
        { 0, -1,  phi}, { 0,  1,  phi}, { 0, -1, -phi}, { 0,  1, -phi},
        { phi, 0, -1}, { phi, 0,  1}, {-phi, 0, -1}, {-phi, 0,  1}
    };
    int indices[20][3] = {
        {0, 11, 5}, {0, 5, 1}, {0, 1, 7}, {0, 7, 10}, {0, 10, 11},
        {1, 5, 9}, {5, 11, 4}, {11, 10, 2}, {10, 7, 6}, {7, 1, 8},
        {3, 9, 4}, {3, 4, 2}, {3, 2, 6}, {3, 6, 8}, {3, 8, 9},
        {4, 9, 5}, {2, 4, 11}, {6, 2, 10}, {8, 6, 7}, {9, 8, 1}
    };
    
    int numFaces = 20;
    mesh.vertexCount = numFaces * 3;
    mesh.triangleCount = numFaces;
    
    mesh.vertices = (float *)MemAlloc(mesh.vertexCount * 3 * sizeof(float));
    mesh.normals = (float *)MemAlloc(mesh.vertexCount * 3 * sizeof(float));
    mesh.texcoords = (float *)MemAlloc(mesh.vertexCount * 2 * sizeof(float));
    mesh.colors = (unsigned char *)MemAlloc(mesh.vertexCount * 4 * sizeof(unsigned char));
    mesh.indices = (unsigned short *)MemAlloc(mesh.vertexCount * sizeof(unsigned short));
    
    int vIndex = 0;
    int iIndex = 0;
    
    for (int i = 0; i < numFaces; i++)
    {
        Vector3 p0 = verts[indices[i][0]];
        Vector3 p1 = verts[indices[i][1]];
        Vector3 p2 = verts[indices[i][2]];
        
        p0 = Vector3Scale(p0, scale);
        p1 = Vector3Scale(p1, scale);
        p2 = Vector3Scale(p2, scale);
        
        Vector3 edge1 = Vector3Subtract(p1, p0);
        Vector3 edge2 = Vector3Subtract(p2, p0);
        Vector3 normal = Vector3Normalize(Vector3CrossProduct(edge1, edge2));
        
        Vector3 center = Vector3Scale(Vector3Add(Vector3Add(p0, p1), p2), 1.0f/3.0f);
        float normalizedY = center.y / (scale * phi); 
        
        Color faceColor;
        if (normalizedY > 0.25f)       faceColor = LIGHTGRAY; 
        else if (normalizedY < -0.25f) faceColor = DARKGRAY;  
        else                           faceColor = GRAY;      
        
        auto AddVertex = [&](Vector3 p) {
            mesh.vertices[vIndex*3] = p.x;
            mesh.vertices[vIndex*3+1] = p.y;
            mesh.vertices[vIndex*3+2] = p.z;
            
            mesh.normals[vIndex*3] = normal.x;
            mesh.normals[vIndex*3+1] = normal.y;
            mesh.normals[vIndex*3+2] = normal.z;
            
            mesh.colors[vIndex*4] = faceColor.r;
            mesh.colors[vIndex*4+1] = faceColor.g;
            mesh.colors[vIndex*4+2] = faceColor.b;
            mesh.colors[vIndex*4+3] = faceColor.a;
            
            mesh.texcoords[vIndex*2] = 0.0f;
            mesh.texcoords[vIndex*2+1] = 0.0f;
            
            mesh.indices[iIndex++] = vIndex;
            vIndex++;
        };
        
        AddVertex(p0); AddVertex(p1); AddVertex(p2);
    }
    
    UploadMesh(&mesh, false);
    return mesh;
}

class StationViewport {
private:
    RenderTexture2D viewTarget;
    Camera3D camera;
    Shader shader;
    
    Mesh meshTorus;
    Model modelTorus;
    Mesh meshIco;
    Model modelIco;
    
    std::vector<Star> stars;
    float rotation;
    
    // Shader Uniform Locations
    int locViewPos;
    int locAmbient;
    int locLightPos[5];
    int locLightColor[5];
    int locLightDir5;
    int locLightCut5;

public:
    StationViewport() : rotation(0.0f), locViewPos(-1) {
        camera = { 0 };
        shader = { 0 };
        viewTarget = { 0 };
    }

    void Init(int width, int height) {
        // 1. Create Framebuffer (use low res for speed)
        viewTarget = LoadRenderTexture(width, height);
        
        // 2. Load dedicated shaders (renamed to lighting.vs/fs per user request)
        // Use path relative to the DLL/Executable
        shader = LoadShader("lighting.vs", "lighting.fs");
        if (shader.id == 0) {
            // Fallback path
            shader = LoadShader("Data/games/AstroMiner/lighting.vs", "Data/games/AstroMiner/lighting.fs");
        }
        
        // Get Locations
        locViewPos = GetShaderLocation(shader, "viewPos");
        locAmbient = GetShaderLocation(shader, "ambientColor");
        
        locLightPos[0] = GetShaderLocation(shader, "lightPos");
        locLightColor[0] = GetShaderLocation(shader, "lightColor");
        locLightPos[1] = GetShaderLocation(shader, "lightPos2");
        locLightColor[1] = GetShaderLocation(shader, "lightColor2");
        locLightPos[2] = GetShaderLocation(shader, "lightPos3");
        locLightColor[2] = GetShaderLocation(shader, "lightColor3");
        locLightPos[3] = GetShaderLocation(shader, "lightPos4");
        locLightColor[3] = GetShaderLocation(shader, "lightColor4");
        
        locLightPos[4] = GetShaderLocation(shader, "lightPos5");
        locLightColor[4] = GetShaderLocation(shader, "lightColor5");
        locLightDir5 = GetShaderLocation(shader, "lightDir5");
        locLightCut5 = GetShaderLocation(shader, "lightCutoff5");
        
        // Set Default Light Values
        float ambient[] = { 0.1f, 0.1f, 0.1f };
        SetShaderValue(shader, locAmbient, ambient, SHADER_UNIFORM_VEC3);
        
        // Lights setup similar to source
        float lColor1[] = { 0.8f, 0.8f, 0.8f }; Vector3 lPos1 = { 0.0f, 50.0f, 0.0f };
        SetShaderValue(shader, locLightColor[0], lColor1, SHADER_UNIFORM_VEC3);
        SetShaderValue(shader, locLightPos[0], &lPos1, SHADER_UNIFORM_VEC3);

        float lColor2[] = { 0.4f, 0.4f, 0.4f }; Vector3 lPos2 = { -50.0f, 0.0f, 0.0f };
        SetShaderValue(shader, locLightColor[1], lColor2, SHADER_UNIFORM_VEC3);
        SetShaderValue(shader, locLightPos[1], &lPos2, SHADER_UNIFORM_VEC3);
        
        float lColor3[] = { 1.0f, 1.0f, 1.0f }; Vector3 lPos3 = { -40.0f, 40.0f, 20.0f };
        SetShaderValue(shader, locLightColor[2], lColor3, SHADER_UNIFORM_VEC3);
        SetShaderValue(shader, locLightPos[2], &lPos3, SHADER_UNIFORM_VEC3);
        
        float lColor4[] = { 0.8f, 0.9f, 1.0f }; Vector3 lPos4 = { 0.0f, 100.0f, 0.0f };
        SetShaderValue(shader, locLightColor[3], lColor4, SHADER_UNIFORM_VEC3);
        SetShaderValue(shader, locLightPos[3], &lPos4, SHADER_UNIFORM_VEC3);
        
        // Light 5 is dynamic (camera spot)
        float lColor5[] = { 0.53f, 0.81f, 0.92f };
        SetShaderValue(shader, locLightColor[4], lColor5, SHADER_UNIFORM_VEC3);
        float cutoff = cosf(30.0f * DEG2RAD);
        SetShaderValue(shader, locLightCut5, &cutoff, SHADER_UNIFORM_FLOAT);

        // 3. Generate Geometry
        meshTorus = GenFlatShadedTorus(12.0f, 3.0f, 24, 16); // Using params from source
        modelTorus = LoadModelFromMesh(meshTorus);
        modelTorus.materials[0].shader = shader;
        modelTorus.materials[0].maps[MATERIAL_MAP_DIFFUSE].color = WHITE;
        
        meshIco = GenFlatShadedIcosahedron(6.0f);
        modelIco = LoadModelFromMesh(meshIco);
        modelIco.materials[0].shader = shader;
        modelIco.materials[0].maps[MATERIAL_MAP_DIFFUSE].color = WHITE;
        
        // 4. Setup Fixed Camera
        camera.position = (Vector3){ 25.0f, 15.0f, 25.0f };
        camera.target = (Vector3){ 0.0f, 0.0f, 0.0f };
        camera.up = (Vector3){ 0.0f, 1.0f, 0.0f };
        camera.fovy = 45.0f;
        camera.projection = CAMERA_PERSPECTIVE;
        
        // 5. Init Stars
        stars.resize(200);
        for(auto& star : stars) {
            star.x = (float)(GetRandomValue(-width/2, width/2));
            star.y = (float)(GetRandomValue(-height/2, height/2));
            star.z = (float)GetRandomValue(1, 1000) / 1000.0f;
            star.speed = 0.005f + (1.0f - star.z) * 0.0025f;
            star.color = WHITE;
            if (GetRandomValue(0, 100) < 20) {
                 int c = GetRandomValue(0, 3);
                 if(c==0) star.color = SKYBLUE;
                 else if(c==1) star.color = YELLOW;
                 else star.color = LIGHTGRAY;
            }
        }
    }
    
    void Update(float dt) {
        rotation += 15.0f * dt;
        if(rotation > 360.0f) rotation -= 360.0f;
        
        // Update stars
        for(auto& star : stars) {
            star.z -= star.speed * dt * 60.0f; // Scale speed for 60fps
            if(star.z <= 0.0f) {
                star.x = (float)(GetRandomValue(-viewTarget.texture.width/2, viewTarget.texture.width/2));
                star.y = (float)(GetRandomValue(-viewTarget.texture.height/2, viewTarget.texture.height/2));
                star.z = 1.0f;
            }
        }
        
        // Update Shader Uniforms (Dynamic Light 5)
        float camPos[3] = { camera.position.x, camera.position.y, camera.position.z };
        SetShaderValue(shader, locViewPos, camPos, SHADER_UNIFORM_VEC3);
        SetShaderValue(shader, locLightPos[4], camPos, SHADER_UNIFORM_VEC3);
        
        Vector3 camDir = Vector3Normalize(Vector3Subtract(camera.target, camera.position));
        float camDirArr[3] = { camDir.x, camDir.y, camDir.z };
        SetShaderValue(shader, locLightDir5, camDirArr, SHADER_UNIFORM_VEC3);
    }
    
    void Render(StationType activeStation) {
        BeginTextureMode(viewTarget);
            ClearBackground(BLACK);
            
            // 1. Draw Starfield
            int w = viewTarget.texture.width;
            int h = viewTarget.texture.height;
            for(const auto& star : stars) {
                float perspective = 1.0f / star.z;
                float x = star.x * perspective + w / 2.0f;
                float y = star.y * perspective + h / 2.0f;
                
                if (x >= 0 && x < w && y >= 0 && y < h) {
                    float size = (1.0f - star.z) * 3.0f;
                    if (size < 1.0f) size = 1.0f;
                    float brightness = 1.0f - star.z;
                    Color c = star.color;
                    c.r = (unsigned char)(c.r * brightness);
                    c.g = (unsigned char)(c.g * brightness);
                    c.b = (unsigned char)(c.b * brightness);
                    DrawCircle((int)x, (int)y, size, c);
                }
            }
            
            // 2. Draw 3D Artifact
            BeginMode3D(camera);
                rlDisableBackfaceCulling();
                
                Model* targetModel = nullptr;
                Color tint = WHITE;
                Vector3 rotationAxis = {0, 1, 0}; // Default Y-axis rotation
                float angleOffset = 0.0f; // Default no angle offset
                
                switch (activeStation) {
                    case STATION_ALPHA: 
                        targetModel = &modelTorus; 
                        break;
                    case STATION_BETA:  
                        targetModel = &modelIco; 
                        break;
                    case STATION_GAMMA: 
                        targetModel = &modelTorus; 
                        tint = RED; 
                        // Slightly angled differently for Halo
                        rotationAxis = Vector3Normalize((Vector3){0.2f, 1.0f, 0.1f}); // Slight tilt
                        angleOffset = 15.0f; // Start at 15 degrees offset
                        break;
                    case STATION_DELTA: 
                        targetModel = &modelIco; 
                        tint = GOLD; 
                        break;
                }
                
                if (targetModel) {
                    float finalRotation = rotation + angleOffset;
                    DrawModelEx(*targetModel, {0,0,0}, rotationAxis, finalRotation, {1,1,1}, tint);
                }
                
                rlEnableBackfaceCulling();
            EndMode3D();
            
        EndTextureMode();
    }
    
    Texture2D GetTexture() {
        return viewTarget.texture;
    }
};

StationViewport stationViewport;

// ------------------------------------------------------------
// LEADERBOARD MODAL
// ------------------------------------------------------------
void DrawLeaderboardModal() {
    if (!g_showLeaderboard || g_leaderboardDismissed) {
        return;
    }
    
    // Calculate modal dimensions (wider to accommodate username column)
    int modalWidth = 950;
    int modalHeight = 600;
    int modalX = (VIRTUAL_WIDTH - modalWidth) / 2;
    int modalY = (VIRTUAL_HEIGHT - modalHeight) / 2;
    
    // Draw dark overlay
    DrawRectangle(0, 0, VIRTUAL_WIDTH, VIRTUAL_HEIGHT, (Color){0, 0, 0, 200});
    
    // Draw rad retro window with neon glow effect
    Color panelFill = {5, 10, 25, 250};
    Color borderGlow = {0, 255, 255, 255};
    Color borderInner = {100, 200, 255, 255};
    
    // Outer glow
    DrawRectangleLinesEx((Rectangle){(float)(modalX - 2), (float)(modalY - 2), (float)(modalWidth + 4), (float)(modalHeight + 4)}, 2, borderGlow);
    // Main window
    DrawRectangle(modalX, modalY, modalWidth, modalHeight, panelFill);
    DrawRectangleLines(modalX, modalY, modalWidth, modalHeight, borderInner);
    
    // Title bar with gradient effect
    DrawRectangle(modalX, modalY, modalWidth, 40, borderGlow);
    const char* title = "ASTRO MINER LEADERBOARD";
    int titleW = MeasureTextWithFont(title, 24);
    DrawTextWithFont(title, modalX + (modalWidth - titleW) / 2, modalY + 8, 24, BLACK);
    
    // Draw leaderboard entries
    int startY = modalY + 60;
    int lineHeight = 45;
    int fontSize = 16;
    int headerFontSize = 14;
    
    // Header
    DrawTextWithFont("RANK", modalX + 30, startY, headerFontSize, YELLOW);
    DrawTextWithFont("SCORE", modalX + 150, startY, headerFontSize, YELLOW);
    DrawTextWithFont("CREDITS", modalX + 300, startY, headerFontSize, YELLOW);
    DrawTextWithFont("USERNAME", modalX + 450, startY, headerFontSize, YELLOW);
    DrawTextWithFont("RANK", modalX + 600, startY, headerFontSize, YELLOW);
    
    // Draw entries
    int entriesToShow = g_leaderboardCount < 10 ? g_leaderboardCount : 10;
    for (int i = 0; i < entriesToShow; i++) {
        int y = startY + 30 + (i * lineHeight);
        Color entryColor = (i == 0 && g_lastFinalScore > 0 && g_leaderboard[i].score == g_lastFinalScore) 
                           ? (Color){255, 255, 0, 255}  // Highlight new entry
                           : (Color){0, 255, 255, 255};  // Cyan for others
        
        // Rank position
        char rankStr[16];
        sprintf(rankStr, "#%d", i + 1);
        DrawTextWithFont(rankStr, modalX + 30, y, fontSize, entryColor);
        
        // Score
        char scoreStr[32];
        sprintf(scoreStr, "%d", g_leaderboard[i].score);
        DrawTextWithFont(scoreStr, modalX + 150, y, fontSize, entryColor);
        
        // Credits
        char creditsStr[32];
        sprintf(creditsStr, "%d", g_leaderboard[i].credits);
        DrawTextWithFont(creditsStr, modalX + 300, y, fontSize, entryColor);
        
        // Username
        DrawTextWithFont(g_leaderboard[i].username, modalX + 450, y, fontSize, entryColor);
        
        // Rank name
        DrawTextWithFont(g_leaderboard[i].rankName, modalX + 600, y, fontSize, entryColor);
    }
    
    // If no entries, show message
    if (g_leaderboardCount == 0) {
        DrawTextWithFont("NO SCORES YET", modalX + modalWidth / 2 - 100, startY + 100, fontSize, GRAY);
    }
    
    // Show last score if available
    if (g_lastFinalScore > 0) {
        char lastScoreText[128];
        sprintf(lastScoreText, "YOUR SCORE: %d", g_lastFinalScore);
        int lastScoreW = MeasureTextWithFont(lastScoreText, 18);
        DrawTextWithFont(lastScoreText, modalX + (modalWidth - lastScoreW) / 2, modalY + modalHeight - 80, 18, YELLOW);
    }
    
    // Dismiss instruction
    const char* dismissText = "PRESS ENTER TO CONTINUE";
    int dismissW = MeasureTextWithFont(dismissText, 14);
    DrawTextWithFont(dismissText, modalX + (modalWidth - dismissW) / 2, modalY + modalHeight - 30, 14, (Color){150, 150, 150, 255});
    
    // Check for Enter key to dismiss
    if (CustomIsKeyPressed(KEY_ENTER) || CustomIsKeyPressed(KEY_SPACE)) {
        PlayTerminalTypeSound();
        g_leaderboardDismissed = true;
        g_showLeaderboard = false;
        printf("[DrawLeaderboardModal] Leaderboard dismissed\n");
    }
}

// ------------------------------------------------------------
// PAGE: SPLASH SCREENS & MENU
// ------------------------------------------------------------
void DrawPageSplash(GameState* state, int* menuSelection, Vector3* shipPos, Vector3* shipVel, float dt) {
    static int draw_call_count = 0;
    draw_call_count++;
    if (draw_call_count == 1 || draw_call_count % 60 == 0) {
        printf("[DrawPageSplash] Called! splashIndex=%d, splashTimer=%.2f, menuOption=%d\n", 
               g_splashIndex, g_splashTimer, g_menuOption);
    }
    
    ClearBackground(BLACK);
    
    // Update splash timer
    g_splashTimer += dt;
    
    // Handle splash screen sequence
    if (g_splashIndex < 3) {
        // Show splash screens in sequence (splash0, splash1, splash2)
        Texture2D* currentSplash = NULL;
        if (g_splashIndex == 0) currentSplash = &splash0Tx;
        else if (g_splashIndex == 1) currentSplash = &splash1Tx;
        else if (g_splashIndex == 2) currentSplash = &splash2Tx;
        
        if (currentSplash && currentSplash->id > 0) {
            DrawTexturePro(*currentSplash,
                (Rectangle){0, 0, (float)currentSplash->width, (float)currentSplash->height},
                (Rectangle){0, 0, VIRTUAL_WIDTH, VIRTUAL_HEIGHT},
                (Vector2){0, 0}, 0.0f, WHITE);
        } else {
            // Debug: Show which splash we're trying to display
            static int debug_logged[3] = {0, 0, 0};
            if (!debug_logged[g_splashIndex]) {
                printf("[DrawPageSplash] WARNING: Splash texture %d not loaded (id=%d)\n", g_splashIndex, currentSplash ? currentSplash->id : 0);
                debug_logged[g_splashIndex] = 1;
            }
            // Draw a placeholder text so we know the splash screen is active
            char splashText[32];
            sprintf(splashText, "SPLASH %d", g_splashIndex);
            DrawTextWithFont(splashText, VIRTUAL_WIDTH/2 - 100, VIRTUAL_HEIGHT/2, 12, WHITE);
        }
        
        // Audio Logic: Background music is already playing (no bostonpump on splash)
        
        // Advance to next splash after beat duration
        if (g_splashTimer >= g_splashBeatDuration) {
            g_splashIndex++;
            g_splashTimer = 0.0f;
            printf("[DrawPageSplash] Advanced to splash index %d\n", g_splashIndex);
            
            // Show leaderboard modal after splash2 (when advancing to menu)
            if (g_splashIndex == 3 && g_showLeaderboard && !g_leaderboardDismissed) {
                // Leaderboard will be shown in the menu phase
            }
        }
    } else {
        // Show leaderboard modal if needed (after splash2, before menu)
        if (g_showLeaderboard && !g_leaderboardDismissed) {
            DrawLeaderboardModal();
            return;  // Don't show menu while leaderboard is visible
        }
        
        // Menu phase - handle navigation
        if (CustomIsKeyPressed(KEY_DOWN)) {
            g_menuOption = (g_menuOption + 1) % 3;
        }
        if (CustomIsKeyPressed(KEY_UP)) {
            g_menuOption = (g_menuOption - 1 + 3) % 3;
        }
        
        // Handle ESC on splash screen menu - ESC should NOT quit the game
        // It just does nothing here (user must use ENTER to select QUIT GAME)
        /*
        if (CustomIsKeyPressed(KEY_ESCAPE)) {
            if (g_menuOption == 2) {  // QUIT GAME selected
                g_exit_requested = true;
            }
            // Otherwise ESC does nothing on splash screen menu
        }
        */
        
        // Draw appropriate menu splash based on selection
        Texture2D* menuSplash = NULL;
        if (g_menuOption == 0) menuSplash = &splashNewGameTx;
        else if (g_menuOption == 1) menuSplash = &splashLoadGameTx;
        else if (g_menuOption == 2) menuSplash = &splashQuitGameTx;
        
        if (menuSplash && menuSplash->id > 0) {
            DrawTexturePro(*menuSplash,
                (Rectangle){0, 0, (float)menuSplash->width, (float)menuSplash->height},
                (Rectangle){0, 0, VIRTUAL_WIDTH, VIRTUAL_HEIGHT},
                (Vector2){0, 0}, 0.0f, WHITE);
        } else {
            // Debug: Show menu option if texture not loaded
            static int menu_debug_logged[3] = {0, 0, 0};
            if (!menu_debug_logged[g_menuOption]) {
                printf("[DrawPageSplash] WARNING: Menu splash texture %d not loaded (id=%d)\n", g_menuOption, menuSplash ? menuSplash->id : 0);
                menu_debug_logged[g_menuOption] = 1;
            }
            // Draw placeholder text
            const char* menuText[] = {"NEW GAME", "LOAD GAME", "QUIT GAME"};
            DrawTextWithFont(menuText[g_menuOption], VIRTUAL_WIDTH/2 - 150, VIRTUAL_HEIGHT/2, 12, WHITE);
            DrawTextWithFont("Use UP/DOWN arrows, ENTER to select", VIRTUAL_WIDTH/2 - 200, VIRTUAL_HEIGHT/2 + 60, 12, GRAY);
        }
        
        // Handle selection
        if (CustomIsKeyPressed(KEY_ENTER) || CustomIsKeyPressed(KEY_SPACE)) {
            PlayTerminalTypeSound();
            if (g_menuOption == 0) {
                // New Game - reset to Depot_Home
                *shipPos = (Vector3){0, 60, -PROSPECT_PERIMETER};
                *shipVel = (Vector3){0, 0, 10};
                
                // Stabilize ship at launch start (reset pitch, roll, yaw, and horizontal velocity)
                g_shipPitch = 0.0f;
                g_shipRoll = 0.0f;
                g_shipYaw = 0.0f;
                shipVel->x = 0.0f;  // Zero horizontal X velocity
                shipVel->z = 10.0f; // Keep forward Z velocity for initial movement
                
                // Reset to new game defaults
                G_Player.fuel = G_Player.maxFuel;
                G_Player.hull = G_Player.maxHull;
                G_Player.power = 20.0f;
                G_Player.rank = 1;
                G_Player.credits = 1000;
                G_Player.totalCreditsEarned = 0;  // Reset lifetime credits
                G_Player.cargoFilled = 0;
                G_Player.hasFuelTankUpgrade = false;
                G_Player.hasCargoBlackHole = false;
                G_Player.hasBetterLaser = false;
                G_Player.hasBetterCollector = false;
                G_Player.shipColor = 0;
                // Clear inventory
                for (int i = 0; i < NUM_COMMODITIES; i++) {
                    G_Player.inventory[i] = 0;
                }
                G_Player.hasLaser = false;  // Reset upgrades
                G_Player.hasCollector = false;
                G_Player.thrusterBoost = 1.0f;
                G_Player.hullResistance = 1.0f;
                SHIP_THRUST_POWER = 24.0f;  // Reset thrust power (20% stronger)
                g_exit_requested = false;  // Reset exit flag
                g_showWelcomeModal = true;  // Show welcome modal for new game
                // Background music is already playing (plays alongside splash music)
                *state = STATE_DEPOT_HOME;
                *menuSelection = 0;
            } else if (g_menuOption == 1) {
                // Load Game - load save file
                // Stop splash music (background music is already playing)
                if (IsMusicStreamPlaying(g_splashMusic)) {
                    StopMusicStream(g_splashMusic);
                    g_splashMusicFadingOut = false;
                }
                // Try to load save file
                if (LoadGame()) {
                    // Load successful - go to the correct home state based on saved location
                    if (g_currentLocation == 1) {
                        *state = STATE_STATION_HOME;
                    } else if (g_currentLocation == 2) {
                        *state = STATE_HALO_HOME;
                    } else {
                        *state = STATE_DEPOT_HOME;
                    }
                    *menuSelection = 0;
                    // Reset depot home page state to ensure asteroid prospects can be viewed
                    g_depotHomePage = 1;
                    g_showProspectAsteroids = false;  // Start with prospects hidden, user presses Enter to show
                } else {
                    // Load failed - show error modal
                    g_showNoSaveModal = true;
                }
            } else if (g_menuOption == 2) {
                // Quit - signal exit to BBS
                g_exit_requested = true;
            }
        }
    }
    
    // Draw no save modal if needed
    if (g_showNoSaveModal) {
        DrawNoSaveModal();
    }
}

// ------------------------------------------------------------
// PAGE: DEPOT HOME
// ------------------------------------------------------------
// Helper function to get rank name
const char* GetRankName(int rank) {
    switch(rank) {
        case 1: return "Cadet Miner";
        case 2: return "Junior Miner";
        case 3: return "Able Miner";
        case 4: return "Leading Miner";
        case 5: return "Chief Miner";
        default: return "Cadet Miner";
    }
}

// ------------------------------------------------------------
// LEADERBOARD SYSTEM
// ------------------------------------------------------------
// Calculate final score: credits × rank multiplier
int CalculateFinalScore(int credits, int rank) {
    return credits * rank;  // x1 for rank 1, x2 for rank 2, etc.
}

// Load leaderboard from file
void LoadLeaderboard() {
    g_leaderboardCount = 0;
    const char* filename = "Data/games/AstroMiner/leaderboard.json";
    
    // Try alternative paths
    const char* paths[] = {
        "Data/games/AstroMiner/leaderboard.json",
        "../../games/AstroMiner/leaderboard.json",
        "leaderboard.json"
    };
    
    FILE* file = NULL;
    for (int i = 0; i < 3; i++) {
        file = fopen(paths[i], "r");
        if (file) {
            printf("[LoadLeaderboard] Loaded from: %s\n", paths[i]);
            break;
        }
    }
    
    if (!file) {
        printf("[LoadLeaderboard] No existing leaderboard file found, starting fresh\n");
        return;
    }
    
    // Simple JSON parsing (one entry per line: {"score":X,"credits":Y,"rank":Z,"rankName":"..."})
    char line[512];
    int entryIdx = 0;
    while (fgets(line, sizeof(line), file) && entryIdx < MAX_LEADERBOARD_ENTRIES) {
        // Skip empty lines and whitespace
        int i = 0;
        while (line[i] == ' ' || line[i] == '\t' || line[i] == '\n' || line[i] == '\r') i++;
        if (line[i] == '\0') continue;
        
        int score = 0, credits = 0, rank = 1;
        char rankName[32] = "";
        char username[MAX_USERNAME_LENGTH] = "";
        
        // Parse JSON manually (simple format) - try multiple patterns with username
        int parsed = sscanf(line, "{\"score\":%d,\"credits\":%d,\"rank\":%d,\"rankName\":\"%31[^\"]\",\"username\":\"%31[^\"]\"}", 
                           &score, &credits, &rank, rankName, username);
        if (parsed == 5) {
            g_leaderboard[entryIdx].score = score;
            g_leaderboard[entryIdx].credits = credits;
            g_leaderboard[entryIdx].rank = rank;
            strncpy(g_leaderboard[entryIdx].rankName, rankName, sizeof(g_leaderboard[entryIdx].rankName) - 1);
            g_leaderboard[entryIdx].rankName[sizeof(g_leaderboard[entryIdx].rankName) - 1] = '\0';
            strncpy(g_leaderboard[entryIdx].username, username, MAX_USERNAME_LENGTH - 1);
            g_leaderboard[entryIdx].username[MAX_USERNAME_LENGTH - 1] = '\0';
            entryIdx++;
        } else {
            // Try without username (backward compatibility)
            parsed = sscanf(line, "{\"score\":%d,\"credits\":%d,\"rank\":%d,\"rankName\":\"%31[^\"]\"}", 
                           &score, &credits, &rank, rankName);
            if (parsed == 4) {
                g_leaderboard[entryIdx].score = score;
                g_leaderboard[entryIdx].credits = credits;
                g_leaderboard[entryIdx].rank = rank;
                strncpy(g_leaderboard[entryIdx].rankName, rankName, sizeof(g_leaderboard[entryIdx].rankName) - 1);
                g_leaderboard[entryIdx].rankName[sizeof(g_leaderboard[entryIdx].rankName) - 1] = '\0';
                strncpy(g_leaderboard[entryIdx].username, "PLAYER", MAX_USERNAME_LENGTH - 1);  // Default for old entries
                g_leaderboard[entryIdx].username[MAX_USERNAME_LENGTH - 1] = '\0';
                entryIdx++;
            } else {
                // Try alternative format (with spaces)
                parsed = sscanf(line, "{ \"score\": %d, \"credits\": %d, \"rank\": %d, \"rankName\": \"%31[^\"]\", \"username\": \"%31[^\"]\" }", 
                               &score, &credits, &rank, rankName, username);
                if (parsed == 5) {
                    g_leaderboard[entryIdx].score = score;
                    g_leaderboard[entryIdx].credits = credits;
                    g_leaderboard[entryIdx].rank = rank;
                    strncpy(g_leaderboard[entryIdx].rankName, rankName, sizeof(g_leaderboard[entryIdx].rankName) - 1);
                    g_leaderboard[entryIdx].rankName[sizeof(g_leaderboard[entryIdx].rankName) - 1] = '\0';
                    strncpy(g_leaderboard[entryIdx].username, username, MAX_USERNAME_LENGTH - 1);
                    g_leaderboard[entryIdx].username[MAX_USERNAME_LENGTH - 1] = '\0';
                    entryIdx++;
                }
            }
        }
    }
    
    g_leaderboardCount = entryIdx;
    fclose(file);
    printf("[LoadLeaderboard] Loaded %d entries\n", g_leaderboardCount);
}

// Save leaderboard to file
void SaveLeaderboard() {
    const char* filename = "Data/games/AstroMiner/leaderboard.json";
    
    // Try alternative paths
    const char* paths[] = {
        "Data/games/AstroMiner/leaderboard.json",
        "../../games/AstroMiner/leaderboard.json",
        "leaderboard.json"
    };
    
    FILE* file = NULL;
    for (int i = 0; i < 3; i++) {
        // Create directory if needed (simple check)
        file = fopen(paths[i], "w");
        if (file) {
            printf("[SaveLeaderboard] Saving to: %s\n", paths[i]);
            break;
        }
    }
    
    if (!file) {
        printf("[SaveLeaderboard] ERROR: Could not open file for writing\n");
        return;
    }
    
    // Write JSON entries (one per line for simplicity)
    for (int i = 0; i < g_leaderboardCount; i++) {
        fprintf(file, "{\"score\":%d,\"credits\":%d,\"rank\":%d,\"rankName\":\"%s\",\"username\":\"%s\"}\n",
                g_leaderboard[i].score,
                g_leaderboard[i].credits,
                g_leaderboard[i].rank,
                g_leaderboard[i].rankName,
                g_leaderboard[i].username);
    }
    
    fclose(file);
    printf("[SaveLeaderboard] Saved %d entries\n", g_leaderboardCount);
}

// Add score to leaderboard (insert in sorted order)
void AddToLeaderboard(int score, int credits, int rank) {
    const char* rankName = GetRankName(rank);
    
    // Find insertion point (keep sorted by score, descending)
    int insertIdx = g_leaderboardCount;
    for (int i = 0; i < g_leaderboardCount; i++) {
        if (score > g_leaderboard[i].score) {
            insertIdx = i;
            break;
        }
    }
    
    // Shift entries down if needed
    if (g_leaderboardCount < MAX_LEADERBOARD_ENTRIES) {
        g_leaderboardCount++;
    }
    
    for (int i = g_leaderboardCount - 1; i > insertIdx; i--) {
        g_leaderboard[i] = g_leaderboard[i - 1];
    }
    
    // Insert new entry
    g_leaderboard[insertIdx].score = score;
    g_leaderboard[insertIdx].credits = credits;
    g_leaderboard[insertIdx].rank = rank;
    strncpy(g_leaderboard[insertIdx].rankName, rankName, sizeof(g_leaderboard[insertIdx].rankName) - 1);
    g_leaderboard[insertIdx].rankName[sizeof(g_leaderboard[insertIdx].rankName) - 1] = '\0';
    strncpy(g_leaderboard[insertIdx].username, g_currentUsername, MAX_USERNAME_LENGTH - 1);
    g_leaderboard[insertIdx].username[MAX_USERNAME_LENGTH - 1] = '\0';
    
    // Keep only top entries
    if (g_leaderboardCount > MAX_LEADERBOARD_ENTRIES) {
        g_leaderboardCount = MAX_LEADERBOARD_ENTRIES;
    }
    
    SaveLeaderboard();
    printf("[AddToLeaderboard] Added score %d (credits: %d, rank: %d) at position %d\n", 
           score, credits, rank, insertIdx + 1);
}

// Reset all player stats to new game defaults
// This is called when launching from BBS to ensure a fresh start
void ResetPlayerStats() {
    printf("[ResetPlayerStats] Resetting all player stats to new game defaults\n");
    
    // Reset player data to new game defaults
    G_Player.fuel = 100.0f;
    G_Player.maxFuel = 100.0f;
    G_Player.hull = 100.0f;
    G_Player.maxHull = 100.0f;
    G_Player.power = 20.0f;
    G_Player.maxPower = 100.0f;
    G_Player.rank = 1;
    G_Player.credits = 1000;
    G_Player.maxCredits = 100000;
    G_Player.totalCreditsEarned = 0;  // Reset lifetime credits
    G_Player.cargoSpace = 25;  // Default cargo space
    G_Player.cargoFilled = 0;
    
    // Clear inventory
    for (int i = 0; i < NUM_COMMODITIES; i++) {
        G_Player.inventory[i] = 0;
    }
    
    // Reset upgrades
    G_Player.hasLaser = false;
    G_Player.hasCollector = false;
    G_Player.thrusterBoost = 1.0f;
    G_Player.hullResistance = 1.0f;
    G_Player.hasGoldCard = false;
    
    // Reset laser system
    G_Player.laserHeat = 0.0f;
    G_Player.maxLaserHeat = 100.0f;
    G_Player.laserCooldown = 0.0f;
    G_Player.laserOverheated = false;
    
    // Reset ship upgrades
    G_Player.hasFuelTankUpgrade = false;
    G_Player.hasCargoBlackHole = false;
    G_Player.hasBetterLaser = false;
    G_Player.hasBetterCollector = false;
    G_Player.shipColor = 0;  // Blue (default)
    
    // Reset ship position and state
    g_shipPos = (Vector3){0, 60, -PROSPECT_PERIMETER};
    g_shipVel = (Vector3){0, 0, 10};
    g_shipPitch = 0.0f;
    g_shipRoll = 0.0f;
    g_shipYaw = 0.0f;
    SHIP_THRUST_POWER = 24.0f;  // Reset thrust power
    
    // Reset game state
    g_currentState = STATE_SPLASH;  // Start with splash screens
    g_splashIndex = 0;
    g_splashTimer = 0.0f;
    g_menuOption = 0;
    g_exit_requested = false;
    
    // Reset location and bar state
    g_currentLocation = 0;  // Depot
    g_barDrinksPurchased = 0;
    g_isDrunk = false;
    g_drunkGravityIncrease = 0;
    g_drunkThreshold = 0;  // Reset drunk threshold
    g_showDrunkModal = false;
    
    // Reset modals
    g_showRankUpModal = false;
    g_showWelcomeModal = false;
    g_showLeaderboard = false;
    g_leaderboardDismissed = false;
    g_lastFinalScore = 0;
    
    // Reset depot home page
    g_depotHomePage = 1;
    g_showProspectAsteroids = false;
    g_showShipyardShop = false;
    g_showCommoditiesMarket = false;
    g_showBarView = false;
    
    // Reset mission state
    g_missionInProgress = false;
    g_wasInsideCylinder = false;
    g_showGetReady = false;
    g_getReadyTimer = 0.0f;
    
    // Reset asteroid data to defaults (in case they were modified by bar events or drunk state)
    // Depot asteroids (lower prosperity, lower fuel)
    int depotProspectScores[6] = {10, 22, 34, 46, 58, 70};
    int depotGravityScores[6] = {25, 38, 51, 64, 76, 88};
    for (int i = 0; i < 6; i++) {
        g_prospectScores[i] = depotProspectScores[i];
        g_gravityScores[i] = depotGravityScores[i];
    }
    
    // Station asteroids (higher prosperity, higher fuel)
    int stationProspectScores[6] = {35, 48, 62, 75, 85, 95};
    int stationGravityScores[6] = {45, 58, 71, 84, 90, 95};
    for (int i = 0; i < 6; i++) {
        g_stationProspectScores[i] = stationProspectScores[i];
        g_stationGravityScores[i] = stationGravityScores[i];
    }
    
    // Halo asteroids (highest prosperity, highest fuel)
    int haloProspectScores[6] = {50, 65, 78, 88, 95, 100};
    int haloGravityScores[6] = {55, 68, 81, 90, 95, 98};
    for (int i = 0; i < 6; i++) {
        g_haloProspectScores[i] = haloProspectScores[i];
        g_haloGravityScores[i] = haloGravityScores[i];
    }
    
    printf("[ResetPlayerStats] All stats reset successfully\n");
}

// Save game state to file
void SaveGame() {
    const char* paths[] = {
        "Data/games/AstroMiner/astrominer_save.json",
        "../../games/AstroMiner/astrominer_save.json",
        "astrominer_save.json"
    };
    
    FILE* file = NULL;
    const char* usedPath = NULL;
    for (int i = 0; i < 3; i++) {
        file = fopen(paths[i], "w");
        if (file) {
            usedPath = paths[i];
            break;
        }
    }
    
    if (!file) {
        printf("[SaveGame] ERROR: Failed to create save file\n");
        return;
    }
    
    // Save player data as JSON
    fprintf(file, "{\n");
    fprintf(file, "  \"fuel\": %.2f,\n", G_Player.fuel);
    fprintf(file, "  \"maxFuel\": %.2f,\n", G_Player.maxFuel);
    fprintf(file, "  \"hull\": %.2f,\n", G_Player.hull);
    fprintf(file, "  \"maxHull\": %.2f,\n", G_Player.maxHull);
    fprintf(file, "  \"power\": %.2f,\n", G_Player.power);
    fprintf(file, "  \"maxPower\": %.2f,\n", G_Player.maxPower);
    fprintf(file, "  \"rank\": %d,\n", G_Player.rank);
    fprintf(file, "  \"credits\": %d,\n", G_Player.credits);
    fprintf(file, "  \"maxCredits\": %d,\n", G_Player.maxCredits);
    fprintf(file, "  \"totalCreditsEarned\": %d,\n", G_Player.totalCreditsEarned);
    fprintf(file, "  \"cargoSpace\": %d,\n", G_Player.cargoSpace);
    fprintf(file, "  \"cargoFilled\": %d,\n", G_Player.cargoFilled);
    fprintf(file, "  \"shipColor\": %d,\n", G_Player.shipColor);
    fprintf(file, "  \"hasLaser\": %s,\n", G_Player.hasLaser ? "true" : "false");
    fprintf(file, "  \"hasCollector\": %s,\n", G_Player.hasCollector ? "true" : "false");
    fprintf(file, "  \"hasBetterLaser\": %s,\n", G_Player.hasBetterLaser ? "true" : "false");
    fprintf(file, "  \"hasBetterCollector\": %s,\n", G_Player.hasBetterCollector ? "true" : "false");
    fprintf(file, "  \"hasFuelTankUpgrade\": %s,\n", G_Player.hasFuelTankUpgrade ? "true" : "false");
    fprintf(file, "  \"hasCargoBlackHole\": %s,\n", G_Player.hasCargoBlackHole ? "true" : "false");
    fprintf(file, "  \"thrusterBoost\": %.2f,\n", G_Player.thrusterBoost);
    fprintf(file, "  \"hullResistance\": %.2f,\n", G_Player.hullResistance);
    fprintf(file, "  \"hasGoldCard\": %s,\n", G_Player.hasGoldCard ? "true" : "false");
    fprintf(file, "  \"currentLocation\": %d,\n", g_currentLocation);
    fprintf(file, "  \"username\": \"%s\",\n", g_currentUsername);
    fprintf(file, "  \"inventory\": [");
    for (int i = 0; i < NUM_COMMODITIES; i++) {
        fprintf(file, "%d", G_Player.inventory[i]);
        if (i < NUM_COMMODITIES - 1) fprintf(file, ", ");
    }
    fprintf(file, "]\n");
    fprintf(file, "}\n");
    
    fclose(file);
    printf("[SaveGame] Game saved to: %s\n", usedPath);
}

// Load game state from file
bool LoadGame() {
    const char* paths[] = {
        "Data/games/AstroMiner/astrominer_save.json",
        "../../games/AstroMiner/astrominer_save.json",
        "astrominer_save.json"
    };
    
    FILE* file = NULL;
    const char* usedPath = NULL;
    for (int i = 0; i < 3; i++) {
        file = fopen(paths[i], "r");
        if (file) {
            usedPath = paths[i];
            break;
        }
    }
    
    if (!file) {
        printf("[LoadGame] Save file not found\n");
        return false;
    }
    
    // Initialize default values
    float fuel = 100.0f, maxFuel = 100.0f, hull = 100.0f, maxHull = 100.0f;
    float power = 20.0f, maxPower = 100.0f;
    int rank = 1, credits = 1000, maxCredits = 100000, totalCreditsEarned = 0;
    int cargoSpace = 25, cargoFilled = 0, shipColor = 0;
    bool hasLaser = false, hasCollector = false, hasBetterLaser = false, hasBetterCollector = false;
    bool hasFuelTankUpgrade = false, hasCargoBlackHole = false, hasGoldCard = false;
    float thrusterBoost = 1.0f, hullResistance = 1.0f;
    int currentLocation = 0;
    int inventory[NUM_COMMODITIES] = {0};
    char savedUsername[MAX_USERNAME_LENGTH] = "";
    
    // Read file line by line and parse JSON
    char buffer[512];
    while (fgets(buffer, sizeof(buffer), file)) {
        // Remove whitespace
        char* line = buffer;
        while (*line == ' ' || *line == '\t') line++;
        
        if (strstr(line, "\"fuel\"")) sscanf(line, "%*[^:]%*c%f", &fuel);
        else if (strstr(line, "\"maxFuel\"")) sscanf(line, "%*[^:]%*c%f", &maxFuel);
        else if (strstr(line, "\"hull\"")) sscanf(line, "%*[^:]%*c%f", &hull);
        else if (strstr(line, "\"maxHull\"")) sscanf(line, "%*[^:]%*c%f", &maxHull);
        else if (strstr(line, "\"power\"")) sscanf(line, "%*[^:]%*c%f", &power);
        else if (strstr(line, "\"maxPower\"")) sscanf(line, "%*[^:]%*c%f", &maxPower);
        else if (strstr(line, "\"rank\"")) sscanf(line, "%*[^:]%*c%d", &rank);
        else if (strstr(line, "\"credits\"")) sscanf(line, "%*[^:]%*c%d", &credits);
        else if (strstr(line, "\"maxCredits\"")) sscanf(line, "%*[^:]%*c%d", &maxCredits);
        else if (strstr(line, "\"totalCreditsEarned\"")) sscanf(line, "%*[^:]%*c%d", &totalCreditsEarned);
        else if (strstr(line, "\"cargoSpace\"")) sscanf(line, "%*[^:]%*c%d", &cargoSpace);
        else if (strstr(line, "\"cargoFilled\"")) sscanf(line, "%*[^:]%*c%d", &cargoFilled);
        else if (strstr(line, "\"shipColor\"")) sscanf(line, "%*[^:]%*c%d", &shipColor);
        else if (strstr(line, "\"hasLaser\"")) hasLaser = (strstr(line, "true") != NULL);
        else if (strstr(line, "\"hasCollector\"")) hasCollector = (strstr(line, "true") != NULL);
        else if (strstr(line, "\"hasBetterLaser\"")) hasBetterLaser = (strstr(line, "true") != NULL);
        else if (strstr(line, "\"hasBetterCollector\"")) hasBetterCollector = (strstr(line, "true") != NULL);
        else if (strstr(line, "\"hasFuelTankUpgrade\"")) hasFuelTankUpgrade = (strstr(line, "true") != NULL);
        else if (strstr(line, "\"hasCargoBlackHole\"")) hasCargoBlackHole = (strstr(line, "true") != NULL);
        else if (strstr(line, "\"hasGoldCard\"")) hasGoldCard = (strstr(line, "true") != NULL);
        else if (strstr(line, "\"thrusterBoost\"")) sscanf(line, "%*[^:]%*c%f", &thrusterBoost);
        else if (strstr(line, "\"hullResistance\"")) sscanf(line, "%*[^:]%*c%f", &hullResistance);
        else if (strstr(line, "\"currentLocation\"")) sscanf(line, "%*[^:]%*c%d", &currentLocation);
        else if (strstr(line, "\"username\"")) {
            // Parse username string
            char* usernameStart = strstr(line, "\"");
            if (usernameStart) {
                usernameStart = strstr(usernameStart + 1, "\"");
                if (usernameStart) {
                    usernameStart++;  // Skip opening quote
                    char* usernameEnd = strstr(usernameStart, "\"");
                    if (usernameEnd) {
                        int len = usernameEnd - usernameStart;
                        if (len > 0 && len < MAX_USERNAME_LENGTH) {
                            strncpy(savedUsername, usernameStart, len);
                            savedUsername[len] = '\0';
                        }
                    }
                }
            }
        }
        else if (strstr(line, "\"inventory\"")) {
            // Parse inventory array
            char* invStart = strstr(line, "[");
            if (invStart) {
                char* token = strtok(invStart + 1, ",]");
                for (int i = 0; i < NUM_COMMODITIES && token; i++) {
                    inventory[i] = atoi(token);
                    token = strtok(NULL, ",]");
                }
            }
        }
    }
    fclose(file);
    
    // Apply loaded values to player
    G_Player.fuel = fuel;
    G_Player.maxFuel = maxFuel;
    G_Player.hull = hull;
    G_Player.maxHull = maxHull;
    G_Player.power = power;
    G_Player.maxPower = maxPower;
    G_Player.rank = rank;
    G_Player.credits = credits;
    G_Player.maxCredits = maxCredits;
    G_Player.totalCreditsEarned = totalCreditsEarned;
    G_Player.cargoSpace = cargoSpace;
    G_Player.cargoFilled = cargoFilled;
    G_Player.shipColor = shipColor;
    G_Player.hasLaser = hasLaser;
    G_Player.hasCollector = hasCollector;
    G_Player.hasBetterLaser = hasBetterLaser;
    G_Player.hasBetterCollector = hasBetterCollector;
    G_Player.hasFuelTankUpgrade = hasFuelTankUpgrade;
    G_Player.hasCargoBlackHole = hasCargoBlackHole;
    G_Player.hasGoldCard = hasGoldCard;
    G_Player.thrusterBoost = thrusterBoost;
    G_Player.hullResistance = hullResistance;
    g_currentLocation = currentLocation;
    for (int i = 0; i < NUM_COMMODITIES; i++) {
        G_Player.inventory[i] = inventory[i];
    }
    
    // Note: Username will be refreshed from BBS when game session enters
    // The saved username is just for reference, but we always use current BBS username
    if (savedUsername[0] != '\0') {
        printf("[LoadGame] Username in save file: %s (will be refreshed from BBS)\n", savedUsername);
    }
    
    printf("[LoadGame] Game loaded from: %s\n", usedPath);
    return true;
}

// Draw modal when save game not found
void DrawNoSaveModal() {
    // Handle ESC or Enter to close modal
    if (CustomIsKeyPressed(KEY_ESCAPE) || CustomIsKeyPressed(KEY_ENTER) || CustomIsKeyPressed(KEY_SPACE)) {
        PlayTerminalTypeSound();
        g_showNoSaveModal = false;
        return;
    }
    
    // Draw modal window (centered on screen)
    int modalWidth = 700;
    int modalHeight = 300;
    int modalX = (VIRTUAL_WIDTH - modalWidth) / 2;
    int modalY = (VIRTUAL_HEIGHT - modalHeight) / 2;
    
    DrawRetroWindow("SAVE GAME NOT FOUND", modalX, modalY, modalWidth, modalHeight, 15);
    
    // Message text (with word wrapping support)
    const char* messageText = "SAVE GAME NOT FOUND. SAVES ARE ONLY POSSIBLE AT THE NAGAKO HALO'S SHIPYARD ONLY!";
    int maxTextWidth = modalWidth - 100;
    int textY = modalY + 80;
    int textBottomY = textY;
    DrawWordWrappedText(messageText, modalX + 50, textY, maxTextWidth, 18, WHITE, &textBottomY);
    
    // OKAY button
    int buttonWidth = 200;
    int buttonHeight = 50;
    int buttonY = CalculateModalButtonY(modalY, modalHeight, buttonHeight);
    int buttonX = modalX + (modalWidth - buttonWidth) / 2;
    
    bool okaySelected = true;  // Only one button, always selected
    DrawButton("OKAY", buttonX, buttonY, buttonWidth, buttonHeight, okaySelected, 15);
}

// Function to update player rank based on total credits earned
// Rank can only increase, never decrease (even if credits are spent)
void UpdateRank() {
    int oldRank = G_Player.rank;
    int newRank = G_Player.rank;  // Default to current rank
    
    // Rank thresholds (covers all 5 ranks):
    // Rank 1 (Cadet Miner): 0-4,999 credits
    // Rank 2 (Junior Miner): 5,000-9,999 credits
    // Rank 3 (Able Miner): 10,000-19,999 credits
    // Rank 4 (Leading Miner): 20,000-34,999 credits
    // Rank 5 (Chief Miner): 35,000+ credits (reached at 35k, 50k is milestone beyond max rank)
    if (G_Player.totalCreditsEarned >= 35000) {
        newRank = 5;
    } else if (G_Player.totalCreditsEarned >= 20000) {
        newRank = 4;
    } else if (G_Player.totalCreditsEarned >= 10000) {
        newRank = 3;
    } else if (G_Player.totalCreditsEarned >= 5000) {
        newRank = 2;
    } else {
        newRank = 1;
    }
    
    // Only update rank if it increased (never decrease rank)
    if (newRank > oldRank) {
        G_Player.rank = newRank;
        g_newRank = newRank;
        const char* newRankName = GetRankName(G_Player.rank);
        printf("[Rank Update] Rank increased to %d: %s (Total Credits: %d)\n", 
               G_Player.rank, newRankName, G_Player.totalCreditsEarned);
        
        // Show rank-up celebration modal
        g_showRankUpModal = true;
        g_rankUpFireworksTimer = 0.0f;
        
        // Set unique message for each rank
        switch (newRank) {
            case 2:  // Junior Miner
                snprintf(g_rankUpMessage, sizeof(g_rankUpMessage),
                    "CONGRATULATIONS YOU LEVELLED UP!\n\n"
                    "YOUR INFLUENCE IN THE BARS ACROSS THE OORT CLOUD HAS INCREASED.\n\n"
                    "YOU'RE NOW A JUNIOR MINER - KEEP AT IT AND YOU'LL BECOME A LEGEND SPACER!");
                break;
            case 3:  // Able Miner
                snprintf(g_rankUpMessage, sizeof(g_rankUpMessage),
                    "CONGRATULATIONS YOU LEVELLED UP!\n\n"
                    "YOUR INFLUENCE IN THE BARS ACROSS THE OORT CLOUD HAS INCREASED.\n\n"
                    "YOU'RE NOW AN ABLE MINER - YOUR REPUTATION IS GROWING, SPACER!");
                break;
            case 4:  // Leading Miner
                snprintf(g_rankUpMessage, sizeof(g_rankUpMessage),
                    "CONGRATULATIONS YOU LEVELLED UP!\n\n"
                    "YOUR INFLUENCE IN THE BARS ACROSS THE OORT CLOUD HAS INCREASED.\n\n"
                    "YOU'RE NOW A LEADING MINER - YOU'RE MAKING A NAME FOR YOURSELF OUT HERE!");
                break;
            case 5:  // Chief Miner
                snprintf(g_rankUpMessage, sizeof(g_rankUpMessage),
                    "CONGRATULATIONS YOU LEVELLED UP!\n\n"
                    "YOUR INFLUENCE IN THE BARS ACROSS THE OORT CLOUD HAS INCREASED.\n\n"
                    "YOU'RE NOW A CHIEF MINER - YOU'VE BECOME A LEGEND OF THE OORT CLOUD, SPACER!");
                break;
            default:
                snprintf(g_rankUpMessage, sizeof(g_rankUpMessage),
                    "CONGRATULATIONS YOU LEVELLED UP!\n\n"
                    "YOUR INFLUENCE IN THE BARS ACROSS THE OORT CLOUD HAS INCREASED.");
                break;
        }
        
        // Play levelup and sale sounds
        if (g_levelupSound.frameCount > 0) {
            PlaySound(g_levelupSound);
        }
        if (g_saleSound.frameCount > 0) {
            // Play sale sound slightly delayed for effect
            PlaySound(g_saleSound);
        }
    }
    // If newRank < oldRank, keep the old rank (shouldn't happen since totalCreditsEarned only increases)
}

// Function to convert collected debris to commodities
void ConvertDebrisToCommodity() {
    // Get the current asteroid index (0-5 for A-F)
    int asteroidIdx = g_selectedAsteroidIndex;
    
    // Safety check: if asteroid index is invalid, use default (asteroid A = index 0)
    // This ensures debris is always converted even if index wasn't set properly
    if (asteroidIdx < 0 || asteroidIdx >= 6) {
        asteroidIdx = 0;  // Default to asteroid A
    }
    
    // Get abundance values for this asteroid
    int* abundances = g_asteroidCommodityAbundance[asteroidIdx];
    
    // Calculate total abundance for probability distribution
    int totalAbundance = 0;
    for (int i = 0; i < NUM_COMMODITIES; i++) {
        totalAbundance += abundances[i];
    }
    
    if (totalAbundance == 0) {
        // Fallback: if abundance is 0, give a random common commodity
        int commonCommodities[] = {COMMODITY_WATER_ICE, COMMODITY_LUNAR_REGOLITH, COMMODITY_HYDROCARBONS};
        int randomCommon = commonCommodities[GetRandomValue(0, 2)];
        G_Player.inventory[randomCommon]++;
        return;
    }
    
    // Roll for which commodity this debris becomes
    int roll = GetRandomValue(0, totalAbundance - 1);
    int cumulative = 0;
    
    for (int i = 0; i < NUM_COMMODITIES; i++) {
        cumulative += abundances[i];
        if (roll < cumulative) {
            // This debris becomes commodity i
            G_Player.inventory[i]++;
            return;
        }
    }
    
    // Fallback: if we somehow didn't assign a commodity, give water ice
    G_Player.inventory[COMMODITY_WATER_ICE]++;
}

// Function to calculate station buy prices based on available asteroids
void CalculateStationPrices() {
    // For each location (0=Depot, 1=Station, 2=Halo)
    for (int location = 0; location < 3; location++) {
        // Get available asteroids for this location
        int* prospectScores;
        int* gravityScores;
        int numAsteroids = 6;
        
        if (location == 1) {  // Station
            prospectScores = g_stationProspectScores;
            gravityScores = g_stationGravityScores;
        } else if (location == 2) {  // Halo
            prospectScores = g_haloProspectScores;
            gravityScores = g_haloGravityScores;
        } else {  // Depot
            prospectScores = g_prospectScores;
            gravityScores = g_gravityScores;
        }
        
        // Calculate average abundance for each commodity across all asteroids
        float avgAbundance[NUM_COMMODITIES] = {0};
        for (int ast = 0; ast < numAsteroids; ast++) {
            for (int comm = 0; comm < NUM_COMMODITIES; comm++) {
                avgAbundance[comm] += (float)g_asteroidCommodityAbundance[ast][comm];
            }
        }
        for (int comm = 0; comm < NUM_COMMODITIES; comm++) {
            avgAbundance[comm] /= (float)numAsteroids;
        }
        
        // Calculate prices: Lower abundance = Higher price (demand without supply)
        // Price multiplier: 1.0 (common) to 3.0 (rare)
        for (int comm = 0; comm < NUM_COMMODITIES; comm++) {
            // Normalize abundance (0-100 scale)
            float normalizedAbundance = avgAbundance[comm] / 100.0f;
            
            // Inverse relationship: low abundance = high price
            // If abundance is 0, price is 3x base. If abundance is 100, price is 1x base
            float priceMultiplier = 1.0f + (2.0f * (1.0f - normalizedAbundance));
            
            // Calculate final price
            int basePrice = g_commodityBasePrices[comm];
            g_stationBuyPrices[location][comm] = (int)(basePrice * priceMultiplier);
        }
    }
}

// Function to render asteroid prospect view to texture (like StationViewport)
void RenderAsteroidProspects() {
    // Initialize render texture if needed (lazy init fallback)
    if (!g_asteroidViewportInitialized) {
        g_asteroidViewport = LoadRenderTexture(RENDER_WIDTH, RENDER_HEIGHT);
        g_asteroidViewportInitialized = true;
    }
    
    // Update rotation
    float dt = GetFrameTime();
    
    // Ping-pong rotation logic
    static float rotationDir = 1.0f;
    g_asteroidRotation += 30.0f * dt * rotationDir; // Slowed down slightly for smoother oscillation
    
    // Bounds check for ping-pong effect (oscillate between -45 and 45 degrees)
    if (g_asteroidRotation > 45.0f) {
        g_asteroidRotation = 45.0f;
        rotationDir = -1.0f;
    } else if (g_asteroidRotation < -45.0f) {
        g_asteroidRotation = -45.0f;
        rotationDir = 1.0f;
    }
    
    // Render to texture (like StationViewport does)
    BeginTextureMode(g_asteroidViewport);
    
    // Draw background texture (Astriod_Prospects.png) if loaded, otherwise clear black
    if (asteroidProspectsBgTx.id > 0) {
        Rectangle srcRect = { 0, 0, (float)asteroidProspectsBgTx.width, (float)asteroidProspectsBgTx.height };
        Rectangle destRect = { 0, 0, (float)RENDER_WIDTH, (float)RENDER_HEIGHT };
        DrawTexturePro(asteroidProspectsBgTx, srcRect, destRect, (Vector2){0,0}, 0.0f, WHITE);
    } else {
        ClearBackground(BLACK);
    }
    
    // Setup camera for 3D calculations (for text positioning only - no models drawn)
    Camera3D asteroidCamera = {0};
    asteroidCamera.position = (Vector3){0, 0, 15};  // Camera position (match StationViewport)
    asteroidCamera.target = (Vector3){0, 0, 0};     // Look at center
    asteroidCamera.up = (Vector3){0, 1, 0};         // Up vector
    asteroidCamera.fovy = 45.0f;                     // Match StationViewport FOV
    asteroidCamera.projection = CAMERA_PERSPECTIVE;
    
    // Centered asteroid positions: three on top row, three on bottom row
    // Shift whole grid left (~50px) and down (~50px) from previous placement
    // Rough mapping at depth ~15: ~1.6 units ≈ 80px horizontally, ~1.5 units ≈ 50px vertically
    Vector3 asteroidPositions[6] = {
        {-3.0f, 3.0f, 0},   // Asteroid A (top left)
        {0.0f,  3.0f, 0},   // Asteroid B (top middle)
        {3.0f,  3.0f, 0},   // Asteroid C (top right)
        {-3.0f, 0.2f, 0},   // Asteroid D (bottom left) - moved down ~20px
        {0.0f,  0.2f, 0},   // Asteroid E (bottom middle) - moved down ~20px
        {3.0f,  0.2f, 0}    // Asteroid F (bottom right) - moved down ~20px
    };
    
    // 3D Model Rendering Disabled - Using static PNG background
    /*
    // Render asteroids in 3D
    BeginMode3D(asteroidCamera);
    rlDisableBackfaceCulling();
    
    float scale = 0.85f;  // Slightly larger but still leaving breathing room
    Vector3 rotationAxis = {0, 1, 0};  // Rotate around Y axis
    
    for (int i = 0; i < 6; i++) {
        DrawModelEx(g_rockModel, asteroidPositions[i], rotationAxis, g_asteroidRotation * DEG2RAD, 
                   (Vector3){scale, scale, scale}, WHITE);
    }
    
    rlEnableBackfaceCulling();
    EndMode3D();
    */
    
    // Asteroid data: Prospect and Gravity percentages (based on location)
    int* prospectScores;
    int* gravityScores;
    if (g_currentLocation == 1) {  // Station
        prospectScores = g_stationProspectScores;
        gravityScores = g_stationGravityScores;
    } else if (g_currentLocation == 2) {  // Halo
        prospectScores = g_haloProspectScores;
        gravityScores = g_haloGravityScores;
    } else {  // Depot (default)
        prospectScores = g_prospectScores;
        gravityScores = g_gravityScores;
    }
    
    // Reduced font size
    int fontSizeName = 6; 
    int fontSizeStats = 5; 
    int labelGap = 12; // pixels between model footprint and first line
    
    // Establish row baselines so text forms a tidy grid beneath each row
    Vector2 topRowPos = GetWorldToScreen(asteroidPositions[0], asteroidCamera);
    Vector2 bottomRowPos = GetWorldToScreen(asteroidPositions[3], asteroidCamera);
    int textYTopRow = (int)(topRowPos.y + labelGap);
    int textYBottomRow = (int)(bottomRowPos.y + labelGap);
    
    // Draw labels using projected screen positions so they remain centered under each rock
    // DISABLED: Text is now baked into the background PNG (Astriod_Prospects.png)
    /*
    for (int i = 0; i < 6; i++) {
        Vector2 screenPos = GetWorldToScreen(asteroidPositions[i], asteroidCamera);
        int centerX = (int)screenPos.x;
        int textY = (i < 3) ? textYTopRow : textYBottomRow; // keep per-row grid alignment
        
        // Asteroid name (A-F) - centered horizontally
        char asteroidName[32];
        snprintf(asteroidName, sizeof(asteroidName), "ASTEROID %c", 'A' + i);
        int nameW = MeasureTextWithFont(asteroidName, fontSizeName);
        DrawTextWithFont(asteroidName, centerX - nameW/2, textY, fontSizeName, WHITE);
        
        // Prospect score - centered horizontally
        char prospectText[32];
        snprintf(prospectText, sizeof(prospectText), "PROSPECT: %d%%", prospectScores[i]);
        int prospectW = MeasureTextWithFont(prospectText, fontSizeStats);
        DrawTextWithFont(prospectText, centerX - prospectW/2, textY + 12, fontSizeStats, GREEN);
        
        // Gravity score - centered horizontally
        char gravityText[32];
        snprintf(gravityText, sizeof(gravityText), "GRAVITY: %d%%", gravityScores[i]);
        int gravityW = MeasureTextWithFont(gravityText, fontSizeStats);
        DrawTextWithFont(gravityText, centerX - gravityW/2, textY + 22, fontSizeStats, (Color){0, 255, 255, 255});  // Cyan
    }
    */
    
    EndTextureMode();
}

// ------------------------------------------------------------
// RENDER: COMMODITIES MARKET (2D UI list inside viewport)
// ------------------------------------------------------------
// ------------------------------------------------------------
// RENDER: COMMODITIES OVERLAY (Direct Draw)
// ------------------------------------------------------------
void DrawCommoditiesOverlay() {
    // This draws text/numbers directly to the screen (on top of the overlay texture)
    
    // Get current station's buy prices
    int* buyPrices = g_stationBuyPrices[g_currentLocation];
    
    // Draw market header (shifted right to avoid overlap)
    const char* marketTitle = (g_currentLocation == 1) ? "HIROHITO STATION MARKET" : 
                              (g_currentLocation == 2) ? "NAGAKO'S HALO MARKET" : 
                              "SHINJUKU DEPOT MARKET";
    int headerX = 270;
    DrawTextWithFont(marketTitle, headerX, 50, 15, YELLOW);
    
    // Draw [S]ELL indicator next to title
    int titleWidth = MeasureTextWithFont(marketTitle, 15);
    DrawTextWithFont("[S]ELL", headerX + titleWidth + 20, 50, 15, YELLOW);
    
    // Draw credits and cargo info
    char creditsText[64];
    snprintf(creditsText, sizeof(creditsText), "CREDITS: %d", G_Player.credits);
    DrawTextWithFont(creditsText, headerX, 90, 15, GREEN);
    
    // Draw [S]ell text
    int creditsWidth = MeasureTextWithFont(creditsText, 15);
    int charWidth = MeasureTextWithFont("M", 15);
    int sellX = headerX + creditsWidth + (charWidth * 7);
    DrawTextWithFont("[S]ELL", sellX, 90, 15, (Color){0, 255, 255, 255});
    
    // Draw cargo info with increased size (50% larger: 11 -> 16-17, using 17)
    int cargoFontSize = 17;  // 50% increase from 11
    char cargoText[64];
    snprintf(cargoText, sizeof(cargoText), "CARGO: %d/%d", G_Player.cargoFilled, G_Player.cargoSpace);
    DrawTextWithFont(cargoText, headerX, 120, cargoFontSize, (Color){0, 255, 255, 255});
    
    // Draw navigation instructions on row under CARGO in yellow (reduced by 2pt)
    const char* navText = "UP/DOWN: Navigate | [S]ELL";
    int navFontSize = cargoFontSize - 2;  // Reduced by 2pt (17 -> 15)
    int navY = 120 + cargoFontSize + 5;  // Row under CARGO
    DrawTextWithFont(navText, headerX, navY, navFontSize, YELLOW);
    
    // Draw commodities list (moved 5% down)
    int navHeight = navFontSize + 5;
    int baseStartY = navY + navHeight + 10;
    int startY = baseStartY + (int)(baseStartY * 0.05f);  // Move 5% down
    int lineHeight = 30;
    int maxVisible = NUM_COMMODITIES;  // Show all commodities, no scrolling

    int nameFontSize = 15;
    
    // Helper function to get shortened commodity name for display
    auto getShortName = [](int idx) -> const char* {
        if (idx == 4) return "HELIUM-4 ISOTO...";  // ISOTOPES -> ISOTO...
        if (idx == 5) return "HYDROGEN ISOTO..."; // ISOTOPES -> ISOTO...
        if (idx == 10) return "PLASMATIC DIAM..."; // DIAMONDS -> DIAM...
        return g_commodityNames[idx];
    };
    
    int maxNameWidth = 0;
    for (int i = 0; i < NUM_COMMODITIES; i++) {
        const char* displayName = getShortName(i);
        int w = MeasureTextWithFont(displayName, nameFontSize);
        if (w > maxNameWidth) maxNameWidth = w;
    }
    int nameX = headerX + 10;
    int priceGap = MeasureTextWithFont("MMMM", nameFontSize);  // Moved 1 character space to the right (was "MMM")
    int priceStartX = nameX + maxNameWidth + priceGap;
    
    int rectStartX = nameX - 15;
    int rectWidth = (priceStartX - nameX) + 110;
    
    for (int i = 0; i < NUM_COMMODITIES; i++) {
        int commIdx = i;
        
        int yPos = startY + (i * lineHeight);
        bool selected = (g_commoditiesMarketSelection == commIdx);
        
        // Highlight
        if (selected) {
            DrawRectangle(rectStartX, yPos - 2, rectWidth, lineHeight, (Color){100, 100, 150, 100});
            DrawRectangleLines(rectStartX, yPos - 2, rectWidth, lineHeight, YELLOW);
        }
        
        // Name (format: "NAME:##" without space before colon, with shortened names)
        const char* displayName = getShortName(commIdx);
        char commText[128];
        snprintf(commText, sizeof(commText), "%s:%d", displayName, G_Player.inventory[commIdx]);
        Color textColor = (G_Player.inventory[commIdx] > 0) ? WHITE : GRAY;
        DrawTextWithFont(commText, nameX, yPos, nameFontSize, textColor);
        
        // Price
        char priceText[64];
        snprintf(priceText, sizeof(priceText), "%dcr", buyPrices[commIdx]);
        DrawTextWithFont(priceText, priceStartX, yPos, nameFontSize, (G_Player.inventory[commIdx] > 0) ? GREEN : GRAY);
    }
    
    // Back Option (moved down 30px)
    int backY = startY + (maxVisible * lineHeight) + 50;  // Was +20, now +50 (30px down)
    bool backSelected = (g_commoditiesMarketSelection == NUM_COMMODITIES);
    if (backSelected) {
        DrawRectangle(rectStartX, backY - 2, rectWidth, lineHeight, (Color){100, 100, 150, 100});
        DrawRectangleLines(rectStartX, backY - 2, rectWidth, lineHeight, YELLOW);
    }
    DrawTextWithFont("[BACK]", nameX, backY, nameFontSize, backSelected ? YELLOW : WHITE);
}




// ------------------------------------------------------------
// RENDER: SHIPYARD SHOP (6 shop items arranged like asteroids)
// ------------------------------------------------------------
void RenderShipyardShop() {
    // Initialize render texture if needed
    if (!g_shipyardShopViewportInitialized) {
        g_shipyardShopViewport = LoadRenderTexture(RENDER_WIDTH, RENDER_HEIGHT);
        g_shipyardShopViewportInitialized = true;
    }
    
    // Rotation update disabled - using static PNG background instead of 3D models
    /*
    // Update rotation (same ping-pong effect as asteroids)
    float dt = GetFrameTime();
    static float rotationDir = 1.0f;
    g_shopItemRotation += 30.0f * dt * rotationDir;
    
    if (g_shopItemRotation > 45.0f) {
        g_shopItemRotation = 45.0f;
        rotationDir = -1.0f;
    } else if (g_shopItemRotation < -45.0f) {
        g_shopItemRotation = -45.0f;
        rotationDir = 1.0f;
    }
    */
    
    // Render to texture
    BeginTextureMode(g_shipyardShopViewport);
    
    // Select appropriate upgrade PNG based on location
    Texture2D* upgradeBgTx = NULL;
    if (g_currentLocation == 1) {  // Station (Hirohito)
        upgradeBgTx = &upgradesHirohitoTx;
    } else if (g_currentLocation == 2) {  // Halo (Nagako)
        upgradeBgTx = &upgradesNagakoTx;
    } else {  // Depot (Shinjuku) - default
        upgradeBgTx = &upgradesShinjukuTx;
    }
    
    // Draw background texture if loaded, otherwise clear black
    if (upgradeBgTx && upgradeBgTx->id > 0) {
        Rectangle srcRect = { 0, 0, (float)upgradeBgTx->width, (float)upgradeBgTx->height };
        Rectangle destRect = { 0, 0, (float)RENDER_WIDTH, (float)RENDER_HEIGHT };
        DrawTexturePro(*upgradeBgTx, srcRect, destRect, (Vector2){0,0}, 0.0f, WHITE);
    } else {
        ClearBackground(BLACK);
    }
    
    // 3D Model and Text Rendering Disabled - Using static PNG background
    /*
    // Setup camera for 3D rendering (same as asteroids)
    Camera3D shopCamera = {0};
    shopCamera.position = (Vector3){0, 0, 15};
    shopCamera.target = (Vector3){0, 0, 0};
    shopCamera.up = (Vector3){0, 1, 0};
    shopCamera.fovy = 45.0f;
    shopCamera.projection = CAMERA_PERSPECTIVE;
    
    // Use centered positions: three on top, three on bottom
    // Same layout as asteroids
    Vector3 shopItemPositions[6] = {
        {-3.0f, 3.0f, 0},   // Item A (top left)
        {0.0f,  3.0f, 0},   // Item B (top middle)
        {3.0f,  3.0f, 0},   // Item C (top right)
        {-3.0f, 0.2f, 0},   // Item D (bottom left)
        {0.0f,  0.2f, 0},   // Item E (bottom middle)
        {3.0f,  0.2f, 0}    // Item F (bottom right)
    };
    
    // Render shop items in 3D with custom models
    BeginMode3D(shopCamera);
    rlDisableBackfaceCulling();
    
    float scale = 0.95f;  // Slightly larger than asteroids but leaves room for labels
    Vector3 rotationAxis = {0, 1, 0};
    
    // Render each shop item with its custom model (location-specific)
    Model* modelsToUse = g_shopItemModels;  // Default to depot models
    if (g_currentLocation == 1) {  // Station
        modelsToUse = g_stationShopModels;
    } else if (g_currentLocation == 2) {  // Halo
        modelsToUse = g_haloShopModels;
    }
    
    for (int i = 0; i < 6; i++) {
        DrawModelEx(modelsToUse[i], shopItemPositions[i], rotationAxis, g_shopItemRotation * DEG2RAD, 
                   (Vector3){scale, scale, scale}, WHITE);
    }
    
    rlEnableBackfaceCulling();
    EndMode3D();
    
    // Draw text labels for each shop item using projected screen positions
    // Shop item names and prices (location-specific)
    const char* shopItemNames[6];
    int shopItemPrices[6];
    
    if (g_currentLocation == 1) {  // Station
        shopItemNames[0] = "[A] FUEL TANK UPGRADE";
        shopItemNames[1] = "[B] CARGO BLACK HOLE";
        shopItemNames[2] = "[C] FUEL";
        shopItemNames[3] = "[D] RED SHIP";
        shopItemNames[4] = "[E] GREEN SHIP";
        shopItemNames[5] = "[F] PURPLE SHIP";
        shopItemPrices[0] = 1500;  // Fuel Tank Upgrade
        shopItemPrices[1] = 2000;  // Cargo Black Hole
        shopItemPrices[2] = 60;    // Fuel (15% more expensive: 50 * 1.15 = 57.5, round to 60)
        shopItemPrices[3] = 5000;  // Red Ship
        shopItemPrices[4] = 8000;  // Green Ship
        shopItemPrices[5] = 10000; // Purple Ship
    } else if (g_currentLocation == 2) {  // Halo
        shopItemNames[0] = "[A] BETTER LASER";
        shopItemNames[1] = "[B] BETTER COLLECTOR";
        shopItemNames[2] = "[C] FUEL";
        shopItemNames[3] = "[D] TIME DISPLACEMENT DISKETTE";
        shopItemNames[4] = "[E] GREEN SHIP";
        shopItemNames[5] = "[F] PURPLE SHIP";
        shopItemPrices[0] = 300;   // Better Laser
        shopItemPrices[1] = 750;   // Better Collector
        shopItemPrices[2] = 60;    // Fuel (20% more expensive: 50 * 1.20 = 60)
        shopItemPrices[3] = 1000;   // Time Displacement Diskette
        shopItemPrices[4] = 8000;  // Green Ship
        shopItemPrices[5] = 10000; // Purple Ship
    } else {  // Depot (default)
        shopItemNames[0] = "[A] LASER";
        shopItemNames[1] = "[B] COLLECTOR";
        shopItemNames[2] = "[C] THRUSTER SYSTEMS & HARDWARE";
        shopItemNames[3] = "[D] EXO-PLATING";
        shopItemNames[4] = "[E] FUEL";
        shopItemNames[5] = "[F] REPAIRS";
        shopItemPrices[0] = 200;
        shopItemPrices[1] = 500;
        shopItemPrices[2] = 500;
        shopItemPrices[3] = 1000;
        shopItemPrices[4] = 50;
        shopItemPrices[5] = 400;  // REPAIRS - Repairs 10 Hull points for 400 credits
    }
    
    int fontSizeName = 6;
    int fontSizePrice = 5;
    int labelGap = 12;

    // Establish row baselines so text forms a tidy grid beneath each row
    Vector2 topRowPos = GetWorldToScreen(shopItemPositions[0], shopCamera);
    Vector2 bottomRowPos = GetWorldToScreen(shopItemPositions[3], shopCamera);
    int textYTopRow = (int)(topRowPos.y + labelGap);
    int textYBottomRow = (int)(bottomRowPos.y + labelGap);
    
    for (int i = 0; i < 6; i++) {
        Vector2 screenPos = GetWorldToScreen(shopItemPositions[i], shopCamera);
        int centerX = (int)screenPos.x;
        int textY = (i < 3) ? textYTopRow : textYBottomRow;
        
        // Shop item name
        int nameW = MeasureTextWithFont(shopItemNames[i], fontSizeName);
        DrawTextWithFont(shopItemNames[i], centerX - nameW/2, textY, fontSizeName, WHITE);
        
        // Price
        char priceText[32];
        snprintf(priceText, sizeof(priceText), "PRICE: %d CR", shopItemPrices[i]);
        int priceW = MeasureTextWithFont(priceText, fontSizePrice);
        DrawTextWithFont(priceText, centerX - priceW/2, textY + 12, fontSizePrice, (Color){255, 255, 0, 255});  // Yellow
    }
    */
    
    EndTextureMode();
}

// ------------------------------------------------------------
// MODAL: ASTEROID LAUNCH CONFIRMATION
// ------------------------------------------------------------
void DrawAsteroidModal(GameState* state, int* menuSelection, Vector3* shipPos, Vector3* shipVel) {
    // Calculate fuel requirements once at the start of the function
    int requiredFuel = g_selectedAsteroidFuelCost / 2;  // Half fuel on launch
    bool hasEnoughFuel = (G_Player.fuel >= requiredFuel);
    
    // Modal data: Prospect and Gravity percentages (same as in RenderAsteroidProspects)
    int prospectScores[6] = {10, 22, 34, 46, 58, 70};
    int gravityScores[6] = {25, 38, 51, 64, 76, 88};
    
    // Handle ESC to close modal
    if (CustomIsKeyPressed(KEY_ESCAPE)) {
        g_showAsteroidModal = false;
        g_fuelCheckFailed = false;
        return;
    }
    
    // Handle modal navigation
    if (CustomIsKeyPressed(KEY_LEFT)) {
        g_modalSelection = 0;  // Launch
    }
    if (CustomIsKeyPressed(KEY_RIGHT)) {
        g_modalSelection = 1;  // Exit
    }
    
    // Handle selection
    if (CustomIsKeyPressed(KEY_ENTER) || CustomIsKeyPressed(KEY_SPACE)) {
        PlayTerminalTypeSound();
        if (g_modalSelection == 0 && hasEnoughFuel) {
            // Launch - fuel already checked above
            if (G_Player.fuel >= requiredFuel) {
                // Asteroid gravity and prosperity already stored when asteroid was selected
                
                // Deduct half the fuel cost
                G_Player.fuel -= requiredFuel;
                if (G_Player.fuel < 0) G_Player.fuel = 0;
                
                // Set mission in progress flag
                g_missionInProgress = true;
                
                // Update thrust power to match player power
                SHIP_THRUST_POWER = G_Player.power;
                
                // Launch - show GET READY screen first, then go to lander mode
                *shipPos = (Vector3){0, 60, -PROSPECT_PERIMETER};
                *shipVel = (Vector3){0, 0, 10};
                
                // Stabilize ship at launch start (reset pitch, roll, yaw, and horizontal velocity)
                g_shipPitch = 0.0f;
                g_shipRoll = 0.0f;
                g_shipYaw = 0.0f;
                shipVel->x = 0.0f;  // Zero horizontal X velocity
                shipVel->z = 10.0f; // Keep forward Z velocity for initial movement
                
                g_showAsteroidModal = false;
                g_fuelCheckFailed = false;
                g_wasInsideCylinder = false; // Reset beam-up sound flag for new mission
                
                // Play launch sequence sound when launching into 3D environment
                if (g_launchSequenceSound.frameCount > 0) {
                    SetSoundVolume(g_launchSequenceSound, 1.3f); // 30% louder
                    PlaySound(g_launchSequenceSound);
                }
                
                // Show GET READY splash screen
                g_showGetReady = true;
                g_getReadyTimer = 5.0f;  // Show for 5 seconds
                
                // Reset rocks (re-generate world for new asteroid) - completely fresh environment
                GenerateRocksAndCollision(); 
                InitCollisionGrid();
                
                // Clear all particles/debris for fresh start
                for (int i = 0; i < MAX_PARTICLES; i++) {
                    particles[i].life = 0.0f; // Kill all particles
                    particles[i].onGround = false;
                }
            } else {
                // Not enough fuel - close modal and show separate warning modal
                g_showAsteroidModal = false;  // Close asteroid selection modal
                g_fuelCheckFailed = true;
                g_showFuelWarningModal = true;
                g_fuelWarningTimer = 3.0f;  // Show for 3 seconds
            }
        } else {
            // Exit - close modal
            g_showAsteroidModal = false;
            g_fuelCheckFailed = false;
        }
    }
    
    // Get asteroid data - use the variables set when A-F key was pressed
    char asteroidName = 'A' + g_selectedAsteroidIndex;
    int prospect = g_selectedAsteroidProspect;  // Use the variable set when key was pressed
    int gravity = g_selectedAsteroidGravity;   // Use the variable set when key was pressed
    
    // Calculate required modal height based on content
    int fontSize = 17;
    int textStartY = 50;  // Top padding
    int lineSpacing = 30;
    // Check fuel status to determine how many lines we need
    int numTextLines = hasEnoughFuel ? 5 : 6;  // Title + 4 info lines, or +1 warning line
    int textBottomY = textStartY + (lineSpacing * (numTextLines - 1)) + fontSize;
    int buttonHeight = 50;
    int buttonSpacing = 50;  // Spacing between text and buttons
    int bottomPadding = 20;
    int requiredHeight = textBottomY + buttonSpacing + buttonHeight + bottomPadding;
    
    // Draw modal window (centered on screen)
    int modalWidth = 600;
    int modalHeight = (requiredHeight > 400) ? requiredHeight : 400;  // Use calculated height or minimum 400
    int modalX = (VIRTUAL_WIDTH - modalWidth) / 2;
    int modalY = (VIRTUAL_HEIGHT - modalHeight) / 2;
    
    DrawRetroWindow("ASTEROID LAUNCH", modalX, modalY, modalWidth, modalHeight, 15);
    
    // Draw asteroid name (centered, font size 17)
    char titleText[64];
    snprintf(titleText, sizeof(titleText), "ASTEROID %c", asteroidName);
    int textY = modalY + textStartY;
    int textWidth = MeasureTextWithFont(titleText, fontSize);
    int textX = modalX + (modalWidth - textWidth) / 2;
    DrawTextWithFont(titleText, textX, textY, fontSize, WHITE);
    
    // Draw fuel cost and current fuel (centered, font size 17)
    char fuelText[64];
    snprintf(fuelText, sizeof(fuelText), "FUEL REQUIRED: %d (HALF ON LAUNCH)", g_selectedAsteroidFuelCost);
    textY += lineSpacing;
    textWidth = MeasureTextWithFont(fuelText, fontSize);
    textX = modalX + (modalWidth - textWidth) / 2;
    DrawTextWithFont(fuelText, textX, textY, fontSize, (Color){0, 255, 255, 255});  // Cyan
    
    // Draw current fuel
    char currentFuelText[64];
    snprintf(currentFuelText, sizeof(currentFuelText), "CURRENT FUEL: %.0f", G_Player.fuel);
    textY += lineSpacing;
    textWidth = MeasureTextWithFont(currentFuelText, fontSize);
    textX = modalX + (modalWidth - textWidth) / 2;
    Color fuelColor = hasEnoughFuel ? GREEN : RED;
    DrawTextWithFont(currentFuelText, textX, textY, fontSize, fuelColor);
    
    // Show insufficient fuel warning if needed
    if (!hasEnoughFuel) {
        textY += lineSpacing;
        char warningText[64] = "INSUFFICIENT FUEL!";
        textWidth = MeasureTextWithFont(warningText, fontSize);
        textX = modalX + (modalWidth - textWidth) / 2;
        DrawTextWithFont(warningText, textX, textY, fontSize, RED);
        textBottomY = textY + fontSize;  // Update bottom position
    }
    
    // Draw prospect percentage (centered, font size 17)
    char prospectText[64];
    snprintf(prospectText, sizeof(prospectText), "PROSPECT: %d%%", prospect);
    textY += lineSpacing;
    textWidth = MeasureTextWithFont(prospectText, fontSize);
    textX = modalX + (modalWidth - textWidth) / 2;
    DrawTextWithFont(prospectText, textX, textY, fontSize, GREEN);
    
    // Draw gravity percentage (centered, font size 17)
    char gravityText[64];
    snprintf(gravityText, sizeof(gravityText), "GRAVITY: %d%%", gravity);
    textY += lineSpacing;
    textWidth = MeasureTextWithFont(gravityText, fontSize);
    textX = modalX + (modalWidth - textWidth) / 2;
    textBottomY = textY + fontSize;  // Actual bottom of text (Y position + font height)
    DrawTextWithFont(gravityText, textX, textY, fontSize, (Color){0, 255, 255, 255});  // Cyan
    
    // Note: Fuel warning is now shown in a separate modal (drawn on top of everything)
    
    // Draw Launch and Exit buttons - use universal rule: fixed 25px from bottom edge
    int buttonWidth = 200;
    // Universal rule: buttons positioned 25px from bottom edge of modal
    int buttonY = CalculateModalButtonY(modalY, modalHeight, buttonHeight);
    int launchX = modalX + (modalWidth / 2) - buttonWidth - 20;
    int exitX = modalX + (modalWidth / 2) + 20;
    
    // Launch button - greyed out if insufficient fuel
    bool launchSelected = (g_modalSelection == 0);
    if (!hasEnoughFuel) {
        // Grey out launch button and prevent selection
        DrawButton("LAUNCH", launchX, buttonY, buttonWidth, buttonHeight, false);
        // Draw grey overlay
        DrawRectangle(launchX, buttonY, buttonWidth, buttonHeight, (Color){100, 100, 100, 150});
        // If launch was selected, force selection to Exit
        if (g_modalSelection == 0) {
            g_modalSelection = 1;
        }
    } else {
        DrawButton("LAUNCH", launchX, buttonY, buttonWidth, buttonHeight, launchSelected);
    }
    
    // Exit button
    bool exitSelected = (g_modalSelection == 1);
    DrawButton("EXIT", exitX, buttonY, buttonWidth, buttonHeight, exitSelected);
}

// ------------------------------------------------------------
// MODAL: SHIPYARD SHOP PURCHASE
// ------------------------------------------------------------
// Helper function to round percentage down to nearest 10%
static int RoundDownToNearest10(float percent) {
    return ((int)(percent / 10.0f)) * 10;
}

void DrawShopPurchaseModal(GameState* state, int* menuSelection) {
    // Shop item data (location-specific)
    const char* shopItemNames[6];
    int shopItemPrices[6];
    const char* shopItemDescriptions[6];
    
    if (g_currentLocation == 1) {  // Station
        shopItemNames[0] = "[A] FUEL TANK UPGRADE";
        shopItemNames[1] = "[B] CARGO BLACK HOLE";
        shopItemNames[2] = "[C] FUEL";
        shopItemNames[3] = "[D] RED SHIP";
        shopItemNames[4] = "[E] GREEN SHIP";
        shopItemNames[5] = "[F] PURPLE SHIP";
        shopItemPrices[0] = 1500;
        shopItemPrices[1] = 2000;
        shopItemPrices[2] = 60;
        shopItemPrices[3] = 5000;
        shopItemPrices[4] = 8000;
        shopItemPrices[5] = 10000;
        shopItemDescriptions[0] = "INCREASES FUEL CAPACITY BY 50%";
        shopItemDescriptions[1] = "MICRO-BLACK HOLE INCREASES CARGO TO 50";
        shopItemDescriptions[2] = "SELLS FUEL IN ONE BARREL (1 BARREL = 10 FUEL)";
        shopItemDescriptions[3] = "RED SHIP: 10% BETTER EVERYTHING";
        shopItemDescriptions[4] = "GREEN SHIP: 20% BETTER EVERYTHING";
        shopItemDescriptions[5] = "PURPLE SHIP: 30% BETTER EVERYTHING";
    } else if (g_currentLocation == 2) {  // Halo
        shopItemNames[0] = "[A] BETTER LASER";
        shopItemNames[1] = "[B] BETTER COLLECTOR";
        shopItemNames[2] = "[C] FUEL";
        shopItemNames[3] = "[D] TIME DISPLACEMENT DISKETTE";
        shopItemNames[4] = "[E] GOLD SHIP";
        shopItemNames[5] = "[F] REPAIRS";
        shopItemPrices[0] = 300;
        shopItemPrices[1] = 750;
        shopItemPrices[2] = 60;
        shopItemPrices[3] = 1000;
        shopItemPrices[4] = 15000;
        shopItemPrices[5] = 250;
        shopItemDescriptions[0] = "ADVANCED LASER THAT BLASTS MORE ROCKS";
        shopItemDescriptions[1] = "IMPROVED COLLECTOR WITH BETTER EFFICIENCY";
        shopItemDescriptions[2] = "SELLS FUEL IN ONE BARREL (1 BARREL = 10 FUEL)";
        shopItemDescriptions[3] = "SAVES AT THIS POINT";
        shopItemDescriptions[4] = "GOLD SHIP: 50% BETTER EVERYTHING";
        shopItemDescriptions[5] = "REPAIRS 10 HULL POINTS";
    } else {  // Depot
        shopItemNames[0] = "[A] LASER";
        shopItemNames[1] = "[B] COLLECTOR";
        shopItemNames[2] = "[C] THRUSTER SYSTEMS & HARDWARE";
        shopItemNames[3] = "[D] EXO-PLATING";
        shopItemNames[4] = "[E] FUEL";
        shopItemNames[5] = "[F] REPAIRS";
        shopItemPrices[0] = 200;
        shopItemPrices[1] = 500;
        shopItemPrices[2] = 500;
        shopItemPrices[3] = 1000;
        shopItemPrices[4] = 50;
        shopItemPrices[5] = 400;  // REPAIRS - Repairs 10 Hull points for 400 credits
        shopItemDescriptions[0] = "FITS A LASER ALLOWING ASTEROIDS TO BE FIRED BY PRESSING SPACE";
        shopItemDescriptions[1] = "ENABLES LASERED DEBRIS TO ENTER THE CARGO OF THE SHIP";
        shopItemDescriptions[2] = "BOOSTS THE SHIP'S THRUST BY 8%";
        shopItemDescriptions[3] = "INCREASES HULL CAPACITY BY 10 POINTS";
        shopItemDescriptions[4] = "SELLS FUEL IN ONE BARREL (1 BARREL = 10 FUEL)";
        shopItemDescriptions[5] = "REPAIRS 10 HULL POINTS";
    }
    
    // Handle ESC to close modal
    if (CustomIsKeyPressed(KEY_ESCAPE)) {
        g_showShopModal = false;
        g_purchaseFailed = false;
        return;
    }
    
    // Handle modal navigation
    if (CustomIsKeyPressed(KEY_LEFT)) {
        g_shopModalSelection = 0;  // Purchase
    }
    if (CustomIsKeyPressed(KEY_RIGHT)) {
        g_shopModalSelection = 1;  // Exit
    }
    
    // Handle selection
    if (CustomIsKeyPressed(KEY_ENTER) || CustomIsKeyPressed(KEY_SPACE)) {
        PlayTerminalTypeSound();
        if (g_shopModalSelection == 0) {
            // Check conditions before purchase
            int price = shopItemPrices[g_selectedShopItemIndex];
            bool canPurchase = true;
            strncpy(g_purchaseFailReason, "INSUFFICIENT CREDITS", sizeof(g_purchaseFailReason));
            
            // Check purchase conditions (location-specific)
            if (G_Player.credits < price) {
                canPurchase = false;
                strncpy(g_purchaseFailReason, "INSUFFICIENT CREDITS", sizeof(g_purchaseFailReason));
            } else if (g_currentLocation == 1) {  // Station
                if (g_selectedShopItemIndex == 0 && G_Player.hasFuelTankUpgrade) {
                    canPurchase = false;
                    strncpy(g_purchaseFailReason, "FUEL TANK ALREADY UPGRADED", sizeof(g_purchaseFailReason));
                } else if (g_selectedShopItemIndex == 1 && G_Player.hasCargoBlackHole) {
                    canPurchase = false;
                    strncpy(g_purchaseFailReason, "CARGO BLACK HOLE ALREADY INSTALLED", sizeof(g_purchaseFailReason));
                } else if (g_selectedShopItemIndex == 2 && G_Player.fuel >= G_Player.maxFuel) {
                    canPurchase = false;
                    strncpy(g_purchaseFailReason, "FUEL TANK FULL", sizeof(g_purchaseFailReason));
                } else if (g_selectedShopItemIndex >= 3 && g_selectedShopItemIndex <= 5) {
                    // Ships - can always purchase (replaces current ship)
                }
            } else if (g_currentLocation == 2) {  // Halo
                if (g_selectedShopItemIndex == 0 && G_Player.hasBetterLaser) {
                    canPurchase = false;
                    strncpy(g_purchaseFailReason, "BETTER LASER ALREADY FITTED", sizeof(g_purchaseFailReason));
                } else if (g_selectedShopItemIndex == 1 && G_Player.hasBetterCollector) {
                    canPurchase = false;
                    strncpy(g_purchaseFailReason, "BETTER COLLECTOR ALREADY FITTED", sizeof(g_purchaseFailReason));
                } else if (g_selectedShopItemIndex == 2 && G_Player.fuel >= G_Player.maxFuel) {
                    canPurchase = false;
                    strncpy(g_purchaseFailReason, "FUEL TANK FULL", sizeof(g_purchaseFailReason));
                } else if (g_selectedShopItemIndex == 4) {
                    // Gold Ship - can always purchase (replaces current ship)
                } else if (g_selectedShopItemIndex == 5 && G_Player.hull >= G_Player.maxHull) {
                    canPurchase = false;
                    strncpy(g_purchaseFailReason, "HULL IS FULLY REPAIRED", sizeof(g_purchaseFailReason));
                }
            } else {  // Depot
                if (g_selectedShopItemIndex == 0 && G_Player.hasLaser) {
                canPurchase = false;
                strncpy(g_purchaseFailReason, "LASER ALREADY FITTED", sizeof(g_purchaseFailReason));
                } else if (g_selectedShopItemIndex == 1 && G_Player.hasCollector) {
                canPurchase = false;
                strncpy(g_purchaseFailReason, "COLLECTOR ALREADY FITTED", sizeof(g_purchaseFailReason));
                } else if (g_selectedShopItemIndex == 5 && G_Player.hull >= G_Player.maxHull) {
                canPurchase = false;
                strncpy(g_purchaseFailReason, "HULL IS FULLY REPAIRED", sizeof(g_purchaseFailReason));
                } else if (g_selectedShopItemIndex == 4 && G_Player.fuel >= G_Player.maxFuel) {
                canPurchase = false;
                strncpy(g_purchaseFailReason, "FUEL TANK FULL", sizeof(g_purchaseFailReason));
                }
            }
            
            if (canPurchase) {
                // Deduct credits
                G_Player.credits -= price;
                
                // Apply upgrade based on item and location
                if (g_currentLocation == 1) {  // Station
                    switch (g_selectedShopItemIndex) {
                        case 0:  // Fuel Tank Upgrade
                            G_Player.hasFuelTankUpgrade = true;
                            G_Player.maxFuel *= 1.5f;  // 50% increase
                            G_Player.fuel = G_Player.maxFuel;  // Fill to new max
                            break;
                        case 1:  // Cargo Black Hole
                            G_Player.hasCargoBlackHole = true;
                            G_Player.cargoSpace = 50;  // Increase to 50
                            break;
                        case 2:  // Fuel
                            G_Player.fuel += 10.0f;
                            if (G_Player.fuel > G_Player.maxFuel) G_Player.fuel = G_Player.maxFuel;
                            // Play fuel.wav sound at 100% volume when fuel is added
                            if (g_fuelSound.frameCount > 0) {
                                SetSoundVolume(g_fuelSound, 1.0f); // 100% volume
                                PlaySound(g_fuelSound);
                            }
                            break;
                        case 3:  // Red Ship (10% better)
                            G_Player.shipColor = 1;
                            // Apply 10% bonuses (rounded down to nearest 10% = 10%)
                            G_Player.maxFuel *= 1.1f;
                            G_Player.maxHull *= 1.1f;
                            G_Player.maxPower *= 1.1f;
                            G_Player.cargoSpace = (int)(G_Player.cargoSpace * 1.1f);
                            G_Player.thrusterBoost *= 1.1f;
                            G_Player.hullResistance *= 0.9f;  // 10% less damage
                            G_Player.fuel = G_Player.maxFuel;
                            G_Player.hull = G_Player.maxHull;
                            break;
                        case 4:  // Green Ship (20% better)
                            G_Player.shipColor = 2;
                            // Apply 20% bonuses
                            G_Player.maxFuel *= 1.2f;
                            G_Player.maxHull *= 1.2f;
                            G_Player.maxPower *= 1.2f;
                            G_Player.cargoSpace = (int)(G_Player.cargoSpace * 1.2f);
                            G_Player.thrusterBoost *= 1.2f;
                            G_Player.hullResistance *= 0.8f;  // 20% less damage
                            G_Player.fuel = G_Player.maxFuel;
                            G_Player.hull = G_Player.maxHull;
                            break;
                        case 5:  // Purple Ship (30% better)
                            G_Player.shipColor = 3;
                            // Apply 30% bonuses
                            G_Player.maxFuel *= 1.3f;
                            G_Player.maxHull *= 1.3f;
                            G_Player.maxPower *= 1.3f;
                            G_Player.cargoSpace = (int)(G_Player.cargoSpace * 1.3f);
                            G_Player.thrusterBoost *= 1.3f;
                            G_Player.hullResistance *= 0.7f;  // 30% less damage
                            G_Player.fuel = G_Player.maxFuel;
                            G_Player.hull = G_Player.maxHull;
                            break;
                    }
                } else if (g_currentLocation == 2) {  // Halo
                    switch (g_selectedShopItemIndex) {
                        case 0:  // Better Laser
                            G_Player.hasBetterLaser = true;
                            G_Player.hasLaser = true;  // Also grants basic laser
                            break;
                        case 1:  // Better Collector
                            G_Player.hasBetterCollector = true;
                            G_Player.hasCollector = true;  // Also grants basic collector
                            break;
                        case 2:  // Fuel
                            G_Player.fuel += 10.0f;
                            if (G_Player.fuel > G_Player.maxFuel) G_Player.fuel = G_Player.maxFuel;
                            // Play fuel.wav sound at 100% volume when fuel is added
                            if (g_fuelSound.frameCount > 0) {
                                SetSoundVolume(g_fuelSound, 1.0f); // 100% volume
                                PlaySound(g_fuelSound);
                            }
                            break;
                        case 3:  // Time Displacement Diskette (Save Game)
                            SaveGame();  // Save the game state
                            break;
                        case 4:  // Gold Ship (50% better)
                            G_Player.shipColor = 4;  // Gold ship color
                            // Apply 50% bonuses
                            G_Player.maxFuel *= 1.5f;
                            G_Player.maxHull *= 1.5f;
                            G_Player.maxPower *= 1.5f;
                            G_Player.cargoSpace = (int)(G_Player.cargoSpace * 1.5f);
                            G_Player.thrusterBoost *= 1.5f;
                            G_Player.hullResistance *= 0.5f;  // 50% less damage
                            G_Player.fuel = G_Player.maxFuel;
                            G_Player.hull = G_Player.maxHull;
                            break;
                        case 5:  // Repairs (10 hull points)
                            G_Player.hull += 10.0f;
                            if (G_Player.hull > G_Player.maxHull) G_Player.hull = G_Player.maxHull;
                            break;
                    }
                } else {  // Depot
                switch (g_selectedShopItemIndex) {
                    case 0:  // LASER
                        G_Player.hasLaser = true;
                        break;
                    case 1:  // COLLECTOR
                        G_Player.hasCollector = true;
                        break;
                    case 2: { // THRUSTER SYSTEMS & HARDWARE - Increases thruster boost and power capacity
                            // Multiply thruster boost (allows stacking if purchased multiple times)
                            G_Player.thrusterBoost *= 1.08f;
                            // Increase power to reflect thruster upgrade (+8 power for 8% boost)
                            float powerIncrease = 8.0f;
                            G_Player.power += powerIncrease;
                            // Also increase maxPower to reflect the upgrade
                            G_Player.maxPower += powerIncrease;
                            // Ensure power doesn't exceed maxPower
                            if (G_Player.power > G_Player.maxPower) G_Player.power = G_Player.maxPower;
                            // Update SHIP_THRUST_POWER to match current power
                            SHIP_THRUST_POWER = G_Player.power;
                        break;
                    }
                    case 3:  // EXO-PLATING - Increases max hull by 10 points (repeatable)
                            G_Player.maxHull += 10.0f;
                            // Also apply current hull increase if hull is at max
                            if (G_Player.hull >= G_Player.maxHull - 10.0f) {
                                G_Player.hull = G_Player.maxHull;
                            }
                        break;
                    case 4:  // FUEL
                            G_Player.fuel += 10.0f;
                        if (G_Player.fuel > G_Player.maxFuel) G_Player.fuel = G_Player.maxFuel;
                        // Play fuel.wav sound at 100% volume when fuel is added
                        if (g_fuelSound.frameCount > 0) {
                            SetSoundVolume(g_fuelSound, 1.0f); // 100% volume
                            PlaySound(g_fuelSound);
                        }
                        break;
                    case 5:  // REPAIRS - Repairs 10 hull points
                            G_Player.hull += 10.0f;
                        if (G_Player.hull > G_Player.maxHull) G_Player.hull = G_Player.maxHull;
                        break;
                    }
                }
                
                // Play fixing-on.wav sound at 100% volume when upgrade is purchased
                if (g_fixingOnSound.frameCount > 0) {
                    SetSoundVolume(g_fixingOnSound, 1.0f); // 100% volume
                    PlaySound(g_fixingOnSound);
                }
                
                g_showShopModal = false;
                g_purchaseFailed = false;
            } else {
                // Cannot purchase - show warning
                g_purchaseFailed = true;
            }
        } else {
            // Exit - close modal
            g_showShopModal = false;
            g_purchaseFailed = false;
        }
    }
    
    // Get shop item data
    char itemName = 'A' + g_selectedShopItemIndex;
    const char* itemNameStr = shopItemNames[g_selectedShopItemIndex];
    int price = shopItemPrices[g_selectedShopItemIndex];
    const char* description = shopItemDescriptions[g_selectedShopItemIndex];
    
    // Draw modal window (centered on screen) - start with base height
    int modalWidth = 600;
    int modalHeight = g_purchaseFailed ? 500 : 400;  // Base height
    int modalX = (VIRTUAL_WIDTH - modalWidth) / 2;
    int modalY = (VIRTUAL_HEIGHT - modalHeight) / 2;
    
    DrawRetroWindow("SHIPYARD SHOP", modalX, modalY, modalWidth, modalHeight, 15);
    
    // Draw item name - use itemNameStr directly (already has [A] format)
    int titleW = MeasureTextWithFont(itemNameStr, 19);
    DrawTextWithFont(itemNameStr, modalX + (modalWidth - titleW) / 2, modalY + 50, 19, WHITE);
    
    // Draw price
    char priceText[64];
    snprintf(priceText, sizeof(priceText), "PRICE: %d CREDITS", price);
    int priceW = MeasureTextWithFont(priceText, 15);
    DrawTextWithFont(priceText, modalX + (modalWidth - priceW) / 2, modalY + 120, 15, (Color){255, 255, 0, 255});  // Yellow
    
    // Draw description (centered, word-wrapped using helper function)
    int fontSizeDesc = 12;
    int maxDescWidth = modalWidth - 100; // Increased padding to prevent overlap
    int textY = modalY + 170;
    int textBottomY = textY;
    DrawWordWrappedText(description, modalX + 50, textY, maxDescWidth, fontSizeDesc, WHITE, &textBottomY);
    
    // Draw warning if purchase failed (positioned below description)
    int warningBottomY = textBottomY;
    if (g_purchaseFailed) {
        int warningY = textBottomY + 20;
        warningBottomY = warningY;
        DrawWordWrappedText(g_purchaseFailReason, modalX + 50, warningY, maxDescWidth, 18, RED, &warningBottomY);
    }
    
    // Position buttons - use universal rule: fixed 25px from bottom edge
    int buttonHeight = 50;
    // Universal rule: buttons positioned 25px from bottom edge of modal
    int buttonY = CalculateModalButtonY(modalY, modalHeight, buttonHeight);
    
    // Ensure modal height accommodates buttons (universal rule)
    int requiredHeight = CalculateRequiredModalHeight(warningBottomY - modalY, buttonHeight);
    if (requiredHeight > modalHeight) {
        modalHeight = requiredHeight;
        modalY = (VIRTUAL_HEIGHT - modalHeight) / 2;
        DrawRetroWindow("SHIPYARD SHOP", modalX, modalY, modalWidth, modalHeight, 15);
        // Redraw all content at new positions
        titleW = MeasureTextWithFont(itemNameStr, 19);
        DrawTextWithFont(itemNameStr, modalX + (modalWidth - titleW) / 2, modalY + 50, 19, WHITE);
        DrawTextWithFont(priceText, modalX + (modalWidth - priceW) / 2, modalY + 120, 15, (Color){255, 255, 0, 255});
        textY = modalY + 170;
        textBottomY = textY;
        DrawWordWrappedText(description, modalX + 50, textY, maxDescWidth, fontSizeDesc, WHITE, &textBottomY);
        if (g_purchaseFailed) {
            int warningY = textBottomY + 20;
            warningBottomY = warningY;
            DrawWordWrappedText(g_purchaseFailReason, modalX + 50, warningY, maxDescWidth, 18, RED, &warningBottomY);
        }
        buttonY = CalculateModalButtonY(modalY, modalHeight, buttonHeight);
    }
    
    // Draw Purchase and Exit buttons
    int buttonWidth = 200;
    int purchaseX = modalX + (modalWidth / 2) - buttonWidth - 20;
    int exitX = modalX + (modalWidth / 2) + 20;
    
    // Purchase button
    bool purchaseSelected = (g_shopModalSelection == 0);
    DrawButton("PURCHASE", purchaseX, buttonY, buttonWidth, buttonHeight, purchaseSelected);
    
    // Exit button
    bool exitSelected = (g_shopModalSelection == 1);
    DrawButton("EXIT", exitX, buttonY, buttonWidth, buttonHeight, exitSelected);
}

// ------------------------------------------------------------
// BAR LOGIC
// ------------------------------------------------------------
void CheckBarEvents() {
    // Initialize drunk threshold on first drink if not set
    if (g_drunkThreshold == 0 && g_barDrinksPurchased == 0) {
        g_drunkThreshold = GetRandomValue(5, 10);  // Random threshold between 5-10 drinks
        printf("[CheckBarEvents] Drunk threshold set to %d drinks\n", g_drunkThreshold);
    }
    
    // Check for negative effects when reaching the random threshold
    if (g_barDrinksPurchased >= g_drunkThreshold && !g_isDrunk) {
        // Player is drunk! (100% chance when threshold is reached)
        g_isDrunk = true;
        g_drunkGravityIncrease = GetRandomValue(10, 30);  // 10-30% increase (hungover effect)
        
        // Apply gravity increase to ALL asteroids at current location
        int* gravityScores;
        if (g_currentLocation == 1) {  // Station
            gravityScores = g_stationGravityScores;
        } else if (g_currentLocation == 2) {  // Halo
            gravityScores = g_haloGravityScores;
        } else {  // Depot
            gravityScores = g_gravityScores;
        }
        
        // Increase gravity for all asteroids
        for (int i = 0; i < 6; i++) {
            int oldGravity = gravityScores[i];
            gravityScores[i] = (int)(gravityScores[i] * (1.0f + g_drunkGravityIncrease / 100.0f));
            if (gravityScores[i] > 100) gravityScores[i] = 100;  // Cap at 100%
        }
        
        snprintf(g_drunkText, sizeof(g_drunkText),
            "YOU'RE DRUNK!\n\n"
            "AFTER ONE TOO MANY DRINKS, YOUR PERCEPTION OF GRAVITY HAS BEEN AFFECTED.\n\n"
            "GRAVITY INCREASED EVERYWHERE BY %d%%!\n\n"
            "THIS EFFECT WILL RESET WHEN YOU LAUNCH INTO SPACE.", g_drunkGravityIncrease);
        g_showDrunkModal = true;
        printf("[CheckBarEvents] Player is drunk! Gravity increased by %d%%\n", g_drunkGravityIncrease);
        }
    
    if (g_barDrinksPurchased >= 5) {
        // Reset drink counter
        g_barDrinksPurchased = 0; 
        
        // Select random asteroid A-C (indices 0-2)
        int asteroidIdx = GetRandomValue(0, 2); 
        char asteroidChar = 'A' + asteroidIdx;
        
        // Randomly choose between gravity deduction or prosperity increase
        bool isGravityReward = (GetRandomValue(0, 1) == 0);
        
        if (isGravityReward) {
            // Reduce gravity 8-20% - use location-specific gravity scores
            int reduction = GetRandomValue(8, 20);
            float factor = 1.0f - (reduction / 100.0f);
            
            int* gravityScores;
            if (g_currentLocation == 1) {  // Station
                gravityScores = g_stationGravityScores;
            } else if (g_currentLocation == 2) {  // Halo
                gravityScores = g_haloGravityScores;
            } else {  // Depot
                gravityScores = g_gravityScores;
            }
            
            int oldGravity = gravityScores[asteroidIdx];
            gravityScores[asteroidIdx] = (int)(gravityScores[asteroidIdx] * factor);
            int newGravity = gravityScores[asteroidIdx];
            
            snprintf(g_barSuccessText, sizeof(g_barSuccessText), 
                "AFTER A HEAVY DRINKING SESSION WITH SOME OF THE SPACERS AND FELLOW MINERS, "
                "ONE OF THE GUYS LETS SLIP OF A SECRET GRAVITY WELL OPERATING ON ASTEROID %c.\n\n"
                "GRAVITY REDUCED FROM %d%% TO %d%%!", asteroidChar, oldGravity, newGravity);
        } else {
            // Increase prosperity 5-15% - use location-specific prospect scores
            int increase = GetRandomValue(5, 15);
            
            int* prospectScores;
            if (g_currentLocation == 1) {  // Station
                prospectScores = g_stationProspectScores;
            } else if (g_currentLocation == 2) {  // Halo
                prospectScores = g_haloProspectScores;
            } else {  // Depot
                prospectScores = g_prospectScores;
            }
            
            int oldProsperity = prospectScores[asteroidIdx];
            prospectScores[asteroidIdx] = prospectScores[asteroidIdx] + increase;
            // Cap at 100%
            if (prospectScores[asteroidIdx] > 100) {
                prospectScores[asteroidIdx] = 100;
            }
            int newProsperity = prospectScores[asteroidIdx];
            
            snprintf(g_barSuccessText, sizeof(g_barSuccessText), 
                "AFTER A HEAVY DRINKING SESSION WITH SOME OF THE SPACERS AND FELLOW MINERS, "
                "ONE OF THE GUYS SHARES VALUABLE MINING INSIGHTS ABOUT ASTEROID %c.\n\n"
                "PROSPERITY INCREASED FROM %d%% TO %d%%!", asteroidChar, oldProsperity, newProsperity);
        }
            
        // Show success modal immediately
        g_showBarSuccessModal = true;
    }
}

// ------------------------------------------------------------
// MODAL: EXIT TO MAIN MENU CONFIRMATION
// ------------------------------------------------------------
void DrawExitToMainMenuModal(GameState* state, int* menuSelection) {
    // Handle ESC to close modal
    if (CustomIsKeyPressed(KEY_ESCAPE)) {
        PlayTerminalTypeSound();
        g_showExitToMainMenuModal = false;
        g_exitModalSelection = 0; // Reset to YES
        return;
    }
    
    // Handle modal navigation
    if (CustomIsKeyPressed(KEY_LEFT)) {
        PlayTerminalTypeSound();
        g_exitModalSelection = 0;  // YES
    }
    if (CustomIsKeyPressed(KEY_RIGHT)) {
        PlayTerminalTypeSound();
        g_exitModalSelection = 1;  // NO
    }
    
    // Handle selection
    if (CustomIsKeyPressed(KEY_ENTER) || CustomIsKeyPressed(KEY_SPACE)) {
        PlayTerminalTypeSound();
        if (g_exitModalSelection == 0) {
            // YES - reset to beginning (splash screen)
            g_showExitToMainMenuModal = false;
            g_exitModalSelection = 0; // Reset
            ResetState(state, menuSelection, STATE_SPLASH);
        } else {
            // NO - close modal
            g_showExitToMainMenuModal = false;
            g_exitModalSelection = 0; // Reset to YES
        }
    }
    
    // Draw modal window (centered on screen)
    int modalWidth = 600;
    int modalHeight = 300;
    int modalX = (VIRTUAL_WIDTH - modalWidth) / 2;
    int modalY = (VIRTUAL_HEIGHT - modalHeight) / 2;
    
    DrawRetroWindow("EXIT TO MAIN MENU", modalX, modalY, modalWidth, modalHeight, 15);
    
    // Question text (with word wrapping support)
    const char* questionText = "EXIT TO MAIN MENU?";
    int maxTextWidth = modalWidth - 100; // Padding to prevent overlap
    int textY = modalY + 80;
    int textBottomY = textY;
    DrawWordWrappedText(questionText, modalX + 50, textY, maxTextWidth, 20, WHITE, &textBottomY);
    
    // Buttons - use universal rule to position inline with text
    int buttonWidth = 200;
    int buttonHeight = 50;
    // Universal rule: buttons positioned 25px from bottom edge of modal
    int buttonY = CalculateModalButtonY(modalY, modalHeight, buttonHeight);
    
    // Ensure modal height accommodates buttons (universal rule)
    int requiredHeight = CalculateRequiredModalHeight(textBottomY - modalY, buttonHeight, 80);
    if (requiredHeight > modalHeight) {
        modalHeight = requiredHeight;
        modalY = (VIRTUAL_HEIGHT - modalHeight) / 2;
        DrawRetroWindow("EXIT TO MAIN MENU", modalX, modalY, modalWidth, modalHeight, 15);
        // Redraw text at new position
        textY = modalY + 80;
        textBottomY = textY;
        DrawWordWrappedText(questionText, modalX + 50, textY, maxTextWidth, 20, WHITE, &textBottomY);
        buttonY = CalculateModalButtonY(modalY, modalHeight, buttonHeight);
    }
    int yesX = modalX + (modalWidth / 2) - buttonWidth - 20;
    int noX = modalX + (modalWidth / 2) + 20;
    
    bool yesSelected = (g_exitModalSelection == 0);
    bool noSelected = (g_exitModalSelection == 1);
    
    DrawButton("YES", yesX, buttonY, buttonWidth, buttonHeight, yesSelected);
    DrawButton("NO", noX, buttonY, buttonWidth, buttonHeight, noSelected);
}

// MODAL: WELCOME TO SHINJUKU STATION
void DrawWelcomeModal(GameState* state, int* menuSelection) {
    // Modal dimensions
    int modalWidth = 700;
    int modalHeight = 600;
    int modalX = (VIRTUAL_WIDTH - modalWidth) / 2;
    int modalY = (VIRTUAL_HEIGHT - modalHeight) / 2;
    
    // Handle ESC or ENTER/SPACE to close modal
    if (CustomIsKeyPressed(KEY_ESCAPE) || CustomIsKeyPressed(KEY_ENTER) || CustomIsKeyPressed(KEY_SPACE)) {
        PlayTerminalTypeSound();
        g_showWelcomeModal = false;
        return;
    }
    
    // Draw modal window - title font size matches body text
    DrawRetroWindow("WELCOME TO SHINJUKU STATION", modalX, modalY, modalWidth, modalHeight, 15);
    
    // Welcome text - centered and properly spaced
    int textStartY = modalY + 50;
    int lineHeight = 24;
    int fontSize = 12;  // Increased by 30% (was 9)
    int textCenterX = modalX + modalWidth / 2;
    int currentY = textStartY;
    
    // Title
    const char* titleText = "WELCOME TO SHINJUKU STATION, SPACER!";
    int titleW = MeasureTextWithFont(titleText, 19);  // Increased by 25% (was 15)
    DrawTextWithFont(titleText, textCenterX - titleW / 2, currentY, 19, (Color){0, 255, 255, 255}); // Cyan
    currentY += lineHeight + 8;
    
    // Tips - each line centered with specific colors
    const char* tips[] = {
        "YOU NEED A LASER AND A COLLECTOR TO MINE EFFECTIVELY.",
        "",
        "WHILE YOU CAN'T AFFORD TO UPGRADE YOUR THRUSTERS YET,",
        "MAKE SURE YOU CHOOSE AN ASTEROID WITH LOW GRAVITY.",
        "",
        "ASTEROIDS ARE ALWAYS MOVING, SO FUEL REQUIRED",
        "DISTANCES WILL ALWAYS BE CHANGING.",
        "",
        "HEAD TO AN ASTEROID ON THE PROSPECT MAP TO LAUNCH.",
        "",
        "GET VALUABLE GOSSIP AND ASTEROID DATA FROM",
        "THE DRUNK SPACERS IN THE BAR.",
        "",
        "COMMODITIES IS WHERE YOU SELL THE STUFF YOU COLLECT.",
        "",
        "BE CAREFUL WITH A FULL HULL - YOUR SHIP GETS HEAVY.",
        "",
        "OUT HERE IN THE OORT CLOUD IT'S DANGEROUS.",
        "",
        "ONCE YOU'RE DEAD... YOU'RE DEAD SPACER!"
    };
    
    // Color mapping for specific lines
    int numTips = sizeof(tips) / sizeof(tips[0]);
    for (int i = 0; i < numTips; i++) {
        if (strlen(tips[i]) > 0) {
            int lineW = MeasureTextWithFont(tips[i], fontSize);
            Color lineColor = WHITE; // Default color
            
            // Set colors for specific lines
            if (strstr(tips[i], "YOU NEED A LASER AND A COLLECTOR") != NULL) {
                lineColor = RED; // Red for laser/collector requirement
            } else if (strstr(tips[i], "HEAD TO AN ASTEROID ON THE PROSPECT MAP") != NULL) {
                lineColor = (Color){0, 255, 255, 255}; // Cyan for prospect map
            } else if (strstr(tips[i], "ONCE YOU'RE DEAD") != NULL) {
                lineColor = RED; // Bright red for death warning
            }
            
            // Center each line
            DrawTextWithFont(tips[i], textCenterX - lineW / 2, currentY, fontSize, lineColor);
            currentY += lineHeight;
        } else {
            // Empty line - smaller spacing
            currentY += lineHeight / 2;
        }
    }
    
    // OKAY button - use universal rule: fixed 25px from bottom edge
    int buttonWidth = 200;
    int buttonHeight = 50;
    // Universal rule: buttons positioned 25px from bottom edge of modal
    int buttonY = CalculateModalButtonY(modalY, modalHeight, buttonHeight);
    
    // Ensure modal height accommodates button (universal rule)
    int requiredHeight = CalculateRequiredModalHeight(currentY - modalY, buttonHeight, 50);
    if (requiredHeight > modalHeight) {
        modalHeight = requiredHeight;
        modalY = (VIRTUAL_HEIGHT - modalHeight) / 2;
        DrawRetroWindow("WELCOME TO SHINJUKU STATION", modalX, modalY, modalWidth, modalHeight, 15);
        // Redraw all text at new positions
        textStartY = modalY + 50;
        currentY = textStartY;
        titleW = MeasureTextWithFont(titleText, 19);
        DrawTextWithFont(titleText, textCenterX - titleW / 2, currentY, 19, (Color){0, 255, 255, 255});
        currentY += lineHeight + 8;
        for (int i = 0; i < numTips; i++) {
            if (strlen(tips[i]) > 0) {
                int lineW = MeasureTextWithFont(tips[i], fontSize);
                Color lineColor = WHITE;
                if (strstr(tips[i], "YOU NEED A LASER AND A COLLECTOR") != NULL) {
                    lineColor = RED;
                } else if (strstr(tips[i], "HEAD TO AN ASTEROID ON THE PROSPECT MAP") != NULL) {
                    lineColor = (Color){0, 255, 255, 255};
                } else if (strstr(tips[i], "ONCE YOU'RE DEAD") != NULL) {
                    lineColor = RED;
                }
                DrawTextWithFont(tips[i], textCenterX - lineW / 2, currentY, fontSize, lineColor);
                currentY += lineHeight;
            } else {
                currentY += lineHeight / 2;
            }
        }
        buttonY = CalculateModalButtonY(modalY, modalHeight, buttonHeight);
    }
    int buttonX = modalX + (modalWidth - buttonWidth) / 2;
    
    if (DrawButton("OKAY", buttonX, buttonY, buttonWidth, buttonHeight, true, 15)) {
        g_showWelcomeModal = false;
    }
}

// Helper function to draw word-wrapped text
// x, y: starting position
// maxWidth: maximum width for wrapping (text will be left-aligned within this width to prevent clipping)
// fontSize: font size for text
// color: text color
// outY: optional pointer to store final Y position
void DrawWordWrappedText(const char* text, int x, int y, int maxWidth, int fontSize, Color color, int* outY) {
    if (!text || strlen(text) == 0) {
        if (outY) *outY = y;
        return;
    }
    
    int currentY = y;
    int lineHeight = fontSize + 8; // Line height based on font size with spacing
    char currentLine[512] = {0};
    int currentLineLen = 0;
    int textLen = (int)strlen(text);
    int wordStart = 0;
    
    for (int i = 0; i <= textLen; i++) {
        char c = (i < textLen) ? text[i] : '\0';
        bool isSpace = (c == ' ' || c == '\t');
        bool isNewline = (c == '\n');
        bool isEnd = (i == textLen);
        
        // Process word when a delimiter is hit
        if (isSpace || isNewline || isEnd) {
            // Extract the word
            int wordLen = i - wordStart;
            if (wordLen > 0 && wordLen < 256) {
                char word[256];
                strncpy(word, &text[wordStart], wordLen);
                word[wordLen] = '\0';
                
                // Test if adding this word would exceed width
                char testLine[512];
                if (currentLineLen > 0) {
                    snprintf(testLine, sizeof(testLine), "%s %s", currentLine, word);
                } else {
                    strncpy(testLine, word, sizeof(testLine));
                }
                int testWidth = MeasureTextWithFont(testLine, fontSize);
                
                // If adding word exceeds maxWidth, wrap to next line
                if (testWidth > maxWidth && currentLineLen > 0) {
                    // Draw current line
                    DrawTextWithFont(currentLine, x, currentY, fontSize, color);
                    currentY += lineHeight;
                    currentLineLen = 0;
                    currentLine[0] = '\0';
                    
                    // Start new line with this word
                    strncpy(currentLine, word, sizeof(currentLine));
                    currentLineLen = wordLen;
                } else {
                    // Append word to current line
                    if (currentLineLen > 0 && currentLineLen < 510) {
                        currentLine[currentLineLen++] = ' ';
                    }
                    if (currentLineLen + wordLen < 511) {
                        strncpy(&currentLine[currentLineLen], word, wordLen);
                        currentLineLen += wordLen;
                    }
                    currentLine[currentLineLen] = '\0';
                }
            }
            
            // If we hit a newline or end, flush the current line
            if (isNewline || isEnd) {
                if (currentLineLen > 0) {
                    DrawTextWithFont(currentLine, x, currentY, fontSize, color);
                    currentY += lineHeight;
                    currentLineLen = 0;
                    currentLine[0] = '\0';
                } else if (isNewline) {
                    // Empty line (double newline)
                    currentY += lineHeight;
                }
            }
            
            wordStart = i + 1;
        }
    }
    
    if (outY) *outY = currentY;
}

// Handle bar modal input (called before drawing)
void HandleBarModalInput() {
    // Handle sub-modals first - they can be closed with ENTER/SPACE
    if (g_showBarRumorModal || g_showBarGoldCardModal || g_showBarGamblingModal || g_showBarScientistModal || g_showBarSuccessModal || g_showBarLaserUpgradeModal || g_showDrunkModal) {
        if (CustomIsKeyPressed(KEY_ENTER) || CustomIsKeyPressed(KEY_SPACE)) {
            PlayTerminalTypeSound();
            g_showBarRumorModal = false;
            g_showBarGoldCardModal = false;
            g_showBarGamblingModal = false;
            g_showBarScientistModal = false;
            g_showBarSuccessModal = false;
            g_showBarLaserUpgradeModal = false;
            g_showDrunkModal = false;
        }
        return; // Don't process main menu input when sub-modal is open
    }
    
    // Check for failsafe condition: no fuel and less than cheapest drink price for this location
    // Location 0 (Depot): cheapest = 5 (Astro Brew)
    // Location 1 (Station): cheapest = 5 (Astro Brew)
    // Location 2 (Halo): cheapest = 15 (Premium Drink)
    int cheapestDrinkPrice = (g_currentLocation == 2) ? 15 : 5;
    bool showFailsafeOption = (G_Player.fuel <= 0.0f && G_Player.credits < cheapestDrinkPrice);
    
    // Get menu options based on location - count conditional options
    int numOptions = 0;
    if (g_currentLocation == 1) {  // Station
        numOptions = 4; // Base: Buy Astro Brew, Take Space Shot, Try Your Luck, Leave Bar
        if (g_barVisitCounts[1] >= 3 && !g_barScientistUsed) {
            numOptions++; // Add Chat with Scientist
        }
        if (showFailsafeOption) {
            numOptions++; // Add Failsafe option
        }
    } else if (g_currentLocation == 2) {  // Halo
        numOptions = 3; // Base: Buy Premium Drink, Network with Traders, Leave Bar
        if (g_barVisitCounts[2] >= 3 && !g_barStoriesUsed) {
            numOptions++; // Add Listen to Stories
        }
        if (showFailsafeOption) {
            numOptions++; // Add Failsafe option
        }
    } else {  // Depot
        numOptions = 3; // Base: Buy Astro Brew, Take Space Shot, Leave Bar
        if (!G_Player.hasGoldCard) {
            numOptions++; // Add Drinks Are On Me!
        }
        if (g_barVisitCounts[0] >= 3 && !g_barLaserUpgradeUsed) {
            numOptions++; // Add Laser Upgrade option
        }
        if (showFailsafeOption) {
            numOptions++; // Add Failsafe option
        }
    }
    
    // Update max menu items to match current location
    g_barMaxMenuItems = numOptions;
    
    // Validate and fix menu selection before processing input
    if (g_barMenuSelection >= numOptions) {
        g_barMenuSelection = numOptions - 1;
    }
    if (g_barMenuSelection < 0) {
        g_barMenuSelection = 0;
    }
    
    // Navigation
    if (CustomIsKeyPressed(KEY_UP)) {
        PlayTerminalTypeSound();
        g_barMenuSelection--;
        if (g_barMenuSelection < 0) {
            g_barMenuSelection = numOptions - 1;
        }
    }
    if (CustomIsKeyPressed(KEY_DOWN)) {
        PlayTerminalTypeSound();
        g_barMenuSelection++;
        if (g_barMenuSelection >= numOptions) {
            g_barMenuSelection = 0;
        }
    }
    
    // Selection
    if (CustomIsKeyPressed(KEY_ENTER) || CustomIsKeyPressed(KEY_SPACE)) {
        // Ignore Enter key if bar was just opened (prevents accidental purchase)
        if (g_barJustOpened && CustomIsKeyPressed(KEY_ENTER)) {
            g_barJustOpened = false; // Clear flag for next frame
            return; // Don't process this Enter key press
        }
        
        // Clear the flag if Space is pressed (Space is always valid)
        if (CustomIsKeyPressed(KEY_SPACE)) {
            g_barJustOpened = false;
        }
        
        PlayTerminalTypeSound();
        
        // Validate selection is still in bounds before processing
        if (g_barMenuSelection < 0 || g_barMenuSelection >= numOptions) {
            return; // Invalid selection, don't process
        }
        
        // Clear flag after processing (Enter was intentionally pressed)
        g_barJustOpened = false;
        
        // Check for failsafe condition: no fuel and less than cheapest drink price for this location
        // Location 0 (Depot): cheapest = 5 (Astro Brew)
        // Location 1 (Station): cheapest = 5 (Astro Brew)
        // Location 2 (Halo): cheapest = 15 (Premium Drink)
        int cheapestDrinkPrice = (g_currentLocation == 2) ? 15 : 5;
        bool showFailsafeOption = (G_Player.fuel <= 0.0f && G_Player.credits < cheapestDrinkPrice);
        
        // Build menu structure to match selection index
        if (g_currentLocation == 1) {  // Station - Hirohito Station Bar
            int menuIdx = 0;
            if (g_barMenuSelection == menuIdx++) { // Buy Astro Brew
                if (G_Player.credits >= 5) {
                    G_Player.credits -= 5;
                    g_barDrinksPurchased++;
                    CheckBarEvents();
                }
            } else if (g_barMenuSelection == menuIdx++) { // Take Space Shot
                if (G_Player.credits >= 10) {
                    G_Player.credits -= 10;
                    g_barDrinksPurchased++;
                    CheckBarEvents();
                }
            } else if (g_barMenuSelection == menuIdx++) { // Try Your Luck
                if (G_Player.credits >= 50) {
                    G_Player.credits -= 50;
                    int winAmount = GetRandomValue(0, 200);
                    G_Player.credits += winAmount;
                    if (winAmount > 0) {
                        G_Player.totalCreditsEarned += winAmount;  // Track lifetime credits for rank
                        UpdateRank();  // Check for rank up after earning credits
                        snprintf(g_barGamblingText, sizeof(g_barGamblingText),
                            "YOU PLACE YOUR BET AND SPIN THE WHEEL...\n\n"
                            "LUCKY! YOU WON %d CREDITS!", winAmount);
                    } else {
                        snprintf(g_barGamblingText, sizeof(g_barGamblingText),
                            "YOU PLACE YOUR BET AND SPIN THE WHEEL...\n\n"
                            "BETTER LUCK NEXT TIME! YOU LOST 50 CREDITS.");
                    }
                    g_showBarGamblingModal = true;
                }
            } else if (g_barVisitCounts[1] >= 3 && !g_barScientistUsed && g_barMenuSelection == menuIdx++) { // Chat with Scientist
                int boostPercent = GetRandomValue(5, 15);
                float boostMultiplier = 1.0f + (boostPercent / 100.0f);
                G_Player.thrusterBoost *= boostMultiplier;
                g_barScientistUsed = true;
                snprintf(g_barScientistText, sizeof(g_barScientistText),
                    "YOU CHAT WITH A SCIENTIST ON THEIR WAY TO A RESEARCH STATION.\n\n"
                    "THEY SHARE SOME TIPS ON IMPROVING YOUR SHIP'S THRUSTERS.\n\n"
                    "THRUSTER BOOST INCREASED BY %d%%!", boostPercent);
                g_showBarScientistModal = true;
            } else if (showFailsafeOption && g_barMenuSelection == menuIdx++) { // Failsafe: Free Fuel
                // Give 1 barrel of fuel (10 fuel) for free
                G_Player.fuel += 10.0f;
                if (G_Player.fuel > G_Player.maxFuel) {
                    G_Player.fuel = G_Player.maxFuel;
                }
                // Play fuel sound if available
                if (g_fuelSound.frameCount > 0) {
                    SetSoundVolume(g_fuelSound, 1.0f);
                    PlaySound(g_fuelSound);
                }
                snprintf(g_barSuccessText, sizeof(g_barSuccessText),
                    "A CARING LOOKING FELLOW SPACER CALLS YOU OVER.\n\n"
                    "\"HEY, YOU LOOK LIKE YOU'RE IN A BIND. HERE, TAKE THIS FUEL.\"\n\n"
                    "YOU RECEIVE 1 BARREL OF FUEL (10 FUEL) FOR FREE!");
                g_showBarSuccessModal = true;
            } else if (g_barMenuSelection == numOptions - 1) { // Leave Bar
                g_showBarView = false;
                g_barJustOpened = false; // Clear flag when leaving bar
                g_barDrinksPurchased = 0;
                g_barMenuSelection = 0;
                g_depotHomePage = 1;
            }
        } else if (g_currentLocation == 2) {  // Halo - Nagako's Halo Bar
            int menuIdx = 0;
            if (g_barMenuSelection == menuIdx++) { // Buy Premium Drink
                if (G_Player.credits >= 15) {
                    G_Player.credits -= 15;
                    g_barDrinksPurchased++;
                    CheckBarEvents();
                }
            } else if (g_barMenuSelection == menuIdx++) { // Network with Traders
                if (G_Player.credits >= 100) {
                    G_Player.credits -= 100;
                    g_barDrinksPurchased++;
                    CheckBarEvents();
                }
            } else if (g_barVisitCounts[2] >= 3 && !g_barStoriesUsed && g_barMenuSelection == menuIdx++) { // Listen to Stories
                g_barDrinksPurchased++;
                g_barStoriesUsed = true;
                CheckBarEvents();
            } else if (showFailsafeOption && g_barMenuSelection == menuIdx++) { // Failsafe: Free Fuel
                // Give 1 barrel of fuel (10 fuel) for free
                G_Player.fuel += 10.0f;
                if (G_Player.fuel > G_Player.maxFuel) {
                    G_Player.fuel = G_Player.maxFuel;
                }
                // Play fuel sound if available
                if (g_fuelSound.frameCount > 0) {
                    SetSoundVolume(g_fuelSound, 1.0f);
                    PlaySound(g_fuelSound);
                }
                snprintf(g_barSuccessText, sizeof(g_barSuccessText),
                    "A CARING LOOKING FELLOW SPACER CALLS YOU OVER.\n\n"
                    "\"HEY, YOU LOOK LIKE YOU'RE IN A BIND. HERE, TAKE THIS FUEL.\"\n\n"
                    "YOU RECEIVE 1 BARREL OF FUEL (10 FUEL) FOR FREE!");
                g_showBarSuccessModal = true;
            } else if (g_barMenuSelection == numOptions - 1) { // Leave Bar
                g_showBarView = false;
                g_barJustOpened = false; // Clear flag when leaving bar
                g_barDrinksPurchased = 0;
                g_barMenuSelection = 0;
                g_depotHomePage = 1;
            }
        } else {  // Depot - The Astro Bar
            int menuIdx = 0;
            if (g_barMenuSelection == menuIdx++) { // Buy Astro Brew
                if (G_Player.credits >= 5) {
                    G_Player.credits -= 5;
                    g_barDrinksPurchased++;
                    CheckBarEvents();
                }
            } else if (g_barMenuSelection == menuIdx++) { // Take Space Shot
                if (G_Player.credits >= 10) {
                    G_Player.credits -= 10;
                    g_barDrinksPurchased++;
                    CheckBarEvents();
                }
            } else if (!G_Player.hasGoldCard && g_barMenuSelection == menuIdx++) { // Drinks Are On Me
                if (G_Player.credits >= 1000) {
                    G_Player.credits -= 1000;
                    G_Player.hasGoldCard = true;
                    g_showBarGoldCardModal = true;
                }
            } else if (g_barVisitCounts[0] >= 3 && !g_barLaserUpgradeUsed && g_barMenuSelection == menuIdx++) { // Laser Upgrade
                int increasePercent = GetRandomValue(5, 15);
                float oldMaxHeat = G_Player.maxLaserHeat;
                G_Player.maxLaserHeat += (oldMaxHeat * increasePercent / 100.0f);
                g_barLaserUpgradeUsed = true;
                snprintf(g_barLaserUpgradeText, sizeof(g_barLaserUpgradeText),
                    "YOU MEET AN ENGINEER WHO'S BEEN MODIFYING MINING EQUIPMENT.\n\n"
                    "THEY SHARE SOME ADVANCED COOLING TECHNIQUES FOR YOUR LASER.\n\n"
                    "LASER OVERHEAT THRESHOLD INCREASED BY %d%%!\n\n"
                    "(FROM %.0f TO %.0f)", increasePercent, oldMaxHeat, G_Player.maxLaserHeat);
                g_showBarLaserUpgradeModal = true;
            } else if (showFailsafeOption && g_barMenuSelection == menuIdx++) { // Failsafe: Free Fuel
                // Give 1 barrel of fuel (10 fuel) for free
                G_Player.fuel += 10.0f;
                if (G_Player.fuel > G_Player.maxFuel) {
                    G_Player.fuel = G_Player.maxFuel;
                }
                // Play fuel sound if available
                if (g_fuelSound.frameCount > 0) {
                    SetSoundVolume(g_fuelSound, 1.0f);
                    PlaySound(g_fuelSound);
                }
                snprintf(g_barSuccessText, sizeof(g_barSuccessText),
                    "A CARING LOOKING FELLOW SPACER CALLS YOU OVER.\n\n"
                    "\"HEY, YOU LOOK LIKE YOU'RE IN A BIND. HERE, TAKE THIS FUEL.\"\n\n"
                    "YOU RECEIVE 1 BARREL OF FUEL (10 FUEL) FOR FREE!");
                g_showBarSuccessModal = true;
            } else if (g_barMenuSelection == numOptions - 1) { // Leave Bar
                g_showBarView = false;
                g_barJustOpened = false; // Clear flag when leaving bar
                g_barDrinksPurchased = 0;
                g_barMenuSelection = 0;
                g_depotHomePage = 1;
            }
        }
    }
}

void DrawBarModal(int modalX, int modalY, int modalWidth, int modalHeight) {
    // Note: Input is now handled in DrawPageDepotHome() update phase, not here
    
    // Draw sub-modals - these take priority and block main menu
    if (g_showBarRumorModal) {
        DrawRetroWindow("RUMOR MILL", modalX, modalY, modalWidth, modalHeight, 15);
        // Center text on OK button - OK button is centered at modalX + modalWidth/2
        // Text should be centered within modalWidth - 100, starting at modalX + 50 (increased padding to prevent overlap)
        // Position text higher to avoid overlap with button
        int textY = modalY + 70;
        int textBottomY = textY;
        // Text increased by 25% (12 * 1.25 = 15)
        DrawWordWrappedText(g_barRumorText, modalX + 50, textY, modalWidth - 100, 15, WHITE, &textBottomY);
        // Universal rule: buttons positioned 25px from bottom edge of modal
        int buttonHeight = 50;
        int buttonY = CalculateModalButtonY(modalY, modalHeight, buttonHeight);
        // Ensure modal height accommodates button (universal rule)
        int requiredHeight = CalculateRequiredModalHeight(textBottomY - modalY, buttonHeight, 70);
        if (requiredHeight > modalHeight) {
            modalHeight = requiredHeight;
            modalY = (VIRTUAL_HEIGHT - modalHeight) / 2;
            DrawRetroWindow("RUMOR MILL", modalX, modalY, modalWidth, modalHeight, 15);
            textY = modalY + 70;
            textBottomY = textY;
            DrawWordWrappedText(g_barRumorText, modalX + 50, textY, modalWidth - 100, 15, WHITE, &textBottomY);
            buttonY = CalculateModalButtonY(modalY, modalHeight, buttonHeight);
        }
        DrawButton("OK", modalX + (modalWidth - 200)/2, buttonY, 200, 50, true, 15);
        return;
    }
    
    if (g_showBarGoldCardModal) {
        DrawRetroWindow("VIP ACCESS", modalX, modalY, modalWidth, modalHeight, 15);
        // Use word wrapping for all text to prevent overlap
        int textCenterX = modalX + modalWidth/2;
        int maxTextWidth = modalWidth - 100; // Padding to prevent overlap
        int currentY = modalY + 70;
        int textBottomY = currentY;
        
        // Title - use word wrapping in case it's too long - increased by 25% (15 * 1.25 = 18.75, round to 19)
        const char* titleText = "DRINKS ARE ON THE HOUSE!";
        DrawWordWrappedText(titleText, modalX + 50, currentY, maxTextWidth, 19, YELLOW, &textBottomY);
        currentY = textBottomY + 20;
        
        // Multi-line text with word wrapping - increased by 25% (12 * 1.25 = 15)
        const char* line1Text = "THE BAR ERUPTS IN CHEERS! A SHADY FIGURE APPROACHES YOU:";
        DrawWordWrappedText(line1Text, modalX + 50, currentY, maxTextWidth, 15, WHITE, &textBottomY);
        currentY = textBottomY + 15;
        
        const char* line2Text = "\"HERE'S A LITTLE SOMETHING FOR YOUR GENEROSITY...\"";
        DrawWordWrappedText(line2Text, modalX + 50, currentY, maxTextWidth, 15, WHITE, &textBottomY);
        currentY = textBottomY + 20;
        
        const char* cardText = "RECEIVED: COMMODITIES GOLD CARD";
        // Increased by 25% (14 * 1.25 = 17.5, round to 18)
        DrawWordWrappedText(cardText, modalX + 50, currentY, maxTextWidth, 18, GREEN, &textBottomY);
        currentY = textBottomY + 20;
        
        const char* bonusText = "(ALL COMMODITY SELL VALUES INCREASED BY 20%)";
        DrawWordWrappedText(bonusText, modalX + 50, currentY, maxTextWidth, 15, (Color){0, 255, 255, 255}, &textBottomY);
        
        // Universal rule: buttons positioned 25px from bottom edge of modal
        int buttonHeight = 50;
        int buttonY = CalculateModalButtonY(modalY, modalHeight, buttonHeight);
        // Ensure modal height accommodates button (universal rule)
        int requiredHeight = CalculateRequiredModalHeight(textBottomY - modalY, buttonHeight, 70);
        if (requiredHeight > modalHeight) {
            modalHeight = requiredHeight;
            modalY = (VIRTUAL_HEIGHT - modalHeight) / 2;
            DrawRetroWindow("VIP ACCESS", modalX, modalY, modalWidth, modalHeight, 15);
            // Redraw all text
            currentY = modalY + 70;
            textBottomY = currentY;
            DrawWordWrappedText(titleText, modalX + 50, currentY, maxTextWidth, 19, YELLOW, &textBottomY);
            currentY = textBottomY + 20;
            DrawWordWrappedText(line1Text, modalX + 50, currentY, maxTextWidth, 15, WHITE, &textBottomY);
            currentY = textBottomY + 15;
            DrawWordWrappedText(line2Text, modalX + 50, currentY, maxTextWidth, 15, WHITE, &textBottomY);
            currentY = textBottomY + 20;
            DrawWordWrappedText(cardText, modalX + 50, currentY, maxTextWidth, 18, GREEN, &textBottomY);
            currentY = textBottomY + 20;
            DrawWordWrappedText(bonusText, modalX + 50, currentY, maxTextWidth, 15, (Color){0, 255, 255, 255}, &textBottomY);
            buttonY = CalculateModalButtonY(modalY, modalHeight, buttonHeight);
        }
        DrawButton("AWESOME", modalX + (modalWidth - 200)/2, buttonY, 200, 50, true, 15);
        return;
    }
    
    if (g_showBarGamblingModal) {
        DrawRetroWindow("SPACE CASINO", modalX, modalY, modalWidth, modalHeight, 15);
        // Center text on OK button - OK button is centered at modalX + modalWidth/2
        // Text should be centered within modalWidth - 100, starting at modalX + 50 (increased padding to prevent overlap)
        // Position text higher to avoid overlap with button
        int textY = modalY + 70;
        int textBottomY = textY;
        // Text increased by 25% (12 * 1.25 = 15)
        DrawWordWrappedText(g_barGamblingText, modalX + 50, textY, modalWidth - 100, 15, WHITE, &textBottomY);
        // Universal rule: buttons positioned 25px from bottom edge of modal
        int buttonHeight = 50;
        int buttonY = CalculateModalButtonY(modalY, modalHeight, buttonHeight);
        // Ensure modal height accommodates button (universal rule)
        int requiredHeight = CalculateRequiredModalHeight(textBottomY - modalY, buttonHeight, 70);
        if (requiredHeight > modalHeight) {
            modalHeight = requiredHeight;
            modalY = (VIRTUAL_HEIGHT - modalHeight) / 2;
            DrawRetroWindow("SPACE CASINO", modalX, modalY, modalWidth, modalHeight, 15);
            textY = modalY + 70;
            textBottomY = textY;
            DrawWordWrappedText(g_barGamblingText, modalX + 50, textY, modalWidth - 100, 15, WHITE, &textBottomY);
            buttonY = CalculateModalButtonY(modalY, modalHeight, buttonHeight);
        }
        DrawButton("OK", modalX + (modalWidth - 200)/2, buttonY, 200, 50, true, 15);
        return;
    }
    
    if (g_showBarScientistModal) {
        DrawRetroWindow("SCIENTIST TIPS", modalX, modalY, modalWidth, modalHeight, 15);
        // Center text on OK button - OK button is centered at modalX + modalWidth/2
        // Text should be centered within modalWidth - 100, starting at modalX + 50 (increased padding to prevent overlap)
        // Position text higher to avoid overlap with button
        int textY = modalY + 70;
        int textBottomY = textY;
        // Text increased by 25% (12 * 1.25 = 15)
        DrawWordWrappedText(g_barScientistText, modalX + 50, textY, modalWidth - 100, 15, WHITE, &textBottomY);
        // Universal rule: buttons positioned 25px from bottom edge of modal
        int buttonHeight = 50;
        int buttonY = CalculateModalButtonY(modalY, modalHeight, buttonHeight);
        // Ensure modal height accommodates button (universal rule)
        int requiredHeight = CalculateRequiredModalHeight(textBottomY - modalY, buttonHeight, 70);
        if (requiredHeight > modalHeight) {
            modalHeight = requiredHeight;
            modalY = (VIRTUAL_HEIGHT - modalHeight) / 2;
            DrawRetroWindow("SCIENTIST TIPS", modalX, modalY, modalWidth, modalHeight, 15);
            textY = modalY + 70;
            textBottomY = textY;
            DrawWordWrappedText(g_barScientistText, modalX + 50, textY, modalWidth - 100, 15, WHITE, &textBottomY);
            buttonY = CalculateModalButtonY(modalY, modalHeight, buttonHeight);
        }
        DrawButton("OK", modalX + (modalWidth - 200)/2, buttonY, 200, 50, true, 15);
        return;
    }
    
    if (g_showBarSuccessModal) {
        // Use taller modal for success message to accommodate all text
        int successModalHeight = 550; // Increased from 450 to 550 for more space
        int successModalY = (VIRTUAL_HEIGHT - successModalHeight) / 2;
        DrawRetroWindow("SUCCESS!", modalX, successModalY, modalWidth, successModalHeight, 15);
        
        // Position text with proper spacing from top
        int textY = successModalY + 80; // Increased from 70 to 80 for more top padding
        int textBottomY = textY;
        // Text increased by 25% (12 * 1.25 = 15)
        DrawWordWrappedText(g_barSuccessText, modalX + 50, textY, modalWidth - 100, 15, WHITE, &textBottomY);
        
        // Universal rule: buttons positioned 25px from bottom edge of modal
        int buttonHeight = 50;
        int buttonY = CalculateModalButtonY(successModalY, successModalHeight, buttonHeight);
        // Ensure modal height accommodates button (universal rule)
        int requiredHeight = CalculateRequiredModalHeight(textBottomY - successModalY, buttonHeight, 80);
        if (requiredHeight > successModalHeight) {
            successModalHeight = requiredHeight;
            successModalY = (VIRTUAL_HEIGHT - successModalHeight) / 2;
            DrawRetroWindow("SUCCESS!", modalX, successModalY, modalWidth, successModalHeight, 15);
            textY = successModalY + 80;
            textBottomY = textY;
            DrawWordWrappedText(g_barSuccessText, modalX + 50, textY, modalWidth - 100, 15, WHITE, &textBottomY);
            buttonY = CalculateModalButtonY(successModalY, successModalHeight, buttonHeight);
        }
        DrawButton("OK", modalX + (modalWidth - 200)/2, buttonY, 200, 50, true, 15);
        return;
    }
    
    if (g_showBarLaserUpgradeModal) {
        DrawRetroWindow("LASER UPGRADE", modalX, modalY, modalWidth, modalHeight, 15);
        // Center text on OK button - OK button is centered at modalX + modalWidth/2
        // Text should be centered within modalWidth - 100, starting at modalX + 50 (increased padding to prevent overlap)
        // Position text higher to avoid overlap with button
        int textY = modalY + 70;
        int textBottomY = textY;
        // Text increased by 25% (12 * 1.25 = 15)
        DrawWordWrappedText(g_barLaserUpgradeText, modalX + 50, textY, modalWidth - 100, 15, WHITE, &textBottomY);
        // Universal rule: buttons positioned 25px from bottom edge of modal
        int buttonHeight = 50;
        int buttonY = CalculateModalButtonY(modalY, modalHeight, buttonHeight);
        // Ensure modal height accommodates button (universal rule)
        int requiredHeight = CalculateRequiredModalHeight(textBottomY - modalY, buttonHeight, 70);
        if (requiredHeight > modalHeight) {
            modalHeight = requiredHeight;
            modalY = (VIRTUAL_HEIGHT - modalHeight) / 2;
            DrawRetroWindow("LASER UPGRADE", modalX, modalY, modalWidth, modalHeight, 15);
            textY = modalY + 70;
            textBottomY = textY;
            DrawWordWrappedText(g_barLaserUpgradeText, modalX + 50, textY, modalWidth - 100, 15, WHITE, &textBottomY);
            buttonY = CalculateModalButtonY(modalY, modalHeight, buttonHeight);
        }
        DrawButton("OK", modalX + (modalWidth - 200)/2, buttonY, 200, 50, true, 15);
        return;
    }
    
    if (g_showDrunkModal) {
        DrawRetroWindow("YOU'RE DRUNK!", modalX, modalY, modalWidth, modalHeight, 15);
        int textY = modalY + 70;
        int textBottomY = textY;
        // Text increased by 25% (12 * 1.25 = 15)
        DrawWordWrappedText(g_drunkText, modalX + 50, textY, modalWidth - 100, 15, WHITE, &textBottomY);
        // Universal rule: buttons positioned 25px from bottom edge of modal
        int buttonHeight = 50;
        int buttonY = CalculateModalButtonY(modalY, modalHeight, buttonHeight);
        // Ensure modal height accommodates button (universal rule)
        int requiredHeight = CalculateRequiredModalHeight(textBottomY - modalY, buttonHeight, 70);
        if (requiredHeight > modalHeight) {
            modalHeight = requiredHeight;
            modalY = (VIRTUAL_HEIGHT - modalHeight) / 2;
            DrawRetroWindow("YOU'RE DRUNK!", modalX, modalY, modalWidth, modalHeight, 15);
            textY = modalY + 70;
            textBottomY = textY;
            DrawWordWrappedText(g_drunkText, modalX + 50, textY, modalWidth - 100, 15, WHITE, &textBottomY);
            buttonY = CalculateModalButtonY(modalY, modalHeight, buttonHeight);
        }
        DrawButton("OK", modalX + (modalWidth - 200)/2, buttonY, 200, 50, true, 15);
        return;
    }
    
    // Main Bar Menu - determine title and options based on location
    const char* barTitle;
    const char* options[6];
    int numOptions = 0;
    
    // Check for failsafe condition: no fuel and less than cheapest drink price for this location
    // Location 0 (Depot): cheapest = 5 (Astro Brew)
    // Location 1 (Station): cheapest = 5 (Astro Brew)
    // Location 2 (Halo): cheapest = 15 (Premium Drink)
    int cheapestDrinkPrice = (g_currentLocation == 2) ? 15 : 5;
    bool showFailsafeOption = (G_Player.fuel <= 0.0f && G_Player.credits < cheapestDrinkPrice);
    
    if (g_currentLocation == 1) {  // Station - Hirohito Station Bar
        barTitle = "HIROHITO STATION BAR";
        options[numOptions++] = "BUY ASTRO BREW (5 CR)";
        options[numOptions++] = "TAKE SPACE SHOT (10 CR)";
        options[numOptions++] = "TRY YOUR LUCK (50 CR)";
        // Conditional: Chat with Scientist - only on 3rd visit and if not used
        if (g_barVisitCounts[1] >= 3 && !g_barScientistUsed) {
            options[numOptions++] = "CHAT WITH SCIENTIST (FREE)";
        }
        // Failsafe option: Free fuel when out of fuel and low credits
        if (showFailsafeOption) {
            options[numOptions++] = "A CARING LOOKING FELLOW SPACER CALLS YOU OVER <FREE>";
        }
        options[numOptions++] = "LEAVE BAR";
    } else if (g_currentLocation == 2) {  // Halo - Nagako's Halo Bar
        barTitle = "NAGAKO'S HALO BAR";
        options[numOptions++] = "BUY PREMIUM DRINK (15 CR)";
        options[numOptions++] = "NETWORK WITH TRADERS (100 CR)";
        // Conditional: Listen to Stories - only on 3rd visit and if not used
        if (g_barVisitCounts[2] >= 3 && !g_barStoriesUsed) {
            options[numOptions++] = "LISTEN TO STORIES (FREE)";
        }
        // Failsafe option: Free fuel when out of fuel and low credits
        if (showFailsafeOption) {
            options[numOptions++] = "A CARING LOOKING FELLOW SPACER CALLS YOU OVER <FREE>";
        }
        options[numOptions++] = "LEAVE BAR";
    } else {  // Depot - The Astro Bar
        barTitle = "THE ASTRO BAR";
        options[numOptions++] = "BUY ASTRO BREW (5 CR)";
        options[numOptions++] = "TAKE SPACE SHOT (10 CR)";
        // Conditional: Drinks Are On Me - only if no gold card
        if (!G_Player.hasGoldCard) {
            options[numOptions++] = "DRINKS ARE ON ME! (1000 CR)";
        }
        // Conditional: Laser Upgrade - only on 3rd visit and if not used
        if (g_barVisitCounts[0] >= 3 && !g_barLaserUpgradeUsed) {
            options[numOptions++] = "LASER COOLING UPGRADE (FREE)";
        }
        // Failsafe option: Free fuel when out of fuel and low credits
        if (showFailsafeOption) {
            options[numOptions++] = "A CARING LOOKING FELLOW SPACER CALLS YOU OVER <FREE>";
        }
        options[numOptions++] = "LEAVE BAR";
    }
    
    // Ensure menu selection is valid for current location
    if (g_barMenuSelection >= numOptions) {
        g_barMenuSelection = numOptions - 1;
    }
    if (g_barMenuSelection < 0) {
        g_barMenuSelection = 0;
    }
    
    // Update max menu items to match current location
    g_barMaxMenuItems = numOptions;
    
    // Draw the main bar window
    DrawRetroWindow(barTitle, modalX, modalY, modalWidth, modalHeight, 15);
    
    // Mood Text - centered at top with word wrapping - increased by 25% (11 * 1.25 = 13.75, round to 14)
    int moodTextY = modalY + 50;
    int moodTextBottomY = moodTextY;
    DrawWordWrappedText(g_barMoods[g_barRandomMood], modalX + 50, moodTextY, modalWidth - 100, 14, LIGHTGRAY, &moodTextBottomY);
    
    // Draw menu options - ensure proper spacing to avoid overlap with status bar
    int startY = modalY + 100;
    int spacing = 50;
    
    // Calculate last button position to ensure status bar doesn't overlap
    int lastButtonY = startY + (numOptions - 1) * spacing;
    int lastButtonBottom = lastButtonY + 45; // Button height is 45
    
    for (int i = 0; i < numOptions; i++) {
        bool selected = (g_barMenuSelection == i);
        int btnY = startY + i * spacing;
        // Button text increased by 25% (12 * 1.25 = 15)
        DrawButton(options[i], modalX + 50, btnY, modalWidth - 100, 45, selected, 15);
        
        // Show [OWNED] indicator for Gold Card option in Depot if already owned - increased by 25% (12 * 1.25 = 15)
        if (i == 2 && g_currentLocation == 0 && G_Player.hasGoldCard) {
            if (retroFont.texture.id > 0) {
                DrawTextEx(retroFont, "[OWNED]",
                    (Vector2){(float)(modalX + modalWidth - 120), (float)(btnY + 12)},
                    15.0f, 0, GREEN);
            } else {
                DrawTextWithFont("[OWNED]", modalX + modalWidth - 120, btnY + 12, 15, GREEN);
            }
        }
    }
    
    // Status bar at bottom - ensure it doesn't overlap with buttons (at least 20px gap)
    int statusY = lastButtonBottom + 25; // 25px gap after last button
    if (statusY > modalY + modalHeight - 30) {
        statusY = modalY + modalHeight - 30; // Ensure status fits in modal
    }
    char status[64];
    snprintf(status, sizeof(status), "CREDITS: %d", G_Player.credits);
    // Status text increased by 25% (13 * 1.25 = 16.25, round to 16)
    if (retroFont.texture.id > 0) {
        Vector2 statusSize = MeasureTextEx(retroFont, status, 16.0f, 0);
        DrawTextEx(retroFont, status,
            (Vector2){(float)(modalX + (modalWidth - statusSize.x)/2), (float)statusY},
            16.0f, 0, YELLOW);
    } else {
        DrawTextWithFont(status, modalX + (modalWidth - MeasureTextWithFont(status, 16))/2, statusY, 16, YELLOW);
    }
}

// ------------------------------------------------------------
// DEPOT/STATION SHARED HELPERS
// ------------------------------------------------------------
void DrawDepotStats(int statsYOffset) {
    // Draw Stats Overlay (on top of PNG) - SHIP DATA and PILOT DATA
    Color coralColor = (Color){255, 127, 80, 255};
    
    // SHIP DATA section (left bottom) - Progress bars
    int shipDataX = 335;   // Base X position
    int shipDataY = VIRTUAL_HEIGHT - 120 + statsYOffset;  // Base Y position
    int rectWidth = 9;     // Width of each rectangle
    int rectHeight = 11;   // Height of each rectangle
    int rectSpacing = 2;   // Spacing between rectangles
    int maxRects = 10;     // Maximum rectangles
    
    // Individual positions for each bar - Hull aligned horizontally with Power and Fuel
    int hullX = shipDataX + 9;
    int hullY = shipDataY + 5;
    int powerX = shipDataX + 9;
    int powerY = shipDataY + 35;
    int fuelX = shipDataX + 9;
    int fuelY = shipDataY + 63;
    
    // HULL progress bars - Green
    int hullRects = (int)(G_Player.hull / 10.0f);
    for (int i = 0; i < maxRects; i++) {
        int rectX = hullX + i * (rectWidth + rectSpacing);
        if (i < hullRects) {
            DrawRectangle(rectX, hullY, rectWidth, rectHeight, GREEN);
        } else {
            DrawRectangle(rectX, hullY, rectWidth, rectHeight, DARKGRAY);
        }
    }
    
    // POWER progress bars - Red
    int powerRects = (int)(G_Player.power / 10.0f);
    for (int i = 0; i < maxRects; i++) {
        int rectX = powerX + i * (rectWidth + rectSpacing);
        if (i < powerRects) {
            DrawRectangle(rectX, powerY, rectWidth, rectHeight, RED);
        } else {
            DrawRectangle(rectX, powerY, rectWidth, rectHeight, DARKGRAY);
        }
    }
    
    // FUEL progress bars - Cyan
    int fuelRects = (int)(G_Player.fuel / 10.0f);
    Color cyanColor = (Color){0, 255, 255, 255};
    for (int i = 0; i < maxRects; i++) {
        int rectX = fuelX + i * (rectWidth + rectSpacing);
        if (i < fuelRects) {
            DrawRectangle(rectX, fuelY, rectWidth, rectHeight, cyanColor);
        } else {
            DrawRectangle(rectX, fuelY, rectWidth, rectHeight, DARKGRAY);
        }
    }
    
    // PILOT DATA section (right bottom) - Rank and Credits
    int pilotDataX = VIRTUAL_WIDTH - 180 - 3;  // Moved left 3px
    int pilotDataY = VIRTUAL_HEIGHT - 125 + statsYOffset + 3;  // Moved down 3px
    
    const char* rankName = GetRankName(G_Player.rank);
    char rankUpper[64];
    int i = 0;
    while (rankName[i] != '\0' && i < 63) {
        rankUpper[i] = (rankName[i] >= 'a' && rankName[i] <= 'z') ? (rankName[i] - 32) : rankName[i];
        i++;
    }
    rankUpper[i] = '\0';
    
    if (retroFont.texture.id > 0) {
        DrawTextEx(retroFont, rankUpper, (Vector2){(float)pilotDataX, (float)pilotDataY}, 14, 0, WHITE);
    } else {
        DrawTextWithFont(rankUpper, pilotDataX, pilotDataY, 14, WHITE);
    }
    
    char creditsText[32];
    snprintf(creditsText, sizeof(creditsText), "%d", G_Player.credits);
    if (retroFont.texture.id > 0) {
        DrawTextEx(retroFont, creditsText, (Vector2){(float)pilotDataX, (float)pilotDataY + 30}, 14, 0, WHITE);  // Moved down 5px (from +25 to +30)
    } else {
        DrawTextWithFont(creditsText, pilotDataX, pilotDataY + 30, 14, WHITE);  // Moved down 5px (from +25 to +30)
    }
    
    // CARGO DATA section (middle bottom) - Display collected commodities (no header, all caps)
    int cargoDataX = VIRTUAL_WIDTH / 2 - 200 + 160;  // Moved right 10px (from 150 to 160)
    int cargoDataY = VIRTUAL_HEIGHT - 120 + statsYOffset - 12;  // Moved down 3px (from -15 to -12)
    int cargoLineHeight = 22; // Tight spacing - font size is 20, so 22 gives minimal gap
    int maxCargoLines = 5;  // Show only first 5 commodities
    
    // Display commodities that player has collected (all caps, no header) - limit to first 5
    int cargoLine = 0;
    for (int i = 0; i < NUM_COMMODITIES && cargoLine < maxCargoLines; i++) {
        if (G_Player.inventory[i] > 0) {
            // Convert commodity name to uppercase
            char commNameUpper[64];
            const char* commName = g_commodityNames[i];
            int j = 0;
            while (commName[j] != '\0' && j < 63) {
                commNameUpper[j] = (commName[j] >= 'a' && commName[j] <= 'z') ? (commName[j] - 32) : commName[j];
                j++;
            }
            commNameUpper[j] = '\0';
            
            char cargoText[64];
            snprintf(cargoText, sizeof(cargoText), "%s: %d", commNameUpper, G_Player.inventory[i]);
            int yPos = cargoDataY + (cargoLine * cargoLineHeight);
            
            if (retroFont.texture.id > 0) {
                DrawTextEx(retroFont, cargoText, (Vector2){(float)cargoDataX, (float)yPos}, 12, 0, (Color){200, 200, 255, 255});
            } else {
                DrawTextWithFont(cargoText, cargoDataX, yPos, 12, (Color){200, 200, 255, 255});
            }
            cargoLine++;
            
            // Stop after displaying 5 items
            if (cargoLine >= maxCargoLines) break;
        }
    }
    
    // If no cargo, show empty message
    if (cargoLine == 0) {
        const char* emptyText = "EMPTY";
        int yPos = cargoDataY + 2;  // Moved down 2px
        if (retroFont.texture.id > 0) {
            DrawTextEx(retroFont, emptyText, (Vector2){(float)cargoDataX, (float)yPos}, 13, 0, GRAY);
        } else {
            DrawTextWithFont(emptyText, cargoDataX, yPos, 13, GRAY);
        }
    }
}

void HandleDepotInput(GameState* state, int* menuSelection) {
    // Handle Page Switching (Up/Down Arrows) - but NOT when bar view is open (bar needs UP/DOWN for menu navigation)
    if (!g_showBarView) {
        if (CustomIsKeyPressed(KEY_DOWN)) {
            g_depotHomePage++;
            if (g_depotHomePage > 4) g_depotHomePage = 1;
            // Reset overlay states when changing pages
            g_showProspectAsteroids = false;
            g_showShipyardShop = false;
            g_showCommoditiesMarket = false;
            g_showBarView = false;
            g_barJustOpened = false; // Clear flag when leaving bar via page navigation
        }
        if (CustomIsKeyPressed(KEY_UP)) {
            g_depotHomePage--;
            if (g_depotHomePage < 1) g_depotHomePage = 4;
            g_showProspectAsteroids = false;
            g_showShipyardShop = false;
            g_showBarView = false;
            g_barJustOpened = false; // Clear flag when leaving bar via page navigation
        }
    }
}

Texture2D* GetDepotPageTexture() {
    if (g_showProspectAsteroids && g_depotHomePage == 1) {
        switch (g_prospectPageOverlay) {
            case 1: return &prospectPageATx;
            case 2: return &prospectPageBTx;
            case 3: return &prospectPageCTx;
            case 4: return &prospectPageDTx;
            case 5: return &prospectPageETx;
            case 6: return &prospectPageFTx;
            default: return &prospectPageTx;
        }
    } else if (g_showShipyardShop && g_depotHomePage == 2) {
        switch (g_shipyardPageOverlay) {
            case 1: return &shipyardPageATx;
            case 2: return &shipyardPageBTx;
            case 3: return &shipyardPageCTx;
            case 4: return &shipyardPageDTx;
            case 5: return &shipyardPageETx;
            case 6: return &shipyardPageFTx;
            default: return &shipyardPageTx;
        }
    } else if (g_showBarView && g_depotHomePage == 4) {
        return &barPageTx;
    } else {
        switch (g_depotHomePage) {
            case 1: return &prospectGuiTx;
            case 2: return &shipyardGuiTx;
            case 3: return &commoditiesGuiTx;
            case 4: return &barGuiTx;
            default: return &prospectGuiTx;
        }
    }
}

void DrawPageDepotHome(GameState* state, int* menuSelection, Vector3* shipPos, Vector3* shipVel) {
    // Simulate left arrow key press immediately when returning to depot/station/halo to exit previous page
    static GameState lastState = STATE_SPLASH;
    static int enteringStationSoundPlayCount = 0; // Track how many times we've played (0, 1, or 2)
    bool justEnteredHome = false;
    bool isInHomeState = (*state == STATE_DEPOT_HOME || *state == STATE_STATION_HOME || *state == STATE_HALO_HOME);
    
    if ((lastState != STATE_DEPOT_HOME && *state == STATE_DEPOT_HOME) ||
        (lastState != STATE_STATION_HOME && *state == STATE_STATION_HOME) ||
        (lastState != STATE_HALO_HOME && *state == STATE_HALO_HOME)) {
        // Just entered home state
        justEnteredHome = true;
        // Reset the play count when entering a new home state
        enteringStationSoundPlayCount = 0;
        // Simulate left arrow press immediately
        if (KEY_LEFT >= 0 && KEY_LEFT < 512) {
            g_inputState.keysPressed[KEY_LEFT] = true;
        }
    }
    
    // Play entering station sound when entering from splash (new game) or from 3D environment
    // Play it twice: once immediately, then again after the first finishes
    if (isInHomeState && (lastState == STATE_SPLASH || lastState == STATE_LANDER || 
                          lastState == STATE_DEBRIS || lastState == STATE_NAV_SCREEN)) {
        if (g_enteringStationSound.frameCount > 0 && !IsSoundPlaying(g_enteringStationSound)) {
            if (enteringStationSoundPlayCount == 0) {
                // Play first instance
                PlaySound(g_enteringStationSound);
                enteringStationSoundPlayCount = 1;
            } else if (enteringStationSoundPlayCount == 1) {
                // First instance finished, play second instance
                PlaySound(g_enteringStationSound);
                enteringStationSoundPlayCount = 2; // Mark as complete
            }
        }
    }
    
    // Reset play count if we leave the home state
    if (!isInHomeState) {
        enteringStationSoundPlayCount = 0;
    }
    
    lastState = *state;
    
    // 1. Clear Background
    ClearBackground(BLACK);
    
    // Handle ESC key - close modal/prospect view/shop view first, then show exit modal, then go back
    if (CustomIsKeyPressed(KEY_ESCAPE)) {
        if (g_showWelcomeModal) {
            // Close welcome modal
            PlayTerminalTypeSound();
            g_showWelcomeModal = false;
            return;
        } else if (g_showExitToMainMenuModal) {
            // Close exit modal
            g_showExitToMainMenuModal = false;
            g_exitModalSelection = 0; // Reset to YES
            return;
        } else if (g_showNoCommodityModal) {
            // Close no commodity modal first
            g_showNoCommodityModal = false;
            return;
        } else if (g_showAsteroidModal) {
            g_showAsteroidModal = false;
            g_fuelCheckFailed = false;
            return;
        } else if (g_showShopModal) {
            g_showShopModal = false;
            g_purchaseFailed = false;
            return;
        } else if (g_showProspectAsteroids) {
            // Close prospect view and go back to Depot_Home page 1
            g_showProspectAsteroids = false;
            g_prospectPageOverlay = 0;
            g_depotHomePage = 1;
            return;
        } else if (g_showShipyardShop) {
            // Close shop view and go back to Depot_Home page 1
            g_showShipyardShop = false;
            g_shipyardPageOverlay = 0;
            g_depotHomePage = 1;
            return;
        } else if (g_showCommoditiesMarket) {
            // Close commodities market view and go back to Depot_Home page 1
            g_showCommoditiesMarket = false;
            g_depotHomePage = 1;
            return;
        } else if (g_showBarView) {
            // Close bar modals first if any are open
            if (g_showBarRumorModal || g_showBarGoldCardModal || g_showBarGamblingModal || g_showBarScientistModal || g_showBarSuccessModal || g_showBarLaserUpgradeModal) {
                PlayTerminalTypeSound();
                g_showBarRumorModal = false;
                g_showBarGoldCardModal = false;
                g_showBarGamblingModal = false;
                g_showBarScientistModal = false;
                g_showBarSuccessModal = false;
                g_showBarLaserUpgradeModal = false;
                return;
            }
            // Close bar view and go back to Depot_Home page 1
            PlayTerminalTypeSound();
            g_showBarView = false;
            g_barJustOpened = false; // Clear flag when leaving bar
            g_barDrinksPurchased = 0; // Reset drinks when leaving
            g_drunkThreshold = 0; // Reset drunk threshold for next visit
            g_barMenuSelection = 0; // Reset menu selection
            g_depotHomePage = 1;
            return;
        } else if (isInHomeState) {
            // Show exit to main menu modal when in home state
            g_showExitToMainMenuModal = true;
            g_exitModalSelection = 0; // Default to YES
            return;
        } else {
            // Navigate back to previous state
            HandleESCNavigation(state, menuSelection);
            return;
        }
    }
    
    // Block input when welcome modal is open (except ESC/ENTER/SPACE handled above)
    if (g_showWelcomeModal) {
        // Skip all other input processing - modal handles its own input
    } else {
        // Handle Enter key on page 1 to toggle asteroid prospect view (disabled when modal is open)
        if (g_depotHomePage == 1 && !g_showAsteroidModal && CustomIsKeyPressed(KEY_ENTER)) {
        PlayTerminalTypeSound();
        g_showProspectAsteroids = !g_showProspectAsteroids;
        if (g_showProspectAsteroids) {
            g_prospectPageOverlay = 0;  // Reset to base overlay when entering prospect view
        } else {
            g_showAsteroidModal = false;  // Close modal when exiting prospect view
        }
    }
    
    // Handle Enter key on page 2 to toggle shipyard shop view (disabled when modal is open)
    if (g_depotHomePage == 2 && !g_showShopModal && CustomIsKeyPressed(KEY_ENTER)) {
        PlayTerminalTypeSound();
        g_showShipyardShop = !g_showShipyardShop;
        if (g_showShipyardShop) {
            g_shipyardPageOverlay = 0;  // Reset to base overlay when entering shop view
        } else {
            g_showShopModal = false;  // Close modal when exiting shop view
        }
    }
    
    // Handle Enter key on page 3 to toggle commodities market view
    if (g_depotHomePage == 3 && CustomIsKeyPressed(KEY_ENTER)) {
        PlayTerminalTypeSound();
        g_showCommoditiesMarket = !g_showCommoditiesMarket;
        if (g_showCommoditiesMarket) {
            g_commoditiesMarketSelection = 0;  // Reset selection when entering
        }
    }
    
    // Handle Enter key on page 4 to toggle Bar view
    if (g_depotHomePage == 4 && CustomIsKeyPressed(KEY_ENTER)) {
        PlayTerminalTypeSound();
        if (!g_showBarView) {
            g_showBarView = true;
            g_barJustOpened = true; // Set flag to prevent Enter from immediately purchasing
            g_barModalTimer = 0.0f; // Start fresh delay before showing options
            g_barDrinksPurchased = 0;
            g_drunkThreshold = 0; // Reset drunk threshold for new bar visit
            g_barMenuSelection = 0; // Reset menu selection to first item
            g_barRandomMood = GetRandomValue(0, g_numBarMoods - 1);
            
            // Play bar.wav sound when entering bar
            if (g_barSound.frameCount > 0) {
                PlaySound(g_barSound);
            }
            
            // Increment visit counter for current location
            if (g_currentLocation >= 0 && g_currentLocation < 3) {
                g_barVisitCounts[g_currentLocation]++;
            }
            
            // Set max menu items based on current location (will be recalculated in DrawBarModal)
            if (g_currentLocation == 1) {
                g_barMaxMenuItems = 5; // Station has 5 options
            } else {
                g_barMaxMenuItems = 4; // Halo and Depot have 4 options
            }
            
            // Close any open modals when entering bar
            g_showBarRumorModal = false;
            g_showBarGoldCardModal = false;
            g_showBarGamblingModal = false;
            g_showBarScientistModal = false;
            g_showBarSuccessModal = false;
            g_showBarLaserUpgradeModal = false;
        }
    }
    
    // Handle A-F key presses when showing asteroid prospects
    if (g_showProspectAsteroids && g_depotHomePage == 1 && !g_showAsteroidModal) {
        // Get correct arrays based on location
        int* prospectScores;
        int* gravityScores;
        int fuelMin, fuelMax;
        if (g_currentLocation == 1) {  // Station
            prospectScores = g_stationProspectScores;
            gravityScores = g_stationGravityScores;
            fuelMin = 40; fuelMax = 80;  // Higher fuel costs
        } else if (g_currentLocation == 2) {  // Halo
            prospectScores = g_haloProspectScores;
            gravityScores = g_haloGravityScores;
            fuelMin = 60; fuelMax = 100;  // Highest fuel costs
        } else {  // Depot
            prospectScores = g_prospectScores;
            gravityScores = g_gravityScores;
            fuelMin = 20; fuelMax = 50;  // Standard fuel costs
        }
        
        if (CustomIsKeyPressed(KEY_A)) {
            PlayTerminalTypeSound();
            // Close fuel warning modal if open
            g_showFuelWarningModal = false;
            g_fuelCheckFailed = false;
            g_prospectPageOverlay = 1;  // A
            g_selectedAsteroidIndex = 0;  // A = index 0
            g_selectedAsteroidFuelCost = GetRandomValue(fuelMin, fuelMax);
            g_selectedAsteroidGravity = gravityScores[0];
            g_selectedAsteroidProspect = prospectScores[0];
            g_showAsteroidModal = true;
            g_modalSelection = 0;
        } else if (CustomIsKeyPressed(KEY_B)) {
            PlayTerminalTypeSound();
            // Close fuel warning modal if open
            g_showFuelWarningModal = false;
            g_fuelCheckFailed = false;
            g_prospectPageOverlay = 2;  // B
            g_selectedAsteroidIndex = 1;
            g_selectedAsteroidFuelCost = GetRandomValue(fuelMin, fuelMax);
            g_selectedAsteroidGravity = gravityScores[1];
            g_selectedAsteroidProspect = prospectScores[1];
            g_showAsteroidModal = true;
            g_modalSelection = 0;
        } else if (CustomIsKeyPressed(KEY_C)) {
            PlayTerminalTypeSound();
            // Close fuel warning modal if open
            g_showFuelWarningModal = false;
            g_fuelCheckFailed = false;
            g_prospectPageOverlay = 3;  // C
            g_selectedAsteroidIndex = 2;
            g_selectedAsteroidFuelCost = GetRandomValue(fuelMin, fuelMax);
            g_selectedAsteroidGravity = gravityScores[2];
            g_selectedAsteroidProspect = prospectScores[2];
            g_showAsteroidModal = true;
            g_modalSelection = 0;
        } else if (CustomIsKeyPressed(KEY_D)) {
            PlayTerminalTypeSound();
            // Close fuel warning modal if open
            g_showFuelWarningModal = false;
            g_fuelCheckFailed = false;
            g_prospectPageOverlay = 4;  // D
            g_selectedAsteroidIndex = 3;
            g_selectedAsteroidFuelCost = GetRandomValue(fuelMin, fuelMax);
            g_selectedAsteroidGravity = gravityScores[3];
            g_selectedAsteroidProspect = prospectScores[3];
            g_showAsteroidModal = true;
            g_modalSelection = 0;
        } else if (CustomIsKeyPressed(KEY_E)) {
            PlayTerminalTypeSound();
            // Close fuel warning modal if open
            g_showFuelWarningModal = false;
            g_fuelCheckFailed = false;
            g_prospectPageOverlay = 5;  // E
            g_selectedAsteroidIndex = 4;
            g_selectedAsteroidFuelCost = GetRandomValue(fuelMin, fuelMax);
            g_selectedAsteroidGravity = gravityScores[4];
            g_selectedAsteroidProspect = prospectScores[4];
            g_showAsteroidModal = true;
            g_modalSelection = 0;
        } else if (CustomIsKeyPressed(KEY_F)) {
            PlayTerminalTypeSound();
            // Close fuel warning modal if open
            g_showFuelWarningModal = false;
            g_fuelCheckFailed = false;
            g_prospectPageOverlay = 6;  // F
            g_selectedAsteroidIndex = 5;
            g_selectedAsteroidFuelCost = GetRandomValue(fuelMin, fuelMax);
            g_selectedAsteroidGravity = gravityScores[5];
            g_selectedAsteroidProspect = prospectScores[5];
            g_showAsteroidModal = true;
            g_modalSelection = 0;
        }
    }
    
    // Handle A-F key presses when showing shipyard shop
    if (g_showShipyardShop && g_depotHomePage == 2 && !g_showShopModal) {
        if (CustomIsKeyPressed(KEY_A)) {
            PlayTerminalTypeSound();
            g_shipyardPageOverlay = 1;  // A
            g_selectedShopItemIndex = 0;  // A = LASER
            g_showShopModal = true;
            g_shopModalSelection = 0;  // Default to Purchase
            g_purchaseFailed = false;
        } else if (CustomIsKeyPressed(KEY_B)) {
            PlayTerminalTypeSound();
            g_shipyardPageOverlay = 2;  // B
            g_selectedShopItemIndex = 1;  // B = COLLECTOR
            g_showShopModal = true;
            g_shopModalSelection = 0;
            g_purchaseFailed = false;
        } else if (CustomIsKeyPressed(KEY_C)) {
            PlayTerminalTypeSound();
            g_shipyardPageOverlay = 3;  // C
            g_selectedShopItemIndex = 2;  // C = THRUSTER
            g_showShopModal = true;
            g_shopModalSelection = 0;
            g_purchaseFailed = false;
        } else if (CustomIsKeyPressed(KEY_D)) {
            PlayTerminalTypeSound();
            g_shipyardPageOverlay = 4;  // D
            g_selectedShopItemIndex = 3;  // D = EXO-PLATING
            g_showShopModal = true;
            g_shopModalSelection = 0;
            g_purchaseFailed = false;
        } else if (CustomIsKeyPressed(KEY_E)) {
            PlayTerminalTypeSound();
            g_shipyardPageOverlay = 5;  // E
            g_selectedShopItemIndex = 4;  // E = FUEL
            g_showShopModal = true;
            g_shopModalSelection = 0;
            g_purchaseFailed = false;
        } else if (CustomIsKeyPressed(KEY_F)) {
            PlayTerminalTypeSound();
            g_shipyardPageOverlay = 6;  // F
            g_selectedShopItemIndex = 5;  // F = REPAIRS
            g_showShopModal = true;
            g_shopModalSelection = 0;
            g_purchaseFailed = false;
        }
    }
    
    // 2. Draw background - either station viewport (torus) or asteroid prospects or shop or commodities market
    // Both use the texture rendered in UpdateFrame
    Texture2D viewTex;
    if (g_showProspectAsteroids && g_depotHomePage == 1) {
        // Use asteroid prospects texture
        viewTex = g_asteroidViewport.texture;
    } else if (g_showShipyardShop && g_depotHomePage == 2) {
        // Use shipyard shop texture
        viewTex = g_shipyardShopViewport.texture;
    } else {
        // Use Station Viewport Texture (Standard Background)
        viewTex = stationViewport.GetTexture();
    }
    
    // Draw the background texture to fill the screen
    Rectangle srcRect = { 0, 0, (float)viewTex.width, (float)-viewTex.height }; // Flip Y
    Rectangle destRect = { 0, 0, VIRTUAL_WIDTH, VIRTUAL_HEIGHT }; // Full virtual screen
    DrawTexturePro(viewTex, srcRect, destRect, (Vector2){0,0}, 0.0f, WHITE);
    
    // Handle bar input when bar view is active
    if (g_showBarView && g_depotHomePage == 4) {
        // Update timer for bar menu delay
        g_barModalTimer += GetFrameTime();
        // Handle bar input (this will process UP/DOWN/ENTER keys)
        HandleBarModalInput();
    }
    
    // Handle commodities market navigation when market view is active
    if (g_showCommoditiesMarket && g_depotHomePage == 3) {
        int numOpt = NUM_COMMODITIES + 1;  // Commodities + back
        if (CustomIsKeyPressed(KEY_DOWN)) {
            g_commoditiesMarketSelection = (g_commoditiesMarketSelection + 1) % numOpt;
            PlayTerminalTypeSound();
        }
        if (CustomIsKeyPressed(KEY_UP)) {
            g_commoditiesMarketSelection = (g_commoditiesMarketSelection - 1 + numOpt) % numOpt;
            PlayTerminalTypeSound();
        }
        // Handle [S] key for selling (changed from ENTER)
        if (CustomIsKeyPressed(KEY_S)) {
            // Sell selected commodity
            if (g_commoditiesMarketSelection < NUM_COMMODITIES) {
                // Sell commodity
                int* buyPrices = g_stationBuyPrices[g_currentLocation];
                if (G_Player.inventory[g_commoditiesMarketSelection] > 0) {
                    // Play sale sound instead of terminal type sound
                    if (g_saleSound.frameCount > 0) {
                        PlaySound(g_saleSound);
                    }
                    G_Player.inventory[g_commoditiesMarketSelection]--;
                    // Apply gold card bonus: 20% increase in sell value
                    int basePrice = buyPrices[g_commoditiesMarketSelection];
                    int sellPrice = G_Player.hasGoldCard ? (int)(basePrice * 1.2f) : basePrice;
                    G_Player.credits += sellPrice;
                    G_Player.totalCreditsEarned += sellPrice;  // Track lifetime credits for rank
                    G_Player.cargoFilled--;
                    UpdateRank();  // Check for rank up after earning credits
                } else {
                    // Play No.wav sound at 100% volume when trying to sell commodity you don't have
                    if (g_noSound.frameCount > 0) {
                        PlaySound(g_noSound);
                    }
                }
            }
        }
        // Handle ENTER for back/exit only (only when BACK is selected)
        if (CustomIsKeyPressed(KEY_ENTER) || CustomIsKeyPressed(KEY_SPACE)) {
            if (g_commoditiesMarketSelection == NUM_COMMODITIES) {
                // Back - close market view
                PlayTerminalTypeSound();
                g_showCommoditiesMarket = false;
            }
            // Do nothing if a commodity is selected (not BACK)
        }
    }
    } // End of welcome modal input block
    
    // 3. Handle page navigation with up/down arrows (pages 1-4) - disabled when modal is open or in sub-views
    if (!g_showWelcomeModal && !g_showAsteroidModal && !g_showShopModal && !g_showBarView && !g_showCommoditiesMarket) {
        if (CustomIsKeyPressed(KEY_DOWN)) {
            if (g_depotHomePage < 4) {
                g_depotHomePage++;
                g_showProspectAsteroids = false;  // Reset when changing pages
                g_showAsteroidModal = false;  // Close modal when changing pages
                g_showShipyardShop = false;  // Reset shop view when changing pages
                g_showShopModal = false;  // Close shop modal when changing pages
                g_showCommoditiesMarket = false;  // Reset commodities market when changing pages
            }
        }
        if (CustomIsKeyPressed(KEY_UP)) {
            if (g_depotHomePage > 1) {
                g_depotHomePage--;
                g_showProspectAsteroids = false;  // Reset when changing pages
                g_showAsteroidModal = false;  // Close modal when changing pages
                g_showShipyardShop = false;  // Reset shop view when changing pages
                g_showShopModal = false;  // Close shop modal when changing pages
                g_showCommoditiesMarket = false;  // Reset commodities market when changing pages
            }
        }
    }
    
    // 4. Draw the appropriate PNG GUI overlay based on page number and prospect/shop view state
    Texture2D* currentGuiTx = NULL;
    
    // If showing asteroid prospects, use prospect page overlays
    if (g_showProspectAsteroids && g_depotHomePage == 1) {
        switch (g_prospectPageOverlay) {
            case 0:
                currentGuiTx = &prospectPageTx;  // Base prospect_page.png
                break;
            case 1:
                currentGuiTx = &prospectPageATx;  // prospect_page_A.png
                break;
            case 2:
                currentGuiTx = &prospectPageBTx;  // prospect_page_B.png
                break;
            case 3:
                currentGuiTx = &prospectPageCTx;  // prospect_page_C.png
                break;
            case 4:
                currentGuiTx = &prospectPageDTx;  // prospect_page_D.png
                break;
            case 5:
                currentGuiTx = &prospectPageETx;  // prospect_page_E.png
                break;
            case 6:
                currentGuiTx = &prospectPageFTx;  // prospect_page_F.png
                break;
            default:
                currentGuiTx = &prospectPageTx;  // Fallback to base
                break;
        }
    } else if (g_showShipyardShop && g_depotHomePage == 2) {
        // If showing shipyard shop, use shop page overlays
        switch (g_shipyardPageOverlay) {
            case 0:
                currentGuiTx = &shipyardPageTx;  // Base shipyard_page.png
                break;
            case 1:
                currentGuiTx = &shipyardPageATx;  // shipyard_page_A.png
                break;
            case 2:
                currentGuiTx = &shipyardPageBTx;  // shipyard_page_B.png
                break;
            case 3:
                currentGuiTx = &shipyardPageCTx;  // shipyard_page_C.png
                break;
            case 4:
                currentGuiTx = &shipyardPageDTx;  // shipyard_page_D.png
                break;
            case 5:
                currentGuiTx = &shipyardPageETx;  // shipyard_page_E.png
                break;
            case 6:
                currentGuiTx = &shipyardPageFTx;  // shipyard_page_F.png
                break;
            default:
                currentGuiTx = &shipyardPageTx;  // Fallback to base shipyard_page.png
                break;
        }
    } else if (g_showCommoditiesMarket && g_depotHomePage == 3) {
        // Use new Texture-based Commodities UI overlay
        currentGuiTx = &commoditiesMarketTx;
    } else if (g_showBarView && g_depotHomePage == 4) {
        currentGuiTx = &barPageTx;  // Bar page overlay
    } else {
        // Use normal depot page overlays
        switch (g_depotHomePage) {
            case 1:
                currentGuiTx = &prospectGuiTx;
                break;
            case 2:
                currentGuiTx = &shipyardGuiTx;
                break;
            case 3:
                currentGuiTx = &commoditiesGuiTx;
                break;
            case 4:
                currentGuiTx = &barGuiTx;
                break;
            default:
                currentGuiTx = &prospectGuiTx;  // Fallback to page 1
                break;
        }
    }
    
    // Draw the selected PNG texture overlay (on top of the space scene)
    if (currentGuiTx && currentGuiTx->id > 0) {
        Rectangle srcRectGui = { 0, 0, (float)currentGuiTx->width, (float)currentGuiTx->height };
        Rectangle destRectGui = { 0, 0, VIRTUAL_WIDTH, VIRTUAL_HEIGHT };
        DrawTexturePro(*currentGuiTx, srcRectGui, destRectGui, (Vector2){0, 0}, 0.0f, WHITE);
    }

    // Draw Commodities UI text/interactive elements directly on top of the overlay texture
    if (g_showCommoditiesMarket && g_depotHomePage == 3) {
        DrawCommoditiesOverlay();
    }
    
    // Draw Location Overlay (Shinjuku/Hirohito/Nagako) if applicable
    if (g_currentLocation == 0 && shinjukuOverlayTx.id > 0) { // Depot
        Rectangle srcRectGui = { 0, 0, (float)shinjukuOverlayTx.width, (float)shinjukuOverlayTx.height };
        Rectangle destRectGui = { 0, 0, VIRTUAL_WIDTH, VIRTUAL_HEIGHT };
        DrawTexturePro(shinjukuOverlayTx, srcRectGui, destRectGui, (Vector2){0, 0}, 0.0f, WHITE);
    } else if (g_currentLocation == 1 && hirohitoOverlayTx.id > 0) { // Station
        Rectangle srcRectGui = { 0, 0, (float)hirohitoOverlayTx.width, (float)hirohitoOverlayTx.height };
        Rectangle destRectGui = { 0, 0, VIRTUAL_WIDTH, VIRTUAL_HEIGHT };
        DrawTexturePro(hirohitoOverlayTx, srcRectGui, destRectGui, (Vector2){0, 0}, 0.0f, WHITE);
    } else if (g_currentLocation == 2 && nagakoOverlayTx.id > 0) { // Halo
        Rectangle srcRectGui = { 0, 0, (float)nagakoOverlayTx.width, (float)nagakoOverlayTx.height };
        Rectangle destRectGui = { 0, 0, VIRTUAL_WIDTH, VIRTUAL_HEIGHT };
        DrawTexturePro(nagakoOverlayTx, srcRectGui, destRectGui, (Vector2){0, 0}, 0.0f, WHITE);
    }
    
    // 5. Draw Stats Overlay (on top of PNG) - SHIP DATA, PILOT DATA, and CARGO DATA
    // Note: Fuel is NOT automatically refueled here - it persists between screens
    // Fuel is only refueled when purchasing at shop or starting new game
    DrawDepotStats(0);
    
    // Draw welcome modal if open (on top of everything, shown first)
    if (g_showWelcomeModal) {
        DrawWelcomeModal(state, menuSelection);
    }
    
    // Draw exit to main menu modal if open (on top of everything)
    if (g_showExitToMainMenuModal) {
        DrawExitToMainMenuModal(state, menuSelection);
    }
    
    // Draw asteroid launch modal if open (on top of everything)
    if (g_showAsteroidModal && g_showProspectAsteroids && g_depotHomePage == 1) {
        DrawAsteroidModal(state, menuSelection, shipPos, shipVel);
    }
    
    // Draw shop purchase modal if open (on top of everything)
    if (g_showShopModal && g_showShipyardShop && g_depotHomePage == 2) {
        DrawShopPurchaseModal(state, menuSelection);
    }
    
    // Draw Fuel Warning Modal (on top of everything, with OKAY button, closes on Enter or after 3 seconds)
    if (g_showFuelWarningModal) {
        // Handle Enter key to close modal
        if (CustomIsKeyPressed(KEY_ENTER)) {
            PlayTerminalTypeSound();
            g_showFuelWarningModal = false;
            g_fuelCheckFailed = false;
        } else {
            float dt = GetFrameTime();
            g_fuelWarningTimer -= dt;
            
            // Auto-close after 3 seconds as fallback
            if (g_fuelWarningTimer <= 0.0f) {
                g_showFuelWarningModal = false;
                g_fuelCheckFailed = false;
            } else {
                // Draw modal on top of everything
                int modalWidth = 700;
                int modalHeight = 300;
                int modalX = (VIRTUAL_WIDTH - modalWidth) / 2;
                int modalY = (VIRTUAL_HEIGHT - modalHeight) / 2;
                
                // Dark background with border
                DrawRectangle(modalX, modalY, modalWidth, modalHeight, (Color){20, 5, 5, 240});
                DrawRectangleLines(modalX, modalY, modalWidth, modalHeight, RED);
                DrawRectangleLines(modalX + 1, modalY + 1, modalWidth - 2, modalHeight - 2, (Color){255, 100, 100, 255});
                
                // Warning text (with word wrapping support)
                const char* warningText = "OUT OF FUEL WARNING";
                int maxTextWidth = modalWidth - 100; // Padding to prevent overlap
                int textY = modalY + 60;
                int textBottomY = textY;
                DrawWordWrappedText(warningText, modalX + 50, textY, maxTextWidth, 23, RED, &textBottomY);
                
                // Abort text (with word wrapping support)
                const char* abortText = "MINE ABORTED";
                textY = textBottomY + 30;
                DrawWordWrappedText(abortText, modalX + 50, textY, maxTextWidth, 18, YELLOW, &textBottomY);
                
                // OKAY button - use universal rule to position inline with text
                int buttonWidth = 150;
                int buttonHeight = 40;
                // Universal rule: buttons positioned 25px from bottom edge of modal
                int buttonX = modalX + (modalWidth - buttonWidth) / 2;
                int buttonY = CalculateModalButtonY(modalY, modalHeight, buttonHeight);
                
                // Ensure modal height accommodates button (universal rule)
                int requiredHeight = CalculateRequiredModalHeight(textBottomY - modalY, buttonHeight, 60);
                if (requiredHeight > modalHeight) {
                    modalHeight = requiredHeight;
                    modalY = (VIRTUAL_HEIGHT - modalHeight) / 2;
                    // Redraw background
                    DrawRectangle(modalX, modalY, modalWidth, modalHeight, (Color){20, 5, 5, 240});
                    DrawRectangleLines(modalX, modalY, modalWidth, modalHeight, RED);
                    DrawRectangleLines(modalX + 1, modalY + 1, modalWidth - 2, modalHeight - 2, (Color){255, 100, 100, 255});
                    // Redraw text
                    textY = modalY + 60;
                    textBottomY = textY;
                    DrawWordWrappedText(warningText, modalX + 50, textY, maxTextWidth, 23, RED, &textBottomY);
                    textY = textBottomY + 30;
                    DrawWordWrappedText(abortText, modalX + 50, textY, maxTextWidth, 18, YELLOW, &textBottomY);
                    buttonY = CalculateModalButtonY(modalY, modalHeight, buttonHeight);
                }
                
                // Button background (highlighted to show it's active)
                Color buttonColor = (Color){100, 0, 0, 255};
                DrawRectangle(buttonX, buttonY, buttonWidth, buttonHeight, buttonColor);
                DrawRectangleLines(buttonX, buttonY, buttonWidth, buttonHeight, RED);
                DrawRectangleLines(buttonX + 1, buttonY + 1, buttonWidth - 2, buttonHeight - 2, (Color){255, 150, 150, 255});
                
                // Button text
                const char* buttonText = "OKAY";
                int buttonTextW = MeasureTextWithFont(buttonText, 15);
                DrawTextWithFont(buttonText, buttonX + (buttonWidth - buttonTextW) / 2, buttonY + 8, 15, WHITE);
                
                // Instruction text below button
                const char* instructionText = "PRESS ENTER";
                int instructionW = MeasureTextWithFont(instructionText, 11);
                DrawTextWithFont(instructionText, modalX + (modalWidth - instructionW) / 2, buttonY + buttonHeight + 5, 11, (Color){200, 200, 200, 255});
            }
        }
    }
    
    // Draw No Commodity Modal (when trying to sell commodity you don't have)
    if (g_showNoCommodityModal) {
        // Handle ESC or ENTER to close modal
        if (CustomIsKeyPressed(KEY_ESCAPE) || CustomIsKeyPressed(KEY_ENTER) || CustomIsKeyPressed(KEY_SPACE)) {
            PlayTerminalTypeSound();
            g_showNoCommodityModal = false;
        } else {
            // Draw modal on top of everything
            int modalWidth = 700;
            int modalHeight = 250;
            int modalX = (VIRTUAL_WIDTH - modalWidth) / 2;
            int modalY = (VIRTUAL_HEIGHT - modalHeight) / 2;
            
            // Dark background with border
            DrawRectangle(modalX, modalY, modalWidth, modalHeight, (Color){20, 20, 5, 240});
            DrawRectangleLines(modalX, modalY, modalWidth, modalHeight, YELLOW);
            DrawRectangleLines(modalX + 1, modalY + 1, modalWidth - 2, modalHeight - 2, (Color){255, 255, 100, 255});
            
            // Message text: "YOU HAVE NO X TO SELL" (with word wrapping support)
            char messageText[128];
            snprintf(messageText, sizeof(messageText), "YOU HAVE NO %s TO SELL", g_noCommodityName);
            int maxTextWidth = modalWidth - 100; // Padding to prevent overlap
            int textY = modalY + 80;
            int textBottomY = textY;
            DrawWordWrappedText(messageText, modalX + 50, textY, maxTextWidth, 20, YELLOW, &textBottomY);
            
            // Instruction text (with word wrapping support)
            const char* instructionText = "PRESS ENTER OR ESC TO CLOSE";
            textY = textBottomY + 30;
            DrawWordWrappedText(instructionText, modalX + 50, textY, maxTextWidth, 12, WHITE, &textBottomY);
        }
    }
    
    // Draw Bar modal/interface if open (AFTER all other modals, so it renders on top)
    // This includes sub-modals like gold card, rumor, success, etc.
    // IMPORTANT: Draw sub-modals even if bar view is not active (they can persist)
    bool hasActiveBarModal = g_showBarRumorModal || g_showBarGoldCardModal || g_showBarGamblingModal || 
                              g_showBarScientistModal || g_showBarSuccessModal || g_showBarLaserUpgradeModal ||
                              g_showDrunkModal;
    
    // Always draw bar modals if any are active (regardless of bar view state)
    if (hasActiveBarModal || (g_showBarView && g_depotHomePage == 4)) {
        // Draw dark background overlay for sub-modals to make them stand out
        if (hasActiveBarModal) {
            // Semi-transparent dark overlay covering entire screen
            DrawRectangle(0, 0, VIRTUAL_WIDTH, VIRTUAL_HEIGHT, (Color){0, 0, 0, 180});
        }
        
        // Center modal on screen
        int modalWidth = 600;
        int modalHeight = 450;
        int modalX = (VIRTUAL_WIDTH - modalWidth) / 2;
        int modalY = (VIRTUAL_HEIGHT - modalHeight) / 2;
        DrawBarModal(modalX, modalY, modalWidth, modalHeight);
    }
    
    // Draw Rank-Up Modal with Fireworks (on top of everything)
    if (g_showRankUpModal) {
        float dt = GetFrameTime();
        g_rankUpFireworksTimer += dt;
        
        // Draw dark overlay
        DrawRectangle(0, 0, VIRTUAL_WIDTH, VIRTUAL_HEIGHT, (Color){0, 0, 0, 200});
        
        // Draw fireworks particles (simple particle system)
        int numParticles = 50;
        float time = g_rankUpFireworksTimer;
        for (int i = 0; i < numParticles; i++) {
            float angle = (float)i / numParticles * 2.0f * 3.14159f;
            float speed = 200.0f + (float)(i % 20) * 10.0f;
            float x = VIRTUAL_WIDTH / 2 + cosf(angle) * speed * time;
            float y = VIRTUAL_HEIGHT / 2 + sinf(angle) * speed * time - 100.0f * time * time;
            
            // Color based on angle (rainbow effect)
            Color particleColor;
            int colorIdx = (i / 8) % 6;
            switch (colorIdx) {
                case 0: particleColor = RED; break;
                case 1: particleColor = YELLOW; break;
                case 2: particleColor = GREEN; break;
                case 3: particleColor = (Color){0, 255, 255, 255}; break; // Cyan
                case 4: particleColor = BLUE; break;
                case 5: particleColor = MAGENTA; break;
                default: particleColor = WHITE; break;
            }
            
            if (y < VIRTUAL_HEIGHT && y > 0 && x > 0 && x < VIRTUAL_WIDTH) {
                DrawCircle((int)x, (int)y, 3, particleColor);
            }
        }
        
        // Draw modal
        int modalWidth = 700;
        int modalHeight = 500;
        int modalX = (VIRTUAL_WIDTH - modalWidth) / 2;
        int modalY = (VIRTUAL_HEIGHT - modalHeight) / 2;
        
        // Draw with golden glow effect
        Color panelFill = {20, 15, 5, 250};
        Color borderGlow = {255, 215, 0, 255};
        DrawRectangle(modalX - 2, modalY - 2, modalWidth + 4, modalHeight + 4, borderGlow);
        DrawRectangle(modalX, modalY, modalWidth, modalHeight, panelFill);
        DrawRectangleLines(modalX, modalY, modalWidth, modalHeight, borderGlow);
        
        // Title bar
        DrawRectangle(modalX, modalY, modalWidth, 50, borderGlow);
        const char* title = "CONGRATULATIONS!";
        int titleW = MeasureTextWithFont(title, 28);
        DrawTextWithFont(title, modalX + (modalWidth - titleW) / 2, modalY + 12, 28, BLACK);
        
        // Message text
        int textY = modalY + 80;
        int textBottomY = textY;
        DrawWordWrappedText(g_rankUpMessage, modalX + 50, textY, modalWidth - 100, 18, YELLOW, &textBottomY);
        
        // OKAY button
        int buttonHeight = 50;
        int buttonY = CalculateModalButtonY(modalY, modalHeight, buttonHeight);
        if (DrawButton("OKAY", modalX + (modalWidth - 200)/2, buttonY, 200, buttonHeight, true, 18)) {
            g_showRankUpModal = false;
            PlayTerminalTypeSound();
        }
    }
}

// ------------------------------------------------------------
// PAGE: DEBRIS COLLECTION
// ------------------------------------------------------------
void DrawPageDebris(GameState* state, int* menuSelection) {
    ClearBackground((Color){5, 20, 10, 255});
    DrawRetroWindow("DEBRIS COLLECTION", 300, 200, 600, 400);
    DrawTextWithFont("Collecting Debris...", 450, 300, 12, GREEN);
    
    if (DrawButton("FINISH", 500, 500, 200, 40, true)) {
        // Old debris collection - now handled by ConvertDebrisToCommodity()
        G_Player.cargoFilled++;
        // Reset drunk state when launching
        if (g_isDrunk) {
            // Restore original gravity scores
            int* gravityScores;
            if (g_currentLocation == 1) {  // Station
                gravityScores = g_stationGravityScores;
            } else if (g_currentLocation == 2) {  // Halo
                gravityScores = g_haloGravityScores;
            } else {  // Depot
                gravityScores = g_gravityScores;
            }
            
            // Restore gravity for all asteroids (remove drunk increase)
            float restoreFactor = 1.0f / (1.0f + g_drunkGravityIncrease / 100.0f);
            for (int i = 0; i < 6; i++) {
                gravityScores[i] = (int)(gravityScores[i] * restoreFactor);
            }
            
            g_isDrunk = false;
            g_drunkGravityIncrease = 0;
            printf("[ResetState] Drunk state reset - gravity restored\n");
        }
        
        ResetState(state, menuSelection, STATE_LANDER);
    }
}

// ------------------------------------------------------------
// PAGE: DEPOT MAP
// ------------------------------------------------------------
void DrawPageDepotSelect(GameState* state, int* menuSelection) {
    ClearBackground((Color){10, 10, 30, 255});
    DrawRetroWindow("AVAILABLE DEPOTS", 100, 100, 1000, 600);
    
    // 2 Options
    if (CustomIsKeyPressed(KEY_RIGHT) || CustomIsKeyPressed(KEY_LEFT) || CustomIsKeyPressed(KEY_UP) || CustomIsKeyPressed(KEY_DOWN)) {
        *menuSelection = (*menuSelection == 0) ? 1 : 0;
    }

    // Station Icons
    Color c1 = (*menuSelection == 0) ? WHITE : GRAY;
    Color c2 = (*menuSelection == 1) ? WHITE : GRAY;

    DrawCircle(400, 300, 60, BLUE);
    DrawCircleLines(400, 300, 65, c1);
    DrawTextWithFont("ALPHA STATION", 350, 370, 12, c1);
    if (DrawButton("DOCK", 350, 400, 100, 30, *menuSelection == 0)) {
        ResetState(state, menuSelection, STATE_DEPOT_HOME);
    }

    DrawCircle(800, 400, 40, PURPLE);
    DrawCircleLines(800, 400, 45, c2);
    DrawTextWithFont("OUTPOST BETA", 750, 450, 12, c2);
    if (DrawButton("LOCKED", 750, 480, 100, 30, *menuSelection == 1)) {
        // Locked logic
    }
}

// ------------------------------------------------------------
// PAGE: STATION HOME (Hirohito Station)
// ------------------------------------------------------------
void DrawPageStationHome(GameState* state, int* menuSelection, Vector3* shipPos, Vector3* shipVel) {
    // Reuse Depot Home logic (including input, stats, and overlays)
    // Note: Refueling is handled in DrawPageDepotHome before drawing fuel bar
    // The UpdateFrame function sets the correct 3D Viewport (Icosahedron)
    // The DrawPageDepotHome function now handles the extra Hirohito overlay based on g_currentLocation
    DrawPageDepotHome(state, menuSelection, shipPos, shipVel);
}

// ------------------------------------------------------------
// PAGE: HALO HOME (Nagako's Halo)
// ------------------------------------------------------------
void DrawPageHaloHome(GameState* state, int* menuSelection, Vector3* shipPos, Vector3* shipVel) {
    // Reuse Depot Home logic
    // Note: Refueling is handled in DrawPageDepotHome before drawing fuel bar
    DrawPageDepotHome(state, menuSelection, shipPos, shipVel);
}

// ------------------------------------------------------------
// PAGE: GAME OVER
// ------------------------------------------------------------
void DrawPageGameOver(GameState* state, int* menuSelection) {
    ClearBackground((Color){10, 5, 5, 255});  // Dark red background
    
    // Draw "GAME OVER" text
    char gameOverText[] = "GAME OVER";
    int textWidth = MeasureTextWithFont(gameOverText, 50);
    int centerX = VIRTUAL_WIDTH / 2;
    int centerY = VIRTUAL_HEIGHT / 2;
    
    // Draw with outline for visibility
    DrawTextWithFont(gameOverText, centerX - textWidth/2 + 3, centerY - 40 + 3, 50, BLACK);
    DrawTextWithFont(gameOverText, centerX - textWidth/2, centerY - 40, 50, RED);
    
    // Draw instruction text
    char instructionText[] = "PRESS ANY KEY TO CONTINUE";
    int instWidth = MeasureTextWithFont(instructionText, 19);
    DrawTextWithFont(instructionText, centerX - instWidth/2, centerY + 60, 19, YELLOW);
    
    // Check for any key press to return to splash
    // Check all keys from A-Z, 0-9, and common keys
    bool anyKeyPressed = false;
    for (int key = KEY_A; key <= KEY_Z; key++) {
        if (CustomIsKeyPressed(key)) {
            anyKeyPressed = true;
            break;
        }
    }
    if (!anyKeyPressed) {
        for (int key = KEY_ZERO; key <= KEY_NINE; key++) {
            if (CustomIsKeyPressed(key)) {
                anyKeyPressed = true;
                break;
            }
        }
    }
    if (!anyKeyPressed) {
        if (CustomIsKeyPressed(KEY_SPACE) || CustomIsKeyPressed(KEY_ENTER) || 
            CustomIsKeyPressed(KEY_ESCAPE) || CustomIsKeyPressed(KEY_UP) ||
            CustomIsKeyPressed(KEY_DOWN) || CustomIsKeyPressed(KEY_LEFT) ||
            CustomIsKeyPressed(KEY_RIGHT)) {
            anyKeyPressed = true;
        }
    }
    
    if (anyKeyPressed) {
        ResetState(state, menuSelection, STATE_SPLASH);
    }
}

// ------------------------------------------------------------
// PAGE: GET READY SPLASH SCREEN
// ------------------------------------------------------------
void DrawPageGetReady(GameState* state, int* menuSelection) {
    ClearBackground((Color){5, 5, 10, 255});  // Dark blue background (similar to game over style)
    
    // Draw "GET READY" text with flashing effect
    char getReadyText[] = "GET READY";
    int textWidth = MeasureTextWithFont(getReadyText, 50);
    int centerX = VIRTUAL_WIDTH / 2;
    int centerY = VIRTUAL_HEIGHT / 2;
    
    // Flash effect: alternate between visible and invisible (4 times per second)
    bool flashOn = ((int)(GetTime() * 4) % 2 == 0);
    
    if (flashOn) {
        // Draw with outline for visibility (same style as game over)
        DrawTextWithFont(getReadyText, centerX - textWidth/2 + 3, centerY - 200 + 3, 50, BLACK);
        DrawTextWithFont(getReadyText, centerX - textWidth/2, centerY - 200, 50, (Color){0, 255, 255, 255}); // Cyan color
    }
    
    // Controls and Guide (below GET READY text) - Larger text
    int startY = centerY - 60;
    int lineHeight = 35;
    int fontSize = 18;  // Larger font size
    
    // Controls Section - All on one line in red
    const char* controlsLine = "LMB = THRUST .. MOUSE = MOVE .. RMB = YAW";
    int controlsW = MeasureTextWithFont(controlsLine, fontSize);
    DrawTextWithFont(controlsLine, centerX - controlsW/2, startY, fontSize, RED);
    
    // SPACE = FIRE LASER in cyan below controls
    int laserY = startY + lineHeight;
    if (G_Player.hasLaser) {
        const char* laserText = "SPACE = FIRE LASER";
        int laserW = MeasureTextWithFont(laserText, fontSize);
        DrawTextWithFont(laserText, centerX - laserW/2, laserY, fontSize, (Color){0, 255, 255, 255}); // Cyan
    } else {
        const char* laserText = "SPACE = FIRE LASER (LASER REQ)";
        int laserW = MeasureTextWithFont(laserText, fontSize);
        DrawTextWithFont(laserText, centerX - laserW/2, laserY, fontSize, (Color){0, 255, 255, 255}); // Cyan
    }
    
    // Guide Section
    int guideY = laserY + lineHeight * 2;
    const char* guideLabel = "GUIDE";
    int guideW = MeasureTextWithFont(guideLabel, fontSize);
    DrawTextWithFont(guideLabel, centerX - guideW/2, guideY, fontSize, YELLOW);
    
    // LASER THE ROCKS text in cyan
    int laserRocksY = guideY + lineHeight;
    const char* laserRocksText = "LASER THE ROCKS OBSERVING CLOSELY FOR DEBRIS";
    int laserRocksW = MeasureTextWithFont(laserRocksText, fontSize);
    DrawTextWithFont(laserRocksText, centerX - laserRocksW/2, laserRocksY, fontSize, (Color){0, 255, 255, 255}); // Cyan
    
    // COLLECT text in cyan
    int collectY = laserRocksY + lineHeight;
    if (G_Player.hasCollector) {
        const char* collectText = "COLLECT: Fly close slowly to collect it";
        int collectW = MeasureTextWithFont(collectText, fontSize);
        DrawTextWithFont(collectText, centerX - collectW/2, collectY, fontSize, (Color){0, 255, 255, 255}); // Cyan
    } else {
        const char* collectText = "COLLECT: Fly close slowly to collect it (COLLECTOR REQ)";
        int collectW = MeasureTextWithFont(collectText, fontSize);
        DrawTextWithFont(collectText, centerX - collectW/2, collectY, fontSize, (Color){0, 255, 255, 255}); // Cyan
    }
    
    // EXIT text in red (two lines, all caps)
    int exitY = collectY + lineHeight;
    const char* exitText1 = "EXIT: ENTER THE RED GRAVITY REVERSE TUNNEL";
    int exitW1 = MeasureTextWithFont(exitText1, fontSize);
    DrawTextWithFont(exitText1, centerX - exitW1/2, exitY, fontSize, RED);
    int exitY2 = exitY + lineHeight;
    const char* exitText2 = "TO LEAVE CLOSE PROXIMITY ORBIT.";
    int exitW2 = MeasureTextWithFont(exitText2, fontSize);
    DrawTextWithFont(exitText2, centerX - exitW2/2, exitY2, fontSize, RED);
    
    // LEFT MOUSE TO LAUNCH warning in flashing cyan (two lines, split after comma)
    int launchY = exitY2 + lineHeight * 2;
    if (flashOn) {
        const char* launchText1 = "LEFT MOUSE TO LAUNCH,";
        int launchW1 = MeasureTextWithFont(launchText1, fontSize);
        DrawTextWithFont(launchText1, centerX - launchW1/2 + 2, launchY + 2, fontSize, BLACK);
        DrawTextWithFont(launchText1, centerX - launchW1/2, launchY, fontSize, (Color){0, 255, 255, 255}); // Cyan
        int launchY2 = launchY + lineHeight;
        const char* launchText2 = "WARNING GRAVITY CAN OVERPOWER YOUR SHIP";
        int launchW2 = MeasureTextWithFont(launchText2, fontSize);
        DrawTextWithFont(launchText2, centerX - launchW2/2 + 2, launchY2 + 2, fontSize, BLACK);
        DrawTextWithFont(launchText2, centerX - launchW2/2, launchY2, fontSize, (Color){0, 255, 255, 255}); // Cyan
    }
    
    // Update timer and transition to lander when timer expires OR left mouse button is pressed
    float dt = GetFrameTime();
    g_getReadyTimer -= dt;
    
    // Check for left mouse button press to skip the wait
    bool skipReady = CustomIsMouseButtonPressed(MOUSE_BUTTON_LEFT);
    
    if (g_getReadyTimer <= 0.0f || skipReady) {
        g_showGetReady = false;
        // Reset bostonpump flag when leaving Get Ready (it will continue playing in lander)
        // bostonpumpStarted will reset when Get Ready appears again
        *state = STATE_LANDER;
        *menuSelection = 0;
    }
}


// ------------------------------------------------------------
// PAGE: SUB-MENUS
// ------------------------------------------------------------
void DrawPageBar(GameState* state, int* menuSelection) {
    ClearBackground(BLACK);
    DrawRetroWindow("THE RUSTY ROCKET BAR", 200, 100, 800, 600);
    DrawTextWithFont("Bartender: 'Careful out there, miner...'", 250, 200, 12, YELLOW);
    
    if (DrawButton("BACK", 500, 600, 200, 40, true)) ResetState(state, menuSelection, STATE_DEPOT_HOME);
}

void DrawPageShipyard(GameState* state, int* menuSelection) {
    ClearBackground(BLACK);
    DrawRetroWindow("SHIPYARD", 200, 100, 800, 600);
    DrawTextWithFont("UPGRADE YOUR THRUSTERS AND HULL HERE.", 250, 200, 12, WHITE);
    
    if (CustomIsKeyPressed(KEY_DOWN) || CustomIsKeyPressed(KEY_UP)) *menuSelection = !(*menuSelection); // Toggle 0/1

    if (DrawButton("UPGRADE THRUST (500CR)", 250, 300, 300, 40, *menuSelection == 0)) {
        if (G_Player.credits >= 500 && G_Player.power < G_Player.maxPower) {
            G_Player.credits -= 500;
            G_Player.power += 5.0f;
            if (G_Player.power > G_Player.maxPower) G_Player.power = G_Player.maxPower;
            SHIP_THRUST_POWER = G_Player.power;  // Update thrust power to match player power
            
            // Play fixing-on.wav sound at 100% volume when upgrade is purchased
            if (g_fixingOnSound.frameCount > 0) {
                SetSoundVolume(g_fixingOnSound, 1.0f); // 100% volume
                PlaySound(g_fixingOnSound);
            }
        }
    }
    if (DrawButton("BACK", 500, 600, 200, 40, *menuSelection == 1)) ResetState(state, menuSelection, STATE_DEPOT_HOME);
}

void DrawPageMarket(GameState* state, int* menuSelection) {
    // This function is effectively UNUSED in the current "Overlay" architecture.
    // The Commodities Market is rendered via RenderCommoditiesMarket() (to texture)
    // and displayed as an overlay in DrawPageDepotHome().
    // Input is handled in DrawPageDepotHome().
    
    // Fallback if somehow entered
    ClearBackground(BLACK);
    DrawTextWithFont("ERROR: STATE_MARKET is deprecated.", 100, 100, 20, RED);
    DrawTextWithFont("Use DrawPageDepotHome overlay instead.", 100, 130, 20, RED);
    
    if (DrawButton("BACK", 500, 600, 200, 40, true)) {
        ResetState(state, menuSelection, STATE_DEPOT_HOME);
    }
}

void DrawPageLodgings(GameState* state, int* menuSelection) {
    ClearBackground(BLACK);
    DrawRetroWindow("CREW LODGINGS", 200, 100, 800, 600);
    DrawTextWithFont("Zzz... Rested and Saved.", 350, 300, 12, BLUE);
    if (DrawButton("BACK", 500, 600, 200, 40, true)) ResetState(state, menuSelection, STATE_DEPOT_HOME);
}

// ------------------------------------------------------------
// GAME LOOP FUNCTION (called from Python each frame)
// ------------------------------------------------------------
#ifdef __cplusplus
extern "C" {
#endif

// Flag to detect standalone mode (when main() creates the window)
static bool g_standalone_mode = false;

void UpdateInputFromRaylib() {
    // Update input state from raylib (for standalone mode)
    // This allows keyboard/mouse to work without Python forwarding events
    
    // Update key states
    for (int key = 0; key < 512; key++) {
        bool wasDown = g_inputState.keys[key];
        bool isDown = IsKeyDown(key);
        g_inputState.keys[key] = isDown;
        
        // Detect press/release
        if (isDown && !wasDown) {
            g_inputState.keysPressed[key] = true;
        } else {
            g_inputState.keysPressed[key] = false;
        }
    }
    
    // Update mouse button states
    for (int button = 0; button < 8; button++) {
        bool wasDown = g_inputState.mouseButtons[button];
        bool isDown = IsMouseButtonDown(button);
        g_inputState.mouseButtons[button] = isDown;
        
        // Detect press/release
        if (isDown && !wasDown) {
            g_inputState.mouseButtonsPressed[button] = true;
        } else {
            g_inputState.mouseButtonsPressed[button] = false;
        }
        
        // Detect release
        if (!isDown && wasDown) {
            g_inputState.mouseButtonsReleased[button] = true;
        } else {
            g_inputState.mouseButtonsReleased[button] = false;
        }
    }
    
    // Update mouse delta (for ship control in lander mode)
    Vector2 mouseDelta = GetMouseDelta();
    g_inputState.mouseDelta = mouseDelta;
    
    // Update mouse position
    Vector2 mousePos = GetMousePosition();
    g_inputState.mousePosition = mousePos;
}

// ------------------------------------------------------------
// LASER & MINING SYSTEM
// ------------------------------------------------------------

#define MAX_DEBRIS 100

typedef struct {
    Vector3 position;
    Vector3 velocity;
    bool active;
    float scale;
    Color color;
    int prosperityPercentage;  // Prosperity percentage of the asteroid this debris came from
} DebrisChunk;

DebrisChunk g_debris[MAX_DEBRIS];

// Function to spawn smaller rocks when a rock explodes
void SpawnSmallerRocks(Vector3 pos, float sourceRockScale, int prosperityPercentage) {
    // Spawn 8-10 smaller rocks
    int numRocks = GetRandomValue(8, 10);
    
    for (int k = 0; k < numRocks; k++) {
        // Find empty slot in G_Rocks array
        int slot = -1;
        for (int j = 0; j < NUM_ROCKS; j++) {
            if (!G_Rocks[j].active) { slot = j; break; }
        }
        
        if (slot != -1) {
            // Smaller scale: 30-60% of source rock size
            float minScale = sourceRockScale * 0.3f;
            float maxScale = sourceRockScale * 0.6f;
            float newScale = minScale + ((float)GetRandomValue(0, 1000) / 1000.0f) * (maxScale - minScale);
            if (newScale < 0.2f) newScale = 0.2f; // Minimum size
            
            // Spread position around explosion point
            float spreadRadius = sourceRockScale * 0.8f;
            float rx = pos.x + ((float)GetRandomValue(-100, 100) / 100.0f) * spreadRadius;
            float rz = pos.z + ((float)GetRandomValue(-100, 100) / 100.0f) * spreadRadius;
            float ry = GetTerrainHeight(rx, rz) + (0.2f * newScale);
            
            G_Rocks[slot].position = (Vector3){rx, ry, rz};
            G_Rocks[slot].scale = newScale;
            G_Rocks[slot].axis = Vector3Normalize((Vector3){(float)GetRandomValue(-1,1),(float)GetRandomValue(-1,1),(float)GetRandomValue(-1,1)});
            G_Rocks[slot].angle = (float)GetRandomValue(0, 360);
            int tintVal = GetRandomValue(200, 255);
            G_Rocks[slot].color = (Color){(unsigned char)tintVal, (unsigned char)tintVal, (unsigned char)tintVal, 255};
            G_Rocks[slot].active = true;
            G_Rocks[slot].prosperityPercentage = prosperityPercentage;  // Inherit prosperity from source rock
        }
    }
}

void SpawnDebris(Vector3 pos, int count, float sourceRockScale, int asteroidProspect) {
    for (int k = 0; k < count; k++) {
        // Find empty slot
        int slot = -1;
        for (int j = 0; j < MAX_DEBRIS; j++) {
            if (!g_debris[j].active) { slot = j; break; }
        }
        if (slot != -1) {
            g_debris[slot].active = true;
            
            // Add random offset to position for explosion spread
            float spreadRadius = sourceRockScale * 0.5f;
            g_debris[slot].position = (Vector3){
                pos.x + ((float)GetRandomValue(-100, 100) / 100.0f) * spreadRadius,
                pos.y + ((float)GetRandomValue(-100, 100) / 100.0f) * spreadRadius,
                pos.z + ((float)GetRandomValue(-100, 100) / 100.0f) * spreadRadius
            };
            
            // Explosive velocity - faster and more random
            g_debris[slot].velocity = (Vector3){
                (float)GetRandomValue(-50, 50) / 10.0f,
                (float)GetRandomValue(30, 80) / 10.0f, // Upwards burst
                (float)GetRandomValue(-50, 50) / 10.0f
            };
            
            // Debris size: always smaller than source rock, varies more
            // Source rock scale is typically 0.5 to 3.0, so debris should be 0.05 to 0.3
            float maxDebrisScale = sourceRockScale * 0.1f; // Max 10% of source size
            if (maxDebrisScale < 0.05f) maxDebrisScale = 0.05f; // Minimum size
            if (maxDebrisScale > 0.3f) maxDebrisScale = 0.3f; // Maximum size
            float minDebrisScale = maxDebrisScale * 0.2f; // 20% of max for variety
            g_debris[slot].scale = minDebrisScale + ((float)GetRandomValue(0, 1000) / 1000.0f) * (maxDebrisScale - minDebrisScale);
            
            // Collection debris chunks are cyan (swapped from grey) - collectible
            g_debris[slot].color = (Color){0, 255, 255, 255}; // Cyan - swapped from grey
            
            // Store prosperity percentage in debris
            g_debris[slot].prosperityPercentage = asteroidProspect;
        }
    }
}

void UpdateRocksAndDebris(float dt, Vector3 shipPos) {
    // 1. Debris Physics
    for (int i = 0; i < MAX_DEBRIS; i++) {
        if (!g_debris[i].active) continue;
        
        // Gravity
        // Calculate dynamic gravity based on asteroid gravity (matching ship logic but heavier)
        float asteroidGravityFactor = (float)g_selectedAsteroidGravity / 100.0f;
        float minGravity = -6.0f;
        float maxGravity = -18.0f;
        float asteroidGravity = Lerp(minGravity, maxGravity, asteroidGravityFactor);
        
        // Debris is "heavy" - apply 2.0x multiplier to make it fall quickly
        float debrisGravity = asteroidGravity * 2.0f;
        
        g_debris[i].velocity.y += debrisGravity * dt;
        
        // Update Position
        g_debris[i].position = Vector3Add(g_debris[i].position, Vector3Scale(g_debris[i].velocity, dt));
        
        // Ground Collision
        float groundH = GetTerrainHeight(g_debris[i].position.x, g_debris[i].position.z);
        if (g_debris[i].position.y < groundH + 0.2f) {
            g_debris[i].position.y = groundH + 0.2f;
            g_debris[i].velocity.y = 0;
            g_debris[i].velocity.x *= 0.8f; // Friction
            g_debris[i].velocity.z *= 0.8f;
        }
        
        // Collector Vacuum Logic - only attracts cyan collection debris
        // Prospecting score determines rejection rate: 10% prospect = 90% rejection rate
        if (G_Player.hasCollector && G_Player.cargoFilled < G_Player.cargoSpace) {
            // Check if debris is cyan (collection debris) - only cyan debris is collectible
            Color debrisColor = g_debris[i].color;
            bool isCollectionDebris = (debrisColor.r == 0 && debrisColor.g == 255 && debrisColor.b == 255); // Cyan (collection debris)
            
            if (isCollectionDebris) {
            float dist = Vector3Distance(g_debris[i].position, shipPos);
            if (dist < 20.0f) { // Vacuum Range
                    // Use debris's own prosperity percentage for collection chance
                    int debrisProsperity = g_debris[i].prosperityPercentage;
                    int collectionRoll = GetRandomValue(0, 99);
                    
                    // Only proceed if prosperity check succeeds
                    if (collectionRoll < debrisProsperity) {
                Vector3 dir = Vector3Normalize(Vector3Subtract(shipPos, g_debris[i].position));
                float speed = 30.0f * (1.0f - dist/20.0f) + 10.0f; // Faster when closer
                
                // Move towards ship
                g_debris[i].position = Vector3Add(g_debris[i].position, Vector3Scale(dir, speed * dt));
                
                // Collection
                if (dist < 3.0f) { // Close enough to collect
                    g_debris[i].active = false;
                            
                            // Convert debris to commodity based on asteroid's distribution
                            ConvertDebrisToCommodity();
                            
                    G_Player.cargoFilled++;
                    
                    // Play collect sound when cargo is collected
                    if (g_collectSound.frameCount > 0) {
                        PlaySound(g_collectSound);
                    }
                    // Spawn simple spark or effect?
                        }
                    }
                }
            }
        }
    }
}

void UpdateLaserLogic(float dt, Vector3 shipPos, Vector3 shipDir) {
    // Handle Cooling
    if (G_Player.laserOverheated) {
        G_Player.laserCooldown -= dt;
        if (G_Player.laserCooldown <= 0) {
            G_Player.laserOverheated = false;
            G_Player.laserHeat = 0;
        }
    } else if (G_Player.laserHeat > 0 && !CustomIsKeyDown(KEY_SPACE)) {
        // Cool down when not firing: 5 seconds to cool from 100 to 0
        G_Player.laserHeat -= (100.0f / 5.0f) * dt; // 20.0f per second
        if (G_Player.laserHeat < 0) G_Player.laserHeat = 0;
    }

    // Continuous beam while space is held (not just on key press)
    if (CustomIsKeyDown(KEY_SPACE) && G_Player.hasLaser && !G_Player.laserOverheated) {
        // Play laser sound
        if (!IsSoundPlaying(g_laserSound)) {
            PlaySound(g_laserSound);
        }

        // Heat up: 3 seconds to reach max heat (100)
        G_Player.laserHeat += (100.0f / 3.0f) * dt; // ~33.33 per second
        if (G_Player.laserHeat >= G_Player.maxLaserHeat) {
            G_Player.laserOverheated = true;
            G_Player.laserCooldown = 5.0f; // 5 seconds cooldown
            G_Player.laserHeat = G_Player.maxLaserHeat; // Clamp to max
        }
        
        // Raycast Setup
        // Origin: Just a few units in front of the ship's nose (not center)
        // Move forward by 3.5 units (just ahead of the nose assuming center is 0,0,0)
        Vector3 laserOrigin = Vector3Add(shipPos, Vector3Scale(shipDir, 3.5f)); 
        // Adjust Y slightly down to align with "belly" or weapon mount, but keep it high enough to see
        laserOrigin.y -= 0.2f; 
        
        // Ray Direction is shipDir
        Vector3 rayDir = Vector3Normalize(shipDir);
        float maxRange = (float)RENDER_DISTANCE; // Limit range to render distance
        Vector3 laserEnd = Vector3Add(laserOrigin, Vector3Scale(rayDir, maxRange));
        
        // Check Collision with ROCKS (Using existing G_Rocks)
        float closestDist = maxRange;
        int hitRockIdx = -1;
        
        for (int i = 0; i < NUM_ROCKS; i++) {
            if (!G_Rocks[i].active) continue;
            
            // Check if rock is within render distance (optimization)
            if (Vector3Distance(G_Rocks[i].position, shipPos) > maxRange) continue;
            
            // Rock radius approximation
            float radius = G_Rocks[i].scale * 0.5f;
            
            // Simple Sphere Intersection check
            Vector3 m = Vector3Subtract(laserOrigin, G_Rocks[i].position);
            float b = Vector3DotProduct(m, rayDir);
            float c = Vector3DotProduct(m, m) - radius * radius;
            
            // Exit if ray origin outside sphere (c > 0) and ray pointing away (b > 0)
            if (c > 0.0f && b > 0.0f) continue;
            
            float discr = b*b - c;
            if (discr < 0.0f) continue; // Ray misses sphere
            
            float t = -b - sqrtf(discr); // Distance to entry point
            if (t < 0.0f) t = 0.0f; // Inside sphere
            
            if (t < closestDist) {
                closestDist = t;
                hitRockIdx = i;
            }
        }
        
        // Check Collision with DEBRIS (Smallest rocks)
        int hitDebrisIdx = -1;
        for (int i = 0; i < MAX_DEBRIS; i++) {
             if (!g_debris[i].active) continue;
             // Check roughly
             Vector3 m = Vector3Subtract(laserOrigin, g_debris[i].position);
             float b = Vector3DotProduct(m, rayDir);
             float r = g_debris[i].scale; 
             float c = Vector3DotProduct(m, m) - r*r;
             if (c > 0.0f && b > 0.0f) continue;
             float discr = b*b - c;
             if (discr < 0.0f) continue;
             float t = -b - sqrtf(discr);
             if (t < closestDist) {
                 closestDist = t;
                 hitDebrisIdx = i;
                 hitRockIdx = -1; // Prioritize debris if closer
             }
        }

        // Draw Laser
        Vector3 hitPoint = Vector3Add(laserOrigin, Vector3Scale(rayDir, closestDist));
        
        // Draw Laser (Thinner: 75% of previous size, Continuous Beam Visual)
        rlDrawRenderBatchActive(); // Flush batch
        BeginBlendMode(BLEND_ADDITIVE);
        
        // Outer Glow (Wide, very transparent cyan)
        // Was 0.4f -> Now 0.3f
        DrawCylinderEx(laserOrigin, hitPoint, 0.3f, 0.3f, 8, (Color){0, 255, 255, 40});
        
        // Inner Glow (Thicker cyan)
        // Was 0.15f -> Now 0.11f
        DrawCylinderEx(laserOrigin, hitPoint, 0.11f, 0.11f, 8, (Color){0, 255, 255, 180});
        
        // Core (White hot center)
        // Was 0.05f -> Now 0.04f
        DrawCylinderEx(laserOrigin, hitPoint, 0.04f, 0.04f, 6, (Color){255, 255, 255, 255});
        
        EndBlendMode();
        
        // Hit Logic
        if (hitRockIdx != -1) {
            // Check if rock explodes based on prosperity percentage
            int prosperity = G_Rocks[hitRockIdx].prosperityPercentage;
            int roll = GetRandomValue(0, 99);
            
            if (roll < prosperity) {
                // Rock explodes
                float rockScale = G_Rocks[hitRockIdx].scale;
                Vector3 rockPos = G_Rocks[hitRockIdx].position;
                
                // Check if this is a smaller rock (scale < 1.0) - if so, spawn debris particles
                // Otherwise spawn smaller rocks
                if (rockScale < 1.0f) {
                    // Smaller rock - check prosperity to spawn collection debris particles
                    int debrisRoll = GetRandomValue(0, 99);
                    if (debrisRoll < prosperity) {
                        // Spawn collection debris particles
                        int particleCount = GetRandomValue(10, 15);
                        SpawnDebris(rockPos, particleCount, rockScale * 2.0f, prosperity);
                        
                        // Play rock sound when debris is released
                        if (g_rockSound.frameCount > 0) {
                            SetSoundVolume(g_rockSound, 0.70f);
                            PlaySound(g_rockSound);
                        }
                    }
                } else {
                    // Large rock - spawn smaller rocks
                    SpawnSmallerRocks(rockPos, rockScale, prosperity);
                    
                    // Large rocks can also spawn debris - check prosperity
                    int debrisRoll = GetRandomValue(0, 99);
                    if (debrisRoll < prosperity) {
                        // Spawn debris particles from large rock
                        int particleCount = GetRandomValue(10, 15);
                        SpawnDebris(rockPos, particleCount, rockScale, prosperity);
                        
                        // Play rock sound when debris is released
                        if (g_rockSound.frameCount > 0) {
                            SetSoundVolume(g_rockSound, 0.70f);
                            PlaySound(g_rockSound);
                        }
                    }
                }
                
                // Destroy original rock
                G_Rocks[hitRockIdx].active = false;
                
                // Particle effect at hit point
                Vector3 normal = {0, 1, 0}; // Approximate
                SpawnCollisionParticles(hitPoint, normal);
            }
            // If roll fails, rock doesn't explode (nothing happens)
            
        } else if (hitDebrisIdx != -1) {
            // Destroy Debris when hit by laser
            g_debris[hitDebrisIdx].active = false;
            Vector3 normal = {0, 1, 0}; 
            SpawnCollisionParticles(hitPoint, normal);
        }
    } else {
        // Stop laser sound if not firing or overheated
        if (IsSoundPlaying(g_laserSound)) {
            StopSound(g_laserSound);
        }
    }
}

// ------------------------------------------------------------
// NAVIGATION SCREEN VARIABLES
// ------------------------------------------------------------
float g_navRotation = 0.0f;
bool g_navModelsLoaded = false;
Model g_navTorusA = {0};
Model g_navIcoB = {0};
Model g_navTorusC = {0};
bool g_showNavModal = false;
int g_navTarget = 0; // 0=None, 1=A, 2=B, 3=C
int g_navSelection = 0; // 0=Engage, 1=Exit

// ------------------------------------------------------------
// RENDER: NAVIGATION SCREEN (3 destinations in triangle)
// ------------------------------------------------------------
void RenderNavScreen() {
    // Initialize render texture if needed
    if (!g_navViewportInitialized) {
        g_navViewport = LoadRenderTexture(RENDER_WIDTH, RENDER_HEIGHT);
        g_navViewportInitialized = true;
    }
    
    // Update rotation
    float dt = GetFrameTime();
    g_navRotation += 20.0f * dt;
    if (g_navRotation > 360) g_navRotation -= 360;
    
    // Load models if needed - use larger sizes to match depot home viewport
    if (!g_navModelsLoaded) {
        // Use GenFlatShadedTorus for better appearance (matching station viewport)
        Mesh meshA = GenFlatShadedTorus(12.0f, 3.0f, 24, 16);  // Large torus for Depot
        g_navTorusA = LoadModelFromMesh(meshA);
        
        Mesh meshB = GenFlatShadedIcosahedron(6.0f);  // Large icosahedron for Hirohito Station
        // Apply cyan color to icosahedron vertices
        if (!meshB.colors) meshB.colors = (unsigned char*)MemAlloc(meshB.vertexCount * 4);
        for (int i = 0; i < meshB.vertexCount; i++) {
            meshB.colors[i * 4 + 0] = 0;    // R
            meshB.colors[i * 4 + 1] = 255;  // G (cyan)
            meshB.colors[i * 4 + 2] = 255;  // B (cyan)
            meshB.colors[i * 4 + 3] = 255;  // A
        }
        g_navIcoB = LoadModelFromMesh(meshB);
        
        Mesh meshC = GenFlatShadedTorus(12.0f, 3.0f, 24, 16);  // Large torus for Nagako's Halo
        // Apply red gradient: dark red bottom, medium red middle, light red top
        // Colors are already allocated by GenFlatShadedTorus, so we just overwrite them
        for (int i = 0; i < meshC.vertexCount; i++) {
            // Get vertex Y position to determine shading
            float yPos = meshC.vertices[i * 3 + 1]; // Y coordinate
            float minY = -3.0f; // Bottom of torus (size * sin(-90°))
            float maxY = 3.0f;  // Top of torus (size * sin(90°))
            float normalizedY = (yPos - minY) / (maxY - minY);
            normalizedY = (normalizedY < 0.0f) ? 0.0f : (normalizedY > 1.0f) ? 1.0f : normalizedY;
            
            // Three shade rule: dark red bottom -> medium red middle -> light red top
            unsigned char r, g, b;
            if (normalizedY < 0.33f) {
                // Bottom third: dark red (100,0,0) to (140,0,0)
                float t = normalizedY / 0.33f;
                r = (unsigned char)(100 + t * 40);
                g = 0;
                b = 0;
            } else if (normalizedY < 0.67f) {
                // Middle third: medium red (140,0,0) to (215,0,0)
                float t = (normalizedY - 0.33f) / 0.34f;
                r = (unsigned char)(140 + t * 75);
                g = 0;
                b = 0;
            } else {
                // Top third: light red (215,0,0) to (255,50,50)
                float t = (normalizedY - 0.67f) / 0.33f;
                r = (unsigned char)(215 + t * 40);
                g = (unsigned char)(t * 50);
                b = (unsigned char)(t * 50);
            }
            
            meshC.colors[i * 4 + 0] = r;
            meshC.colors[i * 4 + 1] = g;
            meshC.colors[i * 4 + 2] = b;
            meshC.colors[i * 4 + 3] = 255;
        }
        g_navTorusC = LoadModelFromMesh(meshC);
        
        g_navModelsLoaded = true;
    }
    
    // Render to texture
    BeginTextureMode(g_navViewport);
    ClearBackground(BLACK);
    
    // Simple Starfield (moving towards camera)
    static float starZ[200];
    static float starX[200];
    static float starY[200];
    static bool starsInit = false;
    
    if (!starsInit) {
        for(int i=0; i<200; i++) {
            starX[i] = (float)GetRandomValue(-RENDER_WIDTH, RENDER_WIDTH);
            starY[i] = (float)GetRandomValue(-RENDER_HEIGHT, RENDER_HEIGHT);
            starZ[i] = (float)GetRandomValue(1, 100) / 10.0f; // 0.1 to 10.0 depth
        }
        starsInit = true;
    }
    
    // Update and Draw Stars
    for(int i=0; i<200; i++) {
        // Move star towards camera (decrease Z)
        starZ[i] -= dt * 2.0f; // Speed
        if (starZ[i] <= 0.1f) {
            starZ[i] = 10.0f; // Reset to back
            starX[i] = (float)GetRandomValue(-RENDER_WIDTH, RENDER_WIDTH);
            starY[i] = (float)GetRandomValue(-RENDER_HEIGHT, RENDER_HEIGHT);
        }
        
        // Project to screen (Perspective)
        float invZ = 1.0f / starZ[i];
        int sx = (int)(RENDER_WIDTH/2 + starX[i] * invZ);
        int sy = (int)(RENDER_HEIGHT/2 + starY[i] * invZ);
        
        if (sx >= 0 && sx < RENDER_WIDTH && sy >= 0 && sy < RENDER_HEIGHT) {
            float brightness = 1.0f - (starZ[i] / 10.0f);
            Color starCol = (Color){255, 255, 255, (unsigned char)(brightness * 255)};
            DrawPixel(sx, sy, starCol);
        }
    }
    
    // Setup camera - looking down slightly upon 3D objects at a different angle
    Camera3D navCamera = {0};
    navCamera.position = (Vector3){2.0f, 4.0f, 14.0f};  // Camera at a different angle, slightly offset
    navCamera.target = (Vector3){0, -1, 0};   // Target slightly below center
    navCamera.up = (Vector3){0, 1, 0};
    navCamera.fovy = 45.0f;
    navCamera.projection = CAMERA_PERSPECTIVE;
    
    BeginMode3D(navCamera);
    rlDisableBackfaceCulling();
    
    // Apply lighting shader (like depot home torus)
    static Shader navShader = {0};
    static bool navShaderLoaded = false;
    static int navLocViewPos = -1;
    static int navLocAmbient = -1;
    static int navLocLightPos[5] = {-1};
    static int navLocLightColor[5] = {-1};
    static int navLocLightDir5 = -1;
    static int navLocLightCut5 = -1;
    
    if (!navShaderLoaded) {
        navShader = LoadShader("lighting.vs", "lighting.fs");
        if (navShader.id == 0) {
            navShader = LoadShader("Data/games/AstroMiner/lighting.vs", "Data/games/AstroMiner/lighting.fs");
        }
        if (navShader.id > 0) {
            navLocViewPos = GetShaderLocation(navShader, "viewPos");
            navLocAmbient = GetShaderLocation(navShader, "ambientColor");
            navLocLightPos[0] = GetShaderLocation(navShader, "lightPos");
            navLocLightColor[0] = GetShaderLocation(navShader, "lightColor");
            navLocLightPos[1] = GetShaderLocation(navShader, "lightPos2");
            navLocLightColor[1] = GetShaderLocation(navShader, "lightColor2");
            navLocLightPos[2] = GetShaderLocation(navShader, "lightPos3");
            navLocLightColor[2] = GetShaderLocation(navShader, "lightColor3");
            navLocLightPos[3] = GetShaderLocation(navShader, "lightPos4");
            navLocLightColor[3] = GetShaderLocation(navShader, "lightColor4");
            navLocLightPos[4] = GetShaderLocation(navShader, "lightPos5");
            navLocLightColor[4] = GetShaderLocation(navShader, "lightColor5");
            navLocLightDir5 = GetShaderLocation(navShader, "lightDir5");
            navLocLightCut5 = GetShaderLocation(navShader, "lightCutoff5");
            
            // Set up lighting (same as station viewport)
            float ambient[3] = { 0.1f, 0.1f, 0.1f };
            SetShaderValue(navShader, navLocAmbient, ambient, SHADER_UNIFORM_VEC3);
            
            float lightColor[3] = { 0.8f, 0.8f, 0.8f };
            Vector3 lightPos = { 0.0f, 50.0f, 0.0f };
            SetShaderValue(navShader, navLocLightColor[0], lightColor, SHADER_UNIFORM_VEC3);
            SetShaderValue(navShader, navLocLightPos[0], &lightPos, SHADER_UNIFORM_VEC3);
            
            float lightColor2[3] = { 0.4f, 0.4f, 0.4f };
            Vector3 lightPos2 = { -40.0f, 0.0f, 0.0f };
            SetShaderValue(navShader, navLocLightColor[1], lightColor2, SHADER_UNIFORM_VEC3);
            SetShaderValue(navShader, navLocLightPos[1], &lightPos2, SHADER_UNIFORM_VEC3);
            
            float lightColor3[3] = { 1.0f, 1.0f, 1.0f };
            Vector3 lightPos3 = { -40.0f, 40.0f, 20.0f };
            SetShaderValue(navShader, navLocLightColor[2], lightColor3, SHADER_UNIFORM_VEC3);
            SetShaderValue(navShader, navLocLightPos[2], &lightPos3, SHADER_UNIFORM_VEC3);
            
            float lightColor4[3] = { 0.8f, 0.9f, 1.0f };
            Vector3 lightPos4 = { 0.0f, 100.0f, 0.0f };
            SetShaderValue(navShader, navLocLightColor[3], lightColor4, SHADER_UNIFORM_VEC3);
            SetShaderValue(navShader, navLocLightPos[3], &lightPos4, SHADER_UNIFORM_VEC3);
            
            // Light 5: Cyan spotlight pointing at icosahedron (center)
            float lightColor5[3] = { 0.0f, 1.0f, 1.0f };  // Cyan
            Vector3 lightPos5 = { 0.0f, 8.0f, 8.0f };  // Position above and behind icosahedron
            Vector3 lightDir5 = { 0.0f, -1.0f, -1.0f };  // Direction towards icosahedron (0,0,0)
            Vector3 normalizedDir = Vector3Normalize(lightDir5);
            SetShaderValue(navShader, navLocLightColor[4], lightColor5, SHADER_UNIFORM_VEC3);
            SetShaderValue(navShader, navLocLightPos[4], &lightPos5, SHADER_UNIFORM_VEC3);
            SetShaderValue(navShader, navLocLightDir5, &normalizedDir, SHADER_UNIFORM_VEC3);
            float cutoff5 = cosf(30.0f * DEG2RAD);  // 30 degree cone
            SetShaderValue(navShader, navLocLightCut5, &cutoff5, SHADER_UNIFORM_FLOAT);
            
            // Apply shader to models
            g_navTorusA.materials[0].shader = navShader;
            g_navIcoB.materials[0].shader = navShader;
            g_navTorusC.materials[0].shader = navShader;
            
            // Set material colors to preserve base colors
            g_navIcoB.materials[0].maps[MATERIAL_MAP_DIFFUSE].color = (Color){0, 255, 255, 255};  // Cyan
            g_navTorusC.materials[0].maps[MATERIAL_MAP_DIFFUSE].color = (Color){255, 100, 100, 255};  // Red
        }
        navShaderLoaded = true;
    }
    
    // Update shader uniforms
    if (navShader.id > 0 && navLocViewPos >= 0) {
        float camPos[3] = { navCamera.position.x, navCamera.position.y, navCamera.position.z };
        SetShaderValue(navShader, navLocViewPos, camPos, SHADER_UNIFORM_VEC3);
        // Update cyan spotlight to point at icosahedron
        Vector3 lightPos5 = { 0.0f, 8.0f, 8.0f };
        Vector3 lightDir5 = { 0.0f, -1.0f, -1.0f };
        Vector3 normalizedDir = Vector3Normalize(lightDir5);
        SetShaderValue(navShader, navLocLightPos[4], &lightPos5, SHADER_UNIFORM_VEC3);
        SetShaderValue(navShader, navLocLightDir5, &normalizedDir, SHADER_UNIFORM_VEC3);
    }
    
    BeginShaderMode(navShader);
    
    // Rearranged layout: Hirohito Station (Icosahedron) in center, two toruses on either side
    // Scale down models 60% smaller (0.15 * 0.4 = 0.06)
    float shapeScale = 0.06f;  // Base scale for icosahedron
    float icosahedronScale = 0.09975f;  // Icosahedron increased by 33% (0.075 * 1.33 = 0.09975)
    float leftTorusScale = 0.108f;  // Left torus increased by 50% (0.072 * 1.5 = 0.108)
    float rightTorusScale = 0.1044f;  // Right torus increased by 45% (0.072 * 1.45 = 0.1044)
    Vector3 rotationAxis = {0, 1, 0};
    
    // B: Icosahedron (Center) - HIROHITO STATION - increased by 33%, cyan colored
    Vector3 posB = {0.0f, 0.0f, 0.0f};
    Color cyanColor = (Color){0, 255, 255, 255};  // Cyan
    DrawModelEx(g_navIcoB, posB, rotationAxis, g_navRotation * DEG2RAD, 
               (Vector3){icosahedronScale, icosahedronScale, icosahedronScale}, cyanColor);
    
    // A: Torus (Left) - SHINJUKU DEPOT - moved 65px to the right
    Vector3 posA = {-5.1f, -0.05f, 0.0f};  // Moved 65px right (approximately 1.3 units)
    DrawModelEx(g_navTorusA, posA, rotationAxis, g_navRotation * DEG2RAD, 
               (Vector3){leftTorusScale, leftTorusScale, leftTorusScale}, WHITE);
    
    // C: Torus (Right) - NAGAKO'S HALO - moved 65px to the left, red gradient colors
    Vector3 posC = {5.1f, 0.0f, 0.0f};  // Moved 65px left (approximately 1.3 units)
    // Use bright red tint to ensure red colors are visible (multiplies with red vertex colors)
    Color redTint = (Color){255, 200, 200, 255};  // Light red tint to enhance red vertex colors
    DrawModelEx(g_navTorusC, posC, rotationAxis, g_navRotation * DEG2RAD, 
               (Vector3){rightTorusScale, rightTorusScale, rightTorusScale}, redTint);
    
    EndShaderMode();
    rlEnableBackfaceCulling();
    EndMode3D();
    
    // Draw labels on render texture - positioned 5px below each 3D object
    // Text size increased by 50% (11 * 1.5 = 16.5, rounded to 17)
    int fontSize = 10;
    int centerX = RENDER_WIDTH / 2;
    int centerY = RENDER_HEIGHT / 2;
    int textOffsetY = 5;  // 5px below 3D objects
    
    // Calculate approximate screen positions based on 3D layout
    // Objects are at Y=0 in 3D, camera looking down, so they appear roughly at centerY
    int objectScreenY = centerY + 20;  // Objects appear slightly below center
    
    // B: Center - HIROHITO STATION (Icosahedron)
    const char* labelB = "HIROHITO STATION [B]";
    int wB = MeasureTextWithFont(labelB, fontSize);
    int textY_B = objectScreenY + textOffsetY;
    // Ensure text doesn't go off screen
    int textX_B = centerX - wB/2;
    if (textX_B < 0) textX_B = 0;
    if (textX_B + wB > RENDER_WIDTH) textX_B = RENDER_WIDTH - wB;
    DrawTextWithFont(labelB, textX_B, textY_B, fontSize, WHITE);
    const char* fuelB = "FUEL REQ: 80";
    int wFuelB = MeasureTextWithFont(fuelB, fontSize);
    Color fuelColB = (G_Player.fuel >= 80) ? GREEN : RED;
    int fuelX_B = centerX - wFuelB/2;
    if (fuelX_B < 0) fuelX_B = 0;
    if (fuelX_B + wFuelB > RENDER_WIDTH) fuelX_B = RENDER_WIDTH - wFuelB;
    DrawTextWithFont(fuelB, fuelX_B, textY_B + fontSize + 2, fontSize, fuelColB);
    
    // A: Left - SHINJUKU DEPOT (Torus)
    const char* labelA = "SHINJUKU DEPOT [A]";
    int fuelReqA = 20;
    int wA = MeasureTextWithFont(labelA, fontSize);
    int textX_A = (int)(RENDER_WIDTH * 0.25f);  // Left side
    int textY_A = objectScreenY + textOffsetY;
    // Ensure text doesn't go off screen
    if (textX_A - wA/2 < 0) textX_A = wA/2;
    if (textX_A + wA/2 > RENDER_WIDTH) textX_A = RENDER_WIDTH - wA/2;
    DrawTextWithFont(labelA, textX_A - wA/2, textY_A, fontSize, (Color){0, 255, 255, 255});
    char fuelA[32];
    snprintf(fuelA, sizeof(fuelA), "FUEL REQ: %d", fuelReqA);
    int wFuelA = MeasureTextWithFont(fuelA, fontSize);
    Color fuelColA = (G_Player.fuel >= fuelReqA) ? GREEN : RED;
    int fuelX_A = textX_A - wFuelA/2;
    if (fuelX_A < 0) fuelX_A = 0;
    if (fuelX_A + wFuelA > RENDER_WIDTH) fuelX_A = RENDER_WIDTH - wFuelA;
    DrawTextWithFont(fuelA, fuelX_A, textY_A + fontSize + 2, fontSize, fuelColA);
    
    // C: Right - NAGAKO'S HALO (Torus)
    const char* labelC = "NAGAKO'S HALO [C]";
    int wC = MeasureTextWithFont(labelC, fontSize);
    int textX_C = (int)(RENDER_WIDTH * 0.75f);  // Right side
    int textY_C = objectScreenY + textOffsetY;
    // Ensure text doesn't go off screen
    if (textX_C - wC/2 < 0) textX_C = wC/2;
    if (textX_C + wC/2 > RENDER_WIDTH) textX_C = RENDER_WIDTH - wC/2;
    DrawTextWithFont(labelC, textX_C - wC/2, textY_C, fontSize, MAGENTA);
    const char* fuelC = "FUEL REQ: 100";
    int wFuelC = MeasureTextWithFont(fuelC, fontSize);
    Color fuelColC = (G_Player.fuel >= 100) ? GREEN : RED;
    int fuelX_C = textX_C - wFuelC/2;
    if (fuelX_C < 0) fuelX_C = 0;
    if (fuelX_C + wFuelC > RENDER_WIDTH) fuelX_C = RENDER_WIDTH - wFuelC;
    DrawTextWithFont(fuelC, fuelX_C, textY_C + fontSize + 2, fontSize, fuelColC);
    
    EndTextureMode();
}

void DrawNavScreen(GameState* state, int* selection) {
    // Draw background from viewport texture
    Texture2D viewTex = g_navViewport.texture;
    Rectangle srcRect = { 0, 0, (float)viewTex.width, (float)-viewTex.height }; // Flip Y
    Rectangle destRect = { 0, 0, VIRTUAL_WIDTH, VIRTUAL_HEIGHT }; // Full virtual screen
    DrawTexturePro(viewTex, srcRect, destRect, (Vector2){0,0}, 0.0f, WHITE);
    
    // Input handling
    if (!g_showNavModal) {
        if (CustomIsKeyPressed(KEY_A)) { PlayTerminalTypeSound(); g_navTarget = 1; g_showNavModal = true; g_navSelection = 0; }
        if (CustomIsKeyPressed(KEY_B)) { PlayTerminalTypeSound(); g_navTarget = 2; g_showNavModal = true; g_navSelection = 0; }
        if (CustomIsKeyPressed(KEY_C)) { PlayTerminalTypeSound(); g_navTarget = 3; g_showNavModal = true; g_navSelection = 0; }
        if (CustomIsKeyPressed(KEY_ESCAPE)) { ResetState(state, selection, STATE_LANDER); }
    } else {
        // MODAL
        DrawRectangle(300, 200, 600, 300, (Color){10, 10, 20, 240});
        DrawRectangleLines(300, 200, 600, 300, WHITE);
        
        const char* targetName = (g_navTarget==1)?"SHINJUKU DEPOT":(g_navTarget==2)?"HIROHITO STATION":"NAGAKO'S HALO";
        int req = (g_navTarget==1)?20:(g_navTarget==2)?80:100;
        bool canGo = G_Player.fuel >= req;
        
        DrawTextWithFont(TextFormat("DESTINATION: %s", targetName), 350, 250, 15, WHITE);
        DrawTextWithFont(TextFormat("FUEL REQUIRED: %d", req), 350, 290, 12, canGo?GREEN:RED);
        DrawTextWithFont(TextFormat("CURRENT FUEL: %.1f", G_Player.fuel), 350, 320, 12, WHITE);
        
        if (!canGo) DrawTextWithFont("INSUFFICIENT FUEL!", 450, 360, 15, RED);
        
        // Buttons
        Color btnCol1 = (g_navSelection==0)?WHITE:GRAY;
        Color btnCol2 = (g_navSelection==1)?WHITE:GRAY;
        
        if (canGo) {
            DrawTextWithFont("> ENGAGE <", 400, 420, 12, btnCol1);
        } else {
            DrawTextWithFont("  ENGAGE  ", 400, 420, 12, DARKGRAY);
        }
        DrawTextWithFont("> EXIT <", 700, 420, 12, btnCol2);
        
        if (CustomIsKeyPressed(KEY_LEFT) || CustomIsKeyPressed(KEY_RIGHT)) g_navSelection = !g_navSelection;
        
        if (CustomIsKeyPressed(KEY_ENTER)) {
            PlayTerminalTypeSound();
            if (g_navSelection == 1) { // Exit
                g_showNavModal = false;
            } else if (canGo) {
                G_Player.fuel -= req;
                if (g_navTarget == 1) {
                    g_currentLocation = 0; // Depot
                    ResetState(state, selection, STATE_DEPOT_HOME);
                } else if (g_navTarget == 2) {
                    g_currentLocation = 1; // Station
                    ResetState(state, selection, STATE_STATION_HOME); 
                } else if (g_navTarget == 3) {
                    g_currentLocation = 2; // Halo
                    ResetState(state, selection, STATE_HALO_HOME); 
                }
                g_showNavModal = false;
            }
        }
    }
}

__declspec(dllexport) __cdecl void UpdateFrame() {
    static int frame_count = 0;
    frame_count++;
    
    if (!g_framebuffer_initialized || !g_game_initialized) {
        if (frame_count % 60 == 0) {
            printf("[UpdateFrame] ERROR: Not initialized! framebuffer=%d, game=%d\n", 
                   g_framebuffer_initialized, g_game_initialized);
        }
        return;
    }
    
    // In standalone mode, poll input from raylib directly
    if (g_standalone_mode) {
        UpdateInputFromRaylib();
    }
    
    // Run one frame of game logic and rendering
    float dt = GetFrameTime();
    
    // Clamp dt to prevent huge jumps or zero values
    if (dt <= 0.0f || dt > 0.1f) {
        dt = 1.0f / 60.0f;  // Default to 60 FPS if invalid
        if (frame_count % 60 == 0) {
            printf("[UpdateFrame] WARNING: Invalid dt, clamped to %.4f\n", dt);
        }
    }

    // Track state transitions per frame to detect entering/leaving the lander
    static GameState prevFrameState = STATE_SPLASH;
    bool enteringLanderThisFrame = (g_currentState == STATE_LANDER && prevFrameState != STATE_LANDER);
    
    // Handle music based on game state
    if (g_currentState == STATE_SPLASH) {
        // On splash screen - only play background music (no bostonpump)
        Music* currentMusic = (g_currentTrack == 0) ? &g_backgroundMusic : &g_backgroundMusic2;
        if (currentMusic->frameCount > 0) {
            // Start background music if not playing yet
            if (!IsMusicStreamPlaying(*currentMusic)) {
                PlayMusicStream(*currentMusic);
                SetMusicVolume(*currentMusic, 0.7f);
            } else {
                UpdateMusicStream(*currentMusic);
            }
        }
        
        // Stop splash music if playing (shouldn't be on splash screen)
        if (IsMusicStreamPlaying(g_splashMusic)) {
            StopMusicStream(g_splashMusic);
            g_splashMusicFadingOut = false;
        }
    } else if (g_showGetReady || g_currentState == STATE_LANDER || g_currentState == STATE_DEBRIS) {
        // On Get Ready screen or in 3D environment - play bostonpump.wav looping with background music
        // Start bostonpump if not playing yet
        if (g_splashMusic.frameCount > 0) {
            if (!IsMusicStreamPlaying(g_splashMusic)) {
                PlayMusicStream(g_splashMusic);
                SetMusicVolume(g_splashMusic, 0.7f);
                g_splashMusicFadingOut = false;
            } else {
                UpdateMusicStream(g_splashMusic);
            }
        }
        
        // Continue playing background music alongside bostonpump
        Music* currentMusic = (g_currentTrack == 0) ? &g_backgroundMusic : &g_backgroundMusic2;
        if (currentMusic->frameCount > 0) {
            if (!IsMusicStreamPlaying(*currentMusic)) {
                PlayMusicStream(*currentMusic);
                SetMusicVolume(*currentMusic, 0.7f);
            } else {
                UpdateMusicStream(*currentMusic);
            }
        }
    } else {
        // Not on splash or in 3D - stop splash music and update background music
        if (IsMusicStreamPlaying(g_splashMusic)) {
            StopMusicStream(g_splashMusic);
            g_splashMusicFadingOut = false;
        }
        
        // Update background music stream and handle track switching with crossfading
        Music* currentMusic = (g_currentTrack == 0) ? &g_backgroundMusic : &g_backgroundMusic2;
        Music* nextMusic = (g_currentTrack == 0) ? &g_backgroundMusic2 : &g_backgroundMusic;
        
        if (currentMusic->frameCount > 0) {
            UpdateMusicStream(*currentMusic);
            
            // Handle Fading
            float length = GetMusicTimeLength(*currentMusic);
            float played = GetMusicTimePlayed(*currentMusic);
            float targetVol = 0.7f;
            float fadeTime = 2.0f; // 2 seconds fade
            
            // Fade In
            if (played < fadeTime) {
                SetMusicVolume(*currentMusic, targetVol * (played / fadeTime));
            }
            // Fade Out
            else if (played > length - fadeTime) {
                float fadeVal = (length - played) / fadeTime;
                if (fadeVal < 0.0f) fadeVal = 0.0f;
                SetMusicVolume(*currentMusic, targetVol * fadeVal);
            }
            // Normal Volume
            else {
                SetMusicVolume(*currentMusic, targetVol);
            }

            // Check if finished
            if (!IsMusicStreamPlaying(*currentMusic) || played >= length) {
                // Track ended, switch
                if (nextMusic->frameCount > 0) {
                    StopMusicStream(*currentMusic); // Ensure stopped
                    SeekMusicStream(*nextMusic, 0.0f);
                    PlayMusicStream(*nextMusic);
                    SetMusicVolume(*nextMusic, 0.0f); // Start silent for fade in
                    g_currentTrack = (g_currentTrack == 0) ? 1 : 0;
                } else {
                    // If next track failed to load, loop current
                    StopMusicStream(*currentMusic);
                    SeekMusicStream(*currentMusic, 0.0f);
                    PlayMusicStream(*currentMusic);
                    SetMusicVolume(*currentMusic, 0.0f);
                }
            }
        }
    }

    // Update Station Viewport (Animation)
    stationViewport.Update(dt);
    
    // Render Station Viewport (Offscreen) to low-res target
    // Use correct station type based on current location
    StationType activeStationType = STATION_ALPHA; // Default (Depot)
    if (g_currentState == STATE_STATION_HOME) {
        activeStationType = STATION_BETA; // Icosahedron for Hirohito
    } else if (g_currentState == STATE_HALO_HOME) {
        activeStationType = STATION_GAMMA; // Angled Torus for Nagako
    } else if (g_currentState == STATE_DEPOT_HOME) {
        activeStationType = STATION_ALPHA; // Torus for Depot
    }
    stationViewport.Render(activeStationType);
    
    // Render Asteroid Prospect Viewport (Offscreen) if active
    // This matches the method used for the station viewport to prevent zoom issues
    // Asteroid prospects are available at Depot, Station, and Halo
    if ((g_currentState == STATE_DEPOT_HOME || g_currentState == STATE_STATION_HOME || g_currentState == STATE_HALO_HOME) 
        && g_showProspectAsteroids && g_depotHomePage == 1) {
        RenderAsteroidProspects();
    }
    
    // Render shipyard shop 3D items
    bool isShopActive = (g_currentState == STATE_DEPOT_HOME || g_currentState == STATE_STATION_HOME || g_currentState == STATE_HALO_HOME) && 
                        g_showShipyardShop && g_depotHomePage == 2;
                        
    if (isShopActive) {
        RenderShipyardShop();
    }
    

    
    // Render navigation screen viewport
    if (g_currentState == STATE_NAV_SCREEN) {
        RenderNavScreen();
    }
    
    // Start rendering to framebuffer (low resolution)
    BeginTextureMode(g_framebuffer);
    ClearBackground((Color){5, 5, 10, 255});
    
    // Scale Logic: Virtual (1200x800) -> Render (600x400)
    Camera2D screenCam = {0};
    // Fix: Use aspect-correct scaling (fit within screen)
    float scaleX = (float)RENDER_WIDTH / (float)VIRTUAL_WIDTH;
    float scaleY = (float)RENDER_HEIGHT / (float)VIRTUAL_HEIGHT;
    float finalZoom = (scaleX < scaleY) ? scaleX : scaleY;
    
    screenCam.zoom = finalZoom;
    
    // Center the content
    screenCam.offset.x = (RENDER_WIDTH - (VIRTUAL_WIDTH * finalZoom)) / 2.0f;
    screenCam.offset.y = (RENDER_HEIGHT - (VIRTUAL_HEIGHT * finalZoom)) / 2.0f;
    
    // Use Camera2D to scale all 2D drawing calls
    BeginMode2D(screenCam);
    
    // Debug: Log current state occasionally
    static int state_log_counter = 0;
    state_log_counter++;
    if (state_log_counter == 1 || state_log_counter % 180 == 0) {
        printf("[UpdateFrame] Current state: %d (STATE_SPLASH=%d, STATE_DEPOT_HOME=%d)\n", 
               g_currentState, STATE_SPLASH, STATE_DEPOT_HOME);
    }
    
    // Check for GET READY splash screen (shown before transitioning to lander)
    if (g_showGetReady) {
        EnableCursor();
        DrawPageGetReady(&g_currentState, &g_menuSelection);
        DrawScanlines();
        EndMode2D();
        EndTextureMode();
        ClearInputFrame();
        return; // Early return, don't process other states
    }
    
    switch(g_currentState) {
        case STATE_SPLASH: {
            static int splash_state_count = 0;
            splash_state_count++;
            if (splash_state_count == 1 || splash_state_count % 60 == 0) {
                printf("[UpdateFrame] STATE_SPLASH active! Frame %d, splashIndex=%d\n", splash_state_count, g_splashIndex);
            }
            EnableCursor();
            DrawPageSplash(&g_currentState, &g_menuSelection, &g_shipPos, &g_shipVel, dt);
            DrawScanlines();
            break;
        }
            
        case STATE_DEPOT_HOME:
            EnableCursor();
            DrawPageDepotHome(&g_currentState, &g_menuSelection, &g_shipPos, &g_shipVel);
            DrawScanlines();
            break;

        case STATE_STATION_HOME:
            EnableCursor();
            DrawPageStationHome(&g_currentState, &g_menuSelection, &g_shipPos, &g_shipVel);
            DrawScanlines();
            break;

        case STATE_HALO_HOME:
            EnableCursor();
            DrawPageHaloHome(&g_currentState, &g_menuSelection, &g_shipPos, &g_shipVel);
            DrawScanlines();
            break;

        case STATE_DEBRIS:
            EnableCursor();
            HandleESCNavigation(&g_currentState, &g_menuSelection);
            DrawPageDebris(&g_currentState, &g_menuSelection);
            DrawScanlines();
            break;

        case STATE_DEPOT_SELECT:
            EnableCursor();
            HandleESCNavigation(&g_currentState, &g_menuSelection);
            DrawPageDepotSelect(&g_currentState, &g_menuSelection);
            DrawScanlines();
            break;

        case STATE_BAR:
            EnableCursor();
            HandleESCNavigation(&g_currentState, &g_menuSelection);
            DrawPageBar(&g_currentState, &g_menuSelection);
            DrawScanlines();
            break;
            
        case STATE_SHIPYARD:
            EnableCursor();
            HandleESCNavigation(&g_currentState, &g_menuSelection);
            DrawPageShipyard(&g_currentState, &g_menuSelection);
            DrawScanlines();
            break;
            
        case STATE_MARKET:
            EnableCursor();
            HandleESCNavigation(&g_currentState, &g_menuSelection);
            DrawPageMarket(&g_currentState, &g_menuSelection);
            DrawScanlines();
            break;
            
        case STATE_LODGINGS:
            EnableCursor();
            HandleESCNavigation(&g_currentState, &g_menuSelection);
            DrawPageLodgings(&g_currentState, &g_menuSelection);
            DrawScanlines();
            break;

        case STATE_GAME_OVER:
            EnableCursor();
            DrawPageGameOver(&g_currentState, &g_menuSelection);
            DrawScanlines();
            break;

        case STATE_NAV_SCREEN:
            EnableCursor();
            DrawNavScreen(&g_currentState, &g_menuSelection);
            DrawScanlines();
            break;

        case STATE_LANDER:
            DisableCursor();
            
            // Handle ESC for pause/unpause (override normal ESC navigation)
            if (CustomIsKeyPressed(KEY_ESCAPE)) {
                g_isPaused = !g_isPaused;
                PlayTerminalTypeSound();
            }
            
            // Only handle ESC navigation if not paused (and ESC wasn't just pressed)
            if (!g_isPaused) {
                // Don't call HandleESCNavigation here - ESC is now for pause
            }
        {
            // End 2D Mode for 3D rendering to use full framebuffer natively
            EndMode2D();
            
            // Reset pause state when entering lander
            if (g_currentState == STATE_LANDER && g_previousState != STATE_LANDER) {
                g_isPaused = false;  // Reset pause when entering lander
                g_shouldCenterMouse = true;  // Signal mouse should be centered when entering lander
            }
            
            // Reset environment on first frame entering lander - fresh rocks, no debris
            if (enteringLanderThisFrame) {
                // Just entered STATE_LANDER - reset everything for fresh environment
                GenerateRocksAndCollision();
                InitCollisionGrid();
                // Clear all particles/debris - completely fresh start
                for (int i = 0; i < MAX_PARTICLES; i++) {
                    particles[i].life = 0.0f;
                    particles[i].onGround = false;
                }
                // Clear all debris chunks - no leftover debris when launching
                for (int i = 0; i < MAX_DEBRIS; i++) {
                    g_debris[i].active = false;
                }
            }
            
            static int lander_frame = 0;
            lander_frame++;
            
            static float laserErrorDisplayTime = 0.0f;  // Track laser error display time
            static bool wasColliding = false;  // Track if we were colliding last frame
            static Vector3 prevShipPos = {0, 0, 0};  // Track previous position for collision detection
            static bool explosionTriggered = false;  // Track if explosion has been triggered
            static Vector3 frozenCameraPos = {0, 0, 0};  // Store camera position when explosion happens
            static Vector3 explosionPos = {0, 0, 0};  // Store explosion position
            static bool cameraFrozen = false;  // Track if camera has been frozen
            
            // Reset explosion flag if hull is at max (fresh mission started)
            if (G_Player.hull >= G_Player.maxHull) {
                explosionTriggered = false;
                cameraFrozen = false;  // Reset camera frozen state
            }
            
            // Check if explosion particles have all landed, then transition to game over
            if (explosionTriggered && !HasActiveExplosionParticles()) {
                ResetState(&g_currentState, &g_menuSelection, STATE_GAME_OVER);
                explosionTriggered = false;  // Reset for next game
                wasColliding = false;
                prevShipPos = (Vector3){0, 0, 0};
            }
            
            // LANDER LOGIC (Existing 3D Game)
            // Calculate ship rotation and forward vector (needed for drawing even when paused)
            // --- Input ---
            Vector2 mouseDelta = CustomGetMouseDelta();
            
            // Center mouse after reading input to prevent edge case where mouse at position 0
            // prevents further movement in that direction
            // Reset mouse delta after reading to prevent accumulation issues
            g_inputState.mouseDelta = (Vector2){0.0f, 0.0f};
            
            // Only update input if not paused
            if (!g_isPaused) {
            g_shipPitch -= mouseDelta.y * 0.15f; 
            g_shipRoll -= mouseDelta.x * 0.15f; 
            if (fabs(mouseDelta.x) < 0.1f) g_shipRoll = Lerp(g_shipRoll, 0.0f, 1.0f * dt);
            g_shipPitch = Clamp(g_shipPitch, -85.0f, 85.0f);
            if (CustomIsMouseButtonReleased(MOUSE_BUTTON_RIGHT)) g_yawDirection *= -1;
            if (CustomIsMouseButtonDown(MOUSE_BUTTON_RIGHT)) g_shipYaw -= 120.0f * dt * (float)g_yawDirection;
            }

            // Always calculate rotation matrix and forward vector (needed for drawing)
            Matrix matRoll = MatrixRotateZ(DEG2RAD * -g_shipRoll);
            Matrix matPitch = MatrixRotateX(DEG2RAD * g_shipPitch);
            Matrix matYaw = MatrixRotateY(DEG2RAD * g_shipYaw);
            Matrix rot = MatrixMultiply(MatrixMultiply(matPitch, matRoll), matYaw);
            Vector3 shipForward = { rot.m8, rot.m9, rot.m10 }; 
            Vector3 shipUp = { rot.m4, rot.m5, rot.m6 };
            
            // Only update game logic if not paused
            if (!g_isPaused) {        

            // --- Physics & Systems ---
            UpdateRocksAndDebris(dt, g_shipPos);

            // Check if ship is inside navigation target cylinder (zero gravity zone)
            Vector3 targetCylPos = {0.0f, 0.0f, 0.0f};
            float targetCylRadius = 5.0f; // 50% smaller (was 10.0f)
            float targetCylTerrainH = GetTerrainHeight(0.0f, 0.0f);
            float targetCylTop = targetCylTerrainH + 300.0f;
            float distToCylXZ = sqrtf(powf(g_shipPos.x - targetCylPos.x, 2) + powf(g_shipPos.z - targetCylPos.z, 2));
            bool insideTargetCyl = (distToCylXZ < targetCylRadius && g_shipPos.y >= targetCylTerrainH && g_shipPos.y <= targetCylTop);

            // Calculate dynamic gravity based on asteroid gravity + cargo effect
            float asteroidGravityFactor = (float)g_selectedAsteroidGravity / 100.0f;
            float cargoGravityFactor = (float)G_Player.cargoFilled / 25.0f;  // Max 25
            float baseGravity = -12.0f;
            float minGravity = -6.0f;
            float maxGravity = -18.0f;
            
            float asteroidGravity = Lerp(minGravity, maxGravity, asteroidGravityFactor);
            float cargoGravityBonus = cargoGravityFactor * -1.0f; // Max -1.0 at full cargo (was -4.0)
            float dynamicGravity = asteroidGravity + cargoGravityBonus;
            
            // Zero gravity inside target cylinder + auto-thrust and stabilization
            bool autoThrusting = false;
            if (insideTargetCyl) {
                // Play beam-up sound when ship first enters the cylinder
                if (!g_wasInsideCylinder && g_beamUpSound.frameCount > 0) {
                    PlaySound(g_beamUpSound);
                    g_wasInsideCylinder = true;
                }
                
                dynamicGravity = 0.0f;
                // Auto-thrust: apply upward thrust automatically
                autoThrusting = true;
                // Stabilize ship: reduce pitch, roll, and yaw rotation
                g_shipPitch = Lerp(g_shipPitch, 0.0f, 3.0f * dt); // Stabilize pitch
                g_shipRoll = Lerp(g_shipRoll, 0.0f, 3.0f * dt);   // Stabilize roll
                // Reduce horizontal velocity to center in cylinder
                g_shipVel.x = Lerp(g_shipVel.x, 0.0f, 2.0f * dt);
                g_shipVel.z = Lerp(g_shipVel.z, 0.0f, 2.0f * dt);
                
                // Check if reached altitude 20 (relative to terrain) and switch to navigation screen
                float altAboveTerrain = g_shipPos.y - targetCylTerrainH;
                if (altAboveTerrain >= 20.0f) {
                    ResetState(&g_currentState, &g_menuSelection, STATE_NAV_SCREEN);
                    g_wasInsideCylinder = false; // Reset flag when leaving
                }
            } else {
                // Reset flag when ship leaves the cylinder
                g_wasInsideCylinder = false;
            }
            
            // If fuel is empty, apply 500% gravity (5x normal gravity) - massive downward pull
            if (G_Player.fuel <= 0.0f && !insideTargetCyl) {
                dynamicGravity = dynamicGravity * 5.0f; // 500% gravity effect - ship will crash hard
            }
            g_shipVel.y += dynamicGravity * dt;

            // Thrust Logic with Cargo Penalty (or auto-thrust if inside cylinder)
            bool isThrusting = CustomIsMouseButtonDown(MOUSE_LEFT_BUTTON) || CustomIsKeyDown(KEY_W) || autoThrusting;
            
            // Only allow thrusting if fuel is available
            if (isThrusting && G_Player.fuel > 0.0f && !explosionTriggered) {
                // Apply thruster boost and cargo penalty (-5% per cargo unit)
                float cargoPenalty = G_Player.cargoFilled * 0.05f; // 5% per cargo unit
                float thrustMultiplier = (1.0f - cargoPenalty);
                if (thrustMultiplier < 0.65f) thrustMultiplier = 0.65f; // Minimum 65% thrust
                
                float effectiveThrustPower = SHIP_THRUST_POWER * G_Player.thrusterBoost * thrustMultiplier;
                
                g_shipVel = Vector3Add(g_shipVel, Vector3Scale(shipUp, effectiveThrustPower * dt));
                
                // Spawn particles on the ship
                Vector3 engineNozzle = g_shipPos; // Spawn directly on ship
                SpawnThrustParticles(engineNozzle, shipUp);
                
                // Consume fuel based on burn rate
                // Fix: Fuel Upgrade reduces consumption by 50%
                float burnRate = SHIP_FUEL_BURN_RATE;
                if (G_Player.hasFuelTankUpgrade) burnRate *= 0.5f;
                
                G_Player.fuel -= burnRate * dt;
                if (G_Player.fuel < 0.0f) G_Player.fuel = 0.0f;

                // Play thruster sound (looping)
                if (!IsSoundPlaying(g_thrusterSound)) {
                    PlaySound(g_thrusterSound);
                }
            } else {
                // Stop thruster sound if not thrusting or out of fuel
                if (IsSoundPlaying(g_thrusterSound)) {
                    StopSound(g_thrusterSound);
                }

                if (isThrusting && G_Player.fuel <= 0.0f && !explosionTriggered) {
                    // Fuel depleted - no thrust available
                    // Visual/audio feedback could be added here
                }
            }
            
            // Note: Laser logic moved to drawing phase for visuals, but input checked there too.
            // Check for NO LASER error here only if space pressed and no laser
            if (CustomIsKeyPressed(KEY_SPACE) && !G_Player.hasLaser) {
                 laserErrorDisplayTime = 2.0f;
            }
            
            // Update error display timer
            if (laserErrorDisplayTime > 0.0f) {
                laserErrorDisplayTime -= dt;
            }
            
            g_shipVel = Vector3Scale(g_shipVel, SHIP_DRAG_FACTOR);
            Vector3 nextPos = Vector3Add(g_shipPos, Vector3Scale(g_shipVel, dt));

            // --- Terrain Collision ---
            float worldH = GetWorldHeight(nextPos.x, nextPos.z);
            float softCeiling = worldH + 12.0f;
            if (nextPos.y > softCeiling) {
                 g_shipVel.y -= (nextPos.y - softCeiling) * 2.0f * dt;
                 nextPos = Vector3Add(g_shipPos, Vector3Scale(g_shipVel, dt));
            }
            
            // Always ensure ship is above terrain - prevent embedding
            // Use a larger clearance to account for shadow (at +0.15f) and prevent getting stuck
            float minTerrainHeight = worldH + 1.8f; // Increased clearance to prevent shadow/terrain sticking
            if (nextPos.y < minTerrainHeight && !explosionTriggered) {
                // Force ship above terrain immediately - always snap, no lerp to prevent sticking
                nextPos.y = minTerrainHeight;
                
                bool isNewCollision = !wasColliding;
                wasColliding = true;
                
                // Apply damage every frame while embedded in terrain
                if (G_Player.hull > 0) {
                    float collisionVelocity = Vector3Length(g_shipVel);
                    float highVelocityThreshold = 15.0f;
                    
                    if (isNewCollision) {
                        Vector3 collisionNormal = {0, 1, 0};
                        SpawnCollisionParticles(nextPos, collisionNormal);
                        SpawnAsteroidDebris(nextPos);

                        // Fix: One collision = 10 units of hull damage (unless gravity > 50% then 20 units)
                        float damagePerHit = 10.0f;
                        if (g_selectedAsteroidGravity > 50) damagePerHit = 20.0f;
                        damagePerHit *= G_Player.hullResistance;
                        
                        // If out of fuel, ANY collision is instant death
                        if (G_Player.fuel <= 0.0f) damagePerHit = 99999.0f;

                        int hullBefore = (int)G_Player.hull;
                        G_Player.hull -= damagePerHit;
                        int hullAfter = (int)G_Player.hull;
                        // Play crash sound if hull crossed an integer boundary downward
                        if (hullAfter < hullBefore && g_crashSound.frameCount > 0) {
                            PlaySound(g_crashSound);
                        }
                    }
                    
                    if (collisionVelocity > highVelocityThreshold) {
                        int hullBefore = (int)G_Player.hull;
                        G_Player.hull = 0;
                        // Play crash sound if hull was above 0 and is now 0
                        if (hullBefore > 0 && g_crashSound.frameCount > 0) {
                            PlaySound(g_crashSound);
                        }
                    } else {
                        // Continuous damage while stuck in terrain
                        int hullBefore = (int)G_Player.hull;
                        float damageAmount = 2.0f * G_Player.hullResistance * dt;
                        G_Player.hull -= damageAmount;
                        if (G_Player.hull < 0) G_Player.hull = 0;
                        int hullAfter = (int)G_Player.hull;
                        // Play crash sound if hull crossed an integer boundary downward
                        if (hullAfter < hullBefore && g_crashSound.frameCount > 0) {
                            PlaySound(g_crashSound);
                        }
                    }
                    
                    if (G_Player.hull <= 0 && !explosionTriggered) {
                        explosionPos = nextPos;
                        SpawnExplosionParticles(nextPos);
                        // Play explode sound immediately when ship is destroyed
                        if (g_explodeSound.frameCount > 0) {
                            PlaySound(g_explodeSound);
                        }
                        explosionTriggered = true;
                        frozenCameraPos = g_camera.position;
                        float worldH = GetWorldHeight(frozenCameraPos.x, frozenCameraPos.z);
                        if (frozenCameraPos.y < worldH + 10.0f) frozenCameraPos.y = worldH + 10.0f;
                        cameraFrozen = true;
                    }
                }
                
                // Strong upward push to prevent sticking - ensure escape velocity
                if (g_shipVel.y < 4.0f) g_shipVel.y = 4.0f; // Higher minimum upward velocity
                g_shipVel.y += 10.0f * dt; // Stronger upward acceleration
                // Dampen horizontal velocity more to help vertical escape
                g_shipVel.x *= 0.5f;
                g_shipVel.z *= 0.5f;
            } else {
                wasColliding = false;
            }
            
            prevShipPos = g_shipPos;
            
            // --- Boundary & Orbit Detection ---
            if (g_shipPos.y > 80.0f) {
                if (g_missionInProgress) {
                    int returnFuelCost = g_selectedAsteroidFuelCost / 2;
                    G_Player.fuel -= returnFuelCost;
                    if (G_Player.fuel < 0) G_Player.fuel = 0;
                    g_missionInProgress = false;
                }
                ResetState(&g_currentState, &g_menuSelection, STATE_DEPOT_SELECT);
            }
            
            // --- Rock Collision ---
            // Multiple pass collision resolution to prevent getting stuck
            float rockCollisionRadius = 0.8f;
            bool hitAnyRock = false;
            const int MAX_ROCK_PASSES = 3;
            
            for (int pass = 0; pass < MAX_ROCK_PASSES; pass++) {
                bool collisionThisPass = false;
                
            for (int i = 0; i < NUM_ROCKS && G_Player.hull > 0 && !explosionTriggered; i++) {
                if (!G_Rocks[i].active) continue; // Skip inactive rocks
                
                float rockRadius = G_Rocks[i].scale * 0.5f;
                float distance = Vector3Distance(nextPos, G_Rocks[i].position);
                    float minDistance = rockCollisionRadius + rockRadius + 0.4f; // Extra clearance buffer
                    
                    // If ship is inside or touching the rock, push it out and apply damage
                    if (distance < minDistance) {
                        collisionThisPass = true;
                        hitAnyRock = true;
                        
                        // Calculate push direction (from rock center to ship)
                        Vector3 pushDir;
                        if (distance < 0.01f) {
                            // Ship is exactly at rock center - push upward and away from previous position
                            Vector3 escapeDir = Vector3Normalize(Vector3Subtract(nextPos, prevShipPos));
                            if (Vector3Length(escapeDir) < 0.01f) {
                                escapeDir = (Vector3){0.0f, 1.0f, 0.0f}; // Default to up
                            }
                            pushDir = Vector3Normalize(Vector3Add((Vector3){0.0f, 0.7f, 0.0f}, Vector3Scale(escapeDir, 0.3f)));
                        } else {
                            pushDir = Vector3Normalize(Vector3Subtract(nextPos, G_Rocks[i].position));
                        }
                        
                        // Always push ship outside the rock with generous clearance to prevent re-embedding
                        float pushDistance = minDistance + 1.0f; // Large clearance
                        nextPos = Vector3Add(G_Rocks[i].position, Vector3Scale(pushDir, pushDistance));
                        
                        // Apply damage on collision (Discrete, not continuous)
                        float collisionVelocity = Vector3Length(g_shipVel);
                        if (collisionVelocity > 15.0f) {
                            int hullBefore = (int)G_Player.hull;
                            G_Player.hull = 0; // Instant destruction at high speed
                            // Play crash sound if hull was above 0 and is now 0
                            if (hullBefore > 0 && g_crashSound.frameCount > 0) {
                                PlaySound(g_crashSound);
                            }
                        } else {
                            // Fix: One collision = 10 units of hull damage (unless gravity > 50% then 20 units)
                            float damagePerHit = 10.0f;
                            
                            // Check asteroid gravity
                            if (g_selectedAsteroidGravity > 50) damagePerHit = 20.0f;
                            
                            // Sheet Metal (Hull Resistance/Exo-Plating) alters this.
                            damagePerHit *= G_Player.hullResistance;
                            
                            // If out of fuel, ANY collision is instant death
                            if (G_Player.fuel <= 0.0f) damagePerHit = 99999.0f;
                            
                            // Apply instantaneous damage
                            // The collision resolution pushes the ship out, so this happens once per hit.
                            int hullBefore = (int)G_Player.hull;
                            G_Player.hull -= damagePerHit;

                            if (G_Player.hull < 0) G_Player.hull = 0;
                            int hullAfter = (int)G_Player.hull;
                            // Play crash sound if hull crossed an integer boundary downward
                            if (hullAfter < hullBefore && g_crashSound.frameCount > 0) {
                                PlaySound(g_crashSound);
                            }
                         }
                        
                        // Spawn collision particles
                        Vector3 negPushDir = Vector3Scale(pushDir, -1.0f);
                        SpawnCollisionParticles(nextPos, negPushDir);
                        
                        // Strong bounce velocity - push ship away from rock
                        float bounceStrength = 15.0f; // Very strong push to escape
                        g_shipVel = Vector3Add(g_shipVel, Vector3Scale(pushDir, bounceStrength));
                        // Less dampening to allow ship to escape
                        g_shipVel = Vector3Scale(g_shipVel, 0.6f);
                        
                        // Ensure minimum escape velocity
                        if (Vector3Length(g_shipVel) < 3.0f) {
                            g_shipVel = Vector3Scale(Vector3Normalize(pushDir), 3.0f);
                        }
                        
                        // Check for destruction
                        if (G_Player.hull <= 0 && !explosionTriggered) {
                            explosionPos = nextPos;
                            SpawnExplosionParticles(nextPos);
                            // Play explode sound immediately when ship is destroyed
                            if (g_explodeSound.frameCount > 0) {
                                PlaySound(g_explodeSound);
                            }
                            explosionTriggered = true;
                            frozenCameraPos = g_camera.position;
                            float worldH = GetWorldHeight(frozenCameraPos.x, frozenCameraPos.z);
                            if (frozenCameraPos.y < worldH + 10.0f) frozenCameraPos.y = worldH + 10.0f;
                            cameraFrozen = true;
                            break;
                        }
                    }
                }
                
                // If no collisions this pass, we're done
                if (!collisionThisPass) break;
            }
            
            // Final safety check - ensure ship is never stuck in terrain or objects
            float finalWorldH = GetWorldHeight(nextPos.x, nextPos.z);
            float finalMinHeight = finalWorldH + 1.8f;
            if (nextPos.y < finalMinHeight && !explosionTriggered) {
                // Emergency push out - ship should never be here after collision resolution
                nextPos.y = finalMinHeight;
                if (g_shipVel.y < 5.0f) g_shipVel.y = 5.0f; // Force escape velocity
            }
            
            // Check for any remaining rock collisions (safety net)
            for (int i = 0; i < NUM_ROCKS && !explosionTriggered; i++) {
                if (!G_Rocks[i].active) continue;
                float rockRadius = G_Rocks[i].scale * 0.5f;
                float distance = Vector3Distance(nextPos, G_Rocks[i].position);
                float minDistance = 0.8f + rockRadius + 0.4f;
                if (distance < minDistance) {
                    // Emergency push out
                    Vector3 pushDir = (distance < 0.01f) ? (Vector3){0.0f, 1.0f, 0.0f} : 
                                     Vector3Normalize(Vector3Subtract(nextPos, G_Rocks[i].position));
                    nextPos = Vector3Add(G_Rocks[i].position, Vector3Scale(pushDir, minDistance + 1.0f));
                    g_shipVel = Vector3Add(g_shipVel, Vector3Scale(pushDir, 10.0f));
                }
            }
            
            if (nextPos.x > PROSPECT_PERIMETER) { nextPos.x = PROSPECT_PERIMETER; g_shipVel.x = 0; }
            if (nextPos.x < -PROSPECT_PERIMETER) { nextPos.x = -PROSPECT_PERIMETER; g_shipVel.x = 0; }
            if (nextPos.z > PROSPECT_PERIMETER) { nextPos.z = PROSPECT_PERIMETER; g_shipVel.z = 0; }
            if (nextPos.z < -PROSPECT_PERIMETER) { nextPos.z = -PROSPECT_PERIMETER; g_shipVel.z = 0; }
            g_shipPos = nextPos;

            // --- Camera ---
            if (!explosionTriggered) {
                const float CAM_FOLLOW_DIST = 9.0f; 
                const float CAM_HEIGHT_OFFSET = 4.0f;
                Vector3 camOffset = Vector3Scale(shipForward, -CAM_FOLLOW_DIST); 
                camOffset.y += CAM_HEIGHT_OFFSET;
                g_camera.position = Vector3Lerp(g_camera.position, Vector3Add(g_shipPos, camOffset), 5.0f * dt);
                if (g_camera.position.y < 0.5f) g_camera.position.y = 0.5f;
                g_camera.target = g_shipPos;
            } else {
                g_camera.position = frozenCameraPos;
                g_camera.target = explosionPos;
            }

            UpdateParticles(dt);
            } // End of pause check - game logic updates only when not paused

            // --- Draw 3D Scene ---
            BeginMode3D(g_camera);
                // Chunks
                float cullDist = RENDER_DISTANCE + (CHUNK_SIZE * 0.8f); 
                for(int i=0; i<TOTAL_CHUNKS; i++) {
                    if (fabs(g_shipPos.x - g_chunkCenters[i].x) < cullDist && fabs(g_shipPos.z - g_chunkCenters[i].y) < cullDist) {
                        DrawModel(g_chunkModels[i], (Vector3){0,0,0}, 1.0f, WHITE);
                    }
                }
                DrawPerimeterBorder(g_shipPos);
                
                if (!explosionTriggered) {
                    DrawProjectedShadow(g_shipPos);
                    
                    // Select the correct ship model based on color upgrade
                    Model* shipModelToDraw = &g_ship; // Default Blue
                    if (G_Player.shipColor == 1) shipModelToDraw = &g_stationShopModels[3]; // Red
                    else if (G_Player.shipColor == 2) shipModelToDraw = &g_stationShopModels[4]; // Green
                    else if (G_Player.shipColor == 3) shipModelToDraw = &g_stationShopModels[5]; // Purple
                    else if (G_Player.shipColor == 4) shipModelToDraw = &g_goldShipModel; // Gold
                    
                    // Apply rotation transform to the selected model
                    shipModelToDraw->transform = rot;
                    
                    DrawModel(*shipModelToDraw, g_shipPos, 1.0f, WHITE);
                }
                
                // Rocks
                rlDisableBackfaceCulling(); 
                for(int i = 0; i < NUM_ROCKS; i++) {
                    if (!G_Rocks[i].active) continue; // Skip inactive
                    if (fabs(G_Rocks[i].position.x - g_shipPos.x) < (float)RENDER_DISTANCE && fabs(G_Rocks[i].position.z - g_shipPos.z) < (float)RENDER_DISTANCE) {
                        DrawModelEx(g_rockModel, G_Rocks[i].position, G_Rocks[i].axis, G_Rocks[i].angle, (Vector3){G_Rocks[i].scale, G_Rocks[i].scale, G_Rocks[i].scale}, G_Rocks[i].color);
                    }
                }
                
                // Debris (collection debris - cyan with glow)
                for (int i=0; i<MAX_DEBRIS; i++) {
                    if (g_debris[i].active) {
                        Color debrisColor = g_debris[i].color;
                        // Check if this is collection debris (cyan)
                        bool isCollectionDebris = (debrisColor.r == 0 && debrisColor.g == 255 && debrisColor.b == 255);
                        if (isCollectionDebris) {
                            // Draw glow effect for collection debris (draw slightly larger, brighter version behind)
                            float glowSize = g_debris[i].scale * 1.5f;
                            Color glowColor = {debrisColor.r, debrisColor.g, debrisColor.b, (unsigned char)(debrisColor.a * 0.5f)}; // Semi-transparent glow
                            DrawCube(g_debris[i].position, glowSize, glowSize, glowSize, glowColor);
                        }
                        DrawCube(g_debris[i].position, g_debris[i].scale, g_debris[i].scale, g_debris[i].scale, g_debris[i].color);
                    }
                }
                
                // Navigation Target Marker (Red cylinder on terrain surface at 0,0,0)
                // Only draw if within render distance (like other objects)
                Vector3 targetPos = {0.0f, 0.0f, 0.0f};
                if (fabs(g_shipPos.x - targetPos.x) < (float)RENDER_DISTANCE && fabs(g_shipPos.z - targetPos.z) < (float)RENDER_DISTANCE) {
                    float targetTerrainH = GetTerrainHeight(0.0f, 0.0f);
                    float targetHeight = 300.0f; // Tall cylinder
                    float targetRadius = 5.0f; // 50% smaller (was 10.0f, originally 20.0f)
                    Vector3 targetDrawPos = {0.0f, targetTerrainH, 0.0f};
                    
                    // Draw tall red cylinder (no wireframe)
                rlDrawRenderBatchActive();
                BeginBlendMode(BLEND_ALPHA);
                    // 60% opacity = alpha 153 (255 * 0.6 = 153)
                    DrawCylinder(targetDrawPos, targetRadius, targetRadius, targetHeight, 32, (Color){255, 0, 0, 153}); // Red, 60% transparent
                EndBlendMode();
                }
                
                // Laser Visuals (only update when not paused)
                if (!g_isPaused) {
                    UpdateLaserLogic(dt, g_shipPos, shipForward);
                }
                
                rlEnableBackfaceCulling();
                DrawParticles();
            EndMode3D();
            
            // Re-enable 2D Mode for HUD overlay
            BeginMode2D(screenCam);
            
            // --- UI Overlay ---
            // FPS display - REMOVED per user request
            
            int screenH = VIRTUAL_HEIGHT;
            
            // Check if cargo is full (used for flashing effects)
            bool cargoFull = (G_Player.cargoFilled >= 25);
            bool cargoFlashOn = cargoFull && ((int)(GetTime() * 4) % 2 == 0); // Flash 4 times per second
            
            // Altitude Meter - REMOVED per user request
            
            // Fuel gauge
            int fuelBars = (int)(G_Player.fuel / 10.0f);
            DrawTextWithFont("FUEL", 10, screenH - 40, 13, WHITE);  // Increased by 30% (was 10)
            for(int i=0; i<10; i++) {
                Color barCol = (i < fuelBars) ? GREEN : DARKGRAY;
                if (i < 3 && i < fuelBars) barCol = RED;
                DrawRectangle(70 + (i * 25), screenH - 40, 20, 20, barCol);
            }
            
            // Cargo gauge (25 max - updated)
            int cargoMax = G_Player.cargoSpace;
            float cargoPct = (float)G_Player.cargoFilled / (float)cargoMax;
            if (cargoPct > 1.0f) cargoPct = 1.0f;
            
            // Cargo text increased by 25% (8 * 1.25 = 10)
            DrawTextWithFont(TextFormat("CARGO %d/%d", G_Player.cargoFilled, cargoMax), 10, screenH - 80, 10, WHITE);
            // Draw continuous bar
            DrawRectangle(150, screenH - 80, 200, 20, DARKGRAY); // Background
            DrawRectangle(150, screenH - 80, (int)(200 * cargoPct), 20, ORANGE); // Fill
            DrawRectangleLines(150, screenH - 80, 200, 20, WHITE); // Border
            
            // Hull gauge
            int hullBars = (int)(G_Player.hull / 10.0f);
            DrawTextWithFont("HULL", 10, screenH - 120, 13, WHITE);  // Increased by 30% (was 10)
            for(int i=0; i<10; i++) {
                Color barCol = (i < hullBars) ? (Color){200, 200, 255, 255} : DARKGRAY; 
                if (i < 3 && i < hullBars) barCol = RED;
                DrawRectangle(70 + (i * 25), screenH - 120, 20, 20, barCol);
            }
            
            // Laser Heat Bar (if fitted) - Make sure it's always visible
            if (G_Player.hasLaser) {
                 DrawTextWithFont("LASER TEMP", 10, 100, 13, WHITE);  // Increased by 30% (was 10)
                 float heatPct = G_Player.laserHeat / G_Player.maxLaserHeat;
                 if (heatPct > 1.0f) heatPct = 1.0f;
                 Color heatCol = G_Player.laserOverheated ? RED : ORANGE;
                 if (G_Player.laserOverheated && (int)(GetTime()*10)%2==0) heatCol = WHITE; 
                 
                 // Background (always visible)
                 DrawRectangle(10, 130, 200, 20, DARKGRAY);
                 // Fill bar
                 DrawRectangle(10, 130, (int)(200 * heatPct), 20, heatCol);
                 // Border
                 DrawRectangleLines(10, 130, 200, 20, WHITE);
                 
                 // Show heat percentage
                 DrawTextWithFont(TextFormat("%.0f%%", G_Player.laserHeat), 220, 130, 12, WHITE);  // Increased by 30% (was 9)
                 
                 if (G_Player.laserOverheated) {
                     DrawTextWithFont("OVERHEAT", 220, 150, 13, RED);  // Increased by 30% (was 10)
                 }
            }
            
            if (laserErrorDisplayTime > 0.0f) {
                DrawTextWithFont("ERROR: NO LASER", 10, 70, 13, RED);  // Increased by 30% (was 10)
            }
            
            // Mini Map (Bottom Right)
            int mapSize = 150;
            int mapX = VIRTUAL_WIDTH - mapSize - 10;
            int mapY = VIRTUAL_HEIGHT - mapSize - 10;
            
            // Background
            DrawRectangle(mapX, mapY, mapSize, mapSize, (Color){10, 10, 20, 200});
            DrawRectangleLines(mapX, mapY, mapSize, mapSize, WHITE);
            
            // Map center (ship position - always centered, ship never moves on map)
            int mapCenterX = mapX + mapSize / 2;
            int mapCenterY = mapY + mapSize / 2;
            
            // Scale: PROSPECT_PERIMETER * 2 is the full map size, mapSize is the display size
            float mapScale = (float)mapSize / (PROSPECT_PERIMETER * 2.0f);
            
            // Draw boundary square (teal/cyan) - moves relative to ship
            // Boundary is at ±PROSPECT_PERIMETER from origin
            // Convert boundary corners to map coordinates (relative to ship at center)
            float boundarySize = PROSPECT_PERIMETER * 2.0f; // Full boundary size
            float boundaryHalf = PROSPECT_PERIMETER;
            
            // Calculate boundary corners relative to ship position
            // Top-left corner of boundary in world
            float worldBoundTL_X = -boundaryHalf - g_shipPos.x;
            float worldBoundTL_Z = -boundaryHalf - g_shipPos.z;
            // Bottom-right corner of boundary in world
            float worldBoundBR_X = boundaryHalf - g_shipPos.x;
            float worldBoundBR_Z = boundaryHalf - g_shipPos.z;
            
            // Convert to map coordinates
            // Note: X is negated so when ship moves left, world moves right on minimap (SWAPPED)
            // Note: Z is negated because screen Y increases downward, but world Z forward should appear upward on minimap
            Vector2 boundTL = {
                mapCenterX - worldBoundTL_X * mapScale,  // Negated X for swapped left/right
                mapCenterY - worldBoundTL_Z * mapScale  // Negate Z for correct orientation
            };
            Vector2 boundBR = {
                mapCenterX - worldBoundBR_X * mapScale,  // Negated X for swapped left/right
                mapCenterY - worldBoundBR_Z * mapScale  // Negate Z for correct orientation
            };
            
            // Draw boundary square (clamp to map bounds)
            float boundX = (boundTL.x < mapX) ? mapX : boundTL.x;
            float boundY = (boundTL.y < mapY) ? mapY : boundTL.y;
            float boundW = ((boundBR.x > mapX + mapSize) ? (mapX + mapSize) : boundBR.x) - boundX;
            float boundH = ((boundBR.y > mapY + mapSize) ? (mapY + mapSize) : boundBR.y) - boundY;
            
            if (boundW > 0 && boundH > 0) {
                DrawRectangleLines((int)boundX, (int)boundY, (int)boundW, (int)boundH, (Color){0, 255, 255, 200}); // Teal/Cyan
            }
            
            // Draw exit tube (red circle) - cylinder is at (0, 0) in world XZ plane
            // Always visible, moves relative to ship
            // Calculate relative position: cylinder at (0, 0) in XZ, ship at (x, z)
            float relX = 0.0f - g_shipPos.x;  // Relative X position
            float relZ = 0.0f - g_shipPos.z;  // Relative Z position
            // Map to screen: X is negated so when ship moves left, world moves right on minimap (SWAPPED)
            // Z is negated so when ship moves forward, world moves backward on minimap
            Vector2 tubeMapPos = {
                mapCenterX - relX * mapScale,  // Negated X for swapped left/right
                mapCenterY - relZ * mapScale   // Negate Z for correct orientation
            };
            
            // Check if cargo is full for flashing effect (use shared variable from HUD section)
            Color tubeColor = cargoFlashOn ? (Color){255, 255, 255, 255} : RED; // White when flashing, red otherwise
            
            // Always draw exit cylinder (may be off-screen but we draw it anyway)
            DrawCircle((int)tubeMapPos.x, (int)tubeMapPos.y, 8, tubeColor);
            DrawCircleLines((int)tubeMapPos.x, (int)tubeMapPos.y, 8, WHITE);
            
            // Draw nearby rocks on minimap (optional - for reference)
            for (int i = 0; i < NUM_ROCKS; i++) {
                if (!G_Rocks[i].active) continue;
                float rockRelX = G_Rocks[i].position.x - g_shipPos.x;
                float rockRelZ = G_Rocks[i].position.z - g_shipPos.z;
                // Only draw rocks within minimap view range
                float dist = sqrtf(rockRelX * rockRelX + rockRelZ * rockRelZ);
                if (dist < PROSPECT_PERIMETER) {
                    Vector2 rockMapPos = {
                        mapCenterX - rockRelX * mapScale,  // Negated X for swapped left/right
                        mapCenterY - rockRelZ * mapScale   // Negate Z for correct orientation
                    };
                    // Only draw if within minimap bounds
                    if (rockMapPos.x >= mapX && rockMapPos.x <= mapX + mapSize &&
                        rockMapPos.y >= mapY && rockMapPos.y <= mapY + mapSize) {
                        DrawCircle((int)rockMapPos.x, (int)rockMapPos.y, 2, GRAY);
                    }
                }
            }
            
            // Draw collection debris chunks on minimap (cyan debris chunks)
            for (int i = 0; i < MAX_DEBRIS; i++) {
                if (!g_debris[i].active) continue;
                // Check if this is collection debris (cyan)
                Color debrisColor = g_debris[i].color;
                bool isCollectionDebris = (debrisColor.r == 0 && debrisColor.g == 255 && debrisColor.b == 255); // Cyan
                if (!isCollectionDebris) continue;
                
                float debrisRelX = g_debris[i].position.x - g_shipPos.x;
                float debrisRelZ = g_debris[i].position.z - g_shipPos.z;
                float dist = sqrtf(debrisRelX * debrisRelX + debrisRelZ * debrisRelZ);
                if (dist < PROSPECT_PERIMETER) {
                    Vector2 debrisMapPos = {
                        mapCenterX - debrisRelX * mapScale,  // Negated X for swapped left/right
                        mapCenterY - debrisRelZ * mapScale   // Negate Z for correct orientation
                    };
                    // Only draw if within minimap bounds
                    if (debrisMapPos.x >= mapX && debrisMapPos.x <= mapX + mapSize &&
                        debrisMapPos.y >= mapY && debrisMapPos.y <= mapY + mapSize) {
                        DrawCircle((int)debrisMapPos.x, (int)debrisMapPos.y, 1, (Color){0, 255, 255, 255}); // Cyan (collection debris)
                    }
                }
            }
            
            // Draw ship (blue triangle pointing forward) - ALWAYS at center, never moves
            // Ship yaw: 0° = pointing in +Z direction (forward), which should point "up" on minimap
            float shipAngle = g_shipYaw; // Already in degrees
            
            Vector2 shipTip = {(float)mapCenterX, (float)(mapCenterY - 6)};
            Vector2 shipLeft = {(float)(mapCenterX - 4), (float)(mapCenterY + 4)};
            Vector2 shipRight = {(float)(mapCenterX + 4), (float)(mapCenterY + 4)};
            
            // Rotate triangle based on ship yaw
            float cosA = cosf(DEG2RAD * shipAngle);
            float sinA = sinf(DEG2RAD * shipAngle);
            
            // Rotate points around center
            Vector2 center = {(float)mapCenterX, (float)mapCenterY};
            Vector2 tipRot, leftRot, rightRot;
            float dx, dy;
            
            dx = shipTip.x - center.x; dy = shipTip.y - center.y;
            tipRot.x = center.x + dx * cosA - dy * sinA;
            tipRot.y = center.y + dx * sinA + dy * cosA;
            
            dx = shipLeft.x - center.x; dy = shipLeft.y - center.y;
            leftRot.x = center.x + dx * cosA - dy * sinA;
            leftRot.y = center.y + dx * sinA + dy * cosA;
            
            dx = shipRight.x - center.x; dy = shipRight.y - center.y;
            rightRot.x = center.x + dx * cosA - dy * sinA;
            rightRot.y = center.y + dx * sinA + dy * cosA;
            
            DrawTriangle(tipRot, leftRot, rightRot, BLUE);
            DrawTriangleLines(tipRot, leftRot, rightRot, WHITE);
            
            // Draw pause overlay if paused
            if (g_isPaused) {
                // Semi-transparent dark overlay
                DrawRectangle(0, 0, VIRTUAL_WIDTH, VIRTUAL_HEIGHT, (Color){0, 0, 0, 180});
                
                // Pause text
                const char* pauseText = "PAUSED";
                int fontSize = 38;
                int textWidth = MeasureTextWithFont(pauseText, fontSize);
                int textX = (VIRTUAL_WIDTH - textWidth) / 2;
                int textY = VIRTUAL_HEIGHT / 2 - 40;
                
                // Draw text with outline for visibility
                DrawTextWithFont(pauseText, textX + 2, textY + 2, fontSize, BLACK);
                DrawTextWithFont(pauseText, textX, textY, fontSize, YELLOW);
                
                // Instruction text
                const char* instructionText = "PRESS ESC TO UNPAUSE";
                int instFontSize = 15;
                int instWidth = MeasureTextWithFont(instructionText, instFontSize);
                int instX = (VIRTUAL_WIDTH - instWidth) / 2;
                int instY = textY + fontSize + 20;
                DrawTextWithFont(instructionText, instX, instY, instFontSize, WHITE);
            }
            
            DrawScanlines();
            break;
        }
    }
    
    // End 2D Mode if still active (from menus or HUD)
    if (g_currentState != STATE_LANDER) {
        EndMode2D();
    } else {
        EndMode2D(); // Close the HUD mode
    }

    // Update per-frame state tracker after all possible transitions
    prevFrameState = g_currentState;
    
    // Clear one-time input flags at end of frame
    ClearInputFrame();
    
    // End rendering to framebuffer
    EndTextureMode();
}

// ------------------------------------------------------------
// INITIALIZATION FUNCTION
// ------------------------------------------------------------
__declspec(dllexport) __cdecl bool InitializeGame() {
    // Always clear the exit flag before (re)initialization so relaunches work
    g_exit_requested = false;

    if (g_game_initialized) {
        return true; // Already initialized
    }
    
    // Texture loading moved below InitWindow to ensure GL context exists
    
    SetTraceLogLevel(LOG_NONE);
    
    // Only set hidden window flags if window doesn't exist (embedded mode)
    // If window already exists (standalone mode), keep it visible
    if (!IsWindowReady()) {
        SetConfigFlags(FLAG_WINDOW_UNDECORATED | FLAG_WINDOW_HIDDEN);
        InitWindow(VIRTUAL_WIDTH, VIRTUAL_HEIGHT, "AstroMiner_Embedded");
        DisableCursor();
        // Embedded mode: Python manages the loop timing, so we don't want Raylib to wait/sleep
        SetTargetFPS(0); // Unlimited FPS (no waiting)
    } else {
        // Standalone mode: We need to limit FPS
        SetTargetFPS(60);
    }
    
    // Load New Market Texture (Must happen after InitWindow)
    // astrominer_embed.py sets CWD to this directory before initialization, so we use local path
    commoditiesMarketTx = LoadTexture("commodities_market.png");
    
    // Initialize audio device
    // Increase buffer size to prevent popping/crackling (4096 is default, 16384 provides more headroom)
    SetAudioStreamBufferSizeDefault(16384);
    InitAudioDevice();
    
    // Load terminal type sound with multiple fallbacks
    const char* terminalTypePaths[] = {
        "terminal_type.wav",
        "Data/games/AstroMiner/terminal_type.wav",
        "Data/Audio/terminal_type.wav",          // legacy location
        "../../games/AstroMiner/terminal_type.wav"
    };
    bool terminalTypeLoaded = false;
    for (int j = 0; j < 4; j++) {
        printf("[InitializeGame] Trying to load terminal_type.wav from: %s\n", terminalTypePaths[j]);
        g_terminalTypeSound = LoadSound(terminalTypePaths[j]);
        if (g_terminalTypeSound.frameCount > 0) {
            printf("[InitializeGame] SUCCESS: Loaded terminal_type.wav from: %s\n", terminalTypePaths[j]);
            terminalTypeLoaded = true;
            break;
        }
    }
    if (!terminalTypeLoaded) {
        printf("[InitializeGame] ERROR: Failed to load terminal_type.wav from all paths!\n");
    }

    // Load laser sound with multiple fallbacks
    const char* laserSoundPaths[] = {
        "laser.wav",
        "Data/games/AstroMiner/laser.wav",
        "../../games/AstroMiner/laser.wav"
    };
    bool laserSoundLoaded = false;
    for (int j = 0; j < 3; j++) {
        printf("[InitializeGame] Trying to load laser.wav from: %s\n", laserSoundPaths[j]);
        g_laserSound = LoadSound(laserSoundPaths[j]);
        if (g_laserSound.frameCount > 0) {
            printf("[InitializeGame] SUCCESS: Loaded laser.wav from: %s\n", laserSoundPaths[j]);
            laserSoundLoaded = true;
            SetSoundVolume(g_laserSound, 0.50f); // Reduced by ~50% from original, 25% from 0.67
            break;
        }
    }
    if (!laserSoundLoaded) {
        printf("[InitializeGame] ERROR: Failed to load laser.wav from all paths!\n");
    }

    // Load thruster sound with multiple fallbacks
    const char* thrusterSoundPaths[] = {
        "burners.wav",
        "Data/games/AstroMiner/burners.wav",
        "../../games/AstroMiner/burners.wav"
    };
    bool thrusterSoundLoaded = false;
    for (int j = 0; j < 3; j++) {
        printf("[InitializeGame] Trying to load burners.wav from: %s\n", thrusterSoundPaths[j]);
        g_thrusterSound = LoadSound(thrusterSoundPaths[j]);
        if (g_thrusterSound.frameCount > 0) {
            printf("[InitializeGame] SUCCESS: Loaded burners.wav from: %s\n", thrusterSoundPaths[j]);
            thrusterSoundLoaded = true;
            break;
        }
    }
    if (!thrusterSoundLoaded) {
        printf("[InitializeGame] ERROR: Failed to load burners.wav from all paths!\n");
    }

    // Load sale sound with multiple fallbacks
    const char* saleSoundPaths[] = {
        "sale.wav",
        "Data/games/AstroMiner/sale.wav",
        "../../games/AstroMiner/sale.wav"
    };
    bool saleSoundLoaded = false;
    for (int j = 0; j < 3; j++) {
        printf("[InitializeGame] Trying to load sale.wav from: %s\n", saleSoundPaths[j]);
        g_saleSound = LoadSound(saleSoundPaths[j]);
        if (g_saleSound.frameCount > 0) {
            printf("[InitializeGame] SUCCESS: Loaded sale.wav from: %s\n", saleSoundPaths[j]);
            saleSoundLoaded = true;
            break;
        }
    }
    if (!saleSoundLoaded) {
        printf("[InitializeGame] ERROR: Failed to load sale.wav from all paths!\n");
    }

    // Load No sound with multiple fallbacks
    const char* noSoundPaths[] = {
        "No.wav",
        "Data/games/AstroMiner/No.wav",
        "../../games/AstroMiner/No.wav"
    };
    bool noSoundLoaded = false;
    for (int j = 0; j < 3; j++) {
        printf("[InitializeGame] Trying to load No.wav from: %s\n", noSoundPaths[j]);
        g_noSound = LoadSound(noSoundPaths[j]);
        if (g_noSound.frameCount > 0) {
            printf("[InitializeGame] SUCCESS: Loaded No.wav from: %s\n", noSoundPaths[j]);
            noSoundLoaded = true;
            SetSoundVolume(g_noSound, 1.0f); // Set to 100% volume
            break;
        }
    }
    if (!noSoundLoaded) {
        printf("[InitializeGame] ERROR: Failed to load No.wav from all paths!\n");
    }

    // Load crash sound with multiple fallbacks
    const char* crashSoundPaths[] = {
        "crash.wav",
        "Data/games/AstroMiner/crash.wav",
        "../../games/AstroMiner/crash.wav"
    };
    bool crashSoundLoaded = false;
    for (int j = 0; j < 3; j++) {
        printf("[InitializeGame] Trying to load crash.wav from: %s\n", crashSoundPaths[j]);
        g_crashSound = LoadSound(crashSoundPaths[j]);
        if (g_crashSound.frameCount > 0) {
            printf("[InitializeGame] SUCCESS: Loaded crash.wav from: %s\n", crashSoundPaths[j]);
            crashSoundLoaded = true;
            break;
        }
    }
    if (!crashSoundLoaded) {
        printf("[InitializeGame] ERROR: Failed to load crash.wav from all paths!\n");
    }

    // Load explode sound with multiple fallbacks
    const char* explodeSoundPaths[] = {
        "explode.wav",
        "Data/games/AstroMiner/explode.wav",
        "../../games/AstroMiner/explode.wav"
    };
    bool explodeSoundLoaded = false;
    for (int j = 0; j < 3; j++) {
        printf("[InitializeGame] Trying to load explode.wav from: %s\n", explodeSoundPaths[j]);
        g_explodeSound = LoadSound(explodeSoundPaths[j]);
        if (g_explodeSound.frameCount > 0) {
            printf("[InitializeGame] SUCCESS: Loaded explode.wav from: %s\n", explodeSoundPaths[j]);
            explodeSoundLoaded = true;
            break;
        }
    }
    if (!explodeSoundLoaded) {
        printf("[InitializeGame] ERROR: Failed to load explode.wav from all paths!\n");
    }

    // Load entering station sound with multiple fallbacks
    const char* enteringStationSoundPaths[] = {
        "entering_station.wav",
        "Data/games/AstroMiner/entering_station.wav",
        "../../games/AstroMiner/entering_station.wav"
    };
    bool enteringStationSoundLoaded = false;
    for (int j = 0; j < 3; j++) {
        printf("[InitializeGame] Trying to load entering_station.wav from: %s\n", enteringStationSoundPaths[j]);
        g_enteringStationSound = LoadSound(enteringStationSoundPaths[j]);
        if (g_enteringStationSound.frameCount > 0) {
            printf("[InitializeGame] SUCCESS: Loaded entering_station.wav from: %s\n", enteringStationSoundPaths[j]);
            enteringStationSoundLoaded = true;
            break;
        }
    }
    if (!enteringStationSoundLoaded) {
        printf("[InitializeGame] ERROR: Failed to load entering_station.wav from all paths!\n");
    }

    // Load collect sound with multiple fallbacks
    const char* collectSoundPaths[] = {
        "collect.wav",
        "Data/games/AstroMiner/collect.wav",
        "../../games/AstroMiner/collect.wav"
    };
    bool collectSoundLoaded = false;
    for (int j = 0; j < 3; j++) {
        printf("[InitializeGame] Trying to load collect.wav from: %s\n", collectSoundPaths[j]);
        g_collectSound = LoadSound(collectSoundPaths[j]);
        if (g_collectSound.frameCount > 0) {
            printf("[InitializeGame] SUCCESS: Loaded collect.wav from: %s\n", collectSoundPaths[j]);
            collectSoundLoaded = true;
            break;
        }
    }
    if (!collectSoundLoaded) {
        printf("[InitializeGame] ERROR: Failed to load collect.wav from all paths!\n");
    }

    // Load rock sound with multiple fallbacks
    const char* rockSoundPaths[] = {
        "rock.wav",
        "Data/games/AstroMiner/rock.wav",
        "../../games/AstroMiner/rock.wav"
    };
    bool rockSoundLoaded = false;
    for (int j = 0; j < 3; j++) {
        printf("[InitializeGame] Trying to load rock.wav from: %s\n", rockSoundPaths[j]);
        g_rockSound = LoadSound(rockSoundPaths[j]);
        if (g_rockSound.frameCount > 0) {
            printf("[InitializeGame] SUCCESS: Loaded rock.wav from: %s\n", rockSoundPaths[j]);
            rockSoundLoaded = true;
            SetSoundVolume(g_rockSound, 0.70f); // Set to 70% volume
            break;
        }
    }
    if (!rockSoundLoaded) {
        printf("[InitializeGame] ERROR: Failed to load rock.wav from all paths!\n");
    }

    // Load beam-up ship sound with multiple fallbacks
    const char* beamUpSoundPaths[] = {
        "beam-up-ship.wav",
        "Data/games/AstroMiner/beam-up-ship.wav",
        "../../games/AstroMiner/beam-up-ship.wav"
    };
    bool beamUpSoundLoaded = false;
    for (int j = 0; j < 3; j++) {
        printf("[InitializeGame] Trying to load beam-up-ship.wav from: %s\n", beamUpSoundPaths[j]);
        g_beamUpSound = LoadSound(beamUpSoundPaths[j]);
        if (g_beamUpSound.frameCount > 0) {
            printf("[InitializeGame] SUCCESS: Loaded beam-up-ship.wav from: %s\n", beamUpSoundPaths[j]);
            beamUpSoundLoaded = true;
            break;
        }
    }
    if (!beamUpSoundLoaded) {
        printf("[InitializeGame] ERROR: Failed to load beam-up-ship.wav from all paths!\n");
    }
    
    // Load launch sequence sound with multiple fallbacks
    const char* launchSequenceSoundPaths[] = {
        "launch-sequence.wav",
        "Data/games/AstroMiner/launch-sequence.wav",
        "../../games/AstroMiner/launch-sequence.wav"
    };
    bool launchSequenceSoundLoaded = false;
    for (int j = 0; j < 3; j++) {
        printf("[InitializeGame] Trying to load launch-sequence.wav from: %s\n", launchSequenceSoundPaths[j]);
        g_launchSequenceSound = LoadSound(launchSequenceSoundPaths[j]);
        if (g_launchSequenceSound.frameCount > 0) {
            printf("[InitializeGame] SUCCESS: Loaded launch-sequence.wav from: %s\n", launchSequenceSoundPaths[j]);
            launchSequenceSoundLoaded = true;
            break;
        }
    }
    if (!launchSequenceSoundLoaded) {
        printf("[InitializeGame] ERROR: Failed to load launch-sequence.wav from all paths!\n");
    }

    // Load fixing-on sound with multiple fallbacks
    const char* fixingOnSoundPaths[] = {
        "fixing-on.wav",
        "Data/games/AstroMiner/fixing-on.wav",
        "../../games/AstroMiner/fixing-on.wav"
    };
    bool fixingOnSoundLoaded = false;
    for (int j = 0; j < 3; j++) {
        printf("[InitializeGame] Trying to load fixing-on.wav from: %s\n", fixingOnSoundPaths[j]);
        g_fixingOnSound = LoadSound(fixingOnSoundPaths[j]);
        if (g_fixingOnSound.frameCount > 0) {
            printf("[InitializeGame] SUCCESS: Loaded fixing-on.wav from: %s\n", fixingOnSoundPaths[j]);
            fixingOnSoundLoaded = true;
            break;
        }
    }
    if (!fixingOnSoundLoaded) {
        printf("[InitializeGame] ERROR: Failed to load fixing-on.wav from all paths!\n");
    }

    // Load fuel sound with multiple fallbacks
    const char* fuelSoundPaths[] = {
        "fuel.wav",
        "Data/games/AstroMiner/fuel.wav",
        "../../games/AstroMiner/fuel.wav"
    };
    bool fuelSoundLoaded = false;
    for (int j = 0; j < 3; j++) {
        printf("[InitializeGame] Trying to load fuel.wav from: %s\n", fuelSoundPaths[j]);
        g_fuelSound = LoadSound(fuelSoundPaths[j]);
        if (g_fuelSound.frameCount > 0) {
            printf("[InitializeGame] SUCCESS: Loaded fuel.wav from: %s\n", fuelSoundPaths[j]);
            fuelSoundLoaded = true;
            break;
        }
    }
    if (!fuelSoundLoaded) {
        printf("[InitializeGame] ERROR: Failed to load fuel.wav from all paths!\n");
    }

    // Load bar sound with multiple fallbacks
    const char* barSoundPaths[] = {
        "bar.wav",
        "Data/games/AstroMiner/bar.wav",
        "Data/Audio/bar.wav",          // legacy location
        "../../games/AstroMiner/bar.wav"
    };
    bool barSoundLoaded = false;
    for (int j = 0; j < 4; j++) {
        printf("[InitializeGame] Trying to load bar.wav from: %s\n", barSoundPaths[j]);
        g_barSound = LoadSound(barSoundPaths[j]);
        if (g_barSound.frameCount > 0) {
            printf("[InitializeGame] SUCCESS: Loaded bar.wav from: %s\n", barSoundPaths[j]);
            barSoundLoaded = true;
            break;
        }
    }
    if (!barSoundLoaded) {
        printf("[InitializeGame] ERROR: Failed to load bar.wav from all paths!\n");
    }
    
    // Load levelup sound with multiple fallbacks
    const char* levelupSoundPaths[] = {
        "levelup.wav",
        "Data/games/AstroMiner/levelup.wav",
        "Data/Audio/levelup.wav",
        "../../games/AstroMiner/levelup.wav"
    };
    bool levelupSoundLoaded = false;
    for (int j = 0; j < 4; j++) {
        printf("[InitializeGame] Trying to load levelup.wav from: %s\n", levelupSoundPaths[j]);
        g_levelupSound = LoadSound(levelupSoundPaths[j]);
        if (g_levelupSound.frameCount > 0) {
            printf("[InitializeGame] SUCCESS: Loaded levelup.wav from: %s\n", levelupSoundPaths[j]);
            levelupSoundLoaded = true;
            break;
        }
    }
    if (!levelupSoundLoaded) {
        printf("[InitializeGame] ERROR: Failed to load levelup.wav from all paths!\n");
    }

    // Load background music (AstroMiner.mp3) with multiple fallbacks
    const char* musicPaths[] = {
        "AstroMiner.mp3",
        "Data/games/AstroMiner/AstroMiner.mp3",
        "../../games/AstroMiner/AstroMiner.mp3"
    };
    bool musicLoaded = false;
    for (int j = 0; j < 3; j++) {
        printf("[InitializeGame] Trying to load AstroMiner.mp3 from: %s\n", musicPaths[j]);
        g_backgroundMusic = LoadMusicStream(musicPaths[j]);
        if (g_backgroundMusic.frameCount > 0) {
            printf("[InitializeGame] SUCCESS: Loaded AstroMiner.mp3 from: %s\n", musicPaths[j]);
            musicLoaded = true;
            // Set volume to 70% (0.7)
            SetMusicVolume(g_backgroundMusic, 0.7f);
            g_backgroundMusic.looping = false; // Disable looping for manual transition
            break;
        }
    }
    if (!musicLoaded) {
        printf("[InitializeGame] ERROR: Failed to load AstroMiner.mp3 from all paths!\n");
    }
    
    // Load background music 2 (AstroMiner2.mp3) with multiple fallbacks
    const char* musicPaths2[] = {
        "AstroMiner2.mp3",
        "Data/games/AstroMiner/AstroMiner2.mp3",
        "../../games/AstroMiner/AstroMiner2.mp3"
    };
    bool musicLoaded2 = false;
    for (int j = 0; j < 3; j++) {
        printf("[InitializeGame] Trying to load AstroMiner2.mp3 from: %s\n", musicPaths2[j]);
        g_backgroundMusic2 = LoadMusicStream(musicPaths2[j]);
        if (g_backgroundMusic2.frameCount > 0) {
            printf("[InitializeGame] SUCCESS: Loaded AstroMiner2.mp3 from: %s\n", musicPaths2[j]);
            musicLoaded2 = true;
            // Set volume to 70% (0.7)
            SetMusicVolume(g_backgroundMusic2, 0.7f);
            g_backgroundMusic2.looping = false; // Disable looping for manual transition
            break;
        }
    }
    if (!musicLoaded2) {
        printf("[InitializeGame] ERROR: Failed to load AstroMiner2.mp3 from all paths!\n");
    }

    // Load splash screen music (bostonpump.wav) with multiple fallbacks
    const char* splashMusicPaths[] = {
        "bostonpump.wav",
        "Data/games/AstroMiner/bostonpump.wav",
        "../../games/AstroMiner/bostonpump.wav"
    };
    bool splashMusicLoaded = false;
    for (int j = 0; j < 3; j++) {
        printf("[InitializeGame] Trying to load bostonpump.wav from: %s\n", splashMusicPaths[j]);
        g_splashMusic = LoadMusicStream(splashMusicPaths[j]);
        if (g_splashMusic.frameCount > 0) {
            printf("[InitializeGame] SUCCESS: Loaded bostonpump.wav from: %s\n", splashMusicPaths[j]);
            splashMusicLoaded = true;
            SetMusicVolume(g_splashMusic, 0.7f);
            g_splashMusic.looping = true; // Loop the splash music
            break;
        }
    }
    if (!splashMusicLoaded) {
        printf("[InitializeGame] ERROR: Failed to load bostonpump.wav from all paths!\n");
    }

    // Load leaderboard
    LoadLeaderboard();
    
    // Start background music immediately - it will play alongside splash music
    if (musicLoaded) {
        PlayMusicStream(g_backgroundMusic);
        SetMusicVolume(g_backgroundMusic, 0.7f);
        g_currentTrack = 0;
        printf("[InitializeGame] Background music 1 started playing (70%% volume)\n");
    } else if (musicLoaded2) {
        PlayMusicStream(g_backgroundMusic2);
        SetMusicVolume(g_backgroundMusic2, 0.7f);
        g_currentTrack = 1;
        printf("[InitializeGame] Background music 2 started playing (70%% volume)\n");
    }
    
    // Create offscreen render texture (Low Res)
    g_framebuffer = LoadRenderTexture(RENDER_WIDTH, RENDER_HEIGHT);
    g_framebuffer_initialized = true;
    
    // Initialize Station Viewport (Low Res)
    stationViewport.Init(RENDER_WIDTH, RENDER_HEIGHT);
    
    // Initialize asteroid viewport render texture
    g_asteroidViewport = LoadRenderTexture(RENDER_WIDTH, RENDER_HEIGHT);
    g_asteroidViewportInitialized = true;
    
    // Initialize navigation viewport render texture
    g_navViewport = LoadRenderTexture(RENDER_WIDTH, RENDER_HEIGHT);
    g_navViewportInitialized = true;
    
    // Initialize camera (position it near the ship's starting position)
    g_camera.up = (Vector3){0,1,0};
    g_camera.fovy = 60;
    g_camera.projection = CAMERA_PERSPECTIVE;
    // Start camera behind and above the ship's starting position
    g_camera.position = (Vector3){0, 64, -PROSPECT_PERIMETER - 9.0f};  // Behind ship, slightly above
    g_camera.target = (Vector3){0, 60, -PROSPECT_PERIMETER};  // Point at ship's starting position
    
    // Create meshes and models
    Mesh shipMesh = CreateSolidShip();
    g_ship = LoadModelFromMesh(shipMesh);
    
    Mesh rockBaseMesh = CreateBaseRockMesh();
    g_rockModel = LoadModelFromMesh(rockBaseMesh);
    
    // Load shop item models
    Mesh laserMesh = CreateLaserMesh();
    g_shopItemModels[0] = LoadModelFromMesh(laserMesh);
    
    Mesh collectorMesh = CreateCollectorMesh();
    g_shopItemModels[1] = LoadModelFromMesh(collectorMesh);
    
    Mesh thrusterMesh = CreateThrusterMesh();
    g_shopItemModels[2] = LoadModelFromMesh(thrusterMesh);
    
    Mesh exoPlatingMesh = CreateExoPlatingMesh();
    g_shopItemModels[3] = LoadModelFromMesh(exoPlatingMesh);
    
    Mesh fuelMesh = CreateFuelMesh();
    g_shopItemModels[4] = LoadModelFromMesh(fuelMesh);
    
    Mesh repairsMesh = CreateRepairsMesh();
    g_shopItemModels[5] = LoadModelFromMesh(repairsMesh);
    
    // Initialize Station shop models
    Mesh fuelTankUpgradeMesh = CreateFuelTankUpgradeMesh();
    g_stationShopModels[0] = LoadModelFromMesh(fuelTankUpgradeMesh);
    Mesh cargoBlackHoleMesh = CreateCargoBlackHoleMesh();
    g_stationShopModels[1] = LoadModelFromMesh(cargoBlackHoleMesh);
    g_stationShopModels[2] = g_shopItemModels[4];  // Fuel (reuse)
    Mesh redShipMesh = CreateColoredShipMesh(0);
    g_stationShopModels[3] = LoadModelFromMesh(redShipMesh);
    Mesh greenShipMesh = CreateColoredShipMesh(1);
    g_stationShopModels[4] = LoadModelFromMesh(greenShipMesh);
    Mesh purpleShipMesh = CreateColoredShipMesh(2);
    g_stationShopModels[5] = LoadModelFromMesh(purpleShipMesh);
    Mesh goldShipMesh = CreateColoredShipMesh(3);  // Gold ship (colorType 3)
    g_goldShipModel = LoadModelFromMesh(goldShipMesh);
    
    // Initialize Halo shop models
    g_haloShopModels[0] = g_shopItemModels[0];  // Better Laser (reuse laser mesh)
    g_haloShopModels[1] = g_shopItemModels[1];  // Better Collector (reuse collector mesh)
    g_haloShopModels[2] = g_shopItemModels[4];  // Fuel (reuse)
    g_haloShopModels[3] = g_stationShopModels[3];  // Red Ship (reuse)
    g_haloShopModels[4] = g_stationShopModels[4];  // Green Ship (reuse)
    g_haloShopModels[5] = g_stationShopModels[5];  // Purple Ship (reuse)
    
    // Load bar page overlay
    printf("[InitializeGame] Loading bar page texture...\n");
    const char* barPagePaths[] = {
        "bar_page.png",
        "Data/games/AstroMiner/bar_page.png",
        "../../games/AstroMiner/bar_page.png"
    };
    bool barPageLoaded = false;
    for (int j = 0; j < 3; j++) {
        printf("[InitializeGame] Trying to load bar_page.png from: %s\n", barPagePaths[j]);
        barPageTx = LoadTexture(barPagePaths[j]);
        if (barPageTx.id > 0) {
            printf("[InitializeGame] SUCCESS: Loaded bar_page.png from: %s (size: %dx%d)\n", 
                   barPagePaths[j], barPageTx.width, barPageTx.height);
            barPageLoaded = true;
            break;
        }
    }
    if (!barPageLoaded) {
        printf("[InitializeGame] ERROR: Failed to load bar_page.png from all paths!\n");
    }
    
    // Initialize asteroid fuel costs persistently (so they don't change while browsing)
    for (int i = 0; i < 6; i++) {
        // Depot costs: 20-50
        g_fuelCosts[i] = GetRandomValue(20, 50);
        
        // Station costs (if we had separate arrays, but currently reusing logic or randomizing on keypress)
        // To strictly follow "set and do not change", we should have arrays for all locations or 
        // update this array when location changes.
    }
    
    // Load scanline texture
    scanlineTx = LoadTexture("../../images/scanline.png");
    
    // Load GUI_and_HUD texture with multiple fallbacks
    guiHudTx = LoadTexture("GUI_and_HUD.png");
    if (guiHudTx.id == 0) {
        guiHudTx = LoadTexture("Data/games/AstroMiner/GUI_and_HUD.png");
    }
    if (guiHudTx.id == 0) {
        guiHudTx = LoadTexture("../../games/AstroMiner/GUI_and_HUD.png");
    }
    
    if (guiHudTx.id > 0) {
        printf("[InitializeGame] Loaded GUI texture: %d x %d\n", guiHudTx.width, guiHudTx.height);
    } else {
        printf("[InitializeGame] FAILED TO LOAD GUI TEXTURE from any path\n");
    }
    
    // Load splash screen textures with multiple fallbacks
    // NOTE: CWD is currently set to dll_dir, so "splash0.png" should work
    const char* splashPaths[][3] = {
        {"splash0.png", "Data/games/AstroMiner/splash0.png", "../../games/AstroMiner/splash0.png"},
        {"splash1.png", "Data/games/AstroMiner/splash1.png", "../../games/AstroMiner/splash1.png"},
        {"splash2.png", "Data/games/AstroMiner/splash2.png", "../../games/AstroMiner/splash2.png"},
        {"splash_new_game.png", "Data/games/AstroMiner/splash_new_game.png", "../../games/AstroMiner/splash_new_game.png"},
        {"splash_load_game.png", "Data/games/AstroMiner/splash_load_game.png", "../../games/AstroMiner/splash_load_game.png"},
        {"splash_quit_game.png", "Data/games/AstroMiner/splash_quit_game.png", "../../games/AstroMiner/splash_quit_game.png"}
    };
    
    const char* splashNames[] = {"splash0", "splash1", "splash2", "splash_new_game", "splash_load_game", "splash_quit_game"};
    Texture2D* splashTextures[] = {&splash0Tx, &splash1Tx, &splash2Tx, &splashNewGameTx, &splashLoadGameTx, &splashQuitGameTx};
    
    printf("[InitializeGame] Loading splash textures...\n");
    for (int i = 0; i < 6; i++) {
        bool loaded = false;
        for (int j = 0; j < 3; j++) {
            printf("[InitializeGame] Trying to load %s from: %s\n", splashNames[i], splashPaths[i][j]);
            *splashTextures[i] = LoadTexture(splashPaths[i][j]);
            if (splashTextures[i]->id > 0) {
                printf("[InitializeGame] SUCCESS: Loaded splash texture %d (%s) from: %s (size: %dx%d)\n", 
                       i, splashNames[i], splashPaths[i][j], 
                       splashTextures[i]->width, splashTextures[i]->height);
                loaded = true;
                break;
            } else {
                printf("[InitializeGame] Failed to load from: %s\n", splashPaths[i][j]);
            }
        }
        if (!loaded) {
            printf("[InitializeGame] ERROR: Failed to load splash texture %d (%s) from all paths!\n", i, splashNames[i]);
        }
    }
    
    // Load depot home page PNGs with multiple fallbacks
    const char* depotGuiPaths[][3] = {
        {"prospect_gui.png", "Data/games/AstroMiner/prospect_gui.png", "../../games/AstroMiner/prospect_gui.png"},
        {"shipyard_gui.png", "Data/games/AstroMiner/shipyard_gui.png", "../../games/AstroMiner/shipyard_gui.png"},
        {"commodities_gui.png", "Data/games/AstroMiner/commodities_gui.png", "../../games/AstroMiner/commodities_gui.png"},
        {"bar_gui.png", "Data/games/AstroMiner/bar_gui.png", "../../games/AstroMiner/bar_gui.png"}
    };
    
    const char* depotGuiNames[] = {"prospect_gui", "shipyard_gui", "commodities_gui", "bar_gui"};
    Texture2D* depotGuiTextures[] = {&prospectGuiTx, &shipyardGuiTx, &commoditiesGuiTx, &barGuiTx};
    
    printf("[InitializeGame] Loading depot GUI textures...\n");
    for (int i = 0; i < 4; i++) {
        bool loaded = false;
        for (int j = 0; j < 3; j++) {
            printf("[InitializeGame] Trying to load %s from: %s\n", depotGuiNames[i], depotGuiPaths[i][j]);
            *depotGuiTextures[i] = LoadTexture(depotGuiPaths[i][j]);
            if (depotGuiTextures[i]->id > 0) {
                printf("[InitializeGame] SUCCESS: Loaded depot GUI texture %d (%s) from: %s (size: %dx%d)\n", 
                       i, depotGuiNames[i], depotGuiPaths[i][j], 
                       depotGuiTextures[i]->width, depotGuiTextures[i]->height);
                loaded = true;
                break;
            } else {
                printf("[InitializeGame] Failed to load from: %s\n", depotGuiPaths[i][j]);
            }
        }
        if (!loaded) {
            printf("[InitializeGame] ERROR: Failed to load depot GUI texture %d (%s) from all paths!\n", i, depotGuiNames[i]);
        }
    }

    // Load Astriod_Prospects.png background
    const char* asteroidBgPaths[] = {
        "Astriod_Prospects.png",
        "Data/games/AstroMiner/Astriod_Prospects.png",
        "../../games/AstroMiner/Astriod_Prospects.png"
    };
    bool asteroidBgLoaded = false;
    for (int j = 0; j < 3; j++) {
        printf("[InitializeGame] Trying to load Astriod_Prospects.png from: %s\n", asteroidBgPaths[j]);
        asteroidProspectsBgTx = LoadTexture(asteroidBgPaths[j]);
        if (asteroidProspectsBgTx.id > 0) {
            printf("[InitializeGame] SUCCESS: Loaded Astriod_Prospects.png from: %s (size: %dx%d)\n", 
                   asteroidBgPaths[j], asteroidProspectsBgTx.width, asteroidProspectsBgTx.height);
            asteroidBgLoaded = true;
            break;
        }
    }
    if (!asteroidBgLoaded) {
        printf("[InitializeGame] ERROR: Failed to load Astriod_Prospects.png from all paths!\n");
    }

    // Load Shipyard upgrade PNGs (location-specific)
    const char* upgradePaths[][3] = {
        {"upgrades_shijuku.png", "Data/games/AstroMiner/upgrades_shijuku.png", "../../games/AstroMiner/upgrades_shijuku.png"},
        {"upgrades_hirohito.png", "Data/games/AstroMiner/upgrades_hirohito.png", "../../games/AstroMiner/upgrades_hirohito.png"},
        {"upgrades_nagako.png", "Data/games/AstroMiner/upgrades_nagako.png", "../../games/AstroMiner/upgrades_nagako.png"}
    };
    
    const char* upgradeNames[] = {"upgrades_shijuku", "upgrades_hirohito", "upgrades_nagako"};
    Texture2D* upgradeTextures[] = {&upgradesShinjukuTx, &upgradesHirohitoTx, &upgradesNagakoTx};
    
    printf("[InitializeGame] Loading shipyard upgrade textures...\n");
    for (int i = 0; i < 3; i++) {
        bool loaded = false;
        for (int j = 0; j < 3; j++) {
            printf("[InitializeGame] Trying to load %s from: %s\n", upgradeNames[i], upgradePaths[i][j]);
            *upgradeTextures[i] = LoadTexture(upgradePaths[i][j]);
            if (upgradeTextures[i]->id > 0) {
                printf("[InitializeGame] SUCCESS: Loaded upgrade texture %d (%s) from: %s (size: %dx%d)\n", 
                       i, upgradeNames[i], upgradePaths[i][j], 
                       upgradeTextures[i]->width, upgradeTextures[i]->height);
                loaded = true;
                break;
            } else {
                printf("[InitializeGame] Failed to load from: %s\n", upgradePaths[i][j]);
            }
        }
        if (!loaded) {
            printf("[InitializeGame] ERROR: Failed to load upgrade texture %d (%s) from all paths!\n", i, upgradeNames[i]);
        }
    }
    
    // Load Depot, Station, and Halo overlay textures
    const char* overlayPaths[][3] = {
        {"Shinjuku_overlay.png", "Data/games/AstroMiner/Shinjuku_overlay.png", "../../games/AstroMiner/Shinjuku_overlay.png"},
        {"Hirohito_overlay.png", "Data/games/AstroMiner/Hirohito_overlay.png", "../../games/AstroMiner/Hirohito_overlay.png"},
        {"Nagako_overlay.png", "Data/games/AstroMiner/Nagako_overlay.png", "../../games/AstroMiner/Nagako_overlay.png"}
    };
    
    const char* overlayNames[] = {"Shinjuku_overlay", "Hirohito_overlay", "Nagako_overlay"};
    Texture2D* overlayTextures[] = {&shinjukuOverlayTx, &hirohitoOverlayTx, &nagakoOverlayTx};
    
    printf("[InitializeGame] Loading depot/station/halo overlay textures...\n");
    for (int i = 0; i < 3; i++) {
        bool loaded = false;
        for (int j = 0; j < 3; j++) {
            printf("[InitializeGame] Trying to load %s from: %s\n", overlayNames[i], overlayPaths[i][j]);
            *overlayTextures[i] = LoadTexture(overlayPaths[i][j]);
            if (overlayTextures[i]->id > 0) {
                printf("[InitializeGame] SUCCESS: Loaded overlay texture %d (%s) from: %s (size: %dx%d)\n", 
                       i, overlayNames[i], overlayPaths[i][j], 
                       overlayTextures[i]->width, overlayTextures[i]->height);
                loaded = true;
                break;
            } else {
                printf("[InitializeGame] Failed to load from: %s\n", overlayPaths[i][j]);
            }
        }
        if (!loaded) {
            printf("[InitializeGame] ERROR: Failed to load overlay texture %d (%s) from all paths!\n", i, overlayNames[i]);
        }
    }
    
    // Load prospect page overlays (base + A-F variants) with multiple fallbacks
    const char* prospectPagePaths[][3] = {
        {"prospect_page.png", "Data/games/AstroMiner/prospect_page.png", "../../games/AstroMiner/prospect_page.png"},
        {"prospect_page_A.png", "Data/games/AstroMiner/prospect_page_A.png", "../../games/AstroMiner/prospect_page_A.png"},
        {"prospect_page_B.png", "Data/games/AstroMiner/prospect_page_B.png", "../../games/AstroMiner/prospect_page_B.png"},
        {"prospect_page_C.png", "Data/games/AstroMiner/prospect_page_C.png", "../../games/AstroMiner/prospect_page_C.png"},
        {"prospect_page_D.png", "Data/games/AstroMiner/prospect_page_D.png", "../../games/AstroMiner/prospect_page_D.png"},
        {"prospect_page_E.png", "Data/games/AstroMiner/prospect_page_E.png", "../../games/AstroMiner/prospect_page_E.png"},
        {"prospect_page_F.png", "Data/games/AstroMiner/prospect_page_F.png", "../../games/AstroMiner/prospect_page_F.png"}
    };
    
    const char* prospectPageNames[] = {"prospect_page", "prospect_page_A", "prospect_page_B", "prospect_page_C", "prospect_page_D", "prospect_page_E", "prospect_page_F"};
    Texture2D* prospectPageTextures[] = {&prospectPageTx, &prospectPageATx, &prospectPageBTx, &prospectPageCTx, &prospectPageDTx, &prospectPageETx, &prospectPageFTx};
    
    printf("[InitializeGame] Loading prospect page overlay textures...\n");
    for (int i = 0; i < 7; i++) {
        bool loaded = false;
        for (int j = 0; j < 3; j++) {
            printf("[InitializeGame] Trying to load %s from: %s\n", prospectPageNames[i], prospectPagePaths[i][j]);
            *prospectPageTextures[i] = LoadTexture(prospectPagePaths[i][j]);
            if (prospectPageTextures[i]->id > 0) {
                printf("[InitializeGame] SUCCESS: Loaded prospect page texture %d (%s) from: %s (size: %dx%d)\n", 
                       i, prospectPageNames[i], prospectPagePaths[i][j], 
                       prospectPageTextures[i]->width, prospectPageTextures[i]->height);
                loaded = true;
                break;
            } else {
                printf("[InitializeGame] Failed to load from: %s\n", prospectPagePaths[i][j]);
            }
        }
        if (!loaded) {
            printf("[InitializeGame] ERROR: Failed to load prospect page texture %d (%s) from all paths!\n", i, prospectPageNames[i]);
        }
    }
    
    // Load shipyard shop page overlay textures (including base shipyard_page.png)
    printf("[InitializeGame] Loading shipyard shop page overlay textures...\n");
    const char* shipyardPagePaths[][3] = {
        {"shipyard_page.png", "Data/games/AstroMiner/shipyard_page.png", "../../games/AstroMiner/shipyard_page.png"},
        {"shipyard_page_A.png", "Data/games/AstroMiner/shipyard_page_A.png", "../../games/AstroMiner/shipyard_page_A.png"},
        {"shipyard_page_B.png", "Data/games/AstroMiner/shipyard_page_B.png", "../../games/AstroMiner/shipyard_page_B.png"},
        {"shipyard_page_C.png", "Data/games/AstroMiner/shipyard_page_C.png", "../../games/AstroMiner/shipyard_page_C.png"},
        {"shipyard_page_D.png", "Data/games/AstroMiner/shipyard_page_D.png", "../../games/AstroMiner/shipyard_page_D.png"},
        {"shipyard_page_E.png", "Data/games/AstroMiner/shipyard_page_E.png", "../../games/AstroMiner/shipyard_page_E.png"},
        {"shipyard_page_F.png", "Data/games/AstroMiner/shipyard_page_F.png", "../../games/AstroMiner/shipyard_page_F.png"}
    };
    const char* shipyardPageNames[] = {"shipyard_page", "shipyard_page_A", "shipyard_page_B", "shipyard_page_C", "shipyard_page_D", "shipyard_page_E", "shipyard_page_F"};
    Texture2D* shipyardPageTextures[] = {&shipyardPageTx, &shipyardPageATx, &shipyardPageBTx, &shipyardPageCTx, &shipyardPageDTx, &shipyardPageETx, &shipyardPageFTx};
    
    for (int i = 0; i < 7; i++) {
        bool loaded = false;
        for (int j = 0; j < 3; j++) {
            printf("[InitializeGame] Trying to load %s from: %s\n", shipyardPageNames[i], shipyardPagePaths[i][j]);
            *shipyardPageTextures[i] = LoadTexture(shipyardPagePaths[i][j]);
            if (shipyardPageTextures[i]->id > 0) {
                printf("[InitializeGame] SUCCESS: Loaded shipyard page texture %d (%s) from: %s (size: %dx%d)\n", 
                       i, shipyardPageNames[i], shipyardPagePaths[i][j], 
                       shipyardPageTextures[i]->width, shipyardPageTextures[i]->height);
                loaded = true;
                break;
            } else {
                printf("[InitializeGame] Failed to load from: %s\n", shipyardPagePaths[i][j]);
            }
        }
        if (!loaded) {
            printf("[InitializeGame] ERROR: Failed to load shipyard page texture %d (%s) from all paths!\n", i, shipyardPageNames[i]);
        }
    }
    
    // Load retro font for stats overlay (try multiple paths)
    const char* retroFontPaths[] = {
        "PressStart2P-Regular.ttf",
        "Data/games/AstroMiner/PressStart2P-Regular.ttf",
        "../../PressStart2P-Regular.ttf",
        "Retro Gaming.ttf",
        "Data/Retro Gaming.ttf",
        "../../Retro Gaming.ttf",
        "PressStart2P.ttf",
        "../../PressStart2P.ttf"
    };
    
    printf("[InitializeGame] Loading retro font...\n");
    bool fontLoaded = false;
    int numFontPaths = sizeof(retroFontPaths) / sizeof(retroFontPaths[0]);
    for (int i = 0; i < numFontPaths; i++) {
        printf("[InitializeGame] Trying to load font from: %s\n", retroFontPaths[i]);
        retroFont = LoadFont(retroFontPaths[i]);
        if (retroFont.texture.id > 0) {
            printf("[InitializeGame] SUCCESS: Loaded retro font from: %s\n", retroFontPaths[i]);
            fontLoaded = true;
            break;
        }
    }
    if (!fontLoaded) {
        printf("[InitializeGame] WARNING: Failed to load retro font, will use default font\n");
    }
    
    // Bake terrain chunks
    int chunkIdx = 0;
    float startP = -PROSPECT_PERIMETER;
    for (int z = 0; z < CHUNKS_AXIS; z++) {
        for (int x = 0; x < CHUNKS_AXIS; x++) {
            float cx = startP + (x * CHUNK_SIZE);
            float cz = startP + (z * CHUNK_SIZE);
            Mesh cMesh = CreateTerrainChunk(cx, cz, (float)CHUNK_SIZE);
            g_chunkModels[chunkIdx] = LoadModelFromMesh(cMesh);
            g_chunkCenters[chunkIdx] = (Vector2){ cx + CHUNK_SIZE/2.0f, cz + CHUNK_SIZE/2.0f };
            chunkIdx++;
        }
    }
    
    // Initialize game state
    g_shipPos = (Vector3){0, 60, -PROSPECT_PERIMETER};
    g_shipVel = (Vector3){0, 0, 10};
    
    // Stabilize ship at launch start (reset pitch, roll, yaw, and horizontal velocity)
    g_shipPitch = 0.0f;
    g_shipRoll = 0.0f;
    g_shipYaw = 0.0f;
    g_shipVel.x = 0.0f;  // Zero horizontal X velocity
    g_shipVel.z = 10.0f; // Keep forward Z velocity for initial movement
    g_shipPitch = 0.0f;
    g_shipRoll = 0.0f;
    g_shipYaw = 0.0f;
    g_yawDirection = 1;
    g_currentState = STATE_SPLASH;
    g_menuSelection = 0;
    
    // Ensure fuel is properly initialized
    G_Player.fuel = G_Player.maxFuel;
    
    // Initialize splash screen state
    g_splashIndex = 0;
    g_splashTimer = 0.0f;
    g_menuOption = 0;
    g_exit_requested = false;
    
    printf("[InitializeGame] Starting in STATE_SPLASH, splashIndex=%d\n", g_splashIndex);
    
    // Calculate station-specific commodity prices
    CalculateStationPrices();
    
    g_game_initialized = true;
    
    return g_framebuffer_initialized && g_game_initialized;
}

#ifdef __cplusplus
}
#endif

// ------------------------------------------------------------
// MAIN (for standalone testing - can be removed when embedded)
// ------------------------------------------------------------
int main(void)
{
    // Set standalone mode flag BEFORE InitializeGame
    g_standalone_mode = true;
    
    // For standalone mode, create a visible window
    // Override the hidden window settings from InitializeGame
    SetConfigFlags(0);  // No special flags - normal visible window
    InitWindow(VIRTUAL_WIDTH, VIRTUAL_HEIGHT, "Astro Miner - Standalone Debug");
    SetTargetFPS(60);
    
    if (!InitializeGame()) {
        CloseWindow();
        return 1;
    }
    
    printf("[main] Standalone mode - window created, starting game loop\n");
    printf("[main] Keyboard and mouse input will be polled from raylib\n");
    
    while (!WindowShouldClose() && !g_exit_requested)
    {
        UpdateFrame();
        
        // Draw framebuffer to screen
        BeginDrawing();
        ClearBackground(BLACK);
        DrawTexturePro(g_framebuffer.texture, 
            (Rectangle){0, 0, (float)g_framebuffer.texture.width, (float)-g_framebuffer.texture.height},
            (Rectangle){0, 0, (float)GetScreenWidth(), (float)GetScreenHeight()},
            (Vector2){0,0}, 0.0f, WHITE);
        EndDrawing();
    }
    
    CloseWindow();
    return 0;
}
