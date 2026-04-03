# Requirements: Spotify Family Safe Mode

**Defined:** 2026-04-02
**Core Value:** Songs that violate family-safe rules are skipped automatically before children hear them — with zero manual effort when Family Safe Mode is on.

## v1.3 Requirements

Requirements for milestone v1.3: Drug & Sexual Reference Detection.

### Pipeline

- [ ] **PIPE-01**: `ContentChecker.check()` returns a named `TrackEvalResult` dataclass instead of a positional 3-tuple

### Drug Detection

- [ ] **DRUG-01**: System detects drug references in song lyrics using word-boundary keyword matching
- [ ] **DRUG-02**: Drug detection returns list of matched terms alongside the boolean signal
- [ ] **DRUG-03**: Skip is triggered when drug reference is detected and Family Safe Mode is active

### Sexual Content

- [ ] **SEXL-01**: System detects sexual content in song lyrics using word-boundary keyword matching
- [ ] **SEXL-02**: Sexual content detection returns list of matched terms alongside the boolean signal
- [ ] **SEXL-03**: Sexual content keyword list has no overlap with terms already in the profanity `SEVERITY_MAP`
- [ ] **SEXL-04**: Skip is triggered when sexual content is detected and Family Safe Mode is active

### Incident Log

- [ ] **LOG-01**: Skip events in `skip_events.jsonl` include boolean fields for all four signals: `explicit`, `profanity`, `drug_reference`, `sexual_content`

### Dashboard

- [ ] **UI-01**: Skip feed in dashboard displays distinct badges for drug reference and sexual content skip reasons

## Future Requirements

Requirements deferred to future milestones.

### v1.3 — Category Toggles

- **TOGL-01**: Parent can enable/disable drug reference detection independently via dashboard toggle
- **TOGL-02**: Parent can enable/disable sexual content detection independently via dashboard toggle
- **TOGL-03**: Toggle state persists across service restarts

### v2+

- **SENS-01**: Severity scoring within drug detection category (none / mild / explicit)
- **SENS-02**: Severity scoring within sexual content category
- **PROF-01**: Per-child profiles with age-based filtering tiers
- **ALC-01**: Alcohol reference detection category

## Out of Scope

| Feature | Reason |
|---------|--------|
| LLM/semantic detection | Explicitly excluded — implementation within existing pipeline; no LLM integration |
| Configurable per-category UI toggles | Deferred to v1.3 — detection ships first, controls come next milestone |
| Alcohol/violence detection | Separate categories requiring their own planning; not in this milestone |
| Now-playing dashboard card | Deferred — separate milestone focus |
| Manual skip button in dashboard | Deferred — separate milestone focus |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| PIPE-01 | Phase 6 | Pending |
| DRUG-01 | Phase 7 | Pending |
| DRUG-02 | Phase 7 | Pending |
| DRUG-03 | Phase 9 | Pending |
| SEXL-01 | Phase 8 | Pending |
| SEXL-02 | Phase 8 | Pending |
| SEXL-03 | Phase 8 | Pending |
| SEXL-04 | Phase 9 | Pending |
| LOG-01 | Phase 9 | Pending |
| UI-01 | Phase 10 | Pending |

**Coverage:**
- v1.2 requirements: 10 total
- Mapped to phases: 10
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-02*
*Last updated: 2026-04-02 after roadmap creation — all 10 requirements mapped; renumbered v1.2 → v1.3*
