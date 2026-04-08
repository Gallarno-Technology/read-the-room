# Stack Research

**Domain:** Open source release infrastructure — CI/tooling additions for a Python/Docker home automation tool (no PyPI publish)
**Researched:** 2026-04-06
**Confidence:** HIGH

---

## Context: What This Milestone Adds (v1.6)

The existing codebase is a working, self-hosted Python 3.12 asyncio daemon + FastAPI web UI deployed via Docker Compose. It already has:

- `pytest` 8.3.5 + `pytest-asyncio` 0.25.3 with 11+ test files under `tests/`
- `requirements.txt` (flat install list, no packaging metadata)
- Docker Compose deployment only — never published to PyPI
- No `.github/` directory, no CI, no license file, no badges

v1.6 adds open source release infrastructure: CI, lint enforcement, license, and documentation polish for strangers cloning and running the project.

---

## Recommended Stack

### Core Technologies — CI/CD

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| GitHub Actions | — | Run tests on push and pull requests | Free for public repos, zero-infra, no external service. Native to GitHub where the repo lives. Ubuntu runners have Docker + Python preinstalled. |
| `actions/checkout` | v4 | Checkout repo in CI workflow | v4 is the current widely-adopted stable major. v6 exists but requires runner v2.327.1+; v4 is safer default for broad compatibility without any feature gap for this use case. |
| `actions/setup-python` | v5 | Install Python 3.12 in CI runner | v5 is the current stable major in wide use. v6 (released Jan 2026) adds Node 24 but breaks older runners; v5 is the safe, supported choice unless runner pinning is explicitly managed. |
| `ubuntu-latest` runner | — | CI execution environment | Fastest cold start for Python projects, matches the Docker host environment (Linux), free on public repos. |

### Core Technologies — Code Quality

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| `ruff` | 0.15.9 | Linter + formatter (replaces flake8, black, isort) | Single tool replaces three. Written in Rust — runs in milliseconds on this codebase (~4K lines). `ruff check` catches real bugs (undefined names, unused imports); `ruff format` enforces consistent style. Configured in `pyproject.toml` alongside pytest. The Python ecosystem has converged on ruff for new projects in 2025-2026. |
| `pre-commit` | 4.5.1 | Run ruff hooks before commit | Catches lint/format failures before they land in CI. Especially useful for contributors unfamiliar with the project. Single `pre-commit install` sets up the hook; no per-dev manual setup required. |

### Core Technologies — Project Metadata

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| `pyproject.toml` | PEP 517/518 standard | Central config for ruff, pytest, and project metadata | Single file replaces `setup.py`, `setup.cfg`, `pytest.ini`, `.flake8`. Does NOT require publishing to PyPI — the `[tool.*]` sections work for any project. Consolidates ruff and pytest config in one place. No `[build-system]` table needed if not publishing. |
| MIT License | — | Open source license file | MIT is the simplest permissive license: no attribution beyond copyright notice, no patent grant complexity. Appropriate for a self-hosted utility with no corporate entanglement. Home Assistant uses Apache-2.0 (adds explicit patent grant); MIT is sufficient for this project. |

---

## Supporting Libraries

No new runtime dependencies. The following are dev-only additions:

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `ruff` | 0.15.9 | Lint and format — dev only | Add to `requirements-dev.txt` (or `pyproject.toml` optional-dependencies). NOT in main `requirements.txt` — not needed at runtime or in Docker container. |
| `pre-commit` | 4.5.1 | Git hook manager — dev only | Install once per dev machine: `pip install pre-commit && pre-commit install`. Never add to `requirements.txt` or Dockerfile. |

---

## Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| GitHub Actions workflow (`.github/workflows/ci.yml`) | Run `pytest` on push and PR to `main` | Single job: checkout → setup Python 3.12 → `pip install -r requirements.txt` → `pip install ruff` → `ruff check .` → `pytest tests/` |
| `.pre-commit-config.yaml` | Ruff hooks run before each commit | Two hooks: `ruff` (lint + autofix) then `ruff-format` (format). Run in that order so lint fixes are formatted. |
| `pyproject.toml` | Central project config | `[tool.pytest.ini_options]` for `testpaths`, `asyncio_mode`; `[tool.ruff]` for `target-version`, `line-length`, `select` rules. |
| `LICENSE` | MIT license text | Standard GitHub license file; enables GitHub's license detection and the license badge. |

---

## CI Workflow: Exact Specification

**File:** `.github/workflows/ci.yml`

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: "pip"

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Install dev tools
        run: pip install ruff==0.15.9

      - name: Lint
        run: ruff check .

      - name: Format check
        run: ruff format --check .

      - name: Test
        run: pytest tests/ -v
