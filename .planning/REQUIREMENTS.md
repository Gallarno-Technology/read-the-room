# Requirements: Read the Room

**Defined:** 2026-04-08
**Milestone:** v1.7 — Cloud-Ready Architecture
**Core Value:** Songs that violate family-safe rules are skipped automatically before children hear them — with zero manual effort when Family Safe Mode is on.

## v1.7 Requirements

Refactor the daemon to expose four injectable seams. All seams default to current OSS
behavior — zero functional change for self-hosters. Cloud implementations live outside
this repo and plug in at startup.

### TrackCache

- [ ] **CACHE-01**: `TrackCache` abstract interface defined with `get(track_id)` and `put(track_id, data)` methods covering both lyrics and analysis results
- [ ] **CACHE-02**: `SQLiteTrackCache` implements `TrackCache` as the OSS default, consolidating existing SQLite lyrics cache and adding analysis result storage in the same DB
- [ ] **CACHE-03**: `ContentChecker` accepts an injected `TrackCache`; checks cache before running pipeline (cache hit skips full scan), writes result after pipeline completes
- [ ] **CACHE-04**: Daemon wires `SQLiteTrackCache` by default; passing `None` disables caching entirely

### EventEmitter

- [ ] **EMIT-01**: `EventEmitter` abstract interface defined with a single `emit(event: dict)` async method
- [ ] **EMIT-02**: `FileEventEmitter` implements `EventEmitter` — writes to `events.jsonl` and puts to SSE queue (current behavior, unchanged)
- [ ] **EMIT-03**: All `_append_event()` calls and `skip_event_queue.put_nowait()` calls in `daemon.py` replaced with a single `event_emitter.emit()` call
- [ ] **EMIT-04**: Daemon wires `FileEventEmitter` by default

### SkipExecutor

- [ ] **SKIP-01**: `SkipExecutor` abstract interface defined with `skip(track, device)` and `pause(device)` async methods
- [ ] **SKIP-02**: `DefaultSkipExecutor` implements `SkipExecutor` with existing Spotify-first → Sonos-fallback chain (current behavior, unchanged)
- [ ] **SKIP-03**: Daemon wires `DefaultSkipExecutor` by default; skip and pause calls routed through the injected executor

### AnalysisBackend

- [ ] **ANLYS-01**: `AnalysisBackend` abstract interface defined with `analyze(track: dict, result: TrackEvalResult)` async method
- [ ] **ANLYS-02**: `NoOpAnalysisBackend` implements `AnalysisBackend` (returns immediately, does nothing) — OSS default
- [ ] **ANLYS-03**: Daemon calls `analysis_backend.analyze()` after pipeline completes, non-blocking (fire-and-forget via `asyncio.create_task`); skip decision is never delayed by analysis
- [ ] **ANLYS-04**: Daemon wires `NoOpAnalysisBackend` by default

### Test Coverage

- [ ] **TEST-01**: Unit tests verify each default OSS implementation preserves current behavior (FileEventEmitter writes jsonl, SQLiteTrackCache round-trips lyrics and results, DefaultSkipExecutor follows Spotify→Sonos order, NoOpAnalysisBackend completes without side effects)
- [ ] **TEST-02**: Integration test verifies that injecting `None` or no-op implementations does not change daemon skip/allow outcomes

## v2+ Requirements

- Custom cloud implementations of all four seams (DynamoDB cache, SQS emitter, LLM analysis backend, Spotify-only executor) — lives outside OSS repo
- CommandReceiver seam for cloud → local Sonos command routing — deferred until cloud service is built
- Multi-tenant coroutine runner (N users per Fargate task) — deferred until scale demands it

## Out of Scope

| Feature | Reason |
|---------|--------|
| Sonos support in cloud daemon | Cloud daemon uses Spotify API only; Sonos is LAN-only |
| LLM inference code | Cloud-only feature; OSS repo exposes the seam (AnalysisBackend), not the implementation |
| Cloud infrastructure (DynamoDB, SQS, Lambda) | Outside this repo entirely |
| New user-facing features | Pure refactor milestone — no UI or behavioral changes |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| CACHE-01 | Phase 23 | Pending |
| CACHE-02 | Phase 23 | Pending |
| CACHE-03 | Phase 23 | Pending |
| CACHE-04 | Phase 23 | Pending |
| EMIT-01 | Phase 24 | Pending |
| EMIT-02 | Phase 24 | Pending |
| EMIT-03 | Phase 24 | Pending |
| EMIT-04 | Phase 24 | Pending |
| SKIP-01 | Phase 25 | Pending |
| SKIP-02 | Phase 25 | Pending |
| SKIP-03 | Phase 25 | Pending |
| ANLYS-01 | Phase 26 | Pending |
| ANLYS-02 | Phase 26 | Pending |
| ANLYS-03 | Phase 26 | Pending |
| ANLYS-04 | Phase 26 | Pending |
| TEST-01 | Phase 23–26 | Pending |
| TEST-02 | Phase 26 | Pending |

**Coverage:**
- v1.7 requirements: 17 total
- Mapped to phases: 17
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-08*
*Last updated: 2026-04-11 after v1.7 milestone start*
