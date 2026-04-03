# Feature Research: Drug Reference and Sexual Content Detection (v1.3)

**Domain:** Keyword-based content signal detection for family-safe music filtering
**Researched:** 2026-04-03
**Confidence:** HIGH — based on direct code inspection of v1.2 codebase, ESRB/RIAA categorization standards, and analysis of prior FEATURES.md patterns. External research used to validate keyword taxonomy and confirm boolean-vs-severity decision.

---

## Scope

This file covers the two new content signals for v1.3:

1. **Drug reference detection** — keyword scan of LRCLIB lyrics; boolean signal with matched terms list
2. **Sexual content detection** — keyword scan of LRCLIB lyrics; boolean signal with matched terms list
3. **TrackEvalResult dataclass** — refactor of ContentChecker.check() from positional 3-tuple to named dataclass; enables all future signal additions without positional coupling

The existing explicit flag, profanity scanner (severity 1-3), LRCLIB cache, skip logic, and dashboard infrastructure are unchanged.

---

## Categorization: How These Signals Differ From Profanity

Industry content advisory systems (ESRB, RIAA, IMDB Parents Guide) consistently treat drug reference and sexual content as **discrete categories, not severity tiers**, at the detection layer:

- ESRB uses "Drug Reference" (boolean presence) vs "Use of Drugs" (active depiction) as separate descriptors — not a severity scale
- IMDB's "Alcohol/Drugs/Smoking" and "Sex and Nudity" categories can carry Mild/Moderate/Severe intensity votes, but the *detection* question is always binary: is this category present?
- RIAA's 2002 specific-area labels used three named categories: "strong language", "violent content", "sexual content" — all boolean presence signals, not tiered

**Implication for this project:** Profanity earns severity tiers because parents of 3- and 7-year-olds meaningfully distinguish "damn" from "motherfucker." Drug references and sexual content have no analogous gradient that is actionable at v1.3. A song referencing "weed" in one line is a skip just as surely as one that glorifies heroin. The detection answer is yes/no; the policy answer is skip/allow. Severity tiers for these signals belong in v2+ (per PROJECT.md "Deferred" section).

---

## Feature Landscape

### Table Stakes (Users Expect These)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Drug reference detection (boolean + matched terms) | Core v1.3 requirement; parents of young children expect "drugs" to be a filter category, just as profanity is | LOW | Word-by-word scan against a static DRUG_TERMS set; same pattern as SEVERITY_MAP in profanity_scanner.py |
| Sexual content detection (boolean + matched terms) | Core v1.3 requirement; sexual content is the other primary parental concern alongside language | LOW | Word-by-word scan against a static SEXUAL_TERMS set; word boundary matching required |
| Both signals trigger skip when FSM is active | Without skip enforcement, detection is reporting-only, which violates the core value | LOW | ContentChecker.check() already has skip/allow dispatch; drug and sexual signals feed into it |
| Both signals logged in skip_events.jsonl | Incident log is the parent's audit trail; a skip with no logged reason is confusing | LOW | _append_skip_event() already handles arbitrary reason strings; new reasons: "drug_reference", "sexual_content" |
| Dashboard badges for drug-reference and sexual-content skip reasons | v1.2 established the badge-group pattern specifically for extensibility; missing badges break the skip feed UX | LOW | Add two badge variants to index.html matching existing CSS badge pattern |
| TrackEvalResult named dataclass replacing positional 3-tuple | Required by PROJECT.md v1.3; positional tuple cannot carry two new boolean fields without breaking every caller | MEDIUM | Define `@dataclass class TrackEvalResult` with fields: action, reason, severity, drug_ref, sexual_content, matched_drug_terms, matched_sexual_terms |

### Differentiators (Competitive Advantage)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Matched terms included in skip log | Parent sees "Skipped: drug reference (blunt, molly)" rather than just "drug reference" — builds trust in the filter by showing what triggered it | LOW | TrackEvalResult already carries matched_drug_terms list; serialize to skip_events.jsonl entry |
| Drug and sexual signals as independent named booleans on TrackEvalResult | Enables per-category toggle UI in a future milestone without changing the detection logic or log schema | LOW | Named fields on dataclass cost nothing extra; PROJECT.md "Deferred" section names per-category toggles as v2+ |
| Word-boundary enforcement for sexual terms | Prevents Scunthorpe-class false positives on innocent substrings (e.g., "bass", "class", "expression") | LOW | Use `re.search(r'\b' + re.escape(term) + r'\b', normalized)` or split-word comparison; profanity_scanner.py already uses word-split approach which implicitly handles boundaries |

