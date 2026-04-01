# Project Research Summary

**Project:** spotify-sentiment — Family-Safe Spotify Filter Daemon
**Domain:** Music playback monitoring, content filtering, home automation
**Researched:** 2026-04-01
**Confidence:** HIGH (core API facts verified); MEDIUM (Sonos skip path, Signal reliability)

---

## Executive Summary

This is a background daemon for a home Mac server that monitors Spotify playback in real time, evaluates each new track against family-safe rules, and skips violating songs automatically. Research across four domains (Spotify/Sonos integration, lyrics filtering, Signal notifications, and system architecture) converges on a clear, buildable design with one non-obvious architectural forcing function: Spotify's Web API cannot issue skip commands to Sonos speakers. Sonos devices appear as `is_restricted: true` and any write call (skip, pause, seek) is silently rejected. The hybrid workaround — read track metadata from the Spotify API, skip via SoCo UPnP locally — is validated in production by the Home Assistant community and is the correct approach for this project.

The recommended stack is Python 3.11+ with `spotipy` (v2.26+, actively maintained, March 2026 release) as the Spotify client. Both Node.js Spotify libraries — `spotify-web-api-node` and `@spotify/web-api-ts-sdk` — are confirmed unmaintained as of 2026. Lyrics come from LRCLIB (free, no API key, no rate limits, ~97.5% hit rate on well-tagged libraries); Musixmatch's free tier was terminated August 2025 and is no longer a viable option. Signal notifications are delivered via `bbernhard/signal-cli-rest-api` running in Docker with `json-rpc` mode, which exposes both an HTTP POST endpoint for sending and a WebSocket for receiving user replies — covering the interactive "allow or skip?" confirmation pattern. The daemon runs as a macOS LaunchAgent with `KeepAlive = true`.

The three principal risks are: (1) Sonos skip path depends on LAN UPnP reachability and SoCo's `DIDLMetadataError` bug when Spotify Direct Connect is active (mitigation: use Spotify API for all reads, SoCo only for the skip call); (2) LRCLIB is run by a single maintainer with no SLA — maintain a periodic SQLite dump as local fallback; (3) Signal's unofficial protocol can break on Signal server updates, typically repaired within days but with no guarantee. None of these are blockers; all have documented mitigations.

---

## Key Findings

### Recommended Stack

Python with `spotipy` is the only defensible language/library choice in 2026. The Spotify TypeScript SDK last published 2 years ago; `spotify-web-api-node` is explicitly in maintenance mode. `spotipy` v2.26.0 (March 2026) is the most actively maintained Spotify client across all languages, handles OAuth token refresh automatically via `CacheFileHandler`, and integrates with asyncio without extra wrappers. SoCo (Python UPnP for Sonos) makes Python the clear winner for this dual-API requirement.

**Core technologies:**
- **Python 3.11+**: Language — only language with maintained libraries for both Spotify and Sonos
- **spotipy 2.26+**: Spotify API client — handles OAuth, token refresh, all playback endpoints
- **SoCo**: Sonos UPnP control — required for skip on `is_restricted` Sonos devices; local LAN, no cloud dependency
- **LRCLIB**: Lyrics API — free, no API key, no rate limits, returns `plainLyrics` + `instrumental` flag
- **obscenity** (npm) / Python equivalent: Profanity scanner — obfuscation-aware, word-boundary detection, avoids false positives on substrings
- **SQLite**: Lyrics cache — zero operational overhead, Spotify track ID as cache key, indefinite TTL
- **signal-cli-rest-api** (Docker, `json-rpc` mode): Signal notifications + interactive reply via WebSocket
- **macOS LaunchAgent (launchd)**: Daemon lifecycle — native, no Node.js/pm2 dependency, `KeepAlive = true`

### Expected Features

**Must have (table stakes):**
- Detect track changes via Spotify `GET /me/player` polling (1-second interval, adaptive near track end)
- Skip `explicit: true` tracks immediately — no lyrics lookup required
- Skip tracks matching profanity scan of LRCLIB lyrics (`obscenity` library)
- Dual skip path: Spotify API for standard devices, SoCo `speaker.group.coordinator.next()` for Sonos
- OAuth one-time setup script — browser redirect, token persisted to `~/.spotify_token_cache`
- Signal notification on every skip (what was skipped, why)
- Family Safe Mode toggle — readable from `state.json` on every poll cycle without restart
- Consecutive skip guard (cap at ~5) to prevent infinite-skip loops on blocked playlists

