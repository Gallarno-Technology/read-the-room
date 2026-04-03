# Feature Research: Now-Playing Card and Manual Skip (v1.2)

**Domain:** Real-time now-playing dashboard card with evaluation state badge and manual skip control in a family-filter parental dashboard
**Researched:** 2026-04-02
**Confidence:** HIGH — based on direct code inspection of the v1.1 codebase combined with first-principles UI analysis. No external libraries required; patterns derived from existing SSE infrastructure.

---

## Scope

This file is narrowly scoped to the two new features for v1.2:

1. **Now-playing card** — current track name, artist, and real-time evaluation state badge (evaluating → passed / no-lyrics / skipped)
2. **Manual skip button** — triggers a skip from the web UI without opening Spotify

The existing skip feed, FSM toggle, warning banner, and five-consecutive-skip pause logic are already built and remain unchanged.

---

## Evaluation State Machine

The evaluation state is the conceptual heart of this milestone. Getting the state machine right before writing any code is critical.

### States

| State | Display Label | When It Applies |
|-------|---------------|-----------------|
| `evaluating` | Evaluating... | Track has changed; ContentChecker.check() is in progress (lyrics fetching or profanity scanning) |
| `passed` | Passed | ContentChecker returned action="allow" with reason="clean" |
| `no_lyrics` | No lyrics | ContentChecker returned action="allow" with reason="lyrics_unavailable" or reason="instrumental" |
| `skipped` | Skipped | ContentChecker returned action="skip" (any reason) and the track was actually skipped |
| `fsm_off` | (no badge) | Family Safe Mode is off; evaluation does not run; no badge shown |
| `idle` | (no card) | No track currently playing; nothing to display |

### State Transition Diagram (UI perspective)

```
[idle: no playback]
    │  Spotify reports a playing track
    ▼
[evaluating: new track detected]
    │  FSM is OFF
    ├──────────────────────────────────→ [no_badge: FSM off — show track, no evaluation badge]
    │
    │  FSM is ON
    │  ContentChecker.check() completes
    ├── action="allow", reason="clean"        → [passed]
    ├── action="allow", reason="instrumental" → [no_lyrics]
    ├── action="allow", reason="lyrics_unavailable" → [no_lyrics]
    └── action="skip"                         → [skipped]
         │
         │  Next track starts (daemon detects track_id change)
         └──────────────────────────────────→ [evaluating: new track]
```

### Key Constraint: "Evaluating" is Always Initial

PROJECT.md states explicitly: "Evaluating is always the initial state on every new track — Spotify/Sonos API latency means no instant result is reliable."

This has concrete implications:
- The now-playing card must not show "Passed" before evaluation completes. Even if the previous track passed, the new track starts at "Evaluating".
- LRCLIB fetch + profanity scan takes 100ms-2s depending on cache state. The badge must reflect this gap honestly rather than jumping to an optimistic result.
- On an explicit track, the daemon skips immediately (Tier 1, no lyrics fetch). The "Evaluating" state may only flash briefly before transitioning to "Skipped". This is correct behaviour, not a bug.

### What Drives State Transitions

The daemon currently emits two SSE event types: `skip` and `five_skip_warning`. A third event type is needed:

```
"now_playing" event (NEW):
{
    "type": "now_playing",
    "track": "Song Title",
    "artist": "Artist Name",
    "track_id": "spotify:track:...",
    "state": "evaluating" | "passed" | "no_lyrics" | "skipped",
    "reason": "clean" | "instrumental" | "lyrics_unavailable" | "explicit" | "profanity" | null,
    "timestamp": "14:32:07"
}
```

This event is emitted by the daemon at two moments per track:
1. **On track change detected:** `state="evaluating"` (before ContentChecker runs)
2. **On evaluation complete:** `state="passed"` | `state="no_lyrics"` | `state="skipped"` (after ContentChecker.check() returns)

