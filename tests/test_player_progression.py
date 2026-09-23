from pathlib import Path

import pytest

from app import create_app
from app.db import get_db, migrate_existing_save
from app.services import create_career, get_active_career


ATTRIBUTE_NAMES = (
    "pace",
    "shooting",
    "passing",
    "dribbling",
    "defending",
    "physical",
)


def make_app(tmp_path: Path):
    database = tmp_path / "progression.sqlite3"
    return create_app(
        {
            "TESTING": True,
            "DATABASE": str(database),
            "SECRET_KEY": "test",
        }
    )


def _reset_legacy_state(db, career_id: int, *, xp: int, focus: str):
    db.execute(
        "UPDATE careers SET xp=?, training_focus=? WHERE id=?",
        (xp, focus, career_id),
    )
    db.execute(
        """
        UPDATE player_attributes
        SET pace_xp=0, shooting_xp=0, passing_xp=0,
            dribbling_xp=0, defending_xp=0, physical_xp=0,
            legacy_xp_migrated=0
        WHERE career_id=?
        """,
        (career_id,),
    )
    db.commit()


def _attribute_row(db, career_id: int):
    return db.execute(
        """
        SELECT pace_xp, shooting_xp, passing_xp,
               dribbling_xp, defending_xp, physical_xp,
               legacy_xp_migrated
        FROM player_attributes
        WHERE career_id=?
        """,
        (career_id,),
    ).fetchone()


def test_attribute_xp_schema_and_active_career_expose_six_zero_meters(tmp_path: Path):
    app = make_app(tmp_path)
    with app.app_context():
        career_id = create_career("Advay", "India", "CAM")
        row = _attribute_row(get_db(), career_id)
        assert row is not None
        assert row["legacy_xp_migrated"] == 1
        assert all(row[f"{name}_xp"] == 0 for name in ATTRIBUTE_NAMES)

        career = get_active_career()
        assert all(career[f"{name}_xp"] == 0 for name in ATTRIBUTE_NAMES)


def test_migration_moves_legacy_xp_to_selected_attribute_once(tmp_path: Path):
    app = make_app(tmp_path)
    with app.app_context():
        career_id = create_career("Advay", "India", "CAM")
        db = get_db()
        _reset_legacy_state(db, career_id, xp=47, focus="passing")

        migrate_existing_save(db)

        row = _attribute_row(db, career_id)
        career = db.execute(
            "SELECT xp FROM careers WHERE id=?",
            (career_id,),
        ).fetchone()
        assert row["passing_xp"] == 47
        assert sum(row[f"{name}_xp"] for name in ATTRIBUTE_NAMES) == 47
        assert row["legacy_xp_migrated"] == 1
        assert career["xp"] == 0

        migrate_existing_save(db)

        row_again = _attribute_row(db, career_id)
        career_again = db.execute(
            "SELECT xp FROM careers WHERE id=?",
            (career_id,),
        ).fetchone()
        assert dict(row_again) == dict(row)
        assert career_again["xp"] == 0


@pytest.mark.parametrize("focus", ["balanced", "recovery"])
def test_migration_fallback_uses_highest_position_weight_once(
    tmp_path: Path,
    focus: str,
):
    app = make_app(tmp_path)
    with app.app_context():
        career_id = create_career("Advay", "India", "ST")
        db = get_db()
        _reset_legacy_state(db, career_id, xp=33, focus=focus)

        migrate_existing_save(db)

        row = _attribute_row(db, career_id)
        assert row["shooting_xp"] == 33
        assert sum(row[f"{name}_xp"] for name in ATTRIBUTE_NAMES) == 33
        assert row["legacy_xp_migrated"] == 1


from app.progression import ATTRIBUTES, apply_attribute_xp, largest_remainder_scale, upgrade_cost


def test_upgrade_cost_uses_attribute_band_and_potential_gap():
    assert upgrade_cost(55, 58, 88) == 48
    assert upgrade_cost(65, 65, 88) == 68
    assert upgrade_cost(75, 75, 88) == 105
    assert upgrade_cost(82, 82, 88) == 174
    assert upgrade_cost(86, 86, 88) == 300


