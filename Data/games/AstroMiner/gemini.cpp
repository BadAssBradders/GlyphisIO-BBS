#include "raylib.h"
#include "raymath.h"
#include "rlgl.h"
#include <math.h>

// ------------------------------------------------------------
// CONSTANTS
// ------------------------------------------------------------
#define ROCK_TRI_COUNT 36
// REDUCED DRAWING DISTANCE (Was 30, now 15 for 50% reduction)
const int RENDER_DISTANCE = 15;

// ------------------------------------------------------------
// DATA STRUCTURES FOR COLLISION
// ------------------------------------------------------------
typedef struct Tri {
    Vector3 a;
    Vector3 b;
    Vector3 c;
} Tri;

Tri G_RockTris[ROCK_TRI_COUNT];

// ------------------------------------------------------------
// MATH HELPERS
// ------------------------------------------------------------
// Barycentric technique to get height on a 3D triangle from 2D coords
bool GetHeightOnTriangle(Vector3 p1, Vector3 p2, Vector3 p3, float x, float z, float* outY)
{
    float det = (p2.z - p3.z) * (p1.x - p3.x) + (p3.x - p2.x) * (p1.z - p3.z);
    float l1 = ((p2.z - p3.z) * (x - p3.x) + (p3.x - p2.x) * (z - p3.z)) / det;
    float l2 = ((p3.z - p1.z) * (x - p3.x) + (p1.x - p3.x) * (z - p3.z)) / det;
    float l3 = 1.0f - l1 - l2;
    if (l1 >= 0.0f && l1 <= 1.0f && l2 >= 0.0f && l2 <= 1.0f && l3 >= 0.0f && l3 <= 1.0f) {
        *outY = l1 * p1.y + l2 * p2.y + l3 * p3.y;
        return true;
    }
    return false;
}

// ------------------------------------------------------------
// TERRAIN
// ------------------------------------------------------------
float GetTerrainHeight(float x, float z)
{
    return
        1.2f * sinf(x * 0.15f) +
        0.8f * cosf(z * 0.12f) +
        0.4f * sinf((x + z) * 0.08f);
}

// ------------------------------------------------------------
// WORLD HEIGHT (ACCURATE MESH COLLISION)
// ------------------------------------------------------------
float GetWorldHeight(float x, float z)
{
    float height = GetTerrainHeight(x, z);
    for (int i = 0; i < ROCK_TRI_COUNT; i++) {
        float triH;
        if (GetHeightOnTriangle(G_RockTris[i].a, G_RockTris[i].b, G_RockTris[i].c, x, z, &triH)) {
            if (triH > height) height = triH;
        }
    }
    return height;
}

// ------------------------------------------------------------
// PARTICLES
// ------------------------------------------------------------
struct Particle {
    Vector3 pos; Vector3 vel; Color color; float life; bool onGround;
};
#define MAX_PARTICLES 400
Particle particles[MAX_PARTICLES] = {0};
Color thrusterPalette[7] = { GOLD, ORANGE, RED, MAROON, YELLOW, (Color){0, 255, 255, 255}, WHITE };

void SpawnThrustParticles(Vector3 nozzlePos, Vector3 shipUpVector) {
    Vector3 ejectDir = Vector3Scale(shipUpVector, -1.0f);
    int particlesPerFrame = 4;
    for (int k = 0; k < particlesPerFrame; k++) {
        for (int i = 0; i < MAX_PARTICLES; i++) {
            if (particles[i].life <= 0) {
                particles[i].pos = nozzlePos; particles[i].onGround = false;
                Vector3 noise = { (GetRandomValue(-50,50))/100.0f, (GetRandomValue(-50,50))/100.0f, (GetRandomValue(-50,50))/100.0f };
                Vector3 spreadDir = Vector3Add(ejectDir, Vector3Scale(noise, 0.6f));
                particles[i].vel = Vector3Scale(spreadDir, (float)GetRandomValue(50, 100) / 10.0f);
                particles[i].color = thrusterPalette[GetRandomValue(0,6)];
                particles[i].life = 1.5f; break;
            }
        }
    }
}

void UpdateParticles(float dt) {
    float gravity = -9.0f;
    for (int i = 0; i < MAX_PARTICLES; i++) {
        if (particles[i].life > 0) {
            particles[i].life -= dt;
            if (!particles[i].onGround) {
                particles[i].vel.y += gravity * dt;
                particles[i].pos = Vector3Add(particles[i].pos, Vector3Scale(particles[i].vel, dt));
                float worldH = GetWorldHeight(particles[i].pos.x, particles[i].pos.z);
                if (particles[i].pos.y <= worldH + 0.05f) {
                    particles[i].pos.y = worldH + 0.05f; particles[i].onGround = true;
                    particles[i].vel.y = 0; particles[i].vel.x *= 0.5f; particles[i].vel.z *= 0.5f;
                }
            } else {
                particles[i].vel.x *= 0.90f; particles[i].vel.z *= 0.90f;
                particles[i].pos = Vector3Add(particles[i].pos, Vector3Scale(particles[i].vel, dt));
            }
        }
    }
}

