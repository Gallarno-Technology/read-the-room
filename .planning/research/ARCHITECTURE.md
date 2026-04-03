# Architecture Research

**Domain:** Drug and sexual content detection integration into existing ContentChecker pipeline
**Researched:** 2026-04-02
**Confidence:** HIGH — based on direct code inspection of the v1.1 codebase

---

## Standard Architecture

### System Overview (Current v1.1)

```
┌──────────────────────────────────────────────────────────────────┐
│  asyncio daemon (daemon.py)                                       │
│                                                                   │
│  poll_loop() → track change detected                              │
│      │                                                            │
│      ▼                                                            │
│  ContentChecker.check(track) ─────────────────────────────────┐  │
│      │                                                         │  │
│      │  Tier 1: track["explicit"] → (skip, "explicit", 3)     │  │
│      │                                                         │  │
│      │  Tier 2: LyricsService.get_lyrics()                     │  │
│      │      → instrumental  → (allow, "instrumental", 0)      │  │
│      │      → lyrics=None   → (allow, "lyrics_unavailable", 0) │  │
│      │                                                         │  │
│      │  Tier 3: ProfanityScanner.scan(lyrics)                  │  │
│      │      → severity >= min → (skip, "profanity", severity) │  │
│      │      → otherwise       → (allow, "clean", severity)    │  │
│      │                                                         │  │
│      └─── returns tuple[str, str, int]  ◄───────────────────── ┘  │
│                                                                   │
│      ▼                                                            │
│  skip decision → SocoSkipClient or SpotifySkipClient             │
│      │                                                            │
│      ▼                                                            │
│  _append_skip_event({"type","track","artist","reason","timestamp"})│
│      │ writes to data/skip_events.jsonl                          │
│      ▼                                                            │
│  skip_event_queue.put_nowait(event)                               │
└──────────────────────────────────────────────────────────────────┘
           │ file-based IPC
           ▼
┌──────────────────────────────────────────────────────────────────┐
│  web_ui (FastAPI)                                                 │
│  _file_tail() reads skip_events.jsonl → SSE → browser            │
└──────────────────────────────────────────────────────────────────┘
```

### System Overview (Target v1.2)

```
┌──────────────────────────────────────────────────────────────────┐
│  asyncio daemon (daemon.py)  [UNCHANGED]                          │
│                                                                   │
│  poll_loop() → track change detected                              │
│      │                                                            │
│      ▼                                                            │
│  ContentChecker.check(track) ─────────────────────────────────┐  │
│      │                                                         │  │
│      │  Tier 1: track["explicit"] → early skip                │  │
│      │                                                         │  │
│      │  Tier 2: LyricsService.get_lyrics()                     │  │
│      │      → instrumental / None → early return              │  │
│      │                                                         │  │
│      │  Tier 3a: ProfanityScanner.scan(lyrics)     [EXISTING] │  │
│      │  Tier 3b: DrugScanner.scan(lyrics)          [NEW]      │  │
│      │  Tier 3c: SexualContentScanner.scan(lyrics) [NEW]      │  │
│      │                                                         │  │
│      │  Compose results into TrackEvalResult       [NEW]      │  │
│      │      explicit: bool                                     │  │
│      │      profanity: bool                                    │  │
│      │      drug_reference: bool                               │  │
│      │      sexual_content: bool                               │  │
│      │      profanity_severity: int                            │  │
│      │      skip_reason: str                                   │  │
│      │      should_skip: bool                                  │  │
│      │                                                         │  │
│      └─── returns TrackEvalResult  ◄──────────────────────────┘  │
│                                                                   │
│      ▼                                                            │
│  skip decision reads result.should_skip                          │
│      │                                                            │
│      ▼                                                            │
│  _append_skip_event({                  [EXTENDED]                │
│      "type", "track", "artist",                                   │
│      "reason", "timestamp",                                       │
│      "explicit", "profanity",          ← NEW fields               │
│      "drug_reference", "sexual_content"                           │
│  })                                                               │
└──────────────────────────────────────────────────────────────────┘
```

---

## Component Responsibilities

