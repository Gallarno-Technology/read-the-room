# Architecture Research

**Domain:** Adding drug/sexual content detection signals to existing Python content filter pipeline (v1.3)
**Researched:** 2026-04-03
**Confidence:** HIGH — based on direct codebase inspection of all production files and test suite

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                      daemon.py (asyncio poll loop)                   │
│                                                                      │
│  sp.current_playback() → track_id change detected                   │
│      │                                                               │
│      ├─ emit track_change event + write now_playing (evaluating)     │
│      │                                                               │
│      └─ ContentChecker.check(track) → TrackEvalResult               │
│              │                                                       │
│              ├─ .action: str ('skip' | 'allow')                      │
│              ├─ .reason: str ('explicit' | 'profanity' |             │
│              │           'drug_reference' | 'sexual_content' |       │
│              │           'instrumental' | 'clean' | ...)             │
│              ├─ .severity: int (0-3)                                 │
│              ├─ .drug_reference: bool       ← NEW v1.3              │
│              ├─ .drug_terms: list[str]      ← NEW v1.3              │
│              ├─ .sexual_content: bool       ← NEW v1.3              │
│              └─ .sexual_terms: list[str]    ← NEW v1.3              │
│                                                                      │
│  result → eval_result event (events.jsonl) with new bool fields      │
│  result → now_playing.json updated with new bool fields              │
└──────────────────────────────────────────────────────────────────────┘
          │ file-based IPC (data/events.jsonl + data/now_playing.json)
┌─────────▼────────────────────────────────────────────────────────────┐
│                    web_ui/main.py (FastAPI)                           │
│                                                                      │
│  _file_tail() tails events.jsonl → SSE broadcast verbatim            │
│  GET /now-playing → reads now_playing.json verbatim                  │
│  (no code changes needed — new fields pass through automatically)    │
└──────────────────────────────────────────────────────────────────────┘
          │ SSE events + /now-playing JSON hydration
┌─────────▼────────────────────────────────────────────────────────────┐
│                  index.html (vanilla JS dashboard)                   │
│                                                                      │
│  eval_result handler → setEvalBadge() extended for drug/sexual       │
│  skip feed handler → setBadgeClass() / badgeLabel() extended         │
└──────────────────────────────────────────────────────────────────────┘
```

### ContentChecker Filter Pipeline (after v1.3)

```
ContentChecker.check(track)
    │
    Tier 1: track.get("explicit") == True?
        └─ YES → return TrackEvalResult(action='skip', reason='explicit', severity=3)
    │
    Tier 2: lyrics_service.get_lyrics()
        ├─ instrumental=True → return TrackEvalResult(action='allow', reason='instrumental', severity=0)
        └─ lyrics=None       → return TrackEvalResult(action='allow', reason='lyrics_unavailable', severity=0)
    │
    Tier 3: profanity_scanner.scan(lyrics) → (severity, matched_words)
    Tier 4: drug_scanner.scan(lyrics)      → (drug_ref: bool, drug_terms: list[str])   ← NEW
    Tier 5: sexual_content_scanner.scan(lyrics) → (sexual: bool, sexual_terms: list[str])  ← NEW
    │
    (all three scans run before deciding action)
    │
    Aggregate:
        action = 'skip'  if severity >= min_severity OR drug_ref OR sexual
        action = 'allow' otherwise
        reason = 'profanity'       if severity >= min_severity
               | 'drug_reference'  elif drug_ref
               | 'sexual_content'  elif sexual
               | 'clean'           otherwise
    │
    return TrackEvalResult(
        action=action, reason=reason, severity=severity,
        drug_reference=drug_ref, drug_terms=drug_terms,
        sexual_content=sexual, sexual_terms=sexual_terms
    )
