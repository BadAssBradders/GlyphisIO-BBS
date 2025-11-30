#include "raylib.h"
#include "raymath.h"
#include "rlgl.h"
#include <cmath>
#include <vector>

// Star structure
struct Star {
    float x;
    float y;
    float z;        // Depth (0 = far, 1 = close)
    float speed;
    Color color;
};

// Function to generate a torus mesh with FLAT shading (duplicated vertices)
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
            // Determine color based on face orientation (Top/Middle/Bottom)
            // v is the angle around the tube section
            float v = (float)j / sides * PI * 2.0f;
            float sinV = sinf(v); // -1 (Bottom) to 1 (Top)
            
            Color faceColor;
            // Use a small threshold to separate bands
            if (sinV > 0.2f)       faceColor = LIGHTGRAY; // Top faces
            else if (sinV < -0.2f) faceColor = DARKGRAY;  // Bottom faces
            else                   faceColor = GRAY;      // Middle faces
            
            // Vertices for this face (quad)
            int iNext = (i + 1) % radSeg;
            int jNext = (j + 1) % sides;
            
            // Helper to compute vertex position
            auto GetPos = [&](int seg, int side) -> Vector3 {
                float u = (float)seg / radSeg * PI * 2.0f;
                float v = (float)side / sides * PI * 2.0f;
                
                float x = (radius + size * cosf(v)) * cosf(u);
                float y = size * sinf(v); // Tube height
                float z = (radius + size * cosf(v)) * sinf(u);
                return (Vector3){x, y, z};
            };
            
            Vector3 p0 = GetPos(i, j);
            Vector3 p1 = GetPos(iNext, j);
            Vector3 p2 = GetPos(iNext, jNext);
            Vector3 p3 = GetPos(i, jNext);
            
            // Calculate Flat Normal for the face
            Vector3 edge1 = Vector3Subtract(p1, p0);
            Vector3 edge2 = Vector3Subtract(p3, p0);
            Vector3 normal = Vector3Normalize(Vector3CrossProduct(Vector3Subtract(p1, p0), Vector3Subtract(p2, p0))); 
            
            // Add vertices
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
            
            // Start index for this face
            int baseIndex = vIndex;
            
            AddVertex(p0);
            AddVertex(p1);
            AddVertex(p2);
            AddVertex(p3);
            
            // Add indices (2 triangles) - Standard CCW
            mesh.indices[iIndex++] = baseIndex;
            mesh.indices[iIndex++] = baseIndex + 1;
            mesh.indices[iIndex++] = baseIndex + 2;
            
            mesh.indices[iIndex++] = baseIndex;
            mesh.indices[iIndex++] = baseIndex + 2;
            mesh.indices[iIndex++] = baseIndex + 3;
        }
    }
    
    // Upload mesh to GPU
    UploadMesh(&mesh, false);
    
    return mesh;
}

