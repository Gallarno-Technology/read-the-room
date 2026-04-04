# Phase 15: Skip History - Research

**Researched:** 2026-04-04
**Domain:** Backend endpoint (FastAPI), frontend hydration (vanilla JS), file-based event log
**Confidence:** HIGH

## Summary

Phase 15 adds skip feed persistence across page refreshes and SSE reconnects. The implementation is straightforward: a new `GET /feed` endpoint reads `events.jsonl` tail, filters to `skip` and `five_skip_warning` types, and returns JSON. The frontend fetches this on page load and SSE reconnect, deduplicating by a new event ID field added to every event in the daemon.

All the pieces exist: `_append_event()` in daemon.py is the single write path, `/now-playing` is the pattern for the new endpoint, `prependSkipItem()` builds feed items, and `hydrateNowPlaying()` shows the DOMContentLoaded hydration pattern. The work is connecting these with an ID field, a new endpoint, and frontend merge logic.

**Primary recommendation:** Add monotonic integer `id` field in `_append_event()`, build `GET /feed` by reading last ~200 lines of events.jsonl and filtering to skip/five_skip_warning (return last 20), hydrate on page load, and merge-by-id on SSE reconnect.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- D-01: New `GET /feed` endpoint in `web_ui/main.py` returns last 20 skip and five_skip_warning events from `events.jsonl` as JSON array, newest-first
- D-02: Filter events.jsonl to only `type: "skip"` and `type: "five_skip_warning"` -- exclude track_change, idle, eval_result, and other types
- D-03: Daemon adds unique event ID to every event written to `events.jsonl`. Field name: `"id"`
- D-04: Event IDs enable robust deduplication during SSE reconnect merge
- D-05: On page load, frontend fetches `GET /feed` and renders returned events into skip feed before SSE events arrive
- D-06: Hydration runs in `DOMContentLoaded` alongside existing `hydrateNowPlaying()` call
- D-07: On SSE reconnect, frontend fetches `GET /feed`, merges with events already in DOM. Deduplication uses event ID. No visual disruption
- D-08: `_file_tail` continues to seek to EOF on startup -- no change. History delivered by `/feed`, not SSE replay
- D-09: Feed displays newest events on top (matches current `insertBefore(li, firstChild)` pattern)
- D-10: DOM feed capped at 20 items. When new event arrives and feed has 20 `<li>` elements, remove oldest (last child) before prepending

### Claude's Discretion
- Exact monotonic counter vs UUID choice for event IDs
- Error handling for /feed endpoint (empty file, malformed lines)
- Whether to show a subtle "loaded N events" indicator after hydration or just silently populate

### Deferred Ideas (OUT OF SCOPE)
None
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| HIST-01 | User sees up to 20 most recent session skips in the skip feed on page load | D-05, D-06: `GET /feed` called in DOMContentLoaded, events rendered via reusable `prependSkipItem()` |
| HIST-02 | Skip feed history preserved after SSE reconnects (no blank-out) | D-07: `es.onopen` fetches `/feed`, merges by event ID, existing DOM items preserved |
| HIST-03 | `GET /feed` endpoint returns last N skip/five_skip_warning events from events.jsonl | D-01, D-02: New endpoint reads file, filters by type, returns newest-first JSON array |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | (existing) | Web framework for `/feed` endpoint | Already in use for `/now-playing`, `/skip`, `/fsm` |
| Vanilla JS | N/A | Frontend hydration and DOM manipulation | Already in use -- no framework in this project |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | (existing) | Testing `/feed` endpoint | Existing test infrastructure in `tests/` |
| fastapi.testclient | (existing) | HTTP-level endpoint tests | Pattern established in `test_web_ui_endpoints.py` |

No new dependencies required. Everything needed is already in the project.

## Architecture Patterns

### Pattern 1: File-Based IPC (Established)
**What:** Daemon writes events.jsonl, web_ui reads it. No shared memory or message queue.
**When to use:** All event data flows -- this is the project's IPC pattern.
**Implementation for /feed:**
```python
# Read events.jsonl from the end, filter, return last 20
# Pattern mirrors /now-playing (file read -> JSON response)
@app.get("/feed")
async def feed() -> JSONResponse:
    try:
        with open(EVENTS_PATH) as f:
            lines = f.readlines()
    except FileNotFoundError:
        return JSONResponse([])
    
    events = []
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            evt = json.loads(line)
        except json.JSONDecodeError:
            continue
        if evt.get("type") in ("skip", "five_skip_warning"):
            events.append(evt)
            if len(events) >= 20:
                break
    return JSONResponse(events)  # already newest-first from reversed()
```

### Pattern 2: Monotonic Event ID (New)
**What:** Integer counter in `_append_event()` incremented on each call. Added as `"id"` field to every event.
**Why monotonic integer over UUID:** Simpler, smaller, sortable, and dedup comparison is a trivial `===` on integers. Reset on daemon restart is acceptable per D-03.
**Implementation:**
```python
_event_counter = 0

def _append_event(event: dict) -> None:
    global _event_counter
    _event_counter += 1
    event["id"] = _event_counter
    try:
        os.makedirs(os.path.dirname(EVENTS_PATH) or ".", exist_ok=True)
        with open(EVENTS_PATH, "a") as f:
            f.write(json.dumps(event) + "\n")
    except OSError as exc:
        log.error("[EVENTS] failed to write event log: %s", exc)
```

