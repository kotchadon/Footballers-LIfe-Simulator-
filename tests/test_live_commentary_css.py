from pathlib import Path
import re


def test_live_commentary_event_slide_finishes_visible():
    css = Path("app/static/style.css").read_text(encoding="utf-8")
    compact = re.sub(r"\s+", "", css)

    assert (
        ".timeline-event{animation:eventSlide.4scubic-bezier(.2,.8,.2,1)forwards}"
        in compact
    ), "eventSlide must preserve its final visible frame"

    assert (
        "@keyframeseventSlide{"
        "from{opacity:0;transform:translateX(-14px)}"
        "to{opacity:1;transform:translateX(0)}"
        "}"
        in compact
    ), "eventSlide must explicitly finish at opacity:1"
