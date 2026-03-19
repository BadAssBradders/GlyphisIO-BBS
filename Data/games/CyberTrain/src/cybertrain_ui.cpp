// â”€â”€ Splash Asset Loading â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

static void LoadSplashAssets() {
    if (g_splashAssetsLoaded) return;

    const char* splash1Paths[] = {
        "images/SPLASH1.PNG", "../images/SPLASH1.PNG",
        "Data/games/CyberTrain/images/SPLASH1.PNG", "../../images/SPLASH1.PNG"
    };
    const char* splash2Paths[] = {
        "images/SPLASH2.PNG", "../images/SPLASH2.PNG",
        "Data/games/CyberTrain/images/SPLASH2.PNG", "../../images/SPLASH2.PNG"
    };
    const char* splash3Paths[] = {
        "images/SPLASH3.PNG", "../images/SPLASH3.PNG",
        "Data/games/CyberTrain/images/SPLASH3.PNG", "../../images/SPLASH3.PNG"
    };

    // SPLASH1 â€” simple texture (fade-in only, no mosaic needed)
    for (int i = 0; i < 4; i++) {
        if (FileExists(splash1Paths[i])) {
            g_splashTex1 = LoadTexture(splash1Paths[i]);
            if (g_splashTex1.id != 0) { SetTextureFilter(g_splashTex1, TEXTURE_FILTER_POINT); break; }
        }
    }

    // Load SPLASH2 and SPLASH3 as plain textures (slide-in transitions)
    for (int i = 0; i < 4; i++) {
        if (FileExists(splash2Paths[i])) {
            g_splashTex2 = LoadTexture(splash2Paths[i]);
            if (g_splashTex2.id != 0) { SetTextureFilter(g_splashTex2, TEXTURE_FILTER_POINT); break; }
        }
    }
    for (int i = 0; i < 4; i++) {
        if (FileExists(splash3Paths[i])) {
            g_splashTex3 = LoadTexture(splash3Paths[i]);
            if (g_splashTex3.id != 0) { SetTextureFilter(g_splashTex3, TEXTURE_FILTER_POINT); break; }
        }
    }

    g_splashAssetsLoaded = true;
    printf("[LoadSplashAssets] Splash assets loaded\n");
}

static void UnloadSplashAssets() {
    if (g_splashTex1.id != 0) { UnloadTexture(g_splashTex1); g_splashTex1 = {0}; }
    if (g_splashTex2.id != 0) { UnloadTexture(g_splashTex2); g_splashTex2 = {0}; }
    if (g_splashTex3.id != 0) { UnloadTexture(g_splashTex3); g_splashTex3 = {0}; }
    for (int i = 0; i < SPLASH_MOSAIC_LEVELS; i++) {
        if (g_splashMosaicTex2[i].id != 0) { UnloadTexture(g_splashMosaicTex2[i]); g_splashMosaicTex2[i] = {0}; }
        if (g_splashMosaicTex3[i].id != 0) { UnloadTexture(g_splashMosaicTex3[i]); g_splashMosaicTex3[i] = {0}; }
    }
    g_splashAssetsLoaded = false;
}

// ═══════════════════════════════════════════════════════════════════════════════
// AUDIO SYSTEM
// ═══════════════════════════════════════════════════════════════════════════════

static float GetVolumeFloat(int level) {
    if (level <= 0) return 0.25f;
    if (level >= 2) return 1.0f;
    return 0.5f;
}

static void ApplyMusicVolume() {
    float vol = GetVolumeFloat(g_musicVolume);
    for (int i = 0; i < 3; i++) {
        if (g_musicTracks[i].stream.buffer != NULL) {
            SetMusicVolume(g_musicTracks[i], vol);
        }
    }
}

static void ApplySfxVolume() {
    float vol = GetVolumeFloat(g_sfxVolume);
    if (g_sfxBuildTrain.frameCount > 0) SetSoundVolume(g_sfxBuildTrain, vol);
    if (g_sfxBuildSys.frameCount > 0)   SetSoundVolume(g_sfxBuildSys, vol);
    if (g_sfxFactoryBuilt.frameCount > 0) SetSoundVolume(g_sfxFactoryBuilt, vol);
    if (g_sfxBureauBuilt.frameCount > 0)  SetSoundVolume(g_sfxBureauBuilt, vol);
    if (g_sfxSiloBuilt.frameCount > 0)    SetSoundVolume(g_sfxSiloBuilt, vol);
}

static void LoadAudioAssets() {
    if (g_musicLoaded) return;

    const char* trackPaths[][4] = {
        { "Audio/CyberTrain_Track1.mp3", "../Audio/CyberTrain_Track1.mp3", "Data/games/CyberTrain/Audio/CyberTrain_Track1.mp3", "../../Audio/CyberTrain_Track1.mp3" },
        { "Audio/CyberTrain_Track2.mp3", "../Audio/CyberTrain_Track2.mp3", "Data/games/CyberTrain/Audio/CyberTrain_Track2.mp3", "../../Audio/CyberTrain_Track2.mp3" },
        { "Audio/Cybertrain_Track3.mp3", "../Audio/Cybertrain_Track3.mp3", "Data/games/CyberTrain/Audio/Cybertrain_Track3.mp3", "../../Audio/Cybertrain_Track3.mp3" },
    };

    for (int t = 0; t < 3; t++) {
        for (int p = 0; p < 4; p++) {
            if (FileExists(trackPaths[t][p])) {
                g_musicTracks[t] = LoadMusicStream(trackPaths[t][p]);
                if (g_musicTracks[t].stream.buffer != NULL) {
                    g_musicTracks[t].looping = false;
                    printf("[LoadAudioAssets] Loaded track %d from %s\n", t+1, trackPaths[t][p]);
                    break;
                }
            }
        }
    }
    g_musicLoaded = true;

    struct { Sound* snd; const char* name; } sfxFiles[] = {
        { &g_sfxBuildTrain,   "BUILD-Train.wav" },
        { &g_sfxBuildSys,     "BUILD-Sys8-12.wav" },
        { &g_sfxFactoryBuilt, "Factory-Built.wav" },
        { &g_sfxBureauBuilt,  "Bureau-BUILT.wav" },
        { &g_sfxSiloBuilt,    "SILO-Built.wav" },
    };
    const char* audioDirs[] = { "Audio/", "../Audio/", "Data/games/CyberTrain/Audio/", "../../Audio/" };
    for (auto& sf : sfxFiles) {
        for (int d = 0; d < 4; d++) {
            char path[256];
            snprintf(path, sizeof(path), "%s%s", audioDirs[d], sf.name);
            if (FileExists(path)) {
                *sf.snd = LoadSound(path);
                if (sf.snd->frameCount > 0) {
                    printf("[LoadAudioAssets] Loaded SFX: %s\n", path);
                    break;
                }
            }
        }
    }
    g_sfxLoaded = true;

    ApplyMusicVolume();
    ApplySfxVolume();
    g_currentTrack = 0;
}

static void UnloadAudioAssets() {
    for (int i = 0; i < 3; i++) {
        if (g_musicTracks[i].stream.buffer != NULL) {
            StopMusicStream(g_musicTracks[i]);
            UnloadMusicStream(g_musicTracks[i]);
            g_musicTracks[i] = {};
        }
    }
    g_musicLoaded = false;

    if (g_sfxBuildTrain.frameCount > 0)   UnloadSound(g_sfxBuildTrain);
    if (g_sfxBuildSys.frameCount > 0)     UnloadSound(g_sfxBuildSys);
    if (g_sfxFactoryBuilt.frameCount > 0) UnloadSound(g_sfxFactoryBuilt);
    if (g_sfxBureauBuilt.frameCount > 0)  UnloadSound(g_sfxBureauBuilt);
    if (g_sfxSiloBuilt.frameCount > 0)    UnloadSound(g_sfxSiloBuilt);
    g_sfxBuildTrain = {};
    g_sfxBuildSys = {};
    g_sfxFactoryBuilt = {};
    g_sfxBureauBuilt = {};
    g_sfxSiloBuilt = {};
    g_sfxLoaded = false;
}

static void UpdateMusic() {
    if (!g_musicLoaded) return;

    Music& current = g_musicTracks[g_currentTrack];
    if (current.stream.buffer == NULL) return;

    if (!IsMusicStreamPlaying(current)) {
        g_currentTrack = (g_currentTrack + 1) % 3;
        Music& next = g_musicTracks[g_currentTrack];
        if (next.stream.buffer != NULL) {
            PlayMusicStream(next);
        }
    }
    for (int i = 0; i < 3; i++) {
        if (g_musicTracks[i].stream.buffer != NULL && IsMusicStreamPlaying(g_musicTracks[i])) {
            UpdateMusicStream(g_musicTracks[i]);
        }
    }
}

// ── Options Screen ────────────────────────────────────────────────────────────

static void DrawOptionsScreen() {
    int sw = g_renderWidth;
    int sh = g_renderHeight;

    DrawRectangle(0, 0, sw, sh, (Color){0, 0, 0, 180});

    float fontSize = GetScaledFontSize(BASE_FONT_SIZE) * 1.4f;
    float lineSpacing = 1.0f;
    float titleFontSize = fontSize * 1.5f;

    const char* title = "OPTIONS";
    float titleW = MeasureTextEx(gameFont, title, titleFontSize, lineSpacing).x;
    DrawTextEx(gameFont, title, {(sw - titleW) * 0.5f, sh * 0.25f}, titleFontSize, lineSpacing, WHITE);

    const char* labels[] = { "MUSIC VOLUME", "SOUND FX", "GAMMA" };
    const char* values[] = { "LOW", "MID", "HIGH" };
    int* settings[] = { &g_musicVolume, &g_sfxVolume, &g_gammaLevel };

    float startY = sh * 0.38f;
    float rowH = fontSize * 2.5f;

    for (int row = 0; row < 3; row++) {
        float y = startY + row * rowH;
        bool selected = (row == g_optionsSelection);
        Color labelCol = selected ? (Color){0, 255, 255, 255} : (Color){180, 180, 180, 255};

        DrawTextEx(gameFont, labels[row], {sw * 0.25f, y}, fontSize, lineSpacing, labelCol);

        float valX = sw * 0.60f;
        for (int v = 0; v < 3; v++) {
            bool isCurrent = (*settings[row] == v);
            Color valCol;
            if (selected && isCurrent) valCol = (Color){0, 255, 0, 255};
            else if (isCurrent) valCol = (Color){0, 200, 0, 200};
            else if (selected) valCol = (Color){120, 120, 120, 255};
            else valCol = (Color){80, 80, 80, 255};

            if (selected && isCurrent) {
                char bracketBuf[16];
                snprintf(bracketBuf, sizeof(bracketBuf), "[%s]", values[v]);
                DrawTextEx(gameFont, bracketBuf, {valX, y}, fontSize, lineSpacing, valCol);
                valX += MeasureTextEx(gameFont, bracketBuf, fontSize, lineSpacing).x + fontSize * 0.8f;
            } else {
                DrawTextEx(gameFont, values[v], {valX, y}, fontSize, lineSpacing, valCol);
                valX += MeasureTextEx(gameFont, values[v], fontSize, lineSpacing).x + fontSize * 0.8f;
            }
        }
    }

    float instrY = startY + 3 * rowH + fontSize;
    const char* instr = "UP/DOWN: SELECT   LEFT/RIGHT: CHANGE   ESC/ENTER: CLOSE";
    float instrW = MeasureTextEx(gameFont, instr, fontSize * 0.7f, lineSpacing).x;
    DrawTextEx(gameFont, instr, {(sw - instrW) * 0.5f, instrY}, fontSize * 0.7f, lineSpacing, (Color){140, 140, 140, 255});
}

