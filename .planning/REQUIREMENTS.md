# Requirements: Spotify Family Safe Mode

**Defined:** 2026-04-02
**Core Value:** Songs that violate family-safe rules are skipped automatically before children hear them — with zero manual effort when Family Safe Mode is on.

## v1.2 Requirements

Requirements for milestone v1.2: Now Playing Status.

### Daemon Extensions

- [x] **DAEM-01**: Daemon emits a `track_change` event on the SSE channel immediately when a new track is detected, before evaluation runs
- [x] **DAEM-02**: Daemon emits an `eval_result` event for every track after evaluation completes, regardless of outcome (passed, no-lyrics, or skipped)
- [x] **DAEM-03**: Daemon writes current track metadata and evaluation state to `now_playing.json` after each evaluation

### Now Playing Display

- [x] **NOW-01**: Dashboard displays a now-playing card showing current track name and artist
- [x] **NOW-02**: Card shows an evaluation state badge that updates in real-time (evaluating → passed / no-lyrics / skipped)
- [x] **NOW-03**: Badge shows "evaluating" immediately when a new track starts, before evaluation completes
- [x] **NOW-04**: Card is populated on fresh page load — not blank when opening the dashboard mid-session
- [x] **NOW-05**: Card is populated correctly after SSE reconnection
- [x] **NOW-06**: Card displays album artwork
- [x] **NOW-07**: Badge ignores `eval_result` events with a mismatched `track_id` (prevents stale results from rapid skips overwriting current state)

### Manual Skip

- [x] **SKIP-01**: Dashboard displays a manual skip button on the now-playing card
- [x] **SKIP-02**: User can skip the current track by clicking the skip button
- [x] **SKIP-03**: Manual skip does not increment the consecutive-skip counter
- [x] **SKIP-04**: Skip button is disabled while a skip request is in flight to prevent double-fire

## v1.3 Requirements

Requirements for milestone v1.3: Drug & Sexual Reference Detection.

### Pipeline

- [x] **PIPE-01**: `ContentChecker.check()` returns a named `TrackEvalResult` dataclass instead of a positional 3-tuple

### Drug Detection

- [x] **DRUG-01**: System detects drug references in song lyrics using word-boundary keyword matching
- [x] **DRUG-02**: `DrugScanner.scan()` returns a `(bool, list[str])` tuple — matched terms available for debug logging
- [ ] **DRUG-03**: Skip is triggered when a drug reference is detected and Family Safe Mode is active

### Sexual Content Detection

- [x] **SEXL-01**: System detects sexual content in song lyrics using word-boundary keyword matching
- [x] **SEXL-02**: `SexualContentScanner.scan()` returns a `(bool, list[str])` tuple — matched terms available for debug logging
- [x] **SEXL-03**: Sexual content keyword list has no overlap with terms already in the profanity `SEVERITY_MAP` (enforced by unit test)
- [ ] **SEXL-04**: Skip is triggered when sexual content is detected and Family Safe Mode is active

### Logging

- [ ] **LOG-01**: Skip events in `skip_events.jsonl` include boolean fields for all four signals: `explicit`, `profanity`, `drug_reference`, `sexual_content`
- [ ] **LOG-02**: Matched terms from drug/sexual scanners are logged to Python logger only — not written to `skip_events.jsonl`

### Dashboard

- [ ] **UI-01**: Skip feed displays distinct badge variants for drug-reference and sexual-content skip reasons

## Future Requirements

### v2+

- **TOGL-01**: Parent can enable/disable drug reference detection independently via dashboard
- **TOGL-02**: Parent can enable/disable sexual content detection independently via dashboard
- **ROOMS-01**: Support for multiple Sonos rooms without env var mapping
- **PROF-01**: Per-child profiles with age-based filtering tiers

## Out of Scope

| Feature | Reason |
|---------|--------|
| Manual skip counts toward 5-skip pause | Parent intent is deliberate — not an algorithmic cascade; bypass is correct behavior |
| Daemon-mediated skip IPC | web_ui calls Spotify directly via shared token cache — cleaner web-app separation |
| Evaluation history per track | Current track only; history is the existing skip feed |
| Matched terms in skip_events.jsonl | Debug logging sufficient; keeps JSONL schema clean and avoids leaking term lists to web_ui |
| Severity tiers for drug/sexual signals | No actionable effect for ages 3 and 7 — any detection warrants a skip; defer to v2+ |
| Phrase matching ("making love", "getting high") | Requires multi-word scan; defer to v2+ |
| Alcohol/tobacco as a separate signal | Too many false positives in mainstream pop; defer to per-category toggle milestone |
| Drug/sexual badges on now-playing eval card | Skip feed shows the history; now-playing card eval state (skipped) is sufficient |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| DAEM-01 | Phase 6 | Complete |
| DAEM-02 | Phase 6 | Complete |
| DAEM-03 | Phase 6 | Complete |
| NOW-01 | Phase 8 | Complete |
| NOW-02 | Phase 8 | Complete |
| NOW-03 | Phase 8 | Complete |
| NOW-04 | Phase 8 | Complete |
| NOW-05 | Phase 8 | Complete |
| NOW-06 | Phase 8 | Complete |
| NOW-07 | Phase 8 | Complete |
| SKIP-01 | Phase 8 | Complete |
| SKIP-02 | Phase 7 | Complete |
| SKIP-03 | Phase 7 | Complete |
| SKIP-04 | Phase 8 | Complete |
| PIPE-01 | Phase 9 | Complete |
| DRUG-01 | Phase 10 | Complete |
| DRUG-02 | Phase 10 | Complete |
| DRUG-03 | Phase 11 | Pending |
| SEXL-01 | Phase 10 | Complete |
| SEXL-02 | Phase 10 | Complete |
| SEXL-03 | Phase 10 | Complete |
| SEXL-04 | Phase 11 | Pending |
| LOG-01 | Phase 12 | Pending |
| LOG-02 | Phase 12 | Pending |
| UI-01 | Phase 13 | Pending |

**Coverage:**
- v1.3 requirements: 11 total
- Mapped to phases: 11 (roadmap complete)
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-02*
*Last updated: 2026-04-03 after v1.3 roadmap creation — all 11 requirements mapped*
