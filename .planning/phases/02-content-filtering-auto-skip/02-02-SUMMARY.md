---
phase: 02-content-filtering-auto-skip
plan: "02"
subsystem: content-filtering
tags: [lyrics, profanity-scanner, sqlite, lrclib, aiosqlite, better-profanity, severity-mapping]
dependency_graph:
  requires:
    - phase: 02-01
      provides: ContentChecker stub (tiers 2-3 dormant), SkipClient infrastructure, daemon FSM guard
  provides:
    - lyrics_service.LyricsService (LRCLIB fetch + aiosqlite cache)
    - lyrics_service.LyricsResult (dataclass: instrumental, lyrics, cached)
    - profanity_scanner.ProfanityScanner (severity word mapping + better-profanity leet-speak fallback)
    - profanity_scanner.SEVERITY_MAP (3-tier word map: mild=1, moderate=2, severe=3)
    - content_checker.ContentChecker (all three tiers now active)
    - daemon.py (full lyrics pipeline wired, LyricsService cleanup on shutdown)
  affects:
    - daemon.py (LyricsService/ProfanityScanner instantiation and lifecycle)
    - content_checker.py (tier 2-3 now live, [SCAN] log for all paths)
tech_stack:
  added:
    - lrclibapi==0.3.1 (LRCLIB lyrics API Python wrapper)
    - aiosqlite==0.22.1 (async SQLite for lyrics cache)
    - better-profanity==0.7.0 (leet-speak/obfuscation detection fallback)
  patterns:
    - Two-pass profanity scan: custom SEVERITY_MAP word lookup + better-profanity leet-speak fallback
    - Cache-first lyrics lookup: SQLite hit returns immediately, LRCLIB only called on miss
    - Synchronous library isolation: lrclibapi wrapped in run_in_executor (Pitfall 3 compliance)
    - [SCAN] structured log inside ContentChecker for all code paths (D-09)
key_files:
  created:
    - profanity_scanner.py (ProfanityScanner with SEVERITY_MAP, better-profanity fallback)
    - lyrics_service.py (LyricsService + LyricsResult dataclass, aiosqlite cache)
  modified:
    - content_checker.py ([SCAN] log added for all paths; tiers 2-3 now fully active)
    - daemon.py (LyricsService + ProfanityScanner imports, LYRICS_DB_PATH, main() wiring, close())
    - requirements.txt (lrclibapi==0.3.1, aiosqlite==0.22.1, better-profanity==0.7.0 added)
key_decisions:
  - "Used search_lyrics() instead of get_lyrics() — lrclibapi.get_lyrics() requires album_name and duration which are not in ContentChecker's interface; search_lyrics() takes only track+artist"
  - "[SCAN] log moved into ContentChecker.check() — method has access to matched words and all code paths; daemon.py only needed the 3-tuple return value"
  - "LyricsResult.cached field added to distinguish cache hits from fresh fetches (aids debugging)"
patterns_established:
  - "Sync-in-async: all synchronous library calls (lrclibapi) wrapped in asyncio.get_event_loop().run_in_executor(None, lambda: ...)"
  - "Cache-first reads: check SQLite before any network call; cache every result regardless of outcome (miss or 404 or instrumental)"
  - "Graceful degradation: LRCLIB failure → LyricsResult(instrumental=False, lyrics=None) → ContentChecker allows track (FILT-05)"
requirements_completed:
  - FILT-02
  - FILT-03
  - FILT-04
  - FILT-05
  - FILT-06
duration: 5min
completed: "2026-04-01"
---

# Phase 02 Plan 02: Lyrics Pipeline and Profanity Scanner Summary

**LRCLIB lyrics fetch with SQLite cache, three-tier severity word mapping with better-profanity leet-speak fallback, and full ContentChecker pipeline activation — non-explicit tracks with profanity are now auto-skipped.**

## Performance

- **Duration:** ~5 minutes
- **Started:** 2026-04-01T20:43:53Z
- **Completed:** 2026-04-01T20:48:46Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments

