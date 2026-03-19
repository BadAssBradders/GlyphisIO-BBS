// Forward declarations for functions defined in cybertrain_network_worldgen.cpp
// (included after this file in the single translation unit)
static std::vector<Vector3> GetSortedAdjacentPositions(const Vector3& position, const std::vector<PlacedPlatform>& platforms, float gridSize);
static int NumJunctionPairs(int exits);
static bool PairIndexToIJ(int exits, int pairIndex, int& outI, int& outJ);
static int DefaultJunctionPairIndex(const Vector3& center, const std::vector<Vector3>& exits);

static void RecomputeSilosAndMarket() {
    g_silos.clear();
    for (int i = 0; i < 7; i++) g_siloCountBySystem[i] = 0;
    g_commoditiesUnlocked = 0;
    g_greenStocksUnlocked = 0;
    g_magentaStocksUnlocked = 0;
    g_cyanStocksUnlocked = 0;
    g_orangeStocksUnlocked = 0;
    g_redStocksUnlocked = 0;
    g_greenGrowthFloorBonus = 0;
    g_cyanGrowthFloorBonus = 0;
    g_orangeGrowthFloorBonus = 0;
    g_redGrowthFloorBonus = 0;
    g_magentaGrowthFloorBonus = 0;
    g_marketUnlocked = false;
    g_marketChaos = 50;
    g_yellowEligibleBureauCount = 0;
    g_yellowStationsOnEstablishedLinesCount = 0;
    g_yellowTrainsOnEstablishedLinesCount = 0;
    g_totalStationsOnEstablishedLines = 0;
    g_establishedLineCount = 0;
    g_establishedLineIds.clear();
    snprintf(g_sys7DiagnosticMsg, sizeof(g_sys7DiagnosticMsg), "No established lines");
    bool sys7DiagnosticLocked = false;
    auto setSys7Diagnostic = [&](const char* fmt, ...) {
        if (sys7DiagnosticLocked) return;
        va_list args;
        va_start(args, fmt);
        vsnprintf(g_sys7DiagnosticMsg, sizeof(g_sys7DiagnosticMsg), fmt, args);
        va_end(args);
    };
    g_lineBureauSiloPotential.clear();

    for (auto& p : g_placedPlatforms) {
        if (p.isDepot) p.lineOwnerId = -1;
    }
    for (auto& f : g_placedFactories) {
        f.lineOwnerId = -1;
        f.depotOwnerId = -1;
    }

    if (g_lines.empty() || g_placedPlatforms.empty()) return;

    struct StationSnapshot {
        int stationId = -1;
        int lineId = -1;
        int lineIndex = -1;
        int platformIndex = -1;
        Vector3 position = { 0.0f, 0.0f, 0.0f };
        int cellX = -1;
        int cellZ = -1;
        long long positionKey = 0;
    };

    std::vector<StationSnapshot> stations;
    stations.reserve(g_placedPlatforms.size() / 2);

    for (int pi = 0; pi < (int)g_placedPlatforms.size(); pi++) {
        const PlacedPlatform& p = g_placedPlatforms[pi];
        if (p.isDepot || !p.isStation || p.stationPart != 3) continue;
        int lineIndex = GetLineIndexFromPlatformIndex(pi);
        if (lineIndex < 0) continue;

        StationSnapshot st;
        st.lineIndex = lineIndex;
        st.lineId = g_lines[lineIndex].id;
        st.platformIndex = pi;
        st.position = p.position;
        st.cellX = WorldToGridCell(p.position.x);
        st.cellZ = WorldToGridCell(p.position.z);
        st.positionKey = MakePositionKey(p.position.x, p.position.z);
        stations.push_back(st);
    }

    if (stations.empty()) return;

    std::vector<long long> stationKeys;
    stationKeys.reserve(stations.size());
    for (const auto& st : stations) stationKeys.push_back(st.positionKey);
    std::sort(stationKeys.begin(), stationKeys.end());
    stationKeys.erase(std::unique(stationKeys.begin(), stationKeys.end()), stationKeys.end());

    std::unordered_map<long long, int> stationIdByKey;
    stationIdByKey.reserve(stationKeys.size());
    for (int i = 0; i < (int)stationKeys.size(); i++) {
        stationIdByKey[stationKeys[i]] = i + 1;
    }
    for (auto& st : stations) st.stationId = stationIdByKey[st.positionKey];

    std::unordered_map<int, int> platformToStationIndex;
    for (int i = 0; i < (int)stations.size(); i++)
        platformToStationIndex[stations[i].platformIndex] = i;

    std::unordered_map<int, std::vector<int>> lineStationIndices;
    lineStationIndices.reserve(g_lines.size());
    for (int li = 0; li < (int)g_lines.size(); li++) {
        int lineId = g_lines[li].id;
        for (int pi : g_lines[li].platformIndices) {
            if (pi < 0 || pi >= (int)g_placedPlatforms.size()) continue;
            const PlacedPlatform& p = g_placedPlatforms[pi];
            if (p.isDepot || !p.isStation || p.stationPart != 3) continue;
            auto it = platformToStationIndex.find(pi);
            if (it != platformToStationIndex.end())
                lineStationIndices[lineId].push_back(it->second);
        }
    }

    std::set<int> establishedLineIds;
    for (auto& kv : lineStationIndices) {
        auto& idxs = kv.second;
        std::sort(idxs.begin(), idxs.end(), [&](int a, int b) {
            return stations[a].stationId < stations[b].stationId;
        });
        idxs.erase(std::unique(idxs.begin(), idxs.end(), [&](int a, int b) {
            return stations[a].stationId == stations[b].stationId;
        }), idxs.end());
        if ((int)idxs.size() >= 2) establishedLineIds.insert(kv.first);
    }

    g_establishedLineCount = (int)establishedLineIds.size();
    g_establishedLineIds = establishedLineIds;
    for (int lid : establishedLineIds) {
        auto it = lineStationIndices.find(lid);
        if (it != lineStationIndices.end()) g_totalStationsOnEstablishedLines += (int)it->second.size();
    }

    if (establishedLineIds.empty()) return;

    struct Sys1Diag {
        int cargoTrains = 0;
        int activeFactories = 0;
        int cargoClusterStations = 0;
        int qualifyingStations = 0;
        int silos = 0;
    };
    std::unordered_map<int, Sys1Diag> sys1ByLine;
    std::vector<std::string> siloDebugLines;
    siloDebugLines.reserve(establishedLineIds.size());

    // Map every station tile to a deterministic stationId on that line (nearest prime on same line).
    struct StationTileRef {
        int lineId = -1;
        int stationId = -1;
        int platformIndex = -1;
        Vector3 position = { 0.0f, 0.0f, 0.0f };
        int cellX = -1;
        int cellZ = -1;
    };
    std::vector<StationTileRef> stationTiles;
    stationTiles.reserve(g_placedPlatforms.size());
    for (int pi = 0; pi < (int)g_placedPlatforms.size(); pi++) {
        const auto& p = g_placedPlatforms[pi];
        if (p.isDepot || !p.isStation) continue;
        int lineIndex = GetLineIndexFromPlatformIndex(pi);
        if (lineIndex < 0) continue;
        int lineId = g_lines[lineIndex].id;
        if (establishedLineIds.find(lineId) == establishedLineIds.end()) continue;

        int bestStationId = -1;
        float bestDist = 1e30f;
        auto it = lineStationIndices.find(lineId);
        if (it != lineStationIndices.end()) {
            for (int sidx : it->second) {
                float d = Vector3Distance(p.position, stations[sidx].position);
                if (d < bestDist) {
                    bestDist = d;
                    bestStationId = stations[sidx].stationId;
                }
            }
        }
        if (bestStationId < 0) continue;

        StationTileRef ref;
        ref.lineId = lineId;
        ref.stationId = bestStationId;
        ref.platformIndex = pi;
        ref.position = p.position;
        ref.cellX = WorldToGridCell(p.position.x);
        ref.cellZ = WorldToGridCell(p.position.z);
        stationTiles.push_back(ref);
    }

    struct DepotOwnership {
        int depotIndex = -1;
        int depotId = -1;
        int lineOwnerId = -1;
        int ownerStationId = -1;
        Vector3 position = { 0.0f, 0.0f, 0.0f };
    };
    std::vector<DepotOwnership> depots;
    std::unordered_map<int, int> depotIdxToVec;

    for (int pi = 0; pi < (int)g_placedPlatforms.size(); pi++) {
        const auto& p = g_placedPlatforms[pi];
        if (!p.isDepot) continue;

        int chosenLine = -1;
        int chosenStationId = -1;
        for (const auto& st : stationTiles) {
            if (!IsOneTileManhattanAdjacent(p.position, st.position)) continue;
            if (chosenLine < 0 || st.lineId < chosenLine || (st.lineId == chosenLine && st.stationId < chosenStationId)) {
                chosenLine = st.lineId;
                chosenStationId = st.stationId;
            }
        }

        DepotOwnership dep;
        dep.depotIndex = pi;
        dep.depotId = (int)depots.size() + 1;
        dep.lineOwnerId = chosenLine;
        dep.ownerStationId = chosenStationId;
        dep.position = p.position;
        depotIdxToVec[pi] = (int)depots.size();
        depots.push_back(dep);
    }
    for (const auto& dep : depots) {
        if (dep.depotIndex >= 0 && dep.depotIndex < (int)g_placedPlatforms.size()) {
            g_placedPlatforms[dep.depotIndex].lineOwnerId = dep.lineOwnerId;
        }
    }

    struct FactoryOwnership {
        int factoryIndex = -1;
        int factoryId = -1;
        int lineOwnerId = -1;
        int depotOwnerId = -1;
    };
    std::vector<FactoryOwnership> factories;
    for (int fi = 0; fi < (int)g_placedFactories.size(); fi++) {
        int chosenDepotVec = -1;
        int chosenDepotId = -1;
        for (int di = 0; di < (int)depots.size(); di++) {
            if (!IsDepotAdjacentToFactoryFootprint(depots[di].position, g_placedFactories[fi].position)) continue;
            if (chosenDepotId < 0 || depots[di].depotId < chosenDepotId) {
                chosenDepotId = depots[di].depotId;
                chosenDepotVec = di;
            }
        }

        FactoryOwnership fo;
        fo.factoryIndex = fi;
        fo.factoryId = fi + 1;
        if (chosenDepotVec >= 0) {
            fo.depotOwnerId = depots[chosenDepotVec].depotId;
            fo.lineOwnerId = depots[chosenDepotVec].lineOwnerId;
        }
        factories.push_back(fo);
        if (fi >= 0 && fi < (int)g_placedFactories.size()) {
            g_placedFactories[fi].lineOwnerId = fo.lineOwnerId;
            g_placedFactories[fi].depotOwnerId = fo.depotOwnerId;
        }
    }

    // Train explicit line assignment. If missing, derive from path and persist.
    std::unordered_map<int, int> cargoTrainsPerLine;
    std::unordered_map<int, int> greenTrainsPerLine;
    std::unordered_map<int, int> magentaTrainsPerLine;
    std::unordered_map<int, int> cyanTrainsPerLine;
    std::unordered_map<int, int> orangeTrainsPerLine;
    std::unordered_map<int, int> redTrainsPerLine;
    std::unordered_map<int, int> yellowTrainsPerLine;
    for (auto& tr : g_placedTrains) {
        if (tr.isPaused && tr.lineId < 0) continue;
        if (establishedLineIds.find(tr.lineId) == establishedLineIds.end()) {
            int derivedLineId = -1;
            for (const auto& pathPos : tr.path) {
                for (int pi = 0; pi < (int)g_placedPlatforms.size(); pi++) {
                    if (Vector3Distance(pathPos, g_placedPlatforms[pi].position) >= 0.25f) continue;
                    int lineIndex = GetLineIndexFromPlatformIndex(pi);
                    if (lineIndex < 0) continue;
                    int candidate = g_lines[lineIndex].id;
                    if (establishedLineIds.find(candidate) == establishedLineIds.end()) continue;
                    if (derivedLineId < 0 || candidate < derivedLineId) derivedLineId = candidate;
                }
            }
            tr.lineId = derivedLineId;
        }
        if (establishedLineIds.find(tr.lineId) != establishedLineIds.end()) {
            if (tr.type == PlacedTrain::TrainType::Cargo) cargoTrainsPerLine[tr.lineId]++;
            if (tr.type == PlacedTrain::TrainType::Passenger) greenTrainsPerLine[tr.lineId]++;
            if (tr.type == PlacedTrain::TrainType::Magenta) magentaTrainsPerLine[tr.lineId]++;
            if (tr.type == PlacedTrain::TrainType::Cyan) cyanTrainsPerLine[tr.lineId]++;
            if (tr.type == PlacedTrain::TrainType::Orange) orangeTrainsPerLine[tr.lineId]++;
            if (tr.type == PlacedTrain::TrainType::Red) redTrainsPerLine[tr.lineId]++;
            if (tr.type == PlacedTrain::TrainType::Yellow) yellowTrainsPerLine[tr.lineId]++;
        }
    }

    float innerRingRadius = GetBureauInnerRingRadius();
    float bureauHalfFoot = g_gridSpacing * 1.0f;
    std::vector<char> bureauYellowEligible(g_placedBureaus.size(), 0);

    std::set<long long> innerCityHubTiles;
    CollectInnerCityHubTiles(innerCityHubTiles);

    struct StationFlags {
        bool nearGreen = false;
        bool inMagenta = false;
        bool inCyan = false;
        bool inOrange = false;
        bool inRed = false;
        bool nearYellow = false;
        bool nearInnerCityHub = false;
        bool hasIndustryAdj = false; // Industry station = within 2 grid spaces of a factory
    };
    std::unordered_map<long long, StationFlags> stationFlags;

    float bldProx = g_gridSpacing * 1.5f;
    for (const auto& stTile : stationTiles) {
        long long key = PackIntPair(stTile.lineId, stTile.stationId);
        StationFlags& flags = stationFlags[key];
        float wx = stTile.position.x;
        float wz = stTile.position.z;
        if (IsStationNearCluster(stTile.cellX, stTile.cellZ, ClusterType::ClusterGreen)
            || IsNearClusterBuilding(wx, wz, ClusterType::ClusterGreen, bldProx)) flags.nearGreen = true;
        if (IsStationInsideCluster(stTile.cellX, stTile.cellZ, ClusterType::ClusterMagenta)
            || IsNearClusterBuilding(wx, wz, ClusterType::ClusterMagenta, bldProx)) flags.inMagenta = true;
        if (IsStationInsideCluster(stTile.cellX, stTile.cellZ, ClusterType::ClusterCyan)
            || IsNearClusterBuilding(wx, wz, ClusterType::ClusterCyan, bldProx)) flags.inCyan = true;
        if (IsStationInsideCluster(stTile.cellX, stTile.cellZ, ClusterType::ClusterOrange)
            || IsNearClusterBuilding(wx, wz, ClusterType::ClusterOrange, bldProx)) flags.inOrange = true;
        if (IsStationInsideCluster(stTile.cellX, stTile.cellZ, ClusterType::ClusterRed)
            || IsNearClusterBuilding(wx, wz, ClusterType::ClusterRed, bldProx)) flags.inRed = true;
        if (IsStationNearCluster(stTile.cellX, stTile.cellZ, ClusterType::ClusterYellow)
            || IsNearClusterBuilding(wx, wz, ClusterType::ClusterYellow, bldProx)) flags.nearYellow = true;
        if (IsStationNearInnerCityHubTile(stTile.cellX, stTile.cellZ, innerCityHubTiles)) flags.nearInnerCityHub = true;
        for (const auto& f : g_placedFactories) {
            if (IsStationNearFactoryForIndustry(stTile.position, f.position)) {
                flags.hasIndustryAdj = true;
                break;
            }
        }
    }

    std::unordered_map<int, int> lineIndexById;
    for (int li = 0; li < (int)g_lines.size(); li++) lineIndexById[g_lines[li].id] = li;

    // A bureau can touch multiple line stations in its inner ring; assign ownership to the closest
    // established-line station so color, preview, and silo contribution all follow one deterministic line.
    std::vector<int> bureauOwnedLineId(g_placedBureaus.size(), -1);
    std::vector<int> bureauOwnedStationId(g_placedBureaus.size(), -1);
    for (int bi = 0; bi < (int)g_placedBureaus.size(); bi++) {
        const auto& b = g_placedBureaus[bi];
        float bestDistSq = 1e30f;
        int bestLineId = -1;
        int bestStationId = -1;
        for (const auto& stTile : stationTiles) {
            if (establishedLineIds.find(stTile.lineId) == establishedLineIds.end()) continue;
            float dx = std::max(0.0f, fabsf(b.position.x - stTile.position.x) - bureauHalfFoot);
            float dz = std::max(0.0f, fabsf(b.position.z - stTile.position.z) - bureauHalfFoot);
            float distSq = dx * dx + dz * dz;
            if (distSq > innerRingRadius * innerRingRadius) continue;
            bool better = (distSq < bestDistSq - 0.0001f);
            bool tie = fabsf(distSq - bestDistSq) <= 0.0001f;
            if (better || (tie && (bestLineId < 0 || stTile.lineId < bestLineId ||
                                    (stTile.lineId == bestLineId && stTile.stationId < bestStationId)))) {
                bestDistSq = distSq;
                bestLineId = stTile.lineId;
                bestStationId = stTile.stationId;
            }
        }
        bureauOwnedLineId[bi] = bestLineId;
        bureauOwnedStationId[bi] = bestStationId;
        if (bestLineId >= 0) {
            bureauYellowEligible[bi] = 1; // Any bureau linked to an established line is SYS7-eligible.
            g_yellowEligibleBureauCount++;
        }
    }

    std::unordered_map<long long, BureauChoice> bestBureauByLineStation;
    for (int bi = 0; bi < (int)g_placedBureaus.size(); bi++) {
        const auto& b = g_placedBureaus[bi];
        int ownedLineId = bureauOwnedLineId[bi];
        int ownedStationId = bureauOwnedStationId[bi];
        if (ownedLineId < 0 || ownedStationId < 0) continue;
        long long k = PackIntPair(ownedLineId, ownedStationId);
        auto it = bestBureauByLineStation.find(k);
        if (it == bestBureauByLineStation.end() ||
            b.floors > it->second.floors ||
            (b.floors == it->second.floors && bi < it->second.bureauIndex)) {
            bestBureauByLineStation[k] = { bi, b.floors };
        }
    }

    g_cachedBureauLineId.assign(g_placedBureaus.size(), -1);
    for (int bi = 0; bi < (int)g_placedBureaus.size(); bi++) {
        int ownedLineId = bureauOwnedLineId[bi];
        auto it = lineIndexById.find(ownedLineId);
        if (it != lineIndexById.end()) g_cachedBureauLineId[bi] = it->second;
    }

    auto hasBureauAtLineStation = [&](int lineId, int stationId) -> bool {
        return bestBureauByLineStation.find(PackIntPair(lineId, stationId)) != bestBureauByLineStation.end();
    };
    auto getBureauChoice = [&](int lineId, int stationId) -> BureauChoice {
        auto it = bestBureauByLineStation.find(PackIntPair(lineId, stationId));
        if (it == bestBureauByLineStation.end()) return BureauChoice{};
        return it->second;
    };

    std::set<std::tuple<int, int, int, int, int>> seenSiloKeys;
    auto addSilo = [&](SiloSystem system, int lineId, int stationAId, int stationBId, int bureauStationId, int bureauHeight) {
        std::tuple<int, int, int, int, int> key = {
            (int)system, lineId, stationAId, stationBId, bureauStationId
        };
        if (seenSiloKeys.find(key) != seenSiloKeys.end()) return;
        seenSiloKeys.insert(key);
        Silo s;
        s.system = system;
        s.lineId = lineId;
        s.stationAId = stationAId;
        s.stationBId = stationBId;
        s.bureauStationId = bureauStationId;
        s.bureauHeight = bureauHeight;
        g_silos.push_back(s);
    };

    auto lineStationIds = [&](int lineId) -> std::vector<int> {
        std::vector<int> out;
        auto it = lineStationIndices.find(lineId);
        if (it == lineStationIndices.end()) return out;
        for (int sidx : it->second) out.push_back(stations[sidx].stationId);
        std::sort(out.begin(), out.end());
        out.erase(std::unique(out.begin(), out.end()), out.end());
        return out;
    };

    // SYS1: cargo train + active factory/depot cargo cluster + at least one station in that cluster on same established line.
    for (int lineId : establishedLineIds) {
        int t = (cargoTrainsPerLine.find(lineId) != cargoTrainsPerLine.end()) ? cargoTrainsPerLine[lineId] : 0;
        int magTrainsOnLineForSys1 = (magentaTrainsPerLine.find(lineId) != magentaTrainsPerLine.end()) ? magentaTrainsPerLine[lineId] : 0;
        int activeFactories = 0;
        for (const auto& fo : factories) {
            // Magenta line bonus: established magenta lines double factory output for cargo silos
            if (fo.lineOwnerId == lineId && fo.depotOwnerId > 0)
                activeFactories += (magTrainsOnLineForSys1 > 0) ? 2 : 1;
        }
        std::vector<int> cargoClusterStations;
        std::vector<int> lineStationIdsVec = lineStationIds(lineId);
        int greenTrainsOnLine = (greenTrainsPerLine.find(lineId) != greenTrainsPerLine.end())
                                    ? greenTrainsPerLine[lineId] : 0;
        for (int sid : lineStationIdsVec) {
            bool inCargoCluster = false;
            for (const auto& stTile : stationTiles) {
                if (stTile.lineId != lineId || stTile.stationId != sid) continue;
                if (IsWorldPosInActivatedCargoCluster(stTile.position.x, stTile.position.z)) {
                    inCargoCluster = true;
                    break;
                }
            }
            if (inCargoCluster) cargoClusterStations.push_back(sid);
        }
        int qualifyingStations = (int)cargoClusterStations.size();
        int silosForLine = std::min(t, std::min(activeFactories, qualifyingStations));
        sys1ByLine[lineId] = { t, activeFactories, qualifyingStations, qualifyingStations, silosForLine };
        if (silosForLine <= 0) continue;
        for (int i = 0; i < silosForLine; i++) {
            int a = cargoClusterStations[i % (int)cargoClusterStations.size()];
            int b = a;
            addSilo(SiloSystem::SYS1_CARGO, lineId, a, b, -1, 0);
        }
    }

    std::set<int> yellowBureauIndicesUsed;

    // SYS2..SYS7
    for (int lineId : establishedLineIds) {
        std::vector<int> greenStations;
        std::vector<int> magentaStations;
        std::vector<int> cyanStations;
        std::vector<int> orangeStations;
        std::vector<int> redStations;
        std::vector<int> yellowStations;
        std::vector<int> innerCityHubStations;
        std::vector<int> industryStations;
        int greenTrainsOnLine = (greenTrainsPerLine.find(lineId) != greenTrainsPerLine.end())
                                    ? greenTrainsPerLine[lineId] : 0;
        int magentaTrainsOnLine = (magentaTrainsPerLine.find(lineId) != magentaTrainsPerLine.end())
                                      ? magentaTrainsPerLine[lineId] : 0;
        int cyanTrainsOnLine = (cyanTrainsPerLine.find(lineId) != cyanTrainsPerLine.end())
                                   ? cyanTrainsPerLine[lineId] : 0;
        int orangeTrainsOnLine = (orangeTrainsPerLine.find(lineId) != orangeTrainsPerLine.end())
                                     ? orangeTrainsPerLine[lineId] : 0;
        int redTrainsOnLine = (redTrainsPerLine.find(lineId) != redTrainsPerLine.end())
                                  ? redTrainsPerLine[lineId] : 0;
        std::vector<int> lineStationIdsVec = lineStationIds(lineId);
        for (int sid : lineStationIdsVec) {
            long long k = PackIntPair(lineId, sid);
            auto fit = stationFlags.find(k);
            if (fit == stationFlags.end()) continue;
            const StationFlags& f = fit->second;
            if (f.nearGreen) greenStations.push_back(sid);
            if (f.inMagenta) magentaStations.push_back(sid);
            if (f.inCyan) cyanStations.push_back(sid);
            if (f.inOrange) orangeStations.push_back(sid);
            if (f.inRed) redStations.push_back(sid);
            if (f.nearYellow) yellowStations.push_back(sid);
            if (f.nearInnerCityHub) innerCityHubStations.push_back(sid);
            if (f.hasIndustryAdj) industryStations.push_back(sid);
        }
        std::sort(greenStations.begin(), greenStations.end());
        greenStations.erase(std::unique(greenStations.begin(), greenStations.end()), greenStations.end());
        std::sort(magentaStations.begin(), magentaStations.end());
        magentaStations.erase(std::unique(magentaStations.begin(), magentaStations.end()), magentaStations.end());
        std::sort(cyanStations.begin(), cyanStations.end());
        cyanStations.erase(std::unique(cyanStations.begin(), cyanStations.end()), cyanStations.end());
        std::sort(orangeStations.begin(), orangeStations.end());
        orangeStations.erase(std::unique(orangeStations.begin(), orangeStations.end()), orangeStations.end());
        std::sort(redStations.begin(), redStations.end());
        redStations.erase(std::unique(redStations.begin(), redStations.end()), redStations.end());
        std::sort(yellowStations.begin(), yellowStations.end());
        yellowStations.erase(std::unique(yellowStations.begin(), yellowStations.end()), yellowStations.end());
        g_yellowStationsOnEstablishedLinesCount += (int)yellowStations.size();
        std::sort(innerCityHubStations.begin(), innerCityHubStations.end());
        innerCityHubStations.erase(std::unique(innerCityHubStations.begin(), innerCityHubStations.end()), innerCityHubStations.end());

        // Distinct bureau stations on this line with deterministic "best bureau per station".
        std::vector<int> bureauStations;
        for (const auto& st : stations) {
            if (st.lineId != lineId) continue;
            if (hasBureauAtLineStation(lineId, st.stationId)) bureauStations.push_back(st.stationId);
        }
        std::sort(bureauStations.begin(), bureauStations.end());
        bureauStations.erase(std::unique(bureauStations.begin(), bureauStations.end()), bureauStations.end());

        // Bureau silo potential: which systems could benefit from a bureau on this line
        {
            int potential = 0;
            if (greenTrainsOnLine > 0 && !greenStations.empty() && !innerCityHubStations.empty())
                potential |= (1 << (int)SiloSystem::SYS2_GREEN);
            if (cyanTrainsOnLine > 0 && !cyanStations.empty()) potential |= (1 << (int)SiloSystem::SYS4_CYAN);
            if (orangeTrainsOnLine > 0 && !orangeStations.empty()) potential |= (1 << (int)SiloSystem::SYS5_ORANGE);
            if (redTrainsOnLine > 0 && !redStations.empty()) potential |= (1 << (int)SiloSystem::SYS6_RED);
            if (!yellowStations.empty())  potential |= (1 << (int)SiloSystem::SYS7_YELLOW);
            g_lineBureauSiloPotential[lineId] = potential;
        }

        // SYS2: strict 1:1 fairness rule.
        // One qualifying bureau at a hub station = one Green silo/listing, capped by Green stations.
        std::vector<int> greenHubBureauStations;
        for (int rsid : innerCityHubStations) {
            if (!hasBureauAtLineStation(lineId, rsid)) continue;
            greenHubBureauStations.push_back(rsid);
        }
        std::sort(greenHubBureauStations.begin(), greenHubBureauStations.end());
        greenHubBureauStations.erase(std::unique(greenHubBureauStations.begin(), greenHubBureauStations.end()), greenHubBureauStations.end());
        int sys2SilosForLine = (greenTrainsOnLine > 0)
            ? std::min((int)greenStations.size(), (int)greenHubBureauStations.size())
            : 0;
        for (int i = 0; i < sys2SilosForLine; i++) {
            int gsid = greenStations[i];
            int rsid = greenHubBureauStations[i];
            BureauChoice bc = getBureauChoice(lineId, rsid);
            addSilo(SiloSystem::SYS2_GREEN, lineId, gsid, rsid, rsid, bc.floors);
        }

        // SYS3: magenta train + magenta station + industry station (within 2 grid spaces of a factory)
        std::sort(industryStations.begin(), industryStations.end());
        industryStations.erase(std::unique(industryStations.begin(), industryStations.end()), industryStations.end());
        if (magentaTrainsOnLine > 0) {
            for (int msid : magentaStations) {
                for (int isid : industryStations) {
                    addSilo(SiloSystem::SYS3_MAGENTA, lineId, msid, isid, -1, 0);
                }
            }
            // Magenta bureau floor bonus: bureaus linked to active magenta lines boost magenta+commodity share performance
            if (!magentaStations.empty() && !industryStations.empty()) {
                for (int bsid : bureauStations) {
                    BureauChoice bc = getBureauChoice(lineId, bsid);
                    g_magentaGrowthFloorBonus += std::max(0, bc.floors);
                }
            }
        }

        // SYS4: cyan train + cyan station + bureau station on same line
        if (cyanTrainsOnLine > 0) {
            for (int csid : cyanStations) {
                for (int bsid : bureauStations) {
                    BureauChoice bc = getBureauChoice(lineId, bsid);
                    addSilo(SiloSystem::SYS4_CYAN, lineId, csid, bsid, bsid, bc.floors);
                }
            }
        }

        // SYS5: orange train + orange station + bureau station on same line
        if (orangeTrainsOnLine > 0) {
            for (int osid : orangeStations) {
                for (int bsid : bureauStations) {
                    BureauChoice bc = getBureauChoice(lineId, bsid);
                    addSilo(SiloSystem::SYS5_ORANGE, lineId, osid, bsid, bsid, bc.floors);
                }
            }
        }

        // SYS6: red train + red station + bureau station on same line
        if (redTrainsOnLine > 0) {
            for (int rsid : redStations) {
                for (int bsid : bureauStations) {
                    BureauChoice bc = getBureauChoice(lineId, bsid);
                    addSilo(SiloSystem::SYS6_RED, lineId, rsid, bsid, bsid, bc.floors);
                }
            }
        }

        // SYS7 (line-level): one established line qualifies if
        // - it has at least one Yellow train on the line, and
        // - it has at least one yellow-near station, and
        // - it has at least one station with an eligible bureau linked to that line
        //   (eligible = bureau passed blanket build rings and was linked via inner-ring station detection).
        int yellowTrainsOnLine = (yellowTrainsPerLine.find(lineId) != yellowTrainsPerLine.end())
                                     ? yellowTrainsPerLine[lineId] : 0;
        g_yellowTrainsOnEstablishedLinesCount += yellowTrainsOnLine;
        int totalBureausOnLine = (int)bureauStations.size();
        int eligibleBureausOnLine = 0;
        bool sys7Created = false;

        // SYS7 diagnostic: track the most-advanced failing condition per line
        if (yellowTrainsOnLine <= 0) {
            setSys7Diagnostic("L%d: NO YELLOW TRAIN (need 1)", lineId);
        } else if (yellowStations.empty()) {
            setSys7Diagnostic("L%d: NO STATION NEAR YELLOW CLUSTER", lineId);
        } else {
            // Has yellow train + yellow station. Check bureau.
            std::vector<int> eligibleBureauStations;
            for (int bsid : bureauStations) {
                BureauChoice bc = getBureauChoice(lineId, bsid);
                if (bc.bureauIndex < 0 || bc.bureauIndex >= (int)bureauYellowEligible.size()) continue;
                if (!bureauYellowEligible[bc.bureauIndex]) continue;
                eligibleBureauStations.push_back(bsid);
            }
            eligibleBureausOnLine = (int)eligibleBureauStations.size();

            if (totalBureausOnLine == 0) {
                setSys7Diagnostic("L%d: NO BUREAU LINKED TO LINE (need inner ring touching an established-line station)", lineId);
            } else if (eligibleBureauStations.empty()) {
                setSys7Diagnostic("L%d: BUREAU NOT ELIGIBLE (%d linked but none eligible)", lineId, totalBureausOnLine);
            } else {
                std::sort(eligibleBureauStations.begin(), eligibleBureauStations.end());
                eligibleBureauStations.erase(std::unique(eligibleBureauStations.begin(), eligibleBureauStations.end()), eligibleBureauStations.end());

                int ysid = yellowStations[0];
                int bsid = eligibleBureauStations[0];
                BureauChoice bc = getBureauChoice(lineId, bsid);
                addSilo(SiloSystem::SYS7_YELLOW, lineId, ysid, bsid, bsid, bc.floors);
                if (bc.bureauIndex >= 0) yellowBureauIndicesUsed.insert(bc.bureauIndex);
                sys7Created = true;
                setSys7Diagnostic("L%d: SYS7 SILO CREATED!", lineId);
                sys7DiagnosticLocked = true;
            }
        }

        const Sys1Diag& d1 = sys1ByLine[lineId];
        int sys2Potential = (sys2SilosForLine > 0) ? 1 : 0;
        int sys3Potential = (magentaTrainsOnLine > 0 && !magentaStations.empty() && !industryStations.empty()) ? 1 : 0;
        int sys4Potential = (cyanTrainsOnLine > 0 && !cyanStations.empty() && !bureauStations.empty()) ? 1 : 0;
        int sys5Potential = (orangeTrainsOnLine > 0 && !orangeStations.empty() && !bureauStations.empty()) ? 1 : 0;
        int sys6Potential = (redTrainsOnLine > 0 && !redStations.empty() && !bureauStations.empty()) ? 1 : 0;
        char dbgBuf[512];
        snprintf(dbgBuf, sizeof(dbgBuf),
            "SILO_DEBUG: L%d SYS1[t=%d af=%d cs=%d qs=%d=>%d] SYS2[gT=%d g=%d hubB=%d=>%d] SYS3[mT=%d m=%d ind=%d=>%d] SYS4[cT=%d c=%d b=%d=>%d] SYS5[oT=%d o=%d b=%d=>%d] SYS6[rT=%d r=%d b=%d=>%d] SYS7[yT=%d yS=%d b=%d eB=%d=>%d]",
            lineId,
            d1.cargoTrains, d1.activeFactories, d1.cargoClusterStations, d1.qualifyingStations, d1.silos,
            greenTrainsOnLine, (int)greenStations.size(), (int)greenHubBureauStations.size(), sys2Potential,
            magentaTrainsOnLine, (int)magentaStations.size(), (int)industryStations.size(), sys3Potential,
            cyanTrainsOnLine, (int)cyanStations.size(), (int)bureauStations.size(), sys4Potential,
            orangeTrainsOnLine, (int)orangeStations.size(), (int)bureauStations.size(), sys5Potential,
            redTrainsOnLine, (int)redStations.size(), (int)bureauStations.size(), sys6Potential,
            yellowTrainsOnLine, (int)yellowStations.size(), totalBureausOnLine, eligibleBureausOnLine, sys7Created ? 1 : 0);
        siloDebugLines.push_back(dbgBuf);
    }

    std::sort(g_silos.begin(), g_silos.end(), [](const Silo& a, const Silo& b) {
        if ((int)a.system != (int)b.system) return (int)a.system < (int)b.system;
        if (a.lineId != b.lineId) return a.lineId < b.lineId;
        if (a.stationAId != b.stationAId) return a.stationAId < b.stationAId;
        if (a.stationBId != b.stationBId) return a.stationBId < b.stationBId;
        return a.bureauStationId < b.bureauStationId;
    });
    for (int i = 0; i < (int)g_silos.size(); i++) g_silos[i].id = i + 1;

    for (const auto& s : g_silos) g_siloCountBySystem[(int)s.system]++;

    g_commoditiesUnlocked = std::min(6, g_siloCountBySystem[(int)SiloSystem::SYS1_CARGO]);
    g_greenStocksUnlocked = std::min(6, g_siloCountBySystem[(int)SiloSystem::SYS2_GREEN]);
    g_magentaStocksUnlocked = std::min(6, g_siloCountBySystem[(int)SiloSystem::SYS3_MAGENTA]);
    g_cyanStocksUnlocked = std::min(6, g_siloCountBySystem[(int)SiloSystem::SYS4_CYAN]);
    g_orangeStocksUnlocked = std::min(6, g_siloCountBySystem[(int)SiloSystem::SYS5_ORANGE]);
    g_redStocksUnlocked = std::min(6, g_siloCountBySystem[(int)SiloSystem::SYS6_RED]);
    g_marketUnlocked = (g_siloCountBySystem[(int)SiloSystem::SYS7_YELLOW] >= 1);

    // Colour-sector growth bias: bureau floors used by silos increase bullish odds
    // for that same sector's stock trend rolls.
    for (const auto& s : g_silos) {
        int floors = std::max(0, s.bureauHeight);
        if (s.system == SiloSystem::SYS2_GREEN) g_greenGrowthFloorBonus += floors;
        else if (s.system == SiloSystem::SYS4_CYAN) g_cyanGrowthFloorBonus += floors;
        else if (s.system == SiloSystem::SYS5_ORANGE) g_orangeGrowthFloorBonus += floors;
        else if (s.system == SiloSystem::SYS6_RED) g_redGrowthFloorBonus += floors;
    }

    // Market chaos is reduced by unique SYS7 bureau floors (unique bureau strategy chosen for fairness).
    int totalYellowBureauFloors = 0;
    for (int bi : yellowBureauIndicesUsed) {
        if (bi >= 0 && bi < (int)g_placedBureaus.size()) totalYellowBureauFloors += g_placedBureaus[bi].floors;
    }
    g_marketChaos = std::max(0, 50 - totalYellowBureauFloors);

    // Throttled silo diagnostics for all systems: log on state change and periodic heartbeat.
    static unsigned long long s_lastSiloDebugSig = 0ULL;
    static int s_siloDebugFrameCounter = 0;
    s_siloDebugFrameCounter++;

    unsigned long long sig = 1469598103934665603ULL; // FNV-1a 64-bit offset basis
    auto hashInt = [&](int v) {
        sig ^= (unsigned long long)(unsigned int)v;
        sig *= 1099511628211ULL;
    };
    hashInt(g_establishedLineCount);
    for (int i = 0; i < 7; i++) hashInt(g_siloCountBySystem[i]);
    for (const auto& line : siloDebugLines) {
        for (unsigned char ch : line) {
            sig ^= (unsigned long long)ch;
            sig *= 1099511628211ULL;
        }
    }
    bool debugChanged = (sig != s_lastSiloDebugSig);
    bool debugHeartbeat = (s_siloDebugFrameCounter % 240) == 0;
    if (debugChanged || debugHeartbeat) {
        s_lastSiloDebugSig = sig;
        DebugLogFormat("SILO_DEBUG: totals estLines=%d cargo=%d green=%d magenta=%d cyan=%d orange=%d red=%d yellow=%d chaos=%d marketUnlocked=%d",
            g_establishedLineCount,
            g_siloCountBySystem[(int)SiloSystem::SYS1_CARGO],
            g_siloCountBySystem[(int)SiloSystem::SYS2_GREEN],
            g_siloCountBySystem[(int)SiloSystem::SYS3_MAGENTA],
            g_siloCountBySystem[(int)SiloSystem::SYS4_CYAN],
            g_siloCountBySystem[(int)SiloSystem::SYS5_ORANGE],
            g_siloCountBySystem[(int)SiloSystem::SYS6_RED],
            g_siloCountBySystem[(int)SiloSystem::SYS7_YELLOW],
            g_marketChaos, g_marketUnlocked ? 1 : 0);
        for (const auto& line : siloDebugLines) {
            DebugLogFormat("%s", line.c_str());
        }
    }
}

