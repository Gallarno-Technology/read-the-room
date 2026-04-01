# Architecture Patterns

**Domain:** Real-time music playback monitoring and content filtering daemon
**Researched:** 2026-04-01
**Confidence:** HIGH (core API facts verified against official Spotify docs; polling interval guidance MEDIUM from community)

---

## Recommended Architecture

A single Python process running as a macOS LaunchAgent. The main loop polls
`GET /me/player/currently-playing` on an adaptive interval, compares the
returned track ID against the previous state, and issues `POST /me/player/next`
within the same event tick when a violation is detected. State is persisted to
a small JSON file so the process can survive crashes and restarts.

```
┌─────────────────────────────────────────────────────────┐
│  macOS LaunchAgent (KeepAlive = true)                   │
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Polling Loop (asyncio)                          │   │
│  │                                                  │   │
│  │  1. GET /me/player/currently-playing             │   │
│  │  2. Compare track_id to last_seen_track_id       │   │
│  │  3. On change → ContentChecker                   │   │
│  │  4. ContentChecker returns SKIP / ALLOW          │   │
│  │  5. On SKIP → POST /me/player/next               │   │
│  │  6. Write state.json                             │   │
│  │  7. Adaptive sleep (see interval table)          │   │
│  └──────────────────────────────────────────────────┘   │
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │  ContentChecker                                  │   │
│  │  • explicit flag from track object               │   │
│  │  • configurable keyword/artist blocklist         │   │
│  │  • Family Safe Mode toggle (read from state)     │   │
│  └──────────────────────────────────────────────────┘   │
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │  state.json (on-disk, written after each change) │   │
│  │  • last_track_id, last_track_name                │   │
│  │  • family_safe_mode: bool                        │   │
│  │  • consecutive_skips: int                        │   │
│  │  • skip_log: [{track, reason, timestamp}]        │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

---

## Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| `daemon.py` | Entry point, asyncio event loop, signal handling | SpotifyClient, ContentChecker, StateStore |
| `SpotifyClient` | All HTTP calls to Spotify Web API; auth + token refresh | Spotify REST API |
| `ContentChecker` | Evaluates a track object; returns SKIP/ALLOW + reason | StateStore (for toggle) |
| `StateStore` | Read/write `state.json`; in-memory cache | Filesystem |
| `launchd plist` | Process lifecycle, KeepAlive, log redirection | macOS launchd |

---

## 1. Polling vs. Webhooks

### Verdict: Polling only — no webhook alternative exists

Spotify has never offered native webhooks for playback events. There are open
GitHub issues requesting this (issue #492, issue #538 on `spotify/web-api`)
dating to 2016 that remain unresolved as of 2026.

The internal WebSocket that the Spotify desktop client uses is not publicly
accessible. Reverse-engineered access to it is unsupported, fragile, and risks
account suspension.

**The only supported approach is polling `GET /me/player/currently-playing`.**

### Polling Rate Limits

Spotify's rate limit is a rolling 30-second window. The exact number is not
published. Empirical community reports (verified across multiple forum threads)
suggest roughly 180 requests per 30 seconds (~6 req/s) before hitting 429.

For a personal, single-account use case with one polling loop:

| Interval | Requests/30 s | Risk | Latency to detect change |
|----------|---------------|------|--------------------------|
| 1 s      | 30            | Low  | ~1 s (worst case)        |
| 2 s      | 15            | Very low | ~2 s                 |
| 3 s      | 10            | Minimal | ~3 s                  |

**Recommendation: 1-second polling for a personal, single-user daemon.**

At 30 requests per 30-second window for one account, the rate limit (empirically
observed at ~180 req/30 s) is not a concern. This gives worst-case detection
latency of 1 second, meeting the "within 1-2 seconds" requirement.

### Adaptive Interval Strategy (optional optimization)

The `currently-playing` response includes `progress_ms` and `duration_ms`. You
can use these to tighten the polling window:

```python
time_remaining_ms = track.duration_ms - track.progress_ms
if time_remaining_ms > 30_000:
    sleep_interval = 1.0   # standard 1-second polling
