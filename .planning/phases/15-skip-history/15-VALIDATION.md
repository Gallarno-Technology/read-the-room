---
phase: 15
slug: skip-history
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-04
---

# Phase 15 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `tests/` directory (existing) |
| **Quick run command** | `python -m pytest tests/ -x -q` |
| **Full suite command** | `python -m pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/ -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 15-01-01 | 01 | 1 | HIST-03 | unit | `python -m pytest tests/test_feed_endpoint.py -v` | ❌ W0 | ⬜ pending |
| 15-01-02 | 01 | 1 | HIST-01 | unit | `python -m pytest tests/test_feed_endpoint.py -v` | ❌ W0 | ⬜ pending |
| 15-02-01 | 02 | 1 | HIST-01 | integration | `python -m pytest tests/test_feed_hydration.py -v` | ❌ W0 | ⬜ pending |
| 15-02-02 | 02 | 1 | HIST-02 | integration | `python -m pytest tests/test_feed_hydration.py -v` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_feed_endpoint.py` — stubs for HIST-01, HIST-03 (GET /feed endpoint, event filtering, limit)
- [ ] `tests/test_event_ids.py` — stubs for event ID generation and dedup
- [ ] Existing test infrastructure covers pytest — no new framework install needed

*Existing infrastructure covers framework requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Skip feed populates on page load in browser | HIST-01 | Requires browser rendering | Open dashboard, verify 20 items appear before any new skip |
| SSE reconnect retains feed items | HIST-02 | Requires SSE disconnect simulation | Kill SSE, reconnect, verify no blank-out |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