### Anti-Features (Commonly Requested, Often Problematic)

| Anti-Feature | Why Requested | Why Problematic | Alternative |
|--------------|---------------|-----------------|-------------|
| Severity tiers for drug references (mild=cannabis vs severe=heroin) | Seems analogous to profanity severity tiers; parents might want different policies for alcohol references vs hard drugs | For ages 3 and 7, no drug reference is appropriate; the policy distinction has no actionable effect at this age range; adds maintenance burden (categorizing every drug term into tiers) with zero skip-behavior change | Boolean detection now; add sub-category toggles (cannabis / alcohol / hard drugs) in v2+ per PROJECT.md deferred list |
| Severity tiers for sexual content (innuendo vs explicit) | Profanity has tiers; users expect consistency | "I want a little sex" is a skip for a 3-year-old; "innuendo" vs "explicit" distinction requires context, not just keywords; keyword-only approach cannot reliably distinguish intent without NLP; adds false complexity | Boolean now; add NLP-based severity in v2+ if needed |
| LLM-based contextual detection to reduce false positives | LLMs would understand "high" as altitude vs drug reference | Requires external API call per track (latency, cost, offline risk); PROJECT.md explicitly places NLP/LLM in "Out of Scope" and "Deferred" for layered-approach reason; false positives are acceptable at this age range (err on side of caution) | Accept keyword false positives; maintain the DRUG_TERMS and SEXUAL_TERMS lists; parent can override by turning FSM off |
| Alcohol/tobacco as a distinct third signal from drugs | ESRB separates "Alcohol" from "Drugs" | Adds a third new signal to an already substantial milestone; alcohol references in popular music are extremely common (wine, beer, shots) and would trigger constant skips that parents may not want; merging or deferring is safer | Defer alcohol/tobacco as a separate configurable signal in v2+ per-category toggle milestone |
| Merging drug_reference into profanity SEVERITY_MAP at tier 3 | Drugs could be considered severity-3 content alongside the f-word and slurs | Conflates two categorically different content types; breaks per-category toggle extensibility; the SEVERITY_MAP is specifically for language severity, not content categories; the dashboard badge group already treats explicit/profanity as separate signals | Keep drug and sexual signals as independent scanners parallel to ProfanityScanner; do not modify SEVERITY_MAP |
| Combining drug scanner and sexual content scanner into one class | Reduces file count | Couples two independent keyword sets; harder to unit test in isolation; harder to toggle one without the other in v2+; mirroring ProfanityScanner's standalone module pattern is the correct approach | Two separate scanner modules: drug_scanner.py and sexual_content_scanner.py, following profanity_scanner.py pattern exactly |

---

## Keyword Taxonomy: Drug References

Research on drug detection in music lyrics (PMC drug-lyrics Twitter study, LYDIA alcohol algorithm) identifies two useful categories of drug terms for keyword lists:

**Pharmaceutical / common names:** Terms most parents recognize and unambiguous in context.
**Street names / slang:** Terms used in contemporary pop, hip-hop, and rap; evolve rapidly but a fixed set covers the vast majority of current usage.

### High-confidence core terms (LOW false-positive risk)

These terms have essentially no innocent meaning in a lyrics context:

- Cocaine/crack: cocaine, coke, crack, crack rock, yayo, yeyo, base
- Cannabis: weed, blunt, blunts, doobie, spliff, reefer, mary jane, kush, ganja, dank, dabs, bong, bongs, 420
- MDMA/molly: molly, mdma, ecstasy, rolling, roll
- Opioids/pills: heroin, smack, dope, oxy, oxys, oxycodone, fentanyl, xanax, xanny, xannies, percocet, perc, percs, lean, sizzurp, purple drank
- Amphetamines: meth, crystal, crank, tweak, ice, adderall (lower confidence — legitimate medical)
- General: dope (MEDIUM confidence — also means cool), stoned (LOW confidence — too ambiguous), getting high (phrase match needed), on drugs, drug dealer, plug (LOW confidence — also means electrical plug), trap (LOW — also means genre)

### Terms requiring word-boundary enforcement to avoid false positives

- "high" — extremely high false positive rate; skip entirely unless phrase-matched ("get high", "getting high", "stay high")
- "snow" — skip; too ambiguous (weather, name)
- "grass" — skip; too ambiguous
- "pot" — skip; too ambiguous (cooking pot)
- "trip" — skip; too ambiguous
- "stash" — MEDIUM risk; primarily drug context in rap but also general storage
- "dope" — MEDIUM risk; contemporary usage often just means "cool"; include with awareness of false positives

