# Requirements: Spotify Family Safe Mode

**Defined:** 2026-04-04
**Milestone:** v1.4 — Dashboard Polish & Filter Profiles
**Core Value:** Songs that violate family-safe rules are skipped automatically before children hear them — with zero manual effort when Family Safe Mode is on.

## v1.4 Requirements

Requirements for this milestone. Each maps to a roadmap phase.

### Skip History

- [x] **HIST-01**: User sees up to 20 most recent session skips in the skip feed on page load
- [x] **HIST-02**: Skip feed history is preserved after SSE reconnects (no blank-out on reconnect)
- [x] **HIST-03**: `GET /feed` endpoint returns last N skip/five_skip_warning events from events.jsonl

### Idle Detection

- [x] **IDLE-01**: Daemon writes idle state to now_playing.json when Spotify reports no active playback
- [x] **IDLE-02**: Dashboard now-playing card transitions to "Nothing playing" view within ~5s of playback stopping

### Filter Profiles

- [ ] **PROF-01**: User can select one of four named filter profiles from the dashboard UI
- [ ] **PROF-02**: Active profile persists in state.json and survives service restart
- [ ] **PROF-03**: ContentChecker applies the active profile's per-scanner rules (explicit_skip, min_severity, drug_enabled, sexual_enabled)
- [ ] **PROF-04**: Dashboard displays the currently active profile name

## Future Requirements

### Filter Profiles (deferred)

- **PROF-05**: Per-room profile assignment (Living Room vs. Office)
- **PROF-06**: Custom profile creation (user-defined thresholds, not just presets)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Per-child profiles | Covered by v1.4 presets; per-child complexity deferred to v2+ |
| Severity scoring within categories | Boolean per-scanner flags sufficient for v1.4 |
| Real-time profile preview | Nice-to-have; static profile names sufficient |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| HIST-01 | Phase 15 | Complete |
| HIST-02 | Phase 15 | Complete |
| HIST-03 | Phase 15 | Complete |
| IDLE-01 | Phase 14 | Complete |
| IDLE-02 | Phase 14 | Complete |
| PROF-01 | Phase 16 | Pending |
| PROF-02 | Phase 16 | Pending |
| PROF-03 | Phase 16 | Pending |
| PROF-04 | Phase 16 | Pending |

**Coverage:**
- v1.4 requirements: 9 total
- Mapped to phases: 9
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-04*
*Last updated: 2026-04-04 after initial definition*
