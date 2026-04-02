# Requirements: Spotify Family Safe Mode

**Defined:** 2026-04-02
**Core Value:** Songs that violate family-safe rules are skipped automatically before children hear them — with zero manual effort when Family Safe Mode is on.

## v1.1 Requirements

### DISC — Sonos Discovery

- [ ] **DISC-01**: Sonos speakers are discovered automatically via SSDP on a properly configured network — no `SONOS_SPEAKER_IPS` required
- [ ] **DISC-02**: `SONOS_SPEAKER_IPS` remains as an explicit override fallback, documented as an escape hatch for restricted networks
- [ ] **DISC-03**: Service logs a clear, actionable message when SSDP discovery fails (includes firewall/multicast hint)

### DEPL — Deployment

- [ ] **DEPL-01**: README covers complete first-time setup: prerequisites, clone, `.env` config, Spotify OAuth, and `docker compose up -d`
- [ ] **DEPL-02**: README documents Sonos network requirements (multicast UDP port 1900, firewall rules, Proxmox LXC bridge config)
- [ ] **DEPL-03**: Service survives host reboots without manual intervention — Docker daemon auto-start documented and verified
- [ ] **DEPL-04**: `docker-compose.yml` includes a healthcheck that detects a silently hung daemon and triggers automatic restart
- [ ] **DEPL-05**: Updating to a new version requires only `git pull && docker compose up -d --build` — no manual migration steps, data safe across updates

## v2 Requirements

### Sentiment Analysis

- **SENT-01**: Lyrics are analyzed for adult themes: depression, suicide, drug use, and suggestive/sexual content
- **SENT-02**: Theme detection uses an LLM API with structured output (handles euphemism and implicit references)
- **SENT-03**: Theme sensitivity levels are configurable per category

### Sonos Automation

- **SONO-01**: Family Safe Mode automatically activates when Spotify playback switches to a Sonos speaker
- **SONO-02**: Family Safe Mode automatically deactivates when playback moves to phone/headphones
- **SONO-03**: Support for multiple Sonos rooms without env var mapping

### Apple Music Support

- **AMUS-01**: Service supports Apple Music playback monitoring alongside Spotify
- **AMUS-02**: Skip and filtering logic is abstracted behind a common playback interface

### Profiles

- **PROF-01**: Per-child profiles or age-based filtering tiers

## Out of Scope

| Feature | Reason |
|---------|--------|
| Signal bot notifications | Replaced by web dashboard |
| iOS native app | Web dashboard covers the use case |
| Cloud deployment | Home server is free, private, and sufficient; cloud adds cost and complexity |
| Helm chart / Kubernetes | Overkill for a single-household home server service |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| DISC-01 | Phase 4 | Pending |
| DISC-02 | Phase 4 | Pending |
| DISC-03 | Phase 4 | Pending |
| DEPL-01 | Phase 5 | Pending |
| DEPL-02 | Phase 5 | Pending |
| DEPL-03 | Phase 5 | Pending |
| DEPL-04 | Phase 5 | Pending |
| DEPL-05 | Phase 5 | Pending |

**Coverage:**
- v1.1 requirements: 8 total
- Mapped to phases: 8
- Unmapped: 0

---
*Requirements defined: 2026-04-02*
*Last updated: 2026-04-02 after v1.1 roadmap creation*
