#include "raylib.h"
#include "raymath.h"
#include "rlgl.h"
#include <math.h>

// ------------------------------------------------------------
// CONSTANTS
// ------------------------------------------------------------
#define NUM_ROCKS 100
#define TRIS_PER_ROCK 36
#define ROCK_TRI_COUNT (NUM_ROCKS * TRIS_PER_ROCK)
#define PROSPECT_PERIMETER 120.0f 

// Render Distance (Reduced by 50% from 30 to 15)
const int RENDER_DISTANCE = 15; 

// Terrain Chunking (GPU Optimization)
// Reduced from 20 to 8 to make the "pop-in" smoother and less blocky
#define CHUNK_SIZE 8 
#define CHUNKS_AXIS (int)((PROSPECT_PERIMETER * 2) / CHUNK_SIZE)
#define TOTAL_CHUNKS (CHUNKS_AXIS * CHUNKS_AXIS)

// ------------------------------------------------------------
// DATA STRUCTURES
// ------------------------------------------------------------
typedef struct Tri {
    Vector3 a;
    Vector3 b;
    Vector3 c;
} Tri;

// Global collision array for all rocks
Tri G_RockTris[ROCK_TRI_COUNT];

struct RockInstance {
    Vector3 position;
    Vector3 axis;
    float angle;
    float scale;
    Color color;
};

RockInstance G_Rocks[NUM_ROCKS];

