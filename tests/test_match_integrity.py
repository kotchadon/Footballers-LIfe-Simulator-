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


# Task 5: real database settlement and retry protection.
import pytest

TASK5_ATTRIBUTES = ('pace','shooting','passing','dribbling','defending','physical')


def _task5_prepare_career():
    career_id = create_career('Advay','India','CAM')
    db = get_db()
    db.execute("UPDATE careers SET calendar_week=6,season_phase='competitive',training_focus='passing',overall=58,potential=88,fitness=80,morale=70,manager_trust=35,squad_level='first_team' WHERE id=?", (career_id,))
    db.execute('UPDATE player_attributes SET pace=58,shooting=58,passing=58,dribbling=58,defending=58,physical=58,pace_xp=40,shooting_xp=40,passing_xp=40,dribbling_xp=40,defending_xp=40,physical_xp=40 WHERE career_id=?', (career_id,))
    db.commit()
    return career_id


def _task5_state():
    career = get_active_career()
    return ({name:career[name] for name in TASK5_ATTRIBUTES}, {name:career[name+'_xp'] for name in TASK5_ATTRIBUTES}, career['overall'],career['xp'])


@pytest.mark.parametrize('skip', [False, True])
def test_task5_settlement_matches_sealed_state_and_retry_is_unchanged(tmp_path, skip):
    app = make_app(tmp_path)
    with app.app_context():
        career_id = _task5_prepare_career()
        before = _task5_state()
        session = prepare_next_match(career_id, seed=4)
        assert _task5_state() == before
        snapshot = json.loads(session['simulation_json'])
        development = snapshot['post_match']['development']
        assert development['meters_before'] == before[1]
        if not skip:
            ok, _, _ = complete_match_session(session['public_id'],career_id,allow_skip=False)
            assert not ok and _task5_state() == before
            for cursor in range(session['event_count']):
                ok, message, _ = advance_match_session(session['public_id'],career_id,cursor)
                assert ok, message
        ok, message, first = complete_match_session(session['public_id'],career_id,allow_skip=skip)
        assert ok, message
        assert _task5_state() == (development['attributes'],development['meters_after'],development['overall'],0)
        after = dict(get_active_career())
        stats = dict(get_stats(career_id))
        for repeat_skip in (False,True):
            ok, message, retry = complete_match_session(session['public_id'],career_id,allow_skip=repeat_skip)
            assert ok, message
            assert retry == first
            assert dict(get_active_career()) == after
            assert dict(get_stats(career_id)) == stats
        assert get_db().execute('SELECT COUNT(*) FROM match_reports WHERE session_id=?',(session['id'],)).fetchone()[0] == 1


def test_task5_settled_match_prevents_calendar_double_training(tmp_path):
    app = make_app(tmp_path)
    with app.app_context():
        career_id = _task5_prepare_career()
        session = prepare_next_match(career_id,seed=4)
        ok, message, _ = complete_match_session(session['public_id'],career_id,allow_skip=True)
        assert ok,message
        before = _task5_state()
        ok,message,_ = advance_calendar_week(career_id,seed=7)
        assert ok,message
        assert _task5_state() == before
        assert get_active_career()['calendar_week'] == 7


def test_task5_second_fixture_in_week_gets_match_xp_without_repeat_training(tmp_path):
    app = make_app(tmp_path)
    with app.app_context():
        career_id = _task5_prepare_career()
        db=get_db()
        db.execute('UPDATE fixtures SET calendar_week=6 WHERE career_id=? AND season_number=1 AND week=2',(career_id,))
        db.commit()
        first=prepare_next_match(career_id,seed=4)
        assert complete_match_session(first['public_id'],career_id,allow_skip=True)[0]
        second=prepare_next_match(career_id,seed=4)
        assert second is not None
        development=json.loads(second['simulation_json'])['post_match']['development']
        assert sum(development['training_xp'].values()) == 0
        assert development['total_xp'] == development['match_xp']
        assert complete_match_session(second['public_id'],career_id,allow_skip=True)[0]
        before=_task5_state()
        assert advance_calendar_week(career_id,seed=7)[0]
        assert _task5_state() == before