```

### Component Responsibilities

| Component | Responsibility | v1.3 Change |
|-----------|----------------|-------------|
| `content_checker.py` | Orchestrates all filter tiers; owns `TrackEvalResult` dataclass | Define `TrackEvalResult`; change `check()` return type; inject and call `DrugScanner` + `SexualContentScanner` |
| `profanity_scanner.py` | Scan lyrics for profanity; return `(severity, matched_words)` | No change |
| `drug_scanner.py` | NEW — scan lyrics for drug references; return `(bool, list[str])` | New file |
| `sexual_content_scanner.py` | NEW — scan lyrics for sexual content; return `(bool, list[str])` | New file |
| `daemon.py` | Poll loop; unpack `TrackEvalResult`; emit events; write `now_playing.json` | Replace 3-tuple destructuring with attribute access; propagate new fields into event payloads |
| `web_ui/main.py` | FastAPI server; file-tail IPC bridge; SSE broadcast; `/now-playing` | No code change — new fields pass through verbatim via `json.loads()` / `json.dumps()` |
| `web_ui/templates/index.html` | Dashboard; badge rendering; skip feed | Add `badge--drug` + `badge--sexual` CSS; extend `setBadgeClass()`, `badgeLabel()`, `setEvalBadge()` |
| `tests/test_daemon_events.py` | Integration tests for event emission | Update 8+ mock `check()` return values from tuple to `TrackEvalResult` |
| `tests/test_content_checker.py` | Unit tests for ContentChecker | New or extended: assert new fields on `TrackEvalResult` |
| `tests/test_drug_scanner.py` | NEW — unit tests for `DrugScanner` | New file |
| `tests/test_sexual_content_scanner.py` | NEW — unit tests for `SexualContentScanner` | New file |

## Recommended Project Structure

```
spotify-sentiment/
├── content_checker.py              # Modified: TrackEvalResult dataclass; new scanner injection
├── daemon.py                       # Modified: attribute access on TrackEvalResult; new event fields
├── profanity_scanner.py            # Unchanged
├── drug_scanner.py                 # NEW: keyword list + scan() method
├── sexual_content_scanner.py       # NEW: keyword list + scan() method
├── lyrics_service.py               # Unchanged
├── skip_client.py                  # Unchanged
├── web_ui/
│   ├── main.py                     # Unchanged
│   └── templates/
│       └── index.html              # Modified: new badge CSS + JS label/class extensions
└── tests/
    ├── conftest.py                 # Unchanged
    ├── test_drug_scanner.py        # NEW
    ├── test_sexual_content_scanner.py  # NEW
    ├── test_content_checker.py     # NEW or extended
    ├── test_daemon_events.py       # Modified: mock return values
    ├── test_web_ui_endpoints.py    # Unchanged
    ├── test_skip_client.py         # Unchanged
    ├── test_sonos_probe.py         # Unchanged
    └── test_healthcheck.py         # Unchanged
```

### Structure Rationale

- **`drug_scanner.py` / `sexual_content_scanner.py` as separate top-level files:** Mirrors the existing `profanity_scanner.py` pattern. Each scanner is independently testable and configurable. The `SEVERITY_MAP` pattern in `profanity_scanner.py` maps cleanly to a per-category term `frozenset`.
- **`TrackEvalResult` defined in `content_checker.py`:** It is the contract between `ContentChecker.check()` and `daemon.py`. Co-locating the dataclass with the class that produces it keeps the module self-contained. No separate `models.py` needed at this codebase scale.

## Architectural Patterns

### Pattern 1: TrackEvalResult Dataclass (replaces 3-tuple)

**What:** A `@dataclass` with named fields and sensible defaults, replacing the `(action, reason, severity)` positional return tuple from `ContentChecker.check()`.

**When to use:** Any time a function returns more than 2-3 values that callers must destructure by position. Named fields prevent positional errors. New fields with defaults are backward-compatible — existing test mocks that construct `TrackEvalResult(action=..., reason=..., severity=...)` do not break when `drug_reference` and `sexual_content` are added later.

**Trade-offs:** Slightly more boilerplate than a tuple. The benefit is that `result.action` is unambiguous, while `t[0]` is not.

**Dataclass definition (in `content_checker.py`):**
```python
from dataclasses import dataclass, field