void DrawParticles() {
    for (int i = 0; i < MAX_PARTICLES; i++) if (particles[i].life > 0)
        DrawCube(particles[i].pos, 0.075f, 0.075f, 0.075f, particles[i].color);
}

// ------------------------------------------------------------
// SHIP MESH
// ------------------------------------------------------------
Mesh CreateSolidShip() {
    Vector3 nose={0,0,1.0f}, tail={0,0,-1.0f}, left={-0.8f,0,-0.5f}, right={0.8f,0,-0.5f}, top={0,0.3f,-0.2f}, bottom={0,-0.3f,-0.2f};
    Vector3 tris[8][3]={{top,left,nose},{top,nose,right},{top,tail,left},{top,right,tail},{bottom,nose,left},{bottom,right,nose},{bottom,left,tail},{bottom,tail,right}};
    Color col[8]={{135,206,250,255},{70,170,240,255},{30,144,255,255},{0,100,220,255},{0,60,180,255},{0,40,140,255},{0,20,100,255},{0,5,60,255}};
    Mesh mesh={0}; mesh.triangleCount=8; mesh.vertexCount=24;
    mesh.vertices=(float*)MemAlloc(mesh.vertexCount*3*sizeof(float));
    mesh.normals=(float*)MemAlloc(mesh.vertexCount*3*sizeof(float));
    mesh.colors=(unsigned char*)MemAlloc(mesh.vertexCount*4);
    int idx=0;
    for(int t=0;t<8;t++){
        Vector3 n=Vector3Normalize(Vector3CrossProduct(Vector3Subtract(tris[t][1],tris[t][0]), Vector3Subtract(tris[t][2],tris[t][0])));
        for(int k=0;k<3;k++){
            mesh.vertices[idx*3+0]=tris[t][k].x; mesh.vertices[idx*3+1]=tris[t][k].y; mesh.vertices[idx*3+2]=tris[t][k].z;
            mesh.normals[idx*3+0]=n.x; mesh.normals[idx*3+1]=n.y; mesh.normals[idx*3+2]=n.z;
            mesh.colors[idx*4+0]=col[t].r; mesh.colors[idx*4+1]=col[t].g; mesh.colors[idx*4+2]=col[t].b; mesh.colors[idx*4+3]=col[t].a;
            idx++;
        }
    }
    UploadMesh(&mesh,false); return mesh;
}

// ------------------------------------------------------------
// ROCK MESH (Generates Graphics AND Physics Data)
// ------------------------------------------------------------
Mesh CreateRockMeshAndData(Vector3 worldPos, float scale, Matrix rotation) {
    float phi = 1.61803398875f; float inv = 1.0f/phi;
    Vector3 vLocal[20] = {{1,1,1},{1,1,-1},{1,-1,1},{1,-1,-1},{-1,1,1},{-1,1,-1},{-1,-1,1},{-1,-1,-1},{0,inv,phi},{0,inv,-phi},{0,-inv,phi},{0,-inv,-phi},{inv,phi,0},{inv,-phi,0},{-inv,phi,0},{-inv,-phi,0},{phi,0,inv},{phi,0,-inv},{-phi,0,inv},{-phi,0,-inv}};
    int faces[12][5] = {{0,16,2,10,8},{0,8,4,14,12},{16,17,1,12,0},{1,9,11,3,17},{1,12,14,5,9},{2,13,15,6,10},{13,3,11,7,15},{4,8,10,6,18},{14,4,18,19,5},{5,19,7,11,9},{15,7,19,18,6},{2,16,17,3,13}};
    Color rockPalette[12] = {{80,80,80,255},{100,100,105,255},{90,85,80,255},{70,70,70,255},{60,60,65,255},{110,110,110,255},{55,55,55,255},{75,70,65,255},{65,65,65,255},{85,85,90,255},{45,45,50,255},{95,95,95,255}};
    Mesh mesh = {0}; mesh.triangleCount=36; mesh.vertexCount=mesh.triangleCount*3;
    mesh.vertices=(float*)MemAlloc(mesh.vertexCount*3*sizeof(float));
    mesh.normals=(float*)MemAlloc(mesh.vertexCount*3*sizeof(float));
    mesh.colors=(unsigned char*)MemAlloc(mesh.vertexCount*4);
    int idx=0; int globalTriIdx=0;
    for(int f=0;f<12;f++){
        Color faceCol=rockPalette[f]; Vector3 pWorld[5];
        for(int i=0;i<5;i++) {
            pWorld[i]=Vector3Add(Vector3Transform(Vector3Scale(vLocal[faces[f][i]],scale),rotation), worldPos);
        }
        Vector3 n=Vector3Normalize(Vector3CrossProduct(Vector3Subtract(pWorld[1],pWorld[0]), Vector3Subtract(pWorld[2],pWorld[0])));
        int tris[3][3]={{0,1,2},{0,2,3},{0,3,4}};
        for(int t=0;t<3;t++){
            G_RockTris[globalTriIdx].a=pWorld[tris[t][0]]; G_RockTris[globalTriIdx].b=pWorld[tris[t][1]]; G_RockTris[globalTriIdx].c=pWorld[tris[t][2]]; globalTriIdx++;
            for(int k=0;k<3;k++){
                int ptIndex=tris[t][k];
                mesh.vertices[idx*3+0]=pWorld[ptIndex].x; mesh.vertices[idx*3+1]=pWorld[ptIndex].y; mesh.vertices[idx*3+2]=pWorld[ptIndex].z;
                mesh.normals[idx*3+0]=n.x; mesh.normals[idx*3+1]=n.y; mesh.normals[idx*3+2]=n.z;
                mesh.colors[idx*4+0]=faceCol.r; mesh.colors[idx*4+1]=faceCol.g; mesh.colors[idx*4+2]=faceCol.b; mesh.colors[idx*4+3]=255; idx++;
            }
        }
    }
    UploadMesh(&mesh,false); return mesh;
}

