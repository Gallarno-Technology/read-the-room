#!/usr/bin/env python3
"""Content filtering orchestrator for Spotify Family Safe Mode (Phase 2).

Implements a five-tier filter pipeline:
  Tier 1: Spotify explicit flag (instant — no API call needed)
  Tier 2: LRCLIB lyrics fetch (cache-first, then API)
  Tier 3: Profanity scan with severity scoring
  Tier 4: Drug reference scan (DRUG-03)
  Tier 5: Sexual content scan (SEXL-04)

Tiers 2 and 3 are stubbed in this plan (Plan 01) — the conditional check on
``self.lyrics_service is not None`` keeps them dormant until Plan 02 wires in
LyricsService and ProfanityScanner.
"""
import logging
from dataclasses import dataclass, field
from typing import Optional

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class TrackEvalResult:
    """Named result from ContentChecker.check().

    Replaces the positional (action, reason, severity) 3-tuple (PIPE-01).
    frozen=True enforces immutability and value-object semantics.
    The four boolean fields default to False for backward compatibility with
    existing test mocks that omit them (D-01, D-03).
    """
    action: str    # 'skip' | 'allow'
    reason: str    # 'explicit' | 'profanity' | 'instrumental' | 'clean'
                   # | 'lyrics_unavailable' | 'no_lyrics_service'
                   # | 'drug_reference' | 'sexual_content'
    severity: int  # 0-3 (0=none, 1=mild, 2=moderate, 3=severe)
    explicit: bool = field(default=False)
    profanity: bool = field(default=False)
    drug_reference: bool = field(default=False)
    sexual_content: bool = field(default=False)


class ContentChecker:
    """Five-tier content filter.

    Args:
        lyrics_service: LyricsService instance. None until wired.
        profanity_scanner: ProfanityScanner instance. None until wired.
        drug_scanner: DrugScanner instance (DRUG-03). None disables drug scan.
        sexual_content_scanner: SexualContentScanner instance (SEXL-04). None disables sexual scan.
        min_severity: Minimum profanity severity level to trigger skip (D-10).
            1=mild, 2=moderate (default), 3=severe only.
    """

    def __init__(
        self,
        lyrics_service=None,
        profanity_scanner=None,
        drug_scanner=None,
        sexual_content_scanner=None,
        min_severity: int = 2,
    ) -> None:
        self.lyrics_service = lyrics_service
        self.profanity_scanner = profanity_scanner
        self.drug_scanner = drug_scanner
        self.sexual_content_scanner = sexual_content_scanner
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
                      'clean' | 'lyrics_unavailable' | 'no_lyrics_service' |
                      'drug_reference' | 'sexual_content'
            - severity: 0-3 (0=none, 1=mild, 2=moderate, 3=severe)
        """
        track_name = track.get("name", "unknown")
        artist_name = track["artists"][0]["name"] if track.get("artists") else "unknown"

        # Tier 1: Spotify explicit flag (FILT-01)
        # Instant check — no network call required.
        if track.get("explicit", False):
            log.debug(
                "[SCAN] track=%r artist=%r severity=3 matched=[] action=skip",
                track_name,
                artist_name,
            )
            return TrackEvalResult(action="skip", reason="explicit", severity=3, explicit=True)

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
                log.debug(
                    "[SCAN] track=%r artist=%r severity=0 matched=[] action=allow reason=instrumental",
                    track_name,
                    artist_name,
                )
                return TrackEvalResult(action="allow", reason="instrumental", severity=0)

            # FILT-05: Lyrics unavailable = ambiguous, do NOT auto-skip
            if lyrics_result.lyrics is None:
                log.debug(
                    "[SCAN] track=%r artist=%r severity=0 matched=[] action=allow reason=lyrics_unavailable",
                    track_name,
                    artist_name,
                )
                return TrackEvalResult(action="allow", reason="lyrics_unavailable", severity=0)

            # Tiers 3-5: Run ALL scanners unconditionally — no short-circuit (Success Criteria 3)
            severity, prof_matched = self.profanity_scanner.scan(lyrics_result.lyrics)

            drug_detected, drug_matched = False, []
            if self.drug_scanner is not None:
                drug_detected, drug_matched = self.drug_scanner.scan(lyrics_result.lyrics)

            sexual_detected, sexual_matched = False, []
            if self.sexual_content_scanner is not None:
                sexual_detected, sexual_matched = self.sexual_content_scanner.scan(lyrics_result.lyrics)

            # Decision: priority order profanity > drug > sexual
            if severity >= self.min_severity:
                action, reason = "skip", "profanity"
            elif drug_detected:
                action, reason = "skip", "drug_reference"
            elif sexual_detected:
                action, reason = "skip", "sexual_content"
            else:
                action, reason = "allow", "clean"

            log.debug(
                "[SCAN] track=%r artist=%r severity=%d prof_matched=%s "
                "drug_matched=%s sexual_matched=%s action=%s",
                track_name,
                artist_name,
                severity,
                prof_matched,
                drug_matched,
                sexual_matched,
                action,
            )
            return TrackEvalResult(
                action=action,
                reason=reason,
                severity=severity,
                explicit=False,
                profanity=(severity >= self.min_severity),
                drug_reference=drug_detected,
                sexual_content=sexual_detected,
            )

        # No lyrics service configured yet (or failed to initialize) — allow non-explicit tracks.
        log.warning(
            "[SCAN] track=%r artist=%r severity=0 matched=[] action=allow reason=no_lyrics_service "
            "(lyrics pipeline not active — check LYRICS_DB_PATH and container logs)",
            track_name,
            artist_name,
        )
        return TrackEvalResult(action="allow", reason="no_lyrics_service", severity=0)
