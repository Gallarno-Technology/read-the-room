"""Read the Room — Web UI Service (single household).

FastAPI app serving the dashboard HTML and providing:
  GET  /              -> HTML dashboard (redirects to /auth/login if no token)
  GET  /auth/login    -> redirect to Spotify authorization
  GET  /auth/callback -> exchange code, write token cache, redirect to /
  GET  /events        -> SSE stream of skip events tailed from events.jsonl
  GET  /fsm           -> current FSM state {"family_safe_mode": bool}
  POST /fsm           -> toggle FSM {"enabled": bool} -> {"family_safe_mode": bool}
  GET  /profile       -> current active filter profile
  POST /profile       -> set active filter profile
  GET  /now-playing   -> current track state; {"status":"idle"} when absent
  POST /skip          -> skip current track via Spotify API; {"ok":true} on success
                         (also logs a 'manual_skip' feedback row for review)
  POST /feedback      -> 👎 on an auto-skip event {"event_id": int, "note"?: str}
  GET  /review        -> feedback review + golden set page
  GET  /api/feedback  -> feedback rows (?status=pending|promoted|dismissed|all)
  POST /api/feedback/{id}/promote -> copy into golden set with expected verdicts
  POST /api/feedback/{id}/dismiss -> mark reviewed, not promoted
  GET  /api/golden-set            -> golden set rows
  DELETE /api/golden-set/{id}     -> remove a golden set row
  GET  /golden-set.csv            -> golden set export

Single-user model: one Spotify account per deployment. All on-disk paths are
process-global env vars shared with the daemon container (STATE_PATH,
EVENTS_PATH, SPOTIFY_CACHE_PATH). The daemon runs as its own container and
polls Spotify; this service only reads the files it produces and writes the
FSM/profile toggles plus the OAuth token cache.

SSE tail architecture:
  _tail_task: single asyncio.Task tailing events.jsonl (lazy start)
  _subscribers: list of per-tab asyncio.Queue instances
asyncio is single-threaded; no locks needed.
"""

import asyncio
import csv
import html as _html
import io
import json
import logging
import os
from typing import AsyncGenerator

import spotipy
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import (
    HTMLResponse,
    JSONResponse,
    RedirectResponse,
    Response,
    StreamingResponse,
)
from pydantic import BaseModel
from spotipy.oauth2 import CacheFileHandler, SpotifyOAuth

from feedback_store import FeedbackStore
from profiles import DEFAULT_PROFILE, PROFILES
from skip_client import SocoSkipClient

load_dotenv()

log = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")

# ---------------------------------------------------------------------------
# Process-global paths — shared with the daemon container via .env (D-06).
# Defaults match daemon.py so both services agree when env vars are unset.
# ---------------------------------------------------------------------------
STATE_PATH = os.environ.get("STATE_PATH", "state.json")
EVENTS_PATH = os.environ.get("EVENTS_PATH", "data/events.jsonl")
NOW_PLAYING_PATH = os.path.join(os.path.dirname(EVENTS_PATH) or ".", "now_playing.json")
SPOTIFY_CACHE_PATH = os.environ.get("SPOTIFY_CACHE_PATH", "token_cache/.cache")

# Scope must exactly match daemon.py — a mismatch causes Spotify 403.
SCOPE = "user-read-playback-state user-read-currently-playing user-modify-playback-state"
# Fixed OAuth state token — single-user CSRF guard (no per-user uid anymore).
_OAUTH_STATE = "read-the-room"


app = FastAPI(title="Read the Room", docs_url=None, redoc_url=None)


# ---------------------------------------------------------------------------
# Spotipy client — per-request, reads the shared token cache from disk (D-10)
# ---------------------------------------------------------------------------


