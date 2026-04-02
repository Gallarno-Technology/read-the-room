# Phase 5: Deployment & Documentation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the discussion.

**Date:** 2026-04-02
**Phase:** 05-deployment-documentation
**Mode:** discuss
**Areas discussed:** README structure & depth, Proxmox/LXC multicast doc

---

## Areas Selected

User selected 2 of 4 offered areas:
- README structure & depth ✓
- Proxmox/LXC multicast doc ✓
- Healthcheck design — skipped (Claude's discretion applied)
- Update workflow — skipped (Claude's discretion applied)

---

## README Structure & Depth

| Question | Options Presented | Selected |
|----------|------------------|----------|
| Target reader | Me (returning user) / Any developer / Non-technical | Me, returning after weeks away |
| Top-level structure | Quick-start first + details / Comprehensive single flow / Minimal only | Quick-start first, details below |
| Sections below quick-start | Prerequisites / Sonos setup / Updating / Troubleshooting | Prerequisites + Updating |
| Quick-start style | make targets / Explicit docker commands / Both | Explicit docker commands |

**Key decisions:**
- README optimizes for re-setup speed, not onboarding new developers
- Quick-start uses raw docker commands (not make targets)
- Minimal sections: Prerequisites + Updating only
- No troubleshooting, no configuration reference (`.env.example` handles that)

---

## Proxmox/LXC Multicast Documentation

| Question | Options Presented | Selected |
|----------|------------------|----------|
| Specificity level | Actual verified commands / Researched best-practice steps / High-level note only | High-level note only |
| Location | Inline in README / Separate PROXMOX.md / Skip for now | Separate PROXMOX.md |

**Key decisions:**
- No specific nftables/bridge commands — user hasn't verified them personally
- High-level note: "multicast bridge forwarding required" + link to Proxmox docs
- PROXMOX.md at repo root, linked from README
- SONOS_SPEAKER_IPS escape hatch prominently mentioned as the practical alternative

---

## Areas on Claude's Discretion (not discussed)

**Healthcheck design:**
Defaulted to: touch-file mechanism in `poll_loop()`, checked by Docker healthcheck every 30s.
Rationale: Simple, no external dependencies, daemon already runs poll_loop() continuously.

**Update workflow:**
Defaulted to: `git pull && docker compose up -d --build` documented in README Updating section.
Rationale: Bind-mount pattern already makes rebuilds safe; no Makefile target needed.