static bool HandleOptionsInput() {
    if (g_optionsScreen != OptionsScreen::Visible) return false;

    if (CustomIsKeyPressed(KEY_UP)) {
        g_optionsSelection = (g_optionsSelection + 2) % 3;
    }
    if (CustomIsKeyPressed(KEY_DOWN)) {
        g_optionsSelection = (g_optionsSelection + 1) % 3;
    }

    int* settings[] = { &g_musicVolume, &g_sfxVolume, &g_gammaLevel };

    if (CustomIsKeyPressed(KEY_LEFT)) {
        if (*settings[g_optionsSelection] > 0) {
            (*settings[g_optionsSelection])--;
            if (g_optionsSelection == 0) ApplyMusicVolume();
            if (g_optionsSelection == 1) ApplySfxVolume();
        }
    }
    if (CustomIsKeyPressed(KEY_RIGHT)) {
        if (*settings[g_optionsSelection] < 2) {
            (*settings[g_optionsSelection])++;
            if (g_optionsSelection == 0) ApplyMusicVolume();
            if (g_optionsSelection == 1) ApplySfxVolume();
        }
    }

    if (CustomIsKeyPressed(KEY_ESCAPE) || CustomIsKeyPressed(KEY_ENTER)) {
        g_optionsScreen = OptionsScreen::Hidden;
    }

    return true;
}

static void DrawGammaOverlay() {
    if (g_gammaLevel == 1) return;
    int sw = g_renderWidth;
    int sh = g_renderHeight;
    if (g_gammaLevel == 0) {
        // Low gamma = noticeably darker
        DrawRectangle(0, 0, sw, sh, (Color){0, 0, 0, 120});
    } else {
        // High gamma = noticeably brighter
        DrawRectangle(0, 0, sw, sh, (Color){255, 255, 255, 60});
    }
}

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
// UI IMPLEMENTATION
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

static void LoadUIAssets() {
    if (g_uiAssetsLoaded) return;
    
    printf("[LoadUIAssets] Loading UI textures...\n");
    
    // Try multiple paths (order matters - try most likely first)
    // For standalone: images/ should work after we fix working directory
    // For embedded: Data/games/CyberTrain/images/ should work
    const char* uiPaths[] = { 
        "images/UI.png", 
        "../images/UI.png",  // If running from bin/
        "Data/games/CyberTrain/images/UI.png", 
        "../../images/UI.png" 
    };
    const char* cursorPaths[] = { 
        "images/mouse_cursor.png", 
        "../images/mouse_cursor.png",  // If running from bin/
        "Data/games/CyberTrain/images/mouse_cursor.png", 
        "../../images/mouse_cursor.png" 
    };
    const char* gameOver1Paths[] = {
        "images/GameOver1.png",
        "../images/GameOver1.png",
        "Data/games/CyberTrain/images/GameOver1.png",
        "../../images/GameOver1.png"
    };
    const char* gameOver2Paths[] = {
        "images/GameOver2.png",
        "../images/GameOver2.png",
        "Data/games/CyberTrain/images/GameOver2.png",
        "../../images/GameOver2.png"
    };
    
    // Load UI BG
    for (int i = 0; i < 4; i++) {
        if (FileExists(uiPaths[i])) {
            g_texUI = LoadTexture(uiPaths[i]);
            if (g_texUI.id != 0) {
                printf("[LoadUIAssets] Loaded UI BG from %s (%dx%d)\n", uiPaths[i], g_texUI.width, g_texUI.height);
                SetTextureFilter(g_texUI, TEXTURE_FILTER_POINT); 
                break;
            }
        }
    }
    
    // Load cargo UI variants (same directory as UI.png)
    const char* cargo1Paths[] = { "images/UI_cargo1_selected.png", "../images/UI_cargo1_selected.png", "Data/games/CyberTrain/images/UI_cargo1_selected.png", "../../images/UI_cargo1_selected.png" };
    const char* cargo2Paths[] = { "images/UI_cargo2_selected.png", "../images/UI_cargo2_selected.png", "Data/games/CyberTrain/images/UI_cargo2_selected.png", "../../images/UI_cargo2_selected.png" };
    const char* cargo3Paths[] = { "images/UI_cargo3_selected.png", "../images/UI_cargo3_selected.png", "Data/games/CyberTrain/images/UI_cargo3_selected.png", "../../images/UI_cargo3_selected.png" };
    for (int i = 0; i < 4; i++) {
        if (FileExists(cargo1Paths[i])) { g_texUICargo1 = LoadTexture(cargo1Paths[i]); if (g_texUICargo1.id != 0) { SetTextureFilter(g_texUICargo1, TEXTURE_FILTER_POINT); break; } }
    }
    for (int i = 0; i < 4; i++) {
        if (FileExists(cargo2Paths[i])) { g_texUICargo2 = LoadTexture(cargo2Paths[i]); if (g_texUICargo2.id != 0) { SetTextureFilter(g_texUICargo2, TEXTURE_FILTER_POINT); break; } }
    }
    for (int i = 0; i < 4; i++) {
        if (FileExists(cargo3Paths[i])) { g_texUICargo3 = LoadTexture(cargo3Paths[i]); if (g_texUICargo3.id != 0) { SetTextureFilter(g_texUICargo3, TEXTURE_FILTER_POINT); break; } }
    }
    const char* greenPaths[] = { "images/UI_green_selected_sys2.png", "../images/UI_green_selected_sys2.png", "Data/games/CyberTrain/images/UI_green_selected_sys2.png", "../../images/UI_green_selected_sys2.png", "images/UI_green_selected.png", "../images/UI_green_selected.png", "Data/games/CyberTrain/images/UI_green_selected.png", "../../images/UI_green_selected.png" };
    for (int i = 0; i < 8; i++) {
        if (FileExists(greenPaths[i])) { g_texUIGreen = LoadTexture(greenPaths[i]); if (g_texUIGreen.id != 0) { SetTextureFilter(g_texUIGreen, TEXTURE_FILTER_POINT); break; } }
    }
    const char* sys3Paths[] = { "images/UI_magenta_selected_sys3.png", "../images/UI_magenta_selected_sys3.png", "Data/games/CyberTrain/images/UI_magenta_selected_sys3.png", "../../images/UI_magenta_selected_sys3.png" };
    const char* sys4Paths[] = { "images/UI_cyan_selected_sys4.png", "../images/UI_cyan_selected_sys4.png", "Data/games/CyberTrain/images/UI_cyan_selected_sys4.png", "../../images/UI_cyan_selected_sys4.png" };
    const char* sys5Paths[] = { "images/UI_orange_selected_sys5.png", "../images/UI_orange_selected_sys5.png", "Data/games/CyberTrain/images/UI_orange_selected_sys5.png", "../../images/UI_orange_selected_sys5.png" };
    const char* sys6Paths[] = { "images/UI_red_selected_sys6.png", "../images/UI_red_selected_sys6.png", "Data/games/CyberTrain/images/UI_red_selected_sys6.png", "../../images/UI_red_selected_sys6.png" };
    const char* sys7Paths[] = { "images/UI_yellow_selected_sys7.png", "../images/UI_yellow_selected_sys7.png", "Data/games/CyberTrain/images/UI_yellow_selected_sys7.png", "../../images/UI_yellow_selected_sys7.png" };
    for (int i = 0; i < 4; i++) { if (FileExists(sys3Paths[i])) { g_texUISys3 = LoadTexture(sys3Paths[i]); if (g_texUISys3.id != 0) { SetTextureFilter(g_texUISys3, TEXTURE_FILTER_POINT); break; } } }
    for (int i = 0; i < 4; i++) { if (FileExists(sys4Paths[i])) { g_texUISys4 = LoadTexture(sys4Paths[i]); if (g_texUISys4.id != 0) { SetTextureFilter(g_texUISys4, TEXTURE_FILTER_POINT); break; } } }
    for (int i = 0; i < 4; i++) { if (FileExists(sys5Paths[i])) { g_texUISys5 = LoadTexture(sys5Paths[i]); if (g_texUISys5.id != 0) { SetTextureFilter(g_texUISys5, TEXTURE_FILTER_POINT); break; } } }
    for (int i = 0; i < 4; i++) { if (FileExists(sys6Paths[i])) { g_texUISys6 = LoadTexture(sys6Paths[i]); if (g_texUISys6.id != 0) { SetTextureFilter(g_texUISys6, TEXTURE_FILTER_POINT); break; } } }
    for (int i = 0; i < 4; i++) { if (FileExists(sys7Paths[i])) { g_texUISys7 = LoadTexture(sys7Paths[i]); if (g_texUISys7.id != 0) { SetTextureFilter(g_texUISys7, TEXTURE_FILTER_POINT); break; } } }

    // Load modal template and button textures
    const char* modalTplPaths[] = { "images/modal_template.png", "../images/modal_template.png", "Data/games/CyberTrain/images/modal_template.png", "../../images/modal_template.png" };
    const char* modalConfirmSelPaths[] = { "images/modal_confirm_selected.png", "../images/modal_confirm_selected.png", "Data/games/CyberTrain/images/modal_confirm_selected.png", "../../images/modal_confirm_selected.png" };
    const char* modalConfirmNotPaths[] = { "images/modal_confirm_not_selected.png", "../images/modal_confirm_not_selected.png", "Data/games/CyberTrain/images/modal_confirm_not_selected.png", "../../images/modal_confirm_not_selected.png" };
    for (int i = 0; i < 4; i++) {
        if (FileExists(modalTplPaths[i])) { g_texModalTemplate = LoadTexture(modalTplPaths[i]); if (g_texModalTemplate.id != 0) break; }
    }
    const char* largeModalPaths[] = { "images/large_modal_template.png", "../images/large_modal_template.png", "Data/games/CyberTrain/images/large_modal_template.png", "../../images/large_modal_template.png" };
    for (int i = 0; i < 4; i++) {
        if (FileExists(largeModalPaths[i])) { g_texLargeModalTemplate = LoadTexture(largeModalPaths[i]); if (g_texLargeModalTemplate.id != 0) break; }
    }
    for (int i = 0; i < 4; i++) {
        if (FileExists(modalConfirmSelPaths[i])) { g_texModalConfirmSelected = LoadTexture(modalConfirmSelPaths[i]); if (g_texModalConfirmSelected.id != 0) break; }
    }
    for (int i = 0; i < 4; i++) {
        if (FileExists(modalConfirmNotPaths[i])) { g_texModalConfirmNotSelected = LoadTexture(modalConfirmNotPaths[i]); if (g_texModalConfirmNotSelected.id != 0) break; }
    }
    
    // Load Cursor
    for (int i = 0; i < 4; i++) {
        if (FileExists(cursorPaths[i])) {
            g_texCursor = LoadTexture(cursorPaths[i]);
            if (g_texCursor.id != 0) {
                printf("[LoadUIAssets] Loaded Cursor from %s (%dx%d)\n", cursorPaths[i], g_texCursor.width, g_texCursor.height);
                SetTextureFilter(g_texCursor, TEXTURE_FILTER_POINT);
                break;
            }
        }
    }

    // Load game-over slide panels
    for (int i = 0; i < 4; i++) {
        if (FileExists(gameOver1Paths[i])) {
            g_texGameOver1 = LoadTexture(gameOver1Paths[i]);
            if (g_texGameOver1.id != 0) { SetTextureFilter(g_texGameOver1, TEXTURE_FILTER_POINT); break; }
        }
    }
    for (int i = 0; i < 4; i++) {
        if (FileExists(gameOver2Paths[i])) {
            g_texGameOver2 = LoadTexture(gameOver2Paths[i]);
            if (g_texGameOver2.id != 0) { SetTextureFilter(g_texGameOver2, TEXTURE_FILTER_POINT); break; }
        }
    }
    
    if (g_texUI.id == 0) printf("[LoadUIAssets] WARNING: Failed to load UI.png\n");
    else g_uiAssetsLoaded = true;

    LoadSplashAssets();
}

