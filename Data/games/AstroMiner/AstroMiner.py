import sys
import math
import random
import ctypes
import os
import site

# ------------------------------------------------------------
# 1. ROBUST LIBRARY LOADING
# ------------------------------------------------------------
def load_raylib_library():
    lib_names = ["raylib.dll", "libraylib.so", "libraylib.dylib"]
    search_paths = [os.getcwd(), os.path.dirname(os.path.abspath(__file__))]
    for site_pkg in site.getsitepackages():
        search_paths.append(site_pkg)
        search_paths.append(os.path.join(site_pkg, "raylib"))

    found_lib_path = None
    for path in search_paths:
        for name in lib_names:
            full_path = os.path.join(path, name)
            if os.path.exists(full_path):
                found_lib_path = full_path
                break
        if found_lib_path: break
    
    if found_lib_path:
        print(f"INFO: Loading Raylib binary from: {found_lib_path}")
        return ctypes.CDLL(found_lib_path)
    else:
        try:
            if sys.platform == "win32": return ctypes.CDLL("raylib.dll")
            elif sys.platform == "darwin": return ctypes.CDLL("libraylib.dylib")
            else: return ctypes.CDLL("libraylib.so")
        except:
            return None

rl = load_raylib_library()
if not rl:
    print("CRITICAL ERROR: Could not load raylib shared library.")
    sys.exit(1)

# ------------------------------------------------------------
# 2. CTYPES STRUCTURE DEFINITIONS
# ------------------------------------------------------------
class Vector2(ctypes.Structure):
    _fields_ = [("x", ctypes.c_float), ("y", ctypes.c_float)]
    def __init__(self, x=0.0, y=0.0): super().__init__(x, y)

class Vector3(ctypes.Structure):
    _fields_ = [("x", ctypes.c_float), ("y", ctypes.c_float), ("z", ctypes.c_float)]
    def __init__(self, x=0.0, y=0.0, z=0.0): super().__init__(x, y, z)

class Vector4(ctypes.Structure):
    _fields_ = [("x", ctypes.c_float), ("y", ctypes.c_float), ("z", ctypes.c_float), ("w", ctypes.c_float)]
    def __init__(self, x=0.0, y=0.0, z=0.0, w=0.0): super().__init__(x, y, z, w)

class Matrix(ctypes.Structure):
    _fields_ = [
        ("m0", ctypes.c_float), ("m4", ctypes.c_float), ("m8", ctypes.c_float), ("m12", ctypes.c_float),
        ("m1", ctypes.c_float), ("m5", ctypes.c_float), ("m9", ctypes.c_float), ("m13", ctypes.c_float),
        ("m2", ctypes.c_float), ("m6", ctypes.c_float), ("m10", ctypes.c_float), ("m14", ctypes.c_float),
        ("m3", ctypes.c_float), ("m7", ctypes.c_float), ("m11", ctypes.c_float), ("m15", ctypes.c_float)
    ]

class Color(ctypes.Structure):
    _fields_ = [("r", ctypes.c_ubyte), ("g", ctypes.c_ubyte), ("b", ctypes.c_ubyte), ("a", ctypes.c_ubyte)]
    def __init__(self, r=255, g=255, b=255, a=255): super().__init__(r, g, b, a)

class Camera3D(ctypes.Structure):
    _fields_ = [("position", Vector3), ("target", Vector3), ("up", Vector3), ("fovy", ctypes.c_float), ("projection", ctypes.c_int)]

class Mesh(ctypes.Structure):
    _fields_ = [
        ("vertexCount", ctypes.c_int),
        ("triangleCount", ctypes.c_int),
        ("vertices", ctypes.POINTER(ctypes.c_float)),
        ("texcoords", ctypes.POINTER(ctypes.c_float)),
        ("texcoords2", ctypes.POINTER(ctypes.c_float)),
        ("normals", ctypes.POINTER(ctypes.c_float)),
        ("tangents", ctypes.POINTER(ctypes.c_float)),
        ("colors", ctypes.POINTER(ctypes.c_ubyte)),
        ("indices", ctypes.POINTER(ctypes.c_ushort)),
        ("animVertices", ctypes.POINTER(ctypes.c_float)),
        ("animNormals", ctypes.POINTER(ctypes.c_float)),
        ("boneIds", ctypes.POINTER(ctypes.c_ubyte)),
        ("boneWeights", ctypes.POINTER(ctypes.c_float)),
        ("vaoId", ctypes.c_uint),
        ("vboId", ctypes.POINTER(ctypes.c_uint))
    ]

class Shader(ctypes.Structure):
    _fields_ = [("id", ctypes.c_uint), ("locs", ctypes.POINTER(ctypes.c_int))]

class Texture2D(ctypes.Structure):
    _fields_ = [("id", ctypes.c_uint), ("width", ctypes.c_int), ("height", ctypes.c_int), ("mipmaps", ctypes.c_int), ("format", ctypes.c_int)]

class Rectangle(ctypes.Structure):
    _fields_ = [("x", ctypes.c_float), ("y", ctypes.c_float), ("width", ctypes.c_float), ("height", ctypes.c_float)]
    def __init__(self, x=0.0, y=0.0, width=0.0, height=0.0): super().__init__(x, y, width, height)

class MaterialMap(ctypes.Structure):
    _fields_ = [("texture", Texture2D), ("color", Color), ("value", ctypes.c_float)]

class Material(ctypes.Structure):
    _fields_ = [("shader", Shader), ("maps", ctypes.POINTER(MaterialMap)), ("params", ctypes.c_float * 4)]

class Transform(ctypes.Structure):
    _fields_ = [("translation", Vector3), ("rotation", Vector4), ("scale", Vector3)]

class BoneInfo(ctypes.Structure):
    _fields_ = [("name", ctypes.c_char * 32), ("parent", ctypes.c_int)]

class Model(ctypes.Structure):
    _fields_ = [
        ("transform", Matrix),
        ("meshCount", ctypes.c_int),
        ("materialCount", ctypes.c_int),
        ("meshes", ctypes.POINTER(Mesh)),
        ("materials", ctypes.POINTER(Material)),
        ("meshMaterial", ctypes.POINTER(ctypes.c_int)),
        ("boneCount", ctypes.c_int),
        ("bones", ctypes.POINTER(BoneInfo)),
        ("bindPose", ctypes.POINTER(Transform))
    ]

