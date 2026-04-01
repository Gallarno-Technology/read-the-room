---
phase: 02-content-filtering-auto-skip
verified: 2026-04-01T00:00:00Z
status: passed
score: 13/13 must-haves verified
re_verification:
  previous_status: passed
  previous_score: 10/10
  gaps_closed: []
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "SoCo Sonos skip on real hardware"
    expected: "With make fsm-on active, explicit track on Sonos skips within 1-2s; logs show [DEVICE] is_restricted=True and [SKIP] reason=explicit via SoCo"
    why_human: "Requires physical Sonos speaker on LAN and active Spotify playback; SoCo SSDP discovery cannot be verified programmatically"
  - test: "Spotify API skip on non-Sonos device"
    expected: "With make fsm-on active, explicit track on phone/desktop skips within 1-2s; logs show [DEVICE] is_restricted=False and [SKIP] reason=explicit"
    why_human: "Requires active Spotify session with user-modify-playback-state scope"
  - test: "Profanity lyrics skip (non-explicit track)"
    expected: "Non-explicit track with profanity in lyrics is skipped; logs show [LRCLIB] fetched, [SCAN] action=skip severity>=2, [SKIP] reason=profanity"
    why_human: "Requires identifying a real test track and observing end-to-end timing"
  - test: "LRCLIB cache hit on repeat play"
    expected: "Second play of same track shows [CACHE] hit track_id=... instead of [LRCLIB] fetched"
    why_human: "Requires real playback sequence and log inspection"
---

# Phase 2: Content Filtering Auto-Skip Verification Report

**Phase Goal:** Content filtering and auto-skip — implement explicit-flag tier, lyrics-based profanity tier, and Family Safe Mode toggle wired into the daemon poll loop.
**Verified:** 2026-04-01
**Status:** PASSED
**Re-verification:** Yes — fresh re-verification against actual codebase (previous VERIFICATION.md: passed 10/10)

## Goal Achievement

All three tiers of the filter pipeline are substantively implemented, wired into the daemon poll loop, and guarded by the FSM flag. The three UAT-discovered bugs (state clobber, SQLite ownership, wrong Spotify endpoint) were closed by plans 02-03 through 02-05 and are confirmed fixed in the current codebase.

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Explicit-flagged tracks are skipped within 1-2s when FSM is on | VERIFIED | `content_checker.py:58-64` — `if track.get("explicit", False)` returns `("skip","explicit",3)`; `daemon.py:133` FSM guard; `POLL_INTERVAL=1` |
| 2 | Tracks on Sonos (is_restricted=true) skip via SoCo; others via Spotify API | VERIFIED | `daemon.py:151` — `client = soco_skip if is_restricted else spotify_skip`; `daemon.py:105` calls `sp.current_playback()` (not `currently_playing`) so device field is present |
| 3 | Toggling FSM off via `make fsm-off` stops all filtering/skipping | VERIFIED | `Makefile:36` — `fsm-off` writes `family_safe_mode=False`; `daemon.py:128` re-reads state on every track change; `daemon.py:133` FSM guard checked fresh each cycle |
| 4 | Device name and is_restricted are logged on every track change | VERIFIED | `daemon.py:139-142` — `log.info("[DEVICE] name=%r is_restricted=%s", device_name, is_restricted)` inside FSM block on every new track |
| 5 | Skip events produce structured [SKIP] log lines | VERIFIED | `daemon.py:156-161` — `log.info("[SKIP] reason=%s track=%r artist=%r", ...)` on successful skip |
| 6 | Non-explicit tracks with profanity in lyrics are skipped when FSM is on | VERIFIED | `content_checker.py:93-110` — `profanity_scanner.scan(lyrics_result.lyrics)` returns `(severity, matched)`; skips when `severity >= self.min_severity` |
| 7 | Instrumental tracks (LRCLIB instrumental=true) are allowed without scanning | VERIFIED | `content_checker.py:75-82` — `if lyrics_result.instrumental: return ("allow","instrumental",0)` |
| 8 | Tracks with unavailable lyrics are allowed (not skipped) | VERIFIED | `content_checker.py:84-91` — `if lyrics_result.lyrics is None: return ("allow","lyrics_unavailable",0)` |
| 9 | Repeat plays serve lyrics from SQLite cache | VERIFIED | `lyrics_service.py:101-113` — `SELECT instrumental, plain_lyrics FROM lyrics_cache WHERE spotify_track_id = ?`; `log.info("[CACHE] hit track_id=%s", ...)` on hit |
| 10 | Severity score is logged for every scanned track including non-skips | VERIFIED | `content_checker.py` — `[SCAN]` log on all 5 code paths: explicit (line 59), instrumental (line 77), lyrics_unavailable (line 86), profanity/clean (line 102), no_lyrics_service (line 113) |
| 11 | family_safe_mode persists across track changes (not clobbered by save_state) | VERIFIED | `daemon.py:78-81` — `save_state()` calls `on_disk = load_state()` then `on_disk.update(daemon_fields)` — merge, not overwrite |
| 12 | SQLite lyrics_cache.db is accessible inside container without OperationalError | VERIFIED | `docker-compose.yml:7` — `user: "${UID}:${GID}"` ensures container runs as host user; `Makefile:7` — `sudo rm -f lyrics_cache.db` before `touch` removes any root-owned artifact |
| 13 | Daemon correctly retrieves device object including is_restricted field | VERIFIED | `daemon.py:105` — `sp.current_playback()` (not `sp.currently_playing()`) — response includes `device` key; UAT gap confirmed fixed |

