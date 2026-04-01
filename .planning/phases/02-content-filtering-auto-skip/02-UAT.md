---
status: complete
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
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""

- truth: "explicit track on Spotify iOS device is skipped within ~2 seconds when FSM is on"
  status: failed
  reason: "User reported: fail, no skip log, playing on ios app"
  severity: blocker
  test: 4
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""

- truth: "LRCLIB API is reachable from within the Docker container; lyrics are fetched successfully"
  status: failed
  reason: "User reported: fail looks like no connection to lyric api"
  severity: blocker
  test: 8
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""

- truth: "SQLite lyrics cache returns [CACHE] hit on second play of same track"
  status: failed
  reason: "User reported: fail"
  severity: major
  test: 10
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""

- truth: "clean non-explicit track is allowed through with [SCAN] action=allow log"
  status: failed
  reason: "User reported: fail"
  severity: major
  test: 7
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""

- truth: "[SCAN] log entries include severity score for all code paths"
  status: failed
  reason: "User reported: can't test because of existing issue, but not seeing severity scores on the logs."
  severity: major
  test: 6
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""

- truth: "family_safe_mode persists in state.json across track changes (fsm-off stays off)"
  status: failed
  reason: "User reported: fsm-off set family_safe_mode to off, clobbered when song changes."
  severity: blocker
  test: 3
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""
