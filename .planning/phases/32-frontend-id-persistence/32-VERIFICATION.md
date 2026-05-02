---
phase: 32-frontend-id-persistence
verified: 2026-05-01T00:00:00Z
status: human_needed
score: 10/10 must-haves verified
overrides_applied: 0
overrides:
  - must_have: "JS writes uid to localStorage (UI-02 REQUIREMENTS.md wording)"
    reason: >
      REQUIREMENTS.md UI-02 says 'JS writes uid to localStorage' but CONTEXT.md D-06
      (confirmed by user in planning) explicitly removes localStorage as a requirement.
      The ROADMAP success criterion SC-2 for Phase 32 does not mention localStorage —
      it says 'sets the httpOnly uid cookie; the dashboard loads immediately without a
      second prompt', which the implementation satisfies. localStorage was intentionally
      removed and the REQUIREMENTS.md wording is stale. The httpOnly cookie alone is
      the persistence mechanism per CONTEXT.md §D-06.
    accepted_by: "verifier (claude)"
    accepted_at: "2026-05-01T00:00:00Z"
human_verification:
  - test: "Visit the root URL in a real browser with no uid cookie set"
    expected: "Browser is redirected to /login and sees the dark-themed login card with 'Read the Room' heading, password input, and gold Enter button"
    why_human: "Visual rendering of login.html cannot be verified programmatically; requires a real browser"
  - test: "Enter a valid access code in the login gate, click Enter"
    expected: "Dashboard loads immediately with no second ID prompt; browser address bar shows / (not /login)"
    why_human: "End-to-end cookie-to-redirect flow requires a live server and real browser to observe"
  - test: "Enter an invalid or unknown access code, click Enter"
    expected: "Inline error message 'Unknown access code' appears below the button in red; no page navigation occurs"
    why_human: "Error display UX requires a browser to verify the inline error renders correctly"
  - test: "Arrive at / after OAuth callback (Phase 29 flow) with uid cookie already set"
    expected: "Dashboard loads directly without showing the login gate"
    why_human: "Requires full OAuth callback integration with a real Spotify app; cannot simulate in unit tests"
---

# Phase 32: Frontend ID Persistence Verification Report

**Phase Goal:** A user enters their access code once and every subsequent visit loads their dashboard directly without re-entering it
**Verified:** 2026-05-01T00:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | A browser with no uid cookie visiting the root URL sees a full-page ID entry gate, not the dashboard | VERIFIED | `test_no_cookie_redirects_to_login` passes: GET / with no cookie returns 302 to /login. GET /login serves login.html with `id="login-form"`. |
| 2 | Entering a valid ID at the gate sets the httpOnly uid cookie; the dashboard loads immediately without a second prompt | VERIFIED | `test_post_login_valid_uid` passes: POST /login with active uid returns `{"ok": true}` and sets `uid` cookie with `httponly=True, samesite="lax", secure=True, max_age=86400`. `test_valid_uid_cookie_serves_dashboard` passes: GET / with valid cookie returns 200 dashboard HTML. `window.location.replace('/')` in login.html JS completes the flow. |
| 3 | Entering an unknown or malformed ID at the gate shows a clear inline error message — no silent redirect or blank screen | VERIFIED | `test_post_login_unknown_uid` and `test_post_login_pending_uid` pass: POST /login returns HTTP 200 with `{"ok": false, "error": "Unknown access code"}`. login.html JS renders `data.error` to `#login-error` element (role="alert"). |
| 4 | A browser arriving at the post-OAuth callback URL has the uid cookie set automatically and then loads the dashboard — no second ID entry required | VERIFIED | CONTEXT.md D-11: `GET /auth/callback` was already implemented (Phase 29) and sets uid cookie + redirects to /. GET / with valid cookie returns 200 dashboard HTML (SC-2 verified above). No code change required; D-02 wiring satisfies this. |

**Score:** 4/4 roadmap success criteria verified

### Plan Frontmatter Must-Haves (32-01-PLAN.md)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `("GET", "/", None)` NOT in 401 parametrize list | VERIFIED | `grep '"GET", "/"' tests/test_web_ui_endpoints.py` returns no output — line was removed |
| 2 | Seven new test functions exist with exact names | VERIFIED | All 7 grep matches confirmed: `test_no_cookie_redirects_to_login`, `test_unknown_uid_redirects_to_login`, `test_login_page_serves_html`, `test_post_login_valid_uid`, `test_post_login_unknown_uid`, `test_post_login_pending_uid`, `test_valid_uid_cookie_serves_dashboard` |
| 3 | `test_unknown_uid_returns_401` targets `/fsm`, not `/` | VERIFIED | Line 93: `unauthed_client.get("/fsm", cookies={"uid": "doesnotexist"})` |
| 4 | `test_pending_uid_returns_401` targets `/fsm`, not `/` | VERIFIED | Line 102: `c.get("/fsm", cookies={"uid": "pendinguid"})` |
| 5 | `web_ui/templates/login.html` exists with all 4 required IDs | VERIFIED | File exists; contains `id="login-form"`, `id="uid-input"`, `id="submit-btn"`, `id="login-error"` |
| 6 | login.html contains `--bg: #0d0b08` and `--accent: #c9a84c` CSS variables | VERIFIED | Lines 12, 15 confirmed by grep |
| 7 | login.html contains vanilla JS fetch flow targeting POST /login | VERIFIED | `fetch('/login', { method: 'POST', ... })` at line 149 |
| 8 | login.html contains `window.location.replace('/')` | VERIFIED | Line 156 confirmed |

