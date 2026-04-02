---
phase: 03-signal-notifications-interactive-confirmations
plan: 01
subsystem: api
tags: [fastapi, asyncio, sse, server-sent-events, skip-queue, fsm-toggle]

# Dependency graph
requires:
  - phase: 02-content-filtering-auto-skip
    provides: daemon.py poll_loop with skip logic and save_state() read-merge-write pattern
provides:
  - skip_event_queue asyncio.Queue in daemon.py (SSE bridge for web_ui)
  - 5-consecutive-skip counter with pause_playback + five_skip_warning event
  - FastAPI web_ui service with /events SSE, GET /fsm, POST /fsm endpoints
  - web_ui package (web_ui/__init__.py, web_ui/main.py, web_ui/requirements.txt)
affects:
  - 03-02 (HTML template + docker-compose integration consumes this)

# Tech tracking
tech-stack:
  added: [fastapi==0.115.12, uvicorn[standard]==0.34.0, python-dotenv==1.2.2 (for web_ui)]
  patterns:
    - SSE broadcaster pattern (one source queue -> per-client subscriber queues)
    - FSM toggle read-merge-write (mirrors daemon save_state pattern)
    - In-process daemon queue import with fallback to local queue

key-files:
  created:
    - web_ui/__init__.py
    - web_ui/main.py
    - web_ui/requirements.txt
  modified:
    - daemon.py

key-decisions:
  - "skip_event_queue is a module-level asyncio.Queue in daemon.py; web_ui imports it directly when running in-process (standalone mode falls back to local queue)"
  - "Broadcaster pattern: one _SOURCE_QUEUE relays to per-client asyncio.Queue(maxsize=100) — prevents slow clients from blocking the source"
  - "consecutive_skips counter lives inside poll_loop() scope (not persisted to state.json) — resets on process restart, sufficient for v1 UX"
  - "five_skip_warning event uses same put_nowait path as skip events — uniform SSE message format for browser consumption"
  - "_save_state_merge in web_ui mirrors daemon save_state() exactly: read-load-update-write with direct write (not os.replace) per Phase 1 EBUSY decision"

patterns-established:
  - "SSE broadcaster: single asyncio.Queue source + list of per-client subscriber queues with QueueFull cleanup"
  - "In-process module import with ImportError fallback for multi-process / same-process flexibility"

requirements-completed: [FSM-03, SIG-01, SIG-04]

# Metrics
duration: 8min
completed: 2026-04-02
---

# Phase 03 Plan 01: Signal Notifications — Backend Wiring Summary

**asyncio.Queue skip event bridge in daemon.py with FastAPI SSE endpoint, 5-consecutive-skip pause logic, and FSM toggle API using daemon's read-merge-write state pattern**

## Performance

- **Duration:** 8 min
- **Started:** 2026-04-02T03:20:23Z
- **Completed:** 2026-04-02T03:28:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- daemon.py now pushes structured skip event dicts to skip_event_queue after every successful skip, with 5-consecutive-skip pause + five_skip_warning emission
- FastAPI web_ui service created with /events SSE StreamingResponse, GET/POST /fsm endpoints replicating daemon's state pattern
- Broadcaster pattern isolates each SSE client in its own asyncio.Queue(maxsize=100) so slow clients cannot block the daemon

## Task Commits

Each task was committed atomically:

1. **Task 1: Add skip event queue and 5-skip logic to daemon.py** - `af3629b` (feat)
2. **Task 2: Create FastAPI web_ui service (SSE, FSM toggle, FSM status)** - `c9b77c4` (feat)

## Files Created/Modified

- `daemon.py` - Added skip_event_queue module-level Queue, consecutive_skips counter in poll_loop, structured event push + 5-skip pause logic
- `web_ui/__init__.py` - Package marker (empty)
- `web_ui/main.py` - FastAPI app with /events SSE, GET /fsm, POST /fsm, GET / dashboard stub
- `web_ui/requirements.txt` - fastapi==0.115.12, uvicorn[standard]==0.34.0, python-dotenv==1.2.2

## Decisions Made

- consecutive_skips counter is in-memory (poll_loop scope), not persisted — resets on restart; sufficient for v1 since the 5-skip behavior is a session-level guard, not a persistent counter
- web_ui imports daemon.skip_event_queue directly (in-process) with ImportError fallback to local queue — supports both same-process testing and multi-process docker-compose deployment
- Broadcaster task created on FastAPI startup event; per-client queues have maxsize=100 to shed load from stalled connections

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required for this plan. docker-compose integration in Plan 03-02.

## Known Stubs

- `GET /` in web_ui/main.py returns a placeholder HTML string when `web_ui/templates/index.html` is absent. The template is created in Plan 03-02; this is an intentional stub that will be resolved there.

## Next Phase Readiness

- skip_event_queue is wired and ready for Plan 03-02 to consume via the SSE endpoint
- POST /fsm and GET /fsm are fully functional and can be tested immediately via curl
- web_ui/templates/ directory and docker-compose.yml web_ui service entry are the two remaining pieces (Plan 03-02)

---
*Phase: 03-signal-notifications-interactive-confirmations*
*Completed: 2026-04-02*

## Self-Check: PASSED

- daemon.py: FOUND
- web_ui/__init__.py: FOUND
- web_ui/main.py: FOUND
- web_ui/requirements.txt: FOUND
- 03-01-SUMMARY.md: FOUND
- Commit af3629b: FOUND
- Commit c9b77c4: FOUND
