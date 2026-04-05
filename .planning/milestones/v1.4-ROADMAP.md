# Roadmap: Spotify Family Safe Mode

## Milestones

- ✅ **v1.0 MVP** - Phases 1-3 (shipped 2026-04-02)
- ✅ **v1.1 Deployment** - Phases 4-5 (shipped 2026-04-02)
- ✅ **v1.2 Now Playing Status** - Phases 6-8.1 (shipped 2026-04-03)
- ✅ **v1.3 Drug & Sexual Reference Detection** - Phases 9-13 (shipped 2026-04-04)
- 🚧 **v1.4 Dashboard Polish & Filter Profiles** - Phases 14-16 (in progress)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1-3) - SHIPPED 2026-04-02</summary>

### Phase 1: Foundation
**Goal**: Project runs in Docker with Spotify OAuth and live polling
**Plans**: 2 plans

Plans:
- [x] 01-01: OAuth setup script and Docker scaffolding
- [x] 01-02: Asyncio daemon with track-change detection and SIGTERM shutdown

### Phase 2: Content Filtering
**Goal**: Tracks are evaluated and skipped based on explicit flag and lyric profanity scan
**Plans**: 7 plans

Plans:
- [x] 02-01 through 02-07: LRCLIB lyrics cache, ContentChecker pipeline, profanity severity tiers, Sonos skip, state persistence

### Phase 3: Dashboard & Skip Feed
**Goal**: Parent can monitor skips and toggle FSM from browser
**Plans**: 5 plans

Plans:
- [x] 03-01 through 03-05: SSE skip feed, FSM toggle API, dark-theme dashboard, consecutive-skip pause logic, file-based IPC

</details>

<details>
<summary>✅ v1.1 Deployment (Phases 4-5) - SHIPPED 2026-04-02</summary>

### Phase 4: Sonos Discovery
**Goal**: Sonos speakers are discovered automatically without manual IP configuration
**Plans**: 2 plans

Plans:
- [x] 04-01: SSDP auto-discovery wired at daemon startup
- [x] 04-02: Actionable multicast warnings; SONOS_SPEAKER_IPS as escape hatch

### Phase 5: README & Ops
**Goal**: Any developer can clone and run the project from the README alone
**Plans**: 2 plans

Plans:
- [x] 05-01: README.md with OAuth flow, UID/GID pitfall docs
- [x] 05-02: PROXMOX.md for LXC multicast/SSDP edge case

</details>

<details>
<summary>✅ v1.2 Now Playing Status (Phases 6-8.1) - SHIPPED 2026-04-03</summary>

### Phase 6: Now Playing API
**Goal**: Dashboard shows current track with real-time eval-state badge
**Plans**: 4 plans

Plans:
- [x] 06-01 through 06-04: GET /now-playing, shared token cache, now-playing card UI, SSE track_change/eval_result wiring

### Phase 7: Manual Skip
**Goal**: Parent can skip the current track from the dashboard without opening Spotify
**Plans**: 2 plans

Plans:
- [x] 07-01: POST /skip implementation with spotipy
- [x] 07-02: Skip button wired to dashboard

### Phase 8: Severity Badges
**Goal**: Dashboard shows severity-aware badges (Passed + Mild language simultaneously)
**Plans**: 1 plan

Plans:
- [x] 08-01: Severity propagation and multi-badge flex container

### Phase 8.1: Allow-Reason Context (INSERTED)
**Goal**: Severity-aware badge shown when track passes with mild language
**Plans**: 2 plans

Plans:
- [x] 08.1-01: Badge group CSS and JS severity rendering
- [x] 08.1-02: FSM-off badge variant

</details>

<details>
<summary>✅ v1.3 Drug & Sexual Reference Detection (Phases 9-13) - SHIPPED 2026-04-04</summary>

### Phase 9: TrackEvalResult Refactor
**Goal**: ContentChecker returns a named dataclass instead of a positional tuple
**Plans**: 3 plans

Plans:
- [x] 09-01: TrackEvalResult frozen dataclass definition
- [x] 09-02: All return sites and test mocks updated
- [x] 09-03: Zero bare-tuple unpacks verified

### Phase 10: Drug & Sexual Scanners
**Goal**: DrugScanner and SexualContentScanner modules exist with full unit test coverage
**Plans**: 2 plans

