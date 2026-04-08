# Requirements: Read the Room

**Defined:** 2026-04-08
**Milestone:** v1.6 — Open Source
**Core Value:** Songs that violate family-safe rules are skipped automatically before children hear them — with zero manual effort when Family Safe Mode is on.

## v1.6 Requirements

Requirements for the open source release milestone. Each maps to a roadmap phase.

### Repository Hygiene

- [x] **HYG-01**: A `.dockerignore` exists so live OAuth tokens, `.env`, and runtime data directories are excluded from Docker build context
- [x] **HYG-02**: `.claude/` directory is untracked from git and added to `.gitignore`
- [ ] **HYG-03**: Personal IP `192.168.1.164` replaced with generic placeholder (`192.168.1.100`) in `tests/test_sonos_probe.py`
- [ ] **HYG-04**: "Spotify Family Safe Mode" replaced with "Read the Room" in all module docstrings and source strings (user-agent in `lyrics_service.py`, FastAPI title in `web_ui/main.py`)
- [ ] **HYG-05**: `.env.example` updated to include `UID`, `GID`, and `EVENTS_PATH` with explanatory comments

### Legal & Docs

- [ ] **DOCS-01**: `LICENSE` (MIT) present at repository root
- [ ] **DOCS-02**: `README.md` rewritten for a public audience — description, prerequisites, quick start, how it works, filter profiles, Sonos notes, repo named `read-the-room`
- [ ] **DOCS-03**: `CONTRIBUTING.md` created — filing issues, submitting PRs, project layout, local dev setup

### CI & Tooling

- [ ] **CI-01**: `.github/workflows/ci.yml` runs `pytest tests/` on push and pull_request (all tests mocked — no real credentials needed)
- [ ] **CI-02**: `pyproject.toml` created with `[tool.pytest.ini_options]` and `[tool.ruff]` sections (no `[build-system]` — not a PyPI package)
- [ ] **CI-03**: Ruff lint/format check added to CI workflow
- [ ] **CI-04**: README header includes CI status badge and MIT license badge

## Future Requirements

### Community Infrastructure

- **COM-01**: Issue templates (bug report, feature request)
- **COM-02**: Pull request template
- **COM-03**: Code of conduct (Contributor Covenant)
- **COM-04**: SECURITY.md — vulnerability reporting policy

### Hosted Version Prep

- **HOST-01**: Local agent bridge mode — optional cloud connection flag
- **HOST-02**: WebSocket relay protocol spec for cloud connectivity

## Out of Scope

| Feature | Reason |
|---------|--------|
| PyPI publishing | Self-hosted Docker tool, not a Python library |
| Docker Hub image publishing | Users build locally; no image registry in scope |
| pre-commit hooks | Nice-to-have post-launch; not a contributor blocker |
| Hosted/multi-user architecture | Separate future project (read-the-room-cloud) |
| Source file / repo directory rename (RBR-03) | Low value, high churn — deferred from v1.5 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| HYG-01 | Phase 20 | Complete |
| HYG-02 | Phase 20 | Complete |
| HYG-03 | Phase 20 | Pending |
| HYG-04 | Phase 20 | Pending |
| HYG-05 | Phase 20 | Pending |
| DOCS-01 | Phase 21 | Pending |
| DOCS-02 | Phase 21 | Pending |
| DOCS-03 | Phase 21 | Pending |
| CI-01 | Phase 22 | Pending |
| CI-02 | Phase 22 | Pending |
| CI-03 | Phase 22 | Pending |
| CI-04 | Phase 22 | Pending |

**Coverage:**
- v1.6 requirements: 12 total
- Mapped to phases: 12
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-08*
*Last updated: 2026-04-08 — traceability confirmed against ROADMAP.md (Phases 20-22)*
