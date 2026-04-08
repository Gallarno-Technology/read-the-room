# Feature Research

**Domain:** Open source release preparation for a self-hosted Python home automation tool
**Researched:** 2026-04-06
**Confidence:** HIGH (based on direct codebase audit + verified OSS community standards)

---

## Framing: What "Feature" Means Here

This is not a greenfield product. All runtime functionality already ships. The "features" being researched are the OSS release artifacts — documents, automation, and hygiene changes — that let a stranger successfully clone, understand, run, and contribute to this project.

The downstream consumer is: someone who finds a link to this repo, has Docker installed, owns a Sonos + Spotify setup, and wants to run it.

---

## Feature Landscape

### Table Stakes (Day-1 Blockers — Without These, You Cannot Share the Link)

Features a stranger requires before they can even evaluate the project. Missing any of these makes the repo non-viable for public sharing.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| LICENSE file | Without a license, the code is legally all-rights-reserved by default. Strangers cannot legally fork, use, or modify it. | LOW | MIT is standard for home automation tools. Single file, no code changes. |
| README rewritten for strangers | Current README is correct but author-centric: no "what is this" lede, opens immediately with `git clone`, uses `cd spotify-sentiment` (internal dir name), references no hardware requirements for a first-time visitor. A public user needs: what it does, what hardware is required, what accounts are needed. | MEDIUM | Existing Quick Start steps are solid — needs a lede section and hardware prerequisites block. Phased content revision, not rewrite from zero. |
| Old app name sanitized in source files | Six Python source files carry docstring headers referencing "Spotify Family Safe Mode" (the pre-rebrand name). `web_ui/main.py` sets `FastAPI(title="Spotify Family Safe Mode")`. `lyrics_service.py` sends `user_agent="SpotifyFamilySafe/1.0"` to the LRCLIB API. `README.md` still has `cd spotify-sentiment`. | LOW | Find-and-replace across 8 files. No logic changes. Low risk. |
| Personal IP replaced in test file | `tests/test_sonos_probe.py` hardcodes `192.168.1.164` — the author's actual Living Room Sonos IP — in 7 mock assertions. While harmless (it is mocked), it is a real home LAN address in a public repo. | LOW | 7 occurrences in one file. Replace with RFC 5737 documentation range (`192.0.2.1`) or a clearly fictional value (`192.168.0.10`). Purely cosmetic — no logic change. |
| Confirm `.env` and runtime files not in git history | `.env` (contains real `SPOTIFY_CLIENT_ID` and `SONOS_SPEAKER_IPS=Living Room=192.168.1.164`) is gitignored. `state.json` (contains real Spotify track ID and FSM state) is gitignored. `data/events.jsonl` (real listen history with track names and album art URLs) is gitignored. All confirmed not present in git history via `git log -S`. | LOW | **Already clean — verification only, no action required.** The gitignore is working. Confirm before first push. |
| `.gitignore` completeness audit | Current `.gitignore` covers `.env`, `state.json`, `token_cache/`, `data/`, `lyrics_cache.db`, `__pycache__/`, `.venv/`. Missing: `*.db-wal` and `*.db-shm` (SQLite WAL journal files that appear when the DB is open), `.DS_Store` (macOS), `.pytest_cache/` (pytest run cache). | LOW | Three-line addition. Prevents accidental staging of runtime artifacts on macOS hosts. |

### Should-Have (Add Before or Shortly After First Public Link)

Features that do not block the link going out, but which any informed public user will notice missing within the first day.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| CONTRIBUTING.md | The first question a contributor asks is "how do I submit a PR?" GitHub automatically surfaces CONTRIBUTING.md in new issue and PR creation flows when it exists. Without it, contributors either send random PRs or give up. | LOW | For a small project: one page covering clone+venv setup, how to run pytest, PR expectations, issue etiquette. No fancy tooling. |
| GitHub Actions CI (pytest) | A public repo without CI signals "tests may or may not pass on your machine." The pytest suite is already comprehensive (12 test files, all mocked). A push-triggered workflow that installs deps and runs `pytest` is ~20 lines of YAML. No docker-compose complexity needed. | LOW | Tests mock all external dependencies. `ubuntu-latest` + `python 3.12` + `pip install -r requirements.txt` + `pytest` is sufficient. Docker-compose in CI would add 2+ minutes of startup time with no benefit. |
| SECURITY.md | GitHub surfaces a security policy in the "Security" tab. For a tool that stores Spotify OAuth tokens on a home server, a brief "please use GitHub private vulnerability reporting" file sets appropriate expectations. Not a day-1 blocker, but expected within the first week. | LOW | Two paragraphs. GitHub has built-in private vulnerability reporting that makes the implementation trivial. |

### Nice-to-Have (Post-Launch Polish)

