# Phase 2: Content Filtering & Auto-Skip - Research

**Researched:** 2026-04-01
**Domain:** Content filtering, lyrics APIs, profanity detection, Sonos/Spotify playback control
**Confidence:** HIGH

## Summary

Phase 2 adds the core product value: automatic content filtering and track skipping. The architecture is a three-tier filter (explicit Spotify flag, LRCLIB lyrics fetch, profanity scan) with dual skip paths (SoCo for Sonos, Spotify API for everything else). All required libraries exist, are actively maintained, and have straightforward APIs. The main integration challenge is hooking filtering into the existing async poll loop without blocking, and managing the additional OAuth scope (`user-modify-playback-state`) required for Spotify skip.

The "obscenity library" referenced in CONTEXT.md does not exist as a named Python package with severity tiers. Research recommends `better-profanity` for leet-speak-aware detection combined with a custom severity word mapping (three tiers: mild=1, moderate=2, severe=3) to implement the `PROFANITY_MIN_SEVERITY` threshold. This avoids a heavy scikit-learn dependency while satisfying all requirements.

**Primary recommendation:** Use `lrclibapi` for lyrics, `better-profanity` + custom severity mapping for profanity scanning, `soco` for Sonos skip, `spotipy` (already installed) for Spotify skip, and `aiosqlite` for async SQLite lyrics cache.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Detect Sonos speakers using the Spotify `is_restricted: true` device flag from the currently-playing API response. No SoCo network scan at startup, no user-configured room name list.
- **D-02:** Log the device name and `is_restricted` value on every track change so detection can be debugged easily.
- **D-03:** Abstract the skip action behind a `SkipClient` interface with two concrete implementations: `SocoSkipClient` (local UPnP, self-hosted) and `SpotifySkipClient` (Spotify API, non-Sonos). The daemon selects at runtime based on D-01.
- **D-04:** The interface must be designed so a future `BridgeSkipClient` (central-hosting path via local LAN bridge) can be plugged in without modifying daemon.py. Self-host remains the primary deployment target for v1.
- **D-05:** FSM is toggled via `make fsm-on` and `make fsm-off` Makefile targets. These write `{"family_safe_mode": true/false}` into state.json. Phase 3 (Web UI) will add in-browser toggle.
- **D-06:** Daemon reads `family_safe_mode` from state.json on every poll cycle (not cached at startup), so toggle takes effect within one poll interval (~1s).
- **D-07:** Phase 2 has no notification delivery (Signal dropped; Web UI arrives in Phase 3). All skip events, profanity detections, and FSM state changes are written as structured log lines to stdout. Log format: `[SKIP] reason=explicit track="X" artist="Y"` -- machine-parseable for future ingestion by the Web UI.
- **D-08:** Default threshold: moderate/severe words only (not any-match). Mild language ("damn", "hell") passes through at default settings.
- **D-09:** Log the severity score for every scanned track to stdout, including tracks that are NOT skipped. Format: `[SCAN] track="X" artist="Y" severity=2 matched=["word"] action=allow`.
- **D-10:** Threshold is configurable via env var `PROFANITY_MIN_SEVERITY` (integer, default 2 = moderate). Phase 2 reads this from `.env`.
- **D-11:** Self-host (single Proxmox/Docker deployment) remains the primary and only supported mode for v1.
- **D-12:** No per-user data model, auth layer, or multi-tenancy in Phase 2.

### Claude's Discretion
- SQLite schema for lyrics cache (FILT-06) -- column names, indexes, cache TTL strategy
- Exact SoCo method calls for skip (`next_track()` vs transport skip)
- Error handling for LRCLIB rate limits and timeouts
- How consecutive-skip count is tracked across the poll loop (in-memory vs state.json)

