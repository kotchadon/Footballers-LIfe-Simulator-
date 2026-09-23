from __future__ import annotations

from app.progression import (
    ATTRIBUTES,
    apply_attribute_xp,
    match_development_xp,
    training_development_xp,
)


POSITION = "CAM"
AGE = 22
STARTING_OVERALL = 58
POTENTIAL = 88
FOCUS_ROTATION = (
    "passing",
    "dribbling",
    "shooting",
    "pace",
    "physical",
    "recovery",
)


def _blank_metrics():
    return {
        "shots": 0,
        "shots_on_target": 0,
        "shot_accuracy": 0,
        "xg": 0,
        "key_passes": 0,
        "big_chances_created": 0,
        "xa": 0,
        "passes_attempted": 0,
        "passes_completed": 0,
        "pass_accuracy": 0,
        "dribbles_attempted": 0,
        "dribbles_completed": 0,
        "dribble_success": 0,
        "tackles_attempted": 0,
        "tackles_won": 0,
        "tackle_success": 0,
        "duels": 0,
        "duels_won": 0,
        "duel_win_rate": 0,
        "touches": 0,
        "turnovers": 0,
        "fouls_committed": 0,
        "progressive_actions": 0,
    }


def _performance(profile: str, index: int) -> dict:
    metrics = _blank_metrics()

    if profile == "mixed":
        goals = 1 if index % 13 == 0 else 0
        assists = 1 if index % 9 == 0 else 0
        minutes = 52
        rating = 6.7 + (0.4 if goals or assists else 0)
        metrics.update(
            {
                "passes_attempted": 25,
                "passes_completed": 20,
                "pass_accuracy": 80,
                "key_passes": 1,
                "shots": 1,
                "shots_on_target": 1 if index % 3 == 0 else 0,
                "shot_accuracy": 100 if index % 3 == 0 else 0,
                "dribbles_attempted": 2,
                "dribbles_completed": 1,
                "dribble_success": 50,
                "tackles_attempted": 1,
                "tackles_won": 1 if index % 2 == 0 else 0,
                "tackle_success": 100 if index % 2 == 0 else 0,
                "duels": 5,
                "duels_won": 2,
                "progressive_actions": 3,
            }
        )
    elif profile == "strong":
        goals = 1 if index % 5 == 0 else 0
        assists = 1 if index % 4 == 0 else 0
        minutes = 78
        rating = 7.6 + (0.3 if goals or assists else 0)
        metrics.update(
            {
                "passes_attempted": 34,
                "passes_completed": 29,
                "pass_accuracy": 85.3,
                "key_passes": 1,
                "shots": 2,
                "shots_on_target": 1,
                "shot_accuracy": 50,
                "dribbles_attempted": 4,
                "dribbles_completed": 2,
                "dribble_success": 50,
                "tackles_attempted": 2,
                "tackles_won": 1,
                "tackle_success": 50,
                "duels": 7,
                "duels_won": 3,
                "progressive_actions": 4,
            }
        )
    elif profile == "exceptional":
        goals = 1 if index % 2 == 0 else 0
        assists = 1 if index % 2 == 1 or index % 5 == 0 else 0
        minutes = 85
        rating = 8.7
        metrics.update(
            {
                "passes_attempted": 45,
                "passes_completed": 40,
                "pass_accuracy": 88.9,
                "key_passes": 3,
                "shots": 4,
                "shots_on_target": 3,
                "shot_accuracy": 75,
                "dribbles_attempted": 6,
                "dribbles_completed": 4,
                "dribble_success": 66.7,
                "tackles_attempted": 3,
                "tackles_won": 2,
                "tackle_success": 66.7,
                "duels": 10,
                "duels_won": 6,
                "progressive_actions": 8,
            }
        )
    else:
        raise ValueError(profile)

    return {
        "minutes": minutes,
        "rating": rating,
        "goals": goals,
        "assists": assists,
        "injured": False,
        "injury_weeks": 0,
        "yellow_cards": 0,
        "red_cards": 0,
        "motm": False,
        "metrics": metrics,
        "events": [],
        "commentary": "",
    }


