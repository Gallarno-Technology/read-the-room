---
phase: 16-filter-profiles
plan: "03"
subsystem: web_ui/templates
tags: [frontend, ui, html, css, js, split-button, profile-selector]
dependency_graph:
  requires: [16-02]
  provides: [PROF-01, PROF-04]
  affects: [web_ui/templates/index.html]
tech_stack:
  added: []
  patterns: [split-button compound element, CSS custom dropdown, click-zone separation via stopPropagation, aria-expanded/aria-haspopup accessibility]
key_files:
  created: []
  modified:
    - web_ui/templates/index.html
decisions:
  - "Profile dropdown uses position:absolute on .card (position:relative) for full-width alignment below the split button — no JS measurement needed"
  - "Dropdown close added to es.onopen (SSE reconnect) to prevent stale open dropdown after reconnect"
  - "FSM toggle listener on #fsm-toggle (left zone only), not on container — prevents right zone click from toggling FSM without needing stopPropagation on the main zone"
metrics:
  duration: "~25min (including human verification + post-checkpoint fixes)"
  completed: "2026-04-05"
  tasks_completed: 3
  files_modified: 1
---

# Phase 16 Plan 03: Split-Button UI Summary

Split-button FSM/profile control with CSS dropdown; left zone toggles FSM on/off, right zone opens profile selector with checkmark indicator on active profile.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Replace FSM CSS + HTML with split-button structure | 2b8c114 | web_ui/templates/index.html |
| 2 | Replace FSM JS with split-button JS (click zones, dropdown, profile selection) | 1cd4952 | web_ui/templates/index.html |
| 3 | Human verification checkpoint — APPROVED | — | — |
| 4 (post-checkpoint) | Fix button text color + dropdown width/corner attachment | c4214fa | web_ui/templates/index.html |

## What Was Built

**CSS changes (`web_ui/templates/index.html`):**
- Replaced `#fsm-toggle { ... }`, `.fsm-on`, `.fsm-off` (single button rules) with:
  - `.fsm-split` container (flex, 44px height, 6px border-radius, overflow:hidden)
  - `.fsm-main-zone` left zone (flex:1, transparent bg, text-align:left)
  - `.fsm-dropdown-zone` right zone (40px wide, border-left separator)
  - `.fsm-split.fsm-on` / `.fsm-split.fsm-off` for container-level color state
  - `.profile-dropdown` absolute-positioned panel (top:44px, z-index:10)
  - `.profile-option` and `.profile-option--active` with `::before` checkmark (U+2713 + nbsp)

**HTML changes (`web_ui/templates/index.html`):**
- Replaced `<button id="fsm-toggle" class="fsm-off">` single button with compound structure:
  - `<div id="fsm-split-btn">` container with `<button id="fsm-toggle" class="fsm-main-zone">` + `<button id="profile-dropdown-trigger">` (▾ trigger)
  - `<div id="profile-dropdown">` with 4 `.profile-option` divs for all profiles

**JS changes (`web_ui/templates/index.html`):**
- Added `activeProfile = PROFILE_INITIAL || "kids_present"` state variable
- Added `fsmSplitBtn`, `fsmMainZone`, `profileTrigger`, `profileDropdown` DOM references
- Replaced `setFsmUI(enabled)` with `setFsmUI(enabled, profile)` that:
  - Updates `fsmSplitBtn.className` (fsm-split fsm-on/fsm-off)
  - Shows profile display name (PROFILE_DISPLAY_NAMES lookup) or "The Library is Closed" for fresh install
  - Updates `profile-option--active` class and `aria-selected` on all dropdown options
- Added `PROFILE_DISPLAY_NAMES` lookup for all 4 profiles
- Moved FSM click listener to `fsmMainZone` (left zone only)
- Added `profileTrigger` click handler with `e.stopPropagation()` (D-05)
- Added `profileDropdown` click handler: optimistic update + `POST /profile` + revert on error
- Added document click handler for outside-click dropdown dismiss (D-10)
- Added document keydown handler for Escape dismiss (D-10)
- Added dropdown close in `es.onopen` SSE reconnect handler (Pitfall 5)

## Deviations from Plan

### Post-Checkpoint Visual Fixes (human-approved)

After the human checkpoint was approved, two additional visual fixes were applied and committed as `c4214fa`:

**1. [Post-checkpoint - Visual Fix] Added `color: inherit` to child button zones**
- **Found during:** Human verification (checkpoint)
- **Issue:** `.fsm-main-zone` and `.fsm-dropdown-zone` had `background: transparent` but no explicit `color`, so browser default button color overrode the container's color in some states — button text appeared wrong color (black instead of gold or var(--text))
- **Fix:** Added `color: inherit` to both `.fsm-main-zone` and `.fsm-dropdown-zone` CSS rules
- **Files modified:** `web_ui/templates/index.html`
- **Committed in:** `c4214fa`

**2. [Post-checkpoint - Visual Fix] Introduced `.fsm-btn-wrapper` for dropdown width + corner attachment**
- **Found during:** Human verification (checkpoint)
- **Issue:** Dropdown was positioned relative to `.card` (wider than button) — dropdown appeared wider than the button; also had `border-radius: 6px` on all corners even when attached to open button
- **Fix:** Introduced `.fsm-btn-wrapper` div (position: relative) wrapping `#fsm-split-btn` + `#profile-dropdown`. Added `dropdown-open` class on `#fsm-split-btn` for corner-radius attachment (6px 6px 0 0 on button, 0 0 6px 6px on dropdown). Added `openDropdown()`/`closeDropdown()` helpers managing `hidden`, `aria-expanded`, and `dropdown-open` atomically. Refactored all open/close call sites to use helpers
- **Files modified:** `web_ui/templates/index.html`
- **Committed in:** `c4214fa`

---

**Total deviations:** 2 post-checkpoint visual fixes
**Impact on plan:** Both fixes improve visual correctness. No behavior or API surface changes. All plan success criteria remain satisfied.

## Deferred Issues

**Pre-existing test failure (out of scope):** `tests/test_skip_client.py::test_soco_pause_uses_cached_ip`
- Confirmed failing before any plan 16-03 changes via `git stash` verification
- Unrelated to HTML/CSS/JS changes in this plan
- `SocoSkipClient.pause()` does not call `speaker.pause()` — implementation gap in skip client
- Logged to `deferred-items.md`

## Test Results

All 82 non-skip-client tests pass: `pytest tests/ --ignore=tests/test_skip_client.py -x -q` → 82 passed, 27 warnings

The pre-existing `test_soco_pause_uses_cached_ip` failure was present before plan 16-03 changes.

## Known Stubs

None — the `PROFILE_INITIAL` placeholder is consumed server-side via `html.replace("__PROFILE_INITIAL__", active_profile)` in `web_ui/main.py` (implemented in plan 16-02). The value is always a valid profile key from `state.json`.

## Checkpoint: APPROVED

The `checkpoint:human-verify` gate (Task 3) was completed and approved by the human. All 11 verification checks passed. Two post-checkpoint visual fixes were applied and committed as `c4214fa` following approval.

## Self-Check: PASSED

- FOUND: web_ui/templates/index.html
- FOUND: .planning/phases/16-filter-profiles/16-03-SUMMARY.md
- FOUND commit: 2b8c114 (Task 1 — CSS + HTML)
- FOUND commit: 1cd4952 (Task 2 — JS)
- FOUND commit: c4214fa (post-checkpoint fixes — color + dropdown wrapper)
