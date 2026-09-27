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
        before = get_active_career()
        report = play_next_week(career_id, seed=13)

        assert report is not None
        assert len(report["events"]) >= 9
        assert report["events"][0]["minute"] == 0
        assert report["events"][-1]["minute"] == 90
        assert report["fitness_after"] >= 45
        assert "Match development:" in report["development_summary"]
        assert "Training:" in report["development_summary"]

        career = get_active_career()
        assert career["current_week"] == 2
        assert career["xp"] == 0
        assert any(
            career[name] > before[name] or career[f"{name}_xp"] > before[f"{name}_xp"]
            for name in ("pace", "shooting", "passing", "dribbling", "defending", "physical")
        )


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


def _task6_html_tags(html):
    from html.parser import HTMLParser
    class Tags(HTMLParser):
        def __init__(self):
            super().__init__()
            self.tags=[]
        def handle_starttag(self, tag, attrs):
            self.tags.append((tag,dict(attrs)))
    parser=Tags()
    parser.feed(html)
    return parser.tags


def test_task6_dashboard_renders_six_accessible_current_meters_and_focus_controls(tmp_path):
    app=make_app(tmp_path)
    with app.app_context():
        career_id=create_career('Advay','India','CAM')
        get_db().execute('UPDATE player_attributes SET passing_xp=14 WHERE career_id=?',(career_id,))
        get_db().commit()
    response=app.test_client().get('/')
    assert response.status_code == 200
    html=response.get_data(as_text=True)
    tags=_task6_html_tags(html)
    meters=[attrs for tag,attrs in tags if attrs.get('role')=='progressbar' and 'data-attribute-meter' in attrs]
    assert len(meters)==6
    assert {m['data-attribute-meter'] for m in meters} == {'pace','shooting','passing','dribbling','defending','physical'}
    for m in meters:
        assert m['aria-valuemin']=='0' and m['aria-valuemax']=='100'
        assert 0 <= int(m['aria-valuenow']) <= 100
        assert m['aria-label'] and 'XP' in m['aria-valuetext']
    controls={attrs['data-training-focus']:(tag,attrs) for tag,attrs in tags if 'data-training-focus' in attrs}
    assert set(controls)=={'pace','shooting','passing','dribbling','defending','physical','balanced','recovery'}
    for focus,(tag,attrs) in controls.items():
        assert tag=='button' and attrs['type']=='button'
        assert attrs['aria-pressed'] in ('true','false')
        assert 'disabled' not in attrs
    assert sum(attrs['aria-pressed']=='true' for _,attrs in controls.values())==1
    assert 'id="xp-progress"' not in html and 'id="xp-track-fill"' not in html
    assert len([a for _,a in tags if 'data-training-preview' in a])==6
    assert any(a.get('id')=='training-preview-note' for _,a in tags)


def test_task6_dashboard_caps_do_not_promise_impossible_next_attribute(tmp_path):
    app=make_app(tmp_path)
    with app.app_context():
        career_id=create_career('Advay','India','CAM')
        db=get_db()
        db.execute('UPDATE careers SET overall=88,potential=88 WHERE id=?',(career_id,))
        db.execute('UPDATE player_attributes SET passing=99,passing_xp=500 WHERE career_id=?',(career_id,))
        db.commit()
    html=app.test_client().get('/').get_data(as_text=True)
    assert 'Attribute limit reached' in html
    assert 'Potential reached' in html
    assert 'XP to 100' not in html
    tags=_task6_html_tags(html)
    passing=next(a for _,a in tags if a.get('data-attribute-meter')=='passing')
    assert passing['aria-valuenow']=='100'
    assert '500 XP banked' in passing['aria-valuetext']


def test_task6_dashboard_keeps_all_training_controls_locked_during_match(tmp_path):
    from app.services import prepare_next_match
    app=make_app(tmp_path)
    with app.app_context():
        career_id=create_career('Advay','India','CAM')
        get_db().execute("UPDATE careers SET calendar_week=6,season_phase='competitive' WHERE id=?",(career_id,))
        get_db().commit()
        assert prepare_next_match(career_id,seed=4) is not None
    html=app.test_client().get('/').get_data(as_text=True)
    controls=[a for _,a in _task6_html_tags(html) if 'data-training-focus' in a]
    assert len(controls)==8
    assert all('disabled' in a for a in controls)
    assert 'data-training-locked="true"' in html


def test_task6_progressbar_roles_are_not_hidden_inside_buttons(tmp_path):
    from html.parser import HTMLParser
    class AccessibleMeters(HTMLParser):
        def __init__(self):
            super().__init__()
            self.in_button=False
            self.nested=[]
        def handle_starttag(self,tag,attrs):
            if tag=='button': self.in_button=True
            attrs=dict(attrs)
            if attrs.get('role')=='progressbar' and self.in_button:
                self.nested.append(attrs.get('data-attribute-meter'))
        def handle_endtag(self,tag):
            if tag=='button': self.in_button=False
    app=make_app(tmp_path)
    with app.app_context(): create_career('QA','India','CAM')
    parser=AccessibleMeters()
    parser.feed(app.test_client().get('/').get_data(as_text=True))
    assert parser.nested == [], 'Button descendants can hide progressbar semantics from assistive technology'
