# Stack Research

**Domain:** Lyrics content detection — drug references and sexual content
**Researched:** 2026-04-02
**Confidence:** HIGH

---

## Context: What This Milestone Adds

The existing pipeline is:

```
ContentChecker.check(track)
  → Tier 1: Spotify explicit flag
  → Tier 2: LyricsService.get_lyrics()  (LRCLIB + SQLite cache)
  → Tier 3: ProfanityScanner.scan()     (dict lookup + better-profanity fallback)
```

This milestone adds two new boolean signals alongside profanity:
- `drug_refs: bool` — drug/substance references detected in lyrics
- `sexual_content: bool` — sexual content detected in lyrics

Both signals must integrate at Tier 3, run against already-fetched lyrics, and be logged in the incident log alongside the profanity severity.

---

## Recommended Stack

### Core Technologies

No new core framework additions required.

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python `re` (stdlib) | built-in (3.12) | Compiled regex alternation for keyword/phrase matching | Zero dependencies; `re.compile(r'\b(term1\|term2\|...)\b', re.IGNORECASE)` handles both single-word and multi-word phrase matching correctly with word-boundary protection. For lists under ~500 terms, compiled alternation is fast enough that pyahocorasick provides no measurable benefit in this use case. |

### Supporting Libraries

No new PyPI dependencies required.

The existing `better_profanity==0.7.0` is **not** extended for drug or sexual terms. See "What NOT to Use" below.

### Development Tools

No changes to development toolchain. Existing pytest/pytest-asyncio covers unit testing of new scanner classes.

---

## Architecture: New Components

### `KeywordScanner` — one class, two instances

Create a single generic `KeywordScanner` class (new file, e.g., `keyword_scanner.py`) that mirrors `ProfanityScanner`'s interface:

```python
class KeywordScanner:
    def __init__(self, category: str, terms: list[str]) -> None:
        # Pre-compile a single regex: \b(term1|term2|...)\b, IGNORECASE
        ...

    def scan(self, lyrics: str) -> tuple[bool, list[str]]:
        # Returns (matched: bool, matched_terms: list[str])
        ...
```

Instantiate it twice at startup — once with a `DRUG_TERMS` list, once with a `SEXUAL_TERMS` list. Pass both instances into `ContentChecker.__init__()` alongside the existing `profanity_scanner`.

This pattern:
- Mirrors the existing `ProfanityScanner` injection pattern (no structural change to `ContentChecker`)
- Gives each category an independent, testable unit
- Allows per-category enable/disable toggles in a future milestone (the `ContentChecker` already receives each scanner as a named argument)

### Phrase Matching: `re` vs dict lookup

`ProfanityScanner` uses a `word.strip(punct).lower()` dict lookup — correct for single-word profanity. Drug and sexual terms include multi-word phrases ("smoke weed", "get it on", "roll up", "in the sheets"). A compiled regex with `\b` word boundaries handles both single words and phrases in one pass:

```python
import re

_pattern = re.compile(
    r'\b(' + '|'.join(re.escape(t) for t in sorted(terms, key=len, reverse=True)) + r')\b',
    re.IGNORECASE,
)
```

Sorting terms longest-first ensures longer phrases match before their component words (e.g., "lean back" before "lean"), which prevents false-positive component matches.

### Term Lists

Maintain as Python module-level constants in `keyword_scanner.py`. Do NOT load from external files — keeps the service self-contained in the Docker image and makes the lists version-controlled and reviewable.

**Drug terms — representative coverage (curated at implementation time):**
Single words: weed, marijuana, cannabis, blunt, joint, spliff, doobie, kush, chronic, 420, reefer, hash, dabs, edibles, cocaine, coke, crack, snow, blow, white, yayo, heroin, smack, dope, molly, ecstasy, mdma, meth, crystal, ice, speed, lean, purple drank, codeine, promethazine, syrup, percocet, percs, oxy, oxycodone, xanax, bars (drug sense), adderall, fentanyl, shrooms, mushrooms, acid, lsd, pcp, ketamine, poppers, nitrous

