---
id: SEED-012
status: dormant
planted: 2026-04-05
planted_during: v1.4 — Dashboard Polish & Filter Profiles
trigger_when: when a milestone focuses on dashboard UX or visual polish
scope: Small
---

# SEED-012: Increase mobile friendliness — no zoom, limited text selection

## Why This Matters

The dashboard is used on phones (typically the parent's phone on the couch).
Browser default behaviors — pinch-zoom, double-tap zoom, text selection on
buttons and labels — make it feel like a webpage instead of an app control
panel. Disabling these makes the UI feel native and intentional.

## When to Surface

**Trigger:** When a milestone focuses on dashboard UX or visual polish

This seed should be presented during `/gsd:new-milestone` when the milestone
scope matches any of these conditions:
- Dashboard UX, visual polish, or "feels like an app" improvements
- Any milestone that touches `index.html` layout or CSS
- A pre-release / public launch milestone focused on first impressions

## Scope Estimate

**Small** — A few hours. Concretely:
- Update the `<meta name="viewport">` tag to add `user-scalable=no` (prevents
  pinch-zoom and double-tap zoom on iOS/Android)
- Add `user-select: none` to UI chrome elements (buttons, labels, profile
  options, status text) so tapping doesn't highlight text
- Review touch target sizes — buttons should be at least 44×44px per Apple HIG
- Test on a real mobile browser (Safari iOS, Chrome Android)

## Breadcrumbs

Related code and decisions found in the current codebase:

- `web_ui/templates/index.html:5` — existing viewport meta tag
  (`width=device-width, initial-scale=1.0`); needs `user-scalable=no` added
- `web_ui/templates/index.html` — all button, label, and `.profile-option`
  elements are candidates for `user-select: none`
- CSS block starting around line 225 — `.profile-dropdown`, `.profile-option`
  styles; touch target sizing review goes here

## Notes

The current viewport tag already sets `initial-scale=1.0` but does not
prevent zoom. The fix is minimal — one attribute addition plus a CSS rule.
`user-select: none` should be scoped to interactive chrome only, not to
content areas like the now-playing track title (users may want to copy that).