static void InitializeMarketPrices() {
    auto initGroup = [](MarketListingState* states, int count, float basePrice, float baseVol) {
        std::uniform_real_distribution<float> pDist(basePrice * 0.7f, basePrice * 1.3f);
        std::uniform_real_distribution<float> vDist(baseVol * 0.6f, baseVol * 1.4f);
        for (int i = 0; i < count; i++) {
            states[i].price = pDist(g_marketRng);
            states[i].previousPrice = states[i].price;
            states[i].volatility = vDist(g_marketRng);
            states[i].trend = 0;
            states[i].trendDaysLeft = 0;
            states[i].sharesOwned = 0;
            states[i].avgBuyPrice = 0.0f;
        }
    };
    initGroup(g_commodityStates, 6, 50.0f, 0.08f);
    initGroup(g_greenStockStates, 6, 120.0f, 0.05f);
    initGroup(g_magentaStockStates, 6, 200.0f, 0.04f);
    initGroup(g_cyanStockStates, 6, 300.0f, 0.04f);
    initGroup(g_orangeStockStates, 6, 250.0f, 0.05f);
    initGroup(g_redStockStates, 6, 400.0f, 0.03f);
    g_dayCount = 0;
    g_marketRevenueLast = 0;
    g_activeMarketEvents.clear();
    g_hasDynamicTicker = false;
    g_year5WarningShown = false;
    g_year5ModalOpen    = false;
    g_year5ModalFrames  = 0;
    g_gameOver          = false;
    g_finalScore        = 0;
    g_gameOverTimer     = 0.0f;
    g_gameOverPhase     = 0;
    g_bankruptcyGraceActive = false;
    g_bankruptcyDeadlineYear = -1;
    g_introModalOpen    = false;
    g_introModalFrames  = 0;
    g_helpModalOpen     = false;
    g_helpPage          = 0;
}

static MarketListingState* GetStatesForTab(MarketTab tab) {
    switch (tab) {
        case MarketTab::Commodities: return g_commodityStates;
        case MarketTab::Green: return g_greenStockStates;
        case MarketTab::Magenta: return g_magentaStockStates;
        case MarketTab::Cyan: return g_cyanStockStates;
        case MarketTab::Orange: return g_orangeStockStates;
        case MarketTab::Red: return g_redStockStates;
        default: return g_commodityStates;
    }
}

static const MarketListing* GetListingsForTab(MarketTab tab) {
    switch (tab) {
        case MarketTab::Commodities: return kCommodityListings;
        case MarketTab::Green: return kGreenCorpListings;
        case MarketTab::Magenta: return kMagentaCorpListings;
        case MarketTab::Cyan: return kCyanCorpListings;
        case MarketTab::Orange: return kOrangeCorpListings;
        case MarketTab::Red: return kRedCorpListings;
        default: return kCommodityListings;
    }
}

static int GetUnlockedCountForTab(MarketTab tab) {
    switch (tab) {
        case MarketTab::Commodities: return g_commoditiesUnlocked;
        case MarketTab::Green: return g_greenStocksUnlocked;
        case MarketTab::Magenta: return g_magentaStocksUnlocked;
        case MarketTab::Cyan: return g_cyanStocksUnlocked;
        case MarketTab::Orange: return g_orangeStocksUnlocked;
        case MarketTab::Red: return g_redStocksUnlocked;
        default: return 0;
    }
}

static const char* GetTabName(MarketTab tab) {
    switch (tab) {
        case MarketTab::Commodities: return "COMMODITIES";
        case MarketTab::Green: return "GREEN";
        case MarketTab::Magenta: return "MAGENTA";
        case MarketTab::Cyan: return "CYAN";
        case MarketTab::Orange: return "ORANGE";
        case MarketTab::Red: return "RED";
        default: return "???";
    }
}

static Color GetTabColor(MarketTab tab) {
    switch (tab) {
        case MarketTab::Commodities: return (Color){255, 255, 0, 255};
        case MarketTab::Green: return (Color){0, 255, 0, 255};
        case MarketTab::Magenta: return (Color){255, 0, 255, 255};
        case MarketTab::Cyan: return (Color){0, 255, 255, 255};
        case MarketTab::Orange: return (Color){255, 165, 0, 255};
        case MarketTab::Red: return (Color){255, 60, 60, 255};
        default: return WHITE;
    }
}

static const char* GetSiloHintForTab(MarketTab tab) {
    switch (tab) {
        case MarketTab::Commodities: return "Build Cargo Silos (cargo train + depot + factory). Magenta lines double factory output. Magenta bureau floors boost commodity share performance by 10% per floor.";
        case MarketTab::Green: return "Build Green Silos (green train + linked HUB bureau; 1 bureau = 1 listing). Each green bureau floor boosts green share performance by 10% and improves bullish trend odds.";
        case MarketTab::Magenta: return "Build Magenta Silos (magenta train + magenta station + industry station). Magenta lines double factory output for cargo silos. Bureau floors on magenta lines boost magenta and commodity share performance by 10% per floor.";
        case MarketTab::Cyan: return "Build Cyan Silos (cyan train + cyan station + linked bureau). More bureau floors = higher cyan growth odds.";
        case MarketTab::Orange: return "Build Orange Silos (orange train + orange station + linked bureau). More bureau floors = higher orange growth odds.";
        case MarketTab::Red: return "Build Red Silos (red train + red station + linked bureau). More bureau floors = higher red growth odds.";
        default: return "";
    }
}

static float GetEventModifierForTab(int tabIdx) {
    float mod = 0.0f;
    for (const auto& e : g_activeMarketEvents) {
        if (e.tabIndex == tabIdx) mod += e.modifier;
    }
    return mod;
}

static void UpdateMarketPrices() {
    if (!g_marketUnlocked) return;

    float chaosScale = 1.0f + (g_marketChaos / 50.0f);
    auto growthFloorBonusForTab = [&](int tabIdx) -> int {
        switch (tabIdx) {
            case 0: return g_magentaGrowthFloorBonus;  // Commodities: boosted by magenta bureau floors
            case 1: return g_greenGrowthFloorBonus;
            case 2: return g_magentaGrowthFloorBonus;  // Magenta: boosted by magenta bureau floors
            case 3: return g_cyanGrowthFloorBonus;
            case 4: return g_orangeGrowthFloorBonus;
            case 5: return g_redGrowthFloorBonus;
            default: return 0;
        }
    };

    auto updateGroup = [&](MarketListingState* states, int unlocked, int tabIdx) {
        std::uniform_real_distribution<float> rDist(-1.0f, 1.0f);
        std::uniform_int_distribution<int> trendDist(0, 9);
        std::uniform_real_distribution<float> trendRoll(0.0f, 1.0f);
        float eventMod = GetEventModifierForTab(tabIdx);

        for (int i = 0; i < 6; i++) {
            MarketListingState& s = states[i];
            s.previousPrice = s.price;
            if (i >= unlocked) continue;

            if (s.trendDaysLeft <= 0) {
                int growthFloors = growthFloorBonusForTab(tabIdx);
                if (growthFloors > 0) {
                    // Sector-specific growth bias (Green/Cyan/Orange/Red): more silo-linked bureau floors
                    // increase bullish trend odds for that same sector.
                    float bullChance = std::min(0.90f, 0.30f + 0.003f * (float)growthFloors);
                    float bearChance = std::max(0.05f, 0.30f - 0.0015f * (float)growthFloors);
                    if (bearChance + bullChance > 0.95f) bearChance = 0.95f - bullChance;
                    float roll = trendRoll(g_marketRng);
                    if (roll < bearChance) s.trend = -1;
                    else if (roll < (1.0f - bullChance)) s.trend = 0;
                    else s.trend = 1;
                } else {
                    int roll = trendDist(g_marketRng);
                    if (roll < 3) s.trend = -1;
                    else if (roll < 7) s.trend = 0;
                    else s.trend = 1;
                }
                s.trendDaysLeft = 2 + (trendDist(g_marketRng) % 5);
            }
            s.trendDaysLeft--;

            float drift = s.trend * s.volatility * 0.3f;
            // 10% share performance boost per bureau floor for green/magenta/commodities (bullish only)
            if (s.trend > 0) {
                int driftFloors = (tabIdx == 0 || tabIdx == 2) ? g_magentaGrowthFloorBonus
                                : (tabIdx == 1)                ? g_greenGrowthFloorBonus
                                :                                0;
                if (driftFloors > 0)
                    drift *= std::min(3.0f, 1.0f + 0.10f * (float)driftFloors);
            }
            float noise = rDist(g_marketRng) * s.volatility * chaosScale;
            float change = drift + noise + eventMod * s.volatility;
            s.price *= (1.0f + change);
            if (s.price < 1.0f) s.price = 1.0f;
            if (s.price > 99999.0f) s.price = 99999.0f;
        }
    };

    updateGroup(g_commodityStates, g_commoditiesUnlocked, 0);
    updateGroup(g_greenStockStates, g_greenStocksUnlocked, 1);
    updateGroup(g_magentaStockStates, g_magentaStocksUnlocked, 2);
    updateGroup(g_cyanStockStates, g_cyanStocksUnlocked, 3);
    updateGroup(g_orangeStockStates, g_orangeStocksUnlocked, 4);
    updateGroup(g_redStockStates, g_redStocksUnlocked, 5);
}

