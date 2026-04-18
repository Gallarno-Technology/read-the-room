---
phase: 28-cookie-routing-per-user-sse
plan: 01
subsystem: api
tags: [fastapi, cookie, routing, per-user, sse, user-registry, depends]

# Dependency graph
requires:
  - phase: 27-user-registry-operator-cli
    provides: UserRegistry class with user_paths() for uid validation and path resolution
provides:
  - UserContext dataclass with per-user file path fields
  - get_user_context FastAPI Depends resolving uid cookie to UserContext
  - All non-SSE routes wired with per-user path resolution
  - 401 JSON on missing/unknown/pending uid cookie across all routes
  - Per-uid SSE tail infrastructure (lazy start, immediate teardown)
affects: [28-02, phase-29-oauth-callback, phase-32-frontend-id-gate]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "FastAPI Depends for cookie-based auth: get_user_context reads uid cookie, validates via UserRegistry, returns UserContext"
    - "dependency_overrides in tests: replace get_user_context with lambda returning mock UserContext"
    - "Per-uid SSE tails: _tails dict[str, Task] + _subscribers dict[str, list[Queue]] for fan-out"

key-files:
  created: []
  modified:
    - web_ui/main.py
    - tests/test_web_ui_endpoints.py
    - tests/test_feed_endpoint.py

key-decisions:
  - "get_user_context raises HTTPException(401) directly — cleaner than returning None for FastAPI dependency chain"
  - "pending uid status treated same as unknown — 401 (D-02): cookie should not be set until OAuth complete"
  - "Lazy tail start (D-06): first /events connection for uid triggers asyncio.create_task; no startup hook needed"
  - "Immediate tail teardown (D-07): last subscriber leaving cancels tail task; hydrateFeed() on reconnect recovers gap events"
  - "Rule 1 auto-fix: test_feed_endpoint.py updated to mock_ctx fixture pattern — broken by EVENTS_PATH global removal"

patterns-established:
  - "UserContext injection: ctx: UserContext = Depends(get_user_context) in every route signature"
  - "Test pattern: dependency_overrides[get_user_context] = lambda: mock_ctx replaces monkeypatch.setattr for path globals"

requirements-completed: [ROUTE-01]

# Metrics
duration: 10min
completed: 2026-04-18
---

# Phase 28 Plan 01: Cookie Routing Per-User SSE Summary

**Per-user path isolation via uid cookie: UserContext dataclass + get_user_context Depends wired to all 9 non-SSE routes with 401 enforcement and per-uid SSE tail infrastructure**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-04-18T19:43:00Z
- **Completed:** 2026-04-18T19:53:13Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Replaced all module-level path globals (STATE_PATH, EVENTS_PATH, NOW_PLAYING_PATH) with per-request UserContext (D-09)
- Added UserContext dataclass and get_user_context Depends; all 9 non-SSE routes return 401 on missing/unknown/pending uid cookie
- Rebuilt SSE infrastructure from a single global _subscribers list to per-uid _tails + _subscribers dicts with lazy start and immediate teardown

## Task Commits

1. **Task 1: Add UserContext dataclass and get_user_context Depends** - `883ca44` (feat)
2. **Task 2: Update tests for per-user routing** - `30886d7` (feat)

## Files Created/Modified

- `web_ui/main.py` - UserContext dataclass, get_user_context Depends, per-uid SSE tail infrastructure, all route handlers updated
- `tests/test_web_ui_endpoints.py` - Rewritten with mock_ctx fixture, unauthed_client fixture, 401 parametrized tests
- `tests/test_feed_endpoint.py` - Updated to mock_ctx fixture pattern (Rule 1 auto-fix)

## Decisions Made

- `get_user_context` raises `HTTPException(401)` directly — cleaner than returning None in FastAPI Depends chain
- Pending uid treated as unknown (returns 401) — D-02: cookie should not be set until Phase 29 OAuth completes
- SSE tail starts lazily on first `/events` connection per uid; cancelled immediately when last subscriber disconnects

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] test_feed_endpoint.py broken by EVENTS_PATH global removal**
- **Found during:** Task 2 (full suite run after Task 1)
- **Issue:** `test_feed_endpoint.py` used `monkeypatch.setattr(web_ui_main, "EVENTS_PATH", ...)` — attribute no longer exists after global removal
- **Fix:** Rewrote `test_feed_endpoint.py` to use `mock_ctx` fixture and `dependency_overrides` pattern matching the new test architecture
- **Files modified:** `tests/test_feed_endpoint.py`
- **Verification:** All 5 feed tests pass; full suite 143 passed (up from 133)
- **Committed in:** `30886d7` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug)
**Impact on plan:** Required fix — test_feed_endpoint.py was directly broken by the global removal that is the core of this plan. No scope creep.

## Issues Encountered

Pre-existing failures in `test_info_icon.py`, `test_sexual_content_scanner.py`, and `test_skip_client.py` (4 tests) exist before this plan and are unrelated to these changes. Logged to deferred-items tracking.

## Next Phase Readiness

- Plan 28-01 complete: UserContext + get_user_context + per-uid SSE infrastructure in place
- Plan 28-02 (SSE per-user routing) can now add `/events` per-user tail tests and verify teardown behavior
- Phase 29 (OAuth callback) can write uid cookie after token; Phase 32 (frontend ID gate) can redirect 401 at GET /

---
*Phase: 28-cookie-routing-per-user-sse*
*Completed: 2026-04-18*
