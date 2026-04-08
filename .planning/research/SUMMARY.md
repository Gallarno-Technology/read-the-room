# Project Research Summary

**Project:** Read the Room v1.6 — OSS Release Preparation
**Domain:** Open source release infrastructure for a private Python/Docker home automation daemon
**Researched:** 2026-04-06
**Confidence:** HIGH

## Executive Summary

Read the Room is a working, self-hosted Python 3.12 asyncio daemon + FastAPI web UI that monitors Spotify playback and skips explicit content on Sonos speakers. The v1.6 milestone is not a feature milestone — it is a release hygiene milestone. All runtime functionality already ships. The work is: remove personal data from the codebase, create the legal and contributor scaffolding a stranger requires, and add CI infrastructure that signals the project is maintained. Every finding in this research is grounded in direct codebase inspection; all sanitization items cite exact file paths and line numbers.

The recommended approach is strict sequential execution dictated by hard dependencies: hygiene first, then legal and contributor docs, then CI, then GitHub repository configuration at launch. The hygiene phase is a hard gate — publishing a personal home IP, 530 internal planning files with absolute home directory paths, and an absent `.dockerignore` that would expose OAuth credentials in any Docker build creates problems that are difficult to reverse once contributors or forks appear. The documentation and CI phases are independently deliverable once hygiene is clean.

The two critical pre-existing risks that must be resolved before the repo goes public are: (1) no `.dockerignore` exists, meaning `COPY . .` in the Dockerfile would bake `.env` credentials and a live OAuth refresh token into any Docker image built from the project root; and (2) `.planning/` and `.claude/` (530 tracked files with `/home/cgallarno/` absolute paths) are currently tracked by git and will appear on GitHub. All other findings are low-to-moderate risk text substitutions and new file additions with no logic impact.

---

## Key Findings

### Recommended Stack

The project adds no new runtime dependencies in v1.6. All additions are dev/CI tooling: GitHub Actions for CI (free on public repos, zero-infra, native to the platform where the repo lives), `ruff` 0.15.9 as a single replacement for flake8 + black + isort, `pre-commit` 4.5.1 for local hook enforcement, and `pyproject.toml` as the consolidated tool config. No PyPI publish step, no tox, no matrix CI — the project targets Python 3.12 in a fixed Docker environment and these would add noise without benefit.

The exact CI YAML, `pyproject.toml` content, and `.pre-commit-config.yaml` content are fully specified in STACK.md and can be copied directly into implementation without further design work.

**Core technologies:**
- GitHub Actions (`actions/checkout@v4`, `actions/setup-python@v5`, `ubuntu-latest`): Run pytest on push/PR — free for public repos, zero infrastructure, Linux runner matches Docker host environment. `cache: pip` cuts subsequent run time by ~30s.
- `ruff` 0.15.9: Lint and format in one tool (replaces flake8 + black + isort) — written in Rust, runs in milliseconds, Python ecosystem has converged on ruff for new projects in 2025-2026.
- `pre-commit` 4.5.1: Git hook manager — catches lint failures before they reach CI; `pre-commit install` is a one-time setup per clone.
- `pyproject.toml` (tool config only): Consolidates `[tool.pytest.ini_options]` and `[tool.ruff]` — no `[project]` table since the project is not published to PyPI.
- MIT License: Standard permissive license for a personal utility — no patent grant complexity, appropriate for a home automation tool.

### Expected Features

All v1.6 deliverables are OSS release artifacts — documents, automation, and hygiene changes. No new runtime features ship in this milestone.

**Must have before first public link (P1 — hard gates):**
- `.dockerignore` created — currently absent; `COPY . .` in Dockerfile exposes `.env` and `token_cache/` in any Docker build
- `.planning/` and `.claude/` removed from git tracking — 530 files with absolute home directory paths
- LICENSE file (MIT) — without it, the code is legally all-rights-reserved and cannot be legally used or forked
- Old app name sanitized across 9 files — "Spotify Family Safe Mode" in docstrings, `FastAPI(title=)`, and `user_agent=` string
- Personal IP replaced in test file — `192.168.1.164` in 7 locations in `tests/test_sonos_probe.py`
- README rewritten for strangers — lede, hardware prerequisites, "what you need" before Quick Start
- `.gitignore` patched — add `*.db-wal`, `*.db-shm`, `.DS_Store`, `.pytest_cache/`
- `.env.example` additions — `UID`, `GID`, and `EVENTS_PATH` variables currently undocumented

