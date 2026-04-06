# Phase 18: Profile Info Icon - Context

**Gathered:** 2026-04-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Add an ⓘ icon to the FSM control card. Tapping or clicking it reveals a plain-prose breakdown of what the active filter profile skips — updates automatically when the profile changes. All changes confined to `web_ui/templates/index.html`.

</domain>

<decisions>
## Implementation Decisions

### Icon Placement
- **D-01:** The ⓘ icon is absolutely positioned in the **top-right corner of the FSM card**. The card already has `position: relative` — no structural change needed.
- **D-02:** Icon is visible at all times regardless of FSM on/off state (INFO-01).

### Reveal Mechanism
- **D-03:** **Responsive reveal** — popover flyout on desktop (≥640px viewport width); bottom sheet that slides up from the bottom of the viewport on mobile (≤640px).
- **D-04:** Dismiss on outside click (desktop popover) or tap outside the sheet (mobile). Second tap on ⓘ also closes it.
- **D-05:** The breakdown updates when the active profile changes — JS re-renders content on each open (reads current profile state at open time), or updates live if already open.

### Info Content Format
- **D-06:** Content is **profile name as a heading** followed by a **plain prose sentence** describing what the profile skips.
  - Kids Present: "Skips profanity, drug references, sexual content, and explicit-flagged tracks."
  - We're All Adults: "Skips profanity and sexual content."
  - Above The Covers: "Skips sexual content."
  - Permissive: "Skips explicit-flagged tracks."
- **D-07:** Content is driven by a **static JS map** in index.html (no new API endpoint). Profile names and sentences are hardcoded constants — no round-trip needed since PROFILE_MAP is stable.

### Claude's Discretion
- Exact CSS for the popover (shadow, border, padding, width)
- Exact CSS for the bottom sheet (slide-up animation, overlay backdrop)
- Icon button size, color, and hover/active states
- Z-index layering relative to the profile dropdown

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §Profile Info — INFO-01, INFO-02 (the two acceptance criteria for this phase)
- `.planning/REQUIREMENTS.md` §Out of Scope — "Info icon inside the dropdown per-option" explicitly excluded

### Source file to modify
- `web_ui/templates/index.html` — the only file that changes; CSS and JS are inline

### Profile data reference
- `daemon.py` lines 51–83 — `PROFILE_MAP` definitions: the four profiles and their boolean flags (`explicit_skip`, `profanity`, `drug`, `sexual`, `lyrics`). Use this to verify the static JS sentences match the actual rules.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- FSM card (`<div class="card" style="position: relative">`, index.html ~line 448) — `position: relative` already set; top-right absolute positioning available without markup changes
- `now_playing.json` / SSE state — `active_profile` field is already delivered to the frontend on every state update; JS can read this to populate the popover content
- Profile dropdown close logic (index.html ~line 624) — existing outside-click handler pattern to follow for popover dismiss

### Established Patterns
- Profile dropdown (`#profile-dropdown`) uses `hidden` attribute toggle + JS open/close functions — same pattern for popover open/close
- Outside-click guard: `if (!profileDropdown.hidden && !fsmSplitBtn.contains(e.target)) closeDropdown()` — mirror this for the info popover
- Badge rgba color system — may inform popover border/background styling

### Integration Points
- SSE handler already updates the active profile name in the UI — the info popover must read the same `active_profile` state variable and re-render when it changes
- `position: relative` card with `z-index` of profile dropdown — info popover z-index must stack correctly without clipping

</code_context>

<specifics>
## Specific Ideas

- Responsive breakpoint: 640px (same breakpoint Phase 19 will use for mobile polish — establish the pattern here)
- Bottom sheet on mobile should feel like a native drawer: slides up from bottom edge, has a visible handle or close button (✖)
- Desktop popover anchors to the ⓘ icon position (top-right of card)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 18-profile-info-icon*
*Context gathered: 2026-04-06*