### Deferred Ideas (OUT OF SCOPE)
- Web UI (Phase 3 replacement): Signal is dropped. Phase 3 should become a Web UI.
- Sonos Cloud API: Remote Sonos control without a local bridge.
- Local bridge for central hosting.
- Per-family profanity threshold.
- Non-English profanity detection.

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FILT-01 | Tracks marked `explicit: true` by Spotify are immediately flagged for auto-skip | Spotify `currently_playing()` already returns `track["explicit"]` (Phase 1 logs it). Trivial boolean check. |
| FILT-02 | For non-explicit tracks, lyrics are fetched from LRCLIB using track title and artist | LRCLIB API: `GET /api/get?track_name=X&artist_name=Y`. Python wrapper `lrclibapi` 0.3.1. No auth, no rate limits. |
| FILT-03 | Lyrics scanned for profanity using the `obscenity` library (handles obfuscation and leet-speak) | No Python package named "obscenity" exists. Recommend `better-profanity` 0.7.0 which handles leet-speak natively, combined with custom severity word mapping. |
| FILT-04 | Instrumental tracks (LRCLIB `instrumental: true` or no lyrics found) are allowed without scanning | LRCLIB response includes `instrumental` boolean. When `true`, skip profanity scan entirely. |
| FILT-05 | Tracks with lyrics unavailable in LRCLIB are treated as ambiguous (not auto-skipped) | LRCLIB returns 404 when track not found. Treat as "allow" -- do not skip. |
| FILT-06 | Fetched lyrics cached locally (SQLite, keyed by track ID) to avoid repeat API calls | `aiosqlite` 0.22.1 for async access. Schema: `spotify_track_id` PK, `instrumental` bool, `plain_lyrics` text, `fetched_at` timestamp. |
| SKIP-01 | Sonos speakers skipped via SoCo (local UPnP) | SoCo 0.30.14: `soco.discovery.by_name(room_name).next()`. But per D-01, discovery is by Spotify device name, not SoCo scan -- need `by_name()` with name from Spotify API. |
| SKIP-02 | Non-Sonos devices skipped via Spotify API (`POST /me/player/next`) | Spotipy `sp.next_track(device_id=None)`. Requires `user-modify-playback-state` scope (must be added). |
| SKIP-03 | Service detects whether active device is Sonos and routes skip accordingly | Per D-01: check `device["is_restricted"]` from `currently_playing()` response. `True` = Sonos, use SoCo. `False` = Spotify API. |
| FSM-01 | Family Safe Mode can be toggled on/off (persisted in local state file) | Extend `state.json` with `family_safe_mode` key. Makefile targets `fsm-on`/`fsm-off` write JSON. |
| FSM-02 | Filtering and skipping only occurs when Family Safe Mode is active | Read `state["family_safe_mode"]` each poll cycle (D-06). Guard all filter logic behind this check. |

</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| soco | 0.30.14 | Sonos speaker discovery and playback control via UPnP | Only maintained Python Sonos library; used by Home Assistant |
| lrclibapi | 0.3.1 | Python wrapper for LRCLIB lyrics API | Official wrapper, handles HTTP details, typed responses |
| better-profanity | 0.7.0 | Profanity detection with leet-speak handling | Handles obfuscation (p0rn, h4NDjob, b*tCh) per FILT-03 requirement |
| aiosqlite | 0.22.1 | Async SQLite access for lyrics cache | Async-compatible with existing asyncio poll loop |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| spotipy | 2.26.0 (existing) | Spotify API skip endpoint | Already installed; add `user-modify-playback-state` scope |
| python-dotenv | 1.2.2 (existing) | Read PROFANITY_MIN_SEVERITY from .env | Already installed; existing pattern |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| better-profanity | alt-profanity-check 1.8.0 | ML-based probability scores (natural severity), but heavy scikit-learn dependency, no leet-speak handling, requires Python >=3.11 |
| better-profanity | profanity-check | Same as alt-profanity-check (it is the original, less maintained) |
| lrclibapi | Raw httpx/aiohttp calls | No benefit; lrclibapi is thin, typed, and handles edge cases |
| aiosqlite | sqlite3 (stdlib) | Synchronous; would block the asyncio event loop on disk I/O |

**Installation (add to requirements.txt):**
```bash
soco==0.30.14
lrclibapi==0.3.1
better-profanity==0.7.0
aiosqlite==0.22.1
```

## Architecture Patterns

