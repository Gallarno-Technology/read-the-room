---
phase: 01-core-daemon-spotify-auth
verified: 2026-04-01T16:00:00Z
status: passed
score: 4/4 must-haves verified
re_verification: false
---

# Phase 1: Core Daemon & Spotify Auth Verification Report

**Phase Goal:** A daemon runs continuously on the home server (Proxmox/Arch Linux Docker), authenticates with Spotify via terminal OAuth, and correctly detects the currently playing track every ~1 second
**Verified:** 2026-04-01
**Status:** PASSED
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (from ROADMAP.md Success Criteria)

| #  | Truth                                                                                                                    | Status     | Evidence                                                                                                     |
|----|--------------------------------------------------------------------------------------------------------------------------|------------|--------------------------------------------------------------------------------------------------------------|
| 1  | `docker compose up -d` starts the daemon; logs show track name + artist + explicit flag within ~1s of a track change     | VERIFIED   | daemon.py poll_loop logs "Track change: %s — %s (explicit=%s)"; asyncio.sleep(POLL_INTERVAL) with default 1s |
| 2  | After one-time `python setup_auth.py` OAuth step, daemon restarts headlessly with no browser or re-auth required         | VERIFIED   | CacheFileHandler persists token to token_cache/.cache; token_cache/.cache exists on disk (509 bytes, owned by container root — confirms live run) |
| 3  | `docker compose stop` stops daemon within 1-2s (SIGTERM via exec-form CMD); `docker compose up -d` resumes automatically | VERIFIED   | Dockerfile uses exec-form `CMD ["python", "daemon.py"]`; loop.add_signal_handler(SIGTERM, stop_event.set); restart:always in docker-compose.yml |
| 4  | `state.json` persists last track ID across container restarts and rebuilds                                               | VERIFIED   | state.json on disk contains `{"last_track_id": "11ZulcYY4lowvcQm4oe3VJ"}` — real track ID from live run; save_state()/load_state() wired to STATE_PATH bind mount |

**Score:** 4/4 truths verified

---

### Required Artifacts

| Artifact            | Expected                                               | Status     | Details                                                                    |
|---------------------|--------------------------------------------------------|------------|----------------------------------------------------------------------------|
| `daemon.py`         | Asyncio poll loop with track detection, 429 backoff, SIGTERM shutdown | VERIFIED | 188 lines; all key patterns present; syntax OK                         |
| `setup_auth.py`     | One-time terminal OAuth setup                          | VERIFIED   | 80 lines; open_browser=False, CacheFileHandler, get_authorize_url, parse_response_code, current_user() validation |
| `requirements.txt`  | Pinned Python dependencies                             | VERIFIED   | spotipy==2.26.0 and python-dotenv==1.2.2 — exact pins present             |
| `.env.example`      | Config template committed to git                       | VERIFIED   | All 7 vars present: SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REDIRECT_URI, SPOTIFY_CACHE_PATH, POLL_INTERVAL_SECONDS, HEARTBEAT_INTERVAL_SECONDS, STATE_PATH |
| `Dockerfile`        | Python container image                                 | VERIFIED   | FROM python:3.12-slim; CMD ["python", "daemon.py"] exec-form              |
| `docker-compose.yml`| Service orchestration with restart policy              | VERIFIED   | restart:always, network_mode:host, env_file:.env, both bind mounts present |
| `state.json`        | Minimal runtime state file                             | VERIFIED   | Valid JSON; last_track_id contains real track ID "11ZulcYY4lowvcQm4oe3VJ" (not null — confirms live run) |
| `Makefile`          | Setup/auth/up/down/logs targets                        | VERIFIED   | setup and auth targets present; auth runs setup_auth.py inside container  |
| `.gitignore`        | Excludes .env, state.json, token_cache/                | VERIFIED   | All three patterns present with exact matches                              |

---

### Key Link Verification

