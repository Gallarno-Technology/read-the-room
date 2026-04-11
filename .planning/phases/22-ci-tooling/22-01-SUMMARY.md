---
phase: 22-ci-tooling
plan: 01
subsystem: infra
tags: [ruff, pytest, pyproject-toml, ci, tooling]

# Dependency graph
requires: []
provides:
  - pyproject.toml with [tool.pytest.ini_options] asyncio_mode=auto
  - pyproject.toml with [tool.ruff] lint/format configuration for py312
  - ruff==0.15.10 pinned in requirements.txt for CI pip install
affects:
  - 22-ci-tooling plan 02 (GitHub Actions workflow reads pyproject.toml and installs ruff via requirements.txt)

# Tech tracking
tech-stack:
  added: [ruff==0.15.10]
  patterns:
    - pyproject.toml as single dev-tooling config file (no setup.cfg, no pytest.ini, no [build-system])
    - ruff pinned in requirements.txt so CI installs it with one pip install step

key-files:
  created:
    - pyproject.toml
  modified:
    - requirements.txt

key-decisions:
  - "No [build-system] in pyproject.toml — project is not a PyPI package; file is purely dev-tool config"
  - "asyncio_mode = auto set explicitly to prevent pytest-asyncio 1.0 strict default breaking async tests"

patterns-established:
  - "Pattern: pyproject.toml tool-sections-only without [build-system] for non-package projects"

requirements-completed: [CI-02, CI-03]

# Metrics
duration: 1min
completed: 2026-04-11
---

# Phase 22 Plan 01: CI Tooling Foundations Summary

**pyproject.toml created with pytest asyncio_mode=auto and ruff py312 lint/format config; ruff==0.15.10 pinned in requirements.txt**

## Performance

- **Duration:** ~1 min
- **Started:** 2026-04-11T12:55:12Z
- **Completed:** 2026-04-11T12:55:52Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Created pyproject.toml at repository root with four [tool.*] sections and no [build-system] table
- Set asyncio_mode = "auto" in [tool.pytest.ini_options] — future-proofs against pytest-asyncio 1.0 strict default change
- Configured ruff with target-version py312, line-length 88, E4/E7/E9/F/I lint rules, and double-quote/space-indent format rules
- Appended ruff==0.15.10 to requirements.txt — CI installs it via single pip install -r requirements.txt step

## Task Commits

Each task was committed atomically:

1. **Task 1: Create pyproject.toml** - `f0f917f` (chore)
2. **Task 2: Add ruff to requirements.txt** - `811112e` (chore)

## Files Created/Modified

- `/home/cgallarno/Development/spotify-sentiment/pyproject.toml` - Pytest asyncio_mode + ruff lint/format config; no [build-system]
- `/home/cgallarno/Development/spotify-sentiment/requirements.txt` - ruff==0.15.10 appended as 9th line

## Decisions Made

- No [build-system] section in pyproject.toml: project is not a PyPI package; adding [build-system] would cause unintended pip install behavior downstream
- asyncio_mode = "auto" chosen over omitting the setting: pytest-asyncio 1.0 changes default to strict which would silently affect async fixture behavior; explicit "auto" is forward-compatible with all existing @pytest.mark.asyncio tests

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- pyproject.toml provides ruff version target and pytest config for Plan 02 (GitHub Actions CI workflow)
- requirements.txt installs ruff via pip install -r requirements.txt — no extra install step needed in workflow YAML
- Plan 02 can reference pyproject.toml [tool.ruff] for ruff-action version auto-detection

---
*Phase: 22-ci-tooling*
*Completed: 2026-04-11*
