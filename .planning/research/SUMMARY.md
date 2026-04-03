# Project Research Summary

**Project:** Spotify Family Safe Mode — Now-Playing Card and Manual Skip
**Domain:** Real-time dashboard extension for an existing FastAPI/SSE filter daemon
**Researched:** 2026-04-02
**Confidence:** HIGH

## Executive Summary

This milestone adds two features to an already-working parental filter dashboard: a now-playing card showing current track, artist, and real-time evaluation state badge, and a manual skip button the parent can use without opening Spotify. Both features extend existing FastAPI/SSE infrastructure rather than introducing new technology. The stack is fully locked — no new PyPI dependencies are needed in either container. The core implementation pattern is additive: two new SSE event types (`track_change` and `eval_result`) written to the existing `skip_events.jsonl` file, a `now_playing.json` snapshot file for page-load hydration, and a `POST /skip` endpoint in the web UI.

The recommended architecture keeps the daemon as the primary Spotify/SoCo actor. For the manual skip, the web UI should call the Spotify API directly using a shared token cache file (already bind-mounted between containers) via a web_ui-side spotipy instance. This avoids inter-container HTTP, requires no new IPC file, and mirrors how the daemon's `SpotifySkipClient` works. The trade-off is that the daemon's in-memory `consecutive_skips` counter will not see manual skips — this must be an explicit design decision. The alternative (file-IPC where web_ui writes a skip request for the daemon to execute) preserves counter accuracy at the cost of 1s poll latency on every manual skip response.

The highest-risk pitfalls are well-understood and all preventable at design time. The three that must be built in from the start — not retrofitted — are: (1) emit `eval_result` for ALL ContentChecker outcomes (not just skips), or the badge stays "Evaluating" forever for safe tracks; (2) include `track_id` in all events and guard on it in the browser, or rapid track changes produce wrong badges on wrong tracks; (3) implement `GET /now-playing` reading `now_playing.json` at the same time as the card, not later, or the card is blank on every page load and SSE reconnect.

---

## Key Findings

### Recommended Stack

No new dependencies are introduced. The existing stack — Python 3.12, FastAPI 0.115.12, spotipy 2.26.0, vanilla JS EventSource, asyncio file-tail IPC — is sufficient for every new requirement. The `skip_events.jsonl` file-tail pattern used for skip and warning events handles the new `track_change` and `eval_result` event types transparently: `_file_tail()` in web_ui already fans out all JSON lines to all SSE subscribers regardless of event type.

The only new data artifact is `data/now_playing.json`, a single-record snapshot written by the daemon on track change and read by the web UI on `GET /now-playing`. No new Docker volumes are needed; the `./data` bind mount is already shared between both containers in `docker-compose.yml`.

**Core technologies:**
- `asyncio` (stdlib, Python 3.12): Coordinate new `_skip_command_tail()` coroutine alongside existing poll loop, if file-IPC skip approach is chosen — zero additional cost, same pattern as `_file_tail()`
- `spotipy` 2.26.0 (existing in daemon): Daemon owns all `current_playback()` calls; no new API calls or scopes required; `user-modify-playback-state` scope already present
- FastAPI 0.115.12 (existing in web_ui): `POST /skip` and `GET /now-playing` are ~10 lines each, mirroring the existing `POST /fsm` pattern
- Vanilla JS `EventSource` (browser native): Extend existing `onmessage` handler with `track_change` and `eval_result` case branches; no framework changes

### Expected Features

**Must have (table stakes):**
- Track name and artist on the now-playing card — daemon already has this data on every poll cycle via `current_playback()`
- Evaluation state badge cycling through: Evaluating → Passed / No lyrics / Skipped — the badge is the core value of this milestone
- "Evaluating" shown immediately on track change before ContentChecker runs — prevents false "Passed" display during LRCLIB fetch (100ms–2s latency)
- Badge updates to final state after ContentChecker completes — requires emitting `eval_result` for ALL outcomes (allow and skip), not only skips
- Manual skip button disabled while no track is playing, FSM is off, or a skip is in flight — prevents accidental double-skip
- `POST /skip` endpoint in web_ui — delegates to skip mechanism without duplicating Spotify OAuth
- Card hidden when playback is idle — requires an explicit idle state transition emitted by the daemon when `current_playback()` returns None
- Page-load hydration showing current track without waiting for next track change — requires `GET /now-playing` REST endpoint reading `now_playing.json`