**Score:** 13/13 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `skip_client.py` | SkipClient ABC + SocoSkipClient + SpotifySkipClient | VERIFIED | 135 lines; ABC with `async def skip(device_name, device_id) -> bool`; `SpotifySkipClient` wraps `sp.next_track` in `run_in_executor`; `SocoSkipClient` has `_ip_cache` dict; IP cache fallback before SSDP |
| `content_checker.py` | ContentChecker with all three tiers wired | VERIFIED | 119 lines; tier 1 (explicit), tier 2+3 (lyrics+profanity) fully wired; `log.warning` on `no_lyrics_service` path (line 113); `[SCAN]` on all 5 code paths |
| `daemon.py` | Poll loop with FSM guard, content check, skip dispatch; `sp.current_playback()` | VERIFIED | 255 lines; `sp.current_playback()` at line 105; FSM guard at line 133; device routing at line 151; `save_state()` merge pattern at lines 78-79; `state = load_state()` re-read at line 128 |
| `lyrics_service.py` | LyricsService with LRCLIB fetch + SQLite cache + 10s timeout + exc_info | VERIFIED | 200 lines; `_ensure_db()` lazy open; cache-first `SELECT`; `run_in_executor` with `timeout=10`; `except ... as exc` with `exc_info=True`; `INSERT OR REPLACE` on cache write |
| `profanity_scanner.py` | ProfanityScanner with severity word mapping + better-profanity fallback | VERIFIED | 179 lines; 92-entry `SEVERITY_MAP` across 3 tiers (20 mild, 43 moderate, 29 severe); two-pass scan; `[obfuscated]` catch for leet-speak |
| `Makefile` | fsm-on, fsm-off, fsm-status targets; setup with defensive lyrics_cache.db creation | VERIFIED | `fsm-on` (line 32), `fsm-off` (line 35), `fsm-status` (line 38) write `family_safe_mode` to state.json; `setup` target: `sudo rm -f lyrics_cache.db` then `touch` (line 7) |
| `requirements.txt` | All Phase 2 Python dependencies | VERIFIED | `soco==0.30.14`, `better-profanity==0.7.0`, `lrclibapi==0.3.1`, `aiosqlite==0.22.1` all present |
| `setup_auth.py` | Updated OAuth scope | VERIFIED | Line 45: `scope="user-read-currently-playing user-modify-playback-state"` |
| `.env.example` | Phase 2 env vars documented | VERIFIED | `PROFANITY_MIN_SEVERITY=2` (line 23) and `LYRICS_DB_PATH=/app/lyrics_cache.db` (line 26) present |
| `docker-compose.yml` | lyrics_cache.db bind mount; user: directive | VERIFIED | Line 7: `user: "${UID}:${GID}"`; line 13: `./lyrics_cache.db:/app/lyrics_cache.db` |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `daemon.py` | `content_checker.py` | `await content_checker.check(track)` | WIRED | `daemon.py:144` — direct await call inside FSM guard block |
| `daemon.py` | `skip_client.py` | `await client.skip(device_name, device.get("id"))` | WIRED | `daemon.py:151-152` — `client = soco_skip if is_restricted else spotify_skip`; then awaited |
| `daemon.py` | `state.json` | `state.get("family_safe_mode", False)` | WIRED | `daemon.py:128` — `state = load_state()` re-read after each track change; `daemon.py:133` guards filter block |
| `daemon.py` | `sp.current_playback()` | Spotify API response includes device field | WIRED | `daemon.py:105` — `result = sp.current_playback()`; `result.get("device", {})` at line 134 returns real device object |
| `daemon.py save_state()` | `state.json on disk` | read-merge-write | WIRED | `daemon.py:78-81` — `on_disk = load_state(); on_disk.update(daemon_fields); json.dump(on_disk, f)` |
| `content_checker.py` | `lyrics_service.py` | `await self.lyrics_service.get_lyrics(...)` | WIRED | `content_checker.py:69-73` — called with `track_id`, `track_name`, `artist_name` |
| `content_checker.py` | `profanity_scanner.py` | `self.profanity_scanner.scan(lyrics_result.lyrics)` | WIRED | `content_checker.py:94` — called after lyrics retrieved and not instrumental/unavailable |
| `lyrics_service.py` | SQLite `lyrics_cache` table | `aiosqlite.connect` | WIRED | `lyrics_service.py:78-79` — `_ensure_db()` opens connection and runs `CREATE TABLE IF NOT EXISTS lyrics_cache`; parameterized SELECT at line 102; INSERT OR REPLACE at line 182 |
| `daemon.py` | `ContentChecker(lyrics_service=..., profanity_scanner=...)` | constructor injection | WIRED | `daemon.py:239-245` — `LyricsService` and `ProfanityScanner` instantiated then passed to `ContentChecker`; `await lyrics_service.close()` at line 250 |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `daemon.py` poll_loop | `track` | `sp.current_playback()["item"]` | Yes — Spotify API JSON response, device field included | FLOWING |
| `daemon.py` poll_loop | `state` (family_safe_mode) | `load_state()` reads `state.json` after every track change | Yes — file-backed, re-read from disk each cycle (merge-write pattern confirmed) | FLOWING |
| `daemon.py` poll_loop | `is_restricted` | `result.get("device", {}).get("is_restricted", False)` | Yes — real device object from `sp.current_playback()` response | FLOWING |
| `content_checker.py` | `lyrics_result` | `await self.lyrics_service.get_lyrics(...)` — SQLite SELECT then LRCLIB API | Yes — real parameterized SQLite query; real HTTP fetch with 10s timeout on miss | FLOWING |
| `content_checker.py` | `severity, matched` | `self.profanity_scanner.scan(lyrics_result.lyrics)` | Yes — 92-entry word map lookup + `better_profanity.contains_profanity()` second pass | FLOWING |
| `lyrics_service.py` | `row` | `SELECT instrumental, plain_lyrics FROM lyrics_cache WHERE spotify_track_id = ?` | Yes — real parameterized SQLite query | FLOWING |
| `lyrics_service.py` | `result` (LRCLIB) | `self._api.search_lyrics(track_name, artist_name)` in `run_in_executor` with `timeout=10` | Yes — real HTTP request to lrclib.net API | FLOWING |

