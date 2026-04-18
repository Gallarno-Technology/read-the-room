"""Read the Room — Web UI Service.

FastAPI app serving the dashboard HTML and providing:
  GET  /              -> HTML dashboard (template rendered by Plan 03-02)
  GET  /events        -> SSE stream of skip events — per-user tail task (Phase 28)
  GET  /fsm           -> current FSM state {"family_safe_mode": bool}
  POST /fsm           -> toggle FSM {"enabled": bool} -> {"family_safe_mode": bool}
  GET  /now-playing   -> current track state from now_playing.json; {"status":"idle"} when absent
  POST /skip          -> skip current track via Spotify API; {"ok":true} on success

Phase 28: All routes resolve per-user file paths from a uid httpOnly cookie via
get_user_context(). Global STATE_PATH, EVENTS_PATH, NOW_PLAYING_PATH globals removed
(D-09). _sp_init() accepts cache_path parameter (D-10).

SSE tail architecture (D-05, D-06, D-07):
  _tails: dict[str, asyncio.Task]  — one tail task per active uid (lazy start)
  _subscribers: dict[str, list[asyncio.Queue]]  — per-uid list of tab queues
asyncio is single-threaded; no locks needed on _tails or _subscribers.
"""
import asyncio
import json
import logging
import os
import pathlib
from dataclasses import dataclass
from typing import AsyncGenerator

from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth, CacheFileHandler
from fastapi import Cookie, Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from skip_client import SocoSkipClient
from user_registry import UserRegistry

load_dotenv()

log = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")

app = FastAPI(title="Read the Room", docs_url=None, redoc_url=None)


# ---------------------------------------------------------------------------
# UserContext — per-request resolved from uid cookie (D-03, D-04)
# ---------------------------------------------------------------------------

@dataclass
class UserContext:
    uid: str
    state_path: str
    events_path: str
    now_playing_path: str
    token_cache_path: str


# Registry singleton — base_dir is project root (parent of web_ui/).
# asyncio is single-threaded; no lock needed on this object.
_registry = UserRegistry(base_dir=str(pathlib.Path(__file__).parent.parent))


def get_user_context(uid: str | None = Cookie(default=None)) -> UserContext:
    """Resolve per-user paths from uid httpOnly cookie.

    Raises HTTPException(401) if cookie is absent, uid is unknown, or
    user status is 'pending' (OAuth not yet complete — D-01, D-02).
    No redirect in this phase; Phase 32 converts 401 at GET / to a redirect.
    """
    if uid is None:
        raise HTTPException(status_code=401, detail="uid cookie required")
    users = _registry.load()
    user = next((u for u in users if u["uid"] == uid), None)
    if user is None or user.get("status") == "pending":
        raise HTTPException(status_code=401, detail="unknown uid")
    try:
        paths = _registry.user_paths(uid)
    except ValueError:
        raise HTTPException(status_code=401, detail="unknown uid")
    return UserContext(
        uid=uid,
        state_path=paths["state_path"],
        events_path=paths["events_path"],
        now_playing_path=paths["now_playing_path"],
        token_cache_path=paths["cache_path"],
    )


# ---------------------------------------------------------------------------
# Spotipy client — per-request, cache_path from UserContext (D-10)
# ---------------------------------------------------------------------------

def _sp_init(cache_path: str) -> "spotipy.Spotify | None":
    """Create spotipy client using the given per-user token cache path (D-10).

    Called per-request (not cached at module level) so the auth manager always
    reads the current token from disk.  The daemon keeps the cache file fresh
    via its own refresh cycle; a stale module-level client would hold an expired
    token in memory and fail after ~60 min.
    """
    client_id = os.environ.get("SPOTIFY_CLIENT_ID")
    client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET")
    redirect_uri = os.environ.get("SPOTIFY_REDIRECT_URI")
    if not all([cache_path, client_id, client_secret, redirect_uri]):
        log.warning("web_ui: Spotify env vars not set — POST /skip will return 503 until configured")
        return None
    if not os.path.exists(cache_path):
        log.warning(
            "web_ui: token cache %s not found — POST /skip will fail until daemon authenticates",
            cache_path,
        )
    cache_handler = CacheFileHandler(cache_path=cache_path)
    auth_manager = SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope="user-read-currently-playing user-modify-playback-state",
        open_browser=False,
        cache_handler=cache_handler,
    )
    return spotipy.Spotify(auth_manager=auth_manager)


