#!/usr/bin/env python3
"""Read the Room — Core Daemon.

Polls Spotify /me/player/currently-playing every POLL_INTERVAL_SECONDS,
detects track changes by comparing track IDs, logs meaningful events, and
runs headlessly inside Docker with graceful SIGTERM shutdown.
"""
from __future__ import annotations

import asyncio
import datetime
import json
import logging
import os
import random
import signal
import sys
import time
from pathlib import Path
from typing import Optional

import soco.discovery
import spotipy
from dotenv import load_dotenv
from spotipy.exceptions import SpotifyException
from spotipy.oauth2 import CacheFileHandler, SpotifyOAuth

from content_checker import ContentChecker, TrackEvalResult
from drug_scanner import DrugScanner
from lyrics_service import LyricsService
from profanity_scanner import ProfanityScanner
from sexual_content_scanner import SexualContentScanner
from skip_client import SocoSkipClient, SpotifySkipClient
from track_cache import SQLiteTrackCache

load_dotenv()

# ---------------------------------------------------------------------------
# Configuration — all values from .env (D-05, D-10, D-14)
# ---------------------------------------------------------------------------
POLL_INTERVAL = float(os.environ.get("POLL_INTERVAL_SECONDS", "1"))       # D-04, D-05
HEARTBEAT_INTERVAL = float(os.environ.get("HEARTBEAT_INTERVAL_SECONDS", "300"))  # D-10
STATE_PATH = os.environ.get("STATE_PATH", "state.json")
PROFANITY_MIN_SEVERITY = int(os.environ.get("PROFANITY_MIN_SEVERITY", "2"))  # D-10
IDLE_THRESHOLD: int = 3  # consecutive empty polls before writing idle state (D-03)
LYRICS_DB_PATH = os.environ.get("LYRICS_DB_PATH", "lyrics_cache.db")
EVENTS_PATH = os.environ.get("EVENTS_PATH", "data/events.jsonl")
NOW_PLAYING_PATH = os.path.join(os.path.dirname(EVENTS_PATH) or ".", "now_playing.json")

# ---------------------------------------------------------------------------
# Filter Profile Map (Phase 16, PROF-03)
# Maps active_profile state.json keys to ContentChecker constructor kwargs.
# Scanner objects are long-lived; only the ContentChecker wrapper is rebuilt on change.
# ---------------------------------------------------------------------------
PROFILE_MAP: dict = {
    "kids_present": {
        "explicit_skip": True,
        "min_severity": 2,
        "drug": True,
        "sexual": True,
        "profanity": True,
        "lyrics": True,
    },
    "were_all_adults": {
        "explicit_skip": False,
        "min_severity": 3,
        "drug": False,
        "sexual": True,
        "profanity": True,
        "lyrics": True,
    },
    "above_the_covers": {
        "explicit_skip": False,
        "min_severity": 2,
        "drug": False,
        "sexual": True,
        "profanity": False,
        "lyrics": True,
    },
    "permissive": {
        "explicit_skip": True,
        "min_severity": 2,
        "drug": False,
        "sexual": False,
        "profanity": False,
        "lyrics": False,
    },
}

# ---------------------------------------------------------------------------
# Monotonic event ID counter (HIST-03, Phase 15)
# ---------------------------------------------------------------------------
_event_counter = 0


def _init_event_counter() -> None:
    """Seed _event_counter from the last event's id in events.jsonl.

    Called at daemon startup so new events continue from the last known id.
    Sets counter to 0 if the file does not exist or has no valid events.
    """
    global _event_counter
    _event_counter = 0
    try:
        with open(EVENTS_PATH) as f:
            lines = f.readlines()
        for line in reversed(lines):
            line = line.strip()
            if not line:
                continue
            try:
                evt = json.loads(line)
                _event_counter = evt.get("id", 0)
                return
            except json.JSONDecodeError:
                continue
    except FileNotFoundError:
        pass

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
# Shared skip event queue — consumed by web_ui SSE endpoint (Phase 3, D-08)
skip_event_queue: asyncio.Queue = asyncio.Queue()


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