elif time_remaining_ms > 5_000:
    sleep_interval = 0.5   # tighten near end of track
else:
    sleep_interval = 0.25  # very frequent near track boundary
```

**Caveat:** `progress_ms` is reported to lag by 0.5–1.5 seconds and can be off
by more. Manual skips also invalidate the timer. Treat this as an optimization
layer, not a replacement for constant polling.

### 429 Handling

```python
async def poll_with_backoff(client, state):
    retry_after = 1
    while True:
        try:
            result = await client.currently_playing()
            retry_after = 1   # reset on success
            await process(result, state)
        except SpotifyRateLimitError as e:
            # Retry-After header is authoritative
            wait = getattr(e, 'retry_after', retry_after)
            await asyncio.sleep(wait)
            retry_after = min(retry_after * 2, 60)
        except SpotifyNetworkError:
            await asyncio.sleep(5)
```

---

## 2. Technology Stack Recommendation

### Language: Python 3.11+

**Why Python over Node.js or Go:**

- `spotipy` (version 2.26.0, released March 2026, 42.9k dependents) is the most
  maintained Spotify client library across all languages. It wraps the full Web
  API and handles OAuth token refresh automatically.
- `asyncio` standard library handles the polling loop without dependencies.
- Easier to read/modify for a personal project than Go.
- Node.js is viable but `spotify-web-api-node` is in maintenance mode (last
  release 4.0.0 over a year ago). The official `@spotify/web-api-ts-sdk`
  (v1.2.0) is last published 2 years ago. Neither is actively maintained.
- Go has no first-class Spotify library; raw HTTP is straightforward but adds
  boilerplate for a project of this scope.

### Primary Library: spotipy 2.26+

```bash
pip install spotipy
```

Key capabilities used:
- `sp.currently_playing()` — polls playback state
- `sp.next_track()` — issues skip
- `sp.queue()` — fetches upcoming tracks for pre-fetch
- `SpotifyOAuth` with `CacheFileHandler` — handles token refresh for daemon use

### Authentication Pattern for a Daemon

The OAuth dance (browser redirect) must happen once, manually, during setup.
After that, spotipy's `CacheFileHandler` stores and auto-refreshes the token.

```python
from spotipy.oauth2 import SpotifyOAuth, CacheFileHandler

SCOPES = " ".join([
    "user-read-currently-playing",
    "user-read-playback-state",
    "user-modify-playback-state",
])

cache = CacheFileHandler(cache_path="/home/user/.spotify_token_cache")
auth = SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri="http://localhost:8888/callback",
    scope=SCOPES,
    cache_handler=cache,
    open_browser=False,   # safe for headless/daemon operation
)
sp = spotipy.Spotify(auth_manager=auth)
```

Run `python setup_auth.py` once interactively to complete the browser redirect.
After that the daemon runs headlessly, refreshing the token automatically.

**Note:** As of February 2026, the app owner must have an active Spotify Premium
subscription for Development Mode apps. The skip endpoint (`POST /me/player/next`)
requires Premium. This is non-negotiable.

---

## 3. Polling Loop and Skip Architecture

### Core Pattern: Compare-and-Act

```python
async def main_loop(sp: spotipy.Spotify, state: StateStore):
    last_track_id = state.load().get("last_track_id")

    while True:
        try:
            playback = sp.currently_playing()

            if playback is None or not playback["is_playing"]:
                await asyncio.sleep(2)   # nothing playing, check less often
                continue

            item = playback.get("item")
            if item is None:
                await asyncio.sleep(1)
                continue

            track_id = item["id"]

            if track_id != last_track_id:
                # New track detected
                last_track_id = track_id
                decision = check_content(item, state)

                if decision.should_skip:
                    sp.next_track()   # fire immediately
                    state.record_skip(item, decision.reason)
                else:
                    state.record_play(item)

            await asyncio.sleep(compute_interval(playback))

        except spotipy.SpotifyException as e:
            if e.http_status == 429:
                retry_after = int(e.headers.get("Retry-After", 5))
                await asyncio.sleep(retry_after)
            else:
                await asyncio.sleep(5)
