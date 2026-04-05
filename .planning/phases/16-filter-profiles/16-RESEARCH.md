# Phase 16: Filter Profiles - Research

**Researched:** 2026-04-04
**Domain:** FastAPI endpoint, Python ContentChecker refactor, vanilla JS split-button UI, state.json persistence
**Confidence:** HIGH

## Summary

Phase 16 wires four named filter profiles into the existing daemon + web_ui stack. All building blocks already exist — this phase assembles them in a new configuration rather than introducing new libraries. The daemon already reads `family_safe_mode` from `state.json` each poll cycle; the same `load_state()` pattern extends cleanly to `active_profile`. ContentChecker already accepts `min_severity`, `drug_scanner`, and `sexual_content_scanner` as constructor arguments; adding `explicit_skip: bool = True` to gate Tier 1 is the only new parameter needed. The web_ui already has `_save_state_merge()` and the `__FSM_INITIAL__` injection pattern; a parallel `POST /profile` endpoint and `__PROFILE_INITIAL__` placeholder follow the identical shape.

The largest implementation surface is the split-button UI in `index.html`. The existing `#fsm-toggle` is a single `<button>`; it must become a compound element with two click zones (left = FSM toggle, right = dropdown trigger) and a CSS custom dropdown. No new JS libraries are required — vanilla JS event delegation is sufficient. The CSS variables (`--accent`, `--surface-raised`, `--border`, `--text`) already provide all the styling tokens needed.

The most important correctness invariant: the FSM toggle and profile selection are independent actions. A `POST /profile` call MUST NOT change `family_safe_mode`. A `POST /fsm` call MUST NOT change `active_profile`. Both use `_save_state_merge()` which preserves all unrelated keys by design.

**Primary recommendation:** Implement in three sequenced plans — (1) ContentChecker + daemon backend, (2) `POST /profile` API + state injection, (3) split-button UI. This separation means each plan is independently testable.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Profile selector UI — Split button design**
- D-01: The existing FSM button is converted to a split button. Left/main area toggles FSM on/off (same as before). Right area (▾ icon) opens a profile dropdown — clicking it does NOT toggle FSM.
- D-02: When FSM is on, the button shows the active profile name in gold styling: `[ Family Friendly ▾ ]`
- D-03: When FSM is off, the button shows the current profile name in grey/fsm-off styling with ▾ still visible: `[ Family Friendly ▾ ]` (grey). This allows pre-selecting a profile while FSM is off.
- D-04: Exception for fresh install / no profile set: button shows `[ The Library is Closed ▾ ]` in grey. Default profile on first run is **Family Friendly**.
- D-05: The ▾ trigger occupies the right portion of the button. Clicking anywhere in the left/main area toggles FSM; clicking the ▾ area opens the dropdown. A visual separator (e.g., a faint vertical divider line) can distinguish the two zones.

**Profile dropdown**
- D-06: Custom CSS dropdown — styled to match dashboard aesthetic (dark background, Courier Prime font, border matching `--border` CSS variable). Native `<select>` not used.
- D-07: Dropdown opens below the button, full-width aligned to the button.
- D-08: Dropdown shows all 4 profiles. Currently active/stored profile shows a ✓ (bullet) indicator. This applies whether FSM is on or off — the dropdown always reflects the stored profile.
- D-09: Clicking a profile in the dropdown: saves the selection to state.json immediately via a `POST /profile` API call, updates the button label, closes the dropdown. Does NOT change FSM state.
- D-10: Clicking outside the dropdown (or pressing Escape) closes it without changing selection.

**Profile persistence**
- D-11: Active profile stored in `state.json` as `active_profile` field using the existing read-merge-write pattern. Example key values: `"family_friendly"`, `"adult_wholesome"`, `"adult_no_sexual"`, `"not_explicit"`.
- D-12: Profile survives service restart — state.json is read on daemon startup.
- D-13: When FSM turns on after being off, the profile that was stored (last-used or pre-selected) is restored automatically. No reset to a default.

