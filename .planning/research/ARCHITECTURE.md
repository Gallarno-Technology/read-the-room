# Architecture Research

**Domain:** Now-playing card and manual skip integration into existing FastAPI/SSE dashboard (v1.2)
**Researched:** 2026-04-02
**Confidence:** HIGH — based on direct code inspection of the v1.1 codebase

---

## Standard Architecture

### System Overview (Current v1.1)

```
┌──────────────────────────────────────────────────────────────────┐
│  daemon (daemon.py) — Docker container                            │
│                                                                   │
│  poll_loop() every 1s                                             │
│      │                                                            │
│      ├── track_id unchanged → silent (no event emitted)          │
│      │                                                            │
│      └── track_id changed                                         │
│              │                                                    │
│              ├── save_state({"last_track_id": ...})               │
│              │                                                    │
│              └── if FSM on → ContentChecker.check(track)         │
│                      │                                            │
│                      └── if skip → _append_skip_event(...)       │
│                                    writes data/skip_events.jsonl │
└──────────────────────────────────────────────────────────────────┘
          │ ./data bind mount (shared volume)
          ▼
┌──────────────────────────────────────────────────────────────────┐
│  web_ui (web_ui/main.py) — Docker container                       │
│                                                                   │
│  _file_tail() polls skip_events.jsonl every 250ms                │
│      │                                                            │
│      └── new line → push to _subscribers queues → SSE /events    │
│                                                                   │
│  GET /events  → SSE stream (skip + five_skip_warning events)     │
│  GET/POST /fsm → read/write state.json                           │
└──────────────────────────────────────────────────────────────────┘
          │ SSE connection
          ▼
┌──────────────────────────────────────────────────────────────────┐
│  Browser (vanilla JS)                                             │
│                                                                   │
│  EventSource('/events')                                           │
│      → "skip" event → prepend to #skip-feed list                 │
│      → "five_skip_warning" event → show banner                   │
└──────────────────────────────────────────────────────────────────┘
```

### System Overview (Target v1.2)

