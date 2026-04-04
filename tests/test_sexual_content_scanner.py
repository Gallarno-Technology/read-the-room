"""Tests for SexualContentScanner — SEXL-01, SEXL-02, SEXL-03."""
import pytest
from sexual_content_scanner import SexualContentScanner, SEXUAL_TERMS
from profanity_scanner import SEVERITY_MAP


def test_sexual_terms_disjoint_from_severity_map():
    """SEXUAL_TERMS must not overlap with SEVERITY_MAP keys (SEXL-03).

    This test MUST pass before any scanner behavior test is meaningful.
    If this fails, remove the overlapping terms from SEXUAL_TERMS —
    they are already covered by ProfanityScanner.
    """
    overlap = SEXUAL_TERMS & set(SEVERITY_MAP.keys())
    assert overlap == set(), (
        f"SEXUAL_TERMS overlaps with SEVERITY_MAP keys: {overlap!r}. "
        "Remove these from SEXUAL_TERMS — they are already covered by ProfanityScanner."
    )


@pytest.fixture
def scanner():
    return SexualContentScanner()


def test_sexual_scanner_detects_fornicate(scanner):
    """SexualContentScanner.scan() returns (True, ...) for fornicate reference."""
    detected, matched = scanner.scan("she wants to fornicate with him tonight")
    assert detected is True
    assert "fornicate" in matched


def test_sexual_scanner_detects_masturbate(scanner):
    """SexualContentScanner.scan() returns (True, ...) for masturbate reference."""
    detected, matched = scanner.scan("he tried to masturbate alone in the dark")
    assert detected is True
    assert "masturbate" in matched


def test_sexual_scanner_detects_fellatio(scanner):
    """SexualContentScanner.scan() returns (True, ...) for fellatio reference."""
    detected, matched = scanner.scan("performed oral fellatio on the stage")
    assert detected is True
    assert "fellatio" in matched


def test_sexual_scanner_detects_penis(scanner):
    """SexualContentScanner.scan() returns (True, ...) for penis reference."""
    detected, matched = scanner.scan("his penis was visible through the fabric")
    assert detected is True
    assert "penis" in matched


def test_sexual_scanner_detects_vagina(scanner):
    """SexualContentScanner.scan() returns (True, ...) for vagina reference."""
    detected, matched = scanner.scan("her vagina ached from the cold")
    assert detected is True
    assert "vagina" in matched


def test_sexual_scanner_case_insensitive(scanner):
    """SexualContentScanner.scan() is case-insensitive."""
    detected, matched = scanner.scan("MASTURBATE right here in the lyrics")
    assert detected is True
    assert len(matched) > 0


def test_sexual_scanner_clean_lyrics(scanner):
    """SexualContentScanner.scan() returns (False, []) for clean lyrics."""
    detected, matched = scanner.scan("I love you and the music plays on and on")
    assert detected is False
    assert matched == []


def test_sexual_scanner_excludes_naked(scanner):
    """'naked' must NOT trigger detection — excluded per D-09."""
    detected, matched = scanner.scan("she was naked in the rain and danced freely")
    assert detected is False, f"'naked' should be excluded per D-09, got matched={matched!r}"
    assert matched == []


def test_sexual_scanner_return_type(scanner):
    """SexualContentScanner.scan() returns (bool, list)."""
    detected, matched = scanner.scan("fornicate here in this song")
    assert isinstance(detected, bool), f"Expected bool, got {type(detected)}"
    assert isinstance(matched, list), f"Expected list, got {type(matched)}"
