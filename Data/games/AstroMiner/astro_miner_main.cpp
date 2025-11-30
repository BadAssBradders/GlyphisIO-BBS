#include "raylib.h"
#include "raymath.h"
#include "rlgl.h"
#include <math.h>
#include <stdio.h>
#include <string.h>
#include <vector>
#include <cmath>

// Export functions for Python embedding
#ifdef __cplusplus
extern "C" {
#endif

// Global framebuffer (declared early, initialized later)
RenderTexture2D g_framebuffer = {0};
bool g_framebuffer_initialized = false;
unsigned char* g_frame_buffer_data = NULL;
int g_frame_buffer_size = 0;
bool g_game_initialized = false;

// Optimization: Render at half resolution
#define RENDER_WIDTH 600
#define RENDER_HEIGHT 400
#define VIRTUAL_WIDTH 1200
#define VIRTUAL_HEIGHT 800

// Input state tracking (for headless mode)
struct InputState {
    bool keys[512];  // KEY_* enum values
    bool keysPressed[512];  // One-time press events
    bool mouseButtons[8];  // MOUSE_BUTTON_* enum values
    bool mouseButtonsPressed[8];  // One-time press events
    bool mouseButtonsReleased[8];  // One-time release events
    Vector2 mousePosition;
    Vector2 mouseDelta;
    bool inputUpdated;  // Flag to clear pressed/released after one frame
} g_inputState = {0};

// C export functions for Python (use __cdecl calling convention)
__declspec(dllexport) __cdecl unsigned char* GetFrameBuffer() {
    if (!g_framebuffer_initialized || g_framebuffer.texture.id == 0) {
        return NULL;
    }
    
    // Read pixels from the render texture
    // NOTE: This is slow because it reads from GPU to CPU every frame
    // Reducing resolution to 600x400 (4x fewer pixels) speeds this up significantly
    Image img = LoadImageFromTexture(g_framebuffer.texture);
    
    // Allocate persistent buffer if needed
    int size = img.width * img.height * 4; // RGBA
    if (g_frame_buffer_size != size) {
        if (g_frame_buffer_data) {
            MemFree(g_frame_buffer_data);
        }
        g_frame_buffer_data = (unsigned char*)MemAlloc(size);
        g_frame_buffer_size = size;
    }
    
    // Copy pixel data to persistent buffer
    memcpy(g_frame_buffer_data, img.data, size);
    
    // Clean up temporary image
    UnloadImage(img);
    
    return g_frame_buffer_data;
}

__declspec(dllexport) __cdecl int GetWidth() {
    if (!g_framebuffer_initialized) return 0;
    return g_framebuffer.texture.width;
}

__declspec(dllexport) __cdecl int GetHeight() {
    if (!g_framebuffer_initialized) return 0;
    return g_framebuffer.texture.height;
}

// Forward declarations for functions defined later
__declspec(dllexport) __cdecl bool InitializeGame();
__declspec(dllexport) __cdecl void UpdateFrame();
__declspec(dllexport) __cdecl void SetKeyState(int key, bool down);
__declspec(dllexport) __cdecl void SetMouseButtonState(int button, bool down);
__declspec(dllexport) __cdecl void SetInputMousePosition(float x, float y);
__declspec(dllexport) __cdecl void SetMouseDelta(float dx, float dy);
__declspec(dllexport) __cdecl void ClearInputFrame();  // Call at end of frame to clear pressed/released flags

Mesh CreateStationMesh(); // Added forward decl


#ifdef __cplusplus
}
#endif

// ------------------------------------------------------------
// GAME STATES & SHARED DATA
// ------------------------------------------------------------
typedef enum {
    STATE_PROSPECT_MAP,
    STATE_LANDER,
    STATE_DRILLING,
    STATE_DEBRIS,
    STATE_DEPOT_SELECT,
    STATE_DEPOT_HOME,
    STATE_BAR,
    STATE_SHIPYARD,
    STATE_MARKET,
    STATE_LODGINGS
} GameState;

typedef struct {
    float fuel;
    float maxFuel;
    float hull;
    float maxHull;
    int credits;
    int cargoSpace;
    int cargoFilled;
    // Market Goods
    int iron;
    int gold;
} PlayerData;

// Global Player Instance
PlayerData G_Player = { 10.0f, 10.0f, 100.0f, 100.0f, 500, 20, 0, 0, 0 };

// Global game state variables (declared after types/constants)
GameState g_currentState = STATE_PROSPECT_MAP;
int g_menuSelection = 0;
Vector3 g_shipPos = {0, 60, 0};  // Will be initialized properly in InitializeGame()
Vector3 g_shipVel = {0, 0, 10};
float g_shipPitch = 0.0f;
float g_shipRoll = 0.0f;
float g_shipYaw = 0.0f;
int g_yawDirection = 1;
Camera3D g_camera = {0};
Model g_ship = {0};
Model g_rockModel = {0};
Texture2D scanlineTx = {0};
Texture2D guiHudTx = {0};

void DrawScanlines() {
    if (scanlineTx.id > 0) {
        DrawTexturePro(scanlineTx, 
            (Rectangle){0, 0, (float)scanlineTx.width, (float)scanlineTx.height}, 
            (Rectangle){0, 0, VIRTUAL_WIDTH, VIRTUAL_HEIGHT}, 
            (Vector2){0, 0}, 0.0f, (Color){255, 255, 255, 255});
    }
}

// ------------------------------------------------------------
// CONSTANTS (LANDER)
// ------------------------------------------------------------
#define NUM_ROCKS 1000
#define TRIS_PER_ROCK 36
#define ROCK_TRI_COUNT (NUM_ROCKS * TRIS_PER_ROCK)
#define PROSPECT_PERIMETER 120.0f 
#define RENDER_DISTANCE 15
#define CHUNK_SIZE 8 
#define CHUNKS_AXIS (int)((PROSPECT_PERIMETER * 2) / CHUNK_SIZE)
#define TOTAL_CHUNKS (CHUNKS_AXIS * CHUNKS_AXIS)
#define GRID_CELL_SIZE 16.0f
#define GRID_DIM (int)((PROSPECT_PERIMETER * 2.0f) / GRID_CELL_SIZE) + 2
#define MAX_ROCKS_PER_CELL 128

// Global arrays (declared after TOTAL_CHUNKS is defined)
Model g_chunkModels[TOTAL_CHUNKS] = {0};
Vector2 g_chunkCenters[TOTAL_CHUNKS] = {0};

// --- SHIP ENGINE STATS (UPGRADEABLE) ---
float SHIP_GRAVITY = -12.0f;
float SHIP_THRUST_POWER = 37.5f; 
float SHIP_DRAG_FACTOR = 0.985f;
float SHIP_FUEL_BURN_RATE = 1.0f / 10.0f; 

// ------------------------------------------------------------
// DATA STRUCTURES (LANDER)
// ------------------------------------------------------------
typedef struct Tri { Vector3 a; Vector3 b; Vector3 c; } Tri;
Tri G_RockTris[ROCK_TRI_COUNT];

struct RockInstance {
    Vector3 position;
    Vector3 axis;
    float angle;
    float scale;
    Color color;
};
RockInstance G_Rocks[NUM_ROCKS];

struct GridCell {
    int count;
    int rockIndices[MAX_ROCKS_PER_CELL];
};
GridCell G_CollisionGrid[GRID_DIM][GRID_DIM];

struct Particle { Vector3 pos; Vector3 vel; Color color; float life; bool onGround; };
#define MAX_PARTICLES 400
Particle particles[MAX_PARTICLES] = {0};

// ------------------------------------------------------------
// LANDER MATH & PHYSICS
// ------------------------------------------------------------
float GetTerrainHeight(float x, float z) {
    return 1.2f * sinf(x * 0.15f) + 0.8f * cosf(z * 0.12f) + 0.4f * sinf((x + z) * 0.08f);
}

bool GetHeightOnTriangle(Vector3 p1, Vector3 p2, Vector3 p3, float x, float z, float* outY) {
    float det = (p2.z - p3.z) * (p1.x - p3.x) + (p3.x - p2.x) * (p1.z - p3.z);
    if (fabs(det) < 0.0001f) return false;
    float l1 = ((p2.z - p3.z) * (x - p3.x) + (p3.x - p2.x) * (z - p3.z)) / det;
    float l2 = ((p3.z - p1.z) * (x - p3.x) + (p1.x - p3.x) * (z - p3.z)) / det;
    float l3 = 1.0f - l1 - l2;
    if (l1 >= 0.0f && l1 <= 1.0f && l2 >= 0.0f && l2 <= 1.0f && l3 >= 0.0f && l3 <= 1.0f) {
        *outY = l1 * p1.y + l2 * p2.y + l3 * p3.y;
        return true;
    }
    return false;
}

float GetWorldHeight(float x, float z) {
    float height = GetTerrainHeight(x, z);
    float offset = PROSPECT_PERIMETER;
    int cellX = (int)((x + offset) / GRID_CELL_SIZE);
    int cellZ = (int)((z + offset) / GRID_CELL_SIZE);

    if (cellX >= 0 && cellX < GRID_DIM && cellZ >= 0 && cellZ < GRID_DIM) {
        GridCell* cell = &G_CollisionGrid[cellX][cellZ];
        for(int i = 0; i < cell->count; i++) {
            int rockIdx = cell->rockIndices[i];
            int startTri = rockIdx * TRIS_PER_ROCK;
            int endTri = startTri + TRIS_PER_ROCK;
            for (int t = startTri; t < endTri; t++) {
                float triH;
                if (GetHeightOnTriangle(G_RockTris[t].a, G_RockTris[t].b, G_RockTris[t].c, x, z, &triH)) {
                    if (triH > height) height = triH;
                }
            }
        }
    }
    return height;
}

