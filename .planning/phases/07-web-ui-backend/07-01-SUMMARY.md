---
phase: 07-web-ui-backend
plan: 01
subsystem: testing, infra
tags: [spotipy, fastapi, pytest, docker-compose, tdd]

# Dependency graph
requires:
  - phase: 06-daemon-sse-extensions
    provides: now_playing.json written by daemon; EVENTS_PATH/data volume established
provides:
  - spotipy dependency available in web_ui container at build time
  - token_cache volume shared between daemon and web_ui services
  - 4 failing TDD test stubs for /now-playing and /skip endpoints (Plan 02 target)
affects:
  - 07-02 (implements NOW_PLAYING_PATH, sp, GET /now-playing, POST /skip to make tests pass)

# Tech tracking
tech-stack:
  added: [spotipy==2.26.0 in web_ui/requirements.txt, fastapi+httpx in dev venv for testing]
  patterns: [TDD scaffold — tests written before implementation; monkeypatch for module-level constants]

key-files:
  created: [tests/test_web_ui_endpoints.py]
  modified: [web_ui/requirements.txt, docker-compose.yml]

key-decisions:
  - "spotipy pinned at 2.26.0 in web_ui to match daemon version exactly (plan guessed 2.25.1)"
  - "fastapi+httpx installed into project venv to enable pytest collection of TestClient-based tests"

patterns-established:
  - "TestClient fixture with patch.object on module-level sp attribute (mirrors daemon monkeypatch pattern)"
  - "now_playing_path fixture uses monkeypatch.setattr on NOW_PLAYING_PATH for isolation"

requirements-completed: [SKIP-02, SKIP-03]

# Metrics
duration: 2min
completed: 2026-04-03
---

# Phase 07 Plan 01: Web UI Backend Infrastructure Summary

**spotipy added to web_ui container and token_cache volume shared with daemon; 4 failing TDD stubs for /now-playing and /skip ready for Plan 02**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-04-03T11:18:14Z
- **Completed:** 2026-04-03T11:19:40Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Added `spotipy==2.26.0` to `web_ui/requirements.txt` (matches daemon version exactly)
- Added `./token_cache:/app/token_cache` bind mount to web_ui service in `docker-compose.yml` so the OAuth token is reachable inside the container
- Created `tests/test_web_ui_endpoints.py` with 4 failing TDD stubs covering the two new endpoints — all 4 collect successfully and fail with AttributeError (NOW_PLAYING_PATH and sp missing, as intended)

## Task Commits

1. **Task 1: Add spotipy to web_ui/requirements.txt and token_cache volume** - `c2b6621` (chore)
2. **Task 2: Write failing test scaffold for /now-playing and /skip** - `6f9b6d7` (test)

**Plan metadata:** (docs commit to follow)

## Files Created/Modified

- `web_ui/requirements.txt` - Added spotipy==2.26.0
- `docker-compose.yml` - Added token_cache volume mount to web_ui service
- `tests/test_web_ui_endpoints.py` - 4 failing TDD stubs: test_now_playing_idle, test_now_playing_returns_file_contents, test_skip_success, test_skip_spotify_error_returns_503

## Decisions Made

- Used `spotipy==2.26.0` instead of `2.25.1` (plan's guess) — matched exact version from root `requirements.txt`
- Installed fastapi and httpx into the project dev venv (Rule 3: blocking issue) because the existing venv only had daemon dependencies, preventing pytest from collecting TestClient-based tests

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Installed fastapi+httpx into project venv for test collection**
- **Found during:** Task 2 (writing test scaffold)
- **Issue:** Project venv had daemon packages only (spotipy, soco, etc.); `from fastapi.testclient import TestClient` failed with ModuleNotFoundError, blocking test collection
- **Fix:** Ran `.venv/bin/pip install "fastapi==0.115.12" "httpx>=0.27" "starlette"` — pinned fastapi version to match web_ui's requirements.txt
- **Files modified:** venv only (not tracked in git)
- **Verification:** `pytest --collect-only` collected all 4 tests without import errors
- **Committed in:** N/A (venv not committed; fix is a local dev environment setup step)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Required for plan acceptance criteria (test collection). No scope creep.

## Issues Encountered

- Plan guessed spotipy version as 2.25.1 — actual version in root requirements.txt is 2.26.0. Used actual version to meet acceptance criteria ("versions must match").

## Known Stubs

None — this plan intentionally creates failing tests. The test file itself is the scaffold; stubs are resolved in Plan 02.

## Next Phase Readiness

- Plan 02 can immediately implement `NOW_PLAYING_PATH`, `sp` (spotipy client), `GET /now-playing`, and `POST /skip` in `web_ui/main.py` — all 4 tests will pass when those are added
- Docker build for web_ui will install spotipy at build time
- Token cache is accessible at `/app/token_cache` inside the web_ui container

---
*Phase: 07-web-ui-backend*
*Completed: 2026-04-03*
