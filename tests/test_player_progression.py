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
