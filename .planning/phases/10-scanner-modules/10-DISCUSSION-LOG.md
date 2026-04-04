# Phase 10: Scanner Modules - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-03
**Phase:** 10-scanner-modules
**Areas discussed:** Drug keyword philosophy, Sexual keyword scope

---

## Drug keyword philosophy

| Option | Description | Selected |
|--------|-------------|----------|
| Conservative: unambiguous only | Clinical terms only — cocaine, heroin, meth, etc. No slang like "high", "weed", "pot" | ✓ |
| Slang included, phrase-guarded | Slang with context words — but phrase matching is deferred to v2+ | |
| Slang included, test-validated | Add weed, pot, joint, high, dope — accept some slip-through | |

**User's choice:** Conservative — unambiguous terms only

**Specific additions requested:** crystal meth, sizzurp, purple drank, coke (beyond pure clinical names)

**Notes:** Ages 3 and 7 — err on caution. Ambiguous slang ("high", "weed", "pot", "joint") excluded due to false positive risk on innocent songs.

---

## Sexual keyword scope

| Option | Description | Selected |
|--------|-------------|----------|
| Explicit acts only | Sex act verbs only | |
| Acts + anatomy not in profanity map | Anatomical terms alongside act words | ✓ |
| Acts + innuendo / euphemisms | Wider net including euphemisms — higher false positive risk | |

**User's choice:** Explicit acts + anatomical terms — "obvious red flags" only

**Notes:**
- User confirmed fingering, rimming are NOT false positive risks in lyrics — include them
- "naked", "nude" explicitly excluded — too many innocent uses in mainstream lyrics
- LLM layer planned for future milestone to handle nuance and hidden meanings
- Profanity map already claims: dick, cock, pussy, tits, slut, whore, fuck (and variants), cunt — sexual scanner must not overlap (SEXL-03)

---

## Claude's Discretion

- File layout: two separate files (drug_scanner.py, sexual_content_scanner.py) — not discussed but follows profanity_scanner.py pattern
- Exact inflected forms per term
- Whether to pre-compile regex patterns
- Unit test structure

## Deferred Ideas

- Phrase matching for drug/sexual detection — REQUIREMENTS.md out-of-scope, v2+
- Ambiguous drug slang (weed, pot, high, joint, dope) — excluded now; LLM layer will handle
- Alcohol/tobacco signal — deferred per requirements
- LLM nuance layer — future milestone
