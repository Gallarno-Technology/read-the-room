---
phase: 06-daemon-sse-extensions
plan: 02
subsystem: daemon
tags: [python, file-ipc, events, jsonl, rename, constants]

# Dependency graph
requires:
  - phase: 06-01
    provides: Test scaffold with EVENTS_PATH and NOW_PLAYING_PATH references (xfail stubs)
provides:
  - EVENTS_PATH constant in daemon.py (default: data/events.jsonl)
  - NOW_PLAYING_PATH constant in daemon.py (derived from EVENTS_PATH directory)
  - _append_event() function replacing _append_skip_event()
  - EVENTS_PATH constant in web_ui/main.py (default: data/events.jsonl)
  - docker-compose.yml volume comments updated to reflect Phase 6 scope
affects:
  - 06-03 (event emission: track_change, eval_result)
  - 06-04 (now_playing.json write via NOW_PLAYING_PATH)

# Tech tracking
tech-stack:
  added: [import datetime added to daemon.py]
  patterns: [hard rename with no backwards-compat alias (D-01 decision)]

key-files:
  created: []
  modified:
    - daemon.py
    - web_ui/main.py
    - docker-compose.yml

key-decisions:
  - "Hard rename SKIP_EVENTS_PATH → EVENTS_PATH per D-01 — no backwards-compat alias"
  - "NOW_PLAYING_PATH derived as os.path.join(dirname(EVENTS_PATH), 'now_playing.json') so both paths share the same data/ directory"
  - "import datetime added now to avoid second pass in Plan 04 for now_playing.json ISO timestamps"
  - "docker-compose.yml had no explicit SKIP_EVENTS_PATH env block — only volume comments updated"

patterns-established:
  - "All daemon file-based IPC uses EVENTS_PATH; _append_event() is the single write point"

requirements-completed: [DAEM-01, DAEM-02, DAEM-03]

# Metrics
duration: 5min
completed: 2026-04-03
---

# Phase 06 Plan 02: Env-var Migration Summary

**Hard rename of SKIP_EVENTS_PATH to EVENTS_PATH across daemon.py, web_ui/main.py, and docker-compose.yml, adding NOW_PLAYING_PATH constant and datetime import in preparation for Plans 03 and 04**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-04-03T10:30:00Z
- **Completed:** 2026-04-03T10:35:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Renamed `SKIP_EVENTS_PATH` → `EVENTS_PATH` (default `data/events.jsonl`) in daemon.py and web_ui/main.py
- Renamed `_append_skip_event()` → `_append_event()` with updated docstring covering all event types
- Added `NOW_PLAYING_PATH` constant derived from `EVENTS_PATH` directory (needed in Plan 04)
- Added `import datetime` to daemon.py (needed for ISO timestamps in Plan 04)
- Updated all 2 call sites in daemon.py poll_loop and all 3 call sites in web_ui `_file_tail()`
- Updated docker-compose.yml volume comments to reflect Phase 6 scope

## Task Commits

Each task was committed atomically:

1. **Task 1: Rename SKIP_EVENTS_PATH → EVENTS_PATH in daemon.py and add NOW_PLAYING_PATH** - `db1c7bb` (feat)
2. **Task 2: Rename SKIP_EVENTS_PATH → EVENTS_PATH in web_ui/main.py and docker-compose.yml** - `8be0447` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `daemon.py` - EVENTS_PATH constant, NOW_PLAYING_PATH constant, _append_event() function, datetime import, 2 call sites updated
- `web_ui/main.py` - EVENTS_PATH constant, 3 call sites in _file_tail() updated
- `docker-compose.yml` - Volume comments updated for both daemon and web_ui service sections

## Decisions Made

- Hard rename with no backwards-compat alias (D-01) — if `.env` contains `SKIP_EVENTS_PATH`, user must rename it to `EVENTS_PATH=data/events.jsonl` before restarting containers
- `NOW_PLAYING_PATH` derives its directory from `EVENTS_PATH` so both paths always share the same bind-mount directory
- `import datetime` added proactively to avoid a second mechanical pass in Plan 04

## Deviations from Plan

None — plan executed exactly as written.

The plan mentioned "4 call sites" of `_append_skip_event` but the actual file had 2 (one for five_skip_warning, one for skip events). Both were correctly renamed. The plan's count appears to have double-counted the `skip_event_queue.put_nowait()` calls which are separate (not renamed per plan instructions).

## Issues Encountered

`test_existing_events_unaffected` remains xfail after rename because the test fails on `Path('/app/.healthcheck').touch()` — the `/app/` directory doesn't exist in the test environment. This is a pre-existing condition affecting all `test_daemon_events.py` tests; the xfail marker with `strict=False` correctly captures this state. The tests will be addressable in Plans 03/04 when the healthcheck path is mocked.

## User Setup Required

**Important:** If your `.env` file contains `SKIP_EVENTS_PATH=data/skip_events.jsonl`, rename it to:
```
EVENTS_PATH=data/events.jsonl
```
Then restart containers: `docker compose restart`

The default value changed from `data/skip_events.jsonl` to `data/events.jsonl`. Existing data in the old file will NOT be read from the new path — this is intentional (history is not migrated).

## Next Phase Readiness

- Plan 03 (event emission) can now use `EVENTS_PATH` and `_append_event()` directly
- Plan 04 (now_playing.json) can use `NOW_PLAYING_PATH` and `datetime` immediately
- No blockers; rename unblocks both plans

---
*Phase: 06-daemon-sse-extensions*
*Completed: 2026-04-03*
