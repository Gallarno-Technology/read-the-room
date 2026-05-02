---
phase: 32-frontend-id-persistence
plan: "02"
subsystem: web_ui
tags: [login-gate, fastapi, httponly-cookie, redirect, tdd-green]
dependency_graph:
  requires:
    - phase: 32-01
      provides: test-scaffolds for login gate routing and login.html template
  provides:
    - GET / redirects unauthenticated browsers to /login (302)
    - GET /login serves login.html HTMLResponse
    - POST /login validates uid, sets httpOnly cookie, returns ok flag
    - LoginRequest Pydantic model
  affects: [web_ui/main.py, tests/test_web_ui_endpoints.py]
tech_stack:
  added: []
  patterns:
    - "response_model=None on routes returning HTMLResponse | RedirectResponse union type"
    - "Manual cookie-check redirect pattern replacing Depends(get_user_context) for HTML routes"
    - "POST /login HTTP 200 for both success and error paths (gate JS reads body without 4xx handling)"
key_files:
  created: []
  modified:
    - web_ui/main.py
    - tests/test_web_ui_endpoints.py
key_decisions:
  - "response_model=None required on GET / decorator when return type is HTMLResponse | RedirectResponse — FastAPI cannot generate Pydantic response field from union of Response subclasses (auth_callback uses same pattern)"
  - "LoginRequest model placed in Pydantic models block before routes section to avoid NameError at function definition time"
  - "test_dashboard_injects_profile_initial updated to patch _registry and send uid cookie — client fixture's get_user_context override no longer applies to GET / after D-02 (auto-fix Rule 1)"
  - "Pydantic models (FSMRequest, ProfileRequest, LoginRequest) consolidated before routes section for clarity"
requirements-completed: [UI-01, UI-02, UI-03, UI-04]
duration: "11min"
completed: "2026-05-02"
---

# Phase 32 Plan 02: GREEN Phase — Login Gate Implementation Summary

**FastAPI login gate with 302 redirect on GET /, GET /login serving login.html, and POST /login validating uid via UserRegistry and setting httpOnly cookie with 30-day max_age**

## Performance

- **Duration:** ~11 min
- **Started:** 2026-05-02T03:32:54Z
- **Completed:** 2026-05-02T03:35:43Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- GET / refactored to manual cookie-check redirect: no cookie or unknown/pending uid → 302 to /login; valid active uid → serves dashboard HTML as before
- GET /login added: reads login.html from templates dir, returns HTMLResponse always (no redirect-if-authed per D-04)
- POST /login added: validates uid against UserRegistry, sets httpOnly+SameSite=Lax+Secure+30d cookie on success, returns {ok: false, error: "Unknown access code"} at HTTP 200 on failure
- All 48 tests in test_web_ui_endpoints.py pass GREEN including all 7 new Phase 32 tests
- All API routes (/fsm, /skip, /events, /now-playing, /profile, /feed) retain Depends(get_user_context) and continue returning 401 (D-03)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add LoginRequest model and refactor GET / with cookie-check redirect** - `361e756` (feat)
2. **Task 2: Add GET /login and POST /login handlers; fix dashboard test** - `73c6368` (feat)

**Plan metadata:** committed with docs commit below

## Files Created/Modified
- `web_ui/main.py` - Pydantic models consolidated before routes; GET / refactored (D-02); GET /login and POST /login added (D-04, D-07)
- `tests/test_web_ui_endpoints.py` - test_dashboard_injects_profile_initial updated to use _registry patch + uid cookie (Rule 1 auto-fix)

## Decisions Made
- Used `response_model=None` on `GET /` decorator — required when return type annotation is `HTMLResponse | RedirectResponse`; identical to existing `auth_callback` route pattern.
- Moved all Pydantic models (FSMRequest, ProfileRequest, LoginRequest) into a single block before the routes section to ensure `LoginRequest` is defined before `POST /login` function body is processed at import time.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Added response_model=None to GET / decorator**
- **Found during:** Task 1 (GET / refactor)
- **Issue:** FastAPI raises `FastAPIError: Invalid args for response field!` when return type annotation includes `RedirectResponse` without `response_model=None`. The union `HTMLResponse | RedirectResponse` cannot be used as a Pydantic field.
- **Fix:** Added `response_model=None` to `@app.get("/", response_class=HTMLResponse, response_model=None)` — same pattern already used on `auth_callback`.
- **Files modified:** web_ui/main.py
- **Verification:** `uv run python -m pytest tests/test_web_ui_endpoints.py -x -q` exits 0
- **Committed in:** 361e756 (Task 1 commit)

