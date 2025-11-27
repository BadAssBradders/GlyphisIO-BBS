import pygame
import math
import random

# Initialize Pygame
pygame.init()
WIDTH, HEIGHT = 1024, 768
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Vector Space Command - Elite Style")
clock = pygame.time.Clock()

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
CYAN = (0, 255, 255)
RED = (255, 50, 50)
BLUE = (100, 150, 255)
GREEN = (0, 255, 0)
YELLOW = (255, 255, 0)
DARK_GREY = (30, 30, 30)
ORANGE = (255, 165, 0)
HUD_COLOR = (0, 200, 100)

# View modes
VIEW_NORMAL = 0
VIEW_REAR = 1
VIEW_SIDE = 2
VIEW_MAP = 3
VIEW_SURFACE = 4
current_view = VIEW_NORMAL

# Simple 3D ship vertices (a classic Elite-style cobra-ish ship)
ship_vertices = [
    [0, 0, 2],      # 0 nose
    [-1, -0.5, -1], # 1 left wing back
    [1, -0.5, -1],  # 2 right wing back
    [-0.3, 0.3, -1], # 3 left top back
    [0.3, 0.3, -1],  # 4 right top back
    [0, -0.3, -1],   # 5 bottom back center
]

# Faces (vertex indices and color)
ship_faces = [
    ([0, 2, 5], BLUE),      # Right bottom
    ([0, 5, 1], DARK_GREY), # Left bottom
    ([0, 2, 4], CYAN),      # Right top
    ([0, 4, 3], DARK_GREY), # Left top
    ([1, 2, 5], RED),       # Back bottom
    ([1, 3, 4, 2], RED),    # Back face
]

# Create multiple ships for the scene
class Ship:
    def __init__(self, x, y, z, color_offset=0):
        self.x = x
        self.y = y
        self.z = z
        self.angle_x = random.uniform(0, math.pi * 2)
        self.angle_y = random.uniform(0, math.pi * 2)
        self.angle_z = random.uniform(0, math.pi * 2)
        self.color_offset = color_offset
        
    def get_faces(self):
        faces = []
        for verts, color in ship_faces:
            # Vary color slightly
            new_color = tuple(max(0, min(255, c + self.color_offset)) for c in color)
            faces.append((verts, new_color))
        return faces

# Create a small fleet
other_ships = [
    Ship(5, 2, 10, -30),
    Ship(-4, -3, 15, 20),
    Ship(0, 5, 8, -50),
    Ship(-6, 0, 20, 40),
]

# Stars for background
stars = []
for _ in range(150):
    stars.append([
        random.randint(0, WIDTH),
        random.randint(0, HEIGHT),
        random.uniform(0.5, 2.5)
    ])

# Terrain generation for Lander-style surface
class Terrain:
    def __init__(self, width=200, resolution=2):
        self.width = width
        self.resolution = resolution
        self.points = width // resolution
        self.heights = self.generate_terrain()
        self.craters = self.generate_craters()
        self.rocks = self.generate_rocks()
        
    def generate_terrain(self):
        """Generate base terrain using simple noise"""
        heights = []
        for i in range(self.points):
            # Base rolling hills
            base = math.sin(i * 0.1) * 2 + math.sin(i * 0.05) * 4
            # Add roughness
            roughness = random.uniform(-0.5, 0.5)
            heights.append(base + roughness)
        return heights
    
    def generate_craters(self):
        """Generate crater positions and sizes"""
        craters = []
        for _ in range(15):
            x = random.randint(10, self.points - 10)
            radius = random.uniform(3, 12)
            depth = random.uniform(1.5, 4)
            craters.append({'x': x, 'radius': radius, 'depth': depth})
        
        # Apply craters to terrain
        for crater in craters:
            cx = crater['x']
            radius = crater['radius']
            depth = crater['depth']
            
            for i in range(max(0, int(cx - radius)), min(self.points, int(cx + radius))):
                dist = abs(i - cx)
                if dist < radius:
                    # Crater profile (bowl shape)
                    factor = 1 - (dist / radius)
                    self.heights[i] -= depth * factor * factor
        
        return craters
    
    def generate_rocks(self):
        """Generate surface rocks/boulders"""
        rocks = []
        for _ in range(40):
            x = random.randint(0, self.points - 1)
            height = self.heights[x]
            size = random.uniform(0.3, 1.5)
            rock_type = random.choice(['pyramid', 'block', 'wedge'])
            rocks.append({
                'x': x,
                'y': height,
                'size': size,
                'type': rock_type,
                'rotation': random.uniform(0, math.pi)
            })
        return rocks
    
    def get_height_at(self, x):
        """Get terrain height at position x"""
        idx = int(x / self.resolution) % self.points
        return self.heights[idx]