**Should have (differentiators):**
- Interactive Signal confirmation for ambiguous tracks — send "Allow or Skip?" prompt, await reply with 30s timeout
- SQLite lyrics cache — avoids re-fetching LRCLIB on repeated plays, Spotify track ID as key
- Configurable artist and keyword blocklist beyond the explicit flag
- Graceful handling of LRCLIB misses — log as "lyrics unavailable," allow play, retry after 24h for new releases
- Pre-fetch queue for upcoming track logging/analytics (cannot prevent play, but enables lookahead)

**Defer (v2+):**
- Multilingual profanity detection (non-English songs fall through to allow in v1)
- Sentiment analysis / LLM-based euphemism detection for drug/violence/sexual themes without profanity
- Companion web UI or status dashboard
- ntfy.sh as Signal fallback (architecture supports swap; build only if Signal proves unreliable)

### Architecture Approach

Single Python process running as a macOS LaunchAgent. The main asyncio loop polls `GET /me/player` on an adaptive interval (1s default, tighter near track end, 30s when idle). On track change, the `ContentChecker` evaluates the track against an ordered rule set: explicit flag first (fast, no I/O), then LRCLIB lyrics + profanity scan (cache-first). Skip is dispatched via a two-path branch on `device.is_restricted`. State persists to `state.json` via atomic write (tmp + `os.replace`) to survive crashes. Signal runs as a sidecar Docker container; the daemon communicates with it via localhost HTTP (send) and WebSocket (receive).

**Major components:**
1. **`daemon.py`** — entry point, asyncio event loop, SIGTERM/SIGINT handler, main poll loop
2. **`SpotifyClient`** — wraps spotipy; all Spotify HTTP calls, token refresh, 429 backoff
3. **`SonosClient`** — wraps SoCo; discovery, group coordinator resolution, `next()` call
4. **`ContentChecker`** — ordered rule evaluation returning `SKIP/ALLOW + reason`; reads config from state
5. **`LyricsService`** — LRCLIB fetch, SQLite cache read/write, miss tracking, re-fetch scheduling
6. **`SignalNotifier`** — HTTP POST to signal-cli-rest-api for send; WebSocket receive loop for replies; pending-confirmation map with timeout
7. **`StateStore`** — atomic JSON read/write for `state.json`; in-memory cache; toggle family safe mode
8. **`launchd plist`** — `KeepAlive`, `ThrottleInterval=5`, log redirection, env vars from dotenv file

### Critical Pitfalls

1. **Sonos `is_restricted` silently rejects Spotify skip calls** — the Spotify API returns track metadata correctly when Sonos is active, but `POST /me/player/next` fails silently (no error, no skip). Always check `device.is_restricted` before choosing skip path. Use SoCo `speaker.group.coordinator.next()` for Sonos, Spotify API for everything else.

2. **OAuth requires a one-time interactive browser step** — the Authorization Code Flow mandates a browser redirect to obtain the initial `code`. For a headless daemon, this must be a documented, manual setup step (`python setup_auth.py` run once with a browser available). The implicit grant flow was deprecated November 2025. PKCE rotates refresh tokens on every use (fragile for a daemon). Classic Authorization Code + `client_secret` is correct here.

3. **SoCo `DIDLMetadataError` on Spotify Direct Connect** — when Spotify is playing via Spotify Connect (not Sonos queue), SoCo's `avTransport` event subscription throws `DIDLMetadataError` about a missing `restricted` attribute. Do not use SoCo's event subscription for track detection. Use Spotify API polling for all reads; call SoCo only for the skip action.

4. **LRCLIB is a single-maintainer service with no SLA** — ~97.5% hit rate on well-tagged libraries, but the service can disappear. Mitigation: download the LRCLIB SQLite database dump periodically as a local fallback. Do not block playback on LRCLIB unavailability — allow play and log the miss.

5. **Spotify `explicit: false` does not mean clean** — the flag is label/distributor-applied and under-flags. Older catalog, international tracks, and DJ sets frequently lack explicit labels despite containing profanity. The explicit flag is a fast Tier 1 filter only; the LRCLIB + obscenity scan is the primary quality gate.

6. **Rapid track ID echo after skip** — after calling `next_track()` or `soco.next()`, the Spotify API may return the old track for 1–3 seconds. Implement a "recently skipped" set to avoid double-skip on the same track ID.

