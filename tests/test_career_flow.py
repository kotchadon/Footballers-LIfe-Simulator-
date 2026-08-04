from pathlib import Path

from app import create_app
from app.db import get_db
from app.services import (
    advance_calendar_week,
    create_career,
    finalize_season,
    get_active_career,
    play_next_week,
    set_training_focus,
    start_next_season,
)


def make_app(tmp_path: Path):
    database = tmp_path / "test.sqlite3"
    return create_app({"TESTING": True, "DATABASE": str(database), "SECRET_KEY": "test"})


def test_training_plan_changes_without_instant_stat_or_fitness_gain(tmp_path: Path):
    app = make_app(tmp_path)
    with app.app_context():
        career_id = create_career("Advay", "India", "ST")
        before = get_active_career()
        attributes_before = tuple(before[name] for name in ("pace", "shooting", "passing", "dribbling", "defending", "physical"))

        success, _message, plan = set_training_focus(career_id, "shooting")
        assert success
        assert plan["focus"] == "shooting"

        after = get_active_career()
        attributes_after = tuple(after[name] for name in ("pace", "shooting", "passing", "dribbling", "defending", "physical"))
        assert attributes_after == attributes_before
        assert after["fitness"] == before["fitness"]
        assert after["training_focus"] == "shooting"


def test_matchweek_creates_replay_events_and_automatic_development(tmp_path: Path):
    app = make_app(tmp_path)
    with app.app_context():
        career_id = create_career("Advay", "India", "CAM")
        set_training_focus(career_id, "passing")
        report = play_next_week(career_id, seed=13)

        assert report is not None
        assert len(report["events"]) >= 9
        assert report["events"][0]["minute"] == 0
        assert report["events"][-1]["minute"] == 90
        assert report["fitness_after"] >= 45
        assert "Progress:" in report["development_summary"] or "breakthrough" in report["development_summary"]

        career = get_active_career()
        assert career["current_week"] == 2
        assert 0 <= career["xp"] < 100


def test_training_plan_api_returns_json_without_page_reload(tmp_path: Path):
    app = make_app(tmp_path)
    with app.app_context():
        create_career("Advay", "India", "ST")

    client = app.test_client()
    response = client.post("/api/training-plan", json={"focus": "pace"})
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    assert payload["plan"]["focus"] == "pace"


def test_complete_season_and_rollover(tmp_path: Path):
    app = make_app(tmp_path)

    with app.app_context():
        career_id = create_career("Advay", "India", "ST")
        career = get_active_career()
        assert career["season_number"] == 1

        max_week = get_db().execute(
            "SELECT MAX(week) AS max_week FROM fixtures WHERE career_id=? AND season_number=1",
            (career_id,),
        ).fetchone()["max_week"]
        seed = 1
        while True:
            report = play_next_week(career_id, seed=seed)
            if report is None:
                break
            seed += 1

        career = get_active_career()
        assert career["current_week"] == max_week + 1
        success, _message = finalize_season(career_id, seed=7)
        assert success

        career = get_active_career()
        assert career["season_number"] == 1
        assert career["season_phase"] == "offseason"
        assert career["age"] == 16

        while get_active_career()["calendar_week"] <= 52:
            success, message, _data = advance_calendar_week(career_id, seed=99)
            assert success, message
        success, message = start_next_season(career_id)
        assert success, message
        career = get_active_career()
        assert career["season_number"] == 2
        assert career["age"] == 17
        assert career["current_week"] == 1
        assert career["calendar_week"] == 1

        history_count = get_db().execute(
            "SELECT COUNT(*) AS total FROM season_history WHERE career_id = ?", (career_id,)
        ).fetchone()["total"]
        assert history_count == 1
