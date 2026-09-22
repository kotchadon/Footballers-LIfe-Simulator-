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
