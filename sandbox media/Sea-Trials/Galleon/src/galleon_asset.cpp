#include "galleon_asset.h"
#include "raymath.h"
#include <algorithm>
#include <array>
#include <cmath>
#include <vector>

namespace
{
constexpr int kMaxSpotlights = 16;
constexpr float kDefaultOpacity = 1.00f;
constexpr float kHeroOpacity = 1.00f;

const char *kSpotlightVertexShader = R"(
#version 330

in vec3 vertexPosition;
in vec2 vertexTexCoord;
in vec3 vertexNormal;

uniform mat4 mvp;
uniform mat4 matModel;
uniform mat4 matNormal;

out vec3 fragPosition;
out vec3 fragNormal;

void main()
{
    fragPosition = vec3(matModel * vec4(vertexPosition, 1.0));
    fragNormal = normalize((mat3(matNormal)) * vertexNormal);
    gl_Position = mvp * vec4(vertexPosition, 1.0);
}
)";

const char *kSpotlightFragmentShader = R"(
#version 330

#define MAX_SPOTLIGHTS 16

in vec3 fragPosition;
in vec3 fragNormal;

out vec4 finalColor;

uniform vec4 colDiffuse;
uniform int spotlightCount;
uniform vec3 lightPos[MAX_SPOTLIGHTS];
uniform vec3 lightDir[MAX_SPOTLIGHTS];
uniform float lightCutoff[MAX_SPOTLIGHTS];
uniform float lightIntensity[MAX_SPOTLIGHTS];

void main()
{
    vec3 normal = normalize(fragNormal);
    vec3 totalLight = vec3(0.16, 0.18, 0.20);

    for (int i = 0; i < spotlightCount; i++)
    {
        vec3 toLight = lightPos[i] - fragPosition;
        float distanceToLight = length(toLight);
        if (distanceToLight <= 0.0001) continue;

        vec3 lightVector = toLight / distanceToLight;
        vec3 coneVector = normalize(fragPosition - lightPos[i]);
        float coneDot = dot(normalize(lightDir[i]), coneVector);
        float coneFactor = smoothstep(lightCutoff[i], min(0.999, lightCutoff[i] + 0.08), coneDot);

        float diffuse = max(dot(normal, lightVector), 0.0);
        float attenuation = 1.0 / (1.0 + 0.06 * distanceToLight + 0.01 * distanceToLight * distanceToLight);
        totalLight += vec3(1.0) * diffuse * coneFactor * attenuation * lightIntensity[i];
    }

    finalColor = vec4(colDiffuse.rgb * totalLight, colDiffuse.a);
}
)";

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

Color WithOpacity(Color color, float opacity)
{
    color.a = (unsigned char)std::clamp((int)std::round(255.0f * opacity), 0, 255);
    return color;
}

Material MakeMaterial(Shader shader, Color color)
{
    Material material = LoadMaterialDefault();
    material.shader = shader;
    material.maps[MATERIAL_MAP_DIFFUSE].color = color;
    return material;
}

void AddBox(MeshBuilder &builder, Vector3 center, Vector3 size)
{
    const Vector3 half = Vector3Scale(size, 0.5f);

    const Vector3 p000 = Vector3Add(center, Vector3{ -half.x, -half.y, -half.z });
    const Vector3 p001 = Vector3Add(center, Vector3{ -half.x, -half.y, half.z });
    const Vector3 p010 = Vector3Add(center, Vector3{ -half.x, half.y, -half.z });
    const Vector3 p011 = Vector3Add(center, Vector3{ -half.x, half.y, half.z });
    const Vector3 p100 = Vector3Add(center, Vector3{ half.x, -half.y, -half.z });
    const Vector3 p101 = Vector3Add(center, Vector3{ half.x, -half.y, half.z });
    const Vector3 p110 = Vector3Add(center, Vector3{ half.x, half.y, -half.z });
    const Vector3 p111 = Vector3Add(center, Vector3{ half.x, half.y, half.z });

    builder.AddQuad(p010, p110, p111, p011);
    builder.AddQuad(p100, p000, p001, p101);
    builder.AddQuad(p000, p010, p011, p001);
    builder.AddQuad(p110, p100, p101, p111);
    builder.AddQuad(p001, p011, p111, p101);
    builder.AddQuad(p000, p100, p110, p010);
}

