# Feature Research

**Domain:** Drug reference and sexual content detection in lyric-based family filter (v1.2 milestone)
**Researched:** 2026-04-02
**Confidence:** MEDIUM (keyword approach characteristics HIGH; edge case frequencies LOW; false positive rates at this specific word list size MEDIUM)

---

## Scope

This file is narrowly scoped to the two new detection signals for v1.2:

1. **Drug reference detection** — lyrics contain references to illicit drug use
2. **Sexual content detection** — lyrics contain references to sexual acts or explicit sexual language

The existing pipeline (explicit flag, profanity scan, LRCLIB fetch, SQLite cache) is already built. These two signals slot in as additional scanners alongside `ProfanityScanner`, consuming the same `lyrics_result.lyrics` string already produced by `LyricsService`.

---

## Feature Landscape

### Table Stakes (Users Expect These)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Drug reference boolean signal on track evaluation | PROJECT.md explicitly names this as v1.2 target; parent audience of children ages 3 and 7 expects drug glorification to be filtered | LOW | Single-pass keyword scan against known drug terms and slang, analogous to ProfanityScanner pattern |
| Sexual content boolean signal on track evaluation | Same parent audience; "sexual content" is a universally recognized filter category alongside profanity | LOW | Single-pass keyword scan; separate from profanity_scanner.py which already handles some sexual terms (slut, whore, cock, pussy) as tier-2/3 profanity |
| Both signals present in skip_events.jsonl incident log | Parent needs to understand why a track was skipped; existing incident log already records reason field | LOW | Extend existing `reason` field or add named boolean fields alongside it; PROJECT.md specifies "both signals logged in incident log alongside existing flags" |
| Independent named booleans per category on evaluation result | PROJECT.md explicitly requires this for forward compatibility with per-category UI toggles | LOW | `has_drug_refs: bool` and `has_sexual_content: bool` on whatever result structure ContentChecker returns or on the skip event payload |
| Detection runs on already-fetched lyrics, no new API calls | System already fetches lyrics via LRCLIB; users and developers expect new detection not to add latency from new network calls | LOW | All new scanners consume `lyrics_result.lyrics` already in hand — this is purely in-process |
| Skip triggered on detection (when Family Safe Mode is on) | If you add detection, the obvious behavior is to skip; not skipping on a detected signal would confuse the parent | LOW | ContentChecker.check() already returns (action, reason, severity) tuple; needs to return on drug or sexual signal just as it returns on profanity |

