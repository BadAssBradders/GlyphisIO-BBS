extends RigidBody2D
class_name Ship

# Simple tuning values
var thrust_force: float = 500.0
var stabilise_strength: float = 6.0

func _ready() -> void:
	gravity_scale = 1.0
	linear_damp = 0.2
	angular_damp = 0.3
	_create_collider()
	_create_visual_polygon()

func _create_collider() -> void:
	var collider := CollisionPolygon2D.new()
	# A small diamond shaped lander
	collider.polygon = PackedVector2Array([
		Vector2(0, -14),
		Vector2(9, 6),
		Vector2(0, 12),
		Vector2(-9, 6),
	])
	add_child(collider)

func _create_visual_polygon() -> void:
	var hull := Polygon2D.new()
	hull.polygon = [
		Vector2(0, -14),
		Vector2(9, 6),
		Vector2(0, 12),
		Vector2(-9, 6),
	]
	# Cyan hull
	hull.color = Color(0.0, 1.0, 1.0)
	add_child(hull)

	# Optional: a pink cockpit triangle
	var cockpit := Polygon2D.new()
	cockpit.polygon = [
		Vector2(0, -10),
		Vector2(4, 0),
		Vector2(-4, 0),
	]
	cockpit.color = Color(1.0, 0.4, 0.7)  # pink
	add_child(cockpit)

func _integrate_forces(state: PhysicsDirectBodyState2D) -> void:
	# Left mouse button = thruster
	if Input.is_mouse_button_pressed(MOUSE_BUTTON_LEFT):
		var forward := Vector2.UP.rotated(rotation)
		var force := forward * thrust_force
		state.apply_central_force(force)

	# Right mouse button = stabiliser
	if Input.is_mouse_button_pressed(MOUSE_BUTTON_RIGHT):
		# Reduce spin
		state.angular_velocity = lerp(state.angular_velocity, 0.0, stabilise_strength * state.step)
		# Try to align ship so it points up
		var desired_rotation := 0.0
		var diff := wrapf(desired_rotation - rotation, -PI, PI)
		var torque := diff * 10.0
		state.apply_torque(torque)

	# Space bar = special (for now just a debug print)
	if Input.is_action_just_pressed("special"):
		_do_special()

func _do_special() -> void:
	print("Special button pressed for ASTRO MINER")
