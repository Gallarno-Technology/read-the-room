---
phase: 02-content-filtering-auto-skip
plan: "01"
subsystem: content-filtering
tags: [skip-client, content-checker, fsm, soco, spotipy, oauth]
dependency_graph:
  requires: []
  provides:
    - skip_client.SkipClient (ABC)
    - skip_client.SpotifySkipClient
    - skip_client.SocoSkipClient
    - content_checker.ContentChecker (tier 1 live, tiers 2-3 stubbed)
    - daemon.py poll_loop FSM guard + skip dispatch
    - Makefile fsm-on / fsm-off targets
  affects:
    - daemon.py (poll_loop signature, main, imports, OAuth scope)
    - requirements.txt (soco added)
tech_stack:
  added:
    - soco==0.30.14 (Sonos UPnP skip via by_name discovery with IP caching)
  patterns:
    - Strategy pattern for SkipClient ABC (SwappableSkipClient)
    - run_in_executor wrapping for all sync library calls in async context
    - FSM guard reads state.json each poll cycle (no startup cache)
key_files:
  created:
    - skip_client.py (SkipClient ABC, SpotifySkipClient, SocoSkipClient)
    - content_checker.py (ContentChecker with tier 1; tiers 2-3 stubbed)
  modified:
    - daemon.py (imports, PROFANITY_MIN_SEVERITY, poll_loop sig + FSM block, main)
    - setup_auth.py (OAuth scope expanded)
    - Makefile (fsm-on, fsm-off, fsm-status targets; setup touch lyrics_cache.db)
    - .env.example (PROFANITY_MIN_SEVERITY, LYRICS_DB_PATH)
    - docker-compose.yml (lyrics_cache.db bind mount)
    - requirements.txt (soco==0.30.14)
decisions:
  - "SkipClient ABC designed for future BridgeSkipClient extension without daemon changes (D-04)"
  - "SocoSkipClient caches speaker IP after first successful discovery to avoid repeat SSDP multicast (Pitfall 6)"
  - "ContentChecker tiers 2-3 conditioned on lyrics_service/profanity_scanner not None — dormant until Plan 02"
  - "FSM Makefile targets run inside container via docker compose exec to use same state.json bind-mount path"
metrics:
  duration: "3 minutes"
  completed_date: "2026-04-01"
  tasks_completed: 2
  files_changed: 8
---

# Phase 02 Plan 01: Skip Infrastructure and FSM Guard Summary

**One-liner:** SkipClient ABC with SoCo/Spotify implementations, ContentChecker explicit-flag tier, and FSM-guarded poll loop integration with structured skip logging.

## What Was Built

Plan 01 establishes the entire skip execution layer and family safe mode guard. The daemon can now detect explicit tracks, select the correct skip transport (SoCo for Sonos, Spotify API for everything else), and log all skip events in structured format. Plan 02 will inject the lyrics service and profanity scanner to activate tiers 2 and 3.

### skip_client.py

`SkipClient` ABC with two concrete implementations:

- **`SpotifySkipClient`**: wraps `sp.next_track(device_id)` in `run_in_executor` to avoid blocking the asyncio event loop. Catches `SpotifyException`, returns `False` on failure.
- **`SocoSkipClient`**: wraps SoCo discovery and `device.next()` in `run_in_executor`. After first successful discovery, caches the speaker IP to bypass slow SSDP multicast on subsequent skips. Falls back to re-discovery if cached IP fails.

### content_checker.py

`ContentChecker.check(track)` returns `(action, reason, severity)`:

- **Tier 1 (live):** Returns `("skip", "explicit", 3)` when `track["explicit"]` is True (FILT-01).
- **Tiers 2-3 (stubbed):** Conditioned on `self.lyrics_service is not None` — dormant until Plan 02 injects `LyricsService` and `ProfanityScanner`.
- Without lyrics service: returns `("allow", "no_lyrics_service", 0)`.

### daemon.py integration

- New imports: `ContentChecker`, `SocoSkipClient`, `SpotifySkipClient`
- `PROFANITY_MIN_SEVERITY` config constant from env (D-10)
- `poll_loop` signature expanded to accept `content_checker`, `soco_skip`, `spotify_skip`
- FSM guard block added after track-change detection:
  - Reads `state.get("family_safe_mode", False)` each cycle (D-06 — no startup cache)
  - Logs `[DEVICE] name=... is_restricted=...` on every track change (D-02)
  - Logs `[SCAN] track=... severity=... reason=... action=...` for all scanned tracks (D-09)
  - Logs `[SKIP] reason=... track=... artist=...` on successful skip (D-07)
  - Selects `soco_skip` if `is_restricted=True`, else `spotify_skip` (SKIP-03, D-01)
- OAuth scope expanded to `user-read-currently-playing user-modify-playback-state`
- `main()` instantiates `ContentChecker`, `SocoSkipClient`, `SpotifySkipClient` and passes to poll_loop

### Supporting file changes

- **setup_auth.py**: OAuth scope expanded (user must delete token cache and re-run `make auth`)
- **Makefile**: `fsm-on`, `fsm-off`, `fsm-status` targets using `docker compose exec` (D-05); `setup` target adds `touch lyrics_cache.db`
- **.env.example**: `PROFANITY_MIN_SEVERITY=2` and `LYRICS_DB_PATH=/app/lyrics_cache.db` documented
- **docker-compose.yml**: `./lyrics_cache.db:/app/lyrics_cache.db` bind mount added
- **requirements.txt**: `soco==0.30.14` added

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Create skip_client.py | 94e0064 | skip_client.py, requirements.txt |
| 2 | ContentChecker, daemon wiring, FSM targets | 9ce29c8 | content_checker.py, daemon.py, setup_auth.py, Makefile, .env.example, docker-compose.yml |

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

| File | Stub | Reason |
|------|------|--------|
| content_checker.py:58 | `if self.lyrics_service is not None and self.profanity_scanner is not None:` | Tiers 2-3 (LRCLIB lyrics + profanity scan) intentionally dormant until Plan 02 injects LyricsService and ProfanityScanner. Non-explicit tracks return `("allow", "no_lyrics_service", 0)`. |

These stubs are intentional: Plan 01's goal is explicit-flag skipping only. Plan 02 will wire in lyrics and profanity scanning.

## Self-Check: PASSED

All created files verified present. Both task commits confirmed in git log.

## User Action Required

After deploying this plan, the user must re-authenticate with the expanded OAuth scope:

1. Delete the cached token: `rm token_cache/.cache`
2. Re-run auth: `make auth`
3. Open the auth URL on your phone, approve, paste redirect URL back

This is required because `user-modify-playback-state` was not in the original token scope.
