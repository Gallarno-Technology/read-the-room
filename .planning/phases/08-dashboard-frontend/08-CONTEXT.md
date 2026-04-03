# Phase 8: Dashboard Frontend - Context

**Gathered:** 2026-04-03 (assumptions mode)
**Status:** Ready for planning

<domain>
## Phase Boundary

The browser dashboard gains a now-playing card: current track name, artist, album artwork, an eval-state badge that updates in real-time, and a manual skip button. Card hydrates from `GET /now-playing` on page load and after SSE reconnect; live updates arrive via the existing SSE `track_change` and `eval_result` events from Phase 6.

Covers: NOW-01, NOW-02, NOW-03, NOW-04, NOW-05, NOW-06, NOW-07, SKIP-01, SKIP-04.
Does NOT cover: new backend endpoints (done in Phase 7), daemon changes, skip counter logic, CSS framework or build tooling.
</domain>

<decisions>
## Implementation Decisions

### Card Layout and Placement

- **D-01:** The now-playing card is inserted between the FSM toggle card and the Incident Log card — not at the top or bottom. Hierarchy: global control (FSM) → current action (now playing + skip) → history (incident log).
- **D-02:** Card structure (inline in `index.html`, no separate file):
  - Album art `<img>` (64×64 or similar), floated or flex-adjacent to track info
  - Track name + artist on two lines
  - Eval-state badge (`.badge` + modifier class)
  - Skip `<button>` below the track info
  - Empty/idle state: show placeholder text ("Nothing playing") with skip button hidden when `data.status === "idle"`.

### Page-Load Hydration (NOW-04, NOW-05)

- **D-03:** On `DOMContentLoaded`, call `GET /now-playing` once. If `data.status === "idle"`, show the idle placeholder. Otherwise render card with full track data.
- **D-04:** On SSE `onopen` (including reconnects), re-call `GET /now-playing` to repopulate the card. This handles NOW-05: after reconnect the card shows current state rather than going blank. The same idle-check applies.
- **D-05:** No polling. SSE `track_change` and `eval_result` events drive all in-session updates after hydration.

### SSE Event Routing (NOW-02, NOW-03, NOW-07)

- **D-06:** `track_change` event → update the card: set track name, artist, album art, reset badge to `eval_state: "evaluating"`. This is the NOW-03 signal: badge shows "Evaluating" the instant a new track starts.
- **D-07:** `eval_result` event → update badge ONLY if `evt.track_id === currentTrackId` (NOW-07 guard). If `track_id` doesn't match (stale result from a rapid skip), ignore silently.
- **D-08:** Both event types already arrive via the existing `es.onmessage` handler in `index.html`. The handler currently routes `skip` and `five_skip_warning` by `evt.type`; add `track_change` and `eval_result` cases to the same switch/if-else.

### Eval-State Badge Rendering

- **D-09:** New CSS modifier classes alongside existing feed badge classes (which remain untouched):
  - `.badge--evaluating` — amber/muted (evaluating state, result unknown)
  - `.badge--passed` — green (track cleared all filters)
  - `.badge--no-lyrics` — grey (no lyrics found, no skip)
  - `.badge--skipped` — red (auto-skipped by daemon)
  - `.badge--paused` — orange (5th consecutive skip, playback paused)
  - `.badge--fsm-off` — faint/dim (FSM disabled, no evaluation ran)
- **D-10:** Badge label text (human-readable):
  - `evaluating` → "Checking…"
  - `passed` → "Passed"
  - `no-lyrics` → "No lyrics"
  - `skipped` → "Skipped"
  - `paused` → "Paused"
  - `fsm-off` → "Monitoring off"
- **D-11:** A `currentTrackId` variable (module-level in the JS) stores the track_id of the currently displayed track. Set on `track_change` events and on hydration from `GET /now-playing`. Used for the NOW-07 guard in `eval_result` handling.

### Skip Button (SKIP-01, SKIP-04)

- **D-12:** Skip button is a `<button>` element inside the now-playing card. Hidden (or `display:none`) when `data.status === "idle"`, visible when a track is playing.
- **D-13:** On click: set `button.disabled = true` immediately (SKIP-04). Call `POST /skip`. Re-enable (`button.disabled = false`) when the fetch settles (success or error).
- **D-14:** On 503 response (`{"detail":"skip_failed"}`), show a brief inline error message below the button — same pattern as `#fsm-error` in the FSM card. Clear it after 3 seconds.
- **D-15:** On success (`{"ok":true}`), no special UI response needed. The next `track_change` SSE event will update the card naturally as the daemon detects the new track.

