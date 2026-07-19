"""Tests for Phase 18 Profile Info Icon — INFO-01.

Parses web_ui/templates/index.html as a string to verify the
required structural elements and JS constants are present.
JavaScript interaction (INFO-02) is validated manually in browser.
"""
import os

TEMPLATE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "web_ui", "templates", "index.html"
)


def _template() -> str:
    with open(TEMPLATE_PATH, encoding="utf-8") as f:
        return f.read()


def test_info_btn_present():
    """INFO-01: ⓘ button element exists in the FSM card markup."""
    html = _template()
    assert 'id="info-btn"' in html, "Missing #info-btn element in FSM card"


def test_info_panel_present():
    """INFO-01: Info panel element exists."""
    html = _template()
    assert 'id="info-panel"' in html, "Missing #info-panel element"


def test_info_profile_map_present():
    """INFO-02: The three current profile keys are defined in the template."""
    html = _template()
    assert "family_friendly" in html
    assert "mixed_company" in html
    assert "close_friends" in html


def test_info_prose_sentences_present():
    """INFO-02: Each of the three profile prose descriptions is present."""
    html = _template()
    assert "Strict — kids in the room." in html
    assert "Around coworkers or guests." in html
    assert "Permissive — your inner circle." in html