void AddTaperedBox(MeshBuilder &builder, Vector3 center, Vector3 sizeRear, Vector3 sizeFront)
{
    const Vector3 halfRear = Vector3Scale(sizeRear, 0.5f);
    const Vector3 halfFront = Vector3Scale(sizeFront, 0.5f);
    const float halfLen = (sizeRear.x + sizeFront.x) * 0.25f; // Simplified average length

    const Vector3 p000 = { center.x - halfLen, center.y - halfRear.y, center.z - halfRear.z };
    const Vector3 p001 = { center.x - halfLen, center.y - halfRear.y, center.z + halfRear.z };
    const Vector3 p010 = { center.x - halfLen, center.y + halfRear.y, center.z - halfRear.z };
    const Vector3 p011 = { center.x - halfLen, center.y + halfRear.y, center.z + halfRear.z };

    const Vector3 p100 = { center.x + halfLen, center.y - halfFront.y, center.z - halfFront.z };
    const Vector3 p101 = { center.x + halfLen, center.y - halfFront.y, center.z + halfFront.z };
    const Vector3 p110 = { center.x + halfLen, center.y + halfFront.y, center.z - halfFront.z };
    const Vector3 p111 = { center.x + halfLen, center.y + halfFront.y, center.z + halfFront.z };

    builder.AddQuad(p010, p110, p111, p011);
    builder.AddQuad(p100, p000, p001, p101);
    builder.AddQuad(p000, p010, p011, p001);
    builder.AddQuad(p110, p100, p101, p111);
    builder.AddQuad(p001, p011, p111, p101);
    builder.AddQuad(p000, p100, p110, p010);
}

void AddFrustum(MeshBuilder &builder, Vector3 center, Vector2 topXZ, Vector2 bottomXZ, float height)
{
    const float yTop = center.y + height * 0.5f;
    const float yBottom = center.y - height * 0.5f;

    const Vector3 topBackLeft = { center.x - topXZ.x * 0.5f, yTop, center.z - topXZ.y * 0.5f };
    const Vector3 topBackRight = { center.x - topXZ.x * 0.5f, yTop, center.z + topXZ.y * 0.5f };
    const Vector3 topFrontLeft = { center.x + topXZ.x * 0.5f, yTop, center.z - topXZ.y * 0.5f };
    const Vector3 topFrontRight = { center.x + topXZ.x * 0.5f, yTop, center.z + topXZ.y * 0.5f };

    const Vector3 bottomBackLeft = { center.x - bottomXZ.x * 0.5f, yBottom, center.z - bottomXZ.y * 0.5f };
    const Vector3 bottomBackRight = { center.x - bottomXZ.x * 0.5f, yBottom, center.z + bottomXZ.y * 0.5f };
    const Vector3 bottomFrontLeft = { center.x + bottomXZ.x * 0.5f, yBottom, center.z - bottomXZ.y * 0.5f };
    const Vector3 bottomFrontRight = { center.x + bottomXZ.x * 0.5f, yBottom, center.z + bottomXZ.y * 0.5f };

    builder.AddQuad(topBackLeft, topBackRight, topFrontRight, topFrontLeft);
    builder.AddQuad(bottomBackLeft, bottomFrontLeft, bottomFrontRight, bottomBackRight);
    builder.AddQuad(bottomBackLeft, bottomBackRight, topBackRight, topBackLeft);
    builder.AddQuad(topFrontLeft, topFrontRight, bottomFrontRight, bottomFrontLeft);
    builder.AddQuad(bottomBackLeft, topBackLeft, topFrontLeft, bottomFrontLeft);
    builder.AddQuad(bottomFrontRight, topFrontRight, topBackRight, bottomBackRight);
}