### Pattern 3: DOM Hydration on Page Load (Established)
**What:** Fetch JSON endpoint in DOMContentLoaded, render into DOM.
**Existing example:** `hydrateNowPlaying()` fetches `/now-playing` and renders track card.
**New pattern:** `hydrateFeed()` fetches `/feed` and renders skip items.

### Pattern 4: SSE Reconnect Merge
**What:** On `es.onopen`, fetch `/feed`, compare event IDs against items already in DOM, prepend only new ones.
**Key detail:** Each `<li>` in the skip feed needs a `data-event-id` attribute so the merge logic can check which events are already displayed.
**Implementation sketch:**
```javascript
async function hydrateFeed() {
    const resp = await fetch('/feed');
    const events = await resp.json();
    // Events arrive newest-first; we need to render oldest-first 
    // so that insertBefore(li, firstChild) produces correct order
    const existing = new Set();
    skipFeed.querySelectorAll('li[data-event-id]').forEach(li => {
        existing.add(Number(li.dataset.eventId));
    });
    // Reverse so oldest renders first (each prepend puts it at top)
    const toRender = events.filter(e => !existing.has(e.id)).reverse();
    for (const evt of toRender) {
        prependSkipItem(evt);  // modified to accept and set data-event-id
    }
}
```

### Pattern 5: DOM Cap (New)
**What:** Keep max 20 `<li>` elements in skip feed. Trim oldest when adding new.
**Where:** In `prependSkipItem()` after inserting, check `skipFeed.children.length > 20` and remove `lastChild`.

### Anti-Patterns to Avoid
- **Replaying history via SSE:** D-08 explicitly says `_file_tail` stays at EOF. History is only served via `/feed`.
- **Reading entire events.jsonl into memory without limit:** File could grow large over weeks. Read from end or limit lines read.
- **Timestamp-based dedup:** Event IDs chosen over timestamps because two events can share the same `HH:MM:SS` timestamp.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON Lines parsing | Custom line parser | `readlines()` + `json.loads()` per line | Standard pattern, handles malformed lines with try/except |
| SSE reconnect | Custom reconnect logic | Browser-native `EventSource` auto-reconnect | Already working -- just add `/feed` fetch to `es.onopen` |
| DOM element dedup | Complex DOM traversal | `data-event-id` attribute + `Set` lookup | O(1) lookup, trivial to implement |

## Common Pitfalls

### Pitfall 1: Large events.jsonl File
**What goes wrong:** Reading entire file into memory becomes slow as events accumulate over weeks/months.
**Why it happens:** events.jsonl is append-only, never truncated.
**How to avoid:** Read all lines but break early when 20 matching events found (reading from end). For v1.4 this is acceptable -- file will be small. If it grows, a future phase could add log rotation.
**Warning signs:** Slow `/feed` response times.

