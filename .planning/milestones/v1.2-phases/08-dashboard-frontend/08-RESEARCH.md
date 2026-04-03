# Phase 8: Dashboard Frontend - Research

**Researched:** 2026-04-03
**Domain:** Vanilla HTML/CSS/JS — server-rendered single-file dashboard; SSE event routing; fetch-based hydration
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Now-playing card inserted between the FSM toggle card and the Incident Log card.
- **D-02:** Card structure inline in `index.html` (no separate file): album art `<img>` (64×64), track name + artist on two lines, eval-state badge, skip `<button>` below track info. Idle state: placeholder text "Nothing playing" + skip button hidden when `data.status === "idle"`.
- **D-03:** On `DOMContentLoaded`, call `GET /now-playing` once. If `data.status === "idle"`, show idle placeholder; otherwise render card with full track data.
- **D-04:** On SSE `onopen` (including reconnects), re-call `GET /now-playing` to repopulate the card (NOW-05). Same idle-check applies.
- **D-05:** No polling. SSE `track_change` and `eval_result` events drive all in-session updates after hydration.
- **D-06:** `track_change` event → update card: set track name, artist, album art, reset badge to `eval_state: "evaluating"`.
- **D-07:** `eval_result` event → update badge ONLY if `evt.track_id === currentTrackId` (NOW-07 guard). Mismatched track_id → ignore silently.
- **D-08:** Add `track_change` and `eval_result` cases to the existing `es.onmessage` switch/if-else chain alongside `skip` and `five_skip_warning`.
- **D-09:** New CSS modifier classes (alongside existing feed badge classes, which remain untouched):
  - `.badge--evaluating` — amber/muted
  - `.badge--passed` — green
  - `.badge--no-lyrics` — grey
  - `.badge--skipped` — red
  - `.badge--paused` — orange
  - `.badge--fsm-off` — faint/dim
- **D-10:** Badge label text:
  - `evaluating` → "Checking…"
  - `passed` → "Passed"
  - `no-lyrics` → "No lyrics"
  - `skipped` → "Skipped"
  - `paused` → "Paused"
  - `fsm-off` → "Monitoring off"
- **D-11:** `currentTrackId` — module-level JS variable. Set on `track_change` events and on hydration from `GET /now-playing`. Used for the NOW-07 guard.
- **D-12:** Skip button hidden (`display:none`) when `data.status === "idle"`, visible when a track is playing.
- **D-13:** On click: `button.disabled = true` immediately (SKIP-04). Call `POST /skip`. Re-enable on fetch settle (success or error).
- **D-14:** On 503 response (`{"detail":"skip_failed"}`), show inline error message below the button — same pattern as `#fsm-error`. Clear after 3 seconds.
- **D-15:** On success (`{"ok":true}`), no special UI response. Next `track_change` SSE event updates the card naturally.
- **D-16:** `<img>` `src` set from `album_art_url`. If `album_art_url` is `null`, hide the img element. URL comes from Spotify CDN; no external CDN dependency introduced by Phase 8.

### Claude's Discretion

- Exact CSS sizing for album art (suggested: 64px square with `border-radius: 4px`)
- Whether to use CSS flex or inline-block for art + track info layout
- Exact placeholder text for idle state and for null album art
- Animation for badge state transitions (can reuse existing `.feed-new` fadeIn or none)
- Whether to add a `aria-live` region for the now-playing card for accessibility

### Deferred Ideas (OUT OF SCOPE)