**2. [Rule 1 - Bug] Updated test_dashboard_injects_profile_initial to work with D-02**
- **Found during:** Task 2 (full suite run)
- **Issue:** `test_dashboard_injects_profile_initial` used the `client` fixture which overrides `get_user_context`. After D-02, GET / no longer calls `get_user_context` — it reads the uid cookie directly. The `client` fixture sends no uid cookie, so GET / redirects to /login (302 → follow → login.html served). Test received login.html content instead of index.html with profile injection.
- **Fix:** Updated test to drop `client` fixture dependency, instead patching `_registry.load` and `_registry.user_paths` with the mock user data, and sending `cookies={"uid": uid}` to the TestClient. Pattern mirrors `test_valid_uid_cookie_serves_dashboard`.
- **Files modified:** tests/test_web_ui_endpoints.py
- **Verification:** `uv run python -m pytest tests/test_web_ui_endpoints.py::test_dashboard_injects_profile_initial -v` exits 0
- **Committed in:** 73c6368 (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (2 Rule 1 bugs)
**Impact on plan:** Both auto-fixes necessary for correctness. The `response_model=None` fix is a known FastAPI constraint (same as auth_callback). The test update was the expected consequence of removing `get_user_context` dependency from GET /.

## Issues Encountered

Pre-existing test failures in other test files (not caused by Phase 32):
- `tests/test_info_icon.py::test_info_profile_map_present` — PROFILE_INFO constant missing from index.html (pre-existing, confirmed via git stash)
- `tests/test_sexual_content_scanner.py::test_sexual_terms_disjoint_from_severity_map` — pre-existing
- `tests/test_skip_client.py::test_soco_pause_*` (2 tests) — pre-existing

All 4 pre-existing failures are out of scope for Phase 32. All Phase 32 tests (48 in test_web_ui_endpoints.py) pass GREEN.

## Known Stubs

None. GET / serves real dashboard HTML with state injection from user's state.json. GET /login serves the fully-implemented login.html from Plan 01. POST /login validates against the real UserRegistry. No placeholder data or hardcoded values in rendering paths.

## Threat Surface Scan

POST /login is a new network endpoint at the auth trust boundary. This is covered in the plan's threat model:
- T-32-06: uid cookie forged — mitigated by _registry.load() validation + status == "active" check
- T-32-07: POST /login body injection — mitigated by Pydantic LoginRequest model + 422 on malformed body
- T-32-08: CSRF on POST /login — accepted; JSON Content-Type + SameSite=Lax sufficient for 5-user beta
- T-32-09: uid cookie interception — mitigated by secure=True + httponly=True
- T-32-10: pending uid escalation — mitigated by status != "active" guard

No new threat surface beyond what the plan's threat model covers.

## Next Phase Readiness

Phase 32 is complete. The login gate is fully operational:
- Browser visit with no cookie → redirected to /login gate page
- User enters uid → POST /login validates and sets cookie → redirected to dashboard
- OAuth callback flow (Phase 29) already sets the cookie — GET / with valid cookie serves dashboard directly (UI-04 satisfied without changes)
- All Phase 32 requirements (UI-01, UI-02, UI-03, UI-04) are satisfied

## Self-Check

### Files Created/Modified
- [x] FOUND: web_ui/main.py
- [x] FOUND: tests/test_web_ui_endpoints.py
- [x] FOUND: .planning/phases/32-frontend-id-persistence/32-02-SUMMARY.md

### Commits
- [x] FOUND: 361e756 — feat(32-02): add LoginRequest model and refactor GET / with cookie-check redirect
- [x] FOUND: 73c6368 — feat(32-02): add GET /login and POST /login handlers; fix dashboard test

### Test Verification
- [x] 48 passed, 0 failed in tests/test_web_ui_endpoints.py

## Self-Check: PASSED

---
*Phase: 32-frontend-id-persistence*
*Completed: 2026-05-02*
