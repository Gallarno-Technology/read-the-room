# Domain Pitfalls

**Domain:** Adding a real-time now-playing card and manual skip to an existing Spotify filter daemon + SSE dashboard
**Researched:** 2026-04-02
**Confidence:** HIGH (codebase read directly; all pitfalls grounded in specific existing code paths in daemon.py, web_ui/main.py, and skip_client.py)

---

## Critical Pitfalls

### Pitfall 1: Stale Now-Playing on Fresh Page Load — state.json Has No Evaluation Result

**What goes wrong:**
The dashboard loads, reads `state.json`, and tries to show the current track. `state.json` currently contains only `last_track_id` and `family_safe_mode` — there is no `current_track_name`, `current_artist`, or `eval_state` in it. The dashboard has no track info to show until the daemon detects a track change, which may not happen for minutes if the same song is already playing.

**Why it happens:**
The daemon only writes `last_track_id` to `state.json` on track change. A user who opens the dashboard mid-song sees nothing in the now-playing card because the file does not carry human-readable track metadata or evaluation state. The web UI render path (`GET /`) injects `__FSM_INITIAL__` from `state.json` but has no parallel injection for current track.

**Consequences:**
The now-playing card shows blank or a loading state indefinitely on fresh page loads unless the user waits for the next track change. This is the default failure mode without any code change — the card will never populate on first load from the current state.json schema.

**Prevention:**
Extend `state.json` to carry current track snapshot: `{last_track_id, current_track, current_artist, eval_state, family_safe_mode}`. The daemon writes these fields on every track change alongside `last_track_id`. The web UI `GET /` endpoint injects them into the template the same way it already injects `__FSM_INITIAL__`. The fields default to `null` / `"idle"` when nothing is playing.

**Detection:**
- Dashboard shows empty now-playing card on page load even though music is playing
- Refreshing the page does not show the current track

**Phase to address:** v1.2 — must be addressed at the same time as the now-playing card is added; skipping this makes the card useless on fresh load

---

### Pitfall 2: Race Between Daemon Skip and Manual Skip Button — Double Skip

**What goes wrong:**
The parent clicks the manual skip button. The HTTP POST to `/skip` fires. The daemon is mid-evaluation of the same track and is about to auto-skip it too. Both skip calls execute within the same 1-second poll window. The result is two consecutive `next_track()` calls arriving at Spotify within milliseconds, skipping two songs instead of one. On Sonos via SoCo, a second UPnP `next()` while the queue is mid-transition raises a `SoCoUPnPException` error 701, which the existing fallback path logs but does not fully suppress.

**Why it happens:**
The daemon polls at 1s. The web UI manual skip endpoint and the daemon poll loop are in different processes (separate Docker containers) with no shared lock. There is no "skip in progress" flag accessible to both processes. The manual skip fires asynchronously to the daemon's current evaluation cycle.

**Consequences:**
Two songs skipped instead of one. The `consecutive_skips` counter in the daemon is incremented for the auto-skip, but the manual skip via the web UI has no access to the daemon's in-memory `consecutive_skips` counter — meaning the counter state diverges from reality. If the parent manually skips 4 more songs, the 5th auto-skip triggers the 5-skip pause at count=5 but the actual number of user-perceived skips was already 6+.

**Prevention:**
The lightest mitigation is a cooldown timestamp on the skip endpoint: write the last-manual-skip timestamp to `state.json` when a manual skip fires. The daemon reads `state.json` at the top of each track-change block (it already does `state = load_state()` on track change). If `last_manual_skip_at` is within the last N seconds (2s is sufficient given the 1s poll), the daemon suppresses its auto-skip for that track. No shared mutex needed — just a timestamp in the shared file.

Alternative: the manual skip endpoint calls the skip API and also writes a `skip_in_progress: true` flag; the daemon clears it on next track detection. The timestamp approach is simpler.

