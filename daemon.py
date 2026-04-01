#!/usr/bin/env python3
"""Spotify Family Safe Mode — Core Daemon (Phase 1).

Polls Spotify /me/player/currently-playing every POLL_INTERVAL_SECONDS,
detects track changes by comparing track IDs, logs meaningful events, and
runs headlessly inside Docker with graceful SIGTERM shutdown.
"""
import asyncio
import json
import logging
import os
import random
import signal
import time

from dotenv import load_dotenv
import spotipy
from spotipy.exceptions import SpotifyException
from spotipy.oauth2 import CacheFileHandler, SpotifyOAuth

load_dotenv()

# ---------------------------------------------------------------------------
# Configuration — all values from .env (D-05, D-10, D-14)
# ---------------------------------------------------------------------------
POLL_INTERVAL = float(os.environ.get("POLL_INTERVAL_SECONDS", "1"))       # D-04, D-05
HEARTBEAT_INTERVAL = float(os.environ.get("HEARTBEAT_INTERVAL_SECONDS", "300"))  # D-10
STATE_PATH = os.environ.get("STATE_PATH", "state.json")

# ---------------------------------------------------------------------------
# Logging — plain text with timestamps to stdout (D-08, D-09)
# Docker captures stdout; use `docker compose logs -f daemon` to monitor.
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shutdown coordination
# ---------------------------------------------------------------------------
stop_event = asyncio.Event()


# ---------------------------------------------------------------------------
# State persistence (D-06)
# Phase 1 schema: {"last_track_id": null}
# Phase 2 will add family_safe_mode and consecutive_skips — use .get() style.
# ---------------------------------------------------------------------------
def load_state() -> dict:
    """Load state from STATE_PATH. Returns default state on missing/corrupt file."""
    try:
        with open(STATE_PATH) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"last_track_id": None}


def save_state(state: dict) -> None:
    """Atomically write state to STATE_PATH."""
    tmp_path = STATE_PATH + ".tmp"
    with open(tmp_path, "w") as f:
        json.dump(state, f)
    os.replace(tmp_path, STATE_PATH)


# ---------------------------------------------------------------------------
# Poll loop
# ---------------------------------------------------------------------------
async def poll_loop(sp: spotipy.Spotify) -> None:
    """Main polling coroutine. Runs until stop_event is set."""
    state = load_state()
    last_heartbeat = time.monotonic()

    log.info(
        "Daemon started. Poll interval=%.1fs, heartbeat=%.1fs",
        POLL_INTERVAL,
        HEARTBEAT_INTERVAL,
    )

    while not stop_event.is_set():
        try:
            result = sp.currently_playing()

            if result is None or result.get("item") is None:
                # 204 No Content (nothing playing) or item=null (podcast/ad)
                # D-09: log only the heartbeat, not every silent poll
                if time.monotonic() - last_heartbeat >= HEARTBEAT_INTERVAL:
                    log.info("Heartbeat: daemon alive, no playback detected")
                    last_heartbeat = time.monotonic()

            else:
                track = result["item"]
                track_id = track["id"]

                if track_id != state.get("last_track_id"):
                    # D-06: new track detected — log and persist
                    # CORE-04: read explicit flag from track item
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
                # D-07: 429 backoff — read Retry-After header, apply jitter, sleep interruptibly
                # getattr guard: SpotifyException.headers may be None on non-HTTP paths
                headers = getattr(exc, "headers", {}) or {}
                retry_after = int(headers.get("Retry-After", 5))
                # Exponential backoff with full jitter, capped at 120 seconds
                jitter = random.uniform(0, retry_after * 0.5)
                wait = min(retry_after + jitter, 120.0)
                log.warning(
                    "Rate limited (429). Backing off %.1fs (Retry-After=%s)",
                    wait,
                    retry_after,
                )
                # Sleep interruptibly so SIGTERM still exits cleanly during backoff
                try:
                    await asyncio.wait_for(
                        asyncio.shield(stop_event.wait()), timeout=wait
                    )
                except asyncio.TimeoutError:
                    pass
                continue  # Skip the normal asyncio.sleep at the end of the loop

            elif exc.http_status == 401:
                # Token refresh failed — log error; spotipy will retry on next call
                log.error("Auth error (401): %s — token refresh may have failed", exc)

            else:
                log.error("Spotify API error %s: %s", exc.http_status, exc)

        except Exception as exc:  # noqa: BLE001
            log.error("Unexpected error in poll loop: %s", exc, exc_info=True)

        # D-04: fixed 1s interval; no adaptive rate
        await asyncio.sleep(POLL_INTERVAL)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
async def main() -> None:
    """Set up auth, register signal handlers, and run the poll loop."""
    # Validate required env vars
    required = ["SPOTIFY_CLIENT_ID", "SPOTIFY_CLIENT_SECRET",
                "SPOTIFY_REDIRECT_URI", "SPOTIFY_CACHE_PATH"]
    missing = [v for v in required if not os.environ.get(v)]
    if missing:
        log.error("Missing required environment variables: %s", ", ".join(missing))
        raise SystemExit(1)

    cache_handler = CacheFileHandler(cache_path=os.environ["SPOTIFY_CACHE_PATH"])
    auth_manager = SpotifyOAuth(
        client_id=os.environ["SPOTIFY_CLIENT_ID"],
        client_secret=os.environ["SPOTIFY_CLIENT_SECRET"],
        redirect_uri=os.environ["SPOTIFY_REDIRECT_URI"],
        scope="user-read-currently-playing",
        open_browser=False,  # D-01 pattern: headless, never block on browser
        cache_handler=cache_handler,
    )
    sp = spotipy.Spotify(auth_manager=auth_manager)

    # Register SIGTERM and SIGINT handlers via asyncio event loop (not signal.signal)
    # loop.add_signal_handler schedules the callback on the event loop thread,
    # avoiding races with async tasks. (signal.signal would run in main thread.)
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop_event.set)

    await poll_loop(sp)
    log.info("Daemon stopped cleanly")


if __name__ == "__main__":
    asyncio.run(main())