None — analysis stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| NOW-01 | Dashboard displays a now-playing card showing current track name and artist | Card HTML structure defined in D-02 and UI-SPEC; maps to `#now-playing-name`, `#now-playing-artist` |
| NOW-02 | Card shows an evaluation state badge that updates in real-time | Badge state machine from D-09/D-10; driven by `eval_result` SSE events |
| NOW-03 | Badge shows "evaluating" immediately when a new track starts, before evaluation completes | `track_change` event resets badge to `.badge--evaluating` / "Checking…" per D-06 |
| NOW-04 | Card is populated on fresh page load — not blank when opening the dashboard mid-session | `DOMContentLoaded` → `fetch('/now-playing')` per D-03 |
| NOW-05 | Card is populated correctly after SSE reconnection | `es.onopen` → `fetch('/now-playing')` per D-04 |
| NOW-06 | Card displays album artwork | `<img id="now-playing-art">` from `album_art_url` field per D-16 |
| NOW-07 | Badge ignores `eval_result` events with a mismatched `track_id` | `currentTrackId` guard in `eval_result` handler per D-07/D-11 |
| SKIP-01 | Dashboard displays a manual skip button on the now-playing card | `<button id="skip-btn">` inside card per D-12 |
| SKIP-04 | Skip button is disabled while a skip request is in flight to prevent double-fire | `button.disabled = true` before fetch, re-enable in finally per D-13 |
</phase_requirements>

---

## Summary

Phase 8 is a pure frontend change — all changes land in a single file: `web_ui/templates/index.html`. No new Python, no new endpoints, no build step. The backend contracts (GET /now-playing, POST /skip, SSE events) are already implemented in Phases 6 and 7; Phase 8 wires them to the DOM.

The implementation decomposes into three orthogonal concerns: (1) HTML structure — insert the now-playing card between the two existing cards; (2) CSS — add six new `.badge--*` modifier classes following the exact pattern of the four existing feed badge classes; (3) JS — add hydration calls (DOMContentLoaded + es.onopen), two new SSE event handlers (track_change, eval_result), a skip button click handler, and a `currentTrackId` guard variable. Each concern is independent and can be planned as a discrete task.

All design decisions are already locked in 08-CONTEXT.md and 08-UI-SPEC.md. The UI-SPEC provides the exact HTML markup, color values, typography rules, spacing, copywriting, and interaction contracts verbatim — the planner and implementer need only follow that spec. The only discretionary choices are animation (reuse `.feed-new` fadeIn) and `aria-live` (add per UI-SPEC decision).

**Primary recommendation:** Implement in three tasks: (1) HTML card insertion, (2) CSS badge modifier classes, (3) JS hydration + SSE routing + skip button handler — in that order, since CSS can be verified visually before JS behavior is wired up.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Vanilla HTML/CSS/JS | ES6 (browser-native) | UI implementation | Established by existing `index.html`; no build step; project constraint |
| EventSource API | Browser-native | SSE subscription | Already in use via `const es = new EventSource('/events')` |
| Fetch API | Browser-native | REST calls (`GET /now-playing`, `POST /skip`) | Already in use for FSM toggle |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Google Fonts (CDN) | — | Playfair Display, Source Sans 3, Courier Prime | Already imported in `<head>`; no additional fonts needed for Phase 8 |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Inline CSS in `index.html` | Separate CSS file | No build step exists; inline is the established pattern — do not change |
| Vanilla ES6 | React/Vue/Svelte | No bundler; adding a framework would require build tooling — out of scope |

**Installation:** None required. No new dependencies. All browser APIs are native.

---

## Architecture Patterns

### Recommended Project Structure

```
web_ui/templates/index.html   -- single file: all HTML, <style>, <script> inline
```

No new files. All changes are edits to the single existing template.

### Pattern 1: Card Insertion Position

**What:** Insert the new card `div.card#now-playing-card` after the FSM toggle card `div.card` and before the Incident Log card `div.card`.

**When to use:** Always — D-01 is a locked decision.

**Example (insertion point in existing HTML):**
```html
<div class="card">
  <button id="fsm-toggle" ...></button>
  <div id="fsm-error"></div>
</div>

<!-- INSERT NOW-PLAYING CARD HERE -->

<div class="card">
  <h2 class="card-heading">Incident Log</h2>
  ...
</div>
```

### Pattern 2: Two-Section Card (idle vs. track)

**What:** Card has two child sections — `#now-playing-idle` (visible when idle) and `#now-playing-track` (visible when track playing). Toggle `display:none` / `display:block` between them.

**When to use:** Whenever rendering any state — hydration, track_change, or eval_result.

