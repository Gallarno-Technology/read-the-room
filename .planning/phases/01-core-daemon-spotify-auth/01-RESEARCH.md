# Phase 1: Core Daemon & Spotify Auth - Research

**Researched:** 2026-04-01
**Domain:** Python asyncio daemon, Spotify Web API OAuth, spotipy, Docker
**Confidence:** HIGH

## Summary

Phase 1 establishes the backbone of the system: a Docker-based Python daemon that authenticates headlessly with Spotify after a one-time terminal OAuth setup, polls `GET /me/player/currently-playing` every second, and persists minimal state across restarts. The technical stack is well-understood (spotipy 2.26.0, Python 3.14, asyncio, Docker Compose 5.x), and all four requirements are directly addressable with existing libraries.

One critical API restriction surfaced during research: as of March 2026, Spotify's Development Mode requires a **Premium account** from the app owner, and the app is limited to **5 authorized users**. For this single-user personal project, this is fine as long as the app owner has Premium. The `explicit` field on the track `item` object is NOT among the fields Spotify removed in February 2026 — it remains available in Development Mode.

The asyncio poll loop requires a carefully structured graceful shutdown pattern: `loop.add_signal_handler` for SIGTERM/SIGINT, and an `asyncio.Event` stop flag rather than relying on `asyncio.run()` defaults. Docker's `restart: always` replaces macOS LaunchAgent; the Dockerfile MUST use exec form `CMD ["python", "daemon.py"]` to ensure Python is PID 1 and receives SIGTERM.

**Primary recommendation:** Use spotipy 2.26.0 with `SpotifyOAuth(open_browser=False)` and `CacheFileHandler`, python-dotenv for `.env` loading, and a manual asyncio event loop with explicit signal handlers. Do not use tenacity or backoff libraries — hand-write 429 handling (read `Retry-After` header, sleep, resume) because spotipy's internal retry adapter does not surface the `Retry-After` value to application code.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** `setup_auth.py` prints the Spotify auth URL to the terminal — no auto-open browser. User opens URL on their phone (SSH'd into the host from mobile), approves in Spotify, then pastes the full redirect URL back into the terminal prompt.
- **D-02:** After saving the token, the script makes one test API call (e.g. fetch current user profile) to validate the token works, then prints a success message and exits.
- **D-03:** Token stored via spotipy's `CacheFileHandler` (Authorization Code Flow). Token file path configurable via `.env`.
- **D-04:** Fixed 1s poll interval — no adaptive rate. Daemon calls `GET /me/player/currently-playing` every second regardless of playback state.
- **D-05:** Poll interval is configurable via `.env` (e.g. `POLL_INTERVAL_SECONDS=1`).
- **D-06:** Track change detection: compare returned track ID to last known track ID. New ID = new track event.
- **D-07:** 429 backoff on Spotify rate limit responses — exponential backoff with jitter, then resume normal polling.
- **D-08:** Plain text with timestamps to stdout. Docker captures stdout; use `docker logs` to monitor live.
- **D-09:** Log only meaningful events: daemon start, track changes, auth errors, API errors. Silent between events.
- **D-10:** Periodic heartbeat log line when no playback is detected (interval configurable via `.env`, e.g. `HEARTBEAT_INTERVAL_SECONDS=300`). Confirms daemon is alive when nothing is playing.
- **D-11:** Docker + docker-compose. The daemon and `signal-cli-rest-api` (Phase 3) are services in the same compose stack.
- **D-12:** `network_mode: host` on the daemon service — required for SoCo UPnP/multicast to reach Sonos speakers on the local network.
- **D-13:** `restart: always` on the daemon service — replaces macOS LaunchAgent KeepAlive. Auto-restarts on crash or exit.
- **D-14:** All runtime config (poll interval, token cache path, heartbeat interval, etc.) lives in a `.env` file at repo root, sourced by docker-compose.
- **D-15:** CORE-03 in REQUIREMENTS.md must be updated: "macOS LaunchAgent" → "Docker service with `restart: always`".

### Claude's Discretion

- Exact 429 backoff algorithm and max wait cap
- Heartbeat log message wording
- `.env` variable naming conventions
- `state.json` schema (Phase 1 only needs to persist current track ID for change detection across restarts)

