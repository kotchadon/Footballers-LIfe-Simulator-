from pathlib import Path
from app import match_visuals


def snap(status="starter", minutes=90, home=True):
    return {
        "career": {
            "id": 1, "player_name": "Advay Katoch", "position": "LW",
            "fitness": 82, "pace": 74, "shooting": 64, "passing": 68,
            "dribbling": 71, "defending": 41, "physical": 62,
        },
        "fixture": {
            "fixture_id": 101, "home_club_id": 10, "away_club_id": 11,
            "home_name": "Home FC", "away_name": "Away FC",
            "home_strength": 72, "away_strength": 69,
            "player_team_is_home": home,
        },
        "performance": {
            "selection_status": status, "minutes": minutes, "events": [],
        },
    }


def test_starter_is_active_at_kickoff():
    plan = match_visuals.build_visual_plan(snap(), 918273)
    assert plan["user_actor_id"] == "career_player"
    assert plan["career_player"]["state"] == "starting"
    assert plan["career_player"]["active_from_minute"] == 0


def test_substitute_is_bench_without_future_minute_spoiler():
    plan = match_visuals.build_visual_plan(snap("substitute", 22), 918273)
    ids = {a["actor_id"] for a in plan["actors"]}
    assert plan["user_actor_id"] is None
    assert "career_player" not in ids
    assert plan["career_player"]["state"] == "bench"
    assert plan["career_player"]["active_from_minute"] is None
    assert plan["career_player"]["active_until_minute"] is None
    assert "rating" not in plan["career_player"]


def test_unused_bench_and_unavailable_are_not_active():
    bench = match_visuals.build_visual_plan(snap("bench", 0), 918273)
    injured = match_visuals.build_visual_plan(snap("injured", 0), 918273)
    assert bench["user_actor_id"] is None
    assert bench["career_player"]["state"] == "bench"
    assert injured["user_actor_id"] is None
    assert injured["career_player"]["state"] == "not_selected"


def test_player_on_reveal_contains_activation_actor():
    visual = match_visuals.visual_event_metadata(
        snap("substitute", 22),
        {
            "sequence": 6, "minute": 68, "kind": "player_on",
            "text": "Advay comes off the bench.",
            "metadata": {"side": "player"},
        },
        6,
        seed=918273,
    )
    assert visual["kind"] == "substitution_on"
    assert visual["actor_id"] == "career_player"
    assert visual["actor"]["actor_id"] == "career_player"
    assert visual["actor"]["visual_profile"]["is_user"] is True


def test_player_off_contract_is_supported_without_creating_event():
    visual = match_visuals.visual_event_metadata(
        snap(),
        {
            "sequence": 8, "minute": 74, "kind": "player_off",
            "metadata": {"side": "player"},
        },
        8,
        seed=918273,
    )
    assert visual["kind"] == "substitution_off"
    assert visual["actor_id"] == "career_player"


def test_revealed_set_piece_classification_uses_current_event():
    visual = match_visuals.visual_event_metadata(
        snap(),
        {
            "sequence": 5, "minute": 39, "kind": "set_piece",
            "text": "A corner causes chaos before the defence clears.",
            "metadata": {"side": "neutral"},
        },
        5,
        seed=918273,
    )
    assert visual["set_piece_type"] == "corner"


def test_tactical_transition_contract():
    text = Path("app/static/match/tactical-engine.js").read_text()
    assert "TEN_MAN_SHAPES" in text
    for fn in ("removeActor", "activateActor", "switchEnds",
               "reshapeForRedCard", "prepareSetPiece"):
        assert f"function {fn}(" in text
    assert "animationController.cancelActor" in text


def test_set_piece_path_cannot_invent_shot_or_goal():
    text = Path("app/static/match/tactical-engine.js").read_text()
    part = text.split("function prepareSetPiece", 1)[1].split(
        "function beginAuthoritativeEvent", 1
    )[0]
    assert "ballController.shoot" not in part
    assert '"GOAL"' not in part


def test_corner_restart_crosses_and_neutral_event_uses_presentation_possession():
    text = Path("app/static/match/tactical-engine.js").read_text()
    part = text.split("function prepareSetPiece", 1)[1].split(
        "function beginAuthoritativeEvent", 1
    )[0]
    assert ": possessionTeam;" in part
    assert "ballController.cross(" in part
    assert '"CROSS"' in part
    assert '"RECEIVE"' in part


def test_throw_in_and_free_kick_are_restarts_not_shots():
    text = Path("app/static/match/tactical-engine.js").read_text()
    part = text.split("function prepareSetPiece", 1)[1].split(
        "function beginAuthoritativeEvent", 1
    )[0]
    assert "ballController.pass(" in part
    assert "ballController.longBall(" in part
    assert "ballController.shoot(" not in part


