# Phase 3: Signal Notifications & Interactive Confirmations - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the discussion.

**Date:** 2026-04-01
**Phase:** 03-signal-notifications-interactive-confirmations
**Mode:** discuss
**Areas discussed:** Signal vs Web UI, Ambiguous track timing, Notification format & 5-skip counter

## Gray Areas Presented

| Area | Selected for discussion? |
|------|--------------------------|
| Signal vs Web UI | Yes |
| Signal account linking | No (user skipped) |
| Ambiguous track timing | Yes |
| Notification format & 5-skip counter | Yes |

## Decisions Made

### Signal vs Web UI
- **Options presented:** Signal as planned / Web UI instead / Signal now + Web UI later
- **User chose:** Web UI instead
- **Follow-up — Signal role:** Web UI only (Signal dropped entirely)
- **Follow-up — Web UI features:** Skip history feed + FSM toggle (not: allow/skip prompts, not: now playing)
- **Follow-up — UI stack:** FastAPI + plain HTML/JS (user wanted simplest option that supports real-time updates)
- **Key user quote:** "I would like the simplest option, so FastAPI + plain HTML/JS as long as that means we can still update the 'recently skipped' songs in real-time"
- **Resolution:** SSE (Server-Sent Events) enables real-time push without complexity — confirmed as the approach

### Ambiguous Track Timing
- **Options presented:** Auto-allow (keep current) / Auto-skip (err on caution)
- **User chose:** Auto-allow — keep current behavior
- **Impact:** FILT-05 unchanged; `lyrics_unavailable` continues to return `("allow", "lyrics_unavailable", 0)`; no interactive confirmation flow

### Notification Format & 5-Skip Counter
- **Skip entry format options:** Track+artist+reason+time / Track+artist+reason+time+severity / Track+artist+reason only
- **User chose:** Track + artist + reason + time
- **5-skip options:** Banner in Web UI / Drop it entirely / Special entry in feed
- **User interrupted:** Asked "can we show a banner AND have Spotify stop the music?"
- **Agreed addition:** On 5th consecutive skip — pause Spotify playback immediately (PUT /me/player/pause) + warning banner in Web UI
- **Pause timing:** Immediately on 5th skip (not before 6th)

## Scope Change Note

Phase 3 was originally "Signal Notifications & Interactive Confirmations" per ROADMAP. User decision:
- Signal dropped entirely
- Interactive confirmations dropped (no prompts in Web UI or Signal)
- Phase becomes: Web UI Dashboard (skip history + FSM toggle + 5-skip pause)

ROADMAP.md phase name, goal, and success criteria are stale. REQUIREMENTS.md SIG-01 through SIG-04 and FSM-03 need updating. Planner must address this before writing plans.

## Items Left to Claude's Discretion

- Consecutive skip counter storage (in-memory)
- SSE event format
- Daemon ↔ FastAPI event sharing mechanism
- FastAPI port number
- HTML/CSS styling