Features experienced OSS contributors expect but new users never notice. Add reactively when the community warrants it.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| GitHub issue templates | Pre-populate bug reports with "Steps to reproduce / Expected / Actual / Docker version / Platform" fields. Reduces back-and-forth on low-quality issues. Only useful once external issue volume exists. | LOW | YAML frontmatter + markdown in `.github/ISSUE_TEMPLATE/`. One bug-report template and one feature-request template covers all cases. Add when external issues start arriving. |
| PR template | Prompts contributors to describe what changed and link to an issue. Reduces review back-and-forth. | LOW | Single `.github/pull_request_template.md`. Add when first external PR arrives. |
| Code of Conduct | Contributor Covenant is the de-facto standard (adopted by 40,000+ projects including Home Assistant). GitHub's "Community Standards" checklist flags its absence. For a solo-maintainer project with no community yet, it is low urgency. | LOW | Copy-paste Contributor Covenant v2.1. Fully boilerplate. Add when first external contributor engages. |
| Repository topics and description (GitHub UI) | Search discoverability. Topics like "spotify sonos parental-controls home-automation docker python" help the right users find it. | LOW | GitHub UI setting, not a file. Add at launch. Zero code change. |
| Changelog (CHANGELOG.md or GitHub Releases) | Lets users know what changed across versions. Not useful day-1 for a project with no prior public version history. Expected by the time v2.0 ships. | LOW–MEDIUM | GitHub Releases UI is simpler than a hand-maintained CHANGELOG.md for small projects. |

### Anti-Features (Commonly Requested, Often Problematic)

| Anti-Feature | Why Requested | Why Problematic | Alternative |
|--------------|---------------|-----------------|-------------|
| Full developer wiki or docs site | Seems professional. | Creates maintenance burden. Becomes stale faster than code. | README + CONTRIBUTING.md covers all real cases at this project size. |
| Automated secret scanning in CI (gitleaks, git-secrets) | Seems security-conscious. | Overkill for a solo project where secrets are already gitignored and never committed. CI gate adds friction with no incremental safety. | Verify `.gitignore` is complete (it is). Done. |
| Docker-compose in GitHub Actions CI | "Tests should match production environment." | The pytest suite mocks all external deps — Spotify API, SoCo, LRCLIB, file system. There is no integration test that needs Docker running. Docker-compose in CI adds 2+ minutes of startup time and significant workflow complexity for zero benefit. | Run `pytest` directly on the CI runner with `pip install`. |
| Badges overload in README | Some projects display 8+ status badges. | Visual noise. No download counts, no coverage service configured, no version badge to show. | One CI status badge (GitHub Actions) once the workflow is stable. That is sufficient. |
| All-contributors bot | Credits every contributor automatically. | Total overhead for a tool likely to have 0–3 external contributors ever. The bot requires PR reviews and config maintenance. | Acknowledge contributors in release notes if and when they appear. |
| Separate documentation site (MkDocs, Sphinx) | Large projects use them. | For a tool this size, a well-structured README plus PROXMOX.md is all anyone will read. | Keep docs in the repo as Markdown files. |

---

## Feature Dependencies

```
LICENSE
    └──required-before──> any public link

README (stranger-facing rewrite)
    └──enhanced-by──> CONTRIBUTING.md (sets contributor expectations)
    └──enhanced-by──> GitHub Actions CI badge (signals test status to first visitors)

Source sanitization (old app name in 8 files, personal IP in test file)
    └──required-before──> any public link

.gitignore completeness
    └──required-before──> any public link (blocks accidental future staging)

.env / state.json / data/ audit
    └──required-before──> any public link (one-time verification, already clean)

GitHub Actions CI
    └──required-before──> CONTRIBUTING.md references it
    └──depends-on──> requirements.txt (already exists and correct)

SECURITY.md
    └──independent──> add any time after launch

Issue templates / PR template / Code of Conduct
    └──depends-on──> having external contributors (add reactively, not proactively)
```

### Dependency Notes

- **LICENSE before public link.** No license means legally unusable. This is a hard gate, not a recommendation.
- **Source sanitization before public link.** Publishing with the author's home IP and a stale app name in version-controlled files is fixable-but-embarrassing. Worth doing before the link goes out, not after.
- **CI before CONTRIBUTING.md.** CONTRIBUTING.md should tell contributors how to run tests and what CI checks. Write the workflow first, then reference it.
- **Issue templates after community forms.** GitHub's community health checklist penalizes absence, but empty-template forms that nobody fills out add no value. Add reactively when volume warrants it.

---

## MVP Definition

### Launch With (Day-1, Blocks Public Link)

