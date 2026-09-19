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

def test_slice4_event_choreography_module_exists():
    assert (
        MATCH_DIR / "event-choreography.js"
    ).exists()


def test_event_choreography_handles_authoritative_goal_save_and_miss():
    text = (
        MATCH_DIR / "event-choreography.js"
    ).read_text()

    assert "export function createEventChoreography" in text

    for token in (
        "GOAL",
        "SAVE",
        "MISS",
        "GK_DIVE",
        "GK_CATCH",
    ):
        assert token in text

    assert "playEvent" in text


def test_advance_match_session_attaches_visual_to_only_current_event():
    text = Path("app/services.py").read_text()

    start = text.index(
        "def advance_match_session("
    )

    end = text.index(
        "\ndef ",
        start + 1,
    )

    block = text[start:end]

    assert "event = dict(events[cursor])" in block
    assert (
        'event["visual"] = visual_event_metadata('
        in block
    )
    assert '"event": event' in block
    assert '"events": events' not in block


def test_bootstrap_consumes_visual_metadata_from_revealed_event_directly():
    text = (
        MATCH_DIR / "bootstrap.js"
    ).read_text()

    assert "window.FootyMatchVisuals" in text
    assert "item?.visual" in text
    assert "visual-event" not in text
    assert "fetchVisualEvent" not in text


def test_app_replay_preserves_instant_contract_and_awaits_visuals():
    text = Path("app/static/app.js").read_text()

    assert (
        "function addEventImmediate("
        "item, instant = false)"
        in text
    )

    assert (
        "async function addEvent("
        "item, instant = false)"
        in text
    )

    assert "await addEvent(payload.event);" in text
    assert (
        "await addEvent(events[index], skip);"
        in text
    )
    assert "VISUAL_TIMEOUT_MS = 1600" in text


def test_app_replay_removes_old_pitch_mutation_from_commit_path():
    text = Path("app/static/app.js").read_text()

    start = text.index(
        "function addEventImmediate("
        "item, instant = false)"
    )

    end = text.index(
        "async function addEvent("
        "item, instant = false)",
        start,
    )

    immediate = text[start:end]

    assert "animatePitchEvent(item)" not in immediate


def test_tactical_engine_exposes_authoritative_shot_override():
    text = (
        MATCH_DIR / "tactical-engine.js"
    ).read_text()

    assert "beginAuthoritativeEvent" in text
    assert "eventOverrideUntil" in text
    assert "playKeeperAction" in text
    assert "ballController.shoot" in text
    assert "ballController.deflect" in text

def test_slice7_match_focus_reuses_v5_portrait_and_live_safe_fields():
    source = Path("app/templates/match.html").read_text()
    assert '{% from "_player_visual.html" import player_visual as render_player_visual %}' in source
    assert "render_player_visual(player_visual_model" in source
    assert 'id="live-player-state"' in source
    assert 'id="live-player-fitness"' in source
    assert 'id="live-player-goals"' in source
    assert 'id="live-player-assists"' in source
    assert 'id="live-player-cards"' in source
    assert "#17" in source
    for status in ("STARTING", "BENCH", "NOT SELECTED"):
        assert status in source

    app = Path("app/static/app.js").read_text()
    assert '"ON PITCH"' in app
    assert '"SUBBED OFF"' in app

    start = source.index('id="player-briefing"')
    end = source.index("</aside>", start)
    panel = source[start:end].lower()
    assert "rating" not in panel


def test_slice7_match_route_builds_read_only_match_portrait_context():
    source = Path("app/routes.py").read_text()
    assert "player_visual_model=build_player_visual(" in source
    assert 'selection_status=session["selection_status"]' in source
    assert 'context="match"' in source


def test_slice7_shared_portrait_escapes_hostile_player_name():
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    from app.player_visuals import build_player_visual

    career = {
        "id": 17,
        "player_name": '<script>alert("x")</script>',
        "position": "CM",
        "overall": 72,
        "club_id": 4,
        "club_name": "Test United",
        "fitness": 91,
        "morale": 78,
        "stress": 22,
        "injured_weeks": 0,
        "suspended_matches": 0,
    }

    env = Environment(
        loader=FileSystemLoader(Path("app/templates")),
        autoescape=select_autoescape(("html", "xml")),
    )
    module = env.get_template("_player_visual.html").module
    visual = build_player_visual(
        career,
        selection_status="starter",
        context="match",
    )
    html = str(
        module.player_visual(
            visual,
            size="match",
            show_status=False,
        )
    )

    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_slice7_live_team_indicators_are_explicitly_presentation_only():
    source = Path("app/templates/match.html").read_text()
    for token in (
        'id="home-revealed-shots"',
        'id="away-revealed-shots"',
        'id="match-pressure"',
        'id="match-territory"',
        "PRESENTATION",
    ):
        assert token in source


def test_slice7_audio_toggle_defaults_off_and_is_accessible():
    source = Path("app/templates/match.html").read_text()
    assert 'id="match-audio-toggle"' in source
    assert 'aria-pressed="false"' in source
    assert "Audio off" in source


def test_slice7_audio_controller_is_local_synthesis_only():
    audio = Path("app/static/match/audio.js")
    assert audio.exists()
    text = audio.read_text()
    assert "export function createAudioController" in text
    assert "enabled = false" in text
    assert "function setEnabled(" in text
    assert "function play(" in text
    for cue in ("whistle", "kick", "crowd", "goal"):
        assert f'"{cue}"' in text
    lowered = text.lower()
    assert "http://" not in lowered
    assert "https://" not in lowered
    assert "new audio(" not in lowered


def test_final_review_shortcut_help_matches_1_2_4_replay_contract():
    text = Path("app/templates/base.html").read_text()
    assert "<kbd>1/2/4</kbd><span>Replay speed</span>" in text
    assert "<kbd>1–3</kbd><span>Replay speed</span>" not in text