static void UpdateMarketEvents() {
    for (int i = (int)g_activeMarketEvents.size() - 1; i >= 0; i--) {
        g_activeMarketEvents[i].daysLeft--;
        if (g_activeMarketEvents[i].daysLeft <= 0) {
            g_activeMarketEvents.erase(g_activeMarketEvents.begin() + i);
        }
    }

    std::uniform_int_distribution<int> eventRoll(0, 99);
    int roll = eventRoll(g_marketRng);
    int eventThreshold = 12 + g_marketChaos / 3;

    if (roll < eventThreshold && g_activeMarketEvents.size() < 3) {
        MarketEvent ev;
        std::uniform_int_distribution<int> tabDist(0, 5);
        ev.tabIndex = tabDist(g_marketRng);

        std::uniform_int_distribution<int> typeDist(0, 3);
        int t = typeDist(g_marketRng);
        const char* tabNames[] = {"COMMODITIES", "GREEN CORP", "MAGENTA CORP", "CYAN CORP", "ORANGE CORP", "RED CORP"};

        if (t == 0) {
            ev.type = MarketEventType::SectorBoom;
            ev.modifier = 0.15f + (g_marketChaos * 0.003f);
            ev.daysLeft = 2 + (eventRoll(g_marketRng) % 4);
            snprintf(ev.description, sizeof(ev.description), "SECTOR BOOM: %s surging +%.0f%% for %d days!",
                     tabNames[ev.tabIndex], ev.modifier * 100.0f, ev.daysLeft);
        } else if (t == 1) {
            ev.type = MarketEventType::SectorCrash;
            ev.modifier = -(0.12f + (g_marketChaos * 0.004f));
            ev.daysLeft = 2 + (eventRoll(g_marketRng) % 3);
            snprintf(ev.description, sizeof(ev.description), "SECTOR CRASH: %s plunging %.0f%% for %d days!",
                     tabNames[ev.tabIndex], ev.modifier * 100.0f, ev.daysLeft);
        } else if (t == 2) {
            ev.type = MarketEventType::CargoShortage;
            ev.tabIndex = 0;
            ev.modifier = 0.10f;
            ev.daysLeft = 3;
            snprintf(ev.description, sizeof(ev.description), "CARGO SHORTAGE: Commodity prices spiking for 3 days!");
        } else {
            ev.type = MarketEventType::BureauDividend;
            ev.modifier = 0.0f;
            ev.daysLeft = 1;
            int bonusPct = 20 + (eventRoll(g_marketRng) % 30);
            snprintf(ev.description, sizeof(ev.description), "BUREAU DIVIDEND: %s paying +%d%% bonus dividends!",
                     tabNames[ev.tabIndex], bonusPct);
            ev.modifier = bonusPct / 100.0f;
        }

        g_activeMarketEvents.push_back(ev);

        snprintf(g_dynamicTickerBuf, sizeof(g_dynamicTickerBuf), "%s", ev.description);
        g_hasDynamicTicker = true;

        AddTerminalMessage(ev.description);
    }
}

static int CalculateMarketRevenue() {
    if (!g_marketUnlocked) return 0;

    float stabilityFactor = 1.0f - (g_marketChaos / 100.0f);
    if (stabilityFactor < 0.1f) stabilityFactor = 0.1f;
    int revenue = 0;

    for (int i = 0; i < g_commoditiesUnlocked; i++) {
        revenue += (int)(g_commodityStates[i].price * 0.5f * stabilityFactor);
    }

    auto addStockRevenue = [&](MarketListingState* states, int unlocked) {
        for (int i = 0; i < unlocked; i++) {
            revenue += (int)(states[i].price * 0.3f * stabilityFactor);
            if (states[i].sharesOwned > 0) {
                float dividendYield = 0.02f * stabilityFactor;
                for (const auto& e : g_activeMarketEvents) {
                    if (e.type == MarketEventType::BureauDividend) dividendYield += e.modifier * 0.02f;
                }
                revenue += (int)(states[i].price * states[i].sharesOwned * dividendYield);
            }
        }
    };

    addStockRevenue(g_greenStockStates, g_greenStocksUnlocked);
    addStockRevenue(g_magentaStockStates, g_magentaStocksUnlocked);
    addStockRevenue(g_cyanStockStates, g_cyanStocksUnlocked);
    addStockRevenue(g_orangeStockStates, g_orangeStocksUnlocked);
    addStockRevenue(g_redStockStates, g_redStocksUnlocked);

    return revenue;
}

static int CalculateNetWorth() {
    int worth = g_playerCredits;
    MarketListingState* groups[] = {
        g_commodityStates, g_greenStockStates, g_magentaStockStates,
        g_cyanStockStates, g_orangeStockStates, g_redStockStates
    };
    for (int g = 0; g < 6; g++) {
        for (int i = 0; i < 6; i++) {
            if (groups[g][i].sharesOwned > 0)
                worth += (int)(groups[g][i].sharesOwned * groups[g][i].price);
        }
    }
    return worth;
}

static void MarketBuyShare(MarketTab tab, int listingIdx) {
    MarketListingState* states = GetStatesForTab(tab);
    int unlocked = GetUnlockedCountForTab(tab);
    if (listingIdx < 0 || listingIdx >= unlocked) return;

    int cost = (int)ceilf(states[listingIdx].price);
    if (cost <= 0 || g_playerCredits < cost) return;

    g_playerCredits -= cost;
    float oldTotal = states[listingIdx].avgBuyPrice * states[listingIdx].sharesOwned;
    states[listingIdx].sharesOwned++;
    states[listingIdx].avgBuyPrice = (oldTotal + states[listingIdx].price) / states[listingIdx].sharesOwned;

    char buf[128];
    const MarketListing* listings = GetListingsForTab(tab);
    snprintf(buf, sizeof(buf), "BOUGHT 1x [%s] @ %d CREDITS", listings[listingIdx].symbol, cost);
    AddTerminalMessage(buf);
}

static void MarketSellShare(MarketTab tab, int listingIdx) {
    MarketListingState* states = GetStatesForTab(tab);
    int unlocked = GetUnlockedCountForTab(tab);
    if (listingIdx < 0 || listingIdx >= unlocked) return;
    if (states[listingIdx].sharesOwned <= 0) return;

    int salePrice = (int)floorf(states[listingIdx].price);
    if (salePrice < 1) salePrice = 1;
    g_playerCredits += salePrice;
    states[listingIdx].sharesOwned--;
    if (states[listingIdx].sharesOwned <= 0) states[listingIdx].avgBuyPrice = 0.0f;

    char buf[128];
    const MarketListing* listings = GetListingsForTab(tab);
    snprintf(buf, sizeof(buf), "SOLD 1x [%s] @ %d CREDITS", listings[listingIdx].symbol, salePrice);
    AddTerminalMessage(buf);
}

static void RebuildTickerText() {
    if (!g_marketUnlocked) {
        g_tickerChunks.clear();
        snprintf(g_tickerTextBuf, sizeof(g_tickerTextBuf), "%s", g_baseTickerText);
        return;
    }

    g_tickerChunks.clear();
    auto appendStockChunks = [&](const char* sym, const MarketListingState& st, Color symColor) {
        float chg = (st.previousPrice > 0.01f) ? ((st.price - st.previousPrice) / st.previousPrice) * 100.0f : 0.0f;
        const char* arrow = (chg > 0.01f) ? "^" : ((chg < -0.01f) ? "v" : "-");
        Color arrowColor = (chg > 0.01f) ? (Color){0, 255, 90, 255}
                          : (chg < -0.01f) ? (Color){255, 70, 70, 255}
                                           : (Color){180, 180, 180, 255};
        char priceBuf[64];
        snprintf(priceBuf, sizeof(priceBuf), "$%.0f ", st.price);

        g_tickerChunks.push_back({" | [", WHITE});
        g_tickerChunks.push_back({sym, symColor});
        g_tickerChunks.push_back({"] ", WHITE});
        g_tickerChunks.push_back({priceBuf, WHITE});
        g_tickerChunks.push_back({arrow, arrowColor});
        g_tickerChunks.push_back({" ", WHITE});
    };

    for (int i = 0; i < g_commoditiesUnlocked; i++) appendStockChunks(kCommodityListings[i].symbol, g_commodityStates[i], (Color){255, 255, 0, 255});
    for (int i = 0; i < g_greenStocksUnlocked; i++) appendStockChunks(kGreenCorpListings[i].symbol, g_greenStockStates[i], GetTabColor(MarketTab::Green));
    for (int i = 0; i < g_magentaStocksUnlocked; i++) appendStockChunks(kMagentaCorpListings[i].symbol, g_magentaStockStates[i], GetTabColor(MarketTab::Magenta));
    for (int i = 0; i < g_cyanStocksUnlocked; i++) appendStockChunks(kCyanCorpListings[i].symbol, g_cyanStockStates[i], GetTabColor(MarketTab::Cyan));
    for (int i = 0; i < g_orangeStocksUnlocked; i++) appendStockChunks(kOrangeCorpListings[i].symbol, g_orangeStockStates[i], GetTabColor(MarketTab::Orange));
    for (int i = 0; i < g_redStocksUnlocked; i++) appendStockChunks(kRedCorpListings[i].symbol, g_redStockStates[i], GetTabColor(MarketTab::Red));

    if (g_tickerChunks.empty()) {
        g_tickerChunks.push_back({"MARKET ONLINE - BUILD SILOS TO UNLOCK STOCK LISTINGS", WHITE});
    } else {
        g_tickerChunks.insert(g_tickerChunks.begin(), {"STOCKS", WHITE});
    }
    g_tickerChunks.insert(g_tickerChunks.begin(), {" | KEY EL=EST LINE | MAT=CARGO MATERIALS | CR=CREDITS | NS=NEARBY STATION | LB=LINKED BUREAU | HUB=INNER CITY HUB | OOB=OUT OF BOUNDS | OVR=OVERLAP | IR/OR=BUREAU RINGS ", WHITE});
    // Always prepend the "H FOR HELP | " hint; color is updated each frame in DrawTicker
    g_tickerChunks.insert(g_tickerChunks.begin(), {"H FOR HELP | ", WHITE});
    g_tickerTextBuf[0] = '\0';
}

// Apply confirmed station modal data (name + delay) to all 4 tiles of the station, then close.
static void CancelStationModal(StationModalData& modal) {
    if (modal.isNewBuild) {
        // Remove the 4 station tiles that were just placed and refund credits
        int anchorIdx = modal.anchorPlatformIndex;
        if (anchorIdx >= 0 && anchorIdx < (int)g_placedPlatforms.size()) {
            std::vector<int> toRemove = CollectPhysicalStationTileIndices(anchorIdx, g_placedPlatforms, g_gridSpacing);
            // Sort descending so erasing by index is safe
            std::sort(toRemove.begin(), toRemove.end(), std::greater<int>());
            for (int idx : toRemove)
                g_placedPlatforms.erase(g_placedPlatforms.begin() + idx);
            g_playerCredits += 1000;
            AddTerminalMessage("STATION CANCELLED - 1000 CREDITS REFUNDED");
        }
    }
    // Exit station placement mode after a new build so the cursor returns to neutral.
    if (modal.isNewBuild) ClearAllPlacementModes();
    modal.open = false;
    modal.cancelClicked = false;
    InvalidatePlatformCaches();
}

static void CommitStationModal(StationModalData& modal) {
    int anchorIdx = modal.anchorPlatformIndex;
    if (anchorIdx >= 0 && anchorIdx < (int)g_placedPlatforms.size() && g_placedPlatforms[anchorIdx].isStation) {
        std::vector<int> stationTiles = CollectPhysicalStationTileIndices(anchorIdx, g_placedPlatforms, g_gridSpacing);
        for (int pi : stationTiles) {
            if (pi < 0 || pi >= (int)g_placedPlatforms.size()) continue;
            PlacedPlatform& p = g_placedPlatforms[pi];
            if (p.isStation) {
                memcpy(p.stationName, modal.nameBuffer, 64);
                p.stationDelayMode = modal.delayMode;
            }
        }
        // Also log the dwell info
        const char* delayNames[3] = {"FLOW (no pause)", "SHORT DWELL (2s)", "LONG DWELL (10s)"};
        char buf[192];
        const char* nameStr = modal.nameBuffer[0] ? modal.nameBuffer : "(unnamed)";
        snprintf(buf, sizeof(buf), "STATION \"%s\" CONFIGURED â€” DWELL: %s", nameStr, delayNames[modal.delayMode]);
        AddTerminalMessage(buf);
    }
    // Exit station placement mode after a new build so the cursor returns to neutral
    // and subsequent neutral-clicks on the station will open the modal correctly.
    if (modal.isNewBuild) ClearAllPlacementModes();
    modal.open = false;
    modal.confirmClicked = false;
    modal.cancelClicked  = false;
    // Re-trigger establish-line detection. The station modal blocks the detection
    // while open. If the build that opened it also completed a 2-station component,
    // the detection was skipped this frame and will never run again unless we
    // invalidate the cache here so the next frame picks it up.
    InvalidatePlatformCaches();
}

// â"€â"€ Station Configuration Modal â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€
// Opened when a station is first built, or when the player neutral-clicks a station tile.
// Lets the player name the station and set the platform dwell time for that stop.
// When the station is on an established line it also shows live telemetry.
static void DrawStationModal(StationModalData& modal, int screenWidth, int screenHeight) {
    g_stationModalOpen = modal.open;
    if (!modal.open) return;
    modal.framesOpen++;

    // â"€â"€ Geometry â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€
    DrawRectangle(0, 0, screenWidth, screenHeight, (Color){0, 0, 0, 200});

    float modalWidth  = 989.0f;
    float modalHeight = 695.0f;
    float modalX = (screenWidth  - modalWidth)  / 2.0f;
    float modalY = (screenHeight - modalHeight) / 2.0f;

    float titleBarH    = 49.0f;
    float contentTop   = 90.0f;
    float contentBottom= 570.0f;
    float contentInset = 40.0f;
    float innerX = modalX + contentInset;
    float innerY = modalY + contentTop;
    float innerW = modalWidth - 2.0f * contentInset;
    float innerH = contentBottom - contentTop;
    float btnBarTop = 617.85f;
    float btnH  = 50.0f;
    float btnGap = 20.0f;
    float btnW  = (modalWidth - 2.0f * contentInset - btnGap) / 2.0f;

    Rectangle contentBox = { innerX, innerY, innerW, innerH };
    Rectangle confirmBtn = { modalX + contentInset, modalY + btnBarTop, btnW, btnH };
    Rectangle cancelBtn  = { modalX + contentInset + btnW + btnGap, modalY + btnBarTop, btnW, btnH };
    float closeBtnSize = 42.0f;
    Rectangle closeBtn = { modalX + modalWidth - closeBtnSize - 8.0f, modalY + 4.0f, closeBtnSize, closeBtnSize };

    // â"€â"€ Background â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€
    bool usingTex = false;
    if (g_texLargeModalTemplate.id != 0) {
        Rectangle src = { 0, 0, (float)g_texLargeModalTemplate.width, (float)g_texLargeModalTemplate.height };
        DrawTexturePro(g_texLargeModalTemplate, src, (Rectangle){modalX, modalY, modalWidth, modalHeight}, {0,0}, 0.0f, WHITE);
        usingTex = true;
    } else {
        DrawRectangle((int)modalX, (int)modalY, (int)modalWidth, (int)modalHeight, (Color){28, 28, 36, 255});
        DrawRectangleLinesEx((Rectangle){modalX, modalY, modalWidth, modalHeight}, 2, SKYBLUE);
        DrawRectangleLinesEx(contentBox, 1, SKYBLUE);
    }

    // â"€â"€ Close button â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€
    bool closeHover = CheckCollisionPointRec(CustomGetMousePosition(), closeBtn);
    if (!usingTex) {
        DrawRectangleRec(closeBtn, closeHover ? (Color){180,50,50,255} : (Color){140,40,40,255});
        float xPad = closeBtnSize * 0.25f;
        DrawLineEx({closeBtn.x+xPad, closeBtn.y+xPad}, {closeBtn.x+closeBtnSize-xPad, closeBtn.y+closeBtnSize-xPad}, 2, WHITE);
        DrawLineEx({closeBtn.x+closeBtnSize-xPad, closeBtn.y+xPad}, {closeBtn.x+xPad, closeBtn.y+closeBtnSize-xPad}, 2, WHITE);
    }

    float titleFontSize = GetScaledFontSize(BASE_FONT_SIZE) * 2.0f;
    float bodyFontSize  = GetScaledFontSize(BASE_FONT_SIZE) * 1.6f;
    float smallFontSize = GetScaledFontSize(BASE_FONT_SIZE) * 1.35f;
    Color titleColor = (Color){0, 255, 128, 255};
    Color bodyColor  = WHITE;
    Color dimColor   = (Color){160, 200, 220, 255};

    // â"€â"€ Title â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€
    const char* title = "CONFIGURE STATION";
    float titleW = MeasureTextEx(gameFont, title, titleFontSize, 0.0f).x;
    float titleY = modalY + (titleBarH - titleFontSize) / 2.0f - 4.0f + modalHeight * 0.02f;
    DrawTextEx(gameFont, title, {modalX + (modalWidth - titleW) / 2.0f, titleY}, titleFontSize, 0.0f, titleColor);

    // â"€â"€ Content â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€
    BeginScissorMode((int)innerX+1, (int)innerY+1, (int)innerW-2, (int)innerH-2);
    float yPos = innerY + 18.0f;

    // -- Station name input --
    DrawTextEx(gameFont, "STATION NAME:", {innerX+15.0f, yPos}, bodyFontSize, 0.0f, bodyColor);
    yPos += 36.0f;
    Rectangle textBox = {innerX+15.0f, yPos, innerW-30.0f, 50.0f};
    DrawRectangleRec(textBox, (Color){20,20,30,255});
    DrawRectangleLinesEx(textBox, 1, SKYBLUE);
    DrawTextEx(gameFont, modal.nameBuffer, {innerX+22.0f, yPos+12.0f}, bodyFontSize, 0.0f, WHITE);
    float nameTextW = MeasureTextEx(gameFont, modal.nameBuffer, bodyFontSize, 0.0f).x;
    if (sinf((float)GetTime() * 4.0f) > 0.0f)
        DrawTextEx(gameFont, "_", {innerX+22.0f+nameTextW, yPos+12.0f}, bodyFontSize, 0.0f, WHITE);

    // Text input
    int key = CustomGetCharPressed();
    while (key > 0) {
        if (key >= 32 && key <= 126 && modal.nameCursorPos < 63) {
            modal.nameBuffer[modal.nameCursorPos++] = (char)key;
            modal.nameBuffer[modal.nameCursorPos] = '\0';
        }
        key = CustomGetCharPressed();
    }
    if (CustomIsKeyPressed(KEY_BACKSPACE) && modal.nameCursorPos > 0)
        modal.nameBuffer[--modal.nameCursorPos] = '\0';

    yPos += 62.0f;

    // -- Platform dwell --
    DrawTextEx(gameFont, "PLATFORM DWELL:", {innerX+15.0f, yPos}, bodyFontSize, 0.0f, bodyColor);
    yPos += 30.0f;
    // Description
    const char* dwellDesc =
        "Set the time trains pause at this stop. Precise dwell control is essential for "
        "timetable management â€” uneven spacing leads to bunching and collisions.";
    // Word-wrap the description
    {
        char lineBuf[256] = {0}; int lineLen = 0;
        float wrapW = innerW - 30.0f;
        char descCopy[512]; strncpy(descCopy, dwellDesc, sizeof(descCopy)-1);
        char* tok = strtok(descCopy, " ");
        while (tok) {
            char testBuf[256]; snprintf(testBuf, sizeof(testBuf), "%s%s%s", lineBuf, lineLen?"":" ", tok);
            float testW = MeasureTextEx(gameFont, lineLen?testBuf:tok, smallFontSize, 0.0f).x;
            if (lineLen > 0 && testW > wrapW) {
                DrawTextEx(gameFont, lineBuf, {innerX+15.0f, yPos}, smallFontSize, 0.0f, dimColor);
                yPos += smallFontSize + 3.0f;
                strncpy(lineBuf, tok, sizeof(lineBuf)-1); lineLen = (int)strlen(tok);
            } else {
                if (lineLen) { strcat(lineBuf, " "); strcat(lineBuf, tok); lineLen += 1+(int)strlen(tok); }
                else { strncpy(lineBuf, tok, sizeof(lineBuf)-1); lineLen = (int)strlen(tok); }
            }
            tok = strtok(nullptr, " ");
        }
        if (lineLen) { DrawTextEx(gameFont, lineBuf, {innerX+15.0f, yPos}, smallFontSize, 0.0f, dimColor); yPos += smallFontSize + 3.0f; }
    }
    yPos += 10.0f;

    // 3 dwell buttons
    float dwellBtnW = (innerW - 30.0f - 16.0f) / 3.0f;
    float dwellBtnH = 46.0f;
    const char* dwellLabels[3] = { "FLOW", "SHORT DWELL", "LONG DWELL" };
    const char* dwellSubs[3]   = { "No pause", "2 second pause", "10 second pause" };
    Color dwellActiveCol   = (Color){0, 160, 80, 255};
    Color dwellHoverCol    = (Color){0, 100, 50, 255};
    Color dwellInactiveCol = (Color){30, 40, 50, 255};
    for (int di = 0; di < 3; di++) {
        float bx = innerX + 15.0f + di * (dwellBtnW + 8.0f);
        Rectangle btn = {bx, yPos, dwellBtnW, dwellBtnH};
        bool hover = CheckCollisionPointRec(CustomGetMousePosition(), btn);
        bool active = (modal.delayMode == di);
        Color fill = active ? dwellActiveCol : (hover ? dwellHoverCol : dwellInactiveCol);
        DrawRectangleRec(btn, fill);
        DrawRectangleLinesEx(btn, active ? 2.0f : 1.0f, active ? (Color){0,255,128,255} : SKYBLUE);
        float lw = MeasureTextEx(gameFont, dwellLabels[di], smallFontSize, 0.0f).x;
        DrawTextEx(gameFont, dwellLabels[di], {bx+(dwellBtnW-lw)/2.0f, yPos+6.0f}, smallFontSize, 0.0f, WHITE);
        float sw = MeasureTextEx(gameFont, dwellSubs[di], smallFontSize*0.75f, 0.0f).x;
        DrawTextEx(gameFont, dwellSubs[di], {bx+(dwellBtnW-sw)/2.0f, yPos+dwellBtnH-smallFontSize*0.85f}, smallFontSize*0.75f, 0.0f, dimColor);
        if (modal.framesOpen >= 2 && RawIsMouseButtonPressed(MOUSE_BUTTON_LEFT) && hover)
            modal.delayMode = di;
    }
    yPos += dwellBtnH + 18.0f;

    // â"€â"€ Telemetry divider â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€
    DrawLineEx({innerX+15.0f, yPos}, {innerX+innerW-15.0f, yPos}, 1.0f, (Color){60,80,100,200});
    yPos += 10.0f;

    // Gather telemetry for this station
    int anchorIdx = modal.anchorPlatformIndex;
    bool hasStation = (anchorIdx >= 0 && anchorIdx < (int)g_placedPlatforms.size() && g_placedPlatforms[anchorIdx].isStation);

    if (hasStation) {
        std::vector<int> siblingIndices = CollectPhysicalStationTileIndices(anchorIdx, g_placedPlatforms, g_gridSpacing);

        // Find lines that contain any sibling tile
        std::vector<int> connectedLineIndices;
        for (int li = 0; li < (int)g_lines.size(); li++) {
            for (int si : siblingIndices) {
                if (g_lines[li].platformIndices.count(si)) { connectedLineIndices.push_back(li); break; }
            }
        }

        if (connectedLineIndices.empty()) {
            DrawTextEx(gameFont, "NOT YET LINKED TO A LINE", {innerX+15.0f, yPos}, smallFontSize, 0.0f, (Color){120,140,160,255});
            yPos += smallFontSize + 6.0f;
        } else {
            DrawTextEx(gameFont, "NETWORK TELEMETRY:", {innerX+15.0f, yPos}, bodyFontSize, 0.0f, titleColor);
            yPos += bodyFontSize + 8.0f;

            for (int li : connectedLineIndices) {
                if (yPos + smallFontSize > innerY + innerH - 4.0f) break;
                const Line& line = g_lines[li];
                bool established = (g_establishedLineIds.count(line.id) > 0);
                char lineBuf[192];
                snprintf(lineBuf, sizeof(lineBuf), "  LINE: %s  [%s]", line.name.c_str(), established ? "ESTABLISHED" : "UNESTABLISHED");
                DrawTextEx(gameFont, lineBuf, {innerX+15.0f, yPos}, smallFontSize, 0.0f, established ? (Color){0,255,128,220} : (Color){180,180,100,200});
                yPos += smallFontSize + 4.0f;

                if (!established) continue;

                // Active trains on this line
                const char* sysNames[7] = {"CARGO","GREEN","MAGENTA","CYAN","ORANGE","RED","YELLOW"};
                int trainsByType[7] = {0};
                for (const auto& tr : g_placedTrains) {
                    if (tr.lineId == line.id && (int)tr.type < 7) trainsByType[(int)tr.type]++;
                }
                char trainBuf[192] = "  TRAINS: ";
                bool anyTrain = false;
                for (int t = 0; t < 7; t++) {
                    if (trainsByType[t] > 0) {
                        char tb[32]; snprintf(tb,sizeof(tb),"%sÃ—%d  ", sysNames[t], trainsByType[t]);
                        strncat(trainBuf, tb, sizeof(trainBuf)-strlen(trainBuf)-1);
                        anyTrain = true;
                    }
                }
                if (!anyTrain) strncat(trainBuf, "none", sizeof(trainBuf)-strlen(trainBuf)-1);
                if (yPos + smallFontSize < innerY + innerH - 4.0f) {
                    DrawTextEx(gameFont, trainBuf, {innerX+15.0f, yPos}, smallFontSize, 0.0f, dimColor);
                    yPos += smallFontSize + 4.0f;
                }

                // Active silos on this line
                if (g_siloCountBySystem[0] > 0 || g_siloCountBySystem[1] > 0 || g_siloCountBySystem[2] > 0
                    || g_siloCountBySystem[3] > 0 || g_siloCountBySystem[4] > 0 || g_siloCountBySystem[5] > 0
                    || g_siloCountBySystem[6] > 0) {
                    char siloBuf[192] = "  ACTIVE SILOS: ";
                    bool anySilo = false;
                    const char* siloTickers[7] = {"MATERIALS","GREEN-CORP","MAGENTA-IND","CYAN-TECH","ORANGE-SEC","RED-BIO","YELLOW-EXEC"};
                    for (int s = 0; s < 7; s++) {
                        if (g_siloCountBySystem[s] > 0) {
                            char sb[40]; snprintf(sb,sizeof(sb),"%s ", siloTickers[s]);
                            strncat(siloBuf, sb, sizeof(siloBuf)-strlen(siloBuf)-1);
                            anySilo = true;
                        }
                    }
                    if (!anySilo) strncat(siloBuf, "none", sizeof(siloBuf)-strlen(siloBuf)-1);
                    if (yPos + smallFontSize < innerY + innerH - 4.0f) {
                        DrawTextEx(gameFont, siloBuf, {innerX+15.0f, yPos}, smallFontSize, 0.0f, dimColor);
                        yPos += smallFontSize + 4.0f;
                    }
                }

                // Nearby bureaus
                int nearBureau = 0;
                for (const auto& b : g_placedBureaus) {
                    for (int si : siblingIndices) {
                        if (Vector3Distance(b.position, g_placedPlatforms[si].position) < g_gridSpacing * 4.0f)
                            { nearBureau += b.floors; break; }
                    }
                }
                // Nearby depots & factories
                int nearDepot = 0, nearFactory = 0;
                for (const auto& p : g_placedPlatforms) {
                    if (!p.isDepot) continue;
                    for (int si : siblingIndices)
                        if (Vector3Distance(p.position, g_placedPlatforms[si].position) < g_gridSpacing * 4.0f)
                            { nearDepot++; break; }
                }
                for (const auto& f : g_placedFactories) {
                    for (int si : siblingIndices)
                        if (Vector3Distance(f.position, g_placedPlatforms[si].position) < g_gridSpacing * 6.0f)
                            { nearFactory++; break; }
                }
                if (nearBureau > 0 || nearDepot > 0 || nearFactory > 0) {
                    char infra[192]; infra[0] = '\0';
                    if (nearBureau  > 0) { char b[40]; snprintf(b,sizeof(b),"BUREAU (%d FLOORS)  ",nearBureau);  strncat(infra,b,sizeof(infra)-strlen(infra)-1); }
                    if (nearDepot   > 0) { char b[40]; snprintf(b,sizeof(b),"DEPOTS Ã—%d  ",nearDepot);           strncat(infra,b,sizeof(infra)-strlen(infra)-1); }
                    if (nearFactory > 0) { char b[40]; snprintf(b,sizeof(b),"FACTORIES Ã—%d",nearFactory);        strncat(infra,b,sizeof(infra)-strlen(infra)-1); }
                    char fullBuf[256]; snprintf(fullBuf,sizeof(fullBuf),"  NEARBY: %s",infra);
                    if (yPos + smallFontSize < innerY + innerH - 4.0f) {
                        DrawTextEx(gameFont, fullBuf, {innerX+15.0f, yPos}, smallFontSize, 0.0f, dimColor);
                        yPos += smallFontSize + 4.0f;
                    }
                }

                // Stock/commodities feeding this line
                if (g_commoditiesUnlocked > 0 || g_greenStocksUnlocked > 0 || g_magentaStocksUnlocked > 0
                    || g_cyanStocksUnlocked > 0 || g_orangeStocksUnlocked > 0 || g_redStocksUnlocked > 0) {
                    char mkBuf[192] = "  MARKET FEEDS: ";
                    if (g_commoditiesUnlocked > 0) strncat(mkBuf, "COMMODITIES  ", sizeof(mkBuf)-strlen(mkBuf)-1);
                    if (g_greenStocksUnlocked   > 0) strncat(mkBuf, "GREEN  ",    sizeof(mkBuf)-strlen(mkBuf)-1);
                    if (g_magentaStocksUnlocked > 0) strncat(mkBuf, "MAGENTA  ",  sizeof(mkBuf)-strlen(mkBuf)-1);
                    if (g_cyanStocksUnlocked    > 0) strncat(mkBuf, "CYAN  ",     sizeof(mkBuf)-strlen(mkBuf)-1);
                    if (g_orangeStocksUnlocked  > 0) strncat(mkBuf, "ORANGE  ",   sizeof(mkBuf)-strlen(mkBuf)-1);
                    if (g_redStocksUnlocked     > 0) strncat(mkBuf, "RED",        sizeof(mkBuf)-strlen(mkBuf)-1);
                    if (yPos + smallFontSize < innerY + innerH - 4.0f) {
                        DrawTextEx(gameFont, mkBuf, {innerX+15.0f, yPos}, smallFontSize, 0.0f, dimColor);
                        yPos += smallFontSize + 4.0f;
                    }
                }
            }
        }
    }

    EndScissorMode();

    // â"€â"€ Confirm / Cancel buttons â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€
    bool confirmHover = CheckCollisionPointRec(CustomGetMousePosition(), confirmBtn);
    bool cancelHover  = CheckCollisionPointRec(CustomGetMousePosition(), cancelBtn);

    auto drawModalBtn = [&](Rectangle r, bool hover, const char* label) {
        Texture2D tex = (hover && g_texModalConfirmSelected.id != 0) ? g_texModalConfirmSelected : g_texModalConfirmNotSelected;
        if (tex.id != 0) {
            DrawTexturePro(tex, {0,0,(float)tex.width,(float)tex.height}, r, {0,0}, 0.0f, WHITE);
        } else {
            DrawRectangleRec(r, hover ? (Color){60,120,80,255} : (Color){45,90,60,255});
        }
        float lw = MeasureTextEx(gameFont, label, bodyFontSize, 0.0f).x;
        DrawTextEx(gameFont, label, {r.x+(r.width-lw)/2.0f, r.y+(r.height-bodyFontSize)/2.0f-3.0f}, bodyFontSize, 0.0f, WHITE);
    };
    drawModalBtn(confirmBtn, confirmHover, "CONFIRM");
    drawModalBtn(cancelBtn,  cancelHover,  "CANCEL");

    if (modal.framesOpen >= 2 && RawIsMouseButtonPressed(MOUSE_BUTTON_LEFT)) {
        if (closeHover || cancelHover) modal.cancelClicked = true;
        else if (confirmHover)         modal.confirmClicked = true;
    }
}