// ------------------------------------------------------------
// INITIALIZATION HELPERS
// ------------------------------------------------------------
void InitCollisionGrid() {
    for(int i=0; i<GRID_DIM; i++) for(int j=0; j<GRID_DIM; j++) G_CollisionGrid[i][j].count = 0;
    float offset = PROSPECT_PERIMETER;
    for (int r = 0; r < NUM_ROCKS; r++) {
        float radius = G_Rocks[r].scale * 1.5f;
        int startX = (int)((G_Rocks[r].position.x - radius + offset) / GRID_CELL_SIZE);
        int endX = (int)((G_Rocks[r].position.x + radius + offset) / GRID_CELL_SIZE);
        int startZ = (int)((G_Rocks[r].position.z - radius + offset) / GRID_CELL_SIZE);
        int endZ = (int)((G_Rocks[r].position.z + radius + offset) / GRID_CELL_SIZE);
        if (startX < 0) startX = 0; if (startX >= GRID_DIM) startX = GRID_DIM - 1;
        if (endX < 0) endX = 0; if (endX >= GRID_DIM) endX = GRID_DIM - 1;
        if (startZ < 0) startZ = 0; if (startZ >= GRID_DIM) startZ = GRID_DIM - 1;
        if (endZ < 0) endZ = 0; if (endZ >= GRID_DIM) endZ = GRID_DIM - 1;
        for (int x = startX; x <= endX; x++) {
            for (int z = startZ; z <= endZ; z++) {
                if (G_CollisionGrid[x][z].count < MAX_ROCKS_PER_CELL) {
                    G_CollisionGrid[x][z].rockIndices[G_CollisionGrid[x][z].count] = r;
                    G_CollisionGrid[x][z].count++;
                }
            }
        }
    }
}

// ------------------------------------------------------------
// RESTORED: MESH & PARTICLE HELPERS
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

Mesh CreateStationMesh() {
    // Legacy function, might not be needed if using StationViewport
    return (Mesh){0};
}

Mesh CreateBaseRockMesh() {
    float phi = 1.61803398875f; float inv = 1.0f/phi;
    Vector3 vLocal[20] = {{1,1,1},{1,1,-1},{1,-1,1},{1,-1,-1},{-1,1,1},{-1,1,-1},{-1,-1,1},{-1,-1,-1},{0,inv,phi},{0,inv,-phi},{0,-inv,phi},{0,-inv,-phi},{inv,phi,0},{inv,-phi,0},{-inv,phi,0},{-inv,-phi,0},{phi,0,inv},{phi,0,-inv},{-phi,0,inv},{-phi,0,-inv}};
    int faces[12][5] = {{0,16,2,10,8},{0,8,4,14,12},{16,17,1,12,0},{1,9,11,3,17},{1,12,14,5,9},{2,13,15,6,10},{13,3,11,7,15},{4,8,10,6,18},{14,4,18,19,5},{5,19,7,11,9},{15,7,19,18,6},{2,16,17,3,13}};
    Color rockPalette[12] = {{80,80,80,255},{100,100,105,255},{90,85,80,255},{70,70,70,255},{60,60,65,255},{110,110,110,255},{55,55,55,255},{75,70,65,255},{65,65,65,255},{85,85,90,255},{45,45,50,255},{95,95,95,255}};
    
    Mesh mesh = {0}; mesh.triangleCount=36; mesh.vertexCount=mesh.triangleCount*3;
    mesh.vertices=(float*)MemAlloc(mesh.vertexCount*3*sizeof(float));
    mesh.normals=(float*)MemAlloc(mesh.vertexCount*3*sizeof(float));
    mesh.colors=(unsigned char*)MemAlloc(mesh.vertexCount*4);
    
    int idx=0;
    for(int f=0;f<12;f++){
        Color faceCol=rockPalette[f];
        Vector3 pLocal[5]; for(int i=0;i<5;i++) pLocal[i]=vLocal[faces[f][i]];
        Vector3 n=Vector3Normalize(Vector3CrossProduct(Vector3Subtract(pLocal[1],pLocal[0]), Vector3Subtract(pLocal[2],pLocal[0])));
        int tris[3][3]={{0,1,2},{0,2,3},{0,3,4}};
        for(int t=0;t<3;t++){
            for(int k=0;k<3;k++){
                int ptIndex=tris[t][k];
                mesh.vertices[idx*3+0]=pLocal[ptIndex].x; mesh.vertices[idx*3+1]=pLocal[ptIndex].y; mesh.vertices[idx*3+2]=pLocal[ptIndex].z;
                mesh.normals[idx*3+0]=n.x; mesh.normals[idx*3+1]=n.y; mesh.normals[idx*3+2]=n.z;
                mesh.colors[idx*4+0]=faceCol.r; mesh.colors[idx*4+1]=faceCol.g; mesh.colors[idx*4+2]=faceCol.b; mesh.colors[idx*4+3]=255; idx++;
            }
        }
    }
    UploadMesh(&mesh,false); return mesh;
}

void GenerateRocksAndCollision() {
    float phi = 1.61803398875f; float inv = 1.0f/phi;
    Vector3 vLocal[20] = {{1,1,1},{1,1,-1},{1,-1,1},{1,-1,-1},{-1,1,1},{-1,1,-1},{-1,-1,1},{-1,-1,-1},{0,inv,phi},{0,inv,-phi},{0,-inv,phi},{0,-inv,-phi},{inv,phi,0},{inv,-phi,0},{-inv,phi,0},{-inv,-phi,0},{phi,0,inv},{phi,0,-inv},{-phi,0,inv},{-phi,0,-inv}};
    int faces[12][5] = {{0,16,2,10,8},{0,8,4,14,12},{16,17,1,12,0},{1,9,11,3,17},{1,12,14,5,9},{2,13,15,6,10},{13,3,11,7,15},{4,8,10,6,18},{14,4,18,19,5},{5,19,7,11,9},{15,7,19,18,6},{2,16,17,3,13}};
    int globalTriIdx = 0;
    int limit = (int)PROSPECT_PERIMETER;
    Vector3 clusterCenter = {0};

    for (int r = 0; r < NUM_ROCKS; r++) {
        float scale = (float)GetRandomValue(50, 300) / 100.0f;
        float rx, rz;
        if (r % 2 == 0) { rx = (float)GetRandomValue(-limit, limit); rz = (float)GetRandomValue(-limit, limit); clusterCenter = (Vector3){rx, 0, rz}; } 
        else { float angle = (float)GetRandomValue(0, 360) * DEG2RAD; float dist = (float)GetRandomValue(20, 60) / 10.0f; rx = clusterCenter.x + cosf(angle) * dist; rz = clusterCenter.z + sinf(angle) * dist; if(rx > limit) rx = limit; if(rx < -limit) rx = -limit; if(rz > limit) rz = limit; if(rz < -limit) rz = -limit; }
        
        G_Rocks[r].position = (Vector3){rx, GetTerrainHeight(rx, rz) + (0.2f * scale), rz};
        G_Rocks[r].scale = scale;
        G_Rocks[r].axis = Vector3Normalize((Vector3){(float)GetRandomValue(-1,1),(float)GetRandomValue(-1,1),(float)GetRandomValue(-1,1)});
        G_Rocks[r].angle = (float)GetRandomValue(0, 360);
        int tintVal = GetRandomValue(200, 255);
        G_Rocks[r].color = (Color){(unsigned char)tintVal, (unsigned char)tintVal, (unsigned char)tintVal, 255};

        Matrix matScale = MatrixScale(scale, scale, scale);
        Matrix matRot = MatrixRotate(G_Rocks[r].axis, G_Rocks[r].angle * DEG2RAD);
        Matrix matTrans = MatrixTranslate(G_Rocks[r].position.x, G_Rocks[r].position.y, G_Rocks[r].position.z);
        Matrix matWorld = MatrixMultiply(MatrixMultiply(matScale, matRot), matTrans);

        for(int f=0;f<12;f++){
            Vector3 pWorld[5]; for(int i=0;i<5;i++) pWorld[i] = Vector3Transform(vLocal[faces[f][i]], matWorld);
            int tris[3][3]={{0,1,2},{0,2,3},{0,3,4}};
            for(int t=0;t<3;t++){
                G_RockTris[globalTriIdx].a = pWorld[tris[t][0]]; G_RockTris[globalTriIdx].b = pWorld[tris[t][1]]; G_RockTris[globalTriIdx].c = pWorld[tris[t][2]]; globalTriIdx++;
            }
        }
    }
}