@dataclass
class TrackEvalResult:
    action: str           # 'skip' | 'allow'
    reason: str           # 'explicit' | 'profanity' | 'drug_reference' |
                          # 'sexual_content' | 'instrumental' | 'clean' |
                          # 'lyrics_unavailable' | 'no_lyrics_service'
    severity: int         # 0-3 (profanity severity; 0 for non-profanity paths)
    drug_reference: bool = field(default=False)
    drug_terms: list[str] = field(default_factory=list)
    sexual_content: bool = field(default=False)
    sexual_terms: list[str] = field(default_factory=list)
```

**Existing test mock migration:** Each `AsyncMock(return_value=("allow", "clean", 0))` becomes `AsyncMock(return_value=TrackEvalResult(action="allow", reason="clean", severity=0))`. The `drug_reference` and `sexual_content` fields default to `False` and `[]` so no test needs to specify them unless testing those specific paths.

### Pattern 2: Scanner Injection into ContentChecker

**What:** `DrugScanner` and `SexualContentScanner` are injected via `ContentChecker.__init__()` as optional keyword arguments (defaulting to `None`), identical to the existing `profanity_scanner` injection pattern.

**When to use:** When scanners need to be replaced with mocks in tests, or swapped without changing `ContentChecker`'s interface.

**`ContentChecker.__init__` signature (after v1.3):**
```python
def __init__(
    self,
    lyrics_service=None,
    profanity_scanner=None,
    drug_scanner=None,              # NEW
    sexual_content_scanner=None,    # NEW
    min_severity: int = 2,
) -> None:
```

**Wiring in `daemon.py` `main()`:**
```python
from drug_scanner import DrugScanner
from sexual_content_scanner import SexualContentScanner

drug_scanner = DrugScanner()
sexual_content_scanner = SexualContentScanner()
content_checker = ContentChecker(
    lyrics_service=lyrics_service,
    profanity_scanner=profanity_scanner,
    drug_scanner=drug_scanner,
    sexual_content_scanner=sexual_content_scanner,
    min_severity=PROFANITY_MIN_SEVERITY,
)
```

**Guard in `check()` (mirrors existing profanity_scanner guard):**
The new scans should run only when the scanner is not `None`. This preserves the existing pattern where the lyrics tier is only active when both `self.lyrics_service` and `self.profanity_scanner` are not `None`. For v1.3, where all three scanners are always injected together, this guard prevents `AttributeError` in test scenarios that pass `drug_scanner=None`.

### Pattern 3: Keyword List Scan (mirrors SEVERITY_MAP in profanity_scanner.py)

**What:** Each new scanner holds a module-level `frozenset` of lowercase terms. The `scan()` method normalizes lyrics (lowercase, strip punctuation), splits on whitespace, and checks set membership — identical to Pass 1 of `ProfanityScanner.scan()`.

**When to use:** Boolean signal detection where exact-match keywords are sufficient. Correct for v1.3 — the goal is "errs on the side of caution" for a 3- and 7-year-old audience without NLP complexity.

**Return type for new scanners:**
```python
def scan(self, lyrics: str) -> tuple[bool, list[str]]:
    # Returns (detected: bool, matched_terms: list[str])
