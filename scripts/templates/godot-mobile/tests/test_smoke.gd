extends "res://tests/test_case.gd"
## Template smoke test. Keep it; add real tests next to it.


func test_main_scene_loads() -> void:
	var scene: PackedScene = load("res://scenes/main.tscn")
	assert_true(scene != null, "main scene must load")
	assert_true(scene.can_instantiate(), "main scene must instantiate")


func test_assertions_work() -> void:
	assert_eq(1 + 1, 2)
	assert_eq(2, 2.0, "int/float compare numerically")
	assert_almost_eq(0.1 + 0.2, 0.3)
