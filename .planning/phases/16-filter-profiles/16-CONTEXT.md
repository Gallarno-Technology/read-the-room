# Phase 16: Filter Profiles - Context

**Gathered:** 2026-04-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Parent can select one of four named filter profiles from the dashboard. The active profile controls which content rules ContentChecker applies (explicit_skip, min_severity, drug_enabled, sexual_enabled). FSM toggle still gates whether filtering runs at all — profile controls which rules apply when it does.

Four profiles (defined in PROJECT.md):
- **Family Friendly**: explicit skip, profanity ≥ severity 2, drug skip, sexual skip
- **Adult but Wholesome**: explicit skip, profanity ≥ severity 3, drug allow, sexual skip
- **Adult, No Sexual**: explicit allow, profanity allow, drug allow, sexual skip
- **Not Explicit**: explicit skip only, all lyric scanning off

</domain>

<decisions>
## Implementation Decisions

### Profile selector UI — Split button design
- **D-01:** The existing FSM button is converted to a split button. Left/main area toggles FSM on/off (same as before). Right area (▾ icon) opens a profile dropdown — clicking it does NOT toggle FSM.
- **D-02:** When FSM is on, the button shows the active profile name in gold styling: `[ Family Friendly ▾ ]`
- **D-03:** When FSM is off, the button shows the current profile name in grey/fsm-off styling with ▾ still visible: `[ Family Friendly ▾ ]` (grey). This allows pre-selecting a profile while FSM is off.
- **D-04:** Exception for fresh install / no profile set: button shows `[ The Library is Closed ▾ ]` in grey. Default profile on first run is **Family Friendly**.
- **D-05:** The ▾ trigger occupies the right portion of the button. Clicking anywhere in the left/main area toggles FSM; clicking the ▾ area opens the dropdown. A visual separator (e.g., a faint vertical divider line) can distinguish the two zones.

### Profile dropdown
- **D-06:** Custom CSS dropdown — styled to match dashboard aesthetic (dark background, Courier Prime font, border matching `--border` CSS variable). Native `<select>` not used.
- **D-07:** Dropdown opens below the button, full-width aligned to the button.
- **D-08:** Dropdown shows all 4 profiles. Currently active/stored profile shows a ✓ (bullet) indicator. This applies whether FSM is on or off — the dropdown always reflects the stored profile.
- **D-09:** Clicking a profile in the dropdown: saves the selection to state.json immediately via a `POST /profile` API call, updates the button label, closes the dropdown. Does NOT change FSM state.
- **D-10:** Clicking outside the dropdown (or pressing Escape) closes it without changing selection.

### Profile persistence
- **D-11:** Active profile stored in `state.json` as `active_profile` field using the existing read-merge-write pattern. Example key values: `"family_friendly"`, `"adult_wholesome"`, `"adult_no_sexual"`, `"not_explicit"`.
- **D-12:** Profile survives service restart — state.json is read on daemon startup.
- **D-13:** When FSM turns on after being off, the profile that was stored (last-used or pre-selected) is restored automatically. No reset to a default.

### ContentChecker profile application
- **D-14:** Daemon reads `active_profile` from state.json each poll cycle (alongside `family_safe_mode`). When profile changes, daemon reconstructs ContentChecker with new settings for the next poll.
- **D-15:** Profile-to-ContentChecker mapping:
  - `family_friendly`: `min_severity=2`, drug_scanner active, sexual_content_scanner active, explicit check ON
  - `adult_wholesome`: `min_severity=3`, drug_scanner=None, sexual_content_scanner active, explicit check ON
  - `adult_no_sexual`: explicit check OFF (skip Tier 1), `min_severity=99` (never fires), drug_scanner=None, sexual_content_scanner active
  - `not_explicit`: explicit check ON, lyrics_service=None / profanity_scanner=None / drug_scanner=None / sexual_content_scanner=None (all lyric scanning off)
