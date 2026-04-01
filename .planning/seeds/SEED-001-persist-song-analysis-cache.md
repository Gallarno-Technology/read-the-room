---
id: SEED-001
status: dormant
planted: 2026-04-01
planted_during: v1.0 / Phase 2 complete
trigger_when: when performance or scale becomes a priority
scope: medium
---

# SEED-001: Persist song analysis to prevent re-evaluating the same song multiple times

## Why This Matters

Currently `ContentChecker.check()` re-runs the full three-tier pipeline on every
track play — even for tracks seen before. This means:

1. **Redundant LRCLIB API calls** — lyrics are already cached in `lyrics_cache`
   (SQLite, keyed by Spotify track ID), but the profanity scan and severity scoring
   run again from scratch every time.
2. **Slower skip decisions** — the full scan pipeline adds latency before a skip
   fires. Persisting the final `(action, reason, severity)` tuple per track ID
   would make repeat-track decisions near-instant.

The SQLite infrastructure is already in place (`lyrics_service.py`). Adding an
`analysis_cache` table alongside `lyrics_cache` is a natural extension.

## When to Surface

**Trigger:** When a milestone focuses on performance, efficiency, or handling high
track volumes (e.g., multi-room playback, multi-account support, or analytics).

This seed should be presented during `/gsd:new-milestone` when the milestone
scope matches any of these conditions:
- Milestone mentions performance, latency, or efficiency
- Milestone involves scale (multiple users, rooms, or devices)
- Milestone adds analytics or history features (where cached decisions are useful input)
- Repeated-track skip latency is reported as a user pain point

## Scope Estimate

**Medium** — A phase or two. SQLite is already in place, but this needs:
- Schema design for `analysis_cache` table (track_id, action, reason, severity, scanned_at, lyrics_version)
- Cache invalidation strategy (TTL? manual invalidation on word-list changes?)
- Integration point in `ContentChecker.check()` — cache lookup before Tier 1
- Migration / backfill considerations if lyrics_cache already has data

## Breadcrumbs

Relevant code in the current codebase:

- `lyrics_service.py:27` — `lyrics_cache` SQLite table schema (model for new table)
- `lyrics_service.py:87` — `get_lyrics()` cache-first lookup pattern to replicate
- `content_checker.py:39` — `ContentChecker.check()` — where the cache lookup should be inserted
- `content_checker.py:94` — `profanity_scanner.scan()` — the expensive step to skip on cache hit
- `profanity_scanner.py` — severity scoring logic; any word-list version bump should invalidate analysis cache

## Notes

- The `LyricsResult.cached` field already distinguishes cache hits from fresh fetches
  (added in Phase 2). The same pattern applies here.
- STATE.md records: "LyricsResult.cached field added to distinguish SQLite cache hits
  from fresh LRCLIB fetches" — analysis cache should add a similar `from_cache` flag
  for observability.
- Consider: if the profanity word list changes, existing analysis cache entries become
  stale. A schema version column or a hash of the word list config could handle this.