# ------------------------------------------------------------
# 3. FUNCTION BINDINGS
# ------------------------------------------------------------
rl.InitWindow.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_char_p]
rl.SetTargetFPS.argtypes = [ctypes.c_int]
rl.WindowShouldClose.restype = ctypes.c_bool
rl.CloseWindow.argtypes = []
rl.DisableCursor.argtypes = []
rl.GetFrameTime.restype = ctypes.c_float
rl.GetTime.restype = ctypes.c_double
rl.IsKeyDown.argtypes = [ctypes.c_int]; rl.IsKeyDown.restype = ctypes.c_bool
rl.IsKeyPressed.argtypes = [ctypes.c_int]; rl.IsKeyPressed.restype = ctypes.c_bool
rl.IsMouseButtonDown.argtypes = [ctypes.c_int]; rl.IsMouseButtonDown.restype = ctypes.c_bool
rl.IsMouseButtonReleased.argtypes = [ctypes.c_int]; rl.IsMouseButtonReleased.restype = ctypes.c_bool
rl.GetMouseDelta.restype = Vector2
rl.BeginDrawing.argtypes = []
rl.EndDrawing.argtypes = []
rl.ClearBackground.argtypes = [Color]
rl.BeginMode3D.argtypes = [Camera3D]
rl.EndMode3D.argtypes = []
rl.DrawFPS.argtypes = [ctypes.c_int, ctypes.c_int]
rl.DrawText.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, Color]
rl.DrawRectangle.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, Color]
rl.DrawRectangleLines.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, Color]
rl.DrawCircle.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_float, Color]
rl.DrawCircleLines.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_float, Color]
rl.DrawCube.argtypes = [Vector3, ctypes.c_float, ctypes.c_float, ctypes.c_float, Color]
rl.MeasureText.argtypes = [ctypes.c_char_p, ctypes.c_int]; rl.MeasureText.restype = ctypes.c_int
rl.UploadMesh.argtypes = [ctypes.POINTER(Mesh), ctypes.c_bool]
rl.LoadModelFromMesh.argtypes = [Mesh]; rl.LoadModelFromMesh.restype = Model
rl.UnloadModel.argtypes = [Model]
rl.DrawModel.argtypes = [Model, Vector3, ctypes.c_float, Color]
rl.DrawModelEx.argtypes = [Model, Vector3, Vector3, ctypes.c_float, Vector3, Color]
rl.rlDisableBackfaceCulling.argtypes = []
rl.rlEnableBackfaceCulling.argtypes = []
rl.rlBegin.argtypes = [ctypes.c_int]
rl.rlEnd.argtypes = []
rl.rlColor4ub.argtypes = [ctypes.c_ubyte, ctypes.c_ubyte, ctypes.c_ubyte, ctypes.c_ubyte]
rl.rlVertex3f.argtypes = [ctypes.c_float, ctypes.c_float, ctypes.c_float]
rl.LoadTexture.argtypes = [ctypes.c_char_p]; rl.LoadTexture.restype = Texture2D
rl.UnloadTexture.argtypes = [Texture2D]
rl.DrawTexture.argtypes = [Texture2D, ctypes.c_int, ctypes.c_int, Color]
rl.DrawTexturePro.argtypes = [Texture2D, Rectangle, Rectangle, Vector2, ctypes.c_float, Color]

# Constants
CAMERA_PERSPECTIVE = 0
WHITE = Color(255, 255, 255, 255); BLACK = Color(0, 0, 0, 255)
RED = Color(230, 41, 55, 255); GREEN = Color(0, 228, 48, 255)
BLUE = Color(0, 121, 241, 255); SKYBLUE = Color(102, 191, 255, 255)
DARKGRAY = Color(80, 80, 80, 255); GRAY = Color(130, 130, 130, 255)
YELLOW = Color(253, 249, 0, 255); ORANGE = Color(255, 161, 0, 255); GOLD = Color(255, 203, 0, 255)
KEY_RIGHT = 262; KEY_LEFT = 263; KEY_DOWN = 264; KEY_UP = 265; KEY_SPACE = 32; KEY_ENTER = 257; KEY_W = 87
MOUSE_LEFT_BUTTON = 0; MOUSE_RIGHT_BUTTON = 1
RL_QUADS = 7
DEG2RAD = math.pi / 180.0

# ------------------------------------------------------------
# 4. MATH IMPLEMENTATIONS
# ------------------------------------------------------------
def vec3_add(v1, v2): return Vector3(v1.x + v2.x, v1.y + v2.y, v1.z + v2.z)
def vec3_sub(v1, v2): return Vector3(v1.x - v2.x, v1.y - v2.y, v1.z - v2.z)
def vec3_scale(v, s): return Vector3(v.x * s, v.y * s, v.z * s)
def vec3_length(v): return math.sqrt(v.x*v.x + v.y*v.y + v.z*v.z)
def vec3_normalize(v):
    l = vec3_length(v)
    if l == 0: return Vector3(0,0,0)
    return Vector3(v.x/l, v.y/l, v.z/l)
def vec3_cross(v1, v2): return Vector3(v1.y*v2.z - v1.z*v2.y, v1.z*v2.x - v1.x*v2.z, v1.x*v2.y - v1.y*v2.x)
def vec3_transform(v, mat):
    x, y, z = v.x, v.y, v.z
    return Vector3(mat.m0*x + mat.m4*y + mat.m8*z + mat.m12, mat.m1*x + mat.m5*y + mat.m9*z + mat.m13, mat.m2*x + mat.m6*y + mat.m10*z + mat.m14)