```

### Why synchronous spotipy inside asyncio is acceptable here

The polling loop is I/O-bound and sequential (one request at a time). Running
spotipy's synchronous HTTP calls inside `asyncio.run_in_executor` adds
complexity for no benefit at this scale. The blocking call takes ~100–300ms on
a home network — well within a 1-second polling budget.

For stricter async needs, the `async-spotify` library on PyPI exists but has
low community adoption and limited documentation.

### Content Checking

The Spotify track object includes an `explicit` boolean field. This is the
primary signal. The explicit field reflects Spotify's own labeling, which is
imperfect (some tracks with mature content are not labeled explicit). Layer
additional rules on top:

```python
def check_content(track: dict, state: StateStore) -> Decision:
    config = state.load_config()

    # Gate: Family Safe Mode must be on
    if not config["family_safe_mode"]:
        return Decision(should_skip=False)

    # Rule 1: Spotify explicit label
    if track.get("explicit", False):
        return Decision(should_skip=True, reason="explicit_label")

    # Rule 2: Artist blocklist
    artist_names = [a["name"].lower() for a in track.get("artists", [])]
    for artist in artist_names:
        if artist in config.get("blocked_artists", []):
            return Decision(should_skip=True, reason=f"blocked_artist:{artist}")

    # Rule 3: Track name keyword filter (last resort, high false-positive risk)
    track_name = track.get("name", "").lower()
    for keyword in config.get("blocked_keywords", []):
        if keyword in track_name:
            return Decision(should_skip=True, reason=f"keyword:{keyword}")

    return Decision(should_skip=False)
```

**Important limitation:** Spotify's `explicit` flag is creator/label-applied.
Songs with explicit lyrics that were never labeled by their label will pass
through. There is no lyric analysis API available via Spotify (audio features
were restricted in November 2024 and do not include lyrics anyway). A secondary
lyric-check service (e.g., Musixmatch, Genius API) would require a separate
lookup, adding latency.

---

## 4. Pre-fetching the Queue

### Verdict: Pre-fetch is possible but provides minimal benefit for skip use case

The `GET /me/player/queue` endpoint exists and returns the `currently_playing`
object plus an array of upcoming `queue` items (up to 20 tracks when shuffle is
on; fewer without shuffle).

You can call this at the moment a new track starts to evaluate the next-up track:

```python
def prefetch_queue(sp: spotipy.Spotify) -> list[dict]:
    result = sp.queue()
    return result.get("queue", [])  # list of track objects
```

**However, pre-fetch for skip does not eliminate the latency problem:**

- Spotify does not offer a "skip queued item before it plays" API call. The only
  skip mechanism is `POST /me/player/next`, which acts on the currently playing
  track.
- Even if you know the next track will be explicit, you cannot prevent it from
  starting — only skip it once it has started playing.
- The 1-second polling window already gives you ~1 second latency on detection.
  Pre-fetch does not reduce this.

**Where pre-fetch is useful:**

- Logging / analytics: record what is about to play without waiting.
- Warning UX: if building a companion app, you can warn a parent before the
  track starts.
- Future feature: building a replacement queue by injecting tracks via
  `POST /me/player/queue` to route around violating tracks without the jarring
  skip experience.

**Known queue endpoint limitations:**
- Returns only the first ~20 songs
- Returns empty if no device is actively playing
- Shuffle behaviour changes what is returned
- No pagination

---

## 5. macOS Daemon: launchd vs. pm2

### Recommendation: Native launchd LaunchAgent

For a personal home-server Mac, `launchd` is the correct tool. It is the macOS
native init system, starts at login (LaunchAgent) or boot (LaunchDaemon), and
requires no extra runtime.

**Do not use pm2** for a Python process. pm2 is a Node.js process manager; its
Python support works but adds unnecessary Node.js dependency and has documented
issues with launchd integration on macOS.

### Plist Location

```
~/Library/LaunchAgents/com.familysafe.spotify-monitor.plist
```

Use `LaunchAgents/` (not `LaunchDaemons/`) so the process runs as the user
whose Spotify account is authorized and can access the user keychain/token cache.

### Plist Template

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
    "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.familysafe.spotify-monitor</string>

    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/python3</string>
        <string>/Users/yourname/spotify-sentiment/daemon.py</string>
    </array>

    <!-- Restart on crash and at login -->
    <key>KeepAlive</key>
    <true/>

    <key>RunAtLoad</key>
    <true/>

    <!-- 5-second throttle: launchd won't restart faster than this -->
    <key>ThrottleInterval</key>
    <integer>5</integer>

    <key>WorkingDirectory</key>
    <string>/Users/yourname/spotify-sentiment</string>

    <!-- Capture logs for debugging -->
    <key>StandardOutPath</key>
    <string>/Users/yourname/spotify-sentiment/logs/daemon.log</string>

    <key>StandardErrorPath</key>
    <string>/Users/yourname/spotify-sentiment/logs/daemon-error.log</string>

    <!-- Environment variables for credentials -->
    <key>EnvironmentVariables</key>
    <dict>
        <key>SPOTIPY_CLIENT_ID</key>
        <string>your_client_id_here</string>
        <key>SPOTIPY_CLIENT_SECRET</key>
        <string>your_client_secret_here</string>
        <key>SPOTIPY_REDIRECT_URI</key>
        <string>http://localhost:8888/callback</string>
    </dict>
</dict>
</plist>
```

