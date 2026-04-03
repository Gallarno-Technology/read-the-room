# Project Research Summary

**Project:** Spotify Family Safe Mode — v1.2 Drug & Sexual Content Detection
**Domain:** Lyric-based content filtering — drug reference and sexual content signals
**Researched:** 2026-04-02
**Confidence:** HIGH

---

## Executive Summary

This milestone adds two new boolean detection signals — drug references and sexual content — to an existing three-tier lyric filter pipeline. The current pipeline already fetches lyrics (LRCLIB + SQLite cache) and runs profanity scanning; the new signals slot in as Tier 3b and 3c alongside the existing `ProfanityScanner`. Research is grounded in direct codebase inspection and confirms the architecture is well-understood. The recommended approach is a generic `KeywordScanner` class instantiated twice with separate curated word lists, using compiled regex alternation with `\b` word boundaries to handle both single-word and multi-word phrase matching correctly. No new dependencies are required.

The central implementation risk is false positives, not false negatives. Academic literature and practical content moderation research consistently show that word-list approaches have acceptable precision only when the list is deliberately conservative — preferring multi-word phrases over ambiguous single words and explicitly excluding high-polysemy terms like "high", "lean", "blow", "roll", and "pot". A false positive (skipping a song the family wants) collapses parent trust in the filter faster than a false negative (missing a drug reference). The initial lists should be 30–50 unambiguous phrases and expanded only after reviewing real-world skip log data.

The one structural change that must land before new signals can be added cleanly is replacing the `ContentChecker.check()` return type from a positional 3-tuple `(action, reason, severity)` to a named `TrackEvalResult` dataclass. This is a targeted one-commit refactor that touches `content_checker.py`, `daemon.py`, and existing tests together. All subsequent signal additions — including the v1.3 per-category toggle UI — depend on this named-field structure being in place.

---

## Key Findings

### Recommended Stack

No new PyPI dependencies are required. The Python standard library `re` module with compiled alternation patterns handles all matching needs. For term lists under ~500 entries at the keyword counts appropriate for this milestone, a pre-compiled `re.compile(r'\b(?:term1|term2|...)\b', re.IGNORECASE)` pattern is fast enough that there is no measurable startup or scan-time benefit from `pyahocorasick`. `pyahocorasick 2.3.0` is confirmed Python 3.12 compatible and is the correct upgrade path if the term list ever grows beyond ~500 entries. `better-profanity 0.7.0` is unchanged and must not be extended with drug or sexual terms because doing so would corrupt the existing profanity severity signal.

**Core technologies:**
- `re` (stdlib, Python 3.12): Compiled regex alternation for keyword and phrase matching — zero dependencies, handles word boundaries and multi-word phrases in one pass
- `better-profanity 0.7.0`: Unchanged — still used for leet-speak obfuscation fallback in `ProfanityScanner` only; do not extend it with new categories
- `pytest` / `pytest-asyncio`: Existing test infrastructure covers all new scanner unit tests and pipeline integration tests without modification

### Expected Features

Research confirms a tight, well-defined MVP. All table-stakes features are low-complexity because the infrastructure (lyrics fetch, content check orchestration, skip logic, incident log) already exists.

**Must have (table stakes — v1.2):**
- Drug reference boolean signal on track evaluation — single-pass keyword scan returning `(detected: bool, matched: list[str])`
- Sexual content boolean signal on track evaluation — same interface, separate scanner
- Independent named boolean fields on evaluation result (`drug_reference`, `sexual_content`) — required for v1.3 toggle UI to wire in without a retrofit
- Both signals written to `skip_events.jsonl` — parent needs to see why a track was skipped
- Skip triggered on either new signal when Family Safe Mode is active — behaviorally identical to a profanity skip
- Conservative curated word lists (~30–50 phrases) with documented rationale for exclusions

**Should have (differentiators — v1.2):**
- Matched-term logging alongside boolean signal — parent sees "blunt, weed" not just "drug reference detected"
- Explicit deduplication against `SEVERITY_MAP` in `profanity_scanner.py` — sexual content list must not include words already in the profanity tier to avoid ambiguous skip reasons and double-fire
- `allow_on_unavailable` behavior preserved — new scanners run only when `lyrics` is a non-None, non-empty string; no change to existing FILT-05 logic

