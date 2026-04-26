---
phase: 30-per-user-daemon-management
plan: 02
subsystem: infra
tags: [asyncio, subprocess, supervisor, fastapi, lifespan, daemon-management]

# Dependency graph
requires:
  - phase: 30-per-user-daemon-management
    provides: TDD RED scaffolds for _spawn_daemon, _supervisor_for_uid, lifespan (Plan 01)
  - phase: 29-oauth-onboarding-flow
    provides: /auth/callback with fire-and-forget spawn (replaced by _spawn_daemon in this plan)
provides:
  - _spawn_daemon(uid) — shared coroutine that spawns daemon with uid-specific env vars, writes PID file, stores in _daemons
  - _supervisor_for_uid(uid) — asyncio supervisor coroutine with restart policy (codes 0/2/unexpected, D-13 removal check)
  - _daemons module-level dict tracking live asyncio.subprocess.Process per uid
  - FastAPI lifespan context manager booting daemons for all active users on startup
  - /auth/callback refactored to use _spawn_daemon + supervisor task instead of bare create_subprocess_exec
affects: [30-per-user-daemon-management, 31-https-caddy-integration]

# Tech tracking
tech-stack:
  added:
    - contextlib.asynccontextmanager (stdlib — for FastAPI lifespan decorator)
  patterns:
    - FastAPI lifespan context manager pattern (replaces deprecated @app.on_event("startup"))
    - asyncio supervisor while-loop: await proc.wait() → check exit code → restart or exit
    - _daemons dict follows established _tails/_subscribers per-uid asyncio state pattern
    - stderr=DEVNULL on all daemon spawns (avoids pipe-buffer stall — RESEARCH.md Pitfall 5)

key-files:
  created: []
  modified:
    - web_ui/main.py

key-decisions:
  - "lifespan context manager defined before app = FastAPI() — Python resolves _registry/_spawn_daemon/_supervisor_for_uid at call time (runtime), not definition time; no forward-reference issue"
  - "No max retry count on supervisor restart — correct per D-08 (5-user beta scale)"
  - "Supervisor cancellation on shutdown prevents 'Task was destroyed but it is pending!' asyncio warnings in tests"

patterns-established:
  - "_spawn_daemon is the single spawn entry point for both lifespan (boot) and /auth/callback (new user) — no duplicated env var assembly"
  - "Supervisor re-checks registry after each proc.wait() (D-13) — handles remove-while-running without shared stop-set"

requirements-completed: [PROC-01, PROC-02, PROC-03, PROC-04]

# Metrics
duration: 3min
completed: 2026-04-26
---

# Phase 30 Plan 02: Per-User Daemon Management Supervisor Infrastructure Summary

**asyncio supervisor layer in web_ui/main.py: _spawn_daemon, _supervisor_for_uid coroutine with restart policy, _daemons dict, FastAPI lifespan boot, and /auth/callback refactor**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-04-26T14:48:05Z
- **Completed:** 2026-04-26T14:50:12Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments
- Added `_daemons: dict[str, asyncio.subprocess.Process] = {}` module-level dict following established _tails/_subscribers pattern
- Implemented `_spawn_daemon(uid)` — sets STATE_PATH, EVENTS_PATH, LYRICS_DB_PATH, SPOTIFY_CACHE_PATH, POLL_INTERVAL_SECONDS=3; writes PID file; stores process in _daemons
- Implemented `_supervisor_for_uid(uid)` — while-loop supervisor: restarts on unexpected exit, stops on code 0 (clean) or code 2 (token revoked), re-checks registry after each exit (D-13)
- Added FastAPI lifespan context manager — boots daemons for all `status == "active"` users on startup; cancels supervisor tasks on shutdown
- Refactored /auth/callback to call `await _spawn_daemon(uid)` + `asyncio.create_task(_supervisor_for_uid(uid))` — removes inline env var assembly and `stderr=PIPE` stall risk
- All 10 new Phase 30 web_ui tests turn green; all 42 test_web_ui_endpoints.py tests pass

## Task Commits

1. **Task 1: _daemons dict, _spawn_daemon, _supervisor_for_uid, lifespan context manager** - `4bdb3ed` (feat)
2. **Task 2: Refactor /auth/callback to use _spawn_daemon + supervisor task** - `870f562` (feat)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified
- `web_ui/main.py` - Added asynccontextmanager import, _daemons dict, _spawn_daemon function, _supervisor_for_uid coroutine, lifespan context manager; wired lifespan= to FastAPI app; replaced bare spawn block in /auth/callback

## Decisions Made
- `lifespan` defined before `app = FastAPI()` per plan instructions — Python resolves function-body references at call time, so _registry/_spawn_daemon/_supervisor_for_uid are available when lifespan runs despite appearing later in the file
- Supervisor tasks cancelled on FastAPI shutdown (lifespan yield → cancel all tasks) — prevents asyncio "pending task destroyed" warnings in test teardown

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Pre-existing RED test failures from Plan 01 remain (test_three_consecutive_401s_trigger_exit2 in test_daemon_events.py, test_remove_sends_sigterm_to_daemon in test_manage_users.py) — confirmed out-of-scope per Plan 01 summary; belong to Plans 03/04 implementation work

## Known Stubs
None.

## Next Phase Readiness
- PROC-01, PROC-02, PROC-03, PROC-04 all have passing test coverage
- /auth/callback and lifespan both wire supervisor tasks correctly
- Plan 03 can implement daemon.py consecutive-401 counter (turning test_three_consecutive_401s_trigger_exit2 green)
- Plan 04 can implement manage_users.py _stop_daemon_via_pid (turning manage_users RED tests green)

---
*Phase: 30-per-user-daemon-management*
*Completed: 2026-04-26*
