---
phase: 16
slug: filter-profiles
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-04
---

# Phase 16 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.3.5 + pytest-asyncio 0.25.3 |
| **Config file** | none — pytest discovers tests/ automatically |
| **Quick run command** | `pytest tests/test_content_checker.py tests/test_web_ui_endpoints.py -x -q` |
| **Full suite command** | `pytest tests/ -x -q` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_content_checker.py tests/test_web_ui_endpoints.py -x -q`
- **After every plan wave:** Run `pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 16-01-01 | 01 | 1 | PROF-03 | unit | `pytest tests/test_content_checker.py -x -q -k explicit_skip` | ❌ W0 | ⬜ pending |
| 16-01-02 | 01 | 1 | PROF-03 | unit | `pytest tests/test_content_checker.py -x -q -k min_severity_99` | ❌ W0 | ⬜ pending |
| 16-01-03 | 01 | 1 | PROF-03 | unit | `pytest tests/test_content_checker.py -x -q -k no_drug_scanner` | ✅ | ⬜ pending |
| 16-02-01 | 02 | 2 | PROF-01, PROF-02 | unit | `pytest tests/test_web_ui_endpoints.py -x -q -k profile_initial` | ❌ W0 | ⬜ pending |
| 16-02-02 | 02 | 2 | PROF-02 | unit | `pytest tests/test_web_ui_endpoints.py -x -q -k profile` | ❌ W0 | ⬜ pending |
| 16-02-03 | 02 | 2 | PROF-02 | unit | `pytest tests/test_web_ui_endpoints.py -x -q -k invalid_profile` | ❌ W0 | ⬜ pending |
| 16-03-01 | 03 | 3 | PROF-04 | manual | Browser visual inspection | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_content_checker.py` — new cases: `explicit_skip=False` behavior for PROF-03
- [ ] `tests/test_web_ui_endpoints.py` — new cases: `POST /profile` endpoint (PROF-01, PROF-02)
- [ ] `tests/test_web_ui_endpoints.py` — new case: `__PROFILE_INITIAL__` injection in dashboard HTML (PROF-04)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Split button renders correctly — left toggles FSM, right opens dropdown | PROF-04 | DOM interaction / visual layout cannot be fully tested with pytest | Load dashboard; confirm ▾ zone opens dropdown without toggling FSM; confirm left click toggles FSM without opening dropdown |
| Dropdown shows ✓ on active profile | PROF-04 | Visual indicator requires browser inspection | Open dropdown; verify active profile has ✓ prefix |
| Profile label updates in button after selection | PROF-04 | DOM mutation check | Select a profile; verify button label updates to selected profile name |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
