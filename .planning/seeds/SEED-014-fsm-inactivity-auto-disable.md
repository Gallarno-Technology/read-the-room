---
id: SEED-014
status: dormant
planted: 2026-04-06
planted_during: v1.5 / 18-profile-info-icon
trigger_when: UX / comfort milestone — when we focus on reducing friction or improving day-to-day feel
scope: small
---

# SEED-014: Disable FSM automatically after a period of inactivity

## Why This Matters

FSM left on after kids go to bed silently filters adult listening with no indication it's still
running. Users have to remember to turn it off — cognitive overhead that defeats the "zero effort"
promise of the app. An inactivity timer (e.g. auto-disable after N minutes of no playback) removes
that burden entirely.

## When to Surface

**Trigger:** Any milestone focused on UX comfort, friction reduction, or day-to-day feel.

This seed should be presented during `/gsd:new-milestone` when the milestone scope matches any of:
- UX polish / comfort / annoyance reduction
- Idle detection revisit (Phase 14 follow-up)
- Time-based or presence-aware FSM rules

## Scope Estimate

**Small** — a few hours. The idle-detection infrastructure already exists in `daemon.py`
(`idle_counter`, `IDLE_THRESHOLD`, `was_idle` transition logic at lines 330–355). The daemon
already knows when playback stops. The missing piece is: after N consecutive idle polls (or a
configurable wall-clock timeout), call `POST /fsm` with `{"enabled": false}` and log the
auto-disable event. The UI already reflects state changes on next poll.

Optional additions (still small): a UI indicator showing "FSM will auto-disable in Xm" while idle,
and a configurable timeout exposed in settings.

## Breadcrumbs

- `daemon.py:41` — `IDLE_THRESHOLD = 3` (consecutive empty polls before idle state); the
  auto-disable timer would key off the same idle transition
- `daemon.py:330–355` — `idle_counter` / `was_idle` loop; this is where auto-disable logic would
  hook in after sustained idle
- `web_ui/main.py:221` — `POST /fsm` endpoint; daemon can call this directly (or write
  `state.json` via the shared `_save_state_merge` path) to disable FSM
- `web_ui/main.py:6–7` — FSM state API contract; no changes needed, auto-disable is a write not
  a new endpoint

## Notes

The simplest implementation: count idle polls past `IDLE_THRESHOLD` into a second counter
(`idle_fsm_counter`); when it exceeds a configurable `FSM_IDLE_DISABLE_THRESHOLD`, set
`family_safe_mode = False` in `state.json` and log `[FSM] auto-disabled after N minutes idle`.
No new endpoints, no UI changes required for MVP.
