#pragma once

#include "raylib.h"
#include <vector>

struct HexCell
{
    int q;
    int r;
    Vector3 center;
};

struct HexGridAsset
{
    Mesh mesh;
    Material material;
    float radius;
    float hoverHeight;
    std::vector<HexCell> cells;
};

HexGridAsset CreateHexGridAsset(Shader shader, float radius, float thickness, float hoverHeight, int mapRadius, Color color);
void DestroyHexGridAsset(HexGridAsset &asset);
void DrawHexGridInstanced(const HexGridAsset &asset, const std::vector<Matrix> &tileTransforms);
std::vector<Matrix> BuildHexTileTransforms(const HexGridAsset &asset);
int FindClosestHexCell(const HexGridAsset &asset, Vector3 point, float maxDistance);
