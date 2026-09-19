import app.match_visuals as match_visuals


def _snapshot():
    return {
        "schema_version": 1,
        "seed": 918273,
        "career": {
            "id": 1,
            "player_name": "Advay Katoch",
            "position": "LW",
            "fitness": 82,
            "pace": 74,
            "shooting": 64,
            "passing": 68,
            "dribbling": 71,
            "defending": 41,
            "physical": 62,
        },
        "fixture": {
            "fixture_id": 101,
            "home_club_id": 10,
            "away_club_id": 11,
            "home_name": "Home FC",
            "away_name": "Away FC",
            "home_strength": 72,
            "away_strength": 69,
            "player_team_is_home": True,
        },
        "performance": {
            "selection_status": "starter",
            "events": [],
        },
    }


def test_visual_schema_version_is_stable():
    assert match_visuals.VISUAL_SCHEMA_VERSION == 1


def test_normalize_match_actor_accepts_tactical_and_future_persistent_players():
    tactical = match_visuals.normalize_match_actor({
        "actor_id": "home_st",
        "display_name": "R. Costa",
        "shirt_number": 9,
        "role": "ST",
        "team": "home",
    })
    persistent = match_visuals.normalize_match_actor({
        "actor_id": "player:48172",
        "persistent_player_id": 48172,
        "display_name": "Rafael Costa",
        "shirt_number": 9,
        "role": "ST",
        "team": "home",
        "attributes": {"pace": 81, "stamina": 76},
    })

    assert tactical["actor_id"] == "home_st"
    assert tactical["attributes"] == {}
    assert persistent["persistent_player_id"] == 48172
    assert persistent["attributes"]["pace"] == 81
    assert set(tactical) == set(persistent)


def test_visual_seed_is_deterministic_and_part_sensitive():
    assert match_visuals.visual_seed(1234, "phase", 7) == match_visuals.visual_seed(1234, "phase", 7)
    assert match_visuals.visual_seed(1234, "phase", 7) != match_visuals.visual_seed(1234, "phase", 8)


def test_build_visual_plan_has_22_actors_and_no_authoritative_result_fields():
    plan = match_visuals.build_visual_plan(_snapshot(), seed=918273)

    assert plan["schema_version"] == 1
    assert len(plan["actors"]) == 22
    assert {actor["team"] for actor in plan["actors"]} == {"home", "away"}
    actor_ids = {actor["actor_id"] for actor in plan["actors"]}
    assert plan["user_actor_id"] in actor_ids
    assert "final_score" not in plan
    assert "report" not in plan


def test_visual_plan_is_deterministic_for_same_seed():
    assert match_visuals.build_visual_plan(_snapshot(), seed=918273) == match_visuals.build_visual_plan(_snapshot(), seed=918273)


def test_visual_plan_user_actor_uses_career_attributes():
    plan = match_visuals.build_visual_plan(_snapshot(), seed=918273)
    user = next(actor for actor in plan["actors"] if actor["actor_id"] == plan["user_actor_id"])

    assert user["display_name"] == "Advay Katoch"
    assert user["role"] == "LW"
    assert user["attributes"]["pace"] == 74
    assert user["attributes"]["dribbling"] == 71



def test_starter_user_actor_is_present_across_many_visual_seeds():
    snapshot = _snapshot()
    for seed in range(1, 40):
        plan = match_visuals.build_visual_plan(snapshot, seed=seed)
        actor_ids = {actor["actor_id"] for actor in plan["actors"]}
        assert plan["user_actor_id"] == "career_player"
        assert "career_player" in actor_ids

def test_visual_event_metadata_maps_real_ledger_goal_sides():
    snapshot = _snapshot()

    goal_for = {
        "sequence": 0,
        "minute": 12,
        "kind": "goal_for",
        "text": "GOAL!",
        "metadata": {
            "side": "player",
            "contribution": "goal",
        },
    }

    visual = match_visuals.visual_event_metadata(
        snapshot,
        goal_for,
        0,
        seed=918273,
    )

    assert visual["sequence"] == 0
    assert visual["source_kind"] == "goal_for"
    assert visual["kind"] == "goal"
    assert visual["side"] == "home"
    assert visual["actor_id"] == "career_player"
    assert visual["keeper_outcome"] == "concede"

    against = {
        "sequence": 1,
        "minute": 44,
        "kind": "goal_against",
        "text": "Goal against.",
        "metadata": {"side": "opponent"},
    }

    visual_against = match_visuals.visual_event_metadata(
        snapshot,
        against,
        1,
        seed=918273,
    )

    assert visual_against["kind"] == "goal"
    assert visual_against["side"] == "away"


def test_visual_event_metadata_maps_real_saved_and_missed_shots():
    snapshot = _snapshot()

    saved = match_visuals.visual_event_metadata(
        snapshot,
        {
            "sequence": 3,
            "minute": 67,
            "kind": "player_shot_saved",
            "metadata": {"side": "player"},
        },
        3,
        seed=918273,
    )

    missed = match_visuals.visual_event_metadata(
        snapshot,
        {
            "sequence": 4,
            "minute": 71,
            "kind": "player_shot_off_target",
            "metadata": {"side": "player"},
        },
        4,
        seed=918273,
    )

    assert saved["kind"] == "save"
    assert saved["side"] == "home"
    assert saved["keeper_outcome"] == "save"
    assert saved["actor_id"] == "career_player"

    assert missed["kind"] == "miss"
    assert missed["keeper_outcome"] == "miss"


def test_visual_event_side_mapping_respects_away_career_team():
    snapshot = _snapshot()
    snapshot["fixture"]["player_team_is_home"] = False

    visual = match_visuals.visual_event_metadata(
        snapshot,
        {
            "sequence": 0,
            "minute": 20,
            "kind": "goal_for",
            "metadata": {
                "side": "player",
                "contribution": "team",
            },
        },
        0,
        seed=55,
    )

    assert visual["side"] == "away"
    assert visual["actor_id"] is None


def test_visual_metadata_is_deterministic_and_result_neutral():
    snapshot = _snapshot()

    event = {
        "sequence": 2,
        "minute": 50,
        "kind": "goal_for",
        "metadata": {
            "side": "player",
            "contribution": "team",
        },
    }

    one = match_visuals.visual_event_metadata(
        snapshot,
        event,
        2,
        seed=123,
    )

    two = match_visuals.visual_event_metadata(
        snapshot,
        event,
        2,
        seed=123,
    )

    assert one == two
    assert "final_score" not in one
    assert "report" not in one
    assert "result" not in one
