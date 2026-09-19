from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape
from app.player_visuals import build_player_visual

ROOT = Path(__file__).resolve().parents[1]

BASE = {
    "id": 17,
    "player_name": "Test Player",
    "position": "CM",
    "overall": 72,
    "club_id": 4,
    "club_name": "Test United",
    "fitness": 91,
    "morale": 78,
    "stress": 22,
    "injured_weeks": 0,
    "suspended_matches": 0,
}

def render(career=None):
    env = Environment(loader=FileSystemLoader(ROOT / "app" / "templates"), autoescape=select_autoescape(("html", "xml")))
    module = env.get_template("_player_visual.html").module
    return str(module.player_visual(build_player_visual(BASE if career is None else career)))

def test_renderer_outputs_accessible_svg():
    html = render()
    assert "<svg" in html
    assert 'role="img"' in html
    assert 'data-layer="portrait"' in html

def test_renderer_escapes_text():
    html = render(dict(BASE, player_name="<script>x</script>"))
    assert "<script>" not in html
    assert "&lt;script&gt;" in html

def test_renderer_has_reduced_motion_css():
    css = (ROOT / "app" / "static" / "style.css").read_text(encoding="utf-8")
    assert "@media (prefers-reduced-motion: reduce)" in css
