# Spotify Web API + Sonos Integration Research

**Domain:** Family-safe Spotify playback monitoring and auto-skip service
**Researched:** 2026-04-01
**Overall confidence:** HIGH (playback API patterns), MEDIUM (Sonos skip workarounds)

---

## 1. Spotify Web API: Playback State Endpoints

### Primary Endpoint: Get Playback State

```
GET https://api.spotify.com/v1/me/player
```

**Required scope:** `user-read-playback-state`

**Returns:**
- `device` object: `id`, `name`, `type` (computer/smartphone/speaker), `is_active`, `is_restricted`, `volume_percent`
- `is_playing` (boolean)
- `progress_ms` (current position in ms)
- `timestamp` (unix ms of last state change)
- `item` — full Track or Episode object including:
  - `id`, `name`, `uri` (`spotify:track:...`)
  - `explicit` (boolean — `true` = has explicit lyrics, `false` = clean OR unknown)
  - `is_local` (boolean — local file with no Spotify metadata)
  - `type` (`"track"` or `"episode"`)
  - `duration_ms`
  - `restrictions` object (present when content is restricted)
- `context` — playlist/album/artist the track is playing from
- `actions` — which controls are currently available

**HTTP responses:**
- `200 OK` — playback active, body contains state
- `204 No Content` — no active playback, no track playing, or private session is on
- `401` — token expired
- `429` — rate limited (check `Retry-After` header)

**Source:** https://developer.spotify.com/documentation/web-api/reference/get-information-about-the-users-current-playback

### Secondary Endpoint: Get Currently Playing Track

```
GET https://api.spotify.com/v1/me/player/currently-playing
```

**Required scope:** `user-read-currently-playing`

This is a lighter endpoint focused on the current item. It also returns device information. For this service, `GET /me/player` is preferred because it also returns `progress_ms` and `duration_ms`, which are needed for the smart polling interval calculation.

### No Webhooks / No Push Updates

