# Phase 11: ContentChecker Pipeline Integration - Research

**Researched:** 2026-04-03
**Domain:** Python async content filtering pipeline, pytest unit/integration testing
**Confidence:** HIGH

## Summary

Phase 11 wires the two scanner modules created in Phase 10 (`DrugScanner`, `SexualContentScanner`) into `ContentChecker.check()`. Currently `ContentChecker` has a three-tier pipeline: (1) explicit flag, (2) lyrics fetch, (3) profanity scan. Phase 11 adds tiers 4 and 5 — drug scan and sexual content scan — running unconditionally on every track that has lyrics, AFTER the profanity scan, and NOT short-circuiting when profanity fires first (Success Criteria 3).

The existing `ContentChecker.__init__()` already accepts `profanity_scanner` as a constructor argument — the integration pattern is simply to add `drug_scanner` and `sexual_content_scanner` as additional optional constructor arguments (mirroring the existing pattern), inject them in `daemon.py`'s `main()`, and call them inside `check()`. The `daemon.py` instantiation site already shows the wiring pattern for profanity scanner injection.

The `TrackEvalResult.reason` field needs two new values: `"drug_reference"` and `"sexual_content"`. The daemon already consumes `result.reason` for logging and the skip-event payload — no daemon changes are needed beyond those required by the new reason values (and the docstring of `reason` in `content_checker.py` should be updated).

The integration test requirement (Success Criteria 4) needs a new test file `tests/test_content_checker.py` covering all five combinations: clean, profanity-only, drug-only, sexual-only, and multiple signals simultaneously. Existing `test_daemon_events.py` uses `TrackEvalResult` directly via mocking — those tests are unaffected by Phase 11 changes.

**Primary recommendation:** Add `drug_scanner` and `sexual_content_scanner` as optional `__init__` args to `ContentChecker`, add parallel scan calls in `check()` after the profanity scan, and create `tests/test_content_checker.py` covering all five signal combinations.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DRUG-03 | Skip is triggered when a drug reference is detected and Family Safe Mode is active | ContentChecker.check() must call DrugScanner.scan() and return TrackEvalResult(action="skip", reason="drug_reference", ...) when detected=True; daemon already acts on result.action=="skip" unconditionally |
| SEXL-04 | Skip is triggered when sexual content is detected and Family Safe Mode is active | ContentChecker.check() must call SexualContentScanner.scan() and return TrackEvalResult(action="skip", reason="sexual_content", ...) when detected=True; same daemon code path as DRUG-03 |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `content_checker.py` (project) | Phase 11 target | Pipeline orchestrator | Existing orchestrator; the only file that needs modification |
| `daemon.py` (project) | Phase 11 target | Instantiation site | Already injects profanity_scanner — extend same pattern for drug/sexual scanners |
| `drug_scanner.py` (project, Phase 10) | Complete | Drug reference detection | `DrugScanner.scan()` returns `(bool, list[str])` |
| `sexual_content_scanner.py` (project, Phase 10) | Complete | Sexual content detection | `SexualContentScanner.scan()` returns `(bool, list[str])` |
| `pytest` | 9.0.2 (in `.venv`) | Test framework | Already installed; pytest-asyncio 1.3.0 already available for async tests |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `unittest.mock` (stdlib) | Python 3.12 | Mock LyricsService, scanners in tests | Already used in test_daemon_events.py; required for ContentChecker integration tests |
| `pytest_asyncio` | 1.3.0 (in `.venv`) | Async test support | `ContentChecker.check()` is async — needed for `@pytest.mark.asyncio` |

No new packages needed. No changes to `requirements.txt`.

**Run command:** `.venv/bin/pytest tests/test_content_checker.py -x`

## Architecture Patterns

### Existing ContentChecker Constructor (before Phase 11)
```python
def __init__(
    self,
    lyrics_service=None,
    profanity_scanner=None,
    min_severity: int = 2,
) -> None:
    self.lyrics_service = lyrics_service
    self.profanity_scanner = profanity_scanner
    self.min_severity = min_severity
```