| Component | Responsibility | Change in v1.2 |
|-----------|----------------|----------------|
| `daemon.py` | Polling loop, skip orchestration, event logging | Minimal — adapt to consume `TrackEvalResult` instead of bare tuple |
| `content_checker.py` | Orchestrates all detection tiers | Modified — inject two new scanners, return `TrackEvalResult` |
| `lyrics_service.py` | LRCLIB fetch + SQLite cache | None |
| `profanity_scanner.py` | Profanity word-list scan with severity | None |
| `drug_scanner.py` | Drug reference word-list scan | New file |
| `sexual_content_scanner.py` | Sexual content word-list scan | New file |
| `web_ui/main.py` | FastAPI dashboard, SSE, FSM toggle | None in v1.2 (toggle UI is v1.3) |

---

## Recommended Project Structure

```
spotify-sentiment/
├── content_checker.py          # Modified — orchestrates all scanners
├── daemon.py                   # Modified — consumes TrackEvalResult
├── drug_scanner.py             # New — drug reference detection
├── sexual_content_scanner.py   # New — sexual content detection
├── profanity_scanner.py        # Unchanged
├── lyrics_service.py           # Unchanged
├── skip_client.py              # Unchanged
├── web_ui/
│   └── main.py                 # Unchanged in v1.2
├── tests/
│   ├── test_drug_scanner.py    # New
│   ├── test_sexual_content_scanner.py  # New
│   └── test_content_checker.py # New — covers full pipeline composition
└── data/
    └── skip_events.jsonl       # Extended with new boolean fields
```

### Structure Rationale

- **Separate scanner files:** Each scanner is independently testable, independently wordlist-maintained, and independently injectable into ContentChecker. Putting all three scanners in one file would make the wordlists collide and tests harder to scope.
- **No scanner subdirectory:** The codebase is flat (profanity_scanner.py at root); stay consistent with the existing convention. A `scanners/` subdirectory would be correct at larger scale but is premature here.
- **`content_checker.py` owns composition:** The ContentChecker is already the composition point. Adding DrugScanner and SexualContentScanner as constructor-injected dependencies (same pattern as ProfanityScanner) keeps daemon.py unchanged except for the return type.

---

## Architectural Patterns

### Pattern 1: Named Dataclass Return (Replace Tuple)

**What:** Replace `tuple[str, str, int]` return from `ContentChecker.check()` with a named dataclass `TrackEvalResult` carrying independent boolean fields per signal.

**When to use:** Any time the return type carries more than two related values, or when consumers need to access individual signals rather than a positional result.

**Trade-offs:** Slightly more upfront code; named fields are unambiguous at the call site and support future field addition without breaking callers.

**Why now:** The current tuple `(action, reason, severity)` cannot express multiple independent signals cleanly. Adding drug_reference and sexual_content as additional tuple positions would produce `(action, reason, severity, drug_ref, sexual)` — positionally brittle and unreadable. A dataclass solves this definitively.

**Example:**
```python
from dataclasses import dataclass

@dataclass
class TrackEvalResult:
    should_skip: bool
    skip_reason: str          # "explicit" | "profanity" | "drug_reference" |
                              # "sexual_content" | "instrumental" |
                              # "clean" | "lyrics_unavailable" | "no_lyrics_service"
    explicit: bool
    profanity: bool
    drug_reference: bool
    sexual_content: bool
    profanity_severity: int   # 0-3, matches existing severity scale
```

The `skip_reason` field records the first-triggering reason (for display in the skip feed). The individual boolean fields record every signal independently, including signals that are true but not the primary skip reason.

### Pattern 2: Constructor-Injected Scanner (Existing Pattern, Extended)

**What:** Pass DrugScanner and SexualContentScanner into ContentChecker via `__init__`, exactly as ProfanityScanner is injected today.

**When to use:** Always — this is the existing pattern. Do not change it.

**Trade-offs:** All wiring is in `daemon.py:main()`, which is the only place that constructs ContentChecker. Tests can pass mocks or real instances.

**Example (daemon.py main(), additions only):**
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

ContentChecker's `__init__` signature grows two new optional parameters (`drug_scanner=None`, `sexual_content_scanner=None`), defaulting to None so that tests that only care about profanity do not need to change.

### Pattern 3: Wordlist Scanner (Mirrors ProfanityScanner)

**What:** Drug and sexual content scanners follow the same structural pattern as ProfanityScanner — a module-level word dict, a class with a `scan(lyrics: str) -> tuple[bool, list[str]]` method, word normalization (lowercase, strip punctuation), word-boundary-aware matching.