terrain = Terrain()

# Viewport areas
MAIN_VIEW_RECT = pygame.Rect(10, 60, 640, 480)
RADAR_RECT = pygame.Rect(670, 60, 330, 230)
MAP_RECT = pygame.Rect(670, 310, 330, 230)
STATUS_RECT = pygame.Rect(670, 560, 330, 180)

def rotate_3d(vertices, angle_x, angle_y, angle_z):
    """Rotate vertices around x, y, z axes"""
    rotated = []
    
    cos_x, sin_x = math.cos(angle_x), math.sin(angle_x)
    cos_y, sin_y = math.cos(angle_y), math.sin(angle_y)
    cos_z, sin_z = math.cos(angle_z), math.sin(angle_z)
    
    for v in vertices:
        x, y, z = v
        
        # Rotate around X
        y, z = y * cos_x - z * sin_x, y * sin_x + z * cos_x
        
        # Rotate around Y
        x, z = x * cos_y + z * sin_y, -x * sin_y + z * cos_y
        
        # Rotate around Z
        x, y = x * cos_z - y * sin_z, x * sin_z + y * cos_z
        
        rotated.append([x, y, z])
    
    return rotated

def apply_camera_transform(vertices, camera_angle_x, camera_angle_y, camera_angle_z):
    """Transform vertices based on camera rotation"""
    return rotate_3d(vertices, -camera_angle_x, -camera_angle_y, -camera_angle_z)

def project_3d_to_2d(vertex, viewport, fov=256, viewer_distance=4):
    """Project 3D point to 2D screen coordinates within viewport"""
    x, y, z = vertex
    
    # Perspective projection
    factor = fov / (viewer_distance + z)
    x_proj = x * factor + viewport.centerx
    y_proj = -y * factor + viewport.centery
    
    return int(x_proj), int(y_proj), z

def draw_ship(surface, vertices, faces, viewport, ship_offset=(0, 0, 0)):
    """Draw the ship with filled polygons and wireframe edges"""
    
    # Offset vertices
    offset_vertices = [[v[0] + ship_offset[0], v[1] + ship_offset[1], v[2] + ship_offset[2]] 
                       for v in vertices]
    
    # Calculate face depths for sorting (painter's algorithm)
    faces_with_depth = []
    for face_verts, color in faces:
        # Calculate average Z for face
        avg_z = sum(offset_vertices[i][2] for i in face_verts) / len(face_verts)
        faces_with_depth.append((face_verts, color, avg_z))
    
    # Sort by depth (furthest first)
    faces_with_depth.sort(key=lambda f: f[2])
    
    # Draw faces
    for face_verts, color, _ in faces_with_depth:
        points_2d = []
        all_in_front = True
        for vert_idx in face_verts:
            x, y, z = project_3d_to_2d(offset_vertices[vert_idx], viewport)
            if z < -3:  # Behind camera
                all_in_front = False
                break
            points_2d.append((x, y))
        
        if all_in_front and len(points_2d) >= 3:
            # Clip to viewport
            if all(viewport.collidepoint(p) or 
                   (abs(p[0] - viewport.centerx) < viewport.width and 
                    abs(p[1] - viewport.centery) < viewport.height) 
                   for p in points_2d):
                # Draw filled polygon
                pygame.draw.polygon(surface, color, points_2d)
                # Draw wireframe edge
                pygame.draw.polygon(surface, WHITE, points_2d, 1)

