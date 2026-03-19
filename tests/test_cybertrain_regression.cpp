#include <iostream>
#include <set>
#include <string>
#include <vector>

#define main cybertrain_standalone_entry
#include "../Data/games/CyberTrain/main.cpp"
#undef main

static PlacedPlatform MakeStationTile(float centerX, float centerZ, int orientation, int stationPart) {
    PlacedPlatform p = {};
    p.isStation = true;
    p.isDepot = false;
    p.placementOrientation = orientation;
    p.stationPart = stationPart;
    const float off = (stationPart - 1.5f) * g_gridSpacing;
    switch (orientation) {
        case 0: p.position = { centerX + off, 0.0f, centerZ }; break;
        case 1: p.position = { centerX, 0.0f, centerZ + off }; break;
        case 2: p.position = { centerX - off, 0.0f, centerZ }; break;
        case 3: p.position = { centerX, 0.0f, centerZ - off }; break;
        default: p.position = { centerX, 0.0f, centerZ }; break;
    }
    return p;
}

static std::vector<int> AddStation(float centerX, float centerZ, int orientation, const char* name) {
    std::vector<int> indices;
    for (int part = 0; part < 4; part++) {
        PlacedPlatform p = MakeStationTile(centerX, centerZ, orientation, part);
        if (name) strncpy(p.stationName, name, sizeof(p.stationName) - 1);
        p.stationDelayMode = 0;
        indices.push_back((int)g_placedPlatforms.size());
        g_placedPlatforms.push_back(p);
    }
    return indices;
}

static void AddLine(int id, const char* name, Color color, const std::vector<int>& platformIndices, int chosenSystem = -1) {
    Line line = {};
    line.id = id;
    line.name = name;
    line.color = color;
    line.chosenSystem = chosenSystem;
    line.stationCount = 0;
    for (int pi : platformIndices) line.platformIndices.insert(pi);
    line.stationCount = CountPhysicalStationsInLine(line, g_placedPlatforms);
    g_lines.push_back(line);
    g_establishedLineIds.insert(id);
}

static void AddTrain(int id, int lineId, PlacedTrain::TrainType type, const std::vector<Vector3>& path) {
    PlacedTrain t = {};
    t.id = id;
    t.lineId = lineId;
    t.type = type;
    t.path = path;
    t.pathProgress = 0.0f;
    t.direction = 1.0f;
    t.pathLength = GetPathLength(path);
    t.position = path.empty() ? Vector3{0.0f, 0.0f, 0.0f} : path.front();
    g_placedTrains.push_back(t);
}

static void ResetCyberTrainState() {
    g_playerCredits = 50000;
    g_placedPlatforms.clear();
    g_placedTrains.clear();
    g_placedFactories.clear();
    g_placedBureaus.clear();
    g_lines.clear();
    g_silos.clear();
    g_cachedBureauLineId.clear();
    g_establishedLineIds.clear();
    g_declinedComponentKeys.clear();
    g_declinedNeutralBranchPlatformKeys.clear();
    g_lockedBranchOwnerLineId.clear();
    g_demolishNeutralizedPlatformKeys.clear();
    g_overpassGroupsByPosKey.clear();
    g_demolishConfirmModal = {};
    g_stationModal = {};
    g_selectedTrainIndex = -1;
    g_platformCacheDirty = true;
    g_lineCacheDirty = true;
}

static bool Expect(bool condition, const std::string& message) {
    if (!condition) {
        std::cerr << "[FAIL] " << message << "\n";
        return false;
    }
    return true;
}

static bool TestStationIdentityIsolation() {
    ResetCyberTrainState();
    std::vector<int> stationA = AddStation(0.0f, 0.0f, 0, "A");
    std::vector<int> stationB = AddStation(20.0f, 0.0f, 0, "B");

    if (!Expect(!SamePhysicalStation(g_placedPlatforms[stationA[3]], g_placedPlatforms[stationB[0]], g_gridSpacing),
                "nearby aligned stations should not be treated as the same physical station")) return false;

    std::vector<int> collected = CollectPhysicalStationTileIndices(stationA[2], g_placedPlatforms, g_gridSpacing);
    std::set<int> collectedSet(collected.begin(), collected.end());
    std::set<int> expected(stationA.begin(), stationA.end());
    return Expect(collectedSet == expected, "CollectPhysicalStationTileIndices should return only the clicked station tiles");
}

