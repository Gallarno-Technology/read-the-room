# Lyrics Filtering Research

**Domain:** Family-safe music content filtering
**Researched:** 2026-04-01
**Overall confidence:** MEDIUM-HIGH (API specifics are HIGH; coverage percentages and false-positive rates are MEDIUM due to limited benchmark data)

---

## 1. Lyrics APIs

### 1.1 LRCLIB (Recommended Primary Source)

**Verdict:** Best free option available today. No API key, no rate limits, no authentication.

**What it is:** An open-source, crowd-sourced lyrics database with ~2–3 million entries. Built explicitly for FOSS music players. No profit motive.

**Endpoints:**

```
GET https://lrclib.net/api/get
  ?track_name=<name>
  &artist_name=<artist>
  &album_name=<album>       (optional, improves match accuracy)
  &duration=<seconds>       (optional, improves match accuracy)

GET https://lrclib.net/api/search
  ?q=<search term>          (song title, lyrics fragment, artist)

GET https://lrclib.net/api/get/<id>
  (by LRCLIB internal ID)
```

**Response format:**

```json
{
  "id": 12345,
  "trackName": "Bohemian Rhapsody",
  "artistName": "Queen",
  "albumName": "A Night at the Opera",
  "duration": 354,
  "instrumental": false,
  "plainLyrics": "Is this the real life...",
  "syncedLyrics": "[00:00.00] Is this the real life..."
}
```

Returns both `plainLyrics` (plain text, good for profanity scanning) and `syncedLyrics` (LRC timestamp format).

**Rate limits:** None published. The project explicitly states no rate limiting. Community guidance is to include a `User-Agent` header with your app name and version. Using 2–3 second delays between batch requests is recommended by the community as good citizenship.

**Coverage:** ~2–3 million entries (not deduplicated). One case study processing 5,000 tracks reported a 97.5% success rate. However, that was a personal music library with good metadata. For Spotify's full catalog, coverage of niche/older/non-English tracks will be lower.

**Instrumental flag:** The response includes `"instrumental": true` when the track has no lyrics, which is directly useful for skipping lyric scan on instrumentals.

**ISRC / Spotify ID lookup:** LRCLIB does NOT support lookup by ISRC or Spotify track ID. You must look up by `track_name` + `artist_name`. Fuzzy matching means metadata quality matters. Get track name and primary artist from Spotify's `/v1/me/player/currently-playing`, then query LRCLIB.

**Full database dump available:** LRCLIB publishes SQLite database dumps at their db-dumps page. This means you could seed a local cache with the entire database and never hit the API at all for known tracks.

**Limitations:**
- Some entries have duration mismatches (5–6 seconds off), affecting synced lyric accuracy (irrelevant for plain-text profanity scan)
- Coverage thins out for very new releases (crowd-sourced, so lag exists)
- Non-English coverage is uneven — strong for English, European languages, moderate for others
- No canonical ID system; lookup is fuzzy by name/artist

