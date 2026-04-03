# Milestones

## v1.2 Now Playing Status (Shipped: 2026-04-03)

**Phases completed:** 7 phases, 23 plans, 45 tasks

**Key accomplishments:**

- SpotifyOAuth headless setup script with CacheFileHandler token persistence, pinned spotipy/dotenv deps, exec-form Dockerfile, and docker-compose with restart:always and host-bind mounts
- Asyncio daemon polling Spotify /me/player/currently-playing every 1s with track-change detection, 429 backoff, and clean SIGTERM shutdown verified live in Docker
- One-liner:
- LRCLIB lyrics fetch with SQLite cache, three-tier severity word mapping with better-profanity leet-speak fallback, and full ContentChecker pipeline activation — non-explicit tracks with profanity are now auto-skipped.
- save_state() read-merges disk state before writing so family_safe_mode written by make fsm-on/fsm-off is never dropped on track change
- LRCLIB exception binding (as exc + exc_info=True) and asyncio.wait_for 10s timeout added; no_lyrics_service log upgraded from INFO to WARNING
- Three targeted one-line fixes closing two root-cause bugs: Docker bind-mount file ownership (SQLite OperationalError) and wrong Spotify endpoint (Sonos is_restricted always False)
- Compound -d/-f guard in Makefile setup prevents Permission denied on root-owned lyrics_cache.db directory; reason=instrumental and reason=lyrics_unavailable added to [SCAN] log lines for observability
- soco.discovery.by_name replaced with discover() + .strip().lower() iteration, closing UAT Test 5 gap where Sonos skip failed due to casing/whitespace mismatch between Spotify device name and Sonos room name
- asyncio.Queue skip event bridge in daemon.py with FastAPI SSE endpoint, 5-consecutive-skip pause logic, and FSM toggle API using daemon's read-merge-write state pattern
- Dark-theme single-page dashboard with FSM toggle, SSE skip feed (four badge variants), five-skip warning banner, wired into docker-compose as a second service alongside the daemon
- Corrected web_ui container startup by fixing Dockerfile COPY path and added FSM False->True transition detection to reset the consecutive-skip counter on re-enable
- daemon.py writes skip events to data/skip_events.jsonl; web_ui tails that file via _file_tail() coroutine, replacing the broken cross-process asyncio.Queue import that silently delivered no events in docker-compose
- SoCo-backed pause() added to SkipClient ABC and both implementations so Sonos speakers actually stop after 5 consecutive explicit tracks
- 9-test xfail scaffold covering DAEM-01 track_change, DAEM-02 eval_result, DAEM-03 now_playing.json and D-01 regression — ready for Wave 1 implementation
- Hard rename of SKIP_EVENTS_PATH to EVENTS_PATH across daemon.py, web_ui/main.py, and docker-compose.yml, adding NOW_PLAYING_PATH constant and datetime import in preparation for Plans 03 and 04
- poll_loop now emits track_change before ContentChecker and eval_result in all 4 outcome branches, turning 6 DAEM-01/DAEM-02 xfail stubs green
- _write_now_playing() helper added to daemon.py with 5 call sites: eval_state=evaluating before check() and final eval_state in all 4 outcome branches (allow, paused, skipped, fsm-off)
- spotipy added to web_ui container and token_cache volume shared with daemon; 4 failing TDD stubs for /now-playing and /skip ready for Plan 02
- GET /now-playing and POST /skip implemented in web_ui/main.py using shared spotipy token cache; all 4 TDD tests pass
- Now-playing card with real-time eval-state badge and skip button wired to GET /now-playing hydration and SSE track_change/eval_result events
- Severity integer (0-3) propagated from content_checker.check() into all eval_result SSE events and now_playing.json writes across 8 call sites in daemon.py
- Multi-badge flex container and severity-aware JS rendering — dashboard shows Passed + Mild language badges simultaneously for tracks with severity >= 1

---

## v1.1 Deployment (Shipped: 2026-04-02)

**Phases completed:** 2 phases, 4 plans, 6 tasks

**Key accomplishments:**

- TDD RED scaffold: 6 failing probe tests + 2 failing warning-text tests establish behavioral contracts for DISC-01, DISC-02, DISC-03 before any implementation
- SSDP auto-discovery wired as first-class startup step in daemon.py with probe_sonos_speakers; actionable multicast warnings in skip_client.py; SONOS_SPEAKER_IPS reframed as escape hatch in .env.example
- One-liner:
- README.md and PROXMOX.md written — clone-and-run setup guide with OAuth flow, UID/GID pitfall docs, and Proxmox LXC multicast/SSDP escape hatch via SONOS_SPEAKER_IPS

---

## v1.0 MVP (Shipped: 2026-04-02)

**Phases completed:** 3 phases, 14 plans, 28 tasks

**Key accomplishments:**

- SpotifyOAuth headless setup script with CacheFileHandler token persistence, pinned spotipy/dotenv deps, exec-form Dockerfile, and docker-compose with restart:always and host-bind mounts
- Asyncio daemon polling Spotify /me/player/currently-playing every 1s with track-change detection, 429 backoff, and clean SIGTERM shutdown verified live in Docker
- One-liner:
- LRCLIB lyrics fetch with SQLite cache, three-tier severity word mapping with better-profanity leet-speak fallback, and full ContentChecker pipeline activation — non-explicit tracks with profanity are now auto-skipped.
- save_state() read-merges disk state before writing so family_safe_mode written by make fsm-on/fsm-off is never dropped on track change
- LRCLIB exception binding (as exc + exc_info=True) and asyncio.wait_for 10s timeout added; no_lyrics_service log upgraded from INFO to WARNING
- Three targeted one-line fixes closing two root-cause bugs: Docker bind-mount file ownership (SQLite OperationalError) and wrong Spotify endpoint (Sonos is_restricted always False)
- Compound -d/-f guard in Makefile setup prevents Permission denied on root-owned lyrics_cache.db directory; reason=instrumental and reason=lyrics_unavailable added to [SCAN] log lines for observability
- soco.discovery.by_name replaced with discover() + .strip().lower() iteration, closing UAT Test 5 gap where Sonos skip failed due to casing/whitespace mismatch between Spotify device name and Sonos room name
- asyncio.Queue skip event bridge in daemon.py with FastAPI SSE endpoint, 5-consecutive-skip pause logic, and FSM toggle API using daemon's read-merge-write state pattern
- Dark-theme single-page dashboard with FSM toggle, SSE skip feed (four badge variants), five-skip warning banner, wired into docker-compose as a second service alongside the daemon
- Corrected web_ui container startup by fixing Dockerfile COPY path and added FSM False->True transition detection to reset the consecutive-skip counter on re-enable
- daemon.py writes skip events to data/skip_events.jsonl; web_ui tails that file via _file_tail() coroutine, replacing the broken cross-process asyncio.Queue import that silently delivered no events in docker-compose
- SoCo-backed pause() added to SkipClient ABC and both implementations so Sonos speakers actually stop after 5 consecutive explicit tracks

---
