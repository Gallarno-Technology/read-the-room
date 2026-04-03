# Pitfalls Research

**Domain:** Extending a lyric-filter pipeline with drug reference and sexual content detection
**Researched:** 2026-04-02
**Confidence:** HIGH (codebase read directly; false positive/negative patterns verified across multiple research sources)

---

## Critical Pitfalls

### Pitfall 1: Substring Matching Causes Mass False Positives

**What goes wrong:**
The existing `ProfanityScanner.scan()` uses `str.split()` + `strip(punct_chars)` to tokenize lyrics before looking up words in `SEVERITY_MAP`. This works reasonably well for profanity because those words rarely appear as substrings of innocent words. Drug and sexual keyword lists are far more likely to contain short words that are innocent substrings: "high" in "highway" or "highlight", "blow" in "blowfish" or "elbow", "grass" in "grasshopper", "joint" in "joint venture", "cock" in "cocktail" (already partially protected by the profanity map), "roll" in "rock and roll", "score" in "scoreboard", "molly" as a common given name, "pot" in "spot" or "depot", "crack" in "cracker" or "backtrack".

The current `split()` tokenizer strips surrounding punctuation but does NOT enforce word boundaries. A lyric line like "she highlights her eyes" will match "high" if "high" is in the drug list, because after splitting the word is "highlights" and after stripping punctuation it is still "highlights" — the strip only removes leading/trailing punctuation, not embedded substrings. However the check `clean in SEVERITY_MAP` will not match "highlights" against "high". That is actually safe. The real danger is that the strip step produces shorter tokens when punctuation is adjacent: "high," → "high". So this path is actually OK for the exact-word case.

The real risk emerges if the new scanner uses `in` substring checks, `str.contains()`, or `re.search(pattern, lyrics)` without word boundaries. This is the instinctive first implementation — build a list of drug words, then `any(word in lyrics_lower for word in drug_words)` — and it is wrong.

**Why it happens:**
The profanity scanner already exists and uses a dict lookup. When adding a new scanner it is tempting to copy the simpler form: `any(keyword in lyrics for keyword in DRUG_KEYWORDS)`. Python's `in` operator performs substring matching, not whole-word matching. This is a well-documented Python gotcha: `"hell" in "hello"` is `True`.

**How to avoid:**
Use `re.search(r'\b' + re.escape(keyword) + r'\b', lyrics_lower)` for each keyword, or build a single compiled regex alternation: `re.compile(r'\b(?:' + '|'.join(re.escape(k) for k in sorted(keywords, key=len, reverse=True)) + r')\b')`. Mirror the existing split-and-lookup approach if word boundaries are reliable enough. Do not use raw `in` substring checks.

**Warning signs:**
- A test with lyrics "highlight the classroom on the whiteboard" triggers drug detection
- A test with "cockney accent" triggers sexual detection
- A test with "grasshopper" triggers drug detection
- Any test where the matched keyword is shorter than the actual word in lyrics

**Phase to address:** Drug detection implementation phase (before any integration into ContentChecker)

---

### Pitfall 2: No Context Awareness — "High" in Hymns, "Roll" in Rock, "Blow" in Jazz

**What goes wrong:**
Keyword lists flag words that are legitimately drug-coded in one genre but completely innocent in another. "High" is a drug reference in "I get high with a little help from my friends" but not in "How Great Thou Art" ("Then sings my soul"). "Blow" is slang for cocaine in hip-hop but the name of a Miles Davis album. "Mary Jane" flags as marijuana but is also Spider-Man's girlfriend. "Trees" is slang for marijuana in some lyrics but appears in thousands of innocent songs about nature.

Because the existing pipeline has no context model — it is deliberately keyword-only, per the PROJECT.md "Sentiment NLP — too complex for v1" decision — these false positives cannot be fully resolved. But an unmanaged list will make the feature unusable.

**Why it happens:**
Drug and sexual euphemism lists circulate online and are tempting to import wholesale. These lists are optimized for recall (catch everything), not precision (avoid false positives). Importing one unchanged into a binary skip decision causes the family filter to skip innocent songs constantly, which is worse than missing some drug references — it breaks trust and the toggle gets turned off permanently.

**How to avoid:**
- Prefer specific multi-word phrases over single common words: "getting high" not "high", "roll a blunt" not "roll", "hit the pipe" not "hit"
- Exclude words that are also proper nouns, place names, or common given names from the single-word list: "Molly", "Mary Jane", "Charlie", "Lucy in the sky" — use full phrase matching
- Maintain an explicit allow-list (known false positive phrases) that short-circuits the keyword check: if any allow-phrase is present, suppress the signal
- Set an initial list that is small and deliberately conservative — start with 20–30 clearly unambiguous phrases rather than 200 ambiguous single words
- Log every match at INFO level with the matched phrase and surrounding 5 words; review the first 20 real-world matches before finalizing the list