### Deferred Ideas (OUT OF SCOPE)

- Sonos auto-detection of Family Safe Mode (v2 — SONO-01/02 in REQUIREMENTS.md)
- Web dashboard or UI for monitoring (explicitly out of scope)
- Adaptive polling rate based on playback state (user chose fixed 1s instead)
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CORE-01 | Service polls Spotify playback state every ~1 second and detects when a new track begins | asyncio poll loop with `asyncio.sleep(POLL_INTERVAL)`, track-ID comparison (D-06) |
| CORE-02 | Service authenticates with Spotify via OAuth (one-time browser setup, then headless token refresh) | spotipy `SpotifyOAuth(open_browser=False)` + `CacheFileHandler`; token auto-refreshed on each call |
| CORE-03 | Service runs as a Docker service with `restart: always` and auto-restarts on crash (updated per D-15) | Docker Compose `restart: always`, exec-form CMD for SIGTERM delivery |
| CORE-04 | Service reads the `explicit` flag from the currently playing Spotify track | `response['item']['explicit']` — field confirmed present in Development Mode after Feb 2026 changes |
</phase_requirements>

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| spotipy | 2.26.0 | Spotify Web API client, OAuth, token refresh | Official-style community library; only maintained Python SDK for Spotify; ships `SpotifyOAuth` with `open_browser=False` and `CacheFileHandler` |
| python-dotenv | 1.2.2 | Load `.env` file into `os.environ` | De-facto standard for 12-factor env config in Python; `load_dotenv()` one-liner at startup |
| asyncio | stdlib | Poll loop, sleep, signal handling | Python 3.14 stdlib; no extra dep; correct tool for I/O-bound polling |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| logging | stdlib | Structured stdout logging with timestamps | Use `logging.basicConfig(format=..., level=INFO)` — do NOT use `print()` for log lines |
| json | stdlib | Read/write `state.json` | Track ID persistence across restarts |
| signal | stdlib | SIGTERM/SIGINT handlers | Register via `loop.add_signal_handler` |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| asyncio poll loop | `threading.Timer` or `schedule` | asyncio is cleaner for future I/O work (Phase 2/3 also async); threading adds complexity |
| python-dotenv | `os.environ` only | dotenv allows per-project `.env` without polluting shell environment |
| spotipy | raw `httpx`/`requests` | spotipy handles token refresh, retry adapter, all endpoint wrappers — no reason to hand-roll |
| Hand-written 429 handler | `tenacity` / `backoff` library | 429 handling is 10 lines; adding a dep for it is overkill. Also: must read `Retry-After` header from `SpotifyException`, which decorator-based retry libs don't expose naturally |

**Installation:**
```bash
pip install spotipy==2.26.0 python-dotenv==1.2.2
```

**Version verification:** Confirmed against PyPI on 2026-04-01:
- `spotipy`: 2.26.0 (released March 3, 2026)
- `python-dotenv`: 1.2.2

---

## Architecture Patterns

### Recommended Project Structure

```
/
├── daemon.py              # Main asyncio poll loop + signal handlers
├── setup_auth.py          # One-time OAuth setup (print URL, paste redirect)
├── state.json             # Runtime state persisted across restarts (gitignored)
├── .env                   # Config vars — never committed
├── .env.example           # Template committed to git
├── Dockerfile             # Python image, exec-form CMD
├── docker-compose.yml     # daemon service (network_mode: host, restart: always)
└── requirements.txt       # spotipy, python-dotenv
```

### Pattern 1: SpotifyOAuth Headless Setup (setup_auth.py)

**What:** One-time terminal OAuth. Print auth URL, user pastes redirect URL, token saved to cache file.

**When to use:** Only run by human during initial setup on the server.

