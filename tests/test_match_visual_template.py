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



def test_match_renderer_files_exist():
    expected = {"player-rig.js", "renderer.js", "bootstrap.js", "match.css"}
    assert expected <= {path.name for path in MATCH_DIR.iterdir() if path.is_file()}


def test_match_template_exposes_layered_svg_canvas_stage():
    text = Path("app/templates/match.html").read_text()
    assert 'id="match-visual-stage"' in text
    assert 'id="match-pitch-svg"' in text
    assert 'id="match-canvas"' in text
    assert 'data-visual-endpoint=' in text
    assert "match/bootstrap.js" in text
    assert "match/match.css" in text


def test_match_speed_control_uses_four_x_not_three_x():
    text = Path("app/templates/match.html").read_text()
    assert 'data-match-speed="4"' in text
    assert 'data-match-speed="3"' not in text


def test_player_rig_is_articulated_and_has_key_action_poses():
    text = (MATCH_DIR / "player-rig.js").read_text()
    assert "drawPlayerRig" in text
    assert "poseForState" in text
    for state in ("IDLE", "JOG", "RUN", "SPRINT", "PASS", "SHOOT", "GK_SET", "GK_DIVE"):
        assert state in text
    assert "leftKnee" in text
    assert "rightKnee" in text


def test_renderer_uses_canvas_dpr_projection_and_failure_hook():
    text = (MATCH_DIR / "renderer.js").read_text()
    assert 'getContext("2d"' in text
    assert "devicePixelRatio" in text
    assert "broadcastProjection" in text
    assert "onError(error)" in text


def test_bootstrap_uses_animation_frames_and_server_visual_plan():
    text = (MATCH_DIR / "bootstrap.js").read_text()
    assert "requestAnimationFrame" in text
    assert "root.dataset.visualEndpoint" in text
    assert "formationAnchors" in text
    assert "integrateMovement" in text
    assert "Math.random(" not in text


def test_match_css_contains_reduced_motion_and_visual_stage():
    text = (MATCH_DIR / "match.css").read_text()
    assert ".match-visual-stage" in text
    assert "prefers-reduced-motion" in text


def test_base_template_has_page_asset_extension_blocks():
    text = Path("app/templates/base.html").read_text()
    assert "{% block head_extra %}" in text
    assert "{% block scripts_extra %}" in text


def test_visual_plan_api_is_presentation_only():
    routes = Path("app/routes.py").read_text()
    services = Path("app/services.py").read_text()
    assert '"/api/matches/<session_id>/visual-plan"' in routes
    assert "def get_match_visual_plan(" in services
    helper = services.split("def get_match_visual_plan(", 1)[1].split("def get_match_session_view(", 1)[0]
    assert "simulation_json" in helper
    assert 'snapshot.get("visual")' in helper
