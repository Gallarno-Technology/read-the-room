---
phase: 16-filter-profiles
plan: "02"
subsystem: web_ui
tags: [api, profile, tdd, fastapi, state]
dependency_graph:
  requires: [16-01]
  provides: [POST /profile endpoint, GET /profile endpoint, __PROFILE_INITIAL__ injection]
  affects: [web_ui/main.py, web_ui/templates/index.html]
tech_stack:
  added: []
  patterns: [read-merge-write state, FSMRequest pattern mirroring, TDD red-green]
key_files:
  created: []
  modified:
    - web_ui/main.py
    - web_ui/templates/index.html
    - tests/test_web_ui_endpoints.py
    - tests/test_feed_endpoint.py
decisions:
  - VALID_PROFILES frozenset uses 4 named presets: kids_present, were_all_adults, above_the_covers, permissive
  - POST /profile mirrors FSMRequest pattern exactly (read-merge-write, 400 for invalid key)
  - __PROFILE_INITIAL__ placeholder added to index.html in this plan (not deferred to 16-03) to satisfy PROF-04 test
metrics:
  duration: "9 min"
  completed: "2026-04-05"
  tasks_completed: 2
  files_modified: 4
---

# Phase 16 Plan 02: POST /profile Endpoint + Dashboard Injection Summary

POST /profile endpoint and __PROFILE_INITIAL__ dashboard injection using frozenset validation and read-merge-write state pattern.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add failing profile tests (TDD RED) | bb80bc8 | tests/test_web_ui_endpoints.py |
| 2 | Add ProfileRequest + POST /profile + __PROFILE_INITIAL__ injection | 9908d29 | web_ui/main.py, web_ui/templates/index.html, tests/test_feed_endpoint.py |

## Decisions Made

- `VALID_PROFILES` is a `frozenset` of 4 string keys: `kids_present`, `were_all_adults`, `above_the_covers`, `permissive`. Consistent with existing FSM pattern.
- `POST /profile` returns `{"active_profile": body.profile}` on success and `HTTP 400` for unknown keys. Mirrors `set_fsm` exactly.
- `__PROFILE_INITIAL__` placeholder added to `index.html` in this plan. The test `test_dashboard_injects_profile_initial` asserts the value appears in the HTML response, which requires the placeholder to be present in the template. Deferring the placeholder to 16-03 would have broken the test.
- Default profile fallback is `"kids_present"` (safest for children ages 3 and 7).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed broken test fixture: `patch.object(web_ui_main, "sp", ...)` failed because `main.py` has no module-level `sp` attribute**

- **Found during:** Task 1 (running RED tests)
- **Issue:** `client` fixture in `test_web_ui_endpoints.py` and `test_feed_endpoint.py` patched `web_ui_main.sp`, but `main.py` uses `_sp_init()` per-request — no module-level `sp` exists. All 4 existing tests errored with `AttributeError`.
- **Fix:** Changed both fixtures to `patch.object(web_ui_main, "_sp_init", return_value=mock_sp)`. For `test_skip_spotify_error_returns_503`, changed the exception `http_status` from 403 to 429 to avoid triggering the SoCo fallback path (the test intent is to verify non-403 errors return 503, not to test the SoCo fallback).
- **Files modified:** `tests/test_web_ui_endpoints.py`, `tests/test_feed_endpoint.py`
- **Commit:** bb80bc8, 9908d29

**2. [Rule 2 - Missing] Added `__PROFILE_INITIAL__` placeholder to `index.html` template**

- **Found during:** Task 2 (GREEN run)
- **Issue:** Plan listed `web_ui/main.py` in `files_modified` but not `web_ui/templates/index.html`. The `dashboard()` injection replaces `__PROFILE_INITIAL__` but the placeholder wasn't in the template, making `replace()` a no-op and causing `test_dashboard_injects_profile_initial` to fail.
- **Fix:** Added `const PROFILE_INITIAL = "__PROFILE_INITIAL__";` comment line to the JS block in `index.html` immediately after `FSM_INITIAL`.
- **Files modified:** `web_ui/templates/index.html`
- **Commit:** 9908d29

## Known Stubs

None. `PROFILE_INITIAL` JavaScript variable is declared but not yet wired to UI state — this is intentional; Plan 16-03 (frontend) will consume the value to render the profile split button. The variable declaration is not a stub that blocks this plan's goal (API endpoint + injection).

## Verification

```
pytest tests/test_web_ui_endpoints.py -x -q
# 8 passed, 2 warnings

grep -n "ProfileRequest\|VALID_PROFILES\|set_profile\|__PROFILE_INITIAL__" web_ui/main.py
# 173: html.replace("__PROFILE_INITIAL__", active_profile)
# 237: VALID_PROFILES: frozenset = frozenset({
# 245: class ProfileRequest(BaseModel):
# 257: async def set_profile(body: ProfileRequest)
# 262: if body.profile not in VALID_PROFILES:
```

## Self-Check: PASSED