def test_largest_remainder_preserves_exact_integer_total_at_cap():
    scaled = largest_remainder_scale(
        {"passing": 30.4, "shooting": 20.2, "dribbling": 15.1, "physical": 9.3},
        75,
    )
    assert scaled == {"passing": 31, "shooting": 20, "dribbling": 15, "physical": 9}
    assert sum(scaled.values()) == 75


def test_largest_remainder_does_not_pad_values_below_cap():
    scaled = largest_remainder_scale({"passing": 10.2, "shooting": 5.2}, 75)
    assert scaled == {"passing": 10, "shooting": 5}
    assert sum(scaled.values()) == 15


def test_largest_remainder_caps_large_values_deterministically():
    scaled = largest_remainder_scale(
        {"pace": 20.0, "shooting": 30.0, "passing": 25.0, "dribbling": 20.0, "defending": 5.0, "physical": 10.0},
        75,
    )
    assert sum(scaled.values()) == 75
    assert all(value >= 0 for value in scaled.values())


def _attrs(value=50):
    return {name: value for name in ATTRIBUTES}


def _meters(value=0):
    return {name: value for name in ATTRIBUTES}


def test_attribute_xp_crosses_exact_threshold_and_carries_remainder():
    attributes = _attrs(58)
    attributes["passing"] = 59
    result = apply_attribute_xp(
        attributes=attributes,
        meters=_meters(),
        gains={"passing": 58},
        position="CAM",
        potential=88,
    )
    assert result["attributes"]["passing"] == 60
    assert result["meters"]["passing"] == 10
    assert result["upgrades"] == [{"attribute": "passing", "from": 59, "to": 60}]


def test_attribute_xp_can_cross_multiple_thresholds_with_changing_cost():
    result = apply_attribute_xp(
        attributes=_attrs(50),
        meters=_meters(),
        gains={"shooting": 200},
        position="ST",
        potential=88,
    )
    assert result["attributes"]["shooting"] == 54
    assert result["meters"]["shooting"] == 8
    assert len(result["upgrades"]) == 4


def test_attribute_xp_keeps_unspent_meter_when_already_at_potential():
    result = apply_attribute_xp(
        attributes=_attrs(88),
        meters=_meters(),
        gains={"shooting": 500},
        position="ST",
        potential=88,
    )
    assert result["overall"] == 88
    assert result["attributes"]["shooting"] == 88
    assert result["meters"]["shooting"] == 500
    assert result["upgrades"] == []


def test_attribute_xp_stops_conversion_as_soon_as_overall_hits_potential():
    result = apply_attribute_xp(
        attributes=_attrs(87),
        meters=_meters(),
        gains={"shooting": 2000},
        position="ST",
        potential=88,
    )
    assert result["overall"] == 88
    assert result["attributes"]["shooting"] < 99
    assert result["meters"]["shooting"] > 0


def test_attribute_xp_never_accepts_negative_gain():
    result = apply_attribute_xp(
        attributes=_attrs(50),
        meters=_meters(7),
        gains={"passing": -500},
        position="CM",
        potential=88,
    )
    assert result["attributes"]["passing"] == 50
    assert result["meters"]["passing"] == 7


# Task 3: performance-led match development.
from copy import deepcopy


def _task3_performance(*, minutes=9, rating=7.0, goals=0, assists=0, injured=False, **metrics):
    values = dict.fromkeys((
        "shots", "shots_on_target", "shot_accuracy", "xg", "key_passes",
        "big_chances_created", "xa", "passes_attempted", "passes_completed",
        "pass_accuracy", "dribbles_attempted", "dribbles_completed",
        "dribble_success", "tackles_attempted", "tackles_won", "tackle_success",
        "duels", "duels_won", "duel_win_rate", "touches", "turnovers",
        "fouls_committed", "progressive_actions",
    ), 0)
    values.update(metrics)
    values["schema_version"] = 1
    return {
        "minutes": minutes, "rating": rating, "goals": goals, "assists": assists,
        "injured": injured, "injury_weeks": int(injured), "yellow_cards": 0,
        "red_cards": 0, "motm": False, "metrics": values,
        "events": [], "commentary": "",
    }


