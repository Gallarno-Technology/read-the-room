# Stack Research

**Domain:** Keyword-based drug reference and sexual content detection in lyrics text — Python content filter extension
**Researched:** 2026-04-03
**Confidence:** HIGH

---

## Context: What This Milestone Adds (v1.3)

The existing daemon already has:

- `ContentChecker` class with `check()` returning a positional 3-tuple `(action, reason, severity)`
- `ProfanityScanner` doing word-split + dict lookup (Pass 1) and `better-profanity` leet-speak fallback (Pass 2)
- `LyricsService` fetching LRCLIB lyrics, cache-first via `aiosqlite` SQLite
- Full lyrics text available as a plain string at `lyrics_result.lyrics`
- Dashboard badge infrastructure already extended for additive badge display (`badge-group` flex pattern)

v1.3 adds two new boolean detection signals on top of the existing lyrics text, without changing how lyrics are fetched:

- Drug reference detection (keyword match against lyrics text)
- Sexual content detection (keyword match against lyrics text)
- `ContentChecker.check()` returns a named `TrackEvalResult` dataclass instead of positional 3-tuple

---

## Recommended Stack

### Core Technologies

No new PyPI dependencies required. All three capabilities — regex matching, dataclass return type, and word lists — are handled by Python stdlib.

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| `re` (stdlib) | Python 3.12 built-in | Word-boundary keyword matching against lyrics text | `\b` word boundary anchors prevent substring false positives (e.g. "grass" matching "ass"). `re.compile()` with alternation pattern `\b(?:term1|term2|...)\b` precompiled at module load — O(1) pattern reuse per scan. `re.IGNORECASE` handles mixed-case lyrics without normalization overhead. No external dependency. |
| `dataclasses` (stdlib) | Python 3.12 built-in | Named return type `TrackEvalResult` replacing positional 3-tuple | `@dataclass` in stdlib since Python 3.7. Python 3.12 supports `slots=True` (added 3.10) for minor memory savings. `frozen=True` is appropriate for an immutable result object. No new package needed — zero requirements.txt change. |
| `frozenset` (stdlib) | Python 3.12 built-in | Backing store for drug and sexual content keyword lists | O(1) membership testing vs O(n) for list. Immutable (cannot be accidentally mutated at runtime). Communicates intent: these are fixed canonical sets, not user-configurable lists. Used as source for building the compiled regex alternation at module load time. |

### Supporting Libraries

No new libraries needed. Existing stack already provides everything required.

| Library | Version | Already in? | Role in v1.3 |
|---------|---------|-------------|--------------|
| `better-profanity` | 0.7.0 | daemon | Unchanged — leet-speak fallback for profanity only; drug/sexual scanners do NOT use it |
| `aiosqlite` | 0.22.1 | daemon | Unchanged — lyrics cache layer; drug/sexual scan happens on already-fetched lyrics string |
| `pytest` | 8.3.5 | daemon | Unit tests for new scanner classes and `TrackEvalResult` dataclass |
| `pytest-asyncio` | 0.25.3 | daemon | Unchanged — `ContentChecker.check()` is still async |

### Development Tools

No changes to dev toolchain.

| Tool | Purpose | Notes |
|------|---------|-------|
| `pytest` + `pytest-asyncio` | Test new scanner classes and updated `check()` return type | Existing `conftest.py` patterns apply; scanner tests are synchronous (no async needed) |

---

## Pattern: Word-Boundary Regex Matching

The correct implementation pattern for both `DrugScanner` and `SexualContentScanner` is:

```python
import re
from frozenset import ...  # frozenset is a builtin

# Defined at module level — compiled once, reused on every scan
_DRUG_TERMS: frozenset[str] = frozenset({
    "weed", "marijuana", "cannabis", "cocaine", "coke", "crack",
    "heroin", "meth", "molly", "ecstasy", "mdma", "xanax", "percocet",
    "oxy", "oxycontin", "codeine", "lean", "sizzurp", "blunt", "joint",
    "spliff", "bong", "dope", "acid", "lsd", "shrooms", "ketamine",
    "adderall", "vicodin", "morphine", "fentanyl", "bars", "perc",
    # ... full list in implementation
})

_DRUG_PATTERN: re.Pattern[str] = re.compile(
    r"\b(?:" + "|".join(map(re.escape, sorted(_DRUG_TERMS))) + r")\b",
    re.IGNORECASE,
)

def scan_drugs(lyrics: str) -> bool:
    return bool(_DRUG_PATTERN.search(lyrics))
```