### Recommended Project Structure
```
/app/
  daemon.py              # Existing poll loop -- add ContentChecker integration
  content_checker.py     # Three-tier filter orchestrator
  lyrics_service.py      # LRCLIB fetch + SQLite cache
  profanity_scanner.py   # better-profanity wrapper + severity mapping
  skip_client.py         # SkipClient interface + SocoSkipClient + SpotifySkipClient
  state.json             # Extended: {last_track_id, family_safe_mode, consecutive_skips}
  Makefile               # Add fsm-on / fsm-off targets
```

### Pattern 1: Three-Tier Filter Pipeline
**What:** ContentChecker runs three checks in order, short-circuiting on first match.
**When to use:** Every track change when FSM is on.
**Example:**
```python
# content_checker.py
class ContentChecker:
    def __init__(self, lyrics_service, profanity_scanner):
        self.lyrics_service = lyrics_service
        self.profanity_scanner = profanity_scanner

    async def check(self, track: dict) -> tuple[str, str, int]:
        """Returns (action, reason, severity).
        action: 'skip' or 'allow'
        reason: 'explicit', 'profanity', 'instrumental', 'clean', 'lyrics_unavailable'
        severity: 0-3 (0=none, 1=mild, 2=moderate, 3=severe)
        """
        # Tier 1: Spotify explicit flag (instant, no API call)
        if track["explicit"]:
            return ("skip", "explicit", 3)

        # Tier 2: Fetch lyrics (cache-first, then LRCLIB)
        lyrics_result = await self.lyrics_service.get_lyrics(
            track_id=track["id"],
            track_name=track["name"],
            artist_name=track["artists"][0]["name"],
        )

        if lyrics_result.instrumental:
            return ("allow", "instrumental", 0)

        if lyrics_result.lyrics is None:
            # FILT-05: lyrics unavailable = ambiguous, do NOT skip
            return ("allow", "lyrics_unavailable", 0)

        # Tier 3: Profanity scan
        severity, matched = self.profanity_scanner.scan(lyrics_result.lyrics)
        if severity >= self.min_severity:
            return ("skip", "profanity", severity)

        return ("allow", "clean", severity)
```

### Pattern 2: SkipClient Interface (Strategy Pattern)
**What:** Abstract skip action so SoCo and Spotify implementations are interchangeable.
**When to use:** Every skip action; selection based on `is_restricted` device flag.
**Example:**
```python
# skip_client.py
from abc import ABC, abstractmethod

class SkipClient(ABC):
    @abstractmethod
    async def skip(self, device_name: str, device_id: str) -> bool:
        """Skip current track. Returns True on success."""
        ...

class SpotifySkipClient(SkipClient):
    def __init__(self, sp: spotipy.Spotify):
        self.sp = sp

    async def skip(self, device_name: str, device_id: str) -> bool:
        # spotipy is synchronous -- run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.sp.next_track, device_id)
        return True

class SocoSkipClient(SkipClient):
    async def skip(self, device_name: str, device_id: str) -> bool:
        loop = asyncio.get_event_loop()
        # Use SoCo discovery by name (from Spotify device name)
        device = await loop.run_in_executor(
            None, soco.discovery.by_name, device_name
        )
        if device is None:
            raise RuntimeError(f"Sonos speaker '{device_name}' not found on network")
        await loop.run_in_executor(None, device.next)
        return True
```

### Pattern 3: Severity Word Mapping (Custom)
**What:** Since `better-profanity` only returns boolean, maintain a curated word-to-severity mapping for the logging/threshold requirement.
**When to use:** Every profanity scan to satisfy D-08, D-09, D-10.
**Example:**
```python
# profanity_scanner.py
from better_profanity import profanity

# Curated severity tiers
SEVERITY_MAP = {
    # 1 = mild (damn, hell, crap, ass)
    "damn": 1, "hell": 1, "crap": 1, "ass": 1,
    # 2 = moderate (shit, bitch, bastard, piss)
    "shit": 2, "bitch": 2, "bastard": 2, "piss": 2,
    # 3 = severe (f-word, n-word, c-word, slurs)
    # ... full list in implementation
}

class ProfanityScanner:
    def __init__(self, min_severity: int = 2):
        self.min_severity = min_severity
        profanity.load_censor_words()

    def scan(self, lyrics: str) -> tuple[int, list[str]]:
        """Scan lyrics and return (max_severity, matched_words)."""
        words = lyrics.lower().split()
        matched = []
        max_severity = 0
        for word in words:
            clean = word.strip(".,!?;:'\"()[]")
            if clean in SEVERITY_MAP:
                matched.append(clean)
                max_severity = max(max_severity, SEVERITY_MAP[clean])

        # Also run better-profanity for leet-speak detection
        # It catches obfuscated variants that plain lookup misses
        if profanity.contains_profanity(lyrics):
            # If better-profanity catches something our map missed,
            # assign moderate severity as default
            if not matched:
                matched = ["[obfuscated]"]
                max_severity = max(max_severity, 2)

        return (max_severity, matched)
```