7. **LaunchDaemon vs. LaunchAgent** — placing the plist in `/Library/LaunchDaemons/` runs as root before user login. The Spotify OAuth token is stored in the user's home directory and is inaccessible to root. Use `~/Library/LaunchAgents/` exclusively.

---

## Implications for Roadmap

Based on the combined research, a 4-phase structure is recommended. Phases 1 and 2 are strictly sequential (each is a dependency for the next). Phases 3 and 4 can be planned independently once Phase 2 is stable.

### Phase 1: Core Daemon and Spotify Integration

**Rationale:** Everything depends on a working poll loop with reliable Spotify authentication. OAuth setup, token refresh, and the basic track-change detection loop are the skeleton that all other features attach to. No filtering, no notifications — prove the plumbing works first.

**Delivers:** Running daemon that detects track changes and logs them; OAuth setup script; launchd plist; `state.json` persistence; graceful shutdown; 429 backoff.

**Addresses:** Track change detection, adaptive polling, token refresh, family safe mode toggle scaffold.

**Avoids:** LaunchDaemon vs. LaunchAgent mistake; hardcoded credentials in plist; implicit grant flow.

**Research flag:** Standard patterns. OAuth Authorization Code flow and spotipy `CacheFileHandler` are thoroughly documented. No additional research needed.

---

### Phase 2: Content Filtering and Auto-Skip

**Rationale:** The core product value. Builds on Phase 1's poll loop. Introduces the two-path skip architecture (Spotify API vs. SoCo for Sonos) and the three-tier content evaluation (explicit flag → LRCLIB lyrics → obscenity scan). SQLite lyrics cache included here because it is a prerequisite for reliable skip timing.

**Delivers:** Functional family-safe filter. Tier 1 explicit flag skip (instant). Tier 2 LRCLIB lyrics fetch + profanity scan. SQLite lyrics cache. Dual skip path (Spotify API + SoCo). Consecutive skip guard. Skip logging.

**Uses:** spotipy `next_track()`, SoCo `speaker.group.coordinator.next()`, LRCLIB REST API, `obscenity` profanity library, SQLite.

**Implements:** `ContentChecker`, `LyricsService`, `SonosClient`.

**Avoids:** SoCo avTransport event subscription bug (do not subscribe — use only for skip action). Double-skip debounce on Spotify API lag. Blocking on LRCLIB misses.

**Research flag:** Sonos skip path needs careful integration testing. SoCo speaker discovery and group coordinator resolution should be prototyped early. The `DIDLMetadataError` bug is confirmed but only manifests in the subscribe path — using SoCo for skip-only avoids it.

---

### Phase 3: Signal Notifications and Interactive Confirmations

**Rationale:** Adds human-in-the-loop interaction. Signal requires Docker infrastructure (signal-cli-rest-api) and a one-time device linking step. Decoupled from filtering logic — the `ContentChecker` simply emits a decision; `SignalNotifier` is a listener. The interactive confirmation pattern (ambiguous track → ask user → await reply) requires the `pending-confirmation` map with timeout.

**Delivers:** Skip notifications via Signal DM. Interactive "Allow or Skip?" prompt for ambiguous tracks. 30-second reply timeout with safe default (skip). WebSocket receive loop with reconnect on close.

**Uses:** `bbernhard/signal-cli-rest-api` (Docker, `json-rpc` mode), `websockets` Python library, `httpx` for send.

**Implements:** `SignalNotifier`, pending-confirmation map.

**Avoids:** Using `normal` mode (polling receive, 3–10s latency). Using `AUTO_RECEIVE_SCHEDULE` alongside WebSocket receive (they conflict). Burst-sending messages (space >= 2 seconds). Skipping persistent volume mount for signal-cli config.

**Research flag:** Signal setup (Docker, QR code linking) is well-documented by `bbernhard/signal-cli-rest-api`. However, Signal's unofficial protocol has a history of breaking on server updates — build with reconnect logic and test thoroughly before relying on it. ntfy.sh is a documented fallback if Signal proves unreliable.

---

### Phase 4: Hardening and Configuration UX

**Rationale:** Operational robustness for daily family use. Adds configurable blocklists, artist/keyword rules, LRCLIB database dump as local fallback, miss-rate monitoring, and install documentation. Not MVP but necessary for handing off to family members who are not developers.

