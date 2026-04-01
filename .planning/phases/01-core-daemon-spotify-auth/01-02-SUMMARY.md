---
phase: 01-core-daemon-spotify-auth
plan: 02
subsystem: infra
tags: [asyncio, spotipy, docker, spotify-api, polling, signal-handling]

# Dependency graph
requires:
  - phase: 01-core-daemon-spotify-auth (plan 01)
    provides: setup_auth.py terminal OAuth, CacheFileHandler token, Dockerfile, docker-compose.yml, .env.example
provides:
  - daemon.py — asyncio poll loop with track-change detection, 429 backoff, SIGTERM shutdown
  - state.json — host-side persistent state file (last_track_id)
affects: [02-content-filtering, 02-skip, phase-2-planning]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - asyncio event loop with stop_event for clean shutdown coordination
    - loop.add_signal_handler (not signal.signal) for SIGTERM/SIGINT — asyncio-safe
    - Interruptible 429 backoff via asyncio.wait_for(asyncio.shield(stop_event.wait()), timeout=wait)
    - state.get("last_track_id") style access — forward-compatible with Phase 2 additions
    - Direct file write for bind-mounted state.json (os.replace fails on bind-mounted files with EBUSY)

key-files:
  created:
    - daemon.py
    - state.json
  modified:
    - Makefile
    - .env.example

key-decisions:
  - "save_state() uses direct write (not atomic rename) — os.replace() raises EBUSY on Docker bind-mounted files on Linux"
  - "SPOTIFY_REDIRECT_URI uses https://127.0.0.1:8080 — Spotify Dashboard requires HTTPS for redirect URIs"
  - "make auth target runs setup_auth.py inside the container — no host Python/pip installation needed"
  - "loop.add_signal_handler used for SIGTERM/SIGINT — asyncio-safe, avoids race conditions with async tasks"

patterns-established:
  - "Poll loop pattern: while not stop_event.is_set() with asyncio.sleep at tail"
  - "Heartbeat pattern: log only when HEARTBEAT_INTERVAL elapsed since last activity, not on every silent poll"
  - "State forward-compatibility: state.get('key') not state['key'] so Phase 2 additions don't break Phase 1 reads"

requirements-completed: [CORE-01, CORE-02, CORE-03, CORE-04]

# Metrics
duration: ~30min (including live Docker verification)
completed: 2026-04-01
---

# Phase 1 Plan 02: Core Daemon & Spotify Auth (Poll Loop) Summary

**Asyncio daemon polling Spotify /me/player/currently-playing every 1s with track-change detection, 429 backoff, and clean SIGTERM shutdown verified live in Docker**

## Performance

- **Duration:** ~30 min
- **Started:** 2026-04-01 (continuation of 01-01)
- **Completed:** 2026-04-01
- **Tasks:** 3 (including human-verify checkpoint)
- **Files modified:** 4

## Accomplishments

- Asyncio poll loop running continuously in Docker with restart:always, detecting track changes within ~2 seconds
- Explicit flag read from Spotify track item on every change (CORE-04)
- 429 rate-limit backoff with Retry-After header extraction and interruptible sleep (does not block SIGTERM during backoff)
- Graceful shutdown on SIGTERM completing in under 1 second — verified live
- state.json persists last_track_id across container restarts and rebuilds
- make auth target eliminates need to install Python/spotipy on the host for the one-time OAuth step

## Task Commits

Each task was committed atomically:

1. **Task 1: state.json — initial state file** - `98dfa78` (chore)
2. **Task 2: daemon.py — asyncio poll loop** - `7044629` (feat)
3. **Post-checkpoint fix: make auth target in Makefile** - `41f7fc9` (fix)
4. **Post-checkpoint fix: https redirect URI in .env.example** - `509d6cb` (fix)
5. **Post-checkpoint fix: direct write in save_state()** - `b8e4b27` (fix)

**Plan metadata:** (docs commit — this summary)

## Files Created/Modified

- `daemon.py` — Asyncio poll loop: track-change detection, 429 backoff, SIGTERM shutdown, heartbeat logging
- `state.json` — Host-side state file (gitignored); pre-created to avoid Docker bind-mount creating a directory
- `Makefile` — Added `make auth` target to run setup_auth.py inside the container
- `.env.example` — Updated SPOTIFY_REDIRECT_URI to use https:// (Spotify Dashboard requirement)

