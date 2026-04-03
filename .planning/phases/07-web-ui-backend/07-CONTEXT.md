# Phase 7: Web UI Backend - Context

**Gathered:** 2026-04-03 (discuss mode)
**Status:** Ready for planning

<domain>
## Phase Boundary

The web UI container gains two new API endpoints: `GET /now-playing` for page-load hydration (reads `now_playing.json` written by the daemon) and `POST /skip` for manual skip (calls Spotify directly, bypassing the daemon). Also adds Spotipy initialization to the web_ui container and the missing `token_cache` volume mount in docker-compose.yml.

Covers: SKIP-02, SKIP-03.
Does NOT cover: frontend UI changes (Phase 8), SSE event routing changes (already done in Phase 6), daemon changes.
</domain>

<decisions>
## Implementation Decisions

### GET /now-playing

- **D-01:** `GET /now-playing` reads `data/now_playing.json` directly on every request — no in-memory caching, no file watching. File path derived the same way as daemon: `os.path.join(os.path.dirname(EVENTS_PATH) or ".", "now_playing.json")`.
- **D-02:** If the file does not exist (first boot, before any track plays), return `{"status": "idle"}` with HTTP 200. This is the only "idle" sentinel — no other null-field variant.
- **D-03:** If the file exists, return its full contents as-is (JSON passthrough). No staleness detection — Phase 8's SSE disconnect handling is the signal for "daemon offline". Stale data is acceptable; the `eval_state` in the file is the last known truth.

### POST /skip

- **D-04:** `POST /skip` calls `sp.next_track()` (spotipy wrapper for `POST /me/player/next`). No request body needed. Returns `{"ok": true}` on success with HTTP 200.
- **D-05:** On Spotify error (no active playback, device unavailable, `SpotifyException`), return HTTP 503 with `{"detail": "skip_failed", "reason": "<exception message>"}`. Phase 8 handles the error state — just needs to distinguish success from failure.
- **D-06:** SKIP-03 (manual skip must not increment consecutive-skip counter) is architecturally guaranteed — `consecutive_skips` is an in-memory variable inside daemon's `poll_loop()`. The web_ui calls Spotify directly and the daemon never sees it as its own skip action. No special implementation needed.

### Spotipy Auth in web_ui

- **D-07:** web_ui initializes a `spotipy.Spotify` instance at startup using `SpotifyOAuth` + `CacheFileHandler` with `SPOTIFY_CACHE_PATH` env var — identical pattern to daemon.py lines 432–441. The cached token (written by the daemon's initial auth) is reused; no new OAuth flow.
- **D-08:** Scope for web_ui spotipy: `user-read-currently-playing user-modify-playback-state` — same as daemon — to avoid token scope mismatch on auto-refresh. (The cached token already has both scopes; using only `user-modify-playback-state` risks scope narrowing on refresh.)
- **D-09:** `docker-compose.yml` web_ui service is missing `./token_cache:/app/token_cache` volume mount. This must be added — without it, `SPOTIFY_CACHE_PATH=/app/token_cache/.cache` will not resolve to the shared token and every request will fail auth.
- **D-10:** If the token cache file doesn't exist at startup (daemon not yet authed), log a warning but don't crash. Requests to `POST /skip` will fail with 503 until auth is done — acceptable.

### Claude's Discretion

- Whether to initialize spotipy as a module-level singleton or inside a FastAPI lifespan event
- Exact exception handling granularity (one broad `SpotifyException` catch vs specific HTTP 403/404 cases)
- Whether to add `GET /now-playing` to the existing docstring at the top of main.py
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §v1.2 Manual Skip — SKIP-02, SKIP-03 define success criteria
- `.planning/ROADMAP.md` §Phase 7 — all four success criteria (endpoints, counter bypass, shared token)

### Existing web_ui code
- `web_ui/main.py` — all existing routes, patterns, and helpers; new endpoints must follow same style
- `web_ui/Dockerfile` — uvicorn startup; spotipy must be added to `web_ui/requirements.txt`

### Daemon reference (auth pattern to copy)
- `daemon.py` lines 425–441 — `SpotifyOAuth` + `CacheFileHandler` initialization; replicate in web_ui

### Infrastructure
- `docker-compose.yml` — web_ui `volumes` section; `./token_cache:/app/token_cache` must be added
- `.env` — `SPOTIFY_CACHE_PATH`, `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, `SPOTIFY_REDIRECT_URI` all already present and shared via `env_file: .env`

### Event schema (read-only for Phase 7)
- `.planning/phases/06-daemon-sse-extensions/06-CONTEXT.md` §D-06 — `now_playing.json` schema; `GET /now-playing` returns this shape verbatim
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `web_ui/main.py:_load_state()` — direct file read pattern (no try/except on missing file returns default). `GET /now-playing` uses same pattern but returns `{"status": "idle"}` on missing rather than a default dict.
- `web_ui/main.py:_save_state_merge()` — write pattern for reference only (Phase 7 doesn't write files).
- `web_ui/main.py:@app.on_event("startup")` — existing startup hook; spotipy init and `_file_tail` task both launch here.

### Established Patterns
- Direct file read with `open()` + `json.load()` — no atomic reads, no locks (bind-mount files on Linux)
- `JSONResponse({...})` for all endpoints
- `HTTPException(status_code=..., detail=...)` for errors
- Module-level constants for paths (`STATE_PATH`, `EVENTS_PATH`) derived from `os.environ.get()`

### Integration Points
- `data/now_playing.json` — already reachable via existing `./data:/app/data` volume mount; no new mounts needed for the file itself
- `token_cache/.cache` — needs `./token_cache:/app/token_cache` added to docker-compose.yml web_ui service
- `web_ui/requirements.txt` — `spotipy` must be added (currently only in root `requirements.txt` for daemon)
</code_context>

<specifics>
## Specific Ideas

- Stale `now_playing.json` is acceptable — return contents as-is. Phase 8's SSE disconnect is the staleness signal, not a timestamp check.
- `{"status": "idle"}` is the one and only idle sentinel from `GET /now-playing`. Phase 8 checks `data.status === "idle"` to show empty state.
</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.
</deferred>

---

*Phase: 07-web-ui-backend*
*Context gathered: 2026-04-03*
