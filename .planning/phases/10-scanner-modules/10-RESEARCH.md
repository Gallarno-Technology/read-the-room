# Phase 10: Scanner Modules - Research

**Researched:** 2026-04-03
**Domain:** Python regex scanning, keyword set design, pytest unit testing
**Confidence:** HIGH

## Summary

Phase 10 creates two new scanner classes — `DrugScanner` and `SexualContentScanner` — each as a standalone `.py` file following the `profanity_scanner.py` template exactly. Both scanners are pure functions with no external dependencies beyond the Python standard library `re` module. The implementation is entirely greenfield within the project's established patterns.

The primary implementation challenge is not technical complexity but term set design: the drug list must be conservative enough that "High Hopes", "Here Comes the Sun", and "Puff the Magic Dragon" all return `(False, [])`, and the sexual terms set must be strictly disjoint from `SEVERITY_MAP.keys()` in `profanity_scanner.py`. Both constraints have been verified computationally in this research.

The architectural upgrade over `ProfanityScanner` is switching from the split-then-strip word loop to pre-compiled `re.compile(r'\b' + re.escape(term) + r'\b', re.IGNORECASE)` patterns at module load time. This correctly handles punctuation-adjacent terms and multi-word phrases ("crystal meth", "purple drank") that the split approach cannot handle at all.

**Primary recommendation:** Mirror `profanity_scanner.py` structure exactly (module docstring, `log = logging.getLogger(__name__)`, constant set at module level, class with `scan()` method), replacing the two-pass word-loop with a dict of pre-compiled regex patterns iterated in `scan()`.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Conservative keyword list only — unambiguous terms with near-zero false positive risk
- **D-02:** Include hard drug clinical names: cocaine, heroin, methamphetamine/meth, fentanyl, opioid, morphine, oxycodone, ketamine, LSD, PCP, ecstasy, MDMA, crack
- **D-03:** Include low-ambiguity slang explicitly requested: crystal meth, sizzurp, purple drank, coke
- **D-04:** Exclude ambiguous slang: "high", "weed", "pot", "joint", "dope", "blunt" — false positive risk on innocent songs too high for ages 3 & 7
- **D-05:** False positive guard: "High Hopes", "Here Comes the Sun", "Puff the Magic Dragon" must all return `(False, [])` (required by success criteria)
- **D-06:** Cover explicit sex acts, anatomical terms, and unambiguous act slang — "obvious red flags" only; nuance deferred to future LLM layer
- **D-07:** Include explicit act words: fornicate, copulate, masturbate, ejaculate, orgasm (as verb), fellatio, cunnilingus, handjob, blowjob, fingering, rimming — none have innocent uses in lyrics
- **D-08:** Include anatomical terms not already in `SEVERITY_MAP`: penis, vagina, vulva, clitoris, scrotum, testicles, anus, nipple (and common variants/slang not already claimed)
- **D-09:** Exclude: naked, nude — too many innocent uses in mainstream lyrics
- **D-10:** `SEXUAL_TERMS` must be strictly disjoint from `SEVERITY_MAP.keys()` — enforced by unit test (SEXL-03)
- **D-11:** Mirror `profanity_scanner.py` file-per-scanner pattern: `drug_scanner.py` and `sexual_content_scanner.py` as separate files
- **D-12:** Each scanner is a class with a `scan(lyrics: str) -> tuple[bool, list[str]]` method, matching the existing class pattern. Pure — no instance state needed beyond the keyword set constant.
- **D-13:** Word-boundary regex matching (`re.search(r'\b' + re.escape(term) + r'\b', ...)`) — replaces the split-then-strip approach used in `ProfanityScanner`; handles punctuation-adjacent terms correctly

