from pathlib import Path

from app import create_app
from app.db import get_db
from app.services import (
    advance_calendar_week,
    create_career,
    get_active_career,
    get_calendar_dashboard,
    get_financial_dashboard,
    get_international_summary,
    play_next_week,
    finalize_season,
    get_market_dashboard,
)


def make_app(tmp_path: Path):
    return create_app({"TESTING": True, "DATABASE": str(tmp_path / "v6.sqlite3"), "SECRET_KEY": "test"})


def test_calendar_has_52_weeks_free_windows_and_no_league_collision(tmp_path: Path):
    app = make_app(tmp_path)
    with app.app_context():
        career_id = create_career("Advay", "England", "CM")
        calendar = get_calendar_dashboard(career_id)
        assert len(calendar["weeks"]) == 52
        assert calendar["weeks"][0]["phase"] == "offseason"
        assert calendar["weeks"][3]["phase"] == "preseason"
        collisions = get_db().execute(
            """
            SELECT COUNT(*) AS n FROM fixtures
            WHERE career_id=? AND calendar_week IN (14,15,21,36)
            """,
            (career_id,),
        ).fetchone()["n"]
        assert collisions == 0
        assert get_db().execute(
            "SELECT MIN(calendar_week) AS first, MAX(calendar_week) AS last FROM fixtures WHERE career_id=?",
            (career_id,),
        ).fetchone()["first"] >= 6


def test_weekly_finance_is_idempotent_and_explained(tmp_path: Path):
    app = make_app(tmp_path)
    with app.app_context():
        career_id = create_career("Advay", "India", "CAM")
        career = get_active_career()
        before = career["money"]
        success, message, _data = advance_calendar_week(career_id, seed=1)
        assert success, message
        after = get_active_career()["money"]
        assert after != before
        finance = get_financial_dashboard(career_id)
        categories = {row["category"] for row in finance["transactions"]}
        assert {"Salary", "Agent fee", "Tax reserve", "Living costs"}.issubset(categories)
        assert get_db().execute("SELECT COUNT(*) AS n FROM career_week_finance").fetchone()["n"] == 1


def test_international_window_creates_selection_record(tmp_path: Path):
    app = make_app(tmp_path)
    with app.app_context():
        career_id = create_career("Advay", "India", "RW")
        get_db().execute("UPDATE careers SET calendar_week=14 WHERE id=?", (career_id,))
        get_db().commit()
        success, message, _data = advance_calendar_week(career_id, seed=2)
        assert success, message
        summary = get_international_summary(career_id)
        assert summary["team"]["name"] == "India"
        assert len(summary["recent"]) == 1
        assert summary["recent"][0]["status"] in {"selected", "not_selected", "not_qualified"}


def test_close_season_generates_broad_market(tmp_path: Path):
    app = make_app(tmp_path)
    with app.app_context():
        career_id = create_career("Advay", "India", "ST")
        seed = 1
        while play_next_week(career_id, seed=seed) is not None:
            seed += 1
        ok, message = finalize_season(career_id, seed=443)
        assert ok, message
        market = get_market_dashboard(career_id)
        assert len(market["offers"]) + len(market["watching"]) >= 4
        assert market["window_open"] is True


def test_v6_pages_render(tmp_path: Path):
    app = make_app(tmp_path)
    with app.app_context():
        create_career("Advay", "Spain", "CAM")
    client = app.test_client()
    for path, marker in (("/calendar", "52-WEEK MASTER SCHEDULE"), ("/market", "Transfer market"), ("/finances", "Money without mystery")):
        response = client.get(path)
        assert response.status_code == 200
        assert marker in response.get_data(as_text=True)


# Task 4: persistent free-week progression through the real calendar service.
import pytest


TASK4_ATTRIBUTES = ("pace", "shooting", "passing", "dribbling", "defending", "physical")


def _task4_career(*, week=4, focus="passing", injured=0, passing_xp=0, all_meters=None):
    career_id = create_career("Advay", "India", "CAM")
    db = get_db()
    db.execute("UPDATE careers SET calendar_week=?, season_phase='preseason', training_focus=?, injured_weeks=?, overall=58, potential=88, xp=0, fitness=60, morale=60, stress=20 WHERE id=?", (week, focus, injured, career_id))
    db.execute("UPDATE player_attributes SET pace=58, shooting=58, passing=58, dribbling=58, defending=58, physical=58, pace_xp=0, shooting_xp=0, passing_xp=?, dribbling_xp=0, defending_xp=0, physical_xp=0 WHERE career_id=?", (passing_xp, career_id))
    if all_meters is not None:
        db.execute("UPDATE player_attributes SET pace_xp=?, shooting_xp=?, passing_xp=?, dribbling_xp=?, defending_xp=?, physical_xp=? WHERE career_id=?", (*([all_meters] * 6), career_id))
    db.commit()
    return career_id


def _task4_development_state():
    career = get_active_career()
    return ({name: career[name] for name in TASK4_ATTRIBUTES}, {name: career[f"{name}_xp"] for name in TASK4_ATTRIBUTES}, career["overall"], career["xp"])


