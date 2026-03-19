#include "galleon_asset.h"
#include "raylib.h"
#include "raymath.h"
#include "rlgl.h"
#include <algorithm>
#include <cfloat>
#include <cmath>
#include <vector>

namespace
{
struct DebugShape
{
    const char *name;
    BoundingBox bounds;
};

Vector3 MakeVec(float x, float y, float z)
{
    return Vector3{ x, y, z };
}

BoundingBox MakeBounds(Vector3 center, Vector3 size)
{
    const Vector3 half = Vector3Scale(size, 0.5f);
    return BoundingBox{ Vector3Subtract(center, half), Vector3Add(center, half) };
}

void AddBoxDebugShape(std::vector<DebugShape> &shapes, const char *name, Vector3 center, Vector3 size)
{
    shapes.push_back(DebugShape{ name, MakeBounds(center, size) });
}

std::vector<DebugShape> BuildDebugShapes(float bobOffset)
{
    std::vector<DebugShape> shapes;
    shapes.reserve(40);

    AddBoxDebugShape(shapes, "Keel Band", MakeVec(0.0f, 1.27f + bobOffset, 0.0f), MakeVec(18.0f, 1.2f, 3.4f));
    AddBoxDebugShape(shapes, "Mid Hull Band", MakeVec(0.2f, 2.2f + bobOffset, 0.0f), MakeVec(15.5f, 1.7f, 4.9f));
    AddBoxDebugShape(shapes, "Upper Hull Band", MakeVec(0.0f, 3.2f + bobOffset, 0.0f), MakeVec(11.5f, 1.1f, 4.2f));
    AddBoxDebugShape(shapes, "Bow Wedge", MakeVec(8.3f, 2.05f + bobOffset, 0.0f), MakeVec(4.6f, 2.9f, 4.1f));
    AddBoxDebugShape(shapes, "Main Deck", MakeVec(-0.2f, 4.05f + bobOffset, 0.0f), MakeVec(10.5f, 0.35f, 3.7f));
    AddBoxDebugShape(shapes, "Quarterdeck", MakeVec(-6.2f, 4.15f + bobOffset, 0.0f), MakeVec(4.8f, 3.1f, 3.9f));
    AddBoxDebugShape(shapes, "Sterncastle", MakeVec(-5.6f, 5.5f + bobOffset, 0.0f), MakeVec(3.4f, 1.2f, 3.3f));
    AddBoxDebugShape(shapes, "Forecastle", MakeVec(7.56f, 3.49f + bobOffset, 0.0f), MakeVec(3.8f, 1.68f, 3.8f));
    AddBoxDebugShape(shapes, "Main Mast", MakeVec(0.8f, 9.2f + bobOffset, 0.0f), MakeVec(0.7f, 10.2f, 0.7f));
    AddBoxDebugShape(shapes, "Fore Mast", MakeVec(4.025f, 8.45f + bobOffset, 0.0f), MakeVec(0.6f, 8.7f, 0.6f));
    AddBoxDebugShape(shapes, "Secondary Mast", MakeVec(-2.47f, 9.2f + bobOffset, 0.0f), MakeVec(0.6f, 10.2f, 0.6f));
    AddBoxDebugShape(shapes, "Jib Mast", MakeVec(7.56f, 6.7f + bobOffset, 0.0f), MakeVec(0.42f, 5.1f, 0.42f));
    AddBoxDebugShape(shapes, "Mizzen Mast", MakeVec(-5.0f, 7.7f + bobOffset, 0.0f), MakeVec(0.5f, 5.8f, 0.5f));
    
    AddBoxDebugShape(shapes, "Lower Top Main Yard", MakeVec(0.8f, 6.36f + bobOffset, 0.0f), MakeVec(0.32f, 0.32f, 5.28f));
    AddBoxDebugShape(shapes, "Lower Main Yard", MakeVec(0.8f, 8.4f + bobOffset, 0.0f), MakeVec(0.45f, 0.45f, 7.26f));
    AddBoxDebugShape(shapes, "Main Yard", MakeVec(0.8f, 11.2f + bobOffset, 0.0f), MakeVec(0.34f, 0.34f, 6.6f));
    AddBoxDebugShape(shapes, "Top Main Yard", MakeVec(0.8f, 13.4f + bobOffset, 0.0f), MakeVec(0.32f, 0.32f, 5.28f));
    
    AddBoxDebugShape(shapes, "Lowest Fore Yard", MakeVec(4.025f, 5.55f + bobOffset, 0.0f), MakeVec(0.46f, 0.46f, 7.42f));
    AddBoxDebugShape(shapes, "Fore Lower Yard", MakeVec(4.025f, 7.77f + bobOffset, 0.0f), MakeVec(0.38f, 0.38f, 6.18f));
    AddBoxDebugShape(shapes, "Fore Yard", MakeVec(4.025f, 10.15f + bobOffset, 0.0f), MakeVec(0.34f, 0.34f, 5.62f));
    AddBoxDebugShape(shapes, "Top Fore Yard", MakeVec(4.025f, 11.85f + bobOffset, 0.0f), MakeVec(0.30f, 0.30f, 4.5f));

    AddBoxDebugShape(shapes, "Secondary Lowest Yard", MakeVec(-2.47f, 7.5f + bobOffset, 0.0f), MakeVec(0.46f, 0.46f, 7.42f));
    AddBoxDebugShape(shapes, "Secondary Lower Yard", MakeVec(-2.47f, 10.0f + bobOffset, 0.0f), MakeVec(0.38f, 0.38f, 6.18f));
    AddBoxDebugShape(shapes, "Secondary Yard", MakeVec(-2.47f, 12.0f + bobOffset, 0.0f), MakeVec(0.34f, 0.34f, 5.62f));
    AddBoxDebugShape(shapes, "Secondary Top Yard", MakeVec(-2.47f, 13.5f + bobOffset, 0.0f), MakeVec(0.30f, 0.30f, 4.5f));

    AddBoxDebugShape(shapes, "Lower Mizzen Yard", MakeVec(-5.0f, 8.0f + bobOffset, 0.0f), MakeVec(0.35f, 0.35f, 4.26f));
    AddBoxDebugShape(shapes, "Mizzen Yard", MakeVec(-5.0f, 10.0f + bobOffset, 0.0f), MakeVec(0.3f, 0.3f, 3.7f));
    
    AddBoxDebugShape(shapes, "Main Sail", MakeVec(0.9f, 12.3f + bobOffset, 0.0f), MakeVec(0.9f, 2.2f, 6.6f));
    AddBoxDebugShape(shapes, "Lower Main Sail", MakeVec(0.96f, 9.8f + bobOffset, 0.0f), MakeVec(1.1f, 2.8f, 7.26f));
    AddBoxDebugShape(shapes, "Lowest Main Sail", MakeVec(0.92f, 7.38f + bobOffset, 0.0f), MakeVec(1.0f, 2.04f, 7.26f));
    
    AddBoxDebugShape(shapes, "Top Fore Sail", MakeVec(4.095f, 11.0f + bobOffset, 0.0f), MakeVec(0.8f, 1.7f, 5.62f));
    AddBoxDebugShape(shapes, "Lower Fore Sail", MakeVec(4.16f, 8.96f + bobOffset, 0.0f), MakeVec(0.9f, 2.38f, 6.18f));
    AddBoxDebugShape(shapes, "Lowest Fore Sail", MakeVec(4.21f, 6.66f + bobOffset, 0.0f), MakeVec(1.0f, 2.22f, 7.42f));

    AddBoxDebugShape(shapes, "Secondary Top Sail", MakeVec(-2.47f + 0.07f, 12.75f + bobOffset, 0.0f), MakeVec(0.8f, 1.5f, 4.5f));
    AddBoxDebugShape(shapes, "Secondary Lower Sail", MakeVec(-2.47f + 0.13f, 11.0f + bobOffset, 0.0f), MakeVec(0.9f, 2.0f, 5.62f));
    AddBoxDebugShape(shapes, "Secondary Lowest Sail", MakeVec(-2.47f + 0.18f, 8.75f + bobOffset, 0.0f), MakeVec(1.0f, 2.5f, 6.18f));

    AddBoxDebugShape(shapes, "Mizzen Sail", MakeVec(-4.95f, 9.0f + bobOffset, 0.0f), MakeVec(0.7f, 2.0f, 4.26f));
    AddBoxDebugShape(shapes, "Jib Sail", MakeVec(9.66f, 7.15f + bobOffset, 0.0f), MakeVec(4.3f, 4.3f, 0.4f));
    AddBoxDebugShape(shapes, "Jib Post", MakeVec(9.66f, 5.6f + bobOffset, 0.0f), MakeVec(4.3f, 0.3f, 0.3f));

    return shapes;
}

int FindHoveredShape(const std::vector<DebugShape> &shapes, Ray ray)
{
    int hoveredIndex = -1;
    float closestDistance = FLT_MAX;

    for (int i = 0; i < (int)shapes.size(); ++i)
    {
        const RayCollision hit = GetRayCollisionBox(ray, shapes[i].bounds);
        if (hit.hit && hit.distance < closestDistance)
        {
            hoveredIndex = i;
            closestDistance = hit.distance;
        }
    }

    return hoveredIndex;
}
}