static bool TestStationModalIsolation() {
    ResetCyberTrainState();
    std::vector<int> stationA = AddStation(0.0f, 0.0f, 0, "OLD_A");
    std::vector<int> stationB = AddStation(20.0f, 0.0f, 0, "OLD_B");

    StationModalData modal = {};
    modal.anchorPlatformIndex = stationA[0];
    strncpy(modal.nameBuffer, "ALPHA", sizeof(modal.nameBuffer) - 1);
    modal.delayMode = 2;
    CommitStationModal(modal);

    for (int idx : stationA) {
        if (!Expect(std::string(g_placedPlatforms[idx].stationName) == "ALPHA", "CommitStationModal should update only the target station name")) return false;
        if (!Expect(g_placedPlatforms[idx].stationDelayMode == 2, "CommitStationModal should update only the target station dwell")) return false;
    }
    for (int idx : stationB) {
        if (!Expect(std::string(g_placedPlatforms[idx].stationName) == "OLD_B", "CommitStationModal should not rename a nearby aligned station")) return false;
        if (!Expect(g_placedPlatforms[idx].stationDelayMode == 0, "CommitStationModal should not change dwell on a nearby aligned station")) return false;
    }

    ResetCyberTrainState();
    stationA = AddStation(0.0f, 0.0f, 0, "NEW_A");
    stationB = AddStation(20.0f, 0.0f, 0, "KEEP_B");
    g_playerCredits = 100;
    modal = {};
    modal.isNewBuild = true;
    modal.anchorPlatformIndex = stationA[0];
    CancelStationModal(modal);

    if (!Expect((int)g_placedPlatforms.size() == 4, "CancelStationModal should remove only the cancelled station")) return false;
    for (const auto& p : g_placedPlatforms) {
        if (!Expect(std::string(p.stationName) == "KEEP_B", "CancelStationModal should leave the nearby station untouched")) return false;
    }
    return Expect(g_playerCredits == 1100, "CancelStationModal should refund the cancelled station cost");
}

static bool TestAdjacentLineDemolishIsolation() {
    ResetCyberTrainState();
    std::vector<int> cargoNear = AddStation(0.0f, 0.0f, 0, "CARGO_NEAR");
    std::vector<int> cargoFar = AddStation(60.0f, 0.0f, 0, "CARGO_FAR");
    std::vector<int> cyanNear = AddStation(20.0f, 0.0f, 0, "CYAN_NEAR");
    std::vector<int> cyanFar = AddStation(80.0f, 0.0f, 0, "CYAN_FAR");

    std::vector<int> cargoLinePlatforms = cargoNear;
    cargoLinePlatforms.insert(cargoLinePlatforms.end(), cargoFar.begin(), cargoFar.end());
    std::vector<int> cyanLinePlatforms = cyanNear;
    cyanLinePlatforms.insert(cyanLinePlatforms.end(), cyanFar.begin(), cyanFar.end());

    AddLine(101, "Cargo Line", (Color){139, 90, 43, 255}, cargoLinePlatforms);
    AddLine(202, "Cyan Line", (Color){0, 220, 255, 255}, cyanLinePlatforms);

    AddTrain(1, 101, PlacedTrain::TrainType::Cargo, {g_placedPlatforms[cargoNear[0]].position, g_placedPlatforms[cargoFar[0]].position});
    AddTrain(2, 202, PlacedTrain::TrainType::Cyan, {g_placedPlatforms[cyanNear[0]].position, g_placedPlatforms[cyanFar[0]].position});
    AddTrain(3, 202, PlacedTrain::TrainType::Cyan, {g_placedPlatforms[cyanFar[0]].position, g_placedPlatforms[cyanNear[0]].position});

    g_demolishConfirmModal = {};
    g_demolishConfirmModal.isStationDemolish = true;
    g_demolishConfirmModal.anchorIdx = cargoNear[0];
    g_demolishConfirmModal.lineIdx = 0;
    strncpy(g_demolishConfirmModal.lineName, "Cargo Line", sizeof(g_demolishConfirmModal.lineName) - 1);

    ExecuteDemolishStationAndLine();

    if (!Expect((int)g_lines.size() == 1, "demolishing one station from a 2-station cargo line should delete only that line")) return false;
    if (!Expect(g_lines[0].id == 202, "the neighboring cyan line should remain after cargo demolish")) return false;

    int cyanPlatformCount = 0;
    int cargoNearPlatformCount = 0;
    for (const auto& p : g_placedPlatforms) {
        if (std::string(p.stationName) == "CYAN_NEAR" || std::string(p.stationName) == "CYAN_FAR") cyanPlatformCount++;
        if (std::string(p.stationName) == "CARGO_NEAR") cargoNearPlatformCount++;
    }
    if (!Expect(cyanPlatformCount == 8, "cyan stations should remain untouched after nearby cargo demolish")) return false;
    if (!Expect(cargoNearPlatformCount == 0, "only the demolished cargo station should be removed")) return false;

    if (!Expect(g_placedTrains.size() == 3, "demolish should not delete trains outright")) return false;
    if (!Expect(g_placedTrains[0].isPaused && g_placedTrains[0].lineId == -1, "cargo train should pause when its deleted line is demolished")) return false;
    if (!Expect(!g_placedTrains[1].isPaused && g_placedTrains[1].lineId == 202, "first cyan train should remain active")) return false;
    return Expect(!g_placedTrains[2].isPaused && g_placedTrains[2].lineId == 202, "second cyan train should remain active");
}

