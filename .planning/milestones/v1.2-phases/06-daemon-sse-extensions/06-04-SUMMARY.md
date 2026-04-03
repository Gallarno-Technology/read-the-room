---
phase: 06-daemon-sse-extensions
plan: "04"
subsystem: daemon
tags: [daemon, now_playing, events, jsonl, iso8601, pytest]

# Dependency graph
requires:
  - phase: 06-03
    provides: album_art_url local variable in scope, eval_result _append_event calls in all 4 outcome branches
provides:
  - _write_now_playing() helper writes now_playing.json with ISO-8601 timestamps
  - now_playing.json written twice per track: evaluating (before check) + final eval_state (after check)
  - DAEM-03 requirement fully satisfied
  - All 9 test_daemon_events.py tests pass (DAEM-01 through DAEM-03)
affects: [07-web-backend, 08-dashboard-ui]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "_write_now_playing() direct open('w') pattern — no atomic rename (EBUSY on bind mounts)"
    - "os.makedirs with 'or .' guard for dirname of path with no directory component"
    - "ISO-8601 timestamp via datetime.datetime.utcnow().isoformat() + 'Z' for now_playing.json"

key-files:
  created: []
  modified:
    - daemon.py

key-decisions:
  - "Direct open('w') for now_playing.json writes — os.replace() raises EBUSY on bind-mounted files (established pattern from Phase 1)"
  - "os.makedirs guard uses 'or .' to handle paths with no directory component"
  - "_eval_state_from_result(action, reason) called twice in allow branch (once for eval_result, once for now_playing) — consistent with existing pattern"

patterns-established:
  - "Pattern 1: _write_now_playing(data: dict) is the canonical interface for updating now_playing.json — callers pass full schema dict including all 6 fields"
  - "Pattern 2: now_playing.json always written unconditionally after track detection (eval_state=evaluating), then overwritten in each FSM branch with final state"

requirements-completed:
  - DAEM-03

# Metrics
duration: 2min
completed: 2026-04-03
---

# Phase 6 Plan 04: now_playing.json hydration writes Summary

**_write_now_playing() helper added to daemon.py with 5 call sites: eval_state=evaluating before check() and final eval_state in all 4 outcome branches (allow, paused, skipped, fsm-off)**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-03T10:34:01Z
- **Completed:** 2026-04-03T10:36:01Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments
- Implemented `_write_now_playing(data: dict)` helper with OSError guard, os.makedirs guard, and direct open("w") write pattern
- Added first call site immediately after track_change `_append_event` — writes eval_state="evaluating" before ContentChecker runs
- Added 4 final-state call sites after each `eval_result` _append_event in the allow, five_skip pause, skip-success, and FSM-off branches
- All 9 tests in test_daemon_events.py now pass (DAEM-01, DAEM-02, DAEM-03 complete)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add _write_now_playing helper and first call site (eval_state=evaluating)** - `7003d2a` (feat)
2. **Task 2: Add final-state now_playing.json writes in all outcome branches** - `b22d599` (feat)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified
- `daemon.py` - Added _write_now_playing() function definition and 5 call sites

## Decisions Made
- Used `datetime.datetime.utcnow().isoformat() + "Z"` for ISO-8601 timestamps in now_playing.json, following the plan spec (despite Python 3.12 deprecation warning — consistent with prior decision to use this pattern)
- Called `_eval_state_from_result(action, reason)` twice in the allow branch to avoid caching the result in a local variable — simpler code with negligible overhead

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None. All test stubs transitioned from XFAIL to XPASS as expected.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `data/now_playing.json` is now written on every track cycle by the daemon
- Phase 7 (`GET /now-playing` endpoint) can read this file for page-load hydration of the now-playing card
- No blockers

## Self-Check: PASSED

- SUMMARY.md: FOUND
- Task 1 commit 7003d2a: FOUND
- Task 2 commit b22d599: FOUND

---
*Phase: 06-daemon-sse-extensions*
*Completed: 2026-04-03*
