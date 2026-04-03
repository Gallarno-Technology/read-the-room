---
phase: 08-dashboard-frontend
plan: 01
subsystem: ui
tags: [vanilla-js, sse, html, css, now-playing, eval-badge, skip-button]

# Dependency graph
requires:
  - phase: 07-web-ui-backend
    provides: GET /now-playing hydration endpoint and POST /skip manual skip endpoint
  - phase: 06-daemon-sse-extensions
    provides: track_change and eval_result SSE events with track_id field
provides:
  - Now-playing card HTML with album art, track name, artist, eval badge, skip button
  - Six eval-state badge CSS modifier classes (evaluating, passed, no-lyrics, skipped, paused, fsm-off)
  - JS hydration on DOMContentLoaded from GET /now-playing
  - JS SSE routing for track_change and eval_result events with track_id guard (NOW-07)
  - Skip button with in-flight disable and finally re-enable (SKIP-04)
affects: [08-dashboard-frontend]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "currentTrackId guard: eval_result events only update badge if track_id matches currently displayed track"
    - "SSE reconnect re-hydration: es.onopen calls hydrateNowPlaying() to repopulate card without going blank"
    - "Skip button finally re-enable: skipBtn.disabled reset in finally block to guarantee re-enable on both success and error"

key-files:
  created: []
  modified:
    - web_ui/templates/index.html

key-decisions:
  - "currentTrackId set only from track_change events and hydration — never from eval_result events (NOW-07)"
  - "album_art_url null check is explicit if (data.album_art_url) — img.src never set to null"
  - "No polling — all live updates come exclusively from SSE events"

patterns-established:
  - "Eval badge state machine: EVAL_BADGE_CLASS/EVAL_BADGE_LABEL maps drive setEvalBadge() — single source of truth"
  - "renderTrack/renderIdle helper split: clear separation of idle vs active card rendering state"

requirements-completed: [NOW-01, NOW-02, NOW-03, NOW-04, NOW-05, NOW-06, NOW-07, SKIP-01, SKIP-04]

# Metrics
duration: 2min
completed: 2026-04-03
---

# Phase 8 Plan 01: Now-Playing Card Summary

**Now-playing card with real-time eval-state badge and skip button wired to GET /now-playing hydration and SSE track_change/eval_result events**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-03T12:28:32Z
- **Completed:** 2026-04-03T12:30:52Z
- **Tasks:** 3
- **Files modified:** 1

## Accomplishments
- Inserted now-playing card HTML between FSM toggle and Incident Log cards with all required child elements (album art, name, artist, eval badge, skip button, error div)
- Added six eval-state badge CSS modifier classes matching UI-SPEC color palette (evaluating=amber, passed=green, no-lyrics=grey, skipped=red, paused=amber, fsm-off=faint)
- Wired full JS behavior: DOMContentLoaded hydration, SSE reconnect re-hydration, track_change/eval_result routing with track_id guard, skip button with in-flight disable

## Task Commits

Each task was committed atomically:

1. **Task 1: Insert now-playing card HTML and skip-btn disabled CSS** - `abcfc9c` (feat)
2. **Task 2: Add six eval-state badge CSS modifier classes** - `53b1c48` (feat)
3. **Task 3: Add JS hydration, SSE routing, eval badge state machine, skip handler** - `a4ceebe` (feat)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified
- `web_ui/templates/index.html` - Added now-playing card HTML, six eval badge CSS classes, all JS wiring

## Decisions Made
- currentTrackId set only from track_change events and hydration, never from eval_result — maintains NOW-07 guard integrity
- album_art_url null check is `if (data.album_art_url)` (not `!== null`) — prevents setting img.src to "null" string
- No polling added — all live updates exclusively from SSE events per D-05 constraint

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Two pre-existing test failures in `tests/test_skip_client.py` (test_soco_pause_uses_cached_ip, test_soco_pause_falls_back_to_discovery_when_not_cached) confirmed to exist before Phase 08 changes — not caused by this plan. Phase 08 only modifies HTML with no Python changes.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- v1.2 Now Playing Status milestone complete: dashboard shows current track with real-time eval state and manual skip button
- All NOW-01 through NOW-07 and SKIP-01/SKIP-04 requirements fulfilled
- Ready for v1.3 drug and sexual reference detection (Phase 09+)

---
*Phase: 08-dashboard-frontend*
*Completed: 2026-04-03*