static void UnloadUIAssets() {
    if (g_texUI.id != 0) UnloadTexture(g_texUI);
    if (g_texCursor.id != 0) UnloadTexture(g_texCursor);
    if (g_texUICargo1.id != 0) UnloadTexture(g_texUICargo1);
    if (g_texUICargo2.id != 0) UnloadTexture(g_texUICargo2);
    if (g_texUICargo3.id != 0) UnloadTexture(g_texUICargo3);
    if (g_texUIGreen.id != 0) UnloadTexture(g_texUIGreen);
    if (g_texUISys3.id != 0) UnloadTexture(g_texUISys3);
    if (g_texUISys4.id != 0) UnloadTexture(g_texUISys4);
    if (g_texUISys5.id != 0) UnloadTexture(g_texUISys5);
    if (g_texUISys6.id != 0) UnloadTexture(g_texUISys6);
    if (g_texUISys7.id != 0) UnloadTexture(g_texUISys7);
    if (g_texModalTemplate.id != 0) UnloadTexture(g_texModalTemplate);
    if (g_texLargeModalTemplate.id != 0) UnloadTexture(g_texLargeModalTemplate);
    if (g_texModalConfirmSelected.id != 0) UnloadTexture(g_texModalConfirmSelected);
    if (g_texModalConfirmNotSelected.id != 0) UnloadTexture(g_texModalConfirmNotSelected);
    if (g_texGameOver1.id != 0) UnloadTexture(g_texGameOver1);
    if (g_texGameOver2.id != 0) UnloadTexture(g_texGameOver2);
    g_texUI = { 0 };
    g_texCursor = { 0 };
    g_texUICargo1 = { 0 };
    g_texUICargo2 = { 0 };
    g_texUICargo3 = { 0 };
    g_texUIGreen = { 0 };
    g_texUISys3 = { 0 };
    g_texUISys4 = { 0 };
    g_texUISys5 = { 0 };
    g_texUISys6 = { 0 };
    g_texUISys7 = { 0 };
    g_texModalTemplate = { 0 };
    g_texLargeModalTemplate = { 0 };
    g_texModalConfirmSelected = { 0 };
    g_texModalConfirmNotSelected = { 0 };
    g_texGameOver1 = { 0 };
    g_texGameOver2 = { 0 };
    g_uiAssetsLoaded = false;
    UnloadSplashAssets();
}

static void DrawUIOverlay() {
    if (!g_uiAssetsLoaded) return;

    // Use render dimensions to ensure UI matches BBS screen dimensions exactly
    int sw = g_renderWidth;
    int sh = g_renderHeight;
    
    // Draw UI background (switch based on selected system hotspot only - NOT placement modes)
    Texture2D texToUse = g_texUI;
    if (g_selectedSystemHotspot == 0) {
        if (g_system1CargoState == 1 && g_texUICargo1.id != 0) texToUse = g_texUICargo1;
        else if (g_system1CargoState == 2 && g_texUICargo2.id != 0) texToUse = g_texUICargo2;
        else if (g_system1CargoState == 3 && g_texUICargo3.id != 0) texToUse = g_texUICargo3;
    } else if (g_selectedSystemHotspot == 1 && g_texUIGreen.id != 0) texToUse = g_texUIGreen;  // system2 = sys2
    else if (g_selectedSystemHotspot == 2 && g_texUISys3.id != 0) texToUse = g_texUISys3;     // system3 = sys3
    else if (g_selectedSystemHotspot == 3 && g_texUISys4.id != 0) texToUse = g_texUISys4;     // system4 = sys4
    else if (g_selectedSystemHotspot == 4 && g_texUISys5.id != 0) texToUse = g_texUISys5;     // system5 = sys5
    else if (g_selectedSystemHotspot == 5 && g_texUISys6.id != 0) texToUse = g_texUISys6;     // system6 = sys6
    else if (g_selectedSystemHotspot == 6 && g_texUISys7.id != 0) texToUse = g_texUISys7;     // system7 = sys7
    if (texToUse.id != 0) {
        Rectangle src = { 0, 0, (float)texToUse.width, (float)texToUse.height };
        Rectangle dst = { 0, 0, (float)sw, (float)sh };
        DrawTexturePro(texToUse, src, dst, {0,0}, 0.0f, WHITE);
    }
    
    // 3D viewport rect: top-left 14.3% x 12.2%, bottom-right 96.8% x 76% (bottom lifted 2.9% to clear overlay)
    g_viewfinderRect = (Rectangle){
        0.143f * sw,
        0.122f * sh,
        (0.968f - 0.143f) * sw,
        (0.76f - 0.122f) * sh
    };
    
    // Bottom-left cutout: base 6% square, extended: top up 3.5% (7% - 1.7% - 1.8%), right 1.7%
    float cutoutSize = 0.06f * (g_viewfinderRect.width < g_viewfinderRect.height ? g_viewfinderRect.width : g_viewfinderRect.height);
    float cutoutW = cutoutSize + 0.017f * sw;   // Right side extended 1.7%
    float cutoutH = cutoutSize + 0.035f * sh;   // Top extended up 3.5%
    g_viewfinderCutoutRect = (Rectangle){
        g_viewfinderRect.x,
        g_viewfinderRect.y + g_viewfinderRect.height - cutoutH,
        cutoutW,
        cutoutH
    };
    
    // (Debug borders removed)
    if (g_demolishMode) {
        DrawRectangleRec(g_viewfinderCutoutRect, (Color){ 0, 255, 255, 80 });  // Semi-transparent cyan highlight when demolish selected
    }
    
    // System hotspots: exact placements (top-left x,y, bottom-right x,y as percentages)
    g_systemHotspots[0] = (Rectangle){ 0.026f * sw, 0.16f * sh, (0.104f - 0.026f) * sw, (0.22f - 0.16f) * sh };  // system1
    g_systemHotspots[1] = (Rectangle){ 0.028f * sw, 0.258f * sh, (0.102f - 0.028f) * sw, (0.319f - 0.258f) * sh }; // system2
    g_systemHotspots[2] = (Rectangle){ 0.028f * sw, 0.34f * sh,  (0.102f - 0.028f) * sw, (0.402f - 0.34f) * sh };  // system3
    g_systemHotspots[3] = (Rectangle){ 0.028f * sw, 0.422f * sh, (0.102f - 0.028f) * sw, (0.486f - 0.422f) * sh }; // system4
    g_systemHotspots[4] = (Rectangle){ 0.028f * sw, 0.519f * sh, (0.102f - 0.028f) * sw, (0.579f - 0.519f) * sh }; // system5
    g_systemHotspots[5] = (Rectangle){ 0.028f * sw, 0.594f * sh, (0.102f - 0.028f) * sw, (0.652f - 0.594f) * sh }; // system6
    g_systemHotspots[6] = (Rectangle){ 0.025f * sw, 0.681f * sh, (0.102f - 0.025f) * sw, (0.75f - 0.681f) * sh };  // system7

    
    // Bottom icon hotspots: system8-13 (percentages: x1,y1 x2,y2 -> x,y,w,h)
    g_bottomHotspots[0] = (Rectangle){ 0.052f * sw, 0.829f * sh, (0.126f - 0.052f) * sw, (0.926f - 0.829f) * sh };   // system8: platform/track
    g_bottomHotspots[1] = (Rectangle){ 0.143f * sw, 0.829f * sh, (0.219f - 0.143f) * sw, (0.926f - 0.829f) * sh };   // system9: station
    g_bottomHotspots[2] = (Rectangle){ 0.242f * sw, 0.829f * sh, (0.315f - 0.242f) * sw, (0.926f - 0.829f) * sh };   // system10: depot
    g_bottomHotspots[3] = (Rectangle){ 0.332f * sw, 0.829f * sh, (0.408f - 0.332f) * sw, (0.926f - 0.829f) * sh };   // system11: factory
    g_bottomHotspots[4] = (Rectangle){ 0.432f * sw, 0.829f * sh, (0.502f - 0.432f) * sw, (0.926f - 0.829f) * sh };   // system12: bureau
    g_bottomHotspots[5] = (Rectangle){ 0.528f * sw, 0.829f * sh, (0.602f - 0.528f) * sw, (0.926f - 0.829f) * sh };   // system13: Stock & Commodities Market
    for (int i = 0; i < 6; i++) {
        bool highlighted = (g_selectedBottomHotspot == i) || (i == 5 && g_stockModal.open);  // system13 highlight when modal open
        if (highlighted) {
            DrawRectangleRec(g_bottomHotspots[i], (Color){ 0, 255, 255, 80 });  // Semi-transparent cyan highlight
        }
    }
    // Update global mouse-over-UI state
    // Cutout in bottom-left counts as UI (cursor visible, button hotspot)
    Vector2 m = CustomGetMousePosition();
    if (CheckCollisionPointRec(m, g_viewfinderCutoutRect)) {
        g_isMouseOverUI = true;  // Cutout = UI area, cursor visible
    } else if (CheckCollisionPointRec(m, g_viewfinderRect)) {
        g_isMouseOverUI = false; // Inside viewfinder = interacting with world
    } else {
        g_isMouseOverUI = true;  // Outside viewfinder = interacting with UI
    }
}

static void DrawCustomCursor() {
    // Always hide system cursor
    if (IsCursorHidden() == false) HideCursor();

    Vector2 cursorPos = CustomGetMousePosition();

    // In map mode draw a white cross at the mouse screen position.
    // Called last by both render branches so it is always on top of modals.
    if (g_mapMode) {
        float arm = g_gridSpacing * 0.35f * g_mapCamera.zoom;
        DrawLineV({cursorPos.x - arm, cursorPos.y}, {cursorPos.x + arm, cursorPos.y}, WHITE);
        DrawLineV({cursorPos.x, cursorPos.y - arm}, {cursorPos.x, cursorPos.y + arm}, WHITE);
        return;
    }

    // In 3D mode: cursor is always visible everywhere, rendered last so it is always on top.
    if (g_texCursor.id != 0) {
        float cursorScale = Clamp((float)g_renderHeight / 800.0f, 0.45f, 1.0f);
        float cw = (float)g_texCursor.width * cursorScale;
        float ch = (float)g_texCursor.height * cursorScale;
        Rectangle src = {0.0f, 0.0f, (float)g_texCursor.width, (float)g_texCursor.height};
        Rectangle dst = {cursorPos.x, cursorPos.y, cw, ch};
        DrawTexturePro(g_texCursor, src, dst, {0.0f, 0.0f}, 0.0f, WHITE);
    } else {
        DrawCircleV(cursorPos, 5, RED);
    }
}

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
// LEADERBOARD â€” file I/O, display, year-5 modal, end-game screen
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

