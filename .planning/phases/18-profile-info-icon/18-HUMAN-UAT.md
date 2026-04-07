---
status: diagnosed
phase: 18-profile-info-icon
source: [18-VERIFICATION.md]
started: 2026-04-06T00:00:00.000Z
updated: 2026-04-06T04:00:00.000Z
---

## Current Test

[testing complete]

## Tests

### 1. Desktop popover behavior
expected: Clicking ⓘ opens a popover flyout (≥640px viewport) showing profile name + prose sentence. Outside-click, Escape key, and second ⓘ tap all dismiss it. Switching profiles while open updates the content live.
result: pass

### 2. Mobile bottom-sheet behavior
expected: Tapping ⓘ at ≤640px viewport slides up a bottom-sheet with profile name + prose sentence. Backdrop tap dismisses it. Profile dropdown z-index is not regressed (dropdown still renders above other elements when open).
result: issue
reported: "the info button overlaps the top right corner of the button, it should be above the button, inside the card. perhaps we can add a header to the button card, the info icon be right aligned with that. title should say: 'House Rules'. the popover / sheet should explain all modes, regardless of which is active."
severity: major

## Summary

total: 2
passed: 1
issues: 1
pending: 0
skipped: 0
blocked: 0

## Gaps

- truth: "ⓘ button positioned above profile button, inside card; card has 'House Rules' header with icon right-aligned; popover/sheet explains all modes regardless of active one"
  status: failed
  reason: "User reported: the info button overlaps the top right corner of the button, it should be above the button, inside the card. perhaps we can add a header to the button card, the info icon be right aligned with that. title should say: 'House Rules'. the popover / sheet should explain all modes, regardless of which is active."
  severity: major
  test: 2
  root_cause: ".info-btn uses position:absolute top:10px right:10px as a sibling to .fsm-btn-wrapper inside the card, landing it directly over the profile button's dropdown trigger zone; openInfo() only renders the active profile's description from PROFILE_INFO instead of all four"
  artifacts:
    - path: "web_ui/templates/index.html"
      issue: "Line 540: card has inline position:relative but no header row; line 554: #info-btn is absolute-positioned sibling to profile button; lines 267-279: .info-btn CSS uses position:absolute top/right; lines 707-724: openInfo() only reads PROFILE_INFO[activeProfile]"
  missing:
    - "Add flex card-header row inside the profile card with <h2>House Rules</h2> left and #info-btn right (normal flow, not absolute)"
    - "Remove position:absolute from .info-btn CSS, make it a flex child"
    - "Update openInfo() and #info-panel markup to render all four entries from PROFILE_INFO, not just the active one"
  debug_session: ""