```

Intentionally simpler than `ProfanityScanner.scan()` which returns a severity int. Drug and sexual detection are boolean signals in v1.3; per-category severity is explicitly deferred to v2+ (PROJECT.md Deferred section).

## Data Flow

### Filter Pipeline Execution Order — Rationale

All three scans (profanity, drug, sexual) run after the lyrics are fetched and before `action` is determined. **Do not short-circuit on the first skip trigger.** A track that fires profanity AND a drug reference should log both signals — the incident log needs complete signal data for future per-category UI toggles (v2+).

The Spotify explicit flag remains a short-circuit (Tier 1) because it skips the lyrics fetch entirely. On explicit-flag skips, `drug_reference` and `sexual_content` default to `False` and `[]` — which is correct: the track is skipped regardless, and no lyrics were available to scan.

**Priority for `reason` field** (determines badge label in the skip feed): profanity takes precedence over `drug_reference`, which takes precedence over `sexual_content`. This matches the existing tiered model where a higher-severity finding is surfaced as the primary reason.

### Event Propagation — Fields Added to Existing Payloads

**`eval_result` event (already exists — two new fields added):**
```json
{
  "type": "eval_result",
  "track_id": "...",
  "eval_state": "passed",
  "severity": 0,
  "drug_reference": false,
  "sexual_content": false,
  "timestamp": "14:23:02"
}
```

**`skip` event (already exists — two new fields added):**
```json
{
  "type": "skip",
  "track": "...",
  "artist": "...",
  "reason": "drug_reference",
  "drug_reference": true,
  "sexual_content": false,
  "timestamp": "14:23:02"
}
```

**`now_playing.json` (already exists — two new fields added):**
```json
{
  "track_id": "...",
  "track": "...",
  "artist": "...",
  "album_art_url": "...",
  "eval_state": "skipped",
  "severity": 0,
  "drug_reference": true,
  "sexual_content": false,
  "timestamp": "2026-04-03T14:23:02Z"
}
```

**`web_ui/main.py`:** The `_file_tail()` loop reads each line with `json.loads()` and broadcasts with `json.dumps()`. New fields in the JSON lines pass through to SSE subscribers without any code change.

**Dashboard JS:** The only changes are in `setEvalBadge()` (reads `drug_reference` and `sexual_content` booleans from `eval_result` SSE event and `/now-playing` hydration to render additional badges), `setBadgeClass()` (handles `"drug_reference"` and `"sexual_content"` reason strings in the skip feed), and `badgeLabel()` (same extension).

### Key Data Flows

1. **Track with drug reference, no profanity:** ContentChecker completes profanity scan (severity=0, matched=[]), drug scan (drug_ref=True, drug_terms=["..."]). `action='skip'`, `reason='drug_reference'`. eval_result event carries `drug_reference: true`. Dashboard renders "Skipped" badge + drug reference indicator badge.

2. **Track with both profanity and sexual content:** Both scans run. `reason='profanity'` (profanity takes priority in reason field). `sexual_content: true` is still logged in the event. Both boolean flags are available for the dashboard to render a multi-badge display.

3. **Track with no violations:** All scans run. `action='allow'`, `reason='clean'`, all booleans `False`. eval_result carries `drug_reference: false, sexual_content: false`. Dashboard renders "Passed" badge.

4. **Explicit-flag skip:** Short-circuit in Tier 1 returns immediately. `drug_reference=False, sexual_content=False` (dataclass defaults). No lyrics were fetched; nothing to scan.

## Integration Points — All 3-Tuple Call Sites

This section exhaustively identifies every location that must change when replacing the `(action, reason, severity)` 3-tuple with `TrackEvalResult`.

### Production Code — Required Changes

| File | Line(s) | Current code | Required change |
|------|---------|--------------|-----------------|
| `content_checker.py` | 39 | `async def check(self, track: dict) -> tuple[str, str, int]:` | Change to `-> TrackEvalResult:` |
| `content_checker.py` | 47-51 | Docstring listing `(action, reason, severity)` | Update docstring |
| `content_checker.py` | 64 | `return ("skip", "explicit", 3)` | `return TrackEvalResult(action="skip", reason="explicit", severity=3)` |
| `content_checker.py` | 81 | `return ("allow", "instrumental", 0)` | `return TrackEvalResult(action="allow", reason="instrumental", severity=0)` |
| `content_checker.py` | 91 | `return ("allow", "lyrics_unavailable", 0)` | `return TrackEvalResult(action="allow", reason="lyrics_unavailable", severity=0)` |
| `content_checker.py` | 110 | `return (action, reason, severity)` | `return TrackEvalResult(action=action, reason=reason, severity=severity, ...)` |
| `content_checker.py` | 119 | `return ("allow", "no_lyrics_service", 0)` | `return TrackEvalResult(action="allow", reason="no_lyrics_service", severity=0)` |
| `daemon.py` | 248 | `action, reason, severity = await content_checker.check(track)` | `result = await content_checker.check(track)` |
| `daemon.py` | 253 | `if action == "allow":` | `if result.action == "allow":` |
| `daemon.py` | 257 | `"eval_state": _eval_state_from_result(action, reason),` | `_eval_state_from_result(result.action, result.reason)` |
| `daemon.py` | 258 | `"severity": severity,` | `"severity": result.severity,` |
| `daemon.py` | 259-271 (allow branch) | Event dict and `_write_now_playing` call | Add `"drug_reference": result.drug_reference, "sexual_content": result.sexual_content` to both dicts |
| `daemon.py` | 273 | `if action == "skip":` | `if result.action == "skip":` |
| `daemon.py` | 327 | `"reason": reason,` (in skip event) | `"reason": result.reason,` |
| `daemon.py` | 332-345 (skip branch) | Skip event dict and eval_result dict | Add `"drug_reference": result.drug_reference, "sexual_content": result.sexual_content` to both dicts |
| `daemon.py` | 354-363 (skip eval_result) | `_write_now_playing` call | Add new fields |
| `daemon.py` | 147 | `_eval_state_from_result(action: str, reason: str)` | Signature unchanged; call sites updated to use `result.action`, `result.reason` |

### Test Code — Required Changes

| File | Location | Current code | Required change |
|------|---------|--------------|-----------------|
| `tests/test_daemon_events.py` | Line 102 (spy return) | `return ("allow", "clean", 0)` | `return TrackEvalResult(action="allow", reason="clean", severity=0)` |
| `tests/test_daemon_events.py` | Line 121 | `AsyncMock(return_value=("allow", "clean", 0))` | `AsyncMock(return_value=TrackEvalResult(action="allow", reason="clean", severity=0))` |
| `tests/test_daemon_events.py` | Line 149 | same | same |
| `tests/test_daemon_events.py` | Line 169 | `AsyncMock(return_value=("skip", "explicit", 3))` | `AsyncMock(return_value=TrackEvalResult(action="skip", reason="explicit", severity=3))` |
| `tests/test_daemon_events.py` | Line 211 | `("allow", "clean", 0)` | `TrackEvalResult(action="allow", reason="clean", severity=0)` |
| `tests/test_daemon_events.py` | Line 231 | `("skip", "explicit", 3)` | `TrackEvalResult(action="skip", reason="explicit", severity=3)` |
| `tests/test_daemon_events.py` | Line 275 (spy return) | `return ("allow", "clean", 0)` | `return TrackEvalResult(action="allow", reason="clean", severity=0)` |
| `tests/test_daemon_events.py` | Line 300 | `("allow", "clean", 0)` | `TrackEvalResult(action="allow", reason="clean", severity=0)` |
| `tests/test_daemon_events.py` | Line 320 | `("skip", "explicit", 3)` | `TrackEvalResult(action="skip", reason="explicit", severity=3)` |
| `tests/test_daemon_events.py` | Line 361 | `("allow", "mild_language", 1)` | `TrackEvalResult(action="allow", reason="mild_language", severity=1)` |

**Import required in `test_daemon_events.py`:** Add `from content_checker import TrackEvalResult` after the existing `import daemon` line.

### No Change Required

| File | Reason |
|------|--------|
| `web_ui/main.py` | `_file_tail()` uses `json.loads()` / `json.dumps()` — new fields pass through verbatim |
| `profanity_scanner.py` | Called internally by `ContentChecker`; interface unchanged |
| `lyrics_service.py` | Not involved in return type |
| `skip_client.py` | Receives `device_name` and `device_id` only; no eval result involved |
| `tests/test_web_ui_endpoints.py` | Tests JSON passthrough verbatim; new fields in `now_playing.json` do not break assertions |
| `tests/test_skip_client.py` | Not related to content evaluation |
| `tests/test_sonos_probe.py` | Not related to content evaluation |
| `tests/test_healthcheck.py` | Not related to content evaluation |

## Scaling Considerations

Single-user home service. The keyword scan approach runs in microseconds per track against roughly 5-15KB of lyrics text. Scaling is not a concern.

| Scale | Architecture Adjustments |
|-------|--------------------------|
| Single household (current) | Module-level `frozenset` — no database needed |
| Multi-family (hypothetical) | Term lists move to config file; per-user scanner configuration |

## Anti-Patterns

### Anti-Pattern 1: Extending ProfanityScanner with drug/sexual terms

**What people do:** Add drug and sexual terms to `SEVERITY_MAP` using a new "category" dimension alongside the existing severity tiers.

**Why it's wrong:** `ProfanityScanner.scan()` returns `(severity, matched_words)` — a severity int does not represent drug/sexual category. Conflating the two axes prevents independent per-category UI toggles (a v2+ requirement explicitly listed in PROJECT.md). Changing `ProfanityScanner`'s return type would break `ContentChecker` and every test that calls it.

**Do this instead:** Independent `DrugScanner` and `SexualContentScanner` classes with `scan(lyrics) -> tuple[bool, list[str]]` interfaces, injected separately into `ContentChecker`.

### Anti-Pattern 2: Short-circuiting drug/sexual scans when profanity fires

**What people do:** Gate the drug/sexual scans with `if severity < self.min_severity:` to skip them when profanity already triggers a skip, reasoning that the track will be skipped anyway.

**Why it's wrong:** The boolean signals must be populated for all tracks that reach lyric scanning, including those skipped for profanity. A track that fires both profanity AND a drug reference should log both. The incident log and v2+ per-category toggle UI depend on complete signal data. Skipping the scan also means the dashboard cannot render a drug badge alongside a profanity skip.

**Do this instead:** Run all three scans (profanity, drug, sexual) unconditionally once lyrics are available. Determine `action` only after all scans complete.

### Anti-Pattern 3: Logging drug_terms / sexual_terms in events.jsonl

**What people do:** Include the full `drug_terms` and `sexual_terms` lists in every `skip` event and `eval_result` event payload.

**Why it's wrong:** The PROJECT.md milestone spec requires only boolean signals in the log. The matched term lists add no value in the browser dashboard — the parent sees "Flagged: drug reference" not a list of words. They inflate the events file and appear in every SSE payload delivered to the browser.

**Do this instead:** Log only `drug_reference: bool` and `sexual_content: bool` in events. The term lists remain available on `TrackEvalResult` for internal `[SCAN]` log lines in `content_checker.py`, following the existing pattern where `matched` words appear in debug logs but not in the JSONL incident log.

### Anti-Pattern 4: Expanding the 3-tuple to a 7-tuple

**What people do:** Add the four new fields by extending the existing tuple: `(action, reason, severity, drug_ref, drug_terms, sexual, sexual_terms)`.

**Why it's wrong:** Every test with `return_value=("allow", "clean", 0)` breaks immediately unless all 7 positions are provided. Any future field addition causes another mass-update across all test mocks. The v1.3 tests already have 10 mock call sites that would all need to be widened positionally.

**Do this instead:** `TrackEvalResult` dataclass with `field(default=False)` and `field(default_factory=list)` on new signals. Existing test mocks constructing `TrackEvalResult(action="allow", reason="clean", severity=0)` continue to work without modification when a new field is added in v1.4.

### Anti-Pattern 5: Putting TrackEvalResult in a separate models.py

**What people do:** Create a `models.py` file to hold shared data classes.

**Why it's wrong:** `TrackEvalResult` is produced exclusively by `ContentChecker.check()` and consumed exclusively by `daemon.py`. It does not need to be shared across multiple unrelated modules. At this codebase size (5 Python files in the root), a `models.py` adds an import indirection that gains nothing. If `TrackEvalResult` ever needs sharing beyond these two modules, move it at that time.

**Do this instead:** Define `TrackEvalResult` at the top of `content_checker.py`, alongside the class that produces it.

## Suggested Build Order

The dataclass refactor is a hard prerequisite for new signal work — it must be done before adding fields to it.

**Phase 1 — TrackEvalResult dataclass + 3-tuple migration (pure refactor, no behavior change)**
- Define `TrackEvalResult` dataclass at the top of `content_checker.py`
- Change all 5 `return (...)` statements in `check()` to `return TrackEvalResult(...)`
- Update `check()` return type annotation
- Update `daemon.py` line 248 from tuple destructuring to `result = ...`
- Update all `action`, `reason`, `severity` variable references in `daemon.py` poll loop to `result.action`, `result.reason`, `result.severity`
- Update all 10 mock return values in `test_daemon_events.py` (add `from content_checker import TrackEvalResult` import)
- Run full test suite — all tests must pass before Phase 2 begins
- Rationale: zero behavior change; isolated refactor; every subsequent phase writes and reads named attributes only

**Phase 2 — DrugScanner + SexualContentScanner modules**
- Create `drug_scanner.py` with term `frozenset` and `scan(lyrics) -> tuple[bool, list[str]]`
- Create `sexual_content_scanner.py` same structure
- Write isolated unit tests in `test_drug_scanner.py` and `test_sexual_content_scanner.py`
- Rationale: pure functions with no dependencies on the rest of the pipeline; test independently before wiring into `ContentChecker`

**Phase 3 — ContentChecker pipeline integration**
- Add `drug_scanner=None` and `sexual_content_scanner=None` parameters to `ContentChecker.__init__()`
- Store both on `self`
- In `check()`, after profanity scan, call both new scanners (guard: `if self.drug_scanner is not None`)
- Aggregate results; populate all `TrackEvalResult` fields
- Wire both scanners into `daemon.py` `main()` instantiation block
- Write/extend `test_content_checker.py` for all new pipeline paths
- Rationale: depends on Phase 1 (`TrackEvalResult` exists) and Phase 2 (scanner classes exist)

**Phase 4 — Event propagation + incident log**
- Add `"drug_reference": result.drug_reference` and `"sexual_content": result.sexual_content` to:
  - `eval_result` event dict in `daemon.py` (allow branch)
  - `skip` event dict in `daemon.py`
  - `eval_result` event dict after successful skip
  - All `_write_now_playing()` calls in the FSM-on branch
  - The paused-branch eval_result and now_playing calls (use `result.drug_reference` etc — or `False`/`False` since pause path does not re-evaluate)
- Verify `test_daemon_events.py` still passes; add assertions for new fields where relevant
- Rationale: depends on Phase 3 (`ContentChecker` now populates these fields on `TrackEvalResult`)

**Phase 5 — Dashboard badge variants**
- Add `badge--drug` and `badge--sexual` CSS classes to `index.html` (following the existing badge color pattern)
- Extend `setBadgeClass(reason)` to return `'badge--drug'` for `reason.includes('drug')` and `'badge--sexual'` for `reason.includes('sexual')`
- Extend `badgeLabel(reason)` to return `'Flagged: drug reference'` and `'Flagged: sexual content'`
- Extend `setEvalBadge(evalState, severity, drugRef, sexualContent)` — or read new fields off the event object — to render additional `badge--drug` / `badge--sexual` badges in the now-playing card badge-group div
- Update `es.onmessage` eval_result handler to pass `evt.drug_reference` and `evt.sexual_content` through to `setEvalBadge()`
- Update `hydrateNowPlaying()` / `renderTrack()` to pass `data.drug_reference` and `data.sexual_content` through to `setEvalBadge()`
- Rationale: depends on Phase 4 (SSE events and `/now-playing` response now carry boolean fields)

## Sources

- Direct inspection: `content_checker.py`, `daemon.py`, `profanity_scanner.py`, `lyrics_service.py`, `web_ui/main.py`, `web_ui/templates/index.html`, `tests/test_daemon_events.py`, `tests/test_web_ui_endpoints.py`, `tests/conftest.py`
- `.planning/PROJECT.md` v1.3 milestone context and deferred features list
- Confidence: HIGH — all findings derived from the current v1.2 codebase; no external sources required for this integration architecture

---
*Architecture research for: Spotify Family Safe Mode v1.3 — Drug & Sexual Reference Detection*
*Researched: 2026-04-03*