```
┌──────────────────────────────────────────────────────────────────┐
│  daemon (daemon.py) — MODIFIED                                    │
│                                                                   │
│  poll_loop() every 1s                                             │
│      │                                                            │
│      ├── track_id unchanged → silent                             │
│      │                                                            │
│      └── track_id changed                                         │
│              │                                                    │
│              ├── save_state({"last_track_id": ...})               │
│              │                                                    │
│              ├── emit "track_change" event immediately            │  ← NEW
│              │   {type: "track_change", track, artist, album_art,│
│              │    track_id, eval_state: "evaluating"}             │
│              │   writes data/now_playing.json [atomic-ish write]  │
│              │   writes data/skip_events.jsonl (new event type)   │
│              │                                                    │
│              └── if FSM on → ContentChecker.check(track)         │
│                      │                                            │
│                      ├── emit "eval_result" event                 │  ← NEW
│                      │   {type: "eval_result", track_id,         │
│                      │    eval_state: "passed"|"skipped"|        │
│                      │    "no_lyrics"|"explicit"}                 │
│                      │   writes data/skip_events.jsonl            │
│                      │                                            │
│                      └── if skip → existing skip logic            │
│                                    (skip event unchanged)         │
└──────────────────────────────────────────────────────────────────┘
          │ ./data bind mount (shared volume)
          ▼
┌──────────────────────────────────────────────────────────────────┐
│  web_ui (web_ui/main.py) — MODIFIED                               │
│                                                                   │
│  GET /now-playing → reads data/now_playing.json                   │  ← NEW
│      returns current track + eval_state for on-load hydration    │
│                                                                   │
│  POST /skip → calls daemon's skip logic via SkipClient            │  ← NEW
│      (SpotifySkipClient only — web_ui owns a Spotify auth inst.)  │
│                                                                   │
│  _file_tail() — EXTENDED to pass through all event types         │
│      including "track_change" and "eval_result"                   │
└──────────────────────────────────────────────────────────────────┘
          │ SSE + fetch
          ▼
┌──────────────────────────────────────────────────────────────────┐
│  Browser (vanilla JS) — MODIFIED                                  │
│                                                                   │
│  On load: fetch('/now-playing') → render now-playing card         │
│                                                                   │
│  EventSource('/events') — EXTENDED:                              │
│      → "track_change" event → update card, set badge=evaluating  │
│      → "eval_result" event → update badge to final state          │
│      → "skip" event → existing feed logic (unchanged)             │
│                                                                   │
│  Manual skip button → POST /skip                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## IPC Mechanism: Extend skip_events.jsonl With New Event Types

### Decision

Extend `skip_events.jsonl` with two new event types (`track_change` and `eval_result`). Also write `data/now_playing.json` as a simple state snapshot for on-load hydration.

### Why This Approach

**Option A — Extend skip_events.jsonl:** Reuses the exact IPC path already working in production. `_file_tail()` already reads every new line and fans out to all SSE subscribers. Adding new event types is additive — the existing browser handler ignores unknown types. The web_ui tailing loop requires zero changes to propagate the new events.

**Option B — Separate now_playing.json state file (polling):** UI polls an endpoint every N seconds. Requires the browser to have its own poll timer. Adds 1-5s latency depending on poll interval. Does not compose cleanly with the existing SSE connection the browser already holds open.

**Option C — New SSE channel (e.g., /now-playing/events):** Browser manages two concurrent EventSource connections. Two separate tailing coroutines in web_ui. More code, more browser connections, no architectural benefit over extending the existing channel.

**Option D — In-process asyncio.Queue bridge:** Already rejected in v1.0 because daemon and web_ui run in separate Docker containers. The Queue is not shared across process boundaries (Gap-2 fix in v1.1 explains this decision).

**Verdict:** Option A is the right choice. The file-tail pattern is proven, the fan-out infrastructure is in place, and adding event types is the minimal change. Option B (now_playing.json) is needed as a companion for page load hydration only — it is not a polling IPC mechanism, just a state snapshot.

### now_playing.json Role

A single-record JSON file at `data/now_playing.json` holds the most recent track plus its last known eval_state. The web_ui reads this once on GET /now-playing to hydrate the card when a browser opens the dashboard mid-session. Without it, a browser opened after a track started would see an empty card until the next track change.

Write pattern: overwrite in place (same reasoning as `state.json` — `os.replace()` raises EBUSY on bind-mounted files on Linux). The daemon writes this file immediately on track change, before starting ContentChecker evaluation.

---

## Evaluation State Transitions

The badge cycles through these states for every track:

```
track detected by daemon
    │
    ▼
"evaluating"          ← emitted immediately with track_change event
                         browser renders spinner or "Checking..." badge
    │
    ├── FSM is OFF → "passed"    (no content check performed)
    │
    └── FSM is ON → ContentChecker.check(track)
            │
            ├── action=="allow", reason=="instrumental" → "no_lyrics"
            ├── action=="allow", reason=="lyrics_unavailable" → "no_lyrics"
            ├── action=="allow", reason=="clean" → "passed"
            ├── action=="skip", reason=="explicit" → "skipped"
            └── action=="skip", reason=="profanity" → "skipped"
