from pathlib import Path
import re


def get_rule(css, selector_pattern):
    match = re.search(
        rf"{selector_pattern}\s*\{{([^}}]*)\}}",
        css,
        flags=re.S,
    )
    assert match is not None, f"Missing CSS rule: {selector_pattern}"
    return re.sub(r"\s+", "", match.group(1))


def test_dashboard_transfer_preview_matches_dark_theme():
    css = Path("app/static/style.css").read_text(encoding="utf-8")

    card = get_rule(
        css,
        r"\.transfer-panel\s+\.offer-card"
    )

    assert "color:var(--read-text)!important" in card
    assert "background:#132238!important" in card
    assert "border-color:var(--read-border-soft)!important" in card
    assert "border-top-color:#527bd3!important" in card

    wage = get_rule(
        css,
        r"\.transfer-panel\s+\.offer-money\s+strong"
    )
    assert "color:var(--read-text-strong)!important" in wage

    bonus = get_rule(
        css,
        r"\.transfer-panel\s+\.offer-money\s+span"
    )
    assert "color:var(--read-muted)!important" in bonus