**Warning signs:**
- More than 10% of skips attributed to the new signal within the first week of use
- Classic rock, gospel, or jazz tracks being flagged
- Tracks with matching artist names ("The Doors", "The Stones") triggering lyric detection because an artist name fragment matches

**Phase to address:** Keyword list design (before implementation), then reviewed after first production run

---

### Pitfall 3: Return Type Changes Break the ContentChecker Integration Contract

**What goes wrong:**
`ContentChecker.check()` currently returns `tuple[str, str, int]` — `(action, reason, severity)`. The daemon and test suite both unpack this tuple positionally. Adding two new boolean signals (drug reference, sexual content) requires extending this return type.

If the new signals are appended to the tuple (making it a 5-tuple), every call site that does `action, reason, severity = await content_checker.check(track)` raises `ValueError: too many values to unpack`. The daemon has one call site; the test suite has implicit assumptions about the shape. The web UI skip event dict also uses `reason` to categorize skips in the SSE feed.

**Why it happens:**
Tuple positional unpacking is fragile — adding to the end looks backward-compatible but breaks any unpacking assignment. This is a common Python API evolution mistake.

**How to avoid:**
Replace the tuple return with a dataclass or `TypedDict` before adding fields:
```python
@dataclass
class CheckResult:
    action: str          # 'skip' | 'allow'
    reason: str          # existing reasons + 'drug_reference' | 'sexual_content'
    severity: int        # 0–3
    drug_reference: bool # new
    sexual_content: bool # new
```
Update all call sites at the same time. The daemon's `action, reason, severity = await content_checker.check(track)` line becomes `result = await content_checker.check(track)` with attribute access. This is a refactor that should be done in a single commit covering ContentChecker, daemon, and tests together.

Alternatively, extend the reason string to encode the new signals (`reason="drug_reference"`, `reason="sexual_content"`) and keep the 3-tuple intact. This avoids changing call sites but loses the ability to log both signals independently (e.g., a track that is both drug-referenced and sexually explicit).

**Warning signs:**
- `ValueError: not enough values to unpack` or `too many values to unpack` in daemon logs
- Test failures on any test that unpacks the check() return value
- SSE feed showing `undefined` or missing reason fields in the browser dashboard

**Phase to address:** ContentChecker return type refactor (must happen before adding new signals)

---

### Pitfall 4: Cached Lyrics Are Not Re-scanned After Keyword List Changes

**What goes wrong:**
`LyricsService` caches lyrics in SQLite keyed by Spotify track ID with no schema version or scan-result invalidation. The cache stores `plain_lyrics` text but does NOT store drug/sexual detection results. This is fine — the scan happens in `ContentChecker` on each play, not at cache-write time. However, if someone adds a new scanner (DrugScanner, SexualContentScanner) as a stateful object that caches its own scan results in the DB, those results will become stale when the keyword list is updated.

The specific failure mode: a developer adds a `drug_detected` column to `lyrics_cache` to avoid re-scanning on repeat plays. The keyword list is later updated. The cached `drug_detected = 0` result from the old list is served, and the new keywords are never evaluated against that track's lyrics until the cache entry expires (90 days by default) or is manually deleted.

**Why it happens:**
Performance optimization impulse — "why re-scan lyrics we've already fetched?" is reasonable. The problem is conflating the immutable fact (lyrics text) with the mutable decision (drug/sexual signal given the current keyword list).

**How to avoid:**
Keep scan results out of the lyrics cache. The `lyrics_cache` table stores the raw text — always correct, no TTL issue. The scan runs in memory on each new-track event against the cached text. This adds ~1ms of CPU for a string scan; it is not a performance concern. Do not add `drug_detected` or `sexual_detected` columns to `lyrics_cache`.

If scan-result persistence is ever needed for analytics, put it in a separate `scan_results` table with a `keyword_list_version` column that is invalidated when the list changes.

**Warning signs:**
- A scan result column added to `lyrics_cache` during implementation
- A `scan()` call that writes back to SQLite
- Any test that verifies a cached scan result rather than scanning fresh text

**Phase to address:** DrugScanner and SexualContentScanner implementation (architectural guardrail, enforce during code review)

---

### Pitfall 5: The `better-profanity` Fallback Fires on Drug/Sexual Keywords

