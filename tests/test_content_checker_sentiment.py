"""Tests for ContentChecker's v1.9 LLM sentiment pipeline.

Uses a fake SentimentService (no network) and a real in-memory
SQLiteSentimentCache so the cache-hit / don't-recompute behaviour is exercised
for real. Covers the explicit fast-path, cache hit (no LLM), profile
differentiation from one cached analysis, lyrics gating, and the review
fail-safes (eval failure, confidence=unknown).

asyncio_mode = "auto" — no @pytest.mark.asyncio needed.
"""
import time
import types

import pytest

from content_checker import ContentChecker
from profiles import CLOSE_FRIENDS, FAMILY_FRIENDLY
from sentiment_cache import SQLiteSentimentCache
from sentiment_provider import SentimentProvider
from sentiment_service import CategoryRating, SentimentService, SongAnalysis


def _track(track_id="t1", name="Song", artist="Artist", explicit=False):
    return {"id": track_id, "name": name, "artists": [{"name": artist}], "explicit": explicit}


def _lyrics(lyrics="all the other kids with the pumped up kicks", instrumental=False):
    r = types.SimpleNamespace()
    r.lyrics = lyrics
    r.instrumental = instrumental
    return r


def _analysis(confidence="known", model_id="fake-1", rubric_version="v2", **cats):
    base = dict(
        sexual=CategoryRating("none", ""),
        drug_references=CategoryRating("none", ""),
        violence=CategoryRating("graphic", "first-person shooter POV"),
        dark_themes=CategoryRating("none", ""),
        language=CategoryRating("none", ""),
        framing="neutral",
        confidence=confidence,
        summary="Graphic violence.",
        model_id=model_id,
        rubric_version=rubric_version,
        evaluated_at=1_700_000_000.0,
    )
    base.update(cats)
    return SongAnalysis(**base)


class FakeService:
    """Stands in for SentimentService: same surface ContentChecker touches."""

    def __init__(self, result, rubric_version="v2", model_id="fake-1"):
        self.rubric_version = rubric_version
        self.provider = types.SimpleNamespace(model_id=model_id)
        self._result = result
        self.calls = 0

    async def evaluate(self, track_id, title, artist, lyrics):
        self.calls += 1
        return self._result  # SongAnalysis, or None to model a backend failure


class FakeLyrics:
    def __init__(self, result):
        self._result = result
        self.calls = 0

    async def get_lyrics(self, track_id, track_name, artist_name):
        self.calls += 1
        return self._result


@pytest.fixture
async def cache():
    c = SQLiteSentimentCache(":memory:")
    yield c
    await c.close()


def _checker(service, cache=None, lyrics=None, profile=FAMILY_FRIENDLY, explicit_skip=True):
    return ContentChecker(
        lyrics_service=FakeLyrics(lyrics) if lyrics is not None else None,
        explicit_skip=explicit_skip,
        sentiment_service=service,
        sentiment_cache=cache,
        active_profile=profile,
    )


# ---------------------------------------------------------------------------
# Explicit fast-path
# ---------------------------------------------------------------------------

async def test_explicit_flag_skips_without_llm():
    svc = FakeService(_analysis())
    checker = _checker(svc, lyrics=_lyrics(), explicit_skip=True)
    res = await checker.check(_track(explicit=True))
    assert res.action == "skip" and res.reason == "explicit"
    assert svc.calls == 0  # no LLM


async def test_explicit_flag_passed_through_when_explicit_skip_false():
    """MC/CF (explicit_skip=False) send explicit-tagged tracks to the LLM."""
    svc = FakeService(_analysis(violence=CategoryRating("none", "")))  # clean → pass
    checker = _checker(svc, lyrics=_lyrics(), profile=CLOSE_FRIENDS, explicit_skip=False)
    res = await checker.check(_track(explicit=True))
    assert svc.calls == 1
    assert res.action == "allow"


# ---------------------------------------------------------------------------
# Cache: evaluate once, never again; derive verdict per profile
# ---------------------------------------------------------------------------

async def test_first_play_evaluates_and_caches(cache):
    svc = FakeService(_analysis())  # violence=graphic
    lyrics = _lyrics()
    checker = _checker(svc, cache=cache, lyrics=lyrics, profile=FAMILY_FRIENDLY)

    res = await checker.check(_track())
    assert res.action == "skip" and res.reason == "sentiment"  # FF declines graphic violence
    assert svc.calls == 1
    assert await cache.get("t1") is not None  # cached


async def test_second_play_is_cache_hit_no_llm_no_lyrics(cache):
    svc = FakeService(_analysis())
    lyrics = FakeLyrics(_lyrics())
    checker = ContentChecker(
        lyrics_service=lyrics, sentiment_service=svc, sentiment_cache=cache,
        active_profile=FAMILY_FRIENDLY,
    )
    await checker.check(_track())          # first play → evaluate + cache
    lyrics.calls = 0
    res = await checker.check(_track())     # second play → cache hit
    assert res.action == "skip"
    assert svc.calls == 1                    # NOT re-evaluated
    assert lyrics.calls == 0                 # no lyrics fetch on cache hit


