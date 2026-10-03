#!/usr/bin/env python3
"""Read the Room — Content filtering orchestrator.

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
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from profiles import DEFAULT_PROFILE, derive_verdict

if TYPE_CHECKING:
    from sentiment_cache import SentimentCache
    from sentiment_service import SentimentService, SongAnalysis
    from track_cache import TrackCache

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
                   # | 'sentiment' (LLM decline) | 'needs_review'
    severity: int  # 0-3 (0=none, 1=mild, 2=moderate, 3=severe)
    explicit: bool = field(default=False)
    profanity: bool = field(default=False)
    drug_reference: bool = field(default=False)
    sexual_content: bool = field(default=False)
    needs_review: bool = field(default=False)


class ContentChecker:
    """Five-tier content filter.

    Args:
        lyrics_service: LyricsService instance. None until wired.
        profanity_scanner: ProfanityScanner instance. None until wired.
        drug_scanner: DrugScanner instance (DRUG-03). None disables drug scan.
        sexual_content_scanner: SexualContentScanner instance (SEXL-04). None disables sexual scan.
        min_severity: Minimum profanity severity level to trigger skip (D-10).
            1=mild, 2=moderate (default), 3=severe only.
        explicit_skip: When True (default), tracks with Spotify's explicit=True flag are
            immediately skipped (Tier 1). When False, Tier 1 is bypassed (D-16).
    """

    def __init__(
        self,
        lyrics_service=None,
        profanity_scanner=None,
        drug_scanner=None,
        sexual_content_scanner=None,
        min_severity: int = 2,
        explicit_skip: bool = True,   # D-16: when False, Tier 1 explicit check is bypassed
        track_cache: "TrackCache | None" = None,  # D-05: injected seam, None disables caching
        sentiment_service: "SentimentService | None" = None,
        sentiment_cache: "SentimentCache | None" = None,
        active_profile: str = DEFAULT_PROFILE,
    ) -> None:
        self.lyrics_service = lyrics_service
        self.profanity_scanner = profanity_scanner
        self.drug_scanner = drug_scanner
        self.sexual_content_scanner = sexual_content_scanner
        self.min_severity = min_severity
        self.explicit_skip = explicit_skip
        self.track_cache = track_cache
        # LLM sentiment tier (v1.9). When sentiment_service is set, check() routes
        # through the LLM pipeline (per-category cache + profile verdict derived in
        # code) instead of the legacy keyword-decision pipeline.
        self.sentiment_service = sentiment_service
        self.sentiment_cache = sentiment_cache
        self.active_profile = active_profile

    async def check(self, track: dict, on_stage=None) -> "TrackEvalResult":
        """Check a track against content filter rules.

        Cache fast-path: if track_cache is set and the track is already cached,
        returns the cached result immediately without running the pipeline (D-06).

        Args:
            track: Spotify track object from currently_playing() API response.
                   Must contain: id, name, artists, explicit fields.
            on_stage: optional callback(stage: str) invoked at the start of each
                   I/O step of the sentiment pipeline ("lyrics", "llm") — purely
                   an in-flight progress signal for the caller to surface (e.g.
                   as a UI badge update); has no effect on the result.

        Returns:
            TrackEvalResult with fields:
            - action: 'skip' or 'allow'
            - reason: 'explicit' | 'profanity' | 'instrumental' |
                      'clean' | 'lyrics_unavailable' | 'no_lyrics_service' |
                      'drug_reference' | 'sexual_content'
            - severity: 0-3 (0=none, 1=mild, 2=moderate, 3=severe)
        """
        # LLM sentiment pipeline (v1.9) takes over when a service is wired. It has
        # its own per-category cache and derives the profile verdict in code, so it
        # bypasses track_cache (which stores a profile-coupled final action).
        if self.sentiment_service is not None:
            return await self._run_sentiment_pipeline(track, on_stage=on_stage)

        # Cache fast-path (D-06 step 1) — runs before Tier 1
        if self.track_cache is not None:
            cached = await self.track_cache.get(track["id"])
            if cached is not None:
                return cached

        # Run the full five-tier pipeline
        result = await self._run_pipeline(track)

        # Cache write after pipeline completes (D-06 step 3)
        if self.track_cache is not None:
            await self.track_cache.put(track["id"], result)
        return result

    async def _run_sentiment_pipeline(self, track: dict, on_stage=None) -> "TrackEvalResult":
        """LLM content pipeline (v1.9). See CLAUDE.md / the plan for the flow:

          1. explicit flag ....... obvious decline, no LLM (respects explicit_skip)
          2. sentiment_cache hit .. derive the active profile's verdict, no LLM
          3. lyrics fetch ......... instrumental → allow; no lyrics → needs_review
                                    (the LLM is NEVER called without lyrics)
          4. evaluate ............. failure/unknown → needs_review (not cached);
                                    else cache the analysis + derive the verdict

        Keyword scanners are intentionally NOT used as a decision gate here: they
        can't tell slur-as-slur from cultural register (the exact call the LLM
        exists to make), so gating on them would misfire. The only pre-LLM decline
        is the explicit flag. Cost is bounded by the permanent per-track cache.
        """
        track_name = track.get("name", "unknown")
        artist_name = track["artists"][0]["name"] if track.get("artists") else "unknown"
        track_id = track["id"]

        # Tier 1: explicit flag — instant decline, no LLM (FF only; MC/CF pass it on).
        if self.explicit_skip and track.get("explicit", False):
            log.debug("[SENTIMENT] track=%r explicit → skip", track_name)
            return TrackEvalResult(action="skip", reason="explicit", severity=3, explicit=True)

        # Tier 2: per-category cache — hit means we NEVER re-run the LLM (the core
        # "already analyzed, don't recompute" guarantee). Verdict derived in code.
        if self.sentiment_cache is not None:
            analysis = await self.sentiment_cache.get(
                track_id,
                rubric_version=self.sentiment_service.rubric_version,
                model_id=self.sentiment_service.provider.model_id,
            )
            if analysis is not None:
                log.debug("[SENTIMENT] track=%r cache hit", track_name)
                return self._result_from_analysis(analysis)

        # Tier 3: lyrics — required for the LLM (spike lock: no LLM on title only).
        if self.lyrics_service is None:
            log.warning("[SENTIMENT] track=%r no lyrics_service → needs_review", track_name)
            return self._review_result(action="allow", reason="no_lyrics_service")

        if on_stage is not None:
            on_stage("lyrics")
        lyrics_result = await self.lyrics_service.get_lyrics(
            track_id=track_id, track_name=track_name, artist_name=artist_name
        )
        if lyrics_result.instrumental:
            return TrackEvalResult(action="allow", reason="instrumental", severity=0)
        if lyrics_result.lyrics is None:
            log.debug("[SENTIMENT] track=%r no lyrics → needs_review", track_name)
            return self._review_result(action="allow", reason="needs_review")

        # Tier 4: LLM evaluation.
        if on_stage is not None:
            on_stage("llm")
        analysis = await self.sentiment_service.evaluate(
            track_id, track_name, artist_name, lyrics_result.lyrics
        )
        if analysis is None:
            # Transient failure — allow (don't skip music we couldn't assess) and
            # flag for review. Not cached, so it re-evaluates next play.
            log.warning("[SENTIMENT] track=%r eval failed → needs_review", track_name)
            return self._review_result(action="allow", reason="needs_review")
        if analysis.confidence == "unknown":
            # Model couldn't ground its answer despite lyrics — fail-safe decline +
            # review, and do NOT cache an ungrounded analysis (spike lock).
            log.warning("[SENTIMENT] track=%r confidence=unknown → skip+review", track_name)
            return self._review_result(action="skip", reason="needs_review")

        # Cache the profile-agnostic analysis, then derive this profile's verdict.
        if self.sentiment_cache is not None:
            await self.sentiment_cache.put(track_id, analysis)
        return self._result_from_analysis(analysis)

    def _result_from_analysis(self, analysis: "SongAnalysis") -> "TrackEvalResult":
        """Derive the active profile's verdict from a cached/fresh analysis and map
        it onto a TrackEvalResult, surfacing category booleans for the UI badges."""
        verdict = derive_verdict(analysis, self.active_profile)
        skip = verdict == "decline"
        return TrackEvalResult(
            action="skip" if skip else "allow",
            reason="sentiment" if skip else "clean",
            severity=3 if skip else 0,
            profanity=analysis.language.severity != "none",
            drug_reference=analysis.drug_references.severity != "none",
            sexual_content=analysis.sexual.severity != "none",
        )

    @staticmethod
    def _review_result(action: str, reason: str) -> "TrackEvalResult":
        """A result flagged for the manual-review queue (v1 just sets the flag)."""
        return TrackEvalResult(
            action=action, reason=reason, severity=0, needs_review=True
        )

    async def _run_pipeline(self, track: dict) -> "TrackEvalResult":
        """Execute the five-tier content filter pipeline.

        Contains the unchanged pipeline body — all existing scan logic, logging,
        and return values are preserved verbatim.
        """
        track_name = track.get("name", "unknown")
        artist_name = track["artists"][0]["name"] if track.get("artists") else "unknown"

        # Tier 1: Spotify explicit flag (FILT-01)
        # Instant check — no network call required.
        if self.explicit_skip and track.get("explicit", False):
            log.debug(
                "[SCAN] track=%r artist=%r severity=3 matched=[] action=skip",
                track_name,
                artist_name,
            )
            return TrackEvalResult(action="skip", reason="explicit", severity=3, explicit=True)

        # Tier 2+: Lyrics fetch + content scan pipeline.
        # Activates whenever lyrics_service is available; individual scanners
        # (profanity, drug, sexual) are invoked conditionally on their own non-None check.
        if self.lyrics_service is not None:
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

            # FILT-05: Lyrics unavailable = scan title+artist before falling back
            if lyrics_result.lyrics is None:
                scan_text = f"{track_name} {artist_name}"

                # Run all enabled scanners against the title+artist string (no short-circuit)
                title_severity, title_prof_matched = 0, []
                if self.profanity_scanner is not None:
                    title_severity, title_prof_matched = self.profanity_scanner.scan(scan_text)

                title_drug_detected, title_drug_matched = False, []
                if self.drug_scanner is not None:
                    title_drug_detected, title_drug_matched = self.drug_scanner.scan(scan_text)

                title_sexual_detected, title_sexual_matched = False, []
                if self.sexual_content_scanner is not None:
                    title_sexual_detected, title_sexual_matched = self.sexual_content_scanner.scan(scan_text)

                # Priority: profanity > drug > sexual
                if title_severity >= self.min_severity:
                    title_action, title_reason = "skip", "profanity"
                elif title_drug_detected:
                    title_action, title_reason = "skip", "drug_reference"
                elif title_sexual_detected:
                    title_action, title_reason = "skip", "sexual_content"
                else:
                    title_action, title_reason = "allow", "lyrics_unavailable"

                log.debug(
                    "[SCAN] track=%r artist=%r title_fallback=True severity=%d action=%s",
                    track_name,
                    artist_name,
                    title_severity,
                    title_action,
                )
                return TrackEvalResult(
                    action=title_action,
                    reason=title_reason,
                    severity=title_severity,
                    profanity=(title_severity >= self.min_severity),
                    drug_reference=title_drug_detected,
                    sexual_content=title_sexual_detected,
                )

            # Tiers 3-5: Run ALL enabled scanners — no short-circuit (Success Criteria 3)
            severity, prof_matched = 0, []
            if self.profanity_scanner is not None:
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
