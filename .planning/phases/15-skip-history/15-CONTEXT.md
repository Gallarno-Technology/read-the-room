# Phase 15: Skip History - Context

**Gathered:** 2026-04-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Skip feed history survives page refresh and SSE reconnect. On page load, up to 20 most recent skip events appear in the feed immediately. After an SSE reconnect, the skip feed retains all previously loaded entries and fills in any events missed during the disconnect. A new `GET /feed` endpoint serves the last N skip and five_skip_warning events from events.jsonl.

</domain>

<decisions>
## Implementation Decisions

### Feed endpoint
- **D-01:** New `GET /feed` endpoint in `web_ui/main.py` returns the last 20 skip and five_skip_warning events from `events.jsonl` as a JSON array, newest-first.
- **D-02:** Filter events.jsonl to only include `type: "skip"` and `type: "five_skip_warning"` — exclude `track_change`, `idle`, `eval_result`, and other event types.

### Event IDs
- **D-03:** Daemon adds a unique event ID to every event written to `events.jsonl`. Use a monotonic counter (integer, persisted in memory, reset on daemon restart is acceptable) or UUID. Field name: `"id"`.
- **D-04:** Event IDs enable robust deduplication during SSE reconnect merge — no timestamp collision ambiguity.

### Page-load hydration
- **D-05:** On page load, frontend fetches `GET /feed` and renders the returned events into the skip feed before any SSE events arrive. This satisfies HIST-01 (20 most recent skips visible immediately).
- **D-06:** Hydration runs in `DOMContentLoaded` alongside the existing `hydrateNowPlaying()` call.

### SSE reconnect behavior
- **D-07:** On SSE reconnect, frontend fetches `GET /feed`, then merges with events already in the DOM. Deduplication uses event ID (D-03). New events not already displayed are prepended. No visual disruption — user doesn't notice the reconnect.
- **D-08:** `_file_tail` in `web_ui/main.py` continues to seek to EOF on startup — no change. History delivery is handled entirely by `GET /feed`, not by replaying the SSE stream.

### Event cap & ordering
- **D-09:** Feed displays newest events on top (matches current `insertBefore(li, firstChild)` pattern).
- **D-10:** DOM feed is capped at 20 items. When a new event arrives and the feed already has 20 `<li>` elements, remove the oldest (last child) before prepending the new one. Prevents DOM bloat during long sessions.

### Claude's Discretion
- Exact monotonic counter vs UUID choice for event IDs
- Error handling for /feed endpoint (empty file, malformed lines)
- Whether to show a subtle "loaded N events" indicator after hydration or just silently populate

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` -- HIST-01, HIST-02, HIST-03 requirements

### Source files to modify
- `daemon.py` lines 80-101 -- `_append_event()` -- add event ID field to every emitted event
- `daemon.py` lines 346-393 -- `skip_event_queue.put_nowait()` calls -- event shape will gain `id` field
- `web_ui/main.py` lines 46-53 -- `EVENTS_PATH` constant and file-based IPC bridge -- reuse for /feed endpoint
- `web_ui/main.py` lines 89-123 -- `_file_tail()` -- no changes needed but important to understand (stays at EOF)
- `web_ui/main.py` lines 228-238 -- `/now-playing` endpoint -- pattern reference for the new `/feed` endpoint
- `web_ui/templates/index.html` lines 380-386 -- `#skip-feed` element and incident log section
- `web_ui/templates/index.html` lines 400-586 -- JavaScript section with `skipFeed`, `removeEmptyState()`, event rendering

### Prior phase context
- `.planning/phases/14-idle-detection/14-CONTEXT.md` -- idle event type added to events.jsonl (filter it out of /feed results)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_append_event(data)` (daemon.py:80) -- appends JSON line to events.jsonl; add `id` field here for all events
- `/now-playing` endpoint (web_ui/main.py:231) -- pattern for the new `/feed` endpoint (file read, JSON response)
- `removeEmptyState()` (index.html:540) -- removes "No skips yet" placeholder; reuse during hydration
- Skip `<li>` rendering logic (index.html:545-586) -- existing code builds skip feed items; extract into reusable function for hydration

### Established Patterns
- File-based IPC: daemon writes events.jsonl, web_ui reads it -- /feed reads from same file
- SSE event shape: `{"type": "<name>", "timestamp": "...", ...}` -- add `"id"` field to this shape
- Hydration pattern: `/now-playing` fetched on page load for now-playing card -- `/feed` follows same pattern for skip feed
- `_file_tail` seeks to EOF -- history is never replayed via SSE, only via /feed endpoint

### Integration Points
- `GET /feed` endpoint added to `web_ui/main.py` alongside existing `/now-playing` and `/skip` routes
- Frontend `DOMContentLoaded` handler gains a `fetch('/feed')` call alongside `hydrateNowPlaying()`
- `es.onopen` (SSE reconnect) triggers another `/feed` fetch + merge with existing DOM items
- DOM cap trimming integrates with the existing `skipFeed.insertBefore()` rendering path

</code_context>

<specifics>
## Specific Ideas

- Event IDs chosen over timestamp-based dedup for robustness -- user explicitly preferred this even though it requires daemon-side changes
- Keep-and-merge reconnect strategy chosen over clear-and-refetch to avoid visual disruption

</specifics>

<deferred>
## Deferred Ideas

None -- discussion stayed within phase scope

</deferred>

---

*Phase: 15-skip-history*
*Context gathered: 2026-04-04*