### Pattern 4: Poll Loop Integration
**What:** Hook ContentChecker into daemon.py's existing track-change detection without blocking.
**When to use:** Main integration point.
**Example:**
```python
# In daemon.py poll_loop(), after track change detection:
if track_id != state.get("last_track_id"):
    # ... existing logging ...

    # Phase 2: Content filtering (only when FSM is on)
    if state.get("family_safe_mode", False):
        device = result.get("device", {})
        device_name = device.get("name", "unknown")
        is_restricted = device.get("is_restricted", False)

        # D-02: Log device info on every track change
        log.info("[DEVICE] name=%r is_restricted=%s", device_name, is_restricted)

        action, reason, severity = await content_checker.check(track)

        # D-09: Log scan result for ALL tracks
        log.info(
            '[SCAN] track=%r artist=%r severity=%d matched=%s action=%s',
            track["name"], track["artists"][0]["name"],
            severity, matched, action,
        )

        if action == "skip":
            # Select skip client based on is_restricted
            client = soco_skip if is_restricted else spotify_skip
            await client.skip(device_name, device.get("id"))

            # D-07: Structured skip log
            log.info(
                '[SKIP] reason=%s track=%r artist=%r',
                reason, track["name"], track["artists"][0]["name"],
            )
```

### Anti-Patterns to Avoid
- **Synchronous SoCo/spotipy calls in async loop:** Both libraries are synchronous. MUST use `loop.run_in_executor()` to avoid blocking the poll loop. Never call `device.next()` or `sp.next_track()` directly in an async context.
- **Caching lyrics in memory only:** Memory cache is lost on container restart. SQLite survives restarts and is negligible overhead.
- **Atomic file writes for state.json:** `os.replace()` raises `EBUSY` on Docker bind-mounted files on Linux. Continue using direct write (Phase 1 established pattern).
- **Scanning all text as one string for profanity:** Song lyrics may have line breaks that join words ("hell\nfire"). Normalize whitespace before scanning.
- **Hardcoding Sonos room names:** Per D-01, Sonos is detected via Spotify's `is_restricted` flag. The device name from Spotify is passed to `soco.discovery.by_name()`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Lyrics fetching | Custom HTTP client for LRCLIB | `lrclibapi` | Handles edge cases, typed responses, maintained wrapper |
| Leet-speak detection | Regex substitution table | `better-profanity` | Already handles p0rn, h4NDjob, b*tCh variants; maintained wordlist |
| Async SQLite | Thread pool + raw sqlite3 | `aiosqlite` | Clean async context manager API, handles connection pooling |
| Sonos UPnP control | Raw UPnP/SOAP calls | `soco` | UPnP is complex; SoCo handles SOAP envelopes, discovery, and transport |
| Spotify playback control | Raw HTTP to Spotify API | `spotipy` (already installed) | Auth token refresh, rate limit handling built in |

**Key insight:** Every external integration in this phase has a well-maintained Python library. The only custom code needed is the severity word mapping (which is project-specific configuration, not infrastructure).

## Common Pitfalls

### Pitfall 1: Missing OAuth Scope for Spotify Skip
**What goes wrong:** `POST /me/player/next` returns 403 Forbidden.
**Why it happens:** Phase 1 only requested `user-read-currently-playing` scope. Skip requires `user-modify-playback-state`.
**How to avoid:** Add `user-modify-playback-state` to the scope string in both `daemon.py` and `setup_auth.py`. User must re-run `make auth` to get a new token with the expanded scope. Delete the cached token first.
**Warning signs:** 403 error from Spotify on first skip attempt.

