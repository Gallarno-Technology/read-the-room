---
status: diagnosed
phase: 02-content-filtering-auto-skip
source: [02-01-SUMMARY.md, 02-02-SUMMARY.md]
started: 2026-04-01T00:00:00Z
updated: 2026-04-01T00:00:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Cold Start Smoke Test
expected: Kill any running container. Run `docker compose down` then `docker compose up --build`. The daemon boots without errors, connects to Spotify, and starts polling. No crash, no missing-module errors, and the lyrics_cache.db bind mount is created if absent.
result: pass

### 2. FSM Toggle — On
expected: Run `make fsm-on` (inside container or via docker compose exec). Then check state.json — `family_safe_mode` should be `true`. The daemon log should continue running normally with no restart needed.
result: issue
reported: "fsm-on sets family_safe_mode on, but Explicit songs don't skip. Upon looking at state after a song changes, the family_safe_mode is removed."
severity: blocker

### 3. FSM Toggle — Off
expected: Run `make fsm-off`. Check state.json — `family_safe_mode` should be `false`. Tracks that were being scanned are now allowed through without evaluation.
result: issue
reported: "fsm-off set family_safe_mode to off, clobbered when song changes."
severity: blocker

### 4. Explicit Track Skip (Spotify device)
expected: With FSM on, play an explicit track (Spotify-marked explicit) on a non-Sonos device. The daemon logs `[SCAN] ... action=skip` and `[SKIP] reason=explicit ...` and the track advances to the next one within ~2 seconds.
result: issue
reported: "fail, no skip log, playing on ios app"
severity: blocker

### 5. Explicit Track Skip (Sonos)
expected: With FSM on, play an explicit track on a Sonos speaker. The daemon detects `is_restricted=True`, logs `[DEVICE] is_restricted=True`, and uses SoCo to call next() — track advances on the Sonos device.
result: skipped

### 6. Profanity Scan — Skip on Moderate/Severe Words
expected: With FSM on, play a non-explicit track (Spotify explicit flag = false) that contains moderate or severe profanity in its lyrics. The daemon fetches lyrics from LRCLIB, scans them, and skips the track. Log shows `[SCAN] severity=2 (or 3) action=skip`.
result: issue
reported: "can't test because of existing issue, but not seeing severity scores on the logs."
severity: major

### 7. Profanity Scan — Allow Clean Track
expected: With FSM on, play a clean non-explicit track. The daemon fetches lyrics, scans, finds no profanity at or above the threshold, and allows it. Log shows `[SCAN] severity=0 action=allow` or `[SCAN] severity=1 action=allow`.
result: issue
reported: "fail"
severity: major

### 8. Instrumental Track — Allowed Without Scan
expected: With FSM on, play an instrumental track (one LRCLIB marks as instrumental). The daemon allows it immediately — log shows `[SCAN] severity=0 matched=[] action=allow` with reason `instrumental`. No profanity scan attempted.
result: issue
reported: "fail looks like no connection to lyric api"
severity: blocker

### 9. Lyrics Unavailable — Allowed
expected: With FSM on, play a track LRCLIB has no lyrics for. The daemon logs `[SCAN] severity=0 matched=[] action=allow` with reason `lyrics_unavailable` and the track plays normally.
result: skipped

### 10. Lyrics Cache Hit
expected: Play any track that was already scanned once (lyrics fetched from LRCLIB). On the second play, the daemon log should show `[CACHE] hit` rather than a fresh LRCLIB API call — the lyrics come from the local SQLite database.
result: issue
reported: "fail"
severity: major

## Summary

total: 10
passed: 1
issues: 7
pending: 0
skipped: 2
blocked: 0

## Gaps

- truth: "family_safe_mode persists in state.json across track changes; explicit tracks are skipped when FSM is on"
  status: failed
  reason: "User reported: fsm-on sets family_safe_mode on, but Explicit songs don't skip. Upon looking at state after a song changes, the family_safe_mode is removed."
  severity: blocker
  test: 2
  root_cause: "daemon.py save_state() (line 68-76) does a blind json.dump — no read-merge. daemon loads state once at startup; any key written externally after start is absent from the in-memory dict and gets dropped on next save (line 123). FSM check at line 128 also reads from stale in-memory dict, never re-reads disk."
  artifacts:
    - path: "daemon.py"
      issue: "save_state() blindly overwrites state.json without merging existing keys (line 68-76)"
    - path: "daemon.py"
      issue: "FSM flag read from stale in-memory dict at line 128, not from disk each poll cycle"
  missing:
    - "save_state() must read disk, merge daemon fields on top, then write back"
    - "FSM flag must be re-read from disk each poll cycle (D-06 comment promises this but code does not)"
  debug_session: ""