// Draw modal UI for line establishment (uses modal_template.png layout: title bar, inner content box, CONFIRM/CANCEL buttons)
static void DrawLineModal(LineModalData& modal, const std::vector<Line>& lines, int screenWidth, int screenHeight) {
    g_lineModalOpen = (modal.state != LineModalState::None);
    if (modal.state == LineModalState::None) return;

    modal.framesOpen++;

    // Semi-transparent overlay
    DrawRectangle(0, 0, screenWidth, screenHeight, (Color){0, 0, 0, 200});

    bool useLargeEstablishModal = (modal.state == LineModalState::EstablishLine || modal.state == LineModalState::ChooseSilo);
    float modalWidth = useLargeEstablishModal ? 989.0f : 700.0f;
    float modalHeight = useLargeEstablishModal ? 695.0f : 450.0f;
    float modalX = (screenWidth - modalWidth) / 2.0f;
    float modalY = (screenHeight - modalHeight) / 2.0f;

    // Layout: title bar (top), inner content box (middle), button bar (bottom)
    float titleBarH = useLargeEstablishModal ? 49.0f : 50.0f;
    float contentTop = useLargeEstablishModal ? 90.0f : 65.0f;
    float contentBottom = useLargeEstablishModal ? 570.0f : 370.0f;
    float contentInset = 40.0f;
    float innerX = modalX + contentInset;
    float innerY = modalY + contentTop;
    float innerW = modalWidth - 2.0f * contentInset;
    float innerH = contentBottom - contentTop;
    float btnBarTop = useLargeEstablishModal ? 617.85f : 375.0f;
    float btnH = useLargeEstablishModal ? 50.0f : 55.0f;
    float btnGap = 20.0f;
    float btnW = (modalWidth - 2.0f * contentInset - btnGap) / 2.0f;

    Rectangle contentBox = { innerX, innerY, innerW, innerH };
    Rectangle confirmBtn = { modalX + contentInset, modalY + btnBarTop, btnW, btnH };
    Rectangle cancelBtn = { modalX + contentInset + btnW + btnGap, modalY + btnBarTop, btnW, btnH };
    float closeBtnSize = useLargeEstablishModal ? 42.0f : 28.0f;
    Rectangle closeBtn = useLargeEstablishModal
        ? (Rectangle){ modalX + modalWidth - closeBtnSize - 8.0f, modalY + 4.0f, closeBtnSize, closeBtnSize }
        : (Rectangle){ modalX + modalWidth - closeBtnSize - 12.0f, modalY + 10.0f, closeBtnSize, closeBtnSize };

    // Draw modal background: EstablishLine uses large template; AddToLine uses standard template.
    bool usingTemplateTexture = false;
    if (useLargeEstablishModal && g_texLargeModalTemplate.id != 0) {
        Rectangle src = { 0, 0, (float)g_texLargeModalTemplate.width, (float)g_texLargeModalTemplate.height };
        Rectangle dst = { modalX, modalY, modalWidth, modalHeight };
        DrawTexturePro(g_texLargeModalTemplate, src, dst, {0,0}, 0.0f, WHITE);
        usingTemplateTexture = true;
    } else if (!useLargeEstablishModal && g_texModalTemplate.id != 0) {
        Rectangle src = { 0, 0, (float)g_texModalTemplate.width, (float)g_texModalTemplate.height };
        Rectangle dst = { modalX, modalY, modalWidth, modalHeight };
        DrawTexturePro(g_texModalTemplate, src, dst, {0,0}, 0.0f, WHITE);
        usingTemplateTexture = true;
    }
    if (!usingTemplateTexture) {
        DrawRectangle((int)modalX, (int)modalY, (int)modalWidth, (int)modalHeight, (Color){28, 28, 36, 255});
        DrawRectangleLinesEx((Rectangle){modalX, modalY, modalWidth, modalHeight}, 2, SKYBLUE);
        DrawRectangleLinesEx(contentBox, 1, SKYBLUE);
    }

    // Close X button (template may include it; we handle click either way)
    bool closeHover = CheckCollisionPointRec(CustomGetMousePosition(), closeBtn);
    if (!usingTemplateTexture) {
        DrawRectangleRec(closeBtn, closeHover ? (Color){180, 50, 50, 255} : (Color){140, 40, 40, 255});
        float xPad = closeBtnSize * 0.25f;
        DrawLineEx((Vector2){closeBtn.x + xPad, closeBtn.y + xPad}, (Vector2){closeBtn.x + closeBtnSize - xPad, closeBtn.y + closeBtnSize - xPad}, 2, WHITE);
        DrawLineEx((Vector2){closeBtn.x + closeBtnSize - xPad, closeBtn.y + xPad}, (Vector2){closeBtn.x + xPad, closeBtn.y + closeBtnSize - xPad}, 2, WHITE);
    }

    float titleFontSize = GetScaledFontSize(BASE_FONT_SIZE) * 2.0f;
    float bodyFontSize = GetScaledFontSize(BASE_FONT_SIZE) * 1.6f;
    Color titleColor = (Color){0, 255, 128, 255};  // Bright green for title
    Color bodyColor = WHITE;

    if (modal.state == LineModalState::ChooseSilo) {
        // Title
        const char* title = "SILO CONFLICT";
        float titleW = MeasureTextEx(gameFont, title, titleFontSize, 0.0f).x;
        float titleY = modalY + (titleBarH - titleFontSize) / 2.0f - 4.0f + modalHeight * 0.02f;
        DrawTextEx(gameFont, title, (Vector2){modalX + (modalWidth - titleW) / 2.0f, titleY}, titleFontSize, 0.0f, (Color){255, 200, 0, 255});

        BeginScissorMode((int)innerX + 1, (int)innerY + 1, (int)innerW - 2, (int)innerH - 2);
        float yPos = innerY + 20.0f;

        const char* desc = "Your stations span multiple silo regions. Choose which silo system this line will belong to:";
        float descFontSize = bodyFontSize * 0.9f;
        yPos = DrawWrappedText(desc, innerX + 15.0f, yPos, innerW - 30.0f, innerY + innerH - 4.0f, descFontSize, (Color){180, 220, 255, 255});
        yPos += 20.0f;

        // Draw silo choice buttons
        Vector2 mousePosModal = CustomGetMousePosition();
        float btnWidth = innerW - 60.0f;
        float btnHeight = 58.0f;
        float btnSpacing = 10.0f;
        for (int i = 0; i < (int)modal.detectedSystems.size(); i++) {
            int sys = modal.detectedSystems[i];
            SystemColorShades shades = GetSystemColorShades(sys);

            float btnX = innerX + 30.0f;
            float btnY = yPos + i * (btnHeight + btnSpacing);
            Rectangle btnRect = { btnX, btnY, btnWidth, btnHeight };
            bool hover = CheckCollisionPointRec(mousePosModal, btnRect);
            bool selected = (i == modal.siloChoiceIndex);

            // Background
            Color bgColor = selected ? (Color){40, 60, 80, 255} : (Color){25, 25, 35, 255};
            if (hover) bgColor = (Color){50, 70, 90, 255};
            DrawRectangleRec(btnRect, bgColor);

            // Color swatch on left
            float swatchSize = btnHeight - 16.0f;
            Rectangle swatchRect = { btnX + 8.0f, btnY + 8.0f, swatchSize, swatchSize };
            DrawRectangleRec(swatchRect, shades.colors[1]);
            DrawRectangleLinesEx(swatchRect, 1, WHITE);

            // System name
            float textX = btnX + swatchSize + 24.0f;
            float textY = btnY + (btnHeight - bodyFontSize) / 2.0f;
            DrawTextEx(gameFont, shades.systemLabel, (Vector2){textX, textY}, bodyFontSize, 0.0f, shades.colors[1]);

            // Selection border
            Color borderColor = selected ? SKYBLUE : (Color){60, 60, 80, 255};
            if (hover) borderColor = (Color){100, 200, 255, 255};
            DrawRectangleLinesEx(btnRect, selected ? 2.0f : 1.0f, borderColor);

            // Click to select
            if (modal.framesOpen >= 2 && RawIsMouseButtonPressed(MOUSE_BUTTON_LEFT) && hover) {
                modal.siloChoiceIndex = i;
            }
        }

        // Keyboard navigation
        if (IsKeyPressed(KEY_UP) && modal.siloChoiceIndex > 0) modal.siloChoiceIndex--;
        if (IsKeyPressed(KEY_DOWN) && modal.siloChoiceIndex < (int)modal.detectedSystems.size() - 1) modal.siloChoiceIndex++;

        EndScissorMode();

        // Buttons
        bool confirmHover = CheckCollisionPointRec(CustomGetMousePosition(), confirmBtn);
        bool cancelHover = CheckCollisionPointRec(CustomGetMousePosition(), cancelBtn);

        Texture2D confirmTex = (confirmHover && g_texModalConfirmSelected.id != 0) ? g_texModalConfirmSelected : g_texModalConfirmNotSelected;
        Texture2D cancelTex = (cancelHover && g_texModalConfirmSelected.id != 0) ? g_texModalConfirmSelected : g_texModalConfirmNotSelected;

        if (confirmTex.id != 0) {
            DrawTexturePro(confirmTex, {0,0,(float)confirmTex.width,(float)confirmTex.height}, confirmBtn, {0,0}, 0, WHITE);
            DrawTexturePro(cancelTex, {0,0,(float)cancelTex.width,(float)cancelTex.height}, cancelBtn, {0,0}, 0, WHITE);
        } else {
            DrawRectangleRec(confirmBtn, confirmHover ? (Color){0,120,0,255} : (Color){0,80,0,255});
            DrawRectangleRec(cancelBtn, cancelHover ? (Color){120,0,0,255} : (Color){80,0,0,255});
        }
        float confirmFontSize = bodyFontSize * 1.1f;
        const char* confirmLabel = "CHOOSE";
        const char* cancelLabel = "CANCEL";
        float clW = MeasureTextEx(gameFont, confirmLabel, confirmFontSize, 0.0f).x;
        float caW = MeasureTextEx(gameFont, cancelLabel, confirmFontSize, 0.0f).x;
        DrawTextEx(gameFont, confirmLabel, {confirmBtn.x+(confirmBtn.width-clW)/2.0f, confirmBtn.y+(confirmBtn.height-confirmFontSize)/2.0f-3.0f}, confirmFontSize, 0.0f, WHITE);
        DrawTextEx(gameFont, cancelLabel, {cancelBtn.x+(cancelBtn.width-caW)/2.0f, cancelBtn.y+(cancelBtn.height-confirmFontSize)/2.0f-3.0f}, confirmFontSize, 0.0f, WHITE);

        if (modal.framesOpen >= 2 && RawIsMouseButtonPressed(MOUSE_BUTTON_LEFT)) {
            if (closeHover || cancelHover) modal.cancelClicked = true;
            else if (confirmHover) modal.siloChoiceClicked = true;
        }
        if (IsKeyPressed(KEY_ENTER)) modal.siloChoiceClicked = true;
        if (IsKeyPressed(KEY_ESCAPE)) modal.cancelClicked = true;
    } else if (modal.state == LineModalState::EstablishLine) {
        // Title in title bar (centered, moved down 2%)
        const char* title = "ESTABLISH NEW LINE?";
        float titleW = MeasureTextEx(gameFont, title, titleFontSize, 0.0f).x;
        float titleY = modalY + (titleBarH - titleFontSize) / 2.0f - 4.0f + modalHeight * 0.02f;
        DrawTextEx(gameFont, title, (Vector2){modalX + (modalWidth - titleW) / 2.0f, titleY}, titleFontSize, 0.0f, titleColor);

        BeginScissorMode((int)innerX + 1, (int)innerY + 1, (int)innerW - 2, (int)innerH - 2);
        float yPos = innerY + 20.0f;

        // Body content inside inner box
        DrawTextEx(gameFont, "NAME:", (Vector2){innerX + 15.0f, yPos}, bodyFontSize, 0.0f, bodyColor);
        yPos += 38.0f;

        Rectangle textBox = {innerX + 15.0f, yPos, innerW - 30.0f, 52.0f};
        DrawRectangleRec(textBox, (Color){20, 20, 30, 255});
        DrawRectangleLinesEx(textBox, 1, SKYBLUE);
        DrawTextEx(gameFont, modal.nameBuffer, (Vector2){innerX + 22.0f, yPos + 14.0f}, bodyFontSize, 0.0f, WHITE);

        float textWidth = MeasureTextEx(gameFont, modal.nameBuffer, bodyFontSize, 0.0f).x;
        if (sinf((float)GetTime() * 4.0f) > 0.0f) {
            DrawTextEx(gameFont, "_", (Vector2){innerX + 22.0f + textWidth, yPos + 14.0f}, bodyFontSize, 0.0f, WHITE);
        }

        int key = CustomGetCharPressed();
        while (key > 0) {
            if (key >= 32 && key <= 126 && modal.nameCursorPos < 63) {
                modal.nameBuffer[modal.nameCursorPos] = (char)key;
                modal.nameCursorPos++;
                modal.nameBuffer[modal.nameCursorPos] = '\0';
            }
            key = CustomGetCharPressed();
        }
        if (CustomIsKeyPressed(KEY_BACKSPACE) && modal.nameCursorPos > 0) {
            modal.nameCursorPos--;
            modal.nameBuffer[modal.nameCursorPos] = '\0';
        }

        yPos += 65.0f;
        DrawTextEx(gameFont, "COLOR:", (Vector2){innerX + 15.0f, yPos}, bodyFontSize, 0.0f, bodyColor);
        yPos += 36.0f;

        // Build color palette: 4 system shades if a cluster was detected, otherwise full palette
        std::vector<Color> colors;
        std::vector<const char*> colorNames;
        const char* systemLabel = nullptr;
        if (modal.detectedSystem >= 0) {
            SystemColorShades shades = GetSystemColorShades(modal.detectedSystem);
            for (int i = 0; i < 4; i++) { colors.push_back(shades.colors[i]); colorNames.push_back(shades.names[i]); }
            systemLabel = shades.systemLabel;
        } else {
            colors = GetLineColorPalette();
            static const char* defaultNames[] = { "Cyan", "Red", "Green", "Yellow", "Magenta", "Blue", "Orange", "Light Cyan", "Purple", "White" };
            for (int i = 0; i < (int)colors.size(); i++) colorNames.push_back(defaultNames[i]);
        }

        if (systemLabel && systemLabel[0]) {
            char sysLabelBuf[128];
            snprintf(sysLabelBuf, sizeof(sysLabelBuf), "SYSTEM: %s", systemLabel);
            float sysLabelW = MeasureTextEx(gameFont, sysLabelBuf, bodyFontSize * 0.85f, 0.0f).x;
            DrawTextEx(gameFont, sysLabelBuf, (Vector2){innerX + (innerW - sysLabelW) / 2.0f, yPos - 2.0f}, bodyFontSize * 0.85f, 0.0f, colors[1]);
            yPos += bodyFontSize * 1.1f;
        }

        float colorBoxSize = 56.0f * 0.9f;
        float colorSpacing = 6.0f;
        float totalColorRowWidth = (int)colors.size() * colorBoxSize + ((int)colors.size() - 1) * colorSpacing;
        float colorRowStartX = modalX + (modalWidth - totalColorRowWidth) / 2.0f;
        Vector2 mousePosModal = CustomGetMousePosition();
        for (int i = 0; i < (int)colors.size(); i++) {
            float x = colorRowStartX + i * (colorBoxSize + colorSpacing);
            Rectangle colorRect = {x, yPos, colorBoxSize, colorBoxSize};
            DrawRectangleRec(colorRect, colors[i]);
            DrawRectangleLinesEx(colorRect, 2, i == modal.colorIndex ? SKYBLUE : GRAY);
            if (modal.framesOpen >= 2 && RawIsMouseButtonPressed(MOUSE_BUTTON_LEFT) && CheckCollisionPointRec(mousePosModal, colorRect)) {
                modal.colorIndex = i;
            }
        }
        if (IsKeyPressed(KEY_LEFT) && modal.colorIndex > 0) modal.colorIndex--;
        if (IsKeyPressed(KEY_RIGHT) && modal.colorIndex < (int)colors.size() - 1) modal.colorIndex++;
        if (modal.colorIndex >= (int)colors.size()) modal.colorIndex = (int)colors.size() - 1;
        modal.selectedColor = colors[modal.colorIndex];

        yPos += colorBoxSize + 20.0f;
        const char* lineNameDisplay = (modal.nameBuffer[0] != '\0') ? modal.nameBuffer : "(enter name)";
        const char* chosenColorName = (modal.colorIndex >= 0 && modal.colorIndex < (int)colorNames.size()) ? colorNames[modal.colorIndex] : "Custom";
        char feedbackBuf[256];
        snprintf(feedbackBuf, sizeof(feedbackBuf), "\"%s\" will be added to your CyberTrain network and given the colour: %s.", lineNameDisplay, chosenColorName);
        float feedbackFontSize = bodyFontSize * 0.9f;
        float feedbackMaxW = innerW - 30.0f;
        float lineHeight = feedbackFontSize * 1.2f;
        char lineBuf[128];
        int lineLen = 0;
        lineBuf[0] = '\0';
        const char* wordStart = feedbackBuf;
        float feedbackStartY = yPos;
        for (const char* p = feedbackBuf; ; p++) {
            if (!*p) break;
            bool atWordEnd = (*p == ' ');
            if (atWordEnd && wordStart < p) {
                bool hasNonSpace = false;
                for (const char* c = wordStart; c < p; c++) if (*c != ' ') { hasNonSpace = true; break; }
                if (!hasNonSpace) { wordStart = p + 1; continue; }
                char word[64];
                size_t wlen = (size_t)(p - wordStart);
                if (wlen >= sizeof(word)) wlen = sizeof(word) - 1;
                memcpy(word, wordStart, wlen);
                word[wlen] = '\0';
                float addW = MeasureTextEx(gameFont, word, feedbackFontSize, 0.0f).x;
                float curW = (lineLen > 0) ? MeasureTextEx(gameFont, lineBuf, feedbackFontSize, 0.0f).x : 0.0f;
                if (lineLen > 0 && curW + addW + 2.0f > feedbackMaxW) {
                    float lineTextW = MeasureTextEx(gameFont, lineBuf, feedbackFontSize, 0.0f).x;
                    DrawTextEx(gameFont, lineBuf, (Vector2){innerX + (innerW - lineTextW) / 2.0f, feedbackStartY}, feedbackFontSize, 0.0f, (Color){180, 220, 255, 255});
                    feedbackStartY += lineHeight;
                    lineLen = 0;
                    lineBuf[0] = '\0';
                }
                if (lineLen > 0) { lineBuf[lineLen++] = ' '; lineBuf[lineLen] = '\0'; }
                for (size_t i = 0; word[i] && lineLen < (int)sizeof(lineBuf) - 1; i++) lineBuf[lineLen++] = word[i];
                lineBuf[lineLen] = '\0';
                wordStart = p + 1;
            }
        }
        if (*wordStart) {
            char word[64];
            size_t wlen = strlen(wordStart);
            if (wlen >= sizeof(word)) wlen = sizeof(word) - 1;
            memcpy(word, wordStart, wlen);
            word[wlen] = '\0';
            float addW = MeasureTextEx(gameFont, word, feedbackFontSize, 0.0f).x;
            float curW = (lineLen > 0) ? MeasureTextEx(gameFont, lineBuf, feedbackFontSize, 0.0f).x : 0.0f;
            if (lineLen > 0 && curW + addW + 2.0f > feedbackMaxW) {
                float lineTextW = MeasureTextEx(gameFont, lineBuf, feedbackFontSize, 0.0f).x;
                DrawTextEx(gameFont, lineBuf, (Vector2){innerX + (innerW - lineTextW) / 2.0f, feedbackStartY}, feedbackFontSize, 0.0f, (Color){180, 220, 255, 255});
                feedbackStartY += lineHeight;
                lineLen = 0;
                lineBuf[0] = '\0';
            }
            if (lineLen > 0) { lineBuf[lineLen++] = ' '; lineBuf[lineLen] = '\0'; }
            for (size_t i = 0; word[i] && lineLen < (int)sizeof(lineBuf) - 1; i++) lineBuf[lineLen++] = word[i];
            lineBuf[lineLen] = '\0';
        }
        if (lineLen > 0) {
            float lineTextW = MeasureTextEx(gameFont, lineBuf, feedbackFontSize, 0.0f).x;
            DrawTextEx(gameFont, lineBuf, (Vector2){innerX + (innerW - lineTextW) / 2.0f, feedbackStartY}, feedbackFontSize, 0.0f, (Color){180, 220, 255, 255});
            feedbackStartY += lineHeight;
        }

        // Silo build hint: when a system color cluster is detected, show what's needed
        if (modal.detectedSystem >= 0) {
            feedbackStartY += 8.0f;
            const char* siloHint = nullptr;
            switch (modal.detectedSystem) {
                case 0: siloHint = "SILO REQ: Cargo train + depot + factory on this line."; break;
                case 1: siloHint = "SILO REQ: Green train + linked bureau in the Inner City Hub."; break;
                case 2: siloHint = "SILO REQ: Magenta train + magenta station near a factory."; break;
                case 3: siloHint = "SILO REQ: Cyan train + cyan station + linked bureau."; break;
                case 4: siloHint = "SILO REQ: Orange train + orange station + linked bureau."; break;
                case 5: siloHint = "SILO REQ: Red train + red station + linked bureau."; break;
                case 6: siloHint = "SILO REQ: Yellow train + yellow station + linked bureau."; break;
            }
            if (siloHint) {
                float hintFontSize = feedbackFontSize * 0.85f;
                DrawWrappedText(siloHint, innerX + 15.0f, feedbackStartY,
                                innerW - 30.0f, innerY + innerH - 4.0f,
                                hintFontSize, (Color){180, 255, 200, 200});
            }
        }
        EndScissorMode();

        // Buttons: Confirm (ESTABLISH) and Cancel (CONTINUE BUILDING)
        bool confirmHover = CheckCollisionPointRec(CustomGetMousePosition(), confirmBtn);
        bool cancelHover = CheckCollisionPointRec(CustomGetMousePosition(), cancelBtn);

        Texture2D confirmTex = (confirmHover && g_texModalConfirmSelected.id != 0) ? g_texModalConfirmSelected : g_texModalConfirmNotSelected;
        Texture2D cancelTex = (cancelHover && g_texModalConfirmSelected.id != 0) ? g_texModalConfirmSelected : g_texModalConfirmNotSelected;

        if (confirmTex.id != 0) {
            Rectangle src = {0, 0, (float)confirmTex.width, (float)confirmTex.height};
            DrawTexturePro(confirmTex, src, confirmBtn, {0,0}, 0.0f, WHITE);
        } else {
            DrawRectangleRec(confirmBtn, confirmHover ? (Color){60, 120, 80, 255} : (Color){45, 90, 60, 255});
        }
        if (cancelTex.id != 0) {
            Rectangle src = {0, 0, (float)cancelTex.width, (float)cancelTex.height};
            DrawTexturePro(cancelTex, src, cancelBtn, {0,0}, 0.0f, WHITE);
        } else {
            DrawRectangleRec(cancelBtn, cancelHover ? (Color){100, 60, 60, 255} : (Color){80, 50, 50, 255});
        }

        float btnFontSize = bodyFontSize * 1.18f;    // 18% larger
        float btnTextOffsetY = modalHeight * 0.01f;   // Move button text down 1% (up 1.5% from 2.5%)
        float estW = MeasureTextEx(gameFont, "ESTABLISH", btnFontSize, 0.0f).x;
        float contW = MeasureTextEx(gameFont, "CONTINUE BUILDING", btnFontSize, 0.0f).x;
        DrawTextEx(gameFont, "ESTABLISH", (Vector2){confirmBtn.x + (confirmBtn.width - estW) / 2.0f, confirmBtn.y + (btnH - btnFontSize) / 2.0f - 4.0f + btnTextOffsetY}, btnFontSize, 0.0f, WHITE);
        DrawTextEx(gameFont, "CONTINUE BUILDING", (Vector2){cancelBtn.x + (cancelBtn.width - contW) / 2.0f, cancelBtn.y + (btnH - btnFontSize) / 2.0f - 4.0f + btnTextOffsetY}, btnFontSize, 0.0f, WHITE);

        if (modal.framesOpen >= 2 && RawIsMouseButtonPressed(MOUSE_BUTTON_LEFT)) {
            if (closeHover) modal.cancelClicked = true;
            else if (confirmHover) modal.establishClicked = true;
            else if (cancelHover) modal.cancelClicked = true;
        }
    } else if (modal.state == LineModalState::AddToLine) {
        const char* title = "ADD TO EXISTING LINE?";
        float titleW = MeasureTextEx(gameFont, title, titleFontSize, 0.0f).x;
        DrawTextEx(gameFont, title, (Vector2){modalX + (modalWidth - titleW) / 2.0f, modalY + (titleBarH - titleFontSize) / 2.0f - 4.0f + modalHeight * 0.02f}, titleFontSize, 0.0f, titleColor);

        BeginScissorMode((int)innerX + 1, (int)innerY + 1, (int)innerW - 2, (int)innerH - 2);
        float yPos = innerY + 25.0f;

        if (modal.targetLineId >= 0 && modal.targetLineId < (int)g_lines.size()) {
            const Line& targetLine = g_lines[modal.targetLineId];
            char lineInfo[128];
            snprintf(lineInfo, sizeof(lineInfo), "LINE: %s (%d STATIONS)", targetLine.name.c_str(), targetLine.stationCount);
            DrawTextEx(gameFont, lineInfo, (Vector2){innerX + 20.0f, yPos}, bodyFontSize, 0.0f, bodyColor);
            yPos += 40.0f;
        }
        DrawTextEx(gameFont, "ADD THIS STATION TO THE EXISTING LINE,", (Vector2){innerX + 20.0f, yPos}, bodyFontSize, 0.0f, bodyColor);
        yPos += 35.0f;
        DrawTextEx(gameFont, "OR CONTINUE BUILDING WITHOUT ADDING?", (Vector2){innerX + 20.0f, yPos}, bodyFontSize, 0.0f, bodyColor);
        EndScissorMode();

        bool confirmHover = CheckCollisionPointRec(CustomGetMousePosition(), confirmBtn);
        bool cancelHover = CheckCollisionPointRec(CustomGetMousePosition(), cancelBtn);

        Texture2D confirmTex = (confirmHover && g_texModalConfirmSelected.id != 0) ? g_texModalConfirmSelected : g_texModalConfirmNotSelected;
        Texture2D cancelTex = (cancelHover && g_texModalConfirmSelected.id != 0) ? g_texModalConfirmSelected : g_texModalConfirmNotSelected;

        if (confirmTex.id != 0) {
            Rectangle src = {0, 0, (float)confirmTex.width, (float)confirmTex.height};
            DrawTexturePro(confirmTex, src, confirmBtn, {0,0}, 0.0f, WHITE);
        } else {
            DrawRectangleRec(confirmBtn, confirmHover ? (Color){60, 120, 80, 255} : (Color){45, 90, 60, 255});
        }
        if (cancelTex.id != 0) {
            Rectangle src = {0, 0, (float)cancelTex.width, (float)cancelTex.height};
            DrawTexturePro(cancelTex, src, cancelBtn, {0,0}, 0.0f, WHITE);
        } else {
            DrawRectangleRec(cancelBtn, cancelHover ? (Color){100, 60, 60, 255} : (Color){80, 50, 50, 255});
        }

        float yesW = MeasureTextEx(gameFont, "YES, ADD TO LINE", bodyFontSize, 0.0f).x;
        float noW = MeasureTextEx(gameFont, "NO, CONTINUE", bodyFontSize, 0.0f).x;
        DrawTextEx(gameFont, "YES, ADD TO LINE", (Vector2){confirmBtn.x + (confirmBtn.width - yesW) / 2.0f, confirmBtn.y + (btnH - bodyFontSize) / 2.0f - 4.0f}, bodyFontSize, 0.0f, WHITE);
        DrawTextEx(gameFont, "NO, CONTINUE", (Vector2){cancelBtn.x + (cancelBtn.width - noW) / 2.0f, cancelBtn.y + (btnH - bodyFontSize) / 2.0f - 4.0f}, bodyFontSize, 0.0f, WHITE);

        if (modal.framesOpen >= 2 && RawIsMouseButtonPressed(MOUSE_BUTTON_LEFT)) {
            if (closeHover) modal.cancelClicked = true;
            else if (confirmHover) modal.addToLineClicked = true;
            else if (cancelHover) modal.cancelClicked = true;
        }
    }
}

