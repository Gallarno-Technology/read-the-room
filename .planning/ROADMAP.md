# Roadmap: Spotify Family Safe Mode

## Milestones

- ✅ **v1.0 MVP** — Phases 1-3 (shipped 2026-04-02)
- ✅ **v1.1 Deployment** — Phases 4-5 (shipped 2026-04-02)
- ✅ **v1.2 Now Playing Status** — Phases 6-8.1 (shipped 2026-04-03)
- ✅ **v1.3 Drug & Sexual Reference Detection** — Phases 9-13 (shipped 2026-04-04)
- ✅ **v1.4 Dashboard Polish & Filter Profiles** — Phases 14-16 (shipped 2026-04-05)
- 🚧 **v1.5 Dashboard Polish & Mobile UX** — Phases 17-19 (in progress)

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

### 🚧 v1.5 Dashboard Polish & Mobile UX (In Progress)

**Milestone Goal:** Polish the dashboard with a rebrand to "Read the Room," per-profile transparency via an info icon, and mobile-friendly behavior fixes.

- [ ] **Phase 17: Rebrand** — Update app display name to "Read the Room" in UI and README
- [ ] **Phase 18: Profile Info Icon** — Add info icon revealing what the active profile skips
- [ ] **Phase 19: Mobile Polish** — Prevent pinch-zoom and restrict text selection on UI chrome

## Phase Details

### Phase 17: Rebrand
**Goal**: The app presents itself as "Read the Room" everywhere a user sees its name
**Depends on**: Phase 16
**Requirements**: RBR-01, RBR-02
**Success Criteria** (what must be TRUE):
  1. Browser tab shows "Read the Room" as the page title
  2. Dashboard heading displays "Read the Room" (not "Spotify Family Safe Mode")
  3. README.md header and opening paragraph reference "Read the Room"
**Plans**: TBD
**UI hint**: yes

### Phase 18: Profile Info Icon
**Goal**: Parents can see exactly what content each filter profile blocks without leaving the dashboard
**Depends on**: Phase 17
**Requirements**: INFO-01, INFO-02
**Success Criteria** (what must be TRUE):
  1. An info icon (ⓘ) is visible on the FSM control card at all times, regardless of FSM state
  2. Tapping or clicking the icon reveals a readable breakdown of what the active profile skips (profanity level, drug refs, sexual content, explicit flag)
  3. The breakdown updates when the active profile changes
**Plans**: TBD
**UI hint**: yes

### Phase 19: Mobile Polish
**Goal**: The dashboard behaves predictably on mobile — no accidental zoom or text selection on UI chrome
**Depends on**: Phase 18
**Requirements**: MOB-01, MOB-02
**Success Criteria** (what must be TRUE):
  1. Pinch-zoom and double-tap zoom are disabled on the dashboard viewport on mobile
  2. Buttons, badges, labels, and profile options cannot be accidentally selected as text
  3. Track title and artist text remain selectable (not affected by selection restriction)
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
| 17. Rebrand | v1.5 | 0/TBD | Not started | - |
| 18. Profile Info Icon | v1.5 | 0/TBD | Not started | - |
| 19. Mobile Polish | v1.5 | 0/TBD | Not started | - |