**Example (from 08-UI-SPEC.md):**
```html
<div class="card" id="now-playing-card">
  <h2 class="card-heading">Now Playing</h2>
  <hr class="section-divider">
  <p id="now-playing-idle" class="empty-body">Nothing playing</p>
  <div id="now-playing-track" style="display:none">
    <div style="display:flex; align-items:center; gap:16px">
      <img id="now-playing-art" src="" alt="" width="64" height="64"
           style="border-radius:4px; flex-shrink:0; display:none">
      <div>
        <div id="now-playing-name" style="font-size:14px; line-height:1.5"></div>
        <div id="now-playing-artist" style="font-size:14px; color:var(--text-dim); line-height:1.5"></div>
        <span id="now-playing-badge" class="badge"></span>
      </div>
    </div>
    <button id="skip-btn" style="margin-top:16px; width:100%; height:44px">Skip Track</button>
    <div id="skip-error" style="margin-top:8px; font-size:12px; color:var(--danger); min-height:16px"></div>
  </div>
</div>
```

### Pattern 3: Badge State Machine

**What:** `setBadgeClass()` and `badgeLabel()` patterns already exist for the feed badges. Replicate for eval_state with a `setEvalBadge(evalState)` function.

**When to use:** On `track_change` (force to "evaluating"), on `eval_result` (update to final state), on hydration.

**Example:**
```js
const EVAL_BADGE_CLASS = {
  'evaluating': 'badge--evaluating',
  'passed':     'badge--passed',
  'no-lyrics':  'badge--no-lyrics',
  'skipped':    'badge--skipped',
  'paused':     'badge--paused',
  'fsm-off':    'badge--fsm-off',
};
const EVAL_BADGE_LABEL = {
  'evaluating': 'Checking\u2026',
  'passed':     'Passed',
  'no-lyrics':  'No lyrics',
  'skipped':    'Skipped',
  'paused':     'Paused',
  'fsm-off':    'Monitoring off',
};

function setEvalBadge(evalState) {
  const badge = document.getElementById('now-playing-badge');
  // Remove existing modifier classes
  badge.className = 'badge ' + (EVAL_BADGE_CLASS[evalState] || 'badge--evaluating');
  badge.textContent = EVAL_BADGE_LABEL[evalState] || '';
}
```

### Pattern 4: Hydration Function (shared by DOMContentLoaded + es.onopen)

**What:** Single `hydrateNowPlaying()` async function called from both entry points to avoid code duplication.

**When to use:** On page load and on every SSE reconnect.

**Example:**
```js
async function hydrateNowPlaying() {
  try {
    const resp = await fetch('/now-playing');
    const data = await resp.json();
    if (data.status === 'idle') {
      renderIdle();
    } else {
      renderTrack(data);
      currentTrackId = data.track_id;
    }
  } catch (err) {
    // Network error — leave card in current state; SSE reconnect will retry
  }
}

document.addEventListener('DOMContentLoaded', hydrateNowPlaying);
es.onopen = function() {
  sseDot.className = 'sse-dot connected';
  sseLabel.textContent = '';
  hydrateNowPlaying();  // NOW-05: repopulate after reconnect
};
```

### Pattern 5: SSE Event Router Extension

**What:** Extend the existing `es.onmessage` if-else chain to handle `track_change` and `eval_result`. Do NOT restructure the existing `skip` and `five_skip_warning` branches.

**When to use:** Adding new event types — always extend, never restructure existing.

**Example:**
```js
es.onmessage = function(e) {
  try {
    const evt = JSON.parse(e.data);
    if (evt.type === 'skip') {
      prependSkipItem(evt);
    } else if (evt.type === 'five_skip_warning') {
      banner.removeAttribute('hidden');
    } else if (evt.type === 'track_change') {
      renderTrack(evt);
      currentTrackId = evt.track_id;
      setEvalBadge('evaluating');
    } else if (evt.type === 'eval_result') {
      if (evt.track_id === currentTrackId) {  // NOW-07 guard
        setEvalBadge(evt.eval_state);
      }
    }
  } catch (err) {
    // Ignore malformed events — existing pattern
  }
};
```

### Pattern 6: Skip Button with In-Flight Disable

**What:** Disable button before fetch, re-enable in a finally block so it always re-enables regardless of success or error.

