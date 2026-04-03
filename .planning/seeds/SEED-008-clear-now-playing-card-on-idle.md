---
id: SEED-008
status: dormant
planted: 2026-04-03
planted_during: v1.2 Now Playing Status
trigger_when: next UI polish milestone
scope: medium
---

# SEED-008: Clear now-playing card when nothing is playing via heartbeat poll

## Why This Matters

The card currently shows stale track info after playback stops — it keeps displaying the last
track as if it were still playing, which confuses parents ("why is it showing a song that
isn't on?"). There's no mechanism to detect the stopped/idle state and revert the card to
its "Nothing playing" idle view.

## When to Surface

**Trigger:** Next UI polish milestone or any dashboard UX iteration.

This seed should be presented during `/gsd:new-milestone` when the milestone
scope matches any of these conditions:
- Milestone involves dashboard UX improvements or polish
- Milestone involves Spotify state reliability / accuracy
- Milestone involves "what parents see" fidelity

## Scope Estimate

**Medium** — A phase or two, needs planning.

The JS-only fix (periodic `GET /now-playing` poll) is small, but the user flagged that a
deeper rethink may be warranted: mirroring Spotify playback state more uniformly so idle,
paused, and stopped are all reliably reflected rather than patched case-by-case.
Exploration needed before planning.

## Breadcrumbs

Related code and decisions found in the current codebase:

- `web_ui/templates/index.html:351` — `#now-playing-idle` element ("Nothing playing") already exists but is only shown on page-load hydration when `status === 'idle'`
- `web_ui/templates/index.html:511` — `hydrateNowPlaying()` handles `status: idle` from `/now-playing` on page load — same logic needed on interval
- `web_ui/templates/index.html:489-504` — `showTrack()` / `showIdle()` show/hide pattern already in place; heartbeat just needs to call them
- `web_ui/main.py:232-244` — `GET /now-playing` already returns `{"status": "idle"}` when `now_playing.json` absent — backend is ready
- `web_ui/main.py:8` — comment confirms idle contract: `{"status":"idle"}` when file absent
- `web_ui/templates/index.html:573` — SSE-only event loop today; no polling fallback

## Notes

The daemon writes `now_playing.json` on track detection but does NOT delete it when
playback stops. For a heartbeat approach to work reliably, either:
1. The daemon deletes / overwrites `now_playing.json` with `{"status":"idle"}` when
   Spotify reports nothing playing, OR
2. The frontend polls Spotify state indirectly through a new `/playback-state` endpoint
   that queries the live Spotify API rather than the snapshot file

Option 1 is simpler. Option 2 is more reliable but adds latency and a Spotify API call on
every heartbeat interval. Decision deferred to planning.
