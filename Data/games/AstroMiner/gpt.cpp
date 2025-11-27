#include "raylib.h"
#include "raymath.h"

// ------------------------------------------------------------
// TERRAIN FUNCTION
// ------------------------------------------------------------
float GetTerrainHeight(float x, float z)
{
    return
        1.2f * sinf(x * 0.15f) +
        0.8f * cosf(z * 0.12f) +
        0.4f * sinf((x + z) * 0.08f);
}

// ------------------------------------------------------------
// PARTICLES
// ------------------------------------------------------------
struct Particle {
    Vector3 pos;
    Vector3 vel;
    Color color;
    float life;
};

Particle particles[100] = {0};

Color thrusterPalette[5] = {
    (Color){0,255,255,255},
    WHITE,
    (Color){135,206,235,255},
    (Color){255,127,80,255},
    YELLOW
};

void SpawnParticle(Vector3 worldPos, Vector3 thrustDir)
{
    for (int i = 0; i < 100; i++)
    {
        if (particles[i].life <= 0)
        {
            particles[i].pos = worldPos;

            particles[i].vel = Vector3Add(
                Vector3Scale(thrustDir, -1.2f),
                (Vector3){
                    ((float)GetRandomValue(-10, 10))/120.0f,
                    ((float)GetRandomValue(-10, 10))/120.0f,
                    ((float)GetRandomValue(-10, 10))/120.0f
                }
            );

            particles[i].color = thrusterPalette[GetRandomValue(0,4)];
            particles[i].life = 1.0f;
            return;
        }
    }
}

void UpdateParticles(float dt)
{
    for (int i = 0; i < 100; i++)
    {
        if (particles[i].life > 0)
        {
            particles[i].life -= dt;
            particles[i].pos = Vector3Add(particles[i].pos, Vector3Scale(particles[i].vel, dt));
            particles[i].vel.y -= 0.25f * dt;
        }
    }
}

void DrawParticles()
{
    for (int i = 0; i < 100; i++)
    {
        if (particles[i].life > 0)
        {
            Color c = particles[i].color;
            c.a = (unsigned char)(particles[i].life * 255);
            DrawCube(particles[i].pos, 0.05f, 0.05f, 0.05f, c);
        }
    }
}

// ------------------------------------------------------------
// SHIP MODEL
// ------------------------------------------------------------
Mesh CreateSolidShip()
{
    Vector3 nose   = { 0,    0,    1.8f };
    Vector3 tail   = { 0,    0,   -1.5f };
    Vector3 left   = {-1.5f, 0,   -0.8f };
    Vector3 right  = { 1.5f, 0,   -0.8f };
    Vector3 top    = { 0,    0.4f,-0.3f };
    Vector3 bottom = { 0,   -0.4f,-0.3f };

    Vector3 tris[8][3] = {
        { top,    left,   nose },
        { top,    nose,   right },
        { top,    tail,   left },
        { top,    right,  tail },

        { bottom, nose,   left },
        { bottom, right,  nose },
        { bottom, left,   tail },
        { bottom, tail,   right }
    };

    Color col[8] = {
        {135,206,235,255},{173,216,230,255},{0,191,255,255},{30,144,255,255},
        {65,105,225,255},{0,0,205,255},{0,0,139,255},{0,0,128,255}
    };

    Mesh mesh = {0};
    mesh.triangleCount = 8;
    mesh.vertexCount = 24;

    mesh.vertices = (float*)MemAlloc(mesh.vertexCount * 3 * sizeof(float));
    mesh.normals  = (float*)MemAlloc(mesh.vertexCount * 3 * sizeof(float));
    mesh.colors   = (unsigned char*)MemAlloc(mesh.vertexCount * 4);

    int idx = 0;

    for (int t = 0; t < 8; t++)
    {
        Vector3 a = tris[t][0];
        Vector3 b = tris[t][1];
        Vector3 c = tris[t][2];

        Vector3 n = Vector3Normalize(Vector3CrossProduct(Vector3Subtract(b,a), Vector3Subtract(c,a)));

        Vector3 v[3] = {a,b,c};
        for (int k = 0; k < 3; k++)
        {
            mesh.vertices[idx*3+0] = v[k].x;
            mesh.vertices[idx*3+1] = v[k].y;
            mesh.vertices[idx*3+2] = v[k].z;

            mesh.normals[idx*3+0] = n.x;
            mesh.normals[idx*3+1] = n.y;
            mesh.normals[idx*3+2] = n.z;

            mesh.colors[idx*4+0] = col[t].r;
            mesh.colors[idx*4+1] = col[t].g;
            mesh.colors[idx*4+2] = col[t].b;
            mesh.colors[idx*4+3] = col[t].a;

            idx++;
        }
    }

    UploadMesh(&mesh, false);
    return mesh;
}

// ------------------------------------------------------------
// ROTATION MATRIX
// ------------------------------------------------------------
Matrix GetShipRotationMatrix(float pitch, float roll)
{
    Matrix rotPitch = MatrixRotateX(DEG2RAD * pitch);
    Matrix rotRoll  = MatrixRotateZ(DEG2RAD * roll);
    return MatrixMultiply(rotRoll, rotPitch);
}