async def test_profile_switch_reuses_cached_analysis(cache):
    """Same cached analysis → different verdict per profile, with no re-eval."""
    svc = FakeService(_analysis())  # violence=graphic: FF/MC decline, CF passes
    ff = _checker(svc, cache=cache, lyrics=_lyrics(), profile=FAMILY_FRIENDLY)
    assert (await ff.check(_track())).action == "skip"
    assert svc.calls == 1

    cf = _checker(svc, cache=cache, lyrics=_lyrics(), profile=CLOSE_FRIENDS)
    res = await cf.check(_track())
    assert res.action == "allow"     # CF is not a censor for graphic violence
    assert svc.calls == 1            # reused cache, no second eval


async def test_category_booleans_surface_for_badges(cache):
    svc = FakeService(_analysis(
        sexual=CategoryRating("innuendo", "x"),
        drug_references=CategoryRating("casual", "y"),
        language=CategoryRating("mild", "z"),
        violence=CategoryRating("none", ""),
    ))
    checker = _checker(svc, cache=cache, lyrics=_lyrics(), profile=CLOSE_FRIENDS)
    res = await checker.check(_track())
    assert res.sexual_content is True
    assert res.drug_reference is True
    assert res.profanity is True
    assert res.violence is False


async def test_violence_and_dark_themes_surface_for_badges(cache):
    """Violence/dark_themes weren't surfaced as booleans at all before — a
    sentiment-triggered skip for either showed only a generic 'Flagged:
    content' badge with no way to tell which category actually fired."""
    svc = FakeService(_analysis(
        violence=CategoryRating("graphic", "first-person shooter POV"),
        dark_themes=CategoryRating("explicit", "suicidal ideation"),
        sexual=CategoryRating("none", ""),
        drug_references=CategoryRating("none", ""),
        language=CategoryRating("none", ""),
        summary="Graphic violence and explicit dark themes.",
    ))
    checker = _checker(svc, cache=cache, lyrics=_lyrics(), profile=FAMILY_FRIENDLY)
    res = await checker.check(_track())
    assert res.action == "skip"
    assert res.violence is True
    assert res.dark_themes is True
    assert res.sexual_content is False
    assert res.drug_reference is False
    assert res.detail == "Graphic violence and explicit dark themes."


# ---------------------------------------------------------------------------
# Lyrics gating — the LLM is never called without lyrics
# ---------------------------------------------------------------------------

async def test_instrumental_allowed_without_llm():
    svc = FakeService(_analysis())
    checker = _checker(svc, lyrics=_lyrics(instrumental=True))
    res = await checker.check(_track())
    assert res.action == "allow" and res.reason == "instrumental"
    assert svc.calls == 0


async def test_no_lyrics_routes_to_review_without_llm():
    svc = FakeService(_analysis())
    checker = _checker(svc, lyrics=_lyrics(lyrics=None))
    res = await checker.check(_track())
    assert res.action == "allow" and res.reason == "needs_review"
    assert res.needs_review is True
    assert svc.calls == 0


async def test_no_lyrics_service_routes_to_review():
    svc = FakeService(_analysis())
    checker = _checker(svc, lyrics=None)  # no lyrics_service
    res = await checker.check(_track())
    assert res.needs_review is True
    assert svc.calls == 0


# ---------------------------------------------------------------------------
# Review fail-safes — not cached
# ---------------------------------------------------------------------------

async def test_eval_failure_allows_and_flags_review_not_cached(cache):
    # SentimentService.evaluate returns None on any backend failure (it catches
    # internally) — content_checker treats that as route-to-review.
    svc = FakeService(None)
    checker = _checker(svc, cache=cache, lyrics=_lyrics())
    res = await checker.check(_track())
    assert res.action == "allow" and res.needs_review is True
    assert await cache.get("t1") is None  # not cached → retried next play


async def test_confidence_unknown_declines_and_reviews_not_cached(cache):
    svc = FakeService(_analysis(confidence="unknown"))
    checker = _checker(svc, cache=cache, lyrics=_lyrics())
    res = await checker.check(_track())
    assert res.action == "skip" and res.needs_review is True  # fail-safe decline
    assert await cache.get("t1") is None  # ungrounded → not cached


# ---------------------------------------------------------------------------
# A hung (not failed) LLM call must still bound check() and degrade to review
# ---------------------------------------------------------------------------

class _SlowProvider(SentimentProvider):
    """Simulates a stalled network call through the REAL SentimentService —
    proves the timeout plumbing (not just the FakeService stand-in) actually
    bounds ContentChecker.check() end-to-end."""

    def __init__(self, delay):
        self._delay = delay

    @property
    def model_id(self):
        return "slow-model"

    def evaluate(self, system_prompt, user_message, schema):
        time.sleep(self._delay)
        return None  # never reached within the timeout anyway


async def test_hang_in_llm_provider_bounds_check_and_needs_review(cache, tmp_path):
    rubric = tmp_path / "rubric.md"
    rubric.write_text("RUBRIC TEXT")
    svc = SentimentService(provider=_SlowProvider(delay=0.3), rubric_path=rubric, timeout_seconds=0.05)
    checker = ContentChecker(
        lyrics_service=FakeLyrics(_lyrics()), sentiment_service=svc, sentiment_cache=cache,
        active_profile=FAMILY_FRIENDLY,
    )

    start = time.monotonic()
    res = await checker.check(_track())
    elapsed = time.monotonic() - start

    assert elapsed < 0.2, f"check() should be bounded by the service timeout, took {elapsed:.3f}s"
    assert res.action == "allow" and res.reason == "needs_review" and res.needs_review is True
    assert await cache.get("t1") is None  # timeout degrades like any other failure — not cached