### Pitfall 2: SoCo Discovery Fails to Find Speaker by Spotify Device Name
**What goes wrong:** `soco.discovery.by_name("Living Room")` returns `None` because the Sonos room name doesn't match the Spotify device name exactly.
**Why it happens:** Spotify may report the device name differently than SoCo sees it (e.g., "Living Room" vs "Living Room (Sonos One)"). Case sensitivity may also differ.
**How to avoid:** Log both names. Implement fuzzy matching or substring matching as a fallback. Consider caching the SoCo device-name-to-IP mapping after first successful discovery.
**Warning signs:** Successful `is_restricted=True` detection but `SocoSkipClient.skip()` throws "speaker not found".

### Pitfall 3: Blocking the Async Event Loop
**What goes wrong:** Poll loop freezes for 2-5 seconds during lyrics fetch or SoCo discovery.
**Why it happens:** `lrclibapi`, `soco`, and `spotipy` are all synchronous libraries. Calling them directly in an async function blocks the event loop.
**How to avoid:** Wrap ALL synchronous library calls in `loop.run_in_executor(None, ...)`. For lyrics fetch, consider whether `lrclibapi` uses `requests` internally (it does) -- must be in executor.
**Warning signs:** Heartbeat logs show gaps during content checks.

### Pitfall 4: LRCLIB Returning Empty Lyrics for Non-Instrumental Tracks
**What goes wrong:** Track exists in LRCLIB but `plainLyrics` is `None` or empty string while `instrumental` is `False`.
**Why it happens:** LRCLIB entries can be incomplete. A track may have synced lyrics but no plain lyrics, or the entry may be a stub.
**How to avoid:** Check both `plainLyrics` and `syncedLyrics`. If both are empty/None and `instrumental` is `False`, treat as "lyrics unavailable" (FILT-05 path).
**Warning signs:** Tracks with known lyrics getting classified as "lyrics_unavailable".

### Pitfall 5: State.json Race Between Makefile and Daemon
**What goes wrong:** `make fsm-on` writes state.json at the same moment the daemon writes it (track ID update), corrupting the file.
**Why it happens:** Two processes writing to the same bind-mounted file with no locking.
**How to avoid:** Makefile targets should use a merge strategy: read current state, update only the `family_safe_mode` key, write back. Alternatively, since the daemon reads state every poll cycle, a brief corruption self-heals on next read (load_state returns defaults on JSONDecodeError). Document this as acceptable given the ~1s poll interval.
**Warning signs:** Occasional `JSONDecodeError` in daemon logs after toggling FSM.

### Pitfall 6: SoCo Discovery Timeout on Large Networks
**What goes wrong:** `soco.discovery.by_name()` takes 5+ seconds, blocking the event loop (even in executor, it delays the skip).
**Why it happens:** SoCo uses multicast SSDP discovery which has a default timeout. On networks with many devices, this can be slow.
**How to avoid:** After first successful discovery, cache the speaker IP. On subsequent skips, try the cached IP first. SoCo allows direct instantiation: `soco.SoCo("192.168.1.x")` bypasses discovery entirely.
**Warning signs:** Skip latency > 3 seconds on Sonos.

## Code Examples

### LRCLIB Lyrics Fetch (via lrclibapi)
```python
# Source: lrclibapi 0.3.1 docs / GitHub
from lrclib import LrcLibAPI

api = LrcLibAPI(user_agent="SpotifyFamilySafe/1.0")

# Fetch lyrics by track name and artist
result = api.get_lyrics(
    track_name="Shape of You",
    artist_name="Ed Sheeran",
    album_name="Divide",   # optional, improves matching
    duration=234,           # optional, in seconds
)

# Response object fields:
# result.id            -> int
# result.track_name    -> str
# result.artist_name   -> str
# result.instrumental  -> bool
# result.plain_lyrics  -> str | None
# result.synced_lyrics -> str | None

if result.instrumental:
    print("Instrumental track -- allow")
elif result.plain_lyrics:
    print(f"Lyrics: {result.plain_lyrics[:100]}...")
else:
    print("No lyrics available -- ambiguous, allow")
```