**ContentChecker profile application**
- D-14: Daemon reads `active_profile` from state.json each poll cycle (alongside `family_safe_mode`). When profile changes, daemon reconstructs ContentChecker with new settings for the next poll.
- D-15: Profile-to-ContentChecker mapping:
  - `family_friendly`: `min_severity=2`, drug_scanner active, sexual_content_scanner active, explicit check ON
  - `adult_wholesome`: `min_severity=3`, drug_scanner=None, sexual_content_scanner active, explicit check ON
  - `adult_no_sexual`: explicit check OFF (skip Tier 1), `min_severity=99` (never fires), drug_scanner=None, sexual_content_scanner active
  - `not_explicit`: explicit check ON, lyrics_service=None / profanity_scanner=None / drug_scanner=None / sexual_content_scanner=None (all lyric scanning off)
- D-16: "Explicit check OFF" for `adult_no_sexual` means ContentChecker skips Tier 1 (the `if track.get("explicit")` skip). This requires a new `explicit_skip: bool` parameter on ContentChecker.

**Dashboard profile display (PROF-04)**
- D-17: The split button itself satisfies PROF-04 — the active profile name is always visible as the button label when FSM is on (and even when off). No separate display element needed.

### Claude's Discretion
- Exact CSS for the split button divider between toggle zone and ▾ zone
- Dropdown animation (fade-in vs instant appear)
- Whether profile mismatch between state.json and ContentChecker is detected by comparing the profile key vs re-reading each cycle
- `POST /profile` endpoint shape — suggest `{"profile": "family_friendly"}` matching existing verb-noun route conventions
- Web UI initial state injection pattern for profile (extend existing `__FSM_INITIAL__` pattern)

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PROF-01 | User can select one of four named filter profiles from the dashboard UI | Split-button + dropdown UI; `POST /profile` API — follows FSM button + POST /fsm pattern |
| PROF-02 | Active profile persists in state.json and survives service restart | `_save_state_merge({"active_profile": ...})` in web_ui; `load_state()` reads it in daemon on startup |
| PROF-03 | ContentChecker applies the active profile's per-scanner rules (explicit_skip, min_severity, drug_enabled, sexual_enabled) | `explicit_skip` param added to ContentChecker.__init__; daemon reconstructs ContentChecker when profile changes |
| PROF-04 | Dashboard displays the currently active profile name | Split button label shows profile name at all times (D-17); `__PROFILE_INITIAL__` injection at serve time |
</phase_requirements>

---

## Standard Stack

No new libraries required. All dependencies already in `requirements.txt` and `web_ui/requirements.txt`.

### Core (already installed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | 0.115.12 | `POST /profile` endpoint | Already used for all API routes |
| Pydantic BaseModel | (FastAPI dep) | Request body validation for `POST /profile` | Established pattern — `FSMRequest` is the model to mirror |
| pytest | 8.3.5 | Unit + integration tests | Project test framework |
| pytest-asyncio | 0.25.3 | Async ContentChecker tests | Used by existing `test_content_checker.py` |

### No New Dependencies
The split-button dropdown is plain HTML/CSS/JS. No dropdown library, no animation library, no component framework. The CSS variables already cover all required tokens.

---

## Architecture Patterns

### Recommended Plan Decomposition

```
Plan 16-01: ContentChecker + daemon backend
  - Add explicit_skip: bool = True to ContentChecker.__init__()
  - Gate Tier 1 behind: if self.explicit_skip and track.get("explicit", False)
  - Add PROFILE_MAP constant in daemon.py mapping profile keys to ContentChecker kwargs
  - Daemon reads active_profile from state.json each poll cycle
  - Reconstruct ContentChecker when active_profile changes (compare prev_profile)
  - Tests: test_content_checker.py additions for explicit_skip=False case

Plan 16-02: POST /profile API + state injection
  - Add ProfileRequest(BaseModel) with profile: str field
  - Validate against allowed set; return 400 for unknown profile keys
  - _save_state_merge({"active_profile": body.profile})
  - Extend dashboard() route: inject __PROFILE_INITIAL__ alongside __FSM_INITIAL__
  - Tests: test_web_ui_endpoints.py additions for POST /profile

Plan 16-03: Split-button UI
  - Restructure #fsm-toggle from <button> to compound element
  - CSS split-button + custom dropdown
  - JS: split click zones, dropdown open/close, POST /profile on selection
  - Update setFsmUI() to accept profile name and render correct label
```

### Existing Pattern: State Read per Poll Cycle

The daemon already re-reads `state.json` on every new track detection:

```python
# daemon.py lines 302-303 — ALREADY THERE, extend this
save_state({"last_track_id": track_id})
state = load_state()   # re-read disk so family_safe_mode and future keys are fresh
```

