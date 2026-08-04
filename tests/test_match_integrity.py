import json
from pathlib import Path

from app import create_app
from app.db import get_db
from app.services import (
    advance_calendar_week,
    advance_match_session,
    complete_match_session,
    create_career,
    get_active_career,
    get_match_session_view,
    get_stats,
    prepare_next_match,
)


def make_app(tmp_path: Path):
    database = tmp_path / "test.sqlite3"
    return create_app({"TESTING": True, "DATABASE": str(database), "SECRET_KEY": "test"})


def advance_to_first_fixture(career_id):
    while True:
        career = get_active_career()
        fixture = get_db().execute(
            """
            SELECT 1 FROM fixtures
            WHERE career_id=? AND season_number=? AND played=0 AND calendar_week=?
              AND (home_club_id=? OR away_club_id=?) LIMIT 1
            """,
            (career_id, career["season_number"], career["calendar_week"], career["club_id"], career["club_id"]),
        ).fetchone()
        if fixture:
            return
        ok, message, _data = advance_calendar_week(career_id, seed=1701 + career["calendar_week"])
        assert ok, message


def test_prepared_match_is_sealed_and_does_not_mutate_career(tmp_path: Path):
    app = make_app(tmp_path)
    with app.app_context():
        career_id = create_career("Advay", "India", "ST")
        advance_to_first_fixture(career_id)
        before = get_active_career()
        stats_before = dict(get_stats(career_id))

        session = prepare_next_match(career_id, seed=77)
        assert session is not None

        after = get_active_career()
        assert after["current_week"] == before["current_week"]
        assert after["money"] == before["money"]
        assert after["xp"] == before["xp"]
        assert dict(get_stats(career_id)) == stats_before
        assert get_db().execute(
            "SELECT COUNT(*) AS total FROM fixtures WHERE career_id = ? AND played = 1",
            (career_id,),
        ).fetchone()["total"] == 0

        safe_view = get_match_session_view(session["public_id"], career_id)
        assert "home_goals" not in safe_view
        assert "away_goals" not in safe_view
        assert "report" not in safe_view


def test_event_reveal_is_sequential_and_retry_safe(tmp_path: Path):
    app = make_app(tmp_path)
    with app.app_context():
        career_id = create_career("Advay", "India", "CAM")
        advance_to_first_fixture(career_id)
        session = prepare_next_match(career_id, seed=11)

        ok, _message, first = advance_match_session(session["public_id"], career_id, 0)
        assert ok
        assert first["event"]["sequence"] == 0

        ok, _message, retry = advance_match_session(session["public_id"], career_id, 0)
        assert ok
        assert retry["event"] == first["event"]

        ok, _message, skipped = advance_match_session(session["public_id"], career_id, 2)
        assert not ok
        assert skipped is None


def test_completion_is_transactional_and_idempotent(tmp_path: Path):
    app = make_app(tmp_path)
    with app.app_context():
        career_id = create_career("Advay", "India", "ST")
        advance_to_first_fixture(career_id)
        session = prepare_next_match(career_id, seed=19)

        ok, _message, payload = complete_match_session(
            session["public_id"], career_id, allow_skip=False
        )
        assert not ok
        assert payload is None

        ok, _message, first = complete_match_session(
            session["public_id"], career_id, allow_skip=True
        )
        assert ok
        career_after_first = get_active_career()
        stats_after_first = dict(get_stats(career_id))
        report_count = get_db().execute(
            "SELECT COUNT(*) AS total FROM match_reports WHERE session_id = ?",
            (session["id"],),
        ).fetchone()["total"]
        assert report_count == 1

        ok, _message, second = complete_match_session(
            session["public_id"], career_id, allow_skip=True
        )
        assert ok
        career_after_second = get_active_career()
        assert second["final_score"] == first["final_score"]
        assert career_after_second["current_week"] == career_after_first["current_week"]
        assert career_after_second["money"] == career_after_first["money"]
        assert dict(get_stats(career_id)) == stats_after_first
        assert get_db().execute(
            "SELECT COUNT(*) AS total FROM match_reports WHERE session_id = ?",
            (session["id"],),
        ).fetchone()["total"] == 1


def test_report_is_derived_from_same_event_ledger(tmp_path: Path):
    app = make_app(tmp_path)
    with app.app_context():
        career_id = create_career("Advay", "India", "RW")
        advance_to_first_fixture(career_id)
        session = prepare_next_match(career_id, seed=29)
        snapshot = json.loads(session["simulation_json"])
        events = snapshot["performance"]["events"]
        assert "analysis" not in snapshot["performance"]

        ok, _message, payload = complete_match_session(
            session["public_id"], career_id, allow_skip=True
        )
        assert ok
        analysis = payload["report"]["analysis"]
        assert analysis["trace"]["event_count"] == len(events)
        assert analysis["trace"]["goals_from_events"] == sum(
            event["kind"] == "goal_for" for event in events
        )
        assert analysis["trace"]["goals_against_from_events"] == sum(
            event["kind"] == "goal_against" for event in events
        )
        assert analysis["metrics"] == snapshot["performance"]["metrics"]
        assert analysis["gaps"]
        assert analysis["coaching_actions"]


def test_match_html_contains_no_final_result_payload(tmp_path: Path):
    app = make_app(tmp_path)
    with app.app_context():
        create_career("Advay", "India", "ST")
        advance_to_first_fixture(get_active_career()["id"])

    client = app.test_client()
    response = client.post("/play", follow_redirects=True)
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "data-final-home" not in html
    assert "data-final-away" not in html
    assert "FULL RESULT" not in html
    assert "Final score, rating, development, rewards and analysis stay locked" in html



def test_match_html_contains_no_final_report_markup_or_payload(tmp_path: Path):
    app = make_app(tmp_path)
    with app.app_context():
        create_career("Advay", "India", "ST")
        advance_to_first_fixture(get_active_career()["id"])
    client = app.test_client()
    play_response = client.post("/play", follow_redirects=False)
    assert play_response.status_code == 303
    page = client.get(play_response.headers["Location"])
    html = page.get_data(as_text=True)
    assert "FULL-TIME ANALYSIS" not in html
    assert 'id="report-headline"' not in html
    assert 'id="final-player-stats"' not in html
    assert 'id="post-match-mount"' in html
    assert "no-store" in page.headers["Cache-Control"]


def test_report_is_pending_until_completion_then_frozen(tmp_path: Path):
    app = make_app(tmp_path)
    with app.app_context():
        career_id = create_career("Advay", "India", "CAM")
        advance_to_first_fixture(career_id)
        session = prepare_next_match(career_id, seed=91)
        row = get_db().execute("SELECT report_json FROM match_sessions WHERE id = ?", (session["id"],)).fetchone()
        assert json.loads(row["report_json"])["status"] == "pending"
        ok, _, payload = complete_match_session(session["public_id"], career_id, allow_skip=True)
        assert ok
        assert payload["report"]["analysis"]["source"] == "sealed_event_ledger"
        row = get_db().execute("SELECT report_json FROM match_sessions WHERE id = ?", (session["id"],)).fetchone()
        frozen = json.loads(row["report_json"])
        assert frozen["status"] == "completed"
        assert frozen["analysis"]["trace"]["event_count"] >= 2