### Phase 11 ContentChecker Constructor (after)
```python
def __init__(
    self,
    lyrics_service=None,
    profanity_scanner=None,
    drug_scanner=None,
    sexual_content_scanner=None,
    min_severity: int = 2,
) -> None:
    self.lyrics_service = lyrics_service
    self.profanity_scanner = profanity_scanner
    self.drug_scanner = drug_scanner
    self.sexual_content_scanner = sexual_content_scanner
    self.min_severity = min_severity
```

### Scan Ordering in check() — The Key Design Decision

**Success Criteria 3** requires: "Both scans run on every track with lyrics — detection does not short-circuit when profanity fires first."

This means the profanity scan result CANNOT immediately return — all three scans (profanity, drug, sexual) must run before a return value is computed. The pattern is:

```python
# Run all three scans unconditionally (no short-circuit)
severity, prof_matched = self.profanity_scanner.scan(lyrics_result.lyrics)
drug_detected, drug_matched = False, []
if self.drug_scanner is not None:
    drug_detected, drug_matched = self.drug_scanner.scan(lyrics_result.lyrics)
sexual_detected, sexual_matched = False, []
if self.sexual_content_scanner is not None:
    sexual_detected, sexual_matched = self.sexual_content_scanner.scan(lyrics_result.lyrics)

# Decision: any signal triggers skip
if severity >= self.min_severity:
    action, reason = "skip", "profanity"
elif drug_detected:
    action, reason = "skip", "drug_reference"
elif sexual_detected:
    action, reason = "skip", "sexual_content"
else:
    action, reason = "allow", "clean"
```

**Reason priority:** profanity > drug > sexual (when multiple signals fire simultaneously, the first wins for the `reason` field — but ALL scans still ran). This is consistent with the existing logger output pattern where a single reason is logged.

### Logging Pattern — Extend Existing [SCAN] Log

The existing `[SCAN]` log line in `check()` already logs `severity`, `matched`, `action`. Extend it to also include drug/sexual matched terms. Matched terms from drug/sexual scanners go to Python logger only per REQUIREMENTS.md LOG-02 (confirmed out of scope for Phase 11 — LOG-01/LOG-02 are Phase 12).

### daemon.py Instantiation Site

Current `main()` in `daemon.py`:
```python
# Source: daemon.py lines 460-466 (read directly)
lyrics_service = LyricsService(db_path=LYRICS_DB_PATH)
profanity_scanner = ProfanityScanner(min_severity=PROFANITY_MIN_SEVERITY)
content_checker = ContentChecker(
    lyrics_service=lyrics_service,
    profanity_scanner=profanity_scanner,
    min_severity=PROFANITY_MIN_SEVERITY,
)
```

Phase 11 extends this to:
```python
from drug_scanner import DrugScanner
from sexual_content_scanner import SexualContentScanner

lyrics_service = LyricsService(db_path=LYRICS_DB_PATH)
profanity_scanner = ProfanityScanner(min_severity=PROFANITY_MIN_SEVERITY)
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

`DrugScanner()` and `SexualContentScanner()` have no required constructor args — instantiation is trivial.

### TrackEvalResult.reason — New Valid Values

The `reason` field docstring in `content_checker.py` currently documents:
```
'explicit' | 'profanity' | 'instrumental' | 'clean' | 'lyrics_unavailable' | 'no_lyrics_service'
```

Phase 11 adds:
```
'drug_reference' | 'sexual_content'
```

No structural change to `TrackEvalResult` (still `action`, `reason`, `severity`). Drug and sexual signals have severity=0 because the scanners return `bool`, not `int` — there are no severity tiers for these signals (REQUIREMENTS.md out-of-scope: "Severity tiers for drug/sexual signals — No actionable effect for ages 3 and 7 — any detection warrants a skip; defer to v2+").

**Severity for drug/sexual skips:** Use `severity=3` to indicate the track was skipped (maximum severity, same as explicit). This is consistent: the track gets skipped regardless, and severity=3 conveys "this is a skip-worthy finding" to the dashboard badge logic. Alternatively, severity=0 is also defensible (no severity tier exists). **Recommended: severity=0** — the scanners are boolean-only and severity is not defined for these signals; using 0 is more honest than claiming severity=3 which implies a tier system that doesn't exist.

### Test File Structure — tests/test_content_checker.py

**What it covers (Success Criteria 4):**
All combinations: clean, profanity-only, drug-only, sexual-only, and multiple signals simultaneously.

```python
# Source: pattern from tests/test_daemon_events.py (AsyncMock usage) + content_checker.py
"""Tests for ContentChecker pipeline integration — DRUG-03, SEXL-04."""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from content_checker import ContentChecker, TrackEvalResult