**Defer (v2+):**
- Severity scoring within drug / sexual categories — boolean is sufficient to drive skip/allow; severity requires editorial consensus that does not exist yet
- Semantic / LLM-based euphemism detection — explicitly deferred in PROJECT.md as "Sentiment NLP — too complex for v1"
- Alcohol detection category — pervasiveness in mainstream music requires its own toggle before it is useful
- Per-child profile filtering tiers — out of scope for v1.x

### Architecture Approach

The v1.2 architecture extends the existing three-tier pipeline minimally. `daemon.py` is structurally unchanged except for consuming a `TrackEvalResult` dataclass instead of a positional tuple. `ContentChecker` gains two constructor-injected scanner instances following the exact pattern already used for `ProfanityScanner`. Two new files (`drug_scanner.py`, `sexual_content_scanner.py`) each contain a wordlist and a scanner class with a `scan(lyrics: str) -> tuple[bool, list[str]]` interface. A new `TrackEvalResult` dataclass replaces the `tuple[str, str, int]` return and carries named boolean fields for all four signals plus `should_skip` and `profanity_severity`. The incident log format is extended additively — new boolean fields are appended to the existing JSON schema, so the web UI continues to function without changes in v1.2.

**Major components:**
1. `TrackEvalResult` dataclass — named return type for `ContentChecker.check()`; central to all other changes; defines the named boolean contract consumed by daemon, tests, and v1.3 toggle logic
2. `DrugScanner` (new file) — drug term wordlist + `scan()` returning `(bool, list[str])`; constructor-injected into `ContentChecker`
3. `SexualContentScanner` (new file) — sexual content wordlist + `scan()` returning `(bool, list[str])`; constructor-injected into `ContentChecker`
4. `ContentChecker` (modified) — orchestrates Tier 3a/3b/3c; composes `TrackEvalResult`; `should_skip = profanity OR drug_reference OR sexual_content`
5. `daemon.py` (modified) — consumes `TrackEvalResult` fields via attribute access; extends `_append_skip_event()` with four signal booleans

### Critical Pitfalls

1. **Substring matching causes mass false positives** — Never use raw `in` substring checks (`any(word in lyrics for word in keywords)`). Python's `in` operator matches substrings: "high" matches "highlight", "cock" matches "cocktail", "ass" matches "classroom". Use `re.compile(r'\b(?:...)\b', re.IGNORECASE)` with word boundaries from the start. Longest-first term ordering in the alternation prevents partial-phrase matches. Add explicit word-boundary unit tests before integrating into ContentChecker.

2. **Overly broad single-word keyword lists erode parent trust** — Importing a high-recall drug slang list wholesale produces constant false positives on classic rock, gospel, and jazz. "High" appears in hymns. "Blow" is a Miles Davis album. "Roll" is in the name of a genre. Start conservative (30–50 multi-word phrases), log matched terms, review the first 20 real-world matches before expanding. The false positive rate collapsing trust is a worse outcome than missing coded euphemisms. The keyword list size gate should fail CI if either list exceeds 80 entries.

3. **Return type change breaks ContentChecker integration contract** — The existing `action, reason, severity = await content_checker.check(track)` tuple unpacking in `daemon.py` will raise `ValueError` the moment the return type changes. Refactor to `TrackEvalResult` dataclass in a single commit that updates ContentChecker, daemon, and all existing tests simultaneously. Do this before adding any new signals.

4. **Scan results cached in SQLite become stale after wordlist changes** — Do not add `drug_detected` or `sexual_detected` columns to the `lyrics_cache` table. The cache stores immutable lyrics text; detection results are mutable (wordlist changes). Scan in memory on every play from cached lyrics text — the scan takes less than 1ms and re-scanning is always correct.

5. **`better-profanity` and new sexual content list double-fire** — `better-profanity`'s default word list overlaps with many sexual terms. Words already in `SEVERITY_MAP` (cock, pussy, slut, whore, tits, dick) must not be added to the sexual content scanner list. Cross-reference `SEVERITY_MAP` explicitly during list construction and enforce the disjointness with an assertion test: `assert set(SEXUAL_TERMS) & set(SEVERITY_MAP.keys()) == set()`.

---

## Implications for Roadmap

Based on the build-order dependencies identified in ARCHITECTURE.md and the pitfall prevention requirements, the natural phase structure for v1.2 is:

### Phase 1: Return Type Refactor

**Rationale:** The `ContentChecker.check()` return type must change from `tuple[str, str, int]` to `TrackEvalResult` before any new signals can be added. Doing this first avoids doing it twice and eliminates the risk of mid-milestone breakage. It is a contained refactor with clear success criteria: all existing tests pass after the change.