**Why this pattern over word-split + dict lookup (the profanity scanner approach):**

The profanity scanner splits on whitespace then strips punctuation from each token. This works for profanity (single-word terms). For drug/sexual content it fails on multi-word phrases like "lean drink" if we ever add them, and requires manual punctuation stripping. The `re.compile` pattern handles punctuation boundaries natively via `\b` and is more composable.

**Why `re.search` not `re.findall`:**

For a boolean signal we only need to know if any term exists — `search()` short-circuits on first match. `findall()` scans the entire text and collects all matches, which is wasteful for a detection-only use case.

**Why `re.IGNORECASE` not manual `.lower()`:**

Normalizing the entire lyrics string to lowercase before matching creates a temporary string allocation per check. `re.IGNORECASE` is a flag on the compiled pattern — no allocation overhead.

**`re.escape` on each term before joining:**

Ensures terms with regex metacharacters (e.g. dots, parentheses) are treated literally. Defensive against word list additions that accidentally include regex syntax.

---

## Pattern: TrackEvalResult Dataclass

Replace the existing `tuple[str, str, int]` return type from `ContentChecker.check()` with a named dataclass:

```python
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class TrackEvalResult:
    action: str          # "skip" | "allow"
    reason: str          # "explicit" | "profanity" | "drug" | "sexual" | "instrumental" | "clean" | "lyrics_unavailable" | "no_lyrics_service"
    severity: int        # 0-3 (profanity severity; 0 for non-profanity skip reasons)
    has_drug_ref: bool   # True if drug reference detected in lyrics
    has_sexual_content: bool  # True if sexual content detected in lyrics
```

**`frozen=True`:** Result objects are immutable values — they should not be modified after `check()` returns. `frozen=True` enforces this and auto-generates `__hash__`, enabling use in sets/dicts if needed for caching.

**`slots=True`:** Available since Python 3.10, present in 3.12. Reduces per-instance memory by using `__slots__` instead of `__dict__`. For a small struct returned per-track on every poll cycle (once per second), this is a mild but free improvement.

**No `@dataclass(eq=True)` needed:** `eq=True` is the default. Equality comparison of result objects is correct behavior for tests.

**Backward compatibility on call sites:** All existing call sites unpack `(action, reason, severity) = result` or access `result[0]`. `frozen=True` dataclasses do NOT support index access (`result[0]`). All call sites must be migrated to attribute access (`result.action`, `result.reason`, `result.severity`). This is the expected migration cost — positional tuple → named dataclass.

---

## Word Lists: Drug References

No PyPI package provides a maintained, curated list of drug slang specifically for music/lyric content filtering. The packages found on PyPI (`drug-named-entity-recognition`, `drugstone`, `druglinker`) are pharmaceutical NER tools designed for clinical text — not appropriate for lyric slang.

**Recommendation: Maintain a custom `frozenset` in the codebase** (same approach as `SEVERITY_MAP` in `profanity_scanner.py`). This gives full control, auditability, and no transitive dependency risk.

**Evidence-based seed list** (from academic research on drug references in Billboard Hot 100 music, 2008-2018):

Cannabis: `weed`, `marijuana`, `cannabis`, `pot`, `blunt`, `joint`, `spliff`, `bong`, `dank`, `chronic`, `kush`, `bud`, `reefer`, `ganja`, `420`, `doobie`

Cocaine/stimulants: `cocaine`, `coke`, `crack`, `blow`, `snow`, `powder`, `meth`, `ice`, `crystal`, `speed`, `adderall`

Opioids: `heroin`, `smack`, `dope`, `oxy`, `oxycontin`, `oxycodone`, `percocet`, `perc`, `vicodin`, `morphine`, `codeine`, `lean`, `sizzurp`, `promethazine`, `fentanyl`, `bars` (Xanax bars), `xanax`

MDMA/psychedelics: `molly`, `ecstasy`, `mdma`, `acid`, `lsd`, `shrooms`, `mushrooms`, `ketamine`, `pcp`

