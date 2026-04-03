---
phase: 06-daemon-sse-extensions
plan: 01
subsystem: testing
tags: [pytest, pytest-asyncio, daemon, asyncio, xfail, tdd]

requires:
  - phase: 05-sonos-healthcheck
    provides: stable daemon.py with poll_loop, _append_skip_event, SKIP_EVENTS_PATH

provides:
  - 9 xfail test stubs covering DAEM-01, DAEM-02, DAEM-03 and D-01 regression
  - data_dir fixture for isolated filesystem testing of daemon event I/O
  - _run_one_cycle helper for driving poll_loop in tests with a single track detection

affects:
  - 06-02 (EVENTS_PATH rename + _append_event): tests turn green on rename
  - 06-03 (track_change + eval_result emission): tests turn green on implementation
  - 06-04 (now_playing.json): tests turn green on implementation

tech-stack:
  added: []
  patterns:
    - data_dir fixture using monkeypatch.setattr on daemon.EVENTS_PATH and daemon.NOW_PLAYING_PATH
    - _run_one_cycle helper drives poll_loop for exactly one cycle via asyncio.sleep replacement
    - xfail(strict=False) marks all stubs so suite reports xfail until implementation lands

key-files:
  created:
    - tests/test_daemon_events.py
  modified: []

key-decisions:
  - "Tests reference post-rename names (EVENTS_PATH, NOW_PLAYING_PATH) even before rename exists — xfail catches AttributeError"
  - "All 9 tests marked xfail(strict=False) so existing suite remains greenish during Wave 1"
  - "eval_result not emitted on skip failure — test_eval_result_not_emitted_on_skip_failure enforces this"

patterns-established:
  - "Pattern: data_dir fixture redirects all daemon file I/O to tmp_path via monkeypatch.setattr"
  - "Pattern: _run_one_cycle replaces asyncio.sleep to fire stop_event after one iteration"

requirements-completed:
  - DAEM-01
  - DAEM-02
  - DAEM-03

duration: 5min
completed: 2026-04-03
---

# Phase 6 Plan 1: Daemon Events Test Scaffold Summary

**9-test xfail scaffold covering DAEM-01 track_change, DAEM-02 eval_result, DAEM-03 now_playing.json and D-01 regression — ready for Wave 1 implementation**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-04-03T10:21:32Z
- **Completed:** 2026-04-03T10:26:30Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Created `tests/test_daemon_events.py` with 9 named test stubs, all marked `xfail(strict=False)`
- Tests reference post-rename attribute names (`EVENTS_PATH`, `NOW_PLAYING_PATH`, `_append_event`) so Wave 1 plans can make tests pass incrementally
- `data_dir` fixture redirects all daemon file I/O to `tmp_path` for full isolation
- `_run_one_cycle()` helper drives `poll_loop` for exactly one track detection iteration without real Spotify calls
- Existing test suite (16 passing, 2 pre-existing failures in test_skip_client.py) unaffected

## Task Commits

1. **Task 1: Write failing test scaffold for all daemon event behaviors** - `37547c2` (test)

## Files Created/Modified

- `tests/test_daemon_events.py` - 9 xfail test stubs covering all Phase 6 daemon event requirements

## Decisions Made

- Tests reference the post-rename names (`EVENTS_PATH`, `NOW_PLAYING_PATH`) even before the rename exists in Plan 02. This means tests fail with `AttributeError` (caught by xfail) until the rename lands — no special test branching needed.
- All 9 tests use `xfail(strict=False)` rather than strict xfail, so unexpected passes during partial implementation don't break CI.
- `test_eval_result_not_emitted_on_skip_failure` asserts no eval_result is written when both skip clients return False — enforcing the RESEARCH.md recommendation against emitting on skip failure.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Wave 0 scaffold complete — all 9 test stubs exist and are xfail
- Plan 02 (EVENTS_PATH rename) will turn `test_existing_events_unaffected` green
- Plans 02/03/04 (implementation) will turn remaining 8 tests green
- No blockers

## Self-Check: PASSED

- FOUND: tests/test_daemon_events.py
- FOUND: 06-01-SUMMARY.md
- FOUND: commit 37547c2

---
*Phase: 06-daemon-sse-extensions*
*Completed: 2026-04-03*