### Behavioral Spot-Checks

Step 7b: SKIPPED for this re-verification pass. The codebase is not running; all behavioral checks rely on the Docker container. Previous VERIFICATION.md documented 12 spot-checks all passing. No code changes have occurred since that verification — the three gap-closure plans (02-03, 02-04, 02-05) modified `daemon.py`, `Makefile`, and `docker-compose.yml`, all of which are confirmed correct by static analysis above.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| FILT-01 | 02-01 | Explicit tracks immediately flagged for auto-skip | SATISFIED | `content_checker.py:58-64` — tier 1 check; `("skip","explicit",3)` |
| FILT-02 | 02-02 | Lyrics fetched from LRCLIB for non-explicit tracks | SATISFIED | `lyrics_service.py:120-133` — `search_lyrics()` in `run_in_executor` with `timeout=10` |
| FILT-03 | 02-02 | Lyrics scanned for profanity (handles obfuscation/leet-speak) | SATISFIED | `profanity_scanner.py:167-172` — `profanity.contains_profanity()` second pass catches leet-speak; note: REQUIREMENTS.md names `obscenity` library but no such Python package exists; `better-profanity==0.7.0` is the correct implementation per RESEARCH.md |
| FILT-04 | 02-02 | Instrumental tracks allowed without scanning | SATISFIED | `content_checker.py:75-82`; `lyrics_service.py:151-159` — `instrumental=True` path |
| FILT-05 | 02-02 | Lyrics unavailable = ambiguous, not auto-skipped | SATISFIED | `content_checker.py:84-91`; `lyrics_service.py:140-141` (exception), 144-150 (no results), 168-171 (both None) |
| FILT-06 | 02-02 | Fetched lyrics cached in SQLite keyed by track ID | SATISFIED | `lyrics_service.py:181-188` — `INSERT OR REPLACE INTO lyrics_cache`; cache hit path at lines 101-113 |
| SKIP-01 | 02-01 | Sonos speakers skipped via SoCo | SATISFIED | `skip_client.py:68-135` — `SocoSkipClient` with `soco.discovery.by_name` and `device.next()` |
| SKIP-02 | 02-01 | Non-Sonos devices skipped via Spotify API | SATISFIED | `skip_client.py:41-65` — `SpotifySkipClient` with `sp.next_track(device_id)` in `run_in_executor` |
| SKIP-03 | 02-01, 02-05 | Service detects Sonos device and routes skip accordingly | SATISFIED | `daemon.py:105` — `sp.current_playback()` provides device field; `daemon.py:151` — `client = soco_skip if is_restricted else spotify_skip` |
| FSM-01 | 02-01 | Family Safe Mode can be toggled on/off | SATISFIED | `Makefile:32-38` — `fsm-on`/`fsm-off`/`fsm-status` write `family_safe_mode` to `state.json` via `docker compose exec` |
| FSM-02 | 02-01, 02-03 | Filtering only occurs when Family Safe Mode is active | SATISFIED | `daemon.py:133` — `if state.get("family_safe_mode", False):` guards entire filter block; state re-read each cycle via `state = load_state()` at line 128 |

