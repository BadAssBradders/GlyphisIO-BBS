# Technical Specification: Station Viewport Module

**To:** Engineering Team  
**From:** [Your Name]  
**Subject:** Implementation of 3D Station Pre-Launch Viewport  

We are adding a dynamic "Hangar View" to the pre-mission GUI. This viewport will display the currently selected Space Station (represented by procedurally generated 3D artifacts) within the UI dashboard.

### 1. Asset Isolation (Crucial)
To prevent conflicts with the existing landing sequence shaders, the prototype shaders have been renamed. Please import them as follows:

*   `src/lighting.vs` $\rightarrow$ Rename to `station_artifact.vs`
*   `src/lighting.fs` $\rightarrow$ Rename to `station_artifact.fs`

### 2. Architecture: The `StationViewport` Class

We should encapsulate this logic into a dedicated class/struct rather than polluting the main game loop. This class will manage its own Render Target (Framebuffer).

```cpp
enum StationType {
    STATION_ALPHA,  // Torus
    STATION_BETA,   // Icosahedron
    STATION_GAMMA,  // Torus (Variant)
    STATION_DELTA   // Icosahedron (Variant)
};

class StationViewport {
private:
    // Rendering Context
    RenderTexture2D viewTarget; // The "Screen" texture
    Camera3D camera;
    Shader shader;
    
    // Assets
    Mesh meshTorus;
    Model modelTorus;
    Mesh meshIco;
    Model modelIco;
    
    // State
    std::vector<Star> stars;
    float rotation;
    
    // Shader Uniform Locations
    int locViewPos;
    // ... light locations ...

public:
    void Init(int width, int height); // Size of the window inside the GUI
    void Update();
    void Render(StationType activeStation); // Renders to the internal texture
    Texture2D GetTexture(); // Returns the rendered frame
    void Cleanup();
};
```

### 3. Implementation Details

#### A. Initialization
Initialize the `RenderTexture2D` with the exact pixel dimensions of the "window" in your PNG overlay.

```cpp
void StationViewport::Init(int width, int height) {
    // 1. Create Framebuffer
    viewTarget = LoadRenderTexture(width, height);
    
    // 2. Load dedicated shaders
    shader = LoadShader("station_artifact.vs", "station_artifact.fs");
    
    // 3. Generate Geometry (Reuse functions provided in prototype)
    meshTorus = GenTorus(4.0f, 1.0f, 32, 32);
    modelTorus = LoadModelFromMesh(meshTorus);
    modelTorus.materials[0].shader = shader; // Assign custom shader
    
    meshIco = GenFlatShadedIcosahedron(6.0f);
    modelIco = LoadModelFromMesh(meshIco);
    modelIco.materials[0].shader = shader;
    
    // 4. Setup Fixed Camera
    camera = { 0 };
    camera.position = (Vector3){ 25.0f, 15.0f, 25.0f };
    camera.target = (Vector3){ 0.0f, 0.0f, 0.0f };
    camera.up = (Vector3){ 0.0f, 1.0f, 0.0f };
    camera.fovy = 45.0f;
    camera.projection = CAMERA_PERSPECTIVE;
}
```

#### B. The "Off-Screen" Render Pass
We render the stars and shape into the texture, not the screen. This allows perfect layering.

```cpp
void StationViewport::Render(StationType activeStation) {
    // RENDER TO TEXTURE
    BeginTextureMode(viewTarget);
        ClearBackground(BLACK);
        
        // 1. Draw Starfield (2D background within the window)
        // ... (Insert Star loop from prototype) ...
        
        // 2. Draw 3D Artifact
        BeginMode3D(camera);
            rlDisableBackfaceCulling();
            
            // Update Lighting Uniforms
            float camPos[3] = { camera.position.x, camera.position.y, camera.position.z };
            SetShaderValue(shader, locViewPos, camPos, SHADER_UNIFORM_VEC3);
            
            // Select Model based on Station ID
            Model* targetModel = nullptr;
            Color tint = WHITE;
            
            switch (activeStation) {
                case STATION_ALPHA: targetModel = &modelTorus; break;
                case STATION_BETA:  targetModel = &modelIco; break;
                // Reuse meshes for other stations with different colors?
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
```

### 4. Integration into Main Scene
This is how you layer it in the main game loop (Python/C++ wrapper):

```cpp
// In your Main Game Loop

// 1. Update the viewport logic
stationViewport.Update();

// 2. Draw the 3D scene into its private texture
stationViewport.Render(currentStationId);

// 3. Draw the Main Scene Composition
BeginDrawing();
    ClearBackground(DARKGRAY); // Or main game background

    // Layer 1: The Station Viewport Texture
    // Draw it at the specific coordinates where the "window" is
    // Note: RenderTextures are flipped vertically in OpenGL, so we flip the source rect
    Rectangle srcRect = { 0, 0, (float)viewTarget.texture.width, (float)-viewTarget.texture.height };
    Rectangle destRect = { 100, 100, 400, 300 }; // Coordinates on screen
    DrawTexturePro(stationViewport.GetTexture(), srcRect, destRect, {0,0}, 0.0f, WHITE);

    // Layer 2: The GUI Overlay (PNG)
    // This PNG should have a transparent hole where the viewport goes
    DrawTexture(guiOverlayTexture, 0, 0, WHITE);
    
    // Layer 3: Buttons/Text
    DrawText("LAUNCH MISSION", 500, 500, 20, GREEN);

EndDrawing();
```

### Summary of Benefits
1.  **Safety:** Renaming shaders prevents regression in the landing sequence.
2.  **Clipping:** The `RenderTexture` ensures stars don't "leak" out of the GUI window.
3.  **Flexibility:** We can resize, move, or fade the station view independently of the 3D rendering logic.
4.  **Reusability:** We support 4 stations using just 2 meshes by Tinting or applying different shader uniforms per frame.

