"""Decision-logic regression suite for profiles.derive_verdict.

Feeds synthetic category rows for all 14 calibration anchors
(prompts/rubric_v2.md §Calibration anchors) into derive_verdict and asserts the
expected Family Friendly / Mixed Company / Close Friends verdicts. Pure logic —
no live LLM, no I/O.

FF "TD" (threshold-dependent) anchors are asserted as `decline`: every TD anchor
here carries content that trips a hard FF rule (sexual≥innuendo, drug≥casual,
violence≥narrative, or dark≥present), so the code's deterministic answer is
decline.
"""
import pytest

from profiles import (
    CLOSE_FRIENDS,
    DECLINE,
    FAMILY_FRIENDLY,
    MIXED_COMPANY,
    PASS,
    derive_verdict,
)
from sentiment_service import CategoryRating, SongAnalysis


def make(
    *,
    sexual="none",
    drug_references="none",
    violence="none",
    dark_themes="none",
    language="none",
    framing="neutral",
    confidence="known",
    language_reason="",
):
    """Build a SongAnalysis from concise severity kwargs."""
    return SongAnalysis(
        sexual=CategoryRating(sexual),
        drug_references=CategoryRating(drug_references),
        violence=CategoryRating(violence),
        dark_themes=CategoryRating(dark_themes),
        language=CategoryRating(language, language_reason),
        framing=framing,
        confidence=confidence,
    )


# name -> (analysis, (FF, MC, CF)) — the 14 calibration anchors.
ANCHORS = {
    "Blinding Lights": (
        make(),
        (PASS, PASS, PASS),
    ),
    "Promiscuous": (
        make(sexual="innuendo", framing="transactional"),
        (DECLINE, DECLINE, PASS),
    ),
    "WAP": (
        make(sexual="explicit", framing="objectifying"),
        (DECLINE, DECLINE, DECLINE),
    ),
    "Tears": (
        make(sexual="explicit"),
        (DECLINE, DECLINE, DECLINE),
    ),
    "Pumped Up Kicks": (
        make(violence="graphic"),
        (DECLINE, DECLINE, PASS),
    ),
    "Semi-Charmed Life": (
        make(drug_references="hard_drug", framing="cautionary"),
        (DECLINE, PASS, PASS),
    ),
    "Don't Threaten Me With a Good Time": (
        make(drug_references="hard_drug", framing="glorifying"),
        (DECLINE, DECLINE, PASS),
    ),
    "The Muffin Song": (
        make(dark_themes="prominent"),
        (DECLINE, DECLINE, PASS),
    ),
    "Brown Sugar": (
        make(sexual="innuendo", dark_themes="prominent", framing="objectifying"),
        (DECLINE, DECLINE, PASS),
    ),
    "Can't Tame Her": (
        make(framing="empowering"),
        (PASS, PASS, PASS),
    ),
    "Forget You": (
        make(language="mild"),
        (PASS, PASS, PASS),
    ),
    "House Tour": (
        make(sexual="innuendo"),
        (DECLINE, PASS, PASS),
    ),
    "Istanbul (Not Constantinople)": (
        make(),
        (PASS, PASS, PASS),
    ),
    "Elastic": (
        make(language="heavy", language_reason="n-word in cultural register, not slur-as-slur"),
        (DECLINE, PASS, PASS),
    ),
}


@pytest.mark.parametrize("name", list(ANCHORS))
def test_anchor_family_friendly(name):
    analysis, (ff, _mc, _cf) = ANCHORS[name]
    assert derive_verdict(analysis, FAMILY_FRIENDLY) == ff, f"{name} FF"


@pytest.mark.parametrize("name", list(ANCHORS))
def test_anchor_mixed_company(name):
    analysis, (_ff, mc, _cf) = ANCHORS[name]
    assert derive_verdict(analysis, MIXED_COMPANY) == mc, f"{name} MC"


@pytest.mark.parametrize("name", list(ANCHORS))
def test_anchor_close_friends(name):
    analysis, (_ff, _mc, cf) = ANCHORS[name]
    assert derive_verdict(analysis, CLOSE_FRIENDS) == cf, f"{name} CF"


# ---------------------------------------------------------------------------
# Fail-safe + migration behaviour
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("profile", [FAMILY_FRIENDLY, MIXED_COMPANY, CLOSE_FRIENDS])
def test_confidence_unknown_declines_everywhere(profile):
    """confidence=unknown is a fail-safe decline for every profile."""
    a = make(confidence="unknown")
    assert derive_verdict(a, profile) == DECLINE


def test_cultural_register_rescues_heavy_language_only_for_mc_and_cf():
    """Heavy language in cultural register passes MC/CF but FF still declines it."""
    a = make(language="heavy", language_reason="cultural register, not slur-as-slur")
    assert derive_verdict(a, FAMILY_FRIENDLY) == DECLINE
    assert derive_verdict(a, MIXED_COMPANY) == PASS
    assert derive_verdict(a, CLOSE_FRIENDS) == PASS


def test_heavy_language_as_slur_declines_mc_and_cf():
    """Heavy language WITHOUT the cultural-register marker is slur-as-slur → declines."""
    a = make(language="heavy", language_reason="repeated slur directed as an insult")
    assert derive_verdict(a, MIXED_COMPANY) == DECLINE
    assert derive_verdict(a, CLOSE_FRIENDS) == DECLINE


def test_unknown_profile_falls_back_to_strictest():
    """An unrecognized profile name is treated as Family Friendly (safety default)."""
    a = make(sexual="innuendo")  # only FF declines this
    assert derive_verdict(a, "nonsense") == DECLINE
