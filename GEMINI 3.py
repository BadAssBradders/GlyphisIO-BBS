from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
from ursina.prefabs.trail_renderer import TrailRenderer  # Import added here
import random

# 1. Setup the Window
app = Ursina()
window.title = "ACORN LANDER: ELITE DRIFT"
window.borderless = False
window.fullscreen = False
window.color = color.rgb(5, 5, 10)  # Deep space/night blue

# 2. Retro Aesthetics (The "Frontier" Look)
# Enable fog to hide the chunk loading and give depth
scene.fog_density = .02
scene.fog_color = color.rgb(5, 5, 10)

# 3. The Player Ship (Newtonian Physics)
class PhysicsShip(Entity):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # CHANGED: 'cone' to 'diamond' (more reliable and looks very retro/Elite)
        self.model = 'diamond' 
        self.color = color.lime
        self.scale = 1.5
        self.rotation_x = 90 # Point forward
        
        # Physics State
        self.velocity = Vec3(0, 0, 0)
        self.thrust_speed = 20
        self.torque_speed = 100
        self.gravity = 5
        self.drag = 0.5 # Space has low drag, but air has some
        self.fuel = 1000

        # Visuals: Engine trail
        self.trail = TrailRenderer(parent=self, thickness=2, color=color.orange, length=10)

    def update(self):
        dt = time.dt

        # A. Rotation Controls (Pitch/Roll/Yaw)
        # Note: In "Elite", you roll and pitch. Here we simplify to WASD for accessibility.
        if held_keys['w']: self.rotation_x -= self.torque_speed * dt
        if held_keys['s']: self.rotation_x += self.torque_speed * dt
        if held_keys['a']: self.rotation_z += self.torque_speed * dt
        if held_keys['d']: self.rotation_z -= self.torque_speed * dt
        
        # Q/E for Yaw (turning left/right flat)
        if held_keys['q']: self.rotation_y -= self.torque_speed * dt
        if held_keys['e']: self.rotation_y += self.torque_speed * dt

        # B. Thrust Physics
        thrust_vector = Vec3(0, 0, 0)
        is_thrusting = held_keys['space']

        if is_thrusting and self.fuel > 0:
            # Calculate forward vector based on rotation
            thrust_vector = self.forward * self.thrust_speed * dt
            self.fuel -= 1 * dt
            # Visual flair: Pulse color when thrusting
            self.color = color.white if random.random() > 0.5 else color.lime
        else:
            self.color = color.lime

        # C. Apply Forces
        # Gravity pulls down (negative Y)
        gravity_vector = Vec3(0, -self.gravity * dt, 0)
        
        # Add forces to velocity (Newtons 2nd Law)
        self.velocity += thrust_vector + gravity_vector
        
        # Apply Drag (Air resistance) - slows you down gradually
        self.velocity -= self.velocity * self.drag * dt

        # D. Move the Ship
        self.position += self.velocity * dt

        # E. Collision with Ground
        if self.y < 0:
            self.y = 0
            # Crash bounce
            self.velocity.y = -self.velocity.y * 0.5   # Lose energy on bounce
            self.velocity.x *= 0.5 # Friction
            self.velocity.z *= 0.5

        # Update HUD
        speed_text.text = f"SPEED: {int(self.velocity.length() * 10)}"
        alt_text.text = f"ALT: {int(self.y)}"
        fuel_text.text = f"FUEL: {int(self.fuel)}"

# 4. The World Generation (Procedural Retro Grid)
def create_retro_world():
    # The Floor: A classic infinite-looking grid
    ground = Entity(
        model='plane',
        scale=2000,
        texture='grass', # Using default grass but tinting it for synthwave look
        texture_scale=(100, 100),
        color=color.rgb(20, 20, 30),
        collider='box'
    )
    
    # Obstacles: Random "Pyramids" and "Monoliths"
    for i in range(100):
        e = Entity(
            # CHANGED: 'cone' to 'diamond' here as well to prevent errors
            model=random.choice(['cube', 'diamond']),
            position=(random.randint(-400, 400), 0, random.randint(-400, 400)),
            scale=(random.randint(10, 50), random.randint(10, 100), random.randint(10, 50)),
            color=random.choice([color.cyan, color.magenta, color.rgb(255, 0, 128)]),
            alpha=0.8,
            shader=None # Keep it flat shaded!
        )
        # Randomly rotate some to look like crashed ships or alien ruins
        e.rotation = (0, random.randint(0, 360), 0)
        
        # Make sure they sit on the ground
        e.y = e.scale_y / 2 

    return ground

# 5. Camera Logic (Smooth Follow)
class SmoothFollow(Entity):
    def __init__(self, target, offset=(0, 5, -15), speed=4):
        super().__init__()
        self.target = target
        self.offset = Vec3(*offset)
        self.speed = speed

    def update(self):
        # Desired position is behind and above the target
        # We need to transform the offset to be relative to the ship's rotation? 
        # Actually for "Lander" style, a fixed camera angle often works better 
        # to see the ship's rotation clearly. 
        
        desired_pos = self.target.position + self.offset
        
        # Lerp (Linear Interpolation) for smooth camera lag
        self.position = lerp(self.position, desired_pos, time.dt * self.speed)
        
        # Always look at the ship
        self.look_at(self.target)

# --- GAME SETUP ---

# Create World
create_retro_world()

# Create Player
ship = PhysicsShip(position=(0, 10, 0))

# Create Camera
cam_rig = SmoothFollow(target=ship)

# Create Sun
sun = Entity(model='sphere', color=color.yellow, scale=50, position=(500, 500, 500), unlit=True)

# HUD (Heads Up Display)
# Note: Fonts can sometimes cause warnings too, but 'VeraMono.ttf' usually works. 
# If it fails, Ursina defaults to a backup font automatically.
Text.default_font = 'models/font/VeraMono.ttf' 
speed_text = Text(text='SPEED: 0', position=(-0.85, 0.45), scale=1.5, color=color.cyan)
alt_text = Text(text='ALT: 0', position=(-0.85, 0.40), scale=1.5, color=color.cyan)
fuel_text = Text(text='FUEL: 1000', position=(-0.85, 0.35), scale=1.5, color=color.orange)

# Simple controls Helper
controls_text = Text(
    text='CONTROLS:\nW/S: Pitch | A/D: Roll | Q/E: Yaw | SPACE: Thrust',
    position=(0.5, 0.45),
    scale=1,
    color=color.white,
    origin=(0.5, 0)
)

# Start the Engine
app.run()