`active_profile` is read from the same `state` dict — no additional I/O. The only new logic is comparing the profile key to the previously-used profile and reconstructing `ContentChecker` when it differs.

### Pattern: ContentChecker Reconstruction on Profile Change

```python
# daemon.py main() — PROFILE_MAP replaces hardcoded scanner args
PROFILE_MAP = {
    "family_friendly":  {"explicit_skip": True,  "min_severity": 2,  "drug": True,  "sexual": True},
    "adult_wholesome":  {"explicit_skip": True,  "min_severity": 3,  "drug": False, "sexual": True},
    "adult_no_sexual":  {"explicit_skip": False, "min_severity": 99, "drug": False, "sexual": True},
    "not_explicit":     {"explicit_skip": True,  "min_severity": 99, "drug": False, "sexual": False, "lyrics": False},
}

def _build_content_checker(profile_key: str, lyrics_service, profanity_scanner,
                            drug_scanner, sexual_content_scanner) -> ContentChecker:
    cfg = PROFILE_MAP.get(profile_key, PROFILE_MAP["family_friendly"])
    return ContentChecker(
        lyrics_service=lyrics_service if cfg.get("lyrics", True) else None,
        profanity_scanner=profanity_scanner if cfg.get("lyrics", True) else None,
        drug_scanner=drug_scanner if cfg["drug"] else None,
        sexual_content_scanner=sexual_content_scanner if cfg["sexual"] else None,
        min_severity=cfg["min_severity"],
        explicit_skip=cfg["explicit_skip"],
    )
```

The poll loop tracks `prev_profile` alongside `prev_fsm`. When `active_profile != prev_profile`, call `_build_content_checker()` and replace the `content_checker` reference.

### Pattern: FSM Request Model (mirror for ProfileRequest)

```python
# web_ui/main.py — EXISTING
class FSMRequest(BaseModel):
    enabled: bool

@app.post("/fsm")
async def set_fsm(body: FSMRequest) -> JSONResponse:
    _save_state_merge({"family_safe_mode": body.enabled})
    return JSONResponse({"family_safe_mode": body.enabled})

# NEW — follows identical shape
VALID_PROFILES = {"family_friendly", "adult_wholesome", "adult_no_sexual", "not_explicit"}

class ProfileRequest(BaseModel):
    profile: str

@app.post("/profile")
async def set_profile(body: ProfileRequest) -> JSONResponse:
    if body.profile not in VALID_PROFILES:
        raise HTTPException(status_code=400, detail=f"Unknown profile: {body.profile}")
    _save_state_merge({"active_profile": body.profile})
    return JSONResponse({"active_profile": body.profile})
```

### Pattern: Initial State Injection (extend existing)

```python
# web_ui/main.py dashboard() — EXISTING
state = _load_state()
fsm_on = str(state.get("family_safe_mode", False)).lower()
html = html.replace("__FSM_INITIAL__", fsm_on)

# EXTEND — add after existing injection
active_profile = state.get("active_profile", "family_friendly")
html = html.replace("__PROFILE_INITIAL__", active_profile)
```

```javascript
// index.html — EXTEND existing pattern
const FSM_INITIAL = "__FSM_INITIAL__";
const PROFILE_INITIAL = "__PROFILE_INITIAL__";   // NEW
let fsmEnabled = FSM_INITIAL === "true";
let activeProfile = PROFILE_INITIAL;              // NEW
```

### Pattern: ContentChecker explicit_skip Parameter

```python
# content_checker.py ContentChecker.__init__ — ADD parameter
def __init__(
    self,
    lyrics_service=None,
    profanity_scanner=None,
    drug_scanner=None,
    sexual_content_scanner=None,
    min_severity: int = 2,
    explicit_skip: bool = True,   # NEW — D-16
) -> None:
    ...
    self.explicit_skip = explicit_skip

# content_checker.py check() — Tier 1 modification
# BEFORE: if track.get("explicit", False):
# AFTER:
if self.explicit_skip and track.get("explicit", False):
    return TrackEvalResult(action="skip", reason="explicit", severity=3, explicit=True)
```

### Split-Button HTML Structure

