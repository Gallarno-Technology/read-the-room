# Phase 14: Idle Detection - Research

**Researched:** 2026-04-04
**Domain:** Daemon poll loop state machine, SSE event pipeline, frontend SSE handler
**Confidence:** HIGH

## Summary

This phase is almost entirely an integration of existing infrastructure. All four components needed — `_write_now_playing()`, `_append_event()`, `renderIdle()`, and `hydrateNowPlaying()` — already exist and work correctly. The work is connecting them: a debounce counter and a dedup flag in `poll_loop`, and one new `else if` branch in the frontend `es.onmessage` handler.

The implementation follows the same patterns already established for `last_track_id`, `consecutive_skips`, and `prev_fsm` in `poll_loop`. No new libraries, no new helpers, no new endpoints, and no structural changes to any existing logic.

The only discretionary choices are: the exact debounce threshold (2 or 3 polls, both satisfy IDLE-02's ~5s requirement), the ISO timestamp format in the idle SSE event, and the wording of the log line. Research confirms the rest is fully specified in CONTEXT.md decisions D-01 through D-08.

**Primary recommendation:** Implement with debounce threshold = 3 polls (3 seconds at 1s interval), using `datetime.datetime.utcnow().isoformat() + "Z"` for timestamp (consistent with existing `_write_now_playing` pattern). Log: `"[IDLE] no active playback — idle state written"`.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Idle triggers only on `result is None` (204 No Content) or `result.get("item") is None` (podcast/ad). No change to the condition itself.
- **D-02:** Paused playback (`is_playing=False` but `item` present) continues to show the current track. No extra logic added.
- **D-03:** Write idle after 2-3 consecutive empty polls (~2-3s). Avoids brief "Nothing playing" flash between back-to-back tracks.
- **D-04:** Track consecutive empty poll count with a local counter in `poll_loop`. Reset to 0 whenever `result["item"]` is present. When counter reaches threshold, write idle + emit SSE.
- **D-05:** Write `{"status":"idle"}` to `now_playing.json` and emit `{"type":"idle"}` to `events.jsonl` ONLY ONCE per idle transition (not on every subsequent empty poll). Boolean flag `was_idle` gates the write/emit. Reset when a track is detected.
- **D-06:** Daemon emits `{"type": "idle", "timestamp": "<ISO>"}` to `events.jsonl`. The existing `_file_tail` in `web_ui/main.py` picks it up automatically.
- **D-07:** Frontend adds one branch to `es.onmessage`: `evt.type === 'idle'` → call `renderIdle()` and set `currentTrackId = null`. No other frontend changes needed.
- **D-08:** Write `{"status": "idle"}` (matching the shape `/now-playing` already returns when the file is missing). Ensures `hydrateNowPlaying()` on page load or SSE reconnect renders idle correctly.

### Claude's Discretion

- Exact debounce threshold value (2 or 3 polls — within the ~2-3s range)
- ISO timestamp format in the SSE idle event
- Log message text for idle transition

### Deferred Ideas (OUT OF SCOPE)

- **Extended pause as idle**: Paused-for-extended-time (e.g., 10+ min) transitioning to idle. Requires a timer tracking how long `is_playing=False` has been True. Out of scope for Phase 14.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| IDLE-01 | Daemon writes idle state to now_playing.json when Spotify reports no active playback | D-08: `_write_now_playing({"status":"idle"})` call after debounce threshold crossed; D-05: write once per idle transition |
| IDLE-02 | Dashboard now-playing card transitions to "Nothing playing" view within ~5s of playback stopping | D-03/D-04: 3-poll debounce = ~3s; D-06/D-07: SSE idle event → `renderIdle()` in frontend |
</phase_requirements>

## Standard Stack

No new libraries required. All work uses the existing project stack.

### Core (already installed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib `datetime` | 3.12 | ISO timestamp for idle event | Already used in `_write_now_playing` |
| Python stdlib `time` | 3.12 | HH:MM:SS timestamp format | Already used in `_append_event` calls |
| FastAPI SSE (existing) | — | Delivers idle event to browser | `_file_tail` already forwards all event types |
| Browser `EventSource` | — | Client-side SSE handler | `es.onmessage` already dispatches on event type |

### Installation
No new packages. No `pip install` step required.

## Architecture Patterns

### Existing Poll Loop State Machine Pattern

`poll_loop` already tracks multiple in-memory boolean/counter state variables:

```python
# Existing pattern (daemon.py ~200-260)
last_heartbeat = ...
consecutive_skips = 0      # counter — reset on condition
prev_fsm = False           # boolean flag — mirrors state transitions
```

The idle detection adds two variables following this exact pattern:

```python
idle_counter = 0           # consecutive empty polls; reset when item is present
was_idle = False           # dedup flag; gates write/emit to once per transition
```

### Debounce Counter Pattern

```python
# Source: CONTEXT.md D-03, D-04
if result is None or result.get("item") is None:
    idle_counter += 1
    if idle_counter >= IDLE_THRESHOLD and not was_idle:
        _write_now_playing({"status": "idle"})
        _append_event({"type": "idle", "timestamp": ...})
        was_idle = True
        log.info("[IDLE] no active playback — idle state written")
    # heartbeat logic unchanged here
else:
    # item present (playing or paused)
    idle_counter = 0
    was_idle = False
    # ... existing track change logic
```

**Key invariant:** `idle_counter` resets on ANY poll where `result["item"]` is present — whether playing or paused. `was_idle` stays True until a track appears, preventing repeated writes on every subsequent empty poll.

### SSE Event Shape

Existing events use two timestamp formats. The idle event should use both for consistency:

```python
# HH:MM:SS (used by skip, track_change, etc. in events.jsonl)
"timestamp": time.strftime("%H:%M:%S")

# ISO 8601 (used by now_playing.json)
"timestamp": datetime.datetime.utcnow().isoformat() + "Z"
```

For the idle event appended to `events.jsonl`, use `time.strftime("%H:%M:%S")` — consistent with all other event types that the frontend may consume.

### Frontend SSE Handler Addition

```javascript
// Source: CONTEXT.md D-07; index.html line 602 es.onmessage
// Insert AFTER the existing 'eval_result' branch (line ~617):
} else if (evt.type === 'idle') {
    renderIdle();
    currentTrackId = null;
}
```

`renderIdle()` (index.html:518) already shows `nowPlayingIdle`, hides `nowPlayingTrack`. No changes to `renderIdle()` itself.

### now_playing.json Shape on Idle

```json
{"status": "idle"}
```

This is the same shape that `GET /now-playing` already returns when the file is missing (web_ui/main.py:244). `hydrateNowPlaying()` already handles `data.status === 'idle'` → `renderIdle()` (index.html:527). No changes needed to `/now-playing` endpoint or `hydrateNowPlaying()`.

### Anti-Patterns to Avoid

- **Writing idle on every empty poll:** Without the `was_idle` flag, `_write_now_playing` and `_append_event` would fire every second during idle — causing unnecessary disk I/O and flooding the SSE stream.
- **Resetting idle_counter on paused tracks:** Paused tracks still have `result["item"]` present. The existing check `result is None or result.get("item") is None` correctly excludes them. Do not add `is_playing` to the condition.
- **Using os.replace() for atomic writes:** The codebase comment in `_write_now_playing` documents this explicitly — `os.replace()` raises EBUSY on bind-mounted Docker files. Direct write is the established pattern.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SSE delivery to browser | Custom push mechanism | Existing `_file_tail` + `_subscribers` | Already forwards all event types from events.jsonl |
| Idle page-load hydration | New endpoint | Existing `GET /now-playing` + `hydrateNowPlaying()` | Already handles `{"status":"idle"}` shape |
| Idle UI rendering | New DOM manipulation | Existing `renderIdle()` | Already correct — shows idle element, hides track div |

**Key insight:** The entire SSE pipeline is transparent to event type. `_file_tail` reads every JSON line from `events.jsonl` and forwards it to all subscribers. The frontend `es.onmessage` already dispatches on `evt.type`. Adding `idle` is purely additive.

## Common Pitfalls

### Pitfall 1: Counter Not Resetting When Playback Resumes
**What goes wrong:** `idle_counter` stays elevated, so the next gap after resumption hits the threshold faster than intended.
**Why it happens:** The reset is in the `else` branch (item present) but if the developer puts the reset only inside the `track_id != last_track_id` sub-block, it won't fire on same-track polls.
**How to avoid:** Reset `idle_counter = 0` and `was_idle = False` at the TOP of the `else` branch, before the `track_id` comparison.
**Warning signs:** Test shows idle fires after only 1 empty poll following resumption.

### Pitfall 2: Idle Emitted During Paused Playback
**What goes wrong:** `is_playing=False` is mistakenly treated as idle.
**Why it happens:** Confusing "no active device" (Spotify returns 204/None) with "paused" (Spotify returns item but `is_playing=False`).
**How to avoid:** The existing condition `result is None or result.get("item") is None` is correct. Do not add `result.get("is_playing", True) is False` to the condition — this is explicitly deferred per D-02.
**Warning signs:** Idle fires when manually pausing in Spotify.

### Pitfall 3: Multiple Idle Events Per Idle Period
**What goes wrong:** The SSE stream gets flooded with `idle` events — one per poll cycle for the entire idle period.
**Why it happens:** Missing the `was_idle` flag check before writing/emitting.
**How to avoid:** Gate both `_write_now_playing` and `_append_event` with `if not was_idle`.
**Warning signs:** Test shows > 1 idle event in events.jsonl after a single idle transition.

### Pitfall 4: Stale Track Data After Idle Period
**What goes wrong:** After playback resumes, `hydrateNowPlaying()` on SSE reconnect shows the old track from before idle.
**Why it happens:** `now_playing.json` still contains the last track; the idle write was skipped or didn't overwrite it.
**How to avoid:** `_write_now_playing({"status": "idle"})` must overwrite the file completely (not merge). The existing direct-write implementation does this correctly.
**Warning signs:** Page refresh after resume shows wrong track.

### Pitfall 5: currentTrackId Not Cleared on Idle
**What goes wrong:** After the idle event, a subsequent `eval_result` event for a stale `track_id` updates the badge incorrectly.
**Why it happens:** `currentTrackId` still holds the last track ID when idle fires.
**How to avoid:** Set `currentTrackId = null` in the `idle` branch of `es.onmessage` (D-07 specifies this explicitly).
**Warning signs:** Badge updates appear on the idle card after playback stops.

## Code Examples

### Daemon: Idle Counter and Flag Variables (add to poll_loop scope)

```python
# Source: CONTEXT.md D-03, D-04, D-05
# These two variables join last_heartbeat, consecutive_skips, prev_fsm
idle_counter: int = 0
was_idle: bool = False
```

### Daemon: Modified No-Playback Branch

```python
# Source: daemon.py line 230 — existing condition, extended
if result is None or result.get("item") is None:
    idle_counter += 1
    if idle_counter >= 3 and not was_idle:
        _write_now_playing({"status": "idle"})
        _append_event({
            "type": "idle",
            "timestamp": time.strftime("%H:%M:%S"),
        })
        was_idle = True
        log.info("[IDLE] no active playback — idle state written")
    # existing heartbeat logic unchanged:
    if time.monotonic() - last_heartbeat >= HEARTBEAT_INTERVAL:
        log.info("Heartbeat: daemon alive, no playback detected")
        last_heartbeat = time.monotonic()
else:
    # item present — reset idle state
    idle_counter = 0
    was_idle = False
    # ... existing track/evaluation logic unchanged
```

### Frontend: Idle Branch in es.onmessage

```javascript
// Source: CONTEXT.md D-07; insert after eval_result branch (index.html ~line 617)
} else if (evt.type === 'idle') {
    renderIdle();
    currentTrackId = null;
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Idle not detected | Detect via consecutive empty polls | Phase 14 | Dashboard shows "Nothing playing" within ~5s |
| Stale last-track data on reconnect | `now_playing.json` overwritten with `{"status":"idle"}` | Phase 14 | `hydrateNowPlaying()` renders idle correctly on reconnect |

## Open Questions

1. **Debounce threshold: 2 or 3 polls?**
   - What we know: Both satisfy IDLE-02 (~5s requirement). 3 polls = 3s idle window provides slightly more protection against false positives during gapless playback transitions. 2 polls = 2s.
   - What's unclear: Whether any Spotify gapless playback gaps exceed 2s.
   - Recommendation: Use 3 polls (more conservative, still well within requirement). Expose as a named constant `IDLE_THRESHOLD = 3` at the top of the function.

2. **Timestamp format for idle SSE event**
   - What we know: `_append_event` calls for skip/track_change use `time.strftime("%H:%M:%S")`. `_write_now_playing` uses `datetime.datetime.utcnow().isoformat() + "Z"`.
   - What's unclear: The CONTEXT.md specifies `"timestamp": "<ISO>"` in the SSE event shape, but the existing SSE event pattern uses HH:MM:SS.
   - Recommendation: Use `time.strftime("%H:%M:%S")` for the events.jsonl entry (consistent with all other `_append_event` calls). If the planner wants ISO format, add a second field `"iso_timestamp"` but don't break consistency.

## Environment Availability

Step 2.6: SKIPPED — Phase 14 is a pure code change with no external dependencies beyond the existing Python environment and Docker setup.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 + pytest-asyncio 0.25.3 |
| Config file | None — tests use `@pytest.mark.asyncio` decorators directly |
| Quick run command | `.venv/bin/python -m pytest tests/test_daemon_events.py tests/test_web_ui_endpoints.py -x -q` |
| Full suite command | `.venv/bin/python -m pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| IDLE-01 | Daemon writes `{"status":"idle"}` to `now_playing.json` after 3 consecutive empty polls | unit (async) | `.venv/bin/python -m pytest tests/test_daemon_events.py::test_idle_writes_now_playing -x` | Wave 0 |
| IDLE-01 | Daemon does NOT write idle on each subsequent empty poll (dedup via `was_idle`) | unit (async) | `.venv/bin/python -m pytest tests/test_daemon_events.py::test_idle_dedup -x` | Wave 0 |
| IDLE-01 | `was_idle` resets when track resumes — idle written again on next idle period | unit (async) | `.venv/bin/python -m pytest tests/test_daemon_events.py::test_idle_resets_on_track -x` | Wave 0 |
| IDLE-02 | Daemon emits `{"type":"idle"}` to events.jsonl after threshold (SSE delivery) | unit (async) | `.venv/bin/python -m pytest tests/test_daemon_events.py::test_idle_event_emitted -x` | Wave 0 |
| IDLE-02 | Debounce: fewer than threshold empty polls do NOT trigger idle | unit (async) | `.venv/bin/python -m pytest tests/test_daemon_events.py::test_idle_debounce -x` | Wave 0 |

### Sampling Rate

- **Per task commit:** `.venv/bin/python -m pytest tests/test_daemon_events.py -x -q`
- **Per wave merge:** `.venv/bin/python -m pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_daemon_events.py` — 5 new test functions covering IDLE-01 and IDLE-02 (file exists, new functions needed)

No new test files required. All idle tests extend the existing `tests/test_daemon_events.py`, following its established pattern of `_run_one_cycle` / multi-cycle helpers with `data_dir` fixture.

The `_run_one_cycle` helper in `test_daemon_events.py` runs exactly one cycle (stop_event fires after first sleep). Idle tests need a multi-cycle variant that runs N polls with `current_playback` returning None, then optionally resumes. That helper must be added in Wave 0.

## Sources

### Primary (HIGH confidence)

- Direct code inspection: `daemon.py` lines 225-454 — `poll_loop` implementation, all state variables, `_write_now_playing` and `_append_event` usage
- Direct code inspection: `web_ui/main.py` lines 89-124 — `_file_tail` confirms automatic forwarding of all event types
- Direct code inspection: `web_ui/templates/index.html` lines 518-621 — `renderIdle()`, `hydrateNowPlaying()`, `es.onmessage` handler
- Direct code inspection: `tests/test_daemon_events.py` — established test patterns, `data_dir` fixture, `_run_one_cycle` helper
- `.planning/phases/14-idle-detection/14-CONTEXT.md` — all implementation decisions D-01 through D-08

### Secondary (MEDIUM confidence)

- `.planning/REQUIREMENTS.md` — IDLE-01, IDLE-02 acceptance criteria
- `.planning/STATE.md` — phase context and accumulated project decisions

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new libraries; all existing
- Architecture: HIGH — patterns directly observed in daemon.py and test_daemon_events.py
- Pitfalls: HIGH — derived from direct reading of the existing code and CONTEXT.md decisions

**Research date:** 2026-04-04
**Valid until:** 2026-05-04 (stable codebase, no external dependencies)
