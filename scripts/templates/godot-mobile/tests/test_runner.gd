extends SceneTree
## Headless test runner (no addons).
## Run: godot --headless --path <project> -s res://tests/test_runner.gd
## Runs every test_*() method in res://tests/test_*.gd. Exit 0 = all passed.
## studio.py also fails the run if Godot prints SCRIPT ERROR (GDScript has no
## exceptions, so a crashing test would otherwise look like a pass).

const TEST_DIR := "res://tests"


func _initialize() -> void:
	var files: Array[String] = []
	for f in DirAccess.get_files_at(TEST_DIR):
		if f.begins_with("test_") and f.ends_with(".gd") and f != "test_runner.gd" and f != "test_case.gd":
			files.append(f)
	files.sort()
	var passed := 0
	var failed := 0
	for f in files:
		var script: GDScript = load(TEST_DIR.path_join(f))
		if script == null or not script.can_instantiate():
			print("FAIL %s: script failed to load" % f)
			failed += 1
			continue
		for m in script.get_script_method_list():
			var method: String = m["name"]
			if not method.begins_with("test_"):
				continue
			var t: Object = script.new()
			if t.has_method("before_each"):
				t.call("before_each")
			t.call(method)
			var errs: Array = t.get("failures")
			if errs.is_empty():
				passed += 1
				print("ok   %s::%s" % [f, method])
			else:
				failed += 1
				for e in errs:
					print("FAIL %s::%s - %s" % [f, method, e])
	print("RESULT: %d passed, %d failed" % [passed, failed])
	quit(1 if failed > 0 or passed == 0 else 0)