def matrix_identity(): m = Matrix(); m.m0 = m.m5 = m.m10 = m.m15 = 1.0; return m
def matrix_translate(x, y, z): m = matrix_identity(); m.m12 = x; m.m13 = y; m.m14 = z; return m
def matrix_scale(x, y, z): m = matrix_identity(); m.m0 = x; m.m5 = y; m.m10 = z; return m
def matrix_rotate_x(angle): m = matrix_identity(); c = math.cos(angle); s = math.sin(angle); m.m5 = c; m.m6 = -s; m.m9 = s; m.m10 = c; return m
def matrix_rotate_y(angle): m = matrix_identity(); c = math.cos(angle); s = math.sin(angle); m.m0 = c; m.m2 = s; m.m8 = -s; m.m10 = c; return m
def matrix_rotate_z(angle): m = matrix_identity(); c = math.cos(angle); s = math.sin(angle); m.m0 = c; m.m1 = -s; m.m4 = s; m.m5 = c; return m
def matrix_rotate(axis, angle):
    mat = matrix_identity(); x, y, z = axis.x, axis.y, axis.z
    ls = x*x + y*y + z*z
    if ls != 1.0 and ls != 0.0: il = 1.0/math.sqrt(ls); x*=il; y*=il; z*=il
    si = math.sin(angle); co = math.cos(angle); t = 1.0 - co
    mat.m0 = x*x*t + co; mat.m1 = y*x*t + z*si; mat.m2 = z*x*t - y*si
    mat.m4 = x*y*t - z*si; mat.m5 = y*y*t + co; mat.m6 = z*y*t + x*si
    mat.m8 = x*z*t + y*si; mat.m9 = y*z*t - x*si; mat.m10 = z*z*t + co
    return mat
def matrix_multiply(l, r):
    res = Matrix()
    res.m0 = l.m0*r.m0 + l.m4*r.m1 + l.m8*r.m2 + l.m12*r.m3; res.m4 = l.m0*r.m4 + l.m4*r.m5 + l.m8*r.m6 + l.m12*r.m7; res.m8 = l.m0*r.m8 + l.m4*r.m9 + l.m8*r.m10 + l.m12*r.m11; res.m12 = l.m0*r.m12 + l.m4*r.m13 + l.m8*r.m14 + l.m12*r.m15
    res.m1 = l.m1*r.m0 + l.m5*r.m1 + l.m9*r.m2 + l.m13*r.m3; res.m5 = l.m1*r.m4 + l.m5*r.m5 + l.m9*r.m6 + l.m13*r.m7; res.m9 = l.m1*r.m8 + l.m5*r.m9 + l.m9*r.m10 + l.m13*r.m11; res.m13 = l.m1*r.m12 + l.m5*r.m13 + l.m9*r.m14 + l.m13*r.m15
    res.m2 = l.m2*r.m0 + l.m6*r.m1 + l.m10*r.m2 + l.m14*r.m3; res.m6 = l.m2*r.m4 + l.m6*r.m5 + l.m10*r.m6 + l.m14*r.m7; res.m10 = l.m2*r.m8 + l.m6*r.m9 + l.m10*r.m10 + l.m14*r.m11; res.m14 = l.m2*r.m12 + l.m6*r.m13 + l.m10*r.m14 + l.m14*r.m15
    res.m3 = l.m3*r.m0 + l.m7*r.m1 + l.m11*r.m2 + l.m15*r.m3; res.m7 = l.m3*r.m4 + l.m7*r.m5 + l.m11*r.m6 + l.m15*r.m7; res.m11 = l.m3*r.m8 + l.m7*r.m9 + l.m11*r.m10 + l.m15*r.m11; res.m15 = l.m3*r.m12 + l.m7*r.m13 + l.m11*r.m14 + l.m15*r.m15
    return res

# ------------------------------------------------------------
# GAME LOGIC & STATE
# ------------------------------------------------------------
class GameState:
    PROSPECT_MAP, LANDER, DRILLING, DEBRIS, DEPOT_SELECT = 0, 1, 2, 3, 4
    DEPOT_HOME, BAR, SHIPYARD, MARKET, LODGINGS = 5, 6, 7, 8, 9

class PlayerData:
    def __init__(self):
        self.fuel = 10.0; self.max_fuel = 10.0
        self.hull = 100.0; self.max_hull = 100.0
        self.credits = 500; self.cargo_space = 20; self.cargo_filled = 0
        self.iron = 0; self.gold = 0
G_Player = PlayerData()

NUM_ROCKS = 1000; PROSPECT_PERIMETER = 120.0; RENDER_DISTANCE = 15
CHUNK_SIZE = 8; CHUNKS_AXIS = int((PROSPECT_PERIMETER * 2) / CHUNK_SIZE)
TOTAL_CHUNKS = CHUNKS_AXIS * CHUNKS_AXIS; GRID_CELL_SIZE = 16.0
GRID_DIM = int((PROSPECT_PERIMETER * 2.0) / GRID_CELL_SIZE) + 2
MAX_ROCKS_PER_CELL = 128
TRIS_PER_ROCK = 36
ROCK_TRI_COUNT = NUM_ROCKS * TRIS_PER_ROCK
ship_gravity = -12.0; ship_thrust_power = 25.0; ship_drag_factor = 0.985; ship_fuel_burn_rate = 1.0 / 10.0

class Tri:
    def __init__(self): self.a = Vector3(); self.b = Vector3(); self.c = Vector3()
G_RockTris = [Tri() for _ in range(ROCK_TRI_COUNT)]

class RockInstance:
    def __init__(self): self.position = Vector3(); self.axis = Vector3(); self.angle = 0.0; self.scale = 1.0; self.color = WHITE
G_Rocks = [RockInstance() for _ in range(NUM_ROCKS)]

class GridCell:
    def __init__(self): self.count = 0; self.rock_indices = [0] * MAX_ROCKS_PER_CELL
G_CollisionGrid = [[GridCell() for _ in range(GRID_DIM)] for _ in range(GRID_DIM)]

class Particle:
    def __init__(self): self.pos = Vector3(); self.vel = Vector3(); self.color = WHITE; self.life = 0.0; self.on_ground = False
MAX_PARTICLES = 400; particles = [Particle() for _ in range(MAX_PARTICLES)]

def get_terrain_height(x, z):
    return 1.2 * math.sin(x * 0.15) + 0.8 * math.cos(z * 0.12) + 0.4 * math.sin((x + z) * 0.08)

def get_height_on_triangle(p1, p2, p3, x, z):
    det = (p2.z - p3.z) * (p1.x - p3.x) + (p3.x - p2.x) * (p1.z - p3.z)
    if abs(det) < 0.0001: return None
    l1 = ((p2.z - p3.z) * (x - p3.x) + (p3.x - p2.x) * (z - p3.z)) / det
    l2 = ((p3.z - p1.z) * (x - p3.x) + (p1.x - p3.x) * (z - p3.z)) / det
    l3 = 1.0 - l1 - l2
    if 0.0 <= l1 <= 1.0 and 0.0 <= l2 <= 1.0 and 0.0 <= l3 <= 1.0:
        return l1 * p1.y + l2 * p2.y + l3 * p3.y
    return None