// Junction modal: BUILD JUNCTION (place track through existing, creating junction) or DO NOT BUILD (cancel placement)
static void DrawJunctionModal(JunctionModalData& modal, int screenWidth, int screenHeight) {
    if (!modal.open) return;
    modal.framesOpen++;
    DrawRectangle(0, 0, screenWidth, screenHeight, (Color){0, 0, 0, 200});
    float modalWidth = 700.0f;
    float modalHeight = 450.0f;
    float modalX = (screenWidth - modalWidth) / 2.0f;
    float modalY = (screenHeight - modalHeight) / 2.0f;
    float titleBarH = 50.0f;
    float contentTop = 65.0f;
    float contentBottom = 370.0f;
    float contentInset = 40.0f;
    float innerX = modalX + contentInset;
    float innerY = modalY + contentTop;
    float innerW = modalWidth - 2.0f * contentInset;
    float btnBarTop = 375.0f;
    float btnH = 55.0f;
    float btnGap = 20.0f;
    float btnW = (modalWidth - 2.0f * contentInset - btnGap) / 2.0f;
    Rectangle confirmBtn = { modalX + contentInset, modalY + btnBarTop, btnW, btnH };
    Rectangle cancelBtn = { modalX + contentInset + btnW + btnGap, modalY + btnBarTop, btnW, btnH };
    float closeBtnSize = 28.0f;
    Rectangle closeBtn = { modalX + modalWidth - closeBtnSize - 12.0f, modalY + 10.0f, closeBtnSize, closeBtnSize };
    if (g_texModalTemplate.id != 0) {
        Rectangle src = { 0, 0, (float)g_texModalTemplate.width, (float)g_texModalTemplate.height };
        DrawTexturePro(g_texModalTemplate, src, (Rectangle){modalX, modalY, modalWidth, modalHeight}, {0,0}, 0.0f, WHITE);
    } else {
        DrawRectangle((int)modalX, (int)modalY, (int)modalWidth, (int)modalHeight, (Color){28, 28, 36, 255});
        DrawRectangleLinesEx((Rectangle){modalX, modalY, modalWidth, modalHeight}, 2, SKYBLUE);
    }
    bool closeHover = CheckCollisionPointRec(CustomGetMousePosition(), closeBtn);
    if (g_texModalTemplate.id == 0) {
        DrawRectangleRec(closeBtn, closeHover ? (Color){180, 50, 50, 255} : (Color){140, 40, 40, 255});
        float xPad = closeBtnSize * 0.25f;
        DrawLineEx((Vector2){closeBtn.x + xPad, closeBtn.y + xPad}, (Vector2){closeBtn.x + closeBtnSize - xPad, closeBtn.y + closeBtnSize - xPad}, 2, WHITE);
        DrawLineEx((Vector2){closeBtn.x + closeBtnSize - xPad, closeBtn.y + xPad}, (Vector2){closeBtn.x + xPad, closeBtn.y + closeBtnSize - xPad}, 2, WHITE);
    }
    float titleFontSize = GetScaledFontSize(BASE_FONT_SIZE) * 2.0f;
    float bodyFontSize = GetScaledFontSize(BASE_FONT_SIZE) * 1.35f;
    Color titleColor = (Color){0, 255, 200, 255};
    Color bodyColor = (Color){220, 240, 255, 255};
    const char* titleStr = "BUILD JUNCTION?";
    float titleW = MeasureTextEx(gameFont, titleStr, titleFontSize, 0.0f).x;
    DrawTextEx(gameFont, titleStr, (Vector2){modalX + (modalWidth - titleW) / 2.0f, modalY + (titleBarH - titleFontSize) / 2.0f - 4.0f + modalHeight * 0.02f}, titleFontSize, 0.0f, titleColor);
    float yPos = innerY + 25.0f;
    float juncMaxY = innerY + (contentBottom - contentTop) - bodyFontSize;
    DrawWrappedText("This track would cross existing track.", innerX + 20.0f, yPos, innerW - 40.0f, juncMaxY, bodyFontSize, bodyColor);
    yPos += bodyFontSize * 1.4f;
    DrawWrappedText("BUILD JUNCTION = connect here. DO NOT BUILD = dead end or side-by-side only.", innerX + 20.0f, yPos, innerW - 40.0f, juncMaxY, bodyFontSize, bodyColor);
    bool confirmHover = CheckCollisionPointRec(CustomGetMousePosition(), confirmBtn);
    bool cancelHover = CheckCollisionPointRec(CustomGetMousePosition(), cancelBtn);
    Texture2D confirmTex = (confirmHover && g_texModalConfirmSelected.id != 0) ? g_texModalConfirmSelected : g_texModalConfirmNotSelected;
    Texture2D cancelTex = (cancelHover && g_texModalConfirmSelected.id != 0) ? g_texModalConfirmSelected : g_texModalConfirmNotSelected;
    if (confirmTex.id != 0) {
        DrawTexturePro(confirmTex, (Rectangle){0, 0, (float)confirmTex.width, (float)confirmTex.height}, confirmBtn, {0,0}, 0.0f, WHITE);
    } else {
        DrawRectangleRec(confirmBtn, confirmHover ? (Color){60, 120, 80, 255} : (Color){45, 90, 60, 255});
    }
    if (cancelTex.id != 0) {
        DrawTexturePro(cancelTex, (Rectangle){0, 0, (float)cancelTex.width, (float)cancelTex.height}, cancelBtn, {0,0}, 0.0f, WHITE);
    } else {
        DrawRectangleRec(cancelBtn, cancelHover ? (Color){100, 60, 60, 255} : (Color){80, 50, 50, 255});
    }
    float buildW = MeasureTextEx(gameFont, "BUILD JUNCTION", bodyFontSize, 0.0f).x;
    float noW = MeasureTextEx(gameFont, "DO NOT BUILD", bodyFontSize, 0.0f).x;
    DrawTextEx(gameFont, "BUILD JUNCTION", (Vector2){confirmBtn.x + (confirmBtn.width - buildW) / 2.0f, confirmBtn.y + (btnH - bodyFontSize) / 2.0f - 4.0f}, bodyFontSize, 0.0f, WHITE);
    DrawTextEx(gameFont, "DO NOT BUILD", (Vector2){cancelBtn.x + (cancelBtn.width - noW) / 2.0f, cancelBtn.y + (btnH - bodyFontSize) / 2.0f - 4.0f}, bodyFontSize, 0.0f, WHITE);
    if (modal.framesOpen >= 2 && RawIsMouseButtonPressed(MOUSE_BUTTON_LEFT)) {
        if (closeHover) modal.doNotBuildClicked = true;
        else if (confirmHover) modal.buildJunctionClicked = true;
        else if (cancelHover) modal.doNotBuildClicked = true;
    }
}

// â"€â"€ Demolish Station + Line â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€

// Forward declaration â€” defined later alongside train path logic
static bool RebuildTrainPath(PlacedTrain& train, const std::vector<PlacedPlatform>& platforms, float gridSize);

static const char* GetSiloSystemDisplayName(SiloSystem sys) {
    switch (sys) {
        case SiloSystem::SYS1_CARGO:   return "MATERIALS SILO";
        case SiloSystem::SYS2_GREEN:   return "GREEN EXECUTIVE SILO";
        case SiloSystem::SYS3_MAGENTA: return "MAGENTA INDUSTRY SILO";
        case SiloSystem::SYS4_CYAN:    return "CYAN SILO";
        case SiloSystem::SYS5_ORANGE:  return "ORANGE SILO";
        case SiloSystem::SYS6_RED:     return "RED SILO";
        case SiloSystem::SYS7_YELLOW:  return "YELLOW SILO";
        default:                        return "SILO";
    }
}

// Build a comma-separated warning string of all silo names belonging to any
// established line whose platformIndices overlap with the given platform indices.
static void BuildDemolishSiloWarning(const std::vector<int>& platformIndices, char* out, int outSize) {
    out[0] = '\0';
    std::set<int> affectedLineIds;
    for (int pi : platformIndices) {
        for (const auto& line : g_lines) {
            if (line.platformIndices.count(pi))
                affectedLineIds.insert(line.id);
        }
    }
    std::set<int> siloSystems;
    for (const auto& silo : g_silos) {
        if (affectedLineIds.count(silo.lineId))
            siloSystems.insert((int)silo.system);
    }
    bool first = true;
    for (int sys : siloSystems) {
        const char* name = GetSiloSystemDisplayName((SiloSystem)sys);
        if (!first) strncat(out, ", ", outSize - (int)strlen(out) - 1);
        strncat(out, name, outSize - (int)strlen(out) - 1);
        first = false;
    }
}