Emitting two events per track change means the UI correctly shows "Evaluating..." while the daemon fetches lyrics, then snaps to the final state. This is the minimal change to the existing IPC contract.

---

## Table Stakes

Features users expect. Missing = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Track name and artist on now-playing card | Parents need to know what is playing without opening Spotify | LOW | Daemon already has track["name"] and track["artists"][0]["name"] on every poll cycle |
| Evaluation state badge | Core value of the milestone per PROJECT.md; without it the card is just a track name | LOW | New "now_playing" SSE event type; badge updated in JS on event receipt |
| "Evaluating" shown while evaluation is in progress | PROJECT.md mandates this as always-initial; it prevents the UI from showing a false "Passed" while lyrics are fetching | LOW | Emit now_playing(state="evaluating") on track change before awaiting content_checker.check() |
| Badge updates when evaluation completes | Evaluation result must be reflected in the card | LOW | Emit now_playing(state=final_state) after ContentChecker returns |
| Card clears / shows idle state when nothing is playing | Otherwise the card shows stale track info after playback ends | LOW | Poll `/status` endpoint on load OR emit a "playback_stopped" event when Spotify returns 204 |
| Manual skip button | PROJECT.md v1.2 target; parent can skip without opening Spotify | MEDIUM | New POST /skip endpoint in web_ui; endpoint delegates to daemon via shared state mechanism |
| Skip button disabled while no track is playing | Clicking skip with nothing playing is an error; button should reflect system state | LOW | JS disables button when card is in idle state |
| Skip button disabled or shows pending state while skip in flight | Prevent double-submit; skip takes 200-800ms via SoCo SSDP | LOW | Disable button during fetch; re-enable after response |

---

## Differentiators

Features that set this product apart. Not expected, but valued.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| "No lyrics" badge distinct from "Passed" | Parent understands that LRCLIB couldn't find lyrics and the track was allowed by policy (FILT-05), not because it was clean | LOW | Two separate badge styles: green for "Passed", amber/grey for "No lyrics" — communicates honest uncertainty |
| Skip button disabled when FSM is off | Makes the parent mode / filtering state visually coherent — manual skip only makes sense in the context of family filtering | LOW | Read FSM state on card render; disable skip button when fsm_off |
| Card persists after skip with "Skipped" state briefly | After a skip, the card shows the skipped track's name and "Skipped" badge for 1-2 seconds before updating to the next track. This confirms to the parent that the skip fired. | LOW | "Skipped" state displayed until next now_playing(state="evaluating") event arrives |
| Reason visible in skipped badge tooltip or secondary line | When state="skipped", showing reason="explicit" vs reason="profanity" helps parent understand filter behaviour | LOW | Badge text can include reason: "Skipped: explicit tag" vs "Skipped: strong language" — mirrors existing skip feed badge pattern |
| Album artwork (nice-to-have) | Visual polish; confirms parent is looking at the right track | MEDIUM | Spotify track object already contains `album.images[0].url` (640px), `[1].url` (300px), `[2].url` (64px). The 64px or 300px thumbnail fits a card layout. Requires no new API call — artwork URL is in the already-fetched track object. Not required per PROJECT.md but trivially achievable if desired. |

---

## Anti-Features

