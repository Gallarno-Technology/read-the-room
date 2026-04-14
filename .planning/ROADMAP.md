# Roadmap: Read the Room

## Milestones

- ✅ **v1.0 MVP** — Phases 1-3 (shipped 2026-04-02)
- ✅ **v1.1 Deployment** — Phases 4-5 (shipped 2026-04-02)
- ✅ **v1.2 Now Playing Status** — Phases 6-8.1 (shipped 2026-04-03)
- ✅ **v1.3 Drug & Sexual Reference Detection** — Phases 9-13 (shipped 2026-04-04)
- ✅ **v1.4 Dashboard Polish & Filter Profiles** — Phases 14-16 (shipped 2026-04-05)
- ✅ **v1.5 Dashboard Polish & Mobile UX** — Phases 17-19 (shipped 2026-04-06)
- ✅ **v1.6 Open Source** — Phases 20-22 (shipped 2026-04-11)
- 🚧 **v1.7 Cloud-Ready Architecture** — Phases 23-26 (in progress)

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

<details>
<summary>✅ v1.5 Dashboard Polish & Mobile UX (Phases 17-19) — SHIPPED 2026-04-06</summary>

- [x] Phase 17: Rebrand (1/1 plan) — completed 2026-04-06
- [x] Phase 18: Profile Info Icon (1/1 plan) — completed 2026-04-06
- [x] Phase 19: Mobile Polish (1/1 plan) — completed 2026-04-06

</details>

<details>
<summary>✅ v1.6 Open Source (Phases 20-22) — SHIPPED 2026-04-11</summary>

- [x] Phase 20: Repository Hygiene (2/2 plans) — completed 2026-04-08
- [x] Phase 21: Legal & Docs (2/2 plans) — completed 2026-04-10
- [x] Phase 22: CI & Tooling (3/3 plans) — completed 2026-04-11

</details>

### 🚧 v1.7 Cloud-Ready Architecture (In Progress)

**Milestone Goal:** Refactor the daemon to expose four injectable seams — preserving identical OSS behavior while making it possible to plug in cloud implementations at startup.

- [ ] **Phase 23: TrackCache Seam** — Abstract cache interface + SQLite default; ContentChecker wired to use it
- [ ] **Phase 24: EventEmitter Seam** — Abstract emit interface + FileEventEmitter default; all daemon emit calls routed through it
- [ ] **Phase 25: SkipExecutor Seam** — Abstract skip/pause interface + DefaultSkipExecutor; daemon skip/pause calls routed through it
- [ ] **Phase 26: AnalysisBackend Seam** — Abstract analysis interface + NoOp default; fire-and-forget post-pipeline hook in daemon

## Phase Details

### Phase 23: TrackCache Seam
**Goal**: ContentChecker uses an injected cache so lyrics and analysis results can be stored and retrieved through a swappable backend
**Depends on**: Phase 22
**Requirements**: CACHE-01, CACHE-02, CACHE-03, CACHE-04, TEST-01 (TrackCache unit tests)
**Success Criteria** (what must be TRUE):
  1. `TrackCache` abstract interface exists with `get(track_id)` and `put(track_id, data)` methods
  2. `SQLiteTrackCache` stores and retrieves both lyrics and analysis results from the existing SQLite DB
  3. `ContentChecker` skips the full scan pipeline on a cache hit and writes the result after a cache miss
  4. Daemon wires `SQLiteTrackCache` by default; passing `None` disables caching with no errors
  5. Unit tests confirm SQLiteTrackCache round-trips lyrics and analysis results correctly
**Plans:** 2 plans

Plans:
- [ ] 23-01-PLAN.md — TrackCache ABC + SQLiteTrackCache + unit tests (track_cache.py, tests/test_track_cache.py)
- [ ] 23-02-PLAN.md — Wire ContentChecker and daemon.py (content_checker.py, daemon.py, tests/test_content_checker.py)

### Phase 24: EventEmitter Seam
**Goal**: All daemon event emission routes through a single injected `EventEmitter`, replacing scattered direct writes and queue calls
**Depends on**: Phase 23
**Requirements**: EMIT-01, EMIT-02, EMIT-03, EMIT-04, TEST-01 (FileEventEmitter unit tests)
**Success Criteria** (what must be TRUE):
  1. `EventEmitter` abstract interface exists with a single `emit(event: dict)` async method
  2. `FileEventEmitter` writes to `events.jsonl` and puts to the SSE queue — identical to current behavior
  3. No direct `_append_event()` or `skip_event_queue.put_nowait()` calls remain in `daemon.py`; all replaced by `event_emitter.emit()`
  4. Daemon wires `FileEventEmitter` by default; OSS runtime behavior is unchanged
  5. Unit tests confirm FileEventEmitter produces correct jsonl output and SSE queue entries
**Plans**: TBD

### Phase 25: SkipExecutor Seam
**Goal**: Skip and pause operations are routed through an injected `SkipExecutor`, formalizing the existing Spotify-first → Sonos-fallback chain
**Depends on**: Phase 24
**Requirements**: SKIP-01, SKIP-02, SKIP-03, TEST-01 (DefaultSkipExecutor unit tests)
**Success Criteria** (what must be TRUE):
  1. `SkipExecutor` abstract interface exists with `skip(track, device)` and `pause(device)` async methods
  2. `DefaultSkipExecutor` implements the existing Spotify-first → Sonos-fallback skip logic unchanged
  3. All skip and pause calls in `daemon.py` route through the injected executor; no direct SoCo or Spotify API calls remain outside it
  4. Daemon wires `DefaultSkipExecutor` by default; skips and pauses behave identically to pre-refactor
  5. Unit tests confirm DefaultSkipExecutor follows Spotify → Sonos order correctly
**Plans**: TBD

### Phase 26: AnalysisBackend Seam
**Goal**: Daemon calls a post-pipeline analysis hook as a fire-and-forget task; the OSS default is a no-op that leaves skip timing untouched
**Depends on**: Phase 25
**Requirements**: ANLYS-01, ANLYS-02, ANLYS-03, ANLYS-04, TEST-01 (NoOpAnalysisBackend unit tests), TEST-02
**Success Criteria** (what must be TRUE):
  1. `AnalysisBackend` abstract interface exists with `analyze(track: dict, result: TrackEvalResult)` async method
  2. `NoOpAnalysisBackend` completes immediately with no side effects
  3. Daemon calls `analysis_backend.analyze()` via `asyncio.create_task` after pipeline completes; skip decision is never delayed
  4. Daemon wires `NoOpAnalysisBackend` by default; skip/allow outcomes are identical to pre-refactor
  5. Integration test confirms that injecting `None` or no-op implementations does not change daemon skip/allow outcomes
**Plans**: TBD

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
| 17. Rebrand | v1.5 | 1/1 | Complete | 2026-04-06 |
| 18. Profile Info Icon | v1.5 | 1/1 | Complete | 2026-04-06 |
| 19. Mobile Polish | v1.5 | 1/1 | Complete | 2026-04-06 |
| 20. Repository Hygiene | v1.6 | 2/2 | Complete | 2026-04-08 |
| 21. Legal & Docs | v1.6 | 2/2 | Complete | 2026-04-10 |
| 22. CI & Tooling | v1.6 | 3/3 | Complete | 2026-04-11 |
| 23. TrackCache Seam | v1.7 | 0/2 | In progress | - |
| 24. EventEmitter Seam | v1.7 | 0/? | Not started | - |
| 25. SkipExecutor Seam | v1.7 | 0/? | Not started | - |
| 26. AnalysisBackend Seam | v1.7 | 0/? | Not started | - |