```html
<!-- Replace: <button id="fsm-toggle" class="fsm-off">The Library is Closed</button> -->
<!-- With: -->
<div id="fsm-split-btn" class="fsm-split fsm-off">
  <button id="fsm-toggle" class="fsm-main-zone">The Library is Closed</button>
  <button id="profile-dropdown-trigger" class="fsm-dropdown-zone" aria-haspopup="listbox" aria-expanded="false">&#9660;</button>
</div>
<div id="profile-dropdown" class="profile-dropdown" hidden role="listbox">
  <div class="profile-option" data-profile="family_friendly">Family Friendly</div>
  <div class="profile-option" data-profile="adult_wholesome">Adult but Wholesome</div>
  <div class="profile-option" data-profile="adult_no_sexual">Adult, No Sexual</div>
  <div class="profile-option" data-profile="not_explicit">Not Explicit</div>
</div>
<div id="fsm-error"></div>
```

The key structural point: `#fsm-toggle` becomes the left zone child button (FSM toggle), and `#profile-dropdown-trigger` is a sibling right zone button. Both are inside a container `#fsm-split-btn` which carries the `fsm-on`/`fsm-off` class for background color. The existing JS that checks `fsmBtn.className` needs updating to target the container div.

### Anti-Patterns to Avoid

- **Writing the whole state.json from scratch:** `_save_state_merge()` exists precisely to prevent overwriting `last_track_id`, `family_safe_mode`, or any daemon-owned keys. Always use it.
- **Resetting profile when FSM toggles:** D-09 and D-13 both forbid coupling FSM state to profile state. The toggle handler must only POST to `/fsm`; profile selection must only POST to `/profile`.
- **Re-creating all scanner objects on every poll cycle:** Only reconstruct `ContentChecker` when `active_profile` changes. The scanner instances (`LyricsService`, `ProfanityScanner`, `DrugScanner`, `SexualContentScanner`) are long-lived; only the `ContentChecker` wrapper changes.
- **Using native `<select>` for profile dropdown:** D-06 explicitly prohibits it. The custom CSS dropdown must match the dashboard aesthetic.
- **Treating `min_severity=99` as "magic":** It is the intentional mechanism for "profanity scanning is wired but never fires". Document it clearly so future readers don't interpret it as a bug.
- **Closing dropdown on any click — including on the dropdown itself:** The outside-click handler must check `!dropdown.contains(event.target) && event.target !== trigger` before closing.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Profile persistence | Custom file format or DB | Extend existing `state.json` via `_save_state_merge()` | Pattern already handles concurrent writes, key isolation, and file corruption recovery |
| Profile validation | Custom validator | Pydantic `BaseModel` + set membership check in route handler | Already the project pattern; consistent error shape |
| Dropdown positioning | JS position calculation | CSS `position: absolute` relative to `position: relative` container | No JavaScript measurement needed; full-width aligned naturally |
| Profile → scanner config mapping | Inline if/else chains | `PROFILE_MAP` dict constant | Declarative, testable, single source of truth |

---

## Common Pitfalls

### Pitfall 1: FSM click zone bleeds into dropdown trigger zone
**What goes wrong:** A click on ▾ also fires the FSM toggle handler because both elements are inside the same parent container.
**Why it happens:** Event bubbling — a click on `#profile-dropdown-trigger` bubbles up to a click listener on `#fsm-split-btn` or `document`.
**How to avoid:** Attach the FSM toggle listener to `#fsm-toggle` (the left zone button) only — not to the container. Call `event.stopPropagation()` inside the dropdown trigger handler to prevent bubbling. Test by clicking ▾ and verifying FSM state does not change.
**Warning signs:** FSM toggles unexpectedly when selecting a profile.

### Pitfall 2: `_save_state_merge` race between daemon and web_ui
**What goes wrong:** Daemon writes `last_track_id` at the exact moment web_ui writes `active_profile`; one overwrites the other.
**Why it happens:** Both do a read-then-write without an OS-level lock. This race exists for `family_safe_mode` already.
**How to avoid:** This is a known accepted limitation (Phase 1 decision — no atomic rename on bind-mounted files). The window is milliseconds and state.json is small. The daemon's `load_state()` on the next poll cycle recovers any lost key within 1 second. Document, don't over-engineer.
**Warning signs:** `active_profile` disappears from state.json after daemon writes.

