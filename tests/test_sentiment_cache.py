"""Unit tests for SentimentCache ABC and SQLiteSentimentCache.

Covers:
  - abstract interface enforcement
  - round-trip correctness (all fields survive get after put)
  - cache miss on unknown track
  - overwrite (put replaces a prior entry)
  - D-05: stale rubric_version / model_id → treated as MISS
  - coexistence with another table in the same shared DB file

asyncio_mode = "auto" in pyproject.toml — no @pytest.mark.asyncio needed.
"""
import pytest

from sentiment_cache import SentimentCache, SQLiteSentimentCache
from sentiment_service import CategoryRating, SongAnalysis


def analysis(**over):
    """A representative SongAnalysis; override individual fields via kwargs."""
    base = dict(
        sexual=CategoryRating("innuendo", "suggestive double entendre"),
        drug_references=CategoryRating("none", ""),
        violence=CategoryRating("none", ""),
        dark_themes=CategoryRating("prominent", "predatory/slavery imagery"),
        language=CategoryRating("none", ""),
        framing="objectifying",
        confidence="known",
        summary="Innuendo plus dark themes; declines MC, passes CF.",
        model_id="claude-haiku-4-5-20251001",
        rubric_version="v2",
        evaluated_at=1_700_000_000.0,
    )
    base.update(over)
    return SongAnalysis(**base)


@pytest.fixture
async def cache():
    c = SQLiteSentimentCache(db_path=":memory:")
    yield c
    await c.close()


# ---------------------------------------------------------------------------
# Abstract interface enforcement
# ---------------------------------------------------------------------------

def test_abstract_interface_enforced():
    class Concrete(SentimentCache):
        pass

    with pytest.raises(TypeError):
        Concrete()


def test_abstract_interface_satisfied():
    class FullConcrete(SentimentCache):
        async def get(self, track_id, rubric_version=None, model_id=None):
            return None

        async def put(self, track_id, analysis):
            pass

    FullConcrete()  # no raise


# ---------------------------------------------------------------------------
# Round-trip / miss / overwrite
# ---------------------------------------------------------------------------

async def test_miss_returns_none(cache):
    assert await cache.get("nope") is None


async def test_round_trip_preserves_all_fields(cache):
    a = analysis()
    await cache.put("track1", a)
    got = await cache.get("track1")

    assert got is not None
    assert got.sexual == CategoryRating("innuendo", "suggestive double entendre")
    assert got.drug_references.severity == "none"
    assert got.dark_themes == CategoryRating("prominent", "predatory/slavery imagery")
    assert got.framing == "objectifying"
    assert got.confidence == "known"
    assert got.summary == "Innuendo plus dark themes; declines MC, passes CF."
    assert got.model_id == "claude-haiku-4-5-20251001"
    assert got.rubric_version == "v2"
    assert got.evaluated_at == 1_700_000_000.0


async def test_put_overwrites_existing(cache):
    await cache.put("track1", analysis(summary="first"))
    await cache.put("track1", analysis(summary="second"))
    got = await cache.get("track1")
    assert got.summary == "second"


async def test_evaluated_at_defaults_to_now_when_zero(cache):
    await cache.put("track1", analysis(evaluated_at=0.0))
    got = await cache.get("track1")
    assert got.evaluated_at > 0.0


# ---------------------------------------------------------------------------
# D-05: stale-stamp rows are a miss
# ---------------------------------------------------------------------------

async def test_matching_stamp_is_a_hit(cache):
    await cache.put("track1", analysis())
    got = await cache.get("track1", rubric_version="v2", model_id="claude-haiku-4-5-20251001")
    assert got is not None


async def test_stale_rubric_version_is_a_miss(cache):
    await cache.put("track1", analysis(rubric_version="v2"))
    assert await cache.get("track1", rubric_version="v3") is None


async def test_stale_model_id_is_a_miss(cache):
    await cache.put("track1", analysis(model_id="claude-haiku-4-5-20251001"))
    assert await cache.get("track1", model_id="some-other-model") is None


async def test_no_stamp_args_ignores_stamp(cache):
    """get() without stamp args returns any stored row regardless of version."""
    await cache.put("track1", analysis(rubric_version="v1"))
    assert await cache.get("track1") is not None


# ---------------------------------------------------------------------------
# Coexistence with another table in the same DB file
# ---------------------------------------------------------------------------

async def test_coexists_with_other_table(cache):
    db = await cache._ensure_db()
    await db.execute("CREATE TABLE IF NOT EXISTS lyrics (track_id TEXT PRIMARY KEY, text TEXT)")
    await db.execute("INSERT INTO lyrics VALUES ('track1', 'la la la')")
    await db.commit()

    await cache.put("track1", analysis())
    got = await cache.get("track1")
    assert got is not None

    async with db.execute("SELECT text FROM lyrics WHERE track_id = 'track1'") as cur:
        row = await cur.fetchone()
    assert row[0] == "la la la"