def _sp_init() -> "spotipy.Spotify | None":
    """Create a spotipy client from the shared token cache.

    Called per-request (not cached at module level) so the auth manager always
    reads the current token from disk. The daemon keeps the cache file fresh via
    its own refresh cycle; a stale module-level client would hold an expired
    token in memory and fail after ~60 min.
    """
    client_id = os.environ.get("SPOTIFY_CLIENT_ID")
    client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET")
    redirect_uri = os.environ.get("SPOTIFY_REDIRECT_URI")
    if not all([SPOTIFY_CACHE_PATH, client_id, client_secret, redirect_uri]):
        log.warning(
            "web_ui: Spotify env vars not set — POST /skip will return 503 until configured"
        )
        return None
    if not os.path.exists(SPOTIFY_CACHE_PATH):
        log.warning(
            "web_ui: token cache %s not found — authenticate via /auth/login first",
            SPOTIFY_CACHE_PATH,
        )
    cache_handler = CacheFileHandler(cache_path=SPOTIFY_CACHE_PATH)
    auth_manager = SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope=SCOPE,
        open_browser=False,
        cache_handler=cache_handler,
    )
    return spotipy.Spotify(auth_manager=auth_manager)


def _auth_manager() -> SpotifyOAuth:
    """Build a SpotifyOAuth bound to the shared token cache for onboarding."""
    return SpotifyOAuth(
        client_id=os.environ["SPOTIFY_CLIENT_ID"],
        client_secret=os.environ["SPOTIFY_CLIENT_SECRET"],
        redirect_uri=os.environ["SPOTIFY_REDIRECT_URI"],
        scope=SCOPE,
        open_browser=False,
        cache_handler=CacheFileHandler(cache_path=SPOTIFY_CACHE_PATH),
        state=_OAUTH_STATE,
    )


def _is_authenticated() -> bool:
    """True when a Spotify token cache exists on disk."""
    return os.path.exists(SPOTIFY_CACHE_PATH)


def _error_html(status_code: int, reason: str) -> HTMLResponse:
    """Return a minimal human-readable error page for OAuth callback failures."""
    html = (
        "<!DOCTYPE html>"
        "<html><head><title>Authorization Error</title></head>"
        "<body>"
        "<h2>Authorization Failed</h2>"
        f"<pre>{_html.escape(reason)}</pre>"
        '<p><a href="/auth/login">Try again</a></p>'
        "</body></html>"
    )
    return HTMLResponse(content=html, status_code=status_code)


# ---------------------------------------------------------------------------
# SSE tail infrastructure — single tail task, list of subscriber queues.
# asyncio single-threaded — no locks needed.
# ---------------------------------------------------------------------------

_tail_task: "asyncio.Task | None" = None
_subscribers: list[asyncio.Queue] = []


async def _file_tail() -> None:
    """Tail events.jsonl and push new events to all subscribers.

    Starts reading from the END of the file (live events only). Runs until
    cancelled (when the last subscriber disconnects).
    """
    log.info("web_ui: tailing %s", EVENTS_PATH)
    while not os.path.exists(EVENTS_PATH):
        await asyncio.sleep(1)

    with open(EVENTS_PATH) as fh:
        fh.seek(0, 2)  # seek to end — skip existing history
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
            dead = []
            for q in _subscribers:
                try:
                    q.put_nowait(event)
                except asyncio.QueueFull:
                    dead.append(q)
            for q in dead:
                try:
                    _subscribers.remove(q)
                except ValueError:
                    pass


def _ensure_tail() -> None:
    """Start the tail task if not already running (lazy start)."""
    global _tail_task
    if _tail_task is None or _tail_task.done():
        _tail_task = asyncio.create_task(_file_tail())


def _teardown_tail_if_empty() -> None:
    """Cancel the tail task if no subscribers remain (immediate teardown)."""
    global _tail_task
    if not _subscribers and _tail_task is not None:
        if not _tail_task.done():
            _tail_task.cancel()
        _tail_task = None


# ---------------------------------------------------------------------------
# State helpers — replicate daemon save_state() read-merge-write pattern (D-09)
# ---------------------------------------------------------------------------


def _load_state() -> dict:
    try:
        with open(STATE_PATH) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"last_track_id": None, "family_safe_mode": False}


def _save_state_merge(fields: dict) -> None:
    """Read-merge-write: never drops keys the daemon owns. Direct write (no atomic
    rename — os.replace() raises EBUSY on bind-mounted files on Linux)."""
    on_disk = _load_state()
    on_disk.update(fields)
    with open(STATE_PATH, "w") as f:
        json.dump(on_disk, f)