### Pitfall 3: `min_severity=99` breaks profanity scanner initialization
**What goes wrong:** `ProfanityScanner(min_severity=99)` may not validate the range — check whether the scanner constructor enforces a max.
**Why it happens:** `adult_no_sexual` profile uses `min_severity=99` as a "never fires" sentinel. If `ProfanityScanner` validates the range as 1–3, instantiation will fail.
**How to avoid:** Review `ProfanityScanner.__init__` before using `min_severity=99`. If it validates, pass the scanner as `None` for `adult_no_sexual` instead. The `not_explicit` profile already sets `profanity_scanner=None` — the same pattern can apply.
**Warning signs:** Daemon startup exception from ProfanityScanner.

### Pitfall 4: Existing tests break when ContentChecker Tier 1 changes
**What goes wrong:** Tests that mock a track with `explicit=True` and expect `action="skip"` will pass (explicit_skip defaults to True), but tests that construct `ContentChecker()` without `explicit_skip` and expect Tier 1 behavior unchanged must still work.
**Why it happens:** Adding `explicit_skip: bool = True` with a default preserves existing test behavior — explicit_skip=True is the default. Zero existing tests should break.
**How to avoid:** Default `explicit_skip=True`. Verify all existing test fixtures still pass before adding new profile tests.
**Warning signs:** `test_content_checker.py` failures after adding the parameter.

### Pitfall 5: Profile dropdown remains open after navigation or SSE reconnect
**What goes wrong:** The dropdown is open; SSE reconnects and triggers a UI state refresh; the dropdown stays open in a stale state.
**Why it happens:** The dropdown open/close state is only managed by JS click handlers, not by the SSE event handler.
**How to avoid:** Close the dropdown (set `hidden`, update aria-expanded) at the start of any SSE reconnect handler and on page focus events.
**Warning signs:** Dropdown lingers after reconnect with wrong ✓ indicator.

### Pitfall 6: Fresh install — no `active_profile` in state.json
**What goes wrong:** `state.get("active_profile")` returns `None`; button label shows `None ▾` instead of `The Library is Closed ▾` or `Family Friendly ▾`.
**Why it happens:** D-04 specifies a special "fresh install" case — profile not yet stored means button shows "The Library is Closed" text.
**How to avoid:** In JS, `PROFILE_INITIAL` defaults to `"family_friendly"` from server injection. In `web_ui/main.py`, `state.get("active_profile", "family_friendly")` ensures the placeholder is always a valid key. The "Library is Closed" text only shows when `active_profile` is `None` AND `family_safe_mode` is False — implement as a special label case in `setFsmUI()`.
**Warning signs:** Button shows "null ▾" or "undefined ▾" on fresh installs.

---

## Code Examples

### ContentChecker Tier 1 Gate (explicit_skip)
```python
# content_checker.py — Tier 1, after adding self.explicit_skip
if self.explicit_skip and track.get("explicit", False):
    log.debug(
        "[SCAN] track=%r artist=%r severity=3 matched=[] action=skip",
        track_name,
        artist_name,
    )
    return TrackEvalResult(action="skip", reason="explicit", severity=3, explicit=True)
```

### Daemon Profile Change Detection
```python
# poll_loop() — add alongside prev_fsm tracking
prev_profile: str = state.get("active_profile", "family_friendly")

# Inside track-change branch, after state = load_state():
current_profile = state.get("active_profile", "family_friendly")
if current_profile != prev_profile:
    content_checker = _build_content_checker(
        current_profile, lyrics_service, profanity_scanner, drug_scanner, sexual_content_scanner
    )
    prev_profile = current_profile
    log.info("[PROFILE] switched to %r", current_profile)
```

### POST /profile Endpoint
```python
# web_ui/main.py
VALID_PROFILES = frozenset({"family_friendly", "adult_wholesome", "adult_no_sexual", "not_explicit"})

class ProfileRequest(BaseModel):
    profile: str

@app.post("/profile")
async def set_profile(body: ProfileRequest) -> JSONResponse:
    if body.profile not in VALID_PROFILES:
        raise HTTPException(status_code=400, detail=f"Unknown profile: {body.profile!r}")
    try:
        _save_state_merge({"active_profile": body.profile})
    except OSError as exc:
        log.error("POST /profile write failed: %s", exc)
        raise HTTPException(status_code=500, detail="Could not write state.json")
    return JSONResponse({"active_profile": body.profile})
```

