#include "hex_grid.h"
#include "raymath.h"
#include <array>
#include <algorithm>
#include <cmath>
#include <vector>

namespace
{
struct MeshBuilder
{
    std::vector<float> vertices;
    std::vector<float> normals;
    std::vector<float> texcoords;

    void AddVertex(Vector3 position, Vector3 normal)
    {
        vertices.push_back(position.x);
        vertices.push_back(position.y);
        vertices.push_back(position.z);

        normals.push_back(normal.x);
        normals.push_back(normal.y);
        normals.push_back(normal.z);

        texcoords.push_back(0.0f);
        texcoords.push_back(0.0f);
    }

    void AddTriangle(Vector3 a, Vector3 b, Vector3 c)
    {
        const Vector3 normal = Vector3Normalize(Vector3CrossProduct(Vector3Subtract(b, a), Vector3Subtract(c, a)));
        AddVertex(a, normal);
        AddVertex(b, normal);
        AddVertex(c, normal);
    }

    void AddQuad(Vector3 a, Vector3 b, Vector3 c, Vector3 d)
    {
        AddTriangle(a, b, c);
        AddTriangle(a, c, d);
    }

    Mesh Build() const
    {
        Mesh mesh = { 0 };
        mesh.vertexCount = (int)(vertices.size() / 3);
        mesh.triangleCount = mesh.vertexCount / 3;
        mesh.vertices = (float *)MemAlloc(vertices.size() * sizeof(float));
        mesh.normals = (float *)MemAlloc(normals.size() * sizeof(float));
        mesh.texcoords = (float *)MemAlloc(texcoords.size() * sizeof(float));
        std::copy(vertices.begin(), vertices.end(), mesh.vertices);
        std::copy(normals.begin(), normals.end(), mesh.normals);
        std::copy(texcoords.begin(), texcoords.end(), mesh.texcoords);
        UploadMesh(&mesh, false);
        return mesh;
    }
};

Material MakeMaterial(Shader shader, Color color)
{
    Material material = LoadMaterialDefault();
    material.shader = shader;
    material.maps[MATERIAL_MAP_DIFFUSE].color = color;
    return material;
}

Mesh CreateHexPrismMesh(float radius, float thickness)
{
    MeshBuilder builder;
    std::array<Vector3, 6> top = { 0 };
    std::array<Vector3, 6> bottom = { 0 };
    const float topY = thickness * 0.5f;
    const float bottomY = -thickness * 0.5f;

    for (int i = 0; i < 6; ++i)
    {
        const float angle = DEG2RAD * (60.0f * i - 30.0f);
        const float x = std::cos(angle) * radius;
        const float z = std::sin(angle) * radius;
        top[i] = { x, topY, z };
        bottom[i] = { x, bottomY, z };
    }

    for (int i = 1; i < 5; ++i)
    {
        builder.AddTriangle(top[0], top[i], top[i + 1]);
        builder.AddTriangle(bottom[0], bottom[i + 1], bottom[i]);
    }

    for (int i = 0; i < 6; ++i)
    {
        const int next = (i + 1) % 6;
        builder.AddQuad(bottom[i], bottom[next], top[next], top[i]);
    }

    return builder.Build();
}

Vector3 AxialToWorld(int q, int r, float radius, float y)
{
    const float x = radius * std::sqrt(3.0f) * ((float)q + (float)r * 0.5f);
    const float z = radius * 1.5f * (float)r;
    return { x, y, z };
}
}

HexGridAsset CreateHexGridAsset(Shader shader, float radius, float thickness, float hoverHeight, int mapRadius, Color color)
{
    HexGridAsset asset = { 0 };
    asset.mesh = CreateHexPrismMesh(radius, thickness);
    asset.material = MakeMaterial(shader, color);
    asset.radius = radius;
    asset.hoverHeight = hoverHeight;

    for (int q = -mapRadius; q <= mapRadius; ++q)
    {
        const int rMin = std::max(-mapRadius, -q - mapRadius);
        const int rMax = std::min(mapRadius, -q + mapRadius);
        for (int r = rMin; r <= rMax; ++r)
        {
            asset.cells.push_back(HexCell{ q, r, AxialToWorld(q, r, radius, hoverHeight) });
        }
    }

    return asset;
}

void DestroyHexGridAsset(HexGridAsset &asset)
{
    UnloadMaterial(asset.material);
    UnloadMesh(asset.mesh);
    asset.cells.clear();
}

void DrawHexGridInstanced(const HexGridAsset &asset, const std::vector<Matrix> &tileTransforms)
{
    if (tileTransforms.empty()) return;
    DrawMeshInstanced(asset.mesh, asset.material, tileTransforms.data(), (int)tileTransforms.size());
}

std::vector<Matrix> BuildHexTileTransforms(const HexGridAsset &asset)
{
    std::vector<Matrix> transforms;
    transforms.reserve(asset.cells.size());
    for (const HexCell &cell : asset.cells)
    {
        transforms.push_back(MatrixTranslate(cell.center.x, cell.center.y, cell.center.z));
    }
    return transforms;
}

int FindClosestHexCell(const HexGridAsset &asset, Vector3 point, float maxDistance)
{
    int closestIndex = -1;
    float closestDistance = maxDistance;

    for (int i = 0; i < (int)asset.cells.size(); ++i)
    {
        const Vector2 a = { asset.cells[i].center.x, asset.cells[i].center.z };
        const Vector2 b = { point.x, point.z };
        const float distance = Vector2Distance(a, b);
        if (distance < closestDistance)
        {
            closestDistance = distance;
            closestIndex = i;
        }
    }

    return closestIndex;
}