def test_task5_changed_xp_after_preparation_is_rejected_without_overwrite(tmp_path):
    app=make_app(tmp_path)
    with app.app_context():
        career_id=_task5_prepare_career()
        session=prepare_next_match(career_id,seed=4)
        db=get_db()
        db.execute('UPDATE player_attributes SET passing_xp=passing_xp+1 WHERE career_id=?',(career_id,))
        db.commit()
        before=_task5_state()
        ok,message,_=complete_match_session(session['public_id'],career_id,allow_skip=True)
        assert not ok
        assert 'changed' in message.lower()
        assert _task5_state()==before
        assert db.execute('SELECT COUNT(*) FROM match_reports WHERE session_id=?',(session['id'],)).fetchone()[0]==0
        assert db.execute('SELECT COUNT(*) FROM fixtures WHERE career_id=? AND played=1',(career_id,)).fetchone()[0]==0


def test_task5_late_failure_rolls_back_all_progression_and_allows_safe_retry(tmp_path):
    import sqlite3
    app=make_app(tmp_path)
    with app.app_context():
        career_id=_task5_prepare_career()
        session=prepare_next_match(career_id,seed=4)
        development=json.loads(session['simulation_json'])['post_match']['development']
        db=get_db()
        before=dict(get_active_career())
        stats=dict(get_stats(career_id))
        db.execute("CREATE TEMP TRIGGER task5_fail BEFORE UPDATE OF status ON match_sessions WHEN NEW.status='completed' BEGIN SELECT RAISE(ABORT, 'task5 forced rollback'); END")
        db.commit()
        with pytest.raises(sqlite3.IntegrityError,match='task5 forced rollback'):
            complete_match_session(session['public_id'],career_id,allow_skip=True)
        assert dict(get_active_career())==before
        assert dict(get_stats(career_id))==stats
        assert db.execute('SELECT COUNT(*) FROM match_reports WHERE session_id=?',(session['id'],)).fetchone()[0]==0
        db.execute('DROP TRIGGER task5_fail');db.commit()
        assert complete_match_session(session['public_id'],career_id,allow_skip=True)[0]
        assert _task5_state()==(development['attributes'],development['meters_after'],development['overall'],0)


def test_task5_legacy_prepared_match_keeps_sealed_result_and_migrates_remainder_once(tmp_path):
    app=make_app(tmp_path)
    with app.app_context():
        career_id=_task5_prepare_career()
        session=prepare_next_match(career_id,seed=4)
        snapshot=json.loads(session['simulation_json'])
        before=_task5_state()
        legacy_attributes=dict(before[0]);legacy_attributes['passing']=59
        snapshot['post_match']['development']={'attributes':legacy_attributes,'overall':58,'xp':17,'upgrades':['passing']}
        db=get_db()
        db.execute('UPDATE match_sessions SET simulation_json=? WHERE id=?',(json.dumps(snapshot),session['id']))
        db.commit()
        assert complete_match_session(session['public_id'],career_id,allow_skip=True)[0]
        expected_meters=dict(before[1]);expected_meters['passing']+=17
        assert _task5_state()==(legacy_attributes,expected_meters,58,0)
        assert complete_match_session(session['public_id'],career_id,allow_skip=True)[0]
        assert _task5_state()==(legacy_attributes,expected_meters,58,0)


def test_task5_live_payloads_never_expose_sealed_progression(tmp_path):
    app=make_app(tmp_path)
    with app.app_context():
        career_id=_task5_prepare_career()
        session=prepare_next_match(career_id,seed=4)
        view=get_match_session_view(session['public_id'],career_id)
        ok,message,event=advance_match_session(session['public_id'],career_id,0)
        assert ok,message
        for data in (view,event):
            encoded=json.dumps(data)
            for secret in ('meters_after','total_xp','attributes_before','match_xp'):
                assert secret not in encoded



