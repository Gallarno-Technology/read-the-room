---
phase: 20
slug: repository-hygiene
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-08
---

# Phase 20 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | bash/grep (no test suite — all verifications are filesystem/git state checks) |
| **Config file** | none |
| **Quick run command** | `grep -r "Spotify Family Safe Mode" daemon.py content_checker.py skip_client.py drug_scanner.py sexual_content_scanner.py web_ui/main.py lyrics_service.py` |
| **Full suite command** | see Per-Task Verification Map below |
| **Estimated runtime** | ~2 seconds |

---

## Sampling Rate

- **After every task commit:** Run task-specific grep check
- **After every plan wave:** Run full acceptance verification suite
- **Before `/gsd:verify-work`:** All 5 grep checks must return zero matches (or expected output for HYG-01/HYG-05)
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| 20-01-01 | 01 | 1 | HYG-01 | grep | `cat .dockerignore \| grep -E "^\.env$"` | ⬜ pending |
| 20-02-01 | 02 | 1 | HYG-02 | git | `git ls-files .claude/` (must return empty) | ⬜ pending |
| 20-03-01 | 03 | 1 | HYG-03 | grep | `grep "192.168.1.164" tests/test_sonos_probe.py` (must return empty) | ⬜ pending |
| 20-04-01 | 04 | 1 | HYG-04 | grep | `grep -r "Spotify Family Safe Mode" daemon.py content_checker.py skip_client.py drug_scanner.py sexual_content_scanner.py web_ui/main.py lyrics_service.py` (must return empty) | ⬜ pending |
| 20-05-01 | 05 | 1 | HYG-05 | grep | `grep -E "^UID=|^GID=|^EVENTS_PATH=" .env.example` (must return 3 lines) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. No new test files needed — all verification is grep/git-based.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Docker build excludes secrets | HYG-01 | Requires running a Docker build | `docker build -t test-hygiene . && docker run --rm test-hygiene ls /app/.env 2>&1` should return "No such file" |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