```

The eval_result event carries `track_id` so the browser can confirm it applies to the currently displayed track. If a very fast skip causes the daemon to detect a second track before the first eval completes, the browser ignores eval_result events whose `track_id` does not match the currently displayed track.

**State mapping:**

| ContentChecker result | eval_state value | Badge display |
|----------------------|------------------|---------------|
| (initial, pre-check) | `"evaluating"` | "Checking..." |
| FSM off | `"passed"` | "OK" |
| allow, instrumental | `"no_lyrics"` | "Instrumental" |
| allow, lyrics_unavailable | `"no_lyrics"` | "No lyrics" |
| allow, clean | `"passed"` | "Clean" |
| skip, explicit | `"skipped"` | "Skipped" |
| skip, profanity | `"skipped"` | "Skipped" |

---

## Event Schema

### track_change event (new)

Written to `skip_events.jsonl` and now_playing.json when daemon detects a new track:

```json
{
  "type": "track_change",
  "track_id": "276zciJ7Fg7Jk6Ta6QuLkp",
  "track": "Song Title",
  "artist": "Artist Name",
  "album_art_url": "https://i.scdn.co/image/...",
  "timestamp": "14:23:01",
  "eval_state": "evaluating"
}
```

`album_art_url` sourced from `track["album"]["images"][0]["url"]` in the Spotify track object. Nullable — set to null if not present.

### eval_result event (new)

Written to `skip_events.jsonl` after ContentChecker completes (or when FSM is off):

```json
{
  "type": "eval_result",
  "track_id": "276zciJ7Fg7Jk6Ta6QuLkp",
  "eval_state": "passed",
  "timestamp": "14:23:02"
}
```

### now_playing.json snapshot

Written to `data/now_playing.json` by the daemon on every track change. Updated again after eval completes:

```json
{
  "track_id": "276zciJ7Fg7Jk6Ta6QuLkp",
  "track": "Song Title",
  "artist": "Artist Name",
  "album_art_url": "https://i.scdn.co/image/...",
  "eval_state": "passed",
  "timestamp": "14:23:01"
}
```

---

## Manual Skip Endpoint Design

### How It Works

The web_ui needs to trigger a skip from the browser without reimplementing Spotify OAuth. The daemon already holds an authenticated `spotipy.Spotify` instance (`sp`) and both skip clients (`SocoSkipClient`, `SpotifySkipClient`). The web_ui does not have access to these — it is a separate process.

**The simplest correct design:** The web_ui's `POST /skip` endpoint calls the Spotify Web API directly using its own spotipy instance, identical to how the daemon's `SpotifySkipClient` works.

Both containers share the same OAuth credentials (via `.env`) and the same token cache file (via the `./token_cache:/app/token_cache` bind mount in docker-compose). The token is refreshed by whichever process uses it. Since the token cache is a shared file, both processes can refresh independently without conflict — spotipy's `CacheFileHandler` does a file-write on refresh, and the 60-second token expiry window makes a concurrent write race unlikely in practice.

**This is not reimplementing auth** — it reuses the same credentials and token file. It is instantiating spotipy once in web_ui at startup, exactly as the daemon does. The web_ui already reads the same `.env` for FSM state operations.

```python
# web_ui/main.py additions (startup block)
cache_handler = CacheFileHandler(cache_path=os.environ["SPOTIFY_CACHE_PATH"])
auth_manager = SpotifyOAuth(
    client_id=os.environ["SPOTIFY_CLIENT_ID"],
    client_secret=os.environ["SPOTIFY_CLIENT_SECRET"],
    redirect_uri=os.environ["SPOTIFY_REDIRECT_URI"],
    scope="user-read-currently-playing user-modify-playback-state",
    open_browser=False,
    cache_handler=cache_handler,
)
_sp = spotipy.Spotify(auth_manager=auth_manager)
_spotify_skip = SpotifySkipClient(_sp)
```

### POST /skip endpoint

```
POST /skip
Body: {"device_id": "<optional>"}
Response: {"ok": true} or {"ok": false, "error": "..."}
```

The endpoint calls `_spotify_skip.skip(device_name, device_id)`. The `device_id` can be omitted — Spotify's `next_track()` without a device_id targets the currently active device. If the browser does not have the device_id (it may not), passing `device_id=None` is sufficient.

The web_ui does not need to know whether playback is on Sonos or a regular device. Manual skip from the UI always uses `SpotifySkipClient` because:
1. Sonos in Spotify Connect mode already uses `SpotifySkipClient` as a fallback in the daemon (error 701 issue documented in PROJECT.md).
2. The web_ui does not have SoCo discovery state (no `_ip_cache`).
3. Manual skip is a user-initiated action — the slight additional latency of the Spotify API vs. UPnP is acceptable.

### Why Not HTTP Call From web_ui to Daemon

An alternative is exposing a `POST /internal-skip` on the daemon and having web_ui call it. This requires the daemon to run an HTTP server (it does not — it is a pure asyncio poll loop), doubles the failure modes, and creates a dependency on container networking. The shared spotipy approach is simpler and already proven by the daemon's own skip path.

---

## Data Flow: Daemon Track Detection to Browser Badge Update

```
1. daemon poll_loop detects track_id != state["last_track_id"]
       │
       ▼
2. daemon writes track_change event to skip_events.jsonl
   daemon writes now_playing.json (eval_state: "evaluating")
       │
       ▼ (within 250ms — _file_tail poll interval)
