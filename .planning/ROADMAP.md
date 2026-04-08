# Roadmap: Read the Room

## Milestones

- ✅ **v1.0 MVP** — Phases 1-3 (shipped 2026-04-02)
- ✅ **v1.1 Deployment** — Phases 4-5 (shipped 2026-04-02)
- ✅ **v1.2 Now Playing Status** — Phases 6-8.1 (shipped 2026-04-03)
- ✅ **v1.3 Drug & Sexual Reference Detection** — Phases 9-13 (shipped 2026-04-04)
- ✅ **v1.4 Dashboard Polish & Filter Profiles** — Phases 14-16 (shipped 2026-04-05)
- ✅ **v1.5 Dashboard Polish & Mobile UX** — Phases 17-19 (shipped 2026-04-06)
- 🚧 **v1.6 Open Source** — Phases 20-22 (in progress)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1-3) — SHIPPED 2026-04-02</summary>

- [x] Phase 1: Foundation (2/2 plans) — completed 2026-04-02
- [x] Phase 2: Content Filtering (7/7 plans) — completed 2026-04-02
- [x] Phase 3: Dashboard & Skip Feed (5/5 plans) — completed 2026-04-02

</details>

<details>
<summary>✅ v1.1 Deployment (Phases 4-5) — SHIPPED 2026-04-02</summary>

- [x] Phase 4: Sonos Discovery (2/2 plans) — completed 2026-04-02
- [x] Phase 5: README & Ops (2/2 plans) — completed 2026-04-02

</details>

<details>
<summary>✅ v1.2 Now Playing Status (Phases 6-8.1) — SHIPPED 2026-04-03</summary>

- [x] Phase 6: Now Playing API (4/4 plans) — completed 2026-04-03
- [x] Phase 7: Manual Skip (2/2 plans) — completed 2026-04-03
- [x] Phase 8: Severity Badges (1/1 plan) — completed 2026-04-03
- [x] Phase 8.1: Allow-Reason Context — INSERTED (2/2 plans) — completed 2026-04-03

</details>

<details>
<summary>✅ v1.3 Drug & Sexual Reference Detection (Phases 9-13) — SHIPPED 2026-04-04</summary>

- [x] Phase 9: TrackEvalResult Refactor (3/3 plans) — completed 2026-04-04
- [x] Phase 10: Drug & Sexual Scanners (2/2 plans) — completed 2026-04-04
- [x] Phase 11: ContentChecker Pipeline Integration (2/2 plans) — completed 2026-04-04
- [x] Phase 12: Event Propagation & Incident Log (2/2 plans) — completed 2026-04-04
- [x] Phase 13: Dashboard Badge Variants (1/1 plan) — completed 2026-04-04

</details>

<details>
<summary>✅ v1.4 Dashboard Polish & Filter Profiles (Phases 14-16) — SHIPPED 2026-04-05</summary>

- [x] Phase 14: Idle Detection (2/2 plans) — completed 2026-04-04
- [x] Phase 15: Skip History (2/2 plans) — completed 2026-04-04
- [x] Phase 16: Filter Profiles (3/3 plans) — completed 2026-04-05

</details>

<details>
<summary>✅ v1.5 Dashboard Polish & Mobile UX (Phases 17-19) — SHIPPED 2026-04-06</summary>

- [x] Phase 17: Rebrand (1/1 plan) — completed 2026-04-06
- [x] Phase 18: Profile Info Icon (1/1 plan) — completed 2026-04-06
- [x] Phase 19: Mobile Polish (1/1 plan) — completed 2026-04-06

</details>

### 🚧 v1.6 Open Source (In Progress)

**Milestone Goal:** Prepare the repository for public release so strangers can clone, understand, and run Read the Room.

- [ ] **Phase 20: Repository Hygiene** — Remove personal data, fix credential exposure, sanitize branding and IPs
- [ ] **Phase 21: Legal & Docs** — Add LICENSE, rewrite README for strangers, create CONTRIBUTING.md
- [ ] **Phase 22: CI & Tooling** — GitHub Actions CI, pyproject.toml, ruff lint/format, README badges

## Phase Details

### Phase 17: Rebrand
**Goal**: The app presents itself as "Read the Room" everywhere a user sees its name
**Depends on**: Phase 16
**Requirements**: RBR-01, RBR-02
**Success Criteria** (what must be TRUE):
  1. Browser tab shows "Read the Room" as the page title
  2. Dashboard heading displays "Read the Room" (not "Spotify Family Safe Mode")
  3. README.md header and opening paragraph reference "Read the Room"
**Plans**: 1 plan
Plans:
- [x] 17-01-PLAN.md — Rename all user-visible display strings to "Read the Room" in index.html and README.md
**UI hint**: yes

### Phase 18: Profile Info Icon
**Goal**: Parents can see exactly what content each filter profile blocks without leaving the dashboard
**Depends on**: Phase 17
**Requirements**: INFO-01, INFO-02
**Success Criteria** (what must be TRUE):
  1. An info icon (ⓘ) is visible on the FSM control card at all times, regardless of FSM state
  2. Tapping or clicking the icon reveals a readable breakdown of what the active profile skips (profanity level, drug refs, sexual content, explicit flag)
  3. The breakdown updates when the active profile changes