# ---------------------------------------------------------------------------
# Per-uid SSE tail infrastructure (D-05, D-06, D-07, D-08)
# asyncio single-threaded — no locks needed on _tails or _subscribers.
# ---------------------------------------------------------------------------

# _tails: uid -> running asyncio.Task for that user's file tail
_tails: dict[str, asyncio.Task] = {}
# _subscribers: uid -> list of per-tab asyncio.Queue instances
_subscribers: dict[str, list[asyncio.Queue]] = {}


async def _file_tail_for_uid(uid: str, events_path: str) -> None:
    """Tail events.jsonl for a specific uid and push new events to that uid's subscribers.

    Starts reading from the END of the file on start (D-08) — live events only.
    Runs until cancelled (when last subscriber disconnects — D-07).
    """
    log.info("web_ui: tailing %s for uid=%s", events_path, uid)
    # Wait until the file exists (daemon may start slightly after web_ui)
    while not os.path.exists(events_path):
        await asyncio.sleep(1)

    with open(events_path) as fh:
        fh.seek(0, 2)  # seek to end — skip existing history (D-08)
        while True:
            line = fh.readline()
            if not line:
                await asyncio.sleep(0.25)  # poll every 250 ms
                continue
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                log.warning("web_ui: skipping malformed event line: %r", line)
                continue
            queues = _subscribers.get(uid, [])
            dead = []
            for q in queues:
                try:
                    q.put_nowait(event)
                except asyncio.QueueFull:
                    dead.append(q)
            for q in dead:
                try:
                    _subscribers[uid].remove(q)
                except (KeyError, ValueError):
                    pass


def _ensure_tail(uid: str, events_path: str) -> None:
    """Start the tail task for uid if not already running (D-06 — lazy start)."""
    task = _tails.get(uid)
    if task is None or task.done():
        _tails[uid] = asyncio.create_task(_file_tail_for_uid(uid, events_path))


def _teardown_tail_if_empty(uid: str) -> None:
    """Cancel the tail task for uid if no subscribers remain (D-07 — immediate teardown)."""
    if not _subscribers.get(uid):
        task = _tails.pop(uid, None)
        if task and not task.done():
            task.cancel()


# ---------------------------------------------------------------------------
# State helpers — replicate daemon save_state() read-merge-write pattern (D-09)
# ---------------------------------------------------------------------------

def _load_state(state_path: str) -> dict:
    try:
        with open(state_path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"last_track_id": None, "family_safe_mode": False}


def _save_state_merge(state_path: str, fields: dict) -> None:
    """Read-merge-write: never drops keys the daemon owns. Direct write (no atomic rename
    — os.replace() raises EBUSY on bind-mounted files on Linux, per Phase 1 decision)."""
    on_disk = _load_state(state_path)
    on_disk.update(fields)
    with open(state_path, "w") as f:
        json.dump(on_disk, f)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, ctx: UserContext = Depends(get_user_context)) -> HTMLResponse:
    """Serve the dashboard HTML. Template file created in Plan 03-02."""
    template_path = os.path.join(TEMPLATES_DIR, "index.html")
    try:
        with open(template_path) as f:
            html = f.read()
    except FileNotFoundError:
        html = "<html><body><p>Dashboard template not yet installed (Plan 03-02).</p></body></html>"
    # Inject current FSM state so the button renders correctly on first load
    state = _load_state(ctx.state_path)
    fsm_on = str(state.get("family_safe_mode", False)).lower()
    html = html.replace("__FSM_INITIAL__", fsm_on)
    active_profile = state.get("active_profile", "kids_present")
    html = html.replace("__PROFILE_INITIAL__", active_profile)
    return HTMLResponse(content=html)


