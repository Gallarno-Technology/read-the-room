# Roadmap: Spotify Family Safe Mode

## Milestones

- ✅ **v1.0 MVP** — Phases 1-3 (shipped 2026-04-02)
- 🚧 **v1.1 Deployment** — Phases 4-5 (in progress)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1-3) — SHIPPED 2026-04-02</summary>

- [x] **Phase 1: Core Daemon & Spotify Auth** — Authenticated poll loop as Docker service; track-change detection (completed 2026-04-01)
- [x] **Phase 2: Content Filtering & Auto-Skip** — Three-tier filter (explicit flag → LRCLIB → profanity scan); dual skip path SoCo + Spotify API; FSM toggle (completed 2026-04-02)
- [x] **Phase 3: Web UI Dashboard** — Real-time skip feed + FSM toggle via FastAPI/SSE; 5-skip pause; dismissible warning banner (completed 2026-04-02)

See `.planning/milestones/v1.0-ROADMAP.md` for full phase details.

</details>

### 🚧 v1.1 Deployment (In Progress)

**Milestone Goal:** Make the project easy to clone and run on any Docker host, fix Sonos SSDP discovery so manual IP mapping isn't required, and verify boot persistence.

- [ ] **Phase 4: Sonos Discovery Hardening** — SSDP auto-discovery with IP fallback and actionable failure logging
- [ ] **Phase 5: Deployment & Documentation** — Clone-and-run README, healthcheck, and safe update workflow

## Phase Details

### Phase 4: Sonos Discovery Hardening
**Goal**: Sonos speakers are discovered automatically on properly configured networks, with `SONOS_SPEAKER_IPS` as an explicit escape hatch and clear guidance when discovery fails
**Depends on**: Phase 3
**Requirements**: DISC-01, DISC-02, DISC-03
**Success Criteria** (what must be TRUE):
  1. Service connects to a Sonos speaker on a multicast-enabled network without any `SONOS_SPEAKER_IPS` configuration
  2. Setting `SONOS_SPEAKER_IPS` in `.env` skips SSDP and uses the provided IPs directly (fallback still works)
  3. When SSDP discovery finds no speakers, the log contains a message with a concrete firewall/multicast remediation hint
  4. `.env.example` documents `SONOS_SPEAKER_IPS` as an optional escape hatch with a comment explaining when to use it
**Plans**: 2 plans

Plans:
- [x] 04-01-PLAN.md — TDD scaffold: failing tests for probe_sonos_speakers and updated skip_client warnings
- [ ] 04-02-PLAN.md — Implementation: probe_sonos_speakers in daemon.py, updated warnings in skip_client.py, reframed .env.example comment

### Phase 5: Deployment & Documentation
**Goal**: Any developer with Docker can clone the repo and have the service running — and the service survives reboots, hangs silently, and updates cleanly
**Depends on**: Phase 4
**Requirements**: DEPL-01, DEPL-02, DEPL-03, DEPL-04, DEPL-05
**Success Criteria** (what must be TRUE):
  1. A developer following the README from a fresh clone reaches a running service without consulting any other source
  2. README includes Sonos network requirements (multicast UDP 1900, firewall rules, Proxmox/LXC bridge config)
  3. After a host reboot, the service resumes automatically with no manual intervention
  4. A silently hung daemon container is restarted automatically by Docker (healthcheck triggers restart)
  5. Running `git pull && docker compose up -d --build` updates to the latest version with no data loss and no manual migration steps
**Plans**: TBD
**UI hint**: yes

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Core Daemon & Spotify Auth | v1.0 | 2/2 | Complete | 2026-04-01 |
| 2. Content Filtering & Auto-Skip | v1.0 | 7/7 | Complete | 2026-04-02 |
| 3. Web UI Dashboard | v1.0 | 5/5 | Complete | 2026-04-02 |
| 4. Sonos Discovery Hardening | v1.1 | 1/2 | In Progress|  |
| 5. Deployment & Documentation | v1.1 | 0/? | Not started | - |
