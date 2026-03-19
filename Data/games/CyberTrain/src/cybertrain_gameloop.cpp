// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
// GAME LOOP BODY - Called once per frame by UpdateFrame() or main()
// This is the heart of the game - all rendering and logic happens here
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

// ── CyberTrain cam helpers ────────────────────────────────────────────────────
static void ExitCyberTrainCam() {
    g_camera.position  = g_cyberTrainCamSavedPos;
    g_camera.target    = g_cyberTrainCamSavedTarget;
    g_cameraAltitude   = g_cyberTrainCamSavedAlt;
    g_cameraRadius     = g_cyberTrainCamSavedRadius;
    g_cameraYaw        = g_cyberTrainCamSavedYaw;
    g_currentGameSpeed = g_cyberTrainCamSavedSpeed;
    g_cyberTrainCamActive  = false;
    g_cyberTrainCamTrainId = -1;
}

static void EnterCyberTrainCam(int siloSystem) {
    // Find the most-recently created silo matching this system to get its lineId
    int targetLineId = -1;
    for (int i = (int)g_silos.size() - 1; i >= 0; i--) {
        if ((int)g_silos[i].system == siloSystem) { targetLineId = g_silos[i].lineId; break; }
    }
    // Find a train on that line with a valid path
    int trainId = -1;
    for (const auto& t : g_placedTrains) {
        if (t.lineId == targetLineId && (int)t.path.size() >= 2) { trainId = t.id; break; }
    }
    // Fallback: any train whose type matches the silo system
    if (trainId < 0) {
        for (const auto& t : g_placedTrains) {
            if (RequiredSiloSystemForTrainType(t.type) == siloSystem && (int)t.path.size() >= 2) {
                trainId = t.id; break;
            }
        }
    }
    if (trainId < 0) return;  // No eligible train on this line; skip silently

    // Save current camera + speed state
    g_cyberTrainCamSavedPos    = g_camera.position;
    g_cyberTrainCamSavedTarget = g_camera.target;
    g_cyberTrainCamSavedAlt    = g_cameraAltitude;
    g_cyberTrainCamSavedRadius = g_cameraRadius;
    g_cyberTrainCamSavedYaw    = g_cameraYaw;
    g_cyberTrainCamSavedSpeed  = g_currentGameSpeed;

    g_cyberTrainCamTrainId = trainId;
    g_cyberTrainCamActive  = true;
    g_currentGameSpeed     = SPEED_QUICK;
    g_mapMode              = false;
}

static void ClearPlacementProtectionForPlatform(const Vector3& position) {
    long long key = MakePositionKey(position.x, position.z);
    g_demolishNeutralizedPlatformKeys.erase(key);
    g_declinedNeutralBranchPlatformKeys.erase(key);
}

static int ProcessCargoBureauMaterialSales(int monthsCrossed) {
    if (monthsCrossed <= 0 || g_placedBureaus.empty() || g_silos.empty()) return 0;

    std::set<int> cargoSiloLineIds;
    for (const auto& silo : g_silos) {
        if (silo.system == SiloSystem::SYS1_CARGO) cargoSiloLineIds.insert(silo.lineId);
    }
    if (cargoSiloLineIds.empty()) return 0;

    std::unordered_map<int, int> demandByLineId;
    for (int bi = 0; bi < (int)g_placedBureaus.size(); bi++) {
        int li = (bi < (int)g_cachedBureauLineId.size()) ? g_cachedBureauLineId[bi] : -1;
        if (!IsLineEstablishedByIndex(li)) continue;
        int lineId = g_lines[li].id;
        if (cargoSiloLineIds.find(lineId) == cargoSiloLineIds.end()) continue;
        demandByLineId[lineId] += g_placedBureaus[bi].floors * monthsCrossed;
    }
    if (demandByLineId.empty()) return 0;

    int totalCredits = 0;
    for (const auto& line : g_lines) {
        auto it = demandByLineId.find(line.id);
        if (it == demandByLineId.end()) continue;

        int soldMat = RemoveCargoFromLineOwnedDepots(g_placedPlatforms, line.id, it->second);
        if (soldMat <= 0) continue;

        int credits = soldMat * 100;
        g_playerCredits += credits;
        totalCredits += credits;

        char buf[160];
        snprintf(buf, sizeof(buf), "[CARGO] MAT SALES %s: +%d CR (%d MAT)", line.name.c_str(), credits, soldMat);
        AppendTerminalMessage(buf);
    }
    return totalCredits;
}

static void RebuildTrainsOnLines(const std::set<int>& affectedLineIds) {
    if (affectedLineIds.empty()) return;
    for (auto& train : g_placedTrains) {
        if (train.isPaused) continue;
        if (!affectedLineIds.count(train.lineId)) continue;
        (void)RebuildTrainPath(train, g_placedPlatforms, g_gridSpacing);
    }
}

static bool HasAnyActiveTrainOnLine(int lineId, int ignoreTrainIndex = -1) {
    for (int i = 0; i < (int)g_placedTrains.size(); i++) {
        if (i == ignoreTrainIndex) continue;
        const PlacedTrain& train = g_placedTrains[i];
        if (train.isPaused) continue;
        if (train.lineId == lineId) return true;
    }
    return false;
}

static void RemovePlatformsAndRemapState(const std::vector<int>& indicesToRemove) {
    if (indicesToRemove.empty()) return;

    const int oldSize = (int)g_placedPlatforms.size();
    std::set<int> removed(indicesToRemove.begin(), indicesToRemove.end());
    std::set<long long> removedKeys;
    for (int idx : removed) {
        if (idx < 0 || idx >= oldSize) continue;
        const Vector3& pos = g_placedPlatforms[idx].position;
        removedKeys.insert(MakePositionKey(pos.x, pos.z));
    }

    for (long long key : removedKeys) {
        g_demolishNeutralizedPlatformKeys.erase(key);
        g_declinedNeutralBranchPlatformKeys.erase(key);
        g_lockedBranchOwnerLineId.erase(key);
        g_overpassGroupsByPosKey.erase(key);
    }
    for (auto& line : g_lines) {
        for (long long key : removedKeys) {
            line.declinedBranchPlatformKeys.erase(key);
        }
    }

    std::vector<int> oldToNew(oldSize, -1);
    int nextIndex = 0;
    for (int i = 0; i < oldSize; i++) {
        if (removed.count(i)) continue;
        oldToNew[i] = nextIndex++;
    }

    std::vector<int> sorted(indicesToRemove.begin(), indicesToRemove.end());
    std::sort(sorted.begin(), sorted.end(), std::greater<int>());
    for (int idx : sorted) {
        if (idx >= 0 && idx < (int)g_placedPlatforms.size())
            g_placedPlatforms.erase(g_placedPlatforms.begin() + idx);
    }

    for (auto& line : g_lines) {
        std::set<int> remapped;
        for (int pi : line.platformIndices) {
            if (pi >= 0 && pi < oldSize && oldToNew[pi] >= 0)
                remapped.insert(oldToNew[pi]);
        }
        line.platformIndices = remapped;
    }

    if (g_lineModal.state != LineModalState::None) {
        auto remapVec = [&](std::vector<int>& v) {
            std::vector<int> remapped;
            for (int pi : v) {
                if (pi >= 0 && pi < oldSize && oldToNew[pi] >= 0)
                    remapped.push_back(oldToNew[pi]);
            }
            v = remapped;
        };
        remapVec(g_lineModal.pendingNewPlatforms);
        remapVec(g_lineModal.pendingJunctions);
        remapVec(g_lineModal.pendingEstablishPlatforms);
        std::set<int> remappedTarget;
        for (int pi : g_lineModal.targetPlatformIndicesAtShow) {
            if (pi >= 0 && pi < oldSize && oldToNew[pi] >= 0)
                remappedTarget.insert(oldToNew[pi]);
        }
        g_lineModal.targetPlatformIndicesAtShow = remappedTarget;
        g_lineModal.pendingCid = -1;
    }

    if (g_stationModal.anchorPlatformIndex >= 0) {
        if (g_stationModal.anchorPlatformIndex < oldSize)
            g_stationModal.anchorPlatformIndex = oldToNew[g_stationModal.anchorPlatformIndex];
        else
            g_stationModal.anchorPlatformIndex = -1;
    }

    InvalidatePlatformCaches();
    InvalidateLineCaches();
}

static void RestartToSplashAfterGameOver() {
    // Reset game/session flow flags
    g_exit_requested = false;
    g_gameOver = false;
    g_finalScore = 0;
    g_lastFinalScore = 0;
    g_gameOverTimer = 0.0f;
    g_gameOverPhase = 0;
    g_year5WarningShown = false;
    g_year5ModalOpen = false;
    g_year5ModalFrames = 0;
    g_bankruptcyGraceActive = false;
    g_bankruptcyDeadlineYear = -1;

    // Reset world state
    g_playerCredits = 50000;
    g_nextLineId = 1;
    g_nextTrainId = 1;
    g_selectedTrainIndex = -1;
    g_junctionSetupTrainId = -1;
    g_junctionSetupBadgeTimer = 0.0f;
    g_nextPlacementGroupId = 1;
    g_dayClock = 0.0f;
    g_currentGameSpeed = SPEED_PAUSE;
    g_mapMode = false;
    g_trainPlacementMode = false;
    g_cargoTrainPlacementMode = false;
    g_depotPlacementMode = false;
    g_factoryPlacementMode = false;
    g_stationPlacementMode = false;
    g_bureauPlacementMode = false;
    g_demolishMode = false;
    g_platformDragActive = false;
    g_platformDragPlacedKeys.clear();
    g_mouseWorldPos = {0.0f, 0.0f, 0.0f};

    // Clear runtime containers/caches
    g_placedPlatforms.clear();
    g_placedTrains.clear();
    g_placedFactories.clear();
    g_placedBureaus.clear();
    g_lines.clear();
    g_silos.clear();
    g_buildParticles.clear();
    g_factorySmokeParticles.clear();
    g_terminalMessages.clear();
    g_establishedLineIds.clear();
    g_lineBureauSiloPotential.clear();
    g_previousStationComponentKeys.clear();
    g_cachedStationCompId.clear();
    g_cachedStationCompKey.clear();
    g_cachedStationMembers.clear();
    g_cachedPlatformTypes.clear();
    g_cachedPlatformLineId.clear();
    g_cachedStationPrimePlatformIdx.clear();
    g_cachedStationPrimePos.clear();
    g_cachedStationHasAdjacentDepot.clear();
    g_cachedBureauLineId.clear();
    g_declinedComponentKeys.clear();
    g_declinedNeutralBranchPlatformKeys.clear();
    g_demolishNeutralizedPlatformKeys.clear();
    g_lockedBranchOwnerLineId.clear();
    g_overpassGroupsByPosKey.clear();
    memset(g_siloCountBySystem, 0, sizeof(g_siloCountBySystem));
    memset(g_previousSiloCountBySystem, 0, sizeof(g_previousSiloCountBySystem));
    memset(g_sysTrainMoving, 0, sizeof(g_sysTrainMoving));
    memset(g_sysTrainWasMoving, 0, sizeof(g_sysTrainWasMoving));

    // Reset modal state
    g_lineModal = LineModalData{};
    g_junctionModal = JunctionModalData{};
    g_stationModal = StationModalData{};
    g_stockModal = StockCommoditiesModalData{};
    g_siloAnnounceModal = SiloAnnounceModalData{};
    g_demolishConfirmModal = DemolishConfirmModal{};
    g_lineModalOpen = false;
    g_junctionModalOpen = false;
    g_stockModalOpen = false;
    g_stationModalOpen = false;
    g_demolishConfirmModalOpen = false;

    // Rebuild generated world
    const int clusterSeed = 42;
    ClusterGenResult clusterResult = GenerateClusters(CLUSTER_GRID_W, CLUSTER_GRID_H, clusterSeed);
    g_clusters = clusterResult.clusters;
    g_clusterGrid = std::move(clusterResult.grid);
    g_buildings = generateCitySkyline();
    AddClusterBuildings(g_buildings, g_clusters, clusterSeed);
    AddOuterRingBuildings(g_buildings, g_clusters, clusterSeed);

    // Reset market/economy and ticker
    InitializeMarketPrices();
    snprintf(g_tickerTextBuf, sizeof(g_tickerTextBuf), "%s", g_baseTickerText);
    g_tickerPosition = (float)g_renderWidth * 0.608f;

    // Reset camera and intro/help flow to startup defaults
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
    g_cyberTrainCamActive = false;
    g_cyberTrainCamTrainId = -1;
    g_cyberTrainCamSavedPos = g_camera.position;
    g_cyberTrainCamSavedTarget = g_camera.target;
    g_cyberTrainCamSavedAlt = g_cameraAltitude;
    g_cyberTrainCamSavedRadius = g_cameraRadius;
    g_cyberTrainCamSavedYaw = g_cameraYaw;
    g_cyberTrainCamSavedSpeed = g_currentGameSpeed;
    g_mapCamera.target = { 0.0f, 0.0f };
    g_mapCamera.offset = { (float)g_renderWidth * 0.5f, (float)g_renderHeight * 0.5f };
    g_mapCamera.rotation = 0.0f;
    g_mapCamera.zoom = 6.0f;

    // Return to the very start splash sequence
    g_splashPhase = SplashPhase::FadeIn1;
    g_splashTimer = 0.0f;
    g_splash12Bright = 1.0f;
    g_splashTypeChars = 0;
    g_splashTypeTimer = 0.0f;
    g_introModalOpen = false;
    g_introModalFrames = 0;
    g_helpModalOpen = false;
    g_helpPage = 0;
    g_zoomIntroActive = false;
    g_zoomIntroDone = false;

    // Reset audio state
    g_currentTrack = 0;
    for (int i = 0; i < 3; i++) {
        if (g_musicTracks[i].stream.buffer != NULL) StopMusicStream(g_musicTracks[i]);
    }
    g_pendingSfxActive = false;
    g_pendingSfxTimer = 0.0f;
    g_musicVolume = 1;
    g_sfxVolume = 1;
    g_gammaLevel = 1;
    g_optionsScreen = OptionsScreen::Hidden;
    ApplyMusicVolume();
    ApplySfxVolume();

    LoadCyberTrainLeaderboard();
}

