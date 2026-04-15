#!/usr/bin/env python3
"""Read the Room — TrackCache seam.

Defines the TrackCache abstract interface (CACHE-01) and the SQLiteTrackCache
default implementation (CACHE-02).  Other modules import from this file;
daemon.py will wire SQLiteTrackCache in a later plan.

Design decisions:
  D-01: TrackCache is an ABC so future implementations (e.g. in-memory test
        double, Redis) can be swapped without touching callers.
  D-02: SQLiteTrackCache mirrors the LyricsService lazy-open pattern exactly
        (same _db / _ensure_db convention) so the mental model is consistent.
  D-03: eval_results table uses individual columns — no JSON blob (D-04).
  D-04: Boolean fields are stored as INTEGER (SQLite has no BOOLEAN type) and
        reconstructed via bool() in get() so callers always receive Python bool.
"""
import abc
import time

import aiosqlite

from content_checker import TrackEvalResult

# ---------------------------------------------------------------------------
# SQLite DDL
# ---------------------------------------------------------------------------
CREATE_EVAL_TABLE = """
CREATE TABLE IF NOT EXISTS eval_results (
    spotify_track_id  TEXT PRIMARY KEY,
    action            TEXT NOT NULL,
    reason            TEXT NOT NULL,
    severity          INTEGER NOT NULL,
    explicit          INTEGER NOT NULL DEFAULT 0,
    profanity         INTEGER NOT NULL DEFAULT 0,
    drug_reference    INTEGER NOT NULL DEFAULT 0,
    sexual_content    INTEGER NOT NULL DEFAULT 0,
    cached_at         REAL NOT NULL
);
"""


# ---------------------------------------------------------------------------
# Abstract interface — CACHE-01 / D-02
# ---------------------------------------------------------------------------
class TrackCache(abc.ABC):
    """Abstract interface for a track-evaluation result cache.

    Concrete implementations must provide get() and put().
    Callers depend on this type; the daemon wires the concrete class.
    """

    @abc.abstractmethod
    async def get(self, track_id: str) -> TrackEvalResult | None:
        """Return the cached TrackEvalResult for track_id, or None on miss."""
        ...

    @abc.abstractmethod
    async def put(self, track_id: str, data: TrackEvalResult) -> None:
        """Store data keyed by track_id, replacing any previous entry."""
        ...


# ---------------------------------------------------------------------------
# SQLite implementation — CACHE-02 / D-03 / D-04
# ---------------------------------------------------------------------------
class SQLiteTrackCache(TrackCache):
    """Persistent TrackEvalResult cache backed by an SQLite eval_results table.

    Mirrors the LyricsService lazy-open pattern: the database connection is
    opened on first use, not in __init__, so the constructor is synchronous.

    Args:
        db_path: Path to the SQLite file.  Use ":memory:" in tests.
    """

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._db: aiosqlite.Connection | None = None

    async def _ensure_db(self) -> aiosqlite.Connection:
        """Lazily open the aiosqlite connection and create the eval_results table."""
        if self._db is None:
            self._db = await aiosqlite.connect(self.db_path)
            await self._db.executescript(CREATE_EVAL_TABLE)
        return self._db

    async def get(self, track_id: str) -> TrackEvalResult | None:
        """Return the cached result for track_id, or None on cache miss.

        Boolean columns are read as INTEGER by SQLite; bool() converts them
        back to Python bool so callers never receive bare 0/1 integers.
        Parameterized query prevents SQL injection via track_id.
        """
        db = await self._ensure_db()
        async with db.execute(
            """
            SELECT action, reason, severity,
                   explicit, profanity, drug_reference, sexual_content
            FROM eval_results
            WHERE spotify_track_id = ?
            """,
            (track_id,),
        ) as cursor:
            row = await cursor.fetchone()

        if row is None:
            return None

        return TrackEvalResult(
            action=row[0],
            reason=row[1],
            severity=row[2],
            explicit=bool(row[3]),
            profanity=bool(row[4]),
            drug_reference=bool(row[5]),
            sexual_content=bool(row[6]),
        )

    async def put(self, track_id: str, data: TrackEvalResult) -> None:
        """Store data keyed by track_id, replacing any existing entry.

        Booleans are cast to int() before storage (SQLite INTEGER).
        cached_at records wall-clock time for future TTL support.
        Parameterized query prevents SQL injection via track_id.
        """
        db = await self._ensure_db()
        await db.execute(
            """
            INSERT OR REPLACE INTO eval_results
                (spotify_track_id, action, reason, severity,
                 explicit, profanity, drug_reference, sexual_content, cached_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                track_id,
                data.action,
                data.reason,
                data.severity,
                int(data.explicit),
                int(data.profanity),
                int(data.drug_reference),
                int(data.sexual_content),
                time.time(),
            ),
        )
        await db.commit()

    async def close(self) -> None:
        """Close the database connection, mirroring LyricsService.close()."""
        if self._db is not None:
            await self._db.close()
            self._db = None