def _make_track(track_id="t1", name="Test", artist="Artist", explicit=False):
    return {
        "id": track_id, "name": name,
        "artists": [{"name": artist}],
        "explicit": explicit,
    }


def _make_lyrics_result(lyrics=None, instrumental=False):
    result = MagicMock()
    result.lyrics = lyrics
    result.instrumental = instrumental
    return result


@pytest.fixture
def checker_with_scanners():
    """ContentChecker with all three scanners wired in."""
    lyrics_service = MagicMock()
    profanity_scanner = MagicMock()
    profanity_scanner.scan.return_value = (0, [])   # clean by default
    drug_scanner = MagicMock()
    drug_scanner.scan.return_value = (False, [])    # clean by default
    sexual_scanner = MagicMock()
    sexual_scanner.scan.return_value = (False, [])  # clean by default
    checker = ContentChecker(
        lyrics_service=lyrics_service,
        profanity_scanner=profanity_scanner,
        drug_scanner=drug_scanner,
        sexual_content_scanner=sexual_scanner,
        min_severity=2,
    )
    return checker, lyrics_service, profanity_scanner, drug_scanner, sexual_scanner


@pytest.mark.asyncio
async def test_clean_track_allowed(checker_with_scanners):
    checker, lyrics_svc, prof, drug, sexual = checker_with_scanners
    lyrics_svc.get_lyrics = AsyncMock(return_value=_make_lyrics_result("la la la"))
    result = await checker.check(_make_track())
    assert result.action == "allow"
    assert result.reason == "clean"


@pytest.mark.asyncio
async def test_drug_reference_triggers_skip(checker_with_scanners):
    checker, lyrics_svc, prof, drug, sexual = checker_with_scanners
    lyrics_svc.get_lyrics = AsyncMock(return_value=_make_lyrics_result("cocaine in the lyrics"))
    drug.scan.return_value = (True, ["cocaine"])
    result = await checker.check(_make_track())
    assert result.action == "skip"
    assert result.reason == "drug_reference"


@pytest.mark.asyncio
async def test_sexual_content_triggers_skip(checker_with_scanners):
    checker, lyrics_svc, prof, drug, sexual = checker_with_scanners
    lyrics_svc.get_lyrics = AsyncMock(return_value=_make_lyrics_result("penis in the lyrics"))
    sexual.scan.return_value = (True, ["penis"])
    result = await checker.check(_make_track())
    assert result.action == "skip"
    assert result.reason == "sexual_content"


@pytest.mark.asyncio
async def test_profanity_only_triggers_skip(checker_with_scanners):
    checker, lyrics_svc, prof, drug, sexual = checker_with_scanners
    lyrics_svc.get_lyrics = AsyncMock(return_value=_make_lyrics_result("fuck this song"))
    prof.scan.return_value = (3, ["fuck"])
    result = await checker.check(_make_track())
    assert result.action == "skip"
    assert result.reason == "profanity"