int main()
{
    // Initialization
    const int screenWidth = 1200;
    const int screenHeight = 800;
    const int numStars = 500;
    const float baseSpeed = 0.005f;      // Base speed (very slow)
    const float speedVariation = 0.0025f; // Speed variation based on depth

    InitWindow(screenWidth, screenHeight, "Torus - Star Field");
    
    // Initialize 3D camera
    Camera3D camera = { 0 };
    camera.position = (Vector3){ 25.0f, 15.0f, 25.0f }; // Isometric view
    camera.target = (Vector3){ 0.0f, 0.0f, 0.0f };      // Looking at center
    camera.up = (Vector3){ 0.0f, 1.0f, 0.0f };          // Standard up vector
    camera.fovy = 45.0f;                                 // Field-of-view
    camera.projection = CAMERA_PERSPECTIVE;              // Projection type

    SetTargetFPS(60);

    // Create stars
    Star stars[numStars];
    
    // Initialize stars with random positions and speeds
    for (int i = 0; i < numStars; i++)
    {
        stars[i].x = (float)(GetRandomValue(-screenWidth/2, screenWidth/2));
        stars[i].y = (float)(GetRandomValue(-screenHeight/2, screenHeight/2));
        stars[i].z = (float)GetRandomValue(1, 1000) / 1000.0f;
        stars[i].speed = baseSpeed + (1.0f - stars[i].z) * speedVariation;
        stars[i].color = WHITE;
        
        if (GetRandomValue(0, 100) < 20)
        {
            int colorChoice = GetRandomValue(0, 3);
            switch (colorChoice)
            {
                case 0: stars[i].color = SKYBLUE; break;
                case 1: stars[i].color = YELLOW; break;
                case 2: stars[i].color = LIGHTGRAY; break;
                default: stars[i].color = WHITE; break;
            }
        }
    }
    
    // Create custom FLAT SHADED torus mesh
    // Radius 12.0f (Less wide), tube radius 3.0f
    // 9 columns, 8 rows = 72 faces
    Mesh torusMesh = GenFlatShadedTorus(12.0f, 3.0f, 9, 8);
    Model torusModel = LoadModelFromMesh(torusMesh);
    
    // Use default material but ensure it uses vertex colors
    torusModel.materials[0].maps[MATERIAL_MAP_DIFFUSE].color = WHITE;
    
    // Load lighting shader
    Shader shader = LoadShader("src/lighting.vs", "src/lighting.fs");
    
    // Get shader locations
    shader.locs[SHADER_LOC_VECTOR_VIEW] = GetShaderLocation(shader, "viewPos");
    int ambientLoc = GetShaderLocation(shader, "ambientColor");
    int lightPosLoc = GetShaderLocation(shader, "lightPos");
    int lightColLoc = GetShaderLocation(shader, "lightColor");
    int lightPos2Loc = GetShaderLocation(shader, "lightPos2");
    int lightCol2Loc = GetShaderLocation(shader, "lightColor2");
    int lightPos3Loc = GetShaderLocation(shader, "lightPos3");
    int lightCol3Loc = GetShaderLocation(shader, "lightColor3");
    int lightPos4Loc = GetShaderLocation(shader, "lightPos4");
    int lightCol4Loc = GetShaderLocation(shader, "lightColor4");
    
    // Camera Spot Light locs
    int lightPos5Loc = GetShaderLocation(shader, "lightPos5");
    int lightDir5Loc = GetShaderLocation(shader, "lightDir5");
    int lightCol5Loc = GetShaderLocation(shader, "lightColor5");
    int lightCut5Loc = GetShaderLocation(shader, "lightCutoff5");
    
    // Set shader values
    float ambient[3] = { 0.1f, 0.1f, 0.1f }; // Dark ambient
    SetShaderValue(shader, ambientLoc, ambient, SHADER_UNIFORM_VEC3);
    
    // Light 1: From Above (Bright)
    float lightColor[3] = { 0.8f, 0.8f, 0.8f }; 
    SetShaderValue(shader, lightColLoc, lightColor, SHADER_UNIFORM_VEC3);
    
    Vector3 lightPos = { 0.0f, 50.0f, 0.0f }; 
    SetShaderValue(shader, lightPosLoc, &lightPos, SHADER_UNIFORM_VEC3);

    // Light 2: From Left (Dim)
    float lightColor2[3] = { 0.4f, 0.4f, 0.4f }; 
    SetShaderValue(shader, lightCol2Loc, lightColor2, SHADER_UNIFORM_VEC3);
    
    Vector3 lightPos2 = { -50.0f, 0.0f, 0.0f }; 
    SetShaderValue(shader, lightPos2Loc, &lightPos2, SHADER_UNIFORM_VEC3);

    // Light 3: From Top-Left (Bright Spot)
    float lightColor3[3] = { 1.0f, 1.0f, 1.0f }; 
    SetShaderValue(shader, lightCol3Loc, lightColor3, SHADER_UNIFORM_VEC3);
    
    Vector3 lightPos3 = { -40.0f, 40.0f, 20.0f }; 
    SetShaderValue(shader, lightPos3Loc, &lightPos3, SHADER_UNIFORM_VEC3);
    
    // Light 4: Top Down (Light Blue)
    float lightColor4[3] = { 0.8f, 0.9f, 1.0f }; // Very Light Blue
    SetShaderValue(shader, lightCol4Loc, lightColor4, SHADER_UNIFORM_VEC3);
    
    Vector3 lightPos4 = { 0.0f, 100.0f, 0.0f }; // Directly Above
    SetShaderValue(shader, lightPos4Loc, &lightPos4, SHADER_UNIFORM_VEC3);

    // Light 5: Camera Spot (Sky Blue) - Dynamic update in loop
    float lightColor5[3] = { 0.53f, 0.81f, 0.92f }; // Sky Blue
    SetShaderValue(shader, lightCol5Loc, lightColor5, SHADER_UNIFORM_VEC3);
    
    float cutoff5 = cosf(30.0f * DEG2RAD); // 30 degree cone
    SetShaderValue(shader, lightCut5Loc, &cutoff5, SHADER_UNIFORM_FLOAT);

    // Apply shader to torus
    torusModel.materials[0].shader = shader;
    
    // Disable backface culling for safety
    rlDisableBackfaceCulling();
    
    // Rotation angle for torus
    float torusRotation = 0.0f;

    // Main game loop
    while (!WindowShouldClose())
    {
        // Update torus rotation
        torusRotation += 0.5f * GetFrameTime();
        if (torusRotation >= 360.0f) torusRotation -= 360.0f;
        
        // Update camera position for shader (specular)
        float cameraPos[3] = { camera.position.x, camera.position.y, camera.position.z };
        SetShaderValue(shader, shader.locs[SHADER_LOC_VECTOR_VIEW], cameraPos, SHADER_UNIFORM_VEC3);
        
        // Update Camera Spot Light (Light 5)
        SetShaderValue(shader, lightPos5Loc, cameraPos, SHADER_UNIFORM_VEC3);
        Vector3 camDir = Vector3Normalize(Vector3Subtract(camera.target, camera.position));
        float camDirArr[3] = { camDir.x, camDir.y, camDir.z };
        SetShaderValue(shader, lightDir5Loc, camDirArr, SHADER_UNIFORM_VEC3);
        
        // Update stars
        for (int i = 0; i < numStars; i++)
        {
            stars[i].z -= stars[i].speed * GetFrameTime() * 1.5f;

            if (stars[i].z <= 0.0f)
            {
                stars[i].x = (float)(GetRandomValue(-screenWidth/2, screenWidth/2));
                stars[i].y = (float)(GetRandomValue(-screenHeight/2, screenHeight/2));
                stars[i].z = 1.0f; 
                stars[i].speed = baseSpeed + (1.0f - stars[i].z) * speedVariation;
            }
        }

        // Draw
        BeginDrawing();

        ClearBackground(BLACK);

        // Draw stars (Background)
        for (int i = 0; i < numStars; i++)
        {
            float perspective = 1.0f / stars[i].z;
            float x = stars[i].x * perspective + screenWidth / 2.0f;
            float y = stars[i].y * perspective + screenHeight / 2.0f;

            if (x >= 0 && x < screenWidth && y >= 0 && y < screenHeight)
            {
                float size = (1.0f - stars[i].z) * 3.0f;
                if (size < 1.0f) size = 1.0f;
                if (size > 3.0f) size = 3.0f;

                float brightness = 1.0f - stars[i].z;
                Color starColor = {
                    (unsigned char)(stars[i].color.r * brightness),
                    (unsigned char)(stars[i].color.g * brightness),
                    (unsigned char)(stars[i].color.b * brightness),
                    255
                };

                DrawCircle((int)x, (int)y, size, starColor);
            }
        }
        
        // Draw 3D torus (Foreground)
        BeginMode3D(camera);
        
        // Disable culling
        rlDisableBackfaceCulling();
        
        // Draw torus in the center
        DrawModelEx(torusModel, 
                   (Vector3){ 0.0f, 0.0f, 0.0f },  
                   (Vector3){ 0.0f, 1.0f, 0.0f },  // Rotation axis (Y-axis spin)
                   torusRotation,                    
                   (Vector3){ 1.0f, 1.0f, 1.0f },  
                   WHITE);                          
        
        // Re-enable culling
        rlEnableBackfaceCulling();
        
        EndMode3D();

        // Draw instructions
        DrawText("Star Field - Press ESC to exit", 10, 10, 20, GRAY);

        EndDrawing();
    }

    // De-Initialization
    UnloadShader(shader);
    UnloadModel(torusModel);  
    CloseWindow();

    return 0;
}