def _task3_award(performance):
    from app import progression
    function = getattr(progression, "match_development_xp", None)
    assert callable(function), "Task 3 missing: match_development_xp"
    return function(performance)


@pytest.mark.parametrize("metrics,assists,want", [
    ({"passes_completed": 15, "passes_attempted": 20, "pass_accuracy": 75, "key_passes": 2}, 1, 17),
    ({"passes_completed": 17, "passes_attempted": 20, "pass_accuracy": 85}, 0, 8),
    ({"passes_completed": 17, "passes_attempted": 20, "pass_accuracy": 84.9}, 0, 3),
    ({"passes_completed": 18, "passes_attempted": 19, "pass_accuracy": 94.7}, 0, 4),
    ({"passes_completed": 23, "passes_attempted": 25, "pass_accuracy": 92}, 0, 13),
    ({"passes_completed": 23, "passes_attempted": 25, "pass_accuracy": 91.9}, 0, 10),
    ({"passes_completed": 90, "passes_attempted": 95, "pass_accuracy": 94.7, "key_passes": 10}, 4, 28),
])
def test_task3_match_passing_actions_bonuses_and_cap(metrics, assists, want):
    result = _task3_award(_task3_performance(assists=assists, **metrics))
    assert result == {"pace": 0, "shooting": 0, "passing": want, "dribbling": 0, "defending": 0, "physical": 0}


@pytest.mark.parametrize("shots,on_target,accuracy,goals,want", [
    (3, 1, 33.3, 1, 15), (2, 1, 50, 0, 7), (2, 1, 49.9, 0, 4),
    (1, 1, 100, 0, 3), (9, 9, 100, 5, 24),
])
def test_task3_match_shooting_actions_bonuses_and_cap(shots, on_target, accuracy, goals, want):
    result = _task3_award(_task3_performance(goals=goals, shots=shots, shots_on_target=on_target, shot_accuracy=accuracy))
    assert result == {"pace": 0, "shooting": want, "passing": 0, "dribbling": 0, "defending": 0, "physical": 0}


@pytest.mark.parametrize("attempts,completed,success,progressive,want", [
    (5, 3, 60, 0, 12), (5, 3, 59.9, 0, 8), (2, 2, 100, 0, 5),
    (0, 0, 0, 10, 4), (9, 9, 100, 18, 20),
])
def test_task3_match_dribbling_bonus_progressive_actions_and_cap(attempts, completed, success, progressive, want):
    result = _task3_award(_task3_performance(dribbles_attempted=attempts, dribbles_completed=completed, dribble_success=success, progressive_actions=progressive))
    assert result["dribbling"] == want


@pytest.mark.parametrize("attempts,won,success,duels,want", [
    (10, 7, 70, 0, 22), (3, 2, 70, 1, 11), (3, 2, 69.9, 1, 7),
    (1, 1, 100, 0, 3), (0, 0, 0, 5, 5), (10, 10, 100, 15, 22),
])
def test_task3_match_defending_actions_bonus_and_cap(attempts, won, success, duels, want):
    result = _task3_award(_task3_performance(tackles_attempted=attempts, tackles_won=won, tackle_success=success, duels_won=duels, duels=duels))
    assert result["defending"] == want


@pytest.mark.parametrize("minutes,duels,want", [(9, 0, 0), (10, 0, 1), (59, 0, 5), (89, 0, 8), (90, 0, 11), (30, 5, 6), (90, 15, 15)])
def test_task3_match_physical_minutes_duels_and_cap(minutes, duels, want):
    result = _task3_award(_task3_performance(minutes=minutes, duels_won=duels, duels=duels))
    assert result["physical"] == want


@pytest.mark.parametrize("minutes,progressive,dribbles,want", [(59, 0, 0, 0), (60, 0, 0, 2), (9, 4, 2, 5), (90, 18, 9, 12)])
def test_task3_match_pace_actions_minutes_and_cap(minutes, progressive, dribbles, want):
    result = _task3_award(_task3_performance(minutes=minutes, progressive_actions=progressive, dribbles_attempted=dribbles, dribbles_completed=dribbles))
    assert result["pace"] == want


