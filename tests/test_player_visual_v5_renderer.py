from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape
from app.player_visuals import build_player_visual

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "app" / "templates" / "_player_visual.html"
PARTS = ROOT / "app" / "templates" / "player_portrait_v5" / "_parts.html"
CSS = ROOT / "app" / "static" / "style.css"

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

def render(career=None, *, selection_status=None, show_status=True):
    env = Environment(loader=FileSystemLoader(ROOT / "app" / "templates"), autoescape=select_autoescape(("html", "xml")))
    module = env.get_template("_player_visual.html").module
    visual = build_player_visual(BASE if career is None else career, selection_status=selection_status, context="dashboard")
    return str(module.player_visual(visual, size="hero", show_status=show_status))

def test_v5_public_renderer_uses_modular_parts():
    source = TEMPLATE.read_text(encoding="utf-8")
    assert 'from "player_portrait_v5/_parts.html"' in source
    html = render()
    for layer in ("portrait", "kit", "neck", "head", "brows", "eyes", "nose", "mouth", "facial-hair", "hair"):
        assert f'data-layer="{layer}"' in html

def test_v5_removes_rejected_visual_languages():
    combined = TEMPLATE.read_text(encoding="utf-8") + PARTS.read_text(encoding="utf-8") + CSS.read_text(encoding="utf-8")
    for token in ("CAREER PLAYER", "PLAYER ID", "player-portrait-v2", "player-portrait-v3", "pv2-", "pv3-", "player-portrait-v4", "pv4-", "pv-breathe"):
        assert token not in combined
    assert "<text" not in combined

def test_v5_contract_keeps_identity_and_reaction_hooks():
    visual = build_player_visual(BASE)
    html = render()
    assert visual["identity_key"] in html
    assert f'data-energy="{visual["state"]["energy"]}"' in html
    assert f'data-mood="{visual["state"]["mood"]}"' in html
    assert f'data-expression="{visual["presentation"]["expression"]}"' in html

def test_v5_visual_state_comes_from_authoritative_career_fields():
    fit = render(dict(BASE, injured_weeks=0, fitness=95))
    hurt = render(dict(BASE, injured_weeks=2, fitness=30))
    assert 'data-layer="treatment"' not in fit
    assert 'data-layer="fatigue"' not in fit
    assert 'data-layer="treatment"' in hurt
    assert 'data-layer="fatigue"' in hurt
    assert 'data-injury="injured"' in hurt

def test_v5_match_selection_is_normalized_not_free_text():
    html = render(selection_status="bench")
    assert 'data-selection="substitute"' in html

def test_v5_player_text_is_escaped():
    hostile = dict(BASE, player_name='<script>alert("x")</script>', club_name='<img src=x onerror=alert(1)>')
    html = render(hostile)
    assert "<script>" not in html
    assert "<img" not in html
    assert "&lt;script&gt;" in html
    assert "&lt;img" in html

def test_v5_has_no_unsafe_or_remote_rendering_path():
    combined = (TEMPLATE.read_text(encoding="utf-8") + PARTS.read_text(encoding="utf-8")).lower()
    assert "|safe" not in combined
    assert "<image" not in combined
    assert "http://" not in combined
    assert "https://" not in combined
    assert "javascript:" not in combined
    assert "innerhtml" not in combined

def test_v5_covers_identity_trait_catalogue():
    from app import player_visuals as pv
    source = PARTS.read_text(encoding="utf-8")
    for value in pv.HAIR_STYLES + pv.FACE_SHAPES + pv.EYE_STYLES + pv.BROW_STYLES + pv.NOSE_STYLES + pv.BUILD_STYLES:
        assert value in source

def test_v5_final_cut_has_no_continuous_keyframe_animation():
    css = CSS.read_text(encoding="utf-8")
    block = css.split("/* Player identity V5 — final-cut football portrait */", 1)[1]
    assert "@keyframes" not in block

def test_v5_renderer_can_hide_caption_without_losing_accessibility():
    html = render(show_status=False)
    assert "player-visual__caption" not in html
    assert 'role="img"' in html
    assert "Test Player, CM, 72 overall, Test United" in html
