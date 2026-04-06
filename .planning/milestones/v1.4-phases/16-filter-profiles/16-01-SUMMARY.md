---
phase: 16-filter-profiles
plan: "01"
subsystem: content-filtering
tags: [explicit_skip, profile_map, content_checker, daemon, tdd, prof-03]
dependency_graph:
  requires: []
  provides: [explicit_skip-param, PROFILE_MAP, _build_content_checker, prev_profile-tracking]
  affects: [content_checker.py, daemon.py, tests/test_content_checker.py]
tech_stack:
  added: []
  patterns: [profile-aware ContentChecker reconstruction, scanner passthrough pattern]
key_files:
  created: []
  modified:
    - tests/test_content_checker.py
    - content_checker.py
    - daemon.py
decisions:
  - explicit_skip defaults True so all existing Tier 1 behavior is preserved by default (no regression)
  - PROFILE_MAP maps profile keys to ContentChecker kwargs; scanner objects are long-lived, only wrapper is rebuilt
  - poll_loop receives scanner instances as params so _build_content_checker can reconstruct on profile change
  - _build_content_checker falls back to kids_present for unknown profile keys (safest default)
metrics:
  duration: "2m17s"
  completed: "2026-04-05"
  tasks_completed: 3
  files_modified: 3
---

# Phase 16 Plan 01: Add explicit_skip to ContentChecker + PROFILE_MAP + daemon wiring Summary

**One-liner:** Added `explicit_skip: bool = True` to ContentChecker and wired profile-aware ContentChecker reconstruction into daemon.py using a PROFILE_MAP constant and `_build_content_checker()` helper.

## Tasks Completed

| # | Name | Commit | Files |
|---|------|--------|-------|
| 1 | Add explicit_skip tests (TDD RED) | e3d7730 | tests/test_content_checker.py |
| 2 | Add explicit_skip to ContentChecker (TDD GREEN) | b4c3554 | content_checker.py |
| 3 | PROFILE_MAP + _build_content_checker + poll_loop wiring | 6710bb6 | daemon.py |

## What Was Built

### ContentChecker Changes (`content_checker.py`)

- Added `explicit_skip: bool = True` parameter to `ContentChecker.__init__`
- Stored as `self.explicit_skip` instance attribute
- Tier 1 check now reads `if self.explicit_skip and track.get("explicit", False):`
- When `explicit_skip=False`, Tier 1 is bypassed entirely — track falls through to Tier 2+ or `no_lyrics_service` allow

### Tests (`tests/test_content_checker.py`)

3 new tests:
- `test_explicit_skip_false_allows_explicit_track`: explicit_skip=False bypasses Tier 1 (D-16)
- `test_explicit_skip_true_skips_explicit_track`: explicit_skip=True preserves FILT-01 behavior
- `test_explicit_skip_default_is_true`: no regression on default ContentChecker() usage

All 16 tests pass (13 pre-existing + 3 new).

### Daemon Changes (`daemon.py`)

**PROFILE_MAP constant** (4 profiles):
- `kids_present`: explicit_skip=True, min_severity=2, all scanners enabled
- `were_all_adults`: explicit_skip=False, min_severity=3, drug disabled, sexual+profanity enabled
- `above_the_covers`: explicit_skip=False, min_severity=2, drug+profanity disabled, sexual enabled
- `permissive`: explicit_skip=True, min_severity=2, all lyric scanning disabled

**`_build_content_checker()` helper**: Constructs ContentChecker from PROFILE_MAP config. Falls back to `kids_present` for unknown keys. Scanner objects are passed through (long-lived); only the ContentChecker wrapper is rebuilt.

**`poll_loop` updates**:
- Signature extended with `lyrics_service`, `profanity_scanner`, `drug_scanner`, `sexual_content_scanner`
- `prev_profile: str` initialized from `state.get("active_profile", "kids_present")`
- Profile change detection: on each track change, compares `current_profile != prev_profile`; if changed, calls `_build_content_checker()` and logs `[PROFILE] switched to <profile>`

**`main()` updates**:
- ContentChecker now created via `_build_content_checker(startup_profile, ...)` using active_profile from state.json
- All scanner instances passed to `poll_loop` for dynamic rebuild capability

## Decisions Made

- `explicit_skip` defaults `True` — preserves all existing Tier 1 explicit-skip behavior with zero regression
- PROFILE_MAP as a module-level dict constant — simple, readable, no external config needed
- Scanner objects created once in `main()`, passed through to `poll_loop` — avoids recreation cost on profile switch
- `_build_content_checker()` falls back to `kids_present` on unknown profile key — safest default per project context (children ages 3 and 7)
- `poll_loop` signature extended with keyword-optional scanner args (default None) — backward compatible if called without them

## Verification Results

```
pytest tests/test_content_checker.py -x -q  → 16 passed
python -c "import daemon; print('OK')"       → OK
grep explicit_skip content_checker.py        → 4 matches (docstring, param, assignment, Tier 1 gate)
grep PROFILE_MAP daemon.py                   → 3 matches (definition, fallback lookup ×2)
grep _build_content_checker daemon.py        → 3 matches (definition, main(), poll_loop)
grep prev_profile daemon.py                  → 3 matches (init, comparison, assignment)
```

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all changes are fully wired. The `active_profile` key in state.json is read by the daemon on each track change; it will default to `kids_present` until a profile selector UI writes it (Phase 16 Plan 02/03).

## Self-Check

- [x] `tests/test_content_checker.py` contains 3 new explicit_skip tests
- [x] `content_checker.py` contains `explicit_skip: bool = True` parameter
- [x] `content_checker.py` Tier 1 reads `if self.explicit_skip and track.get("explicit", False):`
- [x] `daemon.py` contains PROFILE_MAP with 4 profile keys
- [x] `daemon.py` contains `_build_content_checker()` function
- [x] `daemon.py` contains `prev_profile` tracking
- [x] All 16 tests pass
- [x] Commits e3d7730, b4c3554, 6710bb6 exist