@pytest.mark.asyncio
async def test_all_signals_fire_all_scans_run(checker_with_scanners):
    """All three scanners run even when profanity fires — no short-circuit (Success Criteria 3)."""
    checker, lyrics_svc, prof, drug, sexual = checker_with_scanners
    lyrics_svc.get_lyrics = AsyncMock(return_value=_make_lyrics_result("fuck cocaine penis"))
    prof.scan.return_value = (3, ["fuck"])
    drug.scan.return_value = (True, ["cocaine"])
    sexual.scan.return_value = (True, ["penis"])
    result = await checker.check(_make_track())
    assert result.action == "skip"
    # All three scan() methods must have been called
    prof.scan.assert_called_once()
    drug.scan.assert_called_once()
    sexual.scan.assert_called_once()
```

### Anti-Patterns to Avoid

- **Short-circuiting after profanity detection:** Returning immediately from `check()` when profanity fires means drug/sexual scanners never run. Success Criteria 3 explicitly forbids this. Run all three scans, then decide.
- **Using `if self.drug_scanner and drug_detected` as a single condition:** Check `self.drug_scanner is not None` first (guard for when scanner isn't injected), then run it unconditionally (don't gate the scan on prior signals).
- **Assigning severity=3 to drug/sexual skips without justification:** These scanners return bool, not severity int. Use severity=0 (or at minimum, be consistent — pick one value and document it).
- **Forgetting to update TrackEvalResult.reason docstring:** The `reason` type annotation is `str` — new valid values should be added to the docstring comment.
- **Forgetting to add imports in daemon.py:** `DrugScanner` and `SexualContentScanner` must be imported in `daemon.py` at the top.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Multiple scan results aggregation | Custom signal aggregator class | Simple `if/elif` decision tree | Three boolean/severity inputs with a clear priority — no combinator needed |
| Scanner injection in tests | Manually constructing real scanners | `MagicMock()` with `.scan.return_value` | Isolates ContentChecker logic from scanner regex behavior; faster tests |
| Async test runner | Custom event loop management | `@pytest.mark.asyncio` (already installed) | pytest-asyncio 1.3.0 already in .venv; pattern already used in test_daemon_events.py |

**Key insight:** The existing profanity scanner injection pattern (`self.profanity_scanner`) is the complete template — Phase 11 repeats it twice more.

## Common Pitfalls

### Pitfall 1: Short-Circuit on Profanity (violates Success Criteria 3)
**What goes wrong:** Adding `if severity >= self.min_severity: return TrackEvalResult(...)` before the drug/sexual scan calls — drug and sexual scans are never reached when profanity fires.
**Why it happens:** The original profanity-scan code path returned immediately after deciding to skip. Copy-paste from the original without restructuring to run-all-then-decide.
**How to avoid:** Restructure Tier 3 to collect ALL scan results first, THEN make the single return decision. The test `test_all_signals_fire_all_scans_run` enforces this by asserting all three `.scan.assert_called_once()`.
**Warning signs:** `test_all_signals_fire_all_scans_run` fails because `drug.scan.assert_called_once()` raises `AssertionError: Expected 'scan' to have been called once. Called 0 times.`

### Pitfall 2: reason field collision with daemon skip event logging
**What goes wrong:** `daemon.py` writes `result.reason` directly to the skip event in `events.jsonl`. New reason values `"drug_reference"` and `"sexual_content"` will appear there. This is expected and correct for Phase 11 — but LOG-01 (Phase 12) will add explicit boolean fields for each signal. Do not add those fields in Phase 11.
**Why it happens:** Phase 12 extends the skip event schema — Phase 11 should not pre-empt it.
**How to avoid:** Phase 11 writes only `reason="drug_reference"` or `reason="sexual_content"` into the reason field. No new fields in the event payload.

### Pitfall 3: ContentChecker constructor backward compatibility
**What goes wrong:** Adding positional args to `__init__` breaks the existing `daemon.py` instantiation and any tests that construct `ContentChecker(lyrics_service=..., profanity_scanner=..., ...)` with keyword args.
**Why it happens:** Adding new args without keyword-only defaults.
**How to avoid:** Add new scanner args with `= None` defaults, always using keyword argument style. The existing pattern already uses `profanity_scanner=None` — just extend it.

### Pitfall 4: Forgetting FSM guard in daemon
**What goes wrong:** Assuming Phase 11 changes daemon.py's skip logic. It doesn't — `daemon.py` already gates the entire evaluation on `state.get("family_safe_mode", False)`. ContentChecker.check() is only called when FSM is active. No new FSM guard needed.
**Why it happens:** Re-reading the success criteria "when Family Safe Mode is active" and thinking the FSM check belongs in ContentChecker.
**How to avoid:** FSM check stays in daemon.py. ContentChecker.check() is always unconditionally honest — it reports what it finds; daemon decides whether to act.

## Code Examples

### Minimal check() Restructure (Tier 3 — run all, then decide)
```python
# Source: content_checker.py (read directly) — restructured for non-short-circuit
# Tier 3: Run all scanners unconditionally
severity, prof_matched = self.profanity_scanner.scan(lyrics_result.lyrics)

