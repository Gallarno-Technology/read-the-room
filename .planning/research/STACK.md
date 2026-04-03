# Stack Research

**Domain:** Real-time now-playing dashboard card with manual skip — FastAPI/SSE web app
**Researched:** 2026-04-02
**Confidence:** HIGH

---

## Context: What This Milestone Adds

The existing web_ui service (`web_ui/main.py`) already has:

- A running SSE endpoint at `GET /events` backed by `asyncio.Queue` fan-out to per-client subscriber queues
- A file-tail coroutine (`_file_tail`) that reads `data/skip_events.jsonl` written by the daemon and pushes JSON objects to all subscribers
- FSM toggle via `GET/POST /fsm` reading/writing `state.json` (shared volume with daemon)
- Vanilla JS `EventSource('/events')` client that routes on `evt.type` (`skip`, `five_skip_warning`)

The daemon (`daemon.py`) already:
- Calls `sp.current_playback()` every 1 second via spotipy
- Detects track changes by comparing `track["id"]` against `state["last_track_id"]`
- Writes all skip events to `data/skip_events.jsonl` for IPC
- Holds a fully-authenticated `spotipy.Spotify` instance with scope `user-modify-playback-state`
- Uses `SocoSkipClient.skip()` + `SpotifySkipClient.skip()` as its skip abstraction

v1.2 adds:
- A now-playing card in the dashboard showing track name, artist, and evaluation state badge
- A manual skip button wired to the existing skip logic (no Spotify auth duplication)

---

## Recommended Stack

### Core Technologies

No new framework dependencies. All additions use the existing stack.

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python `asyncio` (stdlib) | 3.12 built-in | Coordinate new `now_playing_event` type alongside existing skip events in the file-tail coroutine | Already the concurrency primitive for all IPC. Zero cost to extend. |
| spotipy | 2.26.0 (existing) | Daemon reads `current_playback()` for track state — no new API calls needed | Already authenticated and scoped; `user-modify-playback-state` covers both read and skip. |
| FastAPI | 0.115.12 (existing) | New `POST /skip` endpoint — one route, ~10 lines | No additional setup; existing app instance, existing error-handling patterns. |
| Vanilla JS `EventSource` | Browser native | Receive `now_playing` SSE events, update card, dispatch skip button click | Already in use; routing on `evt.type` is trivial to extend. |

### New SSE Event Type: `now_playing`

The daemon emits a new event to `skip_events.jsonl` on every track change:

```json
{
  "type": "now_playing",
  "track": "Track Name",
  "artist": "Artist Name",
  "state": "evaluating",
  "timestamp": "14:32:01"
}
```

A second write with `state` updated to the final evaluation outcome (`passed`, `profanity`, `explicit`, `no_lyrics`, `skipped`) follows once `content_checker.check()` completes.

The web_ui `_file_tail` coroutine passes this event to all subscribers without modification — no web_ui code changes needed for IPC delivery.

### Manual Skip Endpoint

```
POST /skip
Response: {"ok": true} | HTTP 503 {"detail": "..."}
```

**Wiring approach — command file (no shared Spotify auth):**

The web_ui runs as a separate Docker container from the daemon. The daemon owns the authenticated `spotipy.Spotify` instance and the `SocoSkipClient`/`SpotifySkipClient` abstractions. Duplicating Spotify OAuth in web_ui is wrong — it would require re-shipping the token cache, re-instantiating the auth manager, and keeping two token refresh loops in sync.

The correct IPC pattern is a **command file** — the same pattern already used for `state.json` (FSM toggle):

1. `POST /skip` handler in web_ui writes `{"type": "skip_requested", "timestamp": "..."}` to `data/skip_commands.jsonl` (same `./data` bind-mount volume)
2. Daemon's `poll_loop` tails `skip_commands.jsonl` the same way web_ui tails `skip_events.jsonl`
3. On seeing a `skip_requested` entry, daemon calls the existing skip path it already runs for auto-skips
4. Daemon writes a `skip` event back to `skip_events.jsonl` — web_ui SSE propagates it to the browser

This requires:
- One new file in the `./data` volume: `data/skip_commands.jsonl`
- One new async tail coroutine in daemon (~20 lines, mirrors `_file_tail` pattern)
- One new FastAPI route in web_ui (~10 lines, mirrors `POST /fsm` pattern)
- One new `EventSource` handler branch in JS (`skip` event already handled — no new type needed)

