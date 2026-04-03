---
id: SEED-006
status: dormant
planted: 2026-04-02
planted_during: v1.1 milestone complete
trigger_when: when dashboard has enough UI surface to manage lists, or when a milestone adds listening preferences beyond content filtering
scope: small
---

# SEED-006: Artist allow and block list, configurable per session / profile

## Why This Matters

The system currently filters purely on content (lyrics, explicit flag). This seed extends it
into **listening preference** — allowing an artist to be skipped regardless of content, or
allowed through regardless of content, based on who is in the room.

The motivating scenario: a shared space (living room) where one person likes an artist but
another (e.g. spouse) wants nothing to do with them. The content filter won't catch this —
the songs may be perfectly clean. A per-session artist block list lets you flip a switch when
the audience changes, then flip it back.

This is a meaningful shift in product framing: from "content safety tool" to "shared listening
preference manager." That's a bigger surface but the core mechanic is small.

## When to Surface

**Trigger:** When the dashboard has enough UI surface to manage lists, or when a milestone
is scoped around listening preferences / profile support.

This seed should be presented during `/gsd:new-milestone` when the milestone scope matches:
- Dashboard enhancements that add settings or configuration panels
- Any milestone framed around "listening preferences" vs. pure content filtering
- Profile or per-user support milestone

## Scope Estimate

**Small** — the filter decision point is already in `content_checker.py` / `daemon.py:199`
(`content_checker.check(track)`). An artist block/allow list is a pre-check before content
evaluation: if artist is in block list → skip; if artist is in allow list → pass without
evaluation. The list itself lives in `state.json` (already the shared config file) and the
UI needs a simple management surface (add/remove artist name or Spotify artist ID).

Session vs. persistent is the main design decision: session-only lists live in memory and
reset on container restart; persistent lists write to `state.json`. Both are small.

## Breadcrumbs

- `daemon.py:172` — `track["artists"][0]["name"]` — artist name already extracted at track change
- `daemon.py:199` — `content_checker.check(track)` — pre-check hook point; artist filter goes here
- `daemon.py:252` — `"artist": track["artists"][0]["name"]` — artist included in skip event log
- `state.json` — shared config already holds `family_safe_mode` and `consecutive_skips`; artist lists fit naturally here
- `content_checker.py` — ContentChecker already has a `check()` method that returns `(action, reason, severity)`; an allow/block result is a new `action` value

## Notes

- Spotify track objects include `artists` as a list — multi-artist tracks (features) should
  match if ANY listed artist is in the block list
- "Session" framing means: toggled from the dashboard UI, resets on restart. No `.env` changes required.
- Artist ID (Spotify URI) is more reliable than name for matching; name is human-readable for display