| From                | To                            | Via                                        | Status  | Details                                                                 |
|---------------------|-------------------------------|---------------------------------------------|---------|-------------------------------------------------------------------------|
| `setup_auth.py`     | `token_cache/`                | `CacheFileHandler(cache_path=SPOTIFY_CACHE_PATH)` | WIRED   | Pattern verified in setup_auth.py line 40                              |
| `daemon.py`         | `token_cache/`                | `CacheFileHandler(cache_path=SPOTIFY_CACHE_PATH)` | WIRED   | Pattern verified in daemon.py line 164                                 |
| `docker-compose.yml`| `token_cache/`                | bind mount volumes                          | WIRED   | `./token_cache:/app/token_cache` on line 11                            |
| `docker-compose.yml`| `.env`                        | `env_file: .env` directive                  | WIRED   | Line 6 of docker-compose.yml                                           |
| `daemon.py`         | Spotify API `/me/player/currently-playing` | `sp.currently_playing()` in poll_loop | WIRED | Line 88; result used on lines 90, 98                                  |
| `daemon.py`         | `state.json`                  | `load_state()` / `save_state()` on track change | WIRED | load_state() line 77; save_state() called after track_id update line 111 |
| `daemon.py`         | asyncio signal handlers       | `loop.add_signal_handler(signal.SIGTERM, stop_event.set)` | WIRED | Lines 179-180; stop_event checked in poll_loop line 86 |

---

### Data-Flow Trace (Level 4)

| Artifact    | Data Variable     | Source                               | Produces Real Data | Status   |
|-------------|-------------------|--------------------------------------|-------------------|----------|
| `daemon.py` | `result`          | `sp.currently_playing()` — Spotify API call | Yes (confirmed: token_cache/.cache exists at 509 bytes, state.json has real track ID) | FLOWING |
| `daemon.py` | `track["explicit"]` | `result["item"]["explicit"]` from Spotify API response | Yes — read directly from API payload | FLOWING |
| `daemon.py` | `state["last_track_id"]` | `load_state()` reads `state.json`; `save_state()` writes after each track change | Yes — state.json contains real track ID on disk | FLOWING |
| `setup_auth.py` | `user`          | `sp.current_user()` — Spotify API validation call | Yes — OAuth setup confirmed by token_cache/.cache existence | FLOWING |

---

### Behavioral Spot-Checks

| Behavior                              | Check                                                           | Result                                      | Status |
|---------------------------------------|-----------------------------------------------------------------|---------------------------------------------|--------|
| daemon.py has valid Python syntax     | `python3 -c "import ast; ast.parse(...)"` exits 0             | "daemon.py: syntax OK"                      | PASS   |
| setup_auth.py has valid Python syntax | `python3 -c "import ast; ast.parse(...)"` exits 0             | "setup_auth.py: syntax OK"                  | PASS   |
| asyncio entry point present           | `asyncio.run(main())` in daemon.py                             | Found                                       | PASS   |
| state.json is valid JSON with last_track_id | `python3 -c "import json; ..."`                          | last_track_id = "11ZulcYY4lowvcQm4oe3VJ"   | PASS   |
| Token cache populated                 | `ls token_cache/.cache`                                        | 509 bytes, created 2026-04-01T15:18 (root-owned from container) | PASS |
| No hardcoded credentials              | grep for secrets patterns in committed files                   | None found                                  | PASS   |
| Interruptible 429 backoff             | `asyncio.wait_for(asyncio.shield(stop_event.wait()), ...)` in daemon.py | Found at line 130                  | PASS   |

Note: Live daemon execution (docker compose up/stop cycle) was verified by the implementation team during the checkpoint task in plan 01-02 before this verification ran. Evidence of live execution: state.json holds real track ID (not null), token_cache/.cache exists with real token data.

---

### Requirements Coverage

| Requirement | Source Plan | Description                                                                        | Status    | Evidence                                                                                                |
|-------------|-------------|------------------------------------------------------------------------------------|-----------|---------------------------------------------------------------------------------------------------------|
| CORE-01     | 01-02       | Service polls Spotify playback state every ~1 second and detects when a new track begins | SATISFIED | `asyncio.sleep(POLL_INTERVAL)` with default 1s; `currently_playing()` called each iteration; track_id comparison detects changes |
| CORE-02     | 01-01, 01-02 | Service authenticates with Spotify via OAuth (one-time browser setup, then headless token refresh) | SATISFIED | `setup_auth.py` handles one-time OAuth; `CacheFileHandler` enables headless token refresh in daemon.py; `open_browser=False` in both |
| CORE-03     | 01-01       | Service runs as a macOS LaunchAgent and auto-restarts on crash                     | SATISFIED (with note) | Implemented via Docker `restart: always` — ROADMAP explicitly states "Docker service with restart:always" as the delivery vehicle for this requirement; the REQUIREMENTS.md wording "macOS LaunchAgent" is outdated relative to the Docker-on-Arch-Linux deployment target established in ROADMAP and CONTEXT |
| CORE-04     | 01-02       | Service reads the `explicit` flag from the currently playing Spotify track         | SATISFIED | `track["explicit"]` read and logged on every track change (daemon.py line 108); data flows from Spotify API response through poll_loop to log output |

