---
phase: 02-content-filtering-auto-skip
plan: "04"
subsystem: lyrics
tags: [lrclib, asyncio, logging, sqlite, docker]

# Dependency graph
requires:
  - phase: 02-02
    provides: LyricsService with LRCLIB fetch and SQLite cache

provides:
  - LRCLIB exception handler with bound exc, exc_info=True, and asyncio.wait_for 10s timeout
  - content_checker.py no_lyrics_service path logs at WARNING not INFO
  - Makefile setup target pre-creates lyrics_cache.db (already present, confirmed)

affects: [02-content-filtering-auto-skip, lyrics_service, content_checker]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "asyncio.wait_for wrapping run_in_executor for synchronous library calls with timeout"
    - "Exception binding with 'as exc' + exc_info=True for full traceback visibility in logs"

key-files:
  created: []
  modified:
    - lyrics_service.py
    - content_checker.py

key-decisions:
  - "asyncio.TimeoutError is a subclass of Exception — no separate except clause needed for timeout; caught by existing handler"
  - "Makefile already contained 'touch lyrics_cache.db' in setup target — no change required"

patterns-established:
  - "LRCLIB failures: log at WARNING with %s exc placeholder and exc_info=True"
  - "run_in_executor for sync libs: always wrap with asyncio.wait_for(timeout=10)"

requirements-completed: [FILT-02, FILT-03, FILT-04, FILT-05, FILT-06]

# Metrics
duration: 1min
completed: 2026-04-01
---

# Phase 02 Plan 04: LRCLIB Error Visibility and Timeout Summary

**LRCLIB exception binding (as exc + exc_info=True) and asyncio.wait_for 10s timeout added; no_lyrics_service log upgraded from INFO to WARNING**

## Performance

- **Duration:** ~1 min
- **Started:** 2026-04-01T23:01:14Z
- **Completed:** 2026-04-01T23:02:17Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Bound exception variable in LRCLIB except clause (`as exc`) so the error type and message are captured instead of silently discarded
- Added `exc_info=True` to `log.warning` for full traceback visibility in Docker logs
- Wrapped `run_in_executor` with `asyncio.wait_for(timeout=10)` to cancel stalling LRCLIB connections after 10 seconds (treated as lyrics unavailable per FILT-05)
- Changed `log.info` to `log.warning` in the `no_lyrics_service` fallback path in `content_checker.py` so operators see a visible warning when the lyrics pipeline is not active
- Confirmed Makefile `setup` target already contains `touch lyrics_cache.db` — no change needed

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix LRCLIB exception handler — bind exc, add exc_info, add 10s timeout** - `366d62c` (fix)
2. **Task 2: Upgrade no_lyrics_service log to WARNING and verify Makefile** - `bd38228` (fix)

## Files Created/Modified

- `lyrics_service.py` - Exception binding, exc_info=True, asyncio.wait_for(timeout=10) in get_lyrics()
- `content_checker.py` - no_lyrics_service fallback: log.info -> log.warning with actionable message

## Decisions Made

- `asyncio.TimeoutError` is a subclass of `Exception` — no additional except clause needed for timeout handling; caught by existing `except (NotFoundError, APIError, Exception) as exc:` handler
- Makefile already had `touch lyrics_cache.db` in the setup target — confirmed correct, no modification required

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- `from lyrics_service import LyricsService` fails on host Python (no `aiosqlite` installed) — this is expected; service runs in Docker. Verification performed via AST parse and source-text inspection instead of live import.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- LRCLIB error visibility now operator-visible in Docker logs with full exception detail
- Stalling LRCLIB connections no longer hang the executor thread pool
- Lyrics pipeline inactivity now produces WARNING-level logs visible in monitoring
- All content filtering correctness requirements for FILT-02 through FILT-06 addressed
- Phase 02 is now complete — Phase 03 (Signal notifications) can proceed

## Self-Check: PASSED

- lyrics_service.py: FOUND
- content_checker.py: FOUND
- 02-04-SUMMARY.md: FOUND
- Commit 366d62c: FOUND
- Commit bd38228: FOUND

---
*Phase: 02-content-filtering-auto-skip*
*Completed: 2026-04-01*