# ---------------------------------------------------------------------------
# Pydantic request models
# ---------------------------------------------------------------------------


class FSMRequest(BaseModel):
    enabled: bool


class ProfileRequest(BaseModel):
    profile: str


class FeedbackRequest(BaseModel):
    event_id: int
    note: str = ""


class PromoteRequest(BaseModel):
    family_friendly: str
    mixed_company: str
    close_friends: str
    notes: str = ""


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/", response_class=HTMLResponse, response_model=None)
async def dashboard() -> HTMLResponse | RedirectResponse:
    """Serve the dashboard HTML.

    Redirects to /auth/login when no Spotify token cache exists yet so the
    household can complete OAuth on first visit.
    """
    if not _is_authenticated():
        return RedirectResponse(url="/auth/login", status_code=302)
    template_path = os.path.join(TEMPLATES_DIR, "index.html")
    try:
        with open(template_path) as f:
            html = f.read()
    except FileNotFoundError:
        html = "<html><body><p>Dashboard template not installed.</p></body></html>"
    # Inject current FSM + profile state so controls render correctly on first load
    state = _load_state()
    fsm_on = str(state.get("family_safe_mode", False)).lower()
    html = html.replace("__FSM_INITIAL__", fsm_on)
    active_profile = state.get("active_profile", DEFAULT_PROFILE)
    html = html.replace("__PROFILE_INITIAL__", active_profile)
    return HTMLResponse(content=html)


# ---------------------------------------------------------------------------
# OAuth onboarding — single-user Authorization Code flow
# ---------------------------------------------------------------------------


@app.get("/auth/login")
async def auth_login() -> RedirectResponse:
    """Redirect the browser to Spotify's authorization page."""
    try:
        url = _auth_manager().get_authorize_url()
    except KeyError as exc:
        return _error_html(500, f"Missing Spotify env var: {exc}")
    return RedirectResponse(url=url, status_code=302)


@app.get("/auth/callback", response_model=None)
async def auth_callback(request: Request) -> HTMLResponse | RedirectResponse:
    """Spotify OAuth callback — validate state, exchange code, write token cache."""
    error = request.query_params.get("error")
    code = request.query_params.get("code")
    state = request.query_params.get("state")

    if error:
        return _error_html(400, f"Authorization was denied: {error}")
    if not code:
        return _error_html(400, "Missing authorization code from Spotify")
    if state != _OAUTH_STATE:
        return _error_html(400, "State mismatch — please retry the login")

    try:
        auth_manager = _auth_manager()
        # check_cache=False forces a fresh exchange, skipping any stale cached token
        auth_manager.get_access_token(code, as_dict=False, check_cache=False)
    except KeyError as exc:
        return _error_html(500, f"Missing Spotify env var: {exc}")
    except Exception as exc:  # noqa: BLE001
        log.error("web_ui: token exchange failed: %s", exc)
        return _error_html(500, f"Token exchange failed: {exc}")

    log.info(
        "web_ui: Spotify token written to %s — daemon will pick it up",
        SPOTIFY_CACHE_PATH,
    )
    return RedirectResponse(url="/", status_code=302)


# ---------------------------------------------------------------------------
# SSE — live event stream
# ---------------------------------------------------------------------------


async def _sse_event_generator(subscriber: asyncio.Queue) -> AsyncGenerator[str, None]:
    """Yield SSE-formatted strings from the subscriber queue indefinitely.

    Sends a `:` comment heartbeat every 15s if no events arrive — keeps the
    reverse proxy from closing the stream as idle. Browsers ignore comment lines.
    """
    try:
        while True:
            try:
                event = await asyncio.wait_for(subscriber.get(), timeout=15)
            except asyncio.TimeoutError:
                yield ": keepalive\n\n"
                continue
            payload = json.dumps(event)
            yield f"data: {payload}\n\n"
    except asyncio.CancelledError:
        pass
    finally:
        try:
            _subscribers.remove(subscriber)
        except ValueError:
            pass
        _teardown_tail_if_empty()