def test_halftime_waits_until_first_revealed_event_after_45():
    text = Path("app/static/match/event-choreography.js").read_text()
    assert "minute <= 45" in text
    assert "minute < 45" not in text


def test_animation_controller_can_cancel_removed_actor():
    text = Path("app/static/match/animation-controller.js").read_text()
    assert "function cancelActor(actorId)" in text
    assert "cancelActor," in text


def test_match_engine_transition_handlers_exist():
    text = Path("app/static/match/match-engine.js").read_text()
    for fn in ("handleHalftime", "handleSubstitution", "handleCard",
               "handlePenalty", "handleCorner", "handleThrowIn", "handleFreeKick"):
        assert f"function {fn}(" in text
        assert f"{fn}," in text
    assert "halftimeHandled" in text


def test_choreography_routes_revealed_transitions():
    text = Path("app/static/match/event-choreography.js").read_text()
    for marker in (
        'kind === "SUBSTITUTION_ON"', 'kind === "SUBSTITUTION_OFF"',
        'kind === "RED_CARD"', '"SET_PIECE"',
        "handleHalftime", "handleSubstitution", "handleCard",
    ):
        assert marker in text


def test_template_has_transition_overlay_and_plan_has_no_rating():
    html = Path("app/templates/match.html").read_text()
    assert 'id="match-transition-overlay"' in html
    assert 'id="match-transition-text"' in html
    src = Path("app/match_visuals.py").read_text()
    build = src.split("def build_visual_plan", 1)[1].split(
        "_VISUAL_EVENT_KIND_MAP", 1
    )[0]
    assert '"rating"' not in build

def test_broadcast_camera_module_contract_exists():
    camera = Path("app/static/match/camera.js")
    assert camera.exists()
    text = camera.read_text()
    assert "export function createCameraController" in text
    assert "function update(" in text
    assert "function emphasize(" in text
    assert "reducedMotion" in text
    assert "Math.random(" not in text


def test_broadcast_camera_keeps_full_pitch_bias_bounded():
    text = Path("app/static/match/camera.js").read_text()
    assert "MIN_ZOOM = .955" in text
    assert "MAX_ZOOM = .995" in text
    assert "MAX_PAN_PERCENT = 1.6" in text
    assert "clamp(" in text


def test_match_renderer_applies_same_camera_transform_to_pitch_and_canvas():
    text = Path("app/static/match/renderer.js").read_text()
    assert "pitch = null" in text
    assert "function applyCameraTransform(" in text
    assert "canvas.style.transform = transform" in text
    assert "pitch.style.transform = transform" in text
    assert "state.camera || {}" in text


def test_match_engine_uses_three_minute_clock_mapping_and_valid_speeds():
    text = Path("app/static/match/match-engine.js").read_text()
    assert "REAL_SECONDS_PER_MATCH_MINUTE = 2" in text
    assert "[1, 2, 4].includes(next)" in text
    assert "visualMinute" in text


def test_renderer_failure_is_isolated_inside_match_engine():
    text = Path("app/static/match/match-engine.js").read_text()
    assert "let visualEnabled = true" in text
    assert "renderer.render(" in text
    assert "visualEnabled = false" in text
    assert 'console.error("Match visual renderer disabled:", error)' in text


def test_camera_is_wired_into_live_event_emphasis():
    text = Path("app/static/match/bootstrap.js").read_text()
    assert 'from "./camera.js"' in text
    assert "createCameraController" in text
    assert "pitch," in text
    assert "camera," in text
    assert "engine.emphasizeEvent" in text


def test_template_keeps_1_2_4_and_adds_next_event_control():
    html = Path("app/templates/match.html").read_text()
    for speed in ("1", "2", "4"):
        assert f'data-match-speed="{speed}"' in html
    assert 'data-match-speed="3"' not in html
    assert 'id="skip-next-event"' in html
    assert 'id="finish-replay"' in html
    assert "Enter" in html


def test_replay_pacing_targets_three_minute_match_without_future_metadata():
    text = Path("app/static/app.js").read_text()
    assert "REAL_SECONDS_PER_MATCH_MINUTE = 2" in text
    assert "BASE_MATCH_DURATION_MS" in text
    assert "totalEvents" in text
    assert "next_minute" not in text
    assert "future_events" not in text


def test_skip_to_next_major_event_reveals_sequentially_through_existing_endpoint():
    text = Path("app/static/app.js").read_text()
    assert "async function skipToNextMajorEvent(" in text
    assert "function isMajorEvent(" in text
    assert "postJson(advanceEndpoint, {cursor})" in text
    assert "await addEvent(payload.event, !major)" in text
    section = text.split("async function skipToNextMajorEvent", 1)[1].split(
        "function togglePause", 1
    )[0]
    assert "remaining_events" not in section


