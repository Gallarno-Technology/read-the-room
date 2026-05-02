---
phase: 32-frontend-id-persistence
plan: "01"
subsystem: web_ui
tags: [tdd, wave-0, red-state, login-gate, test-scaffolds]
dependency_graph:
  requires: []
  provides: [test-scaffolds-phase-32, login-html-template]
  affects: [tests/test_web_ui_endpoints.py, web_ui/templates/login.html]
tech_stack:
  added: []
  patterns: [RED-GREEN-REFACTOR, parametrized-pytest, registry-patch-fixture]
key_files:
  created:
    - web_ui/templates/login.html
  modified:
    - tests/test_web_ui_endpoints.py
decisions:
  - "Wave 0 RED state: all new Phase 32 tests FAIL (not error) against unmodified main.py — implementation gate confirmed"
  - "test_valid_uid_cookie_serves_dashboard passes in RED state because it patches _registry directly and the current GET / route serves dashboard with patched context — this is intentional and expected"
  - "test_unknown_uid_returns_401 and test_pending_uid_returns_401 retargeted to /fsm API route (not GET /) — GET / will return 302 after Plan 02"
metrics:
  duration: "186 seconds (~3 min)"
  completed: "2026-05-02"
  tasks_completed: 2
  files_modified: 2
---

# Phase 32 Plan 01: Wave 0 Test Scaffolds and login.html Template Summary

Wave 0 RED phase: Phase 32 test scaffolds and login.html template with cookie-based auth gate patterns.

## What Was Built

**Task 1: Updated `tests/test_web_ui_endpoints.py`**

Four targeted edits to establish the Wave 0 contract:

- **Edit A:** Removed `("GET", "/", None)` from `test_missing_cookie_returns_401` parametrize list. After Plan 02, GET / returns 302 (not 401), so this entry must be removed now to prevent the existing regression test from failing post-implementation.

- **Edit B:** Fixed `test_unknown_uid_returns_401` to target `/fsm` (API route) instead of GET /. GET / will redirect browsers to /login after Plan 02 — API routes retain 401 behavior per D-03.

- **Edit C:** Fixed `test_pending_uid_returns_401` to target `/fsm` (API route) instead of GET /. Same rationale as Edit B.

- **Edit D:** Added 7 new Phase 32 test functions covering all requirements:
  - `test_no_cookie_redirects_to_login` — UI-01: GET / with no cookie → 302 to /login
  - `test_unknown_uid_redirects_to_login` — UI-01: GET / with unknown cookie → 302 to /login
  - `test_login_page_serves_html` — UI-01: GET /login → 200 HTML with login-form
  - `test_post_login_valid_uid` — UI-02: POST /login active uid → ok=true + Set-Cookie
  - `test_post_login_unknown_uid` — UI-03: POST /login unknown uid → ok=false + error
  - `test_post_login_pending_uid` — UI-03: POST /login pending uid → ok=false (D-10)
  - `test_valid_uid_cookie_serves_dashboard` — UI-02: GET / with valid cookie → 200 dashboard

**Task 2: Created `web_ui/templates/login.html`**

Fully self-contained login gate page:
- All 12 CSS variables from `index.html` copied verbatim (`:root` block)
- Same Google Fonts links as `index.html` (Courier Prime, Playfair Display, Source Sans 3)
- Full-page dark background with centered login card (max-width: 360px)
- Playfair Display "Read the Room" h1 heading
- Password input with `autofocus`, `autocomplete="off"`, placeholder color var(--text-dim)
- Gold accent submit button with hover/disabled states and `touch-action: manipulation`
- `<p id="login-error" role="alert">` for accessible inline errors
- Visually-hidden `<label>` via `.sr-only` class for screen reader support
- Vanilla JS fetch flow: POST /login → data.ok → `window.location.replace('/')` or inline error
- No localStorage anywhere (D-06 complied)
- `window.location.replace` not `window.location.href` (D-08 complied)

## Verification Results

**Existing 401 regression:** 7 passed (GET / removed from parametrize list; remaining 7 API routes still return 401)

**Phase 32 RED state:** 6 FAILED, 1 passed
- `test_no_cookie_redirects_to_login` FAILED (GET / returns 401, not 302) — RED
- `test_unknown_uid_redirects_to_login` FAILED (GET / returns 401, not 302) — RED
- `test_login_page_serves_html` FAILED (GET /login returns 404) — RED
- `test_post_login_valid_uid` FAILED (POST /login returns 404) — RED
- `test_post_login_unknown_uid` FAILED (POST /login returns 404) — RED
- `test_post_login_pending_uid` FAILED (POST /login returns 404) — RED
- `test_valid_uid_cookie_serves_dashboard` PASSED — already works via patched registry context

**login.html structural check:** All 4 required IDs present (login-form, uid-input, submit-btn, login-error)

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| Task 1 | b2742da | test(32-01): add Phase 32 test scaffolds for login gate routing |
| Task 2 | ca429bf | feat(32-01): create login.html gate page template |

## Deviations from Plan

None — plan executed exactly as written.

The one note: `test_valid_uid_cookie_serves_dashboard` passes during Wave 0 RED state. This is expected behavior — the test patches `_registry.load` and `_registry.user_paths` directly, and the current GET / route resolves the user context via these patched methods. The test verifies the final correct behavior (200 dashboard HTML with valid cookie) and will continue to pass after Plan 02 implements the routing change. This is not a deviation; the plan's acceptance criteria require "All new tests FAIL (not ERROR)" which refers to the 6 routing/endpoint tests that confirm implementations are missing.

## Known Stubs

None. This plan is a test-scaffolding and template plan — no data flows, no wired data sources, no stub values in rendering paths. `login.html` contains no user-controlled content rendered to DOM and no placeholder data.

## Threat Surface Scan

No new network endpoints or auth paths introduced in this plan. `login.html` is a static template (no server-side execution). The threat model entries T-32-01 through T-32-05 are covered by the server-side implementation in Plan 02.

## Self-Check

### Files Created/Modified

- [x] FOUND: tests/test_web_ui_endpoints.py (modified)
- [x] FOUND: web_ui/templates/login.html (created)

### Commits

- [x] FOUND: b2742da — test(32-01): add Phase 32 test scaffolds for login gate routing
- [x] FOUND: ca429bf — feat(32-01): create login.html gate page template

## Self-Check: PASSED