### SoCo Speaker Discovery and Skip
```python
# Source: SoCo 0.30.14 docs
import soco
from soco.discovery import by_name

# Find speaker by room name (matches Spotify device name)
speaker = by_name("Living Room")
if speaker:
    speaker.next()  # Skip to next track
    # speaker.player_name -> "Living Room"
    # speaker.ip_address  -> "192.168.1.42"

# Direct connection (cached IP, bypasses discovery):
speaker = soco.SoCo("192.168.1.42")
speaker.next()

# Discovery returns None if speaker not found
# next() raises soco.exceptions.SoCoUPnPException on failure
```

### Spotify Skip via Spotipy
```python
# Source: Spotipy 2.26.0 / Spotify Web API docs
import spotipy

# Requires scope: "user-modify-playback-state"
sp.next_track(device_id=None)  # Skips on active device
sp.next_track(device_id="abc123")  # Skip on specific device

# Returns None on success (204 No Content)
# Raises SpotifyException on 403/429/etc.
```

### SQLite Lyrics Cache Schema
```python
# Recommended schema for lyrics cache
import aiosqlite

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS lyrics_cache (
    spotify_track_id TEXT PRIMARY KEY,
    track_name       TEXT NOT NULL,
    artist_name      TEXT NOT NULL,
    instrumental     BOOLEAN NOT NULL DEFAULT 0,
    plain_lyrics     TEXT,
    severity         INTEGER,
    matched_words    TEXT,
    fetched_at       REAL NOT NULL,
    CHECK (severity >= 0 AND severity <= 3)
);
CREATE INDEX IF NOT EXISTS idx_fetched_at ON lyrics_cache(fetched_at);
"""

async def get_cached(db: aiosqlite.Connection, track_id: str):
    async with db.execute(
        "SELECT * FROM lyrics_cache WHERE spotify_track_id = ?",
        (track_id,)
    ) as cursor:
        return await cursor.fetchone()

async def cache_lyrics(db: aiosqlite.Connection, track_id: str, **kwargs):
    await db.execute(
        """INSERT OR REPLACE INTO lyrics_cache
           (spotify_track_id, track_name, artist_name, instrumental,
            plain_lyrics, severity, matched_words, fetched_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (track_id, kwargs["track_name"], kwargs["artist_name"],
         kwargs["instrumental"], kwargs.get("plain_lyrics"),
         kwargs.get("severity"), kwargs.get("matched_words"),
         time.time())
    )
    await db.commit()
```