def get_world_height(x, z):
    height = get_terrain_height(x, z)
    offset = PROSPECT_PERIMETER
    cell_x = int((x + offset) / GRID_CELL_SIZE)
    cell_z = int((z + offset) / GRID_CELL_SIZE)
    if 0 <= cell_x < GRID_DIM and 0 <= cell_z < GRID_DIM:
        cell = G_CollisionGrid[cell_x][cell_z]
        for i in range(cell.count):
            rock_idx = cell.rock_indices[i]
            start = rock_idx * 36
            for t in range(start, start + 36):
                tri_h = get_height_on_triangle(G_RockTris[t].a, G_RockTris[t].b, G_RockTris[t].c, x, z)
                if tri_h is not None and tri_h > height: height = tri_h
    return height

def init_collision_grid():
    for row in G_CollisionGrid:
        for c in row: c.count = 0
    offset = PROSPECT_PERIMETER
    for r in range(NUM_ROCKS):
        rad = G_Rocks[r].scale * 1.5
        pos = G_Rocks[r].position
        sx = max(0, min(int((pos.x - rad + offset) / GRID_CELL_SIZE), GRID_DIM - 1))
        ex = max(0, min(int((pos.x + rad + offset) / GRID_CELL_SIZE), GRID_DIM - 1))
        sz = max(0, min(int((pos.z - rad + offset) / GRID_CELL_SIZE), GRID_DIM - 1))
        ez = max(0, min(int((pos.z + rad + offset) / GRID_CELL_SIZE), GRID_DIM - 1))
        for x in range(sx, ex + 1):
            for z in range(sz, ez + 1):
                if G_CollisionGrid[x][z].count < MAX_ROCKS_PER_CELL:
                    G_CollisionGrid[x][z].rock_indices[G_CollisionGrid[x][z].count] = r
                    G_CollisionGrid[x][z].count += 1

# ------------------------------------------------------------
# ROBUST MESH GENERATION (Fix for Access Violation)
# ------------------------------------------------------------
def create_mesh_buffers(tri_count):
    m = Mesh()
    m.vertexCount = tri_count * 3
    m.triangleCount = tri_count
    
    # Create C arrays
    ArrayTypeF = ctypes.c_float * (m.vertexCount * 3)
    ArrayTypeUB = ctypes.c_ubyte * (m.vertexCount * 4)
    ArrayTypeUV = ctypes.c_float * (m.vertexCount * 2)
    ArrayTypeVBO = ctypes.c_uint * 7

    # Instantiate arrays and attach to mesh object to prevent GC
    m._vertices = ArrayTypeF()
    m._normals = ArrayTypeF()
    m._colors = ArrayTypeUB()
    m._texcoords = ArrayTypeUV()
    m._vboId_arr = ArrayTypeVBO() # Pre-allocate VBO array

    # Cast and assign pointers
    m.vertices = ctypes.cast(m._vertices, ctypes.POINTER(ctypes.c_float))
    m.normals = ctypes.cast(m._normals, ctypes.POINTER(ctypes.c_float))
    m.colors = ctypes.cast(m._colors, ctypes.POINTER(ctypes.c_ubyte))
    m.texcoords = ctypes.cast(m._texcoords, ctypes.POINTER(ctypes.c_float))
    m.vboId = ctypes.cast(m._vboId_arr, ctypes.POINTER(ctypes.c_uint))
    
    return m

def create_solid_ship():
    v = [
        Vector3(0,0.3,-0.2), Vector3(-0.8,0,-0.5), Vector3(0,0,1),
        Vector3(0,0.3,-0.2), Vector3(0,0,1), Vector3(0.8,0,-0.5),
        Vector3(0,0.3,-0.2), Vector3(0,0,-1), Vector3(-0.8,0,-0.5),
        Vector3(0,0.3,-0.2), Vector3(0.8,0,-0.5), Vector3(0,0,-1),
        Vector3(0,-0.3,-0.2), Vector3(0,0,1), Vector3(-0.8,0,-0.5),
        Vector3(0,-0.3,-0.2), Vector3(0.8,0,-0.5), Vector3(0,0,1),
        Vector3(0,-0.3,-0.2), Vector3(-0.8,0,-0.5), Vector3(0,0,-1),
        Vector3(0,-0.3,-0.2), Vector3(0,0,-1), Vector3(0.8,0,-0.5)
    ]
    c = [(135,206,250,255)]*3 + [(70,170,240,255)]*3 + [(30,144,255,255)]*3 + [(0,100,220,255)]*3 + \
        [(0,60,180,255)]*3 + [(0,40,140,255)]*3 + [(0,20,100,255)]*3 + [(0,5,60,255)]*3

    mesh = create_mesh_buffers(8)
    
    # Fill data directly into the kept-alive arrays using ctypes index access
    for i in range(24):
        mesh.vertices[i*3+0] = v[i].x; mesh.vertices[i*3+1] = v[i].y; mesh.vertices[i*3+2] = v[i].z
        ny = 1.0 if i < 12 else -1.0
        mesh.normals[i*3+0] = 0.0; mesh.normals[i*3+1] = ny; mesh.normals[i*3+2] = 0.0
        mesh.colors[i*4+0] = c[i][0]; mesh.colors[i*4+1] = c[i][1]; mesh.colors[i*4+2] = c[i][2]; mesh.colors[i*4+3] = c[i][3]
    
    # NO MANUAL UPLOAD to avoid warnings
    return mesh