**What goes wrong:**
`ProfanityScanner.scan()` has a Pass 2 that calls `profanity.contains_profanity(normalized)` from the `better-profanity` library. If `better-profanity`'s default word list includes some drug slang or sexual terms — and it does, since "bitch", "pussy", "cock", "dick", "whore", "slut" are in the existing `SEVERITY_MAP` at severity 2 — then new keyword lists may overlap with what `better-profanity` already catches.

The dual-fire problem: a track triggers both the new SexualContentScanner AND `better-profanity`, resulting in `reason="profanity"` logged but `sexual_content=True` also set on the `CheckResult`. The skip fires from the profanity path (severity >= 2), but the `sexual_content` flag is set for a word that was already in the profanity map. The logged data becomes ambiguous — did this skip because of "new" sexual content detection, or because the word was already in the profanity map?

**Why it happens:**
The two scanners operate independently without coordination. The new scanners do not know what `SEVERITY_MAP` already contains.

**How to avoid:**
Deduplicate word lists during construction: words already in `SEVERITY_MAP` at any severity level should not be added to the new drug or sexual keyword lists. The new lists are intended to catch signals that profanity scanning misses — euphemisms, slang, coded language. Straightforward explicit sexual terminology is already covered by profanity severity 2+.

For the `reason` field: use a priority ordering when multiple signals fire. If `action=skip` is triggered by profanity (severity >= min_severity), `reason="profanity"` takes precedence. The drug/sexual booleans are still set as secondary metadata on the `CheckResult`.

**Warning signs:**
- The same word appearing in both `SEVERITY_MAP` in `profanity_scanner.py` and the new drug/sexual keyword list
- Skip events logged with `reason="profanity"` but the matched word is in the sexual content list
- Test cases that expect `reason="sexual_content"` but observe `reason="profanity"` because `better-profanity` fires first

**Phase to address:** Keyword list construction (explicitly cross-reference SEVERITY_MAP during design)

---

### Pitfall 6: False Negatives from Heavy Euphemism — The "Miss Rate" Is High and That Is Fine

**What goes wrong:**
Developers building keyword-based drug and sexual detection often see the miss rate — tracks with drug themes that use no keyword from the list — and react by aggressively expanding the keyword list. This expansion loop produces more false positives without meaningfully improving recall. Songs like "Lucy in the Sky with Diamonds", "Semi-Charmed Life", "Brown Sugar", or most coded hip-hop will not be caught by any keyword list that keeps false positives at an acceptable level. This is not a bug; it is a fundamental limitation of keyword-only detection.

The mistake is treating the miss rate as a defect to fix within this milestone, leading to scope creep into NLP/LLM territory that was explicitly deferred.

**Why it happens:**
The parent using this system has a young child and sees a drug-themed song slip through. The instinct is "add more words". But the marginal words are also the most ambiguous ones.

**How to avoid:**
Document the miss rate expectation explicitly in code comments and the FEATURES spec: "This scanner catches direct, unambiguous drug/sexual references. Songs using heavy euphemism or coded language are false negatives by design. Severity scoring and LLM-based detection are deferred to v2+." Set a specific quality bar: the scanner should catch direct references in 4 out of 5 songs where the Spotify explicit flag is already set (since those songs frequently contain direct references in lyrics), and should NOT skip more than 1 in 50 innocent songs.

**Warning signs:**
- Keyword list exceeds 100 entries (scope creep signal)
- Single-syllable common words ("get", "light", "roll", "blow", "come") being added to the list
- A discussion about "should we add 'smoke' because it could mean weed" — that conversation is the warning sign