@app.get("/events")
async def sse_events() -> StreamingResponse:
    """SSE endpoint. Browser opens EventSource('/events'); daemon events stream in.

    Each client gets its own asyncio.Queue (max 100 items) so a slow client can't
    block the broadcaster. The tail task starts lazily on first connection.
    """
    subscriber: asyncio.Queue = asyncio.Queue(maxsize=100)
    _subscribers.append(subscriber)
    _ensure_tail()
    # Adaptive polling kick (quick task 260504-jkb): touch a kick file in the
    # events/data dir so the daemon's next iteration polls immediately instead of
    # waiting up to POLL_INTERVAL_IDLE. The data dir is the volume shared with the
    # daemon container (state.json is a single-file mount, so its dir is not
    # shared). Best-effort — must not block the response.
    try:
        kick_path = os.path.join(os.path.dirname(EVENTS_PATH) or ".", "poll_kick")
        with open(kick_path, "w"):
            pass
    except OSError as exc:
        log.warning("web_ui: could not touch poll_kick: %s", exc)
    return StreamingResponse(
        _sse_event_generator(subscriber),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# Family Safe Mode toggle
# ---------------------------------------------------------------------------


@app.get("/fsm")
async def get_fsm() -> JSONResponse:
    """Return current FSM state."""
    state = _load_state()
    return JSONResponse({"family_safe_mode": state.get("family_safe_mode", False)})


@app.post("/fsm")
async def set_fsm(body: FSMRequest) -> JSONResponse:
    """Toggle FSM. Reads state.json, merges {family_safe_mode: bool}, writes back."""
    try:
        _save_state_merge({"family_safe_mode": body.enabled})
    except OSError as exc:
        log.error("POST /fsm write failed: %s", exc)
        raise HTTPException(status_code=500, detail="Could not write state.json")
    return JSONResponse({"family_safe_mode": body.enabled})


# ---------------------------------------------------------------------------
# Filter Profile — PROF-01, PROF-02 (Phase 16)
# ---------------------------------------------------------------------------

VALID_PROFILES: frozenset = frozenset(PROFILES)


@app.get("/profile")
async def get_profile() -> JSONResponse:
    """Return current active profile from state.json."""
    state = _load_state()
    return JSONResponse({"active_profile": state.get("active_profile", DEFAULT_PROFILE)})


@app.post("/profile")
async def set_profile(body: ProfileRequest) -> JSONResponse:
    """Save active profile to state.json via read-merge-write (D-11, PROF-02).

    Returns 400 for unknown profile keys. Does NOT modify family_safe_mode.
    """
    if body.profile not in VALID_PROFILES:
        raise HTTPException(
            status_code=400, detail=f"Unknown profile: {body.profile!r}"
        )
    try:
        _save_state_merge({"active_profile": body.profile})
    except OSError as exc:
        log.error("POST /profile write failed: %s", exc)
        raise HTTPException(status_code=500, detail="Could not write state.json")
    return JSONResponse({"active_profile": body.profile})


# ---------------------------------------------------------------------------
# Now Playing — hydration endpoint for page-load (Phase 7)
# ---------------------------------------------------------------------------


def _read_now_playing() -> dict | None:
    """now_playing.json contents, or None when absent/unparseable."""
    try:
        with open(NOW_PLAYING_PATH) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


@app.get("/now-playing")
async def now_playing() -> JSONResponse:
    """Return current track state from now_playing.json for page-load hydration.

    Returns {"status": "idle"} (HTTP 200) if the file does not yet exist.
    """
    data = _read_now_playing()
    if data is None:
        return JSONResponse({"status": "idle"}, headers={"Cache-Control": "no-store"})
    return JSONResponse(data, headers={"Cache-Control": "no-store"})


# ---------------------------------------------------------------------------
# Feed — skip history (Phase 15, HIST-03, D-01)
# ---------------------------------------------------------------------------


@app.get("/feed")
async def feed() -> JSONResponse:
    """Return last 20 skip/five_skip_warning events, newest-first (HIST-03, D-01)."""
    try:
        with open(EVENTS_PATH) as f:
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
    try:
        flagged = _store().flagged_event_ids()
    except Exception as exc:  # noqa: BLE001 — feedback must never break the feed
        log.warning("feed: could not read feedback store: %s", exc)
        flagged = set()
    for evt in events:
        evt["feedback_sent"] = evt.get("id") in flagged
    return JSONResponse(events, headers={"Cache-Control": "no-store"})


# ---------------------------------------------------------------------------
# Manual Skip — Spotify API with SoCo UPnP fallback for restricted devices
# (Phase 7, SKIP-02, SKIP-03)
# ---------------------------------------------------------------------------

_soco_skip = SocoSkipClient()


@app.post("/skip")
async def skip_track() -> JSONResponse:
    """Skip the current track.

    Tries the Spotify Web API first. If the active device is restricted (Sonos
    returns 403), falls back to SoCo UPnP — the same strategy the daemon uses.

    Returns {"ok": true} on success (HTTP 200).
    Returns HTTP 503 with {"detail": "skip_failed", "reason": "..."} on any error.
    """
    client = _sp_init()
    if client is None:
        return JSONResponse(
            status_code=503,
            content={
                "detail": "skip_failed",
                "reason": "Spotify client not configured",
            },
        )
    # Snapshot what's playing BEFORE skipping — the daemon rewrites
    # now_playing.json as soon as it sees the next track.
    playing = _read_now_playing()
    try:
        client.next_track()
        _log_manual_skip(playing)
        return JSONResponse({"ok": True})
    except spotipy.SpotifyException as exc:
        if exc.http_status != 403:
            log.warning("POST /skip failed: %s", exc)
            return JSONResponse(
                status_code=503,
                content={"detail": "skip_failed", "reason": str(exc)},
            )
        # 403 Restricted device — fall back to SoCo UPnP (same as daemon)
        log.info(
            "POST /skip: Spotify API returned 403 (restricted device), trying SoCo fallback"
        )
        try:
            playback = client.current_playback()
            if not playback or not playback.get("device"):
                return JSONResponse(
                    status_code=503,
                    content={
                        "detail": "skip_failed",
                        "reason": "No active playback device",
                    },
                )
            device = playback["device"]
            success = await _soco_skip.skip(device["name"], device.get("id", ""))
            if success:
                _log_manual_skip(playing)
                return JSONResponse({"ok": True})
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "skip_failed",
                    "reason": "SoCo fallback failed — check Sonos network",
                },
            )
        except Exception as fallback_exc:  # noqa: BLE001
            log.warning("POST /skip SoCo fallback failed: %s", fallback_exc)
            return JSONResponse(
                status_code=503,
                content={"detail": "skip_failed", "reason": str(fallback_exc)},
            )


