---
id: SEED-003
status: dormant
planted: 2026-04-01
planted_during: v1.0 / Phase 2 complete
trigger_when: after multi-dimensional scoring (SEED-002) ships
scope: large
---

# SEED-003: ML/LLM content analysis as Tier 4 fallback when keyword filters are insufficient

## Why This Matters

The current three-tier pipeline (`explicit flag → LRCLIB lyrics → profanity word scan`)
has a fundamental ceiling: word lists match tokens, not meaning. Keyword filters cannot:

- Distinguish context: "I took a shot" (drinking) vs. "fired a shot" (violence)
- Understand metaphor, slang evolution, or regional idioms
- Score content that uses no flagged words but has clearly explicit themes

There is also a silent gap: when LRCLIB has no lyrics (`reason: lyrics_unavailable`),
the track currently defaults to **allow** (`content_checker.py:91`). This is a
deliberate conservative choice, but it means any track with missing lyrics bypasses
filtering entirely.

An LLM/ML Tier 4 closes both gaps:
1. **Context-aware scoring** for tracks that pass word-list checks but are likely
   inappropriate (false negatives from Tier 3)
2. **Ambiguous track resolution** — replace the "lyrics_unavailable → allow" shortcut
   with an LLM inference call when lyrics are missing

**Caching is critical**: LLM API calls are expensive (~$0.01–0.10/track at GPT-4 rates).
Without SEED-001 (analysis cache), every play of every track would incur an API cost.
The cache converts a per-play cost into a one-time cost per unique track.

## When to Surface

**Trigger:** After SEED-002 (multi-dimensional scoring) ships. LLM analysis is most
valuable as Tier 4 when the scoring model already has distinct categories
(language, violence, drugs, sex) — an LLM can return per-category scores in a single
call, feeding directly into the profile threshold system.

This seed should be presented during `/gsd:new-milestone` when the milestone
scope matches any of these conditions:
- SEED-002 (per-category scoring) is complete and in production
- Users report false negatives that word-list tuning cannot fix
- Milestone explicitly mentions AI, ML, or semantic content analysis
- The "lyrics_unavailable → allow" default has caused household complaints

## Scope Estimate

**Large** — A full milestone. This is not just an API call — it involves:

1. **Model selection**: OpenAI GPT-4o-mini, Claude Haiku, or a self-hosted
   open-weights model (Llama/Mistral). Cost, latency, and privacy tradeoffs differ.
2. **Prompt design**: Structured output prompt that returns per-category severity
   scores matching the SEED-002 schema. Must be deterministic enough for caching.
3. **Cache integration** (depends on SEED-001): LLM result stored in `analysis_cache`
   keyed by track ID. Without a cache this is not viable at scale.
4. **Fallback chain**: Tier 4 only fires when Tiers 1–3 are inconclusive or when
   `lyrics_unavailable`. Should not add latency to clearly clean or clearly explicit tracks.
5. **Cost controls**: Budget cap per day/month; graceful degradation to current
   "allow" behavior if budget exceeded or API unavailable.
6. **Self-hosted option**: For privacy-conscious users, a local model (Ollama +
   Llama 3) should be a drop-in alternative — same prompt interface, lower quality
   but zero API cost and no data leaving the home server.
7. **Confidence threshold**: LLM returns a confidence score; low-confidence results
   fall back to current behavior rather than acting on an uncertain inference.

## Breadcrumbs

Relevant code in the current codebase:

- `content_checker.py:4–7` — Three-tier pipeline comment; Tier 4 slots in after Tier 3
- `content_checker.py:84–91` — `lyrics_unavailable → allow` shortcut; primary target for LLM replacement
- `content_checker.py:93` — Tier 3 entry point; Tier 4 fires when `severity < min_severity` but context suggests otherwise
- `profanity_scanner.py:125` — `scan()` return signature `(int, list[str])`; LLM scorer should return compatible shape, extended with per-category scores (see SEED-002)
- `lyrics_service.py:46` — `LyricsResult` dataclass; an `LLMAnalysisResult` dataclass should follow the same pattern
- `.planning/seeds/SEED-001-persist-song-analysis-cache.md` — analysis cache (prerequisite)
- `.planning/seeds/SEED-002-multi-dimensional-content-scoring-profiles.md` — per-category scoring model (prerequisite / companion)

## Notes

- **Dependency order**: SEED-001 (cache) should ship before or alongside this seed.
  SEED-002 (multi-dimensional scoring) should ship before this seed so LLM output
  maps cleanly to the profile system. Recommended order: SEED-001 → SEED-002 → SEED-003.
- **Privacy consideration**: Lyrics + track metadata are sent to a third-party API.
  The self-hosted model option (Ollama) is the privacy-preserving path and should be
  the default for home-server deployments.
- **Latency budget**: Tier 4 must complete within ~2–3 seconds to avoid audible
  content playing before a skip fires. Fast models (GPT-4o-mini, Claude Haiku,
  Llama 3 8B) are preferable over large/slow models.
- The Signal notification system (Phase 3) should be updated to report `llm_analysis`
  as the skip reason when Tier 4 fires, so users understand why a track was flagged.
