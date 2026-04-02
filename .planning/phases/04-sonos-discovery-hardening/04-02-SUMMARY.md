---
phase: 04-sonos-discovery-hardening
plan: 02
subsystem: sonos
tags: [soco, ssdp, discovery, asyncio, multicast, python]

# Dependency graph
requires:
  - phase: 04-sonos-discovery-hardening
    plan: 01
    provides: "Failing TDD scaffold: 6 probe tests + 2 warning-text tests"
provides:
  - "probe_sonos_speakers async helper in daemon.py: SSDP discovery at startup with IP override bypass and actionable no-speaker warning"
  - "Updated SocoSkipClient.skip() and .pause() warnings with multicast UDP port 1900 and SONOS_SPEAKER_IPS hints"
  - ".env.example SONOS_SPEAKER_IPS comment reframed as escape hatch"
affects:
  - "05-readme-and-boot-persistence (documents network requirements established here)"

# Tech tracking
tech-stack:
  added:
    - "soco.discovery imported in daemon.py (previously only imported in skip_client.py)"
  patterns:
    - "SSDP probe pattern: run_in_executor(None, soco.discovery.discover) with falsy check (not is None check)"
    - "Non-blocking startup probe: probe_sonos_speakers called in main() between client init and poll_loop, no try/except"
    - "Cache seeding pattern: soco_client._ip_cache[speaker.player_name] = speaker.ip_address in probe function"

key-files:
  created: []
  modified:
    - daemon.py
    - skip_client.py
    - .env.example
    - tests/test_sonos_probe.py

key-decisions:
  - "Use falsy check 'if speakers:' not 'if speakers is None:' — soco.discovery.discover returns either None or empty set on failure"
  - "probe_sonos_speakers has no try/except — startup path, let unexpected exceptions propagate (D-03: non-blocking means informational, not exception-swallowing)"
  - "test_probe_seeds_ip_cache: SocoSkipClient() must be instantiated inside the patch.dict context after SONOS_SPEAKER_IPS is popped — .env pre-seeds the constructor"

patterns-established:
  - "Startup probe pattern: eager SSDP discovery before poll_loop, seeds _ip_cache for zero-latency first skip"
  - "Warning message pattern: actionable 3-point checklist (name match, firewall port, env var fallback)"

requirements-completed:
  - DISC-01
  - DISC-02
  - DISC-03

# Metrics
duration: 3min
completed: 2026-04-02
---

# Phase 4 Plan 02: Sonos Discovery Hardening Implementation Summary

**SSDP auto-discovery wired as first-class startup step in daemon.py with probe_sonos_speakers; actionable multicast warnings in skip_client.py; SONOS_SPEAKER_IPS reframed as escape hatch in .env.example**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-04-02T19:29:54Z
- **Completed:** 2026-04-02T19:33:13Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Implemented `probe_sonos_speakers` async function in daemon.py: calls `soco.discovery.discover` via `run_in_executor`, logs speakers by name+IP, pre-seeds `_ip_cache`, logs actionable warning with "multicast UDP port 1900" and "SONOS_SPEAKER_IPS" when no speakers found, bypasses SSDP when `SONOS_SPEAKER_IPS` is already set
- Wired `await probe_sonos_speakers(soco_skip)` in `main()` between `SocoSkipClient()` instantiation and `poll_loop()`
- Updated both `skip()` and `pause()` warning messages in `SocoSkipClient` with 3-point actionable checklist including multicast port 1900 hint
- Reframed `.env.example` SONOS_SPEAKER_IPS comment from "optional but recommended" to "optional escape hatch" with "SSDP is used automatically when this is unset"
- All 8 new tests from Plan 04-01 are GREEN (6 in test_sonos_probe.py + 2 in test_skip_client.py)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add probe_sonos_speakers to daemon.py** - `dac6a16` (feat)
2. **Task 2: Update warnings in skip_client.py and .env.example** - `8611584` (feat)

## Files Created/Modified

- `daemon.py` — Added `import soco.discovery`, `probe_sonos_speakers` async function, `await probe_sonos_speakers(soco_skip)` call in `main()`
- `skip_client.py` — Updated `SocoSkipClient.skip()` and `.pause()` warning messages with actionable multicast/env var hints
- `.env.example` — Reframed SONOS_SPEAKER_IPS 5-line comment block to "escape hatch" framing
- `tests/test_sonos_probe.py` — Fixed `test_probe_seeds_ip_cache`: moved `SocoSkipClient()` instantiation inside `patch.dict` context (Rule 1 auto-fix, see Deviations)

## Decisions Made

- Falsy check `if speakers:` used instead of `if speakers is None:` — `soco.discovery.discover` returns either `None` or empty set on failure; both are falsy and both indicate no speakers found
- No `try/except` around `probe_sonos_speakers` in `main()` — probe is informational and non-blocking per D-03; unexpected exceptions at startup should propagate (Docker restart will recover)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test_probe_seeds_ip_cache failing due to .env pre-seeding**
- **Found during:** Task 1 (after implementing probe_sonos_speakers, tests still failing)
- **Issue:** `SocoSkipClient()` was instantiated outside the `with patch.dict(os.environ, ...)` context manager. The real `.env` file contains `SONOS_SPEAKER_IPS=Living Room=192.168.1.164`. `load_dotenv()` runs at module import time in daemon.py, so when the test creates `SocoSkipClient()`, the constructor reads the real env var and pre-seeds `_ip_cache["Living Room"]`. The test then asserts `"Living Room" not in soco_client._ip_cache` — this fails.
- **Fix:** Moved `soco_client = SocoSkipClient()` and the `assert "Living Room" not in soco_client._ip_cache` assertion inside the `with patch.dict` block (after `os.environ.pop("SONOS_SPEAKER_IPS", None)`), so the constructor sees a clean env.
- **Files modified:** `tests/test_sonos_probe.py`
- **Verification:** All 6 probe tests GREEN
- **Committed in:** `dac6a16` (part of Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — bug in test isolation)
**Impact on plan:** Fix was necessary for tests to accurately verify probe behavior. No scope creep — test logic unchanged, only instantiation order corrected.

## Issues Encountered

- Pre-existing test failures (`test_soco_pause_uses_cached_ip`, `test_soco_pause_falls_back_to_discovery_when_not_cached`) remain as documented in `deferred-items.md` from Plan 04-01. These 2 tests are not part of this plan's 8 target tests and were pre-existing before Phase 4 started.

## Known Stubs

None — all implementation is wired. `probe_sonos_speakers` calls real `soco.discovery.discover` via `run_in_executor`; log messages are concrete (not placeholder text).

## Next Phase Readiness

- Phase 5 (README and boot persistence) can reference the multicast requirements documented in warning messages and `.env.example`
- SSDP discovery is now first-class — `SONOS_SPEAKER_IPS` is explicitly documented as fallback only
- Pre-existing test failures in test_skip_client.py (2 pause mock tests) should be resolved in a future plan (tracked in deferred-items.md)

## Self-Check: PASSED

- SUMMARY.md: FOUND
- Commit dac6a16 (Task 1): FOUND
- Commit 8611584 (Task 2): FOUND

---
*Phase: 04-sonos-discovery-hardening*
*Completed: 2026-04-02*
