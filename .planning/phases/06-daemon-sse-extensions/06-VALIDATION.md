---
phase: 6
slug: daemon-sse-extensions
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-02
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | `pytest.ini` |
| **Quick run command** | `.venv/bin/pytest tests/test_daemon_events.py -x -q` |
| **Full suite command** | `.venv/bin/pytest -x -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `.venv/bin/pytest tests/test_daemon_events.py -x -q`
- **After every plan wave:** Run `.venv/bin/pytest -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 6-01-01 | 01 | 0 | DAEM-01, DAEM-02, DAEM-03 | unit | `.venv/bin/pytest tests/test_daemon_events.py -x -q` | ❌ W0 | ⬜ pending |
| 6-02-01 | 02 | 1 | DAEM-01 | unit | `.venv/bin/pytest tests/test_daemon_events.py::test_track_change_emitted_before_check tests/test_daemon_events.py::test_track_change_schema -x` | ❌ W0 | ⬜ pending |
| 6-03-01 | 03 | 2 | DAEM-02 | unit | `.venv/bin/pytest tests/test_daemon_events.py::test_eval_result_passed tests/test_daemon_events.py::test_eval_result_skipped tests/test_daemon_events.py::test_eval_result_fsm_off tests/test_daemon_events.py::test_eval_result_not_emitted_on_skip_failure -x` | ❌ W0 | ⬜ pending |
| 6-04-01 | 04 | 2 | DAEM-03 | unit | `.venv/bin/pytest tests/test_daemon_events.py::test_now_playing_evaluating tests/test_daemon_events.py::test_now_playing_final_state -x` | ❌ W0 | ⬜ pending |
| 6-05-01 | 05 | 3 | D-01 | unit | `.venv/bin/pytest tests/test_daemon_events.py::test_existing_events_unaffected -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_daemon_events.py` — stubs for DAEM-01, DAEM-02, DAEM-03, and D-01 regression

*Existing `tests/conftest.py` and pytest infrastructure cover everything else — no new framework install needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| events.jsonl file rename visible in running containers | D-01 | Requires live Docker environment | Run daemon + web_ui containers; verify `docker exec` shows `data/events.jsonl` exists and `data/skip_events.jsonl` does not |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
