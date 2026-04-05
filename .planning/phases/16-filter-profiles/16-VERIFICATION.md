---
phase: 16-filter-profiles
verified: 2026-04-05T00:00:00Z
status: human_needed
score: 10/10 automated must-haves verified
re_verification: false
human_verification:
  - test: "Start web_ui (uvicorn main:app --port 8080 --reload from web_ui/), open http://localhost:8080, verify split button renders: left zone shows profile name, right zone shows down-arrow (▾)"
    expected: "Button renders as a compound element. Left side shows the active profile display name (e.g. 'Kids Present'). Right side shows ▾ glyph. Gold background when FSM on; grey surface when FSM off."
    why_human: "Visual rendering and layout correctness cannot be verified by grep or test suite — CSS and HTML structure require browser rendering to confirm."
  - test: "Click the ▾ right zone — confirm dropdown opens showing all 4 profiles with ✓ prefix on the active profile. Then click the left zone — confirm FSM toggles and dropdown does NOT open."
    expected: "Click zones are independent. Right zone opens dropdown only. Left zone toggles FSM only. The two actions never interfere."
    why_human: "Click-zone separation (stopPropagation) is a runtime browser behavior that cannot be verified by static code analysis."
  - test: "With dropdown open, click a different profile. Verify: button label updates to new profile name, dropdown closes, FSM state does NOT change (check state.json or toggle label)."
    expected: "Profile switches; FSM toggle state is unchanged. POST /profile is called (check browser devtools Network tab). state.json contains updated active_profile key."
    why_human: "End-to-end optimistic update + state persistence requires browser interaction and manual state.json inspection."
  - test: "With dropdown open, click outside the dropdown. Then open it again and press Escape."
    expected: "Both actions close the dropdown without changing the selected profile or FSM state."
    why_human: "Outside-click and Escape dismiss are browser event behaviors requiring manual testing."
  - test: "Trigger an SSE reconnect (stop/restart the server while the page is open). Confirm dropdown closes automatically when reconnection occurs."
    expected: "Dropdown is closed on es.onopen. The page reconnects cleanly."
    why_human: "SSE reconnect behavior requires a live server and cannot be tested programmatically in the test suite."
---

# Phase 16: Filter Profiles Verification Report

**Phase Goal:** Parent can select a named filter profile from the dashboard; the active profile controls which content rules apply
**Verified:** 2026-04-05
**Status:** human_needed — all automated checks pass; 5 UI behavioral items require browser verification
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | ContentChecker with explicit_skip=False does NOT skip explicit-flagged tracks at Tier 1 | VERIFIED | `content_checker.py:92` gates Tier 1 on `self.explicit_skip`; test `test_explicit_skip_false_allows_explicit_track` passes |
| 2  | ContentChecker with explicit_skip=True (default) still skips explicit-flagged tracks (no regression) | VERIFIED | 16 tests in `tests/test_content_checker.py` all pass; 3 new explicit_skip tests GREEN |
| 3  | Daemon reads active_profile from state.json on each track change and reconstructs ContentChecker when profile changes | VERIFIED | `daemon.py:389` — `if current_profile != prev_profile:` calls `_build_content_checker()`; `prev_profile` updated on line 397 |
| 4  | PROFILE_MAP in daemon.py defines all four profiles with correct scanner args per D-15 | VERIFIED | `daemon.py:51-84` — all 4 keys present with correct explicit_skip, min_severity, drug/sexual/profanity/lyrics flags |
| 5  | POST /profile with a valid key writes active_profile to state.json and returns 200 | VERIFIED | `web_ui/main.py:257-269` — endpoint exists; `test_post_profile_valid` passes |
| 6  | POST /profile with an invalid key returns 400 | VERIFIED | `web_ui/main.py:262` — VALID_PROFILES frozenset check with HTTPException 400; `test_post_profile_invalid` passes |
| 7  | GET / injects the stored active_profile value into HTML via __PROFILE_INITIAL__ placeholder | VERIFIED | `web_ui/main.py:172-173` — html.replace; template has placeholder at line 502; `test_dashboard_injects_profile_initial` passes |
| 8  | POST /profile does NOT change family_safe_mode (independence invariant) | VERIFIED | `_save_state_merge({"active_profile": body.profile})` — only active_profile key written; `test_post_profile_does_not_change_fsm` passes |
| 9  | Dashboard split button HTML structure is present with all 4 profile options | VERIFIED | `index.html:450-458` — `#fsm-split-btn`, `#fsm-toggle.fsm-main-zone`, `#profile-dropdown-trigger.fsm-dropdown-zone`, 4 `.profile-option` divs |
| 10 | Profile selection in dropdown calls POST /profile and updates button label | VERIFIED | `index.html:609-613` — `fetch('/profile', {method: 'POST', ...})`; `setFsmUI(fsmEnabled, newProfile)` on line 604 updates label |