### Differentiators (Competitive Advantage)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Matched-term logging alongside boolean signal | Parent can see *what* was detected (e.g., "blunt, weed") not just "drug reference detected" — builds trust and allows word list calibration | LOW | ProfanityScanner already does this via `matched` return value; replicate the pattern |
| Prioritized word lists that exclude ambiguous single-word terms | Most off-the-shelf drug keyword lists include "snow", "white", "ice", "blow", "herb", "grass", "speed", "high", "dope" as bare words — all extremely high false-positive risk. Curating a list that requires the word in context OR starts with unambiguous multi-word phrases ("purple drank", "xan bar") produces a much more trustworthy signal | MEDIUM | Requires editorial judgment, not library work. The research shows this is the critical differentiator between "unusable" and "reliable enough for family use" |
| Sexual content word list separate from existing profanity tier-2/3 words | Some sexual terms already covered by ProfanityScanner (cock, slut, pussy, whore) but a sexual content scanner should cover explicit act descriptions, body part combinations, and sexual slang that aren't profanity in isolation | MEDIUM | Requires carefully deduplicating against SEVERITY_MAP in profanity_scanner.py to avoid double-counting |
| `allow_on_unavailable` behavior preserved for new signals | When lyrics are unavailable (LRCLIB miss), the system already does not skip. New signals must honor the same non-skip-on-uncertainty contract. Children are ages 3 and 7; over-skipping is irritating but under-filtering on missing lyrics is already an accepted v1 tradeoff | LOW | No change to existing FILT-05 logic needed; new scanners only run when `lyrics_result.lyrics is not None` |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| NLP/ML-based semantic detection of drug themes and sexual metaphors | Promises to catch euphemisms that keyword lists miss ("I lean on you", "garden of love", "rolling in the deep") | Adds a model dependency (ONNX, spaCy, or remote API call), increases scan latency by 100-500ms per track, requires training data curation, and will still produce false positives on lyrical metaphors. PROJECT.md explicitly defers "Sentiment NLP" to v2+ as "too complex for v1" | Accept known miss rate on euphemisms; log all misses; review them manually over time to inform word list expansion |
| Severity scoring within drug / sexual categories | Intuitive — "smoking weed once" vs "glorifying heroin use" feels like it should produce different scores | PROJECT.md explicitly defers "Severity scoring within content categories" to v2+. Boolean is sufficient to drive skip/allow decisions. Severity adds implementation complexity and requires editorial judgment about relative harm | Boolean signal in v1.2; severity is a named v2+ deferred item |
| Per-category toggle UI in this milestone | Would let parent turn off drug detection but keep sexual detection | Deferred to v1.3 per PROJECT.md ("Active" backlog). The boolean fields on the result struct must be named independently *now* to make this possible later, but no toggle UI yet | Name the booleans correctly now so the toggle wires in cleanly next milestone |
| LLM API call per track for detection | Would handle euphemism, context, and multilingual content elegantly | Requires OpenAI/Anthropic API key, per-call cost, internet dependency, 200-800ms additional latency per track, and breaks the offline/Docker design ethos | Stick to in-process keyword scan; revisit LLM approach in v2+ as already documented in LYRICS_FILTERING.md section 7 |
| Exhaustive drug slang list (200+ terms) from DEA or law enforcement glossaries | Maximizes recall — catches every possible drug reference | Research shows high-recall word lists produce unacceptable false positive rates. "Weed" flags "tweed". "Snow" flags "snowfall". "Ice" flags "ice cream". "Blow" flags "blow a kiss". "High" flags "fly so high". "Speed" flags "the speed of light". "Lean" flags "lean on me". A 200-term list on music lyrics generates noise that undermines parent trust in the filter | Curate a conservative list of unambiguous high-confidence terms (~40-60 terms); explicitly document which common slang was excluded and why |
| Blocking songs with themes of alcohol | Might seem in scope alongside drugs | Alcohol references are pervasive in mainstream music at a level that would skip enormous fractions of popular catalog, including many songs the parent explicitly wants to hear. Alcohol detection would need its own toggle to be useful, and that toggle is v1.3. Not in scope for v1.2 | Leave alcohol as an out-of-scope stub note |

---

## Feature Dependencies

```
Drug reference detection (new)
    └──requires──> LyricsService (already exists)
    └──requires──> ContentChecker pipeline hook (already exists, needs extension)
    └──produces──> has_drug_refs: bool on evaluation result

Sexual content detection (new)
    └──requires──> LyricsService (already exists)
    └──requires──> ContentChecker pipeline hook (already exists, needs extension)
    └──produces──> has_sexual_content: bool on evaluation result

Incident log extension (new)
    └──requires──> has_drug_refs signal
    └──requires──> has_sexual_content signal
    └──enhances──> skip_events.jsonl (already exists)

Per-category toggle UI (future v1.3)
    └──requires──> independent named booleans on result (v1.2 must deliver this)
    └──requires──> dashboard UI work (separate milestone)
```

### Dependency Notes

- **Drug/sexual detection requires LyricsService:** Scanners receive `lyrics_result.lyrics` already in hand. No new service dependency.
- **ContentChecker must be extended, not replaced:** The existing three-tier pipeline (explicit → lyrics → profanity) needs to grow a tier 3b/3c for new signals. The `check()` return signature likely needs revision — either a new named tuple, a dataclass, or additional fields. This is the central implementation question for the milestone.
- **Independent named booleans are a hard dependency for the v1.3 toggle UI:** If both signals are collapsed into a single `reason="drug_or_sexual"` string, the toggle UI becomes impossible to wire without another refactor. v1.2 must deliver named fields.
- **Profanity scanner deduplication:** The existing SEVERITY_MAP in profanity_scanner.py covers several terms that also appear in sexual content word lists (cock, pussy, slut, whore, tits, dick). The new sexual content scanner should be aware of this to avoid the appearance of double-flagging the same word, though in practice the result is the same (track is skipped either way).

