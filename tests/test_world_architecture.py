from pathlib import Path

from app import create_app
from app.db import get_db
from app.services import (
    create_career,
    get_active_career,
    get_world_league,
    get_world_overview,
    play_next_week,
    finalize_season,
)


def make_app(tmp_path: Path):
    tmp_path.mkdir(parents=True, exist_ok=True)
    return create_app({"TESTING": True, "DATABASE": str(tmp_path / "world.sqlite3"), "SECRET_KEY": "test"})


def test_world_seed_is_idempotent_and_substantial(tmp_path: Path):
    app = make_app(tmp_path)
    with app.app_context():
        db = get_db()
        counts = {
            "countries": db.execute("SELECT COUNT(*) AS n FROM countries WHERE code <> 'LGC'").fetchone()["n"],
            "leagues": db.execute("SELECT COUNT(*) AS n FROM leagues WHERE code <> 'LGC1'").fetchone()["n"],
            "clubs": db.execute("SELECT COUNT(*) AS n FROM clubs WHERE is_real=1").fetchone()["n"],
            "competitions": db.execute("SELECT COUNT(*) AS n FROM competitions").fetchone()["n"],
        }
        assert counts["countries"] >= 15
        assert counts["leagues"] >= 20
        assert counts["clubs"] >= 300
        assert counts["competitions"] >= 38
        assert db.execute("SELECT COUNT(*) AS n FROM clubs WHERE name IN ('Manchester United','Real Madrid','FC Bayern München','Paris Saint-Germain','Inter')").fetchone()["n"] == 5
        assert db.execute("SELECT COUNT(*) AS n FROM competitions WHERE code IN ('UCL','UEL','WC','EURO','COPA','ASIAN','FACUP','COPAREY')").fetchone()["n"] == 8
        before = counts.copy()
        from app.world import seed_world_database
        seed_world_database(db)
        assert db.execute("SELECT COUNT(*) AS n FROM clubs WHERE is_real=1").fetchone()["n"] == before["clubs"]
        assert db.execute("SELECT COUNT(*) AS n FROM competitions").fetchone()["n"] == before["competitions"]


def test_top_five_have_two_real_divisions(tmp_path: Path):
    app = make_app(tmp_path)
    with app.app_context():
        rows = get_db().execute(
            """
            SELECT co.code, COUNT(*) AS divisions
            FROM leagues l JOIN countries co ON co.id=l.country_id
            WHERE co.code IN ('ENG','ESP','ITA','GER','FRA')
            GROUP BY co.code
            """
        ).fetchall()
        assert {row["code"]: row["divisions"] for row in rows} == {
            "ENG": 2, "ESP": 2, "ITA": 2, "GER": 2, "FRA": 2
        }


def test_nationality_drives_realistic_starting_market(tmp_path: Path):
    app = make_app(tmp_path)
    with app.app_context():
        create_career("English Prospect", "England", "ST")
        english = get_active_career()
        assert english["country_code"] == "ENG"
        assert english["league_tier"] == 2

    app2 = make_app(tmp_path / "india")
    with app2.app_context():
        create_career("Indian Prospect", "India", "CAM")
        indian = get_active_career()
        assert indian["country_code"] == "IND"
        assert indian["league_code"] == "IND1"


def test_active_league_generates_full_double_round_robin(tmp_path: Path):
    app = make_app(tmp_path)
    with app.app_context():
        career_id = create_career("Advay", "Germany", "CM")
        career = get_active_career()
        league = get_world_league(career_id, career["league_id"])
        n = len(league["clubs"])
        fixture_count = get_db().execute(
            "SELECT COUNT(*) AS n FROM fixtures WHERE career_id=? AND season_number=1",
            (career_id,),
        ).fetchone()["n"]
        assert fixture_count == n * (n - 1)
        assert get_db().execute("SELECT COUNT(*) AS n FROM standings WHERE career_id=?", (career_id,)).fetchone()["n"] == n


def test_world_resolves_promotion_qualification_and_honours(tmp_path: Path):
    app = make_app(tmp_path)
    with app.app_context():
        career_id = create_career("Advay", "India", "ST")
        seed = 1
        while True:
            report = play_next_week(career_id, seed=seed)
            if report is None:
                break
            seed += 1
        ok, message = finalize_season(career_id, seed=1234)
        assert ok, message
        career = get_active_career()
        assert career["season_number"] == 2
        assert get_db().execute(
            "SELECT COUNT(*) AS n FROM world_season_outcomes WHERE career_id=? AND season_number=1",
            (career_id,),
        ).fetchone()["n"] >= 300
        assert get_db().execute(
            "SELECT COUNT(*) AS n FROM competition_entries WHERE career_id=? AND season_number=2",
            (career_id,),
        ).fetchone()["n"] > 0
        movement = get_db().execute(
            "SELECT SUM(promoted) AS promoted, SUM(relegated) AS relegated FROM world_season_outcomes WHERE career_id=? AND season_number=1",
            (career_id,),
        ).fetchone()
        assert movement["promoted"] >= 10
        assert movement["relegated"] >= 10
        assert get_db().execute(
            "SELECT COUNT(*) AS n FROM competition_honours WHERE career_id=? AND season_number=1",
            (career_id,),
        ).fetchone()["n"] >= 10


def test_world_page_and_competition_catalogue(tmp_path: Path):
    app = make_app(tmp_path)
    with app.app_context():
        create_career("Advay", "Spain", "RW")
    client = app.test_client()
    page = client.get("/world")
    html = page.get_data(as_text=True)
    assert page.status_code == 200
    assert "UEFA Champions League" in html
    assert "FIFA World Cup" in html
    assert "LALIGA HYPERMOTION" in html
    assert "Football world" in html
