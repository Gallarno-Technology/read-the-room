# Roadmap: Spotify Family Safe Mode

## Milestones

- ✅ **v1.0 MVP** — Phases 1-3 (shipped 2026-04-02)
- ✅ **v1.1 Deployment** — Phases 4-5 (shipped 2026-04-02)
- ✅ **v1.2 Now Playing Status** — Phases 6-8.1 (shipped 2026-04-03)
- 🚧 **v1.3 Drug & Sexual Reference Detection** — Phases 9-13 (in progress)

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

### 🚧 v1.3 Drug & Sexual Reference Detection (In Progress)

**Milestone Goal:** Extend the filter pipeline with drug reference and sexual content detection signals, both derived from existing LRCLIB lyrics with no new dependencies, logged to the incident file, and visible in the dashboard.

- [ ] **Phase 9: TrackEvalResult Dataclass Refactor** — Replace positional 3-tuple return from ContentChecker.check() with a named frozen dataclass; no behavior change
- [ ] **Phase 10: Scanner Modules** — DrugScanner and SexualContentScanner as standalone pure functions with word-boundary regex matching; disjoint keyword sets
- [ ] **Phase 11: ContentChecker Pipeline Integration** — Wire both scanners into ContentChecker; drug and sexual detection trigger skip when FSM is active
- [ ] **Phase 12: Event Propagation & Incident Log** — Propagate drug_reference and sexual_content booleans through all daemon event emission and now_playing.json write paths
- [ ] **Phase 13: Dashboard Badge Variants** — CSS and JS for drug-reference and sexual-content badge variants in the skip feed

## Phase Details

### Phase 9: TrackEvalResult Dataclass Refactor
**Goal**: ContentChecker.check() returns a named dataclass so all callers access fields by name, not position
**Depends on**: Phase 8.1 (v1.2 complete)
**Requirements**: PIPE-01
**Success Criteria** (what must be TRUE):
  1. `ContentChecker.check()` returns a `TrackEvalResult` instance rather than a bare tuple on every code path
  2. All `daemon.py` call sites access result fields by attribute name (e.g., `result.action`) with no tuple unpacking
  3. All 10 test mocks construct `TrackEvalResult(...)` directly; zero bare-tuple return values remain in test fixtures
  4. Test suite passes green with identical skip/pass/pause behavior to v1.2 — no behavior change
**Plans**: 1 plan

Plans:
- [ ] 09-01-PLAN.md — Define TrackEvalResult dataclass; update content_checker.py, daemon.py, and test mocks

### Phase 10: Scanner Modules
**Goal**: DrugScanner and SexualContentScanner exist as independent, fully-tested pure functions ready for pipeline injection
**Depends on**: Phase 9
**Requirements**: DRUG-01, DRUG-02, SEXL-01, SEXL-02, SEXL-03
**Success Criteria** (what must be TRUE):
  1. `DrugScanner.scan(lyrics)` returns `(True, [matched_terms])` for lyrics containing unambiguous drug references and `(False, [])` for clean lyrics
  2. `SexualContentScanner.scan(lyrics)` returns `(True, [matched_terms])` for lyrics containing sexual content and `(False, [])` for clean lyrics
  3. Neither scanner produces false positives on known-clean songs ("High Hopes", "Here Comes the Sun", "Puff the Magic Dragon")
  4. A unit test asserts `SEXUAL_TERMS.isdisjoint(SEVERITY_MAP.keys())` — no term appears in both sets
  5. Both scanners match case-insensitively and respect word boundaries (no substring false positives)
**Plans**: TBD

### Phase 11: ContentChecker Pipeline Integration
**Goal**: Drug and sexual content detections trigger auto-skip alongside the existing explicit flag and profanity signals
**Depends on**: Phase 10
**Requirements**: DRUG-03, SEXL-04
**Success Criteria** (what must be TRUE):
  1. A track whose lyrics contain a drug reference is auto-skipped when Family Safe Mode is active
  2. A track whose lyrics contain sexual content is auto-skipped when Family Safe Mode is active
  3. Both scans run on every track with lyrics — detection does not short-circuit when profanity fires first
  4. `ContentChecker` integration tests cover all combinations: clean, profanity-only, drug-only, sexual-only, and multiple signals simultaneously
**Plans**: TBD
**UI hint**: no

### Phase 12: Event Propagation & Incident Log
**Goal**: Every eval_result event and skip_events.jsonl entry carries the complete four-signal record including drug_reference and sexual_content
**Depends on**: Phase 11
**Requirements**: LOG-01, LOG-02
**Success Criteria** (what must be TRUE):
  1. Every `eval_result` SSE event payload includes boolean fields `drug_reference` and `sexual_content` regardless of which code path fired
  2. Every entry written to `skip_events.jsonl` includes `explicit`, `profanity`, `drug_reference`, and `sexual_content` boolean fields
  3. Matched drug and sexual terms appear in Python log output at DEBUG level and are absent from `skip_events.jsonl`
  4. `now_playing.json` carries the same four boolean fields as the corresponding `eval_result` event — dashboard hydration on reload reflects the same data as the live SSE stream
**Plans**: TBD

### Phase 13: Dashboard Badge Variants
**Goal**: The skip feed shows visually distinct badge variants for drug-reference and sexual-content skip reasons
**Depends on**: Phase 12
**Requirements**: UI-01
**Success Criteria** (what must be TRUE):
  1. A skip caused by drug reference displays a distinct "Drug reference" badge in the skip feed (not a generic "Skipped" badge)
  2. A skip caused by sexual content displays a distinct "Sexual content" badge in the skip feed (not a generic "Skipped" badge)
  3. Existing badge variants (explicit, profanity, passed, mild language) render identically to v1.2 — no visual regression
  4. Dashboard loads without JS errors when the skip event log contains pre-v1.3 entries that lack `drug_reference` and `sexual_content` fields
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
| 6. Daemon SSE Extensions | v1.2 | 4/4 | Complete | 2026-04-03 |
| 7. Web UI Backend | v1.2 | 2/2 | Complete | 2026-04-03 |
| 8. Dashboard Frontend | v1.2 | 1/1 | Complete | 2026-04-03 |
| 8.1. Allow-reason Context | v1.2 | 2/2 | Complete | 2026-04-03 |
| 9. TrackEvalResult Dataclass Refactor | v1.3 | 0/1 | Not started | - |
| 10. Scanner Modules | v1.3 | 0/TBD | Not started | - |
| 11. ContentChecker Pipeline Integration | v1.3 | 0/TBD | Not started | - |
| 12. Event Propagation & Incident Log | v1.3 | 0/TBD | Not started | - |
| 13. Dashboard Badge Variants | v1.3 | 0/TBD | Not started | - |