### Split-Button JS — Click Zone Separation
```javascript
const fsmMainZone = document.getElementById('fsm-toggle');         // left zone
const profileTrigger = document.getElementById('profile-dropdown-trigger'); // right zone
const profileDropdown = document.getElementById('profile-dropdown');
const fsmSplitBtn = document.getElementById('fsm-split-btn');      // container

// FSM toggle — left zone only
fsmMainZone.addEventListener('click', async function() {
  const newState = !fsmEnabled;
  setFsmUI(newState, activeProfile);
  // ... POST /fsm ...
});

// Dropdown trigger — right zone; stopPropagation prevents FSM toggle
profileTrigger.addEventListener('click', function(e) {
  e.stopPropagation();
  const isOpen = !profileDropdown.hidden;
  profileDropdown.hidden = isOpen;
  profileTrigger.setAttribute('aria-expanded', String(!isOpen));
});

// Close on outside click
document.addEventListener('click', function(e) {
  if (!profileDropdown.hidden &&
      !profileDropdown.contains(e.target) &&
      e.target !== profileTrigger) {
    profileDropdown.hidden = true;
    profileTrigger.setAttribute('aria-expanded', 'false');
  }
});

// Close on Escape
document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape' && !profileDropdown.hidden) {
    profileDropdown.hidden = true;
    profileTrigger.setAttribute('aria-expanded', 'false');
  }
});
```

### setFsmUI — Extended for Profile Label
```javascript
const PROFILE_DISPLAY_NAMES = {
  'family_friendly':  'Family Friendly',
  'adult_wholesome':  'Adult but Wholesome',
  'adult_no_sexual':  'Adult, No Sexual',
  'not_explicit':     'Not Explicit',
};

function setFsmUI(enabled, profile) {
  fsmEnabled = enabled;
  activeProfile = profile || activeProfile;
  const label = PROFILE_DISPLAY_NAMES[activeProfile] || 'Family Friendly';
  const isFresh = !activeProfile && !enabled;

  fsmSplitBtn.className = 'fsm-split ' + (enabled ? 'fsm-on' : 'fsm-off');
  if (isFresh) {
    fsmMainZone.textContent = 'The Library is Closed';
  } else {
    fsmMainZone.textContent = label;
  }
  // ✓ indicator in dropdown
  document.querySelectorAll('.profile-option').forEach(function(opt) {
    opt.classList.toggle('profile-option--active', opt.dataset.profile === activeProfile);
  });
}
```

---

## Validation Architecture

nyquist_validation is enabled (config.json: `"nyquist_validation": true`).

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.3.5 + pytest-asyncio 0.25.3 |
| Config file | none — pytest discovers tests/ automatically |
| Quick run command | `pytest tests/test_content_checker.py tests/test_web_ui_endpoints.py -x -q` |
| Full suite command | `pytest tests/ -x -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PROF-03 | ContentChecker with explicit_skip=False skips Tier 1 for explicit tracks | unit | `pytest tests/test_content_checker.py -x -q -k explicit_skip` | ❌ Wave 0 — new test needed |
| PROF-03 | ContentChecker with min_severity=99 allows all profanity | unit | `pytest tests/test_content_checker.py -x -q -k min_severity_99` | ❌ Wave 0 — new test needed |
| PROF-03 | ContentChecker with drug_scanner=None allows drug references | unit | `pytest tests/test_content_checker.py -x -q -k no_drug_scanner` | ✅ Covered by existing pattern (None scanner = no scan) |
| PROF-02 | POST /profile writes active_profile to state.json | unit | `pytest tests/test_web_ui_endpoints.py -x -q -k profile` | ❌ Wave 0 — new test needed |
| PROF-02 | POST /profile with unknown key returns 400 | unit | `pytest tests/test_web_ui_endpoints.py -x -q -k invalid_profile` | ❌ Wave 0 — new test needed |
| PROF-01, PROF-04 | Dashboard injects PROFILE_INITIAL placeholder | unit | `pytest tests/test_web_ui_endpoints.py -x -q -k profile_initial` | ❌ Wave 0 — new test needed |
| PROF-04 | Split button shows profile name (UI) | manual | Browser visual inspection | N/A — manual only |

### Sampling Rate
- **Per task commit:** `pytest tests/test_content_checker.py tests/test_web_ui_endpoints.py -x -q`
- **Per wave merge:** `pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] New test cases in `tests/test_content_checker.py` — `explicit_skip=False` behavior (PROF-03)
- [ ] New test cases in `tests/test_web_ui_endpoints.py` — `POST /profile` endpoint (PROF-01, PROF-02)
- [ ] New test case in `tests/test_web_ui_endpoints.py` — `__PROFILE_INITIAL__` injection in dashboard HTML (PROF-04)