**What NOT to do — shared spotipy instance:**
The two containers cannot share an in-process object. Any approach that tries to import daemon modules from web_ui, share a socket, or re-initialize SpotifyOAuth in web_ui adds complexity, auth state risk, and breaks the existing container separation.

### Supporting Libraries

No new PyPI dependencies in either container.

| Library | Version | Already in? | Role |
|---------|---------|-------------|------|
| `fastapi` | 0.115.12 | web_ui | `POST /skip` route |
| `python-dotenv` | 1.2.2 | both | unchanged |
| `spotipy` | 2.26.0 | daemon | skip execution |
| `soco` | 0.30.14 | daemon | Sonos skip execution |
| `asyncio` (stdlib) | 3.12 | both | file tail coroutines |

### Development Tools

No changes to dev toolchain. Existing pytest/pytest-asyncio covers unit testing of new daemon tail logic and web_ui route.

---

## Architecture: IPC Flow for Manual Skip

```
Browser
  │  click "Skip"
  │  POST /skip  ─────────────────────────────────────────────────────────┐
  │                                                                        │
  ▼                                                                        ▼
web_ui container                                               web_ui container
  POST /skip handler                                            /events SSE
  writes skip_commands.jsonl  ──── ./data volume ────►  (receives skip event back
                                                           from daemon via skip_events.jsonl)
                                         │
                                         ▼
                                  daemon container
                                  _skip_command_tail() coroutine
                                  reads skip_commands.jsonl
                                  calls existing client.skip()
                                         │
                                         ▼
                                  writes skip event to skip_events.jsonl
                                  (already done for auto-skips)
```

### Now Playing IPC Flow

```
daemon poll_loop
  detects track change
  writes {"type":"now_playing","state":"evaluating",...} to skip_events.jsonl
  runs content_checker.check()
  writes {"type":"now_playing","state":"passed|skipped|...",...} to skip_events.jsonl
         │
         ▼
  _file_tail in web_ui
  forwards both events to all SSE subscriber queues
         │
         ▼
  Browser EventSource.onmessage
  if evt.type === 'now_playing': update card
```

### State Updates per Track

Two writes to `skip_events.jsonl` per track change:

1. Immediately on track detection: `state: "evaluating"` — browser shows "Evaluating" badge
2. After `content_checker.check()` returns: `state: "passed" | "profanity" | "explicit" | "no_lyrics" | "skipped"` — browser updates badge

The "evaluating" initial state correctly handles Spotify/Sonos API latency — no instant result is reliable.

---

## What NOT to Add

| Avoided | Why | What to Do Instead |
|---------|-----|-------------------|
| WebSocket (e.g. via `websockets` or `fastapi-websocket`) | SSE already handles server→browser push; WS adds bidirectional complexity not needed | SSE for push, `fetch POST /skip` for action — same pattern as FSM toggle |
| Duplicate SpotifyOAuth in web_ui | Two token refresh loops competing on shared `token_cache` bind-mount — race condition on token writes | Command file IPC: web_ui writes intent, daemon executes |
| `spotipy` in `web_ui/requirements.txt` | Adds 4MB + auth complexity to a container that only needs to serve HTML/SSE | Daemon owns all Spotify calls |
| Album artwork via Spotify Images API | Requires `album.images[0].url` from `current_playback()` response — already available, but requires CORS-safe image proxying or direct `<img src="...">` from CDN. Not a requirement for v1.2. | Defer to v1.2 nice-to-have or later milestone |
| Polling from browser (`setInterval + fetch /now-playing`) | Would require a new `GET /now-playing` endpoint + polling loop — higher browser-to-server traffic than SSE push | Extend existing SSE event types |
| `sse-starlette` third-party library | FastAPI's `StreamingResponse` already handles SSE correctly — `sse-starlette` is a thin wrapper that adds no value here | Keep existing `StreamingResponse` pattern |
| Server-side track state storage in web_ui | Web_ui is stateless; it relays events from the file. Caching `last_known_track` in web_ui memory creates stale-state risk on reconnect. | Serve current state at connect time from `state.json` if needed (like FSM initial state injection) |

---

## Integration Points with Existing Code

### daemon.py changes

1. **`_append_skip_event()` — no change.** The new `now_playing` event type uses the same function and file.
2. **`poll_loop()` — two additions:**
   - Write `now_playing` event with `state: "evaluating"` on track change detection (before `content_checker.check()`)
   - Write `now_playing` event with final state after `content_checker.check()` returns
