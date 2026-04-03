---
phase: 8
slug: dashboard-frontend
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-03
---

# Phase 8 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Manual browser verification + curl (no JS test framework; vanilla HTML file) |
| **Config file** | none — no test runner needed for pure frontend HTML/JS/CSS |
| **Quick run command** | `curl -s http://localhost:8000/now-playing` |
| **Full suite command** | `curl -s http://localhost:8000/now-playing && curl -s -X POST http://localhost:8000/skip` |
| **Estimated runtime** | ~2 seconds |

---

## Sampling Rate

- **After every task commit:** Run `curl -s http://localhost:8000/now-playing`
- **After every plan wave:** Run `curl -s http://localhost:8000/now-playing && curl -s -X POST http://localhost:8000/skip`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 8-01-01 | 01 | 1 | NOW-01, NOW-06 | static | `grep -c 'now-playing-card\|album-art' web_ui/templates/index.html` | ✅ | ⬜ pending |
| 8-01-02 | 01 | 1 | NOW-03, NOW-07 | static | `grep -c 'badge--evaluating\|badge--passed\|badge--skipped' web_ui/templates/index.html` | ✅ | ⬜ pending |
| 8-01-03 | 01 | 1 | SKIP-01, SKIP-04 | static | `grep -c 'skip-btn\|button.disabled' web_ui/templates/index.html` | ✅ | ⬜ pending |
| 8-01-04 | 01 | 1 | NOW-04, NOW-05 | static | `grep -c '/now-playing\|es.onopen' web_ui/templates/index.html` | ✅ | ⬜ pending |
| 8-01-05 | 01 | 1 | NOW-02, NOW-07 | static | `grep -c 'currentTrackId\|track_change\|eval_result' web_ui/templates/index.html` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

*All changes are in `web_ui/templates/index.html` — no test runner needed. Verification is via grep checks on the file and live curl against the running server.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Badge updates to "Checking…" immediately on track change (no delay) | NOW-03 | Requires real-time SSE stream observation | Open dashboard, play a Spotify track, watch badge update in browser |
| Badge does NOT update when eval_result track_id mismatches | NOW-07 | Requires simulated stale event injection | Check JS logic via grep; functional verify with live SSE if possible |
| Skip button re-enables after POST /skip settles | SKIP-04 | Requires live button interaction | Click skip in browser, verify disabled state then re-enable |
| Card repopulates after SSE reconnect without going blank | NOW-05 | Requires network interruption simulation | Restart server mid-session, verify card re-hydrates |
| Album art hidden when album_art_url is null | NOW-06 | Requires null payload from server | Test with idle state or mock null art URL |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