# ---------------------------------------------------------------------------
# Listener feedback + golden set
#
# 👎 on an auto-skip (wrong_skip) and every in-app manual skip (manual_skip) are
# logged with the active profile and the LLM's full analysis, then reviewed on
# /review and optionally promoted into the golden set — the known-borderline
# list rubric revisions get A/B tested against.
# ---------------------------------------------------------------------------

# Event types a 👎 can target: auto-skips and the 5th-skip pause (which carries
# the paused track's details).
_FEEDBACK_EVENT_TYPES = ("skip", "five_skip_warning")


def _store() -> FeedbackStore:
    """Per-request store. Lives beside events.jsonl in the shared data/ volume
    (FEEDBACK_DB_PATH overrides); resolved per call so tests that repoint
    EVENTS_PATH get an isolated database."""
    path = os.environ.get("FEEDBACK_DB_PATH") or os.path.join(
        os.path.dirname(EVENTS_PATH) or ".", "feedback.db"
    )
    return FeedbackStore(path)


def _find_event(event_id: int) -> dict | None:
    """Find an event by id in events.jsonl, scanning newest-first."""
    try:
        with open(EVENTS_PATH) as f:
            lines = f.readlines()
    except FileNotFoundError:
        return None
    for line in reversed(lines):
        try:
            evt = json.loads(line)
        except json.JSONDecodeError:
            continue
        if evt.get("id") == event_id:
            return evt
    return None