drug_detected, drug_matched = False, []
if self.drug_scanner is not None:
    drug_detected, drug_matched = self.drug_scanner.scan(lyrics_result.lyrics)

sexual_detected, sexual_matched = False, []
if self.sexual_content_scanner is not None:
    sexual_detected, sexual_matched = self.sexual_content_scanner.scan(lyrics_result.lyrics)

# Decision: priority order profanity > drug > sexual
if severity >= self.min_severity:
    action, reason = "skip", "profanity"
elif drug_detected:
    action, reason = "skip", "drug_reference"
elif sexual_detected:
    action, reason = "skip", "sexual_content"
else:
    action, reason = "allow", "clean"

log.info(
    "[SCAN] track=%r artist=%r severity=%d prof_matched=%s "
    "drug_matched=%s sexual_matched=%s action=%s",
    track_name, artist_name, severity,
    prof_matched, drug_matched, sexual_matched, action,
)
return TrackEvalResult(action=action, reason=reason, severity=severity)
```

### daemon.py Import Extension
```python
# Add after existing scanner imports in daemon.py
from drug_scanner import DrugScanner
from sexual_content_scanner import SexualContentScanner
```

### daemon.py main() Instantiation Extension
```python
# Source: daemon.py lines 460-466 (read directly) — extend this block
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

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 (`.venv/bin/pytest`) |
| Config file | none — conftest.py adds project root to sys.path |
| Quick run command | `.venv/bin/pytest tests/test_content_checker.py -x` |
| Full suite command | `.venv/bin/pytest tests/ -x` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DRUG-03 | Drug detection triggers skip (reason="drug_reference") | integration | `.venv/bin/pytest tests/test_content_checker.py::test_drug_reference_triggers_skip -x` | Wave 0 |
| SEXL-04 | Sexual content detection triggers skip (reason="sexual_content") | integration | `.venv/bin/pytest tests/test_content_checker.py::test_sexual_content_triggers_skip -x` | Wave 0 |
| Success Criteria 3 | All three scanners run when profanity fires (no short-circuit) | integration | `.venv/bin/pytest tests/test_content_checker.py::test_all_signals_fire_all_scans_run -x` | Wave 0 |
| Success Criteria 4 | All five combinations tested (clean, profanity-only, drug-only, sexual-only, multi) | integration | `.venv/bin/pytest tests/test_content_checker.py -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `.venv/bin/pytest tests/test_content_checker.py -x`
- **Per wave merge:** `.venv/bin/pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Known Pre-Existing Failure
`tests/test_skip_client.py::test_soco_pause_uses_cached_ip` currently fails (1 failure in full suite run). This is a pre-existing failure unrelated to Phase 11. The phase gate should be: Phase 11 tests all pass, and no NEW failures introduced in the full suite.

### Wave 0 Gaps
- [ ] `tests/test_content_checker.py` — covers DRUG-03, SEXL-04, Success Criteria 3 and 4