**Recommendation for v1.3:** Start with the high-confidence core set only. Err toward fewer terms with low false-positive rate. A missed drug reference is less harmful than a false positive that alienates the parent from trusting the filter.

---

## Keyword Taxonomy: Sexual Content

The sexual content detection challenge differs from drug references in one critical way: **significant overlap with existing SEVERITY_MAP in profanity_scanner.py**.

### Current SEVERITY_MAP entries that are sexual content, not profanity

Reviewing profanity_scanner.py SEVERITY_MAP, these terms are already mapped as profanity severity 2:

- `dick`, `dicks` (sev 2)
- `cock`, `cocks` (sev 2)
- `pussy`, `pussies` (sev 2)
- `tit`, `tits` (sev 2)
- `whore`, `whores` (sev 2)
- `slut`, `sluts`, `slutty` (sev 2)
- `wank`, `wanker`, `wankers`, `wanking` (sev 2)
- `twat`, `twats` (sev 2)

And severity 3:
- `fuck`, `fucking`, etc. (sev 3) — primarily profanity but has strong sexual connotation in context

**Overlap verdict:** Do NOT add these terms to SEXUAL_TERMS. They are already covered by the profanity scanner. The sexual content scanner should target terms that are NOT in SEVERITY_MAP — terms that describe sexual acts or scenarios without being standalone profanity words.

### Terms for SEXUAL_TERMS that are absent from SEVERITY_MAP

High-confidence, low false-positive:

- Sex acts (explicit): sex, sexy is borderline — skip; `making love` (phrase), `booty call`, `hook up`, `hooking up`, `one night stand`, `netflix and chill` — phrase matching required; impractical for word-split scan; defer
- Body terms not in SEVERITY_MAP: `booty` (MEDIUM — also just means butt/treasure), `ass` is in SEVERITY_MAP at sev 1 already; `naked`, `nude`, `nudes`, `undress`, `undressing`
- Sexual activity terms: `orgasm`, `masturbate`, `masturbation`, `fondle`, `groping`, `grope`
- Pornography references: `porn`, `pornography`, `xxx`, `onlyfans`
- Sexual propositions in lyrics: `sleep with`, `get in bed` — phrase matching, impractical for word-split
- Contemporary slang: `smash` (MEDIUM — high false positive in gaming context), `hit it`, `DTF` (phrase)

**Honest assessment:** Pure sexual content detection via keyword scan is harder than drug detection because most sexual slang terms either (a) already appear in SEVERITY_MAP as profanity, or (b) are too context-dependent to flag via keywords alone (e.g., "touch" is never safe to flag). The safe, high-confidence core set is smaller than the drug reference set.

**Recommendation for v1.3:** Target terms that are unambiguously sexual and absent from SEVERITY_MAP: `naked`, `nude`, `nudes`, `porn`, `pornography`, `orgasm`, `masturbate`, `masturbation`. This is a conservative list. It will miss many sexual songs that are already caught by the profanity scanner (which catches `pussy`, `dick`, `fuck`, etc.). Accept this gap — the profanity scanner covers the main vector; the sexual content signal catches songs that describe sex without using profanity words.

---

## The Overlap Problem: Sexual Content and SEVERITY_MAP

This is the most important design concern for v1.3.

**The trap:** A developer might add terms like `dick` or `pussy` to SEXUAL_TERMS because they are semantically sexual. But they are already in SEVERITY_MAP at severity 2. This creates:
1. Double-flagging: a song gets flagged for both `profanity-sev2` and `sexual_content` for the same word
2. Confusing skip log entries: "Skipped: profanity (moderate) + sexual content (dick)" — the parent sees one word triggering two badges
3. No behavior change (the song was already being skipped by the profanity scanner)

**The rule:** SEXUAL_TERMS must be a disjoint set from SEVERITY_MAP keys. Before adding any term to SEXUAL_TERMS, check SEVERITY_MAP. If it is already there, do not add it.

**Implementation check:** This should be enforced by a unit test that asserts `set(SEXUAL_TERMS) & set(SEVERITY_MAP.keys()) == set()`.

---

## Feature Dependencies

