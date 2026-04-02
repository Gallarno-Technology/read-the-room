---
phase: 4
slug: sonos-discovery-hardening
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-02
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio (existing `tests/test_skip_client.py` uses both) |
| **Config file** | none — `conftest.py` adds sys.path; pytest-asyncio configured via decorator |
| **Quick run command** | `python -m pytest tests/ -x -q` |
| **Full suite command** | `python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/ -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 4-W0-01 | Wave 0 | 0 | DISC-01, DISC-02, DISC-03 | unit stub | `python -m pytest tests/test_sonos_probe.py -x -q` | ❌ W0 | ⬜ pending |
| 4-W0-02 | Wave 0 | 0 | DISC-03 | unit | `python -m pytest tests/test_skip_client.py -x -q` | ✅ | ⬜ pending |
| 4-01-01 | 01 | 1 | DISC-01 | unit | `python -m pytest tests/test_sonos_probe.py -x -q` | ❌ W0 | ⬜ pending |
| 4-01-02 | 01 | 1 | DISC-02 | unit | `python -m pytest tests/test_sonos_probe.py -x -q` | ❌ W0 | ⬜ pending |
| 4-01-03 | 01 | 1 | DISC-03 | unit | `python -m pytest tests/test_sonos_probe.py tests/test_skip_client.py -x -q` | ❌ W0 / ✅ | ⬜ pending |
| 4-02-01 | 02 | 2 | DISC-01, DISC-02, DISC-03 | unit | `python -m pytest tests/ -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_sonos_probe.py` — stubs for DISC-01, DISC-02, DISC-03 probe behavior
- [ ] New test case in `tests/test_skip_client.py` — verifies updated warning text in `skip()` and `pause()` includes multicast hint (DISC-03)

*`tests/conftest.py` exists and adds sys.path. Verify pytest and pytest-asyncio are installed in venv before Wave 0.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| SSDP discovery on real multicast-enabled network | DISC-01 | Requires physical Sonos speaker and properly configured network | Start daemon without `SONOS_SPEAKER_IPS`; confirm speaker is discovered in logs within 10s |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