**Detection:**
- Two songs disappear from the queue after one manual skip click
- `consecutive_skips` counter resets unexpectedly or reaches 5 faster than expected
- `[SKIP_FAILED] SoCoUPnPException 701` appearing immediately after a manual skip in daemon logs

**Phase to address:** v1.2 — must be part of the manual skip implementation plan, not a later fix

---

### Pitfall 3: "Evaluating" Badge Stuck After Track Already Evaluated — No SSE Path for Eval State Updates

**What goes wrong:**
The now-playing card shows "Evaluating…" when a new track starts. The daemon evaluates and either allows or skips. If allowed, the result is currently not broadcast anywhere — `skip_events.jsonl` only receives entries when `action == "skip"`. There is no SSE event for `action == "allow"`. The badge stays "Evaluating…" forever for every track that passes — which is most of them.

**Why it happens:**
The existing SSE pipeline was designed purely for skip events. The `_file_tail()` in web_ui reads `skip_events.jsonl`; nothing writes to that file for allowed tracks. The `content_checker.check()` returns `(allow, reason, severity)` but the daemon only calls `_append_skip_event()` in the `action == "skip"` branch.

**Consequences:**
The badge never resolves to "Passed" or "No Lyrics" for the majority of songs. The parent sees "Evaluating…" permanently for safe tracks. This makes the feature useless as a confidence signal.

**Prevention:**
Emit a `track_update` SSE event type from the daemon for all evaluation outcomes, not just skips. Write to `skip_events.jsonl` with `type: "track_update"` and fields `{track, artist, eval_state: "passed" | "no_lyrics" | "instrumental" | "skipped", timestamp}`. The web UI file-tail loop already dispatches all event types to subscribers — it just needs the `track_update` type handled in the frontend JS (currently only `skip` and `five_skip_warning` are handled in `es.onmessage`).

Do not conflate `track_update` events with skip events in the Incident Log — they are different UI elements. The now-playing card listens for `track_update`; the skip feed listens for `skip`.

**Detection:**
- Badge always reads "Evaluating…" even 10 seconds after a track starts
- No entries appear in `skip_events.jsonl` for tracks that were allowed
- Frontend `es.onmessage` has no handler for `track_update` type

**Phase to address:** v1.2 — the eval state badge is the core of the now-playing card; cannot ship without this

---

### Pitfall 4: SSE Reconnection Loses the Current Track State

**What goes wrong:**
The browser's `EventSource` reconnects automatically after a network hiccup. `_file_tail()` in web_ui seeks to the end of `skip_events.jsonl` at startup — it does not replay recent events. After reconnect, the now-playing card goes blank or reverts to the initial server-rendered state (last known track from `state.json` at page load time), even though a `track_update` event occurred while the SSE connection was down.

**Why it happens:**
`_file_tail()` calls `fh.seek(0, 2)` on startup — this is correct behavior for skip history (no point replaying old skips). But for now-playing state, the current track IS relevant to any client that reconnects. The `EventSource` API reconnects using the `Last-Event-ID` header only if the server uses SSE `id:` fields, which the current implementation does not set.

**Consequences:**
After any SSE reconnect — including the brief disconnect that happens when the Docker container restarts — the now-playing card shows stale or empty state until the next track change. In the worst case (a long track) this could be several minutes.

**Prevention:**
Two complementary approaches:

1. **`GET /now-playing` endpoint:** Add a REST endpoint that returns the current track and eval state from `state.json`. The frontend calls this endpoint on SSE reconnect (`es.onerror` / `es.onopen`) to immediately refresh the card without waiting for the next SSE event. This is the simplest reliable solution.

2. **Replay the last `track_update` event:** On SSE reconnect, the client POSTs its `Last-Event-ID` or sends a reconnect signal; the server looks up the last `track_update` from `state.json` and sends it immediately. More complex; the REST approach achieves the same result more simply.

The REST approach is recommended: it also solves Pitfall 1 (fresh page load) via the same endpoint, collapsing two problems into one solution.