```
TrackEvalResult dataclass (new)
    └──required by──> ContentChecker.check() return type change
    └──required by──> daemon.py (all callers of check())
    └──required by──> drug and sexual content signals (need named fields to carry)
    └──must be done first in milestone plan order

DrugScanner (new module: drug_scanner.py)
    └──requires──> TrackEvalResult (to return drug_ref bool + matched terms)
    └──mirrors──> profanity_scanner.py pattern (scan(lyrics) -> tuple[bool, list[str]])
    └──wired into──> ContentChecker.__init__(drug_scanner=...) + ContentChecker.check()

SexualContentScanner (new module: sexual_content_scanner.py)
    └──requires──> TrackEvalResult (to return sexual_content bool + matched terms)
    └──mirrors──> profanity_scanner.py pattern
    └──requires──> SEXUAL_TERMS disjoint from SEVERITY_MAP (enforced by test)
    └──wired into──> ContentChecker.__init__(sexual_content_scanner=...) + ContentChecker.check()

ContentChecker.check() refactor
    └──requires──> TrackEvalResult defined
    └──requires──> DrugScanner wired in
    └──requires──> SexualContentScanner wired in
    └──existing callers (daemon.py) must be updated to use named fields instead of tuple indices

skip_events.jsonl logging
    └──requires──> TrackEvalResult carries drug_ref, sexual_content, matched terms
    └──reason field extended──> "drug_reference" | "sexual_content" | existing reasons unchanged
    └──uses──> existing _append_skip_event() — additive schema change only

Dashboard badges
    └──requires──> skip_events.jsonl carries new reason values
    └──requires──> badge CSS variants for drug-ref and sexual-content
    └──uses──> existing badge-group flex container (groundwork laid in v1.2)
    └──no new SSE infrastructure needed

Existing signals (unaffected):
    Explicit flag ──still first tier──> no change
    Profanity scanner ──still third tier──> no change to SEVERITY_MAP, no change to severity reporting
    LRCLIB fetch ──shared──> drug and sexual scanners reuse the same lyrics result
```

### Dependency Notes

- **TrackEvalResult must be designed before any scanner work:** The dataclass fields determine what information flows through the pipeline. Sketch the full dataclass first (all fields for all signals, including the new ones), then implement scanners against it.
- **DrugScanner and SexualContentScanner are parallel, not sequential:** Both receive the same `lyrics_result.lyrics` string. Order of execution in ContentChecker.check() does not matter.
- **Both scanners run only when lyrics are available:** If `lyrics_result.lyrics is None` (unavailable) or `lyrics_result.instrumental`, skip both scanners — same gating logic as the profanity scanner.
- **Skip reason priority when multiple signals fire:** A song that triggers both drug_ref and profanity-sev3 needs a clear policy. Recommendation: log all triggered signals; reason field on TrackEvalResult lists the primary reason (first-firing signal wins for the `reason` string, e.g., "explicit"), but all badge types are shown. This is consistent with the multi-badge design established in v1.2.
- **No new Spotify API calls required:** Both new signals operate on lyrics already fetched by LyricsService. Zero new network dependencies.

---

## Severity Tiers: v1.3 vs v2+

**Decision: boolean for both signals in v1.3. Severity tiers are v2+.**

Rationale:
1. PROJECT.md already deferred "Severity scoring within content categories" to v2+ — this is locked
2. For the target audience (ages 3 and 7), any drug reference or sexual content warrants a skip; the severity distinction has no actionable effect on skip behavior at this age range
3. The profanity scanner's 3-tier system exists because severity 1 (damn, hell) is the parent's deliberate choice to allow mild language — no equivalent parent preference exists for "mild drug reference"
4. Boolean signals named `drug_ref: bool` and `sexual_content: bool` on TrackEvalResult are forward-compatible: adding severity later means adding a `drug_ref_severity: int` field without removing the boolean; no breaking change

**The TrackEvalResult dataclass should be designed now to accommodate future severity fields:**

```python
@dataclass
class TrackEvalResult:
    action: str                         # "skip" | "allow"
    reason: str                         # primary reason string
    severity: int                       # profanity severity (0-3); 0 for non-profanity skips
    drug_ref: bool                      # True if drug reference detected
    sexual_content: bool                # True if sexual content detected
    matched_drug_terms: list[str]       # matched terms from DrugScanner
    matched_sexual_terms: list[str]     # matched terms from SexualContentScanner
    matched_profanity: list[str]        # matched terms from ProfanityScanner (moved from tuple)
    # Reserved for v2+:
    # drug_ref_severity: int = 0
    # sexual_content_severity: int = 0
```

This design keeps v1.3 boolean but makes the v2+ severity addition a non-breaking field addition.

---

## MVP Definition

### Launch With (v1.3)