**Should have within one week of public link (P2):**
- CONTRIBUTING.md — dev setup, pytest command, PR expectations, UID/GID pitfall warning, `network_mode: host` access pattern
- GitHub Actions CI — pytest workflow on push/PR with dummy env vars; `ruff check` and `ruff format --check`; `pyproject.toml` and `.pre-commit-config.yaml`
- SECURITY.md — two paragraphs pointing to GitHub private vulnerability reporting

**Defer, add reactively (P3):**
- GitHub issue templates — only useful once external issue volume exists
- PR template — add when first external PR arrives
- Code of Conduct (Contributor Covenant v2.1) — add when first external contributor engages
- GitHub Releases / Changelog — defer to v2.0 boundary

### Architecture Approach

The existing architecture is unchanged by v1.6. The daemon and web UI run as two Docker containers communicating via file-based IPC (`./data/events.jsonl`, `./data/now_playing.json`) with shared bind-mount volumes for OAuth tokens and FSM state. The flat layout (all daemon modules at repo root, `web_ui/` as a separate subdirectory with its own Dockerfile and `requirements.txt`) is appropriate for a single-purpose daemon and requires no restructuring.

The only structural changes are: adding `.github/workflows/`, adding top-level documentation files (LICENSE, CONTRIBUTING.md, SECURITY.md), and removing `.planning/` and `.claude/` from git tracking. The repo should ideally be renamed from `spotify-sentiment` to `read-the-room` but this decision is deferred to the owner (see Gaps).

**Major components (existing, unchanged by v1.6):**
1. `daemon.py` — Asyncio poll loop: fetches Spotify state, evaluates content, triggers skip via SoCo or Spotify API, writes events
2. `web_ui/main.py` — FastAPI app: serves dashboard, REST + SSE endpoints, reads/writes `state.json`
3. `ContentChecker` / scanners — Content evaluation with hot-swappable profile configuration; scanner singletons are long-lived
4. `LyricsService` — LRCLIB fetch with SQLite cache and graceful fallback; `user_agent` string needs rebrand update
5. `SocoSkipClient` / `SpotifySkipClient` — Skip abstractions with Sonos-first, Spotify API fallback on error 701

### Critical Pitfalls

1. **No `.dockerignore` — `.env` and OAuth token baked into Docker image**: `COPY . .` in Dockerfile with no `.dockerignore` copies `.env` (real Spotify credentials) and `token_cache/.cache` (live OAuth refresh token granting `user-modify-playback-state`) into any Docker build. Confirmed absent. Verify fix: `docker run --rm <image> cat /app/.env` must fail.

2. **`.planning/` and `.claude/` tracked in git with absolute home paths**: 530 files containing `/home/cgallarno/` absolute paths are currently tracked. Will appear on GitHub, expose personal machine layout, and confuse contributors. Fix: `git rm -r --cached .planning/ .claude/` and add both to `.gitignore`. Directories remain on disk untracked.

3. **GitHub Actions CI fails without dummy Spotify env vars**: Modules import spotipy at load time; without `SPOTIFY_CLIENT_ID` and related vars set, CI fails with `SpotifyOauthError` before any test runs. The test suite is fully mocked — it just needs fake env vars present. Set them in the workflow `env:` block with clearly fake values (`test-client-id`, etc.).

4. **Personal IP `192.168.1.164` in test fixtures**: The author's actual Sonos IP is hardcoded in `tests/test_sonos_probe.py` in 7 mock assertion values. Replace all with `192.168.1.100` (already the convention in `tests/test_skip_client.py`). Pure text substitution; test behavior is identical.

5. **README written for author, not strangers**: No "what is this" section above Quick Start; UID/GID failure mode not surfaced; Sonos optional status not stated; OAuth redirect "browser fails" note buried in step 5. Requires structured rewrite with a stranger-facing persona.

---

## Implications for Roadmap

The dependency structure is rigid and dictates execution order: hygiene must precede documentation (docs should not reference unsanitized code or non-existent CI), CI must be added before CONTRIBUTING.md references it, and all of this must complete before launch. This structure suggests four sequential phases.

### Phase 1: Repository Hygiene and Sanitization

