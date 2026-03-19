// Depots can start at stations or factories, and can extend through connected depot chains.
static bool CanPlaceDepotAt(const Vector3& pos, const std::vector<PlacedPlatform>& platforms, float gridSize) {
    // Always allow a depot directly next to a station tile.
    if (HasAdjacentStation(pos, platforms, gridSize)) return true;

    // Also allow a depot directly adjacent to any factory footprint.
    for (const auto& f : g_placedFactories) {
        if (IsDepotAdjacentToFactoryFootprint(pos, f.position)) return true;
    }

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

// Check if there are at least 5 cargo materials within 10 grid spaces radius
static bool HasEnoughCargoInRadius(const Vector3& pos, 
                                    const std::vector<PlacedPlatform>& platforms,
                                    float gridSize,
                                    int requiredCargo) {
    float maxDist = gridSize * 8.0f; // 8 grid spaces radius
    int totalCargo = 0;

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
    float maxDist = gridSize * 8.0f; // 8 grid spaces radius

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

// Count how many adjacent platforms a given platform has (for connectivity).
// Uses same rules as GetAdjacentPositions: stations never connect to other stations;
// side-by-side track (different placement groups) does NOT count - junctions only when track CROSSES or CONNECTS.
int CountAdjacentPlatforms(const Vector3& position, const std::vector<PlacedPlatform>& platforms, float gridSize) {
    int selfIdx = FindPlatformIndexAtPos(position, platforms);
    if (selfIdx < 0 || selfIdx >= (int)platforms.size()) return 0;
    const PlacedPlatform* self = &platforms[selfIdx];
    if (self && self->isDepot) return 0;

    int count = 0;
    for (int i = 0; i < (int)platforms.size(); i++) {
        const auto& p = platforms[i];
        if (p.isDepot) continue;
        if (i == selfIdx) continue;
        if (!ArePlatformsConnectedForNetwork(selfIdx, i, platforms, gridSize)) continue;
        count++;
    }
    return count;
}

// Determine platform type based on neighbor count
// 0 = isolated, 1 = dead end, 2 = normal track, 3+ = junction/points (unless all neighbors are stations)
enum class PlatformType {
    Isolated,   // 0 neighbors
    DeadEnd,    // 1 neighbor (terminus)
    Track,      // 2 neighbors (normal track segment)
    Points      // 3+ neighbors (junction/switch)
};

// Forward declaration (defined below)
std::vector<Vector3> GetAdjacentPositions(const Vector3& position, const std::vector<PlacedPlatform>& platforms, float gridSize);

PlatformType GetPlatformType(const Vector3& position, const std::vector<PlacedPlatform>& platforms, float gridSize) {
    int neighbors = CountAdjacentPlatforms(position, platforms, gridSize);
    if (neighbors == 0) return PlatformType::Isolated;
    if (neighbors == 1) return PlatformType::DeadEnd;
    if (neighbors == 2) return PlatformType::Track;
    // 3+ neighbors: treat as junction (Points) only if at least one adjacent is not a station.
    // Stations placed next to stations form a straight station line, not a junction.
    const PlacedPlatform* self = FindPlatformAtPos(position, platforms);
    if (self && self->isStation) {
        std::vector<Vector3> adjacent = GetAdjacentPositions(position, platforms, gridSize);
        bool allNeighborsStations = true;
        for (const Vector3& adjPos : adjacent) {
            const PlacedPlatform* adj = FindPlatformAtPos(adjPos, platforms);
            if (!adj || !adj->isStation) {
                allNeighborsStations = false;
                break;
            }
        }
        if (allNeighborsStations)
            return PlatformType::Track;  // Station next to stations = no junction
    }
    return PlatformType::Points;
}

// Get all adjacent platform positions for a given platform.
// Stations never connect to other stations: from a station tile we only include track and same-station tiles.
// Connection by placement group: only connect if same group, or either platform is a junction, or both legacy (-1).
std::vector<Vector3> GetAdjacentPositions(const Vector3& position, const std::vector<PlacedPlatform>& platforms, float gridSize) {
    int selfIdx = FindPlatformIndexAtPos(position, platforms);
    if (selfIdx < 0 || selfIdx >= (int)platforms.size()) return {};
    const PlacedPlatform* self = &platforms[selfIdx];
    if (self && self->isDepot) return {};

    std::vector<Vector3> adjacent;
    for (int i = 0; i < (int)platforms.size(); i++) {
        const auto& p = platforms[i];
        if (p.isDepot) continue;
        if (i == selfIdx) continue; // Skip self
        if (!ArePlatformsConnectedForNetwork(selfIdx, i, platforms, gridSize)) continue;
        adjacent.push_back(p.position);
    }
    return adjacent;
}

// Get adjacent positions sorted clockwise around the platform (stable exit order)
std::vector<Vector3> GetSortedAdjacentPositions(const Vector3& position, const std::vector<PlacedPlatform>& platforms, float gridSize) {
    std::vector<Vector3> adjacent = GetAdjacentPositions(position, platforms, gridSize);
    std::array<bool, 4> hasDir = { false, false, false, false };
    std::array<Vector3, 4> closestByDir = {};
    std::array<float, 4> bestDistSq = {
        FLT_MAX, FLT_MAX, FLT_MAX, FLT_MAX
    };

    for (const auto& adj : adjacent) {
        float dx = adj.x - position.x;
        float dz = adj.z - position.z;
        int dir = 0;
        if (fabsf(dx) >= fabsf(dz)) dir = (dx < 0.0f) ? 0 : 2;
        else dir = (dz < 0.0f) ? 3 : 1;

        float distSq = dx * dx + dz * dz;
        if (!hasDir[dir] || distSq < bestDistSq[dir]) {
            hasDir[dir] = true;
            bestDistSq[dir] = distSq;
            closestByDir[dir] = adj;
        }
    }

    adjacent.clear();
    for (int dir = 0; dir < 4; dir++) {
        if (hasDir[dir]) adjacent.push_back(closestByDir[dir]);
    }

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

// 3D cross gate above a junction: four flat bars, outer half green (clear) or black (blocked).
// When isCrossingOfTwoLines: junction where two established lines cross - non-editable, draw plain white cross only.
// Floating about half a block above the junction; clickable when a train is selected (unless crossing).
void DrawPointsIndicator(const Vector3& position, const std::vector<PlacedPlatform>& platforms, float gridSize, float time, int selectedExitIndex, bool isEditable, bool isCrossingOfTwoLines = false) {
    std::vector<Vector3> adjacent = GetSortedAdjacentPositions(position, platforms, gridSize);
    if (adjacent.size() < 3) return;

    float topY = GetPlatformTopY(position.y, gridSize);
    float topThickness = gridSize * 0.1f;
    float barY = topY + topThickness / 2.0f + gridSize * 0.5f;  // Half a block above junction

    int pairIdx = selectedExitIndex;
    int numPairs = NumJunctionPairs((int)adjacent.size());
    if (pairIdx < 0 || pairIdx >= numPairs) {
        pairIdx = DefaultJunctionPairIndex(position, adjacent);
    }
    int activeI = -1, activeJ = -1;
    (void)PairIndexToIJ((int)adjacent.size(), pairIdx, activeI, activeJ);

    float barLen = gridSize * 0.48f;       // Total length of each arm
    float halfWidth = gridSize * 0.12f;   // Half-width of each bar
    float barHeight = gridSize * 0.06f;   // Slight thickness so it's visible from angle
    Color whiteCenter = { 245, 245, 245, 255 };
    Color greenGate = { 40, 220, 80, 255 };   // Clear to go both ways
    Color blackGate = { 28, 28, 28, 255 };    // Blocked
    Color gateColor = whiteCenter;

    Vector3 center = { position.x, barY, position.z };

    for (int exitIdx = 0; exitIdx < (int)adjacent.size(); exitIdx++) {
        Vector3 dir = Vector3Normalize(Vector3Subtract(adjacent[exitIdx], position));
        Vector3 perp = { -dir.z, 0.0f, dir.x };

        bool isOpen = (exitIdx == activeI || exitIdx == activeJ);

        // Inner half (center to midpoint): white
        Vector3 innerA = { center.x - perp.x * halfWidth, barY, center.z - perp.z * halfWidth };
        Vector3 innerB = { center.x + perp.x * halfWidth, barY, center.z + perp.z * halfWidth };
        Vector3 midA   = { center.x + dir.x * (barLen * 0.5f) - perp.x * halfWidth, barY, center.z + dir.z * (barLen * 0.5f) - perp.z * halfWidth };
        Vector3 midB   = { center.x + dir.x * (barLen * 0.5f) + perp.x * halfWidth, barY, center.z + dir.z * (barLen * 0.5f) + perp.z * halfWidth };
        // Outer half: white only when crossing of two lines (non-editable), else green/black
        Vector3 outerA = { center.x + dir.x * barLen - perp.x * halfWidth, barY, center.z + dir.z * barLen - perp.z * halfWidth };
        Vector3 outerB = { center.x + dir.x * barLen + perp.x * halfWidth, barY, center.z + dir.z * barLen + perp.z * halfWidth };

        DrawTriangle3D(innerA, innerB, midB, whiteCenter);
        DrawTriangle3D(innerA, midB, midA, whiteCenter);
        if (!isCrossingOfTwoLines) gateColor = isOpen ? greenGate : blackGate;
        else gateColor = whiteCenter;
        DrawTriangle3D(midA, midB, outerB, gateColor);
        DrawTriangle3D(midA, outerB, outerA, gateColor);
    }

    // Central square (white) so the cross reads clearly
    float c = gridSize * 0.08f;
    Vector3 c0 = { center.x - c, barY, center.z - c };
    Vector3 c1 = { center.x + c, barY, center.z - c };
    Vector3 c2 = { center.x + c, barY, center.z + c };
    Vector3 c3 = { center.x - c, barY, center.z + c };
    DrawTriangle3D(c0, c1, c2, whiteCenter);
    DrawTriangle3D(c0, c2, c3, whiteCenter);
}

// Returns true if the ray hits the junction cross (flat bars) at the given position.
// Used to allow clicking the floating cross to change gates when a train is selected.
bool RayHitJunctionCross(const Ray& ray, const Vector3& position, const std::vector<PlacedPlatform>& platforms, float gridSize) {
    std::vector<Vector3> adjacent = GetSortedAdjacentPositions(position, platforms, gridSize);
    if (adjacent.size() < 3) return false;

    float topY = GetPlatformTopY(position.y, gridSize);
    float topThickness = gridSize * 0.1f;
    float barY = topY + topThickness / 2.0f + gridSize * 0.5f;

    if (fabsf(ray.direction.y) < 0.0001f) return false;
    float t = (barY - ray.position.y) / ray.direction.y;
    if (t <= 0.0f) return false;
    Vector3 hit = Vector3Add(ray.position, Vector3Scale(ray.direction, t));

    float barLen = gridSize * 0.48f;
    float halfWidth = gridSize * 0.14f;  // Slightly larger for easier click

    float dx = hit.x - position.x;
    float dz = hit.z - position.z;

    for (const auto& adj : adjacent) {
        Vector3 dir = Vector3Normalize(Vector3Subtract(adj, position));
        Vector3 perp = { -dir.z, 0.0f, dir.x };
        // Project hit onto bar axis (dir)
        float along = dx * dir.x + dz * dir.z;
        float across = dx * perp.x + dz * perp.z;
        if (along >= -halfWidth * 0.5f && along <= barLen + halfWidth * 0.5f && fabsf(across) <= halfWidth) {
            return true;
        }
    }
    return false;
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
        
        // Find adjacent platforms (stations never connect to other stations)
        for (size_t i = 0; i < platforms.size(); i++) {
            if (platforms[i].isDepot) continue;
            if (!ArePlatformsConnectedForNetwork(currentIdx, (int)i, platforms, gridSize)) continue;
            if (!visited[i]) {
                visited[i] = true;
                queue.push_back(i);
            }
        }
    }
    
    return connected;
}

// Like FindConnectedPlatforms but only traverses platforms whose index is in linePlatformIndices.
// Used at crossroads: trains stay on their established line instead of treating it as a junction.
// Seeds BFS from the first platform in the line (not from startPos) so we always get the FULL
// connected component of the line - trains must travel the entire line, not just a segment.
static std::vector<Vector3> FindConnectedPlatformsForLine(const Vector3& startPos, const std::vector<PlacedPlatform>& platforms, float gridSize, const std::set<int>& linePlatformIndices) {
    if (linePlatformIndices.empty()) return FindConnectedPlatforms(startPos, platforms, gridSize);
    DebugLogFormat("JUNC_DEBUG: FindConnectedPlatformsForLine start=(%.0f,%.0f) linePlatformIndices.size=%d totalPlatforms=%d",
        startPos.x, startPos.z, (int)linePlatformIndices.size(), (int)platforms.size());
    // Log junction counts for context
    int juncCount = 0;
    for (int idx : linePlatformIndices) {
        if (idx >= 0 && idx < (int)platforms.size() && platforms[idx].isJunction) juncCount++;
    }
    DebugLogFormat("JUNC_DEBUG:   linePlatformIndices has %d junction nodes, %d non-junction nodes",
        juncCount, (int)linePlatformIndices.size() - juncCount);

    std::vector<Vector3> connected;
    std::vector<bool> visited(platforms.size(), false);
    std::vector<int> queue;
    queue.reserve(platforms.size());
    size_t queueHead = 0;

    // Seed BFS from the platform in this line that's closest to the requested start position.
    // This prevents trains from snapping to an unrelated disconnected segment when a line has
    // visual crossings/ownership splits after NO CONTINUE flows.
    int startIdx = -1;
    float bestDist = 1e30f;
    for (int idx : linePlatformIndices) {
        if (idx < 0 || idx >= (int)platforms.size()) continue;
        if (platforms[idx].isDepot) continue;
        float d = Vector3Distance(startPos, platforms[idx].position);
        if (d < bestDist) {
            bestDist = d;
            startIdx = idx;
        }
    }

    if (startIdx < 0) return connected;

    queue.push_back(startIdx);
    visited[startIdx] = true;

    while (queueHead < queue.size()) {
        int currentIdx = queue[queueHead++];
        connected.push_back(platforms[currentIdx].position);
        DebugLogFormat("JUNC_DEBUG:   BFS visiting pi=%d pos=(%.0f,%.0f) isJunc=%d isStn=%d",
            currentIdx, platforms[currentIdx].position.x, platforms[currentIdx].position.z,
            (int)platforms[currentIdx].isJunction, (int)platforms[currentIdx].isStation);

        for (size_t i = 0; i < platforms.size(); i++) {
            if (platforms[i].isDepot) continue;
            // Junction nodes are shared infrastructure: any line's train can pass through them.
            // Only skip non-junction platforms that don't belong to this line.
            bool inLineSet = (linePlatformIndices.find((int)i) != linePlatformIndices.end());
            bool isJunc = platforms[i].isJunction;
            if (!inLineSet && !isJunc) continue;
            if (!ArePlatformsConnectedForNetwork(currentIdx, (int)i, platforms, gridSize)) continue;
            if (!visited[i]) {
                visited[i] = true;
                if (!inLineSet && isJunc) {
                    DebugLogFormat("JUNC_DEBUG:   BFS including junction pi=%d pos=(%.0f,%.0f) via bypass (not in linePlatformIndices)",
                        (int)i, platforms[i].position.x, platforms[i].position.z);
                }
                queue.push_back((int)i);
            }
        }
    }
    DebugLogFormat("JUNC_DEBUG: FindConnectedPlatformsForLine result: connected.size=%d", (int)connected.size());
    return connected;
}

// Build a path through connected platforms using a simple pathfinding algorithm
// Tries to create a continuous path from one end to the other
// If train is provided, uses its junction settings to determine path through junctions
// If linePlatformIndices is non-null and non-empty, path is restricted to that line only (trains stick to their line at crossroads)
std::vector<Vector3> BuildPlatformPath(const Vector3& startPos, const std::vector<PlacedPlatform>& platforms, float gridSize, const PlacedTrain* train = nullptr, const std::set<int>* linePlatformIndices = nullptr) {
    std::vector<Vector3> connected = (linePlatformIndices && !linePlatformIndices->empty())
        ? FindConnectedPlatformsForLine(startPos, platforms, gridSize, *linePlatformIndices)
        : FindConnectedPlatforms(startPos, platforms, gridSize);
    
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

    // When line-restricted: use ArePlatformsAdjacent within connected (matches BFS). The placement-group
    // filter in GetAdjacentPositions can block corners where track was placed in separate strokes.
    auto getNeighborsInConnected = [&](const Vector3& pos) -> std::vector<Vector3> {
        std::vector<Vector3> neighbors;
        if (linePlatformIndices && !linePlatformIndices->empty()) {
            int posIdx = FindPlatformIndexAtPos(pos, platforms);
            for (const auto& c : connected) {
                if (Vector3Distance(pos, c) < 0.1f) continue; // skip self
                int cIdx = FindPlatformIndexAtPos(c, platforms);
                if (posIdx >= 0 && cIdx >= 0) {
                    if (ArePlatformsConnectedForNetwork(posIdx, cIdx, platforms, gridSize)) neighbors.push_back(c);
                } else if (ArePlatformsAdjacent(pos, c, gridSize)) {
                    neighbors.push_back(c);
                }
            }
            std::sort(neighbors.begin(), neighbors.end(), [&](const Vector3& a, const Vector3& b) {
                float angleA = atan2f(a.x - pos.x, a.z - pos.z);
                float angleB = atan2f(b.x - pos.x, b.z - pos.z);
                return angleA < angleB;
            });
        } else {
            std::vector<Vector3> all = GetSortedAdjacentPositions(pos, platforms, gridSize);
            for (const auto& n : all) {
                if (inConnected(n)) neighbors.push_back(n);
            }
        }
        return neighbors;
    };

    // Precompute degrees in this connected component
    std::vector<int> degree(connected.size(), 0);
    for (int i = 0; i < (int)connected.size(); i++) {
        int idxI = FindPlatformIndexAtPos(connected[i], platforms);
        for (int j = 0; j < (int)connected.size(); j++) {
            if (i == j) continue;
            int idxJ = FindPlatformIndexAtPos(connected[j], platforms);
            if (linePlatformIndices && !linePlatformIndices->empty() && idxI >= 0 && idxJ >= 0) {
                if (ArePlatformsConnectedForNetwork(idxI, idxJ, platforms, gridSize)) degree[i]++;
            } else {
                if (ArePlatformsAdjacent(connected[i], connected[j], gridSize)) degree[i]++;
            }
        }
    }
    bool hasEndpoint = false;
    std::vector<int> endpointIndices;
    for (int i = 0; i < (int)connected.size(); i++) {
        if (degree[i] == 1) { hasEndpoint = true; endpointIndices.push_back(i); }
    }

    // For line-restricted paths: try every endpoint as start and keep the LONGEST path.
    // This ensures trains travel the full line (e.g. longest span of a T-shaped line).
    // For non-line paths: use one endpoint or closest to startPos.
    auto doWalk = [&](int startIdx) -> std::vector<Vector3> {

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
        std::vector<Vector3> neighbors = getNeighborsInConnected(cur);
        if (neighbors.empty()) return prevPos; // no move possible

        // Endpoint stop handled by caller (we need neighbors list for that check)
        if (neighbors.size() == 1) return neighbors[0];

        // Junction (degree 3+): apply per-train switch pair settings when they resolve
        // inside the current neighbor set. When a line-restricted train reaches a shared
        // crossroad, `neighbors` already contains only that line's legal exits, so honoring
        // the pair here cannot route the train off-line.
        if (neighbors.size() >= 3) {
            int pairIdx = -1;
            if (train != nullptr) pairIdx = train->GetJunctionSetting(cur.x, cur.z, &neighbors);
            int numPairs = NumJunctionPairs((int)neighbors.size());

            if (pairIdx >= 0 && pairIdx < numPairs) {
                int i = -1, j = -1;
                if (PairIndexToIJ((int)neighbors.size(), pairIdx, i, j)) {
                    // No incoming direction yet (start node): just pick one side of the active pair.
                    if (isSentinelPrev(prevPos)) return neighbors[i];

                    // If we arrived from one side of the active pair, we must exit via the other side.
                    if (samePos(prevPos, neighbors[i])) return neighbors[j];
                    if (samePos(prevPos, neighbors[j])) return neighbors[i];

                    // Arrived from a leg that is not part of the active pair. For unrestricted routing
                    // this is a dead end under the current switch state; for line-restricted routing,
                    // fall through to the straight-through heuristic below.
                    if (!(linePlatformIndices && !linePlatformIndices->empty())) {
                        return prevPos;
                    }
                }
            } else if (!(linePlatformIndices && !linePlatformIndices->empty())) {
                pairIdx = DefaultJunctionPairIndex(cur, neighbors);
                int i = -1, j = -1;
                if (PairIndexToIJ((int)neighbors.size(), pairIdx, i, j)) {
                    if (isSentinelPrev(prevPos)) return neighbors[i];
                    if (samePos(prevPos, neighbors[i])) return neighbors[j];
                    if (samePos(prevPos, neighbors[j])) return neighbors[i];
                    return prevPos;
                }
            }
        }

        // For line-restricted routing through visual crossroads / mixed-color junctions,
        // prefer the straight-through continuation on this line rather than arbitrary angle order.
        if (neighbors.size() >= 3 && (linePlatformIndices && !linePlatformIndices->empty()) && !isSentinelPrev(prevPos)) {
            Vector3 inDir = Vector3Normalize(Vector3Subtract(cur, prevPos));
            float bestDot = -2.0f;
            int bestIdx = -1;
            DebugLogFormat("JUNC_DEBUG: chooseNext line-restricted junction at (%.0f,%.0f) from prev=(%.0f,%.0f) neighbors=%d",
                cur.x, cur.z, prevPos.x, prevPos.z, (int)neighbors.size());
            for (int ni = 0; ni < (int)neighbors.size(); ni++) {
                const Vector3& n = neighbors[ni];
                if (samePos(n, prevPos)) continue; // no U-turn
                Vector3 outDir = Vector3Normalize(Vector3Subtract(n, cur));
                float d = Vector3DotProduct(inDir, outDir); // 1 = straight, -1 = reverse
                DebugLogFormat("JUNC_DEBUG:   neighbor[%d]=(%.0f,%.0f) dot=%.2f", ni, n.x, n.z, d);
                if (d > bestDot) {
                    bestDot = d;
                    bestIdx = ni;
                }
            }
            if (bestIdx >= 0) {
                DebugLogFormat("JUNC_DEBUG:   -> chose neighbor[%d]=(%.0f,%.0f) dot=%.2f",
                    bestIdx, neighbors[bestIdx].x, neighbors[bestIdx].z, bestDot);
                return neighbors[bestIdx];
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
        std::vector<Vector3> neighbors = getNeighborsInConnected(current);

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
    }; // end doWalk

    std::vector<Vector3> path;
    if (linePlatformIndices && !linePlatformIndices->empty() && hasEndpoint && endpointIndices.size() >= 2) {
        // For line-restricted routing, compute the route between the farthest endpoint pair.
        // This avoids greedy branch choices at visual crossroads and traverses the full segment.
        std::vector<std::vector<int>> adjIdx(connected.size());
        for (int i = 0; i < (int)connected.size(); i++) {
            int idxI = FindPlatformIndexAtPos(connected[i], platforms);
            for (int j = 0; j < (int)connected.size(); j++) {
                if (i == j) continue;
                int idxJ = FindPlatformIndexAtPos(connected[j], platforms);
                if (idxI >= 0 && idxJ >= 0) {
                    if (ArePlatformsConnectedForNetwork(idxI, idxJ, platforms, gridSize))
                        adjIdx[i].push_back(j);
                } else if (ArePlatformsAdjacent(connected[i], connected[j], gridSize)) {
                    adjIdx[i].push_back(j);
                }
            }
        }

        int bestDist = -1;
        std::vector<int> bestIdxPath;
        for (int src : endpointIndices) {
            std::vector<int> dist(connected.size(), -1);
            std::vector<int> parent(connected.size(), -1);
            std::vector<int> q;
            q.reserve(connected.size());
            size_t qh = 0;
            q.push_back(src);
            dist[src] = 0;
            while (qh < q.size()) {
                int u = q[qh++];
                for (int v : adjIdx[u]) {
                    if (dist[v] >= 0) continue;
                    dist[v] = dist[u] + 1;
                    parent[v] = u;
                    q.push_back(v);
                }
            }

            for (int dst : endpointIndices) {
                if (dst == src) continue;
                if (dst < 0 || dst >= (int)dist.size()) continue;
                if (dist[dst] < 0) continue;
                if (dist[dst] <= bestDist) continue;
                bestDist = dist[dst];
                std::vector<int> idxPath;
                int cur = dst;
                while (cur >= 0) {
                    idxPath.push_back(cur);
                    if (cur == src) break;
                    cur = parent[cur];
                }
                std::reverse(idxPath.begin(), idxPath.end());
                bestIdxPath = std::move(idxPath);
            }
        }

        if (!bestIdxPath.empty()) {
            path.reserve(bestIdxPath.size());
            for (int idx : bestIdxPath) path.push_back(connected[idx]);
        } else {
            // Fallback to previous walk strategy if graph search found nothing.
            size_t bestLen = 0;
            for (int epIdx : endpointIndices) {
                std::vector<Vector3> candidate = doWalk(epIdx);
                if (candidate.size() > bestLen) {
                    bestLen = candidate.size();
                    path = std::move(candidate);
                }
            }
        }
    } else {
        int startIdx = -1;
        if (hasEndpoint && !endpointIndices.empty()) startIdx = endpointIndices[0];
        if (startIdx == -1) startIdx = findClosestIdx(startPos);
        path = doWalk(startIdx);
    }

    return path;
}

static bool RebuildTrainPath(PlacedTrain& train, const std::vector<PlacedPlatform>& platforms, float gridSize) {
    if (platforms.size() < 4) return false;

    // Build a new path starting from wherever the train currently is (projected to y=0 for platform lookup)
    // Restrict to train's line at crossroads - trains stick to their established line
    const std::set<int>* lineFilter = nullptr;
    if (train.lineId >= 0) {
        for (size_t li = 0; li < g_lines.size(); li++) {
            if (g_lines[li].id == train.lineId) {
                lineFilter = &g_lines[li].platformIndices;
                break;
            }
        }
    }
    Vector3 startPos = { train.position.x, 0.0f, train.position.z };
    DebugLogFormat("JUNC_DEBUG: RebuildTrainPath id=%d lineId=%d lineFilter=%s filterSize=%d startPos=(%.0f,%.0f)",
        train.id, train.lineId,
        lineFilter ? "YES" : "NO",
        lineFilter ? (int)lineFilter->size() : 0,
        startPos.x, startPos.z);
    std::vector<Vector3> newPath = BuildPlatformPath(startPos, platforms, gridSize, &train, lineFilter);
    DebugLogFormat("JUNC_DEBUG: RebuildTrainPath id=%d -> newPath.size=%d (need>=4)", train.id, (int)newPath.size());
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
    DebugLogFormat("TRAIN_DEBUG: RebuildTrainPath train id=%d pathPoints=%d pathLen=%.1f progress=%.1f dir=%.0f",
        train.id, (int)train.path.size(), train.pathLength, train.pathProgress, train.direction);
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

// Convert screen position (pixels) to world position (x, 0, z) when in map mode.
// Uses current g_mapCamera (offset, zoom, target). Map Y axis = -world Z.
static inline Vector3 MapScreenToWorld(Vector2 screenPos) {
    float mapX = (screenPos.x - g_mapCamera.offset.x) / g_mapCamera.zoom + g_mapCamera.target.x;
    float mapY = (screenPos.y - g_mapCamera.offset.y) / g_mapCamera.zoom + g_mapCamera.target.y;
    return { mapX, 0.0f, -mapY };
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

// Draw a thick line segment (quad) in 2D map space
static void DrawThickLineMap(Vector2 a, Vector2 b, float halfThick, Color c) {
    Vector2 d = { b.x - a.x, b.y - a.y };
    float len = sqrtf(d.x*d.x + d.y*d.y);
    if (len < 0.0001f) return;
    d.x /= len; d.y /= len;
    Vector2 perp = { -d.y, d.x };
    Vector2 p0 = { a.x + perp.x * halfThick, a.y + perp.y * halfThick };
    Vector2 p1 = { a.x - perp.x * halfThick, a.y - perp.y * halfThick };
    Vector2 p2 = { b.x - perp.x * halfThick, b.y - perp.y * halfThick };
    Vector2 p3 = { b.x + perp.x * halfThick, b.y + perp.y * halfThick };
    DrawTriangle(p0, p1, p2, c);
    DrawTriangle(p0, p2, p3, c);
}

// Draw junction "through" direction on the 2D map: chunky cross with two thick arms toward the active exit pair.
// If trainIndex >= 0, use that train's junction setting; otherwise use default pair (dim).
void DrawJunctionOnMap(const Vector3& position, const std::vector<PlacedPlatform>& platforms, float gridSize, int trainIndex, float time) {
    std::vector<Vector3> adjacent = GetSortedAdjacentPositions(position, platforms, gridSize);
    if (adjacent.size() < 3) return;
    
    int pairIdx = -1;
    bool isEditable = (trainIndex >= 0 && trainIndex < (int)g_placedTrains.size());
    if (isEditable) {
        pairIdx = g_placedTrains[trainIndex].GetJunctionSetting(position.x, position.z, &adjacent);
    }
    int numPairs = NumJunctionPairs((int)adjacent.size());
    if (pairIdx < 0 || pairIdx >= numPairs) {
        pairIdx = DefaultJunctionPairIndex(position, adjacent);
    }
    
    int activeI = -1, activeJ = -1;
    if (!PairIndexToIJ((int)adjacent.size(), pairIdx, activeI, activeJ)) return;
    
    Vector2 centerMap = WorldToMap(position);
    float halfLen = gridSize * 0.62f;   // Arm length (slightly longer)
    float halfThick = gridSize * 0.14f; // Chunky arm thickness
    float centerHalf = gridSize * 0.22f; // Chunky center cross size
    Color lineColor = isEditable ? (Color){ 0, 255, 100, 240 } : (Color){ 180, 160, 80, 160 };
    if (isEditable) {
        float pulse = (sinf(time * 3.0f) + 1.0f) / 2.0f;
        lineColor.a = (unsigned char)(200 + pulse * 55);
    }
    
    for (int idx : { activeI, activeJ }) {
        Vector3 adj = adjacent[idx];
        Vector3 dir = Vector3Normalize(Vector3Subtract(adj, position));
        Vector2 dirMap = { dir.x, -dir.z };
        float len = sqrtf(dirMap.x*dirMap.x + dirMap.y*dirMap.y);
        if (len < 0.0001f) continue;
        dirMap.x /= len; dirMap.y /= len;
        Vector2 endMap = { centerMap.x + dirMap.x * halfLen, centerMap.y + dirMap.y * halfLen };
        DrawThickLineMap(centerMap, endMap, halfThick, lineColor);
    }
    // Chunky center cross (horizontal and vertical bars)
    DrawThickLineMap((Vector2){ centerMap.x - centerHalf, centerMap.y }, (Vector2){ centerMap.x + centerHalf, centerMap.y }, halfThick, lineColor);
    DrawThickLineMap((Vector2){ centerMap.x, centerMap.y - centerHalf }, (Vector2){ centerMap.x, centerMap.y + centerHalf }, halfThick, lineColor);
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

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
// CLUSTER GENERATION
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
// Fixed distribution: exactly 10 clusters. Deterministic with seed.
// 6 clusters, one per passenger train color. 10x10 footprint, 10 cubes each.

static const std::vector<ClusterType> g_clusterTypeList = {
    ClusterType::ClusterGreen, ClusterType::ClusterMagenta, ClusterType::ClusterCyan,
    ClusterType::ClusterOrange, ClusterType::ClusterRed, ClusterType::ClusterYellow
};

static const int CLUSTER_SIZE = 6;

// Check clearance: no occupied cell within 'gap' cells of the footprint
static bool HasClearance(int x, int y, int width, int height,
    const std::vector<std::vector<int>>& grid, int gap) {
    int minX = (x - gap > 0) ? x - gap : 0;
    int maxX = (x + CLUSTER_SIZE + gap - 1 < width) ? x + CLUSTER_SIZE + gap - 1 : width - 1;
    int minY = (y - gap > 0) ? y - gap : 0;
    int maxY = (y + CLUSTER_SIZE + gap - 1 < height) ? y + CLUSTER_SIZE + gap - 1 : height - 1;
    for (int cy = minY; cy <= maxY; cy++) {
        for (int cx = minX; cx <= maxX; cx++) {
            if (grid[cy][cx] >= 0) return false;
        }
    }
    return true;
}

// Cluster must touch the grid edge (coast placement)
static bool IsOnCoast(int x, int y, int width, int height) {
    return (x == 0 || x == width - CLUSTER_SIZE || y == 0 || y == height - CLUSTER_SIZE);
}

static void PlaceCluster(int x, int y, int clusterIndex, std::vector<std::vector<int>>& grid) {
    for (int dy = 0; dy < CLUSTER_SIZE; dy++) {
        for (int dx = 0; dx < CLUSTER_SIZE; dx++) {
            grid[y + dy][x + dx] = clusterIndex;
        }
    }
}

ClusterGenResult GenerateClusters(int width, int height, int seed) {
    ClusterGenResult result;
    result.grid.resize(height);
    for (int i = 0; i < height; i++)
        result.grid[i].resize(width, -1);

    std::mt19937 gen((unsigned)seed);

    // Build candidate positions along the 4 coast edges
    struct Candidate { int x; int y; };
    std::vector<Candidate> candidates;
    for (int y = 0; y <= height - CLUSTER_SIZE; y++) {
        candidates.push_back({0, y});                        // Left coast
        candidates.push_back({width - CLUSTER_SIZE, y});     // Right coast
    }
    for (int x = 1; x < width - CLUSTER_SIZE; x++) {
        candidates.push_back({x, 0});                        // Top coast
        candidates.push_back({x, height - CLUSTER_SIZE});    // Bottom coast
    }

    // Force yellow to corner at grid (34,34) â€” covers cells 34-39 on both axes
    int redIndex = -1;
    int yellowIndex = -1;
    for (size_t i = 0; i < g_clusterTypeList.size(); i++) {
        if (g_clusterTypeList[i] == ClusterType::ClusterRed) redIndex = (int)i;
        if (g_clusterTypeList[i] == ClusterType::ClusterYellow) yellowIndex = (int)i;
    }
    if (yellowIndex >= 0) {
        int yx = width - CLUSTER_SIZE;
        int yy = height - CLUSTER_SIZE;
        PlaceCluster(yx, yy, yellowIndex, result.grid);
        Cluster c;
        c.type = ClusterType::ClusterYellow;
        c.size = CLUSTER_SIZE;
        c.x = yx;
        c.y = yy;
        result.clusters.push_back(c);
        printf("  Yellow cluster forced to corner (%d, %d)\n", yx, yy);
    }

    // Place all remaining clusters (skip yellow and red)
    for (size_t i = 0; i < g_clusterTypeList.size(); i++) {
        if ((int)i == redIndex || (int)i == yellowIndex) continue;

        int gap = 3 + (int)(gen() % 3);
        std::shuffle(candidates.begin(), candidates.end(), gen);

        Cluster c;
        c.type = g_clusterTypeList[i];
        c.size = CLUSTER_SIZE;
        bool placed = false;

        for (const auto& cand : candidates) {
            if (!IsOnCoast(cand.x, cand.y, width, height)) continue;
            if (!HasClearance(cand.x, cand.y, width, height, result.grid, gap)) continue;

            PlaceCluster(cand.x, cand.y, (int)i, result.grid);
            c.x = cand.x;
            c.y = cand.y;
            result.clusters.push_back(c);
            placed = true;
            break;
        }
        if (!placed) {
            printf("  WARNING: Could not place cluster %zu (type=%d) with gap=%d\n",
                i, (int)g_clusterTypeList[i], gap);
        }
    }

    // Place red in whichever corner is still empty
    if (redIndex >= 0) {
        Candidate corners[4] = {
            {0, 0},
            {width - CLUSTER_SIZE, 0},
            {0, height - CLUSTER_SIZE},
            {width - CLUSTER_SIZE, height - CLUSTER_SIZE}
        };
        Cluster c;
        c.type = ClusterType::ClusterRed;
        c.size = CLUSTER_SIZE;
        bool placed = false;
        for (int ci = 0; ci < 4; ci++) {
            int cx = corners[ci].x;
            int cy = corners[ci].y;
            if (HasClearance(cx, cy, width, height, result.grid, 3)) {
                PlaceCluster(cx, cy, redIndex, result.grid);
                c.x = cx;
                c.y = cy;
                result.clusters.push_back(c);
                placed = true;
                printf("  Red cluster placed in corner (%d, %d)\n", cx, cy);
                break;
            }
        }
        if (!placed) {
            printf("  WARNING: Could not place red cluster in any corner\n");
        }
    }

    return result;
}

static const int CLUSTER_GRID_W = 40;
static const int CLUSTER_GRID_H = 40;

static Color GetClusterColor(ClusterType t) {
    switch (t) {
        case ClusterType::CARGO: return (Color){ 139, 90, 43, 90 };   // Brown
        case ClusterType::ClusterGreen: return (Color){ 0, 200, 80, 90 };
        case ClusterType::ClusterMagenta: return (Color){ 255, 0, 255, 90 };
        case ClusterType::ClusterCyan: return (Color){ 0, 200, 255, 90 };
        case ClusterType::ClusterOrange: return (Color){ 255, 165, 0, 90 };
        case ClusterType::ClusterRed: return (Color){ 230, 41, 55, 90 };
        case ClusterType::ClusterYellow: return (Color){ 253, 249, 0, 90 };
        default: return (Color){ 128, 128, 128, 90 };
    }
}

static Color GetClusterBuildingColor(ClusterType t) {
    Color c = GetClusterColor(t);
    c.a = 220;
    return c;
}

static Color GetActivatedCargoPulseColor() {
    // Lighter brown than standard cargo color for clearer station pulse readability.
    return (Color){ 196, 140, 84, 220 };
}

// Add 10 cubes per cluster in a 10x10 area. Random cell picks; collisions stack up to 3.
// If a cell already has 3, re-roll. Deterministic with clusterSeed.
static void AddClusterBuildings(std::vector<Building>& buildings, const std::vector<Cluster>& clusters, int clusterSeed) {
    const float worldCellSize = (2.0f * g_gridExtent) / (float)CLUSTER_GRID_W;
    const float cubeSize = worldCellSize;
    const float cubeHeight = worldCellSize;
    const int CUBES_PER_CLUSTER = 10;
    const int MAX_STACK = 3;

    std::mt19937 rng((unsigned)(clusterSeed + 777));
    int totalAdded = 0;

    for (size_t ci = 0; ci < clusters.size(); ci++) {
        Color color = GetClusterBuildingColor(clusters[ci].type);

        // Track how many cubes are stacked at each cell in the 10x10 area
        int cellStack[CLUSTER_SIZE * CLUSTER_SIZE];
        memset(cellStack, 0, sizeof(cellStack));

        std::uniform_int_distribution<int> cellDist(0, CLUSTER_SIZE * CLUSTER_SIZE - 1);

        for (int placed = 0; placed < CUBES_PER_CLUSTER; ) {
            int cell = cellDist(rng);
            if (cellStack[cell] >= MAX_STACK) continue;  // Full, re-roll

            int col = cell % CLUSTER_SIZE;
            int row = cell / CLUSTER_SIZE;
            int gx = clusters[ci].x + col;
            int gy = clusters[ci].y + row;
            float wx = -g_gridExtent + ((float)gx + 0.5f) * worldCellSize;
            float wz = -g_gridExtent + ((float)gy + 0.5f) * worldCellSize;
            int level = cellStack[cell];

            Building b;
            b.position = { wx, cubeHeight * 0.5f + cubeHeight * (float)level, wz };
            b.size = { cubeSize, cubeHeight, cubeSize };
            b.color = color;
            buildings.push_back(b);

            cellStack[cell]++;
            totalAdded++;
            placed++;
        }
    }
    printf("  Added %d cluster cubes (%d clusters, %d per cluster)\n", totalAdded, (int)clusters.size(), CUBES_PER_CLUSTER);
    fflush(stdout);
}

static const char* ClusterTypeName(ClusterType t) {
    switch (t) {
        case ClusterType::CARGO: return "CARGO";
        case ClusterType::ClusterGreen: return "GREEN";
        case ClusterType::ClusterMagenta: return "MAGENTA";
        case ClusterType::ClusterCyan: return "CYAN";
        case ClusterType::ClusterOrange: return "ORANGE";
        case ClusterType::ClusterRed: return "RED";
        case ClusterType::ClusterYellow: return "YELLOW";
        default: return "UNKNOWN";
    }
}

// Convert cluster grid cell (cx, cy) to world position. Assumes grid spans -g_gridExtent..+g_gridExtent
static Vector3 ClusterCellToWorld(int cx, int cy, int gridWidth, int gridHeight) {
    float cellSize = (2.0f * g_gridExtent) / (float)(gridWidth > 0 ? gridWidth : 1);
    float wx = -g_gridExtent + ((float)cx + 0.5f) * cellSize;
    float wz = -g_gridExtent + ((float)cy + 0.5f) * cellSize;
    return { wx, 0.0f, wz };
}

// Place 10 buildings per cluster colour in the outer grey ring, near the coast edge closest to each cluster.
static void AddOuterRingBuildings(std::vector<Building>& buildings, const std::vector<Cluster>& clusters, int seed) {
    std::mt19937 gen((unsigned)seed + 9999);
    std::uniform_real_distribution<float> heightDist(4.0f, 18.0f);
    const float cubeSize = g_gridSpacing;
    const int buildingsPerCluster = 10;

    for (const auto& cl : clusters) {
        Color col = GetClusterBuildingColor(cl.type);
        Vector3 clWorld = ClusterCellToWorld(cl.x + cl.size / 2, cl.y + cl.size / 2, CLUSTER_GRID_W, CLUSTER_GRID_H);

        // Determine which coast edge this cluster is closest to and project outward
        float dLeft   = clWorld.x - (-g_gridExtent);
        float dRight  = g_gridExtent - clWorld.x;
        float dTop    = clWorld.z - (-g_gridExtent);
        float dBottom = g_gridExtent - clWorld.z;
        float dMin = std::min({dLeft, dRight, dTop, dBottom});

        // Direction to push buildings into the outer ring
        float dirX = 0.0f, dirZ = 0.0f;
        float edgeCoord = 0.0f;
        bool alongX = false;
        if (dMin == dLeft)       { dirX = -1.0f; edgeCoord = clWorld.z; alongX = false; }
        else if (dMin == dRight) { dirX =  1.0f; edgeCoord = clWorld.z; alongX = false; }
        else if (dMin == dTop)   { dirZ = -1.0f; edgeCoord = clWorld.x; alongX = true;  }
        else                     { dirZ =  1.0f; edgeCoord = clWorld.x; alongX = true;  }

        int placed = 0;
        int attempts = 0;
        while (placed < buildingsPerCluster && attempts < 200) {
            attempts++;
            float spread = ((float)(gen() % 100) - 50.0f) / 50.0f * g_gridSpacing * 8.0f;
            float depth  = g_gridExtent + g_gridSpacing + (float)(gen() % (int)((g_gridExtentOuter - g_gridExtent - g_gridSpacing * 2.0f) * 10.0f)) / 10.0f;
            float h = heightDist(gen);

            float wx, wz;
            if (alongX) {
                wx = edgeCoord + spread;
                wz = dirZ * depth;
            } else {
                wx = dirX * depth;
                wz = edgeCoord + spread;
            }
            wx = roundf(wx / g_gridSpacing) * g_gridSpacing + g_gridSpacing * 0.5f;
            wz = roundf(wz / g_gridSpacing) * g_gridSpacing + g_gridSpacing * 0.5f;

            if (fabsf(wx) <= g_gridExtent && fabsf(wz) <= g_gridExtent) continue;
            if (fabsf(wx) > g_gridExtentOuter - g_gridSpacing * 0.5f) continue;
            if (fabsf(wz) > g_gridExtentOuter - g_gridSpacing * 0.5f) continue;

            Building b;
            b.position = { wx, h / 2.0f, wz };
            b.size = { cubeSize, h, cubeSize };
            b.color = col;
            if (!overlapsWithAny(b, buildings)) {
                buildings.push_back(b);
                placed++;
            }
        }
    }
}

// Validation: count==6, no overlap, all in bounds, on coast, far from center, min 3-cell gap
static bool ValidateClusters(const ClusterGenResult& res, int width, int height) {
    if ((int)res.clusters.size() != (int)g_clusterTypeList.size()) return false;
    for (int i = 0; i < (int)res.clusters.size(); i++) {
        const Cluster& c = res.clusters[i];
        if (c.x < 0 || c.y < 0 || c.x + c.size > width || c.y + c.size > height) return false;
        if (!IsOnCoast(c.x, c.y, width, height)) return false;
        for (int j = i + 1; j < (int)res.clusters.size(); j++) {
            const Cluster& d = res.clusters[j];
            int ax0 = c.x, ax1 = c.x + c.size - 1;
            int ay0 = c.y, ay1 = c.y + c.size - 1;
            int bx0 = d.x, bx1 = d.x + d.size - 1;
            int by0 = d.y, by1 = d.y + d.size - 1;
            bool footprintOverlap = (ax0 <= bx1 && ax1 >= bx0 && ay0 <= by1 && ay1 >= by0);
            if (footprintOverlap) return false;
            // Minimum 3-cell gap between any pair
            int gap = 4;  // 3 empty cells = edges must be > 3 apart
            bool clearanceViolation = (ax1 + gap > bx0 && bx1 + gap > ax0 && ay1 + gap > by0 && by1 + gap > ay0);
            if (clearanceViolation) return false;
        }
    }
    return true;
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
                float height = heightDist(gen) * 1.1f;
                
                // Snap to grid: 1x1 buildings go to cell centers, multi-cell to intersections
                float x = (float)gridX;
                float z = (float)gridZ;
                if (sizeIndex == 0) {
                    x += gridSize * 0.5f;
                    z += gridSize * 0.5f;
                }
                
                building.position = { 
                    x, 
                    height / 2.0f, 
                    z 
                };
                building.size = { width, height, depth };
                building.color = (Color){ 255, 255, 255, 238 };
                
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
        float height = heightDist(gen) * 2.0f * 1.1f; // Taller buildings
        
        int gridX = ((gen() % 20 - 10) / 5) * 5;
        int gridZ = ((gen() % 20 - 10) / 5) * 5;
        float cx = (float)gridX;
        float cz = (float)gridZ;
        if (sizeIndex == 0) { cx += gridSize * 0.5f; cz += gridSize * 0.5f; }
        
        building.position = { 
            cx, 
            height / 2.0f, 
            cz 
        };
        building.size = { width, height, depth };
        building.color = (Color){ 255, 255, 255, 238 };
        
        // Only add if it doesn't overlap with existing buildings
        if (!overlapsWithAny(building, buildings)) {
            buildings.push_back(building);
            i++; // Only increment when successfully placed
        }
    }
    
    return buildings;
}

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
// DLL EXPORTS (for BBS embedded mode)
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