**Delivers:** `TrackEvalResult` dataclass definition; updated `ContentChecker.check()`; updated `daemon.py` call sites (replace positional tuple unpack with attribute access); all existing tests green against the new return type.

**Avoids:** Pitfall 3 (return type contract break); prevents the anti-pattern of appending booleans to a positional tuple.

**Note:** This is purely structural — no new detection behavior is added in this phase.

### Phase 2: Drug Scanner

**Rationale:** DrugScanner has no dependency on SexualContentScanner and can be built and fully tested in isolation. Starting with the drug scanner establishes the implementation pattern (class structure, regex compilation with longest-first term ordering, word-boundary tests) that the sexual content scanner mirrors exactly.

**Delivers:** `drug_scanner.py` with `DrugScanner` class; curated conservative drug term list (~30–50 phrases with documented exclusion rationale); unit tests including word-boundary correctness tests for known false-positive candidates ("highway", "grasshopper", "joint venture"); no ContentChecker integration yet.

**Addresses:** Must-have drug reference detection signal; matched-term logging differentiator.

**Avoids:** Pitfall 1 (substring matching); Pitfall 2 (over-broad keyword lists); Pitfall 6 (false negative scope creep — list must stay under 80 entries).

### Phase 3: Sexual Content Scanner

**Rationale:** Mirrors Phase 2. Building it separately keeps test scope clear and allows the `SEVERITY_MAP` deduplication step to be done carefully without time pressure. Can be built in parallel with Phase 2 if two tracks are available.

**Delivers:** `sexual_content_scanner.py` with `SexualContentScanner` class; curated conservative sexual content term list focused on explicit act terms rather than body-part vocabulary; unit tests; `SEVERITY_MAP` cross-reference assertion test confirming no overlap.

**Avoids:** Pitfall 5 (`better-profanity` overlap / double-fire).

### Phase 4: ContentChecker Integration and Incident Log Extension

**Rationale:** With `TrackEvalResult` already defined (Phase 1) and both scanners tested in isolation (Phases 2–3), wiring them into ContentChecker and extending the incident log is a straightforward composition step. These two changes are a single atomic commit — daemon reads `TrackEvalResult` and writes the event; splitting them creates an intermediate state where new signals are detected but not logged.

**Delivers:** `ContentChecker` modified to accept `drug_scanner` and `sexual_content_scanner` constructor args; all three Tier 3 scanners run on the same lyrics string; `TrackEvalResult` fully populated; `_append_skip_event()` extended with `drug_reference` and `sexual_content` boolean fields in `skip_events.jsonl`.

**Implements:** Full Tier 3a/3b/3c detection flow; incident log extension.

**Avoids:** Pitfall 4 (scan results in cache — code review gate: no new SQLite columns added to `lyrics_cache`).

### Phase 5: End-to-End Validation

**Rationale:** Integration tests covering signal combinations (drug only, sexual only, both simultaneously, neither, profanity + drug simultaneously) must pass before the milestone is done. The "looks done but isn't" checklist in PITFALLS.md provides the acceptance criteria. Daemon behavior that must be verified: 5-consecutive-skip pause logic counts new signal skips correctly; SSE feed shows new reason labels without errors.

**Delivers:** Integration test suite for full pipeline with all signal combinations; verification that `skip_events.jsonl` payloads contain all four boolean fields; confirmation that existing daemon behavior is unaffected.

**Addresses:** All PITFALLS.md checklist items.

### Phase Ordering Rationale

- The return type refactor (Phase 1) is a prerequisite for clean signal integration and must not be deferred to Phase 4. Deferring it means touching ContentChecker and daemon twice instead of once.
- Building and testing scanners in isolation before wiring them in (Phases 2–3 before Phase 4) is the established pattern already used when `ProfanityScanner` was introduced. It keeps test failures localized and allows wordlist review before integration.
- Phases 2 and 3 have no mutual dependency and can be worked in parallel if two tracks are available.
- The incident log extension belongs with ContentChecker integration (Phase 4) as a single atomic change.
- End-to-end validation is a separate phase because it exercises cross-component behavior that unit tests in Phases 2–3 cannot cover.

### Research Flags

No phase in this milestone requires a `/gsd:research-phase` step. The architecture is grounded in direct codebase inspection (HIGH confidence) and all implementation patterns are straightforward extensions of existing code.

