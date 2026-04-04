---
phase: 11
slug: contentchecker-pipeline-integration
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-03
---

# Phase 11 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | none — conftest.py adds project root to sys.path |
| **Quick run command** | `.venv/bin/pytest tests/test_content_checker.py -x` |
| **Full suite command** | `.venv/bin/pytest tests/ -x` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `.venv/bin/pytest tests/test_content_checker.py -x`
- **After every plan wave:** Run `.venv/bin/pytest tests/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green (note: 1 pre-existing failure in `test_skip_client.py::test_soco_pause_uses_cached_ip` is acceptable — no new failures)
- **Max feedback latency:** ~5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 11-01-01 | 01 | 0 | DRUG-03, SEXL-04 | integration | `.venv/bin/pytest tests/test_content_checker.py -x` | ❌ W0 | ⬜ pending |
| 11-02-01 | 02 | 1 | DRUG-03 | integration | `.venv/bin/pytest tests/test_content_checker.py::test_drug_reference_triggers_skip -x` | ✅ | ⬜ pending |
| 11-02-02 | 02 | 1 | SEXL-04 | integration | `.venv/bin/pytest tests/test_content_checker.py::test_sexual_content_triggers_skip -x` | ✅ | ⬜ pending |
| 11-02-03 | 02 | 1 | SC-3 | integration | `.venv/bin/pytest tests/test_content_checker.py::test_all_signals_fire_all_scans_run -x` | ✅ | ⬜ pending |
| 11-02-04 | 02 | 1 | SC-4 | integration | `.venv/bin/pytest tests/test_content_checker.py -x` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_content_checker.py` — stubs for DRUG-03, SEXL-04, Success Criteria 3 and 4

*Existing infrastructure (pytest + pytest-asyncio) already installed in `.venv` — no framework install needed.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
