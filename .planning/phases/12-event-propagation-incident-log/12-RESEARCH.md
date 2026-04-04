# Phase 12: Event Propagation & Incident Log - Research

**Researched:** 2026-04-04
**Domain:** Python dataclass extension, daemon event emission refactoring, JSONL schema evolution
**Confidence:** HIGH

## Summary

Phase 12 is a pure signal-propagation phase: the two new boolean signals (`drug_reference`, `sexual_content`) computed by Phases 10-11 must flow through every emit path in the daemon and appear in every `eval_result` SSE event and `skip` JSONL entry. No new scanning logic, no UI changes, no skip-decision changes.

The work splits into three coordinated changes: (1) extend `TrackEvalResult` with four boolean fields using `default=False`, (2) populate those fields at all `return TrackEvalResult(...)` sites in `content_checker.py`, and (3) extract a `_emit_eval_result` helper in `daemon.py` that calls both `_append_event` and `_write_now_playing` from one place — guaranteeing the four booleans appear on every emit path including the `fsm-off` path where no `result` object exists.

LOG-02 is the simplest change: demote two `log.info("[SCAN] ...")` lines in `content_checker.py` to `log.debug(...)`. Matched terms are already absent from `events.jsonl`; only the log level needs to change.

**Primary recommendation:** Extract `_emit_eval_result` helper first (D-04), then extend `TrackEvalResult` (D-01/D-02), then update the `skip` event payload (D-07), then demote log levels (D-11/D-12). Tests drive each step.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Add four boolean fields to `TrackEvalResult`: `explicit: bool`, `profanity: bool`, `drug_reference: bool`, `sexual_content: bool` — all with `default=False` to preserve backward compatibility with existing test mocks
- **D-02:** ContentChecker populates all four booleans at every return site from scan results (no re-derivation in daemon). Tier 1 (explicit flag) returns `explicit=True`, all others False. Lyrics-scan tiers populate all three scan results accurately even when multiple signals fire simultaneously
- **D-03:** All existing TrackEvalResult constructions in test files use keyword args — adding `default=False` fields requires no mock changes for existing tests; new tests add the new field assertions
- **D-04:** Extract a `_emit_eval_result(track_id, track_name, artist, album_art_url, eval_state, result)` helper that calls both `_append_event` and `_write_now_playing` in one place. All four existing eval_result emit sites (allow path, 5th-skip pause path, skip path, fsm-off path) are replaced with a single `_emit_eval_result(...)` call
- **D-05:** The helper builds the four-signal boolean payload from `result` fields. For the fsm-off path where no result exists, pass `None` as result — helper defaults all four booleans to False
- **D-06:** Every `eval_result` event in events.jsonl includes `drug_reference` and `sexual_content` boolean fields regardless of which code path fired
- **D-07:** Every `skip` type event in events.jsonl includes all four boolean fields: `explicit`, `profanity`, `drug_reference`, `sexual_content` (derived from the TrackEvalResult that triggered the skip)
- **D-08:** The `evaluating` track_change event does NOT include boolean fields — evaluation has not run yet; no placeholder padding needed at that stage
- **D-09:** The `fsm-off` eval_result event includes all four booleans defaulted to False — no scan ran; schema consistency matters for downstream dashboard parsing
- **D-10:** `now_playing.json` carries the same four boolean fields as the corresponding `eval_result` event — `_emit_eval_result` writes both atomically ensuring they stay in sync
- **D-11:** Demote the full `[SCAN]` log line (including prof_matched, drug_matched, sexual_matched terms) from INFO to DEBUG in content_checker.py — matched terms are visible at DEBUG and absent from events.jsonl
- **D-12:** Matched terms are already not written to events.jsonl (confirmed from code review) — no events.jsonl schema change needed to satisfy LOG-02; only the log level changes

### Claude's Discretion

- `_emit_eval_result` helper exact signature and parameter names
- Whether to include `severity` on the fsm-off event (keep 0, as currently coded)
- Test structure for new daemon event assertions (follow test_daemon_events.py patterns)