**Should have (differentiators):**
- "No lyrics" badge distinct from "Passed" — communicates honest uncertainty vs. confirmed clean; amber vs. green badge colour
- Skip reason in the Skipped badge label ("Skipped: explicit tag" vs. "Skipped: strong language") — mirrors existing skip feed badge pattern
- Skip button disabled when FSM is off — coherent interface; manual skip only makes sense in filtering context
- `track_id` guard on `eval_result` application — prevents badge cross-contamination during rapid track changes; discard events whose `track_id` does not match the currently displayed track

**Defer (v2+):**
- Album artwork — data is already in the Spotify response (`track["album"]["images"]`), no new API call needed, but adds `<img>` load complexity; not required per PROJECT.md
- Playback progress bar — requires `progress_ms` polling or client-side timer; out of scope
- Queue / next-track display — requires separate Spotify queue API call; out of scope

### Architecture Approach

The v1.2 architecture extends the existing two-container (daemon + web_ui) system without adding services or volumes. The daemon emits two new event types to the existing `skip_events.jsonl`: `track_change` immediately on detection (with `eval_state: "evaluating"`), and `eval_result` after ContentChecker completes for all outcomes. It also writes/overwrites `data/now_playing.json` at both points as a snapshot for page-load hydration. The web_ui adds `GET /now-playing` (reads `now_playing.json`) and `POST /skip` (calls Spotify API directly or writes a skip request file for the daemon). The browser receives all real-time updates through the existing `/events` SSE channel with two new event type handlers added to `onmessage`.

**Major components:**
1. `daemon.py` (modified) — emits `track_change` and `eval_result` events; writes `now_playing.json` at both points; optionally handles `skip_commands.jsonl` if file-IPC skip approach is chosen
2. `web_ui/main.py` (modified) — adds `GET /now-playing` and `POST /skip` endpoints; optionally initializes a spotipy instance for direct Spotify skip calls
3. `web_ui/templates/index.html` (modified) — now-playing card HTML; badge state machine in JS; manual skip button; `track_change` and `eval_result` SSE handlers; `track_id` guard
4. `data/now_playing.json` (new file) — single-record snapshot for page-load hydration and SSE reconnect recovery; written only by daemon via `os.replace()`-safe pattern
5. `data/skip_events.jsonl` (extended) — existing file; new event types are additive; `_file_tail()` requires no change to pass them through

### Critical Pitfalls

1. **"Evaluating forever" for allowed tracks** — `_append_skip_event()` is currently called only in the `action == "skip"` branch. Emitting `eval_result` for allowed tracks is not optional — without it, the badge never resolves to "Passed" or "No lyrics" for the majority of songs that pass the filter.

2. **Stale card on page load and SSE reconnect** — `state.json` does not carry track metadata or eval state. Without a `GET /now-playing` endpoint reading `now_playing.json`, the card is blank on fresh load and after SSE reconnection. This endpoint must be designed with the card, not added later.

3. **Double skip from concurrent manual and auto-skip** — Manual skip via web UI and an auto-skip from ContentChecker can both fire within the same 1s poll window. Mitigate with a 2-second button debounce and a cooldown timestamp in `state.json` (daemon checks `last_manual_skip_at` before executing an auto-skip for the same track). File-IPC approach eliminates this by design: only the daemon executes skip calls.

4. **Badge cross-contamination on rapid track changes** — An `eval_result` for Song A can arrive while the card displays Song B (LRCLIB fetch takes 200ms–2s). Include `track_id` in all `track_change` and `eval_result` events; browser discards updates where `evt.track_id !== currentTrackId`.

