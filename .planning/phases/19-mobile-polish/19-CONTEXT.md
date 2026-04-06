# Phase 19: Mobile Polish - Context

**Gathered:** 2026-04-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix two mobile UX issues in `web_ui/templates/index.html` only:
1. Prevent accidental pinch-zoom and double-tap zoom on the dashboard viewport (MOB-01)
2. Prevent accidental text selection on UI chrome elements; keep track title and artist text selectable everywhere (MOB-02)

No Python changes, no API changes, no new features.

</domain>

<decisions>
## Implementation Decisions

### Zoom Restriction Method
- **D-01:** Apply **both** approaches for full cross-platform coverage:
  - Update viewport meta to add `user-scalable=no, maximum-scale=1` (required for iOS double-tap zoom disable)
  - Add `touch-action: manipulation` on interactive elements (prevents double-tap zoom on Android Chrome without blocking scroll)
- **D-02:** Neither approach alone is sufficient — iOS ignores `touch-action`; Android Chrome can still double-tap-zoom past `user-scalable=no` on some versions.

### user-select Scope Strategy
- **D-03:** Apply `user-select: none` **broadly** (on `body` or the top-level card container) with **explicit opt-in carve-outs** for selectable text — lower maintenance than targeting each of the 6+ chrome elements individually.
- **D-04:** UI chrome that gets `none` (covered by the broad rule): buttons, badges, labels, profile options, info icon, split-button zones, card headers.

### Selectable Text Carve-outs
- **D-05:** Track title and artist text remain selectable **everywhere they appear** — both in the Now Playing section AND in skip feed history list items.
  - Now Playing: the track name div and `#now-playing-artist`
  - Feed history: track name and artist `<span>` elements within each `<li>`
- **D-06:** Rationale: user may want to copy a song name from history. Consistent rule — all track/artist text is selectable regardless of location.

### Claude's Discretion
- Exact selector specificity (whether to apply broad rule on `body`, `.card`, or a wrapper)
- Whether `touch-action: manipulation` is applied globally or only on `<button>` elements
- CSS specificity ordering to ensure carve-outs override the broad rule cleanly

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §Mobile UX — MOB-01 and MOB-02 (the two acceptance criteria for this phase)
- `.planning/REQUIREMENTS.md` §Out of Scope — "Full mobile responsive layout" explicitly excluded; zoom/select is the only scope

### Source file to modify
- `web_ui/templates/index.html` — the only file that changes; CSS and JS are inline

### Existing viewport meta (line 5)
- Current: `<meta name="viewport" content="width=device-width, initial-scale=1.0">`
- Must be updated to add `user-scalable=no, maximum-scale=1`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Viewport meta at line 5 — direct edit, single token change
- All CSS is inline in `<style>` block — `user-select` rules go there
- `touch-action` can be added to existing button CSS rules (buttons already have cursor/padding rules)

### Established Patterns
- 640px mobile breakpoint established in Phase 18 (popover vs bottom-sheet switch) — consistent with MOB-01/MOB-02 scope (mobile-only concern)
- Badge-group, profile-option, fsm-split-btn, info-btn all have existing CSS classes — the broad `user-select: none` rule will cover them without per-class additions
- Inline style on Skip Track button (line 602) — may need explicit `user-select: none` if broad rule doesn't cover inline-styled elements

### Integration Points
- No JS changes expected — `user-select` and viewport meta are pure CSS/HTML
- Phase 18 bottom sheet and popover are also UI chrome — covered by the broad `user-select: none` rule
- Feed history `<li>` elements: track name in a div, artist in a `<span class="skip-artist">` (line 957) — both need explicit `user-select: text` carve-out

</code_context>

<specifics>
## Specific Ideas

- Track/artist in feed history should be selectable — user might want to copy a song name from history. Consistent rule everywhere: all track/artist text stays selectable.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 19-mobile-polish*
*Context gathered: 2026-04-06*
