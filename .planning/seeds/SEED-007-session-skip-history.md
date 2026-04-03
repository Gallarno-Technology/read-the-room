---
id: SEED-007
status: dormant
planted: 2026-04-03
planted_during: v1.2 Now Playing Status (Phase 8 planning)
trigger_when: milestone focused on dashboard UX polish or parent-facing improvements
scope: medium
---

# SEED-007: Persist recent skip history for the current listening session

## Why This Matters

SSE reconnect and page refresh both destroy the in-memory skip feed in the browser. The
existing SSE tail in `web_ui/main.py` intentionally seeks to the END of `events.jsonl` on
startup (`fh.seek(0, 2)`) to skip old history — but this means any skips that happened
while the tab was backgrounded or while the page was reloading are silently lost.

Parents can't see what was caught during the listening session unless they happened to be
watching the dashboard live. The incident log file accumulates everything forever, but the
live feed in the UI goes blank after every reconnect.

## When to Surface

**Trigger:** Any milestone with a UX polish, dashboard improvements, or parent-facing
visibility theme.

This seed should be presented during `/gsd:new-milestone` when the milestone scope matches
any of these conditions:
- Milestone involves improving the dashboard experience for parents
- Milestone includes session-level tracking or audit trails
- Milestone adds more "what's been playing" context to the UI

## Scope Estimate

**Medium** — A phase or two. Likely decomposition:
1. Backend: `GET /recent-skips` endpoint that reads the last N lines from `events.jsonl`
   (only `skip` and `five_skip_warning` events for the current session window)
2. Frontend: Replace the live-only skip feed with a hybrid — on load/reconnect, fetch
   recent history; then tail new events via SSE as before. Session boundary = process
   start of the daemon (already tracked in `now_playing.json` or derivable from timestamps).

## Breadcrumbs

Related code and decisions in the current codebase:

- `web_ui/main.py:90-102` — SSE tail generator; `fh.seek(0, 2)` is the exact line that
  discards history on startup. Changing this is the key implementation decision.
- `web_ui/main.py:53` — `EVENTS_PATH = os.environ.get("EVENTS_PATH", "data/events.jsonl")`
  — the append-only log that already contains all skip events with timestamps
- `daemon.py:39` — `EVENTS_PATH` definition (same env var, shared between daemon and web_ui)
- `daemon.py:95` — daemon appends to `events.jsonl` via `open(EVENTS_PATH, "a")`
- `web_ui/templates/index.html` — Incident Log card that renders the live feed; the new
  history panel would likely extend or replace the existing `<ul id="feed">` element

## Notes

The `events.jsonl` file already has everything needed — it's an append-only log with full
event payloads. The only work is (a) a backend read endpoint that slices the last N events
by session or time window, and (b) wiring the frontend to call it on load/reconnect instead
of starting from a blank slate.

Session boundary definition is the main design question: time-based (last N minutes),
count-based (last N skips), or daemon-restart-based (events after the daemon's last
startup). The simplest approach is count-based (last 20 skips) with no session concept.