```

**Why this structure:**
- `cache: "pip"` on setup-python caches the pip download cache, cutting subsequent run time by ~30s on a project this size.
- `ruff check` and `ruff format --check` are separate steps so failures show clearly (lint vs format) in the Actions UI.
- `pytest tests/ -v` matches the existing `conftest.py` which adds project root to `sys.path`. Running from repo root with explicit `tests/` path is correct.
- No matrix strategy — the project targets Python 3.12 specifically (matches Dockerfile `FROM python:3.12`). Testing multiple Python versions adds CI noise without benefit for a self-hosted tool.

---

## README Badges: Exact Markdown

**CI badge (GitHub native, no shields.io dependency):**

```markdown
![CI](https://github.com/OWNER/REPO/actions/workflows/ci.yml/badge.svg)
```

This uses GitHub's native badge endpoint — no third-party service dependency. The badge auto-updates to pass/fail on each workflow run.

**License badge (shields.io — static, always reliable):**

```markdown
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
```

Shields.io static badges do not hit any external API and do not require the repo to be configured — they render from the URL parameters alone. This is more reliable than a dynamic license badge that reads GitHub's license API.

**Placement:** Both badges go on line 1 of README.md, before the project title, or immediately after the `# Read the Room` heading. One line of badges is the convention for utilities; do not add Python version badge or Docker badge — they add noise without value for a single-stack self-hosted tool.

---

## pyproject.toml: Exact Specification

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"

[tool.ruff]
target-version = "py312"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "W", "I"]
# E/W: pycodestyle errors and warnings
# F: pyflakes (undefined names, unused imports)
# I: isort (import ordering)
# Deliberately NOT selecting: D (pydocstrings), ANN (type annotations), S (bandit security)
# These generate noise on a working codebase without incremental value for v1.6 scope.
```

**Why `asyncio_mode = "auto"`:**
The existing test suite uses `@pytest.mark.asyncio` via `pytest-asyncio`. Mode `auto` eliminates the need to decorate every async test and matches the existing pattern in the codebase.

**Why NOT include `[project]` table:**
This project is not published to PyPI. The `[project]` metadata table (name, version, dependencies) is only needed for packaging. Omitting it keeps `pyproject.toml` to its useful purpose: tool configuration. Adding a `[project]` table without a `[build-system]` table creates a malformed (but not harmful) file that confuses `pip install .` attempts.

---

## pre-commit Config: Exact Specification

**File:** `.pre-commit-config.yaml`

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.15.9
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
```

**Why `ruff` before `ruff-format`:**
`ruff --fix` may change code (e.g., removing unused imports). `ruff-format` then ensures the fixed code is correctly formatted. Order matters.

**Why `--fix` on the lint hook:**
Auto-fixing import order and minor style issues saves developers from a fail → manually fix → re-stage cycle for mechanical issues. Non-auto-fixable errors (e.g., undefined names) still fail the commit and require manual attention.

---

## Installation (Dev Setup)

```bash
# Install dev tools (not needed in Docker/production)
pip install ruff==0.15.9 pre-commit==4.5.1

# Install pre-commit hooks (once per clone)
pre-commit install

# Run pre-commit against all files (initial cleanup)
pre-commit run --all-files

# Run tests locally
pytest tests/ -v
```

---

## Alternatives Considered

| Recommended | Alternative | When Alternative Makes Sense |
|-------------|-------------|------------------------------|
| `ruff` (lint + format) | `flake8` + `black` + `isort` (3 tools) | Legacy projects where black/flake8 are already configured; teams with established per-tool `.ini` configs. For a greenfield open source release, ruff's single-tool DX is clearly better. |
| `actions/setup-python@v5` | `actions/setup-python@v6` | v6 requires runner ≥ v2.327.1 (Node 24 requirement). Use v6 only if explicitly targeting hosted runners known to meet this requirement. v5 is safe default for public repos. |
| `actions/checkout@v4` | `actions/checkout@v6` | v4 is broadly compatible and well-tested. v6 offers minor improvements not relevant to this workflow. Either works; v4 avoids any runner version risk. |
| MIT License | Apache-2.0 | Apache-2.0 adds explicit patent grant — relevant for companies or projects with IP concerns. MIT is sufficient for a personal utility tool. |
| `pyproject.toml` (tool config only) | Separate `pytest.ini` + `ruff.toml` | Separate files are fine but `pyproject.toml` is the modern convention. Tools like ruff explicitly support and prefer `pyproject.toml` in 2026. |
| No matrix CI (Python 3.12 only) | Matrix across 3.11 / 3.12 / 3.13 | Matrix testing is valuable for libraries. For a self-hosted app pinned to a specific Python version in Dockerfile, matrix testing adds noise without coverage value. |

