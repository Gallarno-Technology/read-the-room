---
status: diagnosed
phase: 02-content-filtering-auto-skip
source: [02-01-SUMMARY.md, 02-02-SUMMARY.md, 02-03-SUMMARY.md, 02-04-SUMMARY.md]
started: 2026-04-01T00:00:00Z
updated: 2026-04-01T00:00:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Cold Start Smoke Test
expected: Kill any running container. Run `make setup` (to ensure lyrics_cache.db exists), then `docker compose down` followed by `docker compose up --build`. The daemon boots without errors, connects to Spotify, and starts polling. No crash, no missing-module errors in the logs.
result: issue
reported: "make setup fails: touch: setting times of 'lyrics_cache.db': Permission denied. Daemon starts and polls but no severity scores in logs."
severity: major

### 2. FSM Toggle — On (persists across track changes)
expected: Run `make fsm-on`. Check state.json — `family_safe_mode` should be `true`. Wait for or trigger a track change. Check state.json again — `family_safe_mode` should still be `true` (not dropped). Daemon log should continue running normally with no restart.
result: issue
reported: "turned on, persists across song changes, but ERROR on every track change: unable to open database file (sqlite3.OperationalError) — aiosqlite.connect fails on lyrics_cache.db bind mount"
severity: blocker

### 3. FSM Toggle — Off (persists across track changes)
expected: Run `make fsm-off`. Check state.json — `family_safe_mode` should be `false`. Trigger a track change. Check state.json again — `family_safe_mode` should still be `false`. No scan or skip activity in the logs.
result: pass

### 4. Explicit Track Skip (Spotify device)
expected: With FSM on, play an explicit track (Spotify-marked explicit) on a non-Sonos device (iOS, desktop). The daemon logs `[DEVICE]`, `[SCAN] ... action=skip`, and `[SKIP] reason=explicit` and the track advances to the next one within ~2 seconds.
result: pass

### 5. Explicit Track Skip (Sonos)
expected: With FSM on, play an explicit track on a Sonos speaker. The daemon detects `is_restricted=True`, logs `[DEVICE] is_restricted=True`, and uses SoCo to call next() — track advances on the Sonos device.
result: issue
reported: "Device shows name='unknown' is_restricted=False — Sonos not detected. SpotifySkipClient used instead of SoCo, gets 403 Restricted device from Spotify API. [SKIP_FAILED] logged."
severity: blocker

### 6. Profanity Scan — Skip on Moderate/Severe Words
expected: With FSM on, play a non-explicit track (Spotify explicit flag = false) that contains moderate or severe profanity in its lyrics. The daemon fetches lyrics from LRCLIB, scans them, and skips the track. Log shows `[SCAN] severity=2` (or 3) `action=skip`. The severity score appears in the log line.
result: blocked
blocked_by: prior-issue
reason: "Same sqlite3.OperationalError: unable to open database file — lyrics service unreachable until SQLite bind mount is fixed"

### 7. Profanity Scan — Allow Clean Track
expected: With FSM on, play a clean non-explicit track. The daemon fetches lyrics, scans, finds no profanity at or above the threshold, and allows it. Log shows `[SCAN] severity=0 action=allow` or `[SCAN] severity=1 action=allow`.
result: blocked
blocked_by: prior-issue
reason: "Blocked by SQLite bind mount failure — lyrics service unreachable"

### 8. Instrumental Track — Allowed Without Scan
expected: With FSM on, play an instrumental track (one LRCLIB marks as instrumental). The daemon allows it immediately — log shows `[SCAN] ... action=allow` with reason `instrumental`. No profanity scan attempted.
result: blocked
blocked_by: prior-issue
reason: "Blocked by SQLite bind mount failure — lyrics service unreachable"

### 9. Lyrics Unavailable — Allowed
expected: With FSM on, play a track LRCLIB has no lyrics for. The daemon logs `[SCAN] severity=0 action=allow` with reason `lyrics_unavailable` and the track plays normally.
result: blocked
blocked_by: prior-issue
reason: "Blocked by SQLite bind mount failure — lyrics service unreachable"

### 10. Lyrics Cache Hit
expected: Play any track that was already scanned once (lyrics fetched from LRCLIB). On the second play, the daemon log should show `[CACHE] hit` rather than a fresh LRCLIB API call — the lyrics come from the local SQLite database.
result: blocked
blocked_by: prior-issue
reason: "Blocked by SQLite bind mount failure — cache is never populated"

## Summary

total: 10
passed: 2
issues: 3
pending: 0
skipped: 0
blocked: 5

## Gaps

- truth: "make setup completes without error and lyrics_cache.db is created/touched successfully"
  status: failed
  reason: "User reported: make setup fails: touch: setting times of 'lyrics_cache.db': Permission denied. Daemon starts and polls but no severity scores in logs."
  severity: major
  test: 1
  root_cause: "Docker auto-creates lyrics_cache.db as a root-owned directory (or root-owned file) on first run. Subsequent make setup fails because the host user can't touch a root-owned path. When mounted, aiosqlite.connect() gets EACCES or tries to open a directory as a SQLite file — both fatal."
  artifacts:
    - path: "Makefile"
      issue: "setup target: `touch lyrics_cache.db` is unconditional — fails if root-owned artifact already exists"
    - path: "docker-compose.yml"
      issue: "no user: directive — daemon runs as root inside container, creating root-owned bind-mount files"
  missing:
    - "Makefile setup target must defensively remove root-owned artifacts or use sudo chown before touch"
    - "docker-compose.yml should set user: \"${UID}:${GID}\" so container files are owned by the host user"
  debug_session: ""

- truth: "daemon poll loop completes content check on every track change without ERROR"
  status: failed
  reason: "User reported: FSM persists correctly, but every track change throws ERROR: sqlite3.OperationalError: unable to open database file — aiosqlite cannot open the lyrics_cache.db bind mount"
  severity: blocker
  test: 2
  root_cause: "Downstream of the same lyrics_cache.db ownership/mount issue as test 1. The container process cannot open the bind-mounted file for read/write. All five lyrics-dependent tests (6–10) are blocked by this."
  artifacts:
    - path: "lyrics_service.py"
      issue: "_ensure_db() calls aiosqlite.connect(db_path) — fails with EACCES or directory-open error on root-owned bind mount"
  missing:
    - "Fix Makefile + docker-compose.yml (same fix as test 1)"
  debug_session: ""

- truth: "Sonos speaker is detected as is_restricted=True and SoCo is used to skip the track"
  status: failed
  reason: "User reported: Device shows name='unknown' is_restricted=False — Sonos not detected. SpotifySkipClient used instead of SoCo, gets 403 Restricted device from Spotify API. [SKIP_FAILED] logged."
  severity: blocker
  test: 5
  root_cause: "daemon.py calls sp.currently_playing() (GET /me/player/currently-playing) which does not include a device object in its response. The device key is only present in sp.current_playback() (GET /me/player). result.get('device', {}) always returns {} so is_restricted defaults to False and SpotifySkipClient is always selected."
  artifacts:
    - path: "daemon.py"
      issue: "Line 105: sp.currently_playing() used instead of sp.current_playback() — response lacks device field"
    - path: "daemon.py"
      issue: "Lines 134-136: result.get('device', {}) always returns {} — name and is_restricted silently default"
  missing:
    - "Replace sp.currently_playing() with sp.current_playback() on line 105 — device object then present in response"
  debug_session: ".planning/debug/sonos-not-detected.md"