def _log_manual_skip(playing: dict | None) -> None:
    """Record an in-app manual skip as feedback. Best-effort — a feedback write
    failure must never turn a successful skip into an error."""
    if not playing or not playing.get("track_id"):
        return
    try:
        _store().add_feedback(
            kind="manual_skip",
            track_id=playing.get("track_id"),
            track=playing.get("track") or "Unknown track",
            artist=playing.get("artist") or "Unknown artist",
            profile=playing.get("profile") or _load_state().get("active_profile"),
            eval_state=playing.get("eval_state"),
            reason=playing.get("reason", ""),
            detail=playing.get("detail", ""),
            analysis=playing.get("analysis"),
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("manual-skip feedback not recorded: %s", exc)


@app.post("/feedback")
async def post_feedback(body: FeedbackRequest) -> JSONResponse:
    """👎 an auto-skip. The server snapshots the event itself (by id) rather than
    trusting client-sent reasoning. Repeat votes on the same event are no-ops."""
    evt = _find_event(body.event_id)
    if evt is None or evt.get("type") not in _FEEDBACK_EVENT_TYPES or not evt.get("track"):
        raise HTTPException(status_code=404, detail="Skip event not found")
    row, created = _store().add_feedback(
        kind="wrong_skip",
        event_id=body.event_id,
        track_id=evt.get("track_id"),
        track=evt["track"],
        artist=evt.get("artist") or "Unknown artist",
        profile=evt.get("profile"),
        eval_state="paused" if evt["type"] == "five_skip_warning" else "skipped",
        reason=evt.get("reason", ""),
        detail=evt.get("detail", ""),
        analysis=evt.get("analysis"),
        note=body.note,
    )
    return JSONResponse({"feedback": row, "created": created}, status_code=201 if created else 200)


@app.get("/review", response_class=HTMLResponse)
async def review_page() -> HTMLResponse:
    with open(os.path.join(TEMPLATES_DIR, "review.html")) as f:
        return HTMLResponse(content=f.read())


@app.get("/api/feedback")
async def list_feedback(status: str = "pending") -> JSONResponse:
    if status not in ("pending", "promoted", "dismissed", "all"):
        raise HTTPException(status_code=400, detail=f"Unknown status: {status!r}")
    rows = _store().list_feedback(None if status == "all" else status)
    return JSONResponse(rows, headers={"Cache-Control": "no-store"})


@app.post("/api/feedback/{feedback_id}/promote")
async def promote_feedback(feedback_id: int, body: PromoteRequest) -> JSONResponse:
    expected = {
        "family_friendly": body.family_friendly,
        "mixed_company": body.mixed_company,
        "close_friends": body.close_friends,
    }
    try:
        golden = _store().promote(feedback_id, expected, notes=body.notes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if golden is None:
        raise HTTPException(status_code=404, detail="Feedback not found")
    return JSONResponse(golden)


@app.post("/api/feedback/{feedback_id}/dismiss")
async def dismiss_feedback(feedback_id: int) -> JSONResponse:
    if not _store().set_status(feedback_id, "dismissed"):
        raise HTTPException(status_code=404, detail="Feedback not found")
    return JSONResponse({"ok": True})


@app.get("/api/golden-set")
async def list_golden_set() -> JSONResponse:
    return JSONResponse(_store().list_golden(), headers={"Cache-Control": "no-store"})


@app.delete("/api/golden-set/{golden_id}")
async def delete_golden(golden_id: int) -> JSONResponse:
    if not _store().delete_golden(golden_id):
        raise HTTPException(status_code=404, detail="Golden set entry not found")
    return JSONResponse({"ok": True})


@app.get("/golden-set.csv")
async def golden_set_csv() -> Response:
    """Export in the same column shape as rtr-test-fixtures.csv's verdict columns."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "Song", "Artist", "Spotify Track ID",
        "Family Friendly Expected", "Mixed Company Expected", "Close Friends Expected",
        "Notes", "Source",
    ])
    for g in _store().list_golden():
        writer.writerow([
            g["track"], g["artist"], g["track_id"] or "",
            g["expected"]["family_friendly"], g["expected"]["mixed_company"],
            g["expected"]["close_friends"], g["notes"], g["source"],
        ])
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="golden-set.csv"'},
    )