---

## MVP Definition

### Launch With (v1.2)

- [x] `DrugScanner` class: keyword scan returning `(detected: bool, matched: list[str])` — same interface pattern as `ProfanityScanner.scan()`
- [x] `SexualContentScanner` class: keyword scan returning `(detected: bool, matched: list[str])`
- [x] ContentChecker extended: new signals evaluated after profanity check; skip on any signal when FSM active
- [x] Result structure: named boolean fields `has_drug_refs` and `has_sexual_content` on evaluation result (not collapsed into reason string)
- [x] Incident log: both new boolean signals written to skip_events.jsonl entries
- [x] Drug word list: curated conservative ~40-60 term list, explicitly excluding ambiguous bare words; documented rationale for exclusions
- [x] Sexual content word list: explicit act terms, genitalia slang not already in profanity tier, sexual euphemisms with low false-positive risk

### Add After Validation (v1.3)

- [ ] Per-category toggle UI in web dashboard — trigger: word lists have been running for 2+ weeks and false positive rate is understood
- [ ] Song-level allowlist / denylist override — trigger: parent identifies a specific false positive they want to override without editing word lists

### Future Consideration (v2+)

- [ ] Severity scoring within drug / sexual categories — deferred per PROJECT.md
- [ ] Semantic/LLM-based euphemism detection — deferred per PROJECT.md "Sentiment NLP"
- [ ] Alcohol detection category — needs its own toggle to avoid catalog decimation
- [ ] Per-child profile filtering tiers — deferred per PROJECT.md

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Drug scanner (boolean) | HIGH | LOW | P1 |
| Sexual content scanner (boolean) | HIGH | LOW | P1 |
| Named boolean fields on result | HIGH (future-proofs toggle UI) | LOW | P1 |
| Incident log extension | MEDIUM (visibility) | LOW | P1 |
| Conservative, curated word lists | HIGH (trust in filter) | MEDIUM (editorial judgment) | P1 |
| Severity scoring in v1.2 | LOW (deferred) | MEDIUM | P3 |
| LLM euphemism detection in v1.2 | LOW (scope creep) | HIGH | P3 |
| Alcohol detection in v1.2 | LOW (catalog noise) | LOW | P3 |

**Priority key:**
- P1: Must have for launch
- P2: Should have, add when possible
- P3: Nice to have, future consideration

---

## Edge Cases and Tradeoffs

### Drug Reference Detection — Edge Cases

**High false-positive risk terms to exclude or handle with care:**

| Term | False Positive Scenario | Recommendation |
|------|------------------------|----------------|
| `high` | "fly so high", "higher ground", "I feel high on life" | Exclude bare form; only include in multi-word phrase like "getting high" — but even that triggers on "getting high hopes". Avoid entirely unless multi-word context guaranteed |
| `lean` | "lean on me", "lean into it", "lean and mean" | Exclude bare form. "Purple lean", "sipping lean", "double cup lean" are higher-confidence phrases |
| `white` | "white picket fence", "white wedding", "snow white" | Exclude bare form completely |
| `snow` | "let it snow", "snow angel" | Exclude bare form |
| `ice` | "ice ice baby" (this one is actually fine to flag), "ice cream", "cold as ice" | High false positive risk; borderline |
| `blow` | "blow a kiss", "blow the candles out" | Exclude bare form; include "blow lines", "blow coke" |
| `herb` | "herb garden", plant names in songs | Exclude bare form; include "smoking herb" |
| `speed` | "speed of light", "up to speed" | Exclude bare form |
| `grass` | "the grass is greener", "sitting on the grass" | Exclude bare form |
| `dope` | "that's dope" (slang for cool), "dope beat" | Extremely polysemous in modern music; exclude or accept high false positive rate |
| `420` | Numerals in lyrics are rare; this is fairly unambiguous | Include |

**Lower false-positive risk terms worth including:**

