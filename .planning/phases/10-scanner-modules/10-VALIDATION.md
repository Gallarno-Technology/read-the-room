---
phase: 10
slug: scanner-modules
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-03
---

# Phase 10 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | none (pytest auto-discovers tests/) |
| **Quick run command** | `python -m pytest tests/test_drug_scanner.py tests/test_sexual_content_scanner.py -v` |
| **Full suite command** | `python -m pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_drug_scanner.py tests/test_sexual_content_scanner.py -v`
- **After every plan wave:** Run `python -m pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 10-01-01 | 01 | 1 | DRUG-01, DRUG-02 | unit | `python -m pytest tests/test_drug_scanner.py -v` | ❌ W0 | ⬜ pending |
| 10-01-02 | 01 | 1 | SEXL-01, SEXL-02, SEXL-03 | unit | `python -m pytest tests/test_sexual_content_scanner.py -v` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_drug_scanner.py` — stubs for DRUG-01, DRUG-02
- [ ] `tests/test_sexual_content_scanner.py` — stubs for SEXL-01, SEXL-02, SEXL-03

*Note: conftest.py already exists and adds project root to sys.path — no changes needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| None | — | — | — |

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