// ------------------------------------------------------------
// MATH HELPERS
// ------------------------------------------------------------
bool GetHeightOnTriangle(Vector3 p1, Vector3 p2, Vector3 p3, float x, float z, float* outY)
{
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
// WORLD COLLISION (Terrain + All Rocks)
// ------------------------------------------------------------
float GetWorldHeight(float x, float z)
{
    float height = GetTerrainHeight(x, z);
    
    // Check all rock triangles
    for (int i = 0; i < ROCK_TRI_COUNT; i++) {
        float triH;
        if (GetHeightOnTriangle(G_RockTris[i].a, G_RockTris[i].b, G_RockTris[i].c, x, z, &triH)) {
            if (triH > height) height = triH;
        }
    }
    return height;
}

// ------------------------------------------------------------
// MESH GENERATION HELPERS (GPU OFFLOADING)
// ------------------------------------------------------------

// Generates a specific square chunk of terrain
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

            // Color Logic (Checkerboard based on world pos)
            int wx = (int)xf; int wz = (int)zf;
            Color gc = (abs(wx) % 2 == abs(wz) % 2) ? grey1 : grey2;

            // Tri 1 (A-B-C)
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

            // Tri 2 (A-C-D)
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

// ------------------------------------------------------------
// DYNAMIC DRAWING HELPERS (Perimeter)
// ------------------------------------------------------------
// We use dynamic drawing for the perimeter so it respects visual culling perfectly
void DrawPerimeterBorder(Vector3 shipPos) {
    Color col = {0, 255, 255, 128}; // Semi-transparent Cyan
    float halfWidth = 1.0f; 
    float step = 2.0f; 
    float limit = PROSPECT_PERIMETER;
    
    // Bounds check to respect Draw Distance (Box culling creates straight lines)
    float minRenderX = shipPos.x - RENDER_DISTANCE;
    float maxRenderX = shipPos.x + RENDER_DISTANCE;
    float minRenderZ = shipPos.z - RENDER_DISTANCE;
    float maxRenderZ = shipPos.z + RENDER_DISTANCE;

    rlBegin(RL_QUADS);
    rlColor4ub(col.r, col.g, col.b, col.a);

    // 1. Z-axis borders (Left and Right)
    float startZ = fmaxf(-limit, minRenderZ);
    float endZ   = fminf(limit, maxRenderZ);

    if (startZ < endZ) {
        // Left Strip
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

        // Right Strip
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

    // 2. X-axis borders (Top and Bottom)
    float startX = fmaxf(-limit, minRenderX);
    float endX   = fminf(limit, maxRenderX);

    if (startX < endX) {
        // Top Strip
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

        // Bottom Strip
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

void DrawProjectedShadow(Vector3 shipPos)
{
    float groundY = GetWorldHeight(shipPos.x, shipPos.z);
    float altitude = shipPos.y - groundY;
    if (altitude < 0) altitude = 0;

    float radius = 0.6f + (altitude * 0.075f);
    if (radius > 2.5f) radius = 2.5f;

    float heightFactor = Clamp(altitude / 12.0f, 0.0f, 1.0f);
    unsigned char alpha = (unsigned char)Lerp(220, 60, heightFactor);
    unsigned char greyVal = (unsigned char)Lerp(0, 80, heightFactor);
    
    Color shadowCol = (Color){greyVal, greyVal, greyVal, alpha}; 
    
    float step = 0.25f; 
    rlBegin(RL_QUADS);
    rlColor4ub(shadowCol.r, shadowCol.g, shadowCol.b, shadowCol.a);

    float startX = shipPos.x - radius; float endX = shipPos.x + radius;
    float startZ = shipPos.z - radius; float endZ = shipPos.z + radius;

    for (float x = startX; x < endX; x += step)
    {
        for (float z = startZ; z < endZ; z += step)
        {
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

// ------------------------------------------------------------
// PARTICLES
// ------------------------------------------------------------
struct Particle { Vector3 pos; Vector3 vel; Color color; float life; bool onGround; };
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
// ROCK MESH GENERATION
// ------------------------------------------------------------

// 1. Create a "Base" mesh at (0,0,0) for rendering
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
        // For the base mesh, we just use local vertices
        Vector3 pLocal[5];
        for(int i=0;i<5;i++) pLocal[i]=vLocal[faces[f][i]];
        
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

// 2. Generate Locations and collision triangles
void GenerateRocksAndCollision() {
    float phi = 1.61803398875f; float inv = 1.0f/phi;
    Vector3 vLocal[20] = {{1,1,1},{1,1,-1},{1,-1,1},{1,-1,-1},{-1,1,1},{-1,1,-1},{-1,-1,1},{-1,-1,-1},{0,inv,phi},{0,inv,-phi},{0,-inv,phi},{0,-inv,-phi},{inv,phi,0},{inv,-phi,0},{-inv,phi,0},{-inv,-phi,0},{phi,0,inv},{phi,0,-inv},{-phi,0,inv},{-phi,0,-inv}};
    int faces[12][5] = {{0,16,2,10,8},{0,8,4,14,12},{16,17,1,12,0},{1,9,11,3,17},{1,12,14,5,9},{2,13,15,6,10},{13,3,11,7,15},{4,8,10,6,18},{14,4,18,19,5},{5,19,7,11,9},{15,7,19,18,6},{2,16,17,3,13}};

    int globalTriIdx = 0;
    
    // Cluster tracking
    Vector3 clusterCenter = {0};
    
    // Max Rock size is 3.0f (300/100). "Two max rock sizes" = 6.0f distance
    float maxClusterDist = 6.0f;
    
    // NOTE: Rocks must strictly adhere to the PROSPECT_PERIMETER to avoid spawning outside the playable area.
    int limit = (int)PROSPECT_PERIMETER;

    for (int r = 0; r < NUM_ROCKS; r++) {
        // Random Properties
        float scale = (float)GetRandomValue(50, 300) / 100.0f; // 0.5 to 3.0
        
        float rx, rz;
        
        // PAIRING LOGIC
        // Even index (0, 2, 4): Start a new random cluster location
        if (r % 2 == 0) {
            rx = (float)GetRandomValue(-limit, limit);
            rz = (float)GetRandomValue(-limit, limit);
            clusterCenter = (Vector3){rx, 0, rz}; // Save for next rock
        } 
        // Odd index (1, 3, 5): Spawn close to the previous rock (clusterCenter)
        else {
            // Random offset within 6.0 units
            float angle = (float)GetRandomValue(0, 360) * DEG2RAD;
            float dist = (float)GetRandomValue(20, 60) / 10.0f; // 2.0 to 6.0 distance
            rx = clusterCenter.x + cosf(angle) * dist;
            rz = clusterCenter.z + sinf(angle) * dist;
            
            // Clamp within bounds just in case
            if(rx > limit) rx = limit; if(rx < -limit) rx = -limit;
            if(rz > limit) rz = limit; if(rz < -limit) rz = -limit;
        }
        
        G_Rocks[r].position = (Vector3){rx, GetTerrainHeight(rx, rz) + (0.2f * scale), rz};
        G_Rocks[r].scale = scale;
        G_Rocks[r].axis = Vector3Normalize((Vector3){(float)GetRandomValue(-1,1),(float)GetRandomValue(-1,1),(float)GetRandomValue(-1,1)});
        G_Rocks[r].angle = (float)GetRandomValue(0, 360);
        int tintVal = GetRandomValue(200, 255);
        G_Rocks[r].color = (Color){(unsigned char)tintVal, (unsigned char)tintVal, (unsigned char)tintVal, 255};

        // Create Rotation Matrix for collision calc
        Matrix matScale = MatrixScale(scale, scale, scale);
        Matrix matRot = MatrixRotate(G_Rocks[r].axis, G_Rocks[r].angle * DEG2RAD);
        Matrix matTrans = MatrixTranslate(G_Rocks[r].position.x, G_Rocks[r].position.y, G_Rocks[r].position.z);
        Matrix matWorld = MatrixMultiply(MatrixMultiply(matScale, matRot), matTrans);

        // Generate Collision Triangles for this specific rock instance
        for(int f=0;f<12;f++){
            Vector3 pWorld[5];
            // Transform local vertices to world space
            for(int i=0;i<5;i++) {
                pWorld[i] = Vector3Transform(vLocal[faces[f][i]], matWorld);
            }

            int tris[3][3]={{0,1,2},{0,2,3},{0,3,4}};
            for(int t=0;t<3;t++){
                G_RockTris[globalTriIdx].a = pWorld[tris[t][0]]; 
                G_RockTris[globalTriIdx].b = pWorld[tris[t][1]]; 
                G_RockTris[globalTriIdx].c = pWorld[tris[t][2]]; 
                globalTriIdx++;
            }
        }
    }
}

// ------------------------------------------------------------
// MAIN
// ------------------------------------------------------------
int main()
{
    InitWindow(1200, 800, "Grey Moon with Scattered Rocks");
    SetTargetFPS(120); 
    DisableCursor();

    Camera3D camera = {0};
    camera.up = (Vector3){0,1,0};
    camera.fovy = 60;
    camera.projection = CAMERA_PERSPECTIVE;
    camera.position = (Vector3){0, 10, -10};

    Mesh shipMesh = CreateSolidShip();
    Model ship = LoadModelFromMesh(shipMesh);

    // SETUP ROCKS
    Mesh rockBaseMesh = CreateBaseRockMesh();
    Model rockModel = LoadModelFromMesh(rockBaseMesh);
    
    // Generate 100 random rocks and populate collision system
    GenerateRocksAndCollision();

    // --- GPU OFFLOAD: BAKE TERRAIN CHUNKS ---
    // We create a grid of static meshes (chunks) so we can cull them based on distance.
    Model chunkModels[TOTAL_CHUNKS];
    Vector2 chunkCenters[TOTAL_CHUNKS];
    
    int chunkIdx = 0;
    float startP = -PROSPECT_PERIMETER;
    
    for (int z = 0; z < CHUNKS_AXIS; z++) {
        for (int x = 0; x < CHUNKS_AXIS; x++) {
            float cx = startP + (x * CHUNK_SIZE);
            float cz = startP + (z * CHUNK_SIZE);
            
            // Generate Mesh for this chunk
            Mesh cMesh = CreateTerrainChunk(cx, cz, (float)CHUNK_SIZE);
            chunkModels[chunkIdx] = LoadModelFromMesh(cMesh);
            
            // Store center for distance checking
            chunkCenters[chunkIdx] = (Vector2){ cx + CHUNK_SIZE/2.0f, cz + CHUNK_SIZE/2.0f };
            chunkIdx++;
        }
    }
    
    // NOTE: Perimeter border is drawn dynamically in the loop for perfect culling

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

        // BOUNDARY CHECK (Prospect Perimeter)
        if (nextPos.x > PROSPECT_PERIMETER) { nextPos.x = PROSPECT_PERIMETER; shipVel.x = 0; }
        if (nextPos.x < -PROSPECT_PERIMETER) { nextPos.x = -PROSPECT_PERIMETER; shipVel.x = 0; }
        if (nextPos.z > PROSPECT_PERIMETER) { nextPos.z = PROSPECT_PERIMETER; shipVel.z = 0; }
        if (nextPos.z < -PROSPECT_PERIMETER) { nextPos.z = -PROSPECT_PERIMETER; shipVel.z = 0; }

        shipPos = nextPos;

        // CAMERA
        Vector3 camOffset = Vector3Scale(shipForward, -CAM_FOLLOW_DIST); 
        camOffset.y += CAM_HEIGHT_OFFSET;
        camera.position = Vector3Lerp(camera.position, Vector3Add(shipPos, camOffset), 5.0f * dt);
        float dist = Vector3Distance(camera.position, shipPos);
        if (dist > CAM_FOLLOW_DIST + 2.0f) camera.position = Vector3Add(shipPos, Vector3Scale(Vector3Normalize(Vector3Subtract(camera.position, shipPos)), CAM_FOLLOW_DIST + 2.0f));
        
        // NEW: Prevent Camera from going below zero level (0.5f margin)
        if (camera.position.y < 0.5f) camera.position.y = 0.5f;

        camera.target = shipPos;

        UpdateParticles(dt);

        // DRAW
        BeginDrawing();
            ClearBackground((Color){5, 5, 10, 255}); // Dark space background
            BeginMode3D(camera);

                // --- DRAW TERRAIN CHUNKS ---
                // BOX CULLING: Only draw chunks that are within square render area
                float cullDist = RENDER_DISTANCE + (CHUNK_SIZE * 0.8f); 
                
                for(int i=0; i<TOTAL_CHUNKS; i++) {
                    // Using Chebyshev Distance (Box) instead of Euclidean (Circle)
                    float dx = fabs(shipPos.x - chunkCenters[i].x);
                    float dz = fabs(shipPos.z - chunkCenters[i].y);
                    
                    if (dx < cullDist && dz < cullDist) {
                        DrawModel(chunkModels[i], (Vector3){0,0,0}, 1.0f, WHITE);
                    }
                }
                
                // --- DYNAMIC PERIMETER DRAW ---
                DrawPerimeterBorder(shipPos);

                DrawProjectedShadow(shipPos);

                ship.transform = rot;
                DrawModel(ship, shipPos, 1.0f, WHITE);
                
                // --- DRAW SCATTERED ROCKS ---
                rlDisableBackfaceCulling(); 
                for(int i = 0; i < NUM_ROCKS; i++) {
                    // NOTE: Rocks must strictly adhere to the RENDER_DISTANCE.
                    // We use Box Culling here to match the square terrain draw distance.
                    // This ensures rocks don't "pop in" or appear floating in the void beyond the generated chunks.
                    float dx = fabs(G_Rocks[i].position.x - shipPos.x);
                    float dz = fabs(G_Rocks[i].position.z - shipPos.z);
                    
                    if (dx < (float)RENDER_DISTANCE && dz < (float)RENDER_DISTANCE) {
                        DrawModelEx(rockModel, G_Rocks[i].position, G_Rocks[i].axis, G_Rocks[i].angle, (Vector3){G_Rocks[i].scale, G_Rocks[i].scale, G_Rocks[i].scale}, G_Rocks[i].color);
                    }
                }
                rlEnableBackfaceCulling();

                DrawParticles();

            EndMode3D();
            DrawFPS(10, 10);
            DrawText(TextFormat("Rocks: %d", NUM_ROCKS), 10, 40, 20, LIGHTGRAY);
            
            // Warning if near boundary
            if (fabs(shipPos.x) > PROSPECT_PERIMETER - 10 || fabs(shipPos.z) > PROSPECT_PERIMETER - 10) {
                 DrawText("WARNING: PERIMETER REACHED", 400, 100, 30, RED);
            }
        EndDrawing();
    }

    UnloadModel(ship);
    UnloadModel(rockModel);
    
    // Unload chunks
    for(int i=0; i<TOTAL_CHUNKS; i++) UnloadModel(chunkModels[i]);

    CloseWindow();
    return 0;
}