Cannabis: `weed`, `marijuana`, `cannabis`, `blunt`, `joint`, `spliff`, `bong`, `kush`, `indica`, `sativa`, `ganja`, `reefer`, `mary jane`, `chronic`, `420`
Cocaine: `cocaine`, `coke`, `yayo`, `nose candy`, `snorting`, `lines of`
Opioids: `heroin`, `smack`, `opioid`, `fentanyl`, `oxy`, `oxycontin`, `percocet`, `lean` (in phrase context), `codeine syrup`, `purple drank`, `sizzurp`
Stimulants: `methamphetamine`, `crystal meth`, `molly`, `ecstasy`, `mdma`, `adderall` (as recreational), `xan`, `xanax` (recreational context)
Generic: `rolling on drugs`, `on drugs`, `getting lit` (borderline — very high false positive)

**Research finding (MEDIUM confidence):** Academic literature on drug-reference detection in lyrics consistently shows that bare single-word terms produce low precision (many false positives). Multi-word phrases and phrase-level context dramatically improve precision at the cost of recall. For a family filter, false positives erode trust faster than false negatives — err toward precision.

### Sexual Content Detection — Edge Cases

**Interaction with existing profanity tier:**

The SEVERITY_MAP in profanity_scanner.py already covers: `dick`, `cock`, `cocks`, `whore`, `slut`, `slutty`, `tit`, `tits`, `pussy`, `wank`, `wanker`, `twat`, `asshole`. These are caught by profanity scan before the sexual content scan would even run. The new sexual content scanner should focus on what the profanity tier misses:

**Terms to include in sexual content scanner (not in profanity tier):**

Explicit acts: `fucking` (already in profanity tier-3 as the F-word), `sex`, `having sex`, `sexual`, `intercourse`, `orgasm`, `ejaculate`, `cumming`, `cum shot`, `fingering`, `going down on`, `blow job`, `blowjob`, `handjob`, `rimjob`, `anal`, `penetrat`
Body parts (explicit slang not in profanity tier): `vagina`, `penis`, `erection`, `boobs`, `nipples` (borderline), `naked body`, `nude`, `strip` (very high false positive — strip mall, stripped down to basics)
Sexual acts described: `making love` (borderline — deliberately romantic, not explicit), `getting laid`, `one night stand` (borderline), `bedroom` (very high false positive)

**Recommended approach:** Focus on explicit act terms (blow job, going down on, orgasm, cumming) rather than body part vocabulary or euphemistic phrases. Explicit act terms have far lower false positive rates in general music lyrics than body part terms. "Boobs" and "nipples" appear in comedy songs, "naked" appears in "Naked Eye" and similar. Explicit act verb phrases are much harder to use accidentally.

**High false-positive risk to avoid:**

| Term | False Positive Scenario | Recommendation |
|------|------------------------|----------------|
| `strip` | Strip club, stripped down, strip mall, strip mine | Exclude bare form |
| `naked` | "Naked Eye", "naked truth", "naked ambition" | Exclude bare form |
| `bed` | Beds are mentioned constantly in non-sexual contexts | Exclude |
| `sexy` | "I'm feeling sexy and free" — parent may want this filtered but it is extremely broad | Borderline; discuss with user |
| `body` | Ubiquitous in non-sexual contexts | Exclude bare form |
| `kiss` | Not sexual content by any definition | Exclude |
| `touch` | Not sexual content | Exclude |
| `love` | Not sexual content | Exclude |
| `making love` | Euphemism, but extremely common in mainstream pop that the parent likely wants to allow | Low-confidence; borderline; lean toward excluding |

### Boolean vs. Severity — Decision

**The project spec says: boolean signal.** This is the right call for v1.2.

Tradeoff analysis:
- **Boolean pros:** Simple to reason about, matches the existing explicit-flag contract, drives a clean skip/allow decision, lower implementation complexity, forward-compatible (severity can be added later by adding a field)
- **Boolean cons:** Cannot distinguish "one oblique drug reference" from "every lyric line glorifies heroin". But this nuance is a v2 problem.
- **Severity cons for v1.2:** Requires editorial decisions about how many matches of what weight constitute a "moderate" vs "high" drug reference. The profanity tier's severity approach works because there's an established cultural hierarchy of profanity severity; no equivalent consensus exists for drug content severity.

