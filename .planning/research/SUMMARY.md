# Project Research Summary

**Project:** Spotify Family Safe Mode — v1.3 Drug & Sexual Content Detection
**Domain:** Keyword-based content signal detection — Python content filter extension
**Researched:** 2026-04-03
**Confidence:** HIGH

## Executive Summary

v1.3 is a well-bounded extension to an already-working content filter pipeline. The existing daemon has `ContentChecker`, `ProfanityScanner`, `LyricsService`, and a badge-group dashboard that were deliberately designed as an extensibility foundation. Adding drug reference and sexual content detection means wiring two new scanner modules into an established pattern — the architecture is already correct; the work is execution, not design.

The recommended approach is entirely Python stdlib: `re.compile` with `\b` word-boundary anchors for keyword matching, `@dataclass(frozen=True)` for the new named return type, and project-owned `frozenset` keyword lists. No new PyPI dependencies are required. The `TrackEvalResult` dataclass refactor (replacing the current `(action, reason, severity)` 3-tuple) is the hard prerequisite for everything else and must ship as a single atomic commit. Both new scanners are then independent pure functions that plug into `ContentChecker` via the same injection pattern already used for `ProfanityScanner`.

The principal risk is not technical — it is false positives destroying parent trust. Drug vocabulary heavily overlaps with everyday English ("high", "smoke", "grass", "roll", "blow"). A high-recall keyword list that flags family-friendly songs will cause parents to disable Family Safe Mode entirely. The correct v1.3 posture is a short, high-precision list of unambiguous terms, with the expectation that some drug references will be missed. The same conservative approach applies to sexual content: `SEXUAL_TERMS` must not duplicate words already in `SEVERITY_MAP`, and the initial list should focus only on unambiguous terms absent from the profanity scanner.

## Key Findings

### Recommended Stack

No new dependencies. All capabilities are available in Python 3.12 stdlib. The three technical choices are: `re.compile` (word-boundary matching), `@dataclass` (named return type), and `frozenset` (keyword backing store). This is the entire stack delta for v1.3.

The `re.compile` approach is preferred over the profanity scanner's word-split + dict lookup pattern because it handles punctuation boundaries natively via `\b` and is composable for potential multi-word phrase additions. Patterns must be compiled once at module load — not inside `scan()` on every call.

**Core technologies:**
- `re` (stdlib): Word-boundary keyword matching — `\b` anchors prevent substring false positives; `re.IGNORECASE` avoids allocation overhead of `.lower()`; `re.search` short-circuits on first match for boolean detection
- `dataclasses` (stdlib): `TrackEvalResult` named return type — `frozen=True` enforces immutability; `slots=True` reduces per-instance memory; default field values mean existing test mocks constructing `TrackEvalResult(action=..., reason=..., severity=...)` continue to work when new fields are added
- `frozenset` (builtin): Keyword list backing store — O(1) membership testing; immutable; communicates intent that these are fixed canonical sets

### Expected Features

v1.3 delivers two new boolean detection signals and one structural refactor. Industry content advisory systems (ESRB, RIAA, IMDB) consistently treat drug reference and sexual content as discrete boolean categories, not severity tiers. For children ages 3 and 7, any drug reference or sexual content warrants a skip — the severity distinction has no actionable effect.

**Must have (table stakes):**
- `TrackEvalResult` dataclass replacing positional 3-tuple — hard prerequisite; unlocks all other work
- `DrugScanner` in `drug_scanner.py` with high-confidence `DRUG_TERMS` frozenset — unambiguous drug names and slang only; omit ambiguous terms like "high", "smoke", "grass"
- `SexualContentScanner` in `sexual_content_scanner.py` with conservative `SEXUAL_TERMS` frozenset — disjoint from `SEVERITY_MAP`; focus on terms the profanity scanner misses
- Both signals trigger `action='skip'` when FSM is active
- Both signals logged in `skip_events.jsonl` with new reason strings (`"drug_reference"`, `"sexual_content"`)
- Dashboard badge variants for drug-reference and sexual-content in the skip feed

**Should have (differentiators):**
- Matched terms included in internal debug logs (not in JSONL events — see Pitfall 7 on security)
- `SEXUAL_TERMS` disjoint-from-`SEVERITY_MAP` unit test — prevents future regression
- `isinstance(result, TrackEvalResult)` smoke test — catches missed migration sites