Spotify provides no webhook or push notification mechanism for playback state changes. The GitHub issue requesting real-time player state updates (issue #492) has been open for years with no resolution. Polling is the only option.

**Source:** https://github.com/spotify/web-api/issues/492

---

## 2. Spotify Web API: Skip to Next Track

```
POST https://api.spotify.com/v1/me/player/next
```

**Required scope:** `user-modify-playback-state`

**Optional query parameter:** `device_id` — target device. If omitted, targets the currently active device.

**Response:** `204 No Content` on success.

**Prerequisites:**
- User must have Spotify Premium (free accounts get 403)
- Device must not be `is_restricted = true` (see Sonos section below)

**Source:** https://developer.spotify.com/documentation/web-api/reference/skip-users-playback-to-next-track

---

## 3. Rate Limits

Spotify does not publish a specific number for its rate limit. The limit is calculated over a **rolling 30-second window**. When exceeded:
- Returns HTTP `429 Too Many Requests`
- Includes `Retry-After` header with seconds to wait

**Practical polling guidance (from community patterns):**
- 1-2 second polling is reported to work but risks hitting limits under heavy use
- **Recommended approach:** adaptive polling based on remaining track duration
  - While a track has > 30 seconds remaining: poll every 5-10 seconds
  - When < `polling_interval` seconds remain: poll again `remaining_ms + 1000ms` after current check
  - On `204` response (no playback): back off to 30+ seconds

The Home Assistant Spotify integration uses exactly this adaptive pattern — it calculates `time_remaining + 1s` as the next poll interval when a track is nearly done.

**Source:** https://developer.spotify.com/documentation/web-api/concepts/rate-limits
**Source:** https://github.com/home-assistant/core/pull/136461

---

## 4. OAuth Scopes Required

For this service, the minimal required scopes are:

| Scope | Purpose |
|-------|---------|
| `user-read-playback-state` | Poll `GET /me/player` to read current track, device, progress |
| `user-modify-playback-state` | `POST /me/player/next` to skip a track |
| `user-read-currently-playing` | Optional — lighter read-only alternative to `user-read-playback-state` |

Request both `user-read-playback-state` and `user-modify-playback-state` together in the initial authorization. Do not request `user-read-currently-playing` separately — it is redundant when you have `user-read-playback-state`.

**Source:** https://developer.spotify.com/documentation/web-api/concepts/scopes

---

## 5. OAuth Flow for a Long-Running Background Service

### Recommended Flow: Authorization Code Flow (server-side)

**Why not PKCE:** PKCE uses refresh token rotation (each refresh burns the old refresh token and issues a new one). For a background daemon storing credentials in a file, the classic Authorization Code Flow with a `client_secret` is simpler — the refresh token does not rotate and stays valid indefinitely.

**Why not Implicit Grant:** Deprecated. Spotify ended support for implicit grant on **27 November 2025**.

**Steps:**

1. **One-time setup** (run manually once from the Mac):
   - Spin up a temporary local HTTP server on a port (e.g., `http://127.0.0.1:8888/callback`)
   - Register this as the redirect URI in the Spotify Developer Dashboard
   - Direct the browser to:
     ```
     https://accounts.spotify.com/authorize
       ?client_id=CLIENT_ID
       &response_type=code
       &redirect_uri=http%3A%2F%2F127.0.0.1%3A8888%2Fcallback
       &scope=user-read-playback-state%20user-modify-playback-state
     ```
   - Exchange the returned `code` for tokens via `POST https://accounts.spotify.com/api/token`
   - Persist `refresh_token` and `access_token` to a local file (e.g., `.spotify_tokens.json`)

2. **Background service token refresh:**
   - Access tokens expire after **1 hour**
   - Before each API call (or on `401` response), check if the access token is near expiry
   - Refresh by posting to `https://accounts.spotify.com/api/token`:
     ```
     grant_type=refresh_token
     refresh_token=<stored_token>
     ```
     With `Authorization: Basic base64(client_id:client_secret)` header
   - The response may or may not include a new `refresh_token` — if it does, update the stored one
   - Refresh tokens have no documented expiry, but Spotify can invalidate them if:
     - The user revokes access
     - The token is unused for a very long time (undocumented threshold)

**Spotipy library (Python):** The `spotipy` library handles this automatically with `SpotifyOAuth` and a `CacheFileHandler`. Tokens are stored in a `.cache` file and refreshed transparently on expiry. This is the recommended approach for a Python service.

```python
import spotipy
from spotipy.oauth2 import SpotifyOAuth

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id="CLIENT_ID",
    client_secret="CLIENT_SECRET",
    redirect_uri="http://127.0.0.1:8888/callback",
    scope="user-read-playback-state user-modify-playback-state",
    cache_handler=spotipy.CacheFileHandler(cache_path=".spotify_tokens.json")
))
```

**Important: localhost redirect URIs and the 2025 OAuth migration:** Spotify ended support for HTTP redirect URIs (non-HTTPS) on 27 November 2025 — except for `127.0.0.1` and `localhost`, which are explicitly exempted for local development. Using `http://127.0.0.1:8888/callback` is safe.

**Source:** https://developer.spotify.com/documentation/web-api/tutorials/refreshing-tokens
**Source:** https://developer.spotify.com/blog/2025-10-14-reminder-oauth-migration-27-nov-2025

---

## 6. February 2026 Developer Mode Restrictions

As of February 11, 2026:

| Restriction | Value |
|-------------|-------|
| Max authorized users per app | **5** (down from 25) |
| Owner must have Premium | Yes |
| Max Client IDs per developer | 1 |
| Playback endpoints affected | **No** — not mentioned in migration guide |

**Impact on this project:** Since this is a personal family use project (owner + family = likely under 5 users), development mode is sufficient and playback control APIs remain available. No need to apply for extended quota mode.

**Source:** https://developer.spotify.com/documentation/web-api/references/changes/february-2026
**Source:** https://developer.spotify.com/blog/2026-02-06-update-on-developer-access-and-platform-security

---

## 7. The Sonos Problem: Critical Architectural Constraint

### What the Spotify API CAN do when Sonos is playing

`GET /me/player` **does return track information** when Spotify is playing on Sonos. Multiple developers confirm: you can see the currently playing track title, artist, URI, explicit flag, and `progress_ms`. The `device.name` will be the Sonos speaker name. The `device.type` will be `"speaker"`.

### What the Spotify API CANNOT do when Sonos is playing

When Sonos is the active device, it appears with `is_restricted: true`. Any write command — including `POST /me/player/next` (skip) — returns an error. The Spotify Web API cannot skip tracks on a Sonos device.

This is a known, long-standing, unresolved limitation. Community threads from 2019 through 2025 all confirm the same behavior. There is no official Spotify workaround.

**Source:** https://community.spotify.com/t5/Spotify-for-Developers/Support-for-restricted-devices-specifically-sonos-speakers/td-p/6457650
**Source:** https://github.com/spotify/web-api/issues/1337

### Detecting a Sonos device

You can detect that the active device is a Sonos speaker by:
1. `device.type == "speaker"` — narrows to speaker class devices
2. `device.name` — check against known Sonos room names (e.g., "Living Room", "Kitchen")
3. `is_restricted: true` — definitive signal that skip via Spotify API will not work

There is no `device.manufacturer` field. Detection relies on name matching or the `is_restricted` flag.

---

## 8. Sonos Skip Workarounds

### Option A: Sonos UPnP Local API via SoCo (Recommended for home server)

SoCo is a Python library that controls Sonos speakers over the local network using UPnP (no cloud, no third-party auth).

**Key methods:**

```python
import soco

# Discover all speakers on the local network
speakers = list(soco.discover())
kitchen = next(s for s in speakers if s.player_name == "Kitchen")

# Get current track info (works for Spotify too)
track = kitchen.get_current_track_info()
# Returns: dict with 'title', 'artist', 'album', 'uri', 'position', 'duration'
# For Spotify: 'uri' = "x-sonos-spotify:spotify%3Atrack%3A..." 

# Skip to next track
kitchen.next()
```

**Event subscription (avTransport service):**

SoCo supports event-driven track change detection via Sonos's UPnP event system. Instead of polling, you subscribe to the `avTransport` service:

```python
sub = kitchen.avTransport.subscribe(auto_renew=True)
while True:
    try:
        event = sub.events.get(timeout=0.5)
        # event.variables contains 'current_track_meta_data', 'transport_state', etc.
    except queue.Empty:
        pass
```

**Known issue:** When Spotify is playing via Spotify Connect (not Sonos queue), avTransport events can throw a `DIDLMetadataError` about a missing `restricted` attribute. This means SoCo's event parsing may fail when Spotify Direct Connect is in use (as opposed to Spotify tracks added to the Sonos queue directly).

**Source:** https://github.com/SoCo/SoCo/issues/453

**Practical hybrid approach:** Use Spotify API polling to read track metadata (since it works correctly for track info), and use SoCo `speaker.next()` to execute the skip on the local network. This avoids the avTransport parsing bug entirely.

### Option B: Sonos Cloud Control API

Sonos has an official cloud API at `api.ws.sonos.com/control/api/v1/...`. It uses OAuth 2.0 (separate from Spotify) and routes commands through Sonos's cloud.

**Skip endpoint pattern:**
```
POST /v1/groups/{groupId}/playback/skipToNextTrack
Authorization: Bearer {sonos_token}
```

**Tradeoffs vs SoCo:**
- Requires registering a Sonos developer app and going through Sonos OAuth
- Cloud-dependent (adds latency, fails if Sonos cloud is down)
- More complex authentication to set up
- Access tokens expire after 24 hours (longer than Spotify's 1 hour)

**Verdict:** For a home server project, SoCo local UPnP is significantly simpler than the Sonos Cloud API. Use SoCo.

**Source:** https://docs.sonos.com/docs/control

### Option C: node-sonos-http-api

A community Node.js bridge (jishi/node-sonos-http-api) that exposes a local HTTP API for Sonos control:
```
GET http://localhost:5005/{RoomName}/next
```
This works but adds a Node.js process as a dependency. Prefer SoCo for a Python-native solution.

---

## 9. Content Filtering: What the API Provides

### Explicit flag

The `explicit` boolean on the `TrackObject` is the primary signal for family-safe filtering:
- `true` — track has explicit lyrics
- `false` — track is clean OR explicit status is unknown

**Limitation:** `false` does not guarantee clean content — it may just mean Spotify has no rating for that track. Local files and some older catalog entries have `explicit: false` by default.

### Track type

The `item.type` field distinguishes:
- `"track"` — standard music track
- `"episode"` — podcast episode

Podcast episodes do not have an `explicit` flag in the same way. You will need to decide separately whether to filter podcast episodes.

### Local files

`is_local: true` tracks have no Spotify URI and minimal metadata. The `explicit` field will be `false` for all local files regardless of content. The service cannot auto-skip local files based on content rating alone.

### Spotify ads

When Spotify plays an ad on a free account, the playback state may return a track URI starting with `spotify:ad:`. Premium accounts do not get ads, so this is only relevant if running on a free account. The skip API call on ads returns a restriction error regardless of device type.

---

## 10. Polling Strategy: Recommended Implementation

```python
import time

POLL_INTERVAL_DEFAULT = 5.0      # seconds, when track has plenty of time left
POLL_INTERVAL_NO_PLAY = 30.0     # seconds, when nothing is playing
MIN_POLL_INTERVAL = 1.0          # don't poll faster than this

last_track_id = None

while True:
    state = sp.current_playback()  # GET /me/player

    if state is None or not state.get("is_playing"):
        time.sleep(POLL_INTERVAL_NO_PLAY)
        continue

    track = state["item"]
    track_id = track["id"] if track else None

    if track_id != last_track_id:
        last_track_id = track_id
        on_track_change(track, state["device"])

    # Calculate time until end of track
    duration_ms = track.get("duration_ms", 0) if track else 0
    progress_ms = state.get("progress_ms", 0)
    remaining_ms = duration_ms - progress_ms

    # Poll again just after track ends
    if remaining_ms < (POLL_INTERVAL_DEFAULT * 1000):
        sleep_s = max(MIN_POLL_INTERVAL, (remaining_ms / 1000) + 1.0)
    else:
        sleep_s = POLL_INTERVAL_DEFAULT

    time.sleep(sleep_s)
```

### Skip logic

```python
def on_track_change(track, device):
    if should_skip(track):
        if device.get("is_restricted"):
            # Sonos: use SoCo local API
            sonos_speaker.next()
        else:
            # Direct Spotify device: use Spotify API
            sp.next_track()

def should_skip(track):
    if track is None:
        return False
    if track.get("explicit"):
        return True
    # Add additional custom rules here
    return False
```

---

## 11. Edge Cases and Gotchas

### Sonos "is_restricted" but GET works

Reading `GET /me/player` succeeds when Sonos is the active device and returns full track info. Only write commands (skip, pause, seek) are blocked. This is the key insight that makes the hybrid Spotify-read + SoCo-skip architecture viable.

### 204 responses between tracks

Between tracks, `GET /me/player` may briefly return `204 No Content` even on active Spotify accounts. This is normal. Treat 204 as "nothing playing right now" and do not treat it as an error. Use the adaptive poll interval: sleep for `remaining_ms + 1s` to catch the track change promptly.

### Rapid track IDs after skip

After calling `next_track()` or `sonos.next()`, the Spotify API may still return the old track for 1-3 seconds before updating. Implement a short debounce or a "recently skipped" set to avoid double-skipping the same track.

### Explicit flag reliability

The `explicit` field is only reliable for tracks Spotify has content-rated. Some tracks — especially older catalog items, regional content, and DJ sets — will have `explicit: false` even if they contain explicit lyrics. The flag is a best-effort signal, not a guarantee.

### Local files bypass all filtering

`is_local: true` tracks have no content rating data. The service will see them with `explicit: false`. Consider defaulting to skip all local files if family-safe mode is the goal, or allowlisting them explicitly.

### Podcast episodes

Episode objects have `explicit` booleans on them. However, podcast ads within episodes cannot be individually skipped via the API. If the user is playing a podcast and an inline ad starts, the service cannot reliably detect it as an ad segment at the track level.

### Free account ads

On a free Spotify account, ads appear as tracks with URI `spotify:ad:...`. Attempting to skip an ad returns a restriction error from Spotify's API regardless of device. Skipping via SoCo may work on Sonos (the Sonos queue would move past the Spotify ad placeholder), but behavior is unpredictable. This project assumes Premium.

### Sonos speaker grouping

If Sonos speakers are grouped (e.g., "Living Room + Kitchen"), SoCo commands target a specific speaker but the group plays in sync. Call `speaker.next()` on the group coordinator (the speaker that "owns" the group). In SoCo, `speaker.group.coordinator` gives you the coordinator.

```python
coordinator = kitchen.group.coordinator
coordinator.next()
```

### Token storage security

The refresh token stored on disk grants full access to the Spotify account. Store it with restrictive file permissions (`chmod 600`). Do not commit it to version control.

### Rate limit 429 on rapid polling

If the service polls at 1-second intervals and the user's Spotify account is also used by the Spotify mobile app, the combined request rate may hit limits. The `Retry-After` header will tell you how long to wait. The adaptive polling strategy above (5s default, burst only near track end) stays well within normal rate limits.

---

## 12. Architecture Decision: Hybrid Approach

Given the constraints above, the recommended architecture for this service is:

**Read:** Spotify Web API (`GET /me/player`) — always works, returns full track metadata including `explicit` flag, regardless of whether Sonos or phone/desktop is the active device.

**Skip:** Two-path based on `device.is_restricted`:
- `is_restricted: false` → `POST /api.spotify.com/v1/me/player/next` (Spotify API)
- `is_restricted: true` (Sonos) → `soco_speaker.group.coordinator.next()` (local UPnP)

**Track change detection:** Polling `GET /me/player` every 5 seconds normally, adapting to `remaining_ms + 1s` near end of track.

This hybrid is the most reliable approach and is validated by real-world usage in the Home Assistant / SpotifyPlus community.

---

## 13. Sources

| Source | Topic | Confidence |
|--------|-------|------------|
| https://developer.spotify.com/documentation/web-api/reference/get-information-about-the-users-current-playback | GET /me/player endpoint reference | HIGH |
| https://developer.spotify.com/documentation/web-api/reference/skip-users-playback-to-next-track | Skip to next endpoint | HIGH |
| https://developer.spotify.com/documentation/web-api/concepts/scopes | OAuth scope definitions | HIGH |
| https://developer.spotify.com/documentation/web-api/concepts/rate-limits | Rate limits | HIGH |
| https://developer.spotify.com/documentation/web-api/tutorials/refreshing-tokens | Token refresh | HIGH |
| https://developer.spotify.com/documentation/web-api/references/changes/february-2026 | Feb 2026 API changes | HIGH |
| https://developer.spotify.com/blog/2026-02-06-update-on-developer-access-and-platform-security | Dev mode restrictions | HIGH |
| https://developer.spotify.com/blog/2025-10-14-reminder-oauth-migration-27-nov-2025 | OAuth migration Nov 2025 | HIGH |
| https://github.com/spotify/web-api/issues/1337 | Sonos is_restricted confirmed | MEDIUM |
| https://github.com/SoCo/SoCo | SoCo Python library | HIGH |
| https://github.com/SoCo/SoCo/issues/453 | avTransport Spotify Direct exception | MEDIUM |
| https://docs.sonos.com/docs/control | Sonos Cloud Control API | MEDIUM |
| https://github.com/home-assistant/core/pull/136461 | Adaptive polling pattern | MEDIUM |
| https://community.spotify.com/t5/Spotify-for-Developers/Support-for-restricted-devices-specifically-sonos-speakers/td-p/6457650 | Sonos restricted confirmed 2025 | MEDIUM |
