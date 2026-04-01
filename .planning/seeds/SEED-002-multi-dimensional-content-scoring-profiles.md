---
id: SEED-002
status: dormant
planted: 2026-04-01
planted_during: v1.0 / Phase 2 complete
trigger_when: next major version (v2.0+)
scope: medium
---

# SEED-002: Multi-dimensional content scoring with per-user listening profiles

## Why This Matters

The current `ProfanityScanner` collapses all content concerns into a single
severity integer (0–3). This is too blunt: a parent may be fine with mild
language for a teenager but want to block all drug references for a younger
child. A single on/off "Family Safe Mode" cannot serve different household
members with different thresholds.

The fix is to replace the flat severity score with a **multi-dimensional score
vector** — one score per content category — and let each listener profile define
its own thresholds per category.

Example categories:
- `language` — profanity and slurs (currently the only dimension)
- `violence` — references to weapons, assault, murder, gore
- `drugs` — alcohol, cannabis, hard drugs
- `sex` — sexual content, innuendo, explicit acts
- `hate` — discriminatory language targeting protected groups

With per-category scores, profiles become expressive:
- **Kids**: block anything > 0 in any category
- **Teens**: allow `language=1`, block `violence≥2`, block `drugs≥1`, block `sex≥2`
- **Adult (language-sensitive)**: allow violence/drugs/sex but block `language≥2`

## When to Surface

**Trigger:** Start of v2.0 or any milestone that introduces multi-user support,
per-device profiles, or a configuration/settings system.

This seed should be presented during `/gsd:new-milestone` when the milestone
scope matches any of these conditions:
- Milestone introduces user profiles, accounts, or per-device settings
- Milestone adds a configuration UI or settings file per listener
- Milestone mentions "granular filtering", "custom thresholds", or "per-user"
- v1.0 is complete and a v2.0 planning session begins

## Scope Estimate

**Medium** — A phase or two. Core tasks:
1. **Scoring model**: Replace `SEVERITY_MAP: dict[str, int]` with
   `CATEGORY_MAP: dict[str, dict[str, int]]` — each word maps to
   `{category: severity}`. A word can appear in multiple categories.
2. **Scanner output**: `ProfanityScanner.scan()` returns
   `dict[str, int]` (category → max severity) instead of a flat int.
3. **Profile schema**: TOML/JSON config per profile with per-category thresholds.
   Stored alongside daemon config or in SQLite.
4. **ContentChecker update**: Accepts active profile, compares score vector
   against profile thresholds to produce `(action, reason)`.
5. **Signal UX**: Skip notifications include the triggering category
   (e.g., "Skipped: drug references (severity 2)") — more informative than
   the current generic reason string.

Word list expansion (violence, drugs, sex, hate categories) is the bulk of the
content work but is independent of the architecture change.

## Breadcrumbs

Relevant code in the current codebase:

- `profanity_scanner.py:23` — `SEVERITY_MAP: dict[str, int]` — the flat map to replace with a category-keyed structure
- `profanity_scanner.py:125` — `ProfanityScanner.scan()` — returns `(max_severity, matched_words)`; signature will change to return per-category scores
- `profanity_scanner.py:9–11` — Current three severity tiers (mild/moderate/severe) — these become per-category severity levels
- `content_checker.py:33` — `min_severity` constructor param — becomes a profile object with per-category thresholds
- `content_checker.py:39` — `ContentChecker.check()` — action decision logic will use profile thresholds
- `content_checker.py:94` — `profanity_scanner.scan()` call site — receives new multi-dimensional result

## Notes

- SEED-001 (persist song analysis) interacts with this seed: if analysis results
  are cached, the cache schema must store the full score vector, not just the
  flat action/reason. Plan SEED-001 after this scoring model is stable, or design
  the cache schema to be category-aware from the start.
- The `better_profanity` fallback (Pass 2 in `profanity_scanner.py:167`) only
  catches obfuscated language-category words. It would need category-specific
  fallback libraries or heuristics for violence/drugs/sex — or accept that
  leet-speak detection only applies to the language category.
- Consider using an LLM-based scorer (GPT/Claude) as an optional Tier 4 for
  ambiguous tracks, replacing the current "lyrics unavailable → allow" fallback.
