# Phase 3: Signal Notifications & Interactive Confirmations - Context

**Gathered:** 2026-04-01
**Status:** Ready for planning

> ⚠️ **Scope change from ROADMAP:** Phase 3 was planned as Signal notifications. During discussion, Signal was dropped entirely in favor of a Web UI dashboard. The phase name and ROADMAP description are stale — planner should update them. Requirements SIG-01 through SIG-04 and FSM-03 need to be replaced with Web UI equivalents before planning begins.

<domain>
## Phase Boundary

A lightweight Web UI dashboard served alongside the daemon. Shows a real-time skip history feed (what was skipped, when, and why) and a Family Safe Mode toggle. Signal is dropped entirely — no signal-cli, no phone notifications. Interactive allow/skip prompts are also out of scope. The daemon's content-checking and skip logic is unchanged; Phase 3 adds observability and control via browser.

</domain>

<decisions>
## Implementation Decisions

### Scope Change
- **D-01:** Signal is dropped entirely. No signal-cli-rest-api, no phone notifications. The Web UI is the only interface for Phase 3. Requirements SIG-01 through SIG-04 are replaced by Web UI equivalents.
- **D-02:** Interactive allow/skip prompts (original SIG-02/SIG-03) are NOT built in Phase 3. Ambiguous tracks (`lyrics_unavailable`) continue to auto-allow — FILT-05 behavior is unchanged.

### Web UI Stack
- **D-03:** FastAPI + plain HTML/JS. No JavaScript framework, no build step, no npm. HTML served directly by FastAPI.
- **D-04:** Real-time skip feed updates via Server-Sent Events (SSE). Browser opens a persistent `EventSource` connection; daemon pushes new skip events as they happen. No polling, no WebSocket.
- **D-05:** FastAPI runs as a second service in the existing `docker-compose.yml`. Shares the host network (`network_mode: host`) so it can read `state.json` and receive events from the daemon process.

### Skip History Feed
- **D-06:** Each skip entry shows: track name + artist + skip reason + timestamp.
- **D-07:** Feed updates in real-time via SSE (D-04). No manual page refresh needed.
- **D-08:** Skip events are emitted by the daemon and consumed by the FastAPI SSE endpoint. The daemon writes to a shared event queue or appends to a lightweight in-memory log that FastAPI reads.

### FSM Toggle
- **D-09:** FSM toggle in the Web UI reads and writes `state.json` directly (same file the daemon uses). Write path must use the same read-merge pattern as `save_state()` in daemon.py — never overwrite keys the daemon owns.
- **D-10:** No auth on the Web UI for v1. Home network only — accessible on LAN, not exposed externally.

### 5-Consecutive-Skip Threshold (FSM-03 replacement)
- **D-11:** When 5 consecutive skips occur with FSM on, the daemon immediately pauses Spotify playback via `PUT /me/player/pause` (Spotify API).
- **D-12:** A warning banner appears in the Web UI: "5 consecutive skips — switch your playlist and resume." Dismissible.
- **D-13:** The consecutive skip counter resets when: FSM is toggled off, or when a non-skipped track plays (action = "allow"). Implementation details (in-memory vs persisted, exact reset triggers) left to Claude's discretion.