- [ ] LICENSE file (MIT) — legal requirement for any usable open source release
- [ ] README rewritten with stranger-facing lede, hardware requirements, and "what you need" block before Quick Start
- [ ] Old app name sanitized: update docstrings in `daemon.py`, `web_ui/main.py`, `skip_client.py`, `drug_scanner.py`, `sexual_content_scanner.py`, `content_checker.py`, `lyrics_service.py`; update `FastAPI(title=)` in `web_ui/main.py`; update `user_agent=` in `lyrics_service.py`; fix `cd spotify-sentiment` in `README.md`
- [ ] Personal IP (`192.168.1.164`) replaced with `192.0.2.1` in `tests/test_sonos_probe.py` (7 occurrences)
- [ ] `.gitignore` patched: add `*.db-wal`, `*.db-shm`, `.DS_Store`, `.pytest_cache/`
- [ ] Confirm `.env`, `state.json`, `data/`, `token_cache/` are not tracked in git history (already confirmed clean — document the verification)

### Add Before or Shortly After Public Link (Strong Should-Have)

- [ ] CONTRIBUTING.md — one page: dev setup, `pytest` command, PR expectations, issue etiquette
- [ ] GitHub Actions CI — simple pytest workflow (~20 lines), triggers on push and PR to main
- [ ] SECURITY.md — two paragraphs pointing to GitHub private vulnerability reporting

### Future Consideration (Post-Launch, Reactive)

- [ ] GitHub issue templates (bug report + feature request) — add when external issues arrive
- [ ] PR template — add when first external PR arrives
- [ ] Code of Conduct (Contributor Covenant v2.1) — add when first external contributor engages
- [ ] Repository topics and description in GitHub UI — add at launch (not a file, zero effort)
- [ ] GitHub Releases / Changelog — add at v2.0 boundary

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| LICENSE file | HIGH (legal gate) | LOW (copy-paste MIT) | P1 |
| README for strangers | HIGH (first impression, trust signal) | MEDIUM (rewrite lede + prerequisites) | P1 |
| Old app name sanitization (8 files) | MEDIUM (professionalism, rebrand completion) | LOW (find-replace, no logic) | P1 |
| Personal IP in tests replaced | MEDIUM (privacy hygiene) | LOW (7 lines, one file) | P1 |
| `.gitignore` completeness | HIGH (prevents future secret staging) | LOW (3-line addition) | P1 |
| Git history audit (verification) | HIGH (confirm no secrets ever committed) | LOW (one-time `git log -S` check) | P1 |
| CONTRIBUTING.md | HIGH (contributor onboarding) | LOW (~1 page) | P2 |
| GitHub Actions CI (pytest) | HIGH (trust signal, catches regressions) | LOW (~20-line YAML) | P2 |
| SECURITY.md | MEDIUM (community health score) | LOW (2 paragraphs) | P2 |
| GitHub repo topics + description | MEDIUM (discoverability) | LOW (UI setting) | P2 |
| GitHub issue templates | LOW (only useful with external volume) | LOW | P3 |
| PR template | LOW (only useful with contributors) | LOW | P3 |
| Code of Conduct | LOW (no community yet) | LOW (copy-paste) | P3 |
| Changelog / GitHub Releases | LOW (no public version history yet) | LOW–MEDIUM | P3 |

**Priority key:**
- P1: Must have before first public link
- P2: Should have, add within a week of going public
- P3: Nice to have, add reactively when community warrants

---

## Specific Sanitization Findings (Direct Codebase Audit)

These are concrete items discovered by inspecting version-controlled files. All require changes before the link goes out.

### Files Requiring Changes Before Public Link

| File | Issue | What to Change |
|------|-------|---------------|
| `lyrics_service.py:73` | `user_agent="SpotifyFamilySafe/1.0"` | Change to `ReadTheRoom/1.0` |
| `web_ui/main.py:1` | Docstring: "Spotify Family Safe Mode — Web UI Service" | Update to "Read the Room — Web UI Service" |
| `web_ui/main.py:47` | `FastAPI(title="Spotify Family Safe Mode")` | Change to `FastAPI(title="Read the Room")` |
| `skip_client.py:2` | Docstring: "Spotify Family Safe Mode (Phase 2)" | Update to "Read the Room" |
| `drug_scanner.py:2` | Docstring: "Drug reference scanner for Spotify Family Safe Mode" | Update to "Read the Room" |
| `daemon.py:2` | Docstring: "Spotify Family Safe Mode — Core Daemon (Phase 1)" | Update to "Read the Room — Core Daemon" |
| `content_checker.py:2` | Docstring: "Content filtering orchestrator for Spotify Family Safe Mode" | Update to "Read the Room" |
| `sexual_content_scanner.py:2` | Docstring: "Sexual content scanner for Spotify Family Safe Mode" | Update to "Read the Room" |
| `README.md:11` | `cd spotify-sentiment` | Change to match actual public repo name (e.g., `cd read-the-room`) |
| `tests/test_sonos_probe.py:47,58,70,82,83,99,113` | `192.168.1.164` — author's real LAN IP in 7 mock assertions | Replace all 7 occurrences with `192.0.2.1` (RFC 5737 documentation range) |

