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

- [ ] **NOW-01**: Dashboard displays a now-playing card showing current track name and artist
- [ ] **NOW-02**: Card shows an evaluation state badge that updates in real-time (evaluating → passed / no-lyrics / skipped)
- [ ] **NOW-03**: Badge shows "evaluating" immediately when a new track starts, before evaluation completes
- [ ] **NOW-04**: Card is populated on fresh page load — not blank when opening the dashboard mid-session
- [ ] **NOW-05**: Card is populated correctly after SSE reconnection
- [ ] **NOW-06**: Card displays album artwork
- [ ] **NOW-07**: Badge ignores `eval_result` events with a mismatched `track_id` (prevents stale results from rapid skips overwriting current state)

### Manual Skip

- [ ] **SKIP-01**: Dashboard displays a manual skip button on the now-playing card
- [ ] **SKIP-02**: User can skip the current track by clicking the skip button
- [ ] **SKIP-03**: Manual skip does not increment the consecutive-skip counter
- [ ] **SKIP-04**: Skip button is disabled while a skip request is in flight to prevent double-fire

## Future Requirements

### v1.3 — Drug & Sexual Reference Detection

- **DRUG-01**: System detects drug references in song lyrics using word-boundary keyword matching
- **DRUG-02**: Drug detection returns list of matched terms alongside the boolean signal
- **DRUG-03**: Skip is triggered when drug reference is detected and Family Safe Mode is active
- **SEXL-01**: System detects sexual content in song lyrics using word-boundary keyword matching
- **SEXL-02**: Sexual content detection returns list of matched terms alongside the boolean signal
- **SEXL-03**: Sexual content keyword list has no overlap with terms already in the profanity `SEVERITY_MAP`
- **SEXL-04**: Skip is triggered when sexual content is detected and Family Safe Mode is active
- **LOG-01**: Skip events in `skip_events.jsonl` include boolean fields for all four signals: `explicit`, `profanity`, `drug_reference`, `sexual_content`
- **UI-01**: Skip feed in dashboard displays distinct badges for drug reference and sexual content skip reasons
- **PIPE-01**: `ContentChecker.check()` returns a named `TrackEvalResult` dataclass instead of a positional 3-tuple

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

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| DAEM-01 | Phase 6 | Complete |
| DAEM-02 | Phase 6 | Complete |
| DAEM-03 | Phase 6 | Complete |
| NOW-01 | Phase 8 | Pending |
| NOW-02 | Phase 8 | Pending |
| NOW-03 | Phase 8 | Pending |
| NOW-04 | Phase 8 | Pending |
| NOW-05 | Phase 8 | Pending |
| NOW-06 | Phase 8 | Pending |
| NOW-07 | Phase 8 | Pending |
| SKIP-01 | Phase 8 | Pending |
| SKIP-02 | Phase 7 | Pending |
| SKIP-03 | Phase 7 | Pending |
| SKIP-04 | Phase 8 | Pending |

**Coverage:**
- v1.2 requirements: 14 total
- Mapped to phases: 14
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-02*
*Last updated: 2026-04-02 after roadmap creation*
