"""Tests for ContentChecker pipeline integration — DRUG-03, SEXL-04."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from content_checker import ContentChecker, TrackEvalResult


def _make_track(track_id="t1", name="Test", artist="Artist", explicit=False):
    return {
        "id": track_id,
        "name": name,
        "artists": [{"name": artist}],
        "explicit": explicit,
    }


def _make_lyrics_result(lyrics=None, instrumental=False):
    result = MagicMock()
    result.lyrics = lyrics
    result.instrumental = instrumental
    return result


@pytest.fixture
def checker_with_scanners():
    """ContentChecker with all three scanners wired in."""
    lyrics_service = MagicMock()
    profanity_scanner = MagicMock()
    profanity_scanner.scan.return_value = (0, [])   # clean by default
    drug_scanner = MagicMock()
    drug_scanner.scan.return_value = (False, [])    # clean by default
    sexual_scanner = MagicMock()
    sexual_scanner.scan.return_value = (False, [])  # clean by default
    checker = ContentChecker(
        lyrics_service=lyrics_service,
        profanity_scanner=profanity_scanner,
        drug_scanner=drug_scanner,
        sexual_content_scanner=sexual_scanner,
        min_severity=2,
    )
    return checker, lyrics_service, profanity_scanner, drug_scanner, sexual_scanner


@pytest.mark.asyncio
async def test_clean_track_allowed(checker_with_scanners):
    checker, lyrics_svc, prof, drug, sexual = checker_with_scanners
    lyrics_svc.get_lyrics = AsyncMock(return_value=_make_lyrics_result("la la la"))
    result = await checker.check(_make_track())
    assert result.action == "allow"
    assert result.reason == "clean"
    assert result.explicit == False
    assert result.profanity == False
    assert result.drug_reference == False
    assert result.sexual_content == False


@pytest.mark.asyncio
async def test_drug_reference_triggers_skip(checker_with_scanners):
    checker, lyrics_svc, prof, drug, sexual = checker_with_scanners
    lyrics_svc.get_lyrics = AsyncMock(return_value=_make_lyrics_result("cocaine in the lyrics"))
    drug.scan.return_value = (True, ["cocaine"])
    result = await checker.check(_make_track())
    assert result.action == "skip"
    assert result.reason == "drug_reference"
    assert result.drug_reference == True
    assert result.sexual_content == False
    assert result.profanity == False
    assert result.explicit == False


@pytest.mark.asyncio
async def test_sexual_content_triggers_skip(checker_with_scanners):
    checker, lyrics_svc, prof, drug, sexual = checker_with_scanners
    lyrics_svc.get_lyrics = AsyncMock(return_value=_make_lyrics_result("sexual content in lyrics"))
    sexual.scan.return_value = (True, ["sex"])
    result = await checker.check(_make_track())
    assert result.action == "skip"
    assert result.reason == "sexual_content"
    assert result.sexual_content == True
    assert result.drug_reference == False
    assert result.profanity == False
    assert result.explicit == False


@pytest.mark.asyncio
async def test_profanity_only_triggers_skip(checker_with_scanners):
    checker, lyrics_svc, prof, drug, sexual = checker_with_scanners
    lyrics_svc.get_lyrics = AsyncMock(return_value=_make_lyrics_result("damn this song"))
    prof.scan.return_value = (3, ["damn"])
    result = await checker.check(_make_track())
    assert result.action == "skip"
    assert result.reason == "profanity"
    assert result.profanity == True
    assert result.drug_reference == False
    assert result.sexual_content == False
    assert result.explicit == False


@pytest.mark.asyncio
async def test_all_signals_fire_all_scans_run(checker_with_scanners):
    """All three scanners run even when profanity fires — no short-circuit (Success Criteria 3)."""
    checker, lyrics_svc, prof, drug, sexual = checker_with_scanners
    lyrics_svc.get_lyrics = AsyncMock(return_value=_make_lyrics_result("damn cocaine sex"))
    prof.scan.return_value = (3, ["damn"])
    drug.scan.return_value = (True, ["cocaine"])
    sexual.scan.return_value = (True, ["sex"])
    result = await checker.check(_make_track())
    assert result.action == "skip"
    # All three scan() methods must have been called — no short-circuit allowed
    prof.scan.assert_called_once()
    drug.scan.assert_called_once()
    sexual.scan.assert_called_once()
    # All three signals were detected — all three booleans must be True (D-02)
    assert result.profanity == True
    assert result.drug_reference == True
    assert result.sexual_content == True
    assert result.explicit == False


@pytest.mark.asyncio
async def test_explicit_track_sets_explicit_boolean():
    """Tier 1 explicit path sets explicit=True, all other booleans False (D-01, D-02)."""
    checker = ContentChecker(min_severity=2)  # no scanners — won't reach Tier 2+
    result = await checker.check(_make_track(explicit=True))
    assert result.action == "skip"
    assert result.reason == "explicit"
    assert result.explicit == True
    assert result.profanity == False
    assert result.drug_reference == False
    assert result.sexual_content == False


@pytest.mark.asyncio
async def test_scan_lines_logged_at_debug_not_info(checker_with_scanners, caplog):
    """[SCAN] log lines must be emitted at DEBUG level, not INFO (LOG-02 / D-11)."""
    import logging
    checker, lyrics_svc, prof, drug, sexual = checker_with_scanners
    lyrics_svc.get_lyrics = AsyncMock(return_value=_make_lyrics_result("la la la"))
    with caplog.at_level(logging.DEBUG, logger="content_checker"):
        await checker.check(_make_track())
    scan_records = [r for r in caplog.records if "[SCAN]" in r.message]
    assert len(scan_records) >= 1, "At least one [SCAN] log line must be emitted"
    for record in scan_records:
        assert record.levelno == logging.DEBUG, (
            f"[SCAN] line emitted at {record.levelname}, expected DEBUG: {record.message!r}"
        )


# ---------------------------------------------------------------------------
# Title-fallback scan tests (260404-avv)
# When lyrics are None (not instrumental), the pipeline must scan the track
# title+artist string before unconditionally allowing the track.
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_no_lyrics_clean_title_allows(checker_with_scanners):
    """Clean title with no lyrics returns action=allow, reason=lyrics_unavailable."""
    checker, lyrics_svc, prof, drug, sexual = checker_with_scanners
    lyrics_svc.get_lyrics = AsyncMock(return_value=_make_lyrics_result(lyrics=None))
    # All scanners return clean by default (fixture default)
    result = await checker.check(_make_track(name="Sunshine", artist="Artist"))
    assert result.action == "allow"
    assert result.reason == "lyrics_unavailable"


@pytest.mark.asyncio
async def test_no_lyrics_drug_title_skips(checker_with_scanners):
    """Drug term in title with no lyrics causes action=skip, reason=drug_reference."""
    checker, lyrics_svc, prof, drug, sexual = checker_with_scanners
    lyrics_svc.get_lyrics = AsyncMock(return_value=_make_lyrics_result(lyrics=None))
    drug.scan.return_value = (True, ["cocaine"])
    result = await checker.check(_make_track(name="Cocaine", artist="Artist"))
    assert result.action == "skip"
    assert result.reason == "drug_reference"
    assert result.drug_reference == True


@pytest.mark.asyncio
async def test_no_lyrics_sexual_title_skips(checker_with_scanners):
    """Sexual term in title with no lyrics causes action=skip, reason=sexual_content."""
    checker, lyrics_svc, prof, drug, sexual = checker_with_scanners
    lyrics_svc.get_lyrics = AsyncMock(return_value=_make_lyrics_result(lyrics=None))
    sexual.scan.return_value = (True, ["sex"])
    result = await checker.check(_make_track(name="Sex", artist="Artist"))
    assert result.action == "skip"
    assert result.reason == "sexual_content"
    assert result.sexual_content == True


@pytest.mark.asyncio
async def test_no_lyrics_profanity_title_skips(checker_with_scanners):
    """Profanity in title with no lyrics causes action=skip, reason=profanity."""
    checker, lyrics_svc, prof, drug, sexual = checker_with_scanners
    lyrics_svc.get_lyrics = AsyncMock(return_value=_make_lyrics_result(lyrics=None))
    prof.scan.return_value = (3, ["damn"])
    result = await checker.check(_make_track(name="Damn It", artist="Artist"))
    assert result.action == "skip"
    assert result.reason == "profanity"
    assert result.profanity == True


@pytest.mark.asyncio
async def test_no_lyrics_no_scanners_allows():
    """With no scanners wired, no-lyrics path still returns lyrics_unavailable allow."""
    lyrics_svc = MagicMock()
    lyrics_svc.get_lyrics = AsyncMock(return_value=_make_lyrics_result(lyrics=None))
    # profanity_scanner is None — no scan block entered at all
    checker = ContentChecker(lyrics_service=lyrics_svc, profanity_scanner=None)
    result = await checker.check(_make_track(name="Cocaine", artist="Artist"))
    assert result.action == "allow"
    assert result.reason == "no_lyrics_service"


@pytest.mark.asyncio
async def test_no_lyrics_scan_text_is_title_plus_artist(checker_with_scanners):
    """Scanner receives concatenated 'track_name artist_name' as scan text."""
    checker, lyrics_svc, prof, drug, sexual = checker_with_scanners
    lyrics_svc.get_lyrics = AsyncMock(return_value=_make_lyrics_result(lyrics=None))
    await checker.check(_make_track(name="MySong", artist="MyArtist"))
    expected_text = "MySong MyArtist"
    # All three scanners must have been called with the title+artist string
    prof.scan.assert_called_once_with(expected_text)
    drug.scan.assert_called_once_with(expected_text)
    sexual.scan.assert_called_once_with(expected_text)
