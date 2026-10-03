#!/usr/bin/env python3
"""Read the Room — LLM sentiment evaluator (Tier 4).

Pipes a song's lyrics through Claude Haiku 4.5 to produce a per-category content
analysis (the SongAnalysis dataclass). The analysis is intentionally
**profile-agnostic** — profiles.derive_verdict() turns it into a pass/decline at
query time, so switching profiles never requires re-evaluating a song.

Design (spike locks — see .planning/spikes/.../architectural-locks.md):
  - The LLM is NEVER called without lyrics. evaluate() short-circuits to None on
    empty lyrics so the caller routes the track to manual review.
  - The rubric (prompts/rubric_v2.md) is sent as the system prompt and structured
    output is forced by the provider, exactly as validated in spike 001.
  - Output stores per-category severity + framing + confidence, NOT per-profile
    verdicts (those are derived in code). The model's own `verdict` block is
    ignored — code owns the decision (profiles.derive_verdict).
  - The model itself is pluggable: SentimentService delegates the actual call to
    a SentimentProvider (sentiment_provider.py — the AI-backend seam). It defaults
    to AnthropicProvider but any conforming backend can be injected. The provider
    imports its SDK lazily, so this module imports cleanly with no SDK installed —
    tests and the pure profile logic never need one.
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

from sentiment_provider import DEFAULT_ANTHROPIC_MODEL, SentimentProvider

log = logging.getLogger(__name__)

DEFAULT_RUBRIC_VERSION = "v2"
_RUBRIC_PATH = Path(__file__).parent / "prompts" / "rubric_v2.md"

# ---------------------------------------------------------------------------
# Output schema — copied verbatim from spike 001 clients._output_schema so the
# production tool input_schema matches the benchmarked shape exactly.
# ---------------------------------------------------------------------------
SEVERITY_LEVELS = {
    "sexual":          ["none", "romantic", "innuendo", "explicit"],
    "drug_references": ["none", "casual", "hard_drug"],
    "violence":        ["none", "narrative", "graphic"],
    "dark_themes":     ["none", "present", "prominent"],
    "language":        ["none", "mild", "moderate", "heavy"],
}
FRAMING_VALUES = ["neutral", "empowering", "cautionary", "transactional", "glorifying", "objectifying"]
CONFIDENCE_VALUES = ["known", "inferred", "unknown"]

CATEGORY_NAMES = tuple(SEVERITY_LEVELS.keys())


def _category_subschema(allowed_severities: list[str]) -> dict:
    return {
        "type": "object",
        "properties": {
            "severity": {"type": "string", "enum": allowed_severities},
            "reason":   {"type": "string"},
        },
        "required": ["severity", "reason"],
        "additionalProperties": False,
    }


def _output_schema() -> dict:
    return {
        "type": "object",
        "properties": {
            "categories": {
                "type": "object",
                "properties": {
                    name: _category_subschema(levels)
                    for name, levels in SEVERITY_LEVELS.items()
                },
                "required": list(SEVERITY_LEVELS.keys()),
                "additionalProperties": False,
            },
            "framing":    {"type": "string", "enum": FRAMING_VALUES},
            "confidence": {"type": "string", "enum": CONFIDENCE_VALUES},
            "verdict": {
                "type": "object",
                "properties": {
                    "family_friendly": {"type": "string", "enum": ["pass", "decline"]},
                    "mixed_company":   {"type": "string", "enum": ["pass", "decline"]},
                    "close_friends":   {"type": "string", "enum": ["pass", "decline"]},
                },
                "required": ["family_friendly", "mixed_company", "close_friends"],
                "additionalProperties": False,
            },
            "summary": {"type": "string"},
        },
        "required": ["categories", "framing", "confidence", "verdict", "summary"],
        "additionalProperties": False,
    }


OUTPUT_SCHEMA = _output_schema()


def _user_message(song: str, artist: str, lyrics: str | None) -> str:
    parts = [f"Song: {song}", f"Artist: {artist}"]
    if lyrics:
        parts.append(f"\nLyrics:\n{lyrics}")
    else:
        parts.append("\nLyrics: (not provided — evaluate from title + artist + your knowledge of the track)")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Analysis dataclasses — the durable, profile-agnostic content breakdown.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class CategoryRating:
    """One content category's severity plus a short model-written reason."""
    severity: str
    reason: str = ""


