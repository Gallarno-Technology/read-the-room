# Requirements: Spotify Family Safe Mode

**Defined:** 2026-04-05
**Milestone:** v1.5 — Dashboard Polish & Mobile UX
**Core Value:** Songs that violate family-safe rules are skipped automatically before children hear them — with zero manual effort when Family Safe Mode is on.

## v1.5 Requirements

Requirements for this milestone. Each maps to a roadmap phase.

### Rebrand

- [ ] **RBR-01**: Dashboard `<title>` tag and visible app heading display "Read the Room"
- [ ] **RBR-02**: README.md header and introduction updated to "Read the Room"

### Profile Info

- [ ] **INFO-01**: An info icon (ⓘ) is visible on the FSM control card at all times
- [ ] **INFO-02**: Tapping/clicking the info icon reveals a breakdown of what the active profile skips (profanity, drug refs, sexual content, explicit flag)

### Mobile UX

- [ ] **MOB-01**: Dashboard viewport prevents pinch-zoom and double-tap zoom on mobile
- [ ] **MOB-02**: Buttons, labels, badges, and profile options have `user-select: none` — track title/artist remain selectable

## Future Requirements

### Rebrand

- **RBR-03**: Rename repo directory and Python filenames to match new brand

## Out of Scope

| Feature | Reason |
|---------|--------|
| Rename source files / repo directory | Low value, high churn — display name change sufficient for v1.5 |
| Info icon inside the dropdown per-option | Card-level icon covers the use case without cluttering the dropdown |
| Full mobile responsive layout | Small scope — fixing zoom/select is the quick win; full responsive is a future milestone |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| RBR-01 | Phase 17 | Pending |
| RBR-02 | Phase 17 | Pending |
| INFO-01 | Phase 18 | Pending |
| INFO-02 | Phase 18 | Pending |
| MOB-01 | Phase 19 | Pending |
| MOB-02 | Phase 19 | Pending |

**Coverage:**
- v1.5 requirements: 6 total
- Mapped to phases: 6
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-05*
*Last updated: 2026-04-05 after roadmap creation (phases 17-19 assigned)*