def save_state(daemon_fields: dict) -> None:
    """Merge daemon_fields into the current on-disk state and write back.

    Reads the existing state.json first so that keys written externally
    (e.g. family_safe_mode from `make fsm-on`) are not overwritten.

    Direct write (not atomic rename) — os.replace() fails on bind-mounted
    files on Linux (EBUSY). Safe here: the daemon recovers cleanly from a
    missing/corrupt file via load_state().
    """
    on_disk = load_state()
    on_disk.update(daemon_fields)
    with open(STATE_PATH, "w") as f:
        json.dump(on_disk, f)


def _append_event(event: dict) -> None:
    """Append a JSON line to the events log (all daemon event types).

    Assigns a monotonic integer id to every event (HIST-03).
    Creates a copy of the event dict to avoid mutating the caller's object.
    """
    global _event_counter
    _event_counter += 1
    payload = {**event, "id": _event_counter}
    try:
        os.makedirs(os.path.dirname(EVENTS_PATH) or ".", exist_ok=True)
        with open(EVENTS_PATH, "a") as f:
            f.write(json.dumps(payload) + "\n")
            f.flush()
    except OSError as exc:
        log.error("[EVENTS] failed to write event log: %s", exc)


def _write_now_playing(data: dict) -> None:
    """Write current track state to now_playing.json (D-06).

    Overwrites the file on every call — first call at eval_state='evaluating',
    second call after evaluation completes with final eval_state.
    Direct write (not atomic rename — os.replace() raises EBUSY on bind-mounted files).
    """
    try:
        os.makedirs(os.path.dirname(NOW_PLAYING_PATH) or ".", exist_ok=True)
        with open(NOW_PLAYING_PATH, "w") as f:
            json.dump(data, f)
    except OSError as exc:
        log.error("[NOW_PLAYING] failed to write: %s", exc)


def _emit_eval_result(
    track_id: str,
    track_name: str,
    artist: str,
    album_art_url: Optional[str],
    eval_state: str,
    severity: int,
    result: Optional["TrackEvalResult"],
) -> None:
    """Emit eval_result event to events.jsonl and now_playing.json atomically (D-04, D-10).

    Accepts result=None for the fsm-off path where no scan ran (D-05).
    All four boolean fields default to False when result is None (D-09).
    """
    explicit = result.explicit if result is not None else False
    profanity = result.profanity if result is not None else False
    drug_reference = result.drug_reference if result is not None else False
    sexual_content = result.sexual_content if result is not None else False

    _append_event({
        "type": "eval_result",
        "track_id": track_id,
        "eval_state": eval_state,
        "severity": severity,
        "explicit": explicit,
        "profanity": profanity,
        "drug_reference": drug_reference,
        "sexual_content": sexual_content,
        "timestamp": time.strftime("%H:%M:%S"),
    })
    _write_now_playing({
        "track_id": track_id,
        "track": track_name,
        "artist": artist,
        "album_art_url": album_art_url,
        "eval_state": eval_state,
        "severity": severity,
        "explicit": explicit,
        "profanity": profanity,
        "drug_reference": drug_reference,
        "sexual_content": sexual_content,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
    })


def _build_content_checker(
    profile_key: str,
    lyrics_service,
    profanity_scanner,
    drug_scanner,
    sexual_content_scanner,
    track_cache=None,   # D-07: default None disables caching
) -> ContentChecker:
    """Construct ContentChecker from the active profile config (D-14, D-15, PROF-03).

    Scanner objects (lyrics_service, profanity_scanner, etc.) are long-lived instances
    created once in main(). Only the ContentChecker wrapper is rebuilt when profile changes.
    Passing None for a scanner disables that scan tier.

    Args:
        profile_key: Key from PROFILE_MAP (e.g. "kids_present"). Falls back to
            "kids_present" if unknown.
        track_cache: TrackCache instance for result caching, or None to disable.
    """
    cfg = PROFILE_MAP.get(profile_key, PROFILE_MAP["kids_present"])
    use_lyrics = cfg.get("lyrics", True)
    use_profanity = cfg.get("profanity", True) and use_lyrics
    return ContentChecker(
        lyrics_service=lyrics_service if use_lyrics else None,
        profanity_scanner=profanity_scanner if use_profanity else None,
        drug_scanner=drug_scanner if cfg["drug"] else None,
        sexual_content_scanner=sexual_content_scanner if cfg["sexual"] else None,
        min_severity=cfg["min_severity"],
        explicit_skip=cfg["explicit_skip"],
        track_cache=track_cache,
    )


