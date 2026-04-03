---
phase: 07-web-ui-backend
plan: 02
subsystem: api
tags: [spotipy, fastapi, pytest, tdd, spotify-api]

# Dependency graph
requires:
  - phase: 07-01
    provides: 4 failing TDD stubs for /now-playing and /skip; spotipy in web_ui requirements.txt; token_cache volume mount
  - phase: 06-daemon-sse-extensions
    provides: now_playing.json written by daemon; EVENTS_PATH/data volume established
provides:
  - GET /now-playing endpoint returning verbatim now_playing.json or {"status":"idle"} when absent
  - POST /skip endpoint calling sp.next_track() and returning {"ok":true} or HTTP 503 on error
  - spotipy module-level singleton initialized via shared CacheFileHandler (D-07)
  - NOW_PLAYING_PATH constant derived from dirname(EVENTS_PATH)
affects:
  - 08-frontend (Phase 8 frontend consumes GET /now-playing for hydration and POST /skip for manual skip button)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "JSONResponse(status_code=503, content={...}) for structured error responses — avoids HTTPException double-wrapping the detail key"
    - "Module-level sp = _sp_init() singleton; graceful None on missing env vars with warning log (D-10)"
    - "NOW_PLAYING_PATH derived from dirname(EVENTS_PATH) so both share same data/ bind-mount directory"

key-files:
  created: []
  modified:
    - web_ui/main.py

key-decisions:
  - "Used JSONResponse(status_code=503) instead of HTTPException for /skip errors — HTTPException wraps dict in an outer detail key, breaking test assertions that check body[detail] directly"
  - "SKIP-03 satisfied architecturally: consecutive_skips is daemon in-memory only; web_ui never touches it"

patterns-established:
  - "Direct JSONResponse with status_code for 5xx errors when response body must be a flat dict"

requirements-completed: [SKIP-02, SKIP-03]

# Metrics
duration: 2min
completed: 2026-04-03
---

# Phase 07 Plan 02: Web UI Backend Endpoints Summary

**GET /now-playing and POST /skip implemented in web_ui/main.py using shared spotipy token cache; all 4 TDD tests pass**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-04-03T11:21:22Z
- **Completed:** 2026-04-03T11:22:45Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- Added spotipy imports, `NOW_PLAYING_PATH` constant, and module-level `sp = _sp_init()` singleton to `web_ui/main.py`
- `_sp_init()` uses `CacheFileHandler` with `SPOTIFY_CACHE_PATH` env var — identical auth pattern to daemon (D-07); logs warning and returns None if env vars absent (D-10)
- Implemented `GET /now-playing` reading `now_playing.json` verbatim or returning `{"status": "idle"}` when absent (D-02, D-03)
- Implemented `POST /skip` calling `sp.next_track()` returning `{"ok": true}`; returns HTTP 503 with `{"detail": "skip_failed", "reason": "..."}` on SpotifyException (D-04, D-05)
- All 4 tests in `tests/test_web_ui_endpoints.py` pass (test_now_playing_idle, test_now_playing_returns_file_contents, test_skip_success, test_skip_spotify_error_returns_503)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add spotipy imports, NOW_PLAYING_PATH constant, and sp singleton** - `f6a01ad` (feat)
2. **Task 2: Implement GET /now-playing and POST /skip endpoints** - `6b2c8dd` (feat)

**Plan metadata:** (docs commit to follow)

## Files Created/Modified

- `web_ui/main.py` — Added spotipy imports, NOW_PLAYING_PATH, _sp_init(), sp singleton, GET /now-playing, POST /skip; updated module docstring

## Decisions Made

- Used `JSONResponse(status_code=503, content={...})` instead of `HTTPException(status_code=503, detail={...})` for the skip failure response. FastAPI wraps the HTTPException detail in `{"detail": <value>}`, so if the detail is already a dict like `{"detail": "skip_failed", "reason": "..."}`, the response would be `{"detail": {"detail": "skip_failed", "reason": "..."}}` — failing the test assertions that check `body["detail"] == "skip_failed"` directly.

## Deviations from Plan

None — plan executed exactly as written, with one intentional deviation in error handling approach (JSONResponse vs HTTPException) necessitated by the test contract.

### Intentional Implementation Choice

**HTTPException vs JSONResponse for 503 errors**
- **Found during:** Task 2 analysis before coding
- **Issue:** Plan's code sample used `HTTPException(status_code=503, detail={"detail": "skip_failed", "reason": ...})` but the test asserts `body["detail"] == "skip_failed"` (flat dict at top level). HTTPException wraps the dict in another `detail` key.
- **Fix:** Used `JSONResponse(status_code=503, content={"detail": "skip_failed", "reason": str(exc)})` to produce the flat structure the tests require.
- **Classification:** Correct implementation per test contract — not a deviation from intent, only from the sample code in the plan.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required beyond what was set up in Phase 07 Plan 01 (token_cache volume already added to docker-compose.yml).

## Known Stubs

None — both endpoints are fully wired to real data sources (now_playing.json and Spotify API).

## Next Phase Readiness

- Phase 8 (frontend) can now call `GET /now-playing` for page-load hydration and `POST /skip` for the manual skip button
- SKIP-02 and SKIP-03 requirements are complete: manual skip works via Spotify API without touching the daemon's consecutive-skip counter
- Docker build will install spotipy (added in Plan 01); token_cache volume is shared with daemon service

## Self-Check: PASSED

- SUMMARY.md exists at `.planning/phases/07-web-ui-backend/07-02-SUMMARY.md`
- `web_ui/main.py` exists with all required patterns
- Task 1 commit `f6a01ad` present in git log
- Task 2 commit `6b2c8dd` present in git log
- All 4 tests pass: `pytest tests/test_web_ui_endpoints.py` 4 passed

---
*Phase: 07-web-ui-backend*
*Completed: 2026-04-03*