static bool TestJunctionSettingRoundTrip() {
    ResetCyberTrainState();
    PlacedTrain train = {};
    std::vector<Vector3> exits = {
        {  0.0f, 0.0f, -5.0f },
        {  5.0f, 0.0f,  0.0f },
        {  0.0f, 0.0f,  5.0f },
        { -5.0f, 0.0f,  0.0f }
    };
    train.SetJunctionSetting(0.0f, 0.0f, 4, &exits);

    std::vector<Vector3> reordered = {
        exits[1],
        exits[3],
        exits[0],
        exits[2]
    };
    int restoredPair = train.GetJunctionSetting(0.0f, 0.0f, &reordered);
    return Expect(restoredPair == 0, "junction settings should survive adjacency reordering by matching stored exit positions");
}

static bool TestCargoBureauMaterialSales() {
    ResetCyberTrainState();

    std::vector<int> cargoStations = AddStation(0.0f, 0.0f, 0, "CARGO_A");
    AddLine(101, "Cargo Export", (Color){139, 90, 43, 255}, cargoStations);

    PlacedPlatform ownedDepotA = {};
    ownedDepotA.isDepot = true;
    ownedDepotA.position = {20.0f, 0.0f, 0.0f};
    ownedDepotA.lineOwnerId = 101;
    ownedDepotA.depotCargo = 2;
    g_placedPlatforms.push_back(ownedDepotA);

    PlacedPlatform ownedDepotB = {};
    ownedDepotB.isDepot = true;
    ownedDepotB.position = {25.0f, 0.0f, 0.0f};
    ownedDepotB.lineOwnerId = 101;
    ownedDepotB.depotCargo = 3;
    g_placedPlatforms.push_back(ownedDepotB);

    PlacedPlatform foreignDepot = {};
    foreignDepot.isDepot = true;
    foreignDepot.position = {40.0f, 0.0f, 0.0f};
    foreignDepot.lineOwnerId = 202;
    foreignDepot.depotCargo = 4;
    g_placedPlatforms.push_back(foreignDepot);

    PlacedBureau bureau = {};
    bureau.position = {5.0f, 0.0f, 0.0f};
    bureau.floors = 3;
    g_placedBureaus.push_back(bureau);
    g_cachedBureauLineId.push_back(0);

    Silo cargoSilo = {};
    cargoSilo.system = SiloSystem::SYS1_CARGO;
    cargoSilo.lineId = 101;
    g_silos.push_back(cargoSilo);

    g_playerCredits = 0;
    int earned = ProcessCargoBureauMaterialSales(1);

    if (!Expect(earned == 300, "cargo bureau should sell one material per floor each month at 100 CR")) return false;
    if (!Expect(g_playerCredits == 300, "cargo bureau sale should add the sale proceeds to player credits")) return false;
    if (!Expect(g_placedPlatforms[(int)cargoStations.size()].depotCargo + g_placedPlatforms[(int)cargoStations.size() + 1].depotCargo == 2,
                "cargo bureau sale should remove sold materials from depots on the owning line")) return false;
    return Expect(g_placedPlatforms[(int)cargoStations.size() + 2].depotCargo == 4,
                  "cargo bureau sale should not remove materials from depots on other lines");
}