**Sources:** [LRCLIB official](https://lrclib.net/), [HN discussion](https://news.ycombinator.com/item?id=39480390), [BrightCoding guide 2025](https://www.blog.brightcoding.dev/2025/12/13/the-ultimate-guide-to-automating-synchronized-lyrics-for-your-music-library-2025/)

---

### 1.2 Musixmatch API

**Verdict:** Free tier is dead. Enterprise-only as of late 2025. Do not plan around this.

**Status:** The Musixmatch developer free tier was terminated on August 25, 2025. New developer registrations on the free tier are no longer available. Existing integrations that relied on the free API (50 requests/day) are broken.

**What remains available:**
- Enterprise/commercial licensing only (contact sales, custom pricing)
- 8+ million licensed lyrics in dozens of languages — the most comprehensive database of the three options
- Powers Spotify's own in-app lyrics (via a licensing deal, not through a public API)
- Supports ISRC-based lookup in the commercial tier

**The Spotify internal lyrics endpoint:** Spotify uses Musixmatch data internally. Some reverse-engineered tools (e.g., `spotify-lyrics-api` on GitHub) intercept Spotify's internal lyrics endpoint using a user's `SP_DC` session cookie. This returns synced lyrics (LINE_SYNCED format). **This violates Spotify ToS and is not a reliable production approach.** Do not build around it.

**If budget exists:** Musixmatch commercial API is the most coverage-complete option with ISRC lookup, but expect enterprise pricing (not publicly listed, contact sales). Attribution ("Lyrics powered by Musixmatch") is required.

**Sources:** [Musixmatch API page](https://publicapis.io/musixmatch-api), [Musixmatch enterprise docs](https://musixmatch.mintlify.app/enterprise-integration/implementation-guidelines), indirect confirmation of free tier termination from affected tools

---

### 1.3 Genius API

**Verdict:** Useful for song metadata and lookup, NOT for lyric text in production.

**What the API provides:**
- Song search by title/artist
- Song metadata (release date, annotations, album art, genius song ID)
- Artist pages, album listings
- Does NOT provide lyrics text via the API

**Rate limits:** Generous for metadata-only queries; the free tier allows substantial usage. No hard published per-minute limit, but abuse triggers bans. Authentication via Bearer token (free signup at genius.com/api-clients).

**The lyrics problem:** Genius owns the lyrics on their platform through licensing agreements. The official API returns a `url` field pointing to the song page. To get actual lyrics text, you must scrape that page — which violates Genius ToS. Libraries like `LyricsGenius` (Python) and `genius-lyrics-api` (Node.js) do exactly this: API call to get the page URL, then Beautiful Soup / Cheerio scrape of the HTML. This is a grey area legally and fragile technically (Genius has changed their HTML structure before, breaking scrapers).

**Practical use case for this project:** Genius is the best source to confirm a song exists and get its canonical name/artist spelling, which you then use to look up in LRCLIB. It should not be your lyrics source.

**ISRC lookup:** Genius does not support lookup by ISRC or Spotify track ID natively. Search by song title + artist name.

**Sources:** [Genius API docs](https://docs.genius.com/), [LyricsGenius how-it-works](https://lyricsgenius.readthedocs.io/en/master/how_it_works.html), [genius-lyrics-api GitHub](https://github.com/farshed/genius-lyrics-api)

---

### 1.4 AZLyrics

**Verdict:** No API. Scraping is increasingly blocked. Not a viable option.

AZLyrics has no official API. It's protected by Cloudflare and Google reCAPTCHA. Datacenter proxies are blocked almost immediately. Residential proxies work but cost money. There is a paid Apify scraper ($0.0015/song) but this adds operational complexity and cost. Avoid.

---

### 1.5 Summary: API Recommendation

**Primary:** LRCLIB for all lyrics fetches. No key needed, no rate limit, free forever, returns plainLyrics directly.

**Fallback:** If LRCLIB misses a track, do not bother with Genius scraping in v1. Log the miss as "lyrics unavailable" and skip the lyric-scan tier for that track. Revisit if miss rate is unacceptably high.

**Spotify-to-lyrics lookup flow:**

```
Spotify /v1/me/player/currently-playing
  → track.name + track.artists[0].name + track.album.name + track.duration_ms/1000
  → LRCLIB GET /api/get?track_name=...&artist_name=...&album_name=...&duration=...
  → response.plainLyrics (or null if not found / instrumental=true)
```

---

## 2. Spotify Explicit Flag (Tier 1 Check)

The Spotify `/v1/me/player/currently-playing` endpoint returns `item.explicit: boolean` directly in the response. This is your cheapest check — no additional API call needed. If `explicit === true`, skip immediately without hitting LRCLIB at all.

**Reliability:** The explicit flag is set by the music distributor/label. It under-flags — many songs with profanity are not marked explicit (especially older music, international music, and songs where labels didn't bother). Do not rely on it as the sole filter.

**What to do:**
- If `explicit === true` → skip track immediately
- If `explicit === false` → proceed to Tier 2 (lyric scan)
- If `explicit === null` → treat as false, proceed to Tier 2

---

## 3. Curse Word Detection Libraries

### 3.1 Recommended: `obscenity` (npm)

**Package:** `obscenity` by jo3-l
**Repo:** https://github.com/jo3-l/obscenity

**Why it wins over simple wordlists:**
- Transformer-based design matches obfuscated variants: "fuuuuuuuckkk", "ʃṳ𝒸𝗄", leet-speak substitutions, Unicode homoglyphs
- Word boundary detection prevents false positives on innocent substrings (avoids matching "pen" in "penalty", "ass" in "assassin", "grass")
- Configurable: remove words you disagree with, add custom terms, disable specific transformers
- TypeScript-native, actively maintained

**Key API:**

```typescript
import { RegExpMatcher, englishDataset, englishRecommendedTransformers } from 'obscenity';

const matcher = new RegExpMatcher({
  ...englishDataset.build(),
  ...englishRecommendedTransformers,
});

// Returns true/false — use for the skip decision
const hasProfanity = matcher.hasMatch(lyricsText);

// Returns array of match objects with position info — use for logging/debugging
const matches = matcher.getAllMatches(lyricsText);
```

**Customization for lyrics context:**

```typescript
// Add music-specific slang not in default list
import { DataSet } from 'obscenity';
const customDataset = new DataSet().addPhrase(/* ... */);

// Build merged matcher
const matcher = new RegExpMatcher({
  ...englishDataset.build(),
  ...customDataset.build(),
  ...englishRecommendedTransformers,
});
```

**Limitations:**
- English-centric. Non-English profanity detection requires separate wordlists per language.
- Not perfect. Songs use creative euphemisms and coded language that no static library catches.
- The authors explicitly state: "use its output as a heuristic, not as the sole judge."

---

### 3.2 Alternatives Considered

**`leo-profanity`:** Simpler wordlist-based approach, Shutterstock dictionary, multi-language support (EN, FR, others). Faster but less robust against obfuscation. Good for languages obscenity doesn't cover.

**`naughty-words`:** Pure wordlist, no detection logic. Use as a supplementary word corpus to merge into `obscenity`'s dataset.

**`@2toad/profanity`:** Multi-language, whole-word matching. Reasonable alternative if obscenity proves overkill.

**`allprofanity`:** Claims Aho-Corasick and Bloom Filter approach with 664% performance improvement on large texts. Could be worth benchmarking for very long lyrics bodies.

**`profanity-check` (Python, not Node):** ML-based SVM model. Not applicable for a Node.js service.

**Custom wordlist:** Building your own list from sources like [dsojevic/profanity-list](https://github.com/dsojevic/profanity-list) (includes severity ratings) is viable but requires maintenance.

**Recommendation:** Start with `obscenity` + default English dataset. Augment the wordlist with music-specific slang from `naughty-words` or a custom list. Accept that it won't catch 100% of cases.

---

## 4. Content Ambiguity and Threshold Setting

### What makes a song "ambiguous"?

**Clear explicit (skip):** Contains a word from the profanity list. No ambiguity.

**Clear clean:** No profanity matches, Spotify explicit flag is false.

**Ambiguous cases:**
- Songs that reference drug use, violence, or sexual themes with euphemisms but no matching profanity (e.g., "Mary Jane", "blunt", coded language in hip-hop)
- Double entendres
- Songs in non-English languages (scanner has no wordlist for that language)
- Songs where lyrics are unavailable (LRCLIB miss)
- Instrumentals (no lyrics to scan)

### Practical V1 Threshold

**Keep it binary at v1.** A confidence-score system adds complexity without much benefit when you can't trust your data sources to be complete.

**Recommended decision tree:**

```
1. explicit flag == true          → SKIP (high confidence, fast)
2. LRCLIB returns instrumental    → ALLOW (no lyrics to check)
3. LRCLIB returns no lyrics       → ALLOW with flag (log for manual review)
4. obscenity.hasMatch(lyrics)     → SKIP (profanity detected)
5. Otherwise                      → ALLOW
```

The tricky cases (euphemisms, non-English) fall through to ALLOW in v1. That is acceptable — the Tier 3 sentiment analysis milestone is exactly the right place to handle those.

**False positive risk:** `obscenity`'s word boundary detection reduces false positives significantly compared to naive substring matching. The main remaining risk is genre-specific slang that the default wordlist over-zealously flags. Plan to maintain a whitelist of false positives (song-level or phrase-level).

**False negative risk (under-filtering):** Higher. Lyrics APIs miss some songs. Euphemisms are not detected. Non-English profanity is not detected. This is a known tradeoff for v1 — acceptable if the explicit flag is catching the most obviously problematic songs.

---

## 5. Rate Limits and Caching Strategy

### Spotify API Rate Limits

Spotify does not publish specific numeric rate limits. The limit is calculated over a rolling 30-second window. Development mode apps have a lower limit than apps in extended quota mode. The `/v1/me/player/currently-playing` endpoint is called to poll playback state.

**Safe polling interval:** 3–5 seconds for development, 1–3 seconds for production with extended quota. Polling faster than 1 second is asking for 429 errors.

**On 429:** Use the `Retry-After` response header value. Implement exponential backoff. The Spotify SDK handles this automatically if you use it.

**Track change detection:** The `item.id` field in the currently-playing response is your change signal. Only trigger lyric fetch and profanity scan when `item.id` changes from the previous poll. This means at most one LRCLIB call per new track, not one per poll cycle.

### LRCLIB Rate Limits

None published. The service asks for a `User-Agent` header as good practice. Since you are caching results locally, you will rarely hit LRCLIB more than once per unique track.

### Caching Strategy

**Recommended: SQLite as local lyrics cache.**

Rationale: A background service with one user doesn't need Redis. SQLite has zero operational overhead, survives restarts, and is sufficient for this workload. Node.js 22+ has a built-in `node:sqlite` module. Alternatively, use `better-sqlite3` for synchronous access.

**Schema:**

```sql
CREATE TABLE lyrics_cache (
  track_id      TEXT PRIMARY KEY,   -- Spotify track ID
  fetched_at    INTEGER NOT NULL,   -- Unix timestamp
  found         INTEGER NOT NULL,   -- 0 = not found, 1 = found
  instrumental  INTEGER NOT NULL,   -- 0/1
  lyrics_text   TEXT,               -- NULL if instrumental or not found
  is_explicit   INTEGER,            -- result of profanity scan: 0/1/NULL
  source        TEXT                -- 'lrclib', 'manual', etc.
);
```

**TTL:** Lyrics don't change. A TTL of 30 days is conservative; 90 days or indefinite is reasonable. Only reason to re-fetch is if the first attempt was a miss (lyrics might appear in LRCLIB later for new releases).

**Miss re-fetch strategy:** If `found = 0`, re-fetch after 24 hours for tracks that are less than 14 days old (new releases take time to appear in crowd-sourced databases). After 14 days, extend to 7-day re-check interval. After 30 days, stop retrying.

**Cache key:** Spotify track ID is the stable, unambiguous key. Do not cache by track name + artist (names can vary).

**Estimated cache size:** ~50KB per 1,000 songs (lyrics text averages ~2–4KB compressed). A 10,000-track working set is ~500KB of SQLite. Trivially small.

---

## 6. Gotchas and Edge Cases

### 6.1 Instrumentals

**Detection approaches (in priority order):**

1. LRCLIB returns `"instrumental": true` in the response body — most reliable signal when you have a LRCLIB result
2. If LRCLIB returns no result and Spotify track metadata suggests instrumental (e.g., track name contains "Instrumental", "Reprise", "Interlude") — heuristic, unreliable
3. Spotify's `instrumentalness` audio feature was in GET /audio-features, **which was deprecated in late 2024** and is now returning 403 for most apps. Do not rely on this.

**Practical handling:** If `instrumental === true` from LRCLIB, skip lyric scan and mark as ALLOW. If LRCLIB returns no lyrics at all (not found), treat as unknown — allow play but log.

### 6.2 Songs Not in LRCLIB

**Frequency:** ~2.5% miss rate on a well-tagged personal library (97.5% success rate from the cited study). In practice, expect higher miss rates for:
- Very new releases (lyrics lag by days to weeks)
- Rare / deep cuts / B-sides
- Non-English language music (especially non-Latin-script languages)
- Podcasts and spoken word (if those appear in playback)

**Handling:** Log misses, allow play, record as "lyrics unavailable." Do not block playback on missing lyrics in v1 — the false negative rate is acceptable if the explicit flag is catching the worst offenders.

### 6.3 Non-English Songs

**The problem:** `obscenity` uses an English dataset. It will not flag profanity in Spanish, French, German, Portuguese, etc.

**V1 approach:** Accept this gap. Non-English content is lower-risk for an English-speaking household. Log the language if detectable (see `franc` or `langdetect` npm packages for language detection).

**V2 option:** `leo-profanity` supports French. For broader multilingual coverage, maintain separate wordlists per language using `naughty-words` package (which has contributed lists for many languages). Detect language first, then apply the appropriate wordlist.

### 6.4 Lyrics API Reliability

**LRCLIB:** Single point of failure. It's run by a single maintainer, zero profit. It could go down or disappear. Mitigation: download the SQLite database dump periodically as a local fallback. The dump covers the entire ~3M entry database.

**Response when not found:** LRCLIB returns a 404 with `{ "error": "Track not found" }` when no match exists. Handle this explicitly.

**Matching issues:** LRCLIB matches on name fuzzy-matching. Tracks with special characters, featuring artists in the name ("feat. XXX"), or minor spelling variations may not match. Strip "feat." suffixes from track names before querying. Try with and without album name if first attempt fails.

### 6.5 API Design Pattern for the Filtering Service

```typescript
// Pseudocode for the main check loop

async function checkCurrentTrack(trackId: string, trackMeta: TrackMeta): Promise<FilterDecision> {
  // Tier 1: Spotify explicit flag (already in hand, no API call needed)
  if (trackMeta.explicit) {
    return { action: 'skip', reason: 'explicit_flag' };
  }

  // Check cache
  const cached = await db.getLyrics(trackId);
  if (cached) {
    return evaluateCached(cached);
  }

  // Tier 2: Fetch lyrics
  const lyrics = await fetchFromLRCLIB(trackMeta.name, trackMeta.artist, trackMeta.album, trackMeta.durationSecs);

  if (lyrics === null) {
    await db.recordMiss(trackId);
    return { action: 'allow', reason: 'lyrics_unavailable' };
  }

  if (lyrics.instrumental) {
    await db.recordInstrumental(trackId);
    return { action: 'allow', reason: 'instrumental' };
  }

  // Tier 2b: Profanity scan
  const hasProfanity = matcher.hasMatch(lyrics.plainLyrics);
  await db.recordLyrics(trackId, lyrics.plainLyrics, hasProfanity);

  if (hasProfanity) {
    return { action: 'skip', reason: 'profanity_detected' };
  }

  return { action: 'allow', reason: 'clean' };
}
```

### 6.6 Skip Mechanics

Spotify's Web API does not have a webhook or push mechanism for playback events. You must poll. The skip action uses:

```
POST https://api.spotify.com/v1/me/player/next
Authorization: Bearer {token}
```

**Timing concern:** If a song with profanity starts, the gap between "song starts" and "skip executes" depends on your polling interval. At 3-second polling, expect up to 3 seconds of the offensive song playing before the skip fires. For a family-safe context this is acceptable. If tighter timing is needed, reduce polling interval and accept higher API call volume.

**Pre-fetch strategy (recommended):** When a song starts playing, immediately fetch and scan the *current* track AND pre-fetch the next track in the queue if accessible. If the queue is not accessible via API, cache results so that when a track is heard again the decision is instant.

---

## 7. V3: Sentiment Analysis for Adult Themes

This is called out as a future phase in the project description. Notes for roadmap planning:

**Why a wordlist alone won't catch adult themes:** Lyrics about depression, suicide, drug use, and suggestive content can be written without a single word in a profanity list. This requires semantic understanding.

**Practical approaches for v3:**

1. **Local LLM (e.g., Ollama + Llama 3):** Run lyrics through a small local model with a prompt like "Does this song contain themes of suicide, drug use, or explicit sexual content? Reply YES or NO." Slow (~2–5s per song), no API cost, privacy-preserving.

2. **OpenAI / Anthropic API with structured output:** Fast and accurate, costs fractions of a cent per song, but requires internet and per-call billing. For a background service processing ~20 songs/hour, cost is negligible.

3. **Fine-tuned classifier:** Research cited (IEEE, PeerJ) shows Bagging/AdaBoost classifiers trained on labeled lyrics outperform wordlist approaches for explicit content detection. Building one requires labeled training data (WASABI dataset, or manually labeled sample from listening history).

**Recommendation for v3:** Start with an LLM-based approach (option 2) using structured JSON output. It avoids the training data problem and handles euphemism, context, and multiple languages natively. Cache results permanently — sentiment classification of a song does not expire.

---

## 8. Recommended Library Stack

| Purpose | Package | Notes |
|---|---|---|
| Lyrics fetch | `lrclib-api` (npm) OR direct HTTP | Thin wrapper around LRCLIB REST API |
| Profanity detection | `obscenity` | TypeScript-native, handles obfuscation |
| Supplementary wordlist | `naughty-words` | Community-maintained multi-language list |
| Local cache | `better-sqlite3` | Synchronous, zero config, persistent |
| Spotify API | `@spotify/web-api-ts-sdk` | Official Spotify TypeScript SDK |
| Language detection (v2) | `franc` | Detects language of lyrics text |

**Installation:**

```bash
npm install obscenity naughty-words better-sqlite3 @spotify/web-api-ts-sdk
npm install lrclib-api   # or just use fetch() directly
npm install -D @types/better-sqlite3
```

---

## 9. Key Decision Summary

| Decision | Recommendation | Confidence | Rationale |
|---|---|---|---|
| Primary lyrics API | LRCLIB | HIGH | Free, no key, ~97.5% hit rate, includes instrumental flag |
| Fallback lyrics API | None in v1 | MEDIUM | Complexity vs. benefit tradeoff; log misses instead |
| Musixmatch | Skip | HIGH | Free tier dead August 2025; enterprise-only |
| Genius | Skip as lyrics source | HIGH | API returns metadata only; scraping violates ToS |
| Profanity library | `obscenity` | HIGH | Best false-positive handling; obfuscation-aware |
| Instrumental detection | LRCLIB flag | HIGH | Directly in API response |
| Lyrics cache | SQLite | HIGH | Zero overhead for single-user service |
| Cache key | Spotify track ID | HIGH | Stable, unambiguous |
| Cache TTL | 90 days / indefinite | MEDIUM | Lyrics don't change; re-fetch new misses after 24h |
| Polling interval | 3s dev / 1–3s prod | MEDIUM | Spotify doesn't publish limits; community practice |
| V3 sentiment | LLM API | MEDIUM | Most flexible for euphemism/context detection |

---

## Sources

- [LRCLIB](https://lrclib.net/)
- [LRCLIB HN Discussion](https://news.ycombinator.com/item?id=39480390)
- [LRCLIB API JS wrapper](https://lrclib.js.org/)
- [BrightCoding LRCLIB guide 2025](https://www.blog.brightcoding.dev/2025/12/13/the-ultimate-guide-to-automating-synchronized-lyrics-for-your-music-library-2025/)
- [Musixmatch enterprise docs](https://musixmatch.mintlify.app/enterprise-integration/implementation-guidelines)
- [Musixmatch free tier termination confirmation](https://publicapis.io/musixmatch-api)
- [Genius API docs](https://docs.genius.com/)
- [LyricsGenius documentation](https://lyricsgenius.readthedocs.io/en/master/how_it_works.html)
- [genius-lyrics-api GitHub](https://github.com/farshed/genius-lyrics-api)
- [obscenity GitHub](https://github.com/jo3-l/obscenity)
- [dsojevic/profanity-list](https://github.com/dsojevic/profanity-list)
- [naughty-words npm](https://www.npmjs.com/package/naughty-words)
- [Spotify currently-playing API reference](https://developer.spotify.com/documentation/web-api/reference/get-the-users-currently-playing-track)
- [Spotify rate limits](https://developer.spotify.com/documentation/web-api/concepts/rate-limits)
- [Spotify audio features deprecation](https://community.spotify.com/t5/Spotify-for-Developers/About-the-latest-changes-to-current-Web-APIs-Deprecations/td-p/6547114)
- [Spotify TypeScript SDK announcement](https://developer.spotify.com/blog/2023-07-03-typescript-sdk)
- [Spotify-lyrics-api GitHub (reverse engineered, ToS risk)](https://github.com/akashrchandran/spotify-lyrics-api)
- [Explicit content ML research](https://ieeexplore.ieee.org/document/8367165/)
- [PeerJ explicit lyrics detection 2023](https://peerj.com/articles/cs-1469/)