### Plan Frontmatter Must-Haves (32-02-PLAN.md)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | GET / with no uid cookie returns 302 to /login | VERIFIED | `test_no_cookie_redirects_to_login` passes |
| 2 | GET / with unknown or pending uid cookie returns 302 to /login | VERIFIED | `test_unknown_uid_redirects_to_login` passes; main.py line 393-395 |
| 3 | GET / with valid active uid cookie returns 200 dashboard HTML | VERIFIED | `test_valid_uid_cookie_serves_dashboard` passes |
| 4 | GET /login returns 200 HTML with login.html content | VERIFIED | `test_login_page_serves_html` passes |
| 5 | POST /login with active uid returns `{ok: true}` and sets httpOnly uid cookie | VERIFIED | `test_post_login_valid_uid` passes; main.py lines 448-456: `httponly=True, samesite="lax", path="/", max_age=86400*30, secure=True` |
| 6 | POST /login with unknown uid returns `{ok: false, error: 'Unknown access code'}` at HTTP 200 | VERIFIED | `test_post_login_unknown_uid` passes; main.py line 446 |
| 7 | POST /login with pending uid returns `{ok: false}` at HTTP 200 | VERIFIED | `test_post_login_pending_uid` passes |
| 8 | All API routes (/fsm, /skip, /events, /now-playing, /profile) still return 401 on missing cookie | VERIFIED | `test_missing_cookie_returns_401` passes for all 7 parametrized API routes |
| 9 | All Phase 32 pytest tests pass green | VERIFIED | 48 passed in `test_web_ui_endpoints.py`; all 7 Phase 32 tests confirmed individually |
| 10 | GET /auth/callback unchanged (D-11) — UI-04 satisfied by GET / valid-cookie path | VERIFIED | No callback changes; GET / correctly serves dashboard on valid cookie (D-02) |

**Overall must-have score:** 10/10 verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tests/test_web_ui_endpoints.py` | Test scaffolds for all Phase 32 routes | VERIFIED | Contains all 7 new Phase 32 test functions; 48 tests pass |
| `web_ui/templates/login.html` | Login gate page HTML/CSS/JS | VERIFIED | Fully implemented with all 4 required element IDs, correct CSS variables, fetch flow |
| `web_ui/main.py` | GET /, GET /login, POST /login route handlers | VERIFIED | All three routes implemented at lines 377-457 |
| `web_ui/main.py` | `class LoginRequest(BaseModel)` | VERIFIED | Defined at line 369-370 |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `web_ui/main.py GET /` | `/login` | `RedirectResponse(url='/login', status_code=302)` | WIRED | 3 redirect paths present (lines 390, 395, 399); test confirms 302 |
| `web_ui/main.py POST /login` | `_registry.load()` | `UserRegistry.load()` for uid validation | WIRED | Line 442: `users = _registry.load()` |
| `web_ui/main.py POST /login` | `response.set_cookie` | httpOnly cookie on JSONResponse | WIRED | Lines 448-456: all required cookie attributes present |
| `web_ui/templates/login.html` | `web_ui/main.py GET /login` | HTMLResponse serving the template | WIRED | `test_login_page_serves_html` passes; `login-form` present in served HTML |
| `login.html JS` | `POST /login` | `fetch('/login', { method: 'POST', ... })` | WIRED | Line 149-153 in login.html |
| `login.html JS` | `/` on success | `window.location.replace('/')` | WIRED | Line 156 in login.html |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `web_ui/main.py POST /login` | `user` from `users` list | `_registry.load()` reads `users.json` from disk | Yes — real UserRegistry lookup | FLOWING |
| `web_ui/main.py GET /` | `html` content | `_load_state(ctx.state_path)` reads user's `state.json` | Yes — real file read with state injection | FLOWING |
| `web_ui/templates/login.html` | `data.error` from fetch response | Server returns `{"ok": false, "error": "Unknown access code"}` | Yes — server-controlled string | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| 7 Phase 32 tests pass | `uv run python -m pytest tests/test_web_ui_endpoints.py -k "redirects_to_login or login_page or post_login or valid_uid_cookie" -v` | 7 passed, 0 failed | PASS |
| Full test_web_ui_endpoints.py green | `uv run python -m pytest tests/test_web_ui_endpoints.py -x -q` | 48 passed, 0 failed | PASS |
| login.html has no localStorage | `grep -c "localStorage" web_ui/templates/login.html` | 0 matches | PASS |
| GET / has 3 redirect paths | `grep -c 'RedirectResponse(url="/login"' web_ui/main.py` | 3 matches | PASS |
| Pre-existing test failures unrelated to Phase 32 | `uv run python -m pytest tests/ -q` | 4 pre-existing failures (test_info_icon, test_sexual_content_scanner, test_skip_client x2) — all documented in 32-02-SUMMARY.md; confirmed pre-Phase 32 via git stash | PASS (out of scope) |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| UI-01 | 32-01, 32-02 | First visit with no uid cookie shows a full-page ID entry gate | SATISFIED | `test_no_cookie_redirects_to_login` and `test_login_page_serves_html` pass; login.html with all required elements exists |
| UI-02 | 32-01, 32-02 | On valid ID entry or post-OAuth callback, server sets httpOnly uid cookie; subsequent visits load dashboard directly | SATISFIED | `test_post_login_valid_uid` confirms cookie set; `test_valid_uid_cookie_serves_dashboard` confirms direct dashboard access. NOTE: REQUIREMENTS.md also says "JS writes uid to localStorage" — this clause was intentionally removed (CONTEXT.md D-06, user confirmed); override applied |
| UI-03 | 32-01, 32-02 | Invalid or unknown uid at gate shows clear error message | SATISFIED | `test_post_login_unknown_uid` and `test_post_login_pending_uid` pass; error element `#login-error` with `role="alert"` and `data.error` rendering in login.html |
| UI-04 | 32-02 | Post-OAuth callback redirects to dashboard where cookie persistence runs | SATISFIED | CONTEXT.md D-11: no code changes required; `GET /auth/callback` (Phase 29) already sets cookie and redirects to /; GET / now serves dashboard on valid cookie |