### Files Confirmed Clean (No Action Required)

| File | Status | Why Clean |
|------|--------|-----------|
| `.env` | Gitignored, never committed | Contains real Client ID and personal Sonos IP. Confirmed absent from all git commits via `git log -S "886bfa"` — returned no results. |
| `state.json` | Gitignored, never committed | Contains real Spotify track ID and FSM state. Not in git history. |
| `data/events.jsonl` | Gitignored, never committed | Contains real listen history (track names, artist names, album art URLs). Not tracked. |
| `data/now_playing.json` | Gitignored, never committed | Contains `{"status": "idle"}` — harmless in any case. Not tracked. |
| `token_cache/` | Gitignored, never committed | OAuth tokens. Not tracked. |
| `.env.example` | Tracked, already clean | Uses `your_client_id_here` and example IPs (`192.168.1.50`, `192.168.1.51`). No personal data. |
| `PROXMOX.md` | Tracked, clean | Uses generic example IPs in documentation. Appropriate for a stranger audience. |

### `.gitignore` Gaps to Patch

Current `.gitignore` covers the critical items but is missing:
```
*.db-wal
*.db-shm
.DS_Store
.pytest_cache/
*.egg-info/
```

---

## README Structure Recommendation (For Strangers)

The current README opens with `git clone` before explaining what the tool does. A stranger landing via a link needs this ordering:

1. **What it is** — 2–3 sentences in plain English. "A background service that monitors Spotify playback and automatically skips explicit or profane songs when Read the Room is enabled. Works with Sonos speakers and non-Sonos Spotify Connect devices."
2. **What you need** — Hardware (Sonos optional but primary use case), accounts (Spotify Premium required for playback control), software (Docker + docker compose v2).
3. **Quick Start** — The existing 7-step flow is correct. Keep it. Fix `cd spotify-sentiment`.
4. **Configuration** — `.env` fields explained (already in `.env.example` comments — can link there).
5. **Dashboard** — A screenshot or brief description of what the browser UI shows.
6. **Proxmox/LXC note** — Already in PROXMOX.md with a callout in README. Keep it.
7. **Updating** — Already correct.

What to remove from current README: internal references to phase numbers ("Phase 2", "D-05") if any appear, the `cd spotify-sentiment` hardcoded directory name, any assumption that the reader already knows what FSM means.

---

## CONTRIBUTING.md Structure Recommendation

For a small solo project with occasional external contributors, one page is the right scope:

1. **Reporting bugs** — Open a GitHub issue. Include: Docker version, host OS, daemon container logs (`docker compose logs daemon`), what you expected vs what happened.
2. **Requesting features** — Open a GitHub issue before writing code. Describe the use case, not just the feature.
3. **Development setup** — `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
4. **Running tests** — `pytest tests/` — note that all external services (Spotify API, SoCo, LRCLIB) are mocked. No real accounts or hardware needed.
5. **Submitting PRs** — One feature or fix per PR. Tests required for new logic. Keep CI green. Reference the issue number.
6. **Code style** — The codebase uses no linter configuration currently. Note this honestly. A future milestone can add `ruff` or `black` if the project attracts contributors.

---

## Sources

- Direct codebase audit: `/home/cgallarno/Development/spotify-sentiment/` — HIGH confidence. All sanitization findings are from direct file inspection, not inference.
- [GitHub Docs: Configuring issue templates](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/configuring-issue-templates-for-your-repository) — HIGH confidence
- [Open Source Guides: Code of Conduct](https://opensource.guide/code-of-conduct/) — HIGH confidence
- [GitHub Docs: Removing sensitive data from a repository](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository) — HIGH confidence
- [Contributor Covenant](https://www.contributor-covenant.org/) — HIGH confidence (40,000+ projects, including Home Assistant)
- [GitHub blog: Coordinated vulnerability disclosure for open source](https://github.blog/security/vulnerability-research/coordinated-vulnerability-disclosure-cvd-open-source-projects/) — MEDIUM confidence
- [GitHub Actions setup for Python projects in 2025](https://ber2.github.io/posts/2025_github_actions_python/) — MEDIUM confidence
- [Open source pre-launch checklist (binbash)](https://medium.com/binbash-inc/open-source-github-repository-pre-launch-checklist-4a52dbbe4af1) — MEDIUM confidence (general checklist, no home automation specificity)
- [GitHub Docs: Adding a security policy](https://docs.github.com/en/code-security/getting-started/adding-a-security-policy-to-your-repository) — HIGH confidence

---
*Feature research for: OSS release preparation (Read the Room v1.6)*
*Researched: 2026-04-06*
