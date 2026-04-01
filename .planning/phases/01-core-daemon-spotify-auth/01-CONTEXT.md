# Phase 1: Core Daemon & Spotify Auth - Context

**Gathered:** 2026-04-01
**Status:** Ready for planning

<domain>
## Phase Boundary

A background daemon authenticates with Spotify (one-time browser OAuth, then headless token refresh), polls playback state every ~1 second, and correctly detects the currently playing track. Runs as a Docker service on Proxmox (production) and Arch Linux (development). This is the skeleton everything else attaches to — no filtering, no skipping, no notifications in this phase.

</domain>

<decisions>
## Implementation Decisions

### OAuth Setup Flow
- **D-01:** `setup_auth.py` prints the Spotify auth URL to the terminal — no auto-open browser. User opens URL on their phone (SSH'd into the host from mobile), approves in Spotify, then pastes the full redirect URL back into the terminal prompt.
- **D-02:** After saving the token, the script makes one test API call (e.g. fetch current user profile) to validate the token works, then prints a success message and exits.
- **D-03:** Token stored via spotipy's `CacheFileHandler` (Authorization Code Flow). Token file path configurable via `.env`.

### Polling
- **D-04:** Fixed 1s poll interval — no adaptive rate. Daemon calls `GET /me/player/currently-playing` every second regardless of playback state.
- **D-05:** Poll interval is configurable via `.env` (e.g. `POLL_INTERVAL_SECONDS=1`).
- **D-06:** Track change detection: compare returned track ID to last known track ID. New ID = new track event.
- **D-07:** 429 backoff on Spotify rate limit responses — exponential backoff with jitter, then resume normal polling.

### Logging
- **D-08:** Plain text with timestamps to stdout. Docker captures stdout; use `docker logs` to monitor live.
- **D-09:** Log only meaningful events: daemon start, track changes, auth errors, API errors. Silent between events.
- **D-10:** Periodic heartbeat log line when no playback is detected (interval configurable via `.env`, e.g. `HEARTBEAT_INTERVAL_SECONDS=300`). Confirms daemon is alive when nothing is playing.

### Deployment
- **D-11:** Docker + docker-compose. The daemon and `signal-cli-rest-api` (Phase 3) are services in the same compose stack.
- **D-12:** `network_mode: host` on the daemon service — required for SoCo UPnP/multicast to reach Sonos speakers on the local network.
- **D-13:** `restart: always` on the daemon service — replaces macOS LaunchAgent KeepAlive. Auto-restarts on crash or exit.
- **D-14:** All runtime config (poll interval, token cache path, heartbeat interval, etc.) lives in a `.env` file at repo root, sourced by docker-compose.
- **D-15:** CORE-03 in REQUIREMENTS.md must be updated: "macOS LaunchAgent" → "Docker service with `restart: always`".

### Claude's Discretion
- Exact 429 backoff algorithm and max wait cap
- Heartbeat log message wording
- `.env` variable naming conventions
- `state.json` schema (Phase 1 only needs to persist current track ID for change detection across restarts)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §Daemon & Spotify Integration (CORE-01 through CORE-04) — polling, OAuth, LaunchAgent→Docker, explicit flag read
- `.planning/PROJECT.md` §Constraints — Spotify Web API only, no scraping

### Roadmap
- `.planning/ROADMAP.md` §Phase 1 — success criteria, plan breakdown (01-01, 01-02)

No external specs — requirements fully captured in decisions above and REQUIREMENTS.md.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None yet — greenfield project. No existing source files.

### Established Patterns
- spotipy: use `SpotifyOAuth` with `open_browser=False` and `CacheFileHandler` for headless token refresh
- asyncio poll loop (per ROADMAP.md plan 01-02)

### Integration Points
- Phase 2 attaches content filtering logic to the track-change event emitted by this poll loop
- Phase 3 attaches Signal notification calls to skip events (built in Phase 2)
- SoCo skip (Phase 2) requires `network_mode: host` — already locked in D-12

</code_context>

<specifics>
## Specific Ideas

- "If this is to be initiated from the host machine then it should print the URL and let the user paste the code, as I will be SSH'd through a mobile device on the local network" — auth flow must be terminal-only, no browser auto-open.
- User is on Proxmox in production — Docker is the deployment target, not macOS LaunchAgent.

</specifics>

<deferred>
## Deferred Ideas

- Sonos auto-detection of Family Safe Mode (v2 — SONO-01/02 in REQUIREMENTS.md)
- Web dashboard or UI for monitoring (explicitly out of scope)
- Adaptive polling rate based on playback state (user chose fixed 1s instead)

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 01-core-daemon-spotify-auth*
*Context gathered: 2026-04-01*