def draw_hud_frame(surface):
    """Draw the main HUD frame and panels"""
    # Main view frame
    pygame.draw.rect(surface, HUD_COLOR, MAIN_VIEW_RECT, 2)
    pygame.draw.line(surface, HUD_COLOR, 
                     (MAIN_VIEW_RECT.left, MAIN_VIEW_RECT.top + 20),
                     (MAIN_VIEW_RECT.right, MAIN_VIEW_RECT.top + 20), 1)
    
    # Radar frame
    pygame.draw.rect(surface, HUD_COLOR, RADAR_RECT, 2)
    
    # Map frame
    pygame.draw.rect(surface, HUD_COLOR, MAP_RECT, 2)
    
    # Status frame
    pygame.draw.rect(surface, HUD_COLOR, STATUS_RECT, 2)
    
    # Corner brackets on main view
    bracket_size = 15
    for corner in [(MAIN_VIEW_RECT.left, MAIN_VIEW_RECT.top),
                   (MAIN_VIEW_RECT.right, MAIN_VIEW_RECT.top),
                   (MAIN_VIEW_RECT.left, MAIN_VIEW_RECT.bottom),
                   (MAIN_VIEW_RECT.right, MAIN_VIEW_RECT.bottom)]:
        x, y = corner
        dx = bracket_size if x == MAIN_VIEW_RECT.left else -bracket_size
        dy = bracket_size if y == MAIN_VIEW_RECT.top else -bracket_size
        pygame.draw.line(surface, CYAN, (x, y), (x + dx, y), 2)
        pygame.draw.line(surface, CYAN, (x, y), (x, y + dy), 2)

