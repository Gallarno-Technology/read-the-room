# Roadmap: Read the Room

## Milestones

- ✅ **v1.0 MVP** — Phases 1-3 (shipped 2026-04-02)
- ✅ **v1.1 Deployment** — Phases 4-5 (shipped 2026-04-02)
- ✅ **v1.2 Now Playing Status** — Phases 6-8.1 (shipped 2026-04-03)
- ✅ **v1.3 Drug & Sexual Reference Detection** — Phases 9-13 (shipped 2026-04-04)
- ✅ **v1.4 Dashboard Polish & Filter Profiles** — Phases 14-16 (shipped 2026-04-05)
- ✅ **v1.5 Dashboard Polish & Mobile UX** — Phases 17-19 (shipped 2026-04-06)
- 🚧 **v1.6 Open Source** — Phases 20-22 (in progress)
- 🔜 **v1.8 Multi-User Beta** — Phases 27-32

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

- [x] **Phase 20: Repository Hygiene** — Remove personal data, fix credential exposure, sanitize branding and IPs (completed 2026-04-08)
- [ ] **Phase 21: Legal & Docs** — Add LICENSE, rewrite README for strangers, create CONTRIBUTING.md
- [ ] **Phase 22: CI & Tooling** — GitHub Actions CI, pyproject.toml, ruff lint/format, README badges

### 🔜 v1.8 Multi-User Beta

**Milestone Goal:** Run up to 5 independent user instances on a hosted server — each with their own Spotify token, daemon, and isolated data — accessible via an opaque ID stored in browser localStorage.

- [x] **Phase 27: User Registry + Operator CLI** — Per-user data directory isolation and operator onboarding commands (completed 2026-04-17)
- [x] **Phase 28: Cookie Routing + Per-User SSE** — All routes resolve per-user context; SSE streams are isolated and leak-free (completed 2026-04-18)
- [x] **Phase 29: OAuth Onboarding Flow** — Server-side OAuth callback completes token exchange and daemon launch (completed 2026-04-18)
- [ ] **Phase 30: Per-User Daemon Management** — Each user's daemon spawns, supervises, and restarts automatically
- [ ] **Phase 31: VPS Deployment + HTTPS** — Caddy TLS termination and environment-conditional Sonos networking
- [ ] **Phase 32: Frontend ID Persistence** — ID entry gate on first visit; cookie + localStorage on success

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
**Plans**: 2 plans
Plans:
- [x] 20-01-PLAN.md — Create .dockerignore and untrack .claude/ from git (HYG-01, HYG-02)
- [x] 20-02-PLAN.md — Replace personal IP, rename branding strings, update .env.example (HYG-03, HYG-04, HYG-05)

### Phase 21: Legal & Docs
**Goal**: A stranger who finds the repository has legal permission to use it, a clear explanation of what it does, and a documented path to contributing
**Depends on**: Phase 20
**Requirements**: DOCS-01, DOCS-02, DOCS-03
**Success Criteria** (what must be TRUE):
  1. `LICENSE` (MIT) is present at the repository root
  2. README opens with a stranger-facing lede — what the project is, hardware prerequisites, and quick start — without assuming prior knowledge of the author's setup
  3. `CONTRIBUTING.md` exists and covers local dev setup, how to run tests, and how to submit a PR
**Plans**: 2 plans
Plans:
- [x] 21-01-PLAN.md — Create LICENSE (MIT) and CONTRIBUTING.md (DOCS-01, DOCS-03)
- [ ] 21-02-PLAN.md — Rewrite README.md for a stranger-facing audience (DOCS-02)

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

---

### Phase 27: User Registry + Operator CLI
**Goal**: An operator can provision a new user, inspect the registry, and remove a user — all data properly namespaced and isolated on disk
**Depends on**: Phase 23 (TrackCache)
**Requirements**: ISOL-01, ISOL-02, ISOL-03, OPS-01, OPS-02
**Success Criteria** (what must be TRUE):
  1. Running `manage_users.py generate-url <name>` prints a new uid and a valid Spotify OAuth URL with that uid in the `state` parameter
  2. After provisioning, `users/{uid}/` exists with `state.json`, `data/events.jsonl`, `data/now_playing.json`, and `token_cache/` subdirectory
  3. `users.json` at the project root contains the new uid, name, and `created_at` timestamp after provisioning
  4. Running `manage_users.py remove <uid>` stops the daemon, removes the user's directory tree, and removes their entry from `users.json`
  5. `lyrics_cache.db` is a single shared file at the project root — not duplicated inside any per-user directory
**Plans**: 2 plans
Plans:
- [x] 27-01-PLAN.md — UserRegistry class: uid generation, directory scaffolding, users.json persistence (ISOL-01, ISOL-02, ISOL-03)
- [ ] 27-02-PLAN.md — scripts/manage_users.py CLI: generate-url and remove subcommands (OPS-01, OPS-02)

### Phase 28: Cookie Routing + Per-User SSE
**Goal**: Every API request resolves to the correct user's data from a uid cookie; SSE streams are isolated per user and clean up on disconnect
**Depends on**: Phase 27
**Requirements**: ROUTE-01, ROUTE-02
**Success Criteria** (what must be TRUE):
  1. Requests without a valid uid cookie are rejected (401 or redirect to ID gate) rather than falling through to global state
  2. All endpoints (`/now-playing`, `/skip`, `/events`, `/profile`) serve data scoped to the cookie-identified user's file paths
  3. Opening `/events` in two browser tabs for different users delivers independent, non-overlapping event streams
  4. Closing a browser tab stops the SSE tail task for that user without leaking open file handles or lingering subscriber entries
