import pygame
import numpy as np
import math
from pygame.locals import *

# Initialize Pygame
pygame.init()

# Constants
SCREEN_WIDTH = 872
SCREEN_HEIGHT = 654
FPS = 60

# Physics constants
GRAVITY = 0.15  # Moon-like gravity (about 1/6 of Earth)
THRUST_INCREMENT = 0.02  # How quickly thrust builds up
MAX_THRUST = 1.5
DAMPING = 0.98  # Slight air resistance

# Colors
SKY_COLOR = (20, 20, 30)
GROUND_COLOR = (60, 60, 70)
SHIP_GREY = (120, 130, 140)
SHIP_DARK = (80, 90, 100)
SHIP_LIGHT = (150, 160, 170)
COCKPIT_COLOR = (30, 30, 40)
ENGINE_GLOW = (255, 200, 100)

class Camera:
    def __init__(self):
        self.position = np.array([0.0, -5.0, -15.0])
        self.rotation = np.array([20.0, 0.0, 0.0])  # pitch, yaw, roll
        
    def get_view_matrix(self):
        # Simple view transformation
        return self.position, self.rotation

class Vector3D:
    @staticmethod
    def normalize(v):
        norm = np.linalg.norm(v)
        if norm == 0:
            return v
        return v / norm
    
    @staticmethod
    def cross(v1, v2):
        return np.cross(v1, v2)
    
    @staticmethod
    def dot(v1, v2):
        return np.dot(v1, v2)