static const char* kLBPathEmbedded = "Data/games/CyberTrain/leaderboard.json";
static const char* kLBPathStandalone = "leaderboard.json";

static const char* GetCyberTrainLeaderboardPath() {
    if (g_standalone_mode) return kLBPathStandalone;
    if (FileExists(kLBPathEmbedded)) return kLBPathEmbedded;
    if (FileExists(kLBPathStandalone)) return kLBPathStandalone;
    return kLBPathEmbedded;
}

static std::string EscapeCyberTrainLeaderboardString(const char* text) {
    std::string out;
    if (!text) return out;
    for (const unsigned char* p = (const unsigned char*)text; *p; ++p) {
        switch (*p) {
            case '\\': out += "\\\\"; break;
            case '"':  out += "\\\""; break;
            case '\n': out += "\\n"; break;
            case '\r': out += "\\r"; break;
            case '\t': out += "\\t"; break;
            default:   out.push_back((char)*p); break;
        }
    }
    return out;
}

static bool ParseCyberTrainLeaderboardQuoted(const std::string& line, size_t startQuote, size_t* outEndQuote, std::string* outValue) {
    if (startQuote >= line.size() || line[startQuote] != '"') return false;
    std::string value;
    bool escaping = false;
    for (size_t i = startQuote + 1; i < line.size(); i++) {
        char c = line[i];
        if (escaping) {
            switch (c) {
                case 'n': value.push_back('\n'); break;
                case 'r': value.push_back('\r'); break;
                case 't': value.push_back('\t'); break;
                case '\\': value.push_back('\\'); break;
                case '"': value.push_back('"'); break;
                default: value.push_back(c); break;
            }
            escaping = false;
            continue;
        }
        if (c == '\\') {
            escaping = true;
            continue;
        }
        if (c == '"') {
            if (outEndQuote) *outEndQuote = i;
            if (outValue) *outValue = value;
            return true;
        }
        value.push_back(c);
    }
    return false;
}

static void LoadCyberTrainLeaderboard() {
    g_leaderboard.clear();
    std::ifstream f(GetCyberTrainLeaderboardPath());
    if (!f.is_open()) return;
    std::string line;
    while (std::getline(f, line) && (int)g_leaderboard.size() < kLBMaxEntries) {
        auto upos = line.find("\"username\":"); auto spos = line.find("\"score\":");
        if (upos == std::string::npos || spos == std::string::npos) continue;
        size_t uquote = line.find('"', upos + 11);
        std::string uname;
        size_t uend = std::string::npos;
        if (uquote == std::string::npos || !ParseCyberTrainLeaderboardQuoted(line, uquote, &uend, &uname)) continue;
        size_t ss = spos + 8;
        while (ss < line.size() && !isdigit((unsigned char)line[ss]) && line[ss] != '-') ss++;
        size_t se = ss;
        if (se < line.size() && line[se] == '-') se++;
        while (se < line.size() && isdigit((unsigned char)line[se])) se++;
        if (se == ss) continue;
        CyberTrainLBEntry e;
        SanitizeCyberTrainUsername(uname.c_str(), e.username, sizeof(e.username));
        try {
            e.score = std::stoi(line.substr(ss, se - ss));
        } catch (...) {
            continue;
        }
        g_leaderboard.push_back(e);
    }
}

static void SaveAndMergeLBEntry(const char* username, int score) {
    char safeUsername[64];
    SanitizeCyberTrainUsername(username, safeUsername, sizeof(safeUsername));
    LoadCyberTrainLeaderboard();
    bool found = false;
    for (auto& e : g_leaderboard) {
        if (strncmp(e.username, safeUsername, 63) == 0) {
            if (score > e.score) e.score = score;
            found = true; break;
        }
    }
    if (!found) {
        CyberTrainLBEntry ne;
        strncpy(ne.username, safeUsername, 63);
        ne.username[63] = '\0';
        ne.score = score;
        g_leaderboard.push_back(ne);
    }
    std::sort(g_leaderboard.begin(), g_leaderboard.end(),
        [](const CyberTrainLBEntry& a, const CyberTrainLBEntry& b){ return a.score > b.score; });
    if ((int)g_leaderboard.size() > kLBMaxEntries) g_leaderboard.resize(kLBMaxEntries);
    std::ofstream fw(GetCyberTrainLeaderboardPath());
    for (const auto& e : g_leaderboard)
        fw << "{\"username\":\"" << EscapeCyberTrainLeaderboardString(e.username) << "\",\"score\":" << e.score << "}\n";
}

// Shared leaderboard table renderer â€” cx/cy is the centre point of the table
static void DrawLeaderboardTable(float cx, float cy, float w, float h, float fontSize) {
    DrawRectangle((int)(cx-w*0.5f),(int)(cy-h*0.5f),(int)w,(int)h,(Color){0,0,0,185});
    DrawRectangleLinesEx({cx-w*0.5f,cy-h*0.5f,w,h},2,(Color){0,255,255,200});
    const char* title = "CYBERTRAIN BEST CITY PLANNERS";
    float tf = fontSize*1.25f;
    float tw = MeasureTextEx(gameFont,title,tf,0.0f).x;
    DrawTextEx(gameFont,title,{cx-tw*0.5f,cy-h*0.5f+10.0f},tf,0.0f,(Color){255,215,60,255});
    float rowH  = (h-55.0f)/(kLBMaxEntries+0.5f);
    float startY = cy-h*0.5f+52.0f;
    float lx = cx-w*0.5f+18.0f, rx = cx+w*0.5f-18.0f;
    for (int i=0; i<(int)g_leaderboard.size() && i<kLBMaxEntries; i++) {
        char rankBuf[8]; snprintf(rankBuf,sizeof(rankBuf),"#%d",i+1);
        char scoreBuf[32]; snprintf(scoreBuf,sizeof(scoreBuf),"%d CR",g_leaderboard[i].score);
        float ry = startY+i*rowH;
        Color rc = (i==0)?(Color){255,215,60,255}:(i==1)?(Color){200,200,200,255}:
                   (i==2)?(Color){205,127,50,255}:(Color){180,220,255,255};
        DrawTextEx(gameFont,rankBuf,{lx,ry},fontSize,0.0f,rc);
        DrawTextEx(gameFont,g_leaderboard[i].username,{lx+46.0f,ry},fontSize,0.0f,rc);
        float sw = MeasureTextEx(gameFont,scoreBuf,fontSize,0.0f).x;
        DrawTextEx(gameFont,scoreBuf,{rx-sw,ry},fontSize,0.0f,rc);
    }
    if (g_leaderboard.empty()) {
        const char* empty = "NO ENTRIES YET -- BE THE FIRST!";
        float ew = MeasureTextEx(gameFont,empty,fontSize,0.0f).x;
        DrawTextEx(gameFont,empty,{cx-ew*0.5f,cy},fontSize,0.0f,(Color){150,150,150,255});
    }
}

// Year-5 warning modal
// â”€â”€ Intro Modal â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
// Shown once after the splash screen. Player chooses BEGIN or HELP.
static void DrawIntroModal() {
    if (!g_introModalOpen) return;
    g_introModalFrames++;
    float fw = (float)g_renderWidth, fh = (float)g_renderHeight;
    DrawRectangle(0, 0, (int)fw, (int)fh, (Color){0, 0, 0, 210});
    float mw = 720.0f, mh = 420.0f, mx = (fw - mw) * 0.5f, my = (fh - mh) * 0.5f;
    float tbH = 52.0f;
    if (g_texModalTemplate.id != 0)
        DrawTexturePro(g_texModalTemplate, {0, 0, (float)g_texModalTemplate.width, (float)g_texModalTemplate.height},
                       {mx, my, mw, mh}, {0, 0}, 0.0f, WHITE);
    else { DrawRectangle((int)mx, (int)my, (int)mw, (int)mh, {28, 28, 36, 255}); DrawRectangleLinesEx({mx, my, mw, mh}, 2, {0, 200, 128, 255}); }
    float tf = GetScaledFontSize(BASE_FONT_SIZE) * 2.0f;
    float bf = GetScaledFontSize(BASE_FONT_SIZE) * 1.35f;
    const char* titleStr = "QUADTRON CITY NETWORK AUTHORITY";
    float tW = MeasureTextEx(gameFont, titleStr, tf, 0.0f).x;
    DrawTextEx(gameFont, titleStr, {mx + (mw - tW) * 0.5f, my + (tbH - tf) * 0.5f + mh * 0.02f}, tf, 0.0f, {0, 255, 128, 255});
    DrawWrappedText(
        "You're the newly contracted grid-runner for Quadtron City's transit network. "
        "Jack in, lay down the rail-links, build Silos containing the various human, "
        "transhuman and AI situated at the various clusters, route the cargo and "
        "survive the punishing upkeep across 6 in-game years. Your NET INCOME dictates "
        "your standing on the global leaderboard. You are what remains of the human "
        "workforce within the council of this society, so be sure to leave with your "
        "head held high before the Quadtron AI deems you obsolete.",
        mx + 40.0f, my + tbH + 22.0f, mw - 80.0f, my + 325.0f, bf, (Color){220, 240, 255, 255});
    // Two side-by-side buttons: BEGIN | HELP
    float btnW = 270.0f, btnH = 52.0f, btnGap = 24.0f, btnBarY = my + 348.0f;
    float totalBtnW = btnW * 2.0f + btnGap;
    float btnLeft = mx + (mw - totalBtnW) * 0.5f;
    Rectangle beginBtn = {btnLeft, btnBarY, btnW, btnH};
    Rectangle helpBtn  = {btnLeft + btnW + btnGap, btnBarY, btnW, btnH};
    Rectangle closeXBtn = { mx + mw - 42.0f - 8.0f, my + 4.0f, 42.0f, 42.0f };
    Vector2 mp = CustomGetMousePosition();
    bool hoverBegin = CheckCollisionPointRec(mp, beginBtn);
    bool hoverHelp  = CheckCollisionPointRec(mp, helpBtn);
    bool hoverCloseX = CheckCollisionPointRec(mp, closeXBtn);
    Texture2D btBegin = (hoverBegin && g_texModalConfirmSelected.id != 0) ? g_texModalConfirmSelected : g_texModalConfirmNotSelected;
    if (btBegin.id != 0) DrawTexturePro(btBegin, {0,0,(float)btBegin.width,(float)btBegin.height}, beginBtn, {0,0}, 0.0f, WHITE);
    else DrawRectangleRec(beginBtn, hoverBegin ? (Color){40,160,80,255} : (Color){30,120,60,255});
    const char* lblBegin = "BEGIN";
    float lbW = MeasureTextEx(gameFont, lblBegin, bf, 0.0f).x;
    DrawTextEx(gameFont, lblBegin, {beginBtn.x + (btnW - lbW) * 0.5f, beginBtn.y + (btnH - bf) * 0.5f - 4.0f}, bf, 0.0f, WHITE);
    Texture2D btHelp = (hoverHelp && g_texModalConfirmSelected.id != 0) ? g_texModalConfirmSelected : g_texModalConfirmNotSelected;
    if (btHelp.id != 0) DrawTexturePro(btHelp, {0,0,(float)btHelp.width,(float)btHelp.height}, helpBtn, {0,0}, 0.0f, WHITE);
    else DrawRectangleRec(helpBtn, hoverHelp ? (Color){40,100,200,255} : (Color){30,70,160,255});
    const char* lblHelp = "HELP";
    float lhW = MeasureTextEx(gameFont, lblHelp, bf, 0.0f).x;
    DrawTextEx(gameFont, lblHelp, {helpBtn.x + (btnW - lhW) * 0.5f, helpBtn.y + (btnH - bf) * 0.5f - 4.0f}, bf, 0.0f, WHITE);
    if (g_introModalFrames >= 2 && RawIsMouseButtonPressed(MOUSE_BUTTON_LEFT)) {
        if (hoverCloseX || hoverBegin) { g_introModalOpen = false; BlockMouseClicksAfterModalClose(); }
        if (hoverHelp)  { g_introModalOpen = false; g_helpModalOpen = true; g_helpModalFrames = 0; g_helpPage = 0; BlockMouseClicksAfterModalClose(); }
    }
}