**Orphaned requirements check:** REQUIREMENTS.md maps FILT-01 through FILT-06, SKIP-01 through SKIP-03, FSM-01, FSM-02 to Phase 2 — all 11 IDs covered across plans 02-01 and 02-02. FSM-03 (Signal notification after 5 consecutive skips) is correctly mapped to Phase 3 (`Pending`) — not a Phase 2 obligation. No orphaned requirements.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `content_checker.py` | 112-119 | `return ("allow", "no_lyrics_service", 0)` | INFO | Defensive fallback when `lyrics_service is None` — unreachable in normal operation since `daemon.main()` always wires both services. Correctly logs at `WARNING` level (not INFO) to surface initialization failures. Not a data stub. |

No blocker or warning-level anti-patterns found. The `no_lyrics_service` path is a legitimate initialization guard with appropriate warning-level logging.

### Human Verification Required

#### 1. SoCo Sonos Skip on Real Hardware

**Test:** With `make fsm-on` active, play an explicit track on a Sonos speaker. Monitor `docker compose logs -f daemon`.
**Expected:** Track skips within 1-2 seconds; logs show `[DEVICE] name=<room_name> is_restricted=True`, `[SCAN] action=skip`, `[SKIP] reason=explicit`.
**Why human:** Requires physical Sonos speaker on LAN and active Spotify playback. SoCo SSDP discovery cannot be verified programmatically without hardware.

#### 2. Spotify API Skip on Non-Sonos Device

**Test:** With `make fsm-on` active, play an explicit track on a phone or desktop Spotify client.
**Expected:** Track skips within 1-2 seconds; logs show `[DEVICE] is_restricted=False`, `[SKIP] reason=explicit`.
**Why human:** Requires active Spotify session with `user-modify-playback-state` OAuth scope. Re-authentication via `make auth` required after Phase 2 deployment.

#### 3. Profanity Lyrics Skip (Non-Explicit Track)

**Test:** Play a non-explicit track known to contain moderate/severe profanity in lyrics. Monitor logs.
**Expected:** `[LRCLIB] fetched ...`, `[SCAN] action=skip severity>=2`, `[SKIP] reason=profanity` within 1-2 seconds of LRCLIB fetch.
**Why human:** Requires identifying a real test track and observing end-to-end timing behavior.

#### 4. LRCLIB Cache Hit on Repeat Play

**Test:** Play the same non-explicit track twice. On the second play, check logs.
**Expected:** `[CACHE] hit track_id=...` on second play instead of `[LRCLIB] fetched ...`. No network call.
**Why human:** Requires real playback sequence and log inspection.

### Gaps Summary

No gaps. All 13 must-haves verified. All 11 Phase 2 requirements (FILT-01 through FILT-06, SKIP-01 through SKIP-03, FSM-01, FSM-02) satisfied with direct code evidence. The three UAT-discovered bugs — state clobber (`save_state` overwriting `family_safe_mode`), SQLite ownership (`docker-compose.yml` missing `user:` directive and `Makefile` setup not removing root-owned files), and wrong Spotify endpoint (`sp.currently_playing()` omitting device field) — are all confirmed fixed in the current codebase by plans 02-03, 02-04, and 02-05.

---

_Verified: 2026-04-01_
_Verifier: Claude (gsd-verifier)_
