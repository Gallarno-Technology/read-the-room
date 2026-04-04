---
phase: quick
plan: 260404-avv
subsystem: content_checker
tags: [lyrics, title-scan, drug-reference, sexual-content, profanity, tdd]
dependency_graph:
  requires: [content_checker.py lyrics_unavailable branch, all three scanner modules]
  provides: [Title-fallback scan on no-lyrics tracks]
  affects: [content_checker.py, tests/test_content_checker.py]
tech_stack:
  added: []
  patterns: [no-short-circuit scanner pattern (existing), title+artist concat scan text]
key_files:
  created: []
  modified:
    - content_checker.py
    - tests/test_content_checker.py
decisions:
  - Scan text is simple concat 'track_name artist_name' — no normalization
  - No-short-circuit: all three scanners always called in title-fallback path (same as lyrics path)
  - reason stays lyrics_unavailable when title scan is clean (no new reason value)
  - pre-existing test_soco_pause_uses_cached_ip failure in test_skip_client.py confirmed out-of-scope (pre-existing, unrelated to this plan)
metrics:
  duration: ~4 min
  completed: 2026-04-04
  tasks_completed: 1
  files_modified: 2
---

# Quick Task 260404-avv: Title-Fallback Scan When Lyrics Unavailable Summary

**One-liner:** Title+artist fallback scan in the lyrics_unavailable branch using all three enabled scanners before unconditionally allowing a track.

## What Was Done

When LRCLIB returns no lyrics for a non-instrumental track, the pipeline previously
returned `reason="lyrics_unavailable"` and allowed the track unconditionally. This
missed obvious cases where the track title itself contained a flagged term (e.g. a
song literally called "Cocaine").

The fix runs all three enabled scanners (profanity, drug, sexual) against the
`"{track_name} {artist_name}"` string before falling back to allow. The same
priority ordering (profanity > drug > sexual) and no-short-circuit contract
already used for the lyrics path is applied consistently.

## Commits

| Hash | Type | Description |
|------|------|-------------|
| 4c8fc80 | test | Add failing tests for title-fallback scan on no-lyrics tracks (RED) |
| 56974bb | feat | Scan title+artist when lyrics unavailable before allowing track (GREEN) |

## Tasks

| # | Name | Status | Commit |
|---|------|--------|--------|
| 1 | Add title-fallback scan in the lyrics_unavailable branch | Done | 56974bb |

## TDD Flow

- **RED (4c8fc80):** 6 new tests written and confirmed failing before implementation
- **GREEN (56974bb):** Implementation makes all 13 content_checker tests pass

## Test Results

- `pytest tests/test_content_checker.py`: 13 passed (7 existing + 6 new)
- `pytest tests/` (full suite): 61 passed (excluding pre-existing unrelated failure in test_skip_client.py)

## Deviations from Plan

None — plan executed exactly as written.

## Known Pre-Existing Issues (Out of Scope)

- `tests/test_skip_client.py::test_soco_pause_uses_cached_ip` fails before and after this change. Confirmed pre-existing and unrelated to this plan. Logged to deferred-items for tracking.

## Self-Check: PASSED

- `content_checker.py` modified: FOUND
- `tests/test_content_checker.py` modified: FOUND
- Commit 4c8fc80: FOUND
- Commit 56974bb: FOUND
- 13 tests pass: CONFIRMED