## Decisions Made

- **Direct write for save_state():** The original plan specified an atomic rename via `os.replace()`. During live Docker testing, this failed with `EBUSY` on the bind-mounted `state.json`. Switched to direct write (`open(STATE_PATH, "w")`). Trade-off: a crash mid-write could produce a corrupt state file, but state.json is tiny and the load_state() fallback handles corruption gracefully.
- **https:// redirect URI:** Spotify Developer Dashboard now requires HTTPS for redirect URIs. `.env.example` updated from `http://127.0.0.1:8080` to `https://127.0.0.1:8080`.
- **make auth target:** Running `setup_auth.py` inside the container avoids requiring users to install spotipy and python-dotenv on the host. This is the better DX and aligns with the Docker-first deployment model.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] save_state() atomic rename fails on bind-mounted files**
- **Found during:** Task 3 (checkpoint) — live Docker verification
- **Issue:** `os.replace(tmp_path, STATE_PATH)` raises `OSError: [Errno 16] Device or resource busy` on Linux when the target is a Docker bind-mounted file
- **Fix:** Replaced atomic write-then-rename with direct `open(STATE_PATH, "w")` write; removed `.tmp` path logic
- **Files modified:** `daemon.py`
- **Verification:** `docker compose stop && docker compose up -d` — state.json updated correctly with last_track_id after track change; no EBUSY errors in logs
- **Committed in:** `b8e4b27`

**2. [Rule 2 - Missing Critical] https:// redirect URI required by Spotify Dashboard**
- **Found during:** Task 3 (checkpoint) — OAuth setup step
- **Issue:** `.env.example` had `http://127.0.0.1:8080`; Spotify Developer Dashboard rejects HTTP redirect URIs (requires HTTPS)
- **Fix:** Updated `.env.example` SPOTIFY_REDIRECT_URI to `https://127.0.0.1:8080`
- **Files modified:** `.env.example`
- **Verification:** OAuth flow completed successfully with updated URI
- **Committed in:** `509d6cb`

**3. [Rule 2 - Missing Critical] make auth target for host-free OAuth setup**
- **Found during:** Task 3 (checkpoint) — setup procedure
- **Issue:** Plan's OAuth setup instructions required installing spotipy and python-dotenv on the host machine; this is unnecessary friction and pollutes the host environment
- **Fix:** Added `make auth` target to Makefile that runs `docker compose run --rm -it daemon python setup_auth.py`
- **Files modified:** `Makefile`
- **Verification:** `make auth` successfully ran setup_auth.py inside the container without any host pip install
- **Committed in:** `41f7fc9`

---

**Total deviations:** 3 auto-fixed (1 bug, 2 missing critical)
**Impact on plan:** All three fixes were discovered during live verification and are essential for correct operation. No scope creep.

## Issues Encountered

- `os.replace()` EBUSY on bind-mounted files is a known Linux Docker behavior (not a spotipy or Python issue). The direct-write fallback loses crash-atomicity but is acceptable given state.json's tiny size and resilient load_state() fallback.

## User Setup Required

Users must:
1. Copy `.env.example` to `.env` and fill in `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET`
2. Register `https://127.0.0.1:8080` as a Redirect URI in the Spotify Developer Dashboard
3. Run `make setup` to pre-create `state.json` and `token_cache/`
4. Run `make auth` for the one-time OAuth terminal flow (opens URL to approve on phone)
5. Run `docker compose up -d` — daemon starts automatically and persists across reboots

No further host-side setup required. All subsequent container restarts are headless.

## Next Phase Readiness

- Phase 1 complete. Poll loop is running, track changes detected, explicit flag available per track.
- Phase 2 can attach content-filtering logic directly inside the `if track_id != state.get("last_track_id")` block in `poll_loop()`.
- Phase 2 will need to add `family_safe_mode` and `consecutive_skips` to `state.json` — daemon.py uses `.get()` access throughout so these additions are backward-compatible.
- Blocker for Phase 2: SoCo speaker discovery requires knowing room names — user must provide this before Phase 2 planning.

---
*Phase: 01-core-daemon-spotify-auth*
*Completed: 2026-04-01*