Generic: `dope`, `stash`, `plug` (slang for dealer), `trap` (context-dependent — flag for review)

**Note on false positives:** Terms like `pot`, `speed`, `crystal`, `ice`, `bars`, `trap`, and `plug` have common non-drug uses in lyrics. The word-boundary pattern prevents substring false positives, but context-dependent terms will produce some false positives. This is consistent with the project's established philosophy: "err on the side of caution" for ages 3 and 7. False positives (over-skipping) are preferable to false negatives.

**Note on `420` and numeric slang:** `\b` word boundary works with digits — `\b420\b` will match `420` as a standalone token but not `1420` or `4200`. Include numeric slang terms in the list.

---

## Word Lists: Sexual Content

Same recommendation: custom `frozenset` in codebase. The existing `profanity_scanner.py` `SEVERITY_MAP` already contains several sexual terms at severity tier 2 (`whore`, `slut`, `tits`, `cock`, `pussy`, `wank`, etc.). The sexual content scanner serves a different purpose: detecting explicit sexual *acts and scenarios* in lyrics, which would not trigger the profanity scanner's severity threshold.

The sexual content scanner keyword list should include terms for sexual acts, body parts not already in the profanity map, and common euphemisms used in popular music. The full list is the implementation team's domain judgment — the scanner class structure is identical to the drug scanner.

**Overlap with profanity map:** Words already in `SEVERITY_MAP` at tier 2/3 (e.g. `dick`, `pussy`, `cock`, `fuck`) do NOT need duplication in the sexual content list. The profanity scanner already handles them. The sexual content list should focus on terms the profanity scanner misses: act descriptors, contextual slang, and euphemisms.

---

## What NOT to Add

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `drug-named-entity-recognition` (PyPI) | Clinical/pharmaceutical NER, not music slang. Requires ML model download, heavy dependency. Would recognize "Tylenol" but miss "lean". | Custom `frozenset` with curated music slang terms |
| `spacy` or `nltk` for NLP-based detection | Adds 50-500MB of model data and startup time to a container that polls every second. Overkill for boolean keyword detection. | `re.compile` with `\b` boundaries — sufficient and instant |
| `better-profanity` for drug/sexual scanning | Its leet-speak expansion is only relevant for profanity — drug/sexual slang is not typically leet-encoded in music lyrics. Extending its wordlist would mix concerns. | Separate scanner classes with dedicated `frozenset` + compiled regex |
| `pydantic.BaseModel` for `TrackEvalResult` | Pydantic adds validation overhead and a 3MB dependency for a result object that never crosses a serialization boundary. | stdlib `@dataclass(frozen=True, slots=True)` — immutable, zero-cost, no new dep |
| `NamedTuple` for `TrackEvalResult` | Supports index access (`result[0]`), which encourages continued positional usage instead of named attributes. Harder to add fields with defaults. | `@dataclass(frozen=True)` — attribute-only access enforces named usage |
| Checking `better_profanity.profanity_wordlist.txt` for drug/sexual terms | The built-in wordlist mixes categories without labels — no reliable way to extract drug-specific or sexual-content-specific terms programmatically. | Curated project-owned lists |
| `re.MULTILINE` flag | Not needed — lyrics are searched as a single string, not line-by-line. `\b` works correctly without it. | No flag (default) |
| Calling `re.search(pattern_string, ...)` inside scan method | Recompiles the pattern on every call even with internal caching. | `re.compile()` at module level, call `.search(lyrics)` on the compiled object |

---

## Installation

No new packages. No changes to `requirements.txt` in daemon or web_ui.

```bash
# No changes required — all capabilities are Python 3.12 stdlib:
# - re (word-boundary regex matching)
# - dataclasses (@dataclass decorator)
# - frozenset (builtin type, no import)
```

---

## Alternatives Considered