3. **New `_skip_command_tail()` coroutine** — mirrors `web_ui/_file_tail`. Tails `data/skip_commands.jsonl`, on `skip_requested` event executes the same skip path as auto-skip (selects SoCo vs Spotify skip client based on current device state).
4. **`main()` — add `asyncio.create_task(_skip_command_tail(...))`** alongside the existing poll_loop task.

### web_ui/main.py changes

1. **New `POST /skip` route** (~10 lines) — writes `{"type":"skip_requested","timestamp":"..."}` to `data/skip_commands.jsonl`. Returns `{"ok": true}`. Mirrors `POST /fsm` pattern.
2. **No changes to `_file_tail`, `_sse_event_generator`, or `GET /events`** — they already pass through any JSON object; `now_playing` events will flow through unchanged.

### web_ui/templates/index.html changes

1. **New now-playing card** — static HTML skeleton rendered server-side; JS populates it from SSE.
2. **New `skip` button** — `fetch('POST /skip')` on click; button is disabled while request in-flight.
3. **New `EventSource.onmessage` branch** — `evt.type === 'now_playing'` updates card DOM.
4. **Existing badge CSS classes** — reuse `badge--explicit`, `badge--profanity`, `badge--approved`, `badge--adult` for the evaluation state badge. Add `badge--evaluating` for the pending state.

### docker-compose.yml changes

No changes. The `./data` volume is already mounted in both containers. `skip_commands.jsonl` is a new file in that directory — no new volume mounts required.

---

## Installation

No new packages in either container.

```bash
# daemon/requirements.txt — no changes
# web_ui/requirements.txt — no changes
```

The only new artifact is `data/skip_commands.jsonl` (created at runtime by web_ui on first skip request, same as `data/skip_events.jsonl` is created by daemon).

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Manual skip IPC | Command file `skip_commands.jsonl` (same pattern as `skip_events.jsonl`) | Shared HTTP endpoint between containers (web_ui calls daemon's internal API) | Adds inter-container networking, health dependency, and retry logic. The daemon has no internal HTTP server — adding one is disproportionate to the problem. |
| Manual skip IPC | Command file | Redis pub/sub | Heavyweight external dependency for a single-host, two-container setup. Overkill. |
| Manual skip IPC | Command file | Unix domain socket | Requires socket file in shared volume, connection management, framing — all complexity that the append-only file avoids. |
| Now-playing push | New `now_playing` SSE event type via existing `skip_events.jsonl` | New `GET /now-playing` polling endpoint | Polling increases request frequency. SSE push is already wired and ready; zero incremental infrastructure. |
| Now-playing push | Two events per track (evaluating + final) | Single event after evaluation completes | Single event means the card shows stale data during the 1-3s lyrics fetch. Two events gives accurate "Evaluating..." badge immediately. |
| Spotify auth for skip | Command file IPC to daemon | Duplicate SpotifyOAuth in web_ui | Token file race condition, two refresh loops, auth state drift. One authenticated client is a fundamental architectural rule for this project. |

---

## Version Compatibility

| Package | Container | Version | Notes |
|---------|-----------|---------|-------|
| Python | both | 3.12 | `asyncio` file tail pattern unchanged |
| fastapi | web_ui | 0.115.12 | `StreamingResponse` SSE pattern unchanged |
| spotipy | daemon | 2.26.0 | `current_playback()` returns `album.images` — artwork available if needed |
| uvicorn | web_ui | 0.34.0 | Unchanged |

---

## Sources

- Existing `web_ui/main.py` — `_file_tail`, `_sse_event_generator`, `POST /fsm` patterns (HIGH confidence, primary source)
- Existing `daemon.py` — `_append_skip_event`, `poll_loop`, skip client usage (HIGH confidence, primary source)
- Existing `docker-compose.yml` — `./data` volume mount confirmed in both containers (HIGH confidence, primary source)
- [FastAPI StreamingResponse docs](https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse) — SSE via StreamingResponse (HIGH confidence, official docs)
- [spotipy current_playback docs](https://spotipy.readthedocs.io/en/2.26.0/#spotipy.client.Spotify.current_playback) — Response structure confirmed (HIGH confidence, official docs)
- [MDN EventSource](https://developer.mozilla.org/en-US/docs/Web/API/EventSource) — Browser SSE API, `onmessage` routing (HIGH confidence, official docs)

---

*Stack research for: Spotify Family Safe Mode v1.2 — now-playing dashboard card and manual skip*
*Researched: 2026-04-02*