Mesh CreateTerrainChunk(float startX, float startZ, float size) {
    Mesh mesh = { 0 };
    int range = (int)size;
    
    mesh.triangleCount = range * range * 2;
    mesh.vertexCount = mesh.triangleCount * 3;
    
    mesh.vertices = (float *)MemAlloc(mesh.vertexCount * 3 * sizeof(float));
    mesh.normals = (float *)MemAlloc(mesh.vertexCount * 3 * sizeof(float));
    mesh.colors = (unsigned char *)MemAlloc(mesh.vertexCount * 4 * sizeof(unsigned char));

    int vCounter = 0;
    Color grey1 = {80, 80, 80, 255};
    Color grey2 = {50, 50, 50, 255};

    for (int z = 0; z < range; z++) {
        for (int x = 0; x < range; x++) {
            float xf = startX + (float)x; 
            float zf = startZ + (float)z;

            // Heights
            float y0 = GetTerrainHeight(xf, zf);
            float y1 = GetTerrainHeight(xf, zf + 1);
            float y2 = GetTerrainHeight(xf + 1, zf + 1);
            float y3 = GetTerrainHeight(xf + 1, zf);

            // Vertices
            Vector3 vA = { xf, y0, zf };
            Vector3 vB = { xf, y1, zf + 1 };
            Vector3 vC = { xf + 1, y2, zf + 1 };
            Vector3 vD = { xf + 1, y3, zf };

            // Color Logic
            int wx = (int)xf; int wz = (int)zf;
            Color gc = (abs(wx) % 2 == abs(wz) % 2) ? grey1 : grey2;

            // Tri 1
            mesh.vertices[vCounter*3+0] = vA.x; mesh.vertices[vCounter*3+1] = vA.y; mesh.vertices[vCounter*3+2] = vA.z;
            mesh.normals[vCounter*3+0] = 0.0f; mesh.normals[vCounter*3+1] = 1.0f; mesh.normals[vCounter*3+2] = 0.0f; 
            mesh.colors[vCounter*4+0] = gc.r; mesh.colors[vCounter*4+1] = gc.g; mesh.colors[vCounter*4+2] = gc.b; mesh.colors[vCounter*4+3] = gc.a;
            vCounter++;
            mesh.vertices[vCounter*3+0] = vB.x; mesh.vertices[vCounter*3+1] = vB.y; mesh.vertices[vCounter*3+2] = vB.z;
            mesh.normals[vCounter*3+0] = 0.0f; mesh.normals[vCounter*3+1] = 1.0f; mesh.normals[vCounter*3+2] = 0.0f;
            mesh.colors[vCounter*4+0] = gc.r; mesh.colors[vCounter*4+1] = gc.g; mesh.colors[vCounter*4+2] = gc.b; mesh.colors[vCounter*4+3] = gc.a;
            vCounter++;
            mesh.vertices[vCounter*3+0] = vC.x; mesh.vertices[vCounter*3+1] = vC.y; mesh.vertices[vCounter*3+2] = vC.z;
            mesh.normals[vCounter*3+0] = 0.0f; mesh.normals[vCounter*3+1] = 1.0f; mesh.normals[vCounter*3+2] = 0.0f;
            mesh.colors[vCounter*4+0] = gc.r; mesh.colors[vCounter*4+1] = gc.g; mesh.colors[vCounter*4+2] = gc.b; mesh.colors[vCounter*4+3] = gc.a;
            vCounter++;

            // Tri 2
            mesh.vertices[vCounter*3+0] = vA.x; mesh.vertices[vCounter*3+1] = vA.y; mesh.vertices[vCounter*3+2] = vA.z;
            mesh.normals[vCounter*3+0] = 0.0f; mesh.normals[vCounter*3+1] = 1.0f; mesh.normals[vCounter*3+2] = 0.0f;
            mesh.colors[vCounter*4+0] = gc.r; mesh.colors[vCounter*4+1] = gc.g; mesh.colors[vCounter*4+2] = gc.b; mesh.colors[vCounter*4+3] = gc.a;
            vCounter++;
            mesh.vertices[vCounter*3+0] = vC.x; mesh.vertices[vCounter*3+1] = vC.y; mesh.vertices[vCounter*3+2] = vC.z;
            mesh.normals[vCounter*3+0] = 0.0f; mesh.normals[vCounter*3+1] = 1.0f; mesh.normals[vCounter*3+2] = 0.0f;
            mesh.colors[vCounter*4+0] = gc.r; mesh.colors[vCounter*4+1] = gc.g; mesh.colors[vCounter*4+2] = gc.b; mesh.colors[vCounter*4+3] = gc.a;
            vCounter++;
            mesh.vertices[vCounter*3+0] = vD.x; mesh.vertices[vCounter*3+1] = vD.y; mesh.vertices[vCounter*3+2] = vD.z;
            mesh.normals[vCounter*3+0] = 0.0f; mesh.normals[vCounter*3+1] = 1.0f; mesh.normals[vCounter*3+2] = 0.0f;
            mesh.colors[vCounter*4+0] = gc.r; mesh.colors[vCounter*4+1] = gc.g; mesh.colors[vCounter*4+2] = gc.b; mesh.colors[vCounter*4+3] = gc.a;
            vCounter++;
        }
    }
    UploadMesh(&mesh, false);
    return mesh;
}

void DrawPerimeterBorder(Vector3 shipPos) {
    Color col = {0, 255, 255, 128}; 
    float halfWidth = 1.0f; 
    float step = 2.0f; 
    float limit = PROSPECT_PERIMETER;
    float minRenderX = shipPos.x - RENDER_DISTANCE;
    float maxRenderX = shipPos.x + RENDER_DISTANCE;
    float minRenderZ = shipPos.z - RENDER_DISTANCE;
    float maxRenderZ = shipPos.z + RENDER_DISTANCE;

    rlBegin(RL_QUADS);
    rlColor4ub(col.r, col.g, col.b, col.a);

    float startZ = fmaxf(-limit, minRenderZ);
    float endZ   = fminf(limit, maxRenderZ);
    if (startZ < endZ) {
        if (-limit >= minRenderX && -limit <= maxRenderX) {
            for (float z = startZ; z < endZ; z += step) {
                float zNext = (z + step > endZ) ? endZ : z + step;
                float h1 = GetTerrainHeight(-limit - halfWidth, z);
                float h2 = GetTerrainHeight(-limit + halfWidth, z);
                float h3 = GetTerrainHeight(-limit + halfWidth, zNext);
                float h4 = GetTerrainHeight(-limit - halfWidth, zNext);
                rlVertex3f(-limit - halfWidth, h1 + 0.1f, z);
                rlVertex3f(-limit + halfWidth, h2 + 0.1f, z);
                rlVertex3f(-limit + halfWidth, h3 + 0.1f, zNext);
                rlVertex3f(-limit - halfWidth, h4 + 0.1f, zNext);
            }
        }
        if (limit >= minRenderX && limit <= maxRenderX) {
            for (float z = startZ; z < endZ; z += step) {
                float zNext = (z + step > endZ) ? endZ : z + step;
                float h1 = GetTerrainHeight(limit - halfWidth, z);
                float h2 = GetTerrainHeight(limit + halfWidth, z);
                float h3 = GetTerrainHeight(limit + halfWidth, zNext);
                float h4 = GetTerrainHeight(limit - halfWidth, zNext);
                rlVertex3f(limit - halfWidth, h1 + 0.1f, z);
                rlVertex3f(limit + halfWidth, h2 + 0.1f, z);
                rlVertex3f(limit + halfWidth, h3 + 0.1f, zNext);
                rlVertex3f(limit - halfWidth, h4 + 0.1f, zNext);
            }
        }
    }

    float startX = fmaxf(-limit, minRenderX);
    float endX   = fminf(limit, maxRenderX);
    if (startX < endX) {
        if (-limit >= minRenderZ && -limit <= maxRenderZ) {
            for (float x = startX; x < endX; x += step) {
                float xNext = (x + step > endX) ? endX : x + step;
                float h1 = GetTerrainHeight(x, -limit - halfWidth);
                float h2 = GetTerrainHeight(x, -limit + halfWidth);
                float h3 = GetTerrainHeight(xNext, -limit + halfWidth);
                float h4 = GetTerrainHeight(xNext, -limit - halfWidth);
                rlVertex3f(x, h1 + 0.1f, -limit - halfWidth);
                rlVertex3f(x, h2 + 0.1f, -limit + halfWidth);
                rlVertex3f(xNext, h3 + 0.1f, -limit + halfWidth);
                rlVertex3f(xNext, h4 + 0.1f, -limit - halfWidth);
            }
        }
        if (limit >= minRenderZ && limit <= maxRenderZ) {
            for (float x = startX; x < endX; x += step) {
                float xNext = (x + step > endX) ? endX : x + step;
                float h1 = GetTerrainHeight(x, limit - halfWidth);
                float h2 = GetTerrainHeight(x, limit + halfWidth);
                float h3 = GetTerrainHeight(xNext, limit + halfWidth);
                float h4 = GetTerrainHeight(xNext, limit - halfWidth);
                rlVertex3f(x, h1 + 0.1f, limit - halfWidth);
                rlVertex3f(x, h2 + 0.1f, limit + halfWidth);
                rlVertex3f(xNext, h3 + 0.1f, limit + halfWidth);
                rlVertex3f(xNext, h4 + 0.1f, limit - halfWidth);
            }
        }
    }
    rlEnd();
}

void DrawProjectedShadow(Vector3 shipPos) {
    float groundY = GetWorldHeight(shipPos.x, shipPos.z);
    float altitude = shipPos.y - groundY;
    if (altitude < 0) altitude = 0;
    float radius = 0.6f + (altitude * 0.075f);
    if (radius > 2.5f) radius = 2.5f;
    float heightFactor = Clamp(altitude / 12.0f, 0.0f, 1.0f);
    unsigned char alpha = (unsigned char)Lerp(220, 60, heightFactor);
    unsigned char greyVal = (unsigned char)Lerp(0, 80, heightFactor);
    Color shadowCol = (Color){greyVal, greyVal, greyVal, alpha}; 
    float step = 0.5f; 
    rlBegin(RL_QUADS);
    rlColor4ub(shadowCol.r, shadowCol.g, shadowCol.b, shadowCol.a);
    float startX = shipPos.x - radius; float endX = shipPos.x + radius;
    float startZ = shipPos.z - radius; float endZ = shipPos.z + radius;
    for (float x = startX; x < endX; x += step) {
        for (float z = startZ; z < endZ; z += step) {
            float dx = x - shipPos.x; float dz = z - shipPos.z;
            if ((dx*dx + dz*dz) > (radius*radius)) continue;
            float lift = 0.04f;
            float y0 = GetWorldHeight(x, z) + lift;
            float y1 = GetWorldHeight(x, z + step) + lift;
            float y2 = GetWorldHeight(x + step, z + step) + lift;
            float y3 = GetWorldHeight(x + step, z) + lift;
            rlVertex3f(x, y0, z);
            rlVertex3f(x, y1, z + step);
            rlVertex3f(x + step, y2, z + step);
            rlVertex3f(x + step, y3, z);
        }
    }
    rlEnd();
}

