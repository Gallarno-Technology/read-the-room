# Milestones

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