Features to explicitly NOT build for this milestone.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Playback progress bar | A progress bar requires either Spotify polling for `progress_ms` on every cycle (adds complexity to daemon) or a client-side timer synchronized to a start timestamp (brittle when paused). The now-playing card does not need to behave like a Spotify client. | Show track name and state; no progress. If progress is desired later, add progress_ms to the now_playing event and animate client-side |
| Queue / next-track display | Requires Spotify's queue endpoint which is a separate API call not currently made; adds polling load and surface area | Stick to current track only; PROJECT.md explicitly says "Current track only — existing skip feed history unchanged" |
| Playback controls (play/pause/previous) | Adds significant surface area and auth concerns; transforms a monitoring dashboard into a playback remote | Keep the manual skip as the single action. Play/pause already available in Spotify or on Sonos app. |
| Optimistic UI state (show "Passed" before evaluation) | Tempting to use the previous track's result to pre-populate the new track's badge. Always wrong — a new track may be explicit even if the last one was clean. | Always start at "Evaluating" per PROJECT.md |
| Instant skip without debounce | Parent could accidentally double-tap. A skip that fires twice moves the track forward twice. | Disable the button during the skip request (see table stakes). 1-2s disable window is sufficient. |
| Auto-refresh polling as alternative to SSE for now-playing state | Page-level polling (setInterval fetch /status) is less real-time than SSE and adds unnecessary server load | Use the existing SSE connection for all now-playing events; SSE is already established and connected |
| Storing current track in state.json for web_ui to read | state.json is a write-heavy file read by both daemon and web_ui; adding current track info creates read/write contention and inconsistency | Daemon emits now_playing events via skip_events.jsonl (same IPC path); web_ui reads via existing file-tail |

---

## Feature Dependencies

```
Now-playing card (new)
    └──requires──> "now_playing" SSE event type from daemon (new)
    └──requires──> daemon emits evaluating event before await content_checker.check()
    └──requires──> daemon emits final state event after content_checker.check() returns
    └──requires──> web_ui SSE handler updated to process "now_playing" event type
    └──uses──> existing SSE infrastructure (/events endpoint, _file_tail, _subscribers)
    └──uses──> existing skip_events.jsonl file-based IPC

Evaluation state badge (new — part of now-playing card)
    └──requires──> "now_playing" event carries state field
    └──requires──> now_playing event with state="evaluating" fired on track change
    └──requires──> now_playing event with state=final_state fired after check()
    └──reads──> reason field for badge label differentiation (explicit vs profanity)

Manual skip button (new)
    └──requires──> POST /skip endpoint in web_ui/main.py (new)
    └──requires──> daemon exposes a skip mechanism the web_ui can invoke
    └──CONSTRAINT──> web_ui cannot call Spotify API directly (no auth token in web_ui)
    └──CONSTRAINT──> web_ui cannot call SoCo directly (no device context in web_ui)
    └──uses──> state.json as IPC: web_ui writes {"manual_skip_requested": true, "manual_skip_device_id": "..."}
    └──requires──> daemon's poll_loop checks for manual_skip_requested flag each cycle
    └──OR alternative──> dedicated skip_request.json file as cleaner IPC channel

Manual skip IPC options (choose one):
    Option A — state.json flag: simplest; reuses existing read/write pattern;
               daemon clears flag after acting; web_ui sets flag; no new files
    Option B — skip_request.json: separate concern; cleaner; avoids polluting
               state.json with transient request state; easy to tell if a request
               is stale (check timestamp vs current time); preferred for clarity
    Option C — in-process HTTP (web_ui calls daemon on localhost): requires daemon
               to expose its own HTTP server; significant new surface area; NOT
               recommended (violates current architecture — two Docker services)

Note on device context for manual skip:
    The daemon knows which device is active (from Spotify API `result["device"]` in
    poll_loop). The web_ui does not have device info. The IPC message for manual skip
    need only say "skip now" — the daemon reads current device from its own poll_loop
    context. The web_ui does NOT need to specify a device_id in the skip request.
    The daemon acts on the most recently known active device when it processes the request.

Idle state handling (new)
    └──requires──> daemon emits "playback_stopped" event type when Spotify returns
                   result=None (no active playback)
    └──OR alternative──> web_ui treats absence of now_playing events for N seconds as idle
    └──recommendation──> emit explicit "playback_stopped" event; avoids false idle on
                         temporary network hiccup vs actual stop
```

### Dependency Notes