### Claude's Discretion
- Exact inflected forms to include per term (e.g., "cocaine" → also "cocaines"? unlikely; scanner author's call)
- Whether to pre-compile regex patterns at module level for performance
- Unit test file naming and fixture structure (follow existing test conventions)

### Deferred Ideas (OUT OF SCOPE)
- Phrase/multi-word matching ("making love", "getting high", "smoke weed") — deferred to v2+
- "dope", "weed", "pot", "joint", "high" as drug terms — excluded from v1.3
- "naked", "nude" as sexual terms — excluded
- Alcohol/tobacco as a separate signal — deferred
- LLM nuance layer — future milestone
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DRUG-01 | System detects drug references in song lyrics using word-boundary keyword matching | Verified: `\b`-anchored `re.compile` patterns handle this correctly; confirmed none of the locked drug terms appear in the three guard songs |
| DRUG-02 | `DrugScanner.scan()` returns a `(bool, list[str])` tuple — matched terms available for debug logging | Confirmed: mirror of `profanity_scanner.py` scan() signature, adjusted return type from `(int, list[str])` to `(bool, list[str])` |
| SEXL-01 | System detects sexual content in song lyrics using word-boundary keyword matching | Verified: same regex pattern approach as DRUG-01; pre-compiled dict at module level |
| SEXL-02 | `SexualContentScanner.scan()` returns a `(bool, list[str])` tuple — matched terms available for debug logging | Confirmed: identical signature to DrugScanner.scan() |
| SEXL-03 | Sexual content keyword list has no overlap with terms already in the profanity `SEVERITY_MAP` (enforced by unit test) | Verified computationally: proposed SEXUAL_TERMS set is disjoint from all 121 SEVERITY_MAP keys; cock/dick/tit/ass/pussy/cunt/arse/prick already claimed by SEVERITY_MAP |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `re` (stdlib) | Python 3.12 | Word-boundary regex matching | No external dependency; `\b` anchors handle word boundaries correctly including adjacent punctuation |
| `logging` (stdlib) | Python 3.12 | Debug logging of matched terms | Matches existing pattern: `log = logging.getLogger(__name__)` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pytest` | 9.0.2 (installed) | Unit test framework | All test files in `tests/` |

No new packages needed. No changes to `requirements.txt`.

**Version verification:** Confirmed via `python3 -c "import pytest; print(pytest.__version__)"` — pytest 9.0.2, pytest-asyncio 1.3.0.

## Architecture Patterns

### File Layout
```
profanity_scanner.py          # existing — template to mirror
drug_scanner.py               # new — Phase 10
sexual_content_scanner.py     # new — Phase 10
tests/
├── conftest.py               # existing — adds project root to sys.path
├── test_drug_scanner.py      # new — Phase 10
└── test_sexual_content_scanner.py  # new — Phase 10
```

### Pattern 1: Scanner Class Structure (mirror profanity_scanner.py exactly)

**What:** Module-level constant (set or compiled dict), class with no required constructor args, `scan(lyrics: str) -> tuple[bool, list[str]]` method, `log.debug(...)` at end of scan.

**When to use:** All new scanners in this project.

```python
# Source: profanity_scanner.py (existing, verified)
#!/usr/bin/env python3
"""[Docstring describing scanner purpose]"""
import logging
import re

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Keyword set — [description of scope and philosophy]
# ---------------------------------------------------------------------------
DRUG_TERMS: set[str] = {
    "cocaine",
    "heroin",
    # ... full set (see Term Set Design section below)
}

# Pre-compile for performance (Claude's discretion — recommended)
_DRUG_PATTERNS: dict[str, re.Pattern[str]] = {
    term: re.compile(r"\b" + re.escape(term) + r"\b", re.IGNORECASE)
    for term in DRUG_TERMS
}


class DrugScanner:
    """Scan lyrics for drug references and return a boolean signal.

    Returns (True, matched_terms) on any drug reference detection.
    Conservative keyword list only — unambiguous terms (D-01).
    """

    def scan(self, lyrics: str) -> tuple[bool, list[str]]:
        """Scan lyrics text for drug references.

        Args:
            lyrics: Raw lyrics string (may contain newlines).

        Returns:
            Tuple of (detected, matched_terms):
            - detected: True if any drug reference found, False otherwise
            - matched_terms: Deduplicated list of matched terms (lowercased).
        """
        matched: list[str] = []
        seen: set[str] = set()

        for term, pattern in _DRUG_PATTERNS.items():
            if term not in seen and pattern.search(lyrics):
                matched.append(term)
                seen.add(term)

        detected = len(matched) > 0
        log.debug("DrugScanner: detected=%s matched=%s", detected, matched)
        return (detected, matched)
```

### Pattern 2: Word-Boundary Regex (the upgrade from ProfanityScanner)

**What:** `re.compile(r"\b" + re.escape(term) + r"\b", re.IGNORECASE)` at module level.

**Why better than split-then-strip:** The existing `ProfanityScanner` strips punctuation then checks a dict. This works for single words but cannot handle:
1. Multi-word terms ("crystal meth", "purple drank") — split produces two tokens
2. Punctuation-adjacent matches ("cocaine," with trailing comma)

Pre-compiled `\b` regex handles both correctly.

**Verified behavior:**
- `"cocaine,"` — matches `cocaine` term (punctuation after word is fine)
- `"methadone"` — does NOT match `meth` term (`\b` prevents substring match)
- `"crystal meth"` — matches `crystal meth` as a phrase when the full phrase is in the set
- `"methamphetamine"` — does NOT match `meth` alone (`\b` boundary stops at word end)

### Pattern 3: Test File Structure

**What:** Plain pytest (synchronous) — no `@pytest.mark.asyncio` needed; scanners are synchronous pure functions.

**When to use:** All scanner unit tests.

```python
# Source: pattern derived from tests/test_skip_client.py and tests/test_sonos_probe.py
"""Tests for DrugScanner — DRUG-01, DRUG-02.

Covers:
  test_drug_scanner_detects_cocaine: returns (True, ['cocaine']) on match
  test_drug_scanner_returns_false_for_clean: returns (False, []) for clean lyrics
  test_drug_scanner_false_positive_high_hopes: guard song returns (False, [])
  ...
"""
import pytest
from drug_scanner import DrugScanner, DRUG_TERMS


@pytest.fixture
def scanner():
    return DrugScanner()


def test_drug_scanner_detects_cocaine(scanner):
    """DrugScanner.scan() returns (True, ['cocaine']) for cocaine reference."""
    detected, matched = scanner.scan("she snorted cocaine off the mirror")
    assert detected is True
    assert "cocaine" in matched


def test_drug_scanner_returns_false_for_clean_lyrics(scanner):
    """DrugScanner.scan() returns (False, []) for clean lyrics."""
    detected, matched = scanner.scan("I love you and the music plays")
    assert detected is False
    assert matched == []
```

### Pattern 4: Disjoint Enforcement Test (SEXL-03)

**Critical:** This test must exist in `test_sexual_content_scanner.py` and must be the first or clearly prominent test. It imports both `SEXUAL_TERMS` and `SEVERITY_MAP` directly.

```python
from sexual_content_scanner import SEXUAL_TERMS
from profanity_scanner import SEVERITY_MAP


def test_sexual_terms_disjoint_from_severity_map():
    """SEXUAL_TERMS must have no overlap with SEVERITY_MAP keys (SEXL-03)."""
    overlap = SEXUAL_TERMS & set(SEVERITY_MAP.keys())
    assert overlap == set(), (
        f"SEXUAL_TERMS overlaps with SEVERITY_MAP: {overlap}"
    )
```

### Anti-Patterns to Avoid
- **Using the split-then-strip loop from ProfanityScanner for new scanners:** Cannot handle multi-word terms or punctuation-adjacent tokens. Use pre-compiled `\b` regex.
- **Including SEVERITY_MAP terms in SEXUAL_TERMS:** cock, dick, tit, tits, ass, pussy, cunt, cocks, arse, prick are all already in SEVERITY_MAP — adding them to SEXUAL_TERMS would break SEXL-03.
- **Adding constructor arguments:** New scanners are boolean-only (no `min_severity` equivalent). `__init__` is not needed (or can be `def __init__(self) -> None: pass`).
- **Using `re.search()` per scan call without pre-compilation:** Technically correct but wastes compile time on every call. Pre-compile at module level.
- **Multi-word terms as separate single-word entries:** "crystal" alone would match "crystal clear" (false positive). "crystal meth" as a phrase is the correct unit.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Word-boundary matching | Custom tokenizer or string.split() logic | `re.compile(r"\b...\b", re.IGNORECASE)` | Handles punctuation adjacent words, multi-word phrases, and case in one shot |
| Substring prevention | Manual prefix/suffix checks | `\b` anchors | `\b` already does this; `meth` does not match inside `methadone` |
| Case normalization | `.lower()` preprocessing | `re.IGNORECASE` flag | Cleaner; works with `\b` without modifying the lyrics string |

**Key insight:** The standard library `re` module with `\b` anchors solves every matching requirement in this phase without any custom logic.

## Term Set Design

### DRUG_TERMS (verified against D-02, D-03, D-04)

**Included — clinical names (D-02):**
```
cocaine, heroin, methamphetamine, meth, fentanyl, opioid, morphine,
oxycodone, ketamine, lsd, pcp, ecstasy, mdma, crack
```

**Included — explicit slang (D-03):**
```
crystal meth, sizzurp, purple drank, coke
```

**Excluded by lock (D-04) — false positive risk too high:**
- `high`, `weed`, `pot`, `joint`, `dope`, `blunt`

**False positive verification (D-05, computationally confirmed):**
- "High Hopes" (Panic! at the Disco): none of the above terms appear — passes `(False, [])`
- "Here Comes the Sun" (The Beatles): none of the above terms appear — passes `(False, [])`
- "Puff the Magic Dragon" (Peter Paul and Mary): none of the above terms appear — passes `(False, [])`

Note on "Puff the Magic Dragon": the song title contains "puff" and "magic dragon" but neither is in the drug list. The word "puff" is not included per D-04 exclusion reasoning. This is the correct outcome.

**Inflection guidance (Claude's discretion):** Drug names are typically used as nouns without inflection in lyrics. Recommend including: `opioids` (plural of `opioid`), `morphines` (unlikely — omit), `oxycodones` (unlikely — omit). The term `meth` is already a short form of `methamphetamine` — both should be in the set independently. `crack` as written covers "crack cocaine" contexts; `crack` alone may occasionally mean "crack of dawn" but user accepted this risk.

### SEXUAL_TERMS (verified against D-07, D-08, D-10)

**Included — act words (D-07):**
```
fornicate, fornicates, fornicating, fornication,
copulate, copulates, copulating, copulation,
masturbate, masturbates, masturbating, masturbation,
ejaculate, ejaculates, ejaculating, ejaculation,
orgasm,
fellatio, cunnilingus,
handjob, handjobs,
blowjob, blowjobs,
fingering, rimming
```

**Included — anatomical terms NOT in SEVERITY_MAP (D-08):**
```
penis, vagina, vulva, clitoris, scrotum, testicle, testicles, anus, nipple, nipples, anal
```

**Terms already in SEVERITY_MAP (must NOT be added to SEXUAL_TERMS):**
```
cock, cocks, dick, dicks, dicking,
tit, tits,
ass, asses, asshole, assholes, arsehole,
arse, arses,
prick, pricks,
pussy, pussies,
cunt, cunts,
wank, wanker, wankers, wanking,
twat, twats,
slut, sluts, slutty,
whore, whores
```

**Excluded by lock (D-09):** `naked`, `nude`

**Disjoint constraint (D-10, SEXL-03): computationally verified** — the proposed `SEXUAL_TERMS` set has zero overlap with all 121 keys in `SEVERITY_MAP`.

## Common Pitfalls

### Pitfall 1: Multi-Word Terms With Split Approach
**What goes wrong:** Including "crystal meth" in the term set but using `split()` — `"crystal"` and `"meth"` become separate tokens; "crystal meth" as a phrase is never matched.
**Why it happens:** Copying ProfanityScanner's split loop without upgrading to regex.
**How to avoid:** Use `re.compile(r"\b" + re.escape(term) + r"\b", re.IGNORECASE)` which handles multi-word phrases as continuous strings.
**Warning signs:** Test for "crystal meth" passes when testing "meth" alone but fails for the phrase.

### Pitfall 2: SEXUAL_TERMS Overlap With SEVERITY_MAP
**What goes wrong:** Adding `cock`, `dick`, `pussy`, `ass`, `tit` etc. to SEXUAL_TERMS seems logical but breaks SEXL-03.
**Why it happens:** These are obviously sexual anatomical terms — easy to include without checking the existing map.
**How to avoid:** Run the disjoint test first (it is a test, not just a check) and verify the full list against SEVERITY_MAP keys before committing. The disjoint test imports both sets and asserts equality to empty set.
**Warning signs:** SEXL-03 test fails with overlap = `{'cock', 'dick', ...}`.

### Pitfall 3: `coke` Matching "Coca-Cola" Brand References
**What goes wrong:** "coke" in lyrics like "drink a coke and smile" triggers a false positive.
**Why it happens:** "coke" is ambiguous (D-04 logic). The user explicitly accepted this term (D-03).
**How to avoid:** This is an accepted tradeoff per user decision D-03. The LLM nuance layer (future phase) will handle it. Document this in the scanner's module docstring.
**Warning signs:** A false positive on an innocent pop song. Acceptable for v1.3 per spec.

### Pitfall 4: `meth` Matching `methamphetamine` Double-Count
**What goes wrong:** Lyrics containing "methamphetamine" match both `meth` and `methamphetamine` terms, returning both in `matched_terms`.
**Why it happens:** `\b` correctly prevents `meth` matching inside `methadone` (different word boundary), but `methamphetamine` contains `meth` at the START — and `\bmeth\b` will NOT match inside `methamphetamine` because the boundary check fails at the `a` in `methamphetamine`.
**Verification:** Confirmed — `re.search(r'\bmeth\b', 'methamphetamine')` returns None. No double-count issue.

### Pitfall 5: Forgetting `re.IGNORECASE` Flag
**What goes wrong:** "COCAINE" or "Cocaine" (title case in lyrics) does not match.
**Why it happens:** Passing compiled pattern without the flag, then forgetting to lowercase lyrics.
**How to avoid:** Always include `re.IGNORECASE` in the compile call. Do not rely on normalizing lyrics to lowercase.

## Code Examples

### Complete DrugScanner Template
```python
# Source: mirrors profanity_scanner.py exactly; pattern verified locally
#!/usr/bin/env python3
"""Drug reference scanner for Spotify Family Safe Mode.

Conservative keyword list — unambiguous terms only (D-01).
Ambiguous slang ('high', 'weed', 'dope') excluded to prevent
false positives on innocent songs.

Note: 'coke' is included per D-03 — accepted minor ambiguity risk.
"""
import logging
import re

log = logging.getLogger(__name__)

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

_DRUG_PATTERNS: dict[str, re.Pattern[str]] = {
    term: re.compile(r"\b" + re.escape(term) + r"\b", re.IGNORECASE)
    for term in DRUG_TERMS
}


class DrugScanner:
    """Scan lyrics for drug references."""

    def scan(self, lyrics: str) -> tuple[bool, list[str]]:
        matched: list[str] = []
        seen: set[str] = set()
        for term, pattern in _DRUG_PATTERNS.items():
            if term not in seen and pattern.search(lyrics):
                matched.append(term)
                seen.add(term)
        detected = bool(matched)
        log.debug("DrugScanner: detected=%s matched=%s", detected, matched)
        return (detected, matched)
```

### Disjoint Unit Test (SEXL-03)
```python
# Source: derived from requirements SEXL-03 and CONTEXT.md D-10
def test_sexual_terms_disjoint_from_severity_map():
    """SEXUAL_TERMS must not overlap with SEVERITY_MAP keys (SEXL-03)."""
    from sexual_content_scanner import SEXUAL_TERMS
    from profanity_scanner import SEVERITY_MAP
    overlap = SEXUAL_TERMS & set(SEVERITY_MAP.keys())
    assert overlap == set(), (
        f"SEXUAL_TERMS overlaps with SEVERITY_MAP keys: {overlap!r}. "
        "Remove these from SEXUAL_TERMS — they are already covered by ProfanityScanner."
    )
```

### False Positive Guard Tests (Success Criteria 3)
```python
@pytest.mark.parametrize("song_lyrics", [
    "had high hopes shooting for the stars climbed every mountain",
    "here comes the sun little darling its been a long cold lonely winter",
    "puff the magic dragon lived by the sea and frolicked in the autumn mist",
])
def test_drug_scanner_false_positive_guard_songs(scanner, song_lyrics):
    """Guard songs must return (False, []) — no drug false positives (D-05)."""
    detected, matched = scanner.scan(song_lyrics)
    assert detected is False, f"False positive on guard song: matched={matched!r}"
    assert matched == []
```

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | none — conftest.py adds project root to sys.path |
| Quick run command | `python -m pytest tests/test_drug_scanner.py tests/test_sexual_content_scanner.py -x` |
| Full suite command | `python -m pytest tests/ -x` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DRUG-01 | DrugScanner matches cocaine/heroin/etc with word boundaries | unit | `python -m pytest tests/test_drug_scanner.py -x` | Wave 0 |
| DRUG-02 | DrugScanner.scan() returns `(bool, list[str])` | unit | `python -m pytest tests/test_drug_scanner.py::test_drug_scanner_return_type -x` | Wave 0 |
| SEXL-01 | SexualContentScanner matches act/anatomical terms | unit | `python -m pytest tests/test_sexual_content_scanner.py -x` | Wave 0 |
| SEXL-02 | SexualContentScanner.scan() returns `(bool, list[str])` | unit | `python -m pytest tests/test_sexual_content_scanner.py::test_sexual_scanner_return_type -x` | Wave 0 |
| SEXL-03 | `SEXUAL_TERMS.isdisjoint(SEVERITY_MAP.keys())` | unit | `python -m pytest tests/test_sexual_content_scanner.py::test_sexual_terms_disjoint_from_severity_map -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_drug_scanner.py tests/test_sexual_content_scanner.py -x`
- **Per wave merge:** `python -m pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_drug_scanner.py` — covers DRUG-01, DRUG-02
- [ ] `tests/test_sexual_content_scanner.py` — covers SEXL-01, SEXL-02, SEXL-03

*(No framework install needed — pytest already installed and configured)*

## Environment Availability

Step 2.6: SKIPPED — phase is purely Python code with no external dependencies beyond stdlib `re` and the already-installed `pytest`. No databases, CLIs, Docker, or network services involved.

## Sources

### Primary (HIGH confidence)
- `profanity_scanner.py` (project file, read directly) — complete implementation template; all patterns derived from this
- `tests/conftest.py`, `tests/test_skip_client.py`, `tests/test_sonos_probe.py` (project files, read directly) — test structure, fixture patterns, assertion style
- `content_checker.py` (project file, read directly) — confirms Phase 11 integration target; scanner injection pattern
- Python 3.12 stdlib `re` module — `\b` word boundary semantics verified via local execution

### Secondary (MEDIUM confidence)
- Verified computationally: `DRUG_TERMS` set produces zero matches on representative guard song lyrics
- Verified computationally: proposed `SEXUAL_TERMS` is disjoint from all 121 `SEVERITY_MAP` keys

### Tertiary (LOW confidence)
- Guard song lyrics used in verification are representative summaries from training knowledge, not authoritative full-text. Final implementation should test against actual LRCLIB-returned lyrics for these songs.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — stdlib only; no version risk
- Architecture: HIGH — directly mirrors existing code in the same repo
- Term sets: HIGH for clinical drug names and act words; MEDIUM for slang terms (coke, crack ambiguity accepted by user decision)
- Test patterns: HIGH — copied from existing test files in same repo
- Pitfalls: HIGH — verified computationally with actual Python execution

**Research date:** 2026-04-03
**Valid until:** Stable (no external dependencies that can change)