// â”€â”€ Help Modal â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
// Multi-page reference guide. Opened from intro modal HELP button or H key at any time.
static void DrawHelpModal() {
    if (!g_helpModalOpen) return;
    g_helpModalFrames++;
    float fw = (float)g_renderWidth, fh = (float)g_renderHeight;
    DrawRectangle(0, 0, (int)fw, (int)fh, (Color){0, 0, 0, 210});
    float mw = 989.0f, mh = 695.0f, mx = (fw - mw) * 0.5f, my = (fh - mh) * 0.5f;
    if (g_texLargeModalTemplate.id != 0)
        DrawTexturePro(g_texLargeModalTemplate, {0,0,(float)g_texLargeModalTemplate.width,(float)g_texLargeModalTemplate.height},
                       {mx, my, mw, mh}, {0,0}, 0.0f, WHITE);
    else { DrawRectangle((int)mx,(int)my,(int)mw,(int)mh,{20,20,30,255}); DrawRectangleLinesEx({mx,my,mw,mh},2,{60,140,255,255}); }
    float tf = GetScaledFontSize(BASE_FONT_SIZE) * 1.9f;
    float bf = GetScaledFontSize(BASE_FONT_SIZE) * 1.6f; // Matched to stock market body font size
    float tbH = 52.0f;
    Color titleCol  = {80, 180, 255, 255};
    Color bodyCol   = {220, 240, 255, 255};
    Color accentCol = {255, 215, 60, 255};
    const char* titles[16] = {
        "HELP 1/16 - CORE CONTROLS",
        "HELP 2/16 - LINES & TRAINS",
        "HELP 3/16 - CARGO & INDUSTRY",
        "HELP 4/16 - BUREAU RULES",
        "HELP 5/16 - BUREAU COSTS & ROI",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "HELP 13/16 - MARKET PLAYBOOK",
        "HELP 14/16 - COST CONTROL",
        "HELP 15/16 - 6-YEAR RUNBOOK",
        "HELP 16/16 - LEADERBOARD META"
    };
    Vector2 titlePos = {mx + 40.0f, my + (tbH - tf) * 0.5f + mh * 0.015f};
    auto DrawColourSystemTitle = [&](const char* prefix, const char* colourName, Color colour, const char* systemName) {
        DrawTextEx(gameFont, prefix, titlePos, tf, 0.0f, titleCol);
        float x = titlePos.x + MeasureTextEx(gameFont, prefix, tf, 0.0f).x;
        DrawTextEx(gameFont, colourName, {x, titlePos.y}, tf, 0.0f, colour);
        x += MeasureTextEx(gameFont, colourName, tf, 0.0f).x;
        DrawTextEx(gameFont, systemName, {x, titlePos.y}, tf, 0.0f, titleCol);
    };
    if (g_helpPage >= 5 && g_helpPage <= 11) {
        switch (g_helpPage) {
            case 5:  DrawColourSystemTitle("HELP 6/16 - ",  "CARGO",   GetSystemColorShades((int)SiloSystem::SYS1_CARGO).colors[1],   ": MATERIALS INDUSTRY"); break;
            case 6:  DrawColourSystemTitle("HELP 7/16 - ",  "GREEN",   GetSystemColorShades((int)SiloSystem::SYS2_GREEN).colors[1],   ": GENERAL PATRIOTS"); break;
            case 7:  DrawColourSystemTitle("HELP 8/16 - ",  "MAGENTA", GetSystemColorShades((int)SiloSystem::SYS3_MAGENTA).colors[1], ": AI INDUSTRIAL"); break;
            case 8:  DrawColourSystemTitle("HELP 9/16 - ",  "ORANGE",  GetSystemColorShades((int)SiloSystem::SYS5_ORANGE).colors[1],  ": AI ADMINISTRATION"); break;
            case 9:  DrawColourSystemTitle("HELP 10/16 - ", "CYAN",    GetSystemColorShades((int)SiloSystem::SYS4_CYAN).colors[1],    ": AI TECHNOLOGY"); break;
            case 10: DrawColourSystemTitle("HELP 11/16 - ", "RED",     GetSystemColorShades((int)SiloSystem::SYS6_RED).colors[1],     ": TRANSHUMAN ELITES"); break;
            case 11: DrawColourSystemTitle("HELP 12/16 - ", "YELLOW",  GetSystemColorShades((int)SiloSystem::SYS7_YELLOW).colors[1],  ": CORPORATE EXECUTIVES"); break;
        }
    } else {
        DrawTextEx(gameFont, titles[g_helpPage], titlePos, tf, 0.0f, titleCol);
    }
    float lh   = bf * 1.3f;  // line height per wrapped block
    float paraGap = 0.0f;
    float textX = mx + 48.0f, textW = mw - 96.0f;
    float y = my + tbH + 24.0f + mh * 0.05f, maxY = my + 598.0f;
    float closeBtnW = 42.0f;
    float closeBtnH = 42.0f;
    Rectangle closeXBtn = { mx + mw - closeBtnW - 8.0f, my + 4.0f, closeBtnW, closeBtnH };
    if (g_helpPage == 0) {
        y = DrawWrappedText("SPACE cycles game speed. Keep SPEED QUICK or QUICKEST during growth phases, then PAUSE to plan expensive placements.",
            textX, y, textW, maxY, bf, bodyCol) + paraGap;
        y = DrawWrappedText("T enters Track mode, S Station mode, D Depot mode, F Factory mode, B Bureau mode, C Market, M Map, X Demolish, H Help.",
            textX, y, textW, maxY, bf, bodyCol) + paraGap;
        y = DrawWrappedText("Left/Right pan camera. Shift+Left/Right rotates. Up/Down pans forward/back. Shift+Up/Down changes altitude.",
            textX, y, textW, maxY, bf, bodyCol) + paraGap;
        DrawWrappedText("Core loop: build line -> establish line -> run trains -> place bureau floors -> convert income into more floors.",
            textX, y, textW, maxY, bf, accentCol);
    } else if (g_helpPage == 1) {
        y = DrawWrappedText("A line becomes ESTABLISHED only when connected station count reaches 2 or more. Most economy systems require established lines.",
            textX, y, textW, maxY, bf, bodyCol) + paraGap;
        y = DrawWrappedText("Train colors must match line system rules. Cargo trains support materials flow. Non-cargo systems drive bureau income.",
            textX, y, textW, maxY, bf, bodyCol) + paraGap;
        y = DrawWrappedText("Junction clicks are per-train route memory. Use this to keep cargo and passenger flows separated on shared infrastructure.",
            textX, y, textW, maxY, bf, bodyCol) + paraGap;
        y = DrawWrappedText("Use map mode to validate network shape quickly before committing to more stations, factories, and bureau clusters.",
            textX, y, textW, maxY, bf, bodyCol) + paraGap;
        y = DrawWrappedText("Expansion order matters: station pair first, train second, bureau third. Avoid expensive orphan stations.",
            textX, y, textW, maxY, bf, accentCol);
    } else if (g_helpPage == 2) {
        y = DrawWrappedText("Factories produce MAT into adjacent depot clusters. Cargo trains move MAT when entering station zones.",
            textX, y, textW, maxY, bf, bodyCol) + paraGap;
        y = DrawWrappedText("Cargo is the strategic bottleneck for bureaus. Build depot chains so outer-ring cargo checks pass in multiple districts.",
            textX, y, textW, maxY, bf, bodyCol) + paraGap;
        y = DrawWrappedText("Brown bureaus on established cargo lines also export stored MAT monthly: 1 MAT per floor for 100 CR, but only if that line's depots really hold stock.",
            textX, y, textW, maxY, bf, bodyCol) + paraGap;
        DrawWrappedText("Best bootstrap: 1 cargo train + 1 factory + depot cluster + early brown bureau, then pivot into a stronger paying colour line.",
            textX, y, textW, maxY, bf, accentCol);
    } else if (g_helpPage == 3) {
        y = DrawWrappedText("Bureau placement requires BOTH checks: INNER ring must touch a station tile on an established line; OUTER ring must have enough cargo.",
            textX, y, textW, maxY, bf, bodyCol) + paraGap;
        y = DrawWrappedText("If either rule fails, placement is blocked. Use ring visuals to validate before spending credits.",
            textX, y, textW, maxY, bf, bodyCol) + paraGap;
        y = DrawWrappedText("Bureau income only counts when linked line has a non-cargo system and that system has a moving train.",
            textX, y, textW, maxY, bf, bodyCol) + paraGap;
        DrawWrappedText("Cargo-linked bureaus are still useful for setup and silo logic, but they are not your primary score engine.",
            textX, y, textW, maxY, bf, accentCol);
    } else if (g_helpPage == 4) {
        y = DrawWrappedText("Bureau cost is now SYSTEM-BASED per floor. Final price = floors x costPerFloor, then Red build discount applies.",
            textX, y, textW, maxY, bf, bodyCol) + paraGap;
        y = DrawWrappedText("CARGO/NEUTRAL: 3000 CR per floor. Brown bureaus also sell 1 MAT per floor each month for 100 CR if linked line depots hold stock.",
            textX, y, textW, maxY, bf, bodyCol) + paraGap;
        y = DrawWrappedText("GREEN: 3500 CR per floor. MAGENTA: 4000 CR per floor. ORANGE: 4500 CR per floor.",
            textX, y, textW, maxY, bf, bodyCol) + paraGap;
        y = DrawWrappedText("CYAN: 5000 CR per floor. RED: 5500 CR per floor. YELLOW: 6000 CR per floor.",
            textX, y, textW, maxY, bf, bodyCol) + paraGap;
        y = DrawWrappedText("Revenue baseline remains 50 CR per floor per week-cycle for active eligible systems. Evaluate payback by system and upkeep pressure.",
            textX, y, textW, maxY, bf, bodyCol) + paraGap;
        DrawWrappedText("Practical rule: buy floors where uptime is stable and train movement is continuous. Idle lines delay payback.",
            textX, y, textW, maxY, bf, accentCol);
    } else if (g_helpPage == 5) {
        y = DrawWrappedText("Build correctly: use an ESTABLISHED line with 1 cargo train, 1 active factory/depot cargo cluster, and 1 station on that same line inside the activated cargo cluster.",
            textX, y, textW, maxY, bf, bodyCol) + paraGap;
        y = DrawWrappedText("Cost: cargo or neutral bureau floors cost 3000 CR each, but the cargo silo itself does not require bureau floors.",
            textX, y, textW, maxY, bf, bodyCol) + paraGap;
        y = DrawWrappedText("Benefit: each cargo silo unlocks 1 of 6 commodity listings. Magenta on that line doubles factory output for cargo checks.",
            textX, y, textW, maxY, bf, bodyCol) + paraGap;
        y = DrawWrappedText("Brown bureau effect: each floor sells 1 MAT per month from depots on that established line for 100 CR, consuming real stored MAT.",
            textX, y, textW, maxY, bf, bodyCol) + paraGap;
        DrawWrappedText("Cargo is still the bootstrap system: it opens materials, supports bureau placement, and now gives brown bureaus direct MAT sales.",
            textX, y, textW, maxY, bf, accentCol);
    } else if (g_helpPage == 6) {
        y = DrawWrappedText("Build correctly: run at least 1 green train on an ESTABLISHED line, place at least 1 station near a green district, and place a bureau on an inner-city hub station on that same line.",
            textX, y, textW, maxY, bf, bodyCol) + paraGap;
        y = DrawWrappedText("Cost: green bureau floors cost 3500 CR per floor. Green is the cheapest colour-specific bureau route after cargo.",
            textX, y, textW, maxY, bf, bodyCol) + paraGap;
        y = DrawWrappedText("Benefit: each qualifying hub bureau creates 1 green silo and unlocks green listings up to 6 total. The system uses a strict 1 bureau to 1 listing rule, capped by your green-station count.",
            textX, y, textW, maxY, bf, bodyCol) + paraGap;
        y = DrawWrappedText("Bureau floor effect: each floor used by a green silo adds 10% bullish green-share performance and improves green bullish trend odds.",
            textX, y, textW, maxY, bf, bodyCol) + paraGap;
        DrawWrappedText("Green is the cleanest early specialist play: cheaper than the executive colours and reliable when you have real hub coverage.",
            textX, y, textW, maxY, bf, accentCol);
    } else if (g_helpPage == 7) {
        y = DrawWrappedText("Build correctly: run at least 1 magenta train on an ESTABLISHED line with at least 1 magenta station and at least 1 industry station within 2 grid spaces of a factory.",
            textX, y, textW, maxY, bf, bodyCol) + paraGap;
        y = DrawWrappedText("Cost: bureau floors on magenta lines cost 4000 CR per floor. The magenta silo itself does not require a bureau to form.",
            textX, y, textW, maxY, bf, bodyCol) + paraGap;
        y = DrawWrappedText("Benefit: each magenta silo unlocks magenta listings up to 6 total, and established magenta lines double factory output for cargo silos on that line.",
            textX, y, textW, maxY, bf, bodyCol) + paraGap;
        y = DrawWrappedText("Bureau floor effect: every bureau floor linked to an active magenta line adds 10% bullish performance to BOTH magenta shares and commodity shares, capped at 3x total drift.",
            textX, y, textW, maxY, bf, bodyCol) + paraGap;
        DrawWrappedText("Magenta is the bridge system: it upgrades cargo productivity and turns the market into a stronger compounding engine.",
            textX, y, textW, maxY, bf, accentCol);
    } else if (g_helpPage == 8) {
        y = DrawWrappedText("Build correctly: run at least 1 orange train on an ESTABLISHED line with at least 1 orange station and at least 1 linked bureau station on that line.",
            textX, y, textW, maxY, bf, bodyCol) + paraGap;
        y = DrawWrappedText("Cost: orange bureau floors cost 4500 CR per floor.",
            textX, y, textW, maxY, bf, bodyCol) + paraGap;
        y = DrawWrappedText("Benefit: each orange silo unlocks orange listings up to 6 total and gives you a bureau-linked executive income path on that line.",
            textX, y, textW, maxY, bf, bodyCol) + paraGap;
        y = DrawWrappedText("Bureau floor effect: each floor reduces bureau cargo cost by 1 material when placing new bureaus, with a floor at zero.",
            textX, y, textW, maxY, bf, bodyCol) + paraGap;
        DrawWrappedText("Orange is a placement accelerator: build it when bureau expansion is limited more by cargo spend than by credits.",
            textX, y, textW, maxY, bf, accentCol);
    } else if (g_helpPage == 9) {
        y = DrawWrappedText("Build correctly: run at least 1 cyan train on an ESTABLISHED line with at least 1 cyan station and at least 1 linked bureau station on that line.",
            textX, y, textW, maxY, bf, bodyCol) + paraGap;
        y = DrawWrappedText("Cost: cyan bureau floors cost 5000 CR per floor.",
            textX, y, textW, maxY, bf, bodyCol) + paraGap;
        y = DrawWrappedText("Benefit: each cyan silo unlocks cyan listings up to 6 total and makes expensive networks easier to sustain.",
            textX, y, textW, maxY, bf, bodyCol) + paraGap;
        y = DrawWrappedText("Bureau floor effect: each floor cuts global running costs by 5%, capped at 95%, and also improves cyan bullish trend odds.",
            textX, y, textW, maxY, bf, bodyCol) + paraGap;
        DrawWrappedText("Cyan is the upkeep stabilizer. It is usually worth buying before very large expansion phases or before rescuing a bloated network.",
            textX, y, textW, maxY, bf, accentCol);
    } else if (g_helpPage == 10) {
        y = DrawWrappedText("Build correctly: run at least 1 red train on an ESTABLISHED line with at least 1 red station and at least 1 linked bureau station on that line.",
            textX, y, textW, maxY, bf, bodyCol) + paraGap;
        y = DrawWrappedText("Cost: red bureau floors cost 5500 CR per floor.",
            textX, y, textW, maxY, bf, bodyCol) + paraGap;
        y = DrawWrappedText("Benefit: each red silo unlocks red listings up to 6 total and turns high-credit construction plans into cheaper plays.",
            textX, y, textW, maxY, bf, bodyCol) + paraGap;
        y = DrawWrappedText("Bureau floor effect: each floor cuts build credit costs by 10%, capped at 90%, and also improves red bullish trend odds.",
            textX, y, textW, maxY, bf, bodyCol) + paraGap;
        DrawWrappedText("Red is the capex weapon. Use it before major station, bureau, factory, or track pushes when cash is the limiting resource.",
            textX, y, textW, maxY, bf, accentCol);
    } else if (g_helpPage == 11) {
        y = DrawWrappedText("Build correctly: use an ESTABLISHED line with at least 1 yellow train, at least 1 station near a yellow cluster, and at least 1 eligible linked bureau on that line.",
            textX, y, textW, maxY, bf, bodyCol) + paraGap;
        y = DrawWrappedText("Cost: yellow bureau floors cost 6000 CR per floor, the highest in the game.",
            textX, y, textW, maxY, bf, bodyCol) + paraGap;
        y = DrawWrappedText("Benefit: the first yellow silo unlocks the STOCK & COMMODITIES MARKET. Stronger yellow bureau support makes the market calmer instead of wilder.",
            textX, y, textW, maxY, bf, bodyCol) + paraGap;
        y = DrawWrappedText("Bureau floor effect: the unique bureau floors used by yellow silos reduce market chaos by 1 per floor from a base of 50, giving calmer swings and more controllable market play.",
            textX, y, textW, maxY, bf, bodyCol) + paraGap;
        DrawWrappedText("Yellow is a late accelerator. Build it after your rail economy is already stable enough to survive without immediate bureau payback.",
            textX, y, textW, maxY, bf, accentCol);
    } else if (g_helpPage == 12) {
        y = DrawWrappedText("Market revenue adds passive credits each cycle once unlocked. Treat it as acceleration, not replacement, for bureau-led growth.",
            textX, y, textW, maxY, bf, bodyCol) + paraGap;
        y = DrawWrappedText("Unlock sequence: establish a yellow-capable ecosystem, then keep network health stable so market gains are not erased by upkeep spikes.",
            textX, y, textW, maxY, bf, bodyCol) + paraGap;
        y = DrawWrappedText("When market is active, continue expanding bureau floors on high-uptime lines. Dual income streams produce the best late-game scaling.",
            textX, y, textW, maxY, bf, bodyCol) + paraGap;
        DrawWrappedText("Use market timing to fund critical expansions, not decorative overbuild.",
            textX, y, textW, maxY, bf, accentCol);
    } else if (g_helpPage == 13) {
        y = DrawWrappedText("Weekly costs: trains. Monthly costs: track, stations, depots, factories, bureaus. Negative credits trigger a one-year bankruptcy grace.",
            textX, y, textW, maxY, bf, bodyCol) + paraGap;
        y = DrawWrappedText("Outer ring construction is cheaper. Use it for long corridors and logistics backbone, then concentrate high-value bureaus where rules permit.",
            textX, y, textW, maxY, bf, bodyCol) + paraGap;
        y = DrawWrappedText("Cyan cost reduction and Red build reduction are your strongest anti-upkeep and anti-capex levers.",
            textX, y, textW, maxY, bf, bodyCol) + paraGap;
        DrawWrappedText("Cut underperforming sections early with demolish mode if they consume upkeep without enabling new revenue.",
            textX, y, textW, maxY, bf, accentCol);
    } else if (g_helpPage == 14) {
        y = DrawWrappedText("YEAR 1-2: Build one reliable cargo bootstrap, establish the first paying non-cargo line, and place the first bureau floors.",
            textX, y, textW, maxY, bf, bodyCol) + paraGap;
        y = DrawWrappedText("YEAR 3-4: Scale bureau count and floors. Add silos that improve compounding, especially Cyan, Red, and Orange, before broad expansion.",
            textX, y, textW, maxY, bf, bodyCol) + paraGap;
        y = DrawWrappedText("YEAR 5: Optimize for net score, reduce waste, and push high-confidence floor additions with active train coverage.",
            textX, y, textW, maxY, bf, bodyCol) + paraGap;
        DrawWrappedText("YEAR 6: Avoid risky long-payback projects. Convert liquidity into immediate, low-risk score gains.",
            textX, y, textW, maxY, bf, (Color){255, 80, 80, 255});
    } else {
        y = DrawWrappedText("Final score is your credits/net-income state at contract end. Leaderboard is global and highly sensitive to late-game efficiency.",
            textX, y, textW, maxY, bf, bodyCol) + paraGap;
        y = DrawWrappedText("Top runs maintain train uptime, avoid stranded assets, and place bureaus where both placement rules and system payout conditions hold.",
            textX, y, textW, maxY, bf, bodyCol) + paraGap;
        y = DrawWrappedText("Common losses: overbuilding track, unlocking systems without bureau support, and carrying high upkeep into Year 6.",
            textX, y, textW, maxY, bf, bodyCol) + paraGap;
        DrawWrappedText("Leaderboard rule: build for compounding first, aesthetics second.",
            textX, y, textW, maxY, bf, (Color){255, 80, 80, 255});
    }
    // Bottom buttons: PREV | CLOSE | NEXT
    float btnW = 200.0f, btnH = 48.0f, btnGap = 20.0f;
    float btnBarY = my + mh - 68.0f;
    float totalW  = btnW * 3.0f + btnGap * 2.0f;
    float btnStartX = mx + (mw - totalW) * 0.5f;
    Rectangle prevBtn  = {btnStartX,                     btnBarY, btnW, btnH};
    Rectangle closeBtn = {btnStartX + btnW + btnGap,     btnBarY, btnW, btnH};
    Rectangle nextBtn  = {btnStartX + (btnW + btnGap)*2, btnBarY, btnW, btnH};
    Vector2 mp = CustomGetMousePosition();
    bool hoverPrev  = g_helpPage > 0               && CheckCollisionPointRec(mp, prevBtn);
    bool hoverClose = CheckCollisionPointRec(mp, closeBtn);
    bool hoverNext  = g_helpPage < kHelpPageCount-1 && CheckCollisionPointRec(mp, nextBtn);
    bool hoverCloseX = CheckCollisionPointRec(mp, closeXBtn);
    auto DrawHelpBtn = [&](Rectangle btn, const char* lbl, bool active, bool hover) {
        Texture2D bt = (hover && active && g_texModalConfirmSelected.id != 0) ? g_texModalConfirmSelected : g_texModalConfirmNotSelected;
        if (bt.id != 0 && active) DrawTexturePro(bt, {0,0,(float)bt.width,(float)bt.height}, btn, {0,0}, 0.0f, WHITE);
        else DrawRectangleRec(btn, active ? (hover ? (Color){60,140,220,255} : (Color){40,100,180,255}) : (Color){50,50,60,255});
        float lW = MeasureTextEx(gameFont, lbl, bf, 0.0f).x;
        DrawTextEx(gameFont, lbl, {btn.x + (btnW - lW) * 0.5f, btn.y + (btnH - bf) * 0.5f - 3.0f}, bf, 0.0f,
                   active ? WHITE : (Color){80, 80, 90, 255});
    };
    DrawHelpBtn(prevBtn,  "< PREV", g_helpPage > 0,               hoverPrev);
    DrawHelpBtn(closeBtn, "CLOSE",  true,                          hoverClose);
    DrawHelpBtn(nextBtn,  "NEXT >", g_helpPage < kHelpPageCount-1, hoverNext);
    // Page indicator dots
    float dotR = 6.0f, dotGap = 18.0f;
    float dotTotalW = kHelpPageCount * (dotR * 2.0f) + (kHelpPageCount - 1) * dotGap;
    float dotX = mx + (mw - dotTotalW) * 0.5f, dotY = btnBarY - 22.0f;
    for (int i = 0; i < kHelpPageCount; i++) {
        Color dc = (i == g_helpPage) ? (Color){80,180,255,255} : (Color){70,70,90,255};
        DrawCircle((int)(dotX + i * (dotR * 2.0f + dotGap) + dotR), (int)dotY, dotR, dc);
    }
    if (g_helpModalFrames >= 2 && RawIsMouseButtonPressed(MOUSE_BUTTON_LEFT)) {
        if (hoverClose || hoverCloseX) {
            g_helpModalOpen = false;
            g_helpModalFrames = 0;
            BlockMouseClicksAfterModalClose();
        }
        if (hoverPrev && g_helpPage > 0)               g_helpPage--;
        if (hoverNext && g_helpPage < kHelpPageCount-1) g_helpPage++;
    }
    // H key close is handled by the main toggle in the input handler (line ~8431)
}