**Defer (v2+):**
- Severity tiers for drug or sexual signals — no actionable effect on skip behavior for ages 3 and 7
- Per-category enable/disable toggles — requires UI changes beyond v1.3 scope
- Phrase matching for sexual content ("making love", "netflix and chill")
- Alcohol/tobacco as a separate configurable signal
- LLM/NLP contextual detection to reduce false positives

### Architecture Approach

v1.3 adds two new scanner modules that mirror `profanity_scanner.py` exactly, extends `ContentChecker` with scanner injection, replaces the 3-tuple return type with a named dataclass, and propagates two new boolean fields through the existing file-based IPC chain. The `web_ui/main.py` FastAPI server requires zero changes — new JSON fields pass through its `json.loads/json.dumps` SSE bridge verbatim. Only `daemon.py` call sites and `index.html` badge logic require updates beyond the new modules.

**Major components:**
1. `drug_scanner.py` (new) — `DrugScanner` with module-level compiled regex; `scan(lyrics) -> tuple[bool, list[str]]`
2. `sexual_content_scanner.py` (new) — `SexualContentScanner`, same structure; `SEXUAL_TERMS` must be disjoint from `SEVERITY_MAP`
3. `content_checker.py` (modified) — `TrackEvalResult` dataclass defined here; `check()` return type updated; both new scanners injected via `__init__` kwargs with `None` defaults; all three scans run unconditionally once lyrics are available (no short-circuit on profanity)
4. `daemon.py` (modified) — 10 mock call sites in tests updated; all 4 `_append_event` / `_write_now_playing` call sites updated with new boolean fields; a `_emit_eval_result` helper should be extracted to avoid the 4-site update problem
5. `web_ui/templates/index.html` (modified) — `badge--drug` and `badge--sexual` CSS classes; `setBadgeClass()`, `badgeLabel()`, `setEvalBadge()` extended

### Critical Pitfalls

1. **Substring matching on common words** — Never use `term in lyrics` or bare `re.search(term, lyrics)`. Always compile with `r'\b(?:term1|term2)\b'` word-boundary anchors. Test against a known-clean song corpus before merging. "High Hopes", "Here Comes the Sun", and "Puff the Magic Dragon" must produce zero false positives.

2. **`SEXUAL_TERMS` duplicating `SEVERITY_MAP` words** — `dick`, `cock`, `pussy`, `whore`, `slut`, `tits`, `wank`, `twat` are already in `SEVERITY_MAP` at severity 2. Adding them to `SEXUAL_TERMS` creates double-flagging with no behavior change. Enforce with a `isdisjoint` assertion unit test that must pass before any other scanner test.

3. **3-tuple to `TrackEvalResult` migration breaking call sites silently** — Python will not raise at import time; it raises `TypeError` only when the unpack executes. All 10 mock return values in `test_daemon_events.py` and all `return (...)` statements in `content_checker.py` must be updated in a single atomic commit. Add `from content_checker import TrackEvalResult` to the test file. Verify with grep for zero remaining bare-tuple unpack patterns.

4. **New boolean fields absent from some `eval_result` code paths** — `daemon.py` emits `eval_result` events from 4 separate inline dict-construction call sites. Missing one means inconsistent events: some carry `drug_reference` and `sexual_content`, others do not. Extract a `_emit_eval_result` helper before adding the new fields, so all 4 paths are covered in one change.

5. **`now_playing.json` not updated in sync with `eval_result` events** — The SSE stream and the JSON hydration endpoint are written from separate call sites. Drug/sexual badges visible in the live feed will disappear on page reload if `_write_now_playing` is not updated with the same new fields. The `_emit_eval_result` helper from pitfall 4 should call both `_append_event` and `_write_now_playing` to keep them in sync automatically.

## Implications for Roadmap

Based on research, the build order is driven by a single hard prerequisite (the dataclass refactor) followed by parallel independent work (scanner modules), followed by wiring, propagation, and UI in that order.

### Phase 1: TrackEvalResult Dataclass Refactor

