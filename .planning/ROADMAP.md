# Roadmap: Spotify Family Safe Mode

## Milestones

- ✅ **v1.0 MVP** — Phases 1-3 (shipped 2026-04-02)
- ✅ **v1.1 Deployment** — Phases 4-5 (shipped 2026-04-02)

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

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Core Daemon & Spotify Auth | v1.0 | 2/2 | Complete | 2026-04-01 |
| 2. Content Filtering & Auto-Skip | v1.0 | 7/7 | Complete | 2026-04-02 |
| 3. Web UI Dashboard | v1.0 | 5/5 | Complete | 2026-04-02 |
| 4. Sonos Discovery Hardening | v1.1 | 2/2 | Complete | 2026-04-02 |
| 5. Deployment & Documentation | v1.1 | 2/2 | Complete | 2026-04-02 |