static void DrawYear5WarningModal() {
    if (!g_year5ModalOpen) return;
    g_year5ModalFrames++;
    float fw=(float)g_renderWidth, fh=(float)g_renderHeight;
    DrawRectangle(0,0,(int)fw,(int)fh,(Color){0,0,0,210});
    float mw=720.0f, mh=400.0f, mx=(fw-mw)*0.5f, my=(fh-mh)*0.5f, tbH=52.0f;
    if (g_texModalTemplate.id!=0)
        DrawTexturePro(g_texModalTemplate,{0,0,(float)g_texModalTemplate.width,(float)g_texModalTemplate.height},
                       {mx,my,mw,mh},{0,0},0.0f,WHITE);
    else { DrawRectangle((int)mx,(int)my,(int)mw,(int)mh,{28,28,36,255}); DrawRectangleLinesEx({mx,my,mw,mh},2,{255,80,80,255}); }
    float tf=GetScaledFontSize(BASE_FONT_SIZE)*2.0f, bf=GetScaledFontSize(BASE_FONT_SIZE)*1.35f;
    const char* titleStr="CITY PLANNING REVIEW -- YEAR 5 OF 6";
    float tW=MeasureTextEx(gameFont,titleStr,tf,0.0f).x;
    DrawTextEx(gameFont,titleStr,{mx+(mw-tW)*0.5f,my+(tbH-tf)*0.5f+mh*0.02f},tf,0.0f,{255,80,80,255});
    float btnW=320.0f, btnH=52.0f, btnBarTop=316.0f;
    Rectangle dismissBtn={mx+(mw-btnW)*0.5f,my+btnBarTop,btnW,btnH};
    Rectangle closeXBtn={mx+mw-28.0f-12.0f,my+10.0f,28.0f,28.0f};
    // Body text â€” two passes: first plain, then Quadtron name in gold
    DrawWrappedText(
        "Your contract concludes at the end of Year 6. You have ONE YEAR to perfect "
        "your network and maximise NET INCOME before you are replaced by:",
        mx+40.0f,my+tbH+18.0f,mw-80.0f,my+tbH+110.0f,bf,(Color){220,240,255,255});
    const char* qtName="The Quadtron City Active-Terminal 3.0";
    float qtW=MeasureTextEx(gameFont,qtName,bf,0.0f).x;
    DrawTextEx(gameFont,qtName,{mx+(mw-qtW)*0.5f,my+tbH+118.0f},bf,0.0f,(Color){255,215,60,255});
    DrawWrappedText("Make it count.",mx+40.0f,my+tbH+155.0f,mw-80.0f,my+btnBarTop-10.0f,bf,(Color){220,240,255,255});
    Vector2 mp=CustomGetMousePosition();
    bool hover=CheckCollisionPointRec(mp,dismissBtn);
    bool hoverCloseX=CheckCollisionPointRec(mp,closeXBtn);
    Texture2D bt=(hover&&g_texModalConfirmSelected.id!=0)?g_texModalConfirmSelected:g_texModalConfirmNotSelected;
    if (bt.id!=0) DrawTexturePro(bt,{0,0,(float)bt.width,(float)bt.height},dismissBtn,{0,0},0.0f,WHITE);
    else DrawRectangleRec(dismissBtn,hover?(Color){160,40,40,255}:(Color){120,30,30,255});
    const char* lbl="UNDERSTOOD";
    float lw=MeasureTextEx(gameFont,lbl,bf,0.0f).x;
    DrawTextEx(gameFont,lbl,{dismissBtn.x+(btnW-lw)*0.5f,dismissBtn.y+(btnH-bf)*0.5f-4.0f},bf,0.0f,WHITE);
    if (g_year5ModalFrames>=2 && RawIsMouseButtonPressed(MOUSE_BUTTON_LEFT) && (hover || hoverCloseX)) {
        g_year5ModalOpen=false;
        BlockMouseClicksAfterModalClose();
    }
}

