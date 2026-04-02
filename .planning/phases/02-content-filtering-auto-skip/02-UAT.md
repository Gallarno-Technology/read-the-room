---
status: complete
phase: 02-content-filtering-auto-skip
source: [02-01-SUMMARY.md, 02-02-SUMMARY.md, 02-03-SUMMARY.md, 02-04-SUMMARY.md, 02-05-SUMMARY.md]
started: 2026-04-01T00:00:00Z
updated: 2026-04-02T13:30:00Z
---

## Current Test

[testing complete — all gaps resolved 2026-04-02]

## Tests

### 1. Cold Start Smoke Test
expected: Kill any running container. Run `make setup` (to create lyrics_cache.db as the host user), then `docker compose up --build`. The daemon boots without errors, connects to Spotify, and starts polling. `make setup` must complete without "Permission denied". No crash, no missing-module errors in the logs.
result: pass

### 2. FSM Toggle — On (persists across track changes)
expected: Run `make fsm-on`. Check state.json — `family_safe_mode` should be `true`. Wait for or trigger a track change. Check state.json again — `family_safe_mode` should still be `true` (not dropped). Daemon log should continue running normally with no sqlite3.OperationalError.
result: pass

### 3. FSM Toggle — Off (persists across track changes)
expected: Run `make fsm-off`. Check state.json — `family_safe_mode` should be `false`. Trigger a track change. Check state.json again — `family_safe_mode` should still be `false`. No scan or skip activity in the logs.
result: pass

### 4. Explicit Track Skip (Spotify device)
expected: With FSM on, play an explicit track (Spotify-marked explicit) on a non-Sonos device (iOS, desktop). The daemon logs `[DEVICE]`, `[SCAN] ... action=skip`, and `[SKIP] reason=explicit` and the track advances to the next one within ~2 seconds.
result: pass

### 5. Explicit Track Skip (Sonos)
expected: With FSM on, play an explicit track on a Sonos speaker. The daemon detects `is_restricted=True`, logs `[DEVICE] is_restricted=True`, and uses SoCo to call next() — track advances on the Sonos device.
result: pass

### 6. Profanity Scan — Skip on Moderate/Severe Words
expected: With FSM on, play a non-explicit track (Spotify explicit flag = false) that contains moderate or severe profanity in its lyrics. The daemon fetches lyrics from LRCLIB, scans them, and skips the track. Log shows `[SCAN] severity=2` (or 3) `action=skip`. The severity score appears in the log line.
result: pass

### 7. Profanity Scan — Allow Clean Track
expected: With FSM on, play a clean non-explicit track. The daemon fetches lyrics, scans, finds no profanity at or above the threshold, and allows it. Log shows `[SCAN] severity=0 action=allow` or `[SCAN] severity=1 action=allow`.
result: pass

### 8. Instrumental Track — Allowed Without Scan
expected: With FSM on, play an instrumental track (one LRCLIB marks as instrumental). The daemon allows it immediately — log shows `[SCAN] ... action=allow` with reason `instrumental`. No profanity scan attempted.
result: pass

### 9. Lyrics Unavailable — Allowed
expected: With FSM on, play a track LRCLIB has no lyrics for. The daemon logs `[SCAN] severity=0 action=allow` with reason `lyrics_unavailable` and the track plays normally.
result: pass

### 10. Lyrics Cache Hit
expected: Play any track that was already scanned once (lyrics fetched from LRCLIB). On the second play, the daemon log should show `[CACHE] hit` rather than a fresh LRCLIB API call — the lyrics come from the local SQLite database.
result: pass

## Summary

total: 10
passed: 10
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

- truth: "make setup completes without Permission denied when lyrics_cache.db is a root-owned directory"
  status: failed
  reason: "User reported: make setup still fails with Permission denied when lyrics_cache.db is a root-owned directory (not file). Makefile guard uses -f which skips directories. Required manual sudo rm -rf lyrics_cache.db first."
  severity: major
  test: 1
  root_cause: "Makefile line 7 guard uses `[ ! -f lyrics_cache.db ]` which only matches regular files — when Docker created lyrics_cache.db as a root-owned directory, the condition is false, sudo rm is skipped, and touch fails with Permission denied."
  artifacts:
    - path: "Makefile"
      issue: "Line 7: [ ! -f lyrics_cache.db ] does not match directories — sudo rm -f never fires when lyrics_cache.db is a directory"
  missing:
    - "Replace -f guard with compound check: detect -d branch (sudo rm -rf) and -f branch (sudo rm -f) before touch, or use -e to catch both"
  debug_session: ""

- truth: "Instrumental track is allowed immediately without running a profanity scan (reason=instrumental in log)"
  status: failed
  reason: "User reported: LRCLIB correctly returns instrumental=True has_lyrics=False, but the scan still runs and logs severity=0 matched=[] action=allow instead of short-circuiting with reason=instrumental."
  severity: minor
  test: 8
  root_cause: "content_checker.py line 78 log.info call in the instrumental branch uses the same format string as a full scan (no reason field), so the log is indistinguishable from a clean scan — the return value and early-exit logic are already correct."
  artifacts:
    - path: "content_checker.py"
      issue: "Line 78: log.info format string omits reason=instrumental — log output matches a zero-score full scan"
    - path: "content_checker.py"
      issue: "Line 87: same omission for lyrics_unavailable branch"
  missing:
    - "Add reason=instrumental to log.info on line 78"
    - "Add reason=lyrics_unavailable to log.info on line 87 for consistency"
  debug_session: ""

- truth: "Sonos speaker is found by SoCo and track is skipped via SoCo next()"
  status: failed
  reason: "User reported: is_restricted=True detected correctly and SoCo is selected, but SoCo can't find the speaker — 'Playroom' (Spotify device name) doesn't match the Sonos room name exactly. SKIP_FAILED."
  severity: blocker
  test: 5
  root_cause: "SocoSkipClient.skip passes the raw Spotify device name to soco.discovery.by_name which does a strict case-sensitive equality check — any difference in casing, spacing, or punctuation causes discovery to return None."
  artifacts:
    - path: "skip_client.py"
      issue: "Lines 108-109: soco.discovery.by_name(device_name) called with raw Spotify name, no normalization"
  missing:
    - "Replace soco.discovery.by_name with soco.discovery.discover() + iterate with .strip().lower() comparison on both sides"
  debug_session: ""