```python
# Source: spotipy docs + GitHub spotipy-dev/spotipy oauth2.py
import os
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth, CacheFileHandler

load_dotenv()

cache_handler = CacheFileHandler(cache_path=os.environ["SPOTIFY_CACHE_PATH"])
auth_manager = SpotifyOAuth(
    client_id=os.environ["SPOTIFY_CLIENT_ID"],
    client_secret=os.environ["SPOTIFY_CLIENT_SECRET"],
    redirect_uri=os.environ["SPOTIFY_REDIRECT_URI"],  # http://127.0.0.1:8080
    scope="user-read-currently-playing",
    open_browser=False,       # Critical: print URL instead of auto-opening
    cache_handler=cache_handler,
)

# SpotifyOAuth.get_authorize_url() returns the URL to print
auth_url = auth_manager.get_authorize_url()
print(f"Open this URL in a browser and approve:\n{auth_url}\n")
redirect_response = input("Paste the full redirect URL here: ").strip()

# Exchange code for token (saves to cache automatically)
auth_manager.get_access_token(
    auth_manager.parse_response_code(redirect_response)
)

# Validate with one test call (D-02)
sp = spotipy.Spotify(auth_manager=auth_manager)
user = sp.current_user()
print(f"Auth successful. Logged in as: {user['display_name']}")
```

**Key details:**
- `redirect_uri` must be registered in the Spotify Developer Dashboard. Use `http://127.0.0.1:8080` (not `localhost` — Spotify banned the hostname alias Nov 2025, but `127.0.0.1` IP is still allowed).
- Scope required: `user-read-currently-playing` (minimum). Add `user-read-playback-state` if device info is needed later.

### Pattern 2: Daemon Poll Loop (daemon.py)

**What:** asyncio loop that polls every `POLL_INTERVAL_SECONDS`, compares track IDs, logs on change, handles 429 with backoff, writes heartbeat, saves state.

```python
# Source: Python asyncio docs + roguelynn.com graceful shutdown article
import asyncio
import json
import logging
import os
import random
import signal
import time
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth, CacheFileHandler
from spotipy.exceptions import SpotifyException

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger(__name__)

POLL_INTERVAL = float(os.environ.get("POLL_INTERVAL_SECONDS", "1"))
HEARTBEAT_INTERVAL = float(os.environ.get("HEARTBEAT_INTERVAL_SECONDS", "300"))
STATE_PATH = os.environ.get("STATE_PATH", "state.json")

stop_event = asyncio.Event()


def load_state():
    try:
        with open(STATE_PATH) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"last_track_id": None}


def save_state(state: dict):
    with open(STATE_PATH, "w") as f:
        json.dump(state, f)


async def poll_loop(sp: spotipy.Spotify):
    state = load_state()
    last_heartbeat = time.monotonic()
    log.info("Daemon started. Polling every %.1fs", POLL_INTERVAL)

    while not stop_event.is_set():
        try:
            result = sp.currently_playing()

            if result is None or result.get("item") is None:
                # 204 No Content or nothing playing
                if time.monotonic() - last_heartbeat >= HEARTBEAT_INTERVAL:
                    log.info("Heartbeat: no playback detected")
                    last_heartbeat = time.monotonic()
            else:
                track = result["item"]
                track_id = track["id"]
                if track_id != state["last_track_id"]:
                    log.info(
                        "Track change: %s — %s (explicit=%s)",
                        track["name"],
                        track["artists"][0]["name"],
                        track["explicit"],
                    )
                    state["last_track_id"] = track_id
                    save_state(state)
                    last_heartbeat = time.monotonic()

        except SpotifyException as exc:
            if exc.http_status == 429:
                retry_after = int(exc.headers.get("Retry-After", 5))
                # Exponential backoff with full jitter, cap at 120s
                wait = min(retry_after + random.uniform(0, retry_after * 0.5), 120)
                log.warning("Rate limited (429). Sleeping %.1fs", wait)
                try:
                    await asyncio.wait_for(
                        asyncio.shield(stop_event.wait()), timeout=wait
                    )
                except asyncio.TimeoutError:
                    pass
                continue
            else:
                log.error("Spotify API error %s: %s", exc.http_status, exc)

        except Exception as exc:
            log.error("Unexpected error: %s", exc)

        await asyncio.sleep(POLL_INTERVAL)


async def main():
    cache_handler = CacheFileHandler(cache_path=os.environ["SPOTIFY_CACHE_PATH"])
    auth_manager = SpotifyOAuth(
        client_id=os.environ["SPOTIFY_CLIENT_ID"],
        client_secret=os.environ["SPOTIFY_CLIENT_SECRET"],
        redirect_uri=os.environ["SPOTIFY_REDIRECT_URI"],
        scope="user-read-currently-playing",
        open_browser=False,
        cache_handler=cache_handler,
    )
    sp = spotipy.Spotify(auth_manager=auth_manager)

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop_event.set)

    await poll_loop(sp)
    log.info("Daemon stopped cleanly")


if __name__ == "__main__":
    asyncio.run(main())
```