### Load / Unload Commands

```bash
# Install (load at login)
launchctl load ~/Library/LaunchAgents/com.familysafe.spotify-monitor.plist

# Start now
launchctl start com.familysafe.spotify-monitor

# Stop
launchctl stop com.familysafe.spotify-monitor

# Uninstall
launchctl unload ~/Library/LaunchAgents/com.familysafe.spotify-monitor.plist

# Check status
launchctl list | grep spotify-monitor
```

### KeepAlive Behaviour

With `KeepAlive = true` and `ThrottleInterval = 5`, launchd will:
1. Restart the process immediately after any crash
2. Wait 5 seconds before restarting (prevents CPU spin on immediate crash loops)
3. Restart at every user login
4. Log to the specified StandardOutPath/StandardErrorPath

---

## 6. State Management

### Pattern: Simple JSON File (not SQLite)

For this use case — a handful of scalar values written once per track change —
SQLite adds unnecessary complexity. A JSON file written atomically is sufficient,
reliable, and trivially human-readable for debugging.

**Atomic write pattern** (prevents corruption on crash mid-write):

```python
import json
import os
import tempfile
from pathlib import Path
from dataclasses import dataclass, field, asdict
from datetime import datetime

STATE_FILE = Path("/Users/yourname/spotify-sentiment/state.json")

@dataclass
class SkipEvent:
    track_id: str
    track_name: str
    artists: list[str]
    reason: str
    timestamp: str

@dataclass
class DaemonState:
    family_safe_mode: bool = True
    last_track_id: str | None = None
    last_track_name: str | None = None
    consecutive_skips: int = 0
    skip_log: list[SkipEvent] = field(default_factory=list)
    last_updated: str = ""

class StateStore:
    def __init__(self, path: Path = STATE_FILE):
        self.path = path
        self._cache: DaemonState | None = None

    def load(self) -> DaemonState:
        if self._cache:
            return self._cache
        try:
            data = json.loads(self.path.read_text())
            state = DaemonState(**data)
        except (FileNotFoundError, json.JSONDecodeError, TypeError):
            state = DaemonState()
        self._cache = state
        return state

    def save(self, state: DaemonState) -> None:
        state.last_updated = datetime.utcnow().isoformat()
        self._cache = state
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(asdict(state), indent=2))
        os.replace(tmp, self.path)  # atomic on POSIX

    def toggle_family_safe(self) -> bool:
        state = self.load()
        state.family_safe_mode = not state.family_safe_mode
        self.save(state)
        return state.family_safe_mode
```

### Toggling Family Safe Mode at Runtime

The daemon watches for the state file to change (via a periodic re-read on each
loop iteration). An external script or companion CLI can flip the toggle without
restarting the daemon:

