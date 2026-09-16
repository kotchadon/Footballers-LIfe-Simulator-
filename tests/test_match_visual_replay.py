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