**When to use:** SKIP-04 — must use `try/finally` pattern, not success-only re-enable.

**Example:**
```js
document.getElementById('skip-btn').addEventListener('click', async function() {
  const skipBtn = this;
  const skipError = document.getElementById('skip-error');
  skipBtn.disabled = true;
  skipError.textContent = '';
  try {
    const resp = await fetch('/skip', { method: 'POST' });
    if (resp.status === 503) {
      skipError.textContent = 'Skip failed \u2014 try again.';
      setTimeout(function() { skipError.textContent = ''; }, 3000);
    }
    // On success: no UI update needed (next track_change SSE event handles it)
  } catch (err) {
    skipError.textContent = 'Skip failed \u2014 try again.';
    setTimeout(function() { skipError.textContent = ''; }, 3000);
  } finally {
    skipBtn.disabled = false;  // Always re-enable
  }
});
```

### Anti-Patterns to Avoid

- **Restructuring existing es.onmessage:** The existing `skip` and `five_skip_warning` branches must be preserved exactly — only add new `else if` branches.
- **Re-enabling skip button only on success:** Must use `finally` so the button re-enables even when POST /skip fails with a network error.
- **Applying `eval_result` without track_id guard:** Every `eval_result` handler MUST check `evt.track_id === currentTrackId` before updating the badge (NOW-07).
- **Setting `currentTrackId` from `eval_result`:** Only set `currentTrackId` from `track_change` events and hydration — never from `eval_result`.
- **Re-fetching /now-playing on every SSE event:** Only fetch on `es.onopen` (reconnects). Live updates come from SSE events directly.
- **Polling for updates:** No interval-based polling — D-05 is a locked decision.
- **Using feed badge modifier classes for eval badge:** The six new `badge--*` classes are semantically distinct from the four feed badge classes — do not reuse them.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SSE reconnection | Custom WebSocket fallback or retry loop | Native `EventSource` auto-reconnect | Browser EventSource reconnects automatically; existing `es.onerror` already handles UI feedback |
| Badge color system | New CSS variables or custom property system | Existing `--bg`, `--warn`, `--danger`, `--text-dim`, `--text-faint` CSS variables | All six badge colors are already specified in UI-SPEC using existing variables |
| Animation | CSS transition library | Existing `.feed-new` `@keyframes fadeIn` | Already defined in `index.html`; zero additional CSS needed |
| Fetch error handling | Retry logic | Single try/catch per fetch, show error, let SSE reconnect trigger re-hydration | SSE reconnect is the reliable recovery path; complex retry logic is unnecessary |

---

## Runtime State Inventory

Step 2.5: SKIPPED — Phase 8 is not a rename/refactor/migration phase. It is a greenfield feature addition to an existing HTML file.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Browser (EventSource, Fetch) | SSE + hydration | ✓ | Browser-native | — |
| Google Fonts CDN | Typography | ✓ (already in use) | — | System sans-serif fallback already in font-family stack |
| Spotify CDN (`i.scdn.co`) | Album art images | ✓ (runtime) | — | Null check hides `<img>` per D-16 |
| `.venv/bin/pytest` | Test suite | ✓ | 8.3.5 | — |
| FastAPI TestClient (httpx) | Existing endpoint tests | ✓ (already installed) | — | — |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:** None — all dependencies are available or have a defined fallback path.

---

## Common Pitfalls

### Pitfall 1: es.onopen Fires on Initial Connect, Not Just Reconnects

**What goes wrong:** Developer thinks `es.onopen` only fires on reconnect, so they put hydration only in `DOMContentLoaded`. After reconnect the card goes blank.

**Why it happens:** `EventSource.onopen` fires on EVERY successful connection, including the first. This is why putting hydration in both `DOMContentLoaded` AND `es.onopen` works — the `DOMContentLoaded` call races the first SSE `onopen`, but both paths render the same data, so the second call is idempotent.

**How to avoid:** Always call `hydrateNowPlaying()` from both `DOMContentLoaded` and `es.onopen`. The double-call on page load is harmless.

**Warning signs:** Card populates on load but goes blank after browser loses and regains network connection.