class Spaceship:
    def __init__(self):
        # Define the spaceship vertices
        self.vertices = self.create_spaceship_geometry()
        self.faces = self.create_spaceship_faces()
        
        # Physics properties
        self.position = np.array([0.0, 3.0, 0.0])
        self.velocity = np.array([0.0, 0.0, 0.0])
        self.rotation = np.array([0.0, 0.0, 0.0])  # pitch, yaw, roll
        self.angular_velocity = np.array([0.0, 0.0, 0.0])
        
        # Thrust
        self.current_thrust = 0.0
        self.thrusting = False
        
    def create_spaceship_geometry(self):
        """Create the low-poly spaceship vertices"""
        vertices = []
        
        # Nose point (front)
        vertices.append(np.array([0.0, 0.0, 3.0]))  # 0
        
        # Forward section (cockpit area)
        vertices.append(np.array([-0.3, 0.2, 2.0]))  # 1 - left top
        vertices.append(np.array([0.3, 0.2, 2.0]))   # 2 - right top
        vertices.append(np.array([-0.3, -0.2, 2.0])) # 3 - left bottom
        vertices.append(np.array([0.3, -0.2, 2.0]))  # 4 - right bottom
        
        # Mid section (wider)
        vertices.append(np.array([-0.8, 0.3, 0.0]))  # 5 - left top
        vertices.append(np.array([0.8, 0.3, 0.0]))   # 6 - right top
        vertices.append(np.array([-0.8, -0.2, 0.0])) # 7 - left bottom
        vertices.append(np.array([0.8, -0.2, 0.0]))  # 8 - right bottom
        
        # Rear section (massive trapezoid for engine)
        vertices.append(np.array([-1.5, 0.4, -2.0]))  # 9 - left top back
        vertices.append(np.array([1.5, 0.4, -2.0]))   # 10 - right top back
        vertices.append(np.array([-1.5, -0.3, -2.0])) # 11 - left bottom back
        vertices.append(np.array([1.5, -0.3, -2.0]))  # 12 - right bottom back
        
        # Wing tips (extended lateral edges)
        vertices.append(np.array([-2.0, 0.1, -1.0]))  # 13 - left wing tip
        vertices.append(np.array([2.0, 0.1, -1.0]))   # 14 - right wing tip
        
        return np.array(vertices)
    
    def create_spaceship_faces(self):
        """Define faces as triangles with colors"""
        faces = []
        
        # Top surfaces (dorsal spine)
        faces.append({'indices': [0, 2, 1], 'color': SHIP_LIGHT})  # Nose top
        faces.append({'indices': [1, 2, 6], 'color': SHIP_GREY})   # Forward top left
        faces.append({'indices': [1, 6, 5], 'color': SHIP_GREY})   # Forward top left 2
        faces.append({'indices': [6, 10, 5], 'color': SHIP_DARK})  # Mid-rear top left
        faces.append({'indices': [5, 10, 9], 'color': SHIP_DARK})  # Rear top left
        faces.append({'indices': [6, 14, 10], 'color': SHIP_GREY}) # Wing right
        faces.append({'indices': [5, 9, 13], 'color': SHIP_GREY})  # Wing left
        
        # Bottom surfaces (underside - thrust area)
        faces.append({'indices': [0, 3, 4], 'color': SHIP_DARK})   # Nose bottom
        faces.append({'indices': [3, 7, 4], 'color': SHIP_GREY})   # Forward bottom
        faces.append({'indices': [4, 7, 8], 'color': SHIP_GREY})   # Forward bottom 2
        faces.append({'indices': [7, 11, 8], 'color': SHIP_LIGHT}) # Mid-rear bottom
        faces.append({'indices': [8, 11, 12], 'color': SHIP_LIGHT})# Rear bottom
        
        # Side surfaces
        faces.append({'indices': [0, 1, 3], 'color': SHIP_GREY})   # Nose left
        faces.append({'indices': [0, 4, 2], 'color': SHIP_GREY})   # Nose right
        faces.append({'indices': [1, 5, 7], 'color': SHIP_DARK})   # Left side forward
        faces.append({'indices': [1, 7, 3], 'color': SHIP_DARK})   # Left side forward 2
        faces.append({'indices': [2, 4, 8], 'color': SHIP_DARK})   # Right side forward
        faces.append({'indices': [2, 8, 6], 'color': SHIP_DARK})   # Right side forward 2
        faces.append({'indices': [5, 13, 7], 'color': SHIP_GREY})  # Left wing
        faces.append({'indices': [7, 13, 11], 'color': SHIP_GREY}) # Left wing lower
        faces.append({'indices': [6, 8, 14], 'color': SHIP_GREY})  # Right wing
        faces.append({'indices': [8, 12, 14], 'color': SHIP_GREY}) # Right wing lower
        faces.append({'indices': [13, 9, 11], 'color': SHIP_DARK}) # Left rear
        faces.append({'indices': [14, 12, 10], 'color': SHIP_DARK})# Right rear
        
        # Rear engine face (massive trapezoid - bright glow)
        faces.append({'indices': [9, 10, 11], 'color': ENGINE_GLOW})
        faces.append({'indices': [10, 12, 11], 'color': ENGINE_GLOW})
        
        # Cockpit canopy (dark quadrilateral near nose)
        faces.append({'indices': [1, 2, 4], 'color': COCKPIT_COLOR})
        faces.append({'indices': [1, 4, 3], 'color': COCKPIT_COLOR})
        
        return faces
    
    def apply_thrust(self, delta_time):
        """Apply upward thrust when thrusting"""
        if self.thrusting:
            self.current_thrust = min(self.current_thrust + THRUST_INCREMENT, MAX_THRUST)
        else:
            self.current_thrust = max(self.current_thrust - THRUST_INCREMENT * 2, 0.0)
        
        # Apply thrust force upward
        thrust_force = np.array([0.0, self.current_thrust, 0.0])
        self.velocity += thrust_force * delta_time
    
    def update(self, delta_time):
        """Update physics"""
        # Apply gravity
        self.velocity[1] -= GRAVITY * delta_time
        
        # Apply thrust
        self.apply_thrust(delta_time)
        
        # Apply damping
        self.velocity *= DAMPING
        
        # Update position
        self.position += self.velocity * delta_time
        
        # Ground collision
        if self.position[1] < 0.5:
            self.position[1] = 0.5
            self.velocity[1] = max(0, self.velocity[1])  # Stop downward velocity
            self.velocity *= 0.8  # Landing friction
        
        # Slight auto-rotation for visual interest
        self.rotation[1] += 0.5 * delta_time