def test_task4_free_week_persists_focused_xp_and_preserves_wellbeing(tmp_path):
    app = make_app(tmp_path)
    with app.app_context():
        career_id = _task4_career()
        ok, message, data = advance_calendar_week(career_id, seed=410)
        assert ok, message
        attributes, meters, overall, legacy = _task4_development_state()
        assert meters == dict(zip(TASK4_ATTRIBUTES, (0, 0, 25, 7, 0, 6)))
        assert attributes == dict.fromkeys(TASK4_ATTRIBUTES, 58)
        assert overall == 58 and legacy == 0
        assert data["next_week"] == 5
        career = get_active_career()
        assert (career["fitness"], career["morale"], career["stress"]) == (67, 61, 19)
        assert "38 development XP" in message


def test_task4_free_week_crosses_threshold_and_carries_remainder(tmp_path):
    app = make_app(tmp_path)
    with app.app_context():
        career_id = _task4_career(passing_xp=40)
        ok, message, _ = advance_calendar_week(career_id, seed=411)
        assert ok, message
        attributes, meters, overall, legacy = _task4_development_state()
        assert attributes == dict(zip(TASK4_ATTRIBUTES, (58, 58, 59, 58, 58, 58)))
        assert meters == dict(zip(TASK4_ATTRIBUTES, (0, 0, 17, 7, 0, 6)))
        assert overall == 58 and legacy == 0
        assert "Passing" in message


@pytest.mark.parametrize("focus,injured,want_wellbeing", [("recovery", 0, (72, 62, 17)), ("passing", 2, (67, 61, 19)), ("recovery", 2, (72, 62, 17))])
def test_task4_recovery_and_injury_preserve_banked_xp_without_converting(tmp_path, focus, injured, want_wellbeing):
    app = make_app(tmp_path)
    with app.app_context():
        career_id = _task4_career(focus=focus, injured=injured, all_meters=70)
        before = _task4_development_state()
        ok, message, _ = advance_calendar_week(career_id, seed=412)
        assert ok, message
        assert _task4_development_state() == before
        career = get_active_career()
        assert (career["fitness"], career["morale"], career["stress"]) == want_wellbeing


def test_task4_focus_change_does_not_award_xp_before_week_advances(tmp_path):
    from app.services import set_training_focus
    app = make_app(tmp_path)
    with app.app_context():
        career_id = _task4_career()
        before = _task4_development_state()
        ok, message, _ = set_training_focus(career_id, "shooting")
        assert ok, message
        assert _task4_development_state() == before
        ok, message, _ = advance_calendar_week(career_id, seed=413)
        assert ok, message
        assert _task4_development_state()[1] == dict(zip(TASK4_ATTRIBUTES, (0, 25, 0, 7, 0, 6)))


def test_task4_two_preseason_weeks_award_once_each_then_fixture_blocks(tmp_path):
    app = make_app(tmp_path)
    with app.app_context():
        career_id = _task4_career()
        for week in (4, 5):
            ok, message, data = advance_calendar_week(career_id, seed=414)
            assert ok, message
            assert data["next_week"] == week + 1
        attributes, meters, _, legacy = _task4_development_state()
        assert attributes["passing"] == 59
        assert meters == dict(zip(TASK4_ATTRIBUTES, (0, 0, 2, 14, 0, 12)))
        assert legacy == 0
        before = _task4_development_state()
        money = get_active_career()["money"]
        for _ in range(2):
            ok, message, data = advance_calendar_week(career_id, seed=414)
            assert not ok and data is None
            assert "before advancing" in message
            assert _task4_development_state() == before
            assert get_active_career()["money"] == money
        rows = get_db().execute("SELECT week, status FROM career_calendar_weeks WHERE career_id=? AND season_number=1 AND week IN (4,5) ORDER BY week", (career_id,)).fetchall()
        assert [(row["week"], row["status"]) for row in rows] == [(4, "completed"), (5, "completed")]


def test_task4_active_match_blocks_free_week_training(tmp_path):
    from app.services import prepare_next_match
    app = make_app(tmp_path)
    with app.app_context():
        career_id = _task4_career(week=6)
        session = prepare_next_match(career_id, seed=415)
        assert session is not None
        before = _task4_development_state()
        money = get_active_career()["money"]
        ok, message, _ = advance_calendar_week(career_id, seed=415)
        assert not ok
        assert "active match" in message
        assert _task4_development_state() == before
        assert get_active_career()["money"] == money


def test_task4_late_calendar_failure_rolls_back_xp_and_finance(tmp_path):
    import sqlite3
    app = make_app(tmp_path)
    with app.app_context():
        career_id = _task4_career(passing_xp=40)
        db = get_db()
        before = dict(get_active_career())
        db.execute("CREATE TEMP TRIGGER task4_fail_advance BEFORE UPDATE OF calendar_week ON careers BEGIN SELECT RAISE(ABORT, 'task4 forced rollback'); END")
        db.commit()
        with pytest.raises(sqlite3.IntegrityError, match="task4 forced rollback"):
            advance_calendar_week(career_id, seed=416)
        assert dict(get_active_career()) == before
        assert db.execute("SELECT COUNT(*) FROM career_week_finance WHERE career_id=?", (career_id,)).fetchone()[0] == 0
        db.execute("DROP TRIGGER task4_fail_advance")
        db.commit()
        ok, message, _ = advance_calendar_week(career_id, seed=416)
        assert ok, message
        assert _task4_development_state()[0]["passing"] == 59
        assert _task4_development_state()[1]["passing"] == 17
