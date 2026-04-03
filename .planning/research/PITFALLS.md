# Pitfalls Research

**Domain:** Adding drug/sexual content detection to existing Python content filter (Spotify Family Safe Mode v1.3)
**Researched:** 2026-04-03
**Confidence:** HIGH — based on direct inspection of existing codebase

---

## Critical Pitfalls

### Pitfall 1: Substring matching catches innocent words

**What goes wrong:**
A naive `if keyword in lyrics` check or a plain `re.findall(keyword, lyrics)` call
matches word fragments. "Cocaine" is fine alone, but if "coke" is on the list it matches
"Coca-Cola", "stroke", "choke". Sexual terms are worse: "come" appears in almost every
love song, "sex" is inside "Sussex" and "sextuplets", "high" is in half the pop catalog,
"grass" appears in every outdoor lyric, "weed" is in gardening references. Children's
music is not immune — "Puff the Magic Dragon" contains "grass" and "high" throughout.
Without word-boundary anchors, every ambiguous term in the list will generate false
positives at scale.

**Why it happens:**
The existing `ProfanityScanner.scan()` deliberately avoids this by splitting on
whitespace and stripping punctuation before doing an exact dict lookup:

```python
words = normalized.split()
for word in words:
    clean = word.strip(punct_chars)
    if clean in SEVERITY_MAP:
        ...
```

That pattern is safe for single-word terms. Developers adding new detection modules
often reach for `re.search(term, lyrics)` or `term in lyrics` without realising the
existing code already solved this problem.

**How to avoid:**
Match on whole words only. Use `r'\b' + re.escape(term) + r'\b'` for every term in the
keyword list. Compile patterns once at module load, not on every lyric scan. Follow the
same split-and-strip pattern already used in `ProfanityScanner` for any single-word
terms. Never use `term in lyrics` substring containment.

