# Phase 14: Idle Detection - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-04
**Phase:** 14-Idle Detection
**Areas discussed:** Paused vs stopped, Idle debounce, SSE vs polling

---

## Paused vs stopped

| Option | Description | Selected |
|--------|-------------|----------|
| Show track when paused | Paused = track still loaded. Existing check (`result is None or item is None`) handles this free — no extra logic needed. | ✓ |
| Show idle when paused | Would require adding `is_playing` check. Treats pause and stop the same. | |

**User's choice:** Show track when paused
**Notes:** User clarified they wanted extended pause (10+ min) to eventually show idle. After discussion, confirmed that Spotify continues returning the track item regardless of pause duration — so extended-pause-as-idle requires additional timer logic. Deferred to future phase/quick task. Phase 14 starts minimal: idle only on `result is None`.

---

## Idle debounce

| Option | Description | Selected |
|--------|-------------|----------|
| 2-3 polls = ~2-3s | Write idle after 2-3 consecutive empty polls. Avoids brief "Nothing playing" flash during track transitions. Within ~5s requirement. | ✓ |
| Immediate (1st empty poll) | Write idle on very first empty poll (~1s). Fastest but may flash briefly during back-to-back track transitions. | |

**User's choice:** 2-3 polls (~2-3s)

---

## SSE vs polling

| Option | Description | Selected |
|--------|-------------|----------|
| SSE event | Daemon emits `{"type":"idle"}` to events.jsonl. Consistent with track_change/eval_result pattern. Note: idle events appear in events.jsonl — Phase 15 skip history will filter them. | ✓ |
| Frontend polling | `setInterval` in browser polls `/now-playing` every ~3s. No events.jsonl entries, but new polling pattern and more requests. | |

**User's choice:** SSE event

---

## Claude's Discretion

- Exact debounce threshold (2 or 3 polls within the 2-3s range)
- ISO timestamp format in the SSE idle event
- Log message text for idle transition

## Deferred Ideas

- Extended-pause-as-idle: user wants this eventually; requires timer tracking `is_playing=False` duration — deferred to quick task or future phase
