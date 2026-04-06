# Phase 19: Mobile Polish - Research

**Researched:** 2026-04-06
**Domain:** CSS mobile UX — viewport zoom control and text selection restriction
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Apply **both** approaches for full cross-platform coverage:
  - Update viewport meta to add `user-scalable=no, maximum-scale=1` (required for iOS double-tap zoom disable)
  - Add `touch-action: manipulation` on interactive elements (prevents double-tap zoom on Android Chrome without blocking scroll)
- **D-02:** Neither approach alone is sufficient — iOS ignores `touch-action`; Android Chrome can still double-tap-zoom past `user-scalable=no` on some versions.
- **D-03:** Apply `user-select: none` **broadly** (on `body` or the top-level card container) with **explicit opt-in carve-outs** for selectable text.
- **D-04:** UI chrome that gets `none` (covered by the broad rule): buttons, badges, labels, profile options, info icon, split-button zones, card headers.
- **D-05:** Track title and artist text remain selectable **everywhere they appear** — both in the Now Playing section AND in skip feed history list items.
- **D-06:** All track/artist text is selectable regardless of location (consistent rule).

### Claude's Discretion

- Exact selector specificity (whether to apply broad rule on `body`, `.card`, or a wrapper)
- Whether `touch-action: manipulation` is applied globally or only on `<button>` elements
- CSS specificity ordering to ensure carve-outs override the broad rule cleanly

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MOB-01 | Dashboard viewport prevents pinch-zoom and double-tap zoom on mobile | Viewport meta update + `touch-action: manipulation` on interactive elements (see Architecture Patterns) |
| MOB-02 | Buttons, labels, badges, and profile options have `user-select: none` — track title/artist remain selectable | Broad `user-select: none` on body + explicit `user-select: text` carve-outs (see Architecture Patterns) |
</phase_requirements>

## Summary

Phase 19 is a two-property CSS/HTML patch targeting `web_ui/templates/index.html` only. The scope is tightly bounded: one viewport meta token change and a small set of CSS rules in the existing inline `<style>` block. No Python, no API, no new JS.

The zoom restriction problem (MOB-01) requires a dual approach because iOS Safari and Android Chrome respond to different signals. `user-scalable=no, maximum-scale=1` in the viewport meta is partially effective on iOS (respected for double-tap in some configurations; ignored for pinch since iOS 10 accessibility changes). `touch-action: manipulation` on interactive elements prevents double-tap zoom on Android Chrome and removes the 300ms click delay on both platforms — but iOS Safari only honours `auto` and `manipulation` values (not `pan-y`). Together, the two signals achieve the widest practical coverage without JS event interception.

The text selection problem (MOB-02) is well understood. `user-select: none` on `body` inherits to all descendants. Child elements with `user-select: text` override this inheritance cleanly in all modern browsers (97% compatibility). The only implementation decision is selector precision for the feed history carve-outs — track and artist spans in the feed have no CSS class (unlike `.feed-sep`, `.badge`, `.feed-timestamp`), so the carve-out must use a negation selector or assign a new class.

**Primary recommendation:** Apply `user-select: none` to `body`, apply `touch-action: manipulation` to all `<button>` elements in CSS (not element-by-element), add carve-outs for Now Playing name/artist by ID and for feed track/artist spans by negation selector. Update the viewport meta with both tokens.

## Standard Stack

### Core

| Property | Value | Purpose | Why Standard |
|----------|-------|---------|--------------|
| Viewport meta | `user-scalable=no, maximum-scale=1` | Signals intent to suppress zoom to iOS | Only HTML signal Safari partially respects for double-tap |
| `touch-action: manipulation` | CSS property | Disables double-tap zoom; removes 300ms click delay | W3C standard; supported since Android Chrome 36 / iOS Safari 9.3 |
| `user-select: none` | CSS property | Prevents text selection on UI chrome | 97% browser compatibility; inherits naturally through DOM |
| `user-select: text` | CSS property | Opt-in carve-out for selectable content | Overrides inherited `none` on child elements |

No new packages are required. All changes are pure CSS and one HTML attribute change.

**Installation:** None. No new dependencies.

## Architecture Patterns

### Recommended Change Structure

```
web_ui/templates/index.html
├── <head> line 5          viewport meta — add two tokens
├── <style> existing block
│   ├── body {}            add user-select: none
│   ├── button {}          add touch-action: manipulation (new or merged rule)
│   ├── #now-playing-name  add user-select: text (carve-out)
│   ├── #now-playing-artist add user-select: text (carve-out)
│   └── #skip-feed li span carve-out rule (see Pattern 3)
└── no other files change
```

### Pattern 1: Viewport Meta Update (MOB-01 partial)

**What:** Extend the existing viewport meta with two additional tokens.
**When to use:** Single edit, line 5.