def test_full_time_completion_path_remains_existing_authoritative_path():
    text = Path("app/static/app.js").read_text()
    assert "postJson(completeEndpoint, {skip})" in text
    assert "await addEvent(events[index], skip);" in text


def test_hidden_tab_pause_and_resume_still_prevent_delta_spike():
    text = Path("app/static/match/match-engine.js").read_text()
    assert 'document.addEventListener("visibilitychange", onVisibilityChange)' in text
    assert 'pause("hidden")' in text
    assert 'resume("hidden")' in text
    assert "lastTimestamp = performance.now()" in text


def test_camera_css_has_gpu_transform_and_reduced_motion_guard():
    css = Path("app/static/match/match.css").read_text()
    assert "will-change: transform" in css
    assert ".skip-next-event" in css
    assert "@media (prefers-reduced-motion: reduce)" in css

def test_next_major_event_n_keyboard_shortcut_is_bound_safely():
    text = Path("app/static/app.js").read_text()
    assert "function handleNextEventShortcut(event)" in text
    assert 'event.key.toLowerCase() !== "n"' in text
    assert "event.repeat" in text
    assert "event.metaKey" in text
    assert "event.ctrlKey" in text
    assert "event.altKey" in text
    assert "target.isContentEditable" in text
    assert 'target.matches("input, textarea, select")' in text
    assert "event.preventDefault()" in text
    assert "skipToNextMajorEvent()" in text
    assert 'document.addEventListener(' in text
    assert '"keydown"' in text
    assert "handleNextEventShortcut" in text

def test_slice7_live_player_stats_only_consume_revealed_event_argument():
    text = Path("app/static/app.js").read_text()
    start = text.index("function updateLivePresentation(item)")
    end = text.index("function addEventImmediate(", start)
    block = text[start:end]

    assert "item?.visual" in block
    assert "item?.metadata?.contribution" in block
    assert '"career_player"' in block
    assert '"substitution_on"' in block
    assert '"substitution_off"' in block
    assert '"goal"' in block
    assert '"assist"' in block
    assert '"yellow_card"' in block
    assert '"red_card"' in block
    assert "fetch(" not in block
    assert "completeEndpoint" not in block
    assert "remaining_events" not in block
    assert "simulation_json" not in block


def test_slice7_revealed_shot_counter_uses_visual_side_only():
    text = Path("app/static/app.js").read_text()
    start = text.index("function updateLivePresentation(item)")
    end = text.index("function addEventImmediate(", start)
    block = text[start:end]
    assert '["goal", "save", "miss"].includes(visualKind)' in block
    assert 'visual.side === "home"' in block
    assert 'visual.side === "away"' in block


def test_slice7_audio_preference_and_event_audio_are_wired_in_bootstrap():
    text = Path("app/static/match/bootstrap.js").read_text()
    assert 'from "./audio.js"' in text
    assert "createAudioController" in text
    assert 'localStorage.getItem("footy-match-audio")' in text
    assert "localStorage.setItem(" in text
    assert '"footy-match-audio"' in text
    assert 'enabled ? "1" : "0"' in text
    assert "audio.setEnabled(enabled)" in text
    assert 'audio.play("goal")' in text
    assert 'audio.play("kick")' in text
    assert 'audio.play("whistle")' in text


def test_slice7_match_engine_exposes_presentation_ball_state_not_hidden_events():
    text = Path("app/static/match/match-engine.js").read_text()
    start = text.index("onStatus({")
    end = text.index("});", start)
    block = text[start:end]
    assert "ball: state.ball" in block
    assert "visualMinute" in block
    assert "events" not in block
    assert "report" not in block


def test_slice7_pressure_and_territory_are_labelled_presentation_data():
    text = Path("app/static/match/bootstrap.js").read_text()
    assert "function updatePresentationIndicators(status)" in text
    assert "matchPressure" in text
    assert "matchTerritory" in text
    assert '"HOME HALF"' in text
    assert '"CENTRAL"' in text
    assert '"AWAY HALF"' in text


def test_slice7_reduced_motion_keeps_camera_shake_disabled_and_event_motion_optional():
    camera = Path("app/static/match/camera.js").read_text()
    css = Path("app/static/match/match.css").read_text()
    assert "!reducedMotion" in camera
    assert 'state.emphasis === "GOAL"' in camera
    assert "@media (prefers-reduced-motion: reduce)" in css
    assert ".live-player-focus.is-live-event" in css
    reduced = css.split("@media (prefers-reduced-motion: reduce)", 1)[1]
    assert "animation: none" in reduced or "animation:none" in reduced