**UI-02 localStorage override note:** REQUIREMENTS.md UI-02 contains the clause "JS writes uid to localStorage" which conflicts with the implementation decision in CONTEXT.md D-06. The ROADMAP Phase 32 success criterion SC-2 (the contract) does not mention localStorage — it says "sets the httpOnly uid cookie; the dashboard loads immediately without a second prompt." The CONTEXT.md documents the user's explicit confirmation that localStorage is unnecessary. REQUIREMENTS.md wording is stale and the override above documents this intentional deviation.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None found | — | — | — | — |

Scan results:
- No `TODO/FIXME/PLACEHOLDER` comments in Phase 32 modified files
- No `return null` / `return []` / `return {}` stubs in login routes
- No `localStorage` anywhere in login.html (D-06 complied)
- No hardcoded empty data in rendering paths
- `window.location.replace` used correctly (not `window.location.href`)

### Human Verification Required

### 1. Visual Rendering of Login Gate

**Test:** Open the application in a real browser with no uid cookie. Navigate to the root URL.
**Expected:** A full-page dark background with a centered login card. The app name "Read the Room" appears in Playfair Display serif at the top. A password input field (placeholder: "Access code") and a gold "Enter" button are visible. No dashboard content is visible.
**Why human:** CSS rendering, font loading, and visual layout cannot be verified programmatically.

### 2. End-to-End Login Flow

**Test:** At the login gate, type a valid access code (active uid from `users.json`) and click Enter.
**Expected:** The dashboard loads immediately. The browser address bar shows `/`. The login gate does not reappear. Subsequent hard-refreshes also go directly to the dashboard (cookie persisted).
**Why human:** Requires a live server with real `users.json` data and an actual browser to observe the cookie persistence and page transition.

### 3. Inline Error Display on Invalid Code

**Test:** At the login gate, enter a random string that is not a valid uid. Click Enter.
**Expected:** The page stays on `/login`. A red error message reading "Unknown access code" appears below the Enter button. The input field remains accessible for retry. No navigation occurs.
**Why human:** Inline error rendering requires a browser; the JS `errorEl.textContent = data.error` assignment cannot be inspected via unit tests.

### 4. Post-OAuth Dashboard Access (UI-04)

**Test:** Complete the full Phase 29 OAuth flow for a pending user. Observe where the browser lands after `/auth/callback` completes.
**Expected:** Browser lands on `/` and sees the dashboard directly — no login gate appears, no second ID entry required.
**Why human:** Requires real Spotify OAuth app integration (client ID, client secret, redirect URI) and a real browser. Unit tests mock this flow entirely.

### Gaps Summary

No automated gaps found. All 10 must-haves are VERIFIED. All 4 ROADMAP success criteria are met. All 4 UI requirements are satisfied by the implementation.

The UI-02 localStorage clause in REQUIREMENTS.md represents a stale requirement overridden by explicit design decision (CONTEXT.md D-06) confirmed by the user during planning. The ROADMAP contract (Phase 32 SC-2) does not include this clause. Override documented above.

Phase 32 is blocked only on human visual/behavioral verification — the automated implementation is complete and correct.

---

_Verified: 2026-05-01T00:00:00Z_
_Verifier: Claude (gsd-verifier)_