| Category | Recommended | Alternative | When Alternative Makes Sense |
|----------|-------------|-------------|------------------------------|
| Return type | `@dataclass(frozen=True, slots=True)` | `typing.NamedTuple` | NamedTuple is fine if callers legitimately need tuple unpacking or index access. Here we're deliberately breaking positional access to force migration to named attributes. |
| Keyword matching | `re.compile(\b...\b, re.IGNORECASE)` | word-split + `frozenset` lookup (profanity scanner pattern) | The profanity scanner pattern is faster for pure single-token exact-match with manual punctuation stripping. Use it when the term list has no multi-word phrases and you need matched word reporting. The regex approach is more correct for general text matching and handles punctuation automatically. |
| Word list source | Project-owned `frozenset` in source | External data file (`.txt` or `.json`) loaded at startup | External file makes sense when the list is > ~200 terms, needs runtime updates without code deploy, or needs to be shared across multiple services. For v1.3 the list is < 100 terms and changes only with code changes. |
| Drug/sexual detection scope | Keyword matching (boolean, per PROJECT.md) | ML classifier (BERT fine-tune, etc.) | ML is appropriate when context is critical — "I shot the sheriff" vs literal gun violence. For v1.3 the requirement is explicitly a "boolean signal" and the project explicitly excludes "Sentiment NLP — too complex for v1". |

---

## Version Compatibility

| Package | Container | Version | v1.3 Notes |
|---------|-----------|---------|------------|
| Python | daemon | 3.12 | `@dataclass(slots=True)` requires 3.10+ — satisfied |
| `re` (stdlib) | daemon | 3.12 | `\b` word boundary, `re.IGNORECASE`, `re.escape` — all stable, no version concerns |
| `dataclasses` (stdlib) | daemon | 3.12 | `frozen=True`, `slots=True` — both available since 3.10 |
| `better-profanity` | daemon | 0.7.0 | Unchanged — not involved in new scanners |
| `pytest` | daemon | 8.3.5 | Unchanged — scanner unit tests are synchronous |

---

## Integration Points with Existing Code

### New files to create

- `drug_scanner.py` — `DrugScanner` class with module-level compiled pattern, `scan(lyrics: str) -> bool` method
- `sexual_content_scanner.py` — `SexualContentScanner` class, same structure as `DrugScanner`

### Files to modify

- `content_checker.py` — Add `TrackEvalResult` dataclass (or import from a shared `models.py`). Update `check()` return type annotation and all `return` statements. Wire in `DrugScanner` and `SexualContentScanner` alongside existing `ProfanityScanner`.
- `daemon.py` — Update all call sites of `content_checker.check()` to use named attributes (`result.action`, `result.reason`, `result.severity`) instead of tuple unpacking. Add `has_drug_ref` and `has_sexual_content` fields to skip event JSON written to `skip_events.jsonl`.
- `web_ui/main.py` (or `now_playing.json` serialization) — Add `has_drug_ref` and `has_sexual_content` to the SSE event payload for new dashboard badge rendering.

### Dataclass placement

Two options: inline in `content_checker.py` or a new `models.py`. The latter is preferred — it avoids circular imports if `daemon.py` needs to type-annotate the result without importing the full `ContentChecker`.

---

## Sources

- [Python `re` module official docs](https://docs.python.org/3/library/re.html) — `\b` boundary behavior, `re.IGNORECASE`, `re.escape`, compile-once performance (HIGH confidence, official)
- [Python `dataclasses` official docs](https://docs.python.org/3/library/dataclasses.html) — `frozen`, `slots`, `KW_ONLY` parameters, Python 3.10+ feature additions (HIGH confidence, official)
- Existing `profanity_scanner.py` (codebase) — word-split + dict lookup pattern, established precedent for inline word lists (HIGH confidence, primary source)
- Existing `content_checker.py` (codebase) — current `check()` return tuple, integration points for new scanners (HIGH confidence, primary source)
- ResearchGate / PMC study on drug terms in Billboard Hot 100 lyrics — evidence base for drug keyword seed list (MEDIUM confidence, academic source, accessed 2026-04-03)
- [BurntRouter/filtered-word-lists](https://github.com/BurntRouter/filtered-word-lists) — reviewed as candidate source; contains sexual terms but no drug category, no maintenance signal (LOW confidence — not recommended as dependency)
- [Python frozenset O(1) membership](https://www.datacamp.com/tutorial/frozenset) — confirmed O(1) hash lookup vs O(n) list (HIGH confidence, consistent with Python data model)

---

*Stack research for: Spotify Family Safe Mode v1.3 — drug reference and sexual content detection*
*Researched: 2026-04-03*
