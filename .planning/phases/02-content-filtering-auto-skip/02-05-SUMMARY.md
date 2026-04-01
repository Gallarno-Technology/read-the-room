---
phase: 02-content-filtering-auto-skip
plan: "05"
subsystem: infra
tags: [docker, makefile, spotipy, sqlite, sonos]

# Dependency graph
requires:
  - phase: 02-04
    provides: LRCLIB error visibility, timeout handling, and no_lyrics_service WARNING log
provides:
  - docker-compose.yml daemon service runs as host UID:GID so bind-mount files are user-owned
  - Makefile setup target defensively removes root-owned lyrics_cache.db before touch
  - daemon.py poll loop calls sp.current_playback() returning full playback context with device object
affects: [sonos-detection, sqlite-ownership, uAT-tests]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Docker user directive pattern: pass host UID:GID via shell environment variable expansion"
    - "Idempotent setup pattern: conditional sudo rm before touch handles root-owned bind-mount files"

key-files:
  created: []
  modified:
    - docker-compose.yml
    - Makefile
    - daemon.py

key-decisions:
  - "docker-compose.yml user directive uses ${UID}:${GID} from shell environment — no .env entry needed, Docker Compose expands at 'docker compose up' time"
  - "Makefile setup uses conditional guard [ ! -f lyrics_cache.db ] || sudo rm -f lyrics_cache.db — only invokes sudo when file actually exists"
  - "sp.current_playback() chosen over sp.currently_playing() because GET /me/player returns full device context including is_restricted; GET /me/player/currently-playing omits device object entirely"

patterns-established:
  - "Gap closure pattern: verify root cause before patching — two distinct bugs (file ownership, wrong endpoint) required three targeted one-line fixes"

requirements-completed:
  - FILT-02
  - FILT-03
  - FILT-04
  - FILT-05
  - FILT-06
  - SKIP-02
  - SKIP-03

# Metrics
duration: 1min
completed: 2026-04-01
---

# Phase 02 Plan 05: Gap Closure — Docker Ownership and Sonos Detection Fixes Summary

**Three targeted one-line fixes closing two root-cause bugs: Docker bind-mount file ownership (SQLite OperationalError) and wrong Spotify endpoint (Sonos is_restricted always False)**

## Performance

- **Duration:** 1 min
- **Started:** 2026-04-01T23:35:07Z
- **Completed:** 2026-04-01T23:36:40Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- Docker daemon service now runs as host UID:GID — lyrics_cache.db and state.json will be host-user-owned on first creation, eliminating sqlite3.OperationalError on track change
- make setup now idempotently removes a root-owned lyrics_cache.db with sudo before touch — unblocks UAT Tests 1, 2, 6–10
- daemon.py poll loop calls sp.current_playback() instead of sp.currently_playing() — device object now present in every response, enabling is_restricted=True detection for Sonos and proper SocoSkipClient routing (unblocks UAT Test 5)

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix Docker file ownership** - `cdc7162` (fix)
2. **Task 2: Fix make setup** - `4061013` (fix)
3. **Task 3: Fix Sonos detection** - `ce87a49` (fix)

## Files Created/Modified

- `docker-compose.yml` - Added `user: "${UID}:${GID}"` to daemon service after env_file line
- `Makefile` - Added `@[ ! -f lyrics_cache.db ] || sudo rm -f lyrics_cache.db` before `touch lyrics_cache.db` in setup target
- `daemon.py` - Changed `sp.currently_playing()` to `sp.current_playback()` on line 105

## Decisions Made

- Docker Compose user directive uses shell environment variable expansion (`${UID}:${GID}`) at `docker compose up` time — no .env entry needed, avoids confusion with app credentials
- Makefile conditional guard `[ ! -f lyrics_cache.db ] ||` ensures sudo is only invoked when the file actually exists — safe, idempotent, targeted
- `sp.current_playback()` maps to `GET /me/player` which returns the full playback object including `device.is_restricted`; `sp.currently_playing()` maps to `GET /me/player/currently-playing` which omits `device` entirely — the `item` key is present in both, so all downstream track-detection logic is unaffected by this swap

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None — all three fixes were clean one-line changes, each verified immediately with grep.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All 8 previously blocked UAT tests should now be unblockable (Tests 1, 2, 5–10)
- Phase 02 content-filtering-auto-skip is complete; Phase 03 (Signal notifications) can begin
- No new blockers introduced

---
*Phase: 02-content-filtering-auto-skip*
*Completed: 2026-04-01*
