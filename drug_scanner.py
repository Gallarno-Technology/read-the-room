#!/usr/bin/env python3
"""Drug reference scanner for Spotify Family Safe Mode.

Conservative keyword list — unambiguous terms only (D-01).
Ambiguous slang ('high', 'weed', 'dope', 'pot', 'joint', 'blunt') excluded
to prevent false positives on innocent songs (D-04).

Note: 'coke' is included per D-03 — accepted minor ambiguity risk
(e.g., "drink a coke"). The LLM nuance layer (future phase) handles this.
"""
import logging
import re

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Keyword set — conservative, unambiguous terms only (D-01, D-02, D-03).
# Multi-word terms ("crystal meth") are matched as phrases via \b regex.
# ---------------------------------------------------------------------------
DRUG_TERMS: set[str] = {
    # Clinical names (D-02)
    "cocaine",
    "heroin",
    "methamphetamine",
    "meth",
    "fentanyl",
    "opioid",
    "opioids",
    "morphine",
    "oxycodone",
    "ketamine",
    "lsd",
    "pcp",
    "ecstasy",
    "mdma",
    "crack",
    # Explicit slang (D-03)
    "crystal meth",
    "sizzurp",
    "purple drank",
    "coke",
}

# Pre-compile at module load for performance (re.IGNORECASE handles case; D-13).
# re.escape() handles special chars; \b anchors prevent substring matches.
_DRUG_PATTERNS: dict[str, re.Pattern[str]] = {
    term: re.compile(r"\b" + re.escape(term) + r"\b", re.IGNORECASE)
    for term in DRUG_TERMS
}


class DrugScanner:
    """Scan lyrics for drug references.

    Returns (True, matched_terms) when any drug reference is detected.
    Conservative keyword list — unambiguous terms only (D-01).
    """

    def scan(self, lyrics: str) -> tuple[bool, list[str]]:
        """Scan lyrics text for drug references.

        Args:
            lyrics: Raw lyrics string (may contain newlines).

        Returns:
            Tuple of (detected, matched_terms):
            - detected: True if any drug reference found, False otherwise.
            - matched_terms: Deduplicated list of matched terms.
        """
        matched: list[str] = []
        seen: set[str] = set()

        for term, pattern in _DRUG_PATTERNS.items():
            if term not in seen and pattern.search(lyrics):
                matched.append(term)
                seen.add(term)

        detected = bool(matched)
        log.debug("DrugScanner: detected=%s matched=%s", detected, matched)
        return (detected, matched)