- truth: "explicit track on Spotify iOS device is skipped within ~2 seconds when FSM is on"
  status: failed
  reason: "User reported: fail, no skip log, playing on ios app"
  severity: blocker
  test: 4
  root_cause: "Downstream of state.json clobber — FSM is never active so ContentChecker never evaluates tracks for skipping."
  artifacts:
    - path: "daemon.py"
      issue: "state.get('family_safe_mode', False) always False due to stale in-memory state"
  missing:
    - "Fix state.json clobber (same fix as test 2) — explicit skip will work once FSM persists"
  debug_session: ""

- truth: "LRCLIB API is reachable from within the Docker container; lyrics are fetched successfully"
  status: failed
  reason: "User reported: fail looks like no connection to lyric api"
  severity: blocker
  test: 8
  root_cause: "Two issues: (1) lyrics_service.py exception handler (line 131) does not bind the exception variable, so connection errors are swallowed silently with no detail in logs. (2) No timeout on the run_in_executor call — a stalling connection hangs the executor thread indefinitely. Network mode is host (correct). Also: lyrics_cache.db bind-mount must pre-exist on host before docker compose up or LyricsService construction may fail."
  artifacts:
    - path: "lyrics_service.py"
      issue: "except clause at line 131 does not bind exc; log.warning at line 133 discards exception type and message"
    - path: "lyrics_service.py"
      issue: "No asyncio.wait_for timeout wrapping run_in_executor call — stalling connections block executor threads"
    - path: "docker-compose.yml"
      issue: "lyrics_cache.db bind-mount requires host file to pre-exist; missing touch before first compose up"
  missing:
    - "Change except clause to bind exc: except (...) as exc:"
    - "Add exc_info=True and %s exc to log.warning for full error visibility"
    - "Wrap run_in_executor call with asyncio.wait_for(..., timeout=10)"
    - "Ensure touch lyrics_cache.db runs on host before docker compose up"
  debug_session: ""

- truth: "SQLite lyrics cache returns [CACHE] hit on second play of same track"
  status: failed
  reason: "User reported: fail"
  severity: major
  test: 10
  root_cause: "Downstream of LRCLIB connectivity failure — no lyrics are fetched so nothing is written to the SQLite cache. Cache hit path is unreachable until LRCLIB connection is fixed."
  artifacts:
    - path: "lyrics_service.py"
      issue: "Cache never populated due to LRCLIB fetch failures"
  missing:
    - "Fix LRCLIB connectivity (same fix as test 8) — cache hit will work once lyrics are fetched"
  debug_session: ""

- truth: "clean non-explicit track is allowed through with [SCAN] action=allow log"
  status: failed
  reason: "User reported: fail"
  severity: major
  test: 7
  root_cause: "Downstream of state.json clobber — FSM never active so poll loop never reaches ContentChecker scan. Also downstream of LRCLIB failure — even with FSM on, LyricsService may be falling through to no_lyrics_service fallback."
  artifacts:
    - path: "daemon.py"
      issue: "FSM guard never triggers due to state.json clobber"
  missing:
    - "Fix state.json clobber and LRCLIB connectivity — allow path will work once both are fixed"
  debug_session: ""

- truth: "[SCAN] log entries include severity score for all code paths"
  status: failed
  reason: "User reported: can't test because of existing issue, but not seeing severity scores on the logs."
  severity: major
  test: 6
  root_cause: "content_checker.py no_lyrics_service fallback path (lines 113-117) logs severity=0 at INFO level with no warning. If LyricsService construction fails (e.g. missing lyrics_cache.db), the daemon falls through to this path on every track — all [SCAN] lines show severity=0. The profanity scan path (lines 102-109) uses %d correctly but is unreachable when LyricsService is None."
  artifacts:
    - path: "content_checker.py"
      issue: "no_lyrics_service fallback at line 113 logs at INFO with hardcoded severity=0, no warning that lyrics service is missing"
  missing:
    - "Change no_lyrics_service log to log.warning with explanatory prefix"
    - "Fix LyricsService initialization (lyrics_cache.db pre-creation) so profanity scan path is reached"
  debug_session: ""

- truth: "family_safe_mode persists in state.json across track changes (fsm-off stays off)"
  status: failed
  reason: "User reported: fsm-off set family_safe_mode to off, clobbered when song changes."
  severity: blocker
  test: 3
  root_cause: "Same root cause as test 2 — daemon.py save_state() blind overwrite drops family_safe_mode key on next track change."
  artifacts:
    - path: "daemon.py"
      issue: "save_state() at line 68-76 does full overwrite with no read-merge"
  missing:
    - "Same fix as test 2 — save_state() must read-merge before writing"
  debug_session: ""
