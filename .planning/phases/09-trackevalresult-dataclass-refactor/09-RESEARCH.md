# Phase 9: TrackEvalResult Dataclass Refactor - Research

**Researched:** 2026-04-03
**Domain:** Python dataclasses, ContentChecker return type refactor, test mock migration
**Confidence:** HIGH

## Summary

Phase 9 is a pure internal refactor — no behavior change, no new dependencies. The goal is to replace the positional `tuple[str, str, int]` returned by `ContentChecker.check()` with a named `TrackEvalResult` dataclass so downstream callers access fields by name (`result.action`, `result.reason`, `result.severity`) instead of index position. This is a prerequisite for Phase 10's drug/sexual scanner additions, which will need to add new boolean fields to the result without breaking existing callers.

The refactor touches three locations: the `content_checker.py` definition (one `check()` method with four return sites), the single tuple-unpack call site in `daemon.py` (line 248), and all 10 test mock return values in `tests/test_daemon_events.py` that currently return bare 3-tuples. The STATE.md decision log is explicit: this must be atomic — all 10 mocks and all return sites updated in one commit; grep for zero remaining bare-tuple unpacks before declaring done.

`@dataclass` from the stdlib `dataclasses` module (Python 3.7+, available in this project's Python 3.12 venv) is the correct tool. No third-party library is needed. The dataclass should use `frozen=True` (immutable result, signals value semantics) and define the three existing fields: `action: str`, `reason: str`, `severity: int`. The test suite currently has 9 tests that are xpassed (were xfail, now pass) and 2 unrelated pre-existing failures in `test_skip_client.py` — both of these must remain unchanged after this refactor.

**Primary recommendation:** Define `TrackEvalResult` as a `frozen=True` dataclass in `content_checker.py`, update all four return sites in `check()`, update the single unpack in `daemon.py` to attribute access, update all 10 test mock return values to `TrackEvalResult(...)`.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PIPE-01 | `ContentChecker.check()` returns a named `TrackEvalResult` dataclass instead of a positional 3-tuple | All four return sites in `content_checker.py` identified; single daemon.py call site identified; all 10 test mock sites identified |
</phase_requirements>

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `dataclasses` (stdlib) | Python 3.12 (stdlib) | Named, typed result container | Zero dependencies, built-in, correct for value-object pattern |
| `pytest` | installed in .venv | Test runner | Already in use; no change needed |
| `pytest-asyncio` | installed in .venv | Async test support | Already in use; no change needed |

### No New Dependencies

This phase requires zero new packages. `dataclasses` is stdlib since Python 3.7. The project already runs Python 3.12.

**Installation:**
```bash
# No installation required — dataclasses is stdlib
```

## Architecture Patterns

### Recommended Project Structure

No structural changes. `TrackEvalResult` lives in `content_checker.py` alongside `ContentChecker` — same file, imported by `daemon.py` which already imports `ContentChecker`.

### Pattern 1: Frozen Dataclass as Value Object

**What:** A `@dataclass(frozen=True)` class with three typed fields replacing the bare 3-tuple. Frozen means instances are immutable after creation — correct semantics for an evaluation result.

**When to use:** Any time a function returns multiple named values that callers need to reference by name rather than position. Also extensible: future phases add fields (e.g., `drug_reference: bool = False`) without breaking call sites that use attribute access.

**Example:**
```python
# Source: Python stdlib dataclasses documentation
from dataclasses import dataclass

@dataclass(frozen=True)
class TrackEvalResult:
    action: str    # 'skip' | 'allow'
    reason: str    # 'explicit' | 'profanity' | 'instrumental' | 'clean' | 'lyrics_unavailable' | 'no_lyrics_service'
    severity: int  # 0-3

# content_checker.py return site (was: return ("skip", "explicit", 3))
return TrackEvalResult(action="skip", reason="explicit", severity=3)

# daemon.py call site (was: action, reason, severity = await content_checker.check(track))
result = await content_checker.check(track)
# Then use result.action, result.reason, result.severity throughout

# Test mock (was: AsyncMock(return_value=("allow", "clean", 0)))
from content_checker import TrackEvalResult
checker.check = AsyncMock(return_value=TrackEvalResult(action="allow", reason="clean", severity=0))
```

### Pattern 2: Keyword Arguments at Return Sites

**What:** Always use keyword arguments when constructing `TrackEvalResult` at return sites — never positional.

**Why:** Makes the code self-documenting and prevents positional confusion. Also future-proofs: new fields with defaults can be added without changing existing return sites.

```python
# CORRECT
return TrackEvalResult(action="allow", reason="clean", severity=0)

# AVOID — positionally fragile
return TrackEvalResult("allow", "clean", 0)
```

### Anti-Patterns to Avoid

- **Keeping any bare-tuple unpacking:** `action, reason, severity = result` still works on a dataclass (it's iterable by default unless you disable it), but defeats the purpose. All unpacks must become attribute access.
- **Defining `TrackEvalResult` in a separate file:** The class is tightly coupled to `ContentChecker`. Keeping them in `content_checker.py` avoids a new import path.
- **Using `NamedTuple` instead of `dataclass`:** `NamedTuple` is iterable by position, which preserves the fragility we're removing. Dataclass with `frozen=True` explicitly requires attribute access.
- **Forgetting the `_eval_state_from_result` helper:** `daemon.py` line 146 calls `_eval_state_from_result(action, reason)` — after the refactor this becomes `_eval_state_from_result(result.action, result.reason)`. It appears in multiple places after the single unpack is removed.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Named result container | Custom class with `__init__` | `@dataclass(frozen=True)` | Auto-generates `__init__`, `__repr__`, `__eq__`; stdlib; no boilerplate |
| Immutability | Manual `__setattr__` raise | `frozen=True` param | Already built-in |

**Key insight:** `dataclasses` handles all the boilerplate. The entire definition is 5 lines.

## Common Pitfalls

### Pitfall 1: Partial Update — Daemon Reads Fields Wrong

**What goes wrong:** Developer updates `content_checker.py` return sites to return `TrackEvalResult` but leaves `daemon.py` line 248 as `action, reason, severity = await content_checker.check(track)`. This still works because Python dataclasses are iterable by default — silently stays broken with no error.

**Why it happens:** Tuple unpacking works on any iterable, including dataclasses. No TypeError is raised.

**How to avoid:** Search explicitly for all tuple-unpack patterns after the refactor: `grep -n "action, reason, severity" daemon.py` must return zero results.

**Warning signs:** The line `action, reason, severity = await content_checker.check(track)` still exists.

### Pitfall 2: Test Mocks Return Bare Tuples

**What goes wrong:** Test mocks are updated incompletely. One or more `AsyncMock(return_value=("allow", "clean", 0))` remain as bare tuples. Tests pass because tuple access works, but the mock no longer exercises the real return type.

**Why it happens:** There are 10 mock sites across `test_daemon_events.py` — easy to miss one. Two are inside inline `_check_spy` functions (lines 102 and 278) that return tuples directly from inside the function body, not via `return_value=`.

**How to avoid:** After the update, run: `grep -n '"allow"\|"skip"\|"explicit"\|"clean"\|"profanity"\|"instrumental"\|"lyrics_unavailable"' tests/test_daemon_events.py` — any remaining bare tuple returns in that file are misses. The STATE.md decision confirms: grep for zero bare-tuple unpacks before declaring done.

**Warning signs:** Any `return_value=("allow"` or `return ("allow"` in test files.

### Pitfall 3: `_eval_state_from_result` Call Sites Missed

**What goes wrong:** `daemon.py` calls `_eval_state_from_result(action, reason)` at multiple locations (lines 259, 268 via the `action`/`reason` local variables from the tuple unpack). After removing the unpack, these local variables no longer exist — the code will `NameError` at runtime.

**Why it happens:** The single unpack at line 248 creates `action`, `reason`, and `severity` locals used across many subsequent lines. Removing the unpack without updating all downstream uses causes `NameError`.

**How to avoid:** After converting line 248 to `result = await content_checker.check(track)`, systematically replace every reference to `action`, `reason`, and `severity` in the `if state.get("family_safe_mode", False)` block with `result.action`, `result.reason`, `result.severity`.

**Warning signs:** Any bare reference to `action`, `reason`, or `severity` (without `result.` prefix) remaining in `daemon.py` after the refactor.

### Pitfall 4: `_check_spy` Functions Return Bare Tuples

**What goes wrong:** Two tests in `test_daemon_events.py` use inline spy functions (not `AsyncMock`) that return bare tuples: line 102 (`return ("allow", "clean", 0)`) and line 278 (`return ("allow", "clean", 0)`). These are function bodies, not `return_value=` assignments — easy to overlook.

**Why it happens:** They look like regular function returns, not mock configuration.

**How to avoid:** The update must cover `return` statements inside `_check_spy` functions in addition to `AsyncMock(return_value=...)` patterns.

## Code Examples

### Complete `TrackEvalResult` Definition

```python
# Source: Python 3.12 stdlib dataclasses
from dataclasses import dataclass

@dataclass(frozen=True)
class TrackEvalResult:
    """Named result from ContentChecker.check().

    Replaces the positional (action, reason, severity) 3-tuple (PIPE-01).
    frozen=True enforces immutability and value-object semantics.
    """
    action: str    # 'skip' | 'allow'
    reason: str    # 'explicit' | 'profanity' | 'instrumental' | 'clean'
                   # | 'lyrics_unavailable' | 'no_lyrics_service'
    severity: int  # 0-3 (0=none, 1=mild, 2=moderate, 3=severe)
```

### All Four Return Sites in `content_checker.py`

```python
# Line 64 — explicit flag
return TrackEvalResult(action="skip", reason="explicit", severity=3)

# Line 82 — instrumental
return TrackEvalResult(action="allow", reason="instrumental", severity=0)

# Line 91 — lyrics unavailable
return TrackEvalResult(action="allow", reason="lyrics_unavailable", severity=0)

# Line 110 — profanity scan result
return TrackEvalResult(action=action, reason=reason, severity=severity)

# Line 119 — no lyrics service
return TrackEvalResult(action="allow", reason="no_lyrics_service", severity=0)
```

Note: There are actually five return statements (counted from source: lines 64, 82, 91, 110, 119), not four. Line 110 uses local variables from the profanity scan branch.

### Daemon Call Site After Refactor

```python
# daemon.py line 248 — was: action, reason, severity = await content_checker.check(track)
result = await content_checker.check(track)

# All downstream references become:
result.action    # was: action
result.reason    # was: reason
result.severity  # was: severity

# _eval_state_from_result calls — was: _eval_state_from_result(action, reason)
_eval_state_from_result(result.action, result.reason)
```

### Test Mock After Refactor

```python
from content_checker import TrackEvalResult

# AsyncMock sites — was: AsyncMock(return_value=("allow", "clean", 0))
checker.check = AsyncMock(return_value=TrackEvalResult(action="allow", reason="clean", severity=0))
checker.check = AsyncMock(return_value=TrackEvalResult(action="skip", reason="explicit", severity=3))
checker.check = AsyncMock(return_value=TrackEvalResult(action="allow", reason="mild_language", severity=1))

# Spy function body — was: return ("allow", "clean", 0)
return TrackEvalResult(action="allow", reason="clean", severity=0)
```

## Exact Scope Inventory

All sites that must change (source of truth from direct code inspection):

### `content_checker.py` — return sites

| Line | Current | Change To |
|------|---------|-----------|
| 39 | `async def check(...) -> tuple[str, str, int]:` | `async def check(...) -> "TrackEvalResult":` |
| 64 | `return ("skip", "explicit", 3)` | `return TrackEvalResult(action="skip", reason="explicit", severity=3)` |
| 82 | `return ("allow", "instrumental", 0)` | `return TrackEvalResult(action="allow", reason="instrumental", severity=0)` |
| 91 | `return ("allow", "lyrics_unavailable", 0)` | `return TrackEvalResult(action="allow", reason="lyrics_unavailable", severity=0)` |
| 110 | `return (action, reason, severity)` | `return TrackEvalResult(action=action, reason=reason, severity=severity)` |
| 119 | `return ("allow", "no_lyrics_service", 0)` | `return TrackEvalResult(action="allow", reason="no_lyrics_service", severity=0)` |

### `daemon.py` — call site and downstream references

| Line | Current | Change To |
|------|---------|-----------|
| 248 | `action, reason, severity = await content_checker.check(track)` | `result = await content_checker.check(track)` |
| 253 | `if action == "allow":` | `if result.action == "allow":` |
| 257 | `_eval_state_from_result(action, reason)` | `_eval_state_from_result(result.action, result.reason)` |
| 260 | `"severity": severity,` | `"severity": result.severity,` |
| 268 | `_eval_state_from_result(action, reason)` | `_eval_state_from_result(result.action, result.reason)` |
| 269 | `"severity": severity,` | `"severity": result.severity,` |
| 273 | `if action == "skip":` | `if result.action == "skip":` |
| 330 | `"reason": reason,` | `"reason": result.reason,` |
| 336 | `"reason": reason,` | `"reason": result.reason,` |
| 352 | `"severity": severity,` | `"severity": result.severity,` |
| 361 | `"severity": severity,` | `"severity": result.severity,` |

### `tests/test_daemon_events.py` — mock sites (10 total)

| Line | Current | Change To |
|------|---------|-----------|
| 102 | `return ("allow", "clean", 0)` (spy body) | `return TrackEvalResult(action="allow", reason="clean", severity=0)` |
| 121 | `AsyncMock(return_value=("allow", "clean", 0))` | `AsyncMock(return_value=TrackEvalResult(...))` |
| 149 | `AsyncMock(return_value=("allow", "clean", 0))` | `AsyncMock(return_value=TrackEvalResult(...))` |
| 169 | `AsyncMock(return_value=("skip", "explicit", 3))` | `AsyncMock(return_value=TrackEvalResult(...))` |
| 211 | `AsyncMock(return_value=("allow", "clean", 0))` | `AsyncMock(return_value=TrackEvalResult(...))` |
| 231 | `AsyncMock(return_value=("skip", "explicit", 3))` | `AsyncMock(return_value=TrackEvalResult(...))` |
| 278 | `return ("allow", "clean", 0)` (spy body) | `return TrackEvalResult(action="allow", reason="clean", severity=0)` |
| 300 | `AsyncMock(return_value=("allow", "clean", 0))` | `AsyncMock(return_value=TrackEvalResult(...))` |
| 320 | `AsyncMock(return_value=("skip", "explicit", 3))` | `AsyncMock(return_value=TrackEvalResult(...))` |
| 361 | `AsyncMock(return_value=("allow", "mild_language", 1))` | `AsyncMock(return_value=TrackEvalResult(...))` |

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Positional 3-tuple `(action, reason, severity)` | Named `TrackEvalResult` dataclass | Phase 9 (now) | Call sites use attribute names; new fields added in Phase 10 without breaking callers |

**Why this matters for Phase 10:** When `DrugScanner` and `SexualContentScanner` are added, their boolean results must be included in the evaluation result. Adding `drug_reference: bool = False` and `sexual_content: bool = False` to `TrackEvalResult` is trivial once it's a dataclass — existing callers that don't reference the new fields need no changes.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (installed in .venv) |
| Config file | none (no pytest.ini; uses default discovery) |
| Quick run command | `.venv/bin/python -m pytest tests/test_daemon_events.py -q` |
| Full suite command | `.venv/bin/python -m pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PIPE-01 | `check()` returns `TrackEvalResult` instance, not bare tuple | unit | `.venv/bin/python -m pytest tests/test_daemon_events.py -q` | Yes (all 10 mocks in test_daemon_events.py) |
| PIPE-01 | All daemon.py call sites use `result.action`/`result.reason`/`result.severity` | smoke (grep) | `grep -c "action, reason, severity" daemon.py` must return 0 | Verified by grep at commit |
| PIPE-01 | Zero bare tuple returns remain in test fixtures | smoke (grep) | `grep -c 'return_value=("allow\|return_value=("skip' tests/test_daemon_events.py` must return 0 | Verified by grep at commit |
| PIPE-01 | Test suite passes green with identical behavior | regression | `.venv/bin/python -m pytest tests/ -q` | Yes |

### Baseline Test State (Pre-Refactor)

- 2 pre-existing FAILED tests in `test_skip_client.py` (unrelated to this phase — SoCo pause tests)
- 9 xpassed tests in `test_daemon_events.py` (were xfail-marked, implementation already present)
- 21 passed tests

Post-refactor: same counts must hold. The 2 pre-existing failures must not be introduced as new failures. The 9 xpassed tests must remain passing.

### Sampling Rate

- **Per task commit:** `.venv/bin/python -m pytest tests/test_daemon_events.py -q`
- **Per wave merge:** `.venv/bin/python -m pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd:verify-work` — 2 pre-existing failures acceptable, no new failures

### Wave 0 Gaps

None — existing test infrastructure covers all phase requirements. The 10 mock sites in `test_daemon_events.py` serve as the test coverage for PIPE-01 once updated to `TrackEvalResult(...)`.

## Environment Availability

Step 2.6: SKIPPED — this phase is purely code/config changes (dataclass definition + call site updates). No external tools, services, runtimes, databases, or CLIs beyond the project's own Python venv.

The project venv at `.venv/` uses Python 3.12. `dataclasses` is stdlib. No installation step required.

## Open Questions

None. All call sites, return sites, and mock sites have been identified by direct code inspection with HIGH confidence.

## Sources

### Primary (HIGH confidence)

- Direct code inspection of `content_checker.py` — all 5 return sites identified
- Direct code inspection of `daemon.py` — single unpack at line 248, all downstream `action`/`reason`/`severity` references mapped
- Direct code inspection of `tests/test_daemon_events.py` — all 10 mock sites identified (8 `AsyncMock(return_value=(...))` + 2 inline `_check_spy` function returns)
- Python 3.12 stdlib `dataclasses` module — verified available, `frozen=True` confirmed supported
- `.venv/bin/python -m pytest tests/ -q` — baseline test run: 21 passed, 9 xpassed, 2 failed (pre-existing), 27 warnings

### Secondary (MEDIUM confidence)

- STATE.md decision log: "Phase 9: TrackEvalResult refactor must be atomic — all 10 test mocks and all return sites updated in one commit; grep for zero remaining bare-tuple unpacks before declaring done"

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — stdlib dataclasses, no new deps
- Architecture: HIGH — all sites inventoried from direct source inspection
- Pitfalls: HIGH — derived from actual code structure; tuple-unpack-still-works pitfall is the critical one
- Test coverage: HIGH — all 10 mock sites identified with line numbers

**Research date:** 2026-04-03
**Valid until:** N/A — this is a code-inspection-based research document; the findings are stable until the source files change
