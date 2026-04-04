---
phase: quick
plan: 260404-avv
type: execute
wave: 1
depends_on: []
files_modified:
  - content_checker.py
  - tests/test_content_checker.py
autonomous: true
requirements: []

must_haves:
  truths:
    - "A track with no lyrics (but not instrumental) is scanned against its title text"
    - "A title that matches a drug/sexual/profanity term causes a skip even without lyrics"
    - "A clean title still returns action=allow with reason=lyrics_unavailable"
    - "reason stays 'lyrics_unavailable' when the title scan also comes back clean"
    - "reason becomes 'drug_reference' / 'sexual_content' / 'profanity' when title triggers a scanner"
  artifacts:
    - path: "content_checker.py"
      provides: "Title fallback scan logic in the lyrics_unavailable branch"
    - path: "tests/test_content_checker.py"
      provides: "Tests covering title-scan behaviour on no-lyrics tracks"
  key_links:
    - from: "content_checker.py lyrics_unavailable branch"
      to: "profanity_scanner / drug_scanner / sexual_content_scanner"
      via: "scanner.scan(track_name) calls"
      pattern: "scan\\(track_name\\)"
---

<objective>
When LRCLIB returns no lyrics for a non-instrumental track, the pipeline currently
returns `reason="lyrics_unavailable"` and allows the track unconditionally. This
misses obvious cases where the track *title itself* contains a flagged term (e.g.
a song literally called "Cocaine"). Fix: run all enabled scanners against the
track title (and artist name concatenated) before falling back to allow.

Purpose: Catch flagged content in titles when lyrics are absent.
Output: Updated content_checker.py + new tests.
</objective>

<execution_context>
@/home/cgallarno/Development/spotify-sentiment/.claude/get-shit-done/workflows/execute-plan.md
@/home/cgallarno/Development/spotify-sentiment/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@/home/cgallarno/Development/spotify-sentiment/content_checker.py
@/home/cgallarno/Development/spotify-sentiment/tests/test_content_checker.py
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add title-fallback scan in the lyrics_unavailable branch</name>
  <files>content_checker.py, tests/test_content_checker.py</files>
  <behavior>
    - test_no_lyrics_clean_title_allows: lyrics=None, title="Sunshine", all scanners return clean → action=allow, reason=lyrics_unavailable
    - test_no_lyrics_drug_title_skips: lyrics=None, title="Cocaine", drug_scanner.scan returns (True, ["cocaine"]) → action=skip, reason=drug_reference, drug_reference=True
    - test_no_lyrics_sexual_title_skips: lyrics=None, title="Sex", sexual_scanner returns (True, ["sex"]) → action=skip, reason=sexual_content, sexual_content=True
    - test_no_lyrics_profanity_title_skips: lyrics=None, title="Damn It", profanity_scanner returns (3, ["damn"]) → action=skip, reason=profanity, profanity=True
    - test_no_lyrics_no_scanners_allows: lyrics=None, title="Cocaine", but no scanners wired → action=allow, reason=lyrics_unavailable (scanners are None, fallback unchanged)
    - test_no_lyrics_scan_text_is_title_plus_artist: verify that the text passed to scanner.scan() contains both track_name and artist_name concatenated (use assert_called_once_with or call_args inspection)
  </behavior>
  <action>
    In content_checker.py, locate the `lyrics_result.lyrics is None` guard inside the
    `if self.lyrics_service is not None and self.profanity_scanner is not None` block
    (currently lines 115-121). Replace the immediate `return` with a title-fallback
    scan before returning.

    Implementation detail:
    1. Build a scan_text string: `f"{track_name} {artist_name}"` — simple concat,
       no normalization needed.
    2. Run all three enabled scanners (profanity, drug, sexual) against scan_text
       using the exact same no-short-circuit pattern already used for lyrics (lines
       124-132 in content_checker.py). All three always run.
    3. Apply the same priority decision (profanity > drug > sexual). If any fires,
       return TrackEvalResult with the appropriate action/reason/severity/booleans.
    4. If nothing fires, return TrackEvalResult(action="allow",
       reason="lyrics_unavailable", severity=0) — same as before.
    5. Add a log.debug line for the title-scan path:
       `[SCAN] track=%r artist=%r title_fallback=True severity=%d action=%s`

    Write the failing tests FIRST (RED), then implement (GREEN).
    Do not change the instrumental branch or any other branch.
  </action>
  <verify>
    <automated>cd /home/cgallarno/Development/spotify-sentiment && python -m pytest tests/test_content_checker.py -x -q 2>&1 | tail -20</automated>
  </verify>
  <done>
    All existing tests still pass. Six new tests all pass. The lyrics_unavailable
    branch scans the title+artist string before allowing when scanners are wired.
  </done>
</task>

</tasks>

<verification>
Run the full test suite to confirm no regressions:

```
cd /home/cgallarno/Development/spotify-sentiment && python -m pytest tests/ -x -q
```

All tests pass.
</verification>

<success_criteria>
- `pytest tests/test_content_checker.py` passes with at least 6 new test cases
- `pytest tests/` (full suite) passes with zero failures
- `content_checker.py` title-fallback branch follows existing no-short-circuit pattern
- `reason="lyrics_unavailable"` is preserved when the title scan is clean
</success_criteria>

<output>
After completion, create `.planning/quick/260404-avv-when-a-song-has-no-lyrics-evaluate-again/260404-avv-SUMMARY.md`
</output>
