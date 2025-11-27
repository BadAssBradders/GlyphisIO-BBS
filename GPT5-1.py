import pygame
import math
import sys

pygame.init()

# ---------------------------------------------------------------------
# Window / basic setup
# ---------------------------------------------------------------------
WIDTH, HEIGHT = 872, 654
SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("2.5D Arrowhead Lander")

CLOCK = pygame.time.Clock()

# ---------------------------------------------------------------------
# Simple 3D math helpers
# ---------------------------------------------------------------------
def vec_sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])

def vec_cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )

def vec_dot(a, b):
    return a[0]*b[0] + a[1]*b[1] + a[2]*b[2]

def vec_len(v):
    return math.sqrt(v[0]*v[0] + v[1]*v[1] + v[2]*v[2])

def vec_norm(v):
    l = vec_len(v)
    if l == 0:
        return (0, 0, 0)
    return (v[0]/l, v[1]/l, v[2]/l)

# ---------------------------------------------------------------------
# Camera & projection
# ---------------------------------------------------------------------
CAMERA_POS = (0, 40, -400)   # Slightly above and behind
FOV = 350.0
SCREEN_CX, SCREEN_CY = WIDTH // 2, HEIGHT // 2

def project_point(p):
    # Simple perspective projection
    x, y, z = p
    cx, cy, cz = CAMERA_POS
    x -= cx
    y -= cy
    z -= cz
    if z <= 1:
        z = 1
    scale = FOV / z
    sx = SCREEN_CX + int(x * scale)
    sy = SCREEN_CY - int(y * scale)
    return (sx, sy)

# ---------------------------------------------------------------------
# Ship geometry (low-poly wedge / arrowhead)
# All triangles, flat shaded, no smoothing.
# ---------------------------------------------------------------------
# Dimensions
L = 220  # length
W = 120  # width
H = 50   # height

# Base vertices for a single-hull wedge with a dorsal spine.
# Coordinates: (x: left-right, y: up-down, z: front-back)
BASE_VERTS = [
    # Nose apex (top)
    (0,      H/2,   -L/2),       # 0

    # Nose edges (slightly back, underside)
    (-W/2,  -H/2,   -L/4),       # 1
    ( W/2,  -H/2,   -L/4),       # 2

    # Dorsal spine midpoints
    (0,      H/2,    0),         # 3
    (0,      H/2,    L/4),       # 4

    # Wing edges (sloped down from spine)
    (-W/2,   0,      0),         # 5
    ( W/2,   0,      0),         # 6
    (-W/2,   0,      L/4),       # 7
    ( W/2,   0,      L/4),       # 8

    # Back bottom corners (massive trapezoid engine housing)
    (-W/2,  -H/2,    L/2),       # 9
    ( W/2,  -H/2,    L/2),       #10

    # Back top centre (for dorsal to engine housing)
    (0,      H/2,    L/2),       #11

    # Back bottom centre (for engine face)
    (0,     -H/2,    L/2),       #12
]

# Texture "atlas": solid flat colours
GREY_1 = (90,  96, 110)
GREY_2 = (70,  76, 90)
BLUE_1 = (40,  60, 110)
BLUE_2 = (30,  40, 70)
ENGINE_BASE = (80, 180, 255)   # will be brightened emissive
COCKPIT_COLOR = (10, 15, 25)   # dark canopy

# Faces defined as (vertex_indices, base_color, "tag")
# tag can be "engine" for emissive, "hull" otherwise.
FACES = [
    # Nose wedge top
    ([0, 5, 3], GREY_1, "hull"),
    ([0, 3, 6], GREY_1, "hull"),

    # Mid top spine to back
    ([3, 7, 4], GREY_2, "hull"),
    ([3, 4, 8], GREY_2, "hull"),
    ([4, 7,11], GREY_1, "hull"),
    ([4,11, 8], GREY_1, "hull"),

    # Left side upper
    ([0, 1, 5], BLUE_1, "hull"),
    ([1, 7, 5], BLUE_1, "hull"),
    ([1, 9, 7], BLUE_2, "hull"),
    ([7, 9,11], BLUE_2, "hull"),

    # Right side upper
    ([0, 6, 2], BLUE_1, "hull"),
    ([6, 8, 2], BLUE_1, "hull"),
    ([2, 8,10], BLUE_2, "hull"),
    ([8,11,10], BLUE_2, "hull"),

    # Underside
    ([1, 2,12], GREY_2, "hull"),
    ([1,12, 9], GREY_2, "hull"),
    ([2,10,12], GREY_2, "hull"),
    ([9,12,10], GREY_2, "hull"),

    # Engine rear vertical face (bright emissive)
    ([11, 9,12], ENGINE_BASE, "engine"),
    ([11,12,10], ENGINE_BASE, "engine"),
]

# Cockpit canopy quad near the nose apex, flush with top spine
# Defined as 3D points; rendered as overlay polygon (two tris).
COCKPIT_VERTS = [
    (-W*0.12, H/2 + 0.1, -L*0.35),  # left-back
    ( W*0.12, H/2 + 0.1, -L*0.35),  # right-back
    ( W*0.08, H/2 + 0.1, -L*0.45),  # right-front
    (-W*0.08, H/2 + 0.1, -L*0.45),  # left-front
]

# ---------------------------------------------------------------------
# Lighting: soft spotlight from above
# ---------------------------------------------------------------------
LIGHT_DIR = vec_norm((0, -1, -0.5))  # from above, slightly toward the ship
AMBIENT = 0.25

