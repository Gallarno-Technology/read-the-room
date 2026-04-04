---
phase: 12
slug: event-propagation-incident-log
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-04
---

# Phase 12 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pytest.ini or pyproject.toml |
| **Quick run command** | `cd /home/cgallarno/Development/spotify-sentiment && python -m pytest tests/ -x -q 2>&1 | tail -5` |
| **Full suite command** | `cd /home/cgallarno/Development/spotify-sentiment && python -m pytest tests/ -q 2>&1 | tail -10` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/ -x -q 2>&1 | tail -5`
- **After every plan wave:** Run `python -m pytest tests/ -q 2>&1 | tail -10`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 12-01-01 | 01 | 1 | LOG-01 | unit | `python -m pytest tests/test_content_checker.py -q` | ✅ | ⬜ pending |
| 12-01-02 | 01 | 1 | LOG-01 | unit | `python -m pytest tests/test_content_checker.py -q` | ✅ | ⬜ pending |
| 12-01-03 | 01 | 2 | LOG-01 | unit | `python -m pytest tests/test_daemon_events.py -q` | ✅ | ⬜ pending |
| 12-01-04 | 01 | 2 | LOG-01 | unit | `python -m pytest tests/test_daemon_events.py -q` | ✅ | ⬜ pending |
| 12-01-05 | 01 | 3 | LOG-02 | unit | `python -m pytest tests/test_content_checker.py -q` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- Existing infrastructure covers all phase requirements.

*All test files (test_content_checker.py, test_daemon_events.py) already exist. No new test stubs needed before Wave 1.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `skip_events.jsonl` entries contain all four boolean fields at runtime | LOG-01 | File written during daemon execution, not under pytest | Run daemon against a flagged track; inspect `data/skip_events.jsonl` last entry for `explicit`, `profanity`, `drug_reference`, `sexual_content` keys |
| `now_playing.json` matches `eval_result` SSE payload | LOG-01 | Requires live SSE stream + file read comparison | Trigger track change; compare `now_playing.json` booleans with browser SSE event payload |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
