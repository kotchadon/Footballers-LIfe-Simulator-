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