**Phases with standard patterns (skip research-phase):**
- **Phase 1:** Dataclass refactor is a standard Python pattern; the two call sites to update (`check()` return and `_append_skip_event()`) are confirmed by direct code inspection.
- **Phases 2 and 3:** Scanner implementation mirrors the existing `ProfanityScanner` exactly. Regex compilation behavior is stdlib-documented.
- **Phase 4:** ContentChecker injection follows the existing constructor-injection pattern. No new architectural decisions required.
- **Phase 5:** Standard pytest integration test patterns using the existing test infrastructure.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | `re` stdlib behavior verified against Python 3.12 docs; all alternatives evaluated against official PyPI pages; no new dependencies means no version risk |
| Features | MEDIUM | Table stakes and MVP scope HIGH confidence; edge case false positive rates in this specific codebase MEDIUM — must validate against real-world skip logs after initial deploy |
| Architecture | HIGH | Based on direct inspection of `content_checker.py`, `daemon.py`, `profanity_scanner.py`, `lyrics_service.py`; all component boundaries confirmed in actual code |
| Pitfalls | HIGH | Substring matching and tuple-unpack pitfalls confirmed against actual code; false positive patterns verified across multiple research sources |

**Overall confidence:** HIGH

### Gaps to Address

- **Keyword list final curation:** Research provides representative coverage and clear exclusion criteria, but the specific ~30–50 phrase list for each scanner requires editorial judgment calls at implementation time. The first two weeks of production data will surface false positives that should drive list revisions before the v1.3 toggle UI milestone.
- **`better-profanity` default word list exact contents:** Research identifies the overlap risk and the mitigation (assert disjointness), but the exact contents of `better_profanity.profanity.CENSOR_WORDLIST` should be confirmed at implementation time by inspecting the installed package directly, not from documentation.
- **Web UI dashboard handling of new reason strings:** PITFALLS.md flags that `"drug_reference"` and `"sexual_content"` reason values need to be handled in any switch/match statements in the dashboard JavaScript. This is a minor v1.2 task that should be confirmed during Phase 4 or Phase 5.

---

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection: `content_checker.py`, `daemon.py`, `profanity_scanner.py`, `lyrics_service.py`, `web_ui/main.py` — pipeline structure, return types, all call sites
- `.planning/PROJECT.md` — confirmed v1.2 scope, deferred items, architecture constraints
- [Python `re` module documentation](https://docs.python.org/3/library/re.html) — `\b` word boundary behavior, compiled alternation
- [pyahocorasick PyPI](https://pypi.org/project/pyahocorasick/) — version 2.3.0, Python 3.12 confirmed, upgrade path validated
- [better-profanity PyPI](https://pypi.org/project/better-profanity/) — version 0.7.0, `add_censor_words()` API and conflict risk confirmed

### Secondary (MEDIUM confidence)
- [An Analysis of the Prevalence and Trends in Drug-Related Lyrics (JMIR 2024)](https://formative.jmir.org/2024/1/e49567) — word-based approaches have acceptable precision; fuzzy matching improves recall
- [Covering Cracks in Content Moderation: Delexicalized Distant Supervision for Illicit Drug Jargon Detection (KDD 2025)](https://arxiv.org/html/2503.14926v1) — context-based approaches outperform bare keyword lists; confirms false positive patterns
- [Fine-Tuning LLMs for Explicit Content in Spanish Lyrics (arXiv 2026)](https://arxiv.org/html/2602.05485) — dictionary-based filtering 61% F1-score; ML 87%+; euphemism miss rate is fundamental to the approach, not fixable with bigger lists
- [A novel approach for explicit song lyrics detection (PeerJ 2023)](https://peerj.com/articles/cs-1469/) — false positive analysis in keyword approaches
- [Keyword lists and filtering guide (Sightengine 2026)](https://sightengine.com/keyword-lists-for-text-moderation-the-guide) — practical content moderation false positive tradeoffs
- [DEA Drug Slang Reference (2018)](https://www.dea.gov/sites/default/files/2018-07/DIR-022-18.pdf) — used to identify high-recall / high-false-positive terms to exclude from conservative list
- [Drug Slang in Music — Delphi Behavioral Health Group](https://delphihealthgroup.com/drug-slang-in-music/) — drug slang terminology reference

### Tertiary (LOW confidence)
- [Self-Supervised Euphemism Detection (arXiv 2021)](https://arxiv.org/pdf/2103.16808) — euphemisms escape keyword filters; semantic approaches required for full coverage — confirms the v2+ deferral decision but not actionable for v1.2

---
*Research completed: 2026-04-02*
*Ready for roadmap: yes*