### Pitfall 2: Stale eval_result Overwrites Badge on Rapid Skips

**What goes wrong:** User manually skips a track. Before the eval_result for the new track arrives, a delayed eval_result for the just-skipped track arrives and overwrites the "Checking…" badge with the old track's result.

**Why it happens:** Network or daemon latency — eval_result for track A arrives after track_change for track B.

**How to avoid:** The NOW-07 guard (`if (evt.track_id === currentTrackId)`) prevents this. `currentTrackId` must be set ONLY from `track_change` events and hydration.

**Warning signs:** Badge briefly shows wrong state ("Passed") then flips back to "Checking…" when a new track starts while the previous was still evaluating.

### Pitfall 3: Skip Button Not Re-Enabled After Network Error

**What goes wrong:** `fetch('/skip')` throws (network error, not HTTP error). Button stays disabled permanently because the catch block doesn't re-enable.

**Why it happens:** Network errors don't produce a `Response` object — they throw before `.status` is readable. If re-enable is only in the success path, error path leaves button stuck.

**How to avoid:** Always re-enable in a `finally` block, not in `then` or the try body.

**Warning signs:** After one failed skip (network blip), skip button stays grayed out and `button.disabled` is `true`.

### Pitfall 4: Inline Style Conflicts With Card Toggle Logic

**What goes wrong:** `#now-playing-track` has `style="display:none"` in HTML. JS sets `element.style.display = 'block'` to show. A future CSS rule `.card div { display: flex }` could conflict.

**Why it happens:** Inline styles have higher specificity than class-based CSS rules.

**How to avoid:** Keep display toggle as `element.style.display = ''` (reset to CSS default) rather than `'block'`, or use the same flex pattern as the existing card layout. The UI-SPEC uses flex for the art+info row; the outer `#now-playing-track` div can reset to block (the flex is on the inner row, not the outer wrapper).

**Warning signs:** Card layout breaks when showing/hiding — art and text stack incorrectly.

### Pitfall 5: album_art_url Null Check Missing

**What goes wrong:** When `album_art_url` is `null`, setting `img.src = null` sets it to `"null"` (string), causing a broken image request to `/null`.

**Why it happens:** `element.setAttribute('src', null)` coerces null to the string "null".

**How to avoid:** Explicit null check:
```js
if (data.album_art_url) {
  artImg.src = data.album_art_url;
  artImg.style.display = '';
} else {
  artImg.style.display = 'none';
}
```

**Warning signs:** Browser network tab shows `GET /null 404` requests.

---

## Code Examples

Verified patterns from existing `web_ui/templates/index.html`:

### Existing Feed Badge Pattern (model for eval badge)
```js
// Source: web_ui/templates/index.html (verified)
function setBadgeClass(reason) {
  const r = (reason || '').toLowerCase();
  if (r.includes('explicit')) return 'badge--explicit';
  if (r.includes('profanity') || r.includes('language')) return 'badge--profanity';
  if (r.includes('adult')) return 'badge--adult';
  return 'badge--explicit';
}
```
Replicate with a lookup table for eval_state (exact string match, not includes).

### Existing Error Pattern (model for skip error)
```js
// Source: web_ui/templates/index.html (verified)
fsmError.textContent = 'Could not update — try again.';
setTimeout(function() { fsmError.textContent = ''; }, 3000);
```
Skip error uses identical pattern with `#skip-error` element.

### Existing SSE Router (extension point)
```js
// Source: web_ui/templates/index.html (verified)
es.onmessage = function(e) {
  try {
    const evt = JSON.parse(e.data);
    if (evt.type === 'skip') {
      prependSkipItem(evt);
    } else if (evt.type === 'five_skip_warning') {
      banner.removeAttribute('hidden');
    }
    // ADD: track_change and eval_result cases here
  } catch (err) {
    // Ignore malformed events
  }
};
```

### Existing Badge CSS Pattern (model for new badge modifier classes)
```css
/* Source: web_ui/templates/index.html (verified) */
.badge--explicit {
  background: rgba(168, 50, 50, 0.2);
  color: #e06060;
  border-color: rgba(168, 50, 50, 0.3);
}
```
All six eval badge modifier classes follow this exact three-property pattern.