Color thrusterPalette[10] = { WHITE, WHITE, RAYWHITE, (Color){0, 255, 255, 255}, (Color){100, 255, 255, 255}, SKYBLUE, WHITE, ORANGE, RED, GOLD };

void SpawnThrustParticles(Vector3 nozzlePos, Vector3 shipUpVector) {
    Vector3 ejectDir = Vector3Scale(shipUpVector, -1.0f);
    int particlesPerFrame = 4;
    for (int k = 0; k < particlesPerFrame; k++) {
        for (int i = 0; i < MAX_PARTICLES; i++) {
            if (particles[i].life <= 0) {
                particles[i].pos = nozzlePos; particles[i].onGround = false;
                Vector3 noise = { (GetRandomValue(-50,50))/100.0f, (GetRandomValue(-50,50))/100.0f, (GetRandomValue(-50,50))/100.0f };
                Vector3 spreadDir = Vector3Add(ejectDir, Vector3Scale(noise, 0.6f));
                particles[i].vel = Vector3Scale(spreadDir, (float)GetRandomValue(75, 150) / 10.0f);
                particles[i].color = thrusterPalette[GetRandomValue(0,9)];
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
            if (particles[i].life < 0.5f) {
                float alpha = (particles[i].life / 0.5f);
                particles[i].color.a = (unsigned char)(255 * alpha);
            }
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
    float pSize = 0.064f; 
    for (int i = 0; i < MAX_PARTICLES; i++) if (particles[i].life > 0)
        DrawCube(particles[i].pos, pSize, pSize, pSize, particles[i].color);
}

// ------------------------------------------------------------
// HELPER: STATE RESET
// ------------------------------------------------------------
void ResetState(GameState* currentState, int* menuSelection, GameState newState) {
    *currentState = newState;
    *menuSelection = 0;
}

// ------------------------------------------------------------
// INPUT WRAPPER FUNCTIONS (use custom input state instead of raylib)
// Must be defined before Draw functions that use them
// ------------------------------------------------------------
static bool CustomIsKeyDown(int key) {
    if (key >= 0 && key < 512) {
        return g_inputState.keys[key];
    }
    return false;
}

static bool CustomIsKeyPressed(int key) {
    if (key >= 0 && key < 512) {
        return g_inputState.keysPressed[key];
    }
    return false;
}

static bool CustomIsMouseButtonDown(int button) {
    if (button >= 0 && button < 8) {
        return g_inputState.mouseButtons[button];
    }
    return false;
}

static bool CustomIsMouseButtonPressed(int button) {
    if (button >= 0 && button < 8) {
        return g_inputState.mouseButtonsPressed[button];
    }
    return false;
}

static bool CustomIsMouseButtonReleased(int button) {
    if (button >= 0 && button < 8) {
        return g_inputState.mouseButtonsReleased[button];
    }
    return false;
}

static Vector2 CustomGetMouseDelta() {
    return g_inputState.mouseDelta;
}

static Vector2 CustomGetMousePosition() {
    return g_inputState.mousePosition;
}

// ------------------------------------------------------------
// INPUT SETTING FUNCTIONS (called from Python)
// ------------------------------------------------------------
// NOTE: These are defined outside extern "C" because they implement forward declarations
// that were inside extern "C". The linker should match them.
// If not, we can wrap them in extern "C" too.

__declspec(dllexport) __cdecl void SetKeyState(int key, bool down) {
    static int key_event_count = 0;
    if (key >= 0 && key < 512) {
        bool wasDown = g_inputState.keys[key];
        g_inputState.keys[key] = down;
        // Set pressed flag if just pressed (wasn't down, now is)
        if (!wasDown && down) {
            g_inputState.keysPressed[key] = true;
            key_event_count++;
        }
    }
}

__declspec(dllexport) __cdecl void SetMouseButtonState(int button, bool down) {
    if (button >= 0 && button < 8) {
        bool wasDown = g_inputState.mouseButtons[button];
        g_inputState.mouseButtons[button] = down;
        // Set pressed/released flags
        if (!wasDown && down) {
            g_inputState.mouseButtonsPressed[button] = true;
        } else if (wasDown && !down) {
            g_inputState.mouseButtonsReleased[button] = true;
        }
    }
}

__declspec(dllexport) __cdecl void SetInputMousePosition(float x, float y) {
    g_inputState.mousePosition = (Vector2){x, y};
}

__declspec(dllexport) __cdecl void SetMouseDelta(float dx, float dy) {
    g_inputState.mouseDelta = (Vector2){dx, dy};
}

__declspec(dllexport) __cdecl void ClearInputFrame() {
    // Clear one-time press/release flags at end of frame
    memset(g_inputState.keysPressed, 0, sizeof(g_inputState.keysPressed));
    memset(g_inputState.mouseButtonsPressed, 0, sizeof(g_inputState.mouseButtonsPressed));
    memset(g_inputState.mouseButtonsReleased, 0, sizeof(g_inputState.mouseButtonsReleased));
}

// ------------------------------------------------------------
// DRAWING HELPERS (Shared UI)
// ------------------------------------------------------------
void DrawRetroWindow(const char* title, int x, int y, int w, int h) {
    Color panelFill = {10, 15, 30, 240};
    Color border = {0, 255, 255, 255};
    DrawRectangle(x, y, w, h, panelFill);
    DrawRectangleLines(x, y, w, h, border);
    DrawRectangle(x, y, w, 30, border);
    DrawText(title, x + 10, y + 5, 20, BLACK);
}

// KEYBOARD NAVIGATION BUTTON
bool DrawButton(const char* text, int x, int y, int w, int h, bool selected) {
    Color fill = selected ? (Color){0, 100, 100, 255} : (Color){0, 40, 40, 255};
    Color border = selected ? WHITE : (Color){0, 255, 255, 255};
    
    DrawRectangle(x, y, w, h, fill);
    DrawRectangleLines(x, y, w, h, border);
    int textW = MeasureText(text, 20);
    DrawText(text, x + (w-textW)/2, y + (h-20)/2, 20, border);
    
    if (selected && (CustomIsKeyPressed(KEY_ENTER) || CustomIsKeyPressed(KEY_SPACE))) return true;
    return false;
}

// ------------------------------------------------------------
// STATION VIEWPORT MODULE
// ------------------------------------------------------------

enum StationType {
    STATION_ALPHA,  // Torus
    STATION_BETA,   // Icosahedron
    STATION_GAMMA,  // Torus (Variant)
    STATION_DELTA   // Icosahedron (Variant)
};

struct Star {
    float x;
    float y;
    float z;        // Depth (0 = far, 1 = close)
    float speed;
    Color color;
};

// MESH GENERATION FUNCTIONS (ADAPTED FROM SHAPES_IN_SPACE)

Mesh GenFlatShadedTorus(float radius, float size, int radSeg, int sides)
{
    Mesh mesh = { 0 };
    
    int numFaces = radSeg * sides;
    int numVertices = numFaces * 4; // 4 vertices per face (quads)
    int numIndices = numFaces * 6;  // 6 indices per face (2 triangles)
    
    mesh.vertexCount = numVertices;
    mesh.triangleCount = numFaces * 2;
    
    mesh.vertices = (float *)MemAlloc(mesh.vertexCount * 3 * sizeof(float));
    mesh.normals = (float *)MemAlloc(mesh.vertexCount * 3 * sizeof(float));
    mesh.texcoords = (float *)MemAlloc(mesh.vertexCount * 2 * sizeof(float));
    mesh.colors = (unsigned char *)MemAlloc(mesh.vertexCount * 4 * sizeof(unsigned char));
    mesh.indices = (unsigned short *)MemAlloc(numIndices * sizeof(unsigned short));
    
    int vIndex = 0;
    int iIndex = 0;
    
    for (int i = 0; i < radSeg; i++)
    {
        for (int j = 0; j < sides; j++)
        {
            float v = (float)j / sides * PI * 2.0f;
            float sinV = sinf(v); 
            
            Color faceColor;
            if (sinV > 0.2f)       faceColor = LIGHTGRAY; 
            else if (sinV < -0.2f) faceColor = DARKGRAY;  
            else                   faceColor = GRAY;      
            
            int iNext = (i + 1) % radSeg;
            int jNext = (j + 1) % sides;
            
            auto GetPos = [&](int seg, int side) -> Vector3 {
                float u = (float)seg / radSeg * PI * 2.0f;
                float v = (float)side / sides * PI * 2.0f;
                
                float x = (radius + size * cosf(v)) * cosf(u);
                float y = size * sinf(v); 
                float z = (radius + size * cosf(v)) * sinf(u);
                return (Vector3){x, y, z};
            };
            
            Vector3 p0 = GetPos(i, j);
            Vector3 p1 = GetPos(iNext, j);
            Vector3 p2 = GetPos(iNext, jNext);
            Vector3 p3 = GetPos(i, jNext);
            
            Vector3 normal = Vector3Normalize(Vector3CrossProduct(Vector3Subtract(p1, p0), Vector3Subtract(p2, p0))); 
            
            auto AddVertex = [&](Vector3 p) {
                mesh.vertices[vIndex*3] = p.x;
                mesh.vertices[vIndex*3+1] = p.y;
                mesh.vertices[vIndex*3+2] = p.z;
                
                mesh.normals[vIndex*3] = normal.x;
                mesh.normals[vIndex*3+1] = normal.y;
                mesh.normals[vIndex*3+2] = normal.z;
                
                mesh.colors[vIndex*4] = faceColor.r;
                mesh.colors[vIndex*4+1] = faceColor.g;
                mesh.colors[vIndex*4+2] = faceColor.b;
                mesh.colors[vIndex*4+3] = faceColor.a;
                
                mesh.texcoords[vIndex*2] = 0.0f;
                mesh.texcoords[vIndex*2+1] = 0.0f;
                
                vIndex++;
            };
            
            int baseIndex = vIndex;
            AddVertex(p0); AddVertex(p1); AddVertex(p2); AddVertex(p3);
            
            mesh.indices[iIndex++] = baseIndex;
            mesh.indices[iIndex++] = baseIndex + 1;
            mesh.indices[iIndex++] = baseIndex + 2;
            
            mesh.indices[iIndex++] = baseIndex;
            mesh.indices[iIndex++] = baseIndex + 2;
            mesh.indices[iIndex++] = baseIndex + 3;
        }
    }
    
    UploadMesh(&mesh, false);
    return mesh;
}

Mesh GenFlatShadedIcosahedron(float scale)
{
    Mesh mesh = { 0 };
    float phi = (1.0f + sqrtf(5.0f)) / 2.0f;
    Vector3 verts[12] = {
        {-1,  phi, 0}, { 1,  phi, 0}, {-1, -phi, 0}, { 1, -phi, 0},
        { 0, -1,  phi}, { 0,  1,  phi}, { 0, -1, -phi}, { 0,  1, -phi},
        { phi, 0, -1}, { phi, 0,  1}, {-phi, 0, -1}, {-phi, 0,  1}
    };
    int indices[20][3] = {
        {0, 11, 5}, {0, 5, 1}, {0, 1, 7}, {0, 7, 10}, {0, 10, 11},
        {1, 5, 9}, {5, 11, 4}, {11, 10, 2}, {10, 7, 6}, {7, 1, 8},
        {3, 9, 4}, {3, 4, 2}, {3, 2, 6}, {3, 6, 8}, {3, 8, 9},
        {4, 9, 5}, {2, 4, 11}, {6, 2, 10}, {8, 6, 7}, {9, 8, 1}
    };
    
    int numFaces = 20;
    mesh.vertexCount = numFaces * 3;
    mesh.triangleCount = numFaces;
    
    mesh.vertices = (float *)MemAlloc(mesh.vertexCount * 3 * sizeof(float));
    mesh.normals = (float *)MemAlloc(mesh.vertexCount * 3 * sizeof(float));
    mesh.texcoords = (float *)MemAlloc(mesh.vertexCount * 2 * sizeof(float));
    mesh.colors = (unsigned char *)MemAlloc(mesh.vertexCount * 4 * sizeof(unsigned char));
    mesh.indices = (unsigned short *)MemAlloc(mesh.vertexCount * sizeof(unsigned short));
    
    int vIndex = 0;
    int iIndex = 0;
    
    for (int i = 0; i < numFaces; i++)
    {
        Vector3 p0 = verts[indices[i][0]];
        Vector3 p1 = verts[indices[i][1]];
        Vector3 p2 = verts[indices[i][2]];
        
        p0 = Vector3Scale(p0, scale);
        p1 = Vector3Scale(p1, scale);
        p2 = Vector3Scale(p2, scale);
        
        Vector3 edge1 = Vector3Subtract(p1, p0);
        Vector3 edge2 = Vector3Subtract(p2, p0);
        Vector3 normal = Vector3Normalize(Vector3CrossProduct(edge1, edge2));
        
        Vector3 center = Vector3Scale(Vector3Add(Vector3Add(p0, p1), p2), 1.0f/3.0f);
        float normalizedY = center.y / (scale * phi); 
        
        Color faceColor;
        if (normalizedY > 0.25f)       faceColor = LIGHTGRAY; 
        else if (normalizedY < -0.25f) faceColor = DARKGRAY;  
        else                           faceColor = GRAY;      
        
        auto AddVertex = [&](Vector3 p) {
            mesh.vertices[vIndex*3] = p.x;
            mesh.vertices[vIndex*3+1] = p.y;
            mesh.vertices[vIndex*3+2] = p.z;
            
            mesh.normals[vIndex*3] = normal.x;
            mesh.normals[vIndex*3+1] = normal.y;
            mesh.normals[vIndex*3+2] = normal.z;
            
            mesh.colors[vIndex*4] = faceColor.r;
            mesh.colors[vIndex*4+1] = faceColor.g;
            mesh.colors[vIndex*4+2] = faceColor.b;
            mesh.colors[vIndex*4+3] = faceColor.a;
            
            mesh.texcoords[vIndex*2] = 0.0f;
            mesh.texcoords[vIndex*2+1] = 0.0f;
            
            mesh.indices[iIndex++] = vIndex;
            vIndex++;
        };
        
        AddVertex(p0); AddVertex(p1); AddVertex(p2);
    }
    
    UploadMesh(&mesh, false);
    return mesh;
}

class StationViewport {
private:
    RenderTexture2D viewTarget;
    Camera3D camera;
    Shader shader;
    
    Mesh meshTorus;
    Model modelTorus;
    Mesh meshIco;
    Model modelIco;
    
    std::vector<Star> stars;
    float rotation;
    
    // Shader Uniform Locations
    int locViewPos;
    int locAmbient;
    int locLightPos[5];
    int locLightColor[5];
    int locLightDir5;
    int locLightCut5;

public:
    StationViewport() : rotation(0.0f), locViewPos(-1) {
        camera = { 0 };
        shader = { 0 };
        viewTarget = { 0 };
    }

    void Init(int width, int height) {
        // 1. Create Framebuffer (use low res for speed)
        viewTarget = LoadRenderTexture(width, height);
        
        // 2. Load dedicated shaders (renamed to lighting.vs/fs per user request)
        // Use path relative to the DLL/Executable
        shader = LoadShader("lighting.vs", "lighting.fs");
        if (shader.id == 0) {
            // Fallback path
            shader = LoadShader("Data/games/AstroMiner/lighting.vs", "Data/games/AstroMiner/lighting.fs");
        }
        
        // Get Locations
        locViewPos = GetShaderLocation(shader, "viewPos");
        locAmbient = GetShaderLocation(shader, "ambientColor");
        
        locLightPos[0] = GetShaderLocation(shader, "lightPos");
        locLightColor[0] = GetShaderLocation(shader, "lightColor");
        locLightPos[1] = GetShaderLocation(shader, "lightPos2");
        locLightColor[1] = GetShaderLocation(shader, "lightColor2");
        locLightPos[2] = GetShaderLocation(shader, "lightPos3");
        locLightColor[2] = GetShaderLocation(shader, "lightColor3");
        locLightPos[3] = GetShaderLocation(shader, "lightPos4");
        locLightColor[3] = GetShaderLocation(shader, "lightColor4");
        
        locLightPos[4] = GetShaderLocation(shader, "lightPos5");
        locLightColor[4] = GetShaderLocation(shader, "lightColor5");
        locLightDir5 = GetShaderLocation(shader, "lightDir5");
        locLightCut5 = GetShaderLocation(shader, "lightCutoff5");
        
        // Set Default Light Values
        float ambient[] = { 0.1f, 0.1f, 0.1f };
        SetShaderValue(shader, locAmbient, ambient, SHADER_UNIFORM_VEC3);
        
        // Lights setup similar to source
        float lColor1[] = { 0.8f, 0.8f, 0.8f }; Vector3 lPos1 = { 0.0f, 50.0f, 0.0f };
        SetShaderValue(shader, locLightColor[0], lColor1, SHADER_UNIFORM_VEC3);
        SetShaderValue(shader, locLightPos[0], &lPos1, SHADER_UNIFORM_VEC3);

        float lColor2[] = { 0.4f, 0.4f, 0.4f }; Vector3 lPos2 = { -50.0f, 0.0f, 0.0f };
        SetShaderValue(shader, locLightColor[1], lColor2, SHADER_UNIFORM_VEC3);
        SetShaderValue(shader, locLightPos[1], &lPos2, SHADER_UNIFORM_VEC3);
        
        float lColor3[] = { 1.0f, 1.0f, 1.0f }; Vector3 lPos3 = { -40.0f, 40.0f, 20.0f };
        SetShaderValue(shader, locLightColor[2], lColor3, SHADER_UNIFORM_VEC3);
        SetShaderValue(shader, locLightPos[2], &lPos3, SHADER_UNIFORM_VEC3);
        
        float lColor4[] = { 0.8f, 0.9f, 1.0f }; Vector3 lPos4 = { 0.0f, 100.0f, 0.0f };
        SetShaderValue(shader, locLightColor[3], lColor4, SHADER_UNIFORM_VEC3);
        SetShaderValue(shader, locLightPos[3], &lPos4, SHADER_UNIFORM_VEC3);
        
        // Light 5 is dynamic (camera spot)
        float lColor5[] = { 0.53f, 0.81f, 0.92f };
        SetShaderValue(shader, locLightColor[4], lColor5, SHADER_UNIFORM_VEC3);
        float cutoff = cosf(30.0f * DEG2RAD);
        SetShaderValue(shader, locLightCut5, &cutoff, SHADER_UNIFORM_FLOAT);

        // 3. Generate Geometry
        meshTorus = GenFlatShadedTorus(12.0f, 3.0f, 24, 16); // Using params from source
        modelTorus = LoadModelFromMesh(meshTorus);
        modelTorus.materials[0].shader = shader;
        modelTorus.materials[0].maps[MATERIAL_MAP_DIFFUSE].color = WHITE;
        
        meshIco = GenFlatShadedIcosahedron(6.0f);
        modelIco = LoadModelFromMesh(meshIco);
        modelIco.materials[0].shader = shader;
        modelIco.materials[0].maps[MATERIAL_MAP_DIFFUSE].color = WHITE;
        
        // 4. Setup Fixed Camera
        camera.position = (Vector3){ 25.0f, 15.0f, 25.0f };
        camera.target = (Vector3){ 0.0f, 0.0f, 0.0f };
        camera.up = (Vector3){ 0.0f, 1.0f, 0.0f };
        camera.fovy = 45.0f;
        camera.projection = CAMERA_PERSPECTIVE;
        
        // 5. Init Stars
        stars.resize(200);
        for(auto& star : stars) {
            star.x = (float)(GetRandomValue(-width/2, width/2));
            star.y = (float)(GetRandomValue(-height/2, height/2));
            star.z = (float)GetRandomValue(1, 1000) / 1000.0f;
            star.speed = 0.005f + (1.0f - star.z) * 0.0025f;
            star.color = WHITE;
            if (GetRandomValue(0, 100) < 20) {
                 int c = GetRandomValue(0, 3);
                 if(c==0) star.color = SKYBLUE;
                 else if(c==1) star.color = YELLOW;
                 else star.color = LIGHTGRAY;
            }
        }
    }
    
    void Update(float dt) {
        rotation += 15.0f * dt;
        if(rotation > 360.0f) rotation -= 360.0f;
        
        // Update stars
        for(auto& star : stars) {
            star.z -= star.speed * dt * 60.0f; // Scale speed for 60fps
            if(star.z <= 0.0f) {
                star.x = (float)(GetRandomValue(-viewTarget.texture.width/2, viewTarget.texture.width/2));
                star.y = (float)(GetRandomValue(-viewTarget.texture.height/2, viewTarget.texture.height/2));
                star.z = 1.0f;
            }
        }
        
        // Update Shader Uniforms (Dynamic Light 5)
        float camPos[3] = { camera.position.x, camera.position.y, camera.position.z };
        SetShaderValue(shader, locViewPos, camPos, SHADER_UNIFORM_VEC3);
        SetShaderValue(shader, locLightPos[4], camPos, SHADER_UNIFORM_VEC3);
        
        Vector3 camDir = Vector3Normalize(Vector3Subtract(camera.target, camera.position));
        float camDirArr[3] = { camDir.x, camDir.y, camDir.z };
        SetShaderValue(shader, locLightDir5, camDirArr, SHADER_UNIFORM_VEC3);
    }
    
    void Render(StationType activeStation) {
        BeginTextureMode(viewTarget);
            ClearBackground(BLACK);
            
            // 1. Draw Starfield
            int w = viewTarget.texture.width;
            int h = viewTarget.texture.height;
            for(const auto& star : stars) {
                float perspective = 1.0f / star.z;
                float x = star.x * perspective + w / 2.0f;
                float y = star.y * perspective + h / 2.0f;
                
                if (x >= 0 && x < w && y >= 0 && y < h) {
                    float size = (1.0f - star.z) * 3.0f;
                    if (size < 1.0f) size = 1.0f;
                    float brightness = 1.0f - star.z;
                    Color c = star.color;
                    c.r = (unsigned char)(c.r * brightness);
                    c.g = (unsigned char)(c.g * brightness);
                    c.b = (unsigned char)(c.b * brightness);
                    DrawCircle((int)x, (int)y, size, c);
                }
            }
            
            // 2. Draw 3D Artifact
            BeginMode3D(camera);
                rlDisableBackfaceCulling();
                
                Model* targetModel = nullptr;
                Color tint = WHITE;
                
                switch (activeStation) {
                    case STATION_ALPHA: targetModel = &modelTorus; break;
                    case STATION_BETA:  targetModel = &modelIco; break;
                    case STATION_GAMMA: targetModel = &modelTorus; tint = RED; break;
                    case STATION_DELTA: targetModel = &modelIco; tint = GOLD; break;
                }
                
                if (targetModel) {
                    DrawModelEx(*targetModel, {0,0,0}, {0,1,0}, rotation, {1,1,1}, tint);
                }
                
                rlEnableBackfaceCulling();
            EndMode3D();
            
        EndTextureMode();
    }
    
    Texture2D GetTexture() {
        return viewTarget.texture;
    }
};

StationViewport stationViewport;

// ------------------------------------------------------------
// PAGE: PROSPECT MAP
// ------------------------------------------------------------
void DrawPageProspectMap(GameState* state, int* menuSelection, Vector3* shipPos, Vector3* shipVel) {
    // 1. Clear Background
    ClearBackground(BLACK);
    
    // 2. Draw Station Viewport Texture (Rendered previously in UpdateFrame)
    Texture2D viewTex = stationViewport.GetTexture();
    Rectangle srcRect = { 0, 0, (float)viewTex.width, (float)-viewTex.height }; // Flip Y
    Rectangle destRect = { 0, 0, VIRTUAL_WIDTH, VIRTUAL_HEIGHT }; // Full virtual screen
    DrawTexturePro(viewTex, srcRect, destRect, {0,0}, 0.0f, WHITE);
    
    // 3. Draw GUI Texture (Overlay with Transparency)
    if (guiHudTx.id > 0) {
        DrawTexturePro(guiHudTx, 
            (Rectangle){0, 0, (float)guiHudTx.width, (float)guiHudTx.height},
            (Rectangle){0, 0, VIRTUAL_WIDTH, VIRTUAL_HEIGHT},
            (Vector2){0, 0}, 0.0f, WHITE);
    }
    
    // Keep navigation logic for entering lander
    if (CustomIsKeyPressed(KEY_ENTER) || CustomIsKeyPressed(KEY_SPACE)) {
                *shipPos = (Vector3){0, 60, -PROSPECT_PERIMETER}; 
                *shipVel = (Vector3){0, 0, 10};
                ResetState(state, menuSelection, STATE_LANDER);
    }
    
    DrawText("PRESS ENTER TO LAUNCH MISSION", 400, 760, 20, LIGHTGRAY);
}

// ------------------------------------------------------------
// PAGE: DRILLING SEQUENCE
// ------------------------------------------------------------
float drillProgress = 0.0f;
void DrawPageDrilling(GameState* state, int* menuSelection) {
    ClearBackground((Color){20, 10, 5, 255});
    DrawRetroWindow("DRILLING OPERATION", 300, 200, 600, 400);
    
    drillProgress += GetFrameTime() * 20.0f;
    if (drillProgress > 100.0f) drillProgress = 100.0f;
    
    DrawText("DRILLING IN PROGRESS...", 450, 300, 20, WHITE);
    
    // Bar
    DrawRectangle(350, 350, 500, 40, DARKGRAY);
    DrawRectangle(350, 350, (int)(drillProgress * 5), 40, ORANGE);
    DrawRectangleLines(350, 350, 500, 40, WHITE);
    
    if (drillProgress >= 100.0f) {
        DrawText("SUCCESS! RESOURCES ACQUIRED.", 420, 420, 20, GREEN);
        // Only 1 option, simpler handling
        if (DrawButton("RETURN TO SHIP", 500, 500, 200, 40, true)) {
            G_Player.iron += GetRandomValue(1, 3);
            G_Player.cargoFilled++;
            ResetState(state, menuSelection, STATE_LANDER);
            drillProgress = 0.0f;
        }
    }
}

// ------------------------------------------------------------
// PAGE: DEBRIS COLLECTION
// ------------------------------------------------------------
void DrawPageDebris(GameState* state, int* menuSelection) {
    ClearBackground((Color){5, 20, 10, 255});
    DrawRetroWindow("DEBRIS COLLECTION", 300, 200, 600, 400);
    DrawText("Collecting Debris...", 450, 300, 20, GREEN);
    
    if (DrawButton("FINISH", 500, 500, 200, 40, true)) {
        G_Player.gold += 1;
        G_Player.cargoFilled++;
        ResetState(state, menuSelection, STATE_LANDER);
    }
}

// ------------------------------------------------------------
// PAGE: DEPOT MAP
// ------------------------------------------------------------
void DrawPageDepotSelect(GameState* state, int* menuSelection) {
    ClearBackground((Color){10, 10, 30, 255});
    DrawRetroWindow("AVAILABLE DEPOTS", 100, 100, 1000, 600);
    
    // 2 Options
    if (CustomIsKeyPressed(KEY_RIGHT) || CustomIsKeyPressed(KEY_LEFT) || CustomIsKeyPressed(KEY_UP) || CustomIsKeyPressed(KEY_DOWN)) {
        *menuSelection = (*menuSelection == 0) ? 1 : 0;
    }

    // Station Icons
    Color c1 = (*menuSelection == 0) ? WHITE : GRAY;
    Color c2 = (*menuSelection == 1) ? WHITE : GRAY;

    DrawCircle(400, 300, 60, BLUE);
    DrawCircleLines(400, 300, 65, c1);
    DrawText("ALPHA STATION", 350, 370, 20, c1);
    if (DrawButton("DOCK", 350, 400, 100, 30, *menuSelection == 0)) {
        ResetState(state, menuSelection, STATE_DEPOT_HOME);
    }

    DrawCircle(800, 400, 40, PURPLE);
    DrawCircleLines(800, 400, 45, c2);
    DrawText("OUTPOST BETA", 750, 450, 20, c2);
    if (DrawButton("LOCKED", 750, 480, 100, 30, *menuSelection == 1)) {
        // Locked logic
    }
}

// ------------------------------------------------------------
// PAGE: DEPOT HOME
// ------------------------------------------------------------
void DrawPageDepotHome(GameState* state, int* menuSelection) {
    ClearBackground((Color){20, 20, 25, 255});
    DrawRetroWindow("ALPHA STATION HUB", 50, 50, 1100, 700);
    
    int numOptions = 5;
    if (CustomIsKeyPressed(KEY_DOWN)) *menuSelection = (*menuSelection + 1) % numOptions;
    if (CustomIsKeyPressed(KEY_UP)) *menuSelection = (*menuSelection - 1 + numOptions) % numOptions;

    int btnX = 100;
    int btnY = 150;
    int spacing = 60;
    
    if (DrawButton("SPACE STATION BAR", btnX, btnY, 300, 40, *menuSelection == 0)) ResetState(state, menuSelection, STATE_BAR);
    btnY += spacing;
    if (DrawButton("SHIPYARD & UPGRADES", btnX, btnY, 300, 40, *menuSelection == 1)) ResetState(state, menuSelection, STATE_SHIPYARD);
    btnY += spacing;
    if (DrawButton("COMMODITIES MARKET", btnX, btnY, 300, 40, *menuSelection == 2)) ResetState(state, menuSelection, STATE_MARKET);
    btnY += spacing;
    if (DrawButton("LODGINGS", btnX, btnY, 300, 40, *menuSelection == 3)) ResetState(state, menuSelection, STATE_LODGINGS);
    btnY += spacing * 2;
    
    // Auto Refuel visual
    G_Player.fuel = G_Player.maxFuel;
    DrawText("SHIP REFUELLEDBY STATION SERVICES", btnX, btnY, 20, GREEN);
    btnY += 40;

    if (DrawButton("UNDOCK (TO MAP)", btnX, btnY, 300, 40, *menuSelection == 4)) ResetState(state, menuSelection, STATE_PROSPECT_MAP);
}

// ------------------------------------------------------------
// PAGE: SUB-MENUS
// ------------------------------------------------------------
void DrawPageBar(GameState* state, int* menuSelection) {
    ClearBackground(BLACK);
    DrawRetroWindow("THE RUSTY ROCKET BAR", 200, 100, 800, 600);
    DrawText("Bartender: 'Careful out there, miner...'", 250, 200, 20, YELLOW);
    
    if (DrawButton("BACK", 500, 600, 200, 40, true)) ResetState(state, menuSelection, STATE_DEPOT_HOME);
}

void DrawPageShipyard(GameState* state, int* menuSelection) {
    ClearBackground(BLACK);
    DrawRetroWindow("SHIPYARD", 200, 100, 800, 600);
    DrawText("Upgrade your thrusters and hull here.", 250, 200, 20, WHITE);
    
    if (CustomIsKeyPressed(KEY_DOWN) || CustomIsKeyPressed(KEY_UP)) *menuSelection = !(*menuSelection); // Toggle 0/1

    if (DrawButton("UPGRADE THRUST (500cr)", 250, 300, 300, 40, *menuSelection == 0)) {
        if (G_Player.credits >= 500) {
            G_Player.credits -= 500;
            SHIP_THRUST_POWER += 5.0f;
        }
    }
    if (DrawButton("BACK", 500, 600, 200, 40, *menuSelection == 1)) ResetState(state, menuSelection, STATE_DEPOT_HOME);
}

void DrawPageMarket(GameState* state, int* menuSelection) {
    ClearBackground(BLACK);
    DrawRetroWindow("COMMODITIES MARKET", 200, 100, 800, 600);
    
    int numOpt = 3;
    if (CustomIsKeyPressed(KEY_DOWN)) *menuSelection = (*menuSelection + 1) % numOpt;
    if (CustomIsKeyPressed(KEY_UP)) *menuSelection = (*menuSelection - 1 + numOpt) % numOpt;

    DrawText(TextFormat("CREDITS: %d", G_Player.credits), 250, 160, 30, GREEN);
    DrawText(TextFormat("IRON ORE: %d", G_Player.iron), 250, 220, 20, WHITE);
    if (DrawButton("SELL IRON (50cr)", 500, 210, 200, 30, *menuSelection == 0)) {
        if (G_Player.iron > 0) { G_Player.iron--; G_Player.credits += 50; G_Player.cargoFilled--; }
    }
    
    DrawText(TextFormat("GOLD ORE: %d", G_Player.gold), 250, 270, 20, WHITE);
    if (DrawButton("SELL GOLD (100cr)", 500, 260, 200, 30, *menuSelection == 1)) {
        if (G_Player.gold > 0) { G_Player.gold--; G_Player.credits += 100; G_Player.cargoFilled--; }
    }

    if (DrawButton("BACK", 500, 600, 200, 40, *menuSelection == 2)) ResetState(state, menuSelection, STATE_DEPOT_HOME);
}

void DrawPageLodgings(GameState* state, int* menuSelection) {
    ClearBackground(BLACK);
    DrawRetroWindow("CREW LODGINGS", 200, 100, 800, 600);
    DrawText("Zzz... Rested and Saved.", 350, 300, 20, BLUE);
    if (DrawButton("BACK", 500, 600, 200, 40, true)) ResetState(state, menuSelection, STATE_DEPOT_HOME);
}

// ------------------------------------------------------------
// GAME LOOP FUNCTION (called from Python each frame)
// ------------------------------------------------------------
#ifdef __cplusplus
extern "C" {
#endif

__declspec(dllexport) __cdecl void UpdateFrame() {
    static int frame_count = 0;
    frame_count++;
    
    if (!g_framebuffer_initialized || !g_game_initialized) {
        if (frame_count % 60 == 0) {
            printf("[UpdateFrame] ERROR: Not initialized! framebuffer=%d, game=%d\n", 
                   g_framebuffer_initialized, g_game_initialized);
        }
        return;
    }
    
    // Run one frame of game logic and rendering
    float dt = GetFrameTime();
    
    // Clamp dt to prevent huge jumps or zero values
    if (dt <= 0.0f || dt > 0.1f) {
        dt = 1.0f / 60.0f;  // Default to 60 FPS if invalid
        if (frame_count % 60 == 0) {
            printf("[UpdateFrame] WARNING: Invalid dt, clamped to %.4f\n", dt);
        }
    }

    // Update Station Viewport (Animation)
    stationViewport.Update(dt);
    
    // Render Station Viewport (Offscreen) to low-res target
    stationViewport.Render(STATION_ALPHA);
    
    // Start rendering to framebuffer (low resolution)
    BeginTextureMode(g_framebuffer);
    ClearBackground((Color){5, 5, 10, 255});
    
    // Scale Logic: Virtual (1200x800) -> Render (600x400)
    Camera2D screenCam = {0};
    screenCam.zoom = (float)RENDER_WIDTH / (float)VIRTUAL_WIDTH; // 0.5f
    
    // Use Camera2D to scale all 2D drawing calls
    BeginMode2D(screenCam);
    
    switch(g_currentState) {
        case STATE_PROSPECT_MAP:
            DrawPageProspectMap(&g_currentState, &g_menuSelection, &g_shipPos, &g_shipVel);
            DrawScanlines();
            break;

        case STATE_DRILLING:
            DrawPageDrilling(&g_currentState, &g_menuSelection);
            DrawScanlines();
            break;

        case STATE_DEBRIS:
            DrawPageDebris(&g_currentState, &g_menuSelection);
            DrawScanlines();
            break;

        case STATE_DEPOT_SELECT:
            DrawPageDepotSelect(&g_currentState, &g_menuSelection);
            DrawScanlines();
            break;

        case STATE_DEPOT_HOME:
            DrawPageDepotHome(&g_currentState, &g_menuSelection);
            DrawScanlines();
            break;

        case STATE_BAR:
            DrawPageBar(&g_currentState, &g_menuSelection);
            DrawScanlines();
            break;
            
        case STATE_SHIPYARD:
            DrawPageShipyard(&g_currentState, &g_menuSelection);
            DrawScanlines();
            break;
            
        case STATE_MARKET:
            DrawPageMarket(&g_currentState, &g_menuSelection);
            DrawScanlines();
            break;
            
        case STATE_LODGINGS:
            DrawPageLodgings(&g_currentState, &g_menuSelection);
            DrawScanlines();
            break;

        case STATE_LANDER:
        {
            // End 2D Mode for 3D rendering to use full framebuffer natively
            EndMode2D();
            
            static int lander_frame = 0;
            lander_frame++;
            
            // LANDER LOGIC (Existing 3D Game)
            // --- Input ---
            Vector2 mouseDelta = CustomGetMouseDelta();
            
            g_shipPitch -= mouseDelta.y * 0.15f; 
            g_shipRoll -= mouseDelta.x * 0.15f; 
            if (fabs(mouseDelta.x) < 0.1f) g_shipRoll = Lerp(g_shipRoll, 0.0f, 1.0f * dt);
            g_shipPitch = Clamp(g_shipPitch, -85.0f, 85.0f);
            if (CustomIsMouseButtonReleased(MOUSE_BUTTON_RIGHT)) g_yawDirection *= -1;
            if (CustomIsMouseButtonDown(MOUSE_BUTTON_RIGHT)) g_shipYaw -= 120.0f * dt * (float)g_yawDirection;

            Matrix matRoll = MatrixRotateZ(DEG2RAD * -g_shipRoll);
            Matrix matPitch = MatrixRotateX(DEG2RAD * g_shipPitch);
            Matrix matYaw = MatrixRotateY(DEG2RAD * g_shipYaw);
            Matrix rot = MatrixMultiply(MatrixMultiply(matPitch, matRoll), matYaw);
            Vector3 shipForward = { rot.m8, rot.m9, rot.m10 }; 
            Vector3 shipUp = { rot.m4, rot.m5, rot.m6 };        

            // --- Physics ---
            g_shipVel.y += SHIP_GRAVITY * dt;
            bool isThrusting = CustomIsMouseButtonDown(MOUSE_LEFT_BUTTON) || CustomIsKeyDown(KEY_SPACE) || CustomIsKeyDown(KEY_W);
            if (isThrusting && G_Player.fuel > 0.0f) {
                g_shipVel = Vector3Add(g_shipVel, Vector3Scale(shipUp, SHIP_THRUST_POWER * dt));
                Vector3 engineNozzle = Vector3Add(g_shipPos, Vector3Scale(shipUp, -0.4f));
                SpawnThrustParticles(engineNozzle, shipUp);
                G_Player.fuel -= SHIP_FUEL_BURN_RATE * dt;
                if (G_Player.fuel < 0) G_Player.fuel = 0;
            }
            g_shipVel = Vector3Scale(g_shipVel, SHIP_DRAG_FACTOR);
            Vector3 nextPos = Vector3Add(g_shipPos, Vector3Scale(g_shipVel, dt));

            // --- Collision ---
            float worldH = GetWorldHeight(nextPos.x, nextPos.z);
            float softCeiling = worldH + 12.0f;
            if (nextPos.y > softCeiling) {
                 g_shipVel.y -= (nextPos.y - softCeiling) * 2.0f * dt;
                 nextPos = Vector3Add(g_shipPos, Vector3Scale(g_shipVel, dt));
            }
            if (nextPos.y < worldH + 0.5f) {
                nextPos.y = worldH + 0.5f;
                
                // LANDING DETECTION
                if (Vector3Length(g_shipVel) < 1.0f) {
                    ResetState(&g_currentState, &g_menuSelection, STATE_DRILLING);
                } else {
                    // Crash - bounce
                    if (g_shipVel.y < 0) g_shipVel.y = 0;
                    g_shipVel = Vector3Scale(g_shipVel, 0.5f); 
                }
            }
            
            // --- Boundary & Orbit Detection ---
            if (g_shipPos.y > 80.0f) {
                ResetState(&g_currentState, &g_menuSelection, STATE_DEPOT_SELECT);
            }

            if (nextPos.x > PROSPECT_PERIMETER) { nextPos.x = PROSPECT_PERIMETER; g_shipVel.x = 0; }
            if (nextPos.x < -PROSPECT_PERIMETER) { nextPos.x = -PROSPECT_PERIMETER; g_shipVel.x = 0; }
            if (nextPos.z > PROSPECT_PERIMETER) { nextPos.z = PROSPECT_PERIMETER; g_shipVel.z = 0; }
            if (nextPos.z < -PROSPECT_PERIMETER) { nextPos.z = -PROSPECT_PERIMETER; g_shipVel.z = 0; }
            g_shipPos = nextPos;

            // --- Camera ---
            const float CAM_FOLLOW_DIST = 9.0f; 
            const float CAM_HEIGHT_OFFSET = 4.0f;
            Vector3 camOffset = Vector3Scale(shipForward, -CAM_FOLLOW_DIST); 
            camOffset.y += CAM_HEIGHT_OFFSET;
            g_camera.position = Vector3Lerp(g_camera.position, Vector3Add(g_shipPos, camOffset), 5.0f * dt);
            if (g_camera.position.y < 0.5f) g_camera.position.y = 0.5f;
            g_camera.target = g_shipPos;

            UpdateParticles(dt);

            // --- Draw 3D Scene ---
            BeginMode3D(g_camera);
                // Chunks
                float cullDist = RENDER_DISTANCE + (CHUNK_SIZE * 0.8f); 
                for(int i=0; i<TOTAL_CHUNKS; i++) {
                    if (fabs(g_shipPos.x - g_chunkCenters[i].x) < cullDist && fabs(g_shipPos.z - g_chunkCenters[i].y) < cullDist) {
                        DrawModel(g_chunkModels[i], (Vector3){0,0,0}, 1.0f, WHITE);
                    }
                }
                DrawPerimeterBorder(g_shipPos);
                DrawProjectedShadow(g_shipPos);
                g_ship.transform = rot;
                DrawModel(g_ship, g_shipPos, 1.0f, WHITE);
                // Rocks
                rlDisableBackfaceCulling(); 
                for(int i = 0; i < NUM_ROCKS; i++) {
                    if (fabs(G_Rocks[i].position.x - g_shipPos.x) < (float)RENDER_DISTANCE && fabs(G_Rocks[i].position.z - g_shipPos.z) < (float)RENDER_DISTANCE) {
                        DrawModelEx(g_rockModel, G_Rocks[i].position, G_Rocks[i].axis, G_Rocks[i].angle, (Vector3){G_Rocks[i].scale, G_Rocks[i].scale, G_Rocks[i].scale}, G_Rocks[i].color);
                    }
                }
                rlEnableBackfaceCulling();
                DrawParticles();
            EndMode3D();
            
            // Re-enable 2D Mode for HUD overlay
            BeginMode2D(screenCam);
            
            // --- UI Overlay ---
            DrawFPS(10, 10);
            DrawText("LAND TO DRILL - FLY UP TO ORBIT", 10, 40, 20, LIGHTGRAY);
            int bars = (int)G_Player.fuel;
            int screenH = VIRTUAL_HEIGHT; // We use virtual height because of scaling
            DrawText("FUEL", 10, screenH - 40, 20, WHITE);
            for(int i=0; i<10; i++) {
                Color barCol = (i < bars) ? GREEN : DARKGRAY;
                if (i < 3 && i < bars) barCol = RED;
                DrawRectangle(70 + (i * 25), screenH - 40, 20, 20, barCol);
            }
            DrawScanlines();
            break;
        }
    }
    
    // End 2D Mode if still active (from menus or HUD)
    if (g_currentState != STATE_LANDER) {
        EndMode2D();
    } else {
        EndMode2D(); // Close the HUD mode
    }
    
    // Clear one-time input flags at end of frame
    ClearInputFrame();
    
    // End rendering to framebuffer
    EndTextureMode();
}

// ------------------------------------------------------------
// INITIALIZATION FUNCTION
// ------------------------------------------------------------
__declspec(dllexport) __cdecl bool InitializeGame() {
    if (g_game_initialized) {
        return true; // Already initialized
    }
    
    SetTraceLogLevel(LOG_NONE);
    SetConfigFlags(FLAG_WINDOW_UNDECORATED | FLAG_WINDOW_HIDDEN);
    
    if (!IsWindowReady()) {
        InitWindow(VIRTUAL_WIDTH, VIRTUAL_HEIGHT, "AstroMiner_Embedded");
    }
    
    SetTargetFPS(60);
    DisableCursor();
    
    // Create offscreen render texture (Low Res)
    g_framebuffer = LoadRenderTexture(RENDER_WIDTH, RENDER_HEIGHT);
    g_framebuffer_initialized = true;
    
    // Initialize Station Viewport (Low Res)
    stationViewport.Init(RENDER_WIDTH, RENDER_HEIGHT);
    
    // Initialize camera (position it near the ship's starting position)
    g_camera.up = (Vector3){0,1,0};
    g_camera.fovy = 60;
    g_camera.projection = CAMERA_PERSPECTIVE;
    // Start camera behind and above the ship's starting position
    g_camera.position = (Vector3){0, 64, -PROSPECT_PERIMETER - 9.0f};  // Behind ship, slightly above
    g_camera.target = (Vector3){0, 60, -PROSPECT_PERIMETER};  // Point at ship's starting position
    
    // Create meshes and models
    Mesh shipMesh = CreateSolidShip();
    g_ship = LoadModelFromMesh(shipMesh);
    
    Mesh rockBaseMesh = CreateBaseRockMesh();
    g_rockModel = LoadModelFromMesh(rockBaseMesh);
    
    // Generate world
    GenerateRocksAndCollision();
    InitCollisionGrid();
    
    // Load scanline texture
    scanlineTx = LoadTexture("../../images/scanline.png");
    
    // Load GUI_and_HUD texture with multiple fallbacks
    guiHudTx = LoadTexture("GUI_and_HUD.png");
    if (guiHudTx.id == 0) {
        guiHudTx = LoadTexture("Data/games/AstroMiner/GUI_and_HUD.png");
    }
    if (guiHudTx.id == 0) {
        guiHudTx = LoadTexture("../../games/AstroMiner/GUI_and_HUD.png");
    }
    
    if (guiHudTx.id > 0) {
        printf("[InitializeGame] Loaded GUI texture: %d x %d\n", guiHudTx.width, guiHudTx.height);
    } else {
        printf("[InitializeGame] FAILED TO LOAD GUI TEXTURE from any path\n");
    }
    
    // Bake terrain chunks
    int chunkIdx = 0;
    float startP = -PROSPECT_PERIMETER;
    for (int z = 0; z < CHUNKS_AXIS; z++) {
        for (int x = 0; x < CHUNKS_AXIS; x++) {
            float cx = startP + (x * CHUNK_SIZE);
            float cz = startP + (z * CHUNK_SIZE);
            Mesh cMesh = CreateTerrainChunk(cx, cz, (float)CHUNK_SIZE);
            g_chunkModels[chunkIdx] = LoadModelFromMesh(cMesh);
            g_chunkCenters[chunkIdx] = (Vector2){ cx + CHUNK_SIZE/2.0f, cz + CHUNK_SIZE/2.0f };
            chunkIdx++;
        }
    }
    
    // Initialize game state
    g_shipPos = (Vector3){0, 60, -PROSPECT_PERIMETER};
    g_shipVel = (Vector3){0, 0, 10};
    g_shipPitch = 0.0f;
    g_shipRoll = 0.0f;
    g_shipYaw = 0.0f;
    g_yawDirection = 1;
    g_currentState = STATE_PROSPECT_MAP;
    g_menuSelection = 0;
    
    g_game_initialized = true;
    
    return g_framebuffer_initialized && g_game_initialized;
}

#ifdef __cplusplus
}
#endif

// ------------------------------------------------------------
// MAIN (for standalone testing - can be removed when embedded)
// ------------------------------------------------------------
int main()
{
    if (!InitializeGame()) {
        return 1;
    }
    
    while (!WindowShouldClose())
    {
        UpdateFrame();
        
        // Draw framebuffer to screen for testing
        BeginDrawing();
        DrawTexturePro(g_framebuffer.texture, 
            (Rectangle){0, 0, (float)g_framebuffer.texture.width, (float)-g_framebuffer.texture.height},
            (Rectangle){0, 0, (float)GetScreenWidth(), (float)GetScreenHeight()},
            (Vector2){0,0}, 0.0f, WHITE);
        EndDrawing();
    }
    
    CloseWindow();
    return 0;
}