def _appearance_weeks(count: int) -> set[int]:
    if count <= 0:
        return set()
    competitive = list(range(6, 53))
    if count == 1:
        return {competitive[len(competitive) // 2]}
    indexes = [
        round(index * (len(competitive) - 1) / (count - 1))
        for index in range(count)
    ]
    weeks = {competitive[index] for index in indexes}
    assert len(weeks) == count
    return weeks


def _simulate_season(*, appearances: int, profile: str | None) -> dict:
    attributes = dict.fromkeys(ATTRIBUTES, STARTING_OVERALL)
    meters = dict.fromkeys(ATTRIBUTES, 0)
    appearance_weeks = _appearance_weeks(appearances)
    appearance_index = 0
    training_total = 0
    match_total = 0
    match_awards = []

    for week in range(1, 53):
        phase = "preseason" if week <= 5 else "competitive"
        focus = FOCUS_ROTATION[(week - 1) % len(FOCUS_ROTATION)]

        if week in appearance_weeks:
            performance = _performance(profile, appearance_index)
            appearance_index += 1
            minutes = performance["minutes"]
            match_xp = match_development_xp(performance)
            match_awards.append(sum(match_xp.values()))
        else:
            minutes = 0
            match_xp = dict.fromkeys(ATTRIBUTES, 0)

        training_xp = training_development_xp(
            focus=focus,
            position=POSITION,
            season_phase=phase,
            minutes=minutes,
            unavailable_injured=False,
        )
        gains = {
            name: training_xp[name] + match_xp[name]
            for name in ATTRIBUTES
        }
        result = apply_attribute_xp(
            attributes=attributes,
            meters=meters,
            gains=gains,
            position=POSITION,
            potential=POTENTIAL,
        )
        attributes = result["attributes"]
        meters = result["meters"]
        training_total += sum(training_xp.values())
        match_total += sum(match_xp.values())

    assert appearance_index == appearances
    return {
        "age": AGE,
        "overall": result["overall"],
        "attributes": attributes,
        "meters": meters,
        "training_xp": training_total,
        "match_xp": match_total,
        "match_awards": match_awards,
    }


def test_task8_training_only_hits_approved_61_to_62_target():
    result = _simulate_season(appearances=0, profile=None)
    assert 61 <= result["overall"] <= 62
    assert result["match_xp"] == 0
    assert result["overall"] <= POTENTIAL


def test_task8_mixed_season_hits_approved_63_to_65_target():
    result = _simulate_season(appearances=25, profile="mixed")
    assert 63 <= result["overall"] <= 65
    assert result["overall"] <= POTENTIAL


def test_task8_strong_starter_hits_approved_65_to_68_target():
    result = _simulate_season(appearances=32, profile="strong")
    assert 65 <= result["overall"] <= 68
    assert result["overall"] <= POTENTIAL


def test_task8_exceptional_season_stays_at_or_below_69():
    result = _simulate_season(appearances=36, profile="exceptional")
    assert result["overall"] <= 69
    assert result["overall"] <= POTENTIAL


def test_task8_more_performance_produces_monotonic_season_outcomes():
    training = _simulate_season(appearances=0, profile=None)
    mixed = _simulate_season(appearances=25, profile="mixed")
    strong = _simulate_season(appearances=32, profile="strong")
    exceptional = _simulate_season(appearances=36, profile="exceptional")
    assert training["overall"] < mixed["overall"] < strong["overall"] <= exceptional["overall"]


def test_task8_fixture_profiles_match_intended_match_xp_bands():
    mixed = _simulate_season(appearances=25, profile="mixed")
    strong = _simulate_season(appearances=32, profile="strong")
    exceptional = _simulate_season(appearances=36, profile="exceptional")

    mixed_average = mixed["match_xp"] / 25
    strong_average = strong["match_xp"] / 32
    exceptional_average = exceptional["match_xp"] / 36

    assert 25 <= mixed_average <= 40
    assert 45 <= strong_average <= 65
    assert 65 <= exceptional_average <= 75
    assert max(exceptional["match_awards"]) <= 75


def test_task8_season_simulation_is_fully_deterministic():
    for appearances, profile in (
        (0, None),
        (25, "mixed"),
        (32, "strong"),
        (36, "exceptional"),
    ):
        first = _simulate_season(appearances=appearances, profile=profile)
        second = _simulate_season(appearances=appearances, profile=profile)
        assert second == first