3. web_ui _file_tail reads new line, parses JSON
   event.type == "track_change" → push to all _subscribers queues
       │
       ▼
4. browser SSE onmessage fires
   evt.type == "track_change"
       → update now-playing card (track name, artist, art)
       → set badge to "Checking..." (eval_state: "evaluating")
       → store currentTrackId = evt.track_id
       │
       ▼
5. daemon ContentChecker.check(track) completes
   (duration: ~0ms for explicit flag, ~100-500ms for lyrics fetch,
    ~1-50ms for profanity scan)
       │
       ▼
6. daemon writes eval_result event to skip_events.jsonl
   daemon updates now_playing.json (eval_state: final)
       │
       ▼ (within 250ms)
7. web_ui _file_tail reads eval_result line
   push to all _subscribers queues
       │
       ▼
8. browser SSE onmessage fires
   evt.type == "eval_result" AND evt.track_id == currentTrackId
       → update badge to final state
       (if track_id mismatch: discard — stale eval for previous track)
       │
       ▼ (only if action == "skip")
9. daemon also writes existing "skip" event to skip_events.jsonl
   browser receives "skip" event → prepends to #skip-feed (unchanged behavior)
```

**Total end-to-end latency budget:**

- Daemon detects track: up to 1s (poll interval)
- Daemon writes track_change: <1ms
- _file_tail picks up new line: up to 250ms
- Browser SSE delivery: <50ms on LAN
- "evaluating" badge appears: ~300ms after actual track change at median

- ContentChecker runs (explicit only): <5ms after track_change
- ContentChecker runs (lyrics path): 100-2000ms (LRCLIB cache hit vs. miss)
- eval_result badge update: 300ms after ContentChecker completes

---

## Recommended Project Structure

```
spotify-sentiment/
├── daemon.py                   # Modified — emit track_change and eval_result events
├── content_checker.py          # Unchanged in v1.2
├── skip_client.py              # Unchanged
├── lyrics_service.py           # Unchanged
├── profanity_scanner.py        # Unchanged
├── web_ui/
│   ├── main.py                 # Modified — add /now-playing, /skip endpoints
│   │                           #            add spotipy init at startup
│   └── templates/
│       └── index.html          # Modified — add now-playing card, manual skip button
├── data/
│   ├── skip_events.jsonl       # Extended with track_change and eval_result event types
│   └── now_playing.json        # New — snapshot for on-load hydration
└── tests/
    └── test_web_ui.py          # New or extended — cover /now-playing and /skip endpoints