**When to use:** For all keyword-based content detection in this codebase.

**Trade-offs:** Simple, fast, fully inspectable, no network dependency, no library dependency. Misses obfuscated variants and euphemistic coded language (e.g., "Mary Jane", "snow" for cocaine) — this is accepted scope for v1.2. Better-profanity fallback (leet-speak obfuscation) is already covering the profanity tier; drug and sexual scanners do not need it because the obfuscation patterns for those domains differ significantly and the false-positive cost is higher.

**Return type:** `tuple[bool, list[str]]` (detected: bool, matched_words: list). Differs from ProfanityScanner which returns `tuple[int, list[str]]` (severity, matched). Drug and sexual detection are boolean in v1.2 — no severity tiers needed yet. This simplifies the scanner API.

**Example (DrugScanner structure):**
```python
DRUG_TERMS: dict[str, int] = {
    # common terms — key is lowercase canonical form
    "cocaine": 1, "coke": 1, "crack": 1,
    "heroin": 1, "smack": 1,
    "meth": 1, "methamphetamine": 1, "crystal": 1,
    "weed": 1, "marijuana": 1, "cannabis": 1, "blunt": 1,
    "molly": 1, "ecstasy": 1, "mdma": 1,
    "xanax": 1, "lean": 1, "codeine": 1, "syrup": 1,
    "acid": 1, "lsd": 1, "shrooms": 1,
    # ... extend as needed
}

class DrugScanner:
    def scan(self, lyrics: str) -> tuple[bool, list[str]]:
        ...
```

The severity integer in the dict is unused at v1.2 but preserved for forward compatibility if per-category severity is added later.

---

## Data Flow

### Full Detection Flow (v1.2)

```
Spotify track object
    │
    ▼ [Tier 1 — daemon.py poll_loop, before ContentChecker]
track["explicit"] == True
    → TrackEvalResult(should_skip=True, skip_reason="explicit", explicit=True, ...)
    → skip immediately, log event

    [Tier 2 — inside ContentChecker.check()]
LyricsService.get_lyrics(track_id, track_name, artist_name)
    → LyricsResult(instrumental=True)
        → TrackEvalResult(should_skip=False, skip_reason="instrumental", ...)
    → LyricsResult(lyrics=None)
        → TrackEvalResult(should_skip=False, skip_reason="lyrics_unavailable", ...)

    [Tier 3 — all three scanners run on same lyrics string]
    lyrics text (plain string)
        │
        ├── ProfanityScanner.scan(lyrics)  → (severity: int, matched: list[str])
        ├── DrugScanner.scan(lyrics)       → (detected: bool, matched: list[str])
        └── SexualContentScanner.scan(lyrics) → (detected: bool, matched: list[str])
        │
        ▼
    Compose TrackEvalResult:
        explicit          = False (already past Tier 1)
        profanity         = severity >= min_severity
        drug_reference    = drug_detected
        sexual_content    = sexual_detected
        profanity_severity = severity
        should_skip       = profanity OR drug_reference OR sexual_content
        skip_reason       = first True signal ("profanity" | "drug_reference" | "sexual_content" | "clean")
        │
        ▼
daemon.py poll_loop receives TrackEvalResult
    │
    ├── result.should_skip == False → consecutive_skips = 0, no action
    │
    └── result.should_skip == True
            │
            ├── skip via SocoSkipClient or SpotifySkipClient
            │
            └── _append_skip_event({
                    "type": "skip",
                    "track": ..., "artist": ..., "timestamp": ...,
                    "reason": result.skip_reason,
                    "explicit": result.explicit,
                    "profanity": result.profanity,
                    "drug_reference": result.drug_reference,
                    "sexual_content": result.sexual_content,
                })
                → data/skip_events.jsonl (append)
                → skip_event_queue.put_nowait (in-process)
```

### Key Data Flows

1. **Lyrics → detection:** A single `lyrics: str` string passes through all three Tier 3 scanners independently. Each scanner normalizes independently (lowercase, strip punctuation). They do not share state.

2. **Detection → skip decision:** ContentChecker composes the three scan results into a single `TrackEvalResult`. The skip decision is `any([profanity, drug_reference, sexual_content])`. Each boolean is preserved independently in the result — not collapsed into a single flag.

