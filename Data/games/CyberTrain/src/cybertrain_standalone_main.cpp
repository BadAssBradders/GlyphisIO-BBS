// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
// MAIN FUNCTION - Entry point for standalone mode (not called in embedded mode)
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

int main() {
    // Standalone mode: initialize everything ourselves
    g_standalone_mode = true;
    
    // Fix working directory for standalone mode (so images can be found)
    // If running from bin/, change to parent directory (CyberTrain folder)
#ifdef _WIN32
    char exePath[MAX_PATH];
    GetModuleFileNameA(NULL, exePath, MAX_PATH);
    // Remove filename, get directory
    char* lastSlash = strrchr(exePath, '\\');
    if (lastSlash) {
        *lastSlash = '\0';
        // Check if directory ends with "\bin" or "/bin" (case-insensitive)
        int len = (int)strlen(exePath);
        if (len >= 4) {
            char* end = exePath + len - 4;
            // Simple case-insensitive check
            bool isBin = false;
            // Check exact match first
            if (strcmp(end, "\\bin") == 0 || strcmp(end, "/bin") == 0) {
                isBin = true;
            } else {
                // Try case-insensitive - convert to lowercase for comparison
                char lower[5] = {0};
                for (int i = 0; i < 4; i++) {
                    char c = end[i];
                    lower[i] = (c >= 'A' && c <= 'Z') ? (char)(c + 32) : c;
                }
                isBin = (strcmp(lower, "\\bin") == 0) || (strcmp(lower, "/bin") == 0);
            }
            if (isBin) {
                // We're in bin/, go up one level
                *end = '\0';
            }
        }
        SetCurrentDirectoryA(exePath);
        printf("[main] Changed working directory to: %s\n", exePath);
    }
#else
    char exePath[PATH_MAX];
    ssize_t count = readlink("/proc/self/exe", exePath, PATH_MAX);
    if (count != -1) {
        exePath[count] = '\0';
        char* lastSlash = strrchr(exePath, '/');
        if (lastSlash) {
            *lastSlash = '\0';
            // Check if directory ends with "/bin"
            int len = (int)strlen(exePath);
            if (len >= 4 && strcmp(exePath + len - 4, "/bin") == 0) {
                // We're in bin/, go up one level
                exePath[len - 4] = '\0';
            }
            chdir(exePath);
            printf("[main] Changed working directory to: %s\n", exePath);
        }
    }
#endif
    
    // Initialize window
    const int screenWidth = 1200;
    const int screenHeight = 800;
    InitWindow(screenWidth, screenHeight, "CyberTrain - Railway Builder");
    SetExitKey(KEY_NULL);  // Disable Raylib's built-in ESC-to-quit; we handle ESC in the game loop
    SetTargetFPS(60);

    // Initialize audio device (match AstroMiner pattern)
    SetAudioStreamBufferSizeDefault(16384);
    InitAudioDevice();

    // Load custom font (try multiple paths)
    const char* fontPaths[] = {
        "VT323-Regular.ttf",
        "../VT323-Regular.ttf",  // If running from bin/
        "Data/games/CyberTrain/VT323-Regular.ttf",
        "static/VT323-Regular.ttf"
    };
    bool fontLoaded = false;
    for (int i = 0; i < 4 && !fontLoaded; i++) {
        if (FileExists(fontPaths[i])) {
            gameFont = LoadFont(fontPaths[i]);
            if (gameFont.texture.id != 0) {
                fontIsCustom = true;
                fontLoaded = true;
                printf("[main] Loaded font from: %s\n", fontPaths[i]);
            }
        }
    }
    if (!fontLoaded) {
        TraceLog(LOG_WARNING, "Failed to load VT323-Regular.ttf, using default font");
        gameFont = GetFontDefault();
        fontIsCustom = false;
    }
    
    // Initialize debug file
    InitDebugFile();
    DebugLog("=== Game Started (Standalone) ===");
    
    // Initialize game state (same initialization as InitializeGame())
    // Generate clusters
    {
        const int clusterSeed = 42;
        ClusterGenResult clusterResult = GenerateClusters(CLUSTER_GRID_W, CLUSTER_GRID_H, clusterSeed);
        if (ValidateClusters(clusterResult, CLUSTER_GRID_W, CLUSTER_GRID_H)) {
            printf("[main] Clusters: %d generated, validation OK\n", (int)clusterResult.clusters.size());
        } else {
            printf("[main] Clusters: %d generated, validation FAILED\n", (int)clusterResult.clusters.size());
        }
        g_clusters = clusterResult.clusters;
        g_clusterGrid = std::move(clusterResult.grid);
        for (size_t i = 0; i < g_clusters.size(); i++) {
            printf("  [%zu] %s x=%d y=%d\n", i, ClusterTypeName(g_clusters[i].type), g_clusters[i].x, g_clusters[i].y);
        }
        fflush(stdout);
    }

    g_buildings = generateCitySkyline();

    // Add cluster buildings on the inner edge of the grid (individual cubes with stacking)
    AddClusterBuildings(g_buildings, g_clusters, 42);
    AddOuterRingBuildings(g_buildings, g_clusters, 42);

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
    g_tickerPosition = (float)screenWidth * 0.608f;
    
    // Initialize 2D map camera
    g_mapCamera.target = { 0.0f, 0.0f };
    g_mapCamera.offset = { (float)GetScreenWidth() * 0.5f, (float)GetScreenHeight() * 0.5f };
    g_mapCamera.rotation = 0.0f;
    g_mapCamera.zoom = 6.0f;
    
    g_game_initialized = true;
    
    // Load UI Assets (Standalone)
    LoadUIAssets();
    LoadAudioAssets();
    
    // Main game loop
    while (!WindowShouldClose()) {
        GameLoopBody();
    }
    
    // Cleanup
    UnloadAudioAssets();
    UnloadUIAssets();
    DebugLog("=== Game Ended ===");
    if (debugFile.is_open()) {
        debugFile.close();
    }
    if (fontIsCustom) {
        UnloadFont(gameFont);
    }
    CloseAudioDevice();
    CloseWindow();
    
    return 0;
}