**Phase to address:** Keyword list design review gate before implementation begins

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Raw `in` substring check instead of word-boundary regex | 2-line implementation | Mass false positives on innocent words; "grass" matches "grassroots" | Never — use `\b` word boundaries from the start |
| Adding `drug_detected` column to `lyrics_cache` | Avoids re-scan on repeat plays | Stale cached results after keyword list updates; requires cache invalidation logic | Never — scan in memory, store only raw lyrics |
| Copy-pasting a large drug/sexual euphemism list from GitHub | Fast keyword list bootstrap | Too many ambiguous single-word entries; high false positive rate from day one | Only if filtered down to unambiguous multi-word phrases before use |
| Keeping `check()` as a 3-tuple instead of refactoring to dataclass | No call-site changes | Impossible to add new signals without breaking all callers; deferred pain makes the refactor larger later | Never if adding new return fields; only acceptable if signals are encoded in the existing `reason` string |
| One combined "explicit content" scanner instead of two separate scanners | Simpler class structure | Cannot toggle drug vs. sexual detection independently in the next milestone (per-category UI toggles are the stated next feature) | Never — PROJECT.md explicitly names per-category toggles as next milestone |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| `ContentChecker.check()` return type | Appending to the existing 3-tuple | Refactor to a `CheckResult` dataclass with named fields before adding new signals |
| `daemon.py` skip event dict | Forgetting to propagate `drug_reference` and `sexual_content` booleans to the `skip_events.jsonl` payload | Update the event dict construction at both `_append_skip_event()` call sites to include the new fields from `CheckResult` |
| `web_ui/main.py` SSE feed | SSE skip events use `reason` string; new reasons `"drug_reference"` and `"sexual_content"` need to be handled in the frontend | Add the new reason strings to any switch/match statement or CSS class mapping in the dashboard JavaScript |
| `ProfanityScanner` Pass 2 (`better-profanity`) | New sexual keywords that overlap with `better-profanity`'s built-in list cause double-firing | Cross-reference `better_profanity.profanity.CENSOR_WORDLIST` at init time and exclude overlapping words from the new lists |
| `lyrics_cache` SQLite schema | Temptation to cache scan results alongside lyrics | Keep scan results out of the lyrics cache; scan in memory on every play using cached plain text |
| `SEVERITY_MAP` in `profanity_scanner.py` | New scanner lists include words already in severity 2+ profanity map | Deduplicate: new lists should only contain words absent from `SEVERITY_MAP` |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Compiling a new regex per keyword on every scan call | Scan latency grows linearly with keyword list size; noticeable if list exceeds ~200 words | Compile a single alternation regex at module load time: `re.compile(r'\b(?:phrase1\|phrase2\|...)\b', re.IGNORECASE)` | At ~100+ keywords per scan; the existing profanity scanner does not hit this because it uses a dict lookup |
| Using `re.search` in a loop over 200+ keywords | Each `re.search()` call is O(lyrics_length) per keyword | Build one compiled pattern with alternation; a single pass over the lyrics text is O(lyrics_length) regardless of keyword count | At 50+ keywords with lyrics averaging 300–500 words |
| Blocking the asyncio event loop with CPU-bound regex scan | Poll loop stalls; skip latency increases | The existing scanner is synchronous and called directly from the async poll loop. For lists under 300 keywords and lyrics under 5KB, a synchronous scan completes in <2ms — acceptable. If list grows beyond 500 keywords, wrap in `run_in_executor` | This is not a concern at the keyword counts appropriate for this milestone; flag if keyword list exceeds 500 entries |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Storing keyword lists in plaintext in the repository | The list itself is not sensitive, but very specific euphemism lists can be gamed by anyone who can read them | Not a meaningful security concern for a home server project; keyword lists are semi-public by nature |
| Logging matched drug/sexual keywords verbatim in INFO-level daemon logs | Logs visible to anyone with Docker access; matched words are by definition explicit | Already mitigated by existing pattern: `[SCAN] matched=[...]` logs are INFO-level and the matched word list is controlled. No change needed; keep existing log format |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| New signals skip songs that were previously allowed without informing the parent why | Parent turns off Family Safe Mode because songs they liked are now being skipped, with no way to understand why | Ensure `reason` in skip events uses distinct values (`"drug_reference"`, `"sexual_content"`) so the skip history feed in the dashboard shows the specific signal that fired |
| Both drug and sexual signals log separately but the skip feed shows only one reason | Parent cannot tell if a song was skipped for both drug AND sexual content, or only one | The `CheckResult` dataclass approach (vs. single-string reason) allows logging both signals simultaneously: log `drug_reference=True sexual_content=True` when both fire |
| Surprise skips on songs the family knows and trusts (classic rock, country) from the new keyword lists | Trust in the system collapses; FSM gets turned off permanently | Conservative list design (multi-word phrases over single words) is the only mitigation; cannot fix this with UI alone |

---

## "Looks Done But Isn't" Checklist