---

## What NOT to Add

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| PyPI publish step in CI | This is a self-hosted Docker tool, not a library. Publishing to PyPI creates a confusing, unsupported package. | No publish step. `docker compose up` is the install path. |
| `setup.py` or `setup.cfg` | Legacy packaging files. If `pyproject.toml` exists for tool config, adding `setup.py` creates confusion about the build system. | `pyproject.toml` with tool sections only; no `[build-system]` table. |
| `codecov` or coverage badges | Adds external service dependency and maintenance overhead. Not warranted for a personal utility reaching open source. | Bare `pytest` pass/fail in CI is sufficient signal. |
| `mypy` or `pyright` in CI | Type checking this codebase introduces annotation debt on ~4K lines of working code that has no type annotations. Adding it as a CI gate blocks contributors immediately. | Defer type annotations to a future milestone if desired. |
| `tox` | Tox is for testing across multiple Python versions and environments. This project targets one Python version in a fixed Docker environment. | Direct `pytest` invocation in CI. |
| `dependabot` auto-PRs for `requirements.txt` | Dependabot PRs for `spotipy`, `soco`, `better-profanity` will require manual API compatibility testing — they are not pure library upgrades. Auto-PRs would create noise without a test infrastructure that validates end-to-end behavior. | Mention manual dependency review in CONTRIBUTING.md. |
| `.editorconfig` | Ruff handles formatting. `.editorconfig` adds a second source of truth for indentation/line endings. | `ruff format` configuration in `pyproject.toml`. |

---

## Version Compatibility

| Package | Version | Notes |
|---------|---------|-------|
| `ruff` | 0.15.9 | Targets `py312`. `ruff format` 0.15.9 implements the 2026 style guide (lambda changes). Pin exact version in CI (`pip install ruff==0.15.9`) to avoid surprise style changes from ruff upgrades. |
| `pre-commit` | 4.5.1 | Uses `ruff-pre-commit` rev `v0.15.9` — must match the CI version to avoid lint passing locally but failing in CI. |
| `pytest` | 8.3.5 | Already in `requirements.txt`. CI installs from `requirements.txt` — no version conflict. |
| `pytest-asyncio` | 0.25.3 | Already in `requirements.txt`. `asyncio_mode = "auto"` in `pyproject.toml` is compatible with 0.25.x. |
| `actions/checkout` | v4 | Stable, no known compatibility issues with `ubuntu-latest`. |
| `actions/setup-python` | v5 | Compatible with `ubuntu-latest`. v6 requires runner ≥ v2.327.1 (Node 24) — avoid until GitHub confirms default hosted runners meet this. |

---

## Sources

- [GitHub Actions: Building and testing Python (official docs)](https://docs.github.com/actions/guides/building-and-testing-python) — workflow structure, `cache: pip` option (HIGH confidence, official)
- [actions/checkout releases](https://github.com/actions/checkout/releases) — confirmed v4 as current safe stable major; v6.0.2 exists (HIGH confidence, official)
- [actions/setup-python releases](https://github.com/actions/setup-python) — confirmed v5 as widely-adopted stable; v6.2.0 has Node 24 runner requirement (HIGH confidence, official)
- [GitHub Docs: Adding a workflow status badge](https://docs.github.com/en/actions/monitoring-and-troubleshooting-workflows/adding-a-workflow-status-badge) — exact badge URL format (HIGH confidence, official)
- [ruff PyPI](https://pypi.org/project/ruff/) — confirmed 0.15.9 latest as of 2026-04-02 (HIGH confidence, official)
- [ruff pre-commit integration](https://github.com/astral-sh/ruff-pre-commit) — hook IDs `ruff` and `ruff-format`, ordering recommendation (HIGH confidence, official)
- [pre-commit PyPI](https://pypi.org/project/pre-commit/) — confirmed 4.5.1 latest (HIGH confidence, official)
- [ruff configuration docs](https://docs.astral.sh/ruff/configuration/) — `pyproject.toml` `[tool.ruff]` and `[tool.ruff.lint]` tables (HIGH confidence, official)
- [shields.io static badge docs](https://shields.io/) — MIT license badge URL pattern (MEDIUM confidence, well-known service)

---

*Stack research for: Read the Room v1.6 — open source release CI/tooling infrastructure*
*Researched: 2026-04-06*
