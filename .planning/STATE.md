---
gsd_state_version: 1.0
milestone: v1.8
milestone_name: Multi-User Beta
status: complete
stopped_at: v1.8 milestone closed 2026-05-03
last_updated: "2026-05-03T00:00:00Z"
last_activity: 2026-05-03
progress:
  total_phases: 6
  completed_phases: 6
  total_plans: 13
  completed_plans: 13
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-03)

**Core value:** Songs that violate family-safe rules are skipped automatically before children hear them — with zero manual effort when Family Safe Mode is on.
**Current focus:** Planning next milestone

## Current Position

Phase: v1.8 complete
Plan: All 13 plans complete
Status: Milestone closed 2026-05-03
Last activity: 2026-05-03

Progress: [██████████] 100%

## Deferred Items

Items acknowledged and deferred at milestone close on 2026-05-03:

| Category | Item | Status |
|----------|------|--------|
| debug | daemon-clobbers-state-json | investigating (stale — fixed in Phase 1) |
| debug | lyrics-pipeline-not-active | awaiting_human_verify (stale — fixed in Phase 2) |
| debug | sonos-not-detected | investigating (stale — fixed in Phases 3-4) |

## Performance Metrics

**Velocity:**

- Total plans completed: 46 (v1.0–v1.8 partial)
- Average duration: ~3 min
- Total execution time: ~133 min

**By Phase (recent):**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| Phase 17-rebrand | 1 | 2 tasks | 2 files |
| Phase 18-profile-info-icon | 1 | 5 tasks | 4 files |
| Phase 19-mobile-polish | 1 | 2 tasks | 2 files |
| Phase 20-repository-hygiene P01 | 3 | 2 tasks | 2 files |
| Phase 20-repository-hygiene P02 | 8 | 3 tasks | 9 files |
| Phase 21-legal-docs P01 | 2 | 2 tasks | 2 files |
| 23 | 2 | - | - |
| Phase 27-user-registry-operator-cli P01 | 2 | 2 tasks | 2 files |
| Phase 27-user-registry-operator-cli P02 | 2 | 2 tasks | 3 files |
| Phase 28 P01 | 10 | 2 tasks | 3 files |
| Phase 28-cookie-routing-per-user-sse P02 | 6 | 2 tasks | 1 files |
| Phase 29-oauth-onboarding-flow P01 | 2 | 2 tasks | 2 files |
| Phase 30-per-user-daemon-management P01 | 2 | 2 tasks | 3 files |
| Phase 30-per-user-daemon-management P02 | 2 | 2 tasks | 1 files |
| Phase 30-per-user-daemon-management P03 | 2 | 2 tasks | 2 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.

Recent decisions affecting current work:

- [Phase 19]: touch-action: manipulation on button/.profile-option only — iOS Safari scroll jank prevention
- [v1.6 Research]: `.planning/` and `.claude/` must be removed from git tracking before repo goes public (530 files with absolute home paths)
- [v1.6 Research]: CI needs dummy Spotify env vars — test suite is fully mocked but modules import spotipy at load time
- [v1.6 Research]: Phase 20 (Hygiene) is a hard gate — no other v1.6 phase begins before hygiene is clean
- [Phase 20-repository-hygiene]: Edit .gitignore before git rm --cached to close re-tracking window (per RESEARCH.md Pitfall 3)
- [Phase 20-repository-hygiene]: Replace personal IP 192.168.1.164 with 192.168.1.100 in test fixtures; module docstrings drop phase numbers during brand rename; snake_case family_safe_mode key preserved per D-04
- [Phase 21-legal-docs]: LICENSE is proprietary all-rights-reserved single-line notice for Gallarno Technology LLC (not MIT — task action was authoritative over objective description)
- [v1.8 Research]: Spotify dev mode user cap dropped from 25 to 5 in March 2026 — scope revised accordingly; gate CLI at 5 users
- [v1.8 Roadmap]: Cookie-based uid routing (httpOnly) chosen over path-param routing per REQUIREMENTS.md; uid travels through OAuth `state` parameter to prevent callback collisions
- [v1.8 Roadmap]: asyncio.create_subprocess_exec (stdlib) chosen for daemon supervision — resolve supervisord vs. asyncio open decision at Phase 30 planning
- [v1.8 Roadmap]: lyrics_cache.db shared across all users (keyed by Spotify track ID) — ISOL-03
- [Phase 27-user-registry-operator-cli]: UserRegistry(base_dir) pattern for testability — no hardcoded project root paths
- [Phase 27-user-registry-operator-cli]: lyrics_cache.db stays at project root (ISOL-03) — shared across users, NOT inside users/{uid}/
- [Phase 27-user-registry-operator-cli P02]: SpotifyOAuth state=uid bakes uid into OAuth URL state param — callback in Phase 29 reads it back; CacheFileHandler uses placeholder path overwritten by Phase 29
- [Phase 28]: get_user_context raises HTTPException(401) directly for FastAPI Depends; pending uid treated same as unknown (D-02)
- [Phase 28]: SSE tail starts lazily on first /events connection; cancelled immediately when last subscriber disconnects (D-06, D-07)
- [Phase 28]: Task 1 (per-uid SSE infrastructure) was pre-implemented in Phase 28-01 — SSE tests added in 28-02 to complete ROUTE-02 verification
- [Phase 29-01]: activate(uid) does not check if status is already 'active' — method sets status unconditionally for any found uid; D-04 validation happens at callback level in Plan 02
- [Phase 30-01]: Test _stop_daemon_via_pid directly (not via cmd_remove) for cleaner isolation; ImportError at test runtime (not collection) ensures FAILED not ERROR
- [Phase 30-01]: asyncio.run() drives supervisor coroutines from synchronous test functions — matches existing pattern for pure-async coroutines not needing TestClient
- [Phase 30-02]: lifespan context manager defined before app = FastAPI() — Python resolves function-body names at call time, not definition time; _registry/_spawn_daemon/_supervisor_for_uid available at startup despite appearing later in file
- [Phase 30-02]: Supervisor tasks cancelled on FastAPI shutdown to prevent asyncio "pending task destroyed" warnings in test teardown
- [Phase 30-03]: import sys added to daemon.py — was absent despite being needed for sys.exit(2) in 401 counter
- [Phase 30-03]: _stop_daemon_via_pid uses time.monotonic() deadline while-loop (not for-range) to be compatible with test patching of time.monotonic

### Pending Todos

None.

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260419-p21 | Add a list to manage_users.py that lists registered users and state | 2026-04-19 | 4c885fe | [260419-p21-add-a-list-to-manage-users-py-that-lists](.planning/quick/260419-p21-add-a-list-to-manage-users-py-that-lists/) |
| 260419-qh7 | Add Caddy reverse proxy with self-signed HTTPS for 192.168.1.220 | 2026-04-19 | 8588cb7 | [260419-qh7-add-caddy-reverse-proxy-with-self-signed](.planning/quick/260419-qh7-add-caddy-reverse-proxy-with-self-signed/) |

### Blockers/Concerns

None — v1.8 complete.

## Session Continuity

Last session: 2026-05-03
Stopped at: v1.8 milestone closed — all 6 phases, 13 plans complete
Resume: Run /gsd-new-milestone to start v1.9 or v2.0
