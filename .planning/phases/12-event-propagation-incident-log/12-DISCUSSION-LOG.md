# Phase 12: Event Propagation & Incident Log - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the discussion.

**Date:** 2026-04-04
**Phase:** 12-event-propagation-incident-log
**Mode:** discuss

## Gray Areas Analyzed

| Area | Gray Area | Resolution |
|------|-----------|------------|
| TrackEvalResult extension | 4 booleans (explicit+profanity+drug+sexual) vs 2 (drug+sexual only) | User selected: 4 fields with default=False |
| Matched terms log level | Split INFO+DEBUG vs demote full [SCAN] line to DEBUG | User selected: demote full [SCAN] line to DEBUG |
| emit_eval_result helper | Where to place, what signature | Locked from STATE.md; Claude's discretion for exact signature |
| FSM-off boolean padding | Whether to pad non-evaluated events with False booleans | Resolved: fsm-off gets False defaults; evaluating event omits (not yet evaluated) |

## Discussion

### TrackEvalResult extension scope

**Gray area:** LOG-01 requires all four signals in events.jsonl. The no-short-circuit contract from Phase 11 means profanity + drug could both fire simultaneously, but TrackEvalResult only stores the winning `reason`. To preserve all signal data, all four booleans must be on the result.

**User decision:** 4 fields (explicit, profanity, drug_reference, sexual_content) all with `default=False` — ContentChecker populates from scan results, daemon reads directly.

**Why:** Cleanest approach; no re-derivation in daemon; captures simultaneous multi-signal firings.

### Matched terms log level

**Gray area:** LOG-02 says matched terms at DEBUG. Current `[SCAN]` INFO line includes prof_matched, drug_matched, sexual_matched.

**User decision:** Demote full `[SCAN]` line to DEBUG — simpler change; matched terms are visible at DEBUG.

**Note:** The explicit-path `[SCAN]` log (line ~83) and lyrics-scan `[SCAN]` log (line ~138) both get demoted to DEBUG.

## Locked Decisions (from prior context, not re-asked)

- Extract `_emit_eval_result` helper covering all 4 emit sites (STATE.md decision)
- Matched terms NOT in events.jsonl (REQUIREMENTS.md out-of-scope, already absent from code)
- Drug/sexual badges on now-playing card NOT in scope (REQUIREMENTS.md out-of-scope)
- No scope extension to Phase 13 dashboard badge work