### Exact Eval Badge Colors (from 08-UI-SPEC.md, verified against existing variables)
```css
.badge--evaluating {
  background: rgba(181,114,42,0.2);
  color: #d4924a;
  border-color: rgba(181,114,42,0.3);
}
.badge--passed {
  background: rgba(80,140,80,0.15);
  color: #70a870;
  border-color: rgba(80,140,80,0.25);
}
.badge--no-lyrics {
  background: rgba(90,84,72,0.3);
  color: #9a9080;
  border-color: rgba(90,84,72,0.4);
}
.badge--skipped {
  background: rgba(168,50,50,0.2);
  color: #e06060;
  border-color: rgba(168,50,50,0.3);
}
.badge--paused {
  background: rgba(181,114,42,0.2);
  color: #d4924a;
  border-color: rgba(181,114,42,0.3);
}
.badge--fsm-off {
  background: rgba(90,84,72,0.15);
  color: #5a5448;
  border-color: rgba(90,84,72,0.2);
}
```

### Skip Button Default Style (matches #fsm-toggle .fsm-off)
```css
/* Apply to #skip-btn as inline style or class — matches .fsm-off appearance */
background: var(--surface-raised);
color: var(--text);
border: 1px solid var(--border);
border-radius: 6px;
cursor: pointer;
font-family: 'Courier Prime', monospace;
font-size: 13px;
font-weight: 600;
```

### Disabled Skip Button Appearance
```css
#skip-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No now-playing card | Now-playing card with real-time badge | Phase 8 | Parents see current track without opening Spotify |
| Incident log only | Incident log + now-playing card | Phase 8 | Adds proactive display alongside reactive history |

**No deprecated patterns in this phase.** All patterns follow the existing `index.html` conventions.

---

## Open Questions

1. **es.onopen double-call on initial page load**
   - What we know: `DOMContentLoaded` and `es.onopen` both call `hydrateNowPlaying()`. On initial page load they race.
   - What's unclear: Could a very fast SSE connection cause `es.onopen` to fire before `DOMContentLoaded`?
   - Recommendation: Not a problem in practice. Both calls render the same data idempotently. The card will show correct state regardless of which resolves first. No special handling needed.

2. **Skip button styling class vs. inline style**
   - What we know: `#fsm-toggle` uses `.fsm-off` / `.fsm-on` CSS classes to toggle appearance. UI-SPEC shows skip button with the same visual style as `.fsm-off` but it does not toggle (always the same style).
   - What's unclear: Use `.fsm-off` class directly, or duplicate the CSS as inline style or a new `.skip-btn` class?
   - Recommendation: Apply the styling inline (matching the UI-SPEC markup pattern) or as a dedicated `#skip-btn` CSS rule in the `<style>` block. Do NOT reuse `.fsm-off` as a class — semantic coupling is wrong. A dedicated CSS block for `#skip-btn` is cleanest.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.3.5 |
