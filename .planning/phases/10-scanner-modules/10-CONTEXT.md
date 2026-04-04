# Phase 10: Scanner Modules - Context

**Gathered:** 2026-04-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Create `DrugScanner` and `SexualContentScanner` as independent, fully-tested modules with word-boundary regex matching. These are pure scanning units — pipeline wiring into `ContentChecker` happens in Phase 11.

Both scanners return `(bool, list[str])`. Neither has severity tiers (boolean signal only). No phrase/multi-word matching — single-word keyword lists only. An LLM layer will handle nuance and hidden meanings in a future milestone.

</domain>

<decisions>
## Implementation Decisions

### Drug Keyword Philosophy
- **D-01:** Conservative keyword list only — unambiguous terms with near-zero false positive risk
- **D-02:** Include hard drug clinical names: cocaine, heroin, methamphetamine/meth, fentanyl, opioid, morphine, oxycodone, ketamine, LSD, PCP, ecstasy, MDMA, crack
- **D-03:** Include low-ambiguity slang explicitly requested: crystal meth, sizzurp, purple drank, coke
- **D-04:** Exclude ambiguous slang: "high", "weed", "pot", "joint", "dope", "blunt" — false positive risk on innocent songs too high for ages 3 & 7
- **D-05:** False positive guard: "High Hopes", "Here Comes the Sun", "Puff the Magic Dragon" must all return `(False, [])` (required by success criteria)

### Sexual Keyword Scope
- **D-06:** Cover explicit sex acts, anatomical terms, and unambiguous act slang — "obvious red flags" only; nuance deferred to future LLM layer
- **D-07:** Include explicit act words: fornicate, copulate, masturbate, ejaculate, orgasm (as verb), fellatio, cunnilingus, handjob, blowjob, fingering, rimming — none have innocent uses in lyrics
- **D-08:** Include anatomical terms not already in `SEVERITY_MAP`: penis, vagina, vulva, clitoris, scrotum, testicles, anus, nipple (and common variants/slang not already claimed)
- **D-09:** Exclude: naked, nude — too many innocent uses in mainstream lyrics
- **D-10:** `SEXUAL_TERMS` must be strictly disjoint from `SEVERITY_MAP.keys()` — enforced by unit test (SEXL-03)

### Implementation Pattern
- **D-11:** Mirror `profanity_scanner.py` file-per-scanner pattern: `drug_scanner.py` and `sexual_content_scanner.py` as separate files
- **D-12:** Each scanner is a class with a `scan(lyrics: str) -> tuple[bool, list[str]]` method, matching the existing class pattern. Pure — no instance state needed beyond the keyword set constant.
- **D-13:** Word-boundary regex matching (`re.search(r'\b' + re.escape(term) + r'\b', ...)`) — replaces the split-then-strip approach used in `ProfanityScanner`; handles punctuation-adjacent terms correctly

### Claude's Discretion
- Exact inflected forms to include per term (e.g., "cocaine" → also "cocaines"? unlikely; scanner author's call)
- Whether to pre-compile regex patterns at module level for performance
- Unit test file naming and fixture structure (follow existing test conventions)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §DRUG-01, DRUG-02, SEXL-01, SEXL-02, SEXL-03 — exact return signatures and disjoint constraint

### Existing scanner to mirror
- `profanity_scanner.py` — class structure, scan() signature pattern, SEVERITY_MAP as the canonical list of already-claimed terms (SEXUAL_TERMS must be disjoint from this)

### Phase roadmap
- `.planning/ROADMAP.md` §Phase 10 — success criteria including the three false-positive test songs

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `profanity_scanner.py`: `ProfanityScanner` class — direct template for both new scanner classes; reuse class-with-scan-method pattern
- `profanity_scanner.py`: `SEVERITY_MAP` — authoritative list of terms the sexual scanner must not overlap with (SEXL-03)

### Established Patterns
- Scanner class has no required constructor args (or `min_severity` equivalent not needed for boolean scanners)
- `scan()` returns a tuple — `(bool, list[str])` for new scanners vs `(int, list[str])` for profanity
- Logging via `log = logging.getLogger(__name__)` at module level; `log.debug(...)` for matched terms
- Tests live in `tests/` with `pytest`; existing tests use `pytest` fixtures and plain `assert` statements

### Integration Points
- Phase 11 will inject both scanners into `ContentChecker.__init__()` alongside the existing `profanity_scanner` arg
- No changes to `content_checker.py` or `daemon.py` in this phase — scanners are standalone units only

</code_context>

<specifics>
## Specific Ideas

- Crystal meth, sizzurp, purple drank, coke specifically called out by user as additions beyond pure clinical names
- "fingering" and "rimming" explicitly confirmed as low false-positive risk in lyrics context — include them
- "naked" and "nude" explicitly excluded — too many innocent lyric uses
- Future LLM layer will handle nuance, hidden meanings, and euphemisms — this scanner is the "obvious red flags" layer only

</specifics>

<deferred>
## Deferred Ideas

- Phrase/multi-word matching ("making love", "getting high", "smoke weed") — deferred to v2+ per REQUIREMENTS.md out-of-scope
- "dope", "weed", "pot", "joint", "high" as drug terms — excluded from v1.3 due to false positive risk; revisit with LLM layer
- "naked", "nude" as sexual terms — excluded; may reconsider with context-aware detection in future milestone
- Alcohol/tobacco as a separate signal — deferred per REQUIREMENTS.md out-of-scope
- LLM nuance layer — future milestone, handles euphemisms and hidden meanings

</deferred>

---

*Phase: 10-scanner-modules*
*Context gathered: 2026-04-03*
