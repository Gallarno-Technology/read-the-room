#!/usr/bin/env python3
"""Content filtering orchestrator for Spotify Family Safe Mode (Phase 2).

Implements a three-tier filter pipeline:
  Tier 1: Spotify explicit flag (instant — no API call needed)
  Tier 2: LRCLIB lyrics fetch (cache-first, then API)
  Tier 3: Profanity scan with severity scoring

Tiers 2 and 3 are stubbed in this plan (Plan 01) — the conditional check on
``self.lyrics_service is not None`` keeps them dormant until Plan 02 wires in
LyricsService and ProfanityScanner.
"""
import logging
from dataclasses import dataclass
from typing import Optional

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class TrackEvalResult:
    """Named result from ContentChecker.check().

    Replaces the positional (action, reason, severity) 3-tuple (PIPE-01).
    frozen=True enforces immutability and value-object semantics.
    """
    action: str    # 'skip' | 'allow'
    reason: str    # 'explicit' | 'profanity' | 'instrumental' | 'clean'
                   # | 'lyrics_unavailable' | 'no_lyrics_service'
    severity: int  # 0-3 (0=none, 1=mild, 2=moderate, 3=severe)


class ContentChecker:
    """Three-tier content filter.

    Args:
        lyrics_service: LyricsService instance (Plan 02). None until wired.
        profanity_scanner: ProfanityScanner instance (Plan 02). None until wired.
        min_severity: Minimum profanity severity level to trigger skip (D-10).
            1=mild, 2=moderate (default), 3=severe only.
    """

    def __init__(
        self,
        lyrics_service=None,
        profanity_scanner=None,
        min_severity: int = 2,
    ) -> None:
        self.lyrics_service = lyrics_service
        self.profanity_scanner = profanity_scanner
        self.min_severity = min_severity

    async def check(self, track: dict) -> "TrackEvalResult":
        """Check a track against content filter rules.

        Args:
            track: Spotify track object from currently_playing() API response.
                   Must contain: id, name, artists, explicit fields.

        Returns:
            TrackEvalResult with fields:
            - action: 'skip' or 'allow'
            - reason: 'explicit' | 'profanity' | 'instrumental' |
                      'clean' | 'lyrics_unavailable' | 'no_lyrics_service'
            - severity: 0-3 (0=none, 1=mild, 2=moderate, 3=severe)
        """
        track_name = track.get("name", "unknown")
        artist_name = track["artists"][0]["name"] if track.get("artists") else "unknown"

        # Tier 1: Spotify explicit flag (FILT-01)
        # Instant check — no network call required.
        if track.get("explicit", False):
            log.info(
                "[SCAN] track=%r artist=%r severity=3 matched=[] action=skip",
                track_name,
                artist_name,
            )
            return TrackEvalResult(action="skip", reason="explicit", severity=3)

        # Tier 2 & 3: Lyrics fetch + profanity scan (Plan 02)
        # Only runs when both services are wired in — Plan 02 will inject them.
        if self.lyrics_service is not None and self.profanity_scanner is not None:
            lyrics_result = await self.lyrics_service.get_lyrics(
                track_id=track["id"],
                track_name=track_name,
                artist_name=artist_name,
            )

            # FILT-04: Instrumental tracks are allowed without scanning
            if lyrics_result.instrumental:
                log.info(
                    "[SCAN] track=%r artist=%r severity=0 matched=[] action=allow reason=instrumental",
                    track_name,
                    artist_name,
                )
                return TrackEvalResult(action="allow", reason="instrumental", severity=0)

            # FILT-05: Lyrics unavailable = ambiguous, do NOT auto-skip
            if lyrics_result.lyrics is None:
                log.info(
                    "[SCAN] track=%r artist=%r severity=0 matched=[] action=allow reason=lyrics_unavailable",
                    track_name,
                    artist_name,
                )
                return TrackEvalResult(action="allow", reason="lyrics_unavailable", severity=0)

            # Tier 3: Profanity scan (D-09)
            severity, matched = self.profanity_scanner.scan(lyrics_result.lyrics)
            if severity >= self.min_severity:
                action = "skip"
                reason = "profanity"
            else:
                action = "allow"
                reason = "clean"

            log.info(
                "[SCAN] track=%r artist=%r severity=%d matched=%s action=%s",
                track_name,
                artist_name,
                severity,
                matched,
                action,
            )
            return TrackEvalResult(action=action, reason=reason, severity=severity)

        # No lyrics service configured yet (or failed to initialize) — allow non-explicit tracks.
        log.warning(
            "[SCAN] track=%r artist=%r severity=0 matched=[] action=allow reason=no_lyrics_service "
            "(lyrics pipeline not active — check LYRICS_DB_PATH and container logs)",
            track_name,
            artist_name,
        )
        return TrackEvalResult(action="allow", reason="no_lyrics_service", severity=0)