```bash
# toggle_safe_mode.py (CLI companion)
import json, os, sys
from pathlib import Path

p = Path("/Users/yourname/spotify-sentiment/state.json")
data = json.loads(p.read_text())
data["family_safe_mode"] = not data.get("family_safe_mode", True)
p.write_text(json.dumps(data, indent=2))
print(f"Family Safe Mode: {data['family_safe_mode']}")
```

### Consecutive Skip Guard

To prevent an infinite skip loop (e.g., every track in the queue is blocked),
cap consecutive skips and pause the monitor:

```python
MAX_CONSECUTIVE_SKIPS = 5

if state.consecutive_skips >= MAX_CONSECUTIVE_SKIPS:
    # Stop skipping, log alert, wait for human intervention
    log.warning("Consecutive skip limit reached. Pausing content filter.")
    state.family_safe_mode = False   # or enter a degraded mode
    store.save(state)
```

---

## Key API Endpoints and Required Scopes

| Action | Endpoint | Scope |
|--------|----------|-------|
| Check what is playing | `GET /me/player/currently-playing` | `user-read-currently-playing` |
| Get full playback state | `GET /me/player` | `user-read-playback-state` |
| Skip to next track | `POST /me/player/next` | `user-modify-playback-state` |
| Look ahead at queue | `GET /me/player/queue` | `user-read-currently-playing` |

**Note:** `POST /me/player/next` (skip) requires an active Spotify Premium
subscription. This cannot be worked around.

**February 2026 API changes:** All four endpoints above remain available in
Development Mode. The November 2024 restrictions affected recommendation,
audio-features, and related-artist endpoints — none of which are needed here.

---

## Patterns to Follow

### Pattern 1: Track-ID-based Change Detection

Never use track name or progress to detect changes. Use the track `id` field.
Track IDs are stable, unique, and unambiguous.

```python
# Correct
if current_track["id"] != state.last_track_id:
    handle_new_track(current_track)

# Wrong — can cause false positives
if current_track["progress_ms"] < 2000:
    handle_new_track(current_track)
```

### Pattern 2: Immediate Skip, Then Update State

Fire the skip call before updating state. If the skip call fails, the state
remains at the previous track, and the next poll will re-evaluate.

```python
if decision.should_skip:
    try:
        sp.next_track()
        state.last_track_id = track_id   # only update after successful skip
        state.consecutive_skips += 1
    except spotipy.SpotifyException as e:
        log.error(f"Skip failed: {e}")
        # Don't update state — retry on next poll
```

### Pattern 3: Graceful Shutdown via Signal Handler

```python
import signal, asyncio

shutdown_event = asyncio.Event()

def _handle_signal(sig, frame):
    shutdown_event.set()

signal.signal(signal.SIGTERM, _handle_signal)
signal.signal(signal.SIGINT, _handle_signal)

async def main_loop():
    while not shutdown_event.is_set():
        await poll_once()
        await asyncio.sleep(1)
    store.save(state)   # flush state on clean exit
```

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Polling Faster Than 1 Second Without Back-off

**What:** `while True: check(); sleep(0.1)`
**Why bad:** 300 requests per 30 seconds for a single account is far beyond what
is needed. It provides no latency benefit beyond 1-second polling (the track has
already started; one second is the minimum perceptible window).

**Instead:** 1-second intervals with adaptive tightening near track boundaries.

### Anti-Pattern 2: Re-checking Explicit Status on Every Poll

**What:** Calling `GET /tracks/{id}` for explicit flag on every loop iteration.
**Why bad:** The `currently-playing` response already includes the `explicit`
field in the `item` object. No additional call is needed.

**Instead:** Read `playback["item"]["explicit"]` directly from the poll response.

### Anti-Pattern 3: LaunchDaemon Instead of LaunchAgent

**What:** Placing the plist in `/Library/LaunchDaemons/` to run at system boot.
**Why bad:** The daemon needs access to the user's Spotify OAuth token (stored in
`~/.spotify_token_cache`). LaunchDaemons run as root before user login; they
cannot access user home directories reliably.