**Rationale:** The dataclass migration is a pure refactor with zero behavior change and zero new features, but it is the hard prerequisite for Phases 2-5. Every subsequent phase writes to and reads from named attributes on `TrackEvalResult`. Doing this first as an isolated commit means the test suite can be confirmed green before any new detection logic is added. If done last or interleaved, a failing migration will be difficult to isolate from failing detection logic.
**Delivers:** `TrackEvalResult` dataclass in `content_checker.py`; all 5 `return (...)` statements in `check()` replaced; `daemon.py` attribute access updated; all 10 test mocks updated; test suite green with no behavior change.
**Addresses:** Table-stakes feature — `TrackEvalResult` named dataclass (P1 from FEATURES.md)
**Avoids:** Pitfall 3 (tuple migration silently breaking call sites) — atomic commit, grep verification, smoke test

### Phase 2: Scanner Modules

**Rationale:** `DrugScanner` and `SexualContentScanner` are pure functions with no dependencies on each other and no dependency on the rest of the pipeline. They receive a lyrics string and return a `(bool, list[str])` tuple. Both can be written and unit-tested in complete isolation before any wiring occurs. Developing them before Phase 3 means ContentChecker integration can be tested against real scanner classes rather than mocks.
**Delivers:** `drug_scanner.py` with curated high-confidence `DRUG_TERMS` frozenset and compiled regex; `sexual_content_scanner.py` with conservative `SEXUAL_TERMS` frozenset (disjoint from `SEVERITY_MAP`); unit tests in `test_drug_scanner.py` and `test_sexual_content_scanner.py`; disjoint-from-`SEVERITY_MAP` assertion test passing.
**Uses:** `re` stdlib, `frozenset` builtin — zero new dependencies
**Avoids:** Pitfall 1 (substring matching); Pitfall 2 (SEVERITY_MAP overlap); Pitfall 6 (ambiguous drug terms)

### Phase 3: ContentChecker Pipeline Integration

**Rationale:** Depends on Phase 1 (`TrackEvalResult` exists) and Phase 2 (scanner classes exist). Wires both scanners into `ContentChecker.__init__` as optional injection parameters (default `None`), adds them to the `check()` pipeline after the profanity scan, and aggregates results into `TrackEvalResult` fields. All three scans must run unconditionally — do not short-circuit on profanity.
**Delivers:** `ContentChecker` wired with `DrugScanner` and `SexualContentScanner`; `TrackEvalResult` fields `drug_reference`, `drug_terms`, `sexual_content`, `sexual_terms` populated; `daemon.py` instantiation updated; `test_content_checker.py` extended for all new pipeline paths.
**Implements:** ContentChecker filter pipeline (Architecture section)
**Avoids:** Short-circuiting drug/sexual scans when profanity fires

### Phase 4: Event Propagation and Incident Log

**Rationale:** Depends on Phase 3 (ContentChecker now populates the new fields). The recommended approach is to extract a `_emit_eval_result` helper in `daemon.py` first, then add the two new boolean fields in that single helper rather than updating 4 inline dict-construction call sites. Both `_append_event` and `_write_now_playing` should be called from this helper to guarantee `events.jsonl` and `now_playing.json` stay in sync.
**Delivers:** `drug_reference` and `sexual_content` booleans in all `eval_result` and `skip` events; same fields in `now_playing.json`; `test_daemon_events.py` updated with field assertions.
**Avoids:** Pitfall 4 (missing fields on some code paths); Pitfall 5 (now_playing.json not updated)

### Phase 5: Dashboard Badge Variants

**Rationale:** Depends on Phase 4 (SSE events and `/now-playing` now carry the boolean fields). CSS badge classes must be defined before JS tries to assign them. Extend `setBadgeClass()`, `badgeLabel()`, and `setEvalBadge()` independently — do not overload `severity` to signal drug/sexual content. Guard all JS reads with `?? false` for backward compatibility with pre-v1.3 events in the log.
**Delivers:** `badge--drug` and `badge--sexual` CSS classes; extended badge JS; visual skip feed showing distinct badge types for drug-reference and sexual-content skips.
**Avoids:** Pitfall 7 (sexual-content / profanity badge collision); UX pitfall (no visual distinction in incident log)

### Phase Ordering Rationale