### Pitfall 2: Event ID Collision After Daemon Restart
**What goes wrong:** Monotonic counter resets to 0, producing duplicate IDs for events already in the file.
**Why it happens:** Counter is in-memory only (D-03 says reset on restart is acceptable).
**How to avoid:** This is acceptable per the decision. Dedup only matters within a browser session -- page refresh fetches fresh data. The IDs just need to be unique within a "session window" of ~20 events. However, to be robust: initialize counter from the last event's ID in events.jsonl on daemon startup.
**Recommendation (Claude's discretion):** Initialize `_event_counter` from the max ID found in the last ~50 lines of events.jsonl at daemon startup. Costs ~2 lines of code, eliminates the edge case entirely.

### Pitfall 3: Race Between /feed Response and SSE Events
**What goes wrong:** A new SSE event arrives between the `/feed` fetch and the merge render, causing a duplicate.
**Why it happens:** Network timing.
**How to avoid:** The `data-event-id` + Set dedup handles this naturally -- SSE events rendered before the merge completes will be in the existing Set and skipped.

### Pitfall 4: five_skip_warning Rendering in Feed
**What goes wrong:** `prependSkipItem()` assumes skip event shape (track, artist, reason). `five_skip_warning` events have different fields.
**Why it happens:** D-02 says both types appear in feed, but current rendering logic only handles skips.
**How to avoid:** Add a conditional branch in the rendering function or a separate `prependWarningItem()` for five_skip_warning events. The warning events have `{type, timestamp}` -- render as "5 consecutive skips -- playback paused" with timestamp.

### Pitfall 5: Empty State Not Removed on Hydration
**What goes wrong:** "No skips yet" placeholder stays visible alongside hydrated events.
**Why it happens:** `removeEmptyState()` is called inside `prependSkipItem()` but might not trigger if hydration uses a different code path.
**How to avoid:** Ensure `hydrateFeed()` calls `removeEmptyState()` before or during rendering -- but `prependSkipItem()` already does this, so reusing that function handles it automatically.

## Code Examples

### Daemon: Event ID Addition (daemon.py)
```python
# At module level, after EVENTS_PATH definition
_event_counter = 0

def _init_event_counter() -> None:
    """Initialize event counter from last event in events.jsonl."""
    global _event_counter
    try:
        with open(EVENTS_PATH) as f:
            lines = f.readlines()
        for line in reversed(lines):
            line = line.strip()
            if not line:
                continue
            try:
                evt = json.loads(line)
                _event_counter = evt.get("id", 0)
                return
            except json.JSONDecodeError:
                continue
    except FileNotFoundError:
        pass

def _append_event(event: dict) -> None:
    global _event_counter
    _event_counter += 1
    event["id"] = _event_counter
    try:
        os.makedirs(os.path.dirname(EVENTS_PATH) or ".", exist_ok=True)
        with open(EVENTS_PATH, "a") as f:
            f.write(json.dumps(event) + "\n")
    except OSError as exc:
        log.error("[EVENTS] failed to write event log: %s", exc)
```

### Web UI: /feed Endpoint (web_ui/main.py)
```python
@app.get("/feed")
async def feed() -> JSONResponse:
    """Return last 20 skip/five_skip_warning events, newest-first (HIST-03)."""
    try:
        with open(EVENTS_PATH) as f:
            lines = f.readlines()
    except FileNotFoundError:
        return JSONResponse([])
    
    events = []
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            evt = json.loads(line)
        except json.JSONDecodeError:
            continue
        if evt.get("type") in ("skip", "five_skip_warning"):
            events.append(evt)
            if len(events) >= 20:
                break
    return JSONResponse(events)
```

### Frontend: Hydration + Merge (index.html)
```javascript
async function hydrateFeed() {
    try {
        const resp = await fetch('/feed');
        const events = await resp.json();
        const existing = new Set();
        skipFeed.querySelectorAll('li[data-event-id]').forEach(li => {
            existing.add(Number(li.dataset.eventId));
        });
        // Filter out already-displayed events, reverse so oldest prepends first
        const toRender = events.filter(e => !existing.has(e.id)).reverse();
        for (const evt of toRender) {
            if (evt.type === 'skip') {
                prependSkipItem(evt);
            } else if (evt.type === 'five_skip_warning') {
                prependWarningItem(evt);
            }
        }
        // Enforce 20-item cap
        while (skipFeed.querySelectorAll('li[data-event-id]').length > 20) {
            skipFeed.removeChild(skipFeed.lastElementChild);
        }
    } catch (err) {
        // Silently fail -- SSE will pick up live events
    }
}

// Call on page load alongside hydrateNowPlaying
document.addEventListener('DOMContentLoaded', function() {
    hydrateNowPlaying();
    hydrateFeed();
});

// Call on SSE reconnect
es.onopen = function() {
    sseDot.className = 'sse-dot connected';
    sseLabel.textContent = '';
    hydrateNowPlaying();
    hydrateFeed();  // merge with existing DOM items
};
```

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing) |
| Config file | none (uses default discovery) |
| Quick run command | `python -m pytest tests/test_web_ui_endpoints.py -x` |
| Full suite command | `python -m pytest tests/ -x` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| HIST-01 | Page load shows up to 20 recent skips | integration | `python -m pytest tests/test_web_ui_endpoints.py::test_feed_returns_recent_skips -x` | Wave 0 |
| HIST-02 | SSE reconnect preserves feed (frontend) | manual-only | Visual: refresh page, verify events persist | N/A |
| HIST-03 | GET /feed returns filtered events | unit | `python -m pytest tests/test_web_ui_endpoints.py::test_feed_endpoint -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_web_ui_endpoints.py -x`
- **Per wave merge:** `python -m pytest tests/ -x`
- **Phase gate:** Full suite green before verify

### Wave 0 Gaps
- [ ] `tests/test_web_ui_endpoints.py::test_feed_*` -- HIST-03 endpoint tests (empty file, normal events, filtering, cap at 20)
- [ ] `tests/test_daemon_events.py::test_event_id_*` -- verify `_append_event` adds `id` field, counter increments

## Sources

### Primary (HIGH confidence)
- Source code: `daemon.py` lines 95-103 -- `_append_event()` implementation
- Source code: `web_ui/main.py` lines 89-123 -- `_file_tail()` SSE publisher
- Source code: `web_ui/main.py` lines 231-244 -- `/now-playing` endpoint (pattern reference)
- Source code: `web_ui/templates/index.html` lines 545-586 -- `prependSkipItem()` rendering
- Source code: `web_ui/templates/index.html` lines 589-624 -- SSE event handling, `es.onopen`
- Source code: `tests/test_web_ui_endpoints.py` -- existing test patterns

### Secondary (MEDIUM confidence)
- FastAPI JSONResponse -- standard usage, well-known

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - no new dependencies, all existing project code
- Architecture: HIGH - all patterns established in codebase, just extending them
- Pitfalls: HIGH - identified through direct code reading, edge cases are concrete

**Research date:** 2026-04-04
**Valid until:** 2026-05-04 (stable -- no external dependency changes)
