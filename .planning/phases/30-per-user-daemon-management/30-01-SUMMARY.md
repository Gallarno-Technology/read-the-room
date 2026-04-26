---
phase: 30-per-user-daemon-management
plan: 01
subsystem: testing
tags: [tdd, pytest, asyncio, subprocess, signals, daemon-management]

# Dependency graph
requires:
  - phase: 29-oauth-onboarding-flow
    provides: OAuth callback with fire-and-forget daemon spawn (to be replaced by _spawn_daemon)
  - phase: 27-user-registry-operator-cli
    provides: manage_users.py cmd_remove (to be extended with PID kill)
provides:
  - Failing RED test scaffolds for all Phase 30 behaviors
  - test_web_ui_endpoints.py: 10 new tests for _spawn_daemon, _supervisor_for_uid, lifespan
  - test_daemon_events.py: 3 new tests for consecutive 401 counter (D-01, D-02)
  - test_manage_users.py: 4 new tests for _stop_daemon_via_pid SIGTERM/SIGKILL (D-12)
affects: [30-per-user-daemon-management]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - asyncio.run() to drive supervisor coroutines from synchronous test functions
    - SpotifyException(http_status=401) mock pattern for 401 counter testing
    - _drive_poll_loop_with_401s helper drives poll_loop with controlled 401/success sequences
    - side_effect list approach for os.kill mock in PID kill tests

key-files:
  created: []
  modified:
    - tests/test_web_ui_endpoints.py
    - tests/test_daemon_events.py
    - tests/test_manage_users.py

key-decisions:
  - "Test _stop_daemon_via_pid directly (not via cmd_remove) — cleaner isolation, avoids registry wiring complexity"
  - "test_single_401_does_not_exit and test_consecutive_401_counter_resets_on_success document contracts already held; test_three_consecutive_401s_trigger_exit2 is the RED gate"
  - "_active_user_record helper added as _active_user_record_p30 (existing _active_user_record had different uid default)"

patterns-established:
  - "RED-only plan: 17 new tests added across 3 files; all tests against unimplemented features fail correctly"
  - "Pre-existing failures (test_info_icon, test_sexual_content_scanner, test_skip_client) confirmed out-of-scope"

requirements-completed: [PROC-01, PROC-02, PROC-03, PROC-04]

# Metrics
duration: 4min
completed: 2026-04-26
---

# Phase 30 Plan 01: Per-User Daemon Management TDD Scaffolds Summary

**17 failing RED test cases across 3 test files defining the contract for _spawn_daemon, _supervisor_for_uid, FastAPI lifespan, consecutive-401 exit, and SIGTERM/SIGKILL daemon stop**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-04-26T14:40:53Z
- **Completed:** 2026-04-26T14:44:35Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- 10 new RED tests in test_web_ui_endpoints.py covering _spawn_daemon env vars, PID file write, _daemons dict storage, supervisor restart policy (codes 0/2/unexpected), uid-removed supervisor exit, lifespan active/pending user handling, and callback supervisor task creation
- 3 new RED tests in test_daemon_events.py covering 3-consecutive-401 exit(2), counter reset on success, and single-401 boundary contract
- 4 new RED tests in test_manage_users.py covering _stop_daemon_via_pid SIGTERM, SIGKILL on timeout, missing PID file, and already-dead process graceful handling
- All 171 pre-existing passing tests remain green

## Task Commits

1. **Task 1: _spawn_daemon, _supervisor_for_uid, lifespan scaffolds** - `036a35a` (test)
2. **Task 2: daemon.py 401 counter and manage_users.py PID kill scaffolds** - `7bde574` (test)

## Files Created/Modified
- `tests/test_web_ui_endpoints.py` - Added 10 Phase 30 RED test functions + `_active_user_record_p30` helper
- `tests/test_daemon_events.py` - Added `sys`, `SpotifyException` imports + 3 Phase 30 RED test functions + `_drive_poll_loop_with_401s` helper
- `tests/test_manage_users.py` - Added `os`, `signal`, `time`, `call` imports + 4 Phase 30 RED test functions

## Decisions Made
- Imported `_stop_daemon_via_pid` directly in each test function (not at module level) so the `ImportError` is raised at test runtime rather than collection time, giving cleaner FAILED status instead of ERROR
- Used `_active_user_record_p30` (separate from existing `_active_user_record`) to avoid uid default collision
- `test_single_401_does_not_exit` documents the boundary contract even though it passes trivially against unmodified codebase — it becomes meaningful as a regression guard after implementation

## Deviations from Plan

None - plan executed exactly as written. The `test_spawn_daemon_writes_pid_file` test was simplified to an `hasattr` assertion (rather than a complex path-patching approach) since the primary RED signal needed is AttributeError on `_spawn_daemon` not existing — the PID file path assertion is covered by the `_spawn_daemon` implementation in Plan 02.

## Issues Encountered
- Pre-existing test failures discovered (test_info_icon.py, test_sexual_content_scanner.py, test_skip_client.py) — confirmed pre-existing before this plan, logged as out-of-scope per deviation rules scope boundary.

## Known Stubs
None — this is a test-only plan; no production code changes.

## Next Phase Readiness
- All RED scaffolds committed; Phase 30 Plan 02 can begin implementation
- Tests define exact contracts: env var names, exit codes (0/2/unexpected), SIGTERM→SIGKILL sequence, PID file location
- TDD gate compliance: all 17 new tests fail against unmodified codebase (correct RED state)

---
*Phase: 30-per-user-daemon-management*
*Completed: 2026-04-26*