---

## Environment Availability

Step 2.6: SKIPPED (no external dependencies — purely code/config changes within the existing Python + HTML/CSS/JS stack).

---

## Runtime State Inventory

Step 2.5: NOT a rename/refactor/migration phase. Skipped.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `PROFANITY_MIN_SEVERITY` env var — hardcoded filter config | Profile-driven config from state.json | Phase 16 | `PROFANITY_MIN_SEVERITY` env var becomes the daemon fallback default only; profile overrides it at runtime |
| Single `ContentChecker` instance for daemon lifetime | Profile-aware reconstruction on profile change | Phase 16 | Scanner objects are long-lived; only the thin `ContentChecker` wrapper is replaced |
| FSM toggle is a single `<button>` | Split-button compound element (left = toggle, right = dropdown trigger) | Phase 16 | Existing `fsmBtn` reference in JS must be split into `fsmMainZone` and `profileTrigger` |

---

## Open Questions

1. **`ProfanityScanner` constructor — does it validate min_severity range?**
   - What we know: `adult_no_sexual` profile uses `min_severity=99`. `ProfanityScanner(min_severity=PROFANITY_MIN_SEVERITY)` currently only receives values 1–3 (env var).
   - What's unclear: Whether `ProfanityScanner.__init__` has a range assertion that would raise on 99.
   - Recommendation: Check `profanity_scanner.py` before Plan 16-01. If it validates, use `profanity_scanner=None` instead of `min_severity=99` for `adult_no_sexual` (equivalent behavior — no profanity skip when scanner is None).

2. **`adult_no_sexual` — sexual_content_scanner still active with explicit_skip=False**
   - What we know: D-15 specifies sexual_content_scanner is active for `adult_no_sexual`, but explicit check is off. So explicit tracks are allowed, but sexual content in lyrics still triggers a skip.
   - What's unclear: `adult_no_sexual` with `min_severity=99` means profanity never fires. If `profanity_scanner` is still wired but `min_severity=99`, the scanner runs and produces results that are silently discarded. This is wasteful but harmless.
   - Recommendation: Wire `profanity_scanner=None` for `adult_no_sexual` (profanity never fires anyway at severity 99); this avoids the unnecessary scan cost. The locked decision D-15 says `min_severity=99` but doesn't prohibit also setting `profanity_scanner=None` — both achieve the same outcome.

3. **Daemon profile change detection — per-cycle vs per-track-change**
   - What we know: D-14 says daemon reads `active_profile` each poll cycle. `load_state()` is called on each new track detection (line 303). Between track changes, the daemon uses the ContentChecker from the last track change.
   - What's unclear: Should profile changes take effect mid-track (i.e., every poll cycle) or only on next track change?
   - Recommendation: Per-track-change is sufficient — the current architecture already re-evaluates on track change. Profile changes don't apply retroactively to the currently playing track. Keep detection in the track-change branch alongside `prev_fsm` tracking.

---

## Sources

### Primary (HIGH confidence)
- Direct source file reads: `content_checker.py`, `daemon.py`, `web_ui/main.py`, `web_ui/templates/index.html`, `tests/test_content_checker.py`, `tests/test_web_ui_endpoints.py` — exact signatures, patterns, and line numbers verified
- `.planning/phases/16-filter-profiles/16-CONTEXT.md` — locked decisions and implementation constraints
- `.planning/REQUIREMENTS.md` — requirement IDs and descriptions
- `.planning/PROJECT.md` — project history and tech stack
- `requirements.txt`, `web_ui/requirements.txt` — exact library versions confirmed

### Secondary (MEDIUM confidence)
- None needed — all research grounded in project source files

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — verified from requirements.txt and source files; no new libraries
- Architecture: HIGH — all patterns traced directly to existing working code in daemon.py and web_ui/main.py
- Pitfalls: HIGH — derived from code inspection of event bubbling mechanics, state.json race condition (documented in Phase 1 decisions), and ContentChecker constructor analysis

**Research date:** 2026-04-04
**Valid until:** Stable (no external dependencies; valid until source files change)