- Phase 1 before all others: the dataclass is a hard structural prerequisite; isolating it as a no-behavior-change refactor lets CI confirm green before new logic is added
- Phase 2 before Phase 3: scanner modules are pure functions that can be unit-tested in isolation; wiring them into ContentChecker after they are tested independently reduces debugging surface
- Phase 3 before Phase 4: ContentChecker must populate `TrackEvalResult` fields before daemon can propagate them to events
- Phase 4 before Phase 5: dashboard needs the boolean fields to arrive in SSE events before JS can render badges
- The `_emit_eval_result` helper extraction in Phase 4 is a prerequisite within that phase, not its own numbered phase

### Research Flags

Phases with standard patterns (skip research-phase):
- **Phase 1 (Dataclass Refactor):** Well-documented stdlib `@dataclass` pattern; exhaustive call-site inventory already compiled in ARCHITECTURE.md
- **Phase 2 (Scanner Modules):** Standard `re.compile` + `frozenset` pattern; keyword list content is domain judgment, not a research question
- **Phase 3 (ContentChecker Integration):** Mirrors existing `ProfanityScanner` injection pattern exactly; no novel architecture
- **Phase 4 (Event Propagation):** JSON field addition through existing JSONL pipeline; no novel architecture
- **Phase 5 (Dashboard Badges):** Extends existing `badge-group` CSS/JS pattern from v1.2

No phases require `/gsd:research-phase` during planning. All patterns are well-documented and the existing codebase provides direct precedent for every change required.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All findings based on official Python docs and direct codebase inspection; zero external dependencies reduce uncertainty |
| Features | HIGH | Based on direct code inspection of v1.2, ESRB/RIAA official documentation, and explicit PROJECT.md v1.3 milestone requirements |
| Architecture | HIGH | All findings based on direct inspection of every production and test file in the codebase; exhaustive call-site inventory compiled |
| Pitfalls | HIGH | All pitfalls identified from direct codebase inspection of real production code; not inferred from external sources |

**Overall confidence:** HIGH

### Gaps to Address

- **Drug keyword list completeness:** The research provides a high-confidence seed list but the final term selection is a domain judgment call for the implementation team. Terms like "dope", "bars", "plug", and "trap" are noted as medium-confidence with real false-positive risk. Plan for a manual review pass against a clean-song corpus before merging the keyword list. This is an implementation quality gate, not a design question.

- **Sexual content keyword list size:** The safe, high-confidence core set for sexual content is intentionally small because most sexual slang either appears in `SEVERITY_MAP` already or is too context-dependent for keyword-only detection. The v1.3 list (`naked`, `nude`, `nudes`, `porn`, `pornography`, `orgasm`, `masturbate`, `masturbation`) is conservative by design — the profanity scanner covers the primary detection vector. Accept this gap.

- **`_eval_state_from_result` helper in `daemon.py` (line 147):** ARCHITECTURE.md identifies this as a migration target. Whether it should accept a `TrackEvalResult` or remain taking positional `action`/`reason` strings is a minor implementation decision to confirm during Phase 1.

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection: `content_checker.py`, `daemon.py`, `profanity_scanner.py`, `lyrics_service.py`, `web_ui/main.py`, `web_ui/templates/index.html`, `tests/test_daemon_events.py` — all architecture and pitfall findings
- Python official docs: `re` module, `dataclasses` module — stack technology rationale
- `.planning/PROJECT.md` v1.3 milestone section — feature scope, deferred items
- ESRB content descriptors (https://www.esrb.org/ratings-guide/) — boolean category model for drug/sexual signals
- RIAA Parental Advisory evolution — boolean three-category model confirmation

### Secondary (MEDIUM confidence)
- PMC study on drug-related lyrics (190-keyword corpus) — drug keyword taxonomy seed list
- LYDIA alcohol detection algorithm (PMC) — word-based detection; false-positive analysis for ambiguous terms
- arxiv.org sexual content detection study — confirms 61% F1 for dictionary-based approach; supports conservative list strategy

### Tertiary (LOW confidence)
- BurntRouter/filtered-word-lists (GitHub) — reviewed as candidate keyword source; not recommended (no drug category, no maintenance signal)
- Drug slang lists from recovery resource sites — consulted for slang term awareness only; evolve rapidly; used for initial term selection only

---
*Research completed: 2026-04-03*
*Ready for roadmap: yes*