### Deferred Ideas (OUT OF SCOPE)

- Drug/sexual badge variants in dashboard skip feed — Phase 13 (UI-01)
- Per-category toggle UI (TOGL-01, TOGL-02) — v2+
- now-playing card badge variants for drug/sexual — explicitly out of scope per REQUIREMENTS.md
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| LOG-01 | Skip events in `skip_events.jsonl` include boolean fields for all four signals: `explicit`, `profanity`, `drug_reference`, `sexual_content` | D-06, D-07: `_emit_eval_result` helper propagates all four booleans from TrackEvalResult to every eval_result and skip event; the `skip` event payload picks them up from result fields |
| LOG-02 | Matched terms from drug/sexual scanners are logged to Python logger only — not written to `skip_events.jsonl` | D-11, D-12: two `log.info("[SCAN]...")` calls in content_checker.py demoted to `log.debug(...)`. Verified from code that matched terms are already absent from events.jsonl |
</phase_requirements>

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python `dataclasses` (stdlib) | stdlib (Python 3.7+) | `@dataclass(frozen=True)` + `field(default=False)` for TrackEvalResult extension | Already used; `frozen=True` with `default` via `field()` is idiomatic and valid |
| `logging` (stdlib) | stdlib | Change log level from INFO to DEBUG at two [SCAN] sites | Already wired in daemon.py and content_checker.py |
| `pytest` + `pytest-asyncio` | 9.0.2 / 0.25.3 (via .venv) | Test assertions on JSONL payload fields and TrackEvalResult fields | Already installed and passing 49/51 tests baseline |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `asyncio.Queue` | stdlib | `skip_event_queue` already exists; skip event payload update needed | At the `skip_event_queue.put_nowait(...)` call in daemon.py ~line 334 — update payload to include four booleans |

**Installation:** No new packages required. All dependencies are available in `.venv`.

**Version verification:** pytest 9.0.2 (confirmed by `.venv/bin/pytest --version`). pytest-asyncio 0.25.3 (from requirements.txt).

---

## Architecture Patterns

### Existing File Structure (no new files needed)
```
content_checker.py     # TrackEvalResult extension + log level change
daemon.py              # _emit_eval_result helper + 4 emit site replacements + skip payload
tests/
├── test_content_checker.py  # Add 4-boolean assertions on TrackEvalResult return values
└── test_daemon_events.py    # Add drug_reference/sexual_content assertions on event payloads
```

### Pattern 1: TrackEvalResult Extension with `field(default=False)`

**What:** Extend the frozen dataclass with four boolean fields that default to False. Existing test mocks (which omit the new fields) continue working unchanged.

**When to use:** Any time a frozen dataclass gains new optional fields without breaking callsites.

**Example (based on existing dataclass structure):**
```python
# content_checker.py
from dataclasses import dataclass, field

@dataclass(frozen=True)
class TrackEvalResult:
    action: str
    reason: str
    severity: int
    explicit: bool = field(default=False)
    profanity: bool = field(default=False)
    drug_reference: bool = field(default=False)
    sexual_content: bool = field(default=False)
```

Note: `frozen=True` is fully compatible with `field(default=False)`. The frozen constraint applies after construction, not to default values.

### Pattern 2: Return Site Populations in ContentChecker

**What:** At every `return TrackEvalResult(...)` site, pass the appropriate boolean values derived from local scan variables.

**Return sites confirmed in content_checker.py:**
1. Line 88 — Tier 1 explicit path: `explicit=True`, others `False`
2. Line 106 — Instrumental path: all `False` (no scan ran)
3. Line 115 — Lyrics unavailable path: all `False` (no scan ran)
4. Line 149 — Lyrics-scan path (profanity/drug/sexual): populate from `drug_detected` and `sexual_detected` locals; `profanity=(severity >= self.min_severity)`, `drug_reference=drug_detected`, `sexual_content=sexual_detected`, `explicit=False` (already passed Tier 1)
5. Line 158 — No lyrics service path: all `False`

