from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.player_visuals import build_player_visual


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "app" / "templates" / "_player_visual.html"
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


def render(career=None, *, selection_status=None, size="hero", show_status=True):
    env = Environment(
        loader=FileSystemLoader(ROOT / "app" / "templates"),
        autoescape=select_autoescape(("html", "xml")),
    )
    module = env.get_template("_player_visual.html").module
    visual = build_player_visual(
        BASE if career is None else career,
        selection_status=selection_status,
        context="match" if selection_status is not None else "dashboard",
    )
    return str(module.player_visual(visual, size=size, show_status=show_status))


def test_renderer_is_a_real_layered_svg_character():
    html = render()

    assert "<svg" in html
    for layer in ("posture", "idle", "character", "torso", "neck", "face", "brows", "eyes", "nose", "expression", "hair"):
        assert f'data-layer="{layer}"' in html
    assert 'role="img"' in html
    assert 'data-player-identity="v1-' in html


def test_posture_and_breathing_use_separate_transform_layers():
    template_source = TEMPLATE.read_text(encoding="utf-8")
    css_source = CSS.read_text(encoding="utf-8")

    posture_pos = template_source.index('data-layer="posture"')
    idle_pos = template_source.index('data-layer="idle"')
    character_pos = template_source.index('data-layer="character"')

    assert posture_pos < idle_pos < character_pos
    assert ".pv-posture--slumped" in css_source
    assert ".pv-idle {" in css_source
    posture_rule = css_source.split(".pv-posture--slumped", 1)[1].split("}", 1)[0]
    idle_rule = css_source.split(".pv-idle {", 1)[1].split("}", 1)[0]
    assert "transform:" in posture_rule
    assert "animation: pv-breathe" in idle_rule


def test_stylesheet_has_canonical_single_newline_eof():
    raw = CSS.read_bytes()
    assert raw.endswith(b"\n")
    assert not raw.endswith(b"\n\n")


def test_renderer_uses_the_model_identity_traits():
    visual = build_player_visual(BASE)
    html = render()

    assert f"pv-face--{visual['appearance']['face_shape']}" in html
    assert f"pv-hair--{visual['appearance']['hair_style']}" in html
    assert f"pv-body--{visual['appearance']['build']}" in html
    assert f"pv-expression--{visual['presentation']['expression']}" in html


def test_injury_treatment_only_renders_from_authoritative_injury_state():
    fit_html = render(dict(BASE, injured_weeks=0))
    hurt_html = render(dict(BASE, injured_weeks=3))

    assert 'data-layer="treatment"' not in fit_html
    assert 'data-layer="treatment"' in hurt_html
    assert 'data-injury="injured"' in hurt_html


def test_fatigue_visuals_are_state_driven():
    fresh = render(dict(BASE, fitness=95))
    exhausted = render(dict(BASE, fitness=30))

    assert 'data-layer="fatigue"' not in fresh
    assert 'data-layer="fatigue"' in exhausted
    assert 'data-energy="exhausted"' in exhausted
    assert "pv-posture--slumped" in exhausted


def test_match_selection_is_presentation_only_and_normalized():
    html = render(selection_status="bench", size="compact")

    assert 'data-selection="substitute"' in html
    assert "player-visual--compact" in html


def test_player_text_is_escaped_by_jinja():
    hostile = dict(
        BASE,
        player_name='<script>alert("x")</script>',
        club_name='<img src=x onerror=alert(1)>',
    )
    html = render(hostile)

    assert "<script>" not in html
    assert "<img" not in html
    assert "&lt;script&gt;" in html
    assert "&lt;img" in html


def test_template_contains_no_unsafe_or_remote_rendering_paths():
    source = TEMPLATE.read_text(encoding="utf-8").lower()

    assert "|safe" not in source
    assert "<image" not in source
    assert "http://" not in source
    assert "https://" not in source
    assert "javascript:" not in source
    assert "innerhtml" not in source


def test_all_declared_hair_styles_have_renderer_branches():
    from app import player_visuals as pv

    source = TEMPLATE.read_text(encoding="utf-8")
    for style in pv.HAIR_STYLES:
        assert style in source


def test_renderer_can_hide_caption_without_hiding_svg_accessibility():
    html = render(show_status=False)

    assert "player-visual__caption" not in html
    assert 'role="img"' in html
    assert "Test Player, CM, 72 overall, Test United" in html


def test_component_css_is_namespaced_and_reduced_motion_safe():
    source = CSS.read_text(encoding="utf-8")

    assert ".player-visual {" in source
    assert ".pv-posture" in source
    assert ".pv-idle" in source
    assert "@media (prefers-reduced-motion: reduce)" in source
    assert "pv-breathe" in source

