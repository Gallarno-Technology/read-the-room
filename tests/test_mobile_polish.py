"""Tests for Phase 19 Mobile Polish — MOB-01 and MOB-02.

Parses web_ui/templates/index.html as a string to verify the
required CSS rules and viewport meta are present.
Actual rendering behavior on device requires manual verification.
"""
import os

TEMPLATE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "web_ui", "templates", "index.html"
)


def _template() -> str:
    with open(TEMPLATE_PATH, encoding="utf-8") as f:
        return f.read()


def test_viewport_meta_zoom_disabled():
    """MOB-01: Viewport meta includes user-scalable=no and maximum-scale=1."""
    html = _template()
    assert "user-scalable=no" in html, "Viewport meta missing user-scalable=no"
    assert "maximum-scale=1" in html, "Viewport meta missing maximum-scale=1"


def test_touch_action_manipulation_present():
    """MOB-01: touch-action: manipulation appears in the <style> block."""
    html = _template()
    assert "touch-action: manipulation" in html, (
        "Missing touch-action: manipulation CSS rule for double-tap zoom prevention"
    )


def test_user_select_none_on_body():
    """MOB-02: body rule contains user-select: none (and -webkit- prefix)."""
    html = _template()
    assert "user-select: none" in html, "Missing user-select: none on body"
    assert "-webkit-user-select: none" in html, "Missing -webkit-user-select: none (iOS prefix)"


def test_now_playing_name_selectable():
    """MOB-02: #now-playing-name has user-select: text carve-out."""
    html = _template()
    assert "#now-playing-name" in html
    assert "-webkit-user-select: text" in html, "Missing -webkit-user-select: text carve-out"
    assert "user-select: text" in html, "Missing user-select: text carve-out"


def test_now_playing_artist_selectable():
    """MOB-02: #now-playing-artist has user-select: text carve-out."""
    html = _template()
    assert "#now-playing-artist" in html, "Missing #now-playing-artist selector in carve-out block"


def test_feed_span_carveout_present():
    """MOB-02: Feed history span negation carve-out rule is present in CSS."""
    html = _template()
    assert "#skip-feed li span:not(.feed-sep):not(.badge):not(.feed-timestamp)" in html, (
        "Missing feed history span carve-out selector"
    )