void AddBowWedge(MeshBuilder &builder, Vector3 center, float length, float height, float width)
{
    const float xRear = center.x - length * 0.5f;
    const float xTip = center.x + length * 0.5f;
    const float yBottom = center.y - height * 0.5f;
    const float yTop = center.y + height * 0.5f;
    const float zRear = width * 0.5f;

    const Vector3 tipBottom = { xTip, yBottom, 0.0f };
    const Vector3 tipTop = { xTip, yTop, 0.0f };
    const Vector3 rearBottomLeft = { xRear, yBottom, -zRear };
    const Vector3 rearBottomRight = { xRear, yBottom, zRear };
    const Vector3 rearTopLeft = { xRear, yTop, -zRear * 1.18f };
    const Vector3 rearTopRight = { xRear, yTop, zRear * 1.18f };

    builder.AddTriangle(tipBottom, rearBottomLeft, tipTop);
    builder.AddTriangle(tipBottom, tipTop, rearBottomRight);
    builder.AddTriangle(tipTop, rearTopLeft, rearTopRight);
    builder.AddTriangle(tipTop, rearTopRight, rearBottomRight);
    builder.AddTriangle(tipTop, rearBottomLeft, rearTopLeft);
    builder.AddQuad(rearBottomLeft, rearBottomRight, rearTopRight, rearTopLeft);
}

void AddPrismBarrel(
    MeshBuilder &builder,
    Vector3 start,
    Vector3 end,
    float startRadius,
    float endRadius,
    int sides)
{
    const Vector3 axis = Vector3Normalize(Vector3Subtract(end, start));
    const Vector3 up = (std::fabs(axis.y) < 0.95f) ? Vector3{ 0.0f, 1.0f, 0.0f } : Vector3{ 1.0f, 0.0f, 0.0f };
    const Vector3 sideA = Vector3Normalize(Vector3CrossProduct(axis, up));
    const Vector3 sideB = Vector3Normalize(Vector3CrossProduct(sideA, axis));

    std::vector<Vector3> startRing;
    std::vector<Vector3> endRing;
    startRing.reserve(sides);
    endRing.reserve(sides);

    for (int i = 0; i < sides; ++i)
    {
        const float angle = 2.0f * PI * ((float)i / (float)sides);
        const Vector3 radial = Vector3Add(
            Vector3Scale(sideA, std::cos(angle)),
            Vector3Scale(sideB, std::sin(angle))
        );
        startRing.push_back(Vector3Add(start, Vector3Scale(radial, startRadius)));
        endRing.push_back(Vector3Add(end, Vector3Scale(radial, endRadius)));
    }

    for (int i = 0; i < sides; ++i)
    {
        const int next = (i + 1) % sides;
        builder.AddQuad(startRing[i], startRing[next], endRing[next], endRing[i]);
        builder.AddTriangle(start, startRing[next], startRing[i]);
        builder.AddTriangle(end, endRing[i], endRing[next]);
    }
}