static bool TestChosenLineSystemPersistsRules() {
    ResetCyberTrainState();
    std::vector<int> mixedStations = AddStation(0.0f, 0.0f, 0, "MIXED");
    AddLine(101, "Chosen Cyan", (Color){0, 220, 255, 255}, mixedStations, (int)SiloSystem::SYS4_CYAN);

    if (!Expect(DetectStrictClusterSystemForLine(0) == (int)SiloSystem::SYS4_CYAN, "line should report its chosen system when established")) return false;
    if (!Expect(DoesEstablishedLineMatchTrainType(0, PlacedTrain::TrainType::Cyan), "chosen cyan line should accept cyan trains")) return false;
    if (!Expect(!DoesEstablishedLineMatchTrainType(0, PlacedTrain::TrainType::Cargo), "chosen cyan line should reject cargo trains even if stations later touch cargo")) return false;
    return Expect(GetBureauCostPerFloorForLineIndex(0) == 5000, "bureau cost should follow the persisted chosen system");
}

static bool TestPausedDetachedTrainStaysDetached() {
    ResetCyberTrainState();
    std::vector<int> cargoStations = AddStation(0.0f, 0.0f, 0, "CARGO_A");
    AddLine(101, "Cargo Line", (Color){139, 90, 43, 255}, cargoStations, (int)SiloSystem::SYS1_CARGO);

    PlacedTrain detached = {};
    detached.id = 1;
    detached.type = PlacedTrain::TrainType::Cargo;
    detached.lineId = -1;
    detached.isPaused = true;
    detached.path = { g_placedPlatforms[cargoStations[0]].position, g_placedPlatforms[cargoStations[3]].position };
    detached.pathLength = GetPathLength(detached.path);
    g_placedTrains.push_back(detached);

    RecomputeSilosAndMarket();

    return Expect(g_placedTrains[0].lineId == -1, "paused detached train should not be reattached during silo recompute");
}

static bool TestRestartClearsSessionResidue() {
    ResetCyberTrainState();
    g_lastFinalScore = 1234;
    g_demolishNeutralizedPlatformKeys.insert(MakePositionKey(10.0f, 20.0f));
    g_cyberTrainCamActive = true;
    g_cyberTrainCamTrainId = 77;
    g_cyberTrainCamSavedSpeed = SPEED_QUICKEST;
    g_currentGameSpeed = SPEED_SLOW;

    RestartToSplashAfterGameOver();

    if (!Expect(g_lastFinalScore == 0, "restart should clear sticky final score exports")) return false;
    if (!Expect(g_demolishNeutralizedPlatformKeys.empty(), "restart should clear demolish-neutralized platform keys")) return false;
    if (!Expect(!g_cyberTrainCamActive && g_cyberTrainCamTrainId == -1, "restart should clear follow-cam tracking state")) return false;
    return Expect(g_cyberTrainCamSavedSpeed == g_currentGameSpeed, "restart should refresh saved follow-cam speed to the new session default");
}

static bool TestFinalScoreExportConsumesValue() {
    ResetCyberTrainState();
    g_lastFinalScore = 4321;
    if (!Expect(GetLastFinalScore() == 4321, "GetLastFinalScore should return the pending score once")) return false;
    return Expect(GetLastFinalScore() == 0, "GetLastFinalScore should clear the pending score after export");
}

int main() {
    bool ok = true;
    ok = TestStationIdentityIsolation() && ok;
    ok = TestStationModalIsolation() && ok;
    ok = TestAdjacentLineDemolishIsolation() && ok;
    ok = TestJunctionSettingRoundTrip() && ok;
    ok = TestCargoBureauMaterialSales() && ok;
    ok = TestChosenLineSystemPersistsRules() && ok;
    ok = TestPausedDetachedTrainStaysDetached() && ok;
    ok = TestRestartClearsSessionResidue() && ok;
    ok = TestFinalScoreExportConsumesValue() && ok;

    if (!ok) return 1;
    std::cout << "[PASS] CyberTrain regression harness completed\n";
    return 0;
}