@pytest.mark.parametrize("rating,multiplier,want", [(3.5, .9, 9), (6.49, .9, 9), (6.5, 1., 10), (7.49, 1., 10), (7.5, 1.1, 11), (8.49, 1.1, 11), (8.5, 1.2, 12), (10., 1.2, 12)])
def test_task3_rating_boundaries_amplify_only_earned_xp(rating, multiplier, want):
    from app import progression
    function = getattr(progression, "rating_multiplier", None)
    assert callable(function), "Task 3 missing: rating_multiplier"
    assert function(rating) == multiplier
    result = _task3_award(_task3_performance(rating=rating, passes_attempted=50, passes_completed=50, pass_accuracy=0))
    assert result == {"pace": 0, "shooting": 0, "passing": want, "dribbling": 0, "defending": 0, "physical": 0}


def test_task3_caps_each_category_before_rating_then_scales_to_75():
    performance = _task3_performance(minutes=90, rating=9, goals=5, assists=5,
        shots=9, shots_on_target=9, shot_accuracy=100,
        passes_attempted=95, passes_completed=95, pass_accuracy=100, key_passes=10,
        dribbles_attempted=9, dribbles_completed=9, dribble_success=100,
        tackles_attempted=10, tackles_won=10, tackle_success=100,
        duels=15, duels_won=15, progressive_actions=18)
    # Spec: cap, multiply, round each category, then scale (14,29,34,24,26,18).
    want = {"pace": 7, "shooting": 15, "passing": 18, "dribbling": 12, "defending": 14, "physical": 9}
    assert _task3_award(performance) == want
    assert _task3_award(performance) == want
    assert sum(want.values()) == 75


def test_task3_rounds_each_multiplied_category_before_global_scaling():
    result = _task3_award(_task3_performance(rating=8.5, dribbles_completed=1, dribbles_attempted=1, passes_completed=2))
    assert result == {"pace": 1, "shooting": 0, "passing": 0, "dribbling": 3, "defending": 0, "physical": 0}


@pytest.mark.parametrize("minutes", [0, -1])
def test_task3_no_minutes_means_no_match_xp_even_with_actions(minutes):
    result = _task3_award(_task3_performance(minutes=minutes, rating=10, goals=5, assists=5, passes_completed=80))
    assert result == dict.fromkeys(("pace", "shooting", "passing", "dribbling", "defending", "physical"), 0)


def test_task3_injury_retains_earned_xp_and_input_is_unchanged():
    performance = _task3_performance(minutes=30, goals=1, shots=1, shots_on_target=1, shot_accuracy=100, injured=True)
    before = deepcopy(performance)
    result = _task3_award(performance)
    assert result == {"pace": 0, "shooting": 13, "passing": 0, "dribbling": 0, "defending": 0, "physical": 3}
    assert performance == before


def test_task3_low_rating_and_negative_action_counts_never_remove_xp():
    result = _task3_award(_task3_performance(rating=3.5, goals=-2, assists=-1, passes_completed=-10, shots=-5, shots_on_target=-1, key_passes=-2, dribbles_completed=-1, tackles_won=-1, duels_won=-1, progressive_actions=-1))
    assert result == dict.fromkeys(("pace", "shooting", "passing", "dribbling", "defending", "physical"), 0)


def test_task3_missing_minutes_never_assumes_full_match():
    performance = _task3_performance(goals=1, shots=1)
    del performance["minutes"]
    assert sum(_task3_award(performance).values()) == 0


def test_task3_real_engine_metrics_with_authoritative_minutes():
    import random
    from app.engine import simulate_player_performance
    performance = simulate_player_performance(player_name="Advay", position="CAM", overall=58, fitness=90, morale=70, team_goals=2, opponent_goals=1, minutes=78, rng=random.Random(42))
    performance["minutes"] = 78
    before = deepcopy(performance)
    result = _task3_award(performance)
    assert set(result) == {"pace", "shooting", "passing", "dribbling", "defending", "physical"}
    assert all(type(value) is int and value >= 0 for value in result.values())
    assert 0 < sum(result.values()) <= 75
    assert result["passing"] > 0
    assert result["physical"] > 0
    assert performance == before


