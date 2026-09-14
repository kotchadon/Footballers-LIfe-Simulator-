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


def test_bootstrap_delegates_animation_to_match_engine_and_uses_server_visual_plan():
    text = (MATCH_DIR / "bootstrap.js").read_text()
    assert "root.dataset.visualEndpoint" in text
    assert 'from "./match-engine.js"' in text
    assert 'from "./tactical-engine.js"' in text
    assert "createMatchEngine" in text
    assert "createTacticalEngine" in text
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

def test_slice2_tactical_engine_modules_exist():
    expected = {"tactical-engine.js", "match-engine.js"}
    assert expected <= {path.name for path in MATCH_DIR.iterdir() if path.is_file()}


def test_tactical_engine_has_real_football_phases_and_no_unseeded_random():
    text = (MATCH_DIR / "tactical-engine.js").read_text()
    assert "export function createTacticalEngine" in text
    for phase in (
        "BUILDUP",
        "PROGRESSION",
        "FINAL_THIRD",
        "TRANSITION_ATTACK",
        "TRANSITION_DEFENCE",
        "DEFENSIVE_BLOCK",
    ):
        assert phase in text
    assert "Math.random(" not in text


def test_tactical_engine_uses_localized_pressing_and_cover():
    text = (MATCH_DIR / "tactical-engine.js").read_text()
    assert "primaryPresserId" in text
    assert "coverActorId" in text
    assert "nearestOutfieldActors" in text
    assert "pressIntensity" in text


def test_tactical_engine_changes_shape_for_possession_and_ball_side():
    text = (MATCH_DIR / "tactical-engine.js").read_text()
    assert "possessionXShift" in text
    assert "ballSideShift" in text
    assert "compactness" in text
    assert "width" in text


def test_tactical_engine_has_role_specific_off_ball_runs():
    text = (MATCH_DIR / "tactical-engine.js").read_text()
    assert "roleMovementOffset" in text
    assert "overlap" in text
    assert "runBehind" in text
    assert "supportRun" in text


def test_tactical_engine_responds_to_score_and_late_match_context():
    text = (MATCH_DIR / "tactical-engine.js").read_text()
    assert "homeScore" in text
    assert "awayScore" in text
    assert "context.minute" in text
    assert ">= 70" in text
    assert "trailing" in text
    assert "leading" in text


def test_match_engine_owns_animation_loop_pause_and_hidden_tab_behavior():
    text = (MATCH_DIR / "match-engine.js").read_text()
    assert "export function createMatchEngine" in text
    assert "requestAnimationFrame" in text
    assert "visibilitychange" in text
    assert "setSpeed" in text
    assert "pause" in text
    assert "resume" in text


def test_bootstrap_uses_tactical_engine_instead_of_manual_sine_drift():
    text = (MATCH_DIR / "bootstrap.js").read_text()
    assert 'from "./tactical-engine.js"' in text
    assert 'from "./match-engine.js"' in text
    assert "createTacticalEngine" in text
    assert "createMatchEngine" in text
    assert "amplitudeX" not in text
    assert "amplitudeY" not in text


def test_slice2_ball_is_driven_by_tactical_possession():
    text = (MATCH_DIR / "tactical-engine.js").read_text()
    assert "ownerActorId" in text
    assert "selectCarrier" in text
    assert "updateBall" in text

def test_slice3_ball_and_animation_modules_exist():
    expected = {"ball.js", "animation-controller.js"}
    assert expected <= {path.name for path in MATCH_DIR.iterdir() if path.is_file()}


def test_ball_controller_supports_control_pass_cross_shot_and_deflection():
    text = (MATCH_DIR / "ball.js").read_text()
    assert "export function createBallController" in text
    for state in (
        "CONTROLLED",
        "PASS",
        "LONG_BALL",
        "CROSS",
        "SHOT",
        "DEFLECTION",
        "KEEPER_HELD",
    ):
        assert state in text
    for method in ("control(", "pass(", "cross(", "shoot(", "deflect(", "update("):
        assert method in text


def test_ball_controller_uses_visual_height_arc_and_no_unseeded_random():
    text = (MATCH_DIR / "ball.js").read_text()
    assert "4 * action.maxHeight * progress * (1 - progress)" in text
    assert "Math.random(" not in text


def test_animation_controller_has_timed_action_states():
    text = (MATCH_DIR / "animation-controller.js").read_text()
    assert "export function createAnimationController" in text
    assert "play(actorId" in text
    assert "getState(actorId" in text
    assert "update(dtSeconds" in text
    for state in ("RECEIVE", "DRIBBLE", "PASS", "LONG_PASS", "CROSS", "SHOOT", "GK_DIVE"):
        assert state in text


def test_player_rig_contains_receive_dribble_cross_and_long_pass_poses():
    text = (MATCH_DIR / "player-rig.js").read_text()
    for state in ("RECEIVE", "DRIBBLE", "LONG_PASS", "CROSS"):
        assert state in text


def test_tactical_engine_runs_visual_pass_sequences_between_carriers():
    text = (MATCH_DIR / "tactical-engine.js").read_text()
    assert 'from "./ball.js"' in text
    assert 'from "./animation-controller.js"' in text
    assert "schedulePass" in text
    assert "selectReceiver" in text
    assert "passClock" in text
    assert "ballController.update" in text
    assert "animationController.update" in text


def test_tactical_filler_does_not_trigger_visual_shot_actions():
    text = (MATCH_DIR / "tactical-engine.js").read_text()
    section = text.split("function schedulePass", 1)[1].split("function updateTeamStates", 1)[0]
    assert ".shoot(" not in section
    assert '"SHOOT"' not in section


def test_pass_sequences_have_receive_and_passing_body_animation():
    text = (MATCH_DIR / "tactical-engine.js").read_text()
    assert '"PASS"' in text
    assert '"LONG_PASS"' in text
    assert '"CROSS"' in text
    assert '"RECEIVE"' in text


def test_renderer_still_draws_ball_height_and_shadow():
    text = (MATCH_DIR / "renderer.js").read_text()
    assert "ball.height" in text
    assert "ground = projection" in text
    assert "ctx.ellipse" in text