**Delivers:** Configurable artist/keyword blocklist (beyond explicit flag). LRCLIB SQLite dump scheduled download for offline fallback. LRCLIB miss-rate logging and re-fetch scheduling for new releases. Install/setup documentation (OAuth one-time step prominently documented). Token file `chmod 600` enforcement. Credential storage via macOS Keychain instead of plist env vars.

**Avoids:** Hardcoding credentials; world-readable token cache; no documentation for non-technical family members.

**Research flag:** Standard patterns. No additional research needed for this phase.

---

### Phase 5 (v2): Sentiment Analysis for Adult Themes

**Rationale:** Wordlist-based profanity scanning misses euphemisms, coded language, and themes (depression, drug use, sexual content) expressed without profanity. An LLM-based scan covers these cases. Deferred because: (a) it adds per-song API cost or local inference latency; (b) it requires careful prompt design; (c) Phases 1–4 deliver a working product that handles the most obvious violations. Build only after the v1 system is stable in daily use.

**Delivers:** LLM-based theme classification (structured JSON output). Permanent cache of LLM decisions (sentiment does not expire). Handling for non-English profanity (multilingual wordlists or LLM prompt).

**Research flag:** Needs research. LLM provider selection (local Ollama vs. OpenAI/Anthropic API), prompt design, and cost modeling require a dedicated research spike before roadmap phase is defined.

---

### Phase Ordering Rationale

- Phase 1 before Phase 2: No content filtering without a working poll loop and authenticated Spotify client.
- Phase 2 before Phase 3: Skip notifications are only meaningful once filtering is functional. Signal complexity should not slow down the core filter.
- Phase 3 before Phase 4: The interactive confirmation pattern in Phase 3 is a feature; Phase 4 hardens the system around all prior features.
- Phase 5 deferred: v1 delivers clear value without LLM complexity. Sentiment analysis is a quality improvement, not a baseline requirement.

### Research Flags

**Phases needing deeper research during planning:**
- **Phase 5 (Sentiment Analysis):** LLM provider selection, prompt design, cost model, and caching strategy need a dedicated research spike. Do not plan implementation milestones without it.
- **Phase 2 (Sonos integration):** SoCo speaker discovery and group coordinator resolution should be validated in a prototype against real Sonos hardware before committing to implementation milestones. The `is_restricted` flag detection logic needs testing with the actual device name.

**Phases with standard patterns (skip research-phase):**
- **Phase 1:** Spotipy OAuth + launchd LaunchAgent are thoroughly documented. Patterns are clear from official docs.
- **Phase 3:** signal-cli-rest-api setup is well-documented. json-rpc mode + WebSocket pattern is confirmed working by Home Assistant integration at scale.
- **Phase 4:** All items are configuration and hardening work on already-researched components.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Spotify API (polling, skip, scopes, rate limits) | HIGH | Official Spotify docs; confirmed against February 2026 changelog |
| Sonos `is_restricted` constraint | HIGH | Confirmed by multiple community threads 2019–2025; GitHub issue unresolved |
| SoCo skip workaround | MEDIUM | Works in practice; `DIDLMetadataError` bug is real but avoidable with hybrid read/skip split |
| LRCLIB as primary lyrics source | HIGH | No API key, documented no-rate-limit policy, ~97.5% hit rate confirmed by case study |
| Musixmatch free tier dead | HIGH | Terminated August 25, 2025; confirmed from multiple affected tool maintainers |
| Obscenity for profanity scanning | HIGH | Actively maintained, TypeScript-native; Python equivalent exists; word-boundary detection confirmed |
| spotipy as primary Spotify library | HIGH | v2.26.0 released March 2026; Node.js alternatives confirmed unmaintained |
| signal-cli-rest-api integration | MEDIUM | Core patterns HIGH; Signal unofficial protocol has breakage history |
| OAuth one-time setup requirement | HIGH | Authorization Code Flow is the only viable option for a daemon post-November 2025 |
| 1-second polling safety | MEDIUM | Community consensus at ~30/180 requests per 30s window; Spotify does not publish the limit |

**Overall confidence:** HIGH for Phase 1–4 implementation decisions. MEDIUM for Sonos skip path (needs hardware validation) and Signal reliability (protocol stability risk).

### Gaps to Address

