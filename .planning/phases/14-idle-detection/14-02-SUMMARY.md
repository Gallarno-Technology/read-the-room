---
phase: 14-idle-detection
plan: 02
subsystem: daemon, ui
tags: [idle-detection, sse, debounce, state-machine, asyncio]

# Dependency graph
requires:
  - phase: 14-idle-detection
    provides: RED idle-detection tests and _run_n_empty_cycles helper (plan 01)
  - phase: 06-daemon-sse-extensions
    provides: poll_loop, _write_now_playing, _append_event, SSE event pipeline
provides:
  - Idle state machine in daemon.py poll_loop (IDLE_THRESHOLD=3, idle_counter, was_idle)
  - Idle SSE event handling in dashboard es.onmessage
affects: [15-skip-history-persistence, 16-filter-profiles]

# Tech tracking
tech-stack:
  added: []
  patterns: [debounce counter with dedup flag for transition-only writes]

key-files:
  created: []
  modified: [daemon.py, web_ui/templates/index.html]

key-decisions:
  - "idle_counter reset at top of else branch (not inside track_id change sub-block) to handle same-track continuation polls"
  - "currentTrackId set to null on idle to prevent stale eval_result badge updates"

patterns-established:
  - "Idle state machine: counter + dedup flag pattern for debounced transition detection"

requirements-completed: [IDLE-01, IDLE-02]

# Metrics
duration: 2min
completed: 2026-04-04
---

# Phase 14 Plan 02: Idle Detection Implementation Summary

**Idle state machine with 3-poll debounce in daemon.py + idle SSE branch in dashboard es.onmessage**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-04-04T18:57:09Z
- **Completed:** 2026-04-04T18:59:20Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Implemented idle state machine in daemon.py: IDLE_THRESHOLD=3 constant, idle_counter and was_idle variables, debounced write of {"status":"idle"} to now_playing.json, idle event emission to events.jsonl
- Added idle SSE branch in dashboard es.onmessage: calls renderIdle() and clears currentTrackId on idle event
- All 5 idle tests GREEN (previously 4 RED from plan 01); full daemon event suite 17/17 passing

## Task Commits

1. **Task 1: Add idle counter, flag, and debounce logic to daemon.py poll_loop** - `061918c` (feat)
2. **Task 2: Add idle SSE branch to es.onmessage in index.html** - `acfcd69` (feat)

**Plan metadata:** (see final commit below)

## Files Created/Modified
- `daemon.py` - Added IDLE_THRESHOLD constant, idle_counter/was_idle state variables, debounce write logic in no-playback branch, idle reset in else branch
- `web_ui/templates/index.html` - Added `else if (evt.type === 'idle')` branch with renderIdle() and currentTrackId = null

## Decisions Made
- idle_counter reset placed at top of else branch (before `track = result["item"]`) to ensure resets on every active poll, not just track changes -- prevents idle_counter accumulating during same-track continuation
- currentTrackId nulled on idle to prevent stale eval_result from updating badge after idle card shown

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Known Pre-existing Failures
- 2 tests in test_skip_client.py (soco_pause) fail before and after this plan -- logged to deferred-items.md

## Next Phase Readiness
- Idle detection fully wired: daemon writes idle state, dashboard renders idle card via SSE
- hydrateNowPlaying() already handles {"status":"idle"} from now_playing.json (no changes needed)
- Ready for skip history persistence (Phase 15) and filter profiles (Phase 16)

---
*Phase: 14-idle-detection*
*Completed: 2026-04-04*
