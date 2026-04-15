---
phase: 23-trackcache-seam
plan: "02"
subsystem: track-cache
tags: [sqlite, caching, content-checker, daemon, tdd, injection]
dependency_graph:
  requires: [track_cache.TrackCache, track_cache.SQLiteTrackCache, content_checker.ContentChecker]
  provides: [ContentChecker.track_cache seam, daemon SQLiteTrackCache wiring]
  affects: [content_checker.py, daemon.py]
tech_stack:
  added: []
  patterns: [cache fast-path with single-exit check(), TYPE_CHECKING import cycle guard, _run_pipeline() delegation]
key_files:
  created: []
  modified:
    - content_checker.py
    - daemon.py
    - tests/test_content_checker.py
decisions:
  - "_run_pipeline() delegation pattern — check() has single exit point, cache get before, cache put after"
  - "TYPE_CHECKING guard in content_checker.py prevents runtime import cycle with track_cache.py"
  - "track_cache=None default preserves zero-behavior-change for all existing callers"
  - "SQLiteTrackCache shares LYRICS_DB_PATH — same SQLite file, separate table (eval_results)"
  - "track_cache.close() called in main() shutdown path alongside lyrics_service.close()"
metrics:
  duration: "~8 minutes"
  completed_date: "2026-04-15"
  tasks_completed: 2
  files_changed: 3
---

# Phase 23 Plan 02: TrackCache Wiring Summary

**One-liner:** ContentChecker gains cache fast-path via injected TrackCache seam; daemon.py instantiates SQLiteTrackCache once and threads it through both _build_content_checker call sites.

## What Was Built

**content_checker.py** — TrackCache injection and cache fast-path:

- `from __future__ import annotations` + `TYPE_CHECKING` guard — prevents runtime import cycle (track_cache.py imports TrackEvalResult from content_checker.py; the guard breaks the cycle)
- `track_cache: "TrackCache | None" = None` added to `ContentChecker.__init__`
- `check()` refactored to delegate pipeline to `_run_pipeline()`. New `check()` body: cache get before pipeline, cache put after
- `_run_pipeline()` — contains the verbatim previous `check()` body with all five tiers unchanged

**daemon.py** — SQLiteTrackCache wiring:

- `from track_cache import SQLiteTrackCache` added
- `_build_content_checker()` gains `track_cache=None` parameter; passes to ContentChecker
- `main()` instantiates `SQLiteTrackCache(db_path=LYRICS_DB_PATH)` once after LyricsService
- Startup call to `_build_content_checker()` passes `track_cache`
- Profile-change call site inside `poll_loop` passes `track_cache` (Pitfall 4 resolved)
- `poll_loop()` signature gains `track_cache=None` parameter
- `await track_cache.close()` in shutdown path

**tests/test_content_checker.py** — 4 new cache tests appended:

- `test_cache_hit_skips_pipeline` — cache hit returns immediately, lyrics_service never called
- `test_cache_miss_writes_result` — miss runs pipeline and writes result via track_cache.put
- `test_none_cache_no_error` — ContentChecker(track_cache=None) works without error
- `test_cache_hit_explicit_tier` — explicit track cached result returned without Tier 1 re-evaluation

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 RED | Failing cache tests | 719f5f8 | tests/test_content_checker.py |
| 1 GREEN | ContentChecker cache seam | 81c6f78 | content_checker.py |
| 2 | daemon.py wiring | d6182b2 | daemon.py |

## Test Coverage

| Test | Requirement | Result |
|------|-------------|--------|
| test_cache_hit_skips_pipeline | CACHE-03 | PASS |
| test_cache_miss_writes_result | CACHE-04 | PASS |
| test_none_cache_no_error | CACHE-03 backward compat | PASS |
| test_cache_hit_explicit_tier | CACHE-03 | PASS |
| All 15 previous content checker tests | regression | 14 PASS, 1 pre-existing FAIL |
| All 8 track cache tests | CACHE-01/02 | PASS |

## Verification

- `pytest tests/test_content_checker.py -v` — 19/20 passed (1 pre-existing failure: test_no_lyrics_no_scanners_allows)
- `pytest tests/test_track_cache.py -v` — 8/8 passed
- `pytest` (full suite) — 108/113 passed (5 pre-existing failures, none caused by this plan)
- `ruff check content_checker.py daemon.py` — no lint errors

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Pre-existing ruff errors in daemon.py**

- **Found during:** Task 2 ruff check
- **Issue:** daemon.py had pre-existing `I001` (import sort) and `F821` (undefined `TrackEvalResult`) ruff errors. The plan requires `ruff check daemon.py` exits 0, so these had to be fixed.
- **Fix:** Added `from __future__ import annotations`; sorted import blocks (stdlib → third-party → local); added `TrackEvalResult` to the `from content_checker import` line
- **Files modified:** daemon.py
- **Commit:** d6182b2

## Pre-existing Test Failures (not caused by this plan)

All 5 failures existed before any changes in this plan:
- `tests/test_content_checker.py::test_no_lyrics_no_scanners_allows` — pre-existing logic mismatch
- `tests/test_info_icon.py::test_info_profile_map_present` — pre-existing
- `tests/test_sexual_content_scanner.py::test_sexual_terms_disjoint_from_severity_map` — pre-existing
- `tests/test_skip_client.py::test_soco_pause_uses_cached_ip` — pre-existing
- `tests/test_skip_client.py::test_soco_pause_falls_back_to_discovery_when_not_cached` — pre-existing

## Known Stubs

None — cache is fully wired end-to-end. No placeholder data flows to callers.

## Self-Check

- `content_checker.py` exists: FOUND
- `daemon.py` exists: FOUND
- `tests/test_content_checker.py` exists: FOUND
- Commit 719f5f8 (RED tests): FOUND
- Commit 81c6f78 (GREEN ContentChecker): FOUND
- Commit d6182b2 (daemon wiring): FOUND
- 4 new cache tests pass: VERIFIED
- ruff content_checker.py exits 0: VERIFIED
- ruff daemon.py exits 0: VERIFIED
- Full suite 108 pass (5 pre-existing failures): VERIFIED

## Self-Check: PASSED
