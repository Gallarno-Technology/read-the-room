# Requirements: Spotify Family Safe Mode

**Defined:** 2026-04-01
**Core Value:** Songs that violate family-safe rules are skipped automatically before children hear them — with zero manual effort when Family Safe Mode is on.

## v1 Requirements

### Daemon & Spotify Integration

- [ ] **CORE-01**: Service polls Spotify playback state every ~1 second and detects when a new track begins
- [x] **CORE-02**: Service authenticates with Spotify via OAuth (one-time browser setup, then headless token refresh)
- [x] **CORE-03**: Service runs as a macOS LaunchAgent and auto-restarts on crash
- [ ] **CORE-04**: Service reads the `explicit` flag from the currently playing Spotify track

### Content Filtering

- [ ] **FILT-01**: Tracks marked `explicit: true` by Spotify are immediately flagged for auto-skip
- [ ] **FILT-02**: For non-explicit tracks, lyrics are fetched from LRCLIB using the track title and artist
- [ ] **FILT-03**: Lyrics are scanned for profanity using the `obscenity` library (handles obfuscation and leet-speak)
- [ ] **FILT-04**: Instrumental tracks (LRCLIB `instrumental: true` or no lyrics found) are allowed without scanning
- [ ] **FILT-05**: Tracks with lyrics unavailable in LRCLIB are treated as ambiguous (not auto-skipped)
- [ ] **FILT-06**: Fetched lyrics are cached locally (SQLite, keyed by track ID) to avoid repeat API calls

### Skip Execution

- [ ] **SKIP-01**: Tracks playing on Sonos speakers are skipped via SoCo (Python, local UPnP — Spotify API skip fails on Sonos `is_restricted` devices)
- [ ] **SKIP-02**: Tracks playing on non-Sonos devices are skipped via Spotify API (`POST /me/player/next`)
- [ ] **SKIP-03**: The service detects whether the active playback device is a Sonos speaker and routes skip accordingly

### Family Safe Mode

- [ ] **FSM-01**: Family Safe Mode can be toggled on/off (persisted in a local state file)
- [ ] **FSM-02**: Filtering and skipping only occurs when Family Safe Mode is active
- [ ] **FSM-03**: After 5 consecutive skips, a Signal notification prompts the user to switch playlist or radio

### Signal Notifications

- [ ] **SIG-01**: A Signal notification is sent whenever a track is auto-skipped (includes track name, artist, and reason)
- [ ] **SIG-02**: For ambiguous tracks (lyrics unavailable, borderline profanity), a Signal notification asks the user to allow or skip — with a 30-second timeout defaulting to skip
- [ ] **SIG-03**: The user can reply "allow" or "skip" to the Signal prompt and the service acts on the reply in real-time
- [ ] **SIG-04**: Signal integration uses signal-cli-rest-api (Docker, json-rpc/WebSocket mode)

## v2 Requirements

### Sentiment Analysis

- **SENT-01**: Lyrics are analyzed for adult themes: depression, suicide, drug use, and suggestive/sexual content
- **SENT-02**: Theme detection uses an LLM API with structured output (handles euphemism and implicit references)
- **SENT-03**: Theme sensitivity levels are configurable per category

### Sonos Auto-Detection

- **SONO-01**: Family Safe Mode automatically activates when Spotify playback switches to a Sonos speaker
- **SONO-02**: Family Safe Mode automatically deactivates when playback moves to phone/headphones

### Apple Music Support

- **AMUS-01**: Service supports Apple Music playback monitoring alongside Spotify
- **AMUS-02**: Skip and filtering logic is abstracted behind a common playback interface

## Out of Scope

| Feature | Reason |
|---------|--------|
| Web dashboard or mobile app | Signal bot handles all interaction for v1; no separate UI needed |
| Multi-user / per-child profiles | Single household, single user; added complexity not warranted for v1 |
| Non-English profanity detection | Gaps in v1 tooling; defer to v2 with language detection |
| Musixmatch API | Free tier terminated August 2025; use LRCLIB instead |
| Spotify audio features API | Deprecated late 2024, returns 403 for new apps |
| Cloud deployment | Home server is free, private, and sufficient; cloud adds cost and complexity |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| CORE-01 | Phase 1 | Pending |
| CORE-02 | Phase 1 | Complete |
| CORE-03 | Phase 1 | Complete |
| CORE-04 | Phase 1 | Pending |
| FILT-01 | Phase 2 | Pending |
| FILT-02 | Phase 2 | Pending |
| FILT-03 | Phase 2 | Pending |
| FILT-04 | Phase 2 | Pending |
| FILT-05 | Phase 2 | Pending |
| FILT-06 | Phase 2 | Pending |
| SKIP-01 | Phase 2 | Pending |
| SKIP-02 | Phase 2 | Pending |
| SKIP-03 | Phase 2 | Pending |
| FSM-01 | Phase 2 | Pending |
| FSM-02 | Phase 2 | Pending |
| FSM-03 | Phase 3 | Pending |
| SIG-01 | Phase 3 | Pending |
| SIG-02 | Phase 3 | Pending |
| SIG-03 | Phase 3 | Pending |
| SIG-04 | Phase 3 | Pending |

**Coverage:**
- v1 requirements: 20 total
- Mapped to phases: 20
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-01*
*Last updated: 2026-04-01 after initial definition*