Multi-word phrases: "smoke weed", "roll a blunt", "pass the blunt", "blunt rolled", "smoke a j", "hit the blunt", "puff puff pass", "lean back", "sip lean", "pour up", "pop a perc", "pop a pill", "pop mollies", "roll up", "light up"

**Sexual content terms — representative coverage (curated at implementation time):**
Single words: sex, sexual, sexy, naked, nude, nudes, booty, boobs, breasts, penis, vagina, genitals, orgasm, climax, masturbate, masturbation, ejaculate, ejaculation, erection, horny, aroused, lust, lusty, seductive, seduce, foreplay, intercourse, copulate, copulation, penetrate, penetration, anal, oral sex, handjob, blowjob, cunnilingus, fellatio

Multi-word phrases: "make love", "get it on", "have sex", "sleep with", "in bed with", "take your clothes", "take it off", "feel me up", "hook up", "one night stand", "in the sheets", "between the sheets", "get naked", "show me your body", "give it to me"

Note: Several profanity-tier-2 words in `profanity_scanner.py` (`cock`, `pussy`, `tits`, etc.) already exist in the profanity severity map. Do NOT duplicate those in the sexual content list — they are covered by the existing profanity scan. The sexual content scanner targets context/euphemism signals not already caught by profanity scanning.

---

## Installation

No new packages. The only change to `requirements.txt` is none — `re` is stdlib.

```bash
# No additions needed
# Existing requirements.txt is sufficient:
#   better-profanity==0.7.0  (unchanged — still used for leet-speak in ProfanityScanner)
```

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| stdlib `re` compiled alternation | `pyahocorasick==2.3.0` | Use pyahocorasick if the term list grows beyond ~500 entries AND profiling shows regex compilation time at startup is a bottleneck. It is actively maintained (2.3.0 released Dec 2025, Python 3.12 supported) and would be the right upgrade path. |
| stdlib `re` compiled alternation | `flashtext==2.7` | Avoid — last released 2018, unmaintained. `flashtext` also does not support regex word-boundary semantics needed for phrase matching. |
| New `KeywordScanner` class | Extend `better_profanity` censor list | Do not do this. See "What NOT to Use". |
| New `KeywordScanner` class | `alt-profanity-check==1.8.0` (sklearn LinearSVC) | ML classifier is black-box — cannot inspect which terms triggered it, cannot tune per-term, produces confidence scores not boolean categories, and adds scikit-learn + numpy as heavyweight dependencies for a 50ms latency check. Only justified if term-list approach proves too high false-positive rate after real-world tuning. |
| New `KeywordScanner` class | spaCy `PhraseMatcher` | Massive dependency (spaCy model downloads ~50-500MB) for a problem that compiled regex solves with zero overhead. |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| Extending `better_profanity` censor list with drug/sex terms | `better-profanity`'s censor mechanism conflates all loaded terms into a single detection pass with no category distinction. Adding drug terms to its list would mean `profanity.contains_profanity("weed")` returns True — making the `[obfuscated]` fallback in `ProfanityScanner` fire on drug terms and increment the profanity severity score, corrupting the profanity signal. The two concerns must be kept separate. | `KeywordScanner` class with `re` |
| `flashtext==2.7` | No releases since 2018, open issues unfixed, no word-boundary semantics for phrase matching. | `re` compiled alternation or `pyahocorasick` |
| `profanity-check==1.0.3` | Abandoned — last release 2019. Superseded by `alt-profanity-check`. | `alt-profanity-check` if ML classifier ever becomes necessary |
| Loading term lists from external files (YAML, JSON, txt) | Adds file-loading complexity at startup, terms become invisible to Docker build context verification, and changes require container restart but no visibility in code review. | Module-level constants in `keyword_scanner.py` — version-controlled, reviewable, zero I/O |
| scikit-learn / ML classifiers | Heavyweight dependencies (scikit-learn + numpy adds ~80MB to Docker image), opaque results (cannot log which term matched), and no benefit over a curated word list for this narrow domain. | Curated keyword list with compiled regex |

