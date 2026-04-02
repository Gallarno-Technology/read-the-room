---
id: SEED-004
status: dormant
planted: 2026-04-02T00:00:00Z
planted_during: v1.0 / Phase 03 — signal-notifications-interactive-confirmations
trigger_when: next milestone / UI iteration
scope: small
---

# SEED-004: Now-playing widget with allow-reason context and manual skip button

## Why This Matters

Seeing the current track — what's playing, why it was allowed, and a thumbnail — builds
confidence that the content filter is working correctly. Without this, the dashboard is
reactive (shows what was skipped) but gives no signal about the tracks that sailed through.
A skip button lets a parent act immediately from the dashboard without opening Spotify.

## When to Surface

**Trigger:** Next milestone or any UI iteration phase.

This seed should be presented during `/gsd:new-milestone` when the milestone scope
matches any of these conditions:
- Dashboard UI improvements or polish are in scope
- A "now playing" or "monitoring" feature is mentioned
- Phase involves adding new web_ui endpoints

## Scope Estimate

**Small** — likely 1–2 tasks:
1. Daemon writes current track (name, artist, album thumbnail URL, allow-reason) to
   `data/now_playing.json` on each `allow` action (or on every track change). web_ui
   exposes `GET /now-playing` that reads this file.
2. Dashboard adds a "Now Playing" card above the skip feed: album art thumbnail,
   track + artist, allow-reason badge, and a POST `/skip` button (web_ui proxies to
   the Spotify skip API or writes a skip-request file for the daemon to action).

## Breadcrumbs

- `daemon.py:130–142` — track metadata available: `track["name"]`, `track["artists"][0]["name"]`, `track["album"]["images"]` (Spotify API returns thumbnail URLs here)
- `daemon.py:166` — `action, reason, severity = await content_checker.check(track)` — reason string is available on every `allow` action
- `daemon.py:87–94` — `_append_skip_event()` pattern — same approach can write `data/now_playing.json`
- `web_ui/main.py:174–178` — GET /fsm endpoint pattern — same pattern for GET /now-playing
- `web_ui/templates/index.html` — existing dashboard to add the widget to
- `docker-compose.yml:14,26` — `./data:/app/data` volume already shared between both containers

## Notes

- Album thumbnail: `track["album"]["images"][0]["url"]` (640×640), `[2]["url"]` (64×64 for small UI)
- The skip button in web_ui would need to call the Spotify API directly (requires token access in web_ui) or write a `data/skip_request` sentinel file that the daemon polls — the sentinel approach avoids duplicating auth logic.
- Consider showing "allowed because: lyrics clean, not explicit" style reasoning rather than raw reason codes.