```html
<!-- Before -->
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<!-- After -->
<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no, maximum-scale=1">
```

**Confidence note:** iOS Safari (since iOS 10) ignores `user-scalable=no` for pinch zoom when the OS accessibility "Zoom" feature is off and for user-initiated pinch in general. However, `maximum-scale=1` can suppress certain auto-zoom behaviors (e.g., input field focus zoom on older iOS). The D-01 decision to include both is correct — the tokens are low-cost and cover some iOS edge cases.

### Pattern 2: touch-action: manipulation (MOB-01 Android Chrome)

**What:** Add `touch-action: manipulation` to the CSS button rule (covers `.fsm-main-zone`, `.fsm-dropdown-zone`, `#skip-btn`, `#banner-dismiss`, `.info-btn` automatically since they are `<button>` elements).
**When to use:** Applied globally to all buttons via CSS.

```css
/* Source: MDN Web Docs — touch-action property */
button {
  touch-action: manipulation;
}
```

**Scope choice (Claude's Discretion):** Applying to `button` element selector is cleanest — all interactive controls in this file are `<button>` elements or have explicit `cursor: pointer` on `div`-based elements (`.profile-option`). The `.profile-option` elements are `<div>` with click handlers — they would need `touch-action: manipulation` added explicitly, or the rule can be widened to `button, .profile-option`.

**What `manipulation` does and does NOT do:**
- Disables double-tap zoom: YES (Android Chrome and most mobile browsers)
- Disables pinch zoom: NO — pinch zoom remains enabled
- Removes 300ms click delay: YES (on both platforms)
- Works on iOS Safari for double-tap: PARTIALLY — iOS Safari only honours `auto` and `manipulation` (not `pan-y`), but even `manipulation` does not fully suppress pinch zoom on iOS without the viewport meta token

### Pattern 3: user-select: none Broad Rule + Carve-outs (MOB-02)

**What:** Set `user-select: none` on `body`, then restore selectability for track/artist text only.

```css
/* Source: MDN Web Docs — user-select property */

/* Broad rule — covers all UI chrome by inheritance */
body {
  user-select: none;
}

/* Carve-out 1: Now Playing track name */
#now-playing-name {
  user-select: text;
}

/* Carve-out 2: Now Playing artist */
#now-playing-artist {
  user-select: text;
}

/* Carve-out 3: Feed history track and artist spans
   (track span and artist span have no class;
    .feed-sep, .badge, .feed-timestamp DO have classes) */
#skip-feed li span:not(.feed-sep):not(.badge):not(.feed-timestamp) {
  user-select: text;
}
```

**Why this specificity works:** `user-select` is an inherited property. Setting `none` on `body` flows down. The carve-out IDs and the negation selector have sufficient specificity to override the body rule without `!important`.

**Feed history detail:** Track name spans and artist name spans in JS-built `<li>` elements have no CSS class assigned (confirmed in `prependSkipItem()` at lines 949-957 of index.html). They are distinguishable from `.feed-sep`, `.badge`, and `.feed-timestamp` spans by the absence of any class. The `:not()` negation selector reliably identifies them.

**Alternative approach:** Assign explicit CSS classes (`feed-track`, `feed-artist`) in the JS that builds feed items, then use simple class selectors for carve-outs. This is cleaner and more maintainable than negation selectors, though it requires a small JS change in `prependSkipItem()`. Either approach is valid — the negation approach avoids touching JS entirely.

### Pattern 4: Skip Track Button Inline Style Interaction

**What:** `#skip-btn` is defined with `style="..."` inline (line 602 of index.html). CSS rules in `<style>` have lower specificity than inline styles for properties specified inline — but `user-select` is NOT set inline, so the body rule applies to it without conflict.

**Verification:** The inline style on `#skip-btn` contains: `margin-top`, `width`, `height`, `border`, `border-radius`, `background`, `color`, `font-family`, `font-size`, `font-weight`, `cursor`. No `user-select` or `touch-action` inline — both can be set via CSS rules without specificity conflict.

### Anti-Patterns to Avoid

- **Applying `user-select: none` per-element on each chrome item:** 6+ elements to maintain; the broad-then-carve approach requires fewer rules and is less prone to missing new elements added later.
- **Using `touch-action: pan-y` for pinch zoom suppression on iOS:** iOS Safari does not support `pan-y` — only `auto` and `manipulation`. Using `pan-y` on `body` would be silently ignored on iOS.
- **Relying solely on `user-scalable=no` for double-tap zoom on Android Chrome:** Android Chrome can ignore this in some versions — `touch-action: manipulation` is the reliable signal for Chrome.
- **Using `!important` on carve-outs:** Not needed; natural specificity of ID selectors over body suffices.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Double-tap zoom disable | JavaScript touchstart/touchend timer | `touch-action: manipulation` CSS | Native browser optimization; no event interference |
| Text selection prevention | JS mousedown preventDefault | `user-select: none` CSS | CSS handles all selection modes (keyboard, pointer, long-press) |
| Per-element selection blocking | Adding `user-select: none` to each button individually | Body-level rule + carve-outs | Maintenance: new chrome elements are covered automatically |

## Common Pitfalls

### Pitfall 1: iOS Ignores user-scalable=no for Pinch Zoom
**What goes wrong:** Developer adds `user-scalable=no` expecting pinch zoom to be fully disabled on iOS, but users can still pinch zoom.
**Why it happens:** Apple disabled this behavior in iOS 10 for accessibility reasons. The setting is now only partially effective (may suppress auto-zoom on input focus in some configurations).
**How to avoid:** Accept that pinch zoom cannot be fully disabled on iOS via HTML/CSS alone without JavaScript event interception. The phase scope (D-01/D-02) accepts this trade-off — the goal is double-tap zoom, not full pinch lock.
**Warning signs:** Testing on physical iOS device shows pinch still works despite the meta tag.

### Pitfall 2: iOS Safari touch-action Limited Values
**What goes wrong:** Using `touch-action: pan-y` on body to block pinch zoom — works in Chrome but silently ignored in iOS Safari.
**Why it happens:** iOS Safari only supports `auto` and `manipulation` values for `touch-action`.
**How to avoid:** Use `manipulation` (not `pan-y`) on interactive elements. Accept pinch-zoom still works on iOS. The phase's D-01 correctly avoids `pan-y`.
**Warning signs:** No visible error; iOS Safari behaves as if the rule isn't there.

### Pitfall 3: Negation Selector Class Name Drift
**What goes wrong:** A future change adds a class to the artist or track span in `prependSkipItem()`, breaking the negation selector carve-out.
**Why it happens:** The carve-out `span:not(.feed-sep):not(.badge):not(.feed-timestamp)` depends on track/artist spans being classless.
**How to avoid:** If using the negation approach, document the dependency. Alternatively, assign explicit `feed-track` and `feed-artist` classes in JS (the cleaner long-term solution, at the cost of a minor JS touch).
**Warning signs:** After adding a class to a span, its text becomes unselectable.

### Pitfall 4: WebKit Prefix for user-select
**What goes wrong:** Older WebKit/iOS browsers require `-webkit-user-select`.
**Why it happens:** `user-select` was unprefixed in WebKit relatively recently.
**How to avoid:** Add `-webkit-user-select` alongside the unprefixed property as a defensive measure, since this project likely runs on iOS devices that may use older Safari versions.
**Warning signs:** Text remains selectable on older iOS Safari despite the CSS rule.

```css
/* Defensive cross-browser user-select */
body {
  -webkit-user-select: none;
  user-select: none;
}
/* Carve-out also needs the prefix */
#now-playing-name {
  -webkit-user-select: text;
  user-select: text;
}
```

### Pitfall 5: .profile-option Elements Not Covered by button Rule
**What goes wrong:** `.profile-option` divs still double-tap zoom because `touch-action: manipulation` was only applied to `button`.
**Why it happens:** Profile options are `<div>` elements with click handlers, not `<button>` elements.
**How to avoid:** Widen the `touch-action` rule: `button, .profile-option { touch-action: manipulation; }`. Or apply it broadly on the container.
**Warning signs:** Double-tap on profile dropdown options triggers zoom on Android.

## Code Examples

### Complete CSS additions (consolidated)

```css
/* Source: MDN Web Docs — user-select, touch-action */

/* MOB-02: Prevent accidental text selection on all UI chrome */
body {
  -webkit-user-select: none;
  user-select: none;
}

/* MOB-01: Prevent double-tap zoom on interactive elements (Android Chrome) */
button,
.profile-option {
  touch-action: manipulation;
}

/* MOB-02 carve-outs: keep track/artist text selectable */
#now-playing-name,
#now-playing-artist {
  -webkit-user-select: text;
  user-select: text;
}

/* Feed history track + artist spans (no class; .feed-sep/.badge/.feed-timestamp have classes) */
#skip-feed li span:not(.feed-sep):not(.badge):not(.feed-timestamp) {
  -webkit-user-select: text;
  user-select: text;
}
```

### Viewport meta (single line edit, line 5)

```html
<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no, maximum-scale=1">
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `user-scalable=no` blocks all iOS zoom | Ignored since iOS 10 for pinch; partially effective for auto-zoom | 2016 (iOS 10) | Cannot fully lock pinch zoom on iOS via meta tag alone |
| JS touchstart preventDefault for zoom | `touch-action: manipulation` CSS | ~2015 (CSS4) | Native; no event handler needed |
| Per-vendor-prefix-only `user-select` | `user-select` unprefixed (with `-webkit-` as fallback) | 2022-2023 | Include `-webkit-` for older iOS; unprefixed for modern |

## Environment Availability

Step 2.6: SKIPPED — no external dependencies. This phase modifies one HTML file with CSS and a meta attribute. No tools, services, CLIs, or runtimes beyond the project's own code are required.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | none (uses defaults; conftest.py adds project root to sys.path) |
| Quick run command | `/home/cgallarno/Development/spotify-sentiment/.venv/bin/python3 -m pytest tests/test_mobile_polish.py -x -q` |
| Full suite command | `/home/cgallarno/Development/spotify-sentiment/.venv/bin/python3 -m pytest tests/ -q` |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MOB-01 | Viewport meta contains `user-scalable=no` and `maximum-scale=1` | unit (string parse) | `.venv/bin/python3 -m pytest tests/test_mobile_polish.py::test_viewport_meta_zoom_disabled -x` | No — Wave 0 |
| MOB-01 | `touch-action: manipulation` appears in `<style>` block | unit (string parse) | `.venv/bin/python3 -m pytest tests/test_mobile_polish.py::test_touch_action_manipulation_present -x` | No — Wave 0 |
| MOB-02 | `user-select: none` applied to `body` in CSS | unit (string parse) | `.venv/bin/python3 -m pytest tests/test_mobile_polish.py::test_user_select_none_on_body -x` | No — Wave 0 |
| MOB-02 | `#now-playing-name` has `user-select: text` carve-out | unit (string parse) | `.venv/bin/python3 -m pytest tests/test_mobile_polish.py::test_now_playing_name_selectable -x` | No — Wave 0 |
| MOB-02 | `#now-playing-artist` has `user-select: text` carve-out | unit (string parse) | `.venv/bin/python3 -m pytest tests/test_mobile_polish.py::test_now_playing_artist_selectable -x` | No — Wave 0 |
| MOB-02 | Feed span carve-out rule present in CSS | unit (string parse) | `.venv/bin/python3 -m pytest tests/test_mobile_polish.py::test_feed_span_carveout_present -x` | No — Wave 0 |
| MOB-02 | Actual browser selectability of track/artist text | manual | In-browser: long-press on track name on mobile — must select | — |

**Note on test approach:** The established project pattern (see `tests/test_info_icon.py`) is to parse `index.html` as a string and assert CSS selectors/values are present. This is sufficient to verify the correct CSS rules are written — actual rendering behavior on device requires manual verification.

### Sampling Rate

- **Per task commit:** `.venv/bin/python3 -m pytest tests/test_mobile_polish.py -x -q`
- **Per wave merge:** `.venv/bin/python3 -m pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_mobile_polish.py` — covers MOB-01 and MOB-02 string-parse assertions (6 tests)

## Sources

### Primary (HIGH confidence)
- MDN Web Docs — `touch-action` property — manipulation definition, browser compat, iOS Safari limited value support
- MDN Web Docs — `user-select` property — inheritance behavior, carve-out mechanics, `user-select: text` override
- Caniuse.com — `user-select: none` — 97/100 browser compatibility score

### Secondary (MEDIUM confidence)
- [lukeplant.me.uk — "You can stop using user-scalable=no and maximum-scale=1 in viewport meta tags now"](https://lukeplant.me.uk/blog/posts/you-can-stop-using-user-scalable-no-and-maximum-scale-1-in-viewport-meta-tags-now/) — verifies iOS Safari ignores user-scalable since iOS 10; recommends touch-action as alternative
- [dev.to/jasperreddin — "Disabling Viewport Zoom on iOS 14 Web Browsers"](https://dev.to/jasperreddin/disabling-viewport-zoom-on-ios-14-web-browsers-l13) — confirms iOS Safari supports only `auto` and `manipulation` for touch-action (not `pan-y`)
- [raulmelo.me — "Disable Double-Tap Zoom with CSS touch-action"](https://raulmelo.me/en/til/disable-double-tap-zoom-css-touch-action) — confirms `manipulation` disables double-tap zoom on Android Chrome

### Source: Code inspection (HIGH confidence)
- `web_ui/templates/index.html` lines 1-543 — confirmed: viewport meta at line 5; CSS style block; button elements; inline style on `#skip-btn`; feed history JS at lines 940-981 confirming track/artist spans have no class

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — CSS properties verified against MDN; no packages involved
- Architecture: HIGH — patterns derived from reading actual index.html structure
- Pitfalls: HIGH (iOS behavior) / MEDIUM (browser-specific edge cases) — iOS10+ behavior documented in multiple sources

**Research date:** 2026-04-06
**Valid until:** 2026-10-06 (CSS properties are stable; viewport meta behavior unlikely to change soon)