// End-game screen drawn over everything; SPACE signals exit to BBS
static void DrawEndGameScreen() {
    if (!g_gameOver) return;
    float dt = GetFrameTime();
    if (dt <= 0.0f || dt > 0.1f) dt = 1.0f / 60.0f;
    g_gameOverTimer += dt;
    float fw=(float)g_renderWidth, fh=(float)g_renderHeight;
    float tf=GetScaledFontSize(BASE_FONT_SIZE)*2.2f;
    float bf=GetScaledFontSize(BASE_FONT_SIZE)*1.35f;
    float sf=GetScaledFontSize(BASE_FONT_SIZE)*1.2f;

    if (g_gameOverPhase == 0) {
        float t = Clamp(g_gameOverTimer / 1.2f, 0.0f, 1.0f);
        unsigned char fadeA = (unsigned char)(180.0f * t);
        DrawRectangle(0,0,(int)fw,(int)fh,{0,0,0,fadeA});

        float topY = -fh + (fh * t);
        float botY = fh - (fh * t);

        if (g_texGameOver1.id != 0) {
            DrawTexturePro(g_texGameOver1,
                {0,0,(float)g_texGameOver1.width,(float)g_texGameOver1.height},
                {0,topY,fw,fh},
                {0,0},0.0f,WHITE);
        }
        if (g_texGameOver2.id != 0) {
            DrawTexturePro(g_texGameOver2,
                {0,0,(float)g_texGameOver2.width,(float)g_texGameOver2.height},
                {0,botY,fw,fh},
                {0,0},0.0f,WHITE);
        }

        if (g_gameOverTimer > 1.2f && (sinf(GetTime()*3.5f) > 0.0f)) {
            const char* prompt="PRESS SPACE TO CONTINUE";
            float pW=MeasureTextEx(gameFont,prompt,bf,0.0f).x;
            DrawTextEx(gameFont,prompt,{(fw-pW)*0.5f,fh*0.92f},bf,0.0f,WHITE);
        }
        if (g_gameOverTimer > 1.2f && CustomIsKeyPressed(KEY_SPACE)) {
            g_gameOverPhase = 1;
            g_gameOverTimer = 0.0f;
        }
        return;
    }

    DrawRectangle(0,0,(int)fw,(int)fh,{0,0,0,235});
    const char* endTitle="GLOBAL LEADERBOARD";
    float etW=MeasureTextEx(gameFont,endTitle,tf,0.0f).x;
    DrawTextEx(gameFont,endTitle,{(fw-etW)*0.5f,fh*0.07f},tf,0.0f,{255,215,60,255});
    char scoreLine[160];
    snprintf(scoreLine,sizeof(scoreLine),"%s  --  FINAL NET INCOME: %d CR",g_username,g_finalScore);
    float slW=MeasureTextEx(gameFont,scoreLine,bf,0.0f).x;
    DrawTextEx(gameFont,scoreLine,{(fw-slW)*0.5f,fh*0.16f},bf,0.0f,{220,240,255,255});
    DrawLeaderboardTable(fw*0.5f,fh*0.58f,fw*0.54f,fh*0.54f,sf);
    if (g_gameOverTimer > 5.0f || CustomIsKeyPressed(KEY_SPACE)) {
        RestartToSplashAfterGameOver();
    }
}

