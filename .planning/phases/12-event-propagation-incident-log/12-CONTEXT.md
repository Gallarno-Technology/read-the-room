# Phase 12: Event Propagation & Incident Log - Context

**Gathered:** 2026-04-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Propagate the drug_reference and sexual_content booleans (already computed in ContentChecker's five-tier pipeline) through every daemon event emission path and now_playing.json write. Every eval_result SSE event and every events.jsonl entry must carry the complete four-signal record: explicit, profanity, drug_reference, sexual_content.

No new scanning, no UI changes, no skip logic changes — this phase is purely signal propagation and schema completion.

</domain>

<decisions>
## Implementation Decisions

### TrackEvalResult Extension
- **D-01:** Add four boolean fields to `TrackEvalResult`: `explicit: bool`, `profanity: bool`, `drug_reference: bool`, `sexual_content: bool` — all with `default=False` to preserve backward compatibility with existing test mocks
- **D-02:** ContentChecker populates all four booleans at every return site from scan results (no re-derivation in daemon). Tier 1 (explicit flag) returns `explicit=True`, all others False. Lyrics-scan tiers populate all three scan results accurately even when multiple signals fire simultaneously
- **D-03:** All existing TrackEvalResult constructions in test files use keyword args — adding `default=False` fields requires no mock changes for existing tests; new tests add the new field assertions

### `_emit_eval_result` Helper (Locked — STATE.md)
- **D-04:** Extract a `_emit_eval_result(track_id, track_name, artist, album_art_url, eval_state, result)` helper that calls both `_append_event` and `_write_now_playing` in one place. All four existing eval_result emit sites (allow path, 5th-skip pause path, skip path, fsm-off path) are replaced with a single `_emit_eval_result(...)` call
- **D-05:** The helper builds the four-signal boolean payload from `result` fields. For the fsm-off path where no result exists, pass `None` as result — helper defaults all four booleans to False

### events.jsonl Schema (LOG-01)
- **D-06:** Every `eval_result` event in events.jsonl includes `drug_reference` and `sexual_content` boolean fields regardless of which code path fired
- **D-07:** Every `skip` type event in events.jsonl includes all four boolean fields: `explicit`, `profanity`, `drug_reference`, `sexual_content` (derived from the TrackEvalResult that triggered the skip)
- **D-08:** The `evaluating` track_change event does NOT include boolean fields — evaluation has not run yet; no placeholder padding needed at that stage
- **D-09:** The `fsm-off` eval_result event includes all four booleans defaulted to False — no scan ran; schema consistency matters for downstream dashboard parsing

### now_playing.json Schema (Success Criteria 4)
- **D-10:** `now_playing.json` carries the same four boolean fields as the corresponding `eval_result` event — `_emit_eval_result` writes both atomically ensuring they stay in sync

### Matched Terms Logging (LOG-02)
- **D-11:** Demote the full `[SCAN]` log line (including prof_matched, drug_matched, sexual_matched terms) from INFO to DEBUG in content_checker.py — matched terms are visible at DEBUG and absent from events.jsonl
- **D-12:** Matched terms are already not written to events.jsonl (confirmed from code review) — no events.jsonl schema change needed to satisfy LOG-02; only the log level changes

### Claude's Discretion
- `_emit_eval_result` helper exact signature and parameter names
- Whether to include `severity` on the fsm-off event (keep 0, as currently coded)
- Test structure for new daemon event assertions (follow test_daemon_events.py patterns)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §LOG-01, LOG-02 — exact schema requirements for events.jsonl and matched-term log behavior
- `.planning/REQUIREMENTS.md` §Out of Scope — "Matched terms in skip_events.jsonl: debug logging sufficient; keeps JSONL schema clean" (confirms D-12)
- `.planning/REQUIREMENTS.md` §Out of Scope — "Drug/sexual badges on now-playing eval card: Skip feed shows the history; now-playing card eval state (skipped) is sufficient" (NOT in scope for this phase)

### Source files to modify
- `content_checker.py` — TrackEvalResult dataclass (add 4 boolean fields), all `return TrackEvalResult(...)` call sites, `[SCAN]` log level change
- `daemon.py` — Extract `_emit_eval_result` helper, update all 4 eval_result emit sites, update `skip` event payload

### Test files to update
- `tests/test_daemon_events.py` — Add assertions for drug_reference and sexual_content fields on eval_result events; update skip event assertions for four-signal schema
- `tests/test_content_checker.py` — Assert new boolean fields on TrackEvalResult return values for drug/sexual/explicit/profanity paths

### Locked decisions from STATE.md
- `.planning/STATE.md` — "Extract `_emit_eval_result` helper first so all 4 daemon emit sites are covered in one change; helper must call both `_append_event` and `_write_now_playing` to keep events.jsonl and now_playing.json in sync"

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `daemon.py:_append_event()` — appends JSON line to `data/events.jsonl`; use as-is inside new helper
- `daemon.py:_write_now_playing()` — overwrites `data/now_playing.json`; use as-is inside new helper
- `daemon.py:_eval_state_from_result()` — maps (action, reason) → eval_state string; already used at all emit sites, reuse in helper

### Established Patterns
- `TrackEvalResult` is a `@dataclass(frozen=True)` — new fields must use `field(default=False)` from `dataclasses` module (frozen=True + default is valid Python)
- All four `eval_result` emit sites in daemon.py follow an identical pattern: `_append_event({...})` then `_write_now_playing({...})` — trivially extractable into a helper
- Test mocks construct `TrackEvalResult(action=..., reason=..., severity=...)` without keyword-exhaustive style — default=False fields won't break them
- `test_daemon_events.py` asserts specific fields on parsed JSONL lines — new field assertions follow same `assert eval_result_lines[0]["drug_reference"] == False` pattern

### Integration Points
- All scan results (`drug_detected`, `sexual_detected`, `severity`) are local variables in `content_checker.py:check()` — already computed before the `return TrackEvalResult(...)` calls; just add them to the return
- The `skip_event_queue.put_nowait({...})` call at daemon.py line 334 (legacy SSE queue) may also need updating if dashboard reads skip events from there — verify during planning

### Current emit site inventory (daemon.py)
1. Line ~258: allow path → `eval_state = _eval_state_from_result(...)` → "passed" or "no-lyrics"
2. Line ~303: 5th-skip pause path → `eval_state = "paused"`
3. Line ~350: successful skip path → `eval_state = "skipped"`
4. Line ~376: FSM-off path → `eval_state = "fsm-off"`, no `result` available

</code_context>

<specifics>
## Specific Ideas

- The [SCAN] log level change to DEBUG applies to the full log line in content_checker.py — both the existing INFO log at line 83 (explicit path) and the INFO log at line 138 (lyrics scan path)
- For the fsm-off emit site, `result` is None — the helper receives None and defaults all four booleans to False (explicit=False, profanity=False, drug_reference=False, sexual_content=False)

</specifics>

<deferred>
## Deferred Ideas

- Drug/sexual badge variants in dashboard skip feed — Phase 13 (UI-01)
- Per-category toggle UI (TOGL-01, TOGL-02) — v2+
- now-playing card badge variants for drug/sexual — explicitly out of scope per REQUIREMENTS.md

</deferred>

---

*Phase: 12-event-propagation-incident-log*
*Context gathered: 2026-04-04*