void AddBillowedSail(
    MeshBuilder &builder,
    float mastX,
    float topY,
    float bottomY,
    float topHalfSpan,
    float bottomHalfSpan,
    float bellyDepth,
    float thickness)
{
    const float upperMidY = topY - (topY - bottomY) * 0.32f;
    const float lowerMidY = topY - (topY - bottomY) * 0.68f;
    const float upperMidSpan = topHalfSpan + (bottomHalfSpan - topHalfSpan) * 0.35f;
    const float lowerMidSpan = topHalfSpan + (bottomHalfSpan - topHalfSpan) * 0.72f;
    const float upperMidDepth = bellyDepth * 0.78f;
    const float lowerMidDepth = bellyDepth * 0.92f;
    const float halfThickness = thickness * 0.5f;

    const Vector3 frontTopLeft = { mastX + halfThickness, topY, -topHalfSpan };
    const Vector3 frontTopRight = { mastX + halfThickness, topY, topHalfSpan };
    const Vector3 frontUpperLeft = { mastX + upperMidDepth + halfThickness, upperMidY, -upperMidSpan };
    const Vector3 frontUpperRight = { mastX + upperMidDepth + halfThickness, upperMidY, upperMidSpan };
    const Vector3 frontLowerLeft = { mastX + lowerMidDepth + halfThickness, lowerMidY, -lowerMidSpan };
    const Vector3 frontLowerRight = { mastX + lowerMidDepth + halfThickness, lowerMidY, lowerMidSpan };
    const Vector3 frontBottomLeft = { mastX + halfThickness, bottomY, -bottomHalfSpan };
    const Vector3 frontBottomRight = { mastX + halfThickness, bottomY, bottomHalfSpan };

    const Vector3 backTopLeft = { mastX - halfThickness, topY, -topHalfSpan };
    const Vector3 backTopRight = { mastX - halfThickness, topY, topHalfSpan };
    const Vector3 backUpperLeft = { mastX + upperMidDepth - halfThickness, upperMidY, -upperMidSpan };
    const Vector3 backUpperRight = { mastX + upperMidDepth - halfThickness, upperMidY, upperMidSpan };
    const Vector3 backLowerLeft = { mastX + lowerMidDepth - halfThickness, lowerMidY, -lowerMidSpan };
    const Vector3 backLowerRight = { mastX + lowerMidDepth - halfThickness, lowerMidY, lowerMidSpan };
    const Vector3 backBottomLeft = { mastX - halfThickness, bottomY, -bottomHalfSpan };
    const Vector3 backBottomRight = { mastX - halfThickness, bottomY, bottomHalfSpan };

    builder.AddQuad(frontTopLeft, frontTopRight, frontUpperRight, frontUpperLeft);
    builder.AddQuad(frontUpperLeft, frontUpperRight, frontLowerRight, frontLowerLeft);
    builder.AddQuad(frontLowerLeft, frontLowerRight, frontBottomRight, frontBottomLeft);

    builder.AddQuad(backTopRight, backTopLeft, backUpperLeft, backUpperRight);
    builder.AddQuad(backUpperRight, backUpperLeft, backLowerLeft, backLowerRight);
    builder.AddQuad(backLowerRight, backLowerLeft, backBottomLeft, backBottomRight);

    builder.AddQuad(frontTopLeft, backTopLeft, backTopRight, frontTopRight);
    builder.AddQuad(frontBottomLeft, frontBottomRight, backBottomRight, backBottomLeft);
    builder.AddQuad(frontTopLeft, frontUpperLeft, backUpperLeft, backTopLeft);
    builder.AddQuad(frontTopRight, backTopRight, backUpperRight, frontUpperRight);
    builder.AddQuad(frontUpperLeft, frontLowerLeft, backLowerLeft, backUpperLeft);
    builder.AddQuad(frontUpperRight, backUpperRight, backLowerRight, frontLowerRight);
    builder.AddQuad(frontLowerLeft, frontBottomLeft, backBottomLeft, backLowerLeft);
    builder.AddQuad(frontLowerRight, backLowerRight, backBottomRight, frontBottomRight);
}

void AddJibSail(MeshBuilder &builder)
{
    const float thickness = 0.10f;
    const Vector3 frontA = { 7.56f + thickness * 0.5f, 9.25f, 0.0f };
    const Vector3 frontB = { 11.75f + thickness * 0.5f, 6.2f, 0.0f };
    const Vector3 frontC = { 7.56f + thickness * 0.5f, 5.05f, 0.0f };

    const Vector3 backA = { 7.56f - thickness * 0.5f, 9.25f, 0.0f };
    const Vector3 backB = { 11.75f - thickness * 0.5f, 6.2f, 0.0f };
    const Vector3 backC = { 7.56f - thickness * 0.5f, 5.05f, 0.0f };

    builder.AddTriangle(frontA, frontB, frontC);
    builder.AddTriangle(backB, backA, backC);
    builder.AddQuad(frontA, backA, backB, frontB);
    builder.AddQuad(frontB, backB, backC, frontC);
    builder.AddQuad(frontC, backC, backA, frontA);
}

void AddGalleonPart(std::vector<GalleonPart> &parts, Mesh mesh, Shader shader, Color color)
{
    parts.push_back(GalleonPart{ mesh, MakeMaterial(shader, color) });
}
}