**Detection:**
- Now-playing card goes blank after a browser tab is backgrounded and SSE reconnects
- Restarting the web_ui container clears the card until the next track change

**Phase to address:** v1.2 — design the `/now-playing` REST endpoint at the same time as the card, not as a later fix

---

### Pitfall 5: "Evaluating" Badge Flicker on Rapid Track Changes

**What goes wrong:**
On playlist skip-throughs (user tapping next repeatedly in Spotify), the daemon detects each track change and emits `track_update` events in rapid succession. The browser receives `{track: "Song A", eval_state: "evaluating"}`, then `{track: "Song B", eval_state: "evaluating"}`, then `{track: "Song C", eval_state: "evaluating"}` within 2–3 seconds. The card flickers between track names while the "Evaluating…" spinner runs for each.

Worse: a `track_update` for Song A's final eval state (`"passed"`) may arrive after the card has already moved to Song B — because LRCLIB lyrics fetch for Song A can take 200ms–2s. The card then briefly shows "Song B — Passed" (incorrect — that was Song A's result applied to the wrong display name).

**Why it happens:**
The daemon emits eval results asynchronously after lyrics fetch completes. Track changes can outpace eval completion. The frontend applies the most recently received `track_update` event without checking whether the `track` field matches the currently displayed track.

**Consequences:**
The wrong eval state badge appears on the wrong track name. "Song B — Passed" when Song A passed but B hasn't been evaluated yet. This is visually jarring and technically incorrect.

**Prevention:**
Include `track_id` in all `track_update` SSE events. The frontend only applies an eval state update if the incoming `track_id` matches the currently displayed `track_id`. If they differ, discard the update silently. This is a version-check pattern: tag each state snapshot with the entity ID it belongs to.

On the daemon side, track the `track_id` being evaluated through the async call chain. If `last_track_id` changes between when lyrics fetch starts and when it returns, discard the result.

**Detection:**
- "Passed" badge appearing on the wrong song name after rapid skipping
- Badge shows "Passed" for 500ms before switching to "Evaluating" for the new track
- Manual test: rapidly skip 5 songs in Spotify; observe card behavior

**Phase to address:** v1.2 — include `track_id` in all events from the start; retrofitting is harder

---

### Pitfall 6: Manual Skip Endpoint Needs Spotify Auth — Web UI Container Has No Token

**What goes wrong:**
The manual skip POST endpoint (`/skip`) in the web UI container calls Spotify's `next_track()` API. The `spotipy.Spotify` instance with the OAuth token lives in the daemon container. The web UI container does not import `daemon.py` directly (they are separate Docker containers sharing only `state.json` and `data/` via bind mount). The web UI has no Spotify credentials.

**Why it happens:**
This was explicitly noted as acceptable for the existing FSM toggle (reads/writes `state.json` only — no Spotify API call needed). But a manual skip requires an actual API call to Spotify. The web UI container would need either its own spotipy client (duplicating auth setup) or a mechanism to ask the daemon to skip on its behalf.

**Consequences:**
The most natural implementation — add a `/skip` endpoint to `web_ui/main.py` that calls `sp.next_track()` — fails immediately because `sp` does not exist in that process. Attempting to import `daemon.py` to get `skip_client` would recreate the in-process import problem that was explicitly abandoned (Gap-2 fix in v1.0).

**Prevention:**
Two viable approaches:

1. **Write a "skip request" to `state.json`**: The web UI sets `{"manual_skip_requested": true}` in `state.json`. The daemon's poll loop reads this flag on each cycle (it already calls `load_state()` after track-change detection) and fires the skip, then clears the flag. This piggybacks on the existing file-based IPC pattern — consistent with Gap-2 fix precedent.

2. **Add a `/skip` endpoint to the daemon's own FastAPI or a lightweight internal HTTP endpoint**: The daemon exposes `POST /internal/skip` on localhost. The web UI proxies the manual skip request to the daemon's internal endpoint. Requires the daemon to run an HTTP server (currently it does not).

