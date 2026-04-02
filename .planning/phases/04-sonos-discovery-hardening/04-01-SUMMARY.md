---
phase: 04-sonos-discovery-hardening
plan: 01
subsystem: testing
tags: [pytest, tdd, sonos, ssdp, discovery, asyncio]

# Dependency graph
requires: []
provides:
  - Failing test scaffold for probe_sonos_speakers (DISC-01, DISC-02, DISC-03)
  - Failing tests asserting updated warning text in SocoSkipClient.skip() and .pause()
affects:
  - 04-02 (implements probe_sonos_speakers to make these tests GREEN)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "TDD RED phase: import-failing tests signal unimplemented functions"
    - "caplog.at_level pattern for asserting structured log messages in async tests"
    - "patch.dict(os.environ) combined with os.environ.pop for clean env var isolation"

key-files:
  created:
    - tests/test_sonos_probe.py
  modified:
    - tests/test_skip_client.py

key-decisions:
  - "Tests import probe_sonos_speakers directly from daemon — failure at ImportError is intentional RED state"
  - "Patch target is 'daemon.soco.discovery.discover' not 'soco.discovery.discover' — matches how daemon.py imports soco"
  - "Pre-existing test_soco_pause_uses_cached_ip and test_soco_pause_falls_back_to_discovery_when_not_cached failures are out-of-scope; documented in deferred-items.md"

patterns-established:
  - "Probe test pattern: patch env var + soco.discovery.discover, assert log message via caplog"
  - "Two-assertion WARNING pattern: check both 'multicast UDP port 1900' AND 'SONOS_SPEAKER_IPS' are in combined warning text"

requirements-completed:
  - DISC-01
  - DISC-02
  - DISC-03

# Metrics
duration: 3min
completed: 2026-04-02
---

# Phase 4 Plan 01: Sonos Discovery TDD Red Phase Summary

**TDD RED scaffold: 6 failing probe tests + 2 failing warning-text tests establish behavioral contracts for DISC-01, DISC-02, DISC-03 before any implementation**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-04-02T19:24:27Z
- **Completed:** 2026-04-02T19:27:30Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Created tests/test_sonos_probe.py with 6 failing tests covering all three discovery behaviors (SSDP path, IP override path, no-speaker warning path)
- Appended 2 failing tests to tests/test_skip_client.py asserting updated warning text with multicast/port/env hints
- All 8 new tests are RED (fail with ImportError or assertion failure) because probe_sonos_speakers does not yet exist
- 5 pre-existing passing tests remain GREEN and unmodified

## Task Commits

Each task was committed atomically:

1. **Task 1: Write failing tests for probe_sonos_speakers** - `668efbc` (test)
2. **Task 2: Add failing tests for updated warning text** - `c81bd74` (test)

## Files Created/Modified

- `tests/test_sonos_probe.py` — New test file: 6 async tests for probe_sonos_speakers covering DISC-01 (SSDP discovery), DISC-02 (IP override bypass), DISC-03 (actionable warning when no speakers found)
- `tests/test_skip_client.py` — Appended 2 tests: test_soco_skip_warning_includes_multicast_hint, test_soco_pause_warning_includes_multicast_hint; assert warning text updated in Plan 04-02

## Decisions Made

- Used `patch("daemon.soco.discovery.discover")` as the patch target (not `soco.discovery.discover`) since the implementation will access soco through daemon's module namespace
- Tests use `from daemon import probe_sonos_speakers` inside each test body so ImportError is the RED signal (if placed at module level, collection would fail differently)

## Deviations from Plan

### Observed but Out of Scope

**1. [Out of Scope] Pre-existing test_skip_client.py failures**
- **Found during:** Task 2 verification
- **Tests:** test_soco_pause_uses_cached_ip, test_soco_pause_falls_back_to_discovery_when_not_cached
- **Issue:** Both were already failing before Plan 04-01 began (verified by git stash check)
- **Action:** Documented in deferred-items.md; not fixed (out of scope per deviation rule boundary)
- **Impact:** Does not affect Plan 04-01 success criteria — these are pre-existing, not introduced by this plan

---

**Total deviations:** 0 auto-fixes applied
**Impact on plan:** None — plan executed exactly as written; pre-existing failures documented but not in scope

## Issues Encountered

- `python -m pytest` failed (no system pytest); resolved by using `.venv/bin/python -m pytest` which is the correct venv for this project

## Known Stubs

None — this is a test-only plan. No production code was added.

## Next Phase Readiness

- Plan 04-02 can now implement probe_sonos_speakers in daemon.py to make all 6 probe tests GREEN
- Plan 04-02 must also update SocoSkipClient.skip() and .pause() warning text to make 2 new tests GREEN
- The patch target `daemon.soco.discovery.discover` constrains how daemon.py must import soco (must use `import soco` at module level, not `from soco.discovery import discover`)

---
*Phase: 04-sonos-discovery-hardening*
*Completed: 2026-04-02*
