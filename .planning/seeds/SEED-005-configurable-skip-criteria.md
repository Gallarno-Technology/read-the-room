---
id: SEED-005
status: dormant
planted: 2026-04-02
planted_during: v1.1 Deployment / Phase 4
trigger_when: when we reevaluate what triggers a skip, or how we measure the criteria of a song
scope: small
---

# SEED-005: Use explicit tag as a signal, not a filter — configurable skip criteria per client

## Why This Matters

The content filter is one expression of a broader idea: your music library, filtered for
the room you're in right now.

Today, Spotify's `explicit` flag is a hard gate — if it's set, the song is skipped (Tier 1,
severity 3, no further evaluation). But the explicit tag is a broad brush. Some tracks are
tagged explicit for one fleeting word; others for relentless profanity. A 9-year-old and a
40-year-old have different tolerances, and a family dinner needs different rules than solo
listening.

The fix: treat `explicit` as a weighted signal in the scoring pipeline — not a binary skip
trigger. Let the client configure how much weight each signal carries, what the skip
threshold is, and which signals matter. The filter becomes a *policy*, not a hardcoded rule.

## When to Surface

**Trigger:** when we reevaluate what triggers a skip, or how we measure the criteria of a song

This seed should be presented during `/gsd:new-milestone` when the milestone scope matches
any of these conditions:
- Revisiting the skip/filter logic (thresholds, tiers, scoring)
- Adding per-listener or per-room profiles
- Adding a settings UI where skip criteria could be exposed
- Refactoring `content_checker.py` for any reason

## Scope Estimate

**Small** — `content_checker.py` is already tier-based with a `min_severity` parameter
(line 33). The explicit flag is already isolated at lines 56–64. The change is:
1. Stop returning early on `explicit` alone — fold it into the score
2. Add configurable weights (explicit_weight, min_severity, skip_threshold) — likely env
   vars or a `.env` config section first, settings UI later
3. Update tests in `tests/test_content_checker.py`

No new infrastructure needed for v1. Could ship as a single phase.

## Breadcrumbs

- `content_checker.py:56–64` — Tier 1 hard gate on explicit flag (the thing to change)
- `content_checker.py:25,33,37` — `min_severity` already a constructor param; pattern for
  adding `explicit_weight` and `skip_threshold`
- `content_checker.py:93–95` — Tier 3 severity threshold check — would become unified
  threshold across all signals
- `profanity_scanner.py:125` — returns numeric severity score — already composable
- `.env.example` — where new config knobs should be documented first

## Notes

Came up after Phase 4 (Sonos discovery hardening). The explicit-as-signal idea unlocks
the room-aware filtering concept: Living Room (kids present) = strict policy; Office (solo)
= relaxed policy. That larger idea is in SEED-002 (multi-dimensional scoring profiles) —
this seed is the prerequisite that decouples the explicit flag from the skip decision.
