from pathlib import Path

from app import create_app
from app.db import get_db
from app.services import create_career, get_active_career, get_club_history, get_season_history


def make_app(tmp_path: Path):
    return create_app({
        "TESTING": True,
        "DATABASE": str(tmp_path / "history.sqlite3"),
        "SECRET_KEY": "test",
    })


def test_history_includes_live_current_season_before_finalize(tmp_path):
    app = make_app(tmp_path)
    with app.app_context():
        career_id = create_career("Advay", "India", "CAM")
        career = get_active_career()
        rows = get_season_history(career_id)
        assert len(rows) == 1
        assert rows[0]["club_name"] == career["club_name"]
        assert rows[0]["league_name"] == career["league_name"]
        assert rows[0]["is_current"] is True


def _legacy_chain(app):
    with app.app_context():
        career_id = create_career("Advay", "India", "CAM")
        db = get_db()
        start = get_active_career()
        destinations = db.execute(
            """
            SELECT c.id,c.name,c.league_id,l.name AS league_name
            FROM clubs c JOIN leagues l ON l.id=c.league_id
            WHERE c.id<>? ORDER BY c.id LIMIT 3
            """,
            (start["club_id"],),
        ).fetchall()
        assert len(destinations) == 3
        previous = start["club_id"]
        for season_number, club in zip((2, 3, 4), destinations):
            db.execute(
                """
                INSERT INTO transfer_offers(
                    career_id,season_number,from_club_id,to_club_id,wage,status,to_league_id
                ) VALUES (?,?,?,?,?,'accepted',?)
                """,
                (career_id, season_number, previous, club["id"], 1000 + season_number, club["league_id"]),
            )
            previous = club["id"]
        db.execute("DELETE FROM season_history WHERE career_id=?", (career_id,))
        db.execute("DELETE FROM club_history WHERE career_id=? AND joined_season>1", (career_id,))
        db.execute("DELETE FROM season_player_stats WHERE career_id=? AND season_number>1", (career_id,))
        db.execute(
            """
            UPDATE careers
            SET season_number=4,season_label='2029/30',club_id=?,league_id=?,season_phase='competitive'
            WHERE id=?
            """,
            (destinations[-1]["id"], destinations[-1]["league_id"], career_id),
        )
        db.commit()
        return career_id, start["club_name"], [(x["name"], x["league_name"]) for x in destinations]


def test_history_recovers_missing_legacy_transfer_chain(tmp_path):
    app = make_app(tmp_path)
    career_id, start_name, destinations = _legacy_chain(app)
    with app.app_context():
        seasons = get_season_history(career_id)
        clubs = get_club_history(career_id)
        season_names = {x["club_name"] for x in seasons}
        club_names = {x["club_name"] for x in clubs}
        assert start_name in season_names and start_name in club_names
        for club_name, league_name in destinations:
            assert club_name in season_names
            assert club_name in club_names
            assert any(x["club_name"] == club_name and x["league_name"] == league_name for x in seasons)
        assert seasons[0]["club_name"] == destinations[-1][0]
        assert seasons[0]["is_current"] is True


def test_history_page_renders_recovered_clubs_and_leagues(tmp_path):
    app = make_app(tmp_path)
    _career_id, start_name, destinations = _legacy_chain(app)
    response = app.test_client().get("/career-history")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert start_name in html
    for club_name, league_name in destinations:
        assert club_name in html
        assert league_name in html