Shader CreateSpotlightShader()
{
    return LoadShaderFromMemory(kSpotlightVertexShader, kSpotlightFragmentShader);
}

void ApplySpotlights(Shader shader, const std::vector<SpotlightRecord> &lights)
{
    const int spotlightCountLoc = GetShaderLocation(shader, "spotlightCount");
    const int lightPosLoc = GetShaderLocation(shader, "lightPos[0]");
    const int lightDirLoc = GetShaderLocation(shader, "lightDir[0]");
    const int lightCutoffLoc = GetShaderLocation(shader, "lightCutoff[0]");
    const int lightIntensityLoc = GetShaderLocation(shader, "lightIntensity[0]");

    float lightPositions[kMaxSpotlights * 3] = { 0.0f };
    float lightDirections[kMaxSpotlights * 3] = { 0.0f };
    float lightCutoffs[kMaxSpotlights] = { 0.0f };
    float lightIntensities[kMaxSpotlights] = { 0.0f };

    const int activeCount = std::min((int)lights.size(), kMaxSpotlights);
    for (int i = 0; i < activeCount; ++i)
    {
        const int base = i * 3;
        lightPositions[base] = lights[i].position.x;
        lightPositions[base + 1] = lights[i].position.y;
        lightPositions[base + 2] = lights[i].position.z;
        lightDirections[base] = lights[i].direction.x;
        lightDirections[base + 1] = lights[i].direction.y;
        lightDirections[base + 2] = lights[i].direction.z;
        lightCutoffs[i] = lights[i].cutoff;
        lightIntensities[i] = lights[i].intensity;
    }

    SetShaderValue(shader, spotlightCountLoc, &activeCount, SHADER_UNIFORM_INT);
    SetShaderValueV(shader, lightPosLoc, lightPositions, SHADER_UNIFORM_VEC3, activeCount);
    SetShaderValueV(shader, lightDirLoc, lightDirections, SHADER_UNIFORM_VEC3, activeCount);
    SetShaderValueV(shader, lightCutoffLoc, lightCutoffs, SHADER_UNIFORM_FLOAT, activeCount);
    SetShaderValueV(shader, lightIntensityLoc, lightIntensities, SHADER_UNIFORM_FLOAT, activeCount);
}

std::vector<SpotlightRecord> GetDefaultGalleonSpotlights()
{
    return {
        { { -33.956f, 8.000f, -1.731f }, Vector3Normalize({ 0.9932f, -0.1053f, 0.0506f }), 0.89879f, 17.82f },
        { { -33.956f, 28.000f, -1.731f }, Vector3Normalize({ 0.8204f, -0.5702f, 0.0418f }), 0.89879f, 3.28f },
        { { 25.041f, 28.000f, 22.999f }, Vector3Normalize({ -0.6050f, -0.5702f, -0.5557f }), 0.89879f, 16.41f },
        { { 25.909f, 28.000f, -22.016f }, Vector3Normalize({ -0.6260f, -0.5702f, 0.5320f }), 0.89879f, 10.65f },
    };
}