| Config file | none (runs with `pytest tests/` from project root) |
| Quick run command | `.venv/bin/pytest tests/test_web_ui_endpoints.py -q` |
| Full suite command | `.venv/bin/pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| NOW-01 | Card renders track name + artist from hydration | integration (TestClient) | `.venv/bin/pytest tests/test_web_ui_frontend.py::test_now_playing_card_renders -x` | ❌ Wave 0 |
| NOW-02 | Badge updates via eval_result SSE event | manual (browser) | manual-only — SSE event routing is in-browser JS, not testable via TestClient | manual-only |
| NOW-03 | Badge shows "Checking…" immediately on track_change | manual (browser) | manual-only — same reason as NOW-02 | manual-only |
| NOW-04 | Fresh page load populates card from /now-playing | integration (TestClient + JS behavior) | `.venv/bin/pytest tests/test_web_ui_frontend.py::test_now_playing_hydration_on_load -x` | ❌ Wave 0 |
| NOW-05 | SSE reconnect re-populates card | manual (browser) | manual-only — requires live SSE reconnect simulation | manual-only |
| NOW-06 | Album art shown when album_art_url non-null | integration | `.venv/bin/pytest tests/test_web_ui_frontend.py::test_album_art_visible -x` | ❌ Wave 0 |
| NOW-07 | Mismatched track_id eval_result ignored | manual (browser) | manual-only — JS guard requires live SSE events | manual-only |
| SKIP-01 | Skip button present in card markup | integration | `.venv/bin/pytest tests/test_web_ui_frontend.py::test_skip_button_present -x` | ❌ Wave 0 |
| SKIP-04 | Skip button disabled while request in flight | manual (browser) | manual-only — requires timing observation in browser | manual-only |

**Justification for manual-only tests:** SSE event routing and in-flight button state require a live browser environment. TestClient serves HTML but does not execute inline JavaScript. The recommended approach is to test HTML structure (card elements present, correct initial markup) via TestClient, and verify the JS behavior manually in a browser during the verify-work phase.

### Sampling Rate

- **Per task commit:** `.venv/bin/pytest tests/test_web_ui_endpoints.py tests/test_daemon_events.py -q` (verify existing backend contracts unbroken)
- **Per wave merge:** `.venv/bin/pytest tests/ -q`
- **Phase gate:** Full suite green + manual browser walkthrough of all 5 success criteria before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_web_ui_frontend.py` — HTML structure assertions: card present, elements present, badge classes present in markup. Covers NOW-01, NOW-04, NOW-06, SKIP-01 (structural).

*(Existing test infrastructure covers all backend concerns; only the new HTML structure test file is needed.)*

---

## Project Constraints (from CLAUDE.md)

CLAUDE.md does not exist in the project root. No project-specific guidelines to enforce.

The following constraints are derived from the codebase and CONTEXT.md decisions:

- **No build step:** All JS and CSS are inline in `web_ui/templates/index.html`. No webpack, no vite, no transpilation.
- **No JS framework:** Vanilla ES6 only. No React, Vue, or Svelte.
- **No new files:** All Phase 8 changes land in the single existing `index.html`. No new templates, no separate CSS or JS files.
- **No new Python:** Phase 8 is HTML/CSS/JS only. `web_ui/main.py` is read-only for this phase.
- **No new dependencies:** All browser APIs used are native (EventSource, Fetch). No npm installs.
- **CSS variable system:** Use existing CSS custom properties (`--bg`, `--surface`, `--warn`, etc.). Do not introduce new CSS variables.
- **Google Fonts:** Already imported. Do not add new font imports.
- **Inline style for toggle visibility:** Established pattern is `element.style.display = 'none'` / `''`. Match this for the card section toggle.

---

## Sources

### Primary (HIGH confidence)

- `web_ui/templates/index.html` (read directly) — existing CSS variables, badge classes, SSE router, fetch patterns, element IDs
- `.planning/phases/08-dashboard-frontend/08-CONTEXT.md` (read directly) — all locked implementation decisions
- `.planning/phases/08-dashboard-frontend/08-UI-SPEC.md` (read directly) — exact HTML markup, color values, typography, interaction contracts
- `.planning/phases/06-daemon-sse-extensions/06-CONTEXT.md` (read directly) — event schemas for track_change (D-04), eval_result (D-05), now_playing.json (D-06)
- `.planning/phases/07-web-ui-backend/07-CONTEXT.md` (read directly) — GET /now-playing and POST /skip response contracts

### Secondary (MEDIUM confidence)

- MDN EventSource API — EventSource.onopen fires on every successful connection (including initial), not only reconnects. This is the basis for Pitfall 1 and the dual-hydration pattern. [https://developer.mozilla.org/en-US/docs/Web/API/EventSource/open_event]

### Tertiary (LOW confidence)

- None.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no third-party libraries; all browser-native APIs; verified from existing code
- Architecture: HIGH — all patterns derived directly from existing `index.html` and locked CONTEXT.md decisions; no speculation
- Pitfalls: HIGH — pitfalls derived from direct code analysis and established JS behavior (EventSource spec, null coercion, finally semantics)

**Research date:** 2026-04-03
**Valid until:** 2026-05-03 (stable domain — vanilla JS + browser APIs change slowly)