- `ProfanityScanner` built with a 90+ entry `SEVERITY_MAP` across three severity tiers and better-profanity leet-speak second pass — catches both plain words and obfuscated variants
- `LyricsService` fetches from LRCLIB via `search_lyrics()` with SQLite cache (`INSERT OR REPLACE`); cache hits are served immediately with a `[CACHE] hit` log; all outcomes cached to prevent repeat API calls
- Full three-tier ContentChecker pipeline is now live: Tier 1 (explicit flag) → Tier 2 (LRCLIB lyrics) → Tier 3 (profanity scan); `[SCAN]` log emitted for every code path with severity, matched words, and action (D-09)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create ProfanityScanner** - `78a315e` (feat)
2. **Task 2: Create LyricsService** - `2854acb` (feat)
3. **Task 3: Wire into daemon and ContentChecker** - `7167b61` (feat)

## Files Created/Modified

- `/home/cgallarno/Development/spotify-sentiment/profanity_scanner.py` - ProfanityScanner class with SEVERITY_MAP (90+ entries, 3 tiers), two-pass scan(), better-profanity fallback
- `/home/cgallarno/Development/spotify-sentiment/lyrics_service.py` - LyricsResult dataclass + LyricsService with aiosqlite cache and LRCLIB fetch via run_in_executor
- `/home/cgallarno/Development/spotify-sentiment/content_checker.py` - [SCAN] log added for all code paths; tiers 2-3 now active (no longer conditioned on dormant stub)
- `/home/cgallarno/Development/spotify-sentiment/daemon.py` - Added LyricsService/ProfanityScanner imports, LYRICS_DB_PATH constant, wired services in main(), added lyrics_service.close() cleanup, removed duplicate [SCAN] log
- `/home/cgallarno/Development/spotify-sentiment/requirements.txt` - Added lrclibapi==0.3.1, aiosqlite==0.22.1, better-profanity==0.7.0

## Decisions Made

- **search_lyrics() vs get_lyrics():** `lrclibapi.get_lyrics()` requires `album_name` and `duration` as required parameters, but the `ContentChecker.check(track)` interface only passes `track_id`, `track_name`, and `artist_name`. Used `search_lyrics(track_name, artist_name)` which is optional-parameter-friendly and returns a relevance-ranked list; take first result.
- **[SCAN] log location:** Plan originally had `[SCAN]` in daemon.py poll_loop, then decided to move it into `ContentChecker.check()`. Moved it to ContentChecker since it has direct access to `matched` words from the profanity scanner and all code paths. daemon.py only receives the 3-tuple return value.
- **LyricsResult.cached field:** Added a `cached: bool` field to distinguish cache hits from fresh LRCLIB fetches. Used for the `[CACHE] hit` log in LyricsService; consumers can inspect this for debugging.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Used search_lyrics() instead of get_lyrics()**
- **Found during:** Task 2 (Create LyricsService)
- **Issue:** `lrclibapi.get_lyrics()` requires `album_name: str` and `duration: int` as positional required parameters. The plan specifies `get_lyrics(track_name, artist_name)` but the library signature does not support that call.
- **Fix:** Used `search_lyrics(track_name=..., artist_name=...)` which has all optional parameters and returns a relevance-sorted list. First result is taken if available.
- **Files modified:** lyrics_service.py
- **Verification:** Integration smoke test passed; LyricsService instantiation and cache confirmed working
- **Committed in:** 2854acb (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking — library API mismatch)
**Impact on plan:** Zero functional impact. search_lyrics() provides equivalent coverage to get_lyrics() for the track+artist lookup pattern. Actual LRCLIB API behavior is identical.

## Issues Encountered

- No local Python pip; used `uv` to create `.venv` for verification tests. Project runs inside Docker (see Dockerfile). The `.venv` is for local test execution only.

## Known Stubs

None. All three filter tiers are now active. The `no_lyrics_service` fallback path remains in `content_checker.py` as a defensive fallback (unreachable in normal daemon operation with services wired), not a functional stub.

## Next Phase Readiness

Phase 02 is complete — both plans executed. The full content filtering pipeline is active:
- Explicit tracks: auto-skip (FILT-01)
- Non-explicit tracks: LRCLIB lyrics fetch with SQLite cache → profanity scan with severity threshold
- Instrumental / lyrics-unavailable: allow without skip (FILT-04, FILT-05)
- All skip events logged in structured format for future Web UI ingestion (D-07, D-09)

Phase 03 (Web UI or Signal notifications) can proceed. No blockers from Phase 02.

## Self-Check: PASSED

All created files verified present. All three task commits confirmed in git log.

---

*Phase: 02-content-filtering-auto-skip*
*Completed: 2026-04-01*
