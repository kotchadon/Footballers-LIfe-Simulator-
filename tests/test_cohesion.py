from pathlib import Path

from app import create_app
from app.services import create_career, get_career_command_center


def make_app(tmp_path: Path):
    return create_app({"TESTING": True, "DATABASE": str(tmp_path / "cohesion.sqlite3"), "SECRET_KEY": "test"})


def test_command_center_exposes_one_primary_action(tmp_path: Path):
    app = make_app(tmp_path)
    with app.app_context():
        career_id = create_career("Advay", "Spain", "CAM")
        state = get_career_command_center(career_id)
        assert state["week_total"] == 52
        assert state["primary"]["kind"] in {
            "resume_match", "play_match", "close_season", "start_season", "advance_week"
        }
        assert state["primary"]["label"]
        assert isinstance(state["decisions"], list)


def test_main_pages_share_career_hud_and_live_scopes(tmp_path: Path):
    app = make_app(tmp_path)
    with app.app_context():
        create_career("Advay", "Spain", "CAM")
    client = app.test_client()
    pages = {
        "/": ("career-hud", "dashboard-app", "CAREER COMMAND CENTRE"),
        "/calendar": ("career-hud", "calendar-app", "THIS WEEK IN CONTEXT"),
        "/market": ("career-hud", "market-app", "Transfer market"),
        "/finances": ("career-hud", "finance-app", "Money without mystery"),
    }
    for path, markers in pages.items():
        response = client.get(path)
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        for marker in markers:
            assert marker in html


def test_career_state_api_matches_backend_state(tmp_path: Path):
    app = make_app(tmp_path)
    with app.app_context():
        create_career("Advay", "India", "RW")
    client = app.test_client()
    response = client.get("/api/career-state")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    assert payload["state"]["week_total"] == 52
    assert payload["state"]["primary"]["label"]
