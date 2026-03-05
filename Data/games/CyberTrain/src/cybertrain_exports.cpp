// Forward declarations for functions defined later in the translation unit
static void GameLoopBody();
static void LoadCyberTrainLeaderboard();
static void LoadAudioAssets();
static void UnloadAudioAssets();

extern "C" {

__declspec(dllexport) bool InitializeGame() {
    printf("[InitializeGame] Starting CyberTrain unified initialization...\n");
    fflush(stdout);
    g_standalone_mode = false;
    g_exit_requested = false;
    // Match standalone startup flow in embedded mode (Astro-style parity).
    g_splashPhase = SplashPhase::FadeIn1;
    g_splashTimer = 0.0f;
    g_splash12Bright = 1.0f;
    g_splashTypeChars = 0;
    g_splashTypeTimer = 0.0f;
    g_introModalOpen = false;
    g_introModalFrames = 0;
    g_helpModalOpen = false;
    g_helpPage = 0;
    
    SetTraceLogLevel(LOG_NONE);
    
    if (!IsWindowReady()) {
        printf("[InitializeGame] Creating hidden window...\n");
        fflush(stdout);
        SetConfigFlags(FLAG_WINDOW_UNDECORATED | FLAG_WINDOW_HIDDEN);
        InitWindow(VIRTUAL_WIDTH, VIRTUAL_HEIGHT, "CyberTrain_Embedded");
        SetExitKey(KEY_NULL);  // Disable Raylib's built-in ESC-to-quit; we handle ESC in the game loop
        DisableCursor();
        SetTargetFPS(0); // Unlimited FPS for embedded mode
    }
    
    printf("[InitializeGame] Creating framebuffer %dx%d...\n", g_renderWidth, g_renderHeight);
    fflush(stdout);
    g_framebuffer = LoadRenderTexture(g_renderWidth, g_renderHeight);
    g_framebuffer_initialized = true;
    printf("[InitializeGame] Framebuffer texture format=%d (forcing RGBA8 readback)\n", g_framebuffer.texture.format);
    fflush(stdout);
    
    // Initialize audio device (matches AstroMiner embedded pattern)
    SetAudioStreamBufferSizeDefault(16384);
    InitAudioDevice();
    g_audio_initialized = true;
    printf("[InitializeGame] Audio device initialized\n");
    fflush(stdout);
    
    printf("[InitializeGame] Loading font...\n");
    fflush(stdout);
    const char* fontPaths[] = {"VT323-Regular.ttf", "Data/games/CyberTrain/VT323-Regular.ttf", "static/VT323-Regular.ttf"};
    bool fontLoaded = false;
    for (int i = 0; i < 3 && !fontLoaded; i++) {
        gameFont = LoadFont(fontPaths[i]);
        if (gameFont.texture.id != 0) { fontIsCustom = true; fontLoaded = true; }
    }
    if (!fontLoaded) gameFont = GetFontDefault();
    
    // Load UI Assets
    LoadUIAssets();
    LoadAudioAssets();

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
    // Generate clusters: 10 clusters (5x5 each, 1-cell gap). Grid 40x40 matches world extent (-100..100 with g_gridSpacing=5)
    const int clusterSeed = 42;
    ClusterGenResult clusterResult = GenerateClusters(CLUSTER_GRID_W, CLUSTER_GRID_H, clusterSeed);
    if (ValidateClusters(clusterResult, CLUSTER_GRID_W, CLUSTER_GRID_H)) {
        printf("[InitializeGame] Clusters: %d generated, validation OK\n", (int)clusterResult.clusters.size());
    } else {
        printf("[InitializeGame] Clusters: %d generated, validation FAILED\n", (int)clusterResult.clusters.size());
    }
    g_clusters = clusterResult.clusters;
    g_clusterGrid = std::move(clusterResult.grid);
    for (size_t i = 0; i < g_clusters.size(); i++) {
        printf("  [%zu] %s x=%d y=%d\n", i, ClusterTypeName(g_clusters[i].type), g_clusters[i].x, g_clusters[i].y);
    }
    // Report which corners have clusters
    int cs = CLUSTER_SIZE;
    const char* cornerNames[] = {"top-left (0,0)", "top-right (34,0)", "bottom-left (0,34)", "bottom-right (34,34)"};
    int cornerX[] = {0, CLUSTER_GRID_W - cs, 0, CLUSTER_GRID_W - cs};
    int cornerY[] = {0, 0, CLUSTER_GRID_H - cs, CLUSTER_GRID_H - cs};
    for (int ci = 0; ci < 4; ci++) {
        bool occupied = false;
        for (const auto& cl : g_clusters) {
            if (cl.x <= cornerX[ci] + cs - 1 && cl.x + cl.size - 1 >= cornerX[ci] &&
                cl.y <= cornerY[ci] + cs - 1 && cl.y + cl.size - 1 >= cornerY[ci]) {
                occupied = true;
                printf("  Corner %s: %s\n", cornerNames[ci], ClusterTypeName(cl.type));
                break;
            }
        }
        if (!occupied) printf("  Corner %s: EMPTY\n", cornerNames[ci]);
    }
    fflush(stdout);

    printf("[InitializeGame] Generating skyline...\n");
    fflush(stdout);
    g_buildings = generateCitySkyline();
    printf("[InitializeGame] Skyline generated: %d buildings\n", (int)g_buildings.size());
    fflush(stdout);

    // Add cluster buildings on the inner edge of the grid (individual cubes with stacking)
    AddClusterBuildings(g_buildings, g_clusters, clusterSeed);
    AddOuterRingBuildings(g_buildings, g_clusters, clusterSeed);

    InitializeMarketPrices();
    snprintf(g_tickerTextBuf, sizeof(g_tickerTextBuf), "%s", g_baseTickerText);

    // Initialize camera at distance 700; intro zoom animation will pull it in to 200
    float defaultZoomDistance = 700.0f;
    Vector3 defaultDirection = { 60.0f, 50.0f, 60.0f };
    float currentDistance = sqrtf(defaultDirection.x * defaultDirection.x + 
                                  defaultDirection.y * defaultDirection.y + 
                                  defaultDirection.z * defaultDirection.z);
    float scaleFactor = defaultZoomDistance / currentDistance;
    g_camera.position = (Vector3){ defaultDirection.x * scaleFactor, 
                                   defaultDirection.y * scaleFactor, 
                                   defaultDirection.z * scaleFactor };
    g_camera.target = (Vector3){ 0.0f, 0.0f, 0.0f };
    g_camera.up = (Vector3){ 0.0f, 1.0f, 0.0f };
    g_camera.fovy = 45.0f;
    g_camera.projection = CAMERA_PERSPECTIVE;
    g_cameraAltitude = g_camera.position.y;
    g_cameraYaw = atan2f(g_camera.position.x - g_camera.target.x, g_camera.position.z - g_camera.target.z);
    g_cameraRadius = sqrtf((g_camera.position.x - g_camera.target.x) * (g_camera.position.x - g_camera.target.x) +
                           (g_camera.position.z - g_camera.target.z) * (g_camera.position.z - g_camera.target.z));
    
    // Initialize ticker position (start at right edge of ticker area - 60.8% of width)
    g_tickerPosition = (float)g_renderWidth * 0.608f;
    
    // Initialize 2D map camera (zoom will be set to fit full grid when map is opened)
    g_mapCamera.target = { 0.0f, 0.0f };
    g_mapCamera.offset = { (float)g_renderWidth * 0.5f, (float)g_renderHeight * 0.5f };
    g_mapCamera.rotation = 0.0f;
    g_mapCamera.zoom = 6.0f;  // Default; pressing M sets zoom to fit full grid
    
    g_game_initialized = true;
    LoadCyberTrainLeaderboard();  // pre-load leaderboard for splash display
    printf("[InitializeGame] CyberTrain initialized successfully.\n");
    fflush(stdout);
    return true;
}

__declspec(dllexport) void UpdateFrame() { 
    if (!g_game_initialized || !g_framebuffer_initialized) return;
    g_debugFrameCounter++;
    
    // Run one iteration of the game loop
    GameLoopBody();
    
    // Clear one-shot input events
    ClearInputFrame();
}

__declspec(dllexport) unsigned char* GetFrameBuffer() {
    if (!g_framebuffer_initialized) return NULL;
    int w = g_framebuffer.texture.width, h = g_framebuffer.texture.height, sz = w*h*4;
    if (g_frame_buffer_size != sz) { if (g_frame_buffer_data) MemFree(g_frame_buffer_data); g_frame_buffer_data = (unsigned char*)MemAlloc(sz); g_frame_buffer_size = sz; }
    // Always request 32-bit RGBA so Python can safely treat the buffer as width*height*4 bytes.
    // Some platforms/backends store the render texture in a different native format.
    void* px = rlReadTexturePixels(g_framebuffer.texture.id, w, h, PIXELFORMAT_UNCOMPRESSED_R8G8B8A8);
    if (px) { memcpy(g_frame_buffer_data, px, sz); MemFree(px); }
    return g_frame_buffer_data;
}

__declspec(dllexport) int GetWidth() { return g_framebuffer_initialized ? g_framebuffer.texture.width : 0; }
__declspec(dllexport) int GetHeight() { return g_framebuffer_initialized ? g_framebuffer.texture.height : 0; }
__declspec(dllexport) void SetKeyState(int k, bool d) { if (k>=0 && k<512) { if (d && !g_inputState.keys[k]) g_inputState.keysPressed[k]=true; g_inputState.keys[k]=d; } }
__declspec(dllexport) void SetCharInput(int codepoint) {
    if (codepoint <= 0) return;
    int nextTail = (g_inputState.charQueueTail + 1) % 64;
    if (nextTail == g_inputState.charQueueHead) {
        // Queue full: drop oldest char to keep input responsive.
        g_inputState.charQueueHead = (g_inputState.charQueueHead + 1) % 64;
    }
    g_inputState.charQueue[g_inputState.charQueueTail] = codepoint;
    g_inputState.charQueueTail = nextTail;
}
__declspec(dllexport) void SetMouseButtonState(int b, bool d) {
    if (b>=0 && b<8) {
        if (d && !g_inputState.mouseButtons[b]) g_inputState.mouseButtonsPressed[b]=true;
        if (!d && g_inputState.mouseButtons[b]) g_inputState.mouseButtonsReleased[b]=true;
        g_inputState.mouseButtons[b]=d;
    }
}
__declspec(dllexport) void SetInputMousePosition(float x, float y) { g_inputState.mousePosition = {x, y}; }
__declspec(dllexport) void SetMouseDelta(float dx, float dy) { g_inputState.mouseDelta = {dx, dy}; }
__declspec(dllexport) void SetMouseWheelMove(float m) { g_inputState.mouseWheelMove = m; }
// ClearInputFrame is already defined above as a static function
__declspec(dllexport) bool ShouldExit() { return g_exit_requested; }
__declspec(dllexport) void CleanupGame() { if (g_framebuffer_initialized) { UnloadRenderTexture(g_framebuffer); g_framebuffer_initialized = false; } UnloadAudioAssets(); UnloadUIAssets(); if (g_frame_buffer_data) { MemFree(g_frame_buffer_data); g_frame_buffer_data = NULL; } g_frame_buffer_size = 0; g_game_initialized = false; g_renderWidth = 1200; g_renderHeight = 800; if (g_audio_initialized) { CloseAudioDevice(); g_audio_initialized = false; } }
__declspec(dllexport) void SetRenderResolution(int width, int height) { if (!g_framebuffer_initialized) { g_renderWidth = width; g_renderHeight = height; } }
__declspec(dllexport) unsigned int GetFrameTextureHandle() { return g_framebuffer_initialized ? g_framebuffer.texture.id : 0; }
__declspec(dllexport) void SetRenderResolutionPreset(int preset) { 
    if (g_framebuffer_initialized) return;
    if (preset == 0) { g_renderWidth = 480; g_renderHeight = 320; }
    else if (preset == 2) { g_renderWidth = 720; g_renderHeight = 480; }
    else { g_renderWidth = 1200; g_renderHeight = 800; }
}
__declspec(dllexport) bool ShouldCenterMouse() { bool r = g_shouldCenterMouse; g_shouldCenterMouse = false; return r; }
__declspec(dllexport) void SetUsername(const char* name) { if(name) { strncpy(g_username, name, 63); g_username[63] = '\0'; } }
__declspec(dllexport) int GetLastFinalScore() { return g_lastFinalScore; }
// â”€â”€ Leaderboard / game-over exports consumed by the Python Steam layer â”€â”€â”€â”€â”€â”€â”€â”€
__declspec(dllexport) bool IsGameOver() { return g_gameOver; }
__declspec(dllexport) int  GetFinalScore() { return g_finalScore; }
__declspec(dllexport) void PushLeaderboardEntry(const char* username, int score) {
    if (!username) return;
    for (auto& e : g_leaderboard) {
        if (strncmp(e.username, username, 63) == 0) {
            if (score > e.score) e.score = score;
            else return;
            goto sort_lb;
        }
    }
    { CyberTrainLBEntry ne; strncpy(ne.username, username, 63); ne.username[63]='\0'; ne.score=score; g_leaderboard.push_back(ne); }
    sort_lb:
    std::sort(g_leaderboard.begin(), g_leaderboard.end(),
        [](const CyberTrainLBEntry& a, const CyberTrainLBEntry& b){ return a.score > b.score; });
    if ((int)g_leaderboard.size() > kLBMaxEntries) g_leaderboard.resize(kLBMaxEntries);
}
__declspec(dllexport) int  GetLeaderboardCount() { return (int)g_leaderboard.size(); }
__declspec(dllexport) void GetLeaderboardEntry(int index, char* usernameOut, int usernameLen, int* scoreOut) {
    if (index < 0 || index >= (int)g_leaderboard.size()) return;
    if (usernameOut && usernameLen > 0) { strncpy(usernameOut, g_leaderboard[index].username, usernameLen-1); usernameOut[usernameLen-1]='\0'; }
    if (scoreOut) *scoreOut = g_leaderboard[index].score;
}

// Debug exports for Python-side diagnostics during BBS embedding.
__declspec(dllexport) int GetDebugFrameCounter() { return g_debugFrameCounter; }
__declspec(dllexport) int GetDebugRenderStage() { return g_debugRenderStage; }
__declspec(dllexport) int GetDebugSplashPhase() { return (int)g_splashPhase; }
__declspec(dllexport) int GetDebugIntroModalOpen() { return g_introModalOpen ? 1 : 0; }
__declspec(dllexport) int GetDebugHelpModalOpen() { return g_helpModalOpen ? 1 : 0; }
__declspec(dllexport) int GetDebugUIAssetsLoaded() { return g_uiAssetsLoaded ? 1 : 0; }
__declspec(dllexport) int GetDebugTextureIdUI() { return (int)g_texUI.id; }
__declspec(dllexport) int GetDebugTextureIdCursor() { return (int)g_texCursor.id; }
__declspec(dllexport) int GetDebugTextureIdSplash1() { return (int)g_splashTex1.id; }
__declspec(dllexport) int GetDebugTextureIdSplash2() { return (int)g_splashTex2.id; }
__declspec(dllexport) int GetDebugTextureIdSplash3() { return (int)g_splashTex3.id; }
__declspec(dllexport) int GetDebugTextureIdModal() { return (int)g_texModalTemplate.id; }
__declspec(dllexport) int GetDebugTextureIdLargeModal() { return (int)g_texLargeModalTemplate.id; }
__declspec(dllexport) int GetDebugFramebufferTextureId() { return (int)g_framebuffer.texture.id; }

}