**Key details:**
- `loop.add_signal_handler` (not `signal.signal`) because asyncio needs to schedule the stop on the event loop thread.
- `stop_event.set()` is the only thing signal handlers do — no complex logic in signal context.
- The 429 backoff reads `Retry-After` from the exception headers, applies `min(retry_after * 1.5, 120)` jitter cap, then sleeps interruptibly via `asyncio.wait_for` so SIGTERM still exits cleanly.

### Pattern 3: Docker Configuration

**What:** Dockerfile + docker-compose.yml for the daemon service.

```dockerfile
# Dockerfile — exec form CMD critical for SIGTERM delivery
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "daemon.py"]
```

```yaml
# docker-compose.yml
services:
  daemon:
    build: .
    restart: always
    network_mode: host          # Required for SoCo UPnP (Phase 2); no cost in Phase 1
    env_file: .env
    volumes:
      - ./state.json:/app/state.json    # Bind mount — persists state across restarts
      - ./token_cache:/app/token_cache  # Bind mount — persists OAuth token
```

**Key details:**
- `CMD ["python", "daemon.py"]` (exec form) — Python becomes PID 1 and receives SIGTERM directly. Shell form `CMD "python daemon.py"` causes a 10-second kill delay.
- `state.json` bind-mounted from host so it survives container replacement. Pre-create the file (`echo '{}' > state.json`) before first `docker compose up` or the bind mount creates a directory instead.
- `env_file: .env` — docker-compose loads the `.env` file; no need for `${VAR}` interpolation in the compose file itself.

### Anti-Patterns to Avoid

- **Shell form CMD in Dockerfile:** `CMD "python daemon.py"` spawns a shell as PID 1; SIGTERM never reaches Python; container takes 10 seconds to stop. Use exec form array syntax.
- **Using `signal.signal()` instead of `loop.add_signal_handler()`:** `signal.signal` works but doesn't integrate with asyncio's event loop — the handler runs in the main thread and can race with async tasks.
- **`asyncio.run()` for signal handling only:** `asyncio.run()` is fine here; just register handlers inside the coroutine via `asyncio.get_running_loop()`.
- **Named volume for state.json:** `volumes: - state_data:/app/state.json` — Docker treats the path as a directory inside the volume, not a file. Use bind mount with a host-side file.
- **Storing `open_browser=True` in production:** spotipy defaults to `open_browser=True`; forgetting `open_browser=False` blocks the daemon on startup waiting for a browser that will never open.
- **Using `localhost` as redirect URI:** Spotify banned hostname-alias `localhost` in OAuth redirect URIs on Nov 27, 2025. Use `http://127.0.0.1:8080` explicitly.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Spotify OAuth + token refresh | Custom auth flow | `spotipy.SpotifyOAuth` + `CacheFileHandler` | Token refresh, cache serialization, scope management, error codes — all handled |
| `.env` file loading | `os.environ` + manual file parse | `python-dotenv` | dotenv handles quoting, comments, multiline, env override ordering correctly |
| HTTP retry adapter | Custom `requests.Session` | spotipy's built-in `Retry` adapter | Already configured for 429/500/502/503/504 at the session level |

**Key insight:** The only custom logic worth hand-rolling is the 429 Retry-After sleep, because spotipy's internal adapter doesn't surface the header value to application code — you need to catch `SpotifyException` and read `exc.headers["Retry-After"]` yourself.

---

## Common Pitfalls

### Pitfall 1: `currently_playing()` Returns `None` (204 No Content)

**What goes wrong:** When nothing is playing, Spotify returns HTTP 204 — no body. spotipy returns `None`. Code that does `result["item"]` immediately raises `TypeError`.

**Why it happens:** The endpoint returns 204 (not 200 with empty data) when no active playback exists.

**How to avoid:** Always guard: `if result is None or result.get("item") is None: # nothing playing`.