Option 1 is the lowest-friction approach given the existing architecture. It has a 1s poll latency (acceptable for a manual action) and reuses the proven file-IPC pattern. Option 2 adds an HTTP server to the daemon, which is a larger change.

**Detection:**
- `AttributeError: module 'daemon' has no attribute 'sp'` in web_ui container logs
- `NameError: name 'sp' is not defined` when the skip endpoint is first called
- Web UI container starting without Spotify credentials in `.env`

**Phase to address:** v1.2 — architectural decision (option 1 vs. option 2) must be made before implementation begins

---

### Pitfall 7: Spotify Rate Limit on Manual Skip — Compounding with Auto-Skip Traffic

**What goes wrong:**
Spotify's `POST /v1/me/player/next` endpoint is rate limited. The existing daemon already calls `GET /v1/me/player` (current playback) every 1 second — 60 calls/minute, plus the occasional `POST /next` for auto-skips. Adding a manual skip button that can be clicked rapidly by a parent (or a child who finds the dashboard) could trigger 429 responses on the skip endpoint.

The daemon already handles 429 on `current_playback()` with backoff + jitter. But the manual skip path in the web UI is a separate HTTP call that would need its own 429 handling, and the two paths do not share a rate limit budget.

**Why it happens:**
The Spotify rate limit is per-application (per `client_id`), not per-endpoint. Every API call from the same credentials counts toward the same bucket. The limit is undocumented but practically around 180 requests/30 seconds for user endpoints. At 1s polling (60/min) plus occasional skips, there is usually headroom — but rapid manual clicking can exhaust it.

**Consequences:**
Manual skip appears to fail (HTTP 204 is expected on success; 429 means failure). The parent clicks again. More 429s. The daemon's playback polling starts getting 429s too, which degrades the auto-skip detection latency. The existing backoff in daemon.py handles the daemon side, but the web UI skip path would need its own handling.

**Prevention:**
- Add a 2-second UI debounce on the skip button: disable it for 2 seconds after click, regardless of success/failure
- On 429 response from the skip endpoint, show a brief "wait a moment" message rather than silently failing
- Do not expose the skip button to children — the dashboard is parent-only but has no auth; document this
- The skip endpoint should propagate a 429 error back to the frontend as a distinct failure code

**Detection:**
- Skip button clicked rapidly produces no result and daemon logs show 429s
- Auto-skip detection latency increases after manual skip activity
- `SpotifyException(http_status=429)` in web_ui or daemon logs

**Phase to address:** v1.2 — debounce is trivial to add at button creation; add it by default

---

## Moderate Pitfalls

### Pitfall 8: Now-Playing Card Not Cleared When Playback Stops

**What goes wrong:**
Spotify playback stops (user pauses, session ends, Spotify closes). The daemon receives `result is None` or `item is None` from `current_playback()`. It logs "no playback detected" at heartbeat interval (300s default) but does NOT write anything to `skip_events.jsonl` or update `state.json` with a "not playing" signal. The now-playing card on the dashboard continues to show the last track indefinitely.

**Prevention:**
When the daemon transitions from "track playing" to "no playback", emit a `track_update` event with `eval_state: "idle"` and null track info. The frontend clears the card on receiving this. Also write `current_track: null` to `state.json` so fresh page loads also see the idle state.

**Phase to address:** v1.2 — include "idle" state transitions in the `track_update` event design

---

### Pitfall 9: Manual Skip During 5-Skip Pause State Causes Inconsistent Consecutive Skip Count

**What goes wrong:**
The daemon's `consecutive_skips` counter is in-memory in the daemon process. After a 5-skip pause, it resets to 0. If the parent manually skips via the web UI endpoint while the daemon is in mid-evaluation, the daemon's counter is not incremented (the manual skip is invisible to it). The parent could chain manual skips indefinitely without triggering the 5-skip pause guard.