def create_terrain_chunk(sx, sz, size):
    rng = int(size)
    mesh = create_mesh_buffers(rng * rng * 2)
    vert_counter = 0
    g1 = (80,80,80,255); g2 = (50,50,50,255)
    for z in range(rng):
        for x in range(rng):
            xf, zf = sx + x, sz + z
            y0 = get_terrain_height(xf, zf); y1 = get_terrain_height(xf, zf+1)
            y2 = get_terrain_height(xf+1, zf+1); y3 = get_terrain_height(xf+1, zf)
            gc = g1 if (int(abs(xf)) % 2 == int(abs(zf)) % 2) else g2
            
            def sv(vv):
                nonlocal vert_counter
                mesh.vertices[vert_counter*3+0] = vv.x; mesh.vertices[vert_counter*3+1] = vv.y; mesh.vertices[vert_counter*3+2] = vv.z
                mesh.normals[vert_counter*3+0] = 0.0; mesh.normals[vert_counter*3+1] = 1.0; mesh.normals[vert_counter*3+2] = 0.0
                mesh.colors[vert_counter*4+0] = gc[0]; mesh.colors[vert_counter*4+1] = gc[1]; mesh.colors[vert_counter*4+2] = gc[2]; mesh.colors[vert_counter*4+3] = gc[3]
                vert_counter += 1
            
            v1 = Vector3(xf, y0, zf); v2 = Vector3(xf, y1, zf+1); v3 = Vector3(xf+1, y2, zf+1); v4 = Vector3(xf+1, y3, zf)
            sv(v1); sv(v2); sv(v3); sv(v1); sv(v3); sv(v4)
    
    return mesh

def create_base_rock_mesh():
    phi = 1.618; inv = 1.0/phi
    v = [Vector3(1,1,1), Vector3(1,1,-1), Vector3(1,-1,1), Vector3(1,-1,-1), Vector3(-1,1,1), Vector3(-1,1,-1), Vector3(-1,-1,1), Vector3(-1,-1,-1),
         Vector3(0,inv,phi), Vector3(0,inv,-phi), Vector3(0,-inv,phi), Vector3(0,-inv,-phi), Vector3(inv,phi,0), Vector3(inv,-phi,0), Vector3(-inv,phi,0), Vector3(-inv,-phi,0),
         Vector3(phi,0,inv), Vector3(phi,0,-inv), Vector3(-phi,0,inv), Vector3(-phi,0,-inv)]
    faces = [[0,16,2,10,8], [0,8,4,14,12], [16,17,1,12,0], [1,9,11,3,17], [1,12,14,5,9], [2,13,15,6,10], [13,3,11,7,15], [4,8,10,6,18], [14,4,18,19,5], [5,19,7,11,9], [15,7,19,18,6], [2,16,17,3,13]]
    cols = [(80,80,80,255), (100,100,105,255), (90,85,80,255), (70,70,70,255), (60,60,65,255), (110,110,110,255), (55,55,55,255), (75,70,65,255), (65,65,65,255), (85,85,90,255), (45,45,50,255), (95,95,95,255)]
    
    mesh = create_mesh_buffers(36)
    idx = 0
    for f in range(12):
        fc = cols[f]
        p = [v[faces[f][i]] for i in range(5)]
        tris = [[0,1,2], [0,2,3], [0,3,4]]
        for t in range(3):
            for k in range(3):
                pt = p[tris[t][k]]
                mesh.vertices[idx*3+0] = pt.x; mesh.vertices[idx*3+1] = pt.y; mesh.vertices[idx*3+2] = pt.z
                mesh.normals[idx*3+0] = 0; mesh.normals[idx*3+1] = 1; mesh.normals[idx*3+2] = 0
                mesh.colors[idx*4+0] = fc[0]; mesh.colors[idx*4+1] = fc[1]; mesh.colors[idx*4+2] = fc[2]; mesh.colors[idx*4+3] = 255
                idx += 1
    return mesh

def generate_rocks():
    gt = 0; lim = int(PROSPECT_PERIMETER); cc = Vector3(0,0,0)
    v = [Vector3(1,1,1), Vector3(1,1,-1), Vector3(1,-1,1), Vector3(1,-1,-1), Vector3(-1,1,1), Vector3(-1,1,-1), Vector3(-1,-1,1), Vector3(-1,-1,-1)] 
    faces = [[0,1,2],[1,3,2],[4,5,6],[5,7,6],[0,1,4],[1,5,4],[2,3,6],[3,7,6],[0,2,4],[2,6,4],[1,3,5],[3,7,5]]
    
    for r in range(NUM_ROCKS):
        sc = random.randint(50, 300) / 100.0
        if r % 2 == 0: rx = float(random.randint(-lim, lim)); rz = float(random.randint(-lim, lim)); cc = Vector3(rx, 0, rz)
        else:
            ang = random.uniform(0, 360) * DEG2RAD; d = random.uniform(2, 6)
            rx = max(-lim, min(cc.x + math.cos(ang)*d, lim))
            rz = max(-lim, min(cc.z + math.sin(ang)*d, lim))
        
        ry = get_terrain_height(rx, rz) + (0.2 * sc)
        G_Rocks[r].position = Vector3(rx, ry, rz); G_Rocks[r].scale = sc; G_Rocks[r].axis = Vector3(0,1,0); G_Rocks[r].angle = 0
        G_Rocks[r].color = Color(random.randint(200,255), random.randint(200,255), random.randint(200,255), 255)
        
        ms = matrix_scale(sc, sc, sc); mt = matrix_translate(rx, ry, rz); mw = matrix_multiply(ms, mt)
        c_verts = [vec3_transform(p, mw) for p in v]
        
        local_tri_idx = 0
        for tri in faces:
            G_RockTris[gt].a = c_verts[tri[0]]; G_RockTris[gt].b = c_verts[tri[1]]; G_RockTris[gt].c = c_verts[tri[2]]
            gt += 1; local_tri_idx += 1
        gt += (TRIS_PER_ROCK - local_tri_idx)

# ------------------------------------------------------------
# UI & MAIN
# ------------------------------------------------------------
def draw_retro_window(title, x, y, w, h):
    rl.DrawRectangle(x, y, w, h, Color(10, 15, 30, 240))
    rl.DrawRectangleLines(x, y, w, h, Color(0, 255, 255, 255))
    rl.DrawRectangle(x, y, w, 30, Color(0, 255, 255, 255))
    rl.DrawText(title.encode('utf-8'), x + 10, y + 5, 20, BLACK)