### Album Art (NOW-06)

- **D-16:** `<img>` element with `src` set from `album_art_url` field in `track_change` events / `GET /now-playing` response. If `album_art_url` is `null`, hide the img element (or show a placeholder). No external CDN dependency — the URL comes directly from Spotify's image CDN, already stored in the event.

### Claude's Discretion

- Exact CSS sizing for album art (suggested: 64px square with `border-radius: 4px`)
- Whether to use CSS flex or inline-block for art + track info layout
- Exact placeholder text for idle state and for null album art
- Animation for badge state transitions (can reuse existing `.feed-new` fadeIn or none)
- Whether to add a `aria-live` region for the now-playing card for accessibility
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §v1.2 Now Playing Display — NOW-01 through NOW-07 success criteria
- `.planning/REQUIREMENTS.md` §v1.2 Manual Skip — SKIP-01, SKIP-04 success criteria
- `.planning/ROADMAP.md` §Phase 8 — 5 success criteria (hydration, badge real-time, SSE reconnect, track_id guard, skip button in-flight disable)

### Existing frontend (modify this file)
- `web_ui/templates/index.html` — single-file dashboard; all CSS and JS are inline; no build step; add now-playing card between FSM toggle card and incident log card

### Backend contracts (read-only for Phase 8)
- `.planning/phases/07-web-ui-backend/07-CONTEXT.md` §GET /now-playing — idle sentinel `{"status":"idle"}`, full now_playing.json passthrough
- `.planning/phases/07-web-ui-backend/07-CONTEXT.md` §POST /skip — `{"ok":true}` on success, HTTP 503 `{"detail":"skip_failed","reason":"..."}` on error

### Event schemas (read-only for Phase 8)
- `.planning/phases/06-daemon-sse-extensions/06-CONTEXT.md` §D-04 — `track_change` event schema (track_id, track, artist, album_art_url, eval_state:"evaluating")
- `.planning/phases/06-daemon-sse-extensions/06-CONTEXT.md` §D-05 — `eval_result` event schema (track_id, eval_state)
- `.planning/phases/06-daemon-sse-extensions/06-CONTEXT.md` §D-02 — complete eval_state vocabulary

### Existing UI patterns to follow
- `web_ui/main.py` — `dashboard()` route; template var `__FSM_INITIAL__` pattern; FSM and SSE route implementations for reference
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `.badge` base class + modifier classes (`.badge--explicit`, `.badge--profanity`, `.badge--adult`, `.badge--approved`) — base class CSS reused; new modifier classes added in same style
- `setBadgeClass()` / `badgeLabel()` JS functions — pattern to replicate for eval_state badge mapping
- `#fsm-error` div + `setTimeout(..., 3000)` pattern — reuse for skip button error display
- `es.onmessage` event router — add `track_change` and `eval_result` branches to existing if-else chain
- `.feed-new` CSS animation (fadeIn) — optionally reuse for badge state transitions

### Established Patterns
- All fetch calls: async function, optimistic update before fetch, revert + error text on failure, clear error after 3s
- `es.onopen` / `es.onerror` already set SSE dot status; re-hydration fetch goes in `es.onopen`
- Module-level JS variables for UI state (e.g., `fsmEnabled`) — add `currentTrackId` and `currentCard` state similarly
- No JS framework, no build step — vanilla ES6 in `<script>` tag inside `index.html`
- Template vars injected by Python at serve time via `html.replace("__TOKEN__", value)` — not needed for now-playing (card hydrates from JS fetch, not server-side render)

### Integration Points
- `es.onmessage` — primary integration point for real-time updates; add `track_change` and `eval_result` routing here
- `es.onopen` — integration point for SSE reconnect re-hydration (NOW-05)
- `DOMContentLoaded` — add `fetch('/now-playing')` initial call here (NOW-04)
- The card's skip button → `POST /skip` → existing endpoint from Phase 7
</code_context>

<specifics>
## Specific Ideas

- Card position confirmed: between FSM toggle and Incident Log (not top, not bottom)
- Badge uses new modifier classes (not reusing feed badge classes) — eval state and skip reason are semantically distinct
- `{"status":"idle"}` check: `data.status === "idle"` is the only idle condition; all other responses have track data
- Badge label for `fsm-off` is "Monitoring off" (user-facing language, not the raw daemon string)
</specifics>

<deferred>
## Deferred Ideas

None — analysis stayed within phase scope.
</deferred>

---

*Phase: 08-dashboard-frontend*
*Context gathered: 2026-04-03*
