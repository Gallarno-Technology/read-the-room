# Phase 18: Profile Info Icon - Research

**Researched:** 2026-04-06
**Domain:** Inline HTML/CSS/JS — popover + bottom-sheet reveal pattern, single-file template modification
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** The ⓘ icon is absolutely positioned in the top-right corner of the FSM card. The card already has `position: relative` — no structural change needed.
- **D-02:** Icon is visible at all times regardless of FSM on/off state (INFO-01).
- **D-03:** Responsive reveal — popover flyout on desktop (≥640px viewport width); bottom sheet that slides up from the bottom of the viewport on mobile (≤640px).
- **D-04:** Dismiss on outside click (desktop popover) or tap outside the sheet (mobile). Second tap on ⓘ also closes it.
- **D-05:** The breakdown updates when the active profile changes — JS re-renders content on each open (reads current profile state at open time), or updates live if already open.
- **D-06:** Content is profile name as a heading followed by a plain prose sentence:
  - Kids Present: "Skips profanity, drug references, sexual content, and explicit-flagged tracks."
  - We're All Adults: "Skips profanity and sexual content."
  - Above The Covers: "Skips sexual content."
  - Permissive: "Skips explicit-flagged tracks."
- **D-07:** Content is driven by a static JS map in index.html — no new API endpoint.

### Claude's Discretion
- Exact CSS for the popover (shadow, border, padding, width)
- Exact CSS for the bottom sheet (slide-up animation, overlay backdrop)
- Icon button size, color, and hover/active states
- Z-index layering relative to the profile dropdown

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INFO-01 | An info icon (ⓘ) is visible on the FSM control card at all times | Absolute positioning in top-right of the card (already `position: relative`); CSS independent of `.fsm-on`/`.fsm-off` state classes |
| INFO-02 | Tapping/clicking the info icon reveals a breakdown of what the active profile skips | Static JS map keyed to `activeProfile`; popover/bottom-sheet toggled by `hidden` attribute; content rendered at open time from `activeProfile` variable |
</phase_requirements>

---

## Summary

Phase 18 is a pure front-end addition to `web_ui/templates/index.html` — no Python changes, no new endpoints, no new files. The FSM card at line 448 already carries `position: relative`, making the top-right corner available for an absolutely-positioned ⓘ button with zero structural markup changes to the card.

The reveal mechanism splits by viewport width: at ≥640px a popover anchored near the icon appears; at ≤640px a bottom sheet slides up from the viewport edge. Both are driven by the same JS open/close functions — only the CSS presentation changes at the breakpoint. Dismiss behavior (outside click + second tap) mirrors the existing profile dropdown pattern exactly.

Content comes from a static JS object (`PROFILE_INFO`) keyed by profile slug. The `activeProfile` variable is already maintained in the page script and updated by `setFsmUI()` on every profile change and SSE event, so the popover reads correct state at open time without any new data wiring.

**Primary recommendation:** Add the ⓘ button and its panel as a self-contained block (CSS class + hidden panel + JS open/close) that follows the same `hidden` attribute toggle pattern as `#profile-dropdown`. Use a single `@media (max-width: 640px)` block to swap from anchored popover to fixed bottom-sheet overlay.

---

## Standard Stack

This phase introduces no third-party libraries. All implementation is vanilla HTML/CSS/JS within the existing single-file template.

### Core (existing, already in use)
| Asset | Purpose |
|-------|---------|
| `web_ui/templates/index.html` | The only file modified; CSS and JS are inline |
| CSS custom properties (`--bg`, `--surface`, `--border`, `--accent`, `--text`, `--text-dim`) | All colour tokens already defined in `:root` — use these for popover/sheet styling |
| `hidden` attribute pattern | Already used by `#profile-dropdown` for show/hide — use the same pattern for the info panel |
| `position: absolute` on `.card` | Card already has `position: relative` at line 448 |
| `z-index: 10` (profile dropdown) | Establish info popover at `z-index: 20` to clear the dropdown |
| `@keyframes fadeIn` (already defined) | Reuse for popover entrance; add `slideUp` keyframe for bottom sheet |
| `document.addEventListener('click', ...)` outside-click handler | Existing pattern at line 625 — mirror for popover dismiss |