def test_task7_completion_exposes_only_settled_development(tmp_path):
    app = make_app(tmp_path)
    with app.app_context():
        career_id = create_career("Advay", "India", "CAM")
        advance_to_first_fixture(career_id)
        session = prepare_next_match(career_id, seed=1707)
        snapshot = json.loads(session["simulation_json"])
        sealed = snapshot["post_match"]["development"]
        assert sealed["schema_version"] == 2

        ok, message, payload = complete_match_session(
            session["public_id"], career_id, allow_skip=True
        )
        assert ok, message
        public = payload["development"]

        assert set(public) == {
            "schema_version",
            "match_xp",
            "training_xp",
            "meters_after",
            "attributes",
            "overall_before",
            "overall",
            "upgrades",
        }
        assert public["schema_version"] == 2
        assert public["match_xp"] == sealed["match_xp"]
        assert public["training_xp"] == sealed["training_xp"]
        assert public["meters_after"] == sealed["meters_after"]
        assert public["attributes"] == sealed["attributes"]
        assert public["overall_before"] == sealed["overall_before"]
        assert public["overall"] == sealed["overall"]
        assert public["upgrades"] == sealed["upgrades"]
        for hidden in ("meters_before", "attributes_before", "total_xp", "potential_before"):
            assert hidden not in public
        assert payload["report"]["development_summary"]


def test_task7_completion_retry_returns_identical_development(tmp_path):
    app = make_app(tmp_path)
    with app.app_context():
        career_id = create_career("Advay", "India", "RW")
        advance_to_first_fixture(career_id)
        session = prepare_next_match(career_id, seed=1708)

        ok, message, first = complete_match_session(
            session["public_id"], career_id, allow_skip=True
        )
        assert ok, message
        state_after_first = dict(get_active_career())

        ok, message, second = complete_match_session(
            session["public_id"], career_id, allow_skip=True
        )
        assert ok, message
        assert second["development"] == first["development"]
        assert second["report"]["development_summary"] == first["report"]["development_summary"]
        assert dict(get_active_career()) == state_after_first


def test_task7_live_advance_payload_never_exposes_settled_development(tmp_path):
    app = make_app(tmp_path)
    with app.app_context():
        career_id = create_career("Advay", "India", "LW")
        advance_to_first_fixture(career_id)
        session = prepare_next_match(career_id, seed=1709)

        view = get_match_session_view(session["public_id"], career_id)
        ok, message, event = advance_match_session(
            session["public_id"], career_id, 0
        )
        assert ok, message

        for data in (view, event):
            encoded = json.dumps(data)
            assert '"development"' not in encoded
            for secret in (
                "match_xp",
                "training_xp",
                "meters_after",
                "attributes_before",
                "total_xp",
            ):
                assert secret not in encoded


def test_task7_legacy_prepared_match_uses_summary_fallback_without_crashing(tmp_path):
    app = make_app(tmp_path)
    with app.app_context():
        career_id = create_career("Advay", "India", "CM")
        advance_to_first_fixture(career_id)
        session = prepare_next_match(career_id, seed=1710)
        snapshot = json.loads(session["simulation_json"])
        sealed = snapshot["post_match"]["development"]
        snapshot["post_match"]["development"] = {
            "attributes": dict(sealed["attributes_before"]),
            "overall": sealed["overall_before"],
            "xp": 17,
            "upgrades": ["passing"],
        }

        db = get_db()
        db.execute(
            "UPDATE match_sessions SET simulation_json=? WHERE id=?",
            (json.dumps(snapshot), session["id"]),
        )
        db.commit()

        ok, message, payload = complete_match_session(
            session["public_id"], career_id, allow_skip=True
        )
        assert ok, message
        assert payload["development"] is None
        assert payload["report"]["development_summary"]
