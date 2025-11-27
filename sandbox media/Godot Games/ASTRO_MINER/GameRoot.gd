extends Node2D

func _ready():
	# Set window size and mode again at runtime, just to be sure
	DisplayServer.window_set_size(Vector2i(872, 654))
	DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_WINDOWED)
	DisplayServer.window_set_flag(DisplayServer.WINDOW_FLAG_RESIZE_DISABLED, true)

	# Create a dark blue background
	var bg = ColorRect.new()
	bg.color = Color(0.02, 0.02, 0.08)  # dark blue
	bg.size = get_viewport_rect().size
	add_child(bg)

	# Create and add the ship (we will define Ship.gd shortly)
	var ship = Ship.new()
	add_child(ship)
	ship.position = get_viewport_rect().size / 2