// ------------------------------------------------------------
// MAIN
// ------------------------------------------------------------
int main()
{
    InitWindow(1200, 800, "Reduced Draw Distance + Rock Culling");
    SetTargetFPS(60);
    DisableCursor();

    Camera3D camera = {0};
    camera.up = (Vector3){0,1,0};
    camera.fovy = 60;
    camera.projection = CAMERA_PERSPECTIVE;
    camera.position = (Vector3){0, 10, -10};

    Mesh shipMesh = CreateSolidShip();
    Model ship = LoadModelFromMesh(shipMesh);

    // SETUP ROCK
    Vector3 rockWorldPos = {15.0f, 0, 10.0f};
    rockWorldPos.y = GetTerrainHeight(rockWorldPos.x, rockWorldPos.z) + 0.5f;
    Matrix rockRot = MatrixRotateXYZ((Vector3){(float)GetRandomValue(0,360)*DEG2RAD, (float)GetRandomValue(0,360)*DEG2RAD, (float)GetRandomValue(0,360)*DEG2RAD});
    Mesh rockMesh = CreateRockMeshAndData(rockWorldPos, 2.5f, rockRot);
    Model rock = LoadModelFromMesh(rockMesh);
    rock.transform = MatrixIdentity(); 
    Vector3 rockDrawPos = {0,0,0}; 

    Vector3 shipPos = {0, 6, 0};
    Vector3 shipVel = {0, 0, 0};
    float shipPitch = 0.0f; float shipRoll = 0.0f; float shipYaw = 0.0f;
    int yawDirection = 1;

    const float GRAVITY = -4.0f;
    const float THRUST_POWER = 15.0f;
    const float DRAG_FACTOR = 0.985f; 
    const float CAM_FOLLOW_DIST = 9.0f; 
    const float CAM_HEIGHT_OFFSET = 4.0f;

    while (!WindowShouldClose())
    {
        float dt = GetFrameTime();

        // INPUT
        Vector2 mouseDelta = GetMouseDelta();
        shipPitch -= mouseDelta.y * 0.15f; 
        shipRoll -= mouseDelta.x * 0.15f; 
        if (fabs(mouseDelta.x) < 0.1f) shipRoll = Lerp(shipRoll, 0.0f, 1.0f * dt);
        shipPitch = Clamp(shipPitch, -85.0f, 85.0f);

        if (IsMouseButtonReleased(MOUSE_BUTTON_RIGHT)) yawDirection *= -1;
        if (IsMouseButtonDown(MOUSE_BUTTON_RIGHT)) shipYaw -= 120.0f * dt * (float)yawDirection;

        Matrix matRoll = MatrixRotateZ(DEG2RAD * -shipRoll);
        Matrix matPitch = MatrixRotateX(DEG2RAD * shipPitch);
        Matrix matYaw = MatrixRotateY(DEG2RAD * shipYaw);
        Matrix rot = MatrixMultiply(MatrixMultiply(matPitch, matRoll), matYaw);
        Vector3 shipForward = { rot.m8, rot.m9, rot.m10 }; 
        Vector3 shipUp = { rot.m4, rot.m5, rot.m6 };       

        // PHYSICS
        shipVel.y += GRAVITY * dt;
        if (IsMouseButtonDown(MOUSE_LEFT_BUTTON) || IsKeyDown(KEY_SPACE) || IsKeyDown(KEY_W)) {
            shipVel = Vector3Add(shipVel, Vector3Scale(shipUp, THRUST_POWER * dt));
            Vector3 engineNozzle = Vector3Add(shipPos, Vector3Scale(shipUp, -0.4f));
            SpawnThrustParticles(engineNozzle, shipUp);
        }
        shipVel = Vector3Scale(shipVel, DRAG_FACTOR);
        Vector3 nextPos = Vector3Add(shipPos, Vector3Scale(shipVel, dt));

        // COLLISION
        float worldH = GetWorldHeight(nextPos.x, nextPos.z);
        float softCeiling = worldH + 12.0f;
        if (nextPos.y > softCeiling) {
             shipVel.y -= (nextPos.y - softCeiling) * 2.0f * dt;
             nextPos = Vector3Add(shipPos, Vector3Scale(shipVel, dt));
        }
        if (nextPos.y < worldH + 0.5f) {
            nextPos.y = worldH + 0.5f;
            if (shipVel.y < 0) shipVel.y = 0;
            shipVel = Vector3Scale(shipVel, 0.9f); 
        }
        shipPos = nextPos;

        // CAMERA
        Vector3 camOffset = Vector3Scale(shipForward, -CAM_FOLLOW_DIST); 
        camOffset.y += CAM_HEIGHT_OFFSET;
        camera.position = Vector3Lerp(camera.position, Vector3Add(shipPos, camOffset), 5.0f * dt);
        float dist = Vector3Distance(camera.position, shipPos);
        if (dist > CAM_FOLLOW_DIST + 2.0f) camera.position = Vector3Add(shipPos, Vector3Scale(Vector3Normalize(Vector3Subtract(camera.position, shipPos)), CAM_FOLLOW_DIST + 2.0f));
        camera.target = shipPos;

        UpdateParticles(dt);

        // DRAW
        BeginDrawing();
            ClearBackground((Color){20, 20, 40, 255});
            BeginMode3D(camera);

                // Terrain Drawing (Using reduced RENDER_DISTANCE)
                int sx = (int)shipPos.x; int sz = (int)shipPos.z;
                for (int x = sx - RENDER_DISTANCE; x < sx + RENDER_DISTANCE; x++) {
                    for (int z = sz - RENDER_DISTANCE; z < sz + RENDER_DISTANCE; z++) {
                        float xf=(float)x, zf=(float)z;
                        Vector3 p0={xf,GetTerrainHeight(xf,zf),zf}, p1={xf+1,GetTerrainHeight(xf+1,zf),zf}, p2={xf,GetTerrainHeight(xf,zf+1),zf+1}, p3={xf+1,GetTerrainHeight(xf+1,zf+1),zf+1};
                        Color gc = (abs(x)%2 == abs(z)%2) ? DARKGREEN : (Color){0, 100, 40, 255};
                        DrawTriangle3D(p0, p2, p1, gc); DrawTriangle3D(p1, p2, p3, gc);
                    }
                }

                float shadowY = GetWorldHeight(shipPos.x, shipPos.z) + 0.05f;
                DrawCylinder((Vector3){shipPos.x, shadowY, shipPos.z}, 1.2f, 1.2f, 0.0f, 16, (Color){0,0,0,150});

                ship.transform = rot;
                DrawModel(ship, shipPos, 1.0f, WHITE);
                
                // Rock Drawing (Conditional based on distance, mimicking terrain culling)
                // Check if the rock's center is within the current rendering bounds
                bool rockInX = (rockWorldPos.x > sx - RENDER_DISTANCE && rockWorldPos.x < sx + RENDER_DISTANCE);
                bool rockInZ = (rockWorldPos.z > sz - RENDER_DISTANCE && rockWorldPos.z < sz + RENDER_DISTANCE);

                if (rockInX && rockInZ)
                {
                    rlDisableBackfaceCulling();
                        DrawModel(rock, rockDrawPos, 1.0f, WHITE);
                    rlEnableBackfaceCulling();
                }

                DrawParticles();

            EndMode3D();
            DrawFPS(10, 10);
            const char* dirText = (yawDirection == 1) ? "RIGHT" : "LEFT";
            if (IsMouseButtonDown(MOUSE_BUTTON_RIGHT)) DrawText(TextFormat("YAWING %s", dirText), 10, 40, 20, GREEN);
            else DrawText(TextFormat("Next Yaw: %s", dirText), 10, 40, 20, DARKGRAY);
        EndDrawing();
    }

    UnloadModel(ship);
    UnloadModel(rock);
    CloseWindow();
    return 0;
}