### Not Needed
No npm installs, no CDN imports, no new Python dependencies.

---

## Architecture Patterns

### Recommended Markup — ⓘ Button + Panel
```html
<!-- inside .card at line 462, after #fsm-error -->
<button id="info-btn" class="info-btn" aria-label="Filter profile info" aria-expanded="false">&#9432;</button>
<div id="info-panel" class="info-panel" hidden role="tooltip">
  <p id="info-heading" class="info-heading"></p>
  <p id="info-body" class="info-body"></p>
</div>
```

The button sits inside `.card` (which is `position: relative`), absolutely positioned to the top-right corner. The panel is a sibling element — also inside the card — so desktop popover positioning is relative to the card. On mobile, CSS overrides reposition it to `position: fixed` at the bottom of the viewport.

### CSS Pattern — Desktop Popover
```css
.info-btn {
  position: absolute;
  top: 10px;
  right: 10px;
  background: none;
  border: none;
  color: var(--text-dim);
  cursor: pointer;
  font-size: 16px;
  line-height: 1;
  padding: 4px;
  z-index: 5;
}

.info-btn:hover {
  color: var(--text);
}

.info-panel {
  position: absolute;
  top: 36px;         /* below icon */
  right: 0;
  width: 260px;
  background: var(--surface-raised);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 12px 14px;
  z-index: 20;       /* above profile dropdown z-index: 10 */
  box-shadow: 0 4px 16px rgba(0,0,0,0.5);
}

.info-panel[hidden] { display: none; }

.info-heading {
  font-family: 'Playfair Display', serif;
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
  margin-bottom: 6px;
}

.info-body {
  font-family: 'Source Sans 3', sans-serif;
  font-size: 13px;
  color: var(--text-dim);
  line-height: 1.5;
}
```

### CSS Pattern — Mobile Bottom Sheet (≤640px)
```css
@media (max-width: 640px) {
  .info-panel {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    width: 100%;
    border-radius: 12px 12px 0 0;
    padding: 20px 20px 32px;
    z-index: 200;
    transform: translateY(100%);
    transition: transform 0.25s ease;
  }

  .info-panel:not([hidden]) {
    transform: translateY(0);
  }

  /* Backdrop overlay */
  .info-backdrop {
    display: none;
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.55);
    z-index: 199;
  }

  .info-backdrop.active {
    display: block;
  }
}
```

Note: `hidden` attribute sets `display: none`, which prevents CSS transitions from working on the initial open. The implementation must remove `hidden` one frame before applying the visible transform — or use a class-based approach instead of the `hidden` attribute for mobile. See Pitfall 1 below.

### JS Pattern — Static Info Map
```javascript
const PROFILE_INFO = {
  'kids_present': {
    name: 'Kids Present',
    desc: 'Skips profanity, drug references, sexual content, and explicit-flagged tracks.'
  },
  'were_all_adults': {
    name: "We're All Adults",
    desc: 'Skips profanity and sexual content.'
  },
  'above_the_covers': {
    name: 'Above The Covers',
    desc: 'Skips sexual content.'
  },
  'permissive': {
    name: 'Permissive',
    desc: 'Skips explicit-flagged tracks.'
  }
};
```