**Prevention:**
If the "skip request" file-IPC approach is used for Pitfall 6, the daemon handles the actual skip call and can increment `consecutive_skips` correctly. If the web UI directly calls the Spotify API, the daemon never knows the skip happened and the counter diverges. This is another reason to prefer the file-IPC approach (daemon handles all actual skip calls) over the web UI calling Spotify directly.

**Phase to address:** v1.2 — consequence of architectural choice made for Pitfall 6; document the coupling

---

### Pitfall 10: SSE `_file_tail()` Polls Every 250ms — Adequate for Skips, Borderline for "Evaluating" State

**What goes wrong:**
The existing `_file_tail()` polling interval is 250ms — acceptable for a skip history feed where latency is not noticeable. For the "Evaluating" → "Passed" transition on the now-playing card, a 250ms polling lag means the badge transition is perceptibly delayed. An explicit track triggers within 1–2 polls (250–500ms); a lyrics fetch can take 500ms–2s, so total time from track start to badge resolution is 1–3 seconds. That's acceptable.

The concern is if the polling interval is increased by an operator (e.g., `POLL_INTERVAL_SECONDS=5`), the badge resolution lag grows to 5+ seconds — the card stays "Evaluating" noticeably too long.

**Prevention:**
No code change needed for the default case. Document that the badge resolution latency is `poll_daemon_interval + lyrics_fetch_time + file_tail_poll_interval`. Accept this as an architectural property. If sub-200ms badge transitions are ever required, the file-tail approach should be replaced with a websocket or a daemon-side HTTP push — but that is out of scope for v1.2.

**Phase to address:** v1.2 — document in code comments, no implementation change needed

---

### Pitfall 11: `state.json` Write Contention Between Daemon and Web UI

**What goes wrong:**
`state.json` is written by both the daemon (on track change) and the web UI (on FSM toggle via POST /fsm). Both use the read-merge-write pattern (not atomic rename, per the existing EBUSY decision). Adding a third write path (the manual skip request flag from Pitfall 6) introduces a third writer. Three processes writing to the same non-atomic file create a small but non-zero chance of a partial write collision under load.

**Why it happens:**
`os.replace()` fails on bind-mounted files on Linux (EBUSY) — this was established in v1.0 and the direct write pattern was adopted as the solution. The data in `state.json` is small (<200 bytes) and writes are infrequent (track changes every ~3 minutes on average), so the collision window is extremely narrow in practice. Adding a third writer does not meaningfully increase risk, but it is worth noting.

**Prevention:**
The existing pattern is accepted as-is per the PROJECT.md decision log. No change needed. If contention becomes an observable problem, the mitigation is a single-writer model (daemon owns all writes; web UI sends commands via IPC) — but this is over-engineering for the current scale.

**Detection:**
- `json.JSONDecodeError` in daemon or web UI logs on `state.json` read (indicates partial write caught mid-read)
- Track state reverting unexpectedly

**Phase to address:** Awareness only — not a new problem introduced by v1.2, but worth noting when adding a third writer

---

## Minor Pitfalls

### Pitfall 12: Frontend Handles `skip` and `five_skip_warning` Only — New Event Types Break Silently

**What goes wrong:**
`es.onmessage` in `index.html` currently handles exactly two event types: `skip` and `five_skip_warning`. Any unrecognized type is silently ignored (the catch block discards parse errors but unrecognized types fall through without action). Adding `track_update` requires explicitly adding a handler — there is no default dispatch, and forgetting it means the now-playing card never updates despite events being delivered.

**Prevention:**
When adding `track_update` event handling, also add a development-mode console.log for unhandled event types so unknown events are visible during testing. Remove or gate the log in production.

**Phase to address:** v1.2 — frontend handler must be written alongside the daemon-side event emission

---

### Pitfall 13: Album Art Requires a Separate Spotify API Call