**Plans**: 1 plan
Plans:
- [x] 18-01-PLAN.md — Add ⓘ info button to FSM card with responsive desktop popover and mobile bottom-sheet reveal
**UI hint**: yes

### Phase 19: Mobile Polish
**Goal**: The dashboard behaves predictably on mobile — no accidental zoom or text selection on UI chrome
**Depends on**: Phase 18
**Requirements**: MOB-01, MOB-02
**Success Criteria** (what must be TRUE):
  1. Pinch-zoom and double-tap zoom are disabled on the dashboard viewport on mobile
  2. Buttons, badges, labels, and profile options cannot be accidentally selected as text
  3. Track title and artist text remain selectable (not affected by selection restriction)
**Plans**: 1 plan
Plans:
- [x] 19-01-PLAN.md — Viewport meta zoom tokens + CSS user-select/touch-action rules in index.html
**UI hint**: yes

### Phase 20: Repository Hygiene
**Goal**: The repository is safe and non-embarrassing to make public — no credential exposure vectors, no personal data, no stale branding
**Depends on**: Phase 19
**Requirements**: HYG-01, HYG-02, HYG-03, HYG-04, HYG-05
**Success Criteria** (what must be TRUE):
  1. A Docker build from the project root cannot bake `.env` or `token_cache/` into the image (`.dockerignore` present and effective)
  2. `.claude/` directory is absent from `git ls-files` output and added to `.gitignore`
  3. `tests/test_sonos_probe.py` contains no personal IP address — all occurrences replaced with `192.168.1.100`
  4. No module docstring, FastAPI title, or user-agent string in source code references "Spotify Family Safe Mode"
  5. `.env.example` documents `UID`, `GID`, and `EVENTS_PATH` with explanatory comments
**Plans**: TBD

### Phase 21: Legal & Docs
**Goal**: A stranger who finds the repository has legal permission to use it, a clear explanation of what it does, and a documented path to contributing
**Depends on**: Phase 20
**Requirements**: DOCS-01, DOCS-02, DOCS-03
**Success Criteria** (what must be TRUE):
  1. `LICENSE` (MIT) is present at the repository root
  2. README opens with a stranger-facing lede — what the project is, hardware prerequisites, and quick start — without assuming prior knowledge of the author's setup
  3. `CONTRIBUTING.md` exists and covers local dev setup, how to run tests, and how to submit a PR
**Plans**: TBD

### Phase 22: CI & Tooling
**Goal**: The repository signals it is maintained — tests and lint pass in CI from the first day the public link goes out
**Depends on**: Phase 21
**Requirements**: CI-01, CI-02, CI-03, CI-04
**Success Criteria** (what must be TRUE):
  1. A push or pull request triggers GitHub Actions and runs the full `pytest tests/` suite without real Spotify credentials
  2. Ruff lint and format checks run in CI and fail the workflow on violations
  3. `pyproject.toml` exists at the repository root with `[tool.pytest.ini_options]` and `[tool.ruff]` sections
  4. README header displays a live CI status badge and a static MIT license badge
**Plans**: TBD

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Foundation | v1.0 | 2/2 | Complete | 2026-04-02 |
| 2. Content Filtering | v1.0 | 7/7 | Complete | 2026-04-02 |
| 3. Dashboard & Skip Feed | v1.0 | 5/5 | Complete | 2026-04-02 |
| 4. Sonos Discovery | v1.1 | 2/2 | Complete | 2026-04-02 |
| 5. README & Ops | v1.1 | 2/2 | Complete | 2026-04-02 |
| 6. Now Playing API | v1.2 | 4/4 | Complete | 2026-04-03 |
| 7. Manual Skip | v1.2 | 2/2 | Complete | 2026-04-03 |
| 8. Severity Badges | v1.2 | 1/1 | Complete | 2026-04-03 |
| 8.1. Allow-Reason Context | v1.2 | 2/2 | Complete | 2026-04-03 |
| 9. TrackEvalResult Refactor | v1.3 | 3/3 | Complete | 2026-04-04 |
| 10. Drug & Sexual Scanners | v1.3 | 2/2 | Complete | 2026-04-04 |
| 11. ContentChecker Pipeline Integration | v1.3 | 2/2 | Complete | 2026-04-04 |
| 12. Event Propagation & Incident Log | v1.3 | 2/2 | Complete | 2026-04-04 |
| 13. Dashboard Badge Variants | v1.3 | 1/1 | Complete | 2026-04-04 |
| 14. Idle Detection | v1.4 | 2/2 | Complete | 2026-04-04 |
| 15. Skip History | v1.4 | 2/2 | Complete | 2026-04-04 |
| 16. Filter Profiles | v1.4 | 3/3 | Complete | 2026-04-05 |
| 17. Rebrand | v1.5 | 1/1 | Complete | 2026-04-06 |
| 18. Profile Info Icon | v1.5 | 1/1 | Complete | 2026-04-06 |
| 19. Mobile Polish | v1.5 | 1/1 | Complete | 2026-04-06 |
| 20. Repository Hygiene | v1.6 | 0/? | Not started | - |
| 21. Legal & Docs | v1.6 | 0/? | Not started | - |
| 22. CI & Tooling | v1.6 | 0/? | Not started | - |
