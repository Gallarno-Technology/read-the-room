---
phase: 5
slug: deployment-documentation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-02
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio |
| **Config file** | none — no pytest.ini / pyproject.toml found |
| **Quick run command** | `docker compose run --rm daemon python -m pytest tests/test_healthcheck.py -x -q` |
| **Full suite command** | `docker compose run --rm daemon python -m pytest tests/ -v` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `docker compose run --rm daemon python -m pytest tests/test_healthcheck.py -x -q`
- **After every plan wave:** Run `docker compose run --rm daemon python -m pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 5-01-01 | 01 | 1 | DEPL-04 | unit | `docker compose run --rm daemon python -m pytest tests/test_healthcheck.py -x -q` | ❌ Wave 0 | ⬜ pending |
| 5-01-02 | 01 | 1 | DEPL-04 | unit | `docker compose run --rm daemon python -m pytest tests/test_healthcheck.py -x -q` | ❌ Wave 0 | ⬜ pending |
| 5-02-01 | 02 | 2 | DEPL-01 | manual | verify README.md exists and matches structure | ❌ n/a (doc) | ⬜ pending |
| 5-02-02 | 02 | 2 | DEPL-02 | manual | verify PROXMOX.md exists and is linked from README | ❌ n/a (doc) | ⬜ pending |
| 5-03-01 | 03 | 3 | DEPL-03 | manual | `docker compose ps` after `docker compose restart` | ❌ n/a (host-level) | ⬜ pending |
| 5-03-02 | 03 | 3 | DEPL-05 | manual | verify bind-mounts survive `docker compose up -d --build` | ❌ n/a (operational) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_healthcheck.py` — two tests: `test_poll_loop_touches_healthcheck_file` and `test_healthcheck_cmd_detects_stale_file` (covers DEPL-04)

*All other phase requirements are documentation/operational — no automated tests feasible.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| README covers complete first-time setup | DEPL-01 | Documentation quality — no grep can verify completeness | Read through README following quick-start; confirm steps lead to running service |
| README documents Sonos network reqs + PROXMOX.md linked | DEPL-02 | Docs existence + cross-link | `ls PROXMOX.md && grep -q PROXMOX README.md` |
| Service survives host reboot | DEPL-03 | Requires actual OS reboot or simulated restart | `docker compose restart daemon && docker compose ps` — verify (healthy) |
| `git pull && docker compose up -d --build` is safe | DEPL-05 | Operational verification | Rebuild image, confirm state.json / lyrics_cache.db / token_cache/ / data/ unchanged |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