**Warning signs:**
- Popular family-friendly songs ("Here Comes the Sun", "High Hopes", "Sunshine on my
  Shoulders") getting flagged in manual testing
- Any single-syllable term on the keyword list with zero false positives is suspicious —
  the list likely has not been tested yet
- False positive rate above ~1% on a known-clean playlist

**Phase to address:**
The keyword list design and matching implementation phase. Test the keyword list against
a curated clean-playlist fixture before shipping. Include at least three known-clean
songs per ambiguous term in unit tests.

---

### Pitfall 2: New sexual-content keyword list duplicates words already in SEVERITY_MAP

**What goes wrong:**
`SEVERITY_MAP` in `profanity_scanner.py` already contains explicit sexual terms at tier
2 and 3: `dick`, `cock`, `pussy`, `whore`, `slut`, `tits`, `wank`, `twat`, `cunt`,
`fag`, and more. If the new scanner re-declares these same words without coordination,
two independent code paths will both fire on the same lyric. The result is a compound
match where `reason` reflects only one signal and the other is silently dropped. Worse,
if the duplicate entry carries a different severity or different boolean flag, one result
will win arbitrarily depending on evaluation order.

**Why it happens:**
The two modules (`ProfanityScanner` and the new scanner) are developed independently.
`SEVERITY_MAP` is buried in `profanity_scanner.py` and easy to overlook. The natural
instinct is to start a new keyword list from scratch.

**How to avoid:**
Before building the new keyword list, diff it against `SEVERITY_MAP`. Words already in
`SEVERITY_MAP` at severity >= 2 should not be added to the sexual-content scanner unless
there is a deliberate reason to double-fire. Audit the two lists at code-review time. A
unit test asserting `set(SEXUAL_TERMS).isdisjoint(SEVERITY_MAP.keys())` (or that the
intersection matches a known-acceptable overlap set) will catch future regressions.

**Warning signs:**
- A song is logged with both `reason=profanity` and `has_sexual_content=True` for a word
  that is unambiguously sexual, not profane — a sign the categories are colliding
- Any word in the new scanner list that already appears in `SEVERITY_MAP` at severity >= 2

**Phase to address:**
Keyword list definition phase. Run the overlap check as a test before the list is used
in any integration.

---

### Pitfall 3: Refactoring check() 3-tuple to TrackEvalResult breaks all call sites silently

**What goes wrong:**
`ContentChecker.check()` currently returns `tuple[str, str, int]`. Every call site uses
positional unpacking:

```python
action, reason, severity = await content_checker.check(track)
```

There are at least three places in `daemon.py` that unpack this tuple (line 248 and the
`_eval_state_from_result(action, reason)` helper at line 146). The test files mock
`checker.check` returning bare tuples: `AsyncMock(return_value=("allow", "clean", 0))`.

If `check()` is changed to return a `TrackEvalResult` dataclass without simultaneously
updating every call site and every mock, Python will not raise an error at import time.
It will fail only at runtime when the unpack executes and Python tries to iterate a
dataclass (raising `TypeError: cannot unpack non-sequence TrackEvalResult` — unless the
dataclass accidentally implements `__iter__`, in which case the unpack silently succeeds
with values in the wrong order).

**Why it happens:**
Python's duck typing makes the type change invisible until the new return type actually
executes. The project does not enforce a strict mypy baseline in CI. Many tests are
marked `xfail` (test_daemon_events.py lines 92–357), meaning they do not block merges
even when they fail.

**How to avoid:**
Change all call sites atomically in the same commit as the dataclass introduction.
Update every `AsyncMock(return_value=("allow", "clean", 0))` in tests to return a
`TrackEvalResult` instance. Write a smoke-test that calls `content_checker.check()`
and asserts `isinstance(result, TrackEvalResult)`. Do not make the dataclass iterable —
force call sites to use named attribute access so any forgotten unpack site surfaces as
a `TypeError` immediately rather than silently succeeding with wrong values.

**Warning signs:**
- `grep "action, reason, severity" daemon.py tests/` still finds matches after the
  migration commit
- Any test mock still returning a bare 3-tuple after migration
- `_eval_state_from_result(action, reason)` in daemon.py still accepting positional
  string args rather than a `TrackEvalResult`

**Phase to address:**
The dataclass migration phase. This must be a single atomic commit. Enforce with a grep
check in the plan's success criteria: zero occurrences of `action, reason, severity =
await content_checker` in the codebase after the migration.

---

### Pitfall 4: New boolean fields in eval_result events not emitted on all code paths

**What goes wrong:**
`daemon.py` emits `eval_result` events in at least four separate `_append_event(...)`
call sites:
- `action == "allow"` path (line ~256)
- 5-skip pause path (line ~301)
- Successful auto-skip path (line ~347)
- FSM-off path (line ~373)

When `has_drug_content` and `has_sexual_content` are added, developers naturally update
the most visible path first (the skip path) and miss the others. The result is that some
`eval_result` lines in `events.jsonl` have the new fields and others do not. The frontend
receives inconsistent events with no error — fields read as `undefined` on old-style
events.

**Why it happens:**
The `eval_result` event dict is constructed inline at each call site rather than through
a shared factory. Four separate dict literals means four places to update.

**How to avoid:**
Extract a single `_emit_eval_result(track_id, eval_state, severity, **kwargs)` helper
that constructs and appends the event dict in one place. All four call sites become calls
to this helper. New fields are added in one location. A unit test asserting every emitted
`eval_result` event contains `has_drug_content` and `has_sexual_content` keys
(defaulting to `False`) will catch any path that calls `_append_event` directly.

**Warning signs:**
- `grep "_append_event" daemon.py` finds more than one match that builds an `eval_result`
  dict inline
- Any `eval_result` line in `events.jsonl` missing the new boolean fields after the
  daemon restarts with new code

**Phase to address:**
The event emission / log format phase. Extract the helper before adding the new fields —
do not add the fields to four separate dict literals.

---

### Pitfall 5: now_playing.json not updated with new boolean fields

**What goes wrong:**
`daemon.py` writes `now_playing.json` alongside every `eval_result` emission in four
parallel `_write_now_playing(...)` call sites (same four paths as Pitfall 4). If
`has_drug_content` and `has_sexual_content` are added to `eval_result` events but not to
the parallel `now_playing.json` write, the SSE stream will show drug/sexual badges on
newly arriving events but a hard page reload will hydrate without them. The badge
disappears on F5.

**Why it happens:**
The `eval_result` event dict and the `now_playing.json` dict are constructed separately
in every code path. They are not kept in sync by any shared structure.

**How to avoid:**
The `_emit_eval_result` helper from Pitfall 4 should also call `_write_now_playing` with
the same payload. If both writes come from the same function, they stay in sync
automatically. Add an integration test: trigger a scan cycle that returns
`has_drug_content=True`, then call `GET /now-playing` and assert the field is present.

**Warning signs:**
- Drug/sexual badge appears in the SSE feed but disappears after page reload
- `now_playing.json` on disk does not contain `has_drug_content` after a drug-detection
  scan cycle

**Phase to address:**
The event emission phase, immediately after the helper from Pitfall 4 is in place.

---

### Pitfall 6: Drug-term keyword list fires on euphemisms that are not drug references

**What goes wrong:**
Common drug-adjacent terms that appear frequently in non-drug song lyrics:
- "high" — hundreds of songs with no drug meaning ("Running High", "High Hopes",
  "Sky High", "High Road")
- "smoke" — barbecue songs, "Smoke on the Water", atmospheric descriptions
- "grass" — pastoral lyrics, gardening, sports references
- "roll" / "rolling" — "Rock and Roll", "On a Roll", "Rolling in the Deep"
- "trip" — travel songs, road trip anthems, "Day Tripper"
- "blow" — wind references ("Blowin' in the Wind"), idiomatic usage
- "stoned" — biblical references, "Stoned Soul Picnic", classical poetry
- "baked" — cooking, baking songs
- "joint" — anatomical, construction, "joint effort" idioms

With children ages 3 and 7 in the target audience and the system designed to err on the
side of caution, false positives translate directly into skipped family-friendly songs.
Enough false positives will cause the parent to disable Family Safe Mode to avoid
frustration — the opposite of the desired outcome.

**Why it happens:**
Drug vocabulary heavily overlaps with everyday English. A single-word list without
context cannot distinguish literal from metaphorical usage.

**How to avoid:**
Tier the keyword list by specificity. Reserve `has_drug_content=True` for unambiguous,
high-confidence terms only: specific drug names (heroin, cocaine, methamphetamine,
fentanyl, ketamine, oxycodone), unambiguous slang with minimal innocent usage, and
explicit drug-use action phrases. Exclude all ambiguous single-word terms ("high",
"smoke", "roll") unless they co-occur within the same lyric line as a more specific
unambiguous term. For v1.3, a short high-precision list is better than a long
high-recall list — the requirement says "boolean signal", not "comprehensive detection",
which justifies starting narrow.

**Warning signs:**
- Any common English word without drug-specific alternate spelling appears on the list
- Testing against 20 random family-friendly songs yields any false positive at all

**Phase to address:**
Keyword list design phase. Test list against a known-clean corpus before merging. Review
must be explicitly part of the phase plan's success criteria.

---

### Pitfall 7: Sexual-content scanner collides with "Mild language" badge logic at severity=1

**What goes wrong:**
The frontend shows a "Mild language" badge when `eval_state === 'passed' && severity >= 1`
(index.html lines 478–485). This badge was designed for mild profanity that does not
trigger a skip. If `has_sexual_content=True` is added as a separate boolean signal but
the song is not skipped, there is no badge variant for it in the current badge system.
A developer may try to repurpose `severity=1` to signal sexual content, which would
incorrectly display "Mild language" for a song with no profanity. Or they may silently
omit the badge, making the detection invisible in the UI.

**Why it happens:**
The badge system was designed for a single profanity severity axis. It has no
first-class support for orthogonal boolean signals. The `badge-group` div and
`badge--mild-language` CSS were added in v1.2 as an extensibility point (PROJECT.md
confirms this was groundwork for v1.3) but require new CSS classes and new JS logic
for each new signal.

**How to avoid:**
Add distinct CSS badge classes (`badge--drug`, `badge--sexual`) before wiring the JS to
display them. Do not overload the `severity` field to carry non-profanity signals — keep
`severity` strictly for profanity level as documented. In the frontend `setEvalBadge`
function, check `evt.has_drug_content` and `evt.has_sexual_content` independently and
append the appropriate badge to the existing `badge-group` flex container.

**Warning signs:**
- "Mild language" badge appearing on songs with no profanity words in the incident log
- Any code that sets `severity` to a non-zero value for a non-profanity signal

**Phase to address:**
Dashboard badge implementation phase. Add CSS classes and JS handler before wiring the
daemon signals.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Keeping `_append_event` call sites inline rather than extracting a helper | Fewer lines changed | Every new field requires updating 4+ call sites; one will be missed | Never — extract the helper in v1.3 |
| Using `in lyrics` substring matching instead of `\b` word-boundary regex | Simpler code to write | 5–20% false positive rate on common words; parent disables FSM | Never for production keyword matching |
| Deploying new boolean fields as optional (absent on old events) | Backwards-compatible with existing log | Frontend must guard every read with `?? false`; history readers get inconsistent data | Acceptable for v1.3 if frontend always guards |
| Starting with a large permissive keyword list and pruning later | More detections immediately | Parent trust damaged by false positives on first day; hard to recover | Never with real children present |
| Making `TrackEvalResult` iterable so old unpack syntax still works | No call-site changes needed | Positional access semantics preserved, defeating the purpose of the migration | Never — defeats the migration goal |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| `events.jsonl` file tail in `web_ui/main.py` | Adding fields to daemon events without checking what the SSE consumer does with unknown fields | JS consumers read `evt.fieldName` directly — unknown fields are `undefined`. Guard all new field reads with `?? false`. |
| `now_playing.json` hydration at `/now-playing` | Updating `eval_result` event but forgetting the parallel `_write_now_playing()` call | Both writes must carry the same payload. Use a shared helper or an integration test that verifies hydration reflects the scan result. |
| `ProfanityScanner.SEVERITY_MAP` | Adding sexual-content words to a new scanner that are already in `SEVERITY_MAP` at severity >= 2 | Audit overlap before adding the new list. Assert in tests that the intersection is empty or intentional. |
| `ContentChecker.check()` return type | Updating return type to dataclass but leaving test mocks returning raw tuples | Update all `AsyncMock(return_value=(...))` in the same commit as the dataclass change. |
| `_eval_state_from_result(action, reason)` in daemon.py (line 146) | Passing `TrackEvalResult` attributes to a function that still expects positional strings | Update the function signature or inline it during the dataclass migration. |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Compiling regex patterns inside `scan()` for every lyric call | Noticeable latency spike on each track change | Compile all `re.compile(r'\b...\b')` patterns once at module load in `__init__` | From the first track change; always visible as slow scans |
| Very large keyword lists (500+ terms) with `re.compile` union patterns | Regex engine backtracking on long lyrics | Keep lists short; use compiled alternation (`re.compile(r'\b(term1|term2|...)\b')`) not loop-per-term | At ~200+ terms on lyrics > 1000 words |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Logging matched drug or sexual terms verbatim to `events.jsonl` on the shared Docker volume | If a child on the same network inspects the volume, they see exact terms | Use sanitised labels ("drug reference detected") rather than the matched term in logged events; keep raw matched terms in daemon stdout only |
| Keyword list committed to a public repository | List becomes a bypass roadmap | Acceptable for a home project; not a concern for this use case |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Skip triggered by a false positive on a family-friendly song | Parent loses trust and disables Family Safe Mode entirely | Start with a short high-precision keyword list; add terms only after manual verification against a clean song corpus |
| No visual distinction between "skipped for profanity" and "skipped for drug content" in the incident log | Parent cannot tell which signal fired; harder to investigate and tune | Add distinct badge variants in the skip feed for drug/sexual reasons alongside the existing "strong language" badge |
| Boolean drug/sexual signals shown in now-playing badge only, absent from the incident log skip entry | Parent reviews incident log and cannot see which signals fired on a past skip | Ensure the `skip` event's `reason` field (or a new `signals` array) carries all active signals, not just the primary skip reason |

---

## "Looks Done But Isn't" Checklist

- [ ] **Keyword matching:** All terms use `\b` word-boundary anchors — verify with a unit test that "The High Road" does not trigger the drug "high" term
- [ ] **SEVERITY_MAP overlap:** `assert set(DRUG_TERMS).isdisjoint(SEVERITY_MAP.keys())` passes (or known-overlap set is documented)
- [ ] **SEVERITY_MAP overlap (sexual):** `assert set(SEXUAL_TERMS).isdisjoint(SEVERITY_MAP.keys())` passes (or known overlap is documented)
- [ ] **Dataclass migration:** `grep -r "action, reason, severity" .` returns zero results after the migration commit
- [ ] **eval_result consistency:** All four `_append_event` call sites in daemon.py emit `has_drug_content` and `has_sexual_content`
- [ ] **now_playing.json parity:** `has_drug_content` and `has_sexual_content` present in `now_playing.json` after a matching scan cycle
- [ ] **Test mocks updated:** No `AsyncMock(return_value=("allow", ..., ...))` bare-tuple mocks remain after dataclass migration
- [ ] **Frontend guards:** All JS reads of `evt.has_drug_content` and `evt.has_sexual_content` use `?? false` to handle pre-v1.3 events
- [ ] **Badge CSS exists:** `badge--drug` and `badge--sexual` CSS classes defined before JS tries to assign them
- [ ] **False positive test:** At least 10 family-friendly songs tested against new keyword lists with zero false positives before merging

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Substring matching shipped to production | MEDIUM | Roll back keyword list to empty, restart daemon, add word-boundary anchors, retest, redeploy |
| Dataclass migration broke daemon at runtime | HIGH | Revert to tuple return immediately (daemon is the live skip engine). Fix all call sites before re-attempting. |
| eval_result missing new fields on some code paths | LOW | Daemon restart picks up the fix on next track change; forward-guarded JS consumers handle missing fields gracefully |
| now_playing.json out of sync with eval_result | LOW | Daemon restart corrects on next track change; F5 after one song resolves it |
| False positive rate too high (parent disables FSM) | HIGH | Remove problematic terms from keyword list, restart daemon, explain to parent that the list has been tightened |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Substring matching on common words | Keyword list design + unit test phase | Automated test: family-friendly song corpus, zero false positives |
| SEVERITY_MAP overlap with new terms | Keyword list definition phase | Unit test: `isdisjoint` assertion on both new term lists vs. SEVERITY_MAP |
| Tuple-to-dataclass call-site breakage | Dataclass migration phase (must be atomic) | grep for bare-tuple unpack patterns; smoke test `isinstance(result, TrackEvalResult)` |
| Inconsistent eval_result fields across code paths | Event emission refactor phase (extract helper first) | Unit test every daemon eval path emits both new boolean fields |
| now_playing.json missing new fields | Event emission phase (same helper) | Integration test: scan cycle → GET /now-playing → assert fields present |
| Ambiguous drug terms causing false positives | Keyword list review phase | Manual test against 20 known-clean songs before merging |
| Sexual-content / profanity badge collision | Dashboard badge phase | Visual review: no "Mild language" badge on drug/sexual-only detections |
| New signals absent from incident log skip entry | Skip event emission phase | Manual: trigger drug detection, confirm incident log entry in browser shows correct badge |

---

## Sources

- Direct inspection of `content_checker.py` — `ContentChecker.check()` return type and call sites
- Direct inspection of `profanity_scanner.py` — `SEVERITY_MAP` full word list, word-boundary handling in `scan()`
- Direct inspection of `daemon.py` — `eval_result` emission call sites (lines 256–381), `_eval_state_from_result`, `_append_event`, `_write_now_playing`
- Direct inspection of `web_ui/main.py` — `_file_tail()` SSE consumer
- Direct inspection of `web_ui/templates/index.html` — `setEvalBadge()`, badge CSS classes, SSE `onmessage` handler, `badge-group` extensibility point
- Direct inspection of `tests/test_daemon_events.py` — existing mock patterns (`AsyncMock` returning bare tuples)
- Direct inspection of `data/events.jsonl` — live event schema in production use
- Project context: `.planning/PROJECT.md` — v1.3 milestone requirements, "errors on side of caution" design principle, `badge-group` as v1.3 groundwork

---
*Pitfalls research for: v1.3 drug and sexual reference detection addition to Spotify Family Safe Mode*
*Researched: 2026-04-03*