static void GameLoopBody() {
    if (DrawSplashScreen() || g_exit_requested) return;  // Show splash until SPACE is pressed, or stop immediately if splash requested exit

    // ── Audio update ──────────────────────────────────────────────────────────
    UpdateMusic();

    // Pending SFX timer (delayed BUILD-Sys8-12.wav after factory/bureau build)
    if (g_pendingSfxActive) {
        g_pendingSfxTimer -= GetFrameTime();
        if (g_pendingSfxTimer <= 0.0f) {
            g_pendingSfxActive = false;
            if (g_sfxBuildSys.frameCount > 0) PlaySound(g_sfxBuildSys);
        }
    }

    // â”€â”€ Game-over: freeze all gameplay, show end screen only â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    if (g_gameOver) {
        g_debugRenderStage = 2;
        if (!g_standalone_mode && g_framebuffer_initialized) BeginTextureMode(g_framebuffer);
        else BeginDrawing();
        ClearBackground(BLACK);
        DrawEndGameScreen();
        DrawCustomCursor();
        if (!g_standalone_mode && g_framebuffer_initialized) EndTextureMode();
        else EndDrawing();
        return;
    }

    // Compute modal guard once per frame: blocks all game hotkeys when any modal is active
    bool anyModalOpen = (g_lineModal.state != LineModalState::None)
        || g_stockModal.open || g_stationModal.open
        || g_junctionModal.open || g_siloAnnounceModal.open
        || g_demolishConfirmModal.open || g_pausedTrainDeleteModal.open
        || g_quitConfirmModalOpen
        || g_junctionConfigModalOpen
        || g_year5ModalOpen
        || g_introModalOpen || g_helpModalOpen
        || (g_optionsScreen == OptionsScreen::Visible);
    if (g_modalClickBlockFrames > 0) g_modalClickBlockFrames--;

    // H key opens/closes help only when no game-blocking modal is open.
    // We allow H when the help modal itself is the only open modal (so it can be closed).
    if (CustomIsKeyPressed(KEY_H) && (!anyModalOpen || g_helpModalOpen)) {
        g_helpModalOpen = !g_helpModalOpen;
        if (g_helpModalOpen) { g_helpPage = 0; g_helpModalFrames = 0; }
    }
    // O key opens/closes options screen (allow when options is the only "modal")
    if (CustomIsKeyPressed(KEY_O) && (!anyModalOpen || g_optionsScreen == OptionsScreen::Visible)) {
        if (g_optionsScreen == OptionsScreen::Visible) {
            g_optionsScreen = OptionsScreen::Hidden;
        } else {
            g_optionsScreen = OptionsScreen::Visible;
            g_optionsSelection = 0;
        }
    }
    // When options screen is visible, handle its input
    if (g_optionsScreen == OptionsScreen::Visible) {
        HandleOptionsInput();
    }
    if (CustomIsKeyPressed(KEY_F8)) {
        g_cameraDebugOverlay = !g_cameraDebugOverlay;
        g_camDbgLogCounter = 0;
        AddTerminalMessage(g_cameraDebugOverlay ? "CAMERA LOG DEBUG: ON (debug.log)" : "CAMERA LOG DEBUG: OFF");
    }

    // Trigger intro zoom animation the first time all start-up modals close
    {
        static bool s_introHasOpened = false;
        if (g_introModalOpen || g_helpModalOpen) s_introHasOpened = true;
        if (s_introHasOpened && !g_introModalOpen && !g_helpModalOpen && !g_zoomIntroDone) {
            g_zoomIntroActive = true;
            g_zoomIntroDone   = true;
        }
    }

    // Toggle 2D map view (disabled when modal is open)
    if (CustomIsKeyPressed(KEY_M) && !anyModalOpen) {
        g_mapMode = !g_mapMode;
        if (g_mapMode) {
            g_mapCamera.target = WorldToMap(g_camera.target);
            // Set zoom so the entire grid fits on one screen (inner + outer extent)
            float gridSpan = 2.0f * g_gridExtentOuter;
            float minDim = (float)(g_renderWidth < g_renderHeight ? g_renderWidth : g_renderHeight);
            g_mapCamera.zoom = minDim / gridSpan;
            g_mapCamera.zoom = Clamp(g_mapCamera.zoom, 0.2f, 40.0f);
        }
    }

    // Update map camera controls (pan/zoom)
    float deltaTime = GetFrameTime();
    if (deltaTime <= 0.0f || deltaTime > 0.1f) deltaTime = 1.0f/60.0f;
    g_camDbgControlMode = 0;
    g_camDbgStep = 0.0f;
    g_camDbgMoveVector = {0.0f, 0.0f, 0.0f};
    
    // Handle spacebar to cycle game speed
    if (CustomIsKeyPressed(KEY_SPACE) && !anyModalOpen) {
        g_currentGameSpeed = (g_currentGameSpeed + 1) % 5;
    }
        
    // Calculate scaled delta time based on game speed
    float timeScale = GetGameTimeScale();
    float scaledDeltaTime = deltaTime * timeScale;

    if (g_lineModalOpen || g_junctionModalOpen || g_stockModalOpen || g_demolishConfirmModalOpen || g_stationModalOpen) scaledDeltaTime = 0.0f;

    // Advance in-game clock (always advances, even in map mode) - uses scaled time
    float prevDayClock = g_dayClock;
    g_dayClock += scaledDeltaTime;

    int dayCyclesPassed = 0;
    if (g_dayCycleSeconds > 0.0f) {
        dayCyclesPassed = (int)floorf((prevDayClock + scaledDeltaTime) / g_dayCycleSeconds);
        if (g_dayClock >= g_dayCycleSeconds) g_dayClock = fmodf(g_dayClock, g_dayCycleSeconds);
    }

    // Recompute train-moving flags for use by factory and bureau income blocks
    for (int si = 0; si < 7; si++) g_sysTrainMoving[si] = false;
    for (const auto& t : g_placedTrains) {
        if (t.path.size() < 2 || t.isPaused || t.isJammed || t.isDwelling) continue;
        if (fabsf(t.direction) > 0.0f) {
            int sys = RequiredSiloSystemForTrainType(t.type);
            if (sys >= 0 && sys < 7) g_sysTrainMoving[sys] = true;
        }
    }

    // Factory production: when a new day-cycle begins, each factory produces base cargo into its connected depot
    // cluster. Only SYS1 (Cargo) and SYS3 (Magenta) silo ecosystems can boost factories, and only when
    // that same line has at least one linked bureau.
    bool anyCargoTrainMoving = g_sysTrainMoving[(int)SiloSystem::SYS1_CARGO];
    if (dayCyclesPassed > 0 && anyCargoTrainMoving && !g_placedFactories.empty() && !g_placedPlatforms.empty()) {
        const float baseProducedPerFactory = 2.0f * (float)dayCyclesPassed;
        std::unordered_map<int, int> bureauFloorsByLineId;
        for (int bi = 0; bi < (int)g_placedBureaus.size(); bi++) {
            int li = (bi < (int)g_cachedBureauLineId.size()) ? g_cachedBureauLineId[bi] : -1;
            if (!IsLineEstablishedByIndex(li)) continue;
            int lineId = g_lines[li].id;
            bureauFloorsByLineId[lineId] += g_placedBureaus[bi].floors;
        }

        for (auto& f : g_placedFactories) {
            int connectedSiloCount = 0; // Only SYS1/SYS3 count
            int bureauFloorsOnLine = 0;
            if (f.lineOwnerId >= 0) {
                for (const auto& s : g_silos) {
                    if (s.lineId != f.lineOwnerId) continue;
                    if (s.system == SiloSystem::SYS1_CARGO) {
                        connectedSiloCount++;
                    } else if (s.system == SiloSystem::SYS3_MAGENTA && g_sysTrainMoving[(int)SiloSystem::SYS3_MAGENTA]) {
                        connectedSiloCount++;
                    }
                }
                auto bfIt = bureauFloorsByLineId.find(f.lineOwnerId);
                if (bfIt != bureauFloorsByLineId.end()) bureauFloorsOnLine = bfIt->second;
            }
            bool hasQualifyingEcosystem = (connectedSiloCount > 0 && bureauFloorsOnLine > 0);
            float productionMultiplier = 1.0f;
            if (hasQualifyingEcosystem) {
                productionMultiplier += 0.20f * (float)connectedSiloCount;
                productionMultiplier += 0.10f * (float)bureauFloorsOnLine;
            }
            float producedWithBonus = baseProducedPerFactory * productionMultiplier + f.productionCarry;
            int producedPerFactory = (int)floorf(producedWithBonus);
            f.productionCarry = producedWithBonus - (float)producedPerFactory;
            if (producedPerFactory <= 0) continue;

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

        // â”€â”€ Advance global week counter (always, regardless of market unlock) â”€â”€
        if (dayCyclesPassed > 0) {
            int prevDayCount = g_dayCount;
            g_dayCount += dayCyclesPassed;

            // Weekly running costs (trains) â€” reduced by cyan bureau floors
            int weeklyRunCost = CalculateWeeklyRunningCosts();
            if (weeklyRunCost > 0) {
                int totalWkCost = (int)ceilf(weeklyRunCost * dayCyclesPassed * GetRunningCostMultiplier());
                g_playerCredits -= totalWkCost;
                char wkBuf[128];
                snprintf(wkBuf, sizeof(wkBuf), "TRAIN UPKEEP: -%d CR (%d CR/WK)", totalWkCost, weeklyRunCost);
                AddTerminalMessage(wkBuf);
            }

            // Monthly running costs (track, stations, depots, factories, bureaus) â€” reduced by cyan bureau floors
            int prevMonths = GetTotalMonths(prevDayCount);
            int currMonths = GetTotalMonths(g_dayCount);
            int monthsCrossed = currMonths - prevMonths;
            if (monthsCrossed > 0) {
                int monthlyRunCost = CalculateMonthlyRunningCosts();
                if (monthlyRunCost > 0) {
                    int totalMthCost = (int)ceilf(monthlyRunCost * monthsCrossed * GetRunningCostMultiplier());
                    g_playerCredits -= totalMthCost;
                    char mthBuf[128];
                    snprintf(mthBuf, sizeof(mthBuf), "INFRASTRUCTURE UPKEEP: -%d CR (%d CR/MTH)", totalMthCost, monthlyRunCost);
                    AddTerminalMessage(mthBuf);
                }
                ProcessCargoBureauMaterialSales(monthsCrossed);
            }
        }

        // â”€â”€ Year boundary checks (fire once per year crossing) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        if (dayCyclesPassed > 0) {
            int cyWk, cyMonth, cyYear;
            GetYearClock(g_dayCount, cyWk, cyMonth, cyYear);
            if (g_playerCredits < 0 && !g_bankruptcyGraceActive) {
                g_bankruptcyGraceActive = true;
                g_bankruptcyDeadlineYear = cyYear + 1;
                char debtBuf[160];
                snprintf(debtBuf, sizeof(debtBuf),
                    "CREDITS NEGATIVE -- ONE YEAR TO RECOVER (DEADLINE YEAR %d)", g_bankruptcyDeadlineYear);
                AddTerminalMessage(debtBuf);
            } else if (g_playerCredits >= 0 && g_bankruptcyGraceActive) {
                g_bankruptcyGraceActive = false;
                g_bankruptcyDeadlineYear = -1;
                AddTerminalMessage("DEBT CLEARED -- OPERATING IN THE BLACK");
            }
            if (g_bankruptcyGraceActive && g_playerCredits < 0 &&
                g_bankruptcyDeadlineYear > 0 && cyYear >= g_bankruptcyDeadlineYear && !g_gameOver) {
                g_gameOver       = true;
                g_gameOverPhase  = 0;
                g_gameOverTimer  = 0.0f;
                g_finalScore     = g_playerCredits;
                g_lastFinalScore = g_finalScore;
                SaveAndMergeLBEntry(g_username, g_finalScore);
                LoadCyberTrainLeaderboard();
                AddTerminalMessage("BANKRUPTCY CONFIRMED -- NETWORK ADMINISTRATION REVOKED");
            }
            if (cyYear >= 5 && !g_year5WarningShown) {
                g_year5WarningShown = true;
                g_year5ModalOpen    = true;
                g_year5ModalFrames  = 0;
            }
            if (cyYear >= 6 && !g_gameOver) {
                g_gameOver       = true;
                g_finalScore     = g_playerCredits;
                g_lastFinalScore = g_finalScore;
                SaveAndMergeLBEntry(g_username, g_finalScore);
                LoadCyberTrainLeaderboard();
                char msg[128];
                snprintf(msg, sizeof(msg), "YEAR 6 REACHED -- FINAL NET INCOME: %d CR", g_finalScore);
                AddTerminalMessage(msg);
            }
        }

        // Market day-cycle updates: prices, events, revenue
        if (g_marketUnlocked) {
            for (int dc = 0; dc < dayCyclesPassed; dc++) {
                UpdateMarketEvents();
                UpdateMarketPrices();
            }
            int revenue = CalculateMarketRevenue() * dayCyclesPassed;
            g_marketRevenueLast = CalculateMarketRevenue();
            if (revenue > 0) {
                g_playerCredits += revenue;
                char revBuf[128];
                snprintf(revBuf, sizeof(revBuf), "MARKET REVENUE: +%d CREDITS", revenue);
                AddTerminalMessage(revBuf);
            }
            RebuildTickerText();
        }

        // Bureau income: pay for each non-cargo system that has a moving train
        if (dayCyclesPassed > 0) {
            int bureauFloorsBySys[7] = {0};
            for (int bi = 0; bi < (int)g_placedBureaus.size(); bi++) {
                int li = (bi < (int)g_cachedBureauLineId.size()) ? g_cachedBureauLineId[bi] : -1;
                if (!IsLineEstablishedByIndex(li)) continue;
                std::set<int> lineSystems;
                for (const auto& s : g_silos) {
                    if (s.lineId == g_lines[li].id && s.system != SiloSystem::SYS1_CARGO)
                        lineSystems.insert((int)s.system);
                }
                for (int sys : lineSystems) {
                    if (sys >= 1 && sys <= 6) bureauFloorsBySys[sys] += g_placedBureaus[bi].floors;
                }
            }
            const char* sysNames[] = {"CARGO","GREEN","MAGENTA","CYAN","ORANGE","RED","YELLOW"};
            for (int sys = 1; sys <= 6; sys++) {
                if (!g_sysTrainMoving[sys] || bureauFloorsBySys[sys] <= 0) continue;
                int income = (int)(bureauFloorsBySys[sys] * kBureauIncomePerFloorPerDay * dayCyclesPassed);
                if (income > 0) {
                    g_playerCredits += income;
                    char buf[128];
                    snprintf(buf, sizeof(buf), "[%s] BUREAU INCOME: +%d CR", sysNames[sys], income);
                    AppendTerminalMessage(buf);
                }
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

        float brightness = 1.0f;  // No dimming â€” constant full brightness
        Color nightBlue = (Color){ 0, 0, 0, 255 };  // No night tint

        Color g_platformColorEff = AddColor(MulColor(g_platformColor, brightness), nightBlue);
        Color g_stationColorEff  = AddColor(MulColor(g_stationColor,  brightness), nightBlue);
        Color g_pointsColorEff   = AddColor(MulColor(g_pointsColor,   brightness), nightBlue);
        if (g_mapMode) {
            // Keep offset centered in case window size changes
            g_mapCamera.offset = { (float)g_renderWidth * 0.5f, (float)g_renderHeight * 0.5f };

            // Zoom with mouse wheel: allow zoom out so the entire grid fits on one screen (zoom min < 1)
            float wheel = CustomGetMouseWheelMove();
            if (wheel != 0.0f) {
                float zoomFactor = 1.0f + wheel * 0.15f;
                float minZoom = 0.2f;   // Zoom out enough to see full grid (2*g_gridExtentOuter) on typical screens
                float maxZoom = 40.0f;
                g_mapCamera.zoom = Clamp(g_mapCamera.zoom * zoomFactor, minZoom, maxZoom);
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
        g_mouseInEffective3DArea = false;  // Reset; set below when in viewfinder and not cutout
        if (!g_mapMode) {
        // Skip 3D interaction when mouse is in the cutout (that area is UI, not 3D)
        float vfw = (0.968f - 0.143f) * (float)g_renderWidth;
        float vfh = (0.76f - 0.122f) * (float)g_renderHeight;
        Rectangle vfRect = (Rectangle){ 0.143f * g_renderWidth, 0.122f * g_renderHeight, vfw, vfh };
        float cutSize = 0.06f * (vfw < vfh ? vfw : vfh);
        Rectangle cutRect = (Rectangle){ vfRect.x, vfRect.y + vfRect.height - (cutSize + 0.035f * g_renderHeight), cutSize + 0.017f * g_renderWidth, cutSize + 0.035f * g_renderHeight };
        bool mouseInCutout = CheckCollisionPointRec(mousePos, cutRect);
        g_mouseInEffective3DArea = CheckCollisionPointRec(mousePos, vfRect) && !mouseInCutout;
        
        // Use GetScreenToWorldRayEx with framebuffer dimensions for accurate ray calculation in embedded mode
        Ray mouseRay = GetScreenToWorldRayEx(mousePos, g_camera, g_renderWidth, g_renderHeight);
        
        // Calculate intersection with ground plane (y=0) manually - only update when in 3D area (not cutout)
        if (g_mouseInEffective3DArea && (mouseRay.direction.y < -0.0001f || mouseRay.direction.y > 0.0001f)) {
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
                // For station placement, offset center so the 4-tile station aligns to grid for all 4 orientations
                else if (g_stationPlacementMode) {
                    switch (g_placementOrientation) {
                        case 0: g_mouseWorldPos = { snappedX + g_gridSpacing * 1.5f, 0.0f, snappedZ }; break;  // +X
                        case 1: g_mouseWorldPos = { snappedX, 0.0f, snappedZ + g_gridSpacing * 1.5f }; break;  // +Z
                        case 2: g_mouseWorldPos = { snappedX - g_gridSpacing * 1.5f, 0.0f, snappedZ }; break;  // -X
                        case 3: g_mouseWorldPos = { snappedX, 0.0f, snappedZ - g_gridSpacing * 1.5f }; break;  // -Z
                        default: g_mouseWorldPos = { snappedX + g_gridSpacing * 1.5f, 0.0f, snappedZ }; break;
                    }
                } else {
                    g_mouseWorldPos = { snappedX, 0.0f, snappedZ };
                }
            }
        }
        }  // !g_mapMode - only compute effective 3D area and world pos when in 3D viewfinder
        else if (g_mapMode) {
            // In map mode: convert screen mouse to world and snap to grid center (for click hit-test)
            Vector3 world = MapScreenToWorld(mousePos);
            float gridCellX = floorf(world.x / g_gridSpacing);
            float gridCellZ = floorf(world.z / g_gridSpacing);
            g_mouseWorldPos.x = gridCellX * g_gridSpacing + g_gridSpacing / 2.0f;
            g_mouseWorldPos.z = gridCellZ * g_gridSpacing + g_gridSpacing / 2.0f;
            g_mouseWorldPos.y = 0.0f;
        }
        
        // Handle T key to toggle platform/track placement mode (disabled in map mode, when modal is open, or when awaiting first train)
        if (!g_mapMode && !anyModalOpen && g_awaitingTrainForLineId < 0 && CustomIsKeyPressed(KEY_T)) {
            bool wasOn = IsTrackPlacementSelected();
            ClearAllPlacementModes();
            if (!wasOn) { g_trainPlacementMode = true; g_selectedBottomHotspot = 0; }
        }

        // Handle C key to toggle cargo train placement mode.
        // When a newly established line is awaiting its first train, only allow cargo mode
        // if that awaited line actually accepts cargo trains.
        bool cargoModeAllowed = (g_awaitingTrainForLineId < 0)
            || AwaitedLineAcceptsTrainType(PlacedTrain::TrainType::Cargo);
        if (!g_mapMode && !anyModalOpen && cargoModeAllowed && CustomIsKeyPressed(KEY_C)) {
            if (!g_cargoTrainPlacementMode) {
                ClearAllPlacementModes();
                g_cargoTrainPlacementMode = true;
                g_cargoPlacementTrailers = (g_system1CargoState >= 1 && g_system1CargoState <= 3) ? g_system1CargoState : 1;
            } else {
                g_cargoPlacementTrailers = (g_system1CargoState >= 1 && g_system1CargoState <= 3) ? g_system1CargoState : 1;
            }
        }

        // Handle D key to toggle Materials-Depot placement mode (disabled in map mode, when modal is open, or when awaiting first train)
        if (!g_mapMode && !anyModalOpen && g_awaitingTrainForLineId < 0 && CustomIsKeyPressed(KEY_D)) {
            bool wasOn = g_depotPlacementMode;
            ClearAllPlacementModes();
            if (!wasOn) { g_depotPlacementMode = true; g_selectedBottomHotspot = 2; }
        }

        // Handle F key to toggle Factory placement mode (disabled in map mode, when modal is open, or when awaiting first train)
        if (!g_mapMode && !anyModalOpen && g_awaitingTrainForLineId < 0 && CustomIsKeyPressed(KEY_F)) {
            bool wasOn = g_factoryPlacementMode;
            ClearAllPlacementModes();
            if (!wasOn) { g_factoryPlacementMode = true; g_selectedBottomHotspot = 3; }
        }
        
        // Handle B key to toggle Bureau placement mode (disabled in map mode, when modal is open, or when awaiting first train)
        if (!g_mapMode && !anyModalOpen && g_awaitingTrainForLineId < 0 && CustomIsKeyPressed(KEY_B)) {
            if (!g_bureauPlacementMode) {
                ClearAllPlacementModes();
                g_bureauPlacementMode = true;
                g_bureauFloorIndex = 0;
                g_selectedBottomHotspot = 4;
            } else {
                g_bureauFloorIndex = (g_bureauFloorIndex + 1) % (int)g_bureauFloorOptions.size();
            }
            {
                int floors = g_bureauFloorOptions[g_bureauFloorIndex];
                int minCost = ApplyBuildDiscount(floors * GetBureauCostPerFloorForSystem((int)SiloSystem::SYS1_CARGO));
                int maxCost = ApplyBuildDiscount(floors * GetBureauCostPerFloorForSystem((int)SiloSystem::SYS7_YELLOW));
                int cargo = ApplyOrangeBureauDiscount(GetBureauCargoCost(g_bureauFloorIndex));
                char buf[256];
                snprintf(buf, sizeof(buf), "BUREAU (B): %d-%d CREDITS (%d floors, %d cargo). Cost/floor by line: Cargo/Neutral 3000, Green 3500, Magenta 4000, Orange 4500, Cyan 5000, Red 5500, Yellow 6000. Build rule: INNER ring must touch an established-line station tile; OUTER ring must have enough cargo. B cycles floors.", minCost, maxCost, floors, cargo);
                AddTerminalMessage(buf);
            }
        }
        
        // Handle S key to toggle station placement mode (disabled in map mode, when modal is open, or when awaiting first train)
        if (!g_mapMode && !anyModalOpen && g_awaitingTrainForLineId < 0 && CustomIsKeyPressed(KEY_S)) {
            bool wasOn = g_stationPlacementMode;
            ClearAllPlacementModes();
            if (!wasOn) { g_stationPlacementMode = true; g_selectedBottomHotspot = 1; }
        }

        // Handle R key to rotate placement orientation (all objects: station, depot, factory, bureau)
        // Cycles through 4 cardinal directions: 0=+X, 1=+Z, 2=-X, 3=-Z
        if (!g_mapMode && !anyModalOpen && CustomIsKeyPressed(KEY_R)) {
            bool inAnyPlacementMode = g_trainPlacementMode || g_cargoTrainPlacementMode || g_stationPlacementMode
                || g_depotPlacementMode || g_factoryPlacementMode || g_bureauPlacementMode;
            if (inAnyPlacementMode) {
                g_placementOrientation = (g_placementOrientation + 1) % 4;
            }
        }
        
        // Handle X key to toggle demolish mode (disabled in map mode and when modal is open)
        if (!g_mapMode && !anyModalOpen && CustomIsKeyPressed(KEY_X)) {
            bool wasOn = g_demolishMode;
            ClearAllPlacementModes();
            if (!wasOn) { g_demolishMode = true; }
        }
        
        // Handle D key to cycle dwell mode on selected train
        if (!g_mapMode && !anyModalOpen
            && CustomIsKeyPressed(KEY_D) && g_selectedTrainIndex >= 0
            && g_selectedTrainIndex < (int)g_placedTrains.size()) {
            PlacedTrain& t = g_placedTrains[g_selectedTrainIndex];
            t.dwellMode = (PlacedTrain::DwellMode)(((int)t.dwellMode + 1) % 3);
            const char* modeNames[] = {"FLOW", "SHORT WAIT (2s)", "LONG WAIT (10s)"};
            char buf[128];
            snprintf(buf, sizeof(buf), "TRAIN DWELL: %s", modeNames[(int)t.dwellMode]);
            AppendTerminalMessage(buf);
        }

        // Handle ESC key: blocked by modals; exits CyberTrain cam, otherwise opens quit modal
        if (CustomIsKeyPressed(KEY_ESCAPE) && !anyModalOpen) {
            if (g_cyberTrainCamActive) {
                ExitCyberTrainCam();
            } else if (g_splashPhase == SplashPhase::Done) {
                g_quitConfirmModal = {};
                g_quitConfirmModal.open = true;
                g_quitConfirmModalOpen  = true;
            }
        }

        // RMB hard-clear: return to neutral "nothing selected" state.
        if (CustomIsMouseButtonPressed(MOUSE_BUTTON_RIGHT)) {
            ClearAllPlacementModes();
            g_selectedTrainIndex = -1;
        }
        
        // Update bottom icon hotspot rects for this frame (used by click handler and DrawUIOverlay)
        {
            int sw = g_renderWidth;
            int sh = g_renderHeight;
            g_bottomHotspots[0] = (Rectangle){ 0.052f * sw, 0.829f * sh, (0.126f - 0.052f) * sw, (0.926f - 0.829f) * sh };   // system8
            g_bottomHotspots[1] = (Rectangle){ 0.143f * sw, 0.829f * sh, (0.219f - 0.143f) * sw, (0.926f - 0.829f) * sh };   // system9
            g_bottomHotspots[2] = (Rectangle){ 0.242f * sw, 0.829f * sh, (0.315f - 0.242f) * sw, (0.926f - 0.829f) * sh };   // system10
            g_bottomHotspots[3] = (Rectangle){ 0.332f * sw, 0.829f * sh, (0.408f - 0.332f) * sw, (0.926f - 0.829f) * sh };   // system11
            g_bottomHotspots[4] = (Rectangle){ 0.432f * sw, 0.829f * sh, (0.502f - 0.432f) * sw, (0.926f - 0.829f) * sh };   // system12
            g_bottomHotspots[5] = (Rectangle){ 0.528f * sw, 0.829f * sh, (0.602f - 0.528f) * sw, (0.926f - 0.829f) * sh };   // system13: Stock & Commodities
        }
        
        // Handle system hotspot clicks (display PNG only - NOT tied to placement modes)
        // Handle bottom icon hotspot clicks (system8-13: platform, station, depot, factory, bureau, Stock&Commodities)
        // Handle cutout click (system14: demolish)
        bool rawLeftPressed = RawIsMouseButtonPressed(MOUSE_BUTTON_LEFT);
        if (rawLeftPressed && !g_mapMode && !anyModalOpen) {
            Vector2 mousePos = CustomGetMousePosition();
            if (cargoModeAllowed && CheckCollisionPointRec(mousePos, g_systemHotspots[0])) {
                ClearAllPlacementModes();
                g_selectedSystemHotspot = 0;
                g_system1CargoState = (g_system1CargoState + 1) % 4;  // 0->1->2->3->0
                g_cargoPlacementTrailers = (g_system1CargoState >= 1 && g_system1CargoState <= 3) ? g_system1CargoState : 1;
                g_cargoTrainPlacementMode = true;
                AddTerminalMessage("CARGO TRAIN: Build cost 30/80/100 CR (1/2/3 trailers), running cost 10/20/30 CR/WK. Click a station on a matching established line to place. Click again to cycle trailer count (1-3).");
            } else if (CheckCollisionPointRec(mousePos, g_systemHotspots[1])) {
                ClearAllPlacementModes();
                g_selectedSystemHotspot = 1;
                g_trainColorIndex = 0;
                g_trainPlacementMode = true;
                AddTerminalMessage("GREEN PASSENGER: Build cost 150 CR, running cost 25 CR/WK. Click a station on a matching established line to place.");
            } else if (CheckCollisionPointRec(mousePos, g_systemHotspots[2])) {
                ClearAllPlacementModes();
                g_selectedSystemHotspot = 2;
                g_trainColorIndex = 1;
                g_trainPlacementMode = true;
                AddTerminalMessage("MAGENTA PASSENGER: Build cost 100 CR, running cost 20 CR/WK. Click a station on a matching established line to place.");
            } else if (CheckCollisionPointRec(mousePos, g_systemHotspots[3])) {
                ClearAllPlacementModes();
                g_selectedSystemHotspot = 3;
                g_trainColorIndex = 2;
                g_trainPlacementMode = true;
                AddTerminalMessage("CYAN PASSENGER: Build cost 100 CR, running cost 20 CR/WK. Click a station on a matching established line to place.");
            } else if (CheckCollisionPointRec(mousePos, g_systemHotspots[4])) {
                ClearAllPlacementModes();
                g_selectedSystemHotspot = 4;
                g_trainColorIndex = 3;
                g_trainPlacementMode = true;
                AddTerminalMessage("ORANGE PASSENGER: Build cost 100 CR, running cost 20 CR/WK. Click a station on a matching established line to place.");
            } else if (CheckCollisionPointRec(mousePos, g_systemHotspots[5])) {
                ClearAllPlacementModes();
                g_selectedSystemHotspot = 5;
                g_trainColorIndex = 4;
                g_trainPlacementMode = true;
                AddTerminalMessage("RED PASSENGER: Build cost 200 CR, running cost 50 CR/WK. Click a station on a matching established line to place.");
            } else if (CheckCollisionPointRec(mousePos, g_systemHotspots[6])) {
                ClearAllPlacementModes();
                g_selectedSystemHotspot = 6;
                g_trainColorIndex = 5;
                g_trainPlacementMode = true;
                AddTerminalMessage("YELLOW PASSENGER: Build cost 300 CR, running cost 80 CR/WK. Click a station on a matching established line to place.");
            } else if (CheckCollisionPointRec(mousePos, g_bottomHotspots[0])) {
                bool wasOn = IsTrackPlacementSelected();
                ClearAllPlacementModes();
                if (!wasOn) { g_trainPlacementMode = true; g_selectedBottomHotspot = 0; }
                AddTerminalMessage("PLATFORM/TRACK (T): 150 CREDITS. Click to start line, drag to extend/shrink, release to build.");
            } else if (CheckCollisionPointRec(mousePos, g_bottomHotspots[1])) {
                bool wasOn = g_stationPlacementMode;
                ClearAllPlacementModes();
                if (!wasOn) { g_stationPlacementMode = true; g_selectedBottomHotspot = 1; }
                AddTerminalMessage("STATION (S): 1000 CREDITS. R to rotate (4 directions). Must connect to track. Forms part of completed line when linked.");
            } else if (CheckCollisionPointRec(mousePos, g_bottomHotspots[2])) {
                bool wasOn = g_depotPlacementMode;
                ClearAllPlacementModes();
                if (!wasOn) { g_depotPlacementMode = true; g_selectedBottomHotspot = 2; }
                AddTerminalMessage("DEPOT (D): 1500 CREDITS. R to rotate. Stores materials for bureau construction; keep depot clusters within bureau outer-ring cargo reach.");
            } else if (CheckCollisionPointRec(mousePos, g_bottomHotspots[3])) {
                bool wasOn = g_factoryPlacementMode;
                ClearAllPlacementModes();
                if (!wasOn) { g_factoryPlacementMode = true; g_selectedBottomHotspot = 3; }
                AddTerminalMessage("FACTORY (F): 10000 CREDITS. R to rotate. Factories produce materials; pair with depots so stored cargo can be reached by bureau outer rings.");
            } else if (CheckCollisionPointRec(mousePos, g_bottomHotspots[4])) {
                if (!g_bureauPlacementMode) {
                    ClearAllPlacementModes();
                    g_bureauPlacementMode = true;
                    g_bureauFloorIndex = 0;
                    g_selectedBottomHotspot = 4;
                } else {
                    g_bureauFloorIndex = (g_bureauFloorIndex + 1) % (int)g_bureauFloorOptions.size();
                }
                int floors = g_bureauFloorOptions[g_bureauFloorIndex];
                int minCost = ApplyBuildDiscount(floors * GetBureauCostPerFloorForSystem((int)SiloSystem::SYS1_CARGO));
                int maxCost = ApplyBuildDiscount(floors * GetBureauCostPerFloorForSystem((int)SiloSystem::SYS7_YELLOW));
                char buf[256];
                int cargo = ApplyOrangeBureauDiscount(GetBureauCargoCost(g_bureauFloorIndex));
                snprintf(buf, sizeof(buf), "BUREAU (B): %d-%d CREDITS (%d floors, %d cargo). Cost/floor by line: Cargo/Neutral 3000, Green 3500, Magenta 4000, Orange 4500, Cyan 5000, Red 5500, Yellow 6000. Build rule: INNER ring must touch an established-line station tile; OUTER ring must have enough cargo. B cycles floors.", minCost, maxCost, floors, cargo);
                AddTerminalMessage(buf);
            } else if (CheckCollisionPointRec(mousePos, g_bottomHotspots[5])) {
                ClearAllPlacementModes();
                g_stockModal.open = true;
                g_stockModal.framesOpen = 0;
                g_stockModal.closeClicked = false;
                if (!g_marketUnlocked) {
                    AddTerminalMessage("Build a Corporate Executive Silo (Yellow) to unlock the Market.");
                }
            } else if (CheckCollisionPointRec(mousePos, g_viewfinderCutoutRect)) {
                bool wasOn = g_demolishMode;
                ClearAllPlacementModes();
                if (!wasOn) { g_demolishMode = true; }
                AddTerminalMessage("DEMOLISH (X): 100 CREDITS per removal. Click on platform, depot, station, or factory to remove.");
            }
        }
        
        // Handle mouse click to place platform, train, select train, configure junction, or demolish (disabled in map mode and when modal is open)
        // Also prevent building when cursor is visible (outside 3D viewport)
        if (!g_mapMode && !anyModalOpen && CustomIsMouseButtonPressed(MOUSE_BUTTON_LEFT) && !IsCursorVisible()) {
            bool clickHandled = false;
            
            // Demolish mode: remove anything at the clicked grid square
            if (g_demolishMode) {
                bool demolished = false;
                
                // Check for platforms/depots/stations at this position
                for (int i = (int)g_placedPlatforms.size() - 1; i >= 0; i--) {
                    float dist = Vector3Distance(g_mouseWorldPos, g_placedPlatforms[i].position);
                    if (dist < g_gridSpacing * 0.6f) {
                        PlacedPlatform& hit = g_placedPlatforms[i];
                        if (hit.isStation && !hit.isDepot) {
                            // Collect only the 4 tiles of this exact physical station.
                            std::vector<int> siblings = CollectPhysicalStationTileIndices(i, g_placedPlatforms, g_gridSpacing);
                            int anchorIdx = -1;
                            for (int j : siblings)
                                if (g_placedPlatforms[j].stationPart == 0) { anchorIdx = j; break; }
                            if (anchorIdx < 0 && !siblings.empty()) anchorIdx = siblings[0];
                            // Check if any sibling is on an established line
                            int lineIdx = -1;
                            for (int si : siblings) {
                                for (int li = 0; li < (int)g_lines.size(); li++) {
                                    if (g_lines[li].platformIndices.count(si)) {
                                        lineIdx = li;
                                        break;
                                    }
                                }
                                if (lineIdx >= 0) break;
                            }
                            // Filter siblings: only keep tiles on the target line or not on any line
                            if (lineIdx >= 0) {
                                std::vector<int> filtered;
                                for (int si : siblings) {
                                    bool onOtherLine = false;
                                    for (int li = 0; li < (int)g_lines.size(); li++) {
                                        if (li == lineIdx) continue;
                                        if (g_lines[li].platformIndices.count(si)) { onOtherLine = true; break; }
                                    }
                                    if (!onOtherLine) filtered.push_back(si);
                                }
                                siblings = filtered;
                                // Re-find anchor in filtered set
                                anchorIdx = -1;
                                for (int si : siblings)
                                    if (g_placedPlatforms[si].stationPart == 0) { anchorIdx = si; break; }
                                if (anchorIdx < 0 && !siblings.empty()) anchorIdx = siblings[0];
                            }
                            if (lineIdx >= 0) {
                                // Open confirm modal â€” do NOT demolish yet
                                g_demolishConfirmModal.open = true;
                                g_demolishConfirmModal.framesOpen = 0;
                                g_demolishConfirmModal.confirmClicked = false;
                                g_demolishConfirmModal.cancelClicked = false;
                                g_demolishConfirmModal.isStationDemolish = true;
                                g_demolishConfirmModal.anchorIdx = anchorIdx;
                                g_demolishConfirmModal.platformIdx = -1;
                                g_demolishConfirmModal.lineIdx = lineIdx;
                                strncpy(g_demolishConfirmModal.lineName, g_lines[lineIdx].name.c_str(), 127);
                                g_demolishConfirmModal.lineName[127] = '\0';
                                BuildDemolishSiloWarning(siblings, g_demolishConfirmModal.siloWarning, sizeof(g_demolishConfirmModal.siloWarning));
                                // Count trains on affected lines for modal warning
                                {
                                    std::set<int> affectedLineIds;
                                    for (int si : siblings)
                                        for (int li = 0; li < (int)g_lines.size(); li++)
                                            if (g_lines[li].platformIndices.count(si)) affectedLineIds.insert(g_lines[li].id);
                                    g_demolishConfirmModal.hasAffectedTrains = false;
                                    g_demolishConfirmModal.affectedTrainCount = 0;
                                    for (const auto& train : g_placedTrains) {
                                        if (affectedLineIds.count(train.lineId)) {
                                            g_demolishConfirmModal.hasAffectedTrains = true;
                                            g_demolishConfirmModal.affectedTrainCount++;
                                        }
                                    }
                                }
                                // demolished stays false â€” modal handles the removal
                            } else {
                                // No line: remove all 4 tiles immediately (descending order)
                                RemovePlatformsAndRemapState(siblings);
                                demolished = true;
                            }
                        } else {
                            // Non-station tile: check if it belongs to an established line
                            int lineIdx = -1;
                            for (int li = 0; li < (int)g_lines.size(); li++) {
                                if (g_lines[li].platformIndices.count(i)) { lineIdx = li; break; }
                            }
                            if (lineIdx >= 0) {
                                // On an established line â€” open confirm modal, revert line on confirm
                                g_demolishConfirmModal.open = true;
                                g_demolishConfirmModal.framesOpen = 0;
                                g_demolishConfirmModal.confirmClicked = false;
                                g_demolishConfirmModal.cancelClicked = false;
                                g_demolishConfirmModal.isStationDemolish = false;
                                g_demolishConfirmModal.anchorIdx = -1;
                                g_demolishConfirmModal.platformIdx = i;
                                g_demolishConfirmModal.lineIdx = lineIdx;
                                strncpy(g_demolishConfirmModal.lineName, g_lines[lineIdx].name.c_str(), 127);
                                g_demolishConfirmModal.lineName[127] = '\0';
                                std::vector<int> platVec = {i};
                                BuildDemolishSiloWarning(platVec, g_demolishConfirmModal.siloWarning, sizeof(g_demolishConfirmModal.siloWarning));
                                // Count trains on affected lines for modal warning
                                {
                                    std::set<int> affLineIds;
                                    for (int li = 0; li < (int)g_lines.size(); li++)
                                        if (g_lines[li].platformIndices.count(i)) affLineIds.insert(g_lines[li].id);
                                    g_demolishConfirmModal.hasAffectedTrains = false;
                                    g_demolishConfirmModal.affectedTrainCount = 0;
                                    for (const auto& train : g_placedTrains) {
                                        if (affLineIds.count(train.lineId)) {
                                            g_demolishConfirmModal.hasAffectedTrains = true;
                                            g_demolishConfirmModal.affectedTrainCount++;
                                        }
                                    }
                                }
                                // demolished stays false â€” modal handles the removal
                            } else {
                                // No established line â€” remove immediately
                                RemovePlatformsAndRemapState({ i });
                                demolished = true;
                            }
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
                                int removedLineId = g_placedTrains[i].lineId;
                                g_placedTrains.erase(g_placedTrains.begin() + i);
                                if (g_selectedTrainIndex == i) g_selectedTrainIndex = -1;
                                else if (g_selectedTrainIndex > i) g_selectedTrainIndex--;
                                if (removedLineId >= 0 && !HasAnyActiveTrainOnLine(removedLineId))
                                    RefreshAwaitingTrainLock();
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
                    AddTerminalMessage("OBJECT DEMOLISHED - 100 CREDITS");
                }
                
                clickHandled = true;
            }
            
            // Station click: open configuration modal for any station tile â€” highest priority after demolish
            // Blocked when placing trains (clicks should place the train, not open the modal)
            if (!clickHandled && !IsPassengerTrainPlacementSelected() && !g_cargoTrainPlacementMode) {
                for (int pi = 0; pi < (int)g_placedPlatforms.size(); pi++) {
                    const PlacedPlatform& plat = g_placedPlatforms[pi];
                    if (!plat.isStation || plat.isDepot) continue;
                    if (Vector3Distance(g_mouseWorldPos, plat.position) < g_gridSpacing * 0.6f) {
                        std::vector<int> stationTiles = CollectPhysicalStationTileIndices(pi, g_placedPlatforms, g_gridSpacing);
                        int anchorIdx = pi;
                        for (int si : stationTiles)
                            if (g_placedPlatforms[si].stationPart == 0) { anchorIdx = si; break; }
                        g_stationModal.open = true;
                        g_stationModal.framesOpen = 0;
                        g_stationModal.confirmClicked = false;
                        g_stationModal.cancelClicked  = false;
                        g_stationModal.anchorPlatformIndex = anchorIdx;
                        ClearCharInputQueue();
                        memcpy(g_stationModal.nameBuffer, g_placedPlatforms[anchorIdx].stationName, 64);
                        g_stationModal.nameCursorPos = (int)strlen(g_stationModal.nameBuffer);
                        g_stationModal.delayMode = g_placedPlatforms[anchorIdx].stationDelayMode;
                        g_stationModal.isNewBuild = false;
                        clickHandled = true;
                        break;
                    }
                }
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
                                if (g_placedTrains[i].isPaused) {
                                    // Paused train: open delete modal instead of selecting
                                    g_pausedTrainDeleteModal.open = true;
                                    g_pausedTrainDeleteModal.framesOpen = 0;
                                    g_pausedTrainDeleteModal.confirmClicked = false;
                                    g_pausedTrainDeleteModal.cancelClicked = false;
                                    g_pausedTrainDeleteModal.trainIndex = (int)i;
                                } else if (g_selectedTrainIndex == (int)i) {
                                    g_selectedTrainIndex = -1; // Deselect if clicking same train
                                    g_junctionSetupTrainId = -1;
                                    g_junctionSetupBadgeTimer = 0.0f;
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
            
            // If a train is selected, check if clicking the junction gate cross (or junction cell) to configure it.
            // Important: disable this while placing a new train so prior-train junction state never hijacks placement clicks.
            if (!clickHandled
                && !IsPassengerTrainPlacementSelected()
                && !g_cargoTrainPlacementMode
                && g_selectedTrainIndex >= 0
                && g_selectedTrainIndex < (int)g_placedTrains.size()) {
                Ray mouseRay = GetScreenToWorldRayEx(mousePos, g_camera, g_renderWidth, g_renderHeight);
                const PlacedPlatform* hitJunction = nullptr;
                // Prefer hit on the floating cross (click the gate shape)
                for (const auto& platform : g_placedPlatforms) {
                    PlatformType pType = GetPlatformType(platform.position, g_placedPlatforms, g_gridSpacing);
                    if (pType == PlatformType::Points && RayHitJunctionCross(mouseRay, platform.position, g_placedPlatforms, g_gridSpacing)) {
                        hitJunction = &platform;
                        break;
                    }
                }
                // Fallback: click on junction cell on the ground
                if (!hitJunction) {
                    for (const auto& platform : g_placedPlatforms) {
                        if (Vector3Distance(g_mouseWorldPos, platform.position) < g_gridSpacing * 0.6f) {
                            PlatformType pType = GetPlatformType(platform.position, g_placedPlatforms, g_gridSpacing);
                            if (pType == PlatformType::Points) {
                                hitJunction = &platform;
                                break;
                            }
                        }
                    }
                }
                if (hitJunction) {
                    int juncPi = -1;
                    for (int jpi = 0; jpi < (int)g_placedPlatforms.size(); jpi++) {
                        if (Vector3Distance(g_placedPlatforms[jpi].position, hitJunction->position) < 0.01f) {
                            juncPi = jpi; break;
                        }
                    }
                    int switchReason = 0;
                    int establishedAtJunction = 0;
                    if (IsJunctionSwitchable(juncPi, &switchReason, &establishedAtJunction)) {
                        std::vector<Vector3> adjacent = GetSortedAdjacentPositions(hitJunction->position, g_placedPlatforms, g_gridSpacing);
                        int numExits = (int)adjacent.size();
                        int numPairs = NumJunctionPairs(numExits);
                        if (numPairs <= 0) numPairs = 1;
                        int currentSetting = g_placedTrains[g_selectedTrainIndex].GetJunctionSetting(hitJunction->position.x, hitJunction->position.z, &adjacent);
                        int newSetting = (currentSetting + 1) % numPairs;
                        if (newSetting < 0) newSetting = 0;
                        g_placedTrains[g_selectedTrainIndex].SetJunctionSetting(hitJunction->position.x, hitJunction->position.z, newSetting, &adjacent);
                        PlacedTrain& train = g_placedTrains[g_selectedTrainIndex];
                        if (!train.path.empty()) {
                            (void)RebuildTrainPath(train, g_placedPlatforms, g_gridSpacing);
                        }
                        if (g_junctionSetupTrainId == train.id) {
                            g_junctionSetupTrainId = -1;
                            g_junctionSetupBadgeTimer = 0.0f;
                        }
                        clickHandled = true;
                    } else if (juncPi >= 0) {
                        DebugLogFormat("LINE_DEBUG: Junction switch blocked at (%.0f,%.0f) reason=%d establishedExits=%d",
                            g_placedPlatforms[juncPi].position.x, g_placedPlatforms[juncPi].position.z, switchReason, establishedAtJunction);
                    }
                }
            }

            // If NO train is selected, clicking a switchable junction opens the config modal
            if (!clickHandled
                && !IsPassengerTrainPlacementSelected()
                && !g_cargoTrainPlacementMode
                && !IsTrackPlacementSelected()
                && !g_stationPlacementMode
                && !g_depotPlacementMode
                && !g_demolishMode
                && g_selectedTrainIndex < 0) {
                Ray mouseRay = GetScreenToWorldRayEx(mousePos, g_camera, g_renderWidth, g_renderHeight);
                const PlacedPlatform* hitJunction = nullptr;
                for (const auto& platform : g_placedPlatforms) {
                    PlatformType pType = GetPlatformType(platform.position, g_placedPlatforms, g_gridSpacing);
                    if (pType == PlatformType::Points && RayHitJunctionCross(mouseRay, platform.position, g_placedPlatforms, g_gridSpacing)) {
                        hitJunction = &platform;
                        break;
                    }
                }
                if (!hitJunction) {
                    for (const auto& platform : g_placedPlatforms) {
                        if (Vector3Distance(g_mouseWorldPos, platform.position) < g_gridSpacing * 0.6f) {
                            PlatformType pType = GetPlatformType(platform.position, g_placedPlatforms, g_gridSpacing);
                            if (pType == PlatformType::Points) {
                                hitJunction = &platform;
                                break;
                            }
                        }
                    }
                }
                if (hitJunction) {
                    int juncPi = -1;
                    for (int jpi = 0; jpi < (int)g_placedPlatforms.size(); jpi++) {
                        if (Vector3Distance(g_placedPlatforms[jpi].position, hitJunction->position) < 0.01f) {
                            juncPi = jpi; break;
                        }
                    }
                    if (juncPi >= 0 && IsJunctionSwitchable(juncPi)) {
                        // Populate modal with trains that pass through this junction
                        g_junctionConfigModal = {};
                        g_junctionConfigModal.open = true;
                        g_junctionConfigModal.junctionPlatformIndex = juncPi;
                        g_junctionConfigModal.junctionPos = hitJunction->position;
                        // Find all non-paused trains whose line includes this junction
                        for (int ti = 0; ti < (int)g_placedTrains.size(); ti++) {
                            const PlacedTrain& train = g_placedTrains[ti];
                            if (train.isPaused || train.lineId < 0) continue;
                            for (const auto& line : g_lines) {
                                if (line.id == train.lineId && line.platformIndices.count(juncPi)) {
                                    g_junctionConfigModal.trainIndices.push_back(ti);
                                    break;
                                }
                            }
                        }
                        g_junctionConfigModalOpen = true;
                        clickHandled = true;
                    }
                }
            }

            if (!clickHandled && (IsTrackPlacementSelected() || IsPassengerTrainPlacementSelected() || g_cargoTrainPlacementMode)) {
                // Place passenger/cargo train when train mode is active, or start track drag when track mode is active.
                // Check if the platform under mouse is a station
                const PlacedPlatform* targetPlatform = nullptr;
                for (const auto& p : g_placedPlatforms) {
                    if (Vector3Distance(g_mouseWorldPos, p.position) < 0.1f) {
                        targetPlatform = &p;
                        break;
                    }
                }

                if ((IsPassengerTrainPlacementSelected() || g_cargoTrainPlacementMode) && targetPlatform && targetPlatform->isStation) {
                    // Check if there are at least 4 connected platforms
                    Vector3 pathCenter;
                    
                    if (CheckConnectedPlatforms(g_mouseWorldPos, g_placedPlatforms, g_gridSpacing, pathCenter)) {
                        // Get target line for path restriction (trains stick to their line at crossroads)
                        int targetPlatformIndex = -1;
                        for (int tpi = 0; tpi < (int)g_placedPlatforms.size(); tpi++) {
                            if (Vector3Distance(g_placedPlatforms[tpi].position, targetPlatform->position) < 0.1f) {
                                targetPlatformIndex = tpi;
                                break;
                            }
                        }
                        int targetLineIndex = GetLineIndexFromPlatformIndex(targetPlatformIndex);
                        const std::set<int>* lineFilter = nullptr;
                        if (targetLineIndex >= 0 && targetLineIndex < (int)g_lines.size())
                            lineFilter = &g_lines[targetLineIndex].platformIndices;
                        std::vector<Vector3> path = BuildPlatformPath(g_mouseWorldPos, g_placedPlatforms, g_gridSpacing, nullptr, lineFilter);
                        
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
                            newTrain.lineId = (targetLineIndex >= 0 && targetLineIndex < (int)g_lines.size())
                                ? g_lines[targetLineIndex].id
                                : -1;
                            if (g_cargoTrainPlacementMode) {
                                newTrain.type = PlacedTrain::TrainType::Cargo;
                            } else {
                                int idx = (g_trainColorIndex >= 0 && g_trainColorIndex <= 5) ? g_trainColorIndex : 0;
                                newTrain.type = (PlacedTrain::TrainType)((int)PlacedTrain::TrainType::Passenger + idx);
                                if (newTrain.type > PlacedTrain::TrainType::Yellow) newTrain.type = PlacedTrain::TrainType::Passenger;
                            }
                            if (!DoesEstablishedLineMatchTrainType(targetLineIndex, newTrain.type)) {
                                AddTerminalMessage("TRAIN PLACEMENT BLOCKED: Train type must match an established line system colour.");
                                clickHandled = true;
                            } else {
                                newTrain.cargoTrailers = g_cargoTrainPlacementMode ? g_cargoPlacementTrailers : 1;
                                int trainBuildCost = GetTrainBuildCost(newTrain.type, newTrain.cargoTrailers);
                                if (g_playerCredits < trainBuildCost) {
                                    char costBuf[128];
                                    snprintf(costBuf, sizeof(costBuf), "INSUFFICIENT CREDITS: Train build cost is %d CR.", trainBuildCost);
                                    AddTerminalMessage(costBuf);
                                    clickHandled = true;
                                }
                                if (!clickHandled) {
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
                                    float placeRadius = GetTrainTotalLength(newTrain, g_gridSpacing) * 0.5f;
                                    for (const auto& existingTrain : g_placedTrains) {
                                        float otherRadius = GetTrainTotalLength(existingTrain, g_gridSpacing) * 0.5f;
                                        if (Vector3Distance(newTrain.position, existingTrain.position) < (placeRadius + otherRadius)) {
                                            canPlace = false;
                                            break;
                                        }
                                    }
                                    
                                    if (canPlace) {
                                        g_playerCredits -= trainBuildCost;
                                        g_placedTrains.push_back(newTrain);
                                    DebugLogFormat("TRAIN_DEBUG: Placed train id=%d type=%d lineId=%d pathPoints=%d pathLen=%.1f spawnProgress=%.1f dir=%.0f pos=(%.0f,%.0f) targetLineIdx=%d",
                                        newTrain.id, (int)newTrain.type, newTrain.lineId, (int)newTrain.path.size(), newTrain.pathLength,
                                        newTrain.pathProgress, newTrain.direction, newTrain.position.x, newTrain.position.z, targetLineIndex);
                                    char trainCostMsg[128];
                                    snprintf(trainCostMsg, sizeof(trainCostMsg), "TRAIN BUILT - %d CREDITS.", trainBuildCost);
                                    AddTerminalMessage(trainCostMsg);
                                    if (g_sfxBuildTrain.frameCount > 0) PlaySound(g_sfxBuildTrain);
                                    // Unlock sys8-12 hotspots if this train satisfies the post-establish lock
                                    if (g_awaitingTrainForLineId >= 0 && newTrain.lineId == g_awaitingTrainForLineId)
                                        RefreshAwaitingTrainLock();
                                    // Deselect the train-to-build (equivalent to RMB), keeping the placed train selected below
                                    ClearAllPlacementModes();
                                    // Auto-select the newly placed train
                                    g_selectedTrainIndex = (int)g_placedTrains.size() - 1;
                                    g_junctionSetupTrainId = newTrain.id;
                                    g_junctionSetupBadgeTimer = 6.0f;
                                    // Prompt per-train junction setup (settings are train-specific, never inherited).
                                    int switchableJunctionsOnLine = 0;
                                    if (targetLineIndex >= 0 && targetLineIndex < (int)g_lines.size()) {
                                        for (int pi : g_lines[targetLineIndex].platformIndices) {
                                            if (pi < 0 || pi >= (int)g_placedPlatforms.size()) continue;
                                            PlatformType pType = GetPlatformType(g_placedPlatforms[pi].position, g_placedPlatforms, g_gridSpacing);
                                            if (pType != PlatformType::Points) continue;
                                            if (IsJunctionSwitchable(pi)) switchableJunctionsOnLine++;
                                        }
                                    }
                                    if (switchableJunctionsOnLine > 0) {
                                        char jbuf[256];
                                        snprintf(jbuf, sizeof(jbuf),
                                            "TRAIN %d PLACED: Configure %d junction(s) for THIS train by clicking their gate crosses.",
                                            newTrain.id, switchableJunctionsOnLine);
                                        AddTerminalMessage(jbuf);
                                    }
                                        clickHandled = true;
                                    }
                                }
                            }
                        }
                    }
                }
                // If we didn't place a train and we're in platform/track mode, start line placement (preview only until release)
                if (!clickHandled && IsTrackPlacementSelected()) {
                    bool canStart = true;
                    if (!IsWithinGridBounds(g_mouseWorldPos.x, g_mouseWorldPos.z, g_gridSpacing * 0.5f)) canStart = false;
                    Building testBuilding;
                    testBuilding.position = g_mouseWorldPos;
                    testBuilding.size = { g_gridSpacing, g_gridSpacing, g_gridSpacing };
                    if (overlapsWithAny(testBuilding, g_buildings)) canStart = false;
                    for (const auto& placed : g_placedPlatforms) {
                        float dist = Vector3Distance(g_mouseWorldPos, placed.position);
                        if (dist < g_gridSpacing * 0.9f) { canStart = false; break; }
                    }
                    int startCost = ApplyBuildDiscount(OuterGridCost(150, g_mouseWorldPos.x, g_mouseWorldPos.z));
                    if (canStart && g_playerCredits < startCost) canStart = false;
                    if (canStart) {
                        // Start drag: show preview line, place nothing until LMB release
                        g_platformDragActive = true;
                        g_platformDragStartPos = g_mouseWorldPos;
                        g_platformDragPlacedKeys.clear();  // Unused during preview; we place on release
                    }
                }
            } else if (!clickHandled && g_stationPlacementMode) {
                bool canPlace = true;
                std::vector<Vector3> segments;
                for (int i = 0; i < 4 && canPlace; i++) {
                    Vector3 pos = g_mouseWorldPos;
                    float offset = (i - 1.5f) * g_gridSpacing;
                    switch (g_placementOrientation) {
                        case 0: pos.x += offset; break;
                        case 1: pos.z += offset; break;
                        case 2: pos.x -= offset; break;
                        case 3: pos.z -= offset; break;
                        default: pos.x += offset; break;
                    }
                    segments.push_back(pos);

                    if (!IsWithinGridBounds(pos.x, pos.z, g_gridSpacing * 0.5f)) canPlace = false;

                    Building testBuilding;
                    testBuilding.position = pos;
                    testBuilding.size = { g_gridSpacing, g_gridSpacing, g_gridSpacing };
                    if (overlapsWithAny(testBuilding, g_buildings)) canPlace = false;

                    for (const auto& p : g_placedPlatforms) {
                        if (Vector3Distance(pos, p.position) < g_gridSpacing * 0.9f) canPlace = false;
                    }

                    // Block placement inside factory footprints (4x4 grid, half = 2 * gridSpacing)
                    const float factoryHalf = g_gridSpacing * 2.0f;
                    for (const auto& f : g_placedFactories) {
                        if (fabsf(pos.x - f.position.x) < factoryHalf &&
                            fabsf(pos.z - f.position.z) < factoryHalf) {
                            canPlace = false;
                            break;
                        }
                    }
                }

                // Check credits (Stations cost 1000 credits; 750 in outer grid; red bureau discount applies)
                int stationCost = ApplyBuildDiscount(OuterGridCost(1000, g_mouseWorldPos.x, g_mouseWorldPos.z));
                if (canPlace && g_playerCredits < stationCost) {
                    canPlace = false;
                }

                if (canPlace) {
                    g_playerCredits -= stationCost; // Deduct station cost
                    // If any part of the station is in a qualifying colored silo cluster, show silo-available message
                    ClusterType siloCluster = ClusterType::CARGO;
                    for (int i = 0; i < 4; i++) {
                        int sx = WorldToGridCell(segments[i].x);
                        int sz = WorldToGridCell(segments[i].z);
                        ClusterType ct = GetClusterTypeForStation(sx, sz);
                        if (ct != ClusterType::CARGO) { siloCluster = ct; break; }
                    }
                    // World-space fallback if grid didn't match (e.g. different grid init): check segment world position vs cluster buildings
                    if (siloCluster == ClusterType::CARGO) {
                        const float prox = g_gridSpacing * 1.5f;
                        for (int i = 0; i < 4 && siloCluster == ClusterType::CARGO; i++) {
                            float wx = segments[i].x, wz = segments[i].z;
                            if (IsNearClusterBuilding(wx, wz, ClusterType::ClusterYellow, prox)) siloCluster = ClusterType::ClusterYellow;
                            else if (IsNearClusterBuilding(wx, wz, ClusterType::ClusterRed, prox)) siloCluster = ClusterType::ClusterRed;
                            else if (IsNearClusterBuilding(wx, wz, ClusterType::ClusterOrange, prox)) siloCluster = ClusterType::ClusterOrange;
                            else if (IsNearClusterBuilding(wx, wz, ClusterType::ClusterCyan, prox)) siloCluster = ClusterType::ClusterCyan;
                            else if (IsNearClusterBuilding(wx, wz, ClusterType::ClusterMagenta, prox)) siloCluster = ClusterType::ClusterMagenta;
                            else if (IsNearClusterBuilding(wx, wz, ClusterType::ClusterGreen, prox)) siloCluster = ClusterType::ClusterGreen;
                        }
                    }
                    const char* siloName = GetSiloNameForClusterType(siloCluster);
                    if (!siloName) {
                        for (int i = 0; i < 4; i++) {
                            if (IsWorldPosInActivatedCargoCluster(segments[i].x, segments[i].z)) {
                                siloName = "MATERIALS SILO";
                                break;
                            }
                        }
                    }
                    if (siloName) {
                        char buf[256];
                        snprintf(buf, sizeof(buf),
                            "STATION BUILT - %d CREDITS. %s AVAILABLE - TRACK TO INNER CITY HUB, CONNECTING STATION, DEDICATED BUREAU AND TRAIN REQUIRED TO COMPLETE.",
                            stationCost, siloName);
                        AddTerminalMessage(buf);
                    } else {
                        char buf[64];
                        snprintf(buf, sizeof(buf), "STATION BUILT - %d CREDITS", stationCost);
                        AddTerminalMessage(buf);
                    }
                    if (g_sfxBuildSys.frameCount > 0) PlaySound(g_sfxBuildSys);
                    int firstNewStationIdx = (int)g_placedPlatforms.size();
                    for (int i = 0; i < 4; i++) {
                        PlacedPlatform p;
                        p.position = segments[i];
                        p.isStation = true;
                        p.placementOrientation = g_placementOrientation;
                        p.stationPart = i;
                        p.isDepot = false;
                        p.depotCargo = 0;
                        g_placedPlatforms.push_back(p);

                        // Spawn build particles for each station segment
                        SpawnBuildParticles(segments[i], g_stationColor, g_gridSpacing);
                    }

                    // Surgically lift neutralization guard for the newly-placed tiles only
                    for (int si = firstNewStationIdx; si < (int)g_placedPlatforms.size(); si++)
                        ClearPlacementProtectionForPlatform(g_placedPlatforms[si].position);
                    InvalidatePlatformCaches();

                    // Auto-extend established lines with new station platforms
                    {
                        std::vector<int> tempCompId;
                        std::vector<long long> tempCompKey;
                        std::vector<std::vector<int>> tempMembers;
                        BuildStationComponents(g_placedPlatforms, g_gridSpacing, tempCompId, tempCompKey, tempMembers);
                        for (int pi = firstNewStationIdx; pi < (int)g_placedPlatforms.size(); pi++) {
                            if (pi >= (int)tempCompId.size()) continue;
                            int cid = tempCompId[pi];
                            if (cid < 0) continue;
                            // Skip platforms still under demolish neutralization guard
                            long long piKey = MakePositionKey(g_placedPlatforms[pi].position.x,
                                                              g_placedPlatforms[pi].position.z);
                            if (g_demolishNeutralizedPlatformKeys.count(piKey)) continue;
                            for (auto& line : g_lines) {
                                bool lineOwnsComponent = false;
                                for (int existingPi : line.platformIndices) {
                                    if (existingPi < (int)tempCompId.size() && tempCompId[existingPi] == cid) {
                                        lineOwnsComponent = true;
                                        break;
                                    }
                                }
                                if (lineOwnsComponent) {
                                    line.platformIndices.insert(pi);
                                    break; // Only add to the first matching line
                                }
                            }
                        }
                    }

                    // Network expanded: rebuild existing train paths so they can use newly connected track
                    {
                        std::set<int> affectedLineIds;
                        for (const auto& line : g_lines) {
                            for (int pi = firstNewStationIdx; pi < (int)g_placedPlatforms.size(); pi++) {
                                if (line.platformIndices.count(pi)) {
                                    affectedLineIds.insert(line.id);
                                    break;
                                }
                            }
                        }
                        RebuildTrainsOnLines(affectedLineIds);
                    }
                    // Open station configuration modal immediately after build
                    {
                        int anchorIdx = -1;
                        for (int i = (int)g_placedPlatforms.size()-1; i >= 0; i--) {
                            if (g_placedPlatforms[i].isStation && g_placedPlatforms[i].stationPart == 0) { anchorIdx = i; break; }
                        }
                        if (anchorIdx >= 0) {
                            g_stationModal.open = true;
                            g_stationModal.framesOpen = 0;
                            g_stationModal.confirmClicked = false;
                            g_stationModal.cancelClicked  = false;
                            g_stationModal.anchorPlatformIndex = anchorIdx;
                            ClearCharInputQueue();
                            memset(g_stationModal.nameBuffer, 0, sizeof(g_stationModal.nameBuffer));
                            g_stationModal.nameCursorPos = 0;
                            g_stationModal.delayMode = 0;
                            g_stationModal.isNewBuild = true;
                        }
                    }
                }
            } else if (!clickHandled && g_depotPlacementMode) {
                // Place Materials-Depot
                bool canPlace = true;
                if (!IsWithinGridBounds(g_mouseWorldPos.x, g_mouseWorldPos.z, g_gridSpacing * 0.5f)) canPlace = false;

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

                // Check credits (Depots cost 1500 credits; 1125 in outer grid; red bureau discount applies)
                int depotCost = ApplyBuildDiscount(OuterGridCost(1500, g_mouseWorldPos.x, g_mouseWorldPos.z));
                if (canPlace && g_playerCredits < depotCost) {
                    canPlace = false;
                }

                if (canPlace) {
                    g_playerCredits -= depotCost; // Deduct depot cost
                    char depotMsg[64];
                    snprintf(depotMsg, sizeof(depotMsg), "DEPOT BUILT - %d CREDITS", depotCost);
                    AddTerminalMessage(depotMsg);
                    if (g_sfxBuildSys.frameCount > 0) PlaySound(g_sfxBuildSys);
                    PlacedPlatform depot;
                    depot.position = g_mouseWorldPos;
                    depot.isStation = false;
                    depot.placementOrientation = 0;
                    depot.stationPart = 0;
                    depot.isDepot = true;
                    depot.depotCargo = 0;
                    g_placedPlatforms.push_back(depot);
                    // Surgically lift neutralization guard for the newly-placed depot tile only
                    {
                        ClearPlacementProtectionForPlatform(depot.position);
                    }
                    InvalidatePlatformCaches();
                    
                    // Spawn build particles
                    Color depotColor = (Color){ 160, 160, 160, 220 };
                    SpawnBuildParticles(g_mouseWorldPos, depotColor, g_gridSpacing);
                }
            } else if (!clickHandled && g_factoryPlacementMode) {
                // Place Factory
                bool canPlace = true;
                if (!IsWithinGridBounds(g_mouseWorldPos.x, g_mouseWorldPos.z, g_gridSpacing * 2.0f)) canPlace = false;

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

                // Check credits (Factories cost 10,000 credits; 7,500 in outer grid; red bureau discount applies)
                int factoryCost = ApplyBuildDiscount(OuterGridCost(10000, factoryPos.x, factoryPos.z));
                if (canPlace && g_playerCredits < factoryCost) {
                    canPlace = false;
                }

                if (canPlace) {
                    g_playerCredits -= factoryCost; // Deduct factory cost
                    char factMsg[64];
                    snprintf(factMsg, sizeof(factMsg), "FACTORY BUILT - %d CREDITS.", factoryCost);
                    AddTerminalMessage(factMsg);
                    if (g_sfxFactoryBuilt.frameCount > 0) PlaySound(g_sfxFactoryBuilt);
                    g_pendingSfxActive = true;
                    g_pendingSfxTimer = 0.15f;
                    g_placedFactories.push_back({ factoryPos });
                    
                    // Spawn build particles
                    Color factoryColor = (Color){ 130, 130, 130, 220 };
                    SpawnBuildParticles(factoryPos, factoryColor, g_gridSpacing);
                }
            } else if (!clickHandled && g_bureauPlacementMode) {
                // Place Bureau
                bool canPlace = true;
                if (!IsWithinGridBounds(g_mouseWorldPos.x, g_mouseWorldPos.z, g_gridSpacing * 1.0f)) canPlace = false;
                Vector3 bureauPos = g_mouseWorldPos; // already snapped to grid intersection (2x2 footprint aligns with grid squares)
                int selectedFloors = g_bureauFloorOptions[g_bureauFloorIndex];

                // Bureau footprint is 1/4 factory size (2x2 tiles)
                float bureauHalf = g_gridSpacing * 1.0f; // 2x2 means half is 1 grid
                // No skyline building overlap check — bureaus can be placed next to clusters

                // Overlap with platforms/depots
                if (canPlace) {
                    for (const auto& p : g_placedPlatforms) {
                        if (p.position.x >= bureauPos.x - bureauHalf - 0.1f && p.position.x <= bureauPos.x + bureauHalf + 0.1f &&
                            p.position.z >= bureauPos.z - bureauHalf - 0.1f && p.position.z <= bureauPos.z + bureauHalf + 0.1f) {
                            canPlace = false;                            break;
                        }
                    }
                }

                // Overlap with factories
                if (canPlace) {
                    float factoryHalf = g_gridSpacing * 2.0f;
                    for (const auto& f : g_placedFactories) {
                        if (fabsf(f.position.x - bureauPos.x) <= (factoryHalf + bureauHalf) &&
                            fabsf(f.position.z - bureauPos.z) <= (factoryHalf + bureauHalf)) {
                            canPlace = false;                            break;
                        }
                    }
                }

                // Overlap with other bureaus
                if (canPlace) {
                    for (const auto& b : g_placedBureaus) {
                        if (fabsf(b.position.x - bureauPos.x) <= (bureauHalf * 2.0f) &&
                            fabsf(b.position.z - bureauPos.z) <= (bureauHalf * 2.0f)) {
                            canPlace = false;                            break;
                        }
                    }
                }

                // Blanket bureau rule: inner ring must touch at least one station tile on an established line.
                int detectedLineIndex = -1;
                if (canPlace) {
                    if (!DetectClosestEstablishedLineForBureauInnerRing(bureauPos, &detectedLineIndex)) { canPlace = false; }
                }

                int cargoCost = ApplyOrangeBureauDiscount(GetBureauCargoCost(g_bureauFloorIndex));
                if (canPlace && !HasEnoughCargoInRadius(bureauPos, g_placedPlatforms, g_gridSpacing, cargoCost)) {
                    canPlace = false;                }

                int costPerFloor = GetBureauCostPerFloorForLineIndex(detectedLineIndex);
                int totalCost = ApplyBuildDiscount(selectedFloors * costPerFloor);
                if (canPlace && g_playerCredits < totalCost) {
                    canPlace = false;                }
                if (canPlace) {
                    // Deduct credits and cargo
                    g_playerCredits -= totalCost;
                    RemoveCargoFromRadius(bureauPos, g_placedPlatforms, g_gridSpacing, cargoCost);
                    
                    PlacedBureau bureau;
                    bureau.position = bureauPos;
                    bureau.floors = selectedFloors;
                    char bureauMsg[128];
                    snprintf(bureauMsg, sizeof(bureauMsg), "BUREAU BUILT - %d CREDITS", totalCost);
                    AddTerminalMessage(bureauMsg);
                    if (g_sfxBureauBuilt.frameCount > 0) PlaySound(g_sfxBureauBuilt);
                    g_pendingSfxActive = true;
                    g_pendingSfxTimer = 0.15f;
                    g_placedBureaus.push_back(bureau);
                    
                    // Spawn build particles
                    Color bureauColor = (Color){ 0, 255, 255, 200 };
                    SpawnBuildParticles(bureauPos, bureauColor, g_gridSpacing);
                }
            }
        }
        
        // Map mode (M): click to select train, click junction to set route, click empty to deselect
        if (g_mapMode && g_lineModal.state == LineModalState::None && !g_stockModal.open && CustomIsMouseButtonPressed(MOUSE_BUTTON_LEFT)) {
            bool mapClickHandled = false;
            Vector2 mapClick = WorldToMap(g_mouseWorldPos);
            
            // Hit-test trains on map (triangle in map space)
            if (!mapClickHandled) {
                for (size_t i = 0; i < g_placedTrains.size(); i++) {
                    const PlacedTrain& train = g_placedTrains[i];
                    if (train.path.size() < 2) continue;
                    PathPoint center = GetPathPoint(train.path, train.pathProgress);
                    Vector2 p = WorldToMap(center.position);
                    Vector2 f = WorldDirToMap(center.direction);
                    float fl = sqrtf(f.x*f.x + f.y*f.y);
                    if (fl < 0.0001f) f = { 1.0f, 0.0f };
                    else { f.x /= fl; f.y /= fl; }
                    Vector2 r = { -f.y, f.x };
                    const float trainScale = 0.8f;
                    float tipLen = g_gridSpacing * 0.60f * trainScale;
                    float backLen = g_gridSpacing * 0.45f * trainScale;
                    float halfW = g_gridSpacing * 0.25f * trainScale;
                    Vector2 tip   = { p.x + f.x * tipLen,              p.y + f.y * tipLen };
                    Vector2 baseC = { p.x - f.x * backLen,             p.y - f.y * backLen };
                    Vector2 b1    = { baseC.x + r.x * halfW,           baseC.y + r.y * halfW };
                    Vector2 b2    = { baseC.x - r.x * halfW,           baseC.y - r.y * halfW };
                    if (CheckCollisionPointTriangle(mapClick, tip, b1, b2)) {
                        if (g_placedTrains[i].isPaused) {
                            // Paused train: open delete modal instead of selecting
                            g_pausedTrainDeleteModal.open = true;
                            g_pausedTrainDeleteModal.framesOpen = 0;
                            g_pausedTrainDeleteModal.confirmClicked = false;
                            g_pausedTrainDeleteModal.cancelClicked = false;
                            g_pausedTrainDeleteModal.trainIndex = (int)i;
                        } else if (g_selectedTrainIndex == (int)i) {
                            g_selectedTrainIndex = -1;
                        } else {
                            g_selectedTrainIndex = (int)i;
                        }
                        mapClickHandled = true;
                        break;
                    }
                }
            }
            
            // If train selected: click on junction to cycle its route for that train
            if (!mapClickHandled && g_selectedTrainIndex >= 0 && g_selectedTrainIndex < (int)g_placedTrains.size()) {
                for (int pi = 0; pi < (int)g_placedPlatforms.size(); pi++) {
                    const auto& platform = g_placedPlatforms[pi];
                    if (Vector3Distance(g_mouseWorldPos, platform.position) < g_gridSpacing * 0.6f) {
                        PlatformType pType = GetPlatformType(platform.position, g_placedPlatforms, g_gridSpacing);
                        int switchReason = 0;
                        int establishedAtJunction = 0;
                        bool canSwitch = (pType == PlatformType::Points) && IsJunctionSwitchable(pi, &switchReason, &establishedAtJunction);
                        if (canSwitch) {
                            std::vector<Vector3> adjacent = GetSortedAdjacentPositions(platform.position, g_placedPlatforms, g_gridSpacing);
                            int numExits = (int)adjacent.size();
                            int numPairs = NumJunctionPairs(numExits);
                            if (numPairs <= 0) numPairs = 1;
                            int currentSetting = g_placedTrains[g_selectedTrainIndex].GetJunctionSetting(platform.position.x, platform.position.z, &adjacent);
                            int newSetting = (currentSetting + 1) % numPairs;
                            if (newSetting < 0) newSetting = 0;
                            g_placedTrains[g_selectedTrainIndex].SetJunctionSetting(platform.position.x, platform.position.z, newSetting, &adjacent);
                            PlacedTrain& train = g_placedTrains[g_selectedTrainIndex];
                            if (!train.path.empty()) {
                                (void)RebuildTrainPath(train, g_placedPlatforms, g_gridSpacing);
                            }
                            mapClickHandled = true;
                            break;
                        } else if (pType == PlatformType::Points) {
                            DebugLogFormat("LINE_DEBUG: Map junction switch blocked at (%.0f,%.0f) reason=%d establishedExits=%d",
                                platform.position.x, platform.position.z, switchReason, establishedAtJunction);
                        }
                    }
                }
            }
            
            // No train selected: clicking a switchable junction in map mode opens the config modal
            if (!mapClickHandled && g_selectedTrainIndex < 0
                && !g_demolishMode && !IsTrackPlacementSelected()
                && !IsPassengerTrainPlacementSelected() && !g_cargoTrainPlacementMode) {
                for (int pi = 0; pi < (int)g_placedPlatforms.size(); pi++) {
                    const auto& platform = g_placedPlatforms[pi];
                    if (Vector3Distance(g_mouseWorldPos, platform.position) < g_gridSpacing * 0.6f) {
                        PlatformType pType = GetPlatformType(platform.position, g_placedPlatforms, g_gridSpacing);
                        if (pType == PlatformType::Points && IsJunctionSwitchable(pi)) {
                            g_junctionConfigModal = {};
                            g_junctionConfigModal.open = true;
                            g_junctionConfigModal.junctionPlatformIndex = pi;
                            g_junctionConfigModal.junctionPos = platform.position;
                            for (int ti = 0; ti < (int)g_placedTrains.size(); ti++) {
                                const PlacedTrain& train = g_placedTrains[ti];
                                if (train.isPaused || train.lineId < 0) continue;
                                for (const auto& line : g_lines) {
                                    if (line.id == train.lineId && line.platformIndices.count(pi)) {
                                        g_junctionConfigModal.trainIndices.push_back(ti);
                                        break;
                                    }
                                }
                            }
                            g_junctionConfigModalOpen = true;
                            mapClickHandled = true;
                            break;
                        }
                    }
                }
            }

            // Neutral-click on a station tile in map mode: open station configuration modal
            // Blocked when placing trains (clicks should place the train, not open the modal)
            if (!mapClickHandled && !g_demolishMode && !IsPassengerTrainPlacementSelected() && !g_cargoTrainPlacementMode) {
                for (int pi = 0; pi < (int)g_placedPlatforms.size(); pi++) {
                    const PlacedPlatform& plat = g_placedPlatforms[pi];
                    if (!plat.isStation) continue;
                    if (Vector3Distance(g_mouseWorldPos, plat.position) < g_gridSpacing * 0.6f) {
                        std::vector<int> stationTiles = CollectPhysicalStationTileIndices(pi, g_placedPlatforms, g_gridSpacing);
                        int anchorIdx = pi;
                        for (int si : stationTiles)
                            if (g_placedPlatforms[si].stationPart == 0) { anchorIdx = si; break; }
                        g_stationModal.open = true;
                        g_stationModal.framesOpen = 0;
                        g_stationModal.confirmClicked = false;
                        g_stationModal.cancelClicked  = false;
                        g_stationModal.anchorPlatformIndex = anchorIdx;
                        ClearCharInputQueue();
                        memcpy(g_stationModal.nameBuffer, g_placedPlatforms[anchorIdx].stationName, 64);
                        g_stationModal.nameCursorPos = (int)strlen(g_stationModal.nameBuffer);
                        g_stationModal.delayMode = g_placedPlatforms[anchorIdx].stationDelayMode;
                        g_stationModal.isNewBuild = false;
                        mapClickHandled = true;
                        break;
                    }
                }
            }

            // Click on empty map: deselect train
            if (!mapClickHandled && g_selectedTrainIndex >= 0) {
                bool onPlatform = false;
                for (const auto& platform : g_placedPlatforms) {
                    if (Vector3Distance(g_mouseWorldPos, platform.position) < g_gridSpacing * 0.6f) {
                        onPlatform = true;
                        break;
                    }
                }
                if (!onPlatform) {
                    g_selectedTrainIndex = -1;
                }
            }
        }
        
        // Platform drag-to-place: continue placing track along line while mouse is held (runs every frame)
        if (!g_mapMode && g_lineModal.state == LineModalState::None && !g_junctionModal.open && !g_stockModal.open && !IsCursorVisible()) {
            if (CustomIsMouseButtonReleased(MOUSE_BUTTON_LEFT) && g_platformDragActive && IsTrackPlacementSelected()) {
                // LMB released: build track along the preview line. If any cell crosses existing track (same cell), show junction modal.
                std::vector<Vector3> lineCells;
                { Vector3 cf = { g_camera.target.x - g_camera.position.x, 0.0f, g_camera.target.z - g_camera.position.z };
                  float cl = sqrtf(cf.x*cf.x + cf.z*cf.z); if (cl > 0.001f) { cf.x /= cl; cf.z /= cl; }
                  GetGridCellsLShape(g_platformDragStartPos, g_mouseWorldPos, g_gridSpacing, cf, lineCells); }
                bool wouldCreateJunction = false;
                for (const Vector3& pos : lineCells) {
                    if (FindPlatformIndexAtPos(pos, g_placedPlatforms) >= 0) { wouldCreateJunction = true; break; }
                }
                if (wouldCreateJunction) {
                    g_junctionModal.pendingStartPos = g_platformDragStartPos;
                    g_junctionModal.pendingEndPos = g_mouseWorldPos;
                    g_junctionModal.open = true;
                    g_junctionModalOpen = true;
                    g_junctionModal.framesOpen = 0;
                    g_junctionModal.buildJunctionClicked = false;
                    g_junctionModal.doNotBuildClicked = false;
                    g_platformDragActive = false;
                    g_liveCostPreview[0] = '\0';
                } else {
                    int groupId = g_nextPlacementGroupId++;
                    int placedCount = 0;
                    int totalSpent = 0;
                    int firstNewPlatformIdx = (int)g_placedPlatforms.size();
                    for (const Vector3& pos : lineCells) {
                        bool canPlace = true;
                        if (!IsWithinGridBounds(pos.x, pos.z, g_gridSpacing * 0.5f)) canPlace = false;
                        Building testBuilding;
                        testBuilding.position = pos;
                        testBuilding.size = { g_gridSpacing, g_gridSpacing, g_gridSpacing };
                        if (overlapsWithAny(testBuilding, g_buildings)) canPlace = false;
                        for (const auto& placed : g_placedPlatforms) {
                            if (Vector3Distance(pos, placed.position) < g_gridSpacing * 0.9f) { canPlace = false; break; }
                        }
                        int segCost = ApplyBuildDiscount(OuterGridCost(150, pos.x, pos.z));
                        if (canPlace && g_playerCredits < segCost) canPlace = false;
                        if (canPlace) {
                            g_playerCredits -= segCost;
                            totalSpent += segCost;
                            PlacedPlatform newPlatform;
                            newPlatform.position = pos;
                            newPlatform.isStation = false;
                            newPlatform.placementOrientation = 0;
                            newPlatform.stationPart = 0;
                            newPlatform.isDepot = false;
                            newPlatform.depotCargo = 0;
                            newPlatform.placementGroupId = groupId;
                            newPlatform.isJunction = false;
                            g_placedPlatforms.push_back(newPlatform);
                            // Surgically lift neutralization guard for this tile only
                            {
                                ClearPlacementProtectionForPlatform(pos);
                            }
                            InvalidatePlatformCaches();
                            SpawnBuildParticles(pos, g_platformColor, g_gridSpacing);
                            placedCount++;
                        }
                    }
                    if (placedCount > 0) {
                        // Auto-extend established lines: if new track connects to an
                        // existing line's component, add the new platforms to that line.
                        {
                            std::vector<int> tempCompId;
                            std::vector<long long> tempCompKey;
                            std::vector<std::vector<int>> tempMembers;
                            BuildStationComponents(g_placedPlatforms, g_gridSpacing, tempCompId, tempCompKey, tempMembers);

                            for (int pi = firstNewPlatformIdx; pi < (int)g_placedPlatforms.size(); pi++) {
                                if (pi >= (int)tempCompId.size()) continue;
                                int cid = tempCompId[pi];
                                if (cid < 0) continue;
                                // Skip platforms still under demolish neutralization guard
                                long long piKey = MakePositionKey(g_placedPlatforms[pi].position.x,
                                                                  g_placedPlatforms[pi].position.z);
                                if (g_demolishNeutralizedPlatformKeys.count(piKey)) continue;
                                // Find which established line owns platforms in this component
                                for (auto& line : g_lines) {
                                    bool lineOwnsComponent = false;
                                    for (int existingPi : line.platformIndices) {
                                        if (existingPi < (int)tempCompId.size() && tempCompId[existingPi] == cid) {
                                            lineOwnsComponent = true;
                                            break;
                                        }
                                    }
                                    if (lineOwnsComponent) {
                                        line.platformIndices.insert(pi);
                                        break; // Only add to the first matching line
                                    }
                                }
                            }
                        }

                        {
                            std::set<int> affectedLineIds;
                            for (const auto& line : g_lines) {
                                for (int pi = firstNewPlatformIdx; pi < (int)g_placedPlatforms.size(); pi++) {
                                    if (line.platformIndices.count(pi)) {
                                        affectedLineIds.insert(line.id);
                                        break;
                                    }
                                }
                            }
                            RebuildTrainsOnLines(affectedLineIds);
                        }
                        char buf[128];
                        snprintf(buf, sizeof(buf), "PLATFORM LINE BUILT - %d CREDITS", totalSpent);
                        AddTerminalMessage(buf);
                        if (g_sfxBuildSys.frameCount > 0) PlaySound(g_sfxBuildSys);
                    }
                    g_platformDragActive = false;
                    g_liveCostPreview[0] = '\0';
                }
            } else if (CustomIsMouseButtonReleased(MOUSE_BUTTON_LEFT)) {
                g_platformDragActive = false;
                g_liveCostPreview[0] = '\0';
            }
            if (g_platformDragActive && IsTrackPlacementSelected() && CustomIsMouseButtonDown(MOUSE_BUTTON_LEFT) && g_mouseInEffective3DArea) {
                // Preview only: update cost display, no placement
                std::vector<Vector3> lineCells;
                { Vector3 cf = { g_camera.target.x - g_camera.position.x, 0.0f, g_camera.target.z - g_camera.position.z };
                  float cl = sqrtf(cf.x*cf.x + cf.z*cf.z); if (cl > 0.001f) { cf.x /= cl; cf.z /= cl; }
                  GetGridCellsLShape(g_platformDragStartPos, g_mouseWorldPos, g_gridSpacing, cf, lineCells); }
                int potentialCount = 0;
                int creditsRemaining = g_playerCredits;
                int totalCostPreview = 0;
                for (const Vector3& pos : lineCells) {
                    bool canPlace = true;
                    if (!IsWithinGridBounds(pos.x, pos.z, g_gridSpacing * 0.5f)) canPlace = false;
                    Building testBuilding;
                    testBuilding.position = pos;
                    testBuilding.size = { g_gridSpacing, g_gridSpacing, g_gridSpacing };
                    if (overlapsWithAny(testBuilding, g_buildings)) canPlace = false;
                    for (const auto& placed : g_placedPlatforms) {
                        if (Vector3Distance(pos, placed.position) < g_gridSpacing * 0.9f) { canPlace = false; break; }
                    }
                    int segCost = ApplyBuildDiscount(OuterGridCost(150, pos.x, pos.z));
                    if (canPlace && creditsRemaining < segCost) canPlace = false;
                    if (canPlace) { potentialCount++; creditsRemaining -= segCost; totalCostPreview += segCost; }
                }
                snprintf(g_liveCostPreview, sizeof(g_liveCostPreview), "New extended network line cost: %d", totalCostPreview);
            }
        }
        
        // Intro zoom animation: smooth pull-in from 700 → 200 on first modal close
        if (g_zoomIntroActive) {
            float dist = Vector3Distance(g_camera.position, g_camera.target);
            const float kTargetDist = 200.0f;
            float newDist = dist - (dist - kTargetDist) * 2.5f * deltaTime;
            if (newDist <= kTargetDist + 0.5f) {
                newDist = kTargetDist;
                g_zoomIntroActive = false;
            }
            Vector3 dir = Vector3Normalize(Vector3Subtract(g_camera.position, g_camera.target));
            g_camera.position = Vector3Add(g_camera.target, Vector3Scale(dir, newDist));
            g_cameraAltitude  = g_camera.position.y;
            g_cameraRadius    = sqrtf((g_camera.position.x - g_camera.target.x) * (g_camera.position.x - g_camera.target.x) +
                                      (g_camera.position.z - g_camera.target.z) * (g_camera.position.z - g_camera.target.z));
        }

        // CyberTrain follow-cam: lock camera behind the front of the silo's train
        if (g_cyberTrainCamActive) {
            const PlacedTrain* camTrain = nullptr;
            for (const auto& t : g_placedTrains) {
                if (t.id == g_cyberTrainCamTrainId) { camTrain = &t; break; }
            }
            if (!camTrain || (int)camTrain->path.size() < 2) {
                ExitCyberTrainCam();
            } else {
                PathPoint fp = GetTrainHotspotPoint(*camTrain, g_gridSpacing);
                // Reflect path direction by actual movement direction so the cam always looks forward
                float d = (camTrain->direction >= 0.0f) ? 1.0f : -1.0f;
                Vector3 travelDir = { fp.direction.x * d, 0.0f, fp.direction.z * d };
                float tLen = sqrtf(travelDir.x * travelDir.x + travelDir.z * travelDir.z);
                if (tLen > 0.001f) { travelDir.x /= tLen; travelDir.z /= tLen; }
                g_camera.position = {
                    fp.position.x - travelDir.x * 9.0f,
                    fp.position.y  + 3.5f,
                    fp.position.z - travelDir.z * 9.0f
                };
                g_camera.target = {
                    fp.position.x + travelDir.x * 12.0f,
                    fp.position.y,
                    fp.position.z + travelDir.z * 12.0f
                };
                g_cameraAltitude = g_camera.position.y;
                g_cameraRadius   = sqrtf(
                    (g_camera.position.x - g_camera.target.x) * (g_camera.position.x - g_camera.target.x) +
                    (g_camera.position.z - g_camera.target.z) * (g_camera.position.z - g_camera.target.z));
            }
        }

        // Camera controls (isometric - rotation) (disabled in map mode)
        // Calculate forward and right vectors for movement
        Vector3 forward = Vector3Normalize(Vector3Subtract(g_camera.target, g_camera.position));
        Vector3 right = Vector3Normalize(Vector3CrossProduct(forward, g_camera.up));
        
        // Zoom in/out with Ctrl+Shift+/- keys (adjust distance from target) (disabled when modal is open)
        bool ctrlHeld = CustomIsKeyDown(KEY_LEFT_CONTROL) || CustomIsKeyDown(KEY_RIGHT_CONTROL);
        bool shiftHeld = CustomIsKeyDown(KEY_LEFT_SHIFT) || CustomIsKeyDown(KEY_RIGHT_SHIFT);
        const bool cameraInputAllowed = (!g_mapMode && !anyModalOpen);
        const bool zoomKeysDown = (CustomIsKeyDown(KEY_EQUAL) || CustomIsKeyDown(KEY_MINUS));
        const bool lrKeysDown = (CustomIsKeyDown(KEY_LEFT) || CustomIsKeyDown(KEY_RIGHT));
        const bool udKeysDown = (CustomIsKeyDown(KEY_UP) || CustomIsKeyDown(KEY_DOWN));
        const char* reqZoom = "NONE";
        const char* reqLR = "NONE";
        const char* reqUD = "NONE";
        if (ctrlHeld && shiftHeld && zoomKeysDown) {
            reqZoom = CustomIsKeyDown(KEY_MINUS) ? "ZOOM_IN" : "ZOOM_OUT";
        }
        if (lrKeysDown) {
            if (shiftHeld) reqLR = CustomIsKeyDown(KEY_LEFT) ? "ROTATE_LEFT" : "ROTATE_RIGHT";
            else           reqLR = CustomIsKeyDown(KEY_LEFT) ? "PAN_LEFT"    : "PAN_RIGHT";
        }
        if (udKeysDown) {
            if (shiftHeld) reqUD = CustomIsKeyDown(KEY_UP) ? "ALT_UP" : "ALT_DOWN";
            else           reqUD = CustomIsKeyDown(KEY_UP) ? "PAN_FORWARD" : "PAN_BACK";
        }
        if (g_cameraDebugOverlay &&
            (CustomIsKeyPressed(KEY_LEFT) || CustomIsKeyPressed(KEY_RIGHT) || CustomIsKeyPressed(KEY_UP) || CustomIsKeyPressed(KEY_DOWN))) {
            DebugLogFormat("CAMDBG keypress map=%d modal=%d camAllowed=%d follow=%d ctrl=%d shift=%d reqZoom=%s reqLR=%s reqUD=%s pos=(%.2f,%.2f,%.2f) target=(%.2f,%.2f,%.2f) yaw=%.3f radius=%.3f",
                g_mapMode ? 1 : 0, anyModalOpen ? 1 : 0, cameraInputAllowed ? 1 : 0, g_cyberTrainCamActive ? 1 : 0, ctrlHeld ? 1 : 0, shiftHeld ? 1 : 0,
                reqZoom, reqLR, reqUD,
                g_camera.position.x, g_camera.position.y, g_camera.position.z,
                g_camera.target.x, g_camera.target.y, g_camera.target.z, g_cameraYaw, g_cameraRadius);
        }
        if (!g_mapMode && !anyModalOpen && ctrlHeld && shiftHeld &&
            (CustomIsKeyDown(KEY_EQUAL) || CustomIsKeyDown(KEY_MINUS))) {
            float zoomDirection = CustomIsKeyDown(KEY_MINUS) ? -1.0f : 1.0f; // - zooms in (closer), + zooms out (farther)
            Vector3 zoomVector = Vector3Scale(forward, g_zoomSpeed * zoomDirection);
            g_camera.position = Vector3Add(g_camera.position, zoomVector);
            // Maintain fixed altitude after zoom
            g_camera.position.y = g_cameraAltitude;
            // Recalculate camera radius after zoom
            g_cameraRadius = sqrtf((g_camera.position.x - g_camera.target.x) * (g_camera.position.x - g_camera.target.x) +
                                   (g_camera.position.z - g_camera.target.z) * (g_camera.position.z - g_camera.target.z));
            g_camDbgControlMode = 5;
            g_camDbgStep = g_zoomSpeed * zoomDirection;
            g_camDbgMoveVector = zoomVector;
        }
        
        // Move left/right with Left/Right arrows (disabled when modal is open)
        if (!g_mapMode && !anyModalOpen && (CustomIsKeyDown(KEY_LEFT) || CustomIsKeyDown(KEY_RIGHT))) {
            bool shift = CustomIsKeyDown(KEY_LEFT_SHIFT) || CustomIsKeyDown(KEY_RIGHT_SHIFT);
            if (shift) {
                // Orbit-rotate around the target (not affected by game speed)
                float dir = CustomIsKeyDown(KEY_LEFT) ? -1.0f : 1.0f;
                g_cameraYaw += dir * g_rotateSpeed * deltaTime;
                g_camera.position.x = g_camera.target.x + sinf(g_cameraYaw) * g_cameraRadius;
                g_camera.position.z = g_camera.target.z + cosf(g_cameraYaw) * g_cameraRadius;
                g_camera.position.y = g_cameraAltitude;
                g_camDbgControlMode = 2;
                g_camDbgStep = dir * g_rotateSpeed * deltaTime;
            } else {
                // Pan left/right
                float moveDirection = CustomIsKeyDown(KEY_LEFT) ? -1.0f : 1.0f;
                // Normalize pan speed to ~60 FPS baseline to avoid frame-rate-dependent camera jumps.
                float panStep = g_moveSpeed * moveDirection * (deltaTime * 60.0f);
                Vector3 moveVector = Vector3Scale(right, panStep);
                
                // Move both camera position and target together (panning)
                g_camera.position = Vector3Add(g_camera.position, moveVector);
                g_camera.target = Vector3Add(g_camera.target, moveVector);

                // Keep orbit parameters consistent after pan
                g_cameraYaw = atan2f(g_camera.position.x - g_camera.target.x, g_camera.position.z - g_camera.target.z);
                g_cameraRadius = sqrtf((g_camera.position.x - g_camera.target.x) * (g_camera.position.x - g_camera.target.x) +
                                     (g_camera.position.z - g_camera.target.z) * (g_camera.position.z - g_camera.target.z));
                g_camDbgControlMode = 1;
                g_camDbgStep = panStep;
                g_camDbgMoveVector = moveVector;
            }
        }
        
        // Move forward/backward with Up/Down arrows at fixed altitude (disabled when modal is open)
        // Shift+Up/Down instead adjusts camera altitude (zoom closer/farther from the grid).
        if (!g_mapMode && !anyModalOpen && (CustomIsKeyDown(KEY_UP) || CustomIsKeyDown(KEY_DOWN))) {
            bool shift = CustomIsKeyDown(KEY_LEFT_SHIFT) || CustomIsKeyDown(KEY_RIGHT_SHIFT);
            if (shift) {
                // Shift+Up: lower altitude (closer to grid). Shift+Down: raise altitude (farther from grid).
                float altDir = CustomIsKeyDown(KEY_UP) ? -1.0f : 1.0f;
                g_cameraAltitude += altDir * g_zoomSpeed * 2.0f;
                g_cameraAltitude = Clamp(g_cameraAltitude, 5.0f, 400.0f);
                g_camera.position.y = g_cameraAltitude;
                g_camDbgControlMode = 4;
                g_camDbgStep = altDir * g_zoomSpeed * 2.0f;
            } else {
                // Project forward vector onto XZ plane (remove Y component) for horizontal movement
                Vector3 forwardXZ = { forward.x, 0.0f, forward.z };
                float forwardXZLength = Vector3Length(forwardXZ);
                if (forwardXZLength > 0.0001f) {
                    forwardXZ = Vector3Scale(forwardXZ, 1.0f / forwardXZLength); // Normalize
                }

                // Move forward or backward
                float moveDirection = CustomIsKeyDown(KEY_UP) ? 1.0f : -1.0f;
                float panStep = g_moveSpeed * moveDirection * (deltaTime * 60.0f);
                Vector3 moveVector = Vector3Scale(forwardXZ, panStep);

                // Move both camera position and target together, but maintain fixed altitude
                g_camera.position = Vector3Add(g_camera.position, moveVector);
                g_camera.position.y = g_cameraAltitude; // Maintain fixed altitude
                g_camera.target = Vector3Add(g_camera.target, moveVector);

                // Keep orbit parameters consistent after pan
                g_cameraYaw = atan2f(g_camera.position.x - g_camera.target.x, g_camera.position.z - g_camera.target.z);
                g_cameraRadius = sqrtf((g_camera.position.x - g_camera.target.x) * (g_camera.position.x - g_camera.target.x) +
                                     (g_camera.position.z - g_camera.target.z) * (g_camera.position.z - g_camera.target.z));
                g_camDbgControlMode = 3;
                g_camDbgStep = panStep;
                g_camDbgMoveVector = moveVector;
            }
        }
        if (g_cameraDebugOverlay &&
            (CustomIsKeyDown(KEY_LEFT) || CustomIsKeyDown(KEY_RIGHT) || CustomIsKeyDown(KEY_UP) || CustomIsKeyDown(KEY_DOWN))) {
            g_camDbgLogCounter++;
            if ((g_camDbgLogCounter % 4) == 0) {
                int leftDown = CustomIsKeyDown(KEY_LEFT) ? 1 : 0;
                int rightDown = CustomIsKeyDown(KEY_RIGHT) ? 1 : 0;
                int upDown = CustomIsKeyDown(KEY_UP) ? 1 : 0;
                int downDown = CustomIsKeyDown(KEY_DOWN) ? 1 : 0;
                int shiftDown = (CustomIsKeyDown(KEY_LEFT_SHIFT) || CustomIsKeyDown(KEY_RIGHT_SHIFT)) ? 1 : 0;
                int ctrlDown = (CustomIsKeyDown(KEY_LEFT_CONTROL) || CustomIsKeyDown(KEY_RIGHT_CONTROL)) ? 1 : 0;
                DebugLogFormat(
                    "CAMDBG frame mode=%d map=%d modal=%d camAllowed=%d follow=%d reqZoom=%s reqLR=%s reqUD=%s keys(LRUD=%d%d%d%d shift=%d ctrl=%d) step=%.5f move=(%.5f,%.5f,%.5f) pos=(%.4f,%.4f,%.4f) target=(%.4f,%.4f,%.4f) yaw=%.6f radius=%.6f alt=%.6f dt=%.6f forward=(%.4f,%.4f,%.4f) right=(%.4f,%.4f,%.4f)",
                    g_camDbgControlMode, g_mapMode ? 1 : 0, anyModalOpen ? 1 : 0, cameraInputAllowed ? 1 : 0, g_cyberTrainCamActive ? 1 : 0, reqZoom, reqLR, reqUD,
                    leftDown, rightDown, upDown, downDown, shiftDown, ctrlDown,
                    g_camDbgStep, g_camDbgMoveVector.x, g_camDbgMoveVector.y, g_camDbgMoveVector.z,
                    g_camera.position.x, g_camera.position.y, g_camera.position.z,
                    g_camera.target.x, g_camera.target.y, g_camera.target.z,
                    g_cameraYaw, g_cameraRadius, g_cameraAltitude, deltaTime,
                    forward.x, forward.y, forward.z, right.x, right.y, right.z
                );
            }
        }
        
        // Update train positions (move along platform paths)
        const float trainSpeed = 2.0f; // Units per second
        // deltaTime already computed above

        // Only rebuild station components when platforms actually changed
        if (g_platformCacheDirty) {
            g_platformCacheDirty = false;

            g_cachedStationCompId.clear();
            g_cachedStationCompKey.clear();
            g_cachedStationMembers.clear();
            BuildStationComponents(g_placedPlatforms, g_gridSpacing, g_cachedStationCompId, g_cachedStationCompKey, g_cachedStationMembers);

            // Rebuild platform type cache
            g_cachedPlatformTypes.resize(g_placedPlatforms.size());
            for (int pi = 0; pi < (int)g_placedPlatforms.size(); pi++) {
                g_cachedPlatformTypes[pi] = (int)GetPlatformType(g_placedPlatforms[pi].position, g_placedPlatforms, g_gridSpacing);
            }

            // Rebuild platform->line lookup
            g_cachedPlatformLineId.assign(g_placedPlatforms.size(), -1);
            for (int li = 0; li < (int)g_lines.size(); li++) {
                for (int pi : g_lines[li].platformIndices) {
                    if (pi >= 0 && pi < (int)g_cachedPlatformLineId.size())
                        g_cachedPlatformLineId[pi] = li;
                }
            }
            g_lineCacheDirty = false;

            // Detect station connections for line establishment
            // Rules: track stays neutral until connected between 2+ stations.
            // - Establish: ONLY when 2+ NEUTRAL stations are connected (all in same component, none in any line).
            //   Also only when component keys CHANGED this frame (new connection made) to avoid constant re-prompting.
            // - Add to line: show when component is already partly in a line but has new platforms.
            int currentComponentCount = (int)g_cachedStationCompKey.size();
            g_debugPreviousComponentCount = currentComponentCount;
            g_debugCurrentComponentCount = currentComponentCount;

            bool componentKeysChanged = (g_previousStationComponentKeys.size() != g_cachedStationCompKey.size());
            if (!componentKeysChanged) {
                for (size_t i = 0; i < g_cachedStationCompKey.size(); i++) {
                    if (i >= g_previousStationComponentKeys.size() || g_cachedStationCompKey[i] != g_previousStationComponentKeys[i]) {
                        componentKeysChanged = true;
                        break;
                    }
                }
            }

            // IMPORTANT: evaluating only on component-key change misses cases where a component grows
            // (e.g. second station added to a neutral crossing line) but keeps the same key.
            // This block already runs only when platform cache is dirty (new build/demolish), so it's safe
            // to evaluate on every network edit.
            if (g_lineModal.state == LineModalState::None && !g_stockModal.open && !g_stationModal.open && !g_demolishConfirmModal.open && currentComponentCount > 0) {
                for (int cid = 0; cid < (int)g_cachedStationMembers.size(); cid++) {
                    if (cid >= (int)g_cachedStationCompKey.size()) continue;

                    long long compKey = g_cachedStationCompKey[cid];

                    // Count distinct physical stations that are NEUTRAL (not in any line)
                    std::set<long long> neutralStationKeys;
                    for (int idx : g_cachedStationMembers[cid]) {
                        if (idx >= 0 && idx < (int)g_placedPlatforms.size() && g_placedPlatforms[idx].isStation
                            && g_placedPlatforms[idx].stationPart == 3 && !g_placedPlatforms[idx].isDepot) {
                            if (idx >= (int)g_cachedPlatformLineId.size() || g_cachedPlatformLineId[idx] < 0)
                                neutralStationKeys.insert(MakePositionKey(g_placedPlatforms[idx].position.x, g_placedPlatforms[idx].position.z));
                        }
                    }
                    bool hasTwoNeutralStations = ((int)neutralStationKeys.size() >= 2);

                    int existingLineId = -1;
                    int platformsInLine = 0;
                    int totalPlatformsInComponent = 0;
                    std::vector<int> componentNeutralPlatforms;

                    for (int pi = 0; pi < (int)g_placedPlatforms.size(); pi++) {
                        if (pi < (int)g_cachedStationCompId.size() && g_cachedStationCompId[pi] == cid && !g_placedPlatforms[pi].isDepot) {
                            totalPlatformsInComponent++;
                            int lineIdAtPi = (pi < (int)g_cachedPlatformLineId.size()) ? g_cachedPlatformLineId[pi] : -1;
                            if (lineIdAtPi < 0) componentNeutralPlatforms.push_back(pi);
                        }
                    }

                    // Super-simple targeting rule: only consider AddToLine if THIS component's neutral
                    // platforms physically touch an already established line.
                    std::unordered_map<int, int> touchCountByLine;
                    for (int pi : componentNeutralPlatforms) {
                        // Skip platforms reset to neutral by demolish or declined as neutral branch
                        long long piKey = MakePositionKey(g_placedPlatforms[pi].position.x,
                                                         g_placedPlatforms[pi].position.z);
                        if (g_demolishNeutralizedPlatformKeys.count(piKey)) continue;
                        if (g_declinedNeutralBranchPlatformKeys.count(piKey)) continue;
                        for (int li = 0; li < (int)g_lines.size(); li++) {
                            if (!IsLineEstablishedByIndex(li)) continue;
                            for (int pj : g_lines[li].platformIndices) {
                                if (pj < 0 || pj >= (int)g_placedPlatforms.size() || g_placedPlatforms[pj].isDepot) continue;
                                if (ArePlatformsConnectedForNetwork(pi, pj, g_placedPlatforms, g_gridSpacing)) {
                                    touchCountByLine[li]++;
                                    break;
                                }
                            }
                        }
                    }
                    int bestTouchCount = 0;
                    for (const auto& kv : touchCountByLine) {
                        if (kv.second > bestTouchCount || (kv.second == bestTouchCount && (existingLineId < 0 || kv.first < existingLineId))) {
                            bestTouchCount = kv.second;
                            existingLineId = kv.first;
                        }
                    }

                    if (existingLineId >= 0) {
                        for (int pi = 0; pi < (int)g_placedPlatforms.size(); pi++) {
                            if (pi < (int)g_cachedStationCompId.size() && g_cachedStationCompId[pi] == cid && !g_placedPlatforms[pi].isDepot) {
                                if (pi < (int)g_cachedPlatformLineId.size() && g_cachedPlatformLineId[pi] == existingLineId)
                                    platformsInLine++;
                            }
                        }
                    }

                    bool alreadyInLine = (existingLineId >= 0);
                    bool hasNewPlatforms = !componentNeutralPlatforms.empty();

                    if (!alreadyInLine && g_declinedComponentKeys.find(compKey) == g_declinedComponentKeys.end()) {
                        if (!hasTwoNeutralStations) {
                            continue; // Neutral component still needs two stations before first establishment.
                        }
                        int establishDetectedSystem = DetectStrictClusterSystemFromPlatforms(g_cachedStationMembers[cid]);
                        std::vector<int> allSystems = DetectAllClusterSystemsFromPlatforms(g_cachedStationMembers[cid]);
                        if (establishDetectedSystem < (int)SiloSystem::SYS1_CARGO) {
                            // Build order invariant: still allow line establishment even when no silo system is
                            // currently detectable (e.g. cargo ecosystem not activated yet). Players can establish
                            // first, then satisfy silo conditions later.
                            DebugLogFormat("LINE_COLOR: Establish fallback for compKey=%lld (no strict system yet) -> defaulting modal color to cargo", (long long)compKey);
                            for (int pidx : g_cachedStationMembers[cid]) {
                                if (pidx < 0 || pidx >= (int)g_placedPlatforms.size()) continue;
                                const PlacedPlatform& plat = g_placedPlatforms[pidx];
                                if (!plat.isStation || plat.isDepot) continue;
                                int sx = WorldToGridCell(plat.position.x);
                                int sz = WorldToGridCell(plat.position.z);
                                ClusterType cellType = GetClusterTypeAtGridCellStrict(sx, sz);
                                int strictSys = DetectStrictClusterSystemForStationPos(plat.position.x, plat.position.z);
                                DebugLogFormat("LINE_DEBUG:   station pi=%d pos=(%.1f,%.1f) cell=(%d,%d) cellType=%d strictSys=%d",
                                    pidx, plat.position.x, plat.position.z, sx, sz, (int)cellType, strictSys);
                            }
                            establishDetectedSystem = (int)SiloSystem::SYS1_CARGO;
                        }
                        DebugLogFormat("DEBUG: MODAL TRIGGERED! Component has 2+ NEUTRAL stations (count=%d), keyChanged=%d", (int)neutralStationKeys.size(), componentKeysChanged ? 1 : 0);
                        g_lineModal.framesOpen = 0;
                        g_lineModal.newComponentKey = compKey;
                        g_lineModal.connectedComponentKeys.clear();
                        g_lineModal.connectedComponentKeys.push_back(compKey);
                        g_lineModal.establishClicked = false;
                        g_lineModal.cancelClicked = false;
                        g_lineModal.nameCursorPos = 0;
                        memset(g_lineModal.nameBuffer, 0, sizeof(g_lineModal.nameBuffer));
                        g_lineModal.detectedSystems = allSystems;
                        g_lineModal.siloChoiceIndex = 0;
                        g_lineModal.siloChoiceClicked = false;

                        if ((int)allSystems.size() >= 2) {
                            // Multiple silo systems detected — let the player choose
                            DebugLogFormat("LINE_COLOR: Silo collision! %d systems detected, showing ChooseSilo modal", (int)allSystems.size());
                            g_lineModal.state = LineModalState::ChooseSilo;
                        } else {
                            g_lineModal.state = LineModalState::EstablishLine;
                            g_lineModal.detectedSystem = establishDetectedSystem;
                            g_lineModal.colorIndex = 1;
                            SystemColorShades shades = GetSystemColorShades(g_lineModal.detectedSystem);
                            g_lineModal.selectedColor = shades.colors[1];
                        }

                        break;
                    } else if (!alreadyInLine && g_declinedComponentKeys.find(compKey) != g_declinedComponentKeys.end()) {
                        DebugLogFormat("LINE_DEBUG: Establish suppressed for compKey=%lld (player previously declined)", (long long)compKey);
                    } else if (alreadyInLine && hasNewPlatforms) {
                        // Compute new platforms (crossing track) first
                        std::vector<int> tmpNewPlatforms;
                        std::vector<int> tmpJunctions;
                        bool targetDeclined = false;
                        bool autoDeclinedCrossThrough = false;
                        if (existingLineId >= 0 && existingLineId < (int)g_lines.size()) {
                            const Line& targetLine = g_lines[existingLineId];
                            targetDeclined = (targetLine.declinedComponentKeys.find(compKey) != targetLine.declinedComponentKeys.end());
                            for (int pi = 0; pi < (int)g_placedPlatforms.size(); pi++) {
                                if (pi < (int)g_cachedStationCompId.size() && g_cachedStationCompId[pi] == cid && !g_placedPlatforms[pi].isDepot) {
                                    if (targetLine.platformIndices.find(pi) != targetLine.platformIndices.end()) continue;
                                    // Only treat neutral-or-target-owned platforms as the new branch candidate.
                                    // Exclude platforms already established on some *other* line to avoid false
                                    // "second station" triggers when components overlap through crossings.
                                    int platformLine = (pi < (int)g_cachedPlatformLineId.size()) ? g_cachedPlatformLineId[pi] : -1;
                                    if (platformLine >= 0 && platformLine != existingLineId) continue;
                                    tmpNewPlatforms.push_back(pi);
                                }
                            }
                            for (int pi : tmpNewPlatforms) {
                                for (int pj : targetLine.platformIndices) {
                                    if (g_placedPlatforms[pj].isDepot) continue;
                                    if (ArePlatformsConnectedForNetwork(pi, pj, g_placedPlatforms, g_gridSpacing))
                                        tmpJunctions.push_back(pj);
                                }
                            }
                            std::sort(tmpJunctions.begin(), tmpJunctions.end());
                            tmpJunctions.erase(std::unique(tmpJunctions.begin(), tmpJunctions.end()), tmpJunctions.end());
                        }
                        // If this neutral branch touches 2+ established lines, treat it as an obvious cross-through:
                        // do NOT offer AddToLine merge; protect it as neutral (NO CONTINUE semantics) until explicit establish.
                        if (!tmpNewPlatforms.empty() && existingLineId >= 0 && existingLineId < (int)g_lines.size()
                            && (int)touchCountByLine.size() >= 2 && !targetDeclined) {
                            Line& targetLineMutable = g_lines[existingLineId];
                            targetLineMutable.declinedComponentKeys.insert(compKey);
                            for (int pi : tmpNewPlatforms) {
                                if (pi < 0 || pi >= (int)g_placedPlatforms.size()) continue;
                                const Vector3& p = g_placedPlatforms[pi].position;
                                long long k = MakePositionKey(p.x, p.z);
                                targetLineMutable.declinedBranchPlatformKeys.insert(k);
                                g_declinedNeutralBranchPlatformKeys.insert(k);
                            }
                            for (int pj : tmpJunctions) {
                                if (pj < 0 || pj >= (int)g_placedPlatforms.size()) continue;
                                const Vector3& p = g_placedPlatforms[pj].position;
                                long long k = MakePositionKey(p.x, p.z);
                                targetLineMutable.declinedBranchPlatformKeys.insert(k);
                                g_declinedNeutralBranchPlatformKeys.insert(k);
                            }
                            targetDeclined = true;
                            autoDeclinedCrossThrough = true;
                            DebugLogFormat("LINE_COLOR: Auto NO CONTINUE cross-through (touches %d established lines), targetLineIdx=%d newPlatforms=%d junctions=%d",
                                (int)touchCountByLine.size(), existingLineId, (int)tmpNewPlatforms.size(), (int)tmpJunctions.size());
                        }
                        int crossingStationTiles = 0;
                        for (int pi : tmpNewPlatforms) {
                            if (pi >= 0 && pi < (int)g_placedPlatforms.size() && g_placedPlatforms[pi].isStation && !g_placedPlatforms[pi].isDepot)
                                crossingStationTiles++;
                        }
                        int crossingStations = crossingStationTiles / 4;
                        // If target already declined and crossing now has 2+ stations, show Establish directly.
                        // BUT skip if the crossing platforms are already entirely in another line (already established).
                        bool crossingAlreadyEstablished = false;
                        if (targetDeclined && crossingStations >= 2) {
                            std::set<int> crossingSet(tmpNewPlatforms.begin(), tmpNewPlatforms.end());
                            for (int pj : tmpJunctions) crossingSet.insert(pj);
                            int inOtherLine = 0;
                            for (int pi : crossingSet) {
                                if (pi < (int)g_cachedPlatformLineId.size() && g_cachedPlatformLineId[pi] >= 0
                                    && g_cachedPlatformLineId[pi] != existingLineId)
                                    inOtherLine++;
                            }
                            crossingAlreadyEstablished = (inOtherLine == (int)crossingSet.size());
                        }
                        if (targetDeclined && crossingStations >= 2) {
                            if (crossingAlreadyEstablished) {
                                DebugLogFormat("LINE_COLOR: Target declined but crossing already in another line - skip modal");
                            } else {
                                int crossingDetectedSystem = DetectStrictClusterSystemFromPlatforms(tmpNewPlatforms);
                                int targetLineSystem = IsLineEstablishedByIndex(existingLineId) ? DetectStrictClusterSystemForLine(existingLineId) : -1;
                                if (crossingDetectedSystem < (int)SiloSystem::SYS1_CARGO) {
                                    DebugLogFormat("LINE_COLOR: Target declined crossing remains neutral (no station inside colored cluster)");
                                } else if (targetLineSystem >= (int)SiloSystem::SYS1_CARGO && crossingDetectedSystem == targetLineSystem) {
                                    DebugLogFormat("LINE_COLOR: Target declined crossing remains neutral (same cluster color as established line)");
                                } else {
                                    std::vector<int> crossingSystems = DetectAllClusterSystemsFromPlatforms(tmpNewPlatforms);
                                    DebugLogFormat("LINE_COLOR: Target declined, crossing has %d stations and valid new color -> Establish directly", crossingStations);
                                    g_lineModal.state = ((int)crossingSystems.size() >= 2) ? LineModalState::ChooseSilo : LineModalState::EstablishLine;
                                    g_lineModal.framesOpen = 0;
                                    g_lineModal.newComponentKey = 0;
                                    g_lineModal.connectedComponentKeys.clear();
                                    g_lineModal.establishClicked = false;
                                    g_lineModal.cancelClicked = false;
                                    g_lineModal.nameBuffer[0] = '\0';
                                    g_lineModal.nameCursorPos = 0;
                                    g_lineModal.detectedSystems = crossingSystems;
                                    g_lineModal.siloChoiceIndex = 0;
                                    g_lineModal.siloChoiceClicked = false;
                                    g_lineModal.pendingEstablishPlatforms.clear();
                                    for (int pi : tmpNewPlatforms) g_lineModal.pendingEstablishPlatforms.push_back(pi);
                                    for (int pj : tmpJunctions) g_lineModal.pendingEstablishPlatforms.push_back(pj);
                                    g_lineModal.pendingCid = cid;
                                    g_lineModal.targetLineId = existingLineId;  // Keep for reference
                                    g_lineModal.detectedSystem = crossingDetectedSystem;
                                    g_lineModal.colorIndex = 1;
                                    SystemColorShades shades = GetSystemColorShades(g_lineModal.detectedSystem);
                                    g_lineModal.selectedColor = shades.colors[1];
                                }
                            }
                        }
                        // AddToLine only when target hasn't declined; when declined+crossing we Establish or skip
                        if (!(autoDeclinedCrossThrough || (targetDeclined && crossingStations >= 2))) {
                            DebugLogFormat("LINE_COLOR: AddToLine modal SHOWN targetLineIdx=%d compKey=%lld targetPlatforms=%d totalInComp=%d",
                                existingLineId, (long long)compKey, platformsInLine, totalPlatformsInComponent);
                            DebugLogFormat("DEBUG: Showing AddToLine modal for line %d (new platforms connecting)", existingLineId);
                            g_lineModal.state = LineModalState::AddToLine;
                            g_lineModal.framesOpen = 0;
                            g_lineModal.targetLineId = existingLineId;
                            g_lineModal.newComponentKey = compKey;
                            g_lineModal.addToLineClicked = false;
                            g_lineModal.cancelClicked = false;
                            g_lineModal.pendingNewPlatforms = tmpNewPlatforms;
                            g_lineModal.pendingJunctions = tmpJunctions;
                            g_lineModal.targetPlatformIndicesAtShow.clear();
                            g_lineModal.pendingCid = cid;
                            if (existingLineId >= 0 && existingLineId < (int)g_lines.size())
                                g_lineModal.targetPlatformIndicesAtShow = g_lines[existingLineId].platformIndices;
                            DebugLogFormat("LINE_COLOR: Snapshot newPlatforms=%d junctions=%d targetAtShow=%d (before sync pollutes)", (int)g_lineModal.pendingNewPlatforms.size(), (int)g_lineModal.pendingJunctions.size(), (int)g_lineModal.targetPlatformIndicesAtShow.size());
                        }
                        // Only stop scanning components if a modal was actually opened.
                        // Otherwise keep checking other components this frame (build order agnostic).
                        if (g_lineModal.state != LineModalState::None) break;
                    }
                }
            }

            g_previousStationComponentKeys.assign(g_cachedStationCompKey.begin(), g_cachedStationCompKey.end());

            // Rebuild station prime hotspot and depot adjacency caches
            // Each component can contain multiple physical stations; each gets its own prime (stationPart == 3).
            int numComps = (int)g_cachedStationMembers.size();
            g_cachedStationPrimePlatformIdx.assign(numComps, std::vector<int>());
            g_cachedStationPrimePos.assign(numComps, std::vector<Vector3>());
            g_cachedStationHasAdjacentDepot.assign(numComps, 0);
            for (int cid = 0; cid < numComps; cid++) {
                for (int pi : g_cachedStationMembers[cid]) {
                    if (pi < 0 || pi >= (int)g_placedPlatforms.size()) continue;
                    const auto& p = g_placedPlatforms[pi];
                    if (p.isDepot || !p.isStation) continue;
                    if (p.stationPart == 3) {
                        g_cachedStationPrimePlatformIdx[cid].push_back(pi);
                        g_cachedStationPrimePos[cid].push_back(p.position);
                    }
                }
            }
            for (int cid = 0; cid < numComps; cid++) {
                for (int di = 0; di < (int)g_placedPlatforms.size(); di++) {
                    if (!g_placedPlatforms[di].isDepot) continue;
                    for (int si : g_cachedStationMembers[cid]) {
                        if (ArePlatformsAdjacent(g_placedPlatforms[di].position, g_placedPlatforms[si].position, g_gridSpacing)) {
                            g_cachedStationHasAdjacentDepot[cid] = 1;
                            break;
                        }
                    }
                    if (g_cachedStationHasAdjacentDepot[cid]) break;
                }
            }
        }
        // Rebuild platform->line lookup if only lines changed (not platforms)
        if (g_lineCacheDirty) {
            g_lineCacheDirty = false;
            g_cachedPlatformLineId.assign(g_placedPlatforms.size(), -1);
            for (int li = 0; li < (int)g_lines.size(); li++) {
                for (int pi : g_lines[li].platformIndices) {
                    if (pi >= 0 && pi < (int)g_cachedPlatformLineId.size())
                        g_cachedPlatformLineId[pi] = li;
                }
            }
        }
        // Use cached results for the rest of the frame
        const std::vector<int>& stationCompId = g_cachedStationCompId;
        const std::vector<long long>& stationCompKey = g_cachedStationCompKey;
        const std::vector<std::vector<int>>& stationMembers = g_cachedStationMembers;
        
        // Handle modal responses. crossingNewLineIndex/crossingTargetLineId set when user clicks "NO CONTINUE" on AddToLine.
        int crossingNewLineIndex = -1;
        int crossingTargetLineId = -1;
        if (g_junctionModal.open && g_junctionModal.doNotBuildClicked) {
            DebugLogFormat("LINE_DEBUG: Junction modal DO NOT BUILD start=(%.0f,%.0f) end=(%.0f,%.0f)",
                g_junctionModal.pendingStartPos.x, g_junctionModal.pendingStartPos.z,
                g_junctionModal.pendingEndPos.x, g_junctionModal.pendingEndPos.z);
            g_junctionModal.open = false;
            g_junctionModalOpen = false;
            g_junctionModal.doNotBuildClicked = false;
            g_junctionModal.buildJunctionClicked = false;
        } else if (g_junctionModal.open && g_junctionModal.buildJunctionClicked) {
            std::vector<Vector3> lineCells;
            { Vector3 cf = { g_camera.target.x - g_camera.position.x, 0.0f, g_camera.target.z - g_camera.position.z };
              float cl = sqrtf(cf.x*cf.x + cf.z*cf.z); if (cl > 0.001f) { cf.x /= cl; cf.z /= cl; }
              GetGridCellsLShape(g_junctionModal.pendingStartPos, g_junctionModal.pendingEndPos, g_gridSpacing, cf, lineCells); }
            int groupId = g_nextPlacementGroupId++;
            // Per-cell drag direction: compare each cell with its predecessor in the L-path
            auto getCellDragHorizontal = [&](int ci) -> bool {
                if (ci > 0) {
                    float dxp = fabsf(lineCells[ci].x - lineCells[ci-1].x);
                    float dzp = fabsf(lineCells[ci].z - lineCells[ci-1].z);
                    if (dxp > 0.01f || dzp > 0.01f) return dxp >= dzp;
                }
                if (ci + 1 < (int)lineCells.size()) {
                    float dxn = fabsf(lineCells[ci+1].x - lineCells[ci].x);
                    float dzn = fabsf(lineCells[ci+1].z - lineCells[ci].z);
                    if (dxn > 0.01f || dzn > 0.01f) return dxn >= dzn;
                }
                return fabsf(g_junctionModal.pendingEndPos.x - g_junctionModal.pendingStartPos.x)
                    >= fabsf(g_junctionModal.pendingEndPos.z - g_junctionModal.pendingStartPos.z);
            };
            int placedCount = 0;
            int totalSpentJunction = 0;
            bool anyJunctionMarked = false;
            int overpassMarked = 0;
            int firstNewPlatformIdxJ = (int)g_placedPlatforms.size();
            for (int ci = 0; ci < (int)lineCells.size(); ci++) {
                const Vector3& pos = lineCells[ci];
                bool dragHorizontal = getCellDragHorizontal(ci);
                int existingIdx = FindPlatformIndexAtPos(pos, g_placedPlatforms);
                if (existingIdx >= 0) {
                    bool existingHorizontal = false;
                    bool straightExisting = IsStraightThroughTrackCell(existingIdx, g_placedPlatforms, g_gridSpacing, existingHorizontal);
                    Vector3 before = pos;
                    Vector3 after = pos;
                    if (dragHorizontal) {
                        before.x -= g_gridSpacing;
                        after.x += g_gridSpacing;
                    } else {
                        before.z -= g_gridSpacing;
                        after.z += g_gridSpacing;
                    }
                    bool hasBefore = false;
                    bool hasAfter = false;
                    for (const Vector3& c : lineCells) {
                        if (Vector3Distance(c, before) < 0.1f) hasBefore = true;
                        if (Vector3Distance(c, after) < 0.1f) hasAfter = true;
                    }
                    bool crossThrough = hasBefore && hasAfter;
                    bool isPureXCross = crossThrough && straightExisting && (existingHorizontal != dragHorizontal);
                    if (isPureXCross) {
                        long long key = MakePositionKey(pos.x, pos.z);
                        g_overpassGroupsByPosKey[key].insert(groupId);
                        overpassMarked++;
                    } else {
                        g_placedPlatforms[existingIdx].isJunction = true;
                        anyJunctionMarked = true;
                    }
                    continue;
                }
                bool canPlace = true;
                if (!IsWithinGridBounds(pos.x, pos.z, g_gridSpacing * 0.5f)) canPlace = false;
                Building testBuilding;
                testBuilding.position = pos;
                testBuilding.size = { g_gridSpacing, g_gridSpacing, g_gridSpacing };
                if (overlapsWithAny(testBuilding, g_buildings)) canPlace = false;
                for (const auto& placed : g_placedPlatforms) {
                    if (Vector3Distance(pos, placed.position) < g_gridSpacing * 0.9f) { canPlace = false; break; }
                }
                int segCost = ApplyBuildDiscount(OuterGridCost(150, pos.x, pos.z));
                if (canPlace && g_playerCredits < segCost) canPlace = false;
                if (canPlace) {
                    g_playerCredits -= segCost;
                    totalSpentJunction += segCost;
                    PlacedPlatform newPlatform;
                    newPlatform.position = pos;
                    newPlatform.isStation = false;
                    newPlatform.placementOrientation = 0;
                    newPlatform.stationPart = 0;
                    newPlatform.isDepot = false;
                    newPlatform.depotCargo = 0;
                    newPlatform.placementGroupId = groupId;
                    newPlatform.isJunction = false;
                    g_placedPlatforms.push_back(newPlatform);
                    // Surgically lift neutralization guard for this tile only
                    {
                        ClearPlacementProtectionForPlatform(pos);
                    }
                    InvalidatePlatformCaches();
                    SpawnBuildParticles(pos, g_platformColor, g_gridSpacing);
                    placedCount++;
                }
            }
            if (anyJunctionMarked || placedCount > 0 || overpassMarked > 0) {
                InvalidatePlatformCaches();
                // Auto-extend established lines with newly placed junction track
                if (placedCount > 0) {
                    std::vector<int> tempCompId;
                    std::vector<long long> tempCompKey;
                    std::vector<std::vector<int>> tempMembers;
                    BuildStationComponents(g_placedPlatforms, g_gridSpacing, tempCompId, tempCompKey, tempMembers);
                    for (int pi = firstNewPlatformIdxJ; pi < (int)g_placedPlatforms.size(); pi++) {
                        if (pi >= (int)tempCompId.size()) continue;
                        int cid = tempCompId[pi];
                        if (cid < 0) continue;
                        // Skip platforms still under demolish neutralization guard
                        long long piKey = MakePositionKey(g_placedPlatforms[pi].position.x,
                                                          g_placedPlatforms[pi].position.z);
                        if (g_demolishNeutralizedPlatformKeys.count(piKey)) continue;
                        for (auto& line : g_lines) {
                            bool lineOwnsComponent = false;
                            for (int existingPi : line.platformIndices) {
                                if (existingPi < (int)tempCompId.size() && tempCompId[existingPi] == cid) {
                                    lineOwnsComponent = true;
                                    break;
                                }
                            }
                            if (lineOwnsComponent) {
                                line.platformIndices.insert(pi);
                                break; // Only add to the first matching line
                            }
                        }
                    }
                }
                {
                    std::set<int> affectedLineIds;
                    for (const auto& line : g_lines) {
                        for (int pi = firstNewPlatformIdxJ; pi < (int)g_placedPlatforms.size(); pi++) {
                            if (line.platformIndices.count(pi)) {
                                affectedLineIds.insert(line.id);
                                break;
                            }
                        }
                    }
                    RebuildTrainsOnLines(affectedLineIds);
                }
            }
            if (placedCount > 0) {
                char buf[128];
                snprintf(buf, sizeof(buf), "PLATFORM LINE BUILT (JUNCTION) - %d CREDITS", totalSpentJunction);
                AddTerminalMessage(buf);
                if (g_sfxBuildSys.frameCount > 0) PlaySound(g_sfxBuildSys);
            } else if (anyJunctionMarked) {
                AddTerminalMessage("JUNCTION CONNECTED - TRACKS LINKED");
            } else if (overpassMarked > 0) {
                AddTerminalMessage("OVERPASS CROSSING BUILT - LINES STAY SEPARATE");
            }
            DebugLogFormat("LINE_DEBUG: Junction modal BUILD applied start=(%.0f,%.0f) end=(%.0f,%.0f) newTrack=%d markedExisting=%d overpassCross=%d",
                g_junctionModal.pendingStartPos.x, g_junctionModal.pendingStartPos.z,
                g_junctionModal.pendingEndPos.x, g_junctionModal.pendingEndPos.z,
                placedCount, anyJunctionMarked ? 1 : 0, overpassMarked);
            g_junctionModal.open = false;
            g_junctionModalOpen = false;
            g_junctionModal.buildJunctionClicked = false;
            g_junctionModal.doNotBuildClicked = false;
        }
        // Handle ChooseSilo confirmation: transition to EstablishLine with chosen system
        if (g_lineModal.state == LineModalState::ChooseSilo && g_lineModal.siloChoiceClicked) {
            int chosenSystem = -1;
            if (g_lineModal.siloChoiceIndex >= 0 && g_lineModal.siloChoiceIndex < (int)g_lineModal.detectedSystems.size())
                chosenSystem = g_lineModal.detectedSystems[g_lineModal.siloChoiceIndex];
            DebugLogFormat("LINE_COLOR: Silo chosen: system %d", chosenSystem);
            g_lineModal.state = LineModalState::EstablishLine;
            g_lineModal.framesOpen = 0;
            g_lineModal.detectedSystem = chosenSystem;
            g_lineModal.colorIndex = 1;
            g_lineModal.siloChoiceClicked = false;
            g_lineModal.nameBuffer[0] = '\0';
            g_lineModal.nameCursorPos = 0;
            SystemColorShades shades = GetSystemColorShades(chosenSystem);
            g_lineModal.selectedColor = shades.colors[1];
        }
        // Handle ChooseSilo cancel: cancel the whole establish flow
        if (g_lineModal.state == LineModalState::ChooseSilo && g_lineModal.cancelClicked) {
            g_lineModal.state = LineModalState::None;
            g_lineModal.cancelClicked = false;
            g_declinedComponentKeys.insert(g_lineModal.newComponentKey);
        }
        if (g_lineModal.state == LineModalState::EstablishLine && g_lineModal.establishClicked) {
            DebugLogFormat("LINE_DEBUG: Establish confirm clicked compKey=%lld pendingPlatforms=%d detectedSystem=%d",
                (long long)g_lineModal.newComponentKey, (int)g_lineModal.pendingEstablishPlatforms.size(), g_lineModal.detectedSystem);
            // Establish new line (use default name if none entered - prevents modal loop)
            {
                Line newLine;
                newLine.id = g_nextLineId++;
                newLine.name = (g_lineModal.nameCursorPos > 0) ? std::string(g_lineModal.nameBuffer)
                    : std::string("Line") + std::to_string(newLine.id + 1);
                newLine.color = g_lineModal.selectedColor;
                newLine.chosenSystem = g_lineModal.detectedSystem;
                bool createdFromPending = false;
                if (!g_lineModal.pendingEstablishPlatforms.empty()) {
                    // Crossing line: establish from specific platform list (from NO CONTINUE flow)
                    newLine.isCrossingLine = true;
                    for (int pi : g_lineModal.pendingEstablishPlatforms) {
                        if (pi >= 0 && pi < (int)g_placedPlatforms.size() && !g_placedPlatforms[pi].isDepot)
                            newLine.platformIndices.insert(pi);
                    }
                    if (g_lineModal.pendingCid >= 0 && g_lineModal.pendingCid < (int)stationCompKey.size())
                        newLine.componentKeys.insert(stationCompKey[g_lineModal.pendingCid]);
                    newLine.stationCount = CountPhysicalStationsInLine(newLine, g_placedPlatforms);
                    g_lines.push_back(newLine);
                    InvalidateLineCaches();
                    // This branch is now explicitly established; release the neutral-only protection.
                    for (int pi : newLine.platformIndices) {
                        if (pi < 0 || pi >= (int)g_placedPlatforms.size()) continue;
                        const Vector3& p = g_placedPlatforms[pi].position;
                        long long key = MakePositionKey(p.x, p.z);
                        g_declinedNeutralBranchPlatformKeys.erase(key);
                        // Keep visual/pass-through junction cells shareable across lines.
                        // Lock only branch-exclusive (non-junction) platforms.
                        if (!g_placedPlatforms[pi].isJunction) {
                            g_lockedBranchOwnerLineId[key] = newLine.id;
                        }
                    }
                    // Remove locked branch platforms from all other lines so ownership cannot flip to yellow/cargo.
                    for (Line& other : g_lines) {
                        if (other.id == newLine.id) continue;
                        std::vector<int> toErase;
                        for (int opi : other.platformIndices) {
                            if (opi < 0 || opi >= (int)g_placedPlatforms.size()) continue;
                            const Vector3& op = g_placedPlatforms[opi].position;
                            long long oKey = MakePositionKey(op.x, op.z);
                            auto itOwner = g_lockedBranchOwnerLineId.find(oKey);
                            if (itOwner != g_lockedBranchOwnerLineId.end() && itOwner->second == newLine.id
                                && !g_placedPlatforms[opi].isJunction)
                                toErase.push_back(opi);
                        }
                        for (int opi : toErase) other.platformIndices.erase(opi);
                    }
                    g_lineModal.pendingEstablishPlatforms.clear();
                    DebugLogFormat("DEBUG: Created crossing line '%s' (id=%d) color=(%d,%d,%d) %d platforms",
                        newLine.name.c_str(), newLine.id, newLine.color.r, newLine.color.g, newLine.color.b, (int)newLine.platformIndices.size());
                    DebugLogFormat("LINE_COLOR: crossing ownership lock set lineId=%d keys=%d",
                        newLine.id, (int)g_lockedBranchOwnerLineId.size());
                    createdFromPending = true;
                }
                if (!createdFromPending && g_lineModal.newComponentKey != 0) {
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
                } else if (!createdFromPending) {
                    // Fallback: add all component keys if newComponentKey wasn't set
                    for (long long key : stationCompKey) {
                        newLine.componentKeys.insert(key);
                    }
                    DebugLogFormat("DEBUG: Created line '%s' with all component keys (fallback)", newLine.name.c_str());
                }
                if (!createdFromPending) {
                    newLine.stationCount = CountPhysicalStationsInLine(newLine, g_placedPlatforms);
                    g_lines.push_back(newLine);
                    InvalidateLineCaches();
                    DebugLogFormat("DEBUG: Line created id=%d, name='%s', %d component keys, selectedColor R=%d G=%d B=%d A=%d", 
                                   newLine.id, newLine.name.c_str(), (int)newLine.componentKeys.size(), 
                                   newLine.color.r, newLine.color.g, newLine.color.b, newLine.color.a);
                    int keyCount = 0;
                    for (long long key : newLine.componentKeys) {
                        if (keyCount < 5) {
                            DebugLogFormat("DEBUG: Line %d component key %d: %lld", newLine.id, keyCount, key);
                            keyCount++;
                        }
                    }
                }
            }
            if (g_lineModal.newComponentKey != 0) g_declinedComponentKeys.erase(g_lineModal.newComponentKey);
            // Lock sys8-12 hotspots until the user places a matching-colour train on the new line
            if (g_awaitingTrainForLineId < 0 && !g_lines.empty()) g_awaitingTrainForLineId = g_lines.back().id;
            g_lineModal.state = LineModalState::None;
            g_lineModal.establishClicked = false;
            g_lineModal.cancelClicked = false;
        } else if (g_lineModal.state == LineModalState::EstablishLine && g_lineModal.cancelClicked) {
            DebugLogFormat("LINE_DEBUG: Establish cancelled compKey=%lld pendingPlatforms=%d",
                (long long)g_lineModal.newComponentKey, (int)g_lineModal.pendingEstablishPlatforms.size());
            if (g_lineModal.newComponentKey != 0) g_declinedComponentKeys.insert(g_lineModal.newComponentKey);
            g_lineModal.pendingEstablishPlatforms.clear();  // Crossing: platforms stay neutral
            g_lineModal.state = LineModalState::None;
            g_lineModal.cancelClicked = false;
        } else if (g_lineModal.state == LineModalState::AddToLine && g_lineModal.addToLineClicked) {
            DebugLogFormat("LINE_DEBUG: AddToLine confirm clicked targetLineIdx=%d newPlatforms=%d junctions=%d",
                g_lineModal.targetLineId, (int)g_lineModal.pendingNewPlatforms.size(), (int)g_lineModal.pendingJunctions.size());
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
                    
                    targetLine.stationCount = CountPhysicalStationsInLine(targetLine, g_placedPlatforms);
                    InvalidateLineCaches();
                    DebugLogFormat("LINE_COLOR: ADD TO LINE merged into '%s' (id=%d idx=%d) color=(%d,%d,%d) now %d platforms",
                        targetLine.name.c_str(), targetLine.id, g_lineModal.targetLineId,
                        targetLine.color.r, targetLine.color.g, targetLine.color.b,
                        (int)targetLine.platformIndices.size());
                    DebugLogFormat("DEBUG: Extended line '%s' (id=%d) to include %d platforms", 
                                   targetLine.name.c_str(), targetLine.id, (int)targetLine.platformIndices.size());
                } else {
                    DebugLogFormat("LINE_DEBUG: AddToLine confirm failed - no matching component for targetLineIdx=%d",
                        g_lineModal.targetLineId);
                }
            }
            g_lineModal.state = LineModalState::None;
            g_lineModal.addToLineClicked = false;
            g_lineModal.cancelClicked = false;
        } else if (g_lineModal.state == LineModalState::AddToLine && g_lineModal.cancelClicked) {
            // User chose "NO CONTINUE": keep building as a separate line that crosses the established one.
            DebugLogFormat("LINE_COLOR: NO CONTINUE clicked! targetLineId=%d newComponentKey=%lld stationCompKeys count=%d",
                g_lineModal.targetLineId, (long long)g_lineModal.newComponentKey, (int)stationCompKey.size());
            for (size_t c = 0; c < stationCompKey.size() && c < 5; c++)
                DebugLogFormat("LINE_COLOR:   cid=%d key=%lld", (int)c, (long long)stationCompKey[c]);
            // Create a new line containing the new platforms + junction(s) so this crossing can become its own established line/silo.
            if (g_lineModal.targetLineId >= 0 && g_lineModal.targetLineId < (int)g_lines.size()) {
                Line& targetLine = g_lines[g_lineModal.targetLineId];
                int matchingCid = -1;
                for (int cid = 0; cid < (int)stationCompKey.size(); cid++) {
                    if (stationCompKey[cid] != g_lineModal.newComponentKey) continue;
                    for (int pi : targetLine.platformIndices) {
                        if (pi < (int)stationCompId.size() && stationCompId[pi] == cid) {
                            matchingCid = cid;
                            break;
                        }
                    }
                    if (matchingCid >= 0) break;
                }
                DebugLogFormat("LINE_COLOR: matchingCid=%d targetLine.platformIndices=%d pendingNew=%d pendingJunc=%d",
                    matchingCid, (int)targetLine.platformIndices.size(), (int)g_lineModal.pendingNewPlatforms.size(), (int)g_lineModal.pendingJunctions.size());
                std::set<int> newPlatforms;
                std::set<int> junctions;
                if (!g_lineModal.pendingNewPlatforms.empty() || !g_lineModal.pendingJunctions.empty()) {
                    for (int pi : g_lineModal.pendingNewPlatforms) newPlatforms.insert(pi);
                    for (int pj : g_lineModal.pendingJunctions) junctions.insert(pj);
                    DebugLogFormat("LINE_COLOR: Using snapshot newPlatforms=%d junctions=%d", (int)newPlatforms.size(), (int)junctions.size());
                } else if (!g_lineModal.targetPlatformIndicesAtShow.empty() && (matchingCid >= 0 || g_lineModal.pendingCid >= 0)) {
                    // Fallback: target was polluted by sync; use targetPlatformIndicesAtShow from when modal was shown
                    int useCid = (matchingCid >= 0) ? matchingCid : g_lineModal.pendingCid;
                    const std::set<int>& targetAtShow = g_lineModal.targetPlatformIndicesAtShow;
                    for (int pi = 0; pi < (int)g_placedPlatforms.size(); pi++) {
                        if (pi < (int)stationCompId.size() && stationCompId[pi] == useCid && !g_placedPlatforms[pi].isDepot) {
                            if (targetAtShow.find(pi) == targetAtShow.end())
                                newPlatforms.insert(pi);
                        }
                    }
                    for (int pi : newPlatforms) {
                        for (int pj : targetAtShow) {
                            if (pj < 0 || pj >= (int)g_placedPlatforms.size() || g_placedPlatforms[pj].isDepot) continue;
                            if (ArePlatformsConnectedForNetwork(pi, pj, g_placedPlatforms, g_gridSpacing))
                                junctions.insert(pj);
                        }
                    }
                    DebugLogFormat("LINE_COLOR: Fallback (targetAtShow) newPlatforms=%d junctions=%d", (int)newPlatforms.size(), (int)junctions.size());
                } else if (matchingCid >= 0) {
                    for (int pi = 0; pi < (int)g_placedPlatforms.size(); pi++) {
                        if (pi < (int)stationCompId.size() && stationCompId[pi] == matchingCid && !g_placedPlatforms[pi].isDepot) {
                            if (targetLine.platformIndices.find(pi) == targetLine.platformIndices.end())
                                newPlatforms.insert(pi);
                        }
                    }
                    for (int pi : newPlatforms) {
                        for (int pj : targetLine.platformIndices) {
                            if (g_placedPlatforms[pj].isDepot) continue;
                            if (ArePlatformsConnectedForNetwork(pi, pj, g_placedPlatforms, g_gridSpacing))
                                junctions.insert(pj);
                        }
                    }
                    DebugLogFormat("LINE_COLOR: Recomputed newPlatforms=%d junctions=%d", (int)newPlatforms.size(), (int)junctions.size());
                }
                if (matchingCid >= 0 || !newPlatforms.empty() || !junctions.empty()) {
                    if (newPlatforms.empty() && junctions.empty()) {
                        DebugLog("LINE_COLOR: SKIP - newPlatforms and junctions both empty (all platforms already in target line?)");
                    }
                    if (!newPlatforms.empty() || !junctions.empty()) {
                        targetLine.declinedComponentKeys.insert(g_lineModal.newComponentKey);
                        for (int pi : newPlatforms) {
                            if (pi < 0 || pi >= (int)g_placedPlatforms.size()) continue;
                            const Vector3& p = g_placedPlatforms[pi].position;
                            g_declinedNeutralBranchPlatformKeys.insert(MakePositionKey(p.x, p.z));
                        }
                        for (int pi : newPlatforms) {
                            if (pi < 0 || pi >= (int)g_placedPlatforms.size()) continue;
                            const Vector3& p = g_placedPlatforms[pi].position;
                            targetLine.declinedBranchPlatformKeys.insert(MakePositionKey(p.x, p.z));
                        }
                        for (int pj : junctions) {
                            if (pj < 0 || pj >= (int)g_placedPlatforms.size()) continue;
                            const Vector3& p = g_placedPlatforms[pj].position;
                            targetLine.declinedBranchPlatformKeys.insert(MakePositionKey(p.x, p.z));
                        }
                        DebugLogFormat("LINE_COLOR: NO CONTINUE decline seeds stored=%d for targetLineId=%d",
                            (int)targetLine.declinedBranchPlatformKeys.size(), targetLine.id);
                        DebugLogFormat("LINE_COLOR: NO CONTINUE neutral-branch guard keys=%d",
                            (int)g_declinedNeutralBranchPlatformKeys.size());
                        // Count distinct stations on crossing side. Use station tile count / 4 (each station = 4 tiles)
                        // since stationPart==3 can be unreliable when stations span target/crossing boundary
                        int crossingStationTiles = 0;
                        for (int pi : newPlatforms) {
                            if (pi < 0 || pi >= (int)g_placedPlatforms.size()) continue;
                            const PlacedPlatform& p = g_placedPlatforms[pi];
                            int platformLine = (pi < (int)g_cachedPlatformLineId.size()) ? g_cachedPlatformLineId[pi] : -1;
                            if (platformLine >= 0) continue; // only count neutral branch stations
                            if (p.isStation && !p.isDepot) crossingStationTiles++;
                        }
                        int crossingStations = crossingStationTiles / 4;
                        DebugLogFormat("LINE_COLOR: NO CONTINUE - crossing has %d station tiles -> %d stations (need 2+)", crossingStationTiles, crossingStations);
                        if (crossingStations < 2) {
                            // Crossing track has < 2 stations: keep neutral. No line created; platforms stay unassigned until a station connects.
                        } else {
                            std::vector<int> neutralBranchPlatforms;
                            neutralBranchPlatforms.reserve(newPlatforms.size());
                            for (int pi : newPlatforms) {
                                if (pi < 0 || pi >= (int)g_placedPlatforms.size()) continue;
                                int platformLine = (pi < (int)g_cachedPlatformLineId.size()) ? g_cachedPlatformLineId[pi] : -1;
                                if (platformLine >= 0) continue; // ignore stations already belonging to established lines
                                neutralBranchPlatforms.push_back(pi);
                            }
                            int crossingDetectedSystem = DetectStrictClusterSystemFromPlatforms(neutralBranchPlatforms);
                            std::vector<int> crossingSystems = DetectAllClusterSystemsFromPlatforms(neutralBranchPlatforms);
                            int targetLineSystem = IsLineEstablishedByIndex(g_lineModal.targetLineId) ? DetectStrictClusterSystemForLine(g_lineModal.targetLineId) : -1;
                            if (crossingDetectedSystem < (int)SiloSystem::SYS1_CARGO) {
                                DebugLogFormat("LINE_COLOR: NO CONTINUE - crossing stays neutral (no station inside colored cluster)");
                            } else if (targetLineSystem >= (int)SiloSystem::SYS1_CARGO && crossingDetectedSystem == targetLineSystem) {
                                DebugLogFormat("LINE_COLOR: NO CONTINUE - crossing stays neutral (same cluster color as established line)");
                            } else {
                                // Crossing track has 2+ stations and a different qualifying color: establish new line.
                                g_lineModal.state = ((int)crossingSystems.size() >= 2) ? LineModalState::ChooseSilo : LineModalState::EstablishLine;
                                g_lineModal.framesOpen = 0;
                                g_lineModal.establishClicked = false;
                                g_lineModal.cancelClicked = false;
                                g_lineModal.nameBuffer[0] = '\0';
                                g_lineModal.nameCursorPos = 0;
                                g_lineModal.pendingEstablishPlatforms.clear();
                                for (int pi : newPlatforms) g_lineModal.pendingEstablishPlatforms.push_back(pi);
                                for (int pj : junctions) g_lineModal.pendingEstablishPlatforms.push_back(pj);
                                g_lineModal.newComponentKey = 0;  // Not from a component - from platform list
                                g_lineModal.connectedComponentKeys.clear();
                                g_lineModal.detectedSystems = crossingSystems;
                                g_lineModal.siloChoiceIndex = 0;
                                g_lineModal.siloChoiceClicked = false;
                                g_lineModal.detectedSystem = crossingDetectedSystem;
                                g_lineModal.colorIndex = 1;
                                SystemColorShades shades = GetSystemColorShades(crossingDetectedSystem);
                                g_lineModal.selectedColor = shades.colors[1];
                                DebugLogFormat("LINE_COLOR: NO CONTINUE - crossing has %d stations with valid new color, showing Establish modal", crossingStations);
                            }
                        }
                    }
                } else {
                    DebugLog("LINE_COLOR: SKIP - matchingCid not found or newPlatforms+junctions empty (component key may have changed)");
                }
            } else {
                DebugLogFormat("LINE_COLOR: SKIP - invalid targetLineId=%d", g_lineModal.targetLineId);
            }
            // Only clear state if we didn't transition to EstablishLine for crossing naming/coloring
            if (g_lineModal.state != LineModalState::EstablishLine)
                g_lineModal.state = LineModalState::None;
            g_lineModal.cancelClicked = false;
        }
        
        // Update lines when components merge (even if modal wasn't shown)
        // This ensures lines stay synchronized with component changes
        // Rule: track stays neutral until connected between at least two stations - only sync when component has 2+ stations
        // When we just created a crossing line (NO CONTINUE), don't merge new platforms into the established line
        for (Line& line : g_lines) {
            int li = (int)(&line - g_lines.data());
            int matchingCid = -1;
            for (int cid = 0; cid < (int)stationCompKey.size(); cid++) {
                for (int pi : line.platformIndices) {
                    if (pi < (int)stationCompId.size() && stationCompId[pi] == cid) {
                        matchingCid = cid;
                        break;
                    }
                }
                if (matchingCid >= 0) break;
            }
            
            if (matchingCid >= 0) {
                std::set<long long> uniqueStationKeys;
                for (int idx : stationMembers[matchingCid]) {
                    if (idx >= 0 && idx < (int)g_placedPlatforms.size() && g_placedPlatforms[idx].isStation
                        && g_placedPlatforms[idx].stationPart == 3)
                        uniqueStationKeys.insert(MakePositionKey(g_placedPlatforms[idx].position.x, g_placedPlatforms[idx].position.z));
                }
                if ((int)uniqueStationKeys.size() < 2) continue;
                line.componentKeys.clear();
                line.componentKeys.insert(stationCompKey[matchingCid]);
                
                // Rule for ALL colours: if this line previously declined to merge with this component (NO CONTINUE),
                // never add the crossing line's platforms to it - only keep platforms already in this line.
                // Crossing lines (created via NO CONTINUE) also restrict: they only keep new track + junctions, never the established line's full track.
                long long compKey = stationCompKey[matchingCid];
                bool lineDeclinedThisComponent = (line.declinedComponentKeys.find(compKey) != line.declinedComponentKeys.end());
                bool lineDeclinedThisComponentBySeed = false;
                if (!line.declinedBranchPlatformKeys.empty()) {
                    for (int idx : stationMembers[matchingCid]) {
                        if (idx < 0 || idx >= (int)g_placedPlatforms.size()) continue;
                        const Vector3& pos = g_placedPlatforms[idx].position;
                        long long posKey = MakePositionKey(pos.x, pos.z);
                        if (line.declinedBranchPlatformKeys.find(posKey) != line.declinedBranchPlatformKeys.end()) {
                            lineDeclinedThisComponentBySeed = true;
                            break;
                        }
                    }
                }
                bool addToLineModalOpenForThisLine = (g_lineModal.state == LineModalState::AddToLine && g_lineModal.targetLineId == li);
                bool restrictThisFrame = lineDeclinedThisComponent || lineDeclinedThisComponentBySeed || line.isCrossingLine || addToLineModalOpenForThisLine ||
                    (crossingNewLineIndex >= 0 && crossingTargetLineId >= 0 && li == crossingTargetLineId && crossingNewLineIndex < (int)g_lines.size());
                
                for (int pi = 0; pi < (int)g_placedPlatforms.size(); pi++) {
                    if (pi < (int)stationCompId.size() && stationCompId[pi] == matchingCid) {
                        if (g_placedPlatforms[pi].isDepot) continue;
                        // Ownership is explicit (establish/add/no-continue flows). Do not auto-claim
                        // extra platforms from merged components during per-frame sync.
                        if (line.platformIndices.find(pi) == line.platformIndices.end())
                            continue;
                        const Vector3& pos = g_placedPlatforms[pi].position;
                        long long posKey = MakePositionKey(pos.x, pos.z);
                        auto lockedIt = g_lockedBranchOwnerLineId.find(posKey);
                        if (lockedIt != g_lockedBranchOwnerLineId.end() && line.id != lockedIt->second
                            && !g_placedPlatforms[pi].isJunction) {
                            // Hard ownership lock: once crossing line is established, no other line may claim these platforms.
                            line.platformIndices.erase(pi);
                            continue;
                        }
                        bool globallyProtectedNeutralBranch =
                            (g_declinedNeutralBranchPlatformKeys.find(posKey) != g_declinedNeutralBranchPlatformKeys.end());
                        if (globallyProtectedNeutralBranch && line.platformIndices.find(pi) == line.platformIndices.end()) {
                            // A NO CONTINUE branch is marked neutral-only until explicitly established.
                            continue;
                        }
                        if (restrictThisFrame) {
                            if (line.platformIndices.find(pi) == line.platformIndices.end())
                                continue;
                        }
                        // Sync is purely a validation/pruning pass — never auto-insert.
                        // (The guard at line ~3027 already prevents reaching here for
                        //  platforms not already in the set, but being explicit is safer
                        //  after component-ID churn from demolish.)
                    }
                }

                line.stationCount = CountPhysicalStationsInLine(line, g_placedPlatforms);
            }
        }

        // Rebuild platform->line lookup so RecomputeSilosAndMarket() sees
        // the freshest line.platformIndices (line sync above may have changed them).
        // Process crossing lines FIRST, then established lines - so exclusive track (e.g. from
        // magenta cluster) keeps its crossing-line color; shared junctions get established-line color.
        g_cachedPlatformLineId.assign(g_placedPlatforms.size(), -1);
        for (int li = 0; li < (int)g_lines.size(); li++) {
            if (!g_lines[li].isCrossingLine) continue;  // Do crossing lines first
            for (int pi : g_lines[li].platformIndices) {
                if (pi >= 0 && pi < (int)g_cachedPlatformLineId.size())
                    g_cachedPlatformLineId[pi] = li;
            }
        }
        for (int li = 0; li < (int)g_lines.size(); li++) {
            if (g_lines[li].isCrossingLine) continue;   // Now do non-crossing (established) lines - overwrites shared
            for (int pi : g_lines[li].platformIndices) {
                if (pi >= 0 && pi < (int)g_cachedPlatformLineId.size())
                    g_cachedPlatformLineId[pi] = li;
            }
        }

        static int s_lineColorLogFrame = 0;
        if (crossingNewLineIndex >= 0 || (++s_lineColorLogFrame % 300) == 0 || s_lineColorLogFrame == 1) {
            int crossingCount = 0;
            for (const auto& line : g_lines) if (line.isCrossingLine) crossingCount++;
            if (crossingCount > 0) {
                DebugLogFormat("LINE_COLOR: platform->line lookup: %d lines (%d crossing), establishedLineIds=%d",
                    (int)g_lines.size(), crossingCount, (int)g_establishedLineIds.size());
                for (int li = 0; li < (int)g_lines.size(); li++) {
                    if (!g_lines[li].isCrossingLine) continue;
                    int count = 0;
                    for (int pi = 0; pi < (int)g_cachedPlatformLineId.size(); pi++) {
                        if (g_cachedPlatformLineId[pi] == li) count++;
                    }
                    bool established = (g_establishedLineIds.find(g_lines[li].id) != g_establishedLineIds.end());
                    DebugLogFormat("LINE_COLOR:   crossing line idx=%d id=%d '%s' color=(%d,%d,%d) established=%d platformsShown=%d",
                        li, g_lines[li].id, g_lines[li].name.c_str(),
                        g_lines[li].color.r, g_lines[li].color.g, g_lines[li].color.b,
                        established ? 1 : 0, count);
                }
            }
        }

        // Deterministic market/silo state is always derived from current map and line state.
        int prevSiloCounts[7];
        for (int i = 0; i < 7; i++) prevSiloCounts[i] = g_previousSiloCountBySystem[i];
        RecomputeSilosAndMarket();

        // If a silo type just appeared (0 -> >0), show the announcement modal (unless another modal is open)
        if (!g_siloAnnounceModal.open && g_lineModal.state == LineModalState::None && !g_stockModal.open) {
            for (int sys = 0; sys < 7; sys++) {
                if (prevSiloCounts[sys] == 0 && g_siloCountBySystem[sys] > 0) {
                    g_siloAnnounceModal.open = true;
                    g_siloAnnounceModal.system = sys;
                    g_siloAnnounceModal.framesOpen = 0;
                    g_siloAnnounceModal.gotItClicked = false;
                    break;
                }
            }
        }
        for (int i = 0; i < 7; i++) g_previousSiloCountBySystem[i] = g_siloCountBySystem[i];

        // Use cached station prime / depot adjacency data
        const std::vector<std::vector<int>>& stationPrimePlatformIdx = g_cachedStationPrimePlatformIdx;
        const std::vector<std::vector<Vector3>>& stationPrimePos = g_cachedStationPrimePos;
        const std::vector<char>& stationHasAdjacentDepot = g_cachedStationHasAdjacentDepot;

        const long long kNoStation = (long long)0x7fffffffffffffffLL;

        // Build per-physical-station zones by BFS among station tiles only (not through track).
        // Station-Track-Station produces TWO separate zones, each covering exactly one placed station.
        // Each zone is one continuous bounding box â€” one shape, one hotspot.
        struct StationZone {
            float minX, maxX, minZ, maxZ;
            long long key;
            std::vector<int> memberIndices;
        };
        std::vector<StationZone> stationZones;
        {
            const float halfGrid = g_gridSpacing * 0.5f;
            std::vector<char> zoneVisited(g_placedPlatforms.size(), 0);
            for (int i = 0; i < (int)g_placedPlatforms.size(); i++) {
                const auto& p = g_placedPlatforms[i];
                if (p.isDepot || !p.isStation || zoneVisited[i]) continue;

                StationZone zone;
                zone.minX = 1e30f; zone.maxX = -1e30f;
                zone.minZ = 1e30f; zone.maxZ = -1e30f;
                zone.key = (long long)0x7fffffffffffffffLL;

                std::vector<int> q;
                q.push_back(i);
                zoneVisited[i] = 1;

                while (!q.empty()) {
                    int cur = q.back();
                    q.pop_back();
                    zone.memberIndices.push_back(cur);
                    const auto& cp = g_placedPlatforms[cur];
                    if (cp.position.x < zone.minX) zone.minX = cp.position.x;
                    if (cp.position.x > zone.maxX) zone.maxX = cp.position.x;
                    if (cp.position.z < zone.minZ) zone.minZ = cp.position.z;
                    if (cp.position.z > zone.maxZ) zone.maxZ = cp.position.z;
                    long long k = MakePositionKey(cp.position.x, cp.position.z);
                    if (k < zone.key) zone.key = k;

                    for (int j = 0; j < (int)g_placedPlatforms.size(); j++) {
                        if (zoneVisited[j]) continue;
                        const auto& jp = g_placedPlatforms[j];
                        if (jp.isDepot || !jp.isStation) continue;
                        if (ArePlatformsAdjacent(cp.position, jp.position, g_gridSpacing)) {
                            zoneVisited[j] = 1;
                            q.push_back(j);
                        }
                    }
                }
                zone.minX -= halfGrid; zone.maxX += halfGrid;
                zone.minZ -= halfGrid; zone.maxZ += halfGrid;
                stationZones.push_back(std::move(zone));
            }
        }

        auto IsPointInStationZone = [&](float px, float pz, int zid) -> bool {
            const StationZone& z = stationZones[zid];
            return px >= z.minX && px <= z.maxX && pz >= z.minZ && pz <= z.maxZ;
        };

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
            
            // Dwell mode: pause train at station
            if (train.isDwelling) {
                train.dwellTimer -= scaledDeltaTime;
                if (train.dwellTimer <= 0.0f) {
                    train.isDwelling = false;
                    train.direction = train.savedDirection;
                }
                PathPoint centerPoint = GetPathPoint(train.path, train.pathProgress);
                train.position = centerPoint.position;
                continue;
            }

            // Infrastructure pause: train is stationary due to line demolish
            if (train.isPaused) {
                if (!train.path.empty()) {
                    PathPoint pt = GetPathPoint(train.path, train.pathProgress);
                    train.position = pt.position;
                }
                continue;
            }

            // Jam timer countdown
            if (train.isJammed) {
                train.jamTimer -= scaledDeltaTime;
                if (train.jamTimer <= 0.0f) {
                    train.isJammed = false;
                    train.direction = -train.savedDirection;
                    AppendTerminalMessage("JAM CLEARED - TRAIN REVERSING");
                }
                PathPoint centerPoint = GetPathPoint(train.path, train.pathProgress);
                train.position = centerPoint.position;
                continue;
            }

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
                static std::unordered_map<int, bool> s_loggedStopped;
                if (s_loggedStopped.find(train.id) == s_loggedStopped.end()) {
                    s_loggedStopped[train.id] = true;
                    DebugLogFormat("TRAIN_DEBUG: Train id=%d STOPPED (path too short: min=%.1f max=%.1f pathLen=%.1f)",
                        train.id, minProgress, maxProgress, train.pathLength);
                }
            } else {
                if (isLoop) {
                    // Closed loop: wrap around instead of reversing
                    train.pathProgress = WrapDistance(train.pathProgress, train.pathLength);
                } else {
                    // Open path: reverse direction only at true ends (dead-ends)
                    float oldDir = train.direction;
                    if (train.pathProgress > maxProgress) {
                        train.pathProgress = maxProgress;
                        train.direction = -1.0f;
                        DebugLogFormat("TRAIN_DEBUG: Train id=%d REVERSED at max progress=%.1f (open path end) dir %.0f->-1",
                            train.id, maxProgress, oldDir);
                    } else if (train.pathProgress < minProgress) {
                        train.pathProgress = minProgress;
                        train.direction = 1.0f;
                        DebugLogFormat("TRAIN_DEBUG: Train id=%d REVERSED at min progress=%.1f (open path start) dir %.0f->1",
                            train.id, minProgress, oldDir);
                    }
                }
            }
            
            // Update position (center point of the train)
            PathPoint centerPoint = GetPathPoint(train.path, train.pathProgress);
            train.position = centerPoint.position;

            // Throttled status log (~every 2s per train) for movement tracking
            {
                static std::unordered_map<int, double> s_trainLastLogTime;
                double now = GetTime();
                double& last = s_trainLastLogTime[train.id];
                if (now - last >= 2.0) {
                    last = now;
                    DebugLogFormat("TRAIN_DEBUG: Train id=%d lineId=%d progress=%.1f/%.1f dir=%.0f pos=(%.0f,%.0f) pathPoints=%d",
                        train.id, train.lineId, train.pathProgress, train.pathLength, train.direction,
                        train.position.x, train.position.z, (int)train.path.size());
                }
            }

            // Gate opens if train HOTSPOT is inside any physical station zone.
            // Map zone back to component for gate state.
            {
                PathPoint hot = GetTrainHotspotPoint(train, g_gridSpacing);
                for (int zid = 0; zid < (int)stationZones.size(); zid++) {
                    if (IsPointInStationZone(hot.position.x, hot.position.z, zid)) {
                        if (!stationZones[zid].memberIndices.empty()) {
                            int pi0 = stationZones[zid].memberIndices[0];
                            if (pi0 < (int)stationCompId.size()) {
                                int cid = stationCompId[pi0];
                                if (cid >= 0 && cid < (int)stationGateOpen.size())
                                    stationGateOpen[cid] = 1;
                            }
                        }
                    }
                }
            }
        }

        // Update g_sysTrainMoving flags
        for (int si = 0; si < 7; si++) g_sysTrainMoving[si] = false;
        for (const auto& t : g_placedTrains) {
            if (t.path.size() < 2 || t.isPaused || t.isJammed || t.isDwelling) continue;
            if (fabsf(t.direction) > 0.0f) {
                int sys = RequiredSiloSystemForTrainType(t.type);
                if (sys >= 0 && sys < 7) g_sysTrainMoving[sys] = true;
            }
        }
        // Emit state-change terminal messages
        {
            const char* sysNames[] = {"CARGO","GREEN","MAGENTA","CYAN","ORANGE","RED","YELLOW"};
            for (int s = 0; s < 7; s++) {
                if (g_sysTrainMoving[s] != g_sysTrainWasMoving[s]) {
                    char buf[96];
                    snprintf(buf, sizeof(buf), "[%s] %s", sysNames[s], g_sysTrainMoving[s] ? "NETWORK ACTIVE" : "NETWORK IDLE");
                    AppendTerminalMessage(buf);
                    g_sysTrainWasMoving[s] = g_sysTrainMoving[s];
                }
            }
        }

        // Collision detection: check train front hotspot pairs
        {
            const float collisionDist = g_gridSpacing * 0.65f;
            for (int i = 0; i < (int)g_placedTrains.size(); i++) {
                if (g_placedTrains[i].path.size() < 2 || g_placedTrains[i].isJammed || g_placedTrains[i].isDwelling) continue;
                PathPoint hotA = GetTrainHotspotPoint(g_placedTrains[i], g_gridSpacing);
                for (int j = i + 1; j < (int)g_placedTrains.size(); j++) {
                    if (g_placedTrains[j].path.size() < 2 || g_placedTrains[j].isJammed || g_placedTrains[j].isDwelling) continue;
                    // Trains on different lines share track at junctions â€” not a collision
                    if (g_placedTrains[i].lineId != g_placedTrains[j].lineId) continue;
                    PathPoint hotB = GetTrainHotspotPoint(g_placedTrains[j], g_gridSpacing);
                    float dx = hotA.position.x - hotB.position.x;
                    float dz = hotA.position.z - hotB.position.z;
                    float dist = sqrtf(dx*dx + dz*dz);
                    if (dist < collisionDist) {
                        g_placedTrains[i].isJammed = true;
                        g_placedTrains[i].savedDirection = (g_placedTrains[i].direction != 0.0f) ? g_placedTrains[i].direction : 1.0f;
                        g_placedTrains[i].direction = 0.0f;
                        g_placedTrains[i].jamTimer = 5.0f;
                        g_placedTrains[j].isJammed = true;
                        g_placedTrains[j].savedDirection = (g_placedTrains[j].direction != 0.0f) ? g_placedTrains[j].direction : 1.0f;
                        g_placedTrains[j].direction = 0.0f;
                        g_placedTrains[j].jamTimer = 5.0f;
                        AppendTerminalMessage("!! NETWORK JAM - COLLISION DETECTED. TRAINS WILL AUTO-REVERSE.");
                    }
                }
            }
        }

        // Cargo transfer: triggers once when a train ENTERS a physical station zone.
        // Train with cargo arriving at station with free depots â†’ unload into depots.
        // Empty train arriving at station with depot cargo â†’ load from depots onto train.
        for (auto& train : g_placedTrains) {
            if (train.type != PlacedTrain::TrainType::Cargo || train.cargoTrailers <= 0) continue;
            if (train.path.size() < 2) continue;

            PathPoint hot = GetTrainHotspotPoint(train, g_gridSpacing);

            int currentZone = -1;
            for (int zid = 0; zid < (int)stationZones.size(); zid++) {
                if (IsPointInStationZone(hot.position.x, hot.position.z, zid)) { currentZone = zid; break; }
            }

            long long currentKey = (currentZone >= 0) ? stationZones[currentZone].key : kNoStation;
            long long prevKey = train.lastTransferStationKey;

            // Train just ENTERED a station zone (wasn't in this zone last frame).
            if (currentKey != kNoStation && currentKey != prevKey) {
                // Dwell: check per-station delay first; fall back to the train's own dwell mode.
                // Per-station delay (stationDelayMode on any member tile) overrides train dwell when non-zero.
                int stationDelay = 0;  // 0=use train's own dwell, 1=short(2s), 2=long(10s)
                for (int si : stationZones[currentZone].memberIndices) {
                    if (si >= 0 && si < (int)g_placedPlatforms.size() && g_placedPlatforms[si].isStation) {
                        if (g_placedPlatforms[si].stationDelayMode != 0) { stationDelay = g_placedPlatforms[si].stationDelayMode; break; }
                    }
                }
                bool shouldDwell = false;
                float dwellSecs = 0.0f;
                if (stationDelay == 1) { shouldDwell = true; dwellSecs = 2.0f; }
                else if (stationDelay == 2) { shouldDwell = true; dwellSecs = 10.0f; }
                else if (train.dwellMode == PlacedTrain::DwellMode::SHORT_WAIT) { shouldDwell = true; dwellSecs = 2.0f; }
                else if (train.dwellMode == PlacedTrain::DwellMode::LONG_WAIT)  { shouldDwell = true; dwellSecs = 10.0f; }
                if (shouldDwell && !train.isDwelling) {
                    train.savedDirection = (train.direction != 0.0f) ? train.direction : 1.0f;
                    train.direction = 0.0f;
                    train.isDwelling = true;
                    train.dwellTimer = dwellSecs;
                }
                int startDepotIdx = -1;
                for (int di = 0; di < (int)g_placedPlatforms.size(); di++) {
                    if (!g_placedPlatforms[di].isDepot) continue;
                    for (int si : stationZones[currentZone].memberIndices) {
                        if (ArePlatformsAdjacent(g_placedPlatforms[di].position, g_placedPlatforms[si].position, g_gridSpacing)) { startDepotIdx = di; break; }
                    }
                    if (startDepotIdx >= 0) break;
                }

                if (startDepotIdx >= 0) {
                    std::vector<int> cluster = GetDepotClusterIndices(g_placedPlatforms, startDepotIdx, g_gridSpacing);
                    if (!cluster.empty()) {
                        int clusterCargo = GetClusterCargoTotal(g_placedPlatforms, cluster);
                        int clusterCap = GetClusterCapacityTotal(cluster);
                        int clusterFree = clusterCap - clusterCargo;

                        int trainCap = train.cargoTrailers * 2;
                        train.cargoTotal = Clamp(train.cargoTotal, 0, trainCap);

                        if (train.cargoTotal > 0 && clusterFree > 0) {
                            int drop = std::min(train.cargoTotal, clusterFree);
                            AddCargoToCluster(g_placedPlatforms, cluster, drop);
                            train.cargoTotal -= drop;
                        } else if (train.cargoTotal == 0 && clusterCargo > 0) {
                            int taken = RemoveCargoFromCluster(g_placedPlatforms, cluster, std::min(trainCap, clusterCargo));
                            train.cargoTotal = taken;
                        }
                    }
                }
            }

            train.lastTransferStationKey = currentKey;
        }
        
        // Update particles
        UpdateBuildParticles(deltaTime);
        g_factorySmokeSpawnTimer += deltaTime;
        if (g_factorySmokeSpawnTimer >= 0.25f) {
            g_factorySmokeSpawnTimer = 0.0f;
            for (const auto& f : g_placedFactories) {
                SpawnFactorySmoke(f.position, g_gridSpacing);
            }
        }
        UpdateFactorySmoke(deltaTime);
        
        // Update ticker
        UpdateTicker(deltaTime);
        
        // Update terminal
        UpdateTerminal(deltaTime);
        if (g_junctionSetupBadgeTimer > 0.0f) {
            g_junctionSetupBadgeTimer -= deltaTime;
            if (g_junctionSetupBadgeTimer <= 0.0f) {
                g_junctionSetupBadgeTimer = 0.0f;
                g_junctionSetupTrainId = -1;
            }
        }
        
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
            g_debugRenderStage = 3;
            BeginMode2D(g_mapCamera);

            // Draw grid: inner dark red, outer coastal ring dark blue
            Color mapGridInner = (Color){ 80, 0, 0, 255 };
            Color mapGridOuter = (Color){ 40, 40, 40, 255 };

            for (float z = -g_gridExtentOuter; z <= g_gridExtentOuter + 0.01f; z += g_gridSpacing) {
                bool zInner = (z >= -g_gridExtent - 0.01f && z <= g_gridExtent + 0.01f);
                if (zInner) {
                    DrawLineV(WorldToMap((Vector3){ -g_gridExtentOuter, 0.0f, z }), WorldToMap((Vector3){ -g_gridExtent, 0.0f, z }), mapGridOuter);
                    DrawLineV(WorldToMap((Vector3){ -g_gridExtent, 0.0f, z }), WorldToMap((Vector3){ g_gridExtent, 0.0f, z }), mapGridInner);
                    DrawLineV(WorldToMap((Vector3){ g_gridExtent, 0.0f, z }), WorldToMap((Vector3){ g_gridExtentOuter, 0.0f, z }), mapGridOuter);
                } else {
                    DrawLineV(WorldToMap((Vector3){ -g_gridExtentOuter, 0.0f, z }), WorldToMap((Vector3){ g_gridExtentOuter, 0.0f, z }), mapGridOuter);
                }
            }
            for (float x = -g_gridExtentOuter; x <= g_gridExtentOuter + 0.01f; x += g_gridSpacing) {
                bool xInner = (x >= -g_gridExtent - 0.01f && x <= g_gridExtent + 0.01f);
                if (xInner) {
                    DrawLineV(WorldToMap((Vector3){ x, 0.0f, -g_gridExtentOuter }), WorldToMap((Vector3){ x, 0.0f, -g_gridExtent }), mapGridOuter);
                    DrawLineV(WorldToMap((Vector3){ x, 0.0f, -g_gridExtent }), WorldToMap((Vector3){ x, 0.0f, g_gridExtent }), mapGridInner);
                    DrawLineV(WorldToMap((Vector3){ x, 0.0f, g_gridExtent }), WorldToMap((Vector3){ x, 0.0f, g_gridExtentOuter }), mapGridOuter);
                } else {
                    DrawLineV(WorldToMap((Vector3){ x, 0.0f, -g_gridExtentOuter }), WorldToMap((Vector3){ x, 0.0f, g_gridExtentOuter }), mapGridOuter);
                }
            }

            // Buildings (includes cluster buildings on inner edge)
            for (const auto& building : g_buildings) {
                Vector2 p = WorldToMap(building.position);
                Rectangle r = { p.x - building.size.x * 0.5f, p.y - building.size.z * 0.5f, building.size.x, building.size.z };
                DrawRectangleRec(r, AddColor(MulColor(building.color, brightness), nightBlue));
            }

            // Platforms (top-down squares)
            for (int pi = 0; pi < (int)g_placedPlatforms.size(); pi++) {
                const auto& platform = g_placedPlatforms[pi];
                PlatformType pType = (pi < (int)g_cachedPlatformTypes.size())
                    ? (PlatformType)g_cachedPlatformTypes[pi]
                    : GetPlatformType(platform.position, g_placedPlatforms, g_gridSpacing);
                Color c;
                if (platform.isDepot) {
                    c = AddColor(MulColor((Color){ 160, 160, 160, 220 }, brightness), nightBlue);
                } else if (pType == PlatformType::Points) {
                    c = g_pointsColorEff;
                } else {
                    int lineIndex = (pi < (int)g_cachedPlatformLineId.size()) ? g_cachedPlatformLineId[pi] : -1;
                    bool lineIsEstablished = (lineIndex >= 0 && lineIndex < (int)g_lines.size() &&
                        g_establishedLineIds.find(g_lines[lineIndex].id) != g_establishedLineIds.end());

                    if (lineIsEstablished) {
                        // Use line color - adjust brightness based on platform type
                        const Line& line = g_lines[lineIndex];
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
                    // Draw junction "through" direction (active pair) on map
                    DrawJunctionOnMap(platform.position, g_placedPlatforms, g_gridSpacing, g_selectedTrainIndex, (float)GetTime());
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

            // Bureaus (2x2 footprint, color matches established line)
            for (int bi = 0; bi < (int)g_placedBureaus.size(); bi++) {
                const auto& b = g_placedBureaus[bi];
                Vector2 p = WorldToMap(b.position);
                float half = g_gridSpacing * 1.0f;
                Rectangle r = { p.x - half, p.y - half, half * 2.0f, half * 2.0f };
                Color bc = (Color){ 0, 255, 255, 204 };
                int li = (bi < (int)g_cachedBureauLineId.size()) ? g_cachedBureauLineId[bi] : -1;
                if (li >= 0 && li < (int)g_lines.size()) {
                    bc = g_lines[li].color;
                    bc.a = 204;
                }
                Color outline = MulColor(bc, 0.8f);
                outline.a = 220;
                DrawRectangleRec(r, bc);
                DrawRectangleLinesEx(r, 2.0f, outline);
            }

            // Trains
            float realTime = (float)GetTime(); // Real time for pulsing (ignores game speed/pause)
            for (size_t i = 0; i < g_placedTrains.size(); i++) {
                Color trainC;
                if (g_placedTrains[i].isPaused) {
                    // Paused (infrastructure reset): render gray with slow blink
                    float blink = (sinf(realTime * 2.0f) + 1.0f) * 0.5f; // 0..1
                    unsigned char alpha = (unsigned char)(120 + blink * 80);
                    trainC = (Color){128, 128, 128, alpha};
                } else if (g_placedTrains[i].type == PlacedTrain::TrainType::Cargo) {
                    trainC = (Color){ 0, 255, 255, 240 };  // Cargo = cyan on map
                } else {
                    trainC = GetTrainColorForType(g_placedTrains[i].type, 1.0f);
                    trainC.a = 220;
                }
                float trainBrightness = 1.0f;
                if (!g_placedTrains[i].isPaused && (int)i == g_selectedTrainIndex) {
                    trainC = (Color){ trainC.r, trainC.g, trainC.b, 240 };  // Brighter when selected
                    float pulse = (sinf(realTime * 5.0f) + 1.0f) / 2.0f;
                    trainBrightness = 0.7f + pulse * 1.6f;
                }
                DrawTrainOnMap(g_placedTrains[i], g_gridSpacing, trainC, trainBrightness);
            }

            // Origin marker
            DrawCircleV({0.0f, 0.0f}, 0.35f, (Color){ 255, 255, 255, 200 });

            EndMode2D();

            // Draw UI Overlay first (before all text)
            DrawUIOverlay();
            
            // Now draw all text on top of UI overlay
            float fontSize = GetScaledFontSize(BASE_FONT_SIZE);
            float fontSizeLarge = GetScaledFontSize(BASE_FONT_SIZE_LARGE);
            // Map mode text removed - controls now shown in ticker
            
            // Draw scrolling ticker with game tips and controls
            DrawTicker();
            // Per-train junction setup helper badge for newly placed trains.
            if (g_junctionSetupBadgeTimer > 0.0f
                && g_junctionSetupTrainId >= 0
                && g_selectedTrainIndex >= 0
                && g_selectedTrainIndex < (int)g_placedTrains.size()
                && g_placedTrains[g_selectedTrainIndex].id == g_junctionSetupTrainId) {
                const float pulse01 = (sinf((float)GetTime() * 6.0f) + 1.0f) * 0.5f;
                Color badgeColor = {
                    (unsigned char)(160 + pulse01 * 95.0f),
                    255,
                    255,
                    255
                };
                char badgeBuf[160];
                snprintf(badgeBuf, sizeof(badgeBuf), "JUNCTION SETUP MODE (TRAIN %d)", g_junctionSetupTrainId);
                DrawTextEx(gameFont, badgeBuf, (Vector2){(float)g_renderWidth * 0.06f, (float)g_renderHeight * 0.92f}, fontSizeLarge, 0.0f, badgeColor);
            }
            
            // Display mouse position as percentages in map mode
            Vector2 mousePos = CustomGetMousePosition();
            float mouseXPercent = (mousePos.x / (float)g_renderWidth) * 100.0f;
            float mouseYPercent = (mousePos.y / (float)g_renderHeight) * 100.0f;
            char mouseCoordText[64];
            snprintf(mouseCoordText, sizeof(mouseCoordText), "MOUSE: X:%.1f%% Y:%.1f%%", mouseXPercent, mouseYPercent);
            DrawTextEx(gameFont, mouseCoordText, (Vector2){(float)(g_renderWidth - 270), 10}, fontSizeLarge, 0.0f, WHITE);
            
            // Draw scanline overlay
            DrawScanlines();

            // Render-order contract: modals must draw second-to-last and cursor must draw last.
            // Keep this order in sync with the 3D branch below.
            DrawStationModal(g_stationModal, g_renderWidth, g_renderHeight);
            DrawLineModal(g_lineModal, g_lines, g_renderWidth, g_renderHeight);
            DrawJunctionModal(g_junctionModal, g_renderWidth, g_renderHeight);
            DrawSiloAnnounceModal(g_siloAnnounceModal, g_renderWidth, g_renderHeight);
            DrawStockCommoditiesModal(g_stockModal, g_renderWidth, g_renderHeight);
            DrawDemolishConfirmModal(g_demolishConfirmModal, g_renderWidth, g_renderHeight);
            DrawPausedTrainDeleteModal(g_pausedTrainDeleteModal, g_renderWidth, g_renderHeight);
            DrawJunctionConfigModal(g_junctionConfigModal, g_renderWidth, g_renderHeight);
            DrawQuitConfirmModal(g_quitConfirmModal, g_renderWidth, g_renderHeight);
            DrawYear5WarningModal();
            DrawIntroModal();
            DrawHelpModal();

            // Handle modal dismiss/close after drawing modal UI this frame.
            if (g_stationModal.confirmClicked) CommitStationModal(g_stationModal); // also calls InvalidatePlatformCaches
            else if (g_stationModal.cancelClicked) CancelStationModal(g_stationModal);
            if (g_siloAnnounceModal.gotItClicked) {
                int sys = g_siloAnnounceModal.system;
                g_siloAnnounceModal.open = false;
                g_siloAnnounceModal.gotItClicked = false;
                if (g_sfxSiloBuilt.frameCount > 0) PlaySound(g_sfxSiloBuilt);
                EnterCyberTrainCam(sys);
            }
            if (g_stockModal.closeClicked) {
                g_stockModal.open = false;
                g_stockModal.closeClicked = false;
            }
            if (g_demolishConfirmModal.confirmClicked) {
                ExecuteDemolishStationAndLine();  // also clears modes and re-enables demolish
            } else if (g_demolishConfirmModal.cancelClicked) {
                g_demolishConfirmModal.open = false;
                g_demolishConfirmModal.cancelClicked = false;
                g_demolishConfirmModalOpen = false;
                ClearAllPlacementModes();
                g_demolishMode = true;
            }
            if (g_pausedTrainDeleteModal.confirmClicked) {
                int ti = g_pausedTrainDeleteModal.trainIndex;
                if (ti >= 0 && ti < (int)g_placedTrains.size()) {
                    if (g_selectedTrainIndex == ti) g_selectedTrainIndex = -1;
                    else if (g_selectedTrainIndex > ti) g_selectedTrainIndex--;
                    g_placedTrains.erase(g_placedTrains.begin() + ti);
                    AddTerminalMessage("PAUSED TRAIN DESTROYED - 100 CREDITS");
                    if (g_playerCredits >= 100) g_playerCredits -= 100;
                }
                g_pausedTrainDeleteModal.open = false;
                g_pausedTrainDeleteModal.confirmClicked = false;
                g_pausedTrainDeleteModal.trainIndex = -1;
            } else if (g_pausedTrainDeleteModal.cancelClicked) {
                g_pausedTrainDeleteModal.open = false;
                g_pausedTrainDeleteModal.cancelClicked = false;
                g_pausedTrainDeleteModal.trainIndex = -1;
            }
            // Junction config modal: handle SWITCH and DONE
            if (g_junctionConfigModal.switchClicked) {
                g_junctionConfigModal.switchClicked = false;
                int slot = g_junctionConfigModal.selectedTrainSlot;
                if (slot >= 0 && slot < (int)g_junctionConfigModal.trainIndices.size()) {
                    int ti = g_junctionConfigModal.trainIndices[slot];
                    if (ti >= 0 && ti < (int)g_placedTrains.size()) {
                        PlacedTrain& train = g_placedTrains[ti];
                        std::vector<Vector3> adj = GetSortedAdjacentPositions(g_junctionConfigModal.junctionPos, g_placedPlatforms, g_gridSpacing);
                        int numPairs = NumJunctionPairs((int)adj.size());
                        if (numPairs > 0) {
                            int cur = train.GetJunctionSetting(g_junctionConfigModal.junctionPos.x, g_junctionConfigModal.junctionPos.z, &adj);
                            if (cur < 0) cur = DefaultJunctionPairIndex(g_junctionConfigModal.junctionPos, adj);
                            int next = (cur + 1) % numPairs;
                            train.SetJunctionSetting(g_junctionConfigModal.junctionPos.x, g_junctionConfigModal.junctionPos.z, next, &adj);
                            if (!train.path.empty())
                                (void)RebuildTrainPath(train, g_placedPlatforms, g_gridSpacing);
                        }
                    }
                }
            }
            if (g_junctionConfigModal.doneClicked) {
                g_junctionConfigModal = {};
                g_junctionConfigModalOpen = false;
                BlockMouseClicksAfterModalClose();
            }
            if (g_quitConfirmModal.yesClicked) {
                g_quitConfirmModal = {};
                g_quitConfirmModalOpen = false;
                RestartToSplashAfterGameOver();
            }
            if (g_quitConfirmModal.noClicked) {
                g_quitConfirmModal = {};
                g_quitConfirmModalOpen = false;
            }

            // Gamma overlay
            DrawGammaOverlay();

            // Options screen overlay
            if (g_optionsScreen == OptionsScreen::Visible) {
                DrawOptionsScreen();
            }

            // Draw cursor last so it's always on top
            DrawCustomCursor();

            if (!g_standalone_mode && g_framebuffer_initialized) {
                EndTextureMode();
            } else {
                EndDrawing();
            }
            return; // skip 3D draw while in map mode
        }
        
        // Begin 3D mode
        g_debugRenderStage = 4;
        BeginMode3D(g_camera);
        
        // Draw grid at sea level (y=0): inner grid dark red, outer coastal ring dark blue
        Color gridColorInner = AddColor(MulColor((Color){ 139, 0, 0, 255 }, brightness), nightBlue);
        Color gridColorOuter = AddColor(MulColor((Color){ 60, 60, 60, 255 }, brightness), nightBlue);
        
        for (float z = -g_gridExtentOuter; z <= g_gridExtentOuter + 0.01f; z += g_gridSpacing) {
            bool zInner = (z >= -g_gridExtent - 0.01f && z <= g_gridExtent + 0.01f);
            if (zInner) {
                DrawLine3D((Vector3){ -g_gridExtentOuter, 0.0f, z }, (Vector3){ -g_gridExtent, 0.0f, z }, gridColorOuter);
                DrawLine3D((Vector3){ -g_gridExtent, 0.0f, z }, (Vector3){ g_gridExtent, 0.0f, z }, gridColorInner);
                DrawLine3D((Vector3){ g_gridExtent, 0.0f, z }, (Vector3){ g_gridExtentOuter, 0.0f, z }, gridColorOuter);
            } else {
                DrawLine3D((Vector3){ -g_gridExtentOuter, 0.0f, z }, (Vector3){ g_gridExtentOuter, 0.0f, z }, gridColorOuter);
            }
        }
        
        for (float x = -g_gridExtentOuter; x <= g_gridExtentOuter + 0.01f; x += g_gridSpacing) {
            bool xInner = (x >= -g_gridExtent - 0.01f && x <= g_gridExtent + 0.01f);
            if (xInner) {
                DrawLine3D((Vector3){ x, 0.0f, -g_gridExtentOuter }, (Vector3){ x, 0.0f, -g_gridExtent }, gridColorOuter);
                DrawLine3D((Vector3){ x, 0.0f, -g_gridExtent }, (Vector3){ x, 0.0f, g_gridExtent }, gridColorInner);
                DrawLine3D((Vector3){ x, 0.0f, g_gridExtent }, (Vector3){ x, 0.0f, g_gridExtentOuter }, gridColorOuter);
            } else {
                DrawLine3D((Vector3){ x, 0.0f, -g_gridExtentOuter }, (Vector3){ x, 0.0f, g_gridExtentOuter }, gridColorOuter);
            }
        }

        // Highlight hovered grid cell with a short grey cube when nothing is selected
        bool nothingSelected = !g_trainPlacementMode && !g_cargoTrainPlacementMode &&
                               !g_depotPlacementMode && !g_factoryPlacementMode &&
                               !g_stationPlacementMode && !g_bureauPlacementMode &&
                               !g_demolishMode;
        if (nothingSelected && g_mouseInEffective3DArea) {
            float cubeH = g_gridSpacing * 0.03f;
            DrawCube(
                (Vector3){ g_mouseWorldPos.x, cubeH * 0.5f, g_mouseWorldPos.z },
                g_gridSpacing, cubeH, g_gridSpacing,
                (Color){ 180, 180, 180, 140 }
            );
        }

        // Draw all buildings (INNER CITY HUB skyline + colored cluster buildings on inner edge)
        for (const auto& building : g_buildings) {
            // Draw filled cube with building color
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
        
        // Draw placed bureaus (color matches established line when part of a silo)
        for (int bi = 0; bi < (int)g_placedBureaus.size(); bi++) {
            const auto& b = g_placedBureaus[bi];
            Color bureauColor = (Color){ 0, 255, 255, 200 };
            int li = (bi < (int)g_cachedBureauLineId.size()) ? g_cachedBureauLineId[bi] : -1;
            if (li >= 0 && li < (int)g_lines.size()) {
                bureauColor = g_lines[li].color;
                bureauColor.a = 200;
            }
            Color bureauColorEff = AddColor(MulColor(bureauColor, brightness), nightBlue);
            DrawBureau(b.position, g_gridSpacing, b.floors, bureauColorEff);
        }
        
        // Draw placed platforms
        bool mouseOverPlatform = false;
        int hoveredPlatformIndex = -1;
        float currentTime = (float)GetTime(); // For animation effects
        bool hasSelectedTrain = (g_selectedTrainIndex >= 0 && g_selectedTrainIndex < (int)g_placedTrains.size());
        
        for (int pi = 0; pi < (int)g_placedPlatforms.size(); pi++) {
            const auto& platform = g_placedPlatforms[pi];
            PlatformType pType = (pi < (int)g_cachedPlatformTypes.size())
                ? (PlatformType)g_cachedPlatformTypes[pi]
                : GetPlatformType(platform.position, g_placedPlatforms, g_gridSpacing);
            Color drawColor;
            
            Color basePlateOverride = {0,0,0,0};

            if (platform.isDepot) {
                drawColor = AddColor(MulColor((Color){ 160, 160, 160, 220 }, brightness), nightBlue);
            } else if (pType == PlatformType::Points) {
                drawColor = g_pointsColorEff;
            } else {
                int lineIndex = (pi < (int)g_cachedPlatformLineId.size()) ? g_cachedPlatformLineId[pi] : -1;
                bool lineIsEstablished = (lineIndex >= 0 && lineIndex < (int)g_lines.size() &&
                    g_establishedLineIds.find(g_lines[lineIndex].id) != g_establishedLineIds.end());

                if (lineIsEstablished) {
                    const Line& line = g_lines[lineIndex];
                    Color lineColorBase = line.color;
                    
                    if (platform.isStation) {
                        drawColor = g_stationColorEff;
                        Color bp = MulColor(lineColorBase, 0.9f);
                        bp.a = 230;
                        basePlateOverride = AddColor(MulColor(bp, brightness), nightBlue);
                    } else {
                        drawColor = MulColor(lineColorBase, 1.2f);
                        drawColor.a = 199;
                        drawColor = AddColor(MulColor(drawColor, brightness), nightBlue);
                    }
                } else if (platform.isStation) {
                    drawColor = g_stationColorEff;
                } else {
                    drawColor = g_platformColorEff;
                }

                static int s_drawLogCount = 0;
                if (lineIndex >= 0 && lineIndex < (int)g_lines.size() && g_lines[lineIndex].isCrossingLine && ((s_lineColorLogFrame % 300) == 1 || s_lineColorLogFrame == 1) && s_drawLogCount < 6) {
                    s_drawLogCount++;
                    DebugLogFormat("LINE_COLOR: draw pi=%d pos=(%.0f,%.0f) lineIdx=%d established=%d -> %s",
                        pi, platform.position.x, platform.position.z, lineIndex, lineIsEstablished ? 1 : 0,
                        lineIsEstablished ? "LINE_COLOR" : "DEFAULT");
                }
                if ((s_lineColorLogFrame % 300) != 1 && s_lineColorLogFrame != 1) s_drawLogCount = 0;

                // Stations NOT on an established line: pulse base plate to cluster colour
                if (!platform.isDepot && platform.isStation && !lineIsEstablished) {
                    int cx = WorldToGridCell(platform.position.x);
                    int cz = WorldToGridCell(platform.position.z);
                    ClusterType ct = GetClusterTypeForStation(cx, cz);
                    bool inActivatedCargo = IsWorldPosInActivatedCargoCluster(platform.position.x, platform.position.z);
                    if (ct != ClusterType::CARGO || inActivatedCargo) {
                        Color clusterCol = (ct != ClusterType::CARGO) ? GetClusterBuildingColor(ct) : GetActivatedCargoPulseColor();
                        clusterCol = AddColor(MulColor(clusterCol, brightness), nightBlue);
                        float pulse = (sinf(currentTime * 2.5f) + 1.0f) * 0.5f;
                        basePlateOverride = LerpColor((Color){128,128,128,179}, clusterCol, pulse);
                    }
                }
            }
            
            if (platform.isDepot) {
                DrawMaterialsDepot(platform.position, g_gridSpacing, drawColor, platform.depotCargo);
            } else {
                DrawPlatform(platform.position, g_gridSpacing, drawColor, false, basePlateOverride);
            }

            // Draw animated cyberpunk billboards on stations
            if (!platform.isDepot && platform.isStation) {
                DrawStationBillboards(platform.position, g_gridSpacing, currentTime);
            }

            
            
            // Draw visual indicators for Points-Platforms
            if (!platform.isDepot && pType == PlatformType::Points) {
                bool junctionIsSwitchable = IsJunctionSwitchable(pi);
                bool isCrossingOfTwoLines = !junctionIsSwitchable;
                int exitSetting = -1; // -1 = use deterministic default pair
                if (hasSelectedTrain && junctionIsSwitchable) {
                    std::vector<Vector3> adjacent = GetSortedAdjacentPositions(platform.position, g_placedPlatforms, g_gridSpacing);
                    exitSetting = g_placedTrains[g_selectedTrainIndex].GetJunctionSetting(platform.position.x, platform.position.z, &adjacent);
                }
                DrawPointsIndicator(platform.position, g_placedPlatforms, g_gridSpacing, currentTime, exitSetting, hasSelectedTrain && junctionIsSwitchable, isCrossingOfTwoLines);
            }
            
            // Check if mouse is over this platform for highlighting (only when in effective 3D area, not cutout)
            if (g_mouseInEffective3DArea && Vector3Distance(g_mouseWorldPos, platform.position) < 0.1f) {
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
            if (g_placedTrains[i].isPaused) {
                // Paused train: dim and slow-blink to indicate infrastructure halt
                float blink = (sinf(currentTime * 2.0f) + 1.0f) * 0.5f; // 0..1
                trainBrightness = 0.25f + blink * 0.15f; // 0.25..0.4
            } else if ((int)i == g_selectedTrainIndex) {
                // Pulse from 0.7 (-30%) to 2.3 (+230%) brightness (~1.25 seconds per cycle)
                float pulse = (sinf(currentTime * 5.0f) + 1.0f) / 2.0f; // 0 to 1
                trainBrightness = 0.7f + pulse * 1.6f; // 0.7 to 2.3
            }

            if (g_placedTrains[i].type == PlacedTrain::TrainType::Cargo) {
                DrawCargoTrain(g_placedTrains[i].path, g_placedTrains[i].pathProgress, g_gridSpacing, g_placedTrains[i].cargoTrailers, g_placedTrains[i].cargoTotal, trainBrightness);
            } else {
                DrawTrain(g_placedTrains[i].path, g_placedTrains[i].pathProgress, g_gridSpacing, trainBrightness, false, g_placedTrains[i].type);
            }
        }
        
        SetBuildStatusNone();

        // Draw preview (platform or train) at mouse position - only when in effective 3D area (not cutout)
        if (g_mouseInEffective3DArea && (IsTrackPlacementSelected() || IsPassengerTrainPlacementSelected() || g_cargoTrainPlacementMode)) {
            g_liveCostPreview[0] = '\0';  // Clear unless we set it in platform mode below
            float trainPulseToWhite = (sinf((float)GetTime() * 7.0f) + 1.0f) * 0.5f;
            // Check if valid placement location
            Vector3 pathCenter;
            bool canPlaceTrain = false;
            bool buildStatusResolved = false;
            
            // Check if the platform under mouse is a station
            const PlacedPlatform* targetPlatform = nullptr;
            for (const auto& p : g_placedPlatforms) {
                if (Vector3Distance(g_mouseWorldPos, p.position) < 0.1f) {
                    targetPlatform = &p;
                    break;
                }
            }

            // Train preview over station - only when NOT dragging track (avoid showing train while building track)
            if (targetPlatform && targetPlatform->isStation && g_placedPlatforms.size() >= 4 && !g_platformDragActive
                && (IsPassengerTrainPlacementSelected() || g_cargoTrainPlacementMode)) {
                if (CheckConnectedPlatforms(g_mouseWorldPos, g_placedPlatforms, g_gridSpacing, pathCenter)) {
                    int previewPlatformIdx = -1;
                    for (int tpi = 0; tpi < (int)g_placedPlatforms.size(); tpi++) {
                        if (Vector3Distance(g_placedPlatforms[tpi].position, targetPlatform->position) < 0.1f) {
                            previewPlatformIdx = tpi;
                            break;
                        }
                    }
                    int previewLineIdx = GetLineIndexFromPlatformIndex(previewPlatformIdx);
                    const std::set<int>* previewLineFilter = (previewLineIdx >= 0 && previewLineIdx < (int)g_lines.size())
                        ? &g_lines[previewLineIdx].platformIndices : nullptr;
                    PlacedTrain::TrainType previewType = PlacedTrain::TrainType::Cargo;
                    if (g_cargoTrainPlacementMode) {
                        previewType = PlacedTrain::TrainType::Cargo;
                    } else {
                        int idx = (g_trainColorIndex >= 0 && g_trainColorIndex <= 5) ? g_trainColorIndex : 0;
                        previewType = (PlacedTrain::TrainType)((int)PlacedTrain::TrainType::Passenger + idx);
                        if (previewType > PlacedTrain::TrainType::Yellow) previewType = PlacedTrain::TrainType::Passenger;
                    }
                    std::vector<Vector3> path = BuildPlatformPath(g_mouseWorldPos, g_placedPlatforms, g_gridSpacing, nullptr, previewLineFilter);
                    if (path.size() >= 4) {
                        const char* blockedReason = nullptr;
                        canPlaceTrain = DoesEstablishedLineMatchTrainType(previewLineIdx, previewType);
                        if (!canPlaceTrain) blockedReason = "SYS != EL";
                        int previewBuildCost = GetTrainBuildCost(previewType, g_cargoTrainPlacementMode ? g_cargoPlacementTrailers : 1);
                        if (canPlaceTrain && g_playerCredits < previewBuildCost) {
                            canPlaceTrain = false;
                            blockedReason = "NO CR";
                        }
                        if (canPlaceTrain) SetBuildStatusPossible();
                        else SetBuildStatusBlocked(blockedReason);
                        buildStatusResolved = true;
                        // For preview, we need to build a path with Y positions
                        std::vector<Vector3> previewPath;
                        for (const auto& pos : path) {
                            previewPath.push_back({ pos.x, GetPlatformTopY(pos.y, g_gridSpacing), pos.z });
                        }
                        // Preview should match placement rule: centered on the station platform under the cursor
                        float previewProgress = GetClosestDistanceAlongPath(previewPath, (Vector3){ targetPlatform->position.x, GetPlatformTopY(targetPlatform->position.y, g_gridSpacing), targetPlatform->position.z });
                        if (g_cargoTrainPlacementMode) {
                            // Preview cargo as fully loaded so it's obvious it's a cargo train
                            DrawCargoTrain(previewPath, previewProgress, g_gridSpacing, g_cargoPlacementTrailers, g_cargoPlacementTrailers * 2, 1.0f, !canPlaceTrain, trainPulseToWhite);
                        } else {
                            DrawTrain(previewPath, previewProgress, g_gridSpacing, 1.0f, !canPlaceTrain, previewType, trainPulseToWhite);
                        }
                    } else {
                        SetBuildStatusBlocked("REQ EL ST");
                        buildStatusResolved = true;
                    }
                } else {
                    SetBuildStatusBlocked("REQ CONNECTED ST");
                    buildStatusResolved = true;
                }
            }
            
            // When dragging platform line: always show preview line (extends/reduces as you move)
            if (g_platformDragActive && IsTrackPlacementSelected() && CustomIsMouseButtonDown(MOUSE_BUTTON_LEFT)) {
                std::vector<Vector3> lineCells;
                { Vector3 cf = { g_camera.target.x - g_camera.position.x, 0.0f, g_camera.target.z - g_camera.position.z };
                  float cl = sqrtf(cf.x*cf.x + cf.z*cf.z); if (cl > 0.001f) { cf.x /= cl; cf.z /= cl; }
                  GetGridCellsLShape(g_platformDragStartPos, g_mouseWorldPos, g_gridSpacing, cf, lineCells); }
                Color platformColorEff = AddColor(MulColor(g_platformColor, brightness), nightBlue);
                int creditsRemaining = g_playerCredits;
                for (const Vector3& pos : lineCells) {
                    bool canPlace = true;
                    const char* blockedReason = nullptr;
                    if (!IsWithinGridBounds(pos.x, pos.z, g_gridSpacing * 0.5f)) canPlace = false;
                    if (!canPlace) blockedReason = "OOB";
                    Building testBuilding;
                    testBuilding.position = pos;
                    testBuilding.size = { g_gridSpacing, g_gridSpacing, g_gridSpacing };
                    if (overlapsWithAny(testBuilding, g_buildings)) {
                        canPlace = false;
                        blockedReason = "OVR CITY";
                    }
                    for (const auto& placed : g_placedPlatforms) {
                        if (Vector3Distance(pos, placed.position) < g_gridSpacing * 0.9f) {
                            canPlace = false;
                            blockedReason = "TRK OCC";
                            break;
                        }
                    }
                    int segCost = ApplyBuildDiscount(OuterGridCost(150, pos.x, pos.z));
                    if (canPlace && creditsRemaining < segCost) {
                        canPlace = false;
                        blockedReason = "NO CR";
                    }
                    if (canPlace) creditsRemaining -= segCost;
                    Color previewColor = platformColorEff;
                    if (!canPlace) previewColor = AddColor(MulColor(GetInvalidPreviewColor(), 0.6f), nightBlue);
                    previewColor.a = (unsigned char)(previewColor.a * 0.7f);  // Slightly transparent for preview
                    DrawPlatform(pos, g_gridSpacing, previewColor, !canPlace);
                    if (!buildStatusResolved && !canPlace) {
                        SetBuildStatusBlocked(blockedReason);
                        buildStatusResolved = true;
                    }
                }
                if (!buildStatusResolved) {
                    SetBuildStatusPossible();
                    buildStatusResolved = true;
                }
            }
            // When over empty ground (and not dragging): cargo mode shows cargo train preview; platform/track mode shows platform preview
            else if (!canPlaceTrain) {
                // Slow rotation: spin the preview train around its centre at the mouse position.
                const float rotSpeed = 0.7f; // radians per second
                float rotAngle = (float)GetTime() * rotSpeed;
                float rotDirX = -sinf(rotAngle);
                float rotDirZ =  cosf(rotAngle);

                if (g_cargoTrainPlacementMode) {
                    const float carLen = g_gridSpacing * 0.8f;
                    float pathHalfLen = (1.0f + (float)g_cargoPlacementTrailers) * carLen * 0.5f;
                    float topY = GetPlatformTopY(g_mouseWorldPos.y, g_gridSpacing);
                    std::vector<Vector3> previewPath;
                    previewPath.push_back({ g_mouseWorldPos.x - rotDirX * pathHalfLen, topY, g_mouseWorldPos.z - rotDirZ * pathHalfLen });
                    previewPath.push_back({ g_mouseWorldPos.x + rotDirX * pathHalfLen, topY, g_mouseWorldPos.z + rotDirZ * pathHalfLen });
                    DrawCargoTrain(previewPath, pathHalfLen, g_gridSpacing, g_cargoPlacementTrailers, g_cargoPlacementTrailers * 2, 1.0f, true, trainPulseToWhite);
                } else if (IsPassengerTrainPlacementSelected()) {
                    const float carLen = g_gridSpacing * 0.8f;
                    float pathHalfLen = carLen * 2.0f;
                    float topY = GetPlatformTopY(g_mouseWorldPos.y, g_gridSpacing);
                    std::vector<Vector3> previewPath;
                    previewPath.push_back({ g_mouseWorldPos.x - rotDirX * pathHalfLen, topY, g_mouseWorldPos.z - rotDirZ * pathHalfLen });
                    previewPath.push_back({ g_mouseWorldPos.x + rotDirX * pathHalfLen, topY, g_mouseWorldPos.z + rotDirZ * pathHalfLen });
                    int idx = (g_trainColorIndex >= 0 && g_trainColorIndex <= 5) ? g_trainColorIndex : 0;
                    PlacedTrain::TrainType previewType = (PlacedTrain::TrainType)((int)PlacedTrain::TrainType::Passenger + idx);
                    if (previewType > PlacedTrain::TrainType::Yellow) previewType = PlacedTrain::TrainType::Passenger;
                    DrawTrain(previewPath, pathHalfLen, g_gridSpacing, 1.0f, true, previewType, trainPulseToWhite);
                } else if (IsTrackPlacementSelected()) {
                    // Platform/track mode: single platform preview (preview line is drawn above when dragging)
                    bool canPlacePlatform = true;
                    const char* blockedReason = nullptr;
                    if (!IsWithinGridBounds(g_mouseWorldPos.x, g_mouseWorldPos.z, g_gridSpacing * 0.5f)) canPlacePlatform = false;
                    if (!canPlacePlatform) blockedReason = "OOB";
                    Building testBuilding;
                    testBuilding.position = g_mouseWorldPos;
                    testBuilding.size = { g_gridSpacing, g_gridSpacing, g_gridSpacing };
                    if (overlapsWithAny(testBuilding, g_buildings)) {
                        canPlacePlatform = false;
                        blockedReason = "OVR CITY";
                    }
                    if (canPlacePlatform) {
                        for (const auto& placed : g_placedPlatforms) {
                            if (Vector3Distance(g_mouseWorldPos, placed.position) < g_gridSpacing * 0.9f) {
                                canPlacePlatform = false;
                                blockedReason = "TRK OCC";
                                break;
                            }
                        }
                    }
                    int hoverSegCost = ApplyBuildDiscount(OuterGridCost(150, g_mouseWorldPos.x, g_mouseWorldPos.z));
                    if (canPlacePlatform && g_playerCredits < hoverSegCost) {
                        canPlacePlatform = false;
                        blockedReason = "NO CR";
                    }
                    Color platformColorEff = AddColor(MulColor(g_platformColor, brightness), nightBlue);
                    DrawPlatform(g_mouseWorldPos, g_gridSpacing, platformColorEff, !canPlacePlatform);
                    // Cost preview (hover only - drag cost is set in drag block)
                    if (!g_platformDragActive && canPlacePlatform) {
                        snprintf(g_liveCostPreview, sizeof(g_liveCostPreview), "New extended network line cost: %d", hoverSegCost);
                    }
                    if (canPlacePlatform) SetBuildStatusPossible();
                    else SetBuildStatusBlocked(blockedReason);
                    buildStatusResolved = true;
                }
            }

            if (!buildStatusResolved && (IsPassengerTrainPlacementSelected() || g_cargoTrainPlacementMode)) {
                if (!targetPlatform || !targetPlatform->isStation) SetBuildStatusBlocked("REQ ST TARGET");
                else SetBuildStatusBlocked("TRAIN BLOCKED");
            }
        }
        if (!IsTrackPlacementSelected()) g_liveCostPreview[0] = '\0';  // Clear cost when not in platform mode
        if (g_mouseInEffective3DArea && g_bureauPlacementMode) {
            int selectedFloors = g_bureauFloorOptions[g_bureauFloorIndex];
            bool canPlaceBureau = true;
            const char* blockedReason = nullptr;
            if (!IsWithinGridBounds(g_mouseWorldPos.x, g_mouseWorldPos.z, g_gridSpacing * 1.0f)) {
                canPlaceBureau = false;
                blockedReason = "OOB";
            }
            float bureauHalf = g_gridSpacing * 1.0f;
            // No skyline building overlap check — bureaus can be placed next to clusters
            if (canPlaceBureau) {
                for (const auto& p : g_placedPlatforms) {
                    if (p.position.x >= g_mouseWorldPos.x - bureauHalf - 0.1f && p.position.x <= g_mouseWorldPos.x + bureauHalf + 0.1f &&
                        p.position.z >= g_mouseWorldPos.z - bureauHalf - 0.1f && p.position.z <= g_mouseWorldPos.z + bureauHalf + 0.1f) {
                        canPlaceBureau = false;
                        blockedReason = "BUR OVR TRK/ST/DEP";
                        break;
                    }
                }
            }
            if (canPlaceBureau) {
                float factoryHalf = g_gridSpacing * 2.0f;
                for (const auto& f : g_placedFactories) {
                    if (fabsf(f.position.x - g_mouseWorldPos.x) <= (factoryHalf + bureauHalf) &&
                        fabsf(f.position.z - g_mouseWorldPos.z) <= (factoryHalf + bureauHalf)) {
                        canPlaceBureau = false;
                        blockedReason = "BUR OVR FAC";
                        break;
                    }
                }
            }
            if (canPlaceBureau) {
                for (const auto& b : g_placedBureaus) {
                    if (fabsf(b.position.x - g_mouseWorldPos.x) <= (bureauHalf * 2.0f) &&
                        fabsf(b.position.z - g_mouseWorldPos.z) <= (bureauHalf * 2.0f)) {
                        canPlaceBureau = false;
                        blockedReason = "BUR OVR BUR";
                        break;
                    }
                }
            }
            int closestLineIndex = -1;
            bool innerRingOk = DetectClosestEstablishedLineForBureauInnerRing(g_mouseWorldPos, &closestLineIndex);
            if (canPlaceBureau && !innerRingOk) {
                canPlaceBureau = false;
                blockedReason = "IR REQ EL ST";
            }
            int cargoCost = ApplyOrangeBureauDiscount(GetBureauCargoCost(g_bureauFloorIndex));
            bool cargoOk = HasEnoughCargoInRadius(g_mouseWorldPos, g_placedPlatforms, g_gridSpacing, cargoCost);
            if (canPlaceBureau && !cargoOk) {
                canPlaceBureau = false;
                blockedReason = "OR REQ MAT";
            }
            int costPerFloor = GetBureauCostPerFloorForLineIndex(closestLineIndex);
            int totalCost = ApplyBuildDiscount(selectedFloors * costPerFloor);
            if (canPlaceBureau && g_playerCredits < totalCost) {
                canPlaceBureau = false;
                blockedReason = "NO CR";
            }

            Color bureauPreviewColor;
            if (canPlaceBureau) {
                Color base = (Color){ 0, 255, 255, 200 };
                if (closestLineIndex >= 0 && closestLineIndex < (int)g_lines.size()) {
                    base = g_lines[closestLineIndex].color;
                    base.a = 200;
                }
                bureauPreviewColor = AddColor(MulColor(base, brightness), nightBlue);
            } else {
                bureauPreviewColor = AddColor(MulColor(GetInvalidPreviewColor(), brightness), nightBlue);
            }
            DrawBureau(g_mouseWorldPos, g_gridSpacing, selectedFloors, bureauPreviewColor);
            if (canPlaceBureau) SetBuildStatusPossible();
            else SetBuildStatusBlocked(blockedReason);

            // Debug radius indicators
            const int segments = 48;
            float y = 0.15f;
            Color detectedLineColor = (Color){0, 255, 255, 180};
            if (closestLineIndex >= 0 && closestLineIndex < (int)g_lines.size()) {
                detectedLineColor = g_lines[closestLineIndex].color;
                detectedLineColor.a = 180;
            }
            bool bothRingRulesOk = innerRingOk && cargoOk;
            float ringPulse = 0.70f + 0.45f * ((sinf((float)GetTime() * 5.0f) + 1.0f) * 0.5f);
            Color pulsedLineColor = MulColor(detectedLineColor, ringPulse);
            pulsedLineColor.a = detectedLineColor.a;

            // Inner ring: must include at least one established-line station tile.
            {
                float r = GetBureauInnerRingRadius();
                Color ringColor = bothRingRulesOk ? pulsedLineColor : (innerRingOk ? detectedLineColor : (Color){255, 60, 60, 160});
                for (int i = 0; i < segments; i++) {
                    float a0 = (float)i / segments * 2.0f * PI;
                    float a1 = (float)(i + 1) / segments * 2.0f * PI;
                    DrawLine3D(
                        (Vector3){g_mouseWorldPos.x + cosf(a0) * r, y, g_mouseWorldPos.z + sinf(a0) * r},
                        (Vector3){g_mouseWorldPos.x + cosf(a1) * r, y, g_mouseWorldPos.z + sinf(a1) * r},
                        ringColor);
                }
            }
            // Outer ring: cargo requirement radius.
            {
                float r = g_gridSpacing * 8.0f;
                Color ringColor = bothRingRulesOk ? pulsedLineColor : (cargoOk ? detectedLineColor : (Color){255, 60, 60, 160});
                for (int i = 0; i < segments; i++) {
                    float a0 = (float)i / segments * 2.0f * PI;
                    float a1 = (float)(i + 1) / segments * 2.0f * PI;
                    DrawLine3D(
                        (Vector3){g_mouseWorldPos.x + cosf(a0) * r, y, g_mouseWorldPos.z + sinf(a0) * r},
                        (Vector3){g_mouseWorldPos.x + cosf(a1) * r, y, g_mouseWorldPos.z + sinf(a1) * r},
                        ringColor);
                }
            }
        } else if (g_mouseInEffective3DArea && g_demolishMode) {
            // Draw demolish preview (red wireframe box)
            float topY = GetPlatformTopY(g_mouseWorldPos.y, g_gridSpacing);
            float topThickness = g_gridSpacing * 0.1f;
            DrawCubeWires((Vector3){g_mouseWorldPos.x, topY, g_mouseWorldPos.z}, g_gridSpacing * 1.1f, topThickness * 2.0f, g_gridSpacing * 1.1f, RED);
        } else if (g_mouseInEffective3DArea && g_factoryPlacementMode) {
            bool canPlaceFactory = true;
            const char* blockedReason = nullptr;
            if (!IsWithinGridBounds(g_mouseWorldPos.x, g_mouseWorldPos.z, g_gridSpacing * 2.0f)) {
                canPlaceFactory = false;
                blockedReason = "OOB";
            }
            Vector3 factoryPos = g_mouseWorldPos;
            float half = g_gridSpacing * 2.0f;
            BoundingBox factoryBox = { (Vector3){ factoryPos.x - half, 0.0f, factoryPos.z - half },
                                      (Vector3){ factoryPos.x + half, g_gridSpacing * 3.0f, factoryPos.z + half } };
            for (const auto& b : g_buildings) {
                BoundingBox bb = { (Vector3){ b.position.x - b.size.x/2.0f, b.position.y - b.size.y/2.0f, b.position.z - b.size.z/2.0f },
                                 (Vector3){ b.position.x + b.size.x/2.0f, b.position.y + b.size.y/2.0f, b.position.z + b.size.z/2.0f } };
                if (CheckCollisionBoxes(factoryBox, bb)) {
                    canPlaceFactory = false;
                    blockedReason = "OVR CITY";
                    break;
                }
            }
            if (canPlaceFactory) {
                for (const auto& p : g_placedPlatforms) {
                    if (p.position.x >= factoryPos.x - half - 0.1f && p.position.x <= factoryPos.x + half + 0.1f &&
                        p.position.z >= factoryPos.z - half - 0.1f && p.position.z <= factoryPos.z + half + 0.1f) {
                        canPlaceFactory = false;
                        blockedReason = "FAC OVR TRK/ST/DEP";
                        break;
                    }
                }
            }
            if (canPlaceFactory) {
                for (const auto& f : g_placedFactories) {
                    if (fabsf(f.position.x - factoryPos.x) <= (half * 2.0f) && fabsf(f.position.z - factoryPos.z) <= (half * 2.0f)) {
                        canPlaceFactory = false;
                        blockedReason = "FAC OVR FAC";
                        break;
                    }
                }
            }
            if (canPlaceFactory && g_playerCredits < ApplyBuildDiscount(OuterGridCost(10000, g_mouseWorldPos.x, g_mouseWorldPos.z))) {
                canPlaceFactory = false;
                blockedReason = "NO CR";
            }

            Color fc = canPlaceFactory ? AddColor(MulColor((Color){ 130, 130, 130, 220 }, brightness), nightBlue) : (Color){ 0,0,0,0 };
            DrawFactory(g_mouseWorldPos, g_gridSpacing, fc, !canPlaceFactory);
            if (canPlaceFactory) SetBuildStatusPossible();
            else SetBuildStatusBlocked(blockedReason);
        } else if (g_mouseInEffective3DArea && g_depotPlacementMode) {
            bool canPlaceDepot = true;
            const char* blockedReason = nullptr;
            if (!IsWithinGridBounds(g_mouseWorldPos.x, g_mouseWorldPos.z, g_gridSpacing * 0.5f)) {
                canPlaceDepot = false;
                blockedReason = "OOB";
            }
            Building testBuilding;
            testBuilding.position = g_mouseWorldPos;
            testBuilding.size = { g_gridSpacing, g_gridSpacing, g_gridSpacing };
            if (overlapsWithAny(testBuilding, g_buildings)) {
                canPlaceDepot = false;
                blockedReason = "OVR CITY";
            }
            if (canPlaceDepot) {
                for (const auto& placed : g_placedPlatforms) {
                    if (Vector3Distance(g_mouseWorldPos, placed.position) < g_gridSpacing * 0.9f) {
                        canPlaceDepot = false;
                        blockedReason = "DEP OVR TRK/ST";
                        break;
                    }
                }
            }
            if (canPlaceDepot && !CanPlaceDepotAt(g_mouseWorldPos, g_placedPlatforms, g_gridSpacing)) {
                canPlaceDepot = false;
                blockedReason = "DEP REQ NS";
            }
            if (canPlaceDepot && g_playerCredits < ApplyBuildDiscount(OuterGridCost(1500, g_mouseWorldPos.x, g_mouseWorldPos.z))) {
                canPlaceDepot = false;
                blockedReason = "NO CR";
            }

            Color depotColor = canPlaceDepot ? AddColor(MulColor((Color){ 160, 160, 160, 220 }, brightness), nightBlue) : (Color){ 0,0,0,0 };
            DrawMaterialsDepot(g_mouseWorldPos, g_gridSpacing, depotColor, 0, !canPlaceDepot);
            if (canPlaceDepot) SetBuildStatusPossible();
            else SetBuildStatusBlocked(blockedReason);
        } else if (g_mouseInEffective3DArea && g_stationPlacementMode) {
            bool canPlaceStation = true;
            const char* blockedReason = nullptr;
            for (int i = 0; i < 4 && canPlaceStation; i++) {
                Vector3 pos = g_mouseWorldPos;
                float offset = (i - 1.5f) * g_gridSpacing;
                switch (g_placementOrientation) {
                    case 0: pos.x += offset; break;
                    case 1: pos.z += offset; break;
                    case 2: pos.x -= offset; break;
                    case 3: pos.z -= offset; break;
                    default: pos.x += offset; break;
                }
                if (!IsWithinGridBounds(pos.x, pos.z, g_gridSpacing * 0.5f)) {
                    canPlaceStation = false;
                    blockedReason = "OOB";
                }
                Building testBuilding;
                testBuilding.position = pos;
                testBuilding.size = { g_gridSpacing, g_gridSpacing, g_gridSpacing };
                if (overlapsWithAny(testBuilding, g_buildings)) {
                    canPlaceStation = false;
                    blockedReason = "OVR CITY";
                }
                for (const auto& p : g_placedPlatforms) {
                    if (Vector3Distance(pos, p.position) < g_gridSpacing * 0.9f) {
                        canPlaceStation = false;
                        blockedReason = "ST OVR TRK/ST/DEP";
                        break;
                    }
                }
                if (canPlaceStation) {
                    const float factoryHalf = g_gridSpacing * 2.0f;
                    for (const auto& f : g_placedFactories) {
                        if (fabsf(pos.x - f.position.x) < factoryHalf &&
                            fabsf(pos.z - f.position.z) < factoryHalf) {
                            canPlaceStation = false;
                            blockedReason = "ST OVR FAC";
                            break;
                        }
                    }
                }
            }
            if (canPlaceStation && g_playerCredits < ApplyBuildDiscount(OuterGridCost(1000, g_mouseWorldPos.x, g_mouseWorldPos.z))) {
                canPlaceStation = false;
                blockedReason = "NO CR";
            }
            Color stationColorEff = AddColor(MulColor(g_stationColor, brightness), nightBlue);
            float previewTime = (float)GetTime();
            for (int i = 0; i < 4; i++) {
                Vector3 pos = g_mouseWorldPos;
                float offset = (i - 1.5f) * g_gridSpacing;
                switch (g_placementOrientation) {
                    case 0: pos.x += offset; break;
                    case 1: pos.z += offset; break;
                    case 2: pos.x -= offset; break;
                    case 3: pos.z -= offset; break;
                    default: pos.x += offset; break;
                }
                Color basePlateOvr = {0,0,0,0};
                if (canPlaceStation) {
                    int cx = WorldToGridCell(pos.x);
                    int cz = WorldToGridCell(pos.z);
                    ClusterType ct = GetClusterTypeForStation(cx, cz);
                    bool inActivatedCargo = IsWorldPosInActivatedCargoCluster(pos.x, pos.z);
                    if (ct != ClusterType::CARGO || inActivatedCargo) {
                        Color clusterCol = (ct != ClusterType::CARGO) ? GetClusterBuildingColor(ct) : GetActivatedCargoPulseColor();
                        clusterCol = AddColor(MulColor(clusterCol, brightness), nightBlue);
                        float pulse = (sinf(previewTime * 2.5f) + 1.0f) * 0.5f;
                        basePlateOvr = LerpColor((Color){128,128,128,179}, clusterCol, pulse);
                    }
                }
                DrawPlatform(pos, g_gridSpacing, stationColorEff, !canPlaceStation, basePlateOvr);
            }
            if (canPlaceStation) SetBuildStatusPossible();
            else SetBuildStatusBlocked(blockedReason);
        } else if (g_mouseInEffective3DArea && g_demolishMode) {
            // Draw demolish preview (red X or highlight)
            float topY = GetPlatformTopY(g_mouseWorldPos.y, g_gridSpacing);
            float topThickness = g_gridSpacing * 0.1f;
            DrawCubeWires((Vector3){g_mouseWorldPos.x, topY, g_mouseWorldPos.z}, g_gridSpacing * 1.1f, topThickness * 2.0f, g_gridSpacing * 1.1f, RED);
        }
        
        // Render build particles
        RenderBuildParticles();
        // Render factory smoke (floating white/grey cubes from cylinder tops)
        RenderFactorySmoke();
        
        // End 3D mode
        EndMode3D();

        // Debug: station gate status (hover a station tile, or a depot adjacent to that station)
        {
            // Calculate font sizes for resolution scaling (needed for STATION GATE text)
            float fontSize = GetScaledFontSize(BASE_FONT_SIZE);
            float fontSizeLarge = GetScaledFontSize(BASE_FONT_SIZE_LARGE);
            
            long long gateKey = kNoStation;
            int gateComp = -1;

            if (hoveredPlatformIndex >= 0 && hoveredPlatformIndex < (int)g_placedPlatforms.size()) {
                const PlacedPlatform& hp = g_placedPlatforms[hoveredPlatformIndex];

                if (!hp.isDepot && hp.isStation) {
                    int cid = (hoveredPlatformIndex < (int)stationCompId.size()) ? stationCompId[hoveredPlatformIndex] : -1;
                    if (cid >= 0 && cid < (int)stationCompKey.size() &&
                        cid < (int)stationPrimePlatformIdx.size()) {
                        for (int idx : stationPrimePlatformIdx[cid]) {
                            if (idx == hoveredPlatformIndex) { gateKey = stationCompKey[cid]; gateComp = cid; break; }
                        }
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
                    DrawTextEx(gameFont, "STATION GATE: OPEN", (Vector2){10, 110}, fontSize, 0.0f, WHITE);
                } else {
                    DrawTextEx(gameFont, "STATION GATE: CLOSED", (Vector2){10, 110}, fontSize, 0.0f, WHITE);
                }
            }
        }
        
        // Draw UI text - calculate font sizes for resolution scaling
        float fontSize = GetScaledFontSize(BASE_FONT_SIZE);
        float fontSizeLarge = GetScaledFontSize(BASE_FONT_SIZE_LARGE);
        
        // Draw title at 3.7% X, 2.2% Y with pulsing cyan to white effect
        float titleX = (float)g_renderWidth * 0.037f;
        float titleY = (float)g_renderHeight * 0.022f;
        float titleFontSize = fontSize * 2.0f; // 200% larger
        float realTime = (float)GetTime(); // Real time for pulsing (ignores game speed/pause)
        float pulse = (sinf(realTime * 3.0f) + 1.0f) / 2.0f; // 0 to 1
        // Interpolate between CYAN (0, 255, 255) and WHITE (255, 255, 255)
        Color titleColor = {
            (unsigned char)(pulse * 255),
            255,
            255,
            255
        };
        DrawTextEx(gameFont, "CYBERTRAIN - RAIL NETWORK SIMULATOR: ONLINE", (Vector2){titleX, titleY}, titleFontSize, 0.0f, titleColor);
        
        // Derive WK / M / YR from total elapsed week-cycles
        int calWk, calMonth, calYear;
        GetYearClock(g_dayCount, calWk, calMonth, calYear);
        
        // Display credits on same line as title, two character spaces away
        float titleTextWidth = MeasureTextEx(gameFont, "CYBERTRAIN - RAIL NETWORK SIMULATOR: ONLINE", titleFontSize, 0.0f).x;
        float twoSpacesWidth = MeasureTextEx(gameFont, "  ", titleFontSize, 0.0f).x;
        float creditsX = titleX + titleTextWidth + twoSpacesWidth;
        char creditsText[64];
        snprintf(creditsText, sizeof(creditsText), "| CREDITS %d", g_playerCredits);
        Color creditsColor = (Color){ 255, 255, 0, 255 }; // Bright yellow
        DrawTextEx(gameFont, creditsText, (Vector2){creditsX, titleY}, titleFontSize, 0.0f, creditsColor);
        
        // Net Worth display (after credits)
        {
            int netWorth = CalculateNetWorth();
            char netWorthText[64];
            snprintf(netWorthText, sizeof(netWorthText), "| NET WORTH %d", netWorth);
            float netWorthX = creditsX + MeasureTextEx(gameFont, creditsText, titleFontSize, 0.0f).x + twoSpacesWidth;
            DrawTextEx(gameFont, netWorthText, (Vector2){netWorthX, titleY}, titleFontSize, 0.0f, (Color){0, 255, 200, 255});

        }
        
        // Display speed at x: 74% y: 81%, keep same size and color
        char speedText[64];
        snprintf(speedText, sizeof(speedText), "%s", GetSpeedName());
        float speedX = (float)g_renderWidth * 0.66f;
        float speedY = (float)g_renderHeight * 0.81f;
        float timeSpeedFontSize = fontSize * 1.5f; // 50% larger (keep same as before)
        Color timeSpeedColor = (Color){ 0, 255, 255, 255 }; // Bright cyan (keep same as before)
        DrawTextEx(gameFont, speedText, (Vector2){speedX, speedY}, timeSpeedFontSize, 0.0f, timeSpeedColor);

        // Calendar clock on the same row, immediately after the speed text
        {
            float speedTextW = MeasureTextEx(gameFont, speedText, timeSpeedFontSize, 0.0f).x;
            char calText[64];
            snprintf(calText, sizeof(calText), "  WK:%d  M:%d  YR:%d", calWk, calMonth, calYear);
            DrawTextEx(gameFont, calText, (Vector2){speedX + speedTextW, speedY}, timeSpeedFontSize, 0.0f, timeSpeedColor);
        }

        // CyberTrain cam overlay: flashing label + ESC hint
        if (g_cyberTrainCamActive) {
            float flash = (sinf((float)GetTime() * 3.0f) + 1.0f) * 0.5f;
            unsigned char alpha = (unsigned char)(140 + (int)(flash * 115.0f));
            Color camHudColor = { 0, 255, 255, alpha };
            float camHudSize = GetScaledFontSize(BASE_FONT_SIZE) * 2.0f;
            const char* camLabel = "CYBERTRAIN CAM  |  PRESS ESC TO EXIT";
            float camLabelW = MeasureTextEx(gameFont, camLabel, camHudSize, 0.0f).x;
            DrawTextEx(gameFont, camLabel,
                (Vector2){ ((float)g_renderWidth - camLabelW) * 0.5f, (float)g_renderHeight * 0.12f },
                camHudSize, 0.0f, camHudColor);
        }

        // Draw scrolling ticker with game tips and controls
        DrawTicker();
        // Per-train junction setup helper badge for newly placed trains.
        if (g_junctionSetupBadgeTimer > 0.0f
            && g_junctionSetupTrainId >= 0
            && g_selectedTrainIndex >= 0
            && g_selectedTrainIndex < (int)g_placedTrains.size()
            && g_placedTrains[g_selectedTrainIndex].id == g_junctionSetupTrainId) {
            const float pulse01 = (sinf((float)GetTime() * 6.0f) + 1.0f) * 0.5f;
            Color badgeColor = {
                (unsigned char)(160 + pulse01 * 95.0f),
                255,
                255,
                255
            };
            char badgeBuf[160];
            snprintf(badgeBuf, sizeof(badgeBuf), "JUNCTION SETUP MODE (TRAIN %d)", g_junctionSetupTrainId);
            DrawTextEx(gameFont, badgeBuf, (Vector2){(float)g_renderWidth * 0.06f, (float)g_renderHeight * 0.92f}, fontSizeLarge, 0.0f, badgeColor);
        }
        
        // Draw terminal feedback
        DrawTerminal();
        
        // Draw scanline overlay
        DrawScanlines();

        // Render-order contract: modals must draw second-to-last and cursor must draw last.
        // Keep this order in sync with the map-mode branch above.
        DrawStationModal(g_stationModal, g_renderWidth, g_renderHeight);
        DrawLineModal(g_lineModal, g_lines, g_renderWidth, g_renderHeight);
        DrawJunctionModal(g_junctionModal, g_renderWidth, g_renderHeight);
        DrawSiloAnnounceModal(g_siloAnnounceModal, g_renderWidth, g_renderHeight);
        DrawStockCommoditiesModal(g_stockModal, g_renderWidth, g_renderHeight);
        DrawDemolishConfirmModal(g_demolishConfirmModal, g_renderWidth, g_renderHeight);
        DrawPausedTrainDeleteModal(g_pausedTrainDeleteModal, g_renderWidth, g_renderHeight);
        DrawJunctionConfigModal(g_junctionConfigModal, g_renderWidth, g_renderHeight);
        DrawQuitConfirmModal(g_quitConfirmModal, g_renderWidth, g_renderHeight);
        DrawYear5WarningModal();
        DrawIntroModal();
        DrawHelpModal();

        // Handle modal dismiss/close after drawing modal UI this frame.
        if (g_stationModal.confirmClicked) {
            CommitStationModal(g_stationModal); // also calls InvalidatePlatformCaches
            BlockMouseClicksAfterModalClose();
        }
        else if (g_stationModal.cancelClicked) {
            CancelStationModal(g_stationModal); // refunds + removes tiles if isNewBuild
            BlockMouseClicksAfterModalClose();
        }
        if (g_siloAnnounceModal.gotItClicked) {
            int sys = g_siloAnnounceModal.system;
            g_siloAnnounceModal.open = false;
            g_siloAnnounceModal.gotItClicked = false;
            BlockMouseClicksAfterModalClose();
            if (g_sfxSiloBuilt.frameCount > 0) PlaySound(g_sfxSiloBuilt);
            EnterCyberTrainCam(sys);
        }
        if (g_stockModal.closeClicked) {
            g_stockModal.open = false;
            g_stockModal.closeClicked = false;
            BlockMouseClicksAfterModalClose();
        }
        if (g_demolishConfirmModal.confirmClicked) {
            ExecuteDemolishStationAndLine();  // also clears modes and re-enables demolish
            BlockMouseClicksAfterModalClose();
        } else if (g_demolishConfirmModal.cancelClicked) {
            g_demolishConfirmModal.open = false;
            g_demolishConfirmModal.cancelClicked = false;
            g_demolishConfirmModalOpen = false;
            BlockMouseClicksAfterModalClose();
            ClearAllPlacementModes();
            g_demolishMode = true;
        }
        if (g_pausedTrainDeleteModal.confirmClicked) {
            int ti = g_pausedTrainDeleteModal.trainIndex;
            if (ti >= 0 && ti < (int)g_placedTrains.size()) {
                if (g_selectedTrainIndex == ti) g_selectedTrainIndex = -1;
                else if (g_selectedTrainIndex > ti) g_selectedTrainIndex--;
                g_placedTrains.erase(g_placedTrains.begin() + ti);
                AddTerminalMessage("PAUSED TRAIN DESTROYED - 100 CREDITS");
                if (g_playerCredits >= 100) g_playerCredits -= 100;
            }
            g_pausedTrainDeleteModal.open = false;
            g_pausedTrainDeleteModal.confirmClicked = false;
            g_pausedTrainDeleteModal.trainIndex = -1;
            BlockMouseClicksAfterModalClose();
        } else if (g_pausedTrainDeleteModal.cancelClicked) {
            g_pausedTrainDeleteModal.open = false;
            g_pausedTrainDeleteModal.cancelClicked = false;
            g_pausedTrainDeleteModal.trainIndex = -1;
            BlockMouseClicksAfterModalClose();
        }
        // Junction config modal: handle SWITCH and DONE
        if (g_junctionConfigModal.switchClicked) {
            g_junctionConfigModal.switchClicked = false;
            int slot = g_junctionConfigModal.selectedTrainSlot;
            if (slot >= 0 && slot < (int)g_junctionConfigModal.trainIndices.size()) {
                int ti = g_junctionConfigModal.trainIndices[slot];
                if (ti >= 0 && ti < (int)g_placedTrains.size()) {
                    PlacedTrain& train = g_placedTrains[ti];
                    std::vector<Vector3> adj = GetSortedAdjacentPositions(g_junctionConfigModal.junctionPos, g_placedPlatforms, g_gridSpacing);
                    int numPairs = NumJunctionPairs((int)adj.size());
                    if (numPairs > 0) {
                        int cur = train.GetJunctionSetting(g_junctionConfigModal.junctionPos.x, g_junctionConfigModal.junctionPos.z, &adj);
                        if (cur < 0) cur = DefaultJunctionPairIndex(g_junctionConfigModal.junctionPos, adj);
                        int next = (cur + 1) % numPairs;
                        train.SetJunctionSetting(g_junctionConfigModal.junctionPos.x, g_junctionConfigModal.junctionPos.z, next, &adj);
                        if (!train.path.empty())
                            (void)RebuildTrainPath(train, g_placedPlatforms, g_gridSpacing);
                    }
                }
            }
        }
        if (g_junctionConfigModal.doneClicked) {
            g_junctionConfigModal = {};
            g_junctionConfigModalOpen = false;
            BlockMouseClicksAfterModalClose();
        }
        if (g_quitConfirmModal.yesClicked) {
            g_quitConfirmModal = {};
            g_quitConfirmModalOpen = false;
            RestartToSplashAfterGameOver();
            BlockMouseClicksAfterModalClose();
        }
        if (g_quitConfirmModal.noClicked) {
            g_quitConfirmModal = {};
            g_quitConfirmModalOpen = false;
            BlockMouseClicksAfterModalClose();
        }

        // Gamma overlay
        DrawGammaOverlay();

        // Options screen overlay (drawn on top of everything except cursor)
        if (g_optionsScreen == OptionsScreen::Visible) {
            DrawOptionsScreen();
        }

        // Draw cursor last so it's always on top (especially over modal)
        DrawCustomCursor();

        // End drawing
        if (!g_standalone_mode && g_framebuffer_initialized) {
            EndTextureMode();
        } else {
            EndDrawing();
        }
} // End of GameLoopBody()