- **No new Spotify API calls required:** The track name, artist, and album artwork URL are all present in the existing `sp.current_playback()` response. No new scopes or endpoints needed.
- **SSE infrastructure is the right channel for now-playing events:** The file-tail + subscriber broadcast pattern already in place handles now_playing events transparently. The only change is a new event type in daemon.py and a new handler in index.html.
- **Manual skip requires IPC between two Docker containers:** web_ui and daemon run as separate services sharing the ./data volume mount. skip_request.json (Option B) is the cleanest choice: no changes to state.json schema, easy to detect stale requests by timestamp comparison, daemon clears it on action.
- **Album artwork is free if wanted:** `track["album"]["images"][1]["url"]` (300px thumbnail) is in the existing Spotify response. Adding artwork to the now_playing event costs zero extra API calls. The decision is purely UI complexity — whether to add an `<img>` to the card layout.
- **Card is a new DOM section, not a modification of existing sections:** The existing HTML has FSM card + incident log card. The now-playing card is a third card, inserted between the FSM card and the incident log. This avoids any disruption to existing layout.

---

## MVP Definition

### Launch With (v1.2)

- [ ] `now_playing` SSE event type emitted by daemon.py at two points per track change:
  1. Before `await content_checker.check(track)` — `state="evaluating"`
  2. After `content_checker.check()` returns — `state="passed"` | `state="no_lyrics"` | `state="skipped"`
- [ ] `playback_stopped` SSE event type emitted when `sp.current_playback()` returns None (no active playback)
- [ ] Now-playing card in index.html:
  - Track name and artist (large, readable)
  - Evaluation state badge: Evaluating... / Passed / No lyrics / Skipped
  - Badge colour: neutral/spinning for evaluating, green for passed, amber for no_lyrics, red for skipped
  - Card hidden when idle (no playback)
  - Badge label includes reason for "Skipped" state: "Skipped: explicit tag" or "Skipped: strong language"
- [ ] Manual skip button:
  - Visible on the now-playing card
  - Disabled when FSM is off, disabled when no track is playing, disabled during skip-in-flight
  - Sends POST /skip to web_ui
  - Shows error text for 3s on failure (mirrors FSM toggle error pattern)
- [ ] POST /skip endpoint in web_ui/main.py:
  - Writes skip_request.json with `{"requested": true, "timestamp": "..."}` to shared data volume
  - Returns 200 immediately (fire-and-forget from web_ui perspective)
  - Returns 409 if a request is already pending (avoids duplicate requests)
- [ ] daemon.py poll_loop modified:
  - Checks for skip_request.json each cycle; if found and fresh (< 5s old), executes skip using existing client selection logic (SoCo or Spotify API based on is_restricted)
  - Clears skip_request.json after acting
  - Logs `[MANUAL_SKIP]` at INFO level
  - Does not count manual skip toward consecutive_skips counter (parent-initiated skip; no need to trigger the 5-skip pause warning)

### Omit from v1.2

- [ ] Album artwork — PROJECT.md designates this nice-to-have; adds `<img>` load logic but no new API calls; defer to avoid scope creep
- [ ] Progress bar — defer indefinitely
- [ ] Queue display — out of scope per PROJECT.md

---

## Existing Infrastructure Reused (No Changes Required)

| Component | What It Provides | Change Needed |
|-----------|-----------------|---------------|
| `skip_events.jsonl` | File-based IPC channel from daemon to web_ui | Add two new event types (now_playing, playback_stopped) — additive |
| `_file_tail()` in web_ui | Tails skip_events.jsonl and broadcasts to SSE subscribers | None — new event types pass through transparently |
| `/events` SSE endpoint | Streams events to browser | None — new event types arrive in the same stream |
| `es.onmessage` in index.html | Routes events to handlers by type | Add `now_playing` and `playback_stopped` case branches |
| `_append_skip_event()` in daemon | Writes to skip_events.jsonl | Reuse as-is for now_playing and playback_stopped events |
| `state.json` read-merge-write pattern | Cross-process state | Reuse for fsm state check in POST /skip to gate the skip |
| `.card` CSS class | Card layout with dark theme | Reuse for now-playing card — no new CSS needed for the card container |
| `.badge` CSS classes | Reason badges in incident log | Reuse for evaluation state badge — add two new badge variants (evaluating, no_lyrics) |