- **D-16:** "Explicit check OFF" for `adult_no_sexual` means ContentChecker skips Tier 1 (the `if track.get("explicit")` skip). This requires a new `explicit_skip: bool` parameter on ContentChecker.

### Dashboard profile display (PROF-04)
- **D-17:** The split button itself satisfies PROF-04 — the active profile name is always visible as the button label when FSM is on (and even when off). No separate display element needed.

### Claude's Discretion
- Exact CSS for the split button divider between toggle zone and ▾ zone
- Dropdown animation (fade-in vs instant appear)
- Whether profile mismatch between state.json and ContentChecker is detected by comparing the profile key vs re-reading each cycle
- `POST /profile` endpoint shape — suggest `{"profile": "family_friendly"}` matching existing verb-noun route conventions
- Web UI initial state injection pattern for profile (extend existing `__FSM_INITIAL__` pattern)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §Filter Profiles — PROF-01, PROF-02, PROF-03, PROF-04

### Source files to modify
- `content_checker.py` — Add `explicit_skip: bool = True` parameter to ContentChecker.__init__(); use it to gate Tier 1 check
- `daemon.py` lines 39–40 — `STATE_PATH` and `PROFANITY_MIN_SEVERITY` env var; add profile read alongside FSM read
- `daemon.py` lines 540–555 — ContentChecker instantiation in `main()`; make profile-aware and reconstruct on change
- `web_ui/main.py` lines 136–155 — `_load_state()` / `_save_state_merge()` helpers; add `POST /profile` endpoint using same pattern
- `web_ui/main.py` lines 162–175 — initial state injection; extend to inject `active_profile` alongside `__FSM_INITIAL__`
- `web_ui/templates/index.html` lines 140–165 — `#fsm-toggle` CSS; extend to split-button styling
- `web_ui/templates/index.html` lines 354–360 — `<button id="fsm-toggle">` HTML; add ▾ zone and dropdown element
- `web_ui/templates/index.html` lines 400–450 — `setFsmUI()` and FSM toggle JS; extend to handle profile label and split-button zones

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_load_state()` / `_save_state_merge()` in `web_ui/main.py` — identical read-merge-write pattern needed for profile saves
- `FSM_INITIAL` injection pattern (`html.replace("__FSM_INITIAL__", ...)`) — extend to also inject `__PROFILE_INITIAL__`
- `setFsmUI(enabled)` JS function — extend to accept profile name and update button label
- CSS variables: `--accent` (gold), `--surface-raised`, `--border`, `--text` — use for dropdown styling

### Established Patterns
- State mutations always use read-merge-write: read current state.json, merge new fields, write back atomically — never overwrite unrelated fields
- API routes use verb-noun pattern: `/fsm`, `/skip`, `/now-playing`, `/feed`
- Pydantic `BaseModel` for POST request bodies (see `FSMRequest`)
- Initial server-side state injected into HTML via placeholder replacement at serve time (not a separate API call on page load)

### Integration Points
- `daemon.py` poll_loop reads state.json each cycle — profile read fits here naturally
- ContentChecker is currently a fixed instance; needs to become profile-aware (reconstruct on profile change or accept profile config)
- `POST /profile` endpoint writes state.json → daemon picks up change within 1 poll cycle (~1s)
- The `active_profile` key in state.json is the source of truth for both daemon and web_ui

</code_context>

<specifics>
## Specific Ideas

- Split button: left zone = FSM toggle, right zone (▾) = dropdown trigger. A faint vertical separator visually distinguishes the two zones.
- Button text when FSM on: profile name (e.g., "Family Friendly ▾"). Button text when FSM off: profile name still shown (e.g., "Family Friendly ▾") but in grey/fsm-off styling — so parent can see what profile is queued up.
- Dropdown ✓ always shows the currently stored profile, regardless of FSM state.
- "The Library is Closed" text only appears on truly fresh install before any profile has been stored.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 16-filter-profiles*
*Context gathered: 2026-04-04*
