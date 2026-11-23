---
name: godot-dev
description: Godot 4 / GDScript 4 engineering reference for this studio - project layout, mobile settings, Godot-3-to-4 pitfalls, headless testing, Android export. Preloaded by godot-engineer and qa-tester; read it before writing or reviewing GDScript.
user-invocable: false
---

# Godot 4 reference (studio conventions)

## Project layout (`games/<slug>/project/`, created by `studio.py scaffold`)
```
project.godot        portrait 720x1280, stretch canvas_items/expand, GL Compatibility renderer
export_presets.cfg   preset "Android" (debug APK, no Gradle build by default)
scenes/              *.tscn: thin, wiring only
scripts/             *.gd: node scripts
scripts/logic/       pure game rules (extends RefCounted), unit-tested headless
assets/              *.svg art, sfx/*.wav|ogg, fonts/
data/                runtime data; read design/balance.json via a copy or loader (see below)
tests/               test_runner.gd, test_case.gd, test_*.gd
```
- Balance data: copy `design/balance.json` to `project/data/balance.json` (keep them identical; the engineer syncs them) and load it with `JSON.parse_string(FileAccess.get_file_as_string("res://data/balance.json"))`.
- Autoloads (singletons) only for truly global services: `Save`, `Audio`, `Events` (signal bus). Register them in `project.godot` under `[autoload]`.
- Save data goes to `user://save.json` (it persists on Android). Write a temp file, then rename.

## GDScript 4: pitfalls (Godot 3 syntax is a bug here)
| Wrong (Godot 3) | Right (Godot 4) |
|---|---|
| `export var x = 1` · `onready var n = $N` | `@export var x := 1` · `@onready var n: Node2D = $N` |
| `yield(obj, "sig")` | `await obj.sig` |
| `connect("pressed", self, "_on_p")` | `button.pressed.connect(_on_p)` |
| `emit_signal("hit", 1)` (works, but avoid) | `hit.emit(1)` |
| `scene.instance()` | `scene.instantiate()` |
| `KinematicBody2D`, `move_and_slide(vel)` | `CharacterBody2D`; set `velocity`, then `move_and_slide()` |
| `Tween` node, `interpolate_property` | `var t := create_tween(); t.tween_property(n, "position", p, 0.3)` |
| `File.new().open()` | `FileAccess.open(path, FileAccess.READ)` (static) |
| `Directory` | `DirAccess` |
| `rand_range(a, b)` | `randf_range(a, b)` / `randi_range(a, b)` |
| `.empty()` | `.is_empty()` |
| `Engine.editor_hint`, `tool` | `Engine.is_editor_hint()`, `@tool` |
| `setget` | `var x: int: set = _set_x, get = _get_x` (or inline `set(v):`) |
| `PoolStringArray` | `PackedStringArray` |
| `rect_position`, `rect_size` | `position`, `size` (Control) |
| `OS.get_ticks_msec()` | `Time.get_ticks_msec()` |
| `str2var`, `to_json` | `str_to_var`, `JSON.stringify` |

More rules:
- Type everything (`var speed: float = 200.0`, `func f(a: int) -> void:`). Use `:=` only when the type is obvious.
- Indent with tabs. `class_name` works only after an import (`studio.py test` runs `--import` on the first run). Tests use path-based `extends "res://..."`.
- Never call `get_node()` in `_process`; cache it with `@onready`. Avoid allocating arrays or dictionaries every frame.
- Use `queue_free()` instead of `free()` for nodes in the tree. Connect signals in `_ready`.
- Input: handle `InputEventScreenTouch` and `InputEventScreenDrag`. Mouse→touch emulation is on, so the desktop runs work. Use `_unhandled_input` for gameplay so UI can consume input first.

## Mobile essentials
- Portrait 720×1280 base; anchors and containers for UI; safe area via `DisplayServer.get_display_safe_area()`.
- Back button: `NOTIFICATION_WM_GO_BACK_REQUEST` in `_notification` (pause menu, or quit from the title screen).
- Focus loss: `NOTIFICATION_APPLICATION_FOCUS_OUT` / `NOTIFICATION_APPLICATION_PAUSED` → pause and save.
- Haptics: `Input.vibrate_handheld(30)` (needs the VIBRATE permission in the preset if used).
- Performance: GL Compatibility; keep draw calls low; use `CPUParticles2D` (portable) for small effects; target 60 fps on mid-range devices.
- Art: hand-written SVG files in `assets/` (Godot imports SVG as textures) or `_draw()` with shapes. Use a consistent palette from the GDD.

## Testing (no addons)
- Run: `python scripts/studio.py test <slug>` → `godot --headless --path <project> -s res://tests/test_runner.gd`.
- A test file: `tests/test_<area>.gd` with `extends "res://tests/test_case.gd"` and `func test_<behaviour>() -> void:` using `assert_eq`, `assert_true`, `assert_false`, `assert_ne`, `assert_almost_eq`. Optional `before_each()`.
- GDScript has no exceptions. A runtime error aborts only that function, so `studio.py` fails any run that prints `SCRIPT ERROR`.
- Test the logic classes directly. For scene smoke tests, `load()` the PackedScene and `instantiate()` it, then `free()` the instance.
- Each test must be independent and deterministic: seed RNGs (`var rng := RandomNumberGenerator.new(); rng.seed = 1`).

## Android export
- Debug: `python scripts/studio.py build <slug>` → `games/<slug>/build/<slug>-debug.apk`; install with `adb install -r <apk>`.
- Prerequisites (human, one-time): Godot export templates for the exact version, plus the Android SDK and JDK paths in Editor Settings → Export → Android. The debug keystore is auto-generated by Godot or set via `GODOT_ANDROID_KEYSTORE_DEBUG_*`.
- Release: human-only (`--release --aab` needs `gradle_build/use_gradle_build=true`, an installed Android build template, and the `GODOT_ANDROID_KEYSTORE_RELEASE_*` env vars).
- Version: `version/code` (an integer that must increase) and `version/name` in `export_presets.cfg`.