### Claude's Discretion
- Consecutive skip counter storage (in-memory is fine — resets on daemon restart, which is acceptable)
- SSE event format (JSON with track, artist, reason, timestamp fields)
- How the daemon and FastAPI service share skip events (in-process queue vs shared file vs SQLite append)
- FastAPI port (suggest 8080 or 8888 — must not conflict with Spotify redirect URI port)
- HTML/CSS styling (minimal, functional — no design system required)
- How the Web UI handles daemon restarts (SSE reconnect is automatic via EventSource)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` — FSM-03, SIG-01 through SIG-04 (Phase 3 requirements, currently Signal-based — planner must update these to Web UI equivalents before writing plans)

### Existing Daemon Code
- `daemon.py` — `poll_loop()` is the integration point; skip events currently logged via `log.info("[SKIP] ...")` — Phase 3 also pushes these to the SSE event stream
- `daemon.py:save_state()` / `load_state()` — FSM toggle in Web UI must use the same read-merge write pattern
- `content_checker.py` — `check()` returns `(action, reason, severity)`; `action="allow"` with `reason="lyrics_unavailable"` is unchanged (no interactive prompts)
- `docker-compose.yml` — FastAPI service must be added here; `network_mode: host` already set on daemon service

### Project Context
- `.planning/PROJECT.md` — core value, out-of-scope list (Web dashboard was originally out of scope for v1 — planner should note the intentional scope change)
- `.planning/ROADMAP.md` — Phase 3 goal and success criteria are stale (Signal-based); planner must update before writing plans

No external specs — requirements captured in decisions above.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `daemon.py:poll_loop()` — skip events are already structured as `[SKIP] reason=X track=Y artist=Z`; Phase 3 taps into the same code path to also push to SSE
- `daemon.py:save_state()` / `load_state()` — FSM toggle reuses this exact read-merge pattern; no new file-write logic needed
- `state.json` — already contains `family_safe_mode` key; FSM toggle endpoint reads/writes this
- `docker-compose.yml` bind-mount pattern — FastAPI service follows same pattern as daemon (bind-mount `state.json`)

### Established Patterns
- All config from `.env` via `python-dotenv` — FastAPI port and any new config follow this pattern
- Direct file write (not atomic rename) — required for bind-mounted files on Linux (EBUSY); FSM write must use same approach
- `network_mode: host` — already set; FastAPI service inherits this
- Structured log lines to stdout — `[SKIP]` format already machine-parseable; SSE payload mirrors this

### Integration Points
- **Skip event emission:** After `if action == "skip":` block in `poll_loop()`, push event to a shared asyncio Queue that the SSE endpoint consumes
- **FSM toggle endpoint:** `POST /fsm` reads `state.json`, merges `{"family_safe_mode": bool}`, writes back using `save_state()` pattern
- **5-skip counter:** Tracked in `poll_loop()` alongside the existing `last_track_id` check; counter increments on `action="skip"`, resets on `action="allow"` or FSM toggle
- **Pause on 5th skip:** After incrementing to 5, call `sp.pause_playback()` (spotipy wrapper for `PUT /me/player/pause`)

</code_context>

<specifics>
## Specific Ideas

- "Simplest option" — FastAPI + plain HTML/JS chosen explicitly for minimal complexity. No frameworks, no build pipeline.
- "Real-time updates" is a firm requirement — SSE chosen because it works natively in plain JS with `EventSource`, no library needed.
- "Stop the music" on 5 consecutive skips — user wants active intervention (pause), not just a passive notification. Pause fires immediately on the 5th skip.
- Web UI is home-network only — no auth, no HTTPS required for v1. Keep it simple.

</specifics>

<deferred>
## Deferred Ideas

- **Signal notifications (original Phase 3 scope):** Dropped entirely by user decision. If push notifications are ever needed, Signal or another push channel would be a separate phase.
- **Interactive allow/skip prompts:** No prompt mechanism in Phase 3 — not via Signal, not via Web UI. If needed in future, would require a separate phase with a polling or WebSocket approach.
- **Web UI auth / external access:** No auth for v1. If the service ever needs to be accessible outside the home network, auth + HTTPS would be required.
- **Per-reason skip filtering:** User could filter skip history by reason (explicit, profanity, etc.) — not in scope for Phase 3.
- **"Now playing" live track display:** Not selected — skip history is the focus.

### Reviewed Todos (not folded)
None — no pending todos matched Phase 3 scope.

</deferred>

---

*Phase: 03-signal-notifications-interactive-confirmations*
*Context gathered: 2026-04-01*
