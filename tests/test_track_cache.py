"""Unit tests for TrackCache ABC and SQLiteTrackCache.

Covers:
  CACHE-01: TrackCache abstract interface enforcement
  CACHE-02: SQLiteTrackCache round-trip correctness (all boolean variants, miss, overwrite)
  TEST-01:  DB coexistence with lyrics_cache table; instrumental edge case

asyncio_mode = "auto" in pyproject.toml — no @pytest.mark.asyncio needed.
"""
import pytest

from track_cache import SQLiteTrackCache, TrackCache
from content_checker import TrackEvalResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
async def cache():
    """In-memory SQLiteTrackCache — no tmp files, no cleanup complexity."""
    c = SQLiteTrackCache(db_path=":memory:")
    yield c
    await c.close()


# ---------------------------------------------------------------------------
# CACHE-01: Abstract interface enforcement
# ---------------------------------------------------------------------------

def test_abstract_interface_enforced():
    """Concrete subclass without implementations raises TypeError on instantiation."""

    class Concrete(TrackCache):
        pass

    with pytest.raises(TypeError):
        Concrete()


def test_abstract_interface_satisfied():
    """Concrete subclass with both methods implemented can be instantiated."""

    class FullConcrete(TrackCache):
        async def get(self, track_id: str) -> TrackEvalResult | None:
            return None

        async def put(self, track_id: str, data: TrackEvalResult) -> None:
            pass

    instance = FullConcrete()
    assert instance is not None


# ---------------------------------------------------------------------------
# CACHE-02: SQLiteTrackCache round-trip
# ---------------------------------------------------------------------------

async def test_round_trip_all_fields_true(cache):
    """All boolean flags set to True survive the SQLite INTEGER round-trip."""
    original = TrackEvalResult(
        action="skip",
        reason="profanity",
        severity=2,
        explicit=True,
        profanity=True,
        drug_reference=False,
        sexual_content=False,
    )
    await cache.put("track_abc", original)
    retrieved = await cache.get("track_abc")
    assert retrieved == original


async def test_round_trip_all_fields_false(cache):
    """All boolean flags set to False come back as False (not 0)."""
    original = TrackEvalResult(
        action="allow",
        reason="clean",
        severity=0,
        explicit=False,
        profanity=False,
        drug_reference=False,
        sexual_content=False,
    )
    await cache.put("track_xyz", original)
    retrieved = await cache.get("track_xyz")
    assert retrieved == original
    # Explicit type checks — must be bool, not int
    assert isinstance(retrieved.explicit, bool)
    assert isinstance(retrieved.profanity, bool)
    assert isinstance(retrieved.drug_reference, bool)
    assert isinstance(retrieved.sexual_content, bool)
    assert retrieved.explicit is False
    assert retrieved.profanity is False
    assert retrieved.drug_reference is False
    assert retrieved.sexual_content is False


async def test_cache_miss_returns_none(cache):
    """get() returns None for an unknown track_id."""
    result = await cache.get("nonexistent_track")
    assert result is None


async def test_put_overwrites_existing(cache):
    """put() with the same track_id replaces the stored value."""
    result_v1 = TrackEvalResult(
        action="skip",
        reason="explicit",
        severity=3,
        explicit=True,
        profanity=False,
        drug_reference=False,
        sexual_content=False,
    )
    result_v2 = TrackEvalResult(
        action="allow",
        reason="clean",
        severity=0,
        explicit=False,
        profanity=False,
        drug_reference=False,
        sexual_content=False,
    )
    await cache.put("t1", result_v1)
    await cache.put("t1", result_v2)
    retrieved = await cache.get("t1")
    assert retrieved == result_v2


# ---------------------------------------------------------------------------
# DB coexistence
# ---------------------------------------------------------------------------

async def test_db_coexistence_with_lyrics_cache(cache):
    """eval_results and lyrics_cache tables coexist in the same DB without conflict."""
    db = await cache._ensure_db()
    # Create the lyrics_cache table in the same connection (same in-memory DB)
    await db.executescript(
        """
        CREATE TABLE IF NOT EXISTS lyrics_cache (
            spotify_track_id TEXT PRIMARY KEY,
            track_name       TEXT NOT NULL,
            artist_name      TEXT NOT NULL,
            instrumental     INTEGER NOT NULL DEFAULT 0,
            plain_lyrics     TEXT,
            fetched_at       REAL NOT NULL
        );
        """
    )

    original = TrackEvalResult(
        action="skip",
        reason="drug_reference",
        severity=1,
        explicit=False,
        profanity=False,
        drug_reference=True,
        sexual_content=False,
    )
    await cache.put("coexist_track", original)
    retrieved = await cache.get("coexist_track")
    assert retrieved == original


# ---------------------------------------------------------------------------
# Instrumental edge case
# ---------------------------------------------------------------------------

async def test_instrumental_round_trip(cache):
    """Instrumental TrackEvalResult (all booleans False, severity=0) round-trips correctly."""
    original = TrackEvalResult(
        action="allow",
        reason="instrumental",
        severity=0,
        explicit=False,
        profanity=False,
        drug_reference=False,
        sexual_content=False,
    )
    await cache.put("instrumental_track_id", original)
    retrieved = await cache.get("instrumental_track_id")
    assert retrieved == original
    assert retrieved.reason == "instrumental"
    assert retrieved.severity == 0