**Decision: boolean in v1.2, severity deferred to v2+ per PROJECT.md.**

### "Detected and Declined" in Practice

When the drug or sexual content scanner fires:

1. `ContentChecker.check()` returns `(action="skip", reason="drug_refs", ...)` or `(action="skip", reason="sexual_content", ...)`
2. The daemon skips the track (SoCo UPnP or Spotify API fallback, same as profanity skip)
3. `skip_events.jsonl` receives an entry with `reason: "drug_refs"` (or `"sexual_content"`), `matched_terms: ["blunt", "weed"]`, and the new boolean fields `has_drug_refs: true`, `has_sexual_content: false`
4. The web dashboard skip history feed shows the skip with the new reason label
5. The 5-consecutive-skip pause logic counts drug/sexual skips the same as profanity skips

This is behaviorally identical to a profanity skip from the daemon's perspective. The only user-visible difference is the reason label in the dashboard.

---

## Competitor Feature Analysis

| Feature | Spotify (built-in) | Apple Music | Our Approach |
|---------|-------------------|-------------|--------------|
| Explicit flag | Distributor-set boolean; under-flags heavily | RIAA rating; similar limitations | Consumed as Tier 1 check; already built |
| Drug reference detection | Not provided | Not provided | Custom keyword scanner against fetched lyrics |
| Sexual content detection | Not provided (beyond explicit flag) | Not provided (beyond RIAA rating) | Custom keyword scanner against fetched lyrics |
| Euphemism handling | None | None | Accepted miss; will log; expand list over time |
| Per-category toggle | No (just "explicit on/off") | No (just "explicit on/off") | Boolean fields ready; toggle UI in v1.3 |
| Override by song | No | No | Deferred to v1.3 |

Observation: Neither Spotify nor Apple Music provides category-level detection beyond the blunt-instrument explicit flag. This project's word-list approach, even with its known limitations, provides meaningfully more signal than what streaming platforms expose natively.

---

## Sources

- [An Analysis of the Prevalence and Trends in Drug-Related Lyrics (JMIR 2024)](https://formative.jmir.org/2024/1/e49567) — confirms word-based approaches have high precision / low recall; fuzzy matching improves recall
- [Covering Cracks in Content Moderation: Delexicalized Distant Supervision for Illicit Drug Jargon Detection (arXiv 2025)](https://arxiv.org/html/2503.14926v1) — context-aware approaches beat bare keyword lists; JEDIS framework
- [Self-Supervised Euphemism Detection (arXiv 2021)](https://arxiv.org/pdf/2103.16808) — euphemisms specifically escape keyword filters; semantic approaches required for full coverage
- [Fine-Tuning LLMs for Explicit Content in Spanish Lyrics (arXiv 2026)](https://arxiv.org/html/2602.05485) — dictionary-based filtering achieves 61% F1-score; ML achieves 87%+; euphemism problem is severe in genre-specific music
- [Explicit Content Detection in Music Lyrics (IEEE 2018)](https://ieeexplore.ieee.org/document/8367165/) — ML baseline; word-based achieves 78% on Korean lyrics
- [Keyword lists and filtering guide (Sightengine 2026)](https://sightengine.com/keyword-lists-for-text-moderation-the-guide) — practical keyword list maintenance tradeoffs
- [DEA Drug Slang Reference (2018)](https://www.dea.gov/sites/default/files/2018-07/DIR-022-18.pdf) — comprehensive law enforcement slang reference (used to identify high-false-positive terms to exclude)
- [Drug Slang Detection via NLP (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC5838358/) — word embeddings for discovering novel slang; confirms list maintenance burden
- Existing project: `profanity_scanner.py` SEVERITY_MAP (cross-reference to avoid duplicates in sexual content scanner)
- Existing project: `content_checker.py` pipeline structure (integration point for new scanners)

---

*Feature research for: drug reference detection and sexual content detection in lyric-based family filter*
*Researched: 2026-04-02*