### JS Pattern — Open/Close Following Existing Dropdown Model
```javascript
const infoBtn   = document.getElementById('info-btn');
const infoPanel = document.getElementById('info-panel');
// backdrop element only used on mobile
const infoBackdrop = document.getElementById('info-backdrop');

function openInfo() {
  const info = PROFILE_INFO[activeProfile] || PROFILE_INFO['kids_present'];
  document.getElementById('info-heading').textContent = info.name;
  document.getElementById('info-body').textContent    = info.desc;
  infoPanel.removeAttribute('hidden');
  infoBtn.setAttribute('aria-expanded', 'true');
  if (infoBackdrop) infoBackdrop.classList.add('active');
}

function closeInfo() {
  infoPanel.setAttribute('hidden', '');
  infoBtn.setAttribute('aria-expanded', 'false');
  if (infoBackdrop) infoBackdrop.classList.remove('active');
}

infoBtn.addEventListener('click', function(e) {
  e.stopPropagation();
  if (infoPanel.hasAttribute('hidden')) { openInfo(); } else { closeInfo(); }
});

// Outside click — mirror of profile dropdown handler
document.addEventListener('click', function(e) {
  if (!infoPanel.hasAttribute('hidden') &&
      !infoPanel.contains(e.target) &&
      e.target !== infoBtn) {
    closeInfo();
  }
});

// Escape key
document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape' && !infoPanel.hasAttribute('hidden')) {
    closeInfo();
    infoBtn.focus();
  }
});
```

### Live Update When Profile Changes
`setFsmUI()` is the single function called on every profile change (user selection, SSE, initial load). Add an update call inside it:
```javascript
function setFsmUI(enabled, profile) {
  // ... existing code ...
  // If info panel is currently open, refresh its content
  if (!infoPanel.hasAttribute('hidden')) {
    const info = PROFILE_INFO[activeProfile] || PROFILE_INFO['kids_present'];
    document.getElementById('info-heading').textContent = info.name;
    document.getElementById('info-body').textContent    = info.desc;
  }
}
```
This satisfies D-05 without any polling or new listeners.

### Animation for Bottom Sheet
The CSS `transition: transform 0.25s ease` approach requires the element to be in the DOM but not `display: none` when the transition starts. Two viable strategies:

**Option A — Class toggle, never use `hidden` on mobile.**
Always remove `hidden` on first open; subsequent shows/hides toggle a class (`info-panel--open`) that controls `transform`.

**Option B — Remove `hidden`, defer class add by one frame.**
```javascript
function openInfo() {
  infoPanel.removeAttribute('hidden');
  requestAnimationFrame(function() {
    infoPanel.classList.add('info-panel--open');
  });
}
function closeInfo() {
  infoPanel.classList.remove('info-panel--open');
  // Re-add hidden after transition completes (250ms)
  setTimeout(function() {
    if (!infoPanel.classList.contains('info-panel--open')) {
      infoPanel.setAttribute('hidden', '');
    }
  }, 260);
}
```

Recommendation: Use class-based approach for the mobile bottom sheet. On desktop the popover does not use a transition so the `hidden` attribute toggle is fine there. A media query check in JS (`window.matchMedia('(max-width: 640px)').matches`) selects the correct strategy.

### Anti-Patterns to Avoid
- **Querying `activeProfile` from the DOM:** Read the `activeProfile` JS variable directly — it is always current.
- **New API endpoint for profile content:** The PROFILE_MAP is stable; a static JS object is sufficient (D-07).
- **Z-index below profile dropdown:** Popover must be `z-index: 20` or higher — the profile dropdown is `z-index: 10`.
- **Animating `display: none`:** CSS transitions do not fire when toggling `display` — use `transform` + `opacity` for animation, reserve `display: none` / `hidden` for the fully-closed state.
- **Adding backdrop to the card DOM:** The backdrop is a fixed overlay that must cover the full viewport — it must be a direct child of `<body>` or the `.page-wrap`, not inside `.card` (which has `overflow` clipping).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| Popover positioning library | Custom JS to compute `getBoundingClientRect` offsets | Simple `position: absolute` within the `position: relative` card — no JS geometry needed |
| Animation framework | CSS animation library | `@keyframes` already defined in the file; add one `slideUp` keyframe |
| Profile data from server | New `/profile-info` endpoint | Static `PROFILE_INFO` JS map (D-07 — content is stable, no round-trip needed) |
| Focus trap in bottom sheet | Custom focus management | Small panel with few elements — no trap needed; Escape key dismiss is sufficient |

