# Roadmap: Spotify Family Safe Mode

## Milestones

- ✅ **v1.0 MVP** — Phases 1-3 (shipped 2026-04-02)
- ✅ **v1.1 Deployment** — Phases 4-5 (shipped 2026-04-02)
- 🚧 **v1.2 Now Playing Status** — Phases 6-8 (in progress)
- 📋 **v1.3 Drug & Sexual Reference Detection** — Phases TBD (planned)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1-3) — SHIPPED 2026-04-02</summary>

- [x] **Phase 1: Core Daemon & Spotify Auth** — Authenticated poll loop as Docker service; track-change detection (completed 2026-04-01)
- [x] **Phase 2: Content Filtering & Auto-Skip** — Three-tier filter (explicit flag → LRCLIB → profanity scan); dual skip path SoCo + Spotify API; FSM toggle (completed 2026-04-02)
- [x] **Phase 3: Web UI Dashboard** — Real-time skip feed + FSM toggle via FastAPI/SSE; 5-skip pause; dismissible warning banner (completed 2026-04-02)

See `.planning/milestones/v1.0-ROADMAP.md` for full phase details.

</details>

<details>
<summary>✅ v1.1 Deployment (Phases 4-5) — SHIPPED 2026-04-02</summary>

- [x] **Phase 4: Sonos Discovery Hardening** — SSDP auto-discovery with IP fallback and actionable failure logging (completed 2026-04-02)
- [x] **Phase 5: Deployment & Documentation** — Clone-and-run README, healthcheck, and safe update workflow (completed 2026-04-02)

See `.planning/milestones/v1.1-ROADMAP.md` for full phase details.

</details>

### 🚧 v1.2 Now Playing Status (In Progress)

**Milestone Goal:** Dashboard shows the current track with its real-time filter evaluation state and a manual skip button, so parents can see what's playing and act on it without opening Spotify.

- [x] **Phase 6: Daemon SSE Extensions** — Emit track_change and eval_result events for all tracks; write now_playing.json snapshot (completed 2026-04-03)
- [ ] **Phase 7: Web UI Backend** — Spotipy init in web_ui; GET /now-playing hydration endpoint; POST /skip endpoint
- [ ] **Phase 8: Dashboard Frontend** — Now-playing card, evaluation badge state machine, album art, skip button, SSE reconnect hydration

### 📋 v1.3 Drug & Sexual Reference Detection (Planned)

**Milestone Goal:** Extend the filter pipeline with drug reference and sexual content detection signals, both derived from existing LRCLIB lyrics with no new dependencies, logged to the incident file, and visible in the dashboard.

*Phases to be numbered after v1.2 ships.*

## Phase Details

### Phase 6: Daemon SSE Extensions
**Goal**: The daemon emits real-time events for every track so the web UI and browser always have current state to consume
**Depends on**: Phase 5
**Requirements**: DAEM-01, DAEM-02, DAEM-03
**Success Criteria** (what must be TRUE):
  1. A `track_change` event appears in `skip_events.jsonl` immediately when a new track is detected, before ContentChecker runs, with `eval_state: "evaluating"`
  2. An `eval_result` event appears in `skip_events.jsonl` after ContentChecker completes for every track — including tracks that pass — with `track_id` and final `eval_state`
  3. `data/now_playing.json` is written on track detection (evaluating state) and overwritten with the final state after evaluation
  4. Existing skip and warning events are unaffected — all prior event types still appear correctly in the feed
**Plans**: 4 plans
Plans:
- [x] 06-01-PLAN.md — Failing test scaffold (9 xfail stubs for DAEM-01, DAEM-02, DAEM-03)
- [x] 06-02-PLAN.md — Env var + function rename: SKIP_EVENTS_PATH → EVENTS_PATH, _append_skip_event → _append_event
- [x] 06-03-PLAN.md — Event emission in poll_loop: track_change (DAEM-01) + eval_result all branches (DAEM-02)
- [x] 06-04-PLAN.md — now_playing.json writer: _write_now_playing helper + call sites (DAEM-03)

### Phase 7: Web UI Backend
**Goal**: The web UI container can serve current track state for page-load hydration and execute a manual skip directly against the Spotify API
**Depends on**: Phase 6
**Requirements**: SKIP-02, SKIP-03
**Success Criteria** (what must be TRUE):
  1. `GET /now-playing` returns the current track metadata and eval state read from `now_playing.json`, with a defined idle response when no track is playing
  2. `POST /skip` calls the Spotify API and returns success — the track advances
  3. A manual skip via `POST /skip` does not increment the daemon's consecutive-skip counter (counter stays at its pre-skip value)
  4. The web_ui spotipy instance authenticates using the shared token cache without requiring a second OAuth flow
**Plans**: 2 plans
Plans:
- [x] 07-01-PLAN.md — Infrastructure + test scaffold: spotipy in requirements.txt, token_cache volume in docker-compose.yml, 4 failing tests
- [ ] 07-02-PLAN.md — Endpoint implementation: NOW_PLAYING_PATH + sp init + GET /now-playing + POST /skip in web_ui/main.py

### Phase 8: Dashboard Frontend
**Goal**: Parents can see the current track, its real-time evaluation state badge, and album artwork, and skip it from the dashboard without opening Spotify
**Depends on**: Phase 7
**Requirements**: NOW-01, NOW-02, NOW-03, NOW-04, NOW-05, NOW-06, NOW-07, SKIP-01, SKIP-04
**Success Criteria** (what must be TRUE):
  1. Opening the dashboard mid-session shows the current track name, artist, album art, and evaluation badge without waiting for a new track to start
  2. The badge shows "Evaluating" the moment a new track starts and updates to its final state (Passed / No lyrics / Skipped) when evaluation completes — no manual refresh needed
  3. After SSE reconnects, the card repopulates correctly with current track state rather than going blank
  4. An `eval_result` event with a mismatched `track_id` does not overwrite the displayed badge — only the badge matching the currently displayed track updates
  5. Clicking the skip button skips the track; the button is disabled while the request is in flight and re-enables when the request completes
**Plans**: TBD
**UI hint**: yes

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Core Daemon & Spotify Auth | v1.0 | 2/2 | Complete | 2026-04-01 |
| 2. Content Filtering & Auto-Skip | v1.0 | 7/7 | Complete | 2026-04-02 |
| 3. Web UI Dashboard | v1.0 | 5/5 | Complete | 2026-04-02 |
| 4. Sonos Discovery Hardening | v1.1 | 2/2 | Complete | 2026-04-02 |
| 5. Deployment & Documentation | v1.1 | 2/2 | Complete | 2026-04-02 |
| 6. Daemon SSE Extensions | v1.2 | 4/4 | Complete   | 2026-04-03 |
| 7. Web UI Backend | v1.2 | 1/2 | In Progress|  |
| 8. Dashboard Frontend | v1.2 | 0/? | Not started | - |