3. **TrackEvalResult → incident log:** daemon.py serialises all four signal booleans into the skip event JSON. This means the log records not just why a track was skipped but every signal that fired, including secondary signals. A track skipped for profanity that also contains drug references will show both flags in the log.

4. **Incident log → web UI:** The web UI reads skip_events.jsonl via file-tail. The new boolean fields are present in each event; the dashboard can display them. The v1.2 dashboard does not need to change to function — new fields are additive to the JSON. The v1.3 milestone adds per-category toggle UI that will read these fields to show which signals are active per event.

---

## Toggle Readiness: Named Booleans Enable v1.3

The v1.3 milestone (currently deferred) requires per-category toggle UI: the parent can disable drug detection, sexual detection, or profanity detection independently. The named-boolean architecture in v1.2 makes this straightforward:

**v1.3 additions (no v1.2 changes required):**

1. `state.json` gains three new keys: `filter_drug`, `filter_sexual`, `filter_profanity` — all `true` by default.
2. ContentChecker reads these flags from the state and gates each scanner's contribution to `should_skip`:
   ```
   should_skip = (filter_profanity AND profanity) OR
                 (filter_drug AND drug_reference) OR
                 (filter_sexual AND sexual_content)
   ```
3. Web UI adds three toggle buttons. Each writes the corresponding state key via a new `/fsm/filters` POST endpoint.

Because each detection signal is already a named boolean on `TrackEvalResult`, and because the incident log already stores all four booleans per event, the v1.3 toggle implementation requires no changes to the scanner layer or the incident log format. Only the skip decision logic in ContentChecker and the web UI need to change.

If v1.2 instead stored a single `skip_reason` string and collapsed all signals into one, v1.3 would require retrofitting the detection and logging layers. The named-boolean pattern avoids that retrofit.

---

## Integration Points

### New vs. Modified Components

| Component | Status | Change |
|-----------|--------|--------|
| `drug_scanner.py` | New file | Drug term wordlist + `DrugScanner.scan()` returning `tuple[bool, list[str]]` |
| `sexual_content_scanner.py` | New file | Sexual content wordlist + `SexualContentScanner.scan()` returning `tuple[bool, list[str]]` |
| `content_checker.py` | Modified | Accept two new constructor args; run all three scanners; return `TrackEvalResult` instead of tuple |
| `daemon.py` | Modified | Consume `TrackEvalResult` fields instead of tuple unpacking; extend `_append_skip_event()` with four boolean fields |
| `tests/test_drug_scanner.py` | New file | Unit tests for drug wordlist matches and non-matches |
| `tests/test_sexual_content_scanner.py` | New file | Unit tests for sexual content wordlist |
| `tests/test_content_checker.py` | New file | Integration tests for full pipeline composition with all signals |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `daemon.py` → `ContentChecker` | Direct method call: `await content_checker.check(track)` returns `TrackEvalResult` | Currently returns `tuple[str, str, int]`; this is the one breaking change in v1.2 |
| `ContentChecker` → `DrugScanner` / `SexualContentScanner` | Direct synchronous call: `self.drug_scanner.scan(lyrics)` | Same call pattern as `self.profanity_scanner.scan(lyrics)`; no async needed (CPU-bound wordlist scan) |
| `daemon.py` → `skip_events.jsonl` | File append via `_append_skip_event()` | JSON schema extended with four new boolean fields; additive change, backward-compatible with existing log entries |
| `skip_events.jsonl` → `web_ui` | File-tail polling every 250ms | Web UI just forwards the JSON; new fields are transparent until the UI template renders them |

---

## Build Order

The natural dependency order for implementation:

1. **Define `TrackEvalResult` dataclass** (can live in `content_checker.py` or a new `models.py`) — all other changes depend on this type being finalized first.

2. **Implement `DrugScanner`** — no dependencies on other new code; straightforward wordlist scan matching `ProfanityScanner` structure.

3. **Implement `SexualContentScanner`** — same as above; can be done in parallel with step 2.

4. **Write unit tests for both new scanners** — before wiring into ContentChecker; verifies wordlists behave correctly in isolation.

5. **Modify `ContentChecker`** — inject new scanners, run all three, compose `TrackEvalResult`. This is the integration step.

6. **Write integration tests for ContentChecker** — cover combinations of signals (e.g., both drug and profanity fire; only sexual fires; none fire).

