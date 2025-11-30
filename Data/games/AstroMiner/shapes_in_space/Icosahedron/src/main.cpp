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

// Function to generate an Icosahedron mesh with FLAT shading
Mesh GenFlatShadedIcosahedron(float scale)
{
    Mesh mesh = { 0 };
    
    // Golden ratio
    float phi = (1.0f + sqrtf(5.0f)) / 2.0f;
    
    // 12 Vertices
    // Defined using the golden rectangles method
    Vector3 verts[12] = {
        {-1,  phi, 0}, { 1,  phi, 0}, {-1, -phi, 0}, { 1, -phi, 0},
        { 0, -1,  phi}, { 0,  1,  phi}, { 0, -1, -phi}, { 0,  1, -phi},
        { phi, 0, -1}, { phi, 0,  1}, {-phi, 0, -1}, {-phi, 0,  1}
    };
    
    // 20 Faces (Indices into verts array) - CCW winding
    int indices[20][3] = {
        {0, 11, 5}, {0, 5, 1}, {0, 1, 7}, {0, 7, 10}, {0, 10, 11},
        {1, 5, 9}, {5, 11, 4}, {11, 10, 2}, {10, 7, 6}, {7, 1, 8},
        {3, 9, 4}, {3, 4, 2}, {3, 2, 6}, {3, 6, 8}, {3, 8, 9},
        {4, 9, 5}, {2, 4, 11}, {6, 2, 10}, {8, 6, 7}, {9, 8, 1}
    };
    
    int numFaces = 20;
    int numVertices = numFaces * 3; 
    
    mesh.vertexCount = numVertices;
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
        
        // Scale
        p0 = Vector3Scale(p0, scale);
        p1 = Vector3Scale(p1, scale);
        p2 = Vector3Scale(p2, scale);
        
        // Flat Normal
        Vector3 edge1 = Vector3Subtract(p1, p0);
        Vector3 edge2 = Vector3Subtract(p2, p0);
        Vector3 normal = Vector3Normalize(Vector3CrossProduct(edge1, edge2));
        
        // Color based on face center Y
        Vector3 center = Vector3Scale(Vector3Add(Vector3Add(p0, p1), p2), 1.0f/3.0f);
        // Normalize Y relative to the max height (approx scale * phi)
        float normalizedY = center.y / (scale * phi); 
        
        Color faceColor;
        // Use bands similar to the torus
        if (normalizedY > 0.25f)       faceColor = LIGHTGRAY; // Top faces
        else if (normalizedY < -0.25f) faceColor = DARKGRAY;  // Bottom faces
        else                           faceColor = GRAY;      // Middle faces
        
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
            
            mesh.indices[iIndex++] = vIndex;
            vIndex++;
        };
        
        AddVertex(p0);
        AddVertex(p1);
        AddVertex(p2);
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

    InitWindow(screenWidth, screenHeight, "Icosahedron - Star Field");
    
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
    
    // Create custom FLAT SHADED Icosahedron mesh
    // Scale 6.0f (25% smaller than 8.0f)
    Mesh icoMesh = GenFlatShadedIcosahedron(6.0f);
    Model icoModel = LoadModelFromMesh(icoMesh);
    
    // Use default material but ensure it uses vertex colors
    icoModel.materials[0].maps[MATERIAL_MAP_DIFFUSE].color = WHITE;
    
    // Load lighting shader (same as Torus)
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
    float lightColor[3] = { 0.4f, 0.4f, 0.4f }; 
    SetShaderValue(shader, lightColLoc, lightColor, SHADER_UNIFORM_VEC3);
    
    Vector3 lightPos = { 0.0f, 50.0f, 0.0f }; 
    SetShaderValue(shader, lightPosLoc, &lightPos, SHADER_UNIFORM_VEC3);

    // Light 2: From Left (Dim)
    float lightColor2[3] = { 0.2f, 0.2f, 0.2f }; 
    SetShaderValue(shader, lightCol2Loc, lightColor2, SHADER_UNIFORM_VEC3);
    
    Vector3 lightPos2 = { -50.0f, 0.0f, 0.0f }; 
    SetShaderValue(shader, lightPos2Loc, &lightPos2, SHADER_UNIFORM_VEC3);

    // Light 3: From Top-Left (Bright Spot)
    float lightColor3[3] = { 0.5f, 0.5f, 0.5f }; 
    SetShaderValue(shader, lightCol3Loc, lightColor3, SHADER_UNIFORM_VEC3);
    
    Vector3 lightPos3 = { -40.0f, 40.0f, 20.0f }; 
    SetShaderValue(shader, lightPos3Loc, &lightPos3, SHADER_UNIFORM_VEC3);
    
    // Light 4: Top Down (Light Blue)
    float lightColor4[3] = { 0.4f, 0.45f, 0.5f }; // Very Light Blue
    SetShaderValue(shader, lightCol4Loc, lightColor4, SHADER_UNIFORM_VEC3);
    
    Vector3 lightPos4 = { 0.0f, 100.0f, 0.0f }; // Directly Above
    SetShaderValue(shader, lightPos4Loc, &lightPos4, SHADER_UNIFORM_VEC3);

    // Light 5: Camera Spot (Sky Blue) - Dynamic update in loop
    float lightColor5[3] = { 0.265f, 0.405f, 0.46f }; // Sky Blue
    SetShaderValue(shader, lightCol5Loc, lightColor5, SHADER_UNIFORM_VEC3);
    
    float cutoff5 = cosf(30.0f * DEG2RAD); // 30 degree cone
    SetShaderValue(shader, lightCut5Loc, &cutoff5, SHADER_UNIFORM_FLOAT);

    // Apply shader to model
    icoModel.materials[0].shader = shader;
    
    // Disable backface culling for safety
    rlDisableBackfaceCulling();
    
    // Rotation angle
    float rotation = 0.0f;

    // Main game loop
    while (!WindowShouldClose())
    {
        // Update rotation
        rotation += 0.5f * GetFrameTime();
        if (rotation >= 360.0f) rotation -= 360.0f;
        
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
        
        // Draw 3D Icosahedron (Foreground)
        BeginMode3D(camera);
        
        // Disable culling
        rlDisableBackfaceCulling();
        
        // Draw icosahedron in the center
        DrawModelEx(icoModel, 
                   (Vector3){ 0.0f, 0.0f, 0.0f },  
                   (Vector3){ 0.0f, 1.0f, 0.0f },  // Rotation axis (Y-axis spin)
                   rotation,                    
                   (Vector3){ 1.0f, 1.0f, 1.0f },  
                   WHITE);                          
        
        // Re-enable culling
        rlEnableBackfaceCulling();
        
        EndMode3D();

        // Draw instructions
        DrawText("Star Field - Icosahedron - Press ESC to exit", 10, 10, 20, GRAY);

        EndDrawing();
    }

    // De-Initialization
    UnloadShader(shader);
    UnloadModel(icoModel);  
    CloseWindow();

    return 0;
}
