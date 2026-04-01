---
phase: 01-core-daemon-spotify-auth
plan: "01"
subsystem: infra
tags: [spotipy, docker, python, oauth, dotenv]

# Dependency graph
requires: []
provides:
  - OAuth setup script (setup_auth.py) for one-time headless token acquisition
  - requirements.txt with pinned spotipy==2.26.0 and python-dotenv==1.2.2
  - .env.example config template with all 7 required env vars
  - Dockerfile with exec-form CMD (Python as PID 1 for clean SIGTERM)
  - docker-compose.yml with restart:always, network_mode:host, and bind mounts
  - Makefile setup target to pre-create required host-side files
  - .gitignore excluding .env, state.json, and token_cache/
affects:
  - 01-02-daemon (consumes Dockerfile, docker-compose.yml, token_cache/ mount)

# Tech tracking
tech-stack:
  added: [spotipy==2.26.0, python-dotenv==1.2.2, python:3.12-slim]
  patterns:
    - CacheFileHandler pattern for token persistence across container restarts
    - exec-form Dockerfile CMD for SIGTERM propagation to Python PID 1
    - env_file directive in docker-compose (no secrets in compose file)
    - bind mounts for host-persisted state (token_cache/, state.json)

key-files:
  created:
    - setup_auth.py
    - requirements.txt
    - .env.example
    - Dockerfile
    - docker-compose.yml
    - Makefile
    - .gitignore
  modified: []

key-decisions:
  - "open_browser=False in SpotifyOAuth — never auto-opens browser on headless server"
  - "SPOTIFY_REDIRECT_URI=http://127.0.0.1:8080 (not localhost — banned Nov 2025)"
  - "python:3.12-slim base image (not 3.14 — not available as stable Docker Hub image April 2026)"
  - "exec-form CMD [python daemon.py] so Python is PID 1 and receives SIGTERM without /bin/sh wrapper"
  - "network_mode:host required for SoCo UPnP/multicast to Sonos speakers (Phase 2)"

patterns-established:
  - "Pattern 1: CacheFileHandler(cache_path=os.environ['SPOTIFY_CACHE_PATH']) — always use env var for cache path, never hardcode"
  - "Pattern 2: validate env vars at startup with explicit list + sys.exit(1) on missing"
  - "Pattern 3: exec-form CMD in Dockerfile for all Python daemon containers"

requirements-completed: [CORE-02, CORE-03]

# Metrics
duration: 2min
completed: "2026-04-01"
---

# Phase 01 Plan 01: Project Foundation Summary

**SpotifyOAuth headless setup script with CacheFileHandler token persistence, pinned spotipy/dotenv deps, exec-form Dockerfile, and docker-compose with restart:always and host-bind mounts**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-01T14:53:04Z
- **Completed:** 2026-04-01T14:54:58Z
- **Tasks:** 3
- **Files modified:** 7

## Accomplishments
- setup_auth.py implements full headless OAuth flow: prints auth URL, prompts for redirect response, exchanges code, saves token to CacheFileHandler, validates with sp.current_user()
- Project scaffold: requirements.txt pins exact versions, .env.example documents all 7 required env vars, .gitignore excludes all secrets and runtime state
- Docker infrastructure: exec-form CMD ensures SIGTERM reaches Python directly; docker-compose.yml has restart:always, network_mode:host, env_file:.env, and bind mounts persisting both token_cache/ and state.json across rebuilds

## Task Commits

Each task was committed atomically:

1. **Task 1: Project scaffold — requirements, .env template, .gitignore** - `cfd1d5e` (chore)
2. **Task 2: setup_auth.py — terminal OAuth flow with token validation** - `15f4b81` (feat)
3. **Task 3: Dockerfile and docker-compose.yml — exec-form CMD, restart:always, bind mounts** - `ad44355` (feat)

## Files Created/Modified
- `setup_auth.py` — one-time OAuth setup script; run on server SSH session before first daemon start
- `requirements.txt` — pinned spotipy==2.26.0 and python-dotenv==1.2.2
- `.env.example` — committed template with all 7 env vars and comments; user copies to .env
- `Dockerfile` — python:3.12-slim, exec-form CMD ["python", "daemon.py"]
- `docker-compose.yml` — restart:always, network_mode:host, env_file:.env, bind mounts for state.json and token_cache/
- `Makefile` — setup/up/down/logs targets; setup pre-creates host-side state.json and token_cache/
- `.gitignore` — excludes .env, state.json, token_cache/, __pycache__/, .venv/

## Decisions Made
- Used open_browser=False in SpotifyOAuth — headless server cannot open a browser; user opens URL on phone
- SPOTIFY_REDIRECT_URI=http://127.0.0.1:8080 (not localhost — Spotify banned localhost redirects Nov 2025)
- python:3.12-slim base image chosen over 3.14 (not yet available as stable Docker Hub image as of April 2026)
- exec-form CMD ["python", "daemon.py"] ensures Python is PID 1 and receives SIGTERM directly; shell-form would wrap in /bin/sh causing 10-second forced kill on docker compose stop

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required

Before running `python setup_auth.py`, the user must:

1. Create a Spotify app at https://developer.spotify.com/dashboard
2. Add redirect URI: `http://127.0.0.1:8080` in Dashboard -> Your App -> Settings -> Redirect URIs
3. Copy `.env.example` to `.env` and fill in `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET`
4. Run `make setup` to pre-create `state.json` and `token_cache/` on the host
5. Run `python setup_auth.py` to complete OAuth and save token

Note: Spotify Premium required on the app-owner account (Development Mode restriction as of March 9, 2026).

## Next Phase Readiness

- All infrastructure files are in place for Plan 01-02 (daemon.py implementation)
- docker-compose.yml, Dockerfile, and bind mounts are ready to run `docker compose up -d` once daemon.py is written
- token_cache/ mount path matches SPOTIFY_CACHE_PATH=/app/token_cache/.cache in .env.example
- No blockers for Plan 01-02

---
*Phase: 01-core-daemon-spotify-auth*
*Completed: 2026-04-01*

## Self-Check: PASSED

All 7 created files verified present on disk. All 3 task commits verified in git history (cfd1d5e, 15f4b81, ad44355).