# ---------------------------------------------------------------------------
# Sonos startup probe (Phase 4, D-01 through D-07)
# ---------------------------------------------------------------------------
async def probe_sonos_speakers(soco_client: SocoSkipClient) -> None:
    """Eager SSDP discovery at daemon startup (D-01, D-02, D-03, D-05, D-06, D-07).

    Skipped if SONOS_SPEAKER_IPS is already set (D-02 — existing bypass preserved).
    Non-blocking: probe result is informational only; daemon starts regardless (D-03).
    Pre-seeds soco_client._ip_cache so first skip has no SSDP latency.
    """
    if os.environ.get("SONOS_SPEAKER_IPS"):
        log.info("[SONOS] IP override active (SONOS_SPEAKER_IPS set) — skipping SSDP discovery")
        return

    log.info("[SONOS] Starting SSDP discovery (timeout=5s)...")
    loop = asyncio.get_event_loop()
    speakers = await loop.run_in_executor(None, soco.discovery.discover)

    if speakers:
        for speaker in speakers:
            soco_client._ip_cache[speaker.player_name] = speaker.ip_address
            log.info('[SONOS] Discovered: "%s" (%s)', speaker.player_name, speaker.ip_address)
    else:
        log.warning(
            "[SONOS] No speakers found via SSDP. Ensure multicast UDP port 1900 is open "
            "on the host firewall. Set SONOS_SPEAKER_IPS=Name=IP in .env as a fallback. "
            "See README for firewall setup."
        )


def _eval_state_from_result(action: str, reason: str) -> str:
    """Map ContentChecker (action, reason) tuple to canonical eval_state string (D-02)."""
    if action == "allow":
        if reason in ("lyrics_unavailable", "no_lyrics_service"):
            return "no-lyrics"
        return "passed"
    # action == "skip" — caller handles "paused" and "skipped" separately
    return "skipped"