int main()
{
    const int screenWidth = 1280;
    const int screenHeight = 720;

    InitWindow(screenWidth, screenHeight, "Low Poly Galleon");
    SetTargetFPS(60);

    Camera3D camera = { 0 };
    camera.target = MakeVec(0.0f, 4.4f, 0.0f);
    camera.up = MakeVec(0.0f, 1.0f, 0.0f);
    camera.fovy = 38.0f;
    camera.projection = CAMERA_PERSPECTIVE;

    float orbitAngle = 238.25f;
    float orbitHeight = 59.402f;
    float orbitDistance = 76.134f;
    int selectedShape = -1;

    Shader spotlightShader = CreateSpotlightShader();
    const std::vector<SpotlightRecord> lights = GetDefaultGalleonSpotlights();
    ApplySpotlights(spotlightShader, lights);
    GalleonAsset galleon = CreateGalleonAsset(spotlightShader);

    while (!WindowShouldClose())
    {
        if (IsKeyDown(KEY_A)) orbitAngle -= 42.0f * GetFrameTime();
        if (IsKeyDown(KEY_D)) orbitAngle += 42.0f * GetFrameTime();
        if (IsKeyDown(KEY_W)) orbitHeight += 12.0f * GetFrameTime();
        if (IsKeyDown(KEY_S)) orbitHeight -= 12.0f * GetFrameTime();
        if (IsKeyDown(KEY_Q)) orbitDistance -= 16.0f * GetFrameTime();
        if (IsKeyDown(KEY_E)) orbitDistance += 16.0f * GetFrameTime();

        camera.position = MakeVec(
            std::cos(orbitAngle * DEG2RAD) * orbitDistance,
            orbitHeight,
            std::sin(orbitAngle * DEG2RAD) * orbitDistance
        );

        const float time = (float)GetTime();
        const float bobOffset = std::sin(time * 1.35f) * 0.18f;
        const std::vector<DebugShape> debugShapes = BuildDebugShapes(bobOffset);
        const Ray mouseRay = GetMouseRay(GetMousePosition(), camera);
        const int hoveredShape = FindHoveredShape(debugShapes, mouseRay);

        if (IsMouseButtonPressed(MOUSE_LEFT_BUTTON))
        {
            selectedShape = hoveredShape;
        }

        if (IsKeyPressed(KEY_SPACE))
        {
            SetClipboardText(TextFormat("{ %.3ff, %.3ff, %.3ff }", camera.position.x, camera.position.y, camera.position.z));
        }

        const std::vector<Matrix> shipTransforms = { MatrixTranslate(0.0f, bobOffset, 0.0f) };

        BeginDrawing();
        ClearBackground(Color{ 146, 196, 232, 255 });

        BeginMode3D(camera);
            rlSetLineWidth(3.0f);
            DrawPlane(MakeVec(0.0f, -0.15f, 0.0f), Vector2{ 120.0f, 120.0f }, Color{ 36, 86, 126, 255 });
            DrawPlane(MakeVec(0.0f, -0.12f, 0.0f), Vector2{ 120.0f, 120.0f }, Fade(SKYBLUE, 0.18f));

            for (int x = -3; x <= 3; ++x)
            {
                DrawCubeV(
                    MakeVec((float)x * 9.0f, -0.08f, -18.0f + std::sin(time + (float)x) * 0.7f),
                    MakeVec(5.2f, 0.02f, 1.2f),
                    Fade(WHITE, 0.22f)
                );
            }

            BeginShaderMode(spotlightShader);
                rlDisableBackfaceCulling();
                DrawGalleonFleetInstanced(galleon, shipTransforms);
                rlEnableBackfaceCulling();
            EndShaderMode();

            if (hoveredShape >= 0)
            {
                DrawBoundingBox(debugShapes[hoveredShape].bounds, YELLOW);
            }

            if (selectedShape >= 0 && selectedShape < (int)debugShapes.size())
            {
                DrawBoundingBox(debugShapes[selectedShape].bounds, RED);
            }
            rlSetLineWidth(1.0f);
        EndMode3D();

        DrawRectangle(18, 18, 430, 200, Fade(BLACK, 0.62f));
        DrawText("LOW POLY GALLEON STUDY", 30, 28, 24, RAYWHITE);
        DrawText("A/D orbit  W/S height  Q/E zoom", 30, 60, 18, Color{ 196, 220, 235, 255 });
        DrawText("SPACE to copy camera pos", 30, 82, 18, Color{ 196, 220, 235, 255 });
        DrawText(TextFormat("Camera: { %.2f, %.2f, %.2f }", camera.position.x, camera.position.y, camera.position.z), 30, 108, 18, GREEN);
        DrawText(TextFormat("Hover: %s", hoveredShape >= 0 ? debugShapes[hoveredShape].name : "--"), 30, 136, 18, YELLOW);
        DrawText(TextFormat("Selected: %s", selectedShape >= 0 ? debugShapes[selectedShape].name : "--"), 30, 164, 18, RED);
        
        DrawRectangle(18, 226, 430, 74, Fade(BLACK, 0.62f));
        DrawText(TextFormat("Spotlights: %i", (int)lights.size()), 30, 188, 20, RAYWHITE);
        DrawText("Using baked model lighting", 30, 214, 18, Color{ 196, 220, 235, 255 });

        EndDrawing();
    }

    DestroyGalleonAsset(galleon);
    UnloadShader(spotlightShader);
    CloseWindow();
    return 0;
}
