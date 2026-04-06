# Phase 14: Idle Detection - Context

**Gathered:** 2026-04-04
**Status:** Ready for planning

<domain>
## Phase Boundary

When Spotify reports no active playback (`result is None` or `result["item"] is None`), the daemon writes `{"status": "idle"}` to `now_playing.json` and emits an SSE `idle` event so the dashboard's now-playing card transitions to "Nothing playing" within ~5 seconds. Paused playback is out of scope — Spotify keeps returning the track item when paused, so the card continues showing the current track.

</domain>

<decisions>
## Implementation Decisions

### Idle detection scope
- **D-01:** Idle triggers only on `result is None` (204 No Content — no active device) or `result.get("item") is None` (podcast/ad). This is the existing no-playback check in `poll_loop` — no change to the condition.
- **D-02:** Paused playback (`is_playing=False` but `item` present) continues to show the current track. No extra logic added. Free behavior from the existing check.

### Idle write debounce
- **D-03:** Write idle after **2–3 consecutive empty polls** (~2–3s at 1s poll interval). Avoids a brief "Nothing playing" flash during brief Spotify gaps between back-to-back tracks. Still well within the ~5s requirement (IDLE-02).
- **D-04:** Track consecutive empty poll count with a local counter in `poll_loop`. Reset counter to 0 whenever `result["item"]` is present (playback active or paused). When counter reaches threshold, write idle + emit SSE event.

### Idle state deduplication
- **D-05:** Write `{"status":"idle"}` to `now_playing.json` and emit `{"type":"idle"}` to `events.jsonl` **only once per idle transition** — not on every subsequent empty poll. Use a boolean flag (`was_idle`) to gate the write/emit. Reset flag when a track is detected.

### SSE delivery for real-time idle
- **D-06:** Daemon emits `{"type": "idle", "timestamp": "<ISO>"}` to `events.jsonl` when the idle threshold is crossed. The existing `_file_tail` in `web_ui/main.py` picks it up and pushes it to all SSE subscribers.
- **D-07:** Frontend adds one branch to `es.onmessage`: `evt.type === 'idle'` → call `renderIdle()` and set `currentTrackId = null`. No other frontend changes needed — `renderIdle()` already exists.

### now_playing.json on idle
- **D-08:** Write `{"status": "idle"}` (matching the shape `/now-playing` already returns when the file is missing). This ensures `hydrateNowPlaying()` on page load or SSE reconnect correctly renders idle — not the stale last-track data.

### Claude's Discretion
- Exact debounce threshold value (2 or 3 polls) — within the ~2–3s range
- ISO timestamp format in the SSE idle event
- Log message text for idle transition

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §Idle Detection — IDLE-01, IDLE-02 requirements

### Source files to modify
- `daemon.py` lines 225–454 — `poll_loop()` is the only daemon function to modify; add consecutive-empty counter and idle write/emit logic
- `daemon.py` lines 104–116 — `_write_now_playing()` — reuse as-is; call with `{"status": "idle"}`
- `daemon.py` lines 80–101 — `_append_event()` — reuse as-is for idle SSE event
- `web_ui/templates/index.html` lines 588–621 — `es.onmessage` handler — add `idle` event branch
- `web_ui/templates/index.html` lines 518–521 — `renderIdle()` — already exists, no changes needed

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_write_now_playing(data)` (daemon.py:104) — direct file write; call with `{"status":"idle"}` to overwrite stale track
- `_append_event(data)` (daemon.py:80) — appends to events.jsonl; use for `{"type":"idle","timestamp":...}`
- `renderIdle()` (index.html:518) — shows idle element, hides track div; already handles the state correctly
- `hydrateNowPlaying()` (index.html:523) — already handles `data.status === 'idle'` → calls `renderIdle()`

### Established Patterns
- State flag pattern: `was_idle: bool` mirrors how `last_track_id` and `prev_fsm` are tracked in `poll_loop` — in-memory variable, no persistence needed
- SSE event shape: `{"type": "<name>", "timestamp": "<HH:MM:SS>", ...}` — matches existing `track_change`, `skip`, etc.
- `_write_now_playing` uses direct write (not atomic rename) due to EBUSY on bind-mounted files — continue this pattern

### Integration Points
- `poll_loop` (daemon.py:225): add consecutive-empty counter before the `else` branch; threshold write goes in the `if result is None...` block
- `es.onmessage` (index.html:602): add `else if (evt.type === 'idle')` branch after the `eval_result` branch
- `_file_tail` (web_ui/main.py:89): no changes — automatically forwards all event types from events.jsonl to subscribers

</code_context>

<specifics>
## Specific Ideas

- User confirmed: paused = show track is the right default; extended-pause-as-idle is desired eventually but out of scope for Phase 14

</specifics>

<deferred>
## Deferred Ideas

- **Extended pause as idle**: User wants paused-for-extended-time (e.g., 10+ min) to eventually transition to idle. Not achievable with the current `result is None` check alone — would require a timer tracking how long `is_playing=False` has been True. Out of scope for Phase 14; add as a quick task or Phase 16 follow-on.

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 14-idle-detection*
*Context gathered: 2026-04-04*
