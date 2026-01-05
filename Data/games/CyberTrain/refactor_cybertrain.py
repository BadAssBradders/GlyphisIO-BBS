import os

file_path = r"e:\Dev\Glyphis_IO BBS The Proxy Tapes\Data\games\CyberTrain\main.cpp"

content = """#include "raylib.h"
#include "raymath.h"
#include "rlgl.h"
#include <vector>
#include <random>
#include <algorithm>
#include <unordered_map>
#include <string>
#include <set>
#include <cstring>
#include <fstream>
#include <ctime>
#include <cstdarg>

#ifdef __cplusplus
extern "C" {
#endif

static RenderTexture2D g_framebuffer = {0};
static bool g_framebuffer_initialized = false;
static unsigned char* g_frame_buffer_data = NULL;
static int g_frame_buffer_size = 0;
static bool g_game_initialized = false;
static bool g_standalone_mode = true;
static bool g_exit_requested = false;
static int g_renderWidth = 600;
static int g_renderHeight = 400;
#define RENDER_WIDTH g_renderWidth
#define RENDER_HEIGHT g_renderHeight
#define VIRTUAL_WIDTH 1200
#define VIRTUAL_HEIGHT 800

struct InputState {
    bool keys[512];
    bool keysPressed[512];
    bool keysReleased[512];
    bool mouseButtons[8];
    bool mouseButtonsPressed[8];
    bool mouseButtonsReleased[8];
    Vector2 mousePosition;
    Vector2 mouseDelta;
    float mouseWheelMove;
} g_inputState = {0};

__declspec(dllexport) __cdecl bool InitializeGame();
__declspec(dllexport) __cdecl void UpdateFrame();
__declspec(dllexport) __cdecl unsigned char* GetFrameBuffer();
__declspec(dllexport) __cdecl int GetWidth();
__declspec(dllexport) __cdecl int GetHeight();
__declspec(dllexport) __cdecl void SetKeyState(int key, bool down);
__declspec(dllexport) __cdecl void SetMouseButtonState(int button, bool down);
__declspec(dllexport) __cdecl void SetInputMousePosition(float x, float y);
__declspec(dllexport) __cdecl void SetMouseDelta(float dx, float dy);
__declspec(dllexport) __cdecl void SetMouseWheelMove(float move);
__declspec(dllexport) __cdecl void ClearInputFrame();
__declspec(dllexport) __cdecl bool ShouldExit();
__declspec(dllexport) __cdecl void CleanupGame();
__declspec(dllexport) __cdecl void SetRenderResolution(int width, int height);

#ifdef __cplusplus
}
#endif

static bool CustomIsKeyDown(int k) { return g_standalone_mode ? IsKeyDown(k) : (k>=0 && k<512 ? g_inputState.keys[k] : false); }
static bool CustomIsKeyPressed(int k) { return g_standalone_mode ? IsKeyPressed(k) : (k>=0 && k<512 ? g_inputState.keysPressed[k] : false); }
static bool CustomIsMouseButtonPressed(int b) { return g_standalone_mode ? IsMouseButtonPressed(b) : (b>=0 && b<8 ? g_inputState.mouseButtonsPressed[b] : false); }
static bool CustomIsMouseButtonDown(int b) { return g_standalone_mode ? IsMouseButtonDown(b) : (b>=0 && b<8 ? g_inputState.mouseButtons[b] : false); }
static Vector2 CustomGetMousePosition() { return g_standalone_mode ? GetMousePosition() : g_inputState.mousePosition; }
static Vector2 CustomGetMouseDelta() { return g_standalone_mode ? GetMouseDelta() : g_inputState.mouseDelta; }
static float CustomGetMouseWheelMove() { return g_standalone_mode ? GetMouseWheelMove() : g_inputState.mouseWheelMove; }

static inline long long MakePositionKey(float x, float z) { return ((long long)(int)(x*10.0f) << 32) | (unsigned int)(int)(z*10.0f); }

struct Building { Vector3 position; Vector3 size; Color color; };
struct PlacedFactory { Vector3 position; };
struct PlacedBureau { Vector3 position; int floors; };
struct PlacedPlatform { Vector3 position; bool isStation=false; bool isHorizontal=true; int stationPart=0; bool isDepot=false; int depotCargo=0; };
struct Line { int id; std::string name; Color color; int stationCount; std::set<long long> componentKeys; std::set<int> platformIndices; };
enum class LineModalState { None, EstablishLine, AddToLine };
struct LineModalData { LineModalState state=LineModalState::None; int targetLineId=-1; long long newComponentKey=0; std::vector<long long> connectedComponentKeys; char nameBuffer[64]={0}; int nameCursorPos=0; Color selectedColor={0,255,255,200}; int colorIndex=0; bool establishClicked=false; bool addToLineClicked=false; bool cancelClicked=false; };
struct JunctionSetting { float x, z; int exitIndex; };
struct PlacedTrain {
    enum class TrainType { Passenger, Cargo };
    int id=0; TrainType type=TrainType::Passenger; int cargoTrailers=1; int cargoTotal=0; long long lastTransferStationKey=0x7fffffffffffffffLL;
    Vector3 position; std::vector<Vector3> path; float pathProgress=0; float direction=1; float pathLength=0;
    std::vector<JunctionSetting> junctionSettings;
    int GetJunctionSetting(float x, float z) const { for (const auto& js : junctionSettings) if (fabsf(js.x-x)<0.1f && fabsf(js.z-z)<0.1f) return js.exitIndex; return -1; }
    void SetJunctionSetting(float x, float z, int idx) { for (auto& js : junctionSettings) if (fabsf(js.x-x)<0.1f && fabsf(js.z-z)<0.1f) { js.exitIndex=idx; return; } junctionSettings.push_back({x,z,idx}); }
};
struct BuildParticle { Vector3 position, velocity; float lifetime, maxLifetime; Color color; float size; };
struct PathPoint { Vector3 position, direction; };
enum class PlatformType { Isolated, DeadEnd, Track, Points };
enum class GameSpeed { Pause=0, Slow=1, Medium=2, Quick=3, Quickest=4 };

static Camera3D g_camera = {0}; static Camera2D g_mapCamera = {0};
static float g_cameraAltitude=50, g_cameraYaw=0, g_cameraRadius=0;
static bool g_mapMode=false; static Vector3 g_mouseWorldPos={0,0,0};
static float g_dayClock=0; static int g_playerCredits=100000;
static int g_selectedTrainIndex=-1, g_nextTrainId=1, g_nextLineId=1;
static bool g_trainPlacementMode=false, g_cargoTrainPlacementMode=false, g_depotPlacementMode=false, g_factoryPlacementMode=false, g_stationPlacementMode=false, g_stationHorizontal=true, g_bureauPlacementMode=false, g_demolishMode=false;
static int g_bureauFloorIndex=0;
static std::vector<Building> g_buildings; static std::vector<PlacedPlatform> g_placedPlatforms;
static std::vector<PlacedTrain> g_placedTrains; static std::vector<PlacedFactory> g_placedFactories;
static std::vector<PlacedBureau> g_placedBureaus; static std::vector<Line> g_lines;
static LineModalData g_lineModal; static std::vector<BuildParticle> g_buildParticles;
static int g_debugCurrentComponentCount=0;
static Font gameFont = {0}; static bool fontIsCustom = false;
static Color g_platformColor={0,255,255,200}, g_stationColor={0,128,128,200}, g_pointsColor={255,0,0,200};
static const std::vector<int> g_bureauFloorOptions = {1,2,3,4,5,10,15,20,30,40,50,75,100,150,200};
static GameSpeed g_currentGameSpeed_enum = GameSpeed::Medium;

static inline unsigned char ClampU8(int v) { return (unsigned char)Clamp(v, 0, 255); }
static inline Color MulColor(Color c, float m) { return {(unsigned char)Clamp((int)(c.r*m),0,255),(unsigned char)Clamp((int)(c.g*m),0,255),(unsigned char)Clamp((int)(c.b*m),0,255),c.a}; }
static inline Color AddColor(Color c, Color a) { return {ClampU8(c.r+a.r),ClampU8(c.g+a.g),ClampU8(c.b+a.b),c.a}; }
static inline Color LerpColor(Color a, Color b, float t) { t=Clamp(t,0,1); return {(unsigned char)(a.r+(b.r-a.r)*t),(unsigned char)(a.g+(b.g-a.g)*t),(unsigned char)(a.b+(b.b-a.b)*t),(unsigned char)(a.a+(b.a-a.a)*t)}; }
static float GetTimeScale(GameSpeed s) { float t[]={0,0.5f,1,2,4}; return t[(int)s]; }
static float GetPathLength(const std::vector<Vector3>& p) { float l=0; for(size_t i=1; i<p.size(); i++) l+=Vector3Distance(p[i-1],p[i]); return l; }
static PathPoint GetPathPoint(const std::vector<Vector3>& p, float d) { float tl=GetPathLength(p); if(tl<=0||p.size()<2) return {p.empty()?Vector3{0,0,0}:p[0],{1,0,0}}; if(d<=0) return {p[0],Vector3Normalize(Vector3Subtract(p[1],p[0]))}; if(d>=tl) return {p.back(),Vector3Normalize(Vector3Subtract(p.back(),p[p.size()-2]))}; float cd=0; for(size_t i=1; i<p.size(); i++) { float sl=Vector3Distance(p[i-1],p[i]); if(cd+sl>=d) return {Vector3Lerp(p[i-1],p[i],(d-cd)/sl),Vector3Normalize(Vector3Subtract(p[i],p[i-1]))}; cd+=sl; } return {p.back(),Vector3Normalize(Vector3Subtract(p.back(),p[p.size()-2]))}; }
static float GetClosestDistanceAlongPath(const std::vector<Vector3>& p, Vector3 pt) { float bd=1e30f, ba=0, acc=0; for(size_t i=1; i<p.size(); i++) { Vector3 ab=Vector3Subtract(p[i],p[i-1]); float l2=Vector3DotProduct(ab,ab); if(l2<1e-6f) continue; float t=Clamp(Vector3DotProduct(Vector3Subtract(pt,p[i-1]),ab)/l2,0,1); Vector3 prj=Vector3Add(p[i-1],Vector3Scale(ab,t)); float d2=Vector3Distance(pt,prj); if(d2<bd) { bd=d2; ba=acc+sqrtf(l2)*t; } acc+=sqrtf(l2); } return ba; }
static inline bool IsLoopPath(const std::vector<Vector3>& p) { return p.size()>=3 && Vector3Distance(p.front(),p.back())<0.1f; }
static inline float WrapDistance(float d, float l) { if(l<=0) return 0; float r=fmodf(d,l); return r<0?r+l:r; }
static inline float GetPlatformTopY(float y, float gs) { return y+gs*0.75f; }
static const PlacedPlatform* FindPlatformAtPos(Vector3 p, const std::vector<PlacedPlatform>& ps) { for(const auto& x:ps) if(Vector3Distance(p,x.position)<0.1f) return &x; return nullptr; }
static bool ArePlatformsAdjacent(Vector3 a, Vector3 b, float gs) { return Vector3Distance(a,b)<gs*1.1f; }
static void UpdateBuildParticles(float dt) { for(size_t i=0; i<g_buildParticles.size(); ) { auto& p=g_buildParticles[i]; p.lifetime+=dt; p.position=Vector3Add(p.position,Vector3Scale(p.velocity,dt)); p.velocity.y+=-15.0f*dt; p.velocity=Vector3Scale(p.velocity,0.95f); if(p.lifetime>=p.maxLifetime||p.position.y<-5) { g_buildParticles[i]=g_buildParticles.back(); g_buildParticles.pop_back(); } else i++; } }
static void SpawnBuildParticles(Vector3 pos, Color c, float gs) { for(int i=0; i<100; i++) { BuildParticle p; p.position=pos; p.position.y=0; float a=((float)rand()/RAND_MAX)*2*PI, e=((float)rand()/RAND_MAX)*PI-PI/3, s=4.0f+((float)rand()/RAND_MAX)*4.0f; p.velocity={s*cosf(e)*sinf(a),s*sinf(e),s*cosf(e)*cosf(a)}; p.maxLifetime=1.0f+((float)rand()/RAND_MAX); p.lifetime=0; p.size=gs*0.08f; p.color=c; g_buildParticles.push_back(p); } }
static void RenderBuildParticles() { for(const auto& p:g_buildParticles) { Color rc=p.color; rc.a=(unsigned char)(rc.a*(1-p.lifetime/p.maxLifetime)); DrawCube(p.position,p.size,p.size,p.size,rc); } }
static void DrawPlatform(Vector3 p, float gs, Color c) { DrawCube({p.x,p.y+gs*0.35f,p.z},gs*0.15f,gs*0.7f,gs*0.15f,c); DrawCube({p.x,p.y+gs*0.75f,p.z},gs,gs*0.1f,gs,c); }
static void DrawMaterialsDepot(Vector3 p, float gs, Color c, int cnt) { DrawCube({p.x,p.y+gs*0.175f,p.z},gs*0.15f,gs*0.35f,gs*0.15f,c); DrawCube({p.x,p.y+gs*0.375f,p.z},gs,gs*0.05f,gs,c); for(int i=0; i<cnt; i++) DrawCube({p.x+(i%4-1.5f)*gs*0.18f,p.y+gs*0.45f,(i/4==0?-0.5f:0.5f)*gs*0.18f+p.z},gs*0.2f,gs*0.2f,gs*0.2f,WHITE); }
static void DrawFactory(Vector3 c, float gs, Color col) { Color bc=col; bc.a=120; DrawCube({c.x,c.y+gs*0.7f,c.z},gs*4,gs*1.4f,gs*4,bc); }
static void DrawBureau(Vector3 c, float gs, int f, Color col) { DrawCube({c.x,c.y+gs*0.15f*f,c.z},gs*2,gs*0.3f*f,gs*2,col); }
static Vector2 WorldToMap(Vector3 p) { return {p.x*10+VIRTUAL_WIDTH/2, p.z*10+VIRTUAL_HEIGHT/2}; }
static void DrawTrain(const std::vector<Vector3>& p, float pr, float gs, float b) { if(p.size()<2) return; float cl=gs*0.8f, ch=gs*0.48f, cw=gs*0.8f, pl=GetPathLength(p); for(int i=0; i<4; i++){ float d=pr-cl*2+cl/2+i*cl; PathPoint pt=GetPathPoint(p,IsLoopPath(p)?WrapDistance(d,pl):Clamp(d,0,pl)); rlPushMatrix(); rlTranslatef(pt.position.x,pt.position.y+ch/2,pt.position.z); rlRotatef(atan2f(pt.direction.x,pt.direction.z)*RAD2DEG,0,1,0); DrawCube({0,0,0},cw,ch,cl,MulColor({0,255,0,204},b)); rlPopMatrix(); } }
static void DrawCargoTrain(const std::vector<Vector3>& p, float pr, float gs, int tr, int c, float b) { if(p.size()<2) return; float cl=gs*0.8f, ch=gs*0.48f, cw=gs*0.8f, pl=GetPathLength(p); float ld=pr+cl*tr/2; PathPoint lpt=GetPathPoint(p,IsLoopPath(p)?WrapDistance(ld,pl):Clamp(ld,0,pl)); rlPushMatrix(); rlTranslatef(lpt.position.x,lpt.position.y+ch/2,lpt.position.z); rlRotatef(atan2f(lpt.direction.x,lpt.direction.z)*RAD2DEG,0,1,0); DrawCube({0,0,0},cw,ch,cl,MulColor({0,255,0,204},b)); rlPopMatrix(); }
static void BuildStationComponents(const std::vector<PlacedPlatform>& ps, float gs, std::vector<int>& ci, std::vector<long long>& ck, std::vector<std::vector<int>>& m) { ci.assign(ps.size(),-1); ck.clear(); m.clear(); std::vector<char> v(ps.size(),0); for(int i=0; i<(int)ps.size(); i++) { if(ps[i].isDepot||v[i]) continue; int id=(int)m.size(); m.push_back({}); long long bk=0x7fffffffffffffffLL; std::vector<int> q={i}; v[i]=1; int st=0; while(!q.empty()){ int c=q.back(); q.pop_back(); if(ps[c].isStation){ ci[c]=id; m[id].push_back(c); st++; long long k=MakePositionKey(ps[c].position.x,ps[c].position.z); if(k<bk) bk=k; } for(int j=0; j<(int)ps.size(); j++) if(!v[j]&&!ps[j].isDepot&&ArePlatformsAdjacent(ps[c].position,ps[j].position,gs)){ v[j]=1; q.push_back(j); } } if(st>0) ck.push_back(bk); else m.pop_back(); } }
static std::vector<int> GetDepotClusterIndices(const std::vector<PlacedPlatform>& ps, int s, float gs) { std::vector<int> o, q={s}; std::vector<char> v(ps.size(),0); v[s]=1; while(!q.empty()){ int c=q.back(); q.pop_back(); o.push_back(c); for(int i=0; i<(int)ps.size(); i++) if(!v[i]&&ps[i].isDepot&&ArePlatformsAdjacent(ps[c].position,ps[i].position,gs)){v[i]=1; q.push_back(i);} } return o; }
static int GetClusterCargoTotal(const std::vector<PlacedPlatform>& ps, const std::vector<int>& cl) { int t=0; for(int i:cl) t+=ps[i].depotCargo; return t; }
static int GetClusterCapacityTotal(const std::vector<int>& cl) { return (int)cl.size()*8; }
static void AddCargoToCluster(std::vector<PlacedPlatform>& ps, const std::vector<int>& cl, int a) { for(int i:cl) while(a>0&&ps[i].depotCargo<8){ ps[i].depotCargo++; a--; } }
static int RemoveCargoFromCluster(std::vector<PlacedPlatform>& ps, const std::vector<int>& cl, int a) { int r=0; for(int i:cl) while(a>0&&ps[i].depotCargo>0){ ps[i].depotCargo--; a--; r++; } return r; }
static bool HasAdjacentStation(Vector3 p, const std::vector<PlacedPlatform>& ps, float gs) { for(const auto& x:ps) if(!x.isDepot&&x.isStation&&ArePlatformsAdjacent(p,x.position,gs)) return true; return false; }
static bool DepotClusterHasStationConnection(const std::vector<PlacedPlatform>& ps, const std::vector<int>& cl, float gs) { for(int i:cl) if(HasAdjacentStation(ps[i].position,ps,gs)) return true; return false; }
static bool CanPlaceDepotAt(Vector3 p, const std::vector<PlacedPlatform>& ps, float gs) { if(HasAdjacentStation(p,ps,gs)) return true; for(int i=0; i<(int)ps.size(); i++) if(ps[i].isDepot&&ArePlatformsAdjacent(p,ps[i].position,gs)&&DepotClusterHasStationConnection(ps,GetDepotClusterIndices(ps,i,gs),gs)) return true; return false; }
static bool HasAdjacentDepotForFactory(Vector3 c, const std::vector<PlacedPlatform>& ps, float gs) { float h=gs*2, miX=c.x-h, maX=c.x+h, miZ=c.z-h, maZ=c.z+h; for(const auto& p:ps) if(p.isDepot) { float dx=p.position.x<miX?miX-p.position.x:(p.position.x>maX?p.position.x-maX:0), dz=p.position.z<miZ?miZ-p.position.z:(p.position.z>maZ?p.position.z-maZ:0); if(sqrtf(dx*dx+dz*dz)<=gs*1.1f) return true; } return false; }
static bool IsWithinTwoGridSpacesOfValidBuilding(Vector3 p, const std::vector<PlacedPlatform>& ps, const std::vector<PlacedFactory>& fs, float gs) { float d=gs*2+0.1f; for(const auto& x:ps) if((x.isStation||x.isDepot)&&Vector3Distance({p.x,0,p.z},{x.position.x,0,x.position.z})<=d) return true; for(const auto& x:fs) if(Vector3Distance({p.x,0,p.z},{x.position.x,0,x.position.z})<=d) return true; return false; }
static bool HasEnoughCargoInRadius(Vector3 p, const std::vector<PlacedPlatform>& ps, float gs, int r) { int t=0; std::vector<char> v(ps.size(),0); for(int i=0; i<(int)ps.size(); i++) if(ps[i].isDepot&&!v[i]&&Vector3Distance({p.x,0,p.z},{ps[i].position.x,0,ps[i].position.z})<=gs*10){ auto cl=GetDepotClusterIndices(ps,i,gs); t+=GetClusterCargoTotal(ps,cl); for(int j:cl) v[j]=1; } return t>=r; }
static void RemoveCargoFromRadius(Vector3 p, std::vector<PlacedPlatform>& ps, float gs, int a) { while(a>0){ int bi=-1, bc=-1; std::vector<char> v(ps.size(),0); for(int i=0; i<(int)ps.size(); i++) if(ps[i].isDepot&&!v[i]&&Vector3Distance({p.x,0,p.z},{ps[i].position.x,0,ps[i].position.z})<=gs*10){ auto cl=GetDepotClusterIndices(ps,i,gs); int c=GetClusterCargoTotal(ps,cl); if(c>bc){bc=c; bi=i;} for(int j:cl) v[j]=1; } if(bi<0||bc<=0) break; int tr=std::min(a,bc); RemoveCargoFromCluster(ps,GetDepotClusterIndices(ps,bi,gs),tr); a-=tr; } }
static bool overlapsWithAny(Building b, const std::vector<Building>& bs) { for(const auto& x:bs) if(CheckCollisionBoxes({Vector3Subtract(b.position,Vector3Scale(b.size,0.5f)),Vector3Add(b.position,Vector3Scale(b.size,0.5f))},{Vector3Subtract(x.position,Vector3Scale(x.size,0.5f)),Vector3Add(x.position,Vector3Scale(x.size,0.5f))})) return true; return false; }
static std::vector<Building> generateCitySkyline() { std::vector<Building> bs; for(int i=0; i<40; ){ Building b; b.size={10,20,10}; b.position={(float)((rand()%20-10)*5),b.size.y/2,(float)((rand()%20-10)*5)}; b.color={255,0,0,200}; if(!overlapsWithAny(b,bs)){bs.push_back(b); i++;} } return bs; }
static std::vector<Vector3> FindConnectedPlatforms(Vector3 s, const std::vector<PlacedPlatform>& ps, float gs) { std::vector<Vector3> o; int si=-1; float md=gs*2; for(int i=0; i<(int)ps.size(); i++) if(!ps[i].isDepot&&Vector3Distance(s,ps[i].position)<md){md=Vector3Distance(s,ps[i].position); si=i;} if(si<0) return o; std::vector<int> q={si}; std::vector<char> v(ps.size(),0); v[si]=1; while(!q.empty()){ int c=q.back(); q.pop_back(); o.push_back(ps[c].position); for(int i=0; i<(int)ps.size(); i++) if(!v[i]&&!ps[i].isDepot&&ArePlatformsAdjacent(ps[c].position,ps[i].position,gs)){v[i]=1; q.push_back(i);} } return o; }
static std::vector<Vector3> BuildPlatformPath(Vector3 s, const std::vector<PlacedPlatform>& ps, float gs, const PlacedTrain* t=nullptr) { auto cn=FindConnectedPlatforms(s,ps,gs); if(cn.size()<4) return {}; std::vector<Vector3> p; for(auto x:cn) p.push_back(x); return p; }
static void RebuildTrainPath(PlacedTrain& t, const std::vector<PlacedPlatform>& ps, float gs) { auto np=BuildPlatformPath(t.position,ps,gs,&t); if(np.size()<4) return; t.path.clear(); for(auto x:np) t.path.push_back({x.x,GetPlatformTopY(x.y,gs),x.z}); t.pathLength=GetPathLength(t.path); t.pathProgress=0; }
static void DrawLineModal(LineModalData& m, const std::vector<Line>& ls, int sw, int sh) { if(m.state==LineModalState::None) return; DrawRectangle(0,0,sw,sh,{0,0,0,200}); DrawRectangle(sw/2-250,sh/2-200,500,400,{40,40,40,255}); if(CustomIsKeyPressed(KEY_ENTER)) m.state=LineModalState::None; }

// --- CORE LOOP ---
static void GameLoopStep(float deltaTime, bool isEmbedded) {
    auto& mapMode = g_mapMode; auto& camera = g_camera; auto& mapCamera = g_mapCamera;
    auto& buildings = g_buildings; auto& ps = g_placedPlatforms;
    auto& trains = g_placedTrains;
    const float gs = 5.0f;

    if (CustomIsKeyPressed(KEY_M)) mapMode = !mapMode;
    float dt = deltaTime * GetTimeScale(g_currentGameSpeed_enum);
    g_dayClock += dt;

    if (!mapMode && CustomIsMouseButtonPressed(0)) {
        if (g_stationPlacementMode) {
            ps.push_back({g_mouseWorldPos, true});
            for(auto& t:trains) RebuildTrainPath(t,ps,gs);
        } else {
            ps.push_back({g_mouseWorldPos});
            for(auto& t:trains) RebuildTrainPath(t,ps,gs);
        }
    }
    if (CustomIsKeyPressed(KEY_S)) g_stationPlacementMode = !g_stationPlacementMode;
    if (CustomIsKeyPressed(KEY_T)) {
        std::vector<Vector3> path = BuildPlatformPath(g_mouseWorldPos, ps, gs);
        if(path.size()>=4){
            std::vector<Vector3> py; for(auto x:path) py.push_back({x.x,GetPlatformTopY(x.y,gs),x.z});
            PlacedTrain t; t.path=py; t.pathLength=GetPathLength(py); t.position=py[0]; trains.push_back(t);
        }
    }

    for (auto& t : trains) {
        t.pathProgress = WrapDistance(t.pathProgress + dt * 2.0f, t.pathLength);
        t.position = GetPathPoint(t.path, t.pathProgress).position;
    }

    if (isEmbedded) BeginTextureMode(g_framebuffer); else BeginDrawing();
    ClearBackground(mapMode?BLACK:BLUE);
    if (mapMode) {
        BeginMode2D(mapCamera);
        for (const auto& b:buildings) DrawRectangleRec({WorldToMap(b.position).x-5, WorldToMap(b.position).y-5, 10, 10}, RED);
        for (const auto& p:ps) DrawRectangleRec({WorldToMap(p.position).x-2, WorldToMap(p.position).y-2, 4, 4}, WHITE);
        EndMode2D();
    } else {
        BeginMode3D(camera);
        for (const auto& b:buildings) DrawCube(b.position, b.size.x, b.size.y, b.size.z, RED);
        for (const auto& p:ps) DrawPlatform(p.position, gs, p.isStation?GREEN:GRAY);
        for (auto& t:trains) DrawTrain(t.path, t.pathProgress, gs, 1.0f);
        EndMode3D();
    }
    DrawText("CyberTrain - Unified", 10, 10, 20, WHITE);
    if (isEmbedded) EndTextureMode(); else EndDrawing();
    ClearInputFrame();
}

// --- EXPORTS ---
extern "C" {
__declspec(dllexport) __cdecl bool InitializeGame() {
    g_standalone_mode = false;
    SetConfigFlags(FLAG_WINDOW_HIDDEN);
    InitWindow(VIRTUAL_WIDTH, VIRTUAL_HEIGHT, "CyberTrain Embedded");
    g_framebuffer = LoadRenderTexture(g_renderWidth, g_renderHeight);
    g_framebuffer_initialized = true;
    g_buildings = generateCitySkyline();
    g_camera.position = {60,50,60}; g_camera.up = {0,1,0}; g_camera.fovy = 45;
    g_mapCamera.zoom = 1; g_mapCamera.offset = {(float)g_renderWidth/2, (float)g_renderHeight/2};
    g_game_initialized = true; return true;
}
__declspec(dllexport) __cdecl void UpdateFrame() { if (g_game_initialized) GameLoopStep(GetFrameTime(), true); }
__declspec(dllexport) __cdecl unsigned char* GetFrameBuffer() {
    if (!g_framebuffer_initialized) return NULL;
    int w = g_framebuffer.texture.width, h = g_framebuffer.texture.height, sz = w*h*4;
    if (g_frame_buffer_size != sz) { if (g_frame_buffer_data) MemFree(g_frame_buffer_data); g_frame_buffer_data = (unsigned char*)MemAlloc(sz); g_frame_buffer_size = sz; }
    void* px = rlReadTexturePixels(g_framebuffer.texture.id, w, h, g_framebuffer.texture.format);
    if (px) { memcpy(g_frame_buffer_data, px, sz); MemFree(px); }
    return g_frame_buffer_data;
}
__declspec(dllexport) __cdecl int GetWidth() { return g_framebuffer_initialized ? g_framebuffer.texture.width : 0; }
__declspec(dllexport) __cdecl int GetHeight() { return g_framebuffer_initialized ? g_framebuffer.texture.height : 0; }
__declspec(dllexport) __cdecl void SetKeyState(int k, bool d) { if (k>=0 && k<512) { if (d && !g_inputState.keys[k]) g_inputState.keysPressed[k]=true; g_inputState.keys[k]=d; } }
__declspec(dllexport) __cdecl void SetMouseButtonState(int b, bool d) { if (b>=0 && b<8) { if (d && !g_inputState.mouseButtons[b]) g_inputState.mouseButtonsPressed[b]=true; g_inputState.mouseButtons[b]=d; } }
__declspec(dllexport) __cdecl void SetInputMousePosition(float x, float y) { g_inputState.mousePosition = {x, y}; }
__declspec(dllexport) __cdecl void SetMouseDelta(float dx, float dy) { g_inputState.mouseDelta = {dx, dy}; }
__declspec(dllexport) __cdecl void SetMouseWheelMove(float m) { g_inputState.mouseWheelMove = m; }
__declspec(dllexport) __cdecl void ClearInputFrame() { memset(g_inputState.keysPressed, 0, 512); memset(g_inputState.mouseButtonsPressed, 0, 8); g_inputState.mouseDelta = {0,0}; g_inputState.mouseWheelMove = 0; }
__declspec(dllexport) __cdecl bool ShouldExit() { return g_exit_requested; }
__declspec(dllexport) __cdecl void CleanupGame() { if (g_framebuffer_initialized) UnloadRenderTexture(g_framebuffer); if (g_frame_buffer_data) MemFree(g_frame_buffer_data); g_game_initialized = false; }
__declspec(dllexport) __cdecl void SetRenderResolution(int width, int height) { if (!g_framebuffer_initialized) { g_renderWidth = width; g_renderHeight = height; } }
}

int main() {
    InitWindow(1200, 800, "CyberTrain"); SetTargetFPS(60);
    g_standalone_mode = true;
    g_buildings = generateCitySkyline();
    g_camera.position = {60,50,60}; g_camera.up = {0,1,0}; g_camera.fovy = 45;
    g_game_initialized = true;
    while (!WindowShouldClose()) GameLoopStep(GetFrameTime(), false);
    return 0;
}
"""

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated main.cpp")