// Execute after the confirm modal is approved: remove the platform tile(s), ALL
// established lines that ran through them (both sides revert to neutral), remove
// every affected train, rebuild remaining paths, charge the demolish fee, and
// return to demolish mode with all other placement modes cleared.
static void ExecuteDemolishStationAndLine() {
    // â"€â"€ Collect platform tiles to remove â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€
    std::vector<int> tiles;
    int targetLineIdx = g_demolishConfirmModal.lineIdx;
    if (g_demolishConfirmModal.isStationDemolish) {
        int anchorIdx = g_demolishConfirmModal.anchorIdx;
        std::vector<int> stationTiles = CollectPhysicalStationTileIndices(anchorIdx, g_placedPlatforms, g_gridSpacing);
        for (int pi : stationTiles) {
            // Only include tiles on the target line or not on any line
            bool onOtherLine = false;
            if (targetLineIdx >= 0 && targetLineIdx < (int)g_lines.size()) {
                for (int li = 0; li < (int)g_lines.size(); li++) {
                    if (li == targetLineIdx) continue;
                    if (g_lines[li].platformIndices.count(pi)) { onOtherLine = true; break; }
                }
            }
            if (!onOtherLine) tiles.push_back(pi);
        }
    } else {
        int platIdx = g_demolishConfirmModal.platformIdx;
        if (platIdx >= 0 && platIdx < (int)g_placedPlatforms.size())
            tiles.push_back(platIdx);
    }

    // â"€â"€ Find ALL lines that contain any of these platform tiles â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€
    std::set<int> tilesSet(tiles.begin(), tiles.end());
    std::set<int> affectedLineIndices;
    for (int ti : tiles) {
        for (int li = 0; li < (int)g_lines.size(); li++) {
            if (g_lines[li].platformIndices.count(ti))
                affectedLineIndices.insert(li);
        }
    }
    const int oldSize = (int)g_placedPlatforms.size();
    std::set<int> removedSet(tiles.begin(), tiles.end());
    std::set<long long> removedPositionKeys;
    std::set<long long> releasedOwnershipKeys;
    for (int ti : removedSet) {
        if (ti >= 0 && ti < oldSize) {
            removedPositionKeys.insert(MakePositionKey(g_placedPlatforms[ti].position.x,
                                                       g_placedPlatforms[ti].position.z));
        }
    }
    std::vector<int> oldToConnectivity(oldSize, -1);
    std::vector<PlacedPlatform> connectivityPlatforms;
    connectivityPlatforms.reserve(oldSize - (int)removedSet.size());
    for (int i = 0; i < oldSize; i++) {
        if (removedSet.count(i)) continue;
        oldToConnectivity[i] = (int)connectivityPlatforms.size();
        connectivityPlatforms.push_back(g_placedPlatforms[i]);
    }

    // â"€â"€ Smart demolish: remove tiles, check connectivity, split or keep â"€â"€â"€â"€â"€â"€â"€
    // Instead of deleting entire lines, we remove the demolished tiles and check
    // if each affected line is still connected. If split, the larger half keeps
    // the line; smaller halves get neutralized. Lines dropping below 2 stations
    // are deleted entirely.
    std::set<int> deletedLineIds;        // lines fully removed
    std::set<int> lineIndicesToErase;    // vector indices to erase from g_lines
    std::unordered_map<int, std::set<int>> detachedPlatformsByLineId;
    std::unordered_map<int, std::set<int>> survivingPlatformsByLineId;
    // Capture affected line IDs before any erasure (indices become invalid after erase)
    std::set<int> affectedLineIds;
    for (int li : affectedLineIndices) {
        if (li >= 0 && li < (int)g_lines.size())
            affectedLineIds.insert(g_lines[li].id);
    }

    for (int li : affectedLineIndices) {
        if (li < 0 || li >= (int)g_lines.size()) continue;
        Line& line = g_lines[li];

        // Remove demolished tiles from this line's platformIndices
        for (int ti : tiles)
            line.platformIndices.erase(ti);

        // Gather surviving platform indices for this line
        std::vector<int> survivors(line.platformIndices.begin(), line.platformIndices.end());

        if (survivors.empty()) {
            // Line lost all platforms - delete it
            deletedLineIds.insert(line.id);
            lineIndicesToErase.insert(li);
            continue;
        }

        // BFS connectivity check on surviving platforms
        // Build adjacency within the line's surviving set
        std::vector<std::vector<int>> components;  // each component is a list of platform indices
        std::set<int> visited;

        for (int seed : survivors) {
            if (visited.count(seed)) continue;
            // BFS from this seed
            std::vector<int> comp;
            std::vector<int> queue;
            queue.push_back(seed);
            visited.insert(seed);
            size_t head = 0;
            while (head < queue.size()) {
                int cur = queue[head++];
                comp.push_back(cur);
                for (int other : survivors) {
                    if (visited.count(other)) continue;
                    int curConnectivity = (cur >= 0 && cur < oldSize) ? oldToConnectivity[cur] : -1;
                    int otherConnectivity = (other >= 0 && other < oldSize) ? oldToConnectivity[other] : -1;
                    if (curConnectivity >= 0 && otherConnectivity >= 0 &&
                        ArePlatformsConnectedForNetwork(curConnectivity, otherConnectivity, connectivityPlatforms, g_gridSpacing)) {
                        visited.insert(other);
                        queue.push_back(other);
                    }
                }
            }
            components.push_back(comp);
        }

        if (components.size() <= 1) {
            // Still connected - check if enough stations remain
            Line tempLine = line;
            tempLine.platformIndices.clear();
            for (int pi : survivors) {
                int connectivityPi = (pi >= 0 && pi < oldSize) ? oldToConnectivity[pi] : -1;
                if (connectivityPi >= 0) tempLine.platformIndices.insert(connectivityPi);
            }
            int stationCount = CountPhysicalStationsInLine(tempLine, connectivityPlatforms);
            if (stationCount < 2) {
                // Not enough stations to sustain a line - neutralize survivors and delete
                for (int pi : survivors) {
                    if (pi >= 0 && pi < (int)g_placedPlatforms.size()) {
                        long long key = MakePositionKey(g_placedPlatforms[pi].position.x,
                                                       g_placedPlatforms[pi].position.z);
                        releasedOwnershipKeys.insert(key);
                        g_demolishNeutralizedPlatformKeys.insert(key);
                        g_declinedNeutralBranchPlatformKeys.insert(key);
                    }
                }
                deletedLineIds.insert(line.id);
                lineIndicesToErase.insert(li);
            } else {
                // Line survives intact - just update station count
                line.stationCount = stationCount;
                survivingPlatformsByLineId[line.id] = line.platformIndices;
            }
        } else {
            // Split into multiple components - find the largest
            int largestIdx = 0;
            for (int ci = 1; ci < (int)components.size(); ci++) {
                if ((int)components[ci].size() > (int)components[largestIdx].size())
                    largestIdx = ci;
            }

            // Check if the largest component has enough stations
            std::set<int> largestSet(components[largestIdx].begin(), components[largestIdx].end());
            Line tempLine = line;
            tempLine.platformIndices.clear();
            for (int pi : largestSet) {
                int connectivityPi = (pi >= 0 && pi < oldSize) ? oldToConnectivity[pi] : -1;
                if (connectivityPi >= 0) tempLine.platformIndices.insert(connectivityPi);
            }
            int largestStations = CountPhysicalStationsInLine(tempLine, connectivityPlatforms);

            if (largestStations >= 2) {
                // Largest half keeps the line
                line.platformIndices = largestSet;
                line.stationCount = largestStations;

                // Neutralize all smaller halves
                for (int ci = 0; ci < (int)components.size(); ci++) {
                    if (ci == largestIdx) continue;
                    for (int pi : components[ci]) {
                        detachedPlatformsByLineId[line.id].insert(pi);
                        if (pi >= 0 && pi < (int)g_placedPlatforms.size()) {
                            long long key = MakePositionKey(g_placedPlatforms[pi].position.x,
                                                           g_placedPlatforms[pi].position.z);
                            releasedOwnershipKeys.insert(key);
                            g_demolishNeutralizedPlatformKeys.insert(key);
                            g_declinedNeutralBranchPlatformKeys.insert(key);
                        }
                    }
                }
                survivingPlatformsByLineId[line.id] = line.platformIndices;
            } else {
                // Even the largest half doesn't have enough stations - delete entire line
                for (int pi : survivors) {
                    if (pi >= 0 && pi < (int)g_placedPlatforms.size()) {
                        long long key = MakePositionKey(g_placedPlatforms[pi].position.x,
                                                       g_placedPlatforms[pi].position.z);
                        releasedOwnershipKeys.insert(key);
                        g_demolishNeutralizedPlatformKeys.insert(key);
                        g_declinedNeutralBranchPlatformKeys.insert(key);
                    }
                }
                deletedLineIds.insert(line.id);
                lineIndicesToErase.insert(li);
            }
        }
    }

    for (long long key : releasedOwnershipKeys) {
        g_lockedBranchOwnerLineId.erase(key);
        for (auto& line : g_lines)
            line.declinedBranchPlatformKeys.erase(key);
    }
    for (long long key : removedPositionKeys) {
        g_lockedBranchOwnerLineId.erase(key);
        g_overpassGroupsByPosKey.erase(key);
        for (auto& line : g_lines)
            line.declinedBranchPlatformKeys.erase(key);
    }

    // â"€â"€ Remove stale branch ownership entries for deleted lines â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€
    for (auto it = g_lockedBranchOwnerLineId.begin(); it != g_lockedBranchOwnerLineId.end(); ) {
        if (deletedLineIds.count(it->second)) it = g_lockedBranchOwnerLineId.erase(it);
        else ++it;
    }

    // â"€â"€ Pause trains only on lines that were actually deleted â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€
    auto pathPlatformIndex = [&](const Vector3& pathPos) -> int {
        Vector3 worldPos = { pathPos.x, 0.0f, pathPos.z };
        return FindPlatformIndexAtPos(worldPos, g_placedPlatforms);
    };
    auto classifyTrainFragment = [&](const PlacedTrain& train,
                                     const std::set<int>& detached,
                                     const std::set<int>& surviving) -> int {
        auto classifyIndex = [&](int idx) -> int {
            if (idx >= 0 && detached.count(idx)) return 1;
            if (idx >= 0 && surviving.count(idx)) return 2;
            return 0;
        };
        if (train.path.size() >= 2 && train.pathProgress >= 0.0f) {
            float remaining = train.pathProgress;
            for (int i = 0; i < (int)train.path.size() - 1; i++) {
                float segLen = Vector3Distance(train.path[i], train.path[i + 1]);
                if (remaining <= segLen + 0.001f || i == (int)train.path.size() - 2) {
                    int startClass = classifyIndex(pathPlatformIndex(train.path[i]));
                    int endClass = classifyIndex(pathPlatformIndex(train.path[i + 1]));
                    if (startClass != 0 && startClass == endClass) return startClass;
                    if (startClass != 0 && endClass == 0) return startClass;
                    if (endClass != 0 && startClass == 0) return endClass;
                    if (startClass != 0 && endClass != 0 && startClass != endClass) {
                        float t = (segLen > 0.001f) ? Clamp(remaining / segLen, 0.0f, 1.0f) : 0.0f;
                        return (t <= 0.5f) ? startClass : endClass;
                    }
                    break;
                }
                remaining -= segLen;
            }
        }

        Vector3 center = train.position;
        center.y = 0.0f;
        int centerClass = classifyIndex(FindPlatformIndexAtPos(center, g_placedPlatforms));
        if (centerClass != 0) return centerClass;

        PathPoint centerPoint = GetPathPoint(train.path, train.pathProgress);
        Vector3 pathCenter = centerPoint.position;
        pathCenter.y = 0.0f;
        int pathCenterClass = classifyIndex(FindPlatformIndexAtPos(pathCenter, g_placedPlatforms));
        if (pathCenterClass != 0) return pathCenterClass;

        return 0;
    };
    for (auto& train : g_placedTrains) {
        if (deletedLineIds.count(train.lineId)) {
            // Record the line color for display before the line is erased
            for (int li : lineIndicesToErase) {
                if (li >= 0 && li < (int)g_lines.size() && g_lines[li].id == train.lineId) {
                    train.pausedColor = g_lines[li].color;
                    break;
                }
            }
            train.isPaused = true;
            train.lineId = -1; // disassociate from deleted line
            continue;
        }
        auto detachedIt = detachedPlatformsByLineId.find(train.lineId);
        if (detachedIt == detachedPlatformsByLineId.end() || detachedIt->second.empty()) continue;
        auto survivingIt = survivingPlatformsByLineId.find(train.lineId);
        const std::set<int> emptySet;
        const std::set<int>& surviving = (survivingIt != survivingPlatformsByLineId.end())
            ? survivingIt->second
            : emptySet;
        int fragmentClass = classifyTrainFragment(train, detachedIt->second, surviving);
        if (fragmentClass == 1) {
            for (const auto& line : g_lines) {
                if (line.id == train.lineId) {
                    train.pausedColor = line.color;
                    break;
                }
            }
            train.isPaused = true;
            train.lineId = -1;
        }
    }
    // Deselect any currently-selected train that is now paused
    if (g_selectedTrainIndex >= 0 && g_selectedTrainIndex < (int)g_placedTrains.size()
        && g_placedTrains[g_selectedTrainIndex].isPaused)
        g_selectedTrainIndex = -1;

    // â"€â"€ Erase deleted lines (descending to keep indices valid) â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€
    {
        std::vector<int> sortedLines(lineIndicesToErase.begin(), lineIndicesToErase.end());
        std::sort(sortedLines.begin(), sortedLines.end(), std::greater<int>());
        for (int li : sortedLines)
            g_lines.erase(g_lines.begin() + li);
    }
    InvalidateLineCaches();

    // â"€â"€ Remove the platform tiles (descending order) â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€
    // Build old->new index remap BEFORE erasing (tiles is already sorted descending)
    std::vector<int> oldToNew(oldSize, -1);
    {
        int newIdx = 0;
        for (int i = 0; i < oldSize; i++) {
            if (removedSet.count(i)) continue;
            oldToNew[i] = newIdx++;
        }
    }

    std::sort(tiles.begin(), tiles.end(), std::greater<int>());
    for (int idx : tiles)
        g_placedPlatforms.erase(g_placedPlatforms.begin() + idx);
    InvalidatePlatformCaches();

    // â"€â"€ Remap all surviving lines' platformIndices to account for shifted indices â"€â"€
    for (auto& line : g_lines) {
        std::set<int> remapped;
        for (int pi : line.platformIndices) {
            if (pi >= 0 && pi < oldSize && oldToNew[pi] >= 0)
                remapped.insert(oldToNew[pi]);
        }
        line.platformIndices = remapped;
    }

    // Remap LineModalData snapshot indices if the modal is open
    if (g_lineModal.state != LineModalState::None) {
        auto remapVec = [&](std::vector<int>& v) {
            std::vector<int> out;
            for (int pi : v) {
                if (pi >= 0 && pi < oldSize && oldToNew[pi] >= 0)
                    out.push_back(oldToNew[pi]);
            }
            v = out;
        };
        remapVec(g_lineModal.pendingNewPlatforms);
        remapVec(g_lineModal.pendingJunctions);
        remapVec(g_lineModal.pendingEstablishPlatforms);
        g_lineModal.pendingCid = -1;
        std::set<int> remappedTarget;
        for (int pi : g_lineModal.targetPlatformIndicesAtShow) {
            if (pi >= 0 && pi < oldSize && oldToNew[pi] >= 0)
                remappedTarget.insert(oldToNew[pi]);
        }
        g_lineModal.targetPlatformIndicesAtShow = remappedTarget;
    }

    RefreshAwaitingTrainLock();

    // â"€â"€ Rebuild paths only for trains on affected lines â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€
    for (auto& train : g_placedTrains) {
        if (train.isPaused) continue;
        // Only rebuild for trains whose line was affected by this demolish
        if (train.lineId >= 0 && !deletedLineIds.count(train.lineId)
            && !affectedLineIds.count(train.lineId)) continue;
        RebuildTrainPath(train, g_placedPlatforms, g_gridSpacing);
    }

    // â"€â"€ Log and charge â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€
    if (g_playerCredits >= 100) g_playerCredits -= 100;
    int pausedCount = 0;
    for (const auto& t : g_placedTrains) if (t.isPaused) pausedCount++;
    char msg[320];
    bool lineWasDeleted = !deletedLineIds.empty();
    const char* actionStr = g_demolishConfirmModal.isStationDemolish ? "STATION DEMOLISHED" : "TRACK DEMOLISHED";
    const char* resultStr = lineWasDeleted ? "LINE REVERTED TO NEUTRAL" : "LINE TRIMMED";
    const char* trainStr = pausedCount > 0 ? " - DUE TO INFRASTRUCTURE DIFFICULTIES TRAINS ARE STATIONARY" : "";
    snprintf(msg, sizeof(msg), "%s - %s '%s' - 100 CREDITS%s",
        actionStr, resultStr, g_demolishConfirmModal.lineName, trainStr);
    AddTerminalMessage(msg);

    // â"€â"€ Close modal, clear modes, stay in demolish mode â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€
    g_demolishConfirmModal.open           = false;
    g_demolishConfirmModal.confirmClicked = false;
    g_demolishConfirmModal.cancelClicked  = false;
    g_demolishConfirmModal.anchorIdx      = -1;
    g_demolishConfirmModal.platformIdx    = -1;
    g_demolishConfirmModal.lineIdx        = -1;
    g_demolishConfirmModalOpen            = false;
    ClearAllPlacementModes();
    g_demolishMode = true;
}

static void DrawDemolishConfirmModal(DemolishConfirmModal& modal, int screenWidth, int screenHeight) {
    g_demolishConfirmModalOpen = modal.open;
    if (!modal.open) return;
    modal.framesOpen++;

    // Dim the entire screen
    DrawRectangle(0, 0, screenWidth, screenHeight, (Color){0, 0, 0, 200});

    float modalWidth  = 700.0f;
    float modalHeight = 320.0f;
    float modalX = (screenWidth  - modalWidth)  / 2.0f;
    float modalY = (screenHeight - modalHeight) / 2.0f;
    float titleBarH    = 50.0f;
    float contentInset = 40.0f;
    float innerX = modalX + contentInset;
    float innerY = modalY + titleBarH + 15.0f;
    float innerW = modalWidth - 2.0f * contentInset;
    float btnBarTop = 225.0f;
    float btnH      = 55.0f;
    float btnGap    = 20.0f;
    float btnW = (modalWidth - 2.0f * contentInset - btnGap) / 2.0f;
    Rectangle confirmBtn = { modalX + contentInset,                     modalY + btnBarTop, btnW, btnH };
    Rectangle cancelBtn  = { modalX + contentInset + btnW + btnGap,     modalY + btnBarTop, btnW, btnH };

    // Background
    if (g_texModalTemplate.id != 0) {
        DrawTexturePro(g_texModalTemplate,
            (Rectangle){0, 0, (float)g_texModalTemplate.width, (float)g_texModalTemplate.height},
            (Rectangle){modalX, modalY, modalWidth, modalHeight}, {0,0}, 0.0f, WHITE);
    } else {
        DrawRectangle((int)modalX, (int)modalY, (int)modalWidth, (int)modalHeight, (Color){28, 28, 36, 255});
        DrawRectangleLinesEx((Rectangle){modalX, modalY, modalWidth, modalHeight}, 2, RED);
    }

    // Title
    float titleFontSize = GetScaledFontSize(BASE_FONT_SIZE) * 2.0f;
    float bodyFontSize  = GetScaledFontSize(BASE_FONT_SIZE) * 1.35f;
    const char* titleStr = modal.isStationDemolish ? "DEMOLISH STATION" : "DEMOLISH TRACK SECTION";
    float titleW = MeasureTextEx(gameFont, titleStr, titleFontSize, 0.0f).x;
    DrawTextEx(gameFont, titleStr,
        (Vector2){modalX + (modalWidth - titleW) / 2.0f,
                  modalY + (titleBarH - titleFontSize) / 2.0f - 4.0f + modalHeight * 0.02f},
        titleFontSize, 0.0f, (Color){255, 80, 80, 255});

    // Body text
    char bodyText[512];
    if (modal.hasAffectedTrains) {
        snprintf(bodyText, sizeof(bodyText),
            "Demolishing '%s' will reset this line to neutral. "
            "%d train(s) on this line will be removed. "
            "Trains must be re-established on a new line or destroyed.",
            modal.lineName, modal.affectedTrainCount);
    } else {
        snprintf(bodyText, sizeof(bodyText),
            "This action will remove the Established Line '%s' and revert all track to neutral. Continue?",
            modal.lineName);
    }
    bool hasSiloWarning = (modal.siloWarning[0] != '\0');
    float bodyBottom = hasSiloWarning ? modalY + btnBarTop - 65.0f : modalY + btnBarTop - 10.0f;
    DrawWrappedText(bodyText, innerX + 10.0f, innerY + 10.0f,
                    innerW - 20.0f, bodyBottom,
                    bodyFontSize, (Color){220, 240, 255, 255});

    // Silo destruction warning â€” shown in orange when the affected line owns a silo
    if (hasSiloWarning) {
        char warnText[320];
        snprintf(warnText, sizeof(warnText), "! THIS WILL DESTROY YOUR %s !", modal.siloWarning);
        float warnW = MeasureTextEx(gameFont, warnText, bodyFontSize, 0.0f).x;
        DrawTextEx(gameFont, warnText,
            (Vector2){modalX + (modalWidth - warnW) / 2.0f, modalY + btnBarTop - 58.0f},
            bodyFontSize, 0.0f, (Color){255, 120, 0, 255});
    }

    // Buttons
    Vector2 mousePos  = CustomGetMousePosition();
    bool confirmHover = CheckCollisionPointRec(mousePos, confirmBtn);
    bool cancelHover  = CheckCollisionPointRec(mousePos, cancelBtn);
    Texture2D confirmTex = (confirmHover && g_texModalConfirmSelected.id != 0)
        ? g_texModalConfirmSelected : g_texModalConfirmNotSelected;
    Texture2D cancelTex  = (cancelHover  && g_texModalConfirmSelected.id != 0)
        ? g_texModalConfirmSelected : g_texModalConfirmNotSelected;

    if (confirmTex.id != 0) {
        DrawTexturePro(confirmTex, (Rectangle){0,0,(float)confirmTex.width,(float)confirmTex.height},
                       confirmBtn, {0,0}, 0.0f, WHITE);
    } else {
        DrawRectangleRec(confirmBtn, confirmHover ? (Color){160,40,40,255} : (Color){120,30,30,255});
    }
    if (cancelTex.id != 0) {
        DrawTexturePro(cancelTex, (Rectangle){0,0,(float)cancelTex.width,(float)cancelTex.height},
                       cancelBtn, {0,0}, 0.0f, WHITE);
    } else {
        DrawRectangleRec(cancelBtn, cancelHover ? (Color){60,120,80,255} : (Color){45,90,60,255});
    }

    // Button labels
    const char* yesLabel = "YES REMOVE LINE";
    const char* noLabel  = "NO CANCEL";
    float yesW = MeasureTextEx(gameFont, yesLabel, bodyFontSize, 0.0f).x;
    float noW  = MeasureTextEx(gameFont, noLabel,  bodyFontSize, 0.0f).x;
    DrawTextEx(gameFont, yesLabel,
        (Vector2){confirmBtn.x + (confirmBtn.width - yesW) / 2.0f,
                  confirmBtn.y + (btnH - bodyFontSize) / 2.0f - 4.0f},
        bodyFontSize, 0.0f, WHITE);
    DrawTextEx(gameFont, noLabel,
        (Vector2){cancelBtn.x  + (cancelBtn.width  - noW)  / 2.0f,
                  cancelBtn.y  + (btnH - bodyFontSize) / 2.0f - 4.0f},
        bodyFontSize, 0.0f, WHITE);

    // Handle clicks (skip first 2 frames to avoid accidental input)
    if (modal.framesOpen >= 2 && RawIsMouseButtonPressed(MOUSE_BUTTON_LEFT)) {
        if (confirmHover) modal.confirmClicked = true;
        else if (cancelHover) modal.cancelClicked = true;
    }
}

// Silo announcement modal: title and tip text for each silo type (what this silo has enabled)
// Build dynamic silo telemetry string showing actual bonuses now active.
// outBuf must be large enough (512+ chars).
static void BuildSiloTelemetryString(int system, char* outBuf, int bufSize) {
    outBuf[0] = '\0';
    switch (system) {
        case (int)SiloSystem::SYS1_CARGO: {
            int silos = g_siloCountBySystem[0];
            int listings = std::min(6, silos);
            int magFloors = g_magentaGrowthFloorBonus;
            snprintf(outBuf, bufSize,
                "COMMODITY LISTINGS: %d/6 unlocked. "
                "Magenta bureau floors: %d (+%d%% commodity share performance). "
                "Magenta lines double factory output.",
                listings, magFloors, magFloors * 10);
        } break;
        case (int)SiloSystem::SYS2_GREEN: {
            int silos = g_siloCountBySystem[1];
            int listings = std::min(6, silos);
            int floors = g_greenGrowthFloorBonus;
            float bullChance = std::min(0.90f, 0.30f + 0.003f * floors);
            snprintf(outBuf, bufSize,
                "GREEN LISTINGS: %d/6 unlocked. "
                "Bureau floors: %d (+%d%% share performance). "
                "Bullish trend odds: %.0f%% (base 30%%).",
                listings, floors, floors * 10, bullChance * 100.0f);
        } break;
        case (int)SiloSystem::SYS3_MAGENTA: {
            int silos = g_siloCountBySystem[2];
            int listings = std::min(6, silos);
            int floors = g_magentaGrowthFloorBonus;
            snprintf(outBuf, bufSize,
                "MAGENTA LISTINGS: %d/6 unlocked. "
                "Bureau floors: %d (+%d%% magenta & commodity share performance). "
                "Factory output doubled on magenta lines.",
                listings, floors, floors * 10);
        } break;
        case (int)SiloSystem::SYS4_CYAN: {
            int silos = g_siloCountBySystem[3];
            int listings = std::min(6, silos);
            int floors = g_cyanGrowthFloorBonus;
            float reduction = std::min(floors * 0.05f, 0.95f);
            float bullChance = std::min(0.90f, 0.30f + 0.003f * floors);
            snprintf(outBuf, bufSize,
                "CYAN LISTINGS: %d/6 unlocked. "
                "Bureau floors: %d. "
                "Running cost reduction: %.0f%% (5%% per floor, cap 95%%). "
                "Bullish trend odds: %.0f%%.",
                listings, floors, reduction * 100.0f, bullChance * 100.0f);
        } break;
        case (int)SiloSystem::SYS5_ORANGE: {
            int silos = g_siloCountBySystem[4];
            int listings = std::min(6, silos);
            int floors = g_orangeGrowthFloorBonus;
            float bullChance = std::min(0.90f, 0.30f + 0.003f * floors);
            snprintf(outBuf, bufSize,
                "ORANGE LISTINGS: %d/6 unlocked. "
                "Bureau floors: %d. "
                "Bureau cargo cost: -%d materials per placement. "
                "Bullish trend odds: %.0f%%.",
                listings, floors, floors, bullChance * 100.0f);
        } break;
        case (int)SiloSystem::SYS6_RED: {
            int silos = g_siloCountBySystem[5];
            int listings = std::min(6, silos);
            int floors = g_redGrowthFloorBonus;
            float reduction = std::min(floors * 0.10f, 0.90f);
            float bullChance = std::min(0.90f, 0.30f + 0.003f * floors);
            snprintf(outBuf, bufSize,
                "RED LISTINGS: %d/6 unlocked. "
                "Bureau floors: %d. "
                "Build cost discount: %.0f%% (10%% per floor, cap 90%%). "
                "Bullish trend odds: %.0f%%.",
                listings, floors, reduction * 100.0f, bullChance * 100.0f);
        } break;
        case (int)SiloSystem::SYS7_YELLOW: {
            int chaos = std::max(0, 50 - g_siloCountBySystem[6]);
            snprintf(outBuf, bufSize,
                "STOCK & COMMODITIES MARKET UNLOCKED! "
                "Market chaos: %d/50 (lower = calmer swings). "
                "Each additional yellow silo reduces chaos by 1.",
                chaos);
        } break;
        default:
            snprintf(outBuf, bufSize, "A new silo has been created on your network.");
            break;
    }
}