---

## State Machine — UI Edge Cases

| Edge Case | What Happens | Correct Behaviour |
|-----------|-------------|-------------------|
| Track changes while badge shows "Evaluating" | A second now_playing(state="evaluating") arrives | Overwrite with new track name/artist; badge stays Evaluating (still waiting for new track evaluation) |
| Track changes before evaluation completes (e.g., user manually skips in Spotify) | new track_id detected on next poll; evaluating event for the new track arrives before the old track's result arrives | Evaluation result for the old track arrives but is stale — daemon should include track_id in the event so the UI can discard results for non-current tracks |
| Manual skip button pressed while auto-skip is in progress | Both skip mechanisms fire near-simultaneously; Spotify or SoCo may get two skip requests 1s apart | The manual skip's skip_request.json will be picked up on the next poll_loop iteration; since the auto-skip already moved the track, the daemon should detect that track_id has changed and skip the pending manual skip request as stale |
| FSM toggled off while badge shows "Evaluating" | No evaluation result will arrive; badge is stuck | When FSM state change is received via SSE (or re-read on /fsm endpoint), hide or mute the evaluation badge |
| No playback (result=None) on page load | Card should not show stale track info from a previous session | Card starts hidden; only shows when a now_playing event is received in the current session |
| LRCLIB takes >3s to respond (slow API) | "Evaluating" badge sits for 3+ seconds | Correct — the badge correctly communicates that evaluation is in progress. No timeout-based fallback needed for v1.2. |

---

## Competitor Feature Analysis (Family Filter / Parental Control Dashboards)

| Feature | Spotify (built-in) | Circle Home | Amazon Parent Dashboard | This Project |
|---------|-------------------|-------------|------------------------|--------------|
| Now playing display | In Spotify app only | No | No (music not tracked) | New card in web dashboard |
| Filter evaluation state | Not shown | Not shown | Not shown | Evaluation badge (new in v1.2) |
| Manual skip from filter UI | No | No | No | Manual skip button (new in v1.2) |
| Skip reason transparency | Not shown | Not shown | Not shown | Badge label with reason |
| Real-time update | App only | App only | Poll-based | SSE (existing infrastructure) |

Observation: No existing family filter product exposes a real-time evaluation state badge. The "Evaluating → Passed / Skipped" UX pattern is novel for this domain. The closest analogy in other domains is build pipeline status indicators (e.g., GitHub Actions running → passed / failed), which shows the pattern is well-understood and trusted by users when the states are clear.

---

## Sources

- Direct code inspection: `daemon.py` poll_loop, `content_checker.py`, `web_ui/main.py`, `web_ui/templates/index.html`, `skip_client.py` — HIGH confidence
- Existing IPC design: `data/skip_events.jsonl` file-based IPC pattern with `_file_tail()` — HIGH confidence
- Project requirements: `.planning/PROJECT.md` v1.2 milestone section — HIGH confidence
- State machine design: first-principles derivation from ContentChecker return values and daemon action/reason tuple — HIGH confidence
- Manual skip IPC options: analysis of existing Docker-compose architecture (two-service, shared data volume, network_mode: host) — HIGH confidence
- UI edge cases: derived from observed timing characteristics of 1s poll cycle, LRCLIB latency (~100ms cached, ~500ms cold), and Sonos UPnP skip latency (~200ms cached IP, ~1.5s SSDP discovery) — MEDIUM confidence (latency values from project retrospective notes, not measured in v1.2 context)

---

*Feature research for: now-playing card with evaluation state badge and manual skip button — v1.2 milestone*
*Researched: 2026-04-02*