# Task 4: weekly attribute training.
def test_task4_training_allocation_resolves_decimal_ties_in_attribute_order():
    from app.progression import largest_remainder_scale
    # 30 * .18 and 30 * .28 have equal mathematical fractional remainders.
    assert largest_remainder_scale({"shooting": 30 * .18, "passing": 30 * .28}, 14) == {"shooting": 6, "passing": 8}


def _task4_training(**overrides):
    from app import progression
    function = getattr(progression, "training_development_xp", None)
    assert callable(function), "Task 4 missing: training_development_xp"
    arguments = dict(focus="passing", position="CAM", season_phase="competitive", minutes=0, unavailable_injured=False)
    arguments.update(overrides)
    return function(**arguments)


@pytest.mark.parametrize("focus,want", [
    ("pace", (20, 0, 0, 5, 0, 5)),
    ("shooting", (0, 20, 0, 5, 0, 5)),
    ("passing", (0, 0, 20, 5, 0, 5)),
    ("dribbling", (5, 0, 5, 20, 0, 0)),
    ("defending", (0, 0, 5, 0, 20, 5)),
    ("physical", (5, 0, 0, 0, 5, 20)),
])
def test_task4_training_focus_has_fixed_support_pair(focus, want):
    assert _task4_training(focus=focus) == dict(zip(ATTRIBUTE_NAMES, want))


@pytest.mark.parametrize("minutes,want", [
    (0, (0, 0, 20, 5, 0, 5)),
    (1, (0, 0, 18, 5, 0, 4)),
    (29, (0, 0, 18, 5, 0, 4)),
    (30, (0, 0, 16, 4, 0, 4)),
    (59, (0, 0, 16, 4, 0, 4)),
    (60, (0, 0, 14, 4, 0, 3)),
    (90, (0, 0, 14, 4, 0, 3)),
])
def test_task4_training_minutes_reduce_load_at_exact_boundaries(minutes, want):
    assert _task4_training(minutes=minutes) == dict(zip(ATTRIBUTE_NAMES, want))


@pytest.mark.parametrize("minutes,total", [(0, 38), (1, 34), (30, 30), (60, 26)])
def test_task4_training_preseason_bonus_preserves_rounded_total(minutes, total):
    result = _task4_training(season_phase="preseason", minutes=minutes)
    assert sum(result.values()) == total
    if minutes == 0:
        assert result == dict(zip(ATTRIBUTE_NAMES, (0, 0, 25, 7, 0, 6)))


@pytest.mark.parametrize("position,want", [
    ("ST", (6, 10, 3, 5, 1, 5)),
    ("CAM", (3, 6, 8, 8, 1, 4)),
    ("CB", (3, 1, 3, 1, 12, 10)),
])
def test_task4_training_balanced_uses_position_weights_deterministically(position, want):
    result = _task4_training(focus="balanced", position=position)
    assert result == dict(zip(ATTRIBUTE_NAMES, want))
    assert _task4_training(focus="balanced", position=position) == result


@pytest.mark.parametrize("minutes,total", [(0, 38), (1, 34), (30, 30), (60, 26)])
def test_task4_training_balanced_preseason_never_loses_rounding_point(minutes, total):
    result = _task4_training(focus="balanced", season_phase="preseason", minutes=minutes)
    assert sum(result.values()) == total
    assert all(type(value) is int and value >= 0 for value in result.values())


@pytest.mark.parametrize("focus,injured", [("recovery", False), ("recovery", True), ("passing", True), ("balanced", True)])
def test_task4_training_recovery_or_injury_awards_zero(focus, injured):
    assert _task4_training(focus=focus, unavailable_injured=injured, season_phase="preseason") == dict.fromkeys(ATTRIBUTE_NAMES, 0)
