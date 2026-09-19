from pathlib import Path
import ast
from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parents[1]
ROUTES = ROOT / "app" / "routes.py"
DASHBOARD = ROOT / "app" / "templates" / "dashboard.html"
CSS = ROOT / "app" / "static" / "style.css"

def test_dashboard_route_builds_read_only_v5_visual_model():
    source = ROUTES.read_text(encoding="utf-8")
    ast.parse(source)
    assert "from .player_visuals import build_player_visual" in source
    assert 'player_visual_model=build_player_visual(career, context="dashboard")' in source

def test_dashboard_uses_final_cut_v5_hero_and_shared_renderer():
    source = DASHBOARD.read_text(encoding="utf-8")
    assert '{% from "_player_visual.html" import player_visual as render_player_visual %}' in source
    assert 'class="career-hero-v5"' in source
    assert "render_player_visual(player_visual_model" in source
    assert 'class="career-rating-v5"' in source
    assert "player-card-mark" not in source
    assert "<svg" not in source

def test_dashboard_v5_promotes_authoritative_player_state():
    source = DASHBOARD.read_text(encoding="utf-8")
    for token in ("career.fitness", "career.morale", "career.stress", "career.manager_trust", "career.overall", "career.potential", "career.injured_weeks", "career.suspended_matches"):
        assert token in source

def test_dashboard_template_compiles():
    env = Environment(loader=FileSystemLoader(ROOT / "app" / "templates"))
    env.get_template("dashboard.html")

def test_dashboard_v5_css_has_responsive_football_layout():
    css = CSS.read_text(encoding="utf-8")
    for token in (".career-hero-v5 {", ".career-hero-v5__portrait", ".career-hero-v5__metrics", ".career-rating-v5"):
        assert token in css
    assert "@media (max-width: 980px)" in css
    assert "@media (max-width: 680px)" in css

def test_dashboard_v5_adds_no_write_or_js_render_surface():
    source = DASHBOARD.read_text(encoding="utf-8").lower()
    assert "fetch(" not in source
    assert "xmlhttprequest" not in source
    assert "innerhtml" not in source

def test_stylesheet_has_canonical_eof():
    raw = CSS.read_bytes()
    assert raw.endswith(b"\n")
    assert not raw.endswith(b"\n\n")