### Makefile FSM Toggle
```makefile
# Merge family_safe_mode into existing state.json (don't overwrite other keys)
fsm-on:
	@python3 -c "import json; s=json.load(open('state.json')); s['family_safe_mode']=True; json.dump(s, open('state.json','w'))"
	@echo "Family Safe Mode: ON"

fsm-off:
	@python3 -c "import json; s=json.load(open('state.json')); s['family_safe_mode']=False; json.dump(s, open('state.json','w'))"
	@echo "Family Safe Mode: OFF"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Musixmatch for lyrics | LRCLIB (free, no API key) | Aug 2025 (Musixmatch killed free tier) | LRCLIB is the only viable free lyrics source |
| Spotify audio features API | N/A (deprecated) | Late 2024 | Cannot use audio analysis for content detection; lyrics-only approach required |
| SoCo 0.29.x | SoCo 0.30.14 | Dec 2025 | Latest stable; no breaking changes from 0.29 |
| profanity-check (abandoned) | alt-profanity-check 1.8.0 | Jan 2026 | Drop-in replacement; maintained fork. But we recommend better-profanity instead for leet-speak. |

**Deprecated/outdated:**
- `profanity-check` original: No longer maintained, use `alt-profanity-check` if ML approach desired
- Spotify audio features API: Returns 403 for new apps since late 2024

## Open Questions

1. **Spotify device name vs SoCo room name matching**
   - What we know: SoCo `by_name()` uses the Sonos room name. Spotify reports a device name.
   - What's unclear: Whether these always match exactly. Spotify may append model info or differ in casing.
   - Recommendation: Implement case-insensitive substring matching. Log both names for debugging (D-02). Cache successful IP mappings. If all matching fails, fall back to Spotify API skip (which may fail on `is_restricted`, but at least logs the failure).

2. **LRCLIB response for not-found tracks**
   - What we know: API likely returns 404. Python wrapper may raise an exception or return None.
   - What's unclear: Exact behavior of `lrclibapi` on 404 -- does it raise, return None, or return an object with empty fields?
   - Recommendation: Test during implementation. Wrap in try/except and treat any failure as "lyrics unavailable" (FILT-05).

3. **better-profanity word extraction**
   - What we know: `contains_profanity()` returns boolean only. No built-in method to extract matched words.
   - What's unclear: Whether we need to fork/extend the library or if the custom severity map lookup suffices.
   - Recommendation: The custom severity word map (Pattern 3) handles word extraction directly. `better-profanity` is only needed as a second pass for leet-speak variants. Log "[obfuscated]" for leet-speak catches.

4. **OAuth scope migration**
   - What we know: Current token has `user-read-currently-playing` only. Need to add `user-modify-playback-state`.
   - What's unclear: Whether adding the scope requires just re-auth or also updating the Spotify Dashboard app settings.
   - Recommendation: Scopes are requested at auth time, not registered in Dashboard. Delete cached token, update scope in code, re-run `make auth`. Document this in plan as a required manual step.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Docker | Container runtime | Yes | (host) | -- |
| Python 3.12 | All code | Yes | 3.12-slim (Dockerfile) | -- |
| Network: host mode | SoCo UPnP multicast | Yes | docker-compose.yml | -- |
| LRCLIB API (lrclib.net) | Lyrics fetch | Yes (external) | Public API | Treat as "lyrics unavailable" on timeout |
| Spotify API | Skip endpoint | Yes (external) | Web API | -- |
| Sonos speaker on LAN | SoCo skip | Conditional | UPnP | Spotify API skip (may fail on restricted device) |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:**
- If LRCLIB is down: treat all non-explicit tracks as "lyrics unavailable" (FILT-05 path, no skip).
- If Sonos speaker not discoverable: fall back to Spotify API skip attempt, log warning.

## Sources

### Primary (HIGH confidence)
- Spotify Web API docs -- skip endpoint, scopes, response codes: https://developer.spotify.com/documentation/web-api/reference/skip-users-playback-to-next-track
- SoCo 0.30.14 GitHub + PyPI -- discovery, next(), version: https://github.com/SoCo/SoCo
- better-profanity 0.7.0 PyPI -- API, leet-speak support: https://pypi.org/project/better-profanity/
- alt-profanity-check 1.8.0 PyPI -- probability scoring: https://pypi.org/project/alt-profanity-check/
- LRCLIB API docs -- endpoints, no rate limits, no auth: https://lrclib.net/docs
- lrclibapi 0.3.1 GitHub -- Python wrapper: https://github.com/Dr-Blank/lrclibapi
- aiosqlite 0.22.1 -- async SQLite: PyPI registry

### Secondary (MEDIUM confidence)
- LRCLIB API response schema (instrumental, plainLyrics, syncedLyrics) -- reconstructed from JS wrapper docs and multiple sources: https://lrclib.js.org/classes/Client.html
- SoCo `by_name()` discovery -- search results confirmed existence but official docs returned 403: https://docs.python-soco.com/en/latest/api/soco.discovery.html
- LRCLIB User-Agent header -- "encouraged but not required" per GitHub issue: https://github.com/osdlyrics/osdlyrics/issues/146

### Tertiary (LOW confidence)
- LRCLIB 404 behavior for not-found tracks -- inferred from standard REST patterns, not verified against actual API. Needs testing during implementation.
- Spotify device name matching SoCo room name -- assumption based on typical Sonos setups. Not verified with actual device data.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries verified on PyPI with current versions, APIs documented
- Architecture: HIGH - Patterns follow established Phase 1 conventions, CONTEXT.md decisions are clear
- Pitfalls: HIGH - OAuth scope issue is well-documented; async blocking is a known pattern; SoCo discovery is the main risk area
- Profanity severity mapping: MEDIUM - Custom solution required since no Python library has built-in severity tiers matching the CONTEXT.md description. Approach is sound but needs tuning of the word list.

**Research date:** 2026-04-01
**Valid until:** 2026-05-01 (stable domain; libraries are mature)
