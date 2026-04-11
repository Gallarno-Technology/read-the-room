#!/usr/bin/env python3
"""Profanity scanner with severity word mapping and better-profanity fallback.

Implements a two-pass scan:
  Pass 1: Custom severity word map (word-level, severity 1/2/3)
  Pass 2: better-profanity fallback for leet-speak / obfuscated variants

Severity tiers (D-08, D-10):
  1 = mild (damn, hell, crap, ass, ...)
  2 = moderate (shit, bitch, bastard, ...)
  3 = severe (f-word, n-word, c-word, slurs)
"""
import logging

from better_profanity import profanity

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Severity word mapping — three tiers per D-08, D-09, D-10.
# Keys are lowercase. Common variants (stemmed/inflected) are included.
# ---------------------------------------------------------------------------
SEVERITY_MAP: dict[str, int] = {
    # Tier 1: mild
    "damn": 1,
    "damned": 1,
    "damning": 1,
    "dammit": 1,
    "hell": 1,
    "crap": 1,
    "crappy": 1,
    "ass": 1,
    "asses": 1,
    "darn": 1,
    "suck": 1,
    "sucks": 1,
    "sucking": 1,
    "pee": 1,
    "butt": 1,
    "butts": 1,
    "jerk": 1,
    "idiot": 1,
    "stupid": 1,
    "dumbass": 1,
    "jackass": 1,

    # Tier 2: moderate
    "shit": 2,
    "shitty": 2,
    "shitting": 2,
    "shitted": 2,
    "shits": 2,
    "bullshit": 2,
    "bitch": 2,
    "bitches": 2,
    "bitching": 2,
    "bitchy": 2,
    "bitched": 2,
    "bastard": 2,
    "bastards": 2,
    "piss": 2,
    "pissed": 2,
    "pissing": 2,
    "pissy": 2,
    "whore": 2,
    "whores": 2,
    "slut": 2,
    "sluts": 2,
    "slutty": 2,
    "bollocks": 2,
    "arse": 2,
    "arses": 2,
    "asshole": 2,
    "assholes": 2,
    "arsehole": 2,

    # Tier 3: severe
    "fuck": 3,
    "fucked": 3,
    "fucking": 3,
    "fuckin": 3,
    "fucker": 3,
    "fuckers": 3,
    "fucks": 3,
    "motherfucker": 3,
    "motherfuckers": 3,
    "motherfucking": 3,
    "motherfuckin": 3,
    "mf": 3,
    "fag": 3,
    "fags": 3,
    "faggot": 3,
    "faggots": 3,
    "faggoty": 3,
    "nigger": 3,
    "niggers": 3,
    "nigga": 3,
    "niggas": 3,
    "cunt": 3,
    "cunts": 3,
    "retard": 3,
    "retards": 3,
    "retarded": 3,
}


class ProfanityScanner:
    """Scan lyrics for profanity and return a severity score.

    Args:
        min_severity: Not used in scan() itself (that is ContentChecker's job),
            stored for reference/logging.
    """

    def __init__(self, min_severity: int = 2) -> None:
        self.min_severity = min_severity
        profanity.load_censor_words()

    def scan(self, lyrics: str) -> tuple[int, list[str]]:
        """Scan lyrics text for profanity.

        Args:
            lyrics: Raw lyrics string (may contain newlines).

        Returns:
            Tuple of (max_severity, matched_words):
            - max_severity: 0 = none, 1 = mild, 2 = moderate, 3 = severe
            - matched_words: Deduplicated list of matched words (lowercased).
                             May contain "[obfuscated]" for leet-speak catches.
        """
        # Normalize: replace newlines with spaces, lowercase
        normalized = lyrics.replace("\n", " ").replace("\r", " ").lower()

        words = normalized.split()
        max_severity = 0
        matched: list[str] = []
        seen: set[str] = set()

        # Pass 1: word-by-word severity map lookup
        punct_chars = ".,!?;:'\"()[]{}*-_/"
        for word in words:
            clean = word.strip(punct_chars)
            if clean in SEVERITY_MAP and clean not in seen:
                sev = SEVERITY_MAP[clean]
                matched.append(clean)
                seen.add(clean)
                if sev > max_severity:
                    max_severity = sev

        # Pass 2: better-profanity leet-speak / obfuscation detection (D-08)
        if profanity.contains_profanity(normalized):
            if not matched:
                # better-profanity caught something our map missed (obfuscated variant)
                matched.append("[obfuscated]")
                max_severity = max(max_severity, 2)

        log.debug(
            "ProfanityScanner: max_severity=%d matched=%s",
            max_severity,
            matched,
        )
        return (max_severity, matched)