def shade_face(face_verts, base_color, tag, thrust_amount):
    # Compute face normal (for flat shading)
    v0, v1, v2 = face_verts
    e1 = vec_sub(v1, v0)
    e2 = vec_sub(v2, v0)
    normal = vec_norm(vec_cross(e1, e2))

    # Light intensity from above
    # Use negative light dir because we want facing light
    intensity = vec_dot(normal, (-LIGHT_DIR[0], -LIGHT_DIR[1], -LIGHT_DIR[2]))
    if intensity < 0:
        intensity = 0
    intensity = AMBIENT + (1 - AMBIENT) * intensity

    r, g, b = base_color

    # Boost engine emissive based on thrust
    if tag == "engine":
        glow = min(1.0, thrust_amount * 3.0)
        intensity = 0.6 + 0.4 * glow
        r = 120 + int(135 * glow)
        g = 200 + int(55 * glow)
        b = 255

    r = max(0, min(255, int(r * intensity)))
    g = max(0, min(255, int(g * intensity)))
    b = max(0, min(255, int(b * intensity)))
    return (r, g, b)

# ---------------------------------------------------------------------
# Physics: lunar-style gravity, thrust from underside on LMB
# ---------------------------------------------------------------------
gravity = -0.12   # negative = downward in world Y
thrust_power = 0.28
max_thrust_factor = 1.5

ship_height = 0.0   # distance above ground (0 = on ground)
ship_velocity = 0.0
ground_y = -H/2     # so the bottom of the ship touches the ground at height=0

# For thrust charging feel / for engine glow
thrust_accumulator = 0.0

# ---------------------------------------------------------------------
# Ground & environment drawing
# ---------------------------------------------------------------------
def draw_ground():
    # Simple 2.5D ground plane: big trapezoid to fake perspective
    horizon_y = int(HEIGHT * 0.55)
    bottom_y = HEIGHT
    half_w = WIDTH // 2

    ground_color_far = (12,  15,  18)
    ground_color_near = (18,  24,  32)
    bg_color = (5, 7, 10)

    SCREEN.fill(bg_color)

    # Big trapezoid ground
    poly = [
        (0, bottom_y),
        (WIDTH, bottom_y),
        (int(WIDTH * 0.8), horizon_y),
        (int(WIDTH * 0.2), horizon_y),
    ]
    pygame.draw.polygon(SCREEN, ground_color_near, poly)

    # Simple spotlight circle falloff on ground (soft)
    spot_center = (SCREEN_CX, int(HEIGHT * 0.45))
    spot_radius = int(HEIGHT * 0.4)
    for r in range(spot_radius, 0, -8):
        alpha = (spot_radius - r) / spot_radius
        c = int(40 + 30 * alpha)
        color = (c, c, c)
        pygame.draw.circle(SCREEN, color, spot_center, r, 1)

    # Optional: faint ground grid for depth
    grid_color = (25, 30, 38)
    for i in range(8):
        t = i / 8.0
        y = horizon_y + int(t * (bottom_y - horizon_y))
        pygame.draw.line(SCREEN, grid_color, (0, y), (WIDTH, y))

# ---------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------
running = True
while running:
    dt = CLOCK.tick(60) / 1000.0  # seconds per frame

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    mouse_buttons = pygame.mouse.get_pressed()
    left_down = mouse_buttons[0]

    # Physics: lunar gravity + thrust while LMB held
    if left_down:
        # Build thrust and engine glow over time
        thrust_accumulator = min(max_thrust_factor, thrust_accumulator + dt)
        ship_velocity += thrust_power * dt * thrust_accumulator
    else:
        # Leak thrust accumulator down when not firing
        thrust_accumulator = max(0.0, thrust_accumulator - dt * 1.5)

    # Apply gravity
    ship_velocity += gravity * dt
    ship_height += ship_velocity

    # Ground collision
    if ship_height <= 0:
        ship_height = 0
        if ship_velocity < 0:
            ship_velocity = 0

    # -----------------------------------------------------------------
    # Rendering
    # -----------------------------------------------------------------
    draw_ground()

    # Prepare transformed vertices: add world offset (height)
    world_verts = []
    height_offset = ground_y + ship_height
    for x, y, z in BASE_VERTS:
        world_verts.append((x, y + height_offset, z))

    # Same for cockpit patch
    world_cockpit = []
    for x, y, z in COCKPIT_VERTS:
        world_cockpit.append((x, y + height_offset, z))

    # Build face list with projected polygons and depth for painter's sort
    face_draw_list = []
    for indices, base_color, tag in FACES:
        verts3d = [world_verts[i] for i in indices]
        # Compute average z for depth sorting
        avg_z = sum(v[2] for v in verts3d) / len(verts3d)
        color = shade_face(verts3d, base_color, tag, thrust_accumulator)

        # Project to screen
        poly2d = [project_point(v) for v in verts3d]
        face_draw_list.append((avg_z, poly2d, color))

    # Sort back-to-front (largest z first)
    face_draw_list.sort(key=lambda item: item[0], reverse=True)

    # Draw hull and engine
    for _, poly2d, color in face_draw_list:
        pygame.draw.polygon(SCREEN, color, poly2d)

    # Draw dark cockpit canopy as a single quad (two tris)
    cockpit2d = [project_point(v) for v in world_cockpit]
    pygame.draw.polygon(SCREEN, COCKPIT_COLOR, cockpit2d)

    # Simple UI text
    font = pygame.font.SysFont("consolas", 16)
    txt = font.render("LMB: Thrust  |  Gravity: lunar  |  Height: {:.1f}".format(ship_height), True, (200, 200, 220))
    SCREEN.blit(txt, (10, 10))

    pygame.display.flip()

pygame.quit()
sys.exit()
