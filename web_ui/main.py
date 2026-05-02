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
import html as _html
import json
import logging
import os
import pathlib
import sys
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncGenerator

from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth, CacheFileHandler
from fastapi import Cookie, Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
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

# Scope must exactly match scripts/manage_users.py SCOPE — scope mismatch causes Spotify 403.
CALLBACK_SCOPE = "user-read-currently-playing user-modify-playback-state"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Boot-time daemon launch for all active users (PROC-04, D-09).

    Spawns a daemon and starts a supervisor task for each user with
    status == 'active' in users.json. On shutdown, cancels supervisor tasks
    to prevent 'Task was destroyed but it is pending!' warnings in tests.
    """
    supervisor_tasks: list[asyncio.Task] = []
    users = _registry.load()
    for user in users:
        if user.get("status") == "active":
            uid = user["uid"]
            try:
                await _spawn_daemon(uid)
                task = asyncio.create_task(_supervisor_for_uid(uid))
                supervisor_tasks.append(task)
                log.info("web_ui: lifespan — started daemon + supervisor for uid=%s", uid)
            except Exception as exc:
                log.error("web_ui: lifespan — failed to start daemon for uid=%s: %s", uid, exc)
    yield
    # Shutdown: cancel supervisor tasks (prevents asyncio "pending task" warnings)
    for task in supervisor_tasks:
        if not task.done():
            task.cancel()


app = FastAPI(title="Read the Room", lifespan=lifespan, docs_url=None, redoc_url=None)


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


def _error_html(status_code: int, reason: str) -> HTMLResponse:
    """Return a minimal human-readable error page for OAuth callback failures (D-03).

    No JSON — the user came from a browser and expects readable output.
    """
    html = (
        "<!DOCTYPE html>"
        "<html><head><title>Authorization Error</title></head>"
        "<body>"
        "<h2>Authorization Failed</h2>"
        f"<pre>{_html.escape(reason)}</pre>"
        "<p>Please contact the operator to get a new authorization link.</p>"
        "</body></html>"
    )
    return HTMLResponse(content=html, status_code=status_code)


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
    try:
        return UserContext(
            uid=uid,
            state_path=paths["state_path"],
            events_path=paths["events_path"],
            now_playing_path=paths["now_playing_path"],
            token_cache_path=paths["cache_path"],
        )
    except KeyError as exc:
        log.error("web_ui: user_paths missing expected key for uid=%s: %s", uid, exc)
        raise HTTPException(status_code=500, detail="user configuration error")


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

# _daemons: uid -> live asyncio.subprocess.Process for that user's daemon
# asyncio is single-threaded; no lock needed.
_daemons: dict[str, asyncio.subprocess.Process] = {}


async def _spawn_daemon(uid: str) -> asyncio.subprocess.Process:
    """Spawn a daemon process for uid. Write PID file. Store in _daemons.

    Per D-06: called by lifespan (boot) and /auth/callback (new user).
    Sets all uid-specific env vars plus POLL_INTERVAL_SECONDS=3 (PROC-03).
    stderr=DEVNULL: avoids pipe-buffer stall (RESEARCH.md Pitfall 5).
    """
    daemon_path = str(pathlib.Path(__file__).parent.parent / "daemon.py")
    paths = _registry.user_paths(uid)
    env = os.environ.copy()
    env["STATE_PATH"] = paths["state_path"]
    env["EVENTS_PATH"] = paths["events_path"]
    env["LYRICS_DB_PATH"] = str(pathlib.Path(__file__).parent.parent / "lyrics_cache.db")
    env["SPOTIFY_CACHE_PATH"] = paths["cache_path"]
    env["POLL_INTERVAL_SECONDS"] = "3"  # PROC-03
    proc = await asyncio.create_subprocess_exec(
        sys.executable, daemon_path,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
        env=env,
    )
    # Write PID file (D-11) — log warning on failure, do not raise
    pid_path = pathlib.Path(__file__).parent.parent / "users" / uid / "daemon.pid"
    try:
        pid_path.write_text(str(proc.pid))
    except OSError as exc:
        log.warning("web_ui: could not write daemon.pid for uid=%s: %s", uid, exc)
    _daemons[uid] = proc
    log.info("web_ui: daemon spawned pid=%d for uid=%s", proc.pid, uid)
    return proc


async def _supervisor_for_uid(uid: str) -> None:
    """Supervise daemon for uid. Restart on unexpected exit. Stop on clean exit or removal.

    Per D-04: launched as asyncio.Task by lifespan and /auth/callback.
    Per D-07: restarts immediately on unexpected exit (no delay at 5-user scale).
    Per D-08: no max retry count.
    Per D-13: re-checks registry after each exit; stops if uid no longer active.
    """
    while True:
        proc = _daemons.get(uid)
        if proc is None:
            log.info("web_ui: supervisor uid=%s — no process in _daemons, exiting", uid)
            return
        exit_code = await proc.wait()
        # D-13: re-check registry after exit — handles remove-while-running
        users = _registry.load()
        active_uids = {u["uid"] for u in users if u.get("status") == "active"}
        if uid not in active_uids:
            log.info("web_ui: supervisor uid=%s — uid removed from registry, exiting supervisor", uid)
            _daemons.pop(uid, None)
            return
        if exit_code == 0:
            log.info("web_ui: supervisor uid=%s — clean exit (code 0), not restarting", uid)
            _daemons.pop(uid, None)
            return
        if exit_code == 2:
            log.warning(
                "web_ui: uid=%s daemon exited with code 2 (token revoked) — "
                "re-onboard user via manage_users.py",
                uid,
            )
            _daemons.pop(uid, None)
            return
        # Unexpected exit — restart immediately (D-07)
        log.warning("web_ui: uid=%s daemon exited with code %s — restarting", uid, exit_code)
        try:
            await _spawn_daemon(uid)
        except Exception as spawn_exc:
            log.error(
                "web_ui: supervisor uid=%s — restart spawn failed: %s; "
                "retrying in 30s",
                uid, spawn_exc,
            )
            await asyncio.sleep(30)
            continue
        # Loop continues — supervisor awaits the new process


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
# Pydantic request models — used by routes below
# ---------------------------------------------------------------------------

class FSMRequest(BaseModel):
    enabled: bool


class ProfileRequest(BaseModel):
    profile: str


class LoginRequest(BaseModel):
    uid: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse, response_model=None)
async def dashboard(
    request: Request,
    uid: str | None = Cookie(default=None),
) -> HTMLResponse | RedirectResponse:
    """Serve the dashboard HTML.

    Phase 32 D-02: No Depends(get_user_context) — this is an HTML route that must
    redirect browsers instead of returning 401 JSON. Manual cookie check replaces
    the dependency.
    """
    # Phase 32 D-02: redirect unauthenticated browsers to the ID gate
    if uid is None:
        return RedirectResponse(url="/login", status_code=302)
    users = _registry.load()
    user = next((u for u in users if u["uid"] == uid), None)
    if user is None or user.get("status") != "active":
        # D-10: pending status treated identically to unknown
        return RedirectResponse(url="/login", status_code=302)
    try:
        paths = _registry.user_paths(uid)
    except ValueError:
        return RedirectResponse(url="/login", status_code=302)
    ctx = UserContext(
        uid=uid,
        state_path=paths["state_path"],
        events_path=paths["events_path"],
        now_playing_path=paths["now_playing_path"],
        token_cache_path=paths["cache_path"],
    )
    # Serve dashboard — identical to original body below this point
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


@app.get("/login", response_class=HTMLResponse)
async def login_page() -> HTMLResponse:
    """Serve the login gate page (Phase 32 D-04).

    Always serves login.html regardless of cookie state — no redirect-if-authed.
    """
    template_path = os.path.join(TEMPLATES_DIR, "login.html")
    with open(template_path) as f:
        html = f.read()
    return HTMLResponse(content=html)


@app.post("/login")
async def login(body: LoginRequest) -> JSONResponse:
    """Validate access code, set uid cookie, return ok flag (Phase 32 D-07/D-08/D-09).

    Returns HTTP 200 in both success and error cases so gate JS can always read
    the body without special error-handling branches (D-09).
    """
    users = _registry.load()
    user = next((u for u in users if u["uid"] == body.uid), None)
    if user is None or user.get("status") != "active":
        # D-09: HTTP 200 with ok=false; D-10: pending treated as unknown
        return JSONResponse({"ok": False, "error": "Unknown access code"})
    response = JSONResponse({"ok": True})
    response.set_cookie(
        key="uid",
        value=body.uid,
        httponly=True,
        samesite="lax",
        path="/",
        max_age=60 * 60 * 24 * 30,  # 30 days — exact attrs from auth_callback (Phase 29/31)
        secure=True,
    )
    return response


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
# OAuth Callback — server-side Authorization Code Flow completion (Phase 29)
# AUTH-01: validate state, exchange code, write token, activate user
# AUTH-02: uid travels via state param — callback reads request.query_params["state"]
# AUTH-03: daemon spawned fire-and-forget after token write
# ---------------------------------------------------------------------------

@app.get("/auth/callback", response_model=None)
async def auth_callback(request: Request) -> HTMLResponse | RedirectResponse:
    """Spotify OAuth callback — validates state, exchanges code, spawns daemon.

    No Depends(get_user_context) — uid not yet in cookie when this runs.
    """
    error = request.query_params.get("error")
    code = request.query_params.get("code")
    uid = request.query_params.get("state")

    # Handle Spotify-side denial or missing params (D-03)
    if error:
        return _error_html(400, f"Authorization was denied: {error}")
    if not code:
        return _error_html(400, "Missing authorization code from Spotify")
    if not uid:
        return _error_html(400, "Missing state parameter")

    # Validate uid is known and status is "pending" (D-04)
    users = _registry.load()
    user = next((u for u in users if u["uid"] == uid), None)
    if user is None or user.get("status") != "pending":
        return _error_html(400, "Unrecognized or already-active authorization request")

    # Exchange authorization code for token (D-06)
    # Per-request SpotifyOAuth — NOT module-level (anti-pattern: stale tokens)
    try:
        paths = _registry.user_paths(uid)
        cache_handler = CacheFileHandler(cache_path=paths["cache_path"])
        auth_manager = SpotifyOAuth(
            client_id=os.environ["SPOTIFY_CLIENT_ID"],
            client_secret=os.environ["SPOTIFY_CLIENT_SECRET"],
            redirect_uri=os.environ["SPOTIFY_REDIRECT_URI"],
            scope=CALLBACK_SCOPE,
            open_browser=False,
            cache_handler=cache_handler,
            state=uid,
        )
        # check_cache=False forces fresh exchange — skips any stale cached token
        auth_manager.get_access_token(code, as_dict=False, check_cache=False)
    except Exception as exc:
        log.error("web_ui: token exchange failed for uid=%s: %s", uid, exc)
        return _error_html(500, f"Token exchange failed: {exc}")

    # Flip user status to "active" in users.json (D-07, AUTH-01)
    try:
        _registry.activate(uid)
    except Exception as exc:
        log.error(
            "web_ui: registry activate failed for uid=%s — token written but user not activated; "
            "run 'manage_users.py remove %s' to clean up orphaned entry: %s",
            uid, uid, exc,
        )
        return _error_html(500, "Failed to activate user: account cleanup required")

    # Spawn daemon and start supervisor task (D-06, PROC-02, AUTH-03)
    # _spawn_daemon handles env vars, PID file, and _daemons dict storage.
    # supervisor task ensures daemon is restarted on crash.
    try:
        await _spawn_daemon(uid)
        asyncio.create_task(_supervisor_for_uid(uid))
    except Exception as exc:
        # Log and continue — redirect still happens even if spawn fails (D-06)
        log.error("web_ui: daemon spawn failed for uid=%s: %s", uid, exc)

    # Set uid cookie and redirect to dashboard (D-01, D-02)
    response = RedirectResponse(url="/", status_code=302)
    response.set_cookie(
        key="uid",
        value=uid,
        httponly=True,
        samesite="lax",
        path="/",
        max_age=60 * 60 * 24 * 30,  # 30 days — survives browser restarts
        secure=True,
    )
    return response


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
