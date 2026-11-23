extends RefCounted
## Minimal assertion base for headless tests.
## Usage: create res://tests/test_<area>.gd with `extends "res://tests/test_case.gd"`
## and methods named test_<behaviour>(). Optional before_each().

var failures: Array[String] = []


func assert_true(cond: bool, msg := "") -> void:
	if not cond:
		failures.append("expected true. " + msg)


func assert_false(cond: bool, msg := "") -> void:
	if cond:
		failures.append("expected false. " + msg)


func assert_eq(actual: Variant, expected: Variant, msg := "") -> void:
	if not _same(actual, expected):
		failures.append("expected <%s> got <%s>. %s" % [str(expected), str(actual), msg])


func assert_ne(actual: Variant, unexpected: Variant, msg := "") -> void:
	if _same(actual, unexpected):
		failures.append("did not expect <%s>. %s" % [str(actual), msg])


func assert_almost_eq(actual: float, expected: float, eps := 0.0001, msg := "") -> void:
	if absf(actual - expected) > eps:
		failures.append("expected %f +/- %f got %f. %s" % [expected, eps, actual, msg])


func _same(a: Variant, b: Variant) -> bool:
	var numeric := [TYPE_INT, TYPE_FLOAT]
	if typeof(a) in numeric and typeof(b) in numeric:
		return a == b
	if typeof(a) != typeof(b):
		return false
	return a == b
