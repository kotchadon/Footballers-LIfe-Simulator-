from pathlib import Path

MATCH_DIR = Path("app/static/match")


def test_match_math_modules_exist():
    expected = {"prng.js", "formations.js", "movement.js"}
    assert expected <= {path.name for path in MATCH_DIR.glob("*.js")}


def test_match_math_modules_do_not_use_unseeded_math_random():
    for name in ("prng.js", "formations.js", "movement.js"):
        text = (MATCH_DIR / name).read_text()
        assert "Math.random(" not in text


def test_formation_library_contains_required_shapes():
    text = (MATCH_DIR / "formations.js").read_text()
    for shape in ("4-3-3", "4-2-3-1", "4-4-2", "3-5-2", "4-4-1"):
        assert shape in text


def test_movement_uses_delta_time_and_acceleration():
    text = (MATCH_DIR / "movement.js").read_text()
    assert "dtSeconds" in text
    assert "acceleration" in text
    assert "deceleration" in text
    assert "actor.x =" in text