def rotate_point(point, rotation):
    """Rotate a point by given angles (pitch, yaw, roll)"""
    pitch, yaw, roll = np.radians(rotation)
    
    # Rotation around X axis (pitch)
    cos_p, sin_p = np.cos(pitch), np.sin(pitch)
    Rx = np.array([[1, 0, 0],
                   [0, cos_p, -sin_p],
                   [0, sin_p, cos_p]])
    
    # Rotation around Y axis (yaw)
    cos_y, sin_y = np.cos(yaw), np.sin(yaw)
    Ry = np.array([[cos_y, 0, sin_y],
                   [0, 1, 0],
                   [-sin_y, 0, cos_y]])
    
    # Rotation around Z axis (roll)
    cos_r, sin_r = np.cos(roll), np.sin(roll)
    Rz = np.array([[cos_r, -sin_r, 0],
                   [sin_r, cos_r, 0],
                   [0, 0, 1]])
    
    # Combined rotation
    R = Rz @ Ry @ Rx
    return R @ point

def project_point(point, camera_pos, camera_rot):
    """Project 3D point to 2D screen coordinates"""
    # Translate relative to camera
    translated = point - camera_pos
    
    # Rotate according to camera
    rotated = rotate_point(translated, camera_rot)
    
    # Simple perspective projection
    fov = 500
    distance = 10
    
    if rotated[2] > 0.1:  # Prevent division by zero and behind camera
        scale = fov / (rotated[2] + distance)
        x = rotated[0] * scale + SCREEN_WIDTH / 2
        y = -rotated[1] * scale + SCREEN_HEIGHT / 2
        return (int(x), int(y)), rotated[2]
    return None, rotated[2]

def calculate_lighting(normal, light_dir):
    """Calculate simple diffuse lighting"""
    normal = Vector3D.normalize(normal)
    light_dir = Vector3D.normalize(light_dir)
    intensity = max(0.3, min(1.0, Vector3D.dot(normal, light_dir)))
    return intensity

def draw_ground(screen, camera_pos, camera_rot):
    """Draw a simple ground plane"""
    ground_size = 50
    ground_y = 0
    
    # Define ground corners
    corners = [
        np.array([-ground_size, ground_y, -ground_size]),
        np.array([ground_size, ground_y, -ground_size]),
        np.array([ground_size, ground_y, ground_size]),
        np.array([-ground_size, ground_y, ground_size])
    ]
    
    # Project corners
    projected = []
    for corner in corners:
        pos, depth = project_point(corner, camera_pos, camera_rot)
        if pos:
            projected.append(pos)
    
    if len(projected) == 4:
        pygame.draw.polygon(screen, GROUND_COLOR, projected)
        
        # Draw grid lines
        grid_step = 5
        grid_color = (80, 80, 90)
        for i in range(-ground_size, ground_size + 1, grid_step):
            # Lines along Z
            p1, d1 = project_point(np.array([i, ground_y, -ground_size]), camera_pos, camera_rot)
            p2, d2 = project_point(np.array([i, ground_y, ground_size]), camera_pos, camera_rot)
            if p1 and p2:
                pygame.draw.line(screen, grid_color, p1, p2, 1)
            
            # Lines along X
            p1, d1 = project_point(np.array([-ground_size, ground_y, i]), camera_pos, camera_rot)
            p2, d2 = project_point(np.array([ground_size, ground_y, i]), camera_pos, camera_rot)
            if p1 and p2:
                pygame.draw.line(screen, grid_color, p1, p2, 1)

