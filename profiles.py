#!/usr/bin/env python3
"""Read the Room — 3-profile definitions + query-time verdict derivation.

The LLM (sentiment_service) emits a profile-agnostic SongAnalysis. This module
turns that analysis into a pass/decline for one profile, IN CODE — never in the
prompt (spike lock). Because verdicts are derived here, switching the active
profile never requires re-evaluating a cached song, and a profile ruleset can be
retuned without invalidating the analysis cache.

The three profiles (replacing the legacy 4) and their decline rules are the
production rubric's "Decision rules" section (prompts/rubric_v2.md §Decision
rules), encoded here as the single source of truth for the actual skip decision.

Approximation note (violence, Mixed Company): the rubric distinguishes
"graphic AND real-world-imitable" (bypasses framing) from "graphic AND framing ≠
cautionary". The output schema carries no `real_world_imitable` flag, so this
code declines ALL graphic violence for Mixed Company. That is the conservative,
anchor-consistent choice (Pumped Up Kicks declines correctly); the only content
it over-declines is graphic-but-cautionary-and-non-imitable violence, which no
calibration anchor exercises. Tracked as a prompt/schema residual.
"""
from __future__ import annotations

from sentiment_service import SEVERITY_LEVELS, SongAnalysis

FAMILY_FRIENDLY = "family_friendly"
MIXED_COMPANY = "mixed_company"
CLOSE_FRIENDS = "close_friends"

PROFILES = (FAMILY_FRIENDLY, MIXED_COMPANY, CLOSE_FRIENDS)

# The strictest profile — the safe default when none is stored or a name is unknown.
DEFAULT_PROFILE = FAMILY_FRIENDLY

PASS = "pass"
DECLINE = "decline"

# Framings that read as advocacy/reduction — decline for the stricter profiles.
ADULT_FRAMING = frozenset({"transactional", "glorifying", "objectifying"})


def _rank(category: str, severity: str) -> int:
    """Ordinal rank of a severity within its category's scale (none == 0)."""
    levels = SEVERITY_LEVELS[category]
    try:
        return levels.index(severity)
    except ValueError:  # unknown severity → treat as clean (fail-open on parse noise)
        return 0


def _at_least(category: str, severity: str, threshold: str) -> bool:
    """True when `severity` is at or above `threshold` on the category's scale."""
    return _rank(category, severity) >= _rank(category, threshold)


def _is_cultural_register(reason: str) -> bool:
    """Heavy language flagged by the rubric as cultural register (e.g. n-word in
    Black artistic context), NOT slur-as-slur. The rubric writes this marker into
    the language `reason`; its presence rescues MC and CF from a heavy-language
    decline."""
    return "cultural register" in (reason or "").lower()


def derive_verdict(analysis: SongAnalysis, profile: str) -> str:
    """Return PASS or DECLINE for `analysis` under `profile`.

    Encodes prompts/rubric_v2.md §Decision rules. An unrecognized profile resolves
    to Family Friendly (strictest) as a safety default.
    """
    if profile not in PROFILES:
        profile = DEFAULT_PROFILE

    # Fail-safe: the LLM couldn't ground its answer in lyrics → decline everywhere.
    # (Callers should already avoid caching confidence=unknown and route to review;
    # this makes the derivation itself safe even if such an analysis reaches it.)
    if analysis.confidence == "unknown":
        return DECLINE

    sexual = analysis.sexual.severity
    drugs = analysis.drug_references.severity
    violence = analysis.violence.severity
    dark = analysis.dark_themes.severity
    language = analysis.language.severity
    framing = analysis.framing
    lang_cultural = _is_cultural_register(analysis.language.reason)

    if profile == FAMILY_FRIENDLY:
        if _at_least("sexual", sexual, "innuendo"):
            return DECLINE
        if _at_least("drug_references", drugs, "casual"):
            return DECLINE
        if _at_least("violence", violence, "narrative"):
            return DECLINE
        if _at_least("dark_themes", dark, "present"):
            return DECLINE
        if _at_least("language", language, "moderate"):
            return DECLINE
        if framing in ADULT_FRAMING:
            return DECLINE
        return PASS

    if profile == MIXED_COMPANY:
        if sexual == "explicit":
            return DECLINE
        if drugs == "hard_drug" and framing != "cautionary":
            return DECLINE
        if violence == "graphic":  # see module docstring: conservative approximation
            return DECLINE
        if dark == "prominent":
            return DECLINE
        if framing in ADULT_FRAMING:
            return DECLINE
        if language == "heavy" and not lang_cultural:
            return DECLINE
        return PASS

    # CLOSE_FRIENDS — "we're not a censor": only explicit sexual or slur-as-slur.
    if sexual == "explicit":
        return DECLINE
    if language == "heavy" and not lang_cultural:
        return DECLINE
    return PASS