Plans:
- [x] 10-01: DrugScanner with 19-term conservative keyword set
- [x] 10-02: SexualContentScanner with 36-term SEXUAL_TERMS set, disjoint from SEVERITY_MAP

### Phase 11: ContentChecker Pipeline Integration
**Goal**: ContentChecker runs all three scanners unconditionally before priority decision
**Plans**: 2 plans

Plans:
- [x] 11-01: TDD RED scaffold and five-tier pipeline
- [x] 11-02: No-short-circuit contract enforced

### Phase 12: Event Propagation & Incident Log
**Goal**: Drug and sexual reference signals are logged to events.jsonl and now_playing.json on every skip path
**Plans**: 2 plans

Plans:
- [x] 12-01: _emit_eval_result helper extracting all four emit sites
- [x] 12-02: Four booleans propagated to both skip event writes

### Phase 13: Dashboard Badge Variants
**Goal**: Dashboard shows Drug reference (purple) and Sexual content (pink) badge variants in the skip feed
**Plans**: 1 plan

Plans:
- [x] 13-01: CSS badge classes and JS detection branches for drug/sexual variants

</details>

### 🚧 v1.4 Dashboard Polish & Filter Profiles (In Progress)

**Milestone Goal:** Make the dashboard accurately reflect real playback state, preserve skip history across reconnects, and let the parent select a named filter profile from the UI.

#### Phase 14: Idle Detection
**Goal**: Dashboard accurately shows when nothing is playing
**Depends on**: Phase 13
**Requirements**: IDLE-01, IDLE-02
**Success Criteria** (what must be TRUE):
  1. When Spotify reports no active playback, the now-playing card shows a "Nothing playing" (idle) view within ~5 seconds
  2. When playback resumes after an idle period, the now-playing card restores the current track without a page refresh
  3. Daemon writes idle state to now_playing.json so the web_ui can read it on reconnect
**Plans**: 2 plans

Plans:
- [x] 14-01-PLAN.md — Idle test scaffold: _run_n_empty_cycles helper and five RED idle tests
- [x] 14-02-PLAN.md — Idle implementation: daemon.py debounce counter + es.onmessage idle branch

#### Phase 15: Skip History
**Goal**: Skip feed history survives page refresh and SSE reconnect
**Depends on**: Phase 14
**Requirements**: HIST-01, HIST-02, HIST-03
**Success Criteria** (what must be TRUE):
  1. On page load, up to 20 most recent skip events appear in the feed immediately (before any new skips occur)
  2. After an SSE reconnect the skip feed retains all previously loaded entries (no blank-out)
  3. GET /feed returns the last N skip and five_skip_warning events from events.jsonl
**Plans**: 2 plans
**UI hint**: yes

Plans:
- [x] 15-01-PLAN.md — Event IDs in daemon + GET /feed endpoint with tests
- [x] 15-02-PLAN.md — Frontend hydration, SSE reconnect merge, DOM cap

#### Phase 16: Filter Profiles
**Goal**: Parent can select a named filter profile from the dashboard; the active profile controls which content rules apply
**Depends on**: Phase 15
**Requirements**: PROF-01, PROF-02, PROF-03, PROF-04
**Success Criteria** (what must be TRUE):
  1. Dashboard displays four named filter profiles and shows which one is currently active
  2. Parent can switch profiles from the dashboard UI; the selected profile takes effect immediately
  3. Active profile persists in state.json and is still selected after a service restart
  4. ContentChecker applies the active profile's rules (explicit_skip, min_severity, drug_enabled, sexual_enabled) on every track evaluation
**Plans**: 3 plans
**UI hint**: yes

Plans:
- [x] 16-01-PLAN.md — ContentChecker explicit_skip param + daemon PROFILE_MAP + _build_content_checker + poll_loop profile wiring
- [x] 16-02-PLAN.md — POST /profile API + __PROFILE_INITIAL__ injection in dashboard route
- [x] 16-03-PLAN.md — Split-button HTML/CSS/JS: left zone = FSM toggle, right zone = profile dropdown

## Progress

**Execution Order:**
Phases execute in numeric order: 14 → 15 → 16

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
| 14. Idle Detection | v1.4 | 2/2 | Complete    | 2026-04-04 |
| 15. Skip History | v1.4 | 2/2 | Complete    | 2026-04-04 |
| 16. Filter Profiles | v1.4 | 3/3 | Complete    | 2026-04-05 |