GalleonAsset CreateGalleonAsset(Shader shader)
{
    GalleonAsset asset = { };

    const Color darkWood70 = WithOpacity(Color{ 92, 55, 28, 255 }, kDefaultOpacity);
    const Color midWood70 = WithOpacity(Color{ 125, 78, 44, 255 }, kDefaultOpacity);
    const Color lightWood70 = WithOpacity(Color{ 152, 101, 61, 255 }, kDefaultOpacity);
    const Color deckWood70 = WithOpacity(Color{ 168, 123, 77, 255 }, kDefaultOpacity);
    const Color darkWood90 = WithOpacity(Color{ 92, 55, 28, 255 }, kHeroOpacity);
    const Color midWood90 = WithOpacity(Color{ 125, 78, 44, 255 }, kHeroOpacity);
    const Color lightWood90 = WithOpacity(Color{ 152, 101, 61, 255 }, kHeroOpacity);
    const Color quarterdeckColor = WithOpacity(Color{ 125, 78, 44, 255 }, 1.00f);
    const Color sailColor = WithOpacity(Color{ 232, 228, 214, 255 }, 0.70f);
    const Color cannonColor = WithOpacity(Color{ 24, 24, 26, 255 }, kDefaultOpacity);
    const Color trimWood = WithOpacity(Color{ 81, 48, 24, 255 }, kDefaultOpacity);
    const Color mastWood = WithOpacity(Color{ 110, 73, 41, 255 }, kDefaultOpacity);

    {
        MeshBuilder builder;
        AddFrustum(builder, { 0.0f, 1.27f, 0.0f }, { 18.0f, 3.4f }, { 17.4f, 2.24f }, 1.2f);
        AddGalleonPart(asset.parts, builder.Build(), shader, darkWood70);
    }
    {
        MeshBuilder builder;
        AddTaperedBox(builder, { 0.2f, 2.2f, 0.0f }, { 15.5f, 1.7f, 4.9f }, { 15.5f, 1.7f, 4.1f });
        AddGalleonPart(asset.parts, builder.Build(), shader, midWood70);
    }
    {
        MeshBuilder builder;
        AddBox(builder, { 0.0f, 3.2f, 0.0f }, { 11.5f, 1.1f, 4.2f });
        AddGalleonPart(asset.parts, builder.Build(), shader, lightWood70);
    }
    {
        MeshBuilder builder;
        AddBox(builder, { -0.2f, 4.05f, 0.0f }, { 10.5f, 0.35f, 3.7f });
        AddGalleonPart(asset.parts, builder.Build(), shader, deckWood70);
    }
    {
        MeshBuilder builder;
        AddBox(builder, { -6.2f, 4.15f, 0.0f }, { 4.8f, 3.1f, 3.9f });
        AddGalleonPart(asset.parts, builder.Build(), shader, quarterdeckColor);
    }
    {
        MeshBuilder builder;
        AddBox(builder, { -5.6f, 5.5f, 0.0f }, { 3.4f, 1.2f, 3.3f });
        AddGalleonPart(asset.parts, builder.Build(), shader, lightWood70);
    }
    {
        MeshBuilder builder;
        AddFrustum(builder, { 7.56f, 3.49f, 0.0f }, { 3.12f, 1.56f }, { 3.80f, 2.04f }, 1.68f);
        AddGalleonPart(asset.parts, builder.Build(), shader, lightWood90);
    }
    {
        MeshBuilder builder;
        AddBox(builder, { 9.635f, 3.92f, 0.0f }, { 0.85f, 0.82f, 1.30f });
        AddGalleonPart(asset.parts, builder.Build(), shader, lightWood90);
    }
    {
        MeshBuilder builder;
        AddBowWedge(builder, { 8.3f, 2.05f, 0.0f }, 4.6f, 2.9f, 3.4f);
        AddGalleonPart(asset.parts, builder.Build(), shader, midWood90);
    }
    {
        MeshBuilder builder;
        AddBox(builder, { 11.16f, 4.48f, 0.0f }, { 2.88f, 0.14f, 0.14f });
        AddGalleonPart(asset.parts, builder.Build(), shader, mastWood);
    }
    {
        MeshBuilder builder;
        AddBox(builder, { 0.8f, 9.2f, 0.0f }, { 0.32f, 10.0f, 0.32f });
        AddBox(builder, { 4.025f, 8.45f, 0.0f }, { 0.28f, 8.5f, 0.28f });
        AddBox(builder, { -2.47f, 9.2f, 0.0f }, { 0.28f, 10.0f, 0.28f }); // New Mast 15% behind main mast
        AddBox(builder, { 7.56f, 6.7f, 0.0f }, { 0.22f, 5.1f, 0.22f });
        AddBox(builder, { -5.0f, 7.7f, 0.0f }, { 0.24f, 5.6f, 0.24f });
        AddGalleonPart(asset.parts, builder.Build(), shader, mastWood);
    }
    {
        MeshBuilder builder;
        AddBox(builder, { 0.8f, 13.4f, 0.0f }, { 0.12f, 0.12f, 5.28f });
        AddBox(builder, { 0.8f, 11.2f, 0.0f }, { 0.12f, 0.12f, 6.6f });
        AddBox(builder, { 0.8f, 8.4f, 0.0f }, { 0.13f, 0.13f, 7.26f });
        AddBox(builder, { 0.8f, 6.36f, 0.0f }, { 0.11f, 0.11f, 5.28f });
        AddBox(builder, { 4.025f, 11.85f, 0.0f }, { 0.10f, 0.10f, 4.50f });
        AddBox(builder, { 4.025f, 10.15f, 0.0f }, { 0.10f, 0.10f, 5.62f });
        AddBox(builder, { 4.025f, 7.77f, 0.0f }, { 0.11f, 0.11f, 6.18f });
        AddBox(builder, { 4.025f, 5.55f, 0.0f }, { 0.12f, 0.12f, 7.42f });
        // New Mast Yards (Raised)
        AddBox(builder, { -2.47f, 13.5f, 0.0f }, { 0.10f, 0.10f, 4.50f });
        AddBox(builder, { -2.47f, 12.0f, 0.0f }, { 0.10f, 0.10f, 5.62f });
        AddBox(builder, { -2.47f, 10.0f, 0.0f }, { 0.11f, 0.11f, 6.18f });
        AddBox(builder, { -2.47f, 7.5f, 0.0f }, { 0.12f, 0.12f, 7.42f });
        AddBox(builder, { -5.0f, 10.0f, 0.0f }, { 0.09f, 0.09f, 3.70f });
        AddBox(builder, { -5.0f, 8.0f, 0.0f }, { 0.09f, 0.09f, 4.26f });

        // Jib Sail Post
        const Vector3 jibP1 = { 11.75f, 6.2f, 0.0f };
        const Vector3 jibP2 = { 7.56f, 5.05f, 0.0f };
        const Vector3 jibDir = Vector3Subtract(jibP2, jibP1);
        const float jibLen = Vector3Length(jibDir);
        const Vector3 jibMid = Vector3Scale(Vector3Add(jibP1, jibP2), 0.5f);
        const float jibAngle = atan2f(jibDir.y, jibDir.x) * RAD2DEG;
        
        // Using a manual box build for the rotated post
        const float t = 0.09f; // Thickness from lower mizzen yard
        AddBox(builder, {0,0,0}, {jibLen, t, t});
        // We need to apply transformation manually to the vertices just added, or use a better helper.
        // Actually AddBox doesn't support rotation. I'll use a simpler AddPrismBarrel for the jib post.
        AddPrismBarrel(builder, jibP1, jibP2, t*0.5f, t*0.5f, 8);

        AddGalleonPart(asset.parts, builder.Build(), shader, mastWood);
    }
    {
        MeshBuilder builder;
        AddBillowedSail(builder, 0.8f, 13.4f, 11.2f, 2.64f, 3.3f, 0.62f, 0.10f);
        AddBillowedSail(builder, 0.8f, 11.2f, 8.4f, 3.3f, 3.63f, 0.78f, 0.10f);
        AddBillowedSail(builder, 0.8f, 8.4f, 6.36f, 3.63f, 2.64f, 0.72f, 0.10f);
        AddBillowedSail(builder, 4.025f, 11.85f, 10.15f, 2.25f, 2.81f, 0.44f, 0.10f);
        AddBillowedSail(builder, 4.025f, 10.15f, 7.77f, 2.81f, 3.09f, 0.58f, 0.10f);
        AddBillowedSail(builder, 4.025f, 7.77f, 5.55f, 3.09f, 3.71f, 0.66f, 0.10f);
        // New Mast Sails (Raised to match yards)
        AddBillowedSail(builder, -2.47f, 13.5f, 12.0f, 2.25f, 2.81f, 0.44f, 0.10f);
        AddBillowedSail(builder, -2.47f, 12.0f, 10.0f, 2.81f, 3.09f, 0.58f, 0.10f);
        AddBillowedSail(builder, -2.47f, 10.0f, 7.5f, 3.09f, 3.71f, 0.66f, 0.10f);
        AddBillowedSail(builder, -5.0f, 10.0f, 8.0f, 1.85f, 2.13f, 0.46f, 0.10f);
        AddJibSail(builder);
        AddGalleonPart(asset.parts, builder.Build(), shader, sailColor);
    }
    {
        MeshBuilder builder;
        for (int i = -3; i <= 3; ++i)
        {
            AddBox(builder, { i * 1.4f, 4.65f, -1.9f }, { 0.2f, 1.0f, 0.2f });
            AddBox(builder, { i * 1.4f, 4.65f, 1.9f }, { 0.2f, 1.0f, 0.2f });
        }
        AddBox(builder, { -5.8f, 6.35f, -1.55f }, { 0.2f, 1.1f, 0.2f });
        AddBox(builder, { -5.8f, 6.35f, 1.55f }, { 0.2f, 1.1f, 0.2f });
        AddBox(builder, { -3.8f, 6.35f, -1.55f }, { 0.2f, 1.1f, 0.2f });
        AddBox(builder, { -3.8f, 6.35f, 1.55f }, { 0.2f, 1.1f, 0.2f });
        AddGalleonPart(asset.parts, builder.Build(), shader, trimWood);
    }
    {
        MeshBuilder builder;
        const float upperY = 3.18f;
        const float midY = 2.18f;
        const float upperHalfLength = 11.5f * 0.5f;
        const float midHalfLength = 15.5f * 0.5f;
        const float upperSideZ = 4.2f * 0.5f;
        const float midSideZ = 4.9f * 0.5f;
        const float upperCannonLength = 4.2f * 0.10f;
        const float midCannonLength = 4.9f * 0.10f;

        for (int side = -1; side <= 1; side += 2)
        {
            const float sideSign = (float)side;

            for (int i = 0; i < 10; ++i)
            {
                const float t = ((float)i + 0.5f) / 10.0f;
                const float x = -upperHalfLength + t * (upperHalfLength * 2.0f);
                AddPrismBarrel(
                    builder,
                    { x, upperY, sideSign * upperSideZ },
                    { x, upperY, sideSign * (upperSideZ + upperCannonLength) },
                    0.07f,
                    0.06f,
                    8
                );
            }

            for (int i = 0; i < 20; ++i)
            {
                const float t = ((float)i + 0.5f) / 20.0f;
                const float x = -midHalfLength + t * (midHalfLength * 2.0f);
                AddPrismBarrel(
                    builder,
                    { x + 0.2f, midY, sideSign * midSideZ },
                    { x + 0.2f, midY, sideSign * (midSideZ + midCannonLength) },
                    0.06f,
                    0.05f,
                    8
                );
            }
        }
        AddGalleonPart(asset.parts, builder.Build(), shader, cannonColor);
    }

    asset.localBounds = {
        { -9.0f, 0.5f, -3.8f },
        { 12.8f, 14.4f, 3.8f }
    };
    return asset;
}

void DestroyGalleonAsset(GalleonAsset &asset)
{
    for (GalleonPart &part : asset.parts)
    {
        UnloadMaterial(part.material);
        UnloadMesh(part.mesh);
    }
    asset.parts.clear();
}

void DrawGalleonFleetInstanced(const GalleonAsset &asset, const std::vector<Matrix> &shipTransforms)
{
    if (shipTransforms.empty()) return;

    // First draw opaque parts (Alpha > 200)
    for (const GalleonPart &part : asset.parts)
    {
        if (part.material.maps[MATERIAL_MAP_DIFFUSE].color.a > 200)
        {
            DrawMeshInstanced(part.mesh, part.material, shipTransforms.data(), (int)shipTransforms.size());
        }
    }

    // Then draw transparent parts (Alpha <= 200)
    for (const GalleonPart &part : asset.parts)
    {
        if (part.material.maps[MATERIAL_MAP_DIFFUSE].color.a <= 200)
        {
            DrawMeshInstanced(part.mesh, part.material, shipTransforms.data(), (int)shipTransforms.size());
        }
    }
}
