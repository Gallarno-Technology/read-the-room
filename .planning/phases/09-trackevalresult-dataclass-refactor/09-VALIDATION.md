---
phase: 9
slug: trackevalresult-dataclass-refactor
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-03
---

# Phase 9 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (installed in .venv) |
| **Config file** | none (no pytest.ini; uses default discovery) |
| **Quick run command** | `.venv/bin/python -m pytest tests/test_daemon_events.py -q` |
| **Full suite command** | `.venv/bin/python -m pytest tests/ -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `.venv/bin/python -m pytest tests/test_daemon_events.py -q`
- **After every plan wave:** Run `.venv/bin/python -m pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green (2 pre-existing failures in test_skip_client.py acceptable — no new failures)
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 9-01-01 | 01 | 1 | PIPE-01 | unit | `.venv/bin/python -m pytest tests/test_daemon_events.py -q` | ✅ | ⬜ pending |
| 9-01-02 | 01 | 1 | PIPE-01 | smoke (grep) | `grep -c "action, reason, severity" daemon.py` → must return 0 | ✅ | ⬜ pending |
| 9-01-03 | 01 | 1 | PIPE-01 | smoke (grep) | `grep -cE 'return_value=\("allow\|return_value=\("skip' tests/test_daemon_events.py` → must return 0 | ✅ | ⬜ pending |
| 9-01-04 | 01 | 1 | PIPE-01 | regression | `.venv/bin/python -m pytest tests/ -q` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements.* The 10 mock sites in `tests/test_daemon_events.py` serve as the test coverage for PIPE-01 once updated to `TrackEvalResult(...)`. No new test files or framework installations needed.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Identical skip/pass/pause behavior to v1.2 | PIPE-01 | Behavioral regression not captured by unit asserts | Run daemon manually against a Sonos device with a known explicit track and confirm skip fires |

*All other phase behaviors have automated verification.*

---

## Baseline Test State (Pre-Refactor)

- 21 passed, 9 xpassed, 2 failed (pre-existing in `test_skip_client.py` — unrelated SoCo pause tests)
- Post-refactor: same counts must hold; the 2 pre-existing failures must not become new failures

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
