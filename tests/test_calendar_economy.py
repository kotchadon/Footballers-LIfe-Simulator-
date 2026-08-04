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