5. **Manual skip auth gap: web_ui has no Spotify token by default** — The daemon owns the authenticated `spotipy.Spotify` instance. Resolution: web_ui instantiates its own spotipy using the same `.env` credentials and shared token cache bind-mount (`./token_cache:/app/token_cache` already in `docker-compose.yml`). Alternative: file-IPC skip request written to `data/skip_commands.jsonl`; daemon reads and executes it. File-IPC preferred if `consecutive_skips` counter accuracy is required.

---

## Implications for Roadmap

This milestone maps to a single cohesive delivery with two natural implementation phases ordered by data flow: daemon-side event emission first, then web UI consumption. Both phases are small. The critical pre-implementation step is resolving the manual skip architecture decision before any code is written.

### Phase 0: Architecture Decision — Manual Skip IPC

**Rationale:** This is not an implementation phase but a required decision point. The manual skip IPC approach (direct spotipy in web_ui vs. file-IPC through daemon) affects both the daemon code (Phase 1 adds `_skip_command_tail()` if file-IPC) and the web_ui code (Phase 2 adds spotipy init if direct call). Coding either container before this decision wastes rework.

**Delivers:** A recorded decision in PROJECT.md: direct spotipy (simpler, <1s response, counter diverges) or file-IPC (1s poll latency, counter stays accurate). Recommendation is direct spotipy unless consecutive-skip accuracy is a stated requirement.

**Avoids:** Pitfall 6 (missing auth), Pitfall 9 (consecutive skip counter divergence).

### Phase 1: Daemon IPC Extensions

**Rationale:** The daemon is the data-producing end. Every UI feature depends on the events it emits and the `now_playing.json` snapshot it writes. Nothing in the browser or web_ui backend can be tested end-to-end without this phase complete.

**Delivers:**
- `track_change` event emitted immediately on track detection (before ContentChecker), with `track_id`, track name, artist, and `eval_state: "evaluating"`
- `eval_result` event emitted after ContentChecker for ALL outcomes (allow and skip), with `track_id` and final `eval_state`
- `now_playing.json` written at both points (evaluating state on detection, final state after check)
- Idle event emitted when `current_playback()` returns None
- `_skip_command_tail()` coroutine (only if file-IPC approach is chosen in Phase 0)

**Addresses features:** Evaluation state badge, track display, idle card clearing, badge cross-contamination guard
**Avoids:** Pitfall 3 (evaluating forever), Pitfall 5 (badge cross-contamination), Pitfall 8 (card not cleared on stop)

### Phase 2: Web UI Backend and Frontend

**Rationale:** Depends on Phase 1 event schemas being locked. Can be designed in parallel with Phase 1 but requires Phase 1 running for end-to-end testing. All changes in this phase are consumers of Phase 1 outputs.

**Delivers:**
- `GET /now-playing` endpoint reading `now_playing.json` — solves page-load hydration and SSE reconnect blanking
- `POST /skip` endpoint (direct spotipy call or file-IPC write, per Phase 0 decision)
- Now-playing card HTML skeleton with evaluation state badge
- Badge state machine in JS: handles `track_change` (show card, set badge to Evaluating), `eval_result` (update badge if `track_id` matches), idle event (hide card)
- `track_id` guard in JS discarding stale eval results
- Manual skip button: 2-second debounce, disabled when FSM is off or no track playing, error feedback on failure, pending state during request
- On-load hydration via `GET /now-playing`; re-hydrate on SSE `onopen` (reconnect recovery)

**Uses:** FastAPI `StreamingResponse` SSE pattern (existing), `SpotifySkipClient` or file-IPC (per Phase 0), `.card` and `.badge` CSS classes (existing)
**Avoids:** Pitfall 1 (stale page load), Pitfall 2 (double skip), Pitfall 4 (SSE reconnect blank), Pitfall 7 (rate limit), Pitfall 12 (silent unhandled event types)

### Phase Ordering Rationale