**Score:** 10/10 truths verified (automated)

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `content_checker.py` | explicit_skip param + Tier 1 gate | VERIFIED | Line 63: `explicit_skip: bool = True`; line 92: `if self.explicit_skip and track.get(...)` |
| `daemon.py` | PROFILE_MAP + _build_content_checker + prev_profile | VERIFIED | PROFILE_MAP lines 51-84; helper lines 242-268; prev_profile init line 329; comparison line 389 |
| `tests/test_content_checker.py` | 3 new explicit_skip tests | VERIFIED | Lines 227-259 — all 3 functions present and 16 total tests pass |
| `web_ui/main.py` | ProfileRequest + VALID_PROFILES + POST /profile + __PROFILE_INITIAL__ injection | VERIFIED | Lines 237-269 (endpoint); line 172-173 (injection) |
| `tests/test_web_ui_endpoints.py` | 4 new profile tests | VERIFIED | Lines 93-141 — all 4 functions present and 8 total tests pass |
| `web_ui/templates/index.html` | Split-button HTML + CSS + JS | VERIFIED | fsm-split-btn HTML (lines 450-458); CSS (.fsm-split, .fsm-main-zone, .fsm-dropdown-zone, .profile-dropdown, .profile-option at lines 147-265); JS (fsmSplitBtn/fsmMainZone/profileTrigger/profileDropdown DOM refs lines 507-510; PROFILE_DISPLAY_NAMES line 527; setFsmUI updated line 534; click handlers lines 557-638) |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `daemon.py poll_loop` | `_build_content_checker()` | `current_profile != prev_profile` comparison | WIRED | Line 389: comparison present; line 390-396: rebuilds checker and reassigns |
| `content_checker.py ContentChecker.check()` | `self.explicit_skip` | `if self.explicit_skip and track.get(...)` | WIRED | Line 92 — exact pattern confirmed |
| `web_ui/main.py dashboard()` | `html.replace` | `__PROFILE_INITIAL__` placeholder replacement | WIRED | Line 173: replace call; template line 502: placeholder present |
| `web_ui/main.py set_profile()` | `_save_state_merge` | `_save_state_merge({"active_profile": body.profile})` | WIRED | Line 265 — exact call confirmed |
| `index.html #profile-dropdown-trigger click` | `e.stopPropagation()` | Prevents FSM toggle when ▾ clicked | WIRED | Line 592 — stopPropagation in right-zone handler |
| `index.html profile option click` | `POST /profile` | `fetch('/profile', {method: 'POST', body: JSON.stringify({profile: key})})` | WIRED | Lines 609-613 — full fetch call confirmed |
| `index.html setFsmUI()` | `fsmSplitBtn.className` | `'fsm-split ' + (enabled ? 'fsm-on' : 'fsm-off')` | WIRED | Line 543 — exact pattern confirmed |
| `index.html es.onopen` | `closeDropdown()` | SSE reconnect closes dropdown | WIRED | Line 842-844 — profileDropdown.hidden check inside es.onopen handler |

---

## Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `web_ui/main.py dashboard()` | `active_profile` | `_load_state()` reads state.json; falls back to "kids_present" | Yes — state.json read from disk; POST /profile writes to same file | FLOWING |
| `index.html` | `activeProfile` | Server-injected `PROFILE_INITIAL` constant at serve time | Yes — server replaces placeholder with real value from state.json | FLOWING |
| `index.html setFsmUI()` | `label` from `PROFILE_DISPLAY_NAMES[activeProfile]` | `activeProfile` state variable | Yes — lookup table always has a value; fallback to 'Kids Present' | FLOWING |
| `daemon.py poll_loop` | `current_profile` | `state.get("active_profile", "kids_present")` on each track change | Yes — reads live state.json written by POST /profile | FLOWING |