static void GetSiloAnnounceStrings(int system, const char** outTitle, const char** outTip) {
    // Titles remain descriptive; tip text is now built dynamically by the modal
    switch (system) {
        case (int)SiloSystem::SYS1_CARGO:   *outTitle = "MATERIALS SILO CREATED"; break;
        case (int)SiloSystem::SYS2_GREEN:   *outTitle = "GREEN EXECUTIVE SILO CREATED"; break;
        case (int)SiloSystem::SYS3_MAGENTA: *outTitle = "MAGENTA INDUSTRY SILO CREATED"; break;
        case (int)SiloSystem::SYS4_CYAN:    *outTitle = "CYAN EXECUTIVE SILO CREATED"; break;
        case (int)SiloSystem::SYS5_ORANGE:  *outTitle = "ORANGE EXECUTIVE SILO CREATED"; break;
        case (int)SiloSystem::SYS6_RED:     *outTitle = "RED EXECUTIVE SILO CREATED"; break;
        case (int)SiloSystem::SYS7_YELLOW:  *outTitle = "CORPORATE EXECUTIVE SILO CREATED"; break;
        default:                            *outTitle = "SILO CREATED"; break;
    }
    *outTip = ""; // unused; modal calls BuildSiloTelemetryString instead
}

// Draw silo-created announcement modal (uses modal_template.png and same button textures as line modal)
static void DrawSiloAnnounceModal(SiloAnnounceModalData& modal, int screenWidth, int screenHeight) {
    if (!modal.open) return;

    modal.framesOpen++;

    DrawRectangle(0, 0, screenWidth, screenHeight, (Color){0, 0, 0, 200});

    float modalWidth = 700.0f;
    float modalHeight = 450.0f;
    float modalX = (screenWidth - modalWidth) / 2.0f;
    float modalY = (screenHeight - modalHeight) / 2.0f;

    float titleBarH = 50.0f;
    float contentTop = 65.0f;
    float contentBottom = 370.0f;
    float contentInset = 40.0f;
    float innerX = modalX + contentInset;
    float innerY = modalY + contentTop;
    float innerW = modalWidth - 2.0f * contentInset;
    float innerH = contentBottom - contentTop;
    float btnBarTop = 375.0f;
    float btnH = 55.0f;
    float btnGap = 20.0f;
    float btnW = (modalWidth - 2.0f * contentInset - btnGap) / 2.0f;

    Rectangle contentBox = { innerX, innerY, innerW, innerH };
    Rectangle confirmBtn = { modalX + contentInset, modalY + btnBarTop, btnW, btnH };
    Rectangle cancelBtn = { modalX + contentInset + btnW + btnGap, modalY + btnBarTop, btnW, btnH };
    float closeBtnSize = 28.0f;
    Rectangle closeBtn = { modalX + modalWidth - closeBtnSize - 12.0f, modalY + 10.0f, closeBtnSize, closeBtnSize };

    if (g_texModalTemplate.id != 0) {
        Rectangle src = { 0, 0, (float)g_texModalTemplate.width, (float)g_texModalTemplate.height };
        Rectangle dst = { modalX, modalY, modalWidth, modalHeight };
        DrawTexturePro(g_texModalTemplate, src, dst, {0,0}, 0.0f, WHITE);
    } else {
        DrawRectangle((int)modalX, (int)modalY, (int)modalWidth, (int)modalHeight, (Color){28, 28, 36, 255});
        DrawRectangleLinesEx((Rectangle){modalX, modalY, modalWidth, modalHeight}, 2, SKYBLUE);
        DrawRectangleLinesEx(contentBox, 1, SKYBLUE);
    }

    bool closeHover = CheckCollisionPointRec(CustomGetMousePosition(), closeBtn);
    if (g_texModalTemplate.id == 0) {
        DrawRectangleRec(closeBtn, closeHover ? (Color){180, 50, 50, 255} : (Color){140, 40, 40, 255});
        float xPad = closeBtnSize * 0.25f;
        DrawLineEx((Vector2){closeBtn.x + xPad, closeBtn.y + xPad}, (Vector2){closeBtn.x + closeBtnSize - xPad, closeBtn.y + closeBtnSize - xPad}, 2, WHITE);
        DrawLineEx((Vector2){closeBtn.x + closeBtnSize - xPad, closeBtn.y + xPad}, (Vector2){closeBtn.x + xPad, closeBtn.y + closeBtnSize - xPad}, 2, WHITE);
    }

    float titleFontSize = GetScaledFontSize(BASE_FONT_SIZE) * 2.0f;
    float bodyFontSize = GetScaledFontSize(BASE_FONT_SIZE) * 1.35f;
    Color titleColor = (Color){0, 255, 200, 255};
    Color bodyColor = (Color){220, 240, 255, 255};

    const char* titleStr = nullptr;
    const char* tipStr = nullptr;
    GetSiloAnnounceStrings(modal.system, &titleStr, &tipStr);

    // Build dynamic telemetry string showing actual bonuses
    char telemetryBuf[512];
    BuildSiloTelemetryString(modal.system, telemetryBuf, sizeof(telemetryBuf));

    float titleW = MeasureTextEx(gameFont, titleStr, titleFontSize, 0.0f).x;
    DrawTextEx(gameFont, titleStr, (Vector2){modalX + (modalWidth - titleW) / 2.0f, modalY + (titleBarH - titleFontSize) / 2.0f - 4.0f + modalHeight * 0.02f}, titleFontSize, 0.0f, titleColor);

    // Telemetry text in content box (word-wrap)
    BeginScissorMode((int)innerX + 1, (int)innerY + 1, (int)innerW - 2, (int)innerH - 2);
    DrawWrappedText(telemetryBuf, innerX + 15.0f, innerY + 18.0f, innerW - 30.0f, innerY + innerH - bodyFontSize * 1.3f, bodyFontSize, bodyColor);
    EndScissorMode();

    // Buttons: GOT IT (left) and CONTINUE (right) - both dismiss, use same textures as line modal
    bool confirmHover = CheckCollisionPointRec(CustomGetMousePosition(), confirmBtn);
    bool cancelHover = CheckCollisionPointRec(CustomGetMousePosition(), cancelBtn);

    Texture2D confirmTex = (confirmHover && g_texModalConfirmSelected.id != 0) ? g_texModalConfirmSelected : g_texModalConfirmNotSelected;
    Texture2D cancelTex = (cancelHover && g_texModalConfirmSelected.id != 0) ? g_texModalConfirmSelected : g_texModalConfirmNotSelected;

    if (confirmTex.id != 0) {
        Rectangle src = {0, 0, (float)confirmTex.width, (float)confirmTex.height};
        DrawTexturePro(confirmTex, src, confirmBtn, {0,0}, 0.0f, WHITE);
    } else {
        DrawRectangleRec(confirmBtn, confirmHover ? (Color){60, 120, 80, 255} : (Color){45, 90, 60, 255});
    }
    if (cancelTex.id != 0) {
        Rectangle src = {0, 0, (float)cancelTex.width, (float)cancelTex.height};
        DrawTexturePro(cancelTex, src, cancelBtn, {0,0}, 0.0f, WHITE);
    } else {
        DrawRectangleRec(cancelBtn, cancelHover ? (Color){100, 60, 60, 255} : (Color){80, 50, 50, 255});
    }

    float btnFontSize = bodyFontSize * 1.15f;
    float gotItW = MeasureTextEx(gameFont, "GOT IT", btnFontSize, 0.0f).x;
    float contW = MeasureTextEx(gameFont, "CONTINUE", btnFontSize, 0.0f).x;
    DrawTextEx(gameFont, "GOT IT", (Vector2){confirmBtn.x + (confirmBtn.width - gotItW) / 2.0f, confirmBtn.y + (btnH - btnFontSize) / 2.0f - 2.0f}, btnFontSize, 0.0f, WHITE);
    DrawTextEx(gameFont, "CONTINUE", (Vector2){cancelBtn.x + (cancelBtn.width - contW) / 2.0f, cancelBtn.y + (btnH - btnFontSize) / 2.0f - 2.0f}, btnFontSize, 0.0f, WHITE);

    if (modal.framesOpen >= 2 && RawIsMouseButtonPressed(MOUSE_BUTTON_LEFT)) {
        if (closeHover || confirmHover || cancelHover) modal.gotItClicked = true;
    }
}

// Draw Stock & Commodities Market modal (launched by system13)
// Uses large_modal_template.png (989x695) with fallback to programmatic drawing
static void DrawStockCommoditiesModal(StockCommoditiesModalData& modal, int screenWidth, int screenHeight) {
    g_stockModalOpen = modal.open;
    if (!modal.open) return;

    modal.framesOpen++;

    DrawRectangle(0, 0, screenWidth, screenHeight, (Color){0, 0, 0, 200});

    float modalWidth = 989.0f;
    float modalHeight = 695.0f;
    float modalX = (screenWidth - modalWidth) / 2.0f;
    float modalY = (screenHeight - modalHeight) / 2.0f;

    // Layout derived from the large_modal_template.png (989x695)
    // Title bar: top ~7% (0-49px)
    // Content box: inset ~4% sides, top ~12%, bottom ~82%
    // Buttons: bottom ~85-95%
    float titleBarH = 49.0f;
    float contentTopPx = 90.0f;
    float contentBottomPx = 570.0f;
    float contentLeftPx = 40.0f;
    float contentRightPx = 40.0f;
    float innerX = modalX + contentLeftPx;
    float innerY = modalY + contentTopPx;
    float innerW = modalWidth - contentLeftPx - contentRightPx;
    float innerH = contentBottomPx - contentTopPx;

    Rectangle contentBox = { innerX, innerY, innerW, innerH };

    // Close button matches the X in the template top-right
    float closeBtnW = 42.0f;
    float closeBtnH = 42.0f;
    Rectangle closeBtn = { modalX + modalWidth - closeBtnW - 8.0f, modalY + 4.0f, closeBtnW, closeBtnH };

    // CONFIRM and CANCEL buttons at bottom of template
    float btnBarTop = 617.85f;
    float btnH = 50.0f;
    float btnW = 192.0f;
    float btnGap = 24.0f;
    float btnTotalW = btnW * 2.0f + btnGap;
    float btnStartX = modalX + (modalWidth - btnTotalW) / 2.0f;
    Rectangle confirmBtn = { btnStartX, modalY + btnBarTop, btnW, btnH };
    Rectangle cancelBtn  = { btnStartX + btnW + btnGap, modalY + btnBarTop, btnW, btnH };

    // Draw the large modal template
    if (g_texLargeModalTemplate.id != 0) {
        Rectangle src = { 0, 0, (float)g_texLargeModalTemplate.width, (float)g_texLargeModalTemplate.height };
        Rectangle dst = { modalX, modalY, modalWidth, modalHeight };
        DrawTexturePro(g_texLargeModalTemplate, src, dst, {0,0}, 0.0f, WHITE);
    } else {
        DrawRectangle((int)modalX, (int)modalY, (int)modalWidth, (int)modalHeight, (Color){18, 18, 28, 255});
        DrawRectangleLinesEx((Rectangle){modalX, modalY, modalWidth, modalHeight}, 2, (Color){0, 200, 255, 255});
        DrawRectangleLinesEx(contentBox, 1, (Color){0, 120, 160, 180});
    }

    Vector2 mousePos = CustomGetMousePosition();
    bool closeHover = CheckCollisionPointRec(mousePos, closeBtn);
    bool confirmHover = CheckCollisionPointRec(mousePos, confirmBtn);
    bool cancelHover = CheckCollisionPointRec(mousePos, cancelBtn);

    // Draw CONFIRM button with texture or fallback
    {
        Texture2D confirmTex = (confirmHover && g_texModalConfirmSelected.id != 0) ? g_texModalConfirmSelected : g_texModalConfirmNotSelected;
        if (confirmTex.id != 0) {
            Rectangle src = {0, 0, (float)confirmTex.width, (float)confirmTex.height};
            DrawTexturePro(confirmTex, src, confirmBtn, {0,0}, 0.0f, WHITE);
        } else {
            DrawRectangleRec(confirmBtn, confirmHover ? (Color){0, 140, 160, 255} : (Color){0, 80, 100, 255});
            DrawRectangleLinesEx(confirmBtn, 2, (Color){0, 255, 255, 255});
        }
    }

    // Draw CANCEL button with texture or fallback
    {
        Texture2D cancelTex = (cancelHover && g_texModalConfirmSelected.id != 0) ? g_texModalConfirmSelected : g_texModalConfirmNotSelected;
        if (cancelTex.id != 0) {
            Rectangle src = {0, 0, (float)cancelTex.width, (float)cancelTex.height};
            DrawTexturePro(cancelTex, src, cancelBtn, {0,0}, 0.0f, WHITE);
        } else {
            DrawRectangleRec(cancelBtn, cancelHover ? (Color){100, 60, 60, 255} : (Color){60, 40, 40, 255});
            DrawRectangleLinesEx(cancelBtn, 2, (Color){0, 255, 255, 255});
        }
    }

    // Close X hotspot border
    DrawRectangleLinesEx(closeBtn, 2, (Color){0, 255, 255, 255});

    float titleFontSize = GetScaledFontSize(BASE_FONT_SIZE) * 2.2f;
    float bodyFontSize = GetScaledFontSize(BASE_FONT_SIZE) * 1.6f;
    float smallFontSize = GetScaledFontSize(BASE_FONT_SIZE) * 1.3f;
    float btnFontSize = GetScaledFontSize(BASE_FONT_SIZE) * 1.5f;
    Color bodyColor = WHITE;

    // Button label text
    {
        float confirmW = MeasureTextEx(gameFont, "CONFIRM", btnFontSize, 0.0f).x;
        float cancelW = MeasureTextEx(gameFont, "CANCEL", btnFontSize, 0.0f).x;
        DrawTextEx(gameFont, "CONFIRM", (Vector2){confirmBtn.x + (confirmBtn.width - confirmW) / 2.0f, confirmBtn.y + (confirmBtn.height - btnFontSize) / 2.0f}, btnFontSize, 0.0f, WHITE);
        DrawTextEx(gameFont, "CANCEL", (Vector2){cancelBtn.x + (cancelBtn.width - cancelW) / 2.0f, cancelBtn.y + (cancelBtn.height - btnFontSize) / 2.0f}, btnFontSize, 0.0f, WHITE);
    }

    // Title centred in the title bar
    {
        const char* title = "STOCK & COMMODITIES MARKET";
        float titleW = MeasureTextEx(gameFont, title, titleFontSize, 0.0f).x;
        DrawTextEx(gameFont, title, (Vector2){modalX + (modalWidth - titleW) / 2.0f, modalY + (titleBarH - titleFontSize) / 2.0f + modalHeight * 0.03f}, titleFontSize, 0.0f, (Color){255, 255, 0, 255});
    }

    if (!g_marketUnlocked) {
        DrawTextEx(gameFont, "Build a Corporate Executive Silo (Yellow) to unlock the Market.",
                   (Vector2){innerX + 30.0f, innerY + 80.0f}, bodyFontSize, 0.0f, bodyColor);
        if (modal.framesOpen >= 2 && RawIsMouseButtonPressed(MOUSE_BUTTON_LEFT) && (closeHover || confirmHover || cancelHover)) modal.closeClicked = true;
        return;
    }

    // Volatility / status bar between title and content
    float statusBarY = modalY + titleBarH + 4.0f;
    {
        char chaosBuf[128];
        Color chaosColor = (g_marketChaos > 30) ? (Color){255, 60, 60, 255} :
                           (g_marketChaos > 15) ? (Color){255, 200, 0, 255} :
                                                  (Color){0, 255, 100, 255};
        const char* chaosLabel = (g_marketChaos > 30) ? "HIGH VOLATILITY" :
                                 (g_marketChaos > 15) ? "MODERATE" : "STABLE";
        int mktWk, mktMonth, mktYear;
        GetYearClock(g_dayCount, mktWk, mktMonth, mktYear);
        snprintf(chaosBuf, sizeof(chaosBuf), "VOLATILITY: %d%% [%s]  |  WK:%d M:%d YR:%d  |  REVENUE/WK: %d CR",
                 g_marketChaos * 2, chaosLabel, mktWk, mktMonth, mktYear, g_marketRevenueLast);
        DrawTextEx(gameFont, chaosBuf, (Vector2){innerX + 6.0f, statusBarY}, smallFontSize * 0.9f, 0.0f, chaosColor);

        float barX = modalX + modalWidth - 200.0f;
        float barY2 = statusBarY + 2.0f;
        float barW = 150.0f;
        float barH = smallFontSize * 0.85f;
        DrawRectangle((int)barX, (int)barY2, (int)barW, (int)barH, (Color){40, 40, 50, 255});
        float fillW = barW * (1.0f - g_marketChaos / 50.0f);
        DrawRectangle((int)barX, (int)barY2, (int)fillW, (int)barH, chaosColor);
        DrawRectangleLinesEx((Rectangle){barX, barY2, barW, barH}, 1, (Color){80, 80, 100, 255});
    }

    // Tab bar just above the content box
    float tabBarY = statusBarY + smallFontSize + 6.0f;
    float tabStartX = innerX;
    float tabH = 26.0f;
    float tabGap = 5.0f;
    Rectangle tabRects[(int)MarketTab::COUNT];

    for (int t = 0; t < (int)MarketTab::COUNT; t++) {
        MarketTab tab = (MarketTab)t;
        const char* name = GetTabName(tab);
        float tw = MeasureTextEx(gameFont, name, smallFontSize, 0.0f).x + 20.0f;
        tabRects[t] = { tabStartX, tabBarY, tw, tabH };

        bool isActive = (modal.activeTab == tab);
        bool isHover = CheckCollisionPointRec(mousePos, tabRects[t]);
        int tabUnlocked = GetUnlockedCountForTab(tab);
        Color tabCol = GetTabColor(tab);

        if (isActive) {
            DrawRectangleRec(tabRects[t], (Color){(unsigned char)(tabCol.r / 4), (unsigned char)(tabCol.g / 4), (unsigned char)(tabCol.b / 4), 255});
            DrawRectangleLinesEx(tabRects[t], 1, tabCol);
        } else if (isHover) {
            DrawRectangleRec(tabRects[t], (Color){40, 40, 55, 255});
        } else {
            DrawRectangleRec(tabRects[t], (Color){25, 25, 35, 255});
        }

        Color textCol = (tabUnlocked > 0) ? (isActive ? tabCol : (Color){(unsigned char)(tabCol.r/2), (unsigned char)(tabCol.g/2), (unsigned char)(tabCol.b/2), 200}) : (Color){80, 80, 80, 255};
        DrawTextEx(gameFont, name, (Vector2){tabStartX + 10.0f, tabBarY + (tabH - smallFontSize) / 2.0f}, smallFontSize, 0.0f, textCol);
        tabStartX += tw + tabGap;
    }

    // Active events banner
    float bannerY = tabBarY + tabH + 4.0f;
    if (!g_activeMarketEvents.empty()) {
        for (const auto& ev : g_activeMarketEvents) {
            Color evCol = (ev.modifier > 0) ? (Color){0, 255, 100, 200} : (Color){255, 80, 80, 200};
            DrawTextEx(gameFont, ev.description, (Vector2){innerX + 6.0f, bannerY}, smallFontSize * 0.85f, 0.0f, evCol);
            bannerY += smallFontSize + 2.0f;
        }
    }

    // Content listing area
    float listY = bannerY + 6.0f;
    float listBottom = modalY + contentBottomPx - 8.0f;

    MarketTab activeTab = modal.activeTab;
    const MarketListing* listings = GetListingsForTab(activeTab);
    MarketListingState* states = GetStatesForTab(activeTab);
    int unlocked = GetUnlockedCountForTab(activeTab);

    BeginScissorMode((int)innerX, (int)listY, (int)innerW, (int)(listBottom - listY));

    if (unlocked == 0) {
        DrawTextEx(gameFont, "LOCKED", (Vector2){innerX + 30.0f, listY + 30.0f}, bodyFontSize * 1.2f, 0.0f, (Color){120, 120, 120, 255});
        DrawTextEx(gameFont, GetSiloHintForTab(activeTab), (Vector2){innerX + 30.0f, listY + 30.0f + bodyFontSize * 1.6f}, smallFontSize, 0.0f, (Color){180, 180, 180, 255});
    } else {
        float rowH = bodyFontSize * 1.5f;
        float colSymX = innerX + 12.0f;
        float colNameX = innerX + 140.0f;
        float colPriceX = innerX + 400.0f;
        float colChgX = innerX + 530.0f;
        float colOwnX = innerX + 660.0f;
        float colActX = innerX + 760.0f;

        Color headerCol = (Color){0, 200, 255, 255};
        DrawTextEx(gameFont, "SYMBOL", (Vector2){colSymX, listY}, smallFontSize, 0.0f, headerCol);
        DrawTextEx(gameFont, "NAME", (Vector2){colNameX, listY}, smallFontSize, 0.0f, headerCol);
        DrawTextEx(gameFont, "PRICE", (Vector2){colPriceX, listY}, smallFontSize, 0.0f, headerCol);
        DrawTextEx(gameFont, "CHG%", (Vector2){colChgX, listY}, smallFontSize, 0.0f, headerCol);
        DrawTextEx(gameFont, "OWNED", (Vector2){colOwnX, listY}, smallFontSize, 0.0f, headerCol);
        DrawTextEx(gameFont, "BUY/SELL", (Vector2){colActX, listY}, smallFontSize, 0.0f, headerCol);

        DrawLineEx((Vector2){innerX, listY + smallFontSize + 3.0f}, (Vector2){innerX + innerW, listY + smallFontSize + 3.0f}, 1, (Color){60, 60, 80, 255});

        float rowStartY = listY + smallFontSize + 8.0f - modal.scrollOffset;

        for (int i = 0; i < unlocked; i++) {
            float ry = rowStartY + i * rowH;
            if (ry + rowH < listY || ry > listBottom) continue;

            bool isSelected = (modal.selectedListing == i);
            Rectangle rowRect = { innerX, ry, innerW, rowH - 2.0f };
            bool rowHover = CheckCollisionPointRec(mousePos, rowRect) && ry >= listY && ry + rowH <= listBottom;

            if (isSelected) {
                DrawRectangleRec(rowRect, (Color){40, 60, 80, 200});
            } else if (rowHover) {
                DrawRectangleRec(rowRect, (Color){30, 40, 55, 150});
            }

            char buf[64];
            snprintf(buf, sizeof(buf), "[%s]", listings[i].symbol);
            DrawTextEx(gameFont, buf, (Vector2){colSymX, ry + 3.0f}, smallFontSize, 0.0f, GetTabColor(activeTab));

            DrawTextEx(gameFont, listings[i].name, (Vector2){colNameX, ry + 3.0f}, smallFontSize, 0.0f, bodyColor);

            snprintf(buf, sizeof(buf), "$%.0f", states[i].price);
            DrawTextEx(gameFont, buf, (Vector2){colPriceX, ry + 3.0f}, smallFontSize, 0.0f, (Color){255, 255, 200, 255});

            float chg = (states[i].previousPrice > 0.01f)
                ? ((states[i].price - states[i].previousPrice) / states[i].previousPrice) * 100.0f : 0.0f;
            Color chgCol = (chg > 0.01f) ? (Color){0, 255, 80, 255} :
                           (chg < -0.01f) ? (Color){255, 60, 60, 255} : (Color){160, 160, 160, 255};
            const char* arrow = (chg > 0.01f) ? "+" : "";
            snprintf(buf, sizeof(buf), "%s%.1f%%", arrow, chg);
            DrawTextEx(gameFont, buf, (Vector2){colChgX, ry + 3.0f}, smallFontSize, 0.0f, chgCol);

            if (states[i].sharesOwned > 0) {
                snprintf(buf, sizeof(buf), "%d", states[i].sharesOwned);
                DrawTextEx(gameFont, buf, (Vector2){colOwnX, ry + 3.0f}, smallFontSize, 0.0f, (Color){255, 255, 0, 255});
            } else {
                DrawTextEx(gameFont, "-", (Vector2){colOwnX, ry + 3.0f}, smallFontSize, 0.0f, (Color){80, 80, 80, 255});
            }

            // Buy/Sell buttons
            float btnW = 40.0f;
            float btnH = smallFontSize + 4.0f;
            Rectangle buyBtn = { colActX, ry + 2.0f, btnW, btnH };
            Rectangle sellBtn = { colActX + btnW + 6.0f, ry + 2.0f, btnW, btnH };
            bool buyHover = CheckCollisionPointRec(mousePos, buyBtn);
            bool sellHover = CheckCollisionPointRec(mousePos, sellBtn);

            int cost = (int)ceilf(states[i].price);
            bool canBuy = (g_playerCredits >= cost);
            bool canSell = (states[i].sharesOwned > 0);

            Color buyBg = canBuy ? (buyHover ? (Color){0, 120, 60, 255} : (Color){0, 80, 40, 255}) : (Color){40, 40, 40, 255};
            Color sellBg = canSell ? (sellHover ? (Color){120, 40, 40, 255} : (Color){80, 30, 30, 255}) : (Color){40, 40, 40, 255};
            DrawRectangleRec(buyBtn, buyBg);
            DrawRectangleRec(sellBtn, sellBg);
            DrawRectangleLinesEx(buyBtn, 1, canBuy ? (Color){0, 200, 100, 255} : (Color){60, 60, 60, 255});
            DrawRectangleLinesEx(sellBtn, 1, canSell ? (Color){200, 60, 60, 255} : (Color){60, 60, 60, 255});
            Color buyTxt = canBuy ? (Color){0, 255, 128, 255} : (Color){80, 80, 80, 255};
            Color sellTxt = canSell ? (Color){255, 80, 80, 255} : (Color){80, 80, 80, 255};
            DrawTextEx(gameFont, "BUY", (Vector2){buyBtn.x + 5.0f, buyBtn.y + 2.0f}, smallFontSize * 0.85f, 0.0f, buyTxt);
            DrawTextEx(gameFont, "SELL", (Vector2){sellBtn.x + 4.0f, sellBtn.y + 2.0f}, smallFontSize * 0.85f, 0.0f, sellTxt);

            if (modal.framesOpen >= 2 && RawIsMouseButtonPressed(MOUSE_BUTTON_LEFT)) {
                if (buyHover && canBuy) MarketBuyShare(activeTab, i);
                if (sellHover && canSell) MarketSellShare(activeTab, i);
                if (rowHover && !buyHover && !sellHover) modal.selectedListing = i;
            }
        }

        // Portfolio summary below listings
        float summaryY = rowStartY + unlocked * rowH + 12.0f;
        if (summaryY < listBottom - bodyFontSize * 2.0f) {
            int totalShares = 0;
            float totalValue = 0.0f;
            for (int i = 0; i < unlocked; i++) {
                totalShares += states[i].sharesOwned;
                totalValue += states[i].sharesOwned * states[i].price;
            }
            if (totalShares > 0) {
                char sumBuf[128];
                snprintf(sumBuf, sizeof(sumBuf), "PORTFOLIO: %d shares  |  VALUE: $%.0f", totalShares, totalValue);
                DrawTextEx(gameFont, sumBuf, (Vector2){innerX + 12.0f, summaryY}, smallFontSize, 0.0f, (Color){0, 200, 255, 200});
            }
        }
    }

    EndScissorMode();

    // Handle scroll
    float wheel = CustomGetMouseWheelMove();
    if (CheckCollisionPointRec(mousePos, contentBox) && fabsf(wheel) > 0.01f) {
        modal.scrollOffset -= wheel * bodyFontSize * 1.5f;
        if (modal.scrollOffset < 0.0f) modal.scrollOffset = 0.0f;
        float maxScroll = unlocked * bodyFontSize * 1.5f - innerH + 80.0f;
        if (maxScroll < 0.0f) maxScroll = 0.0f;
        if (modal.scrollOffset > maxScroll) modal.scrollOffset = maxScroll;
    }

    // Handle tab clicks, button clicks, and close
    if (modal.framesOpen >= 2 && RawIsMouseButtonPressed(MOUSE_BUTTON_LEFT)) {
        if (closeHover || confirmHover || cancelHover) modal.closeClicked = true;
        for (int t = 0; t < (int)MarketTab::COUNT; t++) {
            if (CheckCollisionPointRec(mousePos, tabRects[t])) {
                modal.activeTab = (MarketTab)t;
                modal.scrollOffset = 0.0f;
                modal.selectedListing = -1;
            }
        }
    }

    // Tab keyboard shortcuts: 1-6
    for (int k = 0; k < (int)MarketTab::COUNT; k++) {
        if (CustomIsKeyPressed(KEY_ONE + k)) {
            modal.activeTab = (MarketTab)k;
            modal.scrollOffset = 0.0f;
            modal.selectedListing = -1;
        }
    }
}

