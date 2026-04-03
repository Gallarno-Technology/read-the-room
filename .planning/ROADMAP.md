# Roadmap: Spotify Family Safe Mode

## Milestones

- ✅ **v1.0 MVP** — Phases 1-3 (shipped 2026-04-02)
- ✅ **v1.1 Deployment** — Phases 4-5 (shipped 2026-04-02)
- ✅ **v1.2 Now Playing Status** — Phases 6-8.1 (shipped 2026-04-03)
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

<details>
<summary>✅ v1.2 Now Playing Status (Phases 6-8.1) — SHIPPED 2026-04-03</summary>

- [x] **Phase 6: Daemon SSE Extensions** — Emit track_change and eval_result events for all tracks; write now_playing.json snapshot (completed 2026-04-03)
- [x] **Phase 7: Web UI Backend** — Spotipy init in web_ui; GET /now-playing hydration endpoint; POST /skip endpoint (completed 2026-04-03)
- [x] **Phase 8: Dashboard Frontend** — Now-playing card, evaluation badge state machine, album art, skip button, SSE reconnect hydration (completed 2026-04-03)
- [x] **Phase 8.1: Allow-reason Context** — Severity-aware badge when track passes with mild language; "Mild language" badge alongside "Passed" in dashboard (INSERTED) (completed 2026-04-03)

See `.planning/milestones/v1.2-ROADMAP.md` for full phase details.

</details>

### 📋 v1.3 Drug & Sexual Reference Detection (Planned)

**Milestone Goal:** Extend the filter pipeline with drug reference and sexual content detection signals, both derived from existing LRCLIB lyrics with no new dependencies, logged to the incident file, and visible in the dashboard.

*Phases to be defined by `/gsd:new-milestone`.*

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Core Daemon & Spotify Auth | v1.0 | 2/2 | Complete | 2026-04-01 |
| 2. Content Filtering & Auto-Skip | v1.0 | 7/7 | Complete | 2026-04-02 |
| 3. Web UI Dashboard | v1.0 | 5/5 | Complete | 2026-04-02 |
| 4. Sonos Discovery Hardening | v1.1 | 2/2 | Complete | 2026-04-02 |
| 5. Deployment & Documentation | v1.1 | 2/2 | Complete | 2026-04-02 |
| 6. Daemon SSE Extensions | v1.2 | 4/4 | Complete | 2026-04-03 |
| 7. Web UI Backend | v1.2 | 2/2 | Complete | 2026-04-03 |
| 8. Dashboard Frontend | v1.2 | 1/1 | Complete | 2026-04-03 |
| 8.1. Allow-reason Context | v1.2 | 2/2 | Complete | 2026-04-03 |
