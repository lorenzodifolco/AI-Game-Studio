extends Node2D
## Entry scene placeholder. Replace with the game's root scene during prototyping.


func _ready() -> void:
	var label := Label.new()
	label.text = "{{TITLE}}"
	label.position = Vector2(40, 600)
	label.add_theme_font_size_override("font_size", 48)
	add_child(label)


func _notification(what: int) -> void:
	# Android back button / gesture. Replace with "open pause menu" once one exists.
	if what == NOTIFICATION_WM_GO_BACK_REQUEST:
		get_tree().quit()