def draw_spaceship(screen, spaceship, camera):
    """Draw the spaceship with proper 3D rendering"""
    camera_pos, camera_rot = camera.get_view_matrix()
    light_direction = np.array([0.0, -1.0, 0.3])  # Soft spotlight from above
    
    # Transform all vertices
    transformed_vertices = []
    for vertex in spaceship.vertices:
        # Rotate vertex
        rotated = rotate_point(vertex, spaceship.rotation)
        # Translate to world position
        world_pos = rotated + spaceship.position
        # Project to screen
        screen_pos, depth = project_point(world_pos, camera_pos, camera_rot)
        transformed_vertices.append((screen_pos, depth, world_pos))
    
    # Prepare faces with depth for sorting
    faces_to_draw = []
    for face in spaceship.faces:
        indices = face['indices']
        
        # Get the three vertices of the triangle
        if all(transformed_vertices[i][0] is not None for i in indices):
            v1, v2, v3 = [transformed_vertices[i] for i in indices]
            
            # Calculate average depth for face sorting
            avg_depth = (v1[1] + v2[1] + v3[1]) / 3
            
            # Calculate face normal for backface culling and lighting
            edge1 = v2[2] - v1[2]
            edge2 = v3[2] - v1[2]
            normal = Vector3D.cross(edge1, edge2)
            
            # Backface culling
            view_dir = v1[2] - camera_pos
            if Vector3D.dot(normal, view_dir) < 0:
                # Calculate lighting
                base_color = face['color']
                
                # Special handling for engine glow (always bright)
                if base_color == ENGINE_GLOW:
                    # Add pulsing effect to engine
                    pulse = 0.8 + 0.2 * abs(math.sin(pygame.time.get_ticks() / 200))
                    lit_color = tuple(int(c * pulse) for c in base_color)
                else:
                    lighting = calculate_lighting(normal, light_direction)
                    lit_color = tuple(int(c * lighting) for c in base_color)
                
                faces_to_draw.append({
                    'vertices': [v1[0], v2[0], v3[0]],
                    'depth': avg_depth,
                    'color': lit_color
                })
    
    # Sort faces by depth (painter's algorithm)
    faces_to_draw.sort(key=lambda f: f['depth'], reverse=True)
    
    # Draw faces
    for face in faces_to_draw:
        pygame.draw.polygon(screen, face['color'], face['vertices'])
        # Draw edges for low-poly look
        pygame.draw.polygon(screen, (0, 0, 0), face['vertices'], 1)
    
    # Draw thrust effect when active
    if spaceship.current_thrust > 0.1:
        # Draw particles/glow under the ship
        thrust_alpha = int(spaceship.current_thrust / MAX_THRUST * 200)
        thrust_size = int(spaceship.current_thrust / MAX_THRUST * 30)
        
        # Get bottom center position
        bottom_center = spaceship.position + np.array([0.0, -0.5, -1.0])
        screen_pos, depth = project_point(bottom_center, camera_pos, camera_rot)
        
        if screen_pos:
            # Create thrust glow surface
            thrust_surface = pygame.Surface((thrust_size * 2, thrust_size * 3), pygame.SRCALPHA)
            for i in range(3):
                alpha = thrust_alpha // (i + 1)
                size = thrust_size // (i + 1)
                pygame.draw.ellipse(thrust_surface, (*ENGINE_GLOW, alpha), 
                                  (thrust_size - size, thrust_size - size, size * 2, size * 3))
            screen.blit(thrust_surface, (screen_pos[0] - thrust_size, screen_pos[1] - thrust_size))

def main():
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Low-Poly Spaceship - Moon Physics")
    clock = pygame.time.Clock()
    
    # Create game objects
    camera = Camera()
    spaceship = Spaceship()
    
    # Font for HUD
    font = pygame.font.Font(None, 24)
    
    running = True
    while running:
        delta_time = clock.tick(FPS) / 1000.0  # Convert to seconds
        
        # Event handling
        for event in pygame.event.get():
            if event.type == QUIT:
                running = False
            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    running = False
        
        # Mouse input for thrust
        mouse_buttons = pygame.mouse.get_pressed()
        spaceship.thrusting = mouse_buttons[0]  # Left mouse button
        
        # Update
        spaceship.update(delta_time)
        
        # Render
        screen.fill(SKY_COLOR)
        
        # Draw ground first
        draw_ground(screen, camera.position, camera.rotation)
        
        # Draw spaceship
        draw_spaceship(screen, spaceship, camera)
        
        # Draw HUD
        altitude_text = font.render(f"Altitude: {spaceship.position[1]:.1f}m", True, (200, 200, 200))
        thrust_text = font.render(f"Thrust: {spaceship.current_thrust/MAX_THRUST*100:.0f}%", True, (200, 200, 200))
        velocity_text = font.render(f"Velocity: {np.linalg.norm(spaceship.velocity):.2f}m/s", True, (200, 200, 200))
        control_text = font.render("Hold LEFT MOUSE to thrust", True, (150, 150, 150))
        
        screen.blit(altitude_text, (10, 10))
        screen.blit(thrust_text, (10, 35))
        screen.blit(velocity_text, (10, 60))
        screen.blit(control_text, (10, SCREEN_HEIGHT - 30))
        
        pygame.display.flip()
    
    pygame.quit()

if __name__ == "__main__":
    main()