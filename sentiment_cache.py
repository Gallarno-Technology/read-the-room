#!/usr/bin/env python3
"""Read the Room — SentimentCache seam.

The durable "already analyzed, don't re-run the LLM" store the user asked for.
Keyed by Spotify track ID, it holds the profile-agnostic SongAnalysis so every
unique track is evaluated by the LLM exactly once, ever. Per-profile verdicts are
derived from the cached analysis at query time (profiles.derive_verdict), so the
cache survives profile redesigns.

Mirrors track_cache.py exactly (D-01..D-04):
  D-01: SentimentCache is an ABC so a test double / alternative backend can swap in.
  D-02: SQLiteSentimentCache uses the same lazy _db / _ensure_db open pattern.
  D-03: analysis_cache uses individual typed columns — no JSON blob.
  D-05: get() honours the rubric/model stamp — a row whose rubric_version or
        model_id no longer matches the caller's current config is treated as a
        cache MISS (stale analysis → re-evaluate), so a rubric bump invalidates
        old analyses without a migration.

Shares the same SQLite file as LyricsService / SQLiteTrackCache (lyrics_cache.db);
the analysis_cache table coexists alongside eval_results and the lyrics table.
"""
import abc
import time

import aiosqlite

from sentiment_service import CategoryRating, SongAnalysis

# ---------------------------------------------------------------------------
# SQLite DDL — individual typed columns per category (D-03).
# ---------------------------------------------------------------------------
CREATE_ANALYSIS_TABLE = """
CREATE TABLE IF NOT EXISTS analysis_cache (
    spotify_track_id        TEXT PRIMARY KEY,
    sexual_severity         TEXT NOT NULL,
    sexual_reason           TEXT NOT NULL DEFAULT '',
    drug_references_severity TEXT NOT NULL,
    drug_references_reason  TEXT NOT NULL DEFAULT '',
    violence_severity       TEXT NOT NULL,
    violence_reason         TEXT NOT NULL DEFAULT '',
    dark_themes_severity    TEXT NOT NULL,
    dark_themes_reason      TEXT NOT NULL DEFAULT '',
    language_severity       TEXT NOT NULL,
    language_reason         TEXT NOT NULL DEFAULT '',
    framing                 TEXT NOT NULL,
    confidence              TEXT NOT NULL,
    summary                 TEXT NOT NULL DEFAULT '',
    rubric_version          TEXT NOT NULL,
    model_id                TEXT NOT NULL,
    evaluated_at            REAL NOT NULL
);
"""

# Column order for SELECT/INSERT — kept in one place so the two stay in lockstep.
_COLUMNS = (
    "spotify_track_id",
    "sexual_severity", "sexual_reason",
    "drug_references_severity", "drug_references_reason",
    "violence_severity", "violence_reason",
    "dark_themes_severity", "dark_themes_reason",
    "language_severity", "language_reason",
    "framing", "confidence", "summary",
    "rubric_version", "model_id", "evaluated_at",
)


# ---------------------------------------------------------------------------
# Abstract interface — D-01 / D-02
# ---------------------------------------------------------------------------
class SentimentCache(abc.ABC):
    """Abstract interface for a per-track SongAnalysis cache."""

    @abc.abstractmethod
    async def get(
        self, track_id: str, rubric_version: str | None = None, model_id: str | None = None
    ) -> SongAnalysis | None:
        """Return the cached SongAnalysis for track_id, or None on miss.

        When rubric_version and/or model_id are given, a stored row whose stamp
        differs is treated as a MISS (stale → re-evaluate)."""
        ...

    @abc.abstractmethod
    async def put(self, track_id: str, analysis: SongAnalysis) -> None:
        """Store analysis keyed by track_id, replacing any previous entry."""
        ...


# ---------------------------------------------------------------------------
# SQLite implementation — D-03 / D-05
# ---------------------------------------------------------------------------
class SQLiteSentimentCache(SentimentCache):
    """Persistent SongAnalysis cache backed by an SQLite analysis_cache table.

    Mirrors SQLiteTrackCache: connection opened lazily on first use so the
    constructor stays synchronous.

    Args:
        db_path: Path to the SQLite file. Use ":memory:" in tests.
    """

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._db: aiosqlite.Connection | None = None

    async def _ensure_db(self) -> aiosqlite.Connection:
        """Lazily open the connection and create the analysis_cache table."""
        if self._db is None:
            db = await aiosqlite.connect(self.db_path)
            try:
                await db.executescript(CREATE_ANALYSIS_TABLE)
            except Exception:
                await db.close()
                raise
            self._db = db
        return self._db

    async def get(
        self, track_id: str, rubric_version: str | None = None, model_id: str | None = None
    ) -> SongAnalysis | None:
        """Return the cached SongAnalysis for track_id, or None on cache miss.

        A row whose rubric_version or model_id no longer matches the requested
        stamp is a miss (D-05). Parameterized query prevents SQL injection.
        """
        db = await self._ensure_db()
        async with db.execute(
            f"SELECT {', '.join(_COLUMNS[1:])} FROM analysis_cache WHERE spotify_track_id = ?",
            (track_id,),
        ) as cursor:
            row = await cursor.fetchone()

        if row is None:
            return None

        (
            sexual_sev, sexual_reason,
            drug_sev, drug_reason,
            violence_sev, violence_reason,
            dark_sev, dark_reason,
            lang_sev, lang_reason,
            framing, confidence, summary,
            row_rubric, row_model, evaluated_at,
        ) = row

        # D-05: stale-stamp rows are a miss so a rubric/model bump forces re-eval.
        if rubric_version is not None and row_rubric != rubric_version:
            return None
        if model_id is not None and row_model != model_id:
            return None

        return SongAnalysis(
            sexual=CategoryRating(sexual_sev, sexual_reason),
            drug_references=CategoryRating(drug_sev, drug_reason),
            violence=CategoryRating(violence_sev, violence_reason),
            dark_themes=CategoryRating(dark_sev, dark_reason),
            language=CategoryRating(lang_sev, lang_reason),
            framing=framing,
            confidence=confidence,
            summary=summary,
            model_id=row_model,
            rubric_version=row_rubric,
            evaluated_at=evaluated_at,
        )

    async def put(self, track_id: str, analysis: SongAnalysis) -> None:
        """Store analysis keyed by track_id, replacing any existing entry.

        evaluated_at falls back to wall-clock time if the analysis carries none.
        Parameterized query prevents SQL injection via track_id.
        """
        db = await self._ensure_db()
        placeholders = ", ".join("?" for _ in _COLUMNS)
        await db.execute(
            f"INSERT OR REPLACE INTO analysis_cache ({', '.join(_COLUMNS)}) VALUES ({placeholders})",
            (
                track_id,
                analysis.sexual.severity, analysis.sexual.reason,
                analysis.drug_references.severity, analysis.drug_references.reason,
                analysis.violence.severity, analysis.violence.reason,
                analysis.dark_themes.severity, analysis.dark_themes.reason,
                analysis.language.severity, analysis.language.reason,
                analysis.framing,
                analysis.confidence,
                analysis.summary,
                analysis.rubric_version,
                analysis.model_id,
                analysis.evaluated_at or time.time(),
            ),
        )
        await db.commit()

    async def close(self) -> None:
        """Close the database connection, mirroring SQLiteTrackCache.close()."""
        if self._db is not None:
            await self._db.close()
            self._db = None
