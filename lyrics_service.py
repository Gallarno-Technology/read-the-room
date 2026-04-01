#!/usr/bin/env python3
"""Lyrics service: LRCLIB fetch with SQLite cache.

Implements a two-layer lookup:
  1. SQLite cache (keyed by Spotify track ID) — served on repeat plays (FILT-06)
  2. LRCLIB API via lrclibapi — synchronous, wrapped in run_in_executor (Pitfall 3)

All LRCLIB failures are treated as "lyrics unavailable" — do not skip (FILT-05).
Instrumental tracks return instrumental=True (FILT-04).
"""
import asyncio
import logging
import re
import time
from dataclasses import dataclass, field

import aiosqlite
from lrclib import LrcLibAPI
from lrclib.exceptions import NotFoundError, APIError

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SQLite schema
# ---------------------------------------------------------------------------
CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS lyrics_cache (
    spotify_track_id TEXT PRIMARY KEY,
    track_name       TEXT NOT NULL,
    artist_name      TEXT NOT NULL,
    instrumental     INTEGER NOT NULL DEFAULT 0,
    plain_lyrics     TEXT,
    fetched_at       REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_fetched_at ON lyrics_cache(fetched_at);
"""

# Regex to strip LRC timestamp tags like [00:15.23] or [00:15.234]
_TIMESTAMP_RE = re.compile(r"\[\d{2}:\d{2}\.\d{2,3}\]\s*")


# ---------------------------------------------------------------------------
# Public data types
# ---------------------------------------------------------------------------
@dataclass
class LyricsResult:
    """Result of a lyrics lookup.

    Attributes:
        instrumental: True if LRCLIB says the track is instrumental (no lyrics expected).
        lyrics: Plain lyrics text, or None if unavailable.
        cached: True if served from SQLite cache (not a fresh LRCLIB fetch).
    """

    instrumental: bool
    lyrics: str | None
    cached: bool = field(default=False)


# ---------------------------------------------------------------------------
# LyricsService
# ---------------------------------------------------------------------------
class LyricsService:
    """Fetch and cache lyrics from LRCLIB.

    Args:
        db_path: Path to the SQLite database file for the lyrics cache.
    """

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._db: aiosqlite.Connection | None = None
        self._api = LrcLibAPI(user_agent="SpotifyFamilySafe/1.0")

    async def _ensure_db(self) -> aiosqlite.Connection:
        """Lazily open aiosqlite connection and create the lyrics_cache table."""
        if self._db is None:
            self._db = await aiosqlite.connect(self.db_path)
            await self._db.executescript(CREATE_TABLE)
        return self._db

    async def get_lyrics(
        self,
        track_id: str,
        track_name: str,
        artist_name: str,
    ) -> LyricsResult:
        """Fetch lyrics for a track, using the SQLite cache first.

        Args:
            track_id: Spotify track ID (used as the primary cache key).
            track_name: Human-readable track title (for LRCLIB query and cache).
            artist_name: Primary artist name (for LRCLIB query and cache).

        Returns:
            LyricsResult with instrumental/lyrics/cached set appropriately.
        """
        db = await self._ensure_db()

        # --- Cache lookup ---
        async with db.execute(
            "SELECT instrumental, plain_lyrics FROM lyrics_cache WHERE spotify_track_id = ?",
            (track_id,),
        ) as cursor:
            row = await cursor.fetchone()

        if row is not None:
            log.info("[CACHE] hit track_id=%s", track_id)
            return LyricsResult(
                instrumental=bool(row[0]),
                lyrics=row[1],
                cached=True,
            )

        # --- LRCLIB fetch (synchronous library → run_in_executor) ---
        loop = asyncio.get_event_loop()

        result = None
        try:
            # Try get_lyrics first using search_lyrics (which only requires track+artist).
            # search_lyrics returns a list sorted by relevance; take the first match.
            search_results = await loop.run_in_executor(
                None,
                lambda: self._api.search_lyrics(
                    track_name=track_name,
                    artist_name=artist_name,
                ),
            )
            if search_results:
                result = search_results[0]
        except (NotFoundError, APIError, Exception):
            log.warning(
                "[LRCLIB] fetch failed for %r by %r", track_name, artist_name
            )
            # Treat as lyrics unavailable (FILT-05)
            return LyricsResult(instrumental=False, lyrics=None, cached=False)

        # --- Handle LRCLIB response ---
        if result is None:
            # No results returned — lyrics unavailable (FILT-05)
            log.info(
                "[LRCLIB] not found track=%r artist=%r", track_name, artist_name
            )
            instrumental = False
            plain_lyrics: str | None = None
        elif result.instrumental:
            # FILT-04: Instrumental track — allow without scanning
            log.info(
                "[LRCLIB] fetched track=%r artist=%r instrumental=True has_lyrics=False",
                track_name,
                artist_name,
            )
            instrumental = True
            plain_lyrics = None
        else:
            # Try plain_lyrics first, fall back to extracting text from synced_lyrics
            if result.plain_lyrics:
                plain_lyrics = result.plain_lyrics
            elif result.synced_lyrics:
                # Strip LRC timestamp tags: [00:15.23] text → text
                plain_lyrics = _TIMESTAMP_RE.sub("", result.synced_lyrics).strip()
                if not plain_lyrics:
                    plain_lyrics = None
            else:
                # Both None/empty and not instrumental — FILT-05
                plain_lyrics = None

            instrumental = False
            log.info(
                "[LRCLIB] fetched track=%r artist=%r instrumental=False has_lyrics=%s",
                track_name,
                artist_name,
                plain_lyrics is not None,
            )

        # --- Cache result in SQLite ---
        await db.execute(
            """INSERT OR REPLACE INTO lyrics_cache
               (spotify_track_id, track_name, artist_name, instrumental, plain_lyrics, fetched_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (track_id, track_name, artist_name, int(instrumental), plain_lyrics, time.time()),
        )
        await db.commit()

        return LyricsResult(
            instrumental=instrumental,
            lyrics=plain_lyrics,
            cached=False,
        )

    async def close(self) -> None:
        """Close the aiosqlite connection."""
        if self._db is not None:
            await self._db.close()
            self._db = None