---

## Common Pitfalls

### Pitfall 1: CSS Transition Blocked by `hidden` / `display: none`
**What goes wrong:** The slide-up animation doesn't play — the sheet appears and disappears instantly.
**Why it happens:** Browsers cannot transition an element from `display: none`; the transition fires before layout is calculated.
**How to avoid:** Remove the `hidden` attribute first, then set the visible transform in the next animation frame (`requestAnimationFrame`). On close, remove the open class, then restore `hidden` after the transition duration (250ms via `setTimeout`).
**Warning signs:** Sheet appears/disappears with no animation in testing.

### Pitfall 2: Z-Index Conflict with Profile Dropdown
**What goes wrong:** The profile dropdown appears on top of the info popover, or vice versa.
**Why it happens:** `.profile-dropdown` uses `z-index: 10`. If the info popover is also `z-index: 10`, they fight.
**How to avoid:** Set `.info-panel` to `z-index: 20`. Set the mobile backdrop to `z-index: 199` and the mobile sheet to `z-index: 200` (well above any card-level stacking context).
**Warning signs:** Clicking the dropdown trigger while info is open shows the dropdown underneath the popover.

### Pitfall 3: Backdrop Clipped by Card Overflow
**What goes wrong:** The mobile backdrop doesn't cover the full viewport — it's clipped at the card edge.
**Why it happens:** If `#info-backdrop` is placed inside `.card`, the card's stacking context clips it.
**How to avoid:** Place `#info-backdrop` as a direct child of `.page-wrap` or `<body>` — not inside `.card`.
**Warning signs:** The dark overlay only covers part of the screen.

### Pitfall 4: Outside-Click Handler Fires Before Toggle
**What goes wrong:** Clicking the ⓘ button closes and immediately re-opens the panel (or opens then immediately closes).
**Why it happens:** The document-level click handler fires on the same event as the button handler, closing a panel that was just opened.
**How to avoid:** Use `e.stopPropagation()` in the `infoBtn` click handler (same solution used by `profileTrigger` at line 591).
**Warning signs:** Panel flickers on click.

### Pitfall 5: Info Content Stale on Profile Change While Panel Open
**What goes wrong:** User changes profile but the open info panel still shows the old profile's description.
**Why it happens:** Content is only rendered in `openInfo()` — not updated when `activeProfile` changes.
**How to avoid:** Add the refresh logic inside `setFsmUI()` (conditioned on `!infoPanel.hasAttribute('hidden')`). This is the same function that already handles all profile state updates.
**Warning signs:** Info text doesn't update when dropdown selection changes while panel is visible.

---

## Code Examples

### Verified Existing Pattern: Outside-Click Guard (index.html line 625)
```javascript
// Mirror this pattern exactly for the info popover
document.addEventListener('click', function(e) {
  if (!profileDropdown.hidden &&
      !profileDropdown.contains(e.target) &&
      e.target !== profileTrigger) {
    closeDropdown();
  }
});
```

### Verified Existing Pattern: `hidden` Attribute Toggle (index.html lines 579–588)
```javascript
function openDropdown() {
  profileDropdown.hidden = false;
  profileTrigger.setAttribute('aria-expanded', 'true');
}
function closeDropdown() {
  profileDropdown.hidden = true;
  profileTrigger.setAttribute('aria-expanded', 'false');
}
```
Use `removeAttribute('hidden')` / `setAttribute('hidden', '')` for the info panel — equivalent behaviour, slightly more explicit for the animation timing case.

### Verified Existing Pattern: Absolute Positioning in Card (index.html lines 102–113)
```css
/* #banner-dismiss is already positioned absolutely inside a position:relative element */
#banner-dismiss {
  position: absolute;
  top: 8px;
  right: 8px;
  background: none;
  border: none;
  color: var(--text-dim);
  cursor: pointer;
}
```
The ⓘ button follows the exact same pattern inside `.card`.

