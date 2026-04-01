# Phase 2: Content Filtering & Auto-Skip - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the reasoning behind them.

**Date:** 2026-04-01
**Phase:** 02-content-filtering-auto-skip
**Mode:** discuss
**Areas analyzed:** Sonos detection, FSM toggle, Profanity threshold, Notification strategy, Central hosting architecture

---

## Assumptions Presented

### Sonos Detection
| Assumption | Confidence | Evidence |
|------------|------------|----------|
| SoCo auto-discover at startup OR configured room names needed | Likely | STATE.md blocker note: "SoCo speaker discovery requires knowing room names" |

### FSM Toggle (Phase 2)
| Assumption | Confidence | Evidence |
|------------|------------|----------|
| Makefile targets or direct state.json edit for Phase 2 | Confident | Signal toggle not built until Phase 3; need interim mechanism |

### Profanity Threshold
| Assumption | Confidence | Evidence |
|------------|------------|----------|
| Any-match most likely given "err on caution" stated preference | Likely | PROJECT.md: "filtering should err on the side of caution"; kids ages 3 and 7 |

### Notification Strategy
| Assumption | Confidence | Evidence |
|------------|------------|----------|
| Signal used for Phase 3 notifications per original plan | Confident | REQUIREMENTS.md SIG-01 through SIG-04; signal-cli-rest-api in SKIP-01 |

---

## Corrections Made

### Sonos Detection
- **Original assumption:** SoCo auto-discovery or configured room name list
- **User correction:** Neither needed — Spotify API provides device name and `is_restricted` flag directly. No local scan required.
- **Reason:** User asked whether Spotify provides the device name; confirmed yes, which eliminates the need for SoCo-based discovery.

### Notification Strategy (Major)
- **Original assumption:** Signal notifications in Phase 3 per REQUIREMENTS.md
- **User correction:** Signal dropped entirely. Replace with Web UI for notifications, FSM toggle, and allow/skip interactions.
- **Reason:** Signal is not expandable beyond the user's own account. Central multi-family hosting requires a Web UI that any household can log into. Signal works only for the original developer's phone.
- **Impact:** Phase 3 scope changes significantly — "Signal Notifications & Interactive Confirmations" → "Web UI & Notifications". Roadmap update required before Phase 3 planning.

### Central Hosting Architecture
- **Original assumption:** Self-hosted only (local Proxmox/Docker)
- **User correction:** Architecture should support future central hosting for other families. Self-host remains primary for v1.
- **Reason:** User wants to share this as a service with other families.
- **Resolution:** Abstract skip path behind `SkipClient` interface (D-03/D-04); local bridge deferred to central hosting milestone; Sonos Cloud API noted as backlog.

### Profanity Threshold
- **Original assumption:** Any-match = skip (strictest)
- **User correction:** Moderate/severe by default. User wants to tune the threshold over time and needs severity data to do so.
- **Reason:** Wants observability (severity scores logged for all tracks) and future configurability (per-family thresholds for multi-tenant). "This will likely require some tuning."
- **Resolution:** `PROFANITY_MIN_SEVERITY` env var; log `[SCAN]` lines for all tracks including non-skips.

---

## Key Insight

The conversation surfaced a significant architecture shift: the project has multi-family SaaS potential, not just a personal tool. This changes the notification strategy (Signal → Web UI) and requires the skip path to be abstraction-friendly. The Phase 2 implementation stays focused on self-hosted filtering, but the code structure is pre-wired for central hosting.

---

*Discussion completed: 2026-04-01*