def draw_radar(surface, player_ship, other_ships, viewport):
    """Draw radar/scanner display"""
    center_x = viewport.centerx
    center_y = viewport.centery
    radius = min(viewport.width, viewport.height) // 2 - 10
    
    # Draw radar circles
    for r in [radius // 3, radius * 2 // 3, radius]:
        pygame.draw.circle(surface, (0, 100, 50), (center_x, center_y), r, 1)
    
    # Draw crosshair
    pygame.draw.line(surface, HUD_COLOR, (center_x - 10, center_y), (center_x + 10, center_y), 1)
    pygame.draw.line(surface, HUD_COLOR, (center_x, center_y - 10), (center_x, center_y + 10), 1)
    
    # Draw other ships on radar
    for ship in other_ships:
        # Calculate relative position
        dx = ship.x
        dy = ship.z
        distance = math.sqrt(dx**2 + dy**2)
        
        if distance > 0:
            # Scale to radar
            scale = radius / 25  # Radar range
            radar_x = int(center_x + dx * scale)
            radar_y = int(center_y + dy * scale)
            
            # Check if in radar range
            if math.sqrt((radar_x - center_x)**2 + (radar_y - center_y)**2) < radius:
                # Size based on distance
                size = max(2, int(5 - distance / 10))
                color = YELLOW if distance < 10 else RED
                pygame.draw.circle(surface, color, (radar_x, radar_y), size)
                pygame.draw.circle(surface, WHITE, (radar_x, radar_y), size, 1)
    
    # Labels
    font = pygame.font.Font(None, 18)
    text = font.render("SCANNER", True, HUD_COLOR)
    surface.blit(text, (viewport.left + 5, viewport.top + 5))

def draw_map(surface, player_ship, other_ships, viewport):
    """Draw tactical map view"""
    center_x = viewport.centerx
    center_y = viewport.centery
    scale = 8
    
    # Grid
    for i in range(-30, 31, 10):
        # Vertical lines
        x = center_x + i * scale
        if viewport.left < x < viewport.right:
            pygame.draw.line(surface, (0, 50, 30), (x, viewport.top), (x, viewport.bottom), 1)
        # Horizontal lines
        y = center_y + i * scale
        if viewport.top < y < viewport.bottom:
            pygame.draw.line(surface, (0, 50, 30), (viewport.left, y), (viewport.right, y), 1)
    
    # Axes
    pygame.draw.line(surface, HUD_COLOR, (center_x, viewport.top), (center_x, viewport.bottom), 1)
    pygame.draw.line(surface, HUD_COLOR, (viewport.left, center_y), (viewport.right, center_y), 1)
    
    # Player ship (center, with heading indicator)
    pygame.draw.circle(surface, GREEN, (center_x, center_y), 5)
    pygame.draw.circle(surface, WHITE, (center_x, center_y), 5, 1)
    
    # Draw heading line (based on player rotation)
    heading_length = 15
    pygame.draw.line(surface, GREEN, 
                     (center_x, center_y),
                     (center_x, center_y - heading_length), 2)
    
    # Other ships
    for ship in other_ships:
        map_x = int(center_x + ship.x * scale)
        map_y = int(center_y + ship.z * scale)
        
        if viewport.collidepoint(map_x, map_y):
            pygame.draw.circle(surface, RED, (map_x, map_y), 3)
            pygame.draw.circle(surface, WHITE, (map_x, map_y), 3, 1)
    
    # Labels
    font = pygame.font.Font(None, 18)
    text = font.render("TACTICAL MAP", True, HUD_COLOR)
    surface.blit(text, (viewport.left + 5, viewport.top + 5))

def draw_status(surface, viewport, view_mode, angle_x, angle_y):
    """Draw status information"""
    font = pygame.font.Font(None, 20)
    small_font = pygame.font.Font(None, 18)
    
    y_offset = viewport.top + 10
    line_height = 22
    
    # View mode
    view_names = ["FORWARD VIEW", "REAR VIEW", "SIDE VIEW", "MAP VIEW", "SURFACE VIEW"]
    text = font.render(view_names[view_mode] if view_mode < len(view_names) else "UNKNOWN", True, CYAN)
    surface.blit(text, (viewport.left + 10, y_offset))
    y_offset += line_height + 5
    
    # Ship status
    status_items = [
        ("SHIELDS:", "100%", GREEN),
        ("ENERGY:", "87%", YELLOW),
        ("FUEL:", "2.4T", GREEN),
        ("SPEED:", "0.00", WHITE),
        ("ALT:", "0M", WHITE),
    ]
    
    for label, value, color in status_items:
        label_text = small_font.render(label, True, HUD_COLOR)
        value_text = small_font.render(value, True, color)
        surface.blit(label_text, (viewport.left + 10, y_offset))
        surface.blit(value_text, (viewport.left + 150, y_offset))
        y_offset += line_height
    
    # Attitude
    y_offset += 10
    pitch_deg = int(math.degrees(angle_x) % 360)
    yaw_deg = int(math.degrees(angle_y) % 360)
    
    att_text = small_font.render(f"PITCH: {pitch_deg:03d}°", True, WHITE)
    surface.blit(att_text, (viewport.left + 10, y_offset))
    y_offset += line_height
    
    att_text = small_font.render(f"YAW:   {yaw_deg:03d}°", True, WHITE)
    surface.blit(att_text, (viewport.left + 10, y_offset))

def draw_terrain_surface(surface, terrain, viewport, camera_x, altitude):
    """Draw Lander-style close-up surface view"""
    # This draws the surface from a side view, like classic Lander
    
    ground_y = viewport.bottom - 100  # Ground level on screen
    scale_x = 8  # Horizontal scale
    scale_y = 15  # Vertical scale
    
    # Draw terrain line by line
    points = []
    for i in range(terrain.points):
        world_x = i * terrain.resolution
        screen_x = viewport.centerx + (world_x - camera_x) * scale_x
        
        if viewport.left - 50 < screen_x < viewport.right + 50:
            height = terrain.heights[i]
            screen_y = ground_y - height * scale_y
            points.append((int(screen_x), int(screen_y)))
    
    # Draw terrain as filled polygon (ground)
    if len(points) > 2:
        # Create bottom points for filled area
        filled_points = points + [
            (viewport.right + 50, viewport.bottom),
            (viewport.left - 50, viewport.bottom)
        ]
        pygame.draw.polygon(surface, (40, 40, 40), filled_points)
        
        # Draw terrain outline
        pygame.draw.lines(surface, (180, 180, 180), False, points, 2)
        
        # Draw detail lines on terrain
        for i in range(0, len(points) - 1, 3):
            if i + 1 < len(points):
                pygame.draw.line(surface, (100, 100, 100), points[i], points[i + 1], 1)
    
    # Draw rocks
    for rock in terrain.rocks:
        rock_world_x = rock['x'] * terrain.resolution
        rock_screen_x = viewport.centerx + (rock_world_x - camera_x) * scale_x
        
        if viewport.left - 20 < rock_screen_x < viewport.right + 20:
            rock_ground_y = ground_y - rock['y'] * scale_y
            size = rock['size'] * scale_y
            
            if rock['type'] == 'pyramid':
                # Triangle rock
                rock_points = [
                    (rock_screen_x, rock_ground_y - size * 1.5),
                    (rock_screen_x - size, rock_ground_y),
                    (rock_screen_x + size, rock_ground_y)
                ]
                pygame.draw.polygon(surface, (90, 90, 90), rock_points)
                pygame.draw.polygon(surface, (150, 150, 150), rock_points, 1)
            elif rock['type'] == 'block':
                # Rectangular rock
                rock_rect = pygame.Rect(rock_screen_x - size/2, rock_ground_y - size, size, size)
                pygame.draw.rect(surface, (80, 80, 80), rock_rect)
                pygame.draw.rect(surface, (140, 140, 140), rock_rect, 1)
            else:  # wedge
                # Angled rock
                rock_points = [
                    (rock_screen_x - size, rock_ground_y),
                    (rock_screen_x + size/2, rock_ground_y),
                    (rock_screen_x + size/2, rock_ground_y - size)
                ]
                pygame.draw.polygon(surface, (85, 85, 85), rock_points)
                pygame.draw.polygon(surface, (145, 145, 145), rock_points, 1)
    
    # Draw craters (additional detail)
    for crater in terrain.craters:
        crater_world_x = crater['x'] * terrain.resolution
        crater_screen_x = viewport.centerx + (crater_world_x - camera_x) * scale_x
        
        if viewport.left - 50 < crater_screen_x < viewport.right + 50:
            crater_y = ground_y - terrain.heights[crater['x']] * scale_y
            radius = crater['radius'] * scale_x
            
            # Draw crater rim as arc
            if viewport.left < crater_screen_x < viewport.right:
                pygame.draw.circle(surface, (100, 100, 100), 
                                 (int(crater_screen_x), int(crater_y)), 
                                 int(radius), 1)
    
    # Draw ship (simplified for surface view)
    ship_screen_x = viewport.centerx
    ship_screen_y = ground_y - altitude * scale_y
    
    # Ship body (simple triangle pointing up)
    ship_size = 8
    ship_points = [
        (ship_screen_x, ship_screen_y - ship_size),
        (ship_screen_x - ship_size/2, ship_screen_y + ship_size/2),
        (ship_screen_x + ship_size/2, ship_screen_y + ship_size/2)
    ]
    pygame.draw.polygon(surface, CYAN, ship_points)
    pygame.draw.polygon(surface, WHITE, ship_points, 2)
    
    # Thruster flame (if low altitude)
    if altitude < 20:
        flame_height = random.randint(3, 8)
        pygame.draw.line(surface, ORANGE, 
                        (ship_screen_x, ship_screen_y + ship_size/2),
                        (ship_screen_x, ship_screen_y + ship_size/2 + flame_height), 2)
        pygame.draw.line(surface, YELLOW,
                        (ship_screen_x, ship_screen_y + ship_size/2),
                        (ship_screen_x, ship_screen_y + ship_size/2 + flame_height - 2), 1)
    
    # Altitude indicator line
    if altitude < 50:
        pygame.draw.line(surface, (100, 200, 100), 
                        (ship_screen_x, ship_screen_y),
                        (ship_screen_x, ground_y), 1)
    
    # Draw altitude text
    font = pygame.font.Font(None, 20)
    alt_text = font.render(f"ALTITUDE: {altitude:.1f}M", True, YELLOW)
    surface.blit(alt_text, (viewport.left + 10, viewport.bottom - 30))

# Main loop
running = True
angle_x, angle_y, angle_z = 0, 0, 0
rotation_speed = 0.01

# Lander/surface mode variables
camera_x = 50  # Position along terrain
altitude = 25  # Height above surface
velocity_x = 0
velocity_y = 0

# Camera angles for different views
camera_angles = {
    VIEW_NORMAL: (0, 0, 0),
    VIEW_REAR: (0, math.pi, 0),
    VIEW_SIDE: (0, math.pi / 2, 0),
}

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            elif event.key == pygame.K_1:
                current_view = VIEW_NORMAL
            elif event.key == pygame.K_2:
                current_view = VIEW_REAR
            elif event.key == pygame.K_3:
                current_view = VIEW_SIDE
            elif event.key == pygame.K_4:
                current_view = VIEW_MAP
            elif event.key == pygame.K_5:
                current_view = VIEW_SURFACE
            elif event.key == pygame.K_SPACE:
                # Cycle views
                current_view = (current_view + 1) % 5
    
    # Handle rotation controls (for space views)
    keys = pygame.key.get_pressed()
    
    if current_view == VIEW_SURFACE:
        # Lander-style controls
        if keys[pygame.K_LEFT]:
            velocity_x -= 0.02
        if keys[pygame.K_RIGHT]:
            velocity_x += 0.02
        if keys[pygame.K_UP]:
            velocity_y += 0.05  # Thrust up
        if keys[pygame.K_DOWN]:
            velocity_y -= 0.02
        
        # Apply physics
        velocity_y -= 0.02  # Gravity
        velocity_x *= 0.98  # Friction
        velocity_y *= 0.98
        
        # Update position
        camera_x += velocity_x
        altitude += velocity_y
        
        # Wrap camera
        if camera_x < 0:
            camera_x += terrain.width
        if camera_x > terrain.width:
            camera_x -= terrain.width
        
        # Get terrain height at current position
        terrain_height = terrain.get_height_at(camera_x)
        
        # Collision with ground
        if altitude < terrain_height + 2:
            altitude = terrain_height + 2
            velocity_y = max(0, velocity_y)
            velocity_x *= 0.9
        
        # Clamp altitude
        altitude = max(terrain_height + 2, min(altitude, 100))
        
    else:
        # Standard rotation controls for space views
        keys_pressed = False
        if keys[pygame.K_LEFT]:
            angle_y -= 0.05
            keys_pressed = True
        if keys[pygame.K_RIGHT]:
            angle_y += 0.05
            keys_pressed = True
        if keys[pygame.K_UP]:
            angle_x -= 0.05
            keys_pressed = True
        if keys[pygame.K_DOWN]:
            angle_x += 0.05
            keys_pressed = True
        if keys[pygame.K_q]:
            angle_z -= 0.05
            keys_pressed = True
        if keys[pygame.K_e]:
            angle_z += 0.05
            keys_pressed = True
        
        # Auto-rotation if no input (just for demo)
        if not keys_pressed:
            angle_y += rotation_speed
            angle_x += rotation_speed * 0.3
    
    # Update other ships (slow rotation)
    for ship in other_ships:
        ship.angle_y += 0.005
        ship.angle_x += 0.002
    
    # Clear screen
    screen.fill(BLACK)
    
    # Draw HUD frame
    draw_hud_frame(screen)
    
    # Title bar
    font = pygame.font.Font(None, 28)
    title = font.render("VECTOR SPACE COMMAND", True, HUD_COLOR)
    screen.blit(title, (20, 20))
    
    # Instructions (top right)
    small_font = pygame.font.Font(None, 18)
    if current_view == VIEW_SURFACE:
        instructions = [
            "SPACE: Cycle Views | 1-5: Select View",
            "← →: Thrust | ↑: Main Engine | ESC: Exit"
        ]
    else:
        instructions = [
            "SPACE: Cycle Views | 1-5: Select View",
            "Arrows: Rotate | Q/E: Roll | ESC: Exit"
        ]
    y_pos = 20
    for inst in instructions:
        text = small_font.render(inst, True, CYAN)
        screen.blit(text, (WIDTH - text.get_width() - 20, y_pos))
        y_pos += 20
    
    # Main view rendering
    if current_view == VIEW_MAP:
        # Full-screen map mode
        map_viewport = pygame.Rect(10, 60, WIDTH - 20, HEIGHT - 80)
        pygame.draw.rect(screen, HUD_COLOR, map_viewport, 2)
        draw_map(screen, None, other_ships, map_viewport)
        
        # Show large status overlay
        status_font = pygame.font.Font(None, 32)
        text = status_font.render("TACTICAL MAP MODE", True, CYAN)
        screen.blit(text, (map_viewport.centerx - text.get_width() // 2, 
                          map_viewport.bottom - 40))
    
    elif current_view == VIEW_SURFACE:
        # Lander-style surface view
        # Black space background
        pygame.draw.rect(screen, BLACK, MAIN_VIEW_RECT)
        
        # Draw some distant stars (stationary)
        for i in range(20):
            star_x = MAIN_VIEW_RECT.left + (i * 37) % MAIN_VIEW_RECT.width
            star_y = MAIN_VIEW_RECT.top + (i * 53) % (MAIN_VIEW_RECT.height // 2)
            pygame.draw.circle(screen, (100, 100, 100), (star_x, star_y), 1)
        
        # Draw the surface
        draw_terrain_surface(screen, terrain, MAIN_VIEW_RECT, camera_x, altitude)
        
        # Draw simplified radar (surface mode)
        draw_radar(screen, None, other_ships, RADAR_RECT)
        
        # Draw map with terrain position indicator
        map_center_x = MAP_RECT.centerx
        map_center_y = MAP_RECT.centery
        pygame.draw.rect(screen, BLACK, MAP_RECT)
        pygame.draw.rect(screen, HUD_COLOR, MAP_RECT, 2)
        
        # Draw terrain strip
        for i in range(-20, 21):
            world_x = (camera_x + i * 2) % terrain.width
            idx = int(world_x / terrain.resolution) % terrain.points
            height = terrain.heights[idx]
            
            x = map_center_x + i * 5
            y = map_center_y + int(height * 2)
            
            if MAP_RECT.collidepoint(x, y):
                pygame.draw.circle(screen, (0, 150, 100), (x, y), 1)
        
        # Player position on terrain map
        pygame.draw.circle(screen, CYAN, (map_center_x, map_center_y), 4)
        pygame.draw.circle(screen, WHITE, (map_center_x, map_center_y), 4, 1)
        
        # Map label
        map_font = pygame.font.Font(None, 18)
        text = map_font.render("TERRAIN MAP", True, HUD_COLOR)
        screen.blit(text, (MAP_RECT.left + 5, MAP_RECT.top + 5))
        
        # Status panel
        draw_status(screen, STATUS_RECT, current_view, angle_x, angle_y)
        
        # Add velocity readout to status
        vel_font = pygame.font.Font(None, 18)
        vel_text = vel_font.render(f"VEL X: {velocity_x:+.2f}", True, YELLOW)
        screen.blit(vel_text, (STATUS_RECT.left + 10, STATUS_RECT.bottom - 60))
        vel_text = vel_font.render(f"VEL Y: {velocity_y:+.2f}", True, YELLOW)
        screen.blit(vel_text, (STATUS_RECT.left + 10, STATUS_RECT.bottom - 40))
        
    else:
        # Draw starfield in main viewport
        for star in stars:
            if MAIN_VIEW_RECT.collidepoint(star[0], star[1]):
                brightness = int(star[2] * 100)
                color = (brightness, brightness, brightness)
                pygame.draw.circle(screen, color, (int(star[0]), int(star[1])), int(star[2]))
        
        # Get camera transform for current view
        if current_view in camera_angles:
            cam_x, cam_y, cam_z = camera_angles[current_view]
        else:
            cam_x, cam_y, cam_z = 0, 0, 0
        
        # Draw other ships
        for ship in other_ships:
            # Rotate ship vertices
            rotated = rotate_3d(ship_vertices, ship.angle_x, ship.angle_y, ship.angle_z)
            
            # Apply camera transform
            camera_rotated = apply_camera_transform(rotated, cam_x, cam_y, cam_z)
            
            draw_ship(screen, camera_rotated, ship.get_faces(), MAIN_VIEW_RECT, 
                     (ship.x, ship.y, ship.z))
        
        # Draw reticle
        pygame.draw.circle(screen, GREEN, MAIN_VIEW_RECT.center, 8, 1)
        pygame.draw.line(screen, GREEN,
                        (MAIN_VIEW_RECT.centerx - 15, MAIN_VIEW_RECT.centery),
                        (MAIN_VIEW_RECT.centerx - 5, MAIN_VIEW_RECT.centery), 1)
        pygame.draw.line(screen, GREEN,
                        (MAIN_VIEW_RECT.centerx + 5, MAIN_VIEW_RECT.centery),
                        (MAIN_VIEW_RECT.centerx + 15, MAIN_VIEW_RECT.centery), 1)
        pygame.draw.line(screen, GREEN,
                        (MAIN_VIEW_RECT.centerx, MAIN_VIEW_RECT.centery - 15),
                        (MAIN_VIEW_RECT.centerx, MAIN_VIEW_RECT.centery - 5), 1)
        pygame.draw.line(screen, GREEN,
                        (MAIN_VIEW_RECT.centerx, MAIN_VIEW_RECT.centery + 5),
                        (MAIN_VIEW_RECT.centerx, MAIN_VIEW_RECT.centery + 15), 1)
        
        # Draw radar
        draw_radar(screen, None, other_ships, RADAR_RECT)
        
        # Draw map
        draw_map(screen, None, other_ships, MAP_RECT)
        
        # Draw status
        draw_status(screen, STATUS_RECT, current_view, angle_x, angle_y)
    
    pygame.display.flip()
    clock.tick(60)

pygame.quit()