def draw_button(text, x, y, w, h, sel):
    fill = Color(0, 100, 100, 255) if sel else Color(0, 40, 40, 255)
    border = WHITE if sel else Color(0, 255, 255, 255)
    rl.DrawRectangle(x, y, w, h, fill)
    rl.DrawRectangleLines(x, y, w, h, border)
    tw = rl.MeasureText(text.encode('utf-8'), 20)
    rl.DrawText(text.encode('utf-8'), x + (w - tw)//2, y + (h - 20)//2, 20, border)
    return sel and (rl.IsKeyPressed(KEY_ENTER) or rl.IsKeyPressed(KEY_SPACE))

def reset_state(state_ref, selection_ref, new_state):
    global depot_home_page
    state_ref[0] = new_state
    selection_ref[0] = 0
    # Reset depot_home page to 1 when entering DEPOT_HOME state
    if new_state == GameState.DEPOT_HOME:
        depot_home_page = 1

def draw_page_prospect_map(state_ref, selection_ref, ship_pos, ship_vel):
    rl.ClearBackground(Color(5, 5, 10, 255))
    draw_retro_window("PROSPECTING MAP - SELECT SECTOR", 50, 50, 1100, 700)
    sel = selection_ref[0]
    if rl.IsKeyPressed(KEY_RIGHT): sel = (sel + 3) % 15
    if rl.IsKeyPressed(KEY_LEFT): sel = (sel - 3 + 15) % 15
    if rl.IsKeyPressed(KEY_DOWN): sel = (sel + 1) % 15
    if rl.IsKeyPressed(KEY_UP): sel = (sel - 1 + 15) % 15
    selection_ref[0] = sel
    idx = 0
    for i in range(5):
        for j in range(3):
            bx = 150 + i * 200; by = 150 + j * 180
            s = (idx == sel)
            rl.DrawCircle(bx + 50, by + 50, 40, Color(80, 80, 80, 255))
            rl.DrawCircleLines(bx + 50, by + 50, 40, WHITE if s else DARKGRAY)
            if draw_button("SURVEY", bx, by + 100, 100, 30, s):
                ship_pos.x = 0; ship_pos.y = 60; ship_pos.z = -PROSPECT_PERIMETER
                ship_vel.x = 0; ship_vel.y = 0; ship_vel.z = 10
                reset_state(state_ref, selection_ref, GameState.LANDER)
            idx += 1
    rl.DrawText(b"ARROWS to Select, ENTER to Confirm", 60, 760, 20, GRAY)

def draw_page_drilling(state_ref, selection_ref):
    global drill_progress
    rl.ClearBackground(Color(20, 10, 5, 255))
    draw_retro_window("DRILLING OPERATION", 300, 200, 600, 400)
    drill_progress += rl.GetFrameTime() * 20.0
    if drill_progress > 100.0: drill_progress = 100.0
    rl.DrawText(b"DRILLING IN PROGRESS...", 450, 300, 20, WHITE)
    rl.DrawRectangle(350, 350, 500, 40, DARKGRAY)
    rl.DrawRectangle(350, 350, int(drill_progress * 5), 40, ORANGE)
    rl.DrawRectangleLines(350, 350, 500, 40, WHITE)
    if drill_progress >= 100.0:
        rl.DrawText(b"SUCCESS! RESOURCES ACQUIRED.", 420, 420, 20, GREEN)
        if draw_button("RETURN TO SHIP", 500, 500, 200, 40, True):
            G_Player.iron += random.randint(1, 3); G_Player.cargo_filled += 1
            reset_state(state_ref, selection_ref, GameState.LANDER)
            drill_progress = 0.0
drill_progress = 0.0

def draw_page_debris(state_ref, selection_ref):
    rl.ClearBackground(Color(5, 20, 10, 255))
    draw_retro_window("DEBRIS COLLECTION", 300, 200, 600, 400)
    rl.DrawText(b"Collecting Debris...", 450, 300, 20, GREEN)
    if draw_button("FINISH", 500, 500, 200, 40, True):
        G_Player.gold += 1; G_Player.cargo_filled += 1
        reset_state(state_ref, selection_ref, GameState.LANDER)

def draw_page_depot_select(state_ref, selection_ref):
    rl.ClearBackground(Color(10, 10, 30, 255))
    draw_retro_window("AVAILABLE DEPOTS", 100, 100, 1000, 600)
    sel = selection_ref[0]
    if rl.IsKeyPressed(KEY_RIGHT) or rl.IsKeyPressed(KEY_LEFT) or rl.IsKeyPressed(KEY_UP) or rl.IsKeyPressed(KEY_DOWN): sel = 1 if sel == 0 else 0
    selection_ref[0] = sel
    c1 = WHITE if sel == 0 else GRAY; c2 = WHITE if sel == 1 else GRAY
    rl.DrawCircle(400, 300, 60, BLUE); rl.DrawCircleLines(400, 300, 65, c1)
    rl.DrawText(b"ALPHA STATION", 350, 370, 20, c1)
    if draw_button("DOCK", 350, 400, 100, 30, sel == 0): reset_state(state_ref, selection_ref, GameState.DEPOT_HOME)
    rl.DrawCircle(800, 400, 40, PURPLE); rl.DrawCircleLines(800, 400, 45, c2)
    rl.DrawText(b"OUTPOST BETA", 750, 450, 20, c2)
    draw_button("LOCKED", 750, 480, 100, 30, sel == 1)

# Global variable to track depot_home page number (1-4)
depot_home_page = 1
depot_home_textures = {}  # Cache for loaded textures

def get_png_path(filename):
    """Get the full path to a PNG file in the AstroMiner directory."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    png_path = os.path.join(script_dir, filename)
    if os.path.exists(png_path):
        return png_path
    # Fallback: try Data/games/AstroMiner/ relative to project root
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(script_dir))))
    fallback_path = os.path.join(base_path, "Data", "games", "AstroMiner", filename)
    if os.path.exists(fallback_path):
        return fallback_path
    return png_path  # Return original path even if not found

def load_depot_texture(filename):
    """Load a texture for depot_home screen, with caching."""
    if filename in depot_home_textures:
        return depot_home_textures[filename]
    png_path = get_png_path(filename)
    try:
        # Convert to bytes for ctypes
        path_bytes = png_path.encode('utf-8') if isinstance(png_path, str) else png_path
        texture = rl.LoadTexture(path_bytes)
        depot_home_textures[filename] = texture
        return texture
    except Exception as e:
        print(f"Warning: Failed to load texture {filename}: {e}")
        return None

def draw_page_depot_home(state_ref, selection_ref):
    global depot_home_page
    
    rl.ClearBackground(Color(20, 20, 25, 255))
    
    # Handle page navigation with up/down arrows (pages 1-4)
    if rl.IsKeyPressed(KEY_DOWN):
        if depot_home_page < 4:
            depot_home_page += 1
    if rl.IsKeyPressed(KEY_UP):
        if depot_home_page > 1:
            depot_home_page -= 1
    
    # Map page number to PNG filename
    page_pngs = {
        1: "prospect_gui.png",
        2: "shipyard_gui.png",
        3: "commodities_gui.png",
        4: "bar_gui.png"
    }
    
    # Load and draw the appropriate PNG
    png_filename = page_pngs.get(depot_home_page, "prospect_gui.png")
    texture = load_depot_texture(png_filename)
    
    if texture:
        # Draw the texture to fill the screen (or a specific area)
        # Using DrawTexturePro for better control
        screen_width = 1200  # Window width
        screen_height = 800  # Window height
        src_rect = Rectangle(0, 0, texture.width, texture.height)
        dest_rect = Rectangle(0, 0, screen_width, screen_height)
        origin = Vector2(0, 0)
        rl.DrawTexturePro(texture, src_rect, dest_rect, origin, 0.0, WHITE)
    
    # Refuel player when in depot
    G_Player.fuel = G_Player.max_fuel

def draw_page_bar(state_ref, selection_ref):
    rl.ClearBackground(BLACK)
    draw_retro_window("THE RUSTY ROCKET BAR", 200, 100, 800, 600)
    rl.DrawText(b"Bartender: 'Careful out there, miner...'", 250, 200, 20, YELLOW)
    if draw_button("BACK", 500, 600, 200, 40, True): reset_state(state_ref, selection_ref, GameState.DEPOT_HOME)

def draw_page_shipyard(state_ref, selection_ref):
    global ship_thrust_power
    rl.ClearBackground(BLACK)
    draw_retro_window("SHIPYARD", 200, 100, 800, 600)
    rl.DrawText(b"Upgrade your thrusters and hull here.", 250, 200, 20, WHITE)
    sel = selection_ref[0]
    if rl.IsKeyPressed(KEY_DOWN) or rl.IsKeyPressed(KEY_UP): sel = 1 if sel == 0 else 0
    selection_ref[0] = sel
    if draw_button("UPGRADE THRUST (500cr)", 250, 300, 300, 40, sel == 0):
        if G_Player.credits >= 500: G_Player.credits -= 500; ship_thrust_power += 5.0
    if draw_button("BACK", 500, 600, 200, 40, sel == 1): reset_state(state_ref, selection_ref, GameState.DEPOT_HOME)

def draw_page_market(state_ref, selection_ref):
    rl.ClearBackground(BLACK)
    draw_retro_window("COMMODITIES MARKET", 200, 100, 800, 600)
    sel = selection_ref[0]; num = 3
    if rl.IsKeyPressed(KEY_DOWN): sel = (sel + 1) % num
    if rl.IsKeyPressed(KEY_UP): sel = (sel - 1 + num) % num
    selection_ref[0] = sel
    rl.DrawText(f"CREDITS: {G_Player.credits}".encode(), 250, 160, 30, GREEN)
    rl.DrawText(f"IRON ORE: {G_Player.iron}".encode(), 250, 220, 20, WHITE)
    if draw_button("SELL IRON (50cr)", 500, 210, 200, 30, sel == 0):
        if G_Player.iron > 0: G_Player.iron -= 1; G_Player.credits += 50; G_Player.cargo_filled -= 1
    rl.DrawText(f"GOLD ORE: {G_Player.gold}".encode(), 250, 270, 20, WHITE)
    if draw_button("SELL GOLD (100cr)", 500, 260, 200, 30, sel == 1):
        if G_Player.gold > 0: G_Player.gold -= 1; G_Player.credits += 100; G_Player.cargo_filled -= 1
    if draw_button("BACK", 500, 600, 200, 40, sel == 2): reset_state(state_ref, selection_ref, GameState.DEPOT_HOME)

def draw_page_lodgings(state_ref, selection_ref):
    rl.ClearBackground(BLACK)
    draw_retro_window("CREW LODGINGS", 200, 100, 800, 600)
    rl.DrawText(b"Zzz... Rested and Saved.", 350, 300, 20, BLUE)
    if draw_button("BACK", 500, 600, 200, 40, True): reset_state(state_ref, selection_ref, GameState.DEPOT_HOME)

def main():
    # ------------------- FIX FOR CRASH -------------------
    # We MUST keep references to the created Mesh objects in Python space
    # otherwise the GC will free the underlying ctypes buffers, leading to
    # Access Violations when Raylib (C) tries to access them.
    meshes_keep_alive = []

    ship_mesh = create_solid_ship()
    meshes_keep_alive.append(ship_mesh) # Keep alive
    ship_model = rl.LoadModelFromMesh(ship_mesh)
    
    rock_mesh = create_base_rock_mesh()
    meshes_keep_alive.append(rock_mesh) # Keep alive
    rock_model = rl.LoadModelFromMesh(rock_mesh)
    
    generate_rocks()
    init_collision_grid()
    
    chunks = []
    chunk_centers = []
    sp = -PROSPECT_PERIMETER
    for z in range(CHUNKS_AXIS):
        for x in range(CHUNKS_AXIS):
            cx = sp + x * CHUNK_SIZE; cz = sp + z * CHUNK_SIZE
            cm = create_terrain_chunk(cx, cz, float(CHUNK_SIZE))
            meshes_keep_alive.append(cm) # Keep alive
            chunks.append(rl.LoadModelFromMesh(cm))
            chunk_centers.append(Vector2(cx + CHUNK_SIZE/2.0, cz + CHUNK_SIZE/2.0))
    
    ship_pos = Vector3(0, 60, -PROSPECT_PERIMETER)
    ship_vel = Vector3(0, 0, 10)
    ship_pitch = 0.0; ship_roll = 0.0; ship_yaw = 0.0; yaw_dir = 1
    state = [GameState.PROSPECT_MAP]; sel = [0]
    
    while not rl.WindowShouldClose():
        st = state[0]
        if st == GameState.PROSPECT_MAP:
            rl.BeginDrawing()
            draw_page_prospect_map(state, sel, ship_pos, ship_vel)
            rl.EndDrawing()
        elif st == GameState.DRILLING:
            rl.BeginDrawing()
            draw_page_drilling(state, sel)
            rl.EndDrawing()
        elif st == GameState.DEBRIS:
            rl.BeginDrawing()
            draw_page_debris(state, sel)
            rl.EndDrawing()
        elif st == GameState.DEPOT_SELECT:
            rl.BeginDrawing()
            draw_page_depot_select(state, sel)
            rl.EndDrawing()
        elif st == GameState.DEPOT_HOME:
            rl.BeginDrawing()
            draw_page_depot_home(state, sel)
            rl.EndDrawing()
        elif st == GameState.BAR: rl.BeginDrawing(); draw_page_bar(state, sel); rl.EndDrawing()
        elif st == GameState.SHIPYARD: rl.BeginDrawing(); draw_page_shipyard(state, sel); rl.EndDrawing()
        elif st == GameState.MARKET: rl.BeginDrawing(); draw_page_market(state, sel); rl.EndDrawing()
        elif st == GameState.LODGINGS: rl.BeginDrawing(); draw_page_lodgings(state, sel); rl.EndDrawing()
        elif st == GameState.LANDER:
            dt = rl.GetFrameTime()
            md = rl.GetMouseDelta()
            ship_pitch -= md.y * 0.15; ship_roll -= md.x * 0.15
            if abs(md.x) < 0.1: ship_roll = ship_roll * (1.0 - dt)
            ship_pitch = max(-85, min(85, ship_pitch))
            if rl.IsMouseButtonReleased(MOUSE_RIGHT_BUTTON): yaw_dir *= -1
            if rl.IsMouseButtonDown(MOUSE_RIGHT_BUTTON): ship_yaw -= 120.0 * dt * yaw_dir
            
            mr = matrix_rotate_z(DEG2RAD * -ship_roll)
            mp = matrix_rotate_x(DEG2RAD * ship_pitch)
            my = matrix_rotate_y(DEG2RAD * ship_yaw)
            rot = matrix_multiply(matrix_multiply(mp, mr), my)
            
            forward = Vector3(rot.m8, rot.m9, rot.m10)
            up = Vector3(rot.m4, rot.m5, rot.m6)
            
            ship_vel.y += ship_gravity * dt
            if (rl.IsMouseButtonDown(MOUSE_LEFT_BUTTON) or rl.IsKeyDown(KEY_SPACE) or rl.IsKeyDown(KEY_W)) and G_Player.fuel > 0:
                thrust = vec3_scale(up, ship_thrust_power * dt)
                ship_vel = vec3_add(ship_vel, thrust)
                nozzle = vec3_add(ship_pos, vec3_scale(up, -0.4))
                spawn_thrust_particles(nozzle, up)
                G_Player.fuel -= ship_fuel_burn_rate * dt
                if G_Player.fuel < 0: G_Player.fuel = 0
            
            ship_vel = vec3_scale(ship_vel, ship_drag_factor)
            next_pos = vec3_add(ship_pos, vec3_scale(ship_vel, dt))
            wh = get_world_height(next_pos.x, next_pos.z)
            if next_pos.y < wh + 0.5:
                next_pos.y = wh + 0.5
                if vec3_length(ship_vel) < 5.0: state[0] = GameState.DRILLING
                else: ship_vel = vec3_scale(ship_vel, 0.5); ship_vel.y = 0
            if next_pos.y > 80: state[0] = GameState.DEPOT_SELECT
            if next_pos.x > PROSPECT_PERIMETER: next_pos.x = PROSPECT_PERIMETER; ship_vel.x = 0
            if next_pos.x < -PROSPECT_PERIMETER: next_pos.x = -PROSPECT_PERIMETER; ship_vel.x = 0
            if next_pos.z > PROSPECT_PERIMETER: next_pos.z = PROSPECT_PERIMETER; ship_vel.z = 0
            if next_pos.z < -PROSPECT_PERIMETER: next_pos.z = -PROSPECT_PERIMETER; ship_vel.z = 0
            ship_pos = next_pos
            
            cam_t = vec3_add(ship_pos, vec3_scale(forward, -9.0)); cam_t.y += 4.0
            camera.position.x += (cam_t.x - camera.position.x) * 5 * dt
            camera.position.y += (cam_t.y - camera.position.y) * 5 * dt
            camera.position.z += (cam_t.z - camera.position.z) * 5 * dt
            if camera.position.y < 0.5: camera.position.y = 0.5
            camera.target = ship_pos
            
            update_particles(dt)
            
            rl.BeginDrawing()
            rl.ClearBackground(Color(5,5,10,255))
            rl.BeginMode3D(camera)
            cull = RENDER_DISTANCE + CHUNK_SIZE
            for i in range(TOTAL_CHUNKS):
                if abs(ship_pos.x - chunk_centers[i].x) < cull and abs(ship_pos.z - chunk_centers[i].y) < cull:
                    rl.DrawModel(chunks[i], Vector3(0,0,0), 1.0, WHITE)
            draw_perimeter_border(ship_pos)
            draw_projected_shadow(ship_pos)
            ship_model.transform = rot
            rl.DrawModel(ship_model, ship_pos, 1.0, WHITE)
            rl.rlDisableBackfaceCulling()
            for r in range(NUM_ROCKS):
                if abs(G_Rocks[r].position.x - ship_pos.x) < RENDER_DISTANCE and abs(G_Rocks[r].position.z - ship_pos.z) < RENDER_DISTANCE:
                    rl.DrawModelEx(rock_model, G_Rocks[r].position, G_Rocks[r].axis, G_Rocks[r].angle, Vector3(G_Rocks[r].scale, G_Rocks[r].scale, G_Rocks[r].scale), G_Rocks[r].color)
            rl.rlEnableBackfaceCulling()
            draw_particles()
            rl.EndMode3D()
            
            rl.DrawFPS(10, 10)
            rl.DrawText(b"LAND TO DRILL - FLY UP TO ORBIT", 10, 40, 20, LIGHTGRAY)
            bars = int(G_Player.fuel)
            rl.DrawText(b"FUEL", 10, 760, 20, WHITE)
            for i in range(10):
                c = GREEN if i < bars else DARKGRAY
                if i < 3 and i < bars: c = RED
                rl.DrawRectangle(70 + i*25, 760, 20, 20, c)
            rl.EndDrawing()

    # Do NOT manually unload Python-managed ctypes meshes to avoid double-free
    # OS will reclaim memory on exit
    rl.CloseWindow()

if __name__ == "__main__":
    main()