# ---------------------------------------------------------------------------
# Poll loop
# ---------------------------------------------------------------------------
async def poll_loop(
    sp: spotipy.Spotify,
    content_checker: ContentChecker,
    soco_skip: SocoSkipClient,
    spotify_skip: SpotifySkipClient,
    lyrics_service=None,
    profanity_scanner=None,
    drug_scanner=None,
    sexual_content_scanner=None,
    track_cache=None,
) -> None:
    """Main polling coroutine. Runs until stop_event is set."""
    state = load_state()
    consecutive_skips: int = 0
    prev_fsm: bool = False
    prev_profile: str = state.get("active_profile", "kids_present")
    idle_counter: int = 0      # consecutive empty-playback polls (D-04)
    was_idle: bool = False     # dedup flag — gates idle write to once per transition (D-05)
    last_heartbeat = time.monotonic()

    _consecutive_401s = 0  # D-01: consecutive 401 counter; sys.exit(2) after 3

    log.info(
        "Daemon started. Poll interval=%.1fs, heartbeat=%.1fs",
        POLL_INTERVAL,
        HEARTBEAT_INTERVAL,
    )

    while not stop_event.is_set():
        Path('/app/.healthcheck').touch()
        try:
            result = sp.currently_playing()
            _consecutive_401s = 0  # D-02: reset on any successful Spotify API call

            if result is None or result.get("item") is None:
                # 204 No Content (nothing playing) or item=null (podcast/ad)
                idle_counter += 1
                if idle_counter >= IDLE_THRESHOLD and not was_idle:
                    _write_now_playing({"status": "idle"})
                    _append_event({
                        "type": "idle",
                        "timestamp": time.strftime("%H:%M:%S"),
                    })
                    was_idle = True
                    log.info("[IDLE] no active playback — idle state written")
                # D-09: log only the heartbeat, not every silent poll
                if time.monotonic() - last_heartbeat >= HEARTBEAT_INTERVAL:
                    log.info("Heartbeat: daemon alive, no playback detected")
                    last_heartbeat = time.monotonic()

            else:
                # Item present (playing or paused) — reset idle state unconditionally (D-04, pitfall 1)
                idle_counter = 0
                was_idle = False
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
                    save_state({"last_track_id": track_id})
                    state = load_state()   # re-read disk so family_safe_mode and future keys are fresh
                    last_heartbeat = time.monotonic()

                    # Gap-3 fix: reset consecutive_skips when FSM transitions from off to on
                    fsm_now = state.get("family_safe_mode", False)
                    if not prev_fsm and fsm_now:
                        consecutive_skips = 0
                        log.info("[FSM] consecutive_skips reset — FSM re-enabled")
                    prev_fsm = fsm_now

                    current_profile = state.get("active_profile", "kids_present")
                    if current_profile != prev_profile:
                        content_checker = _build_content_checker(
                            current_profile,
                            lyrics_service,
                            profanity_scanner,
                            drug_scanner,
                            sexual_content_scanner,
                            track_cache,
                        )
                        prev_profile = current_profile
                        log.info("[PROFILE] switched to %r", current_profile)

                    # DAEM-01: emit track_change immediately on detection, before evaluation
                    images = track.get("album", {}).get("images", [])
                    album_art_url = images[0]["url"] if images else None
                    _append_event({
                        "type": "track_change",
                        "track_id": track_id,
                        "track": track["name"],
                        "artist": track["artists"][0]["name"],
                        "album_art_url": album_art_url,
                        "eval_state": "evaluating",
                        "timestamp": time.strftime("%H:%M:%S"),
                    })
                    # DAEM-03: write now_playing.json at "evaluating" state (D-06)
                    _write_now_playing({
                        "track_id": track_id,
                        "track": track["name"],
                        "artist": track["artists"][0]["name"],
                        "album_art_url": album_art_url,
                        "eval_state": "evaluating",
                        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
                    })

                    # Phase 2: Content filtering (FSM-02: only when FSM is on)
                    # D-06: read family_safe_mode each cycle — toggle takes effect within 1 poll
                    if state.get("family_safe_mode", False):
                        device = result.get("device", {})
                        device_name = device.get("name", "unknown")
                        is_restricted = device.get("is_restricted", False)

                        # D-02: Log device info on every track change
                        log.info(
                            "[DEVICE] name=%r is_restricted=%s",
                            device_name, is_restricted,
                        )

                        eval_result = await content_checker.check(track)

                        # D-09: [SCAN] log is emitted inside content_checker.check()
                        # for all code paths (explicit, instrumental, profanity, clean, etc.)

                        if eval_result.action == "allow":
                            consecutive_skips = 0
                            # DAEM-02: emit eval_result for every allowed track
                            eval_state = _eval_state_from_result(eval_result.action, eval_result.reason)
                            _emit_eval_result(
                                track_id=track_id,
                                track_name=track["name"],
                                artist=track["artists"][0]["name"],
                                album_art_url=album_art_url,
                                eval_state=eval_state,
                                severity=eval_result.severity,
                                result=eval_result,
                            )

                        if eval_result.action == "skip":
                            # SKIP-03: Select skip client based on is_restricted (D-01).
                            # When Spotify Connect controls a Sonos, UPnP next() fails with
                            # error 701 (queue owned by Spotify, not Sonos). Fall back to
                            # spotify_skip in that case — it works despite is_restricted=True.
                            client = soco_skip if is_restricted else spotify_skip

                            # Phase 3 D-11/D-13: on the 5th consecutive skip, pause instead
                            # of skipping. Pausing on the current track avoids the race where
                            # skip() moves Spotify to the next track before pause() fires,
                            # causing playback to continue.
                            if consecutive_skips + 1 >= 5:
                                log.warning("[5SKIP] 5 consecutive skips — pausing playback")
                                paused = await client.pause(device_name, device.get("id"))
                                if not paused and is_restricted:
                                    paused = await spotify_skip.pause(device_name, device.get("id"))
                                if not paused:
                                    log.warning("[5SKIP] pause failed for device %r — playback may continue", device_name)
                                skip_event_queue.put_nowait({
                                    "type": "five_skip_warning",
                                    "timestamp": time.strftime("%H:%M:%S"),
                                })
                                _append_event({
                                    "type": "five_skip_warning",
                                    "timestamp": time.strftime("%H:%M:%S"),
                                })
                                consecutive_skips = 0
                                # DAEM-02: eval_result for 5th-skip pause
                                _emit_eval_result(
                                    track_id=track_id,
                                    track_name=track["name"],
                                    artist=track["artists"][0]["name"],
                                    album_art_url=album_art_url,
                                    eval_state="paused",
                                    severity=eval_result.severity,
                                    result=eval_result,
                                )
                            else:
                                success = await client.skip(device_name, device.get("id"))
                                if not success and is_restricted:
                                    log.info("[SKIP] SoCo failed, retrying via Spotify API for %r", device_name)
                                    success = await spotify_skip.skip(device_name, device.get("id"))

                                if success:
                                    # D-07: Structured skip log
                                    log.info(
                                        "[SKIP] reason=%s track=%r artist=%r",
                                        eval_result.reason,
                                        track["name"],
                                        track["artists"][0]["name"],
                                    )
                                    # Phase 3 D-08: push structured event to SSE queue
                                    skip_event_queue.put_nowait({
                                        "type": "skip",
                                        "track": track["name"],
                                        "artist": track["artists"][0]["name"],
                                        "reason": eval_result.reason,
                                        "explicit": eval_result.explicit,
                                        "profanity": eval_result.profanity,
                                        "drug_reference": eval_result.drug_reference,
                                        "sexual_content": eval_result.sexual_content,
                                        "timestamp": time.strftime("%H:%M:%S"),
                                    })
                                    _append_event({
                                        "type": "skip",
                                        "track": track["name"],
                                        "artist": track["artists"][0]["name"],
                                        "reason": eval_result.reason,
                                        "explicit": eval_result.explicit,
                                        "profanity": eval_result.profanity,
                                        "drug_reference": eval_result.drug_reference,
                                        "sexual_content": eval_result.sexual_content,
                                        "timestamp": time.strftime("%H:%M:%S"),
                                    })
                                    consecutive_skips += 1
                                    # DAEM-02: eval_result for successful auto-skip
                                    _emit_eval_result(
                                        track_id=track_id,
                                        track_name=track["name"],
                                        artist=track["artists"][0]["name"],
                                        album_art_url=album_art_url,
                                        eval_state="skipped",
                                        severity=eval_result.severity,
                                        result=eval_result,
                                    )
                                else:
                                    log.warning(
                                        "[SKIP_FAILED] reason=%s track=%r artist=%r",
                                        eval_result.reason,
                                        track["name"],
                                        track["artists"][0]["name"],
                                    )
                    else:
                        # FSM off — D-03: still emit eval_result with fsm-off
                        # severity=0: no profanity check ran (FSM disabled)
                        _emit_eval_result(
                            track_id=track_id,
                            track_name=track["name"],
                            artist=track["artists"][0]["name"],
                            album_art_url=album_art_url,
                            eval_state="fsm-off",
                            severity=0,
                            result=None,
                        )

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
                _consecutive_401s += 1
                log.error(
                    "Auth error (401): %s — consecutive count: %d",
                    exc, _consecutive_401s,
                )
                if _consecutive_401s >= 3:
                    log.error(
                        "3 consecutive 401s — token revoked, exiting with code 2"
                    )
                    sys.exit(2)

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
        scope="user-read-currently-playing user-modify-playback-state",
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

    # Phase 2 + Phase 16: Build scanner instances once; ContentChecker is profile-aware
    lyrics_service = LyricsService(db_path=LYRICS_DB_PATH)
    track_cache = SQLiteTrackCache(db_path=LYRICS_DB_PATH)
    profanity_scanner = ProfanityScanner(min_severity=PROFANITY_MIN_SEVERITY)
    drug_scanner = DrugScanner()
    sexual_content_scanner = SexualContentScanner()
    startup_state = load_state()
    startup_profile = startup_state.get("active_profile", "kids_present")
    content_checker = _build_content_checker(
        startup_profile, lyrics_service, profanity_scanner, drug_scanner,
        sexual_content_scanner, track_cache
    )
    log.info("[PROFILE] startup profile: %r", startup_profile)
    soco_skip = SocoSkipClient()
    spotify_skip = SpotifySkipClient(sp)

    _init_event_counter()  # HIST-03: seed event counter from last known id

    await probe_sonos_speakers(soco_skip)   # D-01: eager startup probe, non-blocking (D-03)

    await poll_loop(
        sp,
        content_checker,
        soco_skip,
        spotify_skip,
        lyrics_service,
        profanity_scanner,
        drug_scanner,
        sexual_content_scanner,
        track_cache,
    )
    await lyrics_service.close()
    await track_cache.close()
    log.info("Daemon stopped cleanly")


if __name__ == "__main__":
    asyncio.run(main())
