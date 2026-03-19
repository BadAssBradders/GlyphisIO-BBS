#include "raylib.h"
#include "raymath.h"
#include <vector>
#include <iostream>
#include <stdio.h>

struct Plank {
    Vector3 position;
    Vector3 size;
    Color color;
    bool selected;
};

int main() {
    InitWindow(1280, 720, "Sea-Trials: Mini Studio (Undo Enabled)");

    Camera3D camera = { 0 };
    camera.position = (Vector3){ 40.0f, 40.0f, 40.0f };
    camera.target = (Vector3){ 0.0f, 0.0f, 0.0f };
    camera.up = (Vector3){ 0.0f, 1.0f, 0.0f };
    camera.fovy = 30.0f; 
    camera.projection = CAMERA_ORTHOGRAPHIC;

    std::vector<Plank> worldPlanks;
    std::vector<Plank> copyBuffer;
    
    Vector2 selectionStart = { 0 };
    bool isSelecting = false;
    float curH = 1.0f;
    float pW = 1.0f, pL = 3.0f;
    float cameraAngle = 45.0f;
    bool rotated = false;
    float manualY = 0.0f; 

    SetTargetFPS(60);

    while (!WindowShouldClose()) {
        // --- 1. CAMERA & ZOOM ---
        if (IsKeyDown(KEY_RIGHT)) cameraAngle += 2.0f;
        if (IsKeyDown(KEY_LEFT)) cameraAngle -= 2.0f;

        if (IsKeyDown(KEY_LEFT_SHIFT)) {
            if (IsKeyDown(KEY_EQUAL)) camera.fovy -= 0.5f;
            if (IsKeyDown(KEY_MINUS)) camera.fovy += 0.5f;
        }
        if (camera.fovy < 2.0f) camera.fovy = 2.0f;

        camera.position.x = cos(cameraAngle * DEG2RAD) * 60.0f;
        camera.position.z = sin(cameraAngle * DEG2RAD) * 60.0f;

        // --- 2. UNDO LOGIC (Ctrl + Z) ---
        if (IsKeyDown(KEY_LEFT_CONTROL) && IsKeyPressed(KEY_Z)) {
            if (!worldPlanks.empty()) worldPlanks.pop_back();
        }

        // --- 3. ALTITUDE (Z/X) & SPECS ---
        if (IsKeyPressed(KEY_Z)) manualY += 0.25f;
        if (IsKeyPressed(KEY_X)) manualY -= 0.25f;
        if (manualY < 0) manualY = 0; 

        if (IsMouseButtonPressed(MOUSE_RIGHT_BUTTON)) {
            if (curH == 0.5f) curH = 1.0f;
            else if (curH == 1.0f) curH = 2.0f;
            else curH = 0.5f;
        }
        if (IsKeyPressed(KEY_R)) rotated = !rotated;

        Vector3 currentSize = rotated ? (Vector3){ pL, curH, pW } : (Vector3){ pW, curH, pL };
        Ray ray = GetMouseRay(GetMousePosition(), camera);
        RayCollision workPlaneHit = GetRayCollisionQuad(ray, 
            (Vector3){-100, manualY, -100}, (Vector3){-100, manualY, 100}, 
            (Vector3){100, manualY, 100}, (Vector3){100, manualY, -100});

        Vector3 activePos = { 
            round(workPlaneHit.point.x / 0.25f) * 0.25f, 
            manualY + (currentSize.y / 2.0f), 
            round(workPlaneHit.point.z / 0.25f) * 0.25f 
        };

        // --- 4. SELECTION & COPY/PASTE ---
        bool ctrl = IsKeyDown(KEY_LEFT_CONTROL);
        if (ctrl && !IsKeyPressed(KEY_Z) && IsMouseButtonPressed(MOUSE_LEFT_BUTTON)) {
            selectionStart = GetMousePosition();
            isSelecting = true;
            for (auto& p : worldPlanks) p.selected = false;
        }
        
        if (isSelecting && IsMouseButtonReleased(MOUSE_LEFT_BUTTON)) {
            isSelecting = false;
            copyBuffer.clear();
            Rectangle selRect = { fminf(selectionStart.x, GetMouseX()), fminf(selectionStart.y, GetMouseY()), fabsf(selectionStart.x - GetMouseX()), fabsf(selectionStart.y - GetMouseY()) };
            for (auto& p : worldPlanks) {
                Vector2 sPos = GetWorldToScreen(p.position, camera);
                if (CheckCollisionPointRec(sPos, selRect)) {
                    p.selected = true;
                    copyBuffer.push_back(p);
                }
            }
        }

        // --- 5. ACTIONS ---
        // Place
        if (!ctrl && !isSelecting && IsMouseButtonPressed(MOUSE_LEFT_BUTTON)) {
            worldPlanks.push_back({activePos, currentSize, (Color){140, 105, 75, 255}, false});
        }
        // Paste
        if (IsKeyPressed(KEY_V) && !copyBuffer.empty()) {
            Vector3 base = copyBuffer[0].position;
            for (auto p : copyBuffer) {
                Vector3 offset = Vector3Subtract(p.position, base);
                p.position = Vector3Add(activePos, offset);
                p.selected = false;
                worldPlanks.push_back(p);
            }
        }
        // Export
        if (IsKeyPressed(KEY_SPACE)) {
            printf("\n// --- SHIP GENERATED ---\n");
            for (const auto& p : worldPlanks) {
                printf("DrawCube((Vector3){%.2ff, %.2ff, %.2ff}, %.2ff, %.2ff, %.2ff, BROWN);\n", 
                    p.position.x, p.position.y, p.position.z, p.size.x, p.size.y, p.size.z);
            }
            fflush(stdout);
        }

        // --- 6. DRAWING ---
        BeginDrawing();
            ClearBackground((Color){18, 18, 22, 255});
            BeginMode3D(camera);
                DrawGrid(40, 1.0f);
                DrawPlane((Vector3){0, manualY, 0}, (Vector2){100, 100}, Fade(LIME, 0.05f));

                for (auto& p : worldPlanks) {
                    DrawCube(p.position, p.size.x, p.size.y, p.size.z, p.selected ? GOLD : p.color);
                    DrawCubeWires(p.position, p.size.x, p.size.y, p.size.z, p.selected ? YELLOW : Fade(BLACK, 0.3f));
                }
                
                if (!isSelecting) {
                    DrawCube(activePos, currentSize.x, currentSize.y, currentSize.z, Fade(LIME, 0.5f));
                    DrawCubeWires(activePos, currentSize.x, currentSize.y, currentSize.z, GREEN);
                }
            EndMode3D();

            if (isSelecting) DrawRectangleLinesEx({ fminf(selectionStart.x, GetMouseX()), fminf(selectionStart.y, GetMouseY()), fabsf(selectionStart.x - GetMouseX()), fabsf(selectionStart.y - GetMouseY()) }, 2, GOLD);

            DrawRectangle(10, 10, 360, 140, Fade(BLACK, 0.8f));
            DrawText("CTRL + Z: Undo", 20, 20, 16, MAROON);
            DrawText("Z / X: Alt | R: Rotate", 20, 45, 16, WHITE);
            DrawText("CTRL + DRAG: Select | V: Paste", 20, 70, 16, GOLD);
            DrawText(TextFormat("Planks Count: %i", (int)worldPlanks.size()), 20, 100, 18, SKYBLUE);
        EndDrawing();
    }
    CloseWindow();
    return 0;
}