### Verified: `activeProfile` Is Always Current
`activeProfile` is a module-level `let` updated by `setFsmUI(enabled, profile)` (line 534–551), which is called:
- On page load (line 555)
- On FSM toggle click (line 560)
- On profile option selection (line 604)
- (No SSE path yet — but SSE does not currently change the profile; FSM state is not in SSE events)

No additional wiring needed to read current profile from the panel.

---

## Runtime State Inventory

Step 2.5: SKIPPED — this is a UI addition phase, not a rename/refactor/migration phase. No runtime state is being renamed or replaced.

---

## Environment Availability

Step 2.6: SKIPPED — phase is a pure inline HTML/CSS/JS change. No external CLIs, runtimes, services, or databases beyond what already runs the app are required.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (detected in `/tests/`) |
| Config file | none — `conftest.py` handles path setup |
| Quick run command | `python3 -m pytest tests/ -x -q` |
| Full suite command | `python3 -m pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INFO-01 | ⓘ button present in rendered HTML regardless of FSM state | unit (template parse) | `python3 -m pytest tests/test_info_icon.py::test_info_btn_present -x` | ❌ Wave 0 |
| INFO-02 | Clicking icon reveals correct profile description | manual/visual | Manual browser test — DOM interaction not feasible in pytest without a JS runtime | N/A — manual only |

INFO-02 requires JavaScript execution (click event, DOM mutation, profile-aware content). The existing test suite uses FastAPI `TestClient` (no browser). Full JS behaviour must be validated manually in the browser. The single automatable check is confirming the HTML template contains the button element and the static JS map.

### Sampling Rate
- **Per task commit:** `python3 -m pytest tests/ -x -q`
- **Per wave merge:** `python3 -m pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_info_icon.py` — covers INFO-01 (template contains `#info-btn`, `#info-panel`, `PROFILE_INFO` map) via template string inspection
- [ ] No framework install needed — pytest already available

---

## Sources

### Primary (HIGH confidence)
- `web_ui/templates/index.html` — full file read; all CSS, JS, and markup patterns verified directly
- `daemon.py` lines 51–83 — `PROFILE_MAP` verified; four profiles and their boolean flags match D-06 prose sentences exactly

### Secondary (MEDIUM confidence)
- MDN CSS transitions spec (training knowledge, HIGH stability) — `display: none` blocks CSS transitions; `requestAnimationFrame` + `setTimeout` workaround is the standard solution

### No external sources consulted
This phase is entirely self-contained within the existing codebase. All patterns are derived from reading the live source file. No library documentation needed.

---

## Open Questions

1. **Backdrop element placement**
   - What we know: The mobile backdrop needs `position: fixed` covering the full viewport.
   - What's unclear: Whether to place it inside `.page-wrap` or directly in `<body>`. The `.page-wrap` has `max-width: 640px` but fixed children escape it — so `.page-wrap` placement is fine.
   - Recommendation: Place inside `.page-wrap` immediately before `</div>` closing tag for locality. If testing shows clipping, move to `<body>`.

2. **Bottom-sheet close handle**
   - What we know: D-03/D-04 require dismiss on outside tap. CONTEXT.md mentions "visible handle or close button (✖)".
   - What's unclear: Whether the planner wants a drag handle bar (visual only) or a tappable ✖ button.
   - Recommendation: Add a small ✖ button inside the sheet header — simpler to implement and more accessible than a drag gesture.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no third-party libraries; pure inline implementation
- Architecture: HIGH — patterns read directly from live source file
- Pitfalls: HIGH — derived from actual CSS/JS mechanics and existing code structure
- Validation: MEDIUM — JS-heavy INFO-02 cannot be fully automated without a browser runtime; manual validation plan documented

**Research date:** 2026-04-06
**Valid until:** Stable indefinitely — no external dependencies
