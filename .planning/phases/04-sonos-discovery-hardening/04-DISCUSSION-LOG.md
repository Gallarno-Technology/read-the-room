# Phase 4: Sonos Discovery Hardening - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-02
**Phase:** 04-Sonos Discovery Hardening
**Areas discussed:** Discovery timing, Discovery output, Failure message

---

## Discovery timing

| Option | Description | Selected |
|--------|-------------|----------|
| Daemon startup | Eager SSDP probe at daemon startup, before poll loop | ✓ |
| Separate setup command | Standalone script user runs once to discover and write .env | |

**User's choice:** Daemon startup
**Notes:** User also mentioned wanting to eventually auto-activate FSM when playback switches to a specific Sonos speaker — noted as deferred. The startup probe's logged speaker list gives users the info they'd need for that future feature.

---

## Discovery output

| Option | Description | Selected |
|--------|-------------|----------|
| Log only | Print discovered speakers (name + IP) to daemon logs | ✓ |
| Expose in web UI | Show discovered speakers in dashboard | |

**User's choice:** Log only
**Notes:** Web UI changes deferred — Phase 4 is backend only.

---

## Failure message

| Option | Description | Selected |
|--------|-------------|----------|
| Generic hint + port | "No speakers found via SSDP. Ensure multicast UDP port 1900 open. Set SONOS_SPEAKER_IPS as fallback. See README." | ✓ |
| Specific commands inline | Include actual ufw/iptables/Proxmox commands in log line | |

**User's choice:** Generic hint + port
**Notes:** Phase 5 README (DEPL-02) will have full firewall setup instructions — the log just needs to point in the right direction.

---

## Scope clarification

User mentioned auto-activating FSM when playback switches to a specific Sonos speaker ("X"). This maps to REQUIREMENTS.md SONO-01/SONO-02 (v2 scope). Redirected to deferred — Phase 4's speaker discovery output sets this up but does not implement it.