---

## Integration Points with Existing Pipeline

### `ContentChecker` changes

`ContentChecker.__init__()` gains two new optional parameters:

```python
def __init__(
    self,
    lyrics_service=None,
    profanity_scanner=None,
    drug_scanner=None,       # NEW: KeywordScanner instance
    sexual_scanner=None,     # NEW: KeywordScanner instance
    min_severity: int = 2,
) -> None:
```

`ContentChecker.check()` return signature expands from `tuple[str, str, int]` to a structured result (e.g., dataclass or dict) to accommodate the new boolean flags without breaking the existing caller interface in `daemon.py`.

Suggested return structure:
```python
@dataclass
class ScanResult:
    action: str          # 'skip' | 'allow'
    reason: str          # existing reasons + 'drug_refs' | 'sexual_content'
    severity: int        # profanity severity (0-3), unchanged
    drug_refs: bool      # NEW
    sexual_content: bool # NEW
```

### Daemon / incident log changes

The daemon reads `ScanResult` and logs `drug_refs` and `sexual_content` as additional boolean columns in the incident log. The existing skip logic (`action == 'skip'`) gates on whether either new flag is true (same as profanity: if detected, skip).

### Test coverage

New tests in `tests/` cover:
- `KeywordScanner.scan()` returns `(True, [matched])` for known drug terms
- `KeywordScanner.scan()` returns `(False, [])` for clean lyrics
- Multi-word phrase matching ("smoke weed everyday" → True)
- Word-boundary correctness ("leanback" does NOT match "lean", "classical" does NOT match "ass")
- `ContentChecker.check()` returns `drug_refs=True` when drug scanner fires
- `ContentChecker.check()` returns `sexual_content=True` when sexual scanner fires

---

## Version Compatibility

| Package | Version | Notes |
|---------|---------|-------|
| Python | 3.12 | `re` stdlib — no compatibility concerns |
| better-profanity | 0.7.0 | Unchanged — still used for leet-speak obfuscation in `ProfanityScanner` |
| pyahocorasick | 2.3.0 | Not used now; confirmed Python 3.12 compatible if upgrade needed later |

---

## Sources

- [pyahocorasick PyPI](https://pypi.org/project/pyahocorasick/) — Version 2.3.0, Dec 2025, Python 3.12 supported (HIGH confidence, official PyPI)
- [better-profanity PyPI](https://pypi.org/project/better-profanity/) — Version 0.7.0, Nov 2020, last release; `add_censor_words()` API confirmed (HIGH confidence, official PyPI)
- [alt-profanity-check PyPI](https://pypi.org/project/alt-profanity-check/) — Version 1.8.0, Jan 2026; sklearn LinearSVC approach (HIGH confidence, official PyPI)
- [flashtext PyPI](https://pypi.org/project/flashtext/) — Version 2.7, 2018; unmaintained (HIGH confidence, official PyPI)
- [Drug Slang in Music — Delphi Behavioral Health Group](https://delphihealthgroup.com/drug-slang-in-music/) — Drug slang terminology reference (MEDIUM confidence, editorial source)
- [Drug term trends in American hip-hop lyrics — Emerald Insight](https://www.emerald.com/insight/content/doi/10.1108/jpmh-05-2015-0019/full/html) — Academic reference on hip-hop drug terminology (MEDIUM confidence, peer-reviewed)
- [Python re docs](https://docs.python.org/3/library/re.html) — Word boundary and alternation pattern behavior (HIGH confidence, official docs)

---

*Stack research for: Spotify Family Safe Mode v1.2 — drug reference and sexual content detection*
*Researched: 2026-04-02*