**Note on CORE-03 wording:** REQUIREMENTS.md says "macOS LaunchAgent" but the ROADMAP Phase 1 goal and success criteria specify "Docker service with restart:always on Proxmox/Arch Linux". The Docker implementation fully satisfies the intent of CORE-03 (auto-restart on crash). The REQUIREMENTS.md text is an artifact of an earlier deployment target that was superseded before implementation. No implementation gap exists.

**Orphaned requirements check:** No additional CORE-01/02/03/04 mappings appear in REQUIREMENTS.md beyond those claimed by plans 01-01 and 01-02. No orphaned requirements.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| N/A  | —    | —       | —        | —      |

No anti-patterns found. No hardcoded credentials, no TODO/FIXME/placeholder comments, no empty return stubs, no console-log-only implementations.

**Notable deviation (not a gap):** `save_state()` uses direct file write instead of atomic rename via `os.replace()`. This was a deliberate fix during live verification — `os.replace()` raises `EBUSY` on Docker bind-mounted files on Linux. The direct-write approach is documented in the code comment at daemon.py line 63-67 and in the 01-02 SUMMARY deviations section. `load_state()` handles missing/corrupt files gracefully, making this trade-off acceptable.

---

### Human Verification Required

The following behaviors require live execution to confirm fully. They cannot be verified programmatically from static analysis alone. Evidence from the live checkpoint run (plan 01-02, task 3) provides strong indirect confirmation that all of these pass.

#### 1. Track detection latency

**Test:** Start playing a song on Spotify. Open `docker compose logs -f daemon`.
**Expected:** Within ~2 seconds, a log line appears: `Track change: [song name] — [artist] (explicit=True/False)`
**Why human:** Requires active Spotify playback and a running Docker container.
**Evidence from checkpoint:** Plan 01-02 summary confirms this was verified live. state.json contains a real track ID confirming it occurred.

#### 2. SIGTERM clean shutdown timing

**Test:** Run `docker compose stop`. Measure elapsed time until the daemon process exits.
**Expected:** Daemon exits within 1-2 seconds and logs show "Daemon stopped cleanly".
**Why human:** Requires timing measurement on a live container.
**Evidence from checkpoint:** Plan 01-02 summary confirms "Graceful shutdown on SIGTERM completing in under 1 second — verified live".

#### 3. Headless restart without re-auth

**Test:** Run `docker compose restart daemon`. Check that the daemon resumes polling without prompting for OAuth.
**Expected:** Logs resume normally; no authentication error; same token used.
**Why human:** Requires observing log continuity across a container restart.
**Evidence from checkpoint:** token_cache/.cache exists (509 bytes) confirming token was saved; CacheFileHandler is wired to the bind-mounted path in both setup_auth.py and daemon.py.

#### 4. Heartbeat log when nothing is playing

**Test:** Pause or stop Spotify playback. Wait HEARTBEAT_INTERVAL_SECONDS (default 300s).
**Expected:** Log line: "Heartbeat: daemon alive, no playback detected"
**Why human:** Requires waiting 5 minutes with no playback — not practical to verify statically.
**Evidence from code:** Heartbeat condition at daemon.py lines 93-95 is correctly gated on `time.monotonic() - last_heartbeat >= HEARTBEAT_INTERVAL`.

---

### Gaps Summary

No gaps found. All 4 observable truths are verified. All required artifacts exist and are substantive. All key links are wired. Data flows from the Spotify API through the poll loop to log output and state persistence. Requirements CORE-01 through CORE-04 are all satisfied. No blocker anti-patterns detected.

---

_Verified: 2026-04-01T16:00:00Z_
_Verifier: Claude (gsd-verifier)_