@dataclass(frozen=True)
class SongAnalysis:
    """Per-category content analysis for one track. No per-profile verdicts —
    profiles.derive_verdict() computes those from these fields at query time."""
    sexual: CategoryRating
    drug_references: CategoryRating
    violence: CategoryRating
    dark_themes: CategoryRating
    language: CategoryRating
    framing: str
    confidence: str
    summary: str = ""
    model_id: str = ""
    rubric_version: str = ""
    evaluated_at: float = field(default=0.0)

    def category(self, name: str) -> CategoryRating:
        """Return the CategoryRating for one of CATEGORY_NAMES."""
        return getattr(self, name)

    @classmethod
    def from_tool_input(
        cls,
        data: dict,
        *,
        model_id: str,
        rubric_version: str,
        evaluated_at: float | None = None,
    ) -> "SongAnalysis":
        """Build a SongAnalysis from the model's tool_use `.input` dict.

        The model's own `verdict` block is intentionally ignored — code derives
        verdicts (spike lock: profile logic lives in code, not the prompt).
        """
        cats = data.get("categories", {})

        def rating(name: str) -> CategoryRating:
            c = cats.get(name) or {}
            return CategoryRating(severity=c.get("severity", "none"), reason=c.get("reason", ""))

        return cls(
            sexual=rating("sexual"),
            drug_references=rating("drug_references"),
            violence=rating("violence"),
            dark_themes=rating("dark_themes"),
            language=rating("language"),
            framing=data.get("framing", "neutral"),
            confidence=data.get("confidence", "unknown"),
            summary=data.get("summary", ""),
            model_id=model_id,
            rubric_version=rubric_version,
            evaluated_at=time.time() if evaluated_at is None else evaluated_at,
        )


# ---------------------------------------------------------------------------
# The evaluator service.
# ---------------------------------------------------------------------------
class SentimentService:
    """Evaluates song lyrics into a SongAnalysis, delegating the model call to a
    pluggable SentimentProvider (defaults to AnthropicProvider). The provider's
    blocking call is wrapped in an executor so the daemon's event loop is never
    blocked — matching how other blocking IO is called.

    Args:
        provider: the AI backend (sentiment_provider.SentimentProvider). If None,
            an AnthropicProvider is constructed from `api_key` / `model`.
        rubric_version: stamp stored with each analysis so a rubric change
            invalidates stale cache rows.
        rubric_path: override the rubric file (defaults to prompts/rubric_v2.md).
        api_key / model: only used to build the default AnthropicProvider when
            `provider` is None; ignored when a provider is injected.
    """

    def __init__(
        self,
        provider: SentimentProvider | None = None,
        rubric_version: str = DEFAULT_RUBRIC_VERSION,
        rubric_path: str | Path | None = None,
        *,
        api_key: str | None = None,
        model: str = DEFAULT_ANTHROPIC_MODEL,
        timeout_seconds: float = 20.0,
    ) -> None:
        if provider is None:
            from sentiment_provider import AnthropicProvider

            provider = AnthropicProvider(api_key=api_key, model=model)
        self.provider = provider
        self.rubric_version = rubric_version
        self._rubric_path = Path(rubric_path) if rubric_path else _RUBRIC_PATH
        self._rubric: str | None = None
        self._timeout_seconds = timeout_seconds

    @property
    def rubric(self) -> str:
        """The system-prompt rubric text, read from disk once and cached."""
        if self._rubric is None:
            self._rubric = self._rubric_path.read_text()
        return self._rubric

    async def evaluate(
        self, track_id: str, title: str, artist: str, lyrics: str | None
    ) -> SongAnalysis | None:
        """Evaluate a track's lyrics into a SongAnalysis.

        Returns None when:
          - no lyrics were provided (spike lock: never call the LLM on title only),
          - the provider call fails, or
          - the provider returned nothing usable.
        The caller treats None as "route to manual review, do not cache".
        A returned SongAnalysis may carry confidence="unknown" — the caller must
        check that and decline + review + not-cache, per the spike locks.
        """
        if not lyrics or not lyrics.strip():
            return None

        user_message = _user_message(title, artist, lyrics)
        loop = asyncio.get_event_loop()
        try:
            data = await asyncio.wait_for(
                loop.run_in_executor(
                    None, self.provider.evaluate, self.rubric, user_message, OUTPUT_SCHEMA
                ),
                timeout=self._timeout_seconds,
            )
        except asyncio.TimeoutError:
            log.warning(
                "sentiment eval TIMED OUT after %.0fs for %s (%s)",
                self._timeout_seconds, track_id, title,
            )
            return None
        except Exception as exc:  # noqa: BLE001 — degrade to review on any backend error
            log.warning("sentiment eval failed for %s (%s): %s", track_id, title, exc)
            return None

        if not data:
            log.warning("sentiment eval returned no rating for %s (%s)", track_id, title)
            return None

        return SongAnalysis.from_tool_input(
            data, model_id=self.provider.model_id, rubric_version=self.rubric_version
        )
