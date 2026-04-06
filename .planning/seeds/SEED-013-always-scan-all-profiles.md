---
id: SEED-013
status: dormant
planted: 2026-04-06
planted_during: v1.5 / 18-profile-info-icon
trigger_when: when we focus on optimization, caching, or scan performance — or when richer per-track data is needed for UI features
scope: medium
---

# SEED-013: Always run scanners for every profile, regardless of which one is active

## Why This Matters

Today's bug (`above_the_covers` bypassing the lyrics pipeline because its profanity scanner was
`None`) surfaced a deeper opportunity: instead of building `ContentChecker` with only the scanners
the active profile needs, always run all scanners and store per-profile severity scores per track.

This enables richer UI: "this track would be blocked in Kids Present" labels, profile comparison
views, and accurate skip-count projections when switching profiles. It also eliminates the
conditional scanner construction that caused today's bug — one code path, all scanners always run.

## When to Surface

**Trigger:** Performance / optimization milestone, or any milestone adding richer track data, per-profile history, or UI that surfaces how tracks score across profiles.

This seed should be presented during `/gsd:new-milestone` when the milestone scope matches any of:
- Performance / caching / scan latency work (scanning all profiles in parallel is cheap with cached lyrics)
- "Profile insights" or "filter transparency" UI features
- Per-track history, reporting, or audit log work
- Any refactor of `ContentChecker` or `_build_content_checker`

## Scope Estimate

**Medium** — a phase or two. Core change (always build all scanners, return per-profile scores) is
small. The larger effort is deciding where to store multi-profile scores (in-memory cache vs. DB),
how the UI surfaces them, and whether skip history gains a "would have been blocked under X" column.

## Breadcrumbs

- `daemon.py:51` — `PROFILE_MAP` defines which scanners each profile enables; this is the gating
  logic that would be replaced by "always run all"
- `daemon.py:242` — `_build_content_checker()` selects scanners per profile; this is where the
  conditional construction lives
- `content_checker.py` — `ContentChecker` class; `evaluate()` currently short-circuits based on
  which scanners are non-`None`
- `content_checker.py:35` — `TrackEvalResult` dataclass; would need per-profile score fields or a
  new `AllProfileResult` wrapper
- `tests/test_content_checker.py` — 16 tests covering current per-profile behavior; would need
  updating when scanner construction changes
- `.planning/debug/lyrics-pipeline-not-active.md` — the bug that motivated this seed

## Notes

The lyrics fetch is the expensive part (network / DB). Scanner CPU cost is negligible. Running all
four profile scanners against already-fetched lyrics is essentially free — the incremental cost of
"always scan all" is close to zero once lyrics are in hand.
