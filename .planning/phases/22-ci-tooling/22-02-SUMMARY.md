---
phase: 22-ci-tooling
plan: 02
subsystem: infra
tags: [github-actions, ci, pytest, ruff, yaml]

# Dependency graph
requires:
  - phase: 22-01
    provides: pyproject.toml with [tool.ruff] section and requirements.txt with ruff==0.15.10
provides:
  - .github/workflows/ci.yml — single-job GitHub Actions workflow running pytest + ruff on push/PR to main
affects:
  - 22-03 (README badge plan references ci.yml filename in badge URL)

# Tech tracking
tech-stack:
  added: [github-actions, astral-sh/ruff-action@v3, actions/checkout@v4, actions/setup-python@v5]
  patterns: [job-level env block for dummy credentials, ruff-action version auto-detection from pyproject.toml]

key-files:
  created: [.github/workflows/ci.yml]
  modified: []

key-decisions:
  - "ci.yml filename is exact — README badge in Plan 03 references this filename in badge URL"
  - "Job-level env block (not step-level) ensures all steps including pytest fixture instantiation receive dummy Spotify vars"
  - "astral-sh/ruff-action@v3 with no explicit version — auto-detects ruff==0.15.10 from pyproject.toml [tool.ruff]"

patterns-established:
  - "Pattern: dummy Spotify env vars at job level prevent SpotifyOauthError during pytest fixture setup"

requirements-completed: [CI-01, CI-03]

# Metrics
duration: 1min
completed: 2026-04-11
---

# Phase 22 Plan 02: CI Workflow Summary

**GitHub Actions CI workflow with pytest and ruff lint/format check on every push and pull request to main**

## Performance

- **Duration:** ~1 min
- **Started:** 2026-04-11T12:57:24Z
- **Completed:** 2026-04-11T12:57:52Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Created `.github/workflows/ci.yml` with single job `test` on `ubuntu-latest`
- Workflow triggers on push and pull_request to `main`
- Job-level `env:` block provides 6 dummy Spotify/app vars to prevent SpotifyOauthError at fixture instantiation
- Two `astral-sh/ruff-action@v3` steps: lint check and format check (`args: "format --check"`)

## Task Commits

1. **Task 1: Create .github/workflows/ci.yml** - `4527668` (feat)

**Plan metadata:** (pending docs commit)

## Files Created/Modified
- `.github/workflows/ci.yml` - GitHub Actions CI workflow: pytest + ruff lint + ruff format check

## Decisions Made
- File named `ci.yml` exactly — this filename is referenced by the README badge URL in Plan 03
- `env:` block at job level (not step level) so all steps inherit dummy Spotify credentials
- `astral-sh/ruff-action@v3` with no pinned version — reads `ruff==0.15.10` from pyproject.toml automatically

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `.github/workflows/ci.yml` is ready; Plan 03 can now add README badges referencing `ci.yml`
- CI will go green on first push to GitHub once repository is public (all tests are mocked, no real credentials needed)

---
*Phase: 22-ci-tooling*
*Completed: 2026-04-11*