// â”€â”€ Splash Screen â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
// Returns true while splash is showing (GameLoopBody should return immediately).
// Returns false when splash is Done so the game runs normally.
static bool DrawSplashScreen() {
    if (g_splashPhase == SplashPhase::Done) return false;
    g_debugRenderStage = 10 + (int)g_splashPhase;

    // Update music during splash (music starts from the first screen)
    UpdateMusic();

    // If splash textures failed to load, skip splash to avoid black-screen launch.
    if (g_splashTex1.id == 0 || g_splashTex2.id == 0 || g_splashTex3.id == 0) {
        static bool warnedMissingSplash = false;
        if (!warnedMissingSplash) {
            printf("[DrawSplashScreen] WARNING: Missing splash textures; skipping splash sequence.\n");
            warnedMissingSplash = true;
        }
        g_splashPhase = SplashPhase::Done;
        g_introModalOpen = true;
        g_introModalFrames = 0;
        g_debugRenderStage = 19; // splash missing assets fallback
        return false;
    }

    float dt = GetFrameTime();
    // Embedded mode can report 0/invalid frame delta during splash-only startup.
    // Clamp to a stable timestep so fades and phase transitions progress.
    if (dt <= 0.0f || dt > 0.1f) dt = 1.0f / 60.0f;
    float fw = (float)g_renderWidth;
    float fh = (float)g_renderHeight;

    // Stretch a texture to fill the screen with a brightness tint
    auto DrawSplash = [&](Texture2D tex, float brightness) {
        if (tex.id == 0) return;
        unsigned char b = (unsigned char)(Clamp(brightness, 0.0f, 1.0f) * 255.0f);
        Color tint = {b, b, b, 255};
        Rectangle src = {0.0f, 0.0f, (float)tex.width, (float)tex.height};
        Rectangle dst = {0.0f, 0.0f, fw, fh};
        DrawTexturePro(tex, src, dst, {0.0f, 0.0f}, 0.0f, tint);
    };

    // Draw a texture at a vertical offset (for slide transitions), full-screen width/height
    auto DrawSplashAt = [&](Texture2D tex, float offsetY) {
        if (tex.id == 0) return;
        Rectangle src = {0.0f, 0.0f, (float)tex.width, (float)tex.height};
        Rectangle dst = {0.0f, offsetY, fw, fh};
        DrawTexturePro(tex, src, dst, {0.0f, 0.0f}, 0.0f, WHITE);
    };

    // Coloured text segments for typeout â€” total 42 chars
    struct SegData { const char* text; int len; Color col; };
    const SegData segs[4] = {
        {"CONSTRUCT",     9,  {255, 215,  60, 255}},   // gold
        {" the network. ",14, {255, 255, 255, 255}},   // white
        {"COMMAND",       7,  {255, 215,  60, 255}},   // gold
        {" the market.",  12, {255, 255, 255, 255}},   // white
    };
    const int   TOTAL_CHARS  = 42;
    const float fontSize     = 37.0f;
    const float lineSpacing  = 0.0f;

    // Advance timer and open drawing context
    g_splashTimer += dt;
    if (!g_standalone_mode && g_framebuffer_initialized) BeginTextureMode(g_framebuffer);
    else BeginDrawing();
    ClearBackground(BLACK);

    // â”€â”€ FadeIn1: SPLASH1 fades in over 1.5 s â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    if (g_splashPhase == SplashPhase::FadeIn1) {
        const float DURATION = 1.5f;
        DrawSplash(g_splashTex1, Clamp(g_splashTimer / DURATION, 0.0f, 1.0f));
        DrawGammaOverlay();
        DrawCustomCursor();
        if (!g_standalone_mode && g_framebuffer_initialized) EndTextureMode(); else EndDrawing();
        if (g_splashTimer >= DURATION) { g_splashPhase = SplashPhase::Mosaic2; g_splashTimer = 0.0f; }
        return true;
    }

    // â”€â”€ Slide2: SPLASH2 sweeps in from the bottom over 1.5 s â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    if (g_splashPhase == SplashPhase::Mosaic2) {
        const float DURATION = 1.5f;
        float progress = Clamp(g_splashTimer / DURATION, 0.0f, 1.0f);
        float eased    = 1.0f - (1.0f - progress) * (1.0f - progress);  // ease-out quad
        DrawSplash(g_splashTex1, 1.0f);
        DrawSplashAt(g_splashTex2, fh * (1.0f - eased));
        DrawGammaOverlay();
        DrawCustomCursor();
        if (!g_standalone_mode && g_framebuffer_initialized) EndTextureMode(); else EndDrawing();
        if (g_splashTimer >= DURATION) { g_splashPhase = SplashPhase::Mosaic3; g_splashTimer = 0.0f; }
        return true;
    }

    // â”€â”€ Slide3: SPLASH3 sweeps in from the top over 1.5 s â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    if (g_splashPhase == SplashPhase::Mosaic3) {
        const float DURATION = 1.5f;
        float progress = Clamp(g_splashTimer / DURATION, 0.0f, 1.0f);
        float eased    = 1.0f - (1.0f - progress) * (1.0f - progress);  // ease-out quad
        DrawSplash(g_splashTex1, 1.0f);
        DrawSplashAt(g_splashTex2, 0.0f);
        DrawSplashAt(g_splashTex3, -fh * (1.0f - eased));
        DrawGammaOverlay();
        DrawCustomCursor();
        if (!g_standalone_mode && g_framebuffer_initialized) EndTextureMode(); else EndDrawing();
        if (g_splashTimer >= DURATION) {
            g_splashPhase    = SplashPhase::DimType;
            g_splashTimer    = 0.0f;
            g_splash12Bright = 1.0f;
            g_splashTypeChars = 0;
            g_splashTypeTimer = 0.0f;
        }
        return true;
    }

    // â”€â”€ DimType: SPLASH1+2 dim to 0.35, then text types out â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    if (g_splashPhase == SplashPhase::DimType) {
        const float DIM_DURATION  = 0.8f;
        const float CHAR_INTERVAL = 0.055f;
        if (g_splashTimer <= DIM_DURATION) {
            g_splash12Bright = 1.0f - (g_splashTimer / DIM_DURATION) * 0.65f;
        } else {
            g_splash12Bright  = 0.35f;
            g_splashTypeTimer += dt;
            while (g_splashTypeTimer >= CHAR_INTERVAL && g_splashTypeChars < TOTAL_CHARS) {
                g_splashTypeChars++;
                g_splashTypeTimer -= CHAR_INTERVAL;
            }
            if (g_splashTypeChars >= TOTAL_CHARS) {
                g_splashPhase = SplashPhase::WaitSpace;
                g_splashTimer = 0.0f;
            }
        }
        const char* fullLine = "CONSTRUCT the network. COMMAND the market.";
        float totalW = MeasureTextEx(gameFont, fullLine, fontSize, lineSpacing).x;
        float textX  = (fw - totalW) * 0.5f;
        float textY  = fh * 0.60f;
        DrawSplash(g_splashTex1, g_splash12Bright);
        DrawSplash(g_splashTex2, g_splash12Bright);
        DrawSplash(g_splashTex3, 1.0f);
        int charsLeft = g_splashTypeChars;
        float cx = textX;
        for (int s = 0; s < 4 && charsLeft > 0; s++) {
            int draw = (charsLeft >= segs[s].len) ? segs[s].len : charsLeft;
            char buf[32]; memcpy(buf, segs[s].text, draw); buf[draw] = '\0';
            DrawTextEx(gameFont, buf, {cx, textY}, fontSize, lineSpacing, segs[s].col);
            cx += MeasureTextEx(gameFont, buf, fontSize, lineSpacing).x;
            charsLeft -= draw;
        }
        DrawGammaOverlay();
        DrawCustomCursor();
        if (!g_standalone_mode && g_framebuffer_initialized) EndTextureMode(); else EndDrawing();
        return true;
    }

    // â”€â”€ WaitSpace: full text + flashing prompt, SPACE starts the game â”€â”€â”€â”€â”€â”€â”€â”€â”€
    if (g_splashPhase == SplashPhase::WaitSpace) {
        const char* fullLine  = "CONSTRUCT the network. COMMAND the market.";
        float totalW = MeasureTextEx(gameFont, fullLine, fontSize, lineSpacing).x;
        float textX  = (fw - totalW) * 0.5f;
        float textY  = fh * 0.60f;
        const char* pressText = "PRESS SPACE TO BEGIN";
        float pressW = MeasureTextEx(gameFont, pressText, fontSize, lineSpacing).x;
        float pressX = (fw - pressW) * 0.5f;
        float pressY = textY + fontSize * 1.8f;
        bool  flash  = (sinf(GetTime() * 3.5f) > 0.0f);
        DrawSplash(g_splashTex1, 0.35f);
        DrawSplash(g_splashTex2, 0.35f);
        DrawSplash(g_splashTex3, 1.0f);
        float cx = textX;
        for (int s = 0; s < 4; s++) {
            DrawTextEx(gameFont, segs[s].text, {cx, textY}, fontSize, lineSpacing, segs[s].col);
            cx += MeasureTextEx(gameFont, segs[s].text, fontSize, lineSpacing).x;
        }
        if (flash) DrawTextEx(gameFont, pressText, {pressX, pressY}, fontSize, lineSpacing, WHITE);
        // "PRESS O FOR OPTIONS" below the space prompt
        const char* optionsText = "PRESS O FOR OPTIONS";
        float optW = MeasureTextEx(gameFont, optionsText, fontSize * 0.8f, lineSpacing).x;
        float optX = (fw - optW) * 0.5f;
        float optY = pressY + fontSize * 1.5f;
        DrawTextEx(gameFont, optionsText, {optX, optY}, fontSize * 0.8f, lineSpacing, (Color){140, 140, 140, 255});
        // "PRESS ESC TO QUIT" below options prompt
        const char* escText = "PRESS ESC TO QUIT";
        float escW = MeasureTextEx(gameFont, escText, fontSize * 0.8f, lineSpacing).x;
        float escX = (fw - escW) * 0.5f;
        float escY = optY + fontSize * 1.2f;
        DrawTextEx(gameFont, escText, {escX, escY}, fontSize * 0.8f, lineSpacing, (Color){100, 100, 100, 255});
        // After 30 s of inactivity show the global leaderboard
        if (g_splashTimer >= 30.0f) {
            float lbFontSize = GetScaledFontSize(BASE_FONT_SIZE) * 1.15f;
            DrawLeaderboardTable(fw*0.5f, fh*0.5f, fw*0.48f, fh*0.58f, lbFontSize);
        }
        bool optionsClosedThisFrame = false;
        bool quitModalDismissedThisFrame = false;

        // Options screen overlay
        if (g_optionsScreen == OptionsScreen::Visible) {
            bool optionsWasVisible = true;
            HandleOptionsInput();
            optionsClosedThisFrame = optionsWasVisible && g_optionsScreen != OptionsScreen::Visible;
            DrawOptionsScreen();
        }
        // Quit-to-desktop modal overlay (drawn on top of splash)
        DrawQuitConfirmModal(g_quitConfirmModal, (int)fw, (int)fh);
        DrawGammaOverlay();
        DrawCustomCursor();
        if (!g_standalone_mode && g_framebuffer_initialized) EndTextureMode(); else EndDrawing();

        // Handle quit modal result
        if (g_quitConfirmModal.yesClicked) {
            g_quitConfirmModal = {};
            g_quitConfirmModalOpen = false;
            if (g_standalone_mode) {
                g_exit_requested = true;
                return false; // signal exit
            } else {
                g_exit_requested = true;
                return false;
            }
        }
        if (g_quitConfirmModal.noClicked) {
            quitModalDismissedThisFrame = true;
            g_quitConfirmModal = {};
            g_quitConfirmModalOpen = false;
        }

        if (g_quitConfirmModalOpen) return true; // block other input while modal is open
        if (g_optionsScreen == OptionsScreen::Visible) return true; // block game input
        if (!quitModalDismissedThisFrame && !optionsClosedThisFrame && CustomIsKeyPressed(KEY_ESCAPE)) {
            g_quitConfirmModal = {};
            g_quitConfirmModal.open = true;
            g_quitConfirmModal.quitToDesktop = true;
            g_quitConfirmModalOpen = true;
        }
        if (CustomIsKeyPressed(KEY_O)) {
            g_optionsScreen = OptionsScreen::Visible;
            g_optionsSelection = 0;
        }
        if (CustomIsKeyPressed(KEY_SPACE)) {
            g_splashTimer = 0.0f;
            g_splashPhase = SplashPhase::Done;
            g_introModalOpen = true;
            g_introModalFrames = 0;
        }
        return true;
    }

    // Fallback â€” should never reach here
    if (!g_standalone_mode && g_framebuffer_initialized) EndTextureMode(); else EndDrawing();
    return false;
}

