---
phase: 14-idle-detection
plan: 01
subsystem: testing
tags: [pytest, asyncio, idle-detection, tdd, red-tests]

# Dependency graph
requires:
  - phase: 06-daemon-sse-extensions
    provides: poll_loop implementation and test patterns this file extends
provides:
  - Five RED idle-detection test functions in test_daemon_events.py
  - _run_n_empty_cycles helper for simulating empty playback cycles
affects: [14-02-idle-detection-implementation]

# Tech tracking
tech-stack:
  added: []
  patterns: [_run_n_empty_cycles helper pattern for multi-cycle empty poll simulation]

key-files:
  created: []
  modified: [tests/test_daemon_events.py]

key-decisions:
  - "test_idle_debounce passes vacuously (no-op implementation satisfies absence assertion); this is correct — the test's purpose is to assert no idle fires below threshold, and the no-op implementation satisfies that by default"

patterns-established:
  - "_run_n_empty_cycles: helper mirrors _run_one_cycle but uses a call counter to fire stop_event after N sleeps; resume_on parameter injects one active track cycle for reset tests"

requirements-completed: [IDLE-01, IDLE-02]

# Metrics
duration: 1min
completed: 2026-04-04
---

# Phase 14 Plan 01: Idle-Detection RED Tests Summary

**Five failing idle-detection tests + _run_n_empty_cycles helper scaffolding daemon.poll_loop idle behavior contracts (IDLE-01, IDLE-02)**

## Performance

- **Duration:** ~1 min
- **Started:** 2026-04-04T18:07:22Z
- **Completed:** 2026-04-04T18:08:27Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Added `_run_n_empty_cycles` helper that simulates N consecutive empty polls (current_playback returns None), with optional `resume_on` parameter for testing idle reset behavior
- Four idle tests fail RED (assertion errors — no idle logic in daemon.poll_loop yet): test_idle_writes_now_playing, test_idle_dedup, test_idle_resets_on_track, test_idle_event_emitted
- One test (test_idle_debounce) passes vacuously — correctly asserting absence of idle behavior below threshold, which the no-implementation satisfies
- All 12 pre-existing tests remain green

## Task Commits

1. **Task 1: Add multi-cycle idle helper and five RED tests** - `31a355f` (test)

**Plan metadata:** (see final commit below)

## Files Created/Modified
- `tests/test_daemon_events.py` - Added _run_n_empty_cycles helper and 5 idle test functions after existing tests

## Decisions Made
- test_idle_debounce passes vacuously against no-implementation: this is by design — the test asserts absence (no idle event written for 2 polls), and a no-op satisfies absence assertions. Plan 02 will verify this test remains green after adding threshold=3 logic.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- RED state established: 4 of 5 idle tests fail with assertion errors (not import/syntax errors)
- test_daemon_events.py collection succeeds: 17 tests collected
- Plan 02 can now drive daemon.py implementation to turn RED -> GREEN
- Idle threshold is 3 consecutive empty polls (contracts defined by tests)

---
*Phase: 14-idle-detection*
*Completed: 2026-04-04*