**Rationale:** Hard gate — no other phase begins before this is clean. Publishing personal data and credential exposure vectors is irreversible once forks appear. This is the highest-risk phase by far; everything else is low-risk file creation.
**Delivers:** A repo that is safe and non-embarrassing to make public: no credential exposure in Docker builds, no internal planning noise, no personal IPs, no stale branding, complete `.gitignore`.
**Addresses:** `.dockerignore` creation, `.planning/` + `.claude/` removal from tracking, personal IP replacement in `tests/test_sonos_probe.py`, app name sanitization across 9 source files, `.gitignore` completion, `.env.example` additions, git history verification (already confirmed clean for `.env` and `token_cache/`).
**Avoids:** Pitfall 1 (`.dockerignore` absent), Pitfall 2 (OAuth token in Docker image), Pitfall 3 (`.planning/` with home directory paths in public git), Pitfall 4 (personal IP in tests).

### Phase 2: License, Contributing Docs, and README

**Rationale:** Legal requirement (LICENSE) and first-impression infrastructure. A stranger who finds the repo needs three things to evaluate it: legal permission to use it, a clear explanation of what it is, and a path to contributing. All three are in this phase.
**Delivers:** MIT LICENSE file; README rewritten for a stranger persona (lede, hardware prerequisites, UID/GID pitfall call-out, `network_mode: host` access explanation); CONTRIBUTING.md (dev setup, pytest, PR expectations); SECURITY.md (private vulnerability reporting).
**Addresses:** P1 features (LICENSE, README rewrite) and P2 features (CONTRIBUTING.md, SECURITY.md).
**Avoids:** Pitfall 6 (README written for author); the `UID`/`GID` first-run failure documented explicitly in CONTRIBUTING.md; `network_mode: host` dashboard access pattern documented clearly.

### Phase 3: CI Infrastructure

**Rationale:** CI must be added after sanitization (clean code should pass lint and tests before CI gates them) and after Phase 2 (CONTRIBUTING.md references the CI workflow by name). CI should be green at the moment the public link goes out so the badge is accurate from day one.
**Delivers:** `.github/workflows/ci.yml` running `ruff check`, `ruff format --check`, and `pytest` on push and PR with dummy Spotify env vars; `pyproject.toml` with `[tool.pytest.ini_options]` and `[tool.ruff]`; `.pre-commit-config.yaml` with ruff hooks; CI and license badges in README.
**Uses:** `ruff` 0.15.9, `pre-commit` 4.5.1, `actions/checkout@v4`, `actions/setup-python@v5`, `ubuntu-latest`.
**Avoids:** Pitfall 5 (CI failing without real Spotify credentials — solved by dummy env vars in workflow `env:` block); Docker-compose-in-CI anti-pattern (use plain `pytest` on the runner instead).

### Phase 4: Launch and GitHub Repository Configuration

**Rationale:** Final non-code steps that occur at or immediately before making the repository public. No code changes; GitHub UI configuration only.
**Delivers:** Public repository with correct topics (`spotify sonos parental-controls home-automation docker python`), description, and visibility. P3 items (issue templates, PR template, Code of Conduct) are explicitly deferred — add reactively when community volume warrants them.
**Addresses:** P2 feature (GitHub repo topics and description).

### Phase Ordering Rationale

- Hygiene before all else because any documentation written before sanitization would reference unsanitized code or embed personal details.
- Documentation before CI because CONTRIBUTING.md must reference the CI workflow by its correct file name, and the README should show a green badge (not a missing badge).
- CI before launch so the status badge reflects real passing tests from the first moment the link is public.
- Issue templates, PR template, and Code of Conduct explicitly post-launch — they provide no value before external contributors exist and add ongoing maintenance overhead if added prematurely.

### Research Flags

All four phases have standard, well-documented patterns. No phases require a `/gsd:research-phase` during planning.

