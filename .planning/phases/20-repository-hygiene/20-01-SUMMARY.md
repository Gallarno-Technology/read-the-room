---
phase: 20-repository-hygiene
plan: 01
subsystem: infra
tags: [docker, git, gitignore, dockerignore, security]

# Dependency graph
requires: []
provides:
  - .dockerignore at repo root excluding .env, token_cache/, .claude/, tests/, .planning/
  - .claude/ removed from git index (217 files untracked, files preserved on disk)
  - .gitignore extended with .claude/ and .planning/ sections
affects: [all future phases — clean git state, any Docker build step]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - ".dockerignore mirrors .gitignore secret exclusions to prevent image layer leakage"
    - "git rm --cached -r run AFTER .gitignore edit to prevent re-tracking window"

key-files:
  created:
    - .dockerignore
  modified:
    - .gitignore

key-decisions:
  - "Edit .gitignore before running git rm --cached -r to close re-tracking window"
  - ".venv/ excluded from .dockerignore per D-07 (standard Python convention, may not exist in CI)"

patterns-established:
  - ".dockerignore comment style mirrors .gitignore: '# Category — reason' above entries"

requirements-completed: [HYG-01, HYG-02]

# Metrics
duration: 3min
completed: 2026-04-08
---

# Phase 20 Plan 01: Repository Hygiene — Docker and Git Tracking Summary

**.dockerignore created to block secrets from image layers and .claude/ (217 files) removed from git index before public release**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-04-08T22:18:00Z
- **Completed:** 2026-04-08T22:21:23Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Created `.dockerignore` at repository root covering all secret and runtime exclusions required by D-07 — `.env`, `token_cache/`, `state.json`, `data/`, `lyrics_cache.db`, `__pycache__/`, `*.pyc`, `.git/`, `.claude/`, `.planning/`, `tests/`
- Extended `.gitignore` with `.claude/` and `.planning/` entries under a new `Dev tooling` section with matching comment style
- Ran `git rm --cached -r .claude/` to remove 217 tracked files from the git index without deleting them from disk — closes the absolute home path credential exposure vector

## Task Commits

Each task was committed atomically:

1. **Task 1: Create .dockerignore** - `088294f` (chore)
2. **Task 2: Untrack .claude/ from git** - `78860de` (chore)

**Plan metadata:** committed with final docs commit

## Files Created/Modified

- `.dockerignore` - Docker build context exclusions; prevents .env and token_cache/ from being baked into image layers; covers both daemon and web_ui services (both use context: .)
- `.gitignore` - Extended with `.claude/` and `.planning/` entries under "Dev tooling" section

## Decisions Made

- Ordered .gitignore edit before `git rm --cached -r` to prevent a window where files are untracked but not gitignored (per RESEARCH.md Pitfall 3)
- Did not add `.venv/` to .dockerignore per D-07 guidance — it is excluded by standard Python conventions and may not exist in CI

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Both credential exposure vectors closed: Docker cannot bake secrets into layers, and .claude/ absolute home paths are no longer tracked
- `.planning/` still tracked (319 files) — plan only required .claude/ untracking; .planning/ untracking is separate scope if needed
- Repository safe to proceed with remaining v1.6 phases (LICENSE, README, CI)

## Self-Check: PASSED

- .dockerignore: FOUND
- 20-01-SUMMARY.md: FOUND
- Commit 088294f: FOUND
- Commit 78860de: FOUND

---
*Phase: 20-repository-hygiene*
*Completed: 2026-04-08*
