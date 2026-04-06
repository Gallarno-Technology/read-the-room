---
phase: 19
slug: mobile-polish
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-06
---

# Phase 19 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | none (uses defaults; conftest.py adds project root to sys.path) |
| **Quick run command** | `.venv/bin/python3 -m pytest tests/test_mobile_polish.py -x -q` |
| **Full suite command** | `.venv/bin/python3 -m pytest tests/ -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `.venv/bin/python3 -m pytest tests/test_mobile_polish.py -x -q`
- **After every plan wave:** Run `.venv/bin/python3 -m pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 19-01-01 | 01 | 1 | MOB-01 | unit | `.venv/bin/python3 -m pytest tests/test_mobile_polish.py::test_viewport_meta_zoom_disabled -x` | ❌ W0 | ⬜ pending |
| 19-01-02 | 01 | 1 | MOB-01 | unit | `.venv/bin/python3 -m pytest tests/test_mobile_polish.py::test_touch_action_manipulation_present -x` | ❌ W0 | ⬜ pending |
| 19-01-03 | 01 | 1 | MOB-02 | unit | `.venv/bin/python3 -m pytest tests/test_mobile_polish.py::test_user_select_none_on_body -x` | ❌ W0 | ⬜ pending |
| 19-01-04 | 01 | 1 | MOB-02 | unit | `.venv/bin/python3 -m pytest tests/test_mobile_polish.py::test_now_playing_name_selectable -x` | ❌ W0 | ⬜ pending |
| 19-01-05 | 01 | 1 | MOB-02 | unit | `.venv/bin/python3 -m pytest tests/test_mobile_polish.py::test_now_playing_artist_selectable -x` | ❌ W0 | ⬜ pending |
| 19-01-06 | 01 | 1 | MOB-02 | unit | `.venv/bin/python3 -m pytest tests/test_mobile_polish.py::test_feed_span_carveout_present -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_mobile_polish.py` — 6 string-parse tests covering MOB-01 and MOB-02 CSS assertions

*Existing infrastructure covers the test runner and conftest.py — only the new test file is needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Pinch-zoom suppressed on iOS | MOB-01 | iOS ignores `user-scalable=no` for pinch since iOS 10; CSS/HTML cannot fully block it — only double-tap and auto-zoom are suppressible | Open dashboard on physical iOS device; attempt pinch-zoom — should still work (accepted trade-off per D-01/D-02) |
| Track title long-press selection works on mobile | MOB-02 | CSS text selection on mobile requires physical device test | Long-press track name on mobile browser — should highlight/select |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
