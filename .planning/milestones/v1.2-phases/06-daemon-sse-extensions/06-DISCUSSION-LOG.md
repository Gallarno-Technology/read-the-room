# Phase 6: Daemon SSE Extensions - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the discussion.

**Date:** 2026-04-02
**Phase:** 06-daemon-sse-extensions
**Mode:** discuss
**Areas discussed:** Event channel design, eval_state vocabulary, FSM-off behavior

## Gray Areas Presented

- Event channel design — reuse skip_events.jsonl vs. separate file
- Schema: track_change, eval_result, now_playing.json — not selected (captured at Claude's discretion)
- eval_state vocabulary — canonical strings for badge state machine
- FSM-off behavior — whether to emit events when FSM is disabled

## Decisions Made

### Event Channel

| Area | Decision | Confidence |
|------|----------|-----------|
| File strategy | Single file for all events | Confirmed |
| File name | Rename skip_events.jsonl → events.jsonl | User-directed |

- **User clarification:** "keep all events in one file, but rename so it's not specific to skip"

### eval_state Vocabulary

| Assumption | Decision | Source |
|-----------|----------|--------|
| kebab-case strings | Confirmed | User selected |
| 5-state + fsm-off machine | evaluating → passed / no-lyrics / skipped / paused / fsm-off | User confirmed |

### FSM-off Behavior

- **User clarification:** "if we still emit events when FSM is off, can we use the same event when a song goes from evaluating to passed, just the reason/badge would be 'evaluation disabled' — we'll have a better term for the UI"
- **Decision:** Always emit track_change + eval_result; when FSM is off, eval_result fires with `eval_state: "fsm-off"`. Badge label TBD in Phase 8.

## Corrections Applied

None — all areas resolved via discussion.

## Schema (Claude's Discretion)

User did not select "Schema" gray area — captured as D-04 through D-07 in CONTEXT.md based on:
- Phase 7 needs: track_id, eval_state in now_playing.json (hydration endpoint)
- Phase 8 needs: track name, artist, album art, eval_state (dashboard card)
- Album art: 640px image from `track["album"]["images"][0]`, null if missing