**Warning signs:** `TypeError: 'NoneType' object is not subscriptable` in logs immediately after stopping playback.

### Pitfall 2: `item` Can Be `None` Even With 200 Response

**What goes wrong:** The API can return `{"is_playing": false, "item": null, ...}` with a 200 when a podcast or ad is playing. Checking only `result is not None` is insufficient.

**How to avoid:** Always check `result.get("item") is not None` before accessing `result["item"]`.

### Pitfall 3: Redirect URI Must Be `http://127.0.0.1:PORT` Not `http://localhost:PORT`

**What goes wrong:** OAuth fails with an invalid redirect URI error.

**Why it happens:** Spotify banned `localhost` hostname aliases in OAuth redirect URIs on November 27, 2025. Only explicit IP literals work.

**How to avoid:** Register `http://127.0.0.1:8080` (not `localhost`) in the Spotify Developer Dashboard and in `.env`.

### Pitfall 4: Shell-Form CMD Causes Slow Docker Shutdown

**What goes wrong:** `docker compose stop` takes 10 seconds per container, then sends SIGKILL. State may not flush cleanly.

**Why it happens:** Shell form runs a `/bin/sh -c` wrapper as PID 1. Shells don't forward signals to child processes by default.

**How to avoid:** `CMD ["python", "daemon.py"]` — exec form always.

### Pitfall 5: `state.json` Bind Mount Creates Directory

**What goes wrong:** `docker compose up` fails or `state.json` is a directory, not a file.

**Why it happens:** If `state.json` doesn't exist on the host when docker-compose runs, Docker creates a directory at that path for the bind mount.

**How to avoid:** Pre-create the file before first `docker compose up`:
```bash
echo '{"last_track_id": null}' > state.json
```

### Pitfall 6: Token Cache File Not Mounted Loses Auth on Container Rebuild

**What goes wrong:** `docker compose up --build` recreates the container, losing the cached OAuth token, requiring re-running `setup_auth.py`.

**Why it happens:** Token cache stored inside container filesystem, which is ephemeral.

**How to avoid:** Bind-mount the token cache directory to the host (e.g., `./token_cache:/app/token_cache`). Pre-create the directory: `mkdir -p token_cache`.

### Pitfall 7: Development Mode Now Requires Spotify Premium

**What goes wrong:** API calls return 403 "Premium required" errors.

**Why it happens:** As of March 9, 2026, Spotify's Development Mode requires the app owner to have a Spotify Premium subscription.

**How to avoid:** Verify Premium status before starting Phase 1. This is a pre-flight check, not a code issue.

### Pitfall 8: SpotifyException 429 Headers Access

**What goes wrong:** `exc.headers["Retry-After"]` raises `KeyError` or is not accessible.

**Why it happens:** `SpotifyException.headers` is set from the HTTP response headers dict — it may not always include `Retry-After` (rate limit without explicit header).

**How to avoid:** Use `.get("Retry-After", 5)` with a sensible default:
```python
retry_after = int(exc.headers.get("Retry-After", 5))
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| macOS LaunchAgent plist for daemon | Docker `restart: always` | Project decision (D-13) | Works on Proxmox/Arch Linux; no macOS dependency |
| `localhost` in redirect URI | `http://127.0.0.1:PORT` | November 27, 2025 | Existing apps using `localhost` stopped working |
| Implicit grant OAuth flow | Authorization Code Flow (or PKCE) | November 27, 2025 | Implicit flow unsupported; this project always used Auth Code flow |
| Any developer could apply for Extended Quota Mode | Extended Quota Mode restricted to organizations with 250K MAU | May 15, 2025 | Personal projects stay in Development Mode |
| Development Mode free for all | Development Mode requires Spotify Premium from app owner | March 9, 2026 | Must have Premium account |

