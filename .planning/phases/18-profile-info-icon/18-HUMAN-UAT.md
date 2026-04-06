---
status: partial
phase: 18-profile-info-icon
source: [18-VERIFICATION.md]
started: 2026-04-06T00:00:00.000Z
updated: 2026-04-06T00:00:00.000Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Desktop popover behavior
expected: Clicking ⓘ opens a popover flyout (≥640px viewport) showing profile name + prose sentence. Outside-click, Escape key, and second ⓘ tap all dismiss it. Switching profiles while open updates the content live.
result: [pending]

### 2. Mobile bottom-sheet behavior
expected: Tapping ⓘ at ≤640px viewport slides up a bottom-sheet with profile name + prose sentence. Backdrop tap dismisses it. Profile dropdown z-index is not regressed (dropdown still renders above other elements when open).
result: [pending]

## Summary

total: 2
passed: 0
issues: 0
pending: 2
skipped: 0
blocked: 0

## Gaps
