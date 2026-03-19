#pragma once

#include "raylib.h"
#include <vector>

struct SpotlightRecord
{
    Vector3 position;
    Vector3 direction;
    float cutoff;
    float intensity;
};

struct GalleonPart
{
    Mesh mesh;
    Material material;
};

struct GalleonAsset
{
    std::vector<GalleonPart> parts;
    BoundingBox localBounds;
};

Shader CreateSpotlightShader();
void ApplySpotlights(Shader shader, const std::vector<SpotlightRecord> &lights);
std::vector<SpotlightRecord> GetDefaultGalleonSpotlights();

GalleonAsset CreateGalleonAsset(Shader shader);
void DestroyGalleonAsset(GalleonAsset &asset);
void DrawGalleonFleetInstanced(const GalleonAsset &asset, const std::vector<Matrix> &shipTransforms);