**Deprecated/outdated:**
- `util.prompt_for_user_token()`: Deprecated in spotipy — use `SpotifyOAuth` directly.
- `cache_path` and `username` params directly on `SpotifyOAuth`: Deprecated — pass `CacheFileHandler(cache_path=...)` as `cache_handler` instead.
- `localhost` redirect URIs: Banned by Spotify November 2025.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3 | daemon.py, setup_auth.py | Yes | 3.14.3 | — |
| Docker | Container deployment | Yes | 29.3.1 | — |
| Docker Compose | Service orchestration | Yes | 5.1.1 | — |
| spotipy | Spotify API client | Not installed | Needs install (2.26.0) | — |
| python-dotenv | .env loading | Not installed | Needs install (1.2.2) | — |
| Spotify Premium account | Development Mode API access (March 2026 requirement) | Unknown — must verify | — | No fallback; required by Spotify |

**Missing dependencies with no fallback:**
- Spotify Premium: Required as of March 9, 2026 for Development Mode app owner. Must confirm before beginning implementation.

**Missing dependencies with fallback:**
- spotipy, python-dotenv: Not yet installed on host. Will be installed via `pip install` in Dockerfile and optionally in a `requirements.txt` for local dev.

---

## Open Questions

1. **Does the app owner have Spotify Premium?**
   - What we know: Spotify requires Premium from March 9, 2026 for Development Mode.
   - What's unclear: Whether the user has Premium.
   - Recommendation: Verify before starting Wave 1. If not Premium, API calls will fail with 403.

2. **Is `SpotifyException.headers` reliably populated in spotipy 2.26.0?**
   - What we know: `SpotifyException` stores headers from the response. The `Retry-After` key is documented by Spotify as "normally" present on 429 responses.
   - What's unclear: Whether spotipy 2.26.0 always sets `exc.headers` (it may be `None` if the exception is raised from a non-HTTP path).
   - Recommendation: Wrap in `getattr(exc, 'headers', {}) or {}` for safety.

3. **What redirect URI port to use in setup_auth.py?**
   - What we know: Must be `http://127.0.0.1:PORT` registered in Spotify Dashboard.
   - What's unclear: Whether the user has already registered a redirect URI.
   - Recommendation: Plan should include a step to register `http://127.0.0.1:8080` in Spotify Developer Dashboard before running `setup_auth.py`.

---

## Sources

### Primary (HIGH confidence)

- PyPI / curl `https://pypi.org/pypi/spotipy/json` — confirmed 2.26.0, March 3 2026
- PyPI / curl `https://pypi.org/pypi/python-dotenv/json` — confirmed 1.2.2
- PyPI / curl `https://pypi.org/pypi/tenacity/json` — confirmed 9.1.4
- GitHub spotipy-dev/spotipy oauth2.py — `SpotifyOAuth` parameters: `open_browser`, `cache_handler`, `CacheFileHandler(cache_path=)`
- GitHub spotipy-dev/spotipy client.py — `currently_playing()` method signature and return
- Spotify Web API Reference `get-the-users-currently-playing-track` — response structure, `item.explicit`, response codes
- Spotify February 2026 Migration Guide — confirmed `explicit` field NOT removed in Development Mode
- Spotify November 2025 OAuth blog — `localhost` banned, `127.0.0.1` allowed, Auth Code Flow unaffected
- Spotify February 2026 Developer Update — Premium required for Development Mode from March 9, 2026
- Docker docs (tutorialpedia) — exec-form CMD required for PID 1 / SIGTERM delivery

### Secondary (MEDIUM confidence)

- roguelynn.com "Graceful Shutdowns with asyncio" — `loop.add_signal_handler` pattern, `asyncio.Event` stop flag
- Python docs `asyncio-eventloop.html` — `loop.add_signal_handler` API
- Spotify Developer `quota-modes` page — Development Mode 5-user cap, Premium requirement

### Tertiary (LOW confidence)

- WebSearch community results on 429 Retry-After values (reports of 21-hour waits with aggressive polling) — treat as anecdote; follow `Retry-After` header value, capped at 120s

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — versions verified against PyPI registry on 2026-04-01
- Architecture patterns: HIGH — spotipy source code read directly; Docker SIGTERM behavior verified
- API response structure: HIGH — checked Spotify official reference and Feb 2026 migration guide
- Pitfalls: HIGH for known issues (204, redirect URI, PID 1); MEDIUM for SpotifyException.headers edge case
- Spotify Premium requirement: HIGH — official Spotify developer blog post

**Research date:** 2026-04-01
**Valid until:** 2026-05-01 (Spotify API policies are in active flux — re-verify before Phase 2)