- [ ] **Drug scanner:** Returns `False` for clean lyrics — verify with a test that passes a verse from a children's song and asserts no detection
- [ ] **Drug scanner:** Does NOT match "high" in "highway", "joint" in "joint venture", "pot" in "sport" — word boundary tests exist
- [ ] **Sexual content scanner:** Does NOT match "cock" in "cocktail", "ass" in "grassland" or "classroom", "tit" in "title" — word boundary tests exist
- [ ] **ContentChecker:** Return type is a dataclass with named fields, not a tuple — call sites use attribute access, not positional unpacking
- [ ] **ContentChecker:** `drug_reference` and `sexual_content` fields exist on `CheckResult` and are independently settable
- [ ] **Daemon skip event:** Both `drug_reference` and `sexual_content` fields are present in the `skip_events.jsonl` payload written by `_append_skip_event()`
- [ ] **Keyword lists:** Cross-referenced against `SEVERITY_MAP`; no word appears in both
- [ ] **Keyword lists:** No plain single-word entries that are also common English words unrelated to the target category ("high", "blow", "pot", "score", "grass", "roll")
- [ ] **LyricsCache:** No `drug_detected` or `sexual_detected` columns added to the SQLite schema

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Substring false positives already in production | LOW | Edit the keyword list to remove or replace the offending single-word entries with multi-word phrases; no schema migration needed; cache contains only lyrics text |
| Return type broken — daemon crashes on tuple unpack | MEDIUM | Patch daemon.py call site to unpack new tuple length or switch to dataclass; redeploy container |
| Scan results cached in SQLite and now stale | MEDIUM | Add a migration to drop the scan-result columns; re-scan all cached lyrics on next startup (or just delete the cache file and let it rebuild from LRCLIB) |
| Keyword list causes >10% false positive skip rate | LOW–MEDIUM | Temporarily narrow the list to top 10 most unambiguous phrases; review skip log to identify false positive patterns; restore cautiously |
| `better-profanity` overlapping with new sexual list — double-fire confusion in logs | LOW | Remove overlapping words from new list; they are already covered by existing profanity detection |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Substring matching false positives (Pitfall 1) | DrugScanner / SexualContentScanner implementation | Unit tests: verify "highway" does not match "high"; "cocktail" does not match "cock" |
| Context ambiguity / overly broad keywords (Pitfall 2) | Keyword list design review before implementation | Curated list review: no single-word entries that are also common non-drug/non-sexual English words |
| Return type contract break (Pitfall 3) | ContentChecker refactor phase (before new scanners) | All existing tests pass after refactor; daemon starts cleanly; no tuple unpack errors |
| Cached lyrics / stale scan results (Pitfall 4) | Scanner implementation (architectural guardrail) | Code review check: no new columns in `lyrics_cache`; scan result stored in CheckResult only |
| `better-profanity` overlap / double-fire (Pitfall 5) | Keyword list construction | Cross-reference check: assert that `set(DRUG_KEYWORDS) & set(SEVERITY_MAP.keys()) == set()` in a test |
| False negative scope creep (Pitfall 6) | Keyword list design review | Keyword list size gate: CI fails if either list exceeds 80 entries |

---

## Sources

- Codebase direct read: `content_checker.py`, `profanity_scanner.py`, `lyrics_service.py`, `daemon.py` — HIGH confidence
- [Covering Cracks in Content Moderation: Delexicalized Distant Supervision for Illicit Drug Jargon Detection (KDD 2025)](https://arxiv.org/html/2503.14926v1) — MEDIUM confidence (context-based vs. keyword-based drug jargon detection tradeoffs)
- [Fine-Tuning LLMs for Sexually Explicit Content in Spanish Song Lyrics (2026)](https://arxiv.org/html/2602.05485) — MEDIUM confidence (confirms keyword-only approaches miss metaphor and coded language)
- [Explicit Content Detection in Music Lyrics Using Machine Learning — IEEE 2018](https://ieeexplore.ieee.org/document/8367165/) — MEDIUM confidence (still-relevant ML vs. keyword comparison)
- [A novel approach for explicit song lyrics detection — PeerJ 2023](https://peerj.com/articles/cs-1469/) — MEDIUM confidence (false positive analysis in keyword approaches)
- [Toxic keyword lists and filters guide 2026 — Sightengine](https://sightengine.com/keyword-lists-for-text-moderation-the-guide) — MEDIUM confidence (practical content moderation false positive patterns)
- [Python Gotcha: Word boundaries in regular expressions — Developmentality](https://developmentality.wordpress.com/2011/09/22/python-gotcha-word-boundaries-in-regular-expressions/) — HIGH confidence (confirmed against Python docs)
- [Python `re` module documentation — python.org](https://docs.python.org/3/library/re.html) — HIGH confidence (`\b` word boundary behavior)
- [better-profanity PyPI](https://pypi.org/project/better-profanity/) — HIGH confidence (default word list behavior)
- `.planning/PROJECT.md` — HIGH confidence (confirmed existing pipeline structure, active requirements, deferred scope)
- `.planning/research/LYRICS_FILTERING.md` — HIGH confidence (prior research on false positive / false negative tradeoffs, LRCLIB coverage)

---
*Pitfalls research for: drug reference and sexual content detection extension to existing lyric filter pipeline*
*Researched: 2026-04-02*
