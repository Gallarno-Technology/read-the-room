# Phase 6: Daemon SSE Extensions - Context

**Gathered:** 2026-04-02 (discuss mode)
**Status:** Ready for planning

<domain>
## Phase Boundary

The daemon emits real-time events for every track change and evaluation result so the web UI and browser always have current state. Also writes a `now_playing.json` snapshot after each evaluation. Pure daemon instrumentation — no new data sources, no UI changes, no new Spotify API calls.

Covers: DAEM-01, DAEM-02, DAEM-03.
Does NOT cover: web_ui endpoints (Phase 7), dashboard UI (Phase 8).
</domain>

<decisions>
## Implementation Decisions

### Event Channel

- **D-01:** Rename `data/skip_events.jsonl` → `data/events.jsonl`. All daemon events (skip, five_skip_warning, track_change, eval_result) write to this single file. Update `SKIP_EVENTS_PATH` env var name to `EVENTS_PATH` in daemon.py, web_ui/main.py, and docker-compose.yml. web_ui tails this file; browser routes by `type` field.

### eval_state Vocabulary

- **D-02:** Canonical `eval_state` strings are kebab-case. The complete state machine:
  - `"evaluating"` — track detected, ContentChecker not yet complete (emitted in track_change)
  - `"passed"` — track checked, no issues found
  - `"no-lyrics"` — LRCLIB returned nothing and explicit flag was clear (no skip)
  - `"skipped"` — track was auto-skipped by the daemon
  - `"paused"` — 5th consecutive skip; playback was paused instead of skipped
  - `"fsm-off"` — FSM was disabled; evaluation did not run (exact badge label TBD in Phase 8)

  These strings must be used verbatim across all phases (6 daemon, 7 backend, 8 frontend).

### FSM-off Behavior

- **D-03:** The daemon always emits `track_change` and `eval_result` events regardless of FSM state. When FSM is off, `eval_result` fires with `eval_state: "fsm-off"`. Same event schema, same file — no special code path. now_playing.json is also written in both FSM-on and FSM-off cases.

### Event Schemas (Claude's Discretion)

- **D-04:** `track_change` event (emitted before ContentChecker runs):
  ```json
  {
    "type": "track_change",
    "track_id": "<spotify_track_id>",
    "track": "<track_name>",
    "artist": "<artist_name>",
    "album_art_url": "<url_of_640px_image_or_null>",
    "eval_state": "evaluating",
    "timestamp": "<HH:MM:SS>"
  }
  ```

- **D-05:** `eval_result` event (emitted after ContentChecker completes, or immediately when FSM is off):
  ```json
  {
    "type": "eval_result",
    "track_id": "<spotify_track_id>",
    "eval_state": "<passed|no-lyrics|skipped|paused|fsm-off>",
    "timestamp": "<HH:MM:SS>"
  }
  ```

- **D-06:** `now_playing.json` (overwritten on each track_change, then again after eval_result):
  ```json
  {
    "track_id": "<spotify_track_id>",
    "track": "<track_name>",
    "artist": "<artist_name>",
    "album_art_url": "<url_or_null>",
    "eval_state": "<evaluating|passed|no-lyrics|skipped|paused|fsm-off>",
    "timestamp": "<ISO-8601>"
  }
  ```
  Written to `data/now_playing.json`. Shared volume with web_ui container.

- **D-07:** Album art URL: use the 640×640 image from `track["album"]["images"]` (index 0 after Spotify returns images sorted largest-first). Set to `null` if images list is empty.

### Claude's Discretion

- Where exactly in the poll_loop to slot the new `_append_event()` calls (before/after existing skip logic)
- Whether to inline `eval_state` mapping or extract a small helper function
- Exact env var migration approach (backwards-compat alias vs hard rename)
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §v1.2 Daemon Extensions — DAEM-01, DAEM-02, DAEM-03 define the success criteria
- `.planning/ROADMAP.md` §Phase 6 — Success criteria and dependency list

### Implementation reference files (read before touching)
- `daemon.py` — `poll_loop()`, `_append_skip_event()`, `SKIP_EVENTS_PATH` constant; all must be updated
- `web_ui/main.py` — `SKIP_EVENTS_PATH`, `_file_tail()`, `_startup()` event handler; env var rename propagates here
- `docker-compose.yml` — `SKIP_EVENTS_PATH` env var injection; needs updating to `EVENTS_PATH`

No external specs — requirements fully captured in decisions above and REQUIREMENTS.md.
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_append_skip_event(event: dict)` in `daemon.py` — rename to `_append_event()` and reuse as-is; already handles dir creation and error logging
- `skip_event_queue` in `daemon.py` — still used for in-process SSE path; low priority for Phase 6 (file tail is the working IPC)

### Established Patterns
- All events are JSON objects with a `"type"` discriminator field; browser and web_ui already route on this
- `time.strftime("%H:%M:%S")` for human timestamps in skip/warning events
- State reads use `state.get("key", default)` pattern — always read fresh from `load_state()` after track change
- No atomic file rename for writes (EBUSY on bind-mounted files) — direct open+write is the established pattern

### Integration Points
- `poll_loop()` is where both new events must be emitted:
  - `track_change` fires when `track_id != state.get("last_track_id")`, before `content_checker.check()`
  - `eval_result` fires after `content_checker.check()` returns (and also immediately after track detection when FSM is off)
- `data/` directory: `now_playing.json` lives here alongside `events.jsonl`; already created by `_append_event()`'s `os.makedirs` call
- web_ui `_file_tail()` already reads from `SKIP_EVENTS_PATH` — rename env var propagates here automatically
</code_context>

<specifics>
## Specific Ideas

- Rename the file and env var rather than add a new one — user explicitly said "rename so it's not specific to skip"
- `eval_state: "fsm-off"` is the daemon string; the visible badge label ("Monitoring Off" or similar) is a Phase 8 concern
- Same eval_result event fires whether track was allowed, skipped, or FSM was off — Phase 8 differentiates display by eval_state value
</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.
</deferred>

---

*Phase: 06-daemon-sse-extensions*
*Context gathered: 2026-04-02*