- Phase 0 is a decision, not code, but it gates both subsequent phases. Document it first.
- Phase 1 before Phase 2 because the browser cannot display what the daemon has not emitted. Event field names and `track_id` inclusion must be locked before Phase 2 builds consumers.
- Both phases are small enough to implement in a single session each. No intermediate releases are required between them.
- Steps within Phase 1 (daemon changes) and within Phase 2 (web_ui backend vs. frontend) are independent of each other and can be built in either order within the phase.

### Research Flags

Needs deeper research during planning:
- **Phase 0 (skip IPC decision):** Review PROJECT.md decision log for any prior ruling on `consecutive_skips` accuracy requirements. The research identifies two valid options with a clear tradeoff; the decision depends on whether the 5-skip pause guard is a hard behavioral contract or a best-effort heuristic.

Phases with standard patterns (skip research-phase):
- **Phase 1 (daemon event emission):** Fully documented. `_append_skip_event()` pattern already in production; extending it with new event types and `now_playing.json` writes is mechanical.
- **Phase 2 (web UI endpoints + frontend):** Both new endpoints mirror existing patterns (`POST /fsm`, `_file_tail`). Badge state machine is fully specified in FEATURES.md state diagram. No novel architecture.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All research grounded in direct codebase inspection; no new dependencies means zero version or compatibility risk |
| Features | HIGH | Feature set derived from code inspection and PROJECT.md v1.2 requirements; evaluation state machine fully specified with all transition cases |
| Architecture | HIGH | IPC patterns confirmed from running production code; token cache sharing confirmed from docker-compose.yml; EBUSY write constraint documented in PROJECT.md decision log |
| Pitfalls | HIGH | All pitfalls traced to specific existing code paths with line-level analysis; rate limit behavior sourced from official Spotify docs |

**Overall confidence:** HIGH

### Gaps to Address

- **Manual skip architecture decision (Phase 0):** Research presents two valid options with clear tradeoffs. The choice between direct spotipy in web_ui (simpler, no poll latency) and file-IPC through daemon (counter-accurate, 1s latency) must be recorded in PROJECT.md before implementation begins. This is the only unresolved design question.

- **`now_playing.json` vs. `state.json` schema extension:** PITFALLS.md suggests extending `state.json` for hydration; ARCHITECTURE.md recommends a separate `now_playing.json`. Both carry the same data. The separate file approach is cleaner (avoids polluting the FSM state file with transient track metadata) and is the recommended choice — but it must be consistent across Phase 1 and Phase 2.

- **Token cache concurrent write race (informational):** Two processes sharing the token cache file creates a narrow race on concurrent token refresh. Research assesses this as low risk (60-minute token validity, infrequent refresh). No mitigation needed, but the `SPOTIFY_CACHE_PATH` env var must be set correctly in the web_ui container before deployment. Verify this in `docker-compose.yml` before Phase 2 testing.

---

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection: `daemon.py`, `web_ui/main.py`, `skip_client.py`, `content_checker.py`, `web_ui/templates/index.html`, `docker-compose.yml`, `state.json` — all research grounded in actual code; no inference from documentation alone
- `.planning/PROJECT.md` — v1.2 milestone requirements, Gap-2 fix rationale, architectural decision log, EBUSY write constraint
- [FastAPI StreamingResponse docs](https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse) — SSE via StreamingResponse pattern
- [spotipy current_playback docs](https://spotipy.readthedocs.io/en/2.26.0/#spotipy.client.Spotify.current_playback) — response structure including `album.images`
- [MDN EventSource](https://developer.mozilla.org/en-US/docs/Web/API/EventSource) — browser SSE API, `onopen` reconnect behavior, `Last-Event-ID` header

### Secondary (MEDIUM confidence)
- Spotify Web API rate limits — practical limit assessed at ~180 requests/30s for user endpoints; official documentation confirms existence of limits without publishing exact values
- LRCLIB and SoCo latency values (100ms–2s lyrics fetch, 200ms–1.5s SoCo skip) — from project retrospective notes, not measured in current v1.2 context

---

*Research completed: 2026-04-02*
*Ready for roadmap: yes*
