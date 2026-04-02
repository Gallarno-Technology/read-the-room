---
phase: 02-content-filtering-auto-skip
plan: "06"
subsystem: infra
tags: [makefile, docker, logging, content-filtering]

# Dependency graph
requires:
  - phase: 02-content-filtering-auto-skip
    provides: content_checker.py with instrumental and lyrics_unavailable branches

provides:
  - Makefile setup target handles root-owned directory case via compound -d/-f guard before touch
  - content_checker.py [SCAN] log lines include reason= field for instrumental and lyrics_unavailable short-circuit paths

affects: [02-content-filtering-auto-skip, setup-reliability, observability]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Compound shell guard pattern: -d check before -f check before touch — covers all three lyrics_cache.db states"
    - "reason= field in [SCAN] log lines for all short-circuit branches — makes instrumental and unavailable decisions observable"

key-files:
  created: []
  modified:
    - Makefile
    - content_checker.py

key-decisions:
  - "Two-line guard (-d then -f) before touch: directory case removed first, then lingering regular file, then fresh touch — handles all three initial states"
  - "reason= added only to log format strings, not to return tuples — return values were already correct"

patterns-established:
  - "Makefile setup target: -d guard must precede -f guard when both directory and file cases can exist for the same path"
  - "[SCAN] log lines always include reason= for short-circuit paths to distinguish them from a zero-score full scan"

requirements-completed: [FILT-04, FILT-05]

# Metrics
duration: 5min
completed: 2026-04-01
---

# Phase 02 Plan 06: UAT Gap Closure — Makefile Directory Guard and [SCAN] reason= Fields Summary

**Compound -d/-f guard in Makefile setup prevents Permission denied on root-owned lyrics_cache.db directory; reason=instrumental and reason=lyrics_unavailable added to [SCAN] log lines for observability**

## Performance

- **Duration:** 5 min
- **Started:** 2026-04-01T00:00:00Z
- **Completed:** 2026-04-01T00:05:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Makefile setup target now handles all three lyrics_cache.db states: root-owned directory (sudo rm -rf), regular file (sudo rm -f), and absent (nothing to remove before touch)
- [SCAN] log lines in content_checker.py instrumental branch now emit reason=instrumental so Docker logs clearly identify the code path
- [SCAN] log lines in content_checker.py lyrics_unavailable branch now emit reason=lyrics_unavailable so Docker logs distinguish unavailable-lyrics allows from clean-scan allows

## Task Commits

No git commits — project is not a git repository. Changes applied directly.

1. **Task 1: Fix Makefile setup guard to handle root-owned directory** — Makefile line 7 replaced with two-line compound guard
2. **Task 2: Add reason= field to instrumental and lyrics_unavailable [SCAN] log lines** — content_checker.py lines 78 and 87 updated

## Files Created/Modified

- `/home/cgallarno/Development/spotify-sentiment/Makefile` — Added `[ ! -d lyrics_cache.db ] || sudo rm -rf lyrics_cache.db` before existing -f guard in setup target
- `/home/cgallarno/Development/spotify-sentiment/content_checker.py` — Added `reason=instrumental` to line 78 log.info format string and `reason=lyrics_unavailable` to line 87 log.info format string

## Decisions Made

- Two separate guard lines (-d then -f) rather than a single compound expression: matches existing Makefile style and makes each case's intent explicit
- reason= appended only to the log format string, not the return tuple: return values were already correct and specified by the plan as untouched

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- UAT Test 1 (make setup with root-owned directory) gap is closed
- UAT Test 8 (instrumental track [SCAN] log) gap is closed
- UAT Test for lyrics_unavailable [SCAN] log is also closed
- Phase 02 UAT gap closure complete; ready for phase transition or Signal notification phase

## Self-Check: PASSED

- SUMMARY.md: FOUND
- Makefile -d guard (sudo rm -rf lyrics_cache.db): PRESENT
- content_checker.py reason=instrumental: PRESENT
- content_checker.py reason=lyrics_unavailable: PRESENT

---
*Phase: 02-content-filtering-auto-skip*
*Completed: 2026-04-01*
