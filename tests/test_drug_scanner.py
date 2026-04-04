"""Tests for DrugScanner — DRUG-01, DRUG-02."""
import pytest
from drug_scanner import DrugScanner, DRUG_TERMS


@pytest.fixture
def scanner():
    return DrugScanner()


def test_drug_scanner_detects_cocaine(scanner):
    """DrugScanner.scan() returns (True, list containing 'cocaine') for cocaine reference."""
    lyrics = "she snorted cocaine off the mirror"
    detected, matched = scanner.scan(lyrics)
    assert detected is True
    assert "cocaine" in matched


def test_drug_scanner_detects_heroin(scanner):
    """DrugScanner.scan() returns (True, list containing 'heroin') for heroin reference."""
    detected, matched = scanner.scan("a heroin addict on the street")
    assert detected is True
    assert "heroin" in matched


def test_drug_scanner_detects_meth(scanner):
    """DrugScanner.scan() returns (True, list containing 'meth') for meth reference."""
    detected, matched = scanner.scan("he bought meth from the dealer")
    assert detected is True
    assert "meth" in matched


def test_drug_scanner_detects_crystal_meth(scanner):
    """DrugScanner.scan() returns (True, list containing 'crystal meth') for crystal meth phrase."""
    detected, matched = scanner.scan("they were smoking crystal meth")
    assert detected is True
    assert "crystal meth" in matched


def test_drug_scanner_detects_coke(scanner):
    """DrugScanner.scan() returns (True, list containing 'coke') for coke reference."""
    detected, matched = scanner.scan("rail of coke on the table")
    assert detected is True
    assert "coke" in matched


def test_drug_scanner_case_insensitive(scanner):
    """DrugScanner.scan() matches drug terms regardless of case (D-13)."""
    detected, matched = scanner.scan("COCAINE everywhere")
    assert detected is True
    assert len(matched) > 0


def test_drug_scanner_punctuation_adjacent(scanner):
    """DrugScanner.scan() matches drug terms adjacent to punctuation."""
    detected, matched = scanner.scan("cocaine, was everywhere")
    assert detected is True
    assert len(matched) > 0


def test_drug_scanner_no_match_methadone(scanner):
    """'meth' must not match inside 'methadone' — word-boundary enforcement (D-13)."""
    detected, matched = scanner.scan("he took methadone daily")
    assert detected is False, f"'meth' must not match inside 'methadone', got matched={matched!r}"
    assert matched == []


def test_drug_scanner_clean_lyrics(scanner):
    """DrugScanner.scan() returns (False, []) for clean lyrics with no drug terms."""
    detected, matched = scanner.scan("I love you and the music plays on and on")
    assert detected is False
    assert matched == []


def test_drug_scanner_return_type(scanner):
    """DrugScanner.scan() returns (bool, list) — not (int, list) (DRUG-02)."""
    detected, matched = scanner.scan("something cocaine here")
    assert isinstance(detected, bool), f"Expected bool, got {type(detected)}"
    assert isinstance(matched, list), f"Expected list, got {type(matched)}"


@pytest.mark.parametrize("song_lyrics", [
    "had high hopes shooting for the stars climbed every mountain",
    "here comes the sun little darling its been a long cold lonely winter",
    "puff the magic dragon lived by the sea and frolicked in the autumn mist",
])
def test_drug_scanner_false_positive_guard_songs(scanner, song_lyrics):
    """Guard songs must return (False, []) — no drug false positives (D-05)."""
    detected, matched = scanner.scan(song_lyrics)
    assert detected is False, f"False positive on guard song: matched={matched!r}"
    assert matched == []