- **Sonos speaker name / group configuration:** The `is_restricted` detection is reliable, but SoCo speaker discovery requires knowing room names. This is user-specific configuration that must be surfaced in the install/setup docs and potentially as a runtime config option.

- **LRCLIB coverage for user's actual library:** The ~97.5% hit rate is from a personal well-tagged library study. The actual miss rate for this family's listening history is unknown until runtime. Build miss-rate logging in Phase 2 and review after 2–4 weeks of operation.

- **Signal account setup path:** The research recommends linking as a secondary device (QR code) rather than registering a new number. This assumes the owner already has Signal. If they do not, the dedicated bot number path requires a VoIP number and has captcha friction. Validate account setup method before Phase 3.

- **Profanity library language:** `obscenity` is English-only. If the family's playlists include significant non-English content (Spanish, French, etc.), the miss rate for non-English profanity will be high. Not a blocker for v1 but should be measured and reported.

- **February 2026 Developer Mode: 5-user cap:** Spotify reduced the app user cap from 25 to 5 in February 2026. For a family use case (2–5 family members listening), this is likely fine. Validate headcount before development begins; if more than 5 users need independent filtering, extended quota mode application will be required.

---

## Sources

### Primary (HIGH confidence)

- https://developer.spotify.com/documentation/web-api/reference/get-information-about-the-users-current-playback — GET /me/player endpoint; device fields including `is_restricted`
- https://developer.spotify.com/documentation/web-api/reference/skip-users-playback-to-next-track — Skip endpoint; Premium requirement
- https://developer.spotify.com/documentation/web-api/concepts/scopes — OAuth scopes
- https://developer.spotify.com/documentation/web-api/concepts/rate-limits — Rate limit window
- https://developer.spotify.com/documentation/web-api/tutorials/refreshing-tokens — Token refresh; daemon flow
- https://developer.spotify.com/documentation/web-api/references/changes/february-2026 — February 2026 API changes; 5-user cap
- https://developer.spotify.com/blog/2026-02-06-update-on-developer-access-and-platform-security — Developer mode Premium requirement
- https://developer.spotify.com/blog/2025-10-14-reminder-oauth-migration-27-nov-2025 — Implicit grant deprecation; localhost exemption
- https://github.com/spotipy-dev/spotipy — spotipy v2.26.0 (March 2026)
- https://lrclib.net/ — LRCLIB API; no-rate-limit policy; database dump availability
- https://github.com/bbernhard/signal-cli-rest-api — signal-cli-rest-api; json-rpc mode; WebSocket receive
- https://github.com/SoCo/SoCo — SoCo Python library; `next()`, `group.coordinator`

### Secondary (MEDIUM confidence)

- https://github.com/spotify/web-api/issues/1337 — Sonos `is_restricted` confirmed by community (2019–2025)
- https://community.spotify.com/t5/Spotify-for-Developers/Support-for-restricted-devices-specifically-sonos-speakers/td-p/6457650 — Sonos restricted; no official workaround
- https://github.com/SoCo/SoCo/issues/453 — `DIDLMetadataError` on Spotify Direct Connect via avTransport
- https://github.com/home-assistant/core/pull/136461 — Adaptive polling pattern; `remaining_ms + 1s`
- https://news.ycombinator.com/item?id=39480390 — LRCLIB community discussion; 97.5% hit rate
- https://www.blog.brightcoding.dev/2025/12/13/the-ultimate-guide-to-automating-synchronized-lyrics-for-your-music-library-2025/ — LRCLIB practical guide 2025
- https://github.com/AsamK/signal-cli/issues/1823 — Signal-cli rate limit issues
- https://bbernhard.github.io/signal-cli-rest-api/ — signal-cli-rest-api API reference

### Tertiary (LOW confidence — confirms but not authoritative)

- https://github.com/jo3-l/obscenity — obscenity profanity library; obfuscation-aware; word-boundary detection
- https://publicapis.io/musixmatch-api — Musixmatch free tier termination (August 2025) via affected tool maintainers
- https://github.com/thelinmichael/spotify-web-api-node — spotify-web-api-node maintenance mode (last release 4.0.0)
- https://github.com/spotify/spotify-web-api-ts-sdk — Official TypeScript SDK last published 2+ years ago (confirmed stale)
- https://docs.sonos.com/docs/control — Sonos Cloud Control API (evaluated and ruled out in favor of SoCo)

---

*Research completed: 2026-04-01*
*Ready for roadmap: yes*