// ------------------------------------------------------------
// MAIN
// ------------------------------------------------------------
int main()
{
    InitWindow(872, 654, "AstroMiner Lander Flight Model");
    SetTargetFPS(60);

    DisableCursor();

    Camera3D camera = {0};
    camera.up = (Vector3){0,1,0};
    camera.fovy = 45;
    camera.projection = CAMERA_PERSPECTIVE;

    Shader shader = LoadShader("E:/Dev/raylib/shaders/flat.vs",
                               "E:/Dev/raylib/shaders/flat.fs");

    Mesh mesh = CreateSolidShip();
    Model ship = LoadModelFromMesh(mesh);
    ship.materials[0].shader = shader;

    Vector3 shipPos = {0, 4, 0};
    Vector3 shipVel = {0};

    float shipRoll  = 0;
    float shipPitch = 0;

    Vector3 engineOffset = {0, -0.5f, 0};

    float gravity = -1.63f;

    float thrust = 0.0f;
    float thrustBuild = 2.0f;
    float thrustMax = 5.0f;

    float shipHeight = 2.0f;
    float altitudeCap = shipHeight * 10.0f;

    float shipLength = 3.3f;

    // ------------------------------------------------------------
    while (!WindowShouldClose())
    {
        float dt = GetFrameTime();

        // ORIENTATION INPUT
        Vector2 m = GetMouseDelta();
        shipRoll  += m.x * 0.05f;
        shipPitch += m.y * 0.05f;
        shipPitch = Clamp(shipPitch, -20.0f, 20.0f);

        // ROTATION DAMPING (Lander feel)
        shipPitch *= 0.98f;
        shipRoll  *= 0.98f;

        Matrix R = GetShipRotationMatrix(shipPitch, shipRoll);
        Vector3 thrustDir = Vector3Normalize((Vector3){ R.m8, R.m9, R.m10 });

        // THRUST (Lander analogue curve)
        if (IsMouseButtonDown(MOUSE_LEFT_BUTTON)) {
            thrust += thrustBuild * dt;
        } else {
            thrust -= thrustBuild * dt * 0.7f;
        }
        thrust = Clamp(thrust, 0.0f, thrustMax);
        float appliedThrust = thrust * thrust;

        shipVel = Vector3Add(shipVel, Vector3Scale(thrustDir, appliedThrust * dt));
        shipVel.y += gravity * dt;

        // Horizontal drift damp
        shipVel.x *= 0.995f;
        shipVel.z *= 0.995f;

        shipPos = Vector3Add(shipPos, shipVel);

        // TERRAIN & CEILING
        float terrainY = GetTerrainHeight(shipPos.x, shipPos.z);
        float maxAltitude = terrainY + altitudeCap;

        if (shipPos.y > maxAltitude) {
            shipPos.y = maxAltitude;
            shipVel.y *= 0.2f;
        }

        if (shipPos.y < terrainY) {
            shipPos.y = terrainY;
            shipVel.y = 0;
        }

        // PARTICLES
        Vector3 engineWorld = Vector3Add(shipPos, Vector3Transform(engineOffset, R));
        if (IsMouseButtonDown(MOUSE_LEFT_BUTTON)) {
            SpawnParticle(engineWorld, thrustDir);
            SpawnParticle(engineWorld, thrustDir);
        }
        UpdateParticles(dt);

        // CAMERA FOLLOW (8 ship-lengths back)
        Vector3 shipForward = Vector3Normalize((Vector3){ R.m8, R.m9, R.m10 });
        float desiredDist = shipLength * 8.0f;

        Vector3 desiredCamPos =
            Vector3Subtract(shipPos, Vector3Scale(shipForward, desiredDist));

        camera.position = Vector3Lerp(camera.position, desiredCamPos, 4.0f * dt);
        camera.target = shipPos;

        // ------------------------------------------------------------
        // DRAW
        // ------------------------------------------------------------
        BeginDrawing();
        ClearBackground(BLACK);
        BeginMode3D(camera);

        // TERRAIN
        for (int x = -40; x < 40; x++)
        {
            for (int z = -40; z < 40; z++)
            {
                float xf  = (float)x;
                float zf  = (float)z;
                float xf1 = xf + 1;
                float zf1 = zf + 1;

                Vector3 p0 = { xf,  GetTerrainHeight(xf,  zf),  zf  };
                Vector3 p1 = { xf1, GetTerrainHeight(xf1, zf),  zf  };
                Vector3 p2 = { xf,  GetTerrainHeight(xf,  zf1), zf1 };
                Vector3 p3 = { xf1, GetTerrainHeight(xf1, zf1), zf1 };

                DrawTriangle3D(p0, p2, p1, DARKGREEN);
                DrawTriangle3D(p1, p2, p3, DARKGREEN);
            }
        }

        // SHADOW
        float groundY = GetTerrainHeight(shipPos.x, shipPos.z);
        float heightAboveGround = shipPos.y - groundY;
        float shadowSize = Clamp(1.5f - heightAboveGround * 0.05f, 0.3f, 1.5f);

        DrawCylinder(
            (Vector3){ shipPos.x, groundY + 0.02f, shipPos.z },
            shadowSize, shadowSize, 0.01f, 20,
            (Color){0,0,0,120}
        );

        // SHIP
        Vector3 axis = Vector3Normalize((Vector3){shipPitch, 0, shipRoll});
        float angle = Vector3Length((Vector3){shipPitch, 0, shipRoll});

        BeginShaderMode(shader);
            DrawModelEx(ship, shipPos, axis, angle, (Vector3){1,1,1}, WHITE);
        EndShaderMode();

        DrawParticles();

        EndMode3D();

        DrawFPS(10, 10);
        DrawText("Lander-style controls + altitude cap + follow cam", 10, 40, 16, WHITE);

        EndDrawing();
    }

    CloseWindow();
    return 0;
}
