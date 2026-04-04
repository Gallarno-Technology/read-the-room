#!/usr/bin/env python3
"""Sexual content scanner for Spotify Family Safe Mode.

Covers explicit sex acts, anatomical terms, and unambiguous act slang (D-06, D-07, D-08).
'Obvious red flags' only — nuance and euphemisms deferred to future LLM layer.

Excluded terms (D-09): naked, nude — too many innocent lyric uses.
Terms already in SEVERITY_MAP are NOT included here (D-10, SEXL-03):
  cock, dick, tit, ass, pussy, cunt, arse, prick, wank, twat, slut, whore, bollocks
"""
import logging
import re

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Keyword set — explicit sexual content only; disjoint from SEVERITY_MAP (D-10).
# Terms already owned by ProfanityScanner are deliberately excluded.
# ---------------------------------------------------------------------------
SEXUAL_TERMS: set[str] = {
    # Act words — none have innocent uses in lyrics (D-07)
    "fornicate",
    "fornicates",
    "fornicating",
    "fornication",
    "copulate",
    "copulates",
    "copulating",
    "copulation",
    "masturbate",
    "masturbates",
    "masturbating",
    "masturbation",
    "ejaculate",
    "ejaculates",
    "ejaculating",
    "ejaculation",
    "orgasm",
    "fellatio",
    "cunnilingus",
    "handjob",
    "handjobs",
    "blowjob",
    "blowjobs",
    "fingering",
    "rimming",
    # Anatomical terms not already in SEVERITY_MAP (D-08)
    "penis",
    "vagina",
    "vulva",
    "clitoris",
    "scrotum",
    "testicle",
    "testicles",
    "anus",
    "anal",
    "nipple",
    "nipples",
}

# Pre-compile at module load for performance (re.IGNORECASE handles case; D-13).
_SEXUAL_PATTERNS: dict[str, re.Pattern[str]] = {
    term: re.compile(r"\b" + re.escape(term) + r"\b", re.IGNORECASE)
    for term in SEXUAL_TERMS
}


class SexualContentScanner:
    """Scan lyrics for sexual content references.

    Returns (True, matched_terms) when any sexual content is detected.
    'Obvious red flags' only — nuance deferred to future LLM layer (D-06).
    SEXUAL_TERMS is strictly disjoint from SEVERITY_MAP (SEXL-03).
    """

    def scan(self, lyrics: str) -> tuple[bool, list[str]]:
        """Scan lyrics text for sexual content.

        Args:
            lyrics: Raw lyrics string (may contain newlines).

        Returns:
            Tuple of (detected, matched_terms):
            - detected: True if any sexual content found, False otherwise.
            - matched_terms: Deduplicated list of matched terms.
        """
        matched: list[str] = []
        seen: set[str] = set()

        for term, pattern in _SEXUAL_PATTERNS.items():
            if term not in seen and pattern.search(lyrics):
                matched.append(term)
                seen.add(term)

        detected = bool(matched)
        log.debug("SexualContentScanner: detected=%s matched=%s", detected, matched)
        return (detected, matched)