---

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| ContentChecker explicit_skip param exists and is functional | `uv run pytest tests/test_content_checker.py -x -q` | 16 passed | PASS |
| POST /profile endpoint: valid, invalid, FSM-independence, dashboard injection | `uv run pytest tests/test_web_ui_endpoints.py -x -q` | 8 passed, 2 warnings | PASS |
| Full test suite (excluding known pre-existing skip-client failure) | `uv run pytest tests/ -x -q --ignore=tests/test_skip_client.py` | 82 passed, 27 warnings | PASS |
| Pre-existing test_soco_pause_uses_cached_ip confirmed as pre-existing, not a regression | `uv run pytest tests/test_skip_client.py -x -q` | 1 failed (confirmed pre-existing), 4 passed | PASS (excluded per verification note) |
| daemon.py imports cleanly with all new symbols | `python -c "import daemon"` equivalent — PROFILE_MAP, _build_content_checker, prev_profile all grep-verified | Symbols exist at expected lines | PASS |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| PROF-01 | 16-02, 16-03 | User can select one of four named filter profiles from the dashboard UI | SATISFIED (automated) + HUMAN NEEDED (browser) | POST /profile endpoint wired in web_ui/main.py; profile dropdown in index.html with POST /profile fetch call; human browser verification required for actual interaction |
| PROF-02 | 16-02 | Active profile persists in state.json and survives service restart | SATISFIED | `_save_state_merge({"active_profile": body.profile})` uses read-merge-write; `_load_state()` on dashboard loads stored value; `startup_state.get("active_profile", "kids_present")` in daemon.py main() |
| PROF-03 | 16-01 | ContentChecker applies the active profile's per-scanner rules | SATISFIED | PROFILE_MAP (4 profiles, correct args), `_build_content_checker()` wired in poll_loop and main(), `explicit_skip` parameter functional, `prev_profile` tracking operational |
| PROF-04 | 16-02, 16-03 | Dashboard displays the currently active profile name | SATISFIED (automated) + HUMAN NEEDED (browser) | `__PROFILE_INITIAL__` injected server-side; JS consumes it via `PROFILE_INITIAL` constant; `setFsmUI()` renders label via `PROFILE_DISPLAY_NAMES` lookup; test `test_dashboard_injects_profile_initial` passes; visual rendering requires human verification |

No orphaned requirements — all 4 PROF-* requirements claimed by plans and verified.

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None found | — | — | — | — |

No TODO/FIXME/placeholder comments, empty implementations, or hardcoded empty data found in modified files. Old `fsmBtn` variable is fully replaced in JS — zero residual references. `__PROFILE_INITIAL__` in template is the server-side placeholder, correctly replaced at serve time (not a stub).

---

## Human Verification Required

### 1. Split Button Visual Rendering

**Test:** Start web_ui (`uvicorn main:app --port 8080 --reload` from `web_ui/`), open `http://localhost:8080`.
**Expected:** Button renders as a compound element. Left zone shows profile display name (e.g. "Kids Present"). Right zone shows ▾. Container background is gold when FSM on, grey when FSM off. Text color inherits correctly (dark on gold, light on grey).
**Why human:** CSS layout, color rendering, and font inheritance cannot be verified by static code analysis.

### 2. Click Zone Independence

**Test:** Click the ▾ right zone. Confirm dropdown opens. Then click the left zone (not ▾). Confirm FSM toggles but dropdown does NOT open.
**Expected:** The two click zones are completely independent. stopPropagation on the right zone prevents FSM toggle; FSM click listener on `#fsm-toggle` (left zone element only) prevents dropdown opening.
**Why human:** Event bubbling and stopPropagation correctness is a runtime browser behavior.

### 3. Profile Selection End-to-End

**Test:** Open dropdown, click a profile different from the current one. Check: button label updates immediately, dropdown closes, check `state.json` to confirm `active_profile` changed, check that FSM toggle state did not change.
**Expected:** Optimistic UI update + POST /profile succeeds + state.json persists + FSM state unchanged.
**Why human:** End-to-end optimistic update flow and state.json inspection require manual verification.

### 4. Dropdown Dismiss Behaviors

**Test:** (a) Open dropdown, click somewhere outside it — dropdown should close. (b) Open dropdown, press Escape — dropdown should close and focus returns to ▾ trigger.
**Expected:** Both dismiss mechanisms work correctly per D-10.
**Why human:** Browser click events and keyboard focus behavior require live browser testing.

### 5. SSE Reconnect Closes Dropdown

**Test:** Open the dropdown in the browser, then stop and restart the uvicorn server. Observe whether the dropdown closes automatically when SSE reconnects.
**Expected:** `es.onopen` handler calls `closeDropdown()` if dropdown is open (line 842-844).
**Why human:** Requires a live server restart to trigger SSE reconnect.

---

## Gaps Summary

No gaps — all automated must-haves are verified. The 5 human verification items are UI behavioral checks that cannot be confirmed programmatically. The pre-existing `test_soco_pause_uses_cached_ip` failure was confirmed as pre-existing (present before any phase 16 changes) and is explicitly excluded per verification instructions.

---

_Verified: 2026-04-05_
_Verifier: Claude (gsd-verifier)_