```

---

## Architectural Patterns

### Pattern 1: Additive Event Types on Existing JSONL Channel

**What:** Write new event objects with new `type` values to the existing `skip_events.jsonl` file. The `_file_tail()` loop fans them out unchanged; existing browser code ignores types it does not handle.

**When to use:** Any time a new signal from daemon to browser is needed. The pattern absorbs new event types at zero infrastructure cost.

**Trade-offs:** The JSONL file accumulates all event types; tooling that reads skip history must now filter for `type=="skip"` to get the incident log. This is a minor grep-filter, not a structural problem. The alternative of per-event-type files would fragment the IPC into multiple tailing loops.

### Pattern 2: now_playing.json as Hydration State Only

**What:** Write a single-record JSON file (`now_playing.json`) that the web_ui reads once per browser page load via GET /now-playing. This is a state snapshot, not a poll target.

**When to use:** Any time the browser needs to know the current state without waiting for the next event. The SSE stream only delivers events that happen after the browser connects; a browser opened mid-track would otherwise show no current track until the next track change.

**Trade-offs:** Requires two writes per track change (JSONL append and now_playing.json overwrite). Both writes are cheap. The now_playing.json is a cache of the last event — always derivable from the JSONL tail — but faster to read on connection.

### Pattern 3: Manual Skip Uses web_ui's Own Spotipy Instance

**What:** web_ui instantiates its own `spotipy.Spotify` using the same credentials and shared token cache file as the daemon. `POST /skip` calls `sp.next_track()` directly.

**When to use:** When a web tier needs to call the same external API as the daemon. Shared token file avoids duplicating auth setup.

**Trade-offs:** Two processes share a token cache file. Concurrent token refresh writes are possible but unlikely (tokens are valid for 60 minutes and only refreshed when near expiry). If the daemon is actively refreshing and the web_ui simultaneously triggers a skip, one write may overwrite the other's refreshed token — but spotipy will simply re-refresh on the next call. This is the same risk that already exists between the daemon and the existing `POST /fsm` state.json write, and has not caused issues in production.

---

## Integration Points

### Modified Components

| Component | Status | Change |
|-----------|--------|--------|
| `daemon.py` | Modified | Emit `track_change` event at track detection; emit `eval_result` event after ContentChecker; write `now_playing.json` |
| `web_ui/main.py` | Modified | Add spotipy init at startup; add `GET /now-playing` endpoint; add `POST /skip` endpoint |
| `web_ui/templates/index.html` | Modified | Add now-playing card HTML; badge state machine in JS; manual skip button; handle new SSE event types |
| `data/now_playing.json` | New file | Created by daemon on first track change; bind-mounted via existing `./data` volume |
| `data/skip_events.jsonl` | Extended | New `track_change` and `eval_result` event types appended alongside existing `skip` events |

### Unchanged Components

| Component | Reason |
|-----------|--------|
| `content_checker.py` | No interface change needed — daemon wraps it with the new event emissions |
| `skip_client.py` | `SpotifySkipClient` is imported by web_ui; no changes to the class itself |
| `docker-compose.yml` | No new volumes or services; `./data` mount already shared |
| `_file_tail()` in web_ui | Requires no change — it already passes all JSON lines to subscribers regardless of type |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `daemon.py` → `skip_events.jsonl` | File append via `_append_skip_event()` | Add `track_change` and `eval_result` call sites; existing skip/five_skip_warning calls unchanged |
| `daemon.py` → `now_playing.json` | File overwrite (in-place write, same EBUSY reasoning as state.json) | Single-record JSON; daemon owns writes; web_ui reads only |
| `skip_events.jsonl` → `web_ui` | File-tail polling every 250ms (unchanged) | New event types flow through transparently |
| `web_ui /now-playing` → `now_playing.json` | File read on request | Serves snapshot to browser on page load; no caching needed |
| `web_ui /skip` → Spotify API | spotipy `sp.next_track()` via shared token cache | Same pattern as daemon's SpotifySkipClient |
| Browser → `web_ui /skip` | `fetch('POST /skip')` | Triggered by skip button click; 204/200 response acknowledged |

---

## Build Order

Dependency-ordered implementation sequence:

1. **Extend `_append_skip_event()` in `daemon.py`** — add `track_change` call site immediately after track change is detected. Add `eval_result` call site after ContentChecker returns. Write `now_playing.json` at both points (evaluating state first, final state after ContentChecker). This is the data-producing end.

2. **Add `GET /now-playing` in `web_ui/main.py`** — reads `now_playing.json`, returns current track and eval_state. No auth needed. Handle missing file gracefully (return `null` or `{}`). This enables the browser hydration path.

3. **Add spotipy init and `POST /skip` in `web_ui/main.py`** — init at startup (same pattern as daemon's `main()`). Endpoint calls `_spotify_skip.skip(None, None)` — no device_id required, Spotify targets active device. Return `{"ok": true/false}`.

4. **Update `index.html`** — add now-playing card HTML structure; hydrate from `GET /now-playing` on page load; handle `track_change` SSE event (update card, set badge to evaluating); handle `eval_result` SSE event (update badge, guard on track_id match); add skip button that calls `POST /skip`.

5. **Verify end-to-end** — run daemon + web_ui locally; open dashboard; observe card updates and badge transitions as tracks change; test skip button.

Steps 1-3 have no ordering dependency on each other (daemon changes and web_ui backend changes are independent). Step 4 depends on steps 2 and 3 being defined so the JS endpoints are known. Step 5 requires all prior steps.

---

## Anti-Patterns

### Anti-Pattern 1: Polling /now-playing From the Browser

**What people do:** Implement now_playing.json as a file the web_ui endpoint reads, and have the browser poll it every 1-2 seconds for updates.

**Why it's wrong:** The browser already has an open SSE connection to `/events`. A second poll timer is redundant infrastructure. Polling at 1s would double the request rate on a LAN server that already has the SSE push mechanism in place. Any latency goal achievable by polling at 500ms is better achieved by letting SSE push the update within 300ms.

**Do this instead:** Use `now_playing.json` only for the initial page load (GET /now-playing called once). All subsequent updates flow through the SSE channel via the extended skip_events.jsonl.

### Anti-Pattern 2: Adding a New SSE Channel for Now-Playing Events

**What people do:** Create a second SSE endpoint (e.g., `/now-playing/events`) with its own tailing coroutine reading a separate `now_playing_events.jsonl`.

**Why it's wrong:** Browser manages two EventSource connections. web_ui runs two tailing coroutines. Event ordering between the two channels is not guaranteed from the browser's perspective. All of this complexity exists to avoid adding two event types to an existing JSONL file that is already read by a loop that fans out to all subscribers.

**Do this instead:** Extend skip_events.jsonl with `track_change` and `eval_result` types. They flow through the existing pipeline without any infrastructure changes.

### Anti-Pattern 3: Triggering Daemon Skip via HTTP Call from web_ui

**What people do:** Expose a `POST /internal-skip` or similar endpoint on the daemon service, have web_ui call it via HTTP.

**Why it's wrong:** The daemon has no HTTP server — it is a pure asyncio poll loop. Adding one introduces a listener port, error handling for HTTP, and a service dependency in docker-compose. The manual skip does not need daemon involvement because the Spotify API call is stateless — any caller with valid credentials can call `next_track()`.

**Do this instead:** web_ui calls the Spotify API directly via its own spotipy instance sharing the same token cache as the daemon. The daemon detects the track change on its next poll and handles any content evaluation as normal.

### Anti-Pattern 4: Emitting eval_result Only When Action is Skip

**What people do:** Only write an eval_result event to the JSONL when ContentChecker returns `action=="skip"` (because that's the interesting case for the skip feed).

**Why it's wrong:** The browser badge stays stuck at "evaluating" forever for clean tracks. The parent sees "Checking..." indefinitely for safe songs, which is worse UX than seeing "Clean" or "Instrumental".

**Do this instead:** Always emit eval_result after ContentChecker completes, regardless of action. The eval_state value distinguishes the outcome: `"passed"`, `"no_lyrics"`, or `"skipped"`.

### Anti-Pattern 5: Storing track_id in Browser State Across Page Reloads

**What people do:** Use localStorage to persist currentTrackId so the browser can resume badge state after reload.

**Why it's wrong:** The page already calls `GET /now-playing` on load to hydrate the card. The server is the authoritative source for current state. localStorage-based resume adds stale-state risk and complicates the mental model with no benefit — the hydration endpoint already handles this case cleanly.

**Do this instead:** On page load, call `GET /now-playing` once, set currentTrackId from the response. All subsequent badge updates come from SSE.

---

## Scalability Considerations

Single-user, single-process application. Not a scalability concern. Notes only:

| Concern | At current scale | Notes |
|---------|-----------------|-------|
| SSE subscriber list | 1-2 open browser tabs | `_subscribers` list grows with open tabs; full queues are already dropped by `_file_tail()` |
| now_playing.json write contention | None (daemon only writes) | web_ui reads; no concurrent writers |
| Token cache contention | Low — daemon skips continuously; manual skip is rare | If both processes refresh simultaneously, the second write wins; next API call re-refreshes silently |
| JSONL file size | ~1KB per day of active listening | No rotation needed for this use case; file is read from end on startup |

---

## Sources

- Direct code inspection: `daemon.py`, `web_ui/main.py`, `skip_client.py`, `content_checker.py`, `web_ui/templates/index.html`, `docker-compose.yml` — HIGH confidence
- Current `data/skip_events.jsonl` event schema — HIGH confidence
- `state.json` read/write pattern and EBUSY rationale (PROJECT.md key decisions) — HIGH confidence
- Existing token cache sharing (`./token_cache:/app/token_cache` volume in docker-compose.yml) — HIGH confidence
- Error 701 / Sonos UPnP constraint documented in PROJECT.md and skip_client.py — HIGH confidence

---
*Architecture research for: v1.2 Now Playing Status card + manual skip integration*
*Researched: 2026-04-02*
