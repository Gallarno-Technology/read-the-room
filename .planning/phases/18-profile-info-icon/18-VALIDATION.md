---
phase: 18
slug: profile-info-icon
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-06
---

# Phase 18 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | none — `conftest.py` handles path setup |
| **Quick run command** | `python3 -m pytest tests/ -x -q` |
| **Full suite command** | `python3 -m pytest tests/ -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python3 -m pytest tests/ -x -q`
- **After every plan wave:** Run `python3 -m pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 18-01-01 | 01 | 1 | INFO-01 | unit (template parse) | `python3 -m pytest tests/test_info_icon.py::test_info_btn_present -x` | ❌ Wave 0 | ⬜ pending |
| 18-01-02 | 01 | 1 | INFO-02 | manual/visual | manual browser test | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_info_icon.py` — stubs for INFO-01: checks that `#info-btn`, `#info-panel`, and `PROFILE_INFO` JS map are present in the rendered HTML template

*Existing pytest infrastructure covers test execution — no framework install needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Clicking ⓘ shows profile info popover (desktop) | INFO-02 | JavaScript DOM interaction requires browser runtime not available in pytest TestClient | Open dashboard, click ⓘ, verify popover appears with profile name + prose sentence |
| Tapping ⓘ shows bottom sheet (mobile ≤640px) | INFO-02 | Requires browser with responsive viewport simulation | Open dashboard at ≤640px viewport, tap ⓘ, verify bottom sheet slides up |
| Breakdown updates when profile changes | INFO-02 (SC-3) | Requires live SSE + JS state interaction | Change profile via dropdown, reopen ⓘ, verify content reflects new profile |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