- **Phase 1 (Hygiene):** All findings enumerated in PITFALLS.md and ARCHITECTURE.md with exact file paths, line numbers, and replacement values. Execute directly from research output.
- **Phase 2 (Docs):** README structure and CONTRIBUTING.md content fully specified in FEATURES.md and PITFALLS.md. License is MIT copy-paste. SECURITY.md is two paragraphs.
- **Phase 3 (CI):** Exact CI YAML, `pyproject.toml`, and `.pre-commit-config.yaml` are fully specified in STACK.md with rationale and version pins. Copy from research file.
- **Phase 4 (Launch):** GitHub UI settings; no code changes; no research needed.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All tool versions verified against official package registries and GitHub releases as of 2026-04-06. CI YAML is fully specified and immediately usable without modification. |
| Features | HIGH | Based on direct codebase audit; all sanitization findings cite exact file and line. OSS community standards are well-established and corroborated by multiple official sources. |
| Architecture | HIGH | Based on direct inspection of live codebase, git history inventory (`git ls-files`), and `git log --all` verification. All findings are reproducible with the cited commands. |
| Pitfalls | HIGH | Every pitfall confirmed by direct observation: `.dockerignore` absent, 530 tracked internal files, real IP in test fixtures, `token_cache/.cache` confirmed present at 551 bytes. Not hypothetical. |

**Overall confidence:** HIGH

### Gaps to Address

- **Canonical public repo name**: The research recommends renaming `spotify-sentiment` to `read-the-room` for brand consistency, but the actual public repo name has not been decided. The README rewrite phase must resolve this before the link goes out — specifically the `cd spotify-sentiment` reference in Quick Start that will become `cd <repo-name>`.

- **`.planning/` and `.claude/` local retention**: After `git rm -r --cached .planning/ .claude/`, both directories remain on disk (untracked) and the GSD toolchain continues to function locally. No action required — documenting for clarity so implementers do not delete the directories from disk when removing them from git tracking.

- **Docker image publishing**: The research assumes Docker images are only built locally by each user (never pushed to a public registry). If the project ever adds a pre-built image on Docker Hub or GHCR, the `.dockerignore` guidance in CONTRIBUTING.md must be strengthened with an explicit "never push an image built from a directory containing real credentials" warning.

---

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection: `/home/cgallarno/Development/spotify-sentiment/` — all sanitization findings, git history verification, `.dockerignore` absence, OAuth token file confirmed
- [GitHub Actions: Building and testing Python](https://docs.github.com/actions/guides/building-and-testing-python) — CI workflow structure, `cache: pip` option
- [ruff PyPI](https://pypi.org/project/ruff/) — version 0.15.9 confirmed latest as of 2026-04-02
- [ruff pre-commit integration](https://github.com/astral-sh/ruff-pre-commit) — hook IDs `ruff` and `ruff-format`, ordering rationale
- [ruff configuration docs](https://docs.astral.sh/ruff/configuration/) — `pyproject.toml` `[tool.ruff]` and `[tool.ruff.lint]` table structure
- [pre-commit PyPI](https://pypi.org/project/pre-commit/) — version 4.5.1 confirmed
- [actions/checkout releases](https://github.com/actions/checkout/releases) — v4 confirmed safe stable major; v6 exists with no feature gap for this use case
- [actions/setup-python releases](https://github.com/actions/setup-python) — v5 confirmed widely-adopted stable; v6 requires Node 24 runner
- [GitHub Docs: Adding a workflow status badge](https://docs.github.com/en/actions/monitoring-and-troubleshooting-workflows/adding-a-workflow-status-badge) — native badge URL format
- [GitHub Docs: Adding a security policy](https://docs.github.com/en/code-security/getting-started/adding-a-security-policy-to-your-repository) — SECURITY.md guidance
- [GitHub Docs: Configuring issue templates](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/configuring-issue-templates-for-your-repository) — template format
- [Contributor Covenant](https://www.contributor-covenant.org/) — Code of Conduct v2.1 text

### Secondary (MEDIUM confidence)
- [shields.io static badge docs](https://shields.io/) — MIT license badge URL pattern (static badge, no API dependency)
- [GitHub blog: Coordinated vulnerability disclosure for open source](https://github.blog/security/vulnerability-research/coordinated-vulnerability-disclosure-cvd-open-source-projects/) — SECURITY.md framing
- [GitHub Actions setup for Python projects in 2025](https://ber2.github.io/posts/2025_github_actions_python/) — general CI structure patterns
- [Open source pre-launch checklist](https://medium.com/binbash-inc/open-source-github-repository-pre-launch-checklist-4a52dbbe4af1) — general checklist corroboration

---
*Research completed: 2026-04-06*
*Ready for roadmap: yes*
