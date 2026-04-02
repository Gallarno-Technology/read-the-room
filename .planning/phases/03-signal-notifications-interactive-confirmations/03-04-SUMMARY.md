---
phase: 03-signal-notifications-interactive-confirmations
plan: "04"
subsystem: infra
tags: [sse, asyncio, docker-compose, file-ipc, jsonl]

# Dependency graph
requires:
  - phase: 03-signal-notifications-interactive-confirmations
    provides: SSE /events endpoint, daemon skip_event_queue, web_ui dashboard

provides:
  - daemon.py appends JSON lines to data/skip_events.jsonl on every skip and five_skip_warning event
  - web_ui/main.py tails data/skip_events.jsonl via _file_tail() coroutine replacing broken queue import
  - docker-compose.yml mounts ./data:/app/data into both daemon and web_ui containers

affects:
  - any future phase modifying daemon.py skip event handling
  - any future phase modifying web_ui SSE behavior

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "File-based IPC: daemon appends JSON lines, consumer tails file — avoids cross-process queue sharing"
    - "Async file poll: asyncio.sleep(0.25) between readline() attempts — lightweight, no inotify dependency"
    - "Seek-to-end on startup: fh.seek(0, 2) skips history so browser only receives live events"

key-files:
  created: []
  modified:
    - daemon.py
    - web_ui/main.py
    - docker-compose.yml

key-decisions:
  - "File-based IPC (jsonl tail) chosen over message broker or shared memory — simplest fix preserving existing SSE API contract"
  - "250ms poll interval in _file_tail — low latency without busy-loop overhead"
  - "Existing asyncio.Queue put_nowait calls preserved in daemon.py — backward compatibility with single-process test/dev runs"
  - "SKIP_EVENTS_PATH env var in both daemon.py and web_ui/main.py — allows override in tests or alternate deployments"

patterns-established:
  - "Gap-2 fix pattern: file-based IPC for cross-container event sharing without a message broker"
  - "Docker shared volume pattern: ./data bind-mount on both services for simple file sharing"

requirements-completed:
  - FSM-03
  - SIG-01
  - SIG-02
  - SIG-04

# Metrics
duration: 2min
completed: 2026-04-02
---

# Phase 03 Plan 04: File-Based IPC for Cross-Container SSE Events Summary

**daemon.py writes skip events to data/skip_events.jsonl; web_ui tails that file via _file_tail() coroutine, replacing the broken cross-process asyncio.Queue import that silently delivered no events in docker-compose**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-02T10:58:32Z
- **Completed:** 2026-04-02T10:59:55Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- daemon.py now appends JSON lines to data/skip_events.jsonl after every skip event and every five_skip_warning event, with makedirs guard and OSError logging
- web_ui/main.py fully replaces the broken `from daemon import skip_event_queue` try/except block with `_file_tail()` — an asyncio coroutine that waits for the file to exist, seeks to end on startup, and polls every 250ms
- docker-compose.yml gains `./data:/app/data` volume mount on both daemon and web_ui services, enabling the shared file path

## Task Commits

Each task was committed atomically:

1. **Task 1: Add file-based event log writes to daemon.py** - `64d4235` (feat)
2. **Task 2: Replace in-process queue import with file-tail reader in web_ui/main.py and add shared volume to docker-compose.yml** - `2059d37` (feat)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified

- `daemon.py` - Added SKIP_EVENTS_PATH constant, _append_skip_event() helper, and two call sites after skip/five_skip_warning put_nowait blocks
- `web_ui/main.py` - Removed broken daemon import block; added SKIP_EVENTS_PATH constant and _file_tail() coroutine; startup task now calls _file_tail
- `docker-compose.yml` - Added `./data:/app/data` bind-mount to both daemon and web_ui services

## Decisions Made

- File-based IPC (jsonl tail) chosen over message broker or shared memory — simplest fix that preserves existing SSE API contract (/events endpoint, browser EventSource) without requiring Redis or similar
- 250ms poll interval in _file_tail gives sub-second latency without busy-looping
- Existing asyncio.Queue put_nowait calls kept in daemon.py for backward compatibility with single-process dev/test runs
- SKIP_EVENTS_PATH env var exposed in both services to allow path override if needed

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

Before first `docker compose up`, create the data directory on the host:

```bash
mkdir -p data
```

This is required because Docker bind-mounts require the host path to exist. The daemon will create the skip_events.jsonl file inside it automatically on first skip event.

## Next Phase Readiness

- File-based IPC is wired end-to-end: daemon skip -> jsonl append -> web_ui tail -> SSE subscriber queue -> browser EventSource
- The 5-skip warning banner in the browser dashboard will now appear correctly in docker-compose mode
- SSE API contract (/events endpoint, FSM toggle, FSM status routes) fully preserved and unchanged

---
*Phase: 03-signal-notifications-interactive-confirmations*
*Completed: 2026-04-02*
