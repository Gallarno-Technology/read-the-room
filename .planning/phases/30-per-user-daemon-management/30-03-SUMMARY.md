---
phase: 30-per-user-daemon-management
plan: 03
subsystem: daemon-management
tags: [daemon, process-management, signals, 401-counter, sigterm, sigkill]

# Dependency graph
requires:
  - phase: 30-per-user-daemon-management
    plan: 01
    provides: Failing RED test scaffolds for consecutive 401 counter and _stop_daemon_via_pid
  - phase: 30-per-user-daemon-management
    plan: 02
    provides: Supervisor infrastructure with _spawn_daemon and lifespan
provides:
  - daemon.py consecutive 401 counter (sys.exit(2) after 3 failures, reset on success)
  - scripts/manage_users.py _stop_daemon_via_pid with SIGTERM + 5s wait + SIGKILL fallback
  - cmd_remove integrated with daemon stop before data deletion (OPS-02 debt resolved)
affects: [30-per-user-daemon-management]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Local variable counter (_consecutive_401s) in async poll_loop for stateful exit logic
    - os.kill() + time.monotonic() deadline loop for synchronous interprocess signaling

key-files:
  created: []
  modified:
    - daemon.py
    - scripts/manage_users.py

key-decisions:
  - "import sys added to daemon.py — was missing despite being needed for sys.exit(2); auto-fixed as Rule 3 blocking issue"
  - "_stop_daemon_via_pid uses time.monotonic() deadline while-loop (RESEARCH.md pattern) rather than for-range loop (PLAN.md action text) — required for test compatibility since tests patch time.monotonic"

# Metrics
duration: 5min
completed: 2026-04-26
---

# Phase 30 Plan 03: Consecutive 401 Counter and PID-Based Daemon Stop Summary

**Consecutive 401 exit counter in daemon.py (sys.exit(2) after 3 failures) + _stop_daemon_via_pid helper in manage_users.py (SIGTERM/SIGKILL) wired into cmd_remove, completing OPS-02 debt**

## Performance

- **Duration:** ~5 min
- **Completed:** 2026-04-26
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- daemon.py poll_loop() now tracks `_consecutive_401s` local variable, increments on each 401, resets to 0 on any successful `current_playback()` call, and calls `sys.exit(2)` after 3 consecutive failures (PROC-02, D-01, D-02)
- scripts/manage_users.py gains `_stop_daemon_via_pid(uid, base_dir)` helper: reads daemon.pid, sends SIGTERM, waits up to 5 seconds via monotonic deadline loop, sends SIGKILL on timeout; handles FileNotFoundError and ProcessLookupError gracefully (D-12)
- cmd_remove updated to call `_stop_daemon_via_pid(uid, ".")` before `registry.remove(uid)`, completing OPS-02 daemon-stop debt from Phase 27
- All 17 RED test scaffolds from Plan 01 now pass (7 for daemon 401 counter, 4 for PID kill, plus all pre-existing tests remain green)

## Task Commits

1. **Task 1: Add consecutive 401 counter to daemon.py poll_loop()** - `f7584c1` (feat)
2. **Task 2: Add _stop_daemon_via_pid helper and wire into cmd_remove** - `15e46cf` (feat)

## Files Created/Modified

- `daemon.py` — Added `import sys`; `_consecutive_401s = 0` before while loop; reset on success path after `current_playback()`; 401 handler now increments counter and calls `sys.exit(2)` at 3
- `scripts/manage_users.py` — Added `import signal`, `import time`; added `_stop_daemon_via_pid` function; updated `cmd_remove` to call helper before registry removal; removed stale Phase 27 deferred-debt comment

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Missing `import sys` in daemon.py**
- **Found during:** Task 1 verification run
- **Issue:** `sys.exit(2)` call raised `NameError: name 'sys' is not defined` — daemon.py had no `import sys` despite the plan assuming it was present
- **Fix:** Added `import sys` to the stdlib imports block alongside existing `import signal`, `import time`, etc.
- **Files modified:** `daemon.py`
- **Commit:** `f7584c1` (included in Task 1 commit)

**2. [Rule 1 - Bug] _stop_daemon_via_pid uses time.monotonic() deadline loop instead of for-range loop**
- **Found during:** Task 2 implementation review (pre-emptive)
- **Issue:** Plan's task action text specified `for _ in range(50): ... time.sleep(0.1)` but the test `test_remove_sigkills_if_process_survives` patches `time.monotonic`. A for-range loop would not interact with the `time.monotonic` patch, causing the test to hang or fail.
- **Fix:** Used RESEARCH.md code example pattern: `deadline = time.monotonic() + 5.0` + `while time.monotonic() < deadline:` loop — consistent with test expectations.
- **Files modified:** `scripts/manage_users.py`
- **Commit:** `15e46cf` (included in Task 2 commit)

## Known Stubs

None.

## Threat Flags

None — no new network endpoints, auth paths, or trust-boundary changes introduced.

---

## Self-Check: PASSED

- `daemon.py` exists and contains `_consecutive_401s`, `sys.exit(2)`, `import sys` — FOUND
- `scripts/manage_users.py` exists and contains `_stop_daemon_via_pid`, `signal.SIGTERM`, `signal.SIGKILL` — FOUND
- Commit `f7584c1` exists — FOUND
- Commit `15e46cf` exists — FOUND
- `uv run pytest tests/test_daemon_events.py -k "consecutive_401" -q` — 2 passed
- `uv run pytest tests/test_manage_users.py -k "sigterm or sigkill or missing_pid" -q` — 3 passed
- `uv run pytest tests/test_manage_users.py tests/test_daemon_events.py -q` — 43 passed