async def _sse_event_generator(uid: str, subscriber: asyncio.Queue) -> AsyncGenerator[str, None]:
    """Yield SSE-formatted strings from the subscriber queue indefinitely."""
    try:
        while True:
            event = await subscriber.get()
            payload = json.dumps(event)
            yield f"data: {payload}\n\n"
    except asyncio.CancelledError:
        pass
    finally:
        # Remove this subscriber queue and teardown tail if no subscribers remain (D-07)
        try:
            _subscribers[uid].remove(subscriber)
        except (KeyError, ValueError):
            pass
        _teardown_tail_if_empty(uid)


@app.get("/events")
async def sse_events(ctx: UserContext = Depends(get_user_context)) -> StreamingResponse:
    """SSE endpoint. Browser opens EventSource('/events'); daemon pushes skip events.

    Each client gets its own asyncio.Queue (max 100 items) to prevent slow clients
    from blocking the broadcaster. Tail task starts lazily on first connection (D-06).
    """
    subscriber: asyncio.Queue = asyncio.Queue(maxsize=100)
    if ctx.uid not in _subscribers:
        _subscribers[ctx.uid] = []
    _subscribers[ctx.uid].append(subscriber)
    _ensure_tail(ctx.uid, ctx.events_path)
    return StreamingResponse(
        _sse_event_generator(ctx.uid, subscriber),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


class FSMRequest(BaseModel):
    enabled: bool


@app.get("/fsm")
async def get_fsm(ctx: UserContext = Depends(get_user_context)) -> JSONResponse:
    """Return current FSM state."""
    state = _load_state(ctx.state_path)
    return JSONResponse({"family_safe_mode": state.get("family_safe_mode", False)})


@app.post("/fsm")
async def set_fsm(body: FSMRequest, ctx: UserContext = Depends(get_user_context)) -> JSONResponse:
    """Toggle FSM. Reads state.json, merges {family_safe_mode: bool}, writes back (D-09).
    Returns updated state."""
    try:
        _save_state_merge(ctx.state_path, {"family_safe_mode": body.enabled})
    except OSError as exc:
        log.error("POST /fsm write failed: %s", exc)
        raise HTTPException(status_code=500, detail="Could not write state.json")
    return JSONResponse({"family_safe_mode": body.enabled})


# ---------------------------------------------------------------------------
# Filter Profile — PROF-01, PROF-02 (Phase 16)
# ---------------------------------------------------------------------------

VALID_PROFILES: frozenset = frozenset({
    "kids_present",
    "were_all_adults",
    "above_the_covers",
    "permissive",
})


class ProfileRequest(BaseModel):
    profile: str


@app.get("/profile")
async def get_profile(ctx: UserContext = Depends(get_user_context)) -> JSONResponse:
    """Return current active profile from state.json."""
    state = _load_state(ctx.state_path)
    return JSONResponse({"active_profile": state.get("active_profile", "kids_present")})


@app.post("/profile")
async def set_profile(body: ProfileRequest, ctx: UserContext = Depends(get_user_context)) -> JSONResponse:
    """Save active profile to state.json via read-merge-write pattern (D-11, PROF-02).

    Returns 400 for unknown profile keys. Does NOT modify family_safe_mode (D-09, D-13).
    """
    if body.profile not in VALID_PROFILES:
        raise HTTPException(status_code=400, detail=f"Unknown profile: {body.profile!r}")
    try:
        _save_state_merge(ctx.state_path, {"active_profile": body.profile})
    except OSError as exc:
        log.error("POST /profile write failed: %s", exc)
        raise HTTPException(status_code=500, detail="Could not write state.json")
    return JSONResponse({"active_profile": body.profile})


# ---------------------------------------------------------------------------
# Now Playing — hydration endpoint for page-load (Phase 7, SKIP-02 support)
# ---------------------------------------------------------------------------

@app.get("/now-playing")
async def now_playing(ctx: UserContext = Depends(get_user_context)) -> JSONResponse:
    """Return current track state from now_playing.json for page-load hydration.

    Returns {"status": "idle"} (HTTP 200) if the file does not yet exist.
    Returns the file's full JSON contents verbatim if a track is/was playing.
    No staleness detection — Phase 8 SSE reconnect is the staleness signal (D-03).
    """
    try:
        with open(ctx.now_playing_path) as f:
            data = json.load(f)
        return JSONResponse(data, headers={"Cache-Control": "no-store"})
    except (FileNotFoundError, json.JSONDecodeError):
        return JSONResponse({"status": "idle"}, headers={"Cache-Control": "no-store"})


# ---------------------------------------------------------------------------
# Feed — skip history persistence (Phase 15, HIST-03, D-01)
# ---------------------------------------------------------------------------

@app.get("/feed")
async def feed(ctx: UserContext = Depends(get_user_context)) -> JSONResponse:
    """Return last 20 skip/five_skip_warning events, newest-first (HIST-03, D-01).

    Cache-Control: no-store prevents browsers from serving stale feed data on
    page refresh (fetch() default cache mode uses heuristic caching when no
    explicit directives are present).
    """
    try:
        with open(ctx.events_path) as f:
            lines = f.readlines()
    except FileNotFoundError:
        return JSONResponse([], headers={"Cache-Control": "no-store"})

    events = []
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            evt = json.loads(line)
        except json.JSONDecodeError:
            continue
        if evt.get("type") in ("skip", "five_skip_warning"):
            events.append(evt)
            if len(events) >= 20:
                break
    return JSONResponse(events, headers={"Cache-Control": "no-store"})


# ---------------------------------------------------------------------------
# Manual Skip — Spotify API with SoCo UPnP fallback for restricted devices
# (Phase 7, SKIP-02, SKIP-03)
# ---------------------------------------------------------------------------

_soco_skip = SocoSkipClient()


@app.post("/skip")
async def skip_track(ctx: UserContext = Depends(get_user_context)) -> JSONResponse:
    """Skip the current track.

    Tries Spotify Web API first.  If the active device is restricted (Sonos
    returns 403), falls back to SoCo UPnP — the same strategy the daemon uses.

    SKIP-03: does NOT increment consecutive_skips — that counter lives in daemon
    memory and is only touched by the daemon's own skip logic.

    Returns {"ok": true} on success (HTTP 200).
    Returns HTTP 503 with {"detail": "skip_failed", "reason": "..."} on any error.
    """
    client = _sp_init(ctx.token_cache_path)
    if client is None:
        return JSONResponse(
            status_code=503,
            content={"detail": "skip_failed", "reason": "Spotify client not configured"},
        )
    try:
        client.next_track()
        return JSONResponse({"ok": True})
    except spotipy.SpotifyException as exc:
        if exc.http_status != 403:
            log.warning("POST /skip failed: %s", exc)
            return JSONResponse(
                status_code=503,
                content={"detail": "skip_failed", "reason": str(exc)},
            )
        # 403 Restricted device — fall back to SoCo UPnP (same as daemon)
        log.info("POST /skip: Spotify API returned 403 (restricted device), trying SoCo fallback")
        try:
            playback = client.current_playback()
            if not playback or not playback.get("device"):
                return JSONResponse(
                    status_code=503,
                    content={"detail": "skip_failed", "reason": "No active playback device"},
                )
            device = playback["device"]
            success = await _soco_skip.skip(device["name"], device.get("id", ""))
            if success:
                return JSONResponse({"ok": True})
            return JSONResponse(
                status_code=503,
                content={"detail": "skip_failed", "reason": "SoCo fallback failed — check Sonos network"},
            )
        except Exception as fallback_exc:
            log.warning("POST /skip SoCo fallback failed: %s", fallback_exc)
            return JSONResponse(
                status_code=503,
                content={"detail": "skip_failed", "reason": str(fallback_exc)},
            )
