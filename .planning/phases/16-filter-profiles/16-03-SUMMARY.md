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
  duration: "2m37s"
  completed: "2026-04-05"
  tasks_completed: 2
  files_modified: 1
---

# Phase 16 Plan 03: Split-Button UI Summary

Split-button FSM/profile control with CSS dropdown; left zone toggles FSM on/off, right zone opens profile selector with checkmark indicator on active profile.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Replace FSM CSS + HTML with split-button structure | 2b8c114 | web_ui/templates/index.html |
| 2 | Replace FSM JS with split-button JS (click zones, dropdown, profile selection) | 1cd4952 | web_ui/templates/index.html |

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

None — plan executed exactly as written.

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

## Checkpoint: Awaiting Human Verification

The plan includes a `checkpoint:human-verify` gate (Task 3) requiring browser visual inspection:
1. Start web_ui: `cd /home/cgallarno/Development/spotify-sentiment/web_ui && uvicorn main:app --port 8080 --reload`
2. Open http://localhost:8080
3. Verify split button renders with profile name + ▾
4. Test click zone separation (left = FSM toggle, right = dropdown only)
5. Test profile selection (POST /profile, label update, dropdown close)
6. Test outside-click and Escape dismiss
7. Test FSM on/off color states

## Self-Check: PASSED

- FOUND: web_ui/templates/index.html
- FOUND: .planning/phases/16-filter-profiles/16-03-SUMMARY.md
- FOUND commit: 2b8c114 (Task 1 — CSS + HTML)
- FOUND commit: 1cd4952 (Task 2 — JS)
