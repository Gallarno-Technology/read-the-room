---
gsd_state_version: 1.0
milestone: v1.6
milestone_name: Open Source
status: completed
stopped_at: Completed 27-02-PLAN.md (manage_users.py operator CLI)
last_updated: "2026-04-17T02:27:48.437Z"
last_activity: 2026-04-17
progress:
  total_phases: 12
  completed_phases: 1
  total_plans: 2
  completed_plans: 2
  percent: 33
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-16)

**Core value:** Songs that violate family-safe rules are skipped automatically before children hear them — with zero manual effort when Family Safe Mode is on.
**Current focus:** Phase 27 — User Registry + Operator CLI (COMPLETE)

## Current Position

Phase: 28
Plan: Not started
Status: Complete
Last activity: 2026-04-17

Progress: [██░░░░░░░░] 33%

## Performance Metrics

**Velocity:**

- Total plans completed: 45 (v1.0–v1.8 partial)
- Average duration: ~3 min
- Total execution time: ~129 min

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

### Pending Todos

None.

### Blockers/Concerns

- spotipy CacheFileHandler has no file locking — daemon must own token refresh; web_ui spotipy must not trigger refreshes (Phase 29 pitfall).
- OAuth callback race requires `state` → uid binding with a pending-auth map and one active onboarding flow at a time (Phase 29 pitfall).

## Session Continuity

Last session: 2026-04-17T02:22:00.000Z
Stopped at: Completed 27-02-PLAN.md (manage_users.py operator CLI)
Resume file: None