**Plans**: 2 plans
Plans:
- [x] 28-01-PLAN.md — UserContext dataclass, get_user_context Depends, all non-SSE routes wired per-user (ROUTE-01)
- [ ] 28-02-PLAN.md — Per-uid SSE tail tasks with lazy start and immediate teardown (ROUTE-02)

### Phase 29: OAuth Onboarding Flow
**Goal**: An operator-initiated OAuth flow completes server-side, writes the token to the correct user path, and lands the new user on their authenticated dashboard
**Depends on**: Phase 28
**Requirements**: AUTH-01, AUTH-02, AUTH-03
**Success Criteria** (what must be TRUE):
  1. Navigating to the OAuth URL generated by `manage_users.py generate-url` initiates the Spotify authorization flow correctly
  2. After the user grants consent, `GET /auth/callback` validates the `state` uid, exchanges the code, and writes the token to `users/{uid}/token_cache/`
  3. A callback carrying an invalid or unrecognized `state` parameter returns an error and does not write any token to disk
  4. The user's daemon starts automatically after token write completes — no additional operator command required
**Plans**: 2 plans
Plans:
- [x] 29-01-PLAN.md — UserRegistry.activate(uid): flip pending user to active with atomic write + TDD tests (AUTH-01)
- [ ] 29-02-PLAN.md — GET /auth/callback: validate state, exchange code, spawn daemon, set uid cookie + TDD tests (AUTH-01, AUTH-02, AUTH-03)

### Phase 30: Per-User Daemon Management
**Goal**: Each authenticated user has a daemon that starts on server boot, restarts on crash, and does not overwhelm the shared Spotify API rate limit
**Depends on**: Phase 29
**Requirements**: PROC-01, PROC-02, PROC-03, PROC-04
**Success Criteria** (what must be TRUE):
  1. After `web_ui` starts, every uid present in `users.json` has a running daemon process within a few seconds — with uid-specific env vars (`STATE_PATH`, `EVENTS_PATH`, `LYRICS_DB_PATH`, `SPOTIFY_CACHE_PATH`)
  2. Killing a user's daemon process causes the supervisor coroutine to restart it automatically without operator intervention
  3. With multiple users active, each daemon's `POLL_INTERVAL_SECONDS` defaults to `3` — observable in the spawned process's env vars
  4. A daemon that exits due to token expiry does not crash-loop — the supervisor detects clean exits and holds off on restart
**Plans**: 3 plans
Plans:
- [x] 30-01-PLAN.md — Wave 0 test scaffolds: failing tests for _spawn_daemon, supervisor, lifespan, 401 counter, PID kill (PROC-01, PROC-02, PROC-03, PROC-04)
- [ ] 30-02-PLAN.md — web_ui/main.py supervisor layer: _spawn_daemon, _supervisor_for_uid, lifespan, OAuth callback refactor (PROC-01, PROC-02, PROC-03, PROC-04)
- [ ] 30-03-PLAN.md — daemon.py consecutive 401 counter + manage_users.py PID kill for remove (PROC-02, PROC-04)

### Phase 31: VPS Deployment + HTTPS
**Goal**: The service is reachable over HTTPS from the public internet with automatic TLS, and the Sonos networking mode is environment-controlled
**Depends on**: Phase 30
**Requirements**: DEPLOY-01, DEPLOY-02, DEPLOY-03
**Success Criteria** (what must be TRUE):
  1. `docker compose up` on a VPS brings up the Caddy service and serves HTTPS on port 443 with a valid Let's Encrypt certificate — no manual certbot required
  2. The Spotify OAuth redirect callback lands on the HTTPS URL, not `localhost`, completing the flow successfully
  3. Setting `SONOS_ENABLED=false` in `.env` removes `network_mode: host` from the `web_ui` container; setting it `true` keeps host networking — no compose file edits required
**Plans**: TBD

### Phase 32: Frontend ID Persistence
**Goal**: A user enters their access code once and every subsequent visit loads their dashboard directly without re-entering it
**Depends on**: Phase 31
**Requirements**: UI-01, UI-02, UI-03, UI-04
**Success Criteria** (what must be TRUE):
  1. A browser with no uid cookie visiting the root URL sees a full-page ID entry gate, not the dashboard
  2. Entering a valid ID at the gate sets the httpOnly uid cookie and writes the uid to `localStorage`; the dashboard loads immediately without a second prompt
  3. Entering an unknown or malformed ID at the gate shows a clear inline error message — no silent redirect or blank screen
  4. A browser arriving at the post-OAuth callback URL has the uid cookie and `localStorage` entry set automatically and then loads the dashboard — no second ID entry required
**Plans**: TBD
**UI hint**: yes

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
| 20. Repository Hygiene | v1.6 | 2/2 | Complete    | 2026-04-08 |
| 21. Legal & Docs | v1.6 | 1/2 | In Progress|  |
| 22. CI & Tooling | v1.6 | 0/? | Not started | - |
| 27. User Registry + Operator CLI | v1.8 | 2/2 | Complete    | 2026-04-17 |
| 28. Cookie Routing + Per-User SSE | v1.8 | 1/2 | Complete    | 2026-04-18 |
| 29. OAuth Onboarding Flow | v1.8 | 1/2 | Complete    | 2026-04-18 |
| 30. Per-User Daemon Management | v1.8 | 1/3 | In Progress | 2026-04-26 |
| 31. VPS Deployment + HTTPS | v1.8 | 0/? | Not started | - |
| 32. Frontend ID Persistence | v1.8 | 0/? | Not started | - |
