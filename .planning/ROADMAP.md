# Roadmap: Spotify Family Safe Mode

## Milestones

- ✅ **v1.0 MVP** — Phases 1-3 (shipped 2026-04-02)
- ✅ **v1.1 Deployment** — Phases 4-5 (shipped 2026-04-02)
- 📋 **v1.2 Now Playing Status** — Phases TBD (planned)
- 🚧 **v1.3 Drug & Sexual Reference Detection** — Phases 6-10 (in progress)

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

### 📋 v1.2 Now Playing Status (Planned)

**Milestone Goal:** Dashboard shows the current track with its real-time filter evaluation state and a manual skip button, so parents can see what's playing and act on it without opening Spotify.

*Phases not yet defined — run `/gsd:new-milestone` to plan this milestone.*

### 🚧 v1.3 Drug & Sexual Reference Detection (In Progress)

**Milestone Goal:** Extend the filter pipeline with drug reference and sexual content detection signals, both derived from existing LRCLIB lyrics with no new dependencies, logged to the incident file, and visible in the dashboard.

- [ ] **Phase 6: Return Type Refactor** — Replace ContentChecker.check() 3-tuple with TrackEvalResult dataclass
- [ ] **Phase 7: Drug Scanner** — DrugScanner class with conservative phrase list, word-boundary regex, unit tests
- [ ] **Phase 8: Sexual Content Scanner** — SexualContentScanner, SEVERITY_MAP deduplication, unit tests
- [ ] **Phase 9: ContentChecker Integration + Incident Log** — Wire both scanners in; extend skip_events.jsonl with all four signal booleans
- [ ] **Phase 10: Dashboard + End-to-End Validation** — New reason badges in web UI; integration tests covering all signal combinations

## Phase Details

### Phase 6: Return Type Refactor
**Goal**: ContentChecker.check() returns a named TrackEvalResult dataclass so all subsequent signal additions and daemon call sites use attribute access instead of positional tuple unpacking
**Depends on**: Phase 5
**Requirements**: PIPE-01
**Success Criteria** (what must be TRUE):
  1. `ContentChecker.check()` returns a `TrackEvalResult` dataclass instance, not a 3-tuple
  2. `daemon.py` call sites access result fields by name (e.g., `result.should_skip`) with no positional unpack
  3. All existing tests pass without modification to test logic — only import/attribute references updated
**Plans**: TBD

### Phase 7: Drug Scanner
**Goal**: A standalone DrugScanner class exists with a conservative curated phrase list, word-boundary regex matching, and unit tests that verify false-positive candidates do not trigger
**Depends on**: Phase 6
**Requirements**: DRUG-01, DRUG-02
**Success Criteria** (what must be TRUE):
  1. `DrugScanner.scan(lyrics)` returns `(bool, list[str])` — the boolean and the list of matched terms
  2. Known false-positive candidates ("highway", "grasshopper", "joint venture") do not trigger the scanner
  3. Known drug phrases from the curated list are detected correctly with word-boundary isolation
  4. The drug term list contains 80 entries or fewer (CI-enforceable gate)
**Plans**: TBD

### Phase 8: Sexual Content Scanner
**Goal**: A standalone SexualContentScanner class exists with a curated list that has zero overlap with existing profanity SEVERITY_MAP terms, and unit tests that verify both detection and deduplication
**Depends on**: Phase 6
**Requirements**: SEXL-01, SEXL-02, SEXL-03
**Success Criteria** (what must be TRUE):
  1. `SexualContentScanner.scan(lyrics)` returns `(bool, list[str])` with the matched terms alongside the boolean
  2. An assertion test confirms `set(SEXUAL_TERMS) & set(SEVERITY_MAP.keys()) == set()` — no overlap with profanity list
  3. Known sexual content phrases are detected with word-boundary isolation
  4. Terms already in `SEVERITY_MAP` (e.g., "cock", "pussy") do not appear in the sexual content list and do not double-fire
**Plans**: TBD

### Phase 9: ContentChecker Integration + Incident Log
**Goal**: Both new scanners are wired into ContentChecker; skip is triggered on drug or sexual detection when FSM is active; skip_events.jsonl payloads include all four signal booleans
**Depends on**: Phase 7, Phase 8
**Requirements**: DRUG-03, SEXL-04, LOG-01
**Success Criteria** (what must be TRUE):
  1. A track with drug reference lyrics is skipped automatically when Family Safe Mode is on
  2. A track with sexual content lyrics is skipped automatically when Family Safe Mode is on
  3. Every skip event written to `skip_events.jsonl` includes `explicit`, `profanity`, `drug_reference`, and `sexual_content` boolean fields
  4. No new columns are added to the `lyrics_cache` SQLite table (detection is in-memory only)
**Plans**: TBD

### Phase 10: Dashboard + End-to-End Validation
**Goal**: The web dashboard displays distinct skip reason badges for drug reference and sexual content; integration tests confirm all four signal combinations produce correct skip behavior end-to-end
**Depends on**: Phase 9
**Requirements**: UI-01
**Success Criteria** (what must be TRUE):
  1. The skip feed in the dashboard shows a distinct "Drug Reference" badge when a track is skipped for that reason
  2. The skip feed shows a distinct "Sexual Content" badge when a track is skipped for that reason
  3. Integration tests pass for all signal combinations: drug only, sexual only, both simultaneously, neither, profanity + drug simultaneously
  4. The 5-consecutive-skip pause logic counts drug and sexual content skips correctly alongside existing skip types
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
| 6. Return Type Refactor | v1.3 | 0/? | Not started | - |
| 7. Drug Scanner | v1.3 | 0/? | Not started | - |
| 8. Sexual Content Scanner | v1.3 | 0/? | Not started | - |
| 9. ContentChecker Integration + Incident Log | v1.3 | 0/? | Not started | - |
| 10. Dashboard + End-to-End Validation | v1.3 | 0/? | Not started | - |