// Quit confirmation modal: shown when player presses ESC in 3D view (not map mode, not splash)
static void DrawQuitConfirmModal(QuitConfirmModal& modal, int screenWidth, int screenHeight) {
    g_quitConfirmModalOpen = modal.open;
    if (!modal.open) return;
    modal.framesOpen++;

    // Dim the screen
    DrawRectangle(0, 0, screenWidth, screenHeight, (Color){0, 0, 0, 180});

    float modalWidth  = 700.0f;
    float modalHeight = 450.0f;
    float modalX = (screenWidth  - modalWidth)  / 2.0f;
    float modalY = (screenHeight - modalHeight) / 2.0f;
    float titleBarH    = 50.0f;
    float contentInset = 40.0f;
    float innerX = modalX + contentInset;
    float innerY = modalY + titleBarH + 12.0f;
    float innerW = modalWidth - 2.0f * contentInset;
    float btnBarTop = 375.0f;
    float btnH      = 55.0f;
    float btnGap    = 20.0f;
    float btnW = (modalWidth - 2.0f * contentInset - btnGap) / 2.0f;
    Rectangle yesBtn = { modalX + contentInset,                 modalY + btnBarTop, btnW, btnH };
    Rectangle noBtn  = { modalX + contentInset + btnW + btnGap, modalY + btnBarTop, btnW, btnH };

    if (g_texModalTemplate.id != 0) {
        DrawTexturePro(g_texModalTemplate,
            (Rectangle){0, 0, (float)g_texModalTemplate.width, (float)g_texModalTemplate.height},
            (Rectangle){modalX, modalY, modalWidth, modalHeight}, {0,0}, 0.0f, WHITE);
    } else {
        DrawRectangle((int)modalX, (int)modalY, (int)modalWidth, (int)modalHeight, (Color){28, 28, 36, 255});
        DrawRectangleLinesEx((Rectangle){modalX, modalY, modalWidth, modalHeight}, 2, (Color){255,80,80,255});
    }

    float titleFontSize = GetScaledFontSize(BASE_FONT_SIZE) * 2.0f;
    float bodyFontSize  = GetScaledFontSize(BASE_FONT_SIZE) * 1.35f;

    // Title & body adapt to quit-to-desktop vs quit-to-menu
    const char* titleStr = modal.quitToDesktop ? "EXIT GAME?" : "QUIT GAME?";
    const char* bodyStr  = modal.quitToDesktop
        ? "Close CyberTrain and return to the desktop?"
        : "Return to the main menu? Your current game will be lost.";
    float titleW = MeasureTextEx(gameFont, titleStr, titleFontSize, 0.0f).x;
    DrawTextEx(gameFont, titleStr,
        (Vector2){modalX + (modalWidth - titleW) / 2.0f,
                  modalY + (titleBarH - titleFontSize) / 2.0f - 4.0f + modalHeight * 0.02f},
        titleFontSize, 0.0f, (Color){200, 200, 200, 255});

    // Body
    float bodyBottom = modalY + btnBarTop - 10.0f;
    DrawWrappedText(bodyStr, innerX + 8.0f, innerY + 8.0f,
                    innerW - 16.0f, bodyBottom,
                    bodyFontSize, (Color){220, 240, 255, 255});

    // Buttons
    Vector2 mousePos = CustomGetMousePosition();
    bool yesHover    = CheckCollisionPointRec(mousePos, yesBtn);
    bool noHover     = CheckCollisionPointRec(mousePos, noBtn);
    Texture2D yesTx  = (yesHover && g_texModalConfirmSelected.id != 0)
        ? g_texModalConfirmSelected : g_texModalConfirmNotSelected;
    Texture2D noTx   = (noHover  && g_texModalConfirmSelected.id != 0)
        ? g_texModalConfirmSelected : g_texModalConfirmNotSelected;

    if (yesTx.id != 0) {
        DrawTexturePro(yesTx, (Rectangle){0,0,(float)yesTx.width,(float)yesTx.height},
                       yesBtn, {0,0}, 0.0f, WHITE);
    } else {
        DrawRectangleRec(yesBtn, yesHover ? (Color){160,40,40,255} : (Color){120,30,30,255});
    }
    if (noTx.id != 0) {
        DrawTexturePro(noTx, (Rectangle){0,0,(float)noTx.width,(float)noTx.height},
                       noBtn, {0,0}, 0.0f, WHITE);
    } else {
        DrawRectangleRec(noBtn, noHover ? (Color){60,120,80,255} : (Color){45,90,60,255});
    }

    const char* yesLabel = "YES";
    const char* noLabel  = "NO";
    float yW = MeasureTextEx(gameFont, yesLabel, bodyFontSize, 0.0f).x;
    float nW = MeasureTextEx(gameFont, noLabel,  bodyFontSize, 0.0f).x;
    DrawTextEx(gameFont, yesLabel,
        (Vector2){yesBtn.x + (yesBtn.width - yW) / 2.0f,
                  yesBtn.y + (btnH - bodyFontSize) / 2.0f - 4.0f},
        bodyFontSize, 0.0f, WHITE);
    DrawTextEx(gameFont, noLabel,
        (Vector2){noBtn.x  + (noBtn.width  - nW) / 2.0f,
                  noBtn.y  + (btnH - bodyFontSize) / 2.0f - 4.0f},
        bodyFontSize, 0.0f, WHITE);

    if (modal.framesOpen >= 2) {
        if (RawIsMouseButtonPressed(MOUSE_BUTTON_LEFT)) {
            if (yesHover)      modal.yesClicked = true;
            else if (noHover)  modal.noClicked  = true;
        }
        // Keyboard: ESC or N = dismiss, Enter or Y = confirm
        if (CustomIsKeyPressed(KEY_ESCAPE) || CustomIsKeyPressed(KEY_N))
            modal.noClicked = true;
        if (CustomIsKeyPressed(KEY_ENTER) || CustomIsKeyPressed(KEY_Y))
            modal.yesClicked = true;
    }
}

// Junction configuration modal: click a junction → list trains → cycle exit pairs per train.
static void DrawJunctionConfigModal(JunctionConfigModal& modal, int screenWidth, int screenHeight) {
    g_junctionConfigModalOpen = modal.open;
    if (!modal.open) return;
    modal.framesOpen++;

    // Dim the screen
    DrawRectangle(0, 0, screenWidth, screenHeight, (Color){0, 0, 0, 180});

    int trainCount = (int)modal.trainIndices.size();
    float rowH = 52.0f;
    float headerH = 60.0f;
    float btnBarH = 64.0f;
    float contentH = headerH + rowH * std::max(trainCount, 1) + 16.0f + btnBarH;
    float modalWidth  = 700.0f;
    float modalHeight = std::min(contentH, 520.0f);
    float modalX = (screenWidth  - modalWidth)  / 2.0f;
    float modalY = (screenHeight - modalHeight) / 2.0f;
    float contentInset = 28.0f;

    // Background
    if (g_texModalTemplate.id != 0) {
        DrawTexturePro(g_texModalTemplate,
            (Rectangle){0, 0, (float)g_texModalTemplate.width, (float)g_texModalTemplate.height},
            (Rectangle){modalX, modalY, modalWidth, modalHeight}, {0,0}, 0.0f, WHITE);
    } else {
        DrawRectangle((int)modalX, (int)modalY, (int)modalWidth, (int)modalHeight, (Color){28, 28, 36, 255});
        DrawRectangleLinesEx((Rectangle){modalX, modalY, modalWidth, modalHeight}, 2, (Color){0, 200, 200, 255});
    }

    float titleFontSize = GetScaledFontSize(BASE_FONT_SIZE) * 1.8f;
    float bodyFontSize  = GetScaledFontSize(BASE_FONT_SIZE) * 1.25f;
    float smallFontSize = GetScaledFontSize(BASE_FONT_SIZE) * 1.0f;

    // Title
    const char* titleStr = "JUNCTION CONFIGURATION";
    float titleW = MeasureTextEx(gameFont, titleStr, titleFontSize, 0.0f).x;
    DrawTextEx(gameFont, titleStr,
        (Vector2){modalX + (modalWidth - titleW) / 2.0f, modalY + 10.0f},
        titleFontSize, 0.0f, (Color){0, 220, 220, 255});

    float listTop = modalY + headerH;
    Vector2 mousePos = CustomGetMousePosition();

    // Get junction exits info for display
    std::vector<Vector3> adjacent;
    int numExits = 0;
    int numPairs = 0;
    if (modal.junctionPlatformIndex >= 0 && modal.junctionPlatformIndex < (int)g_placedPlatforms.size()) {
        adjacent = GetSortedAdjacentPositions(modal.junctionPos, g_placedPlatforms, g_gridSpacing);
        numExits = (int)adjacent.size();
        numPairs = NumJunctionPairs(numExits);
    }

    if (trainCount == 0) {
        const char* emptyStr = "No trains pass through this junction.";
        float ew = MeasureTextEx(gameFont, emptyStr, bodyFontSize, 0.0f).x;
        DrawTextEx(gameFont, emptyStr,
            (Vector2){modalX + (modalWidth - ew) / 2.0f, listTop + 20.0f},
            bodyFontSize, 0.0f, (Color){180, 180, 180, 255});
    } else {
        // Column headers
        float colTrain = modalX + contentInset;
        float colLine  = colTrain + 160.0f;
        float colPair  = colLine + 200.0f;
        float colBtn   = modalWidth - contentInset - 120.0f + modalX;
        DrawTextEx(gameFont, "TRAIN", (Vector2){colTrain, listTop - 18.0f}, smallFontSize, 0.0f, (Color){140, 140, 140, 255});
        DrawTextEx(gameFont, "LINE", (Vector2){colLine, listTop - 18.0f}, smallFontSize, 0.0f, (Color){140, 140, 140, 255});
        DrawTextEx(gameFont, "PAIR", (Vector2){colPair, listTop - 18.0f}, smallFontSize, 0.0f, (Color){140, 140, 140, 255});

        for (int slot = 0; slot < trainCount; slot++) {
            int ti = modal.trainIndices[slot];
            if (ti < 0 || ti >= (int)g_placedTrains.size()) continue;
            const PlacedTrain& train = g_placedTrains[ti];
            float rowY = listTop + slot * rowH;

            Rectangle rowRect = { modalX + contentInset, rowY, modalWidth - 2 * contentInset, rowH - 4.0f };
            bool rowHover = CheckCollisionPointRec(mousePos, rowRect);

            // Row background (highlight selected)
            Color rowBg = (slot == modal.selectedTrainSlot)
                ? (Color){50, 80, 80, 200}
                : (rowHover ? (Color){40, 50, 60, 150} : (Color){30, 30, 38, 100});
            DrawRectangleRec(rowRect, rowBg);

            // Train ID
            char trainLabel[32];
            snprintf(trainLabel, sizeof(trainLabel), "TRAIN %d", train.id);
            DrawTextEx(gameFont, trainLabel, (Vector2){colTrain + 4.0f, rowY + 12.0f}, bodyFontSize, 0.0f, WHITE);

            // Line color swatch + name
            Color lineColor = {128, 128, 128, 255};
            const char* lineName = "---";
            for (const auto& line : g_lines) {
                if (line.id == train.lineId) {
                    lineColor = line.color;
                    lineName = line.name.c_str();
                    break;
                }
            }
            DrawRectangle((int)(colLine + 4.0f), (int)(rowY + 14.0f), 16, 16, lineColor);
            DrawTextEx(gameFont, lineName, (Vector2){colLine + 26.0f, rowY + 12.0f}, bodyFontSize, 0.0f, (Color){200, 200, 200, 255});

            // Current exit pair
            int currentPair = train.GetJunctionSetting(modal.junctionPos.x, modal.junctionPos.z, &adjacent);
            if (currentPair < 0 && numPairs > 0)
                currentPair = DefaultJunctionPairIndex(modal.junctionPos, adjacent);
            char pairLabel[32];
            if (numPairs > 0) {
                int pI = 0, pJ = 0;
                PairIndexToIJ(numExits, currentPair, pI, pJ);
                snprintf(pairLabel, sizeof(pairLabel), "%d-%d", pI + 1, pJ + 1);
            } else {
                snprintf(pairLabel, sizeof(pairLabel), "---");
            }
            DrawTextEx(gameFont, pairLabel, (Vector2){colPair + 4.0f, rowY + 12.0f}, bodyFontSize, 0.0f, (Color){0, 255, 100, 255});

            // SWITCH button
            float switchBtnW = 110.0f;
            float switchBtnH = 34.0f;
            Rectangle switchBtn = { colBtn, rowY + 8.0f, switchBtnW, switchBtnH };
            bool switchHover = CheckCollisionPointRec(mousePos, switchBtn);
            Color switchBg = switchHover ? (Color){60, 140, 80, 255} : (Color){45, 100, 60, 255};
            DrawRectangleRec(switchBtn, switchBg);
            DrawRectangleLinesEx(switchBtn, 1, (Color){80, 200, 120, 255});
            const char* switchLabel = "SWITCH";
            float sw = MeasureTextEx(gameFont, switchLabel, smallFontSize, 0.0f).x;
            DrawTextEx(gameFont, switchLabel,
                (Vector2){switchBtn.x + (switchBtnW - sw) / 2.0f, switchBtn.y + (switchBtnH - smallFontSize) / 2.0f - 2.0f},
                smallFontSize, 0.0f, WHITE);

            // Handle clicks
            if (modal.framesOpen >= 2 && RawIsMouseButtonPressed(MOUSE_BUTTON_LEFT)) {
                if (switchHover && numPairs > 0) {
                    modal.selectedTrainSlot = slot;
                    modal.switchClicked = true;
                } else if (rowHover) {
                    modal.selectedTrainSlot = slot;
                }
            }
        }
    }

    // DONE button
    float btnW = 180.0f;
    float btnH = 44.0f;
    Rectangle doneBtn = { modalX + (modalWidth - btnW) / 2.0f, modalY + modalHeight - btnBarH + 4.0f, btnW, btnH };
    bool doneHover = CheckCollisionPointRec(mousePos, doneBtn);
    Color doneBg = doneHover ? (Color){60, 120, 160, 255} : (Color){40, 80, 120, 255};
    DrawRectangleRec(doneBtn, doneBg);
    DrawRectangleLinesEx(doneBtn, 1, (Color){80, 160, 220, 255});
    const char* doneLabel = "DONE";
    float dw = MeasureTextEx(gameFont, doneLabel, bodyFontSize, 0.0f).x;
    DrawTextEx(gameFont, doneLabel,
        (Vector2){doneBtn.x + (btnW - dw) / 2.0f, doneBtn.y + (btnH - bodyFontSize) / 2.0f - 2.0f},
        bodyFontSize, 0.0f, WHITE);

    if (modal.framesOpen >= 2) {
        if (RawIsMouseButtonPressed(MOUSE_BUTTON_LEFT) && doneHover)
            modal.doneClicked = true;
        // Keyboard: ESC to close
        if (CustomIsKeyPressed(KEY_ESCAPE))
            modal.doneClicked = true;
    }
}

// Modal shown when player clicks a paused (infrastructure-reset) train
static void DrawPausedTrainDeleteModal(PausedTrainDeleteModal& modal, int screenWidth, int screenHeight) {
    if (!modal.open) return;
    modal.framesOpen++;

    // Dim the screen
    DrawRectangle(0, 0, screenWidth, screenHeight, (Color){0, 0, 0, 180});

    float modalWidth  = 640.0f;
    float modalHeight = 280.0f;
    float modalX = (screenWidth  - modalWidth)  / 2.0f;
    float modalY = (screenHeight - modalHeight) / 2.0f;
    float titleBarH    = 50.0f;
    float contentInset = 36.0f;
    float innerX = modalX + contentInset;
    float innerY = modalY + titleBarH + 12.0f;
    float innerW = modalWidth - 2.0f * contentInset;
    float btnBarTop = 205.0f;
    float btnH      = 50.0f;
    float btnGap    = 18.0f;
    float btnW = (modalWidth - 2.0f * contentInset - btnGap) / 2.0f;
    Rectangle destroyBtn = { modalX + contentInset,                   modalY + btnBarTop, btnW, btnH };
    Rectangle cancelBtn  = { modalX + contentInset + btnW + btnGap,   modalY + btnBarTop, btnW, btnH };

    if (g_texModalTemplate.id != 0) {
        DrawTexturePro(g_texModalTemplate,
            (Rectangle){0, 0, (float)g_texModalTemplate.width, (float)g_texModalTemplate.height},
            (Rectangle){modalX, modalY, modalWidth, modalHeight}, {0,0}, 0.0f, WHITE);
    } else {
        DrawRectangle((int)modalX, (int)modalY, (int)modalWidth, (int)modalHeight, (Color){28, 28, 36, 255});
        DrawRectangleLinesEx((Rectangle){modalX, modalY, modalWidth, modalHeight}, 2, (Color){255,80,80,255});
    }

    float titleFontSize = GetScaledFontSize(BASE_FONT_SIZE) * 2.0f;
    float bodyFontSize  = GetScaledFontSize(BASE_FONT_SIZE) * 1.35f;

    // Title
    const char* titleStr = "STATIONARY TRAIN";
    float titleW = MeasureTextEx(gameFont, titleStr, titleFontSize, 0.0f).x;
    DrawTextEx(gameFont, titleStr,
        (Vector2){modalX + (modalWidth - titleW) / 2.0f,
                  modalY + (titleBarH - titleFontSize) / 2.0f - 4.0f + modalHeight * 0.02f},
        titleFontSize, 0.0f, (Color){200, 200, 200, 255});

    // Body
    const char* bodyStr =
        "Due to infrastructure difficulties this train has no active line.\n"
        "Build a new established line to re-establish, or destroy the train.";
    float bodyBottom = modalY + btnBarTop - 10.0f;
    DrawWrappedText(bodyStr, innerX + 8.0f, innerY + 8.0f,
                    innerW - 16.0f, bodyBottom,
                    bodyFontSize, (Color){220, 240, 255, 255});

    // Buttons
    Vector2 mousePos    = CustomGetMousePosition();
    bool destroyHover   = CheckCollisionPointRec(mousePos, destroyBtn);
    bool cancelHover    = CheckCollisionPointRec(mousePos, cancelBtn);
    Texture2D confirmTx = (destroyHover && g_texModalConfirmSelected.id != 0)
        ? g_texModalConfirmSelected : g_texModalConfirmNotSelected;
    Texture2D cancelTx  = (cancelHover  && g_texModalConfirmSelected.id != 0)
        ? g_texModalConfirmSelected : g_texModalConfirmNotSelected;

    if (confirmTx.id != 0) {
        DrawTexturePro(confirmTx, (Rectangle){0,0,(float)confirmTx.width,(float)confirmTx.height},
                       destroyBtn, {0,0}, 0.0f, WHITE);
    } else {
        DrawRectangleRec(destroyBtn, destroyHover ? (Color){160,40,40,255} : (Color){120,30,30,255});
    }
    if (cancelTx.id != 0) {
        DrawTexturePro(cancelTx, (Rectangle){0,0,(float)cancelTx.width,(float)cancelTx.height},
                       cancelBtn, {0,0}, 0.0f, WHITE);
    } else {
        DrawRectangleRec(cancelBtn, cancelHover ? (Color){60,120,80,255} : (Color){45,90,60,255});
    }

    const char* destroyLabel = "DESTROY TRAIN";
    const char* noLabel      = "CANCEL";
    float dW = MeasureTextEx(gameFont, destroyLabel, bodyFontSize, 0.0f).x;
    float nW = MeasureTextEx(gameFont, noLabel,      bodyFontSize, 0.0f).x;
    DrawTextEx(gameFont, destroyLabel,
        (Vector2){destroyBtn.x + (destroyBtn.width - dW) / 2.0f,
                  destroyBtn.y + (btnH - bodyFontSize) / 2.0f - 4.0f},
        bodyFontSize, 0.0f, WHITE);
    DrawTextEx(gameFont, noLabel,
        (Vector2){cancelBtn.x  + (cancelBtn.width  - nW) / 2.0f,
                  cancelBtn.y  + (btnH - bodyFontSize) / 2.0f - 4.0f},
        bodyFontSize, 0.0f, WHITE);

    if (modal.framesOpen >= 2 && RawIsMouseButtonPressed(MOUSE_BUTTON_LEFT)) {
        if (destroyHover) modal.confirmClicked = true;
        else if (cancelHover) modal.cancelClicked = true;
    }
}