**Key insight for the lyrics-scan return:** All four signals are already computed as locals (`severity`, `drug_detected`, `sexual_detected`) before the single `return TrackEvalResult(...)` at line 149. The booleans derive directly from those locals — no re-scanning.

### Pattern 3: `_emit_eval_result` Helper

**What:** A module-level function in daemon.py that replaces the duplicated `_append_event + _write_now_playing` pairs at all four emit sites. Accepts `result: Optional[TrackEvalResult]` and defaults all four booleans to False when result is None (fsm-off path).

**Signature (Claude's discretion):**
```python
def _emit_eval_result(
    track_id: str,
    track_name: str,
    artist: str,
    album_art_url: Optional[str],
    eval_state: str,
    severity: int,
    result: Optional["TrackEvalResult"],
) -> None:
```

**Payload construction inside helper:**
```python
explicit = result.explicit if result is not None else False
profanity = result.profanity if result is not None else False
drug_reference = result.drug_reference if result is not None else False
sexual_content = result.sexual_content if result is not None else False

_append_event({
    "type": "eval_result",
    "track_id": track_id,
    "eval_state": eval_state,
    "severity": severity,
    "explicit": explicit,
    "profanity": profanity,
    "drug_reference": drug_reference,
    "sexual_content": sexual_content,
    "timestamp": time.strftime("%H:%M:%S"),
})
_write_now_playing({
    "track_id": track_id,
    "track": track_name,
    "artist": artist,
    "album_art_url": album_art_url,
    "eval_state": eval_state,
    "severity": severity,
    "explicit": explicit,
    "profanity": profanity,
    "drug_reference": drug_reference,
    "sexual_content": sexual_content,
    "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
})
```

### Pattern 4: `skip` Event Payload Update

**What:** The `skip` event written via `_append_event` at daemon.py ~line 341 must include all four boolean fields. The `skip_event_queue.put_nowait(...)` at ~line 334 (legacy SSE queue) should also be updated for consistency, though dashboard skip feed rendering is Phase 13 (UI-01) scope.

**Current skip event (lines 341-347):**
```python
_append_event({
    "type": "skip",
    "track": track["name"],
    "artist": track["artists"][0]["name"],
    "reason": result.reason,
    "timestamp": time.strftime("%H:%M:%S"),
})
```

**Updated (add four booleans from result):**
```python
_append_event({
    "type": "skip",
    "track": track["name"],
    "artist": track["artists"][0]["name"],
    "reason": result.reason,
    "explicit": result.explicit,
    "profanity": result.profanity,
    "drug_reference": result.drug_reference,
    "sexual_content": result.sexual_content,
    "timestamp": time.strftime("%H:%M:%S"),
})
```

### Pattern 5: Log Level Demotion

**What:** Two `log.info("[SCAN] ...")` calls in content_checker.py become `log.debug(...)`.

**Confirmed locations from code review:**
- Line 83: Tier 1 explicit path — `log.info("[SCAN] track=%r artist=%r severity=3 matched=[] action=skip", ...)`
- Line 138: Lyrics-scan path — `log.info("[SCAN] track=%r artist=%r severity=%d prof_matched=%s drug_matched=%s sexual_matched=%s action=%s", ...)`

Also demote the instrumental and lyrics-unavailable [SCAN] lines (lines 101, 110) for consistency — all [SCAN] log lines should be at the same level.

**Note from CONTEXT.md D-11:** The directive specifically mentions the `[SCAN]` log line including matched terms. The two primary lines (83 and 138) are the ones containing matched-term data. Lines 101 and 110 do not contain matched terms (they log `matched=[]`) so their level is at Claude's discretion — staying consistent is the safest choice.

### Anti-Patterns to Avoid

- **Re-deriving booleans in daemon from result.reason:** D-02 is explicit that daemon does NOT re-derive. ContentChecker populates the booleans; daemon passes them through.
- **Short-circuiting field defaults:** Do not use `getattr(result, "drug_reference", False)` — the field will always exist once D-01 is implemented. Use direct attribute access.
- **Updating only `_append_event` and not `_write_now_playing`:** Both must carry the four booleans identically (D-10 / success criterion 4). The helper enforces this.
- **Forgetting the `skip_event_queue` legacy path:** The `put_nowait` at ~line 334 is separate from `_append_event`. It needs the four booleans too, or Phase 13 will have mismatched payloads.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Default field values on frozen dataclass | Custom __init__ override | `field(default=False)` from stdlib `dataclasses` | frozen=True + field() is standard; custom __init__ breaks frozen semantics |
| Atomic now_playing + events.jsonl sync | Two separate helpers with duplicated logic | `_emit_eval_result` helper (D-04) | Existing pattern already proven; helper is the correct DRY consolidation |

---

## Common Pitfalls

### Pitfall 1: `frozen=True` Misunderstood
**What goes wrong:** Developer attempts `TrackEvalResult.drug_reference = True` after construction — raises `FrozenInstanceError`.
**Why it happens:** Confusing dataclass field defaults (set at construction time) with post-construction mutation.
**How to avoid:** All boolean values are passed at `TrackEvalResult(...)` construction time. Never mutate after creation.
**Warning signs:** Any code assigning to a TrackEvalResult attribute after construction.

### Pitfall 2: Forgetting the No-Lyrics-Service Return Site
**What goes wrong:** Four of the five return sites in `content_checker.py` are updated; the `no_lyrics_service` path at line 158 is missed. Tests pass because unit tests don't exercise that branch.
**Why it happens:** The no-lyrics-service branch is a configuration fallback, not exercised in standard tests.
**How to avoid:** After updating all return sites, `grep` for all `return TrackEvalResult(` occurrences and verify each one includes the four boolean fields.
**Warning signs:** `grep content_checker.py "return TrackEvalResult"` returns more than one result without all four boolean args.

### Pitfall 3: `skip_event_queue` Left Without Four-Boolean Update
**What goes wrong:** `events.jsonl` skip events have the four booleans, but the in-memory SSE `skip_event_queue` payloads (line ~334) do not. Phase 13 dashboard reads from `events.jsonl` (already covered) but the live SSE stream would be inconsistent.
**Why it happens:** The queue and the JSONL write are two separate code paths and are easy to update only one of.
**How to avoid:** Update the `skip_event_queue.put_nowait(...)` call alongside the `_append_event` call when updating the skip event payload.
**Warning signs:** The `put_nowait` dict does not include `drug_reference` key.

### Pitfall 4: test_daemon_events.py xfail Markers Masking Real Failures
**What goes wrong:** Existing tests marked `xfail` that now pass (xpass) may not be updated to remove the marker. After Phase 12, all `xfail` tests in `test_daemon_events.py` should either be removed or have their `strict=False` changed to `strict=True`.
**Why it happens:** The tests were written as TDD stubs for Phase 6. The implementation already passes them (9 xpassed in current baseline).
**How to avoid:** After Phase 12 implementation, remove `@pytest.mark.xfail` from tests that reliably pass. This is not a blocker but is good hygiene.
**Warning signs:** `pytest -v` output shows `XPASS` on multiple tests.

### Pitfall 5: Profanity Boolean Derivation
**What goes wrong:** `profanity` boolean is set to `True` only when `reason == "profanity"` — this loses the information that profanity was detected but drug_reference won priority (since priority ordering is profanity > drug > sexual).
**Why it happens:** The `reason` field only captures the winning signal. `profanity` should reflect whether profanity was detected (severity >= min_severity), not whether profanity was the skip reason.
**How to avoid:** Set `profanity=(severity >= self.min_severity)` unconditionally at the lyrics-scan return site, regardless of what `reason` was chosen.
**Warning signs:** A track that triggers profanity AND drug_reference gets `profanity=False` in TrackEvalResult.

---

## Code Examples

### TrackEvalResult with four booleans (dataclasses pattern)
```python
# content_checker.py — verified against existing dataclass structure
from dataclasses import dataclass, field

@dataclass(frozen=True)
class TrackEvalResult:
    action: str
    reason: str
    severity: int
    explicit: bool = field(default=False)
    profanity: bool = field(default=False)
    drug_reference: bool = field(default=False)
    sexual_content: bool = field(default=False)
```

### Lyrics-scan return site (the critical multi-signal case)
```python
# content_checker.py lines ~117-149 — after Phase 12
return TrackEvalResult(
    action=action,
    reason=reason,
    severity=severity,
    explicit=False,                           # Passed Tier 1 check already
    profanity=(severity >= self.min_severity),  # True if profanity threshold met
    drug_reference=drug_detected,
    sexual_content=sexual_detected,
)
```

### Test assertion pattern for new fields (from test_daemon_events.py style)
```python
# tests/test_daemon_events.py — new assertions following existing pattern
eval_result_lines = [l for l in lines if l.get("type") == "eval_result"]
assert eval_result_lines[0]["drug_reference"] == False
assert eval_result_lines[0]["sexual_content"] == False
assert eval_result_lines[0]["explicit"] == False
assert eval_result_lines[0]["profanity"] == False
```

### Test assertion pattern for TrackEvalResult fields (from test_content_checker.py style)
```python
# tests/test_content_checker.py — new assertions
result = await checker.check(_make_track())
assert result.drug_reference == True
assert result.sexual_content == False
assert result.profanity == False
assert result.explicit == False
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `TrackEvalResult` with 3 fields (action, reason, severity) | 7 fields (+ explicit, profanity, drug_reference, sexual_content) | Phase 12 | All emit sites must use new fields; no backward compat issue due to `default=False` |
| 4 separate `_append_event + _write_now_playing` pairs | 1 `_emit_eval_result` helper called from all 4 sites | Phase 12 | Eliminates drift risk between events.jsonl and now_playing.json |
| `[SCAN]` lines at INFO level | `[SCAN]` lines at DEBUG level | Phase 12 | Matched terms no longer visible in default Docker log output; visible with `--log-level=DEBUG` |

---

## Open Questions

1. **Should `skip_event_queue.put_nowait(...)` be updated alongside the JSONL `skip` event?**
   - What we know: Phase 13 (UI-01) will render skip feed badges for drug/sexual. The SSE stream feeding the dashboard reads from this queue.
   - What's unclear: Whether Phase 13 reads from `events.jsonl` on load (confirmed) or relies on the live SSE queue for badge data too.
   - Recommendation: Update `skip_event_queue.put_nowait(...)` with the four booleans in Phase 12. Cost is one dict key addition; risk of not doing it is Phase 13 getting incomplete data from the live queue.

2. **xfail markers in test_daemon_events.py**
   - What we know: 9 tests are currently `xfail(strict=False)` but they all pass (XPASS) with the current implementation.
   - What's unclear: Whether the planner should include a cleanup task to remove the stale xfail markers.
   - Recommendation: Include as a task in Phase 12 (test hygiene). The markers no longer reflect reality and create false confidence.

---

## Environment Availability

Step 2.6: SKIPPED for external tooling. All dependencies are internal Python code changes. The `.venv` contains all required packages.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| pytest | Test validation | ✓ | 9.0.2 | — |
| pytest-asyncio | Async test support | ✓ | 0.25.3 | — |
| Python venv | Running tests | ✓ | `.venv/bin/pytest` | — |

**Baseline test state:** 49 passed, 2 failed (pre-existing in test_skip_client.py — unrelated), 9 xpassed.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 + pytest-asyncio 0.25.3 |
| Config file | none (uses conftest.py for sys.path) |
| Quick run command | `.venv/bin/pytest tests/test_content_checker.py tests/test_daemon_events.py -x` |
| Full suite command | `.venv/bin/pytest tests/ -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LOG-01 | eval_result events include drug_reference and sexual_content booleans | unit | `.venv/bin/pytest tests/test_daemon_events.py -k "drug_reference or sexual_content" -x` | ❌ Wave 0 |
| LOG-01 | skip events include all four boolean fields | unit | `.venv/bin/pytest tests/test_daemon_events.py -k "skip" -x` | ❌ Wave 0 |
| LOG-01 | fsm-off eval_result includes four booleans defaulted to False | unit | `.venv/bin/pytest tests/test_daemon_events.py::test_eval_result_fsm_off -x` | ✅ extend |
| LOG-01 | now_playing.json carries same four fields as eval_result event | unit | `.venv/bin/pytest tests/test_daemon_events.py::test_now_playing_final_state -x` | ✅ extend |
| LOG-01 | TrackEvalResult populates drug_reference and sexual_content at lyrics-scan return | unit | `.venv/bin/pytest tests/test_content_checker.py -k "drug or sexual" -x` | ✅ extend |
| LOG-02 | Matched terms appear in DEBUG log output, not INFO | unit | `.venv/bin/pytest tests/test_content_checker.py -k "log_level or debug" -x` | ❌ Wave 0 |
| LOG-02 | events.jsonl skip events do not contain matched terms | unit | verify existing skip event schema tests | ✅ existing coverage |

### Sampling Rate
- **Per task commit:** `.venv/bin/pytest tests/test_content_checker.py tests/test_daemon_events.py -x`
- **Per wave merge:** `.venv/bin/pytest tests/ -v`
- **Phase gate:** Full suite green (except the 2 pre-existing skip_client failures) before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_daemon_events.py` — add `test_eval_result_includes_drug_reference_sexual_content` covering LOG-01 for all four emit paths
- [ ] `tests/test_daemon_events.py` — add `test_skip_event_includes_four_booleans` covering LOG-01 skip schema
- [ ] `tests/test_daemon_events.py` — extend `test_eval_result_fsm_off` to assert four booleans are False
- [ ] `tests/test_daemon_events.py` — extend `test_now_playing_final_state` to assert four booleans in now_playing.json
- [ ] `tests/test_content_checker.py` — extend drug/sexual test cases to assert `result.drug_reference == True` / `result.sexual_content == True`
- [ ] `tests/test_content_checker.py` — add `test_scan_log_at_debug_level` using `caplog` to assert `[SCAN]` lines at DEBUG not INFO

---

## Sources

### Primary (HIGH confidence)
- Direct code read of `content_checker.py` — TrackEvalResult structure, all 5 return sites, log lines at 83 and 138
- Direct code read of `daemon.py` — all 4 eval_result emit sites confirmed at lines ~258, ~303, ~350, ~376; skip event at ~341; `skip_event_queue.put_nowait` at ~334
- Direct code read of `tests/test_daemon_events.py` — 15 tests, assertion patterns, xfail markers
- Direct code read of `tests/test_content_checker.py` — 5 tests, TrackEvalResult construction patterns
- Python stdlib docs (known) — `dataclasses.field(default=...)` with `frozen=True` is valid
- `.venv/bin/pytest --version` — confirmed pytest 9.0.2
- `.venv/bin/pytest tests/ -v` — confirmed baseline: 49 passed, 2 failed (pre-existing), 9 xpassed

### Secondary (MEDIUM confidence)
- `requirements.txt` — pytest-asyncio 0.25.3 confirmed
- `12-CONTEXT.md` — all locked decisions; canonical reference for planning

### Tertiary (LOW confidence)
- None — all claims verified from direct code inspection or confirmed decisions in CONTEXT.md

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new libraries; all changes are stdlib + already-installed packages
- Architecture: HIGH — all emit sites confirmed by direct code read with line numbers; patterns verified from existing code
- Pitfalls: HIGH — identified from direct inspection of code paths and dataclass semantics
- Test gaps: HIGH — verified by running pytest collect and confirming which assertions are missing

**Research date:** 2026-04-04
**Valid until:** 2026-05-04 (stable domain — no external API changes possible here)