*(No framework install needed — pytest + pytest-asyncio already installed in .venv)*

## Environment Availability

Step 2.6: SKIPPED — phase is purely Python code modifications and test additions. No external dependencies beyond the project's own installed `.venv`. Both scanners already exist as completed Phase 10 modules. No databases, CLIs, Docker, or network services involved.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| ContentChecker: 3-tier pipeline (explicit → lyrics → profanity) | 5-tier pipeline after Phase 11 (+ drug → sexual) | Phase 11 | Two new skip reasons; non-short-circuit design required |
| TrackEvalResult.reason: 6 values | 8 values after Phase 11 (+ drug_reference, sexual_content) | Phase 11 | daemon.py skip event payload gets new reason values automatically |

**Deprecated/outdated:**
- ContentChecker docstring comment "three-tier filter pipeline" — update to "five-tier" after Phase 11.

## Open Questions

1. **severity value for drug/sexual skips**
   - What we know: DrugScanner and SexualContentScanner return `(bool, list[str])` — no severity tier exists
   - What's unclear: Should TrackEvalResult.severity be 0 (no tier defined) or 3 (skip = severe)?
   - Recommendation: Use `severity=0`. The dashboard skip feed displays reason-based badges (Phase 13 UI-01), not severity-based ones for these signals. Using 0 is honest and consistent with scanner return type. Phase 12 LOG-01 adds boolean fields per signal — severity is irrelevant for drug/sexual at that point anyway.

2. **When both drug AND sexual signals fire**
   - What we know: Priority order profanity > drug > sexual determines `reason`; all scanners still ran
   - What's unclear: Is this the right priority order?
   - Recommendation: drug > sexual is arbitrary but consistent. The priority only affects the `reason` string in the skip event payload. Phase 12 LOG-01 will add explicit boolean fields for all four signals, making the priority moot for observability. Use drug > sexual as a reasonable default.

## Sources

### Primary (HIGH confidence)
- `content_checker.py` (read directly) — exact current implementation; Phase 11 modifies this file
- `daemon.py` (read directly) — instantiation site, scanner injection pattern, skip event payload
- `drug_scanner.py` (read directly) — `DrugScanner.scan()` signature confirmed
- `sexual_content_scanner.py` (read directly) — `SexualContentScanner.scan()` signature confirmed
- `profanity_scanner.py` (read directly) — `ProfanityScanner.scan()` signature; `SEVERITY_MAP` reference
- `tests/test_daemon_events.py` (read directly) — `AsyncMock`, `MagicMock`, `pytest.mark.asyncio` usage patterns
- `tests/conftest.py` (read directly) — sys.path setup; confirms `tests/test_content_checker.py` will work without any extra setup
- `.planning/REQUIREMENTS.md` (read directly) — DRUG-03, SEXL-04, LOG-01/LOG-02 scope boundaries
- `.planning/phases/10-scanner-modules/10-CONTEXT.md` (read directly) — Phase 10 decisions and integration point documentation
- `.venv/bin/pytest` (found at `/home/cgallarno/Development/spotify-sentiment/.venv/bin/pytest`) — verified test runner

### Secondary (MEDIUM confidence)
- Full test suite run (`.venv/bin/pytest tests/ -x`) — confirmed 24+9xpassed passing (1 pre-existing failure in test_skip_client.py unrelated to Phase 11)

### Tertiary (LOW confidence)
- None — all findings derived from project source code read directly.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all modules exist and are read directly
- Architecture: HIGH — integration pattern is a direct extension of the existing profanity scanner injection; no ambiguity
- Test design: HIGH — test_daemon_events.py provides a complete, working template for async ContentChecker tests
- Scan ordering/priority: HIGH — non-short-circuit design is clearly required by Success Criteria 3; priority order is LOW (arbitrary choice with no spec constraint)
- severity value for new skip reasons: MEDIUM — reasonable argument for 0; no spec constraint

**Research date:** 2026-04-03
**Valid until:** Stable — all sources are project files, no external dependencies
