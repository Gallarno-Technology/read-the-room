---
phase: 18-profile-info-icon
plan: 01
subsystem: ui
tags: [html, css, javascript, info-icon, popover, bottom-sheet, responsive]

# Dependency graph
requires:
  - phase: 16-filter-profiles
    provides: activeProfile JS variable, PROFILE_DISPLAY_NAMES map, setFsmUI() function, FSM card with position:relative
provides:
  - Always-visible ⓘ button in FSM card top-right corner
  - Desktop popover showing active profile name and content description
  - Mobile bottom-sheet sliding up from viewport bottom with dark backdrop
  - Static PROFILE_INFO JS map with prose descriptions for all 4 profiles
  - test_info_icon.py with 4 automated INFO-01/INFO-02 template-parse tests
affects: [19-mobile-ux, any future ui-polish phases]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - class-based slide-up animation (requestAnimationFrame + info-panel--open, avoids hidden/transition conflict)
    - isMobile() media query helper for JS-side responsive branching
    - static JS map (PROFILE_INFO) as data source, no new API endpoint

key-files:
  created:
    - tests/test_info_icon.py
  modified:
    - web_ui/templates/index.html

key-decisions:
  - "Info icon placed in FSM card top-right (position: absolute inside existing position: relative card) — no structural markup change"
  - "Static PROFILE_INFO JS map (no /profile-info API endpoint) — content is stable, no round-trip needed (D-07)"
  - "Mobile bottom-sheet uses class-based open/close (info-panel--open) not hidden attribute to enable CSS transitions (Pitfall 1 workaround)"
  - "infoBackdrop placed inside .page-wrap, not .card, to avoid overflow clipping (Pitfall 3)"
  - "e.stopPropagation() on infoBtn click prevents outside-click handler from immediately closing panel (Pitfall 4)"

patterns-established:
  - "Info panel open/close: openInfo()/closeInfo() mirror openDropdown()/closeDropdown() pattern exactly"
  - "Live update on profile change: check infoPanel.hasAttribute('hidden') inside setFsmUI() (D-05)"

requirements-completed: [INFO-01, INFO-02]

# Metrics
duration: 5min
completed: 2026-04-06
---

# Phase 18 Plan 01: Profile Info Icon Summary

**Always-visible ⓘ button on FSM card showing desktop popover / mobile bottom-sheet with active profile's content filtering description**

## Performance

- **Duration:** 5 min
- **Started:** 2026-04-06T12:14:14Z
- **Completed:** 2026-04-06T12:18:46Z
- **Tasks:** 3 auto + 1 auto-approved checkpoint = 4 total
- **Files modified:** 2

## Accomplishments
- Added #info-btn (absolutely positioned top-right of FSM card, always visible regardless of FSM on/off)
- Desktop popover: simple hidden attribute toggle with absolute positioning anchored to card top-right
- Mobile bottom-sheet: class-based open/close with CSS transform transition and dark backdrop overlay
- PROFILE_INFO static JS map with correct prose descriptions for all 4 profiles
- setFsmUI() extended to live-update panel content when profile changes while panel is open
- 4 automated pytest tests in test_info_icon.py covering INFO-01 and INFO-02 structural evidence

## Task Commits

Each task was committed atomically:

1. **Task 1: Create test scaffold for INFO-01** - `b3803fa` (test)
2. **Task 2: Add HTML markup and all CSS styles** - `712f4b6` (feat)
3. **Task 3: Add JS logic — PROFILE_INFO, open/close, live update** - `cd727f3` (feat)
4. **Task 4: Human visual verification** - auto-approved (checkpoint:human-verify, --auto mode)

## Files Created/Modified
- `tests/test_info_icon.py` - 4 template-parse tests for INFO-01/INFO-02 (created)
- `web_ui/templates/index.html` - ⓘ button, info panel, backdrop HTML; .info-btn/.info-panel/.info-backdrop CSS; @media (max-width: 640px) bottom-sheet overrides; PROFILE_INFO JS map; openInfo/closeInfo functions; all event handlers (modified)

## Decisions Made
- Static JS map (`PROFILE_INFO`) chosen over a new API endpoint — profile descriptions are stable and static (D-07)
- Mobile bottom-sheet uses class toggle (`info-panel--open`) rather than `hidden` attribute for animation, to work around CSS transition-on-hidden-element limitation (Pitfall 1)
- Backdrop placed inside `.page-wrap` (not inside `.card`) to prevent overflow clipping on fixed-position element (Pitfall 3)

## Deviations from Plan

None — plan executed exactly as written. All pitfall avoidance strategies documented in RESEARCH.md were applied as specified.

## Issues Encountered

Pre-existing failing test `tests/test_skip_client.py::test_soco_pause_uses_cached_ip` was discovered during full-suite run. Confirmed it pre-dates this phase (reproduced on stashed state). Out of scope — logged for awareness, not fixed.

## Known Stubs

None — all four profile descriptions are fully wired to the PROFILE_INFO map. The info panel content is not hardcoded placeholder text; it reads from the live `activeProfile` JS variable.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- INFO-01 and INFO-02 requirements fully implemented and tested
- Phase 18 complete (1 of 1 plans done)
- v1.5 milestone remaining work: mobile UX (disable pinch-zoom, limit text selection on UI chrome)

## Self-Check: PASSED

All files confirmed present: tests/test_info_icon.py, web_ui/templates/index.html, 18-01-SUMMARY.md
All commits confirmed: b3803fa, 712f4b6, cd727f3

---
*Phase: 18-profile-info-icon*
*Completed: 2026-04-06*
