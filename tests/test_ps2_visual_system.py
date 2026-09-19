from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
THEME = ROOT / "app" / "static" / "theme-ps2.css"
BASE = ROOT / "app" / "templates" / "base.html"
PLAYER = ROOT / "app" / "templates" / "_player_visual.html"


def css():
    return THEME.read_text(encoding="utf-8")


def test_ps2_theme_exists_and_loads_after_legacy_css():
    assert THEME.exists()
    base = BASE.read_text(encoding="utf-8")
    assert "style.css" in base
    assert "theme-ps2.css" in base
    assert base.index("style.css") < base.index("theme-ps2.css")


def test_local_typography_roles_are_explicit():
    text = css()
    assert '--font-reading: "Iowan Old Style", "Palatino Linotype", "Book Antiqua", Palatino, Georgia, serif;' in text
    assert '--font-display: Impact, Haettenschweiler, "Arial Narrow Bold", "Arial Black", sans-serif;' in text
    assert '--font-ui: "Trebuchet MS", "Arial Narrow", Arial, sans-serif;' in text
    assert "font-family: var(--font-reading)" in text
    assert "font-family: var(--font-display)" in text
    assert "font-family: var(--font-ui)" in text


def test_dark_navy_steel_palette_replaces_purple_core():
    text = css().lower()
    for token in (
        "--ps2-canvas: #07101b",
        "--ps2-canvas-deep: #050a11",
        "--ps2-surface: #0d1928",
        "--ps2-surface-raised: #122237",
        "--ps2-steel: #26384e",
        "--ps2-text-strong: #edf2f8",
        "--ps2-reading: #ddd4c2",
        "--ps2-accent: #5f7faa",
    ):
        assert token in text
    for purple in ("#785fff", "#7c3aed", "#8b5cf6", "#a855f7", "#9333ea"):
        assert purple not in text


def test_no_remote_fonts_or_remote_css():
    text = css().lower()
    assert "@import" not in text
    assert "@font-face" not in text
    assert "http://" not in text
    assert "https://" not in text
    assert "url(" not in text


def test_all_requested_surfaces_are_covered():
    text = css()
    for marker in (
        "/* Navigation */",
        "/* Dashboard */",
        "/* Match Centre */",
        "/* Training */",
        "/* Transfer Market */",
        "/* Finance */",
        "/* World */",
        "/* Calendar */",
        "/* Reports and long-form reading */",
    ):
        assert marker in text


def test_shared_panels_controls_and_tables_are_restyled():
    text = css()
    for selector in (".panel,", ".button,", "table {", "input,", "select,", "textarea {"):
        assert selector in text


def test_v5_portrait_internal_ownership_is_untouched():
    text = css()
    for forbidden in (
        ".football-portrait-v5",
        ".fp5-head",
        ".fp5-eyes",
        ".fp5-hair",
        ".fp5-kit",
        ".fp5-portrait",
    ):
        assert forbidden not in text
    assert "football-portrait-v5" in PLAYER.read_text(encoding="utf-8")


def test_focus_and_reduced_motion_hooks_exist():
    text = css()
    assert ":focus-visible" in text
    assert "@media (prefers-reduced-motion: reduce)" in text
    assert "outline: 2px solid var(--ps2-accent-cold)" in text


def test_theme_is_css_only():
    base = BASE.read_text(encoding="utf-8")
    assert "theme-ps2.css" in base
    assert "theme-ps2.js" not in base


def test_theme_has_canonical_eof():
    raw = THEME.read_bytes()
    assert raw.endswith(b"\n")
    assert not raw.endswith(b"\n\n")