- [ ] `TrackEvalResult` dataclass defined; replaces positional 3-tuple return from `ContentChecker.check()`
- [ ] All existing callers (daemon.py) updated to use named fields (`result.action`, `result.reason`, `result.severity`)
- [ ] `DrugScanner` in `drug_scanner.py` with high-confidence DRUG_TERMS set and `scan(lyrics) -> tuple[bool, list[str]]` interface
- [ ] `SexualContentScanner` in `sexual_content_scanner.py` with conservative SEXUAL_TERMS set (disjoint from SEVERITY_MAP) and `scan(lyrics) -> tuple[bool, list[str]]` interface
- [ ] `ContentChecker` wired with both new scanners; `check()` populates `TrackEvalResult.drug_ref`, `drug_ref_sexual_content`, `matched_drug_terms`, `matched_sexual_terms`
- [ ] Both signals trigger `action="skip"` when FSM is active (consistent with explicit and profanity)
- [ ] Both signals logged with new reason strings in skip_events.jsonl
- [ ] Dashboard badge variants for `drug-ref` and `sexual-content` in the skip feed
- [ ] Unit test asserting `set(SEXUAL_TERMS) & set(SEVERITY_MAP.keys()) == set()` to prevent overlap regression

### Defer from v1.3

- [ ] Alcohol/tobacco as a separate configurable signal — merge into drug_reference or defer to per-category toggle milestone
- [ ] Phrase matching for sexual content ("making love", "netflix and chill") — requires different matching strategy than word-split; defer to v2+ or a dedicated plan
- [ ] Severity tiers for drug or sexual signals — PROJECT.md deferred; v2+ with per-category toggle UI
- [ ] Per-category enable/disable toggles — PROJECT.md deferred; requires UI changes beyond this milestone's scope

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| TrackEvalResult dataclass | HIGH (unblocks everything else) | MEDIUM (refactor all callers) | P1 |
| DrugScanner with core terms | HIGH | LOW | P1 |
| SexualContentScanner (conservative set) | HIGH | LOW | P1 |
| ContentChecker wiring + skip dispatch | HIGH | LOW | P1 |
| Skip log entries for new signals | HIGH | LOW | P1 |
| Dashboard badges for new signals | MEDIUM | LOW | P1 |
| SEXUAL_TERMS/SEVERITY_MAP disjoint test | LOW (developer safety) | LOW | P1 |
| Phrase matching for sexual content | MEDIUM | HIGH | P3 (defer) |
| Severity tiers for drug/sexual | LOW (no behavior change for target ages) | MEDIUM | P3 (v2+) |
| Alcohol as separate signal | MEDIUM | LOW | P2 (next milestone) |

---

## Sources

- Direct code inspection: `profanity_scanner.py` SEVERITY_MAP — confirmed overlap terms; HIGH confidence
- Direct code inspection: `content_checker.py` ContentChecker.check() positional tuple pattern — HIGH confidence
- Project requirements: `.planning/PROJECT.md` v1.3 milestone section and Deferred section — HIGH confidence
- ESRB content descriptors: https://www.esrb.org/ratings-guide/ — "Drug Reference" and "Use of Drugs" as distinct boolean descriptors, not severity tiers; HIGH confidence
- IMDB Parents Guide categories: https://help.imdb.com/article/contribution/titles/parental-guide/GF4KYKYJA4PKQB32 — five discrete categories including "Alcohol/Drugs/Smoking" and "Sex and Nudity"; HIGH confidence
- RIAA Parental Advisory label evolution: https://www.unchainedmusic.io/blog-posts/understanding-the-parental-advisory-labels — three named boolean categories (strong language, violent content, sexual content); HIGH confidence
- Drug lyrics research: PMC study on drug-related lyrics (190 keyword corpus, pharmaceutical + street terms): https://pmc.ncbi.nlm.nih.gov/articles/PMC11729777/ — MEDIUM confidence (academic context; keyword sets not directly transferable but confirm taxonomy)
- LYDIA alcohol detection algorithm: https://pmc.ncbi.nlm.nih.gov/articles/PMC10794165/ — word-based detection; notes false positive risk on ambiguous terms like "rose"; MEDIUM confidence
- Scunthorpe problem / false positive analysis: https://github.com/stephenhaunts/ProfanityDetector and sightengine docs — confirmed word-boundary enforcement requirement; HIGH confidence
- Sexual content detection limitations: https://arxiv.org/html/2602.05485 — confirms keyword-only approach misses metaphor/slang; 61% F1 for dictionary-based approach; MEDIUM confidence (confirms conservative list is the right v1.3 strategy)
- Drug slang lists: https://www.palmerlakerecovery.com/drug-addiction/drug-slang-list-names-and-terms/ — consulted for slang term awareness; LOW confidence for completeness (these lists evolve; used for initial term selection only)

---

*Feature research for: drug reference detection + sexual content detection + TrackEvalResult refactor — v1.3 milestone*
*Researched: 2026-04-03*