**What goes wrong:**
The Spotify `current_playback()` response already includes album art URLs in `item.album.images[]`. No extra API call is needed — the URL is in the daemon's existing `result` object. However, the daemon currently does not write this to `state.json` or include it in any event payload. If album art is added to the now-playing card, the daemon must pass the image URL through the `track_update` event.

The pitfall: treating album art as a separate feature requiring a new Spotify API call, which would double the rate-limit cost. It is free data that is already in the response.

**Prevention:**
Include `album_art_url: track["album"]["images"][0]["url"]` (or the 64px thumbnail at index 2) in the `track_update` event payload from the daemon. No additional API call. The frontend fetches the image from Spotify's CDN directly — no proxy needed.

**Phase to address:** v1.2 — if album art is included, get it from the existing response payload, not a new API call

---

### Pitfall 14: Skip Button Visible When FSM Is Off Causes Parent Confusion

**What goes wrong:**
The manual skip button is useful when FSM is on (parent wants to skip a track the daemon missed or is still evaluating). When FSM is off, the daemon is not filtering, and the parent is presumably listening freely. A skip button is still technically functional when FSM is off (Spotify API accepts skip regardless), but it confuses the interface — the parent may not realize they're skipping just for themselves vs. for the children.

**Prevention:**
Tie the skip button's enabled state to the FSM toggle state. When FSM is off, disable (grey out) the skip button. The FSM state is already available client-side (`fsmEnabled` boolean in the existing JS). This is a UI polish decision, not a correctness requirement.

**Phase to address:** v1.2 — minor, can be deferred to end of phase

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Extending `state.json` schema for now-playing data | Daemon and web UI read `state.json` at different times — partial-write window during track change | Keep writes small; the read-merge-write pattern already mitigates this; accept the narrow race |
| Adding `track_update` events to `skip_events.jsonl` | Eval result arriving after track has changed — badge applied to wrong track | Include `track_id` in all `track_update` payloads; frontend checks before applying |
| Manual skip architecture | Web UI container has no Spotify token | Use file-IPC "skip request" pattern: web UI writes flag to `state.json`, daemon executes the skip |
| SSE reconnection | Now-playing card blanks on reconnect | Add `GET /now-playing` REST endpoint; frontend calls it on SSE `onopen` after reconnect |
| "Evaluating" badge initial state | Badge stuck "Evaluating" for allowed tracks | Daemon must emit `track_update` for ALL outcomes, not just skips |
| Fresh page load | Card blank until next track change | Inject current track state from `state.json` at render time (same pattern as `__FSM_INITIAL__`) |
| Rapid manual skip clicking | Spotify 429 rate limit, double skip | 2-second button debounce; daemon handles actual skip call to keep counter consistent |
| Skip count consistency | Manual skip invisible to daemon's `consecutive_skips` counter | Route all skips through daemon via file-IPC; web UI should not call Spotify API directly |

---

## Sources

- Codebase direct read: `daemon.py`, `web_ui/main.py`, `skip_client.py`, `web_ui/templates/index.html`, `state.json`, `docker-compose.yml` — HIGH confidence
- [Spotify Web API Rate Limits — developer.spotify.com](https://developer.spotify.com/documentation/web-api/concepts/rate-limits) — HIGH confidence (rate limit behavior for user endpoints)
- [Server-Sent Events — MDN Web Docs](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events#reconnection_time) — HIGH confidence (EventSource reconnect behavior and Last-Event-ID)
- [FastAPI StreamingResponse / SSE patterns — fastapi.tiangolo.com](https://fastapi.tiangolo.com/advanced/custom-response/) — HIGH confidence (SSE generator lifecycle)
- `.planning/PROJECT.md` — HIGH confidence (confirmed existing IPC pattern, architectural decisions, v1.2 requirements)

---
*Pitfalls research for: v1.2 now-playing card and manual skip on existing Spotify filter daemon + SSE dashboard*
*Researched: 2026-04-02*