7. **Modify `daemon.py`** — update the two call sites that unpack the ContentChecker result: the `action/reason/severity = await content_checker.check(track)` unpacking and the `_append_skip_event()` call.

8. **Verify end-to-end** — run daemon locally or via tests to confirm skip_events.jsonl entries include the new boolean fields.

Steps 2 and 3 have no mutual dependency and can be done in either order. Steps 1-4 should complete before step 5 to avoid changing ContentChecker twice.

---

## Anti-Patterns

### Anti-Pattern 1: Extending the Tuple Return

**What people do:** Add `drug_ref` and `sexual_content` as two more positions on the existing `tuple[str, str, int]` return.

**Why it's wrong:** Produces `tuple[str, str, int, bool, bool]` — callers must unpack by position, which is fragile and unreadable. Adding a sixth signal in v1.3 requires touching every call site again.

**Do this instead:** `TrackEvalResult` dataclass. Named fields, additive extension, explicit types. The refactor from tuple to dataclass is a one-time cost that pays off across v1.2, v1.3, and beyond.

### Anti-Pattern 2: One Combined Scanner Class

**What people do:** Add `scan_drug()` and `scan_sexual()` as methods on `ProfanityScanner` or on `ContentChecker`.

**Why it's wrong:** A scanner class with three domains of wordlists becomes a kitchen-sink module. Tests for drug detection cannot be run without instantiating profanity infrastructure. Wordlists from different domains clutter the same namespace. If one scanner needs a different normalization strategy (e.g., multi-word phrase matching for "Mary Jane"), it cannot be changed without affecting the others.

**Do this instead:** Three separate scanner classes with identical method signatures. ContentChecker owns composition. Each scanner is independently testable, independently replaceable.

### Anti-Pattern 3: Collapsing Signals Into a Single Skip Reason

**What people do:** Compute `should_skip` and record only the triggering reason in the event log (e.g., `"reason": "drug_reference"` with no record of the profanity that also fired).

**Why it's wrong:** The incident log becomes ambiguous. If a track has both drug references and profanity, only one signal is recorded. The v1.3 per-category toggle cannot retroactively know which signals would have fired under different filter settings.

**Do this instead:** Log all four signal booleans in every skip event, regardless of which one drove the skip decision. The `skip_reason` field records the first-triggering reason for display; the boolean fields record the full picture.

### Anti-Pattern 4: Running Scanners Before Lyrics Are Available

**What people do:** Run all scanners in sequence without short-circuiting on instrumental or missing lyrics.

**Why it's wrong:** Wastes CPU on wordlist scans against a None lyrics string, requires null guards in every scanner, and produces misleading results (no drug references detected because there were no lyrics).

**Do this instead:** Maintain the existing early-return structure in ContentChecker — instrumental and lyrics_unavailable return before reaching Tier 3. All three scanners only run when `lyrics: str` is a non-None, non-empty string.

---

## Scalability Considerations

This is a single-user, single-process application. Scalability is not a concern for v1.2. Notes for completeness:

| Concern | At current scale (1 user) | Notes |
|---------|--------------------------|-------|
| Scanner latency | Negligible (<1ms for wordlist scan) | Three wordlist scans on a ~2KB lyrics string are fast |
| Wordlist maintenance | Low — manual updates | No automated refresh needed; wordlists are static |
| False positive rate | Medium — wordlist-only | "Crystal" matches crystal meth references but also "crystal clear"; context-free matching is the known tradeoff |
| Signal coverage | Low for coded language | "Mary Jane", "snow", "lean" coverage depends on wordlist completeness; LLM-based detection (deferred v2+) would close this gap |

---

## Sources

- Direct code inspection: `content_checker.py`, `daemon.py`, `profanity_scanner.py`, `lyrics_service.py`, `web_ui/main.py` — HIGH confidence
- Existing signal structure in `data/skip_events.jsonl` — HIGH confidence
- Project requirements in `.planning/PROJECT.md` — HIGH confidence
- Prior architecture research in `.planning/research/LYRICS_FILTERING.md` (section 7 on sentiment analysis) — MEDIUM confidence (deferred path, not v1.2 path)

---
*Architecture research for: Drug and sexual content detection integration — v1.2 milestone*
*Researched: 2026-04-02*