**Instead:** Use `~/Library/LaunchAgents/` — runs at user login as the
authenticated user.

### Anti-Pattern 4: Hardcoding Credentials in the Plist

**What:** Putting `client_secret` directly in the plist XML.
**Why bad:** Plist files in `~/Library/LaunchAgents/` are world-readable by
default on macOS.

**Instead:** Store credentials in environment variables sourced from a
`chmod 600` dotenv file, or use the macOS Keychain:

```bash
security add-generic-password -a spotify-monitor -s SPOTIPY_CLIENT_SECRET -w "your_secret"
# Retrieve at runtime:
security find-generic-password -a spotify-monitor -s SPOTIPY_CLIENT_SECRET -w
```

### Anti-Pattern 5: Using the spotify-web-api-node or @spotify/web-api-ts-sdk

**What:** Choosing the Node.js SDK for this service.
**Why bad:** `spotify-web-api-node` is in maintenance mode. `@spotify/web-api-ts-sdk`
(v1.2.0) was last published 2 years ago by the official Spotify org. Neither is
actively maintained as of 2026.

**Instead:** Use `spotipy` (v2.26.0, March 2026 release), which is the only
actively maintained Spotify API client library across all languages.

---

## Scalability Considerations

This is a personal home server application. Scalability is not a concern. The
design is deliberately single-user, single-process, single-account.

| Concern | At 1 user (this use case) | Notes |
|---------|--------------------------|-------|
| API rate limits | Negligible (30 req/30 s) | Well within personal limits |
| Token refresh | Automatic via CacheFileHandler | No manual intervention needed |
| Crash recovery | launchd KeepAlive, 5s ThrottleInterval | State survives via state.json |
| Disk usage | Negligible (JSON state file, text logs) | Rotate logs if needed |

---

## Sources

- [Spotify Web API Rate Limits](https://developer.spotify.com/documentation/web-api/concepts/rate-limits) — HIGH confidence
- [Get Currently Playing Track Reference](https://developer.spotify.com/documentation/web-api/reference/get-the-users-currently-playing-track) — HIGH confidence
- [Skip to Next Track Reference](https://developer.spotify.com/documentation/web-api/reference/skip-users-playback-to-next-track) — HIGH confidence
- [Get User's Queue Reference](https://developer.spotify.com/documentation/web-api/reference/get-queue) — HIGH confidence
- [Spotify Web API February 2026 Changelog](https://developer.spotify.com/documentation/web-api/references/changes/february-2026) — HIGH confidence
- [February 2026 Migration Guide](https://developer.spotify.com/documentation/web-api/tutorials/february-2026-migration-guide) — HIGH confidence
- [Spotify Web API November 2024 Changes](https://developer.spotify.com/blog/2024-11-27-changes-to-the-web-api) — HIGH confidence
- [spotipy on GitHub](https://github.com/spotipy-dev/spotipy) — HIGH confidence (v2.26.0, March 2026)
- [spotify-web-api-ts-sdk (official)](https://github.com/spotify/spotify-web-api-ts-sdk) — HIGH confidence (stale, last release 2+ years ago)
- [spotify-web-api-node (community)](https://github.com/thelinmichael/spotify-web-api-node) — HIGH confidence (maintenance mode)
- [Realtime player state updates — GitHub issue #492](https://github.com/spotify/web-api/issues/492) — MEDIUM confidence (community discussion)
- [macOS launchd plist KeepAlive guide](https://andypi.co.uk/2023/02/14/how-to-run-a-python-script-as-a-service-on-mac-os/) — MEDIUM confidence
- [PM2 startup launchd docs](https://pm2.keymetrics.io/docs/usage/startup/) — HIGH confidence (documentation, not recommended)
- [Best practice to monitor current playback — Spotify Community](https://community.spotify.com/t5/Spotify-for-Developers/Best-practice-to-monitor-current-playback/td-p/6105046) — MEDIUM confidence (community)
- [Mastering Spotify API: Graceful Rate Limiting](https://tossthecoin.tcl.com/blog/mastering-spotify-api-graceful-rate) — MEDIUM confidence
